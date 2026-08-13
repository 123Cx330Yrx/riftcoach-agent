# 5D-6b Zhipu Recent-form Domain Slice 设计

## 1. 当前问题

真实 Adapter Protocol Slice 已经证明生产 `ZhipuProvider` 可以完成严格结构化响应和
一次 `knowledge.search` 工具往返，但它使用的是固定协议夹具，没有经过真实
`recent-form-review` Skill、Context Builder、领域 RAG、ReviewHarness 和 typed output。

因此 5D-6b 还缺最后一层准入：证明同一 Provider 能进入 RiftCoach 已有的领域主链。
本切片只验收组合协议，不在单个样例上调整 Prompt 或比较模型质量。

## 2. 本轮实现与不实现

本轮实现：

- 固定匿名化 Summary/确定性报告作为输入；
- 真实 Catalog、Router、ExecutionBoundary、ContextBuilder 和 AgentRunCompiler；
- 真实本地 `knowledge.search`、AgentLoop、ReviewHarness 和 typed Skill Output；
- Agent 与 Harness 共用一个生产 Provider 和一个累计调用预算；
- 读取、严格校验并哈希上一轮公开 Adapter 协议结果；
- 只保存调用计数、Token、延迟、终态和 SHA-256 等脱敏证据；
- 用 Fake Provider 完整运行同一控制流，真实调用必须等代码公开 CI 通过。

本轮不实现：

- 不执行真实 GLM 领域调用；
- 不修改 Skill Prompt 来追求高分；
- 不选择或接入第二 Provider；
- 不进入 5D-7 Prompt/Context 领域评测；
- 不引入 LangGraph、Agent SDK、Multi-Agent 或第二套 Harness。

## 3. 为什么必须累计核算 7 calls

原始 5D-6b 实施计划把生产 Adapter 协议与领域切片合计限制为最多 7 次真实调用。
协议切片已经使用 3 次：一次结构化直调和两次 Agent 工具往返。因此领域切片只能获得
剩余 4 次，不能把它重新解释为额外 7 次。

```text
approved cumulative budget = 7
prior adapter protocol calls = 3
remaining domain budget = 4
```

正常领域路径需要：

```text
Agent tool request       1 call
Agent final response     1 call
strict Evaluation        1 call
--------------------------------
happy path               3 calls
```

剩余 1 次只允许现有结构化 Evaluation 做一次格式 repair。若模型要求 Coach revision，
后续再评测会超过剩余预算；本次准入必须 fail closed。Fake Provider 测试已经覆盖完整
修订工作流，真实准入不需要付费重跑每个分支。

## 4. 采用方案与替代方案

### 方案 A：领域脚本重新获得 7 calls

最容易实现，但累计最坏值变成 10，违背已经确认的实验边界。拒绝。

### 方案 B：跳过真实 Evaluator 或用 Fake Evaluator

可以把领域调用压到两次，却不能证明真实结构化 Evaluation 能通过 ToolRuntime 进入
唯一 ReviewHarness。拒绝。

### 方案 C：历史证据核算 + 一个共享预算 Provider（采用）

```text
validate zhipu_adapter_slice.json
        │ prior calls=3 + exact-file SHA-256
        ▼
ExternalCallBudget(max_calls=4)
        │
ObservedBudgetedProvider
        ├── AgentLoop (2 calls)
        └── llm.chat ToolRuntime
              ├── Evaluation (1 call)
              └── optional format repair (at most 1 call)
```

预算放在 `LLMProvider.chat()` 前，因此第 5 次领域调用会在底层 Provider 和网络之前
被拒绝。真实 SDK 继续使用 `max_retries=0`；本次准入专用 `llm.chat` ToolDefinition
也收紧为单次尝试，避免一次 Harness 步骤偷偷扩大为多次出网。

## 5. 领域数据流与控制流

