# CacheForge

**A KV-cache fabric for AMD Instinct fleets — pool the fleet's HBM into one shared KV tier, so a prefix computed once is reused everywhere.**

Today every vLLM worker keeps its own isolated KV cache. The same system prompt, RAG template, or agent scaffold gets **recomputed and re-stored on every worker that sees it** — wasted prefill FLOPs and wasted HBM, multiplied by fleet size. CacheForge makes KV cache a **movable, shared fleet resource** instead of data pinned to whichever GPU happened to compute it.

Two layers, shipped in order:

- **v1 — cache-aware routing (built, benchmarked on real MI300X).** Route each request to the worker most likely to already hold its KV-cache prefix, with load-aware spill-over. RadixAttention's idea lifted to the routing layer. Works, measured (below) — but it *pins* cache to a location, so it's a small-fleet design.
- **v2 — the integrating, topology-aware control plane (roadmap).** Stop dragging requests to the cache; place for load and let the cache follow. The AMD KV-serving stack already has the primitives — [**MORI-IO**](https://vllm.ai/blog/2026-04-07-moriio-kv-connector) (AMD's own RDMA KV transport for MI300X), [**kvcached**](https://github.com/ovg-project/kvcached) (virtual-memory KV sharing across instances, ROCm-supported), [**LMCache**](https://github.com/lmcache/lmcache) (multi-tier cache), [**llm-d**](https://llm-d.ai/docs/guide/Installation/precise-prefix-cache-aware) (prefix-cache-aware routing). CacheForge does **not** reinvent these — it orchestrates them under one control plane.

**The sharp edge — MI300X-topology-aware placement.** Every generic router (Dynamo, llm-d, Mooncake) treats a GPU as one flat block. An MI300X isn't: it's 8 XCDs, each with its own HBM stack, splittable into NUMA domains via **NPS partition modes**, linked by an **xGMI mesh**. CacheForge models that topology — its KV-location directory records *which NPS partition / GPU / node* holds each prefix, and routing places cache misses/spills where a future KV **share** (same NPS partition, near-free) or **transfer** (one xGMI hop) is cheapest, instead of a topology-blind global least-loaded pick. This is genuinely unclaimed at the control-plane layer, and it's specifically an AMD problem (NVIDIA GPUs aren't structured this way). See [`/api/kv-directory`](crates/router/src/main.rs) and `CACHEFORGE_WORKER_TOPOLOGY`.

See [PITCH.md](PITCH.md) for the product/market case and honest ecosystem map, and [docs/CacheForge-Implementation-Plan.md](docs/CacheForge-Implementation-Plan.md) for the technical plan.

AMD Hackathon — Track 3 (Unicorn / Open Innovation).

## AMD Compute Usage

- **Target hardware:** AMD Instinct **MI300X** (gfx942, 192 GB HBM3) running **ROCm** + **vLLM** (`rocm/vllm`) with `--enable-prefix-caching`. Worker image: [`deploy/docker/vllm-rocm.Dockerfile`](deploy/docker/vllm-rocm.Dockerfile).
- **Why MI300X specifically:** 192 GB HBM per GPU holds far more KV-cache blocks than the prefix-cache hit horizon on smaller cards — cache-affinity routing converts that headroom directly into TTFT and throughput wins.
- **Control-plane development:** AMD **EPYC** (EC2 `c7a`/`m7a` spot) — the router is hardware-agnostic and is validated against mock vLLM workers on CPU (Track A), then pointed unchanged at ROCm vLLM workers on MI300X (Track B).
- **Autoscaling signal:** vLLM's own `/metrics` (`vllm:gpu_cache_usage_perc`, queue depth) rather than CPU% — KV-cache pressure is the real saturation signal for LLM serving.

## v1 baseline result (Track B — real MI300X)

The routing layer, measured on 1× AMD Instinct MI300X (AMD Developer Cloud)
running 4 vLLM workers (`rocm/vllm`, Qwen2.5-7B-Instruct,
`--enable-prefix-caching`). Prefill-bound workload (32 shared prefixes × 8000
chars, short outputs), 400 requests/mode, 0 errors — only the routing policy
differs. This is the honest floor the v2 fabric builds on.

| metric | round_robin | prefix_affinity | delta |
|--------|------------:|----------------:|------:|
| TTFT p50 (ms) | 87 | 61 | **−30%** |
| TTFT mean (ms) | 107 | 69 | **−36%** |
| latency p50 (ms) | 360 | 300 | −16% |
| throughput (req/s) | 20.5 | 25.8 | **+26%** |

