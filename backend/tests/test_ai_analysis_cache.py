"""AI 분석(/api/ai-analysis) 결과 캐시 (#71).
실행: python -m pytest tests/test_ai_analysis_cache.py"""
import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test")

import app.routers.analysis as an  # noqa: E402
import app.services.naver_cache as nc  # noqa: E402

GOOD = {"analysis": {"score": 4.2, "summary": "좋음"}, "reviews": []}


def run(c):
    return asyncio.run(c)


def setup(monkeypatch, result=GOOD, db=None, delay=0.0):
    an._AI_CACHE.clear()
    an._AI_INFLIGHT.clear()
    calls = {"compute": 0, "saved": []}
    db = {} if db is None else db

    async def compute(query, category):
        calls["compute"] += 1
        await asyncio.sleep(delay)
        return result

    async def get_db(key):
        return db.get(key)

    async def set_db(key, data, ttl_hours=168):
        db[key] = data
        calls["saved"].append((key, ttl_hours))

    monkeypatch.setattr(an, "_compute_ai_analysis", compute)
    monkeypatch.setattr(nc, "get_db_cache", get_db)
    monkeypatch.setattr(nc, "set_db_cache", set_db)
    return calls, db


def test_두번째부터는_AI를_다시_부르지_않음(monkeypatch):
    calls, _ = setup(monkeypatch)
    assert run(an.get_ai_analysis("LG 디오스 S834MEE111", "냉장고")) == GOOD
    assert run(an.get_ai_analysis("LG  디오스 S834MEE111 ", "냉장고")) == GOOD   # 공백만 다른 검색어도 같은 결과
    assert calls["compute"] == 1
    assert calls["saved"][0][1] == 12


def test_서버를_다시_켜도_DB에서_꺼내_씀(monkeypatch):
    key = an._ai_cache_key("LG 디오스 S834MEE111", "냉장고")
    calls, _ = setup(monkeypatch, db={key: GOOD})
    assert run(an.get_ai_analysis("LG 디오스 S834MEE111", "냉장고")) == GOOD
    assert calls["compute"] == 0


def test_품목이_다르면_따로_분석(monkeypatch):
    calls, _ = setup(monkeypatch)
    run(an.get_ai_analysis("삼성 비스포크", "냉장고"))
    run(an.get_ai_analysis("삼성 비스포크", "김치냉장고"))
    assert calls["compute"] == 2


def test_실패나_데이터_부족은_저장하지_않음(monkeypatch):
    bad = {"analysis": None, "reviews": [], "error": "분석할 데이터가 부족합니다"}
    calls, db = setup(monkeypatch, result=bad)
    run(an.get_ai_analysis("없는 제품 XYZ", None))
    run(an.get_ai_analysis("없는 제품 XYZ", None))
    assert calls["compute"] == 2 and db == {}


def test_동시에_두번_들어와도_AI는_한번(monkeypatch):
    calls, _ = setup(monkeypatch, delay=0.05)

    async def both():
        return await asyncio.gather(an.get_ai_analysis("LG 디오스 S834MEE111", "냉장고"),
                                    an.get_ai_analysis("LG 디오스 S834MEE111", "냉장고"))
    a, b = run(both())
    assert a == b == GOOD and calls["compute"] == 1


def test_DB가_안되어도_분석은_돌려줌(monkeypatch):
    calls, _ = setup(monkeypatch)

    async def broken(*a, **k):
        raise ConnectionError("DB 끊김")
    monkeypatch.setattr(nc, "get_db_cache", broken)
    monkeypatch.setattr(nc, "set_db_cache", broken)
    assert run(an.get_ai_analysis("LG 디오스 S834MEE111", "냉장고")) == GOOD
