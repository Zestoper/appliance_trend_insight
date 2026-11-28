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


# 렌탈 · 약정 상품: "60개월약정 월53700원"처럼 '렌탈' 단어 없이 월 요금만 적힌 상품이 현재가로 잡혔다
# (스탠바이미2 Max 127만원 → 53,700원) → 약정 · 의무사용 · 월 요금 표기를 빼낸다
_RENTAL_RE = re.compile(r'약정|의무\s*사용|월\s*[\d,]+\s*원|월\s*\d+\s*만\s*원')


def _is_rental(title: str) -> bool:
    return bool(_RENTAL_RE.search(title or ""))


def _pick_tracked(valid: list[dict], product_id: str | None, price: int, existing_keys: set) -> dict:
    """구매 타이밍에서 추적할 상품을 고른다.
    1) 앱이 보낸 제품 번호와 같은 상품
    2) 앱이 보낸 가격(목록에서 본 가격)이 있으면 그 0.5~2배 안의 상품 중 가격이 가장 가까운 것
       (예전엔 못 찾으면 이력 있는 아무 상품을 골라 렌탈 · 다른 모델 가격이 현재가가 됐다)
    3) 가격이 없으면 예전처럼 이력 있는 상품 → 첫 상품"""
    if product_id:
        same = next((it for it in valid if str(it["id"]) == str(product_id)), None)
        if same and (not price or price * 0.5 <= same["price"] <= price * 2):
            return same
    if price:
        near = [it for it in valid if price * 0.5 <= it["price"] <= price * 2]
        if near:
            return min(near, key=lambda it: abs(it["price"] - price))
    return next((it for it in valid if str(it["id"]) in existing_keys), valid[0])


