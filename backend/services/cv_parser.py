from __future__ import annotations

import io
import re
from typing import Optional

import pdfplumber
from docx import Document

MAX_CHARS = 8000
MIN_VALID_CHARS = 100


def parse_cv(file_bytes: bytes, file_name: str) -> str:
    """Parse a CV file into plain text.

    Returns the extracted text truncated to MAX_CHARS with collapsed whitespace.
    Returns an empty string for scanned/empty PDFs so callers can mark the
    candidate as errored without crashing the batch.
    """
    lower = file_name.lower()

    if lower.endswith(".pdf"):
        text = _parse_pdf(file_bytes)
        if len(text.strip()) < MIN_VALID_CHARS:
            return ""
    elif lower.endswith(".docx"):
        text = _parse_docx(file_bytes)
    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {file_name}")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS]


def parse_jd(file_bytes: bytes, file_name: str) -> str:
    """Parse a JD upload. Restricted to .docx and .txt (no PDF for JDs)."""
    lower = file_name.lower()
    if lower.endswith(".docx"):
        text = _parse_docx(file_bytes)
    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="replace")
    elif lower.endswith(".doc"):
        raise ValueError(
            "Legacy .doc files are not supported. Please save the JD as .docx and re-upload."
        )
    else:
        raise ValueError(
            f"Unsupported JD file type: {file_name}. Accepted formats: .docx, .txt"
        )
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS]


def _parse_pdf(file_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
    return "\n\n".join(pages)


def _parse_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


_NAME_RE = re.compile(r"^([A-Z][a-zA-Z'\-]+)(\s+[A-Z][a-zA-Z'\-]+){1,3}$")


def extract_candidate_name(cv_text: str) -> Optional[str]:
    """Best-effort name extraction from the top of a CV.

    Looks at the first 400 chars and returns the first non-empty line that
    looks like a name: 2-4 capitalised words, no digits, no '@'.
    """
    head = cv_text[:400]
    for raw_line in head.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if _NAME_RE.match(line):
            return line
    return None
