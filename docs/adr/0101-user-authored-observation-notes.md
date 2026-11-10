# ADR-0101: User-authored notes for observed players

Status: Accepted for the bounded observation-note slice, 2026-09-11.

Local consumption follow-up: the default composed API does not inject a session
service, so /auth/session returns auth_unavailable even with a local owner. Add an
explicit loopback-only launcher using the existing local session boundary and
real composed PostgreSQL services. Require the local profile and an explicit owner;
do not change the default API or invent a production identity provider. Session
state lasts for the process lifetime; persisted notes survive restart. Verify the
full composed session/conversation/candidate/accept/readback path with PostgreSQL,
including missing-cookie and missing-CSRF rejection. This is local access, not
OIDC/RSO or foreign Riot account login.

Problem: the archive workbench can display ShowMaker but loses a viewer's notes.
Existing Review Memory already stores observation_note under an owner-player
relationship, but its public structured-input gate rejects this use case.

Decision: reuse Conversation → Memory Candidate → user accept → Review Memory
and the existing owner-scoped review-memory GET. Admit only observed/append/
observation_note for structured user input, with a distinct gate-policy version.
Do not add a table, generic archive upload endpoint, or another persistence stack.
The save button expresses the user's write intent and performs candidate creation
and acceptance. A retry retains operation identity and any returned candidate ID.

An optional user_attached_archive reference carries source_run_id, bundle digest,
report SHA and original observation time. These are user-attached metadata, not
server-verified task provenance. No source_task_id or authenticated run binding is
invented. Old text-only notes remain valid; the 4 KiB typed payload limit remains.

The browser connects only on explicit action, selects an existing matching observed
profile from the authenticated owner's list, and reads notes back. Importing an
archive alone remains local and performs no API calls. No Riot self account is
required. Creating a missing observed profile remains the existing Account flow.

Training, model-generated memory gates and non-observation keys remain unchanged.
The archive report itself stays in the local file; this slice persists user notes,
not report publication, exercise completion, or the entire golden-slice pipeline.

Verification: gate/payload counterexamples, API owner isolation and readback tests
with real PostgreSQL, existing session/CSRF enforcement tests, browser CSRF header
and save/reload/filter/failure tests, and existing regressions.
No external Provider/Riot/OP.GG calls are necessary. Workbench redesign remains
deferred per the four-surface design follow-up.

## Engineering and learning evidence

Code map: memory/gate.py admits the narrow user-observation case;
memory/typed_models.py validates the optional archive reference while preserving
old payload fingerprints. Existing materializers and owner-scoped query services
write/read review_memories. ObservationNotesApi handles existing API contracts;
ObservationNotes implements explicit connect, save, retained retry and readback.
No new database migration or dependency is needed.

Runbook: import an observation JSON at /?view=observation; connect an authenticated
RiftCoach session with a matching observed profile (use the Account page if absent);
write a note and save. Reload, import the same archive, connect and read it again.
An uncertain response keeps the operation on the current page. Reconnect refreshes
the session before retry. Closing the page loses the pending retry identity; saved
notes remain server-side. Reads currently inspect at most 100 recent records.

Failure boundaries: an unavailable session/profile cannot write; owner isolation
is enforced server-side. An accept response lost after commit can be retried without
another candidate or memory row. The UI only claims success after readback. Archive
references are user assertions, not proof of a trusted run. Source identifiers on
the server candidate are not populated from these assertions. Text is rendered
inertly and payload size remains 4 KiB. No Training or source API writes occur.

Verification evidence: 47 focused backend/session tests passed; 280 frontend unit
tests passed; two browser scenarios passed, including uncertain acceptance retry,
reload, no-API local import and mobile overflow. Typecheck/build passed. The new
PostgreSQL round-trip test is explicitly included in the public database job.
Local execution failed connecting to the stopped database at localhost:54329;
this is not counted as a pass or silently skipped. Browser routes use fixtures;
this does not establish an actual user-owned ShowMaker record was written.

Interview wording: implemented owner-scoped observation notes by reusing a
candidate-confirmation-memory pipeline, and tested retry/readback contracts.
Do not claim the entire product or a deployed authenticated golden slice is done.
The parent learning checkpoint stays in progress; this ADR supplies the bounded
slice's design, flow, verification, operations and boundary evidence.

Visual QA: the connected note form and reloaded note list were inspected at desktop
and 390px mobile widths using synthetic browser routes. Screenshots are local
outputs/observation-notes-fixture-desktop.png and observation-notes-fixture-mobile.png.
The fixture label is intentional; these are not real owner database screenshots.


