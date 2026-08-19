# Stage 6 Session/Memory V1 设计

## 1. 结论

RiftCoach 的 Session/Memory V1 采用下面这条主链：

```text
trusted ActorContext.owner_id
→ 异步 Player Link（Account-V1 解析稳定 PUUID）
→ Player Subject + owner-local Relationship
→ 固定一个 subject 的 Conversation
→ Conversation-bound review task / message
→ existing Skill + AgentRuntimeV1 + ReviewHarness
→ Message / Run Artifact
→ Memory Candidate
→ deterministic write gate / user confirmation
→ typed long-term Memory
→ bounded data-only Context selection
```

核心技术选择是：

1. Player Link 独立异步执行，不在 API 同步查 Riot，也不把 link 偷塞进 Review Task；
2. PostgreSQL 是 Session/Memory V1 唯一权威存储；
3. Conversation 创建时固定 `owner + relationship + player subject`，生命周期内不可切换；
4. Memory 使用关系型身份/状态骨架、分类型业务表和严格的有界 JSONB 值；
5. 模型只能提出 Memory Candidate，不能直接永久写画像；
6. Context V1 用确定性 SQL 和现有 ContextBuilder 做有界选择，不上向量库；
7. 按 6B-1 至 6B-9 九个原子批次实施，每批独立验证、提交、推送和公开 CI。

本设计不实现正式 Auth/RSO/HTTPS、SSE/前端、标准 MCP、Multi-Agent、自动任务恢复、Redis、
向量索引、LangGraph 或新 Agent SDK。它也不运行真实 Riot/Provider 请求。

## 2. 给初学者的底层心智模型

### 2.1 六类数据不能混为一谈

| 数据 | 回答的问题 | 生命周期 | 例子 |
|---|---|---|---|
| Task/Run | 一次工作执行到哪里、为何结束 | 一次异步工作 | queued/running/succeeded、run_id、Trace |
| Conversation/Message | 用户正在和 Coach 讨论什么 | 一个对话 | 用户追问、Assistant 回复 |
| Working Context | 这一次模型真正需要看到什么 | 单次运行，派生数据 | 最近消息、选中的 Memory、当前事实 |
| Long-term Memory | 跨会话仍值得保留的 owner/player 状态 | 可更正、过期、删除 | 报告语言、训练目标、历史训练计划 |
| Fact/Artifact | 比赛与运行真正发生了什么 | 领域事实/运行证据 | Summary、确定性报告、final Artifact |
| RAG Knowledge | 外部共享知识是什么 | 知识库版本 | 英雄机制、版本说明、训练原则 |

Task 不是 Session：一个 Conversation 可以产生多次 Review Task；一个 Task 完成后 Conversation 仍存在。

Memory 不是聊天记录：聊天记录是来源，只有经过写入门的少量信息才成为长期 Memory。

Memory 也不是 RAG：Memory 属于某个 owner 或 owner-player；RAG 是所有用户共享的外部知识。

原始比赛事实不能抄进 Memory 冒充个性化：确定性 Summary/Artifact 保持自己的 Schema，Memory 只保存
有复用价值的状态、结论引用或训练进展。

### 2.2 为什么模型不能直接写 Memory

模型输出是概率生成。它可能把一句临时表达误解成稳定偏好，也可能把报告里的推测误写成“玩家习惯”。
如果这种内容直接进入下一轮上下文，错误会自我强化：

```text
一次错误推断
→ 写入画像
→ 下一轮模型把画像当事实
→ 生成更多相同结论
→ 错误越来越像“长期事实”
```

所以模型只能生成 Candidate。确定性代码检查来源、目标作用域、类型、角色权限、冲突、确认要求和版本，
然后才接受或拒绝。这个写入门才是“长期 Memory 安全”的核心，不是选择哪个向量数据库。

### 2.3 PUUID、Riot ID 和 RiftCoach owner 的区别

```text
owner_id              RiftCoach 当前可信用户身份
PUUID                  Riot 公开账号的稳定技术身份
Riot ID                可变的 gameName#tagLine 显示别名
relationship           某 owner 如何使用某 player subject
```

Riot ID→PUUID 只说明账号可查询，不说明 owner 控制该账号。因此：

- `claimed_self` 必须显示“未验证”；
- `public_observed` 只能做公开分析和 owner-local 观察；
- 任何关系都不能解锁非公开 Riot 数据；
- 相同 PUUID 在不同 owner 下不能共享私人 Memory；
- verified-self 当前没有创建路径。

## 3. 当前代码接缝与真正缺口

6A 的当前数据流是：

