# Stage 6 Session/Memory V1 Implementation Plan

> **For Codex:** Execute this plan one canonical batch at a time. Use TDD, the repository `AGENTS.md`,
> real PostgreSQL blocking evidence, independent commits, pushes, and exact-SHA CI. RQ-064 originally
> allowed entering 6B-2 after 6B-1 closes; RQ-065 supersedes that execution scope. Close 6B-1,
> prepare 6B-2, and stop for a later authorization.

**Goal:** Build a durable, owner-isolated Coach Session/Memory system that starts from stable Riot PUUID
identity, prevents model inference from directly mutating long-term state, and composes bounded Memory into
the existing Skill/AgentRuntime/Harness path.

**Architecture:** Keep the existing synchronous Python modular monolith. A dedicated PostgreSQL-backed
Player Link Worker resolves Riot ID to PUUID outside transactions; Conversation then freezes the trusted
owner/relationship/subject tuple. Typed Memory is materialized only through a versioned Candidate write gate.
PostgreSQL remains the sole authority; Context selection is deterministic and data-only.

**Tech Stack:** Python 3.11, Pydantic 2, FastAPI, SQLAlchemy 2, Alembic, psycopg 3, PostgreSQL 17,
pytest, Docker Compose, GitHub Actions, existing AgentRuntimeV1/ReviewHarness.

---

## Global execution rules

1. Read `AGENTS.md` and recover canonical/active-plan state before every batch.
2. Do not edit already-public migrations; add one reversible revision per schema batch.
3. SQLite is not valid evidence for PostgreSQL FK/CHECK/partial-index/concurrency behavior.
4. External Riot/Provider calls remain zero in unit tests, CI and package smoke.
5. API process never constructs Riot/Provider clients; all upstream calls stay in Worker composition.
6. Full PUUID, Riot ID, Message/Memory body, Prompt, Provider/Tool body and Secret never enter public logs/Trace.
7. Existing Review Task 1.0 remains readable; no historical row is silently backfilled from mutable Riot ID.
8. Every batch follows red → minimal green → focused/adjacent/full gates → state sync → independent commit/push →
   exact-SHA CI. CI failure keeps the batch open.
9. RQ-065 ends the current automatic chain after 6B-1 exact-SHA CI. Prepare 6B-2 but do not implement it
   without a later authorization; two batches can never share one commit.
10. Formal Auth/RSO/HTTPS, SSE/frontend, RLS, Redis/vector index, MCP, Multi-Agent, LangGraph and new SDKs remain out.

## 6B-1: Player Identity & Link Persistence Foundation

### Outcome

After this batch, strict Player/Relationship/Link Task domain contracts, PostgreSQL tables and a transactional
Repository/Service exist. No HTTP route, Riot resolver, Worker executable or Conversation exists yet.

### Files

- Create: `app/players/__init__.py`
- Create: `app/players/models.py`
- Create: `app/players/ports.py`
- Create: `app/players/fingerprint.py`
- Create: `app/players/service.py`
- Create: `app/persistence/player_records.py`
- Create: `app/persistence/player_repository.py`
- Create: `migrations/versions/0002_create_player_identity_and_link_tasks.py`
- Modify: `migrations/env.py`
- Create: `tests/test_player_models.py`
- Create: `tests/test_player_link_service.py`
- Create: `tests/test_player_identity_migrations_postgres.py`
- Create: `tests/test_player_repository_postgres.py`
- Modify: `.github/workflows/tests.yml`
- Modify: canonical/governance documents required by `AGENTS.md`

### Contract details

`app/players/models.py` defines:

```python
class RoutingRegion(StrEnum):
    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"

class RelationshipRole(StrEnum):
    SELF = "self"
    OBSERVED = "observed"

class VerificationStatus(StrEnum):
    UNVERIFIED_CLAIM = "unverified_claim"
    NOT_APPLICABLE = "not_applicable"
    RSO_VERIFIED = "rso_verified"

class PlayerLinkStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
```

Current creation commands accept role but never verification status. Service derives self→unverified and
observed→not_applicable. Any current command attempting verified status is impossible by construction.

