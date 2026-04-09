#!/usr/bin/env python3
"""Assemble a benchmark slice by filtering items on metadata fields."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


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


def filter_items(
    items: Sequence[Dict[str, Any]],
    study_split: str | None,
    benchmark_roles: set[str] | None,
    benchmark_sources: set[str] | None,
) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    for item in items:
        metadata = item.get("metadata", {})
        if study_split and metadata.get("study_split") != study_split:
            continue
        if benchmark_roles and metadata.get("benchmark_role") not in benchmark_roles:
            continue
        if benchmark_sources and item.get("benchmark_source") not in benchmark_sources:
            continue
        kept.append(item)
    return kept


def summarize(items: Sequence[Dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"items={len(items)}",
            "benchmark_source: "
            + ", ".join(f"{k}={v}" for k, v in sorted(Counter(item["benchmark_source"] for item in items).items())),
            "pair_type: "
            + ", ".join(f"{k}={v}" for k, v in sorted(Counter(item["pair_type"] for item in items).items())),
            "study_split: "
            + ", ".join(
                f"{k}={v}"
                for k, v in sorted(
                    Counter(item.get("metadata", {}).get("study_split", "missing") for item in items).items()
                )
            ),
            "benchmark_role: "
            + ", ".join(
                f"{k}={v}"
                for k, v in sorted(
                    Counter(item.get("metadata", {}).get("benchmark_role", "missing") for item in items).items()
                )
            ),
        ]
    )


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, help="Benchmark JSON files")
    parser.add_argument("--study-split", help="Filter on metadata.study_split")
    parser.add_argument("--benchmark-roles", nargs="+", help="Allowed metadata.benchmark_role values")
    parser.add_argument("--benchmark-sources", nargs="+", help="Allowed benchmark_source values")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args(argv)

    items = load_all_items(args.inputs)
    kept = filter_items(
        items,
        args.study_split,
        set(args.benchmark_roles) if args.benchmark_roles else None,
        set(args.benchmark_sources) if args.benchmark_sources else None,
    )

    seen_ids: set[str] = set()
    duplicates = sorted(item["item_id"] for item in kept if item["item_id"] in seen_ids or seen_ids.add(item["item_id"]))
    if duplicates:
        print("Duplicate item ids in filtered slice:", file=sys.stderr)
        for item_id in duplicates:
            print(f"- {item_id}", file=sys.stderr)
        return 1

    kept = sorted(kept, key=lambda item: item["item_id"])
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    print(summarize(kept))
    print(f"\nWrote {len(kept)} items to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
