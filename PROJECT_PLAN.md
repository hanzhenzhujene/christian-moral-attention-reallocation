# Christian Framing as Moral Attention Reallocation

## 1. Working Thesis

This project does **not** ask whether Christian framing makes an LLM "more moral" in a general sense.

It asks a narrower and more mechanism-oriented question:

**Does Christian heart-focused framing change what the model treats as morally diagnostic when reading a moral case?**

More concretely, when an LLM evaluates a moral scenario, does it attend more to:

- outward act
- inward motive
- consequence
- rule / norm

Core claim:

> Christian framing may not improve moral judgment uniformly, but it may reallocate moral attention from outward behavioral surface toward inward motive and disposition.

This is a strong framing for a paper because it is:

- more mechanistic than "religious prompts improve morality"
- closer to virtue/character-sensitive moral psychology
- less vulnerable to being dismissed as a generic prompt hack

## 2. Why This Project Matters

The project sits at a useful intersection:

- Christian ethics
- virtue / character-sensitive evaluation
- moral salience diagnosis

The novelty is not primarily "religion helps." The novelty is:

1. testing whether religious framing changes **moral attention allocation**
2. moving beyond pure QA or doctrine recall
3. probing whether models become more **heart-sensitive**, not just more norm-compliant
4. using everyday moral scenarios rather than only trolley-style dilemmas

This gives the paper a clear contribution:

**Christian framing is studied here as a probe on moral cognition, not as a blanket intervention for moral improvement.**

## 3. Main Research Questions

### RQ1

Does Christian heart-focused framing increase sensitivity to inward motive on morally diagnostic cases where outward behavior is held constant?

### RQ2

Does Christian framing shift explanation focus away from outward act and toward motive/disposition?

### RQ3

Is any observed effect specifically Christian/doctrinal, or can it be explained by a secular paraphrase that also highlights inner motive and character?

### RQ4

Does Christian framing increase cross-task consistency between moral evaluation and heart-level attribution?

## 4. Main Hypotheses

### H1: Heart-Sensitivity Hypothesis

On same-act-different-motive items, Christian heart-focused framing will increase the probability that the model identifies the inwardly worse case as more morally problematic.

### H2: Reason-Focus Shift Hypothesis

Christian framing will increase `reason_focus = motive` and decrease `reason_focus = outward_act`, relative to baseline.

### H3: Consistency Hypothesis

Christian framing will increase agreement between:

- which case is judged more morally problematic
- which case is judged to reveal worse inward orientation

### H4: Semantic-Reorientation Alternative

If Christian framing and a secular motive-focused paraphrase perform similarly, then the main mechanism is likely **semantic reorientation toward inward motive**, not uniquely sacred authority.

## 5. Benchmark Strategy

## 5.1 Primary Benchmark: Moral Stories Subset

Use a curated subset of Moral Stories as the main benchmark.

Why it fits:

- it already separates norm, situation, intention, action, and consequence
- it supports controlled contrastive design
- it is closer to everyday moral reasoning than many classic dilemma benchmarks

### Target subset size

Strong full study:

- 180 to 240 items

Small but publishable first pass:

- 150 items

MVP:

- 120 items

### Subset construction priorities

Prioritize items that can be transformed into pairwise comparisons with clean control over the outward act:

- same outward act, different motive
- same norm compliance, different heart posture
- outwardly harsh act with benevolent motive vs malicious motive
- outwardly kind act with vain/self-serving motive vs loving motive

### Item families to preserve

Keep a balanced mix of:

- motive-diagnostic items
- consequence-diagnostic items
- rule-diagnostic items
- mixed-signal items

This lets the paper show whether Christian framing shifts attention selectively, rather than just making the model globally "motive-biased."

## 5.2 Secondary Benchmark: HeartBench Mini-Benchmark

HeartBench should be a custom mini-benchmark, not the main legitimacy anchor.

Its role is to cover Christian moral-psychology cases that existing benchmarks likely underrepresent:

- outwardly good but inwardly vain
- outwardly compliant but resentful
- outwardly harsh but compassionate
- public virtue masking pride
- sacrificial act done for praise
- technically truthful speech delivered with cruelty

### Target size

Strong full study:

- 80 to 120 items

Compact version:

- 60 items

MVP:

- 40 items

### Design principle

HeartBench items should be short, everyday, and pairwise whenever possible.

Avoid:

- overly theological trivia
- obscure doctrine disputes
- only extreme moral dilemmas

Prefer:

- workplace interactions
- family obligations
- church/community service
- honesty, generosity, forgiveness, pride, resentment, vanity, compassion

## 6. Experimental Conditions

Five conditions are enough for the main paper:

1. `Baseline`
2. `Neutral intention-sensitive instruction`
3. `Christian heart-focused framing`
4. `Doctrinal framing`
5. `Secular matched paraphrase`

Optional sixth condition:

6. `Scripture citation only`

