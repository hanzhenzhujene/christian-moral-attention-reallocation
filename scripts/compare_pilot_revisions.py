#!/usr/bin/env python3
"""Compare pilot revision bundles across branches."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_point(summary_record: Dict[str, Any], metric_name: str) -> Any:
    metrics = summary_record.get("metrics", {})
    entry = metrics.get(metric_name)
    if isinstance(entry, dict):
        return entry.get("point")
    return entry


def extract_branch_rows(branch: str, results_root: Path) -> List[Dict[str, Any]]:
    branch_dir = results_root / f"pilot_live_{branch}"
    summary_path = branch_dir / f"pilot_{branch}_smoke_bundle_summary.json"
    health_path = branch_dir / f"pilot_{branch}_smoke_bundle_health.json"
    if not summary_path.exists() or not health_path.exists():
        raise FileNotFoundError(f"Missing summary or health bundle for {branch}: {branch_dir}")

    summary = load_json(summary_path)
    health = load_json(health_path)
    parse_failure_rate = health["parse_failure_rate"]

    rows: List[Dict[str, Any]] = []
    for record in summary["summaries"]:
        rows.append(
            {
                "branch": branch,
                "model": record["model"],
                "condition": record["condition"],
                "n_items": record["n_items"],
                "parse_failure_rate": parse_failure_rate,
                "task_a_accuracy": metric_point(record, "task_a_accuracy"),
                "task_b_accuracy": metric_point(record, "task_b_accuracy"),
                "heart_sensitivity_score": metric_point(record, "heart_sensitivity_score"),
                "same_heart_control_accuracy": metric_point(record, "same_heart_control_accuracy"),
                "heart_overreach_rate": metric_point(record, "heart_overreach_rate"),
                "p_reason_motive": metric_point(record, "p_reason_motive"),
                "motive_cross_task_consistency": metric_point(record, "motive_cross_task_consistency"),
                "mean_explanation_chars": metric_point(record, "mean_explanation_chars"),
            }
        )
    return rows


def build_markdown(rows: List[Dict[str, Any]]) -> str:
    header = [
        "branch",
        "model",
        "condition",
        "parse_fail",
        "HSS",
        "SameHeart",
        "HOR",
        "P(reason=motive)",
        "motive_CTC",
        "mean_chars",
    ]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["branch"]),
                    str(row["model"]),
                    str(row["condition"]),
                    str(row["parse_failure_rate"]),
                    str(row["heart_sensitivity_score"]),
                    str(row["same_heart_control_accuracy"]),
                    str(row["heart_overreach_rate"]),
                    str(row["p_reason_motive"]),
                    str(row["motive_cross_task_consistency"]),
                    str(row["mean_explanation_chars"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def branch_sort_key(branch: str) -> tuple[int, str]:
    match = re.fullmatch(r"v(\d+)", branch)
    if match:
        return (int(match.group(1)), branch)
    return (10**9, branch)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branches", nargs="+", required=True, help="Revision branch names such as v7 v8 v9")
    parser.add_argument(
        "--results-root",
        default="results",
        help="Root directory containing pilot_live_<branch> subdirectories",
    )
    parser.add_argument("--output-json", required=True, help="Write comparison table as JSON")
    parser.add_argument("--output-md", required=True, help="Write comparison table as Markdown")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results_root = Path(args.results_root)
    rows: List[Dict[str, Any]] = []
    for branch in args.branches:
        rows.extend(extract_branch_rows(branch, results_root))

    rows.sort(key=lambda row: (branch_sort_key(row["branch"]), row["model"], row["condition"]))

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    output_md.write_text(build_markdown(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {output_json}")
    print(f"Wrote markdown table to {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
