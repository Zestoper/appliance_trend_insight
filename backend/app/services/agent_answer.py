"""하이브리드 답변의 'LLM 해석' 경로.

확실한 질문은 기존 키워드 경로(템플릿·캐시)가 LLM 없이 처리하고,
애매한 질문만 여기로 와서 3단계로 답한다.

  1단계 (LLM) 질문 해석 → JSON 계획: 카테고리·브랜드·가격대·정렬·필요한 데이터
  2단계 (코드) 계획대로 내 데이터 조회: 상품(다나와/RAG) · 시장 통계 · 후기/뉴스(RAG)
  3단계 (LLM) 조회한 데이터로 답변. 내 데이터에 없는 일반 개념만 일반 지식으로 답하고 표시한다.

LLM 호출이 실패하면 None을 돌려서 기존 키워드 경로가 이어받는다.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

from app.services.query_parser import QueryConditions, BRAND_ALIASES, _categories, normalize

# ── 확실한 질문 판별 ───────────────────────────────────────────────

_MARKET_EXPLICIT = r"시장|동향|트렌드|점유율|가격대|분포|추이|성장|진입|수요|검색량|관심도|현황|분석"


def is_confident(cond: QueryConditions, target: str) -> bool:
    """키워드 경로가 확실하게 처리할 수 있는 질문인가 (그렇다면 LLM 해석을 건너뛴다)."""
    if not cond.category or cond.extras.get("weak_followup"):
        return False
    if target == "b2b":
        return bool(re.search(_MARKET_EXPLICIT, re.sub(r"\s+", "", cond.normalized)))
    return cond.intent in ("recommend", "price")


# ── 1단계: 질문 해석 ──────────────────────────────────────────────

_PLAN_PROMPT = """\
당신은 가전제품 Q&A 서비스의 질문 해석기입니다. 사용자의 질문과 이전 대화를 보고 아래 JSON만 출력하세요.
설명·마크다운·코드블록 없이 JSON 한 개만 출력합니다.

{{
  "is_appliance": true/false,          // 가전제품·가전 브랜드·가전 시장과 관련 있으면 true (인사·잡담·무관한 질문은 false)
  "category": "카테고리 또는 null",     // 반드시 [카테고리 목록] 중 하나. 질문에 없으면 이전 대화 주제를 이어받는다
  "brand": "브랜드 또는 null",          // [브랜드 목록] 중 하나 (원하는 브랜드)
  "exclude_brand": "브랜드 또는 null",  // '삼성 빼고'처럼 빼달라는 브랜드
  "min_price": 정수(원) 또는 null,
  "max_price": 정수(원) 또는 null,     // '더 싼 거'면 직전에 보여준 최저가보다 작게, '더 비싼 거'면 min_price를 최고가보다 크게
  "household": 정수 또는 null,          // 가구 인원
  "sort": "relevance" | "popular" | "cheap" | "premium",
  "need_products": true/false,         // 특정 상품·브랜드·모델·가격·추천·비교·스펙 질문이면 true
  "need_market": true/false,           // 시장 규모·브랜드 비중·가격 추이·트렌드 질문이면 true
  "need_reviews": true/false,          // 후기·장단점·사용감·고장·소음 같은 평판 질문이면 true
  "search_query": "후기/뉴스 검색에 쓸 짧은 한국어 검색어"
}}

