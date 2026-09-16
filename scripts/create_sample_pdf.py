"""Create a tiny text PDF for a zero-download end-to-end demo.

The script uses only Python's standard library. It writes a minimal PDF with a
built-in Helvetica font so pypdf can extract the English text reliably.
"""

from pathlib import Path


PAGES = [
    [
        "Northstar Beverage Group - 2025 Operating Brief",
        "Revenue reached RMB 12.8 billion in 2025, up 12 percent year on year.",
        "Premium products contributed 58 percent of total revenue.",
        "The company expanded its direct-to-consumer channel in East China.",
    ],
    [
        "Risk and Outlook",
        "Inventory turnover days increased from 46 days to 53 days.",
        "Management identified channel inventory and raw material prices as key risks.",
        "The 2026 priority is improving distributor inventory visibility.",
    ],
]


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_pdf(output: Path) -> None:
    objects: list[bytes] = []
    page_ids = [4, 6]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_index, lines in enumerate(PAGES):
        page_id = page_ids[page_index]
        content_id = page_id + 1
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        commands = ["BT", "/F1 12 Tf", "72 730 Td"]
        for index, line in enumerate(lines):
            if index:
                commands.append("0 -24 Td")
            commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode()
        content = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        objects.extend([page, content])

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode())
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf)


if __name__ == "__main__":
    target = Path("data/sample_company_report.pdf")
    create_pdf(target)
    print(f"已生成：{target}")
