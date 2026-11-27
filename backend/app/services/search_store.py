"""다나와가 점검 · 차단으로 안 될 때 보여 줄 '마지막으로 받아 둔 검색 결과' 저장소.

- 다나와 검색이 성공할 때마다 검색어별 결과를 DB(search_store)에 덮어쓴다 (메모리 캐시가 30분이라 같은 검색어는 30분에 한 번 정도만 쓴다).
- 다나와가 안 되면 순서대로 찾는다.
  1. 같은 검색어로 저장해 둔 결과
  2. 검색어에 들어 있는 단어(예: "냉장고")로 저장해 둔 결과 중 나머지 단어(예: "삼성 비스포크")가 상품명 · 브랜드에 있는 것
  3. 트렌드 TOP 결과(trend_cache) 중 같은 조건에 맞는 것
  4. 가격 이력(product_price_history)에서 상품명이 맞는 제품 — 모델명 · 브랜드 같은 구체적인 검색일 때만
     (가격 이력에는 품목이 저장돼 있지 않아서 "냉장고"처럼 품목만 검색하면 가려낼 수 없다)
- 메모리 캐시와 달리 배포 · 재시작해도 남아서 "다나와가 터져도 우리는 안 터지게" 하는 용도다.
"""
import asyncio
import json
import logging
import time

logger = logging.getLogger(__name__)

_table_ready = False
_save_tasks: set[asyncio.Task] = set()   # 저장 작업이 중간에 사라지지 않게 잡아 둔다


async def _ensure_table():
    global _table_ready
    if _table_ready:
        return
    from app.database import execute
    await execute(
        "CREATE TABLE IF NOT EXISTS search_store ("
        " query TEXT PRIMARY KEY,"
        " items TEXT NOT NULL,"
        " updated_at DOUBLE PRECISION NOT NULL)"
    )
    _table_ready = True


async def save_items(query: str, items: list[dict]) -> None:
    if not query or not items:
        return
    try:
        from app.database import execute
        await _ensure_table()
        await execute(
            "INSERT INTO search_store (query, items, updated_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (query) DO UPDATE SET items = EXCLUDED.items, updated_at = EXCLUDED.updated_at",
            (query, json.dumps(items, ensure_ascii=False, default=str), time.time()),
        )
    except Exception as e:
        logger.warning("[search-store] 저장 실패 [%s]: %s", query, e)


def save_items_background(query: str, items: list[dict]) -> None:
    """검색 응답을 늦추지 않도록 뒤에서 저장한다."""
    try:
        task = asyncio.create_task(save_items(query, list(items)))
    except RuntimeError:
        return
    _save_tasks.add(task)
    task.add_done_callback(_save_tasks.discard)


def _matches(item: dict, words: list[str]) -> bool:
    text = f'{item.get("title", "")} {item.get("brand", "")}'.lower()
    return all(w.lower() in text for w in words)


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        key = it.get("id") or it.get("title")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _category_words() -> set[str]:
    """품목 이름과 그 다나와 카테고리 단어 (상품명에는 거의 없어서 가격 이력 검색에서는 뺀다)."""
    from app.config import CATEGORY_RULES
    from app.utils.danawa_category import CATEGORY_KEYWORDS
    words = set(CATEGORY_RULES) | set(CATEGORY_KEYWORDS)
    for ws in CATEGORY_KEYWORDS.values():
        words |= set(ws)
    return words


def _danawa_image(pcode: str) -> str:
    """다나와 상품번호로 대표 사진 주소를 만든다 (예: 17434922 → .../922/434/img/17434922_1.jpg)."""
    if not pcode.isdigit() or len(pcode) < 6:
        return ""
    return f"https://img.danawa.com/prod_img/500000/{pcode[-3:]}/{pcode[-6:-3]}/img/{pcode}_1.jpg"


