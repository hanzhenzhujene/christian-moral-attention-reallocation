#!/usr/bin/env python3
"""Break down Task B swap-gap by model, condition, and pair type."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean(values: Iterable[int]) -> float | None:
    values = list(values)
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def distribution(values: Iterable[str]) -> Dict[str, float]:
    values = list(values)
    if not values:
        return {}
    counts = Counter(values)
    total = sum(counts.values())
    return {label: round(count / total, 4) for label, count in sorted(counts.items())}


def bucket_name(record: Dict[str, Any], mode: str) -> str:
    if mode == "pair_type":
        return record["pair_type"]
    if mode == "benchmark_source":
        return record["benchmark_source"]
    if mode == "pair_type_and_source":
        return f"{record['benchmark_source']}::{record['pair_type']}"
    raise ValueError(f"Unsupported bucket mode: {mode}")


def summarize_bucket(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    swapped_false = [row for row in rows if not row["swapped"]]
    swapped_true = [row for row in rows if row["swapped"]]

    def task_b_correct(row: Dict[str, Any]) -> int:
        return int(
            row["response"]["task_b_worse_inward_orientation"]
            == row["gold"]["task_b_worse_inward_orientation"]
        )

    acc_false = mean(task_b_correct(row) for row in swapped_false)
    acc_true = mean(task_b_correct(row) for row in swapped_true)
    gap = None if acc_false is None or acc_true is None else round(abs(acc_false - acc_true), 4)

    return {
        "n_items": len(rows),
        "n_swapped_false": len(swapped_false),
        "n_swapped_true": len(swapped_true),
        "task_b_accuracy_swapped_false": acc_false,
        "task_b_accuracy_swapped_true": acc_true,
        "task_b_swap_accuracy_gap": gap,
        "task_b_answer_distribution_swapped_false": distribution(
            row["response"]["task_b_worse_inward_orientation"] for row in swapped_false
        ),
        "task_b_answer_distribution_swapped_true": distribution(
            row["response"]["task_b_worse_inward_orientation"] for row in swapped_true
        ),
    }


def render_markdown(groups: Sequence[Dict[str, Any]], bucket_mode: str) -> str:
    lines = [
        "# Task B Swap-Gap Breakdown",
        "",
        f"Bucket mode: `{bucket_mode}`",
        "",
    ]
    for group in groups:
        lines.append(f"## {group['model']} / {group['condition']}")
        lines.append("")
        lines.append("| Bucket | n | swap_false acc | swap_true acc | abs gap |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for bucket in group["buckets"]:
            lines.append(
                "| {bucket_name} | {n_items} | {acc_false} | {acc_true} | {gap} |".format(
                    bucket_name=bucket["bucket"],
                    n_items=bucket["n_items"],
                    acc_false=bucket["task_b_accuracy_swapped_false"],
                    acc_true=bucket["task_b_accuracy_swapped_true"],
                    gap=bucket["task_b_swap_accuracy_gap"],
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Run JSONL files")
    parser.add_argument(
        "--bucket-mode",
        choices=["pair_type", "benchmark_source", "pair_type_and_source"],
        default="pair_type",
        help="How to partition rows before computing swap-gap",
    )
    parser.add_argument("--output-json", required=True, help="JSON output path")
    parser.add_argument("--output-md", help="Optional markdown output path")
    args = parser.parse_args(argv)

    rows: List[Dict[str, Any]] = []
    for raw_path in args.input:
        rows.extend(load_jsonl(Path(raw_path)))

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["model"], row["condition"])].append(row)

    results: List[Dict[str, Any]] = []
    for (model, condition), group_rows in sorted(grouped.items()):
        bucketed: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in group_rows:
            bucketed[bucket_name(row, args.bucket_mode)].append(row)
        bucket_summaries = []
        for bucket, bucket_rows in sorted(bucketed.items()):
            bucket_summary = {"bucket": bucket, **summarize_bucket(bucket_rows)}
            bucket_summaries.append(bucket_summary)
        results.append(
            {
                "model": model,
                "condition": condition,
                "bucket_mode": args.bucket_mode,
                "buckets": bucket_summaries,
            }
        )

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote swap-gap breakdown to {output_json}")

    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(results, args.bucket_mode), encoding="utf-8")
        print(f"Wrote markdown breakdown to {output_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
