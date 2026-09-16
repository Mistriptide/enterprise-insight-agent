"""Orchestration for the minimal RAG pipeline."""

from pathlib import Path

from app.chunking import chunk_pages
from app.ingestion import load_pdfs
from app.llm import answer_question
from app.models import SearchResult
from app.retrieval import KeywordRetriever


class RAGPipeline:
    """Load documents once, then answer multiple questions."""

    def __init__(
        self,
        pdf_paths: list[str | Path],
        *,
        chunk_size: int = 700,
        overlap: int = 100,
    ):
        pages = load_pdfs(pdf_paths)
        self.chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)
        if not self.chunks:
            raise ValueError("未生成任何文本块。")
        self.retriever = KeywordRetriever(self.chunks)

    def retrieve(self, question: str, top_k: int = 4) -> list[SearchResult]:
        return self.retriever.search(question, top_k=top_k)

    def answer(self, question: str, top_k: int = 4) -> tuple[str, list[SearchResult]]:
        results = self.retrieve(question, top_k=top_k)
        return answer_question(question, results), results
