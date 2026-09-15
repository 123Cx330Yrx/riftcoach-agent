# ADR-0102: Source references and bounded evaluation correction

Date: 2026-09-15. Status: accepted for offline experimentation and preparation of
an isolated development candidate, now observed; no production admission or semantic-quality approval.

## 2026-09-15 narrow diagnostic v1 result and v2 correction

The diagnostic implementation `6a73101dbf6d342686fe6aa219f19ad7d247cf95` passed
all three jobs in Actions `34940550415`. The normal Git transport failed twice;
the authenticated Git Data API uploaded identical blobs/tree/commit, verified
the exact SHA and advanced the branch with force=false. This did not create a
different implementation or bypass CI.

`context-relation-6a73101-critical` completed four calls, all stop: 37452 input +
1748 output = **39200 returned tokens**, no unknown usage. Cumulative Provider
reservations are at least **166**. Three outputs were protocol-valid, one invalid;
only two targets matched. Terminal times were 7.375, 6.031, 13.266 and 6.844 seconds.
This is the same high profile and capacity; smaller requests/outputs and a changed
task were observed, not a controlled proof of a single latency cause.

| Target | v1 result | Manual finding |
|---|---|---|
| stable_unbounded | valid / needs_clarification | Correct target classification; an additional claim of conflict with another single-game warning is not separately validated |
| stable_defined_before | valid / sample_defined | Correct explicit definition |
| heading_unbounded | valid / beyond_sample | Overstates missing meaning as a definite extrapolation; explanation also incorrectly says 2–3 games in each mid group |
| heading_defined_after | invalid / raw sample_defined | Correct definition reference and interpretation, but paraphrase violated the required verbatim defined_meaning field |

The frozen report has two mid wins and two mid losses, not 2–3 per group. Never
count the heading's refusal as the correct clarify label or the invalid last
response as a successful result. The private manual audit records these details;
all original inputs, outputs and receipts remain untouched.

The last failure exposes avoidable protocol duplication: context_ref already
recovers the complete original definition. Requiring a second full verbatim
copy does not prove entailment and caused a faithful paraphrase to reject.
**Adopt a separate diagnostic v2**, removing referring_expression/defined_meaning,
keeping the exact target/context references and one natural-language explanation.
Do not relax v1 in place or mark its old invalid response accepted. The source
binding and disposition/context consistency still reject stale or forged input.

The v2 policy also distinguishes undefined wording from an explicit unsupported
extension. Missing meaning gets clarification; beyond_sample requires an actual
assertion beyond the evidence. This is a model judgment, not a keyword allowlist.
No old label changes. A scripted projection of the last v1 response demonstrates
v2 shape validity while retaining its original context, not new model quality.

Implementation: `golden_context_relation_probe_v2.py`; runner selects it only
with `--v2`, records experiment `golden-context-relation-probe-v2` and response
contract 2.0.0. Complete source data and high/32768/300-second settings are the
same. Measured full inputs are recorded in
`data/evaluation/results/golden_context_relation_probe_v2.json`. 36 related tests
passed, including unchanged v1 rejection, v2 reference rejection, full source
preservation, explicit dispatch and separate accounting.

Next: same-SHA public checks, then **one new four-case batch**, at most four calls,
no correction or revision, existing 401920-token/900-second batch caps. Run the
same diagnostic command with `--v2` and a fresh `context-relation-<sha>-v2` run ID.
Stop on protocol/transport failure, manually inspect all decisions/explanations,
and do not automatically start a third diagnostic batch if it fails. These two
small experiments are not a whole-report acceptance gate. A later integrated
candidate must fit factual checks, scope judgment and correction within the
existing evaluation/revision call budget, before Workbench report admission.

## 2026-09-15 four-case observation and next diagnostic experiment

Implementation `9c5aad9cb2e9c3764b23e78435c7daa5048763fe` passed all three jobs
in Actions `34936247772`. The critical real batch did not pass. The original
receipt and 47 original files remain unchanged; `audit-v2.json` is a separate
private replay, not a replacement receipt or new model output.

| Case | Accepted final | Manual assessment |
|---|---|---|
| stable_unbounded | 95/pass, after anchor-only patch | Wrong acceptance: section heading treated as definition of stability |
| stable_defined_before | 96/pass | Correct explicit forward definition |
| heading_unbounded | 95/pass, after full reassessment | Wrong acceptance: unrelated summary limitation treated as definition of this heading |
| heading_defined_after | None | Initial definition reasoning appropriate, but numeric/anchor contract failed; reassessment connection failed |

Seven reservations, six complete responses: 78479 input + 66435 output = 144914
returned tokens. One interrupted request has unknown usage; cumulative requests
are at least 162. Counts are planned 4 / started 4 / finalized 3 / interrupted 1 /
not started 0. Last worker failed at 151438 ms with `connection_failed`; there was
no visible content, finish or usage. This is not evidence of a 300-second deadline
or output exhaustion. Underlying connection cause remains unknown.

