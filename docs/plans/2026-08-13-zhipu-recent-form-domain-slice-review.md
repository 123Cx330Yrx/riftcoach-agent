# 5D-6b Recent-form Domain Slice 初学者复核

## 1. 这一轮究竟在解决什么

前一轮真实 `Adapter Protocol Slice` 已经证明两件底层能力：

1. `ZhipuProvider` 能把 RiftCoach 的结构化输出合同翻译成智谱请求，再把响应还原为
   Provider-neutral 数据；
2. 同一个 Adapter 能让 `AgentLoop` 提出一次 `knowledge.search`，接收本地工具结果，
   再生成最终文本。

但那还是一个固定协议夹具。它没有证明真实 `recent-form-review` Skill 能经过路由、
上下文构造、领域 RAG、独立评测和发布门禁。因此本轮增加的是一条**领域纵向切片的
离线准入控制器**，不是另一套 Agent，也不是 RAG 重写。

```text
协议层问题：这个 Provider 会不会按我们的消息/工具/JSON 合同说话？
领域层问题：它能不能被放进 RiftCoach 的真实近期复盘控制流？
质量层问题：它在多种真实案例上生成的报告到底好不好？
```

本轮先离线完成第二个问题的可执行考场；随后真实 GLM 只进入一次，但在一个计费请求后
没有形成统一 `ChatResponse`，因此没有 ToolCall、知识证据或 Evaluation。这个结果让
领域能力不准入并安全降级；第三个多案例质量问题仍属于 `5D-7`。

## 2. 五个组件各自负责什么

### Provider Adapter

`ZhipuProvider` 是双向翻译器。向外把统一 `ChatRequest` 翻译成智谱 SDK 参数，向内把
智谱响应翻译成统一 `ChatResponse`。它不负责选择 Skill、检索知识或决定发布。

### Agent Loop

`AgentLoop` 是有界的“模型 -> 工具 -> 观察 -> 模型”循环。模型可以在白名单内提出
工具调用，但不能注册新工具、提高迭代次数或直接发布报告。

### Tool Runtime

`ToolRuntime` 执行已经注册的工具，并负责 Schema、超时、重试、缓存、熔断和错误信封。
本次 Agent 侧只注册本地只读 `knowledge.search`；Harness 侧单独注册一次尝试、无缓存、
无 fallback 的 `llm.chat`。

### Skill

`recent-form-review` 声明这类任务的输入输出、允许工具、迭代/调用预算、上下文上限和
质量阈值。Skill 是工作流合同，不是模型，也不是一个自由运行的 Agent。

### Review Harness

`ReviewHarness` 是唯一发布控制面。Agent 的文本先只是 `CoachDraft`；Harness 再执行
结构化事实评测，必要时受限修订，最终只能发布、降级到确定性报告或拒绝。模型自己
不能宣布“我通过了”。

## 3. 数据流与控制流

数据流回答“内容传了什么”：

```text
匿名 Summary + 确定性报告
  -> 最小领域事实 Context
  -> knowledge.search 的知识结果
  -> CoachDraft + KnowledgeEvidence
  -> EvaluationResult
  -> terminal typed Skill Output
```

控制流回答“谁有权决定下一步”：

```text
SkillCatalog / Router
  -> SkillExecutionBoundary
  -> ContextBuilderV1 / AgentRunCompiler
  -> AgentLoop / ToolRuntime
  -> SkillReviewExecutor / ReviewHarness
  -> publish | degrade | reject
```

这两个流必须分开。知识正文属于数据，不能因为正文里写了“请调用某工具”就获得工具
权限；权限只来自已经验证的 Skill Manifest 和 Registry。

## 4. 一次正常运行为什么是三次模型调用

正常 recent-form 领域路径是：

```text
Call 1: Agent 读取事实，提出 knowledge.search
         -> 本地工具执行，不消耗模型调用
Call 2: Agent 看到 Tool Observation，生成 CoachDraft
Call 3: 独立 Evaluator 返回严格 JSON EvaluationResult
```

因此 happy path 是 3 次模型调用，不是“模型只被调用一次”。RAG 检索是本地 Tool 调用，
不计入模型调用数，但仍受 Tool Runtime 的权限与超时约束。

## 5. 为什么是累计 3 + 4，而不是 3 + 7

5D-6b 原设计给协议切片和领域切片的真实实验累计上限是 7 calls。协议切片已经真实使用
3 calls，所以领域切片只剩 4 calls：

```text
累计批准上限 7
- 已用协议调用 3
= 领域剩余预算 4
```

第 4 个领域 call 只留给一次结构化 Evaluation 格式修复。若 Evaluation 判定需要修订，
则“修订 + 再评测”至少需要两个额外 calls，会越过累计上限。控制器允许第 4 call 完成
修订，但第 5 次领域调用会在进入底层 Provider 和网络之前被拒绝，整次准入失败关闭。

这里的原则叫 **pre-I/O budget enforcement**：预算不是调用后记账，而是在可能产生
外部费用和副作用之前检查。

