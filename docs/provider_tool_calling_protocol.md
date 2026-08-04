# 3G-1：Tool Calling 消息协议

## 1. 这一小步解决什么问题

原有 Provider 契约只支持：

```text
ChatMessage(role, content)
→ ChatRequest
→ ChatResponse(content)
```

这足以生成报告，但无法表达模型请求工具。工具调用不是模型直接执行 Python 函数，而是一轮结构化协商：

```text
ToolSpec
→ 模型返回 ToolCall
→ RiftCoach 校验权限并交给 ToolRuntime
→ ToolRuntime 返回 ToolResult
→ RiftCoach 转成 TOOL 消息
→ 模型观察结果后继续
```

3G-1 只定义厂商无关的数据协议。它不实现循环、权限或某个厂商的 SDK 字段。

## 2. 五个核心对象

### `ToolSpec`

交给模型的工具说明书：

- `name`：稳定工具名；
- `description`：用途；
- `input_schema`：参数 JSON Schema。

它不包含 handler，不具备执行权限。真正的 handler 仍保存在 `app.tools.ToolDefinition` 中。

### `ToolCall`

模型提出的候选调用：

- `id`：本次调用关联 ID；
- `name`：工具名；
- `arguments`：模型生成的参数。

`ToolCall` 不是可信执行命令。阶段 5 的 Skill 权限和 ToolRuntime Schema 校验仍必须检查它。

### `ChatMessage(role=ASSISTANT)`

Assistant 消息现在可以是：

- 只有文本；
- 只有一个或多个 `tool_calls`；
- 同时有文本和 `tool_calls`。

不能既没有文本，也没有工具请求。

### `app.tools.ToolResult`

这是现有可靠 ToolRuntime 的执行结果，包含：

- 成功或失败；
- 数据或安全错误；
- 尝试次数；
- 缓存和 fallback；
- 耗时；
- Runtime `call_id`。

Provider 层不再定义第二个同名 `ToolResult`，避免把运行时结果和模型消息混淆。

### `ChatMessage(role=TOOL)`

把可靠执行结果回填给模型的观察消息：

- `content`：序列化后的安全结果；
- `tool_call_id`：必须与模型原始 `ToolCall.id` 对应；
- `name`：可选工具名。

模型只能看到经过裁剪、脱敏和序列化的结果，不直接获得 Runtime 内部异常对象。

## 3. 一次完整时序

```text
1. User
   “分析最近十局。”

2. Request
   messages=[user message]
   tools=[riot.recent_match_ids ToolSpec]
   tool_choice=auto

3. Model Response
   content=None
   tool_calls=[
     ToolCall(
       id="call-1",
       name="riot.recent_match_ids",
       arguments={"puuid": "...", "count": 10}
     )
   ]

4. Runtime
   检查 Skill 白名单
   → JSON Schema 校验
   → ToolRuntime 执行
   → ToolResult

5. Tool Message
   role=tool
   tool_call_id="call-1"
   content='{"match_ids":[...]}'

6. Next Request
   原消息
   + assistant ToolCall 消息
   + tool result 消息

7. Model
   基于 Observation 继续调用工具或给出最终答案
```

`tool_call_id` 是关键关联键。如果丢失，模型无法知道某个结果对应哪次请求，并行工具调用时尤其危险。

## 4. 角色不变量

| Role | 必须包含 | 禁止包含 |
|---|---|---|
| system | 非空文本 | ToolCall、tool_call_id |
| user | 非空文本 | ToolCall、tool_call_id |
| assistant | 文本或 ToolCall 至少一个 | tool_call_id |
| tool | 非空文本、tool_call_id | 新 ToolCall |

同一条 Assistant 响应中的 ToolCall ID 必须唯一；同一请求中的 ToolSpec 名称也必须唯一。

## 5. `tool_choice`

V1 定义三种厂商无关策略：

- `auto`：模型可以回答，也可以请求工具；
- `none`：不允许请求工具；
- `required`：必须请求至少一个已提供的工具。

指定某一个工具、并行调用策略和厂商特有 Strict Schema 以后再扩展，避免 3G-1 过早绑定具体 SDK。

## 6. 当前还没有实现什么

本步骤不能声称系统已经拥有 Agent Loop。尚未实现：

- Registry；
- 智谱 Tool Calling SDK 映射；
- 第二 Provider；
- Skill 工具白名单；
- 工具循环；
- 轮次、Token、时间和工具预算；
- 重复调用和无进展检测；
- Streaming。

Provider Capability 已在 3G-2 建立；其余分别属于 3G-3 至 3G-6 和阶段 5。
详见：[Provider 能力协商](provider_capability_negotiation.md)。

## 7. 测试证明什么

`tests/test_provider_tool_calling_models.py` 验证：

- 旧纯文本消息仍兼容；
- Assistant 可以只返回 ToolCall；
- Tool 消息必须关联原调用；
- Role 不变量被强制执行；
- ToolSpec 使用对象型 JSON Schema；
- 工具名和调用 ID 不允许重复；
- `required` 没有任何工具时会拒绝。

这些测试只证明内部协议一致，不证明智谱或其他厂商真实 API 已支持该协议。

## 8. 面试中的准确说法

可以说：

> 我先把纯文本 Provider 契约扩展成厂商无关的 Tool Calling 消息模型，区分模型可见的 ToolSpec、模型提出的 ToolCall、可靠 ToolRuntime 结果和回填 Observation，并通过 role-specific invariants 与 call ID 关联避免歧义。

暂时不能说：

> 已经实现多模型 Agent Runtime 或完整 Function Calling。
