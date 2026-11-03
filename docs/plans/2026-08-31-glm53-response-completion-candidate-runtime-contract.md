# GLM-5.3-Flash Candidate Recovery Runtime Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a body-free, offline-verifiable contract for a bounded GLM-5.3-Flash fresh-recovery candidate, including per-provider-attempt accounting, budget reservation/settlement, and a trace projection, without enabling network execution.

**Architecture:** Keep the existing registered strict response policy and provider-neutral `ChatResponse` contract unchanged. Add a separate immutable candidate runtime/attempt contract plus a small in-memory ledger that treats every underlying provider request as one attempt, requires an eligible first decision before a single `fresh_recovery` slot, and emits only sanitized trace records. The candidate remains unregistered and the module exposes no provider or retry call.

**Tech Stack:** Python 3.11 dataclasses and `StrEnum`; existing `ResponseCompletionPolicy`, `ResponseCompletionDecision`, and sanitized boundary snapshots; pytest.

---

### Task 1: Freeze the candidate runtime and attempt contract

**Files:**
- Create: `app/providers/response_recovery_contract.py`
- Test: `tests/test_response_recovery_contract.py`

**Step 1: Write failing tests**

Cover exact Flash identity, candidate-only activation, two-attempt maximum, primary-before-recovery ordering, body-free attempt outcomes, and rejection of raw response/request fields.

**Step 2: Run the focused tests**

Run: `python -m pytest tests/test_response_recovery_contract.py -q`

Expected: FAIL because the contract module does not exist.

**Step 3: Implement the immutable contract**

Add a candidate runtime profile bound to `zhipu/glm-5.3-flash`, profile `glm-5.3-flash-runtime-v2-candidate/2.0.0`, 8192 output tokens, the existing 90/120 second execution/transport ceilings, and explicit `candidate` activation. Add typed attempt kinds (`primary`, `fresh_recovery`), sanitized attempt outcomes, attempt specifications, and a plan builder that can describe an offline candidate plan but never grants registered execution.

**Step 4: Run the focused tests**

Run: `python -m pytest tests/test_response_recovery_contract.py -q`

Expected: PASS.

### Task 2: Implement budget reservation and settlement

**Files:**
- Modify: `app/providers/response_recovery_contract.py`
- Test: `tests/test_response_recovery_contract.py`

**Step 1: Write failing tests**

Prove that reservation counts each underlying call, settlement counts observed input/output/latency, failed calls still consume a slot, a second call requires the exact eligible first outcome, cumulative output/time budgets are enforced, and duplicate/out-of-order settlement fails.

**Step 2: Run the focused tests**

Run: `python -m pytest tests/test_response_recovery_contract.py -q`

Expected: FAIL for the new ledger behavior.

**Step 3: Implement the minimal ledger**

Add an explicit reservation token, a mutable ledger with immutable snapshots, one in-flight reservation, no third attempt, fail-closed terminal state after recovery failure, and no use of SDK/ToolRuntime retry semantics.

**Step 4: Run the focused tests**

Run: `python -m pytest tests/test_response_recovery_contract.py -q`

Expected: PASS.

### Task 3: Add a sanitized recovery Trace projection and package exports

**Files:**
- Modify: `app/providers/response_recovery_contract.py`
- Modify: `app/providers/__init__.py`
- Test: `tests/test_response_recovery_contract.py`

**Step 1: Write failing tests**

Verify contiguous attempt ordinals, exact policy/profile identity, recovery only after primary, aggregate totals matching the ledger, and absence of prompt/content/reasoning/tool-argument/request-ID fields from the trace representation.

**Step 2: Implement the projection**

Add immutable per-attempt and aggregate recovery trace records. Keep them separate from the existing `RuntimeTrace` schema; future runtime wiring must explicitly adopt the new schema rather than silently changing old traces. Export the public contract names from `app.providers`.

**Step 3: Run focused tests and adjacent regressions**

Run: `python -m pytest tests/test_response_recovery_contract.py tests/test_response_completion_policy.py tests/test_glm53_flash_runtime_profile.py -q`

Expected: all tests pass; existing strict policy remains 2048/zero extra calls.

### Task 4: Persist evidence and verify boundaries

**Files:**
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/requirements_change_log.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Create: `docs/adr/0072-adopt-bounded-fresh-recovery-attempt-contract.md`
- Create: `docs/learning/8e-glm53-fresh-recovery-attempt-contract-walkthrough.md`

