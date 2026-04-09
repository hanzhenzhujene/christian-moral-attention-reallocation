#!/usr/bin/env python3
"""Compare two solo annotation passes and report self-consistency."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence


TASK_FIELDS = ("task_a_label", "task_b_label", "task_c_label")


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def index_by_item(rows: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    indexed: Dict[str, Dict[str, str]] = {}
    for row in rows:
        item_id = row.get("item_id", "").strip()
        if item_id:
            indexed[item_id] = row
    return indexed


def label(row: Dict[str, str], field: str) -> str:
    return row.get(field, "").strip()


def bool_flag(row: Dict[str, str], field: str) -> bool:
    return row.get(field, "").strip().lower() in {"1", "true", "yes", "y"}


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass-a", required=True, help="CSV for pass A")
    parser.add_argument("--pass-b", required=True, help="CSV for pass B")
    parser.add_argument("--output", help="Optional JSON summary path")
    parser.add_argument("--review-output", help="Optional CSV path with per-item recommendations")
    args = parser.parse_args(argv)

    pass_a = index_by_item(load_rows(Path(args.pass_a)))
    pass_b = index_by_item(load_rows(Path(args.pass_b)))

    missing_in_b = sorted(set(pass_a) - set(pass_b))
    missing_in_a = sorted(set(pass_b) - set(pass_a))
    item_ids = sorted(set(pass_a) & set(pass_b))

    task_agreements = {field: 0 for field in TASK_FIELDS}
    fully_consistent = 0
    review_rows: List[Dict[str, str]] = []

    for item_id in item_ids:
        row_a = pass_a[item_id]
        row_b = pass_b[item_id]
        agreements = {field: label(row_a, field) == label(row_b, field) and label(row_a, field) != "" for field in TASK_FIELDS}
        for field, agreed in agreements.items():
            if agreed:
                task_agreements[field] += 1
        all_consistent = all(agreements.values())
        if all_consistent:
            fully_consistent += 1

        needs_revision = bool_flag(row_a, "needs_revision") or bool_flag(row_b, "needs_revision")
        recommendation = "ready_for_second_annotator" if all_consistent and not needs_revision else "revise_or_drop"
        review_rows.append(
            {
                "item_id": item_id,
                "pass_a_task_a": label(row_a, "task_a_label"),
                "pass_b_task_a": label(row_b, "task_a_label"),
                "pass_a_task_b": label(row_a, "task_b_label"),
                "pass_b_task_b": label(row_b, "task_b_label"),
                "pass_a_task_c": label(row_a, "task_c_label"),
                "pass_b_task_c": label(row_b, "task_c_label"),
                "pass_a_needs_revision": row_a.get("needs_revision", ""),
                "pass_b_needs_revision": row_b.get("needs_revision", ""),
                "all_tasks_consistent": "yes" if all_consistent else "no",
                "recommendation": recommendation,
            }
        )

    n_items = len(item_ids)
    summary = {
        "n_compared_items": n_items,
        "missing_in_pass_a": missing_in_a,
        "missing_in_pass_b": missing_in_b,
        "task_agreement_rate": {
            field: round(task_agreements[field] / n_items, 4) if n_items else None
            for field in TASK_FIELDS
        },
        "all_task_agreement_rate": round(fully_consistent / n_items, 4) if n_items else None,
        "self_disagreement_rate": round((n_items - fully_consistent) / n_items, 4) if n_items else None,
        "recommendation_counts": {
            "ready_for_second_annotator": sum(
                1 for row in review_rows if row["recommendation"] == "ready_for_second_annotator"
            ),
            "revise_or_drop": sum(1 for row in review_rows if row["recommendation"] == "revise_or_drop"),
        },
    }

    print(f"n_compared_items={summary['n_compared_items']}")
    print(f"all_task_agreement_rate={summary['all_task_agreement_rate']}")
    print(f"self_disagreement_rate={summary['self_disagreement_rate']}")
    print(f"recommendation_counts={summary['recommendation_counts']}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nWrote consistency summary to {output_path}")

    if args.review_output:
        output_path = Path(args.review_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(review_rows[0].keys()) if review_rows else [])
            if review_rows:
                writer.writeheader()
                writer.writerows(review_rows)
        print(f"Wrote review recommendations to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