## 6.1 Condition Definitions

### Baseline

No special moral lens. Standard instruction to answer carefully.

Purpose:

- anchor condition
- estimate default moral salience profile

### Neutral Intention-Sensitive Instruction

Explicitly tells the model to consider motives, intentions, and inner orientation, but without religious language.

Purpose:

- separate generic task clarification from specifically Christian framing

### Christian Heart-Focused Framing

Frames moral evaluation in terms of the heart, inward disposition, love, pride, hypocrisy, resentment, and purity/corruption of motive.

Purpose:

- test the main hypothesis directly

### Doctrinal Framing

Explicitly uses Christian doctrinal language about sin, virtue, repentance, love of neighbor, pride, hypocrisy, and inner transformation.

Purpose:

- test whether stronger doctrinal loading produces a different effect than gentler heart-language

### Secular Matched Paraphrase

Uses nonreligious language that is semantically matched to character, motive, sincerity, vanity, compassion, and inner orientation.

Purpose:

- isolate whether the effect depends on Christian authority or on semantic redirection toward motive

### Scripture Citation Only

Provides scriptural citations or short excerpts without additional interpretive framing.

Purpose:

- test whether citation alone is enough, or whether interpretive framing is doing the real work

## 7. Task Design

Each item should be asked in three task formats.

## 7.1 Task A: Moral Evaluation

Question:

**Which case is more morally problematic?**

Output format:

- `A`
- `B`
- `Same`

Purpose:

- measure bottom-line moral judgment

## 7.2 Task B: Heart-Level Attribution

Question:

**Which case reveals a worse inward orientation or more disordered motive?**

Output format:

- `A`
- `B`
- `Same`

Purpose:

- directly test heart-sensitive reading

## 7.3 Task C: Reason Focus

Question:

**What primarily drove your judgment?**

Forced-choice output:

- `outward_act`
- `motive`
- `consequence`
- `rule`

Optional addition:

- one short justification sentence after the forced-choice label

Purpose:

- expose moral attention allocation, not just final answer accuracy

## 8. Data Structure

The cleanest format is pairwise A/B comparison.

Preferred structures:

- same outward act, different motive
- same compliance, different heart posture
- same consequence, different motive
- same motive, different consequence
- outwardly harsh but compassionate vs outwardly harsh but malicious

This structure makes the paper much cleaner because it lets us test:

- what changes when outward behavior is fixed
- whether models overweight visible action
- whether Christian framing changes internal attribution rather than only final verdict

## 9. Main Metrics

## 9.1 Heart-Sensitivity Score (HSS)

Definition:

On items where the outward act is held constant and motive differs, measure the proportion of cases where the model selects the inwardly worse case.

Interpretation:

- higher is better
- this is the most important primary metric

## 9.2 Surface-Overweighting Index (SOI)

Definition:

On same-act-different-motive items, measure how often the model ignores motive by:

- choosing `Same` when one case has clearly worse inward motive
- or giving `reason_focus != motive`

Interpretation:

- higher means the model is more dominated by outward surface
- Christian framing should reduce this index if the thesis is right

## 9.3 Reason-Focus Shift (RFS)

Definition:

The change in probability of `reason_focus = motive` from baseline to each framing condition.

Main contrast:

- `Christian heart-focused` minus `Baseline`

Important comparison:

- `Christian heart-focused` minus `Secular matched paraphrase`

## 9.4 Cross-Task Consistency (CTC)

Definition:

Agreement between Task A and Task B on which case is morally worse / inwardly worse.

Interpretation:

- if the model says B is morally worse but A has the worse heart, that suggests unstable moral reading
- Christian framing should improve coherence if it creates a more integrated heart-level interpretation

## 9.5 Optional Secondary Metrics

- response length, to check verbosity confounds
- decisiveness rate, to check whether framing only reduces `Same`
- confidence or self-rated certainty, if included
- category-specific performance by item type

## 10. Gold Labels and Annotation

The strongest setup is to annotate each pair with:

- morally worse case
- inwardly worse case
- primary diagnostic dimension

For Moral Stories subset items, use existing structure where possible, then manually verify difficult or transformed cases.

For HeartBench, create a simple annotation protocol with at least two annotators for pilot items.

Important rule:

**Do not rely only on free-form explanation scoring.**

Use forced-choice labels for the main analysis, and treat free-text explanations as secondary qualitative evidence.

## 11. Analysis Plan

## 11.1 Main Comparisons

Within each model, compare conditions using paired item-level analysis:

- Baseline vs Neutral intention-sensitive
- Baseline vs Christian heart-focused
- Baseline vs Doctrinal
- Christian heart-focused vs Secular matched
- Doctrinal vs Christian heart-focused

## 11.2 Statistical Strategy

Use one of these as the primary inferential framework:

- mixed-effects logistic regression with random intercepts for item
- paired proportion tests on key binary metrics