@router.get("/api/timing")
async def get_timing(category: str = Query(..., min_length=1), product_id: str = Query(None),
                     price: int = Query(0, ge=0)):
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
        from app.utils.accessory_filter import is_accessory
        valid = [
            it for it in items
            if it["price"] > 0
            and not any(kw in it["title"] for kw in _EXCLUDE_KW)
            and not _is_rental(it["title"])
            and not is_accessory(it["title"], it["price"])     # 거름망 · 물걸레포 등 목록에 없는 소모품까지
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

        top = _pick_tracked(valid, product_id, price, existing_keys)
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
        if product_key.isdigit():   # 다나와 제품번호만 매일 가격 수집 대상으로 기록
            try:
                from app.services.tracking import touch_product
                await touch_product(product_key, product_name)
            except Exception as e:
                logger.warning("추적 제품 기록 실패 [%s]: %s", product_key, e)

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
        # hist_prices는 0원 행을 뺀 목록이라 그 인덱스로 rows를 찾으면 날짜가 어긋날 수 있다 → rows에서 직접 찾는다
        low_day   = next((str(r["snapshot_date"]) for r in rows if r["min_price"] == hist_min), str(rows[0]["snapshot_date"]))

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


# 트렌드 TOP10은 카테고리 10개 × (쇼핑 검색 + 데이터랩) + LLM 호출이라 한 번에 20초 넘게 걸리고
# Render 무료 서버에서 가끔 503으로 끊겼다. 값이 하루 단위로 바뀌는 데이터라 30분 캐시하고
# 새로 만들다 실패하면 직전 결과를 그대로 돌려준다.
#
# 메모리 캐시는 배포 · 재시작 때마다 사라져서 재시작 직후 첫 요청이 91초 걸렸다 (앱 대기 한도 90초).
# 그래서 결과를 DB(trend_cache)에도 저장하고, 오래된 결과라도 있으면 바로 돌려준 뒤
# 새 결과는 뒤에서 만든다. 결과가 하나도 없을 때(최초 1회)만 기다려서 만든다.
_TREND_TTL = 30 * 60
_trend_cache: dict[str, tuple[float, dict]] = {}
_trend_locks: dict[str, asyncio.Lock] = {}
_trend_refreshing: set[str] = set()
_trend_tasks: set[asyncio.Task] = set()   # 백그라운드 작업이 중간에 사라지지 않게 잡아둔다
_trend_table_ready = False


async def _trend_table():
    global _trend_table_ready
    if _trend_table_ready:
        return
    from app.database import execute
    await execute(
        "CREATE TABLE IF NOT EXISTS trend_cache ("
        " cache_key VARCHAR(50) PRIMARY KEY,"
        " payload TEXT NOT NULL,"
        " updated_at DOUBLE PRECISION NOT NULL)"
    )
    _trend_table_ready = True


async def _trend_db_load(key: str) -> tuple[float, dict] | None:
    try:
        from app.database import fetchone
        await _trend_table()
        row = await fetchone("SELECT payload, updated_at FROM trend_cache WHERE cache_key = %s", (key,))
        if row:
            return float(row["updated_at"]), _json.loads(row["payload"])
    except Exception as e:
        logger.warning("[trend] DB 캐시 읽기 실패 [%s]: %s", key, e)
    return None


async def _trend_db_save(key: str, ts: float, result: dict):
    try:
        from app.database import execute
        await _trend_table()
        await execute(
            "INSERT INTO trend_cache (cache_key, payload, updated_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (cache_key) DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at",
            (key, _json.dumps(result, ensure_ascii=False, default=str), ts),
        )
    except Exception as e:
        logger.warning("[trend] DB 캐시 저장 실패 [%s]: %s", key, e)


TREND_MIN_ITEMS = 8   # 전체 TOP10은 이 개수 이상일 때만 저장 (검색 몇 개가 실패해도 이전 결과를 지킨다)


def _trend_complete(key: str, result: dict | None) -> bool:
    items = (result or {}).get("items") or []
    return len(items) >= TREND_MIN_ITEMS if key == "전체" else bool(items)


async def _trend_refresh(key: str, category: str | None) -> dict | None:
    """새 트렌드를 만들어 메모리 · DB에 저장. 같은 카테고리는 동시에 한 번만 만든다."""
    lock = _trend_locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _trend_cache.get(key)
        if hit and datetime.now().timestamp() - hit[0] < _TREND_TTL and _trend_complete(key, hit[1]):
            return hit[1]
        from app.services.danawa_search import used_stored
        marks = []
        token = used_stored.set(marks)
        try:
            result = await _build_trend(category)
        finally:
            used_stored.reset(token)
        if marks:
            # 다나와가 안 돼서 저장된 결과로 만든 트렌드 — 다시 저장하면 저장 시각만 새것이 되므로 저장하지 않는다
            logger.warning("[trend] %s: 다나와 대신 저장된 결과로 만들어져 저장 안 함 (%d개 검색)", key, len(marks))
            if hit and hit[1].get("items"):
                return hit[1]
            return result if result.get("items") else None
        if _trend_complete(key, result):
            ts = datetime.now().timestamp()
            _trend_cache[key] = (ts, result)
            await _trend_db_save(key, ts, result)
            return result
        # 모자란 결과는 저장하지 않는다 (이전 10개를 2개짜리로 덮어쓰지 않도록) — 다음 요청 때 다시 만든다
        logger.warning("[trend] %s: 결과 %d개라 저장 안 함 (이전 결과 유지)", key, len(result.get("items") or []))
        if hit and _trend_complete(key, hit[1]):
            return hit[1]   # 오래됐어도 제대로 된 이전 결과
        return result if result.get("items") else None


def _trend_refresh_background(key: str, category: str | None):
    if key in _trend_refreshing:
        return

    async def run():
        from app.services.danawa_search import background_fetch
        background_fetch.set(True)   # 사용자 검색을 밀어내지 않도록 다나와 뒤쪽 줄 사용
        try:
            await _trend_refresh(key, category)
        except Exception as e:
            logger.warning("[trend] 백그라운드 갱신 실패 [%s]: %s", key, e)
        finally:
            _trend_refreshing.discard(key)

    _trend_refreshing.add(key)
    task = asyncio.create_task(run())
    _trend_tasks.add(task)
    task.add_done_callback(_trend_tasks.discard)


async def warm_trend_cache():
    """서버 시작 시 DB에 저장된 트렌드를 메모리로 올리고, 오래됐으면 뒤에서 새로 만든다."""
    hit = await _trend_db_load("전체")
    if hit and _trend_complete("전체", hit[1]):
        _trend_cache["전체"] = hit
    else:
        hit = None   # 없거나 모자라면 서버가 켜지자마자 새로 만든다 (첫 사용자는 진행 중인 결과를 기다린다)
    if not hit or datetime.now().timestamp() - hit[0] >= _TREND_TTL or not _trend_complete("전체", hit[1]):
        _trend_refresh_background("전체", None)


@router.get("/api/trend")
async def get_trend(category: str = Query(None)):
    key = category or "전체"
    cat = None if key == "전체" else category
    hit = _trend_cache.get(key)
    if not hit:
        hit = await _trend_db_load(key)
        if hit:
            _trend_cache[key] = hit
    if hit and not _trend_complete(key, hit[1]):
        hit = None   # 모자란 결과(예: 2개)는 사용자에게 보여주지 않는다 → 아래에서 제대로 만든 결과를 기다린다
    if hit:
        if datetime.now().timestamp() - hit[0] >= _TREND_TTL:
            _trend_refresh_background(key, cat)   # 오래됐으면 일단 보여주고 뒤에서 새로 만든다
        return hit[1]
    # 저장된 결과가 전혀 없을 때만 기다려서 만든다
    result = await _trend_refresh(key, cat)
    return result or {"items": []}


async def _build_trend(category: str | None):
    # 트렌드는 다나와 검색 10개를 한꺼번에 하는 묶음 작업 → 사용자 검색을 밀어내지 않게 뒤쪽 줄을 쓰고
    # 줄 서는 시간을 시간 초과로 세지 않는다 (처음 만들 때 사용자가 기다리는 경우에도 같다)
    from app.services.danawa_search import background_fetch
    token = background_fetch.set(True)
    try:
        return await _build_trend_inner(category)
    finally:
        background_fetch.reset(token)


async def _build_trend_inner(category: str | None):
    try:
        from app.routers.b2b_utils import _groq_create as _gc

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

            failed = [cat for cat, r in zip(ALL_CATS, products_results)
                      if isinstance(r, Exception) or not (r or {}).get("items")]
            if failed:
                logger.warning("[trend] 전체: %d개 중 %d개 검색 실패 %s", len(ALL_CATS), len(failed), failed)
                print(f"[trend] 전체: {len(ALL_CATS)}개 중 {len(failed)}개 검색 실패 {failed}")

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

            def rank_key(x):
                return x["trend_score"] + x["trend_diff"] * 1.5 + quality(x) * 3

            all_items.sort(key=rank_key, reverse=True)
            pool = all_items[:10]
            # 화면의 '트렌드 지수'를 순위 기준과 같은 값(1위 = 100)으로 보여준다.
            # 예전에는 카테고리 검색량(trend_score)만 보여줘서 4위가 100, 2위가 90처럼 순위와 숫자가 어긋났다
            top = rank_key(pool[0]) if pool else 1
            pool = [{**x, "rank_score": round(max(rank_key(x), 0) / max(top, 1) * 100)} for x in pool]

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

        try:
            rec_res = await _gc(
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": product_text},
                ],
                max_tokens=2000,
                temperature=0.4,
            )
        except Exception as ai_err:
            logger.warning("[trend] AI reason 생략: %s", ai_err)
            return {"items": pool}

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
        from app.routers.b2b_utils import _groq_create as _gc

        budget_match = re.search(r'(\d+(?:\.\d+)?)만원', query)
        budget_max = int(float(budget_match.group(1)) * 10000) if budget_match else None

        _ai_limited = False
        try:
            parse_res = await _gc(
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
                max_tokens=2000,
                temperature=0.1,
            )
            parsed = _parse_json(parse_res.choices[0].message.content)
            search_term = parsed.get("search_term", query[:20]).strip()
            constraints = parsed.get("constraints", [])
        except Exception:
            _ai_limited = True
            price_words = {"만원", "원", "이하", "이상", "미만"}
            search_term = " ".join(w for w in query.split() if w not in price_words)[:30]
            constraints = []

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
            rec_res = await _gc(
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
                max_tokens=2000,
                temperature=0.2,
            )
            rec_data = _parse_json(rec_res.choices[0].message.content)
            recommendations = rec_data.get("recommendations", [])
        except Exception:
            top3 = sorted(items, key=lambda it: quality(it), reverse=True)[:3]
            return {
                "recommendations": [{**it, "reason": "", "highlight": ""} for it in top3],
                "search_term": search_term,
                "ai_limited": True,
            }

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


