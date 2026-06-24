import asyncio
import hashlib
import json
import os
import httpx

_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_HF_URL = f"https://router.huggingface.co/hf-inference/models/{_HF_MODEL}/pipeline/feature-extraction"
_BATCH = 8


def _hf_key() -> str:
    return os.getenv("HUGGINGFACE_API_KEY", "").strip()


def _vec_str(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


async def _embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    key = _hf_key()
    if not key:
        raise RuntimeError("HUGGINGFACE_API_KEY 없음 — RAG 임베딩 불가")
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
            embeddings = await _embed(texts)
        except Exception as e:
            print(f"[RAG] 임베딩 실패: {e}")
            return
        for doc_id, text, meta, emb in zip(ids, texts, metadatas, embeddings):
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
            embeddings = await _embed([query_text])
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
