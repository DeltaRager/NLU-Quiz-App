from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class MCQ:
    id: str
    question: str
    options: list[str]
    correct_option: str
    source: str
    topic: str | None = None
    needs_review: bool = False
    notes: str = ""
    source_pdf: str | None = None
    source_snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCQ":
        return cls(**data)


@dataclass(slots=True)
class TextChunk:
    chunk_id: str
    source_pdf: str
    topic: str
    text: str
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextChunk":
        return cls(**data)

