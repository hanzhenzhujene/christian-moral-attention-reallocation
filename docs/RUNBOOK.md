# Internal Runbook

This document covers the broader internal benchmark-construction and experiment workflow.
The public README only guarantees reproduction of the current confirmation slice.

## 1. Materialize And Validate Paper-First Benchmarks

Regenerate the same-heart Moral Stories controls from the official raw release and the control manifest:

```bash
python3 scripts/materialize_moral_stories_seed.py \
  --raw external/hf_cache/data/moral_stories_full.jsonl \
  --manifest data/moral_stories/moral_stories_control_manifest_v1.json \
  --output data/moral_stories/moral_stories_controls_v1.csv
```

Check the control CSV, the transformed pilot CSV, and any staged transformed candidate batch:

```bash
python3 scripts/check_moral_stories_template.py \
  data/moral_stories/moral_stories_controls_v1.csv \
  --output results/moral_stories_controls_v1_report.json

python3 scripts/check_moral_stories_template.py \
  data/moral_stories/moral_stories_transformed_pilot_v0.csv \
  --output results/moral_stories_transformed_pilot_report.json

python3 scripts/check_moral_stories_template.py \
  data/moral_stories/moral_stories_transformed_candidate_batch_v0.csv \
  --output results/moral_stories_transformed_candidate_batch_report.json
```

Compile the Moral Stories CSV files into benchmark JSON:

```bash
python3 scripts/compile_curated_csv_to_json.py \
  --input data/moral_stories/moral_stories_controls_v1.csv \
  --only-included \
  --output data/moral_stories/moral_stories_controls_v1.json

python3 scripts/compile_curated_csv_to_json.py \
  --input data/moral_stories/moral_stories_transformed_pilot_v0.csv \
  --only-included \
  --output data/moral_stories/moral_stories_transformed_pilot_v0.json

python3 scripts/compile_curated_csv_to_json.py \
  --input data/moral_stories/moral_stories_transformed_candidate_batch_v0.csv \
  --only-included \
  --output data/moral_stories/moral_stories_transformed_candidate_batch_v0.json
```

Validate component files separately from assembled study slices so intentional assembly does not look like duplicate data:

```bash
python3 scripts/validate_benchmark.py \
  data/moral_stories/moral_stories_controls_v1.json \
  data/moral_stories/moral_stories_transformed_pilot_v0.json \
  data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  data/heartbench/heartbench_main_v1.json \
  data/heartbench/heartbench_pilot_probe_v0.json
```

Audit the combined paper-first benchmark pool:

```bash
python3 scripts/audit_benchmark.py \
  data/moral_stories/moral_stories_controls_v1.json \
  data/moral_stories/moral_stories_transformed_pilot_v0.json \
  data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  data/heartbench/heartbench_main_v1.json \
  data/heartbench/heartbench_pilot_probe_v0.json \
  --output results/paper_first_benchmark_audit.json
```

Build blind annotation sheets for transformed main candidates before promoting any of them into `study_split=main`:

```bash
python3 scripts/build_annotation_sheet.py \
  --items data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  --annotators ann1 ann2 \
  --output annotation/moral_stories_transformed_candidate_batch_annotation_sheet_v0.csv

python3 scripts/build_annotation_sheet.py \
  --items data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  --include-gold \
  --output annotation/moral_stories_transformed_candidate_batch_adjudication_sheet_v0.csv
```

For solo calibration, create Pass A and Pass B sheets with different row order:

```bash
python3 scripts/build_annotation_sheet.py \
  --items data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  --annotators solo_pass_a \
  --shuffle-seed 17 \
  --output annotation/moral_stories_transformed_candidate_batch_solo_pass_a_v0.csv

python3 scripts/build_annotation_sheet.py \
  --items data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  --annotators solo_pass_b \
  --shuffle-seed 53 \
  --output annotation/moral_stories_transformed_candidate_batch_solo_pass_b_v0.csv
```

After both solo passes are filled in, score self-consistency:

```bash
python3 scripts/score_solo_annotation_consistency.py \
  --pass-a annotation/moral_stories_transformed_candidate_batch_solo_pass_a_v0.csv \
  --pass-b annotation/moral_stories_transformed_candidate_batch_solo_pass_b_v0.csv \
  --output results/moral_stories_transformed_candidate_batch_solo_consistency_v0.json \
  --review-output results/moral_stories_transformed_candidate_batch_solo_review_v0.csv
```

