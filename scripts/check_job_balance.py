#!/usr/bin/env python3
"""Check A/B swapping and presented gold-label balance for a job file."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def ratio(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(count / total, 4)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Job JSONL file")
    parser.add_argument("--max-a-b-gap", type=float, default=0.2, help="Max allowed |A-B| proportion gap")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    rows = load_jsonl(Path(args.input))
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)

    report: List[Dict[str, Any]] = []
    failures: List[str] = []
    for condition, condition_rows in sorted(grouped.items()):
        n_rows = len(condition_rows)
        swapped_counter = Counter(bool(row.get("swapped")) for row in condition_rows)
        task_a_counter = Counter(row["gold"]["task_a_more_morally_problematic"] for row in condition_rows)
        task_b_counter = Counter(row["gold"]["task_b_worse_inward_orientation"] for row in condition_rows)
        a_count = task_a_counter.get("A", 0)
        b_count = task_a_counter.get("B", 0)
        gap = abs(a_count - b_count) / n_rows if n_rows else 0.0
        if gap > args.max_a_b_gap:
            failures.append(
                f"{condition}: presented Task A gold imbalance {gap:.4f} exceeds threshold {args.max_a_b_gap:.4f}"
            )
        item = {
            "condition": condition,
            "n_jobs": n_rows,
            "swapped_false": swapped_counter.get(False, 0),
            "swapped_true": swapped_counter.get(True, 0),
            "swap_rate_true": ratio(swapped_counter.get(True, 0), n_rows),
            "task_a_gold_presented": dict(sorted(task_a_counter.items())),
            "task_b_gold_presented": dict(sorted(task_b_counter.items())),
            "task_a_presented_a_b_gap": round(gap, 4),
        }
        report.append(item)
        print(
            f"{condition} | n={n_rows} | swap_true={item['swap_rate_true']} | "
            f"task_a_gap={item['task_a_presented_a_b_gap']}"
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote balance report to {output_path}")

    if failures:
        print("\nBalance failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
