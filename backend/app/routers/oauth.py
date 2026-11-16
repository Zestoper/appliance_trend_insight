"""소셜 로그인 (구글 · 카카오) — OAuth2 Authorization Code Flow

흐름
  1. 프론트 버튼 → GET /api/auth/{provider}/login → 구글/카카오 로그인 화면으로 이동
  2. 로그인 후 구글/카카오가 GET /api/auth/{provider}/callback?code=...&state=... 로 돌려보냄
  3. code 를 구글/카카오 access token 으로 바꾸고, 그 토큰으로 사용자 정보(id · 이메일 · 이름) 조회
  4. 연결된 계정이 있으면 그 계정, 없으면 같은 이메일 계정에 연결, 그것도 없으면 새로 가입
  5. 기존 이메일 로그인과 똑같은 자체 JWT 를 만들어 프론트 /oauth/callback#token=... 으로 보냄

필요한 환경변수
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
  KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET(카카오 콘솔에서 켰을 때만)
  BACKEND_URL   — 이 서버 주소 (콜백 주소를 만들 때 사용)
  FRONTEND_URL  — 로그인 후 돌아갈 프론트 주소
"""
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from jose import jwt

from app.auth import make_token, hash_password, JWT_SECRET, JWT_ALGORITHM

router = APIRouter(prefix="/api/auth", tags=["oauth"])

BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

PROVIDERS = {
    "google": {
        "client_id":     os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url":     "https://oauth2.googleapis.com/token",
        "userinfo_url":  "https://openidconnect.googleapis.com/v1/userinfo",
        "scope":         "openid email profile",
    },
    "kakao": {
        "client_id":     os.getenv("KAKAO_REST_API_KEY", ""),
        "client_secret": os.getenv("KAKAO_CLIENT_SECRET", ""),  # 콘솔에서 '사용'으로 켰을 때만 필요
        "authorize_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url":     "https://kauth.kakao.com/oauth/token",
        "userinfo_url":  "https://kapi.kakao.com/v2/user/me",
        # scope 를 비워두면 카카오는 콘솔 '동의항목'에서 켜둔 항목만 요청한다.
        # 직접 적으면 콘솔에서 안 켠 항목(예: 비즈 앱이 아니라 잠긴 이메일)이 섞일 때 KOE205 오류가 난다.
        "scope":         "",
    },
}


def _callback_url(provider: str) -> str:
    # 구글/카카오 콘솔에 등록한 Redirect URI 와 글자 하나까지 같아야 한다
    return f"{BACKEND_URL}/api/auth/{provider}/callback"


def _fail(message: str) -> RedirectResponse:
    """실패하면 로그인 화면으로 돌려보내고 화면에 안내 문구를 띄운다."""
    return RedirectResponse(f"{FRONTEND_URL}/login?oauth_error={quote(message)}")


# ── CSRF 방지용 state ────────────────────────────────────────────────────────
# 프론트(Vercel)와 백엔드(Render) 도메인이 달라 쿠키 세션을 쓰기 어렵다.
# 그래서 서버 비밀키로 서명한 10분짜리 토큰을 state 로 보내고, 돌아올 때 서명을 검증한다.
# → 우리 서버가 시작하지 않은 로그인 요청(위조)은 콜백에서 거절된다.
def _make_state(provider: str) -> str:
    return jwt.encode(
        {"p": provider, "n": secrets.token_urlsafe(8), "exp": datetime.utcnow() + timedelta(minutes=10)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def _state_ok(state: str, provider: str) -> bool:
    try:
        return jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM]).get("p") == provider
    except Exception:
        return False


# ── 구글/카카오 사용자 정보 → 공통 형식 ─────────────────────────────────────
def _normalize(provider: str, raw: dict) -> dict:
    if provider == "google":
        return {
            "provider_id":    raw["sub"],
            "email":          (raw.get("email") or "").lower() or None,
            "email_verified": bool(raw.get("email_verified")),
            "name":           raw.get("name") or "",
        }
    account = raw.get("kakao_account") or {}
    return {
        "provider_id":    str(raw["id"]),
        # 사용자가 이메일 제공에 동의하지 않으면 없을 수 있다
        "email":          (account.get("email") or "").lower() or None,
        "email_verified": bool(account.get("is_email_valid") and account.get("is_email_verified")),
        "name":           (account.get("profile") or {}).get("nickname") or "",
    }


async def _ensure_table():
    from app.database import execute
    await execute(
        "CREATE TABLE IF NOT EXISTS user_social_accounts ("
        " provider    VARCHAR(20)  NOT NULL,"
        " provider_id VARCHAR(255) NOT NULL,"
        " user_id     BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,"
        " created_at  TIMESTAMPTZ DEFAULT NOW(),"
        " PRIMARY KEY (provider, provider_id))"
    )


