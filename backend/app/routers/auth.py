import asyncio
import random
import re
import smtplib
import time

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from app.auth import make_token, hash_password, verify_password, get_current_user
from app.services.email_service import send_verification_email, send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

_verification_codes: dict[str, dict] = {}


class _EmailBody(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        # 'Test@Gmail.com ' 과 'test@gmail.com' 을 같은 이메일로 취급
        return v.strip().lower()


class SendCodeRequest(_EmailBody):
    pass


class VerifyCodeRequest(_EmailBody):
    code: str


class SignupB2C(_EmailBody):
    password: str
    nickname: str
    agree_terms: bool = False   # [필수] 이용약관 · 개인정보 수집 이용 동의


class SignupB2B(_EmailBody):
    password: str
    company_name: str
    business_type: str
    contact_phone: str
    agree_terms: bool = False


# ── 약관 동의 기록 ───────────────────────────────────────────────────────
# 약관이 바뀌면 TERMS_VERSION을 올린다 → 누가 어느 버전에 언제 동의했는지 users에 남는다
# (프론트 frontend/src/legal/legalInfo.js 의 시행일과 맞춘다)
TERMS_VERSION = "2026-11-21"


async def ensure_account_tables():
    """회원 관련 컬럼 · 테이블을 서버 시작 때 한 번만 만든다 (main.py lifespan에서 호출).
    예전에는 가입 요청 도중에 ALTER TABLE을 해서, 같은 요청의 다음 쿼리가 실패하고
    회원만 만들어진 채 약관 기록이 빠지는 일이 있었다."""
    from app.database import execute
    await execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_agreed_at TIMESTAMPTZ")
    await execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version VARCHAR(20)")
    await execute(
        "CREATE TABLE IF NOT EXISTS user_social_accounts ("
        " provider    VARCHAR(20)  NOT NULL,"
        " provider_id VARCHAR(255) NOT NULL,"
        " user_id     BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,"
        " created_at  TIMESTAMPTZ DEFAULT NOW(),"
        " PRIMARY KEY (provider, provider_id))"
    )
    from app.services.push import ensure_push_tables
    await ensure_push_tables()
    from app.services.price_alerts import ensure_alert_tables
    await ensure_alert_tables()


async def create_member(email: str, password_hash: str, user_type: str, *, status: str = "active",
                        nickname: str | None = None, b2b: tuple | None = None,
                        social: tuple | None = None) -> int:
    """회원 생성 · 프로필 · (소셜 연결) · 약관 동의 기록을 하나의 트랜잭션으로.
    중간에 하나라도 실패하면 아무것도 남지 않는다 → '약관 기록 없는 회원'이 생기지 않는다.
    b2b = (company_name, business_type, contact_phone) · social = (provider, provider_id)"""
    from app.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            user_id = await conn.fetchval(
                "INSERT INTO users (email, password_hash, user_type, status, terms_agreed_at, terms_version) "
                "VALUES ($1, $2, $3, $4, NOW(), $5) RETURNING user_id",
                email, password_hash, user_type, status, TERMS_VERSION,
            )
            if b2b:
                await conn.execute(
                    "INSERT INTO user_b2b_profiles (user_id, company_name, business_type, contact_phone) "
                    "VALUES ($1, $2, $3, $4)", user_id, *b2b,
                )
            else:
                await conn.execute(
                    "INSERT INTO user_b2c_profiles (user_id, nickname) VALUES ($1, $2)", user_id, nickname or "회원",
                )
            if social:
                await conn.execute(
                    "INSERT INTO user_social_accounts (provider, provider_id, user_id) VALUES ($1, $2, $3)",
                    social[0], social[1], user_id,
                )
    return user_id


def _require_terms(agree: bool):
    if not agree:
        raise HTTPException(status_code=400, detail="이용약관과 개인정보 수집 · 이용에 동의해 주세요")


class LoginRequest(_EmailBody):
    password: str


@router.post("/send-code")
async def send_code(body: SendCodeRequest):
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", body.email):
        raise HTTPException(status_code=400, detail="올바른 이메일 주소를 입력해주세요")
    from app.database import get_user_by_email
    if await get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    import os as _os
    if _os.getenv("SKIP_EMAIL_VERIFICATION") == "true":
        code = "123456"
        _verification_codes[body.email] = {"code": code, "expires_at": time.time() + 600}
        return {"message": "인증코드가 발송되었습니다"}
    code = str(random.randint(100000, 999999))
    _verification_codes[body.email] = {"code": code, "expires_at": time.time() + 600}
    try:
        await asyncio.to_thread(send_verification_email, body.email, code)
    except smtplib.SMTPRecipientsRefused:
        raise HTTPException(status_code=400, detail="존재하지 않는 이메일 주소입니다")
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=500, detail="메일 서버 인증 오류입니다")
    except Exception as e:
        print(f"[email] SMTP 에러: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다. 주소를 확인해주세요")
    return {"message": "인증코드가 발송되었습니다"}


