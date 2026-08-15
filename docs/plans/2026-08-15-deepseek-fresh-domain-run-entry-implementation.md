# DeepSeek Fresh-Gate 4 Run Entry Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Bind the Fresh-Gate 3 assets to a no-I/O held-out admission and the existing production CLI without reading a Key or running the real held-out.

**Architecture:** Add a strict Fresh readmission/evidence envelope around the existing domain admission and result rather than copying the coordinator. Rebuild all three Context identities before I/O, preserve the historical protocol/result bytes, and expose a prepare-only CLI branch whose dependency graph cannot reach environment loading or Provider construction.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing Provider budget controller, production domain executor, SHA-256 commitments.

---

## Safety boundary

This plan does not read `.env`, call a Provider, execute the real V2 held-out, tune Prompt/Evaluation/RAG, add another model, or leave 5D-7.

### Task 1: Add Fresh held-out evidence and no-I/O admission contracts

**Files:**

- Modify: `app/evaluation/provider_domain_readmission.py`
- Modify: `app/evaluation/provider_domain_experiment.py`
- Modify: `tests/test_provider_domain_readmission.py`

**Steps:**

1. Write failing tests for exact asset-freeze evidence, held-out lifecycle, Context drift, current CI drift, no Provider/Key parameters, and historical compatibility.
2. Run the focused tests and confirm they fail for missing contracts.
3. Implement a strict asset-freeze model, Fresh held-out admission, fresh preparation builder, and a narrow fresh variant of the existing base admission.
4. Keep old protocol/result loading and old preparation behavior unchanged.
5. Run the focused tests to green.

### Task 2: Add an immutable Fresh result envelope

**Files:**

- Modify: `app/evaluation/provider_domain_readmission.py`
- Modify: `app/evaluation/provider_domain_experiment.py`
- Modify: `tests/test_provider_domain_readmission.py`
- Modify: `tests/test_provider_domain_experiment.py`

**Steps:**

1. Write failing tests that require the new envelope to contain the complete admission chain and matching base result.
2. Add a backward-compatible generic commit method to the existing exclusive output reservation.
3. Reject mismatched experiment/result identities and extra raw/secret fields.
4. Prove both the old V1 result and new envelope serialize without changing historical files.

### Task 3: Connect the current production CLI to the Fresh profile

**Files:**

- Modify: `scripts/run_deepseek_domain_heldout.py`
- Modify: `scripts/prepare_second_provider_experiment.py`
- Modify: `tests/test_run_deepseek_domain_heldout_cli.py`

**Steps:**

1. Point the active CLI profile at the V2 Dataset/plan/snapshot/output plus the immutable old protocol/rejection evidence.
2. Add a prepare-only branch and inject only a clean-SHA reader for tests; do not add a Provider to the admission API.
3. Preserve order: output conflict, no-I/O admission, output reservation, environment, Provider, bounded run.
4. Use Fake Provider only in temporary directories to prove the existing production Executor/RAG/Evaluation/Harness path and new result envelope.
5. Assert protected markers, Key, request IDs, exception text, Prompt and fixture bodies are absent from public output.

### Task 4: Proportional and complete offline verification

Run focused tests, the full pytest suite, both RAG gates, compileall, Harness SDK/tracked-data checks, Harness dry-run, governance and `git diff --check`. All external Provider call and real held-out counters remain zero.

### Task 5: Persist and publicly verify

Update canonical state, active plan/findings/progress, roadmap history/amendment, capability matrix and project decisions with only observed evidence. Commit/push the implementation, verify exact-SHA GitHub Actions, then make and verify a state-only follow-up commit. The unique next action remains a separate real-call confirmation; do not load the Key in this plan.

## Execution result

- Status: complete
- Implementation SHA: `ed3cc947bfdcf2eed22d57864ff852c5107f601a`
- GitHub Actions: `31863341338` completed/success
- Adjacent regression: `93 passed`
- Full regression: `580 passed, 103 subtests passed`
- RAG development/held-out gates: passed at frozen 1.0 thresholds
- Same-SHA prepare-only: no-I/O admitted, external Provider calls `0`, held-out executed `false`
- Real V2 result created: `true`
- Real execution: one domain call, 3440 observed tokens, about `$0.00506616`;
  the second call was blocked before I/O by the frozen 4000-token per-case
  budget, so the first case degraded and the remaining cases were skipped
- Result SHA-256:
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`
- Admission: `false`; no automatic rerun is allowed
- Next gate: no-I/O V2 result adjudication and realistic budget-reachability
  TDD inside 5D-7
