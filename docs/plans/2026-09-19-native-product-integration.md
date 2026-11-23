# Native review into the existing product pipeline

## Latest result: transport and file delivery worked; semantic admission failed

`ac2725c` passed all three jobs in Actions35424463066. The single frozen
ShowMaker product run completed real local RAG, generation, native review and
Evidence file publication. Three complete calls took 21.391/54.359/21.688 seconds
and used 26883 input + 3494 output = 30377 tokens, with no unknown usage.
RunQueryService independently read the same report hash, summary and all five
timelines. Historical Provider count is now at least 239. Evidence:
`data/evaluation/results/golden_native_product_result_ac2725c.json`.

The model returned 97/pass, but manual inspection rejected the report's claim
that the mixed-role damage gap mainly came from the support match. The selected
win/loss gap is 695.4183 damage/min; removing support leaves 669.235. Only 26.1833
changes. The correct CS composition observation cannot justify the same damage
attribution. The original response and files remain unchanged. This is a new
false negative from unrestricted generation, not a timeout, output cap or a
retraction of the five earlier control outcomes. No further paid run followed.

Input tracing also found that publication sources were saved but never passed
to generation or review. The standalone controls had supplied them. This is a
separate integration defect, not proof of why the model missed the attribution:
the needed damage numbers were already present. Both supplied OP.GG snapshots
expired on September 10; fixing input delivery must not make them current.

## Source-binding repair and bounded next action

Coach 1.4.1 / Program 3.0.1 (Skill 0.6.0, review wire 3.1.0) passes the exact
already-built publication projection to a server-side renderer. It verifies the
summary digest, reuses the existing source/position renderer, and sends one
deterministic document through generation, review, revision and persistence.
Fresh, applicable OP.GG facts retain their uses and timestamps; expired facts
remain omitted with a reason. Snapshot time is never reset and no data is
fetched. Legacy application behavior is unchanged when no renderer is supplied.
Composition, service and source-renderer files now enter candidate fingerprints.

Eleven native integration checks cover this repair, mismatched summary rejection,
the real executor/Worker atomic-commit branch, rejected/lost-lease publication
fences and conversation-turn/report binding. The task repository in those Worker
checks is a test double: they do not claim a new PostgreSQL/API/browser vertical.
Related application/publication regressions also passed. Two test-fixture defects
were corrected (existing typed text trimming and a missing empty objective-events
collection); neither required a product readback change.

The fresh source-bound preview input ceiling is 33240 < 63936. The preserved
complete attribution pair has input ceilings 41178/41260; the diagnostic
`python -m scripts.check_native_product_regression` reproduces the original
schema-valid false negative and recomputes the numerical contradiction without
Provider calls. It does not prove a semantic fix. The original five controls
are untouched; the new pair is analyst development evidence, not holdout.

The product runner is now explicitly offline pending attribution qualification.
This is a known-quality gate, not a request for more user authorization. Next:
review this full-report pair and the actual comparison evidence as one semantic
case, choose and justify any evaluator change against both the negative and its
correct counterpart, then run relevant offline/full-budget checks and exact-SHA
CI before a bounded new quality experiment. Do not claim the source-binding
repair fixes semantic recall or add another mandatory model call outside the
shared five-call budget. A fresh product run needs this quality evidence first.

The remaining task transaction/API/Workbench vertical, independent evaluation,
learning coverage, frontend redesign/portraits/four-part linkage and personalized
Training remain in the restart plan. Stage8E is still in progress.

The following describes the earlier integration milestone and its design.

The a71eb94 implementation passed public Actions35423244997 and all five
frozen analyst controls. Four wrong reports completed real detect/revise/recheck
and manual inspection; the heading case that failed before now completed too.
Thirteen complete requests consumed 151898 input + 28105 output tokens, no
unknown usage. Evidence: `golden_native_review_result_a71eb94.json`. This is
development evidence, not a holdout accuracy estimate or production admission.
No corrective reassessment was needed in this batch; that recovery path has
offline replay evidence only. Original failed receipts remain failed.

## Product problem and design

The successful standalone evaluator used its own budget and transport. Simply
calling it from Runtime would add its five requests to generation requests and
could retain a failed transport's counters for the next task. The product
composition now gives each task one fresh transport and one budget shared by
generation, review, any reassessment, revision and final review.

The normal product sequence is local RAG selection, report generation, review,
optional revision and recheck. Two generation calls plus three review/revision
calls fit the existing five-call contract. Extra generation or recovery uses
the same remaining budget; exhaustion rejects publication rather than silently
granting a second allowance. All GLM/high/output/input/time limits are retained.

The compiler gets observed/self identity from the trusted frozen relationship.
It carries that identity through generation and evaluation. Observed matches
cannot become the reader's baseline or personal Training evidence.

`build_native_coach_application` uses the existing application service, Harness,
run receipts and Evidence publication writer. It introduces no second save
pipeline. The file manifest and pending snapshot retain owner/task/run identity;
the existing Worker must still atomically commit task state and Evidence before
the frontend can treat the result as delivered.

## Identity and code map

- Coach contract 1.4.0, Skill 0.6.0 and Prompt Program 3.0.0 explicitly bind
  native wire 3.1.0. They do not impersonate an older 1.3.x implementation.
- `app/runtime/native_coach_contract.py` fingerprints current native code and
  gives generation business/report instructions, without evaluator JSON rules
  or the obsolete mandatory passed-check narrative.
- `app/runtime/review_sender.py` uses the existing budget and requires a fresh
  receipt matching the returned response. Request hashing uses actual issued
  bytes after budget adjustments.
- `app/runtime/receipted_provider_factory.py` isolates each run's state and
  keeps actual issued requests, returned responses and transport reservations.
  Reusing a run's journal path cannot overwrite evidence or make another call.
- `app/product/native_coach_composition.py` binds these parts as an explicit
  candidate. Existing Worker defaults and the manual Workbench report stay put.

## Verification and next boundary

Offline tests cover the real application/Runtime/save/read path with scripted
model responses, shared-budget exhaustion, fresh transport identity, observed
context, rejection without a final report, and immutable earlier identities.
They do not establish live semantic accuracy.

`python -m scripts.run_native_coach_product` verifies frozen source hashes and
compiles the actual initial generation request without credentials or calls.
The frozen ShowMaker preview input ceiling is 29790, below 63936. This first
request measurement is not a promise that arbitrary later output fits.

After this implementation passes exact-SHA public CI, run one bounded product
observation with `--execute --run-id native-product-<id> --ci-run <run>
--env-file <private-env-path>`. It uses frozen public-player data, real local RAG,
fresh GLM generation/review, and the existing verified Evidence file readback.
Inspect all actual responses, RAG support, report facts and any revised text.
Any failure ends the batch and retains its receipts; no automatic paid retry.

Remaining Stage8E work includes the task transaction/API/Workbench consumption
proof, representative independent evaluation, learning coverage and accepted
publication gates. Frontend aesthetics/rebuild, champion portraits, four-part
linkage and personalized Training remain in the restart plan's full roadmap.
