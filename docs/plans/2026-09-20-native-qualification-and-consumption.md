# Native qualification, claim scope diagnosis and product consumption

## Current result and v3.6 offline design — 2026-09-21

V3.5 ran after clean `0cdb1c7dd0b51d7b1f23b21b1bb4b092f159425b` passed all
three public jobs in Actions `35550890557`.

| Full-report case | Observed result | Independent decision | Calls | Tokens |
|---|---|---|---:|---:|
| original topic window | 95/pass | Accept | 1 | 13458 |
| actual revised topic | 97/pass | Accept | 1 | 13948 |
| explicit combined population | 80/needs_revision → actual revision → 96/pass | Accept | 3 | 39967 |
| explicit universal metrics | Correct target detection, wrong all-mid vision mean in both reviews; changed issue labelled retained | Reject: semantic and protocol | 2 | 29557 |

Total: 7 completed calls, 82303 input + 14627 output = 96930 tokens; unknown
usage 0; historical Provider calls at least 265. The batch stopped at case 4,
before revision. Cases 5–7, original negatives, historical five and product
did not run. This attempted trailing-text recovery **failed**.

`golden_native_claim_scope_result_0cdb1c7.json` is an analyst summary, with full
reports/revision, public response fields, original receipts and 68 immutable
file hashes. All seven issued requests were reconstructed from the original
implementation, including the budget wrapper metadata and transport hashes.
Original automated receipts still say manual acceptance is false; independent
manual findings are separate, not edits to those receipts.

### End-to-end diagnosis

The four middle vision values are 40/43/25/27: all-mid mean **33.75**, winning
mean **33.5**, losing mean **34**, median **33.5**. Source 16 explicitly identifies
the winning group. Sources 1/20 also permit `(45*5-90)/4=33.75`; the source data
was present and correct. Computed source 31 contains the full calculation and
early-death operands (middle 1.5, support 7, selected 2.6). The selected roots
1/16/20 do not fully support those early-death operands. This is not missing
input, truncation or an output-limit failure, and no internal model cause is
claimed from its text.

The execution contract separately asked for a complete new review while
offering exact-copy retained versus replaced. Two real recoveries have now
failed around that distinction. Repeating the same rule more forcefully was
insufficient; the first uncommitted attempt also exceeded the offline budget.
That wording-only attempt was discarded, not promoted as a repair.

### Implemented change and rejected alternatives

V3.6 / Coach1.4.6 / Skill0.6.0 / Program3.0.6 / wire3.2.0:

- New review schema and validator allow only `replaced` or `withdrawn` for old
  findings. Replaced points to the current complete issue even when unchanged;
  withdrawn has no target and requires explanation and real source references.
  Every original finding is accounted for; full raw text and suffix survive.
  No automatic relabelling, field filling or extra call is introduced. Strict
  retained validation remains only in the explicitly named legacy wire replay,
  which also fixes source resolution to the adjacent v3.5 row layout. Its journal
  cannot silently bind old references to the new projected catalog.
- Native computed evidence is transposed to named statistic arrays in metric
  order: `win_mean`, `loss_mean`, `cohort_mean`, `cohort_median`, `all_pairs`,
  `missing_refs`. Original values, membership, completeness and role contrasts
  reconstruct exactly. Request and resolved source hash the same projection;
  original input identity and reference numbering stay stable. Default old
  callers keep their original layout. This reduces cross-column lookup; it is
  not proof that layout caused or fixed the observed model mistake.
- Avoid full objects per metric: an offline prototype added about 4352 input
  units per request. The chosen transpose is smaller. No model/effort/budget,
  whole-context acceptance standard, default production policy or architecture
  is changed; no ShowMaker answer is encoded in runtime validation.

### Verification and its limits

`scripts/check_native_claim_scope.py --reassessment` reproduces a decisive
counterexample: changing only the second real response's disposition makes the
wire valid while leaving its false 33.5 claim. It also reconstructs the mean
from original rows, checks delivered/selected evidence, produces four complete
statistic-binding controls, and runs an explicitly analyst-authored corrected
review → report revision → full recheck witness. These controls and witness are
offline engineering evidence, not model judgments or added live successes.

