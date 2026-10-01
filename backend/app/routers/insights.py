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
    context: dict | None = None   # 직전 답변의 conditions — 이어 묻는 질문용
    history: list[dict] | None = None   # 최근 대화 [{role: user|ai, content}] — LLM 답변용


class InsightSource(BaseModel):
    rank: int
    text: str


class InsightResponse(BaseModel):
    query: str
    target: str
    report: str
    sources: list[InsightSource]
    conditions: dict | None = None   # 이번 질문에서 뽑은 조건 (프론트가 다음 질문 때 context로 보냄)
    answered_by: str = "llm"   # cache / template / market / market_stats_only / llm / stale_cache — 어느 단계에서 답했는지


router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/rag-status")
async def rag_status(rag: "RAGService | None" = Depends(get_rag_optional)):
    if rag is None:
        return {"status": "disabled", "count": 0}
    return {"status": "ok", "count": await rag.count()}


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
            context=body.context,
            history=body.history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return InsightResponse(
        query=result["query"],
        target=result["target"],
        report=result["report"],
        sources=[InsightSource(**s) for s in result["sources"]],
        conditions=result.get("conditions"),
        answered_by=result.get("answered_by", "llm"),
    )
