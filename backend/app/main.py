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

# Render는 Python 런타임으로 배포돼 Dockerfile의 ENV MALLOC_ARENA_MAX가 적용되지 않는다.
# 다나와 HTML 파싱을 스레드에서 돌리면 glibc가 스레드마다 메모리 영역(arena)을 새로 만들어
# 반납하지 않고 쌓아두므로 512MB 무료 서버에서 메모리 초과로 죽는다 → 시작할 때 영역 수를 2개로 제한
if sys.platform.startswith("linux"):
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").mallopt(-8, 2)  # -8 = M_ARENA_MAX
    except Exception:
        pass

# Render는 터미널이 아니라서 print 출력이 버퍼에 쌓였다가 한참 뒤에 로그에 찍힌다 → 줄마다 바로 내보내기
sys.stdout.reconfigure(line_buffering=True)

from app.database import get_pool, close_pool
import app.dependencies as deps
from app.services.price_service import _init_tables, price_snapshot_loop, price_alert_loop
from app.services.public_data import ext_data_refresh_loop
from app.routers.insights import router as insights_router
from app.routers.naver import router as naver_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.user import router as user_router
from app.routers.analysis import router as analysis_router
from app.routers.b2b import router as b2b_router
from app.routers.payments import router as payments_router

if TYPE_CHECKING:
    from app.rag_service import RAGService


def _env_enabled(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in {"0", "false", "no", "off"}


async def _seed_rag(rag) -> None:
    await asyncio.sleep(30)  # Render 네트워크 초기화 대기
    try:
        from app.services.seed_rag import seed
        await seed(rag)
    except Exception as e:
        print(f"[RAG] seed error: {e}")
    try:
        # 모델별 임베딩 칸 중 비어 있는 곳 채우기 (예: Gemini 키를 새로 넣었을 때 기존 문서)
        await rag.backfill_embeddings()
    except Exception as e:
        print(f"[RAG] 빈칸 채우기 오류: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    await _init_tables()
    if _env_enabled("ENABLE_RAG"):
        try:
            from app.rag_service import RAGService
            rag: "RAGService | None" = RAGService()
            deps.set_rag(rag)
            asyncio.create_task(_seed_rag(rag))  # 백그라운드 시딩 (서버 먼저 기동)
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

    async def _mem_log_loop():
        from app.utils.memory import rss_mb
        while True:
            await asyncio.sleep(30)
            print(f"[mem] {rss_mb()}MB")
    mem_task = asyncio.create_task(_mem_log_loop())

    alert_task = asyncio.create_task(price_alert_loop())
    ext_data_task = asyncio.create_task(ext_data_refresh_loop())

    yield

    if snapshot_task:
        snapshot_task.cancel()
    alert_task.cancel()
    ext_data_task.cancel()
    mem_task.cancel()
    await close_pool()


app = FastAPI(lifespan=lifespan)

# 무거운 API가 끝나면 메모리를 운영체제에 돌려주고 사용량을 로그로 남긴다 (메모리 초과 원인 추적용)
_HEAVY_PATHS = ("/api/b2b/search-analysis", "/api/trend", "/api/report", "/api/ai-analysis",
                "/api/timing", "/api/b2b/", "/api/insights")


# 무거운 API(외부 페이지 여러 개 수집 + 파싱 + LLM)는 동시에 2개까지만 처리하고 나머지는 줄을 세운다.
# 여러 개가 한꺼번에 돌면 각자 수십 MB씩 써서 512MB를 넘을 수 있다.
_HEAVY_SEM = asyncio.Semaphore(2)


@app.middleware("http")
async def _memory_guard(request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith(_HEAVY_PATHS):
        return await call_next(request)
    from app.utils.memory import rss_mb, trim
    async with _HEAVY_SEM:
        trim()
        response = await call_next(request)
        before = rss_mb()
        after = trim()
    print(f"[mem] {path} 끝 {before}MB → 정리 후 {after}MB")
    return response

app.add_middleware(
    CORSMiddleware,
    # 우리 프런트(배포 · Vercel 미리보기 · 로컬)만 허용. 다른 주소는 CORS_ORIGINS 환경변수에 쉼표로 추가
    allow_origins=[o.strip() for o in os.getenv(
        "CORS_ORIGINS",
        "https://appliance-trend-insight.vercel.app,http://localhost:5173,http://localhost:3000",
    ).split(",") if o.strip()],
    allow_origin_regex=r"https://appliance-trend-insight[a-z0-9-]*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights_router)
app.include_router(naver_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(user_router)
app.include_router(analysis_router)
app.include_router(b2b_router)
app.include_router(payments_router)


@app.get("/")
async def root():
    return {"status": "ok"}