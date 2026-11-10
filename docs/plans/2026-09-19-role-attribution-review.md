# Metric-specific attribution review

## Latest outcome: three accepted controls, then missing-field recovery failure

V3.3 (ad6b2d9/CI35432825188 all three jobs successful) made7 complete calls:
81603 input +19607 output=101210 tokens, no unknown usage. Both positives
passed, including the exact earlier false positive. The explicit-mid scope
negative correctly located the error, changed only its relevant sentence, and
rechecked97/pass. All three outcomes were manually accepted. This is a real
bounded improvement, not attribution recall or overall admission.

Case4 found the wrong mid early-death value, but both initial and sole allowed
reassessment omitted issue.block. The second explanation claimed it had added
block14; the JSON had not. Strict validation correctly stopped before revision.
The batch ended; case5 (the original attribution miss) and the historical five
were not run. All receipts/text/hashes and manual decisions are preserved in
`golden_native_scope_result_ad6b2d9.json`. Across both new batches:8 calls,
117430 tokens, no unknown usage; historical Provider count at least247.

Offline replay exposed a separate wording mismatch: retained is exact equality
in the validator, while the prompt described the same problem. Adding a field
with retained is invalid; the same fully corrected issue with replaced has a
valid path. This does not establish why the model omitted block. V3.4 makes
that existing contract explicit; it does not infer block from prose, insert a
field, erase an issue, relax final validation or add another call. Its live
status is `offline_missing_field_reassessment`, Coach1.4.4/Program3.0.4.

The fixture preserves the original input identity and both real responses.
Seventy affected checks passed. An analyst-authored block addition plus explicit
replacement reaches revision and recheck including a second format correction
in five calls, reservation383294. Original-control five-call reservation401442;
actual-usage budgeting remains authoritative. The original missing fields are
still rejected. No scripted success is credited to the model.

Independent final review passed: all17 raw-file hashes, both response contents, original input identity, five-call arithmetic and live manifest verification matched. It found no blocking offline defect and confirmed that the real reassessment also changed explanation, so retained would still be invalid even if block were added. Real correction remains unproven. Next complete exact-SHA CI and the new candidate qualification.
Prioritize the full positive then original attribution negative in the next
bounded batch, before supplementary controls; this run left the central
attribution effect unmeasured by putting all added scope cases ahead of it.
Preserve all required regressions rather than dropping them. No third paid
batch in this turn. Product execution remains offline and Stage8E in progress.


## Current candidate after independent scope review

An independent default Codex agent read all five complete scope reports, both
parent reports and all three hashed original sources, and recomputed the key
numbers. It confirmed accept/accept/reject/reject/reject. Later same-metric
scope resolves an unspecified earlier scope; explicit wrong mid scope is a
source-fact error and is not excused by a correct statement about another
cohort. The Luna delegation failed with unsupported-model404 before execution;
it provided no review and changed no product GLM setting.

V3.3 implements that ordering in the existing review policy: determine scope
from the whole document before selecting numeric groups. It moves the adopted
whole-context rule forward and explains the explicit-versus-inferred scope
boundary, without duplicate output fields, mandatory calls, automatic issue
suppression or semantic approval by the host. Coach1.4.3/Program3.0.3 bind it;
wire3.1 and Skill0.6 stay unchanged. The v3.2 failure remains failed. The new
native candidate uses same-SHA development admission; product execution remains
offline. Seventy-seven affected checks passed; full scripted budget artifacts
cover original controls and attribution revision/recheck. Five maximum-output
reservations are400722 and379784 respectively, still subject to actual usage.

After this implementation's three public CI jobs pass, run scope cases1,2
(positives) then3,4,5 (explicit-scope/numeric/attribution negatives), manually
inspect each full opinion and actual revision before advancing. Case1 is the
unchanged attribution positive and case5 the unchanged attribution negative;
do not run their aliases again. Any failure stops the batch. Only after those
and the five historical controls pass can the source-bound product run resume.


## Live result and current stop

Implementation 3a73231 / public CI35431889592 passed all three jobs. The first
complete positive returned 80/needs_revision after 63.704 seconds, with 11562
input + 4658 output tokens and no unknown usage. It reported an early-death
scope error: mid wins/losses 2.5/0.5 versus selected 2.5/2.6667. Those numbers
are correct; the scope assignment is the issue. Its explanation acknowledges
that block14 explicitly provides selected scope but treats block4's proximity
to a mid damage clause as binding. Block4 does not explicitly call early deaths
mid-only. Under the adopted whole-context rule, later same-metric specifics
resolve that clause; this is an editorial clarity opportunity, not a blocking
fact error. Neither labels nor the response were rewritten.

