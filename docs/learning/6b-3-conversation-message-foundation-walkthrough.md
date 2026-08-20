# 6B-3 Conversation / Message Foundation：从设计到实现

> 当前证据状态：本地实现与本地门禁已建立，等待实现提交的 exact-SHA PostgreSQL 17 与
> Linux package 公共 CI。公共三 job 全绿前，6B-3 仍是 `in_progress`，本文不把本地代码
> 冒充为已经公开完成。

## 0. 先说结论：这一批到底搭起了什么

6B-3 搭起的是 RiftCoach 的“教练对话控制面”：

```text
可信 RiftCoach owner
  → 选择自己名下已经解析成功的 player relationship
  → 创建固定玩家主体的 Conversation
  → 按数据库序号追加 user Message
  → 有界读取、归档或隐藏 Conversation
```

它还不是“模型已经会连续聊天”。这一批不会启动 Agent、ReviewHarness、Riot API 或模型，
也不会把 Message 自动写入长期 Memory。它先把身份、顺序、生命周期和越权边界做可靠，给
后面的 Conversation-bound Review 与 Memory 提供一个不会漂移的地基。

初学者最容易混淆的五个实体如下：

| 实体 | 它回答的问题 | 生命周期 |
|---|---|---|
| Auth Session | “当前是谁登录了 RiftCoach？” | 登录态；当前尚未正式实现 |
| Conversation | “这段 Coach 讨论固定属于哪个 owner 和玩家？” | 多次请求、多个 run |
| Message | “Conversation 内第几条、什么角色的文本？” | Conversation 的有序记录 |
| Review Task / Runtime run | “某一次复盘执行到哪、产生了什么证据？” | 一次异步任务/运行 |
| Memory | “哪些经过写入门的状态值得以后继续使用？” | 跨 Conversation 的长期状态 |

Conversation 不是登录 Session，Message 也不是 Prompt、模型 reasoning 或 Tool body。把这些边界
分开，是后续 Agent 不乱记、不串用户、不伪造回复的前提。

---

## 1. 问题与底层原理

### 1.1 为什么不能直接拿 Riot ID 当 Conversation 身份

Riot ID 是 `gameName#tagLine` 形式的显示身份，可以改名，也可能在更长时间尺度上重指向；
6B-1/6B-2 得到的 `player_subject_id` 才绑定完整 PUUID。Conversation 如果只保存 Riot ID，
改名后可能找不到旧讨论，重指向时更可能把旧训练记录解释成另一个玩家。

因此创建 Conversation 时，服务器从一条 active relationship 复制并冻结：

```text
owner_id
+ relationship_id
+ player_subject_id
+ relationship_role (self | observed)
```

客户端只提交 `relationship_id`。owner 来自可信 `ActorContext`，subject/role 从数据库父行取得；
客户端、自由文本和模型都不能覆盖。

底层原则叫“服务器权威身份”和“不可变聚合绑定”：一个长期业务对象出生时绑定稳定主体，
以后没有隐式 rebind。

### 1.2 为什么创建需要 Idempotency-Key

假设客户端发出创建请求，服务器已经提交，但响应在网络中丢失。客户端重试时，如果系统每次都
创建新 UUID，就会出现两个内容相同的 Coach 房间。

6B-3 把请求身份拆成两部分：

- `Idempotency-Key`：客户端给这次业务意图取的重试键；
- `request_fingerprint`：服务器按 `schema_version + relationship_id` 计算的 SHA-256。

同 owner 下的结果是：

| key | fingerprint | 结果 |
|---|---|---|
| 相同 | 相同 | replay 原 Conversation，HTTP 200 |
| 相同 | 不同 | 安全冲突，HTTP 409 |
| 不同 | 任意 | 新的创建意图 |

不同 owner 可以复用同一个 key。Repository 还用 `owner_id + key` 派生稳定 signed-bigint
PostgreSQL advisory lock，使跨不同 relationship 的同 key 竞态也能收敛，同时不会让无关 owner/key
排在一把全局大锁后面。

底层原则是“幂等不是去重字符串，而是请求身份 + 请求语义的一致性检查”。

### 1.3 为什么 Message 不能用 `MAX(sequence_no) + 1`

两个请求同时执行 `MAX + 1` 时，都可能读到 0，然后都准备写第 1 条。客户端时间也不能当顺序，
因为机器时钟和网络到达顺序都可能不同。

