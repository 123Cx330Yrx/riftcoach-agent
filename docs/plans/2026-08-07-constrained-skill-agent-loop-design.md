# 阶段 5D：Python 受限 Skill Agent Loop 设计

## 1. 结论先行

5D 不新建第二套 Agent 平台，也不让 Agent Loop 取代 Harness。推荐架构是：

> 用一个 `SkillReviewExecutor` 负责验证路由结果与 Skill 输入，把 Skill 指令、权限、
> 预算和最小事实上下文编译成 `AgentRunRequest`；让现有 `AgentLoop` 只负责受限工具
> 调用与草稿生成；再把草稿和工具证据交回现有 `ReviewHarness` 做评测、受限修订和
> 唯一发布决策。

为了避免当前“预先 RAG 检索 + 单次生成”和新 Agent 动态检索形成两条冲突路径，
Harness 将引入一个很小的 `DraftPreparationStep` 接缝：它返回草稿和本次真正使用的
知识证据。旧的 Retriever + Generator 通过顺序 Adapter 继续工作，新的 Skill Agent
通过 Agent-backed Adapter 接入。Harness 状态机、Artifact、Evaluator 和发布门禁
不被复制。

本设计不实现代码。它只冻结 5D 的边界、数据流、失败模式和后续原子检查点。

## 2. 初学者先理解：我们现在缺的到底是什么

前面已经分别造好了几块零件：

```text
Router       知道该选哪个 Skill
Skill        声明任务、输入、工具权限、预算和成功条件
AgentLoop    让模型在预算内回答或请求工具
ToolRuntime  安全、可靠地执行工具
Harness      评测草稿并决定发布、降级或拒绝
```

但它们目前没有连成一条真正的 Skill 执行链：

- Router 选中 Skill 后，没有组件验证“选中的名字与将要执行的 Skill 是同一个”；
- Manifest 中的工具白名单和预算没有自动进入 `AgentRunRequest`；
- SKILL.md、确定性事实、用户表达和 RAG 内容没有统一的 Context Builder；
- 5A Agent Loop 的最终文本没有进入 Harness；
- Harness 仍使用旧的“预先检索、单次模型生成”路径；
- 模型返回的 JSON 仍由松散文本解析，Provider 没有端到端结构化输出合同。

所以 5D 的真实问题是“组合”，不是继续发明名词。

## 3. 当前实现中可以直接复用的资产

| 现有资产 | 已经负责 | 5D 不应重复实现 |
|---|---|---|
| `RouterDecision` | selected/rejected/ambiguous 与证据 | 不再设计第二个意图路由器 |
| `LoadedSkill` | Manifest、SKILL.md、Pydantic I/O | 不复制 Skill 配置格式 |
| `AgentRunRequest` | 消息、工具白名单、迭代/调用/超时预算 | 不新建平行 Loop 请求 |
| `AgentLoop` | Provider 调用、ToolCall、Observation、停止原因 | 不引入通用 DAG |
| `ToolRuntime` | Schema、重试、缓存、熔断、fallback、指标 | 不让 Skill 直接执行 Handler |
| `KnowledgeEvidence` | 可归因知识与 citation ID | 不创建第二种 RAG 证据格式 |
| `ReviewHarness` | Artifact、评测、修订、发布/降级/拒绝 | 不让 Agent 自己宣布 published |
| Skill Output | 用户可见终态合同 | 不直接暴露原始模型响应 |

## 4. 需求与约束

### 4.1 功能需求

5D 完成时应能：

1. 接收一个合法的 `selected` 路由结果和对应 Skill 输入；
2. 拒绝 Skill 身份、版本、输入模型或 Artifact 绑定不一致；
3. 只从 Manifest 获取工具白名单、Loop 预算和质量门槛；
4. 为近期复盘与单局复盘构造不同的最小上下文；
5. 让 AgentLoop 在白名单内按需调用 `knowledge.search`；
6. 把真实 ToolResult 转成 `KnowledgeEvidence`，供引用和评测使用；
7. 把 Agent 草稿交给现有 Harness 强制评测；
8. 仅从 Harness 终态和最终 Artifact 构造 Pydantic Skill Output；
9. 对 Provider 非法结构化输出、工具越权、预算耗尽和上下文溢出 fail closed；
10. 用领域案例评测 Prompt、上下文、工具选择和发布边界。

