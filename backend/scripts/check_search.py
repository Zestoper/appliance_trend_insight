#!/usr/bin/env python3
"""
실제 다나와 검색으로 거르기 결과를 눈으로 확인하는 스크립트 (서버 배포 전 점검용).
다나와 원본 결과가 몇 개였는지 · 무엇이 왜 빠졌는지 · 무엇이 남았는지 보여준다.
사용법 (backend 폴더에서):  python scripts/check_search.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.danawa_search import _danawa_query, _fetch_raw_items, danawa_search_products
from app.utils.danawa_category import in_category, is_accessory_category, is_appliance_category
from app.utils.accessory_filter import wants_accessory

CASES = [
    ("캐리어 21평 에어컨", "에어컨"), ("캐리어 에어컨", "에어컨"), ("21평 에어컨", "에어컨"),
    ("삼성", None), ("로보락 S9 MaxV Ultra", "로봇청소기"),
]


def why(it, q, cat):
    if not is_appliance_category(it):
        return "가전 아님"
    if not wants_accessory(q) and is_accessory_category(it):
        return "소모품 카테고리"
    if not in_category(it, cat):
        return "다른 품목"
    return ""


def line(it):
    return f"{it['price']:>10,}원  {it['title'][:38]:<38}  {' > '.join(it.get('categories') or ['(카테고리 없음)'])}"


async def main():
    for q, cat in CASES:
        raw = list(await _fetch_raw_items(_danawa_query(q)))
        res = await danawa_search_products(query=q, page=1, display=8, sort="sim", category=cat)
        print(f"\n===== '{q}' → 다나와에 '{_danawa_query(q)}' (품목: {cat})  원본 {len(raw)}개 → 남음 {res['total']}개")
        dropped = [(why(it, q, cat), it) for it in raw]
        dropped = [(r, it) for r, it in dropped if r][:6]
        for r, it in dropped:
            print(f"  [빠짐: {r}] {line(it)}")
        for it in res["items"]:
            print(f"  [남음] {line(it)}")

asyncio.run(main())