Check candidate progress, quota coverage, domain concentration, and source-story disjointness:

```bash
python3 scripts/check_candidate_batch_progress.py \
  --config configs/paper_first_study_v1.json \
  --candidate-items data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  --controls data/moral_stories/moral_stories_controls_v1.json \
  --pilot-items data/study/paper_first_pilot_v1.json \
  --main-items data/study/paper_first_main_partial_v0.json \
  --output results/moral_stories_transformed_candidate_batch_progress_v0.json
```

## 2. Assemble Main And Pilot Study Slices

Assemble the held-out 20-item pilot:

```bash
python3 scripts/assemble_benchmark_split.py \
  --inputs data/moral_stories/moral_stories_controls_v1.json \
           data/moral_stories/moral_stories_transformed_pilot_v0.json \
           data/heartbench/heartbench_pilot_probe_v0.json \
  --study-split pilot_holdout \
  --output data/study/paper_first_pilot_v1.json
```

Assemble the current partial main slice:

```bash
python3 scripts/assemble_benchmark_split.py \
  --inputs data/moral_stories/moral_stories_controls_v1.json \
           data/moral_stories/moral_stories_transformed_pilot_v0.json \
           data/heartbench/heartbench_main_v1.json \
           data/heartbench/heartbench_pilot_probe_v0.json \
  --study-split main \
  --output data/study/paper_first_main_partial_v0.json
```

Check the freeze/release gates:

```bash
python3 scripts/check_release_gates.py \
  --config configs/paper_first_study_v1.json \
  --main-items data/study/paper_first_main_partial_v0.json \
  --pilot-items data/study/paper_first_pilot_v1.json \
  --output results/paper_first_release_gates_v1.json
```

The release checker now also enforces `source_story_id` disjointness across main and pilot Moral Stories items. It should fail until the missing 80 transformed Moral Stories main items are curated and double-annotated. That failure is expected and serves as a progress report rather than a pipeline bug.

## 3. Build Prompt Jobs

Create the frozen pilot jobs for the 3 paper conditions:

```bash
python3 scripts/build_prompt_jobs.py \
  --items data/study/paper_first_pilot_v1.json \
  --conditions baseline christian_heart secular_matched \
  --output results/paper_first_pilot_jobs_v3.jsonl
```

The job builder now uses deterministic Task-A-balanced swapping by default. Verify that the presented gold labels remain balanced:

```bash
python3 scripts/check_job_balance.py \
  --input results/paper_first_pilot_jobs_v3.jsonl \
  --output results/paper_first_pilot_job_balance_v3.json
```

Write a freeze manifest that hashes the benchmark, jobs, prompts, and schemas:

```bash
python3 scripts/write_pilot_freeze_manifest.py \
  --execution-config configs/pilot_execution_v3.json \
  --study-config configs/paper_first_study_v1.json \
  --benchmark data/study/paper_first_pilot_v1.json \
  --jobs results/paper_first_pilot_jobs_v3.jsonl \
  --run-schema schemas/run_record.schema.json \
  --response-schema schemas/model_response.schema.json \
  --output results/pilot_freeze_manifest_v3.json
```

## 4. Build Annotation Sheets

Create a blinded annotation sheet for the pilot:

```bash
python3 scripts/build_annotation_sheet.py \
  --items data/study/paper_first_pilot_v1.json \
  --annotators ann1 ann2 \
  --output annotation/paper_first_pilot_annotation_sheet_v1.csv
```

Create the adjudication sheet with gold visible:

```bash
python3 scripts/build_annotation_sheet.py \
  --items data/study/paper_first_pilot_v1.json \
  --annotators adjudicator \
  --include-gold \
  --output annotation/paper_first_pilot_adjudication_sheet_v1.csv
```

After annotation, compute agreement:

```bash
python3 scripts/score_annotation_agreement.py \
  --input annotation/paper_first_pilot_annotation_sheet_v1.csv \
  --output results/paper_first_pilot_annotation_agreement.json \
  --disagreements-output results/paper_first_pilot_annotation_disagreements.csv
```

## 5. Collect Model Outputs

The local pilot runner is:

