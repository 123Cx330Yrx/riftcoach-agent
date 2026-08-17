# 6A-entry-design：FastAPI + PostgreSQL 持久任务模型设计

## 1. 结论

6A 将 5P 已验证的同步、文件型近期复盘切片演进为一个持久异步任务基座：

```text
FastAPI 创建 queued task
→ PostgreSQL 持久化 task_id/run_id/owner/idempotency
→ polling Worker 原子 claim
→ 现有 RecentReviewApplicationService
→ AgentRuntimeV1 + ReviewHarness
→ Artifact / Trace / immutable receipt
→ PostgreSQL 终态投影
→ task/run/report 查询
```

架构保持模块化单体。API 与 Worker 是同一仓库、同一产品部署中的两个进程角色，不拆业务微服务，
不增加 Redis、Celery、Kafka 或 RabbitMQ。PostgreSQL 是唯一生产语义基线；SQLAlchemy 2 负责同步
映射，Alembic 负责 migration，关键语义只认真实 PostgreSQL Docker/CI 证据。

本设计由用户逐节确认。它只关闭 `6A-entry-design`，不直接实现 SQL、Session、Memory、SSE、正式
Auth、前端、真实 Provider 或公网部署。

## 2. 初学者理解：为什么 Agent 需要任务系统

现有 RiftCoach Agent 已经拥有 Domain、RAG、Skill、AgentLoop、ToolRuntime、Harness、Trace 和
Artifact，但同步 API 的一次 HTTP 请求必须一直等完整 Agent 运行：

```text
用户请求
→ Riot 数据
→ 确定性分析
→ Skill / Agent / Tool / RAG
→ Harness 评测与发布
→ HTTP 返回
```

Agent 和普通 CRUD 的区别是：一次运行可能较慢、依赖多个外部组件、可能降级或拒绝发布，而且必须
保留“执行到了哪里、为什么停止、结果是否可信”的证据。任务系统把“用户请求”和“长运行”解耦：

- HTTP 负责可靠接收和返回 task identity；
- Worker 负责执行；
- PostgreSQL 负责生命周期和 ownership；
- Runtime/Harness 负责 Agent 控制与唯一发布；
- Artifact/Trace 负责大正文和证据。

polling Worker 不是 Multi-Agent。Worker 是普通后台执行进程；Agent 仍是现有单 Agent Runtime。

## 3. 当前基线与真实缺口

### 已有能力

- `RecentReviewProductRequest` 严格校验 Riot ID、count、queue 和 focus；
- `RecentReviewApplicationService` 拥有 Summary → deterministic report → compiler → Runtime → receipt
  的用例顺序；
- `AgentRuntimeV1` 统一两个真实 Skill、Tool、Provider observation、Usage、Trace 和终态；
- `ReviewHarness` 保持唯一评测/修订/发布权；
- file receipt/query 会重新核对 Trace、manifest 与 final Artifact；
- FastAPI Adapter 已有同步 POST、run/report 查询、OpenAPI 和安全错误映射测试。

### 尚缺能力

- durable queued/running task；
- owner-scoped HTTP idempotency；
- PostgreSQL schema 与 migration；
- 多 Worker 原子 claim；
- API/Worker composition 与 lifecycle；
- SQL/Artifact crash reconciliation；
- readiness、背压、保留/删除与产品 NFR；
- 真实 PostgreSQL CI 和本地运行包。

EchoMind 的 lifespan 与 user/conversation 分层可作为思想参考，但其全局组件、宽泛 CORS、Redis/Chroma
和非持久 `asyncio.create_task()` 不迁移。Saber/Sea 的 lease、DAG、取消、恢复和迟到结果隔离留阶段 8。

## 4. 总体架构

```text
Client
  │ POST /reviews/recent + Idempotency-Key
  ▼
FastAPI
  ├─ trusted ActorContext
  ├─ strict Product Request
  └─ short create transaction
          │
          ▼
PostgreSQL review_tasks  ◄──────── GET /tasks/{task_id}
          │
          │ SELECT ... FOR UPDATE SKIP LOCKED
          ▼
Polling Worker
  ├─ claim transaction
  ├─ RecentReviewApplicationService（事务外）
  │    ├─ Riot/Summary/Deterministic Report
  │    ├─ Compiler + AgentRuntimeV1
  │    ├─ RAG / Tool / Provider
  │    └─ ReviewHarness
  ├─ Artifact / Trace / immutable receipt
  └─ terminal transaction
          │
          ▼
GET /runs/{run_id} / GET /runs/{run_id}/report
```

### 组件职责

| 组件 | 负责 | 不负责 |
|---|---|---|
| FastAPI | HTTP 校验、ActorContext、task create/query、safe errors | Riot/Agent/Harness 业务 |
| Task Application Service | idempotency、容量、owner、状态投影 | SQL 细节、报告生成 |
| PostgreSQL Repository | transaction、constraints、claim、CAS | Prompt/报告正文 |
| Polling Worker | claim、调用用例、终态协调、退避 | Agent 决策、发布判定 |
| RecentReviewApplicationService | 现有产品用例顺序 | task queue/HTTP |
| AgentRuntimeV1 | Agent/Tool/Usage/Trace | HTTP ownership |
| ReviewHarness | 评测、受限修订、发布/降级/拒绝 | task lifecycle |
| Artifact/Trace | 运行内容、证据、SHA | durable queue |

