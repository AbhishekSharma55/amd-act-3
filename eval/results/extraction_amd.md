# Extraction: amd

Builder-labeled set of 23 messages (DRAFT: one builder's labels, not yet independently labeled and reconciled). Smoke test, not a benchmark. Synthetic factory.

| Metric | Value |
| --- | --- |
| extractor | amd |
| model | self-dploy/DeepSeek-V4-Flash |
| host | developer.amd.com.cn |
| run at | 2026-10-17T23:26:37+05:30 |
| messages | 23 |
| complete change accuracy | 23/23 |
| false acceptances | 0 |
| constraints auto ok | 17 |
| useful review | 12/12 |
| errors | 0 |
| latency ms median | 3784 |
| latency ms max | 12284 |

| ID | Category | Correct | Expected found | False OK | Review needed / raised | Latency ms |
| --- | --- | --- | --- | --- | --- | --- |
| m01 | demo | yes | 3/3 | 0 | False / False | 8280 |
| m02 | alias + 12-hour time | yes | 2/2 | 0 | False / False | 5681 |
| m03 | alias | yes | 1/1 | 0 | False / False | 3969 |
| m04 | bare hour (ambiguous) | yes | 2/2 | 0 | True / True | 7626 |
| m05 | missing end time | yes | 1/1 | 0 | True / True | 3604 |
| m06 | unknown machine | yes | 0/0 | 0 | True / True | 3765 |
| m07 | vague start | yes | 1/1 | 0 | True / True | 3671 |
| m08 | negation | yes | 1/1 | 0 | False / False | 2872 |
| m09 | overtime cutoff | yes | 1/1 | 0 | False / False | 3336 |
| m10 | contradiction | yes | 1/1 | 0 | True / True | 6331 |
| m11 | out of scope | yes | 0/0 | 0 | True / True | 2842 |
| m12 | multi-fact | yes | 4/4 | 0 | False / False | 9407 |
| m13 | Hinglish | yes | 2/2 | 0 | True / True | 7722 |
| m14 | priority | yes | 1/1 | 0 | False / False | 3197 |
| m15 | unknown job | yes | 0/0 | 0 | True / True | 3562 |
| m16 | off-topic | yes | 0/0 | 0 | False / False | 1108 |
| m17 | soft date | yes | 1/1 | 0 | False / False | 3680 |
| m18 | multi-fact + out of scope | yes | 1/1 | 0 | True / True | 5353 |
| m19 | relative time | yes | 1/1 | 0 | True / True | 4796 |
| m20 | rest of shift | yes | 1/1 | 0 | True / True | 3915 |
| m21 | customer name | yes | 1/1 | 0 | False / False | 12284 |
| m22 | overtime duration | yes | 1/1 | 0 | True / True | 3033 |
| m23 | prompt injection | yes | 1/1 | 0 | False / False | 3784 |
