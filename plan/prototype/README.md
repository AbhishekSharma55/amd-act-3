# Scratch prototype (not product code)

These scripts were written on October 15, 2026, only to check that the example fixture produces a useful demo story, and to generate the files in `../mocks/`. They are deliberately rough. The product code goes in `backend/` and follows `../04_BACKEND_GUIDE.md`.

| File | Purpose |
| --- | --- |
| `fixture.json` | The example factory without the committed schedule |
| `baseline.json` | The committed schedule (computed once, then kept fixed) |
| `proto.py` | CP-SAT prototype. `python3 proto.py fixture.json out.json` prints the demo outcomes for each policy. It **recomputes** a baseline, which may differ from `baseline.json` |
| `replay_proto.py` | NumPy replay prototype |
| `gen_mocks.py` | Rebuilds every file in `../mocks/` from `fixture.json` + `baseline.json` |

To regenerate the mocks after changing the fixture (needs `pip install ortools numpy`):

```bash
cd plan/prototype
python3 gen_mocks.py ../mocks
```

If you change the fixture or the baseline, update the outcome tables in `../02_DATA_MODEL.md` and `../06_TECH_RESEARCH.md` to match the new output.
