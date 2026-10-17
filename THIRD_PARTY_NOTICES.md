# Third-party notices and provenance

The root [MIT License](LICENSE) covers this team's original application code,
documentation and synthetic demo data. It does not replace licenses or rights
belonging to dependency authors, font designers, model publishers, AMD, event
organizers or authors of archived research sources.

## Dependency inventory

[`licenses/inventory.json`](licenses/inventory.json) records the versions and
license metadata inspected on 18 October 2026 (IST): 35 installed Python
runtime distributions from the verified application image, eight additional
development-only Python distributions from the local verification environment,
and 44 npm lockfile entries including optional platform variants. It is a
snapshot, not a lockfile or complete native-library/operating-system SBOM.

| Direct application dependency | Version | Upstream license | Preserved notices |
| --- | --- | --- | --- |
| FastAPI | 0.143.3 | MIT | [Python notices](licenses/PYTHON_NOTICES.txt) |
| Uvicorn and standard extras | 0.54.0 | BSD-3-Clause; extras have their own licenses | [Python notices](licenses/PYTHON_NOTICES.txt) |
| Google OR-Tools | 9.15.6755 | Apache-2.0 | [Python notices](licenses/PYTHON_NOTICES.txt) |
| NumPy | 2.5.4 | BSD-3-Clause plus bundled component terms | [Python notices, including NumPy's bundled notices](licenses/PYTHON_NOTICES.txt) |
| OpenAI Python client, used with AMD | 3.33.0 | Apache-2.0 | [Python notices](licenses/PYTHON_NOTICES.txt) |
| python-dotenv | 1.2.4 | BSD-3-Clause | [Python notices](licenses/PYTHON_NOTICES.txt) |
| React / React DOM | 19.3.1 | MIT | [JavaScript notices](licenses/JAVASCRIPT_NOTICES.txt) |
| Vite | 8.3.4 | MIT, with bundled dependency notices | [JavaScript notices](licenses/JAVASCRIPT_NOTICES.txt) |
| Vite React plugin | 6.1.2 | MIT | [JavaScript notices](licenses/JAVASCRIPT_NOTICES.txt) |

The inventory also includes transitive distributions such as pandas, protobuf,
Starlette, Pydantic and the React scheduler, plus pytest/httpx development tools.
Full package-provided copyright/license texts are retained in the linked bundles;
individual packages remain under their own terms. The NumPy and JavaScript
bundles retain their additional embedded notices rather than reducing every
component to its top-level license label.

Lightning CSS (MPL-2.0) is a frontend build dependency; certifi (MPL-2.0) is in
the inspected Python development environment. Neither is authored or relicensed
by this team. The application distributes no modified source files from those
projects. Exact source locations and package archive integrity values are in
the inventory. Optional npm platform variants are listed from the lockfile;
where their archives share a family notice, the inventory identifies that source.

New Docker builds include `LICENSE`, this document and `licenses/` under `/app`.
Installed Python distribution license files and the base image's own copyright
files are retained. Node 22 is a build stage; the Python 3.12 slim-bookworm
runtime also includes Debian/system libraries with their own notices under
`/usr/share/doc`, and Python's notice at
`/usr/local/lib/python3.12/LICENSE.txt`. The inventory
does not claim to enumerate every OS package, native library or compiler runtime.
Review upstream package notices again when dependencies or base images change.

## Fonts

The application serves local WOFF2 assets from `frontend/public/fonts/`:

- **DM Sans:** copyright 2014 The DM Sans Project Authors;
  [SIL Open Font License 1.1](frontend/public/fonts/DM-Sans-OFL.txt).
- **Manrope:** copyright 2018 The Manrope Project Authors;
  [SIL Open Font License 1.1](frontend/public/fonts/Manrope-OFL.txt).

The original notices are copied into the built frontend and remain available
alongside the font files. They are not covered by the project's MIT grant.

## Hosted model and platform

The configured AMD Token Factory model is `DeepSeek-V4-Flash`. Saved live
responses identify it as `self-dploy/DeepSeek-V4-Flash`; that provider identifier
is retained without claiming a particular checkpoint hash or GPU configuration.

DeepSeek's [official upstream model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)
and [license](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/LICENSE)
identify the upstream repository and weights as MIT licensed, copyright
2023 DeepSeek. A [copy of that notice](licenses/DeepSeek-V4-Flash-LICENSE.txt)
is retained for attribution. **This repository and image distribute no model
weights.** The application uses an organizer-provided hosted API; service access,
quotas, account terms and the provider's exact deployment are separate from the
upstream model's license. Changing models requires checking the new publisher's
terms and updating these notices.

AMD and other product/event names identify the services used. Their names,
logos and trademarks remain the property of their respective owners; the
project's license grants no rights in them.

## Demo data and research archive

`shared/fixture.json`, recorded examples, evaluation messages and recovery cases
are team-authored synthetic data. Customer names, orders, machine durations,
cost units and uncertainty distributions illustrate the product; they do not
describe an actual factory. The application loads no external scheduling dataset
or model-training dataset.

`context/` preserves participant-supplied hackathon material. `research/sources/`
and `research/astra/` preserve third-party page/repository excerpts and snapshots
for research provenance; source URLs and retrieval information are in
[`research/source-index.json`](research/source-index.json),
[`research/web-evidence.json`](research/web-evidence.json) and
[`research/README.md`](research/README.md). Their inclusion does not transfer
ownership or relicense them under MIT. Referenced datasets/repositories in that
archive are not runtime dependencies merely because they were researched.

The original archive/history is preserved and is excluded from the Docker build.
Repository visibility and the appropriate public submission packaging of that
archive remain part of final submission preparation; this documentation change
does not publish it or change repository visibility.
