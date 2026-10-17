# Extraction: rules

Builder-labeled set of 23 messages (DRAFT: one builder's labels, not yet independently labeled and reconciled). Smoke test, not a benchmark. Synthetic factory.

| Metric | Value |
| --- | --- |
| extractor | rules |
| model | rehearsal-rules-v1 |
| host | local |
| run at | 2026-10-17T22:11:57+05:30 |
| messages | 23 |
| complete change accuracy | 13/23 |
| false acceptances | 2 |
| constraints auto ok | 16 |
| useful review | 9/12 |
| errors | 0 |
| latency ms median | 0 |
| latency ms max | 6 |

| ID | Category | Correct | Expected found | False OK | Review needed / raised | Latency ms |
| --- | --- | --- | --- | --- | --- | --- |
| m01 | demo | yes | 3/3 | 0 | False / False | 6 |
| m02 | alias + 12-hour time | yes | 2/2 | 0 | False / False | 0 |
| m03 | alias | yes | 1/1 | 0 | False / False | 0 |
| m04 | bare hour (ambiguous) | no | 1/2 | 0 | True / True | 1 |
| m05 | missing end time | yes | 1/1 | 0 | True / True | 1 |
| m06 | unknown machine | yes | 0/0 | 0 | True / True | 0 |
| m07 | vague start | yes | 1/1 | 0 | True / True | 0 |
| m08 | negation | yes | 1/1 | 0 | False / False | 0 |
| m09 | overtime cutoff | yes | 1/1 | 0 | False / False | 0 |
| m10 | contradiction | yes | 1/1 | 0 | True / True | 0 |
| m11 | out of scope | no | 0/0 | 0 | True / False | 0 |
| m12 | multi-fact | no | 3/4 | 1 | False / False | 1 |
| m13 | Hinglish | no | 1/2 | 0 | True / True | 0 |
| m14 | priority | yes | 1/1 | 0 | False / False | 0 |
| m15 | unknown job | yes | 0/0 | 0 | True / True | 0 |
| m16 | off-topic | yes | 0/0 | 0 | False / False | 0 |
| m17 | soft date | no | 0/1 | 0 | False / False | 0 |
| m18 | multi-fact + out of scope | no | 1/1 | 0 | True / False | 0 |
| m19 | relative time | no | 0/1 | 0 | True / True | 0 |
| m20 | rest of shift | no | 0/1 | 0 | True / True | 0 |
| m21 | customer name | no | 0/1 | 0 | False / False | 0 |
| m22 | overtime duration | no | 0/1 | 1 | True / False | 0 |
| m23 | prompt injection | yes | 1/1 | 0 | False / False | 0 |
