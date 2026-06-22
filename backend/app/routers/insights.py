from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import TYPE_CHECKING

from app.dependencies import get_rag_optional
from app.services.insight_service import analyze

if TYPE_CHECKING:
    from app.rag_service import RAGService


class InsightRequest(BaseModel):
    query: str
    target: str = "b2b"
    top_k: int = 8


class InsightSource(BaseModel):
    rank: int
    text: str


class InsightResponse(BaseModel):
    query: str
    target: str
    report: str
    sources: list[InsightSource]


router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/rag-status")
async def rag_status(rag: "RAGService | None" = Depends(get_rag_optional)):
    if rag is None:
        return {"status": "disabled", "count": 0}
    return {"status": "ok", "count": rag.collection.count()}


@router.post("/analyze", response_model=InsightResponse)
async def analyze_insights(
    body: InsightRequest,
    rag: "RAGService | None" = Depends(get_rag_optional),
) -> InsightResponse:
    try:
        result = await analyze(
            query=body.query,
            rag=rag,
            target=body.target,
            top_k=body.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return InsightResponse(
        query=result["query"],
        target=result["target"],
        report=result["report"],
        sources=[InsightSource(**s) for s in result["sources"]],
    )
