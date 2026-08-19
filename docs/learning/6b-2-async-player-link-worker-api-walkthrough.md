# 6B-2 学习复盘：异步 Player Link Worker 与 API 纵向切片

> 实现提交：`0c13a583ea51a7c18301fc29bf5c2931790d6693`<br>
> 公共证据：[GitHub Actions 32301852042](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/32301852042)
> 本文解释 6B-2 如何把 6B-1 的身份地基接成可查询的异步控制流。开发、测试与 Linux smoke 都没有
> 调用真实 Riot/模型 Provider；Conversation、Message、Review subject binding 和 Memory 仍未实现。

## 1. 这一步解决的具体问题

6B-1 已经有四张表、严格 Service 和事务 Repository，但普通用户还不能通过 HTTP 发起 link，后台也没有
组件把 Riot ID 解析成 PUUID。6B-2 要补齐最小纵向切片：

```text
POST link intent
→ PostgreSQL queued
→ dedicated Worker claim
→ transaction 外 Account-V1 resolver
→ PostgreSQL success/failure terminal
→ GET owner-scoped result
```

这里的关键不是“多写两个接口”，而是把三种不同等待时间隔离开：

- HTTP API 只做参数翻译、可信 owner 注入和短数据库事务；
- Worker 可以等待外部 Riot API，但不能在等待时占着数据库事务；
- Repository 只负责可证明的状态转移，不知道 HTTP 或 Riot SDK。

这是一条异步任务控制流，不是 Multi-Agent。Worker 是确定性后台进程，Resolver 是外部 API Adapter，
没有多个自主 Agent 讨论或分工。

## 2. 底层原理：为什么要分 API、Worker、Resolver、Repository

### 2.1 202 只表示“可靠入队”

`POST /player-links` 返回 HTTP 202 时，只能说明 link intent 已被持久化或同一请求被安全 replay。它不说明：

- Riot ID 一定存在；
- Account-V1 已成功；
- 用户拥有该账号；
- Conversation 或 Memory 已创建。

客户端必须通过 `GET /player-links/{link_task_id}` 观察 queued、running、succeeded 或 failed。把 202 当成功
终态，会让网络失败和持久化成功混为一谈。

### 2.2 Claim 必须先提交，再调用外部 API

真实控制流是：

```text
Transaction A                 no DB transaction              Transaction B
claim queued row              Account-V1 call                resolve/fail CAS
write running+worker_id  →    timeout / response       →     write terminal
COMMIT                                                        COMMIT
```

Transaction A 提交后，其他 Worker 才能看见该任务已被领取。Account-V1 调用位于事务外，所以即使限流或超时，
也不会一直持有 row lock。Transaction B 只接受仍由当前 worker 拥有的 running task，防止迟到 Worker 覆盖终态。

### 2.3 Resolver 是“防腐层”，不是薄薄转发 JSON

外部响应和异常不能直接穿过领域边界。`RiotAccountResolver` 把成功值收敛为严格
`ResolvedRiotAccount`，把失败收敛为 allowlisted `PlayerLinkFailure`：

| 外部情况 | 内部安全结果 |
|---|---|
| HTTP 404 | `player_not_found`, non-retryable |
| HTTP 401/403 | `riot_authentication_failed`, non-retryable |
| HTTP 429 | `riot_rate_limited`, retryable；`Retry-After` 只接受 1–300 的 ASCII 整数 |
| timeout | `upstream_timeout`, retryable |
| connection/其他请求异常 | `upstream_unavailable`, retryable |
| 响应 shape/PUUID/显示名非法 | `account_response_invalid`, non-retryable |

