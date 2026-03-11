from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_builder.dataset_builder import DatasetBuildError, build_combined_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final combined and shuffled quiz datasets.")
    parser.add_argument("--originals", type=Path, default=None)
    parser.add_argument("--generated", type=Path, default=Path("quiz_data/generated_reviewed.json"))
    parser.add_argument("--combined-output", type=Path, default=Path("quiz_data/questions_combined.json"))
    parser.add_argument("--shuffled-output", type=Path, default=Path("quiz_data/questions_shuffled.json"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--expected-originals", type=int, default=0)
    parser.add_argument("--expected-generated", type=int, default=400)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        combined, shuffled = build_combined_dataset(
            originals_path=args.originals,
            generated_path=args.generated,
            combined_path=args.combined_output,
            shuffled_path=args.shuffled_output,
            seed=args.seed,
            expected_originals=args.expected_originals,
            expected_generated=args.expected_generated,
        )
    except DatasetBuildError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Combined dataset size: {len(combined)}")
    print(f"Shuffled dataset size: {len(shuffled)}")


if __name__ == "__main__":
    main()
