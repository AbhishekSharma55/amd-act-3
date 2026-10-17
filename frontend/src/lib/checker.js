/** Fail closed: incomplete or inconsistent records must never show a pass. */
export function checkerState(result) {
  if (
    !result ||
    typeof result.valid !== "boolean" ||
    !Array.isArray(result.violations) ||
    result.violations.some(
      (violation) => typeof violation !== "string" || !violation.trim(),
    ) ||
    result.valid !== (result.violations.length === 0)
  ) {
    return { status: "unavailable", label: "Not checked", violations: [] };
  }
  return {
    status: result.valid ? "passed" : "failed",
    label: result.valid ? "Passed checks" : "Plan rejected",
    violations: result.violations,
  };
}
