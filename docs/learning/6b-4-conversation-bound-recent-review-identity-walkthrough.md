# 6B-4 Conversation-bound Recent Review Identity 实现后复盘

> 状态：本地实现完成，等待完整门禁与 exact-SHA 公共 PostgreSQL/Linux package 证据。
> 本文解释的是 6B-4 的真实实现，不表示 6B-5 assistant Message 或长期 Memory 已完成。

## 1. 这一批解决的具体问题

6B-3 已经能创建一个固定绑定到某个玩家主体的 Conversation，6A 也已经能把复盘请求放进
PostgreSQL，由后台 Worker 执行既有 AgentRuntime/Harness。两条链此前却没有连接：旧复盘请求仍由
客户端提交 Riot ID，Worker 执行时再调用 Account-V1 把 Riot ID 解析为 PUUID。

这会出现两个相互冲突的身份源：

```text
Conversation：玩家主体 A
请求 body：另一个 Riot ID → 玩家主体 B
```

如果服务器相信 body，报告可能在 A 的 Conversation 中分析 B；如果执行时读取 UI 当前选中的玩家，
排队任务又会随用户后来切换账号而漂移。6B-4 解决的是“这份复盘到底属于哪个稳定玩家主体”，不是增加
一个模型、一个 Agent 或一种 Memory。

## 2. 底层原理：服务器派生身份

影响权限、数据归属和执行目标的身份不能由客户端、UI 或模型填写，而要从服务器已经持久化并验证过的
状态中派生。这叫 **server-derived identity**。

RiftCoach 当前的可信链是：

```text
trusted Actor owner
→ owner-scoped active relationship
→ active Conversation 的冻结 tuple
→ stable player_subject_id
→ subject 的 PUUID
→ Match-V5
```

Riot ID 是可变显示别名，PUUID 和 `player_subject_id` 才代表稳定主体。Riot ID 改名以后，新任务可以显示
新名字，但不能因此改成另一个 subject，也不能重新通过 Account-V1 猜身份。

## 3. 为什么选择原表 schema 2.0

实现比较过三种方案：

| 方案 | 结论 | 原因 |
|---|---|---|
| 只把 `conversation_id` 放进 JSON | 拒绝 | 数据库不能证明完整 owner/relationship/subject/role tuple |
| Service 先读 Conversation，再另开事务创建 Task | 拒绝 | 两步之间可能发生 archive/hide，产生检查竞态 |
| 新建第二套 Conversation Review Task 表 | 拒绝 | 会复制 claim、Worker、终态 CAS、恢复、保留与删除 |
| 既有 `review_tasks` 增加 nullable schema 2.0 身份列 | 采用 | 保留 1.0 兼容，同时复用成熟异步运行基础设施 |

所以同一张表同时支持：

```text
schema 1.0：四个 Conversation identity column 全部 NULL
schema 2.0：四列全部非 NULL，并由复合 FK 指向同一个 Conversation tuple
```

旧 `/reviews/recent` 和旧 row 不回填、不改义，仍走 Riot ID → Account-V1 的 1.0 路径。新 endpoint 只创建
2.0 Task。

## 4. 公共和私有合同怎样分层

### 4.1 客户端可以控制什么

`POST /conversations/{conversation_id}/reviews/recent` 的 body 只能包含：

```json
{
  "count": 10,
  "queue": 420,
  "focus": "overall"
}
```

`owner_id` 来自可信 Actor，`conversation_id` 来自 path 但仍要 owner-scoped 查询，relationship、subject、
role 和 PUUID 全部由服务器派生。Pydantic 的 `extra="forbid"` 会拒绝客户端伪造这些字段。

### 4.2 SQL Task 冻结什么

`review_tasks` 的 schema 2.0 row 保存：

```text
conversation_id
relationship_id
player_subject_id
relationship_role
```

`owner_id` 已是原 Task 列。复合 FK 将这五项指向 Conversation 的唯一完整身份；CHECK 保证 1.0 all-null、
2.0 all-present，trigger 禁止后续用直接 SQL 重绑 Task 身份。

### 4.3 Worker 私下需要什么

Repository 映射 2.0 row 时才装配内部 `ConversationReviewExecutionTarget`：

```text
完整 PUUID
current routing region
最新 game name / tag line
```

它被 Pydantic `exclude=True` 标记，不进入 `ReviewTaskView`、HTTP 响应、request payload 或日志。公共创建响应
只包含 `conversation_id/task_id/run_id/status/links`。

## 5. 创建链的数据流和控制流

