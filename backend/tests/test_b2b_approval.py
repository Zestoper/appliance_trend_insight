"""사업자 승인 전 · 거절 회원: 로그인 · 개인 기능은 되고 B2B API는 막힘. 실행: python -m pytest tests/test_b2b_approval.py"""
import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app import auth as core  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.routers import auth  # noqa: E402

PW = hash_password("pw123456")


def user_row(status):
    return {"user_id": 7, "email": "b@biz.com", "password_hash": PW, "user_type": "b2b", "role": "user",
            "status": status, "is_active": True, "tier_expires_at": None}


def setup(monkeypatch, status):
    async def get_user_by_email(email):
        return user_row(status)

    async def fetchone(sql, args=None):
        if "FROM users" in sql:
            return user_row(status)
        return {"company_name": "회사"}

    async def tier(uid):
        return "free"

    monkeypatch.setattr(db, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "get_user_tier", tier)


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_승인_전_거절도_로그인되고_status를_준다(monkeypatch, status):
    setup(monkeypatch, status)
    res = asyncio.run(auth.login(auth.LoginRequest(email="b@biz.com", password="pw123456")))
    assert res["token"] and res["status"] == status


@pytest.mark.parametrize("status,phrase", [("pending", "승인 후"), ("rejected", "거절")])
def test_승인_전_거절은_B2B_API_403(monkeypatch, status, phrase):
    setup(monkeypatch, status)
    with pytest.raises(HTTPException) as e:
        asyncio.run(core.require_b2b({"sub": "7", "type": "b2b"}))
    assert e.value.status_code == 403 and phrase in e.value.detail


def test_승인된_사업자는_통과(monkeypatch):
    setup(monkeypatch, "active")
    assert asyncio.run(core.require_b2b({"sub": "7", "type": "b2b"}))["sub"] == "7"


def test_개인_회원은_B2B_API_403():
    with pytest.raises(HTTPException) as e:
        asyncio.run(core.require_b2b({"sub": "1", "type": "b2c"}))
    assert e.value.status_code == 403