Link task request must persist normalized `game_name` and `tag_line` because the later Worker needs them for
Account-V1. These values are bounded private SQL input and are never emitted to general logs. Fingerprint covers
task kind/version/routing/name/tag/role using canonical JSON SHA-256.

Repository protocol:

```python
class PlayerRepository(Protocol):
    def create_or_replay_link(...): ...
    def get_link_by_id(...): ...
    def claim_next_link(...): ...
    def resolve_link(...): ...  # atomic subject+alias+relationship+terminal
    def fail_link(...): ...
```

`resolve_link()` receives a strict `ResolvedRiotAccount` value from the future adapter; it performs no network I/O.
If the owner already has the same subject under a different role, `resolve_link()` atomically writes the Link Task as
`failed/relationship_role_conflict` in that same transaction, without alias/relationship mutation. It must not raise
and rely on a later Worker `fail_link()` transaction.

### Task 1: Freeze pure domain contracts

1. Write failing `tests/test_player_models.py` cases for:
   - accepted routing values and rejected `cn`/`zh_CN`;
   - Riot ID normalization/control/length bounds;
   - valid role/verification pairs and invalid pairs;
   - queued/running/succeeded/failed Link Task shape;
   - success requires subject+relationship; failed forbids them;
   - full PUUID is absent from public `PlayerLinkTaskView`;
   - retryable reason projection is allowlisted;
   - current create command cannot accept verification status.
2. Run:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/test_player_models.py -q
   ```

   Expected: collection/import failure because `app.players` does not exist.
3. Implement the smallest strict Pydantic models and enums.
4. Re-run and require all tests green.

### Task 2: Freeze canonical link fingerprint and Fake service behavior

1. Write failing `tests/test_player_link_service.py` for:
   - field-order independent fingerprint;
   - role/region/name/tag changes alter fingerprint;
   - same owner/key/fingerprint replays original link task;
   - same owner/key/different fingerprint raises idempotency conflict;
   - owner/global active capacity projection;
   - server-generated UUID/identity invalidity fails safely;
   - public service error exposes only allowlisted code.
2. Run the focused test and confirm red because fingerprint/service is missing.
3. Implement `fingerprint.py`, service ports and a test Fake Repository.
4. Re-run focused tests.

### Task 3: Add reversible PostgreSQL schema

1. Write failing `tests/test_player_identity_migrations_postgres.py` that upgrades current head and asserts:
   - four tables exist: `player_subjects`, `player_aliases`, `owner_player_relationships`, `player_link_tasks`;
   - expected PK/UNIQUE/CHECK/FK/index names exist;
   - `(game, puuid)` is unique;
   - `(owner_id, player_subject_id)` relationship is unique;
   - role/verification combinations are constrained;
   - Link Task persists bounded private `game_name`/`tag_line` plus routing/role/fingerprint fields;
   - Link Task lifecycle success/failure shapes are constrained;
   - all FK lookup columns are indexed;
   - downgrade to `0001_review_tasks` removes only the new tables;
   - re-upgrade succeeds.
2. Run locally. Without PostgreSQL, expected result is an explicit skip, not a fake SQLite green.
3. Create ORM records and migration 0002. Import records in `migrations/env.py` so `alembic check` sees metadata.
4. Add the new migration test to the blocking PostgreSQL Actions job.
5. Run compile and no-DB metadata/model tests locally.

### Task 4: Implement transactional PostgreSQL Repository

1. Write failing `tests/test_player_repository_postgres.py` for:
   - create/replay/conflict and owner/global capacity;
   - normalized `game_name`/`tag_line` round-trip to a claimed task without appearing in its public View;
   - owner-scoped GET makes not-owned indistinguishable from missing;
   - deterministic `FOR UPDATE SKIP LOCKED` Link Task claim;
   - two workers cannot claim one task;
   - resolve creates one subject, one alias, one relationship and Link success in one transaction;
   - concurrent same-PUUID resolves converge through unique/upsert semantics;
   - same owner/subject/same role reuses relationship;
   - same owner/subject/different role atomically writes failed/`relationship_role_conflict` without alias or
     relationship mutation and without a second Worker failure transaction;
   - old/wrong worker cannot resolve/fail terminal CAS;
   - failed terminal cannot contain subject/relationship;
   - SQL exception rolls back all four identity writes;
   - timestamps are timezone-aware and ordered.
2. Confirm explicit local skip if PostgreSQL is unavailable.
3. Implement `PostgresPlayerRepository` with short transactions. Use one atomic transaction for resolution;
   never accept a callback that could perform network I/O inside it.
4. Add repository test file to blocking CI.

### Task 5: 6B-1 verification and public closure

Run focused:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_player_models.py `
  tests/test_player_link_service.py `
  tests/test_player_identity_migrations_postgres.py `
  tests/test_player_repository_postgres.py -q
