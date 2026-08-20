# 6B-3 Conversation / Message Foundation 设计与教学稿

> 状态：设计已冻结且本地实现已完成；本文件保留设计角色，实现证据见
> [`6B-3 walkthrough`](../learning/6b-3-conversation-message-foundation-walkthrough.md)。实现提交的
> exact-SHA 三 job 全绿前，6B-3 仍不能关闭。
>
> 对应 ADR：[`ADR-0040`](../adr/0040-conversation-message-foundation-contract.md)

## 1. 先用一句人话说明要做什么

把 Conversation 想成一个“固定给某个玩家的 Coach 讨论房间”，把 Message 想成房间里按
数据库编号排列的 user/assistant 文本。房间创建时就把它绑定到一个稳定的
`player_subject`；之后客户端不能把房间偷偷改绑到另一个 PUUID。6B-3 只建这个可靠的
控制面，不让模型说话，也不执行 Review。

这一步解决的是三个基础问题：

1. **身份问题**：Riot ID 是可变显示名，真正稳定的是 6B-1/6B-2 得到的 PUUID subject；
2. **顺序问题**：两个请求同时发消息时，不能都拿到“第 1 条”；
3. **边界问题**：用户消息、未来可信助手消息、system/tool/provider 内部数据必须分开。

## 2. 范围和非范围

### 本批实现

- Conversation 创建、owner-scoped 幂等和查询；
- 固定 `owner_id + relationship_id + player_subject_id + relationship_role`；
- `active/archived/hidden` 生命周期；
- user Message 创建、有限查询和严格内容 digest；
- PostgreSQL 表、复合外键、CHECK、索引和 immutable trigger；
- FastAPI 薄 Adapter、Fake 端口、真实 PostgreSQL migration/事务/并发证据；
- 本批实现后 walkthrough、代码地图、运行说明、失败/安全和面试边界。

### 明确不实现

- AgentLoop、AgentRuntime、ReviewHarness 调用；
- assistant 公共写入或伪造 terminal；
- Review Task 2.0 / Conversation-bound Review；
- Memory Candidate、长期 Memory、RAG Context；
- Auth/RSO、正式公网鉴权、SSE、前端；
- Redis、Chroma、向量库、LangGraph、新 SDK 或外部 Riot/Provider I/O。

## 3. 功能需求（FR）

| 编号 | 要求 | 可验证证据 |
|---|---|---|
| FR-1 | 创建只能引用当前 owner 的 active relationship | Service + PostgreSQL 行锁测试 |
| FR-2 | 同 owner/key/fingerprint 重试只 replay，不复制 | Fake + unique constraint + 并发测试 |
| FR-3 | 不同 fingerprint 使用同 key 返回 409 | domain/API 测试 |
| FR-4 | Conversation 绑定字段不可重绑 | Repository 无方法 + DB trigger direct SQL |
| FR-5 | archived 可读但拒绝新消息 | 生命周期测试 |
| FR-6 | hidden 与 hidden relationship 对 owner 不可见 | owner-scoped 查询测试 |
| FR-7 | user Message 从 1 开始有序递增 | 两 writer PostgreSQL 并发测试 |
| FR-8 | 内容非空、有界、控制字符受限、digest 服务端生成 | pure/API/DB 三层测试 |
| FR-9 | 公共 HTTP 不允许 assistant/system/tool/provider 输入 | strict DTO/OpenAPI/API negative tests |
| FR-10 | 消息列表有界且稳定排序 | limit/cursor API 测试 |

## 4. 非功能要求（NFR）

- PostgreSQL 是唯一生产语义真源；真实 migration、FK、trigger、事务和并发只由 PostgreSQL
  17 job 证明；
