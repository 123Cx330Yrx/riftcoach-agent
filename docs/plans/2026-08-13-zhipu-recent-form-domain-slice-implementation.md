# Zhipu Recent-form Domain Slice Implementation Plan

> **For Codex:** use `executing-plans`; complete the offline batch and stop before real model I/O.

**Goal:** Build a fail-closed runner that composes the real recent-form Skill pipeline under the
remaining four calls of the already approved cumulative seven-call Provider experiment.

**Architecture:** Strictly reload and hash the admitted three-call Adapter result, then place one
observed `ExternalCallBudget(max_calls=4)` around the production Provider used by both AgentLoop
and Harness `llm.chat`. Run anonymous fixtures through existing production boundaries and persist
only a strict sanitized report.

**Tech Stack:** Python 3.11, Pydantic v2, existing Provider/ToolRuntime/AgentLoop/Skill/
ReviewHarness/local RAG, pytest. No dependency or real Provider call in this batch.

---

### Task 1: Freeze cumulative budget and sanitized result contracts

**Files:**

- Create: `app/evaluation/provider_domain_skill.py`
- Create: `tests/test_provider_domain_skill.py`

1. Write red contract tests for total/prior/remaining/cumulative call consistency, phase counts,
   terminal evidence, digests and admission invariants.
2. Write red tests that reject a non-admitted, non-3-call or Provider/model-mismatched protocol
   report before a domain Provider call.
3. Implement strict Pydantic report contracts and protocol-evidence validation.
4. Implement one observed budget wrapper that records only safe response metadata.
5. Require the fifth domain call to fail before delegating to the underlying Provider.

### Task 2: Compose the real recent-form control flow

**Files:**

- Modify: `app/evaluation/provider_domain_skill.py`
- Modify: `tests/test_provider_domain_skill.py`

1. Build the typed execution through real Catalog, deterministic Router and ExecutionBoundary.
2. Build Context, local RAG and one ToolRegistry containing `knowledge.search` plus a single-attempt
   `llm.chat` tool.
3. Use the same observed Provider in `AgentLoop` and `ChatEvaluationAdapter`/
   `ChatCoachReviser` through `SkillReviewExecutor`.
4. Run a Fake Provider happy path: tool request, observation-aware Coach draft, strict Evaluation,
   ReviewHarness publish and typed output in exactly three domain calls.
5. Test no-tool, invalid structured output, one format repair and revision-over-budget failures.

### Task 3: Add an explicit real-call CLI without running it

**Files:**

- Create: `scripts/run_real_provider_skill_slice.py`
- Create: `tests/test_real_provider_skill_slice.py`

1. Require `--confirm-real-call` and exact cumulative `--max-calls 7` before client creation.
2. Restrict protocol input and result output to the public Provider capability result directory.
3. Strictly read and hash `zhipu_adapter_slice.json`; create the SDK client with
   `max_retries=0` only after all local gates pass.
4. Use the existing anonymous fixtures, Skill directory, local RAG and a temporary runs directory.
5. Serialize only `DomainSkillSliceReport`; tests use injected Fake Provider/runner and never use
   the network or local Key.

### Task 4: Offline vertical verification

**Files:**

- Modify tests as needed without weakening production contracts.

1. Run the new focused tests and require the full real-domain Fake Provider path to pass.
2. Run Skill/Agent/Harness/RAG/ToolRuntime/Provider proportional regression.
3. Run full pytest, compileall, RAG development/holdout gates, governance, security scans,
   Harness dry-run and `git diff --check`.
4. Confirm no real result file was created and no external Provider was called.

### Task 5: Persist status, publish offline controller, and stop

**Files:**

- Modify: canonical state and active planning files
- Modify: roadmap history, amendment, capability matrix and project decisions as applicable
- Create: beginner review document after implementation

1. Record only offline domain-controller completion; keep `5D-6b` in progress.
2. Set the sole next action to commit/push/verify exact public CI, then run one bounded real domain
   slice under RQ-027; do not enter 5D-7 or a second Provider.
3. Stage only this batch, run cached checks, commit, push and verify GitHub Actions for exact SHA.
4. Do not run the real domain CLI in the same offline implementation batch.