```text
POST /reviews/recent
→ ActorContext.owner_id + RecentReviewProductRequest(riot_id)
→ ReviewTaskService 持久化 queued review task
→ ReviewWorker claim
→ RecentReviewTaskExecutor
→ RecentReviewApplicationService._build_summary()
→ RiotPlayerSummaryBuilder.build()
→ Account-V1 才得到 PUUID
→ Match-V5 / Runtime / Harness / Artifact
```

关键事实：

- `app/api/main.py` 明确 API 只负责 HTTP、Actor 与短事务入队；
- `app/tasks/models.py` 的 task kind 目前只有 `recent_review`；
- Review Task 的合法 success 必须携带 publication/Trace/receipt/Artifact；
- `app/persistence/task_record.py` 目前没有 conversation 或 subject；
- `app/lol/player_summary.py` 在完整 Review Worker 执行中才解析 PUUID；
- Riot Client 和 Key 只存在于 Worker composition，API composition 没有 Riot 依赖。

因此不能在当前 POST 时直接创建正式 Conversation，也不能把可变 Riot ID 伪装成 subject。需要在 Review
之前增加一个窄、可持久、可查询的身份解析工作流。

## 4. 功能与非功能要求

### 4.1 功能要求

1. 用户可以提交外服 Riot ID、routing region 和用途 `self|observed`，异步建立 player link；
2. link 成功后返回本地 `player_subject_id` 与 `relationship_id`，不返回完整 PUUID；
3. 相同 owner/请求可幂等复读；并发解析相同 PUUID 只能生成一个 subject；
4. link 成功前不能创建 Conversation；
5. Conversation 固定一个 owner-local relationship/subject，不提供切换 endpoint；
6. Message 按 Conversation 有序保存，并保持 user/assistant 正文边界；
7. Conversation-bound Review Task 从服务器 Conversation 继承身份，客户端不能传 PUUID/subject/owner；
8. 所有长期写入先形成 Candidate；
9. 用户可查看、确认、拒绝、更正、导出和删除 Memory；
10. claimed-self 可以有画像/计划/进度，但持续标记未验证；
11. public-observed 只能有公开趋势和第三人称观察，不能有私人画像/计划/完成度；
12. Context 只选择 active、未过期、同 owner/subject 的合法记录。

### 4.2 非功能要求

- PostgreSQL 是唯一真源；真实 migration、constraint、并发和事务必须由 PostgreSQL 17 CI 验证；
- API 不读取 Riot/Provider Key，不做外部网络 I/O；
- 外部调用期间不持有数据库锁；
- 公开 DTO、日志、Trace 不包含完整 PUUID、Riot ID、Message/Memory 正文、Prompt、Provider body 或 Secret；
- owner 不存在与越权统一投影 404；
- 每个批次保持可逆 migration、向后兼容读取和独立 exact-SHA CI；
- 不宣称公网 Auth、99.9% SLA、跨机容灾或模型领域质量；
- 作品集规模下 warm Conversation/Memory 查询目标 p95 `<300ms`，但只有真实样本才可声称达到；
- Context selection 有硬数量/大小上限，禁止无界加载全部历史。

## 5. 总体架构

```text
Client
  │
  │ POST /player-links + Idempotency-Key
  ▼
FastAPI ── trusted ActorContext
  │ short transaction
  ▼
PostgreSQL player_link_tasks (queued)
  │ SKIP LOCKED
  ▼
PlayerLinkWorker
  │ transaction outside: Riot Account-V1
  │
  └─ short resolve transaction
       ├─ player_subjects
       ├─ player_aliases
       ├─ owner_player_relationships
       └─ player_link_tasks succeeded/failed

Client
  │ POST /conversations {relationship_id}
  ▼
ConversationService
  ├─ verifies owner relationship
  └─ freezes owner/relationship/subject/role

Conversation-bound typed turn
  │
  ├─ Conversation messages
  ├─ current deterministic facts / Artifact
  ├─ active typed Memory selected as data-only
  ▼
existing Skill → AgentRuntimeV1 → ReviewHarness
  │
  ├─ terminal Message / Run Artifact
  └─ Memory Candidate → write gate → typed Memory
```

API 与两个 Worker 仍属于同一个模块化单体，只是不同进程角色。PlayerLinkWorker 不是第二个 Agent，
也不是 Multi-Agent；它只是后台执行 Account-V1 的普通确定性 Worker。

## 6. Player Link 身份模型

### 6.1 RoutingRegion 与 Riot ID 输入

Link Request 使用严格字段：

```text
routing_region = americas | asia | europe | sea
riot_id         = normalized gameName#tagLine
role            = self | observed
```

`zh_CN` 是 Data Dragon 语言，不是中国大陆服务器路由；它不能作为 routing region。当前没有 `cn` 值。

客户端不提交 verification status。服务器根据 role 推导：

```text
self     → unverified_claim
observed → not_applicable
```

