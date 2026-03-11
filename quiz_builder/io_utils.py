from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from quiz_builder.models import MCQ, TextChunk


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: object) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mcqs(path: Path) -> list[MCQ]:
    raw = read_json(path)
    return [MCQ.from_dict(item) for item in raw]


def save_mcqs(path: Path, mcqs: Iterable[MCQ]) -> None:
    write_json(path, [mcq.to_dict() for mcq in mcqs])


def load_chunks(path: Path) -> list[TextChunk]:
    raw = read_json(path)
    return [TextChunk.from_dict(item) for item in raw]


def save_chunks(path: Path, chunks: Iterable[TextChunk]) -> None:
    write_json(path, [chunk.to_dict() for chunk in chunks])