161 affected local tests passed, including source reconstruction/hash binding,
missing-field and trailing-text recovery, native application, runner and Prompt
Program checks. Runtime composition verifies the regenerated manifest. Aggregate
evidence is `golden_native_v36_offline_qualification_v2.json`:

| Scripted five-call path | Full output reservation |
|---|---:|
| seven claim-scope controls | 380514 |
| preserved failure plus analyst-corrected recovery | 382552 |
| historical five controls | 400972 |
| original attribution pair | 380036 |

All are below 401920; every measured input is below 63936, including the long
historical reassessment at 58972. Actual usage plus next reservation remains
authoritative: these are not guarantees for arbitrary response lengths.

### Next executable action and product path

Independent review accepted the new wire, manifest, original-request audit and
numeric counterexamples. Commit and exact-SHA public CI are recorded on PR7.
**No additional paid request in this turn.** Native remains
`offline_claim_scope_reassessment_contract`; product remains offline. A later
development-admission change must refresh the manifest and obtain its own
exact-SHA public checks before any paid request, under existing authorization.

Next bounded qualification order: claim-scope 1 → 4 (this failure) → 3;
then original scope 5/4/3; then remaining claim-scope 2/5/6/7 and the historical
five. All original sources, complete reports and labels stay frozen. Read each
entire review and actual revision before continuing, including every numeric
statement and selected source in the review itself. A schema-valid response with
33.5 as the all-mid mean is still a failure. Stop on the first semantic or
execution failure. Do not force malformed output merely to exercise recovery;
if no live recovery occurs, that qualification limit remains explicit. The four
new statistic-binding full reports are available as focused offline regression
evidence, not silently counted as live tests or automatically required extra calls.

After same-version quality qualification: source-bound product generation →
review/necessary revision → immutable Evidence save/read; then real task lease
and atomic-commit integration, API and Workbench consumption, independent
evaluation and learning coverage. GLM/high and the 5-call/1-revision/401920-token/
900-second envelope are unchanged. Stage8E remains in progress. Frontend redesign,
champion portraits, Coach/Review/Training/Evidence links, requested personal
Training and the full 62-theme list remain in the Astra restart plan.

## Historical records — current action is above

## Latest result: 2026-09-21

The paid batch is closed. Clean implementation
`5aa20b450c1b539b6030d66e6e67bdf62a6781c5` passed all three public jobs in
Actions `35521189302` before any request. The actual order and manual decisions:

| Scope case | Actual behavior | Manual decision | Calls | Tokens |
|---|---|---|---:|---:|
| 1, later explicit scope | 98/pass on unchanged correct report | Accept | 1 | 13542 |
| 5, original damage attribution | 82/needs_revision; only block 14 changed; 98/pass | Accept | 3 | 43680 |
| 4, wrong grouped death count | Detected incorrect 2.67 for mid losses, corrected to 0.5; affected blocks 4/14 revised; 96/pass | Accept | 3 | 42544 |
| 2, explicit correct introduction | 98/pass | Accept | 1 | 12995 |
| 3, explicit wrong introduction | Target error found, but extra scope false positives in both initial and final review; final 85/needs_revision | Reject | 3 | 47396 |

Total: 11 completed calls, 126300 input + 33857 output = 160157 tokens,
unknown usage 0; historical Provider calls at least 258. The historical five
controls and product generation did not run in this batch. Immutable original
receipts, actual public response fields and full revised reports are preserved
in `data/evaluation/results/golden_native_scope_result_5aa20b4.json`; private
reasoning is excluded. Independent review accepted the same four cases and
rejected case 3, checked 110 file hashes and reconstructed all 11 actual
requests against the frozen implementation. This is development evidence,
not a representative accuracy estimate or product admission.

The original attribution failure has real, bounded improvement: the selected
sample's damage win-loss gap is 695.418333..., while the mid-only gap is still
669.235; removing support changes it by only 26.183333.... By contrast the CS
gap changes from 2.351666... to -0.205. The model distinguished the metrics,
revised only the faulty conclusion and accepted the corrected report. These
successes do not cancel the remaining false positive.

