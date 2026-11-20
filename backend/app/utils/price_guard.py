"""
가격 데이터 안전장치 — 소모품 가격이나 다른 제품 가격이 '이 제품 가격'으로 저장 · 표시되지 않게 막는다.

3단계로 막는다.
  1) 검색 단계   : 품목 없이 검색하면 소모품 · 부속품을 뺀다 (routers/naver.py → _drop_accessories)
  2) 계산 단계   : sanitize_items()로 렌탈 · 소모품 · 기준가 대비 이상가를 뺀 뒤에만 최저 · 평균을 낸다
  3) 저장 단계   : is_plausible_price()가 DB에 쌓인 그 제품의 최근 가격과 비교해 튀는 값은 저장하지 않는다
"""
import logging

from app.utils.accessory_filter import is_accessory

logger = logging.getLogger(__name__)

RENTAL_KW = ["렌탈", "월렌탈", "렌탈료", "구독", "리스", "렌트", "할부월", "월정액"]

# 같은 제품 가격이 하루 사이에 이 범위를 벗어나면 다른 제품(대개 소모품)으로 본다
_LOW, _HIGH = 0.4, 2.5


def sanitize_items(items: list[dict], ref_price: int = 0, min_price: int = 0) -> list[dict]:
    """가격 계산에 쓸 상품만 남긴다.
    ref_price: 화면에 보이는 그 상품 가격 (모르면 0) · min_price: 품목 최소가 (CATEGORY_RULES)"""
    out = []
    for it in items:
        p = int(it.get("price") or 0)
        title = it.get("title", "")
        mall = it.get("mallName") or it.get("mall") or ""
        if p <= 0 or p < min_price:
            continue
        if any(k in title or k in mall for k in RENTAL_KW):
            continue
        if is_accessory(title, p):
            continue
        if ref_price and not (ref_price * _LOW <= p <= ref_price * 3):
            continue
        out.append(it)

    # 기준가를 모르면 남은 것끼리 중앙값으로 한 번 더 (소모품을 뺀 뒤라 중앙값이 본품 쪽에 잡힌다)
    if not ref_price and len(out) >= 3:
        ps = sorted(int(it["price"]) for it in out)
        med = ps[len(ps) // 2]
        out = [it for it in out if med * _LOW <= int(it["price"]) <= med * _HIGH]
    return out


async def is_plausible_price(product_key: str, product_name: str, price: int, today_str: str | None = None) -> bool:
    """DB에 저장해도 되는 가격인지. 아니면 False (저장하지 않음)."""
    if not price or price <= 0:
        return False
    if product_name and is_accessory(product_name, price):
        logger.warning("[price-guard] 소모품으로 보여 저장 안 함: %s (%s원)", product_name[:40], f"{price:,}")
        return False
    try:
        from app.database import fetchall
        rows = await fetchall(
            "SELECT min_price FROM product_price_history "
            "WHERE product_key = %s AND min_price > 0 AND snapshot_date <> COALESCE(%s::date, CURRENT_DATE) "
            "ORDER BY snapshot_date DESC LIMIT 14",
            (product_key, today_str),
        )
    except Exception:
        return True   # 확인을 못 하면 막지 않는다 (위 1 · 2단계에서 이미 걸렀다)
    hist = sorted(int(r["min_price"]) for r in rows)
    if len(hist) < 3:
        return True
    med = hist[len(hist) // 2]
    if med * _LOW <= price <= med * _HIGH:
        return True
    logger.warning("[price-guard] 최근 가격(%s원)과 너무 달라 저장 안 함: %s → %s원",
                   f"{med:,}", (product_name or product_key)[:40], f"{price:,}")
    return False
