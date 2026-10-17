"""Environment settings. Values come from the process environment or a local .env file."""
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


AMD_API_BASE = os.getenv("AMD_API_BASE", "").strip()
AMD_API_KEY = os.getenv("AMD_API_KEY", "").strip()
AMD_MODEL = os.getenv("AMD_MODEL", "").strip()
AMD_TIMEOUT_S = float(os.getenv("AMD_TIMEOUT_S", "30"))
# Sent only if set; some thinking models accept "low" to cut latency.
AMD_REASONING_EFFORT = os.getenv("AMD_REASONING_EFFORT", "").strip()
# Set to 0 if the portal's model rejects response_format.
AMD_JSON_MODE = _flag("AMD_JSON_MODE", "1")

# A labeled rule-based fallback is used only when this is on and the AMD call fails or is not configured.
ALLOW_RULE_FALLBACK = _flag("ALLOW_RULE_FALLBACK", "0")

FIXTURE_PATH = Path(os.getenv("FIXTURE_PATH", ROOT / "shared" / "fixture.json"))
# The built frontend: `npm run build` writes frontend/dist; a container may copy it to backend/static.
STATIC_DIR = Path(os.getenv("STATIC_DIR") or next((p for p in (ROOT / "backend" / "static", ROOT / "frontend" / "dist")
                                                  if (p / "index.html").exists()), ROOT / "frontend" / "dist"))
RUN_TTL_S = int(os.getenv("RUN_TTL_S", str(6 * 3600)))
# Oldest runs are dropped beyond this many, so a long-running demo cannot grow memory without bound.
MAX_RUNS = int(os.getenv("MAX_RUNS", "2000"))
# /api/extract calls per client per minute (0 = unlimited); the shared Token Factory key has a small quota.
EXTRACT_RATE_PER_MIN = int(os.getenv("EXTRACT_RATE_PER_MIN", "12"))
SOLVER_WORKERS = int(os.getenv("SOLVER_WORKERS", str(min(8, os.cpu_count() or 2))))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# cpu-numpy, or gpu-torch-rocm once the optional GPU replay (#15) exists.
REPLAY_DEVICE = "cpu-numpy"
MAX_MESSAGE_CHARS = 1000
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
TIMEZONE = os.getenv("FACTORY_TZ", "Asia/Kolkata")


def amd_configured() -> bool:
    return bool(AMD_API_BASE and AMD_API_KEY and AMD_MODEL)


def amd_host() -> str | None:
    return urlparse(AMD_API_BASE).hostname if AMD_API_BASE else None
