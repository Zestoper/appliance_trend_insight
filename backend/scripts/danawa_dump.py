"""다나와 상품 페이지와 가격 기록 원본을 그대로 저장한다 (대표가와 주간 최저가가 왜 다른지 확인용).
실행: cd backend && python scripts/danawa_dump.py RQ33DG71J3EW
결과: 저장소 맨 위 b2b_audit/danawa_<모델>_page.html · _price.json (커밋 안 됨)
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JWT_SECRET", "dump")

import httpx  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "b2b_audit")


async def main(model: str):
    from app.services.price_service import _danawa_search_pcode, _DANAWA_HEADERS
    pcode = await _danawa_search_pcode(model)
    print("pcode:", pcode)
    if not pcode:
        return
    os.makedirs(OUT, exist_ok=True)
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        page = await c.get(f"https://prod.danawa.com/info/?pcode={pcode}",
                           headers={"User-Agent": _DANAWA_HEADERS["User-Agent"], "Accept-Language": "ko-KR"})
        price = await c.get("https://prod.danawa.com/info/ajax/getProductPriceList.ajax.php",
                            params={"productCode": pcode},
                            headers={**_DANAWA_HEADERS, "Referer": f"https://prod.danawa.com/info/?pcode={pcode}"})
    with open(os.path.join(OUT, f"danawa_{model}_page.html"), "w", encoding="utf-8") as f:
        f.write(page.text)
    with open(os.path.join(OUT, f"danawa_{model}_price.json"), "w", encoding="utf-8") as f:
        f.write(price.text)
    print("page", page.status_code, len(page.text), "· price", price.status_code, len(price.text))
    try:
        d = price.json()
        print("가격 기록 키:", list(d.keys()))
        for k in ("1", "3", "6", "12", "24"):
            rs = (d.get(k) or {}).get("result") or []
            if rs:
                print(k, "개월:", len(rs), "개 · 첫 항목:", json.dumps(rs[0], ensure_ascii=False)[:300])
    except Exception as e:
        print("JSON 아님:", e, price.text[:300])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "RQ33DG71J3EW"))
