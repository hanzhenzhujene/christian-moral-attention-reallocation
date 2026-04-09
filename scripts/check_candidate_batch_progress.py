#!/usr/bin/env python3
"""Check transformed candidate batches against quota and quality constraints."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import audit_benchmark
import check_release_gates
import validate_benchmark


TRANSFORMED_PAIR_TYPES = {
    "same_act_different_motive",
    "same_norm_different_heart",
    "same_consequence_different_motive",
}


def load_items(paths: Iterable[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw_path in paths:
        items.extend(validate_benchmark.load_items(Path(raw_path)))
    return items


def transformed_items(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        item
        for item in items
        if item.get("benchmark_source") == "MoralStories"
        and item.get("metadata", {}).get("benchmark_role") == "motive_main"
    ]


def source_ids(items: Sequence[Dict[str, Any]]) -> set[str]:
    out = set()
    for item in items:
        source_story_id = item.get("metadata", {}).get("source_story_id")
        if isinstance(source_story_id, str) and source_story_id:
            out.add(source_story_id)
    return out


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Study config JSON")
    parser.add_argument("--candidate-items", nargs="+", required=True, help="Candidate JSON files")
    parser.add_argument("--controls", nargs="+", default=[], help="Same-heart control JSON files")
    parser.add_argument("--pilot-items", nargs="+", default=[], help="Pilot JSON files")
    parser.add_argument("--main-items", nargs="+", default=[], help="Already-promoted main JSON files")
    parser.add_argument("--solo-consistency", help="Optional solo consistency summary JSON")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    candidates = transformed_items(load_items(args.candidate_items))
    controls = load_items(args.controls)
    pilot_items = load_items(args.pilot_items)
    main_items = transformed_items(load_items(args.main_items))

    cumulative = [*main_items, *candidates]
    pair_counts = Counter(item["pair_type"] for item in cumulative if item["pair_type"] in TRANSFORMED_PAIR_TYPES)
    target_pair_counts = {
        key: value
        for key, value in config["targets"]["main"]["moral_stories_pair_type"].items()
        if key in TRANSFORMED_PAIR_TYPES
    }
    pair_remaining = {
        key: max(target_pair_counts[key] - pair_counts.get(key, 0), 0)
        for key in target_pair_counts
    }

    domain_share = check_release_gates.max_domain_share(cumulative)
    motive_imbalance = check_release_gates.motive_gold_imbalance(cumulative)
    leakage_flags = audit_benchmark.audit_leakage_terms(candidates)
    invariants = audit_benchmark.audit_invariants(candidates)

    candidate_sources = source_ids(candidates)
    overlap = {
        "candidate_vs_controls": sorted(candidate_sources & source_ids(controls)),
        "candidate_vs_pilot": sorted(candidate_sources & source_ids(pilot_items)),
        "candidate_vs_main": sorted(candidate_sources & source_ids(main_items)),
    }

    solo_consistency = None
    if args.solo_consistency:
        solo_consistency = json.loads(Path(args.solo_consistency).read_text(encoding="utf-8"))

    errors: List[str] = []
    if overlap["candidate_vs_controls"] or overlap["candidate_vs_pilot"] or overlap["candidate_vs_main"]:
        errors.append("candidate batch reuses source_story_id values from controls, pilot, or main")
    if domain_share is not None and domain_share > config["gates"]["max_domain_share"]:
        errors.append(
            f"cumulative transformed max domain share {domain_share:.4f} exceeds {config['gates']['max_domain_share']:.4f}"
        )
    if motive_imbalance is not None and motive_imbalance > config["gates"]["max_motive_task_b_imbalance"]:
        errors.append(
            f"cumulative transformed Task B imbalance {motive_imbalance:.4f} exceeds {config['gates']['max_motive_task_b_imbalance']:.4f}"
        )
    if leakage_flags:
        errors.append(f"candidate batch has {len(leakage_flags)} leakage-term flags")
    if invariants:
        errors.append(f"candidate batch has {len(invariants)} invariant violations")
    if solo_consistency and solo_consistency.get("self_disagreement_rate") is not None:
        if solo_consistency["self_disagreement_rate"] > 0:
            errors.append(
                f"solo self_disagreement_rate is {solo_consistency['self_disagreement_rate']:.4f}; revise before promotion"
            )

    report = {
        "n_candidates": len(candidates),
        "candidate_pair_counts": dict(sorted(Counter(item["pair_type"] for item in candidates).items())),
        "candidate_domain_counts": dict(sorted(Counter(item["domain"] for item in candidates).items())),
        "candidate_task_b_counts": dict(
            sorted(Counter(item["gold"]["task_b_worse_inward_orientation"] for item in candidates).items())
        ),
        "cumulative_pair_counts": dict(sorted(pair_counts.items())),
        "cumulative_pair_remaining": pair_remaining,
        "cumulative_max_domain_share": None if domain_share is None else round(domain_share, 4),
        "cumulative_motive_task_b_imbalance": None if motive_imbalance is None else round(motive_imbalance, 4),
        "overlap": overlap,
        "leakage_flags": leakage_flags,
        "invariant_violations": invariants,
        "solo_consistency": solo_consistency,
        "errors": errors,
    }

    print(f"n_candidates={len(candidates)}")
    print(f"candidate_pair_counts={report['candidate_pair_counts']}")
    print(f"cumulative_pair_remaining={pair_remaining}")
    print(f"overlap={overlap}")
    if domain_share is not None:
        print(f"cumulative_max_domain_share={domain_share:.4f}")
    if motive_imbalance is not None:
        print(f"cumulative_motive_task_b_imbalance={motive_imbalance:.4f}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote candidate progress report to {output_path}")

    if errors:
        print("\nCandidate batch failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