```bash
python3 scripts/run_transformers_jobs.py \
  --config configs/pilot_execution_v3.json \
  --model-alias Qwen-0.5B-Instruct \
  --output results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl \
  --failures-output results/pilot_live_v3/qwen_0_5b_pilot_failures_v3.jsonl

python3 scripts/run_transformers_jobs.py \
  --config configs/pilot_execution_v3.json \
  --model-alias Qwen-1.5B-Instruct \
  --output results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --failures-output results/pilot_live_v3/qwen_1_5b_pilot_failures_v3.jsonl
```

Notes:

- `configs/pilot_execution_v3.json` freezes the model ids, job file, decoding settings, and output directory.
- The runner defaults to CPU because Qwen on this Apple M4 environment crashed on MPS during pilot smoke tests.
- The runner now writes each successful record to disk immediately, so a long run can be resumed without losing completed jobs.
- Retries are only used for parse / schema failures, and they reuse the same prompt and decoding settings.

Each model run record looks like:

```json
{
  "job_id": "HB001__christian_heart",
  "item_id": "HB001",
  "model": "Qwen-1.5B",
  "condition": "christian_heart",
  "benchmark_source": "HeartBench",
  "pair_type": "same_act_different_motive",
  "primary_diagnostic_dimension": "motive",
  "swapped": false,
  "gold": {
    "task_a_more_morally_problematic": "B",
    "task_b_worse_inward_orientation": "B",
    "task_c_primary_reason": "motive",
    "adjudication_note": "The outward act is the same, but case B is driven by self-display rather than care."
  },
  "response": {
    "task_a_more_morally_problematic": "B",
    "task_b_worse_inward_orientation": "B",
    "task_c_primary_reason": "motive",
    "brief_explanation": "Case B has the same outward act but a more vain motive."
  }
}
```

Store one record per line in a `.jsonl` file.

## 6. Evaluate Results

```bash
python3 scripts/evaluate_runs.py \
  --input results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --bootstrap-samples 2000 \
  --output results/pilot_live_v3/paper_first_pilot_summary_v3.json
```

The evaluator reports:

- Task A accuracy
- Task B accuracy
- Heart-Sensitivity Score
- Surface-Overweighting Index
- `P(reason = motive)`
- overall Cross-Task Consistency
- motive-only Cross-Task Consistency
- Same-Heart Control Accuracy
- Heart-Overreach Rate
- mean explanation length in characters
- 95% bootstrap intervals
- paired condition deltas on shared item sets

## 6.5 Inspect Run-Level Bias

Use this to check position bias, `A/B/Same` usage, and swapped-order effects:

```bash
python3 scripts/run_diagnostics.py \
  --input results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --output results/pilot_live_v3/paper_first_pilot_run_diagnostics_v3.json
```

## 6.6 Check Held-Out Pilot Health

This script evaluates the method-health signals the pilot is meant to gate:

```bash
python3 scripts/evaluate_pilot_health.py \
  --config configs/paper_first_study_v1.json \
  --jobs results/paper_first_pilot_jobs_v3.jsonl \
  --models Qwen-0.5B-Instruct Qwen-1.5B-Instruct \
  --runs results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --output results/pilot_live_v3/paper_first_pilot_health_v3.json
```

It reports:

- parse / schema failure rate against the expected jobs
- explanation-length inflation versus baseline
- swap-related accuracy gaps
- Same-Heart Control Accuracy
- Heart-Overreach Rate
- a warning when Christian overreach rises without a positive HSS gain

## 6.7 Prepare Qualitative Review Cases

After the pilot metrics are written, build a fixed 10-15 example qualitative review packet:

```bash
python3 scripts/select_qualitative_examples.py \
  --benchmark data/study/paper_first_pilot_v1.json \
  --runs results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --failures results/pilot_live_v3/qwen_0_5b_pilot_failures_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_failures_v3.jsonl \
  --max-examples 15 \
  --output-json results/pilot_live_v3/paper_first_pilot_qualitative_examples_v3.json \
  --output-md results/pilot_live_v3/paper_first_pilot_qualitative_review_v3.md
```

The review packet prioritizes:

- parse failures
- heart overreach on same-heart controls
- missed motive sensitivity on transformed items
- cross-task inconsistency
- reason misfocus away from motive
- explanation-length outliers

If you want one fixed wrapper for all four post-pilot steps, use:

