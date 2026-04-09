# Task B Revision Log

## Purpose

This log records pre-freeze revisions to Task B elicitation and what each revision did or did not fix.
The goal is to avoid ad hoc method drift after seeing pilot behavior.

## v3: Fixed four-field prompt, text-only cases

Artifacts:

- `results/pilot_live_v3/paper_first_pilot_v3_health.json`
- `results/pilot_live_v3/paper_first_pilot_v3_summary.json`
- `results/pilot_live_v3/paper_first_pilot_v3_qualitative_review.md`

What happened:

- `Qwen-0.5B-Instruct` had substantial parse / schema failure.
- `Qwen-1.5B-Instruct` had stable JSON output.
- Both models failed the same-heart controls across all three conditions.
- `same_heart_control_accuracy = 0.0`
- `heart_overreach_rate = 1.0`

Interpretation:

- The core problem was not only formatting.
- Task B was being read as "which case is morally worse overall" rather than "which case reveals worse inward orientation."

## v4: Stronger Task B wording, still four-field output

Artifacts:

- `prompts/pilot_v4/`
- `results/pilot_live_v4/pilot_v4_smoke_bundle_health.json`
- `results/pilot_live_v4/pilot_v4_smoke_bundle_qualitative_review.md`

What changed:

- Explicitly stated that Task B must be `Same` when written inward orientation is the same.
- Repeated that action / consequence / rule differences should not determine Task B.
- Added a same-intention example.

What happened in smoke testing:

- Parse failures dropped to `0`.
- Same-heart overreach did not improve.
- Models still answered `A` or `B` instead of `Same` on same-intention controls.

Interpretation:

- Prompt-only clarification helped formatting.
- Prompt-only clarification did not change the underlying read of the control items.

## v5: Decomposed Task B with written-motive relation

Artifacts:

- `prompts/pilot_v5/`
- `schemas/model_response_decomposed.schema.json`
- `schemas/run_record_decomposed.schema.json`
- `results/pilot_live_v5/pilot_v5_smoke_bundle_health.json`
- `results/pilot_live_v5/pilot_v5_smoke_bundle_run_diagnostics.json`
- `results/pilot_live_v5/pilot_v5_smoke_bundle_qualitative_review.md`

What changed:

- Added `task_b_written_motive_relation` with values `same` or `different`.
- Added an explicit gating rule:
  - if relation is `same`, Task B must be `Same`
  - if relation is `different`, Task B must be `A` or `B`
- Added diagnostics for relation distribution and relation consistency.

What happened in smoke testing:

- `Qwen-0.5B-Instruct` became much less format-stable.
- `Qwen-1.5B-Instruct` stayed partly usable but still marked same-intention controls as `different`.
- When the relation field was present, models usually obeyed the internal consistency rule.
- The real failure moved one step earlier: the model now often misclassified the written-motive relation itself.

Interpretation:

- Decomposition did not solve the main problem.
- The model is not just failing to compare inward orientation.
- It is often failing to identify the written inward relation correctly in same-intention controls.
- For smaller models, the extra field also increases output fragility.

## Current Recommendation

Do not full-run `v4` or `v5`.

The next revision should preserve the four-field main output and target the *input side* of Task B, not the output side.

Most likely next options:

1. Keep four-field output, but add a much stronger "locate the written intention / because-clause first" instruction.
2. Keep four-field output, but provide a compact structured intention cue drawn from the benchmark item metadata.
3. Run that next revision first on a tiny two-item smoke pack with one motive-sensitive item and one same-heart control before any full pilot rerun.

## v6: Structured intention cue, still four-field output

Artifacts:

- `prompts/pilot_v6/`
- `results/pilot_live_v6/pilot_v6_smoke_bundle_health.json`
- `results/pilot_live_v6/pilot_v6_smoke_bundle_summary.json`
- `results/pilot_live_v6/pilot_v6_smoke_bundle_qualitative_review.md`

What changed:

- Kept the original four-field output schema.
- Added a structured Task B cue using benchmark-native `motive_summary` lines:
  - `Case A stated motive/intention: ...`
  - `Case B stated motive/intention: ...`
- Explicitly told the model to use those cue lines for Task B and to ignore action / consequence / rule differences when deciding inward orientation.

What happened in smoke testing:

- Parse stability was good for both `Qwen-0.5B-Instruct` and `Qwen-1.5B-Instruct`.
- Same-heart control behavior still did not improve.
- Both models still marked the same-intention control as inwardly different.
- In several responses, the model appears to reinterpret the cue itself instead of following it literally.

