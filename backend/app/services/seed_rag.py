import asyncio
import re
import httpx
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag_service import RAGService

_CATEGORIES = [
    "에어컨", "냉장고", "세탁기", "건조기", "공기청정기",
    "로봇청소기", "식기세척기", "에어프라이어", "TV", "전기밥솥",
    "선풍기", "가습기", "제습기",
]

_NAVER_HEADERS: dict = {}


def _init_headers():
    _NAVER_HEADERS["X-Naver-Client-Id"] = os.getenv("NAVER_CLIENT_ID", "")
    _NAVER_HEADERS["X-Naver-Client-Secret"] = os.getenv("NAVER_CLIENT_SECRET", "")


def _strip(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def _fetch_news(session: httpx.AsyncClient, category: str, query_suffix: str = "트렌드 후기") -> list[dict]:
    try:
        resp = await session.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers=_NAVER_HEADERS,
            params={"query": f"{category} {query_suffix}", "display": 10, "sort": "date"},
            timeout=8.0,
        )
        items = resp.json().get("items", [])
        return [
            {
                "text": f"[뉴스] {_strip(it['title'])} - {_strip(it.get('description', ''))}",
                "metadata": {"source": "news", "product": category},
            }
            for it in items
            if it.get("title") and len(_strip(it.get("description", ""))) > 20
        ]
    except Exception:
        return []


async def _fetch_blog(session: httpx.AsyncClient, category: str, query_suffix: str = "사용후기 추천") -> list[dict]:
    try:
        resp = await session.get(
            "https://openapi.naver.com/v1/search/blog.json",
            headers=_NAVER_HEADERS,
            params={"query": f"{category} {query_suffix}", "display": 10, "sort": "date"},
            timeout=8.0,
        )
        items = resp.json().get("items", [])
        docs = []
        for it in items:
            title = _strip(it.get("title", ""))
            desc = _strip(it.get("description", ""))
            if not title or len(desc) < 30:
                continue
            docs.append({
                "text": f"[블로그] {title} - {desc[:300]}",
                "metadata": {"source": "blog", "product": category},
            })
        return docs
    except Exception:
        return []


async def _fetch_products(session: httpx.AsyncClient, category: str) -> list[dict]:
    try:
        resp = await session.get(
            "https://openapi.naver.com/v1/search/shop.json",
            headers=_NAVER_HEADERS,
            params={"query": category, "display": 10, "sort": "sim"},
            timeout=8.0,
        )
        items = resp.json().get("items", [])
        docs = []
        for it in items:
            title = _strip(it.get("title", ""))
            brand = it.get("brand") or it.get("maker", "")
            price = it.get("lprice", "")
            score = it.get("reviewScore", "")
            review = it.get("reviewCount", "")
            if not title:
                continue
            text = f"[쇼핑] {title}"
            if brand:
                text += f" | 브랜드: {brand}"
            if price:
                text += f" | 가격: {int(price):,}원"
            if score:
                text += f" | 평점: {score}/5 (리뷰 {review}개)"
            docs.append({"text": text, "metadata": {"source": "shop", "product": category}})
        return docs
    except Exception:
        return []


async def _seed_category(session: httpx.AsyncClient, rag: "RAGService", category: str) -> int:
    consumer_news, market_news, blog_review, blog_market, products = await asyncio.gather(
        _fetch_news(session, category, "트렌드 후기"),
        _fetch_news(session, category, "시장 동향 성장"),
        _fetch_blog(session, category, "사용후기 추천"),
        _fetch_blog(session, category, "시장 트렌드 소비자"),
        _fetch_products(session, category),
    )
    docs = consumer_news + market_news + blog_review + blog_market + products
    if docs:
        await rag.add_documents(docs)
    return len(docs)


async def seed(rag: "RAGService") -> None:
    count = rag.collection.count()
    if count > 0:
        print(f"[RAG] 이미 {count}개 문서 존재 — 시드 생략")
        return

    print("[RAG] 초기 데이터 시딩 시작...")
    _init_headers()

    total = 0
    async with httpx.AsyncClient() as session:
        for category in _CATEGORIES:
            try:
                n = await _seed_category(session, rag, category)
                total += n
                print(f"[RAG] {category}: {n}개 추가")
            except Exception as e:
                print(f"[RAG] {category} 시드 실패: {e}")
            await asyncio.sleep(0.3)

    print(f"[RAG] 시딩 완료 — 총 {rag.collection.count()}개 문서")
