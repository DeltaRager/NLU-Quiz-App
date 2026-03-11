from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_builder.io_utils import save_mcqs, write_json
from quiz_builder.original_parser import parse_quiz_text
from quiz_builder.pdf_ocr import (
    OCRDependencyError,
    detect_tesseract_version,
    extract_pdf_pages_preferring_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract existing MCQs from the quiz PDF.")
    parser.add_argument("--pdf", type=Path, default=Path("documents/nlu-quiz.pdf"))
    parser.add_argument("--output", type=Path, default=Path("quiz_data/originals_extracted.json"))
    parser.add_argument("--stats", type=Path, default=Path("quiz_data/originals_extraction_stats.json"))
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        pages = extract_pdf_pages_preferring_text(args.pdf, dpi=args.dpi)
    except OCRDependencyError as exc:
        raise SystemExit(str(exc)) from exc
    mcqs, stats = parse_quiz_text(pages)
    stats["tesseract_version"] = detect_tesseract_version()
    save_mcqs(args.output, mcqs)
    write_json(args.stats, stats)
    print(f"Saved {len(mcqs)} extracted questions to {args.output}")
    print(f"Questions needing review: {stats['needs_review']}")


if __name__ == "__main__":
    main()
