# ADR-0102: Source references and bounded evaluation correction

Date: 2026-09-15. Status: accepted for offline experimentation and preparation of
an isolated development candidate, now observed; no production admission or semantic-quality approval.

## 2026-09-16 Bounded reception of supplemental notes and display whitespace

Implementation ad1003dd72437842e300ae5ec2cf4dc61bf2d47a passed exact-SHA Actions
34992614360 (pytest, PostgreSQL migrations and package smoke). Its v3 live run
completed two stop responses: 25,829 input + 33,123 output = 58,952 returned
tokens. No unknown usage; cumulative Provider requests at least 177. The second
request was actually issued, verifying the input-budget repair. The pair stopped
on the first report before revision; the future-claim report was not started.

All 22 required reviews were present. The model also supplied c014-c016 notes
for its three added claims, although each addition already had its own note.
The receiver rejected these extras. Offline inspection then found one further
mechanical error: scope_anchor “各只1局” omitted spaces in “各只 1 局”. After
explicit diagnostic projection of those two items, the entire validator passed;
there were no other observed downstream errors. This was not a live pass.

V4 changes reception, not the approved semantic standard. Optional supplemental
notes are allowed only for declared additions, numbered deterministically after
the existing claims in addition-array order. Every original required note remains
mandatory; duplicates, unknown IDs, source reassignment and missing fact issues
still fail. Supplemental text is retained in the journal and never supplies a
second classification or source reference. Its semantic explanation still needs
human/model scrutiny just as the other explanation fields do.

For an edited or added claim's scope_anchor only, the host can restore display
whitespace when all original characters match a single span within that claim's
own quote or explicitly referenced context. Digits/ASCII word characters cannot
be joined or split; numbers, punctuation, words, source and scope cannot change.
Multiple possible spans and out-of-bound anchors still fail. Before/after and
source reference are journaled. Quotes and original request/response bytes are
not edited. This is bounded source-location resolution, not a semantic fix or
permission to rewrite a model's judgment.

111 focused tests passed, including supplemental-ID binding, missing/duplicate
reviews, different digits, split numeric strings, ambiguous whitespace and
punctuation negatives. The original v3 responses replay directly through v4 to
93/pass with zero issues, 13 retained claim edits, three supplemental notes and
one whitespace resolution. `golden_contextual_recovery_ad1003d_v4.json` records
this strictly offline result and unchanged hashes for both responses and the
original failed result. It does not relabel the historical v3 run.

`golden_contextual_readiness_v4.json` measures first requests 47540/47612, three
historical correction shapes 59312/59226/56974, the actual v3 first-response
shape 62348, and revision shape 50540. These are shape measurements, not future
completion guarantees. No budget, timeout, model tier or retry limit changes.
Next: exact-SHA public checks then one new-identity two-report live validation,
including genuine future-claim detection, revision and recheck. Preserve stage
8E and all broader product/frontend follow-ups from the retrospective.

## 2026-09-15 Recovery after the comprehensive retrospective

This batch resumes the latest 206a4c3 contextual candidate. Coach 1.3.25 is a
regression baseline, not the development target. Its original report revision
success remains evidence for that report only; later control failures remain.
No historical response, strict label, or frozen Prompt Program is rewritten.

The 206a4c3 run (Actions 34959615129, three successful jobs) started one of two
reports. Its first response finished with stop: 11,807 input + 13,526 output =
25,333 returned tokens. The next request was rejected locally at input ceiling
64,300; no correction, revision or recheck was sent. Cumulative Provider requests
in the existing scope are at least 175, correcting the stale 174 checkpoint.

2026-09-16 preflight follow-up: complete-report inspection additionally covered
Chinese ordinal rank wording, T-tier numerals and ISO retrieval timestamps at
displayed precision. Wrong rank, tier, timestamp and rate-unit negatives remain
rejected. The two current contextual suites passed all 43 tests after this change.

The v3 candidate repairs connected engineering defects:

- Every first-review claim can be corrected and must be reviewed, including
  claims initially labelled direct_result. The immutable original and explicit
  edit journal remain; quote shrinking/reassignment and unsupported issue removal
  are still rejected. The prior label cannot freeze a semantic mistake.
- Already supplied OP.GG rows become indexed evidence with snapshot provenance,
  position, timestamps, allowed uses and unknown patch preserved. Existing Meta
  row validation is reused. Rank/tier/rates are checked by named metric and unit;
  external values cannot masquerade as queue IDs or unrelated statistics. This
  does not establish semantic entailment or turn a current snapshot into a
  historical, region/rank-matched or personal performance source.
- Fact, provenance and review tables remove repeated keys; external facts refer
  to the complete original snapshot already present in the request. Before I/O,
  the host reconstructs every value and compares canonical JSON. Entire source
  text, report blocks, first-review explanations and diagnostics remain visible.
- Revision now uses the same contextual standard and indexed evidence. The old
  revision constructor inherited v8's superseded local-definition policy. It is
  no longer used by this candidate. Historical constructors remain unchanged.
- The unfinished modification of frozen numeric_v4 was removed: it caused
  component fingerprint drift before baseline loading. New numeric validation
  stays isolated; the current validator reuses frozen restoration/scope helpers.

