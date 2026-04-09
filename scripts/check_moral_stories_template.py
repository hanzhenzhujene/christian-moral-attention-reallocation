#!/usr/bin/env python3
"""Validate and summarize a curated Moral Stories CSV sheet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence


REQUIRED_COLUMNS = [
    "item_id",
    "source_story_id",
    "source_split",
    "domain",
    "difficulty",
    "original_norm",
    "situation",
    "intention",
    "action",
    "consequence",
    "pair_type",
    "primary_diagnostic_dimension",
    "case_a_text",
    "case_b_text",
    "case_a_outward_act_summary",
    "case_b_outward_act_summary",
    "case_a_motive_summary",
    "case_b_motive_summary",
    "case_a_consequence_summary",
    "case_b_consequence_summary",
    "case_a_rule_summary",
    "case_b_rule_summary",
    "gold_task_a",
    "gold_task_b",
    "gold_task_c",
    "adjudication_note",
    "benchmark_role",
    "study_split",
    "held_constant",
    "changed_dimension",
    "include_in_mvp",
    "author",
    "review_status",
    "notes",
]
DOMAINS = {
    "workplace",
    "family",
    "friendship",
    "school",
    "church",
    "community",
    "online",
    "caregiving",
    "public_life",
    "other",
}
DIFFICULTIES = {"easy", "medium", "hard"}
PAIR_TYPES = {
    "same_act_different_motive",
    "same_norm_different_heart",
    "same_consequence_different_motive",
    "same_motive_different_consequence",
    "same_intention_moral_vs_immoral_action",
    "outwardly_harsh_benevolent_vs_malicious",
    "outwardly_good_vain_vs_loving",
    "outwardly_compliant_resentful_vs_cheerful",
    "custom",
}
PRIMARY_DIMENSIONS = {"motive", "outward_act", "consequence", "rule", "mixed"}
AB_SAME = {"A", "B", "Same"}
REASON_LABELS = {"outward_act", "motive", "consequence", "rule"}
REVIEW_STATUSES = {"draft", "reviewed", "approved"}
BENCHMARK_ROLES = {"motive_main", "same_heart_control"}
STUDY_SPLITS = {"main", "pilot_holdout", "candidate", "exploratory"}
YES_VALUES = {"yes", "y", "true", "1"}
NO_VALUES = {"no", "n", "false", "0", ""}


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing required columns: {missing}")
        return list(reader)


def truthy(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in YES_VALUES:
        return True
    if normalized in NO_VALUES:
        return False
    raise ValueError(f"Invalid include_in_mvp value: '{value}'")


def check_rows(rows: Sequence[Dict[str, str]]) -> Dict[str, object]:
    errors: List[str] = []
    included_rows: List[Dict[str, str]] = []
    seen_ids = set()

    for index, row in enumerate(rows, start=2):
        item_id = row["item_id"].strip()
        if not item_id:
            errors.append(f"row {index}: item_id is required")
            continue
        if item_id in seen_ids:
            errors.append(f"row {index}: duplicate item_id '{item_id}'")
        seen_ids.add(item_id)

        for field in (
            "domain",
            "difficulty",
            "pair_type",
            "primary_diagnostic_dimension",
            "gold_task_a",
            "gold_task_b",
            "gold_task_c",
            "benchmark_role",
            "study_split",
            "review_status",
        ):
            if not row[field].strip():
                errors.append(f"row {index}: {field} is required")

        if row["domain"] not in DOMAINS:
            errors.append(f"row {index}: invalid domain '{row['domain']}'")
        if row["difficulty"] not in DIFFICULTIES:
            errors.append(f"row {index}: invalid difficulty '{row['difficulty']}'")
        if row["pair_type"] not in PAIR_TYPES:
            errors.append(f"row {index}: invalid pair_type '{row['pair_type']}'")
        if row["primary_diagnostic_dimension"] not in PRIMARY_DIMENSIONS:
            errors.append(
                f"row {index}: invalid primary_diagnostic_dimension '{row['primary_diagnostic_dimension']}'"
            )
        if row["gold_task_a"] not in AB_SAME:
            errors.append(f"row {index}: invalid gold_task_a '{row['gold_task_a']}'")
        if row["gold_task_b"] not in AB_SAME:
            errors.append(f"row {index}: invalid gold_task_b '{row['gold_task_b']}'")
        if row["gold_task_c"] not in REASON_LABELS:
            errors.append(f"row {index}: invalid gold_task_c '{row['gold_task_c']}'")
        if row["benchmark_role"] not in BENCHMARK_ROLES:
            errors.append(f"row {index}: invalid benchmark_role '{row['benchmark_role']}'")
        if row["study_split"] not in STUDY_SPLITS:
            errors.append(f"row {index}: invalid study_split '{row['study_split']}'")
        if row["review_status"] not in REVIEW_STATUSES:
            errors.append(f"row {index}: invalid review_status '{row['review_status']}'")

        for text_field in (
            "source_story_id",
            "original_norm",
            "situation",
            "intention",
            "action",
            "consequence",
            "case_a_text",
            "case_b_text",
            "case_a_outward_act_summary",
            "case_b_outward_act_summary",
            "case_a_motive_summary",
            "case_b_motive_summary",
            "adjudication_note",
            "held_constant",
            "changed_dimension",
            "author",
        ):
            if not row[text_field].strip():
                errors.append(f"row {index}: {text_field} is required")

        if row["benchmark_role"] == "same_heart_control":
            if row["pair_type"] != "same_intention_moral_vs_immoral_action":
                errors.append(
                    f"row {index}: same_heart_control rows must use pair_type 'same_intention_moral_vs_immoral_action'"
                )
            if row["gold_task_b"] != "Same":
                errors.append(f"row {index}: same_heart_control rows must set gold_task_b to 'Same'")
            if row["gold_task_c"] == "motive":
                errors.append(f"row {index}: same_heart_control rows must not set gold_task_c to 'motive'")

        if row["benchmark_role"] == "motive_main":
            if row["primary_diagnostic_dimension"] != "motive":
                errors.append(f"row {index}: motive_main rows must set primary_diagnostic_dimension to 'motive'")
            if row["gold_task_b"] == "Same":
                errors.append(f"row {index}: motive_main rows should not set gold_task_b to 'Same'")

        try:
            include = truthy(row["include_in_mvp"])
        except ValueError as exc:
            errors.append(f"row {index}: {exc}")
            include = False

        if include:
            included_rows.append(row)

    def distribution(field: str, subset: Sequence[Dict[str, str]]) -> Dict[str, int]:
        return dict(sorted(Counter(row[field] for row in subset).items()))

    summary = {
        "n_rows": len(rows),
        "n_included": len(included_rows),
        "all_rows": {
            "domain": distribution("domain", rows),
            "difficulty": distribution("difficulty", rows),
            "pair_type": distribution("pair_type", rows),
            "primary_diagnostic_dimension": distribution("primary_diagnostic_dimension", rows),
            "benchmark_role": distribution("benchmark_role", rows),
            "study_split": distribution("study_split", rows),
            "gold_task_a": distribution("gold_task_a", rows),
            "gold_task_b": distribution("gold_task_b", rows),
            "gold_task_c": distribution("gold_task_c", rows),
            "review_status": distribution("review_status", rows),
        },
        "included_rows": {
            "domain": distribution("domain", included_rows),
            "difficulty": distribution("difficulty", included_rows),
            "pair_type": distribution("pair_type", included_rows),
            "primary_diagnostic_dimension": distribution("primary_diagnostic_dimension", included_rows),
            "benchmark_role": distribution("benchmark_role", included_rows),
            "study_split": distribution("study_split", included_rows),
            "gold_task_a": distribution("gold_task_a", included_rows),
            "gold_task_b": distribution("gold_task_b", included_rows),
            "gold_task_c": distribution("gold_task_c", included_rows),
            "review_status": distribution("review_status", included_rows),
        },
    }
    return {"errors": errors, "summary": summary}


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Curated Moral Stories CSV")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.input))
    report = check_rows(rows)

    print(f"rows={report['summary']['n_rows']}")
    print(f"included={report['summary']['n_included']}")
    for bucket in ("all_rows", "included_rows"):
        print(bucket + ":")
        for field in (
            "domain",
            "difficulty",
            "pair_type",
            "primary_diagnostic_dimension",
            "benchmark_role",
            "study_split",
            "gold_task_a",
            "gold_task_b",
            "gold_task_c",
            "review_status",
        ):
            values = ", ".join(f"{k}={v}" for k, v in report["summary"][bucket][field].items())
            print(f"  {field}: {values}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote report to {output_path}")

    if report["errors"]:
        print("\nErrors:")
        for error in report["errors"]:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