### 6.2 `player_subjects`

逻辑字段：

| 字段 | 含义 |
|---|---|
| `player_subject_id UUID PK` | RiftCoach 内部公开主体 ID |
| `game` | V1 固定 `lol` |
| `puuid` | 稳定 Riot identifier；数据库内保存，不公开 |
| `current_routing_region` | 最近成功解析的 routing hint |
| `created_at/updated_at/last_resolved_at` | UTC 时间 |

约束：

- `UNIQUE(game, puuid)`；PUUID 是 subject identity，routing region 不是主键；
- game/check、非空、安全长度；
- PUUID 不进入普通结构化日志、Trace 或 HTTP response。

Routing region 作为最近成功查询提示而不是 identity 一部分，可以避免账号跨区域变化后为同一 PUUID 创建
重复 subject。

### 6.3 `player_aliases`

Alias 记录一次已由 Riot 响应确认的显示身份：

| 字段 | 含义 |
|---|---|
| `player_alias_id UUID PK` | alias 记录 ID |
| `player_subject_id` | subject FK |
| `routing_region` | 解析时使用的 routing |
| `game_name/tag_line` | 最近 Riot 返回的显示值 |
| `normalized_riot_id_hash` | 可用于幂等/检索的不可逆摘要 |
| `first_seen_at/last_seen_at` | 观察时间 |

同一 alias 历史上可能指向不同 PUUID，所以不设全局 alias→subject 唯一约束。现有 Conversation 永远不因
alias 后来重指向而变更。完整 Riot ID 不写入通用日志；API 可以在 owner 已知范围内返回显示别名。

### 6.4 `owner_player_relationships`

| 字段 | 含义 |
|---|---|
| `relationship_id UUID PK` | owner-local 关系 ID |
| `owner_id` | trusted owner |
| `player_subject_id` | subject FK |
| `relationship_role` | `self|observed` |
| `verification_status` | `unverified_claim|not_applicable|rso_verified` |
| `status` | `active|hidden` |
| `created_at/updated_at/hidden_at` | UTC 时间 |

约束：

- `UNIQUE(owner_id, player_subject_id)`，同一 owner 对同一 subject 只有一个当前关系；
- 角色/验证组合 CHECK；
- composite unique `(owner_id, relationship_id, player_subject_id, relationship_role)` 供下游外键；
- 现有 Service 拒绝创建 `rso_verified`；
- 同 subject 已是 observed，新的 self link 不静默改角色，返回 `relationship_role_conflict`，以后由显式变更
  用例处理。

### 6.5 `player_link_tasks`

Link Task 独立于 Review Task：

| 分组 | 字段 |
|---|---|
| identity | `link_task_id`, `task_kind=player_link`, `schema_version=1.0` |
| ownership | `owner_id`, `worker_id` |
| request | `idempotency_key`, `request_fingerprint`, normalized `game_name`, normalized `tag_line`, routing region, alias hash, role |
| lifecycle | `queued|running|succeeded|failed`, timestamps |
| terminal | allowlisted reason、subject/relationship（仅 success） |

状态机：

```text
queued → running → succeeded | failed
```

V1 不自动 retry、running→queued 或 lease reclaim。429/timeout/unavailable 可在 View 中标记 retryable，用户
用新 idempotency key 显式创建新任务；不能趁 link 流程偷偷实现阶段 8 恢复运行时。

`game_name` 与 `tag_line` 是后续 Worker 调用 Account-V1 所必需的 bounded private SQL input：必须在 queued
task 中按严格长度和控制字符规则规范化并持久化，不能只保存 hash。它们不得进入普通日志、Trace、公开运行
结果或 Prompt；成功后 API 只按既有 allowlist 返回 Riot 响应确认的显示别名。`request_fingerprint` 仍覆盖
规范化后的 name/tag/region/role，因此同一 owner 的相同幂等键不能改变请求。

成功事务必须同时创建/复读 subject、alias、relationship 并写 task success。失败终态不能含 subject 或
relationship。`owner_id + idempotency_key` 唯一；同 key 同 fingerprint 返回原 task，不同 fingerprint
返回 409。

### 6.6 Link 失败与 crash window

| 场景 | 安全结果 |
|---|---|
| Riot 404 | failed `player_not_found`，无 subject/relationship |
| 401/403 | failed `riot_authentication_failed`，不冒充玩家不存在 |
| 429 | failed `riot_rate_limited`，retryable=true |
| timeout | failed `upstream_timeout`，retryable=true |
| unavailable | failed `upstream_unavailable`，retryable=true |
| 响应缺 PUUID/字段坏 | failed `account_response_invalid` |
| lookup 后、事务前 crash | DB 没有身份副作用；V1 不自动 reclaim/retry，原 task 可能保持 running/recovery-required，后续只能按显式运维或新请求容量规则处理 |
| resolve 事务 commit 后 crash | subject/relationship/task 已一起成功，GET 可复读 |
| commit 结果未知 | 先 owner-scoped GET task，不盲目再次写入 |
| 并发相同 PUUID | UNIQUE + `ON CONFLICT` 收敛为一个 subject |

