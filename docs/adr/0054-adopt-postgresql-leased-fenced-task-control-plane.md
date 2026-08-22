# ADR-0054：采用 PostgreSQL 租约、fencing 与 durable task event 控制面

- 状态：Accepted for `8c-reliable-runtime-core`（2026-08-22，RQ-083）
- 范围：现有单 Runtime/单 Worker 兼容基线上的可靠任务控制面；不采用产品 Multi-Agent、DAG、
  第三方 Runtime 或第二套队列基础设施。

## 背景

RiftCoach 已有 PostgreSQL queued/running/succeeded/failed task、`SKIP LOCKED` 原子领取、owner-scoped
查询、终态 CAS、Runtime Trace、immutable Artifact、Run Receipt 和 Harness 唯一发布权。6A 的保守
reconciliation 能在存在严格终态证据时补齐 succeeded，也能由人工确认死亡 Worker 后安全失败。

当前缺口是：running task 没有租约、heartbeat 或 fencing token，无法区分活跃 Worker 与硬崩溃；
进程内 Runtime event 只在最终 Trace 中原子落盘，不能作为跨进程 task lifecycle replay；cancel 不是
持久请求；旧 Worker 的迟到结果只按 worker_id 拒绝，同一 worker_id 重启时缺少执行代次隔离；也没有
可机器判断的安全 checkpoint。

8B 的唯一 holdout 已拒绝产品 Multi-Agent，普通受限并行也只作为 8D 设计输入。因此 8C 没有证据支持
引入 DAG executor 或重写 Runtime。

## 决策

### 1. PostgreSQL 继续是唯一任务控制面

扩展 `review_tasks`，增加 lease generation、私有 lease token、heartbeat/expiry、cancel request、
checkpoint、recovery count/reason 等字段。所有 ownership 变化继续使用短事务和行级 CAS；Agent、Riot、
Provider、Artifact I/O 不在数据库事务内执行。

### 2. generation + token 共同 fencing

claim 为一次执行尝试分配递增 generation 和随机私有 token，并设置有限 lease。heartbeat、checkpoint、
succeed、fail、cancel terminal 都必须携带 worker_id、generation 和 token。终态 CAS 还要求 lease 未过期、
没有待处理 cancel。token 不进入公共 DTO、日志、event 或 Trace。

### 3. durable task event 不复制 Runtime Trace

新增 append-only `review_task_events`。它只记录 body-free 控制面事实：created、claimed、heartbeat、
checkpoint、execution_started、cancel_requested、recovery_requeued/recovery_required、succeeded/failed/
cancelled/reconciled。每个 event 有全局 cursor、task-local contiguous sequence 和由 canonical envelope
计算的 SHA-256 identity；同一 operation identity 重试只能得到同一 event。

Provider/Tool/Harness 的细节继续只属于既有 Runtime Trace。8E 的 SSE 以后消费 task event cursor，不能
把进程内 `stream()` 冒充 durable replay。

### 4. cancel 是持久请求，恢复坚持 receipt/checkpoint proof

queued task 可在 owner-scoped、幂等请求中直接 cancelled；running task 只先写
`cancel_requested_at/request_id/reason`，由当前 fenced Worker 在安全边界收敛为 cancelled。同步 executor
暂不能保证中断正在进行的外部 HTTP 调用，但 cancel 后的成功/失败 terminal CAS 会被拒绝，不会发布 SQL
结果。

expired lease 的自动处理顺序固定为：

1. 有 cancel request：fenced cancel terminal；
2. 有严格 Receipt + Trace + Artifact 终态证据：reconciled success；
3. 最新 checkpoint 明确为 `claimed_safe` 且尚未开始外部副作用：requeue；
4. 其他情况：进入 `recovery_required`，等待受限人工裁决，不盲目重跑。

每次 requeue 清除旧 token 并计数；达到上限后进入 `recovery_required`。旧 Worker 随后返回时因 token/
generation/lease/status 任一不匹配而失败。

### 5. 背压与可观测性沿用现有边界

queued、running、recovery_required 都计入 owner/global active capacity。事件/日志只允许 task/run/worker、
generation、cursor、reason、latency 等安全字段；不记录 request payload、Prompt、报告、PUUID、Key、
Receipt/Artifact body 或 lease token。

## 非功能要求

- 正确性：同一 task 最多一个有效 lease；最多一个 SQL terminal；task-local event sequence 连续；
- 性能：claim/heartbeat/event append 都是单个短事务；event replay 有 owner scope、cursor 和硬 limit；
- 可恢复性：自动恢复必须有 receipt 或 safe checkpoint proof；未知副作用 fail closed；
- 安全：cancel/replay public seam owner-scoped，lease token 为 private capability；错误 body-free；
- 兼容性：默认单 Worker/单 Runtime 不改变 Harness 唯一发布权；既有终态证据仍可严格读取；
- 运维：不增加 Redis/Celery/Kafka/Kubernetes；作品集规模不声称跨地域 HA、RPO/RTO 或生产 SLA。

## 备选方案

### A. PostgreSQL 增量可靠控制面（采用）

直接修复已观察到的 running-task crash/late-result 缺口，复用真库 CI、Repository、Artifact 和 Harness；
代价是需要严格 migration、CAS 和故障注入测试。

### B. 完整事件溯源 + DAG Runtime 重写（拒绝）

统一性更强，但会同时重写 task、Runtime、Harness、API 和历史数据。8B 没有证明复杂 executor 的收益，
当前重写会扩大故障面并延迟产品交付。

### C. Redis/Celery 外部队列（deferred）

成熟生态可以提供 broker/worker primitives，但会产生 PostgreSQL 与 broker 双真源、额外部署和恢复语义。
当前没有 PostgreSQL 队列吞吐或锁竞争 Bad Case；若以后出现可复现不足，另立 ADR 与迁移/回退计划。

## 影响与限制

- 正面：崩溃、同 worker_id 重启、取消竞态、迟到结果、重复 terminal 和事件重放具有持久可测语义；
- 负面：task mutation 会多写一条 event；heartbeat 产生受控写负载；migration 与 Fake 需要同步升级；
- 限制：当前同步 Runtime 只能在边界观察 cancel，不能强杀已发出的外部请求；只有 `claimed_safe` 和
  receipt-proven terminal 可自动恢复，不冒充通用 mid-step resume；
- 后续：8D 消费可靠控制面完成 evidence fusion；8E 再增加 SSE/Auth/Web/backup；DAG、第三方 Runtime、
  Multi-Agent 仍需全新 Bad Case 和 ADR。
