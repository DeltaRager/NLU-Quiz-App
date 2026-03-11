# Offline NLU Quiz Builder

This project extracts lesson content from the provided NLU PDFs, generates an offline MCQ bank from that material, and serves the final bank through a local Streamlit quiz app.

## Prerequisites

- Python 3.10+
- `tesseract-ocr` installed and available on `PATH`

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Pipeline

1. Extract lecture/tutorial content:

```bash
python3 scripts/extract_course_text.py
```

This writes:

- `quiz_data/source_chunks.json`
- `quiz_data/source_chunks_stats.json`

2. Generate questions from the lesson PDFs.

OpenAI-backed generation:

```bash
python3 scripts/generate_mcqs_offline.py
```

This uses the OpenAI Responses API by default. You can either export the API key:

```bash
export OPENAI_API_KEY=your_key_here
```

or place it in a project-root `.env` file:

```bash
OPENAI_API_KEY=your_key_here
```

You can also force the older heuristic generator:

```bash
python3 scripts/generate_mcqs_offline.py --provider offline
```

This writes:

- `quiz_data/generated_draft.json`
- `quiz_data/generated_stats.json`

By default this targets 400 generated questions using `gpt-4o-mini`.

3. Review and correct `quiz_data/generated_draft.json`, then save the cleaned file as `quiz_data/generated_reviewed.json`.

4. Build the final dataset:

```bash
python3 scripts/build_quiz_dataset.py
```

This writes:

- `quiz_data/questions_combined.json`
- `quiz_data/questions_shuffled.json`

## Run the quiz app

```bash
streamlit run app.py
```

## Data format

The canonical question format is JSON with one object per MCQ:

```json
{
  "id": "gen-001",
  "question": "Which statement best describes symbol grounding?",
  "options": [
    "It links symbols to perceptual or experiential meaning.",
    "It replaces tokenization with stemming.",
    "It is a synonym for topic modeling.",
    "It only applies to dependency parsing."
  ],
  "correct_option": "A",
  "source": "generated",
  "topic": "Symbol grounding",
  "needs_review": false,
  "notes": "",
  "source_pdf": "nlu-tutorials.pdf",
  "source_snippet": "..."
}
```

`source_pdf` and `source_snippet` trace each generated question back to the lesson material.

## Tests

```bash
python3 -m pytest
```
# NLU-Quiz-App
