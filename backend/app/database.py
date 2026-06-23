import os
import re
from datetime import date as _date
import asyncpg
from dotenv import load_dotenv

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _fix_args(args):
    """DATE 컬럼용: 'YYYY-MM-DD' 문자열을 datetime.date로 자동 변환 (asyncpg 요구사항)"""
    if not args:
        return args
    result = []
    for a in args:
        if isinstance(a, str) and _DATE_RE.match(a):
            try:
                result.append(_date.fromisoformat(a))
            except ValueError:
                result.append(a)
        else:
            result.append(a)
    return tuple(result)

load_dotenv()

_pool: asyncpg.Pool | None = None


def _to_pg(sql: str) -> str:
    """MySQL %s 플레이스홀더 → PostgreSQL $1, $2, ... 변환"""
    count = 0
    def repl(_):
        nonlocal count
        count += 1
        return f'${count}'
    return re.sub(r'%s', repl, sql)


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.getenv("DATABASE_URL")
        if dsn:
            # postgresql://... 형식의 URL을 직접 사용 (Supabase Connect 버튼에서 복사)
            _pool = await asyncpg.create_pool(
                dsn=dsn,
                ssl="require",
                min_size=1,
                max_size=10,
                statement_cache_size=0,
            )
        else:
            _pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 5432)),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "postgres"),
                ssl="require",
                min_size=1,
                max_size=10,
                statement_cache_size=0,
            )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def fetchone(sql: str, args=None) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_to_pg(sql), *_fix_args(args or ()))
        return dict(row) if row else None


async def fetchall(sql: str, args=None) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(_to_pg(sql), *_fix_args(args or ()))
        return [dict(r) for r in rows]


async def execute(sql: str, args=None) -> int:
    """INSERT/UPDATE/DELETE — 0 반환 (lastrowid 불필요 시 사용)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_to_pg(sql), *_fix_args(args or ()))
        return 0


async def _execute_returning(sql: str, args=None) -> int:
    """INSERT ... RETURNING id → id 반환"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_to_pg(sql), *_fix_args(args or ()))
        return row[0] if row else 0


async def get_user_by_email(email: str) -> dict | None:
    return await fetchone("SELECT * FROM users WHERE email = %s", (email,))


async def create_user(email: str, password_hash: str, user_type: str, status: str = "active") -> int:
    return await _execute_returning(
        "INSERT INTO users (email, password_hash, user_type, status) "
        "VALUES (%s, %s, %s, %s) RETURNING user_id",
        (email, password_hash, user_type, status),
    )


async def create_b2c_profile(user_id: int, nickname: str) -> int:
    return await _execute_returning(
        "INSERT INTO user_b2c_profiles (user_id, nickname) VALUES (%s, %s) RETURNING profile_id",
        (user_id, nickname),
    )


async def create_b2b_profile(user_id: int, company_name: str, business_type: str, contact_phone: str) -> int:
    return await _execute_returning(
        "INSERT INTO user_b2b_profiles (user_id, company_name, business_type, contact_phone) "
        "VALUES (%s, %s, %s, %s) RETURNING profile_id",
        (user_id, company_name, business_type, contact_phone),
    )


async def get_user_alerts(user_id: int) -> list[dict]:
    return await fetchall(
        "SELECT * FROM price_alert WHERE user_id = %s AND is_active = TRUE ORDER BY created_at DESC",
        (user_id,),
    )


async def create_alert(user_id: int, product_name: str, target_price: float,
                       current_price: float, product_url: str, alert_type: str) -> int:
    return await _execute_returning(
        "INSERT INTO price_alert "
        "(user_id, product_name, target_price, current_price, product_url, alert_type) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING alert_id",
        (user_id, product_name, target_price, current_price, product_url, alert_type),
    )


async def save_ai_report(data_id: int, report_type: str, content: str, model_used: str) -> int:
    return await _execute_returning(
        "INSERT INTO ai_reports (data_id, report_type, content, model_used) "
        "VALUES (%s, %s, %s, %s) RETURNING report_id",
        (data_id, report_type, content, model_used),
    )
