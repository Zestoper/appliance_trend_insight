import asyncio
import json as _json
import logging
import re
from datetime import date, datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

_DANAWA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}


async def _danawa_search_pcode(query: str) -> str | None:
    url = "https://search.danawa.com/dsearch.php"
    params = {"query": query, "tab": "goods"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params, headers=_DANAWA_HEADERS)
        pcodes = re.findall(r'pcode=(\d+)', resp.text)
        return pcodes[0] if pcodes else None
    except Exception:
        return None


async def _danawa_fetch_msrp(pcode: str) -> int | None:
    """Danawa 제품 페이지에서 출시가(권장소비자가) 스크래핑 시도"""
    url = f"https://prod.danawa.com/info/?pcode={pcode}"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, headers={
                "User-Agent": _DANAWA_HEADERS["User-Agent"],
                "Accept-Language": _DANAWA_HEADERS["Accept-Language"],
            })
        html = resp.text
        for pattern in [
            r'출시가[^\d<(]{0,20}([\d,]+)원',
            r'권장소비자가[^\d<(]{0,20}([\d,]+)원',
            r'"msrp"\s*:\s*(\d+)',
            r'"originalPrice"\s*:\s*(\d+)',
        ]:
            m = re.search(pattern, html)
            if m:
                price = int(m.group(1).replace(',', ''))
                if price > 10000:
                    return price
    except Exception:
        pass
    return None


async def get_danawa_price_history(query: str, product_name: str) -> dict:
    """
    반환: {"history": [...], "launch_price": int|None}
    launch_price: 출시가 (다나와 제품 페이지 scrape → 없으면 24개월 최고가로 근사)
    product_name을 우선 검색 (더 구체적), 실패 시 query로 대체
    """
    # 검색 쿼리 후보 생성
    _model_m  = re.search(r'[A-Z]{1,5}[\-]?[A-Z0-9]{3,12}', product_name)
    _model_kw = _model_m.group(0) if _model_m else None
    _cap_m    = re.search(r'\d{2,4}[Ll]', product_name)
    _cap_kw   = _cap_m.group(0) if _cap_m else None
    # 제품명에서 의미 있는 한국어 키워드 추출
    _kw_tokens = re.findall(r'[가-힣]{2,6}(?:형|터|이트|패|색|용)?', product_name)
    _skip_kw   = {'삼성전자', 'LG전자', '이하', '이상', '리터', '이내', '이상'}
    _feat_kws  = [w for w in _kw_tokens if w not in _skip_kw and len(w) >= 2]

    # query에서 첫 단어(브랜드) 제외한 나머지 — "삼성 비스포크 냉장고" → "비스포크 냉장고"
    _query_body = " ".join(query.split()[1:]) if len(query.split()) > 1 else query

    candidate_queries = list(dict.fromkeys(filter(None, [
        product_name[:30],
        product_name,
        query,
        _model_kw,
        # 핵심: "비스포크 냉장고 852L AI인버터" 패턴
        f"{_query_body} {_cap_kw} {_feat_kws[-1]}" if _cap_kw and _feat_kws else None,
        f"{_query_body} {_cap_kw}"                  if _cap_kw else None,
        f"{query} {_cap_kw}"                        if _cap_kw else None,
        f"{query.split()[0]} {_cap_kw}"             if _cap_kw else None,
    ])))

    # 모든 후보를 시도해 데이터가 가장 많은 pcode 선택
    price_url   = "https://prod.danawa.com/info/ajax/getProductPriceList.ajax.php"
    best_pcode  = None
    best_count  = 0
    data        = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        seen_pcodes: set[str] = set()
        for _q in candidate_queries:
            pcode = await _danawa_search_pcode(_q)
            if not pcode or pcode in seen_pcodes:
                continue
            seen_pcodes.add(pcode)
            try:
                headers = {**_DANAWA_HEADERS, "Referer": f"https://prod.danawa.com/info/?pcode={pcode}"}
                resp = await client.get(price_url, params={"productCode": pcode}, headers=headers)
                _d = resp.json()
                _cnt = max((len(_d.get(k, {}).get("result", [])) for k in ["1","3","6","12","24"]), default=0)
                if _cnt > best_count:
                    best_count = _cnt
                    best_pcode = pcode
                    data = _d
                if best_count >= 20:   # 충분한 데이터면 더 이상 탐색 안 함
                    break
            except Exception:
                continue

    if not best_pcode:
        return {"history": [], "launch_price": None}
    pcode = best_pcode

    # 가장 긴 이력 기간 선택: 날짜가 파싱 가능한 항목 수 기준 (24개월 데이터는 날짜 없는 경우 있음)
    def _count_dated(period_items):
        count = 0
        for it in period_items:
            d = it.get("Fulldate") or it.get("date", "")
            if it.get("minPrice", 0) and (
                re.match(r'^\d{2}-\d{2}-\d{2}$', d) or re.match(r'^\d{4}-\d{2}-\d{2}$', d)
            ):
                count += 1
        return count

    items = []
    best_dated = 0
    for period_key in ["24", "12", "6", "3", "1"]:
        period_items = data.get(period_key, {}).get("result", [])
        dated = _count_dated(period_items)
        if dated > best_dated:
            best_dated = dated
            items = period_items

    def _parse_item(item):
        raw_date = item.get("Fulldate") or item.get("date", "")
        price = item.get("minPrice", 0)
        if not price:
            return None
        if re.match(r'^\d{2}-\d{2}-\d{2}$', raw_date):
            raw_date = "20" + raw_date
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', raw_date):
            return None
        return {"period": raw_date, "price": price}

    history = [r for item in items if (r := _parse_item(item))]

    # 출시가: 1) 다나와 제품 페이지 스크래핑  2) 24·12·6개월 최고가로 대체
    launch_price = await _danawa_fetch_msrp(pcode)
    if not launch_price:
        for period_key in ["24", "12", "6"]:
            period_items = data.get(period_key, {}).get("result", [])
            if period_items:
                prices = [it.get("minPrice", 0) for it in period_items if it.get("minPrice", 0) > 0]
                if prices:
                    launch_price = max(prices)
                    break

    return {"history": history, "launch_price": launch_price}


