"""회원 탈퇴 API 테스트 (DB는 가짜로 바꿔서 실제 데이터는 건드리지 않음). 실행: python -m pytest tests/test_withdraw.py"""
import asyncio
import os
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.routers import auth  # noqa: E402

PW = hash_password("correct-pw")


class FakeConn:
    def __init__(self, deleted):
        self.deleted = deleted

    async def fetchval(self, sql, *args):
        return True                      # 모든 테이블이 있다고 가정

    async def execute(self, sql, *args):
        self.deleted.append(sql.split()[2])  # "DELETE FROM 테이블 ..."

    @asynccontextmanager
    async def transaction(self):
        yield


class FakePool:
    def __init__(self, deleted):
        self.deleted = deleted

    @asynccontextmanager
    async def acquire(self):
        yield FakeConn(self.deleted)


def setup(monkeypatch, role="user", providers=()):
    deleted = []

    async def fetchone(sql, args=None):
        if "to_regclass" in sql:
            return {"ok": True}
        return {"user_id": 7, "password_hash": PW, "role": role}

    async def fetchall(sql, args=None):
        return [{"provider": p} for p in providers]

    async def get_pool():
        return FakePool(deleted)

    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "fetchall", fetchall)
    monkeypatch.setattr(db, "get_pool", get_pool)
    return deleted


def call(**body):
    return asyncio.run(auth.withdraw(auth.WithdrawRequest(**body), {"sub": "7"}))


def test_이메일_회원은_비밀번호가_맞으면_탈퇴(monkeypatch):
    deleted = setup(monkeypatch)
    assert call(password="correct-pw")["ok"]
    assert deleted[-1] == "users" and "price_alert" in deleted and "payments" in deleted


def test_비밀번호가_틀리면_401_그리고_아무것도_안_지움(monkeypatch):
    deleted = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        call(password="wrong")
    assert e.value.status_code == 401 and deleted == []


def test_소셜_회원은_탈퇴_입력으로(monkeypatch):
    deleted = setup(monkeypatch, providers=("kakao",))
    assert call(confirm="탈퇴")["ok"] and deleted[-1] == "users"


def test_이메일_회원은_탈퇴_입력만으로는_안됨(monkeypatch):
    deleted = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        call(confirm="탈퇴")
    assert e.value.status_code == 400 and deleted == []


def test_관리자는_탈퇴_불가(monkeypatch):
    deleted = setup(monkeypatch, role="admin")
    with pytest.raises(HTTPException) as e:
        call(password="correct-pw")
    assert e.value.status_code == 403 and deleted == []
