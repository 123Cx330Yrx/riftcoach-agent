# 5D-4 Evidence-Aware Agent Draft Preparation Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` to implement this plan task-by-task;
> stop before 5D-5.

**Goal:** Run a compiled Skill request through the bounded AgentLoop and return a CoachDraft plus
KnowledgeEvidence derived only from actual knowledge tool executions.

**Architecture:** Extract one fail-closed knowledge-payload converter shared by the legacy
LocalRagAdapter and the new Agent path. Add a thin SkillAgentDraftPreparer that compiles the
validated execution/context, runs AgentLoop, validates terminal state, and converts real tool
records without composing ReviewHarness.

**Tech Stack:** Python 3.11, dataclasses, existing Pydantic Skill contracts, AgentRunCompiler,
AgentLoop, ToolRuntime, local hybrid RAG, pytest. No new dependency or real Provider.

---

### Task 1: Extract one shared knowledge evidence converter

**Files:**

- Create: `app/harness/knowledge.py`
- Modify: `app/harness/adapters.py`
- Modify: `app/harness/__init__.py`
- Create: `tests/test_knowledge_evidence_builder.py`
- Modify: `tests/test_harness_adapters.py`

**Steps:**

1. Write failing tests for one payload, multiple payloads, identical chunk deduplication, stable
   K1..Kn/source order, abstention, count mismatch and conflicting duplicate chunk IDs.
2. Run the focused tests and require red because the shared converter does not exist.
3. Implement `KnowledgeEvidenceBuildError` and
   `knowledge_evidence_from_search_payloads()` as a pure fail-closed converter.
4. Make `LocalRagAdapter` call the shared converter for its one real payload and remove duplicate
   formatting/mapping code.
5. Re-run converter and Harness Adapter tests and require green with unchanged legacy behavior.

### Task 2: Freeze Agent draft preparation result and terminal validation

**Files:**

- Create: `app/agent/draft.py`
- Modify: `app/agent/__init__.py`
- Create: `tests/test_agent_draft_preparer.py`

**Steps:**

1. Write failing contract tests for `AgentDraftPreparationResult` and a direct final response with
   no tools producing `CoachDraft + KnowledgeEvidence.empty()`.
2. Write failing tests for stopped/failed runs, absent final text, failed knowledge tool results and
   unsupported non-knowledge tool executions.
3. Run the focused tests and require red because the draft module does not exist.
4. Implement `AgentDraftPreparationError`, immutable result contract and
   `SkillAgentDraftPreparer`; it creates its Compiler from the AgentLoop's exact ToolRegistry.
5. Re-run focused Agent tests and preserve all existing Loop/compiler behavior.

### Task 3: Prove both real Skills with Fake Provider and real knowledge.search

**Files:**

- Modify: `tests/test_agent_draft_preparer.py`

**Steps:**

1. Build recent-form and single-match executions through the real Catalog, deterministic Router,
   SkillExecutionBoundary and ContextBuilder.
2. Use a scripted Fake Provider that requests `knowledge.search`, consumes the real Tool
   Observation and returns a Markdown draft.
3. Use the real LocalHybridKnowledgeProvider, knowledge ToolDefinition and ToolRuntime.
4. Assert final draft, actual ToolExecutionRecord, stable citations/source IDs and run/Skill
   metadata for both Skill identities.
5. Assert a source name invented only in model text never appears in KnowledgeEvidence.

### Task 4: Verify failure and provenance boundaries

**Files:**

- Modify: `tests/test_agent_draft_preparer.py`
- Modify as needed: `tests/test_knowledge_evidence_builder.py`

**Steps:**

1. Test two distinct searches with overlapping chunks; evidence keeps first-seen unique chunks.
2. Test ToolRuntime schema/output failure and ensure no draft preparation result is returned.
3. Test budget/duplicate/timeout stop reasons are surfaced only as safe preparation errors.
4. Confirm no Harness run, Artifact, Skill Output or real Provider is created.
5. Run Agent, Compiler, Context, ToolRuntime, RAG and Harness Adapter regression tests.

### Task 5: Verify, teach, publish and stop before 5D-5

**Files:**

- Modify: `.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify as needed: `docs/project_decisions.md`

**Steps:**

1. Run focused Agent/evidence/RAG/Harness Adapter tests.
2. Run full pytest, compileall, `git diff --check`, stale-state search and governance precheck.
3. Mark only 5D-4 complete and set the exact next checkpoint to 5D-5.
4. Review and stage only 5D-4 files; run cached diff checks.
5. Commit, push `main`, and verify GitHub Actions for the exact final SHA.
6. Stop without composing ReviewHarness, producing terminal Skill Output, calling a real Provider,
   implementing structured output, or entering 5D-5.
