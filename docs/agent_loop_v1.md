# 阶段 5A：最小 Agent Loop

## 1. 这一阶段解决什么问题

阶段 1–4 已经能稳定生成比赛事实、检索知识并通过质量门禁，但调用顺序仍然由脚本预先写死。Agent Loop 解决的是另一类问题：

> 当用户问题无法提前写成固定步骤时，模型如何提出工具请求，程序如何执行并把结果重新交给模型，什么时候安全停止？

这一步第一次实现 Agent 的运行原理，但仍然不是完整产品 Agent。

## 2. 最小循环

```text
ChatMessage[]
    │
    ▼
Provider.chat(ChatRequest)
    │
    ├── 文本响应 → COMPLETED
    │
    └── ToolCall[]
          │
          ├── 工具白名单检查
          ├── ToolRuntime Schema 校验与执行
          ├── ToolResult → TOOL ChatMessage
          └── 返回 Provider.chat()
```

模型只提出请求，不拥有工具执行权限。真正的执行仍由 `ToolRuntime` 负责，工具名称、输入和输出都经过已有契约校验。

## 3. 当前实现边界

`app.agent.loop.AgentLoop` 是：

- 单进程；
- 同步；
- 一次运行内存状态；
- 显式工具白名单；
- 最大轮次和最大工具调用预算；
- 重复 ToolCall 检测；
- Provider 错误和未知工具的结构化停止。

它还不是：

- Skill Router；
- Multi-Agent；
- Streaming；
- Session/Memory；
- DAG 或断点恢复；
- Pi、Claude Agent SDK 或 LangGraph 集成。

## 4. 一次运行中的消息变化

第一次调用：

```text
USER: 请回显 hello
```

模型请求工具：

```text
ASSISTANT: tool_calls=[system.echo({"message": "hello"})]
```

程序执行工具并追加观察结果：

```text
TOOL: {"success": true, "data": {"echo": "hello"}}
```

第二次调用时，模型能看到完整消息历史并生成最终文本。

## 5. 为什么先用 Fake Provider

当前 GLM 适配器只声明已经实现的文本聊天能力，尚未实现 Tool Calling。先用 Fake Provider 测试循环，可以把：

- ToolCall 消息协议；
- 工具白名单；
- ToolRuntime 执行；
- 观察结果回填；
- 停止条件；

与具体厂商 SDK 分开验证。这样 Agent Loop 的正确性不会被网络、费用或某一家模型的响应格式掩盖。

## 6. 面试中的准确表述

当前可以说：

> 我实现了一个 Provider-neutral、同步、有工具白名单和预算限制的最小 Agent Loop，并复用 Tool Runtime 执行模型提出的工具调用；循环通过 Fake Provider 契约测试验证。

当前不能说：

- 已经实现 Multi-Agent；
- 已经接入 Pi Agent SDK；
- GLM 已经支持 RiftCoach Tool Calling；
- 已经实现持久化 Agent Runtime 或自动模型路由。

## 7. 首个 RiftCoach 领域切片

回显工具只能证明循环结构正确，不能证明它已经接上 RiftCoach 的领域能力。因此 5A 又增加了一条不访问网络的集成测试：

```text
用户询问 Data Dragon 是否提供英雄胜率
→ Fake Provider 请求 knowledge.search
→ Agent Loop 检查 knowledge.search 是否在白名单
→ Tool Runtime 校验参数并执行真实 LocalHybridKnowledgeProvider
→ RAG 返回带 source_id 的证据
→ Agent Loop 将 ToolResult 编码为 TOOL 消息
→ Fake Provider 读取证据并返回最终文本
```

这里刻意采用“Fake Provider + 真实 RAG 工具”的组合。它分离了两个问题：

- Agent Loop 是否会正确调度领域工具；
- 某家真实模型是否会稳定生成正确的 ToolCall。

第一项已经由本地确定性测试证明；第二项要等 Provider 适配器实现真实 Tool Calling 后，再使用相同领域案例验收。这样即使真实模型调用受网络、费用或厂商格式影响，也不会混淆循环本身的问题。

对应测试：`tests/test_agent_loop_riftcoach_integration.py`。

## 8. 5A 完成后的边界

5A 已经证明：

- 内部消息协议能表达 Assistant ToolCall 和 Tool Observation；
- Agent Loop 只把白名单内的工具描述交给模型；
- ToolCall 必须经过 Tool Runtime，而不是由模型直接执行；
- 真实的 RiftCoach 知识检索结果能够回填给 Provider；
- 循环会在最终文本、预算耗尽、重复调用或错误时明确停止。

5B 已在此基础上定义 Skill Contract：Skill 决定某类任务允许使用哪些工具、采用多少预算、需要什么输入输出，以及怎样判断成功。下一步 5C 才会根据用户请求选择 Skill。
