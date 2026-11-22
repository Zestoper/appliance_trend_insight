import os
import bcrypt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Depends
from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다")
JWT_ALGORITHM = "HS256"
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "gajeonmussang@gmail.com")   # 서비스 문의 메일 (웹 legalInfo.js와 같게)
JWT_EXPIRE_HOURS = 24 * 7


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def make_token(user_id: int, user_type: str, role: str = "user") -> str:
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "type": user_type, "role": role, "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


async def require_admin(payload: dict = Depends(get_current_user)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다")
    return payload


async def require_b2b(payload: dict = Depends(get_current_user)) -> dict:
    """B2B 전용 API. 토큰의 회원 유형만이 아니라 DB의 승인 상태까지 확인한다.
    (사업자 가입 신청 후 승인 전에도 로그인해서 개인 기능은 쓸 수 있게 바뀌었기 때문에
     토큰만 보면 승인 전 회원이 B2B API를 쓸 수 있다)"""
    if payload.get("role") == "admin":
        return payload
    if payload.get("type") != "b2b":
        raise HTTPException(status_code=403, detail="B2B 회원만 접근할 수 있습니다")
    from app.database import fetchone
    user = await fetchone("SELECT status, is_active FROM users WHERE user_id = %s", (int(payload["sub"]),))
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
    if user.get("status") == "rejected":
        raise HTTPException(status_code=403, detail=f"사업자 승인이 거절됐어요. 문의: {CONTACT_EMAIL}")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="사업자 승인 후 이용할 수 있어요")
    return payload


_TIER_RANK = {"free": 0, "silver": 1, "gold": 2, "platinum": 3}


def require_tier(min_tier: str):
    """등급 검증 의존성 팩토리. JWT에 등급을 넣지 않고 매 요청 DB에서 조회하므로
    결제 직후 재로그인 없이 즉시 반영된다. admin은 모든 등급을 통과한다."""
    async def _dep(payload: dict = Depends(require_b2b)) -> dict:
        if payload.get("role") == "admin":
            return payload
        from app.database import get_user_tier
        tier = await get_user_tier(int(payload["sub"]))
        if _TIER_RANK.get(tier, 0) < _TIER_RANK[min_tier]:
            raise HTTPException(status_code=402, detail=f"{min_tier} 등급 이상 구독이 필요합니다")
        return payload
    return _dep
