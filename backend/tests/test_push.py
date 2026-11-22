"""푸시 토큰 등록 · 해제와 발송. 실행: python -m pytest tests/test_push.py"""
import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.services import push  # noqa: E402
from app.routers import user, admin  # noqa: E402

ME = {"sub": "7", "user_type": "b2b"}


def run(c):
    return asyncio.run(c)


def test_register_and_delete(monkeypatch):
    calls = []

    async def execute(sql, args=None):
        calls.append((sql.split()[0], args))
        return 1
    monkeypatch.setattr(db, "execute", execute)
    run(user.register_push_token(user.PushTokenBody(token=" tok1 "), ME))
    run(user.unregister_push_token(user.PushTokenBody(token="tok1"), ME))
    assert calls[0] == ("INSERT", ("tok1", 7, "android"))
    assert calls[1] == ("DELETE", ("tok1", 7))


def test_register_empty_token():
    with pytest.raises(HTTPException) as e:
        run(user.register_push_token(user.PushTokenBody(token="  "), ME))
    assert e.value.status_code == 400


def test_no_credentials_skips(monkeypatch):
    monkeypatch.setattr(push, "_tried", False)
    monkeypatch.setattr(push, "_app", None)
    monkeypatch.delenv("FIREBASE_CREDENTIALS", raising=False)
    assert run(push.send_to_user(7, "t", "b")) == 0


def test_dead_tokens_removed(monkeypatch):
    from firebase_admin import messaging
    monkeypatch.setattr(push, "_tried", True)
    monkeypatch.setattr(push, "_app", object())
    deleted = []

    async def fetchall(sql, args=None):
        return [{"token": "ok"}, {"token": "dead"}]

    async def execute(sql, args=None):
        deleted.append(args[0])
        return 1

    def fake_send(msg, app=None):
        assert msg.tokens == ["ok", "dead"]
        return SimpleNamespace(responses=[
            SimpleNamespace(success=True, exception=None),
            SimpleNamespace(success=False, exception=messaging.UnregisteredError("gone")),
        ])
    monkeypatch.setattr(db, "fetchall", fetchall)
    monkeypatch.setattr(db, "execute", execute)
    monkeypatch.setattr(messaging, "send_each_for_multicast", fake_send)
    assert run(push.send_to_user(7, "t", "b", {"type": "x"})) == 1
    assert deleted == ["dead"]


@pytest.mark.parametrize("action,status", [("approve", "active"), ("reject", "rejected")])
def test_admin_sends_push(monkeypatch, action, status):
    sent = []

    async def fetchone(sql, args=None):
        return {"user_id": 7, "email": "b@biz.com", "company_name": "회사"}

    async def execute(sql, args=None):
        return 1
    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "execute", execute)
    monkeypatch.setattr(admin, "push_in_background", lambda uid, t, b, d: sent.append((uid, d["status"])))
    monkeypatch.setattr(admin, "_mail_in_background", lambda *a: None)
    adm = {"sub": "1", "role": "admin"}
    if action == "approve":
        run(admin.admin_approve_user(7, adm))
    else:
        run(admin.admin_reject_user(7, adm))
    assert sent == [(7, status)]
