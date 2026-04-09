#!/usr/bin/env python3
"""Compile a curated Moral Stories CSV into benchmark JSON items."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence


YES_VALUES = {"yes", "y", "true", "1"}


def truthy(value: str) -> bool:
    return value.strip().lower() in YES_VALUES


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def compile_row(row: Dict[str, str]) -> Dict[str, object]:
    metadata = {
        "author": row["author"],
        "review_status": row["review_status"],
        "tags": [
            "moralstories",
            row["domain"],
            row["pair_type"],
            row["primary_diagnostic_dimension"],
            row.get("benchmark_role", "").strip(),
            row.get("study_split", "").strip(),
        ],
        "mvp_candidate": truthy(row.get("include_in_mvp", "")),
    }
    metadata["tags"] = [tag for tag in metadata["tags"] if tag]
    for key in (
        "source_story_id",
        "source_split",
        "benchmark_role",
        "study_split",
        "held_constant",
        "changed_dimension",
        "notes",
    ):
        value = row.get(key, "").strip()
        if value:
            metadata[key] = value

    return {
        "item_id": row["item_id"],
        "benchmark_source": "MoralStories",
        "pair_type": row["pair_type"],
        "primary_diagnostic_dimension": row["primary_diagnostic_dimension"],
        "domain": row["domain"],
        "difficulty": row["difficulty"],
        "case_a": {
            "text": row["case_a_text"],
            "outward_act_summary": row["case_a_outward_act_summary"],
            "motive_summary": row["case_a_motive_summary"],
            "consequence_summary": row["case_a_consequence_summary"],
            "rule_summary": row["case_a_rule_summary"],
        },
        "case_b": {
            "text": row["case_b_text"],
            "outward_act_summary": row["case_b_outward_act_summary"],
            "motive_summary": row["case_b_motive_summary"],
            "consequence_summary": row["case_b_consequence_summary"],
            "rule_summary": row["case_b_rule_summary"],
        },
        "gold": {
            "task_a_more_morally_problematic": row["gold_task_a"],
            "task_b_worse_inward_orientation": row["gold_task_b"],
            "task_c_primary_reason": row["gold_task_c"],
            "adjudication_note": row["adjudication_note"],
        },
        "metadata": metadata,
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Curated Moral Stories CSV")
    parser.add_argument("--output", required=True, help="Output benchmark JSON path")
    parser.add_argument(
        "--only-included",
        action="store_true",
        help="Compile only rows marked include_in_mvp=yes",
    )
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.input))
    if args.only_included:
        rows = [row for row in rows if truthy(row.get("include_in_mvp", ""))]

    items = [compile_row(row) for row in rows]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} items to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
