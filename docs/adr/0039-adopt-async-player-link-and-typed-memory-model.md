# ADR-0039：采用独立异步 Player Link 与分类型 PostgreSQL Memory 模型

- 状态：Accepted
- 日期：2026-08-19
- 范围：`stage-6-session-memory-entry-design`
- 需求：RQ-060 至 RQ-066

## 背景

6A 已经形成可重建的 FastAPI + PostgreSQL + polling Worker 任务基座。现有
`POST /reviews/recent` 只在短事务中持久化 `owner_id + Riot ID`，PUUID 要等
Review Worker 调用 `RecentReviewApplicationService` 后才由 Account-V1 解析。

阶段 6 接下来要建立长期 Coach 所需的 Session 与 Memory，但已有边界要求：

- Conversation 创建时必须固定 trusted owner 的一个稳定 player subject；
- Riot ID 是可变显示别名，不能充当 subject 主键；
- Riot ID→PUUID 只证明公开账号可查询，不证明当前 owner 控制账号；
- MVP 同时支持未验证的 `claimed_self` 与受限 `public_observed`；
- 模型不能把一次推断直接永久写入玩家画像；
- PostgreSQL 是 Session/Memory V1 唯一真源；
- 不能把 RAG、原始比赛事实、Task/Run 与长期 Memory 混成一层；
- 不因技术名词引入 Redis、Chroma、向量库、LangGraph、事件溯源或通用 Memory 框架。

当前接缝因此存在一个必须先解决的问题：API 入队时还没有 PUUID，如果直接创建
Conversation，就只能使用可变 Riot ID 或允许 Conversation 以后重绑 subject；两种做法都会
破坏 RQ-063 的身份不变量。

## 决策

### 1. 使用独立异步 Player Link 流程

采用：

```text
POST /player-links
→ PostgreSQL player_link_tasks queued
→ 专用 PlayerLinkWorker 原子 claim
→ 数据库事务外调用 Account-V1
→ 一个 PostgreSQL 短事务：
     upsert player_subject
     record player alias
     create/reuse owner_player_relationship
     link task → succeeded
→ 成功后才允许创建 Conversation
```

`player_link` 不进入现有 `review_tasks`。现有 Review Task 的成功终态必须具备
publication、Trace、receipt 与 final Artifact，而账号解析没有这些语义。为了复用一个表而伪造
Harness 终态会污染两个合同。

Account-V1 网络调用始终发生在事务外。成功解析后的 subject、alias、relationship 和 link terminal
在同一个短事务内提交，避免半个身份关系。API process 不构造 Riot Client、不读取 Riot Key、
不承受上游限流与长尾等待。成功的 Worker 必须从 queued task 读取规范化、bounded 的 `game_name`
和 `tag_line`；只保存它们的 hash 会使后续 resolver 无法工作。完整输入仅作为私有 SQL 数据，
不得进入普通日志、Trace、公开响应或 Prompt。

### 2. 使用稳定 subject、可变 alias 和 owner-local relationship

身份模型分为：

```text
player_subjects
  全局公开账号主体；稳定键是 game + PUUID

player_aliases
  某次已解析的 routing region + Riot ID；可改名、可保留历史

owner_player_relationships
  owner 对 subject 的私有用途和验证状态
```

`player_subjects` 不属于任何 owner。不同 owner 可以引用同一公开 subject，但
relationship、Conversation、备注、训练目标、计划、进度和 Memory 永远不能跨 owner 共享。

Relationship 使用两个维度：

```text
relationship_role = self | observed
verification_status = unverified_claim | not_applicable | rso_verified
```

数据库只允许以下组合：

```text
self     + unverified_claim
self     + rso_verified
observed + not_applicable
```

当前 Application Service 只能创建前两种 MVP 投影中的：

- `self + unverified_claim` → `claimed_self`；
- `observed + not_applicable` → `public_observed`。

