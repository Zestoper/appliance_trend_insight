import asyncio
import hashlib
import json
import os
import re
import time

import httpx

_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_HF_URL = f"https://router.huggingface.co/hf-inference/models/{_HF_MODEL}/pipeline/feature-extraction"
_BATCH = 8


def _hf_key() -> str:
    return os.getenv("HUGGINGFACE_API_KEY", "").strip()


def _vec_str(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


# HuggingFace 무료 크레딧이 떨어지면 402를 준다 → 그동안은 임베딩을 끄고 키워드 검색으로 대신한다
_EMBED_OFF_SECONDS = 3600
_embed_off_until = 0.0


class EmbeddingUnavailable(RuntimeError):
    """임베딩 API를 지금 쓸 수 없음 (키 없음 · 크레딧 소진 · 권한 오류)"""


def embedding_available() -> bool:
    return bool(_hf_key()) and time.monotonic() >= _embed_off_until


async def _embed(texts: list[str]) -> list[list[float]]:
    global _embed_off_until
    if not texts:
        return []
    key = _hf_key()
    if not key:
        raise EmbeddingUnavailable("HUGGINGFACE_API_KEY 없음")
    if time.monotonic() < _embed_off_until:
        raise EmbeddingUnavailable("임베딩 API 일시 중지 상태 (크레딧 소진 등)")
    headers = {"Authorization": f"Bearer {key}"}
    result: list[list[float]] = []
    last_err: Exception | None = None
    async with httpx.AsyncClient() as client:
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            for attempt in range(3):  # DNS 일시 실패 대비 최대 3회 재시도
                try:
                    resp = await client.post(
                        _HF_URL,
                        json={"inputs": batch, "options": {"wait_for_model": True}},
                        headers=headers,
                        timeout=60.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    # 응답 형태: 2D (batch×dim) 또는 3D (batch×tokens×dim) → mean pool
                    if isinstance(data[0][0], list):
                        for sent in data:
                            dim = len(sent[0])
                            result.append([sum(t[d] for t in sent) / len(sent) for d in range(dim)])
                    else:
                        result.extend(data)
                    last_err = None
                    break
                except httpx.HTTPStatusError as e:
                    code = e.response.status_code
                    if code in (401, 402, 403):
                        # 키 오류 · 크레딧 소진은 다시 해도 같으므로 재시도하지 않는다
                        _embed_off_until = time.monotonic() + _EMBED_OFF_SECONDS
                        print(f"[RAG] 임베딩 API 사용 불가({code}) — 1시간 동안 키워드 검색으로 대신합니다")
                        raise EmbeddingUnavailable(f"임베딩 API {code}") from e
                    last_err = e
                    wait = 5 * (attempt + 1)
                    print(f"[RAG] 임베딩 재시도 {attempt + 1}/3 ({wait}s 후): {e}")
                    await asyncio.sleep(wait)
                except Exception as e:
                    last_err = e
                    wait = 5 * (attempt + 1)
                    print(f"[RAG] 임베딩 재시도 {attempt + 1}/3 ({wait}s 후): {e}")
                    await asyncio.sleep(wait)
            if last_err:
                raise last_err
    return result


class RAGService:
    @staticmethod
    def _make_id(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def count(self) -> int:
        from app.database import fetchone
        row = await fetchone("SELECT COUNT(*) AS cnt FROM rag_documents")
        return int(row["cnt"]) if row else 0

    async def add_documents(self, docs: list[dict]) -> None:
        if not docs:
            return
        from app.database import execute
        texts = [d["text"] for d in docs]
        ids = [self._make_id(t) for t in texts]
        metadatas = [d.get("metadata", {}) for d in docs]
        try:
            embeddings: list = await _embed(texts)
        except Exception as e:
            print(f"[RAG] 임베딩 실패 — 텍스트만 저장합니다: {e}")
            embeddings = [None] * len(texts)
        for doc_id, text, meta, emb in zip(ids, texts, metadatas, embeddings):
            if emb is None:
                try:
                    # 이미 임베딩이 있는 문서는 그대로 두고 새 문서만 텍스트로 넣는다
                    await execute(
                        """INSERT INTO rag_documents (id, text, metadata)
                           VALUES (%s, %s, %s::jsonb)
                           ON CONFLICT (id) DO UPDATE
                           SET text = EXCLUDED.text, metadata = EXCLUDED.metadata""",
                        (doc_id, text, json.dumps(meta, ensure_ascii=False)),
                    )
                except Exception as e:
                    print(f"[RAG] 문서 저장 실패: {e}")
                continue
            try:
                await execute(
                    """INSERT INTO rag_documents (id, text, metadata, embedding)
                       VALUES (%s, %s, %s::jsonb, %s::vector)
                       ON CONFLICT (id) DO UPDATE
                       SET text      = EXCLUDED.text,
                           metadata  = EXCLUDED.metadata,
                           embedding = EXCLUDED.embedding""",
                    (doc_id, text, json.dumps(meta, ensure_ascii=False), _vec_str(emb)),
                )
            except Exception as e:
                print(f"[RAG] 문서 저장 실패: {e}")

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
            try:
                embeddings = await _embed([query_text])
            except Exception as e:
                print(f"[RAG] 벡터 검색 불가 — 키워드 검색 사용: {e}")
                return await self._keyword_query(query_text, n_results, where)
            vec = _vec_str(embeddings[0])
            if where:
                conds = []
                params: list = []
                for k, v in where.items():
                    conds.append(f"metadata->>{repr(k)} = %s")
                    params.append(v)
                params.extend([vec, n_results])
                rows = await fetchall(
                    f"SELECT text FROM rag_documents WHERE {' AND '.join(conds)} "
                    f"ORDER BY embedding <=> %s::vector LIMIT %s",
                    params,
                )
            else:
                rows = await fetchall(
                    "SELECT text FROM rag_documents ORDER BY embedding <=> %s::vector LIMIT %s",
                    (vec, n_results),
                )
            return [r["text"] for r in rows]
        except Exception as e:
            print(f"[RAG] query 오류: {e}")
            return []

    async def _keyword_query(
        self,
        query_text: str,
        n_results: int,
        where: dict | None = None,
    ) -> list[str]:
        """임베딩 없이 단어가 많이 겹치는 문서 순으로 찾는다."""
        from app.database import fetchall
        words = [w for w in re.findall(r"[0-9A-Za-z가-힣]+", query_text) if len(w) >= 2]
        words = list(dict.fromkeys(words))[:6]
        if not words:
            return []
        score = " + ".join(["(CASE WHEN text ILIKE %s THEN 1 ELSE 0 END)"] * len(words))
        params: list = [f"%{w}%" for w in words]
        conds = []
        for k, v in (where or {}).items():
            conds.append(f"metadata->>{repr(k)} = %s")
            params.append(v)
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
