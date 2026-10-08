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

For backend continuation, read the short canonical state and active work card
**in the backend checkout**. Apply `docs/plans/2026-09-22-agent-delivery-method.md`
for the execution method. `docs/plans/2026-09-16-astra-restart-plan.md` retains
downstream coverage, but its old experiment sequence is superseded. Original long
state/plan files are archived under `docs/archive/2026-09-22-execution-method/`;
their actions are historical only. Method maintenance is not model qualification;
subsequent implementation and experiments follow the user's existing authorization
and actual product contracts, not a historical pause instruction.

The 2026-09-15 retrospective is under
`C:\Users\33502\Documents\Agent\outputs\riftcoach-retrospective-2026-09-15`.
Use `requirements-and-followups.md` (62 themes), `frontend-renewal.md` and their
source links for requirement recovery, not as another always-read history.
Past statements such as "当前只复盘" describe their date; the latest user request
controls the current task. Current facts must be checked against code/receipts.

## Verified local runtime, 2026-09-28

Docker Desktop and the backend checkout's existing PostgreSQL volume are now
usable. Windows reserves host ports 5374–5473, including 5432. The same Compose
project `riftcoach-agent-rq192-pr` uses a machine-local override mapping only
PostgreSQL to `127.0.0.1:15432`; container port and existing database remain unchanged.
Do not run plain Compose for this machine's database and accidentally restore
the unusable 5432 mapping. Startup command, override and before/after evidence:
`C:/Users/33502/Documents/Agent/outputs/riftcoach-local-runtime-2026-09-28/README.md`.
Host applications must use port15432 with their existing DB credentials; shared
`.env` files were not rewritten. Docker29.7.2, container health, host SQL SELECT1
and migration head0014_message_projection_status were verified. No model Worker
or product candidate was enabled by this environment recovery.

## Machine transfer checkpoint, 2026-10-08

See `docs/plans/2026-10-08-machine-transfer-handoff.md` for the two-branch recovery,
local uncommitted/frontend and raw-evidence snapshots, excluded credentials/DB/host
history, and the closed-batch boundary. No actual transfer to a new machine has
been performed. Old drive paths are not prerequisites for the next checkout.
