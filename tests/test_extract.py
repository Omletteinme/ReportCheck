import io
import zipfile

import pytest

from demo.extract import MAX_BYTES, ExtractError, extract_text

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>' for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def make_pdf(text: str) -> bytes:
    """Smallest valid one-page PDF with a text layer (Helvetica)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)


def test_txt_decodes_utf8_with_bom_and_falls_back_to_cp1252():
    assert extract_text("r.txt", "﻿FINDINGS: clear.".encode("utf-8")) == "FINDINGS: clear."
    assert extract_text("r.TXT", "café – ok".encode("cp1252")) == "café – ok"


def test_whitespace_is_cleaned():
    assert extract_text("r.txt", b"A   line.\r\n\r\n\r\n\r\nNext\tline. \n") == "A line.\n\nNext line."


def test_docx_paragraphs_become_lines():
    text = extract_text("report.docx", make_docx(["FINDINGS: The lungs are clear.", "IMPRESSION: Normal."]))
    assert text == "FINDINGS: The lungs are clear.\nIMPRESSION: Normal."


def test_pdf_text_layer_is_extracted():
    pytest.importorskip("pypdf")
    assert "No pneumothorax" in extract_text("report.pdf", make_pdf("No pneumothorax. Heart size is normal."))


@pytest.mark.parametrize("name,data,message", [
    ("report.doc", b"x", "Upload a .txt"),
    ("report", b"x", "Upload a .txt"),
    ("report.txt", b"", "empty"),
    ("report.txt", b"  \n ", "No text found"),
    ("report.docx", b"not a zip", "does not look like a .docx"),
])
def test_bad_files_give_a_user_facing_message(name, data, message):
    with pytest.raises(ExtractError, match=message):
        extract_text(name, data)


def test_corrupt_pdf_is_reported_not_raised_as_a_crash():
    pytest.importorskip("pypdf")
    with pytest.raises(ExtractError):
        extract_text("report.pdf", b"%PDF-1.4 this is not really a pdf")


def test_pdf_without_text_is_reported_as_scanned():
    pytest.importorskip("pypdf")
    with pytest.raises(ExtractError, match="scanned"):
        extract_text("scan.pdf", make_pdf(""))


def test_oversized_file_is_refused():
    with pytest.raises(ExtractError, match="5 MB"):
        extract_text("report.txt", b"a" * (MAX_BYTES + 1))
