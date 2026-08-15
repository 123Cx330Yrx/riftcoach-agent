# DeepSeek Fresh-Gate 3 Asset Freeze Implementation Plan

> **For Codex:** Use `executing-plans` and TDD. This plan creates and freezes assets only; it never reads a Key or constructs a Provider.

**Goal:** Create a genuinely new anonymous fixture, three-case held-out Dataset, V1.1 input plan, and body-free per-case Prompt/Context snapshot, then freeze their cross-identities with offline tests and exact-SHA public CI.

**Architecture:** Reuse the existing Dataset, input-plan, Prompt/Context and production Executor contracts. Add no new production execution path. Tests reconstruct the committed snapshot through the real Catalog, deterministic Router, SkillExecutionBoundary and ContextBuilderV1, while the committed Dataset remains the separate oracle.

**Tech stack:** Python 3.11, Pydantic v2, pytest, existing RiftCoach evaluation and Skill contracts, SHA-256 commitments.

---

## Safety boundary

This plan will not:

- load `.env` or an API key;
- construct or call a Provider;
- run held-out cases or create a real result;
- change Prompt, Evaluation, Harness, Router, RAG, AgentLoop or Provider code;
- enter Fresh-Gate 4, 5D exit review, 5E, 5F or stage 6.

## Task 1: Add red lifecycle and identity tests

**Files:**

- Create: `tests/test_deepseek_fresh_domain_assets.py`

**Red tests:**

1. Load the five new asset files; the first run must fail because they do not yet exist.
2. Require new fixture/report bytes and all case input identities to differ from old assets.
3. Require held-out/calibration-excluded lifecycle and oracle-blind Executor signature.
4. Rebuild the actual three-case Snapshot and require exact equality with the frozen file.
5. Require all Dataset/plan/snapshot/fixture cross-identities to agree.
6. Require the Snapshot serialization to exclude raw bodies and protected markers.

**Verify red:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_deepseek_fresh_domain_assets.py -q
```

## Task 2: Create the new anonymous fixture pair

**Files:**

- Create: `examples/fixtures/player_summary_domain_adoption_v2.json`
- Create: `examples/fixtures/deterministic_report_domain_adoption_v2.md`

**Implementation:**

- Use only synthetic IDs and data.
- Use different bytes, values, sample size and player identity from the demo fixture.
- Keep aggregate/win/loss values internally consistent.
- State the small-sample and non-causal boundary in the deterministic report.

**Verify:**

```powershell
.\.venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('examples/fixtures/player_summary_domain_adoption_v2.json').read_text(encoding='utf-8')); print('fixture-json-ok')"
```

## Task 3: Freeze Dataset, V1.1 plan and actual body-free Snapshot

**Files:**

- Create: `data/evaluation/domain_e2e_v2_secure_held_out_cases.json`
- Create: `data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json`
- Create: `data/evaluation/contracts/recent_form_prompt_context_v1_2.json`

**Implementation order:**

1. Define three new input cases with new IDs, wording, run IDs and injection markers.
2. Build the Snapshot from the real Context path and the new fixture pair.
3. Put each `case_context_sha256` into the V1.1 plan in exact case order.
4. Bind the Dataset contract to the Snapshot ID/SHA.
5. Serialize the static artifacts once; after acceptance they are immutable and cannot be used for tuning.

**Verify green:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_deepseek_fresh_domain_assets.py tests/test_provider_domain_input_plan.py tests/test_prompt_context_identity.py tests/test_provider_domain_readmission.py -q
```

## Task 4: Run proportional and complete offline verification

**Verify:**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_rag_retrieval.py --provider hybrid --output "$env:TEMP/riftcoach-rag-v1.json" --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0
.\.venv\Scripts\python.exe scripts/evaluate_rag_retrieval.py --provider hybrid --cases data/evaluation/rag_v1_holdout_cases.json --require-independent --output "$env:TEMP/riftcoach-rag-v1-holdout.json" --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0 --min-abstention-accuracy 1.0 --min-citation-support 1.0
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
rg -n "chat\.completions|\.choices" app/harness/adapters.py scripts/run_review_harness.py scripts/generate_llm_coach_report.py scripts/evaluate_coach_report.py scripts/revise_coach_report.py
git ls-files | Select-String -Pattern '(^|/)\.env$|^data/cache/|^data/runs/'
.\.venv\Scripts\python.exe scripts/run_review_harness.py --summary examples/fixtures/player_summary_demo.json --deterministic-report examples/fixtures/deterministic_report_demo.md --runs-root "$env:TEMP/riftcoach-fresh-gate-3-runs" --run-id fresh_gate_3_dry_run --dry-run
.\.venv\Scripts\python.exe scripts/check_project_governance.py
git diff --check
```

## Task 5: Persist and publicly freeze the checkpoint

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

1. Record only local evidence actually produced by Tasks 1-4.
2. Commit and push one reviewable asset-freeze commit.
3. Verify GitHub Actions against that exact SHA.
4. Record the public run in a follow-up persistence commit and verify that SHA too.
5. Set the single next action to Fresh-Gate 4 no-I/O preflight/real-run decision; do not run it in this plan.

## Acceptance

- New fixture/report and all case-specific content differ from the old assets.
- Dataset is held-out and calibration-excluded; production Executor remains oracle-blind.
- Snapshot is rebuilt exactly through the real Context path and contains no raw body.
- Provider calls and held-out executions remain zero.
- No result file exists at `data/evaluation/results/provider_capabilities/deepseek_v4_pro_domain_adoption_v2.json`.
- Local regression and exact-SHA public CI both pass.

## Execution result

- Status: complete
- Asset freeze SHA: `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8`
- GitHub Actions: `31861960565` completed/success
- Focused regression: `39 passed`
- Full regression: `574 passed, 103 subtests passed`
- RAG development/held-out gates: passed at their frozen 1.0 thresholds
- Compile, Harness SDK/tracked-data boundary, dry-run, governance, diff check: passed
- External Provider calls: `0`
- Held-out executions: `0`
- Real result file created: `false`
