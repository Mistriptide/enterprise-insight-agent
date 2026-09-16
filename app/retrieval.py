"""Explainable lexical retrieval baseline for Chinese and English text."""

from collections import Counter
import math
import re

from app.models import DocumentChunk, SearchResult


_ENGLISH_OR_NUMBER = re.compile(r"[a-zA-Z]+(?:[-_][a-zA-Z0-9]+)*|\d+(?:\.\d+)?%?")
_CHINESE_RUN = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """Create English words plus Chinese unigrams/bigrams without extra NLP libraries."""
    lowered = text.lower()
    tokens = _ENGLISH_OR_NUMBER.findall(lowered)
    for run in _CHINESE_RUN.findall(lowered):
        tokens.extend(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


class KeywordRetriever:
    """Rank chunks with query-term TF-IDF and query coverage.

    This is deliberately small and inspectable. It is a baseline, not a semantic
    retriever: synonyms that share no literal token will usually not match.
    """

    def __init__(self, chunks: list[DocumentChunk]):
        if not chunks:
            raise ValueError("检索器至少需要一个 chunk")
        self.chunks = chunks
        self._term_counts = [Counter(tokenize(chunk.text)) for chunk in chunks]
        self._document_frequency: Counter[str] = Counter()
        for counts in self._term_counts:
            self._document_frequency.update(counts.keys())

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("问题不能为空")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")

        query_terms = Counter(tokenize(query))
        if not query_terms:
            return []

        results: list[SearchResult] = []
        document_count = len(self.chunks)
        for chunk, counts in zip(self.chunks, self._term_counts, strict=True):
            score = 0.0
            matched = 0
            for term, query_frequency in query_terms.items():
                term_frequency = counts.get(term, 0)
                if not term_frequency:
                    continue
                matched += 1
                inverse_document_frequency = math.log(
                    (document_count + 1) / (self._document_frequency[term] + 1)
                ) + 1
                score += (1 + math.log(term_frequency)) * inverse_document_frequency * query_frequency

            if score > 0:
                coverage = matched / len(query_terms)
                score *= 1 + coverage
                if query.lower() in chunk.text.lower():
                    score += 2.0
                results.append(SearchResult(chunk=chunk, score=round(score, 4)))

        results.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return results[:top_k]
