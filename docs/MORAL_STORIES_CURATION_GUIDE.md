# Moral Stories Curation Guide

## Goal

Curate a 120-item Moral Stories subset that is useful for testing moral attention reallocation, not just generic moral accuracy.

## Target Composition

- 80 motive-diagnostic items
- 20 consequence-diagnostic items
- 20 rule-diagnostic items

Use a small same-intention control slice alongside the main motive-diagnostic set:

- same stated intention
- moral action versus immoral action
- gold `Task B = Same`
- use these items to detect heart overreach rather than heart sensitivity

Within the 80 motive-diagnostic items, prefer:

- same outward act, different motive
- same norm compliance, different heart posture
- same consequence, different motive

## Inclusion Rules

- Everyday social situations
- Short enough to compare quickly
- Clear enough that motive can be inferred from the text
- Adaptable to parallel A/B structure
- Useful for forced-choice Task A / B / C labeling

## Exclusion Rules

- Heavy dependence on niche world knowledge
- Ambiguous or underspecified intention
- More than one major variable changing at once without control
- Stylized or unnatural wording
- Cases that already contain answer-giving moral labels

## Transformation Rules

1. Keep the original everyday scenario recognizable.
2. Make the A/B pair structurally parallel.
3. Move framing differences into the prompt condition, not the item text.
4. Explicitly track what stays constant across A and B.
5. Keep explanation-bearing summaries separate from the displayed case text.

## What To Fill In The CSV

For every selected item:

- assign `source_story_id`
- assign `domain`
- assign `difficulty`
- choose `pair_type`
- choose `primary_diagnostic_dimension`
- choose `benchmark_role`
- choose `study_split`
- write parallel `case_a_text` and `case_b_text`
- write case summaries for act, motive, consequence, and rule
- assign gold labels for Tasks A, B, and C
- document `held_constant`
- document `changed_dimension`
- write a short adjudication note
- mark `include_in_mvp=yes` only when the item is clean enough for the final subset

For same-intention control items:

- keep `case_a_motive_summary` and `case_b_motive_summary` identical
- keep `case_a_rule_summary` and `case_b_rule_summary` identical
- default `gold_task_b` to `Same`
- choose `gold_task_c` from `rule`, `outward_act`, or `consequence`, not `motive`
- set `benchmark_role=same_heart_control`

For transformed motive-sensitive items:

- set `benchmark_role=motive_main`
- keep `primary_diagnostic_dimension=motive`
- start new transformed items at `study_split=candidate`
- promote to `study_split=main` only after double annotation and adjudication
- reserve `study_split=pilot_holdout` for the held-out pilot items
- do not allow `gold_task_b=Same`
- keep `source_story_id` disjoint across `candidate`, `pilot_holdout`, and `main`

## Quality Targets

- balance `A`-worse and `B`-worse labels as much as practical
- avoid overconcentration in one domain such as school-only or workplace-only
- keep easy items from dominating the benchmark
- reserve `Same` for truly indeterminate items, not weakly written ones

## Review Flow

1. Curate candidate rows in the CSV.
2. Run `scripts/check_moral_stories_template.py`.
3. Compile the included rows into JSON.
4. Run `scripts/validate_benchmark.py`.
5. Run `scripts/audit_benchmark.py`.
6. Double-annotate difficult rows before freezing the subset.
7. Promote only approved transformed candidates into the main split.
8. Check the assembled study with `scripts/check_release_gates.py`.