Record RQ-183 as local candidate-contract completion, retain `8e-productization` as `in_progress`, and state that exact-SHA CI, same-SHA protocol evidence, and separately authorized real diagnostics remain open. Do not mark production recovery, G53-7, 8E, 8F, or `production_media` complete.

Run: `python -m pytest tests/test_response_recovery_contract.py tests/test_response_completion_policy.py tests/test_glm53_flash_runtime_profile.py -q`; `python -m compileall -q app tests`; `git diff --check`; `python scripts/check_project_governance.py`.

No commit, push, server start, provider call, frontend edit, Workbench edit, or cleanup of the pre-existing dirty worktree is part of this plan.

## Completion record (2026-08-31)

Status: `completed-public-evidence`.

The contract and its offline tests are implemented. The implementation commit
A=`e25c3579e8c37724b76505ad028e066a7e28e654` passed exact-SHA public CI in Actions
run `33405110692`; the same A checkout then completed G53-3 with exactly `3/3`
calls (A1 `1/1`, A2 `2/2`, `admitted=true`, SDK retries `0`). The sanitized result
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`
was added only by direct child B=`eca01ce1393286dbbe83992c2985f600ea2b30b0`, whose
Actions run `33405881172` also passed all three jobs. A/B identity preflight passed;
the result's canonical-LF SHA-256 is
`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`.

This is public reproducibility and protocol identity evidence only. The candidate
remains unregistered and `execution_allowed=false`; strict Flash v1 remains
2048/zero extra calls. The next separately authorized substage is one bounded
candidate fresh-recovery diagnostic with cost/latency/failure/Trace review, not
automatic activation, G53-7, or a product-default change.

## RQ-185 diagnostic interruption record (2026-08-31)

The separately authorized diagnostic code is isolated at
`76de589a128b7a71f1def3316da3f30ebdd3a4c8`, against implementation/evidence
baseline `eca01ce1393286dbbe83992c2985f600ea2b30b0`. Two independent starts each
entered only the primary request path, with SDK retries disabled. The first used
the candidate's 120-second transport ceiling and was stopped at the outer
approximately 60-second tool boundary; after renewed user authorization, the
second used a new output name and a temporary 20-second client transport ceiling,
but still did not exit before the same outer boundary.

Neither start produced an observable response, Usage, finish reason, recovery
Trace, or result JSON, and neither opened the `fresh_recovery` slot. Provider
receipt and billing are unknown. The candidate remains unregistered and strict
Flash v1 remains 2048/zero extra calls. A future run requires a newly authorized
transport/proxy boundary review; it must not be treated as an automatic retry,
G53-7 continuation, or product activation.

## RQ-186 request-deadline diagnostic record (2026-09-01)

The review found that the earlier 20-second client default was overridden by the
per-request `ChatRequest.timeout_s=90` passed by `ZhipuProvider`. The isolated
diagnostic now accepts a validated request-level deadline and applies it to both
the primary and any eligible fresh-recovery request. The change is frozen at
`94629161c5d3230629210444b5a1a38212799997`; focused and adjacent tests report
`82 passed`, with compile and diff checks passing.

One new real primary request used `timeout_s=30`, `max_tokens=8192`, and zero SDK
retries. It settled after 30.141 seconds as a transport timeout, with no response,
Usage, finish reason, request ID, or recovery attempt. The sanitized result is
stored at
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_recovery_diagnostic_rq186_request_deadline_v1.json`,
canonical-LF SHA-256
`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`, and local
evidence commit `a7874b0`. Because 30 seconds is below the candidate's 90-second
Agent window, this proves deadline enforcement but does not reject candidate
capability. The candidate remains unregistered; a full-window diagnostic requires
a separate latency-budget decision and authorization.

## RQ-187 full-window diagnostic record (2026-09-01)

After the request-level deadline fix, one authorized run used the candidate's full
`timeout_s=90` window with `max_tokens=8192` and SDK retries disabled. The only
primary settled at 90.188 seconds as a transport timeout; no response, Usage,
finish reason, request ID, or fresh recovery was observed. The sanitized result
has canonical-LF SHA-256
`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263` and is
carried by local evidence commit `50ce5be`.

This rules out the 30-second diagnostic window as the sole cause, but does not
distinguish proxy/read/first-byte delay from server-side generation. The candidate
therefore remains unregistered and the next step is a separately authorized
transport-versus-generation split, not an automatic retry or G53-7 admission.

