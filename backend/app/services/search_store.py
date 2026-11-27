"""다나와가 점검 · 차단으로 안 될 때 보여 줄 '마지막으로 받아 둔 검색 결과' 저장소.

- 다나와 검색이 성공할 때마다 검색어별 결과를 DB(search_store)에 덮어쓴다 (메모리 캐시가 30분이라 같은 검색어는 30분에 한 번 정도만 쓴다).
- 다나와가 안 되면 순서대로 찾는다.
  1. 같은 검색어로 저장해 둔 결과
  2. 검색어에 들어 있는 단어(예: "냉장고")로 저장해 둔 결과 중 나머지 단어(예: "삼성 비스포크")가 상품명 · 브랜드에 있는 것
  3. 트렌드 TOP 결과(trend_cache) 중 같은 조건에 맞는 것
  4. 품목 검색이면 가격 이력(product_price_history) 중 상품명 속 모델명이 에너지공단(KEMCO) 그 품목 모델 목록에 있는 제품
     (가격 이력에는 품목이 없어서 KEMCO 모델 목록으로 품목을 확인한다 · 3번 트렌드 결과와 합쳐서 보여 준다)
  5. 품목 단어 없이 모델명 · 브랜드만 검색했으면 가격 이력에서 상품명이 맞는 제품 (사진은 없다)
- 메모리 캐시와 달리 배포 · 재시작해도 남아서 "다나와가 터져도 우리는 안 터지게" 하는 용도다.
"""
import asyncio
import json
import logging
import re
import time

logger = logging.getLogger(__name__)

_table_ready = False
# KEMCO 모델 목록이 있는 품목 (public_data._KEMCO_CAT_PATH_MAP 과 같다)
_KEMCO_CATEGORIES = {"에어컨", "냉장고", "TV", "선풍기", "공기청정기", "제습기", "세탁기"}
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


async def _from_price_history(words: list[str]) -> tuple[list[dict], float] | None:
    """가격 이력에서 상품명에 검색 단어(품목 단어 제외)가 모두 들어 있는 제품의 가장 최근 가격."""
    from app.database import fetchall
    cat_words = _category_words()
    # 가격 이력에는 품목이 없어서 "삼성 비스포크 냉장고"로 찾으면 비스포크 에어컨 · 청소기까지 섞인다.
    # 품목 단어가 들어간 검색은 쓰지 않고, 품목 없이 브랜드 · 모델명만 검색했을 때만 쓴다
    # (그때는 여러 품목이 섞여 나오는 게 원래 검색 의도와 같다).
    if not words or any(w in cat_words for w in words):
        return None
    name_words = words
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
    items = [_price_item(str(r["product_key"]), r["product_name"], r["min_price"]) for r in rows]
    return items, _kst_ts(min(r["snapshot_date"] for r in rows))


_MODEL_RE = re.compile(r"[A-Z]{1,5}\d{1,4}[A-Z0-9]{2,12}")


def _price_item(key: str, name: str, price: int) -> dict:
    is_pcode = key.isdigit()
    return {
        "id":          key if is_pcode else "",
        "title":       name,
        "brand":       name.split()[0] if name.split() else "",
        "price":       int(price),
        "image":       "",   # 다나와 사진 주소가 img.danuri.io/…/해시값.jpg 라서 상품번호로 만들 수 없다
        "link":        f"https://prod.danawa.com/info/?pcode={key}" if is_pcode else "",
        "mallName":    "다나와 최저가비교",
        "reviewCount": 0,
        "reviewScore": 0.0,
    }


def _kst_ts(d) -> float:
    from datetime import datetime, timezone, timedelta
    return datetime(d.year, d.month, d.day, tzinfo=timezone(timedelta(hours=9))).timestamp()


async def _kemco_models(category: str) -> set[str]:
    """에너지공단에 등록된 그 품목 모델명 (대문자). 냉장고 · 에어컨 · TV · 세탁기 · 공기청정기 · 제습기 · 선풍기만 있다."""
    from app.services.public_data import KEMCO_CACHE_PREFIX
    from app.services.naver_cache import get_db_cache_stale
    cached = await get_db_cache_stale(f"{KEMCO_CACHE_PREFIX}{category}")   # 오래됐어도 모델 목록은 쓸 만하다
    return {m.upper() for m in ((cached or {}).get("map") or {})}


async def _from_price_history_by_kemco(words: list[str]) -> tuple[list[dict], float] | None:
    """품목 단어가 있는 검색: 가격 이력 상품명 속 모델명이 KEMCO 그 품목 목록에 있으면 그 품목 제품으로 본다.
    나머지 단어(브랜드 등)는 상품명에 모두 있어야 한다."""
    from datetime import date, timedelta
    from app.database import fetchall
    category = next((w for w in words if w in _KEMCO_CATEGORIES), None)
    if not category:
        return None
    models = await _kemco_models(category)
    if not models:
        return None
    rest = [w for w in words if w != category and w not in _category_words()]
    rows = await fetchall(
        "SELECT DISTINCT ON (product_key) product_key, product_name, min_price, snapshot_date "
        "FROM product_price_history WHERE min_price > 0 AND snapshot_date >= %s "
        "ORDER BY product_key, snapshot_date DESC, snapshot_hour DESC",
        ((date.today() - timedelta(days=60)).isoformat(),),
    )
    picked = []
    for r in rows:
        name = r.get("product_name") or ""
        key = str(r["product_key"])
        cands = {c for c in _MODEL_RE.findall(name.upper()) if len(c) >= 6}
        if key.upper() in models or cands & models:
            if _matches({"title": name}, rest):
                picked.append(r)
    if not picked:
        return None
    picked.sort(key=lambda r: r["snapshot_date"], reverse=True)
    picked = picked[:40]
    items = [_price_item(str(r["product_key"]), r["product_name"], r["min_price"]) for r in picked]
    return items, _kst_ts(min(r["snapshot_date"] for r in picked))


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

        # 4. 품목 검색이면 KEMCO로 품목을 확인한 가격 이력 제품을 트렌드 결과 뒤에 붙인다
        try:
            by_kemco = await _from_price_history_by_kemco(words)
        except Exception as e:
            logger.warning("[search-store] KEMCO 가격 이력 읽기 실패 [%s]: %s", query, e)
            by_kemco = None
        if by_kemco:
            seen_titles = {it.get("title") for it in found}
            found += [it for it in by_kemco[0] if it["title"] not in seen_titles]
            oldest = min(oldest or by_kemco[1], by_kemco[1])

        found = _dedupe(found)
        if found:
            return found, float(oldest)

        # 5. 가격 이력 (모델명 · 브랜드 검색일 때만)
        return await _from_price_history(words)
    except Exception as e:
        logger.warning("[search-store] 예비 결과 읽기 실패 [%s]: %s", query, e)
    return None