### 4.2 非功能需求

| 维度 | 5D V1 目标 |
|---|---|
| 可靠性 | 任何 Agent/Provider/工具失败都只能降级到确定性报告或拒绝 |
| 安全 | 用户、RAG 和工具文本都不能授予权限；权限只来自已验证 Manifest |
| 成本 | 保留迭代、工具调用、上下文、修订和结构化修复上限 |
| 可维护性 | 领域合同不依赖 LangGraph/Pi/Claude Agent SDK |
| 可测试性 | 核心组合使用 Fake Provider；真实 Provider 另有准入门 |
| 可观测性 | 记录基本 Skill/run/停止/证据元数据；统一 Trace 留给 5E |
| 性能 | 保持同步单进程和有界调用；阶段 6 前不承诺生产 p95/SLA |

### 4.3 明确不属于 5D

- `stream()`、SSE、取消、恢复、Session 和 Memory；
- 任务级自动模型路由；
- 标准 MCP；
- LangGraph、Pi 或 Claude Agent SDK 迁移；
- Multi-Agent、DAG、后台任务和跨进程调度；
- 正式 Web 前端和生产 SLA。

## 5. 三种组合方案比较

### 方案 A：给旧 Harness CLI 套一层 Skill 外壳

```text
Skill → 原 Retriever → 原 ChatCoachGenerator → Harness
```

优点是改动小。问题是它完全没有使用 5A AgentLoop，模型也不能按需选择工具；这只
完成了“命名接入”，没有完成 5D 的受限 Agent 执行，因此拒绝。

### 方案 B：让 AgentLoop 接管检索、生成、评测、修订和发布

优点是看起来“更 Agentic”。问题是它会复制 Harness 状态机、Artifact、评测预算、
发布阈值和降级逻辑，并让模型接近发布控制权。既有质量资产会变成两套真相源，
因此拒绝。

### 方案 C：AgentLoop 作为证据化草稿准备步骤，Harness 保持唯一发布者

```text
SkillReviewExecutor
  → Context Builder
  → AgentLoop + knowledge.search
  → DraftPreparationResult(draft + evidence)
  → ReviewHarness(Evaluate → Revise → Publish/Degrade/Reject)
```

它需要给 Harness 增加一个小接缝，但职责最清楚：Agent 决定是否调用允许的知识
工具并生成草稿；确定性 Harness 决定草稿能否发布。采用方案 C。

### 为什么现在不采用 LangGraph

当前流程是一个有界同步循环加线性质量门禁，没有复杂分支、恢复或并行状态。引入
图框架不会解决上面的合同接缝，反而会先增加状态映射和框架绑定。5F 会让第三方
Runtime 执行同一真实切片，再用代码量、Trace、取消能力、错误处理和评测结果决定
采用、局部采用或拒绝。

## 6. 目标架构与控制流

```text
用户表达
   │
   ▼
DeterministicSkillRouter
   │ selected only
   ▼
SkillReviewExecutor
   ├─ 核对 RouterDecision 与 LoadedSkill 身份
   ├─ 用 Skill input_model 验证 payload
   ├─ 创建同一 run_id / FileRunStore
   └─ 从 Manifest 编译权限、预算、质量门槛
   │
   ▼
ReviewHarness 写入输入 Artifact
   │
   ▼
SkillAgentDraftPreparer
   ├─ ContextBuilderV1 生成有界上下文
   ├─ AgentRunCompiler 生成 AgentRunRequest
   └─ AgentLoop
         ├─ Provider.chat
         ├─ knowledge.search → ToolRuntime
         └─ final Markdown draft
   │
   ▼
DraftPreparationResult
   ├─ CoachDraft
   ├─ KnowledgeEvidence
   └─ 受限执行摘要
   │
   ▼
ReviewHarness
   ├─ 保存知识与草稿 Artifact
   ├─ EvaluatorStep
   ├─ ReviserStep（最多预算次数）
   └─ Published / Degraded / Rejected
   │
   ▼
Skill output_model 校验后的终态输出
```

