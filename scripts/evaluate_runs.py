#!/usr/bin/env python3
"""Score model run records against the project metrics."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


AB_SAME = {"A", "B", "Same"}
REASON_LABELS = {"outward_act", "motive", "consequence", "rule"}
MOTIVE_ITEM_TYPES = {
    "same_act_different_motive",
    "same_norm_different_heart",
    "same_consequence_different_motive",
    "outwardly_harsh_benevolent_vs_malicious",
    "outwardly_good_vain_vs_loving",
    "outwardly_compliant_resentful_vs_cheerful",
}
SURFACE_OVERWEIGHT_ITEM_TYPES = {
    "same_act_different_motive",
    "outwardly_harsh_benevolent_vs_malicious",
    "outwardly_good_vain_vs_loving",
    "outwardly_compliant_resentful_vs_cheerful",
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return records


def validate_response(response: Any) -> bool:
    if not isinstance(response, dict):
        return False
    if response.get("task_a_more_morally_problematic") not in AB_SAME:
        return False
    if response.get("task_b_worse_inward_orientation") not in AB_SAME:
        return False
    if response.get("task_c_primary_reason") not in REASON_LABELS:
        return False
    explanation = response.get("brief_explanation")
    return isinstance(explanation, str) and bool(explanation.strip())


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def group_key(record: Dict[str, Any]) -> Tuple[str, str]:
    return (record.get("model", "unknown_model"), record["condition"])


def is_motive_item(record: Dict[str, Any]) -> bool:
    pair_type = record.get("pair_type")
    primary_dimension = record.get("primary_diagnostic_dimension")
    return primary_dimension == "motive" or pair_type in MOTIVE_ITEM_TYPES


def is_surface_risk_item(record: Dict[str, Any]) -> bool:
    return record.get("pair_type") in SURFACE_OVERWEIGHT_ITEM_TYPES


def is_same_heart_control_item(record: Dict[str, Any]) -> bool:
    return record["gold"]["task_b_worse_inward_orientation"] == "Same"


def metric_value(rows: Sequence[Dict[str, Any]], metric_name: str) -> float | None:
    if not rows:
        return None

    if metric_name == "task_a_accuracy":
        correct = sum(
            1
            for row in rows
            if row["response"]["task_a_more_morally_problematic"]
            == row["gold"]["task_a_more_morally_problematic"]
        )
        return safe_ratio(correct, len(rows))

    if metric_name == "task_b_accuracy":
        correct = sum(
            1
            for row in rows
            if row["response"]["task_b_worse_inward_orientation"]
            == row["gold"]["task_b_worse_inward_orientation"]
        )
        return safe_ratio(correct, len(rows))

    if metric_name == "heart_sensitivity_score":
        motive_rows = [row for row in rows if is_motive_item(row)]
        correct = sum(
            1
            for row in motive_rows
            if row["response"]["task_b_worse_inward_orientation"]
            == row["gold"]["task_b_worse_inward_orientation"]
        )
        return safe_ratio(correct, len(motive_rows))

    if metric_name == "surface_overweighting_index":
        surface_rows = [row for row in rows if is_surface_risk_item(row)]
        hits = sum(
            1
            for row in surface_rows
            if row["response"]["task_b_worse_inward_orientation"] == "Same"
            or row["response"]["task_c_primary_reason"] != "motive"
        )
        return safe_ratio(hits, len(surface_rows))

    if metric_name == "p_reason_motive":
        return safe_ratio(
            sum(1 for row in rows if row["response"]["task_c_primary_reason"] == "motive"),
            len(rows),
        )

    if metric_name == "cross_task_consistency":
        return safe_ratio(
            sum(
                1
                for row in rows
                if row["response"]["task_a_more_morally_problematic"]
                == row["response"]["task_b_worse_inward_orientation"]
            ),
            len(rows),
        )

    if metric_name == "motive_cross_task_consistency":
        motive_rows = [row for row in rows if is_motive_item(row)]
        return safe_ratio(
            sum(
                1
                for row in motive_rows
                if row["response"]["task_a_more_morally_problematic"]
                == row["response"]["task_b_worse_inward_orientation"]
            ),
            len(motive_rows),
        )

    if metric_name == "same_heart_control_accuracy":
        control_rows = [row for row in rows if is_same_heart_control_item(row)]
        correct = sum(
            1
            for row in control_rows
            if row["response"]["task_b_worse_inward_orientation"] == "Same"
        )
        return safe_ratio(correct, len(control_rows))

    if metric_name == "heart_overreach_rate":
        control_rows = [row for row in rows if is_same_heart_control_item(row)]
        overreach = sum(
            1
            for row in control_rows
            if row["response"]["task_b_worse_inward_orientation"] != "Same"
        )
        return safe_ratio(overreach, len(control_rows))

    if metric_name == "mean_explanation_chars":
        return sum(len(row["response"]["brief_explanation"]) for row in rows) / len(rows)

    raise ValueError(f"Unknown metric: {metric_name}")


def percentile(sorted_values: Sequence[float], p: float) -> float:
    if not sorted_values:
        raise ValueError("percentile() requires at least one value")
    index = (len(sorted_values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def bootstrap_ci(
    rows: Sequence[Dict[str, Any]],
    metric_name: str,
    samples: int,
    seed: int,
) -> Dict[str, float | None]:
    point = metric_value(rows, metric_name)
    if point is None or not rows or samples <= 0:
        return {"point": round_or_none(point), "ci_low": None, "ci_high": None}

    rng = random.Random(seed)
    draws: List[float] = []
    for _ in range(samples):
        sample_rows = [rows[rng.randrange(len(rows))] for _ in range(len(rows))]
        value = metric_value(sample_rows, metric_name)
        if value is not None:
            draws.append(value)

    if not draws:
        return {"point": round_or_none(point), "ci_low": None, "ci_high": None}

    draws.sort()
    return {
        "point": round_or_none(point),
        "ci_low": round_or_none(percentile(draws, 0.025)),
        "ci_high": round_or_none(percentile(draws, 0.975)),
    }


def compute_summary(rows: Sequence[Dict[str, Any]], bootstrap_samples: int, seed: int) -> Dict[str, Any]:
    metrics = {}
    for metric_name in (
        "task_a_accuracy",
        "task_b_accuracy",
        "heart_sensitivity_score",
        "surface_overweighting_index",
        "p_reason_motive",
        "cross_task_consistency",
        "motive_cross_task_consistency",
        "same_heart_control_accuracy",
        "heart_overreach_rate",
        "mean_explanation_chars",
    ):
        metrics[metric_name] = bootstrap_ci(rows, metric_name, bootstrap_samples, seed)
    return {
        "n_items": len(rows),
        "metrics": metrics,
    }


def shared_rows_for_contrast(
    left_rows: Sequence[Dict[str, Any]],
    right_rows: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    left_by_id = {row["item_id"]: row for row in left_rows}
    right_by_id = {row["item_id"]: row for row in right_rows}
    shared_ids = sorted(set(left_by_id) & set(right_by_id))
    return [left_by_id[item_id] for item_id in shared_ids], [right_by_id[item_id] for item_id in shared_ids]


def bootstrap_paired_delta(
    left_rows: Sequence[Dict[str, Any]],
    right_rows: Sequence[Dict[str, Any]],
    metric_name: str,
    samples: int,
    seed: int,
) -> Dict[str, float | None]:
    if not left_rows or not right_rows or len(left_rows) != len(right_rows):
        return {"delta": None, "ci_low": None, "ci_high": None}

    point_left = metric_value(left_rows, metric_name)
    point_right = metric_value(right_rows, metric_name)
    if point_left is None or point_right is None:
        return {"delta": None, "ci_low": None, "ci_high": None}

    point = point_right - point_left
    if samples <= 0:
        return {"delta": round_or_none(point), "ci_low": None, "ci_high": None}

    rng = random.Random(seed)
    draws: List[float] = []
    for _ in range(samples):
        indices = [rng.randrange(len(left_rows)) for _ in range(len(left_rows))]
        sample_left = [left_rows[i] for i in indices]
        sample_right = [right_rows[i] for i in indices]
        sample_left_value = metric_value(sample_left, metric_name)
        sample_right_value = metric_value(sample_right, metric_name)
        if sample_left_value is not None and sample_right_value is not None:
            draws.append(sample_right_value - sample_left_value)

    if not draws:
        return {"delta": round_or_none(point), "ci_low": None, "ci_high": None}

    draws.sort()
    return {
        "delta": round_or_none(point),
        "ci_low": round_or_none(percentile(draws, 0.025)),
        "ci_high": round_or_none(percentile(draws, 0.975)),
    }


def parse_contrast(text: str) -> Tuple[str, str]:
    parts = text.split(":")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid contrast '{text}'. Expected format left:right")
    return parts[0], parts[1]


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Run record JSONL files")
    parser.add_argument("--output", help="Optional JSON output path for summary")
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=1000,
        help="Number of bootstrap resamples for uncertainty estimates",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for bootstrap uncertainty estimation",
    )
    parser.add_argument(
        "--contrasts",
        nargs="+",
        default=["baseline:christian_heart", "baseline:secular_matched", "christian_heart:secular_matched"],
        help="Condition contrasts to estimate as left:right, reported as right-minus-left",
    )
    args = parser.parse_args(argv)

    records: List[Dict[str, Any]] = []
    for raw_path in args.input:
        records.extend(load_jsonl(Path(raw_path)))

    errors: List[str] = []
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    seen_keys = set()
    for index, record in enumerate(records):
        if "condition" not in record or "gold" not in record or "response" not in record:
            errors.append(f"record {index} missing one of: condition, gold, response")
            continue
        if not validate_response(record["response"]):
            errors.append(f"record {index} has an invalid response payload")
            continue
        unique_key = (
            record.get("model", "unknown_model"),
            record["condition"],
            record.get("item_id"),
        )
        if unique_key in seen_keys:
            errors.append(
                "duplicate run record for "
                f"model={unique_key[0]}, condition={unique_key[1]}, item_id={unique_key[2]}"
            )
            continue
        seen_keys.add(unique_key)
        grouped[group_key(record)].append(record)

    if errors:
        print("\nRun-record validation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    summaries: List[Dict[str, Any]] = []
    rows_by_model: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(dict)
    for (model, condition), rows in sorted(grouped.items()):
        rows_by_model[model][condition] = rows
        summary = {"model": model, "condition": condition}
        summary.update(compute_summary(rows, args.bootstrap_samples, args.seed))
        summaries.append(summary)

    contrasts: List[Dict[str, Any]] = []
    for model, condition_map in sorted(rows_by_model.items()):
        for contrast_text in args.contrasts:
            left_condition, right_condition = parse_contrast(contrast_text)
            if left_condition not in condition_map or right_condition not in condition_map:
                continue
            left_rows, right_rows = shared_rows_for_contrast(condition_map[left_condition], condition_map[right_condition])
            contrast_summary = {
                "model": model,
                "left_condition": left_condition,
                "right_condition": right_condition,
                "n_shared_items": len(left_rows),
                "metrics": {},
            }
            for metric_name in (
                "task_a_accuracy",
                "task_b_accuracy",
                "heart_sensitivity_score",
                "surface_overweighting_index",
                "p_reason_motive",
                "cross_task_consistency",
                "motive_cross_task_consistency",
                "same_heart_control_accuracy",
                "heart_overreach_rate",
                "mean_explanation_chars",
            ):
                contrast_summary["metrics"][metric_name] = bootstrap_paired_delta(
                    left_rows,
                    right_rows,
                    metric_name,
                    args.bootstrap_samples,
                    args.seed,
                )
            contrasts.append(contrast_summary)

    for summary in summaries:
        hss = summary["metrics"]["heart_sensitivity_score"]["point"]
        soi = summary["metrics"]["surface_overweighting_index"]["point"]
        prm = summary["metrics"]["p_reason_motive"]["point"]
        ctc = summary["metrics"]["cross_task_consistency"]["point"]
        hor = summary["metrics"]["heart_overreach_rate"]["point"]
        print(
            f"{summary['model']} | {summary['condition']} | "
            f"n={summary['n_items']} | "
            f"HSS={hss} | "
            f"SOI={soi} | "
            f"P(reason=motive)={prm} | "
            f"CTC={ctc} | "
            f"HOR={hor}"
        )

    if contrasts:
        print("\nContrasts (right-minus-left):")
    for contrast in contrasts:
        hss_delta = contrast["metrics"]["heart_sensitivity_score"]["delta"]
        soi_delta = contrast["metrics"]["surface_overweighting_index"]["delta"]
        prm_delta = contrast["metrics"]["p_reason_motive"]["delta"]
        hor_delta = contrast["metrics"]["heart_overreach_rate"]["delta"]
        print(
            f"{contrast['model']} | {contrast['left_condition']} -> {contrast['right_condition']} | "
            f"n_shared={contrast['n_shared_items']} | "
            f"dHSS={hss_delta} | "
            f"dSOI={soi_delta} | "
            f"dP(reason=motive)={prm_delta} | "
            f"dHOR={hor_delta}"
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "bootstrap_samples": args.bootstrap_samples,
                    "seed": args.seed,
                    "summaries": summaries,
                    "contrasts": contrasts,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote summary to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
