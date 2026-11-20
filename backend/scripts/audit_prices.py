#!/usr/bin/env python3
"""
DB에 이미 쌓인 '쓰레기 가격'을 찾아서 (원하면) 지우는 점검 스크립트.

찾는 것
  1) 이름이 소모품인 제품의 가격 기록 (예: "… 전용 울트라도크 거름망")
  2) 같은 제품의 다른 날 가격과 비교해 너무 튀는 날 (중앙값의 40% 미만 · 250% 초과)
  3) 매일 가격을 수집하는 추적 목록(tracked_products)에 들어간 소모품

사용법 (backend 폴더에서, .env의 DATABASE_URL 사용)
  python scripts/audit_prices.py            # 찾기만 (아무것도 안 지움)
  python scripts/audit_prices.py --delete   # 찾은 것 삭제
"""
import argparse
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

LOW, HIGH = 0.4, 2.5


async def main(delete: bool):
    from app.database import fetchall, execute, close_pool
    from app.utils.accessory_filter import is_accessory

    rows = await fetchall(
        "SELECT product_key, product_name, snapshot_date, snapshot_hour, min_price "
        "FROM product_price_history WHERE min_price > 0"
    )
    by_key = defaultdict(list)
    for r in rows:
        by_key[r["product_key"]].append(r)

    bad: list[tuple[dict, str]] = []
    for key, rs in by_key.items():
        name = next((r["product_name"] for r in rs if r["product_name"]), "") or ""
        if is_accessory(name, rs[0]["min_price"]):
            bad += [(r, "소모품 이름") for r in rs]
            continue
        if len(rs) >= 3:
            ps = sorted(r["min_price"] for r in rs)
            med = ps[len(ps) // 2]
            bad += [(r, f"중앙값 {med:,}원과 너무 다름") for r in rs if not (med * LOW <= r["min_price"] <= med * HIGH)]

    print(f"가격 기록 {len(rows):,}개 · 제품 {len(by_key):,}개 검사 → 의심 {len(bad):,}개\n")
    for r, why in sorted(bad, key=lambda x: (x[0]["product_key"], str(x[0]["snapshot_date"]))):
        print(f"  {r['snapshot_date']}  {r['min_price']:>10,}원  {(r['product_name'] or r['product_key'])[:45]}  ← {why}")

    tracked = []
    try:
        tracked = await fetchall("SELECT product_key, product_name FROM tracked_products")
    except Exception:
        pass
    bad_tracked = [t for t in tracked if t["product_name"] and is_accessory(t["product_name"])]
    if bad_tracked:
        print(f"\n매일 수집 중인 소모품 {len(bad_tracked)}개")
        for t in bad_tracked:
            print(f"  {t['product_key']}  {t['product_name'][:50]}")

    if delete and (bad or bad_tracked):
        for r, _ in bad:
            await execute(
                "DELETE FROM product_price_history WHERE product_key = %s AND snapshot_date = %s AND snapshot_hour = %s",
                (r["product_key"], r["snapshot_date"], r["snapshot_hour"]),
            )
        for t in bad_tracked:
            await execute("DELETE FROM tracked_products WHERE product_key = %s", (t["product_key"],))
        print(f"\n삭제 완료: 가격 기록 {len(bad)}개 · 추적 제품 {len(bad_tracked)}개")
    elif bad or bad_tracked:
        print("\n지우려면: python scripts/audit_prices.py --delete")
    await close_pool()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true", help="찾은 기록 삭제")
    asyncio.run(main(ap.parse_args().delete))