async def _find_or_create_user(provider: str, info: dict) -> dict:
    from app.database import fetchone, execute, get_user_by_email, create_user, create_b2c_profile
    await _ensure_table()

    # 1) 이미 연결된 소셜 계정
    row = await fetchone(
        "SELECT u.* FROM user_social_accounts s JOIN users u ON u.user_id = s.user_id "
        "WHERE s.provider = %s AND s.provider_id = %s",
        (provider, info["provider_id"]),
    )
    if row:
        return row

    # 2) 같은 이메일로 가입한 계정이 있으면 연결
    #    구글/카카오가 '인증된 이메일'이라고 확인해 준 경우만 — 아니면 남의 계정에 붙을 수 있다
    user = None
    if info["email"] and info["email_verified"]:
        user = await get_user_by_email(info["email"])

    # 3) 없으면 새로 가입 (일반 회원)
    if not user:
        # users.email 은 비울 수 없고 중복도 안 되므로, 이메일을 못 받았으면 고유한 자리표시 주소를 넣는다
        email = info["email"] if info["email"] and not await get_user_by_email(info["email"]) \
            else f"{provider}_{info['provider_id']}@social.local"
        # 비밀번호로는 로그인할 수 없도록 아무도 모르는 임의 값을 해시해서 넣는다
        user_id = await create_user(email, hash_password(secrets.token_urlsafe(32)), "b2c")
        await create_b2c_profile(user_id, (info["name"] or "회원")[:100])
        user = await fetchone("SELECT * FROM users WHERE user_id = %s", (user_id,))

    await execute(
        "INSERT INTO user_social_accounts (provider, provider_id, user_id) VALUES (%s, %s, %s) "
        "ON CONFLICT DO NOTHING",
        (provider, info["provider_id"], user["user_id"]),
    )
    return user


@router.get("/{provider}/login")
async def social_login(provider: str):
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return _fail("지원하지 않는 로그인 방식입니다")
    if not cfg["client_id"]:
        return _fail(f"{provider} 로그인이 아직 설정되지 않았습니다")
    params = {
        "client_id":     cfg["client_id"],
        "redirect_uri":  _callback_url(provider),
        "response_type": "code",
        "state":         _make_state(provider),
    }
    if cfg["scope"]:
        params["scope"] = cfg["scope"]
    if provider == "google":
        params["prompt"] = "select_account"  # 여러 구글 계정 중 고를 수 있게
    return RedirectResponse(f"{cfg['authorize_url']}?{urlencode(params)}")


@router.get("/{provider}/callback")
async def social_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return _fail("지원하지 않는 로그인 방식입니다")
    if error or not code:
        return _fail("로그인이 취소되었습니다")
    if not _state_ok(state, provider):
        return _fail("로그인 요청이 만료되었습니다. 다시 시도해주세요")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            data = {
                "grant_type":   "authorization_code",
                "client_id":    cfg["client_id"],
                "redirect_uri": _callback_url(provider),
                "code":         code,
            }
            if cfg["client_secret"]:
                data["client_secret"] = cfg["client_secret"]
            token_res = await client.post(cfg["token_url"], data=data, headers={"Accept": "application/json"})
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            me_res = await client.get(cfg["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"})
            me_res.raise_for_status()
            info = _normalize(provider, me_res.json())
    except Exception as e:
        body = getattr(getattr(e, "response", None), "text", "")[:300]
        print(f"[oauth] {provider} 토큰/사용자 조회 실패: {type(e).__name__}: {e} {body}")
        return _fail("소셜 로그인에 실패했습니다. 잠시 후 다시 시도해주세요")

    try:
        user = await _find_or_create_user(provider, info)
    except Exception as e:
        print(f"[oauth] {provider} 계정 처리 실패: {type(e).__name__}: {e}")
        return _fail("계정 처리 중 오류가 발생했습니다")

    # 이메일 로그인과 같은 계정 상태 검사
    if not user.get("is_active", True):
        return _fail("비활성화된 계정입니다")
    if user.get("status") == "pending":
        return _fail("사업자 인증 검토 중인 계정입니다")
    if user.get("status") == "rejected":
        return _fail("사업자 인증이 거절되었습니다. 관리자에게 문의해주세요")

    token = make_token(user["user_id"], user["user_type"], role=user.get("role", "user"))
    # 토큰은 # 뒤(fragment)에 붙인다 — 브라우저가 서버로 보내지 않아 접속 기록(로그)에 남지 않는다
    return RedirectResponse(f"{FRONTEND_URL}/oauth/callback#token={token}")
