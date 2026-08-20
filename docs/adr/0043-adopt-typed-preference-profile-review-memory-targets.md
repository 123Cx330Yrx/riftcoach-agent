# ADR-0043：为 Memory Candidate 注册分类型长期记忆目标

- 状态：Accepted（6B-6 设计批）
- 日期：2026-08-20
- 范围：`6B-6-preferences-profile-review-memory`
- 上游：ADR-0039、ADR-0042
- 需求：RQ-070

## 背景

6B-5 已经完成了 `Memory Candidate` 控制面和事务内
`MemoryCandidateMaterializer` 接缝，但生产 registry 在没有具体目标表时必须
fail closed。6B-6 的任务不是再造一个“记忆字符串仓库”，而是把三类不同权限、
不同作用域、不同更正语义的长期信息落到可由 PostgreSQL 约束的真实目标中：

1. owner 全局偏好（Preference）；
2. owner 对自己账号的稳定画像（Player Profile）；
3. 对某个玩家的复盘观察/趋势（Review Memory）。

已有边界继续有效：Riot ID 只是可变显示别名；`claimed_self` 不是正式账号所有权
证明；`public_observed` 不能升级为私人画像；模型 confidence 不能提供写权限；
长期记录不能与 RAG 文档、原始比赛事实、Task/Run 或 Conversation body 混成一层。

## 决策

### 1. 存储采用三张 typed 表

新增：

```text
memory_preferences
player_profiles
review_memories
```

三张表共享一组 Python mixin/Repository 辅助逻辑，但在数据库中保持独立表。
每张表都有自己的 `source_candidate_id UNIQUE`、作用域字段、`memory_key`、
`version`、`status`、严格校验后的 JSONB payload、payload digest、时间戳和
`supersedes_record_id`。关系型列和 SQL 约束负责身份、权限、版本和唯一性；JSONB
只承载经过 Pydantic 严格解析的有界叶子值。

拒绝一张 `memories(kind, payload)` 万能表：那会把 observed 禁止 Profile、
每个 key 只能一个 active、Plan/Progress 外键等不变量退回到散落的 Python if/else，
数据库无法提供第二道防线，也会让面试表述变成“JSON 里约定了一些字段”。

### 2. 作用域和关系权限冻结如下

| Target | 作用域 | 允许 relationship | V1 key | V1 operation |
|---|---|---|---|---|
| Preference | `owner_global` | 仅 `self` 来源的 owner candidate | `report_language` | `set` |
| Player Profile | `owner_player` | 仅 `self` | `main_role`, `champion_pool` | `set` |
| Review Memory | `owner_player` | `self` 或 `observed` | `review_summary`, `observation_note`, `public_trend` | `append` |

Owner Preference 的 Candidate 仍从 Conversation 派生身份以保存 provenance，但
目标记录的业务作用域只有 `owner_id + memory_key`，不会被某次 Conversation 的
player subject 锁死。

Player Profile 的数据库 CHECK 和 materializer 双重拒绝 `observed`。
Review Memory 的 `observed` 只允许 `observation_note` 或 `public_trend`，并且
必须是 `append`；它不能创建 Preference、Profile、Plan 或 Progress。

### 3. payload 使用严格的 typed envelope

为了不修改已经公共闭环的 0005 Candidate 表，6B-6 不新增通用 Candidate 列，而由
三个 materializer 解析候选 payload 的版本化 envelope：

```json
{
  "value": "...typed value...",
  "expected_version": 2
}
```

`expected_version` 可以省略或为 `null`，表示第一次创建；已有 active 记录时必须
精确匹配当前版本。materializer 将 `value` 解析为对应 key 的严格 Pydantic schema，
并只把规范化后的 value 写入目标表，不把 envelope 原样当成业务数据。

V1 的 allowlist：

- `report_language`：`zh-CN` 或 `en-US`；
- `main_role`：`TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY/UNKNOWN`；
- `champion_pool`：1—20 个去重、有限长度的 champion 名称；
- `review_summary`：有界文本和可选结构化 metric；
- `observation_note`：有界第三人称观察文本；
- `public_trend`：有界 metric、方向和可选数值。

未知 key、额外字段、过长/嵌套过深/非 JSON 值、角色与 key 不匹配都拒绝，且不改变
Candidate 状态。

### 4. 版本、supersede 和 append 语义

每个作用域加 `memory_key` 只有一个 `active` 记录。新写入不 UPDATE 旧 payload，
而是：