0 errors; even worker spread under round-robin, cache-affinity spread under
prefix routing; real vLLM prefix-cache hit rate ~75%. GPU telemetry (via AMD's
device-metrics-exporter, proxied to the dashboard) reads VRAM live (164/192 GB
across the 4 workers); note the Dev Cloud MI300X is a **VF** that zeroes the
util/power/temp sensors. Reproduce with [`deploy/mi300x/`](deploy/mi300x/README.md).

## Validated result (Track A testbed)

480 requests/mode, 16 concurrent, 48 shared prefixes, 4 workers with capacity-constrained prefix caches — same binaries, only the routing policy differs:

| metric | round_robin | prefix_affinity | delta |
|--------|------------:|----------------:|------:|
| TTFT p50 (ms) | 324.2 | 77.5 | **−76%** |
| TTFT mean (ms) | 257.2 | 134.3 | −48% |
| upstream cache-hit fraction | 0.24 | 0.67 | **+180%** |
| throughput (req/s) | 15.4 | 17.7 | +15% |
| worker spread | 120/120/120/120 | 123/120/120/117 | still balanced |

Round-robin duplicates every prefix across every worker's cache and thrashes; prefix-affinity partitions the prefix space so each worker's cache stays warm. Reproduce with one command (below).

## Where this goes — the KV fabric (v2)

