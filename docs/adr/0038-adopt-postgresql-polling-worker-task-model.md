# ADR-0038：采用 PostgreSQL polling worker 持久任务模型

- 状态：Accepted
- 日期：2026-08-17
- 范围：`6A-entry-design`

## 背景

5P 已形成同步、文件型的近期复盘产品切片：FastAPI handler 调用
`RecentReviewApplicationService`，Application Service 依次收集确定性数据、生成确定性报告、编译
Runtime 请求、执行 `AgentRuntimeV1`，最后写入 immutable receipt。这个切片证明了产品层接线，但
没有证明生产任务持久化：

- POST 会被完整 Agent 运行阻塞；
- Trace 已写而 file receipt 未写时存在 crash window；
- 文件存储不能让多个 Worker 原子领取同一任务；
- 没有 HTTP 幂等、owner-scoped task、迁移、SQL 事务或恢复接缝；
- FastAPI `BackgroundTasks`/`asyncio.create_task()` 不能在进程重启后保存 ownership。

阶段 6 需要把脚本/同步切片演进为可查询、可隔离的长期 Coach 产品入口，但当前个人项目规模不需要
Redis、Celery、Kafka、微服务或阶段 8 的完整 lease/fencing runtime。

## 决策

### 1. PostgreSQL 是唯一生产语义基线

- SQL 映射使用 SQLAlchemy 2，同步 Session 与同步 psycopg driver；
- Schema migration 使用 Alembic；
- 普通领域逻辑可以用 Fake/单元测试；
- migration、事务、唯一约束、JSONB 和并发 claim 必须用真实 PostgreSQL Docker/CI 验证；
- SQLite 不能作为 PostgreSQL 语义的替代绿灯。

同步 SQLAlchemy 与现有同步 Application/Runtime、独立 Worker 模型一致。当前没有足够并发证据引入
异步 ORM；若未来 API 数据库等待成为实测瓶颈，再通过新 ADR 评估。

### 2. 保持模块化单体，使用独立 polling Worker

FastAPI 与 Worker 在同一仓库、同一产品部署中使用同一 Application/Domain 代码，但作为不同进程
角色运行：

```text
POST /reviews/recent
→ FastAPI 短事务写 queued task
→ 202 + task_id/run_id

PostgreSQL polling Worker
→ FOR UPDATE SKIP LOCKED 原子 claim
→ 短事务 queued → running
→ 事务外调用 RecentReviewApplicationService
→ Artifact/Trace/receipt
→ 短事务写 succeeded/failed
```

不引入 Redis、Celery、RabbitMQ 或 Kafka。PostgreSQL task table 同时是 durable queue 与 task 查询
事实源，但不成为 Prompt/报告正文仓库。

### 3. 任务使用双身份与四态状态机

- `task_id` 标识排队任务；
- `run_id` 标识 Runtime/Artifact 执行；
- 二者均由服务器在入队时生成并持久化；
- `owner_id` 来自可信 `ActorContext`，不能从用户 JSON 正文读取；
- `owner_id + idempotency_key` 唯一，请求 canonical fingerprint 用于检测 Key 重用冲突；
- V1 状态只允许 `queued → running → succeeded|failed`，终态不可逆；
- task succeeded 表示 Runtime/Harness 形成合法终态，不等于 publication published；
- publication 继续使用 `published/degraded/rejected` 独立投影。

SQL 保存规范化小输入、身份、ownership、状态、时间、幂等、safe terminal、publication 与 body-free
Artifact 引用；Prompt、Provider 原始响应、报告、Tool 正文和异常堆栈继续由 Artifact/Trace 或安全
日志边界管理，不进入 task row。

### 4. 所有数据库事务必须短小

创建、claim、终态更新分别使用短事务。Agent、Riot、Tool、RAG、Provider 与 Harness 执行期间不能
持有数据库锁。终态更新必须同时匹配 `task_id + status=running + worker_id`，旧 Worker 或迟到结果
不能覆盖当前状态。

Artifact/Trace 是运行内容与完整性的事实源；SQL 是任务生命周期的事实源。两者通过 `run_id`、
body-free reference 与 SHA 交叉验证。只有匹配的 immutable receipt/Trace/Artifact 才允许写入或补齐
success。

### 5. hard crash 采用保守恢复方案 A

- 匹配 immutable receipt/identity/SHA 时，reconciler 可以自动补齐 succeeded；
- graceful shutdown 时，owner Worker 可以条件更新为 `failed/worker_interrupted`；
- hard crash 且无终态证据时，不自动判死、不自动重跑；只形成 `recovery_required` 运维提示；
- 运维确认 owner Worker 已死亡后，受限命令通过 status/worker 条件更新为 failed；
- lease、heartbeat、fencing token、自动 reclaim、cancel/resume 与迟到结果隔离留到阶段 8。