本实现把 `next_message_sequence` 放在 Conversation 行上：

```text
锁 Conversation 行
→ 读取 n
→ 插入 sequence_no=n 的 Message
→ next_message_sequence=n+1
→ 同一事务提交
```

第二个 writer 必须等第一个释放行锁，随后看到新的 n。`UNIQUE(conversation_id, sequence_no)`
是数据库的第二道防线；插入失败时 Message 和计数器一起回滚。

底层原则是“共享可变序号必须由单一串行化点分配，并与业务写入原子提交”。

### 1.4 为什么 public API 只能写 user Message

数据库 role 预留 `user|assistant`，但“assistant”不是客户端随便写一个字符串就成立。可信助手消息
未来必须能追溯到 AgentRuntime/ReviewHarness 的合法 terminal，至少带可信 `source_run_id`。

所以 6B-3：

- public DTO 只有 `content`；
- Service 只有 `append_user_message()`；
- user Message 禁止任何 source reference；
- assistant 数据合同要求 `source_run_id`，但本批没有公共/产品写入接缝。

底层原则是“角色是一项权限和 provenance 结论，不只是展示字段”。

### 1.5 archived 与 hidden 为什么分开

- `archived`：用户仍能查看历史，但不能继续写；
- `hidden`：owner 查询也得到 404-equivalent，且 V1 不可恢复；
- relationship hidden：即使 Conversation 自身仍是 active/archived，也立即 owner-invisible。

这让“结束讨论”和“从正常产品视图删除”具有不同语义，同时避免泄露其他 owner 或隐藏资源是否存在。

---

## 2. 设计如何落到实现

### 2.1 分层结构

```text
FastAPI DTO / routes
        ↓ 只做 HTTP 校验、Actor 注入和错误投影
ConversationService
        ↓ 生成服务器 ID、fingerprint、digest，校验 Repository 投影
ConversationRepository Port
        ↓
PostgresConversationRepository
        ↓ 短事务、行锁、owner scope
SQLAlchemy ORM metadata
        ↔ Alembic 0003 / PostgreSQL constraint + trigger
```

每层职责不同：

- domain model 让非法状态在内存边界就不能构造；
- Service 保存业务不变量，不知道 SQL 细节；
- Repository 负责事务、锁和数据库错误的安全收敛；
- HTTP Adapter 不复制业务流程；
- migration 是已部署 schema 的可审计版本，不靠 ORM 启动时偷偷建表。

### 2.2 Domain model 做了什么

`app/conversations/models.py` 使用 strict、frozen、extra-forbid 的 Pydantic model：

- owner、key、fingerprint、source run 都有长度和字符白名单；
- Conversation 校验时间顺序、hidden shape、message history shape；
- Message 校验 UTF-8、非空、16,384 Unicode code points、控制字符和 digest；
- user source 必须为空，assistant 必须有 source run；
- Repository result model 也校验 disposition 与 payload shape，防止 Fake/数据库 Adapter 返回
  “状态说成功、对象却为空”等自相矛盾结果；
- Message page 校验 cursor、稳定升序、去重和 `has_more` 形状。

正文不会被 trim、Unicode normalize 或改写。`"  保留空格  "` 只要不是全空白，就按原 UTF-8
字节保存并计算 digest。

### 2.3 Service 为什么还要防守 Repository 返回值

Service 不盲信 Port 的实现。以 create 为例，它会核对：

- owner、relationship、key、fingerprint 是否仍与命令一致；
- `CREATED` 返回的 Conversation ID 是否就是本次服务器生成的 ID；
- `CREATED` 初态是否确实为 active；
- hidden 对象是否被错误投影为正常成功。

这叫“防御性 Port 校验”。Port 是架构边界，不意味着每个 Adapter/Fake 永远正确。否则数据库 Adapter
接线错误可能被 Service 包装成合法成功响应。

### 2.4 PostgreSQL schema 提供哪些第二道防线

0003 新增：

- `conversations`；
- `conversation_messages`；
- owner/key unique；
- Conversation 完整 identity unique；
- relationship 与 Conversation 两级 composite FK；
- role/status/长度/digest shape/时间等 CHECK；
- owner history、relationship、subject、source 等查询索引；
- Conversation binding/lifecycle trigger；
- Message append-only 字段 trigger。

两点不能说错：

1. composite FK 证明 tuple 对得上，但不会自动证明 relationship 当前仍 active；所以 Repository 仍要
   `SELECT ... FOR UPDATE` 后检查 status；
