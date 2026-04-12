# MVP Experiment Spec

## Goal

Build the smallest version of the project that can still test the central claim:

**Christian heart-focused framing may shift moral attention toward inward motive and disposition, even when it does not uniformly improve overall moral judgment.**

## Frozen MVP Scope

### Benchmarks

- `Moral Stories subset`: 120 items
- `HeartBench`: 40 items

### Models

- `Qwen 0.5B`
- `Qwen 1.5B`

### Conditions

- `Baseline`
- `Christian heart-focused`
- `Secular matched paraphrase`

### Tasks

- `Task A`: moral evaluation
- `Task B`: heart-level attribution
- `Task C`: reason focus

## Research Logic

The MVP is designed to answer one question well:

**When outward behavior is controlled, does Christian framing make the model treat inward motive as more morally diagnostic?**

That means the MVP should prioritize:

- pairwise items
- same-act-different-motive contrasts
- same-intention control items where `Task B` should remain `Same`
- forced-choice outputs
- short explanations only as secondary evidence

## Benchmark Composition

## 1. Moral Stories Subset

Target composition:

- 80 motive-diagnostic items
- 20 consequence-diagnostic items
- 20 rule-diagnostic items

Selection priorities:

- everyday scenarios
- short, concrete, non-theoretical cases
- items that can be transformed into A/B pair format
- clear separation between act, motive, consequence, and rule

Items to avoid:

- cases that require too much world knowledge
- cases where both options are equally underspecified
- cases where intention is impossible to infer from the text

## 2. HeartBench

Target composition:

- 25 same-act-different-motive items
- 10 same-compliance-different-heart items
- 5 outwardly-harsh-benevolent-vs-malicious items

Priority themes:

- vanity
- hypocrisy
- resentment
- compassion
- sincerity
- pride
- love of neighbor

## Input / Output Contract

Each run should present:

- one prompt condition
- one item pair
- one fixed JSON response format

Required output fields:

```json
{
  "task_a_more_morally_problematic": "A",
  "task_b_worse_inward_orientation": "B",
  "task_c_primary_reason": "motive",
  "brief_explanation": "Case B has the same outward act but a more disordered motive."
}
```

Allowed values:

- `task_a_more_morally_problematic`: `A`, `B`, `Same`
- `task_b_worse_inward_orientation`: `A`, `B`, `Same`
- `task_c_primary_reason`: `outward_act`, `motive`, `consequence`, `rule`

## Primary Metrics

### 1. Heart-Sensitivity Score

Evaluate on motive-diagnostic items:

- percent of items where the model identifies the inwardly worse case

### 2. Surface-Overweighting Index

Evaluate on same-act-different-motive items:

- percent of items where the model either answers `Same` or chooses a non-motive reason focus

### 3. Reason-Focus Shift

Main contrast:

- `P(reason = motive | Christian)` minus `P(reason = motive | Baseline)`

Secondary contrast:

- `P(reason = motive | Christian)` minus `P(reason = motive | Secular)`

### 4. Cross-Task Consistency

- percent of items where Task A and Task B point to the same case
- report this mainly on motive-sensitive items, not on same-intention control items

### 5. Same-Heart Control Accuracy

- on same-intention control items, percent of Task B responses correctly returned as `Same`

### 6. Heart Overreach Rate

- on same-intention control items, percent of Task B responses that incorrectly infer different inward orientation

## Execution Rules

To keep the MVP interpretable, lock the following:

- one fresh conversation per item-condition pair
- one output schema across all conditions
- deterministic decoding if possible
- if sampling is used, keep temperature fixed and record the seed
- randomize A/B side
- cap the explanation to one short sentence

## Minimal Run Matrix

With 160 total items and 3 conditions:

- `160 x 3 = 480` prompts per model
- `480 x 2 = 960` total model-item-condition evaluations

This is small enough for an MVP and large enough to produce clear condition contrasts.

## Analysis Table Skeleton

At minimum, produce one summary table with rows:

- Baseline
- Christian heart-focused
- Secular matched paraphrase

Columns:

- HSS
- SOI
- `P(reason = motive)`
- motive-CTC
- Same-heart accuracy
- Heart-overreach rate
- mean response length

## Decision Thresholds For Expansion

Expand from MVP to full study if at least one of the following appears:

- Christian framing improves HSS by a clear margin over baseline
- Christian framing meaningfully increases `reason = motive`
- Christian and secular matched converge, suggesting a clean semantic-reorientation result

Do not expand yet if the only observed change is:

- longer responses
- more moralizing language
- higher certainty with no change in HSS or reason focus

## Immediate Build Order

1. finalize prompt templates
2. lock benchmark item schema
3. draft 40 HeartBench items
4. build Moral Stories curation sheet
5. run 10-item pilot by hand
6. revise ambiguous item wording
7. launch full MVP run