## RQ-188 transport/generation split diagnostic record (2026-09-01)

The user granted a broader continuation authorization, so the isolated diagnostic ran one fixed three-probe batch with SDK retries disabled. It used a valid Flash `thinking=enabled`/`reasoning_effort=low` minimal control, the frozen context with a 256-token synchronous cap at max effort, and the same frozen context with an 8192-token stream that stopped after the first chunk.

All three probes were observed. The two synchronous responses had valid Usage but ended with `finish_reason=length`, empty visible content, and non-empty reasoning. The stream produced a first `delta_reasoning` chunk in about 687 ms and was then closed intentionally; terminal Usage and completion were not claimed. The formal sanitized result is `zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_final_v1.json`, canonical-LF SHA-256 `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`, with diagnostic/source identity `b67b4500ebdbff934e470fd92c1461184aa7c49b`.

This narrows the evidence to “endpoint/model path reachable and generation started” versus “long synchronous completion observed.” It does not prove a complete provider-neutral stream contract, explain the 90-second baseline, or admit the candidate. Strict Flash v1 remains 2048 output tokens and zero extra calls; the next bounded candidate exercise is output-budget/reasoning-effort calibration.

## RQ-189 output-budget/reasoning-effort calibration record (2026-09-01)

The evaluation-only calibrator held the frozen context, `temperature=1`,
`top_p=0.95`, endpoint, and model constant. Three independent calls used SDK
`max_retries=0`: low effort with 2048 output tokens completed in 28.344 seconds
with visible content and `finish_reason=stop` (1973 input / 724 output tokens),
while low effort with 8192 and max effort with 8192 reached their 45-second
request deadlines without a complete response. The latter calls exposed no
Usage, body, or request ID, so billing remains unknown.

The immutable body-free results are
`zhipu_glm53_flash_output_budget_calibration_rq189_probe1_v1.json`,
`zhipu_glm53_flash_output_budget_calibration_rq189_probe2_v1.json`, and
`zhipu_glm53_flash_output_budget_calibration_rq189_probe3_v1.json`, with
canonical-LF SHA-256 values `1e001b49370f734404bc56896610d73d94057203aebf8de172d54787728e7c32`,
`42339af9af71db3e63f2ba8e8773898a7f6b60cd8e5ceab06269ec6aca37f32`, and
`fc54d9479db60cef585b216d0b11dd36e511180b485ea00c2ebced60d528379f`.
The first result predates the single-probe/atomic-write safety patch and records
diagnostic SHA `b46d5e39e1d44293452b1b893c91feff13f57b02`; the other two record
`21bc38b211e596f933223aa9a871a5b10f62267f`. Their request payload shape and
body-free projection are unchanged, and all source identities remained stable.

This proves only that the frozen case can complete under low/2048 and that the
two 8192 synchronous windows did not finish within 45 seconds. It does not admit
the candidate, change the strict 2048/zero-extra-call profile, or establish
general quality. The next evaluation-only item is a bounded stream-visible-
completion probe that separates first visible content from terminal completion
and records the `clear_thinking` shape without changing product runtime behavior.

## RQ-191 stream-terminal/Usage completion record (2026-09-01)

The dedicated full-stream probe implementation is
`2a01edf58e9f5b11619553a9eeb4448a4cdb87d0`. One raw stream used the current
product-shaped `clear_thinking=false`, low effort, 2048-token cap, and no SDK
retries. It exposed its first chunk at 2203 ms and first visible content at
3531 ms, then completed at 24140 ms with `finish_reason=stop` and valid Usage:
1973 input, 652 output, and 0 cached input tokens across 642 chunks.

The body-free result is
`zhipu_glm53_flash_stream_terminal_completion_rq191_v1.json`, experiment
`dba57e5316058336dbc0e497d01b115e337ce6367acbb967b5e6760e270b3f46`, SHA-256
`a57fec105859241ea71e32eb8073b4c33b934262a7793b6a47a7b6e4efb4b3c9`. This
confirms complete terminal/Usage observation for one frozen context only. It
does not establish general quality, high-budget/long-context latency,
cross-turn thinking semantics, tool streaming, provider-neutral runtime
adoption, candidate activation, or production readiness. The next item is an
offline provider-neutral stream-adapter contract.