2. trigger 保护 Conversation binding/lifecycle 和 Message immutable fields；连续序号由 Repository
   同事务行锁 + counter + unique 保证，不能把它说成 trigger 的功劳。

### 2.5 为什么事务锁顺序固定为 relationship → Conversation

create、append、archive、hide 都先处理 relationship，再处理 Conversation。统一顺序避免一种事务先锁 A
等 B，另一种先锁 B 等 A 的经典死锁环。

事务内只做数据库读写与纯内存校验，不调用 Riot、模型、HTTP 或文件系统。外部 I/O 如果放在锁内，慢请求
会长时间占锁，吞吐和故障恢复都会恶化。

### 2.6 为什么列表读取也会拿锁

`list_messages()` 需要先确认 Conversation/relationship 可见，再读取下一页 Message。当前实现用同一
relationship→Conversation 锁保证两个查询之间不会刚好发生 hide，然后仍返回一页正文。

代价是列表读取会与 append/archive/hide 串行。对当前作品集规模，这是清晰的强一致取舍；如果以后真实
压力数据证明读锁成为热点，可以设计单 SQL visible-page 投影或新的隔离方案，再用性能/一致性测试评估，
而不是现在无证据地复杂化。

---

## 3. 代码地图：从需求找到源码

| 需求 | 主要实现 | 主要测试 |
|---|---|---|
| strict domain 与 digest | `app/conversations/models.py` | `tests/test_conversation_models.py` |
| Service/安全错误 | `app/conversations/service.py` | `tests/test_conversation_service.py` |
| Port 合同 | `app/conversations/ports.py` | Service/Repository structural tests |
| ORM/constraint metadata | `app/persistence/conversation_records.py` | migration metadata tests |
| 事务、锁、分页 | `app/persistence/conversation_repository.py` | Repository + concurrency PostgreSQL tests |
| 可逆 schema/trigger | `migrations/versions/0003_create_conversations_and_messages.py` | migration/trigger PostgreSQL tests |
| public DTO | `app/api/conversation_models.py` | `tests/test_conversation_api.py` |
| 六个 HTTP endpoint | `app/api/main.py` | API Fake tests |
| lifespan 生产组合 | `app/api/composition.py` | composition + package smoke tests |
| Linux no-I/O 纵向 | `scripts/run_packaging_smoke.py` | `tests/test_packaging_smoke.py` + CI |
| 真库阻塞门 | `.github/workflows/tests.yml` | `postgres-migrations` job |

阅读源码时建议按这条顺序：

1. 先看 `CreateConversationCommand`、`Conversation`、`ConversationMessage`；
2. 再看 `ConversationService.create()` 和 `append_user_message()`；
3. 再看 Repository 的 create/append 与 `_lock_visible_conversation()`；
4. 对照 ORM 和 0003；
5. 最后看 HTTP route 与 package smoke。

这样先理解业务合同，再理解事务实现，不会一上来掉进 SQL 和 FastAPI 细节。

---

## 4. 数据流与控制流

### 4.1 创建 Conversation

```text
POST /conversations
Header: Idempotency-Key
Body: {relationship_id}
          │
          ├─ ActorContext 注入 owner_id
          ├─ Service 生成 conversation_id
          └─ Service 计算 relationship request fingerprint
                         │
                     BEGIN
                         │
        SELECT relationship FOR UPDATE (owner scoped)
                         │
              relationship active?
                 ┌───────┴────────┐
                no               yes
                │                 │
      404-equivalent       scoped advisory lock(owner,key)
                                  │
                       existing owner/key?
                         ┌────────┼─────────┐
                       none     same fp   other fp
                         │         │          │
                      INSERT     replay      conflict
                         └─────────┴──────────┘
                                  │
                                COMMIT
```

Service 最后再次验证成功对象的服务器身份，HTTP 分别投影为 201/200/409/404/503。

### 4.2 追加 user Message

```text
POST /conversations/{id}/messages {content}
  → Actor owner + path conversation_id
  → strict content validation
  → server message_id + exact UTF-8 SHA-256
  → BEGIN
      read immutable identity
      lock active relationship
      lock visible Conversation
      archived? → conflict
      n = next_message_sequence
      INSERT Message(role=user, sequence=n)
      UPDATE Conversation(next=n+1, last_message_at, updated_at)
    COMMIT
  → 201 public Message view
```

