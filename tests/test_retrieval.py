import pytest

from app.models import DocumentChunk
from app.retrieval import KeywordRetriever, tokenize


def _chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(chunk_id=chunk_id, source="report.pdf", page=1, text=text)


def test_tokenize_supports_chinese_and_english() -> None:
    tokens = tokenize("Revenue 增长12%")

    assert "revenue" in tokens
    assert "增长" in tokens
    assert "12%" in tokens


def test_keyword_retriever_ranks_relevant_chunk_first() -> None:
    retriever = KeywordRetriever(
        [
            _chunk("c1", "公司营收增长百分之十二，高端产品贡献明显。"),
            _chunk("c2", "库存周转天数上升，渠道库存是主要风险。"),
        ]
    )

    results = retriever.search("渠道库存风险", top_k=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "c2"
    assert results[0].score > 0


def test_keyword_retriever_returns_empty_for_no_match() -> None:
    retriever = KeywordRetriever([_chunk("c1", "revenue growth")])
    assert retriever.search("库存风险") == []


def test_keyword_retriever_rejects_empty_question() -> None:
    retriever = KeywordRetriever([_chunk("c1", "revenue growth")])
    with pytest.raises(ValueError):
        retriever.search("  ")