Data/control flow: supplied report and evidence -> source-bound input -> first
review -> immutable all-claim state -> explicit correction -> complete validation
-> optional report revision -> first review and correction of the revised report.
Maximum five calls, one revision, high / 32768 / 300 seconds, 401920 total tokens
and 900 seconds remain. Actual usage is settled before reserving the next request;
there is no blanket worst-case completion guarantee or hidden retry.

`golden_contextual_readiness_v3.json` uses the actual workflow input builder and
includes the latest failing response shape. Old integer references are rebound
by source identity for measurement only; this is not a new model judgment. First
requests: 47540 / 47612. Three historical corrections: 59198 / 59112 / 56860.
Latest shape: 63124, with 21 mutable claims, 30 reviews and five external facts.
Revision shape: 50540. All measured requests fit; future responses can still hit
a declared limit and must stop honestly. Original response hashes are retained.

Code map: golden_contextual_sources (index/numbers), golden_contextual_requests
(lossless tables/revision), golden_contextual_validation (final validation),
golden_contextual_correction/workflow (state/sequence). The bounded/integrated
base workflows expose explicit hooks while retaining their existing defaults.
`test_golden_contextual_recovery.py` covers false direct-result classification,
external field/unit negatives, source mutation, malformed snapshots, lossless
reconstruction and a five-call scripted path with changed-source rejection.
These tests prove engineering behavior, not a model's ability to judge language.

Validation: all 642 golden-slice-related tests passed, including historical
profiles and the new regressions; compile, actual CLI preview and governance
passed. A full local suite was interrupted after two database setup errors: the
inherited test URL was set without DATABASE_URL. Setting it for the dedicated
local riftcoach_test database exposed an unavailable endpoint (3-second connection
probe timed out). No migrations completed. Database integration remains for the
existing isolated PostgreSQL CI job; do not claim a full local suite pass.

Reproduce sizes with `python -m scripts.check_golden_contextual_readiness`, passing
--source-run, --base-report, --bounded-run, --context-pair, --latest-case and a NEW
--output path. No Provider is created. After local checks and exact-SHA public CI,
run the existing contextual entry on the two frozen complete reports under a new
run identity. Inspect every finding and source link; stop the pair on a genuine
protocol, transport or semantic failure and retain full receipts.

Stage 8E remains in progress. Do not rebuild the already completed ADR-0099
publication chain or observation-note persistence. Broader follow-ups stay in
the comprehensive retrospective's 62-theme requirements table and separate
frontend-renewal attachment: Review/Coach/Training/Evidence integration, natural
encyclopedic Coach, requested training plans, observed-vs-self identity, full
frontend aesthetic redesign (including champion portraits, Portal and Account),
data/version/role quality, deployment/Auth, and learning/portfolio coverage.
Codex Astra/Luna execution allocation is unrelated to the GLM product tier.
Interview wording: repaired evidence indexing, corrective state mutability and
request composition with reproducible regressions; real quality and production
admission remain unverified.

## 2026-09-15 Owner-approved whole-context standard and single decision protocol

The owner explicitly selected “采用完整上下文标准（推荐）”. A complete report
that clearly bounds the same sample, comparison and meaning may pass without a
special dictionary-like definition of “stable”. Optional wording improvements
must not alone block it. Real factual errors, unsupported long-term/future/causal
claims, and contradictory assessments remain blockers. This supersedes the
assistant-authored strict word-definition gate for the new experiment only.

The preceding v1 observation `bounded-review-96c2c3a-definitions` used implementation
96c2c3a1b90d0df105938ccbef98d937f8f65ba4 and exact-SHA Actions 34956898101
(all three jobs successful). Both responses finished with stop; 50669 returned
tokens, no unknown usage, 2 requests, cumulative Provider requests at least 174.
It failed before revision: c001/c005/c008 duplicated literal vs inference labels;
c010 duplicated conflicting context sources. Raw scores 95/94 were not valid
passes. `golden_bounded_observation_96c2c3a_v1.json` records all four conflicts,
full original response digests and timing. Its old strict labels and raw results
remain unchanged; this decision does not retroactively accept them.

The isolated `golden-contextual-bounded-review-v2` uses
`whole-context-acceptance-v1`. Classification and source reference are expressed
once, in the final claim; review_notes explains each required decision. The host
derives the legacy validation witness from that same final claim. It does not
repair any incoming old response: the v2 wire rejects v1 meaning_reviews and extra
disposition/language_ref. The complete final factual, source, numerical, issue,
heading, security, state and receipt checks still execute. This derivation
removes contradictory duplicate fields but cannot prove semantic entailment.

`golden_contextual_reports_v2.json` assigns independent contextual_01/02 identities
to byte-identical complete reports stable_unbounded/future_with_disclaimer. Under
the approved standard these are accept/reject respectively. Original ten-case
and twelve-case labels remain frozen. These are development controls, not a held-out
benchmark. Labels remain outside model input. The next real run must verify both
correct acceptance and unsupported-future detection, revision and full recheck.