[카테고리 목록] {categories}
[브랜드 목록] {brands}
[이전 대화 조건] {context}
"""


def _parse_json(text: str) -> dict | None:
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # LLM이 // 주석을 따라 쓰는 경우 제거 후 재시도
        try:
            return json.loads(re.sub(r"//[^\n]*", "", m.group(0)))
        except json.JSONDecodeError:
            return None


def _to_int(v) -> int | None:
    try:
        n = int(float(str(v).replace(",", "")))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _plan_to_cond(plan: dict, query: str, base: QueryConditions) -> QueryConditions:
    """LLM 계획을 검증해서 QueryConditions로 바꾼다 (목록에 없는 카테고리·브랜드는 버린다)."""
    cats = _categories()
    cond = copy.deepcopy(base)
    cat = plan.get("category")
    cond.category = cat if cat in cats else base.category
    brand = plan.get("brand")
    cond.brand = brand if brand in BRAND_ALIASES else None
    ex = plan.get("exclude_brand")
    cond.extras["exclude_brand"] = ex if ex in BRAND_ALIASES else None
    cond.min_price = _to_int(plan.get("min_price"))
    cond.max_price = _to_int(plan.get("max_price"))
    if cond.min_price and cond.max_price and cond.min_price > cond.max_price:
        cond.min_price, cond.max_price = cond.max_price, cond.min_price
    cond.household = _to_int(plan.get("household"))
    sort = plan.get("sort")
    cond.extras["popular"] = sort == "popular"
    cond.extras["sort"] = sort if sort in ("relevance", "popular", "cheap", "premium") else "relevance"
    cond.intent = "recommend"
    return cond


async def _llm(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    from app.routers.b2b_utils import _groq_create
    res = await _groq_create(messages=messages, max_tokens=max_tokens,
                             temperature=temperature, reasoning_effort="low")
    return (res.choices[0].message.content or "").strip() or None


async def make_plan(query: str, context: dict | None, history: list[dict] | None) -> dict | None:
    from app.services.insight_service import _history_messages
    ctx = {k: v for k, v in (context or {}).items() if v not in (None, [], "")}
    if ctx.get("shown_titles"):
        ctx["shown_titles"] = ctx["shown_titles"][-5:]
    system = _PLAN_PROMPT.format(
        categories=", ".join(_categories()),
        brands=", ".join(BRAND_ALIASES.keys()),
        context=json.dumps(ctx, ensure_ascii=False) if ctx else "없음",
    )
    text = await _llm([
        {"role": "system", "content": system},
        *_history_messages(history),
        {"role": "user", "content": query},
    ], max_tokens=700, temperature=0)
    plan = _parse_json(text or "")
    if plan is None:
        print(f"[Agent] 계획 JSON 파싱 실패: {(text or '')[:200]}")
    return plan


# ── 2단계: 내 데이터 조회 ─────────────────────────────────────────

def _sort_products(products: list[dict], sort: str) -> list[dict]:
    if sort == "cheap":
        return sorted(products, key=lambda p: p["price"])
    if sort == "premium":
        return sorted(products, key=lambda p: -p["price"])
    if sort == "popular":
        return sorted(products, key=lambda p: -(p.get("reviews") or 0))
    return products


async def gather_data(plan: dict, cond: QueryConditions, rag) -> dict:
    from app.services.product_finder import find_products
    data: dict = {"products": [], "market": None, "reviews": []}

    if cond.category and (plan.get("need_products") or not (plan.get("need_market") or plan.get("need_reviews"))):
        try:
            products, nearest = await find_products(cond, rag, limit=8)
            data["products"] = _sort_products(products, cond.extras.get("sort", "relevance"))[:6]
            data["nearest"] = nearest
        except Exception as e:
            print(f"[Agent] 상품 조회 실패: {e}")

    if cond.category and plan.get("need_market"):
        try:
            from app.services.market_answer import build_market_stats
            data["market"] = await build_market_stats(cond.category, rag)
        except Exception as e:
            print(f"[Agent] 시장 통계 조회 실패: {e}")

    if rag is not None and (plan.get("need_reviews") or plan.get("need_products")):
        try:
            q = (plan.get("search_query") or cond.raw).strip()
            where = {"product": cond.category} if cond.category else None
            chunks = await rag.query(q, n_results=5, where=where)
            data["reviews"] = [c for c in chunks if not c.startswith("[쇼핑]")][:5]
        except Exception as e:
            print(f"[Agent] 후기 검색 실패: {e}")
    return data


def _product_line(p: dict) -> str:
    line = f"- {p['title']} | 브랜드: {p.get('brand') or '-'} | 가격: {p['price']:,}원"
    if p.get("score"):
        line += f" | 평점: {p['score']:.1f}/5 (후기 {p.get('reviews', 0):,}개)"
    return line


def data_to_text(data: dict) -> str:
    from app.services.market_answer import stats_for_llm
    parts = []
    if data.get("products"):
        head = "[상품 데이터] (오늘 기준 실제 판매 중인 제품"
        head += " · 조건에 맞는 게 없어 가장 가까운 가격대)" if data.get("nearest") else ")"
        parts.append(head + "\n" + "\n".join(_product_line(p) for p in data["products"]))
    if data.get("market"):
        parts.append("[시장 데이터]\n" + stats_for_llm(data["market"]))
    if data.get("reviews"):
        parts.append("[후기·뉴스]\n" + "\n".join(f"- {c[:200]}" for c in data["reviews"]))
    return "\n\n".join(parts) if parts else "(조회된 데이터 없음)"


# ── 3단계: 답변 ───────────────────────────────────────────────────

_ANSWER_RULES = """
[답변 규칙]
1. 사용자가 방금 물어본 것에 바로 답하세요. 형식을 맞추려고 묻지 않은 항목을 채우지 마세요.
2. [상품 데이터]·[시장 데이터]·[후기·뉴스]에 있는 내용은 그 데이터를 근거로 구체적으로 답하세요 (모델명·가격·평점·후기 수).
   금액은 데이터에 적힌 표기 그대로 쓰세요.
