# 6B-8 Memory-aware Context / Typed Conversation Turns 设计稿

## 1. 初学者问题定义

长期 Memory 的价值不是“存得越多越好”，而是下一次运行只拿到合法、相关、可审计的一小部分。Context
是单次运行的派生输入，不是数据库副本；Message 是对话历史，不是 system prompt；Memory 是长期状态，
也不是 Tool 权限。6B-8 要把这三层接起来，同时保证一条含“忽略之前规则”的历史正文仍只是 data。

Assistant turn 也必须来自可信终态：模型草稿可能被 Harness 拒绝，Runtime/Artifact 可能损坏，Worker 也
可能失去 SQL ownership。只有 SQL Task、publication、final Artifact 和 Conversation identity 都一致，
最终 report 才能成为下一轮可见的 assistant Message。

## 2. 本批做与不做

本批实现服务器派生 Context binding、bounded legal selector、private body-free manifest、现有
ContextBuilder/Runtime/Harness data-only 接线、typed terminal Assistant writer 和显式 typed Candidate
proposal seam。它不新增开放域聊天 Skill，不改变两个 Skill 的 system instructions/Tool 权限，不提高
ceiling，不做向量检索、6B-9 export/delete/retention、Auth/RSO、SSE/前端或真实外部调用。

## 3. 方案比较与选择

| 方案 | 优点 | 风险 | 裁决 |
|---|---|---|---|
| 原地扩展 `ContextBuilderV1` | 内部选择逻辑可直接复用 | 核心 Builder 混入 DB/Session，所有旧 Prompt identity 隐式变化 | 不采用 |
| run-scoped decorator | 复用同一 Builder/Sizer/Runtime，binding 显式，旧调用兼容 | 增加 wrapper 与 manifest store | 采用 |
| Runtime 外拼 ChatMessage | 代码少 | 绕过 trust/canonical rendering/ceiling/omission | 拒绝 |

选中方案保持一个 AgentRuntime 和一个 ReviewHarness。Decorator 只提供额外 data sections，不拥有 Agent
循环、Provider 或发布状态机。

## 4. 合同与组件

### 4.1 `MemoryContextBinding`

字段为 run_id、owner_id、conversation_id、relationship_id、player_subject_id、relationship_role。它只由
schema 2.0 `ConversationReviewTaskBinding` 转换，进入 `RuntimeRunRequest` 私有字段；legacy request 为 null。
Runtime 在 Context 前再次核对 run identity。

### 4.2 selector snapshot

Repository 在一个只读短事务中先验证 visible Conversation 与 active relationship tuple，再分别查询：

- 最近 12 条 `hidden_at IS NULL` Message，数据库 newest-first limit 后恢复 chronological order；
- owner-global active Preference，按 key/record ID 稳定排序，最多 16；
- 当前 player active Review Memory，最多 12；
- self-only active Profile（16）、active Plan（1）和每 metric 最新 active Progress（12）；
- observed 只保留 Preference、Message 和 allowlisted observed Review Memory。

每条 snapshot record 同时携带 kind、ID、version、digest、stable order、canonical value 和 trust label。
Repository 不返回 Candidate、superseded/retired/hidden 或跨作用域数据。

### 4.3 Context composition

优先级冻结为当前 typed fact sections > owner Preference > active Plan > Profile > latest Progress > Review
Memory > historical Message；同类用稳定 order。所有附加 section 都是
`ContextTrust.DETERMINISTIC_FACTS`、`instructional=false`、user role。Builder 计算
`min(manifest ceiling, caller ceiling)`；必需基础事实装不下仍 fail closed，附加记录只整项选中或省略。

### 4.4 manifest

manifest schema 1.0 包含：run/binding、policy version、effective ceiling、estimated units、每类候选/选中/
省略计数，以及 refs（kind/id/version/digest/disposition/reason）。正文不进入文件。规范 JSON 的 SHA-256
由 store 返回，重复同 run 内容相同则 replay，不同则 integrity failure。

### 4.5 typed terminal turn

`TerminalAssistantTurn` 包含 task/run/binding、publication、final Artifact kind/digest、assistant content
及零个或多个 `TerminalCandidateProposal`。Writer 先验证 Task terminal，再锁 Conversation，按 next sequence
追加 assistant。已有同 source run 且 digest 相同为 replay；不同为 integrity failure。

Candidate proposal 只允许严格枚举 kind/key/operation/payload/confidence，来源固定为 model inference 或
published review observation，绑定同 task/run/artifact。它仍创建 pending Candidate；Gate 禁止的 proposal
使整个 terminal projection fail closed。当前 Recent Review terminal projection 不产生 proposal，因此不
从报告文本提取或猜测 Memory。

## 5. 数据与控制流

```text
schema 2.0 Task binding
→ Application compiler 构造 RuntimeRunRequest + MemoryContextBinding
→ Runtime validate Skill/policy
→ selector owner-scoped 读取 legal snapshot（短事务结束）
→ decorator 投影 data-only sections + existing ContextBuilder/Sizer
→ 原子写 body-free memory_context_manifest
→ existing AgentLoop → ReviewHarness → typed terminal/final Artifact
→ Worker 将 SQL Task 提交 succeeded
→ terminal turn writer 重新验证 Task/Artifact/binding
→ append assistant Message；显式 typed proposals（若有）进入 Candidate gate
```

任何 DB/file Context 失败发生在 Provider 前；任何 terminal writer 失败不能把 draft 或 rejected 内容写成
Message。外部调用期间不持有数据库锁。

## 6. 失败、安全与隐私

- 不存在、隐藏、跨 owner 或 tuple 漂移统一为 context unavailable，不泄露哪一层存在；
- observed Profile/Plan/Progress 在 pure selector 与 SQL query 双重排除；
- Message/Memory 正文不进入 manifest、Trace、日志或公共 DTO；
- system/tool/provider/reasoning 不是 Conversation Message；
- report 只有 published/degraded 且 final Artifact digest 匹配才可落库；
- rejected/failed、source run 冲突、Conversation hidden/archived、重复不同 digest 全部 fail closed；
- 文件 manifest 使用安全 run path、大小上限、原子 replace，拒绝覆盖不一致内容；
- 不声称 ContextSizer 是 Provider tokenizer，也不声称当前没有真实模型运行的结果证明质量提升。

## 7. 测试证明

1. pure binding/snapshot/manifest/priority/whole-record selection；
2. Context decorator 的 role/trust/ceiling/canonical rendering/injection；
3. 真实 PostgreSQL 两 owner、self/observed、hidden/superseded 排除与稳定顺序；
4. manifest store replay/tamper/path/size/atomic failure；
5. terminal assistant succeeded/rejected/digest/identity/replay/concurrency/rollback；
6. Runtime/Application/Executor/Worker schema 2.0 纵向，legacy 1.0 parity；
7. Linux no-I/O package 与完整门禁、八维 walkthrough、exact-SHA 三 job。

## 8. 当前限制

V1 只增强类型化 Recent Review，不支持任意聊天 follow-up；当前 output 不含 typed Candidate proposal，所以
生产只写 terminal Assistant Message；Message 与 Memory 用结构化 SQL selector，不做语义检索；正式 Auth、
RLS、跨机事务、自动恢复、export/delete/retention 属于后续明确 checkpoint。
