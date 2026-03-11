from __future__ import annotations

import re
from dataclasses import dataclass

from quiz_builder.models import MCQ
from quiz_builder.text_utils import normalize_inline, remove_repeated_lines, strip_common_wrappers


QUESTION_START_RE = re.compile(r"^(?:q(?:uestion)?\s*)?(\d{1,3})[\).:\-]\s*(.+)$", re.IGNORECASE)
OPTION_RE = re.compile(r"^\s*([A-D])[\).:\-]\s*(.+)$", re.IGNORECASE)
ANSWER_LINE_RE = re.compile(
    r"^(?:answer\s*(?:key)?\s*)?(?:q(?:uestion)?\s*)?(\d{1,3})[\s:.-]*(?:ans(?:wer)?\s*[:.-]?\s*)?([A-D])\b",
    re.IGNORECASE,
)
QUESTION_SENTINEL_RE = re.compile(r"^(?:q(?:uestion)?\s*)?\d{1,3}[\).:\-]", re.IGNORECASE)
QUESTION_PAGE_RE = re.compile(r"^Q\s*(\d{1,3})$", re.IGNORECASE)
ANSWER_PAGE_RE = re.compile(r"^A\s*(\d{1,3})$", re.IGNORECASE)


@dataclass(slots=True)
class ParsedQuestion:
    number: int
    question: str
    options: dict[str, str]
    notes: list[str]


def _clean_page_lines(page: str) -> list[str]:
    return [strip_common_wrappers(line).strip() for line in page.splitlines() if strip_common_wrappers(line).strip()]


def _parse_question_page(number: int, page: str) -> ParsedQuestion:
    lines = _clean_page_lines(page)
    notes: list[str] = []
    body = lines[1:] if lines and QUESTION_PAGE_RE.match(lines[0]) else lines
    question_parts: list[str] = []
    options: dict[str, str] = {}
    idx = 0
    while idx < len(body):
        line = body[idx]
        opt_match = OPTION_RE.match(line)
        if opt_match:
            option_text, idx = _join_option_lines(body, idx)
            options[opt_match.group(1).upper()] = option_text
            continue
        if not options:
            question_parts.append(line.lstrip("! ").strip())
        idx += 1
    if len(options) != 4:
        notes.append(f"expected 4 options, found {len(options)}")
    return ParsedQuestion(
        number=number,
        question=normalize_inline(" ".join(question_parts)),
        options=options,
        notes=notes,
    )


def _extract_correct_option_from_answer_page(number: int, answer_page: str, parsed: ParsedQuestion) -> tuple[str, str | None, list[str]]:
    lines = _clean_page_lines(answer_page)
    notes: list[str] = []
    body = lines[1:] if lines and ANSWER_PAGE_RE.match(lines[0]) else lines
    answer_text = ""
    correct_option = ""
    explanation_lines: list[str] = []
    explanation_started = False
    idx = 0
    while idx < len(body):
        line = body[idx]
        if line.lower().startswith("explanation"):
            explanation_started = True
            idx += 1
            continue
        if explanation_started:
            explanation_lines.append(line.lstrip("! ").strip())
            idx += 1
            continue
        opt_match = OPTION_RE.match(line)
        if opt_match:
            answer_text, idx = _join_answer_option_lines(body, idx)
            if parsed.options.get(opt_match.group(1).upper()) == answer_text:
                correct_option = opt_match.group(1).upper()
                continue
            break
        idx += 1
    if answer_text:
        if correct_option:
            return correct_option, _normalize_explanation(explanation_lines), notes
        for label, option_text in parsed.options.items():
            if normalize_inline(option_text) == answer_text:
                return label, _normalize_explanation(explanation_lines), notes
        notes.append(f"answer text did not match options for Q{number}")
    else:
        notes.append(f"missing answer option on A{number}")
    return "", _normalize_explanation(explanation_lines), notes


def parse_quiz_pages(pages: list[str]) -> tuple[list[MCQ], dict[str, int]]:
    page_map = {idx + 1: page for idx, page in enumerate(pages)}
    parsed_pages: dict[int, ParsedQuestion] = {}
    answers: dict[int, str] = {}
    explanations: dict[int, str | None] = {}
    review_count = 0

    for page in pages:
        lines = _clean_page_lines(page)
        if not lines:
            continue
        q_match = QUESTION_PAGE_RE.match(lines[0])
        if q_match:
            number = int(q_match.group(1))
            parsed_pages[number] = _parse_question_page(number, page)

    for page in pages:
        lines = _clean_page_lines(page)
        if not lines:
            continue
        a_match = ANSWER_PAGE_RE.match(lines[0])
        if a_match:
            number = int(a_match.group(1))
            parsed = parsed_pages.get(number)
            if not parsed:
                continue
            correct_option, explanation, notes = _extract_correct_option_from_answer_page(number, page, parsed)
            parsed.notes.extend(notes)
            answers[number] = correct_option
            explanations[number] = explanation

    mcqs: list[MCQ] = []
    for number in sorted(parsed_pages):
        parsed = parsed_pages[number]
        correct_option = answers.get(number, "")
        if not correct_option:
            parsed.notes.append("missing answer key entry")
        needs_review = bool(parsed.notes) or sorted(parsed.options) != ["A", "B", "C", "D"]
        if needs_review:
            review_count += 1
        mcqs.append(
            MCQ(
                id=f"orig-draft-{number:03d}",
                question=parsed.question,
                options=[parsed.options.get(label, "") for label in ["A", "B", "C", "D"]],
                correct_option=correct_option,
                source="original",
                explanation=explanations.get(number),
                topic=None,
                needs_review=needs_review,
                notes="; ".join(dict.fromkeys(parsed.notes)),
            )
        )
    return mcqs, {
        "questions_found": len(mcqs),
        "answers_found": len([value for value in answers.values() if value]),
        "needs_review": review_count,
    }