# ── 제품 관련 뉴스 ──
# 예전에는 상품명에서 한글 단어만 골라 뉴스를 찾아서 "삼성전자 AI Q9000 AF60F17D11GS"는 "삼성전자"만,
# "로보락 S9 MaxV Ultra"는 "로보락"만 검색됐다 → 그 회사의 인사 · 주식 · 분양 기사가 나왔다.
# 이제는 "브랜드 + 품목"(예: 삼성전자 에어컨)으로 정확도순 검색한 뒤 품목 이름이 들어간 기사만 남긴다.

_NEWS_CAT_ALIASES = {
    "에어컨": ["에어컨", "냉난방기", "냉방기"],
    "세탁기": ["세탁기", "워시타워", "워시콤보"],
    "전기밥솥": ["밥솥"],
    "TV": ["TV", "티비", "텔레비전"],
    "전기히터": ["히터"],
    "블루투스 스피커": ["스피커"],
}


def _category_from_text(text: str):
    from app.config import _CATEGORY_MAP
    for kw, cat in _CATEGORY_MAP.items():
        if kw in text:
            return cat
    return None


async def _guess_category(clean: str, hint: str | None = None):
    """품목과 (상품명에 없으면) 브랜드를 정한다.
    앱 · 웹이 아는 품목(hint)을 보내면 그걸 먼저 쓴다 (예: "로보락 S9 MaxV Ultra"는 제목에 품목 이름이 없다).
    그다음 상품명 · 쇼핑 검색 결과 제목 순으로 정한다."""
    cat = _category_from_text(hint) if hint else None   # 아는 품목 이름일 때만 (웹 기본값 "제품" 등은 무시)
    cat = cat or _category_from_text(clean)
    brand = _brand_from_title(clean)
    if cat and brand:
        return cat, brand
    try:
        res = await search_products(query=_model_from_title(clean) or _short_name(clean), page=1, display=10, sort="sim", category=None)
        titles = [it.get("title", "") for it in res.get("items", [])]
    except Exception:
        titles = []
    if not cat:
        votes: dict[str, int] = {}
        for t in titles:
            c = _category_from_text(t)
            if c:
                votes[c] = votes.get(c, 0) + 1
        cat = max(votes, key=votes.get) if votes else None
    if not brand and titles:
        brand = _brand_from_title(titles[0])
    return cat, brand