## 7. Conversation 与 Message

### 7.1 `conversations`

Conversation 就是 Coach 会话，不另建含糊的“登录 Session”表。

| 字段 | 含义 |
|---|---|
| `conversation_id UUID PK` | 会话 ID |
| `owner_id` | trusted owner |
| `relationship_id/player_subject_id/relationship_role` | 创建时冻结的复合作用域 |
| `status` | `active|archived|hidden` |
| `next_message_sequence` | 原子分配消息序号 |
| `created_at/updated_at/last_message_at/hidden_at` | UTC 时间 |

使用 composite FK 指向 active relationship identity。PostgreSQL trigger 拒绝更新四个绑定字段；Repository
也不提供 rebind。`archived` 只阻止新 turn，不改变 subject；`hidden` 对 owner 查询立即不可见。

### 7.2 `conversation_messages`

| 字段 | 含义 |
|---|---|
| `message_id UUID PK` | 消息 ID |
| 完整 owner/conversation/relationship/subject tuple | 防止跨作用域写入 |
| `sequence_no` | Conversation 内严格递增 |
| `role` | V1 仅 `user|assistant` |
| `content` | 有界文本，默认最大 16 KiB 字符 |
| `content_sha256` | 完整性/幂等摘要 |
| `source_task_id/source_run_id` | 可选 body-free 来源 |
| `created_at/hidden_at` | UTC 时间 |

`UNIQUE(conversation_id, sequence_no)`。序号通过一条 Conversation row lock/原子递增分配，事务只包含消息
插入，不在锁内运行模型。System Prompt、Tool body、Provider reasoning/response 不进入 Message 表。

Assistant message 只能在 Runtime/Harness 形成可信 terminal 后落库；若运行失败，保存安全 failure state，
不把未经发布的 draft 伪装成 Assistant 回复。

## 8. Conversation-bound Review Identity

新端点最终为：

```text
POST /conversations/{conversation_id}/reviews/recent
body = count + queue + focus
```

客户端不再传 owner、Riot ID、PUUID、subject 或 relationship。Application 从 trusted Conversation 得到：

```text
owner_id + conversation_id + relationship_id + player_subject_id
```

新 Review Task schema 2.0 保存该不可变 tuple。现有 1.0 历史 row 保持可读，不凭旧 Riot ID 静默回填
subject。新路径通过 PUUID 拉 Match-V5；它不应再次用可变 Riot ID 做 Account-V1 解析。Summary Builder
增加 trusted `build_by_puuid()` 接缝，并使用已确认 alias 仅作显示。

旧 `/reviews/recent` 在兼容窗口内仍可工作，但不产生 Conversation/Memory，也不能被描述为长期 Coach
入口。保留期结束前通过明确 deprecation/exit review 决定是否移除。

## 9. Memory Candidate 与写入门

### 9.1 Candidate 为什么是单独实体

Candidate 把“模型/规则提出了什么”与“长期状态最终是什么”分开。即使被拒绝，也能保留有限、可审计的
body-free 决策记录，而不会污染 active Memory。

### 9.2 `memory_candidates`

逻辑字段：

| 分组 | 字段 |
|---|---|
| identity | `candidate_id`, schema/version |
| source | conversation/message/task/run/Artifact reference + SHA |
| target | `owner_global|owner_player` 与完整 relationship tuple |
| proposal | candidate kind、memory key、operation、严格有界 JSONB、fingerprint |
| provenance | kind、producer id/version、confidence |
| gate | policy version、requires_confirmation、status、decision actor/reason/time |

Candidate 状态：

```text
pending → accepted | rejected | expired
```

accepted 后不能回到 pending。目标长期记录可以以后被 superseded，但 Candidate 本身保持当时决策事实。

### 9.3 Provenance 与 gate policy

V1 provenance：

```text
user_structured_input
user_message_extraction
model_inference
deterministic_run_fact
published_review_observation
```

| 来源 | 是否可 deterministic auto-accept |
|---|---|
| 结构化 UI 明确设置的 allowlisted owner preference | 可以，同事务 |
| 结构化 UI 明确设置的 self profile | 可以，但关系必须 self |
| 用户自然语言抽取 | 不可以，pending |
| 模型推断 | 永远不可以，pending |
| deterministic run fact | 仅 allowlisted review/progress 类型 |
| published review observation | 可记录复盘发生/引用，不可自动写心理或因果画像 |
| Training Plan | 必须用户确认才 active |

