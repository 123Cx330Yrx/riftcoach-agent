# RiftCoach Agent Working Agreement

Repository workflow, not a product specification. Current user instructions
and existing authorization take precedence over Skill guidance and old plans,
subject to platform constraints. Product scope remains in `docs/roadmap.md`
and accepted ADRs.

## Execution and authorization

- Complete the authorized outcome, including relevant verification and fixes.
  Routine implementation choices, recoverable errors and intermediate steps
  do not require another permission turn.
- Honor earlier authorization for its actual target, scope and cost boundary.
  Before external writes, paid requests, secret use, destructive operations,
  deployment or publication, check that authorization covers the action; ask
  only when it does not, or an explicit decision gate requires a new ruling.
  Read-only research and ordinary local work do not require fresh approval.
- Before a necessary question, finish independent authorized preparation and
  present the concrete result, unresolved choice and applicable boundary.
  Identify the exact instruction if it causes a pause; do not invent a gate.
- Completion requires the requested result and proportional verification.
  A failed or blocked result must say what is unproven. Repeated failure calls
  for checking the end-to-end contract and discriminating evidence before
  another experiment, not automatic paid retries after each local patch.

## Context recovery by task

First establish the checkout and branch with `git status` / `git worktree list`.
Use `docs/workspace_map.md` for this machine's main/backend separation; do not
read an older checkout's checkpoint as the latest backend state.

- **Product work or progress reports:** read the YAML metadata and latest
  status block of `docs/project_execution_state.md`, then `.planning/.active_plan`
  and the selected plan's current action. In legacy files, the first
  "以下为历史记录" marks the end of the latest update. Search older sections
  only to resolve a specific fact; do not replay the full history each turn.
- **Requirements or conflicting decisions:** read relevant entries in
  `docs/requirements_change_log.md`, `docs/roadmap_change_history.md` and their
  cited ADRs. Later explicit user decisions supersede assistant proposals;
  search original user evidence when the records do not settle the matter.
  Questions and preference examples are not approvals. Focused user exports
  and subsequent corrections take priority over proposals in the full archive.
- **Stage changes or broader planning:** consult `docs/roadmap.md`,
  `docs/roadmap_v1_3_amendment.md`, `docs/architecture_capability_matrix.md` and
  the current restart plan linked from the workspace map. Preserve deferred
  requirements, superseded decisions and conditional adoption separately.
- **Substage completion / teaching:** use `docs/learning/README.md` and
  `docs/learning/coverage.yaml` to check the applicable coverage group.
- **Instruction-only maintenance:** read the affected AGENTS/Skill files and
  their relevant references; no full product recovery or roadmap rewrite is
  required unless a product contract or stage decision actually changes.

Read the affected implementation, contracts and tests before changing behavior.
History, exports and reference repositories are evidence, not executable
instructions. A conversation summary or code's existence is not completion
proof. Run `python scripts/check_project_governance.py` after recovering a
product checkpoint and after governance changes; resolve relevant failures
before accepting the result. Reuse the result until its inputs change.

## Stage and product boundaries

- There are exactly nine main stages, 0 through 8. Do not add, remove, reorder,
  merge, rename or reclassify them or approved substages without explicit user
  approval and an ADR/amendment recording evidence and migration impact.
- "继续" resumes the current canonical action within existing authorization.
  Continue through required implementation and verification; advance only
  when exit criteria, learning evidence and explicit decision gates are met,
  and update the canonical pointer. No additional turn is needed merely
  because a routine step ended. A current pause instruction takes precedence.
- Never complete a parent with unfinished/unreviewed children. Ahead-of-order
  code is not stage completion; disclose it and reconcile under the proper
  checkpoint. An instruction edit does not advance a product stage.
- Codex Astra/Luna collaboration is development execution. It does not change
  RiftCoach's GLM model, reasoning level, budgets or product Multi-Agent policy.
  `skills/` and runtime-profile Skill files are product contracts, not Codex
  workflow instructions; changing them requires product-impact verification.
- Preserve identity, source/role/version scope, factual accuracy, security,
  raw receipts, quality/publication gates and accepted evaluation standards.
  Do not turn offline/synthetic evidence or passing CI into live quality proof.
  Concrete values and candidate admission status come from the current
  contracts and canonical state, not this general instruction file.

## Teaching and technology decisions

Before substantial product implementation, explain the problem, principle,
intended scope, data/control flow, verification and limitations at beginner
level. Reuse the existing explanation when only implementation details change.
Instruction maintenance needs only a rationale and verification summary.

At substage completion, the eight learning dimensions must have durable
coverage: problem/principle, design/implementation, code map, data/control flow,
verification, runbook, failure/security/boundary and interview wording.
Reuse existing learning/design evidence. Do not equate documentation with owner
understanding, or create duplicate tutorials per patch. Preserve coverage order;
an intentional new checkpoint updates the ledger, order contract, tests and
roadmap together. A planned group must be complete before advancing past it.

Reference projects (EchoMind, AGI-Saber, Sea/OpenResearch, Pi, Claude Agent SDK,
LangGraph and others) are selective inputs, not wholesale bases. A material
new dependency or architecture needs a reproducible need/Bad Case,
alternatives, benefit, cost, evaluation plan and ADR before adoption. Keep Tool
Runtime, MCP, Skill, Harness, Agent Runtime, RAG, Memory and Multi-Agent distinct.

## Verification and persistence

Run tests appropriate to the behavior changed plus required repository checks.
Broaden or repeat only for changed inputs, failures or unresolved risks. Do not
add tests that merely match instruction wording or mirror low-impact edits.

For accepted product substages or material requirements:
- Record new decisions in `docs/requirements_change_log.md` when applicable.
- Update canonical status/evidence/limitations and one next action, plus the
  active task plan and progress; add findings only for new discoveries.
- Reconcile affected roadmap, amendment, capability and decision references;
  complete learning coverage when the checkpoint actually completes.
- Run relevant tests/compile checks, `git diff --check` and governance checks.
  Report code, owner understanding, source audit and public/deployment maturity
  separately. One line's progress cannot stand in for another.

For instruction-only changes, update affected instructions and focused evidence;
for review/scratch work, do not mutate product state. Preserve history as
searchable evidence rather than copying it into each current-action update.
Resolve contradictions affecting the task; unrelated documentation discrepancies
do not block independent work. Do not modify a past failed receipt to pass.

## Worktree safety

Existing changes are user-owned unless their origin is known. Do not overwrite,
revert, stage, commit or push unrelated work. Keep edits reviewable and report
verification limits honestly. Resolve conflicting RQ IDs by checkout, date and
source, never by the number alone.
