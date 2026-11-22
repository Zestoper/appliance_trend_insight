"""앱 소셜 로그인(/api/auth/social/token) 테스트. 구글 서명은 테스트용 키로 만들어 검증한다. 실행: python -m pytest tests/test_social_app_login.py"""
import asyncio
import os
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwk, jwt

os.environ.setdefault("JWT_SECRET", "test")

from app.routers import oauth  # noqa: E402

WEB_CLIENT_ID = "web-client.apps.googleusercontent.com"
_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIV = _key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()).decode()
PUB = _key.public_key().public_bytes(serialization.Encoding.PEM,
                                     serialization.PublicFormat.SubjectPublicKeyInfo).decode()
JWKS = {"keys": [{**jwk.construct(PUB, "RS256").to_dict(), "kid": "test", "use": "sig"}]}


def google_token(aud=WEB_CLIENT_ID, iss="https://accounts.google.com", key=PRIV):
    claims = {"sub": "g-1", "email": "g@gmail.com", "email_verified": True, "name": "구글",
              "aud": aud, "iss": iss, "exp": int(time.time()) + 600, "iat": int(time.time())}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test"})


def setup(monkeypatch, existing=None):
    monkeypatch.setitem(oauth.PROVIDERS["google"], "client_id", WEB_CLIENT_ID)

    async def keys(force=False):
        return JWKS

    async def find(provider, info):
        return existing

    monkeypatch.setattr(oauth, "_google_keys", keys)
    monkeypatch.setattr(oauth, "_find_user", find)


def login(provider, token):
    return asyncio.run(oauth.social_token_login(oauth.SocialTokenRequest(provider=provider, token=token)))


def test_구글_처음_온_사람은_가입_티켓(monkeypatch):
    setup(monkeypatch)
    res = login("google", google_token())
    assert res["provider"] == "google" and res["name"] == "구글"
    assert oauth._read_signup_ticket(res["signup"])[1]["provider_id"] == "g-1"


def test_구글_기존_회원은_바로_JWT(monkeypatch):
    setup(monkeypatch, existing={"user_id": 1, "user_type": "b2c", "role": "user"})
    res = login("google", google_token())
    assert res["token"] and res["user_type"] == "b2c"


@pytest.mark.parametrize("token_kw", [
    {"aud": "someone-elses-client"},                     # 다른 앱용 토큰
    {"iss": "https://evil.example.com"},                 # 발급자 위조
])
def test_구글_토큰이_우리_것이_아니면_401(monkeypatch, token_kw):
    setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        login("google", google_token(**token_kw))
    assert e.value.status_code == 401


def test_구글_서명이_다르면_401(monkeypatch):
    setup(monkeypatch)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    with pytest.raises(HTTPException) as e:
        login("google", google_token(key=other))
    assert e.value.status_code == 401


def test_카카오_기존_회원(monkeypatch):
    setup(monkeypatch, existing={"user_id": 2, "user_type": "b2c"})

    async def kakao(token):
        return {"id": 99, "kakao_account": {"email": "k@kakao.com", "profile": {"nickname": "카카오"}}}

    monkeypatch.setattr(oauth, "_verify_kakao_access_token", kakao)
    assert login("kakao", "kakao-access-token")["token"]


def test_승인_대기_사업자도_로그인은_된다(monkeypatch):
    setup(monkeypatch, existing={"user_id": 3, "user_type": "b2b", "status": "pending"})
    assert login("google", google_token())["token"]      # B2B API는 require_b2b가 막는다


def test_비활성_계정은_403(monkeypatch):
    setup(monkeypatch, existing={"user_id": 3, "user_type": "b2c", "is_active": False})
    with pytest.raises(HTTPException) as e:
        login("google", google_token())
    assert e.value.status_code == 403


def test_모르는_로그인_방식은_400(monkeypatch):
    setup(monkeypatch)
    with pytest.raises(HTTPException) as e:
        login("naver", "x")
    assert e.value.status_code == 400
