"""Deploy the built Rehearsal image using AWS CLI; keep AMD credentials out of logs/files in Git.

python deploy/lightsail/deploy.py --image :rehearsal-act3.app-9e3e260.1
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Image registered by lightsail push-container-image.")
    args = parser.parse_args()
    metadata = json.loads((Path(__file__).parent / "deployment.json").read_text())
    env = dotenv_values(ROOT / ".env")
    for name in ("AMD_API_BASE", "AMD_API_KEY", "AMD_MODEL"):
        if not env.get(name):
            raise SystemExit(f"Set {name} in the ignored .env first.")
    key = env["AMD_API_KEY"]
    settings = {name: env.get(name) or default for name, default in {
        "AMD_API_BASE": "", "AMD_API_KEY": "", "AMD_MODEL": "", "AMD_TIMEOUT_S": "30",
        "AMD_JSON_MODE": "1", "AMD_REASONING_EFFORT": "", "EXTRACT_RATE_PER_MIN": "12",
        "EXTRACT_GLOBAL_PER_MIN": "15", "FACTORY_TZ": "Asia/Kolkata", "RUN_TTL_S": "21600",
    }.items()}
    settings.update({"PORT": "7860", "ALLOW_RULE_FALLBACK": "0", "SOLVER_WORKERS": "1",
                     "MAX_RUNS": "250", "CORS_ORIGINS": "", "LOG_LEVEL": "INFO"})
    payload = {"serviceName": metadata["name"],
               "containers": {"rehearsal": {"image": args.image, "environment": settings,
                                             "ports": {"7860": "HTTP"}}},
               "publicEndpoint": {"containerName": "rehearsal", "containerPort": 7860,
                                  "healthCheck": {"path": "/api/health", "successCodes": "200",
                                                  "intervalSeconds": 15, "timeoutSeconds": 5,
                                                  "healthyThreshold": 2, "unhealthyThreshold": 3}}}
    # NamedTemporaryFile uses mode 0600. The credential payload is deleted on success or failure.
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", prefix="rehearsal-secret-") as temporary:
        json.dump(payload, temporary)
        temporary.flush()
        result = subprocess.run([
            "aws", "lightsail", "create-container-service-deployment", "--region", metadata["region"],
            "--cli-input-json", "file://" + temporary.name, "--no-cli-pager", "--output", "json",
            "--query", "containerService.{state:state,url:url,nextDeployment:nextDeployment.{version:version,state:state}}",
        ], capture_output=True, text=True, env={**os.environ, "AWS_PAGER": ""})
    if result.returncode:
        raise SystemExit(result.stderr.replace(key, "[REDACTED]"))
    print(result.stdout.replace(key, "[REDACTED]").strip())
    metadata["image"] = args.image
    (Path(__file__).parent / "deployment.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
