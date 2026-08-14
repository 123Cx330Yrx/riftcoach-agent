# 5D-7 Batch D D4：第二 Provider 候选采用门设计

> 2026-08-14 决策更正：ADR-0018 已取代 ADR-0017 的候选模型与金额停止线。
> 本设计下文已按唯一候选 `deepseek-v4-pro` 和 DeepSeek `$0.10` 停止线同步；独立
> Adapter、同任务比较、调用/Token 上限、停止规则及“候选不等于准入”边界不变。
>
> 2026-08-14 后续归属修正：ADR-0019 保持当前 Pro-only 门不变，并把未来 Flash/Pro
> 分层从 5F 移出；该横向 Provider 优化最早在 5P 后、默认于阶段 6 依据真实产品证据
> 重开。5F 继续只负责 Pi / Claude Agent SDK Runtime 采用实验。

## 1. 这一步到底在解决什么

5D-6b 已经证明两件不同的事：

1. `ZhipuProvider` 能通过最小结构化输出和工具往返协议；
2. GLM-5.2 在一次真实近期复盘领域运行中没有形成可交给 Agent 的规范响应，系统最终安全
   降级，但无法从公开证据精确判断失败发生在哪一层。

因此下一步不能直接“换个新模型再试”。如果候选模型、Prompt、数据、预算和失败处理同时
变化，即使结果变好，也无法知道是模型更好、Adapter 更宽松、测试更容易，还是错误被吞掉。

D4 的目标是先冻结一把尺子：谁可以进入实验、两边怎样做同一任务、最多调用多少次、最多
花多少钱、哪种失败必须立即停止。D4 本身不实现第二 Provider，也不发出真实请求。

## 2. 初学者需要先分清的三个概念

### 2.1 Provider

Provider 是 RiftCoach 与一家模型服务商之间的适配边界。它负责把统一的
`ChatRequest` 翻译成厂商请求，再把厂商响应翻译回统一的 `ChatResponse`。

```text
RiftCoach Agent
      |
      v
LLMProvider 统一合同
      |
      +-- ZhipuProvider ------> GLM-5.2 API
      |
      `-- DeepSeekProvider ---> deepseek-v4-pro API（候选，尚未实现）