The baseline above exposes its own ceiling: routing **pins** a prefix to one worker. On a large fleet that means hot-prefix overload (all of one popular prompt's traffic funnels to a single GPU), cache stuck where it was computed even when that worker is busy, and duplication whenever spill-over or misses re-cache the same prefix elsewhere. Great at 4 workers, fragments at 40.

v2 inverts it: **schedule requests for load, and let the KV cache follow — by integrating the AMD-native primitives that already exist, not reinventing them.**

| scope | who already does it (integrate, don't rebuild) | CacheForge's part |
|-------|-----------------------------------------------|-------------------|
| same GPU, cross-instance sharing | [**kvcached**](https://github.com/ovg-project/kvcached) — virtual-memory KV sharing, ROCm-supported | drive it from the router's KV-location directory |
| GPU ↔ GPU / node ↔ node transport | [**MORI-IO**](https://vllm.ai/blog/2026-04-07-moriio-kv-connector) — AMD's own RDMA KV connector for MI300X | schedule which blocks move where |
| multi-tier cache offload | [**LMCache**](https://github.com/lmcache/lmcache) — CPU/disk/RDMA/NIXL, benchmarked on MI300X | policy + eviction hooks |
| prefix-cache-aware routing | [**llm-d**](https://llm-d.ai/docs/guide/Installation/precise-prefix-cache-aware) / SGLang / Dynamo | v1 here is a clean self-contained take on the same idea |

**Honest note:** these projects already solve the hard transport/sharing problems, several on AMD directly (MORI-IO is AMD's own; kvcached runs on ROCm). CacheForge's contribution is **not** a new KV-transfer mechanism — it's the missing **control plane** that turns its prefix-affinity map into a KV-location directory and orchestrates these primitives as one opinionated, one-command system with unified GPU/cache/routing observability. See [PITCH.md](PITCH.md) for the full ecosystem map.

## Quick start

```bash
# prebuilt image (linux/amd64) — router + mock-vllm + bench in one 108 MB image
docker pull docker.io/mancube/cacheforge:latest

# self-contained live demo (4 mock workers + router) — one container, no GPU:
docker run -d -p 80:8080 --restart unless-stopped docker.io/mancube/cacheforge:latest demo
#   dashboard  http://<host>/        api  http://<host>/v1/chat/completions

# native (Linux/macOS/EC2)
./scripts/demo.sh

# native (Windows)
powershell -File scripts/demo.ps1

# docker
docker compose -f deploy/compose/docker-compose.yml up --build -d
docker compose -f deploy/compose/docker-compose.yml run bench
```

The demo builds the workspace, launches 4 mock vLLM workers + the router, and runs the A/B benchmark (`x-route-mode: round_robin` vs `prefix_affinity` per request).

Point the same router at real MI300X workers by changing one env var:

```bash
CACHEFORGE_WORKERS=http://mi300x-node:8000,http://mi300x-node:8001 cacheforge-router
```

## Architecture

```mermaid
flowchart LR
  C["OpenAI client"] -->|"/v1/chat/completions (SSE)"| R["cacheforge-router · Rust/axum<br/>prefix-affinity + topology-aware spill<br/>KV-location directory · /metrics · dashboard"]
  R -->|"route + stream through"| W0
  R --> W1
  R --> WN
  subgraph FLEET["1× MI300X (192 GB HBM) · rocm/vllm workers"]
    W0["worker 0 · NPS part 0<br/>--enable-prefix-caching"]
    W1["worker 1 · NPS part 1"]
    WN["worker N · NPS part N"]
  end
  W0 -. "/metrics scrape 1s: KV pressure, queue, health" .-> R
  EX["AMD device-metrics-exporter :5000"] -. "GPU util / VRAM / temp / power" .-> R
```

### Request / event flow

```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant R as cacheforge-router
  participant A as AffinityMap (KV directory)
  participant W as vLLM worker

  C->>R: POST /v1/chat/completions
  R->>A: lookup(prompt prefix) — who holds this cache?
  alt cache home healthy & not overloaded
    A-->>R: worker H (affinity hit)
  else home overloaded
    Note over R: topology-aware spill —<br/>min(load + weight · distance(cand, home))
  else cache miss
    Note over R: least-loaded worker
  end
  R->>W: forward request
  W-->>C: stream SSE (TTFT recorded, route headers set)
  R->>A: record(prefix → chosen worker)
  Note over R,W: background loop: scrape worker /metrics every 1s<br/>(KV pressure, running/waiting, health)
```

| crate | what |
|-------|------|
| `crates/router` | OpenAI-compatible gateway: SSE streaming passthrough, prefix-affinity + round-robin routing, **MI300X-topology-aware spill** (NPS/xGMI-cost-weighted), KV-location directory (`/api/kv-directory`), health/retry, Prometheus `/metrics` |
| `crates/common` | prefix chunk chain-hashing, vLLM `/metrics` parser |
| `crates/mock-vllm` | Track-A stand-in worker: OpenAI API + vLLM-style `/metrics` + simulated prefix cache with capacity eviction |
| `crates/bench` | shared-prefix workload generator, A/B TTFT/throughput comparison |

Routing decisions are observable per request (`x-cacheforge-worker`, `x-cacheforge-route` response headers) and in aggregate (`router_route_decisions_total{decision=...}` on `/metrics`).

## Live dashboard

The router serves a self-contained monitoring page at `/` (also `/dashboard`), auto-refreshing every 2 s — no Grafana, no external deps:

- **GPU** — util, VRAM, temp, power per Instinct GPU, from AMD's `rocm/device-metrics-exporter` proxied same-origin at `/gpu/metrics` (set `CACHEFORGE_GPU_EXPORTER=http://127.0.0.1:5000/metrics`). This fills the gap where the AMD Dev Cloud console shows no Instinct GPU telemetry.
- **Workers** — per-worker KV-cache usage, in-flight, queue depth, health.
- **Routing** — TTFT p50/p95, affinity hit rate, decision breakdown.

Aggregate JSON at `/api/stats`. GPU panel degrades gracefully to "unavailable" when no exporter is configured (e.g. Track A).

## Router configuration

| env | default | meaning |
|-----|---------|---------|
| `CACHEFORGE_WORKERS` | — (required) | comma-separated worker base URLs |
| `CACHEFORGE_PORT` | `8080` | listen port |
| `CACHEFORGE_MODE` | `prefix_affinity` | `round_robin` \| `prefix_affinity` |
| `CACHEFORGE_AFFINITY_TTL_SECS` | `300` | prefix entry TTL |
| `CACHEFORGE_OVERLOAD_MARGIN` | `8` | load gap before spilling off the warm worker |
| `CACHEFORGE_ALLOW_MODE_OVERRIDE` | `1` | honor per-request `x-route-mode` header (bench/A-B) |

## Roadmap

Per the [implementation plan](docs/CacheForge-Implementation-Plan.md): Phase 2 adds the `kube-rs` operator (`LLMFleet` CRD, KV-pressure autoscaling, live worker registry), Phase 3 the dashboard + MI300X headline benchmark, Phase 4 hardening (drain on spot interruption, circuit breaking).

## Development

```bash
cargo test --workspace      # 23 unit tests: radix map, scorer, metrics parser, SSE prompt extraction
cargo clippy --workspace --all-targets
```

ROCm/vLLM field guide (gfx942 arch pinning, hipBLASLt warmup, HIP graph fallbacks, container GPU flags): plan section 7.
