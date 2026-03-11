from __future__ import annotations

import os

from quiz_builder.models import MCQ
from quiz_builder.openai_generator import build_openai_client


def explain_mcq(mcq: MCQ, user_choice: str | None = None, model: str | None = None) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = build_openai_client()
    correct_index = ["A", "B", "C", "D"].index(mcq.correct_option)
    correct_text = mcq.options[correct_index]
    option_lines = "\n".join(
        f"{label}. {text}" for label, text in zip(["A", "B", "C", "D"], mcq.options)
    )
    source_hint = mcq.source_pdf or mcq.topic or "unknown source"
    user_line = f"Student selected: {user_choice}" if user_choice else "Student selected: none"
    original_explanation = mcq.explanation or "No built-in explanation was provided."

    response = client.responses.create(
        model=model or os.getenv("OPENAI_EXPLAIN_MODEL", "gpt-4o-mini"),
        input=[
            {
                "role": "system",
                "content": (
                    "You explain quiz answers clearly and briefly. "
                    "Summarize the built-in explanation into a short study note. "
                    "Use the student's selected option to point out the misunderstanding if they were wrong. "
                    "Keep it under 150 words, ideally around 100 words. "
                    "Do not restate every option unless needed."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {mcq.question}\n"
                    f"Options:\n{option_lines}\n"
                    f"Correct answer: {mcq.correct_option}. {correct_text}\n"
                    f"{user_line}\n"
                    f"Topic/source: {source_hint}\n"
                    f"Given explanation: {original_explanation}\n"
                    f"Grounding snippet: {mcq.source_snippet or 'Not available'}"
                ),
            },
        ],
    )
    return response.output_text.strip()