3. 데이터에 없는 일반 개념·고르는 요령·기술 설명은 일반 지식으로 답해도 됩니다. 그 문장 끝에 "(일반 정보)"를 붙이세요.
4. 가격·평점·재고·출시일·점유율처럼 바뀌는 숫자는 데이터에 있는 것만 쓰세요. 없으면 "자료에서 확인되지 않아요"라고 하세요.
5. 3~8줄로 자연스럽게 답하고 필요할 때만 목록을 쓰세요. 마크다운은 ##, ###, -, 1. 와 **굵게**만 쓰세요.
6. 출처 번호는 쓰지 마세요. 반드시 한국어로만 답하세요.
"""

_ANSWER_ROLE = {
    "b2c": "당신은 가전제품 구매 상담을 해주는 친절한 AI 상담원입니다. 일반 소비자가 이해하기 쉬운 구어체로 답하세요.",
    "b2b": "당신은 가전 시장을 분석하는 B2B 전략 컨설턴트입니다. 기획자·MD 관점의 인사이트와 시사점 위주로 답하세요.",
}


def _allowed_amounts(data: dict) -> list[float]:
    vals = [p["price"] / 10_000 for p in data.get("products") or []]
    if data.get("market"):
        from app.services.market_answer import _allowed_amounts as market_amounts
        vals += market_amounts(data["market"])
    return vals


_MAN_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*만\s*원")


def _bad_amounts(text: str, data: dict) -> list[str]:
    allowed = _allowed_amounts(data)
    if not allowed:
        return []
    bad = []
    for m in _MAN_RE.finditer(text):
        if text[m.end():m.end() + 1] == "대" or text[max(0, m.start() - 1):m.start()] in ("~", "-"):
            continue
        v = float(m.group(1).replace(",", ""))
        if not any(abs(v - a) <= max(1.0, a * 0.03) for a in allowed):
            bad.append(m.group(0))
    return bad


async def write_answer(query: str, target: str, data: dict, history: list[dict] | None) -> str | None:
    from app.services.insight_service import _history_messages
    messages = [
        {"role": "system", "content": _ANSWER_ROLE.get(target, _ANSWER_ROLE["b2c"]) + _ANSWER_RULES},
        *_history_messages(history),
        {"role": "user", "content": f"질문: {query}\n\n{data_to_text(data)}"},
    ]
    text = await _llm(messages, max_tokens=2000, temperature=0.4)
    if not text:
        return None
    bad = _bad_amounts(text, data)
    if bad:
        print(f"[Agent] 데이터에 없는 금액 {bad} → 재작성")
        text2 = await _llm(messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": f"{', '.join(bad)}은(는) 데이터에 없는 금액입니다. 금액은 데이터 표기 그대로만 써서 다시 답하세요."},
        ], max_tokens=2000, temperature=0.2)
        if text2 and not _bad_amounts(text2, data):
            return text2
        # 그래도 틀리면 금액 문장을 빼는 대신 경고 없이 원문을 쓰지 않는다
        return None
    return text


# ── 전체 흐름 ─────────────────────────────────────────────────────

_GREETING = ("안녕하세요! 가전제품 추천·가격 비교·후기·시장 분석을 도와드려요.\n\n"
             "- 예: 혼자 사는데 40만원대 에어컨 추천\n- 예: 드리미 로봇청소기 어때?\n- 예: 공기청정기 시장 동향")


async def answer_agent(query: str, base: QueryConditions, rag, target: str,
                       context: dict | None, history: list[dict] | None) -> dict | None:
    """LLM 해석 경로. 실패하면 None (기존 키워드 경로가 이어받는다)."""
    from app.services.insight_service import _cache_get, _cache_set, _cacheable

    try:
        plan = await make_plan(query, context, history)
    except Exception as e:
        print(f"[Agent] 해석 단계 실패 → 키워드 경로로: {e}")
        return None
    if not plan:
        return None

    if plan.get("is_appliance") is False and not base.category:
        return {"report": _GREETING, "sources": [], "answered_by": "agent_greeting",
                "_cond": base}

    cond = _plan_to_cond(plan, query, base)

    # 캐시 키: 해석된 조건 + 질문 문장 + 직전 상품 (같은 질문이라도 맥락이 다르면 다른 답)
    key_src = json.dumps({
        "t": target, "q": re.sub(r"\s+", "", normalize(query))[:150],
        "c": cond.category, "b": cond.brand, "lo": cond.min_price, "hi": cond.max_price,
        "h": cond.household, "s": cond.extras.get("sort"),
        "shown": (context or {}).get("shown_titles", [])[-3:],
    }, ensure_ascii=False, sort_keys=True)
    cache_key = "chat:v4:agent:" + hashlib.md5(key_src.encode("utf-8")).hexdigest()
    cached = await _cache_get(cache_key)
    if cached and _cacheable(cached.get("report")):
        return {**cached, "answered_by": "cache", "_cond": cond}

    data = await gather_data(plan, cond, rag)
    try:
        report = await write_answer(query, target, data, history)
    except Exception as e:
        print(f"[Agent] 답변 단계 실패: {e}")
        report = None
    if not report:
        return None

    products = data.get("products") or []
    sources = [{"rank": i, "text": f"[상품] {p['title']} | {p['price']:,}원"} for i, p in enumerate(products, 1)]
    sources += [{"rank": len(sources) + i, "text": c} for i, c in enumerate(data.get("reviews") or [], 1)]
    result = {"report": report, "sources": sources, "answered_by": "agent"}
    if products:
        prices = [p["price"] for p in products]
        result["_shown"] = {"shown_min": min(prices), "shown_max": max(prices),
                            "shown_titles": [p["title"] for p in products][:6]}
    await _cache_set(cache_key, {k: v for k, v in result.items() if k != "_cond"})
    print(f"[Agent] answered_by=agent plan={json.dumps(plan, ensure_ascii=False)[:300]}")
    return {**result, "_cond": cond}
