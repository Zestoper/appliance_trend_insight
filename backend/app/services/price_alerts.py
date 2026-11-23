"""가격 알림 (개인 · 사업자 모두 목표가 알림 · 사업자는 등급별 개수).

2026-11-23: B2B는 실제 데이터만 보여주기로 해서 매입 신호(매입 추천 · 관망) 푸시와 목록 표시를 껐다.
신호 계산과 기록은 그대로 둬서 나중에 기준을 다시 세우면 SIGNAL_PUSH만 켜면 된다.

- 등록 · 목록 · 삭제는 /api/user/alerts (routers/user.py)
- 매일 한 번 서버가 알림 걸린 제품 가격을 다시 확인하고 조건이 맞으면 FCM 푸시를 보낸다
  (예전에는 앱이 하루 한 번 직접 확인했다 → 안드로이드 절전 때문에 가끔 건너뛰었다)
- 현재가 · 역대 평균 · 매입 신호는 검색 분석 화면과 같은 함수(build_price_block)로 계산한다
  → 분석 화면 · 알림 목록 · 푸시의 결론이 서로 달라지지 않는다
"""
import asyncio
import json
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

# 사업자 등급별 가격 알림 개수
TIER_LIMITS = {"free": 3, "silver": 10, "gold": 30, "platinum": 100}
TIER_LABELS = {"free": "무료", "silver": "실버", "gold": "골드", "platinum": "플래티넘"}
PERSONAL_LIMIT = 20          # 개인 회원 (등급 없음)
MAX_DAILY_PRODUCTS = 200     # 매일 확인하는 제품 수 상한 (Render 512MB · tracked_products 150개와 별도)
RECENT_ANALYZED_DAYS = 14     # B2B 분석에서 최근 이 기간 안에 열린 모델도 매일 가격을 모은다
MAX_ANALYZED_PRODUCTS = 80    # 그중 최대 (알림 걸린 제품이 먼저)
SIGNAL_PUSH = False          # 매입 신호 푸시 · 목록 표시 (실제 데이터만 보여주기로 해서 끔)
SIGNAL_COOLDOWN_DAYS = 7     # 매입 적기 푸시는 같은 알림에 7일에 한 번만
HISTORY_POINTS = 60          # 목록 그래프 점 개수

SIGNAL_LABELS = {"buy": "매입 추천", "wait": "관망 권장", "avoid": "매입 추천하지 않음"}


async def ensure_alert_tables():
    """서버 시작 때 한 번 (ensure_account_tables에서 호출)."""
    from app.database import execute
    for col, typ in [
        ("product_key", "TEXT"), ("model_number", "TEXT"), ("category", "TEXT"), ("image", "TEXT"),
        ("last_signal_type", "VARCHAR(10)"),        # 마지막 확인 때 신호 (바뀌는 순간을 잡으려고)
        ("last_notified_price", "INTEGER"),         # 목표가 푸시를 보낸 가격 (더 내려가야 다시 보냄)
        ("signal_notified_at", "TIMESTAMPTZ"),      # 매입 적기 푸시를 보낸 시각
        ("triggered_at", "TIMESTAMPTZ"),
    ]:
        await execute(f"ALTER TABLE price_alert ADD COLUMN IF NOT EXISTS {col} {typ}")
    await execute("ALTER TABLE price_alert ALTER COLUMN target_price DROP NOT NULL")   # 사업자는 목표가 선택
    await execute("CREATE INDEX IF NOT EXISTS idx_price_alert_key ON price_alert(product_key)")
    await execute(
        "CREATE TABLE IF NOT EXISTS product_signal_state ("
        " product_key    TEXT PRIMARY KEY,"
        " category       TEXT,"
        " image          TEXT,"
        " min_price      INTEGER,"
        " hist_avg_price INTEGER,"
        " vs_hist_pct    REAL,"
        " signal_type    VARCHAR(10),"
        " demand_slope   REAL DEFAULT 0,"     # 검색 분석 때 관심도 추세 (매일 확인은 이 값을 쓴다)
        " history        TEXT,"               # [{date, min_price}] JSON
        " updated_at     TIMESTAMPTZ DEFAULT NOW())"
    )
    await execute("ALTER TABLE product_signal_state ADD COLUMN IF NOT EXISTS product_name TEXT")
    await execute("ALTER TABLE product_signal_state ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMPTZ")