2026-09-11观摩笔记公共收口：实现d177f08a2ccc34c6eb388cf010188ff2eaad1f22经Actions34555782966同SHA三任务success。Python3049 passed/153 skipped/127 subtests、前端280、浏览器40、PostgreSQL209（包含新增真实数据库落库/重试/隔离测试），打包smoke成功。桌面及390px手机笔记区经合成浏览器截图复核。笔记保存/API接线达到completed-public；这不代表已向用户实际ShowMaker档案写入或已部署。新增Provider0、累计68；原报告两项自动质量漏检保留，8E仍in_progress。唯一下一步为现有认证服务与observed档案的真实端到端消费验证准备，沿用ShowMaker，无需本人外服账号；Workbench四块设计仍后置。

## Explicit local session runbook (2026-09-11)

The default composed API has no injected session service and intentionally returns
503 auth_unavailable. The new scripts.run_local_observation_api launcher requires
RIFTCOACH_API_PROFILE=local and an explicit RIFTCOACH_LOCAL_OWNER_ID; DATABASE_URL
must point to an existing migrated local database. Start it from the repository:

```powershell
$env:RIFTCOACH_API_PROFILE = "local"
# Select the owner already associated with the intended local observed profile.
# Supply DATABASE_URL and RIFTCOACH_LOCAL_OWNER_ID locally; never paste secrets into logs.
.venv/Scripts/python.exe -B -m scripts.run_local_observation_api --port 8000
```

The launcher binds only 127.0.0.1. The existing Vite /api proxy targets that port;
for another port, set RIFTCOACH_WEB_API_TARGET to its loopback URL before starting
Vite. Import the original ShowMaker archive and connect. Missing observed profiles
remain an Account/real player-link setup step; this launcher does not fabricate
player identity, seed user notes, start a Worker, migrate/reset a database, or call
Riot/OP.GG/Provider. Local session cookies are HttpOnly, same-site, and HTTP-only
for loopback development. This explicit local factory must not be publicly hosted;
the default production factory remains unchanged and requires a selected auth adapter.
Session restart requires reconnect; persisted notes remain in PostgreSQL.

Verification: tests/test_local_observation_api.py checks explicit local/owner guards,
session issuance and missing-cookie/CSRF rejection without DB I/O. The added composed
PostgreSQL test uses the real lifecycle, service composition, conversation creation,
note acceptance, app restart and owner isolation. Its seeded identity/text are
synthetic; it is not proof of an actual user-owned ShowMaker profile being available.
Local focused checks: 19 passed. Docker Desktop was started normally but its Linux
engine pipe remained unavailable; no volume reset or runtime-directory moves were
performed. Public PostgreSQL verification remains required for this batch.


2026-09-11本地真实观摩消费完成：实现a1eb64e1591151820d20fe2c7bf57870814101c3由Actions34556770700同SHA三任务success（Python3051 passed/154 skipped/127 subtests、前端280、浏览器40、PostgreSQL210，打包通过）。默认入口未注入session的缺口由显式loopback local入口解决，生产默认不变。Docker启动失败已定位到sailor-ingest.sock及Secrets Engine engine.sock无法访问；备份重建两个通信目录后本次启动恢复，未删除数据库卷，不宣称永久修复。原riftcoach库先pg_dump备份，再0011→0014升级。实际通过现有API/单次player-link worker解析DK ShowMaker#KR1 asia为observed，归属于明确本地owner local-showmaker-observer；没有冒充用户正式登录身份。真实浏览器导入原五局归档→连接会话→保存明确标注的验证笔记→刷新/重新导入读回→重启API重新连接读回全部通过，真实DB只有1条验证笔记；390px无溢出，page errors=0。回执outputs/showmaker-notes-live-receipt.json，SHA256 011a8565d23a3d697ea6703fba743fb73156044a67029852c50d4e8a94df966c。实际新增1次Riot Account-V1读取，比赛/OP.GG/Provider0，累计Provider保持68。8E仍in_progress；正式OIDC/RSO、报告可信产品发布、个人Training和两项自动质量漏检仍未完成。唯一下一步为黄金切片剩余缺口审查，优先把两项已确认的自动质量漏检固化为离线反例，再确定修复批次；Workbench四块设计继续后置。

Local live runbook result: http://127.0.0.1:5187/?view=observation proxies the local
API on port 8016. API PID 16448 was restarted successfully; session reconnection
reads the same persisted note. Vite runs in the current desktop terminal session.
The source archive and new desktop/mobile screenshots are in the existing user
outputs folder. Database backup riftcoach-before-local-observation-20260911.dump
is retained for rollback. Communication-directory backups are retained locally;
these are not product evidence and must not be published. No local credentials,
session tokens, database dump, PUUID or run payload were committed.

Earlier statements that Docker recovery and runtime-directory moves had not occurred
refer to the initial preparation. Subsequent log evidence justified the narrowly
scoped backup/rebuild above; it recovered this launch only. The synthetic public
DB test and the later live local ShowMaker browser receipt are separate evidence.
