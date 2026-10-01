import os
from typing import TYPE_CHECKING

from groq import AsyncGroq
from dotenv import load_dotenv as _load_dotenv

if TYPE_CHECKING:
    from app.rag_service import RAGService

_groq_client: AsyncGroq | None = None
_groq_active_key: str | None = None

def _get_groq() -> AsyncGroq:
    global _groq_client, _groq_active_key
    _load_dotenv(override=True)
    current_key = os.getenv("GROQ_API_KEY")
    if _groq_client is None or current_key != _groq_active_key:
        _groq_active_key = current_key
        _groq_client = AsyncGroq(api_key=current_key)
    return _groq_client

_CHUNK_MAX = 150

_B2C_SYSTEM_PROMPT = """\
당신은 가전제품 소비자 구매 참고 리포트 작성 전문가입니다.
반드시 한국어로만 응답하세요. 영어·중국어·일본어 사용 금지.

[작성 규칙]
0. 질문이 가전제품·생활가전·주방가전·계절가전·영상음향기기와 무관한 경우, 리포트 형식 없이 단 한 문장으로만 응답하세요: "가전제품 관련 질문을 입력해주세요. (예: 로봇청소기 후기, 에어컨 추천)"
1. 아래 참고 문서에 실제로 언급된 내용만 작성하세요.
2. 문서에 없는 내용은 추측하거나 단정하지 마세요. 근거 없는 항목은 생략하세요.
3. 출처 번호([1], [2] 등)는 절대 표기하지 마세요. 문장만 자연스럽게 작성하세요.
4. 일반 소비자가 이해하기 쉬운 구어체로 작성하세요.
5. 반드시 아래 마크다운 형식으로만 응답하세요. JSON 금지.

[출력 형식]

## 소비자 구매 참고 리포트

### ✅ 주요 장점
- (장점 한 줄)

### ❌ 주요 단점
- (단점 한 줄)

### 💡 이런 분께 추천
(실제 후기 기반 추천 대상 1~2문장)

### ⚠️ 구매 전 확인사항
- (주의사항)

### 📝 한줄 요약
(전체를 한 문장으로 요약)
"""

_B2B_SYSTEM_PROMPT = """\
당신은 가전 시장 B2B 전략 리포트 작성 전문가입니다. 기업 기획자와 MD가 읽는 리포트를 작성합니다.
반드시 한국어로만 응답하세요. 영어·중국어·일본어 사용 금지.

[작성 규칙]
0. 질문이 가전제품·생활가전·주방가전·계절가전·영상음향기기와 무관한 경우, 리포트 형식 없이 단 한 문장으로만 응답하세요: "가전 시장 관련 질문을 입력해주세요. (예: 에어컨 시장 트렌드, 로봇청소기 소비자 페인포인트)"
1. 아래 참고 문서에 실제로 언급된 내용만 작성하세요.
2. 문서에 없는 내용은 추측하거나 단정하지 마세요. 근거 없는 항목은 생략하세요.
3. 출처 번호([1], [2] 등)는 절대 표기하지 마세요. 문장만 자연스럽게 작성하세요.
4. 비즈니스 관점의 인사이트와 전략적 시사점을 중심으로 작성하세요.
5. 반드시 아래 마크다운 형식으로만 응답하세요. JSON 금지.

[출력 형식]

## 시장 트렌드 리포트

### 📌 시장 동향 요약
(전체 시장 동향 2~3문장)

### 📈 주요 소비자 트렌드
- (트렌드 한 줄)

### 😤 소비자 페인포인트
- (소비자 불만 한 줄)

### 💼 사업 기회
- (기회 한 줄)

### 🎯 전략적 액션 아이템
1. (구체적 액션)
2. (구체적 액션)

### 👥 타겟 바이어 세그먼트
(주요 타겟 고객 설명)
"""

_EMPTY_REPORT = "RAG 데이터를 준비 중이에요. 잠시 후 다시 시도해주세요.\n\n서버 최초 실행 시 Naver 데이터를 수집하는 데 약 30초가 소요됩니다."


_GROQ_MODEL = "llama-3.3-70b-versatile"


_CACHE_TTL_HOURS = 24  # 가격이 매일 바뀌므로 하루만 재사용

# 이 문구들은 일시적 실패 안내라 캐시에 저장하지 않는다
_NO_CACHE_REPORTS = {
    _EMPTY_REPORT,
    "AI 분석을 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
    "답변을 만들지 못했어요. 질문을 조금 더 짧고 구체적으로 다시 입력해주세요.",
}