Case 4 avoided malformed output, so it does not prove live missing-field
recovery. Case 5's first response ended in two backticks; the pre-existing
normalizer accepts that formatting-only suffix. It did not cause a reassessment
and was not a new parser relaxation. All original text remains available.

## Diagnosis and the offline v3.5 change

Case 3's initial review correctly rejected the explicit mid-only early-death
claim, but also treated “这5局内” as an explicit five-game merged denominator
despite the same sentence's mid topic and actual mid values. After the real
revision, it read unspecified “均值” as **every** metric, although the report
already separated CS/damage and printed the opposite vision/death directions.
The final suggestion also confused block 4 with section 4. These are semantic
scope/quantifier errors; complete stops and correct source arithmetic rule out
the previously observed stream, output-budget and missing-field failures here.

The final reviewer does not receive the previous review, but that alone cannot
explain the initial false positive. Adding history or a diff could reinforce
the first wrong opinion. No new fixed call, schema field, keyword exemption,
automatic issue filter or reviewer architecture is introduced for this failure.

Native v3.5 replaces the existing scope supplement: establish the claim's
subject, metric, cohort and quantifier from the whole report before computing.
A window size is not automatically a new denominator; an unspecified mean is
not an all-metrics claim. Explicit factual conflicts and unresolved ambiguity
that changes the conclusion still block. Merely finding one supported reading
is insufficient: independent review caught that overly permissive formulation,
and it was corrected before commitment or any further paid request.

Coach1.4.5 / Skill0.6.0 / Program3.0.5 bind native v3.5 / wire3.1.0. The checked-in
manifest is regenerated with the existing fingerprint algorithm and actual
Runtime composition verified. Native will use `bounded_development_after_exact_ci`
only after the new exact-SHA public checks;
the product runner stays `offline_source_binding_and_attribution_review`.

Seven frozen full-report controls in
`data/evaluation/datasets/golden_native_claim_scope_controls_v1.json` bind the
unchanged sources and original result. Independent labels, in file order, are
accept / accept / reject / reject / accept / reject / accept. They cover the
original wording, the actual revised report, explicitly merged population,
explicit universal metrics, explicit scoped metrics, genuinely unresolved
population and two clearly conditional populations. Labels stay outside model
requests. These are development controls, not holdout. The existing runner now
accepts `--suite claim-scope`; local preview uses the same committed source
loader, with execution still blocked before credentials or Provider creation.
Preview the intended policy via `python -m scripts.run_golden_native_issues_review
--suite claim-scope --case-index 1` (one command). The base
`run_golden_native_review` entry defaults to the older semantic candidate.

## Offline verification and next action

123 affected tests passed across native review/reassessment, missing-field
recovery, role arithmetic, runner, application, sender, Prompt Program and the
new controls. The new test also runs the committed-source audit in CI and rejects
changed origin, source or report identities. Source artifact line endings are
pinned where byte hashes cross platforms. Evidence:

- `golden_native_claim_scope_offline_v1.json`: 7 complete reports / 25 blocks,
  inputs 44630–44936; the real failure still replays as needs_revision; a
  distinctly analyst-authored five-call witness reserves 381302 < 401920.
- `golden_native_scope_review_offline_v3.json`: historical five unchanged
  controls, full five-call reservation 401762 < 401920; long historical response
  reassessment input 59154 < 63936.
- `golden_native_attribution_offline_v3.json`: original attribution pair and
  five-call reservation 380824 < 401920, with independent Decimal arithmetic.
- `golden_native_scope_controls_offline_v3.json`: the five prior scope controls
  retain the same calculated sources and labels.

These reservations describe the measured scripted responses, not a guarantee
for any possible long response. Actual usage plus the next request reservation
remains authoritative. No limit was increased. The earlier paid batch ended at
the first semantic failure; this new turn may run the separately gated v3.5
qualification batch below. Offline evidence does not establish the semantic fix.

Next, qualify v3.5 through the existing development gate, refreshing its manifest
and obtaining public checks for the resulting exact SHA before live requests.
The first qualification batch is at most ten distinct reports: the seven new
controls, then original scope 5/4/3. Read each complete result and actual revision;
stop on the first semantic or execution failure. Scope 1 equals the first new
control and must not be charged twice. If all are accepted, complete the same
implementation's remaining scope 2 and five historical controls before product
qualification. Do not combine successes from different versions into one pass.

