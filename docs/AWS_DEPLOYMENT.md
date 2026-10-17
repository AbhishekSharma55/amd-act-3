# Public AWS deployment — 18 October 2026 (IST)

**Live application:** https://rehearsal-act3.aa0brkr65f1ep.us-east-1.cs.amazonlightsail.com/

AWS Lightsail Container Service serves the built frontend and FastAPI API from
one managed HTTPS address. AMD extraction calls Token Factory from the server;
the solver, independent checker and NumPy replay run on the container's CPU.
All factory data is synthetic.

## Running configuration

| Item | Value |
| --- | --- |
| Region / service | `us-east-1` / `rehearsal-act3` |
| Size / instances | Small: 0.5 shared vCPU, 1 GB RAM / **one instance** |
| Application revision | `9e3e260a94b21c3b9b2506d03b47bf6eacfebd00` |
| Registered image | `:rehearsal-act3.app-9e3e260.1` |
| Uploaded image digest | `sha256:3dafd0a15033db83ef6dca63818ca574fa5cb148ac9d90469844b6798c4d4b39` |
| Application port / health path | HTTP `7860` / `/api/health` |
| AMD model / fallback | `DeepSeek-V4-Flash` / disabled |
| API / solver workers | One Uvicorn process / one CP-SAT worker |
| In-memory run limit / expiry | 250 runs / six hours |

The Mumbai region initially rejected provisioning because its quota was zero;
no service was created there. The running service is in Northern Virginia.
TLS is managed by Lightsail. No custom domain, load balancer, database, GPU,
ECR repository or autoscaling service was added.

The AMD key is supplied in the service's runtime environment. The image build
context and Git exclude `.env`. Only authorized AWS account principals can
read or change service environment settings. Full Lightsail deployment API
responses include that environment: use the filtered commands below when
sharing diagnostics.

## Cost and scheduled expiry

| Usage | Estimated hosting cost, before tax and credits |
| --- | ---: |
| One day, using 730 hours per month | **$0.49** |
| One month, continuously running | **$15.00** |
| Scheduled 28-day lifetime | **$13.81** |

At an illustrative 18% tax, those estimates are $0.58/day, $17.70/month and
$16.29 for 28 days. Actual tax depends on the billing account. Existing AWS
credits may offset eligible usage; the table deliberately excludes credits.
The plan includes 500 GB/month transfer. Excess transfer can add charges.
The personal budget remains $20; AMD's allocation is separate.

