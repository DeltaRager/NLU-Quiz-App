from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from quiz_builder.io_utils import load_mcqs
from quiz_builder.models import MCQ, TextChunk
from quiz_builder.text_utils import normalize_inline, normalized_key

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - fallback for pre-install environments
    class BaseModel:  # type: ignore[override]
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(*_args, **_kwargs):  # type: ignore[misc]
        return None


class GeneratedQuestionPayload(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: str
    topic: str
    source_snippet: str


class GeneratedBatchPayload(BaseModel):
    questions: list[GeneratedQuestionPayload]


@dataclass(slots=True)
class OpenAIGenerationConfig:
    model: str = "gpt-4o-mini"
    batch_size: int = 20
    max_rounds: int = 30
    temperature: float = 0.7
    examples_limit: int = 8
    sleep_seconds: float = 0.0
    progress_callback: callable | None = None


def build_generated_mcqs_with_openai(
    chunks: list[TextChunk],
    target_count: int,
    existing_questions: list[MCQ] | None = None,
    original_examples_path: Path | None = None,
    config: OpenAIGenerationConfig | None = None,
) -> list[MCQ]:
    config = config or OpenAIGenerationConfig()
    client = build_openai_client()
    existing_questions = existing_questions or []
    examples = load_example_questions(original_examples_path, config.examples_limit)
    existing_question_keys = {normalized_key(item.question) for item in existing_questions}
    generated: list[MCQ] = []
    seen_keys: set[str] = set(existing_question_keys)
    round_index = 0
    chunk_cursor = 0

    while len(generated) < target_count and round_index < config.max_rounds:
        round_index += 1
        chunk_batch = select_chunk_batch(chunks, chunk_cursor, width=4)
        chunk_cursor = (chunk_cursor + 4) % max(len(chunks), 1)
        if config.progress_callback:
            config.progress_callback("request_started", len(generated), target_count, round_index, config.max_rounds)
        prompt = build_generation_prompt(
            chunk_batch=chunk_batch,
            target_count=min(config.batch_size, target_count - len(generated)),
            original_examples=examples,
            existing_questions=generated,
        )
        response = client.responses.parse(
            model=config.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You generate high-quality NLU multiple-choice quiz questions. "
                        "Return only structured data. Keep the style concise and exam-like."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            text_format=GeneratedBatchPayload,
        )
        batch = response.output_parsed
        batch_added = 0
        for item in batch.questions:
            mcq = payload_to_mcq(item)
            if not is_valid_generated_mcq(mcq):
                continue
            key = normalized_key(mcq.question)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            mcq.id = f"gen-draft-{len(generated) + 1:03d}"
            generated.append(mcq)
            batch_added += 1
            if len(generated) >= target_count:
                break
        if config.progress_callback:
            config.progress_callback("request_finished", len(generated), target_count, round_index, config.max_rounds, batch_added)
        if config.sleep_seconds > 0:
            time.sleep(config.sleep_seconds)
    return generated


def build_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The `openai` package is not installed. Install requirements.txt.") from exc
    return OpenAI(api_key=api_key)


def load_example_questions(path: Path | None, limit: int) -> list[MCQ]:
    if not path or not path.exists():
        return []
    return load_mcqs(path)[:limit]


def select_chunk_batch(chunks: list[TextChunk], start: int, width: int) -> list[TextChunk]:
    if not chunks:
        return []
    batch: list[TextChunk] = []
    for offset in range(width):
        batch.append(chunks[(start + offset) % len(chunks)])
    return batch


def build_generation_prompt(
    chunk_batch: Iterable[TextChunk],
    target_count: int,
    original_examples: list[MCQ],
    existing_questions: list[MCQ],
) -> str:
    examples_block = "\n\n".join(
        [
            (
                f"Example {idx}\n"
                f"Question: {item.question}\n"
                f"A. {item.options[0]}\n"
                f"B. {item.options[1]}\n"
                f"C. {item.options[2]}\n"
                f"D. {item.options[3]}\n"
                f"Correct: {item.correct_option}"
            )
            for idx, item in enumerate(original_examples, start=1)
        ]
    )
    recent_questions = "\n".join(f"- {item.question}" for item in existing_questions[-30:])
    chunks_block = "\n\n".join(
        [
            (
                f"Source topic: {chunk.topic}\n"
                f"Source PDF: {chunk.source_pdf}\n"
                f"Keywords: {', '.join(chunk.keywords)}\n"
                f"Source text:\n{clean_source_text(chunk.text)}"
            )
            for chunk in chunk_batch
        ]
    )
    return (
        f"Generate {target_count} multiple-choice questions grounded only in the provided source text.\n\n"
        "Requirements:\n"
        "- Match the style and difficulty of the example quiz questions.\n"
        "- One question, four options, exactly one correct answer.\n"
        "- Do not mention tutorials, lectures, slides, source material, or 'according to the material'.\n"
        "- Ask about the topic itself, not about document structure.\n"
        "- Avoid OCR artifacts and malformed text.\n"
        "- Keep wording concise and exam-like.\n"
        "- Make distractors plausible but clearly incorrect.\n"
        "- Prefer NLU/NLP concepts from first-half material.\n"
        "- Include a short source snippet copied from the source text that justifies the answer.\n\n"
        "Avoid duplicates or near-duplicates of these existing generated questions:\n"
        f"{recent_questions or '- none yet'}\n\n"
        "Style examples from the quiz PDF:\n"
        f"{examples_block or 'No examples provided.'}\n\n"
        "Use these source chunks:\n"
        f"{chunks_block}\n"
    )


def clean_source_text(text: str) -> str:
    lines = [normalize_inline(line) for line in text.splitlines()]
    lines = [line for line in lines if line and not looks_like_noise(line)]
    joined = " ".join(lines)
    joined = normalize_inline(joined)
    words = joined.split()
    return " ".join(words[:260])


def looks_like_noise(line: str) -> bool:
    if len(line) < 4:
        return True
    alpha_ratio = sum(ch.isalpha() for ch in line) / max(len(line), 1)
    return alpha_ratio < 0.45


def payload_to_mcq(item: GeneratedQuestionPayload) -> MCQ:
    normalized_options = [normalize_inline(option) for option in item.options]
    return MCQ(
        id="",
        question=normalize_inline(item.question),
        options=normalized_options,
        correct_option=item.correct_option.strip().upper(),
        source="generated",
        topic=normalize_inline(item.topic),
        needs_review=False,
        notes="",
        source_pdf=None,
        source_snippet=normalize_inline(item.source_snippet),
    )


def is_valid_generated_mcq(mcq: MCQ) -> bool:
    if mcq.correct_option not in {"A", "B", "C", "D"}:
        return False
    if len(mcq.options) != 4:
        return False
    if any(not option for option in mcq.options):
        return False
    if len({normalized_key(option) for option in mcq.options}) != 4:
        return False
    lowered = mcq.question.lower()
    banned = [
        "tutorial",
        "lecture",
        "source material",
        "course material",
        "following material",
        "according to the material",
    ]
    if any(token in lowered for token in banned):
        return False
    return True