如果 insert、CHECK、trigger 或 flush 失败，事务整体回滚，因此不会留下“计数器变成 2、但第 1 条消息
不存在”的半状态。

### 4.3 archive/hide 与 append 并发

两种合法线性顺序：

| 第一个拿到锁 | 第二个操作 | 合法结果 |
|---|---|---|
| append | archive/hide | Message 先提交，随后 lifecycle 改变；最终有 1 条消息 |
| archive | append | append 返回 `conversation_archived`；最终 0 条消息 |
| hide | append | append 返回 not-found；最终 0 条消息 |

不存在“lifecycle 已先提交，但后来的 append 仍成功”的合法结果。测试必须主动控制这两个顺序，不能只
让线程同时起跑后接受两种答案。

### 4.4 package smoke 证明什么

Linux smoke 的链路是：

```text
真实 PostgreSQL + migration + FastAPI package
  → 合成 Review Task 安全 failed（外部调用 0）
  → Fake Account Resolver 让 Player Link succeeded（外部调用 0）
  → 使用 relationship 创建 Conversation
  → 追加第 1 条 user Message
  → HTTP 复读 Conversation 和 Message page
```

它证明可重建 package 中的控制面接线，不证明真实 Riot Key、模型质量或 assistant 回复。

---

## 5. 验证：每层绿灯各自证明什么

### 5.1 测试分层

| 层 | 能证明 | 不能替代 |
|---|---|---|
| pure model | strict shape、内容、digest、状态不变量 | PostgreSQL constraint/锁 |
| Service + Fake | 业务映射、Port 防御、错误边界 | 真实事务 |
| FastAPI + Fake | Actor 注入、DTO、HTTP/OpenAPI、日志边界 | DB 并发 |
| metadata/offline migration | ORM/迁移结构和名字基本一致 | trigger 真执行 |
| PostgreSQL migration | FK/CHECK/trigger/downgrade 真语义 | API/package 接线 |
| PostgreSQL Repository | 短事务、回滚、owner scope、分页 | Linux 可重建部署 |
| PostgreSQL concurrency | advisory/row lock 与确定终态 | 公网 SLA |
| Linux package smoke | wheel/image/Compose/API/DB 纵向 | Riot/Provider 质量 |

### 5.2 本轮真实发现并修复了什么

1. **全局 advisory lock 过宽**：初版可能让无关 owner/key 的 create 排队。修为从
   `owner_id + idempotency_key` 经 SHA-256 派生的稳定 signed-bigint，并增加“持有 owner-1/key-A
   的锁不阻塞 owner-2/key-B”真库测试。
2. **Service 对 created projection 防御不足**：新增红灯证明 Repository 若把别的
   `conversation_id` 或非 active 初态冒充 CREATED，Service 必须 503 fail closed。该批红灯曾明确得到
   3 failed，修复后 3 passed。
3. **Barrier-only 并发测试可能假绿**：原测试让 lifecycle 与 append 同时起跑，却接受任一合法结果，
   没证明哪个先拿锁。现在用一个 blocker transaction 锁 Conversation，再用 SQLAlchemy 事件确认第一
   操作已持 relationship、第二操作已尝试同一 relationship 锁，最后释放 blocker；archive/hide 各自
   固定验证 append-first 与 lifecycle-first。
4. **首次 import 测试受模块缓存影响**：原测试文件顶部已经 import composition，后面的
   `importlib.import_module()` 不再是真正首次 import。新增独立 Python 子进程，在 import 前拦截 Secret env、
   Engine 构造和 HTTP request，然后再生成 OpenAPI。
5. **composition 失败清理**：Conversation Repository 构造失败时，readiness 和 endpoint 都安全失败，
   Engine 必须 dispose；正常 shutdown 也解除 Conversation/deletion proxy，避免旧进程对象残留。

### 5.3 当前证据边界

- 本机没有 PostgreSQL/Docker，因此 PostgreSQL tests 会明确 skip；这不是失败，也不是通过。
- 本地完整测试、RAG、Harness、compile/security/YAML/governance/diff 结果在实现提交前会重新生成并记录。
- 只有实现 exact SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke` 全绿，才能关闭 6B-3。
- coverage 在公共闭环前保持 `planned`，避免“文档写完了”被误解成真库已证明。

---

## 6. 运行手册

以下命令都从仓库根目录 `D:\riftcoach-agent` 运行，并显式使用项目虚拟环境。

### 6.1 不需要 PostgreSQL 的聚焦测试

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_conversation_models.py `
  tests\test_conversation_service.py `
  tests\test_conversation_api.py `
  tests\test_api_composition.py `
  tests\test_packaging_smoke.py -q
```

