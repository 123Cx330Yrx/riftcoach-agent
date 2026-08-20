# 6B-4 Conversation-bound Recent Review Identity 设计与教学稿

> 状态：设计冻结，实施中。对应 [ADR-0041](../adr/0041-conversation-bound-review-task-identity.md)。

## 1. 初学者先理解：这一步到底在修什么

6B-3 已经有“固定给某个玩家的 Conversation”，6A 已经有“后台执行复盘的 Review Task”。
但两者现在还没连起来：旧复盘请求自己携带 Riot ID，后台再把它解析成 PUUID。

如果在 Conversation A 里仍允许 body 写另一个 Riot ID，系统就无法回答“这份复盘究竟属于谁”。
6B-4 的目标不是增加新 Agent，而是建立一条可信身份链：

```text
可信 Actor owner
→ 服务器数据库里的 active Conversation
→ Conversation 冻结的 relationship / player subject
→ subject 的稳定 PUUID
→ 既有 Review Task / Runtime / Harness
```

底层原则叫 **server-derived identity**：影响权限和数据归属的身份，必须从服务器已验证的状态派生，
不能由客户端正文、模型输出或 UI 当前选择决定。

## 2. 本批实现与不实现

### 实现

- Review Task schema 2.0 和 legacy 1.0 共存；
- `POST /conversations/{conversation_id}/reviews/recent`；
- body 仅 `count/queue/focus`；
- PostgreSQL 事务内冻结 Conversation identity；
- Task fingerprint 覆盖服务器 tuple；
- PUUID 私有 execution target 与 `build_by_puuid()`；
- v2 Executor → existing Runtime → Harness → Artifact；
- alias rename、late task、owner isolation、真库并发和 no-I/O package 证据。

### 不实现

- 自动写 assistant Message；
- Memory Candidate 或长期 Memory；
- verified-self、正式 Auth/RSO；
- SSE/前端；
- Redis、向量 Memory、LangGraph、Multi-Agent、新 SDK；
- 测试/CI 中真实 Riot 或模型调用。

## 3. 数据合同

### 3.1 公共请求

```json
{
  "count": 10,
  "queue": 420,
  "focus": "overall"
}
```

明确没有：`owner_id`、`riot_id`、PUUID、relationship、subject、role。`conversation_id` 来自 path，
但 path 只是候选 ID；Repository 仍要用 Actor owner 查询并锁定，不能把 path 当成授权证明。

### 3.2 schema 2.0 Task 私有身份

```text
review_tasks.owner_id
review_tasks.conversation_id
review_tasks.relationship_id
review_tasks.player_subject_id
review_tasks.relationship_role
```

完整 tuple 由复合 FK 指向 Conversation。完整 PUUID、routing region 和 alias 在读取/claim 时从受信表
装配为内部 execution target，不进入公共 Task 响应。

### 3.3 版本形状

```text
schema 1.0 → 四个 Conversation identity column 全 NULL
schema 2.0 → 四列全 NOT NULL，且 composite FK 成立
```

这不是把整表升级成只能读 2.0，而是一次兼容迁移：旧 Task 继续查询、执行和删除。

## 4. 创建时的数据和控制流

```text
HTTP POST /conversations/{id}/reviews/recent
  │ body=count/queue/focus，header=Idempotency-Key
  ▼
ActorContext.owner_id
  ▼
ReviewTaskService 生成 task_id/run_id/created_at
  ▼
PostgresTaskRepository 单事务
  ├─ advisory lock：保护 Review Task capacity/idempotency
  ├─ 读取 Conversation identity 候选
  ├─ FOR UPDATE 锁 relationship，要求 active
  ├─ FOR UPDATE 锁 Conversation，要求 active 且 tuple 相同
  ├─ 读取 subject PUUID + 最新 alias
  ├─ fingerprint(request + frozen tuple)
  ├─ create / replay / conflict / capacity
  └─ COMMIT
  ▼
202 + task_id/run_id/status/conversation_id
```

为什么一定是一个事务：如果先读 Conversation、提交，再建 Task，夹在中间的 hide/archive 会让一个
“创建时已经无效”的 Conversation 仍产生新 Task。锁和插入放在一起，最终状态只能是一个合法顺序。

## 5. Worker 执行流

```text
ReviewWorker claim schema 2.0 row
  ▼
Repository 用 frozen subject 加载 PUUID/alias（不看 UI 当前选择）
  ▼
Executor 校验 schema、binding、execution target、fingerprint
  ▼
Application.review_by_puuid()
  ▼
SummaryBuilder.build_by_puuid()
  ├─ 不调用 Account-V1
  └─ 直接 Match-V5 ids/detail/timeline
  ▼
现有 compiler → AgentRuntime → Harness → Artifact/Receipt/Trace
  ▼
现有 terminal verifier → Task succeeded/failed CAS
```

