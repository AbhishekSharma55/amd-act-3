# Deadline interpretation preservation — issue #30

Revalidation now starts from the original server-stored proposals and overlays
only the fields the planner changed. A default in a normalized response does
not establish that the model supplied that value. Changing one field also no
longer confirms an interpretation of another field on the same constraint.

The reproduction is `Mill 4 is down until 14:00. J7 must ship at 12:00.`, with a
model proposal that omits the deadline's `hard` flag. Mapping the outage to M1
leaves the deadline in review, including after repeated revalidation. Clearing
client warnings or claiming `status: ok` does not bypass the decision. Explicit
acceptance or setting the hard flag can resolve it; changing only the date's
time cannot. Rejecting one of two conflicting dates still clears that conflict.

## Verification

- On the extraction parent: **92 backend tests and 97 subtests pass**, including
  six new regression cases. Four of those cases failed before the fix.
- In an isolated checkout combining PRs #22–#29 and both bug fixes: **132 backend
  tests, 97 subtests, 31 frontend tests, production build, checker freshness and
  20 planning regressions pass**.
- A production-build Chrome check confirmed that mapping the machine leaves
  the deadline warning visible and planning disabled; the actual `/api/solve`
  endpoint returns **422 `review_required`** for that revalidated payload.
  Explicit acceptance enables planning. The full combined workflow passed
  eight browser checks, including the replay fix and approval/export.

API/browser interpretation used deterministic local stubs. No AMD inference or
paid resource was used. This verifies the decision gate, not AMD availability.

From this feature checkout, with backend development dependencies installed:

```bash
AMD_API_KEY='' AMD_API_BASE='' AMD_MODEL='' python -m pytest -q backend/tests
```

The fix PR targets the active extraction branch behind #23. Merge it there
before integrating #23 into main; if #23 lands first, retarget the fix to main.