- 所有数据库事务短小，锁内不进行网络、模型或文件 I/O；
- Actor owner 必须来自可信 `ActorContext`，不接受 body/path 中的 owner 覆盖；
- wrong owner、不存在、hidden 统一安全投影，不泄露 PUUID、Riot ID、SQL、正文或 secret；
- 默认正文上限 16 KiB，列表默认 50、最大 100；
- API import/OpenAPI 和 Fake 测试不读取 Key、不连 DB、不访问 Riot/Provider；
- 迁移可逆，`alembic check` 与 metadata 同步；
- 本批不宣称公网 Auth、SLA、跨机容灾或模型领域质量。

## 5. 核心术语和边界

| 名称 | 是什么 | 不是什么 |
|---|---|---|
| Actor/owner | 使用 RiftCoach 的应用主体 | Riot PUUID、客户端传入的任意字符串 |
| player_subject | 以完整 PUUID 表示的稳定外部玩家主体 | Riot ID 显示名、登录 Session |
| relationship | 一个 owner 对某 subject 的用途/验证关系 | 全局共享的私人画像 |
| Conversation | 固定关系的 Coach 讨论容器 | Auth Session、Agent Runtime run |
| Message | 容器内有序、有限的文本记录 | Prompt 全文、tool body、模型 reasoning |

关系层已经在 6B-1/6B-2 建立；6B-3 只读取并冻结它，不重复解析 Riot ID。

## 6. 数据模型

### 6.1 `conversations`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `conversation_id` | UUID PK | 服务器生成，不由客户端指定 |
| `schema_version` | `1.0` | 迁移和 DTO 版本 |
| `owner_id` | bounded string | Actor 作用域 |
| `relationship_id` | UUID | owner-local 关系 |
| `player_subject_id` | UUID | 创建时复制，之后不可变 |
| `relationship_role` | `self|observed` | 创建时复制，之后不可变 |
| `idempotency_key` | bounded string | owner-scoped 重试身份 |
| `request_fingerprint` | 64 hex | schema + relationship 的摘要 |
| `status` | `active|archived|hidden` | 生命周期 |
| `next_message_sequence` | integer >= 1 | 下一条消息序号 |
| `created_at` | timestamptz | UTC |
| `updated_at` | timestamptz | 最近控制面变更 |
| `last_message_at` | timestamptz nullable | 最近成功 append |
| `hidden_at` | timestamptz nullable | hidden 时必填 |

关键约束：

```text
UNIQUE(owner_id, idempotency_key)
UNIQUE(conversation_id, owner_id, relationship_id, player_subject_id, relationship_role)
FOREIGN KEY(owner_id, relationship_id, player_subject_id, relationship_role)
  → owner_player_relationships(owner_id, relationship_id, player_subject_id, relationship_role)
CHECK(status shape, next_message_sequence >= 1, timestamp order)
```

复合 FK 防止“拿到一个合法 relationship_id，却把别人的 owner/subject/role 拼进来”。它仍然
不判断 relationship `status`，所以 Service 必须锁父行并检查 active。

### 6.2 `conversation_messages`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `message_id` | UUID PK | 服务器生成 |
| `conversation_id` | UUID | 容器 |
| `owner_id` / `relationship_id` / `player_subject_id` / `relationship_role` | 完整复合 tuple | 与 Conversation 一致，防跨作用域写入 |
| `sequence_no` | integer >= 1 | Conversation 内有序编号 |
| `role` | `user|assistant` | schema 保留 assistant，公共 6B-3 只写 user |
| `content` | text | 1..16384 字符，非空 |
| `content_sha256` | 64 lowercase hex | 服务端按最终 UTF-8 正文计算 |
| `source_task_id` | UUID nullable | 未来 terminal 的 body-free 引用，无强 FK |
| `source_run_id` | bounded string nullable | 未来 terminal 的 body-free 引用，无强 FK |
| `created_at` | timestamptz | UTC |
| `hidden_at` | timestamptz nullable | 为后续生命周期保留 |

约束：

