"""GET /api/auth/me 응답 필드 테스트 (DB는 가짜). 실행: python -m pytest tests/test_auth_me.py"""
import asyncio
import os
from datetime import datetime, timezone

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.routers import auth  # noqa: E402

CREATED = datetime(2026, 11, 22, tzinfo=timezone.utc)


def setup(monkeypatch, user_type, social=(), has_pw=True):
    async def fetchone(sql, args=None):
        if "FROM users" in sql:
            return {"user_id": 5, "user_type": user_type, "role": "user", "status": "active",
                    "email": "a@b.com", "is_active": True, "created_at": CREATED, "tier_expires_at": None}
        if "b2c_profiles" in sql:
            return {"nickname": "닉"}
        return {"company_name": "회사"}

    async def tier(uid):
        return "gold"

    async def providers(uid):
        return list(social)

    async def haspw(uid):
        return has_pw

    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "get_user_tier", tier)
    monkeypatch.setattr(auth, "social_providers", providers)
    monkeypatch.setattr(auth, "has_password_login", haspw)


def test_개인_회원도_tier와_소셜_비밀번호_가입일이_온다(monkeypatch):
    setup(monkeypatch, "b2c", social=("kakao",), has_pw=False)
    me = asyncio.run(auth.get_me({"sub": "5"}))
    assert me["tier"] == "free" and me["social_providers"] == ["kakao"] and me["has_password"] is False
    assert me["created_at"].startswith("2026-11-22") and me["nickname"] == "닉" and me["user_id"] == 5


def test_사업자_회원은_등급과_회사명(monkeypatch):
    setup(monkeypatch, "b2b")
    me = asyncio.run(auth.get_me({"sub": "5"}))
    assert me["tier"] == "gold" and me["company_name"] == "회사" and me["has_password"] is True
    assert me["social_providers"] == [] and me["status"] == "active"
