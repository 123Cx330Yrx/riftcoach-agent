# ADR-0102: Source references and bounded evaluation correction

Date: 2026-09-15. Status: accepted for offline experimentation and preparation of
an isolated candidate; no runtime adoption or semantic-quality approval.

## Problem and scope

The goal remains a usable, evidence-grounded Coach report followed by revision,
reevaluation and Workbench consumption. The 1.3.25 original-report cycle succeeded;
the independent development controls did not. The next candidate must improve
completion without confusing protocol validity with correct reasoning.

The broader retrospective covered real-data entry on September 10, initial metric
and cohort errors on September 11, the quota-stop handoff, the mistaken Luna
attribution and subsequent scope/evidence contracts. Historical source defects,
the incorrect low diagnostic and its accounting/journal regressions have separate
fixes. They are not a single Provider failure. Luna means Codex execution
collaboration and has no bearing on the product's GLM profile.

Every new evaluation should not be a longer copy of the previous checklist.
Current repair regenerates the whole evaluation; failed original-quote, inventory
or scope references can recur elsewhere. Native `json_object` is not strict
server-side enforcement of the local schema. Complete inventories still do not
prove that the model discovered every assertion.

## Evidence and alternatives

The reproducible measurement is
`data/evaluation/results/golden_review_workflow_offline_v2.json`; its full private
per-response record is under
`data/runs/inference_development/review-workflow-20260915-offline-v2/`.
Only saved responses are inspected; no new model request is made.

| Measure | 1.3.25 controls | 1.3.26 controls |
|---|---:|---:|
| Complete saved responses | 18 | 10 |
| Valid under original contract | 8 | 5 |
| Reversible indexed projections | 17 | 6 |
| Compact original characters, projectable subset | 139543 | 51638 |
| Indexed envelope characters, same subset | 92637 | 33930 |
| Quotes / whole-block matches / single sentence-unit matches | 252 / 178 / 167 | 143 / 95 / 80 |

All 13 originally valid responses remain valid and identical after restoration.
The ten projectable invalid responses remain invalid. Five responses are not
projected: two wrong inventories, two extra-JSON/text suffixes and one invalid
source quote. No projection repairs a historical response or creates an accepted
historical evaluation. The 23 reversible projections shrink from 191181 to 126567
compact characters (33.8%). This is not a token, latency or billing measurement.
Claims/issues quote text and copied block IDs alone were about 19–20% of visible
output; shorter evidence references and serialized fields contribute to the full
projection difference. No reasoning-time reduction is inferred.

Alternatives:

- Whole-block references only: reject as the sole representation. Only 273/395
  existing claim quotes equal a whole block; enlarging every quote changes the
  scope and can combine correct and incorrect assertions.
- Sentence units only: reject as the sole representation. A simple Chinese
  punctuation split matches only 247/395 quotes. More importantly, defining scope
  or negation across units must not be lost. This is a measured baseline, not a
  claim that no better sentence parser could exist.
- Character offsets: not selected. They add model-side counting and allow a
  syntactically legal range to point at the wrong text.
- Whole block plus unique short endpoints: selected for the isolated candidate.
  Program-owned ordered IDs and fact keys become integer references; a quote is
  a whole block or a unique literal head/tail within it. Ambiguous, missing and
  cross-block selections reject instead of choosing the first match.
- Strip a malformed JSON suffix or regenerate all judgments for every formatting
  problem: not selected as a general repair mechanism. Preserve raw output and
  separate reference repair from reassessment.

## Decisions and responsibilities

`SourceIndex` retains the full original report and ordered blocks. Its digest
binds report text, fact values, provenance and registry identity. The model still
sees complete ordered context; input is not split into isolated semantic tasks.
`index_review` / `restore_review` preserve every existing judgment, quote, issue,
explanation and reference. `validate_indexed_review` then runs the original full
validator; indexing does not upgrade a verdict or claim to have checked content.
There is no new dependency, Provider registration, model setting or default path.

The local-correction prototype allows only diagnosed `scope_anchor` replacements
in at most four existing claims. The patch binds the exact raw-response digest
and source digest. It cannot add/remove claims or issues, alter evidence, scope,
score or wording, or edit unrelated locations. Duplicate/stale/wrong targets,
unknown references and failed final validation reject. Non-JSON, duplicate-key,
inventory, security and other semantic/evidence problems require reassessment.
The model can explicitly return `needs_reassessment` with a reason when it finds
another problem; the protocol must not force retention of a mistaken verdict.

The latest timeout's preceding response has one eligible reference defect. A
**human-specified offline** patch changes `中单同位置` to the existing literal
`混合样本`; this restores the original validator's 95/pass result without changing
other judgments. A nonexistent `单局` anchor was rejected during the experiment.
This demonstrates the boundary, not autonomous correction or semantic quality.
The compact patch is 257 characters. The full request builder includes the report,
previous evaluation, facts, deterministic source and complete retrieved knowledge.
Its actual local input ceiling is 53844 versus 58806 for existing whole-review
correction, both below 64000. Output 32768 / 300 seconds are unchanged. Only this
saved shape is measured; every future request still needs its own budget check.

