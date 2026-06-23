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
    await execute("""
        CREATE TABLE IF NOT EXISTS b2b_prediction_log (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            category        VARCHAR(50)  NOT NULL,
            signal_type     VARCHAR(50)  NOT NULL,
            price_at_pred   INT          NOT NULL,
            predicted_at    DATE         NOT NULL,
            verified_at     DATE         DEFAULT NULL,
            price_at_verify INT          DEFAULT NULL,
            price_change_pct FLOAT       DEFAULT NULL,
            was_correct     TINYINT(1)   DEFAULT NULL,
            UNIQUE KEY uk_cat_pred_date (category, predicted_at)
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
        VALUES (%s, %s, %s, %s, %s, %s, %s) AS nv
        ON DUPLICATE KEY UPDATE
            min_price = nv.min_price,
            max_price = nv.max_price,
            avg_price = nv.avg_price
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

    # B2B 모니터용 카테고리 스냅샷 → price_history 테이블 저장
    _B2B_CATS = [
        "에어컨", "냉장고", "세탁기", "건조기", "TV",
        "공기청정기", "로봇청소기", "식기세척기", "전기밥솥", "전자레인지",
    ]

    async def _upsert_price_history(category: str, avg_p: int, min_p: int, max_p: int, median_p: int, brand_json: str, n: int):
        from app.database import execute as db_exec
        await db_exec(
            """
            INSERT INTO price_history
                (category, snapshot_date, avg_price, min_price, max_price, median_price, total_products, brand_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                avg_price     = VALUES(avg_price),
                min_price     = VALUES(min_price),
                max_price     = VALUES(max_price),
                median_price  = VALUES(median_price),
                total_products = VALUES(total_products),
                brand_data    = VALUES(brand_data)
            """,
            (category, today_str, avg_p, min_p, max_p, median_p, n, brand_json),
        )

    for cat in CATEGORY_RULES:
        try:
            products_data = await search_products(
                query=cat, page=1, display=100, sort="sim", category=cat
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
            # 중앙값 50% 미만·300% 초과는 부품·이상값 제거
            valid_items = [it for it in valid_items if med * 0.5 <= it["price"] <= med * 3.0]
            prices = [it["price"] for it in valid_items]
            if not prices:
                continue

            avg_p    = int(sum(prices) / len(prices))
            prices_s = sorted(prices)
            min_p    = prices_s[0]
            max_p    = prices_s[-1]
            median_p = prices_s[len(prices_s) // 2]

            await upsert_price(cat.strip().lower(), cat, min_p, today_str, slot)
            print(f"[snapshot]   {cat}: avg={avg_p:,}원 min={min_p:,}원 n={len(prices)}")

            # B2B 카테고리면 price_history 에도 저장 (브랜드 + 가격 티어 포함)
            if cat in _B2B_CATS:
                brand_map: dict[str, list[int]] = {}
                for it in valid_items:
                    b = (it.get("maker") or it.get("brand") or "").strip()
                    if b:
                        brand_map.setdefault(b, []).append(it["price"])
                brand_list = sorted(
                    [{"brand": b, "avg": int(sum(ps) / len(ps)), "count": len(ps)}
                     for b, ps in brand_map.items() if len(ps) >= 2],
                    key=lambda x: -x["count"]
                )[:8]
                await _upsert_price_history(cat, avg_p, min_p, max_p, median_p, _json.dumps(brand_list, ensure_ascii=False), len(prices))

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

    # ── 매입 적기 알림 이메일 발송 ───────────────────────────────────────────
    await _send_buy_signal_emails(today_str)


async def _send_buy_signal_emails(today_str: str):
    """price_history에서 7일 대비 -5% 이하 카테고리 탐지 → B2B 유저 전체 발송 (하루 1회)."""
    try:
        from app.database import fetchall
        from app.services.email_service import send_buy_signal_alert
        import json as _j

        # 카테고리별 오늘 + 7일 전 비교
        _B2B_CATS = ["에어컨", "냉장고", "세탁기", "건조기", "TV",
                     "공기청정기", "로봇청소기", "식기세척기", "전기밥솥", "전자레인지"]
        buy_cats: list[dict] = []
        for cat in _B2B_CATS:
            rows = await fetchall(
                "SELECT avg_price FROM price_history WHERE category = %s "
                "ORDER BY snapshot_date DESC LIMIT 8",
                (cat,),
            )
            if len(rows) < 5:
                continue
            latest_avg = rows[0]["avg_price"]
            week_avg   = rows[min(6, len(rows) - 1)]["avg_price"]
            if week_avg <= 0:
                continue
            chg = round((latest_avg - week_avg) / week_avg * 100, 1)
            if chg <= -5:
                buy_cats.append({"category": cat, "avg_price": latest_avg, "week_change_pct": chg})

        if not buy_cats:
            print("[email] 매입 적기 카테고리 없음 → 알림 생략")
            return

        # B2B 활성 유저 조회
        users = await fetchall(
            "SELECT email, company_name FROM users WHERE user_type = 'b2b' AND status = 'active'",
        )
        if not users:
            return

        print(f"[email] 매입 적기 카테고리 {[c['category'] for c in buy_cats]} → {len(users)}명 발송")
        import asyncio as _asyncio
        for u in users:
            await _asyncio.to_thread(
                send_buy_signal_alert,
                u["email"],
                u.get("company_name") or "",
                buy_cats,
            )
    except Exception as e:
        print(f"[email] 매입 알림 처리 실패: {e}")


async def price_snapshot_loop():
    await asyncio.sleep(5)
    await _collect_daily_prices()
    while True:
        await asyncio.sleep(24 * 3600)  # 하루 1회 수집 (네이버 API 쿼터 절약)
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) AS nv
                ON DUPLICATE KEY UPDATE
                    avg_price      = nv.avg_price,
                    min_price      = nv.min_price,
                    max_price      = nv.max_price,
                    median_price   = nv.median_price,
                    total_products = nv.total_products
                """,
                (category, d, avg, mn, mx, med, len(prices), _json.dumps([])),
            )
            inserted += 1
        except Exception as e:
            logger.warning("[backfill] INSERT 실패 [%s %s]: %s", category, d, e)

    logger.info("[backfill] %s 완료 — %d일치 삽입", category, inserted)


async def _check_price_alerts():
    """활성 가격 알림을 현재 price_history 평균가와 비교해 조건 충족 시 이메일 발송 후 비활성화"""
    from app.database import fetchall, execute
    from app.services.email_service import send_price_alert_email

    alerts = await fetchall(
        """SELECT pa.alert_id, pa.user_id, pa.product_name AS category, pa.target_price,
                  u.email, u.company_name
           FROM price_alert pa
           JOIN users u ON u.user_id = pa.user_id
           WHERE pa.is_active = 1 AND pa.alert_type = 'below'""",
    )
    if not alerts:
        return

    triggered = 0
    for a in alerts:
        row = await fetchall(
            "SELECT avg_price FROM price_history WHERE category = %s ORDER BY snapshot_date DESC LIMIT 1",
            (a["category"],),
        )
        if not row:
            continue
        current = int(row[0]["avg_price"])
        if current <= int(a["target_price"]):
            send_price_alert_email(
                to_email=a["email"],
                company_name=a.get("company_name", ""),
                category=a["category"],
                target_price=int(a["target_price"]),
                current_price=current,
            )
            await execute(
                "UPDATE price_alert SET is_active=0, triggered_at=NOW() WHERE alert_id=%s",
                (a["alert_id"],),
            )
            triggered += 1
            logger.info("[alert] 발송 완료 → %s | %s 현재 %d원 (목표 %d원)",
                        a["email"], a["category"], current, int(a["target_price"]))

    if triggered:
        logger.info("[alert] 총 %d건 발송", triggered)


async def price_alert_loop():
    """6시간마다 가격 알림 체크 + 매일 예측 검증"""
    import asyncio
    run_count = 0
    while True:
        try:
            await _check_price_alerts()
        except Exception as e:
            logger.warning("[alert] 체크 실패: %s", e)
        # 4번 실행(24시간)마다 예측 검증
        run_count += 1
        if run_count % 4 == 0:
            try:
                await verify_predictions()
            except Exception as e:
                logger.warning("[prediction] 검증 실패: %s", e)
        await asyncio.sleep(6 * 3600)


# ── 예측 적중률 트래킹 ──────────────────────────────────────────────────────

# 신호별 "맞다"고 판정하는 기준 (30일 후 가격 변동률)
_CORRECT_RULES = {
    "buy":     lambda pct: pct <= 5,    # 매입 적기: 30일 후 5% 이내 상승 or 하락
    "watch":   lambda pct: pct <= -3,   # 하락 추세: 실제로 3% 이상 하락
    "neutral": lambda pct: abs(pct) < 5, # 보합: 5% 이내 변동
    "caution": lambda pct: pct >= 3,    # 상승 추세: 실제로 3% 이상 상승
    "wait":    lambda pct: pct >= 5,    # 가격 상승: 실제로 5% 이상 상승
    # 한국어 키
    "매입 적기":  lambda pct: pct <= 5,
    "구매 추천":  lambda pct: pct <= 5,
    "하락 추세":  lambda pct: pct <= -3,
    "관망 권장":  lambda pct: pct <= 5,
    "상승 추세":  lambda pct: pct >= 3,
    "가격 상승":  lambda pct: pct >= 5,
    "보합":      lambda pct: abs(pct) < 5,
    "적정가":    lambda pct: abs(pct) < 5,
}


async def save_prediction(category: str, signal_type: str, avg_price: int):
    """대시보드 로드 시 오늘의 예측 신호를 기록 (하루 1회, 중복 무시)"""
    from app.database import execute
    today = date.today().isoformat()
    try:
        await execute(
            """INSERT IGNORE INTO b2b_prediction_log
               (category, signal_type, price_at_pred, predicted_at)
               VALUES (%s, %s, %s, %s)""",
            (category, signal_type, avg_price, today),
        )
    except Exception as e:
        logger.debug("[prediction] 저장 스킵 [%s]: %s", category, e)


async def verify_predictions():
    """30일 이상 지난 미검증 예측을 price_history와 비교해 was_correct 업데이트"""
    from app.database import fetchall, execute
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    rows = await fetchall(
        """SELECT id, category, signal_type, price_at_pred, predicted_at
           FROM b2b_prediction_log
           WHERE was_correct IS NULL AND predicted_at <= %s""",
        (cutoff,),
    )
    for r in rows:
        verify_date = (date.fromisoformat(str(r["predicted_at"])) + timedelta(days=30)).isoformat()
        actual = await fetchall(
            """SELECT avg_price FROM price_history
               WHERE category = %s AND snapshot_date >= %s
               ORDER BY snapshot_date ASC LIMIT 1""",
            (r["category"], verify_date),
        )
        if not actual:
            continue
        current_price = int(actual[0]["avg_price"])
        base_price    = int(r["price_at_pred"])
        change_pct    = (current_price - base_price) / base_price * 100

        rule = _CORRECT_RULES.get(r["signal_type"])
        correct = int(rule(change_pct)) if rule else None

        await execute(
            """UPDATE b2b_prediction_log
               SET verified_at=%s, price_at_verify=%s, price_change_pct=%s, was_correct=%s
               WHERE id=%s""",
            (verify_date, current_price, round(change_pct, 2), correct, r["id"]),
        )
        logger.info("[prediction] 검증 완료 [%s %s] 변동 %.1f%% → %s",
                    r["category"], r["signal_type"], change_pct, "정답" if correct else "오답")


async def get_prediction_accuracy(days: int = 90) -> dict:
    """최근 N일 예측 적중률 통계 반환"""
    from app.database import fetchall
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = await fetchall(
        """SELECT signal_type, was_correct, COUNT(*) AS cnt
           FROM b2b_prediction_log
           WHERE predicted_at >= %s AND was_correct IS NOT NULL
           GROUP BY signal_type, was_correct""",
        (since,),
    )
    total, correct = 0, 0
    by_signal: dict = {}
    for r in rows:
        sig = r["signal_type"]
        cnt = int(r["cnt"])
        total += cnt
        if r["was_correct"]:
            correct += cnt
        if sig not in by_signal:
            by_signal[sig] = {"correct": 0, "total": 0}
        by_signal[sig]["total"] += cnt
        if r["was_correct"]:
            by_signal[sig]["correct"] += cnt

    overall = round(correct / total * 100, 1) if total else None
    detail  = [
        {"signal": k, "accuracy": round(v["correct"] / v["total"] * 100, 1), "total": v["total"]}
        for k, v in by_signal.items() if v["total"] > 0
    ]
    return {"days": days, "total_predictions": total, "overall_accuracy": overall, "by_signal": detail}
