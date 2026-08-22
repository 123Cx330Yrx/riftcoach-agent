# 8C Reliable Runtime Core：从“任务在跑”到“任务可证明地活着”

这份材料是 `8c-reliable-runtime-core` 的八维学习与工程证据。它解释本轮实际实现、代码入口、
验证方法和不能夸大的边界。设计依据是 [ADR-0054](../adr/0054-adopt-postgresql-leased-fenced-task-control-plane.md)
与 [8C 专用设计](../plans/2026-08-22-8c-reliable-runtime-core-design.md)。

## 1. 问题与原理

### 1.1 原来的缺口

阶段 6 已经能把任务可靠入队、由 PostgreSQL `SKIP LOCKED` 领取，并在完整 Receipt、Trace、Artifact
证据存在时补齐成功。但一个 `running` 任务没有租约和心跳：Worker 硬崩溃后，系统不能区分“还在执行”
和“永远不会回来”；同名 Worker 重启后，旧进程的迟到结果也缺少执行代次隔离。取消请求和可重放的任务
生命周期历史也不存在。

### 1.2 五个基础概念

- **Lease（租约）**：Worker 对任务的所有权只在有限时间内有效；心跳可以延长它。
- **Fencing（栅栏）**：每次领取生成更大的 generation 和私有 token。终态写入必须同时匹配
  worker、generation、token、未过期租约和无 cancel；旧执行即使回来也写不进去。
- **Checkpoint（检查点）**：不是序列化任意 Python 内存，而是一个严格、body-free 的安全边界引用。
  `claimed_safe` 表示还没有开始外部副作用，可以重排队；`execution_started` 表示不能盲目重跑。
- **Durable task event（持久任务事件）**：PostgreSQL 中的控制面流水，只说明 created/claimed/
  heartbeat/cancel/recovery/terminal，不复制 Prompt、Provider 或报告正文。
- **Recovery proof（恢复证明）**：自动动作必须由 strict terminal Receipt 或 `claimed_safe` checkpoint
  支持；不知道外部副作用是否发生时进入 `recovery_required`。

这和 Runtime Trace 是两层事实：task event 回答“谁在什么租约下把任务推进到了什么状态”；Runtime
Trace 回答“一次分析内部调用了什么 Provider/Tool、Harness 最后如何裁决”。混成一个日志会产生双真源。

## 2. 设计与实际实现

8C 沿用 PostgreSQL 单一控制面，没有引入 Redis、Celery、Kafka、DAG Runtime 或 Multi-Agent。

### 2.1 严格合同

`app/tasks/reliable_runtime.py` 提供：

- `TaskLeasePolicy`：租约、心跳、恢复批次和最大恢复次数；心跳周期最多为租约的三分之一；
- `TaskLease`：私有 64 位十六进制 token，序列化和 repr 默认排除；
- `TaskCheckpointReference`：只允许 `claimed_safe` 与 `execution_started` 两种安全阶段；
- cancel、heartbeat、recovery 的 typed disposition；
- `TaskLifecycleEvent`：canonical envelope 的 SHA-256 identity；
- `TaskEventPage` 与 `project_task_lifecycle()`：拒绝身份漂移、乱序、非连续 task sequence、跨 task
  混页、迟到或重复 terminal。

event identity 覆盖 event/checkpoint 时间戳，但不覆盖数据库生成的 global cursor。cursor 用于分页；identity
用于证明事件内容没有被篡改。

### 2.2 PostgreSQL projection 与事件表

Alembic `0010_reliable_runtime_core` 扩展 `review_tasks`，增加 generation/token/expiry/heartbeat、cancel、
checkpoint 与 recovery 字段，并把 status 列扩为 24 字符以容纳 `recovery_required`。新增
`review_task_events`：global identity cursor、task-local contiguous sequence、operation identity、事件
SHA 和 body-free checkpoint reference 都有约束、唯一键和索引。

升级时，legacy `running` 不能假装仍有合法租约，因此迁移为 `recovery_required`；每条旧 task 生成
`snapshot_imported` 事件。降级时，`cancelled`/`recovery_required` 安全投影为旧 schema 可表达的
`failed`，不会把 pre-claim cancel 复活成 queued。

