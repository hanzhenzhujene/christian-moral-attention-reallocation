#!/usr/bin/env python3
"""Select representative pilot examples for manual qualitative review."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import evaluate_runs


CATEGORY_PRIORITY = {
    "parse_failure": 100,
    "relation_inconsistency": 95,
    "heart_overreach": 90,
    "missed_heart_sensitivity": 80,
    "cross_task_inconsistency": 70,
    "reason_misfocus": 60,
    "verbosity_outlier": 50,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def benchmark_by_id(path: Path) -> Dict[str, Dict[str, Any]]:
    items = load_json(path)
    return {item["item_id"]: item for item in items}


def shared_metadata(record: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": record["job_id"],
        "item_id": record["item_id"],
        "model": record["model"],
        "condition": record["condition"],
        "benchmark_source": record["benchmark_source"],
        "pair_type": record["pair_type"],
        "primary_diagnostic_dimension": record["primary_diagnostic_dimension"],
        "domain": item.get("domain"),
        "swapped": record.get("swapped"),
        "case_a_text": item["case_a"]["text"],
        "case_b_text": item["case_b"]["text"],
        "gold": record["gold"],
    }


def record_categories(record: Dict[str, Any]) -> List[str]:
    categories: List[str] = []
    response = record["response"]
    gold = record["gold"]

    relation = response.get("task_b_written_motive_relation")
    if relation == "same" and response["task_b_worse_inward_orientation"] != "Same":
        categories.append("relation_inconsistency")
    if relation == "different" and response["task_b_worse_inward_orientation"] == "Same":
        categories.append("relation_inconsistency")
    if gold["task_b_worse_inward_orientation"] == "Same" and response["task_b_worse_inward_orientation"] != "Same":
        categories.append("heart_overreach")
    if evaluate_runs.is_motive_item(record) and (
        response["task_b_worse_inward_orientation"] != gold["task_b_worse_inward_orientation"]
    ):
        categories.append("missed_heart_sensitivity")
    if response["task_a_more_morally_problematic"] != response["task_b_worse_inward_orientation"]:
        categories.append("cross_task_inconsistency")
    if gold["task_c_primary_reason"] == "motive" and response["task_c_primary_reason"] != "motive":
        categories.append("reason_misfocus")
    return categories


def choose_primary_category(categories: Sequence[str]) -> str:
    if not categories:
        return "verbosity_outlier"
    return sorted(categories, key=lambda category: CATEGORY_PRIORITY[category], reverse=True)[0]


def build_success_examples(
    records: Sequence[Dict[str, Any]],
    items_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    explanation_lengths = [len(record["response"]["brief_explanation"]) for record in records]
    mean_explanation_length = mean(explanation_lengths)

    examples: List[Dict[str, Any]] = []
    for record in records:
        item = items_by_id[record["item_id"]]
        categories = record_categories(record)
        explanation_length = len(record["response"]["brief_explanation"])
        if explanation_length >= mean_explanation_length * 1.8:
            categories.append("verbosity_outlier")
        if not categories:
            continue
        example = shared_metadata(record, item)
        example.update(
            {
                "source": "run_record",
                "primary_category": choose_primary_category(categories),
                "all_categories": sorted(
                    set(categories),
                    key=lambda category: CATEGORY_PRIORITY[category],
                    reverse=True,
                ),
                "response": record["response"],
                "explanation_length": explanation_length,
                "adjudication_note": record["gold"].get("adjudication_note"),
                "score": max(CATEGORY_PRIORITY[category] for category in categories) + len(set(categories)) * 2,
            }
        )
        examples.append(example)
    return examples


def build_failure_examples(
    failures: Sequence[Dict[str, Any]],
    items_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for record in failures:
        item = items_by_id.get(record["item_id"])
        if item is None:
            continue
        example = {
            "job_id": record["job_id"],
            "item_id": record["item_id"],
            "model": record["model"],
            "condition": record["condition"],
            "benchmark_source": item.get("benchmark_source"),
            "pair_type": item.get("pair_type"),
            "primary_diagnostic_dimension": item.get("primary_diagnostic_dimension"),
            "domain": item.get("domain"),
            "swapped": None,
            "case_a_text": item["case_a"]["text"],
            "case_b_text": item["case_b"]["text"],
            "gold": item["gold"],
            "source": "failure_record",
            "primary_category": "parse_failure",
            "all_categories": ["parse_failure"],
            "response": None,
            "explanation_length": None,
            "adjudication_note": item["gold"].get("adjudication_note"),
            "error": record.get("error"),
            "raw_outputs": record.get("raw_outputs", []),
            "score": CATEGORY_PRIORITY["parse_failure"],
        }
        examples.append(example)
    return examples


def select_examples(
    candidates: Sequence[Dict[str, Any]],
    max_examples: int,
    max_per_category: int,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = defaultdict(int)
    seen_job_keys: set[Tuple[str, str]] = set()
    seen_item_condition_pairs: set[Tuple[str, str, str]] = set()

    ranked_candidates = sorted(
        candidates,
        key=lambda item: (
            -item["score"],
            item["model"],
            item["condition"],
            item["item_id"],
        ),
    )

    for example in ranked_candidates:
        if len(selected) >= max_examples:
            break
        category = example["primary_category"]
        if category_counts[category] >= max_per_category:
            continue
        job_key = (example["model"], example["job_id"])
        if job_key in seen_job_keys:
            continue
        pair_key = (example["model"], example["item_id"], example["condition"])
        if pair_key in seen_item_condition_pairs and category != "parse_failure":
            continue
        selected.append(example)
        category_counts[category] += 1
        seen_job_keys.add(job_key)
        seen_item_condition_pairs.add(pair_key)

    if len(selected) < max_examples:
        for example in ranked_candidates:
            if len(selected) >= max_examples:
                break
            job_key = (example["model"], example["job_id"])
            if job_key in seen_job_keys:
                continue
            selected.append(example)
            seen_job_keys.add(job_key)

    return selected


def format_gold_or_response(payload: Dict[str, Any] | None) -> str:
    if not payload:
        return "n/a"
    return (
        f"Task A={payload['task_a_more_morally_problematic']}; "
        f"Task B={payload['task_b_worse_inward_orientation']}; "
        f"Task C={payload['task_c_primary_reason']}"
    )


def render_markdown(examples: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = [
        "# Pilot Qualitative Review",
        "",
        f"Selected examples: {len(examples)}",
        "",
    ]
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for example in examples:
        grouped[example["primary_category"]].append(example)

    for category in sorted(grouped, key=lambda name: CATEGORY_PRIORITY[name], reverse=True):
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        for index, example in enumerate(grouped[category], start=1):
            lines.append(
                f"### {index}. {example['job_id']} | {example['model']} | {example['condition']} | "
                f"{example['benchmark_source']} | {example['pair_type']}"
            )
            lines.append("")
            lines.append(f"- Item: {example['item_id']}")
            lines.append(f"- Domain: {example.get('domain')}")
            lines.append(f"- Categories: {', '.join(example['all_categories'])}")
            if example.get("error"):
                lines.append(f"- Error: {example['error']}")
            relation = example.get("response", {}).get("task_b_written_motive_relation") if example.get("response") else None
            if relation is not None:
                lines.append(f"- Task B written-motive relation: {relation}")
            if example.get("explanation_length") is not None:
                lines.append(f"- Explanation length: {example['explanation_length']}")
            lines.append(f"- Gold: {format_gold_or_response(example['gold'])}")
            lines.append(f"- Response: {format_gold_or_response(example['response'])}")
            lines.append(f"- Case A: {example['case_a_text']}")
            lines.append(f"- Case B: {example['case_b_text']}")
            lines.append(f"- Adjudication note: {example.get('adjudication_note') or 'n/a'}")
            if example.get("response"):
                lines.append(f"- Explanation: {example['response']['brief_explanation']}")
            raw_outputs = example.get("raw_outputs") or []
            if raw_outputs:
                lines.append(f"- Raw output sample: {raw_outputs[0][:400]}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, help="Benchmark JSON used for the pilot")
    parser.add_argument("--runs", nargs="+", required=True, help="Run-record JSONL files")
    parser.add_argument("--failures", nargs="*", default=[], help="Failure JSONL files")
    parser.add_argument("--max-examples", type=int, default=15, help="Maximum examples to select")
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=4,
        help="Soft cap on primary examples per category before backfilling",
    )
    parser.add_argument("--output-json", required=True, help="Selected examples JSON path")
    parser.add_argument("--output-md", required=True, help="Markdown review path")
    return parser


def main(argv: Sequence[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    items_by_id = benchmark_by_id(Path(args.benchmark))
    records: List[Dict[str, Any]] = []
    for raw_path in args.runs:
        records.extend(load_jsonl(Path(raw_path)))

    failure_rows: List[Dict[str, Any]] = []
    for raw_path in args.failures:
        failure_rows.extend(load_jsonl(Path(raw_path)))

    candidates = [
        *build_failure_examples(failure_rows, items_by_id),
        *build_success_examples(records, items_by_id),
    ]
    selected = select_examples(candidates, args.max_examples, args.max_per_category)

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(selected, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(render_markdown(selected), encoding="utf-8")

    print(f"Selected {len(selected)} qualitative review examples")
    print(f"Wrote JSON review set to {output_json}")
    print(f"Wrote markdown review set to {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
