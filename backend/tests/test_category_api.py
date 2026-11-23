import asyncio
import os
os.environ.setdefault("JWT_SECRET", "test")

import app.routers.naver as nv
import app.routers.b2b_search_analysis as bsa


def test_category_api_and_cache(monkeypatch):
    calls = []

    async def fake_detect(q, hint="", model=None):
        calls.append(q)
        return "의류관리기"
    monkeypatch.setattr(bsa, "detect_category", fake_detect)
    nv._CATEGORY_CACHE.clear()
    r1 = asyncio.run(nv.get_category("LG  뉴 스타일러"))
    r2 = asyncio.run(nv.get_category("LG 뉴 스타일러"))
    assert r1 == {"name": "LG 뉴 스타일러", "category": "의류관리기"} and r2["category"] == "의류관리기"
    assert calls == ["LG 뉴 스타일러"]          # 두 번째는 캐시


def test_category_api_not_found(monkeypatch):
    async def none_detect(q, hint="", model=None):
        return None
    monkeypatch.setattr(bsa, "detect_category", none_detect)
    nv._CATEGORY_CACHE.clear()
    assert asyncio.run(nv.get_category("아이폰 16 프로"))["category"] is None
