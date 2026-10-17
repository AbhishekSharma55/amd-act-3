"""Container entry point: validate packaged inputs, then run one API/UI process."""
import logging
import os

import uvicorn

from . import config
from .fixture import FixtureError, get_fixture


def main():
    try:
        port = int(os.environ.get("PORT", "7860"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("PORT must be an integer from 1 to 65535.") from None
    if not (config.STATIC_DIR / "index.html").is_file():
        raise SystemExit("Built frontend is missing. Build the Docker image or set STATIC_DIR to the built frontend.")
    try:
        get_fixture()
    except FixtureError as exc:
        raise SystemExit(str(exc)) from None
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.amd_configured():
        logging.getLogger(__name__).warning(
            "AMD is not configured. Extraction will %s.",
            "use the labeled rule fallback" if config.ALLOW_RULE_FALLBACK else "return amd_not_configured (503)")
    # Runs, approvals and rate limits are process-local. Always keep one worker,
    # including on hosts that set WEB_CONCURRENCY automatically.
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1, log_level=config.LOG_LEVEL.lower())


if __name__ == "__main__":
    main()