@router.post("/verify-code")
async def verify_code(body: VerifyCodeRequest):
    stored = _verification_codes.get(body.email)
    if not stored:
        raise HTTPException(status_code=400, detail="인증코드를 먼저 요청해주세요")
    if time.time() > stored["expires_at"]:
        _verification_codes.pop(body.email, None)
        raise HTTPException(status_code=400, detail="인증코드가 만료되었습니다. 재발송해주세요")
    if stored["code"] != body.code:
        raise HTTPException(status_code=400, detail="인증코드가 올바르지 않습니다")
    _verification_codes.pop(body.email, None)
    return {"message": "이메일 인증 완료"}


@router.post("/signup/b2c")
async def signup_b2c(body: SignupB2C):
    from app.database import get_user_by_email
    _require_terms(body.agree_terms)
    if await get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    user_id = await create_member(body.email, hash_password(body.password), "b2c", nickname=body.nickname)
    return {"token": make_token(user_id, "b2c"), "user_type": "b2c", "nickname": body.nickname}


@router.post("/signup/b2b")
async def signup_b2b(body: SignupB2B):
    from app.database import get_user_by_email
    _require_terms(body.agree_terms)
    if not body.company_name.strip() or not body.business_type.strip():
        raise HTTPException(status_code=400, detail="회사명과 업종을 입력해 주세요")
    if await get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    user_id = await create_member(body.email, hash_password(body.password), "b2b", status="pending",
                                  b2b=(body.company_name, body.business_type, body.contact_phone))
    # 승인 전에도 로그인 상태로 개인 기능은 쓸 수 있게 토큰을 준다 (B2B API는 require_b2b가 승인 여부로 막는다)
    return {"token": make_token(user_id, "b2b"), "user_type": "b2b", "company_name": body.company_name,
            "status": "pending", "tier": "free", "tier_expires_at": None}


@router.post("/login")
async def login(body: LoginRequest):
    from app.database import get_user_by_email, fetchone
    user = await get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")
    # 승인 대기(pending) · 거절(rejected)도 로그인은 된다 → 개인 기능은 계속 쓰고
    # 응답의 status로 화면에서 안내한다 (B2B API는 require_b2b가 승인된 회원만 통과시킨다)

    extra = {}
    if user["user_type"] == "b2c":
        profile = await fetchone("SELECT nickname FROM user_b2c_profiles WHERE user_id = %s", (user["user_id"],))
        extra["nickname"] = profile["nickname"] if profile else ""
    else:
        profile = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user["user_id"],))
        extra["company_name"] = profile["company_name"] if profile else ""
        from app.database import get_user_tier
        extra["tier"] = await get_user_tier(user["user_id"])
        extra["tier_expires_at"] = user["tier_expires_at"].isoformat() if user.get("tier_expires_at") else None

    return {
        "token":     make_token(user["user_id"], user["user_type"], role=user.get("role", "user")),
        "user_type": user["user_type"],
        "role":      user.get("role", "user"),
        "status":    user.get("status", "active"),
        **extra,
    }