```text
anonymous Summary + deterministic report + fixed user request
        │
        ▼
SkillCatalog -> DeterministicSkillRouter
        │ selected recent-form-review@0.2.0
        ▼
SkillExecutionBoundary
        │ typed input + artifact commitments
        ▼
ContextBuilderV1 -> AgentRunCompiler
        │ trust-typed context + Manifest budgets/tools
        ▼
AgentLoop -> real local knowledge.search -> Tool Observation -> final draft
        │
        ▼
SkillAgentDraftPreparer
        │ CoachDraft + KnowledgeEvidence from actual ToolExecutionRecord
        ▼
SkillReviewExecutor -> only ReviewHarness
        │ real structured Evaluation / bounded repair
        ▼
published | degraded | rejected -> typed RecentFormReviewOutput
```

数据流传递的是事实、草稿、工具证据和 Artifact；控制流决定权限、预算、停止、评测和
发布。模型只能提出工具调用和草稿，不能自己提高预算或发布报告。

## 6. 准入与质量必须分开

领域 capability 准入要求：

- Router 精确选择 `recent-form-review@0.2.0`；
- Agent 精确完成一次成功的 `knowledge.search` 往返；
- 工具结果产生至少一个可归因知识来源；
- 至少一次 Evaluation 通过严格 Pydantic 合同；
- Harness 到达合法 terminal state；
- typed output 从已验证 Artifact 构造；
- 累计调用不超过 7，领域调用不超过 4。

`published` 不是 capability 准入的必要条件。若结构化 Evaluation 合法地判定报告质量
不足并让 Harness 降级或拒绝，协议仍可能通过；该质量样例原样留给 5D-7。反之，若
缺少工具证据、Evaluation 无法结构化、预算耗尽或 typed output 失败，则不能准入。

## 7. 脱敏结果合同

公开结果记录：

- Provider、请求模型、代码 SHA、fixture digest；
- 上一轮协议结果的精确文件 SHA、代码 SHA 和 3 calls；
- 本轮剩余/已用/累计 calls 与分阶段调用计数；
- 响应数、Token、延迟、resolved model、finish reason 和 request-ID hash；
- ToolCall/成功执行/知识来源数量；
- Evaluation 是否严格验证、分数、Harness 终态和 typed output digest；
- 安全错误码和是否 domain-admitted。

不保存 API Key、完整 Prompt、模型正文、Tool Observation、知识正文、原始 request ID、
原始异常或临时 Harness Artifact。真实运行使用系统临时目录，结束后自动清理原文。

## 8. 测试怎样证明

- 篡改、未准入、非 3-call 或 Provider/model 不一致的历史结果在出网前被拒绝；
- 第 5 次领域调用在底层 Fake Provider 前被阻止；
- `llm.chat` 准入工具只有一次尝试、无缓存、无 fallback；
- Fake Provider 让真实 Skill 主链依次产生 ToolCall、Observation 后草稿和严格 Evaluation；
- 结果必须显示 Agent 2 calls、Evaluation 1 call、一次知识调用/执行及合法 terminal output；
- 结构化 repair 最多使用第 4 call；需要继续修订/再评测时 fail closed；
- 序列化结果中不出现 fixture 正文、Prompt、模型正文、Observation、原始 ID 或异常；
- 真实 CLI 拒绝脏工作树与既有结果覆盖，保证 `code_sha` 和单次实验可审计；
- pytest/CI 不创建真实客户端、不读取 Key、不访问网络。

## 9. 完成后的准确表述

离线 TDD 完成后只能说：

> RiftCoach 已实现真实近期复盘 Provider 准入控制器：它复用现有 Skill、RAG、
> AgentLoop、ReviewHarness 和 typed output，并用上一轮证据核算累计 7-call 预算；当前
> 完整领域链只由 Fake Provider 离线验证，真实 GLM 运行仍待公开 CI 后执行。

不能说 GLM 已完成领域 Skill 准入、Prompt E2E 已完成、GLM 是最终模型赢家，或整个
5D 已完成。
