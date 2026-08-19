# ADR-0040：采用固定身份的 Conversation/Message 基础合同

- 状态：Accepted（6B-3 设计冻结，待实现与 PostgreSQL exact-SHA CI 验证）
- 日期：2026-08-20
- 范围：阶段 6B-3 `conversation-message-foundation`
- 相关：ADR-0039、`2026-08-19-stage6-session-memory-design.md`

## 背景

6B-1/6B-2 已经把 Riot ID 解析为稳定的 `player_subject`，并把它挂到
owner-scoped 的 `owner_player_relationships`。下一步需要一个能长期保存教练对话的
Conversation 和有序 Message，但这一层容易把几个不同概念混在一起：登录 Session、Agent
Runtime run、Review Task、玩家身份和聊天消息并不是同一个实体。

本批必须先建立控制面，不启动模型、Riot API、Review Task 或长期 Memory。否则会在还没有
稳定身份和消息语义时，把临时文本当成助手终态或把可变 Riot ID 当成会话主键。

## 决策

### 1. Conversation 在创建时冻结 owner/relationship/subject

公共创建请求只允许 `relationship_id`，owner 由可信 `ActorContext` 注入；客户端不得提交
`owner_id`、`player_subject_id`、PUUID、Riot ID、role 或 verification status。

创建事务按以下顺序执行：

```text
owner-scoped SELECT relationship FOR UPDATE
→ 要求 relationship.status = active
→ 从同一行复制 owner/relationship/subject/role
→ INSERT conversation
→ COMMIT
```

复合外键只证明 relationship identity 存在，不能证明它仍是 active；因此必须有行锁后的
状态检查。所有会改变 relationship 状态的实现也必须使用同样的锁顺序。Conversation 的四个
绑定字段没有 rebind 用例，并由 PostgreSQL trigger 拒绝直接 SQL 更新。

### 2. Conversation 创建采用 owner-scoped 幂等

`POST /conversations` 必须带 `Idempotency-Key`。数据库唯一约束为
`(owner_id, idempotency_key)`，fingerprint 覆盖 schema version 和 relationship ID：

- 同 owner、同 key、同 fingerprint：返回原 Conversation，投影为 `replayed`；
- 同 owner、同 key、不同 fingerprint：返回安全的 409；
- 不同 owner 可以使用相同 key，不互相观察。

新建返回 201，重放返回 200。这样网络超时重试不会制造两个 Coach 房间。

### 3. Message 的公共写入只允许 user

数据库 `role` 合同保留 `user|assistant`，以便未来接入可信 Runtime terminal；但 6B-3 的
公共 Service 和 HTTP API 只暴露 `append_user_message()`。本批不提供客户端可调用的
assistant 写入接口，也不实现 Agent/Review/Harness 执行。未来 assistant 写入必须来自
有 `source_run_id`/terminal proof 的内部接缝，并在 6B-8 另行验收。

System prompt、developer 指令、tool payload、provider 原始响应和 reasoning 不属于公共
Message。

### 4. Message 序号由 Conversation 行锁分配

`next_message_sequence` 初始为 1。一次 append 在同一个短事务中：

```text
SELECT conversation FOR UPDATE
→ 校验 owner、relationship active 和 Conversation status
→ 取当前 next_message_sequence 作为 sequence_no
→ INSERT message
→ next_message_sequence += 1，更新 last_message_at
→ COMMIT
```

`UNIQUE(conversation_id, sequence_no)` 是第二道保护。事务回滚会同时回滚计数器和消息，
因此已提交消息的序号连续；不使用客户端时间或 `MAX(sequence_no)+1`。

### 5. 生命周期分为 active、archived、hidden

- `active`：可读取、可追加 user message；
- `archived`：可读取，不可追加；V1 不提供 unarchive；
- `hidden`：对 owner 的读取、追加、归档均投影为 404-equivalent；V1 不提供 unhide。

`active/archived` 要求 `hidden_at IS NULL`，`hidden` 要求非空。Relationship 被 hidden 时，
相关 Conversation 立即按 owner 视为不可见；查询不能只看 Conversation 自身 status。

### 6. 内容和完整性由应用与数据库双重约束

Message 正文必须 trim 后非空、最多 16 KiB Unicode 字符，拒绝 C0/C1 控制字符（允许
`\\n`、`\\r`、`\\t`），保留其余文本的原始字节。服务端按最终保存的 UTF-8 文本计算小写
SHA-256，客户端不能提交 digest。数据库再次检查长度、非空和 digest 形状。

公共 user message 不接受 source task/run 引用；未来内部 assistant 写入才可设置 body-free
引用。Task/Run 生命周期独立，因此这些可选引用不建立阻塞删除的强外键。

### 7. PostgreSQL 是唯一生产语义基线

ORM 负责映射，Alembic 0003 负责表、复合 FK、CHECK、索引和 immutable trigger。SQLite
或 Fake 只能验证纯逻辑/API 投影，不能证明 PostgreSQL 的 FK、trigger、事务回滚或并发序号。
缺少本地 PostgreSQL 时必须显式 skip，由 blocking CI 的 PostgreSQL 17 job 补齐。

## 被拒绝的方案

| 方案 | 拒绝原因 |
|---|---|
| 用 Riot ID 作为 Conversation 主键 | Riot ID 可改名、可重指向，不能保证稳定身份 |
| 只保存 `conversation_id` 外键 | 无法防止跨 owner/subject/role 的错绑 |
| 只在 Service 检查 relationship active | 检查与插入之间存在 hide/create 竞态 |
| 让客户端提交 owner/PUUID/role | 越权和身份污染；Actor 必须是服务器事实 |
| 公共 `role=assistant` POST | 没有 Runtime/Harness terminal 证明，容易伪造教练回复 |
| `MAX(sequence_no)+1` 或客户端时间排序 | 并发下重复/丢序，时间不能承担顺序语义 |
| Redis/聊天框架作为真源 | 引入双写、删除传播和新运维面；当前没有 Bad Case 支撑 |
| 强 FK 绑定 Task/Run | Task 生命周期独立，删除会阻塞消息历史 |

## 后果与边界

正面结果是：会话从出生起就绑定稳定玩家主体，消息顺序和 owner 隔离可以被数据库与
Repository 共同证明，网络重试不会复制会话，6B-3 可在零外部 I/O 下独立测试。

本 ADR 不声称已经实现：Agent 调用、可信 assistant terminal、Review Task 2.0、Memory
Candidate、长期 Memory、Auth/RSO、SSE、前端或公网生产鉴权。这些分别属于 6B-4、6B-5、
6B-8、阶段 8 或后续 ADR。

## 验收门

实现必须先红灯后绿灯，并同时具备：纯模型/API Fake 测试；PostgreSQL migration、trigger、
复合 FK、回滚和并发测试；完整回归、治理、compile/secret/tracked-data 门；提交对应的
exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。任何一个阻塞门失败，
6B-3 不能关闭或推进到 6B-4。
