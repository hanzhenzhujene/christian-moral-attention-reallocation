#!/usr/bin/env python3
"""Inspect run-level bias patterns such as A/B preference and swapped-order effects."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


AB_SAME = {"A", "B", "Same"}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def rate(counter: Counter, total: int) -> Dict[str, float]:
    return {key: round(counter[key] / total, 4) for key in sorted(counter)} if total else {}


def answer_distribution(rows: Sequence[Dict[str, Any]], field: str) -> Dict[str, float]:
    counter = Counter(row["response"][field] for row in rows if row["response"][field] in AB_SAME)
    return rate(counter, len(rows))


def gold_distribution(rows: Sequence[Dict[str, Any]], field: str) -> Dict[str, float]:
    counter = Counter(row["gold"][field] for row in rows if row["gold"][field] in AB_SAME)
    return rate(counter, len(rows))


def reason_distribution(rows: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    counter = Counter(row["response"]["task_c_primary_reason"] for row in rows)
    return rate(counter, len(rows))


def accuracy(rows: Sequence[Dict[str, Any]], response_field: str, gold_field: str) -> float | None:
    if not rows:
        return None
    return round(
        sum(1 for row in rows if row["response"][response_field] == row["gold"][gold_field]) / len(rows),
        4,
    )


def group_key(record: Dict[str, Any]) -> Tuple[str, str]:
    return (record.get("model", "unknown_model"), record["condition"])


def diagnostics_for_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    swapped_true = [row for row in rows if row.get("swapped") is True]
    swapped_false = [row for row in rows if row.get("swapped") is False]
    task_a_answers = answer_distribution(rows, "task_a_more_morally_problematic")
    task_b_answers = answer_distribution(rows, "task_b_worse_inward_orientation")
    task_a_gold = gold_distribution(rows, "task_a_more_morally_problematic")
    task_b_gold = gold_distribution(rows, "task_b_worse_inward_orientation")
    relation_rows = [
        row for row in rows if isinstance(row["response"].get("task_b_written_motive_relation"), str)
    ]
    relation_distribution = (
        rate(
            Counter(row["response"]["task_b_written_motive_relation"] for row in relation_rows),
            len(relation_rows),
        )
        if relation_rows
        else {}
    )
    relation_consistency = None
    if relation_rows:
        consistent = 0
        for row in relation_rows:
            relation = row["response"]["task_b_written_motive_relation"]
            answer = row["response"]["task_b_worse_inward_orientation"]
            if relation == "same" and answer == "Same":
                consistent += 1
            elif relation == "different" and answer in {"A", "B"}:
                consistent += 1
        relation_consistency = round(consistent / len(relation_rows), 4)
    return {
        "n_items": len(rows),
        "task_a_answer_distribution": task_a_answers,
        "task_b_answer_distribution": task_b_answers,
        "task_a_gold_distribution": task_a_gold,
        "task_b_gold_distribution": task_b_gold,
        "task_b_written_motive_relation_distribution": relation_distribution,
        "task_b_relation_consistency_rate": relation_consistency,
        "task_a_excess_a_rate": round(task_a_answers.get("A", 0.0) - task_a_gold.get("A", 0.0), 4),
        "task_b_excess_a_rate": round(task_b_answers.get("A", 0.0) - task_b_gold.get("A", 0.0), 4),
        "reason_distribution": reason_distribution(rows),
        "task_a_accuracy_swapped_false": accuracy(
            swapped_false, "task_a_more_morally_problematic", "task_a_more_morally_problematic"
        ),
        "task_a_accuracy_swapped_true": accuracy(
            swapped_true, "task_a_more_morally_problematic", "task_a_more_morally_problematic"
        ),
        "task_b_accuracy_swapped_false": accuracy(
            swapped_false, "task_b_worse_inward_orientation", "task_b_worse_inward_orientation"
        ),
        "task_b_accuracy_swapped_true": accuracy(
            swapped_true, "task_b_worse_inward_orientation", "task_b_worse_inward_orientation"
        ),
        "task_a_select_a_rate_swapped_false": answer_distribution(
            swapped_false, "task_a_more_morally_problematic"
        ).get("A"),
        "task_a_select_a_rate_swapped_true": answer_distribution(
            swapped_true, "task_a_more_morally_problematic"
        ).get("A"),
        "task_b_select_a_rate_swapped_false": answer_distribution(
            swapped_false, "task_b_worse_inward_orientation"
        ).get("A"),
        "task_b_select_a_rate_swapped_true": answer_distribution(
            swapped_true, "task_b_worse_inward_orientation"
        ).get("A"),
        "same_rate_task_a": task_a_answers.get("Same", 0.0),
        "same_rate_task_b": task_b_answers.get("Same", 0.0),
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Run record JSONL files")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    records: List[Dict[str, Any]] = []
    for raw_path in args.input:
        records.extend(load_jsonl(Path(raw_path)))

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[group_key(record)].append(record)

    report: List[Dict[str, Any]] = []
    for (model, condition), rows in sorted(grouped.items()):
        item = {"model": model, "condition": condition}
        item.update(diagnostics_for_rows(rows))
        report.append(item)
        print(
            f"{model} | {condition} | n={item['n_items']} | "
            f"task_a_excess_A={item['task_a_excess_a_rate']} | "
            f"task_b_excess_A={item['task_b_excess_a_rate']} | "
            f"same_a={item['same_rate_task_a']} | same_b={item['same_rate_task_b']}"
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote diagnostics to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
