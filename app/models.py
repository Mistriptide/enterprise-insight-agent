"""Shared data models for the RAG pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    """Text extracted from one PDF page."""

    source: str
    page: int
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    """A retrievable text unit with traceable source metadata."""

    chunk_id: str
    source: str
    page: int
    text: str


@dataclass(frozen=True)
class SearchResult:
    """A chunk returned by the baseline retriever."""

    chunk: DocumentChunk
    score: float

    @property
    def citation(self) -> str:
        return f"{self.chunk.source} · 第 {self.chunk.page} 页 · {self.chunk.chunk_id}"
