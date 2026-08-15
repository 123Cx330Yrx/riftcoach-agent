# DeepSeek Fresh Domain Gate Offline Implementation Plan

> **For Codex:** REQUIRED SKILL: Use `executing-plans` to implement this plan task by task with TDD checkpoints.

**Goal:** Implement Fresh-Gate 1 as a no-I/O, backward-compatible control-plane contract that preserves the old DeepSeek evidence, binds every synthetic development case to its actual Prompt/Context identity, and rejects any drift before Provider construction.

**Architecture:** Keep the existing Dataset, Provider, Agent, RAG, Evaluator, and ReviewHarness contracts unchanged. Version the input-plan and Prompt/Context identity models compatibly, then add a narrow readmission module that composes historical file-byte evidence, the public multi-ToolCall repair identity, current code/CI identity, and the new development asset commitments. The resulting development admission explicitly cannot authorize Provider construction.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing RiftCoach Skill/Context/Evaluation contracts, SHA-256 file and canonical JSON commitments.

---

## Scope and safety boundary

This plan implements only Fresh-Gate 1 with synthetic development data.

It will not:

- create `domain_e2e_v2_secure_held_out_cases.json` or any formal held-out;
- read `.env` or an API key;
- construct or call DeepSeek, GLM, or another Provider;
- modify Coach Prompt, Evaluation 1.1, RAG, Harness, or model defaults;
- implement true tool concurrency, 5E Trace, Pi/Claude Agent SDK, or Multi-Agent;
- rewrite or overwrite either historical DeepSeek result file.

## Task 1: Version the input-plan contract without breaking V1.0

**Files:**

- Modify: `app/evaluation/provider_domain_plan.py`
- Modify: `tests/test_provider_domain_input_plan.py`

**Red tests:**

1. Parse the committed V1.0 plan and assert byte-derived identity is unchanged.
2. Build a synthetic V1.1 plan with a snapshot ID/SHA and one ordered Context commitment per case.
3. Reject missing, duplicate, reordered, or mismatched case commitments.

**Implementation:**

- Add a strict `DomainCaseContextCommitment` model.
- Allow `schema_version` 1.0 and 1.1 in the existing artifact.
- Require new fields only for 1.1 and forbid them for 1.0.
- Keep `load_domain_case_input_plan()` compatible with the committed old plan.

**Verify:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_domain_input_plan.py -q
```

## Task 2: Build a real per-case Prompt/Context snapshot

**Files:**

- Modify: `app/evaluation/prompt_context_identity.py`
- Modify: `tests/test_prompt_context_identity.py`

**Red tests:**

1. Preserve exact V1.0 snapshot reproduction.
2. Build a V1.1 snapshot from three synthetic `DomainCaseInput` rows.
3. Assert case order, per-case utterance/options/context hashes, and snapshot self-digest are stable.
4. Assert one utterance/focus/section change alters only the expected case commitment and the aggregate snapshot identity.
5. Assert no Prompt, fixture body, injected text, or user text is persisted.

**Implementation:**

- Extract the existing single-case Context construction into a reusable private helper.
- Add `build_prompt_context_snapshot_for_cases()` for explicit case inputs.
- Add a public canonical `case_context_sha256()` helper for plan/admission comparison.
- Preserve `build_prompt_context_snapshot()` output byte-for-byte for schema 1.0.

**Verify:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prompt_context_identity.py -q
```

## Task 3: Add the historical evidence chain and no-I/O development admission

**Files:**

- Create: `app/evaluation/provider_domain_readmission.py`
- Create: `tests/test_provider_domain_readmission.py`

**Red tests:**

1. Strictly reread the old admitted protocol record and old rejected domain record from their exact bytes.
2. Preserve `3 protocol + 1 failed domain` historical calls while keeping failed-domain tokens/cost explicitly unknown.
3. Bind repair commit `037a47f...` and Actions run `31817798170` as the accepted historical fix evidence.
4. Admit only a development Dataset plus a V1.1 plan and V1.1 three-case Context snapshot whose case order and digests all agree.
5. Reject protocol bytes, rejected-result bytes, repair CI, current code/public-CI, Dataset, fixture, plan, Skill/Evaluation, or case Context drift before any Provider object exists.
6. Forbid extra raw Prompt, model output, request ID, API key, exception, or injected body fields.

**Implementation:**

- Add strict historical protocol/rejection/repair evidence models.
- Add a `FreshDomainDevelopmentAdmission` with `external_provider_calls=0`, `held_out_executed=false`, and `provider_construction_authorized=false` literals.
- Add `load_historical_domain_evidence()` and `prepare_fresh_domain_development_admission()`; neither function accepts a Provider.
- Compute one deterministic experiment identity over all admitted commitments.
- Do not add a real-run entry point in this batch.

**Verify:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_domain_readmission.py -q
```

## Task 4: Proportional regression and security checks

**Files:**

- Test only unless a regression reveals a scoped defect.

**Verify:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_domain_input_plan.py tests/test_prompt_context_identity.py tests/test_provider_domain_experiment.py tests/test_provider_domain_production.py tests/test_provider_domain_readmission.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_rag_retrieval.py --provider hybrid --output "$env:TEMP/riftcoach-rag-v1.json" --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0
.\.venv\Scripts\python.exe scripts/evaluate_rag_retrieval.py --provider hybrid --cases data/evaluation/rag_v1_holdout_cases.json --require-independent --output "$env:TEMP/riftcoach-rag-v1-holdout.json" --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0 --min-abstention-accuracy 1.0 --min-citation-support 1.0
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
rg -n "chat\.completions|\.choices" app/harness/adapters.py scripts/run_review_harness.py scripts/generate_llm_coach_report.py scripts/evaluate_coach_report.py scripts/revise_coach_report.py
git ls-files | Select-String -Pattern '(^|/)\.env$|^data/cache/|^data/runs/'
.\.venv\Scripts\python.exe scripts/run_review_harness.py --summary examples/fixtures/player_summary_demo.json --deterministic-report examples/fixtures/deterministic_report_demo.md --runs-root "$env:TEMP/riftcoach-fresh-gate-runs" --run-id fresh_gate_1_dry_run --dry-run
.\.venv\Scripts\python.exe scripts/check_project_governance.py
git diff --check
```

## Task 5: Persist the accepted checkpoint and publish exact-SHA evidence

**Files:**

- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`

**Steps:**

1. Record only evidence actually produced by Tasks 1-4.
2. Keep Fresh-Gate 2 as the exact next action until commit/push/CI succeeds.
3. Commit and push a reviewable implementation commit.
4. Verify GitHub Actions against that exact SHA.
5. Record the Actions run in a follow-up persistence commit and verify its exact SHA as well.
6. Only then set the next checkpoint to Fresh-Gate 3, which creates the new formal held-out assets in a separate authorized turn.

**Acceptance:**

- Old V1.0 files remain byte-identical and strictly readable.
- All new tests use synthetic development data.
- Provider calls and held-out executions are both zero.
- Fresh-Gate 1 code and exact-SHA public CI are separately evidenced.

## Execution result

- Status: complete
- Implementation SHA: `adba965a7f7fb4293020502b4440e9880633e571`
- GitHub Actions: `31860874440` completed/success
- Local/full CI regression: `568 passed, 103 subtests passed`
- External Provider calls: `0`
- Held-out executions: `0`
- Formal new held-out assets created: `0`