def _brand_from_title(clean: str):
    """상품명 첫 단어를 브랜드로 본다. 모델명처럼 생긴 단어면 브랜드 없음."""
    words = _short_name(clean).split()
    if not words:
        return None
    first = words[0]
    if _HYPHEN_MODEL_RE.match(first.upper()) or (re.search(r"\d", first) and re.search(r"[A-Za-z]", first)):
        return None
    return first


def _series_from_title(clean: str, brand: str | None, category: str) -> list[str]:
    """시리즈 이름들.
    - 브랜드 · 품목 말고 남는 첫 한글 단어 (예: 퓨리케어 · 비스포크 · 무풍 · 휘센)
    - 영문 + 숫자로 된 짧은 시리즈명 (예: 로보락 S9 · 삼성 Q9000) — 전체 모델명은 기사에 거의 안 나와서 제외"""
    skip = {brand or "", category, *(_NEWS_CAT_ALIASES.get(category, [])), "스탠드", "벽걸이", "인버터", "가정용", "일반", "삼성", "엘지"}
    out: list[str] = []
    words = _short_name(clean).split()
    for w in words:
        if re.fullmatch(r"[가-힣]{2,}", w) and w not in skip and not _category_from_text(w):
            out.append(w)
            break
    for w in words:
        if 2 <= len(w) <= 6 and re.search(r"[A-Za-z]", w) and re.search(r"\d", w):
            out.append(w)
            break
    return out