### 2.3 Repository 的短事务语义

`PostgresTaskRepository` 把 task 当前 projection 与对应 event 放进同一事务：

- create 同事务追加 `created`；
- claim 递增 generation、生成私有 token、写 lease 与 `claimed_safe` checkpoint，再追加
  `claimed + checkpointed`；
- heartbeat/checkpoint 只接受 live fenced identity；
- queued cancel 直接 terminal，running cancel 先持久化 request；
- succeed/fail/cancel terminal 都要求 live lease，清除可用 token，并在同一事务追加唯一 terminal；
- event 读取 owner-scoped、cursor-bounded，并在映射时重算 SHA；
- expired recovery 的候选扫描与最终 CAS 分开，文件证据验证不占数据库事务。

`(task_id, operation_identity)` 让同一个操作可以幂等复读；若相同 identity 对应不同 envelope，整个事务
fail closed，而不是静默接受碰撞。

### 2.4 Worker、恢复和 HTTP

`ReviewWorker` 在执行前写 `execution_started` checkpoint，执行期间用标准库后台线程做 bounded heartbeat，
结束后再做一次 final heartbeat/cancel check。success/failure CAS 若被最后一瞬 cancel 抢先，会再尝试 fenced
cancel；若 generation/token/status 已被 recovery 改变，则返回 `ownership_lost`，不写 terminal turn。

每轮 claim 前，production composition 先运行有限 expired recovery：

1. 有 cancel request → expired fenced cancel；
2. strict Receipt/Trace/Artifact terminal → reconciled success；
3. 最新 checkpoint 是 `claimed_safe` 且未超过次数 → 清旧 token并 requeue；
4. 其余 → `recovery_required`，等待受限人工裁决。

HTTP 新增 `POST /tasks/{task_id}/cancel` 与 `GET /tasks/{task_id}/events`。owner 来自 trusted
`ActorContext`；公共 event 不暴露 owner、worker、checkpoint、lease token、内部 operation identity、请求正文
或 PUUID。它是 cursor page，不是 SSE；SSE 留给 8E。

## 3. 代码地图

| 层 | 文件 | 主要职责 |
|---|---|---|
| pure domain | `app/tasks/reliable_runtime.py` | lease/checkpoint/event/page/projector |
| task domain/port | `app/tasks/models.py`, `app/tasks/ports.py` | 新状态、可靠字段和 Repository seam |
| ORM/migration | `app/persistence/task_record.py`, `task_event_record.py`, `migrations/versions/0010_reliable_runtime_core.py` | 当前 projection、append-only event、legacy 迁移 |
| Repository | `app/persistence/task_repository.py` | 原子 event、lease/fencing/cancel/replay/recovery CAS |
| Worker | `app/workers/review_worker.py`, `app/workers/composition.py` | execution checkpoint、heartbeat、cancel precedence、bounded recovery |
| recovery | `app/tasks/reconciliation.py` | Receipt/safe-checkpoint 证明与人工 generation CAS |
| service/API | `app/tasks/service.py`, `app/api/task_models.py`, `app/api/main.py` | owner-scoped cancel/event page 与安全投影 |
| package/CI | `scripts/run_packaging_smoke.py`, `.github/workflows/tests.yml` | 安装后 no-I/O task/event 纵向与真库测试清单 |

专用测试是：

- `tests/test_reliable_task_contracts.py`
- `tests/test_reliable_task_migrations_postgres.py`
- `tests/test_reliable_task_repository_postgres.py`
- `tests/test_reliable_review_worker.py`
- `tests/test_reliable_task_recovery.py`
- `tests/test_reliable_task_recovery_postgres.py`
- `tests/test_reliable_task_api.py`

## 4. 数据流与控制流

### 4.1 正常失败纵向（package no-I/O）

