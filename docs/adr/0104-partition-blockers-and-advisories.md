# 0104: Separate report blockers from full-context advisories in a diagnostic contract

Date: 2026-09-22. Status: development experiment; not product adoption.

Latest evidence: three selected controls passed, but the original attribution
negative returned pass on 651a207 (CI 35697455886). The attribution was absent
from both issues and advisories. The qualification batch is stopped; separating
advisories is not sufficient for complete semantic coverage. See
`../plans/2026-09-22-attribution-miss-diagnosis.md` for the bounded diagnostic.

## Context

ADR0103 showed that `submit_report_review` reliably delivered a complete typed
result, but the model still put a context-resolvable wording suggestion in the
blocking `issues` list. The second case also contained a real metric-direction
error. Treating both entries alike stopped revision before the true finding could
be repaired. The adopted standard says facts, unsupported extrapolation and
unresolved contradictions block; clarity improvements do not.

## Decision

Keep one review call and the existing tool transport, sources, budget and
revision workflow. Add a development-only `advisories` array to the submission
contract. `issues` must contain only report-changing findings. `advisories`
preserves suggestions whose full context is already correct and whose change is
optional. Only nonempty `issues` produces `needs_revision`; advisory-only output
is `pass` and the journal retains the advisory with its source selection.
Revision receives the blocking review and does not change the report for an
advisory alone. Invalid advisory source references or unknown fields fail closed.

This is a task/contract partition, not a severity heuristic or a sentence
exception. It is useful only if the model consistently assigns the two classes
correctly; the validator cannot prove free-text meaning from a numeric source
alone. Product contracts, historical modules and fingerprints remain unchanged.

## Alternatives and limits

Treat every low/other issue as advisory: rejected because a true unsupported or
ambiguous finding can be low and would be hidden. Deterministically rewrite the
model's issue: rejected because it would discard semantic evidence. Add a second
judge: exceeds the five-call Agent budget and changes the decision authority.
Keep ADR0103 unchanged: already disproved as a sufficient semantic fix.

## Verification and stop rules

Offline controls must prove advisory-only pass, mixed blocking/advisory revision,
invalid references/extra fields rejection, complete request budget and product
five-call reachability. Real validation starts with the frozen correct report and
the explicit universal-metrics report, with complete manual inspection. If a true
finding is put in `advisories`, or a context-resolvable suggestion remains in
`issues`, stop the batch and reject this contract. A successful pair permits
further same-version coverage only; it does not admit the product.
