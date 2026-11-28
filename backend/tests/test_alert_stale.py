"""다나와 검색 장애로 저장된 예전 결과만 있을 때 가격 알림이 판단 · 저장 · 푸시하지 않는지.
실행: python -m pytest tests/test_alert_stale.py"""
import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test")

import app.routers.b2b_search_analysis as bsa  # noqa: E402
import app.services.price_service as ps  # noqa: E402
import app.services.danawa_search as d  # noqa: E402
from app.services import price_alerts as pa  # noqa: E402

ITEMS = [{"mall": "다나와 최저가비교", "brand": "LG전자", "title": "LG전자 디오스 S834MEE111", "price": 1500000, "link": "", "image": ""}]


def run(c):
    return asyncio.run(c)


def fake_sources(monkeypatch, stale: bool):
    async def fetch_items(query):
        if stale:   # danawa_search 가 저장된 결과로 대신 답했을 때 남기는 표시
            marks = d.used_stored.get()
            if marks is not None:
                marks.append(query)
        return list(ITEMS)

    async def history(query, name, only_real_launch=False):
        return {"history": [], "launch_price": None}

    monkeypatch.setattr(bsa, "fetch_product_price_items", fetch_items)
    monkeypatch.setattr(ps, "get_danawa_price_history", history)


def test_저장된_결과면_None(monkeypatch):
    fake_sources(monkeypatch, stale=True)
    assert run(pa._fetch_live_prices("LG전자 디오스 S834MEE111", "S834MEE111")) is None


def test_실시간이면_가격_그대로(monkeypatch):
    fake_sources(monkeypatch, stale=False)
    items, danawa = run(pa._fetch_live_prices("LG전자 디오스 S834MEE111", "S834MEE111"))
    assert items == ITEMS and danawa["history"] == []


def test_바로_확인도_저장된_결과면_가격을_저장하지_않음(monkeypatch):
    fake_sources(monkeypatch, stale=True)
    calls = {"saved": 0, "marked": 0, "built": 0}

    async def save(*a, **k):
        calls["saved"] += 1

    async def mark(*a, **k):
        calls["marked"] += 1

    async def build(*a, **k):
        calls["built"] += 1
        return {"min_price": 1}, None, None, None

    monkeypatch.setattr(pa, "save_signal_state", save)
    monkeypatch.setattr(pa, "mark_checked_no_price", mark)
    monkeypatch.setattr(bsa, "build_price_block", build)
    assert run(pa.refresh_product_state("LG전자 디오스 S834MEE111", "냉장고")) is None
    assert calls == {"saved": 0, "marked": 1, "built": 0}


def test_실시간이면_바로_확인이_저장함(monkeypatch):
    fake_sources(monkeypatch, stale=False)
    calls = {"saved": 0}

    async def save(*a, **k):
        calls["saved"] += 1

    async def build(*a, **k):
        return {"min_price": 1500000}, None, None, None

    monkeypatch.setattr(pa, "save_signal_state", save)
    monkeypatch.setattr(bsa, "build_price_block", build)
    assert run(pa.refresh_product_state("LG전자 디오스 S834MEE111", "냉장고")) == {"min_price": 1500000}
    assert calls["saved"] == 1
