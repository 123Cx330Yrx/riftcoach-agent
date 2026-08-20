# ADR-0045：采用 run-scoped Memory Context 与 terminal turn writer

- 状态：Accepted（6B-8 设计批）
- 日期：2026-08-21
- 范围：`6B-8-memory-aware-context-typed-turns`
- 上游：ADR-0039、ADR-0040、ADR-0041、ADR-0042、ADR-0043、ADR-0044
- 需求：RQ-071

## 背景

6B-3 已建立固定玩家身份的 Conversation/Message，6B-4 让 Recent Review Task 继承该身份，6B-5 至
6B-7 又建立 Candidate、typed Memory、Plan 和 Artifact-grounded Progress。当前 Agent 仍只看到本次
Summary/确定性报告；如果把整个聊天或 Memory JSON 直接拼进 Prompt，会同时破坏 owner 隔离、
self/observed 权限、Context ceiling、Prompt 注入边界和可复现性。

另一个缺口是 Assistant 正文何时成为 Message。Runtime 草稿、Harness rejected 输出和只有文件但未完成
SQL terminal 的结果都不是可信对话回复；若过早写入，下一轮 Context 会把未发布草稿当历史事实。

## 决策

### 1. 使用服务器派生的 run-scoped binding

Conversation-bound Task 的既有 `owner_id + conversation_id + relationship_id + player_subject_id + role`
成为唯一 Memory Context 身份。该 binding 由 Task Repository 冻结并由 Executor 传给 Application/Runtime，
客户端请求体不增加 owner、subject、PUUID 或 Memory 选择字段。legacy schema 1.0 任务没有 binding，继续
走无 Memory Context 的兼容路径。

### 2. 以 decorator 扩展现有 ContextBuilder

新增 `MemoryAwareContextBuilder`，内部先让 PostgreSQL selector 返回有界、合法的记录快照，再把每条记录
投影为 `ContextTrust.DETERMINISTIC_FACTS` 的 data-only section，最后交给现有 `ContextBuilderV1` 的同一
Sizer、整 section 选择和有效 ceiling。调用方不能提高 Skill Manifest ceiling，Memory 文本也不能改变
system role、Tool allowlist、迭代、超时或 Harness 发布权。

不建立第二套 Agent/Prompt 编排；Runtime、Compiler、AgentLoop、ToolRuntime 和 ReviewHarness 保持原链路。

### 3. selector 使用固定来源、上限和稳定顺序

候选来源只有：同 Conversation 最近可见 user/assistant Message、owner-global active Preference、同
relationship active Profile/Review Memory，以及 self relationship 的 active Plan/每 metric 最新 active
Progress。observed relationship 永不读取 Profile/Plan/Progress。pending/rejected/expired Candidate、
superseded/retired/hidden 记录和其他 owner/Conversation/relationship/subject 一律不进入候选集。

固定上限为 Message 12、Preference 16、Profile 16、Plan 1、Progress 12、Review Memory 12。排序键和
优先级在纯合同中冻结；预算不足时整记录省略，不裁断 Message 或 canonical JSON。

### 4. 私有 manifest body-free 持久化

每次有 binding 的运行写 `memory_context_manifest.json`，只记录 run/binding、selector policy version、
selected/omitted record kind、record ID、version、content/payload digest、数量和 omission reason。它不保存
Message/Memory 正文、PUUID、Riot ID、Prompt、Tool/Provider body 或异常。manifest 使用安全 run path、
规范 JSON、SHA-256 与原子替换；写失败使 Context 阶段 fail closed，模型不执行。

### 5. Assistant 只在 SQL Task 与 Artifact 都已终态后追加

新增 typed terminal turn writer。它重新验证 schema 2.0 Task 已 `succeeded`、publication 为
`published|degraded`、`report_available=true`、run/binding/final Artifact digest 与输入完全一致，然后在
Conversation row lock 下追加一条 assistant Message。`conversation_id + source_run_id` partial unique 保证
重放幂等；failed/rejected、隐藏 Conversation、身份或 digest 不匹配均不写。

Writer 允许同一可信 terminal 携带显式 typed Candidate proposals，但所有 proposal 仍通过 6B-5 Gate 并
保持 pending/confirmation 语义。当前 `RecentFormReviewOutput` 没有 typed proposal 字段，因此生产纵向只
写 Assistant Message，不从自然语言报告猜 Candidate，也不修改 Prompt Program output identity。

## 备选方案

### 原地把 Message/Memory 参数加入 `ContextBuilderV1`

可以复用全部内部函数，但会把 PostgreSQL/Conversation 语义塞进原本只处理已验证 Skill input 的核心，
并让既有 Prompt/Context identity 在所有调用方中发生隐式漂移。拒绝。

### 在 Runtime 外直接拼接 ChatMessage

改动最少，但会绕过 ContextBundle canonical rendering、Sizer、trust label、omission evidence 和 Compiler
复核。拒绝。

### 新建 Session Agent 或自由聊天 Skill

能容纳任意 follow-up，却没有路由、评测、工具权限和领域质量证据，也会复制现有 Runtime/Harness。
拒绝；V1 只增强已类型化的 Conversation-bound Recent Review。

## 后果

正面结果是 Context 来源、权限、预算和终态 Message 都可单独审计，legacy 调用保持兼容。代价是 Runtime
请求多一个私有 binding，worker composition 多一个 selector/store/writer，真实 PostgreSQL 与文件故障都
需要测试。manifest 文件与 SQL Message 不是一个跨介质原子事务；manifest 是本次输入证据，Assistant
Message 则由 SQL terminal 重新验证并幂等写入，6B-9 再验证清理与补偿。

只有出现自由 follow-up 的真实 Bad Case、当前固定 selector 不能表达的检索需求，或规模测试证明 SQL
选择不可接受时，才分别通过新 Skill/评测、语义索引或新基础设施 ADR 重开。
