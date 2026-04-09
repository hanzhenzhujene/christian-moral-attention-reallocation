#!/usr/bin/env python3
"""Validate benchmark item files for the Christian Moral Attention project."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


BENCHMARK_SOURCES = {"MoralStories", "HeartBench"}
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
AB_SAME = {"A", "B", "Same"}
REASON_LABELS = {"outward_act", "motive", "consequence", "rule"}
REVIEW_STATUSES = {"draft", "reviewed", "approved"}
BENCHMARK_ROLES = {"motive_main", "same_heart_control", "supplement", "pilot_probe"}
STUDY_SPLITS = {"main", "pilot_holdout", "candidate", "exploratory"}


def load_items(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"{path}: expected a JSON object or array")


def require_string(item: Dict[str, Any], field: str, errors: List[str], prefix: str) -> None:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}: field '{field}' must be a non-empty string")


def require_enum(
    item: Dict[str, Any],
    field: str,
    allowed: Iterable[str],
    errors: List[str],
    prefix: str,
) -> None:
    value = item.get(field)
    if value not in allowed:
        errors.append(f"{prefix}: field '{field}' must be one of {sorted(allowed)}")


def validate_case(case: Any, label: str, errors: List[str], prefix: str) -> None:
    if not isinstance(case, dict):
        errors.append(f"{prefix}: '{label}' must be an object")
        return
    require_string(case, "text", errors, f"{prefix}.{label}")
    require_string(case, "outward_act_summary", errors, f"{prefix}.{label}")
    require_string(case, "motive_summary", errors, f"{prefix}.{label}")
    for optional_field in ("consequence_summary", "rule_summary"):
        value = case.get(optional_field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{prefix}.{label}: '{optional_field}' must be a string when present")


def validate_gold(gold: Any, errors: List[str], prefix: str) -> None:
    if not isinstance(gold, dict):
        errors.append(f"{prefix}: 'gold' must be an object")
        return
    require_enum(gold, "task_a_more_morally_problematic", AB_SAME, errors, f"{prefix}.gold")
    require_enum(gold, "task_b_worse_inward_orientation", AB_SAME, errors, f"{prefix}.gold")
    require_enum(gold, "task_c_primary_reason", REASON_LABELS, errors, f"{prefix}.gold")
    require_string(gold, "adjudication_note", errors, f"{prefix}.gold")


def validate_metadata(metadata: Any, errors: List[str], prefix: str) -> None:
    if not isinstance(metadata, dict):
        errors.append(f"{prefix}: 'metadata' must be an object")
        return
    require_string(metadata, "author", errors, f"{prefix}.metadata")
    require_enum(metadata, "review_status", REVIEW_STATUSES, errors, f"{prefix}.metadata")
    tags = metadata.get("tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
        errors.append(f"{prefix}.metadata: 'tags' must be a list of non-empty strings")
    if not isinstance(metadata.get("mvp_candidate"), bool):
        errors.append(f"{prefix}.metadata: 'mvp_candidate' must be a boolean")
    for optional_field in ("source_story_id", "source_split", "held_constant", "changed_dimension", "notes"):
        value = metadata.get(optional_field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"{prefix}.metadata: '{optional_field}' must be a non-empty string when present")
    benchmark_role = metadata.get("benchmark_role")
    if benchmark_role is not None and benchmark_role not in BENCHMARK_ROLES:
        errors.append(f"{prefix}.metadata: 'benchmark_role' must be one of {sorted(BENCHMARK_ROLES)}")
    study_split = metadata.get("study_split")
    if study_split is not None and study_split not in STUDY_SPLITS:
        errors.append(f"{prefix}.metadata: 'study_split' must be one of {sorted(STUDY_SPLITS)}")


def validate_item(item: Any, index: int, path: Path, errors: List[str]) -> str | None:
    prefix = f"{path.name}[{index}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix}: each item must be an object")
        return None

    require_string(item, "item_id", errors, prefix)
    require_enum(item, "benchmark_source", BENCHMARK_SOURCES, errors, prefix)
    require_enum(item, "pair_type", PAIR_TYPES, errors, prefix)
    require_enum(item, "primary_diagnostic_dimension", PRIMARY_DIMENSIONS, errors, prefix)
    require_enum(item, "domain", DOMAINS, errors, prefix)
    require_enum(item, "difficulty", DIFFICULTIES, errors, prefix)
    validate_case(item.get("case_a"), "case_a", errors, prefix)
    validate_case(item.get("case_b"), "case_b", errors, prefix)
    validate_gold(item.get("gold"), errors, prefix)
    validate_metadata(item.get("metadata"), errors, prefix)

    item_id = item.get("item_id")
    if isinstance(item_id, str):
        return item_id
    return None


def counter_string(counter: Counter) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))


def summarize(items: Sequence[Dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"items={len(items)}",
            f"benchmark_source: {counter_string(Counter(item['benchmark_source'] for item in items))}",
            f"pair_type: {counter_string(Counter(item['pair_type'] for item in items))}",
            "primary_diagnostic_dimension: "
            + counter_string(Counter(item["primary_diagnostic_dimension"] for item in items)),
            f"domain: {counter_string(Counter(item['domain'] for item in items))}",
            f"difficulty: {counter_string(Counter(item['difficulty'] for item in items))}",
        ]
    )


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="JSON benchmark files to validate")
    args = parser.parse_args(argv)

    errors: List[str] = []
    all_items: List[Dict[str, Any]] = []
    seen_ids: Dict[str, Path] = {}

    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            errors.append(f"{path}: file does not exist")
            continue
        try:
            items = load_items(path)
        except Exception as exc:  # pragma: no cover - simple CLI fallback
            errors.append(str(exc))
            continue

        for index, item in enumerate(items):
            item_id = validate_item(item, index, path, errors)
            if item_id:
                if item_id in seen_ids:
                    errors.append(
                        f"{path.name}[{index}]: duplicate item_id '{item_id}' also found in {seen_ids[item_id].name}"
                    )
                else:
                    seen_ids[item_id] = path
            if isinstance(item, dict):
                all_items.append(item)

        print(f"[ok] loaded {path} ({len(items)} items)")

    if errors:
        print("\nValidation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("\nSummary:")
    print(summarize(all_items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
