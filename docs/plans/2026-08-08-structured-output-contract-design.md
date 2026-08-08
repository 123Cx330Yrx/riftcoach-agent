# 5D-6a Structured Output Contract 设计

## 1. 当前问题

RiftCoach 已经有 Provider-neutral `ChatRequest`、Provider 能力协商和 Harness
`EvaluationResult`，但这三层尚未真正连通。当前评测路径仍然要求模型“只输出
JSON”，然后用 `json.loads` 加少量手写判断解析。这个做法存在四个缺口：

1. Provider 请求不知道调用方需要结构化输出，能力协商不会要求
   `STRUCTURED_OUTPUT`；
2. 手写 parser 没有完整拒绝额外字段、嵌套字段类型错误和不完整 issue；
3. 非 JSON、截断或 Schema 错误没有统一、有限的修复合同；
4. 解析失败依赖各业务 parser，容易漂移。

5D-6a 只解决这些合同问题。它不调用真实 GLM，不映射任何厂商的
`response_format`，不选择第二 Provider，也不把 Markdown Coach 报告改成 JSON。

## 2. 采用方案

采用“请求声明 + 能力协商 + Adapter 严格验证 + 一次修复”的组合：

```text
Evaluation Pydantic Model
→ StructuredResponseContract(name/version/json_schema)
→ ChatRequest.response_contract
→ Provider Capability Negotiation
→ llm.chat Tool Adapter
→ ChatResponse
→ strict JSON + Pydantic validation
→ success
   or one bounded repair request with the same contract
→ strict validation again
→ success or fail closed
```

Provider 合同只携带 JSON Schema，不携带业务 Pydantic 类。厂商 Adapter 只需要理解
稳定 Schema，不反向依赖 Harness 或 Evaluation 模块。Pydantic 类留在业务 Adapter
侧，用于把返回 JSON 验证成机器可消费的领域控制数据。

## 3. Provider-neutral 合同

新增不可变 `StructuredResponseContract`：

- `name`：稳定、非空的合同名称；
- `version`：语义版本；
- `json_schema`：必须是 JSON object Schema；
- `strict`：V1 固定为严格模式。

`ChatRequest` 增加可选 `response_contract`。只要该字段存在，
`required_capabilities_for()` 就必须加入 `STRUCTURED_OUTPUT`。文本请求和普通
Tool Calling 请求保持原行为。当前 `ZhipuProvider` 仍只声明 `text_chat=True`，所以
结构化请求会在 SDK 调用前被明确拒绝；这正是 5D-6b 真实准入前应有的 fail-closed
行为。

## 4. 严格验证与一次修复

新增通用结构化响应验证器，输入为规范化 `ChatResponse`、目标 Pydantic Model 和
合同。验证顺序固定：

1. `finish_reason` 表示截断时拒绝；
2. 内容必须是单个合法 JSON object，不接受 Markdown fence 或前后解释文字；
3. 使用 `model_validate_json(..., strict=True)` 验证；
4. Pydantic Model 必须配置 `extra="forbid"`，拒绝未知字段；
5. 第一次失败时，只有显式提供 repair callback 才允许修复一次；
6. 修复结果必须重新经过完全相同的验证，不能正则抽取或填默认值猜测；
7. 第二次失败抛出安全 `ProviderResponseError`，不把原始模型输出放进异常字符串。

修复是一次新的模型调用，不是本地篡改。repair prompt 只要求把原结果转换为给定
Schema，不允许改变评测语义。调用次数由验证器硬限制为 1，调用方不能提高。

## 5. Evaluation 消费者

第一位消费者是决定 Harness 发布权的评测结果，而不是 Coach 报告。新增严格
Pydantic 模型：

- `EvaluationResponseModel`；
- `EvaluationIssueModel`；
- severity/category/verdict 使用枚举；
- score 为 0..100 的严格整数；
- `issues`、`passed_checks`、`summary` 类型完整；
- 所有层级拒绝额外字段。

`ChatEvaluationAdapter` 不再依赖可任意返回 dict 的 `response_parser`。它把模型的
Pydantic 结果显式转换为已有 `EvaluationResult`，因此 ReviewHarness、Artifact 和
terminal Skill Output 不需要重写。

## 6. Tool Runtime 接线

现有 `llm.chat` 继续是可靠调用入口。其输入允许可选的机器可读
`response_contract`，Handler 将其转换为 `ChatRequest.response_contract`；输出继续
返回规范化 content/model/provider/finish_reason/usage/request_id。

这一步不会声称 Tool Runtime 自己完成业务 Pydantic 验证。职责仍然是：Provider/Tool
层传递合同并做能力门禁；Evaluation Adapter 按业务模型做严格验证；Harness 决定降级、
拒绝或发布。

## 7. 失败与 Harness 行为

| 失败 | 行为 |
|---|---|
| Provider 不支持结构化输出 | SDK 调用前 `unsupported_capability` |
| 非 JSON / fence / 额外字段 / 缺字段 | 第一次进入一次 repair |
| `finish_reason=length` | 视为截断，进入一次 repair |
| repair 仍不合法 | 安全 `invalid_structured_output` |
| repair Tool/Provider 调用失败 | 保留安全 Tool 错误，Harness 降级或拒绝 |
| 合法响应 | 转换为现有 `EvaluationResult` |

Harness 的发布规则不变。结构化解析失败不能生成猜测分数或默认 `pass`。

## 8. 测试与面试边界

本检查点验证合同、能力门禁、合法/非法 JSON、嵌套字段、截断、一次修复和 Harness
降级/拒绝。完成后可以说“机器控制数据有 Provider-neutral 结构化输出合同、严格
Pydantic 校验和 fail-closed 边界”，但不能说 GLM 已实测原生结构化输出、第二 Provider
已接入或所有 Prompt 已通过真实模型 E2E。
