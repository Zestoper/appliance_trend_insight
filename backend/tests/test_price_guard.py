"""가격 안전장치 테스트. 실행: cd backend && python -m pytest tests/test_price_guard.py"""
import asyncio
import sys
import types

from app.utils.accessory_filter import wants_accessory
from app.utils.price_guard import sanitize_items, is_plausible_price

ROBOROCK = [
    {"title": "로보락 S9 MaxV Ultra 전용 울트라도크 거름망 (1개)", "price": 8300},
    {"title": "로보락 S9 MaxV Ultra 물걸레포 6매", "price": 15900},
    {"title": "로보락 S9 MaxV Ultra 사이드 브러시 교체용", "price": 9900},
    {"title": "로보락 S9 MaxV Ultra 더스트백 3개입", "price": 18000},
    {"title": "로보락 S9 MaxV Ultra 렌탈 월 39,900원", "price": 39900},
    {"title": "로보락 S9 MaxV Ultra 로봇청소기 화이트", "price": 1090000},
    {"title": "로보락 S9 MaxV Ultra 정품 직구", "price": 989000},
]


def _titles(items):
    return [it["title"] for it in items]


def test_소모품_렌탈을_빼면_본품만_남는다():
    assert _titles(sanitize_items(ROBOROCK)) == ["로보락 S9 MaxV Ultra 로봇청소기 화이트", "로보락 S9 MaxV Ultra 정품 직구"]


def test_소모품만_있으면_빈_목록():
    assert sanitize_items(ROBOROCK[:4]) == []


def test_기준가로_다른_제품_가격_제외():
    items = ROBOROCK + [{"title": "로보락 S9 MaxV Ultra 도킹 스테이션 단품", "price": 320000}]
    assert "로보락 S9 MaxV Ultra 도킹 스테이션 단품" not in _titles(sanitize_items(items, ref_price=1090000))


def test_소모품을_찾는_검색어는_거르지_않는다():
    assert wants_accessory("로보락 S9 거름망")
    assert wants_accessory("FQ18D7 필터")
    assert not wants_accessory("로보락 S9 MaxV Ultra")
    assert not wants_accessory("FQ18D7DWAN")


def _fake_db(prices):
    db = types.ModuleType("app.database")

    async def fetchall(sql, args=None):
        return [{"min_price": p} for p in prices]
    db.fetchall = fetchall
    return db


def test_최근_가격과_너무_다르면_저장_안_함(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.database", _fake_db([1090000, 1080000, 1100000, 1095000]))
    ok = lambda p: asyncio.run(is_plausible_price("93806297", "로보락 S9 MaxV Ultra", p, "2026-11-21"))
    assert ok(1050000)          # 평소 가격
    assert ok(900000)           # 할인 (17%)
    assert not ok(8300)         # 거름망 가격
    assert not ok(5000000)      # 다른 제품


def test_소모품_이름은_저장_안_함(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.database", _fake_db([]))
    assert not asyncio.run(is_plausible_price("1", "로보락 S9 MaxV Ultra 전용 울트라도크 거름망 (1개)", 8300))
    assert asyncio.run(is_plausible_price("2", "로보락 S9 MaxV Ultra", 1090000))   # 이력이 없으면 막지 않음
