# NLU Quiz App

This repository contains a local Streamlit quiz app for NLU exam practice, plus the supporting Python modules and helper scripts used to prepare the quiz data.

The live app currently uses only the original questions extracted from `documents/nlu-quiz.pdf`.

## What is in this repo

- `app.py`: Streamlit app
- `quiz_builder/`: shared app and data utilities
- `scripts/`: extraction, generation, and dataset build helpers
- `quiz_data/`: local JSON datasets and saved session results
- `tests/`: parser and data-pipeline tests

The raw PDF folder `documents/` is intentionally not tracked by git.

## App features

- 30-question timed sessions
- 18-minute countdown
- Random sampling from the original quiz bank
- Local JSON result saving
- Post-quiz review mode
- Optional OpenAI-powered explanations in review

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`

Install:

```bash
python3 -m pip install -r requirements.txt
```

## Optional OpenAI setup

Question explanations in review mode use the OpenAI API.

Create a project-root `.env` file:

```bash
OPENAI_API_KEY=your_key_here
```

Without an API key, the quiz app still works, but explanation requests will fail.

## Run the app

```bash
streamlit run app.py
```

## Expected local data

The app loads the first available originals dataset from:

- `quiz_data/originals_reviewed.json`
- `quiz_data/originals_extracted.json`

Session results are written to:

- `quiz_data/session_results/`

## Question format

Each question record uses this JSON shape:

```json
{
  "id": "orig-001",
  "question": "How does lemmatization differ from stemming?",
  "options": [
    "It only applies to named entities.",
    "It uses a dictionary to find the base form, while stemming strips affixes with rules.",
    "It always produces longer tokens than stemming.",
    "It is the same process as chunking."
  ],
  "correct_option": "B",
  "source": "original",
  "topic": null,
  "needs_review": false,
  "notes": "",
  "source_pdf": "nlu-quiz.pdf",
  "source_snippet": null
}
```

## Notes

- Timed quiz sessions use only original quiz questions.
- Explanations are disabled during the live quiz and available only in review mode.
- Helper scripts are included in the repo, but they are not required to run the Streamlit app once the JSON dataset already exists.
