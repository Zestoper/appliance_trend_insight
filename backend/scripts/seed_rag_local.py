#!/usr/bin/env python3
"""
로컬(한국 IP)에서 RAG 문서를 Supabase pgvector에 시딩합니다.

사용법:
    cd backend
    python -m scripts.seed_rag_local
    python -m scripts.seed_rag_local --reset  # 기존 문서 삭제 후 재시딩
"""
import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()


async def main(reset: bool = False):
    from app.database import get_pool, close_pool, execute, fetchone
    from app.rag_service import RAGService
    from app.services.seed_rag import seed

    await get_pool()

    if reset:
        await execute("DELETE FROM rag_documents")
        print("[RAG] 기존 문서 전체 삭제 완료")

    count_row = await fetchone("SELECT COUNT(*) AS cnt FROM rag_documents")
    current = int(count_row["cnt"]) if count_row else 0
    print(f"[RAG] 현재 문서 수: {current}개")

    rag = RAGService()
    # reset 시엔 count=0이므로 seed()가 다시 진행됨
    if reset:
        # seed() 내부의 count > 0 조기 종료를 우회
        from app.services.seed_rag import _CATEGORIES, _init_headers, _seed_category
        import httpx
        _init_headers()
        total = 0
        async with httpx.AsyncClient() as session:
            for category in _CATEGORIES:
                try:
                    n = await _seed_category(session, rag, category)
                    total += n
                    print(f"[RAG] {category}: {n}개 추가")
                except Exception as e:
                    print(f"[RAG] {category} 실패: {e}")
                await asyncio.sleep(0.3)
        final = await rag.count()
        print(f"\n완료! Supabase rag_documents에 총 {final}개 문서 저장됨")
    else:
        await seed(rag)

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="기존 문서 삭제 후 재시딩")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
