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


# ── 다나와가 안 되면 DB에 저장해 둔 결과로 대신 보여 주기 ──

STORED = [
    {"id": "1", "title": "삼성전자 비스포크 RF85C90D1AP", "brand": "삼성전자", "price": 2500000,
     "image": "", "link": "", "mallName": "다나와 최저가비교", "reviewCount": 10, "reviewScore": 4.8,
     "categories": ["생활가전", "냉장고", "양문형냉장고"]},
    {"id": "2", "title": "LG전자 디오스 오브제컬렉션 M874GBB031", "brand": "LG전자", "price": 3000000,
     "image": "", "link": "", "mallName": "다나와 최저가비교", "reviewCount": 5, "reviewScore": 4.9,
     "categories": ["생활가전", "냉장고", "양문형냉장고"]},
]


def test_다나와_점검이면_저장된_결과로_대신_보여줌(monkeypatch):
    import app.services.search_store as store

    async def down(query):
        raise d.DanawaUnavailable("점검")

    async def stored(query):
        return list(STORED), 1795700000.0

    monkeypatch.setattr(d, "_fetch_raw_items", down)
    monkeypatch.setattr(store, "load_fallback", stored)
    res = asyncio.run(d.danawa_search_products(query="냉장고", category="냉장고"))
    assert res["total"] == 2 and res["stale"] is True and res["stale_at"].startswith("2026-")


def test_저장된_것도_없으면_원래대로_503(monkeypatch):
    import app.services.search_store as store

    async def down(query):
        raise d.DanawaUnavailable("점검")

    async def nothing(query):
        return None

    monkeypatch.setattr(d, "_fetch_raw_items", down)
    monkeypatch.setattr(store, "load_fallback", nothing)
    with pytest.raises(d.DanawaUnavailable):
        asyncio.run(d.danawa_search_products(query="냉장고", category="냉장고"))


def test_정상이면_stale_표시_없음(monkeypatch):
    async def ok(query):
        return list(STORED)

    monkeypatch.setattr(d, "_fetch_raw_items", ok)
    res = asyncio.run(d.danawa_search_products(query="냉장고", category="냉장고"))
    assert res["total"] == 2 and "stale" not in res


def test_검색어_속_단어로_저장된_결과에서_나머지_단어로_거름():
    import app.services.search_store as store
    hits = [it for it in STORED if store._matches(it, ["삼성", "비스포크"])]
    assert [it["id"] for it in hits] == ["1"]


def test_load_fallback_같은_검색어가_없으면_품목_결과에서_찾음(monkeypatch):
    import json
    import app.database as db
    import app.services.search_store as store

    async def fetchone(sql, args=None):
        return None   # "삼성 비스포크 냉장고"로 저장된 건 없음

    async def fetchall(sql, args=None):
        assert "search_store" in sql
        return [{"query": "냉장고", "items": json.dumps(STORED, ensure_ascii=False), "updated_at": 1795700000.0}]

    monkeypatch.setattr(store, "_table_ready", True)
    monkeypatch.setattr(db, "fetchone", fetchone)
    monkeypatch.setattr(db, "fetchall", fetchall)
    items, saved_at = asyncio.run(store.load_fallback("삼성 비스포크 냉장고"))
    assert [it["id"] for it in items] == ["1"] and saved_at == 1795700000.0