Interpretation:

- The problem is no longer primarily output formatting.
- It is also no longer just that the model ignores a verbal instruction to answer `Same`.
- Even when the written intention cue is made explicit, the model still tends to read outwardly worse cases as inwardly worse.

## v7: Canonical slot rendering

Artifacts:

- `prompts/pilot_v7/`
- `results/pilot_live_v7/pilot_v7_smoke_bundle_health.json`
- `results/pilot_live_v7/pilot_v7_smoke_bundle_summary.json`
- `results/pilot_live_v7/pilot_v7_smoke_bundle_qualitative_review.md`

What changed:

- Re-rendered each case into canonical slots:
  - situation
  - stated intention
  - action
  - consequence
  - governing norm
- Kept the original four-field output schema.

What happened in smoke testing:

- Parse stability stayed at `0.0` failure rate.
- `Qwen-1.5B-Instruct` and the non-baseline `Qwen-0.5B-Instruct` conditions stopped overreaching on the single same-heart smoke control:
  - `same_heart_control_accuracy = 1.0`
  - `heart_overreach_rate = 0.0`
- But `heart_sensitivity_score = 0.0` across all six model-condition cells.

Interpretation:

- Canonical slot rendering can suppress direct action-to-heart projection.
- But it also over-corrects and collapses discrimination on motive-sensitive items.
- In practice, `v7` turns Task B into "answer Same very often," which is not usable as the main design.

## v8: Hybrid branch, full cases for Task A/C plus intention block for Task B

Artifacts:

- `prompts/pilot_v8/`
- `results/pilot_live_v8/pilot_v8_smoke_bundle_health.json`
- `results/pilot_live_v8/pilot_v8_smoke_bundle_summary.json`
- `results/pilot_live_v8/pilot_v8_smoke_bundle_qualitative_review.md`

What changed:

- Restored full raw cases for Task A and Task C.
- Added a separate intention-only block for Task B.
- Kept the original four-field output schema.
- Parser normalization was expanded so outputs like `inwardly worse` map to `motive` instead of counting as parse failures.

What happened in smoke testing:

- Parse stability was again `0.0`.
- Motive sensitivity partly returned:
  - `HSS = 0.6667 / 0.3333 / 0.6667` for baseline / christian / secular on both Qwen models in this smoke pack.
- Same-heart behavior collapsed again in all six model-condition cells:
  - `same_heart_control_accuracy = 0.0`
  - `heart_overreach_rate = 1.0`

Interpretation:

- Once the full narrative is back in view, the models immediately start inferring inward corruption from outwardly worse action.
- The intention block is not being treated as authoritative evidence for Task B.
- `v8` restores sensitivity by reintroducing the same contamination problem we were trying to remove.

## v9: Literal intention-annotation branch

Artifacts:

- `prompts/pilot_v9/`
- `configs/pilot_execution_v9.json`
- `results/pilot_live_v9/pilot_v9_smoke_bundle_health.json`
- `results/pilot_live_v9/pilot_v9_smoke_bundle_summary.json`
- `results/pilot_live_v9/pilot_v9_smoke_bundle_qualitative_review.md`
- `results/pilot_revision_scoreboard.md`

What changed:

- Kept full cases for Task A and Task C.
- Reframed Task B as a literal annotation of the written intention lines.
- Added an explicit rule:
  - if the two intention texts are the same in meaning, answer `Same`
  - do not infer hidden motive from action / consequence / rule

What happened in smoke testing:

- Parse stability remained `0.0`.
- The metric profile was effectively the same as `v8`:
  - `HSS = 0.6667 / 0.3333 / 0.6667` for baseline / christian / secular on both Qwen models in this smoke pack
  - `same_heart_control_accuracy = 0.0`
  - `heart_overreach_rate = 1.0`
- Qualitatively, the models continued to describe the outwardly worse case as showing a more manipulative intention even when the intention strings were identical.

Interpretation:

- Making the intention block more literal did not change the underlying behavior.
- The model is not just misunderstanding a label.
- It is actively overriding the written intention evidence with an action-to-heart inference.

## v10: True multi-pass Task B diagnostic

Artifacts:

