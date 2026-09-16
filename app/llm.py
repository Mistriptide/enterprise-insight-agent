"""DeepSeek answer generation through its OpenAI-compatible API."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models import SearchResult


SYSTEM_PROMPT = """你是企业知识检索与经营分析助手。
请严格依据提供的 Context 回答，不得把外部知识或猜测当作材料事实。
每个关键事实后都要标注对应引用编号，例如 [1]。
如果 Context 不足以回答，请明确说“根据当前资料无法确定”，并说明缺少什么。
回答使用中文，先给结论，再给依据。"""


def build_context(results: list[SearchResult]) -> str:
    """Format retrieved chunks and their metadata for the model."""
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            f"[{index}] 来源：{result.citation}\n"
            f"检索分数：{result.score:.4f}\n"
            f"内容：{result.chunk.text}"
        )
    return "\n\n".join(blocks)


def answer_question(
    question: str,
    results: list[SearchResult],
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Ask DeepSeek to answer from retrieved evidence only."""
    if not results:
        return "根据当前资料无法确定：没有检索到与问题相关的内容。"

    load_dotenv()
    resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请在 .env 中配置。")

    resolved_model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    client = OpenAI(api_key=resolved_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=resolved_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{build_context(results)}\n\n问题：{question}",
            },
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek 返回了空回答。")
    return content.strip()
