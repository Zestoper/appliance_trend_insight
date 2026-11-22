"""소셜 로그인 (구글 · 카카오) — OAuth2 Authorization Code Flow

흐름
  1. 프론트 버튼 → GET /api/auth/{provider}/login → 구글/카카오 로그인 화면으로 이동
  2. 로그인 후 구글/카카오가 GET /api/auth/{provider}/callback?code=...&state=... 로 돌려보냄
  3. code 를 구글/카카오 access token 으로 바꾸고, 그 토큰으로 사용자 정보(id · 이메일 · 이름) 조회
  4. 연결된 계정이 있으면 그 계정, 없으면 같은 이메일 계정에 연결
  5. 기존 이메일 로그인과 똑같은 자체 JWT 를 만들어 프론트 /oauth/callback#token=... 으로 보냄
  6. 처음 온 사람은 바로 가입시키지 않고 /oauth/callback#signup=가입티켓 으로 보낸다
     → 프론트 약관 동의 화면 → POST /api/auth/social/complete 에서 동의를 확인하고 가입

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
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
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


async def _find_user(provider: str, info: dict) -> dict | None:
    """이미 연결된 계정 또는 같은 (인증된) 이메일의 기존 계정. 없으면 None → 약관 동의 후 새로 가입."""
    from app.database import fetchone, execute, get_user_by_email
    await _ensure_table()

    # 1) 이미 연결된 소셜 계정
    row = await fetchone(
        "SELECT u.* FROM user_social_accounts s JOIN users u ON u.user_id = s.user_id "
        "WHERE s.provider = %s AND s.provider_id = %s",
        (provider, info["provider_id"]),
    )
    if row:
        return row

    # 2) 같은 이메일로 가입한 계정이 있으면 연결 (그 회원은 가입할 때 이미 약관에 동의했다)
    #    구글/카카오가 '인증된 이메일'이라고 확인해 준 경우만 — 아니면 남의 계정에 붙을 수 있다
    if info["email"] and info["email_verified"]:
        user = await get_user_by_email(info["email"])
        if user:
            await execute(
                "INSERT INTO user_social_accounts (provider, provider_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (provider, info["provider_id"], user["user_id"]),
            )
            return user
    return None


async def _create_social_user(provider: str, info: dict, nickname: str) -> dict:
    """약관 동의를 받은 뒤 새 회원을 만든다 (일반 회원). 회원 · 프로필 · 소셜 연결 · 약관 기록이 한 트랜잭션"""
    from app.database import fetchone, get_user_by_email
    from app.routers.auth import create_member
    # users.email 은 비울 수 없고 중복도 안 되므로, 이메일을 못 받았으면 고유한 자리표시 주소를 넣는다
    email = info["email"] if info["email"] and not await get_user_by_email(info["email"]) \
        else f"{provider}_{info['provider_id']}@social.local"
    # 비밀번호로는 로그인할 수 없도록 아무도 모르는 임의 값을 해시해서 넣는다
    user_id = await create_member(
        email, hash_password(secrets.token_urlsafe(32)), "b2c",
        nickname=(nickname or info["name"] or "회원")[:100],
        social=(provider, info["provider_id"]),
    )
    return await fetchone("SELECT * FROM users WHERE user_id = %s", (user_id,))


def _account_blocked(user: dict) -> str | None:
    """이메일 로그인과 같은 계정 상태 검사. 막혀 있으면 안내 문구"""
    if not user.get("is_active", True):
        return "비활성화된 계정입니다"
    return None


# ── 소셜 첫 가입: 약관 동의 화면 ──────────────────────────────────────────
# 처음 오는 사람은 바로 가입시키지 않고, 서버가 서명한 15분짜리 '가입 티켓'을 들려
# 프론트 /oauth/callback#signup=... 으로 보낸다. 프론트가 약관 동의 화면을 보여주고
# 동의하면 POST /api/auth/social/complete 로 티켓을 보내 그때 가입시킨다.
# (티켓에 소셜 회원 번호가 서명돼 있어서 다른 사람이 위조할 수 없다)
SIGNUP_TICKET_MINUTES = 15


def _make_signup_ticket(provider: str, info: dict) -> str:
    return jwt.encode(
        {
            "purpose": "social_signup", "p": provider, "id": info["provider_id"],
            "email": info["email"], "ev": info["email_verified"], "name": info["name"],
            "exp": datetime.utcnow() + timedelta(minutes=SIGNUP_TICKET_MINUTES),
        },
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def _read_signup_ticket(ticket: str) -> tuple[str, dict] | None:
    try:
        d = jwt.decode(ticket, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
    if d.get("purpose") != "social_signup" or d.get("p") not in PROVIDERS:
        return None
    return d["p"], {"provider_id": d["id"], "email": d.get("email"),
                    "email_verified": bool(d.get("ev")), "name": d.get("name") or ""}


class SocialCompleteRequest(BaseModel):
    ticket: str
    agree_terms: bool = False
    nickname: str | None = None


@router.post("/social/complete")
async def social_complete(body: SocialCompleteRequest):
    """소셜 첫 가입 마무리 — 약관에 동의해야 회원이 만들어진다. 웹과 앱이 같이 쓴다."""
    from app.routers.auth import _require_terms
    read = _read_signup_ticket(body.ticket)
    if not read:
        raise HTTPException(status_code=400, detail="가입 시간이 지났어요. 소셜 로그인을 다시 해주세요")
    _require_terms(body.agree_terms)
    provider, info = read
    # 두 번 눌렀거나 그 사이 다른 창에서 가입됐으면 새로 만들지 않고 그 계정으로 로그인
    user = await _find_user(provider, info) or await _create_social_user(provider, info, (body.nickname or "").strip())
    token = make_token(user["user_id"], user["user_type"], role=user.get("role", "user"))
    return {"token": token, "user_type": user["user_type"]}


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
        user = await _find_user(provider, info)
    except Exception as e:
        print(f"[oauth] {provider} 계정 처리 실패: {type(e).__name__}: {e}")
        return _fail("계정 처리 중 오류가 발생했습니다")

    if not user:
        # 처음 온 사람 → 약관 동의 화면으로 (가입은 동의한 뒤에)
        ticket = _make_signup_ticket(provider, info)
        return RedirectResponse(
            f"{FRONTEND_URL}/oauth/callback#signup={ticket}&provider={provider}&name={quote(info['name'] or '')}"
        )

    blocked = _account_blocked(user)
    if blocked:
        return _fail(blocked)

    token = make_token(user["user_id"], user["user_type"], role=user.get("role", "user"))
    # 토큰은 # 뒤(fragment)에 붙인다 — 브라우저가 서버로 보내지 않아 접속 기록(로그)에 남지 않는다
    return RedirectResponse(f"{FRONTEND_URL}/oauth/callback#token={token}")


# ── 앱 소셜 로그인 (카카오 · 구글 SDK) ────────────────────────────────────
# 앱은 브라우저 리다이렉트 대신 각 SDK로 로그인하고 받은 토큰을 여기로 보낸다.
#   kakao : 카카오 SDK access token → 우리 앱에서 발급된 토큰인지(app_id) 확인 → 회원 번호 · 이메일 · 닉네임
#   google: Credential Manager ID 토큰 → 구글 공개키로 서명 검증 · aud가 우리 '웹 클라이언트 ID'인지 확인
# 이후는 웹 콜백과 같다: 기존 회원이면 JWT, 처음 온 사람이면 가입 티켓(→ 앱 약관 동의 화면 → /social/complete)
# 필요한 환경변수: GOOGLE_CLIENT_ID(이미 있음) · KAKAO_APP_ID(카카오 콘솔 앱 ID 숫자 — 넣으면 다른 앱 토큰을 거절)
KAKAO_APP_ID = os.getenv("KAKAO_APP_ID", "").strip()
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_google_jwks: dict = {"keys": None, "at": 0.0}


class SocialTokenRequest(BaseModel):
    provider: str
    token: str


async def _google_keys(force: bool = False) -> dict:
    import time
    if force or not _google_jwks["keys"] or time.time() - _google_jwks["at"] > 3600:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://www.googleapis.com/oauth2/v3/certs")
            r.raise_for_status()
            _google_jwks["keys"], _google_jwks["at"] = r.json(), time.time()
    return _google_jwks["keys"]


async def _verify_google_id_token(id_token: str) -> dict:
    client_id = PROVIDERS["google"]["client_id"]
    if not client_id:
        raise HTTPException(status_code=500, detail="google 로그인이 아직 설정되지 않았습니다")
    last = None
    for force in (False, True):   # 구글이 키를 바꿨으면 한 번 새로 받아서 다시 검증
        try:
            claims = jwt.decode(id_token, await _google_keys(force), algorithms=["RS256"],
                                audience=client_id, options={"verify_at_hash": False})
            if claims.get("iss") not in GOOGLE_ISSUERS:
                raise ValueError("iss 불일치")
            return claims
        except Exception as e:
            last = e
    print(f"[oauth-app] google ID 토큰 검증 실패: {type(last).__name__}: {last}")
    raise HTTPException(status_code=401, detail="구글 로그인 정보를 확인할 수 없어요. 다시 시도해 주세요")


async def _verify_kakao_access_token(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            info = await client.get("https://kapi.kakao.com/v1/user/access_token_info", headers=headers)
            info.raise_for_status()
            if KAKAO_APP_ID and str(info.json().get("app_id")) != KAKAO_APP_ID:
                raise ValueError("다른 앱에서 발급된 토큰")
            me = await client.get(PROVIDERS["kakao"]["userinfo_url"], headers=headers)
            me.raise_for_status()
            return me.json()
    except Exception as e:
        print(f"[oauth-app] kakao 토큰 검증 실패: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="카카오 로그인 정보를 확인할 수 없어요. 다시 시도해 주세요")


@router.post("/social/token")
async def social_token_login(body: SocialTokenRequest):
    """앱 소셜 로그인. 200 {"token", "user_type"} 또는 200 {"signup", "provider", "name"} · 401 {"detail"}"""
    provider = body.provider.strip().lower()
    if provider == "google":
        info = _normalize("google", await _verify_google_id_token(body.token))
    elif provider == "kakao":
        info = _normalize("kakao", await _verify_kakao_access_token(body.token))
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 로그인 방식입니다")

    user = await _find_user(provider, info)
    if not user:
        return {"signup": _make_signup_ticket(provider, info), "provider": provider, "name": info["name"] or ""}
    blocked = _account_blocked(user)
    if blocked:
        raise HTTPException(status_code=403, detail=blocked)
    return {"token": make_token(user["user_id"], user["user_type"], role=user.get("role", "user")),
            "user_type": user["user_type"]}
