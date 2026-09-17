import pytest

from app.models import DocumentChunk
from app.vector_retrieval import VectorRetriever


class FakeEmbedder:
    def __init__(self, vectors: dict[str, list[float]]):
        self.vectors = vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors[text] for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self.vectors[query]


def _chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(chunk_id=chunk_id, source="report.pdf", page=1, text=text)


def test_vector_retriever_ranks_semantic_neighbor_first() -> None:
    chunks = [_chunk("sales", "营业收入增长"), _chunk("risk", "渠道库存压力")]
    embedder = FakeEmbedder(
        {
            "营业收入增长": [1.0, 0.0],
            "渠道库存压力": [0.0, 1.0],
            "货物积压带来什么问题": [0.1, 0.9],
        }
    )
    retriever = VectorRetriever(chunks, embedder)

    results = retriever.search("货物积压带来什么问题", top_k=1)

    assert results[0].chunk.chunk_id == "risk"
    assert results[0].score == pytest.approx(0.9939, abs=0.0001)


def test_vector_retriever_rejects_query_dimension_mismatch() -> None:
    chunks = [_chunk("sales", "营业收入增长")]
    embedder = FakeEmbedder(
        {"营业收入增长": [1.0, 0.0], "问题": [1.0, 0.0, 0.0]}
    )
    retriever = VectorRetriever(chunks, embedder)

    with pytest.raises(ValueError, match="维度"):
        retriever.search("问题")
