"""Small, reproducible retrieval evaluation utilities."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from app.models import SearchResult


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[SearchResult]: ...


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_source: str
    expected_page: int


@dataclass(frozen=True)
class CaseResult:
    case: EvaluationCase
    rank: int | None
    retrieved: tuple[str, ...]

    @property
    def hit(self) -> bool:
        return self.rank is not None


@dataclass(frozen=True)
class EvaluationReport:
    retriever_name: str
    top_k: int
    cases: tuple[CaseResult, ...]

    @property
    def recall_at_k(self) -> float:
        return sum(case.hit for case in self.cases) / len(self.cases) if self.cases else 0.0

    @property
    def mean_reciprocal_rank(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 / case.rank for case in self.cases if case.rank) / len(self.cases)


def load_cases(path: str | Path) -> list[EvaluationCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("评测集必须是 JSON 数组")
    cases = [
        EvaluationCase(
            case_id=str(item["id"]),
            question=str(item["question"]),
            expected_source=str(item["expected_source"]),
            expected_page=int(item["expected_page"]),
        )
        for item in data
    ]
    if not cases:
        raise ValueError("评测集不能为空")
    return cases


def evaluate(
    retriever: Retriever,
    cases: list[EvaluationCase],
    *,
    retriever_name: str,
    top_k: int = 2,
) -> EvaluationReport:
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")

    case_results: list[CaseResult] = []
    for case in cases:
        results = retriever.search(case.question, top_k=top_k)
        rank = next(
            (
                index
                for index, result in enumerate(results, start=1)
                if result.chunk.source == case.expected_source
                and result.chunk.page == case.expected_page
            ),
            None,
        )
        case_results.append(
            CaseResult(
                case=case,
                rank=rank,
                retrieved=tuple(result.citation for result in results),
            )
        )
    return EvaluationReport(
        retriever_name=retriever_name, top_k=top_k, cases=tuple(case_results)
    )
