# 8C Reliable Runtime Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有 PostgreSQL task/Worker/Runtime/Harness 上实现可重放、可取消、带租约与 fencing、仅凭安全证据恢复的可靠任务控制面。

**Architecture:** PostgreSQL 继续作为唯一控制面；task row 保存当前 projection，append-only task event 保存
body-free 生命周期历史。Worker 使用 generation + private token + expiry，Recovery 只接受严格 Receipt 或
safe checkpoint；现有 Runtime Trace/Harness/Artifact 保持各自事实源。

**Tech Stack:** Python 3.11、Pydantic v2、SQLAlchemy 2、Alembic、PostgreSQL 17、FastAPI、pytest；不增加新运行时依赖。

---

### Task 1：Pure reliable-runtime contracts 与 projector

**Files:**
- Create: `app/tasks/reliable_runtime.py`
- Modify: `app/tasks/models.py`
- Create: `tests/test_reliable_task_contracts.py`

**Steps:**

1. 写失败测试：lease policy、private token、checkpoint shape、cancel result、event SHA identity、连续 replay、
   duplicate/late terminal 拒绝；运行 `pytest tests/test_reliable_task_contracts.py -q`，预期 collection/import FAIL。
2. 最小实现 strict Pydantic contracts、canonical event identity 与 pure projector；不接数据库。
3. 重跑聚焦测试，预期 PASS；再运行 `tests/test_task_models.py` 与 `tests/test_conversation_review_task_models.py`。
4. 记录 red→green 结果，不在本任务创建 migration。

### Task 2：0010 schema、metadata 与 legacy bootstrap

**Files:**
- Create: `app/persistence/task_event_record.py`
- Modify: `app/persistence/task_record.py`
- Modify: `migrations/env.py`
- Create: `migrations/versions/0010_reliable_runtime_core.py`
- Create: `tests/test_reliable_task_migrations_postgres.py`
- Modify: `tests/test_database_config.py`
- Modify: migration-head assertions that must now name 0010

**Steps:**

1. 先写 offline SQL/metadata 与真 PostgreSQL migration 红灯：新列、event table、约束、索引、legacy snapshot、
   downgrade/reupgrade；本机真库允许明确 skip。
2. 实现 ORM 与 0010 migration；status/lifecycle/checkpoint/event JSON 必须有数据库约束和大小门。
3. 运行聚焦 migration/metadata tests；offline 必须 PASS，本机无 DB 的 test 只能 SKIP。
4. 运行 `alembic upgrade head --sql` 并确认无 SQLite/非 PostgreSQL 语义。

### Task 3：Repository event/lease/fencing/cancel/replay TDD

**Files:**
- Modify: `app/tasks/ports.py`
- Modify: `app/persistence/task_repository.py`
- Create: `tests/test_reliable_task_repository_postgres.py`
- Modify: existing task repository/claim/lifecycle tests only for the new explicit lease contract

**Steps:**

1. 写真库红灯：create+event 原子性、双 claim、generation/token、heartbeat、checkpoint、cancel、terminal lease/
   token fence、duplicate terminal、owner event replay 与 limit。
2. 实现 `_append_event`、strict read mapping 和每个 mutation 的 same-transaction event；事件 identity 重算失败
   必须映射为 integrity failure。
3. 实现 claim/heartbeat/checkpoint/cancel/fenced terminal CAS；token 永不进入 public view/event/log。
4. 运行 repository 聚焦测试；本机无 PostgreSQL 时同时用 SQL/metadata/pure tests 保持可审查，公共 CI 补真库。

### Task 4：Lease-aware Worker 与 cancel precedence

**Files:**
- Modify: `app/workers/review_worker.py`
- Modify: `app/workers/composition.py`
- Modify: `app/tasks/recent_review_executor.py` only if a boundary callback is required
- Create: `tests/test_reliable_review_worker.py`
- Modify: `tests/test_review_worker.py`, `tests/test_worker_composition.py`, `tests/test_task_observability.py`

