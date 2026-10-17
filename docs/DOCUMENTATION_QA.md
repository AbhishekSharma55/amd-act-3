# Documentation verification — 18 October 2026 (IST)

The documentation describes the implemented app and preserves the earlier
research and feature reports. Runtime application logic and evaluation labels
were unchanged. Docker packaging adds license notices; its environment-file
exclusions and single-worker entry point remain in place.

## Clean-checkout checks

A new local Git clone of the documentation branch was used, with no real `.env`,
credentials, `node_modules` or frontend build output copied from the working
directory. A separate Compose project, image tag and host port avoided changing
the existing local app or AWS deployment.

| Check | Observed result |
| --- | --- |
| Copy `.env.example`, Compose build/start without AMD key | Production frontend/API started; strict smoke passed all four groups, including `amd_not_configured` |
| Documented offline Compose command | All seven fallback workflow groups passed: actual CPU solve, checker, replay, concessions, approval and exports |
| Empty AMD overrides | A fake key canary in the test checkout's `.env` was overridden by explicit empty AMD values; health confirmed unconfigured AMD before the offline workflow |
| New license packaging | Project/third-party notices, inventory, upstream model notice and both font OFL files were present in the image |
| Build-context protection | `licenses/.env.docker-canary` stayed outside the image despite the new `licenses/` allowlist |
| Runtime inventory | Every Python runtime name/version in `licenses/inventory.json` matched the built image; UID remained 1000 |
| `npm --prefix frontend ci`, `test`, `run build` | Fresh install, 31 passing tests, production build succeeded |
| Documented integrated backend entry | `python -m uvicorn app.main:app --app-dir backend` served the clean source checkout and its built frontend in the Python 3.12 image; all four strict smoke groups passed |
| Saved-prediction rescoring | Reproduced Abhishek's 21/23 complete changes, zero false acceptances, 9/10 useful review, zero errors without a model request |
| Architecture diagram | Parsed successfully with Mermaid in a DOM-capable environment |
| Local Markdown links and anchors | Resolved in the changed guides |
| License bundle integrity | SHA-256 hashes matched the inventory |
| Credential scan | Current AMD key exact match plus `rc-` and AWS access-key-ID patterns: no findings across 454 local Git blob objects or the new documentation files |

The native backend entry was exercised using Python 3.12 from the container,
bound to the clean checkout. The native host has a different Python version;
the complete host Python 3.12 virtual-environment installation was not separately
repeated. Windows commands are documented but were not executed on Windows.
The credential scan is a scoped check, not a claim that every possible secret
format has been audited. No AMD inference, AWS deployment or paid-resource
creation was needed for these checks.

## Reproduce

From a fresh checkout with Docker installed:

```bash
cp .env.example .env
docker compose up --build --detach
python3 scripts/container_smoke.py http://localhost:7860 --mode strict

AMD_API_BASE= AMD_API_KEY= AMD_MODEL= ALLOW_RULE_FALLBACK=1 \
  docker compose up --build --detach
python3 scripts/container_smoke.py http://localhost:7860 --mode fallback
docker compose down

npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
```

For the strict check, leave the example key empty and ensure the shell supplies
no AMD credential overrides. For an already configured checkout, use isolated
containers as shown in the [Docker guide](DOCKER.md). Port overrides follow that
guide; verification here used port 17868 to preserve the existing app on 7860.

The saved live AMD and public AWS records remain the evidence for actual AMD
inference. These documentation checks do not replace those records or reconcile
the provisional evaluation labels. Video, slides, public repository access,
joint final QA and actual submission remain separate tasks.
