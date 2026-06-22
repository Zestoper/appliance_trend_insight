import asyncio
from datetime import date, timedelta, datetime

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import (
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_HEADERS,
    NAVER_SHOP_URL, YOUTUBE_API_KEY, CATEGORY_RULES, APPLIANCE_KEYWORDS, _DL_CACHE,
)
from app.utils.helpers import strip_html

router = APIRouter()


async def _fetch_transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = await asyncio.to_thread(
            YouTubeTranscriptApi.get_transcript,
            video_id,
            languages=["ko", "ko-KR"],
        )
        return " ".join(t["text"] for t in transcript[:80])[:300]
    except Exception:
        return ""


@router.get("/api/naver/products")
async def search_products(
    query:    str = Query(..., min_length=1),
    page:     int = Query(1,  ge=1),
    display:  int = Query(15, ge=1, le=100),
    sort:     str = Query("sim"),
    category: str = Query(None),
):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Naver API key not configured")

    rules = CATEGORY_RULES.get(category) if category else None
    fetch_display = 100 if rules else display
    start = (page - 1) * fetch_display + 1

    naver_sort = "sim" if (rules and sort in ("asc", "dsc")) else sort
    params = {"query": query, "display": fetch_display, "start": start, "sort": naver_sort}

    async with httpx.AsyncClient(timeout=8.0) as client:
        for attempt in range(3):
            resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS, params=params)
            if resp.status_code != 429:
                break
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))

    if resp.status_code != 200:
        if resp.status_code == 429:
            raise HTTPException(status_code=429, detail="Naver API 요청 한도 초과. 잠시 후 다시 시도해주세요.")
        raise HTTPException(status_code=resp.status_code, detail="Naver API error")

    data = resp.json()

    items = [
        {
            "id":          item.get("productId", ""),
            "title":       strip_html(item["title"]),
            "brand":       item.get("maker") or item.get("brand", ""),
            "price":       int(item["lprice"]) if item.get("lprice") else 0,
            "image":       item.get("image", ""),
            "link":        item.get("link", ""),
            "mallName":    item.get("mallName", ""),
            "reviewCount": int(item.get("reviewCount") or 0),
            "reviewScore": float(item.get("reviewScore") or 0),
        }
        for item in data.get("items", [])
    ]

    _RENTAL_MALL = ["렌탈", "리스", "렌트", "월정액"]
    items = [it for it in items if not any(kw in it["mallName"] for kw in _RENTAL_MALL)]

    if rules:
        safety = [
            it for it in items
            if not any(kw in it["title"] for kw in rules["block"])
            and (it["price"] == 0 or it["price"] >= rules["min_price"])
        ]
        must_ok = [it for it in safety if any(kw in it["title"] for kw in rules["must"])]
        items = (must_ok if must_ok else safety)

        if sort == "asc":
            items.sort(key=lambda x: x["price"] if x["price"] > 0 else 10**9)
        elif sort == "dsc":
            items.sort(key=lambda x: x["price"], reverse=True)

        items = items[:display]
    else:
        # 카테고리 룰 없을 때: 제목에 가전 키워드가 하나도 없으면 제거
        items = [it for it in items if any(kw in it["title"] for kw in APPLIANCE_KEYWORDS)]
        items = items[:display]

    return {"items": items, "total": data.get("total", 0), "page": page, "display": display}


@router.get("/api/naver/news")
async def get_news(
    query:   str = Query(..., min_length=1),
    display: int = Query(5, ge=1, le=10),
):
    url = "https://openapi.naver.com/v1/search/news.json"
    params = {"query": query, "display": display, "sort": "date"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=NAVER_HEADERS, params=params)
        data = resp.json()
        return {
            "items": [
                {
                    "title":       strip_html(item["title"]),
                    "description": strip_html(item["description"]),
                    "pubDate":     item["pubDate"],
                    "link":        item.get("originallink") or item["link"],
                }
                for item in data.get("items", [])
            ]
        }
    except Exception:
        return {"items": []}