async def _product_news(query: str, display: int = 5, category_hint: str | None = None) -> dict:
    """브랜드 + 품목으로 찾은 제품 관련 뉴스. 품목을 모르면 엉뚱한 기사 대신 빈 목록.
    기사 제목에 품목 이름이나 시리즈 이름이 있어야 남긴다 — 본문에 '정수기 · 공기청정기 등'처럼
    지나가듯 나오는 회사 기사(인사 · 구독 · 디자인상)는 뺀다."""
    clean = strip_html(query)
    category, brand = await _guess_category(clean, category_hint)
    if not category:
        return {"items": [], "news_query": None}
    news_query = f"{brand} {category}" if brand else category
    aliases = _NEWS_CAT_ALIASES.get(category, [category]) + _series_from_title(clean, brand, category)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://openapi.naver.com/v1/search/news.json", headers=NAVER_HEADERS,
                                    params={"query": news_query, "display": 30, "sort": "sim"})
        items, seen_titles = [], set()
        for it in resp.json().get("items", []):
            title = strip_html(it.get("title", ""))
            desc = strip_html(it.get("description", ""))
            text = f"{title} {desc}"
            if not any(a in title for a in aliases):       # 제목에 품목 · 시리즈 이름이 없는 기사 제외
                continue
            # 같은 기사가 [포토] 등으로 두 번 오는 경우 → 말머리를 떼고 제목이 같으면 하나만
            key = re.sub(r"^\[[^\]]*\]\s*|\W", "", title)
            if key in seen_titles:
                continue
            seen_titles.add(key)
            items.append({
                "title":       title,
                "description": desc,
                "pubDate":     it.get("pubDate", ""),
                "link":        it.get("originallink") or it.get("link", ""),
                "_brand":      bool(brand and brand in text),
                "_ts":         _news_ts(it.get("pubDate", "")),
            })
        # 브랜드까지 맞는 기사 먼저 · 그 안에서는 최신순
        items.sort(key=lambda x: (x["_brand"], x["_ts"]), reverse=True)
        for x in items:
            x.pop("_brand"); x.pop("_ts")
        return {"items": items[:display], "news_query": news_query}
    except Exception:
        return {"items": [], "news_query": news_query}


def _news_ts(pub: str) -> float:
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub).timestamp()
    except Exception:
        return 0.0


@router.get("/api/report")
async def get_report(query: str = Query(..., min_length=1), category: str | None = Query(None)):
    STOPWORDS = {"이하", "이상", "포함", "이내", "기준", "용", "형"}
    # 단어 분리 후 후행 구두점 제거 (예: "일반배관," → "일반배관")
    raw = [re.sub(r'[^\w가-힣A-Za-z0-9]+$', '', w) for w in query.split()]
    raw = [w for w in raw if re.search(r"[가-힣]", w) and w not in STOPWORDS and w]
    seen = []
    for w in raw:
        if not any(w in s or s in w for s in seen):
            seen.append(w)
    short_query = " ".join(seen[:3]) if seen else " ".join(query.split()[:2])
    dl_alt = " ".join(seen[2:4]) if len(seen) >= 4 else short_query
    # 최후 폴백: 마지막 단어만 (보통 제품 카테고리명 — 브랜드명보다 검색량 많음)
    dl_simple = seen[-1] if seen else short_query

    results = await asyncio.gather(
        _product_news(query, display=5, category_hint=category),
        get_datalab(dl_alt),
        get_datalab(short_query),
        get_datalab(dl_simple),
        youtube_search(query, max_results=4),
        get_ppomppu(short_query),
        return_exceptions=True,
    )

    fallbacks = [{"items": []}, {"data": []}, {"data": []}, {"data": []}, {"items": []}, {"items": []}]
    news, dl_alt_r, dl_main_r, dl_simple_r, youtube, ppomppu = [
        r if not isinstance(r, Exception) else fb
        for r, fb in zip(results, fallbacks)
    ]
    # 데이터 포인트가 가장 많은 쿼리 결과 선택 (최소 2개 이상이어야 차트 렌더 가능)
    if len(dl_alt_r.get("data", [])) >= 10:
        datalab, datalab_query = dl_alt_r, dl_alt
    elif len(dl_main_r.get("data", [])) >= 2:
        datalab, datalab_query = dl_main_r, short_query
    elif len(dl_simple_r.get("data", [])) >= 2:
        datalab, datalab_query = dl_simple_r, dl_simple
    else:
        datalab, datalab_query = dl_main_r, short_query

    return {"news": news, "datalab": datalab, "youtube": youtube, "ppomppu": ppomppu, "datalab_query": datalab_query}


# ── 실사용자 후기 검색 ──
# 예전에는 '제품 이름 전체 + 사용후기'를 최신순(date)으로 8+5개만 가져와서 다른 모델 글 ·
# 특가 홍보 글이 그대로 AI 분석과 RAG에 들어갔다. 이제는 정확도순(sim)으로 넉넉히 가져온 뒤
# 모델명(없으면 제품 이름 핵심 단어)이 실제로 들어간 글만 남긴다. (B2B 분석과 같은 방식)

