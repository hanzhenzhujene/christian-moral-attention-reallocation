#!/usr/bin/env python3
"""Run the fixed post-pilot evaluation sequence in order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence


def run_step(label: str, command: List[str]) -> int:
    print(f"\n== {label} ==")
    print(" ".join(command))
    completed = subprocess.run(command, check=False)
    return completed.returncode


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Study config JSON")
    parser.add_argument("--jobs", required=True, help="Pilot jobs JSONL")
    parser.add_argument("--benchmark", required=True, help="Pilot benchmark JSON")
    parser.add_argument("--runs", nargs="+", required=True, help="Pilot run JSONL files")
    parser.add_argument("--failures", nargs="+", required=True, help="Pilot failure JSONL files")
    parser.add_argument("--models", nargs="+", required=True, help="Model aliases to score")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--prefix", default="paper_first_pilot", help="Output filename prefix")
    parser.add_argument("--bootstrap-samples", type=int, default=2000, help="Bootstrap draws for summary")
    return parser


def main(argv: Sequence[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix

    health_path = output_dir / f"{prefix}_health.json"
    diagnostics_path = output_dir / f"{prefix}_run_diagnostics.json"
    summary_path = output_dir / f"{prefix}_summary.json"
    qualitative_json_path = output_dir / f"{prefix}_qualitative_examples.json"
    qualitative_md_path = output_dir / f"{prefix}_qualitative_review.md"

    python = sys.executable
    step_failures = 0

    step_failures += 1 if run_step(
        "pilot health",
        [
            python,
            "scripts/evaluate_pilot_health.py",
            "--config",
            args.config,
            "--jobs",
            args.jobs,
            "--models",
            *args.models,
            "--runs",
            *args.runs,
            "--output",
            str(health_path),
        ],
    ) else 0
    step_failures += 1 if run_step(
        "run diagnostics",
        [
            python,
            "scripts/run_diagnostics.py",
            "--input",
            *args.runs,
            "--output",
            str(diagnostics_path),
        ],
    ) else 0
    step_failures += 1 if run_step(
        "metric summary",
        [
            python,
            "scripts/evaluate_runs.py",
            "--input",
            *args.runs,
            "--bootstrap-samples",
            str(args.bootstrap_samples),
            "--output",
            str(summary_path),
        ],
    ) else 0
    step_failures += 1 if run_step(
        "qualitative review packet",
        [
            python,
            "scripts/select_qualitative_examples.py",
            "--benchmark",
            args.benchmark,
            "--runs",
            *args.runs,
            "--failures",
            *args.failures,
            "--max-examples",
            "15",
            "--output-json",
            str(qualitative_json_path),
            "--output-md",
            str(qualitative_md_path),
        ],
    ) else 0

    print("\nWrote:")
    for path in (
        health_path,
        diagnostics_path,
        summary_path,
        qualitative_json_path,
        qualitative_md_path,
    ):
        print(path)
    return 1 if step_failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
