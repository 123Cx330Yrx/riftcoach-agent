# ADR0108: Proposed isolated reviewer capability comparison

2026-09-22. **User approved the isolated two-call diagnostic with “允许”.**
Approval covers implementation and the two bounded GLM-5.3/high requests only.
No product model change or product candidate admission is adopted here.
The current model remains GLM-5.3-flash/high. This is unrelated to Codex Luna.

## Actual result: batch stopped after one response

Implementation15c8940 initially failed public CI due to native source-manifest
drift. Fixed in b6b30f8; exact-HEAD CI35747690218 passed all three jobs before
the sole paid request. The run completed in56.406seconds, first tool output at
48.828seconds, terminal at55.937seconds; no output cap, timeout or transport failure.

GLM-5.3/high returned82/needs_revision with one block14 issue and one block4
advisory. Its issue correctly distinguishes CS composition effects from the
damage difference already present within mid: whole damage gap695.4183,
mid669.235, change26.1833. Its optional early-death clarification correctly
recognizes that later full context supplies the whole-sample denominator and
does not turn that wording into a blocker. These are positive textual observations
from **one** response, not a passed full review or stable model-quality evidence.

Strict validation rejected `semantic_source_id_unknown`: **both findings cite
source0, which does not exist** in the declared1–31 source catalog. Block14's
entire sequence `[9,13,17,8,12,16,0]` corresponds to zero-based positions in the
parallel bare `source_index.evidence_keys` array: damage loss/win/support,
CS loss/win/support, aggregate. Under the declared IDs they point instead to
CS/scope/vision or nothing. This supports investigating competing source
coordinates. It is not proof of a universal off-by-one fix: the advisory's
references still do not support its early-death figures after adding one.
No ID shifting, dropped0 or corrected response was accepted or sent onward.

The first rejected result terminated the batch; corrected-control call2 was not
issued. No host acceptance, editing, final review or product replacement occurred.
Actual input12149+output3480=15629tokens; unknown0. At listed uncached prices,
estimated cost0.194632CNY; account bill not independently verified.

Evidence: `data/evaluation/results/golden_review_model_comparison_result_b6b30f8.json`
contains all8 original JSON artifacts/hashes, exact unchanged request identity,
response, rejected accounting, per-source resolution and independent Decimal
arithmetic from original game rows. Raw run remains untouched. The execute gate
is now closed before input/CI/credentials access; the unused second call is not
permission for a retry with changed inputs.

**Decision:** full-model substitution alone has not delivered an adoptable review.
Its true-error detection changes the diagnosis: investigate source addressing
explicitly rather than assuming another semantic-policy rewrite is necessary.
Next authorized independent work is an offline source-contract comparison:
inspect producers/consumers of both coordinate systems; determine whether one
explicit ID can address all original evidence, report blocks and recovery mappings
without losing data or changing raw identities. Use this response plus legacy
wrong-source/unknown/duplicate cases. Do not start another model/prompt/schema
batch or relabel original evidence as passing. Further paid experiments or product
role adoption need a concrete decision beyond this stopped two-call authorization.

## Problem and discriminating question

The four-cell input-layout experiment returned complete valid tool responses,
yet baseline missed the genuine damage attribution error, target-last rejected
correct contextual wording, and another advisory inverted the economic ratio.
No call hit the output/time cap. Sources and the per-metric rule were already
present. Protocol repair and additional copies of that rule do not address the
observed semantic failures. See the actual results and adjudications in
`data/evaluation/results/golden_review_target_layout_result_1d5f7a2.json`.

Can a different supported model, given the **same full review request**, both
detect the original error and accept the corrected report without introducing
false findings or false advice? This is an unproven capability hypothesis. Price,
model naming and vendor benchmarks do not establish superiority on this task.

## Options and current choice