_BRACKET_RE  = re.compile(r"\[[^\]]*\]|\([^)]*\)|【[^】]*】|<[^>]*>")
_UNIT_RE     = re.compile(r"\b\d+(?:\.\d+)?\s*(?:L|l|리터|kg|KG|㎏|인치|형|W|w|평|구|인용|도어|단)\b")
_NOISE_WORDS = {"정품", "공식", "공식인증", "신제품", "신형", "최신형", "무료배송", "무료설치", "당일발송",
                "빠른배송", "국내정품", "사은품", "증정", "특가", "단독", "추천", "인기", "사용후기", "후기"}


def _short_name(title: str) -> str:
    """쇼핑 상품명에서 괄호 · 용량 · 홍보 문구를 걷어내고 앞쪽 핵심 단어 4개만 남긴다."""
    t = _BRACKET_RE.sub(" ", strip_html(title))
    t = _UNIT_RE.sub(" ", t)
    t = re.sub(r"[^\w가-힣\s-]", " ", t)
    words = [w for w in t.split() if w not in _NOISE_WORDS and len(w) >= 2]
    return " ".join(words[:4]) or strip_html(title)[:30]


def _key_tokens(title: str) -> list[str]:
    """관련성 확인용 핵심 단어 (브랜드 · 시리즈 · 품목)."""
    return [w for w in _short_name(title).split() if len(w) >= 2]


def _norm(text: str) -> str:
    return re.sub(r"[\s\-_]", "", text).upper()


_HYPHEN_MODEL_RE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")


def _model_from_title(clean: str):
    """모델명 추출. CRP-LHTR0610FW처럼 하이픈이 있는 모델명은 통째로 쓰고 없으면 B2B와 같은 규칙."""
    from app.routers.b2b_search_analysis import _extract_model_broad
    for raw in re.split(r"[\s()\[\]{},/]+", clean.upper()):
        tok = raw.strip("-_.")
        if 8 <= len(tok) <= 20 and _HYPHEN_MODEL_RE.match(tok) and re.search(r"[A-Z]", tok) and re.search(r"\d", tok):
            return tok
    return _extract_model_broad(clean)


def _model_keys(model: str) -> list[str]:
    """비교용 모델명. 정확한 모델명 다음에 끝 2 · 4글자를 뗀 앞부분 (최소 6자).
    블로거는 AF60F17D11GS를 AF60F17D11처럼 색상 · 구성 글자를 빼고 쓰는 일이 많다.
    (앱 ModelNameExtractor.shorterQueries와 같은 방식)"""
    full = _norm(model)
    keys = [full]
    for cut in (2, 4):
        k = full[:-cut]
        if len(k) >= 6 and k not in keys:
            keys.append(k)
    return keys


def _review_query_and_filter(query: str):
    """검색어 · 넓힌 검색어 · '이 글이 이 제품 얘기인가' 판단 함수를 만든다.
    relevant(title, text, level): level 0은 정확한 모델명 · 1 이상은 앞부분까지 허용."""
    from app.routers.b2b_search_analysis import _PROMO_KW

    clean = strip_html(query)
    model = _model_from_title(clean)
    tokens = _key_tokens(clean)
    need = min(2, len(tokens))
    keys = _model_keys(model) if model else []

    def relevant(title: str, text: str, level: int = 0) -> bool:
        if any(k in title or k in text for k in _PROMO_KW):
            return False
        body = _norm(f"{title} {text}")
        if model:
            return any(k in body for k in keys[: level + 1])
        return sum(_norm(tok) in body for tok in tokens) >= need

    base = model or _short_name(clean)
    # 넓힌 검색어는 원래 표기(하이픈 포함)에서 끝 4글자를 뗀 것 (예: AF60F17D11GS → AF60F17D)
    wider = None
    if model and len(keys) > 1:
        cut = model[: max(len(model) - 4, 6)].rstrip("-_.")
        wider = f"{cut} 사용후기" if len(_norm(cut)) >= 6 else None
    return f"{base} 사용후기", wider, relevant, len(keys)