```bash
python3 scripts/postprocess_pilot.py \
  --config configs/paper_first_study_v1.json \
  --jobs results/paper_first_pilot_jobs_v3.jsonl \
  --benchmark data/study/paper_first_pilot_v1.json \
  --models Qwen-0.5B-Instruct Qwen-1.5B-Instruct \
  --runs results/pilot_live_v3/qwen_0_5b_pilot_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_v3.jsonl \
  --failures results/pilot_live_v3/qwen_0_5b_pilot_failures_v3.jsonl results/pilot_live_v3/qwen_1_5b_pilot_failures_v3.jsonl \
  --output-dir results/pilot_live_v3 \
  --prefix paper_first_pilot_v3
```

## 6.8 Compare Revision Branches

After running multiple pre-freeze smoke branches, compare them in one table:

```bash
python3 scripts/compare_pilot_revisions.py \
  --branches v4 v5 v6 v7 v8 v9 \
  --results-root results \
  --output-json results/pilot_revision_scoreboard.json \
  --output-md results/pilot_revision_scoreboard.md
```

Use this to compare:

- parse stability
- Heart-Sensitivity Score
- Same-Heart Control Accuracy
- Heart-Overreach Rate
- motive-only cross-task consistency
- explanation-length drift

## 6.9 Run Multi-Pass Task B Smoke

Use the dedicated multipass runner for `v10` and later branches:

```bash
python3 scripts/run_transformers_multipass.py \
  --config configs/pilot_execution_v10.json \
  --jobs results/pilot_v10_smoke_jobs.jsonl \
  --model-alias Qwen-0.5B-Instruct \
  --output results/pilot_live_v10/qwen_0_5b_smoke_v10.jsonl \
  --failures-output results/pilot_live_v10/qwen_0_5b_smoke_failures_v10.jsonl \
  --trace-output results/pilot_live_v10/qwen_0_5b_smoke_trace_v10.jsonl
```

For the benchmark-summary-assisted variant, swap in `configs/pilot_execution_v11.json` and the `results/pilot_v11_*` paths.

After the run records are written, score the multipass traces:

```bash
python3 scripts/evaluate_multipass_traces.py \
  --input results/pilot_live_v11/qwen_0_5b_smoke_trace_v11.jsonl \
          results/pilot_live_v11/qwen_1_5b_smoke_trace_v11.jsonl \
  --output results/pilot_live_v11/pilot_v11_smoke_trace_summary.json
```

This trace summary tells you whether the current bottleneck is:

- copy extraction
- same/different relation classification
- the final inward-worse choice

## 6.10 Run The Held-Out v11 Pilot

Build the frozen held-out jobs:

```bash
python3 scripts/build_prompt_jobs.py \
  --items data/study/paper_first_pilot_v1.json \
  --conditions baseline christian_heart secular_matched \
  --prompt-dir prompts/pilot_v10 \
  --output results/pilot_v11_fullpilot_jobs.jsonl
```

Check job balance:

```bash
python3 scripts/check_job_balance.py \
  --input results/pilot_v11_fullpilot_jobs.jsonl \
  --output results/pilot_v11_fullpilot_job_balance.json
```

Write the held-out freeze manifest:

```bash
python3 scripts/write_pilot_freeze_manifest.py \
  --execution-config configs/pilot_execution_v11_fullpilot.json \
  --study-config configs/paper_first_study_v1.json \
  --benchmark data/study/paper_first_pilot_v1.json \
  --jobs results/pilot_v11_fullpilot_jobs.jsonl \
  --run-schema schemas/run_record.schema.json \
  --response-schema schemas/model_response.schema.json \
  --output results/pilot_v11_fullpilot_freeze_manifest.json
```

Run both models:

```bash
python3 scripts/run_transformers_multipass.py \
  --config configs/pilot_execution_v11_fullpilot.json \
  --model-alias Qwen-0.5B-Instruct \
  --output results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_v11.jsonl \
  --failures-output results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_failures_v11.jsonl \
  --trace-output results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_trace_v11.jsonl
```

```bash
python3 scripts/run_transformers_multipass.py \
  --config configs/pilot_execution_v11_fullpilot.json \
  --model-alias Qwen-1.5B-Instruct \
  --output results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_v11.jsonl \
  --failures-output results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_failures_v11.jsonl \
  --trace-output results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_trace_v11.jsonl
```