```

“兼容 OpenAI API”只表示请求外形相似，不表示 thinking、工具名、JSON、错误码和结束原因
完全相同，所以不能只改 `base_url`。

### 2.2 Model

Model 是 Provider 下的具体模型 ID，例如 `glm-5.2` 或 `deepseek-v4-pro`。本次是在
Provider Registry 内为同一个评测任务显式选择模型，不是先做一个给网页用户随意切换模型
的产品开关。

### 2.3 这不是 Multi-Agent

两个 Provider 分别跑同一批测试，仍然是一个 Agent 控制流的 A/B 准入实验。只有多个具有
独立职责、上下文、工具权限和协作协议的 Agent 共同完成任务，才属于 Multi-Agent。

## 3. 已有架构接缝

当前已有的厂商中立部分：

- `LLMProvider` 协议；
- `ChatRequest`、`ChatResponse`、`ToolCall` 和 `TokenUsage`；
- text / tools / structured output 能力声明与调用前协商；
- 显式 `ProviderRegistry`，不做隐式自动路由；
- 类型化、安全的 Provider 错误。

当前仍是厂商特定的部分：

- thinking 的开关和参数；
- 内部工具名到厂商合法函数名的可逆映射；
- 并行工具调用、structured + tools 同轮组合的支持边界；
- `finish_reason`、usage、空 content 和 reasoning 的规范化；
- HTTP/SDK 异常到安全错误码的映射。

第二 Adapter 必须单独实现这些差异。只有两个 Adapter 出现经测试证明相同的纯逻辑后，
才考虑抽取共享 helper；不能先造一个“万能 OpenAI-compatible Adapter”掩盖差异。

## 4. 候选方案比较

### 方案 A：暂时不增加第二 Provider

优点是零新增复杂度和费用。缺点是 5D-6b 已出现真实领域 Bad Case，我们无法验证统一
Provider 合同是否真的可移植，也无法区分 GLM 特有问题与 RiftCoach 公共控制流问题。

结论：不选。现在已有冻结合同、离线基线和独立 held-out，满足受控比较的前提。

### 方案 B：DeepSeek V4 Pro 作为唯一候选

官方直接 API 当前提供：

- 正式模型 ID `deepseek-v4-pro`；
- OpenAI Chat Completions 格式；
- 可显式关闭 thinking；
- JSON output 与 Tool Calls；
- 公开、可快照的按 Token 价格；
- 与仓库现有 `openai>=2,<3` 依赖兼容。

它可以在不引入新 SDK、不扩展 reasoning 消息合同的前提下同时测试 Provider 可移植性，
并让唯一候选代表 D5 真正要验收的复杂领域 Agent 能力。官方 2026-08-13 GA 资料显示，
Pro 在多项生产 Agent 基准上高于 Flash。

结论：选为 D5 唯一候选。候选不等于已接入、已准入或默认生产模型。

### 方案 C：Qwen3.8 Max 作为首次候选

Qwen3.8 Max 已是正式 `qwen3.8-max`，支持混合思考、Function Calling 和结构化输出；
它不是因为能力不足而被排除。

本轮暂缓的原因是控制变量较差：

- 开启 thinking 的工具回合涉及 `reasoning_content` 持久回传，而当前统一消息合同没有该
  字段；虽可关闭 thinking 避开，但这仍是后续需要明确建模的 Provider 语义；
- Token Plan 以动态 Credits 计费，且个人版明确禁止用于自定义应用后端 API；
- 截至本设计日期，官方标准价格页尚未提供足以冻结的 `qwen3.8-max` 按量价格行。

结论：不作为第一次候选。待标准后端 API 计费、reasoning 传递策略和独立 Bad Case 清晰
后再开新 ADR，不作模型质量排名。

### 同系列的 V4 Flash

`deepseek-v4-flash` 具备相同的首轮协议能力，速度更快、价格更低，适合只做 Adapter
smoke test 或未来简单任务的成本/时延分层。但 D5 还包含唯一候选的领域 held-out，不能
只按协议成本选模型。按 ADR-0019，若 5P 后、通常在阶段 6 出现明确的成本或时延 Bad
Case，再通过独立横向 Provider 优化门评估 Flash；该工作不属于 5F。

## 5. 三层准入，不把一个绿灯夸成全部能力

```text
协议准入
  结构化 JSON + 一次工具往返
       |
       v
领域准入
  同一 Skill / Context / RAG / Harness / held-out
       |
       v
产品采用
  更多数据、稳定性、成本和部署证据（本轮不做）
```

- 协议准入通过：只能说明 Adapter 能正确说“RiftCoach 的协议语言”；
- 领域准入通过：只能说明它在 3 个冻结小样本上满足准入门；
- 两者都不等于模型排行、统计显著性或生产默认模型。

## 6. D5 必须保持不变的比较条件

两边必须使用：

- 同一 `recent-form-review@0.2.0`；
- 同一 `context-builder-v1`；
- 同一 `coach_evaluation@1.1.0`；
- 同一 Prompt/Context snapshot
  `recent-form-prompt-context-v1-1@23e95a1b1ddaee408190d6a3842aefd329049fd7c4abade4578988c365e74561`；
- 同一 3 场 `domain-e2e-v1-1-secure-held-out`，顺序固定为正常控制、用户注入、检索
  证据注入；
- 同一真实本地 RAG、AgentLoop、ToolRuntime、ReviewHarness 和 typed output；
- `max_revisions=0`，只允许合同内最多一次 Evaluation JSON repair；
- SDK 自动 retry 为 0，Tool retry 为 0；
- 每个 Provider 独立运行，单次运行中不自动 fallback 到另一 Provider。

GLM 使用已准入的 Zhipu Adapter 协议证据，不重跑 5D-6b 的单样例；DeepSeek 必须先通过
自己的 Adapter protocol gate 才能看到 held-out。

## 7. D5 数据流与控制流

```text
离线配置、能力和预算预检
        |
        v
