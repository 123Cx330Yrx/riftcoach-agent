# ADR-0042：Memory Candidate 使用事务内 typed materializer 接缝

- 状态：Accepted
- 日期：2026-08-20
- 决策范围：`6B-5-memory-candidate-write-gate`
- 上游：ADR-0039、ADR-0040、ADR-0041

## 背景

RiftCoach 已经有固定玩家身份的 Conversation、Message，以及绑定同一身份的 Review Task。下一步要把
“用户、规则或模型提出的一条值得长期保存的信息”变成可审计的 `Memory Candidate`，但 6B-5 又明确
不能提前创建 6B-6/6B-7 的 Preference、Profile、Review Memory、Training Plan、Progress 业务表。

这里存在一个容易被掩盖的矛盾：Candidate 可以被确认，但如果数据库里还没有对应的长期 Memory 表，
“确认成功”究竟写入了什么？只把 Candidate 状态改成 `accepted`，或只插入一张 receipt，都会把
“批准提案”冒充成“长期 Memory 已物化”。这既破坏 exactly-once 语义，也会让面试表述失真。

同时必须满足以下不变量：

- Candidate 的 owner/conversation/relationship/subject/role 只能从服务器 Conversation 派生；
- 模型推断和自然语言抽取无论 confidence 多高都只能 pending；
- `observed` 关系只能提出受限第三人称 review observation；
- Candidate 终态不可逆；
- 目标记录写入与 Candidate accepted 必须同一 PostgreSQL 事务；
- 生产环境没有真实 typed target 时必须 fail closed；
- materializer 不能在锁内调用模型、网络、文件或外部服务。

## 决策

采用“事务内 typed materializer 接缝”，不创建万能 Memory 表，也不把 receipt 当作 Memory。

Repository 在 acceptance 事务中执行：

```text
lock owner-scoped Candidate
→ 验证 pending、Conversation/relationship 仍有效、actor 有权决策
→ 按 candidate_kind 查找已注册 typed materializer
→ materializer 使用同一个 SQLAlchemy Session 写入具体目标表
→ materializer 返回有界 MaterializedMemoryReference
→ Candidate 写 accepted + target reference + decision metadata
→ 一次 commit
```

materializer 是明确的本地持久化协议：输入同一事务 Session 和已经验证的 Candidate，输出目标类型、目标
记录 ID 与 materializer 版本。它不能 commit/rollback，不能进行 I/O，不能改变 Candidate 身份。

6B-5 用测试专用 typed target 表验证成功、回滚、并发和重放。正式 API composition 在 6B-6 注册真实
Preference/Profile/Review Memory materializer 前使用空 registry；此时 accept 返回安全的
`memory_target_unavailable`，Candidate 保持 pending。这个结果表示“写入能力尚未安装”，而不是 Memory
写入成功。

Candidate 自身保存 materialized target reference 只用于审计和重放，不构成目标记录。6B-6/6B-7 的每张
typed target 表仍必须拥有 `source_candidate_id UNIQUE`，形成数据库级第二道 exactly-once 防线。

## Gate 规则

- `user_message_extraction`、`model_inference`：永远 `requires_confirmation=true`；
- `user_structured_input`：仅 allowlisted owner preference 或 self profile 可标记为系统可接受，但真正
  materialize 仍要求相应 typed materializer 已注册；
- `deterministic_run_fact`：只允许 review/progress 类型；具体 Plan/metric 约束由 typed materializer 检查；
- `published_review_observation`：只允许 review observation；
- `observed`：只允许 `review_memory + append + observation_note|public_trend`；
- confidence 只用于排序/展示，不参与授权；
- 用户可以确认 pending Candidate；system actor 只能接受 `requires_confirmation=false` 的 Candidate；
- reject/expire 不调用 materializer；accepted/rejected/expired 都不可逆。

## 公开边界

公开 DTO 只返回 Candidate ID、Conversation ID、类型、key、operation、状态、是否需确认、时间和安全 reason
code。它不返回 payload、完整 provenance、producer、confidence、relationship/subject、PUUID、Message body、
Prompt 或 Artifact body。6B-5 的 public create 只代表用户结构化输入；模型/抽取/确定性事实走以后受信任的
内部 producer，不允许客户端伪造 provenance。

## 备选方案

### A. 一张通用 `memories` JSONB 表

拒绝。它会把 Preference、Profile、Review、Plan、Progress 的角色权限、生命周期和冲突规则压成运行时
if/else，PostgreSQL 无法直接证明 observed 不拥有私人画像或训练进度，也提前越过 6B-6/6B-7。

### B. Candidate accepted + materialization receipt

拒绝。receipt 只能证明系统记录了一次批准动作，不能证明目标 Memory 存在。若后续另事务补写目标表，
进程崩溃会留下半完成状态；若把 receipt 称为 Memory，则语义失真。

### C. 新增 `approved` 中间态

暂不采用。它会改变 ADR-0039 已冻结的 `pending → accepted|rejected|expired` 状态机，并让“已批准但未写入”
成为需要长期恢复的新业务状态。当前通过 fail-closed materializer 可以保持状态简单；只有真实 UX/异步写入
Bad Case 出现时才重新 ADR。

## 后果

### 正面

- 6B-5 可以真实证明原子写协议，而不假装具体长期 Memory 已存在；
- 6B-6/6B-7 只需实现类型化表与 materializer，不必重写 Candidate gate；
- acceptance 失败自动回滚，不会留下“目标没写、Candidate 却 accepted”；
- 生产未配置目标时安全拒绝，测试替身不能泄漏进产品 composition。

### 代价

- Repository 会接收一个受限 registry，并在事务锁内调用本地持久化策略，需要严格 code review；
- 6B-5 的正式 API 能创建、查询、拒绝 Candidate，但在 6B-6 前无法真正 accept 为长期 Memory；
- 跨多张 typed target 表不能使用普通动态外键，必须依靠 materializer、Candidate target reference 和每张
  目标表的 `source_candidate_id UNIQUE` 共同证明。

## 失败与安全边界

- materializer 缺失：Candidate 保持 pending，返回 allowlisted unavailable；
- materializer 抛错、返回错误 kind/ID/version 或企图提交：整个事务失败，Candidate 保持 pending；
- 并发接受：Candidate row lock 串行；第二个请求只读到 accepted 并返回 replay；
- 关系已失效或 Conversation hidden/archived：不 materialize；
- 重复拒绝/过期：同终态可 replay，不同终态返回 terminal conflict；
- 本 ADR 不等于正式 Auth、模型抽取、assistant terminal、Memory Context、向量召回或生产可用。

## 验证

- pure Gate：来源、类型、scope、role、confidence 与 payload bounds；
- PostgreSQL：0005 upgrade/downgrade、FK/CHECK/trigger、owner 隔离、幂等与并发；
- transaction：测试 typed target + Candidate 同 commit，任一步失败整体 rollback；
- API：trusted owner、body/provenance-safe DTO、strict extra forbid、fail-closed accept；
- package：import/OpenAPI/Compose smoke 外部 Riot/Provider/Key I/O 为 0；
- public CI：同一 exact SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke`。
