"""매일 가격을 다시 수집할 '사용자가 실제로 본 제품' 목록.

예전에는 '최근 7일 안에 가격 기록이 있는 제품'을 매일 다시 수집했는데, 수집하는 순간 오늘 기록이
생겨 다시 7일 안에 들어가므로 한 번 들어온 제품은 영원히 빠지지 않았다 (11월 3일 기준 339개).
목록이 계속 늘면서 수집 시간과 메모리가 함께 늘어 Render 무료 서버(512MB)가 죽었다.
→ 사용자가 구매 타이밍 화면에서 본 제품과 매일 수집에서 찾은 카테고리별 최신 제품만 기록하고
  최근 7일 안에 기록된 제품 최대 150개만 수집한다 (실사용자가 없어도 최신 제품 가격이 매일 쌓이도록).
"""
from app.database import execute, fetchall

MAX_TRACKED = 150   # 매일 수집하는 최신 제품(카테고리마다 3개) + 사용자가 본 제품
_ready = False


async def _ensure_table() -> None:
    global _ready
    if _ready:
        return
    await execute(
        """
        CREATE TABLE IF NOT EXISTS tracked_products (
            product_key    TEXT PRIMARY KEY,
            product_name   TEXT,
            last_viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    _ready = True


async def touch_product(product_key: str, product_name: str) -> None:
    await _ensure_table()
    await execute(
        """
        INSERT INTO tracked_products (product_key, product_name, last_viewed_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (product_key) DO UPDATE SET
            product_name = EXCLUDED.product_name,
            last_viewed_at = NOW()
        """,
        (product_key, product_name[:200]),
    )


async def recent_products(days: int = 7, limit: int = MAX_TRACKED) -> list[dict]:
    await _ensure_table()
    return await fetchall(
        """
        SELECT product_key, product_name
        FROM tracked_products
        WHERE last_viewed_at >= NOW() - make_interval(days => %s)
        ORDER BY last_viewed_at DESC
        LIMIT %s
        """,
        (days, limit),
    )
