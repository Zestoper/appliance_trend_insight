"""B2B 시장 분석 답변.

숫자는 코드가 DB·수집 데이터로 먼저 계산하고(LLM 없음), LLM은 그 숫자를 '해석'만 한다.
그래서 LLM이 숫자를 지어낼 틈이 없고, LLM이 실패해도 숫자 부분은 그대로 보여줄 수 있다.

사용 데이터
  - 상품 분포·브랜드 : RAG 쇼핑 문서(metadata price/brand) → 없으면 다나와 실시간 검색
  - 가격 추이        : price_history 테이블 (카테고리별 일일 스냅샷)
  - 검색 관심도      : 네이버 데이터랩 (최근 30일)
"""
from __future__ import annotations

import json
import re
import statistics
from datetime import date, datetime, timedelta, timezone

from app.services.query_parser import QueryConditions, BRAND_ALIASES

_KST = timezone(timedelta(hours=9))
_STATS_TTL_HOURS = 6

# B2B 모드에서 시장 분석으로 보낼 질문 (그 외 '전력효율은?' 같은 구체 질문은 대화형 LLM)
_MARKET_KW = (r"시장|동향|트렌드|점유율|브랜드|경쟁|가격대|분포|추이|성장|진입|기회|수요|검색량|"
              r"관심도|인기|판매|라인업|포지셔닝|타겟|세그먼트|전망|분석|현황|어때|어떰")


def is_market_question(cond: QueryConditions) -> bool:
    if not cond.category:
        return False
    if re.search(_MARKET_KW, re.sub(r"\s+", "", cond.normalized)):
        return True
    # 리뷰·성능 질문은 대화형 LLM이 낫고, 나머지(추천·가격·비교·시기·의도 없음)는 시장 데이터로 답한다
    return cond.intent != "review"


# ── 숫자 계산 ─────────────────────────────────────────────────────

def _brand_name(raw: str, title: str) -> str:
    hay = f"{raw} {title}".lower()
    for brand, aliases in BRAND_ALIASES.items():
        if any(a in hay for a in aliases):
            return brand
    raw = (raw or "").replace("전자", "").strip()
    return raw or "기타"


def _nice_step(median: int) -> int:
    if median >= 1_000_000:
        return 100_000
    if median >= 300_000:
        return 50_000
    return 10_000


def _round_to(v: float, step: int) -> int:
    return int(round(v / step) * step) or step


def _won(v: int) -> str:
    if v >= 10_000:
        man = v / 10_000
        return f"{man:,.0f}만원" if man >= 10 or man == int(man) else f"{man:,.1f}만원"
    return f"{v:,}원"


def _pct(new: float, old: float) -> float | None:
    if not old:
        return None
    return round((new - old) / old * 100, 1)


def _signed(p: float | None) -> str:
    return "데이터 없음" if p is None else f"{p:+.1f}%"


async def _collect_products(category: str, rag) -> list[dict]:
    from app.services.product_finder import _from_rag, _from_danawa
    cond = QueryConditions(raw=category, normalized=category, category=category)
    items: list[dict] = []
    if rag is not None:
        items = await _from_rag(rag, cond, 100)
    if len(items) < 10:
        items = await _from_danawa(cond)
    items = [p for p in items if p.get("price", 0) > 0]
    if len(items) < 3:
        return items
    med = statistics.median(p["price"] for p in items)
    # 부품·액세서리·초고가 이상치 제거 (중앙값 30% 미만 · 400% 초과)
    return [p for p in items if med * 0.3 <= p["price"] <= med * 4]