@router.get("/api/user-reviews")
async def get_user_reviews(query: str = Query(..., min_length=1)):
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    review_query, wider_query, relevant, levels = _review_query_and_filter(query)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            items = await _search_reviews(client, review_query)
            reviews = _pick_reviews(items, relevant, levels)
            # 정확히 맞는 글이 거의 없으면 모델명 앞부분으로 한 번 더 찾는다
            if len(reviews) < 3 and wider_query and wider_query != review_query:
                more = await _search_reviews(client, wider_query)
                seen = {r["link"] for r in reviews}
                reviews += [r for r in _pick_reviews(more, relevant, levels) if r["link"] not in seen]

        # 걸러낸 후기만 RAG에 저장한다 (다른 제품 글이 쌓여 다음 분석을 오염시키지 않도록)
        if rag and reviews:
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


async def _search_reviews(client, review_query: str) -> list[tuple[str, dict]]:
    """네이버 블로그 20 · 카페 10개를 정확도순으로 가져온다."""
    blog_resp, cafe_resp = await asyncio.gather(
        client.get("https://openapi.naver.com/v1/search/blog.json", headers=NAVER_HEADERS,
                   params={"query": review_query, "display": 20, "sort": "sim"}),
        client.get("https://openapi.naver.com/v1/search/cafearticle.json", headers=NAVER_HEADERS,
                   params={"query": review_query, "display": 10, "sort": "sim"}),
    )
    return ([("블로그", it) for it in blog_resp.json().get("items", [])]
            + [("카페", it) for it in cafe_resp.json().get("items", [])])


def _pick_reviews(items: list[tuple[str, dict]], relevant, levels: int) -> list[dict]:
    """정확한 모델명 글부터 고르고 3개가 안 되면 모델명 앞부분이 맞는 글까지 넓힌다."""
    rows = []
    for source, item in items:
        title = strip_html(item.get("title", ""))
        text = strip_html(item.get("description", "")).strip()
        if len(text) < 30:
            continue
        rows.append((source, title, text, item))

    picked: list[dict] = []
    for level in range(max(levels, 1)):
        for source, title, text, item in rows:
            link = item.get("link", "")
            if any(p["link"] == link for p in picked) or not relevant(title, text, level):
                continue
            picked.append({
                "source": source,
                "title":  title,
                "review": text[:200],
                "date":   item.get("postdate", ""),
                "link":   link,
            })
        if len(picked) >= 3:
            break
    return picked


# ── AI 분석 결과 캐시 ─────────────────────────────────────────────
# 예전에는 같은 제품을 다시 열어도 후기 · 뉴스 검색 → RAG → AI 호출을 매번 처음부터 해서 6~13초 걸렸다 (#71).
# 메모리에 먼저 두고 DB(naver_cache)에도 남겨서 서버를 다시 켜도 그대로 쓴다.
# 같은 제품 분석이 동시에 두 번 들어오면 (앱 · 웹 동시 · 새로고침) AI를 한 번만 부른다.
_AI_CACHE_TTL_HOURS = 12
_AI_CACHE_VER = "v1"
_AI_CACHE: dict[str, tuple[float, dict]] = {}
_AI_CACHE_MAX = 300
_AI_INFLIGHT: dict[str, asyncio.Future] = {}


def _ai_cache_key(query: str, category: str | None) -> str:
    q = re.sub(r"\s+", " ", (query or "").strip())
    return f"ai-analysis:{_AI_CACHE_VER}:{(category or '').strip()}:{q}"[:300]


@router.get("/api/ai-analysis")
async def get_ai_analysis(query: str = Query(..., min_length=1), category: str | None = Query(None)):
    import time as _t
    key = _ai_cache_key(query, category)

    hit = _AI_CACHE.get(key)
    if hit and _t.time() < hit[0]:
        return hit[1]

    from app.services.naver_cache import get_db_cache, set_db_cache
    try:
        stored = await get_db_cache(key)
    except Exception:
        stored = None
    if stored and stored.get("analysis"):
        _remember_ai(key, stored)
        return stored

    running = _AI_INFLIGHT.get(key)
    if running:
        return await asyncio.shield(running)

    fut = asyncio.get_running_loop().create_future()
    _AI_INFLIGHT[key] = fut
    try:
        result = await _compute_ai_analysis(query, category)
        if result.get("analysis"):   # 실패 · 데이터 부족은 저장하지 않는다 (다음에 다시 시도)
            _remember_ai(key, result)
            try:
                await set_db_cache(key, result, ttl_hours=_AI_CACHE_TTL_HOURS)
            except Exception as e:
                logger.warning("[ai-analysis] 캐시 저장 실패: %s", e)
        fut.set_result(result)
        return result
    except asyncio.CancelledError:
        fut.cancel()   # 기다리던 쪽도 같이 끝낸다 (그쪽은 다음 요청에서 새로 계산)
        raise
    except Exception as e:
        fut.set_exception(e)
        fut.exception()   # 기다리는 쪽이 없어도 '처리 안 된 예외' 경고가 나지 않게
        raise
    finally:
        _AI_INFLIGHT.pop(key, None)


