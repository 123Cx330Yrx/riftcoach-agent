# Frozen editor opinion-view pair — 2026-09-21

## Question and evidence boundary

The old native first reviewer and editor v1 both expanded a generic statement
into a universal one. Editor v1 also omitted newer domain policy. That delivery
gap is fixed offline at e37e2e0, but no semantic improvement is proven.

This diagnostic asks whether exposing the complete old opinion package versus
only paragraph locators yields different judgments of the same full report
under the same aligned semantic rules. It does not isolate rationale alone:
severity, category, source choices, score, verdict, explanation and suggested
correction are all omitted from the locator view. A locator also changes the
job from judging a particular old allegation to independently checking its
paragraph. One sample in each condition cannot establish a causal anchoring
mechanism, stable effect, reviewer independence or product qualification.

Both requests use the same new diagnostic policy and EditorOutput. The common
adaptation explicitly states that a locator is not evidence of an error, that
the full old review is retained by the host, and that review_sha256 binds that
host review rather than the visible view. It replaces inherited statements
claiming that all prior reasons are shown. Full-opinion is therefore not the
unaltered editor-v2 request, and the old v1 result cannot replace this condition.

All source/report input, output schema and model settings are the same. Only
proposed_review differs. The frozen original review, actual report and all
source hashes remain on the host. No expected disposition, analyst correction,
one-true-one-false hint, old failure outcome or case name enters either request.

## Frozen execution

`scripts/run_native_editor_pair.py` builds both requests before Provider I/O and
checks them against `golden_native_editor_pair_plan_v1.json`. Order is fixed:
locator_only then full_opinion. Each starts independently from the original
report. The first response cannot modify or enter the second request.

The entire pair shares one budget and hard cap of two calls / 401920 tokens /
900 seconds, with GLM-5.3-flash/high, 32768 output, 63936 input, 300 seconds per
request and SDK retries zero. Input ceilings are 42176 and 43924; including both
output reservations, the pair reserves 151636. These are two alternative edits,
not a product chain with two revision attempts; no final review or publication
exists here. Existing product limits and native/editor qualification gates
remain unchanged and offline.

Semantic mismatches are observations in this precommitted comparison, so the
other frozen condition still runs. Transport, schema, source identity or budget
failure stops immediately, preserving an incomplete pair. No retry, supplement,
change to the other request or second patched paid batch is allowed this turn.
This completion rule applies only to this pair, not the existing qualification
batch's first-failure stop. A create-only experiment directory prevents resume.

Current continuation and existing bounded diagnostic authorization cover the
pair after independent request/execution review, local tests and clean exact-SHA
public CI. The previous turn's no-further-paid boundary is historical; the old
failed batch will not resume. No new permission turn is required.

## Reading outcomes

Read each full response, selected sources and complete actual report; compare
both to the original review's specific allegations. Matching dispositions
alone cannot certify that the same issues were addressed or that a true error
was actually corrected. Keep structural completion and semantic acceptance
separate; all runner outputs have semantic_approval=false until independent
manual evidence is recorded separately.

| Full-opinion / locator outcome | Maximum supported conclusion |
|---|---|
| Fails / passes | This sample differs with the opinion-view condition; not causal proof. |
| Same error / same error | Removing old opinions did not avoid the error in this pair. |
| Passes / passes | Both current outputs are correct; old failures remain valid. |
| Passes / fails | Locator-only may lose useful information; inspect the actual findings. |

Preserve actual issued request bytes, Provider receipts, public response text,
full edited reports, manual decisions and known/unknown usage. Private reasoning
never enters public evidence. Neither condition is product admission or proof
that the initial reviewer was repaired.

After this pair, decide from evidence whether to retain the aligned editor
candidate or reject the opinion-hiding route. Do not add prompt instructions
and repeat paid runs in this turn. Stage8E's same-version qualification, product
Evidence/Worker/DB/API/Workbench, independent evaluation/learning and all deferred
frontend/portrait/four-part Training requirements remain in the restart plan.
