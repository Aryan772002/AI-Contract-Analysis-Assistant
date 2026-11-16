"""PyMuPDF text extraction and page-aware chunking for contract documents."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pymupdf


@dataclass(frozen=True)
class TextChunk:
    """A piece of extracted document text with its source page."""

    chunk_id: int
    page_number: int
    text: str


def extract_pages(source: str | Path | BinaryIO | bytes) -> list[tuple[int, str]]:
    """Extract selectable text with PyMuPDF, returning (page number, text).

    Scanned image-only PDFs need OCR and may produce empty page text; OCR can
    be added as a later project step.
    """
    try:
        if isinstance(source, (str, Path)):
            document = pymupdf.open(str(source))
        else:
            data = source if isinstance(source, bytes) else source.read()
            document = pymupdf.open(stream=data, filetype="pdf")
    except (pymupdf.FileDataError, OSError, ValueError) as exc:
        raise ValueError("This file is not a readable PDF.") from exc

    with document:
        if document.needs_pass:
            raise ValueError("This PDF is password-protected. Upload an unlocked copy.")
        return [
            (page_number, page.get_text("text").strip())
            for page_number, page in enumerate(document, start=1)
        ]


def _split_page(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text near whitespace while retaining a small overlap."""
    text = " ".join(text.split())
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        # Move to a word boundary so chunks do not begin mid-word.
        space = text.find(" ", next_start)
        start = space + 1 if space != -1 else next_start
    return chunks


def chunk_pages(
    pages: list[tuple[int, str]], chunk_size: int = 1000, overlap: int = 150
) -> list[TextChunk]:
    """Chunk extracted pages and preserve page numbers for later citations."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be a positive number")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    for page_number, text in pages:
        for piece in _split_page(text, chunk_size, overlap):
            chunks.append(TextChunk(len(chunks), page_number, piece))
    return chunks


def load_pdf(path: str | Path, chunk_size: int = 1000, overlap: int = 150) -> list[TextChunk]:
    """Read a PDF and return page-aware text chunks."""
    return chunk_pages(extract_pages(path), chunk_size=chunk_size, overlap=overlap)
