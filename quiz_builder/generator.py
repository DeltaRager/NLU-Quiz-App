from __future__ import annotations

import random
import re
from collections import defaultdict

from quiz_builder.models import MCQ, TextChunk
from quiz_builder.text_utils import normalize_inline, normalized_key


DEFINITION_RE = re.compile(
    r"(?P<term>[A-Z][A-Za-z0-9/\- ]{2,40})\s+(?:is|refers to|describes|means)\s+(?P<definition>[^.?!]{25,240})[.?!]"
)
CONTRAST_RE = re.compile(
    r"(?P<left>[A-Z][A-Za-z0-9/\- ]{2,30})\s+(?:vs\.?|versus|compared with)\s+(?P<right>[A-Z][A-Za-z0-9/\- ]{2,30})",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")
WORD_BOUNDARY_TEMPLATE = r"\b{}\b"
NOISE_TOKEN_RE = re.compile(r"\b(?:ce|cg|ca|Ol|SE|CR|Al|A\d+|Q\d+)\b")
NON_WORDY_RE = re.compile(r"[^A-Za-z0-9 ,.'\"()/%:-]")
GENERIC_KEYWORDS = {
    "using",
    "between",
    "discuss",
    "explain",
    "examples",
    "example",
    "following",
    "system",
    "systems",
    "each",
    "perform",
    "selected",
    "problems",
    "action",
    "average",
    "research",
    "things",
    "people",
    "same",
    "many",
    "move",
    "good",
    "else",
    "place",
    "time",
    "category",
    "categories",
    "benefits",
    "question",
    "questions",
    "tutorial",
    "lecture",
    "knowledge",
}


def build_generated_mcqs(
    chunks: list[TextChunk],
    existing_questions: list[MCQ] | None = None,
    target_count: int = 400,
    seed: int = 42,
) -> list[MCQ]:
    rng = random.Random(seed)
    existing_questions = existing_questions or []
    existing_keys = {normalized_key(mcq.question) for mcq in existing_questions}
    concepts_by_topic = collect_concepts(chunks)
    statement_bank = collect_keyword_statements(chunks, concepts_by_topic)
    candidates: list[MCQ] = []
    seen_generated: set[str] = set()

    for chunk in chunks:
        candidates.extend(generate_definition_questions(chunk, concepts_by_topic, existing_keys, seen_generated, rng))
        candidates.extend(generate_contrast_questions(chunk, concepts_by_topic, existing_keys, seen_generated, rng))
        candidates.extend(generate_cloze_questions(chunk, concepts_by_topic, existing_keys, seen_generated, rng))
        candidates.extend(
            generate_keyword_statement_questions(
                chunk,
                statement_bank,
                existing_keys,
                seen_generated,
                rng,
            )
        )

    rng.shuffle(candidates)
    unique_candidates = dedupe_generated_candidates(candidates)
    trimmed = unique_candidates[:target_count]
    for idx, mcq in enumerate(trimmed, start=1):
        mcq.id = f"gen-draft-{idx:03d}"
    return trimmed


def collect_concepts(chunks: list[TextChunk]) -> dict[str, list[str]]:
    concepts: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        for match in DEFINITION_RE.finditer(chunk.text):
            term = normalize_inline(match.group("term"))
            if term not in concepts[chunk.topic]:
                concepts[chunk.topic].append(term)
        for keyword in chunk.keywords:
            title = keyword.title()
            if title not in concepts[chunk.topic]:
                concepts[chunk.topic].append(title)
    return concepts


def generate_definition_questions(
    chunk: TextChunk,
    concepts_by_topic: dict[str, list[str]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    concepts = concepts_by_topic.get(chunk.topic, [])
    distractor_pool = [concept for concept in concepts if concept]
    for match in DEFINITION_RE.finditer(chunk.text):
        term = normalize_inline(match.group("term"))
        definition = normalize_inline(match.group("definition"))
        if len(term.split()) > 7 or len(definition.split()) < 5:
            continue
        question = f"Which concept is best described as: {definition}?"
        key = normalized_key(question)
        if key in existing_keys or key in seen_generated:
            continue
        distractors = build_distractors(term, distractor_pool, rng)
        if len(distractors) != 3:
            continue
        options = shuffle_options([term, *distractors], term, rng)
        if len(options) != 4 or term not in options:
            continue
        output.append(
            make_generated_mcq(
                question=question,
                options=options,
                correct_text=term,
                chunk=chunk,
            )
        )
        seen_generated.add(key)
    return output


def generate_true_statement_questions(
    chunk: TextChunk,
    concepts_by_topic: dict[str, list[str]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    sentences = [normalize_inline(sentence) for sentence in SENTENCE_RE.split(chunk.text) if len(normalize_inline(sentence).split()) >= 8]
    topic_terms = concepts_by_topic.get(chunk.topic, [])
    for sentence in sentences:
        if len(output) >= 2:
            break
        if not any(term.lower() in sentence.lower() for term in topic_terms[:8]):
            continue
        question = f"Which statement is most consistent with the course material on {chunk.topic}?"
        key = normalized_key(question + sentence)
        if key in existing_keys or key in seen_generated:
            continue
        false_statements = make_false_statements(sentence, sentences, rng)
        if len(false_statements) != 3:
            continue
        options = shuffle_options([sentence, *false_statements], sentence, rng)
        if len(options) != 4 or sentence not in options:
            continue
        output.append(
            make_generated_mcq(
                question=question,
                options=options,
                correct_text=sentence,
                chunk=chunk,
            )
        )
        seen_generated.add(key)
    return output


def collect_keyword_statements(
    chunks: list[TextChunk],
    concepts_by_topic: dict[str, list[str]],
) -> dict[str, list[tuple[str, TextChunk]]]:
    statements: dict[str, list[tuple[str, TextChunk]]] = defaultdict(list)
    for chunk in chunks:
        keywords = [item for item in dict.fromkeys(chunk.keywords + concepts_by_topic.get(chunk.topic, [])) if is_viable_keyword(item)]
        sentences = cleaned_sentences(chunk.text)
        for keyword in keywords:
            sentence = next((item for item in sentences if keyword_in_text(keyword, item)), "")
            if not sentence:
                continue
            statement = normalize_statement(sentence)
            if not is_viable_statement(statement):
                continue
            statements[keyword].append((statement, chunk))
    return statements


def generate_contrast_questions(
    chunk: TextChunk,
    concepts_by_topic: dict[str, list[str]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    concepts = concepts_by_topic.get(chunk.topic, [])
    for match in CONTRAST_RE.finditer(chunk.text):
        left = normalize_inline(match.group("left"))
        right = normalize_inline(match.group("right"))
        if left == right:
            continue
        question = f"According to the material, which option identifies the correct contrast partner for {left}?"
        key = normalized_key(question)
        if key in existing_keys or key in seen_generated:
            continue
        distractors = build_distractors(right, [concept for concept in concepts if concept != left], rng)
        if len(distractors) != 3:
            continue
        options = shuffle_options([right, *distractors], right, rng)
        if len(options) != 4 or right not in options:
            continue
        output.append(
            make_generated_mcq(
                question=question,
                options=options,
                correct_text=right,
                chunk=chunk,
            )
        )
        seen_generated.add(key)
        if len(output) >= 2:
            break
    return output


def generate_cloze_questions(
    chunk: TextChunk,
    concepts_by_topic: dict[str, list[str]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    context = chunk_context_label(chunk)
    sentences = [normalize_inline(sentence) for sentence in SENTENCE_RE.split(chunk.text) if len(normalize_inline(sentence).split()) >= 6]
    if not sentences:
        return output
    keyword_candidates = [
        item for item in dict.fromkeys(chunk.keywords + concepts_by_topic.get(chunk.topic, [])) if is_viable_keyword(item)
    ]
    for keyword in keyword_candidates:
        if len(output) >= 3:
            break
        sentence = next((item for item in sentences if keyword_in_text(keyword, item) and is_viable_statement(item)), "")
        if not sentence:
            continue
        blanked = blank_keyword(sentence, keyword)
        if not blanked or blanked == sentence or not is_viable_statement(blanked.replace("_____", keyword)):
            continue
        question = f"Which term best completes the following statement: {blanked}"
        key = normalized_key(question)
        if key in existing_keys or key in seen_generated:
            continue
        distractors = build_distractors(keyword, global_concept_pool(concepts_by_topic, exclude_topic=chunk.topic), rng)
        if len(distractors) != 3:
            continue
        options = shuffle_options([keyword, *distractors], keyword, rng)
        if len(options) != 4 or keyword not in options:
            continue
        output.append(make_generated_mcq(question, options, keyword, chunk))
        seen_generated.add(key)
    return output


def generate_keyword_context_questions(
    chunk: TextChunk,
    concepts_by_topic: dict[str, list[str]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    context = chunk_context_label(chunk)
    snippet = make_snippet(chunk.text, max_words=24)
    if not snippet:
        return output
    keyword_candidates = [keyword for keyword in chunk.keywords if is_viable_keyword(keyword) and keyword_in_text(keyword, chunk.text)]
    for keyword in keyword_candidates[:2]:
        question = (
            f"Which term is most directly supported by the following material from {context}: "
            f"\"{snippet}\""
        )
        key = normalized_key(question + keyword)
        if key in existing_keys or key in seen_generated:
            continue
        distractors = build_distractors(keyword, global_keyword_pool(concepts_by_topic, exclude_topic=chunk.topic), rng)
        if len(distractors) != 3:
            continue
        options = shuffle_options([keyword, *distractors], keyword, rng)
        if len(options) != 4 or keyword not in options:
            continue
        output.append(make_generated_mcq(question, options, keyword, chunk))
        seen_generated.add(key)
    return output


def generate_keyword_statement_questions(
    chunk: TextChunk,
    statement_bank: dict[str, list[tuple[str, TextChunk]]],
    existing_keys: set[str],
    seen_generated: set[str],
    rng: random.Random,
) -> list[MCQ]:
    output: list[MCQ] = []
    for keyword in [item for item in chunk.keywords if is_viable_keyword(item)][:4]:
        entries = statement_bank.get(keyword, [])
        if not entries:
            continue
        correct_statement, source_chunk = entries[0]
        if source_chunk.chunk_id != chunk.chunk_id:
            continue
        question = f"Which statement about {keyword} is correct?"
        key = normalized_key(question)
        if key in existing_keys or key in seen_generated:
            continue
        distractors = build_statement_distractors(keyword, correct_statement, statement_bank, rng)
        if len(distractors) != 3:
            continue
        options = shuffle_options([correct_statement, *distractors], correct_statement, rng)
        if len(options) != 4 or correct_statement not in options:
            continue
        output.append(make_generated_mcq(question, options, correct_statement, chunk))
        seen_generated.add(key)
    return output


def build_distractors(correct: str, pool: list[str], rng: random.Random) -> list[str]:
    unique_pool = [item for item in dict.fromkeys(pool) if normalized_key(item) != normalized_key(correct)]
    if len(unique_pool) < 3:
        return []
    ranked = sorted(unique_pool, key=lambda item: similarity_score(correct, item), reverse=True)
    selected = ranked[:6]
    rng.shuffle(selected)
    distractors: list[str] = []
    for item in selected:
        if normalized_key(item) == normalized_key(correct):
            continue
        if normalized_key(item) in {normalized_key(existing) for existing in distractors}:
            continue
        distractors.append(item)
        if len(distractors) == 3:
            break
    return distractors


def build_statement_distractors(
    keyword: str,
    correct_statement: str,
    statement_bank: dict[str, list[tuple[str, TextChunk]]],
    rng: random.Random,
) -> list[str]:
    pool: list[str] = []
    for other_keyword, entries in statement_bank.items():
        if normalized_key(other_keyword) == normalized_key(keyword):
            continue
        for statement, _chunk in entries[:1]:
            if normalized_key(statement) != normalized_key(correct_statement):
                pool.append(statement)
    ranked = sorted(pool, key=lambda item: similarity_score(correct_statement, item), reverse=True)
    selected = ranked[:12]
    rng.shuffle(selected)
    distractors: list[str] = []
    seen: set[str] = set()
    for item in selected:
        key = normalized_key(item)
        if key in seen or not is_viable_statement(item):
            continue
        seen.add(key)
        distractors.append(item)
        if len(distractors) == 3:
            break
    return distractors


def global_concept_pool(concepts_by_topic: dict[str, list[str]], exclude_topic: str) -> list[str]:
    pool: list[str] = []
    for topic, concepts in concepts_by_topic.items():
        if topic == exclude_topic:
            continue
        pool.extend(concepts)
    return pool


def global_keyword_pool(concepts_by_topic: dict[str, list[str]], exclude_topic: str) -> list[str]:
    return global_concept_pool(concepts_by_topic, exclude_topic)


def similarity_score(left: str, right: str) -> tuple[int, int]:
    left_words = set(normalized_key(word) for word in left.split())
    right_words = set(normalized_key(word) for word in right.split())
    overlap = len(left_words & right_words)
    return overlap, -abs(len(left) - len(right))


def keyword_in_text(keyword: str, text: str) -> bool:
    return re.search(WORD_BOUNDARY_TEMPLATE.format(re.escape(keyword)), text, flags=re.IGNORECASE) is not None


def blank_keyword(sentence: str, keyword: str) -> str:
    return re.sub(
        WORD_BOUNDARY_TEMPLATE.format(re.escape(keyword)),
        "_____",
        sentence,
        count=1,
        flags=re.IGNORECASE,
    )


def make_snippet(text: str, max_words: int = 24) -> str:
    words = normalize_inline(text).split()
    if len(words) < 8:
        return ""
    snippet = " ".join(words[:max_words]).strip()
    if snippet.endswith((".", "?", "!")):
        return snippet
    return snippet + " ..."


def chunk_context_label(chunk: TextChunk) -> str:
    tutorial_match = re.search(r"Tutorial\s+\d+", chunk.text, flags=re.IGNORECASE)
    if tutorial_match:
        return tutorial_match.group(0)
    return chunk.topic


def cleaned_sentences(text: str) -> list[str]:
    return [normalize_statement(sentence) for sentence in SENTENCE_RE.split(text) if normalize_statement(sentence)]


def normalize_statement(text: str) -> str:
    text = normalize_inline(text)
    text = NOISE_TOKEN_RE.sub("", text)
    text = NON_WORDY_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:_")
    text = re.sub(r'^\W+', "", text)
    return text


def is_viable_statement(text: str) -> bool:
    words = text.split()
    if len(words) < 6 or len(words) > 28:
        return False
    lowered = text.lower()
    banned_fragments = [
        "course material",
        "tutorial",
        "which statement",
        "which term",
        "the following material",
        "q1",
        "a1",
        "se ce",
    ]
    if any(fragment in lowered for fragment in banned_fragments):
        return False
    if text.count('"') % 2 == 1:
        return False
    alpha_ratio = sum(ch.isalpha() for ch in text) / max(len(text), 1)
    return alpha_ratio >= 0.65


def is_viable_keyword(keyword: str) -> bool:
    cleaned = normalize_statement(keyword)
    if not cleaned:
        return False
    if cleaned.lower() in GENERIC_KEYWORDS:
        return False
    if len(cleaned) < 3 or len(cleaned) > 24:
        return False
    if cleaned.isdigit():
        return False
    alpha_ratio = sum(ch.isalpha() for ch in cleaned) / max(len(cleaned), 1)
    return alpha_ratio >= 0.7


def dedupe_generated_candidates(candidates: list[MCQ]) -> list[MCQ]:
    deduped: list[MCQ] = []
    seen_questions: set[str] = set()
    for mcq in candidates:
        key = normalized_key(mcq.question)
        if key in seen_questions:
            continue
        seen_questions.add(key)
        deduped.append(mcq)
    return deduped


def shuffle_options(options: list[str], correct_text: str, rng: random.Random) -> list[str]:
    shuffled = options[:]
    rng.shuffle(shuffled)
    if len(shuffled) != 4 or len({normalized_key(option) for option in shuffled}) != 4:
        return []
    return shuffled


def make_false_statements(correct_sentence: str, sentence_pool: list[str], rng: random.Random) -> list[str]:
    distractors: list[str] = []
    correct_tokens = correct_sentence.split()
    for sentence in sentence_pool:
        if normalized_key(sentence) == normalized_key(correct_sentence):
            continue
        if len(sentence.split()) < 8:
            continue
        mutated = mutate_statement(correct_tokens, sentence.split(), rng)
        if mutated and normalized_key(mutated) != normalized_key(correct_sentence):
            distractors.append(mutated)
        if len(distractors) == 3:
            break
    return distractors


def mutate_statement(correct_tokens: list[str], donor_tokens: list[str], rng: random.Random) -> str | None:
    if len(correct_tokens) < 8 or len(donor_tokens) < 4:
        return None
    cut = max(3, min(len(correct_tokens) - 2, len(donor_tokens) // 2))
    merged = correct_tokens[:cut] + donor_tokens[-(len(correct_tokens) - cut) :]
    sentence = normalize_inline(" ".join(merged))
    if sentence.endswith("."):
        return sentence
    return sentence + "."


def make_generated_mcq(question: str, options: list[str], correct_text: str, chunk: TextChunk) -> MCQ:
    correct_index = options.index(correct_text)
    correct_option = ["A", "B", "C", "D"][correct_index]
    return MCQ(
        id="",
        question=normalize_inline(question),
        options=options,
        correct_option=correct_option,
        source="generated",
        topic=chunk.topic,
        needs_review=False,
        notes="",
        source_pdf=chunk.source_pdf,
        source_snippet=normalize_inline(chunk.text[:280]),
    )
