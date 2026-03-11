from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path


class OCRDependencyError(RuntimeError):
    """Raised when OCR prerequisites are missing."""


def check_runtime_prerequisites() -> None:
    try:
        import fitz  # noqa: F401
    except ImportError as exc:
        raise OCRDependencyError("PyMuPDF is required. Install dependencies from requirements.txt.") from exc

    try:
        import pytesseract  # noqa: F401
    except ImportError as exc:
        raise OCRDependencyError("pytesseract is required. Install dependencies from requirements.txt.") from exc

    if shutil.which("tesseract") is None:
        raise OCRDependencyError("The `tesseract` executable is not installed or not on PATH.")


def extract_pdf_pages(pdf_path: Path, dpi: int = 200, lang: str = "eng") -> list[str]:
    check_runtime_prerequisites()
    import fitz
    import pytesseract

    document = fitz.open(pdf_path)
    pages: list[str] = []
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image_bytes = pixmap.tobytes("png")
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=lang)
        pages.append(text)
    return pages


def extract_pdf_text_pages(pdf_path: Path) -> list[str]:
    try:
        import fitz
    except ImportError as exc:
        raise OCRDependencyError("PyMuPDF is required. Install dependencies from requirements.txt.") from exc

    document = fitz.open(pdf_path)
    return [page.get_text("text") for page in document]


def extract_pdf_pages_preferring_text(pdf_path: Path, dpi: int = 200, lang: str = "eng") -> list[str]:
    text_pages = extract_pdf_text_pages(pdf_path)
    usable_pages = [page for page in text_pages if len(page.strip()) >= 40]
    if len(usable_pages) >= max(1, len(text_pages) // 2):
        return text_pages
    return extract_pdf_pages(pdf_path, dpi=dpi, lang=lang)


def detect_tesseract_version() -> str | None:
    if shutil.which("tesseract") is None:
        return None
    completed = subprocess.run(
        ["tesseract", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.splitlines()[0].strip()