```text
锁定作用域 key
→ 校验 expected_version
→ 旧 active: active → superseded
→ 插入 version + 1 的新 active
→ Candidate accepted
```

`superseded` 和 `retired` 都是不可重新激活的历史终态；V1 不提供原地修复或直接
删除目标记录的公开接口。`Review Memory.append` 在本版表示“产生一个新的有序版本
并保留旧记录”，并不表示同一 key 同时拥有多个 active 行。这样 Context V1 可以
确定性地取最新 active，而历史查询仍可审计过去的观察。真正需要多条并行 active
笔记时，必须以新需求和新评测重新设计 key/事件模型。

为避免两个 Candidate 同时覆盖同一个 key，materializer 在同一 PostgreSQL 事务中
取得作用域 key 的 transaction advisory lock，再锁定当前 active 行；数据库 partial
unique index 是第二道防线。没有 active 行时也由 advisory lock 串行首次创建。

### 5. exactly-once 和失败语义

真实 materializer 注册为：

```text
OWNER_PREFERENCE → OwnerPreferenceMaterializer
PLAYER_PROFILE   → PlayerProfileMaterializer
REVIEW_MEMORY   → ReviewMemoryMaterializer
```

它们只能使用 Repository 提供的同一 Session，不得 commit/rollback，不得调用模型、
网络、文件或读取 Key。目标表写入、旧版本 supersede 和 Candidate `accepted` 在
一个事务中提交；任一 payload、权限、版本、唯一性或 SQL 错误都回滚，Candidate
保持 `pending` 并返回安全的 allowlisted error。

Candidate `source_candidate_id` 在三张表中唯一，保证 replay 不重复物化。版本冲突
映射为 `memory_version_conflict`，目标不可用映射为 `memory_target_unavailable`；
不把底层 SQL、PUUID、payload 或原始异常泄露给 HTTP 客户端。

### 6. 查询和更正 API

6B-6 提供 owner-scoped 的 active/history 查询：

```text
GET /memory/preferences
GET /memory/players/{relationship_id}/profile
GET /memory/players/{relationship_id}/reviews
```

查询默认只返回 active，`include_history=true` 时使用严格上限返回 superseded 历史。
路径中的 relationship 必须由可信 ActorContext 与数据库复合 identity 再验证；客户端
不能提交 PUUID 或替换 owner。

本批不提供直接 PATCH 目标记录。更正必须创建新的 typed Candidate，并在 envelope 中
带 `expected_version`，再走既有 Candidate gate/materializer；这样所有更正仍有来源、
确认和审计记录，不会绕过 6B-5。

### 7. Migration、查询和基础设施边界

新增一个可逆 Alembic migration（6B-6 目标表及索引/触发器）。不修改 0005 的 Candidate
状态机，不引入 Redis、Chroma、向量库、RLS、LangGraph、Multi-Agent、SDK、SSE、前端、
正式 Auth/RSO 或真实 Riot/Provider 调用。PostgreSQL 仍是唯一生产语义真源；Fake/纯
测试只证明逻辑，partial unique、FK、触发器、 advisory lock、事务回滚与并发必须由
公共 PostgreSQL CI 证明。

## 后果

### 正面

- Preference/Profile/Review Memory 的权限语言直接落在表结构和 CHECK/FK/index；
- 不覆盖历史，expected-version 冲突可解释、可重放；
- 6B-5 的 exactly-once seam 终于连接到真实 target，生产不再因空 registry 拒绝所有合法写入；
- 查询只返回 owner-scoped、body-safe 记录，观察关系不会升级权限；
- 未来 6B-7/6B-8 可复用同一 typed materializer、版本和 Context 选择原则。

### 代价和限制

- 三张表、三套 payload schema 和 migration 测试比一个 JSONB 表更冗长；
- advisory lock 依赖 PostgreSQL，不能用 SQLite 绿灯替代；
- V1 的 Review `append` 只保留一个 active key，复杂事件流需要新设计；
- 没有正式 Auth/RSO 时，`self` 仍是 `unverified_claim`，不能宣传为账号所有权验证。

## 重新评估条件

只有出现以下证据，才另开 ADR 改变本设计：

1. 多 active review note 的真实产品需求和查询/Context 评测；
2. advisory lock 在目标规模产生可重复的锁竞争或延迟问题；
3. 正式 Auth/RSO 带来 verified-self 写路径或 RLS 最小权限需求；
4. 结构化 typed query 出现多个独立召回失败族，需要可重建派生索引。
