from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


HEADER_PATTERNS = (
    re.compile(r"^\s*page\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*title\s+[qa]\d+\s*$", re.IGNORECASE),
)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_inline(text: str) -> str:
    text = normalize_whitespace(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -:")


def squash_linebreak_hyphenation(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return normalize_whitespace(text)


def strip_common_wrappers(text: str) -> str:
    text = re.sub(r"\bTITLE\s+[QA]\d+\b", "", text, flags=re.IGNORECASE)
    return normalize_whitespace(text)


def remove_repeated_lines(pages: Iterable[str]) -> list[str]:
    line_counter: Counter[str] = Counter()
    split_pages: list[list[str]] = []
    for page in pages:
        lines = [normalize_inline(line) for line in page.splitlines() if normalize_inline(line)]
        split_pages.append(lines)
        for line in set(lines):
            if len(line) >= 3:
                line_counter[line] += 1

    repeated = {
        line
        for line, count in line_counter.items()
        if count >= 3 or any(pattern.match(line) for pattern in HEADER_PATTERNS)
    }
    cleaned_pages: list[str] = []
    for lines in split_pages:
        kept = [line for line in lines if line not in repeated and not any(pattern.match(line) for pattern in HEADER_PATTERNS)]
        cleaned_pages.append("\n".join(kept))
    return cleaned_pages


def chunk_paragraphs(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    return [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]


def normalized_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())
