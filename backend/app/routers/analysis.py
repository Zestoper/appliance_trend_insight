import asyncio
import json as _json
import logging
import math
import re
from datetime import date, timedelta, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.config import NAVER_HEADERS, CATEGORY_RULES
from app.utils.helpers import strip_html
from app.routers.naver import search_products, get_datalab, get_news, youtube_search, get_ppomppu

logger = logging.getLogger(__name__)
router = APIRouter()

import os as _os
from dotenv import load_dotenv as _load_dotenv
from groq import AsyncGroq as _AsyncGroq
_groq_client: _AsyncGroq | None = None
_groq_active_key: str | None = None

def _get_groq() -> _AsyncGroq:
    global _groq_client, _groq_active_key
    _load_dotenv(override=True)
    current_key = _os.getenv("GROQ_API_KEY")
    if _groq_client is None or current_key != _groq_active_key:
        _groq_active_key = current_key
        _groq_client = _AsyncGroq(api_key=current_key)
    return _groq_client

_RAG_CHUNK_MAX = 150


def _parse_json(content: str | None) -> dict | list:
    if not content:
        return {}
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?\s*", "", content).strip().rstrip("`").strip()
    # 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 추출
    start = min(
        (text.find("{") if text.find("{") != -1 else len(text)),
        (text.find("[") if text.find("[") != -1 else len(text)),
    )
    end_brace = text.rfind("}")
    end_bracket = text.rfind("]")
    end = max(end_brace, end_bracket) + 1
    if start >= end:
        return {}
    return _json.loads(text[start:end])


@router.get("/api/timing")
async def get_timing(category: str = Query(..., min_length=1), product_id: str = Query(None)):
    from app.database import fetchall
    from app.services.price_service import upsert_price

    today = date.today()
    start_date = today - timedelta(days=30)

    detected_cat = next((cat for cat in CATEGORY_RULES if cat in category), None)
    price_task = search_products(
        query=category, page=1, display=30, sort="sim", category=detected_cat
    )
    dl_url = "https://openapi.naver.com/v1/datalab/search"
    dl_headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
    dl_base = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate":   today.strftime("%Y-%m-%d"),
        "timeUnit":  "date",
    }

    def _dl_candidates():
        seen, out = set(), []
        def add(w):
            if w and w not in seen:
                seen.add(w); out.append(w)
        if detected_cat:
            add(detected_cat)
        for w in reversed(category.split()):
            if len(w) >= 2:
                add(w)
        add(category)
        return out

    async def fetch_datalab():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for kw in _dl_candidates():
                    body = {**dl_base, "keywordGroups": [{"groupName": kw, "keywords": [kw]}]}
                    resp = await client.post(dl_url, json=body, headers=dl_headers)
                    data = (resp.json().get("results") or [{}])[0].get("data", [])
                    if len(data) >= 7:
                        return {"data": data, "keyword": kw}
            return {"data": [], "keyword": category}
        except Exception:
            return {"data": [], "keyword": category}

    try:
        products_data, dl_result = await asyncio.gather(
            price_task, fetch_datalab(), return_exceptions=True
        )
        if isinstance(products_data, Exception):
            products_data = {"items": []}
        if isinstance(dl_result, Exception) or not isinstance(dl_result, dict):
            dl_result = {"data": [], "keyword": category}
        search_data    = dl_result["data"]
        search_keyword = dl_result["keyword"]

        items = products_data.get("items", [])

        _EXCLUDE_KW = ["렌탈", "월렌탈", "렌탈료", "구독", "리스", "할부월",
                       "필터", "부품", "액세서리", "케이스", "커버", "청소포",
                       "먼지봉투", "호스", "거치대", "브라켓", "리모컨"]
        valid = [
            it for it in items
            if it["price"] > 0
            and not any(kw in it["title"] for kw in _EXCLUDE_KW)
        ]

        cat_min = CATEGORY_RULES.get(detected_cat or "", {}).get("min_price", 0)
        if cat_min:
            valid = [it for it in valid if it["price"] >= cat_min]

        if len(valid) >= 3:
            prices_sorted = sorted(it["price"] for it in valid)
            mid = len(prices_sorted) // 2
            median_p = prices_sorted[mid]
            valid = [
                it for it in valid
                if median_p * 0.10 <= it["price"] <= median_p * 10
            ]

        if not valid:
            return {"data": [], "search_data": search_data, "analysis": None,
                    "error": "가격 데이터가 부족합니다. 다른 검색어를 시도해보세요."}

        today_str = today.strftime("%Y-%m-%d")
        cur_slot  = (datetime.utcnow().hour // 6) * 6
        search_date = start_date.strftime("%Y-%m-%d")

        # 검색 결과 중 이미 이력이 있는 제품을 우선 선택 — 날마다 top 제품이 바뀌는 문제 방지
        valid_ids = [str(it["id"]) for it in valid if it["id"]]
        existing_keys: set[str] = set()
        if valid_ids:
            placeholders = ",".join(["%s"] * len(valid_ids))
            existing_rows = await fetchall(
                f"SELECT DISTINCT product_key FROM product_price_history "
                f"WHERE product_key IN ({placeholders}) AND snapshot_date >= %s",
                (*valid_ids, search_date),
            )
            existing_keys = {r["product_key"] for r in existing_rows}

        if product_id:
            top = next((it for it in valid if str(it["id"]) == product_id), None)
            if not top:
                top = next((it for it in valid if str(it["id"]) in existing_keys), valid[0])
        else:
            top = next((it for it in valid if str(it["id"]) in existing_keys), valid[0])
        product_key  = str(top["id"]) if top["id"] else category.strip().lower()
        product_name = top["title"]
        cur_price    = top["price"]
        tracked_product = {
            "id":       top["id"],
            "title":    top["title"],
            "image":    top["image"],
            "link":     top["link"],
            "price":    top["price"],
            "mallName": top["mallName"],
        }

        rows = await fetchall(
            """
            SELECT snapshot_date, MIN(min_price) AS min_price
            FROM product_price_history
            WHERE product_key = %s AND snapshot_date >= %s
            GROUP BY snapshot_date
            ORDER BY snapshot_date ASC
            """,
            (product_key, search_date),
        )

        try:
            await upsert_price(product_key, product_name, cur_price, today_str, cur_slot)
        except Exception as e:
            logger.warning("가격 upsert 실패 [%s]: %s", product_key, e)

        rows = list(rows)

        # ── 제품 불일치 감지 ──────────────────────────────────────────────────
        # 이력 가격 중간값과 현재 네이버 가격이 2배 이상 차이나면
        # 이전에 다른 제품이 추적된 것으로 판단해 이력 폐기
        _hist_only = [r["min_price"] for r in rows
                      if str(r["snapshot_date"]) != today_str and r["min_price"] > 0]
        if len(_hist_only) >= 2:
            _h_med = sorted(_hist_only)[len(_hist_only) // 2]
            if not (_h_med * 0.5 <= cur_price <= _h_med * 2):
                rows = []  # 이력 버림 → 아래 Danawa 백필에서 재검증

        # ── Danawa 백필 ──────────────────────────────────────────────────────
        danawa_launch_price = None
        from app.services.price_service import get_danawa_price_history
        try:
            danawa_result = await get_danawa_price_history(category, product_name)
            danawa_history = danawa_result["history"]
            danawa_launch_price = danawa_result.get("launch_price")

            # DB에 14일 미만 데이터가 있으면 다나와로 보완 (2일치만 있어도 나머지 28일 채움)
            if len(rows) < 14 and danawa_history:
                # 가격 일치 검증: Danawa 중간값이 현재가와 2배 이상 차이나면 다른 제품 → 삽입 안함
                _d_prices = [it["price"] for it in danawa_history]
                _d_med = sorted(_d_prices)[len(_d_prices) // 2]
                if _d_med * 0.5 <= cur_price <= _d_med * 2:
                    # 최근 30일 범위 내의 다나와 데이터만 삽입
                    for item in danawa_history:
                        d, p = item["period"], item["price"]
                        if d >= search_date and d != today_str:
                            await upsert_price(product_key, product_name, p, d, 0)
                    rows = list(await fetchall(
                        """
                        SELECT snapshot_date, MIN(min_price) AS min_price
                        FROM product_price_history
                        WHERE product_key = %s AND snapshot_date >= %s
                        GROUP BY snapshot_date
                        ORDER BY snapshot_date ASC
                        """,
                        (product_key, search_date),
                    ))
        except Exception as e:
            logger.warning("Danawa 백필 실패 [%s]: %s", product_name, e)

        if not rows or str(rows[-1]["snapshot_date"]) != today_str:
            rows.append({"snapshot_date": today_str, "min_price": cur_price})

        cur_min = cur_price
        data = [{"period": str(r["snapshot_date"]), "price": r["min_price"]} for r in rows]

        hist_prices = [r["min_price"] for r in rows if r["min_price"] > 0]
        hist_avg    = round(sum(hist_prices) / len(hist_prices)) if hist_prices else cur_min
        hist_min    = min(hist_prices) if hist_prices else cur_min

        diff_pct = round((cur_min - hist_avg) / max(hist_avg, 1) * 100, 1)

        if len(hist_prices) >= 14:
            recent7   = hist_prices[-7:]
            older7    = hist_prices[-14:-7]
            direction = (sum(recent7) / len(recent7) - sum(older7) / len(older7)) / max(sum(older7) / len(older7), 1)
        elif len(hist_prices) >= 2:
            direction = (hist_prices[-1] - hist_prices[0]) / max(hist_prices[0], 1)
        else:
            direction = 0

        if diff_pct <= -10:
            score = "최고"
            msg   = f"현재가({cur_min:,}원)가 30일 평균보다 {abs(diff_pct):.0f}% 낮아요. 지금이 최적의 구매 타이밍입니다."
            color = "green"
        elif diff_pct <= 0:
            score = "좋음"
            msg   = f"현재가({cur_min:,}원)가 30일 평균 수준이에요. 지금 구매도 좋습니다."
            color = "blue"
        elif diff_pct <= 15:
            score = "보통"
            msg   = f"현재가({cur_min:,}원)가 평균보다 {diff_pct:.0f}% 높아요. 조금 더 기다리면 좋을 수 있어요."
            color = "yellow"
        else:
            score = "대기"
            msg   = f"현재가({cur_min:,}원)가 평균보다 {diff_pct:.0f}% 높아요. 가격이 내릴 때를 기다리세요."
            color = "red"

        trend_dir = "상승" if direction > 0.03 else "하락" if direction < -0.03 else "안정"
        low_idx   = hist_prices.index(hist_min) if hist_prices else 0
        low_day   = str(rows[low_idx]["snapshot_date"])

        search_summary = None
        if len(search_data) >= 7:
            ratios  = [d["ratio"] for d in search_data]
            avg_all = sum(ratios) / len(ratios)
            recent7 = ratios[-7:]
            avg_r7  = sum(recent7) / len(recent7)
            sl_diff = round((avg_r7 - avg_all) / max(avg_all, 1) * 100, 1)
            search_summary = {
                "current":  round(ratios[-1], 1),
                "avg90":    round(avg_all, 1),
                "diff_pct": sl_diff,
                "peak_day": search_data[ratios.index(max(ratios))]["period"],
                "keyword":  search_keyword,
            }

        hist_max = max(hist_prices) if hist_prices else cur_min
        # 출시가: 현재가보다 낮으면 다른 제품 데이터로 판단 → 무시
        if danawa_launch_price and danawa_launch_price < cur_min:
            danawa_launch_price = None
        launch_price = danawa_launch_price or (hist_max if hist_max > cur_min else None)
        launch_disc_pct = (
            round((launch_price - cur_min) / launch_price * 100, 1)
            if launch_price and launch_price > cur_min else None
        )

        return {
            "data":            data,
            "search_data":     search_data,
            "tracked_product": tracked_product,
            "analysis": {
                "cur_min":          cur_min,
                "hist_avg":         hist_avg,
                "hist_min":         hist_min,
                "hist_max":         hist_max,
                "launch_price":     launch_price,
                "launch_disc_pct":  launch_disc_pct,
                "diff_pct":         diff_pct,
                "score":            score,
                "color":            color,
                "message":          msg,
                "trend_dir":        trend_dir,
                "low_day":          low_day,
                "has_history":      len(data) >= 2,
                "search_summary":   search_summary,
            },
        }
    except Exception as e:
        return {"data": [], "search_data": [], "analysis": None, "error": str(e)}


@router.get("/api/trend")
async def get_trend(category: str = Query(None)):
    try:
        groq_client = _get_groq()

        ALL_CATS = ["냉장고", "세탁기", "건조기", "에어컨", "공기청정기",
                    "로봇청소기", "식기세척기", "에어프라이어", "TV", "세탁건조기"]

        def quality(it):
            return it["reviewScore"] * math.log(it["reviewCount"] + 1, 10)

        def dl_diff(dl_data):
            if len(dl_data) < 14:
                return 0
            h = len(dl_data) // 2
            return (sum(d["ratio"] for d in dl_data[h:]) / max(len(dl_data[h:]), 1)
                  - sum(d["ratio"] for d in dl_data[:h]) / max(len(dl_data[:h]), 1))

        if category and category != "전체":
            products_data, datalab = await asyncio.gather(
                search_products(query=category, page=1, display=20, sort="sim", category=category),
                get_datalab(category),
                return_exceptions=True,
            )
            items_raw = (products_data.get("items", []) if not isinstance(products_data, Exception) else [])
            dl_data   = (datalab.get("data", [])        if not isinstance(datalab, Exception) else [])
            ts = dl_data[-1]["ratio"] if dl_data else 50
            td = round(dl_diff(dl_data), 1)
            items_raw.sort(key=quality, reverse=True)
            pool = [{**it, "category": category, "trend_score": ts, "trend_diff": td}
                    for it in items_raw[:10]]
        else:
            products_results = await asyncio.gather(
                *[search_products(query=cat, page=1, display=8, sort="sim", category=cat)
                  for cat in ALL_CATS],
                return_exceptions=True,
            )
            dl_results = []
            for cat in ALL_CATS:
                try:
                    res = await get_datalab(cat)
                    dl_results.append(res)
                except Exception:
                    dl_results.append({"data": []})
                await asyncio.sleep(0.15)

            all_items = []
            for cat, products_data, datalab in zip(ALL_CATS, products_results, dl_results):
                items = (products_data.get("items", []) if not isinstance(products_data, Exception) else [])
                dl    = (datalab.get("data", []) if isinstance(datalab, dict) else [])
                if dl:
                    ts = round(dl[-1]["ratio"], 1)
                    td = round(dl_diff(dl), 1)
                else:
                    q_scores = [quality(it) for it in items if it["price"] > 0]
                    max_q = max(q_scores, default=1) or 1
                    ts = round(min(quality(items[0]), max_q) / max_q * 100, 1) if items else 0
                    td = 0
                items.sort(key=quality, reverse=True)
                all_items.extend(
                    [{**it, "category": cat, "trend_score": ts, "trend_diff": td}
                     for it in items[:2]]
                )

            all_items.sort(
                key=lambda x: x["trend_score"] + x["trend_diff"] * 1.5 + quality(x) * 3,
                reverse=True,
            )
            pool = all_items[:10]

        if not pool:
            return {"items": []}

        product_text = "\n".join([
            f"[{i}]{p['category']}|{p['title'][:30]}|{p['price']//10000}만"
            for i, p in enumerate(pool)
        ])

        sys_msg = (
            f"오늘:{date.today()}. 각 제품이 트렌드인 이유 1문장(한국어). "
            "계절·생활패턴 반영, 범용표현 금지. "
            'JSON만 반환: {"items":[{"index":0,"reason":"문장","tag":"2단어"},...]}'
        )

        async def _ai_create():
            return await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": product_text},
                ],
                max_tokens=700,
                temperature=0.4,
                response_format={"type": "json_object"},
            )

        try:
            rec_res = await _ai_create()
        except Exception as ai_err:
            if "429" in str(ai_err):
                # 일일 토큰 한도 소진 시 sleep 재시도 불가 — AI 이유 없이 원본 반환
                logger.warning("[trend] Groq 429 — AI reason 생략: %s", ai_err)
                return {"items": pool}
            raise

        reasons = _parse_json(rec_res.choices[0].message.content).get("items", [])

        result = []
        for i, item in enumerate(pool):
            r = next((x for x in reasons if x.get("index") == i), {})
            result.append({**item, "reason": r.get("reason", ""), "tag": r.get("tag", "")})

        return {"items": result}

    except Exception as e:
        return {"items": [], "error": str(e)}


@router.get("/api/recommend")
async def get_recommend(query: str = Query(..., min_length=1)):
    try:
        groq_client = _get_groq()

        budget_match = re.search(r'(\d+(?:\.\d+)?)만원', query)
        budget_max = int(float(budget_match.group(1)) * 10000) if budget_match else None

        _ai_limited = False
        try:
            parse_res = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "사용자의 가전제품 구매 요구사항을 분석해서 JSON으로만 반환하세요.\n"
                            "【search_term 규칙】\n"
                            "search_term은 네이버 쇼핑에서 검색할 2~3단어입니다. 반드시 다음을 지키세요:\n"
                            "- 가격·금액·예산 표현(만원, 원, 이하, 이상 등)을 절대 포함하지 마세요\n"
                            "- 사용 환경(자취, 1인, 가족, 사무실 등)도 포함하지 마세요\n"
                            "- 제품 카테고리 + 핵심 스펙만 2~3단어로 추출하세요\n"
                            "예시) '에어컨 1인 자취용 30만원 이하' → search_term: '벽걸이 에어컨'\n"
                            "      '4인 가족 냉장고 200만원' → search_term: '양문형 냉장고'\n"
                            "      '로봇청소기 가성비 30만원 이하' → search_term: '로봇청소기'\n"
                            "【constraints 규칙】\n"
                            "사용 환경·공간·기능 조건을 constraints 배열에 넣으세요.\n"
                            '{"search_term": "카테고리+스펙 2~3단어", '
                            '"constraints": ["조건1", "조건2"]}'
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=700,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = _parse_json(parse_res.choices[0].message.content)
            search_term = parsed.get("search_term", query[:20]).strip()
            constraints = parsed.get("constraints", [])
        except Exception as parse_err:
            if "429" in str(parse_err):
                _ai_limited = True
                price_words = {"만원", "원", "이하", "이상", "미만"}
                search_term = " ".join(w for w in query.split() if w not in price_words)[:30]
                constraints = []
            else:
                raise

        detected_cat = next(
            (cat for cat in CATEGORY_RULES if cat in query or cat in search_term), None
        )
        products_data = await search_products(
            query=search_term, page=1, display=20, sort="sim",
            category=detected_cat,
        )
        items = products_data.get("items", [])

        if budget_max:
            import math as _math
            filtered = [it for it in items if it["price"] == 0 or it["price"] <= budget_max]
            if len(filtered) == 0:
                prices_gt0 = [it["price"] for it in items if it["price"] > 0]
                budget_wan = round(budget_max / 10000)
                if not prices_gt0:
                    return {
                        "recommendations": [],
                        "search_term": search_term,
                        "error": f"'{search_term}' 관련 제품을 찾지 못했어요. 검색어를 바꿔보거나 카테고리를 다시 선택해주세요.",
                    }
                min_price  = min(prices_gt0)
                min_wan    = _math.ceil(min_price / 10000)  # 올림: 30.4만 → 31만 (정확한 안내)
                suggest    = min_wan + (5 if min_wan < 100 else 10)
                return {
                    "recommendations": [],
                    "search_term": search_term,
                    "error": f"'{search_term}'의 최저가는 약 {min_wan}만원이에요. 예산을 {suggest}만원 이상으로 올려보세요!",
                }
            items = filtered

        items = items[:10]
        if not items:
            return {"recommendations": [], "search_term": search_term, "error": "관련 제품을 찾지 못했습니다"}

        def quality(it):
            return round(it["reviewScore"] * math.log(it["reviewCount"] + 1, 10), 2)

        product_list_text = "\n".join([
            f"[{i}] {it['title']} | {it['price']:,}원 | 평점 {it['reviewScore']}/5 | 리뷰 {it['reviewCount']:,}개 | 품질점수 {quality(it)}"
            for i, it in enumerate(items)
        ])
        constraint_text = "\n".join(f"- {c}" for c in constraints) if constraints else "- 특별 조건 없음"
        budget_text = f"{budget_max:,}원 이하" if budget_max else "제한 없음"

        if _ai_limited:
            top3 = sorted(items, key=lambda it: quality(it), reverse=True)[:3]
            return {
                "recommendations": [{**it, "reason": "", "highlight": ""} for it in top3],
                "search_term": search_term,
                "ai_limited": True,
            }

        try:
            rec_res = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 15년 경력의 가전제품 전문 컨설턴트입니다. 아래 규칙을 반드시 지켜 제품 3개를 추천하세요.\n"
                            "규칙:\n"
                            "1. 예산 초과 제품은 절대 추천하지 마세요\n"
                            "2. 품질점수(평점×log리뷰수)가 높은 제품을 우선 고려하세요\n"
                            "3. reason은 반드시 제품마다 달라야 합니다. 제품명·모델·평형수·브랜드 특성 등 이 제품만의 차별점을 언급하세요\n"
                            "4. '가격이 저렴하다', '에너지 효율이 높다' 처럼 모든 제품에 쓸 수 있는 범용 문장은 금지입니다\n"
                            "5. reason은 사용자의 핵심 조건(공간 크기·예산·기능 등)과 연결해 이 제품이 왜 적합한지 구체적으로 쓰세요 (한국어 1~2문장)\n"
                            "6. highlight도 제품마다 달라야 합니다. 이 제품만의 핵심 한 줄 장점 (2~4단어)\n"
                            "7. 1위가 가장 적합한 제품입니다\n"
                            "JSON으로만 응답:\n"
                            '{"recommendations": [{"index": 정수, "reason": "제품 고유 이유", "highlight": "고유 장점"}, ...]}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"[요구사항] {query}\n"
                            f"[예산] {budget_text}\n"
                            f"[핵심 조건]\n{constraint_text}\n\n"
                            f"[제품 목록]\n{product_list_text}"
                        ),
                    },
                ],
                max_tokens=700,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            rec_data = _parse_json(rec_res.choices[0].message.content)
            recommendations = rec_data.get("recommendations", [])
        except Exception as rec_err:
            if "429" in str(rec_err):
                top3 = sorted(items, key=lambda it: quality(it), reverse=True)[:3]
                return {
                    "recommendations": [{**it, "reason": "", "highlight": ""} for it in top3],
                    "search_term": search_term,
                    "ai_limited": True,
                }
            raise

        result = []
        for rec in recommendations[:3]:
            idx = rec.get("index", 0)
            if 0 <= idx < len(items):
                result.append({
                    **items[idx],
                    "reason":    rec.get("reason", ""),
                    "highlight": rec.get("highlight", ""),
                })

        return {"recommendations": result, "search_term": search_term}

    except Exception as e:
        err_str = str(e)
        if "429" in err_str:
            return {"recommendations": [], "error": "AI 분석 한도에 도달했습니다. 잠시 후 다시 시도해주세요."}
        return {"recommendations": [], "error": err_str}


@router.get("/api/report")
async def get_report(query: str = Query(..., min_length=1)):
    STOPWORDS = {"이하", "이상", "포함", "이내", "기준", "용", "형"}
    raw = [w for w in query.split() if re.search(r"[가-힣]", w) and w not in STOPWORDS]
    seen = []
    for w in raw:
        if not any(w in s or s in w for s in seen):
            seen.append(w)
    short_query = " ".join(seen[:3]) if seen else " ".join(query.split()[:2])
    dl_alt = " ".join(seen[2:4]) if len(seen) >= 4 else short_query

    results = await asyncio.gather(
        get_news(short_query, display=5),
        get_datalab(dl_alt),
        get_datalab(short_query),
        youtube_search(query, max_results=4),
        get_ppomppu(short_query),
        return_exceptions=True,
    )

    fallbacks = [{"items": []}, {"data": []}, {"data": []}, {"items": []}, {"items": []}]
    news, dl_alt_r, dl_main_r, youtube, ppomppu = [
        r if not isinstance(r, Exception) else fb
        for r, fb in zip(results, fallbacks)
    ]
    if len(dl_alt_r.get("data", [])) >= 10:
        datalab = dl_alt_r
        datalab_query = dl_alt
    else:
        datalab = dl_main_r
        datalab_query = short_query

    return {"news": news, "datalab": datalab, "youtube": youtube, "ppomppu": ppomppu, "datalab_query": datalab_query}


@router.get("/api/user-reviews")
async def get_user_reviews(query: str = Query(..., min_length=1)):
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    blog_url     = "https://openapi.naver.com/v1/search/blog.json"
    cafe_url     = "https://openapi.naver.com/v1/search/cafearticle.json"
    review_query = f"{query} 사용후기"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            blog_resp, cafe_resp = await asyncio.gather(
                client.get(blog_url, headers=NAVER_HEADERS, params={"query": review_query, "display": 8, "sort": "date"}),
                client.get(cafe_url, headers=NAVER_HEADERS, params={"query": review_query, "display": 5, "sort": "date"}),
            )

        reviews = []

        for item in blog_resp.json().get("items", []):
            text = strip_html(item.get("description", "")).strip()
            if len(text) < 30:
                continue
            reviews.append({
                "source": "블로그",
                "title":  strip_html(item.get("title", "")),
                "review": text[:200],
                "date":   item.get("postdate", ""),
                "link":   item.get("link", ""),
            })

        for item in cafe_resp.json().get("items", []):
            text = strip_html(item.get("description", "")).strip()
            if len(text) < 30:
                continue
            reviews.append({
                "source": "카페",
                "title":  strip_html(item.get("title", "")),
                "review": text[:200],
                "date":   item.get("postdate", ""),
                "link":   item.get("link", ""),
            })

        if rag:
            docs = [
                {
                    "text": f"[{r['source']}] {r['title']} - {r['review']}",
                    "metadata": {"source": r["source"], "product": query},
                }
                for r in reviews
            ]
            asyncio.create_task(rag.add_documents(docs))

        return {"reviews": reviews[:10]}

    except Exception as e:
        return {"reviews": [], "error": str(e)}


@router.get("/api/ai-analysis")
async def get_ai_analysis(query: str = Query(..., min_length=1)):
    try:
        from app.dependencies import get_rag_optional
        rag = get_rag_optional()
        groq_client = _get_groq()

        reviews_result, news_result = await asyncio.gather(
            get_user_reviews(query),
            get_news(query, display=5),
            return_exceptions=True,
        )

        user_reviews = [] if isinstance(reviews_result, Exception) else reviews_result.get("reviews", [])
        news_items   = [] if isinstance(news_result,    Exception) else news_result.get("items",   [])

        if rag:
            docs = []
            for r in user_reviews:
                if r.get("review"):
                    docs.append({
                        "text": f"[{r.get('source','')}] {r.get('title','')} - {r.get('review','')}",
                        "metadata": {"source": r.get("source", ""), "product": query},
                    })
            for n in news_items:
                docs.append({
                    "text": f"[뉴스] {n['title']} - {n.get('description','')}",
                    "metadata": {"source": "news", "product": query},
                })
            await rag.add_documents(docs)

        context_parts = []

        if rag:
            rag_chunks = await rag.query(f"{query} 구매 후기 장단점 특징", n_results=5)
            if rag_chunks:
                context_parts.append(
                    f"[RAG 검색 결과 — {query} 관련 문서 {len(rag_chunks)}개]\n"
                    + "\n".join(c[:_RAG_CHUNK_MAX] for c in rag_chunks)
                )

        if not context_parts:
            if user_reviews:
                lines = [
                    f"[{r.get('source', '')}] {r.get('title', '')} - {r.get('review', '')[:120]}"
                    for r in user_reviews[:12]
                    if r.get("review")
                ]
                if lines:
                    context_parts.append(f"[실사용자 후기 {len(lines)}개]\n" + "\n".join(lines))

            if news_items:
                lines = [f"- {n['title']}: {n.get('description', '')[:80]}" for n in news_items[:5]]
                context_parts.append("[최신 뉴스]\n" + "\n".join(lines))

        if not context_parts:
            return {"analysis": None, "reviews": [], "error": "분석할 데이터가 부족합니다"}

        res = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 가전제품 전문 구매 분석가입니다. 제공된 실제 구매 리뷰와 뉴스를 분석해서 구매 리포트 JSON을 작성하세요.\n"
                        "규칙:\n"
                        "1. 리뷰에 실제로 언급된 내용만 장단점으로 작성 (추측 금지)\n"
                        "2. pros/cons는 각 2~4개, 구체적으로\n"
                        "3. defects는 여러 리뷰에 반복 언급된 결함만 포함 (없으면 빈 배열)\n"
                        "4. recall은 뉴스에 명시적 리콜 언급이 있을 때만 true\n"
                        "5. score는 리뷰 평점과 내용을 종합해 1.0~5.0 소수점 한 자리\n"
                        "6. suitable_for는 실제 사용 후기 기반 구체적인 사용자 유형\n"
                        "반드시 JSON으로만 응답:\n"
                        '{"score": 4.2, "pros": ["장점1","장점2"], "cons": ["단점1","단점2"], '
                        '"defects": [], "recall": false, '
                        '"suitable_for": "추천 대상 1~2문장", '
                        '"cautions": ["주의사항1","주의사항2"], "summary": "종합 한줄평"}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"제품명: {query}\n\n" + "\n\n".join(context_parts),
                },
            ],
            max_tokens=700,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        analysis = _parse_json(res.choices[0].message.content)
        return {"analysis": analysis, "reviews": user_reviews[:10]}

    except Exception as e:
        return {"analysis": None, "reviews": [], "error": str(e)}


@router.get("/api/ai-compare")
async def ai_compare(
    q1: str = Query(..., min_length=1),
    q2: str = Query(..., min_length=1),
    _payload: dict = Depends(get_current_user),
):
    try:
        from app.dependencies import get_rag_optional
        rag = get_rag_optional()
        groq_client = _get_groq()

        r1, r2, n1, n2 = await asyncio.gather(
            get_user_reviews(q1),
            get_user_reviews(q2),
            get_news(q1, display=3),
            get_news(q2, display=3),
            return_exceptions=True,
        )

        def fmt_ctx(reviews_res, news_res, name):
            parts = [f"=== 제품: {name} ==="]
            reviews = [] if isinstance(reviews_res, Exception) else reviews_res.get("reviews", [])
            news    = [] if isinstance(news_res,    Exception) else news_res.get("items", [])
            if reviews:
                lines = [f"- {r.get('title','')} | {r.get('review','')[:100]}"
                         for r in reviews[:8] if r.get("review")]
                if lines:
                    parts.append("실사용 리뷰:\n" + "\n".join(lines))
            if news:
                parts.append("관련 뉴스:\n" + "\n".join(f"- {n['title']}" for n in news[:3]))
            return "\n".join(parts)

        if rag:
            docs = []
            for reviews_res, product_name in [(r1, q1), (r2, q2)]:
                reviews_list = [] if isinstance(reviews_res, Exception) else reviews_res.get("reviews", [])
                for r in reviews_list:
                    if r.get("review"):
                        docs.append({
                            "text": f"[{r.get('source','')}] {r.get('title','')} - {r.get('review','')}",
                            "metadata": {"source": r.get("source", ""), "product": product_name},
                        })
            await rag.add_documents(docs)

            chunks1, chunks2 = await asyncio.gather(
                rag.query(f"{q1} 특징 장단점 후기", n_results=5),
                rag.query(f"{q2} 특징 장단점 후기", n_results=5),
            )

            def fmt_rag(chunks, name):
                if not chunks:
                    return ""
                return f"=== {name} 관련 문서 ===\n" + "\n".join(chunks)

            context = fmt_rag(chunks1, q1) + "\n\n" + fmt_rag(chunks2, q2)
            if not context.strip():
                context = fmt_ctx(r1, n1, q1) + "\n\n" + fmt_ctx(r2, n2, q2)
        else:
            context = fmt_ctx(r1, n1, q1) + "\n\n" + fmt_ctx(r2, n2, q2)

        res = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 가전제품 전문 비교 분석가입니다. 두 제품의 리뷰와 뉴스를 분석해 비교 리포트 JSON을 작성하세요.\n"
                        "규칙:\n"
                        "1. 실제 언급된 내용만 장단점으로 (추측 금지)\n"
                        "2. pros/cons 각 2~3개, 구체적으로\n"
                        "3. winner는 0(첫번째 제품) 또는 1(두번째 제품) 또는 null(무승부)\n"
                        "4. 모든 텍스트는 반드시 한국어로\n"
                        "반드시 아래 JSON만 응답:\n"
                        '{"products":[{"pros":["장점1","장점2"],"cons":["단점1","단점2"],"score":4.2,"summary":"한줄요약"},{"pros":["장점1"],"cons":["단점1"],"score":3.8,"summary":"한줄요약"}],'
                        '"winner":0,"winner_reason":"승자 선택 이유 한 문장","verdict":"어떤 사용자에게 어떤 제품이 적합한지 2문장"}'
                    ),
                },
                {"role": "user", "content": f"비교 대상:\n제품1: {q1}\n제품2: {q2}\n\n수집 데이터:\n{context}"},
            ],
            temperature=0.3,
            max_tokens=700,
        )

        data = _parse_json(res.choices[0].message.content)
        return data
    except Exception as e:
        return {
            "products": [
                {"pros": [], "cons": [], "score": None, "summary": "분석 실패"},
                {"pros": [], "cons": [], "score": None, "summary": "분석 실패"},
            ],
            "winner": None,
            "winner_reason": "",
            "verdict": "AI 분석 중 오류가 발생했습니다.",
            "error": str(e),
        }


@router.get("/api/price-position")
async def get_price_position(
    category: str = Query(..., min_length=1),
    price:    int = Query(0),
):
    from app.database import fetchall

    rows = await fetchall(
        "SELECT snapshot_date, avg_price, min_price, max_price "
        "FROM price_history WHERE category = %s ORDER BY snapshot_date DESC LIMIT 2",
        (category,),
    )
    if not rows:
        return {"available": False}

    latest    = rows[0]
    avg_price = latest["avg_price"]
    min_price = latest["min_price"]
    max_price = latest["max_price"]

    price_range      = max(max_price - min_price, 1)
    position_pct     = max(0, min(100, round((price - min_price) / price_range * 100)))
    avg_position_pct = max(0, min(100, round((avg_price - min_price) / price_range * 100)))

    vs_avg_pct = round((price - avg_price) / max(avg_price, 1) * 100, 1) if price > 0 else None

    if price == 0 or vs_avg_pct is None:
        signal_type, signal = "neutral", "가격 정보 없음"
        reason = "현재 가격 정보를 확인할 수 없습니다"
    elif vs_avg_pct <= -5:
        signal_type, signal = "buy", "구매 추천"
        reason = f"카테고리 평균보다 {abs(vs_avg_pct):.1f}% 저렴합니다. 지금이 구매하기 좋은 시기입니다."
    elif vs_avg_pct >= 5:
        signal_type, signal = "wait", "관망 권장"
        reason = f"카테고리 평균보다 {vs_avg_pct:.1f}% 비쌉니다. 가격이 내려갈 때까지 기다려보세요."
    else:
        signal_type, signal = "neutral", "적정가"
        reason = "카테고리 평균 수준의 가격입니다."

    return {
        "available":        True,
        "avg_price":        avg_price,
        "min_price":        min_price,
        "max_price":        max_price,
        "position_pct":     position_pct,
        "avg_position_pct": avg_position_pct,
        "vs_avg_pct":       vs_avg_pct,
        "signal":           signal,
        "signal_type":      signal_type,
        "reason":           reason,
        "snapshot_date":    str(latest["snapshot_date"]),
    }
