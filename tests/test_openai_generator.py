from quiz_builder.models import MCQ
from quiz_builder.openai_generator import GeneratedQuestionPayload, is_valid_generated_mcq, payload_to_mcq


def test_payload_to_mcq_normalizes_and_validates():
    payload = GeneratedQuestionPayload(
        question="What does NLU focus on? ",
        options=[" Understanding meaning ", "Rendering pixels", "Sorting arrays", "Compressing images"],
        correct_option="a",
        topic="NLU basics",
        source_snippet="NLU focuses on understanding meaning.",
    )

    mcq = payload_to_mcq(payload)

    assert mcq.correct_option == "A"
    assert mcq.options[0] == "Understanding meaning"
    assert mcq.source == "generated"
    assert is_valid_generated_mcq(mcq) is True


def test_is_valid_generated_mcq_rejects_tutorial_wording():
    mcq = MCQ(
        id="gen-001",
        question="According to the material in Tutorial 4, what is ABSA?",
        options=["A", "B", "C", "D"],
        correct_option="A",
        source="generated",
    )

    assert is_valid_generated_mcq(mcq) is False
