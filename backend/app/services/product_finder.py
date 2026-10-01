"""조건(QueryConditions)에 맞는 실제 상품 찾기.

1순위: RAG(rag_documents)의 쇼핑 문서 — metadata의 price/brand로 SQL 필터 (숫자 비교는 벡터 검색이 못 한다)
2순위: 다나와 실시간 검색 (RAG에 해당 카테고리 상품이 없거나 아직 재시딩 전일 때)
3순위: 범위 안에 상품이 없으면 가격이 가장 가까운 상품 (nearest=True)
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from app.services.query_parser import QueryConditions

if TYPE_CHECKING:
    from app.rag_service import RAGService

# 가구 수에 따라 우선 보여줄 상품 키워드 (상품명에 들어있으면 가산점)
_SMALL_KW = r"소형|미니|슬림|1인|원룸|벽걸이|컴팩트|미니멀|소용량|\b[1-4]인용"
_LARGE_KW = r"대용량|스탠드|투인원|2in1|홈멀티|패밀리|[6-9]인용|10인용|대형"


def _popularity(p: dict) -> float:
    return (p.get("score") or 0) * math.log((p.get("reviews") or 0) + 2)


def _rerank(products: list[dict], cond: QueryConditions) -> list[dict]:
    def score(p: dict) -> float:
        s = _popularity(p)
        title = p.get("title", "")
        if cond.household == 1:
            s += 3 if re.search(_SMALL_KW, title) else 0
            s -= 3 if re.search(_LARGE_KW, title) else 0
        elif cond.household and cond.household >= 3:
            s += 3 if re.search(_LARGE_KW, title) else 0
        return s
    return sorted(products, key=score, reverse=True)


def _in_range(price: int, cond: QueryConditions) -> bool:
    if price <= 0:
        return False
    if cond.min_price and price < cond.min_price:
        return False
    if cond.max_price and price > cond.max_price:
        return False
    return True


# 본품이 아닌 부속품·설치 키트·소모품 (예: '드림스테이 드리미 직배수 리폼 키트')
_ACCESSORY_RE = re.compile(r"리폼|키트|부품|필터|소모품|호환|거치대|교체용|브러시|걸레패드|먼지봉투|케이블|리모컨|커버|받침|선반")


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    """다나와 응답에 섞여 오는 검색어 강조 태그(<b>로보락</b>) 제거"""
    return re.sub(r"\s+", " ", _TAG_RE.sub("", text or "")).strip()


# 두 제품을 묶어 파는 세트 상품 (예: '로보락F25 Ultra +로봇청소기Q8 Max Pro Plus')
_BUNDLE_RE = re.compile(r"\+|세트|패키지|1\+1|묶음|번들")


def _is_bundle(p: dict) -> bool:
    return bool(_BUNDLE_RE.search(p.get("title", "")))


def _is_accessory(p: dict) -> bool:
    return bool(_ACCESSORY_RE.search(p.get("title", "")))


def _brand_ok(p: dict, cond: QueryConditions) -> bool:
    from app.services.query_parser import BRAND_ALIASES
    # 브랜드 칸이 있으면 브랜드 칸으로만 판단한다. 제목으로 보면 '드림스테이 드리미 키트'처럼
    # 다른 회사의 호환 부품이 '드리미' 상품으로 잘못 잡힌다. 브랜드 칸이 비었을 때만 제목을 본다.
    hay = (p.get("brand") or p.get("title", "")).lower()
    excluded = cond.extras.get("exclude_brand")
    if excluded and any(a in hay for a in BRAND_ALIASES.get(excluded, [excluded.lower()])):
        return False   # '삼성 빼고'
    if not cond.brand:
        return True
    return any(a in hay for a in BRAND_ALIASES.get(cond.brand, [cond.brand.lower()]))


async def _from_rag(rag: "RAGService", cond: QueryConditions, limit: int) -> list[dict]:
    from app.database import fetchall
    conds = [
        "metadata->>'source' = 'shop'",
        "metadata->>'product' = %s",
        "(metadata->>'price')::int > 0",
    ]
    params: list = [cond.category]
    if cond.min_price:
        conds.append("(metadata->>'price')::int >= %s")
        params.append(cond.min_price)
    if cond.max_price:
        conds.append("(metadata->>'price')::int <= %s")
        params.append(cond.max_price)
    params.append(limit)
    try:
        rows = await fetchall(
            f"SELECT text, metadata FROM rag_documents WHERE {' AND '.join(conds)} "
            "ORDER BY COALESCE((metadata->>'score')::float, 0) DESC LIMIT %s",
            params,
        )
    except Exception as e:
        print(f"[ProductFinder] RAG 상품 조회 실패: {e}")
        return []
    import json
    out = []
    for r in rows:
        meta = r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"])
        out.append({
            "title": _clean(meta.get("title") or r["text"]),
            "brand": _clean(meta.get("brand", "")),
            "price": int(meta.get("price") or 0),
            "score": float(meta.get("score") or 0),
            "reviews": int(meta.get("reviews") or 0),
            "link": meta.get("link", ""),
            "source": "rag",
        })
    return out


async def _from_danawa(cond: QueryConditions) -> list[dict]:
    from app.config import CATEGORY_RULES
    from app.services.danawa_search import danawa_search_products
    query = f"{cond.brand} {cond.category}" if cond.brand else cond.category
    try:
        res = await danawa_search_products(
            query=query, page=1, display=40, sort="sim",
            category=cond.category if cond.category in CATEGORY_RULES else None,
        )
    except Exception as e:
        print(f"[ProductFinder] 다나와 검색 실패: {e}")
        return []
    return [{
        "title": _clean(it.get("title", "")),
        "brand": _clean(it.get("brand", "")),
        "price": int(it.get("price") or 0),
        "score": float(it.get("reviewScore") or 0),
        "reviews": int(it.get("reviewCount") or 0),
        "link": it.get("link", ""),
        "source": "danawa",
    } for it in res.get("items", []) if it.get("price")]


async def find_products(
    cond: QueryConditions,
    rag: "RAGService | None",
    limit: int = 3,
) -> tuple[list[dict], bool]:
    """(상품 목록, nearest 여부) 반환. nearest=True면 범위 안에 없어서 가장 가까운 걸 보여주는 것."""
    if not cond.category:
        return [], False

    exclude = set(cond.extras.get("exclude") or [])

    def ok(p: dict) -> bool:
        return _brand_ok(p, cond) and p["title"] not in exclude and not _is_accessory(p)

    candidates: list[dict] = []
    if rag is not None:
        candidates = [p for p in await _from_rag(rag, cond, 40) if ok(p)]

    live: list[dict] = []
    if len(candidates) < limit:
        live = [p for p in await _from_danawa(cond) if ok(p)]
        seen = {p["title"] for p in candidates}
        candidates += [p for p in live if _in_range(p["price"], cond) and p["title"] not in seen]

    in_range = [p for p in candidates if _in_range(p["price"], cond)]
    # 세트 상품은 단품이 충분하면 빼고, 부족하면 뒤로 보낸다 (가격·비교가 헷갈려서)
    singles = [p for p in in_range if not _is_bundle(p)]
    if len(singles) >= limit:
        in_range = singles
    else:
        in_range = singles + [p for p in in_range if _is_bundle(p)]
    if cond.intent == "price" and not (cond.min_price or cond.max_price):
        # 가격 문의는 인기순이 아니라 최저가 위주로
        ranked = sorted(in_range, key=lambda p: p["price"])
        # 너무 싼 액세서리성 상품을 피하려고 인기 상품 상위권에서만 최저가를 고른다
        popular = _rerank(in_range, cond)[:15]
        ranked = sorted(popular, key=lambda p: p["price"]) or ranked
        return ranked[:limit], False
    if in_range and cond.extras.get("popular"):
        # '많이 구매한 거' → 구매 후기(리뷰) 수가 많은 순
        return sorted(in_range, key=lambda p: (p.get("reviews") or 0, p.get("score") or 0), reverse=True)[:limit], False
    if in_range:
        return _rerank(in_range, cond)[:limit], False

    # 범위 안에 하나도 없으면 → 가장 가까운 가격
    pool = [p for p in (live or await _from_danawa(cond)) if p["price"] > 0 and ok(p)]
    if not pool:
        return [], False

    def distance(p: dict) -> int:
        if cond.min_price and p["price"] < cond.min_price:
            return cond.min_price - p["price"]
        if cond.max_price and p["price"] > cond.max_price:
            return p["price"] - cond.max_price
        return 0
    pool.sort(key=lambda p: (distance(p), -_popularity(p)))
    return pool[:limit], True
