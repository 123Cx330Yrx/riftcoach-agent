# Native review into the existing product pipeline

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
