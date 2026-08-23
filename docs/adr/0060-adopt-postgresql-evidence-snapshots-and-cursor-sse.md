# ADR-0060：采用 PostgreSQL 不可变 Evidence 快照与 cursor SSE 产品接缝

- 状态：Accepted for `8e-productization` Batch C（2026-08-23，RQ-090）
- 范围：EvidenceBundle 持久化/刷新/过期投影、8C event replay → SSE、安全四态产品合同；
  不包含 React、正式 Auth/RSO、外部刷新调度、备份或公网部署。

## 背景

8D 已有可重算 digest 的 typed `EvidenceBundle`，但它目前只存在于一次 Python 调用中；
8C 已有 PostgreSQL append-only task event 和 owner-scoped cursor replay，但浏览器只能分页拉取。
如果直接开始前端，UI 会被迫猜测证据是否仍可用、任务失败与质量拒绝有什么区别，以及断线后从
哪里继续。

Batch C 需要建立产品可消费的持久事实，同时保持现有边界：PostgreSQL 是唯一控制面，Artifact/
Trace 各自保持原事实源，OP.GG/Riot 原始 body、PUUID、Prompt、Key 和 lease token 不进入新存储或
公共 DTO。

## 方案比较

| 方案 | 裁决 | 原因 |
|---|---|---|
| PostgreSQL append-only typed snapshot + 查询时 freshness 投影 | 采用 | 与 task owner/run 身份、事务、迁移、删除和真库 CI 同源；可做 revision/idempotency/digest gate |
| Artifact/file-backed EvidenceBundle store | 拒绝为产品控制面 | 会重现 SQL 可见性与文件 crash 双真源问题；owner query、并发 refresh 和级联删除更复杂 |
| 每次读取重新调用 Riot/OP.GG 并重建 | 拒绝 | 读取变成有费用且不可复现的网络副作用；上游失败会让历史产品结果消失 |

## 决策

### 1. Evidence 快照追加而不覆盖

新增 `evidence_bundle_snapshots`。每行绑定现有 `(task_id, run_id, owner_id)`，保存：

- 单调 `revision` 与调用方提供的 bounded `refresh_id`；
- 8D 完整 typed、body-free storage projection；
- `bundle_digest` 与绑定身份/时间/revision 的 `snapshot_digest`；
- `stored_at` 与从易过期来源推导的 `expires_at`。

Repository 在 task 行锁下分配 revision。同一 `(task_id, refresh_id)` 重试且内容相同返回 replay；
内容不同返回 conflict。旧 revision 永不回写，读取只取最新 revision，不因新快照过期而偷偷回退旧值。

### 2. 过期是查询投影，不改写历史

`expires_at` 取 OP.GG/official patch 等有明确 expiry 来源的最早时间；没有易过期来源时为 `null`。
`now >= expires_at` 时，快照仍可用于审计，但当前 Meta/exact-patch claims 不再作为 usable claims，
产品状态至少降为 `degraded` 并给出 `evidence_expired`。刷新通过新增 revision 恢复 current，不能修改
旧 digest。

### 3. 固定四态产品合同

新增 pure projector，把 task terminal、Harness publication 与最新 evidence 合成：

| 条件 | 产品状态 |
|---|---|
| queued/running/recovery_required | `not_ready` |
| failed/cancelled 或 Harness rejected | `rejected` |
| 报告可用但 Harness degraded、evidence 缺失/过期/degraded/rejected | `degraded` |
| Harness published 且最新 evidence complete/current | `published` |

`reason_code` 必须区分 pending、recovery、execution failure、cancel、quality reject、evidence missing/
expired/degraded 与 ready；不能只靠颜色表达。

### 4. SSE 只是 durable replay 的传输投影

新增 `GET /tasks/{task_id}/events/stream`。连接前先做 trusted-owner lookup；事件继续来自 8C
`read_events(after_cursor)`，SSE `id` 使用数据库 cursor，`Last-Event-ID` 支持断线续传。data 复用
allowlisted `TaskEventResponse`，不包含 owner、worker、operation identity、checkpoint、lease token、
request body 或隐藏推理。

连接采用有限生命周期、keep-alive comment 和终态自动关闭；客户端随后按最后 cursor 重连。数据库
event 才是真相，浏览器连接和进程内 `Runtime.stream()` 都不是。

### 5. 产品 API 读写边界

- 内部 Evidence write port 负责 append/replay；Batch C 不开放公共 refresh POST，也不触发真实外部调用；
- `GET /runs/{run_id}/evidence` 返回最新 owner-scoped safe snapshot view；
- `GET /runs/{run_id}/product-state` 从 owner-scoped task 与 evidence query 形成四态；
- missing/cross-owner 使用不可区分的 404，存储/完整性错误只返回 allowlisted code。

## 数据与控制流

```text
typed EvidenceBundle
  → internal append(refresh_id)
  → lock owner/run task + allocate revision
  → verify bundle digest + store JSONB + snapshot digest
  → owner-scoped latest query(now)
  → digest revalidation + current/expired projection
  → /evidence + /product-state

review_task_events
  → owner-scoped read_events(after_cursor)
  → TaskEventResponse allowlist
  → SSE id/data
  → Last-Event-ID reconnect
```

## 安全、失败与生命周期

- composite FK `ON DELETE CASCADE` 让 terminal task 删除/retention 同时移除快照，不留下 owner 孤儿；
- JSONB 大小、revision、digest、refresh ID、时间顺序和唯一性由模型、migration 与 Repository 同时约束；
- 读取时重建 typed bundle 并重算 bundle/snapshot digest；任一漂移 fail closed；
- SSE 的生成期异常只投影安全 `stream.error` code 后关闭，不返回异常、DSN、路径或 body；
- 当前不声称主动刷新、长期 freshness、backup restore、跨区域 HA、RPO/RTO 或生产 SLA。

## 后果

正面影响：前端第一次拥有可重放、可解释、owner-scoped 的 evidence 与生命周期事实；刷新历史可审计，
过期不会伪装为 current。代价是新增 migration、JSONB 严格重建和 SSE polling 连接管理。

Batch C 公共闭环后才能进入 Batch D 静态/fixture-backed React；正式外部 refresh scheduler、Auth、
限流、HTTPS 和备份仍按 8E 后续批次处理。
