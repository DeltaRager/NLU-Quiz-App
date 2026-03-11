from quiz_builder.generator import build_generated_mcqs
from quiz_builder.models import MCQ, TextChunk


def test_build_generated_mcqs_produces_structurally_valid_items():
    chunks = [
        TextChunk(
            chunk_id="tutorial-001",
            source_pdf="nlu-tutorials.pdf",
            topic="Word Sense Disambiguation",
            text=(
                "Word Sense Disambiguation refers to assigning the correct meaning to a word in context. "
                "Sense inventory is the catalog of meanings used by the system. "
                "Word Sense Disambiguation versus Named Entity Recognition is discussed in class. "
                "Word Sense Disambiguation improves downstream understanding when ambiguous words appear in context. "
                "Lexical ambiguity should be resolved using context rather than isolated word forms."
            ),
            keywords=["disambiguation", "sense", "context", "ambiguity"],
        ),
        TextChunk(
            chunk_id="tutorial-002",
            source_pdf="nlu-tutorials.pdf",
            topic="Symbol Grounding",
            text=(
                "Symbol Grounding is linking symbols to perceptual or experiential meaning. "
                "Grounded representations support intention-aware reasoning in situated systems. "
                "Symbol Grounding versus Surface Matching is highlighted as an important distinction. "
                "Grounded representations improve robustness when the language refers to the physical world."
            ),
            keywords=["grounding", "symbols", "perceptual", "meaning"],
        ),
    ]
    existing = [
        MCQ(
            id="orig-001",
            question="Which task assigns a meaning to an ambiguous word in context?",
            options=["WSD", "NER", "Topic modeling", "OCR"],
            correct_option="A",
            source="original",
        )
    ]

    generated = build_generated_mcqs(chunks, existing, target_count=4, seed=7)

    assert len(generated) >= 2
    for mcq in generated:
        assert len(mcq.options) == 4
        assert mcq.correct_option in {"A", "B", "C", "D"}
        assert mcq.source == "generated"
        assert mcq.source_pdf
        assert mcq.source_snippet