def _distribution(items: list[dict]) -> dict:
    prices = sorted(p["price"] for p in items)
    med = int(statistics.median(prices))
    step = _nice_step(med)
    q1 = _round_to(prices[len(prices) // 3], step)
    q2 = _round_to(prices[len(prices) * 2 // 3], step)
    if q2 <= q1:
        q2 = q1 + step
    tiers = [
        (f"{_won(q1)} 미만", [p for p in items if p["price"] < q1]),
        (f"{_won(q1)} ~ {_won(q2)}", [p for p in items if q1 <= p["price"] < q2]),
        (f"{_won(q2)} 이상", [p for p in items if p["price"] >= q2]),
    ]
    n = len(items)
    return {
        "n": n,
        "median": med,
        "avg": int(sum(prices) / n),
        "tiers": [{
            "label": label,
            "count": len(ps),
            "share": round(len(ps) / n * 100),
            "avg_score": round(sum(p.get("score") or 0 for p in ps) / len(ps), 2) if ps else 0,
        } for label, ps in tiers],
    }


def _brands(items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for p in items:
        groups.setdefault(_brand_name(p.get("brand", ""), p.get("title", "")), []).append(p)
    n = len(items)
    out = [{
        "brand": b,
        "count": len(ps),
        "share": round(len(ps) / n * 100),
        "avg": int(sum(p["price"] for p in ps) / len(ps)),
        "reviews": sum(p.get("reviews") or 0 for p in ps),
    } for b, ps in groups.items()]
    out.sort(key=lambda x: (-x["count"], -x["reviews"]))
    return out[:6]


async def _price_trend(category: str) -> dict | None:
    from app.database import fetchall
    try:
        rows = await fetchall(
            "SELECT snapshot_date, avg_price, median_price FROM price_history "
            "WHERE category = %s ORDER BY snapshot_date DESC LIMIT 120",
            (category,),
        )
    except Exception as e:
        print(f"[Market] price_history 조회 실패: {e}")
        return None
    if not rows:
        return None
    latest = rows[0]
    latest_date = latest["snapshot_date"]

    def near(days: int):
        target = latest_date - timedelta(days=days)
        cands = [r for r in rows if r["snapshot_date"] <= target]
        return cands[0] if cands else None

    r30, r90 = near(30), near(90)
    return {
        "latest_date": str(latest_date),
        "latest_avg": int(latest["avg_price"] or 0),
        "chg_30": _pct(latest["avg_price"], r30["avg_price"]) if r30 else None,
        "chg_90": _pct(latest["avg_price"], r90["avg_price"]) if r90 else None,
        "days": len(rows),
    }


async def _search_trend(category: str) -> dict | None:
    try:
        from app.routers.naver import get_datalab
        data = (await get_datalab(category)).get("data") or []
    except Exception as e:
        print(f"[Market] 데이터랩 조회 실패: {e}")
        return None
    if len(data) < 14:
        return None
    ratios = [float(d.get("ratio") or 0) for d in data]
    recent, prev = ratios[-7:], ratios[-14:-7]
    peak = max(data, key=lambda d: float(d.get("ratio") or 0))
    return {
        "chg_7d": _pct(sum(recent) / 7, sum(prev) / 7),
        "peak_date": peak.get("period", ""),
    }


async def build_market_stats(category: str, rag) -> dict | None:
    """시장 숫자를 계산한다 (6시간 캐시 — 다나와 수집이 무거워서)."""
    from app.services.naver_cache import get_db_cache, set_db_cache
    key = f"market_stats:v1:{category}"
    try:
        cached = await get_db_cache(key)
        if cached:
            return cached
    except Exception:
        pass

    items = await _collect_products(category, rag)
    if len(items) < 5:
        return None
    stats = {
        "category": category,
        "date": datetime.now(_KST).strftime("%Y-%m-%d"),
        "distribution": _distribution(items),
        "brands": _brands(items),
        "price_trend": await _price_trend(category),
        "search_trend": await _search_trend(category),
    }
    try:
        await set_db_cache(key, stats, ttl_hours=_STATS_TTL_HOURS)
    except Exception:
        pass
    return stats


# ── 표시 (Chat.jsx renderMarkdown 문법만 사용) ─────────────────────

def _bar(share: int) -> str:
    return "█" * max(1, round(share / 5)) if share else ""


def render_stats(stats: dict, cond: QueryConditions) -> str:
    cat = stats["category"]
    d = stats["distribution"]
    lines = [f"## 📊 {cat} 시장 분석", "",
             f"상품 {d['n']}개 · 가격 이력 · 네이버 검색 트렌드 기준 ({stats['date']})", ""]

    lines.append("### 💰 가격대별 상품 분포")
    for t in d["tiers"]:
        score = f" · 평균 평점 {t['avg_score']:.1f}" if t["avg_score"] else ""
        lines.append(f"- {t['label']}: {t['count']}개 ({t['share']}%) {_bar(t['share'])}{score}")
    lines.append(f"- 중앙값 {_won(d['median'])} · 평균 {_won(d['avg'])}")
    lines.append("")

    lines.append("### 🏷️ 브랜드별 현황")
    for b in stats["brands"]:
        mark = "👉 " if cond.brand and b["brand"] == cond.brand else ""
        gap = _pct(b["avg"], d["avg"])
        gap_txt = f" (시장 평균 대비 {gap:+.0f}%)" if gap is not None else ""
        lines.append(f"- {mark}{b['brand']}: {b['count']}개 · 비중 {b['share']}% · 평균 {_won(b['avg'])}{gap_txt}")
    if cond.brand and not any(b["brand"] == cond.brand for b in stats["brands"]):
        lines.append(f"- {cond.brand}: 수집된 상위 상품에서 비중이 낮아 목록에 없어요")
    lines.append("")

    lines.append("### 📈 평균가 추이")
    pt = stats.get("price_trend")
    if pt and pt.get("latest_avg"):
        lines.append(f"- 최근 평균가 {_won(pt['latest_avg'])} ({pt['latest_date']} 기준)")
        lines.append(f"- 30일 전 대비 {_signed(pt['chg_30'])} · 90일 전 대비 {_signed(pt['chg_90'])}")
    else:
        lines.append("- 가격 이력 데이터가 아직 충분히 쌓이지 않았어요")
    lines.append("")

    lines.append("### 🔍 검색 관심도 (네이버 데이터랩)")
    st = stats.get("search_trend")
    if st:
        lines.append(f"- 최근 7일 검색량 이전 7일 대비 {_signed(st['chg_7d'])}")
        if st.get("peak_date"):
            lines.append(f"- 최근 30일 중 관심이 가장 높았던 날: {st['peak_date']}")
    else:
        lines.append("- 검색 트렌드 데이터를 가져오지 못했어요")
    return "\n".join(lines)


def stats_for_llm(stats: dict) -> str:
    """LLM에게 넘길 숫자 요약. 화면과 똑같은 '만원' 표기로 넘긴다.
    (원 단위 '1,087,500원'을 넘기면 LLM이 '1,087만원'처럼 단위를 잘못 바꾸는 일이 생긴다)"""
    d = stats["distribution"]
    parts = [f"카테고리: {stats['category']} (수집 상품 {d['n']}개, 중앙값 {_won(d['median'])}, 평균 {_won(d['avg'])})"]
    parts.append("가격대 분포: " + " / ".join(f"{t['label']} {t['share']}%" for t in d["tiers"]))
    parts.append("브랜드: " + " / ".join(f"{b['brand']} 비중 {b['share']}% 평균 {_won(b['avg'])}" for b in stats["brands"]))
    pt = stats.get("price_trend")
    if pt and pt.get("latest_avg"):
        parts.append(f"평균가 추이: 최근 {_won(pt['latest_avg'])}, 30일 대비 {_signed(pt['chg_30'])}, 90일 대비 {_signed(pt['chg_90'])}")
    st = stats.get("search_trend")
    if st:
        parts.append(f"검색 관심도: 최근 7일 이전 7일 대비 {_signed(st['chg_7d'])}")
    return "\n".join(parts)


# ── LLM이 쓴 금액 검증 ────────────────────────────────────────────

_MAN_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*만\s*원")


def _allowed_amounts(stats: dict) -> list[float]:
    """데이터에 실제로 있는 금액들 (만원 단위)"""
    d = stats["distribution"]
    vals = [d["median"], d["avg"]] + [b["avg"] for b in stats["brands"]]
    pt = stats.get("price_trend")
    if pt and pt.get("latest_avg"):
        vals.append(pt["latest_avg"])
    # 가격대 경계값 (예: '80만원 미만')
    for t in d["tiers"]:
        vals += [float(x.replace(",", "")) * 10_000 for x in _MAN_RE.findall(t["label"])]
    return [v / 10_000 for v in vals if v]


def invalid_amounts(text: str, stats: dict) -> list[str]:
    """해석문에 나온 'N만원' 중 데이터에 없는 금액 목록 (±3% 또는 ±1만원까지는 허용)"""
    allowed = _allowed_amounts(stats)
    bad = []
    for m in _MAN_RE.finditer(text):
        raw = m.group(1)
        # '100만원대' · '50~100만원' 같은 가격대 표현은 제안일 뿐 데이터 인용이 아니라서 검사하지 않는다
        if text[m.end():m.end() + 1] == "대" or text[max(0, m.start() - 1):m.start()] in ("~", "-"):
            continue
        v = float(raw.replace(",", ""))
        if not any(abs(v - a) <= max(1.0, a * 0.03) for a in allowed):
            bad.append(f"{raw}만원")
    return bad


_INTERPRET_PROMPT = """\
당신은 가전 시장 B2B 전략 컨설턴트입니다. 반드시 한국어로만 답하세요.
아래 [시장 데이터]의 숫자만 근거로 사용자의 질문에 답하세요.
- 금액은 [시장 데이터]에 적힌 표기(예: 109만원) 그대로 옮겨 쓰세요. 단위를 바꾸거나 다시 계산하지 마세요.
- 데이터에 없는 숫자(점유율·판매량·성장률·금액 등)는 절대 새로 만들지 마세요.
- 3~5줄로 핵심 해석을 쓰고, 마지막에 '💡 시사점' 한 줄을 붙이세요.
- 표나 목록을 다시 나열하지 마세요 (숫자는 이미 화면에 표로 보여주고 있습니다).
- 데이터가 '데이터 없음'인 항목은 판단하지 말고 넘어가세요.
"""


async def _ask(messages: list[dict]) -> str | None:
    from app.routers.b2b_utils import _groq_create
    res = await _groq_create(messages=messages, max_tokens=1500, temperature=0.2, reasoning_effort="low")
    return (res.choices[0].message.content or "").strip() or None


async def interpret(stats: dict, query: str, history: list[dict] | None) -> str | None:
    """숫자 해석을 만들고, 데이터에 없는 금액이 나오면 한 번 고쳐 쓰게 한다. 그래도 틀리면 버린다."""
    from app.services.insight_service import _history_messages
    messages = [
        {"role": "system", "content": _INTERPRET_PROMPT},
        *_history_messages(history),
        {"role": "user", "content": f"질문: {query}\n\n[시장 데이터]\n{stats_for_llm(stats)}"},
    ]
    try:
        text = await _ask(messages)
        if not text:
            return None
        bad = invalid_amounts(text, stats)
        if not bad:
            return text
        print(f"[Market] 해석에 데이터에 없는 금액 {bad} → 재작성 요청")
        retry = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": f"{', '.join(bad)}은(는) [시장 데이터]에 없는 금액입니다. "
                                        "금액은 데이터에 적힌 표기 그대로만 써서 다시 작성하세요."},
        ]
        text2 = await _ask(retry)
        if text2 and not invalid_amounts(text2, stats):
            return text2
        print("[Market] 재작성 후에도 금액 불일치 → 해석 생략")
        return None
    except Exception as e:
        print(f"[Market] 해석 생성 실패: {e}")
        return None


async def answer_market(cond: QueryConditions, query: str, rag, history: list[dict] | None) -> dict | None:
    stats = await build_market_stats(cond.category, rag)
    if not stats:
        return None
    report = render_stats(stats, cond)
    comment = await interpret(stats, query, history)
    if comment:
        report += "\n\n### 🧠 AI 해석\n" + comment
    else:
        report += "\n\n- AI 해석은 지금 생성하지 못했어요. 위 숫자는 수집 데이터 기준이라 그대로 참고하셔도 돼요."
    return {
        "report": report,
        "sources": [{"rank": 1, "text": f"[시장 데이터] {stats_for_llm(stats)}"}],
        "answered_by": "market" if comment else "market_stats_only",
    }
