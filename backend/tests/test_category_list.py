"""다나와 상품 검색이 막혔을 때 품목 요청을 품목 목록 페이지(prod.danawa.com/list)에서 실시간으로 가져오는지.
실행: python -m pytest tests/test_category_list.py"""
import asyncio
import json
import os

os.environ.setdefault("JWT_SECRET", "test")

import httpx  # noqa: E402
import app.services.danawa_search as d  # noqa: E402
import app.services.search_store as store  # noqa: E402


def run(c):
    return asyncio.run(c)


def product(pid, name, price, cats, status=1):
    return {"id": pid, "makerName": name.split()[0], "productName": name, "modelName": name.split()[-1],
            "price": {"min": price, "initial": 0}, "category": {"codes": [], "names": cats},
            "image": {"url": f"https://img.danuri.io/catalog-image/{pid}.jpg?shrink=130"},
            "productUrl": f"https://prod.danawa.com/info/?pcode={pid}&cate=102110",
            "registerDate": "26.04.", "status": status}


def list_html(products):
    """Next.js 페이지처럼 products 배열을 self.__next_f.push 조각에 실어 보낸다."""
    payload = json.dumps({"x": 1, "products": products}, ensure_ascii=False, separators=(",", ":"))
    pad = "<div>" + "a" * 25000 + "</div>"
    return f'<html>{pad}<script>self.__next_f.push([1,{json.dumps(payload, ensure_ascii=False)}])</script></html>'


FRIDGE = ["가전", "냉장고", "양문형냉장고"]


class FakeClient:
    """httpx.AsyncClient 대신. cate 값마다 정해 둔 페이지를 돌려준다."""
    pages: dict = {}
    calls: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        cate = (params or {}).get("cate")
        FakeClient.calls.append(cate)
        page = FakeClient.pages.get(cate)
        if isinstance(page, Exception):
            raise page
        req = httpx.Request("GET", f"https://prod.danawa.com/list/?cate={cate}")
        return httpx.Response(200, text=page or "", request=req)


def setup(monkeypatch, pages, search_down=True):
    d._LIST_CACHE.clear()
    d._LIST_FAILED.clear()
    d._CACHE.clear()
    FakeClient.pages = pages
    FakeClient.calls = []
    monkeypatch.setattr(d.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(store, "save_items_background", lambda q, items: None)

    async def raw(query):
        raise d.DanawaUnavailable("검색 점검 중")
    if search_down:
        monkeypatch.setattr(d, "_fetch_raw_items", raw)

    async def no_stored(query):
        return None
    monkeypatch.setattr(store, "load_fallback", no_stored)


def test_목록_페이지_상품을_검색결과와_같은_모양으로():
    html = list_html([product(1, "LG전자 디오스 T876MEE1H1", 2177430, FRIDGE),
                      product(2, "단종 냉장고 X1", 0, FRIDGE, status=2)])
    items = d._parse_list_html(html)
    assert len(items) == 1          # 판매 중이 아닌 상품은 뺀다
    it = items[0]
    assert it["id"] == "1" and it["price"] == 2177430 and it["brand"] == "LG전자"
    assert it["categories"] == FRIDGE and it["release"] == "2026-04"
    assert it["image"].startswith("https://img.danuri.io/") and "pcode=1" in it["link"]


def test_검색이_막히면_품목은_목록_페이지로_실시간(monkeypatch):
    setup(monkeypatch, {"102110": list_html([product(1, "LG전자 디오스 T876MEE1H1", 2177430, FRIDGE)])})
    marks = []
    token = d.used_stored.set(marks)
    try:
        res = run(d.danawa_search_products("냉장고", category="냉장고"))
    finally:
        d.used_stored.reset(token)
    assert res["total"] == 1 and res["items"][0]["price"] == 2177430
    assert "stale" not in res          # 실시간이라 "저장된 정보" 안내가 붙지 않는다
    assert marks == []                 # 가격 알림 · 트렌드가 저장된 결과로 여기지 않는다


def test_칸이_여러_개면_번갈아_섞고_중복은_한_번만(monkeypatch):
    ac = ["계절가전", "에어컨", "스탠드형"]
    setup(monkeypatch, {
        "1032649": list_html([product(11, "삼성 A1", 1, ac), product(12, "삼성 A2", 1, ac)]),
        "1032653": list_html([product(21, "LG B1", 1, ac), product(11, "삼성 A1", 1, ac)]),
        "10357175": httpx.ConnectError("끊김"),   # 칸 하나가 안 돼도 나머지로
    })
    items = run(d.fetch_category_list("에어컨"))
    assert [it["id"] for it in items] == ["11", "21", "12"]
    assert FakeClient.calls == ["1032649", "1032653", "10357175"]


def test_목록도_캐시해서_다시_받지_않음(monkeypatch):
    setup(monkeypatch, {"102110": list_html([product(1, "LG전자 디오스 T876MEE1H1", 2177430, FRIDGE)])})
    run(d.fetch_category_list("냉장고"))
    run(d.fetch_category_list("냉장고"))
    assert FakeClient.calls == ["102110"]


def test_자유_검색어는_목록_페이지를_쓰지_않고_저장된_정보로(monkeypatch):
    setup(monkeypatch, {})

    async def stored(query):
        return [{"id": "9", "title": "LG전자 디오스 T876MEE1H1", "brand": "LG전자", "price": 2000000,
                 "image": "", "link": "", "categories": FRIDGE}], 1795800000.0
    monkeypatch.setattr(store, "load_fallback", stored)
    res = run(d.danawa_search_products("디오스 T876MEE1H1"))
    assert FakeClient.calls == [] and res["stale"] is True


def test_목록_페이지가_아닌_곳으로_넘어가면_저장된_정보로(monkeypatch):
    setup(monkeypatch, {})

    class Redirected(FakeClient):
        async def get(self, url, params=None, headers=None):
            req = httpx.Request("GET", "https://construction.danawa.com/notice")
            return httpx.Response(200, text="점검 중", request=req)
    monkeypatch.setattr(d.httpx, "AsyncClient", Redirected)

    async def stored(query):
        return [{"id": "9", "title": "LG 냉장고", "brand": "LG전자", "price": 2000000,
                 "image": "", "link": "", "categories": FRIDGE}], 1795800000.0
    monkeypatch.setattr(store, "load_fallback", stored)
    res = run(d.danawa_search_products("냉장고", category="냉장고"))
    assert res["stale"] is True and res["total"] == 1


def test_헤어드라이어_칸_이름_드라이기도_품목으로_인정():
    from app.utils.danawa_category import in_category, is_appliance_category
    it = {"categories": ["생활가전", "헤어기기", "드라이기"]}
    assert in_category(it, "헤어드라이어") and is_appliance_category(it)


def test_막힌_칸은_잠시_다시_부르지_않음(monkeypatch):
    setup(monkeypatch, {"102110": httpx.ConnectError("403")})
    for _ in range(3):
        try:
            run(d.fetch_category_list("냉장고"))
        except Exception:
            pass
    assert FakeClient.calls == ["102110"]   # 첫 실패 뒤 10분 동안은 다시 부르지 않는다