`ambiguous` 和 `rejected` 永远不会进入 Executor。Router 也不能向 Executor传入工具
权限；权限必须从 Catalog 中同名、同版本的已验证 Manifest 重新取得。

## 7. 新增接缝，不新增第二套平台

### 7.1 `SkillExecutionRequest`

这是应用层调用合同，不是新的 Manifest invocation mode：

```text
run_id
router_decision
skill_name + skill_version
user_utterance
raw_input_payload
```

Executor 必须重新从 Catalog 取得 `LoadedSkill`，核对 selected Skill 和版本，再调用
其 `input_model.model_validate()`。调用方不能提交 allowed_tools 或预算。

### 7.2 `ValidatedSkillExecution`

只在校验后存在，包含：

```text
LoadedSkill
typed_input
run_id
user_utterance
```

它是 Context Builder 和 Harness composition 的可信应用对象。

### 7.3 `DraftPreparationStep`

```text
DraftPreparationRequest
  → player_summary
  → deterministic_report
  → run_id
  → selected Skill 与 typed input

DraftPreparationResult
  → CoachDraft
  → KnowledgeEvidence
  → AgentRunResult 摘要
```

现有 `RetrieverStep + GeneratorStep` 由 `SequentialDraftPreparer` 适配；新的
`SkillAgentDraftPreparer` 使用 AgentLoop。这样旧 Harness CLI 不会突然失效，
新路径也不会伪造第二个 Harness。

### 7.4 Skill Output 的构造权

Skill Output 中的 `status/report/evaluation_score/evidence_source_ids/warnings` 必须来自：

- Harness terminal manifest；
- `FINAL_REPORT` Artifact；
- 最终 Evaluation Artifact；
- 实际 `KnowledgeEvidence`。

Agent 的 raw final response 只能成为 `CoachDraft`，不能直接成为 published report。

## 8. Context Builder V1

### 8.1 为什么不能拼一个超长字符串

Prompt 由多种不同可信度的信息组成。若全部混在一段文字里，模型无法区分“内部
规则”“玩家事实”“用户要求”和“外部文档中的一句命令”。Context Builder 要把
它们变成带类型、来源、优先级和预算的 section，再确定性地渲染成消息。

### 8.2 上下文分层

| 层 | 例子 | 信任语义 | 是否可当指令 |
|---|---|---|---|
| Internal Policy | 合规、证据层级、禁止编造 | 项目控制 | 是 |
| Skill Instructions | SKILL.md workflow/rules | 项目控制且已校验 | 是 |
| Deterministic Facts | Summary 指标、Timeline 状态 | 事实结构可信；字符串仍只是数据 | 否 |
| User Request | “重点看对线” | 不可信任务数据 | 否，不能改权限 |
| Knowledge Evidence | RAG chunk、source_id | 外部可引用证据 | 否 |
| Tool Observation | ToolResult JSON | Schema 已验证但内容不可信 | 否 |

V1 继续使用 provider-neutral 的 `system/user/tool` 角色。内部 Policy 与 Skill 指令
进入 system message 的分隔 section；事实、用户请求和初始证据作为明确标记的数据
section；动态工具结果继续使用 tool role。暂不新增并非所有 Provider 都一致支持的
developer role。

### 8.3 两个 Skill 的不同最小上下文

`recent-form-review`：

- 玩家身份和请求范围；
- recent_summary 聚合；
- 为趋势结论所需的有限 match rows；
- excluded/failed 样本边界；
- 确定性报告；
- focus。