Task 创建之后 Conversation 被归档，不会改写冻结身份；已排队任务仍完成自己原来的工作。6B-4 不把
结果追加成 assistant Message，因此也不存在向另一个 Conversation 写消息的问题。

## 6. alias 改名与稳定身份

PUUID/`player_subject_id` 是“同一个账号主体”，Riot ID 是显示名。假设：

```text
创建 Task 时：OldName#TAG → subject S / PUUID P
执行前新增 alias：NewName#TAG → 仍是 subject S / PUUID P
```

执行可以用最新 alias 展示 `NewName#TAG`，但 match 查询仍用 P，Task tuple 仍指向 S。测试必须证明
alias 改名不会让 subject 改成别的玩家，也不会触发 Account-V1。

## 7. 错误和安全投影

| 情况 | 结果 |
|---|---|
| body/header 非法 | 422 `request_invalid` |
| opaque path ID 非 UUID | owner-safe 404 `conversation_not_found` |
| Conversation 不存在、越权、hidden、archived、relationship hidden | 404 `conversation_not_found` |
| 同 owner/key 但 request 或 tuple 不同 | 409 `idempotency_conflict` |
| task capacity | 503 `task_capacity_exceeded` |
| DB/identity/alias 完整性失败 | 503 `service_unavailable` |
| v2 target/fingerprint 被篡改 | Worker safe failure，不调用 Runtime |

错误、日志和公共 DTO 不包含 PUUID、Riot ID、Message body、SQL、Provider body 或 Secret。

## 8. 代码地图

```text
app/product/recent_review.py             # 无 Riot ID 的 Conversation request
app/tasks/models.py                      # v2 command/binding/private target/version shape
app/tasks/fingerprint.py                 # request + trusted identity canonical digest
app/tasks/service.py                     # 生成待绑定任务、映射安全结果
app/persistence/task_record.py           # nullable identity columns
app/persistence/task_repository.py       # 原子锁定/派生/create 与私有 target 装配
migrations/versions/0004_*.py            # CHECK/FK/index/immutable trigger
app/lol/player_summary.py                # build_by_puuid，无 Account-V1
app/product/recent_review_service.py     # review_by_puuid，共用 Runtime/Harness 后半段
app/tasks/recent_review_executor.py      # 1.0/2.0 显式执行分支
app/api/main.py                          # Conversation-bound 202 route
app/api/composition.py                   # 同一 Task Service 的 lazy binding
app/workers/composition.py               # 既有 Worker 自动支持两个 schema
scripts/run_packaging_smoke.py           # Fake/no-I/O 绑定 Task 证据
```

## 9. 分层测试如何证明

1. pure models/fingerprint：严格 request、1.0/2.0 形状、私有字段不投影、identity 改变会改 digest；
2. Service/Fake：v2 command、create/replay/conflict/not-found/capacity、安全错误；
3. API：body extra-forbid、Actor owner、path、202/404/409/503、OpenAPI/import no-I/O；
4. migration：nullable compatibility、schema shape、复合 FK、索引、trigger、upgrade/downgrade；
5. Repository 真库：同事务绑定、owner isolation、archive/hide 竞态、late task、alias rename；
6. Summary/Application/Executor：v2 不调用 Account-V1，1.0 仍调用旧路径，Runtime/Harness 后半段复用；
7. package：Fake Account Resolver 创建 subject/Conversation，再创建 v2 Task，Worker 安全失败，外部调用 0；
8. 完整回归与 exact-SHA CI：pytest、PostgreSQL、Linux package 三 job 全绿。

本机无 PostgreSQL/Docker 时，真库测试只能显式 skip；不能用 SQLite 假装证明 PostgreSQL 锁、FK 或
trigger。

## 10. 当前限制和面试表述

可以说：

> 我让 Conversation-bound Review Task 在 PostgreSQL 短事务中锁定 active relationship 和
> Conversation，由服务器派生并冻结 owner/relationship/subject tuple；schema 2.0 用复合 FK、
> identity-aware fingerprint 和 immutable trigger 防错绑，Worker 通过 PUUID 直接调用 Match-V5，
> 同时保留 schema 1.0 兼容路径。

不能说：

- “Riot ID 查询证明用户拥有该账号”；
- “已经实现长期 Memory 或 assistant 对话闭环”；
- “Task 执行时仍要求 Conversation active”；
- “复合 FK 自己能检查父行 status”；
- “6B-4 是 Multi-Agent 或 LangGraph 工作流”；
- “Fake/no-I/O 测试证明真实 Riot/Provider 可用”。