Scoring defect: the first target was fully quoted except its final Chinese full
stop. The prior exact-string scorer called this target absent. The corrected
scorer requires its original block and every word, allowing only omission of
that final full stop. It now records wrong acceptance; neither target nor whole
report becomes correct. Old labels, evaluations and receipts are preserved.

Diagnostic regression: contextual reassessment sent only one error code. The new
offline helper reports claim/reference positions and actual unsupported numeric
source candidates without changing a response or accepting one. Independent
claim diagnosis also reveals two anchors hidden behind the last case's initial
420 error. Actual queue candidates reference all five `/queue_id` fields. Five
saved response replays with complete feedback measure 57910–59848 input ceilings,
below 64000. This helper is not yet part of frozen Coach 1.3.27.

Decision: reject another unchanged full-review run or a regex that declares
semantic correctness. First isolate the interpretation question in a small
**diagnostic experiment**, not a replacement evaluator: send each of the same
four complete reports with full facts, knowledge and one source-bound target.
Do not send expected labels, case names, prior verdicts, or prior explanations.
Ask only whether the exact assertion has an explicit definition/negation or
needs clarification; require the actual referring phrase and defined meaning
from source text. Program validation checks exact references and output shape,
not whether those phrases semantically establish the relationship.

This changes task decomposition and output obligation, not GLM profile. Freeze
an experiment ID and implementation/source hashes, validate inputs and public CI,
then make at most four separate calls (one per case; no repair, report revision,
or automatic rerun). Keep high / 32768 output / 300 seconds / zero SDK retries
and 401920 tokens / 900 seconds for the batch. Stop on protocol or transport
failure; preserve unknown usage and unfinished cases. Compare both positive and
negative cases manually. It is an assistant-labeled development diagnostic,
not holdout, not whole-report acceptance, and cannot prove task size alone caused
the previous failure. A production candidate needs a budgeted integration
choice and full evaluation/revision validation after this experiment.

Data/control flow: frozen complete report + facts + target reference → narrow
model judgment → reference/shape validation → immutable response and score →
manual semantic audit. The legacy evaluator and product report are untouched.
Code, tests, runbook and measured results are recorded with this section as the
experiment is completed. Stage 8E and all deferred Workbench scope stay unchanged.

### Diagnostic implementation and verification

`golden_context_diagnostics.py` supplies bounded reference/numeric hints and
unabridged context pairs for inspection. `run_golden_context_controls.py` fixes
terminal-full-stop scoring while retaining exact block/word binding.
`golden_context_relation_probe.py` and `run_golden_context_relation_probe.py`
implement the independent diagnostic contract `context_relation_probe/1.0.0`
and experiment `golden-context-relation-probe-v1`. This is not a new Coach
version or a replacement for frozen 1.3.27. No production runtime is registered.

The complete four requests measure 36708, 36870, 36736, and 36800 input ceilings;
see `data/evaluation/results/golden_context_relation_probe_v1.json`. At their
output caps their total reservation estimate is 278186, below the unchanged
401920 batch limit. Every actual request is checked again. This is not token
usage or a guarantee all four finish within 900 seconds.

Runbook: `python -m scripts.run_golden_context_relation_probe --source-run
 data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
 data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`
previews without secret/CI/Provider I/O. Only after same-SHA three-job CI, append
`--execute --env-file <private-path> --ci-run <run> --run-id context-relation-<sha>-critical`.
All four cases and their already frozen labels are fixed by the manifest. Labels
and prior verdicts/explanations never enter a request. Existing run directories
are refused. Reservations precede I/O; transport failures preserve started but
unfinished cases, and invalid JSON/reference output stops after saving that case.
Semantic disagreement alone completes the selected four; no automatic retry.

107 focused/adjacent regressions passed; after adding missing-content diagnostics,
all 11 diagnostic tests passed again. Compilation and governance checks passed.
These regressions cover scoring, independent location/numeric diagnosis,
full request/transport budgeting, literal reference validation, zero-I/O preview,
one-call execution, and protocol/transport/semantic counter distinctions.
The verifier checks a phrase exists, not whether it really defines the target.
A source-valid but semantically wrong judgment remains a failed diagnostic.

## 2026-09-15 isolated candidate implementation (historical preparation)

The next implementation is now opt-in Coach **1.3.27**, Skill **0.5.27**, Program
**2.3.27**, evaluation **1.20.0**, policy `golden-context-reference-v1`. This is an
unadmitted development candidate, not a production/default selection. Its Coach
snapshot is `22dff4e9c22367a009a32804a3fbfab868e4d556e14dabcc303932e800c349a5`.
The earlier offline experiment and historical v7/v8 results below remain distinct.

