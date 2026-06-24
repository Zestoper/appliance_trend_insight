import asyncio
import hashlib
import os
import chromadb

_DEFAULT_CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "chroma_db")


def _make_embedding_function():
    if os.getenv("HUGGINGFACE_API_KEY", "").strip():
        from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction
        print("[RAG] HuggingFace API 임베딩 사용 (원격)")
        return HuggingFaceEmbeddingFunction()
    os.environ.setdefault("ONNXRUNTIME_PROVIDERS", "CPUExecutionProvider")
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    print("[RAG] 로컬 ONNX 임베딩 사용")
    return DefaultEmbeddingFunction()


class RAGService:
    def __init__(self, db_path: str = _DEFAULT_CHROMA_PATH):
        print("[RAG] 임베딩 함수 초기화 중...")
        self._ef = _make_embedding_function()
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="appliance_docs_v2",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        print("[RAG] 초기화 완료")

    @staticmethod
    def _make_id(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def add_documents(self, docs: list[dict]) -> None:
        """docs: [{"text": str, "metadata": dict}]"""
        if not docs:
            return
        texts = [d["text"] for d in docs]
        ids = [self._make_id(t) for t in texts]
        metadatas = [d.get("metadata", {}) for d in docs]
        try:
            await asyncio.to_thread(
                self.collection.upsert,
                ids=ids,
                documents=texts,
                metadatas=metadatas,
            )
        except Exception as e:
            print(f"[RAG] add_documents 오류: {e}")

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[str]:
        try:
            total = self.collection.count()
            if total == 0:
                return []
            n = min(n_results, total)
            kwargs: dict = {"query_texts": [query_text], "n_results": n}
            if where:
                kwargs["where"] = where
            results = await asyncio.to_thread(self.collection.query, **kwargs)
            return results["documents"][0] if results.get("documents") else []
        except Exception as e:
            print(f"[RAG] query 오류: {e}")
            return []