```text
POST /reviews/recent
  → review_tasks(queued) + created event
  → Worker claim(generation=1, private token, expiry)
  → claimed + claimed_safe checkpoint events
  → execution_started checkpoint
  → executor 的预期 no-I/O failure
  → final heartbeat
  → fenced failed terminal + failed event
  → GET /tasks/{id}
  → GET /tasks/{id}/events?after_cursor=0&limit=100
```

package smoke 只证明可重建 Linux image 中 API、PostgreSQL、Worker 和 replay 接缝能协同；故意失败的
executor 不证明 Riot/Provider 成功。

### 4.2 Cancel 与迟到结果

```text
owner cancel request → row lock → cancel_requested event
                             ↓
Worker final heartbeat sees cancel → fenced cancelled terminal

若旧 executor 随后返回：
success/fail CAS sees cancelled / missing token → false → no second terminal
```

### 4.3 过期恢复

```text
bounded expired scan
  → transaction closes
  → verify immutable Receipt/Trace/Artifact outside SQL transaction
  → short expected worker+generation+token+expired-status CAS
```

验证期间如果活 Worker 已提交 terminal，最终 CAS 返回 ownership lost；两方不会同时获胜。

## 5. 验证证据

### 5.1 真实 TDD 红灯

本轮保存的红灯包括：缺 `app.tasks.reliable_runtime`、缺 recovery coordinator、缺 cancel/event routes、
事件时间篡改未进入 identity、`recovery_required` 超过旧 `varchar(16)`、Worker 最后一瞬 cancel/terminal
竞态、queued cancel lifecycle 不一致，以及公共 event 暴露 internal operation identity/package 未查询 replay。

最后两项补强的定向红灯为 `2 failed`，最小修复后 `tests/test_reliable_task_api.py +
tests/test_packaging_smoke.py` 为 `29 passed`。

### 5.2 本地证据

最新完整 Windows 本地回归：`1672 passed, 134 skipped, 1 warning, 127 subtests passed`。134 个 skip
主要是本机无 PostgreSQL/Docker/Linux 条件；它们不能写成“本地真库已通过”。pure、Worker、Fake API、
offline migration 和普通回归已经执行；0010 真迁移、并发 fencing/recovery 和 Linux package 必须由同一
implementation SHA 的公共 `postgres-migrations`、`packaging-smoke` 补证。

上一版 implementation SHA 的公共 CI 先暴露了两个真实 PostgreSQL 边界问题：Alembic downgrade 对已经带
命名 convention 前缀的约束名重复套前缀，以及 SQLAlchemy JSONB 把 queued checkpoint 的 Python `None`
编码成 JSON `null`。本轮分别用 `op.f()` 和 `JSONB(none_as_null=True)` 修复，并增加离线 downgrade、metadata
与 queued insert 回归；这些修复仍待 repair SHA 的公共真库/Linux job 证明。

随后 repair SHA 的真库门又证明：旧终态记录不应被强制补写运行期 heartbeat 或虚构新的 generation；而 JSONB 中的 checkpoint 时间戳
读回是 JSON 字符串，不能直接喂给 strict Pydantic dict validation。现在终态 CHECK 允许 heartbeat 为空，
允许 legacy generation 0，Repository 通过 strict JSON wire parsing 还原 checkpoint；这保留了运行期 fencing 要求，也兼容既有终态投影。

requeue、task read 和 event replay 三条 JSONB 读回路径现在共享同一 parser；它同时处理普通 JSON mapping 和
psycopg `Jsonb` wrapper，仍以严格 JSON Schema 解析，不把任意 Python 类型默默强转。

task row 与 event row 的可空 checkpoint 也统一使用 SQL `NULL` 映射；这样 created/claimed/failed 等无 checkpoint
事件不会在数据库中留下 JSON `null` 伪对象，replay 只面对明确的空值或严格 checkpoint object。

package smoke 的失败诊断只允许 status、allowlisted error code 和 JSON 顶层 key，不打印 event body、owner、
checkpoint、request payload 或内部异常；它用于定位部署接缝，不改变 API 的 body-free 错误合同。

### 5.3 公共关闭门

8C 只有在同一 implementation/evidence SHA 的以下三 job 全部成功后才能关闭：