Problem/principle: the old local-only anchor contract cannot express a definition
in a preceding paragraph that explicitly names the next sentence, or a paragraph
that explicitly defines a heading. The new contract preserves that connection
without concatenating different source sentences or treating proximity as proof.

`golden_context_review.py` defines integer quote/evidence references, complete
ordered inventories, heading classifications and an optional context reference.
`defines_scope` corresponds to `selected_sample`; `negates` corresponds to
`question_or_negation`. A contextual anchor comes from the actual referenced
context. Both exact texts, their block identities and the model's explanation
survive into canonical audits, persisted evaluations and report revision.
Unknown/stale/ambiguous references reject; a context relation is a model claim,
not a deterministic proof that the interpretation follows. Every remaining
paragraph still requires review. Heading misclassification and omitted claims
remain semantic risks that inventories alone cannot detect.

The canonical result retains the existing verdict/issue consistency, scope,
coverage, evidence existence, direct numeric support and table-antecedent checks.
It additionally rejects duplicate same-block claims and duplicate evidence refs.
It does not rewrite old results or automatically inherit their acceptance.

`golden_context_runtime.py` makes at most two requests per evaluation. If full
validation finds only one to four non-context scope-anchor errors, the second
request may change only those anchors. The exact original response and source
digests bind the patch. Any other failure selects one complete reassessment.
A patch response may request reassessment, but that stops the current evaluation
as invalid: it does not create a third call. No new report revision is permitted
in this control batch. Typed prompt-injection findings stop the evaluation; raw
responses/reservations remain in the existing private Counted/stream journals.

`golden_context_requests.py` retains complete report context, facts/provenance,
deterministic report, retrieved knowledge and the observed-user request. It
checks every outgoing input ceiling before I/O. GLM high, 32768 output, 300-second
request deadline, zero SDK retry and the existing per-pair 401920-token/900-second
budget remain unchanged. The common composition entry also explicitly accepts
this new identity and selects its evaluator and reviser; the default stays put.

Full-input review: `golden_context_reports_v1.json` freezes ten complete-report
hashes and separate target/report labels before model execution. The assembler
replaces the first risk bullet in section 3 with the corresponding diagnostic
fragment, removing that bullet's pre-existing local stability definition; the
second risk bullet and all other sections remain. The complete base report was
read, each inserted context reviewed, and the new target/report rationale stored
alongside each hash. These are assistant-reviewed development cases, not a
held-out set or labels individually approved by the user. The original twelve
cases and scores are untouched. Private assembled inputs are in
`data/runs/inference_development/context-inputs-20260915-v1/`.

Measured before candidate registration, `golden_context_requests_v1.json` records
initial input ceilings 57692–57866 and reassessment 57882–58054 across the ten
complete inputs. Projecting the saved v8 pair-04 response and manually correcting
its anchor produces a **scripted** patch-request ceiling 49998 and revision
ceiling 59246. All are below 64000; the projection is neither new model output
nor a worst-case guarantee. Every future request is measured again.

Data/control flow: complete report and facts → source index → independent model
review → exact reference resolution → canonical checks → accepted result, one
bounded anchor correction, or one full reassessment → final full validation.
Accepted contextual audits can pass through the existing revision seam; control
evaluation itself never revises the source report or writes Workbench content.

Verification: 97 focused and adjacent tests passed, including explicit
cross-paragraph definitions, quoted negation, continued rejection of a later
wrong claim, unchanged numerical rejection, stale/forged references, patch escape
and the two-call limit, typed security stop, context preservation in revision,
actual composition factory selection, separate target/report scoring, and
label-blind zero-I/O preview. An additional 102 existing Coach repair/runtime/
product-acceptance tests passed. Old v7/v8/experiment tests still pass. These tests
prove protocol behavior and wiring, not model accuracy. Public CI and real
semantic observations are still required for this new implementation.

Runbook: `python -m scripts.run_golden_context_controls --source-run
data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`
is a zero-I/O preview with full initial-request measurements. It defaults to
definition and heading pairs only (four cases, at most eight calls total).
After same-SHA public success, add `--execute --env-file <private-path>
--ci-run <run> --run-id context-controls-<sha>-critical`. Existing output paths
are refused. Reported counters separate planned/started/finalized/interrupted
and not-started. Raw transport/timeout/auth failures stop the remainder. A final
protocol-invalid case is saved and also stops the suite. Semantically wrong but
valid results finish the selected contrast batch for comparison; no automatic
remaining-six/full-twelve run follows. Inspect each actual target and full report
before deciding the next bounded run. Do not combine versions into an all-pass
score. If the critical set fails, classify representation vs interpretation vs
transport and change the corresponding design before further paid repetition.

Learning/interview boundary: implemented a versioned source/context review
protocol, bounded correction, preserved canonical revision evidence and frozen
full-input contrasts; independent model quality and product admission remain
unverified. Stage 8E stays in progress and the Workbench design memo stays queued.

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