Recommended dependent variables:

- correct identification of inwardly worse case
- `reason_focus = motive`
- Task A / Task B agreement

Useful fixed effects:

- prompt condition
- benchmark source
- item type
- model size

## 11.3 Robustness Checks

- randomize A/B side to avoid position bias
- keep output format fixed across conditions
- run each condition in isolated fresh chats
- hold temperature constant
- optionally repeat with 2 to 3 seeds if using sampling

## 12. Most Important Confounds and Controls

## 12.1 Moral Seriousness / Verbosity Confound

Risk:

Christian framing may only make the model sound more serious, pious, or verbose.

Control:

- forced-choice outputs
- fixed explanation length cap
- measure response length separately
- include secular matched paraphrase

## 12.2 Generic Intention Cueing Confound

Risk:

Any prompt that says "consider intention" may produce the effect.

Control:

- include Neutral intention-sensitive condition
- compare Christian framing directly against both neutral and secular matched conditions

## 12.3 Sacred Authority Confound

Risk:

The effect may come from authority/citation rather than heart-language.

Control:

- doctrinal framing
- scripture citation only
- secular matched paraphrase

## 12.4 Dataset Artifact Risk

Risk:

Moral Stories may make motive too easy or too explicit.

Control:

- use HeartBench for harder and more naturalistic cases
- include item difficulty tags

## 13. Expected Result Patterns

## 13.1 Best-Case Result

Christian framing does not dramatically raise overall moral accuracy, but it clearly improves:

- motive-sensitive item performance
- `reason_focus = motive`
- cross-task consistency

This supports the strongest paper claim:

**Christian framing changes moral attention before it improves moral performance.**

## 13.2 Also Valuable Result

Christian framing and secular matched paraphrase perform similarly.

Then the paper can argue:

**The main mechanism is semantic reorientation toward inward motive, rather than uniquely Christian authority.**

This is still a clean and publishable finding.

## 13.3 Null or Mixed Result

No major change in HSS or RFS, but Christian framing increases verbosity or condemnation language.

This would still be useful because it shows:

- stronger moral rhetoric is not the same as better heart-sensitive reasoning
- religious prompting may alter style more than moral attention

## 14. Minimal Viable Version

If the goal is a fast MVP:

- Moral Stories subset: 120 items
- HeartBench: 40 items
- Conditions: Baseline / Christian / Secular matched
- Models: Qwen 0.5B and Qwen 1.5B
- Tasks: Task A + Task B + Task C

This MVP is strong because it directly tests the core mechanism with limited scope.

## 15. Recommended Full Study

For a stronger paper:

- Moral Stories subset: 180 to 240 items
- HeartBench: 80 to 120 items
- Conditions: all 5 main conditions, optional 6th
- Models: small and medium open models, optionally one stronger proprietary model for comparison
- Full task suite with forced-choice outputs and short explanation sentence

## 16. Paper Storyline

A clean storyline for the paper is:

1. existing work often studies religion in LLMs through QA, value alignment, or broad morality claims
2. this paper studies a more specific mechanism: moral attention allocation
3. Christian moral language is especially relevant because it often foregrounds the heart, motive, and inward disposition
4. experiments show whether this framing shifts what the model treats as morally diagnostic
5. the result is a contribution to both AI moral evaluation and religion-and-LLM research

## 17. Proposed Paper Structure

### Introduction

- problem: "more moral" is too coarse
- proposal: study reallocation of moral attention
- Christian heart-language as test case
- contributions

### Background

- LLM moral reasoning benchmarks
- religion and Christian ethics in LLM evaluation
- virtue ethics, character, motive, and moral salience

### Benchmark Design

- Moral Stories subset
- HeartBench design
- item types and annotation

### Experimental Setup

- prompt conditions
- tasks
- models
- metrics

### Results

- HSS
- SOI
- RFS
- CTC
- ablations and condition contrasts

### Discussion

- moral attention vs moral accuracy
- Christian effect vs secular semantic effect
- implications for prompt-based moral steering
- limits and future work

## 18. Immediate Next Steps

### Week 1

- finalize paper framing and hypotheses
- define exact item templates
- curate first 30 to 40 Moral Stories items
- draft first 15 to 20 HeartBench items

### Week 2

- write prompt templates for 3 MVP conditions
- lock output schema for Tasks A/B/C
- run a small pilot on 20 items
- inspect failure modes and revise benchmark wording

### Week 3

- finish MVP benchmark curation
- run Qwen 0.5B and 1.5B
- compute first-pass HSS, SOI, RFS, and CTC

### Week 4

- write figures and tables
- decide whether to expand to full 5-condition study
- draft introduction and results sections

## 19. One-Sentence Version

If you need the shortest paper pitch:

**We test whether Christian heart-focused prompting changes not how moral LLMs are in general, but what they attend to as morally diagnostic, shifting evaluation from outward act toward inward motive and disposition.**
