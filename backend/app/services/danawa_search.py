import asyncio
import re
import time

import httpx
from bs4 import BeautifulSoup

from app.config import CATEGORY_RULES

_DANAWA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

_RENTAL_KW = ["렌탈", "월렌탈", "렌탈료", "리스", "렌트", "월정액", "구독"]

_COUNT_DIGITS_RE = re.compile(r"\d+")

# 다나와 검색 응답이 2~3MB짜리 무거운 HTML이라 매번 새로 긁고 파싱하면 10~20초씩 걸린다 —
# 같은 검색어(query)는 raw 파싱 결과를 캐싱해 재사용한다 (category/sort/page는 캐시된
# raw 목록을 후처리만 다르게 하는 것이라 캐시 키에 포함하지 않는다).
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 1800  # 30분
_CACHE_MAX = 200  # 자유 검색어가 계속 쌓여 메모리를 무한정 잡아먹지 않도록 상한선


def _parse_item(li) -> dict | None:
    """다나와 검색결과 li.prod_item 하나를 네이버 search_products()와 동일한 item 형태로 변환."""
    name_a = li.select_one(".prod_name a")
    if not name_a:
        return None

    pcode_input = li.select_one("input[name='compareValue']")
    pid = pcode_input["value"] if pcode_input else ""

    price_input = li.select_one("input[id^='min_price_']")
    price = int(price_input["value"]) if price_input and price_input.get("value", "").isdigit() else 0

    # 다나와는 대부분의 이미지를 lazyload 처리해서 실제 URL이 src가 아니라 data-src에
    # 있고, src는 항상 placeholder(noImg_160.gif)로 채워져 있다 — data-src를 우선 본다.
    image = ""
    img = li.select_one(".thumb_image img")
    if img:
        src = img.get("data-src") or img.get("src", "")
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


def _parse_html(html: str) -> list[dict]:
    """CPU/메모리 바운드(대용량 HTML 파싱)라 asyncio.to_thread로 호출해 이벤트 루프를 막지 않는다.
    다나와 검색 페이지는 2~3MB인데 실제 필요한 상품 목록 영역은 20% 안팎이라, 전체를
    BeautifulSoup 트리로 만들면 Render 같은 메모리 제한 환경에서 OOM이 난다 — 상품 목록
    구간만 문자열 검색으로 잘라내 그 부분만 파싱한다 (마커를 못 찾으면 안전하게 전체 파싱)."""
    start = html.find("main_prodlist")
    end = html.rfind("prod_item")
    if start != -1 and end != -1:
        html = html[start:end + 20000]

    soup = BeautifulSoup(html, "html.parser")
    raw_items = [_parse_item(li) for li in soup.select("li.prod_item")]
    items = [it for it in raw_items if it]
    result = [it for it in items if not any(kw in it["title"] for kw in _RENTAL_KW)]
    soup.decompose()  # BS4 트리는 내부적으로 순환참조가 있어 즉시 끊어줘야 GC가 빨리 회수한다
    return result


async def _fetch_raw_items(query: str) -> list[dict]:
    cached = _CACHE.get(query)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    last_err: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    "https://search.danawa.com/dsearch.php",
                    params={"query": query, "tab": "goods"},
                    headers=_DANAWA_HEADERS,
                )
            resp.raise_for_status()
            items = await asyncio.to_thread(_parse_html, resp.text)
            if len(_CACHE) >= _CACHE_MAX:
                oldest_key = min(_CACHE, key=lambda k: _CACHE[k][0])
                del _CACHE[oldest_key]
            _CACHE[query] = (time.time(), items)
            return items
        except Exception as e:
            last_err = e
            if attempt == 0:
                await asyncio.sleep(1.0)
    # 재시도까지 실패하면 만료된 캐시라도 있으면 그거라도 반환 (완전히 빈 결과보다 낫다)
    if cached:
        return cached[1]
    raise last_err


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
    items = list(await _fetch_raw_items(query))

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
        # 다나와 검색엔 실제 상품과 무관한 액세서리/부속품(가격 0원으로 파싱되는 제휴
        # 리스팅)이 섞여 나오는데, "삼성냉장고RB30D4051S9냉장실 선반..."처럼 부속품
        # 제목에 우연히 카테고리 단어가 들어있으면 must 필터를 통과해버려서, 정작 카테고리
        # 단어가 없는 진짜 본품(가격 있음)보다 먼저 뽑히는 문제가 있었다 — 가격이 있는
        # 것만 must 후보로 삼는다.
        must_ok = [it for it in safety if it["price"] > 0 and any(kw in it["title"] for kw in rules["must"])]
        items = must_ok if must_ok else safety

    if sort == "asc":
        items.sort(key=lambda x: x["price"] if x["price"] > 0 else 10**9)
    elif sort == "dsc":
        items.sort(key=lambda x: x["price"], reverse=True)

    total = len(items)
    start = (page - 1) * display
    page_items = items[start:start + display]

    return {"items": page_items, "total": total, "page": page, "display": display}


_LIVE_PRICE_RE = re.compile(r'og:description"\s*content="최저가\s*([0-9,]+)원')
_LIVE_PRICE_CACHE: dict[str, tuple[float, int]] = {}
_LIVE_PRICE_TTL = 600  # 10분 — 검색결과에 박힌 가격(schema.org lowPrice)은 다나와 자체
# 캐시가 갱신 주기가 있어 상세페이지에 실제로 표시되는 "최저가"(og:description)보다
# 꽤 뒤처질 수 있다 — 상품 상세 조회처럼 정확도가 중요한 곳은 이 값을 대신 쓴다.


async def get_danawa_live_price(pcode: str) -> int | None:
    """다나와 상품 상세페이지(prod.danawa.com)의 og:description에 박힌 "최저가 N원"을
    읽어온다 — 검색결과 페이지에 있는 값보다 실제 화면에 보이는 최저가에 더 가깝다."""
    if not pcode:
        return None

    cached = _LIVE_PRICE_CACHE.get(pcode)
    if cached and time.time() - cached[0] < _LIVE_PRICE_TTL:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://prod.danawa.com/info/",
                params={"pcode": pcode},
                headers=_DANAWA_HEADERS,
            )
        m = _LIVE_PRICE_RE.search(resp.text)
        if not m:
            return None
        price = int(m.group(1).replace(",", ""))
        _LIVE_PRICE_CACHE[pcode] = (time.time(), price)
        return price
    except Exception:
        return None
