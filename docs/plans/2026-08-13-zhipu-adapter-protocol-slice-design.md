# 5D-6b Zhipu Adapter Protocol Slice 设计

## 1. 当前缺口

P1-P5 已证明当前 GLM 接口具备基础 JSON mode 与 Function Calling 能力，生产
`ZhipuProvider` 的离线测试也已证明协议映射规则正确。但这两份证据之间仍有一条缝：
尚未用生产 Adapter 和生产 `AgentLoop` 完成一次真实往返。

本切片只回答：

1. Provider-neutral 结构化请求能否经生产 Adapter 返回并通过本地严格校验；
2. 生产 `AgentLoop` 能否经同一 Adapter 调用一个固定只读工具并继续生成最终回答；
3. 实验是否在任何失败下停止，并且公开结果不保存原始 Prompt、模型原文或异常。

它不评价报告质量，不运行领域 Skill，不选择第二 Provider，也不进入 5D-7。

## 2. 采用的组合方式

```text
ExternalCallBudget(max_calls=3)
        │
        ▼
BudgetedProvider ───────────────┐
        │                       │
        ├─ structured request   │ 1 call
        │                       │
        └─ existing AgentLoop ──┤ 2 calls
                  │             │
                  ▼             │
          fixed knowledge.search
          local read-only fixture
```

预算放在 `LLMProvider.chat()` 外层，而不是放在脚本或 SDK 响应之后。这样第 4 次调用会在
进入底层 Provider 前被拒绝。真实 CLI 同时关闭 SDK 自动重试，使一次预算消耗对应一次
真实 HTTP 尝试。

不扩展 raw 微探针，因为那会绕过生产 Adapter；不另写两轮 Function Calling 循环，因为
那会复制 `AgentLoop`。本切片只组合已有生产组件。

## 3. 两个顺序 Case

### A1 `structured_contract`

- 构造带 `EvaluationResponseModel` 合同的 Provider-neutral `ChatRequest`；
- 通过被计数的生产 Provider 发出一次请求；
- 使用 5D-6a 的 `decode_structured_response()` 严格校验；
- 不做 repair，不做重试；
- 失败后 A2 直接 skipped。

### A2 `agent_tool_round_trip`

- 只注册固定、幂等、无缓存、最多一次执行的 `knowledge.search`；
- 运行现有 `AgentLoop(max_iterations=2, max_tool_calls=1)`；
- 第一轮必须得到一个内部名为 `knowledge.search` 的 ToolCall；
- `ToolRuntime` 校验参数并返回本地 fixture；
- 第二轮必须得到固定终止标记；
- 工具未调用、调用失败、多调、少调或终止标记不匹配均不准入。

## 4. 调用预算

本协议切片使用精确三次预算：

| Case | 最大调用数 | 成功时调用数 |
|---|---:|---:|
| A1 structured | 1 | 1 |
| A2 AgentLoop round trip | 2 | 2 |
| 合计 | 3 | 3 |

此前设计中的“最多 7 次”属于后续完整领域切片预算，不在本轮借用。真实领域切片是否以及
如何运行，必须在本协议切片留下证据后再单独推进。

## 5. 公开结果合同

公开 JSON 只允许保存：

- Provider、请求模型、代码 SHA、时间和调用预算；
- case 状态、安全错误码、延迟、Token、响应数、ToolCall/工具执行数；
- resolved model、finish reason；
- request ID、合格输出、工具参数和工具结果的 SHA-256。

禁止保存 API Key、完整 Prompt、模型原文、工具 observation 原文、原始 request ID 和原始
异常。失败 case 不保存输出摘要；skipped case 不得伪造调用指标。

## 6. 失败控制流

```text
A1 failure ──> A2 skipped ──> admitted=false
A1 pass + A2 failure ───────> admitted=false
A1 pass + A2 pass + calls=3 -> admitted=true
budget exhausted ───────────> fail closed before outbound call
```

`admitted=true` 只代表生产 Adapter 协议切片可运行，不代表 GLM 报告质量优秀，也不代表
GLM 已被永久选为唯一模型。

## 7. 离线与真实执行分离

pytest 使用 Scripted Provider 或 Fake SDK，永不访问真实模型。CLI 必须同时满足显式
`adapter_protocol` scope、`--confirm-real-call` 和精确 `--max-calls 3` 才能出网。本检查点
先完成离线 TDD；真实执行及结果落盘是紧随其后的独立动作。
