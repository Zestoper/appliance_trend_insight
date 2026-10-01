"""LLM 없이 상품 데이터를 정해진 틀에 채워 답변을 만드는 템플릿.

Chat.jsx의 renderMarkdown이 지원하는 문법(##, ###, - , 1. )만 사용한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.query_parser import QueryConditions

_KST = timezone(timedelta(hours=9))


def _won(v: int) -> str:
    if v >= 10_000 and v % 10_000 == 0:
        return f"{v // 10_000:,}만원"
    return f"{v:,}원"


def _range_text(cond: QueryConditions) -> str | None:
    lo, hi = cond.min_price, cond.max_price
    if lo and hi:
        return f"{_won(lo)} ~ {_won(hi)}"
    if hi:
        return f"{_won(hi)} 이하"
    if lo:
        return f"{_won(lo)} 이상"
    return None


def _household_text(n: int | None) -> str:
    if n == 1:
        return "1인 가구용 "
    if n == 2:
        return "2인 가구용 "
    if n and n >= 3:
        return f"{n}인 이상 가족용 "
    return ""


def _josa(word: str, with_batchim: str, without: str) -> str:
    """받침 유무에 맞는 조사 (에어컨은 / 냉장고는)"""
    last = word[-1] if word else ""
    code = ord(last) - 0xAC00
    if 0 <= code < 11172:
        return with_batchim if code % 28 else without
    return without


def _condition_summary(cond: QueryConditions) -> str:
    parts = []
    if cond.household:
        parts.append(_household_text(cond.household).strip().replace("용", ""))
    rt = _range_text(cond)
    if rt:
        parts.append(rt)
    return " · ".join(parts)


def _product_block(i: int, p: dict) -> list[str]:
    lines = [f"### {i}. {p['title']}", f"- 가격: {p['price']:,}원"]
    if p.get("brand"):
        lines.append(f"- 브랜드: {p['brand']}")
    if p.get("score"):
        reviews = f" (리뷰 {p['reviews']:,}개)" if p.get("reviews") else ""
        lines.append(f"- 평점: {p['score']:.1f} / 5{reviews}")
    lines.append("")
    return lines


def _footer(cond: QueryConditions, extra: list[str]) -> list[str]:
    today = datetime.now(_KST).strftime("%-m월 %-d일")
    lines = ["### 💡 참고", f"- 가격은 {today} 기준 다나와 최저가라 실제 판매가와 다를 수 있어요."]
    if cond.category_corrected:
        lines.append(f"- 입력하신 내용을 '{cond.category}'(으)로 이해하고 찾았어요.")
    lines += extra
    return lines


def render_recommend(cond: QueryConditions, products: list[dict], nearest: bool) -> str:
    brand = f"{cond.brand} " if cond.brand else ""
    title = f"## 🛒 {_household_text(cond.household)}{brand}{cond.category} 추천"
    summary = _condition_summary(cond)
    lines = [title, ""]
    relative = cond.extras.get("relative")
    if relative == "cheaper" and not nearest:
        lines.append(f"앞에서 보여드린 제품보다 저렴한 {cond.category}{_josa(cond.category, '이에요', '예요')}.")
    elif relative == "cheaper":
        lines.append("앞에서 보여드린 제품보다 저렴한 건 찾지 못해서 가격이 가장 가까운 다른 제품을 골랐어요.")
    elif relative == "pricier" and not nearest:
        lines.append(f"앞에서 보여드린 제품보다 한 단계 위 가격대의 {cond.category}{_josa(cond.category, '이에요', '예요')}.")
    elif relative == "more" and not nearest:
        lines.append("앞에서 보여드린 제품 말고 다른 제품을 골라봤어요.")
    elif relative == "more":
        lines.append("그 가격대에는 더 보여드릴 제품이 없어서 가격이 가장 가까운 다른 제품을 골랐어요.")
    elif nearest:
        lines.append(f"{_range_text(cond) or '말씀하신 조건'}에 맞는 {brand}{cond.category}"
                     f"{_josa(cond.category, '은', '는')} 찾지 못해서 가장 가까운 가격의 제품을 골랐어요.")
    elif summary:
        lines.append(f"{summary} 조건으로 인기 있는 제품을 골라봤어요.")
    else:
        lines.append(f"리뷰와 평점이 좋은 {brand}{cond.category}{_josa(cond.category, '을', '를')} 골라봤어요.")
    lines.append("")
    for i, p in enumerate(products, 1):
        lines += _product_block(i, p)
    extra = []
    if not (cond.min_price or cond.max_price):
        extra.append("- 예산을 알려주시면 더 정확하게 골라드릴게요. (예: 40만원 이하)")
    lines += _footer(cond, extra)
    return "\n".join(lines)


def render_price(cond: QueryConditions, products: list[dict], nearest: bool) -> str:
    brand = f"{cond.brand} " if cond.brand else ""
    lines = [f"## 💰 {brand}{cond.category} 가격 정보", ""]
    if products:
        prices = [p["price"] for p in products]
        lines.append(f"인기 제품 기준으로 {_won(min(prices))}부터 {_won(max(prices))}까지 있어요.")
        lines.append("")
    for i, p in enumerate(products, 1):
        lines += _product_block(i, p)
    lines += _footer(cond, ["- 원하는 예산을 함께 알려주시면 그 가격대 제품을 추천해 드릴게요."])
    return "\n".join(lines)


TEMPLATES = {
    "recommend": render_recommend,
    "price": render_price,
}


def products_as_sources(products: list[dict]) -> list[dict]:
    return [{
        "rank": i,
        "text": f"[쇼핑] {p['title']} | 가격: {p['price']:,}원"
                + (f" | 평점: {p['score']:.1f}" if p.get("score") else ""),
    } for i, p in enumerate(products, 1)]
