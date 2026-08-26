import re

import httpx
from bs4 import BeautifulSoup

from app.config import CATEGORY_RULES

_DANAWA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

_RENTAL_KW = ["렌탈", "월렌탈", "렌탈료", "리스", "렌트", "월정액", "구독"]

_COUNT_DIGITS_RE = re.compile(r"\d+")


def _parse_item(li) -> dict | None:
    """다나와 검색결과 li.prod_item 하나를 네이버 search_products()와 동일한 item 형태로 변환."""
    name_a = li.select_one(".prod_name a")
    if not name_a:
        return None

    pcode_input = li.select_one("input[name='compareValue']")
    pid = pcode_input["value"] if pcode_input else ""

    price_input = li.select_one("input[id^='min_price_']")
    price = int(price_input["value"]) if price_input and price_input.get("value", "").isdigit() else 0

    image = ""
    img = li.select_one(".thumb_image img")
    if img:
        src = img.get("src", "")
        if src and "noImg" not in src:
            image = "https:" + src if src.startswith("//") else src

    maker_btn = li.select_one("[data-maker-name]")
    brand = maker_btn.get("data-maker-name", "").strip() if maker_btn else ""

    score_el = li.select_one(".text__score")
    review_score = float(score_el.get_text(strip=True)) if score_el else 0.0

    review_count = 0
    count_el = li.select_one(".text__number")
    if count_el:
        m = _COUNT_DIGITS_RE.search(count_el.get_text(strip=True).replace(",", ""))
        review_count = int(m.group()) if m else 0

    return {
        "id":          pid,
        "title":       name_a.get_text(strip=True),
        "brand":       brand,
        "price":       price,
        "image":       image,
        "link":        name_a.get("href", ""),
        "mallName":    "다나와 최저가비교",
        "reviewCount": review_count,
        "reviewScore": review_score,
    }


async def danawa_search_products(
    query: str,
    page: int = 1,
    display: int = 15,
    sort: str = "sim",
    category: str | None = None,
) -> dict:
    """네이버 쇼핑 검색(shop.json)이 막혀 있는 동안 다나와 통합검색을 긁어 동일한 응답 형태로 반환.
    다나와는 검색 결과를 한 페이지에 최대 40~50개 정도만 내려주므로, 여러 페이지를 합치는 대신
    한 번의 요청 결과 안에서 필터링·정렬·페이지네이션을 전부 처리한다."""
    params = {"query": query, "tab": "goods"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://search.danawa.com/dsearch.php", params=params, headers=_DANAWA_HEADERS)

    soup = BeautifulSoup(resp.text, "html.parser")
    raw_items = [_parse_item(li) for li in soup.select("li.prod_item")]
    items = [it for it in raw_items if it]

    items = [it for it in items if not any(kw in it["title"] for kw in _RENTAL_KW)]

    # 다나와 상품명은 "브랜드+모델명" 위주라 네이버 쇼핑 제목과 달리 카테고리 단어
    # ("냉장고" 등)가 안 들어있는 경우가 대부분 — 네이버처럼 제목에 가전 키워드가
    # 있는지로 걸러내면 카테고리 없이 호출할 때 결과가 전부 사라진다. 그래서 카테고리
    # 룰이 있을 때만 must/block 필터를 적용하고, 없을 때는 렌탈 제외 정도만 남긴다.
    rules = CATEGORY_RULES.get(category) if category else None
    if rules:
        safety = [
            it for it in items
            if not any(kw in it["title"] for kw in rules["block"])
            and (it["price"] == 0 or it["price"] >= rules["min_price"])
        ]
        must_ok = [it for it in safety if any(kw in it["title"] for kw in rules["must"])]
        items = must_ok if must_ok else safety

    if sort == "asc":
        items.sort(key=lambda x: x["price"] if x["price"] > 0 else 10**9)
    elif sort == "dsc":
        items.sort(key=lambda x: x["price"], reverse=True)

    total = len(items)
    start = (page - 1) * display
    page_items = items[start:start + display]

    return {"items": page_items, "total": total, "page": page, "display": display}
