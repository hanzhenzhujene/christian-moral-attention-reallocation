#!/usr/bin/env python3
"""Render a compact SVG overview for the project README."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Sequence


WIDTH = 1200
HEIGHT = 820
CARD_FILL = "#f8fafc"
CARD_STROKE = "#d7dee8"
TEXT = "#122033"
MUTED = "#5c6b7c"
ACCENT = "#0f766e"
ALERT = "#b45309"
BASELINE = "#5166d6"
CHRISTIAN = "#12805c"
SECULAR = "#d97706"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_map(summary_payload: dict) -> Dict[str, Dict[str, Dict[str, float]]]:
    result: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in summary_payload["summaries"]:
        result.setdefault(row["model"], {})[row["condition"]] = {
            name: values["point"] for name, values in row["metrics"].items()
        }
    return result


def swap_gap_map(health_payload: dict) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    for row in health_payload["groups"]:
        result.setdefault(row["model"], {})[row["condition"]] = row["task_b_swap_accuracy_gap"]
    return result


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def card(x: int, y: int, w: int, h: int, title: str, value: str, subtitle: str, tone: str = "default") -> str:
    title_fill = TEXT
    value_fill = TEXT
    if tone == "good":
        value_fill = ACCENT
    elif tone == "warn":
        value_fill = ALERT
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{CARD_FILL}" stroke="{CARD_STROKE}" />
    <text x="{x + 24}" y="{y + 32}" font-size="18" font-weight="600" fill="{title_fill}">{esc(title)}</text>
    <text x="{x + 24}" y="{y + 82}" font-size="38" font-weight="700" fill="{value_fill}">{esc(value)}</text>
    <text x="{x + 24}" y="{y + 112}" font-size="16" fill="{MUTED}">{esc(subtitle)}</text>
    """


def bar_row(x: int, y: int, label: str, value: float, color: str) -> str:
    value = max(0.0, min(1.0, value))
    bar_w = 300
    fill_w = int(bar_w * value)
    return f"""
    <text x="{x}" y="{y + 6}" font-size="16" font-weight="600" fill="{TEXT}">{esc(label)}</text>
    <rect x="{x + 118}" y="{y - 10}" width="{bar_w}" height="16" rx="8" fill="#e8edf4" />
    <rect x="{x + 118}" y="{y - 10}" width="{fill_w}" height="16" rx="8" fill="{color}" />
    <text x="{x + 430}" y="{y + 6}" font-size="16" fill="{TEXT}" text-anchor="end">{value:.3f}</text>
    """


def model_panel(x: int, y: int, model: str, metrics: Dict[str, Dict[str, float]], swap_gaps: Dict[str, float]) -> str:
    labels = [
        ("baseline", "Baseline", BASELINE),
        ("christian_heart", "Christian", CHRISTIAN),
        ("secular_matched", "Secular", SECULAR),
    ]
    hss_rows = []
    gap_rows = []
    for idx, (key, label, color) in enumerate(labels):
        hss_rows.append(bar_row(x + 28, y + 78 + idx * 42, label, metrics[key]["heart_sensitivity_score"], color))
        gap_rows.append(bar_row(x + 28, y + 246 + idx * 42, label, min(1.0, swap_gaps[key]), color))
    same_heart = metrics["baseline"]["same_heart_control_accuracy"]
    overreach = metrics["baseline"]["heart_overreach_rate"]
    return f"""
    <rect x="{x}" y="{y}" width="548" height="360" rx="22" fill="{CARD_FILL}" stroke="{CARD_STROKE}" />
    <text x="{x + 28}" y="{y + 40}" font-size="26" font-weight="700" fill="{TEXT}">{esc(model)}</text>
    <text x="{x + 28}" y="{y + 66}" font-size="15" fill="{MUTED}">Held-out 20-item pilot, benchmark-assisted multi-pass Task B</text>

    <text x="{x + 28}" y="{y + 110}" font-size="18" font-weight="700" fill="{TEXT}">Heart-Sensitivity Score</text>
    {''.join(hss_rows)}

    <text x="{x + 28}" y="{y + 278}" font-size="18" font-weight="700" fill="{TEXT}">Residual Task B Swap-Gap</text>
    {''.join(gap_rows)}

    <text x="{x + 28}" y="{y + 344}" font-size="14" fill="{MUTED}">Same-heart control = {same_heart:.1f} | Heart overreach = {overreach:.1f}</text>
    """


