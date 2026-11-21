"""트렌드 캐시 테스트: 재시작 직후에도 저장된 결과로 바로 응답하는지. 실행: python -m pytest tests/test_trend_cache.py"""
import asyncio
import os
import time

os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("GROQ_API_KEY", "test")

import app.routers.analysis as a  # noqa: E402


def test_재시작_직후에도_저장된_트렌드로_바로_응답():
    db, calls = {}, []

    async def load(k):
        return db.get(k)

    async def save(k, ts, r):
        db[k] = (ts, r)

    async def build(cat):
        calls.append(cat)
        await asyncio.sleep(0.2)
        return {"items": [{"t": "new"}] * 10}

    a._trend_db_load, a._trend_db_save, a._build_trend = load, save, build
    a._trend_cache.clear()

    async def main():
        # 저장된 결과가 전혀 없으면 기다려서 만든다
        r = await a.get_trend(None)
        assert r["items"][0]["t"] == "new" and len(calls) == 1
        # 재시작 흉내: 메모리는 비고 DB에는 1시간 지난 결과
        a._trend_cache.clear()
        db["전체"] = (time.time() - 3600, {"items": [{"t": "old"}]})
        t0 = time.time()
        r = await a.get_trend(None)
        assert r["items"][0]["t"] == "old" and time.time() - t0 < 0.1   # 기다리지 않고 바로
        await asyncio.sleep(0.3)
        assert len(calls) == 2 and db["전체"][1]["items"][0]["t"] == "new"  # 뒤에서 새로 만듦
        # 새 결과는 다시 만들지 않는다
        r = await a.get_trend(None)
        assert r["items"][0]["t"] == "new" and len(calls) == 2
        # 서버 시작 시 DB 결과를 메모리로 올린다
        a._trend_cache.clear()
        await a.warm_trend_cache()
        assert "전체" in a._trend_cache and len(calls) == 2

    asyncio.run(main())


def test_모자란_결과는_저장하지_않고_이전_결과를_지킨다():
    import time as _t
    db = {"전체": (_t.time() - 3600, {"items": [{"t": "old"}] * 10})}

    async def load(k):
        return db.get(k)

    async def save(k, ts, r):
        db[k] = (ts, r)

    async def build(cat):
        return {"items": [{"t": "partial"}] * 2}   # 10개 중 8개 검색 실패

    a._trend_db_load, a._trend_db_save, a._build_trend = load, save, build
    a._trend_cache.clear()

    async def main():
        r = await a.get_trend(None)
        assert len(r["items"]) == 10 and r["items"][0]["t"] == "old"
        await asyncio.sleep(0.05)
        assert len(db["전체"][1]["items"]) == 10    # 2개짜리로 덮어쓰지 않음

    asyncio.run(main())


def test_이미_저장된_2개짜리_결과는_바로_다시_만든다():
    import time as _t
    db = {"전체": (_t.time(), {"items": [{"t": "bad"}] * 2})}   # 방금 저장됐지만 모자람
    calls = []

    async def load(k):
        return db.get(k)

    async def save(k, ts, r):
        db[k] = (ts, r)

    async def build(cat):
        calls.append(cat)
        return {"items": [{"t": "good"}] * 10}

    a._trend_db_load, a._trend_db_save, a._build_trend = load, save, build
    a._trend_cache.clear()

    async def main():
        await a.get_trend(None)
        await asyncio.sleep(0.05)
        assert calls and len(db["전체"][1]["items"]) == 10

    asyncio.run(main())