def _remember_ai(key: str, result: dict) -> None:
    import time as _t
    if len(_AI_CACHE) >= _AI_CACHE_MAX:
        _AI_CACHE.pop(min(_AI_CACHE, key=lambda k: _AI_CACHE[k][0]), None)
    _AI_CACHE[key] = (_t.time() + _AI_CACHE_TTL_HOURS * 3600, result)


async def _compute_ai_analysis(query: str, category: str | None) -> dict:
    try:
        from app.dependencies import get_rag_optional
        from app.routers.b2b_utils import _groq_create as _gc
        rag = get_rag_optional()

        reviews_result, news_result = await asyncio.gather(
            get_user_reviews(query),
            _product_news(query, display=5, category_hint=category),
            return_exceptions=True,
        )

        user_reviews = [] if isinstance(reviews_result, Exception) else reviews_result.get("reviews", [])
        news_items   = [] if isinstance(news_result,    Exception) else news_result.get("items",   [])

        if rag:
            # 후기는 get_user_reviews가 걸러서 이미 RAG에 넣는다 → 여기서는 뉴스만 (중복 저장 방지)
            docs = []
            for n in news_items:
                docs.append({
                    "text": f"[뉴스] {n['title']} - {n.get('description','')}",
                    "metadata": {"source": "news", "product": query},
                })
            if docs:
                # 임베딩 호출이 1~2초 걸려서 응답을 기다리게 하지 않는다 (이번 분석에는 뉴스를 아래에서 직접 넣는다)
                asyncio.create_task(rag.add_documents(docs))

        # 방금 이 검색어로 직접 가져온 실사용자 후기·뉴스가 있으면 그게 가장 구체적이고
        # 정확한 근거라 항상 먼저 넣는다. RAG 검색 결과는 이걸 대체하지 않고 보조 참고
        # 자료로만 덧붙인다 — RAG가 "냉장고" 같은 넓은 카테고리 시딩 문서를 (실제로는
        # 관련성이 낮은데도) 건져오면, 방금 확보한 구체적인 후기를 아예 못 보고 AI가
        # "데이터 부족"이라고 잘못 판단하는 문제가 있었다.
        context_parts = []

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

        if rag:
            rag_chunks = await rag.query(f"{query} 구매 후기 장단점 특징", n_results=5)
            if rag_chunks:
                context_parts.append(
                    f"[참고 자료 — {query} 관련 문서 {len(rag_chunks)}개]\n"
                    + "\n".join(c[:_RAG_CHUNK_MAX] for c in rag_chunks)
                )

        if not context_parts:
            return {"analysis": None, "reviews": [], "error": "분석할 데이터가 부족합니다"}

        res = await _gc(
            [
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
            max_tokens=2000,
            temperature=0.3,
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
        from app.routers.b2b_utils import _groq_create as _gc

        r1, r2, n1, n2 = await asyncio.gather(
            get_user_reviews(q1),
            get_user_reviews(q2),
            _product_news(q1, display=3),
            _product_news(q2, display=3),
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

        # 방금 확보한 구체적인 실사용 리뷰·뉴스를 항상 먼저 넣고, RAG는 보조 참고
        # 자료로만 덧붙인다 (get_ai_analysis와 동일한 이유 — RAG 단독으로는 넓은
        # 카테고리 시딩 문서만 걸려 정작 구체적인 후기가 프롬프트에서 빠질 수 있음).
        context = fmt_ctx(r1, n1, q1) + "\n\n" + fmt_ctx(r2, n2, q2)

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
                return f"=== {name} 관련 참고 자료 ===\n" + "\n".join(chunks)

            rag_context = fmt_rag(chunks1, q1) + "\n\n" + fmt_rag(chunks2, q2)
            if rag_context.strip():
                context += "\n\n" + rag_context

        res = await _gc(
            [
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
            max_tokens=2000,
            temperature=0.3,
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
