# Christian Moral Attention Reallocation

![Release](https://img.shields.io/github/v/release/hanzhenzhujene/christian-moral-attention-reallocation?style=flat-square)
![Status](https://img.shields.io/badge/status-pre--freeze%20confirmation%20artifact-0f766e?style=flat-square)
![Public Scope](https://img.shields.io/badge/public%20scope-Qwen--1.5B%20confirmation%20slice-12805c?style=flat-square)
![License](https://img.shields.io/badge/license-Apache--2.0-2563eb?style=flat-square)

> This repo does not show that Christian prompting makes LLMs more moral overall. It shows that, on a clean same-act confirmation slice, Christian heart-focused framing directionally improves inward-motive judgment without increasing same-heart overreach.

## Abstract

This repository studies a narrow mechanistic question about moral cognition in language models: not whether Christian prompting makes a model "more moral" overall, but whether Christian heart-focused framing changes what the model treats as morally diagnostic. The benchmark logic centers on pairwise moral cases with three tasks: overall moral verdict (Task A), inward-orientation judgment (Task B), and reason focus (Task C). The key design uses same-act-different-motive pairs together with same-heart controls, so motive sensitivity can be separated from false projection of outwardly worse action into inwardly worse heart. On a 63-item Qwen-1.5B-Instruct confirmation slice, Christian heart-focused framing improved Task B accuracy from `0.8889` to `0.9524` and heart-sensitivity score from `0.6957` to `0.8696`, while same-heart control accuracy remained `1.0` and heart-overreach remained `0.0`. Under conservative paired testing this is a directional confirmation result, not yet a final decisive main-benchmark claim. The broader project design includes matched secular controls, but the current public artifact is intentionally narrower: a pre-freeze confirmation slice with honest reproducibility boundaries.

![Same-act confirmation overview](assets/same-act-confirmation-overview.png)

## Main Result At A Glance

| Model | Slice | Task B | HSS | Same-Heart Control | Overreach | Significance note |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Qwen-1.5B-Instruct | `23` same-act motive pairs + `40` same-heart controls | `0.8889 -> 0.9524` | `0.6957 -> 0.8696` | `1.0 -> 1.0` | `0.0 -> 0.0` | exact paired sign test: one-sided `p = 0.0625`, two-sided `p = 0.125` |

## What This Benchmark Measures

The core question is whether framing changes **what the model pays moral attention to**.

One stylized same-act example looks like this:

| Case A | Case B |
| --- | --- |
| A student offers help mainly to look generous in public. | The same student offers the same help out of sincere concern. |

The three tasks then separate different kinds of judgment:

| Task | Plain-language question | Why it matters |
| --- | --- | --- |
| Task A | Which case is more morally problematic overall? | Tests the top-line verdict. |
| Task B | Which case reveals a worse inward orientation? | Tests whether the model tracks motive and heart posture. |
| Task C | Is the judgment mainly driven by outward act, motive, consequence, or rule? | Tests what the model treats as morally diagnostic. |

Same-heart controls are the guardrail. They hold inward orientation fixed while outward surface changes, so a method cannot "win" by simply over-imputing bad hearts everywhere.

## What We Can Claim

- On the current public confirmation slice, Christian heart-focused framing directionally improves inward-motive judgment.
- The strongest movement is in Task B and heart-sensitivity, not in first-pass Task A verdicts.
- That gain does not come with higher same-heart overreach or longer explanations on this slice.

## What We Cannot Yet Claim

- We cannot claim that Christian prompting improves moral judgment overall across models or benchmarks.
- We cannot yet claim a freeze-grade decisive result for the full paper benchmark.
- We cannot yet claim that the current public confirmation result is uniquely Christian rather than semantic reorientation, because the canonical public slice here is a baseline-vs-Christian comparison.

## Status

**What is frozen now**

- A public `Qwen-1.5B-Instruct` confirmation artifact on a 63-item same-act-plus-control slice.
- The canonical result files in `results/main_same_act_confirmation_v12_mps/`.
- The current project-page figure and a minimal reproduction path for this slice.

**What is not frozen yet**

- The full 160-item main benchmark.
- A fully double-annotated transformed Moral Stories main set.
- A final order-robust Task B method that clears the freeze bar across all cells.
- A public preprint and a full paper-ready main matrix.

## Reproduce The Current Confirmation Slice

This public repo guarantees reproduction of the current `Qwen-1.5B-Instruct` confirmation slice, not the full benchmark-construction workflow. Third-party raw benchmark mirrors are intentionally not vendored here.

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
bash scripts/reproduce_confirmation_slice.sh results/reproduction_confirmation
```

Expected outputs:

- `results/reproduction_confirmation/confirmation_summary.json`
- `results/reproduction_confirmation/confirmation_health.json`
- `results/reproduction_confirmation/confirmation_robustness.md`
- `results/reproduction_confirmation/confirmation_overview.svg`

## Repository Map

- `assets/`: figures used on the project page
- `configs/`: execution configs for the public confirmation artifact and internal study configs
- `results/main_same_act_confirmation_v12_mps/`: canonical public result files for the current strongest slice
- `scripts/reproduce_confirmation_slice.sh`: minimal reproduction entry point
- `docs/RUNBOOK.md`: internal full-pipeline runbook for benchmark construction and broader experiments
- `docs/ANNOTATION_PROTOCOL.md`: annotation rules for Task A, Task B, and Task C
- `docs/archive/`: archived planning and scoping notes from the active workspace phase

<details>
<summary>Method Details And Internal Diagnostics</summary>

- [Same-act confirmation readout](results/main_same_act_confirmation_v12_mps/confirmation_readout.md)
- [Robustness report](results/main_same_act_confirmation_v12_mps/confirmation_robustness.md)
- [Swap-gap breakdown](results/main_same_act_confirmation_v12_mps/confirmation_swap_gap_by_pair_type.md)
- [Annotation protocol](docs/ANNOTATION_PROTOCOL.md)
- [Internal runbook](docs/RUNBOOK.md)
- [Task B revision log](docs/TASK_B_REVISION_LOG.md)
- [Preregistration draft](docs/PREREGISTRATION_DRAFT.md)

</details>

## Citation

Use the GitHub release artifact for citation when referencing this repository:

- Release: [v0.1-confirmation](https://github.com/hanzhenzhujene/christian-moral-attention-reallocation/releases/tag/v0.1-confirmation)
- Citation metadata: [CITATION.cff](CITATION.cff)
- Preprint: no public preprint is linked yet

```bibtex
@software{zhu_2026_christian_moral_attention,
  author = {Zhu, Hanzhen},
  title = {Christian Moral Attention Reallocation},
  year = {2026},
  version = {v0.1-confirmation},
  url = {https://github.com/hanzhenzhujene/christian-moral-attention-reallocation},
  note = {Pre-freeze confirmation artifact}
}
```