@router.get("/api/naver/datalab")
async def get_datalab(query: str = Query(..., min_length=1)):
    end_date   = date.today()
    start_date = end_date - timedelta(days=30)

    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate":   end_date.strftime("%Y-%m-%d"),
        "timeUnit":  "date",
        "keywordGroups": [{"groupName": query, "keywords": [query]}],
    }
    cache_key = f"{query}_{start_date}"
    cached = _DL_CACHE.get(cache_key)
    if cached and (datetime.utcnow() - cached["ts"]).total_seconds() < 6 * 3600:
        return {"data": cached["data"]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
        data = resp.json()
        if "errorCode" in data:
            print(f"[datalab] API 오류: {data.get('errorMessage','')}")
            return {"data": _DL_CACHE.get(cache_key, {}).get("data", [])}
        results = data.get("results", [])
        result_data = results[0]["data"] if results else []
        _DL_CACHE[cache_key] = {"data": result_data, "ts": datetime.utcnow()}
        return {"data": result_data}
    except Exception as e:
        print(f"[datalab] 예외: {e}")
        return {"data": _DL_CACHE.get(cache_key, {}).get("data", [])}


@router.get("/api/youtube/search")
async def youtube_search(
    query:       str = Query(..., min_length=1),
    max_results: int = Query(4, ge=1, le=6),
):
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part":              "snippet",
        "q":                 f"{query} 리뷰",
        "type":              "video",
        "maxResults":        max_results,
        "relevanceLanguage": "ko",
        "key":               YOUTUBE_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
        data = resp.json()

        videos = [
            {
                "videoId":      item["id"]["videoId"],
                "title":        item["snippet"]["title"],
                "channelTitle": item["snippet"]["channelTitle"],
                "publishedAt":  item["snippet"]["publishedAt"][:10],
                "thumbnail":    item["snippet"]["thumbnails"]["medium"]["url"],
            }
            for item in data.get("items", [])
        ]

        transcript_tasks = [_fetch_transcript(v["videoId"]) for v in videos]
        try:
            transcripts = await asyncio.wait_for(
                asyncio.gather(*transcript_tasks, return_exceptions=True),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            transcripts = [""] * len(videos)

        for video, t in zip(videos, transcripts):
            video["transcript"] = t if isinstance(t, str) else ""

        if rag:
            docs = [
                {
                    "text": f"[YouTube] {v['title']} - {v['transcript']}",
                    "metadata": {"source": "youtube", "product": query},
                }
                for v in videos if v.get("transcript")
            ]
            if docs:
                asyncio.create_task(rag.add_documents(docs))

        return {"items": videos}
    except Exception:
        return {"items": []}


@router.get("/api/ppomppu")
async def get_ppomppu(query: str = Query(..., min_length=1)):
    import re
    import urllib.parse
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    try:
        from bs4 import BeautifulSoup

        encoded = urllib.parse.quote(query)
        url = f"https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu&keyword={encoded}&category=0"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept":          "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        soup = BeautifulSoup(resp.content, "html.parser")
        posts = []

        for row in soup.select("tr.baseList")[:10]:
            title_el = None
            for a in row.select("td.title a[href]"):
                if a.get("href", "").startswith("view") and a.get_text(strip=True):
                    title_el = a
                    break

            if not title_el:
                continue

            href = title_el.get("href", "")
            link = (
                "https://www.ppomppu.co.kr/zboard/" + href
                if href.startswith("view")
                else "https://www.ppomppu.co.kr" + href
            )

            post_date = ""
            for td in row.find_all("td"):
                if re.match(r"^\d{2}/\d{2}/\d{2}$", td.get_text(strip=True)):
                    post_date = td.get_text(strip=True)
                    break

            comment_el = row.select_one(".reply_num")

            posts.append({
                "title":        str(title_el.get_text(strip=True)),
                "link":         str(link),
                "date":         str(post_date),
                "commentCount": str(comment_el.get_text(strip=True).strip("[]")) if comment_el else "0",
            })

        kw_list = [w for w in query.split() if len(w) >= 2]
        if kw_list:
            posts = [p for p in posts if any(kw in p["title"] for kw in kw_list)]

        if rag and posts:
            docs = [
                {
                    "text": f"[뽐뿌] {p['title']}",
                    "metadata": {"source": "ppomppu", "product": query},
                }
                for p in posts
            ]
            asyncio.create_task(rag.add_documents(docs))

        return {"items": posts}
    except Exception as e:
        return {"items": [], "error": str(e)}


@router.get("/api/naver/product-image")
async def get_product_image(query: str = Query(..., min_length=1)):
    """네이버 쇼핑 검색으로 제품 대표 이미지 URL 반환."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Naver API key not configured")
    params = {"query": query, "display": 3, "sort": "sim"}
    async with httpx.AsyncClient(timeout=6.0) as client:
        resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Naver API error")
    items = resp.json().get("items", [])
    image = items[0].get("image", "") if items else ""
    return {"image": image}