@router.get("/me")
async def get_me(payload: dict = Depends(get_current_user)):
    """토큰 자체는 유효해도(서명 OK, 만료 전) 그 사이 탈퇴·비활성화됐을 수 있으니
    매번 DB를 다시 조회한다 — 프론트가 앱 로드 시 이걸 호출해서 localStorage에 남아있는
    낡은 로그인 상태를 걸러내는 용도."""
    from app.database import fetchone, get_user_tier
    user = await fetchone("SELECT * FROM users WHERE user_id = %s", (int(payload["sub"]),))
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")

    extra = {}
    if user["user_type"] == "b2c":
        profile = await fetchone("SELECT nickname FROM user_b2c_profiles WHERE user_id = %s", (user["user_id"],))
        extra["nickname"] = profile["nickname"] if profile else ""
        extra["tier"] = "free"
        extra["tier_expires_at"] = None
    else:
        profile = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user["user_id"],))
        extra["company_name"] = profile["company_name"] if profile else ""
        extra["tier"] = await get_user_tier(user["user_id"])
        extra["tier_expires_at"] = user["tier_expires_at"].isoformat() if user.get("tier_expires_at") else None

    # 앱이 이 API 하나로 회원 정보를 다 받을 수 있게 (예전에는 /api/user/me를 따로 불렀다)
    #  social_providers: 비어 있지 않으면 소셜로 연결된 회원 → 탈퇴 시 "탈퇴" 입력
    #  has_password: False면 소셜로 가입한 회원 → 비밀번호 변경 메뉴 숨김
    return {
        "user_id":          user["user_id"],
        "user_type":        user["user_type"],
        "role":             user.get("role", "user"),
        "status":           user.get("status", "active"),
        "email":            user["email"],
        "created_at":       user["created_at"].isoformat() if user.get("created_at") else None,
        "social_providers": await social_providers(user["user_id"]),
        "has_password":     await has_password_login(user["user_id"]),
        **extra,
    }


# ── 비밀번호 재설정 ─────────────────────────────────────────────────────────
# - 가입 여부를 알 수 없도록 이메일이 있든 없든 같은 응답을 준다
# - 링크 토큰 원문은 메일로만 보내고 DB에는 SHA-256 해시만 저장 (DB가 새도 링크를 만들 수 없음)
# - 30분 만료 · 1회용 · 새 요청 시 이전 링크 무효 · 같은 이메일로 15분에 3번까지만 요청
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

_RESET_TTL = timedelta(minutes=30)
_reset_hits: dict[str, list[float]] = {}
_RESET_MESSAGE = "가입된 이메일이면 비밀번호 재설정 링크를 보냈어요. 메일함과 스팸함을 확인해 주세요."


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    new_password: str
    new_password_confirm: str


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _reset_allowed(key: str) -> bool:
    now = time.time()
    hits = [t for t in _reset_hits.get(key, []) if now - t < 15 * 60]
    if len(hits) >= 3:
        _reset_hits[key] = hits
        return False
    _reset_hits[key] = hits + [now]
    return True


async def _ensure_reset_table():
    from app.database import execute
    await execute(
        "CREATE TABLE IF NOT EXISTS password_resets ("
        " token_hash VARCHAR(64) PRIMARY KEY,"
        " user_id BIGINT NOT NULL,"
        " expires_at TIMESTAMPTZ NOT NULL,"
        " created_at TIMESTAMPTZ DEFAULT NOW())"
    )


async def _send_reset_mail(email: str, token: str):
    try:
        await asyncio.to_thread(send_password_reset_email, email, token)
    except Exception as e:
        print(f"[email] 비밀번호 재설정 메일 실패: {type(e).__name__}: {e}")