async def _from_price_history(words: list[str]) -> tuple[list[dict], float] | None:
    """가격 이력에서 상품명에 검색 단어(품목 단어 제외)가 모두 들어 있는 제품의 가장 최근 가격."""
    from datetime import datetime, timezone, timedelta
    from app.database import fetchall
    cat_words = _category_words()
    name_words = [w for w in words if w not in cat_words]
    if not name_words:
        return None   # 품목만 검색 → 가격 이력으로는 그 품목 제품을 가려낼 수 없다
    rows = await fetchall(
        "SELECT DISTINCT ON (product_key) product_key, product_name, min_price, snapshot_date "
        "FROM product_price_history "
        "WHERE product_name ILIKE ALL(%s) AND min_price > 0 "
        "ORDER BY product_key, snapshot_date DESC, snapshot_hour DESC",
        ([f"%{w}%" for w in name_words],),
    )
    rows = [r for r in rows if (r.get("product_name") or "") not in cat_words]   # 품목 평균 가격 줄 제외
    if not rows:
        return None
    rows.sort(key=lambda r: r["snapshot_date"], reverse=True)
    rows = rows[:40]
    items = []
    for r in rows:
        key, name = str(r["product_key"]), r["product_name"]
        is_pcode = key.isdigit()
        items.append({
            "id":          key if is_pcode else "",
            "title":       name,
            "brand":       name.split()[0] if name.split() else "",
            "price":       int(r["min_price"]),
            "image":       _danawa_image(key),
            "link":        f"https://prod.danawa.com/info/?pcode={key}" if is_pcode else "",
            "mallName":    "다나와 최저가비교",
            "reviewCount": 0,
            "reviewScore": 0.0,
        })
    kst = timezone(timedelta(hours=9))
    oldest = min(r["snapshot_date"] for r in rows)
    return items, datetime(oldest.year, oldest.month, oldest.day, tzinfo=kst).timestamp()


async def load_fallback(query: str) -> tuple[list[dict], float] | None:
    """다나와가 안 될 때 쓸 저장된 결과와 그 저장 시각(유닉스 초). 하나도 없으면 None."""
    query = " ".join((query or "").split())
    if not query:
        return None
    words = query.split()
    try:
        from app.database import fetchone, fetchall
        await _ensure_table()

        # 1. 같은 검색어
        row = await fetchone("SELECT items, updated_at FROM search_store WHERE query = %s", (query,))
        if row:
            items = json.loads(row["items"])
            if items:
                return items, float(row["updated_at"])

        found: list[dict] = []
        oldest = None

        # 2. 검색어 속 단어 하나로 저장된 결과 (예: "삼성 비스포크 냉장고" → "냉장고" 결과에서 "삼성" "비스포크"가 있는 상품)
        if len(words) > 1:
            rows = await fetchall(
                "SELECT query, items, updated_at FROM search_store WHERE query = ANY(%s)", (words,)
            )
            for r in rows:
                rest = [w for w in words if w != r["query"]]
                hits = [it for it in json.loads(r["items"]) if _matches(it, rest)]
                if hits:
                    found += hits
                    oldest = min(oldest or r["updated_at"], r["updated_at"])

        # 3. 트렌드 TOP 결과 (품목별 · 전체)
        if not found:
            from app.routers.analysis import _trend_table
            await _trend_table()
            keys = list(dict.fromkeys([*words, "전체"]))
            rows = await fetchall(
                "SELECT cache_key, payload, updated_at FROM trend_cache WHERE cache_key = ANY(%s)", (keys,)
            )
            for r in rows:
                items = (json.loads(r["payload"]) or {}).get("items") or []
                for it in items:
                    cat = it.get("category") or r["cache_key"]
                    rest = [w for w in words if w != cat]
                    # 품목 단어는 품목으로 · 나머지 단어는 상품명 · 브랜드로 맞춘다
                    if (cat in words or r["cache_key"] != "전체") and _matches(it, rest):
                        found.append(it)
                        oldest = min(oldest or r["updated_at"], r["updated_at"])

        found = _dedupe(found)
        if found:
            return found, float(oldest)

        # 4. 가격 이력 (모델명 · 브랜드 검색일 때만)
        return await _from_price_history(words)
    except Exception as e:
        logger.warning("[search-store] 예비 결과 읽기 실패 [%s]: %s", query, e)
    return None
