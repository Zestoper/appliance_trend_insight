#!/usr/bin/env python3
"""
약관 동의 기록 없이 만들어진 회원 찾기 (2026-11-21 약관 동의 도입 이후 가입자 기준).
가입 도중 실패했다가 다시 시도해서 '회원만 있고 약관 기록은 없는' 계정이 생겼을 수 있다.

사용법 (backend 폴더에서, .env의 DATABASE_URL 사용)
  python scripts/check_terms.py                 # 목록만
  python scripts/check_terms.py --delete 12 15  # 그 user_id 회원을 지운다 (테스트 계정 정리용)
본인 확인이 된 실제 회원이면 지우지 말고 다음 로그인 때 약관 동의를 다시 받는 쪽이 맞다.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

SINCE = "2026-11-21"
CHILD_TABLES = ["price_alert", "payments", "user_social_accounts", "password_resets",
                "user_b2c_profiles", "user_b2b_profiles"]


async def main(delete_ids: list[int]):
    from app.database import fetchall, get_pool, close_pool
    rows = await fetchall(
        "SELECT u.user_id, u.email, u.user_type, u.created_at, "
        "       COALESCE(string_agg(s.provider, ','), '') AS providers "
        "FROM users u LEFT JOIN user_social_accounts s ON s.user_id = u.user_id "
        "WHERE u.terms_agreed_at IS NULL AND u.created_at >= %s "
        "GROUP BY u.user_id ORDER BY u.created_at",
        (SINCE,),
    )
    print(f"{SINCE} 이후 가입했는데 약관 동의 기록이 없는 회원: {len(rows)}명")
    for r in rows:
        print(f"  user_id={r['user_id']:<6} {str(r['created_at'])[:19]}  {r['user_type']}  "
              f"{r['providers'] or '이메일'}  {r['email']}")

    if delete_ids:
        allowed = {r["user_id"] for r in rows}
        targets = [i for i in delete_ids if i in allowed]
        skipped = [i for i in delete_ids if i not in allowed]
        if skipped:
            print(f"\n목록에 없는 user_id라 건너뜀: {skipped}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for uid in targets:
                    for t in CHILD_TABLES:
                        if await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{t}"):
                            await conn.execute(f"DELETE FROM {t} WHERE user_id = $1", uid)
                    await conn.execute("DELETE FROM users WHERE user_id = $1", uid)
        print(f"\n삭제 완료: {targets}")
    elif rows:
        print("\n테스트 계정이면: python scripts/check_terms.py --delete <user_id> ...")
    await close_pool()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", nargs="*", type=int, default=[], help="지울 user_id (목록에 있는 것만)")
    asyncio.run(main(ap.parse_args().delete))
