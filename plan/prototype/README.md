# Scratch prototype (not product code)

These scripts check that the example fixture produces a useful demo story and generate `../mocks/`. The original October 15 examples have been corrected during PR review. They remain planning examples; product code goes in `backend/` and follows `../04_BACKEND_GUIDE.md`.

| File | Purpose |
| --- | --- |
| `fixture.json` | The example factory without the committed schedule |
| `baseline.json` | The committed schedule (computed once, then kept fixed) |
| `proto.py` | CP-SAT prototype. `python3 proto.py fixture.json out.json` prints the demo outcomes for each policy. It **recomputes** a baseline, which may differ from `baseline.json` |
| `replay_proto.py` | NumPy replay prototype |
| `gen_mocks.py` | Rebuilds every file in `../mocks/` from `fixture.json` + `baseline.json` |
| `regression_checks.py` | Executes the backend guide's examples and checks input validation, overtime bounds/cost, effective due dates, replay identity/running work, and server-owned approval |

To regenerate the mocks after changing the fixture (reviewed with `pip install ortools==9.15.6755 numpy==2.5.4` in an isolated environment):

```bash
cd plan/prototype
python3 gen_mocks.py ../mocks
```

Run focused checks from the repository root:

```bash
python3 plan/prototype/regression_checks.py
```

The checks load Python examples directly from the backend guide, so copied documentation code is tested too. They do not call AMD or run a web application. Verified during review with Python 3.14.4, OR-Tools 9.15.6755 and NumPy 2.5.4; install compatible packages in an isolated environment.

Replay keeps planned start floors, observed starts and elapsed work fixed; only unstarted durations and running operations' remaining work are randomized. The corrected demo result is J4 on time in **239/500**, with a worst sampled miss of **61 minutes**, replacing the old 211/500 result. If you change the fixture, baseline or simulator, regenerate the mocks and update all outcome tables and demo wording. The baseline remains fixed data.
