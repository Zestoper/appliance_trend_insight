#!/usr/bin/env python3
"""
다나와 검색 결과에 '카테고리' 정보가 어떤 이름으로 들어 있는지 확인하는 일회성 스크립트.
사용법 (backend 폴더에서):  python scripts/danawa_fields.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx

from app.services.danawa_search import _extract_products_json, _DANAWA_HEADERS

QUERIES = ["캐리어 21평 에어컨", "삼성", "로보락 S9 MaxV Ultra"]


async def main():
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for q in QUERIES:
            r = await client.get("https://search.danawa.com/", params={"query": q, "tab": "goods"}, headers=_DANAWA_HEADERS)
            products = _extract_products_json(r.text)
            print(f"\n===== {q} · 상품 {len(products)}개")
            if not products:
                continue
            print("필드 이름:", sorted(products[0].keys()))
            for p in products[:6]:
                cat = {k: v for k, v in p.items() if "cat" in k.lower() or "cate" in k.lower() or "category" in k.lower()}
                print(" -", str(p.get("productName", ""))[:40], "|", json.dumps(cat, ensure_ascii=False)[:300])

asyncio.run(main())
