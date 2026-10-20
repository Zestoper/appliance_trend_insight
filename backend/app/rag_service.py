"""RAG 문서 저장 · 검색.

임베딩은 모델마다 좌표계(벡터 공간)가 달라서 서로 섞어 비교할 수 없다.
그래서 문서를 모델별 칸에 따로 저장하고 질문도 같은 모델로 임베딩해 같은 칸끼리만 비교한다.

검색 순서 (앞 단계가 막히면 다음 단계로)
  1) Gemini 임베딩   → rag_documents.embedding_gemini (768차원, 한국어 포함 다국어)
  2) HuggingFace     → rag_documents.embedding        (384차원, all-MiniLM-L6-v2)
  3) 키워드 검색     → 질문 단어가 많이 들어간 문서

402(크레딧 없음) · 429(한도 초과)처럼 다시 해도 같은 오류는 그 모델을 일정 시간 건너뛴다.
"""
import asyncio
import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass

import httpx

# ── 공통 ────────────────────────────────────────────────────────────────

class EmbeddingUnavailable(RuntimeError):
    """임베딩 모델을 지금 쓸 수 없음 (키 없음 · 크레딧 소진 · 한도 초과 · 권한 오류)"""


def _vec_str(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@dataclass
class _Provider:
    name: str
    column: str          # 이 모델 벡터를 저장하는 칸
    dim: int
    off_until: float = 0.0

    def key(self) -> str:
        return os.getenv(self.env_key, "").strip()

    @property
    def env_key(self) -> str:
        return "GEMINI_API_KEY" if self.name == "gemini" else "HUGGINGFACE_API_KEY"

    def available(self) -> bool:
        return bool(self.key()) and time.monotonic() >= self.off_until

    def pause(self, seconds: float, reason: str) -> None:
        self.off_until = time.monotonic() + seconds
        print(f"[RAG] {self.name} 임베딩 {int(seconds // 60)}분 동안 건너뜀 — {reason}")


GEMINI = _Provider("gemini", "embedding_gemini", 768)
_BACKFILL_BATCH = 50
_BACKFILL_SLEEP = 31.0  # 50개씩 31초 간격 → 분당 약 100개 (무료 한도 안쪽)
HF = _Provider("huggingface", "embedding", 384)
PROVIDERS = [GEMINI, HF]  # 검색 · 저장 우선순위

_PAUSE_FOR = {401: 3600, 402: 3600, 403: 3600, 429: 65}  # 429는 분당 한도라 1분 뒤 풀린다


async def _post_with_retry(client: httpx.AsyncClient, provider: _Provider, url: str, **kw) -> httpx.Response:
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.post(url, timeout=60.0, **kw)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in _PAUSE_FOR:
                # 다시 해도 같은 결과 → 재시도하지 않고 이 모델을 잠시 끈다
                provider.pause(_PAUSE_FOR[code], f"HTTP {code}")
                raise EmbeddingUnavailable(f"{provider.name} {code}") from e
            if 400 <= code < 500:
                raise
            last_err = e
        except httpx.TransportError as e:  # DNS · 연결 끊김 같은 일시 오류
            last_err = e
        wait = 3 * (attempt + 1)
        print(f"[RAG] {provider.name} 임베딩 재시도 {attempt + 1}/3 ({wait}s 후): {last_err!r}")
        await asyncio.sleep(wait)
    raise last_err  # type: ignore[misc]


# ── 모델별 임베딩 ───────────────────────────────────────────────────────

_GEMINI_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
_GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:batchEmbedContents"
_GEMINI_BATCH = 50


_gemini_plain = False  # True면 taskType · outputDimensionality 없이 보낸다 (API가 거부했을 때)


def _gemini_body(batch: list[str], task: str) -> dict:
    reqs = []
    for t in batch:
        r = {"model": f"models/{_GEMINI_MODEL}", "content": {"parts": [{"text": t[:8000]}]}}
        if not _gemini_plain:
            r["taskType"] = task
            r["outputDimensionality"] = GEMINI.dim
        reqs.append(r)
    return {"requests": reqs}


async def _embed_gemini(texts: list[str], task: str) -> list[list[float]]:
    global _gemini_plain
    out: list[list[float]] = []
    headers = {"x-goog-api-key": GEMINI.key()}
    async with httpx.AsyncClient() as client:
        for i in range(0, len(texts), _GEMINI_BATCH):
            batch = texts[i:i + _GEMINI_BATCH]
            try:
                resp = await _post_with_retry(client, GEMINI, _GEMINI_URL, json=_gemini_body(batch, task), headers=headers)
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 400 or _gemini_plain:
                    raise
                # 옵션 필드를 거부하면 기본 요청으로 다시 보내고 앞 768개만 쓴다
                # (Matryoshka 학습 모델이라 앞부분만 잘라 써도 된다)
                print("[RAG] gemini 옵션 필드 거부(400) — 기본 요청으로 전환")
                _gemini_plain = True
                resp = await _post_with_retry(client, GEMINI, _GEMINI_URL, json=_gemini_body(batch, task), headers=headers)
            # 차원을 줄이면 벡터 길이가 1이 아니라서 정규화해 둔다
            out.extend(_normalize(e["values"][:GEMINI.dim]) for e in resp.json()["embeddings"])
    return out


_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_HF_URL = f"https://router.huggingface.co/hf-inference/models/{_HF_MODEL}/pipeline/feature-extraction"
_HF_BATCH = 8


async def _embed_hf(texts: list[str], task: str) -> list[list[float]]:
    out: list[list[float]] = []
    async with httpx.AsyncClient() as client:
        for i in range(0, len(texts), _HF_BATCH):
            batch = texts[i:i + _HF_BATCH]
            resp = await _post_with_retry(
                client, HF, _HF_URL,
                json={"inputs": batch, "options": {"wait_for_model": True}},
                headers={"Authorization": f"Bearer {HF.key()}"},
            )
            data = resp.json()
            # 응답 형태: 2D (batch×dim) 또는 3D (batch×tokens×dim) → mean pool
            if isinstance(data[0][0], list):
                for sent in data:
                    dim = len(sent[0])
                    out.append([sum(t[d] for t in sent) / len(sent) for d in range(dim)])
            else:
                out.extend(data)
    return out


async def embed(provider: _Provider, texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    if not texts:
        return []
    if not provider.key():
        raise EmbeddingUnavailable(f"{provider.env_key} 없음")
    if not provider.available():
        raise EmbeddingUnavailable(f"{provider.name} 일시 중지 상태")
    fn = _embed_gemini if provider is GEMINI else _embed_hf
    return await fn(texts, task)


def embedding_available() -> bool:
    return any(p.available() for p in PROVIDERS)


# ── 저장 · 검색 ─────────────────────────────────────────────────────────

class RAGService:
    _schema_ready = False

    @staticmethod
    def _make_id(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def _ensure_schema(self) -> None:
        if RAGService._schema_ready:
            return
        from app.database import execute
        for sql in (
            f"ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS {GEMINI.column} vector({GEMINI.dim})",
            # 임베딩 없이 텍스트만 먼저 저장할 수 있도록 (이미 허용돼 있으면 아무 일도 안 함)
            f"ALTER TABLE rag_documents ALTER COLUMN {HF.column} DROP NOT NULL",
        ):
            try:
                await execute(sql)
            except Exception as e:
                print(f"[RAG] 스키마 보정 실패 ({sql[:60]}): {e}")
        RAGService._schema_ready = True

    async def count(self) -> int:
        from app.database import fetchone
        row = await fetchone("SELECT COUNT(*) AS cnt FROM rag_documents")
        return int(row["cnt"]) if row else 0

    async def add_documents(self, docs: list[dict]) -> None:
        if not docs:
            return
        from app.database import execute
        await self._ensure_schema()
        texts = [d["text"] for d in docs]
        ids = [self._make_id(t) for t in texts]
        metas = [json.dumps(d.get("metadata", {}), ensure_ascii=False) for d in docs]

        # 1) 텍스트 먼저 저장 (임베딩이 전부 막혀도 키워드 검색은 된다)
        for doc_id, text, meta in zip(ids, texts, metas):
            try:
                await execute(
                    """INSERT INTO rag_documents (id, text, metadata)
                       VALUES (%s, %s, %s::jsonb)
                       ON CONFLICT (id) DO UPDATE
                       SET text = EXCLUDED.text, metadata = EXCLUDED.metadata""",
                    (doc_id, text, meta),
                )
            except Exception as e:
                print(f"[RAG] 문서 저장 실패: {e}")

        # 2) 쓸 수 있는 모델마다 각자 칸에 벡터 저장
        for p in PROVIDERS:
            try:
                vecs = await embed(p, texts)
            except Exception as e:
                print(f"[RAG] {p.name} 임베딩 실패 — 나중에 다시 채웁니다: {e}")
                continue
            for doc_id, v in zip(ids, vecs):
                try:
                    await execute(
                        f"UPDATE rag_documents SET {p.column} = %s::vector WHERE id = %s",
                        (_vec_str(v), doc_id),
                    )
                except Exception as e:
                    print(f"[RAG] {p.name} 벡터 저장 실패: {e}")

    async def backfill_embeddings(self, limit: int = 3000, max_minutes: float = 40) -> dict:
        """모델별 칸이 비어 있는 문서를 채운다 (서버가 켜질 때 백그라운드로 실행).
        무료 한도(분당 요청 수)에 걸리면(429) 멈추지 않고 1분 쉬었다가 이어서 채운다."""
        from app.database import execute, fetchall
        await self._ensure_schema()
        filled: dict[str, int] = {}
        deadline = time.monotonic() + max_minutes * 60
        for p in PROVIDERS:
            if not p.key():
                continue
            done = 0
            while done < limit and time.monotonic() < deadline:
                if not p.available():
                    wait = p.off_until - time.monotonic()
                    if wait > _PAUSE_FOR[429] + 5:   # 크레딧 · 권한 문제(402 등)는 기다려도 안 풀린다
                        print(f"[RAG] {p.name} 빈칸 채우기 중단 — 사용 불가 상태")
                        break
                    await asyncio.sleep(max(wait, 1))
                    continue
                rows = await fetchall(
                    f"SELECT id, text FROM rag_documents WHERE {p.column} IS NULL LIMIT %s",
                    (min(_BACKFILL_BATCH, limit - done),),
                )
                if not rows:
                    break
                try:
                    vecs = await embed(p, [r["text"] for r in rows])
                except EmbeddingUnavailable:
                    continue   # 위에서 기다리거나 중단 여부를 판단한다
                except Exception as e:
                    print(f"[RAG] {p.name} 빈칸 채우기 중단: {e!r}")
                    break
                for r, v in zip(rows, vecs):
                    await execute(
                        f"UPDATE rag_documents SET {p.column} = %s::vector WHERE id = %s",
                        (_vec_str(v), r["id"]),
                    )
                done += len(rows)
                if done % 500 < _BACKFILL_BATCH:
                    print(f"[RAG] {p.name} 임베딩 빈칸 채우는 중… {done}개")
                await asyncio.sleep(_BACKFILL_SLEEP)  # 무료 한도(분당 요청 수) 여유
            if done:
                filled[p.name] = done
                print(f"[RAG] {p.name} 임베딩 빈칸 {done}개 채움")
        return filled

    @staticmethod
    def _where_sql(where: dict | None) -> tuple[list[str], list]:
        conds, params = [], []
        for k, v in (where or {}).items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
                raise ValueError(f"잘못된 메타데이터 키: {k}")
            conds.append(f"metadata->>'{k}' = %s")
            params.append(v)
        return conds, params

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[str]:
        from app.database import fetchall
        try:
            if await self.count() == 0:
                return []
            await self._ensure_schema()
            conds, params = self._where_sql(where)
            for p in PROVIDERS:
                try:
                    vec = (await embed(p, [query_text], task="RETRIEVAL_QUERY"))[0]
                except Exception as e:
                    print(f"[RAG] {p.name} 검색 불가 → 다음 단계: {e}")
                    continue
                cond_sql = " AND ".join(conds + [f"{p.column} IS NOT NULL"])
                rows = await fetchall(
                    f"SELECT text FROM rag_documents WHERE {cond_sql} "
                    f"ORDER BY {p.column} <=> %s::vector LIMIT %s",
                    params + [_vec_str(vec), n_results],
                )
                if rows:
                    return [r["text"] for r in rows]
                # 이 모델 칸이 아직 비어 있으면(빈칸 채우기 전) 다음 단계로
            return await self._keyword_query(query_text, n_results, where)
        except Exception as e:
            print(f"[RAG] query 오류: {e}")
            return []

    async def _keyword_query(
        self,
        query_text: str,
        n_results: int,
        where: dict | None = None,
    ) -> list[str]:
        """임베딩 없이 질문 단어가 많이 겹치는 문서 순으로 찾는다."""
        from app.database import fetchall
        words = [w for w in re.findall(r"[0-9A-Za-z가-힣]+", query_text) if len(w) >= 2]
        words = list(dict.fromkeys(words))[:6]
        if not words:
            return []
        score = " + ".join(["(CASE WHEN text ILIKE %s THEN 1 ELSE 0 END)"] * len(words))
        params: list = [f"%{w}%" for w in words]
        conds, wparams = self._where_sql(where)
        params += wparams
        where_sql = f"WHERE {' AND '.join(conds)}" if conds else ""
        params.append(n_results)
        try:
            rows = await fetchall(
                f"SELECT text FROM (SELECT text, ({score}) AS score FROM rag_documents {where_sql}) t "
                f"WHERE score > 0 ORDER BY score DESC LIMIT %s",
                params,
            )
            return [r["text"] for r in rows]
        except Exception as e:
            print(f"[RAG] 키워드 검색 오류: {e}")
            return []