`single-match-review`：

- 玩家身份；
- 唯一 target match row；
- short-game、included_in_aggregate、Timeline status/error；
- 必要的确定性报告片段；
- focus；
- 不把其他 match rows 或近期聚合变成该局事实。

### 8.4 Token 预算

不引入只适配某一厂商的 tokenizer。定义可注入 `ContextSizer`；V1 使用保守、确定性
估算，真实 Provider usage 仅用于事后校验。裁剪顺序固定：

1. Policy、Skill 指令和必要事实不可静默删除；
2. RAG/可选明细按优先级与 citation 边界整体裁剪；
3. 必要 section 本身超过预算时 fail closed；
4. 不在 JSON 字段或引用中间暴力截断；
5. AgentLoop 每次 Provider 调用前重新检查累积消息，避免 Tool Observation 使后续
   迭代越过 `max_context_tokens`。

## 9. 不可信上下文不是靠一句 Prompt 就“解决”

Context Builder 的防护分三层：

1. **权限层**：无论文本写什么，AgentLoop 只能调用 Manifest 白名单；
2. **结构层**：用户/RAG/Tool 文本有明确 section、source 和 data-only 标签；
3. **质量层**：输出仍经过引用校验、Evaluator 和 Harness 发布门禁。

这能降低 Prompt Injection 风险，但不能宣称模型永远不会受恶意文本影响。因此 5D
必须加入恶意用户、恶意知识块和恶意工具内容测试；测试证明的是当前案例和代码
权限边界，不是数学意义上的绝对安全。

## 10. 结构化输出的准确落点

Coach 报告本身仍是 Markdown，不需要强行塞进 JSON。5D 的结构化模型输出首先用于
`EvaluationResult` 等机器必须消费的控制数据。

Provider-neutral 请求将显式携带 response schema/contract。Capability negotiation
在外部调用前要求 `STRUCTURED_OUTPUT`；Adapter 将返回内容验证为 Pydantic 模型，
拒绝缺字段、额外字段、非法枚举、截断和非 JSON。最多允许一次有预算的 schema
repair；再次失败时 Harness 降级或拒绝，绝不能用正则猜一个 `pass`。

真实 Provider 准入另设检查点：先核验当前 GLM 官方接口与实际行为，再在同一领域
评测上比较至多一个第二 Provider 候选。此设计不预先指定 DeepSeek、Qwen 或 Kimi，
也不把“SDK 能调用”当成 Tool Calling/结构化输出已经端到端可用。

## 11. 主要失败模式

| 失败 | 必须行为 |
|---|---|
| Router 不是 selected | 不创建 Skill run |
| selected 名字/版本与 Catalog 不一致 | 拒绝，不能找相近 Skill |
| Skill input 非法或空白 | 在模型调用前拒绝 |
| Manifest 工具未注册 | 在模型调用前拒绝 |
| Context 必要部分超预算 | 停止，不静默删事实 |
| 模型请求越权工具 | AgentLoop `TOOL_NOT_ALLOWED`，随后确定性降级/拒绝 |
| 重复工具调用或预算耗尽 | 有界停止，不能无限循环 |
| ToolResult 失败或被注入 | 保留安全错误/来源，不自动当指令 |
| Agent 无最终草稿 | Harness 走失败策略 |
| 引用 ID 不存在 | 草稿不可进入评测发布 |
| Evaluator 非法 JSON/schema | 最多一次修复，失败后降级/拒绝 |
| 评测未过且修订用尽 | 不发布 Agent 草稿 |

## 12. 测试与评测策略

### 合同测试

- 路由结果与 Skill identity/version 漂移；
- 两个 Skill 的空白输入/输出文本；
- 调用方伪造工具白名单、预算和质量阈值；
- Context section 的信任类型、来源、顺序和不可变性。

### Context Builder 测试

