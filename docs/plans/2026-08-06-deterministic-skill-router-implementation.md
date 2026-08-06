# Deterministic Skill Router V1 Implementation Plan

> **For Codex:** Execute this plan task-by-task in the existing RiftCoach worktree and stop before stage 5D.

> **Postmortem (2026-08-06):** This implementation batch crossed the approved
> teaching boundaries. Task 2 also implemented preparatory 5C-4 behavior, and
> Task 3 implemented a preliminary 5C-5 development evaluation. Those local
> files remain useful but are excluded from the accepted public baseline until
> 5C-5 review. Passing this plan completed only 5C-3; 5C-4 was later reviewed
> independently, while 5C-5 and 5C-6 still require their original review and
> acceptance.

**Goal:** Build an explainable deterministic router that maps Catalog candidates to the three-state Router Contract and measure it against a versioned development set.

**Architecture:** Skill manifests own declarative required signal groups and exclusions. A stateless router normalizes text, evaluates every candidate, and returns the existing `RouterDecision`; a separate evaluator measures exact decision accuracy without executing Skills.

**Tech Stack:** Python 3.11, Pydantic 2, PyYAML, pytest, standard-library JSON and Unicode normalization.

---

### Task 1: Extend the Skill trigger contract

**Files:**

- Modify: `app/skills/models.py`
- Create: `app/skills/routing_text.py`
- Modify: `app/skills/__init__.py`
- Modify: `skills/recent-form-review/manifest.yaml`
- Modify: `tests/test_skill_contracts.py`

**Steps:**

1. Add a shared deterministic text normalizer and a named trigger-group model with a non-empty, unique `any_of` tuple.
2. Require at least one trigger group and validate unique group names.
3. Reject normalized overlap between required and excluded signals.
4. Add recent-scope, review-goal and exclusion signals to the real Manifest.
5. Run `python -m pytest tests/test_skill_contracts.py -q` and require all tests to pass.

### Task 2: Implement the deterministic strategy

**Files:**

- Create: `app/skills/router.py`
- Modify: `app/skills/__init__.py`
- Create: `tests/test_deterministic_skill_router.py`

**Steps:**

1. Test empty candidates, one complete match, partial match, exclusion veto and no match.
2. Test normalization and longest-signal evidence.
3. Test two matching synthetic candidates return `ambiguous` without tie-breaking.
4. Implement a stateless `DeterministicSkillRouter.route(RouterRequest)`.
5. Run the Router Contract, Catalog and deterministic router tests together.

### Task 3: Add the versioned routing evaluation

**Files:**

- Create: `app/skills/routing_evaluation.py`
- Create: `data/evaluation/skill_router_v1_development_cases.json`
- Create: `scripts/evaluate_skill_routing.py`
- Create: `tests/test_skill_router_evaluation.py`
- Generate: `data/evaluation/results/skill_router_v1_development_baseline.json`

**Steps:**

1. Define validated dataset, case, case-result and aggregate-result records.
2. Load cases from JSON and reject unknown Skill names.
3. Compare outcome, reason, selected Skill and candidate names exactly.
4. Report exact accuracy and false-selection rate for expected rejections.
5. Run the CLI with `--min-accuracy 1.0` and save the development baseline.
6. State explicitly that this is a calibration/development set, not an independent holdout.

### Task 4: Regress and record the checkpoint

**Files:**

- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`

**Steps:**

1. Run `python -m pytest -q`.
2. Run `python -m compileall -q app tests scripts`.
3. Run `git diff --check` and scan new files for trailing whitespace.
4. Mark only 5C-3 complete when the deterministic strategy passes; record the
   5C-4/5 overlap as preparatory implementation, not checkpoint completion.
5. Stop before the independent 5C-4 review. Do not enter 5D Prompt/Context
   Builder or structured model output.
