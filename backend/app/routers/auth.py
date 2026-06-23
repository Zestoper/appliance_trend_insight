import asyncio
import random
import re
import smtplib
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import make_token, hash_password, verify_password
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

_verification_codes: dict[str, dict] = {}


class SendCodeRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


class SignupB2C(BaseModel):
    email: str
    password: str
    nickname: str


class SignupB2B(BaseModel):
    email: str
    password: str
    company_name: str
    business_type: str
    contact_phone: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/send-code")
async def send_code(body: SendCodeRequest):
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", body.email):
        raise HTTPException(status_code=400, detail="올바른 이메일 주소를 입력해주세요")
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

    return {
        "token":     make_token(user["user_id"], user["user_type"], role=user.get("role", "user")),
        "user_type": user["user_type"],
        "role":      user.get("role", "user"),
        "status":    user.get("status", "active"),
        **extra,
    }
