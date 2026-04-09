#!/usr/bin/env python3
"""Check benchmark release gates for the paper-first study design."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import audit_benchmark
import validate_benchmark


def load_config(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_items(paths: Iterable[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw_path in paths:
        items.extend(validate_benchmark.load_items(Path(raw_path)))
    return items


def max_domain_share(items: Sequence[Dict[str, Any]]) -> float | None:
    if not items:
        return None
    counts = Counter(item["domain"] for item in items)
    return max(counts.values()) / len(items)


def motive_gold_imbalance(items: Sequence[Dict[str, Any]]) -> float | None:
    motive_items = [
        item
        for item in items
        if item["gold"]["task_b_worse_inward_orientation"] in {"A", "B"}
        and (
            item["primary_diagnostic_dimension"] == "motive"
            or item["pair_type"]
            in {
                "same_act_different_motive",
                "same_norm_different_heart",
                "same_consequence_different_motive",
                "outwardly_harsh_benevolent_vs_malicious",
                "outwardly_good_vain_vs_loving",
                "outwardly_compliant_resentful_vs_cheerful",
            }
        )
    ]
    if not motive_items:
        return None
    counts = Counter(item["gold"]["task_b_worse_inward_orientation"] for item in motive_items)
    total = sum(counts.values())
    return abs(counts.get("A", 0) - counts.get("B", 0)) / total if total else None


def count_by_pair_type(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return dict(sorted(Counter(item["pair_type"] for item in items).items()))


def count_by_source_and_role(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        role = item.get("metadata", {}).get("benchmark_role", "missing")
        counts[f"{item['benchmark_source']}::{role}"] += 1
    return dict(sorted(counts.items()))


def item_ids(items: Sequence[Dict[str, Any]]) -> set[str]:
    return {item["item_id"] for item in items}


def source_story_map(items: Sequence[Dict[str, Any]], benchmark_source: str | None = None) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for item in items:
        if benchmark_source is not None and item.get("benchmark_source") != benchmark_source:
            continue
        source_story_id = item.get("metadata", {}).get("source_story_id")
        if not isinstance(source_story_id, str) or not source_story_id:
            continue
        mapping.setdefault(source_story_id, []).append(item["item_id"])
    return mapping


def duplicate_source_story_ids(items: Sequence[Dict[str, Any]], benchmark_source: str | None = None) -> Dict[str, List[str]]:
    mapping = source_story_map(items, benchmark_source=benchmark_source)
    return {source_story_id: ids for source_story_id, ids in mapping.items() if len(ids) > 1}


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Study config JSON")
    parser.add_argument("--main-items", nargs="+", required=True, help="Main benchmark JSON files")
    parser.add_argument("--pilot-items", nargs="+", help="Pilot benchmark JSON files")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    main_items = load_items(args.main_items)
    pilot_items = load_items(args.pilot_items or [])

    errors: List[str] = []
    # Schema-level validation.
    seen_ids: Dict[str, Path] = {}
    for path_str in list(args.main_items) + list(args.pilot_items or []):
        path = Path(path_str)
        for index, item in enumerate(validate_benchmark.load_items(path)):
            validate_benchmark.validate_item(item, index, path, errors)
            item_id = item.get("item_id")
            if isinstance(item_id, str):
                if item_id in seen_ids:
                    errors.append(f"{path.name}[{index}]: duplicate item_id '{item_id}' also found in {seen_ids[item_id].name}")
                else:
                    seen_ids[item_id] = path

    main_audit = {
        "invariant_violations": audit_benchmark.audit_invariants(main_items),
        "leakage_term_flags": audit_benchmark.audit_leakage_terms(main_items),
    }
    if main_audit["invariant_violations"]:
        errors.append("main benchmark has invariant violations")
    if main_audit["leakage_term_flags"]:
        errors.append("main benchmark has leakage-term flags")

    overlap = sorted(item_ids(main_items) & item_ids(pilot_items))
    if overlap:
        errors.append(f"main/pilot overlap detected for {len(overlap)} item ids")

    main_duplicate_sources = duplicate_source_story_ids(main_items, benchmark_source="MoralStories")
    if main_duplicate_sources:
        errors.append(
            f"main benchmark reuses {len(main_duplicate_sources)} Moral Stories source_story_id values"
        )

    pilot_duplicate_sources = duplicate_source_story_ids(pilot_items, benchmark_source="MoralStories")
    if pilot_duplicate_sources:
        errors.append(
            f"pilot benchmark reuses {len(pilot_duplicate_sources)} Moral Stories source_story_id values"
        )

    main_sources = source_story_map(main_items, benchmark_source="MoralStories")
    pilot_sources = source_story_map(pilot_items, benchmark_source="MoralStories")
    source_overlap = {
        source_story_id: {"main": main_sources[source_story_id], "pilot": pilot_sources[source_story_id]}
        for source_story_id in sorted(set(main_sources) & set(pilot_sources))
    }
    if source_overlap:
        errors.append(
            f"main/pilot overlap detected for {len(source_overlap)} Moral Stories source_story_id values"
        )

    allowed_statuses = set(config["gates"]["require_review_status"])
    bad_statuses = sorted(
        item["item_id"]
        for item in main_items
        if item.get("metadata", {}).get("review_status") not in allowed_statuses
    )
    if bad_statuses:
        errors.append(f"{len(bad_statuses)} main items have review_status outside {sorted(allowed_statuses)}")

    main_domain_share = max_domain_share(main_items)
    if main_domain_share is not None and main_domain_share > config["gates"]["max_domain_share"]:
        errors.append(
            f"main benchmark max domain share {main_domain_share:.4f} exceeds threshold {config['gates']['max_domain_share']:.4f}"
        )

    motive_imbalance = motive_gold_imbalance(main_items)
    if motive_imbalance is not None and motive_imbalance > config["gates"]["max_motive_task_b_imbalance"]:
        errors.append(
            f"motive Task B imbalance {motive_imbalance:.4f} exceeds threshold {config['gates']['max_motive_task_b_imbalance']:.4f}"
        )

    target_main = config["targets"]["main"]
    if len(main_items) != target_main["expected_total"]:
        errors.append(
            f"main benchmark has {len(main_items)} items, expected {target_main['expected_total']}"
        )
    main_source_role_counts = count_by_source_and_role(main_items)
    for key, expected_count in target_main["source_role"].items():
        if main_source_role_counts.get(key, 0) != expected_count:
            errors.append(
                f"main benchmark composition {key} has {main_source_role_counts.get(key, 0)} items, expected {expected_count}"
            )
    moral_stories_main_items = [
        item for item in main_items if item["benchmark_source"] == "MoralStories"
    ]
    main_pair_counts = count_by_pair_type(moral_stories_main_items)
    for pair_type, expected_count in target_main["moral_stories_pair_type"].items():
        if main_pair_counts.get(pair_type, 0) != expected_count:
            errors.append(
                f"main Moral Stories pair_type {pair_type} has {main_pair_counts.get(pair_type, 0)} items, expected {expected_count}"
            )

    target_pilot = config["targets"]["pilot"]
    if pilot_items and len(pilot_items) != target_pilot["expected_total"]:
        errors.append(f"pilot benchmark has {len(pilot_items)} items, expected {target_pilot['expected_total']}")
    pilot_source_role_counts = count_by_source_and_role(pilot_items)
    for key, expected_count in target_pilot["source_role"].items():
        if pilot_source_role_counts.get(key, 0) != expected_count:
            errors.append(
                f"pilot composition {key} has {pilot_source_role_counts.get(key, 0)} items, expected {expected_count}"
            )

    report = {
        "study_name": config["name"],
        "main_counts": {
            "n_items": len(main_items),
            "pair_type": main_pair_counts,
            "source_role": main_source_role_counts,
            "max_domain_share": None if main_domain_share is None else round(main_domain_share, 4),
            "motive_task_b_imbalance": None if motive_imbalance is None else round(motive_imbalance, 4),
        },
        "pilot_counts": {
            "n_items": len(pilot_items),
            "source_role": pilot_source_role_counts,
        },
        "audit": main_audit,
        "overlap": overlap,
        "source_story_id_overlap": source_overlap,
        "duplicate_source_story_ids": {
            "main": main_duplicate_sources,
            "pilot": pilot_duplicate_sources,
        },
        "errors": errors,
    }

    print(f"study={config['name']}")
    print(f"main_items={len(main_items)}")
    print(f"pilot_items={len(pilot_items)}")
    print(f"main_pair_type={main_pair_counts}")
    print(f"pilot_source_role={pilot_source_role_counts}")
    if main_domain_share is not None:
        print(f"max_domain_share={main_domain_share:.4f}")
    if motive_imbalance is not None:
        print(f"motive_task_b_imbalance={motive_imbalance:.4f}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote gate report to {output_path}")

    if errors:
        print("\nRelease gate failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
