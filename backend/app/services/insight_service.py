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
당신은 가전제품 구매 상담을 해주는 친절한 AI 상담원입니다.
반드시 한국어로만 응답하세요. 영어·중국어·일본어 사용 금지.

[답변 원칙]
0. 이전 대화까지 봐도 가전제품과 전혀 무관한 질문이면 한 문장으로만 답하세요: "가전제품 관련 질문을 입력해주세요. (예: 로봇청소기 후기, 에어컨 추천)"
   이전 대화에서 이어지는 짧은 질문("전력효율은?", "그럼 소음은?")은 가전 질문으로 보고 답하세요.
1. 사용자가 방금 물어본 것에 바로 답하세요. 물어보지 않은 항목을 형식 맞추려고 채우지 마세요.
2. 구체적인 질문(전력효율·소음·용량·비교 등)은 3~8줄로 짧고 자연스럽게 답하세요. 필요할 때만 목록을 쓰세요.
3. "정리해줘"·"리포트"·"장단점 전부"처럼 종합 정리를 원할 때만 아래 정리 형식을 쓰세요.
4. 참고 문서와 이전 대화에 있는 내용만 근거로 쓰세요. 특히 [상품]으로 시작하는 줄은 실제 판매 중인 제품 데이터이니
   상품·브랜드를 물으면 먼저 이 데이터(모델명·가격·평점·후기 수)로 구체적으로 답하세요. "없다"고만 답하지 마세요.
   데이터에 없는 세부 수치(전력량·흡입력 등)만 지어내지 말고 "자료에서 확인되지 않아요"라고 한 뒤 확인 방법을 짧게 알려주세요.
5. 앞에서 보여준 제품이 있으면 그 제품들을 기준으로 답하세요.
6. 출처 번호([1], [2] 등)는 표기하지 마세요. JSON 금지. 일반 소비자가 이해하기 쉬운 구어체로 답하세요.

[정리 형식 — 종합 정리를 원할 때만]
## 소비자 구매 참고 리포트
### ✅ 주요 장점
### ❌ 주요 단점
### 💡 이런 분께 추천
### ⚠️ 구매 전 확인사항
### 📝 한줄 요약
"""

_B2B_SYSTEM_PROMPT = """\
당신은 가전 시장을 분석하는 B2B 전략 컨설턴트입니다. 기업 기획자와 MD의 질문에 답합니다.
반드시 한국어로만 응답하세요. 영어·중국어·일본어 사용 금지.

[답변 원칙]
0. 이전 대화까지 봐도 가전 시장과 전혀 무관한 질문이면 한 문장으로만 답하세요: "가전 시장 관련 질문을 입력해주세요. (예: 에어컨 시장 트렌드, 로봇청소기 소비자 페인포인트)"
   이전 대화에서 이어지는 짧은 질문("전력효율은?", "그럼 가격대는?")은 가전 질문으로 보고 답하세요.
1. 사용자가 방금 물어본 것에 바로 답하세요. 물어보지 않은 항목을 형식 맞추려고 채우지 마세요.
2. 구체적인 질문(특정 성능·가격대·경쟁 제품 등)은 핵심 인사이트 위주로 3~8줄로 답하세요. 필요할 때만 목록을 쓰세요.
3. "시장 동향"·"트렌드 리포트"·"전체 분석"처럼 시장 전반을 물을 때만 아래 리포트 형식을 쓰세요.
4. 참고 문서와 이전 대화에 있는 내용만 근거로 쓰세요. [상품]으로 시작하는 줄은 실제 판매 중인 제품 데이터이니
   상품·브랜드를 물으면 이 데이터(가격대·평점·후기 수)로 먼저 구체적으로 답하세요. 데이터에 없는 수치만 지어내지 마세요.
5. 앞에서 보여준 제품이 있으면 그 제품들을 기준으로 비즈니스 관점에서 답하세요.
6. 출처 번호([1], [2] 등)는 표기하지 마세요. JSON 금지.