### 6.2 有 PostgreSQL 17 时运行真库测试

先让测试库升级/降级可以安全执行，再设置独立测试 URL：

```powershell
$env:RIFTCOACH_TEST_DATABASE_URL = `
  "postgresql+psycopg://riftcoach:local-only@localhost:5432/riftcoach_test"

.\.venv\Scripts\python.exe -m pytest `
  tests\test_conversation_migrations_postgres.py `
  tests\test_conversation_repository_postgres.py `
  tests\test_conversation_concurrency_postgres.py -q -s
```

不要把开发/生产数据库 URL 填进测试变量；这些测试会执行 migration downgrade/upgrade 和清表。

### 6.3 完整本地门禁

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

RAG 与 Harness 横向门继续运行，因为新增控制面不能破坏旧 Agent 能力：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py `
  --provider hybrid `
  --output "$env:TEMP\riftcoach-rag-development.json" `
  --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 `
  --max-no-answer-fpr 0.0

.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py `
  --provider hybrid `
  --cases data\evaluation\rag_v1_holdout_cases.json `
  --require-independent `
  --output "$env:TEMP\riftcoach-rag-holdout.json" `
  --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 `
  --max-no-answer-fpr 0.0 `
  --min-abstention-accuracy 1.0 `
  --min-citation-support 1.0

.\.venv\Scripts\python.exe scripts\run_review_harness.py `
  --summary examples\fixtures\player_summary_demo.json `
  --deterministic-report examples\fixtures\deterministic_report_demo.md `
  --runs-root "$env:TEMP\riftcoach-harness-6b3" `
  --run-id local_6b3_harness `
  --dry-run
```

### 6.4 Linux/Compose package smoke

```powershell
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke up --build --detach --wait --wait-timeout 120 api
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke run --rm --no-deps smoke
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke down -v --remove-orphans
```

本机没有 Docker 时不要伪造结果；GitHub Actions 的 blocking package job 会提供公开 Linux 证据。

---

## 7. 失败、安全和范围边界

### 7.1 失败如何投影

| 情况 | public 结果 | 为什么 |
|---|---|---|
| body/key/content 非法 | 422 `request_invalid` | 客户端合同错误 |
| 不存在、wrong owner、hidden relationship/Conversation | 404 `conversation_not_found` | 防资源枚举 |
| 同 key、不同 fingerprint | 409 `conversation_idempotency_conflict` | 重试语义冲突 |
| archived 后 append | 409 `conversation_archived` | 资源存在但已关闭写入 |
| DB/Adapter/完整性异常 | 503 `service_unavailable` | 不泄露 SQL/异常正文 |

Message 正文只在正常 owner-scoped 响应里出现；不进入安全错误、结构化 observability、Provider Trace
或 package failure code。

### 7.2 已有的安全防线

- owner 只来自 `ActorContext`；body 没有 owner/PUUID/subject/role/source 字段；
- wrong owner 与不存在统一 404；
- composite FK 防跨 owner/subject/role 拼接；
- relationship status 在锁内检查，关闭 check-then-insert 竞态；
- Conversation binding 和不可逆 lifecycle 有 trigger；
- Message 核心字段 append-only；
- public user Message 不能伪造 assistant/source；
- content 有长度、控制字符和 UTF-8/digest 约束；
- API import/OpenAPI 不读取 Key、不建 Engine、不发 HTTP；
- package smoke 的外部 Riot/Provider 调用固定为 0。

### 7.3 现在仍然没有什么

- 没有正式 JWT/OAuth/RSO；当前开发 Actor 不能冒充公网认证；
- 没有 assistant terminal 持久化；
- 没有 Conversation-bound Review Task 2.0；
- 没有 Memory Candidate、Profile、Plan、Progress 或 Memory Context；
- 没有 SSE/前端或自由聊天；
- 没有 Redis、向量 Memory、LangGraph、MCP 或 Multi-Agent；
- 没有公网 SLA、备份或跨机容灾证明；
- 没有在本机执行 PostgreSQL/Docker 时，不能声称本机证明了并发/trigger/package。