当前不存在 `rso_verified` 创建入口。未来只有正式 RiftCoach Auth、安全 RSO callback 与
`/accounts/me` PUUID 精确匹配后，才能通过新 ADR 增加该写路径。

若 `resolve_link()` 发现同一 owner/subject 已存在另一种 role，它必须在当前短事务内把 Link Task 原子写为
`failed/relationship_role_conflict`，不写 alias、不修改 relationship，也不把 subject/relationship 放入失败
terminal。不能先抛异常再由 Worker 调第二次 `fail_link()`；否则两次事务之间的进程崩溃会遗留永久 running。

### 3. Conversation 创建时固定 owner + relationship + subject

Link 成功前不能创建正式 Conversation。Conversation 创建后冻结：

```text
owner_id
relationship_id
player_subject_id
relationship_role
```

Repository 不提供 rebind 方法；PostgreSQL composite foreign key 防止跨 owner/subject 引用，
immutable-binding trigger 防止把整组字段更新成另一个合法 relationship。

消息、Context、review task/run 与 Memory Candidate 都从服务器保存的 Conversation 继承该 tuple。
客户端 body、自由文本、UI 当前选中值和模型输出都不能覆盖它。不同 PUUID 必须创建新 Conversation；
相同 PUUID 改 Riot ID 只更新 alias 观察，不重建 subject 或重绑旧 Conversation。

### 4. Memory 使用混合分型模型

采用“关系型骨架 + 分类型长期记录 + 严格 JSONB 叶子”：

- ownership、外键、角色、状态、版本、时间和唯一性使用普通关系列与约束；
- 各类型内部仍可能演进的小型值使用严格 Pydantic Schema 验证后的有界 JSONB；
- owner preference、player profile、review memory、training plan、training progress 分表；
- 不使用一个覆盖式 profile JSON；
- 不使用万能 `memories(kind, payload)` 表承担全部业务规则。

分表使 PostgreSQL 能直接证明：`public_observed` 不能拥有 Player Profile、Training Plan 或
Training Progress；Progress 必须属于同 owner/subject 的 Plan；每个 relationship V1 最多一个 active
Plan；每个字段键最多一个 active version。

### 5. 所有长期写入先经过 Memory Candidate

任何长期状态变化都先形成 `memory_candidates`。Candidate 明确保存：

- source conversation/message/task/run/Artifact digest；
- target scope：`owner_global` 或 `owner_player`；
- candidate kind、memory key、operation 与严格 payload；
- provenance kind、producer/version、confidence；
- gate policy version、是否需确认、状态和安全 reason code。

`confidence` 只用于排序/展示，不是写权限。写入门规则为：

- 用户在结构化 UI 明确设置的允许列表偏好，可由 deterministic policy 同事务接受；
- 用户自然语言抽取与任何模型推断一律 pending；即使 confidence=1 也不能自动接受；
- Training Plan 必须经用户确认才可 active；
- published review 只能自动记录“复盘发生过”和有 Artifact 支持的允许列表确定性摘要，不能自动
  把心理、习惯或因果推断写成画像；
- Training Progress 只能来自完整、可校验的 run/Artifact，并匹配 active Plan 的允许列表 metric；
- Candidate acceptance 与目标记录 materialization 在一个事务内完成；
- `source_candidate_id` 唯一，保证一个 Candidate 最多物化一次。

### 6. 长期记录采用版本化 supersede，不覆盖历史

Preference、Profile 和可更正的 Review Memory 使用：

```text
active → superseded | retired
```

更正时锁定 Candidate 与当前 active key，校验 expected version，旧记录转 superseded，插入新的 active
记录并指向 `supersedes_id`。PostgreSQL partial unique index 阻止并发产生两个 active version。

Training Plan 使用 `draft | active | completed | abandoned | superseded`；Training Progress 是不可变
测量事件，纠错时插入新事件并 supersede 旧事件，不原地改数值。

### 7. Context V1 使用确定性结构化选择，不使用向量检索