def _join_option_lines(lines: list[str], start_idx: int) -> tuple[str, int]:
    label, text = OPTION_RE.match(lines[start_idx]).groups()  # type: ignore[union-attr]
    collected = [text.strip()]
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if OPTION_RE.match(line) or QUESTION_SENTINEL_RE.match(line) or ANSWER_LINE_RE.match(line):
            break
        collected.append(line)
        idx += 1
    return normalize_inline(" ".join(collected)), idx


def _join_answer_option_lines(lines: list[str], start_idx: int) -> tuple[str, int]:
    _label, text = OPTION_RE.match(lines[start_idx]).groups()  # type: ignore[union-attr]
    collected = [text.strip()]
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if (
            OPTION_RE.match(line)
            or QUESTION_SENTINEL_RE.match(line)
            or ANSWER_LINE_RE.match(line)
            or line.lower().startswith("explanation")
        ):
            break
        collected.append(line)
        idx += 1
    return normalize_inline(" ".join(collected)), idx


def _normalize_explanation(lines: list[str]) -> str | None:
    text = normalize_inline(" ".join(line for line in lines if line.strip()))
    return text or None


def parse_answer_key(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for raw_line in text.splitlines():
        line = normalize_inline(raw_line)
        if not line:
            continue
        match = ANSWER_LINE_RE.match(line)
        if match:
            answers[int(match.group(1))] = match.group(2).upper()
    return answers


def parse_quiz_text(pages: list[str]) -> tuple[list[MCQ], dict[str, int]]:
    if any(QUESTION_PAGE_RE.match(line.strip()) for page in pages for line in page.splitlines()):
        return parse_quiz_pages(pages)

    cleaned_pages = remove_repeated_lines(pages)
    full_text = "\n\n".join(page for page in cleaned_pages if page.strip())
    lines = [strip_common_wrappers(line) for line in full_text.splitlines()]
    lines = [line for line in lines if line.strip()]
    answers = parse_answer_key(full_text)

    questions: list[ParsedQuestion] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        q_match = QUESTION_START_RE.match(line)
        if not q_match:
            idx += 1
            continue
        number = int(q_match.group(1))
        question_parts = [q_match.group(2).strip()]
        idx += 1
        while idx < len(lines):
            next_line = lines[idx].strip()
            if not next_line:
                idx += 1
                continue
            if OPTION_RE.match(next_line) or QUESTION_SENTINEL_RE.match(next_line):
                break
            question_parts.append(next_line)
            idx += 1

        options: dict[str, str] = {}
        notes: list[str] = []
        while idx < len(lines):
            next_line = lines[idx].strip()
            if QUESTION_SENTINEL_RE.match(next_line) and not OPTION_RE.match(next_line):
                break
            opt_match = OPTION_RE.match(next_line)
            if not opt_match:
                if ANSWER_LINE_RE.match(next_line):
                    break
                idx += 1
                continue
            label = opt_match.group(1).upper()
            option_text, idx = _join_option_lines(lines, idx)
            options[label] = option_text
            if len(options) == 4:
                break
        if len(options) != 4:
            notes.append(f"expected 4 options, found {len(options)}")
        if number not in answers:
            notes.append("missing answer key entry")
        questions.append(
            ParsedQuestion(
                number=number,
                question=normalize_inline(" ".join(question_parts)),
                options=options,
                notes=notes,
            )
        )

    mcqs: list[MCQ] = []
    review_count = 0
    for parsed in questions:
        needs_review = bool(parsed.notes) or sorted(parsed.options) != ["A", "B", "C", "D"]
        if needs_review:
            review_count += 1
        mcqs.append(
            MCQ(
                id=f"orig-draft-{parsed.number:03d}",
                question=parsed.question,
                options=[parsed.options.get(label, "") for label in ["A", "B", "C", "D"]],
                correct_option=answers.get(parsed.number, ""),
                source="original",
                explanation=None,
                topic=None,
                needs_review=needs_review,
                notes="; ".join(parsed.notes),
            )
        )
    stats = {
        "questions_found": len(mcqs),
        "answers_found": len(answers),
        "needs_review": review_count,
    }
    return mcqs, stats
