# 5D-5 Harness Composition & Typed Terminal Output Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` to implement this plan task-by-task;
> stop before 5D-6a.

**Goal:** Route both legacy sequential generation and validated Skill Agent drafts through the one
ReviewHarness, then construct validated terminal Skill Outputs only from the terminal manifest and
integrity-checked artifacts.

**Architecture:** Introduce a provider-neutral `DraftPreparationStep` consumed by ReviewHarness and
adapt the old Retriever/Generator pair into it. Add a thin SkillReviewExecutor that binds one
validated execution/context to the Agent preparer and a terminal-output builder that re-reads the
persisted run. Keep AgentRunResult outside Harness.

**Tech Stack:** Python 3.11, dataclasses, Protocols, existing Pydantic Skill models, AgentLoop,
FileRunStore, pytest. No new dependency and no real Provider.

---

### Task 1: Freeze the unified draft-preparation contract

**Files:**

- Modify: `app/harness/steps.py`
- Modify: `app/harness/adapters.py`
- Modify: `app/harness/__init__.py`
- Modify: `tests/test_harness_steps.py`
- Modify: `tests/test_provider_tool_harness_integration.py`

**Steps:**

1. Add failing tests for `DraftPreparationRequest`, immutable
   `DraftPreparationResult`, runtime-checkable `DraftPreparationStep`, and a sequential legacy
   adapter.
2. Run focused tests and require red because the contract/adapter do not exist.
3. Implement the minimal contract and `SequentialDraftPreparer` using the existing Retriever and
   Generator contracts.
4. Verify invalid step results fail closed and Provider/Tool adapters still use neutral contracts.
5. Re-run focused tests to green.

### Task 2: Make ReviewHarness depend on one preparation step

**Files:**

- Modify: `app/harness/runtime.py`
- Modify: `tests/test_harness_runtime.py`
- Modify: `scripts/run_review_harness.py`

**Steps:**

1. Update Harness tests to construct a `SequentialDraftPreparer` and add a red test that a malformed
   preparation result degrades rather than reaching the evaluator.
2. Change `ReviewHarness` to accept only `draft_preparer`, call it once after input artifacts, write
   its evidence, validate draft citations, and continue through the existing evaluation loop.
3. Preserve one `run()` implementation and all terminal state transitions; do not add
   `run_prepared()`.
4. Update the CLI to adapt its existing retriever/generator pair explicitly.
5. Run full Harness runtime and dry-run compatibility tests.

### Task 3: Build terminal outputs from persisted truth

**Files:**

- Create: `app/skills/review_executor.py`
- Modify: `app/skills/__init__.py`
- Create: `tests/test_skill_review_executor.py`

**Steps:**

1. Write failing tests for terminal manifest validation, input binding SHA/schema checks, final
   report reading, final-attempt score selection, persisted evidence IDs, stable warnings, rejected
   report suppression and Output Model validation.
2. Implement `SkillTerminalOutputBuilder` using only `FileRunStore.read_manifest()` and
   `read_artifact()` plus the validated execution.
3. Require exactly one input/final/evidence artifact where applicable and select evaluation by the
   final attempt path.
4. Call `LoadedSkill.output_model.model_validate()` last and wrap validation/integrity failures in a
   safe composition error.
5. Re-run focused tests to green.

### Task 4: Compose the validated Skill Agent through Harness

**Files:**

- Modify: `app/skills/review_executor.py`
- Modify: `tests/test_skill_review_executor.py`

**Steps:**

1. Add failing tests for execution/context identity drift, Manifest quality-gate mapping, Agent
   preparation failure, evaluator failure, rejected fallback policy and revised publication.
2. Implement `SkillReviewExecutor` and a one-run Agent preparation Adapter. Retain the exact
   AgentRunResult outside Harness and expose no draft on failure.
3. Derive threshold/fallback only from Manifest; retain existing max-revision default and reject a
   disabled quality gate in this quality-gated executor.
4. Assert revised Output comes from FINAL_REPORT and final evaluation Artifact, not Agent memory.
5. Re-run focused composition tests to green.

### Task 5: Prove both real Skills end to end without a real Provider

**Files:**

- Modify: `tests/test_skill_review_executor.py`
- Modify as needed: `tests/test_agent_draft_preparer.py`

**Steps:**

1. Build both Skill requests through the real Catalog, deterministic Router,
   SkillExecutionBoundary and ContextBuilder.
2. Use a Fake Provider with the real local `knowledge.search`, ToolRuntime, AgentLoop and
   SkillAgentDraftPreparer.
3. Pass the resulting Agent path through ReviewHarness with deterministic fake Evaluator/Reviser.
4. Assert typed recent-form/single-match outputs, run/Skill/version/target identity, persisted input
   commitments, final report, final score and evidence source IDs.
5. Confirm the Agent draft is evaluated before publication and no real Provider is invoked.

### Task 6: Verify, teach, publish and stop before 5D-6a

**Files:**

- Modify: `.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify as needed: `docs/project_decisions.md`

**Steps:**

1. Run focused Harness/Skill/Agent/RAG/ToolRuntime tests.
2. Run full pytest, compileall, `git diff --check`, stale-state scan and governance precheck.
3. Mark only 5D-5 complete and set exact next checkpoint to 5D-6a.
4. Review and stage only 5D-5 files; run cached diff checks and the real workflow gates locally.
5. Commit, push `main`, and verify GitHub Actions for the exact final SHA.
6. Explain composition, artifact truth, failure paths, test evidence and interview wording to the
   user; stop without implementing structured Provider output or entering 5D-6a.
