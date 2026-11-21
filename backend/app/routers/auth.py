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


class SignupB2B(_EmailBody):
    password: str
    company_name: str
    business_type: str
    contact_phone: str


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
    from app.database import get_user_by_email, create_user, create_b2c_profile
    if await get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    user_id = await create_user(body.email, hash_password(body.password), "b2c")
    await create_b2c_profile(user_id, body.nickname)
    return {"token": make_token(user_id, "b2c"), "user_type": "b2c", "nickname": body.nickname}


@router.post("/signup/b2b")
async def signup_b2b(body: SignupB2B):
    from app.database import get_user_by_email, create_user, create_b2b_profile
    if await get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    user_id = await create_user(body.email, hash_password(body.password), "b2b", status="pending")
    await create_b2b_profile(user_id, body.company_name, body.business_type, body.contact_phone)
    return {"user_type": "b2b", "company_name": body.company_name, "status": "pending"}


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
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="PENDING")
    if user.get("status") == "rejected":
        raise HTTPException(status_code=403, detail="사업자 인증이 거절되었습니다. 관리자에게 문의해주세요")

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
    else:
        profile = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user["user_id"],))
        extra["company_name"] = profile["company_name"] if profile else ""
        extra["tier"] = await get_user_tier(user["user_id"])
        extra["tier_expires_at"] = user["tier_expires_at"].isoformat() if user.get("tier_expires_at") else None

    return {
        "user_type": user["user_type"],
        "role":      user.get("role", "user"),
        "status":    user.get("status", "active"),
        "email":     user["email"],
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
