from __future__ import annotations

import re
from pathlib import Path

from quiz_builder.models import TextChunk
from quiz_builder.text_utils import chunk_paragraphs, normalize_inline, normalize_whitespace, remove_repeated_lines


HEADER_RE = re.compile(r"^(?:[A-Z][A-Za-z0-9/&(), -]{4,}|Tutorial\s+\d+|Invited Lecture\s+#?\d+)$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")
STOPWORDS = {
    "this",
    "that",
    "from",
    "with",
    "have",
    "will",
    "your",
    "about",
    "which",
    "their",
    "there",
    "into",
    "also",
    "than",
    "what",
    "when",
}


def chunk_document_pages(pdf_name: str, pages: list[str]) -> list[TextChunk]:
    cleaned_pages = remove_repeated_lines(pages)
    text = "\n\n".join(page for page in cleaned_pages if page.strip())
    paragraphs = chunk_paragraphs(text)
    chunks: list[TextChunk] = []
    topic = Path(pdf_name).stem
    current_parts: list[str] = []

    def flush_chunk(chunk_index: int) -> None:
        if not current_parts:
            return
        merged = normalize_whitespace("\n\n".join(current_parts))
        keywords = top_keywords(merged)
        chunks.append(
            TextChunk(
                chunk_id=f"{Path(pdf_name).stem.lower().replace(' ', '-')}-{chunk_index:03d}",
                source_pdf=pdf_name,
                topic=topic,
                text=merged,
                keywords=keywords,
            )
        )

    chunk_index = 1
    for paragraph in paragraphs:
        line = normalize_inline(paragraph)
        if HEADER_RE.match(line) and current_parts:
            flush_chunk(chunk_index)
            chunk_index += 1
            current_parts = []
            topic = line
            continue
        current_parts.append(paragraph)
        if len(normalize_inline("\n\n".join(current_parts))) > 1200:
            flush_chunk(chunk_index)
            chunk_index += 1
            current_parts = []
    flush_chunk(chunk_index)
    return chunks


def top_keywords(text: str, limit: int = 8) -> list[str]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    counts: dict[str, int] = {}
    for word in words:
        if word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]

