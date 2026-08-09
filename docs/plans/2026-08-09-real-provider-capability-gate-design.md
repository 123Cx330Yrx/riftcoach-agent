# 5D-6b Real Provider Capability Gate 设计草案

> 状态：待用户确认。本文只冻结实验设计，不调用真实 Provider，不选择第二厂商，
> 不完成 5D-7 Prompt/Context & Domain E2E Evaluation。

## 1. 当前问题

5D-6a 已经建立了 Provider-neutral 结构化响应合同、能力协商、严格 Pydantic 校验、
一次修复和 Harness fail-closed 边界。但现有 `ZhipuProvider` 只会：

- 发送普通 system/user 文本消息；
- 读取普通文本回答；
- 规范化 model、finish reason、usage 和 request ID。

它还不会发送工具定义、恢复 assistant tool call、发送 tool observation、解析返回的
tool calls，也不会映射结构化输出模式。因此 Fake Provider 测试只能证明 RiftCoach
内部合同成立，不能证明 GLM 的真实 API 能跑通这些合同。

5D-6b 的目标是建立一个“准入门”，回答三个问题：

1. 当前配置的 GLM 是否真的能完成 JSON 模式和 Function Calling；
2. RiftCoach Adapter 是否能把厂商请求/响应无损映射到内部合同；
3. 若 GLM 出现真实阻断，是否有足够证据比较最多一个第二 Provider。

## 2. 功能与非功能要求

### 2.1 功能要求

- 验证普通文本调用，作为网络、认证和基础响应基线；
- 验证两种真实 Evaluation JSON，覆盖空 issues 与嵌套 issue；
- 验证单个 `knowledge.search` 风格函数调用；
- 验证 assistant tool call → tool observation → final response 完整协议；
- 在低层能力通过后，运行一个固定的 `recent-form-review` 最小领域切片；
- 记录是否发生结构化 repair、工具调用、Harness 降级或拒绝；
- 用同一证据决定是否需要第二 Provider 对照，不自动实现第二家。

### 2.2 非功能要求

- 安全：API Key 只从环境读取，不输出、落盘或进入异常；
- 成本：真实外部调用有硬上限，前一层失败时停止后续花费；
- 可重复：冻结代码 SHA、Provider ID、请求模型、实际返回模型和案例版本；
- 可观察：记录延迟、Token Usage、finish reason、repair 次数和安全错误码；
- 可靠：任何非法参数、非法 JSON、坏 ToolCall 或不支持模式都 fail closed；
- 可维护：继续使用当前 OpenAI-compatible Client，不为一次实验引入第二套 SDK；
- 诚实边界：小型准入实验只证明协议可用，不证明生产质量、SLA 或自然语言泛化。

## 3. 比较过的三种方案

### 方案 A：根据官方文档直接打开 capability flags

改动最少，但文档声明不能证明当前账号、模型、端点、SDK 和 Adapter 组合真实可用。
它还会让生产路径在没有实测证据时接受结构化或工具请求，因此拒绝。

### 方案 B：先改完整生产 Adapter，再直接跑整个 Skill/Harness

能快速看到报告，但一旦失败，很难区分认证、JSON 模式、ToolCall 映射、RAG、Prompt、
Evaluator 或 Harness 哪层出错；同时会先消耗较多调用，因此拒绝。

### 方案 C：两层准入，低层失败即停止（采用）

```text
官方文档与无密钥配置预检
→ A. 原始 API 能力微探针（最多 5 次外部调用）
→ B. Zhipu Adapter 离线映射测试
→ C. 同一 Adapter 的最小真实领域切片（最多 7 次外部调用）
→ 结构化准入结果
→ 是否触发第二 Provider 比较
```

该方案把“厂商 API 能力”“本地 Adapter 正确性”和“RiftCoach 组合可运行”分开，
失败可以准确归因，最坏外部调用总数不超过 12 次。

## 4. 官方能力边界

截至 2026-08-09，智谱官方文档说明：

- GLM-5.2 支持 Function Calling；
- 工具通过 `tools` 传入，返回参数是 JSON 字符串；
- assistant tool call 与 `role=tool` observation 需要回传后再取得最终回答；
- `tool_choice` 公开文档只列出 `auto`；
- 结构化输出是 `response_format={"type":"json_object"}`；
- JSON Schema 示例仍把 Schema 放进 Prompt，并由客户端验证。

因此 RiftCoach 的准确映射是：

```text
StructuredResponseContract
→ Zhipu json_object mode
→ 模型返回 JSON 文本
→ 5D-6a 本地严格 Pydantic validation
→ accepted / one repair / fail closed
```

这叫“端到端结构化输出准入”，但不能称为“厂商原生 strict JSON Schema”。

官方资料：

- https://docs.bigmodel.cn/cn/guide/capabilities/function-calling
- https://docs.bigmodel.cn/cn/guide/capabilities/struct-output
- https://docs.bigmodel.cn/api-reference/模型-api/对话补全

## 5. 第一层：真实 API 微探针

微探针使用当前 GLM 配置，但与业务 Harness 隔离。它不调用 Riot API，不修改知识库，
也不执行任何有副作用的工具。

| Case | 外部调用 | 证明什么 | 成功条件 |
|---|---:|---|---|
| P1 Text baseline | 1 | 认证、端点、模型和文本响应 | 非空文本、可归一化 model/usage/finish reason |
| P2 Structured pass | 1 | 空 issues 的 Evaluation JSON | 首次响应通过严格 Pydantic 校验 |
| P3 Structured issue | 1 | 嵌套 issue、枚举和严格字段 | 首次响应通过同一严格 Pydantic 校验 |
| P4 Tool request | 1 | 返回一个函数调用 | 唯一 ID/name，arguments 是合法 JSON object |
| P5 Tool final | 1 | Tool Observation 多轮协议 | 回传固定安全 observation 后返回非空 final text |