```text
HTTP POST /conversations/{id}/reviews/recent
  │
  ├─ ActorContext 提供 owner_id
  ├─ body 解析为 ConversationRecentReviewRequest
  └─ Service 只生成 task_id/run_id/created_at
          │
          ▼
PostgresTaskRepository 单一短事务
  ├─ 全局 task-create advisory lock：串行容量与幂等判定
  ├─ 读取 owner-scoped active Conversation identity 候选
  ├─ FOR UPDATE 锁 active relationship
  ├─ FOR UPDATE 锁同 tuple 的 active Conversation
  ├─ 计算 request + owner + frozen tuple fingerprint
  ├─ create / replay / conflict / capacity
  ├─ 插入 schema 2.0 Review Task
  └─ COMMIT
          │
          ▼
HTTP 202：可靠入队，不表示 Agent 已成功或报告已发布
```

锁顺序固定为 relationship → Conversation，与 Conversation archive/hide 使用同一顺序。这样并发结果只有两种
合法串行化：Task 先冻结身份并创建，或者生命周期操作先完成、随后创建安全返回 404。

## 6. 执行链的数据流和控制流

```text
existing ReviewWorker.claim_next()
  │
  ├─ schema 1.0 → legacy execution target
  └─ schema 2.0 → frozen subject 查 PUUID/current routing/latest alias
          │
          ▼
RecentReviewTaskExecutor
  ├─ 校验 running/worker/task kind/schema
  ├─ 1.0：解析 RecentReviewProductRequest + legacy fingerprint
  └─ 2.0：解析 Conversation request + binding/target + identity fingerprint
          │
          ▼
RecentReviewApplicationService.review_by_puuid()
  │
  ▼
RiotPlayerSummaryBuilder.build_by_puuid()
  ├─ Account-V1 calls = 0
  └─ PUUID → Match-V5 ids/detail/timeline
          │
          ▼
共享 validate → deterministic report → compiler → AgentRuntime → Harness
  │
  ▼
共享 receipt / Trace / final Artifact evidence gate → terminal CAS
```

2.0 没有复制 Runtime 或 Harness。新代码只在“怎样取得 Summary”之前分支，得到合法 Summary 后重新汇入原有
质量门。Task 创建后 Conversation 即使被归档，已排队 Task 仍按冻结 subject 执行；6B-4 不写 assistant
Message，所以这不等于向归档 Conversation 追加内容。

## 7. 实际代码地图

| 层 | 文件 | 关键职责 |
|---|---|---|
| Product request | `app/product/recent_review.py` | 无 Riot ID 的严格 Conversation request；compiler 接受两类 typed request |
| Task domain | `app/tasks/models.py` | 2.0 binding、私有 target、pending command 与 1.0/2.0 shape invariant |
| Fingerprint | `app/tasks/fingerprint.py` | canonical JSON 覆盖 request + owner + 全部 frozen tuple |
| Service | `app/tasks/service.py` | 生成待绑定意图并将 Repository disposition 投影成安全错误 |
| ORM/migration | `app/persistence/task_record.py`、`migrations/versions/0004_add_conversation_review_identity.py` | nullable columns、CHECK、复合 FK、索引、immutable trigger、可逆 downgrade |
| Repository | `app/persistence/task_repository.py` | 单事务绑定、锁顺序、create/replay/capacity、2.0 target 映射 |
| Summary | `app/lol/player_summary.py` | 抽取共享 Match-V5 后半段，新增 no-Account-V1 PUUID 入口 |
| Application | `app/product/recent_review_service.py` | `review_by_puuid()` 后复用 validate/render/compiler/runtime/receipt |
| Executor | `app/tasks/recent_review_executor.py` | 明确 1.0/2.0 分支，再汇入相同 terminal evidence gate |
| HTTP | `app/api/main.py`、`app/api/composition.py` | typed 202 route、trusted Actor、owner-safe error、lifespan proxy 转发 |
| Worker/package | `app/workers/composition.py`、`scripts/run_packaging_smoke.py` | 复用一个 Worker；Linux no-I/O 验证 2.0 Task 安全终态 |

## 8. 测试怎样证明设计承诺

| 层 | 主要测试 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| pure domain/fingerprint | `test_conversation_review_task_models.py` | extra forbid、版本形状、私有投影、tuple 改变会改 digest | PostgreSQL 事务 |
| Service/API | `test_conversation_review_task_service.py`、`test_conversation_review_api.py` | create/replay/404/409/422/503、Actor/path/body 分工 | 真数据库锁 |
| migration | `test_conversation_review_migrations_postgres.py` | 1.0/2.0 CHECK、FK、trigger、downgrade | 本机无 DB 时只能 skip |
| Repository | `test_conversation_review_repository_postgres.py` | owner isolation、原子绑定、capacity/rollback、alias、late claim、双向锁顺序 | 外部 Riot 可用性 |
| Summary/Application | `test_recent_review_domain_services.py`、`test_recent_review_application_service.py` | 2.0 Account-V1 为 0，后半段复用 Runtime/Harness | 真实模型质量 |
| Executor | `test_task_reconciliation.py` | binding/target/fingerprint 篡改在 Application 前失败；legacy 不回归 | 正式 Auth |
| composition/package | `test_api_composition.py`、`test_packaging_smoke.py` | composed app 真能转发；同一 Worker 处理 v2；external calls=0 | 成功 Coach 报告 |
| blocking CI | `.github/workflows/tests.yml` | PostgreSQL 17 migration/repository 与 Linux image smoke 成为阻塞门 | 多区域生产 SLA |

