"""Generate reproducible saved checker records; no HTTP, AMD, or solver call."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .checker import check


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "shared" / "checker-reports.json"
SOURCE_FILES = {
    "fixture": "shared/fixture.json",
    "extract": "shared/mocks/extract.json",
    "solve": "shared/mocks/solve.json",
    "checker": "backend/app/checker.py",
}


def generate_report() -> dict:
    sources = {name: {"path": relative, "sha256": hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}
               for name, relative in SOURCE_FILES.items()}
    fixture = json.loads((ROOT / SOURCE_FILES["fixture"]).read_text(encoding="utf-8"))
    extract = json.loads((ROOT / SOURCE_FILES["extract"]).read_text(encoding="utf-8"))
    solve = json.loads((ROOT / SOURCE_FILES["solve"]).read_text(encoding="utf-8"))
    constraints = extract["constraints"]
    recovery = solve["alternatives"][0]["schedule"]
    reports = {
        "committed": check(fixture, [], fixture["committed_schedule"]),
        "recovery": check(fixture, constraints, recovery),
        "disrupted_committed": check(fixture, constraints, fixture["committed_schedule"]),
    }
    expected = {"committed": True, "recovery": True, "disrupted_committed": False}
    for name, valid in expected.items():
        if reports[name]["valid"] is not valid:
            raise ValueError(f"Refusing to save unexpected {name} result: {reports[name]}")
    return {
        "format_version": 1,
        "reports": reports,
        "provenance": {
            "description": "Saved independent checks of synthetic fixture/mock records; not a live backend validation or AMD request.",
            "synthetic": True,
            "amd_request_made": False,
            "source_files": sources,
            "checked_inputs": {
                "committed": {"fixture": "shared/fixture.json", "constraints": [],
                              "schedule": "shared/fixture.json#/committed_schedule"},
                "recovery": {"fixture": "shared/fixture.json", "constraints": "shared/mocks/extract.json#/constraints",
                             "schedule": "shared/mocks/solve.json#/alternatives/0/schedule"},
                "disrupted_committed": {"fixture": "shared/fixture.json", "constraints": "shared/mocks/extract.json#/constraints",
                                        "schedule": "shared/fixture.json#/committed_schedule"},
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if saved results or source hashes differ from current inputs")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        encoded = json.dumps(generate_report(), indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if args.output.read_text(encoding="utf-8") != encoded:
                print(f"Saved checker reports are stale: {args.output}", file=sys.stderr)
                return 1
            print("Saved checker reports and source hashes are current.")
        else:
            args.output.write_text(encoded, encoding="utf-8")
            print(f"Wrote saved checker reports: {args.output}")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"Cannot produce verified checker reports: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
