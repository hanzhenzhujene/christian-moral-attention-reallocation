# Task B Swap-Gap Breakdown

Bucket mode: `pair_type`

## Qwen-0.5B-Instruct / baseline

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 1.0 | None | None |
| same_act_different_motive | 12 | 0.8333 | 0.6667 | 0.1666 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | 1.0 | 1.0 | 0.0 |

## Qwen-0.5B-Instruct / christian_heart

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 0.0 | None | None |
| same_act_different_motive | 12 | 0.2 | 0.5714 | 0.3714 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | None | 0.5 | None |

## Qwen-0.5B-Instruct / secular_matched

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 1.0 | None | None |
| same_act_different_motive | 12 | 1.0 | 0.875 | 0.125 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | 0.0 | 1.0 | 1.0 |

## Qwen-1.5B-Instruct / baseline

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 1.0 | None | None |
| same_act_different_motive | 12 | 1.0 | 0.5 | 0.5 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | 1.0 | 1.0 | 0.0 |

## Qwen-1.5B-Instruct / christian_heart

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 1.0 | None | None |
| same_act_different_motive | 12 | 1.0 | 0.7143 | 0.2857 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | None | 1.0 | None |

## Qwen-1.5B-Instruct / secular_matched

| Bucket | n | swap_false acc | swap_true acc | abs gap |
| --- | ---: | ---: | ---: | ---: |
| outwardly_harsh_benevolent_vs_malicious | 1 | 1.0 | None | None |
| same_act_different_motive | 12 | 0.75 | 0.5 | 0.25 |
| same_intention_moral_vs_immoral_action | 5 | 1.0 | 1.0 | 0.0 |
| same_norm_different_heart | 2 | 1.0 | 1.0 | 0.0 |

