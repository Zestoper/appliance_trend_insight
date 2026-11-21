"""소셜 첫 가입 약관 동의 흐름 테스트 (DB는 가짜). 실행: python -m pytest tests/test_social_signup.py"""
import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

from app.routers import oauth  # noqa: E402

INFO = {"provider_id": "123", "email": "new@kakao.com", "email_verified": True, "name": "준영"}


def setup(monkeypatch, existing=None):
    created = []

    async def find(provider, info):
        return existing

    async def create(provider, info, nickname):
        created.append(nickname)
        return {"user_id": 5, "user_type": "b2c", "role": "user"}

    monkeypatch.setattr(oauth, "_find_user", find)
    monkeypatch.setattr(oauth, "_create_social_user", create)
    return created


def complete(**kw):
    return asyncio.run(oauth.social_complete(oauth.SocialCompleteRequest(**kw)))


def test_가입_티켓은_서명돼_있고_내용을_되돌려준다():
    ticket = oauth._make_signup_ticket("kakao", INFO)
    assert oauth._read_signup_ticket(ticket) == ("kakao", INFO)
    assert oauth._read_signup_ticket(ticket + "x") is None          # 위조
    assert oauth._read_signup_ticket(oauth._make_state("kakao")) is None  # 다른 용도 토큰


def test_동의하지_않으면_가입_안됨(monkeypatch):
    created = setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        complete(ticket=oauth._make_signup_ticket("kakao", INFO))
    assert e.value.status_code == 400 and created == []


def test_동의하면_가입되고_토큰을_준다(monkeypatch):
    created = setup(monkeypatch)
    res = complete(ticket=oauth._make_signup_ticket("kakao", INFO), agree_terms=True, nickname="새닉네임")
    assert res["token"] and created == ["새닉네임"]


def test_이미_가입된_뒤_다시_보내면_새로_만들지_않음(monkeypatch):
    created = setup(monkeypatch, existing={"user_id": 5, "user_type": "b2c"})
    res = complete(ticket=oauth._make_signup_ticket("kakao", INFO), agree_terms=True)
    assert res["token"] and created == []


def test_잘못된_티켓은_400(monkeypatch):
    setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        complete(ticket="garbage", agree_terms=True)
    assert e.value.status_code == 400