`proposal_confidence NUMERIC(4,3)` 的范围为 0..1，但任何阈值都不能把 `model_inference` 自动变成 accepted。

### 9.4 原子 materialization

```text
lock Candidate
→ verify pending + owner/target/source
→ validate target type/relationship role
→ load current active version for memory_key
→ same fingerprint: idempotent replay
→ conflict requiring user decision: remain pending
→ accepted decision:
     old active → superseded（若有）
     insert new active target record
     Candidate → accepted
→ one transaction commit
```

所有目标表使用 `source_candidate_id UNIQUE`，阻止一个 Candidate 被物化两次。

## 10. 分类型长期 Memory

### 10.1 Owner Preference

作用域只到 `owner_id`。保存报告语言、详细程度、称呼风格等，不依赖当前观察哪个玩家。

每个 `owner_id + preference_key` 最多一个 active version；值是 key 对应的严格 typed JSONB，不允许自由
字典。更正插入新 version 并 supersede 旧 version。

### 10.2 Player Profile

作用域是 owner-player 且数据库强制 `relationship_role=self`。适合主玩位置、常用英雄、训练侧重点等
owner 为自己声明或确认的状态。

`claimed_self` 可以使用，但 Context/UI 必须持续显示未验证。`public_observed` 在 Service 与 composite
FK/CHECK 两层都不能创建 Profile。

### 10.3 Review Memory

只保存有来源的复盘情景、允许列表趋势或 owner-local 观察，不复制整份 Summary/报告。

```text
self     → perspective=self_coaching
observed → perspective=third_person_observation
```

observed 仅允许 `observation_note|public_trend`；禁止私人偏好、心理状态、训练承诺与完成度推断。

### 10.4 Training Plan

仅 self relationship。状态：

```text
draft → active → completed | abandoned | superseded
```

V1 每个 relationship 最多一个 active Plan，由 partial unique index 保证。Plan payload 使用严格目标、
周期、允许列表 metric 与完成条件 Schema；active 必须有已接受、用户确认的 Candidate。

### 10.5 Training Progress

仅 self relationship，并 composite FK 到同 owner/subject 的 Training Plan。每条是不可变的 metric
measurement/window：例如某段比赛的 CS/min 或 15 分钟前死亡变化。

来源必须是完整可校验的 run/Artifact，metric 必须属于 active Plan 的 allowlist。纠错插入新 Progress
并 supersede 原记录，不覆盖原数值。public-observed 的公开趋势仍属于 Review Memory，绝不能伪装成对方
完成训练计划。

## 11. Memory-aware Context V1

### 11.1 不建立第二套 Context/Agent

现有 `ContextBuilderV1` 已经区分 system/instructional 与 user/data-only，并受 Skill Manifest Context
ceiling 约束。Session/Memory 只增加一个可信、确定性的上游 selector，把合法记录投影为 data-only
sections；不会让 Memory 直接拼接到 System Prompt，也不会绕过现有 Compiler/Runtime/Harness。

### 11.2 选择算法

输入只能来自服务器：

```text
owner_id + conversation_id + selected Skill + current fact Artifact
```

步骤：

1. owner-scoped 查询 Conversation，并取得冻结 relationship/subject/role；
2. 选择最近完整 Message，按 newest-first 填充后恢复 chronological order；
3. 选择 owner-global active Preference；
4. 若 role=self，选择 active Profile、active Plan、各 metric 最新 active Progress；
5. 选择当前 owner-player 的 active、未过期 Review Memory；
6. 根据 Skill/focus 做 allowlisted key/tag 过滤；
7. 按固定优先级与稳定 tie-breaker 选择完整记录；
8. 用现有 ContextSizer 预估，整项保留或省略，绝不截断 JSON/Message 造成语义漂移；
9. 生成 `memory_context_manifest`，记录 record id/version/value digest/省略原因；
10. 将选中内容以明确 provenance/relationship label 的 data-only sections 交给 ContextBuilder。

### 11.3 硬上限

V1 默认上限由策略配置并受 Skill ceiling 再约束：

- 最近 Message 最多 12 条；
- Owner Preference 最多 16 个 active key；
- Player Profile 最多 16 个 active key；
- active Plan 最多 1 个；
- 每个 Plan metric 最新 Progress 最多 1 条，总计最多 12 条；
- Review Memory 最多 12 条；
- 单条 Message 最大 16 KiB 字符；
- 单条 Memory payload 最大 8 KiB canonical JSON；
- Selector 总 envelope 超限时按固定优先级省略，不允许调用方提高 Manifest ceiling。

这些是本地防御上限，不冒充模型 tokenizer 精确 Token。Runtime/Provider Usage 继续由既有层记录。

