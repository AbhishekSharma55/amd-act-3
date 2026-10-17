# Abhishek's extraction labels

`abhishek.jsonl` contains Abhishek's expected answers for all 23 source messages
in their original order. The interpretation decisions and scoring limits are
documented below. Reconciliation with Muskan's answers remains pending.

## Sources

The inputs were `eval/messages.jsonl` from evaluation commit
`075170f62d22d4f5c4fbcec77c9523fe19e62b2f`, `shared/fixture.json`, and the product
constraint contract in `plan/02_DATA_MODEL.md`. The fixture says now is 10:00,
normal shift end is 18:00, and maximum overtime end is 20:00.

## Preserve these interpretation decisions

- **m01:** `allowed: true` permits consideration of overtime; it does not mean
  the final concession has already been approved. No cutoff was explicitly
  stated, so no cutoff is included in the label.
- **m04/m13:** Afternoon times are tentative proposals that still require AM/PM
  confirmation. The hard-date wording is clear. The unconfirmed clock fields
  are omitted from matched parameters and described in each row's notes.
- **m05/m07:** Unknown repair end and vague outage start stay unknown (`null`).
- **m06/m15:** Preserve the unknown references instead of inventing a mapping.
- **m10:** The explicit correction supersedes 15:00 with 16:30. Hard versus soft
  remains unresolved; `hard` is omitted and review is required.
- **m11/m16/m18:** Unsupported requests require manual handling. Unsupported
  free-text explanations are not exact string targets. m18 retains its valid
  machine outage as a separate fact.
- **m19/m20/m22:** Relative durations use the fixed fixture clock and normal
  shift end. One hour of overtime ends at 19:00.
- **m23:** The malicious instruction must not change computed order outcomes;
  the outage itself remains a valid scheduling fact.

## Scoring and reconciliation

The existing runner compares the subset of fields in each expected `params`
object and checks whether *any* item in a message requires review. It does not
verify review of the specific uncertain field. For example, m04 or m13 could
incorrectly pass if a guessed clock were accepted while a different item raised
review. The row notes record the intended behavior; they are not enforced by
the current scorer. Empty `params` on `unsupported` items also check the type,
not whether the explanatory prose identifies the right issue.

Keep those limits visible when interpreting results. The subset labels must not
be described as proof that each ambiguity was handled correctly.

This change creates **no `final.jsonl`**, performs no reconciliation with
Muskan's answers, and runs no extractor. The existing evaluation runner will
continue reporting its draft label status until reconciliation is completed.
Compare the two label sets and agree the final answers as the next labeling
step. No live AMD execution is established by this file.
