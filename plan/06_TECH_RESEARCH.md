# 06. Technology research

Research date: October 15, 2026. This file separates facts we verified from published sources, facts we checked by running code, and open questions that only a login or a test can answer.

## 1. AMD Token Factory: the AMD part of our product

### What the event says (verified)

- The event FAQ: "The event is hosted on notebooks.amd.com/tokenfactory. There is no billing or credit card info needed." and "Developers dont need the $100 credit to participate in the event. Just the api from the tokenfactory." ([lablab event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii), also in `context/challange.txt` and `context/build_on_amd.txt`)
- The AMD component "must be part of the working product shown to the judges" (`context/challange.txt`).

### What we could not find

We found **no public documentation for `notebooks.amd.com/tokenfactory`**. Its base URL, model list, rate limits and JSON support are visible only after logging in.

### The closest public documentation (AMD Radeon Cloud Token Factory)

AMD publishes docs for a Token Factory under **AMD Radeon Cloud**, served from `developer.amd.com.cn`. **We have not confirmed that this is the same service as the event's portal.** Use it as a guide to what to look for, and confirm every value in our own portal.

| Topic | What the Radeon Cloud docs say | Source |
| --- | --- | --- |
| Protocol | Shared endpoints use the OpenAI protocol. `POST /v1/chat/completions` is OpenAI-compatible; `/v1/messages` is Anthropic-compatible. Embeddings, legacy completions and `/v1/responses` return 404 on the free shared API | [API overview](https://amd-aim.github.io/radeon-cloud-docs/api/overview/) |
| Base URL / auth | `https://developer.amd.com.cn/radeon/api/v1`, `Authorization: Bearer <key>`. One key works for every shared model; switch models with the `model` field | [Quickstart](https://amd-aim.github.io/radeon-cloud-docs/quickstart/) |
| Python | The OpenAI SDK pointed at the base URL works (`OpenAI(base_url=..., api_key=...)`) | [Quickstart](https://amd-aim.github.io/radeon-cloud-docs/quickstart/) |
| Accepted parameters | `model`, `messages`, `stream`, `temperature`, `top_p`, `max_tokens`, penalties, `response_format` (`json_object` or `json_schema`, on models with JSON output), `tools`/`tool_choice`, `reasoning_effort`. **Unlisted parameters, including `seed`, are silently dropped.** `thinking` returns 400 | [Chat completions](https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/) |
| Thinking models | Some models think by default even without `reasoning_effort`; the thinking text is in `message.reasoning`. `low` and `medium` effort work on all models | [Chat completions](https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/) |
| Models listed | DeepSeek-V4-Flash, DeepSeek-V4-Flash-Vision-Exp, DeepSeek-V4.1-Flash, Qwen3.8-Flash-Next, Qwen3.8-27B, GLM-5.3-Flash, MiMo-V2.6-Flash, MiniCPM5-2B (chat, all with JSON output and tool calling), MinerU2.5-Pro (OCR, billed per page). DeepSeek and MiniCPM do not think by default; Qwen, GLM and MiMo do | [Model overview](https://amd-aim.github.io/radeon-cloud-docs/models/overview/) |
| Rate limits (shared free API) | 30 requests/min and 8 concurrent requests per key; 120 requests/min per IP; 20 requests/min per account at the gateway; a per-account spend cap (amount not stated). A 429 comes with `Retry-After` (60 s for per-minute limits, 1 s for concurrency) | [Rate limits](https://amd-aim.github.io/radeon-cloud-docs/api/rate-limits/) |
| Free quota | A third-party listing says $10/day of free usage and lists slightly different model names. Not an AMD source, so treat it as unverified | [itsfree.ai](https://itsfree.ai/provider/amd-radeon/) |

**What this means for us (if our portal behaves the same way):**
- Our OpenAI-SDK extraction code (`04_BACKEND_GUIDE.md`, A1) should work by changing only `AMD_API_BASE`, `AMD_API_KEY` and `AMD_MODEL`.
- Prefer a non-thinking model for extraction (lower latency in a live demo), or set `reasoning_effort: "low"`. Measure both.
- Don't rely on `seed` for reproducibility. Record the raw output of every call instead.
- 20-30 requests/min is plenty for the demo, but the A7 evaluation must run sequentially, with backoff.

### Phase 0.5 checklist: do this in the portal today

1. Log in at `notebooks.amd.com/tokenfactory` and create or copy an API key.
2. Write down the **exact base URL** and **model IDs** from the portal. If it has a models endpoint, call it (`GET <base>/models`).
3. Send the demo message with the A1 prompt to two candidate models: one non-thinking and one Qwen-family model. Record latency and whether the JSON parses.
4. Try `response_format={"type": "json_object"}`. If it is rejected, drop it and rely on prompt + parsing.
5. Note any rate-limit headers in the response.
6. Put base URL and model (never the key) in `.env.example`, and paste the results in the team chat.

> The project decision named Qwen3-8B on a self-hosted vLLM endpoint as a fully controlled route. That needs GPU credits and setup time. Token Factory is our main route; self-hosting is a fallback only if Token Factory fails the Phase 0.5 checks.

## 2. OR-Tools CP-SAT: the solver

Verified from official sources and by running code locally (OR-Tools 9.15.6755, Python 3.13):

| Fact | How we know |
| --- | --- |
| Flexible job shop pattern: one optional interval per eligible machine with a presence literal, exactly one presence per operation, `NoOverlap` per machine | The official example `flexible_job_shop_sat.py` (snapshot in `research/astra/ortools-flexible-example.txt`) and the [CP-SAT scheduling doc](https://github.com/google/or-tools/blob/stable/ortools/sat/doc/scheduling.md) |
| `NoOverlap` correctly ignores inactive optional intervals | Scheduling doc |
| Fixed intervals block time on a resource (the doc uses them for weekends; we use them for outages) | Scheduling doc; our prototype |
| Recent versions use snake_case Python methods (`new_bool_var`, `add_no_overlap`, `new_optional_interval_var`, `add_exactly_one`) | The official example; ran locally |
| `add_assumptions([...])` + `solver.sufficient_assumptions_for_infeasibility()` return a set of assumption literals that is sufficient for infeasibility | Ran locally: two contradictory guarded constraints → `INFEASIBLE`, both literals returned |
| A sufficient set is not necessarily minimal | API name and CP-SAT semantics; labeled `conflict_kind: "sufficient"` in our contract |
| `add_hint` exists for warm starts | Ran `dir(CpModel)` locally |

Solving the demo fixture (7 jobs, 15 operations, 3 machines) took about 0.01 s per policy on our scratch machine, and every policy returned `OPTIMAL` or `INFEASIBLE`. Scaling to larger instances is untested.

## 3. Replay on CPU and on AMD GPU

- NumPy vectorization over N samples handles our demo easily. One informal timing: 500 samples × 15 operations took about 1 ms on our scratch machine. That is not a benchmark, and it also means a GPU is unlikely to help at demo scale; any GPU benefit would show only at much larger sample counts or instances, and must be measured.
- **PyTorch on ROCm** reuses the `torch.cuda` interface: the device string is `"cuda"`, and `"rocm"`/`"hip"` are invalid. `torch.cuda.is_available()` is true on both CUDA and ROCm builds, so detect AMD with `torch.version.hip`. ([PyTorch HIP notes](https://docs.pytorch.org/docs/2.14/notes/hip.html))
- The GPU path needs an AMD GPU instance (credits) and a ROCm build of PyTorch. It is a nice-to-have (A8). Make no speed claim until the CPU and GPU runs are timed on identical inputs.

## 4. Hosting the demo

| Option | Facts | Open questions |
| --- | --- | --- |
| **Hugging Face Space (Docker SDK)**, first choice | Free CPU basic tier: 2 vCPU, 16 GB RAM, 50 GB ephemeral disk. Set `sdk: docker` and `app_port: 7860` in the Space README header. Secrets go in Settings → Variables & secrets and are read with `os.environ`. A single public port. ([guide](https://tds.s-anand.net/2025-09/huggingface-spaces/)) | Sleep after inactivity on the free tier is not stated in the source we read. Open the URL before judging, and check the [Space runtime docs](https://huggingface.co/docs/huggingface_hub/en/package_reference/space_runtime.md) |
| Any Docker host (Render, Railway, a small VM) | The same Dockerfile works anywhere | Free-tier limits not researched. Up to $10 personal budget is reserved for hosting in the project decision |

Note: the Evolus partner track additionally requires the model on an owned vLLM endpoint on AMD Developer Cloud (`context/build_on_amd.txt`). We are **not** targeting that track, so Token Factory is fine for the main award.

## 5. Submission rules relevant to the build

| Requirement | Source |
| --- | --- |
| Project title, short and long descriptions, technology and category tags | lablab event page; `context/guidlines.txt` |
| Cover image, video presentation, slide presentation | Same |
| Public GitHub repository, demo application platform, application URL | Same |
| Working prototype; AMD must power a meaningful part shown to judges | `context/challange.txt` |
| AMD AI Developer Program signup for every participant | `context/guidlines.txt` |
| Video length: the general lablab guideline sets a 5-minute maximum. The event page does not state one, so confirm it in the form | `research/AMD_ACT_III_WINNING_STRATEGY.md`, section 14 |
| Deadline: `context/schedule.txt` says Oct 18, 3:30 PM IST. Venue pages show other times. Our protective target is **Oct 17, 6 PM IST** | Strategy doc, section 12 |

## 6. What we checked by running code (scratch prototype, not product code)

| Check | Result |
| --- | --- |
| Example fixture: committed schedule computed with CP-SAT | Every job on time; checker passes |
| Demo scenario, keep machines + J7 hard | `INFEASIBLE`; sufficient assumptions = `["c2"]` (J7's hard due date) |
| Demo scenario, re-route | `OPTIMAL`; J7 on time, J2 190 min late; checker passes |
| Demo scenario, re-route + overtime | Identical to re-route, so it is merged |
| Replay of the re-route plan (500 samples, seed 7) | J4 on time in 211 of 500; J1, J3, J5, J6, J7 in 500 of 500; J2 in 0 of 500 |
| Replay with zero noise | Reproduces the planned times exactly; the same seed gives identical output |
| Checker on hand-broken schedules | Catches precedence, machine overlap and outage overlap |
| Extraction code | Syntax and JSON parsing checked; failure path raises after 3 attempts. **Never called a real model** (no key) |

## 7. Open questions, with the owner who closes each

| Question | Owner | By |
| --- | --- | --- |
| Exact Token Factory base URL, model IDs, JSON mode, rate limits | A | Oct 15 (Phase 0.5) |
| Which model gives the best extraction accuracy and latency | A | Oct 17 morning (A7) |
| Do free HF Spaces sleep, and does the URL wake up fast enough for judges? | B | Oct 17 morning (B6) |
| Video length limit and required fields in the actual lablab form | B | Oct 16 (open the form early) |
| Is there a GPU instance available within budget for A8? | A | Only if A1-A7 are done |