async def _cache_get(key: str) -> dict | None:
    try:
        from app.services.naver_cache import get_db_cache
        return await get_db_cache(key)
    except Exception as e:
        print(f"[Insight] 캐시 조회 실패: {e}")
        return None


async def _cache_get_stale(key: str) -> dict | None:
    """만료 여부와 상관없이 가장 최근 답변 — LLM이 전부 실패했을 때 대신 보여주는 용도."""
    try:
        from app.services.naver_cache import get_db_cache_stale
        return await get_db_cache_stale(key)
    except Exception as e:
        print(f"[Insight] 이전 답변 조회 실패: {e}")
        return None


async def _cache_set(key: str, result: dict) -> None:
    if result.get("report") in _NO_CACHE_REPORTS:
        return
    try:
        from datetime import datetime, timedelta, timezone
        from app.services.naver_cache import set_db_cache
        kst_now = datetime.now(timezone(timedelta(hours=9)))
        # 나중에 이전 답변으로 꺼내 쓸 때 "○월 ○일 기준"을 보여주려고 저장 날짜를 같이 남긴다
        payload = {**result, "cached_at": f"{kst_now.month}월 {kst_now.day}일"}
        await set_db_cache(key, payload, ttl_hours=_CACHE_TTL_HOURS)
    except Exception as e:
        print(f"[Insight] 캐시 저장 실패: {e}")


async def analyze(
    query: str,
    rag: "RAGService",
    target: str = "b2b",
    top_k: int = 5,
    context: dict | None = None,
) -> dict:
    """context(직전 질문 조건)를 반영해 조건을 뽑고, 답변에 이번 조건을 실어 보낸다.
    프론트는 이 conditions를 저장했다가 다음 질문 때 context로 다시 보내서 대화가 이어진다."""
    from app.services.query_parser import parse_query
    cond = parse_query(query, context)
    result = await _answer(cond, query, rag, target, top_k)

    ctx = cond.to_context()
    shown = result.pop("_shown", None)
    if shown:
        # '더 싼 거' · '다른 거'를 처리하려면 방금 보여준 상품의 가격 범위와 이름이 필요하다
        ctx.update(shown)
    elif context and context.get("category") == cond.category:
        # 이번에 상품 목록을 안 보여줬으면(LLM 답변) 직전 목록 기준을 그대로 이어간다
        for k in ("shown_min", "shown_max", "shown_titles"):
            if context.get(k) is not None:
                ctx[k] = context[k]
    result["conditions"] = ctx
    return result


