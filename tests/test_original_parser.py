from quiz_builder.original_parser import parse_quiz_text


def test_parse_quiz_text_extracts_questions_and_answers():
    pages = [
        """
        TITLE Q01
        Question 1: What does NLU primarily focus on?
        A. Understanding the meaning of language input
        B. Rendering 3D objects for virtual agents
        C. Encrypting text before transmission
        D. Converting speech into waveforms

        Question 2. Which task is most closely tied to word sense disambiguation?
        A. Assigning a unique sense to an ambiguous word in context
        B. Segmenting text into phonemes
        C. Tracking GPU utilization during training
        D. Compressing corpora into embeddings

        TITLE A01
        1 Answer: A
        2 Answer: A
        """
    ]

    mcqs, stats = parse_quiz_text(pages)

    assert stats["questions_found"] == 2
    assert stats["answers_found"] == 2
    assert mcqs[0].question == "What does NLU primarily focus on?"
    assert mcqs[0].options == [
        "Understanding the meaning of language input",
        "Rendering 3D objects for virtual agents",
        "Encrypting text before transmission",
        "Converting speech into waveforms",
    ]
    assert mcqs[0].correct_option == "A"
    assert mcqs[0].source == "original"


def test_parse_quiz_text_handles_q_page_a_page_format():
    pages = [
        "Quiz\n",
        (
            "Q1\n"
            "! What is the difference between NLP and NLU?\n"
            "A) NLP and NLU are synonymous and can be used interchangeably\n"
            "B) NLP focuses on text meaning, NLU on processing and generating text\n"
            "C) NLU includes more theoretical tasks, NLP is more focused on applications\n"
            "D) NLP handles language interaction, NLU focuses on understanding meaning\n"
        ),
        (
            "A1\n"
            "The correct answer is:\n"
            "D) NLP handles language interaction, NLU focuses on understanding meaning\n"
            "Explanation:\n"
            "! NLP is broad.\n"
        ),
    ]

    mcqs, stats = parse_quiz_text(pages)

    assert stats["questions_found"] == 1
    assert stats["answers_found"] == 1
    assert mcqs[0].question == "What is the difference between NLP and NLU?"
    assert mcqs[0].correct_option == "D"
    assert mcqs[0].explanation == "NLP is broad."
    assert mcqs[0].needs_review is False


def test_parse_quiz_text_marks_incomplete_blocks_for_review():
    pages = [
        """
        3) Which option is incomplete?
        A. First option
        B. Second option
        C. Third option

        3 Answer: B
        """
    ]

    mcqs, stats = parse_quiz_text(pages)

    assert len(mcqs) == 1
    assert mcqs[0].needs_review is True
    assert "expected 4 options" in mcqs[0].notes
    assert stats["needs_review"] == 1
