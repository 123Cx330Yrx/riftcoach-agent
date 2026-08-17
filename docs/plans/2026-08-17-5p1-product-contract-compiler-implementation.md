# 5P-1 Product Contract Compiler Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** Compile one strict recent-review product request into the existing selected, content-bound, Manifest-governed `RuntimeRunRequest` without network or Provider I/O.

**Architecture:** Add one small `app.product` boundary. A frozen Pydantic DTO validates and parses the untrusted product fields; a trusted compiler resolves `recent-form-review` from `SkillCatalog`, creates machine-readable selection evidence, validates the real Skill input, generates the run namespace, binds exact Artifact bytes, and derives Runtime policy only from the loaded Manifest plus fixed V1 server policy.

**Tech Stack:** Python 3.11, Pydantic 2, existing Skill Catalog/Execution Boundary/Runtime contracts, pytest.

---

## Scope and invariants

- The client-visible request contains only `riot_id`, `count`, `queue`, and `focus`.
- Riot ID is split on the last `#`; surrounding whitespace is normalized and control characters or bounded-length violations are rejected. These are local transport-safety bounds, not a claim that RiftCoach duplicates every Riot account rule.
- The typed endpoint does not call `DeterministicSkillRouter` and does not manufacture a Chinese keyword utterance.
- `recent-form-review` name/version comes from the current strict Catalog snapshot.
- `run_id`, route evidence, Skill identity, policy, Artifact kinds/versions/digests, and audit description are server-owned.
- Skill budgets and quality policy come from the Manifest; V1 `policy_version`, `event_budget`, and `max_revisions` are fixed server policy.
- The existing `SkillExecutionBoundary` remains the second validation boundary and must reject post-compilation identity or content drift.
- No FastAPI dependency, Prompt Program, Application Service, Riot/Data Dragon request, `.env` read, Provider construction, model call, or held-out execution belongs to 5P-1.

### Task 1: Strict recent-review product request

**Files:**

- Create: `app/product/__init__.py`
- Create: `app/product/recent_review.py`
- Create: `tests/test_recent_review_product_compiler.py`

**Step 1: Write failing request-contract tests**

Cover:

- defaults and frozen/`extra="forbid"` behavior;
- exact `count` range 5-20, `queue` of `420 | None`, and five focus values;
- rejection of client-owned `run_id`, Skill, Provider, policy, path, or digest fields;
- split on the last `#`, normalized display Riot ID, empty component rejection;
- local total/component bounds and control-character rejection;
- strict rejection of coercions such as string counts or boolean counts.

**Step 2: Run the focused test and confirm red**

Run:

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest tests\test_recent_review_product_compiler.py -q
```

Expected: collection fails because `app.product.recent_review` does not exist.

**Step 3: Implement the minimum DTO**

Add a frozen, strict, extra-forbidden `RecentReviewProductRequest` with `game_name` and `tag_line` read-only properties derived from the normalized Riot ID.

**Step 4: Run focused tests**

Expected: request-contract cases pass while compiler cases remain absent.

### Task 2: Trusted typed selection and Manifest-derived policy

**Files:**

- Modify: `app/product/recent_review.py`
- Modify: `tests/test_recent_review_product_compiler.py`

**Step 1: Write failing compiler-unit tests**

Cover:

- exact Catalog-selected name/version and `entrypoint:reviews.recent` evidence;
- no call to `DeterministicSkillRouter`;
- missing `recent-form-review` fails closed;
- unexpected input-model identity fails closed;
- every Manifest budget/quality field maps to `RuntimePolicySnapshot`;
- fixed V1 policy fields cannot be supplied by the product request.

**Step 2: Confirm the new tests fail for missing compiler symbols**

Run the same focused pytest command and preserve the expected failure reason.

**Step 3: Implement minimal trusted compilation helpers**

Add:

- a `ProductRequestCompilationError`;
- one trusted recent Skill selector that reads `SkillCatalog.get()` and builds a selected `RouterDecision` with Catalog version and machine evidence;
- one pure Manifest-to-`RuntimePolicySnapshot` projection using fixed V1 server constants.

Do not import or call the natural-language Router.

**Step 4: Run focused tests**

Expected: selection and policy cases pass.

### Task 3: Complete Runtime request compiler and second-boundary proof

**Files:**

- Modify: `app/product/recent_review.py`
- Modify: `app/product/__init__.py`
- Modify: `tests/test_recent_review_product_compiler.py`

**Step 1: Write failing vertical compiler tests**

Cover:

- injected deterministic run-id factory is called once;
- compiler builds `RecentFormReviewInput`, canonical payload, audit-only `user_utterance`, Artifact binding, policy, and `RuntimeRunRequest`;
- exact Summary/report bytes produce the expected binding;
- compiled request passes the current `SkillExecutionBoundary`;
- tampered payload/digest and post-compile Catalog version drift fail at the existing boundary;
- invalid run-id factory output fails before any Runtime execution;
- the product request dump contains none of the server-owned fields.

**Step 2: Confirm red**

Run the focused file and verify failures identify the missing full compiler.

**Step 3: Implement the minimum compiler**

Add `RecentReviewRuntimeRequestCompiler.compile(...)` with injected `run_id_factory`, deep/canonical Pydantic payload generation, existing `SkillInputArtifactBinding.from_content()`, and existing `RuntimeRunRequest` construction. Export only the product-facing symbols needed by later 5P stages.

**Step 4: Run focused and adjacent tests**

Run:

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest tests\test_recent_review_product_compiler.py tests\test_skill_execution_boundary.py tests\test_agent_runtime.py -q
```

Expected: all pass; no external I/O.

### Task 4: Boundary review and proportional regression

**Files:**

- Modify only if a test exposes a 5P-1 defect.

**Step 1: Review the diff against the 5P-1 exclusions**

Verify there is no FastAPI dependency, Prompt Program code, Provider/Riot construction, file-store write, Router keyword call, or client policy override.

**Step 2: Run contract and cross-layer regression**

Run product/compiler, Skill models/catalog/router/execution, Runtime models/store/runtime, Context/compiler, and Harness composition tests using real discovered filenames.

**Step 3: Run full local gates**

Use the commands from `.github/workflows/tests.yml` and current repository conventions:

- full pytest;
- both RAG evaluation gates;
- `compileall`;
- Harness SDK boundary, tracked secret/run-data boundary, and Harness dry-run;
- project governance and governance tests;
- `git diff --check`.

Expected: all pass with zero Key reads, Riot/Provider calls, and held-out executions.

### Task 5: Persistent state and public evidence

**Files:**

- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md` only if its dynamic status requires reconciliation

**Step 1: Record evidence and limitations**

Mark 5P-1 complete only after all local gates pass. Record exact tests, zero-I/O scope, policy constants, security boundary, and the fact that neither Prompt Program nor API/model quality is implemented.

**Step 2: Set exactly one next checkpoint**

Set canonical next to `5P-2-prompt-program-runtime-composition` and do not implement it in this batch.

**Step 3: Re-run governance and stale-state checks**

Expected: no disagreement among canonical state, active plan, roadmap amendment, capability matrix, and project decisions.

**Step 4: Commit, push, and verify exact-SHA CI**

Commit one reviewable 5P-1 change, push to `origin/main`, and confirm the GitHub Actions run for the exact commit succeeds. If network observation is temporarily unavailable, do not misreport it as test failure and do not create extra code changes.

**Step 5: Stop at 5P-2**

Report the teaching summary, exact evidence, public SHA/CI, current limitations, and the single next checkpoint. Do not install FastAPI or begin Prompt Program implementation.
