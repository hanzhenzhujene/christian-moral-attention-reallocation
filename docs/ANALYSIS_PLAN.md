# Analysis Plan

## Primary Estimand

The central estimand is the change in motive sensitivity under Christian heart-focused framing relative to baseline.

Primary contrast:

- `Christian heart-focused` minus `Baseline`

Secondary mechanism contrast:

- `Christian heart-focused` minus `Secular matched paraphrase`

## Primary Metrics

### 1. Heart-Sensitivity Score

Definition:

- accuracy on motive-sensitive items using Task B gold labels

### 2. Surface-Overweighting Index

Definition:

- on surface-risk item types, the proportion of responses where the model either:
  - answers `Same` on inward-orientation judgment
  - or gives `task_c_primary_reason != motive`

### 3. Reason-Focus Probability

Definition:

- `P(task_c_primary_reason = motive)`

### 4. Cross-Task Consistency

Definition:

- proportion of items where Task A and Task B point to the same case
- report this primarily on motive-sensitive items, because same-intention control items should often have `Task B = Same`

### 5. Same-Heart Control Accuracy

Definition:

- on same-intention control items, accuracy of predicting `Task B = Same`

### 6. Heart-Overreach Rate

Definition:

- on same-intention control items, the proportion of responses that incorrectly infer `A` or `B` for inward orientation instead of `Same`

## Secondary Metrics

- Task A accuracy
- Task B accuracy
- overall cross-task consistency
- mean explanation length

## Uncertainty Estimation

- Use bootstrap confidence intervals over items within each model-condition group.
- Use paired bootstrap contrasts over shared items for condition comparisons.
- Default interval: 95%

## Default Contrasts

- `baseline -> christian_heart`
- `baseline -> secular_matched`
- `christian_heart -> secular_matched`

Interpret deltas as:

- positive delta on HSS or `P(reason = motive)` favors the right-hand condition
- negative delta on SOI favors the right-hand condition

## Reporting Convention

For each model:

1. report condition-level point estimates and confidence intervals
2. report paired condition deltas with confidence intervals
3. separately report motive-sensitive results and same-heart control results
4. treat `Heart-Overreach Rate` as a guardrail against spurious heart-reading
5. separately report response-length changes

## Interpretation Guardrails

- If HSS does not improve but response length increases, treat the result as rhetorical shift, not cognitive improvement.
- If Christian and secular matched conditions converge, interpret the effect as semantic reorientation rather than uniquely sacred authority.
- If effects appear only on easy items, avoid claiming broad heart-sensitive reasoning.
- If Christian framing raises HSS but also raises Heart-Overreach Rate on same-intention controls, interpret the change as a noisier tendency to impute inward corruption rather than cleaner moral attention.