# ── 신호 상태 (검색 분석 · 매일 확인이 저장 · 목록이 읽음) ─────────────────────

async def save_signal_state(product_key: str, block: dict, slope: float | None,
                            category: str | None, image: str | None,
                            product_name: str | None = None, viewed: bool = False):
    """viewed=True: B2B 분석 화면에서 연 것 (매일 가격 모으기 대상이 된다)"""
    from app.database import execute
    history = [{"date": h["date"], "min_price": h["min_price"]} for h in block.get("price_history", [])][-HISTORY_POINTS:]
    await execute(
        "INSERT INTO product_signal_state "
        "(product_key, category, image, min_price, hist_avg_price, vs_hist_pct, signal_type, demand_slope, history, updated_at,"
        " product_name, viewed_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, CASE WHEN %s THEN NOW() END) "
        "ON CONFLICT (product_key) DO UPDATE SET "
        " product_name = COALESCE(EXCLUDED.product_name, product_signal_state.product_name),"
        " viewed_at = COALESCE(EXCLUDED.viewed_at, product_signal_state.viewed_at),"
        " category = COALESCE(EXCLUDED.category, product_signal_state.category),"
        " image = COALESCE(EXCLUDED.image, product_signal_state.image),"
        " min_price = EXCLUDED.min_price, hist_avg_price = EXCLUDED.hist_avg_price,"
        " vs_hist_pct = EXCLUDED.vs_hist_pct, signal_type = EXCLUDED.signal_type,"
        " demand_slope = EXCLUDED.demand_slope, history = EXCLUDED.history, updated_at = NOW()",
        (product_key, category, image or None, block["min_price"], block["hist_avg_price"],
         block["vs_hist_pct"], block["signal_type"], float(slope or 0), json.dumps(history),
         (product_name or None) and product_name[:300], bool(viewed)),
    )


async def mark_checked_no_price(product_key: str, product_name: str | None, category: str | None):
    """가격을 못 찾았어도 '확인했다'는 시각은 남긴다 → 앱이 '확인 중'과 '확인하지 못했어요'를 구분한다.
    이미 가격이 있는 제품은 그 가격 · 시각을 그대로 둔다 (못 찾은 날 때문에 마지막 실제 가격을 지우지 않음)."""
    from app.database import execute
    await execute(
        "INSERT INTO product_signal_state (product_key, category, product_name, updated_at) "
        "VALUES (%s, %s, %s, NOW()) "
        "ON CONFLICT (product_key) DO UPDATE SET updated_at = CASE WHEN product_signal_state.min_price IS NULL "
        "THEN NOW() ELSE product_signal_state.updated_at END",
        (product_key, category, (product_name or None) and product_name[:300]),
    )


async def _states(keys: list) -> dict:
    from app.database import fetchall
    keys = sorted({k for k in keys if k})
    if not keys:
        return {}
    rows = await fetchall("SELECT * FROM product_signal_state WHERE product_key = ANY(%s)", (keys,))
    return {r["product_key"]: r for r in rows}


async def alert_id_for(user_id: int, product_key: str):
    from app.database import fetchone
    row = await fetchone(
        "SELECT alert_id FROM price_alert WHERE user_id = %s AND product_key = %s AND is_active = TRUE "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id, product_key),
    )
    return row["alert_id"] if row else None


# ── 회원 구분 ──────────────────────────────────────────────────────────────

async def is_business(user_id: int) -> bool:
    """승인된 사업자만 매입 신호를 받는다 (승인 대기 · 거절이면 개인 회원처럼 목표가 알림)."""
    from app.database import fetchone
    row = await fetchone("SELECT user_type, status FROM users WHERE user_id = %s", (user_id,))
    return bool(row) and row["user_type"] == "b2b" and (row.get("status") or "active") == "active"


def _detect_category(*texts):
    from app.routers.b2b_utils import _CATEGORY_MAP
    for text in texts:
        for kw, cat in _CATEGORY_MAP.items():
            if text and kw in text:
                return cat
    return None


# ── 목록 · 등록 ─────────────────────────────────────────────────────────────

