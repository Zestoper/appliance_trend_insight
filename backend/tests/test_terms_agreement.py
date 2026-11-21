"""회원가입 약관 동의 테스트 (DB는 가짜). 실행: python -m pytest tests/test_terms_agreement.py"""
import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.routers import auth  # noqa: E402


def setup(monkeypatch):
    sql_log = []

    async def get_user_by_email(email):
        return None

    async def create_user(*a, **k):
        return 11

    async def create_profile(*a, **k):
        return 1

    async def execute(sql, args=None):
        sql_log.append((sql, args))

    monkeypatch.setattr(db, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(db, "create_user", create_user)
    monkeypatch.setattr(db, "create_b2c_profile", create_profile)
    monkeypatch.setattr(db, "create_b2b_profile", create_profile)
    monkeypatch.setattr(db, "execute", execute)
    monkeypatch.setattr(auth, "_terms_columns_ready", False)
    return sql_log


def b2c(**kw):
    return auth.SignupB2C(email="a@b.com", password="pw123456", nickname="닉", **kw)


def test_동의하지_않으면_가입_안됨(monkeypatch):
    log = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.signup_b2c(b2c()))
    assert e.value.status_code == 400 and log == []


def test_동의하면_가입되고_동의_시각과_버전이_저장됨(monkeypatch):
    log = setup(monkeypatch)
    res = asyncio.run(auth.signup_b2c(b2c(agree_terms=True)))
    assert res["user_type"] == "b2c"
    update = [a for sql, a in log if sql.startswith("UPDATE users SET terms_agreed_at")]
    assert update == [(auth.TERMS_VERSION, 11)]


def test_기업_회원도_동의_필수(monkeypatch):
    setup(monkeypatch)
    body = auth.SignupB2B(email="c@d.com", password="pw123456", company_name="회사", business_type="유통", contact_phone="")
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.signup_b2b(body))
    assert e.value.status_code == 400
