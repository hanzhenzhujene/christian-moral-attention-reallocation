# Task B Multi-Pass Diagnostic

## Why This Exists

Single-call prompt revisions `v4` through `v9` now show a stable tradeoff:

- branches that recover motive sensitivity tend to project outwardly worse action back into inward motive
- branches that suppress that projection tend to collapse heart sensitivity

This document defines the next pre-freeze revision as a **multi-pass diagnostic**, not another single-call prompt tweak.

## Goal

Separate three subproblems that the single-call setup currently conflates:

1. Can the model identify the written intention text for each case?
2. Can the model tell whether the written intentions are the same or different?
3. Only if they differ, can the model judge which written intention is inwardly worse?

## Proposed Pipeline

### Pass 1: Intention Copy

Input:

- full Case A
- full Case B

Output:

- `case_a_written_intention_copy`
- `case_b_written_intention_copy`

Rule:

- the model must copy the intention clause as literally as possible from each case
- no comparison yet

### Pass 2: Intention Relation

Input:

- the copied intention strings from Pass 1

Output:

- `task_b_written_motive_relation`: `same` or `different`

Rule:

- this pass compares only the copied strings
- no action, consequence, or rule information is shown

### Pass 3: Conditional Inward-Worse Judgment

Input:

- copied intention strings
- relation label from Pass 2

Output:

- `task_b_worse_inward_orientation`

Rule:

- if relation is `same`, force `task_b_worse_inward_orientation = Same`
- if relation is `different`, ask the model which written intention is inwardly worse

## Why This Is Better Than v5

`v5` added one more field inside the same response object, but it still let the model solve everything in a single contaminated pass.

This multi-pass design is different because:

- copying is isolated from comparison
- relation judgment is isolated from the full narrative
- the `Same` gate can be externally enforced after Pass 2

## Minimal Smoke Design

Run the first multi-pass smoke on the same 4-item pack used for `v7` through `v9`:

- 1 HeartBench motive-sensitive item
- 2 Moral Stories transformed motive-sensitive items
- 1 Moral Stories same-heart control

Models:

- `Qwen-0.5B-Instruct`
- `Qwen-1.5B-Instruct`

Conditions:

- `baseline`
- `christian_heart`
- `secular_matched`

## Success Criteria

Treat the next revision as promising only if all of these move in the right direction:

- parse failure rate stays near `0`
- copied intention strings are faithful enough to support relation checks
- same-heart control accuracy rises above the `v8` / `v9` floor
- heart-overreach rate falls without driving `HSS` back to `0`

## Non-Goals

- This is not yet the full paper method.
- This should not be merged into the main benchmark pipeline before it passes smoke.
- It should not change the paper's frozen primary metrics.

## Initial Outcome

Two concrete branches now exist:

- `v10`: true model-copy multi-pass
- `v11`: benchmark-summary-assisted multi-pass

Current read:

- `v10` solved the core overreach problem on `Qwen-1.5B-Instruct`, but `Qwen-0.5B-Instruct` remained fragile in the intention-copy pass.
- `v11` externalized that copy step and produced `parse_failure_rate = 0.0`, `same_heart_control_accuracy = 1.0`, and `heart_overreach_rate = 0.0` for both Qwen models on the 4-item smoke.

That means the next question is no longer whether multi-pass can work at all.
It is whether the benchmark-assisted `v11` variant is acceptable as the main Task B method, or whether it should be treated as a diagnostic upper bound.

## Held-Out Pilot Outcome

`v11` has now been run on the frozen 20-item held-out pilot, not just the 4-item smoke.

Held-out package:

- `configs/pilot_execution_v11_fullpilot.json`
- `results/pilot_v11_fullpilot_jobs.jsonl`
- `results/pilot_v11_fullpilot_freeze_manifest.json`

Held-out result bundle:

- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_bundle_health.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_bundle_summary.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_trace_summary.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_bundle_qualitative_review.md`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_swap_gap_by_pair_type.md`

What held up:

- both Qwen models completed all jobs with `parse_failure_rate = 0.0`
- both models achieved `same_heart_control_accuracy = 1.0`
- both models achieved `heart_overreach_rate = 0.0`
- relation-stage traces remained clean across the full held-out pilot

What did not fully clear:

- the held-out pilot still fails the study gate on `task_b swap accuracy gap`
- the swap-gap breakdown localizes the remaining asymmetry to `same_act_different_motive`
- same-heart controls are no longer the problem under `v11`

Substantive reading:

- `v11` is now credible as an **upper-bound diagnostic** for Task B
- it demonstrates that decomposition plus explicit intention evidence can suppress heart overreach without collapsing heart sensitivity
- it does **not** yet justify freezing `v11` as the paper's final main Task B method, because order sensitivity still survives in motive-sensitive pairs

## Updated Next Question

The next question is now narrower than before:

1. can the `same_act_different_motive` swap-gap be reduced without reintroducing overreach?
2. if not, should the main paper treat `v11` as an upper-bound diagnostic and score the main Task B claim with additional order-robustness checks?

That is a much better failure mode than the earlier branches.
The pipeline no longer appears fundamentally contaminated by outward-action projection on same-heart controls.