def _history(raw) -> list:
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def list_alerts(user_id: int) -> list:
    from app.database import fetchall
    rows = await fetchall(
        "SELECT * FROM price_alert WHERE user_id = %s AND is_active = TRUE ORDER BY created_at DESC", (user_id,),
    )
    business = await is_business(user_id)
    states = await _states([r.get("product_key") for r in rows])
    out = []
    for r in rows:
        item = dict(r)
        for k in ("last_signal_type", "last_notified_price", "signal_notified_at"):   # 서버 내부 기록
            item.pop(k, None)
        st = states.get(r.get("product_key") or "")
        if not st and r.get("product_key"):
            # 예전에 등록돼 아직 한 번도 확인 안 된 알림 → 뒤에서 한 번 확인 (같은 제품은 10분에 한 번)
            _refresh_soon(r["product_key"], r["product_name"], r.get("category"))
        item["min_price"] = st["min_price"] if st else None                 # 지금 최저가 (마지막 확인 기준)
        item["last_updated"] = st["updated_at"].isoformat() if st and st.get("updated_at") else None
        if not item.get("image") and st:
            item["image"] = st.get("image")
        if business:
            if SIGNAL_PUSH:
                item["signal_type"] = st["signal_type"] if st else None
                item["signal"] = SIGNAL_LABELS.get(st["signal_type"]) if st else None
            item["vs_hist_pct"] = st["vs_hist_pct"] if st else None
            item["hist_avg_price"] = st["hist_avg_price"] if st else None
            item["history"] = _history(st["history"]) if st else []
        out.append(item)
    return out


async def create_alert(user_id: int, product_name: str, target_price, current_price,
                       product_url: str, alert_type: str, hint: str = "", image=None) -> dict:
    from app.database import fetchone, get_user_tier, _execute_returning
    from app.routers.b2b_search_analysis import product_key_for

    name = (product_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="제품명을 입력해 주세요")
    business = await is_business(user_id)
    if target_price is not None and target_price <= 0:
        target_price = None
    # 매입 신호 알림을 꺼서 목표가 없는 알림은 아무것도 보내지 않는다 → 사업자도 목표가 필수
    if target_price is None:
        raise HTTPException(status_code=400, detail="목표 가격을 입력해 주세요")

    model, product_key = product_key_for(name)
    dup = await fetchone(
        "SELECT alert_id FROM price_alert WHERE user_id = %s AND is_active = TRUE "
        "AND (product_key = %s OR product_name = %s) LIMIT 1",
        (user_id, product_key, name),
    )
    if dup:
        raise HTTPException(status_code=409, detail="이미 등록된 알림입니다")

    count = (await fetchone(
        "SELECT COUNT(*) AS n FROM price_alert WHERE user_id = %s AND is_active = TRUE", (user_id,),
    ))["n"]
    if business:
        tier = await get_user_tier(user_id)
        limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        if count >= limit:
            # 앱 Play 결제 정책 때문에 결제 · 구독 안내는 넣지 않는다
            raise HTTPException(status_code=402,
                                detail=f"가격 알림은 {TIER_LABELS.get(tier, '무료')} 등급에서 {limit}개까지 등록할 수 있어요")
    elif count >= PERSONAL_LIMIT:
        raise HTTPException(status_code=400, detail=f"가격 알림은 {PERSONAL_LIMIT}개까지 등록할 수 있어요")

    state = (await _states([product_key])).get(product_key) or {}
    category = state.get("category") or _detect_category(name, hint)
    alert_id = await _execute_returning(
        "INSERT INTO price_alert (user_id, product_name, target_price, current_price, product_url, alert_type, "
        " product_key, model_number, category, image, last_signal_type) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING alert_id",
        # 등록할 때 이미 매입 적기여도 바로 푸시하지 않는다 (신호가 '바뀔 때' 알림)
        (user_id, name[:500], target_price, current_price or 0, product_url or "", alert_type or "below",
         product_key, model, category, image or state.get("image"), state.get("signal_type")),
    )
    if not state.get("min_price"):
        # 처음 보는 제품은 다음 날 새벽 확인 전까지 '지금 가격'이 비어 있었다 (앱: "확인하지 못했어요")
        # → 등록 직후 뒤에서 한 번 확인해 둔다 (푸시는 보내지 않음 · 몇 초 뒤 목록을 다시 열면 보인다)
        _refresh_soon(product_key, name, category)
    items = [a for a in await list_alerts(user_id) if a["alert_id"] == alert_id]
    return items[0] if items else {"alert_id": alert_id}


_bg_tasks: set = set()
_last_refresh: dict = {}          # product_key → 마지막으로 뒤에서 확인을 시작한 시각 (monotonic)
REFRESH_GAP_SEC = 600


