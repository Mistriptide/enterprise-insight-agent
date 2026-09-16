"""Command-line interface for Enterprise Insight Agent."""

import argparse
from pathlib import Path
import sys

from app.pipeline import RAGPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="对一个或多个企业 PDF 进行可追溯问答。"
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        action="append",
        required=True,
        help="PDF 路径；可重复传入多次。",
    )
    parser.add_argument("--question", "-q", help="问题；不传则进入交互模式。")
    parser.add_argument("--top-k", type=int, default=4, help="送入模型的相关文本块数量。")
    parser.add_argument("--chunk-size", type=int, default=700, help="每个文本块的目标字符数。")
    parser.add_argument("--overlap", type=int, default=100, help="相邻文本块重叠字符数。")
    parser.add_argument(
        "--show-context", action="store_true", help="显示召回的原文，便于调试与演示。"
    )
    return parser.parse_args()


def print_answer(pipeline: RAGPipeline, question: str, top_k: int, show_context: bool) -> None:
    answer, results = pipeline.answer(question, top_k=top_k)
    print("\n回答\n----")
    print(answer)
    print("\n引用来源\n--------")
    if not results:
        print("未检索到相关内容")
        return
    for index, result in enumerate(results, start=1):
        print(f"[{index}] {result.citation}（score={result.score:.4f}）")
        if show_context:
            preview = result.chunk.text.replace("\n", " ")
            print(f"    {preview}")


def main() -> int:
    args = parse_args()
    try:
        pipeline = RAGPipeline(
            args.pdf, chunk_size=args.chunk_size, overlap=args.overlap
        )
        print(f"已加载 {len(args.pdf)} 个 PDF，生成 {len(pipeline.chunks)} 个文本块。")

        if args.question:
            print_answer(pipeline, args.question, args.top_k, args.show_context)
            return 0

        print("进入交互模式；输入 exit 或 quit 结束。")
        while True:
            question = input("\n你的问题> ").strip()
            if question.lower() in {"exit", "quit"}:
                return 0
            if question:
                print_answer(pipeline, question, args.top_k, args.show_context)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已退出。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
