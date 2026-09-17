import json
from pathlib import Path

from app.evaluation import EvaluationCase, evaluate, load_cases
from app.models import DocumentChunk, SearchResult


class FakeRetriever:
    def __init__(self, results: dict[str, list[SearchResult]]):
        self.results = results

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        return self.results[query][:top_k]


def _result(page: int) -> SearchResult:
    return SearchResult(
        chunk=DocumentChunk(
            chunk_id=f"report-p{page}-c1",
            source="report.pdf",
            page=page,
            text="text",
        ),
        score=1.0,
    )


def test_evaluate_calculates_recall_and_mrr() -> None:
    cases = [
        EvaluationCase("q1", "question one", "report.pdf", 1),
        EvaluationCase("q2", "question two", "report.pdf", 2),
    ]
    retriever = FakeRetriever(
        {"question one": [_result(1), _result(2)], "question two": [_result(1)]}
    )

    report = evaluate(retriever, cases, retriever_name="fake", top_k=2)

    assert report.recall_at_k == 0.5
    assert report.recall_at(1) == 0.5
    assert report.mean_reciprocal_rank == 0.5
    assert report.cases[0].rank == 1
    assert report.cases[1].rank is None
    assert report.cases[0].retrieved[0].page == 1


def test_load_cases_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "q1",
                    "question": "question",
                    "expected_source": "report.pdf",
                    "expected_page": 2,
                }
            ]
        ),
        encoding="utf-8",
    )

    assert load_cases(path)[0].expected_page == 2