SQLAlchemy 使用同步 Session。FastAPI 的同步 route 在线程池执行短数据库操作，Worker 原生同步调用
现有 Application/Runtime；当前不引入 async ORM 的第二套控制模型。

## 5. Task schema 与状态机

### 双身份

- `task_id`：排队任务；
- `run_id`：Runtime/Artifact；
- 两者在 create transaction 中由服务器预留；
- Worker 必须把持久化 run_id 传入 compiler/Application，不能再次随机生成。

### 逻辑字段

| 分组 | 字段 |
|---|---|
| identity | `task_id`, `run_id`, `task_kind`, `schema_version` |
| ownership | `owner_id`, `worker_id` |
| idempotency | `idempotency_key`, `request_fingerprint` |
| input | normalized `request_payload` JSONB |
| lifecycle | `status`, `created_at`, `updated_at`, `claimed_at`, `finished_at` |
| terminal | `terminal_reason`, `publication_status`, `report_available` |
| evidence | body-free `trace_reference`, receipt/artifact SHA |
| operations | deletion/recovery advisory metadata；不是第五种 task 状态 |

建议索引/约束：

- primary key `task_id`；
- unique `run_id`；
- unique `(owner_id, idempotency_key)`；
- claim index `(status, created_at, task_id)`；
- owner list index `(owner_id, created_at desc)`；
- status、时间与 terminal projection 的 CHECK/invariant。

### 状态机

```text
queued
  │ atomic claim
  ▼
running
  ├─ succeeded
  └─ failed
```

- 不允许 terminal → nonterminal；
- 不允许 6A task 自动重试或 running → queued；
- Worker 终态更新必须匹配当前 worker ownership；
- task succeeded 表示运行形成合法终态；publication 仍可 published/degraded/rejected；
- failed 表示没有形成合法 Runtime terminal，而不是 Harness 对草稿质量的拒绝。

## 6. 事务、幂等与两存储协调

### 创建事务

1. 从可信 ActorContext 取得 owner；
2. 校验 Idempotency-Key 与 Product Request；
3. canonicalize 请求并计算 SHA-256 fingerprint；
4. 检查 owner 非终态容量；
5. 插入 queued task、task_id 与 run_id；
6. 唯一冲突时复读原 row：同 fingerprint 返回原 task，不同 fingerprint 返回 409；
7. commit 后才返回 202。

若 commit 成功但 HTTP 响应丢失，客户端重发同 Key 会得到同一 task，不会重复执行。

### claim 事务

