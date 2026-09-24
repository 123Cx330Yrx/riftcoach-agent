# ADR0111: Separate task outcome observation from reviewer qualification

2026-09-24. Adopted for supplementary offline evidence and bounded development
observation only. This does not replace ADR0109 qualification, change production
admission, or establish a new user acceptance standard.

## Problem and evidence

Current1.5.2 review correctly identifies the explicit universal-metrics error,
but adds false middle-vision27–43 instead of25–43. The original qualification
batch rejected it. The separate unchanged-fixture containment diagnostic then
produced a correct actual Flash edit and acceptable fresh GLM final review.
The29-original public export and the earlier33-original export are immutable.

The Agent's existing consumer uses the final report and final evaluation; it
also retains every intermediate evaluation. One combined acceptance boolean
cannot describe both reviewer failure and successful downstream containment.
Conversely, a successful tail does not establish reliable reviewer accuracy,
continuous execution, fresh original15 coverage or product readiness.

## Decision and relationship to existing gates

1. `role_task_outcome` reuses the existing replay and binds separate full-source
   host assessments to source identity, exact reports, journals and raw-artifact
   fingerprints. `reviewer_quality` covers all review stages; `task_outcome`
   covers actual final text, preservation of correct content and identity/goals,
   accepted editing and the complete final review. Concrete defects remain.
2. Original correct controls must pass unchanged. Missed-error passes and false
   positives still fail replay. Finding a minor issue while missing a major one
   remains a reviewer defect even if the editor happens to repair everything.
   Final score alone cannot establish either dimension.
3. `validate_qualification` and `review_controls_qualified` retain their original
   meaning and consumers. The new observation cannot set any qualification or
   production flag. Even15 task outcomes would not automatically substitute for
   the original gate. A future change to admission requires an explicit adopted
   decision and migration; there is no implicit OR between the two routes.
4. Historical/combined replay explicitly cannot verify fresh IO or continuous
   task budgets. The public audit combines the rejected first review and the
   separate tail only for replay; neither old receipt nor result is edited.

## Prospective development continuation rule

The only added diagnostic continuation is a correctly targeted initial issue
whose correction intent is supported, but whose ancillary explanation has an
unsupported factual statement. Host must preserve `accepted=false`, the exact
defect and complete source reasoning, and affirm the issue target and correction
intent. All defect kinds must be `unsupported_explanation`. This narrowly tests
the existing editor/fresh-review mechanism demonstrated by the tail; it is not
a statement that the initial review is acceptable.

Wrong correction intent, mixed false/true issues, missed material errors,
incorrect initial verdict, original-correct controls requiring edits, identity,
safety, invalid protocol and budget/transport errors stop. Actual editing and
the full fresh final review must each pass source inspection. Any propagation,
removed correct content or unsupported final opinion rejects the outcome.
There is no host rewrite, correct-answer injection or additional model call.

This is a bounded development observation rule, not a production recovery gate.
Original failed batches stay closed. A new plan fixes cases, input hashes,
identity, maximum calls/tokens/time and stop branches before IO, and requires
clean same-commit public CI. It must not restart task time after an interruption.
The current product budget remains5calls/401920tokens/900s,32768/300s per request,
SDK retries0 and score85. Model roles and complete-context standard remain.

## Verification and limits

Public replay reconstructs request object ordering from the unchanged builder
and validates against the original raw-byte digest; sorted JSON is not treated
as original bytes and hashes are not replaced to obtain a match. Counterexamples
cover false positives, missed errors, bad edits/final reviews, missing stages,
changed source/request/report identity, contradictory host decisions and unknown
usage. Tests exercise supplementary accounting, not automatic semantic truth.

The host remains responsible for complete-source inspection. Neither passing
tests nor this rule guarantees future containment. The actual product task,
original15 qualification, Worker/DB/API/UI, four-surface Coach flows, training,
frontend aesthetics/avatars and the remaining restart-plan dependencies remain
open. This decision avoids building a new numerical language without evidence
while retaining the product's final factual and source requirements.
