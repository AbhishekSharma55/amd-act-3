# Extraction: amd

Builder-labeled set of 23 messages (DRAFT: one builder's labels, not yet independently labeled and reconciled). Smoke test, not a benchmark. Synthetic factory.

| Metric | Value |
| --- | --- |
| extractor | amd |
| model | self-dploy/DeepSeek-V4-Flash |
| host | developer.amd.com.cn |
| run at | 2026-10-17T23:21:34+05:30 |
| messages | 23 |
| complete change accuracy | 19/23 |
| false acceptances | 1 |
| constraints auto ok | 17 |
| useful review | 11/12 |
| errors | 1 |
| latency ms median | 3928.5 |
| latency ms max | 9403 |

| ID | Category | Correct | Expected found | False OK | Review needed / raised | Latency ms |
| --- | --- | --- | --- | --- | --- | --- |
| m01 | demo | no | 2/3 | 1 | False / False | 7528 |
| m02 | alias + 12-hour time | yes | 2/2 | 0 | False / False | 5477 |
| m03 | alias | yes | 1/1 | 0 | False / False | 4673 |
| m04 | bare hour (ambiguous) | yes | 2/2 | 0 | True / True | 5850 |
| m05 | missing end time | yes | 1/1 | 0 | True / True | 3779 |
| m06 | unknown machine | yes | 0/0 | 0 | True / True | 3491 |
| m07 | vague start | yes | 1/1 | 0 | True / True | 6446 |
| m08 | negation | yes | 1/1 | 0 | False / False | 2626 |
| m09 | overtime cutoff | yes | 1/1 | 0 | False / False | 3361 |
| m10 | contradiction | no | 1/1 | 0 | True / False | 5474 |
| m11 | out of scope | yes | 0/0 | 0 | True / True | 2577 |
| m12 | multi-fact | yes | 4/4 | 0 | False / False | 9403 |
| m13 | Hinglish | yes | 2/2 | 0 | True / True | 6124 |
| m14 | priority | yes | 1/1 | 0 | False / False | 3047 |
| m15 | unknown job | yes | 0/0 | 0 | True / True | 4895 |
| m16 | off-topic | yes | 0/0 | 0 | False / False | 1519 |
| m17 | soft date | yes | 1/1 | 0 | False / False | 3769 |
| m18 | multi-fact + out of scope | yes | 1/1 | 0 | True / True | 7354 |
| m19 | relative time | yes | 1/1 | 0 | True / True | 4078 |
| m20 | rest of shift | no | 0/1 | 0 | True / True | 2950 |
| m21 | customer name | yes | 1/1 | 0 | False / False | 2949 |
| m22 | overtime duration | yes | 1/1 | 0 | True / True | 3672 |
| m23 | prompt injection | no | 0/1 | 0 | False / False | None |
