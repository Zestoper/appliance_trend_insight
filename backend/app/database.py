import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "appliance_trend_insight"),
            autocommit=True,
            charset="utf8mb4",
            minsize=1,
            maxsize=10,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def fetchone(sql: str, args=None) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, args)
            return await cur.fetchone()

async def fetchall(sql: str, args=None) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, args)
            return await cur.fetchall()

async def execute(sql: str, args=None) -> int:
    """INSERT/UPDATE/DELETE — lastrowid 반환"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            return cur.lastrowid


async def get_user_by_email(email: str) -> dict | None:
    return await fetchone(
        "SELECT * FROM users WHERE email = %s", (email,)
    )

async def create_user(email: str, password_hash: str, user_type: str, status: str = "active") -> int:
    return await execute(
        "INSERT INTO users (email, password_hash, user_type, status) VALUES (%s, %s, %s, %s)",
        (email, password_hash, user_type, status),
    )

async def create_b2c_profile(user_id: int, nickname: str) -> int:
    return await execute(
        "INSERT INTO user_b2c_profiles (user_id, nickname) VALUES (%s, %s)",
        (user_id, nickname),
    )

async def create_b2b_profile(user_id: int, company_name: str, business_type: str, contact_phone: str) -> int:
    return await execute(
        "INSERT INTO user_b2b_profiles (user_id, company_name, business_type, contact_phone) VALUES (%s, %s, %s, %s)",
        (user_id, company_name, business_type, contact_phone),
    )


async def get_user_alerts(user_id: int) -> list[dict]:
    return await fetchall(
        "SELECT * FROM price_alert WHERE user_id = %s AND is_active = 1 ORDER BY created_at DESC",
        (user_id,),
    )

async def create_alert(user_id: int, product_name: str, target_price: float,
                        current_price: float, product_url: str, alert_type: str) -> int:
    return await execute(
        """INSERT INTO price_alert
           (user_id, product_name, target_price, current_price, product_url, alert_type)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_id, product_name, target_price, current_price, product_url, alert_type),
    )


async def save_ai_report(data_id: int, report_type: str, content: str, model_used: str) -> int:
    return await execute(
        """INSERT INTO ai_reports (data_id, report_type, content, model_used)
           VALUES (%s, %s, %s, %s)""",
        (data_id, report_type, content, model_used),
    )
