# 6B-1 学习复盘：Player Identity 与 Link Persistence 地基

> 适用提交：`ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 及其后兼容代码<br>
> 公共证据：[GitHub Actions 32229024069](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/32229024069)
> 本文只解释已经实现并验证的 6B-1。Resolver、Worker 和 HTTP API 属于 6B-2；Conversation、Message
> 和长期 Memory 在本文对应的阶段都还不存在。

## 1. 这一步到底解决什么问题

RiftCoach 最早可以直接接收一个 `gameName#tagLine`，拉取比赛并生成报告。但是如果系统要从“一次性
复盘脚本”成长为长期 Coach，就必须先回答一个更基础的问题：

> 用户今天输入的 Riot ID、以后改名后的 Riot ID，以及数据库中的长期训练记录，怎样可靠地指向同一个
> 公开玩家主体？

不能直接把 Riot ID 当主键，因为 Riot ID 是显示别名，会变化。也不能把 PUUID 直接当作 RiftCoach
用户，因为 PUUID 表示 Riot 公开账号，`owner_id` 才表示 RiftCoach 当前可信用户。更不能因为某个用户
输入了一个外服 Riot ID，就断言该用户拥有这个账号。

所以 6B-1 建立的是“身份与关系的持久化地基”：

```text
RiftCoach owner                    Riot 公开玩家主体
       │                                  │
       └── owner_player_relationship ─────┘
                                              └── 多个可变 Riot ID alias
```

与此同时，系统还需要一个可持久的 `player_link_task`，记录“把这个 owner 和这个公开账号建立何种关系”
的异步意图。6B-1 只把这套合同、四张表和事务 Repository 建好；当时还没有网络 Resolver、后台 Worker
或 HTTP 路由。

### 初学者要记住的四个名词

| 名词 | 回答的问题 | 稳定性 | 是否证明账号所有权 |
|---|---|---|---|
| `owner_id` | 当前是哪个 RiftCoach 用户 | 由可信 ActorContext 提供 | 它只证明 RiftCoach 用户身份 |
| Riot ID | 账号目前显示成什么 `gameName#tagLine` | 可改名 | 否 |
| PUUID / `player_subject` | Riot 体系中是哪个稳定公开账号主体 | 相对稳定 | 否 |
| owner-player relationship | 这个 owner 在 RiftCoach 内如何使用该主体 | owner-local | 仍不等于 Riot 官方认证 |