Prices were checked against the AWS service API and
[Lightsail pricing](https://aws.amazon.com/lightsail/pricing/). Daily and
28-day figures are prorated estimates using the $15 monthly rate and 730 hours;
actual invoice rounding may differ. A disabled service still incurs charges;
[delete it to stop service billing](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-containers.html).

An enabled, one-time EventBridge Scheduler job deletes **this container
service** at **14 November 2026, 18:31:47 UTC / 15 November 2026, 00:01:47 IST**,
28 days after creation. Redeploying the image does not extend the timer.
The execution role allows only `lightsail:DeleteContainerService` on this
service ARN. Its trust is limited to this account and schedule group.
The schedule deletes itself after completion and retries failed invocations.
IAM and Scheduler configuration is recorded under
[`deploy/lightsail/`](../deploy/lightsail/).

This expiry is an automated cleanup attempt, not a hard billing cap. The role's
resource-specific permission simulation and the enabled schedule were checked;
the future deletion has not been executed. Confirm deletion in AWS after the
expiry. IAM role/group leftovers do not keep the application running.

## Verification

- The image passed the complete offline workflow with a local limit of
  0.5 CPU and 1 GB RAM; observed container memory was about 131 MiB without OOM.
- The deployed HTTPS URL passed all seven live
  [workflow check groups](../deploy/lightsail/verification/public_live.json):
  real AMD extraction, exact agreed demo facts, CPU solving, independent
  checking, 500-scenario replay, concession approval, CSV/JSON export,
  idempotency and evidence locking. Fallback was disabled.
- A [fresh isolated Chrome session](../deploy/lightsail/verification/browser_live.json)
  completed the same live workflow and read both exported download blobs.
  Desktop (1440×1000) and emulated phone (390×844) layouts loaded without
  sign-in; the completed flow and a fresh visit fit the phone viewport.
  No JavaScript exceptions or failed HTTP responses occurred. A physical phone
  was not available for this check. [Desktop](../deploy/lightsail/verification/desktop.png)
  and [phone](../deploy/lightsail/verification/mobile.png) screenshots are saved.

AMD response time varied: 7,866 ms with one attempt in the public API check,
and 53,374 ms with two attempts in the browser check. Both produced the correct
demo proposals. The live model can be slow; the UI stays in its working state
while the configured retry completes. These two observations are functional
checks, not a latency benchmark or availability guarantee.

Reproduce from the repository root; this makes one actual AMD request:

```bash
python3 scripts/container_smoke.py \
  https://rehearsal-act3.aa0brkr65f1ep.us-east-1.cs.amazonlightsail.com \
  --mode amd --save-to /tmp/rehearsal-public-check.json
```

The service is provisioned continuously; there is no configured idle suspension.
In a [short idle check](../deploy/lightsail/verification/idle_health.json), health
returned HTTP 200 in 1.209 seconds before and 1.124 seconds after 79.33 seconds
without application requests. Platform health probes continued. This does not
establish long-term availability or a suspend/resume guarantee.
Runs and approvals are process memory. Restarting or redeploying loses them;
download exports before an update. Keep **one instance and one API worker**.
The small host is intended for a hackathon demo; concurrent load was not tested.

## Inspect and update

AWS CLI authentication is already configured on the deployment machine.
Install Docker and the official
[Lightsail CLI plugin](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-install-software.html)
to upload images. If the local shell does not yet have Docker group access,
use `sg docker -c 'COMMAND'` or open a new login session.

```bash
aws lightsail get-container-services --service-name rehearsal-act3 \
  --region us-east-1 \
  --query 'containerServices[0].{state:state,power:power,scale:scale,url:url,current:currentDeployment.{version:version,state:state},next:nextDeployment.{version:version,state:state}}'

aws scheduler get-schedule --name rehearsal-act3-expiry \
  --group-name rehearsal-act3 --region us-east-1 \
  --query '{state:State,at:ScheduleExpression,zone:ScheduleExpressionTimezone,target:Target.Arn}'

docker build --tag rehearsal:local .
aws lightsail push-container-image --service-name rehearsal-act3 \
  --label app-REVISION --image rehearsal:local --region us-east-1

# Use the registered image name printed by the upload; requires python-dotenv
# from backend/requirements.txt and AMD settings in the ignored root .env.
.venv/bin/python deploy/lightsail/deploy.py --image :rehearsal-act3.app-REVISION.VERSION
```

The helper constructs a mode-0600 temporary deployment request, deletes it on
exit, redacts the key from AWS errors and prints only filtered status fields.
It preserves the one-instance service and uses an explicit runtime settings
allowlist. Wait for `RUNNING` with the current deployment `ACTIVE`, then repeat
the public workflow check. Update the recorded source revision and verification
artifacts when shipping another image.

To recreate infrastructure, first create a Small, scale-one Lightsail container
service and wait for `READY` before uploading. The checked-in expiry JSON is
specific to this account, service ARN and original expiry; adapt it to the new
service before creating its IAM role, schedule group and schedule. Scheduler's
universal target requires `ServiceName` with a capital S, as recorded in the
validated schedule request. Do not reuse an expired date for a new deployment.

## Stop early

These commands remove only this project's resources. Export any desired
decisions first. Delete the service before removing its cleanup schedule.

```bash
aws lightsail delete-container-service --service-name rehearsal-act3 --region us-east-1
aws scheduler delete-schedule --name rehearsal-act3-expiry --group-name rehearsal-act3 --region us-east-1
aws scheduler delete-schedule-group --name rehearsal-act3 --region us-east-1
aws iam delete-role-policy --role-name RehearsalLightsailExpiry --policy-name DeleteOnlyRehearsal
aws iam delete-role --role-name RehearsalLightsailExpiry
```

After automatic expiry, the schedule may already be absent. Check the service
is gone, then remove the remaining group and role if desired. The local Compose
container is independent of AWS and can be stopped with `docker compose down`.
