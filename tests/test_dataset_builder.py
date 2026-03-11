import json
from pathlib import Path

from quiz_builder.dataset_builder import build_combined_dataset


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_combined_dataset_assigns_stable_ids_and_shuffles(tmp_path: Path):
    originals = [
        {
            "id": "orig-draft-001",
            "question": "Original question?",
            "options": ["A1", "B1", "C1", "D1"],
            "correct_option": "A",
            "source": "original",
            "topic": None,
            "needs_review": False,
            "notes": "",
            "source_pdf": None,
            "source_snippet": None,
        }
    ]
    generated = [
        {
            "id": "gen-draft-001",
            "question": "Generated question?",
            "options": ["A2", "B2", "C2", "D2"],
            "correct_option": "B",
            "source": "generated",
            "topic": "Topic",
            "needs_review": False,
            "notes": "",
            "source_pdf": "nlu-tutorials.pdf",
            "source_snippet": "snippet",
        }
    ]
    originals_path = tmp_path / "originals_reviewed.json"
    generated_path = tmp_path / "generated_reviewed.json"
    combined_path = tmp_path / "questions_combined.json"
    shuffled_path = tmp_path / "questions_shuffled.json"
    write_json(originals_path, originals)
    write_json(generated_path, generated)

    combined, shuffled = build_combined_dataset(
        originals_path=originals_path,
        generated_path=generated_path,
        combined_path=combined_path,
        shuffled_path=shuffled_path,
        seed=13,
        expected_originals=1,
        expected_generated=1,
    )

    assert [mcq.id for mcq in combined] == ["orig-001", "gen-001"]
    assert sorted(mcq.id for mcq in shuffled) == ["gen-001", "orig-001"]
    assert combined_path.exists()
    assert shuffled_path.exists()


def test_build_combined_dataset_supports_generated_only(tmp_path: Path):
    generated = [
        {
            "id": "gen-draft-001",
            "question": "Generated only question?",
            "options": ["A", "B", "C", "D"],
            "correct_option": "C",
            "source": "generated",
            "topic": "Topic",
            "needs_review": False,
            "notes": "",
            "source_pdf": "nlu-tutorials.pdf",
            "source_snippet": "snippet",
        }
    ]
    generated_path = tmp_path / "generated_reviewed.json"
    combined_path = tmp_path / "questions_combined.json"
    shuffled_path = tmp_path / "questions_shuffled.json"
    write_json(generated_path, generated)

    combined, shuffled = build_combined_dataset(
        originals_path=None,
        generated_path=generated_path,
        combined_path=combined_path,
        shuffled_path=shuffled_path,
        seed=13,
        expected_originals=0,
        expected_generated=1,
    )

    assert [mcq.id for mcq in combined] == ["gen-001"]
    assert [mcq.id for mcq in shuffled] == ["gen-001"]
