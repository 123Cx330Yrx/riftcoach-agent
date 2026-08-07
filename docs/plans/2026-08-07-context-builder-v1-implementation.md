# 5D-2 Context Builder V1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` to implement this plan task-by-task;
> stop before 5D-3.

**Goal:** Build provider-neutral, trust-typed and budget-bounded initial context for the two real
RiftCoach Skills without compiling or executing an `AgentRunRequest`.

**Architecture:** `ContextBuilderV1` projects allowlisted facts from `ValidatedSkillExecution`
into immutable `ContextSection` values, selects whole required/optional sections using an
injectable `ContextSizer`, and renders one system plus one user `ChatMessage`. The verified
Manifest is the hard context ceiling; tool and loop budgets remain 5D-3.

**Tech Stack:** Python 3.11, dataclasses, enums, protocols, standard-library JSON/regex/math,
existing Provider `ChatMessage`, existing `KnowledgeEvidence`, pytest.

---

### Task 1: Freeze section, trust, bundle, and sizing contracts

**Files:**

- Create: `app/agent/context.py`
- Modify: `app/agent/__init__.py`
- Create: `tests/test_context_builder.py`

**Steps:**

1. Write failing tests for nonblank/unique section identity, trust-derived role and instructional
   status, deterministic size estimates, and immutable `ContextBundle` metadata.
2. Run `tests/test_context_builder.py`; require red because the module/contracts do not exist.
3. Implement only the enums, dataclasses, errors, `ContextSizer` protocol and deterministic sizer.
4. Re-run the contract tests and require green before adding Skill projections.

### Task 2: Build the recent-form minimum context

**Files:**

- Modify: `app/agent/context.py`
- Modify: `tests/test_context_builder.py`

**Steps:**

1. Write failing tests using the real Catalog, Router, execution boundary and demo Summary.
2. Require internal policy/SKILL.md in system sections and player/request/aggregate/boundary/report/
   user request in data-only user sections.
3. Require allowlisted match projections, exclude unknown fields and raw failed-match error text,
   and cap constructed recent match sections at 10.
4. Implement minimal recent projection and stable JSON-envelope rendering.
5. Run Context + existing Skill execution tests.

### Task 3: Build the single-match minimum context

**Files:**

- Modify: `app/agent/context.py`
- Modify: `tests/test_context_builder.py`

**Steps:**

1. Write failing available/unavailable Timeline and short-game tests.
2. Require exactly one target row and forbid `recent_summary` plus every non-target match ID.
3. Include only exact target-ID report lines as optional deterministic-report evidence.
4. Implement the single-match allowlist projection without changing Skill input contracts.
5. Run the Context, single-match contract and execution-boundary tests.

### Task 4: Enforce whole-section budgeting and untrusted evidence semantics

**Files:**

- Modify: `app/agent/context.py`
- Modify: `tests/test_context_builder.py`

**Steps:**

1. Write failing tests for malicious user/fact/RAG strings, duplicate citations, lower runtime
   limits, optional whole-section omission, deterministic order and required overflow.
2. Convert each initial `KnowledgeEvidence` citation into one optional data-only section.
3. Implement required-first selection; add optional sections by priority without partial text.
4. Refuse a limit above Manifest by clamping to the Manifest ceiling; fail closed if required
   messages alone exceed the effective limit.
5. Run all 5D-2 focused tests. Do not create `AgentRunRequest` or call AgentLoop.

### Task 5: Regress, document, publish, and stop before 5D-3

**Files:**

- Modify: `.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify as needed: `docs/project_decisions.md`

**Steps:**

1. Run focused Context/Skill/Provider message tests.
2. Run full pytest, compileall, `git diff --check`, stale-state search and governance precheck.
3. Mark only 5D-2 complete and set the exact next checkpoint to 5D-3.
4. Review and stage only 5D-2 files; run cached diff checks.
5. Commit, push `main`, and verify GitHub Actions for the exact final SHA.
6. Stop without compiling `AgentRunRequest`, invoking ToolRuntime/Provider/AgentLoop, or entering
   5D-3.
