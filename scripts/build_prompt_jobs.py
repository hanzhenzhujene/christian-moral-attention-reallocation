#!/usr/bin/env python3
"""Render benchmark items into condition-specific prompt jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_DIR = ROOT / "prompts"
DEFAULT_SCRIPTURE_BLOCK = "\n".join(
    [
        "- 1 Samuel 16:7",
        "- Matthew 5:8",
        "- Matthew 23:27-28",
    ]
)
CONDITION_TO_PROMPT_FILENAME = {
    "baseline": "baseline_prompt.txt",
    "neutral_intention_sensitive": "neutral_intention_sensitive_prompt.txt",
    "christian_heart": "christian_heart_prompt.txt",
    "doctrinal": "doctrinal_prompt.txt",
    "secular_matched": "secular_matched_prompt.txt",
    "scripture_citation_only": "scripture_citation_only_prompt.txt",
}


def load_items(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"{path}: expected a JSON object or array")


def load_all_items(paths: Iterable[str]) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    for raw_path in paths:
        all_items.extend(load_items(Path(raw_path)))
    return all_items


def flip_ab(label: str) -> str:
    if label == "A":
        return "B"
    if label == "B":
        return "A"
    return label


def condition_prompt_path(condition: str, prompt_dir: Path) -> Path:
    try:
        filename = CONDITION_TO_PROMPT_FILENAME[condition]
    except KeyError as exc:
        allowed = ", ".join(sorted(CONDITION_TO_PROMPT_FILENAME))
        raise ValueError(f"Unknown condition '{condition}'. Allowed: {allowed}") from exc
    path = prompt_dir / filename
    if not path.exists():
        raise ValueError(f"Missing prompt template for '{condition}': {path}")
    return path


MORAL_STORIES_CASE_RE = re.compile(
    r"^Situation:\s*(?P<situation>.*?)\s+Intention:\s*(?P<intention>.*?)\s+Action:\s*(?P<action>.*?)\s+Consequence:\s*(?P<consequence>.*)$",
    re.DOTALL,
)


def fallback_situation(text: str) -> str:
    marker = " because "
    if marker in text:
        prefix = text.split(marker, 1)[0].strip()
        if prefix and prefix[-1] not in ".!?":
            prefix += "."
        return prefix
    return text.strip()


def canonical_case_slots(case: Dict[str, Any]) -> Dict[str, str]:
    text = case["text"].strip()
    match = MORAL_STORIES_CASE_RE.match(text)
    if match:
        slots = {
            "situation": match.group("situation").strip(),
            "intention": match.group("intention").strip(),
            "action": match.group("action").strip(),
            "consequence": match.group("consequence").strip(),
            "norm": case["rule_summary"].strip(),
        }
    else:
        slots = {
            "situation": fallback_situation(text),
            "intention": case["motive_summary"].strip(),
            "action": case["outward_act_summary"].strip(),
            "consequence": case["consequence_summary"].strip(),
            "norm": case["rule_summary"].strip(),
        }
    return slots


def structured_case_block(case: Dict[str, Any]) -> str:
    slots = canonical_case_slots(case)
    return "\n".join(
        [
            f"- Situation: {slots['situation']}",
            f"- Stated intention: {slots['intention']}",
            f"- Action: {slots['action']}",
            f"- Consequence: {slots['consequence']}",
            f"- Governing norm: {slots['norm']}",
        ]
    )


def task_ac_case_block(case: Dict[str, Any]) -> str:
    slots = canonical_case_slots(case)
    return "\n".join(
        [
            f"- Situation: {slots['situation']}",
            f"- Action: {slots['action']}",
            f"- Consequence: {slots['consequence']}",
            f"- Governing norm: {slots['norm']}",
        ]
    )


def rendered_prompt(
    template: str,
    presented_case_a: Dict[str, Any],
    presented_case_b: Dict[str, Any],
    scripture_block: str,
) -> str:
    case_a_slots = canonical_case_slots(presented_case_a)
    case_b_slots = canonical_case_slots(presented_case_b)
    replacements = {
        "{{case_a}}": presented_case_a["text"],
        "{{case_b}}": presented_case_b["text"],
        "{{scripture_block}}": scripture_block,
        "{{case_a_outward_act_summary}}": presented_case_a["outward_act_summary"],
        "{{case_b_outward_act_summary}}": presented_case_b["outward_act_summary"],
        "{{case_a_motive_summary}}": presented_case_a["motive_summary"],
        "{{case_b_motive_summary}}": presented_case_b["motive_summary"],
        "{{case_a_consequence_summary}}": presented_case_a["consequence_summary"],
        "{{case_b_consequence_summary}}": presented_case_b["consequence_summary"],
        "{{case_a_rule_summary}}": presented_case_a["rule_summary"],
        "{{case_b_rule_summary}}": presented_case_b["rule_summary"],
        "{{case_a_situation_summary}}": case_a_slots["situation"],
        "{{case_b_situation_summary}}": case_b_slots["situation"],
        "{{case_a_structured}}": structured_case_block(presented_case_a),
        "{{case_b_structured}}": structured_case_block(presented_case_b),
        "{{case_a_task_ac_block}}": task_ac_case_block(presented_case_a),
        "{{case_b_task_ac_block}}": task_ac_case_block(presented_case_b),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def should_swap(item_id: str, condition: str, seed: int, swap_mode: str, ordinal: int) -> bool:
    if swap_mode == "none":
        return False
    if swap_mode == "alternate":
        return ordinal % 2 == 1
    digest = hashlib.sha256(f"{seed}:{item_id}:{condition}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2 == 1


def stable_score(item_id: str, condition: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{item_id}:{condition}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def choose_balanced_swaps(
    items: Sequence[Dict[str, Any]],
    condition: str,
    seed: int,
) -> Dict[str, bool]:
    counts = Counter()
    swap_counts = Counter()
    assignments: Dict[str, bool] = {}
    ordered_items = sorted(items, key=lambda item: stable_score(item["item_id"], condition, seed))
    target_true = len(items) / 2

    for item in ordered_items:
        gold = item["gold"]["task_a_more_morally_problematic"]
        options = []
        for swap in (False, True):
            presented = flip_ab(gold) if swap else gold
            next_counts = counts.copy()
            if presented in {"A", "B"}:
                next_counts[presented] += 1
            gap = abs(next_counts["A"] - next_counts["B"])
            next_swap_counts = swap_counts.copy()
            next_swap_counts[swap] += 1
            swap_gap = abs(next_swap_counts[True] - next_swap_counts[False])
            swap_target_gap = abs(next_swap_counts[True] - target_true)
            options.append((gap, swap_target_gap, swap_gap, stable_score(item["item_id"], condition, seed) % 2, swap))
        _, _, _, _, chosen_swap = min(options)
        assignments[item["item_id"]] = chosen_swap
        presented = flip_ab(gold) if chosen_swap else gold
        if presented in {"A", "B"}:
            counts[presented] += 1
        swap_counts[chosen_swap] += 1

    return assignments


def build_jobs(
    items: Sequence[Dict[str, Any]],
    conditions: Sequence[str],
    seed: int,
    swap_mode: str,
    scripture_block: str,
    prompt_dir: Path,
) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    balanced_assignments = {
        condition: choose_balanced_swaps(items, condition, seed) if swap_mode == "task_a_balanced" else {}
        for condition in conditions
    }
    ordinal = 0
    for item in items:
        for condition in conditions:
            template_path = condition_prompt_path(condition, prompt_dir)
            template_text = template_path.read_text(encoding="utf-8")
            if swap_mode == "task_a_balanced":
                swap = balanced_assignments[condition][item["item_id"]]
            else:
                swap = should_swap(item["item_id"], condition, seed, swap_mode, ordinal)
            ordinal += 1

            presented_case_a = item["case_b"] if swap else item["case_a"]
            presented_case_b = item["case_a"] if swap else item["case_b"]
            gold_a = flip_ab(item["gold"]["task_a_more_morally_problematic"]) if swap else item["gold"]["task_a_more_morally_problematic"]
            gold_b = flip_ab(item["gold"]["task_b_worse_inward_orientation"]) if swap else item["gold"]["task_b_worse_inward_orientation"]

            jobs.append(
                {
                    "job_id": f"{item['item_id']}__{condition}",
                    "item_id": item["item_id"],
                    "benchmark_source": item["benchmark_source"],
                    "condition": condition,
                    "pair_type": item["pair_type"],
                    "primary_diagnostic_dimension": item["primary_diagnostic_dimension"],
                    "domain": item["domain"],
                    "difficulty": item["difficulty"],
                    "swapped": swap,
                    "prompt_template_path": str(template_path),
                    "presented_case_a_source": "case_b" if swap else "case_a",
                    "presented_case_b_source": "case_a" if swap else "case_b",
                    "gold": {
                        "task_a_more_morally_problematic": gold_a,
                        "task_b_worse_inward_orientation": gold_b,
                        "task_c_primary_reason": item["gold"]["task_c_primary_reason"],
                        "adjudication_note": item["gold"]["adjudication_note"],
                    },
                    "prompt": rendered_prompt(template_text, presented_case_a, presented_case_b, scripture_block),
                }
            )
    return jobs


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--items",
        nargs="+",
        required=True,
        help="Benchmark JSON files to include",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["baseline", "christian_heart", "secular_matched"],
        help="Prompt conditions to render",
    )
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--seed", type=int, default=7, help="Seed for deterministic swapping")
    parser.add_argument(
        "--swap-mode",
        choices=["task_a_balanced", "random", "alternate", "none"],
        default="task_a_balanced",
        help="How to assign A/B swapping across jobs",
    )
    parser.add_argument(
        "--scripture-block",
        default=DEFAULT_SCRIPTURE_BLOCK,
        help="Replacement text for the scripture block placeholder",
    )
    parser.add_argument(
        "--prompt-dir",
        default=str(DEFAULT_PROMPT_DIR),
        help="Directory containing prompt template files",
    )
    args = parser.parse_args(argv)

    items = load_all_items(args.items)
    jobs = build_jobs(
        items,
        args.conditions,
        args.seed,
        args.swap_mode,
        args.scripture_block,
        Path(args.prompt_dir),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_path, jobs)

    print(f"Wrote {len(jobs)} jobs to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
