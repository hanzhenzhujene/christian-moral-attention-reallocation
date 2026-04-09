#!/usr/bin/env python3
"""Summarize multi-pass Task B diagnostic traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def group_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row["model"], row["condition"])


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def is_same_heart_control(row: Dict[str, Any]) -> bool:
    return row["gold"]["task_b_worse_inward_orientation"] == "Same"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Trace JSONL files")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args(argv)

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for raw_path in args.input:
        for row in load_jsonl(Path(raw_path)):
            grouped[group_key(row)].append(row)

    summaries: List[Dict[str, Any]] = []
    for (model, condition), rows in sorted(grouped.items()):
        gate_counts = Counter(row["gate_source"] for row in rows)
        exact_match_correct = sum(
            1
            for row in rows
            if (row["copy_exact_match"] and row["expected_relation"] == "same")
            or ((not row["copy_exact_match"]) and row["expected_relation"] == "different")
        )
        relation_rows = [row for row in rows if row["relation_response"] is not None]
        relation_correct = sum(1 for row in relation_rows if row["relation_response"] == row["expected_relation"])
        control_rows = [row for row in rows if is_same_heart_control(row)]
        control_exact_match = sum(1 for row in control_rows if row["copy_exact_match"])
        control_final_same = sum(
            1 for row in control_rows if row["final_response"]["task_b_worse_inward_orientation"] == "Same"
        )
        motive_rows = [row for row in rows if not is_same_heart_control(row)]
        motive_final_correct = sum(
            1
            for row in motive_rows
            if row["final_response"]["task_b_worse_inward_orientation"] == row["gold"]["task_b_worse_inward_orientation"]
        )
        summaries.append(
            {
                "model": model,
                "condition": condition,
                "n_items": len(rows),
                "copy_exact_match_relation_accuracy": safe_ratio(exact_match_correct, len(rows)),
                "relation_pass_accuracy": safe_ratio(relation_correct, len(relation_rows)),
                "control_copy_exact_match_rate": safe_ratio(control_exact_match, len(control_rows)),
                "control_final_same_rate": safe_ratio(control_final_same, len(control_rows)),
                "motive_final_task_b_accuracy": safe_ratio(motive_final_correct, len(motive_rows)),
                "gate_source_distribution": {
                    key: round(value / len(rows), 4) for key, value in sorted(gate_counts.items())
                },
            }
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"summaries": summaries}, indent=2), encoding="utf-8")
    for row in summaries:
        print(
            f"{row['model']} | {row['condition']} | "
            f"copy_relation_acc={row['copy_exact_match_relation_accuracy']} | "
            f"relation_acc={row['relation_pass_accuracy']} | "
            f"control_same={row['control_final_same_rate']} | "
            f"motive_task_b_acc={row['motive_final_task_b_accuracy']}"
        )
    print(f"Wrote multipass trace summary to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