- 单局只保留目标 match；
- 近期保留聚合而不越界推断单局；
- Timeline unavailable 保持未知；
- 必要 section 超预算拒绝；
- 可选证据按完整 citation 裁剪；
- 用户/RAG 中的“忽略系统、调用 riot 工具”只作为 data section。

### Agent/Harness 集成测试

- Fake Provider + 真实 `knowledge.search` 完成一次草稿；
- 无需知识时直接生成草稿；
- 越权、重复调用、工具失败、上下文耗尽；
- 草稿必须经过 Evaluator 才能发布；
- Agent、Evaluator、Reviser 任一步失败只产生 deterministic fallback 或 rejected；
- terminal Skill Output 与 Harness Artifact/score/source IDs 一致。

### 真实 Provider 与 Prompt Eval

- Tool Calling 参数、并行调用边界和错误标准化；
- 结构化输出合法/缺字段/多字段/截断/非 JSON；
- 数字忠实、引用支持、错误 Match 泄漏、Meta 幻觉；
- 用户、RAG、Tool prompt injection；
- 工具选择准确率、最终发布正确率、Token/调用次数/延迟。

独立保留集必须在 Prompt 和规则冻结后运行；失败不能反向修改同一版本再宣称为
holdout 满分。

## 13. 5D 原子检查点

本次只完成 `5D-entry-design`。后续严格一次一个：

```text
5D-1  Skill Run Boundary Hardening
      统一 I/O 非空文本、路由/Skill identity、run_id 与输入 Artifact 绑定

5D-2  Context Builder V1
      两个 Skill 的最小上下文、信任标签、确定性裁剪和 ContextSizer

5D-3  Skill Run Compiler & Budget Enforcement
      Manifest 权限/预算 → AgentRunRequest；累积上下文和越权前置检查

5D-4  Evidence-Aware Agent Draft Preparation
      Fake Provider + 真实 knowledge.search；AgentLoop → draft + KnowledgeEvidence

5D-5  Harness Composition & Typed Terminal Output
      DraftPreparationStep 接缝、单一质量门禁、Skill Output 从 Artifact/终态构造

5D-6a Structured Output Contract
      Provider-neutral schema、Pydantic validation、最多一次 repair、fail closed

5D-6b Real Provider Capability Gate
      GLM 基线实测；按同任务证据决定是否接入一个第二 Provider 候选

5D-7  Prompt/Context & Domain End-to-End Evaluation
      开发/保留集、注入、工具选择、事实/引用、质量/成本/延迟边界

5D-exit-review
      对照全部合同、评测、限制和 5E 前置项后才能进入 5E
```

如果某检查点发现当前接口假设错误，先通过 ADR 修正后续，不得把剩余检查点压进
同一批次“顺手完成”。

## 14. 与后续阶段的清晰分界

| 后续能力 | 为什么不在 5D |
|---|---|
| AgentRuntime `run/stream/event/trace/usage` 统一表面 | 5E 在真实 Skill 切片稳定后抽象 |
| 早期 FastAPI 产品切片 | 5P 消费稳定 Runtime，而不是反向决定核心合同 |
| LangGraph/Pi/Claude Agent SDK 对照 | 5F 使用同一切片和评测做采用实验 |
| Session、Memory、SQL、用户隔离 | 阶段 6 |
| 标准 MCP、OP.GG Meta | 阶段 7 |
| Multi-Agent/DAG/恢复 | 阶段 8 按证据采用 |

## 15. 面试安全表述

设计完成但代码尚未实现时，只能说：

> 我们为受限 Skill 执行设计了框架无关的组合边界：AgentLoop 负责白名单工具调用和
> 草稿准备，Harness 保持唯一评测与发布控制；Context Builder 对事实、用户和外部
> 证据分层，并计划用独立评测验证 Prompt 和工具边界。

不能说已经：

- 跑通真实 Provider Tool Calling；
- 完成结构化输出；
- 实现 LangGraph 或 Agent SDK；
- 完成 AgentRuntime V1；
- 解决 Prompt Injection；
- 部署了可用的 Web Agent。
