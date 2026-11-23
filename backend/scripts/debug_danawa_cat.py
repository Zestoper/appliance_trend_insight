"""다나와 검색 결과의 카테고리 보기. 사용: python3 -m scripts.debug_danawa_cat 검색어"""
import asyncio, os, sys
sys.path.insert(0, ".")
os.environ.setdefault("JWT_SECRET", "check-script-only")


async def main(q):
    from app.services.danawa_search import danawa_search_products
    from app.utils.danawa_category import category_from_danawa
    res = await danawa_search_products(query=q, page=1, display=10, sort="sim")
    for it in res.get("items", [])[:10]:
        print(category_from_danawa(it), "|", it.get("categories"), "|", it.get("title"))

asyncio.run(main(" ".join(sys.argv[1:])))
