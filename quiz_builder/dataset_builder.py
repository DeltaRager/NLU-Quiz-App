from __future__ import annotations

import random
from pathlib import Path

from quiz_builder.io_utils import load_mcqs, save_mcqs
from quiz_builder.models import MCQ
from quiz_builder.text_utils import normalized_key


class DatasetBuildError(RuntimeError):
    """Raised when final dataset validation fails."""


def validate_mcqs(mcqs: list[MCQ]) -> None:
    seen_questions: set[str] = set()
    for mcq in mcqs:
        if len(mcq.options) != 4:
            raise DatasetBuildError(f"{mcq.id}: expected 4 options")
        if mcq.correct_option not in {"A", "B", "C", "D"}:
            raise DatasetBuildError(f"{mcq.id}: invalid correct option")
        key = normalized_key(mcq.question)
        if key in seen_questions:
            raise DatasetBuildError(f"Duplicate question text detected: {mcq.question}")
        seen_questions.add(key)


def assign_stable_ids(mcqs: list[MCQ], prefix: str) -> list[MCQ]:
    assigned: list[MCQ] = []
    for idx, mcq in enumerate(mcqs, start=1):
        assigned.append(
            MCQ(
                id=f"{prefix}-{idx:03d}",
                question=mcq.question,
                options=mcq.options,
                correct_option=mcq.correct_option,
                source=mcq.source,
                topic=mcq.topic,
                needs_review=mcq.needs_review,
                notes=mcq.notes,
                source_pdf=mcq.source_pdf,
                source_snippet=mcq.source_snippet,
            )
        )
    return assigned


def build_combined_dataset(
    originals_path: Path | None,
    generated_path: Path,
    combined_path: Path,
    shuffled_path: Path,
    seed: int = 42,
    expected_originals: int = 0,
    expected_generated: int = 400,
) -> tuple[list[MCQ], list[MCQ]]:
    originals = assign_stable_ids(load_mcqs(originals_path), "orig") if originals_path else []
    generated = assign_stable_ids(load_mcqs(generated_path), "gen")
    if expected_originals >= 0 and len(originals) != expected_originals:
        raise DatasetBuildError(
            f"Expected {expected_originals} reviewed original questions, found {len(originals)}"
        )
    if len(generated) != expected_generated:
        raise DatasetBuildError(
            f"Expected {expected_generated} reviewed generated questions, found {len(generated)}"
        )
    combined = originals + generated
    validate_mcqs(combined)
    save_mcqs(combined_path, combined)
    shuffled = combined[:]
    random.Random(seed).shuffle(shuffled)
    save_mcqs(shuffled_path, shuffled)
    return combined, shuffled
