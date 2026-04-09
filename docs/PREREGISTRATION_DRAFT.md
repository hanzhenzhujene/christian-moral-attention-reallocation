# Preregistration Draft

## Title

Christian Framing as Moral Attention Reallocation in Language Models

## Main Question

Does Christian heart-focused framing change what LLMs treat as morally diagnostic, especially under conditions where outward behavior is held constant and inward motive varies?

## Primary Hypotheses

### H1

Christian heart-focused framing increases Heart-Sensitivity Score relative to baseline.

### H2

Christian heart-focused framing increases `P(reason = motive)` relative to baseline.

### H3

Christian heart-focused framing decreases Surface-Overweighting Index relative to baseline.

### H4

If Christian heart-focused framing and secular matched framing produce similar improvements, the main mechanism is semantic reorientation rather than uniquely sacred authority.

## Primary Contrasts

- `baseline -> christian_heart`
- `baseline -> secular_matched`
- `christian_heart -> secular_matched`

All reported deltas are right-minus-left.

## Inclusion Criteria

- Items must be pairwise and textually interpretable on their own.
- For the MVP, items must be marked as included in the frozen benchmark file.
- Each model-condition pair must contain at most one run record per item.

## Exclusion Criteria

- malformed JSON outputs
- duplicated run records for the same model, condition, and item
- items discovered after freezing to violate structural invariants

## Primary Metrics

- Heart-Sensitivity Score
- Surface-Overweighting Index
- `P(reason = motive)`
- Cross-Task Consistency

## Secondary Metrics

- Task A accuracy
- Task B accuracy
- mean explanation length
- run-level position-bias diagnostics

## Uncertainty Estimation

- 95% bootstrap confidence intervals within model-condition groups
- paired bootstrap deltas on shared item sets for condition comparisons

## Interpretation Boundaries

- Improvements in response length or moralizing tone alone do not count as improvements in moral attention.
- A null Christian-vs-secular contrast is still theoretically informative if both differ from baseline in the same direction.
- Strong claims about general moral improvement require evidence beyond motive-sensitive subsets.