- `configs/pilot_execution_v10.json`
- `scripts/run_transformers_multipass.py`
- `scripts/evaluate_multipass_traces.py`
- `results/pilot_live_v10/pilot_v10_smoke_bundle_health.json`
- `results/pilot_live_v10/pilot_v10_smoke_bundle_summary.json`
- `results/pilot_live_v10/pilot_v10_smoke_trace_summary.json`

What changed:

- Split Task B into multiple passes:
  - Pass 1: copy written intention text from the full cases
  - Pass 2: classify copied intentions as `same` or `different`
  - Pass 3: only if `different`, choose which written intention is inwardly worse
- Kept Task A and Task C in a separate pass with the full cases.
- Wrote standard run-record JSONL for compatibility with the existing evaluators.
- Wrote trace JSONL so copy / relation / final-gate behavior can be inspected separately.

What happened in smoke testing:

- `Qwen-1.5B-Instruct` became the first branch to satisfy the core Task B tradeoff on the 4-item smoke:
  - `parse_failure_rate = 0.0` for the model-level run
  - `same_heart_control_accuracy = 1.0`
  - `heart_overreach_rate = 0.0`
  - `HSS = 1.0 / 0.6667 / 1.0` for baseline / christian / secular
- `Qwen-0.5B-Instruct` failed mainly in Pass 1 copy:
  - after parser cleanup, branch-level `parse_failure_rate = 0.125`
  - all remaining failures were the same-heart control item failing to copy the second intention text
- The trace summary showed a clean separation:
  - where copies existed, relation accuracy was `1.0`
  - the small-model bottleneck was copy extraction, not relation comparison

Interpretation:

- Multi-pass decomposition is the first revision that actually breaks the earlier fork on the larger model.
- The main unresolved problem is now narrower:
  - can smaller models survive the copy pass?
- So the bottleneck has shifted from "single-call moral contamination" to "pass-1 extraction fragility."

## v11: Benchmark-summary-assisted multi-pass

Artifacts:

- `configs/pilot_execution_v11.json`
- `results/pilot_live_v11/pilot_v11_smoke_bundle_health.json`
- `results/pilot_live_v11/pilot_v11_smoke_bundle_summary.json`
- `results/pilot_live_v11/pilot_v11_smoke_trace_summary.json`
- `configs/pilot_execution_v11_fullpilot.json`
- `results/pilot_v11_fullpilot_jobs.jsonl`
- `results/pilot_v11_fullpilot_freeze_manifest.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_bundle_health.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_bundle_summary.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_trace_summary.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_swap_gap_by_pair_type.json`
- `results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_swap_gap_by_pair_type.md`

What changed:

- Kept the `v10` multi-pass architecture.
- Replaced model-generated Pass 1 copies with benchmark-native `motive_summary` strings.
- Left Pass 2 relation and Pass 3 inward-worse judgment inside the model.

What happened in smoke testing:

- Both models reached `parse_failure_rate = 0.0`.
- Both models also reached:
  - `same_heart_control_accuracy = 1.0`
  - `heart_overreach_rate = 0.0`
- `Qwen-1.5B-Instruct` stayed strong:
  - `HSS = 1.0 / 0.6667 / 0.6667`
- `Qwen-0.5B-Instruct` improved from `v10` by eliminating copy-pass failures:
  - `HSS = 0.6667 / 0.6667 / 0.3333`
- The remaining health failure in this tiny smoke was no longer parse or overreach; it was swap-gap sensitivity:
  - `task_b swap accuracy gap = 0.5` for every model-condition cell on a 4-item smoke pack

Interpretation:

- Externalizing the copy pass removes the small-model extraction bottleneck.
- `v11` is currently the strongest-performing branch in terms of the main Task B target:
  - no overreach
  - preserved motive sensitivity
  - no parse failures
- But it changes the task more than `v10`, because the model now consumes benchmark-structured intention summaries rather than extracting intention from the raw case text itself.

### Held-Out 20-Item Pilot Outcome

What changed:

- Promoted `v11` from the 4-item smoke pack to the frozen 20-item held-out pilot:
  - `20 items x 3 conditions x 2 models = 120 calls`
- Kept the same benchmark-summary-assisted multi-pass design:
  - benchmark `motive_summary` enters the pipeline as the written-intention evidence
  - the model still performs relation judgment and conditional inward-worse judgment
- Froze the held-out package with a dedicated config, jobs file, and manifest before running.

What happened in the held-out pilot:

- Both models completed all `60/60` condition-item jobs with:
  - `parse_failure_rate = 0.0`
  - `same_heart_control_accuracy = 1.0`
  - `heart_overreach_rate = 0.0`