def _refresh_soon(product_key: str, name: str, category: str | None):
    import time
    now = time.monotonic()
    if now - _last_refresh.get(product_key, -1e9) < REFRESH_GAP_SEC:
        return
    _last_refresh[product_key] = now
    _spawn(refresh_product_state(name, category))


def _spawn(coro):
    try:
        t = asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        coro.close()
        return
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)


async def refresh_product_state(name: str, category: str | None = None) -> dict | None:
    """제품 하나의 지금 가격을 확인해 product_signal_state에 저장한다 (매일 확인과 같은 계산)."""
    from app.routers.b2b_search_analysis import product_key_for, fetch_product_price_items, build_price_block
    from app.services.price_service import get_danawa_price_history
    from app.services.danawa_search import background_fetch
    model, key = product_key_for(name)
    token = background_fetch.set(True)
    try:
        items = await fetch_product_price_items(model or name)
        try:
            danawa = await get_danawa_price_history(model or name, name, only_real_launch=True)
        except Exception:
            danawa = {"history": [], "launch_price": None}
        block, _, image, _ = await build_price_block(name, model, key, category, items, danawa, 0.0, date.today())
        if block:
            await save_signal_state(key, block, 0.0, category, image, product_name=name)
        else:
            print(f"[alerts] 바로 확인: {name[:24]} 가격 못 찾음")
            await mark_checked_no_price(key, name, category)
        return block
    except Exception as e:
        print(f"[alerts] 바로 확인 실패 {name[:24]}: {type(e).__name__}: {e}")
        try:
            await mark_checked_no_price(key, name, category)
        except Exception:
            pass
        return None
    finally:
        background_fetch.reset(token)


# ── 매일 확인 · 푸시 ────────────────────────────────────────────────────────

def _won(n) -> str:
    return f"{int(n):,}원"


async def _evaluate(row: dict, block: dict, now: datetime):
    """알림 하나를 오늘 가격으로 판단해 DB 상태를 고치고, 보낼 푸시가 있으면 (reason, 제목, 내용)."""
    from app.database import execute
    price = int(block["min_price"])
    sig = block["signal_type"]
    business = row["user_type"] == "b2b" and (row.get("status") or "active") == "active"
    name = row["product_name"][:40]
    push = None

    # 목표가: 처음 내려갔을 때 · 지난번 알린 가격보다 더 내려갔을 때만.
    # 목표가 위로 다시 올라가면 기록을 지워서 다음에 내려올 때 또 알린다
    target = row.get("target_price")
    last_price = row.get("last_notified_price")
    if target and price <= int(target):
        if last_price is None or price < int(last_price):
            push = ("target", "목표 가격 도달", f"{name} 지금 {_won(price)} (목표 {_won(target)})")
            await execute("UPDATE price_alert SET last_notified_price = %s, triggered_at = NOW() WHERE alert_id = %s",
                          (price, row["alert_id"]))
    elif last_price is not None:
        await execute("UPDATE price_alert SET last_notified_price = NULL WHERE alert_id = %s", (row["alert_id"],))

    # 매입 신호 (승인된 사업자만): 다른 상태 → buy 로 바뀐 순간 · 같은 알림은 7일에 한 번
    prev = row.get("last_signal_type")
    if SIGNAL_PUSH and business and sig == "buy" and prev is not None and prev != "buy":
        sent = row.get("signal_notified_at")
        if sent is not None and sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        if sent is None or now - sent >= timedelta(days=SIGNAL_COOLDOWN_DAYS):
            if push is None:   # 같은 날 목표가 푸시가 가면 하나만 보낸다
                pct = abs(block["vs_hist_pct"])
                push = ("signal", "매입 적기 알림", f"{name} 지금 {_won(price)} · 역대 평균보다 {pct}% 저렴해요")
            await execute("UPDATE price_alert SET signal_notified_at = NOW() WHERE alert_id = %s", (row["alert_id"],))
    if prev != sig:
        await execute("UPDATE price_alert SET last_signal_type = %s WHERE alert_id = %s", (sig, row["alert_id"]))
    return push


