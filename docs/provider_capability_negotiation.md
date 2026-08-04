# 3G-2：Provider 能力协商

## 1. 为什么 Tool Calling 协议还不够

3G-1 解决的是消息如何表达：

```text
ToolSpec
→ ToolCall
→ ToolResult
→ TOOL 消息
```

但消息协议本身不能回答：

```text
当前 Provider 是否真的支持 Tool Calling？
是否支持结构化输出？
是否支持流式响应？
是否支持并行工具调用？
```

如果 Harness 不知道这些能力，最危险的行为是把工具请求交给一个只支持文本聊天的适配器。适配器可能：

- 在请求发出后才收到厂商错误；
- 静默丢弃 `tools` 字段，退化成普通文本回答；
- 不同 Provider 对同一个请求表现不一致。

3G-2 的目标是：**在外部 SDK 调用之前完成能力协商**。

## 2. 能力描述的是“当前适配器实现”

`ProviderCapabilities` 描述的不是厂商官网理论能力，也不是模型名称暗示的能力，而是：

> 当前 RiftCoach 适配器已经完成映射、解析、错误处理和测试验证的端到端能力。

因此当前 `ZhipuProvider` 的声明是：

```text
text_chat = true
tool_calling = false
structured_output = false
streaming = false
parallel_tool_calls = false
```

这不是说智谱平台永远不能 Tool Calling，而是说 **RiftCoach 当前还没有完成智谱 Tool Calling 适配**。等 3G-4 完成 SDK 映射和契约测试后，才能把 `tool_calling` 改成 `true`。

## 3. 三个核心对象

### `ProviderCapability`

一个能力名称：

```python
ProviderCapability.TEXT_CHAT
ProviderCapability.TOOL_CALLING
ProviderCapability.STRUCTURED_OUTPUT
ProviderCapability.STREAMING
ProviderCapability.PARALLEL_TOOL_CALLS
```

### `ProviderCapabilities`

一个适配器的能力画像。它使用布尔字段，方便阅读配置和测试；`supported` 属性将已开启的能力转换为集合。

### `CapabilityNegotiation`

一次请求和一个能力画像的比较结果：

```text
required   = 请求需要的能力
supported  = 适配器拥有的能力
missing    = required - supported
compatible = missing 是否为空
```

## 4. 当前请求如何推导需求

目前只实现最小规则：

```text
所有 ChatRequest 都需要 TEXT_CHAT

tools 非空且 tool_choice != none
→ 额外需要 TOOL_CALLING
```

例如：

| 请求 | 需要的能力 | 文本适配器结果 |
|---|---|---|
| 普通文本聊天 | `TEXT_CHAT` | 通过 |
| 带工具且 `auto` | `TEXT_CHAT + TOOL_CALLING` | 拒绝 |
| 带工具且 `required` | `TEXT_CHAT + TOOL_CALLING` | 拒绝 |
| 带工具但 `none` | `TEXT_CHAT` | 通过，工具不会被启用 |

这里的 `none` 是显式策略：调用方告诉 Provider，本轮不允许模型使用工具。它不是“Provider 已支持 Tool Calling”的证明。

## 5. 调用时序

```text
ChatRequest
    │
    ▼
推导 required capabilities
    │
    ▼
比较 ProviderCapabilities
    │
    ├── 缺失能力 → ProviderCapabilityError → 不发生网络请求
    │
    └── 能力满足 → 构建厂商 payload → 调用 SDK
```

`ProviderCapabilityError` 只暴露安全的：

```text
provider
code = unsupported_capability
missing_capabilities
```

不会把 API Key、完整 Prompt 或厂商原始错误带进异常信息。

## 6. 为什么暂时不做自动切换

3G-2 只做“发现不匹配并安全拒绝”。它还不负责：

- 选择第二个 Provider；
- 根据价格或延迟路由；
- 重写请求以适配另一家 Provider；
- 记录健康状态；
- 在 Tool Calling 不支持时自动改成纯文本。

这些属于后续 Registry、Fallback 和 AgentRuntime 决策。过早自动切换会掩盖 Provider 能力差异，让调试和评测失去可解释性。

## 7. 与后续阶段的关系

```text
3G-1  厂商无关 Tool Calling 消息模型
3G-2  Provider 能力声明与运行前协商（当前）
3G-3  Provider Registry 与配置选择（已完成）
3G-4  智谱 Tool Calling 映射与真实冒烟
3G-5  第二 Provider 同契约验证
3G-6  任务级路由、Fallback 与健康状态
5D   Python 受限 Agent Loop
```

Agent Loop 不应直接猜测 Provider 能力；它应向 Provider 契约提出需求，由能力协商结果决定能否运行。

3G-3 详见：[Provider Registry 与配置选择](provider_registry.md)。

## 8. 当前测试证明什么

测试覆盖：

- 文本适配器默认能力只有 `TEXT_CHAT`；
- 并行工具调用不能脱离 Tool Calling 单独开启；
- 普通文本请求可以通过；
- `auto`/`required` 工具请求会发现缺失 `TOOL_CALLING`；
- `none` 请求不会错误要求 Tool Calling；
- 支持 Tool Calling 的画像可以通过协商；
- 智谱适配器遇到未实现的工具请求时，在 SDK 调用前拒绝，调用次数为零。

这些测试证明的是运行前契约，不证明智谱已经完成 Tool Calling。

## 9. 面试中的准确说法

可以说：

> 我没有把厂商支持矩阵写死在 Agent 逻辑里，而是建立了 Provider Capability Contract。Harness 会从请求推导所需能力，在 Provider 适配器执行外部调用前完成协商；当前智谱适配器只宣称已验证的文本能力，对尚未完成映射的 Tool Calling 会安全拒绝。

暂时不能说：

> RiftCoach 已经能自动在 GLM、DeepSeek、Qwen、Kimi 之间切换并完成 Tool Calling。
