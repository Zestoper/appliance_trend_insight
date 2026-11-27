"""다나와가 점검 · 차단 페이지를 주면 0개로 처리하지 않고 503을 주는지 · 빈 결과를 캐시하지 않는지.
실행: python -m pytest tests/test_danawa_unavailable.py"""
import asyncio
import os

import httpx
import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.services.danawa_search as d  # noqa: E402
import app.routers.naver as n  # noqa: E402

NOTICE_HTML = "<html><head><title>DANAWA Notice</title></head><body><img alt='DANAWA NOTICE'></body></html>"
EMPTY_SEARCH_HTML = "<html><head><title>다나와 검색</title></head><body>" + ("x" * 30000) + "</body></html>"


def _client_returning(url: str, html: str):
    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return httpx.Response(200, text=html, request=httpx.Request("GET", url))

    return FakeClient


@pytest.fixture(autouse=True)
def _clear_cache():
    d._CACHE.clear()
    yield
    d._CACHE.clear()


def test_점검_페이지로_넘어가면_DanawaUnavailable(monkeypatch):
    monkeypatch.setattr(d.httpx, "AsyncClient", _client_returning("https://construction.danawa.com/?query=x", NOTICE_HTML))
    with pytest.raises(d.DanawaUnavailable):
        asyncio.run(d._fetch_raw_items("냉장고"))
    assert "냉장고" not in d._CACHE


def test_작은_공지_페이지도_DanawaUnavailable(monkeypatch):
    monkeypatch.setattr(d.httpx, "AsyncClient", _client_returning("https://search.danawa.com/?query=x", NOTICE_HTML))
    with pytest.raises(d.DanawaUnavailable):
        asyncio.run(d._fetch_raw_items("냉장고"))


def test_빈_결과는_캐시하지_않음(monkeypatch):
    monkeypatch.setattr(d.httpx, "AsyncClient", _client_returning("https://search.danawa.com/?query=x", EMPTY_SEARCH_HTML))
    assert asyncio.run(d._fetch_raw_items("없는상품")) == []
    assert "없는상품" not in d._CACHE


def test_점검이면_라우터가_503과_점검_문구(monkeypatch):
    async def down(**kw):
        raise d.DanawaUnavailable("점검")

    monkeypatch.setattr(n, "NAVER_MAINTENANCE_MODE", True)
    monkeypatch.setattr(n, "danawa_search_products", down)
    with pytest.raises(HTTPException) as e:
        asyncio.run(n.search_products(query="냉장고", page=1, display=15, sort="sim", category="냉장고"))
    assert e.value.status_code == 503 and "점검" in e.value.detail