async def check_price_alerts():
    """하루 한 번 (price_service.price_snapshot_loop가 매일 수집 뒤에 run_once_per_day로 부른다).
    메모리가 부족해 중간에 멈추면 False → 완료 기록이 안 남아 다음에 다시 돈다
    (이미 보낸 푸시는 DB에 기록돼 있어 두 번 가지 않는다)."""
    from app.database import fetchall, execute
    from app.routers.b2b_search_analysis import product_key_for, fetch_product_price_items, build_price_block
    from app.services.price_service import get_danawa_price_history, MEMORY_LIMIT_MB
    from app.services.danawa_search import background_fetch
    from app.services.push import send_to_user
    from app.utils.memory import trim

    rows = await fetchall(
        "SELECT pa.*, u.user_type, u.status FROM price_alert pa JOIN users u ON u.user_id = pa.user_id "
        "WHERE pa.is_active = TRUE AND COALESCE(u.is_active, TRUE) ORDER BY pa.created_at",
    )

    groups: dict = {}
    for r in rows:
        r = dict(r)
        key = r.get("product_key")
        if not key:   # 예전에 등록한 알림은 제품 키가 없다 → 지금 규칙으로 채운다
            model, key = product_key_for(r["product_name"])
            await execute("UPDATE price_alert SET product_key = %s, model_number = %s WHERE alert_id = %s",
                          (key, model, r["alert_id"]))
        groups.setdefault(key, []).append(r)
    keys = sorted(groups, key=lambda k: -len(groups[k]))
    # 알림은 없지만 최근 B2B 분석에서 열린 모델도 매일 가격을 모은다
    # (화면에 '매일 가격을 모으고 있어요'라고 안내하는데 예전엔 누가 다시 열 때만 한 줄 쌓였다)
    analyzed = await fetchall(
        "SELECT product_key, product_name, category FROM product_signal_state "
        "WHERE viewed_at >= NOW() - make_interval(days => %s) AND product_name IS NOT NULL "
        "ORDER BY viewed_at DESC LIMIT %s",
        (RECENT_ANALYZED_DAYS, MAX_ANALYZED_PRODUCTS),
    )
    for a in analyzed:
        if a["product_key"] not in groups:
            groups[a["product_key"]] = [{"product_name": a["product_name"], "category": a.get("category"),
                                         "_no_alert": True}]
            keys.append(a["product_key"])
    if len(keys) > MAX_DAILY_PRODUCTS:
        print(f"[alerts] 제품 {len(keys)}개 중 {MAX_DAILY_PRODUCTS}개만 확인 (상한)")
        keys = keys[:MAX_DAILY_PRODUCTS]

    states = await _states(keys)
    token = background_fetch.set(True)   # 사용자 검색을 밀어내지 않도록 다나와 뒤쪽 줄 사용
    sent = 0
    try:
        for n, key in enumerate(keys, 1):
            if trim() > MEMORY_LIMIT_MB:
                print(f"[alerts] 메모리 보호로 중단 ({n - 1}/{len(keys)}) · 다음에 서버가 깨어나면 이어서")
                return False
            first = groups[key][0]
            name = first["product_name"]
            model, _ = product_key_for(name)
            st = states.get(key) or {}
            category = first.get("category") or st.get("category") or _detect_category(name)
            try:
                items = await fetch_product_price_items(model or name)
                try:
                    danawa = await get_danawa_price_history(model or name, name, only_real_launch=True)
                except Exception:
                    danawa = {"history": [], "launch_price": None}
                slope = st.get("demand_slope") or 0.0
                block, _, image, _ = await build_price_block(name, model, key, category, items, danawa,
                                                             slope, date.today())
                if not block:
                    print(f"[alerts] {name[:24]} 가격 못 찾음 → 건너뜀")
                    await mark_checked_no_price(key, name, category)
                    continue
                await save_signal_state(key, block, slope, category, image)
                now = datetime.now(timezone.utc)
                for row in groups[key]:
                    if row.get("_no_alert"):   # 가격만 모으는 제품
                        continue
                    push = await _evaluate(row, block, now)
                    if push:
                        reason, title, body = push
                        await send_to_user(row["user_id"], title, body,
                                           {"type": "price_alert", "alert_id": str(row["alert_id"]), "reason": reason})
                        sent += 1
            except Exception as e:
                print(f"[alerts] {name[:24]} 확인 실패: {type(e).__name__}: {e}")
                try:
                    await mark_checked_no_price(key, name, category)
                except Exception:
                    pass
            trim()
            await asyncio.sleep(1.2)
    finally:
        background_fetch.reset(token)
    print(f"[alerts] 제품 {len(keys)}개 확인 · 푸시 {sent}건")
    return True