### 11.4 禁止进入 Context

- pending/rejected/expired Candidate；
- superseded/retired/hidden/expired 长期记录；
- 其他 owner、subject 或 Conversation 的数据；
- public-observed 的 Profile/Plan/Progress；
- 已删除来源产生且未经重新确认的模型推断；
- Message 中的 system/tool/provider body；
- 完整 PUUID、Secret、内部错误或未公开 Prompt；
- 任何因内容像“系统指令”而提升信任级别的用户/Memory 文本。

### 11.5 Typed Conversation Turn

V1 不立即增加开放域自由聊天 Skill。安全的 `continue_session()` 是产品用例：在同一不可变 Conversation
中继续提交一个已存在、可类型化编译的 review operation，例如新的 recent review focus；Application
重新构造 RuntimeRunRequest，并选择有界 Message/Memory Context。

若未来真实用户需要自由文本 follow-up，必须先证明现有两个 Skill/Router 能正确表达该任务，或者按 Skill
采用门新增独立 workflow、数据集和路由评测。不能只因有 Message 表就把任意自然语言直接送入 Agent。

## 12. 冲突、更正与并发

### 12.1 字段级版本而不是覆盖画像

一个 profile JSON 覆盖写会让两个请求同时修改不同字段时相互丢失，也无法回答“这个字段从哪来”。V1
以 `memory_key + version + status` 管理每个字段，冲突只影响同一个 key。

### 12.2 Optimistic version + partial unique

用户确认更正时提交 expected active version。Repository 在短事务内锁定 Candidate 和 current active row：

- expected version 不匹配：返回 `memory_version_conflict`；
- proposal fingerprint 与 active 相同：幂等复读；
- 值不同且仍需确认：Candidate 保持 pending；
- 确认通过：旧 active superseded，新 active 插入。

Partial unique index 是并发最后防线；应用不能用“先查再插、出错后忽略”的方式掩盖竞争。

### 12.3 关系角色冲突

同 owner/subject 已存在 observed relationship，又提交 self link 时，V1 返回显式
`relationship_role_conflict`。不自动升级、不复制第二个关系，也不把 observed Memory 重新解释为 self
Memory。Repository 必须在 `resolve_link()` 的同一短事务中把 Link Task 原子写为 failed，并且不写 alias、
不修改既有 relationship、失败 terminal 不含 subject/relationship；不能抛错后依赖 Worker 再开一次
`fail_link()` 事务。未来显式关系变更用例必须说明对 Profile/Plan/Conversation 的影响后才能采用。

## 13. 查看、导出、过期与删除

### 13.1 查看

Owner 可以按作用域查看：

- Conversation 与 Message；
- pending/accepted/rejected Candidate 及安全 provenance；
- active 与历史 Preference/Profile/Review Memory；
- Plan/Progress；
- body-free Task/Run/Artifact reference。

Public API 不返回完整 PUUID、Prompt、Provider body、Tool observation 或内部异常。

### 13.2 导出

导出文件使用版本化 Schema 和生成时间，并只从 owner-scoped Repository 读取。导出应保留 relationship
role/verification label、历史 supersede 链和 Candidate decision，使用户能理解 Coach 为什么记住某项
内容。Artifact 只导出引用/SHA，除非其独立导出接口明确允许正文。

### 13.3 Retention

| 数据 | 默认策略 |
|---|---|
| Conversation Message body | 90 天后隐藏/清理 |
| pending Candidate | 30 天过期 |
| rejected/expired Candidate | 决定后 30 天清理 |
| accepted Candidate | 与目标记录同生命周期 |
| active Preference/Profile | 直到删除或 supersede |
| superseded Preference/Profile | 90 天 |
| Review Memory | 365 天，可单项提前过期 |
| completed/abandoned Plan/Progress | 365 天 |
| hidden row physical cleanup | 最迟 30 天 |

Retention 使用 injected clock 和 bounded batch；不通过真实 sleep 测试。

### 13.4 删除范围

用户必须显式选择：

1. `conversation_only`：隐藏 Conversation/Message，不碰已接受长期 Memory；
2. `conversation_and_derived_memory`：同时隐藏来源于该 Conversation 的长期记录；
3. `relationship_private_data`：隐藏该 owner-player 的所有 Conversation/Memory/Plan/Progress。

所有删除先让数据 owner-query 不可见，再做物理清理。清理失败留下 body-free compensation marker，可幂等
重试但不能重新暴露内容。全局 Player Subject 仅在没有任何 owner relationship、Conversation 或保留期引用
后清理。现有 Task/Run/Artifact 生命周期独立，不因删除 Conversation 被静默改写。

## 14. 安全与隐私边界

### 14.1 Broken Access Control 防线