**Steps:**

1. 写失败测试：claim shape、execution-start checkpoint、bounded heartbeat、cancel during execution、expired/lost
   lease、success/failure fence、terminal turn only after accepted terminal。
2. 实现标准库 thread/event 的 bounded lease maintainer；开始 executor 前先写 unsafe execution-start checkpoint，
   结束后做 final heartbeat/cancel check。
3. success/fail CAS 被 cancel 阻断时尝试 fenced cancel terminal；被 recovery/新 generation 阻断则返回 ownership_lost。
4. composition 增加有界 lease 环境设置并 fail closed；不增加网络/队列依赖。

### Task 5：Receipt/checkpoint-proven Recovery

**Files:**
- Modify: `app/tasks/reconciliation.py`
- Create: `tests/test_reliable_task_recovery.py`
- Create: `tests/test_reliable_task_recovery_postgres.py`

**Steps:**

1. 写失败测试：expired cancel、strict receipt reconcile、claimed-safe requeue、execution-started recovery_required、
   max recovery、recovery-vs-late terminal。
2. 实现 bounded candidate scan 与文件验证在事务外、最终 mutation 为 expected generation/token/status 的短 CAS。
3. 任何 missing/drifted receipt 或 unsafe checkpoint 都不得重跑；记录 body-free recovery reason/event。
4. 保留 `ManualReviewTaskRecovery` 兼容，但只允许 recovery_required + expected worker/generation 的受限失败。

### Task 6：Owner-scoped cancel/event HTTP seam 与 no-I/O vertical

**Files:**
- Modify: `app/tasks/service.py`
- Modify: `app/api/task_models.py`
- Modify: `app/api/main.py`
- Modify: `app/api/composition.py` if service wiring requires it
- Create: `tests/test_reliable_task_api.py`
- Modify: `tests/test_async_task_api.py`, `tests/test_async_task_api_postgres.py`

**Steps:**

1. 写 API 红灯：`POST /tasks/{id}/cancel` 需要 trusted owner + Idempotency-Key；event page 需要 owner scope、
   cursor/limit；invalid/other-owner 一律安全 404/422，数据库失败 503。
2. 实现薄 Adapter 和 body-free DTO；不暴露 token、request payload、checkpoint body、PUUID 或内部错误。
3. 跑 Fake API 与真库 API 纵向；external Riot/OP.GG/Provider/Key I/O 必须为 0。

### Task 7：故障注入、八维 evidence 与 checkpoint exit

**Files:**
- Create: `docs/learning/8c-reliable-runtime-core-walkthrough.md`
- Modify: `docs/learning/coverage.yaml`, `docs/learning/README.md`
- Modify: canonical state、active plan、roadmap/history/amendment/capability/project decisions
- Modify: `.github/workflows/tests.yml` and package smoke only where 0010/vertical evidence requires it

**Steps:**

1. 运行 pure/Repository/Worker/recovery/API/Harness 相邻集合，注入 cancel-terminal、recovery-late-result、
   duplicate event/terminal、Receipt drift 和 DB failure。
2. 更新 walkthrough 八维：问题/原理、设计/实现、代码地图、数据/控制流、验证、runbook、失败/安全/边界、
   面试准确表述；coverage 在公共门前保持 `planned`。
3. 运行完整 pytest、两套 RAG、Harness dry-run、compileall、pip、YAML、SDK/Secret/tracked-data、body-free scan、
   governance 与 `git diff --check`。
4. 独立 implementation/evidence 提交并推送；等待 exact-SHA `pytest`、`postgres-migrations`、
   `packaging-smoke` 三 job全部 success。
5. 公共闭环后才把 8C coverage 置 `complete`，独立状态收尾并只交接
   `8d-riot-opgg-evidence-fusion-core` prepared/waiting authorization；不开始 8D。
