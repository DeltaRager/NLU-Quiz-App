from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_builder.env_utils import load_dotenv
from quiz_builder.generator import build_generated_mcqs
from quiz_builder.io_utils import load_chunks, load_mcqs, save_mcqs, write_json
from quiz_builder.openai_generator import OpenAIGenerationConfig, build_generated_mcqs_with_openai


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate new offline MCQs from extracted course text.")
    parser.add_argument("--chunks", type=Path, default=Path("quiz_data/source_chunks.json"))
    parser.add_argument("--existing-questions", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("quiz_data/generated_draft.json"))
    parser.add_argument("--stats", type=Path, default=Path("quiz_data/generated_stats.json"))
    parser.add_argument("--target-count", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--provider", choices=["openai", "offline"], default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--original-examples", type=Path, default=Path("quiz_data/originals_reviewed.json"))
    return parser.parse_args()


def render_progress(current: int, total: int, width: int = 30) -> str:
    total = max(total, 1)
    filled = int(width * current / total)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def progress_callback(event: str, current: int, total: int, round_index: int, max_rounds: int, batch_added: int = 0) -> None:
    bar = render_progress(current, total)
    if event == "request_started":
        print(f"{bar} {current}/{total} | round {round_index}/{max_rounds} | requesting batch...")
    elif event == "request_finished":
        print(f"{bar} {current}/{total} | round {round_index}/{max_rounds} | accepted {batch_added}")


def main() -> None:
    args = parse_args()
    load_dotenv(Path(".env"))
    chunks = load_chunks(args.chunks)
    existing_questions = load_mcqs(args.existing_questions) if args.existing_questions else []
    if args.provider == "openai":
        generated = build_generated_mcqs_with_openai(
            chunks=chunks,
            target_count=args.target_count,
            existing_questions=existing_questions,
            original_examples_path=args.original_examples,
            config=OpenAIGenerationConfig(model=args.model, progress_callback=progress_callback),
        )
    else:
        generated = build_generated_mcqs(
            chunks,
            existing_questions,
            target_count=args.target_count,
            seed=args.seed,
        )
    if len(generated) < args.target_count:
        raise SystemExit(f"Generation did not reach the requested count. Generated {len(generated)} of {args.target_count}.")
    save_mcqs(args.output, generated)
    write_json(
        args.stats,
        {
            "requested_count": args.target_count,
            "generated_count": len(generated),
            "seed": args.seed,
            "provider": args.provider,
            "model": args.model if args.provider == "openai" else None,
        },
    )
    print(f"Saved {len(generated)} generated questions to {args.output}")


if __name__ == "__main__":
    main()