- `pytest`：完整 Python 回归、RAG、Harness 和安全边界；
- `postgres-migrations`：PostgreSQL 17 上 0001→0010 upgrade/downgrade/reupgrade、metadata=head、
  Repository 并发和 recovery 竞态；
- `packaging-smoke`：Linux 非 root image、no-I/O Worker terminal 与 body-free event replay。

公共门前 `docs/learning/coverage.yaml` 必须保持 `planned`。

## 6. Runbook

### 6.1 开发者复核

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_reliable_task_contracts.py tests/test_reliable_review_worker.py tests/test_reliable_task_recovery.py tests/test_reliable_task_api.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe -m pip check
python scripts/check_project_governance.py
git diff --check
```

### 6.2 运行配置

production Worker 可以配置：

- `RIFTCOACH_WORKER_LEASE_SECONDS`（15–3600，默认 120）；
- `RIFTCOACH_WORKER_HEARTBEAT_SECONDS`（默认 30，且三倍不超过 lease）；
- `RIFTCOACH_WORKER_RECOVERY_BATCH_SIZE`（1–100，默认 25）；
- `RIFTCOACH_WORKER_MAX_RECOVERIES`（0–25，默认 3）。

配置在构造 Engine/Provider 前严格校验。不要通过直接 SQL 把 `recovery_required` 改回 queued；当前没有公开
operator API，人工失败裁决必须使用受限的 generation+worker CAS seam，且不能把未知副作用任务重跑。

### 6.3 API 使用

```http
POST /tasks/{task_id}/cancel
Idempotency-Key: cancel-safe-id-1

GET /tasks/{task_id}/events?after_cursor=0&limit=50
```

`cancel` 的 200 只说明取消已立即完成或已持久请求；不代表正在进行的第三方同步 HTTP 已被强杀。event
page 用 `next_cursor` 继续读；它不包含正文，也不是实时推送。

## 7. 失败、安全与范围边界

- lease token 是 private capability：不进入 public DTO、event、Trace、日志或 repr；
- cancel 与 terminal/recovery 在同一 task row 上线性化，谁先满足 CAS 谁提交；
- event SHA、task-local sequence 和 operation identity 共同防漂移/重复，但数据库并非不可攻破的外部
  transparency log；
- heartbeat 线程只能维持租约和观察 cancel，不能强制中断任意阻塞 C 扩展或已发出的网络请求；
- `claimed_safe` 只支持从领取边界重启，不是通用 mid-step resume；
- strict Receipt 只允许投影已有完整终态，不允许重新调用模型；
- unknown/missing/drifted evidence 一律 `recovery_required`，不会为了“自动恢复率”盲目重跑；
- PostgreSQL 仍是单区域单控制面，不声称跨地域 HA、99.9% SLA、RPO/RTO；
- 8C 没有实现 SSE、前端、正式 Auth、备份擦除、8D Evidence fusion、Multi-Agent 或 DAG。

## 8. 面试准确表述

可以说：

> 我在 PostgreSQL task control plane 上增量实现了 lease、heartbeat、generation+private-token fencing、
> append-only body-free lifecycle event、owner-scoped cursor replay、持久 cancel 和 proof-based recovery。
> Worker 的迟到 terminal 必须通过 live lease CAS；自动恢复只接受 strict terminal Receipt 或
> claimed-safe checkpoint，未知副作用进入 recovery-required。纯逻辑、故障注入、真实 PostgreSQL migration/
> concurrency 和 Linux package 分层验证，Runtime Trace 与 task lifecycle event 保持两个事实层。

不能说：

- “实现了任意步骤断点续跑”——只支持 claimed-safe restart 和 receipt-proven projection；
- “取消能立即停止模型请求”——当前是持久请求与终态 fencing；
- “用了事件溯源/DAG/分布式队列”——本轮明确没有；
- “实现了生产级高可用”——没有跨地域、备份 restore、RPO/RTO 或 SLA 证据；
- “Multi-Agent 提升了可靠性”——8B 已根据唯一 holdout reject 产品 Multi-Agent，8C 是单 Runtime 可靠控制面。