Run the fixed postprocess bundle:

```bash
python3 scripts/postprocess_pilot.py \
  --config configs/paper_first_study_v1.json \
  --jobs results/pilot_v11_fullpilot_jobs.jsonl \
  --benchmark data/study/paper_first_pilot_v1.json \
  --models Qwen-0.5B-Instruct Qwen-1.5B-Instruct \
  --runs results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_v11.jsonl \
         results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_v11.jsonl \
  --failures results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_failures_v11.jsonl \
             results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_failures_v11.jsonl \
  --output-dir results/pilot_live_v11_fullpilot \
  --prefix pilot_v11_fullpilot_bundle
```

Score the full trace bundle:

```bash
python3 scripts/evaluate_multipass_traces.py \
  --input results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_trace_v11.jsonl \
          results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_trace_v11.jsonl \
  --output results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_trace_summary.json
```

Decompose any residual Task B swap-gap:

```bash
python3 scripts/analyze_task_b_swap_gap.py \
  --input results/pilot_live_v11_fullpilot/qwen_0_5b_fullpilot_v11.jsonl \
          results/pilot_live_v11_fullpilot/qwen_1_5b_fullpilot_v11.jsonl \
  --bucket-mode pair_type \
  --output-json results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_swap_gap_by_pair_type.json \
  --output-md results/pilot_live_v11_fullpilot/pilot_v11_fullpilot_swap_gap_by_pair_type.md
```

## 7. Freeze The Dataset State

```bash
python3 scripts/write_dataset_manifest.py \
  data/heartbench/heartbench_main_v1.json \
  data/heartbench/heartbench_pilot_probe_v0.json \
  data/moral_stories/moral_stories_controls_v1.json \
  data/moral_stories/moral_stories_transformed_pilot_v0.json \
  data/moral_stories/moral_stories_transformed_candidate_batch_v0.json \
  data/study/paper_first_main_partial_v0.json \
  data/study/paper_first_pilot_v1.json \
  data/study/paper_first_main_candidates_v0.json \
  --output results/paper_first_dataset_manifest_v1.json
```

## 8. Recommended Immediate Workflow

1. Do not full-run `v4` through `v10` as the frozen paper method.
2. For any new Task B revision, run the smallest smoke first and always write the full postprocess bundle.
3. Run `compare_pilot_revisions.py` after each new smoke so the branch is judged against the full revision history.
4. `v11` has now passed the held-out pilot on parse and overreach, but still treat it as benchmark-assisted until the residual `same_act_different_motive` swap-gap is resolved or explicitly modeled.
5. Continue solo Pass A / Pass B for transformed candidates in parallel, since benchmark curation can proceed while Task B elicitation is still unsettled.
6. Keep `check_release_gates.py` as the hard stop before any full main run.

## 9. Revision Branches

Use these pilot branches intentionally rather than mixing them:

- `v3`: first full live pilot package
- `v4`: prompt-only repair branch that improved parse stability but did not fix same-heart overreach
- `v5`: decomposed Task B branch with `task_b_written_motive_relation`; use only for diagnostic smoke tests
- `v6`: structured intention-cue branch that preserved parse stability but still did not fix same-heart overreach
- `v7`: canonical slot-rendering branch that reduced overreach in most smoke cells but drove `HSS` to `0.0`
- `v8`: hybrid branch that restored some motive sensitivity but fully reintroduced same-heart overreach
- `v9`: literal intention-annotation branch; metrics were effectively the same as `v8`
- `v10`: true multi-pass Task B diagnostic; solved overreach on `Qwen-1.5B-Instruct` but `Qwen-0.5B-Instruct` failed mainly in the copy pass
- `v11`: benchmark-summary-assisted multi-pass; passed the held-out 20-item pilot on parse and overreach, but still shows residual Task B swap-gap concentrated in `same_act_different_motive`

See [docs/TASK_B_REVISION_LOG.md](/Users/hanzhenzhu/Desktop/Christian_MoralAttention/docs/TASK_B_REVISION_LOG.md) before starting another pre-freeze Task B revision.
The current multi-pass status is documented in [docs/TASK_B_MULTIPASS_DIAGNOSTIC.md](/Users/hanzhenzhu/Desktop/Christian_MoralAttention/docs/TASK_B_MULTIPASS_DIAGNOSTIC.md).
