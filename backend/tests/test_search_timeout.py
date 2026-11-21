"""상품 검색이 느리거나 실패하면 500 대신 앱이 읽을 수 있는 503 {"detail": ...}을 주는지. 실행: python -m pytest tests/test_search_timeout.py"""
import asyncio
import os
import time

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.routers.naver as n  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def test_다나와가_느리면_시간_제한_후_503(monkeypatch):
    async def slow(**kw):
        await asyncio.sleep(5)

    monkeypatch.setattr(n, "NAVER_MAINTENANCE_MODE", True)
    monkeypatch.setattr(n, "danawa_search_products", slow)
    monkeypatch.setattr(n, "SEARCH_TIMEOUT", 0.2)
    t0 = time.time()
    with pytest.raises(HTTPException) as e:
        _run(n.search_products(query="삼성 에어컨", page=1, display=10, sort="sim", category=None))
    assert e.value.status_code == 503 and "detail" not in str(e.value.detail).lower()
    assert time.time() - t0 < 1


def test_다나와가_실패하면_503(monkeypatch):
    async def boom(**kw):
        raise RuntimeError("danawa down")

    monkeypatch.setattr(n, "NAVER_MAINTENANCE_MODE", True)
    monkeypatch.setattr(n, "danawa_search_products", boom)
    with pytest.raises(HTTPException) as e:
        _run(n.search_products(query="삼성 에어컨", page=1, display=10, sort="sim", category=None))
    assert e.value.status_code == 503


def test_트렌드_뒤쪽_작업은_별도_줄을_쓴다():
    from app.services import danawa_search as d
    assert d.background_fetch.get() is False
    async def inner():
        d.background_fetch.set(True)
        return d.background_fetch.get()
    assert _run(inner()) is True
    assert d.background_fetch.get() is False   # 다른 요청에는 영향 없음
