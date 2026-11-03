"""Plain text out of an uploaded report file (.txt, .docx, .pdf) for the demo page.

.txt is decoded, .docx is read with the standard library (a zip of XML), .pdf uses pypdf (text layer only:
scanned PDFs have none and are reported as such). Old binary .doc files are not supported.
"""
import io
import re
import zipfile
from pathlib import PurePath
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 30
SUPPORTED = (".txt", ".docx", ".pdf")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ExtractError(ValueError):
    """The file cannot be turned into text; the message is shown to the user."""


def _clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _txt(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError):
        raise ExtractError("That does not look like a .docx file (old .doc files are not supported).")
    paragraphs = []
    for p in ElementTree.fromstring(xml).iter(_W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == _W + "t":
                parts.append(node.text or "")
            elif node.tag == _W + "tab":
                parts.append(" ")
            elif node.tag in (_W + "br", _W + "cr"):
                parts.append("\n")
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


def _pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError:
        raise ExtractError("PDF support needs the pypdf package (pip install pypdf).")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractError("That PDF is password protected.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ExtractError(f"That PDF has more than {MAX_PDF_PAGES} pages. Upload just the report.")
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except PyPdfError:
        raise ExtractError("That PDF could not be read.")


def extract_text(filename: str, data: bytes) -> str:
    """Cleaned text of the file; raises ExtractError with a user-facing message otherwise."""
    suffix = PurePath(filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise ExtractError("Upload a .txt, .docx or .pdf file.")
    if not data:
        raise ExtractError("That file is empty.")
    if len(data) > MAX_BYTES:
        raise ExtractError("That file is larger than 5 MB.")
    text = _clean({".txt": _txt, ".docx": _docx, ".pdf": _pdf}[suffix](data))
    if not text:
        raise ExtractError("No text found in that file" + (" (a scanned PDF has no text layer)." if suffix == ".pdf" else "."))
    return text