The batch stopped at one call. The original attribution negative, revision,
recheck and five historical regressions were not tested on v3.2. The new
arithmetic therefore remains engineering evidence, not established recall.
Both data and policy changed in v3.2; this single result cannot isolate which,
if either, caused the scope choice. Native status is now
`offline_role_scope_false_positive`; product status remains offline.

The five full-report scope controls preserve all original data and 25 blocks:
late explicit same-metric scope and explicit scope in both places are positive;
explicit wrong mid scope, wrong mid loss number, and the original false damage
attribution remain negative. This prevents a permissive 'any later correct
sentence cancels an error' fix. They are analyst development labels and still
need independent review. `check_native_product_regression --scope-controls`
proves unchanged arithmetic/source delivery and input ceilings 43860–43958,
not model judgments. The next method review must establish whole-document
scope before numerical judgment, distinguish explicit assertions from an
inferred local reading, and retain per-metric attribution scrutiny without a
new mandatory call or a repeated fact-report output protocol. Do not start
another paid batch immediately after a local policy patch.


The ac2725c product report conflated CS and damage: its review returned 97/pass
even though removing support changed the damage win/loss gap only from 695.4183
to 669.235. Both source groups were already present. Transport completed; the
external-source binding defect was independent. The observed cause is an
unsupported compound inference accepted by the reviewer, not an established
claim about the model's hidden reasoning.

## Decision

Keep the native issue-list workflow and wire 3.1.0. Add deterministic role
contrasts to its existing computed evidence source. For every supplied role and
metric, show the selected win-minus-loss mean, role win-minus-loss mean, and
their difference, calculated from unrounded source values. Preserve member
references, completeness, missing metrics and single-outcome nulls. These are
descriptive regroupings, never causal contributions or counterfactual effects.

The reviewer checks each metric in a compound inference separately and tests
the direction and magnitude of claimed composition effects. Valid sample
explanations, negations and conditional hypotheses remain allowed. No numeric
threshold or ShowMaker-specific answer is encoded. The host does not interpret
natural-language claims or auto-approve them.

Rejected alternatives: a phrase-only warning supplies no discriminating
arithmetic; rejecting every attribution would falsely block supported sample
descriptions; forcing a new claim graph or a second mandatory review repeats
earlier output/budget complexity. This change adds data to the existing review,
revision and recheck without extra mandatory calls or new response fields.

Native policy becomes v3.2; Coach 1.4.2 / Skill 0.6.0 / Program 3.0.2 retain
wire 3.1.0. Legacy computed-source callers default to their existing data shape.
All model settings, source rules, whole-context acceptance and shared budgets
remain unchanged. The product runner stays offline pending quality evidence.

## Evidence and execution

1. Check contrast arithmetic against raw values; test reversed/zero gaps,
   missing metrics, single outcomes, capped rows and input identity. Confirm
   the model and source resolver see the same hashed contrast values.
2. Preserve the five prior controls and the original attribution pair byte for
   byte. The pair's shorter observed-user request makes it a development
   control, not an exact replay of the product request. Labels and independently
   calculated expected answers never enter the model input.
3. Exercise original full-report regressions, normal revision/recheck and both
   allowed format-reassessment calls offline. Measure all request reservations
   and retain the actual-usage budget rule. Run relevant tests and same-SHA
   public pytest/Postgres/packaging checks before any paid request.
4. Run the attribution correct report first; inspect its complete judgment.
   Then the wrong report must be located, actually revised and rechecked, with
   every explanation/source and all revised text inspected. Recheck the prior
   five controls on this implementation. Any failed case ends the paid batch;
   preserve it and diagnose before considering another candidate.
5. Only qualified semantics permit a new complete product observation with
   source binding and saved-result readback. Task transaction/API/Workbench,
   independent evaluation and learning coverage remain required. This control
   suite is neither a holdout accuracy estimate nor Stage8E completion.

All downstream frontend aesthetics/portraits, four-part Workbench and personal
Training requirements remain in the Astra restart plan and 62-theme ledger.
