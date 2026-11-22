"""상품명에 품목 이름 없이 라인 이름만 있어도 카테고리를 찾는다. 실행: python -m pytest tests/test_category_alias.py"""
import pytest

from app.config import _CATEGORY_MAP


def detect(text):
    for kw, cat in _CATEGORY_MAP.items():
        if kw in text:
            return cat
    return None


@pytest.mark.parametrize("name,cat", [
    ("삼성전자 비스포크 김치플러스 RQ33DG71J3EW", "냉장고"),
    ("위니아 딤채 스탠드형 WDQ57GTMRWS", "냉장고"),
    ("쿠쿠 김치톡톡 CRS-FWK0410W", "냉장고"),
    ("LG 디오스 김치냉장고 Z493MEE", "냉장고"),
    ("LG 휘센 제습기", "제습기"),   # 품목 이름이 있으면 그쪽이 먼저
])
def test_detect(name, cat):
    assert detect(name) == cat


@pytest.mark.parametrize("title,brand", [
    ("삼성전자 비스포크 김치플러스 RQ33DG71J2ET", "삼성전자"),
    ("LG 디오스 김치냉장고 Z493MEE", "LG전자"),
    ("위니아 딤채 WDQ57GTMRWS", "위니아"),
    ("비스포크 김치플러스 3도어", None),
])
def test_brand_from_title(title, brand):
    from app.routers.b2b_search_analysis import brand_from_title
    assert brand_from_title(title) == brand


def test_danawa_meta_new_page():
    """2026-11 다나와 개편 페이지 (등록월 사이에 빈 주석 · JSON)"""
    import os
    from app.services.price_service import parse_danawa_meta
    html = open(os.path.join(os.path.dirname(__file__), "fixtures", "danawa_meta_2026_11.html"), encoding="utf-8").read()
    meta = parse_danawa_meta(html)
    assert meta["release_date"] == "2024-10" and meta["maker"] == "삼성전자"
    # JSON만 있어도 읽는다
    only_json = html[html.find('\\"dateLabel'):]
    assert parse_danawa_meta('{\\"makerName\\":\\"삼성전자\\",' + only_json)["release_date"] == "2024-10"


def test_danawa_meta_old_page():
    from app.services.price_service import parse_danawa_meta
    meta = parse_danawa_meta("<span>등록월 : 2023.05.</span> 출시가 1,290,000원")
    assert meta["release_date"] == "2023-05" and meta["launch_price"] == 1290000


def test_danawa_lowest_price():
    import os
    from app.services.price_service import parse_danawa_meta
    html = open(os.path.join(os.path.dirname(__file__), "fixtures", "danawa_meta_2026_11.html"), encoding="utf-8").read()
    assert parse_danawa_meta(html)["lowest_price"] == 1143750


def test_price_block_uses_danawa_lowest(monkeypatch):
    """조건부 특가가 섞인 이력: 대표 최저가 114만원 기준으로 65만 · 76만 같은 점과 62만원 상품을 뺀다"""
    import asyncio
    from datetime import date
    import app.database as db
    from app.routers import b2b_search_analysis as sa

    async def fetchall(sql, args=None):
        return []

    async def execute(sql, args=None):
        return 1

    async def plausible(*a, **k):
        return True
    monkeypatch.setattr(db, "fetchall", fetchall)
    monkeypatch.setattr(db, "execute", execute)
    import app.utils.price_guard as pg
    monkeypatch.setattr(pg, "is_plausible_price", plausible)
    hist = [("2026-09-01", 761990), ("2026-09-08", 1199950), ("2026-09-22", 1173120), ("2026-09-29", 903270),
            ("2026-10-13", 1197670), ("2026-10-20", 654490), ("2026-11-17", 654490)]
    danawa = {"history": [{"period": d, "price": p} for d, p in hist], "launch_price": 1410110,
              "lowest_price": 1143750, "maker": "삼성전자"}
    items = [{"mall": "a", "brand": "", "title": "삼성 RQ33DG71J2ET 3도어", "price": 628320, "link": "", "image": ""},
             {"mall": "b", "brand": "삼성전자", "title": "삼성전자 비스포크 김치플러스 RQ33DG71J2ET", "price": 1143750, "link": "", "image": ""}]
    block, _, _, brand = asyncio.run(sa.build_price_block("삼성전자 비스포크 김치플러스 RQ33DG71J2ET", "RQ33DG71J2ET",
                                                          "RQ33DG71J2ET", "냉장고", items, danawa, 0.0, date(2026, 11, 22)))
    assert block["min_price"] == 1143750
    assert all(h["min_price"] >= 1143750 * 0.7 for h in block["price_history"])
    assert block["signal_type"] != "buy" and brand == "삼성전자"


def test_history_mismatch_uses_own_records(monkeypatch):
    """다나와 주간 이력(62~78만)이 대표가(109만)와 기준이 다르면 섞지 않고, 비교할 기록이 없으면 판단 보류"""
    import asyncio
    from datetime import date
    import app.database as db
    from app.routers import b2b_search_analysis as sa
    import app.utils.price_guard as pg

    async def fetchall(sql, args=None):
        return []

    async def execute(sql, args=None):
        return 1

    async def plausible(*a, **k):
        return True
    monkeypatch.setattr(db, "fetchall", fetchall)
    monkeypatch.setattr(db, "execute", execute)
    monkeypatch.setattr(pg, "is_plausible_price", plausible)
    hist = [("2026-09-15", 779990), ("2026-10-06", 640000), ("2026-10-27", 615990), ("2026-11-17", 615990)]
    danawa = {"history": [{"period": d, "price": p} for d, p in hist], "launch_price": None,
              "lowest_price": 1087460, "max_price_24m": 1260000}
    items = [{"mall": "a", "brand": "삼성전자", "title": "삼성전자 비스포크 김치플러스 RQ33DG71J3EW", "price": 1087460,
              "link": "", "image": ""}]
    block, _, _, _ = asyncio.run(sa.build_price_block("삼성전자 비스포크 김치플러스 RQ33DG71J3EW", "RQ33DG71J3EW",
                                                      "RQ33DG71J3EW", "냉장고", items, danawa, 2.0, date(2026, 11, 22)))
    assert block["history_mismatch"] and block["history_insufficient"]
    assert block["vs_hist_pct"] == 0.0 and block["signal_type"] == "wait" and block["fairness_type"] == "fair"
    assert all(h["min_price"] >= 1087460 * 0.7 for h in block["price_history"])
    assert block["launch_price"] is None and block["max_price_24m"] == 1260000


def test_product_search_has_sort_fields(monkeypatch):
    import asyncio
    from app.routers import b2b_search_analysis as sa

    async def fake_search(**kw):
        return {"items": [{"title": "삼성 비스포크 냉장고 RS84DB5002CW", "brand": "삼성전자", "price": 1500000,
                           "image": "", "link": "", "release": "2025-06", "reviewCount": 120, "reviewScore": 4.6}]}

    async def no_kemco(cat):
        return {}
    monkeypatch.setattr(sa, "search_products", fake_search)
    import app.services.public_data as pd
    monkeypatch.setattr(pd, "get_kemco_model_info_cached", no_kemco)
    it = asyncio.run(sa.get_product_search("냉장고", {}))["items"][0]
    assert it["release"] == "2025-06" and it["review_count"] == 120 and it["review_score"] == 4.6
