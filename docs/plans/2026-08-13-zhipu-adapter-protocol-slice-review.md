# 5D-6b Zhipu Adapter Protocol Slice 教学复核

## 1. 这一步真正验证了什么

此前 P1-P5 直接面向 OpenAI-compatible SDK，回答“当前 GLM 接口是否能返回 JSON、
ToolCall 和 Tool Observation 后的最终文本”。生产 `ZhipuProvider` 的 Fake SDK 测试又
回答“我们的协议翻译代码是否符合预期”。

本切片第一次把两部分接起来：

```text
RiftCoach 统一合同
→ 生产 ZhipuProvider
→ 真实 GLM API
→ 生产 ZhipuProvider 反向解码
→ 现有 AgentLoop / 严格 Pydantic decoder
```

因此这次通过意味着：最小生产 Adapter 的 structured output 与单工具多轮协议可以真实
运行。它仍不意味着近期复盘 Skill、Harness 报告质量或最终模型选型已经通过。

## 2. 三次调用分别做了什么

### Call 1：结构化响应

RiftCoach 构造 `ChatRequest(response_contract=...)`。同一份 Pydantic 模型同时产生 JSON
Schema，并被放入 Prompt；Zhipu Adapter 开启 `json_object` mode。返回文本再经过本地
严格 Pydantic 校验。

这里有两层职责：

- 厂商 JSON mode：提高返回合法 JSON object 的概率；
- RiftCoach decoder：决定字段、类型、枚举、范围和额外字段是否真正合格。

所以不能把 `json_object` 误称为厂商原生 strict JSON Schema。

### Call 2：模型提出工具调用

AgentLoop 把内部工具 `knowledge.search` 交给 Provider。智谱函数名不允许点号，Adapter
只在本次请求内把它翻译成 `knowledge_search`。模型返回 ToolCall 后，Adapter 再还原为
内部名称。

模型在这里没有执行函数，只产生：

```text
tool name + arguments + call id
```

### 本地工具执行：不消耗模型调用

AgentLoop 把 ToolCall 交给 `ToolRuntime`。Runtime 校验白名单和 JSON Schema，再运行
固定只读 fixture，生成 Tool Observation。这是本地 Python 调用，不是第 3 次模型调用。

### Call 3：模型读取 Observation 后结束

AgentLoop 把 assistant ToolCall 与 tool observation 一起放回消息历史。模型必须返回
精确终止标记，且不能再次请求工具。此时完整协议才成立：

```text
assistant ToolCall
→ local ToolRuntime
→ tool observation
→ assistant final response
```

## 3. 数据流与控制流的区别

数据流回答“什么内容在组件之间移动”：

```text
ChatRequest → 厂商 payload → ChatResponse → ToolCall
→ ToolResult → tool message → final ChatResponse
```

控制流回答“谁决定下一步”：

- `AdapterProtocolSliceRunner` 决定先 A1、后 A2，A1 失败则跳过 A2；
- `BudgetedProvider` 决定是否还允许出网；
- `AgentLoop` 决定调用工具还是结束；
- `ToolRuntime` 决定工具输入是否合法、执行是否成功；
- Pydantic report 决定证据是否自洽，最终是否 admitted。

模型只能提出 ToolCall，不能提升白名单、预算或发布权限。

## 4. 为什么需要 Provider 外层预算

`AgentLoop.max_iterations=2` 只约束 Agent 循环；它不知道前面还有一次 structured 直调。
因此本切片在统一 Provider 边界放置：

```text
ExternalCallBudget(max_calls=3)
```

每次 `provider.chat()` 都先扣预算。第 4 次会在进入真实 Provider 前被拒绝。SDK 同时
设置 `max_retries=0`，避免一次逻辑调用在底层变成多次 HTTP 尝试。

## 5. 为什么只使用固定只读工具

本切片要隔离验证 Function Calling 协议，不评价 RAG 召回质量。如果这里直接接复杂
RAG，一旦失败就很难判断是：

- Provider 没返回合法 ToolCall；
- Adapter 别名映射错误；
- ToolRuntime 合同错误；
- 还是检索内容/索引本身有问题。

固定只读工具让变量只剩协议本身。真实本地 RAG 已有独立评测，领域组合留给下一切片。

## 6. 真实结果

控制器先在提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51` 上通过 GitHub
Actions run `31625669630`，随后只执行一次真实实验：

| Case | Calls | Input/Output tokens | Latency | Result |
|---|---:|---:|---:|---|
| A1 structured contract | 1 | 427 / 59 | 2344 ms | passed |
| A2 AgentLoop tool round trip | 2 | 562 / 36 | 5360 ms | passed |
| 合计 | 3 / 3 | 989 / 95 | 7704 ms | admitted |

A2 两次响应的 finish reason 顺序是 `tool_calls → stop`；工具提议一次、实际执行一次。
没有可靠的官方单价快照，因此结果中的 estimated cost 保持 `null`，不能猜成 0。

## 7. 结果为何可以公开

落盘结果只保留：

- Provider、模型、代码 SHA、时间；
- 调用数、Token、延迟、finish reason；
- ToolCall/执行计数；
- request、输出、参数和工具结果的 SHA-256。

它不保留 API Key、完整 Prompt、模型正文、工具 observation、原始 request ID、思维链
或原始异常。哈希用于证明两次观察是否相同，不用于恢复原文。

## 8. 面试中的准确表述

可以说：

> 我为生产 Zhipu Adapter 建立了分层准入：先用隔离微探针验证 JSON mode 和 Function
> Calling，再用共享调用预算把严格 structured request、现有 AgentLoop、ToolRuntime
> 与只读工具组合为 3-call 协议切片。真实实验完成 ToolCall、Observation 回传和 final
> response，结果通过脱敏 Pydantic 合同落盘；任何前置失败都会停止后续调用。

暂时不能说：

- GLM 已经是所有候选中效果最好的模型；
- 真实近期复盘报告已经通过质量评测；
- 整个 5D 或 AgentRuntime 已完成；
- 项目已经是 Multi-Agent、LangGraph 或 Agent SDK 应用；
- 这次固定 fixture 验证了真实 RAG 召回质量。

## 9. 下一步

下一步仍在 5D-6b：设计并离线 TDD 化 `recent-form-review` 领域切片。它将复用真实
Catalog、Router、ExecutionBoundary、ContextBuilder、AgentLoop、真实本地 RAG、唯一
ReviewHarness 与 typed terminal output。

在任何真实领域调用前，必须先明确原设计的累计 7-call 上限如何扣除本切片已经使用的
3 calls，避免两个脚本各自宣称“有预算”却合计失控。