DeepSeek Adapter protocol：最多 3 calls
        |
        +-- fail --> 记录安全分类，候选停止，不运行 held-out
        |
        v
冻结身份复算 + held-out 显式确认
        |
        v
GLM-5.2 / DeepSeek V4 Pro 分别运行同一案例
        |
        v
Provider -> Agent -> knowledge.search -> Agent
        |
        v
Evaluation 1.1 -> blocking policy -> terminal output
        |
        v
分层结果：Provider / Tool / Evidence / Evaluation / Terminal / Resource
```

任何模型文本都不能直接成为证据或发布结果。Evidence 仍只来自成功的真实 ToolExecution，
ReviewHarness 仍是唯一发布权威。

## 8. 能力前置条件

### 8.1 调用前配置门

在任何网络 I/O 前必须验证：

- Provider ID、模型 ID 和 base URL 是设计冻结值；
- API Key 只来自环境变量，不进入参数、日志、结果或 Git；
- `openai` SDK retry 固定为 0；
- 非流式、non-thinking；
- parallel tool calls 不允许；
- structured output 与 tools 不在同一请求中组合；
- 当前 Git 工作树干净，代码 SHA 已由公开 CI 精确验证；
- Dataset、Prompt/Context snapshot 和评测版本逐项匹配。

### 8.2 DeepSeek Adapter protocol

精确复用现有两类协议案例：

1. 一次结构化 Evaluation JSON，最多 1 call；
2. `knowledge.search` ToolCall -> 本地工具执行 -> 最终标记，最多 2 calls。

必须满足：

- 结构化响应通过同一 Pydantic 严格校验；
- 内部 `knowledge.search` 通过请求级可逆别名映射，不污染 Manifest；
- 只允许一次 ToolCall 和一次成功工具执行；
- thinking 已关闭，若仍返回非空 reasoning，按响应合同失败；
- 空 JSON、非严格 JSON、未知工具别名、重复/并行 ToolCall、坏 usage 和未知 finish
  reason 均 fail closed；
- 任一协议案例失败，候选不进入 held-out。

## 9. 失败分类与安全归因

### 9.1 为什么需要分类

“报告失败”不能说明失败点。真实链路至少有 Provider、Agent、Tool、Evidence、Evaluation
和 Terminal 六层。D5 必须保存最接近根因的白名单分类，未知就写 unknown，不能伪装成 0
或成功。

### 9.2 白名单分类

入口与身份：

- `experiment_identity_mismatch`
- `dataset_not_frozen`
- `public_ci_sha_mismatch`
- `provider_configuration_invalid`

Provider / Adapter：

- `provider_authentication_failed`
- `provider_rate_limited`
- `provider_timeout`
- `provider_service_unavailable`
- `provider_request_rejected`
- `provider_capability_mismatch`
- `provider_response_invalid`
- `provider_usage_unavailable`
- `provider_error_unknown`

Agent / Tool / Evidence：

- `agent_provider_failed`
- `agent_control_flow_incomplete`
- `tool_round_trip_incomplete`
- `tool_execution_failed`
- `evidence_missing_or_invalid`

Evaluation / Terminal：

- `structured_evaluation_failed`
- `fact_or_citation_check_failed`
- `injection_resistance_failed`
- `terminal_status_mismatch`
- `unsafe_publication`

Resource：

- `external_call_budget_exhausted`
- `token_budget_exhausted`
- `cost_budget_exhausted`
- `latency_budget_exhausted`

公开结果只能保存这些安全码、计数、时延、Token、模型身份和 SHA-256。禁止保存 Prompt、
用户原文、模型正文、Tool Observation、canary、原始 request ID、SDK 异常、HTTP body 或 Key。

### 9.3 5D-6b 可观测性缺口是 D5 前置项

当前 `AgentLoop` 能保留安全 `error_code`，但草稿准备异常会让外层只看到笼统的执行失败。
D5 离线实现必须让 preparation boundary 暴露类型化、安全的 Agent failure observation，
至少包含 status、stop reason 和白名单 error code；不能通过恢复或记录原始 Provider 文本来
“增强可观测性”。这个前置项未通过，真实比较不得开始。

## 10. 调用、Token 与成本上限

### 10.1 调用上限

| 范围 | 上限 |
|---|---:|
| DeepSeek Adapter protocol | 3 calls |
| DeepSeek 3 场领域 held-out | 12 calls |
| DeepSeek 本轮累计 | 15 calls |
| GLM 3 场领域 held-out | 12 calls |
| 两个 Provider 全部最坏累计 | 27 calls |

每场领域最多 4 calls：Agent 首轮、Agent 工具结果轮、Evaluation，以及必要时一次
Evaluation JSON repair。Coach report revision 为 0。

### 10.2 Token 上限

- 每个领域案例沿用 Dataset 的 `maximum_total_tokens=4000`；
- 每个 Provider 三场领域累计最多 12000 observed tokens；
- DeepSeek protocol 累计最多 4000 observed tokens；
- 每次请求 `max_tokens` 不得高于 1024，结构化协议案例继续使用更小的 512；
- response usage 缺失时不能当作 0，立即分类为 `provider_usage_unavailable` 并停止该
  Provider。

### 10.3 价格快照与金额停止线

设计日期的官方无缓存价格：

- GLM-5.2：输入 ¥8 / 1M tokens，输出 ¥28 / 1M tokens；
- DeepSeek V4 Pro：为覆盖 2026-08-16 起价格变化，预检采用公告中的峰值价，输入
  $1.32 / 1M tokens、输出 $3.96 / 1M tokens，不使用缓存或低谷折扣。

本轮金额停止线：

- GLM 领域比较：估算累计不得超过 ¥0.50；
- DeepSeek 协议 + 领域比较：估算累计不得超过 $0.10。即使把 16000-token 总上限极端地
  全部按峰值输出价估算，约为 $0.06336，仍在该停止线内。

在每次 I/O 前，根据请求预算预留最坏输出成本；每次响应后根据官方 usage 重新结算。若
实际运行日前官方价格、模型 ID 或计费规则变化，必须先更新价格快照和 ADR 证据；若缺少
可靠 usage 或价格，停止而不是把成本写成 0。

金额上限是应用层停止线，不冒充厂商账户级硬限额。真正的硬边界来自调用计数、每请求
输出上限、Dataset 总 Token 门和零自动重试。

## 11. 停止规则

### 全局停止

以下任一情况停止整个实验，不再调用任何 Provider：

- Git/CI、Dataset、Prompt/Context snapshot 或 Evaluation 合同漂移；
- 预算控制器自身失效或可能在计数前发出网络请求；
- 发现密钥、Prompt、模型正文、攻击正文或原始异常将进入公开工件；
- 任一案例出现 `unsafe_publication`；
- 生产发布权不再由唯一 ReviewHarness 控制。

### 单 Provider 停止

以下情况停止该 Provider 的剩余案例：

- DeepSeek Adapter protocol 任一项失败；
- auth、模型不可用、usage 不可观测、调用/Token/金额上限触发；
- 当前案例的分层期望不满足，包括正常控制未发布、注入控制没有安全降级/拒绝并正确分类；
- terminal status 与冻结合同不符。

停止后保留已经发生的脱敏证据，不重跑、不调 Prompt、不更换模型 ID 追绿。

## 12. D5 的实施顺序

下面只是 5D-7 D5 内部执行顺序，不新增或重排主阶段：

1. 离线 TDD：实现 `DeepSeekProvider`、安全错误归因、调用/Token/成本控制器和 CLI 的
   no-I/O dry-run；
2. 本地完整回归、治理和安全扫描；
3. 提交并推送，等待 exact-SHA GitHub Actions 全部成功；
4. 在仍满足价格/模型/密钥/快照前置条件时，先执行最多 3-call 的 DeepSeek 协议门；
5. 协议通过后，才按固定顺序执行两个 Provider 的 3 场 held-out；
6. 结果只用于准入决定，不根据首次 held-out 调 Prompt；用新 ADR 接受、部分接受或拒绝。

下一次“继续”只授权第 1 项离线实现，不自动触发真实调用。

## 13. 测试怎样证明它不是纸面规则

D5 离线测试必须证明：

- 错误 base URL/model/retry/snapshot/CI SHA 在 I/O 前失败；
- 第 16 次 DeepSeek 或第 13 次 GLM 调用在底层 Provider 前被拒绝；
- 每次请求输出上限和累计 Token/金额 ledger 不能绕过；
- 缺失 usage 立即停止且不记为零成本；
- thinking 确实关闭，非空 reasoning 失败关闭；
- JSON、工具别名、单次工具调用和响应规范化严格；
- Agent Provider failure 的安全分类能穿过 draft preparation boundary；
- 公开 Candidate/Result 不含敏感字段或攻击原文；
- Fake/Scripted Provider 能完整模拟通过、协议失败、领域失败、预算失败和全局停止，外部
  调用始终为 0。

真实运行只能证明具体 Provider 在该日期、该模型、该代码 SHA 和三个冻结样例上的结果。

## 14. 非功能要求

### 安全

密钥只来自环境变量；不记录原始响应和攻击正文；任何 unsafe publication 全局停止。

### 可靠性

调用前能力协商、共享 pre-I/O 预算、零自动重试、类型化失败和确定性 fallback。

### 可复现性

代码 SHA、公开 CI、Dataset、Prompt/Context snapshot、模型 ID、价格快照和结果 digest
全部绑定。

### 可维护性

厂商差异留在独立 Adapter；统一 Agent、Skill、Tool、Harness 和 Evaluation 不分叉。

### 成本

小型准入实验，不做大规模基准；调用、Token、金额三重上限，缺失 usage 即停止。

## 15. 本设计明确不做什么

- 不调用 GLM、DeepSeek 或 Qwen；
- 不检查或保存任何真实 API Key；
- 不运行 held-out；
- 不修改 Prompt 追求更高分；
- 不做网页模型切换器或自动模型路由；
- 不引入 LangGraph、Pi/Claude Agent SDK、Multi-Agent、MCP、Memory 或前端；
- 不宣布 GLM、DeepSeek 或 Qwen 谁“最好”；
- 不完成 5D-7、5D exit review 或进入 5E。

## 16. 官方资料快照

资料核验日期：2026-08-14。

- DeepSeek Models & Pricing：
  <https://api-docs.deepseek.com/quick_start/pricing/>
- DeepSeek Updates（V4 Pro GA 与 Agent 基准）：
  <https://api-docs.deepseek.com/updates/>
- DeepSeek V4 官方说明（Pro/Flash 定位）：
  <https://api-docs.deepseek.com/news/news260424/>
- DeepSeek Thinking Mode：
  <https://api-docs.deepseek.com/guides/thinking_mode/>
- 智谱产品价格：<https://bigmodel.cn/pricing>
- Qwen 深度思考：<https://help.aliyun.com/zh/model-studio/deep-thinking>
- Qwen Function Calling：
  <https://help.aliyun.com/zh/model-studio/qwen-function-calling>
- Qwen Structured Output：
  <https://help.aliyun.com/zh/model-studio/qwen-structured-output>
- Qwen Token Plan 个人版边界：
  <https://help.aliyun.com/zh/model-studio/token-plan-personal-overview>
