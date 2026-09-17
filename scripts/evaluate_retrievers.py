"""Compare keyword and vector retrieval on a labeled question set."""

import argparse
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
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument(
        "--mode", choices=("keyword", "vector", "all"), default="all"
    )
    return parser.parse_args()


def print_report(report: EvaluationReport) -> None:
    print(f"\n{report.retriever_name}")
    print("-" * len(report.retriever_name))
    print(f"Recall@{report.top_k}: {report.recall_at_k:.1%}")
    print(f"MRR: {report.mean_reciprocal_rank:.3f}")
    for result in report.cases:
        status = f"rank={result.rank}" if result.rank else "MISS"
        print(f"  {result.case.case_id}: {status} | {result.case.question}")


def run() -> None:
    args = parse_args()
    pages = load_pdfs(args.pdf)
    chunks = chunk_pages(pages)
    cases = load_cases(args.dataset)

    if args.mode in {"keyword", "all"}:
        report = evaluate(
            KeywordRetriever(chunks),
            cases,
            retriever_name="keyword",
            top_k=args.top_k,
        )
        print_report(report)

    if args.mode in {"vector", "all"}:
        report = evaluate(
            VectorRetriever(chunks, FastEmbedEncoder()),
            cases,
            retriever_name="vector",
            top_k=args.top_k,
        )
        print_report(report)


def main() -> int:
    try:
        run()
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
