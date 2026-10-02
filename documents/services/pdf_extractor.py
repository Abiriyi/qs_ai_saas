# documents/services/pdf_extractor.py

import logging
from io import BytesIO
from os import PathLike
from pathlib import Path

import fitz
import pdfplumber

logger = logging.getLogger(__name__)


class PDFExtractorService:

    @staticmethod
    def _coerce_pdf_bytes(source):
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)

        if isinstance(source, (str, PathLike)):
            source = Path(source)
            if not source.exists():
                raise ValueError(f"PDF file does not exist: {source}")
            return source.read_bytes()

        if hasattr(source, "read"):
            pos = None
            try:
                pos = source.tell()
            except (AttributeError, OSError):
                pos = None

            if pos is not None:
                source.seek(0)
            return source.read()

        if hasattr(source, "file") and hasattr(source.file, "read"):
            return PDFExtractorService._coerce_pdf_bytes(source.file)

        raise TypeError(
            "PDFExtractorService.extract_text() expects a PDF path, bytes, or file-like object."
        )

    @staticmethod
    def _extract_with_fitz(pdf_bytes):
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            return "\n".join(page.get_text() or "" for page in pdf)
        finally:
            pdf.close()

    @staticmethod
    def _extract_with_pdfplumber(pdf_bytes):
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    @staticmethod
    def extract_text(file_field):
        pdf_bytes = PDFExtractorService._coerce_pdf_bytes(file_field)

        if not pdf_bytes:
            raise ValueError("The uploaded PDF is empty.")

        last_error = None
        for extractor_name, extractor in (
            ("PyMuPDF", PDFExtractorService._extract_with_fitz),
            ("pdfplumber", PDFExtractorService._extract_with_pdfplumber),
        ):
            try:
                text = extractor(pdf_bytes)
                cleaned = (text or "").strip()
                if cleaned:
                    return cleaned
            except Exception as exc:  # pragma: no cover - defensive fallback branch
                last_error = exc
                logger.warning(
                    "PDF extraction via %s failed: %s",
                    extractor_name,
                    exc,
                    exc_info=True,
                )

        raise ValueError(
            "Could not extract readable text from the PDF."
            if last_error is None
            else f"Could not extract readable text from the PDF: {last_error}"
        )