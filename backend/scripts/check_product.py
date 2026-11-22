"""검색 분석의 현재가 · 제조사 · 출시일이 왜 그렇게 나왔는지 확인한다 (DB에는 아무것도 쓰지 않음).
실행: cd backend && python scripts/check_product.py "삼성전자 비스포크 김치플러스 RQ33DG71J2ET"
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JWT_SECRET", "check")


async def main(q: str):
    from app.routers.b2b_search_analysis import product_key_for, fetch_product_price_items, _clean_product_items
    from app.routers.b2b_utils import _CATEGORY_MAP
    from app.services.price_service import _danawa_search_pcode, _danawa_fetch_product_meta, get_danawa_price_history

    model, key = product_key_for(q)
    cat = next((c for kw, c in _CATEGORY_MAP.items() if kw in q), None)
    print(f"모델명: {model} · 키: {key} · 카테고리: {cat}\n")

    items = await fetch_product_price_items(model or q)
    print(f"[쇼핑 검색 '{model or q}'] {len(items)}개")
    for it in sorted(items, key=lambda x: x["price"])[:15]:
        print(f"  {it['price']:>10,}원 | 브랜드 {it['brand'] or '-':6} | {it['mall'][:10]:10} | {it['title'][:60]}")

    pcode = await _danawa_search_pcode(model or q)
    print(f"\n[다나와 모델 검색 '{model or q}'] pcode: {pcode}")
    if pcode:
        print("  상세 페이지:", await _danawa_fetch_product_meta(pcode))
    dn = await get_danawa_price_history(model or q, q)
    hist = dn.get("history") or []
    print(f"[다나와 가격 이력] {len(hist)}개 · 출시가 {dn.get('launch_price')} · 출시일 {dn.get('release_date')}")
    if hist:
        print("  최근:", [(h['period'], h['price']) for h in sorted(hist, key=lambda h: h['period'])[-5:]])

    ref = max(hist, key=lambda h: h["period"])["price"] if hist else None
    cleaned = _clean_product_items(items, cat, ref)
    print(f"\n[걸러낸 뒤] 다나와 기준가 {ref} → {len(cleaned)}개 · 최저 {min((i['price'] for i in cleaned), default=None)}")
    for it in sorted(cleaned, key=lambda x: x["price"])[:5]:
        print(f"  {it['price']:>10,}원 | {it['title'][:60]}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "삼성전자 비스포크 김치플러스 RQ33DG71J2ET"))
