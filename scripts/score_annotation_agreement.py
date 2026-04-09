#!/usr/bin/env python3
"""Compute pairwise annotation agreement from a CSV annotation sheet."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


TASK_FIELDS = ["task_a_label", "task_b_label", "task_c_label"]


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float | None:
    if not labels_a or not labels_b or len(labels_a) != len(labels_b):
        return None
    n = len(labels_a)
    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    categories = sorted(set(labels_a) | set(labels_b))
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[c] / n) * (counts_b[c] / n) for c in categories)
    if math.isclose(1.0 - expected, 0.0):
        return None
    return round((observed - expected) / (1.0 - expected), 4)


def pairwise_task_agreement(rows: Sequence[Dict[str, str]], field: str) -> Tuple[List[Dict[str, object]], List[Dict[str, str]]]:
    by_item: Dict[str, Dict[str, str]] = defaultdict(dict)
    for row in rows:
        item_id = row.get("item_id", "").strip()
        annotator_id = row.get("annotator_id", "").strip()
        label = row.get(field, "").strip()
        if item_id and annotator_id and label:
            by_item[item_id][annotator_id] = label

    annotators = sorted({row.get("annotator_id", "").strip() for row in rows if row.get("annotator_id", "").strip()})
    summaries: List[Dict[str, object]] = []
    disagreements: List[Dict[str, str]] = []

    for left, right in combinations(annotators, 2):
        paired: List[Tuple[str, str, str]] = []
        for item_id, labels in by_item.items():
            if left in labels and right in labels:
                paired.append((item_id, labels[left], labels[right]))

        n_items = len(paired)
        if n_items == 0:
            summaries.append(
                {
                    "field": field,
                    "annotator_pair": [left, right],
                    "n_items": 0,
                    "percent_agreement": None,
                    "cohen_kappa": None,
                }
            )
            continue

        labels_a = [label_a for _, label_a, _ in paired]
        labels_b = [label_b for _, _, label_b in paired]
        agreements = sum(1 for _, a, b in paired if a == b)
        for item_id, a, b in paired:
            if a != b:
                disagreements.append(
                    {
                        "field": field,
                        "item_id": item_id,
                        "annotator_left": left,
                        "annotator_right": right,
                        "label_left": a,
                        "label_right": b,
                    }
                )

        summaries.append(
            {
                "field": field,
                "annotator_pair": [left, right],
                "n_items": n_items,
                "percent_agreement": round(agreements / n_items, 4),
                "cohen_kappa": cohen_kappa(labels_a, labels_b),
            }
        )

    return summaries, disagreements


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Annotation CSV path")
    parser.add_argument("--output", help="Optional JSON summary path")
    parser.add_argument("--disagreements-output", help="Optional CSV path for disagreements")
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.input))
    summary_rows: List[Dict[str, object]] = []
    disagreement_rows: List[Dict[str, str]] = []
    for field in TASK_FIELDS:
        summaries, disagreements = pairwise_task_agreement(rows, field)
        summary_rows.extend(summaries)
        disagreement_rows.extend(disagreements)

    for summary in summary_rows:
        print(
            f"{summary['field']} | "
            f"{summary['annotator_pair'][0]} vs {summary['annotator_pair'][1]} | "
            f"n={summary['n_items']} | "
            f"agreement={summary['percent_agreement']} | "
            f"kappa={summary['cohen_kappa']}"
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
        print(f"\nWrote agreement summary to {output_path}")

    if args.disagreements_output:
        output_path = Path(args.disagreements_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "field",
                    "item_id",
                    "annotator_left",
                    "annotator_right",
                    "label_left",
                    "label_right",
                ],
            )
            writer.writeheader()
            writer.writerows(disagreement_rows)
        print(f"Wrote disagreements to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