- Trace summaries were fully clean:
  - `copy_relation_acc = 1.0`
  - `relation_acc = 1.0`
  - `control_same = 1.0`
- This confirms that the core same-heart failure from `v3` through `v9` is actually solved in the benchmark-assisted multi-pass regime, not just hidden on the smoke pack.

Held-out HSS by model / condition:

- `Qwen-0.5B-Instruct`
  - baseline: `0.8`
  - christian_heart: `0.4`
  - secular_matched: `0.8667`
- `Qwen-1.5B-Instruct`
  - baseline: `0.8`
  - christian_heart: `0.8667`
  - secular_matched: `0.6667`

Held-out interpretation:

- `v11` is strong as a Task B guardrail method:
  - no parse failures
  - no heart overreach
  - perfect same-heart control performance in this held-out pilot
- But the substantive framing effect is not stable:
  - Christian hurts HSS for `Qwen-0.5B-Instruct`
  - Christian helps HSS slightly for `Qwen-1.5B-Instruct`
  - secular matched is strongest on `Qwen-0.5B-Instruct`
- So the main claim at this stage is not "Christian framing wins under `v11`."
- The main claim is that **benchmark-assisted decomposition can suppress heart overreach without collapsing motive sensitivity.**

Residual problem after the held-out pilot:

- Pilot health still fails on `task_b swap accuracy gap` for multiple model-condition cells.
- The new swap-gap breakdown shows that the residual asymmetry is concentrated in `same_act_different_motive`, not in same-heart controls:
  - `Qwen-1.5B-Instruct / baseline`: `same_act_different_motive` gap `0.5`
  - `Qwen-1.5B-Instruct / christian_heart`: `0.2857`
  - `Qwen-1.5B-Instruct / secular_matched`: `0.25`
  - `Qwen-0.5B-Instruct / christian_heart`: `0.3714`
- That means `v11` solved the overreach problem but not the full order-sensitivity problem.

## Cross-Branch Pattern

The revision scoreboard is in:

- `results/pilot_revision_scoreboard.json`
- `results/pilot_revision_scoreboard.md`

The pattern from `v4` through `v11` is now clearer:

- `v4` to `v6`: prompt-only and prompt-plus-cue branches improve formatting but leave same-heart overreach intact.
- `v7`: representation-heavy rendering can suppress overreach, but it also drives heart sensitivity to zero.
- `v8` and `v9`: hybrid and literal-annotation branches recover motive sensitivity, but same-heart overreach immediately returns.
- `v10`: multi-pass decomposition works on `Qwen-1.5B-Instruct`, but `Qwen-0.5B-Instruct` fails mainly in the intention-copy pass.
- `v11`: benchmark-summary-assisted multi-pass removes the copy bottleneck and is the strongest current branch, but it is also the most benchmark-assisted.

This is no longer just a prompt-engineering problem.
It is now a choice about **where intention evidence should enter the pipeline**, plus a residual question about **swap robustness inside motive-sensitive pairs**.

## Updated Recommendation

Do not full-run `v4` through `v10` as the frozen paper method.

Treat `v11` as the strongest current candidate and as an upper-bound diagnostic, not yet as the final paper task.

The next high-value step is:

1. Keep `v11` as the current upper-bound diagnostic for Task B.
2. Diagnose and reduce the remaining `same_act_different_motive` swap-gap before any benchmark freeze.
3. Decide whether `v11` should be framed as:
   - a benchmark-assisted diagnostic upper bound, or
   - the actual main Task B method.
4. If a less assisted final task is still required, use `v10` as the purer base and only try to replace its copy pass with a narrower extraction aid rather than another single-call prompt rewrite.
5. If swap-gap remains even after targeted fixes, consider scoring both A/B orders for `same_act_different_motive` items as a robustness diagnostic rather than treating a single order as sufficient.

Rationale:

- `v10` already shows that decomposition can solve the core overreach problem on the larger model.
- `v11` shows that the remaining small-model bottleneck is largely the extraction step, not the relation or inward-worse step.
- The held-out `v11` pilot now shows that the remaining methodological question is mostly about **order robustness and task validity**, not parsing or same-heart contamination.

## Freeze Discipline

- `v3` through `v11` should be treated as separate pilot revisions.
- Main benchmark freeze is still blocked.
- No main-run claims should be made from these pilot variants.