原始 response body、URL、request ID、异常文本和异常链都不会进入安全错误，见
[account_resolver.py](../../app/lol/account_resolver.py#L32)。`retryable=true` 只是分类信号；6B-2 没有自动
重新排队或 retry。

### 2.4 API process 不能拥有 Riot Client

[API composition](../../app/api/composition.py#L352) 在 lifespan 中只构造 PostgreSQL
`PostgresPlayerRepository` 与 `PlayerLinkService`。它不加载 `RIOT_API_KEY`，不构造 Resolver/Riot Client。

只有独立 [player-link Worker composition](../../app/players/composition.py#L78) 读取受保护 Key 和完整 routing
policy，并且直到 Worker 真正 resolve 时才由 deferred client factory 构造 `RiotClient`。这个进程隔离同时
缩小 API 的 secret 和外部网络故障面。

## 3. 设计选型与拒绝项

| 方案 | 裁决 | 原因 |
|---|---|---|
| FastAPI 短事务 + PostgreSQL polling Worker + 窄 Resolver | 采用 | 复用 6A 已验证基座；依赖少；事务和外部 I/O 边界清晰 |
| API 内同步 Account-V1 | 拒绝 | API 会持有 Key 并承受 timeout/rate limit；202 和短事务失去意义 |
| 把 link 交给现有 Review Worker | 拒绝 | link terminal 与 Review publication/Trace/Artifact terminal 不同 |
| 在数据库事务 callback 中调用 Resolver | 禁止 | 外部延迟期间持锁，扩大死锁、连接池和吞吐风险 |
| CI 使用真实 Riot Key 跑成功案例 | 拒绝 | 不可重复、会限流、可能泄密，也无法证明账号所有权；使用 Fake Resolver 验证控制流 |
| 自动 retry/lease/reclaim | 本批不做 | 尚未冻结 attempt/backoff/ownership 迁移语义；错误地重试可能覆盖边界或制造重复调用 |
| Redis/Celery/Kafka | 不采用 | PostgreSQL polling 已满足当前作品集规模，没有新增基础设施 Bad Case |
| LangGraph/Agent SDK | 不采用 | 这是一条确定性控制流，不需要模型决定状态转移 |

## 4. 真实源码地图

### 4.1 HTTP 边界

| 文件/位置 | 职责 |
|---|---|
| [app/api/player_models.py](../../app/api/player_models.py#L21) | 严格 POST/GET DTO；响应不含完整 PUUID；success/failed shape 再校验 |
| [`POST /player-links`](../../app/api/main.py#L228) | 从 trusted ActorContext 取得 owner，读取 Idempotency-Key，构造 Command，返回 202/replay 或安全错误 |
| [`GET /player-links/{id}`](../../app/api/main.py#L294) | owner-scoped query；非法、缺失、越权统一 404；持久化失败 503 |
| [app/api/composition.py](../../app/api/composition.py#L352) | 只绑定 DB Repository/Service；API 没有 Riot Client/Resolver/Key |

POST body 只允许：

```json
{
  "riot_id": "gameName#tagLine",
  "routing_region": "asia",
  "relationship_role": "self"
}
```

`owner_id`、PUUID、subject ID、relationship ID、verification status 都不能由 body 指定。幂等 key 是有边界的
HTTP header。

### 4.2 Account-V1 Adapter

| 文件/位置 | 职责 |
|---|---|
| [RiotAccountClient Protocol](../../app/lol/account_resolver.py#L19) | 只要求一个 bounded timeout 的 `get_account_by_riot_id()` |
| [RiotAccountResolver](../../app/lol/account_resolver.py#L65) | construction no-I/O；按 routing 构造 client；严格校验响应；安全映射异常 |
| [`_map_http_error`](../../app/lol/account_resolver.py#L158) | 404/401/403/429/其他上游状态映射 |

这里的 Protocol 使测试可以注入 Fake client，而生产 composition 可以适配现有 `RiotClient`。测试 Fake 不是
“模拟模型效果”，而是为了确定性证明请求/响应合同和失败映射。

### 4.3 Worker 与进程入口

| 文件/位置 | 职责 |
|---|---|
| [PlayerLinkWorker](../../app/players/link_worker.py#L111) | run-once 与 polling 控制流、claim→resolve→terminal、ownership loss、body-free observations |
| [PlayerLinkWorker composition](../../app/players/composition.py#L78) | 严格配置、DB readiness、routing policy、Riot client factory、Repository/Resolver/Worker 组装 |
| [scripts/run_player_link_worker.py](../../scripts/run_player_link_worker.py#L35) | `--check`、`--once`、长驻模式、SIGINT/SIGTERM graceful stop、安全退出码 |
| [compose.yaml player-link-worker](../../compose.yaml#L114) | 独立 runtime service；与 API 分进程，共享 PostgreSQL |

### 4.4 复用的 6B-1 地基

Worker 不直接写 SQL，而是调用 6B-1 的
[`claim_next_link`](../../app/persistence/player_repository.py#L131)、
[`resolve_link`](../../app/persistence/player_repository.py#L178) 和
[`fail_link`](../../app/persistence/player_repository.py#L262)。Service/API 复用相同的 create/query 端口。
因此 6B-2 是在稳定接缝上接线，而不是另造第二套身份状态机。

## 5. 一次请求的完整数据流

```text
Client
  │  POST /player-links + Idempotency-Key
  ▼
FastAPI DTO
  │  trusted ActorContext.owner_id
  ▼
CreatePlayerLinkCommand
  ▼
PlayerLinkService
  │  normalize + fingerprint + capacity/idempotency
  ▼
PostgreSQL player_link_tasks (queued)
  │
  │ 202 {link_task_id, status=queued, link=...}
  ▼
Client polls GET

Dedicated PlayerLinkWorker
  │ claim transaction commits running+worker_id
  ▼
RiotAccountResolver (outside DB transaction)
  │ strict ResolvedRiotAccount OR safe failure
  ▼
PostgresPlayerRepository terminal transaction
  ├─ success: subject + alias + relationship + succeeded
  └─ failure: safe failed terminal

Client GET by same trusted owner
  ├─ queued/running: no terminal identity
  ├─ succeeded: local subject/relationship IDs + confirmed display Riot ID
  └─ failed: allowlisted code + retryable flag
```

注意响应中的 `player_subject_id` 是 RiftCoach 本地 UUID，不是完整 Riot PUUID。API 刻意不暴露 PUUID。

## 6. 控制流与事务边界逐步展开

### 6.1 API create

1. FastAPI 校验 DTO 和 `Idempotency-Key`；恶意 validation detail 可能含 Riot ID，所以统一返回
   body-free `request_invalid`，见 [validation handler](../../app/api/main.py#L211)。
2. `owner_id` 只来自 `ActorContext`。
3. Service/Repository 在短事务内 create 或 replay。
4. API 返回 202；没有 Resolver/Riot I/O。

错误投影是：同 key 不同语义 409；owner/global capacity 503；请求格式 422；内部持久化/配置问题 503。
服务端生成 identity/time 异常不会伪装成用户输入错。

### 6.2 Worker claim

[`run_once()`](../../app/players/link_worker.py#L158) 调 Repository claim。没有任务则返回 `idle`。有任务时必须
得到 `running` 且 `worker_id` 匹配的严格 `PlayerLinkTask`；否则 fail closed，而不是猜测并继续。

### 6.3 事务外 resolve

claim 方法返回前，其 `with session.begin()` 已退出并提交。Worker 随后才在
[link_worker.py lines 200–229](../../app/players/link_worker.py#L200) 调 Resolver。Fake latency 测试明确断言
此时没有打开的 claim transaction。

### 6.4 Terminal CAS

成功 account 交给 `_commit_resolution()`；安全 failure 交给 `_commit_failure()`。Repository 只更新
`status=running AND worker_id=current` 的 row。返回空表示 ownership loss，Worker记录
`ownership_lost` 而不二次写入。role conflict 由 Repository 在一次 resolve transaction 内直接返回合法 failed
terminal，Worker 不再调用第二次 `fail_link()`。

### 6.5 Polling 与关闭

空队列使用既有 bounded exponential backoff + jitter，不 busy-loop。收到 graceful stop 时，当前 `run_once()`
会完成，下一轮 claim 前退出；它不是强制取消当前 Account-V1 请求。对应测试是
[`test_graceful_stop_finishes_current_link_and_claims_no_more`](../../tests/test_player_link_worker.py#L437)。

## 7. 失败、恢复和安全边界

### 7.1 失败图

```text
claim DB error
  → PlayerLinkWorkerError(link_claim_failed), no external call

resolver safe error / bad response
  → fail_link short transaction
  → failed terminal with allowlisted reason

role conflict
  → resolve_link same transaction writes failed/relationship_role_conflict
  → no alias write, no relationship mutation, no second terminal transaction

terminal Repository error
  → link_terminal_update_failed
  → do not pretend terminal was persisted

terminal CAS returns none
  → ownership_lost
  → old Worker performs no follow-up overwrite
```

### 7.2 当前没有自动 hard-crash recovery

如果进程在 claim commit 后、terminal commit 前硬崩溃，row 可能保持 running。6B-2 没有 lease、reclaim、
自动 retry 或人工 recovery 流程。`retryable=true` 也不会自动重排任务。这是有意保留的限制，不能把
graceful shutdown 测试外推成 hard-crash recovery。

### 7.3 账号认领与外服边界

Account-V1 成功只证明该 Riot ID 当前能解析为公开 PUUID，不证明发起请求的 owner 控制账号：

- `relationship_role=self` → `verification_status=unverified_claim`；
- `relationship_role=observed` → `verification_status=not_applicable`；
- 当前没有 `rso_verified` 创建路径；
- `cn`/`zh_CN` 不在 routing allowlist；`asia` 不是中国大陆国服支持；
- 用户选定某个外服账号作为“自己的”只能形成未验证 self claim，UI/报告必须保持这个标签；
- 任何 relationship 都不增加 Riot API 权限。

未来验证所有权需要正式 RiftCoach Auth + RSO callback + `/accounts/me` PUUID 精确匹配，不能用验证码自由文本、
Riot ID 可查询或用户口头声明替代。

### 7.4 Secret、日志与响应

- API composition 不读取 Riot Key；Worker settings 中 Key 使用 `repr=False`；
- Resolver 丢弃 raw upstream response/error context；
- Worker observation 只允许内部 task ID、worker ID、安全 status/reason、latency；不记录 Riot ID/PUUID；
- public DTO 不含 PUUID、原始 exception、request ID、Provider/Tool body；
- missing/unowned GET 都返回 404，避免资源枚举。

## 8. Fake Resolver Linux smoke 证明什么、不证明什么

[run_packaging_smoke.py](../../scripts/run_packaging_smoke.py#L111) 内置 `_FakeAccountResolver`，使用固定测试
PUUID；它会通过本地 API 创建 link，由真实 PostgreSQL Repository 和真实 `PlayerLinkWorker` 完成 claim 与
terminal，然后 GET succeeded。它同时让 Review Task 走安全失败路径。

公共 package 输出：

```text
task_status=failed
link_status=succeeded
external_riot_provider_calls=0
```

它证明：

- Linux image/Compose 能启动；
- API 202、PostgreSQL claim、Fake resolve、身份关系事务和 GET 可以在可重建 package 中串起来；
- Review Task 安全失败和 Link 成功两条控制流可以共存；
- smoke 没有外部 Riot/Provider I/O；
- image 以非 root 运行且排除 `.env`、tests、cache/runs/reports/tmp。

它不证明：

- 真实 Riot Key 有效、Account-V1 在线成功或限流策略充分；
- 用户拥有该账号；
- Coach 报告或模型质量；
- 自动 retry/reclaim/hard-crash recovery；
- 公网 Auth/HTTPS、Session/Memory、SSE/前端或生产 SLA。

## 9. 需求 → 源码 → 测试 → CI → 限制矩阵

| 需求 | 主要源码 | 关键测试 | exact-SHA 公共证据 | 当前限制 |
|---|---|---|---|---|
| Resolver construction no-I/O 与严格成功值 | [account_resolver.py](../../app/lol/account_resolver.py#L65) | [`test_resolver_construction...`](../../tests/test_riot_account_resolver.py#L71) | Actions 32301852042 `pytest` | 真实 Account-V1 未在开发/CI 调用 |
| 上游错误安全映射 | [`_map_http_error`](../../app/lol/account_resolver.py#L158) | HTTP/transport/bad-response tests [L129](../../tests/test_riot_account_resolver.py#L129) | 同上 | retryable 不触发自动 retry |
| claim commit → 事务外 resolve → terminal short transaction | [link_worker.py](../../app/players/link_worker.py#L158) + 6B-1 Repository | [`test_claim_commits_before_external_resolution...`](../../tests/test_player_link_worker.py#L274) | `pytest` + real `postgres-migrations` | hard crash 后 running task 不自动 reclaim |
| ownership loss 与 role conflict | [_commit_resolution](../../app/players/link_worker.py#L255) | worker ownership/role tests [L350](../../tests/test_player_link_worker.py#L350)、真库 role/CAS tests | 同上 | 没有 lease/attempt model |
| owner-scoped POST/GET、严格 OpenAPI、no PUUID | [main.py](../../app/api/main.py#L228)、[player_models.py](../../app/api/player_models.py#L25) | [test_player_link_api.py](../../tests/test_player_link_api.py#L158) | `pytest` | 202 不是 link success |
| API composition 零 Riot 依赖 | [api composition](../../app/api/composition.py#L352) | [`test_app_factory_and_openapi_do_not_read_keys_or_open_io`](../../tests/test_player_link_api.py#L170) | `pytest` | production Worker 仍需 Riot Key |
| 真实 PostgreSQL API replay/owner scope | 6B-1 Repository + API | [test_player_link_api_postgres.py](../../tests/test_player_link_api_postgres.py#L95) | real PG job `70 passed, 1 warning` | 普通 pytest job 的 DB tests 会 skip |
| Worker composition/CLI fail closed | [composition.py](../../app/players/composition.py#L78)、[CLI](../../scripts/run_player_link_worker.py#L35) | [test_player_link_composition.py](../../tests/test_player_link_composition.py#L38) | `pytest` + package | `--check` 只验 composition，不证明真实 lookup |
| 可重建 no-I/O 纵向 package | [smoke](../../scripts/run_packaging_smoke.py#L111)、[compose](../../compose.yaml#L114) | [test_packaging_smoke.py](../../tests/test_packaging_smoke.py#L95) | `packaging-smoke`: link succeeded, external calls 0 | Fake account，非真实 Riot 成功 |

公共 `pytest` 为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`；42 个 skip 主要是普通 runner
没有 PostgreSQL/Docker，不应冒充真库通过。独立 PostgreSQL 17 job 得到 `70 passed, 1 warning` 并验证
可逆 migration/metadata head；Linux package job 单独补 package 边界。三项都对应同一实现 SHA。

## 10. 安全、可重复的本地学习方法

以下默认路径不需要真实 Riot Key，不调用 Riot 或模型 Provider。

### 10.1 跑 Resolver、Worker、API 的 Fake/合同测试

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest `
  tests\test_riot_account_resolver.py `
  tests\test_player_link_worker.py `
  tests\test_player_link_api.py `
  tests\test_player_link_composition.py -q
```

阅读测试时按顺序追：Resolver 分类 → Worker 事务顺序 → HTTP owner/error 投影 → composition secret 边界。

### 10.2 只检查 CLI 合同

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m scripts.run_player_link_worker --help
```

`--help` 不加载环境、数据库或 Key。不要为了学习直接运行生产长驻模式；生产模式会读取配置，并在有任务时
真实调用 Riot。

### 10.3 可选：本机有 Docker 时运行隔离 no-I/O smoke

```powershell
cd D:\riftcoach-agent
$env:COMPOSE_PROJECT_NAME = "riftcoach-learning-6b2"
docker compose --profile smoke up --build --detach --wait --wait-timeout 120 api
docker compose --profile smoke run --rm --no-deps smoke
docker compose --profile smoke down -v --remove-orphans
```

必须使用独立 `COMPOSE_PROJECT_NAME`，避免与普通本地栈混用容器/volume。该 smoke 使用 Fake Resolver，
期望 `external_riot_provider_calls=0`；它不是测试真实外服账号的命令。

## 11. 面试时可以怎样说，不能怎样说

### 可以准确地说

- “我把 Player Link 设计为独立异步控制面：API 只持久化意图并返回 202，专用 Worker 在 claim commit 后、
  数据库事务外调用 Account-V1，再以短事务 CAS 收敛终态。”
- “Resolver 将外部 HTTP/transport/bad-response 映射为 allowlisted body-free failure，不让原始上游正文和
  异常链跨越边界。”
- “API composition 不构造 Riot Client、不读取 Riot Key；只有 Worker process 拥有外部依赖。”
- “owner 从 trusted ActorContext 注入，POST body 不能指定 owner/PUUID/verification，GET 越权与不存在
  统一 404。”
- “真实 PostgreSQL job 验证并发/事务，Fake Resolver Linux smoke 验证可重建 package；我明确区分
  no-I/O 控制流证据与真实 Riot 可用性。”

### 不能说

- “公共 CI 成功调用了 Riot API”；实际 external calls 为 0；
- “系统验证了账号归属”；`self` 仍是 `unverified_claim`；
- “retryable error 会自动重试”；当前没有 auto retry；
- “Worker 崩溃后会自动 reclaim/resume”；当前没有 lease/reclaim；
- “已经支持国服 API”；routing allowlist 不含 CN；
- “已经有聊天 Session、Memory、Agent follow-up 或前端”；
- “这是 Multi-Agent、LangGraph、Celery/Kafka 或生产级分布式系统”；
- “有 99.9% SLA、正式 Auth/RSO、RLS 或公网所有权隔离”。

## 12. 与 6B-3 和长期 Memory 的精确关系

6B-2 成功终态提供：

```text
trusted owner_id
+ active owner_player_relationship
+ stable player_subject_id
+ relationship role / verification label
```

这组数据只是“允许创建 Conversation 的可信地基”。6B-3 才计划：

- 用 active、属于当前 Actor 的 relationship 创建 Conversation；
- 冻结 owner + relationship + subject + role binding，不提供 rebind；
- 持久化只允许 user/assistant 的有界 Message；
- 在 PostgreSQL 中原子分配并发安全的 message sequence；
- archive 后拒绝新消息，hidden 后 owner query 不可见；
- 不调用 Agent、Review、Memory 或任何外部 I/O。

对应 TDD 不变量见
[6B-3 implementation plan](../plans/2026-08-19-stage6-session-memory-implementation.md#6b-3-conversation--message-foundation)。

然后 6B-4 才让 Review Task 从服务器保存的 Conversation 继承 owner/subject tuple；6B-5 才创建 Memory
Candidate 与写入门；6B-6/7 才实现长期画像、复盘记忆、训练计划和进度；6B-8 才把经过选择的 Memory
接入 Context。Player Link 是这些能力的前置身份控制面，不是 Memory 本身。
