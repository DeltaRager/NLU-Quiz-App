from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_builder.course_chunks import chunk_document_pages
from quiz_builder.io_utils import save_chunks, write_json
from quiz_builder.pdf_ocr import OCRDependencyError, extract_pdf_pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract OCR text chunks from lecture/tutorial PDFs.")
    parser.add_argument("--documents-dir", type=Path, default=Path("documents"))
    parser.add_argument("--output", type=Path, default=Path("quiz_data/source_chunks.json"))
    parser.add_argument("--stats", type=Path, default=Path("quiz_data/source_chunks_stats.json"))
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_paths = sorted(path for path in args.documents_dir.glob("*.pdf") if path.name != "nlu-quiz.pdf")
    all_chunks = []
    stats: dict[str, int] = {}
    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_pages(pdf_path, dpi=args.dpi)
        except OCRDependencyError as exc:
            raise SystemExit(str(exc)) from exc
        chunks = chunk_document_pages(pdf_path.name, pages)
        stats[pdf_path.name] = len(chunks)
        all_chunks.extend(chunks)
        print(f"Chunked {pdf_path.name}: {len(chunks)} chunks")
    save_chunks(args.output, all_chunks)
    write_json(args.stats, stats)
    print(f"Saved {len(all_chunks)} chunks to {args.output}")


if __name__ == "__main__":
    main()
