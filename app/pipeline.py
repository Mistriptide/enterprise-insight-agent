"""Orchestration for the minimal RAG pipeline."""

from pathlib import Path

from app.chunking import chunk_pages
from app.ingestion import load_pdfs
from app.llm import answer_question
from app.models import SearchResult
from app.retrieval import KeywordRetriever
from app.vector_retrieval import DEFAULT_EMBEDDING_MODEL, FastEmbedEncoder, VectorRetriever


class RAGPipeline:
    """Load documents once, then answer multiple questions."""

    def __init__(
        self,
        pdf_paths: list[str | Path],
        *,
        chunk_size: int = 700,
        overlap: int = 100,
        retrieval_mode: str = "keyword",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        model_cache: str | Path = "data/model_cache",
    ):
        pages = load_pdfs(pdf_paths)
        self.chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)
        if not self.chunks:
            raise ValueError("未生成任何文本块。")
        if retrieval_mode == "keyword":
            self.retriever = KeywordRetriever(self.chunks)
        elif retrieval_mode == "vector":
            encoder = FastEmbedEncoder(model_name=embedding_model, cache_dir=model_cache)
            self.retriever = VectorRetriever(self.chunks, encoder)
        else:
            raise ValueError("retrieval_mode 必须是 keyword 或 vector")
        self.retrieval_mode = retrieval_mode

    def retrieve(self, question: str, top_k: int = 4) -> list[SearchResult]:
        return self.retriever.search(question, top_k=top_k)

    def answer(self, question: str, top_k: int = 4) -> tuple[str, list[SearchResult]]:
        results = self.retrieve(question, top_k=top_k)
        return answer_question(question, results), results
