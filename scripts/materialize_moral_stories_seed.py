#!/usr/bin/env python3
"""Materialize a curated Moral Stories seed CSV from the official raw release."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW = ROOT / "external/hf_cache/data/moral_stories_full.jsonl"
DEFAULT_MANIFEST = ROOT / "data/moral_stories/moral_stories_seed_manifest_v0.json"
DEFAULT_OUTPUT = ROOT / "data/moral_stories/moral_stories_subset_seed_v0.csv"
FIELDNAMES = [
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
PAIR_TYPE = "same_intention_moral_vs_immoral_action"


def load_manifest(path: Path) -> List[Dict[str, str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError(f"{path}: expected a JSON array")
    for index, row in enumerate(manifest, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: entry {index} must be an object")
        missing = [field for field in ("item_id", "domain", "difficulty", "primary_diagnostic_dimension") if field not in row]
        if missing:
            raise ValueError(f"{path}: entry {index} missing required fields: {missing}")
    return manifest


def load_raw_rows(path: Path) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            item_id = row.get("ID")
            if not item_id:
                raise ValueError(f"{path}:{line_number}: missing ID field")
            rows[item_id] = row
    return rows


def canonical_raw_id(item_id: str) -> str:
    if item_id.startswith("MS_"):
        return item_id[3:]
    return item_id


def build_case_text(situation: str, intention: str, action: str, consequence: str) -> str:
    return (
        f"Situation: {situation} "
        f"Intention: {intention} "
        f"Action: {action} "
        f"Consequence: {consequence}"
    )


def adjudication_note(primary_dimension: str) -> str:
    if primary_dimension == "rule":
        return (
            "Both cases keep the same stated intention, so Task B should stay Same. "
            "Case B is more morally problematic because it violates the governing norm while case A does not."
        )
    if primary_dimension == "outward_act":
        return (
            "Both cases keep the same stated intention, so Task B should stay Same. "
            "Case B is more morally problematic because the outward behavior itself is more wrongful or abusive."
        )
    if primary_dimension == "consequence":
        return (
            "Both cases keep the same stated intention, so Task B should stay Same. "
            "Case B is more morally problematic because it foreseeably produces the more harmful outcome."
        )
    if primary_dimension == "motive":
        return (
            "This control slice holds intention constant, so Task B should stay Same. "
            "A motive-based gold label would be inappropriate for this item family."
        )
    return (
        "Both cases keep the same stated intention, so Task B should stay Same. "
        "Case B is more morally problematic for non-motive reasons."
    )


def materialize_row(config: Dict[str, str], raw: Dict[str, str]) -> Dict[str, str]:
    moral_action = raw["moral_action"].strip()
    immoral_action = raw["immoral_action"].strip()
    moral_consequence = raw["moral_consequence"].strip()
    immoral_consequence = raw["immoral_consequence"].strip()
    intention = raw["intention"].strip()
    norm = raw["norm"].strip()
    situation = raw["situation"].strip()
    primary_dimension = config["primary_diagnostic_dimension"]

    return {
        "item_id": config["item_id"],
        "source_story_id": config.get("source_story_id", canonical_raw_id(config["item_id"])),
        "source_split": config.get("source_split", "full"),
        "domain": config["domain"],
        "difficulty": config["difficulty"],
        "original_norm": norm,
        "situation": situation,
        "intention": intention,
        "action": f"{moral_action} / {immoral_action}",
        "consequence": f"{moral_consequence} / {immoral_consequence}",
        "pair_type": PAIR_TYPE,
        "primary_diagnostic_dimension": primary_dimension,
        "case_a_text": build_case_text(situation, intention, moral_action, moral_consequence),
        "case_b_text": build_case_text(situation, intention, immoral_action, immoral_consequence),
        "case_a_outward_act_summary": moral_action,
        "case_b_outward_act_summary": immoral_action,
        "case_a_motive_summary": intention,
        "case_b_motive_summary": intention,
        "case_a_consequence_summary": moral_consequence,
        "case_b_consequence_summary": immoral_consequence,
        "case_a_rule_summary": norm,
        "case_b_rule_summary": norm,
        "gold_task_a": config.get("gold_task_a", "B"),
        "gold_task_b": config.get("gold_task_b", "Same"),
        "gold_task_c": config.get("gold_task_c", primary_dimension),
        "adjudication_note": config.get("adjudication_note", adjudication_note(primary_dimension)),
        "benchmark_role": config.get("benchmark_role", "same_heart_control"),
        "study_split": config.get("study_split", "main"),
        "held_constant": config.get(
            "held_constant",
            "The situation, source story, and stated intention are held constant across A and B.",
        ),
        "changed_dimension": config.get(
            "changed_dimension",
            "The chosen outward action and downstream consequence differ while the stated intention stays fixed.",
        ),
        "include_in_mvp": config.get("include_in_mvp", "yes"),
        "author": config.get("author", "codex_materialized_v0"),
        "review_status": config.get("review_status", "reviewed"),
        "notes": config.get("notes", ""),
    }


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=str(DEFAULT_RAW), help="Official Moral Stories JSONL")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Curated manifest JSON with item ids and labels",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output curated CSV path")
    args = parser.parse_args(argv)

    raw_rows = load_raw_rows(Path(args.raw))
    manifest = load_manifest(Path(args.manifest))

    missing_ids = [row["item_id"] for row in manifest if canonical_raw_id(row["item_id"]) not in raw_rows]
    if missing_ids:
        print("Missing item ids in raw release:", file=sys.stderr)
        for item_id in missing_ids:
            print(f"- {item_id}", file=sys.stderr)
        return 1

    rows = [materialize_row(row, raw_rows[canonical_raw_id(row["item_id"])]) for row in manifest]
    write_csv(Path(args.output), rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