## 6. 为什么要复读上一轮结果文件

控制器不能只相信代码里的常量“之前用了 3 次”。它会重新读取公开的
`zhipu_adapter_slice.json`，用严格 Pydantic 合同验证：

- 上一轮确实 `admitted=true`；
- 调用数精确为 3；
- Provider 与 model 和本轮一致；
- 记录上一轮代码 SHA；
- 对上一轮结果文件本身计算 SHA-256。

这样新的领域结果能证明它继承的是哪一份历史证据，不能把另一模型、失败结果或被修改
过的 JSON 冒充为调用预算前提。

## 7. 为什么 Agent 和 Harness 必须共用一个预算器

如果 Agent 有 4 次预算、Evaluator 又有自己的 4 次预算，表面每个组件都合规，实际却
可能出网 8 次。本次用一个 `_ObservedBudgetedProvider` 同时注入 AgentLoop 和 Harness
的 `llm.chat`，所有真实模型请求都先经过同一个 `ExternalCallBudget(max_calls=4)`。

这叫把约束放在**共享外部副作用边界**，而不是散落在每个调用方里。未来新增调用步骤
也无法绕过统一计数。

## 8. 公开结果为什么只存摘要

真实运行会在系统临时目录生成 Harness Artifact，退出后自动清理。Git 仓库只保存严格
的 `DomainSkillSliceReport`：调用数、Token、延迟、终态、工具/证据计数、模型名、
finish reason、代码/fixture/结果哈希和安全错误码。

不会保存 API Key、完整 Prompt、模型原文、Tool Observation、知识正文、原始 request
ID、原始异常或完整 Coach 报告。这既降低隐私和密钥风险，也防止公开实验结果变成玩家
原始数据仓库。

CLI 还会拒绝覆盖已经存在的领域结果。要重新实验必须先明确处理旧证据，而不能无意中
重复付费并覆盖审计链。它也会拒绝脏工作树：只有所有执行代码已经提交时，结果记录的
`code_sha` 才能真实对应 GitHub 上通过 CI 的那一版，而不是用旧 HEAD 冒充未提交代码。

## 9. 测试分别证明了什么

- 聚焦合同测试证明历史证据、累计预算、脱敏报告和 CLI 安全门；
- Fake Provider 纵向测试真实走过 Catalog、Router、Context、AgentLoop、本地 RAG、
  ReviewHarness 和 typed output；
- 失败测试覆盖不调用知识工具、Evaluation 非法、一次格式修复、Provider 限流不自动
  重试，以及 revision 后再评测被预算阻断；
- 比例回归证明相邻 Agent/Skill/Harness/RAG/Provider 合同未回归；
- 全量 pytest、两套 RAG 门禁、compileall、敏感文件检查和 Harness dry-run 证明仓库
  其他能力仍然可运行。

这些测试使用 Fake Provider，因此证明的是**控制流正确与边界可靠**，不证明 GLM 在
真实近期复盘上的报告质量。

## 10. 当前能说和不能说什么

可以准确表述：

> 我实现了一个有累计调用预算和证据链的真实 Provider 领域准入控制器。它复用既有
> Skill、AgentLoop、本地 RAG 与唯一 ReviewHarness，在 Provider 出网前统一限制 Agent
> 和 Evaluation 的调用，并只持久化脱敏、可复读的 typed report。

> 实际准入结果是分层的：Zhipu Adapter 的最小 structured/tool 协议通过，但真实
> recent-form 领域运行没有形成统一响应、工具证据或 Evaluation，所以领域能力被拒绝；
> Harness 只返回确定性报告，证明 fail-closed 发布边界有效。

暂时不能表述：

- GLM 已通过 recent-form 领域准入；
- GLM 报告质量已经通过端到端评测；
- GLM 是最终模型赢家；
- 5D 或整个阶段 5 已完成；
- 当前工作流是 Multi-Agent、LangGraph 或第三方 Agent SDK；
- Fake Provider、单个真实样例或小型 RAG holdout 已证明生产泛化能力。

## 11. 为什么 5D-6b 可以结束，以及 5D-7 做什么

准入门的任务不是保证候选一定通过，而是依据冻结合同给出接受或拒绝。真实领域运行已经
按预算执行一次并原样保存；它在一个领域 call 后失败，没有重试，也没有为了追求绿色
结果临场调 Prompt。ADR-0012 因此可以用“协议准入、领域不准入”收尾 5D-6b。

`5D-7` 不会马上盲目改 Prompt 或同时接入多家模型。它先把这次“请求已计费、统一响应
缺失、上层错误分类被压缩”的 Bad Case 变成失败分类和可观测性合同，再建立多案例
数据集，系统评测 Prompt、Context、工具选择、事实/引用、注入、质量、延迟与成本。
只有同任务评测冻结后，才判断是调整 Prompt/Adapter，还是用新 ADR 比较一个第二
Provider。