Flow: complete source/report -> first review -> bounded explicit correction ->
full merged validation -> at most one report revision -> complete review and
correction again. Request construction includes the full lossless generation_view
explanation and verbatim deterministic source in both independent evaluations.
The actual-usage budget runner still enforces high, 32768 output, 300 seconds per
call, 401920 total tokens, 900 seconds and at most five calls per report, no SDK
retries. Larger unexpected requests remain refused before I/O.

Reproduction: `python -m scripts.run_golden_contextual_review --source-run ...
--base-report ...` previews without credentials/network; real mode additionally
requires --execute, --run-id contextual-review-..., --ci-run and --env-file.
`python -m scripts.check_golden_contextual_readiness` measures first requests
50576/50646; historical correction shapes 61386/62024/58960 and revision 53584.
The size replay does not regrade historical responses or guarantee runtime cost.
Tests in test_golden_contextual_review cover protocol isolation, contradictions,
state/source binding, fact issue retention, security, heading additions and full
five-call flow. Local focused/adjacent regression: 129 passed, compilation, governance and diff checks passed. Real semantic acceptance remains pending public checks and the
new observation. No product default, production admission or stage advance.

## 2026-09-15 Efficiency correction: verbatim source and actual-usage admission

The owner asked why the work still was not complete and required more efficient
execution. This audit corrects an assistant-imposed readiness criterion: adding
five independent maximum reservations and requiring that sum to fit 401920 was
being treated as mandatory even though the existing runner reserves only the
NEXT call and settles returned actual usage. This section supersedes the prior
blanket prohibition based on that summed envelope. It does not claim the sum now
fits, guarantee completion, change any budget, or assert owner approval of a new
model tier or weakened quality rule.

A concrete request defect is fixed: deterministic source text was embedded as a
JSON string, repeatedly escaping its own structured sections. It now occupies a
separately labeled untrusted user message. Every source character remains, and
the actual high-profile SDK request retains all three messages. A note makes
clear that machine-generated explanations inside this source report are not
already-proven facts. The complete schema, source rules, local validation and
generic estimator remain unchanged. SDK capture confirms JSON-object mode, not
server-enforced JSON Schema; generic accounting of the local schema remains a
conservative allowance, not a removed constraint.

Measurement: `data/evaluation/results/golden_bounded_review_readiness_v1.json`,
reproducible with `python -m scripts.check_golden_bounded_readiness` and the same
three private source arguments as the previous measurement. Ten complete first
requests measure **50282–50456**; the two actual saved state shapes measure
**63474/60410**, both below preparation limit 63936 and hard input limit 64000.
Historical revision remains **53584**. The summed maximum envelope is still
**445284 > 401920** and is explicitly retained as a limitation. Larger future
states can still be rejected before sending.

`BoundedCorrectionWorkflow` now reuses the established receipt-bearing sender,
revision source binding, report validation and five-call guards. Its evaluation
is first review -> preserved state -> mandatory explicit correction -> complete
canonical validation. One revision may be followed by the same two-step review;
there is no sixth call or silent repair. Invalid first inventories stop rather
than inventing source identities. Correction journals are persisted separately
for initial and revised evaluations. `scripts/run_golden_bounded_review.py` is an
isolated development entry; default preview is offline and execution still
requires clean checkout and the same implementation SHA passing all public jobs.
Old integrated entry defaults, registered Coach versions and production remain
unchanged.

The real `CoachBudgetedProvider` tests demonstrate both sides of admission:

- Five requests whose hypothetical reservation sum exceeds 401920 can complete
  when their returned actual usages leave enough room for each next reservation.
- One token above remaining capacity rejects BEFORE Provider I/O; exact remaining
  capacity admits the next request. The sixth call and elapsed-time exhaustion
  remain rejected. No estimated count is substituted for real returned usage.
- Full first/correction/revision/recheck/correction control flow uses actual
  canonical validation, full revised-report validation and receipt identities;
  changing recheck evidence is refused before another call. SDK capture confirms
  high/32768 and verbatim source transport. These are scripted tests, not claims
  about future real-model accuracy, usage or latency.

Focused and adjacent verification totals **122 tests passing** after correcting
an incomplete test fixture. Code, source text, receipt, budget and semantic
boundaries are tested separately; the existing valid-source/wrong-relationship
counterexample remains documented and is NOT declared solved.

Decision: allow a conditional bounded development observation after this SHA's
public checks, using the frozen complete explicit-definition pair with unchanged
labels: at most five calls/one revision/401920 tokens/900 seconds per report,
32768 output/300 seconds per call, high, SDK retries zero. Stop the pair on any
protocol, transport or scored control failure; preserve first failure and all
responses. Inspect meaning explanations and correction journals before claiming
semantic acceptance. No production admission or broad accuracy estimate follows
from two development reports. This falls within the owner's standing continuation
authorization; no new approval is needed for the local work or already authorized
bounded testing. Do not repeat a failed identity or launch an extra batch merely
because the code checks pass.

The immediate next action is same-SHA public verification followed by that one
bounded observation. The original 1.3.25 ShowMaker revision stays valid; independent
control reliability and Stage 8E remain in progress. Provider count is at least
172 before this observation; source restoration and these tests made no calls.