- owner 只来自 `ActorContext`；
- URL/body 中的 owner/PUUID/subject 字段被拒绝或根本不存在；
- 所有 Repository 查询显式 owner-scoped；
- composite FK 把下游 row 绑定到同 owner/relationship/subject/role；
- public-observed 的 self-only 数据在 Service 和数据库两层拒绝；
- 不存在/越权统一 404，避免资源枚举；
- 迟到 task 只能写自己冻结的 tuple，不能读取 UI 当前选择。

### 14.2 Prompt/Context Injection 防线

Message、Memory、alias 与 review observation 都是 data-only。Context manifest 记录来源和摘要；任何正文
包含“忽略系统提示”也不能改变 role、工具权限、预算或写入门。模型提出的 Candidate 仍需 deterministic
gate/用户确认，形成第二道防线。

### 14.3 Secret 与低敏日志

允许日志字段：内部 task/conversation/subject UUID、安全 status/reason、计数、latency、hash prefix。

禁止日志字段：Riot API Key、DB URL、完整 PUUID、完整 Riot ID、Message/Memory/Prompt/报告正文、
Provider/Tool body、request ID、原始异常堆栈。

### 14.4 为什么当前不使用 RLS

当前 production profile 在没有 Auth Provider 时 fail closed，尚无可信 JWT/OAuth subject 能设置数据库
request context。现在加入 RLS 只会复制一个未建立的 owner identity plumbing。V1 先用 existing
ActorContext、owner-scoped Repository 与数据库结构约束；正式 Auth 实现后再通过 ADR 评估 RLS、数据库
最小权限角色和 connection-pool session variable 清理。

## 15. NFR 与可观测性

| 维度 | V1 边界 |
|---|---|
| deployment | 现有单服务器 API + Review Worker + Link Worker + PostgreSQL |
| link worker concurrency | 每进程默认 1；真库证明多 Worker 不重复 claim |
| external call | 事务外，沿用有限 timeout；V1 不自动 retry |
| API latency | create/query 只做 DB；warm p95 目标 `<300ms` |
| context query | 结构化索引 + 硬上限；warm p95 目标 `<300ms` |
| backpressure | link task owner/global active limit 配置化 |
| observability | body-free status/count/latency/reason；无正文 |
| availability | 不宣称 99.9%；单 DB/本地 Artifact 仍是单点 |
| recovery | link resolve 原子事务；review hard-crash 仍沿用 6A 保守 recovery |
| cost | 不新增 Redis/向量/消息队列服务 |

建议索引均从真实查询模式倒推：

- link claim partial/composite index；
- owner link history；
- relationship owner+subject；
- Conversation owner+updated_at；
- Message conversation+sequence；
- Candidate owner+status+created_at 与 target scope；
- typed Memory 的 owner/relationship+key active partial index；
- Review Memory relationship+status+effective_at；
- Plan relationship active partial index；
- Progress plan+metric+measured_at。

所有 foreign key 列都有相应 index；外部调用期间没有长事务。新增性能数字只有 CI/部署实际记录 sample、
environment、p95 后才能进入公开能力表述。

## 16. 测试矩阵

| 层 | 必须证明 |
|---|---|
| pure models | 枚举、状态 shape、role/verification、payload bounds、confidence/write-gate |
| migration | upgrade/downgrade、table/constraint/index/FK/trigger 与 ORM metadata 一致 |
| PostgreSQL repository | idempotency、owner isolation、upsert、partial unique、composite FK、短事务 |
| link concurrency | 双 Worker、同 PUUID/同 owner 收敛、role conflict、terminal CAS |
| link worker | success、404、401/403、429、timeout、bad response、crash boundary、安全 reason |
| API | 202/replay/409/404/503、body-free DTO、ActorContext、API 零外部 I/O |
| Conversation | 只从 active relationship 创建、不可 rebind、跨 owner/subject 拒绝、并发消息序号 |
| review identity | task 精确继承 tuple、client/model 伪造拒绝、PUUID 路径不重查 Riot ID |
| Candidate gate | 模型不能 auto-accept、高 confidence 不能绕门、accepted exactly once |
| typed Memory | observed 禁止 Profile/Plan/Progress、supersede/version/conflict、active uniqueness |
| Context | pending/superseded/expired 排除、owner/subject 隔离、稳定顺序、预算、data-only |
| lifecycle/export | owner-scoped 导出、三种删除、立即隐藏、幂等补偿、injected clock |
| vertical | Fake Riot + Fake Provider + 真实 PostgreSQL + existing Runtime/Harness；外部 calls 0 |
| packaging | Linux API/两个 Worker/DB composition、非 root、image 不含 Secret/私人数据 |

SQLite 不作为 PostgreSQL 约束或并发绿灯。CI 不读取 `.env`，不调用 Riot/GLM/DeepSeek。

