from pathlib import Path

from app.ingestion import load_pdf
from scripts.create_sample_pdf import create_pdf


def test_load_pdf_extracts_text_and_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)

    pages = load_pdf(pdf_path)

    assert len(pages) == 2
    assert pages[0].source == "sample.pdf"
    assert pages[0].page == 1
    assert "Revenue reached RMB 12.8 billion" in pages[0].text
    assert pages[1].page == 2
    assert "Inventory turnover days" in pages[1].text