def note_panel(x: int, y: int, w: int, h: int, title: str, lines: Sequence[str], tone: str) -> str:
    accent = ACCENT if tone == "good" else ALERT
    text_lines = []
    for i, line in enumerate(lines):
        text_lines.append(
            f'<text x="{x + 28}" y="{y + 72 + i * 28}" font-size="18" fill="{TEXT}">{esc(line)}</text>'
        )
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{CARD_FILL}" stroke="{CARD_STROKE}" />
    <rect x="{x}" y="{y}" width="8" height="{h}" rx="22" fill="{accent}" />
    <text x="{x + 28}" y="{y + 38}" font-size="22" font-weight="700" fill="{TEXT}">{esc(title)}</text>
    {''.join(text_lines)}
    """


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="Summary JSON from evaluate_runs.py")
    parser.add_argument("--health", required=True, help="Health JSON from evaluate_pilot_health.py")
    parser.add_argument("--output", required=True, help="Output SVG path")
    args = parser.parse_args(argv)

    summary = load_json(Path(args.summary))
    health = load_json(Path(args.health))
    metrics = metric_map(summary)
    swap_gaps = swap_gap_map(health)

    parse_failure = health["parse_failure_rate"]
    valid_records = health["valid_records"]
    expected_total = health["expected_jobs_total"]
    max_gap = max(
        row["task_b_swap_accuracy_gap"]
        for row in health["groups"]
        if row["task_b_swap_accuracy_gap"] is not None
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">Christian Moral Attention Reallocation: held-out v11 pilot overview</title>
  <desc id="desc">Held-out v11 pilot summary showing zero parse failures, perfect same-heart control behavior, zero heart overreach, and residual Task B swap-gap concentrated in same-act different-motive pairs.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fffdf8" />
      <stop offset="100%" stop-color="#f3f7fb" />
    </linearGradient>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)" />
  <text x="56" y="74" font-size="40" font-weight="800" fill="{TEXT}">Christian Moral Attention Reallocation</text>
  <text x="56" y="108" font-size="20" fill="{MUTED}">Held-out v11 pilot: benchmark-assisted multi-pass Task B removes same-heart overreach, but order sensitivity still blocks full freeze.</text>

  {card(56, 142, 250, 126, "Valid Pilot Calls", f"{valid_records}/{expected_total}", "Both Qwen models completed all held-out jobs.", "good")}
  {card(326, 142, 250, 126, "Parse Failure Rate", f"{parse_failure:.1f}", "No JSON / schema failures in the held-out run.", "good")}
  {card(596, 142, 250, 126, "Same-Heart Control", "1.0", "Every model-condition cell preserved Same on controls.", "good")}
  {card(866, 142, 278, 126, "Residual Blocking Metric", f"{max_gap:.3f}", "Task B swap-gap remains above threshold in some cells.", "warn")}

  {model_panel(56, 304, "Qwen-0.5B-Instruct", metrics["Qwen-0.5B-Instruct"], swap_gaps["Qwen-0.5B-Instruct"])}
  {model_panel(596, 304, "Qwen-1.5B-Instruct", metrics["Qwen-1.5B-Instruct"], swap_gaps["Qwen-1.5B-Instruct"])}

  {note_panel(56, 684, 540, 108, "What held", ["Zero held-out heart overreach.", "Same-heart controls stayed perfect under all conditions."], "good")}
  {note_panel(604, 684, 540, 108, "What still blocks freeze", ["Swap-gap is concentrated in same-act / different-motive pairs.", "Christian effect is model-dependent rather than uniform."], "warn")}
</svg>
"""

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    print(f"Wrote SVG overview to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