@router.post("/password-reset/request")
async def password_reset_request(body: ResetRequest):
    from app.database import execute, get_user_by_email
    email = body.email.strip()
    if not email or not _reset_allowed(email.lower()):
        return {"message": _RESET_MESSAGE}
    user = await get_user_by_email(email)
    if not user or not user.get("is_active", True):
        return {"message": _RESET_MESSAGE}
    await _ensure_reset_table()
    now = datetime.now(timezone.utc)
    await execute("DELETE FROM password_resets WHERE user_id = %s OR expires_at < %s", (user["user_id"], now))
    token = secrets.token_urlsafe(32)
    await execute(
        "INSERT INTO password_resets (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
        (_token_hash(token), user["user_id"], now + _RESET_TTL),
    )
    asyncio.create_task(_send_reset_mail(user["email"], token))  # 응답은 메일 발송을 기다리지 않음
    return {"message": _RESET_MESSAGE}


@router.get("/password-reset/check")
async def password_reset_check(token: str = ""):
    from app.database import fetchone
    await _ensure_reset_table()
    row = await fetchone(
        "SELECT 1 AS ok FROM password_resets WHERE token_hash = %s AND expires_at > %s",
        (_token_hash(token), datetime.now(timezone.utc)),
    )
    return {"valid": bool(row)}


@router.post("/password-reset/confirm")
async def password_reset_confirm(body: ResetConfirm):
    from app.database import execute, fetchone
    if body.new_password != body.new_password_confirm:
        raise HTTPException(status_code=400, detail="새 비밀번호가 서로 다릅니다")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상으로 입력해주세요")
    await _ensure_reset_table()
    row = await fetchone(
        "DELETE FROM password_resets WHERE token_hash = %s AND expires_at > %s RETURNING user_id",
        (_token_hash(body.token), datetime.now(timezone.utc)),
    )  # 지우면서 확인 — 같은 링크로 동시에 두 번 눌러도 한 번만 성공
    if not row:
        raise HTTPException(status_code=400, detail="링크가 만료됐거나 이미 사용됐어요. 다시 요청해 주세요")
    await execute("UPDATE users SET password_hash = %s WHERE user_id = %s",
                  (hash_password(body.new_password), row["user_id"]))
    await execute("DELETE FROM password_resets WHERE user_id = %s", (row["user_id"],))
    return {"message": "비밀번호를 바꿨어요"}


# ── 회원 탈퇴 ─────────────────────────────────────────────────────────────
# 웹과 앱이 같이 쓴다. POST로 받는 이유: 안드로이드 Retrofit의 @DELETE는 본문을 보내기 번거롭다.
# 확인 방법
#   - 이메일 가입 회원: 현재 비밀번호
#   - 소셜(카카오 · 구글) 가입 회원: 비밀번호를 모르므로 confirm에 "탈퇴"를 입력
#     (/api/user/me 의 social_providers가 비어 있지 않으면 소셜 회원)
# 지우는 것: 회원 정보 · 프로필 · 가격 알림 · 소셜 연결 · 비밀번호 재설정 토큰
# 결제 기록은 전자상거래법상 5년 보관 의무가 있어서 회원과 연결을 끊은 사본을 payments_archive에 남긴 뒤 지운다
#   (개인정보처리방침 2조와 같은 내용 · 5년이 지난 사본은 따로 지워야 함)
# 탈퇴 후 기존 토큰은 /api/auth/me 에서 401이 나서 웹 · 앱 모두 자동으로 로그아웃된다.
WITHDRAW_CONFIRM_WORD = "탈퇴"

# 자식 테이블부터 지운다 (DB에 ON DELETE CASCADE가 없어도 안전하도록)
_WITHDRAW_TABLES = [
    "price_alert", "payments", "user_social_accounts", "password_resets",
    "user_b2c_profiles", "user_b2b_profiles",
]


class WithdrawRequest(BaseModel):
    password: str | None = None
    confirm:  str | None = None