async def _answer(
    cond,
    query: str,
    rag: "RAGService",
    target: str = "b2b",
    top_k: int = 5,
) -> dict:
    """질문 처리 흐름 — LLM은 마지막 수단으로만 쓴다.

    ① 조건 추출(정규식·별칭·오타 보정) → ② 캐시 → ③ 템플릿(추천·가격) → ④ LLM → ⑤ 캐시 저장
    ⑥ LLM이 전부 실패하면 만료된 캐시(예전 답변)라도 날짜 안내와 함께 보여준다
    """
    from app.services.product_finder import find_products
    from app.services.chat_templates import TEMPLATES, products_as_sources

    cache_key = cond.cache_key(target)
    print(f"[Insight] 조건: cat={cond.category} brand={cond.brand} "
          f"price={cond.min_price}~{cond.max_price} house={cond.household} intent={cond.intent} "
          f"followup={cond.extras.get('followup', False)}")

    # ② 캐시 — 표현이 달라도 조건이 같으면 같은 답을 재사용
    cached = await _cache_get(cache_key)
    if cached and cached.get("report"):
        print(f"[Insight] answered_by=cache ({cache_key})")
        return {**cached, "query": query, "target": target, "answered_by": "cache"}

    # ③ 템플릿 — 추천·가격 질문은 실제 상품 데이터를 틀에 채워 바로 답한다 (LLM 0회)
    if cond.category and cond.intent in TEMPLATES:
        products, nearest = await find_products(cond, rag)
        if products:
            prices = [p["price"] for p in products]
            # '다른 거'를 연달아 물으면 앞에서 보여준 것까지 계속 빼야 해서 목록을 누적한다
            prev_titles = cond.extras.get("exclude") if cond.extras.get("relative") == "more" else []
            shown_titles = list(prev_titles or []) + [p["title"] for p in products]
            result = {
                "query": query,
                "target": target,
                "report": TEMPLATES[cond.intent](cond, products, nearest),
                "sources": products_as_sources(products),
                "answered_by": "template",
                # '다른 거'를 계속 물어도 앞에서 보여준 건 계속 빼도록 누적 (최근 30개)
                "_shown": {"shown_min": min(prices), "shown_max": max(prices),
                           "shown_titles": shown_titles[-30:]},
            }
            await _cache_set(cache_key, result)
            print(f"[Insight] answered_by=template ({cache_key})")
            return result

    # ④ LLM — 템플릿이 없는 유형(비교·후기·트렌드 등)이거나 상품을 못 찾았을 때
    # 오타·줄임말(에어콘·로청)이면 표준 카테고리명을 붙여서 RAG 카테고리 필터가 걸리게 한다
    llm_query = f"{query} ({cond.category})" if cond.category and cond.category not in query else query
    if cond.extras.get("followup"):
        # "100만원대는?" 같은 이어 묻기는 LLM이 맥락을 모르니 이어받은 조건을 문장으로 붙여준다
        hint = [cond.category]
        if cond.household:
            hint.append(f"{cond.household}인 가구")
        if cond.brand:
            hint.append(cond.brand)
        if cond.extras.get("prev_shown"):
            hint.append("(앞에서 보여준 제품: " + " / ".join(cond.extras["prev_shown"]) + ")")
        llm_query = f"{' '.join(hint)} — {query}"
    result = await _llm_answer(llm_query, rag, target, top_k)
    result["query"] = query
    result["answered_by"] = "llm"

    # ⑥ LLM이 전부 실패했으면(안내 문구만 받았으면) 같은 질문의 예전 답변이라도 보여준다
    if result.get("report") in _NO_CACHE_REPORTS:
        stale = await _cache_get_stale(cache_key)
        if stale and stale.get("report") and stale["report"] not in _NO_CACHE_REPORTS:
            date = stale.get("cached_at", "이전")
            notice = f"⏳ 지금은 AI 분석이 어려워서 {date} 기준 답변을 보여드려요. 가격은 달라졌을 수 있어요."
            print(f"[Insight] answered_by=stale_cache ({cache_key})")
            return {**stale, "query": query, "target": target,
                    "report": notice + "\n\n" + stale["report"], "answered_by": "stale_cache"}

    await _cache_set(cache_key, result)
    print(f"[Insight] answered_by=llm ({cache_key})")
    return result


async def _llm_answer(
    query: str,
    rag: "RAGService",
    target: str = "b2b",
    top_k: int = 5,
) -> dict:
    """RAG 검색 결과를 Groq LLM에 전달해 마크다운 트렌드 리포트를 생성한다."""
    rag_query = (
        f"{query} 소비자 트렌드 구매 후기 특징"
        if target == "b2c"
        else f"{query} 시장 트렌드 소비자 반응"
    )

    from app.services.seed_rag import _CATEGORIES
    category = next((c for c in _CATEGORIES if c in query), None)
    where = {"product": category} if category else None

    chunks = await rag.query(rag_query, n_results=top_k, where=where) if rag else []
    if not chunks and where:  # 해당 카테고리 문서가 전혀 없을 때만 필터 없이 재시도
        chunks = await rag.query(rag_query, n_results=top_k) if rag else []

    if not chunks:
        return {
            "query": query,
            "target": target,
            "report": _EMPTY_REPORT,
            "sources": [],
        }

    numbered_chunks = [f"[{i + 1}] {chunk[:_CHUNK_MAX]}" for i, chunk in enumerate(chunks)]
    context = (
        f"[참고 문서 — {query} 관련 {len(chunks)}개]\n"
        + "\n".join(numbered_chunks)
    )
    system_prompt = _B2C_SYSTEM_PROMPT if target == "b2c" else _B2B_SYSTEM_PROMPT

    from app.routers.b2b_utils import _groq_create as _gc
    try:
        res = await _gc(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"제품/카테고리: {query}\n\n{context}"},
            ],
            max_tokens=2500,          # 추론 모델은 생각 토큰도 여기 포함 → 여유 있게
            temperature=0.3,
            reasoning_effort="low",   # 문서 정리 작업이라 깊은 추론 불필요 → 토큰 절약
        )
    except Exception:
        return {
            "query": query,
            "target": target,
            "report": "AI 분석을 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
            "sources": [],
        }

    report = (res.choices[0].message.content or "").strip()
    if not report:  # 생각만 하다 토큰이 끝나 본문이 비는 경우 방어
        report = "답변을 만들지 못했어요. 질문을 조금 더 짧고 구체적으로 다시 입력해주세요."
    sources = [{"rank": i + 1, "text": chunk} for i, chunk in enumerate(chunks)]

    return {
        "query": query,
        "target": target,
        "report": report,
        "sources": sources,
    }
