#!/usr/bin/env python3
"""
DB에 이미 쌓인 '쓰레기 가격'을 찾아서 (원하면) 지우는 점검 스크립트.

찾는 것
  1) 이름이 소모품인 제품의 가격 기록 (예: "… 전용 울트라도크 거름망")
  2) 같은 제품의 다른 날 가격과 비교해 너무 튀는 날 (중앙값의 40% 미만 · 250% 초과) — 목록만 보여주고 지우지 않음
  3) 매일 가격을 수집하는 추적 목록(tracked_products)에 들어간 소모품

사용법 (backend 폴더에서, .env의 DATABASE_URL 사용)
  python scripts/audit_prices.py            # 찾기만 (아무것도 안 지움)
  python scripts/audit_prices.py --delete   # 소모품 이름 기록 · 추적 목록의 소모품만 삭제
  python scripts/audit_prices.py --fix 53531354527=300000~1500000
      # 그 제품의 기록 중 가격 범위를 벗어난 것만 삭제 (사람이 확인한 정상 범위를 적는다 · 여러 번 써도 됨)
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


async def fix_ranges(fixes: list[str]):
    from app.database import execute, fetchall
    for f in fixes:
        key, rng = f.split("=", 1)
        lo, hi = (int(x.replace(",", "")) for x in rng.split("~", 1))
        rows = await fetchall(
            "SELECT min_price FROM product_price_history WHERE product_key = %s AND min_price > 0 "
            "AND (min_price < %s OR min_price > %s)", (key, lo, hi))
        await execute(
            "DELETE FROM product_price_history WHERE product_key = %s AND min_price > 0 "
            "AND (min_price < %s OR min_price > %s)", (key, lo, hi))
        print(f"  key={key}  {lo:,}~{hi:,}원 밖의 기록 {len(rows)}개 삭제")


async def main(delete: bool, fixes: list[str]):
    if fixes:
        from app.database import close_pool
        print("범위 밖 기록 삭제")
        await fix_ranges(fixes)
        await close_pool()
        return

    from app.database import fetchall, execute, close_pool
    from app.utils.accessory_filter import is_accessory

    rows = await fetchall(
        "SELECT product_key, product_name, snapshot_date, snapshot_hour, min_price "
        "FROM product_price_history WHERE min_price > 0"
    )
    by_key = defaultdict(list)
    for r in rows:
        by_key[r["product_key"]].append(r)

    from app.utils.accessory_filter import _CATEGORIES

    bad: list[dict] = []                         # 소모품 이름 → --delete로 지움
    odd: list[tuple[dict, int]] = []             # 가격이 튀는 날 → 목록만 (사람이 확인)
    for key, rs in by_key.items():
        name = next((r["product_name"] for r in rs if r["product_name"]), "") or ""
        if is_accessory(name, rs[0]["min_price"]):
            bad += rs
            continue
        # "TV" · "에어컨"처럼 품목 전체 최저가를 모으는 기록은 날마다 다른 상품이라 비교하지 않는다
        if name.strip() in _CATEGORIES or len(rs) < 3:
            continue
        ps = sorted(r["min_price"] for r in rs)
        med = ps[len(ps) // 2]
        odd += [(r, med) for r in rs if not (med * LOW <= r["min_price"] <= med * HIGH)]

    def summary(items):
        groups = defaultdict(list)
        for r in items:
            groups[r["product_key"]].append(r)
        for key, rs in groups.items():
            ps = [r["min_price"] for r in rs]
            ds = sorted(str(r["snapshot_date"]) for r in rs)
            print(f"  {len(rs):>3}개  {min(ps):>10,}~{max(ps):,}원  {ds[0]}~{ds[-1]}  {(rs[0]['product_name'] or key)[:45]}")

    print(f"가격 기록 {len(rows):,}개 · 제품 {len(by_key):,}개 검사\n")
    print(f"[소모품 이름] {len(bad)}개 기록 — --delete로 지워짐")
    summary(bad)
    print(f"\n[가격이 튀는 날] {len(odd)}개 기록 — 자동으로 안 지움 (중앙값 자체가 쓰레기인 경우가 있어서 사람이 확인)")
    groups = defaultdict(list)
    for r, med in odd:
        groups[r["product_key"]].append((r, med))
    for key, rs in groups.items():
        ps = [r["min_price"] for r, _ in rs]
        print(f"  {len(rs):>3}개  {min(ps):>10,}~{max(ps):,}원 (중앙값 {rs[0][1]:,}원)  {(rs[0][0]['product_name'] or key)[:40]}  key={key}")

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
        for r in bad:
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
    ap.add_argument("--delete", action="store_true", help="소모품 이름 기록 삭제")
    ap.add_argument("--fix", action="append", default=[], help="KEY=최소~최대 : 범위 밖 기록 삭제")
    a = ap.parse_args()
    asyncio.run(main(a.delete, a.fix))