async def has_password_login(user_id: int) -> bool:
    """비밀번호로 로그인할 수 있는 회원인지.
    소셜로 처음 가입한 회원은 임의의 비밀번호가 들어 있어서 본인도 모른다 → False.
    가입한 순간 소셜 연결이 함께 만들어졌으면(10초 이내) 소셜 가입, 나중에 연결했으면 이메일 가입 회원이다."""
    from app.database import fetchone
    exists = await fetchone("SELECT to_regclass('public.user_social_accounts') IS NOT NULL AS ok")
    if not exists or not exists["ok"]:
        return True
    row = await fetchone(
        "SELECT 1 AS hit FROM user_social_accounts s JOIN users u ON u.user_id = s.user_id "
        "WHERE s.user_id = %s AND s.created_at - u.created_at < INTERVAL '10 seconds' LIMIT 1",
        (user_id,),
    )
    return not row


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str


@router.post("/password/change")
async def change_password(body: PasswordChangeRequest, payload: dict = Depends(get_current_user)):
    """마이페이지 비밀번호 변경 — 웹과 앱이 같이 쓴다"""
    from app.database import fetchone, execute
    user_id = int(payload["sub"])
    user = await fetchone("SELECT user_id, password_hash FROM users WHERE user_id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
    if not await has_password_login(user_id):
        raise HTTPException(status_code=400, detail="소셜 로그인 회원은 비밀번호가 없어요. 비밀번호 찾기로 새로 만들 수 있어요")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="현재 비밀번호가 올바르지 않습니다")
    if body.new_password != body.new_password_confirm:
        raise HTTPException(status_code=400, detail="새 비밀번호가 서로 다릅니다")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상으로 입력해주세요")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="지금 비밀번호와 다른 비밀번호를 입력해주세요")
    await execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hash_password(body.new_password), user_id))
    # 아직 안 쓴 비밀번호 재설정 링크는 무효로
    await _ensure_reset_table()
    await execute("DELETE FROM password_resets WHERE user_id = %s", (user_id,))
    return {"message": "비밀번호를 바꿨어요"}


async def social_providers(user_id: int) -> list[str]:
    from app.database import fetchone, fetchall
    exists = await fetchone("SELECT to_regclass('public.user_social_accounts') IS NOT NULL AS ok")
    if not exists or not exists["ok"]:
        return []
    rows = await fetchall("SELECT provider FROM user_social_accounts WHERE user_id = %s ORDER BY provider", (user_id,))
    return [r["provider"] for r in rows]


@router.post("/withdraw")
async def withdraw(body: WithdrawRequest, payload: dict = Depends(get_current_user)):
    from app.database import fetchone, get_pool
    user_id = int(payload["sub"])
    user = await fetchone("SELECT user_id, password_hash, role FROM users WHERE user_id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
    if user.get("role") == "admin":
        raise HTTPException(status_code=403, detail="관리자 계정은 탈퇴할 수 없어요")

    password_ok = bool(body.password) and verify_password(body.password, user["password_hash"])
    social_ok = (body.confirm or "").strip() == WITHDRAW_CONFIRM_WORD and bool(await social_providers(user_id))
    if not (password_ok or social_ok):
        if body.password:
            raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다")
        raise HTTPException(status_code=400, detail=f"비밀번호를 입력하거나 소셜 회원은 '{WITHDRAW_CONFIRM_WORD}'를 입력해 주세요")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():   # 중간에 실패하면 아무것도 안 지워진다
            if await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", "public.payments"):
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS payments_archive ("
                    " order_id TEXT, payload JSONB NOT NULL, archived_at TIMESTAMPTZ DEFAULT NOW())"
                )
                # 사본에는 user_id를 빼서 탈퇴한 회원과 연결되지 않게 한다
                await conn.execute(
                    "INSERT INTO payments_archive (order_id, payload) "
                    "SELECT p.order_id, to_jsonb(p) - 'user_id' FROM payments p WHERE p.user_id = $1",
                    user_id,
                )
            for table in _WITHDRAW_TABLES:
                if await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{table}"):
                    await conn.execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    print(f"[auth] 회원 탈퇴 user_id={user_id}")
    return {"ok": True, "message": "탈퇴가 완료되었어요. 그동안 이용해 주셔서 감사합니다"}