Memory Context 继续接入现有 ContextBuilder/Runtime，而不是创建第二套 Agent 编排。选择顺序：

1. trusted Conversation 关系与未验证/观察标签；
2. 当前 Conversation 最近的完整消息；
3. owner-global active preferences；
4. claimed-self 下的 active Player Profile；
5. claimed-self 下的 active Training Plan 与各 metric 最新 Progress；
6. 当前 owner-player 的近期 active Review Memory；
7. 当前确定性比赛事实；
8. 按 Skill ceiling 整项保留或省略，并记录省略原因。

pending/rejected Candidate、superseded/expired 记录、其他 owner/subject/Conversation、以及
public-observed 的 Profile/Plan/Progress 永不进入 Context。所有 Message 与 Memory 都是 data-only，
不能因内容像指令就升级为 system/instructional。

选择结果形成私有 body-free `memory_context_manifest` Artifact；Runtime Trace 只保存其引用、SHA、
记录数和省略原因，不保存 Memory 正文。

### 8. PostgreSQL 是唯一真源，暂不采用 RLS/Redis/向量索引

V1 使用现有 SQLAlchemy/Alembic/PostgreSQL 基座。Redis 只有真实性能 Bad Case 后才能作为可重建
缓存；向量索引只有结构化召回评测失败后才能作为派生索引。

当前尚无正式 Auth，也没有每个请求对应的可信数据库 session identity。此时引入依赖
`current_setting()` 的 RLS 会增加容易误配的第二套 owner context，不能替代 Repository 的 trusted
ActorContext。因此 V1 使用 owner-scoped Repository、composite foreign key、CHECK/UNIQUE/partial
index 与 immutable trigger 双层保护；正式 Auth 实现后再用新 ADR 评估 RLS 和最小权限数据库角色。

### 9. 生命周期、导出和删除分层

默认策略：

- Conversation message body：90 天；
- pending Candidate：30 天；
- rejected/expired Candidate：决定后 30 天；
- accepted Candidate：与物化记录同生命周期；
- active Preference/Profile：直到删除或 supersede；
- superseded Preference/Profile：90 天；
- Review Memory：365 天，可单项更早过期；
- completed/abandoned Plan 与 Progress：365 天；
- hidden 后立即不可见，最迟 30 天物理清理。

删除操作必须显式区分：只删 Conversation、Conversation 加其派生 Memory、整个 owner-player
relationship。Conversation 删除不能暗中删除已独立展示的长期 Memory。Relationship 删除立即隐藏该
owner 的相关 Conversation/Memory；全局 Player Subject 只有无 owner 引用后才允许清理。Task/Run/
Artifact 继续遵守其既有生命周期。

导出为 owner-scoped、版本化结构，包含关系/验证标签、Conversation/Message、active/history Memory、
Candidate 状态与安全 provenance、Plan/Progress 以及 body-free run/Artifact 引用；不导出 Secret、
Prompt、Provider 原始响应、Tool body 或内部异常。

### 10. 按九个原子批次实施

```text
6B-1 Player Identity & Link Persistence Foundation
6B-2 Async Player Link Worker/API Vertical Slice
6B-3 Conversation & Message Foundation
6B-4 Conversation-bound Recent Review Identity
6B-5 Memory Candidate & Write Gate
6B-6 Preferences, Profile & Review Memory
6B-7 Training Plan & Progress
6B-8 Memory-aware Context & Typed Conversation Turns
6B-9 Lifecycle, Export & Exit Review
```

每批独立教学、TDD、真实 PostgreSQL 阻塞证据、本地门禁、提交、推送与 exact-SHA CI。RQ-064
原本允许 entry design 公共闭环后自动进入 6B-1、6B-1 公共闭环后自动进入 6B-2；较晚的 RQ-065
把当轮执行范围收紧为只闭环 6B-1，并已在该公共闭环后停止。更新的 RQ-066 又在独立新一轮只授权
6B-2；它不改变 6B-1 至 6B-9 的架构顺序，也不允许合并跳过批次或自动进入 6B-3。

