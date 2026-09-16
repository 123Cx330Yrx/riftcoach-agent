# Local workspace routing

Verified 2026-09-16. This routes local work; each checkout's canonical state
remains authoritative for its scope. Recheck `git worktree list` and branch
before use. These absolute paths are local conveniences, not portable runtime
configuration. Other machines should select the corresponding verified branch.

| Checkout | Branch | Scope |
|---|---|---|
| `D:\riftcoach-agent` | `codex/g53-7-a-prime` | Main workspace and unfinished frontend/product work; backend checkpoint here is older. Preserve its existing dirty files. |
| `D:\riftcoach-agent-rq192-pr` | `codex/rq192-provider-stream-contract-ci` | Active backend reliability and report-evaluation work; read this checkout's `docs/project_execution_state.md` for that work. |

Do not merge product code, copy state documents between branches, or resolve
same-number RQ entries merely to make the checkouts look identical. Read both
sets of requirements when preparing their eventual integration.

For the next backend continuation, read
`docs/plans/2026-09-16-astra-restart-plan.md` **in the backend checkout**.
It records the instruction audit's restart sequence and downstream coverage;
it does not override the canonical checkpoint, accepted requirements or ADRs.
The current instruction-only task is not permission to restart paid experiments.

The 2026-09-15 retrospective is under
`C:\Users\33502\Documents\Agent\outputs\riftcoach-retrospective-2026-09-15`.
Use `requirements-and-followups.md` (62 themes), `frontend-renewal.md` and their
source links for requirement recovery, not as another always-read history.
Past statements such as "当前只复盘" describe their date; the latest user request
controls the current task. Current facts must be checked against code/receipts.
