# 6B-6 Preferences / Profile / Review Memory 实现后复盘

> 当前证据状态：实现/最小测试修复提交 `5531c81ec7117f5c454d320e406153086baae3ea`
> 已由 GitHub Actions run `32387026797` 的 `pytest`、`postgres-migrations`、
> `packaging-smoke` 三个公共 job exact-SHA 验证；6B-6 已正式完成。

## 1. 这一批解决了什么问题

6B-5 已经有 `Memory Candidate`：它记录“有人提出一条可能值得长期保存的信息”、
来源是什么、是否需要确认、最后是否被接受。但 Candidate 不是长期 Memory 本身。

6B-6 把已经通过写入门的提案物化为三类真实目标：

- `Preference`：owner 全局偏好，例如报告语言；
- `Player Profile`：owner 对自己所认领玩家的稳定画像，例如主位置和英雄池；
- `Review Memory`：对某个玩家的复盘摘要、观察备注和公开趋势。

它第一次让生产 Candidate 的 `accepted` 具有完整含义：typed target 已写入，而且
target 写入与 Candidate terminal 在同一 PostgreSQL 事务中提交。

## 2. 底层原理

### 2.1 Candidate 与 Memory 为什么分开

可以把 Candidate 理解成“数据库变更申请单”，Memory 是“批准后生效的长期状态”。

```text
模型/规则/用户提出信息
→ Candidate（来源、权限、确认、审计）
→ materializer（类型校验、版本冲突、事务写入）
→ typed Memory（可查询的长期状态）
```

如果模型输出直接写 Profile，一次错误推断会污染未来所有会话；如果只把 Candidate
改成 accepted，又没有 target，则只是把“批准”冒充成“已经生效”。两层模型同时
解决了安全写入门和真实物化问题。

### 2.2 为什么三张表，不是一张万能 JSONB 表

三类数据的权限和作用域不同：

| 类型 | 业务作用域 | 关系权限 | active 唯一键 |
|---|---|---|---|
| Preference | `owner_id + key` | 仅 self 来源 | owner + key |
| Profile | owner + relationship + subject + key | self-only | owner + relationship + subject + key |
| Review | owner + relationship + subject + role + key | self/observed 受限 | owner + relationship + subject + role + key |

分表后，PostgreSQL 可以用 CHECK、复合 FK 和 partial unique index 直接证明关键规则。
JSONB 只保存严格 Pydantic schema 校验后的 `value`，不承担 owner、权限、状态和版本。

### 2.3 为什么不原地 UPDATE payload

长期记忆会被更正。原地覆盖会丢掉“以前是什么、为什么被改、谁提出修改”的证据。
本批采用版本链：

```text
v1 active
→ v1 superseded + v2 active
→ v2 superseded + v3 active
```

客户端必须在新 Candidate 中携带 `expected_version`。如果它读到 v1 后，另一个请求
已经写成 v2，它的修改会返回 `memory_version_conflict`，不会覆盖新数据。

### 2.4 advisory lock 和 partial unique 各自做什么

- PostgreSQL transaction advisory lock：即使该 key 还没有 active 行，也能把两个“首次写入”串行化；
- active row `FOR UPDATE`：已有版本时锁住当前记录；
- partial unique index：即使应用代码有 bug，数据库仍不允许同一作用域/key 出现两个 active。

前两者是并发控制，最后一个是数据库不变量；不能只保留其中一个。

## 3. 实际代码地图

### 3.1 纯领域合同

- `app/memory/typed_models.py`
  - `MemoryWriteEnvelope`：严格 `value + expected_version`；
  - `parse_typed_memory_write()`：scope/kind/key/operation/role allowlist；
  - Preference/Profile/Review payload schemas；
  - `TypedMemoryRecordView` / `TypedMemoryPage` 查询投影。

这里没有 SQLAlchemy、文件、网络、Riot 或模型依赖，先回答“什么数据合法”。

### 3.2 materializer 和 composition

- `app/memory/typed_materializers.py`
  - 三个 materializer 将 Candidate 解析后交给同一事务 writer；
- `app/memory/composition.py`
  - 创建不可变、完整的三类 registry；
- `app/api/composition.py`
  - FastAPI lifespan 内把 registry 注入 `MemoryCandidateService`。

materializer 不拥有 commit/rollback，也不调用外部服务。事务仍由 6B-5
`PostgresMemoryCandidateRepository.accept_candidate()` 唯一管理。

### 3.3 PostgreSQL 目标和版本 writer

- `app/persistence/typed_memory_records.py`
  - 三张 ORM 表、FK/CHECK/partial unique/index；
- `migrations/versions/0006_create_typed_memory_targets.py`
  - 可逆 migration、source/supersedes 验证 trigger、immutable update trigger；
- `app/persistence/typed_memory_writer.py`
  - advisory lock、active lock、expected-version、supersede 和插入；
- `app/persistence/memory_repository.py`
  - typed payload/version 冲突转换为安全 disposition，Candidate 保持 pending。

### 3.4 查询 Service / Repository / HTTP

- `app/persistence/typed_memory_query_repository.py`
  - owner-scoped active/history 查询和 relationship active/role 检查；
- `app/memory/typed_service.py`
  - Repository 异常和 scope not-found 的安全映射；
- `app/api/typed_memory_models.py`
  - 不含 PUUID、source candidate、Prompt 或原始 provenance 的响应；
- `app/api/main.py`
  - 三个只读 GET endpoint。

