# Robustness Checklist

## Before Data Collection

- Freeze prompt text for each condition and store the exact file paths used.
- Freeze the benchmark version and record a dataset hash or dated snapshot.
- Define the primary contrasts before running the full matrix:
  - `Christian heart-focused` minus `Baseline`
  - `Christian heart-focused` minus `Secular matched`
- Define the primary metrics before running:
  - Heart-Sensitivity Score
  - Surface-Overweighting Index
  - `P(reason = motive)`
  - motive-sensitive Cross-Task Consistency
  - Same-Heart Control Accuracy
  - Heart-Overreach Rate

## Benchmark Quality

- Run `scripts/validate_benchmark.py` before every full experiment run.
- Run `scripts/audit_benchmark.py` before every full experiment run.
- Run `scripts/check_release_gates.py` before any claimed freeze or main launch.
- Keep pairwise item templates structurally parallel.
- Avoid moralized wording inside the scenario text itself.
- Balance item domains so results are not driven by one social context.
- Balance `A`-worse and `B`-worse labels to reduce side-bias artifacts.
- Keep `source_story_id` values unique across main, pilot, and candidate Moral Stories pools.
- Stage new transformed Moral Stories items as `study_split=candidate` until they survive double annotation and adjudication.

## Annotation Quality

- Use at least 2 annotators for new HeartBench items before they are treated as locked gold.
- Use at least 2 annotators for new transformed Moral Stories candidate items before promoting them into the main split.
- Blind annotators to prompt condition and model identity.
- Prefer annotating Task B before Task A on motive-sensitive items.
- Compute pairwise agreement for Task A, Task B, and Task C.
- Review every disagreement that affects inclusion in the MVP.

## Prompting And Inference

- Use a fresh chat or independent call for every item-condition pair.
- Keep the output schema identical across conditions.
- Keep temperature and other decoding settings fixed within a study.
- Randomize or deterministically balance A/B order.
- Verify presented gold-label balance with `scripts/check_job_balance.py`.
- Cap explanations to one short sentence to reduce verbosity confounds.

## Analysis

- Report summary metrics with uncertainty intervals, not only point estimates.
- Use paired condition contrasts on shared item sets.
- Inspect response length separately so moral seriousness is not confused with better reasoning.
- Report both full benchmark results and motive-sensitive subset results.
- Report same-intention control results separately from motive-sensitive results.
- Separate pilot findings from final findings.
- Run `scripts/evaluate_pilot_health.py` on the held-out pilot before freezing the main run configuration.

## Interpretation

- Do not claim “Christian framing makes models more moral” unless overall evidence really supports that stronger claim.
- Prefer mechanism language:
  - attention reallocation
  - motive salience
  - semantic reorientation
- Treat null results as informative if rhetoric changes without attention shift.
- Treat gains on motive items as suspect if they are paired with higher heart-overreach on same-intention controls.