本地没有 PostgreSQL/Docker，所以真库项显示 skip 是诚实的环境边界。只有同一提交的公共
`postgres-migrations` 和 `packaging-smoke` 成功后，才能把那些语义写成公共完成证据。

## 9. 安全运行方法

聚焦 no-I/O 回归：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_conversation_review_task_models.py `
  tests/test_conversation_review_task_service.py `
  tests/test_conversation_review_api.py `
  tests/test_recent_review_domain_services.py `
  tests/test_recent_review_application_service.py `
  tests/test_task_reconciliation.py `
  tests/test_api_composition.py `
  tests/test_packaging_smoke.py -q
```

本地仅收集真库合同（无 `RIFTCOACH_TEST_DATABASE_URL` 时会明确 skip）：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_conversation_review_migrations_postgres.py `
  tests/test_conversation_review_repository_postgres.py -q
```

这些命令不需要 Riot、GLM 或 DeepSeek Key。不要为了追求本地全绿而把 PostgreSQL 测试改成 SQLite，也不要
在 package smoke 中换成真实外部调用。

## 10. 失败、安全和范围边界

| 场景 | 系统行为 |
|---|---|
| body/header 非法 | 422 `request_invalid` |
| opaque path ID 非 UUID，或 Conversation 不存在/越权/归档/隐藏 | owner-safe 404 `conversation_not_found` |
| 同 owner/key 但 request 或 tuple 不同 | 409 `idempotency_conflict` |
| owner/global active task 超限 | 503 `task_capacity_exceeded` |
| DB、subject、routing 或 alias 完整性失败 | 503 `service_unavailable`，不泄露正文 |
| 2.0 binding/target/fingerprint 被篡改 | Worker 在 Application/Runtime 前安全失败 |
| alias 改名 | 显示最新 alias，但 PUUID/subject/binding 不变 |
| Task 创建后 Conversation 归档 | late Task 仍按冻结身份执行；不追加 Message |

公共 DTO、日志和错误不包含完整 PUUID、Riot ID、relationship/subject tuple、Message body、SQL、Provider
body、异常正文或 Secret。

## 11. 当前明确没有实现什么

- 不证明外服 Riot ID 属于当前用户；当前 `self` 仍是 unverified claim；
- 不自动把报告写成 assistant Message；那是 6B-5 的独立一致性问题；
- 不生成 Memory Candidate，也没有长期训练 Memory；
- 没有正式 Auth/RSO、SSE、前端或公网访问控制；
- 没有新增 LangGraph、Multi-Agent、Redis、向量 Memory 或 Agent SDK；
- 没有证明真实 Riot/Provider 可用、模型质量合格或生产 SLA。

## 12. 面试时怎样准确表述

可以说：

> 我把 Conversation-bound Review Task 设计成既有任务表的 schema 2.0。创建时在 PostgreSQL 短事务中
> 按 relationship→Conversation 锁顺序校验 active tuple，由服务器派生 owner、relationship、subject 和
> role，并用复合外键、身份 fingerprint 与 immutable trigger 防错绑。Worker 从冻结 subject 装配 PUUID，
> 跳过 Account-V1 直接调用 Match-V5，之后复用原 AgentRuntime、Harness、Artifact 和终态证据门，同时
> 保留 schema 1.0 兼容。

不能说：

- “复合 FK 能自己检查 Conversation 是否 active”——active 是 Repository 锁内检查；
- “Task 执行时 Conversation 必须仍 active”——创建后身份已经冻结；
- “我们已实现完整对话教练和长期 Memory”——6B-5 及后续尚未完成；
- “package smoke 证明真实 Agent 成功”——它故意走 no-I/O 安全失败终态；
- “这是 Multi-Agent 或 LangGraph”——它是模块化单体中的可信身份与异步控制流深化。

## 13. 自测问题

1. 为什么 `conversation_id` 不能只放进 request JSON？
2. 为什么 Repository 必须在同一个事务里检查 active 并插入 Task？
3. PUUID、`player_subject_id` 和 Riot ID 各自承担什么角色？
4. 2.0 为什么不调用 Account-V1，1.0 又为什么暂时保留它？
5. 为什么 late Task 可以继续执行，却不能据此宣称 assistant Message 已完成？
6. 本机 PostgreSQL 测试 skip 时，哪些结论必须等待公共 CI？

能用自己的话回答这六题，才算真正理解 6B-4，而不只是知道“测试通过了”。
