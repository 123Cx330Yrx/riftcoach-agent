# ADR-0041：采用原表 schema 2.0 的 Conversation-bound Review Task 身份

- 状态：Accepted（6B-4 实施中）
- 日期：2026-08-20
- 范围：阶段 6B-4 `conversation-bound-recent-review-identity`
- 相关：RQ-068、ADR-0039、ADR-0040

## 背景

6A 已有成熟的 `review_tasks → claim → Worker → AgentRuntime → Harness → Artifact`
异步链路，但 schema 1.0 的创建请求由客户端提交 Riot ID，Worker 执行时再调用 Account-V1
解析 PUUID。6B-1 至 6B-3 已经建立了稳定 Player Subject、owner-local Relationship 和固定
subject 的 Conversation；如果 Conversation 内的复盘仍信任客户端 Riot ID，就会形成两套身份源：

```text
Conversation 说 subject=A
Review body 却可以提交 Riot ID→subject=B
```

这既可能错绑玩家，也会让迟到 Task 随 UI 当前选择漂移。6B-4 必须让 Review Task 在创建时继承
服务器保存的 Conversation 身份，并让后续执行只使用该冻结身份。

## 决策

### 1. 复用现有 `review_tasks`，增加 nullable schema 2.0 identity columns

在原表增加：

```text
conversation_id
relationship_id
player_subject_id
relationship_role
```

schema 1.0 的四列必须全部为 null；schema 2.0 的四列必须全部非 null。schema 2.0 使用复合外键
指向 `conversations(conversation_id, owner_id, relationship_id, player_subject_id,
relationship_role)`，数据库因此能证明 Task tuple 与某个真实 Conversation tuple 完全一致。

不新建第二套 Conversation Review Task 表。既有 claim、Worker、terminal CAS、reconciliation、
retention、Run/Artifact 和查询基础设施继续复用。

### 2. 身份绑定和 Task 创建必须在同一个 PostgreSQL 短事务

公共请求只包含 `count`、`queue`、`focus`；path 提供 `conversation_id`，owner 来自可信
`ActorContext`。Repository 在一次事务中：

```text
锁定 owner 对应的 active relationship
→ 锁定同 tuple 且 status=active 的 Conversation
→ 从行中复制 owner/conversation/relationship/subject/role
→ 从 subject 读取可信 PUUID 与当前显示 alias
→ 用 request + 冻结 tuple 计算 schema 2.0 fingerprint
→ create/replay Review Task
→ COMMIT
```

锁内不调用 Riot、Provider、Runtime、文件系统或模型。Conversation/relationship 不可用、越权、
archived 或 hidden 均安全投影为 `conversation_not_found`。

### 3. schema 2.0 fingerprint 覆盖服务器派生身份

schema 1.0 fingerprint 算法保持不变。schema 2.0 fingerprint 的 canonical envelope 同时包含：

- 公共参数 `count/queue/focus`；
- `owner_id`；
- `conversation_id`；
- `relationship_id`；
- `player_subject_id`；
- `relationship_role`。

这样同 owner 使用同一个 Idempotency-Key，但换了 Conversation 或 subject 时会得到 409，而不会错误
replay 旧 Task。PUUID 和 Riot ID 不进入公共 request payload；完整 PUUID也不进入公共 View。

### 4. Task identity 只能创建，不能更新

ORM 不提供 rebind 方法。migration 增加 update trigger，拒绝直接 SQL 修改 Task 的创建身份、请求
fingerprint/payload 或 Conversation tuple；正常 claim、terminal 和 retention 状态更新仍允许。

Task 创建后，即使 Conversation 后来 archived/hidden，已经排队的 Task 仍按创建时 tuple 执行。
这叫“冻结执行身份”，不表示 Task 可以把结果写进另一个 Conversation；6B-4 也不持久化 assistant
Message 或 Memory。

### 5. Worker 通过可信 PUUID 执行，不再次调用 Account-V1

Repository 在 schema 2.0 Task 投影中装配私有 execution target：PUUID、routing region 和当前显示
alias。公共 `ReviewTaskView` 最多暴露 `conversation_id`，不暴露 PUUID、subject 或 relationship tuple。

`RiotPlayerSummaryBuilder.build_by_puuid()` 直接调用 Match-V5；显示 alias 只用于 Summary 展示。
Riot ID 改名可以改变后续显示名，但不能改变 `player_subject_id` 或 PUUID。schema 1.0 继续走旧
`build(game_name, tag_line, ...)` Account-V1 路径。

### 6. Executor 按 schema 明确分支，保持 legacy 1.0

- 1.0：校验原 `RecentReviewProductRequest` 和原 fingerprint，调用 `review()`；
- 2.0：校验无 Riot ID 的 Conversation request、冻结 binding 和私有 execution target，重算含 tuple
  fingerprint，调用 `review_by_puuid()`；
- 其他版本：安全失败 `task_contract_invalid`。

旧 `/reviews/recent`、旧 row、查询、claim、执行、reconciliation 和删除继续兼容。系统不根据旧 Riot ID
回填 Conversation/subject，也不为 1.0 Task 创建 Message 或 Memory。

## 被拒绝的方案

| 方案 | 拒绝原因 |
|---|---|
| 只把 `conversation_id` 放进 JSON payload | 数据库不能证明完整 tuple，identity 与公共 request 混层 |
| Service 先读 Conversation，再另开事务建 Task | 两步之间存在 archive/hide/rebind 检查竞态 |
| 新建第二套 Conversation Review Task 表 | 重复 claim、Worker、terminal、恢复与生命周期基础设施 |
| 执行时读取 UI 当前 Conversation | 迟到 Task 会漂移到新选择，破坏可重复性 |
| schema 2.0 仍用 Riot ID 调 Account-V1 | 重复解析可变 alias，重新引入双身份源和额外外部调用 |
| 把 PUUID 暴露在公共 Task DTO | 没有产品必要性，扩大身份和日志泄露面 |

## 后果与边界

正面结果是 Task 的 owner/Conversation/player 身份可由 SQL 约束、事务锁和 fingerprint 同时证明，
late task 可重复执行，alias 改名不改变 subject，现有 Runtime/Harness 不被复制。

代价是 Repository 映射 schema 2.0 Task 时需要 join Player Subject/Alias，migration 和兼容测试更复杂；
V1 Worker 仍是按部署配置的 Riot routing client，跨 routing cluster 的产品路由深化留给后续真实需求。

本 ADR 不实现 assistant Message terminal、Memory Candidate/长期 Memory、Auth/RSO、SSE、前端、
LangGraph、Multi-Agent、新 SDK 或真实外部测试调用。6B-5 未获授权。

## 验收门

必须具备 pure/API 红灯、migration/trigger/复合 FK、真实 PostgreSQL 原子绑定与并发、alias rename、
late task、no-Account-V1、legacy 1.0、existing Runtime/Harness no-I/O 纵向和 Linux package smoke 证据。
本地完整门禁后提交推送，并要求同一 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke`
三项 Actions 全绿，才能关闭 6B-4。
