import json
from app.database import fetchone, execute


async def get_db_cache(key: str) -> dict | None:
    row = await fetchone(
        "SELECT data FROM naver_cache WHERE cache_key = %s AND expires_at > NOW()",
        (key,),
    )
    if not row:
        return None
    data = row["data"]
    return data if isinstance(data, dict) else json.loads(data)


async def set_db_cache(key: str, data: dict, ttl_hours: int = 168) -> None:
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    await execute(
        """INSERT INTO naver_cache (cache_key, data, fetched_at, expires_at)
           VALUES (%s, %s::jsonb, NOW(), NOW() + interval '1 hour' * %s)
           ON CONFLICT (cache_key) DO UPDATE
           SET data       = EXCLUDED.data,
               fetched_at = NOW(),
               expires_at = NOW() + interval '1 hour' * %s""",
        (key, json_str, ttl_hours, ttl_hours),
    )