Then resume source-bound product generation, saved Evidence readback, real
Worker/database transaction and owner API/Workbench consumption using the
existing services. Independent evaluation and applicable learning coverage
remain prerequisites for Stage8E completion. Frontend aesthetics/rebuild,
portraits, Coach/Review/Training/Evidence, personal Training and all 62 themes
remain in `2026-09-16-astra-restart-plan.md`; they are not replaced by this
diagnostic work. Production defaults and the manual Workbench report remain as
before. This next action uses existing authorization, not a new approval gate.

The sections below preserve the initial batch plan and its preflight correction.

## Start and decision

Continue Stage8E from backend commit 3f7836022be7641a5964ca807a3540d93abfff8d.
Public run 35434107706 passed pytest, postgres-migrations and packaging-smoke.
The missing-field contract fix already passed 70 affected offline checks and
independent review, including the unchanged real responses/input identity and
the full five-call replacement/revision/recheck witness. This permits bounded
development observation, not semantic or production approval. Only the native
development gate changes; review policy v3.4 and all budgets remain unchanged.
The new admission commit must itself pass exact-SHA public checks before calls.

## Execution and acceptance

1. Run scope case 1 (unchanged correct attribution report), then case 5 (the
   original unsupported damage attribution). Manually read each entire review,
   selected sources and revised report before another case. Correct locations
   or a model pass alone are insufficient. Scope 1/5 are the attribution pair;
   do not call their aliases again.
2. If both succeed, run scope 4 (wrong grouped number and prior missing-field
   failure), then scope 2/3 (explicit correct/wrong scope), followed by the five
   frozen historical controls. Keep labels out of model requests. A case that
   avoids malformed output does not establish actual missing-field recovery;
   record that distinction without manufacturing a live error or extra call.
3. Each case retains its existing maximum 5 calls, 1 revision, 401920 tokens,
   900 seconds; each call retains GLM/high, 32768 output, 300 seconds, zero SDK
   retries and the 63936 input ceiling. At most ten distinct controls enter this
   batch. A failed semantic or execution result ends the batch immediately.
   Preserve failure and usage, then diagnose input/output/validation together.
   A local patch is not grounds for another paid batch in this turn.
4. Only after all required controls are accepted, qualify the source-bound
   product runner against these actual results and run one complete frozen
   ShowMaker product observation after the corresponding public checks. Verify
   RAG, generated/revised text, sources, identity, shared budget and saved
   Evidence readback. A failure ends paid work and requires diagnosis.
5. Accepted product quality permits the existing Worker atomic transaction,
   owner API and Workbench consumption verification. Reuse existing services;
   distinguish isolated tests, actual database/API/browser evidence and public
   deployment. Preserve the manual Workbench report and main-tree frontend work.

Current continuation is already authorized; the previous turn's no-third-batch
limit is preserved as historical, not a permanent ban. No budget, model, user
acceptance standard or stage boundary changes. Stop a failed batch based on
evidence, not because another authorization message is needed.

## Completion and remaining scope

Persist exact implementation/CI identities, immutable receipts, full actual
content (excluding private reasoning), manual decisions and known/unknown usage.
Update canonical state, active plan and PR with one evidence-based next action.
Never transfer older successful semantics automatically to this implementation.
Stage8E completion still requires applicable independent evaluation and learning
coverage. Frontend aesthetics/rebuild, portraits, Coach/Review/Training/Evidence,
personal Training and all 62 tracked themes remain in the Astra restart plan.

## Preflight integration correction

Admission commit dde258c / CI35520737854 failed eight native application tests:
changing LIVE_STATUS changed a fingerprinted module, but its checked-in manifest
was not refreshed. The narrow runner/recovery tests omitted this dependency.
The manifest is regenerated from existing component_fingerprints/digest_for;
only the native module fingerprint changes. Actual Runtime composition and the
existing native application/Prompt Program tests are now included in preflight.
No validator is weakened, no semantic policy changes, and no paid call preceded
this failure. Future admission/status edits must verify their product manifest
even when the model-visible request is unchanged.