## 4. 写入的数据流和控制流

以修改报告语言为例：

```text
POST Candidate {value: "en-US", expected_version: 1}
→ 6B-5 Gate 创建 pending Candidate
→ POST /memory-candidates/{id}/accept
→ lock Conversation/relationship/Candidate
→ OwnerPreferenceMaterializer
→ parse typed envelope
→ pg_advisory_xact_lock(owner, report_language)
→ SELECT active preference FOR UPDATE
→ current version == expected_version ?
→ v1 active → superseded
→ INSERT v2 active, source_candidate_id unique
→ Candidate pending → accepted + target reference
→ one commit
```

如果 payload、relationship、expected version、trigger、FK、unique 或 SQL 任一失败，
整个事务 rollback；不会留下“target 成功但 Candidate pending”或相反的半状态。

## 5. 查询和更正怎么用

本地/测试 profile 启动后，可使用：

```text
GET /memory/preferences?include_history=false&limit=50
GET /memory/players/{relationship_id}/profile?include_history=true&limit=50
GET /memory/players/{relationship_id}/reviews?include_history=false&limit=50
```

默认只返回 active；history 有严格 1—100 上限。更正没有 PATCH endpoint，步骤是：

1. GET 当前记录并读取 `version`；
2. 创建同 kind/key 的新 Candidate；
3. proposal payload 带 `expected_version`；
4. accept Candidate；
5. 再查询 active/history。

这不是多走无意义步骤，而是确保每次更正仍经过来源、权限、确认和审计。

## 6. 测试如何证明

### 6.1 本地可证明

- pure payload/envelope/key/role policy；
- materializer 不依赖 commit/rollback，错误 kind 时 writer 零调用；
- version writer 的首写、supersede、冲突前零副作用；
- Service/API 的安全错误映射、可信 owner 和私有字段排除；
- composition registry 完整且构造 no-I/O；
- migration 离线 SQL、ORM metadata 和 package smoke Fake 流程。

### 6.2 只能由真实 PostgreSQL 公共 CI 证明

- 0006 upgrade/downgrade 和 `alembic check`；
- composite FK、CHECK、source/supersedes trigger；
- partial unique active；
- transaction advisory lock；
- 两个 Candidate 同 expected version 的并发结果；
- target + Candidate 同事务 commit/rollback；
- Linux package 内 Candidate accept 后 Preference 可查询。

本机没有 PostgreSQL/Docker，所以 skip 是“没有本地证据”，不是“测试通过”。

## 7. 失败、安全和边界

### 7.1 安全错误

| 情况 | 对外结果 | Candidate |
|---|---|---|
| typed value/schema 不合法 | 422 `memory_payload_invalid` | pending |
| expected version 过期/缺失 | 409 `memory_version_conflict` | pending |
| materializer 未安装 | 409 `memory_target_unavailable` | pending |
| target scope 不属于 owner | 404 `memory_scope_not_found` | 不变 |
| SQL/未知错误 | 503 `service_unavailable` | rollback |

响应不包含 SQL、密码、PUUID、原始 Candidate payload、Prompt、模型原始响应或内部异常。

### 7.2 self / observed 边界

- `self` 当前仍是 `unverified_claim`，不是正式 Riot 账号所有权证明；
- observed 不能写 Preference、Profile、Plan 或 Progress；
- observed Review 只允许 `observation_note` / `public_trend`；
- confidence 再高也不改变权限。

### 7.3 本批没有实现

- Training Plan / Progress（6B-7）；
- Memory-aware Context、assistant terminal（6B-8）；
- 完整生命周期/导出/删除（6B-9）；
- 正式 Auth/RSO/RLS、SSE、前端和公网部署；
- Redis、Chroma、向量检索；
- LangGraph、Multi-Agent、新 SDK 或真实 Riot/Provider 调用。

## 8. 面试时怎样准确表述

可以说：

> 我先用 Memory Candidate 把模型/规则提案与长期状态隔离，再为 Preference、Player
> Profile 和 Review Memory 建立分类型 PostgreSQL 表。接受 Candidate 时，typed
> materializer 在同一事务中执行 payload 校验、advisory lock、expected-version
> 检查和 supersede/insert，成功后才写 Candidate accepted；partial unique 和 trigger
> 提供数据库第二道防线。查询按 trusted owner/relationship 隔离，更正继续走 Candidate，
> 不开放绕过审计的 PATCH。

还不能说：

- “已经有完整长期教练 Memory”——Plan/Progress/Context/lifecycle 还没完成；
- “支持 Riot 账号验证”——self 仍是未验证认领；
- “Memory 使用向量数据库/语义检索”——V1 是 PostgreSQL 结构化查询；
- “通过了生产级高并发/SLA”——公共 CI 只证明受控并发不变量，不是容量结论；
- “这是 Multi-Agent Memory”——本批是模块化单体里的 typed persistence。

## 9. 参考证据

- ADR-0043；
- `docs/plans/2026-08-20-memory-types-design.md`；
- `docs/plans/2026-08-20-memory-types-implementation.md`；
- 6B-6 源码和测试；
- 实现/最小测试修复提交 `5531c81ec7117f5c454d320e406153086baae3ea`；
- GitHub Actions run `32387026797`：公共 pytest `1402 passed, 100 skipped, 1 warning,
  110 subtests passed`，真实 PostgreSQL `142 passed, 1 warning`，Linux package smoke
  Candidate accepted→Preference v1 query 且 `external_riot_provider_calls=0`。
