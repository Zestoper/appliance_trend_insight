#!/usr/bin/env python3
"""
공공데이터 외부 변수 캐시 갱신 스크립트
crontab 스케줄:
  매시간:     --type airkorea
  3시간마다:  --type kma
  일 1회:     --type kca
  월 1회:     --type customs kepco
  주 1회:     --type kemco kosis
"""
import asyncio
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

async def refresh_kma():
    from app.services.public_data import fetch_kma_history
    from app.services.naver_cache import set_db_cache
    print("[KMA] 기상청 이력 수집 중...", end=" ", flush=True)
    items = await fetch_kma_history(days=730)
    if not items:
        print("✗ 데이터 없음 (API 키 확인)")
        return
    await set_db_cache("ext:kma:history", {"items": items}, ttl_hours=6)
    print(f"✓ {len(items)}일치 저장")


async def refresh_airkorea():
    from app.services.public_data import fetch_airkorea_history
    from app.services.naver_cache import set_db_cache
    print("[AirKorea] 대기오염 이력 수집 중...", end=" ", flush=True)
    items = await fetch_airkorea_history(days=90)
    if not items:
        print("✗ 데이터 없음 (API 키 확인)")
        return
    await set_db_cache("ext:airkorea:history", {"items": items}, ttl_hours=2)
    print(f"✓ {len(items)}건 저장")


async def refresh_kosis():
    from app.services.public_data import fetch_kosis_cpi
    from app.services.naver_cache import set_db_cache
    print("[KOSIS] 소비자물가지수 수집 중...", end=" ", flush=True)
    items = await fetch_kosis_cpi()
    if not items:
        print("✗ 데이터 없음 (KOSIS_API_KEY 확인)")
        return
    await set_db_cache("ext:kosis:cpi", {"items": items}, ttl_hours=24 * 7)
    print(f"✓ {len(items)}개월치 저장")


async def refresh_customs():
    from app.services.public_data import fetch_customs_trade, HS_CODES
    from app.services.naver_cache import set_db_cache
    for cat in HS_CODES.keys():
        print(f"[관세청] {cat} 수입통계 수집 중...", end=" ", flush=True)
        items = await fetch_customs_trade(cat)
        if not items:
            print("✗ 데이터 없음")
            continue
        await set_db_cache(f"ext:customs:{cat}", {"items": items}, ttl_hours=24 * 31)
        print(f"✓ {len(items)}개월치 저장")
        await asyncio.sleep(0.5)


async def refresh_kepco():
    from app.services.public_data import fetch_kepco_rate
    from app.services.naver_cache import set_db_cache
    print("[KEPCO] 전기요금 수집 중...", end=" ", flush=True)
    items = await fetch_kepco_rate()
    if not items:
        print("✗ 데이터 없음 (KEPCO_API_KEY 확인)")
        return
    await set_db_cache("ext:kepco:rate", {"items": items}, ttl_hours=24 * 7)
    print(f"✓ {len(items)}건 저장")


async def refresh_kemco():
    from app.services.public_data import fetch_kemco_efficiency
    from app.services.naver_cache import set_db_cache
    cats = ["에어컨", "냉장고", "세탁기", "TV", "건조기"]
    for cat in cats:
        print(f"[KEMCO] {cat} 효율등급 수집 중...", end=" ", flush=True)
        data = await fetch_kemco_efficiency(cat)
        if not data:
            print("✗ 데이터 없음")
            continue
        await set_db_cache(f"ext:kemco:{cat}", data, ttl_hours=24 * 7)
        print(f"✓ 1등급 비율 {data.get('grade1_ratio')}%")
        await asyncio.sleep(0.5)


async def refresh_kca():
    from app.services.public_data import fetch_kca_complaints
    from app.services.naver_cache import set_db_cache
    cats = ["에어컨", "냉장고", "세탁기", "공기청정기", "로봇청소기", "식기세척기", "TV"]
    for cat in cats:
        print(f"[KCA] {cat} 소비자피해 수집 중...", end=" ", flush=True)
        items = await fetch_kca_complaints(cat)
        if not items:
            print("✗ 데이터 없음")
            continue
        await set_db_cache(f"ext:kca:{cat}", {"items": items}, ttl_hours=24)
        print(f"✓ {len(items)}건 저장")
        await asyncio.sleep(0.3)


TYPE_MAP = {
    "kma":      refresh_kma,
    "airkorea": refresh_airkorea,
    "kosis":    refresh_kosis,
    "customs":  refresh_customs,
    "kepco":    refresh_kepco,
    "kemco":    refresh_kemco,
    "kca":      refresh_kca,
}


async def main(types: list[str]):
    from app.database import get_pool, close_pool
    await get_pool()
    t0 = time.time()
    for t in types:
        fn = TYPE_MAP.get(t)
        if fn:
            await fn()
        else:
            print(f"알 수 없는 타입: {t}")
    await close_pool()
    print(f"\n완료 ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", nargs="+", default=list(TYPE_MAP.keys()),
                        choices=list(TYPE_MAP.keys()),
                        help="수집할 데이터 타입 (기본: 전체)")
    args = parser.parse_args()
    asyncio.run(main(args.type))
