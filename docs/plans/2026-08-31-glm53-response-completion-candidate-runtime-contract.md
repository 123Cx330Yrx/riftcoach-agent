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

Status: `completed-local`.

The contract and its offline tests are implemented. Focused and adjacent verification
passed; the candidate remains unregistered and no provider call was made. The next
authorized substage is exact-SHA public CI plus same-SHA G53-3 evidence, not runtime
activation or a real recovery request.
