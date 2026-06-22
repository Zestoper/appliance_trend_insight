from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from app.rag_service import RAGService

_rag: "RAGService | None" = None


def set_rag(instance: "RAGService | None") -> None:
    global _rag
    _rag = instance


def get_rag() -> "RAGService":
    if _rag is None:
        raise HTTPException(status_code=503, detail="RAG service is not available")
    return _rag


def get_rag_optional() -> "RAGService | None":
    return _rag