```text
UNIQUE(conversation_id, sequence_no)
FOREIGN KEY(conversation_id, owner_id, relationship_id, player_subject_id, relationship_role)
  → conversations(同序复合 unique)
CHECK(role, content length/blank, digest shape, sequence >= 1)
```

Message 的绑定字段、role、sequence、正文和 digest 视为 append-only；Repository 不提供更新
方法，migration trigger 禁止绕过 ORM 修改这些字段。后续如果需要隐藏单条消息，只允许单独的
`hidden_at` 生命周期用例。

## 7. 事务和控制流

### 7.1 创建 Conversation

```text
HTTP body {relationship_id}, Header Idempotency-Key
  ↓
ActorContext → owner_id（服务器事实）
  ↓
ConversationService 校验 UUID/key/fingerprint
  ↓
BEGIN
  SELECT relationship WHERE owner_id=? AND relationship_id=? FOR UPDATE
  ├─ 不存在/非 active → safe domain error，ROLLBACK
  ├─ 已存在 owner+key → fingerprint 相同 replay；不同 conflict
  └─ active → 复制四元组并 INSERT conversation
COMMIT
  ↓
201 created / 200 replay / 409 conflict
```

锁住 relationship 是关键：如果另一个事务同时把 relationship 设为 hidden，二者按同一锁顺序
串行，不能出现“检查时 active、提交时已 hidden”的窗口。创建不会调用 Riot、模型或文件系统。

### 7.2 追加 user Message

```text
HTTP body {content}
  ↓
ActorContext + conversation_id
  ↓
Service 规范化/验证（不改变正文）并计算 digest
  ↓
BEGIN
  SELECT relationship FOR UPDATE（owner scoped）
  SELECT conversation FOR UPDATE
  ├─ 不存在/hidden/relationship hidden → 404-equivalent
  ├─ archived → 409 conversation_archived
  └─ active → n = next_message_sequence
       INSERT message(sequence_no=n, role=user, content, digest)
       UPDATE conversation(next=n+1, timestamps)
COMMIT
  ↓
201 MessageResponse
```

事务内没有 `MAX(sequence_no)+1`，也没有外部调用。两个 writer 会在同一行锁上排队，拿到
不同的 n；任一事务失败时计数器和插入一起回滚。

### 7.3 读取和列表

所有读取都带 `owner_id`，并 join/filter `relationship.status='active'` 或 Conversation
非 hidden。Conversation 是 archived 时仍可读取；Message 列表按 `sequence_no ASC`，使用
`after_sequence` + `limit` 的稳定分页，默认 50、最大 100，拒绝无界查询。

### 7.4 生命周期

```text
active ──archive──> archived
   │                    │
   └──────hide──────────┴──> hidden
```

V1 不提供 unarchive/unhide。archive/hide 使用 relationship→conversation 的锁顺序和条件更新；
append 要么在 archive 提交前完成并属于 active，要么在之后被拒绝，不产生“最终 archived 仍有新消息”
的半状态。

## 8. HTTP 合同

### `POST /conversations`

请求：

```json
{"relationship_id":"<UUID>"}
```

只允许这一个字段，`Idempotency-Key` 必填。响应不包含 PUUID、完整 Riot ID 或 verification
内部字段；可以返回 conversation ID、status、relationship ID、时间和 disposition。

### `GET /conversations/{conversation_id}`

owner-scoped。不存在、其他 owner、hidden Conversation、hidden relationship 均返回同一个 404
错误码 `conversation_not_found`。

### `POST /conversations/{conversation_id}/messages`

请求只允许 `{"content":"..."}`。没有 `role`、source、owner、subject、PUUID 字段；因此
客户端无法伪造 assistant。新 user message 返回 201。

### `GET /conversations/{conversation_id}/messages`

query：`limit=1..100`、`after_sequence>=0`。响应只返回 owner 自己的有序正文和公开角色，
不返回内部 source refs。

### `POST /conversations/{conversation_id}/archive` / `/hide`

无 body。archive 后可读不可写；hide 后对 owner 立即 404-equivalent。二者都没有 un* 路径。