| Option | Evidence / cost | Disposition |
|---|---|---|
| More Flash prompt, layout or output-format variants | Several complete responses still fail semantically; no new discriminating hypothesis | Do not continue this series |
| Add a reviewer call or split every review into several model calls | Normal two generation rounds + review + edit + final review already use five calls | Requires a different task allocation or budget decision; no hidden extra allowance |
| Reuse locator-only editor or two-state final review | Locator arm once succeeded but lost distinct accusations in one paragraph; two-state final review still falsely rejected correct text | Not an untried sufficient fix; do not rerun unchanged |
| Deterministic arithmetic alone | Arithmetic is already correct and in the input; semantic scope and unsupported attribution remain | Retain fact checks; they cannot replace contextual review |
| GLM-5.3-FlashX | Official positioning emphasizes faster inference; no evidence of higher accuracy here | Not selected for this semantic comparison |
| GLM-5.3/high, same API/request | Officially supported; ten times the listed Flash input/output unit prices, quality unproven | Recommend the two-call diagnostic below, subject to the user's model decision |
| Change the generator or entire product model now | Does not first answer why review fails; unnecessarily changes more variables | Not proposed |

The proposed diagnostic is not an adoption decision. Do not implement a large
mixed-model runtime before obtaining capability evidence.

## Concrete prepared comparison

`scripts/prepare_review_model_comparison.py` reconstructs the two baseline
requests from the frozen attribution dataset and checks them against the prior
layout plan. It captures the existing Provider's SDK arguments, then uses the
installed OpenAI SDK with an in-memory HTTP transport for baseline/proposed
bodies. **Only `model` differs.** Full text, source values, message ordering,
tools/schema, `high`, retained-thinking setting, stream/tool stream, usage tail,
temperature, top-p, 32768 output cap and 300-second timeout are preserved.
Host labels never enter either request. No credentials or local run files are
read; no paid API availability or response quality is claimed by this check.

The reproducible plan, body/request hashes, input reservations and cost are in
`data/evaluation/results/golden_review_model_comparison_feasibility_v1.json`.
Run `python -m scripts.prepare_review_model_comparison` to reconstruct it.
That preparation script has **no execute flag**. The approved live runner is
`python -m scripts.run_review_model_comparison --execute --ci-run <exact-head-run>
--env-file <authorized-local-env>`. It reserves one create-only run directory,
uses one two-call/154202-token/600-second ledger, and requires host adjudication
of the full first response before the second call. The host's response-file hash
binds that decision. Waiting for host review consumes the same elapsed budget.
Only the diagnostic transport/profile/policy accepts GLM-5.3/high; product
composition and its Flash-only contract are unchanged. A first failure stops.

| Bound | Proposed diagnostic |
|---|---|
| Order | Original wrong full report, then original corrected full report |
| Model | GLM-5.3/high; no low/default substitution |
| Calls / deadline | At most two calls; 300 seconds each, 600 seconds for batch |
| Token reservation | Input 88666 + output 65536 = 154202 total |
| Cost estimate | Uncached input 8 CNY/million + output 28 CNY/million → 2.544336 CNY at reservation |
| Other calls | No warm-up, retry, reassessment, editing or extra baseline calls |

The input bound is the existing conservative local sizer, not a vendor tokenizer
proof. The estimate is not an account-enforced billing cap; actual usage, cache
and billing follow the provider. Missing usage stays unknown and no retry follows.
Historical Flash results are a reference, not a contemporaneous paired performance
estimate. Two alternative responses cannot establish stability or causal superiority.

For each response inspect **all** issues and advisories against original complete
context and arithmetic. A correct verdict with false advice is not sufficient.
Do not ask the model to check only block14 or provide expected labels.

- First protocol/execution or semantic failure: stop remaining calls, preserve
  response/transport, precise failure and known/unknown usage; no automatic retry.
- Both full responses correct: enough to justify considering reviewer-role
  integration, not qualification or default replacement. One role configuration
  must then pass actual revision/final review and all original15 coverage cases;
  old successes do not transfer across model/configuration versions.