## 后果

### 正面

- Conversation 从出生起就有稳定、不可变的 subject；
- API 保持短事务和零 Riot/Provider I/O；
- link 失败不会产生半个 Conversation 或污染 Memory；
- owner 隔离、public-observed 限制和模型写入门可由数据库与应用共同证明；
- Memory 类型与业务语言一致，便于教学、面试和测试；
- Context 选择可重复、可预算、可审计；
- 不增加当前无证据需要的新基础设施。

### 负面

- 表、migration、Repository 和测试数量较多；
- 用户首次使用需先等待一次异步 link；
- SQL 与 existing Artifact 仍需 body-free 引用协调；
- 没有向量召回时，V1 只能按结构化键、类型、来源和时间选择 Memory；
- 无正式 Auth/RLS 时，公网发布仍被明确阻塞。

### 中性

- Worker 是后台执行进程，不是 Multi-Agent；
- Player Link 是身份准备，不是 Riot 账号所有权验证；
- typed Conversation turn 不表示已经有开放域聊天或新 Skill；
- Stage 6 的 Memory 完成也不表示 Stage 7 MCP、Stage 8 Multi-Agent/恢复/前端已完成。

## 备选方案

### 首个 Review Task 内 bootstrap subject

拒绝。Task 在一半生命周期内没有稳定 subject，必须允许 nullable identity 或中途重绑；Worker 在
关系已写但 review 未完成时崩溃会混淆“link 成功”和“review 成功”，并发首单也增加重复 lookup 与
reconciliation。未来仍会需要独立 link，因此只是把同一问题做两次。

### API 同步 Account-V1 lookup

拒绝。它让 API process 承担 Riot Key、限流、超时与外部长尾，破坏 6A 已验证的 202 短事务边界。
网络调用也不能放在数据库事务中，先网络后入库又产生不可见失败与幂等复杂度。

### 用可变 Riot ID 创建 provisional subject

禁止。改名或重指向时会要求静默替换主身份，直接违反 Conversation subject 不可变规则。

### 每个 owner-player 保存一个大 profile JSONB

拒绝。字段级 provenance、更正、并发冲突、版本和 public-observed 限制无法可靠表达。

### 一张万能 memories 表

拒绝作为 V1 主模型。它会把 Plan/Progress 外键、self-only、active uniqueness 等关键规则下放到应用
约定，数据库无法形成第二道防线。

### EchoMind 式 Redis + Chroma 双真源

拒绝。当前没有性能/语义召回 Bad Case，双写、合并和删除补偿反而增加不一致面。

### 立即使用 PostgreSQL RLS

暂缓。正式 Auth 与可信 DB request context 尚不存在；当前先用 composite constraints 与 owner-scoped
Repository。Auth 落地后再评估，不把未配置正确的 RLS 当安全标签。

## 重新评估条件

1. 结构化 Context selector 在新鲜评测中出现多个语义召回失败族；
2. warm PostgreSQL Context query 达不到冻结的作品集规模目标；
3. 正式 Auth 落地，需要 RLS、最小权限角色或 RSO verified 写路径；
4. 用户真实需要同一 Conversation 切换 subject；
5. 用户真实需要同一 subject 同时存在多个关系角色或多个 active Training Plan；
6. 消息/Memory 删除补偿或 Artifact 协调出现可复现故障，需要 outbox/object storage；
7. typed Conversation turns 无法覆盖真实 follow-up，需新增独立 Skill/Router 评测。

## 参考

- ADR-0038
- RQ-060 至 RQ-065
- `app/api/main.py`
- `app/tasks/models.py`
- `app/tasks/recent_review_executor.py`
- `app/product/recent_review_service.py`
- `app/lol/player_summary.py`
- `docs/roadmap.md`
- `docs/architecture_capability_matrix.md`