```

Run proportional adjacent tests for task models/service/repository/claim/migrations, then full suite and the exact
workflow gates:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py --provider hybrid --output tmp/rag-v1-evaluation.json --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0
.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py --provider hybrid --cases data/evaluation/rag_v1_holdout_cases.json --require-independent --output tmp/rag-v1-holdout-evaluation.json --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0 --min-abstention-accuracy 1.0 --min-citation-support 1.0
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

Update canonical to 6B-1 local-complete/pending public CI, commit only this batch, push, and wait for exact-SHA
`pytest`, `postgres-migrations`, and `packaging-smoke`. Only all-green closes 6B-1; RQ-065 then requires a stop
with 6B-2 prepared/waiting authorization.

### Not in 6B-1

- Riot client/resolver or any external call;
- PlayerLinkWorker/CLI/HTTP routes;
- Conversation/Message/Memory;
- Review Task schema changes;
- Auth/RSO or verified-self creation.

## 6B-2: Async Player Link Worker/API Vertical Slice

### Outcome

After this batch, an owner can POST a link intent, poll it, and a dedicated Worker can resolve it through a narrow
Account-V1 adapter. Tests and Linux smoke use a Fake Resolver and make zero external calls. Conversation remains next.

### Files

- Create: `app/lol/account_resolver.py`
- Create: `app/players/link_worker.py`
- Create: `app/players/composition.py`
- Create: `app/api/player_models.py`
- Modify: `app/api/main.py`
- Modify: `app/api/composition.py`
- Create: `scripts/run_player_link_worker.py`
- Modify: `scripts/run_packaging_smoke.py`
- Modify: `compose.yaml`
- Modify: `.env.example`
- Modify: `.github/workflows/tests.yml`
- Create: `tests/test_riot_account_resolver.py`
- Create: `tests/test_player_link_worker.py`
- Create: `tests/test_player_link_api.py`
- Create: `tests/test_player_link_api_postgres.py`
- Create: `tests/test_player_link_composition.py`
- Modify: `tests/test_packaging_contract.py`
- Modify: `tests/test_packaging_smoke.py`
- Modify: canonical/governance documents required by `AGENTS.md`

### Public API contract

```text
POST /player-links                  202/409/422/503
GET  /player-links/{link_task_id}   200/404/503
```

POST body:

```json
{
  "riot_id": "gameName#tagLine",
  "routing_region": "asia",
  "relationship_role": "self"
}
```

Owner comes only from `ActorContext`; Idempotency-Key remains a header. No body field for owner, PUUID, subject,
relationship or verification exists.

Queued/running response is body-free identity/status. Success may expose local `player_subject_id`,
`relationship_id`, relationship role/verification label and confirmed display Riot ID; it never exposes PUUID.
Failure exposes an allowlisted reason/retryable flag, never upstream body or exception.

### Task 1: Implement and test the narrow Account resolver

1. Write failing `tests/test_riot_account_resolver.py` using an injected Fake Riot client/factory.
2. Cover:
   - explicit routing passed to client factory;
   - strict PUUID/gameName/tagLine response validation;
   - 404→player_not_found;
   - 401/403→riot_authentication_failed;
   - bounded 429 Retry-After→riot_rate_limited;
   - timeout/connection/upstream mappings;
   - raw response/exception/request ID never retained on public error;
   - construction performs no network I/O;
   - `cn`/`zh_CN` cannot reach the client.
3. Implement `RiotAccountResolver` over the existing explicitly configured `RiotClient`; do not load dotenv in API.
4. Re-run focused tests.

### Task 2: Implement deterministic PlayerLinkWorker

1. Write failing `tests/test_player_link_worker.py` for empty claim, successful resolution, every safe resolver failure,
   bad result, role conflict, ownership loss, terminal CAS and graceful stop.
2. Ensure resolver is invoked after claim commit and no transaction remains open during Fake latency.
3. Implement one-iteration and polling Worker with existing bounded backoff/jitter patterns, but no auto retry of a
   failed link task.
4. Add body-free observability: link task id, status, safe reason, latency; no Riot ID/PUUID.

### Task 3: Add POST/GET Link API without Riot dependencies

1. Write failing `tests/test_player_link_api.py` for OpenAPI, strict body/header, 202 create/replay, 409 conflict,
   capacity 503, owner 404, queued/running/succeeded/failed DTOs, retryable flag and no PUUID.
2. Verify application creation/import/OpenAPI calls no resolver, Riot client, Key, DB or network.
3. Add `PlayerLinkServicePort` and routes to `create_app()`; update existing test doubles explicitly rather than making
   production behavior silently optional.
4. Add `tests/test_player_link_api_postgres.py` for real create/replay/owner query and add it to blocking CI.

### Task 4: Compose Worker/API and Linux no-I/O smoke

1. Write failing composition/packaging tests before changing Compose.
2. `app/api/composition.py` builds Player Repository/Service only; it still has no Riot dependency.
3. `app/players/composition.py` builds production Link Worker after DB/migration, explicit Riot Key and routing policy
   validation. Missing configuration fails before claim.
4. `scripts/run_player_link_worker.py` supports `--check` and `--once`, validates worker id before Engine/client creation.
5. Add `player-link-worker` to normal Compose dependency graph.
6. Extend the smoke profile with an explicit Fake Account Resolver inside the diagnostic process: POST link, claim,
   resolve fixture account, GET succeeded. Record `external_riot_provider_calls=0`.
7. Image boundary remains non-root and excludes `.env`, tests, cache/runs/reports/tmp.

### Task 5: 6B-2 verification and public closure

Run focused API/Worker/Resolver/PostgreSQL/package tests, adjacent existing API/Worker/Riot/task suites, then the same
full gates as 6B-1. Commit only 6B-2, push and require exact-SHA all-green jobs. CI cannot contain Riot/Provider Key or
external network calls.

Only after public closure may canonical mark 6B-3 as prepared/waiting authorization; it must not implement 6B-3.
This remains the future 6B-2 closure procedure. RQ-065 defers it to a later authorized turn rather than deleting
or merging the planned batch.

### Not in 6B-2

- Conversation/Message creation;
- Review Task subject binding;
- Memory Candidate or long-term Memory;
- automatic retry/lease/reclaim;
- verified-self/Auth/RSO;
- real Riot call during development/CI.

## 6B-3: Conversation & Message Foundation

### Outcome

Create immutable-subject Conversation and ordered Message storage/API. It only accepts an active relationship owned by
the Actor; no Agent/Review/Memory execution occurs yet.

### Expected files

- Create: `app/conversations/models.py`, `ports.py`, `service.py`
- Create: `app/persistence/conversation_records.py`, `conversation_repository.py`
- Create: `migrations/versions/0003_create_conversations_and_messages.py`
- Create: `app/api/conversation_models.py`
- Modify: `app/api/main.py`, `composition.py`, `migrations/env.py`, workflow
- Create: pure/API/PostgreSQL/concurrency tests

### TDD invariants

- active owner relationship required;
- DB composite FK prevents cross-owner/subject binding;
- trigger and Repository both prohibit rebind;
- archived Conversation rejects new messages; hidden is owner-invisible;
- message sequence is unique, atomic and ordered under concurrency;
- roles only user/assistant; content/digest/size strict;
- system/tool/provider bodies cannot be stored through public Service;
- no external I/O.

## 6B-4: Conversation-bound Recent Review Identity

### Outcome

Add Review Task schema 2.0 and `/conversations/{id}/reviews/recent`. Server derives owner/relationship/subject;
Summary collection uses trusted PUUID, and legacy 1.0 remains read-only-compatible.

### Expected files

- Add migration 0004 for nullable legacy-compatible conversation identity columns plus schema-version CHECK/FK
- Extend task/domain/repository/API models with v2 identity
- Add `RiotPlayerSummaryBuilder.build_by_puuid()` and conversation-bound application compiler
- Add API/Worker/PostgreSQL/existing Runtime-Harness vertical tests

### TDD invariants

- request body contains only count/queue/focus;
- client/model cannot override owner/conversation/subject/PUUID;
- task tuple equals current Conversation tuple at create and execution;
- alias rename does not change subject;
- v2 execution does not call Account-V1 again;
- old 1.0 rows/endpoints remain queryable but create no Conversation/Memory;
- late task cannot write against UI's newly selected Conversation.

## 6B-5: Memory Candidate & Write Gate

### Outcome

Create Candidate source/target/provenance/gate contracts and exactly-once acceptance transaction, without concrete
long-term Memory target tables yet.

### TDD invariants

- source and target scope are distinct;
- model/natural-language proposals always pending regardless of confidence;
- only allowlisted deterministic/UI sources can system-accept;
- public-observed target kinds restricted;
- Candidate terminal state immutable;
- accepted Candidate can materialize exactly once;
- public responses remain body/provenance safe.

## 6B-6: Preferences, Profile & Review Memory

### Outcome

Implement typed field-level versions for owner Preference, self-only Player Profile, and self/observed Review Memory.

### TDD invariants

- partial unique active key;
- optimistic expected version and supersede chain;
- observed cannot create Profile;
- observed Review Memory only third-person observation/public trend;
- source Candidate identity unique;
- cross-owner/subject FK failures;
- view/history/correction API owner isolation.

## 6B-7: Training Plan & Progress

### Outcome

Implement user-confirmed self-only Plan, one active Plan per relationship, Artifact-grounded allowlisted Progress and
deterministic trend comparison.

### TDD invariants

- observed and unowned Plan/Progress rejected in Service and DB;
- draft cannot become active without user-confirmed Candidate;
- one active Plan partial unique;
- Progress metric belongs to Plan allowlist and complete source Artifact;
- correction is a superseding event, not overwrite;
- no causal/psychological inference from metric trend.

## 6B-8: Memory-aware Context & Typed Conversation Turns

### Outcome

Select bounded legal Message/Memory records, emit a private context manifest, compose data-only sections through the
existing ContextBuilder/AgentRuntime/Harness, and persist only terminal Assistant messages/Candidates.

### TDD invariants

- stable selection order and whole-record truncation;
- pending/superseded/expired/hidden excluded;
- claimed/observed projections differ correctly;
- Memory text cannot escalate to instruction/tool permission;
- Context ceiling cannot be raised by caller;
- manifest binds IDs/versions/digests without body;
- no arbitrary free-chat Skill is silently introduced.

## 6B-9: Lifecycle, Export & Exit Review

### Outcome

Implement owner-scoped export, retention/purge, three explicit delete scopes, hidden-before-cleanup compensation,
performance/security/isolation/package evidence and the Session/Memory V1 exit matrix.

### Exit evidence

- two owners/two Conversations/same PUUID private isolation;
- claimed-self/public-observed behavioral and DB separation;
- no verified-self creation path;
- link/Conversation/Memory end-to-end with Fake Riot/Provider and real PostgreSQL;
- correction/export/delete/retention and failure compensation;
- Context manifest and publication gate preserved;
- full tests/RAG/compile/security/governance/PostgreSQL/Linux package exact-SHA green;
- formal Auth/RSO/HTTPS, SSE/frontend, MCP and Multi-Agent remain explicit deferred boundaries.