## 2026-09-15 Bounded state correction: offline implementation, readiness rejected

The prototype now exists in `app/evaluation/golden_bounded_correction.py` and
`golden_bounded_correction_requests.py`. It is not registered, has no five-call
runtime, and makes no Provider calls. Existing candidates and old responses are
unchanged. Its purpose is to keep the first assessment as host-owned state and
let the second response explicitly correct it without regenerating unaffected
claims or dropping independent issues.

Data/control flow: complete report/facts -> source-bound ContextWire first
assessment -> immutable state and short claim/issue/heading handles -> explicit
changes, additions and meaning reviews -> complete canonical validation and an
edit journal. A future runtime must bind the actual budget-transformed request
and receipt before merging; the offline `finish` function enforces this boundary.
Structural first responses without trustworthy source inventories stop rather
than receiving guessed positional identities. No extra repair slot is assumed.

The host preserves untouched fields exactly, rejects unknown/duplicate/missing
handles, and prevents source reassignment or shortening a claim to hide an error.
Every mutable claim (including diagnosed direct facts) and every heading needs a
meaning review. New claims carry their own review. Fact-issue removal requires an
explicit reason and source references; before/after remain in the journal.
Injection is terminal, including when introduced through an issue edit. Full
canonical numeric, source, heading, scope, issue and coverage checks run after
merging, so a scope correction cannot forgive an independent fact error.

Request compaction deduplicates only identical fact values, preserves distinct
JSON types and restores the entire original generation projection. Schema title
annotations are removed, but constraints and literal values named title remain.
The independent correction request now contains its required source and factual
rules explicitly; it cannot rely on an earlier prompt absent from its messages.
A generation-only length policy is replaced with its evaluator obligations;
position/source policies and accuracy/evidence/actionability remain intact.

Evidence: `tests/test_golden_bounded_correction.py` and adjacent source/context,
integrated review and budget tests: **115 passed**. Tests cover explicit definition,
negation, later conflict, overlooked headings, retained facts, numeric rejection,
state tampering, injection, source restoration, request-size boundaries and actual
receipt binding. These are scripted protocol tests, not real semantic controls.
A deliberate wrong definition relationship with a valid source still receives
canonical pass; the journal records `semantic_approval=False`. This explicitly
proves the remaining semantic limitation rather than declaring it fixed.

Reproduce measurement (private frozen source runs required):

```powershell
python -m scripts.check_golden_bounded_correction --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md --context-pair data/runs/inference_development/context-controls-9c5aad9-critical/pair-01
```

The body-free result is
`data/evaluation/results/golden_bounded_correction_offline_v1.json`:

- Ten complete first requests: input ceilings **51598–51772**, all source values
  and JSON types reconstruct exactly.
- Two actual saved first-review states: correction ceilings **64790** and
  **61726** after budget metadata. The first fails both preparation limit 63936
  and runtime input limit 64000. Earlier 63662 omitted necessary standalone
  correction rules and is superseded, not an accepted optimization.
- Historical revision shape: **53584**. Twice the measured maximum first and
  correction requests, plus revision and five 32768 output reservations, yields
  **450548 > 401920**, excess **48628**. This is a measured-shape envelope, not a
  bound on future first responses/revised reports or actual billed usage.
- Even an UNUSABLE sizing ablation deleting all prior state from correction
  requests yields **434584 > 401920**. Shortening handles or state alone cannot
  establish the envelope. This ablation is not an executable request proposal.
- Actual usage settlement may permit some runs despite the conservative summed
  envelope; five 300-second calls also do not guarantee the shared 900 seconds.
  No limits, estimator, GLM profile or retry policy were changed.

Decision: retain the offline state-merge prototype and its regression evidence,
but **reject this composition as ready for real calls or candidate wiring**.
Do not run another paid batch to find out whether the budget happens to suffice.
The current canonical next action is an offline component-level budget decision
for the complete first/correction/revision requests: identify exact source/schema
repetition removable without losing obligations, quantify its achievable saving
against 48628, and accept or reject a concrete composition before more runtime
implementation. Do not add another protocol or reinterpret ordinary-language
ambiguity as a numerical error. If no adequate lossless saving exists, record
that boundary and present a concrete cost/scope choice rather than silently
raising limits, lowering GLM or weakening quality rules.

Original Coach 1.3.25 report revision and 96/pass recheck remain valid. Independent
control reliability and Stage 8E remain in progress. Observation persistence/API/
restart readback are already complete; four-surface design and hero-avatar work
remain indexed in the 2026-09-11 follow-up. Provider cumulative count remains at
least 172, with zero additional calls here. Implementation `56a5467c83371f9da3b462ad94bcdacd2800726f` passed all three
public jobs in Actions `34954808947` with the exact same head SHA. This
documentation closeout changes no product code. No production admission or
deployment follows from CI.

## 2026-09-15 Follow-up: the redesign needs a correction path, not another full pass

