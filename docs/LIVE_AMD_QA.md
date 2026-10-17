# Live AMD integration verification — 17 October 2026

AMD Token Factory authentication, model access and the complete local Docker
workflow are verified. Rule fallback was disabled throughout the live checks.
The service is available locally at http://localhost:7860. Public deployment
has not been verified.

## Provider and configuration

- Base URL: `https://developer.amd.com.cn/radeon/api/v1`, from the organizer's supplied API manual.
- Authenticated `/models` and `/usage` returned HTTP 200. The requested model was in the live catalog.
- Requested model: `DeepSeek-V4-Flash`. Returned identifier: `self-dploy/DeepSeek-V4-Flash` (preserved exactly).
- JSON mode enabled, temperature 0, timeout 30 seconds per attempt, no reasoning-effort override.
- API key supplied at runtime from the ignored `.env`; no key is in the records or image build context.
- Shared quota at the final check: 0.996046 remaining of a 1 USD-denominated daily cap; 20 requests/minute.
  The manual describes the shared APIs as free with a usage cap. This meter is not a cash charge.

## Complete application check

The [saved Docker workflow](../eval/smoke/docker_live.json) passed all
7 check groups. The test checks the agreed demo facts:
M2 unavailable from 10:00 to 14:00, J7 hard due at 16:00, and overtime as an
option requiring separate approval. It then executes CPU solving,
independent checking, 500-scenario NumPy replay, concession approval, CSV/JSON
export, idempotent approval and locking against later replay changes.

That extraction took 8930 ms. A separate fresh
[Chrome session](../eval/smoke/browser_live.json) took 8495 ms for extraction and completed
the same user flow. Both browser download blobs were readable; the decision
record retained a passing checker and the live AMD trace. No JavaScript
exceptions or failed HTTP responses were observed. All factory data in
these checks is synthetic; no factory actions were executed.

Reproduce against the local service or a later deployed URL:

```bash
python3 scripts/container_smoke.py http://localhost:7860 --mode amd \
  --save-to eval/smoke/docker_live.json
```

The `amd` mode makes one real model request and requires configured AMD access
with fallback disabled. CI uses only the strict and labeled-fallback modes.

## Development evaluation

| Saved run / labels | Complete changes | Wrong items marked `ok` | Useful review | API errors |
| --- | --- | --- | --- | --- |
| Initial prompt / Muskan | 19/23 | 1 | 11/12 | 1 |
| Clarified prompt / Muskan | 23/23 | 0 | 12/12 | 0 |
| Same clarified predictions / Abhishek | 21/23 | 0 | 9/10 | 0 |

Successful-call latency in the clarified run: median 3784 ms,
maximum 12284 ms. The initial run's timeout is counted as an error.
Latency statistics in both runs cover successful calls and exclude failed
calls. Saved errors and original model text remain in the JSON results.

The initial run exposed three prompt ambiguities: conditional overtime was
interpreted as a prohibition, a corrected deadline was silently selected,
and the overtime ceiling was used for “rest of shift.” The prompt now spells
out proposed permission, preservation of conflicting statements, and the
normal shift end. The stronger workflow smoke check asserts the expected
facts instead of checking only proposal status. Original records are
preserved under `initial_*`; they predate this assertion.

These are **provisional development results, not a benchmark**. Both runs use
the same frozen 23 builder-written messages, which informed the prompt
changes. No independent test-set performance or factory reliability is
established. The two label files are unchanged, and `final.jsonl` is still
absent. The default runner uses Muskan's labels. Scoring the same saved
predictions against Abhishek's labels yields the separate row above.

The remaining Abhishek-label mismatches are m07 (“after lunch” produced a
13:00 proposal marked for review, while his label requires an unknown start)
and m16 (the coffee request produced no scheduling constraints, while his
label expects an unsupported item for review). These require label and
product-policy reconciliation before publishing a final score. No label was
changed to improve the metric.

Reproduce the alternate scoring without another AMD request:

```bash
python3 eval/rescore_saved.py --predictions eval/results/extraction_amd.json \
  --labels eval/labels/abhishek.jsonl --output eval/results/extraction_amd_abhishek.json
```

Source/prompt hashes are recorded in [initial configuration](../eval/smoke/initial_run_config.json)
and [clarified configuration](../eval/smoke/run_config.json).
See the [initial results](../eval/results/extraction_amd_initial.md),
[clarified results](../eval/results/extraction_amd.md), and
[alternate-label scoring](../eval/results/extraction_amd_abhishek.json).

## Remaining work

Publish a stable public URL and repeat the live workflow there, including a
fresh visitor and sleep/wake checks. Reconcile the two label sets before
claiming final extraction quality. GPU replay and CPU/GPU comparisons remain
optional, unimplemented work; the verified replay here is CPU NumPy.