完整的 Session/Memory 心智模型见 [Stage 6 设计](../plans/2026-08-19-stage6-session-memory-design.md#2-给初学者的底层心智模型)，
架构裁决见 [ADR-0039](../adr/0039-adopt-async-player-link-and-typed-memory-model.md)。

## 2. 底层软件与 Agent 原理

### 2.1 身份、别名和关系必须分开

把三个概念塞进一张表或一个 JSON，会产生三个问题：

1. Riot ID 改名时，系统不知道是“同一主体的新别名”还是“换了一个主体”；
2. 不同 RiftCoach 用户观察同一个公开账号时，私人训练目标可能被错误共享；
3. “用户说这是自己的号”和“Riot 官方验证这是自己的号”会被混成同一个布尔值。

6B-1 因此采用：

- `player_subjects` 保存稳定公开主体；唯一键是 `(game, puuid)`；
- `player_aliases` 保存某次确认过的 routing region 与 Riot ID；
- `owner_player_relationships` 保存某个 owner 对该主体的本地角色和验证状态；
- `player_link_tasks` 保存一次 link 意图及其 `queued → running → succeeded | failed` 生命周期。

这不是“为了表多而拆表”。每张表负责一个可以由 PostgreSQL 独立证明的不变量。

### 2.2 状态机不只写在 Python 里

领域模型在 [models.py](../../app/players/models.py#L75) 中使用严格、冻结的 Pydantic 模型；
数据库表在 [player_records.py](../../app/persistence/player_records.py#L13) 中用 `CHECK`、`UNIQUE`、
`FOREIGN KEY` 和索引再次约束。例如：

- queued 任务不能提前带 `worker_id` 或终态身份；
- succeeded 必须带 subject、relationship 和确认后的显示 Riot ID，且不能带 failure；
- failed 必须带安全 failure reason，且不能暴露 subject/relationship；
- relationship 只允许 `self + unverified_claim`、`self + rso_verified`、
  `observed + not_applicable` 三种组合。

应用层校验给出清晰错误，数据库约束防止绕过应用的坏写入。两层防线各有职责，不能只保留其中一层。

### 2.3 幂等不是“重复请求直接忽略”

`Idempotency-Key` 只在同一个 owner 内有效。Service 先把规范化后的 routing region、Riot ID、role、
task kind 和 schema version 编码成稳定 JSON，再计算 SHA-256 fingerprint，见
[fingerprint.py](../../app/players/fingerprint.py#L18)。

Repository 的规则是：

```text
同 owner + 同 key + 同 fingerprint       → replay 原任务
同 owner + 同 key + 不同 fingerprint     → idempotency_conflict
新 key                                  → 才评估 owner/global 容量并创建
```

因此重复网络请求不会重复创建任务，但客户端也不能拿同一个 key 悄悄替换请求语义。要特别注意：这里的
SHA-256 是一致性指纹，不是加密或账号所有权证明。

### 2.4 网络调用不能藏在数据库事务里

6B-1 的 Repository 只接受已经验证为 `ResolvedRiotAccount` 的值，明确不接受网络 callback，见
[PostgresPlayerRepository](../../app/persistence/player_repository.py#L47)。这是一个重要工程边界：

```text
短数据库事务  → 提交
事务外网络 I/O → 等待外部结果
短数据库事务  → 原子收敛终态
```

如果把 Account-V1 调用放在持有行锁的事务里，网络抖动会长期占锁、放大连接池压力，并让其他 Worker
被一个外部请求拖住。6B-1 先用端口和 Repository 形状阻止了这种实现；6B-2 才把实际控制流接起来。

## 3. 为什么选这套设计，拒绝了什么

| 方案 | 裁决 | 原因 |
|---|---|---|
| 独立异步 Player Link + 四张关系表 | 采用 | 保持 API 短事务；稳定 subject、可变 alias、owner-local relationship 可以分别约束 |
| 在首次 Review Task 中顺手解析身份 | 拒绝 | link 成功和报告成功会混成一种终态；崩溃窗口与并发首单更难解释 |
| API 同步调用 Account-V1 | 拒绝 | API 会持有 Riot Key，并承受限流、超时和长尾；破坏已经验证的 202 快速入队边界 |
| 用 Riot ID 创建 provisional subject | 拒绝 | Riot ID 可变，后续必须静默换主身份或允许 Conversation 重绑 |
| 复用 `review_tasks` 存 link | 拒绝 | Review success 必须有 publication、Trace、receipt 和 final Artifact；link 没有这些语义 |
| 只保存 Riot ID hash | 拒绝 | Worker 以后无法拿到真实 `game_name/tag_line` 调 Account-V1；hash 只适合比较，不可逆 |
| EchoMind 式 Redis + Chroma 双真源 | 暂不采用 | 当前 PostgreSQL 足以表达身份、事务和隔离，没有双写或向量检索 Bad Case |
| LangGraph、消息队列、通用 Memory 框架 | 暂不采用 | 6B-1 是确定性身份控制面，没有证据需要更重的编排或基础设施 |

## 4. 真实源码地图

### 4.1 Domain 与 Service

| 文件 | 已实现职责 |
|---|---|
| [app/players/models.py](../../app/players/models.py#L79) | routing/role/verification/status 枚举、严格 create command、task 状态机、安全 public view、resolved account |
| [app/players/fingerprint.py](../../app/players/fingerprint.py#L18) | 规范化请求的 canonical JSON bytes 与 SHA-256 fingerprint |
| [app/players/ports.py](../../app/players/ports.py#L21) | Repository 端口：create/query/claim/resolve/fail；不暴露 SQLAlchemy 或 Riot Client |
| [app/players/service.py](../../app/players/service.py#L59) | 生成 server-side task identity/time、计算 fingerprint、映射 replay/capacity/error、owner-scoped query |

`CreatePlayerLinkCommand` 不允许客户端传 `verification_status`。当 role 为 `self` 时，只能派生
`unverified_claim`；当 role 为 `observed` 时，只能派生 `not_applicable`，见
[models.py](../../app/players/models.py#L138)。`rso_verified` 虽然作为 future-only 枚举存在，但当前没有
创建入口。

### 4.2 PostgreSQL Schema

| 表 | 关键列/约束 | 它防止什么 |
|---|---|---|
| [player_subjects](../../app/persistence/player_records.py#L13) | `(game, puuid)` unique；routing/time checks | 同一 PUUID 被重复建成多个全局主体 |
| [player_aliases](../../app/persistence/player_records.py#L57) | subject FK；subject+region+alias hash unique | 改名历史与稳定主体混在一起 |
| [owner_player_relationships](../../app/persistence/player_records.py#L113) | owner+subject unique；role/verification checks；composite identity unique | 跨 owner 私人关系共享、非法 role/verification 组合 |
| [player_link_tasks](../../app/persistence/player_records.py#L201) | owner+idempotency unique；lifecycle check；relationship composite FK | 非法状态、越权 relationship 引用、重复任务语义 |

可逆 DDL 位于
[0002_create_player_identity_and_link_tasks.py](../../migrations/versions/0002_create_player_identity_and_link_tasks.py#L15)，
`downgrade()` 按依赖反序删除 6B-1 新增对象，不删除 6A 的 `review_tasks` 基座。

### 4.3 Repository

| 方法 | 事务中的真实动作 |
|---|---|
| [`create_or_replay_link()`](../../app/persistence/player_repository.py#L60) | 事务级 advisory lock；replay/conflict；owner/global active capacity；插入 queued task |
| [`get_link_by_id()`](../../app/persistence/player_repository.py#L99) | `owner_id + link_task_id` 查询；不存在和不属于 owner 都返回空 |
| [`claim_next_link()`](../../app/persistence/player_repository.py#L131) | 按 created time/id 排序，`FOR UPDATE SKIP LOCKED` 领取一个 queued task并写 running/worker |
| [`resolve_link()`](../../app/persistence/player_repository.py#L178) | 只锁定当前 worker 拥有的 running task；upsert subject、取得 relationship、写 alias 与 success terminal |
| [`fail_link()`](../../app/persistence/player_repository.py#L262) | 只允许当前 worker 把自己的 running task 写为安全 failed terminal |

## 5. 数据流与控制流

数据流回答“数据去了哪里”；控制流回答“谁决定下一步、在哪次事务提交”。两者不要混淆。

### 5.1 6B-1 创建意图的数据流

```text
CreatePlayerLinkCommand
  ├─ trusted owner_id
  ├─ idempotency_key
  ├─ bounded Riot ID
  ├─ routing_region
  └─ relationship_role
          │
          ▼
PlayerLinkService
  ├─ 规范化 Riot ID
  ├─ 派生 verification_status
  ├─ 计算 request_fingerprint / alias_hash
  └─ 生成 link_task_id / created_at
          │
          ▼
PostgresPlayerRepository.create_or_replay_link
          │
          ▼
player_link_tasks: queued
```

6B-1 完成时，这条流到 queued 为止还没有 HTTP 入口。测试直接构造严格 Command 验证 Service/Repository；
6B-2 才在它前面接 FastAPI，在它后面接 Worker。

### 5.2 预先实现并由真库验证的终态收敛流

```text
running link task + matching worker_id + ResolvedRiotAccount
                         │
                         ▼  one short transaction
                 lock running task row
                         │
                 upsert player_subject by (game, puuid)
                         │
                 create/reuse owner relationship
                         │
              ┌──────────┴──────────┐
              │ role 一致           │ role 冲突
              ▼                    ▼
        upsert confirmed alias   link → failed
        link → succeeded         reason=relationship_role_conflict
```

角色冲突发生时，已有 relationship 不会被修改，也不会写 alias；任务在同一事务直接失败，而不是先抛异常、
再期待 Worker 开第二个事务补失败。subject 的 upsert 可能已经在同一事务内发生，但不会产生错误的
owner relationship。任何 SQL 异常会回滚本事务的身份写入和终态写入。

## 6. 事务、并发与 CAS 到底在保护什么

### 6.1 创建事务

Repository 使用 PostgreSQL transaction advisory lock，把“检查同 key、统计容量、创建新任务”放在同一个
串行化的临界区，见 [player_repository.py](../../app/persistence/player_repository.py#L71)。这样两个并发请求
不会同时看到“还有最后一个容量”并都插入。

### 6.2 Claim 事务

`FOR UPDATE SKIP LOCKED` 的含义不是忽略错误，而是：一个 Worker 已锁定某条 queued row 时，另一个 Worker
跳过该 row，继续寻找下一条，而不是重复领取。claim 设置 `status=running`、`worker_id` 和时间后先提交。

### 6.3 Terminal CAS

这里的 CAS 是“只有状态和 owner token 仍匹配才更新”：

```text
WHERE link_task_id = ?
  AND status = 'running'
  AND worker_id = ?
```

如果条件不再匹配，`resolve_link()`/`fail_link()` 返回空，旧 Worker 不能覆盖别人的终态。终态本身不可逆；
failed/succeeded 不能再次被普通 Worker 改写。

### 6.4 原子 resolve

subject、alias、relationship 和 link terminal 必须作为一个业务结果提交。若 alias 写入或 constraint 校验
失败，整笔事务回滚，不能留下“relationship 已存在但 link 永远 running”的半成品。对应真库测试是
[`test_resolution_sql_error_rolls_back_all_identity_writes`](../../tests/test_player_repository_postgres.py#L511)。

## 7. 两次公共 migration 事故：发生了什么、为什么测试有价值

这两次失败不是需要隐藏的“丢分”，而是 migration 必须经过真实 PostgreSQL CI 的直接证据。SQLite、
Python import 成功或 ORM metadata 检查都不能替代它。

### 7.1 第一次公共事故：Alembic revision 超过 32 字符

首个实现提交 `656117a` 对应的公共 run
[32227457202](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/32227457202) 在
`postgres-migrations` 和 package migration 阶段失败。原 revision：

```text
0002_player_identity_and_link_tasks   # 35 characters
```

Alembic 默认把当前 revision 写入 `alembic_version.version_num VARCHAR(32)`。DDL 文件名可以很长，Python
字符串也合法，但 migration 状态表装不下该 revision。修复是：

1. 先增加不需要数据库也能运行的回归测试
   [`test_player_identity_revision_fits_alembic_version_column`](../../tests/test_player_identity_migrations_postgres.py#L28)；
2. 把 revision 缩短为当前的 `0002_player_identity_link`，见
   [migration line 15](../../migrations/versions/0002_create_player_identity_and_link_tasks.py#L15)；
3. 不修改 Repository 语义，也不扩大 Alembic 状态列来掩盖问题。

教训：migration identifier 有自己的存储合同；“业务表能建”不等于 migration 系统能记录版本。

### 7.2 第二次公共事故：naming convention 二次命名并触发 PostgreSQL 截断

revision 修复提交 `b8fa2e3` 的 run
[32227937252](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/32227937252) 已通过普通 pytest、
package 和可逆 migration，但真实 PostgreSQL 测试仍有一个稳定 CHECK 名断言失败。

原因是项目的 SQLAlchemy naming convention 会根据 table/constraint 再生成名称。如果 Alembic migration
传入的已经是最终完整 CHECK 名，却不标记为“已格式化”，convention 会再次加前缀；结果超过 PostgreSQL
63 字节 identifier 上限后被数据库截断。Schema 可能能创建，但约束名不再是项目承诺的稳定名字，后续
migration、诊断和测试都会漂移。

修复是：

1. 用 offline SQL 回归测试固定完整名称：
   [`test_player_identity_offline_migration_uses_stable_check_names`](../../tests/test_player_identity_migrations_postgres.py#L37)；
2. 对 migration 中已是最终形式的 CHECK 名使用 Alembic `op.f(...)`，例如
   [player subject checks](../../migrations/versions/0002_create_player_identity_and_link_tasks.py#L46) 和
   [link lifecycle checks](../../migrations/versions/0002_create_player_identity_and_link_tasks.py#L294)；
3. 不放宽名称断言，也不接受被静默截断的 DDL。

最终提交 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 的
[Actions 32229024069](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/32229024069)
中 `pytest`、真实 `postgres-migrations` 和 Linux `packaging-smoke` 三个 job 全部成功。

补充：公共运行前，offline SQL 扫描还曾抓到两个超过 PostgreSQL 63 字符的 identifier 并同步缩短；它不算
上述两次公共事故，但说明“离线 DDL + 真库 CI”是互补防线。

## 8. 失败、安全与外服账号认领边界

### 8.1 账号存在不等于用户拥有账号

MVP 允许用户把一个可查询的外服 Riot ID 标成 `self`，但系统只保存：

```text
self + unverified_claim
```

它可以支持 owner-local 的后续训练体验，却必须显示未验证。选择 `observed` 则保存：

```text
observed + not_applicable
```

后者只适合公开赛后分析与 owner 自己的观察，不能形成“被观察者的私人偏好、训练计划或完成度”。两种关系
都不会解锁 Riot 非公开数据，也不会证明现实身份。未来 `rso_verified` 必须有正式 RiftCoach Auth、RSO
OAuth/OIDC callback，并让 `/accounts/me` 的 PUUID 与 subject 精确匹配；当前不存在这条写路径。

当前 routing allowlist 是 `americas/asia/europe/sea`，见
[RoutingRegion](../../app/players/models.py#L79)。`asia` 是 API regional routing value，不代表中国大陆国服；
`cn` 和 `zh_CN` 被测试明确拒绝，见
[`test_routing_region_allowlist_rejects_cn_and_zh_cn`](../../tests/test_player_models.py#L75)。

### 8.2 Owner 隔离

- owner 不能从请求 body 传入；后续 API 只能从 trusted `ActorContext` 注入；
- query 总是 `owner_id + link_task_id`；不存在与越权得到相同 not-found 语义；
- `player_subjects` 可以被多个 owner 引用，但 relationship 及未来私人数据不能跨 owner 共享；
- composite FK 要求 link terminal 的 owner/relationship/subject/role 是同一合法 tuple。

### 8.3 数据暴露边界

完整请求 Riot ID 组件必须私有存入 `player_link_tasks`，否则异步 Worker 无法解析；alias 也保存确认后的
显示值。它们不是 Secret，但不能进入普通日志、Trace、Prompt 或失败响应。`PlayerLinkTaskView` 隐藏私有
请求字段和完整 PUUID；成功时只投影本地 subject/relationship ID 与确认后的显示 Riot ID，见
[public view](../../app/players/models.py#L388)。

## 9. 需求 → 源码 → 测试 → CI → 限制矩阵

| 需求 | 主要源码 | 关键测试 | 公共证据 | 当前限制 |
|---|---|---|---|---|
| 严格 Riot ID/routing/role/状态合同 | [models.py](../../app/players/models.py#L79) | [test_player_models.py](../../tests/test_player_models.py#L75) | Actions 32229024069 `pytest` | 不是正式 Auth/RSO |
| 稳定且语义敏感的幂等指纹 | [fingerprint.py](../../app/players/fingerprint.py#L18)、[service.py](../../app/players/service.py#L81) | [`test_link_fingerprint...`](../../tests/test_player_link_service.py#L193)、create/replay tests | 同上 | fingerprint 不是加密或所有权证明 |
| 四张表、稳定约束名、可逆 migration | [player_records.py](../../app/persistence/player_records.py#L13)、[0002 migration](../../migrations/versions/0002_create_player_identity_and_link_tasks.py#L21) | [migration tests](../../tests/test_player_identity_migrations_postgres.py#L28) | Actions 32229024069 `postgres-migrations` | 本地无 PostgreSQL 时这些测试会明确 skip |
| 并发安全 claim | [claim_next_link](../../app/persistence/player_repository.py#L131) | [`test_two_workers_cannot_claim...`](../../tests/test_player_repository_postgres.py#L296) | 同一真库 job | 无 lease/reclaim |
| 原子 subject/alias/relationship/terminal | [resolve_link](../../app/persistence/player_repository.py#L178) | resolve/converge/rollback tests [L318](../../tests/test_player_repository_postgres.py#L318) | 同一真库 job | 6B-1 本身没有 Resolver/Worker |
| role conflict 安全收敛 | [_write_role_conflict](../../app/persistence/player_repository.py#L526) | [`test_role_conflict...`](../../tests/test_player_repository_postgres.py#L432) | 同一真库 job | 不支持同 owner/subject 同时拥有两个 role |
| stale Worker 不能覆盖终态 | [resolve/fail CAS](../../app/persistence/player_repository.py#L194) | [`test_stale_worker_terminal...`](../../tests/test_player_repository_postgres.py#L474) | 同一真库 job | hard-crash recovery 未实现 |
| package 与旧 6A 不回归 | migration + package image | full suite / packaging contract | Actions 32229024069 `pytest` + `packaging-smoke` | 不证明真实 Riot I/O 或 Coach 质量 |

6B-1 本地最终实现门曾记录 `1119 passed, 40 skipped, 1 warning, 110 subtests passed`；40 个 skip 是本机
没有 PostgreSQL 的诚实结果，不是“真库已通过”。最终真库和 Linux package 证据来自同一 exact SHA 的
独立 Actions jobs。

## 10. 安全、可重复的本地学习方法

以下命令不读取 Riot Key、不调用 Riot 或模型 Provider。

### 10.1 先跑纯领域与 Service 测试

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest `
  tests\test_player_models.py `
  tests\test_player_link_service.py -q
```

观察重点：输入怎样被规范化、role 怎样派生 verification、同 idempotency key 怎样 replay/conflict。

### 10.2 查看 Alembic 离线 SQL

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

这是离线生成 SQL，不会连接数据库。它能检查 revision 链和 DDL 文本，但不能证明 PostgreSQL 真正接受
事务、并发和约束，因此不能替代 CI 的 `postgres-migrations`。

### 10.3 运行 PostgreSQL 测试文件

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest `
  tests\test_player_identity_migrations_postgres.py `
  tests\test_player_repository_postgres.py -q
```

未设置仓库规定的本地测试 PostgreSQL 时，它会明确 skip。不要为追求绿色临时改成 SQLite，也不要把 skip
描述为真库成功。

## 11. 面试时可以怎样说，不能怎样说

### 可以准确地说

- “我把可变 Riot ID、稳定 PUUID subject 和 owner-local relationship 分离，避免改名和多用户引用污染
  长期教练数据。”
- “Player Link 使用 PostgreSQL 状态机、owner-scoped idempotency、`SKIP LOCKED` claim、worker CAS、
  upsert 和单事务终态收敛，并由真实 PostgreSQL CI 验证。”
- “数据库和 Pydantic 双层约束 succeeded/failed shape；SQL 异常会回滚身份关系与终态，role conflict
  在同一事务内安全失败。”
- “两次公共 migration 失败分别暴露 Alembic revision 长度和 SQLAlchemy naming convention/PG identifier
  截断问题；我用无数据库回归、offline SQL 和 exact-SHA 真库 CI 固化修复。”
- “`self` 只是 `unverified_claim`，Account-V1/PUUID 解析不是所有权认证。”

### 不能说

- “已经验证用户拥有这个 Riot 账号”；
- “已经支持中国大陆国服 API”；
- “6B-1 已经实现 Player Link HTTP/真实 Riot 查询”；这些属于后来的 6B-2，真实开发/CI 仍是 no-I/O；
- “已经实现 Session、Conversation 或长期 Memory”；
- “有自动 retry、lease、reclaim、灾难恢复、RLS、SLA 或多区域容灾”；
- “这是 Multi-Agent、LangGraph 或 EchoMind/Saber 的直接接入”。

## 12. 与 6B-2、6B-3 和 Memory 的关系

```text
6B-1  身份/关系合同 + 四张表 + 事务 Repository
  ↓
6B-2  FastAPI 意图入口 + 专用 Link Worker + Account Resolver
  ↓
6B-3  只允许 active、owner-owned relationship 创建不可重绑 Conversation
  ↓
6B-4  Review Task 从 Conversation 继承 trusted owner/subject tuple
  ↓
6B-5+ Candidate 写入门和分类型长期 Memory
```

6B-3 的计划是创建 Conversation/Message schema、不可变 binding、owner-scoped Service/API 与并发消息序号；
它仍不接 Agent、Review 或 Memory，见
[6B-3 implementation plan](../plans/2026-08-19-stage6-session-memory-implementation.md#6b-3-conversation--message-foundation)。
因此 6B-1 的身份地基是后续 Memory 的必要条件，但绝不能把“必要条件已完成”说成“Memory 已完成”。
