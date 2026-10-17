"""Phase 0 check: one real Token Factory call. Records model, host, JSON mode and latency, never the key.

Run from the repo root after filling .env:
    .venv/Scripts/python backend/scripts/amd_smoke.py            # demo message with AMD_MODEL
    .venv/Scripts/python backend/scripts/amd_smoke.py --models   # list models the key can use
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.extract import ExtractionError, _get_client, extract_amd  # noqa: E402
from app.fixture import get_fixture  # noqa: E402
from app.validate import validate_constraints  # noqa: E402

SMOKE = [
    "Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval.",
    "Big mill is out till 2pm, J7 must ship by 4.",
    "Lathe stopped, no idea when it will be fixed.",
    "J7 ships at 15:00. Correction: J7 ships at 16:30.",
    "Can someone order more coffee for the break room?",
]


def main():
    if not config.amd_configured():
        sys.exit("Set AMD_API_BASE, AMD_API_KEY and AMD_MODEL in .env first.")
    if "--models" in sys.argv:
        for m in _get_client().models.list():
            print(m.id)
        return
    F = get_fixture()
    messages = SMOKE if "--all" in sys.argv else SMOKE[:1]
    out_dir = config.ROOT / "eval" / "smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, msg in enumerate(messages, 1):
        t0 = time.perf_counter()
        try:
            result = extract_amd(msg, F)
        except ExtractionError as e:
            print(f"[{i}] FAILED ({e.code}): {e}")
            continue
        constraints = validate_constraints(msg, result["constraints"], F)
        record = {"message": msg, "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                  "trace": result["trace"], "validated": constraints,
                  "wall_ms": round((time.perf_counter() - t0) * 1000)}
        path = out_dir / f"smoke_{i:02d}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        t = result["trace"]
        print(f"[{i}] model={t['model']} host={t['host']} json_mode={t.get('json_mode')} latency={t['latency_ms']} ms "
              f"attempts={t['attempts']} -> {[(c['type'], c['status']) for c in constraints]}  saved {path.name}")


if __name__ == "__main__":
    main()