## 17. 向后兼容与 migration 策略

### 17.1 Migration 只追加

已公开的 `0001_review_tasks` 不修改。6B 每个数据批次创建新的可逆 Alembic revision；CI 每次执行
`upgrade head → downgrade base → upgrade head → alembic check`。

### 17.2 Legacy Review Task 1.0

现有 task row 没有 subject/conversation。它们保持原合同和 90 天生命周期：

- 仍可 owner-scoped query；
- 不通过重新解析旧 Riot ID 回填 subject；
- 不生成 Conversation 或长期 Memory；
- 新 conversation-bound task 使用 schema 2.0 和不可变 tuple；
- 去除 legacy create endpoint 需要单独 deprecation/exit review。

### 17.3 Alias rename 与 repoint

- 相同 PUUID + 新 Riot ID：增加/刷新 alias，复用 subject/relationship；
- 相同显示 Riot ID + 新 PUUID：创建/复用新 subject，旧 Conversation 保持旧 subject；
- owner 若已对新 subject 有关系则复读；没有则创建；
- 任何流程都不能更新旧 Conversation 的 subject。

## 18. 原子实施顺序

### 6B-1 Player Identity & Link Persistence Foundation

实现 strict domain models、`player_subjects/player_aliases/owner_player_relationships/player_link_tasks`、
Alembic 0002、Repository、Service 与 Fake/真实 PostgreSQL 测试。外部 Resolver、Worker、API、Conversation
均不在本批。

### 6B-2 Async Player Link Worker/API Vertical Slice

实现窄 `RiotAccountResolver` port/adapter、PlayerLinkWorker、POST/GET Link API、composition/CLI、Fake
Resolver 纵向与 Linux no-I/O smoke。该批已由 `0c13a58` / Actions `32301852042` 三 job exact-SHA
公共闭环；package smoke 的外部 Riot/Provider calls 为 0。Conversation 仍未实现。

### 6B-3 Conversation & Message Foundation

实现 Conversation/Message migration、不可变 binding、Repository/Service、创建/读取/归档/消息 API 和
并发顺序测试；不接 Agent 或 Memory。

### 6B-4 Conversation-bound Recent Review Identity

实现 Review Task schema 2.0、Conversation-bound endpoint、trusted tuple、PUUID Summary path、legacy
1.0 compatibility 和 existing Runtime/Harness no-I/O vertical slice。

### 6B-5 Memory Candidate & Write Gate

实现 Candidate migration/model/Repository、provenance/confidence、deterministic gate、用户确认/拒绝、
exactly-once materialization 接缝；暂不创建具体 Memory 表。

### 6B-6 Preferences, Profile & Review Memory

实现三类长期记录、字段级版本、self/observed 权限、supersede/conflict 与 API/query。

### 6B-7 Training Plan & Progress

实现 self-only Plan/Progress、单 active Plan、allowlisted metric、Artifact provenance 和确定性进展比较。

### 6B-8 Memory-aware Context & Typed Conversation Turns

实现 deterministic selector、memory context manifest、ContextBuilder data-only 接线、typed
conversation turn、Message terminal 写入和跨 Skill 回归；不默认新增自由聊天 Skill。

### 6B-9 Lifecycle, Export & Exit Review

实现三种删除范围、retention/purge/补偿、owner export、性能/安全/隔离纵向、package 与完整 exit matrix；
关闭 Session/Memory V1 时仍保留正式 Auth/RSO、SSE/前端和阶段 7/8 deferred。

RQ-064 原允许 entry design exact-SHA 公共闭环后直接进入 6B-1，并在 6B-1 公共闭环后直接进入 6B-2；
较晚的 RQ-065 将当轮收紧为只完成 6B-1，并已在 6B-1 exact-SHA 全绿后停止。RQ-066 现于独立新一轮
只授权 6B-2；该批现已由 `0c13a58` / Actions `32301852042` 公共闭环，并按授权停止在 6B-3
prepared/waiting authorization。它不允许自动实现 6B-3。

## 19. 入口设计退出条件

`stage-6-session-memory-entry-design` 只有同时满足以下证据才关闭：

- ADR-0039、本文与 implementation plan 一致；
- RQ-060 至 RQ-065、canonical、roadmap、amendment、capability matrix、project decisions 无冲突；
- governance、diff、compile/比例回归、安全/Secret 边界通过；
- 提交推送后 exact-SHA GitHub Actions 三 job 成功；
- canonical 只切到 `6B-1-player-identity-link-foundation`；
- 设计批没有创建 migration/schema、读取 Key 或调用 Riot/Provider。

入口设计关闭不等于任何 Session/Memory 产品代码已完成。6B-1 只有在上述公共证据成立后才开始。
