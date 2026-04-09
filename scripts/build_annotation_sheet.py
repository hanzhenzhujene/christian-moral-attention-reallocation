#!/usr/bin/env python3
"""Build a CSV annotation sheet from benchmark JSON items."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


BASE_COLUMNS = [
    "item_id",
    "benchmark_source",
    "pair_type",
    "primary_diagnostic_dimension",
    "domain",
    "difficulty",
    "case_a_text",
    "case_b_text",
]
ANNOTATION_COLUMNS = [
    "annotator_id",
    "task_a_label",
    "task_b_label",
    "task_c_label",
    "note",
    "confidence",
    "needs_revision",
]
GOLD_COLUMNS = [
    "gold_task_a",
    "gold_task_b",
    "gold_task_c",
    "gold_note",
]


def load_items(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"{path}: expected a JSON object or array")


def load_all_items(paths: Iterable[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw_path in paths:
        items.extend(load_items(Path(raw_path)))
    return items


def row_for_item(item: Dict[str, Any], annotator_id: str, include_gold: bool) -> Dict[str, str]:
    row = {
        "item_id": item["item_id"],
        "benchmark_source": item["benchmark_source"],
        "pair_type": item["pair_type"],
        "primary_diagnostic_dimension": item["primary_diagnostic_dimension"],
        "domain": item["domain"],
        "difficulty": item["difficulty"],
        "case_a_text": item["case_a"]["text"],
        "case_b_text": item["case_b"]["text"],
        "annotator_id": annotator_id,
        "task_a_label": "",
        "task_b_label": "",
        "task_c_label": "",
        "note": "",
        "confidence": "",
        "needs_revision": "",
    }
    if include_gold:
        row.update(
            {
                "gold_task_a": item["gold"]["task_a_more_morally_problematic"],
                "gold_task_b": item["gold"]["task_b_worse_inward_orientation"],
                "gold_task_c": item["gold"]["task_c_primary_reason"],
                "gold_note": item["gold"]["adjudication_note"],
            }
        )
    return row


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", nargs="+", required=True, help="Benchmark JSON files to include")
    parser.add_argument("--output", required=True, help="Destination CSV path")
    parser.add_argument(
        "--annotators",
        nargs="+",
        default=["annotator_1", "annotator_2"],
        help="Annotator ids to expand across the sheet",
    )
    parser.add_argument(
        "--include-gold",
        action="store_true",
        help="Include gold labels for adjudication-oriented sheets",
    )
    parser.add_argument(
        "--shuffle-seed",
        type=int,
        help="Optional deterministic shuffle for row order",
    )
    args = parser.parse_args(argv)

    items = load_all_items(args.items)
    columns = BASE_COLUMNS + ANNOTATION_COLUMNS + (GOLD_COLUMNS if args.include_gold else [])
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        row_for_item(item, annotator_id, args.include_gold)
        for item in items
        for annotator_id in args.annotators
    ]
    if args.shuffle_seed is not None:
        rng = random.Random(args.shuffle_seed)
        rng.shuffle(rows)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote annotation sheet with {len(items) * len(args.annotators)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
