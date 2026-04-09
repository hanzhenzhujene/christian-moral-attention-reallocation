# v11 Held-Out Pilot Readout

## Package

- benchmark: `data/study/paper_first_pilot_v1.json`
- jobs: `results/pilot_v11_fullpilot_jobs.jsonl`
- config: `configs/pilot_execution_v11_fullpilot.json`
- freeze: `results/pilot_v11_fullpilot_freeze_manifest.json`

## Global Result

- total calls: `120`
- valid records: `120`
- parse failure rate: `0.0`
- both models completed with `0` failure records

## Guardrail Outcome

The benchmark-summary-assisted multi-pass `v11` branch passed the held-out pilot on the main guardrail that had blocked earlier revisions:

- `same_heart_control_accuracy = 1.0` for all model-condition cells
- `heart_overreach_rate = 0.0` for all model-condition cells

This means the old failure mode, projecting outwardly worse action into inwardly worse heart on same-intention controls, is no longer present in this held-out pilot.

## Held-Out HSS

- `Qwen-0.5B-Instruct`
  - baseline: `0.8`
  - christian_heart: `0.4`
  - secular_matched: `0.8667`
- `Qwen-1.5B-Instruct`
  - baseline: `0.8`
  - christian_heart: `0.8667`
  - secular_matched: `0.6667`

The Christian effect is not uniform. It hurts HSS on the smaller model, helps slightly on the larger model, and does not dominate the secular matched condition.

## Residual Failure

The held-out pilot still fails the study health gate on `task_b swap accuracy gap`:

- `Qwen-0.5B-Instruct / christian_heart`: `0.4066`
- `Qwen-1.5B-Instruct / baseline`: `0.2727`
- `Qwen-1.5B-Instruct / christian_heart`: `0.1538`
- `Qwen-1.5B-Instruct / secular_matched`: `0.2525`

The pair-type breakdown shows that this residual asymmetry is concentrated in `same_act_different_motive`, not in same-heart controls.

## Current Read

`v11` is strong enough to treat as an upper-bound diagnostic for Task B:

- clean formatting
- clean relation-stage traces
- zero held-out heart overreach
- preserved motive sensitivity

But it is not yet clean enough to freeze as the final main Task B method, because order sensitivity still survives inside motive-sensitive pairs.
