"""마이페이지 비밀번호 변경 테스트 (DB는 가짜). 실행: python -m pytest tests/test_password_change.py"""
import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.auth import hash_password, verify_password  # noqa: E402
from app.routers import auth  # noqa: E402

PW = hash_password("old-password")


def setup(monkeypatch, has_password=True):
    log = []

    async def fetchone(sql, args=None):
        return {"user_id": 3, "password_hash": PW}

    async def execute(sql, args=None):
        log.append((sql, args))

    async def has_pw(user_id):
        return has_password

    async def ensure():
        return None

    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "execute", execute)
    monkeypatch.setattr(auth, "has_password_login", has_pw)
    monkeypatch.setattr(auth, "_ensure_reset_table", ensure)
    return log


def change(cur, new, confirm=None):
    body = auth.PasswordChangeRequest(current_password=cur, new_password=new, new_password_confirm=confirm or new)
    return asyncio.run(auth.change_password(body, {"sub": "3"}))


def test_정상_변경_후_재설정_링크도_무효(monkeypatch):
    log = setup(monkeypatch)
    change("old-password", "new-password-1")
    upd = [a for sql, a in log if sql.startswith("UPDATE users SET password_hash")]
    assert len(upd) == 1 and verify_password("new-password-1", upd[0][0])
    assert any(sql.startswith("DELETE FROM password_resets") for sql, _ in log)


@pytest.mark.parametrize("cur,new,confirm,code", [
    ("wrong", "new-password-1", None, 401),            # 현재 비밀번호 틀림
    ("old-password", "new-password-1", "다름", 400),     # 확인 불일치
    ("old-password", "short", None, 400),              # 8자 미만
    ("old-password", "old-password", None, 400),       # 같은 비밀번호
])
def test_변경_실패하면_아무것도_안_바뀜(monkeypatch, cur, new, confirm, code):
    log = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        change(cur, new, confirm)
    assert e.value.status_code == code and log == []


def test_소셜_가입_회원은_변경_불가(monkeypatch):
    log = setup(monkeypatch, has_password=False)
    with pytest.raises(HTTPException) as e:
        change("old-password", "new-password-1")
    assert e.value.status_code == 400 and log == []