The owner again challenged repeated failures after the workflow reassessment.
This is a process defect as well as a model-quality problem: scripted tests
established transport, restoration and refusal behavior, but were not evidence
that the changed division of reasoning would improve the failed controls. The
integrated extraction step left the substantive assessment workload in one call.
Do not repeat the claim that the original report never completed: Coach 1.3.25
already produced its accepted revision and 96/pass recheck. The unresolved work
is reliable independent report evaluation, including protocol validity.

New reproducible offline evidence is in
`data/evaluation/results/golden_review_redesign_offline_v1.json`, produced by
`scripts/check_golden_review_redesign.py`. It makes no Provider calls and does not
contain an executable new Coach candidate:

- Replaying the unchanged v2 response exposes three concurrent structural
  defects: 47/48 judgments, 4/28 additions rows and an unexpected field. The old
  diagnostic returned only that field and mislabeled it `discovery_schema_invalid`.
  `assessment_feedback` now collects independent counts and schema errors under
  the actual assessment phase, then retains existing canonical diagnostics when
  the shape permits them. It does not zip misaligned rows, delete fields, repair
  results or change acceptance. This fixes diagnosis, not the model's omission.
- An explicit short-handle prototype preserves correspondence under reordered
  responses and rejects missing, duplicate and unknown handles. Old positional
  responses are never retrospectively assigned identities. Sparse additions
  should carry their own source references, rather than empty rows for every block.
- A deliberately scripted counterexample points to the genuine overall-summary
  paragraph and claims that its correct statistics define this target's word
  “较稳定”. The existing bound-scope decoder accepts the source/reference protocol;
  the interpretation is still unproved under the frozen rubric. This is an
  executable demonstration that source existence is insufficient, not a new
  model failure or an accepted whole-report evaluation.
- Direct reuse of the full review measures 57692–57866 input-ceiling tokens;
  the existing single-target scope request measures 35630–35896. A batch sizing
  template with explicit handles and sparse additions measures 40930–45886,
  using the actual 48 discovered targets for the failing report and whole blocks
  for the other nine. The historical revision shape is 53584. Five-call envelope
  sums are 404948 (single target) and 424928 (batch), above 401920. These are
  measured reuse shapes, not a minimal fact-only implementation or future maxima.
  The runtime settles actual usage, so this does NOT predict every run fails.
  It does disprove treating this unmodified composition as a proven envelope.
- Two mandatory phases for both initial evaluation and recheck, plus revision,
  consume all five calls. One extra correction after each evaluation needs seven.
  A valid fact issue must survive later scope approval; missing or malformed
  facts cannot be silently filled by a supposedly scope-only judge. A target
  interpreted correctly cannot clear an independent later conflict. A design
  that has no way to satisfy these obligations is not ready for registration.

Rubric audit: the complete negative report DOES already state sample limits and
per-game direction in its opening summary. The frozen target asks for clarification
of an undefined stability term under the explicit-reference rubric; it is not an
arithmetical falsehood or proven assertion of long-term ability. Labels and old
results remain unchanged. A plausible ordinary-language reading must not be
reported as objective numerical error, and these assistant-authored controls are
not independent holdout or an owner-approved universal style rule. Actual
unsupported causal/future claims remain substantive errors; explicitly negated
quotes and genuinely defined local observations must remain acceptable.

Decision: reject direct reuse of “full factual review + scope review” as a ready
candidate. Keep the integrated candidate rejected. Adopt ONLY the next offline
experiment: retain a first review's source-bound state, use the second slot for
bounded corrections and a scope challenge, then perform full final validation.
Unlike the earlier anchor-only patch, this must permit explicit semantic changes
and newly discovered assertions without regenerating every unaffected judgment.
It is not yet an implementation or a claim that patching will improve semantics.

The prototype must preserve first-pass fact/numeric/source issues and diagnostics;
only explicit, justified edits may supersede a finding, and injection findings
remain terminal. Every target uses a host-owned handle; additions resolve an
explicit source reference. The challenger must distinguish the report's language
from empirical support, identify an actual definition/negation relationship or
record unresolved meaning, and test the same facts under changed definition,
negation and later-conflict text. A correct number or a valid reference alone
cannot count as a resolved challenge. Existing canonical validation is the final
gate, not a partial patch acceptance rule. Measure the actual old state, concrete
diagnostics, full report/facts and patch schema together, including revision and
recheck; reject the proposal if these obligations cannot fit two calls per
evaluation/five per report. Do not hide another full review in a “narrow” request.

Reproduction (repository root, use the project Python):

```powershell
python -m scripts.check_golden_review_redesign --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md --run-dir data/runs/inference_development/integrated-review-153ae2c-definitions --historical-evaluation data/runs/inference_development/context-controls-9c5aad9-critical/pair-01/stable_defined_before-evaluation.json
```

The source runs are private audit inputs; public CI tests the independent
correspondence and diagnostic behavior. This checkpoint adds no paid calls,
changes no GLM profile, and makes no production or model-quality claim. The next
offline experiment is within standing authorization and requires no new approval.

