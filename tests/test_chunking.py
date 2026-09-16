import pytest

from app.chunking import chunk_pages
from app.models import PageText


def test_chunk_pages_keeps_metadata_and_overlap() -> None:
    pages = [PageText(source="annual report.pdf", page=3, text="A" * 120)]

    chunks = chunk_pages(pages, chunk_size=50, overlap=10)

    assert len(chunks) == 3
    assert chunks[0].chunk_id == "annual-report-p3-c1"
    assert chunks[0].source == "annual report.pdf"
    assert chunks[0].page == 3
    assert chunks[0].text[-10:] == chunks[1].text[:10]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"), [(0, 0), (100, -1), (100, 100), (100, 120)]
)
def test_chunk_pages_rejects_invalid_settings(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size=chunk_size, overlap=overlap)