## 9. 错误投影

| 内部原因 | HTTP | 公共代码 |
|---|---:|---|
| UUID/body/key/内容非法 | 422 | `request_invalid` |
| 不存在、越权、hidden | 404 | `conversation_not_found` |
| 同 key 不同 fingerprint | 409 | `conversation_idempotency_conflict` |
| archived append | 409 | `conversation_archived` |
| DB/migration/完整性失败 | 503 | `service_unavailable` |

错误正文不回显 SQL、异常、PUUID、Riot ID、Message 正文或 Provider body。日志只允许 task/run/
conversation UUID、状态、allowlist reason 和 latency；正文只在 owner-scoped 正常响应中返回。

## 10. 代码地图（实现后应保持）

```text
app/conversations/models.py       # enum、值对象、命令、视图、校验/digest
app/conversations/ports.py        # Repository/Service Protocol
app/conversations/service.py      # 业务不变量和安全错误
app/persistence/conversation_records.py
                                  # SQLAlchemy ORM + metadata constraints
app/persistence/conversation_repository.py
                                  # 短事务、FOR UPDATE、owner scope、分页
app/api/conversation_models.py    # strict public DTO（无特权字段）
app/api/main.py                   # thin routes/projection
app/api/composition.py            # lazy proxy/lifespan binding
migrations/versions/0003_...py   # PostgreSQL tables/FK/CHECK/index/trigger
migrations/env.py                 # import ORM records for metadata
tests/test_conversation_models.py
tests/test_conversation_service.py
tests/test_conversation_api.py
tests/test_conversation_postgres.py
tests/test_conversation_migrations_postgres.py
tests/test_conversation_concurrency_postgres.py
```

## 11. 分层测试计划

### 红灯先行

1. 纯模型：enum、严格 DTO、key/fingerprint、内容控制字符、digest、sequence/status shape；
2. Service/Fake：active 检查、replay/conflict、owner scope、archive/hidden、assistant 公开拒绝；
3. API：Actor 注入、extra-forbid、错误映射、OpenAPI 和 import no-I/O；
4. PostgreSQL migration：upgrade/downgrade、表/约束/索引/trigger、metadata head；
5. PostgreSQL Repository：创建、追加、回滚、跨 owner FK、直接 SQL rebind；
6. 并发：双 writer 序号、hide/create、archive/append、幂等竞态；
7. 比例回归：相邻 API/任务/6B-2、完整 pytest、RAG/Harness/compile/security/governance/diff；
8. 公共 exact-SHA：`pytest`、`postgres-migrations`、`packaging-smoke` 全绿。

本机没有 PostgreSQL/Docker 时，真实数据库测试必须显示 skip；SQLite 不能替代 PostgreSQL
证据。开发/CI 的 Riot、Provider 和 API key I/O 必须为 0。

## 12. 退出条件与面试边界

### 退出条件

- 所有上述 FR/NFR 有代码、测试和 CI 对应证据；
- `coverage.yaml` 的 6B-3 八维证据全部非空；
- 新增实现后 walkthrough，包含一次真实失败/修复记录；
- canonical 只在 exact-SHA 三 job 全绿后改为 complete，并交接 6B-4。

### 可以准确说

> 我把 Conversation 设计成 owner-scoped、创建即固定 player subject 的关系型控制面；创建时
> 锁定 active relationship，消息用 Conversation 行锁分配连续序号，数据库复合 FK 和 trigger
> 防止跨主体错绑与重绑，HTTP 层只允许 user Message，并用 PostgreSQL 并发测试验证语义。

### 不能说

- “已经接入了 Agent/Memory/多 Agent”；
- “assistant 回复已经由模型生成并持久化”；
- “复合 FK 自动保证 relationship active”；
- “SQLite 测试证明了 PostgreSQL 并发正确”；
- “已有公网 Auth/RSO 或生产级会话安全”。