Local verification: 35 integrated-review tests plus 23 correspondence,
bound-scope and context-diagnostic tests passed; compile, governance and diff
checks passed. The saved failed response now reports all three structural defects
with no omitted diagnostics, and its original bytes remain unchanged. Implementation
abcfc0242b30798d9a239338a1a043dd6ae6ef11 then passed pytest, postgres-migrations
and packaging-smoke in Actions 34951075015 at that exact SHA. This verifies the
diagnostic change and offline experiment, not model semantics or a new candidate.

## 2026-09-15 Integrated v2 complete responses rejected; adoption paused

Implementation 153ae2c240f9c48ac60963ad27a7b30fd454ba33 passed all three jobs in
Actions 34948333840. The second complete-report run
`integrated-review-153ae2c-definitions` planned 2 / started 1 / finalized 1 /
interrupted 0 / not started 1. Both calls returned complete stop: discovery
2445+5865 tokens in 51.875s, assessment 14103+9882 tokens in 97.594s. Total 32295
returned tokens, no unknown usage. Including v1, this work added 3 complete calls
and 41136 tokens; cumulative Provider reservations are at least 172. None is an
output-capacity or stream failure.

The real assessment request's input ceiling was 62012; the v2 budget correction
worked on actual generated targets. However the candidate did not produce an
accepted assessment. It added `judgments[7].context_ref_note`, returned 47 judgments
for 48 targets, and interpreted the required 28-row dense additions/sweep array as
four nonempty rows. It moved the already selected comparison table into additions,
shifting later positional judgments beginning at target 21. Do not align those
later rows by position, remove the extra key, pad the arrays, or call the result
valid. Original files are untouched; manual-audit-v1.json is separate evidence.

There is also a substantive failure independent of those structural defects. The
old ambiguous target is position 16, before the observed shift. The raw judgment
calls it selected_sample/supported with no definition context and explains that
correct per-game direction and a large mixed mean difference justify “较稳定”. The
report never defines that word's meaning at this target. Correct observations do
not supply a missing author definition. The raw pass is therefore not a quality
success even if its structure were repaired. Several scope anchors are descriptive
predicates instead of source sample anchors; unchanged validators still reject.
No accepted initial evaluation, revision or recheck occurred; the positive case
was not started. Workbench and production defaults remain unchanged.

Adjudication: do NOT adopt this two-stage implementation as a reliable Coach.
Its first stage only extracts spans; the second still combines full numerical,
source, advice, scope and explanatory duties. It did not actually isolate the
scope-interpretation task that earlier narrow diagnostics investigated. Dense
positional arrays also introduce unnecessary omission/misalignment failure modes.
These are design findings, not evidence that a new prompt or a larger budget
would fix model semantics. Stop further paid runs of this candidate.

Unique next engineering action: one OFFLINE revision of the workflow decision,
using the saved responses. Compare a first pass that performs factual review AND
finds inference targets with a second pass dedicated to interpretation of those
inference targets. The latter must retain the complete report/facts for context,
use explicit short target handles for a batch (host owns the source text), and use
sparse explicit source references for genuinely new claims. Do not demand 28 empty
arrays or let one skipped result shift every later target. Show how numerical
failure diagnostics, omitted inferences, headings, negation, later conflict and
all final issues survive composition before registering another candidate.
Demonstrate a concrete way to challenge a data-based rationalization of an
undefined term; changing JSON shape alone is insufficient. If the two-call/five-
call budget cannot accommodate a reliable correction path, state that conflict
instead of disguising another full review as a narrow scope check.

No new live run is authorized by this *document's* next action until that offline
integration evidence and same-SHA public checks exist; standing user authorization
for bounded project work remains in force, so this is not a request for repeated
user permission. The gate is concrete engineering evidence. Stage 8E remains in
progress. The four-surface visual/product follow-up remains deferred in its memo.

## 2026-09-15 Integrated v1 observation and v2 actual-target budget repair

Implementation d70416206b8febdcb8aa6a21f27c427cb7f21aa7 passed all three jobs in
Actions 34946858753. The full-report pair stopped before assessment:
`integrated-review-d704162-definitions` planned 2 / started 1 / finalized 1 /
interrupted 0 / not started 1. Discovery returned complete stop and selected 57
valid source spans. Returned input 2445 + output 6396 = 8841 tokens, one Provider
request, no unknown usage. Cumulative reservations are at least 170. No semantic
assessment, report revision or recheck occurred, so this is not a semantic failure
or success. Original request/response/receipt files remain unchanged; the new
manual-audit-v1.json records the independent offline diagnosis.

The assessment builder reached 64348 input-ceiling tokens, above 64000, and stopped
locally BEFORE a second Provider call. The earlier complete-block shape measured
only 28 targets for this report. That estimate was not a generated-span bound;
the actual source selection legitimately expanded it. This exposed a gap in the
candidate request builder, not output exhaustion, GLM profile or a lost stream.

Adopt a distinct `golden-integrated-review-v2` experiment identity. Avoid a redundant
quote_ref wrapper around every known target and check the actual assembled
assessment after budget metadata. When needed, remove only optional numeric-source
navigation entries and increase their explicit omitted count; all source values,
report text, target references, generation facts, knowledge, instructions and schema
remain complete. Stop before I/O if the complete core still cannot fit. Keep
63936 as the preparation threshold, allowing 64 tokens of headroom within the same
64000 input limit for a shorter deadline representation. Do not raise any limits.