[리포트 형식 — 시장 전반을 물을 때만]
## 시장 트렌드 리포트
### 📌 시장 동향 요약
### 📈 주요 소비자 트렌드
### 😤 소비자 페인포인트
### 💼 사업 기회
### 🎯 전략적 액션 아이템
### 👥 타겟 바이어 세그먼트
"""

_HISTORY_TURNS = 4        # 최근 몇 개 메시지를 LLM에 넘길지 (질문·답변 합쳐서)
_HISTORY_CHARS = 600      # 메시지 하나당 최대 글자 수 (토큰 절약)


def _history_messages(history: list[dict] | None) -> list[dict]:
    """프론트가 보낸 최근 대화를 Groq messages 형식으로 변환 (길이 제한)."""
    out = []
    for h in (history or [])[-_HISTORY_TURNS:]:
        role = "assistant" if h.get("role") in ("ai", "assistant") else "user"
        content = str(h.get("content") or "").strip()
        if content:
            out.append({"role": role, "content": content[:_HISTORY_CHARS]})
    return out


_EMPTY_REPORT = "RAG 데이터를 준비 중이에요. 잠시 후 다시 시도해주세요.\n\n서버 최초 실행 시 Naver 데이터를 수집하는 데 약 30초가 소요됩니다."


_GROQ_MODEL = "llama-3.3-70b-versatile"


_CACHE_TTL_HOURS = 24  # 가격이 매일 바뀌므로 하루만 재사용

# 이 문구들은 일시적 실패 안내라 캐시에 저장하지 않는다
_NO_CACHE_REPORTS = {
    _EMPTY_REPORT,
    "AI 분석을 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
    "답변을 만들지 못했어요. 질문을 조금 더 짧고 구체적으로 다시 입력해주세요.",
}


# "가전 관련 질문을 입력해주세요" 같은 거절 안내도 저장하지 않는다 (맥락이 바뀌면 답이 달라져야 해서)
_NO_CACHE_PREFIXES = ("가전제품 관련 질문을 입력해주세요", "가전 시장 관련 질문을 입력해주세요")


def _cacheable(report: str | None) -> bool:
    if not report or report in _NO_CACHE_REPORTS:
        return False
    return not report.strip().startswith(_NO_CACHE_PREFIXES)


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
    if not _cacheable(result.get("report")):
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
    history: list[dict] | None = None,
) -> dict:
    """context(직전 질문 조건)를 반영해 조건을 뽑고, 답변에 이번 조건을 실어 보낸다.
    프론트는 이 conditions를 저장했다가 다음 질문 때 context로 다시 보내서 대화가 이어진다."""
    from app.services.query_parser import parse_query
    cond = parse_query(query, context)
    result = await _answer(cond, query, rag, target, top_k, history)

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
    history: list[dict] | None = None,
) -> dict:
    """질문 처리 흐름 — LLM은 마지막 수단으로만 쓴다.

    ① 조건 추출(정규식·별칭·오타 보정) → ⓑ B2B 시장 분석(숫자 계산 + LLM 해석)
    → ② 캐시 → ③ 템플릿(추천·가격) → ④ LLM → ⑤ 캐시 저장
    ⑥ LLM이 전부 실패하면 만료된 캐시(예전 답변)라도 날짜 안내와 함께 보여준다
    """
    from app.services.product_finder import find_products
    from app.services.chat_templates import TEMPLATES, products_as_sources
    from app.services.market_answer import is_market_question, answer_market

    # ⓑ B2B 시장 분석 — 숫자는 코드가 계산하고 LLM은 해석만 한다
    if target == "b2b" and is_market_question(cond):
        import re as _re
        q_key = _re.sub(r"\s+", "", cond.normalized)[:120]
        mkey = f"chat:v3:b2b:market:{cond.category}:{cond.brand or '-'}:{q_key}"
        cached = await _cache_get(mkey)
        if cached and _cacheable(cached.get("report")):
            print(f"[Insight] answered_by=cache ({mkey})")
            return {**cached, "query": query, "target": target, "answered_by": "cache"}
        market = await answer_market(cond, query, rag, history)
        if market:
            result = {"query": query, "target": target, **market}
            if market["answered_by"] == "market":   # 해석까지 성공한 답만 저장
                await _cache_set(mkey, result)
            print(f"[Insight] answered_by={market['answered_by']} ({mkey})")
            return result
        # 시장 데이터를 못 모았으면 아래 일반 흐름으로 넘어간다

    cache_key = cond.cache_key(target)
    print(f"[Insight] 조건: cat={cond.category} brand={cond.brand} "
          f"price={cond.min_price}~{cond.max_price} house={cond.household} intent={cond.intent} "
          f"followup={cond.extras.get('followup', False)}")

    # ② 캐시 — 표현이 달라도 조건이 같으면 같은 답을 재사용
    cached = await _cache_get(cache_key)
    if cached and _cacheable(cached.get("report")):
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
    # 카테고리를 알면 실제 상품 데이터(가격·평점·후기 수)도 같이 넘긴다.
    # RAG 문서(뉴스·블로그)에는 특정 브랜드 정보가 없을 때가 많아서 "드리미는 어때?"에 답을 못 하던 문제 방지
    product_docs: list[str] = []
    if cond.category:
        try:
            import copy
            pcond = copy.deepcopy(cond)
            pcond.intent = "recommend"
            products, _ = await find_products(pcond, rag, limit=5)
            product_docs = [
                f"[상품] {p['title']} | 브랜드: {p.get('brand') or '-'} | 가격: {p['price']:,}원"
                + (f" | 평점: {p['score']:.1f}/5 (리뷰 {p.get('reviews', 0):,}개)" if p.get("score") else "")
                for p in products
            ]
        except Exception as e:
            print(f"[Insight] LLM용 상품 데이터 조회 실패: {e}")
    result = await _llm_answer(llm_query, rag, target, top_k, history, product_docs)
    result["query"] = query
    result["answered_by"] = "llm"

    # ⑥ LLM이 전부 실패했으면(안내 문구만 받았으면) 같은 질문의 예전 답변이라도 보여준다
    if result.get("report") in _NO_CACHE_REPORTS:
        stale = await _cache_get_stale(cache_key)
        if stale and _cacheable(stale.get("report")):
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
    history: list[dict] | None = None,
    product_docs: list[str] | None = None,
) -> dict:
    """RAG 검색 결과(+실제 상품 데이터)를 Groq LLM에 전달해 답변을 생성한다."""
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

    # 상품 데이터를 맨 앞에 둔다 (가격·평점은 문서보다 정확하다)
    chunks = list(product_docs or []) + list(chunks)

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
                # 최근 대화를 같이 넘겨야 "그럼 이 중엔?" "아까 그거" 같은 질문을 알아듣는다
                *_history_messages(history),
                {"role": "user", "content": f"질문: {query}\n\n{context}"},
            ],
            max_tokens=2500,          # 추론 모델은 생각 토큰도 여기 포함 → 여유 있게
            temperature=0.4,          # 질문마다 표현이 조금씩 달라지도록 살짝 올림
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