- Valid but semantically wrong: reject this model-only substitution as a
  sufficient solution for the controls. Do not cycle another prompt/serialization
  tweak under this plan. Reconsider task allocation using the new error evidence.
- Protocol failure: capability remains unknown, distinct from semantic failure.
  A further run requires a distinct, evidenced repair decision, not a batch reset.

## API feasibility and runtime gap

Official model docs list GLM-5.3: text, 1M context, 128K maximum output,
thinking enabled with low/high/max; same standard Chat Completions endpoint.
API docs explicitly list tool streaming for GLM-5.3 and only `auto` tool choice.
No reliance on strict JSON Schema, required tool choice or a new SDK dependency.
The account's access and live latency are unverified. Existing model resolver
chooses **low** for full GLM-5.3: a diagnostic must use an explicit high profile,
not silently inherit this default.

The real product is **not** a drop-in model-name switch:

The approved diagnostic now implements the profile, policy and transport rows
below. Product role dispatch, product qualification and its shared ledger remain
unimplemented decisions; the diagnostic runner has its own single two-call
ledger, not a second product budget. Relevant130 offline checks passed before CI.
CI then exposed18 product composition failures: the native program hashes both
shared transport source files. Its active manifest now records their actual new
hashes and its derived program digest; the strict drift check and all historical
qualification artifacts remain intact. All66 affected product/diagnostic checks
then passed locally. This source-identity update grants no model qualification.

| Existing seam | Required scope if a later decision permits implementation |
|---|---|
| `zhipu_profiles.py`, request policies | Isolated explicit model/high identity; default Flash selection stays unchanged |
| `golden_stream_bridge.py` | Worker settings, stream assembler and response checks bind Flash; parameterize only the approved diagnostic identity, preserving process deadline and raw records |
| `coach_contract.py` / `coach_budget.py` | Product currently binds one exact Provider. A future role plan needs explicit role→Provider validation under **one** calls/tokens/time ledger |
| `native_coach_composition.py` / `review_sender.py` | Currently reuse one provider and old review workflow; later reviewer dispatch must retain exact exchange identity and shared budget |
| Qualification / product entry | Actual product entry remains closed; future admission must bind the chosen model-role configuration, new workflow and transport, replacing old hardcoded evidence |

If reviewer capability passes and the user approves a role change, the bounded
candidate design is Flash generation/tool rounds and Flash edit, GLM-5.3 initial
and final review. Calls remain 2 + 1 + 1 + 1 = 5 under one 401920-token /900-second
ledger with one revision. A recovery may make the task unable to finish; it must
reject rather than allocate a second reviewer budget. Every request and receipt
keeps its actual model/role identity. This is an **unselected design**, not code
already integrated or a product-quality claim.

## Official sources and verification boundary

Fetched read-only 2026-09-22; URLs and SHA256s are recorded in
`data/evaluation/results/golden_review_model_comparison_sources_v1.json`.
Local snapshots reside in the workspace output folder named in that manifest.

- [GLM-5.3](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3.md)
- [Chat Completions](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8.md)
- [Function Calling](https://docs.bigmodel.cn/cn/guide/capabilities/function-calling.md)
- [Thinking](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode.md)
- [Pricing](https://docs.bigmodel.cn/cn/guide/start/pricing.md)
- [Flash / FlashX](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash.md)

Use the pricing table rather than assuming a promotional discount advertised on
another page. Model guides and mock serialization are necessary feasibility
evidence, not proof the API/account will accept this exact live request.

The user has authorized this isolated paid alternative-model diagnostic;
ordinary implementation and exact-HEAD CI precede its requests. No further
permission is needed for these two calls. It does not authorize product replacement
or a budget increase.
This boundary follows the user's explicit Flash product selection and the
current exact-model contract; it is not an approval rule invented by a Skill.
All other Agent/Training/four-panel/frontend/identity/integration/holdout work
remains tracked by the existing plan and restart dependencies; 8E is not complete.
