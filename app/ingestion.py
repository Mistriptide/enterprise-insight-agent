"""PDF loading and text extraction."""

from pathlib import Path
import re

from pypdf import PdfReader

from app.models import PageText


def _clean_text(text: str) -> str:
    """Remove noisy whitespace while preserving paragraph boundaries."""
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        cleaned = re.sub(r"[ \t]+", " ", block)
        cleaned = re.sub(r"\n+", " ", cleaned).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return "\n\n".join(paragraphs)


def load_pdf(path: str | Path) -> list[PageText]:
    """Extract non-empty pages from one PDF.

    Page numbers are one-based so citations match the number a reader sees.
    Image-only/scanned PDFs need OCR and are intentionally out of scope for v0.1.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在：{pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"仅支持 PDF 文件：{pdf_path}")

    try:
        reader = PdfReader(pdf_path)
    except Exception as exc:
        raise ValueError(f"无法读取 PDF：{pdf_path}") from exc

    pages: list[PageText] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = _clean_text(page.extract_text() or "")
        except Exception as exc:
            raise ValueError(f"提取第 {page_number} 页失败：{pdf_path.name}") from exc
        if text:
            pages.append(PageText(source=pdf_path.name, page=page_number, text=text))
    return pages


def load_pdfs(paths: list[str | Path]) -> list[PageText]:
    """Load multiple PDFs into a single page collection."""
    pages: list[PageText] = []
    for path in paths:
        pages.extend(load_pdf(path))
    if not pages:
        raise ValueError("PDF 中没有可提取文本；扫描版 PDF 需要先进行 OCR。")
    return pages
