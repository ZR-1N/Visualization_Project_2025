"""High-volume data preparation entrypoint for CV landscape dashboards.

This script pins configuration for heavy runs (15k points, relaxed Sankey filters)
so `python scripts/final_processor.py` produces the desired datasets without
remembering a long CLI.
"""

from __future__ import annotations

import argparse
from typing import List

from process_advanced import main as run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the visualization pipeline with tuned high-density defaults."
    )
    parser.add_argument("--input", default="data/cleaned_papers.json")
    parser.add_argument("--landscape-output",
                        default="data/landscape_data.json")
    parser.add_argument("--sankey-output", default="data/sankey_data.json")
    parser.add_argument("--top-per-year", type=int, default=1200,
                        help="Number of papers sampled per year before global capping.")
    parser.add_argument("--max-landscape", type=int, default=15000,
                        help="Maximum number of landscape points to retain.")
    parser.add_argument("--tfidf-features", type=int, default=2000,
                        help="Vocabulary size for TF-IDF embedding.")
    parser.add_argument("--top-terms", type=int, default=6,
                        help="Maximum number of semantic tags per paper.")
    parser.add_argument("--min-link", type=float, default=2.0,
                        help="Sankey edge weight threshold.")
    return parser.parse_args()


def build_cli(args: argparse.Namespace) -> List[str]:
    return [
        "--input", str(args.input),
        "--landscape-output", str(args.landscape_output),
        "--sankey-output", str(args.sankey_output),
        "--top-per-year", str(args.top_per_year),
        "--max-landscape", str(args.max_landscape),
        "--tfidf-features", str(args.tfidf_features),
        "--top-terms", str(args.top_terms),
        "--min-link", str(args.min_link),
    ]


def main() -> None:
    args = parse_args()
    cli_args = build_cli(args)
    run_pipeline(cli_args)


if __name__ == "__main__":
    main()
