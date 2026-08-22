# 8C Reliable Runtime Core 设计

> 本文冻结 `8c-reliable-runtime-core` 的产品边界、数据模型、控制流、故障语义和测试矩阵。
> 它不表示实现或公共 CI 已完成。

## 1. 初学者心智模型

数据库里的 task 是工单，Worker 是接单的人，lease 是有失效时间的工作证，generation/token 是工作证的
代次和防伪码。heartbeat 是定期续证；fencing 是门禁只接受最新工作证。checkpoint 不是保存任意 Python
对象，而是“系统能够证明现在处于哪个安全边界”的版本化引用。durable event 是工单状态的流水账，
Runtime Trace 则是一次分析内部 Provider/Tool/Harness 的审计记录，两者职责不同。

## 2. 需求与边界

### 必须实现

- durable lifecycle event、SHA identity、task-local sequence、global replay cursor；
- lease/heartbeat/generation/token fencing；
- owner-scoped idempotent cancel request；
- body-free checkpoint 与保守恢复；
- receipt-proven reconciliation、safe requeue、recovery_required；
- late-result/duplicate-terminal rejection；
- owner/global active capacity 与安全 observability；
- 单 Worker/单 Runtime/现有 Harness 的离线纵向兼容。

### 本检查点不实现

- 产品 Multi-Agent、DAG、LangGraph/Pi/其他第三方 Runtime；
- Redis、Celery、Kafka、Kubernetes 或第二个任务真源；
- SSE、正式前端、Auth/RSO、HTTPS、备份副本擦除；
- 8D Riot + OP.GG EvidenceBundle；
- 真实 Riot、OP.GG、Provider、Key 或 held-out I/O。

## 3. 现有接缝

| 现有能力 | 接缝 | 8C 扩展 |
|---|---|---|
| task contract | `app/tasks/models.py` | reliable fields、cancel/event/checkpoint DTO |
| task port | `app/tasks/ports.py` | claim lease、heartbeat、checkpoint、cancel、recovery、replay |
| PostgreSQL | `task_record.py` / `task_repository.py` | 0010 migration、event table、fenced CAS |
| Worker | `app/workers/review_worker.py` | lease maintainer、安全 checkpoint、cancel precedence |
| recovery | `app/tasks/reconciliation.py` | expired lease coordinator 与 receipt/safe-checkpoint decision |
| Runtime Trace | `app/runtime/*` | 保持内部 Trace 事实源，不复制 event body |
| Harness | `app/harness/*` | 保持唯一发布权；receipt/artifact proof 继续严格验证 |
| API | `app/api/main.py` / `task_models.py` | owner-scoped cancel 与 cursor page，不做 SSE |

## 4. 数据结构

### `review_tasks` 新字段

```text
lease_generation        bigint not null default 0
lease_token             varchar(64) nullable       # private
lease_expires_at        timestamptz nullable
heartbeat_at            timestamptz nullable
cancel_request_id       varchar(128) nullable
cancel_requested_at     timestamptz nullable
cancel_reason           varchar(64) nullable
checkpoint_sequence     bigint not null default 0
checkpoint_reference    jsonb nullable              # strict/body-free
recovery_count          integer not null default 0
recovery_required_at    timestamptz nullable
recovery_reason         varchar(64) nullable
```

状态增加 `cancelled` 与 `recovery_required`。queued 没有 lease；running 必须有 generation/token/expiry；
recovery_required 保留历史 worker/generation，但 token/expiry 已清除；terminal 清除可用 lease，且成功/失败/
取消各自保持严格 projection shape。

### `review_task_events`

```text
event_cursor       bigint generated identity primary key
event_identity     char(64) unique not null
task_id            uuid not null references review_tasks on delete cascade
run_id             varchar(128) not null
owner_id           varchar(128) not null
task_sequence      bigint not null
event_kind         varchar(32) not null
status_after       varchar(24) not null
lease_generation   bigint not null
worker_id          varchar(128) nullable
operation_identity varchar(128) not null
reason             varchar(64) nullable
checkpoint_reference jsonb nullable
occurred_at        timestamptz not null
unique(task_id, task_sequence)
unique(task_id, operation_identity)
```

`event_identity` 是除 cursor 外 canonical envelope 的 SHA-256。读取时重算；cursor 只负责分页，不参与身份。
event 没有 request/report/Prompt/Provider/MCP body。

## 5. 控制流

### 创建与领取

```text
API → TaskService → PostgreSQL short transaction
    ├─ capacity + idempotency check
    ├─ insert queued task
    └─ append created event

Worker → claim_next
    ├─ SELECT queued FOR UPDATE SKIP LOCKED
    ├─ generation + 1, random private token, lease expiry
    ├─ claimed_safe checkpoint
    └─ append claimed event
```