Offline replay of the exact saved 57 targets now measures 63136 after the budget
wrapper with the complete core unchanged. This shape needs no navigation removal;
a separate boundary regression exercises actual removal and rejects a core overrun.
The existing request/response files are not reclassified as a successful report.
31 focused tests pass. The ten full-block shapes plus historical revision measure
359276 total reservation in data/evaluation/results/golden_integrated_workflow_v2.json;
these remain measured shapes, not a guarantee for arbitrary future output or time.

Next: same-SHA public checks for v2, then a fresh complete-report definition pair
through discovery, assessment, optional revision and full recheck. Keep old v1
failure, old usage, source data and frozen labels. The new run has its own shared
report budget; it must not pretend the earlier extraction was a new model result.
Stop on a protocol/transport/semantic failure and inspect the concrete evidence.
No production registration, Workbench admission, redesign or stage advancement.

## 2026-09-15 Integrated whole-report candidate (offline verified, live pending)

The new isolated `golden-integrated-review-v1` prototype separates source discovery
from assessment. Discovery receives the complete ordered report and user request,
selects spans without a verdict, and does not need the numeric/knowledge payload.
Assessment receives ALL generation facts, inference facts/provenance, deterministic
source facts, knowledge and the complete report. Model-selected spans become
host-owned targets; complete headings and any block with no selected spans are
always retained. Assessment judges each target by position and separately sweeps
all source blocks for omitted assertions. It may add a later conflicting statement;
a correct first clause cannot make an omitted later clause disappear structurally.
A model can still misclassify or overlook a sentence: ordinal/coverage validation
is not evidence of semantic correctness.

Two calls per evaluation are allocated to discovery and assessment. If discovery
format/coverage is invalid, concrete bounded locations are included in assessment,
which then receives every complete block as a target and must discover/split out
claims itself. A valid prompt-injection finding stops immediately, even with other
invalid discovery fields. After assessment, the unchanged contextual validators
check source, evidence, numerical support, scope, headings and issue relations.
Additional numerical checks reject unsupported numbers in explanations; correct
numbers or fluent text can still make wrong mean-versus-individual claims. This
remains a real semantic acceptance item, with an explicit test of the limitation.

Assessment issues bind to target quotes on the host and pass to the existing full
revision request. Canonical diagnostic locations are retained on a rejected final
assessment. Tradeoff: there is no third format-repair call after assessment; an
invalid second output stops the report, rather than re-running silently. This is
not a claim that the old diagnostic helper now repairs frozen Coach 1.3.27.
The workflow permits one revision and a fresh two-call full recheck, at most five
calls. Recheck requires the exact revised text and unchanged facts/knowledge.

`ReceiptedStreamProvider` reads its own reservation and terminal result, after the
real `CoachBudgetedProvider` transformation. The host compares exact issued-input
bytes with that trusted SHA; model output has no source/target identity fields.
It uses existing high/32768/300-second transport, zero retries, and the shared
401920-token/900-second budget. No old Coach/Skill/program registration is changed.
This is an explicit experiment entry, not a production default or new release.

Files: `golden_integrated_review.py` owns requests, source restoration and canonical
validation; `golden_integrated_runtime.py` owns receipt binding, state transitions,
revision/recheck and budget integration; `run_golden_integrated_review.py` is the
isolated real entry; `test_golden_integrated_review.py` supplies scripted protocol
and control-flow tests. These scripts reuse historical validators without editing
old outputs, labels or receipts. The meaningful owner-learning distinction is:
source identity belongs to the host, discovery/interpretation belongs to the
model, and acceptance requires both transport and independently reviewed meaning.

Offline measurement on ten frozen complete reports is in
`data/evaluation/results/golden_integrated_workflow_v1.json`. Discovery requests
measure 12500–12676 input-ceiling tokens; assessment shapes 58648–58866. One complete
historical revision shape measures 53584. Combining the maxima twice and all five
32768 output reservations gives 360508, below 401920. These are conservative size
estimates, not billed usage, model accuracy or an arbitrary-future-output bound.
Every actual generated target/assessment/revision is checked again. Five calls at
300 seconds each do not fit 900 seconds; the shared deadline still stops overruns.

Implementation choice: the first prototype duplicated target text plus unbounded
numeric navigation and reached 80352 assessment input tokens offline. It was
rejected BEFORE external I/O. The adopted request references existing complete
source blocks and bounds navigation to 3000 JSON characters, without dropping the
underlying facts. This does not increase output limits or lower reasoning effort.

Next live gate after same-SHA public checks: one explicit-definition pair of
complete reports with no supplied target/label to either model request. At most
five calls and one revision per report; stop the pair on initial label mismatch,
invalid output, transport failure or unsuccessful revision/recheck. Persist the
original initial result separately so later revision never erases a control
failure. Manually inspect definitions, means versus individual comparisons,
source facts, all discovered targets and additions before any acceptance. Only
then consider the remaining frozen heading/negation/future/conflict pairs. This
is not a third narrow target probe and is not a held-out quality score.

