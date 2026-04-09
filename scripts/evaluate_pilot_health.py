#!/usr/bin/env python3
"""Evaluate held-out pilot run health against paper-first thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import evaluate_runs
import run_diagnostics


def load_jobs(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean_explanation_chars(rows: Sequence[Dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return sum(len(row["response"]["brief_explanation"]) for row in rows) / len(rows)


def ratio(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline in (None, 0):
        return None
    return round(value / baseline, 4)


def group_key(record: Dict[str, Any]) -> Tuple[str, str]:
    return (record.get("model", "unknown_model"), record["condition"])


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Study config JSON")
    parser.add_argument("--jobs", required=True, help="Expected pilot job JSONL")
    parser.add_argument("--runs", nargs="+", required=True, help="Pilot run-record JSONL files")
    parser.add_argument(
        "--models",
        nargs="+",
        help="Optional model aliases to score. Use this when evaluating multiple models with overlapping job ids.",
    )
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    expected_jobs = load_jobs(Path(args.jobs))
    expected_job_ids = {row["job_id"] for row in expected_jobs}

    raw_records: List[Dict[str, Any]] = []
    invalid_records: List[str] = []
    for raw_path in args.runs:
        path = Path(raw_path)
        raw_records.extend(evaluate_runs.load_jsonl(path))

    if args.models:
        expected_models = list(dict.fromkeys(args.models))
    else:
        discovered_models = [record.get("model", "unknown_model") for record in raw_records]
        expected_models = list(dict.fromkeys(discovered_models or config.get("models", [])))
    expected_job_keys = {(model, job_id) for model in expected_models for job_id in expected_job_ids}

    valid_records: List[Dict[str, Any]] = []
    seen_job_keys: set[Tuple[str, str]] = set()
    for record in raw_records:
        model = record.get("model", "unknown_model")
        job_id = record.get("job_id")
        job_key = (model, job_id)
        if job_key in seen_job_keys:
            invalid_records.append(f"duplicate_job_key:{model}:{job_id}")
            continue
        seen_job_keys.add(job_key)
        if not evaluate_runs.validate_response(record.get("response")):
            invalid_records.append(f"invalid_response:{model}:{job_id}")
            continue
        valid_records.append(record)

    valid_job_keys = {(record.get("model", "unknown_model"), record["job_id"]) for record in valid_records}
    missing_job_keys = sorted(expected_job_keys - valid_job_keys)
    parse_failure_rate = (
        round((len(invalid_records) + len(missing_job_keys)) / len(expected_job_keys), 4)
        if expected_job_keys
        else 0.0
    )

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in valid_records:
        grouped[group_key(record)].append(record)

    diagnostics_by_group = {
        group_key: run_diagnostics.diagnostics_for_rows(rows) for group_key, rows in grouped.items()
    }
    summaries_by_group = {
        group_key: evaluate_runs.compute_summary(rows, bootstrap_samples=0, seed=7) for group_key, rows in grouped.items()
    }

    failures: List[str] = []
    thresholds = config["pilot_health_thresholds"]
    if parse_failure_rate > thresholds["max_parse_failure_rate"]:
        failures.append(
            f"parse_failure_rate {parse_failure_rate:.4f} exceeds threshold {thresholds['max_parse_failure_rate']:.4f}"
        )

    report_groups: List[Dict[str, Any]] = []
    by_model: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for (model, condition), rows in sorted(grouped.items()):
        summary = summaries_by_group[(model, condition)]
        diagnostics = diagnostics_by_group[(model, condition)]
        group_report = {
            "model": model,
            "condition": condition,
            "n_records": len(rows),
            "metrics": summary["metrics"],
            "diagnostics": diagnostics,
        }
        report_groups.append(group_report)
        by_model[model][condition] = group_report

    model_contrasts: List[Dict[str, Any]] = []
    for model, condition_map in sorted(by_model.items()):
        baseline = condition_map.get("baseline")
        christian = condition_map.get("christian_heart")
        if baseline:
            baseline_mean = baseline["metrics"]["mean_explanation_chars"]["point"]
            for condition_name, group_report in condition_map.items():
                explanation_ratio = ratio(group_report["metrics"]["mean_explanation_chars"]["point"], baseline_mean)
                group_report["explanation_ratio_vs_baseline"] = explanation_ratio
                if (
                    condition_name != "baseline"
                    and explanation_ratio is not None
                    and explanation_ratio > thresholds["max_explanation_ratio_vs_baseline"]
                ):
                    failures.append(
                        f"{model}/{condition_name}: explanation_ratio_vs_baseline {explanation_ratio:.4f} exceeds threshold {thresholds['max_explanation_ratio_vs_baseline']:.4f}"
                    )
                task_b_gap = None
                group_diagnostics = group_report["diagnostics"]
                if (
                    group_diagnostics["task_b_accuracy_swapped_false"] is not None
                    and group_diagnostics["task_b_accuracy_swapped_true"] is not None
                ):
                    task_b_gap = round(
                        abs(
                            group_diagnostics["task_b_accuracy_swapped_false"]
                            - group_diagnostics["task_b_accuracy_swapped_true"]
                        ),
                        4,
                    )
                    if task_b_gap > thresholds["max_task_b_swap_accuracy_gap"]:
                        failures.append(
                            f"{model}/{condition_name}: task_b swap accuracy gap {task_b_gap:.4f} exceeds threshold {thresholds['max_task_b_swap_accuracy_gap']:.4f}"
                        )
                group_report["task_b_swap_accuracy_gap"] = task_b_gap
                same_heart_acc = group_report["metrics"]["same_heart_control_accuracy"]["point"]
                if same_heart_acc is not None and same_heart_acc < thresholds["min_same_heart_control_accuracy"]:
                    failures.append(
                        f"{model}/{condition_name}: same_heart_control_accuracy {same_heart_acc:.4f} is below threshold {thresholds['min_same_heart_control_accuracy']:.4f}"
                    )
                overreach = group_report["metrics"]["heart_overreach_rate"]["point"]
                if overreach is not None and overreach > thresholds["max_heart_overreach_rate"]:
                    failures.append(
                        f"{model}/{condition_name}: heart_overreach_rate {overreach:.4f} exceeds threshold {thresholds['max_heart_overreach_rate']:.4f}"
                    )
        if baseline and christian:
            overreach_delta = None
            hss_delta = None
            if (
                christian["metrics"]["heart_overreach_rate"]["point"] is not None
                and baseline["metrics"]["heart_overreach_rate"]["point"] is not None
            ):
                overreach_delta = round(
                    christian["metrics"]["heart_overreach_rate"]["point"]
                    - baseline["metrics"]["heart_overreach_rate"]["point"],
                    4,
                )
            if (
                christian["metrics"]["heart_sensitivity_score"]["point"] is not None
                and baseline["metrics"]["heart_sensitivity_score"]["point"] is not None
            ):
                hss_delta = round(
                    christian["metrics"]["heart_sensitivity_score"]["point"]
                    - baseline["metrics"]["heart_sensitivity_score"]["point"],
                    4,
                )
            contrast = {
                "model": model,
                "baseline_to_christian_overreach_delta": overreach_delta,
                "baseline_to_christian_hss_delta": hss_delta,
            }
            model_contrasts.append(contrast)
            if (
                overreach_delta is not None
                and overreach_delta > thresholds["max_overreach_delta_without_hss_gain"]
                and (hss_delta is None or hss_delta <= 0)
            ):
                failures.append(
                    f"{model}: christian overreach delta {overreach_delta:.4f} is too high without positive HSS gain"
                )

    report = {
        "expected_models": expected_models,
        "expected_jobs_per_model": len(expected_job_ids),
        "expected_jobs_total": len(expected_job_keys),
        "valid_records": len(valid_records),
        "invalid_records": invalid_records,
        "missing_job_keys": [f"{model}:{job_id}" for model, job_id in missing_job_keys],
        "parse_failure_rate": parse_failure_rate,
        "groups": report_groups,
        "model_contrasts": model_contrasts,
        "failures": failures,
    }

    print(f"expected_jobs_total={report['expected_jobs_total']}")
    print(f"valid_records={report['valid_records']}")
    print(f"parse_failure_rate={report['parse_failure_rate']}")
    for group in report_groups:
        print(
            f"{group['model']} | {group['condition']} | "
            f"HSS={group['metrics']['heart_sensitivity_score']['point']} | "
            f"SameHeart={group['metrics']['same_heart_control_accuracy']['point']} | "
            f"HOR={group['metrics']['heart_overreach_rate']['point']}"
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote pilot health report to {output_path}")

    if failures:
        print("\nPilot health failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