```sql
SELECT ...
FROM review_tasks
WHERE status = 'queued'
ORDER BY created_at, task_id
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

同一短事务写入 running/worker_id/claimed_at 后立即 commit。Agent 执行期间无行锁。

### 终态事务

Application/Runtime 先原子写 Artifact、Trace 和 immutable receipt；Worker 验证 run_id/reference/SHA 后，
使用 `WHERE task_id=? AND status='running' AND worker_id=?` 条件更新 terminal。影响行数不是 1 就 fail
closed，迟到 Worker 不能覆盖。

### hard-crash 方案 A

- receipt 已存在且完整：自动补齐 succeeded；
- graceful shutdown：owner Worker 可安全写 failed/interrupted；
- 无 receipt hard crash：保持 running，只投影 recovery-required；
- 运维确认 owner 已死后，通过受限命令 CAS 为 failed；
- 不自动重跑，不在 6A 构建 lease/heartbeat/fencing。

## 7. HTTP 合同与失败语义

```text
POST /reviews/recent
GET  /tasks/{task_id}
GET  /runs/{run_id}
GET  /runs/{run_id}/report
GET  /health/live
GET  /health/ready
```

保留业务 POST path，但 response 升级为异步 task receipt。5P 同步合同是本地历史 V1，6A 必须版本化
OpenAPI/Schema 演进，不能静默声称向后兼容。

| 场景 | HTTP/资源语义 |
|---|---|
| invalid request | 422，不创建 task |
| same key + different fingerprint | 409，不创建 task |
| PostgreSQL unavailable | 503，不假装已入队 |
| committed create/replay | 202 + task_id/run_id/status/links |
| task queued/running/succeeded/failed | GET task 200 + safe projection |
| not found or not owned | 统一 404 |
| report not ready/unavailable | 409 |
| Artifact identity/SHA failure | 500 integrity_failed，不返回正文 |

Worker、SQL URL、异常堆栈、Provider body、Prompt、Riot ID 不进入公共错误。

## 8. NFR

| 维度 | 目标/边界 |
|---|---|
| initial deployment | 单服务器 API + 1 Worker + PostgreSQL |
| worker concurrency | 每进程默认 1；可增加进程，不改业务代码 |
| correctness | 两 Worker 真库 claim 无重复 |
| HTTP performance | warm-DB create/query server p95 `<300ms` |
| claim latency | 容量可用时 p95 `<2s` |
| backpressure | owner 3/global 50 nonterminal，配置化 |
| polling | idle exponential/backoff + jitter |
| health | liveness 与 DB/Alembic readiness 分离 |
| observability | task/run/status/latency/safe counts，body-free |
| availability | 不承诺 99.9%，单主机/单 DB/本地 Artifact 是单点 |
| cost | 无额外 Broker/queue service |

性能数字是后续必须测量的目标，不是 entry design 已有证据；Agent/Riot/Provider 总时长不计入 HTTP
create/query p95，继续由 Skill/Runtime budget 和 timeout 约束。

## 9. 安全与数据生命周期

### 安全

- owner 只来自服务器 ActorContext，不接收正文 owner_id；
- local fixed owner 只在开发/测试 profile 可用；production 缺 Auth Provider fail closed；
- 所有资源查询 owner-scoped，不存在/越权统一 404；
- CORS 默认关闭，禁止 production wildcard + credentials；
- SQLAlchemy 参数化查询，不拼 SQL；
- `.env`、Riot/Provider/DB Secret 不进 SQL、Artifact、日志、Git；
- 日志不保存 Riot ID、Prompt、报告、Tool body、异常栈或 Provider body；
- 公开部署前 Auth、HTTPS、限流和安全响应头仍是硬门。

### 生命周期

| 数据 | 默认保留 |
|---|---:|
| Riot 原始 cache | 7 天 |
| terminal task/run/Artifact/Trace | 90 天 |
| 安全运维日志 | 30 天 |
| 长期玩家 Memory | 6A 不创建 |

terminal owner delete 先使内容不可访问，再清理 SQL payload/Artifact/Trace；跨存储删除必须幂等并记录
安全补偿状态。active delete 不等于 cancel，6A 拒绝该操作。真正 cancel/resume 留阶段 8。

## 10. 测试矩阵

| 层 | 证据 |
|---|---|
| pure/Fake | 状态、fingerprint、owner、error、retention config |
| PostgreSQL repository | Alembic、constraints、rollback、UTC/JSONB、idempotency |
| concurrency | 两 Session/Worker barrier + SKIP LOCKED，exactly-once claim |
| API | 202/422/409/503、owner 404、task states、report 409、readiness |
| Worker | success/degraded/rejected/failed、CAS、shutdown、reconciliation/manual recovery |
| offline product | PostgreSQL + current Application + local RAG + Fake Provider + Runtime/Harness + Artifact |
| security/lifecycle | Secret/log/CORS/owner/delete/retention |
| performance | create/query p95、claim delay、backpressure、polling behavior |

GitHub Actions 增加 PostgreSQL service/container 阻塞 job；SQLite 不参与关键语义验收。并发测试使用
barrier 与独立 Session，不靠长 `sleep`。CI 不读取 `.env`，不调用 Riot/GLM/DeepSeek。

## 11. 原子实施顺序

### 6A-1 PostgreSQL Foundation

SQLAlchemy/Alembic/psycopg、配置、真实 PostgreSQL dev/CI、initial migration。

### 6A-2 Task Contract & Repository

双身份、四态、owner、idempotency、capacity、create/query 与真库约束/事务。

### 6A-3 Atomic Claim & Polling Worker

SKIP LOCKED、ownership/CAS、backoff/jitter、graceful shutdown 与两 Worker 测试。

### 6A-4 Application & Artifact Integration

预留 run_id 贯穿 Application/Runtime、receipt/Trace terminal、reconciliation 与人工恢复。

### 6A-5 Async FastAPI & Composition

POST 202、task query、ActorContext、lifespan、live/ready 与版本化 OpenAPI。

### 6A-6 Security, Lifecycle & NFR

CORS/log/Secret、背压、retention/delete、metrics 与 benchmark。

### 6A-7 Packaging & Exit Review

Compose API/Worker/PostgreSQL、CI、Linux smoke、完整回归、文档和 exit matrix。

每个子阶段先教学、再红灯、最小实现、聚焦/完整门禁、提交/推送/exact-SHA CI，并单独更新 canonical。

## 12. 明确不在 6A

- Session、conversation、working/episodic/profile/training Memory；
- 正式 JWT/OAuth、多用户公网 Auth；
- SSE、正式前端和公网发布；
- task 自动 retry、lease、heartbeat、fencing、cancel/resume、checkpoint；
- Multi-Agent、DAG、LangGraph、MCP；
- Pi 产品 Runtime、模型分层或新 Provider 真实质量门；
- 真实 Riot/Provider 调用和生产 SLA。

## 13. 入口设计退出条件

`6A-entry-design` 只有在以下条件同时成立后关闭：

- ADR-0038、本文和 implementation plan 一致；
- canonical/roadmap/capability/project decisions 无冲突；
- governance、diff、compile/现有回归与安全门通过；
- 提交推送后 exact-SHA GitHub Actions 成功；
- 下一 checkpoint 只交接 `6A-1-postgresql-foundation` 准备状态，不自动实施。