### 6. 冻结作品集规模 NFR 与安全边界

- 初始部署为单服务器 API + Worker + PostgreSQL；每 Worker 默认一次执行一个任务；
- 多 Worker 正确性必须在真库验证；
- warm-DB create/query 服务端 p95 目标 `<300ms`，容量可用时 claim p95 `<2s`；
- 每 owner 默认最多 3、全局默认最多 50 个非终态 task；polling 空闲时退避并加 jitter；
- liveness 与 PostgreSQL/Alembic readiness 分离；不宣称 99.9%、跨机容灾或 Artifact 自动备份；
- CORS 默认关闭，production 无 Auth Provider 时 fail closed；不存在/越权统一 404；
- Secret 不进入 SQL/Artifact/log/Git，公共错误与日志保持 body-free；
- 原始 Riot cache、terminal task/run 内容、运维日志默认分别保留 7/90/30 天；terminal delete 与
  active cancel 分离。

### 7. 真实 PostgreSQL 是阻塞测试门

测试分为纯逻辑/Fake、PostgreSQL migration/repository/concurrency、API、Worker、离线产品纵向、
安全/生命周期和性能层。GitHub Actions 必须启动 PostgreSQL service/container，阻塞验证 Alembic、
事务、幂等、两 Worker claim、CAS/reconciliation。CI 不读取 Key，不调用 Riot 或真实 Provider；
Fake Provider 只能证明控制流，不能证明模型质量。

## 后果

### 正面

- POST 可以快速返回且任务不会因 HTTP 断线消失；
- 多 Worker claim、幂等与 owner 隔离有真实数据库语义；
- 复用现有 Application/Runtime/Harness，不形成第二套产品编排；
- SQL 与 Artifact 职责清楚，报告正文不会膨胀 task table；
- 不增加额外消息队列基础设施和运维面；
- hard crash 限制诚实可见，不会重复收费或重复副作用。

### 负面

- PostgreSQL、Alembic、Worker 进程、迁移和 Docker/CI 增加开发与部署复杂度；
- SQL 与文件 Artifact 不能共享一个原子事务，需要 reconciliation；
- 无 lease 的 hard crash 可能需要人工恢复；
- 单服务器 PostgreSQL 与本地 Artifact 仍是单点；
- 真实 Auth、备份、自动恢复、SSE 和完整前端仍未完成。

### 中性

- 5P 的同步 Adapter 是历史受测切片，6A 会版本化演进其 HTTP 合同；
- 采用 PostgreSQL polling 不表示 Multi-Agent、事件总线或微服务；
- 6A 完成也不表示整个阶段 6 完成；Session、Memory 和公网 Auth 仍需后续检查点；
- Pi 继续是 evaluation-only 冻结资产，不进入 Worker 或产品 Runtime。

## 备选方案

### 同步 API + SQL receipt

拒绝。虽然增加了查询记录，但 POST 仍被长运行阻塞，不能形成可靠 task ownership。

### FastAPI BackgroundTasks / `asyncio.create_task()`

拒绝。进程重启会丢失内存任务，多 Uvicorn worker 无 durable claim/recovery 事实源。

### SQLite 开发、PostgreSQL 生产

拒绝作为关键语义门。SQLite 的锁、隔离、JSON 和 SQL 方言不能证明 PostgreSQL
`FOR UPDATE SKIP LOCKED`、migration 和并发行为。

### Celery + Redis/RabbitMQ

当前拒绝。它能提供成熟队列能力，但增加两个运行系统和运维面；当前单服务器作品集规模下 PostgreSQL
已经能承担 durable queue。出现吞吐、调度或 Broker 语义 Bad Case 后再评估。

### 立即加入 lease/heartbeat/fencing

推迟到阶段 8。要安全自动 reclaim，必须同时解决暂停 Worker、迟到结果和 fencing，不能只加一个
超时字段伪装恢复。

### 限制永远只有一个 Worker

拒绝作为架构约束。初始部署可以只有一个 Worker，但代码和真库测试必须保留安全横向扩展能力。

## 重新评估条件

出现以下任一真实证据时，允许用新 ADR 重新评估：

1. PostgreSQL polling 在队列吞吐或查询负载上形成可复现瓶颈；
2. hard crash 人工恢复频率不可接受，需要阶段 8 lease/fencing；
3. 同步 SQLAlchemy 成为 API p95 的主要实测瓶颈；
4. Artifact 本地存储不满足部署/备份目标，需要对象存储或事务 outbox；
5. 公网多用户发布进入实施，需要正式 Auth、限流、备份和隐私策略。

## 参考

- ADR-0033、ADR-0037
- `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-design.md`
- `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-implementation.md`
- `app/api/main.py`
- `app/product/recent_review_service.py`
- `app/product/run_receipts.py`
- `docs/roadmap.md`
- `docs/architecture_capability_matrix.md`
