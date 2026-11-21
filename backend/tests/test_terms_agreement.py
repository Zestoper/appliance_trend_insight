"""회원가입 약관 동의 · 회원 생성 트랜잭션 테스트 (DB는 가짜). 실행: python -m pytest tests/test_terms_agreement.py"""
import asyncio
import os
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.routers import auth, oauth  # noqa: E402


class FakeConn:
    def __init__(self, log, fail_on=None):
        self.log, self.fail_on = log, fail_on

    async def fetchval(self, sql, *args):
        self.log.append(("sql", sql, args))
        return 11

    async def execute(self, sql, *args):
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("DB 오류 흉내")
        self.log.append(("sql", sql, args))

    @asynccontextmanager
    async def transaction(self):
        try:
            yield
            self.log.append(("commit",))
        except Exception:
            self.log.append(("rollback",))
            raise


def setup(monkeypatch, fail_on=None):
    log = []

    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield FakeConn(log, fail_on)

    async def get_pool():
        return Pool()

    async def get_user_by_email(email):
        return None

    async def fetchone(sql, args=None):
        return {"user_id": 11, "user_type": "b2c", "role": "user"}

    monkeypatch.setattr(db, "get_pool", get_pool)
    monkeypatch.setattr(db, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(db, "fetchone", fetchone)
    return log


def b2c(**kw):
    return auth.SignupB2C(email="a@b.com", password="pw123456", nickname="닉", **kw)


def test_동의하지_않으면_가입_안됨(monkeypatch):
    log = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.signup_b2c(b2c()))
    assert e.value.status_code == 400 and log == []


def test_가입하면_회원과_약관_기록이_한_번에_저장되고_커밋(monkeypatch):
    log = setup(monkeypatch)
    res = asyncio.run(auth.signup_b2c(b2c(agree_terms=True)))
    assert res["user_type"] == "b2c"
    insert_user = log[0]
    assert "terms_agreed_at" in insert_user[1] and auth.TERMS_VERSION in insert_user[2]
    assert log[-1] == ("commit",)


def test_기업_회원도_동의_필수(monkeypatch):
    setup(monkeypatch)
    body = auth.SignupB2B(email="c@d.com", password="pw123456", company_name="회사", business_type="유통", contact_phone="")
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.signup_b2b(body))
    assert e.value.status_code == 400


def test_소셜_가입_중간에_실패하면_전부_되돌림(monkeypatch):
    log = setup(monkeypatch, fail_on="user_social_accounts")
    info = {"provider_id": "9", "email": None, "email_verified": False, "name": "카카오"}
    with pytest.raises(RuntimeError):
        asyncio.run(oauth._create_social_user("kakao", info, "닉"))
    assert log[-1] == ("rollback",)          # 회원 · 프로필이 남지 않는다


def test_소셜_가입_성공은_한_트랜잭션(monkeypatch):
    log = setup(monkeypatch)
    info = {"provider_id": "9", "email": None, "email_verified": False, "name": "카카오"}
    user = asyncio.run(oauth._create_social_user("kakao", info, "닉"))
    sqls = [x[1] for x in log if x[0] == "sql"]
    assert user["user_id"] == 11 and log[-1] == ("commit",)
    assert any("user_social_accounts" in q for q in sqls) and "terms_agreed_at" in sqls[0]
