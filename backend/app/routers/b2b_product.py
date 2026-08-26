from fastapi import APIRouter, Depends, Query
from app.routers.b2b_utils import *
from app.routers.naver import search_products

router = APIRouter()


@router.get("/product-price")
async def get_product_price(title: str = Query(..., min_length=1), _: dict = Depends(require_b2b)):
    import json as _json
    from app.database import fetchall, execute as db_exec

    today = date.today()
    model = extract_model_number(title)
    product_key = model if model else re.sub(r'\s+', ' ', title.strip())[:100]
    search_q = model if model else title

    result = await search_products(query=search_q, page=1, display=50, sort="sim")
    items_raw = result.get("items", [])
    _RENTAL_MALL_KW = ["렌탈", "리스", "렌트", "월정액", "구독"]

    items = [
        {
            "mall":  it.get("mallName", ""),
            "title": it["title"],
            "price": it["price"],
            "link":  it.get("link", ""),
        }
        for it in items_raw
        if it.get("price", 0) > 0
        and not any(kw in it.get("mallName", "") for kw in _RENTAL_MALL_KW)
        and not any(kw in it["title"] for kw in _RENTAL_MALL_KW)
    ]

    if not items:
        return {"available": False, "product_key": product_key, "model_number": model}

    raw_prices = sorted(it["price"] for it in items)
    median_price = raw_prices[len(raw_prices) // 2]
    items = [it for it in items if median_price * 0.2 <= it["price"] <= median_price * 5]

    if not items:
        return {"available": False, "product_key": product_key, "model_number": model}

    prices = [it["price"] for it in items]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = int(sum(prices) / len(prices))

    mall_map: dict[str, int] = {}
    for it in items:
        mall = it["mall"]
        if mall and (mall not in mall_map or it["price"] < mall_map[mall]):
            mall_map[mall] = it["price"]

    malls = sorted(
        [{"mall": m, "price": p} for m, p in mall_map.items()],
        key=lambda x: x["price"],
    )[:8]

    cheapest = min(items, key=lambda x: x["price"])

    mall_json = _json.dumps(malls, ensure_ascii=False)
    try:
        await db_exec(
            """
            INSERT INTO product_price_history
                (product_key, product_name, model_number, min_price, max_price, avg_price, snapshot_date, mall_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_key, snapshot_date) DO UPDATE SET
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                avg_price = EXCLUDED.avg_price,
                mall_data = EXCLUDED.mall_data
            """,
            (product_key, title[:500], model, min_price, max_price, avg_price, today, mall_json),
        )
    except Exception as e:
        logger.warning("상품 가격 DB 저장 실패 [%s]: %s", title[:50], e)

    history_rows = await fetchall(
        "SELECT snapshot_date, min_price, avg_price, max_price "
        "FROM product_price_history WHERE product_key = %s "
        "ORDER BY snapshot_date ASC LIMIT 30",
        (product_key,),
    )
    price_history = [
        {
            "date":      str(r["snapshot_date"]),
            "min_price": r["min_price"],
            "avg_price": r["avg_price"],
        }
        for r in history_rows
    ]

    hist_avg = (
        int(sum(r["avg_price"] for r in history_rows) / len(history_rows))
        if history_rows else avg_price
    )
    hist_min = min(r["min_price"] for r in history_rows) if history_rows else min_price

    vs_hist_avg_pct = round((min_price - hist_avg) / max(hist_avg, 1) * 100, 1)

    if vs_hist_avg_pct <= -5:
        signal_type, signal = "buy", "구매 추천"
        reason = f"현재 최저가({min_price // 10000}만원)가 {abs(int(vs_hist_avg_pct))}% 저렴합니다. 지금이 적기입니다."
    elif vs_hist_avg_pct >= 5:
        signal_type, signal = "wait", "관망 권장"
        reason = f"현재 최저가({min_price // 10000}만원)가 평소보다 {int(vs_hist_avg_pct)}% 비쌉니다."
    else:
        signal_type, signal = "neutral", "적정가"
        reason = "현재 가격이 평소 수준입니다."

    return {
        "available":      True,
        "product_key":    product_key,
        "model_number":   model,
        "min_price":      min_price,
        "max_price":      max_price,
        "avg_price":      avg_price,
        "hist_avg_price": hist_avg,
        "hist_min_price": hist_min,
        "cheapest_mall":  cheapest["mall"],
        "cheapest_link":  cheapest["link"],
        "malls":          malls,
        "price_history":  price_history,
        "signal":         signal,
        "signal_type":    signal_type,
        "reason":         reason,
        "snapshot_date":  str(today),
    }