Run preview with `python -m scripts.run_golden_integrated_review --source-run
 data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
 data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`.
Real use appends `--execute --pair 1 --ci-run <same-SHA-success> --env-file
 <private-path> --run-id integrated-review-<sha>-definitions` and writes only to
private run artifacts. Provider reservation/returned usage are counted separately;
interrupted and unstarted cases remain explicit. Stage 8E stays in progress,
Workbench report admission and the four-surface redesign remain pending.

## 2026-09-15 v2 observation and host-owned target binding

Public closeout: offline binding implementation
`753267aa57a34c1460ac37d2f6c21a0ae7aa29fc` passed all three jobs in Actions
`34943310239`. The final issued-input/tool-choice guard also passed its seven
focused tests after the 43-test regression run. This closeout changes documents
only and binds evidence to that implementation SHA; it does not claim a new
model result, runtime registration or whole-report admission. Temporary Git API
relay code is removed after publishing this record. The next action below is
full-report offline integration design/verification, not a third target probe.

Implementation `86358e85839b00128eb4d64672780b22b1f12674` passed Actions
`34941920885`, all three jobs. `context-relation-86358e8-v2` stopped after case 3:
planned 4 / started 3 / finalized 3 / interrupted 0 / not started 1. All three
Provider calls completed with stop. Returned input 28000 + output 1936 = **29936
tokens**, no unknown usage. Cumulative reservations are at least **169**. The two
narrow experiments together used 7 complete calls and 69136 returned tokens.
Earlier historical unknown usage remains unknown.

| Case | V2 observation | Boundary |
|---|---|---|
| stable_unbounded | valid, needs_clarification | Correct target classification |
| stable_defined_before | valid, sample_defined | Explicit definition recognized; explanation inserts group means into an individual-game comparison and is not fully fact-validated |
| heading_unbounded | raw needs_clarification, protocol invalid | Model echoes the complete visible heading while omitting `## ` in target_ref; exact target check rejects |
| heading_defined_after | not started | No v2 result |

Terminal times: 10.484 / 6.297 / 18.094 seconds. The third interpretation correctly
identified missing meaning rather than definite extrapolation, but is not an
accepted v2 result. Do not count it as passing or combine versions into all four.
The previous definition-copy defect has not received a v2 fourth-case result.
No third paid diagnostic follows this batch.

Root design correction: a known request target is host-owned identity. Asking the
model to echo its Markdown representation or source digest is redundant and does
not prove semantic correctness. This recreates a copying failure after source
references were introduced to reduce copying. Keep model-chosen definition
references, but bind the requested target and source through the actual request.

`golden_bound_scope_review.py` is an **offline seam**, not a registered runtime.
It preserves all complete data and the single target in the input; output contains
only disposition, context_ref and explanation. `seal_issued_request` runs after
trusted budget-wrapper changes, verifies unchanged messages/schema, and computes
the same exact byte SHA as `golden_stream_bridge.validate_request`. `decode`
requires that SHA from the trusted transport receipt, restores the full original
target including Markdown, resolves any definition reference, and retains the
model explanation. The receipt SHA must never come from model JSON. Actual
transport/runtime integration is still required; a caller-provided fake receipt
or a unit test is not end-to-end provenance evidence.

Data flow: prepare full input → budget wrapper → seal exact issued bytes → trusted
transport response/receipt → compare request SHA → parse judgment → restore host
source/target and model-chosen context. Changed input/schema, wrong receipt, stale
reference, incomplete stream and model-injected identity fields reject. A source
reference still does not prove meaning, and numerical explanation errors remain
semantic work. No automatic whole-report pass is produced.

Verification: 43 focused/adjacent tests passed. The old third response is preserved;
an explicitly scripted projection removes its redundant model identity fields
and demonstrates that the host restores the exact `##` heading. This is not a new
model result or acceptance of the old response. Full post-budget request sizes
are in `data/evaluation/results/golden_bound_scope_review_v1.json`. Current tests
exercise binding after a changed deadline/metadata, mismatch rejection, exact
heading restoration, literal context restoration and unchanged complete facts.
Run `python -m pytest tests/test_golden_bound_scope_review.py
 tests/test_golden_context_relation_probe_v2.py tests/test_golden_context_diagnostics.py`
for the core offline checks. No real CLI mode exists for this seam.

Next bounded engineering action: prove the unified full-report data flow and
budget offline before an isolated runtime candidate. It must automatically find
review targets, preserve numerical/source/coverage/security checks, use the
concrete diagnostic feedback, and schedule scope interpretation within at most
two calls per evaluation and one revision/five calls per report. Retain the
existing shared 401920-token/900-second bound; do not assume five maximum-sized
requests fit. Verify negation, explicit extrapolation, missing target discovery
and later contradictory claims as well as these four scope controls. The narrow
runner's accept→sample_defined mapping is intentionally limited to these four
cases and must not be reused for negation or whole-report quality scoring.

Do not launch another isolated target-only probe, register the offline seam as a
finished Coach, or replace the Workbench report before the integrated evidence.
Stage 8E stays in progress. Learning outcome: source identity is a transport/host
responsibility; model interpretation is a separate, still fallible obligation.

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
