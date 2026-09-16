from types import SimpleNamespace

from app.llm import answer_question, build_context
from app.models import DocumentChunk, SearchResult


def test_build_context_contains_citation_and_text() -> None:
    result = SearchResult(
        chunk=DocumentChunk(
            chunk_id="report-p2-c1", source="report.pdf", page=2, text="库存上升。"
        ),
        score=3.25,
    )

    context = build_context([result])

    assert "[1]" in context
    assert "report.pdf · 第 2 页 · report-p2-c1" in context
    assert "库存上升。" in context


def test_answer_question_calls_deepseek_with_context(monkeypatch) -> None:
    result = SearchResult(
        chunk=DocumentChunk(
            chunk_id="report-p2-c1", source="report.pdf", page=2, text="库存上升。"
        ),
        score=3.25,
    )
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="主要风险是库存上升。[1]"))]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("app.llm.OpenAI", FakeOpenAI)

    answer = answer_question("主要风险是什么？", [result], api_key="test-key")

    assert answer == "主要风险是库存上升。[1]"
    assert captured["client"]["base_url"] == "https://api.deepseek.com"
    assert captured["model"] == "deepseek-flash"
    assert "report-p2-c1" in captured["messages"][1]["content"]


def test_answer_question_without_results_does_not_call_api() -> None:
    assert "无法确定" in answer_question("问题", [], api_key="unused")
