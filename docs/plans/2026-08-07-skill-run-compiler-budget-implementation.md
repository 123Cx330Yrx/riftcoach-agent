# 5D-3 Skill Run Compiler & Budget Enforcement Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` to implement this plan task-by-task;
> stop before 5D-4.

**Goal:** Compile validated Skill/context contracts into a least-privilege `AgentRunRequest` and
enforce cumulative context plus cooperative timeout budgets without running the 5D-4 draft path.

**Architecture:** A thin `AgentRunCompiler` validates execution/context identity, canonical context
rendering, registered tools and Manifest ceilings, then maps the existing Manifest into the existing
request contract. `AgentLoop` retains orchestration but checks a complete-message `ContextSizer`
before every Provider call and applies one decreasing run deadline to Provider and ToolRuntime.

**Tech Stack:** Python 3.11, dataclasses, protocols, standard-library JSON/time, existing Skill,
Context, Provider, ToolRegistry/ToolRuntime and AgentLoop contracts, pytest.

---

### Task 1: Freeze Context integrity and request-budget contracts

**Files:**

- Modify: `app/agent/context.py`
- Modify: `app/agent/loop.py`
- Modify: `tests/test_context_builder.py`
- Modify: `tests/test_agent_loop.py`

**Steps:**

1. Add failing tests that `ContextBundle.messages` must be the canonical rendering of its sections.
2. Add failing tests for positive `AgentRunRequest.max_context_tokens` and the two new stop reasons.
3. Run the focused tests and require red for the missing contracts.
4. Add the minimum validations/default that preserve existing direct AgentLoop callers.
5. Re-run the focused tests and require green.

### Task 2: Compile verified Manifest permissions and budgets

**Files:**

- Create: `app/agent/compiler.py`
- Modify: `app/agent/__init__.py`
- Create: `tests/test_agent_run_compiler.py`

**Steps:**

1. Build both real `ValidatedSkillExecution` and `ContextBundle` fixtures through the real
   Catalog, Router, execution boundary and ContextBuilder.
2. Write failing tests for exact messages/tool order/iteration/tool/timeout/context mapping and
   safe metadata.
3. Write failing tests for run/name/version drift, raised Context ceiling, actual message overflow
   and missing registered tools.
4. Implement `AgentRunCompileError` and `AgentRunCompiler` without accepting caller overrides.
5. Run compiler, Context, Skill execution and ToolRegistry tests.

### Task 3: Size complete cumulative messages

**Files:**

- Modify: `app/agent/context.py`
- Modify: `tests/test_context_builder.py`

**Steps:**

1. Write a failing test where long ToolCall arguments produce a larger estimate than short ones.
2. Serialize role/content/tool-call/tool-result metadata deterministically before estimation.
3. Keep the sizer tokenizer-free and deterministic; do not add a Provider SDK/tokenizer.
4. Run Context and Provider message-contract tests.

### Task 4: Enforce context and cooperative timeout in AgentLoop

**Files:**

- Modify: `app/agent/loop.py`
- Modify: `app/tools/runtime.py`
- Modify: `tests/test_agent_loop.py`
- Modify: `tests/test_tool_runtime.py`

**Steps:**

1. Write failing fake-sizer tests for initial overflow and post-Tool-Observation overflow; assert
   no prohibited Provider call occurs.
2. Write failing FakeClock tests for decreasing Provider timeout, no Tool execution after deadline,
   and `TIMEOUT` terminal state.
3. Add an optional ToolRuntime timeout cap test and preserve the definition policy as the other
   ceiling.
4. Implement pre-call context checks, cooperative run deadline and ToolRuntime cap.
5. Run AgentLoop, ToolRuntime and real knowledge-tool integration regression tests. Do not create
   a draft preparer or call a real Provider.

### Task 5: Verify, teach, publish and stop before 5D-4

**Files:**

- Modify: `.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify as needed: `docs/project_decisions.md`

**Steps:**

1. Run focused Compiler/Context/AgentLoop/ToolRuntime/Skill tests.
2. Run full pytest, compileall, `git diff --check`, stale-state search and governance precheck.
3. Mark only 5D-3 complete and set the exact next checkpoint to 5D-4.
4. Review and stage only 5D-3 files; run cached diff checks.
5. Commit, push `main`, and verify GitHub Actions for the exact final SHA.
6. Stop without implementing Agent draft/evidence conversion, calling a real Provider, composing
   Harness, or entering 5D-4.