6B-4 才会让 Review Task 从 Conversation 的服务器绑定中继承 owner/relationship/subject；6B-5 以后
才开始 Candidate/长期 Memory。阶段顺序没有因为 6B-3 代码较完整而改变。

---

## 8. 面试如何准确表达

### 8.1 30 秒版本

> 我为 RiftCoach 实现了 owner-scoped 的 Conversation/Message 控制面。Conversation 创建时从 active
> player relationship 冻结 owner、subject 和 role，并用复合外键与 trigger 防止跨主体错绑和 rebind；
> Message 通过 Conversation 行锁在同一事务内分配连续序号。公共 API 只允许 user Message，assistant
> 需要可信 run provenance。并发、trigger 和回滚语义用真实 PostgreSQL 17 CI 验证，而不是用 SQLite
> 冒充。

### 8.2 两分钟版本

> 这一步的难点不是建两张聊天表，而是把身份、幂等、并发和来源边界做对。Riot ID 可变，所以我先复用
> Player Link 得到的稳定 subject/owner relationship。创建时锁 active relationship，复制完整 tuple，
> 再用 owner-scoped key 和 fingerprint 做 replay/conflict；跨 relationship 的同 key 竞态用 scoped
> PostgreSQL advisory lock 收敛。追加消息时统一按 relationship→Conversation 拿锁，用行上的
> next_message_sequence 分配序号，并让 insert、counter 和时间戳同事务提交。数据库再用 composite FK、
> unique、CHECK 和 immutable trigger 做第二道防线。HTTP DTO 不接受 owner、PUUID、role 或 source，
> 因而客户端无法伪造 assistant。测试上我不只测 happy path，还固定两种 lifecycle/append 锁顺序、回滚、
> direct SQL rebind、跨 owner 以及 Linux package 纵向链路。

### 8.3 常见追问

**问：为什么不用数据库自增 ID 直接当消息顺序？**

答：全局自增能唯一，但不直接表达“每个 Conversation 从 1 连续编号”；事务失败也可能留 gap。这里锁
Conversation 的本地 counter，让已提交消息在聚合内连续，unique 再兜底。

**问：复合 FK 为什么还不够？**

答：FK 只证明 relationship tuple 存在，不能表达它此刻必须 active。需要同事务锁父行并检查 status，
否则会有检查后 relationship 被隐藏、Conversation 仍提交的竞态。

**问：为什么既有应用校验又有数据库 trigger？**

答：应用校验给出清晰业务错误并保护正常路径；数据库约束保护其他进程、未来代码或 direct SQL 不绕过
核心不变量。两层职责不同，不是重复。

**问：为什么不用 Redis 做聊天？**

答：当前需要的是唯一真源、事务、复合身份和可逆 migration，PostgreSQL 已经满足。现在加 Redis 会产生
双写、删除传播和新运维面；只有后续出现真实延迟/吞吐 Bad Case 才重新评估缓存或消息层。

**问：这已经是 Agent Memory 吗？**

答：不是。Message 是原始对话记录；Memory 必须经过 Candidate、provenance 和写入门，选择性形成长期
状态。把所有聊天直接叫 Memory 会让模型推断污染长期画像。

**问：为什么不用 LangGraph？**

答：6B-3 是确定性的身份和持久化控制面，没有图编排需求。项目采用技术门要求先有可复现 Bad Case、
备选和评测；在这里引入框架不会改善事务正确性，只会扩大依赖和解释成本。

---

## 9. 自测：能回答这些才算真的理解

1. Conversation、Review Task、Runtime run 和 Memory 的职责分别是什么？
2. 为什么 Riot ID 不能作为长期 Conversation 主体？
3. Idempotency-Key 和 request fingerprint 各解决什么问题？
4. 为什么 Message sequence 必须在 Conversation 行锁下分配？
5. composite FK 能证明什么，不能证明什么？
6. archived、hidden、hidden relationship 的读取/写入区别是什么？
7. 为什么 public API 不开放 assistant role？
8. trigger、Repository transaction、unique constraint 分别保护哪一层？
9. Barrier-only 并发测试为什么可能假绿？现在如何固定两种锁顺序？
10. 为什么本地 1,000 多个测试通过仍不能代替 exact-SHA PostgreSQL/package CI？

如果这些问题能用自己的话回答，并能从代码地图找到对应实现与测试，才算真正掌握 6B-3，而不只是“看过
Codex 写代码”。
