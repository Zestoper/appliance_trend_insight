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
    """쇼핑 상품 문서. 네이버 쇼핑 API가 막혀 있어서 다나와 검색 결과를 쓴다.
    가격·브랜드·평점을 metadata에 숫자로 넣어야 '40만원 이하' 같은 조건을 SQL로 거를 수 있다
    (벡터 검색은 뜻이 비슷한 문장을 찾을 뿐 숫자 비교를 못 한다)."""
    try:
        from app.config import CATEGORY_RULES
        from app.services.danawa_search import danawa_search_products
        res = await danawa_search_products(
            query=category, page=1, display=40, sort="sim",
            category=category if category in CATEGORY_RULES else None,
        )
        docs = []
        for it in res.get("items", []):
            title = it.get("title", "")
            price = int(it.get("price") or 0)
            if not title or price <= 0:
                continue
            brand = it.get("brand", "")
            score = float(it.get("reviewScore") or 0)
            reviews = int(it.get("reviewCount") or 0)
            text = f"[쇼핑] {title}"
            if brand:
                text += f" | 브랜드: {brand}"
            text += f" | 가격: {price:,}원"
            if score:
                text += f" | 평점: {score}/5 (리뷰 {reviews}개)"
            docs.append({
                "text": text,
                "metadata": {
                    "source": "shop", "product": category,
                    "title": title, "brand": brand, "price": price,
                    "score": score, "reviews": reviews, "link": it.get("link", ""),
                },
            })
        return docs
    except Exception as e:
        print(f"[RAG] {category} 상품 수집 실패: {e}")
        return []


async def seed_products(rag: "RAGService") -> int:
    """쇼핑 상품 문서만 새로 고친다 (가격이 바뀌므로 하루 한 번 돌리는 용도).
    새 데이터를 받아온 카테고리만 기존 상품 문서를 지우고 다시 넣는다."""
    from app.database import execute
    total = 0
    async with httpx.AsyncClient() as session:
        for category in _CATEGORIES:
            docs = await _fetch_products(session, category)
            if not docs:
                print(f"[RAG] {category}: 상품 0개 — 기존 데이터 유지")
                continue
            await execute(
                "DELETE FROM rag_documents WHERE metadata->>'source' = 'shop' AND metadata->>'product' = %s",
                (category,),
            )
            await rag.add_documents(docs)
            total += len(docs)
            print(f"[RAG] {category}: 상품 {len(docs)}개 갱신")
            await asyncio.sleep(1.0)  # 다나와에 부담 주지 않도록
    return total


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
    # 네이버 쇼핑 검색(shop.json)만 막혀있고 뉴스/블로그는 정상 동작 — _fetch_products()는
    # 자체 try/except로 빈 리스트를 반환하니 여기서 전체를 막을 필요는 없다.
    count = await rag.count()
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

    print(f"[RAG] 시딩 완료 — 총 {await rag.count()}개 문서")
