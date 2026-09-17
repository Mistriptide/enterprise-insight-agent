"""Compare keyword and vector retrieval on a labeled question set."""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
import sys

from app.chunking import chunk_pages
from app.evaluation import EvaluationReport, evaluate, load_cases
from app.ingestion import load_pdfs
from app.retrieval import KeywordRetriever
from app.vector_retrieval import FastEmbedEncoder, VectorRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="比较两种检索器的 Recall@K 与 MRR。")
    parser.add_argument("--pdf", type=Path, action="append", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cutoffs", type=int, nargs="+", default=[1, 3])
    parser.add_argument(
        "--mode", choices=("keyword", "vector", "all"), default="all"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/retrieval_evaluation.json"),
        help="JSON 结果文件；同时生成同名 Markdown 报告。",
    )
    parser.add_argument(
        "--notes",
        type=Path,
        default=Path("eval/analysis_notes.json"),
        help="逐题退化归因说明。",
    )
    return parser.parse_args()


def print_report(report: EvaluationReport, cutoffs: list[int]) -> None:
    print(f"\n{report.retriever_name}")
    print("-" * len(report.retriever_name))
    for cutoff in cutoffs:
        print(f"Recall@{cutoff}: {report.recall_at(cutoff):.1%}")
    print(f"MRR: {report.mean_reciprocal_rank:.3f}")
    for result in report.cases:
        status = f"rank={result.rank}" if result.rank else "MISS"
        print(f"  {result.case.case_id}: {status} | {result.case.question}")


def _rank_value(rank: int | None) -> float:
    return float("inf") if rank is None else rank


def _comparison(keyword_rank: int | None, vector_rank: int | None) -> str:
    if _rank_value(vector_rank) < _rank_value(keyword_rank):
        return "vector_improved"
    if _rank_value(vector_rank) > _rank_value(keyword_rank):
        return "vector_degraded"
    return "same"


def _report_dict(
    reports: dict[str, EvaluationReport],
    cutoffs: list[int],
    args: argparse.Namespace,
    notes: dict,
    chunk_count: int,
) -> dict:
    metrics = {
        name: {
            **{f"recall_at_{cutoff}": report.recall_at(cutoff) for cutoff in cutoffs},
            "mrr": report.mean_reciprocal_rank,
        }
        for name, report in reports.items()
    }
    cases = []
    if "keyword" in reports and "vector" in reports:
        for keyword_case, vector_case in zip(
            reports["keyword"].cases, reports["vector"].cases, strict=True
        ):
            comparison = _comparison(keyword_case.rank, vector_case.rank)
            cases.append(
                {
                    "id": keyword_case.case.case_id,
                    "question": keyword_case.case.question,
                    "expected_source": keyword_case.case.expected_source,
                    "expected_page": keyword_case.case.expected_page,
                    "keyword": {
                        "rank": keyword_case.rank,
                        "retrieved": [asdict(item) for item in keyword_case.retrieved],
                    },
                    "vector": {
                        "rank": vector_case.rank,
                        "retrieved": [asdict(item) for item in vector_case.retrieved],
                    },
                    "comparison": comparison,
                    "diagnosis": notes.get(keyword_case.case.case_id, {}),
                }
            )

    return {
        "experiment": {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "pdfs": [str(path) for path in args.pdf],
            "dataset": str(args.dataset),
            "cutoffs": cutoffs,
            "chunk_size": 700,
            "overlap": 100,
            "chunk_count": chunk_count,
            "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "fastembed_version": version("fastembed"),
        },
        "metrics": metrics,
        "cases": cases,
    }


def _markdown(data: dict) -> str:
    metrics = data["metrics"]
    cutoffs = data["experiment"]["cutoffs"]
    lines = [
        "# Retrieval Evaluation 实验结果",
        "",
        "## 核心指标",
        "",
        "| Retriever | "
        + " | ".join(f"Recall@{cutoff}" for cutoff in cutoffs)
        + " | MRR |",
        "|---|" + "---:|" * (len(cutoffs) + 1),
    ]
    for name in ("keyword", "vector"):
        if name in metrics:
            item = metrics[name]
            lines.append(
                f"| {name} | "
                + " | ".join(
                    f"{item[f'recall_at_{cutoff}']:.1%}" for cutoff in cutoffs
                )
                + f" | {item['mrr']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## 逐题排名对比",
            "",
            "| ID | Keyword 排名 | Vector 排名 | 对比 | 归因 |",
            "|---|---:|---:|---|---|",
        ]
    )
    labels = {
        "vector_improved": "Vector 改善",
        "vector_degraded": "Vector 退化",
        "same": "持平",
    }
    for case in data["cases"]:
        keyword_rank = case["keyword"]["rank"] or "MISS"
        vector_rank = case["vector"]["rank"] or "MISS"
        diagnosis = case["diagnosis"].get("category", "-")
        lines.append(
            f"| {case['id']} | {keyword_rank} | {vector_rank} | "
            f"{labels[case['comparison']]} | {diagnosis} |"
        )

    lines.extend(["", "## 逐题归因", ""])
    for case in data["cases"]:
        diagnosis = case["diagnosis"]
        if diagnosis:
            lines.append(
                f"- **{case['id']} — {diagnosis['category']}：** {diagnosis['analysis']}"
            )

    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "- 固定测试集只有 6 道问题和 2 个候选 Chunk。",
            "- Recall@3 在这里接近全语料检查，区分度有限。",
            "- 示例 PDF 为英文且远短于真实中文年报。",
            "- 结果证明了评测流程和当前方法差异，不代表生产级模型质量。",
            "",
        ]
    )
    return "\n".join(lines)


def run() -> None:
    args = parse_args()
    cutoffs = sorted(set(args.cutoffs))
    if not cutoffs or cutoffs[0] <= 0:
        raise ValueError("cutoffs 必须是正整数")
    top_k = max(cutoffs)
    pages = load_pdfs(args.pdf)
    chunks = chunk_pages(pages)
    cases = load_cases(args.dataset)
    reports: dict[str, EvaluationReport] = {}

    if args.mode in {"keyword", "all"}:
        reports["keyword"] = evaluate(
            KeywordRetriever(chunks),
            cases,
            retriever_name="keyword",
            top_k=top_k,
        )
        print_report(reports["keyword"], cutoffs)

    if args.mode in {"vector", "all"}:
        reports["vector"] = evaluate(
            VectorRetriever(chunks, FastEmbedEncoder()),
            cases,
            retriever_name="vector",
            top_k=top_k,
        )
        print_report(reports["vector"], cutoffs)

    notes = json.loads(args.notes.read_text(encoding="utf-8")) if args.notes.exists() else {}
    data = _report_dict(reports, cutoffs, args, notes, len(chunks))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path = args.output.with_suffix(".md")
    markdown_path.write_text(_markdown(data), encoding="utf-8")
    print(f"\n结果已保存：{args.output}")
    print(f"报告已保存：{markdown_path}")


def main() -> int:
    try:
        run()
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