async def _init_tables():
    from app.database import execute, fetchall
    status_columns = await fetchall("SHOW COLUMNS FROM users LIKE 'status'")
    if not status_columns:
        await execute("""
            ALTER TABLE users
            ADD COLUMN status ENUM('pending', 'active', 'rejected')
            NOT NULL DEFAULT 'active'
            AFTER user_type
        """)
    await execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            category      VARCHAR(50)  NOT NULL,
            snapshot_date DATE         NOT NULL,
            avg_price     INT          NOT NULL DEFAULT 0,
            min_price     INT          NOT NULL DEFAULT 0,
            max_price     INT          NOT NULL DEFAULT 0,
            median_price  INT          NOT NULL DEFAULT 0,
            total_products INT         NOT NULL DEFAULT 0,
            brand_data    JSON,
            created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_cat_date (category, snapshot_date)
        )
    """)
    await execute("""
        CREATE TABLE IF NOT EXISTS product_price_history (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            product_key   VARCHAR(200) NOT NULL,
            product_name  VARCHAR(500),
            model_number  VARCHAR(100),
            min_price     INT          NOT NULL DEFAULT 0,
            max_price     INT          NOT NULL DEFAULT 0,
            avg_price     INT          NOT NULL DEFAULT 0,
            snapshot_date DATE         NOT NULL,
            snapshot_hour TINYINT      NOT NULL DEFAULT 0,
            mall_data     JSON,
            created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_prod_date_hour (product_key, snapshot_date, snapshot_hour)
        )
    """)
    hour_col = await fetchall("SHOW COLUMNS FROM product_price_history LIKE 'snapshot_hour'")
    if not hour_col:
        await execute("ALTER TABLE product_price_history ADD COLUMN snapshot_hour TINYINT NOT NULL DEFAULT 0 AFTER snapshot_date")
        try:
            await execute("ALTER TABLE product_price_history DROP INDEX uk_prod_date")
        except Exception:
            pass
        try:
            await execute("ALTER TABLE product_price_history ADD UNIQUE KEY uk_prod_date_hour (product_key, snapshot_date, snapshot_hour)")
        except Exception:
            pass


async def upsert_price(product_key: str, product_name: str, price: int, today_str: str, hour: int = 0):
    from app.database import execute
    await execute(
        """
        INSERT INTO product_price_history
            (product_key, product_name, min_price, max_price, avg_price, snapshot_date, snapshot_hour)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            min_price = VALUES(min_price),
            max_price = VALUES(max_price),
            avg_price = VALUES(avg_price)
        """,
        (product_key, product_name, price, price, price, today_str, hour),
    )


async def _collect_daily_prices():
    from app.database import fetchall
    from app.routers.naver import search_products, get_datalab
    from app.config import CATEGORY_RULES

    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    slot = (now.hour // 6) * 6
    seven_days_ago = (now.date() - timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"[snapshot] {today_str} {slot:02d}h 가격 수집 시작")

    _RENTAL_KW_SNAP = ["렌탈", "월렌탈", "렌탈료", "구독", "리스", "할부월"]

    for cat in CATEGORY_RULES:
        try:
            products_data = await search_products(
                query=cat, page=1, display=30, sort="sim", category=cat
            )
            items = products_data.get("items", [])
            cat_min = CATEGORY_RULES[cat].get("min_price", 0)
            valid_items = [
                it for it in items
                if it["price"] > 0
                and it["price"] >= cat_min
                and not any(kw in it["title"] for kw in _RENTAL_KW_SNAP)
            ]
            prices = [it["price"] for it in valid_items]
            if len(prices) < 3:
                continue
            prices_s = sorted(prices)
            med = prices_s[len(prices_s) // 2]
            valid_items = [it for it in valid_items if med * 0.1 <= it["price"] <= med * 10]
            prices = [it["price"] for it in valid_items]
            if not prices:
                continue
            await upsert_price(cat.strip().lower(), cat, min(prices), today_str, slot)
            print(f"[snapshot]   {cat}: {min(prices):,}원")

            # 상위 5개 개별 제품도 추적
            for it in valid_items[:5]:
                if it.get("id") and it["price"] > 0:
                    try:
                        await upsert_price(str(it["id"]), it["title"], it["price"], today_str, slot)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[snapshot]   {cat} 실패: {e}")
        await asyncio.sleep(1.2)

    tracked = await fetchall(
        """
        SELECT DISTINCT product_key, product_name
        FROM product_price_history
        WHERE product_key REGEXP '^[0-9]+$' AND snapshot_date >= %s
        """,
        (seven_days_ago,),
    )
    for row in tracked:
        pid = row["product_key"]
        pname = row["product_name"] or ""
        try:
            res = await search_products(query=pname, page=1, display=20, sort="sim")
            match = next((it for it in res.get("items", []) if str(it["id"]) == pid), None)
            if match and match["price"] > 0:
                await upsert_price(pid, pname, match["price"], today_str, slot)
                print(f"[snapshot]   제품 {pid} ({pname[:20]}): {match['price']:,}원")
        except Exception as e:
            print(f"[snapshot]   제품 {pid} 실패: {e}")
        await asyncio.sleep(1.2)

    from app.config import _DL_CACHE
    DL_CATS = ["냉장고", "세탁기", "건조기", "에어컨", "공기청정기",
               "로봇청소기", "식기세척기", "에어프라이어", "TV", "세탁건조기"]
    start_str = (now.date() - timedelta(days=30)).strftime("%Y-%m-%d")
    for cat in DL_CATS:
        cache_key = f"{cat}_{start_str}"
        try:
            result = await get_datalab(cat)
            if result.get("data"):
                _DL_CACHE[cache_key] = {"data": result["data"], "ts": datetime.utcnow()}
                print(f"[snapshot]   DataLab {cat}: {len(result['data'])}개")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[snapshot]   DataLab {cat} 실패: {e}")

    print(f"[snapshot] {today_str} {slot:02d}h 완료")


async def price_snapshot_loop():
    await asyncio.sleep(5)
    await _collect_daily_prices()
    while True:
        await asyncio.sleep(6 * 3600)
        await _collect_daily_prices()


async def backfill_category_price_history(category: str, today: date) -> None:
    """
    Danawa 가격 이력으로 price_history 테이블을 어제까지 백필한다.
    오늘 데이터는 이미 저장돼 있으므로 today 미만(yesterday and before)만 삽입.
    카테고리 TOP5 제품을 Danawa에서 조회해 날짜별 평균/최소/최대를 집계한다.
    """
    from app.database import execute as db_exec, fetchall
    from app.routers.naver import search_products
    from app.utils.helpers import strip_html

    today_str = str(today)

    # 이미 14일 이상 데이터가 있으면 백필 불필요
    existing = await fetchall(
        "SELECT COUNT(*) AS cnt FROM price_history WHERE category = %s",
        (category,),
    )
    if existing and existing[0]["cnt"] >= 14:
        return

    logger.info("[backfill] %s 시작", category)

    # TOP5 제품 목록
    try:
        raw = await search_products(query=category, page=1, display=10, sort="sim", category=category)
        items = [it for it in raw.get("items", []) if it.get("price", 0) > 0][:5]
    except Exception as e:
        logger.warning("[backfill] 제품 조회 실패 [%s]: %s", category, e)
        return

    if not items:
        return

    # 날짜 → 가격 목록
    date_prices: dict[str, list[int]] = {}

    for item in items:
        product_name = strip_html(item.get("title", ""))
        try:
            result = await get_danawa_price_history(category, product_name)
            for entry in result.get("history", []):
                d, p = entry["period"], entry["price"]
                # 오늘 미만 + 유효 가격만
                if d < today_str and p > 0:
                    date_prices.setdefault(d, []).append(p)
        except Exception as e:
            logger.warning("[backfill] Danawa 조회 실패 [%s]: %s", product_name, e)
        await asyncio.sleep(0.8)

    if not date_prices:
        logger.info("[backfill] %s Danawa 데이터 없음", category)
        return

    # 날짜별 집계 → price_history 삽입
    inserted = 0
    for d, prices in sorted(date_prices.items()):
        if not prices:
            continue
        prices_s = sorted(prices)
        avg = int(sum(prices) / len(prices))
        mn  = prices_s[0]
        mx  = prices_s[-1]
        med = prices_s[len(prices_s) // 2]
        try:
            await db_exec(
                """
                INSERT INTO price_history
                    (category, snapshot_date, avg_price, min_price, max_price,
                     median_price, total_products, brand_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    avg_price      = VALUES(avg_price),
                    min_price      = VALUES(min_price),
                    max_price      = VALUES(max_price),
                    median_price   = VALUES(median_price),
                    total_products = VALUES(total_products)
                """,
                (category, d, avg, mn, mx, med, len(prices), _json.dumps([])),
            )
            inserted += 1
        except Exception as e:
            logger.warning("[backfill] INSERT 실패 [%s %s]: %s", category, d, e)

    logger.info("[backfill] %s 완료 — %d일치 삽입", category, inserted)
