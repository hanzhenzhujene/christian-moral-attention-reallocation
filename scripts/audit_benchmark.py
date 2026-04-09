#!/usr/bin/env python3
"""Audit benchmark files for balance, structural invariants, and leakage risks."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


LEAKAGE_PATTERNS = {
    "selfless": r"\bselfless\b",
    "morally_superior": r"\bmorally superior\b",
    "compassionate_image": r"\bcompassionate image\b",
    "good_parent": r"\bgood parent\b",
    "humble": r"\bhumble\b",
    "virtuous": r"\bvirtuous\b",
    "vicious": r"\bvicious\b",
    "disordered": r"\bdisordered\b",
    "corrupt": r"\bcorrupt\b",
}
PAIR_INVARIANTS = {
    "same_act_different_motive": ("outward_act_summary",),
    "same_norm_different_heart": ("rule_summary",),
    "same_consequence_different_motive": ("consequence_summary",),
    "same_motive_different_consequence": ("motive_summary",),
    "same_intention_moral_vs_immoral_action": ("motive_summary", "rule_summary"),
    "outwardly_harsh_benevolent_vs_malicious": ("outward_act_summary",),
    "outwardly_good_vain_vs_loving": ("outward_act_summary",),
    "outwardly_compliant_resentful_vs_cheerful": ("outward_act_summary",),
}


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


def counter_to_dict(counter: Counter) -> Dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def safe_mean(values: Sequence[int]) -> float | None:
    if not values:
        return None
    return round(statistics.mean(values), 2)


def case_text_lengths(items: Sequence[Dict[str, Any]]) -> Dict[str, float | int | None]:
    lengths = [len(item[case]["text"]) for item in items for case in ("case_a", "case_b")]
    return {
        "min_chars": min(lengths) if lengths else None,
        "max_chars": max(lengths) if lengths else None,
        "mean_chars": safe_mean(lengths),
    }


def audit_invariants(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    for item in items:
        for field in PAIR_INVARIANTS.get(item["pair_type"], ()):
            left = item["case_a"].get(field)
            right = item["case_b"].get(field)
            if left != right:
                violations.append(
                    {
                        "item_id": item["item_id"],
                        "pair_type": item["pair_type"],
                        "field": field,
                        "case_a_value": left,
                        "case_b_value": right,
                    }
                )
    return violations


def audit_primary_reason_alignment(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    warnings: List[Dict[str, Any]] = []
    for item in items:
        primary = item["primary_diagnostic_dimension"]
        gold_reason = item["gold"]["task_c_primary_reason"]
        if primary != "mixed" and primary != gold_reason:
            warnings.append(
                {
                    "item_id": item["item_id"],
                    "primary_diagnostic_dimension": primary,
                    "gold_task_c_primary_reason": gold_reason,
                }
            )
    return warnings


def audit_leakage_terms(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flagged: List[Dict[str, Any]] = []
    for item in items:
        hits = set()
        for case_key in ("case_a", "case_b"):
            text = item[case_key]["text"].lower()
            for label, pattern in LEAKAGE_PATTERNS.items():
                if re.search(pattern, text):
                    hits.add(label)
        if hits:
            flagged.append({"item_id": item["item_id"], "terms": sorted(hits)})
    return flagged


def audit_duplicate_summaries(items: Sequence[Dict[str, Any]], field: str) -> Dict[str, List[str]]:
    bucket: Dict[str, List[str]] = defaultdict(list)
    for item in items:
        for case_key in ("case_a", "case_b"):
            value = item[case_key].get(field)
            if value:
                bucket[value].append(item["item_id"])
    return {
        key: sorted(set(value))
        for key, value in bucket.items()
        if len(set(value)) > 1
    }


def summarize(items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "n_items": len(items),
        "benchmark_source": counter_to_dict(Counter(item["benchmark_source"] for item in items)),
        "pair_type": counter_to_dict(Counter(item["pair_type"] for item in items)),
        "primary_diagnostic_dimension": counter_to_dict(
            Counter(item["primary_diagnostic_dimension"] for item in items)
        ),
        "domain": counter_to_dict(Counter(item["domain"] for item in items)),
        "difficulty": counter_to_dict(Counter(item["difficulty"] for item in items)),
        "gold_task_a": counter_to_dict(
            Counter(item["gold"]["task_a_more_morally_problematic"] for item in items)
        ),
        "gold_task_b": counter_to_dict(
            Counter(item["gold"]["task_b_worse_inward_orientation"] for item in items)
        ),
        "gold_task_c": counter_to_dict(
            Counter(item["gold"]["task_c_primary_reason"] for item in items)
        ),
        "text_length": case_text_lengths(items),
    }


def print_human_report(report: Dict[str, Any]) -> None:
    print(f"items={report['summary']['n_items']}")
    for field in (
        "benchmark_source",
        "pair_type",
        "primary_diagnostic_dimension",
        "domain",
        "difficulty",
        "gold_task_a",
        "gold_task_b",
        "gold_task_c",
    ):
        values = ", ".join(f"{k}={v}" for k, v in report["summary"][field].items())
        print(f"{field}: {values}")
    text_length = report["summary"]["text_length"]
    print(
        "text_length: "
        f"min_chars={text_length['min_chars']}, "
        f"mean_chars={text_length['mean_chars']}, "
        f"max_chars={text_length['max_chars']}"
    )
    print(f"invariant_violations={len(report['invariant_violations'])}")
    print(f"primary_reason_alignment_warnings={len(report['primary_reason_alignment_warnings'])}")
    print(f"leakage_term_flags={len(report['leakage_term_flags'])}")
    print(
        "cross_item_duplicate_outward_act_summaries="
        f"{len(report['cross_item_duplicate_outward_act_summaries'])}"
    )


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Benchmark JSON files to audit")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    items = load_all_items(args.paths)
    report = {
        "summary": summarize(items),
        "invariant_violations": audit_invariants(items),
        "primary_reason_alignment_warnings": audit_primary_reason_alignment(items),
        "leakage_term_flags": audit_leakage_terms(items),
        "cross_item_duplicate_outward_act_summaries": audit_duplicate_summaries(items, "outward_act_summary"),
    }

    print_human_report(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote audit report to {output_path}")

    if report["invariant_violations"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
