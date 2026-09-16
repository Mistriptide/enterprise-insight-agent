"""Simple character-window chunking that keeps page-level citations."""

from pathlib import Path

from app.models import DocumentChunk, PageText


def _best_break(text: str, start: int, target_end: int) -> int:
    """Prefer ending at a readable boundary close to the target size."""
    if target_end >= len(text):
        return len(text)
    lower_bound = start + (target_end - start) // 2
    for marker in ("\n\n", "。", "！", "？", ". ", "; ", "；", "，", ", "):
        position = text.rfind(marker, lower_bound, target_end)
        if position != -1:
            return position + len(marker)
    return target_end


def chunk_pages(
    pages: list[PageText], chunk_size: int = 700, overlap: int = 100
) -> list[DocumentChunk]:
    """Split pages into overlapping chunks without crossing page boundaries."""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")

    chunks: list[DocumentChunk] = []
    for page in pages:
        stem = Path(page.source).stem.replace(" ", "-")
        start = 0
        index = 1
        while start < len(page.text):
            end = _best_break(page.text, start, min(start + chunk_size, len(page.text)))
            content = page.text[start:end].strip()
            if content:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{stem}-p{page.page}-c{index}",
                        source=page.source,
                        page=page.page,
                        text=content,
                    )
                )
                index += 1
            if end >= len(page.text):
                break
            next_start = end - overlap
            start = next_start if next_start > start else end
    return chunks
