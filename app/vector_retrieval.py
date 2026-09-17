"""Local dense-vector retrieval powered by a small multilingual ONNX model."""

from collections.abc import Sequence
import math
from pathlib import Path
from typing import Protocol

from app.models import DocumentChunk, SearchResult


DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


class Embedder(Protocol):
    """Minimal interface that keeps the retriever independent of one library."""

    def embed_documents(self, texts: list[str]) -> list[Sequence[float]]:
        """Return one dense vector per document chunk."""

    def embed_query(self, query: str) -> Sequence[float]:
        """Return one dense vector for a user query."""


class FastEmbedEncoder:
    """Generate local embeddings with FastEmbed and ONNX Runtime."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: str | Path = "data/model_cache",
    ):
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "向量检索需要 fastembed，请先执行 pip install -r requirements.txt"
            ) from exc

        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(cache_path))

    def embed_documents(self, texts: list[str]) -> list[Sequence[float]]:
        return list(self._model.passage_embed(texts))

    def embed_query(self, query: str) -> Sequence[float]:
        vectors = list(self._model.query_embed(query))
        if len(vectors) != 1:
            raise ValueError("查询应返回一个 Embedding")
        return vectors[0]


def _normalize(vector: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in vector)
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("Embedding 模型返回了零向量")
    return tuple(value / norm for value in values)


class VectorRetriever:
    """Rank chunks by cosine similarity in embedding space."""

    def __init__(self, chunks: list[DocumentChunk], embedder: Embedder):
        if not chunks:
            raise ValueError("检索器至少需要一个 chunk")
        self.chunks = chunks
        self.embedder = embedder
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding 数量与 chunk 数量不一致")
        self._vectors = [_normalize(vector) for vector in vectors]
        dimensions = {len(vector) for vector in self._vectors}
        if len(dimensions) != 1:
            raise ValueError("Embedding 向量维度不一致")
        self.dimension = dimensions.pop()

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("问题不能为空")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")

        query_vector = _normalize(self.embedder.embed_query(query))
        if len(query_vector) != self.dimension:
            raise ValueError("查询向量与文档向量维度不一致")

        results = [
            SearchResult(
                chunk=chunk,
                score=round(sum(a * b for a, b in zip(query_vector, vector, strict=True)), 4),
            )
            for chunk, vector in zip(self.chunks, self._vectors, strict=True)
        ]
        results.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return results[:top_k]