微探针不自动 repair，也不自动重试，从而保留一手能力结果。任何 mandatory case 失败，
本轮 GLM 暂不准入对应 capability，并停止进入真实领域切片。

P4/P5 只提供一个只读函数 Schema，函数名和参数形状与 `knowledge.search` 对齐；P5
回传固定本地 fixture，不访问网络。它证明 Function Calling 协议，不评测 RAG 质量。

## 6. 第二层：Adapter 离线合同

第一层通过后才修改生产 `ZhipuProvider`。先用 Fake SDK 写红灯再实现：

- system/user/assistant/tool 四种消息映射；
- ToolSpec → Zhipu function tool；
- `AUTO` 映射为 `tool_choice="auto"`；
- `NONE` 不发送工具；
- `REQUIRED` 因官方未声明支持而明确拒绝，不能静默降为 AUTO；
- assistant `content=None + tool_calls` 合法归一化；
- arguments 必须解析为 JSON object，非 JSON、array、重复 ID、空名称都拒绝；
- response contract 映射为 `json_object`；
- 普通文本路径保持现有行为和错误脱敏；
- `parallel_tool_calls` 继续为 false，未经独立实测不得宣称支持。

只有离线映射测试全部通过后，Adapter 才能临时声明 `tool_calling=True` 和
`structured_output=True` 进入同一 Adapter 的真实领域切片。若真实切片失败，提交前
恢复相应 flag 为 false，并记录拒绝证据，不能把“代码能序列化”当成准入。

## 7. 第三层：最小 RiftCoach 领域切片

领域切片使用一个固定、匿名化、版本化的 `recent-form-review` fixture：

```text
Catalog + deterministic Router
→ SkillExecutionBoundary
→ ContextBuilder
→ AgentRunCompiler
→ real GLM AgentLoop
→ real local knowledge.search
→ CoachDraft + KnowledgeEvidence
→ ReviewHarness
→ real GLM structured Evaluation
→ typed terminal Skill Output
```

它最多允许 7 次外部模型调用：Agent 两轮、首次 Evaluation、一次结构化 repair、一次
Coach revision、修订后 Evaluation 和一次修订后结构化 repair。达到上限即 fail closed。

本层的 capability 成功条件是：

- Provider 调用和 ToolCall 映射没有协议错误；
- 至少一次真实 `knowledge.search` 被调用且 Observation 成功回传；
- Evaluation 最终得到严格合法的机器控制数据；
- Harness 到达合法 terminal state，并从 Artifact 构造 typed output；
- 草稿是否达到 85 分、是否修订、最终 published/degraded/rejected 原样记录。

报告质量分不在 5D-6b 被调 Prompt 或用来宣称模型优劣；那属于 5D-7。若协议全部
成功但报告因质量门禁降级，GLM 可以通过“能力准入”，同时把质量 Bad Case 留给 5D-7。

## 8. 结果记录

每个真实 case 记录一个脱敏结果：

```json
{
  "case_id": "P4_tool_request",
  "provider_id": "zhipu",
  "requested_model": "glm-5.2",
  "resolved_model": "...",
  "code_sha": "...",
  "success": true,
  "error_code": null,
  "latency_ms": 1234,
  "input_tokens": 100,
  "output_tokens": 20,
  "finish_reason": "tool_calls",
  "tool_call_count": 1,
  "repair_count": 0
}
```

不公开保存 API Key、完整原始 Prompt、未经审查的模型原文或原始异常。公开结果保存
案例版本、合同版本、摘要指标和输出 SHA-256；必要的调试原文只放本地忽略目录。

费用不能从 Token 数猜测。实验时另行记录官方价格页 URL、抓取时间和单位价格；若无法
取得可靠按量价格，`estimated_cost` 保持 null 并写明原因，不能填 0。

## 9. 第二 Provider 决策门

GLM 通过所有 mandatory capability 和领域切片协议后，5D-6b 不比较第二 Provider。
Provider Registry 已证明架构可扩展，多接一家不会自动增加业务价值。

只有以下任一真实阻断出现，才开启“最多一个候选”的新对照：

1. 官方支持但当前 GLM 无法稳定返回合法 ToolCall；
2. JSON mode 无法通过两个 mandatory Evaluation Schema case；
3. Tool Observation 无法继续得到 final response；
4. 同一 Adapter 领域切片出现可复现 Provider 协议错误；
5. 有可靠价格/延迟记录证明 GLM 超出随后明确批准的预算边界。

触发后也不立即选 Qwen、DeepSeek 或 Kimi。先按官方文档、OpenAI-compatible 适配成本、
结构化输出、Tool Calling、可用凭据和价格快照筛选一个候选，再运行完全相同的 P1-P5
与同一领域 fixture。最终采用、局部采用或拒绝必须写新 ADR。

## 10. 测试、停止边界与当前不能声称

实现阶段需要：

- Adapter 映射与坏响应单元测试；
- capability negotiation 回归；
- 无密钥时跳过真实 probe 的测试；
- 外部调用预算和前层失败停止测试；
- 脱敏结果 Schema 测试；
- 一个显式命令运行真实 probe，默认 pytest/CI 不消耗额度；
- 聚焦回归、完整 pytest、compileall、diff check、治理和公开 CI。

设计确认后，下一轮才编写实验与 Adapter。真实调用仍需用户明确授权。5D-6b 完成前
不能声称：GLM 已支持 RiftCoach Tool Calling、GLM 已通过结构化输出准入、第二 Provider
已选定、Prompt E2E 已完成、AgentRuntime V1 已完成，或项目已经是 Multi-Agent。