## Context-sensitive rubric and old labels

The frozen twelve labels and all historical scores remain unchanged. Their
original single-claim labels were later embedded into a revised report. That
embedding supplies nearby definitions and changes the semantic task. The audit
below is a new assessment, not a relabeling to obtain a passing score.

| Frozen case | Current contextual assessment |
|---|---|
| selected_pairs | Retain accept: individual values support the stated four-game comparison. |
| selected_means | Retain accept: correct means and explicit limitation; whole-report issues are separate. |
| stable_negation | Retain accept: a denial / observation request, not a stability assertion. |
| stable_local_definition | Retain accept: local direction consistency is expressly defined. |
| long_term | Retain reject: an explicit long-term inference lacks evidence. |
| future_without_keyword | Retain reject: explicit prediction of all future losses lacks evidence. |
| disclaimer_conflict | Retain reject: the disclaimer does not cancel the ensuing long-term assertion. |
| causal_leap | Retain reject: correlation does not establish the cause of defeat. |
| original_stable | Keep historical clarify; review whether it is read as an overview of the adjacent defined comparison. Do not report contract mismatch alone as universal semantic failure. |
| original_reliable | Keep historical clarify; almost the same phrase is defined immediately afterward, so contextual linkage needs separate paired evaluation. |
| reliable_without_keyword | Retain clarify on present evidence: a reliable win/loss discriminator is stronger than a descriptive sample difference. |
| persistent_heading | Keep historical clarify; the body limits its comparison, but how it qualifies this heading needs explicit contextual tests. |

Product-quality rules distinguish wrong facts, unsupported inferences, unresolved
scope and optional editorial improvements. Explicit definitions referring to a
following sentence or preceding heading may establish scope across blocks. Mere
adjacency or a generic disclaimer does not establish that connection. These are
semantic judgments; a `context_ref` can establish where the text is, not whether
the interpretation follows. Quoted assertions explicitly rejected by the author
must not be treated as endorsed claims. A correct target does not make a report
with a different erroneous claim acceptable.

`golden_context_controls_v1.json` adds five pairs / ten assistant-authored
development examples for these distinctions. It records target and whole-report
expectations separately. These are not held-out cases, user-signed labels or
model-validated results. Their raw data must never be sent with expected labels.
These are diagnostic fragments, not ready-to-run complete Coach reports. Before
live evaluation, the final complete input and both labels must be reviewed and
frozen together. Do not send a fragment to the full-report evaluator or inherit
its isolated label after embedding without reviewing the resulting context.
The existing local-anchor-only validator is retained in this experiment to prove
representation equivalence; that does **not** settle the new contextual rubric.

## Verification, operation and next implementation

Code map: `golden_review_experiment.py`, `check_golden_review_workflow.py`,
`test_golden_review_experiment.py`, `test_golden_review_measurement.py`.
Data flow: full report / facts → program-owned index → model-reference-shaped
projection → exact restoration → original validator. For correction: original
response + diagnostics → bounded patch or reassessment → complete revalidation.

Tests cover mixed assertions, retained adjacent context, Markdown/table fidelity,
ambiguous/stale/forged references, unchanged facts and judgments, rejection of JSON
suffixes and duplicate keys, patch escape to reassessment, full request limits,
and interrupted-case accounting. A known misclassified-heading fixture still
passes, explicitly documenting that protocol tests do not prove semantic quality.
The focused experiment, measurement, scope-runner and adjacent v7/v8 suite passed
66 tests locally; compilation, governance and diff checks passed. Implementation
`8d3857251e147ff2ce4f13efd9275a9db3aa7653` passed Actions `34924328754`: all
three jobs (`postgres-migrations`, `packaging-smoke`, `pytest`) succeeded on that
exact SHA. This verifies engineering behavior, not model semantic quality.

The scope runner now additionally reports `case_counts` with planned, started,
finalized, interrupted and not_started, preserving the legacy `attempted` field
with an explicit finalized-cases meaning. Start means the case input was written;
Provider reservations are counted separately. Old receipts are never rewritten.

Run the measurement module with `--summary`, `--source-run`, the two `--runs`, and
new `--output` / `--public-output` paths. It refuses overwrites. Private output
contains per-response hashes/diagnostics; public output contains counts, hashes
and size comparisons, not report bodies. Historical responses remain immutable.

Next: implement one isolated candidate using source references, explicit
contextual support links and bounded correction; measure its complete requests
before registration. A context claim must retain its own identity while naming
the text that defines or negates it. Preserve fact/source/numeric and whole-report
checks. After same-implementation public verification, prioritize the four
definition/heading contrast cases before the remaining context cases and full
frozen regression. A failure must distinguish completion, representation and
semantic interpretation; do not stitch different versions into an all-pass batch.
No further limit increase or model downgrade is selected.

The old original-report success, observed ShowMaker identity, Workbench manual
report and saved notes stay valid. Review/Coach/Training/Evidence and visual work
remain in the September 11 design memo. Stage 8E and automatic quality stay in
progress. Interview wording: built a lossless reference experiment and measured
its limits; not proved reliable autonomous review or production adoption.
