# 5D-3 Skill Run Compiler & Budget Enforcement 设计

## 1. 结论先行

5D-3 在 `ValidatedSkillExecution + ContextBundle` 与现有 `AgentRunRequest` 之间增加
`AgentRunCompiler`。Compiler 不接受调用方提交工具或预算，而是重新从已验证
Manifest 读取 allowed tools、iteration/tool-call/timeout/context budgets，验证工具已
注册、执行身份与 Context 身份一致，再产生不可变 `AgentRunRequest`。

现有 `AgentLoop` 增加两类确定性保护：

1. 每次 Provider 调用前重新估算完整累计消息，包括 assistant ToolCall 参数和
   Tool Observation；超出 `max_context_tokens` 时不再调用 Provider；
2. 将 Manifest `timeout_s` 作为协作式总 deadline，每次 Provider/Tool 调用只获得
   剩余时间；预算耗尽后停止后续调用。

本检查点只编译和测试受限请求/预算执行，不运行真实 Provider，不把 Agent 草稿转换为
`KnowledgeEvidence`，不接 Harness，也不进入 5D-4。

## 2. 初学者理解：Compiler 为什么不是“再写一个 Prompt”

5D-2 已经解决“模型应该看到什么”。5D-3 解决的是另一个问题：

```text
模型看见什么       → ContextBundle
模型被允许做什么   → AgentRunRequest
谁决定这些权限     → AgentRunCompiler（只信 Manifest）
运行中何时必须停止 → AgentLoop 的确定性预算检查
```

如果 allowed tools 或预算来自用户文本、RAG 文档，Prompt Injection 就可能变成真正的
越权。RiftCoach 因此把控制面放在 Python 代码中：模型可以请求工具，但不能给自己添加
工具；可以继续对话，但不能提高 iteration、tool-call、context 或 timeout 上限。

## 3. 三种方案比较

### 方案 A：扩展现有请求与 Loop，增加薄 Compiler

`AgentRunRequest` 已经拥有 messages、allowed tools、迭代/调用/超时字段。只补
context ceiling、Compiler 和 Loop guard，职责最小且可独立测试。采用。

### 方案 B：新增 `BudgetedAgentLoop` 包装现有 Loop

包装器看不到 Loop 内部每次新增的 assistant/tool messages，除非复制循环。这样会出现
两套停止原因、迭代计数和工具执行逻辑，拒绝。

### 方案 C：只把预算写入 metadata

metadata 能用于 Trace，却不能阻止 Provider 或 Tool 被继续调用。这是假门禁，拒绝。

## 4. Compiler 合同

```text
AgentRunCompiler.compile(
    execution: ValidatedSkillExecution,
    context: ContextBundle,
) -> AgentRunRequest
```

Compiler 依次验证：

1. 两个参数都是已通过前置合同的类型；
2. run ID、Skill name/version 完全一致；
3. Context 消息是 sections 的规范渲染，不能夹带另一个 system/user Prompt；
4. 重新估算后的消息未超过 Context effective ceiling；
5. Context ceiling 不高于 Manifest `max_context_tokens`；
6. Manifest 中每个 allowed tool 都存在于当前 ToolRegistry；
7. 只从 Manifest 映射 `max_iterations`、`max_tool_calls` 和 `timeout_s`。

输出 metadata 只记录安全的 run/Skill/context/input digest 摘要，不接收用户自定义权限。

## 5. 完整消息预算

5D-2 的默认 sizer 原先主要计算 `message.content`。但 Tool Calling 消息还包含：

```text
assistant.tool_calls[].id
assistant.tool_calls[].name
assistant.tool_calls[].arguments
tool.tool_call_id
tool.name
tool.content
```

5D-3 将完整 provider-neutral message envelope 做确定性 JSON 序列化后估算。这样大体积
ToolCall arguments 不能绕过预算。

Loop 在每次 Provider 调用前执行：

```text
estimate(accumulated messages) <= request.max_context_tokens
```

初始请求越界时 Provider 调用次数为 0；Tool Observation 导致越界时，下一轮 Provider
调用被阻止。V1 不做 Tool Observation compaction，因为删除或摘要工具证据需要新的
语义/引用评测，属于后续 Context 演进。

## 6. 超时预算

`timeout_s` 定义为 AgentLoop 的协作式总 deadline：

```text
deadline = loop_started_at + timeout_s
remaining = deadline - now
```

- 每次 Provider 请求使用 `remaining` 作为 timeout；
- 每次 ToolRuntime 调用接收同一个 remaining cap，并与工具自身 policy timeout 取较小值；
- remaining 小于等于 0 时，Loop 以 `timeout` 停止；
- Provider/Tool 返回后若总 deadline 已过，不继续下一步。

同步 Python 无法安全强杀任意阻塞函数，因此这是 cooperative deadline，不承诺硬抢占。
网络 Adapter 已通过 `ChatRequest.timeout_s` 或 `ToolContext.remaining_s()` 消费剩余时间；
真正跨进程取消/恢复仍属于阶段 6/8。

## 7. 停止和错误语义

新增：

```text
AgentStopReason.CONTEXT_BUDGET_EXCEEDED
AgentStopReason.TIMEOUT
```

二者属于有界停止 `STOPPED`，不是 Provider 业务失败。Compiler 的身份、工具注册或预算
合同不合法则在 Loop 之前抛 `AgentRunCompileError`，不会调用 Provider。

现有运行时的 `TOOL_NOT_ALLOWED` 仍保留，形成两层防御：Compiler 前置验证正常配置，
Loop 拒绝模型实际请求的越权工具。

## 8. 数据与控制流

```text
ValidatedSkillExecution + ContextBundle + ToolRegistry
                    │
                    ▼
              AgentRunCompiler
        identity / tool / budget checks
                    │
                    ▼
              AgentRunRequest
      messages + allowlist + four budgets
                    │
                    ▼
                AgentLoop
      context check → remaining timeout
                    │
          Provider / ToolRuntime（后续真实执行）
```

本轮测试可以使用 Fake Provider/Fake Clock 证明门禁，但不会创建 5D-4 的真实
`SkillAgentDraftPreparer`。

## 9. 测试如何证明

- 两个真实 Skill 编译出的 tools/budgets 与各自 Manifest 完全一致；
- 调用方没有 API 可以提交 allowed tools 或提高预算；
- run/Skill/version 漂移、Context ceiling 提高、缺失工具在 Provider 前失败；
- ContextBundle messages 与 sections 不一致时无法构造；
- sizer 会计算 ToolCall 参数，长参数比短参数估算更大；
- 初始上下文超限时 Provider 调用为 0；
- Tool Observation 使累计消息超限时第二次 Provider 调用为 0；
- 总 deadline 递减传给 Provider/Tool，耗尽后停止；
- Tool policy 与 run remaining 取较小值；
- 原有 AgentLoop、ToolRuntime、Context 与 Skill 回归持续通过。

## 10. 当前边界与准确表述

完成后可以说：

> RiftCoach 已实现 Manifest 驱动的 Skill Agent 请求编译，并在 Provider 调用前对完整
> 累计消息、迭代、工具调用和协作式总超时做确定性约束。

不能说已经：

- 运行真实 Skill Agent 或真实 Provider Tool Calling；
- 把 ToolResult 转成 KnowledgeEvidence；
- 完成 Harness 组合或报告发布；
- 实现 Tool Observation compaction；
- 能硬中断任意阻塞 Python 代码；
- 完成统一 AgentRuntime、Trace、Session 或恢复。
