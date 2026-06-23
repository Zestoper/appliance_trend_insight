import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

# Windows ProactorEventLoop는 httpx 병렬 SSL 연결에서 오류 발생 → SelectorEventLoop 강제 사용
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import get_pool, close_pool
import app.dependencies as deps
from app.services.price_service import _init_tables, price_snapshot_loop, price_alert_loop
from app.routers.insights import router as insights_router
from app.routers.naver import router as naver_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.user import router as user_router
from app.routers.analysis import router as analysis_router
from app.routers.b2b import router as b2b_router

if TYPE_CHECKING:
    from app.rag_service import RAGService


def _env_enabled(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in {"0", "false", "no", "off"}


async def _seed_rag(rag) -> None:
    try:
        from app.services.seed_rag import seed
        await seed(rag)
    except Exception as e:
        print(f"[RAG] seed error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    await _init_tables()
    if _env_enabled("ENABLE_RAG"):
        try:
            from app.rag_service import RAGService
            rag: "RAGService | None" = RAGService()
            deps.set_rag(rag)
            await _seed_rag(rag)  # 시딩 완료 후 서버 요청 수락
        except Exception as e:
            deps.set_rag(None)
            print(f"[RAG] initialization skipped: {e}")
    else:
        deps.set_rag(None)
        print("[RAG] disabled by ENABLE_RAG")

    snapshot_task = None
    if _env_enabled("ENABLE_PRICE_SNAPSHOT"):
        snapshot_task = asyncio.create_task(price_snapshot_loop())
    else:
        print("[snapshot] disabled by ENABLE_PRICE_SNAPSHOT")

    alert_task = asyncio.create_task(price_alert_loop())

    yield

    if snapshot_task:
        snapshot_task.cancel()
    alert_task.cancel()
    await close_pool()


app = FastAPI(lifespan=lifespan)

_default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(insights_router)
app.include_router(naver_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(user_router)
app.include_router(analysis_router)
app.include_router(b2b_router)