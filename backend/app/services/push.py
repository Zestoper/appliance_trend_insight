"""FCM 푸시 알림.
Render 환경변수 FIREBASE_CREDENTIALS에 서비스 계정 키 JSON 내용 전체를 넣어 쓴다.
키가 없으면 푸시만 건너뛰고 나머지 기능은 그대로 동작한다."""
import asyncio
import json
import os

_app = None
_tried = False
_tasks: set = set()


def _firebase():
    """firebase_admin 앱을 처음 쓸 때 한 번만 만든다. 키가 없거나 잘못되면 None."""
    global _app, _tried
    if _tried:
        return _app
    _tried = True
    raw = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    if not raw:
        print("[push] FIREBASE_CREDENTIALS 없음 → 푸시 발송 안 함")
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        _app = firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    except Exception as e:
        print(f"[push] Firebase 초기화 실패: {type(e).__name__}: {e}")
        _app = None
    return _app


async def ensure_push_tables():
    """서버 시작 때 한 번 (ensure_account_tables에서 호출). 회원 탈퇴 시 토큰도 같이 지워진다."""
    from app.database import execute
    await execute(
        "CREATE TABLE IF NOT EXISTS push_tokens ("
        " token      TEXT PRIMARY KEY,"
        " user_id    BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,"
        " platform   VARCHAR(20) DEFAULT 'android',"
        " updated_at TIMESTAMPTZ DEFAULT NOW())"
    )
    await execute("CREATE INDEX IF NOT EXISTS idx_push_tokens_user ON push_tokens(user_id)")


async def save_token(user_id: int, token: str, platform: str = "android"):
    """같은 기기에서 다른 계정으로 로그인하면 토큰 주인을 새 계정으로 바꾼다."""
    from app.database import execute
    await execute(
        "INSERT INTO push_tokens (token, user_id, platform, updated_at) VALUES (%s, %s, %s, NOW()) "
        "ON CONFLICT (token) DO UPDATE SET user_id = EXCLUDED.user_id, "
        "platform = EXCLUDED.platform, updated_at = NOW()",
        (token, user_id, platform),
    )


async def delete_token(user_id: int, token: str) -> int:
    from app.database import execute
    return await execute("DELETE FROM push_tokens WHERE token = %s AND user_id = %s", (token, user_id))


def _send(tokens: list[str], title: str, body: str, data: dict, channel_id: str | None = None) -> list[str]:
    """실제 발송 (동기). 더 이상 쓸 수 없는 토큰 목록을 돌려준다.
    channel_id: 앱이 꺼져 있을 때 안드로이드가 알림을 띄울 채널 (없으면 앱 기본 채널 'account' = 회원 안내).
    앱 채널: price_alert(가격 알림) · account(회원 안내) — 사용자가 휴대폰 설정에서 채널별로 끌 수 있다."""
    from firebase_admin import messaging
    msg = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in data.items()},
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(channel_id=channel_id) if channel_id else None,
        ),
    )
    res = messaging.send_each_for_multicast(msg, app=_app)
    dead = []
    for tok, r in zip(tokens, res.responses):
        if not r.success and isinstance(r.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
            dead.append(tok)
        elif not r.success:
            print(f"[push] 발송 실패: {type(r.exception).__name__}: {r.exception}")
    return dead


async def send_to_user(user_id: int, title: str, body: str, data: dict | None = None,
                       channel_id: str | None = None) -> int:
    """회원의 모든 기기로 보낸다. 보낸 기기 수를 돌려준다 (키 없거나 토큰 없으면 0)."""
    if _firebase() is None:
        return 0
    from app.database import execute, fetchall
    rows = await fetchall("SELECT token FROM push_tokens WHERE user_id = %s", (user_id,))
    tokens = [r["token"] for r in rows]
    if not tokens:
        return 0
    dead = await asyncio.to_thread(_send, tokens, title, body, data or {}, channel_id)
    for tok in dead:
        await execute("DELETE FROM push_tokens WHERE token = %s", (tok,))
    return len(tokens) - len(dead)


def push_in_background(user_id: int, title: str, body: str, data: dict | None = None):
    """관리자 응답을 기다리게 하지 않도록 뒤에서 보낸다. 실패해도 로그만 남긴다."""
    async def run():
        try:
            await send_to_user(user_id, title, body, data)
        except Exception as e:
            print(f"[push] 푸시 실패 user={user_id}: {type(e).__name__}: {e}")
    task = asyncio.create_task(run())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
