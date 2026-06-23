from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as _BM
from app.routers.b2b_utils import *
from app.routers.b2b_ai import _TREND_CTX_FALLBACK, _GENERIC_FALLBACK

router = APIRouter()


@router.get("/trend-context")
async def get_trend_context(category: str = Query(..., min_length=1), period: str = "3m", _: dict = Depends(require_b2b)):
    """
    트렌드 분석3: 주요 사용 환경(지역별) / 설치 형태 / 구매 목적 / 연관 가전
    """
    import json as _json

    _ck = f"trend-context:{category}:{period}"
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        return _cached[1]

    # 카테고리별 기본 fallback 준비
    fb = _TREND_CTX_FALLBACK.get(category, _GENERIC_FALLBACK)

    # 제품 데이터 + 블로그 텍스트 수집
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            shop_resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=NAVER_HEADERS,
                params={"query": category, "display": 50, "sort": "sim"},
            )
            blog_resp = await client.get(
                "https://openapi.naver.com/v1/search/blog.json",
                headers=NAVER_HEADERS,
                params={"query": f"{category} 구매 후기 설치", "display": 20, "sort": "date"},
            )
        shop_items = shop_resp.json().get("items", [])
        blog_items = blog_resp.json().get("items", [])
    except Exception as e:
        logger.warning(f"[trend-context] 네이버 API 실패: {e}")
        shop_items, blog_items = [], []

    # 제품 타이틀에서 설치 형태 직접 추출
    install_kws = {
        "벽걸이형": ["벽걸이", "벽결이"],
        "스탠드형": ["스탠드"],
        "2in1": ["2in1", "투인원"],
        "창문형": ["창문형"],
        "드럼형": ["드럼"],
        "통돌이형": ["통돌이"],
        "콘덴서형": ["콘덴서"],
        "히트펌프형": ["히트펌프"],
        "양문형": ["양문형", "양문냉장고"],
        "4도어": ["4도어", "빌트인"],
    }
    install_counts: dict[str, int] = {}
    for it in shop_items:
        title_low = strip_html(it.get("title", "")).lower()
        for label, kws in install_kws.items():
            if any(k in title_low for k in kws):
                install_counts[label] = install_counts.get(label, 0) + 1

    total_inst = sum(install_counts.values()) or 0
    install_data = sorted(
        [{"label": k, "pct": round(v / total_inst * 100)} for k, v in install_counts.items()],
        key=lambda x: x["pct"], reverse=True
    )[:4] if total_inst >= 3 else []

    # Groq로 region/purpose/related 생성
    blog_text = " ".join(
        strip_html(b.get("title", "")) + " " + strip_html(b.get("description", ""))
        for b in blog_items
    )[:2000]
    shop_text = " ".join(strip_html(it.get("title", "")) for it in shop_items[:25])

    groq_ok = False
    result = {
        "region":  list(fb["region"]),
        "install": install_data or list(fb["install"]),
        "purpose": list(fb["purpose"]),
        "related": list(fb["related"]),
    }

    try:
        prompt = (
            f"한국 '{category}' 가전 시장을 분석해 JSON만 출력하세요. 다른 텍스트 없이 JSON만.\n\n"
            f"쇼핑 제품명: {shop_text[:600]}\n"
            f"블로그 내용: {blog_text[:900]}\n\n"
            f'{{"region":[{{"label":"서울","pct":숫자}},{{"label":"경기","pct":숫자}},{{"label":"부산","pct":숫자}},{{"label":"대구","pct":숫자}},{{"label":"인천","pct":숫자}}],'
            f'"purpose":[{{"label":"구매이유1","pct":숫자}},{{"label":"구매이유2","pct":숫자}},{{"label":"구매이유3","pct":숫자}},{{"label":"구매이유4","pct":숫자}},{{"label":"구매이유5","pct":숫자}}],'
            f'"related":[{{"label":"연관가전1","pct":숫자}},{{"label":"연관가전2","pct":숫자}},{{"label":"연관가전3","pct":숫자}},{{"label":"연관가전4","pct":숫자}},{{"label":"연관가전5","pct":숫자}}]}}'
            f'\n위 형식대로 실제 한국 {category} 시장 데이터로 채워 JSON만 출력하세요.'
        )
        groq_resp = await _groq_create(
            messages=[
                {"role": "system", "content": "당신은 한국 가전 시장 데이터 전문가입니다. 요청한 JSON 형식만 출력하세요. 마크다운, 설명 없이 순수 JSON만."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.1,
        )
        raw = groq_resp.choices[0].message.content.strip()
        # 마크다운 코드블록 제거
        if "```" in raw:
            raw = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
        # JSON 추출 (첫 { 부터 마지막 } 까지)
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            parsed = _json.loads(raw[start:end+1])
            if parsed.get("region") and parsed.get("purpose") and parsed.get("related"):
                result["region"]  = parsed["region"]
                result["purpose"] = parsed["purpose"]
                result["related"] = parsed["related"]
                groq_ok = True
    except Exception as e:
        logger.warning(f"[trend-context] Groq 실패 (fallback 사용): {e}")

    # Groq 성공 시만 캐시 (실패 결과는 캐시 안 함)
    if groq_ok:
        _GROQ_CACHE[_ck] = (_time.time() + 1800, result)
    return result


@router.get("/product-price")
async def get_product_price(title: str = Query(..., min_length=1), _: dict = Depends(require_b2b)):
    import json as _json
    from app.database import fetchall, execute as db_exec

    today = date.today()
    model = extract_model_number(title)
    product_key = model if model else re.sub(r'\s+', ' ', title.strip())[:100]
    search_q = model if model else title

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(
            NAVER_SHOP_URL,
            headers=NAVER_HEADERS,
            params={"query": search_q, "display": 50, "sort": "sim"},
        )

    items_raw = resp.json().get("items", []) if resp.status_code == 200 else []
    _RENTAL_MALL_KW = ["렌탈", "리스", "렌트", "월정액", "구독"]

    items = [
        {
            "mall":  strip_html(it.get("mallName", "")),
            "title": strip_html(it["title"]),
            "price": int(it["lprice"]),
            "link":  it.get("link", ""),
        }
        for it in items_raw
        if it.get("lprice") and int(it["lprice"]) > 0
        and not any(kw in strip_html(it.get("mallName", "")) for kw in _RENTAL_MALL_KW)
        and not any(kw in strip_html(it["title"]) for kw in _RENTAL_MALL_KW)
    ]

    if not items:
        return {"available": False, "product_key": product_key, "model_number": model}

    raw_prices = sorted(it["price"] for it in items)
    median_price = raw_prices[len(raw_prices) // 2]
    items = [it for it in items if median_price * 0.2 <= it["price"] <= median_price * 5]

    if not items:
        return {"available": False, "product_key": product_key, "model_number": model}

    prices = [it["price"] for it in items]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = int(sum(prices) / len(prices))

    mall_map: dict[str, int] = {}
    for it in items:
        mall = it["mall"]
        if mall and (mall not in mall_map or it["price"] < mall_map[mall]):
            mall_map[mall] = it["price"]

    malls = sorted(
        [{"mall": m, "price": p} for m, p in mall_map.items()],
        key=lambda x: x["price"],
    )[:8]

    cheapest = min(items, key=lambda x: x["price"])

    mall_json = _json.dumps(malls, ensure_ascii=False)
    try:
        await db_exec(
            """
            INSERT INTO product_price_history
                (product_key, product_name, model_number, min_price, max_price, avg_price, snapshot_date, mall_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) AS nv
            ON DUPLICATE KEY UPDATE
                min_price = nv.min_price,
                max_price = nv.max_price,
                avg_price = nv.avg_price,
                mall_data = nv.mall_data
            """,
            (product_key, title[:500], model, min_price, max_price, avg_price, today, mall_json),
        )
    except Exception as e:
        logger.warning("상품 가격 DB 저장 실패 [%s]: %s", title[:50], e)

    history_rows = await fetchall(
        "SELECT snapshot_date, min_price, avg_price, max_price "
        "FROM product_price_history WHERE product_key = %s "
        "ORDER BY snapshot_date ASC LIMIT 30",
        (product_key,),
    )
    price_history = [
        {
            "date":      str(r["snapshot_date"]),
            "min_price": r["min_price"],
            "avg_price": r["avg_price"],
        }
        for r in history_rows
    ]

    hist_avg = (
        int(sum(r["avg_price"] for r in history_rows) / len(history_rows))
        if history_rows else avg_price
    )
    hist_min = min(r["min_price"] for r in history_rows) if history_rows else min_price

    vs_hist_avg_pct = round((min_price - hist_avg) / max(hist_avg, 1) * 100, 1)

    if vs_hist_avg_pct <= -5:
        signal_type, signal = "buy", "구매 추천"
        reason = f"현재 최저가({min_price // 10000}만원)가 {abs(int(vs_hist_avg_pct))}% 저렴합니다. 지금이 적기입니다."
    elif vs_hist_avg_pct >= 5:
        signal_type, signal = "wait", "관망 권장"
        reason = f"현재 최저가({min_price // 10000}만원)가 평소보다 {int(vs_hist_avg_pct)}% 비쌉니다."
    else:
        signal_type, signal = "neutral", "적정가"
        reason = "현재 가격이 평소 수준입니다."

    return {
        "available":      True,
        "product_key":    product_key,
        "model_number":   model,
        "min_price":      min_price,
        "max_price":      max_price,
        "avg_price":      avg_price,
        "hist_avg_price": hist_avg,
        "hist_min_price": hist_min,
        "cheapest_mall":  cheapest["mall"],
        "cheapest_link":  cheapest["link"],
        "malls":          malls,
        "price_history":  price_history,
        "signal":         signal,
        "signal_type":    signal_type,
        "reason":         reason,
        "snapshot_date":  str(today),
    }


@router.get("/product-analysis")
async def get_product_analysis(
    q: str = Query(..., min_length=1),
    category: str = Query(None),
    _: dict = Depends(require_b2b),
):
    from app.database import fetchall
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    today = date.today()
    model = extract_model_number(q)
    product_key = model if model else re.sub(r'\s+', ' ', q.strip())[:100]

    # 카테고리 확정: 명시 전달 > 쿼리 키워드 감지
    detected_category = category or None
    if not detected_category:
        for kw, cat in _CATEGORY_MAP.items():
            if kw in q:
                detected_category = cat
                break

    # 네이버 쇼핑 검색어: 모델번호면 그대로, 일반어면 카테고리 prefix
    search_q = model if model else (f"{detected_category} {q}" if detected_category else q)

    async def _fetch_price():
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS,
                    params={"query": search_q, "display": 50, "sort": "sim"})
            _RKW = ["렌탈", "리스", "렌트", "월정액", "구독"]
            items_raw = resp.json().get("items", []) if resp.status_code == 200 else []
            items = [
                {"mall": strip_html(it.get("mallName", "")), "price": int(it["lprice"]), "link": it.get("link", "")}
                for it in items_raw
                if it.get("lprice") and int(it["lprice"]) > 0
                and not any(kw in strip_html(it.get("mallName", "")) for kw in _RKW)
                and not any(kw in strip_html(it.get("title", "")) for kw in _RKW)
            ]
            if not items:
                return None
            raw = sorted(it["price"] for it in items)
            med = raw[len(raw) // 2]
            items = [it for it in items if med * 0.2 <= it["price"] <= med * 5]
            if not items:
                return None
            prices = [it["price"] for it in items]
            mall_map: dict = {}
            for it in items:
                m = it["mall"]
                if m and (m not in mall_map or it["price"] < mall_map[m]["price"]):
                    mall_map[m] = it
            malls = sorted([{"mall": m, "price": v["price"], "link": v["link"]}
                            for m, v in mall_map.items()], key=lambda x: x["price"])[:10]
            cheapest = malls[0]
            history_rows = await fetchall(
                "SELECT snapshot_date, min_price, avg_price FROM product_price_history "
                "WHERE product_key = %s ORDER BY snapshot_date ASC LIMIT 30",
                (product_key,),
            )
            price_history = [{"date": str(r["snapshot_date"]), "min_price": r["min_price"],
                               "avg_price": r["avg_price"]} for r in history_rows]
            hist_avg = int(sum(r["avg_price"] for r in history_rows) / len(history_rows)) if history_rows else int(sum(prices) / len(prices))
            hist_min = min(r["min_price"] for r in history_rows) if history_rows else min(prices)
            min_p = min(prices)
            vs_pct = round((min_p - hist_avg) / max(hist_avg, 1) * 100, 1)
            if vs_pct <= -5:
                signal, signal_type = "구매 추천", "buy"
                reason = f"현재 최저가({min_p // 10000}만원)가 {abs(int(vs_pct))}% 저렴합니다."
            elif vs_pct >= 5:
                signal, signal_type = "관망 권장", "wait"
                reason = f"현재 가격이 평소보다 {int(vs_pct)}% 비쌉니다."
            else:
                signal, signal_type = "적정가", "neutral"
                reason = "현재 가격이 평소 수준입니다."
            return {
                "min_price": min_p, "avg_price": int(sum(prices) / len(prices)),
                "max_price": max(prices), "hist_avg": hist_avg, "hist_min": hist_min,
                "malls": malls, "cheapest_mall": cheapest["mall"], "cheapest_link": cheapest["link"],
                "price_history": price_history, "signal": signal, "signal_type": signal_type,
                "reason": reason, "model_number": model,
            }
        except Exception as e:
            logger.warning("상품 가격 조회 실패: %s", e)
            return None

    async def _fetch_trend():
        try:
            start_d = (today - timedelta(days=90)).strftime("%Y-%m-%d")
            end_d   = today.strftime("%Y-%m-%d")
            headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
            body = {"startDate": start_d, "endDate": end_d, "timeUnit": "week",
                    "keywordGroups": [{"groupName": q, "keywords": [q]}]}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://openapi.naver.com/v1/datalab/search",
                                         json=body, headers=headers)
            results = resp.json().get("results", [])
            return results[0]["data"] if results else []
        except Exception as e:
            logger.warning("트렌드 데이터 조회 실패: %s", e)
            return []

    async def _fetch_reviews():
        try:
            rq = f"{q} 사용후기"
            async with httpx.AsyncClient(timeout=8.0) as client:
                blog_r, cafe_r = await asyncio.gather(
                    client.get("https://openapi.naver.com/v1/search/blog.json",
                               headers=NAVER_HEADERS, params={"query": rq, "display": 10, "sort": "date"}),
                    client.get("https://openapi.naver.com/v1/search/cafearticle.json",
                               headers=NAVER_HEADERS, params={"query": rq, "display": 8, "sort": "date"}),
                )
            reviews = []
            for it in blog_r.json().get("items", []):
                txt = strip_html(it.get("description", "")).strip()
                if len(txt) < 30:
                    continue
                reviews.append({"source": "블로그", "title": strip_html(it["title"]),
                                 "review": txt[:200], "link": it.get("link", "")})
            for it in cafe_r.json().get("items", []):
                txt = strip_html(it.get("description", "")).strip()
                if len(txt) < 30:
                    continue
                reviews.append({"source": "카페", "title": strip_html(it["title"]),
                                 "review": txt[:200], "link": it.get("link", "")})
            return reviews[:12]
        except Exception:
            return []

    async def _fetch_competitors():
        if not detected_category:
            return []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS,
                    params={"query": detected_category, "display": 40, "sort": "sim"})
            items = resp.json().get("items", []) if resp.status_code == 200 else []
            filtered = [
                {"title": strip_html(it["title"])[:50],
                 "brand": it.get("maker", "") or it.get("brand", ""),
                 "price": int(it["lprice"]), "link": it.get("link", ""), "image": it.get("image", "")}
                for it in items if it.get("lprice") and int(it["lprice"]) > 0
            ]
            if filtered:
                prices = sorted(f["price"] for f in filtered)
                med = prices[len(prices) // 2]
                filtered = [f for f in filtered if med * 0.3 <= f["price"] <= med * 3]
            # 브랜드당 최대 2개, 전체 최대 12개
            seen: dict = {}
            result = []
            for f in filtered:
                b = f["brand"] or "기타"
                cnt = seen.get(b, 0)
                if cnt < 2:
                    seen[b] = cnt + 1
                    result.append(f)
                if len(result) >= 12:
                    break
            return result
        except Exception:
            return []

    price_data, trend_data, reviews, competitors = await asyncio.gather(
        _fetch_price(), _fetch_trend(), _fetch_reviews(), _fetch_competitors(),
        return_exceptions=True,
    )
    price_data  = price_data  if not isinstance(price_data,  Exception) else None
    trend_data  = trend_data  if not isinstance(trend_data,  Exception) else []
    reviews     = reviews     if not isinstance(reviews,     Exception) else []
    competitors = competitors if not isinstance(competitors, Exception) else []

    all_text = ' '.join(r["review"] for r in reviews)
    pos = sum(1 for w in _POS_WORDS if w in all_text)
    neg = sum(1 for w in _NEG_WORDS if w in all_text)
    score = round(pos / (pos + neg) * 100) if (pos + neg) > 0 else 50
    words = re.findall(r'[가-힣]{2,5}', all_text)
    kw_counts = Counter(w for w in words if w not in _STOP)
    keywords = [{"word": w, "count": c} for w, c in kw_counts.most_common(16)]

    # 리뷰별 감성 태그
    tagged_reviews = []
    for r in reviews[:8]:
        txt = r["review"]
        p = sum(1 for w in _POS_WORDS if w in txt)
        n = sum(1 for w in _NEG_WORDS if w in txt)
        r["sentiment"] = "neg" if n > 0 else "pos"
        r["pos_count"] = p
        r["neg_count"] = n
        tagged_reviews.append(r)

    return {
        "query":    q,
        "model_number": model,
        "category": detected_category,
        "price":    price_data,
        "trend":    trend_data,
        "reviews":  tagged_reviews,
        "sentiment": {"pos": pos, "neg": neg, "score": score, "keywords": keywords},
        "competitors": competitors,
    }


@router.get("/keyword-review")
async def get_keyword_review(
    category: str = Query(..., min_length=1),
    keyword:  str = Query(..., min_length=1),
    _: dict = Depends(require_b2b),
):
    """키워드(브랜드/기능) 별 블로그+카페 리뷰 언급량"""
    query = f"{category} {keyword} 리뷰"
    async with httpx.AsyncClient(timeout=6.0) as client:
        blog_r, cafe_r = await asyncio.gather(
            client.get("https://openapi.naver.com/v1/search/blog.json",
                       headers=NAVER_HEADERS,
                       params={"query": query, "display": 1}),
            client.get("https://openapi.naver.com/v1/search/cafearticle.json",
                       headers=NAVER_HEADERS,
                       params={"query": query, "display": 1}),
        )
    blog_total = blog_r.json().get("total", 0) if blog_r.status_code == 200 else 0
    cafe_total = cafe_r.json().get("total", 0) if cafe_r.status_code == 200 else 0

    return {
        "keyword":  keyword,
        "category": category,
        "blog":     blog_total,
        "cafe":     cafe_total,
        "total":    blog_total + cafe_total,
    }


# ── B2B 가격 알림 ────────────────────────────────────────────────────────────

class _AlertIn(_BM):
    category: str
    target_price: int   # 원 단위

@router.get("/alerts")
async def list_b2b_alerts(user: dict = Depends(require_b2b)):
    from app.database import fetchall
    rows = await fetchall(
        "SELECT alert_id, product_name AS category, target_price, created_at "
        "FROM price_alert WHERE user_id = %s AND is_active = 1 "
        "AND alert_type = 'below' ORDER BY created_at DESC",
        (user["user_id"],),
    )
    return rows

@router.post("/alerts")
async def create_b2b_alert(body: _AlertIn, user: dict = Depends(require_b2b)):
    from app.database import fetchall, execute
    # 같은 카테고리 알림이 이미 있으면 업데이트
    existing = await fetchall(
        "SELECT alert_id FROM price_alert WHERE user_id=%s AND product_name=%s AND is_active=1",
        (user["user_id"], body.category),
    )
    if existing:
        await execute(
            "UPDATE price_alert SET target_price=%s WHERE alert_id=%s",
            (body.target_price, existing[0]["alert_id"]),
        )
        return {"alert_id": existing[0]["alert_id"], "updated": True}
    from app.database import create_alert
    aid = await create_alert(
        user_id=user["user_id"],
        product_name=body.category,
        target_price=body.target_price,
        current_price=0,
        product_url="",
        alert_type="below",
    )
    return {"alert_id": aid, "created": True}

@router.delete("/alerts/{alert_id}")
async def delete_b2b_alert(alert_id: int, user: dict = Depends(require_b2b)):
    from app.database import execute, fetchall
    row = await fetchall(
        "SELECT alert_id FROM price_alert WHERE alert_id=%s AND user_id=%s",
        (alert_id, user["user_id"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="알림 없음")
    await execute("UPDATE price_alert SET is_active=0 WHERE alert_id=%s", (alert_id,))
    return {"deleted": True}


@router.get("/prediction-accuracy")
async def get_prediction_accuracy_endpoint(
    days: int = Query(90, ge=7, le=365),
    _: dict = Depends(require_b2b),
):
    from app.services.price_service import get_prediction_accuracy
    return await get_prediction_accuracy(days)


@router.post("/run-backtest")
async def run_backtest(_: dict = Depends(require_b2b)):
    """price_history 과거 데이터로 예측 적중률 백테스트 실행 (1회성)"""
    from app.database import fetchall, execute
    from datetime import date, timedelta

    rows = await fetchall(
        "SELECT category, snapshot_date, avg_price FROM price_history ORDER BY category, snapshot_date ASC"
    )

    # category → [(date, avg_price), ...]
    by_cat: dict = {}
    for r in rows:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append((r["snapshot_date"], int(r["avg_price"])))

    inserted = 0
    for cat, history in by_cat.items():
        for i, (snap_date, price) in enumerate(history):
            # 30일 후 데이터가 있는 것만
            target_date = snap_date + timedelta(days=30) if hasattr(snap_date, 'days') else \
                          date.fromisoformat(str(snap_date)) + timedelta(days=30)
            snap_date_obj = snap_date if hasattr(snap_date, 'year') else date.fromisoformat(str(snap_date))

            future = next(
                (p for d, p in history if
                 (d if hasattr(d, 'year') else date.fromisoformat(str(d))) >= target_date),
                None
            )
            if future is None:
                continue

            # 직전 7일 평균으로 신호 결정
            week_ago_prices = [p for d, p in history[:i] if
                               (d if hasattr(d, 'year') else date.fromisoformat(str(d))) >= snap_date_obj - timedelta(days=7)]
            week_avg = sum(week_ago_prices) / len(week_ago_prices) if week_ago_prices else price
            week_chg = (price - week_avg) / max(week_avg, 1) * 100

            if week_chg <= -4:
                signal = "매입 적기"
            elif week_chg <= -1.5:
                signal = "관망 권장"
            elif week_chg >= 4:
                signal = "적정가"
            else:
                signal = "적정가"

            change_pct = (future - price) / max(price, 1) * 100

            from app.services.price_service import _CORRECT_RULES
            rule = _CORRECT_RULES.get(signal)
            correct = int(rule(change_pct)) if rule else None

            try:
                await execute(
                    """INSERT IGNORE INTO b2b_prediction_log
                       (category, signal_type, price_at_pred, predicted_at,
                        verified_at, price_at_verify, price_change_pct, was_correct)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (cat, signal, price, str(snap_date_obj),
                     str(target_date), future, round(change_pct, 2), correct),
                )
                inserted += 1
            except Exception:
                pass

    return {"inserted": inserted, "categories": list(by_cat.keys())}


# ── 뉴스 피드 ─────────────────────────────────────────────────────────────────
@router.get("/news")
async def get_b2b_news(category: str = Query(..., min_length=1), _: dict = Depends(require_b2b)):
    _ck = f"news:{_CACHE_VER}:{category}"
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        return _cached[1]

    async with httpx.AsyncClient(timeout=8.0) as client:
        news_r, blog_r = await asyncio.gather(
            client.get("https://openapi.naver.com/v1/search/news.json",
                       headers=NAVER_HEADERS,
                       params={"query": f"{category} 시장 트렌드", "display": 8, "sort": "date"}),
            client.get("https://openapi.naver.com/v1/search/blog.json",
                       headers=NAVER_HEADERS,
                       params={"query": f"{category} 구매 후기 2025", "display": 6, "sort": "date"}),
            return_exceptions=True,
        )

    items = []
    if not isinstance(news_r, Exception) and news_r.status_code == 200:
        for it in news_r.json().get("items", []):
            items.append({
                "type":        "news",
                "title":       strip_html(it.get("title", "")),
                "description": strip_html(it.get("description", ""))[:140],
                "link":        it.get("originallink") or it.get("link", ""),
                "pubDate":     it.get("pubDate", "")[:10],
                "source":      it.get("officename") or "뉴스",
            })
    if not isinstance(blog_r, Exception) and blog_r.status_code == 200:
        for it in blog_r.json().get("items", []):
            items.append({
                "type":        "blog",
                "title":       strip_html(it.get("title", "")),
                "description": strip_html(it.get("description", ""))[:140],
                "link":        it.get("link", ""),
                "pubDate":     it.get("postdate", "")[:10] if it.get("postdate") else it.get("pubDate", "")[:10],
                "source":      it.get("bloggername") or "블로그",
            })

    # 날짜 내림차순, 최대 12개
    items.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    result = items[:12]
    _GROQ_CACHE[_ck] = (_time.time() + 1800, result)
    return result


# ── DataLab 쇼핑인사이트 ──────────────────────────────────────────────────────
_SHOPPING_CAT_MAP = {
    "에어컨":    "50000134",
    "냉장고":    "50000136",
    "세탁기":    "50000138",
    "건조기":    "50000139",
    "공기청정기": "50000140",
    "로봇청소기": "50000141",
    "식기세척기": "50000142",
    "TV":        "50000008",
    "전기밥솥":  "50000143",
    "전자레인지": "50000144",
}

@router.get("/shopping-insight")
async def get_shopping_insight(category: str = Query(..., min_length=1), period: str = "3m", _: dict = Depends(require_b2b)):
    _ck = f"shopping-insight:{_CACHE_VER}:{category}:{period}"
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        return _cached[1]

    cat_code = _SHOPPING_CAT_MAP.get(category)
    if not cat_code:
        return {"error": f"'{category}' 카테고리 코드 없음"}

    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 90)
    from datetime import date as _date, timedelta as _td
    end_dt   = _date.today()
    start_dt = end_dt - _td(days=days)
    dl_headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
    body_base = {
        "startDate": start_dt.strftime("%Y-%m-%d"),
        "endDate":   end_dt.strftime("%Y-%m-%d"),
        "timeUnit":  "month",
        "category":  cat_code,
    }

    async def _fetch(url, extra=None):
        body = {**body_base, **(extra or {})}
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(url, json=body, headers=dl_headers)
        return r.json() if r.status_code == 200 else {}

    base_url = "https://openapi.naver.com/v1/datalab/shopping/category"
    trend_r, gender_r, age_r, device_r = await asyncio.gather(
        _fetch(f"{base_url}"),
        _fetch(f"{base_url}/gender"),
        _fetch(f"{base_url}/age"),
        _fetch(f"{base_url}/device"),
        return_exceptions=True,
    )

    def _results(r):
        if isinstance(r, Exception) or not isinstance(r, dict):
            return []
        return r.get("results", [{}])[0].get("data", []) if r.get("results") else []

    result = {
        "trend":  _results(trend_r),
        "gender": _results(gender_r),
        "age":    _results(age_r),
        "device": _results(device_r),
        "error":  None,
    }
    if all(not result[k] for k in ("trend", "gender", "age", "device")):
        err = trend_r if isinstance(trend_r, dict) else {}
        result["error"] = err.get("errorMessage") or "쇼핑인사이트 데이터 없음"

    if not result["error"]:
        _GROQ_CACHE[_ck] = (_time.time() + 3600, result)
    return result