### 执行、heartbeat 与终态

```text
Worker mark execution_started checkpoint (safe_replay=false)
  → bounded heartbeat loop while synchronous executor runs
  → Runtime → Harness → immutable Artifact/Trace/Receipt
  → final heartbeat/cancel check
  → terminal CAS(worker + generation + token + live lease + no cancel)
  → append exactly one terminal event in the same SQL transaction
```

旧 Worker 即使拿到完整 result，只要 lease 已过期、token 被清除、generation 已变化、cancel 已写入或状态已经
terminal，CAS 都返回 false；它不能追加 terminal event，也不能覆盖新结果。

### Cancel

```text
POST /tasks/{id}/cancel + Idempotency-Key
  queued  → cancelled + terminal event
  running → cancel_requested event; Worker heartbeat observes request
  terminal/recovery_required → stable disposition, no state rewrite
```

running cancel 不把进程信号当成 durable truth。Worker 在边界收敛 cancelled；若 Worker 已死，expired recovery
优先完成 cancelled。同步外部调用可能继续到返回，但 SQL success/fail 被 cancel CAS 阻断。

### Recovery

```text
scan expired lease (bounded, SKIP LOCKED candidate read)
  ├─ cancel requested          → cancelled
  ├─ strict terminal receipt  → reconciled succeeded
  ├─ latest claimed_safe only → requeue, invalidate token, recovery_count + 1
  └─ unknown/started/max retry→ recovery_required
```

Recovery 先读有限候选，再在文件系统事务外验证 Receipt/Trace/Artifact，最后以 expected generation/token/status
做短 CAS。验证期间发生的并发 terminal 会让 CAS 安全失败。

### Replay

owner-scoped query 使用 `after_cursor`（默认 0）和 1–100 的 limit；结果返回 events、`next_cursor` 与
`has_more`。pure projector 校验 identity、identity tuple、task sequence、状态转换和 duplicate terminal。
8E 可以基于同一 cursor 加 SSE，而不用重定义状态。

## 6. 故障与安全语义

| 故障/竞态 | 结果 |
|---|---|
| 同 task 两 Worker claim | `SKIP LOCKED` + row state，只一张 lease |
| 同 worker_id 重启 | generation/token 不同，旧实例被 fenced |
| heartbeat 超时 | 旧 terminal 因 lease 过期拒绝 |
| cancel 与 success 竞争 | 同一 row CAS 决定线性顺序；cancel 先写则 success 不可提交 |
| recovery 与迟到 terminal 竞争 | expected status/generation/token 只允许一方成功 |
| terminal 重试 | terminal status + unique event operation identity 阻止第二终态 |
| event 重试 | `(task_id, operation_identity)` 与 SHA identity 幂等 |
| event/body 注入 | strict enum/size/field shape，公共 replay body-free |
| Receipt 缺失或漂移 | 不自动重跑，进入 recovery_required |
| event consumer 断线 | 使用 cursor 重放；不依赖进程内队列 |

## 7. 测试矩阵

- pure contracts：event identity、projector、lease/checkpoint/cancel shape、非法 token/body/sequence/terminal；
- migration/metadata：0010 upgrade/downgrade/reupgrade、约束/索引/FK、legacy snapshot bootstrap；
- PostgreSQL repository：claim generation/token、heartbeat、checkpoint、cancel、terminal fencing、event replay；
- concurrency：双 claim、cancel-vs-terminal、recovery-vs-late-result、duplicate terminal；
- Worker：heartbeat lifecycle、cancel precedence、lost lease、executor error、Harness terminal compatibility；
- recovery：receipt success、claimed_safe requeue、started→recovery_required、max recovery、expired cancel；
- API：owner 404、cancel idempotency、terminal disposition、cursor/limit/body-free；
- vertical/package：Fake/fixture no-I/O Worker → Runtime/Harness terminal → task/event query；
- exit：完整 pytest、真实 PostgreSQL job、Linux package、RAG、Harness dry-run、compileall、secret/body scan、
  governance、diff check 和 exact-SHA 三 job。

## 8. 当前限制

- 没有通用 mid-step resume；只有 claimed-safe restart 与 receipt-proven projection 自动化；
- 线程 heartbeat 不能强制中断已进入第三方库的同步调用，只能 fence 其最终提交；
- event replay 先提供 Repository/API page，不在 8C 实现 SSE；
- 单区域 PostgreSQL 仍是单控制面，不声称跨地域容灾、99.9% SLA、RPO/RTO；
- terminal assistant 的既有同步 projection 保持兼容，后续若观察到投影丢失 Bad Case，再采用 durable outbox，
  不在本批扩张。
