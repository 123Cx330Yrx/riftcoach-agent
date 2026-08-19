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

## 9. 把概念落到真实源码

前面的循环图解释“发生了什么”，这一节解释“代码分别在哪里做”。先看 5A
建立时最核心的四个对象：

| 对象 | 源码位置 | 在一次运行中的职责 |
|---|---|---|
| `AgentRunRequest` | `app/agent/loop.py` | 保存初始消息、允许工具、最大迭代数、最大工具调用数、超时和运行元数据；对象不可变，调用方不能在循环途中偷偷扩大权限 |
| `AgentLoop` | `app/agent/loop.py` | 取得工具定义，构造 `ChatRequest`，调用 Provider，判断是最终文本还是 ToolCall，并决定继续或停止 |
| `ToolExecutionRecord` | `app/agent/loop.py` | 把模型给出的 call ID、工具名、参数和 `ToolRuntime` 的稳定结果包成一条可审计记录 |
| `AgentRunResult` | `app/agent/loop.py` | 统一返回状态、停止原因、完整消息、Provider 响应、工具记录、Usage 和最终响应；调用方不必从异常或日志里猜结局 |

真正的协作关系是：

```text
调用方
  │ 构造 AgentRunRequest
  ▼
AgentLoop
  ├─ ToolRegistry.get()：把 allowed_tools 解析为真实工具定义
  ├─ require_provider_capabilities()：有工具时要求 Provider 支持 Tool Calling
  ├─ LLMProvider.chat()：只让模型提出文本或结构化 ToolCall
  ├─ ToolRuntime.execute()：程序校验并执行模型请求
  ├─ ToolExecutionRecord：保存每次实际执行的稳定结果
  └─ AgentRunResult：形成 completed / stopped / failed 终态
```

这张图里最重要的权限边界是：`AgentLoop` 只把 `AgentRunRequest.allowed_tools`
列出的 `ToolSpec` 给 Provider；模型返回的工具名还要再次对照这份白名单。通过后也
不是模型直接运行 Python，而是交给阶段 3 已有的 `ToolRuntime` 做输入 Schema、超时、
重试、熔断、fallback 和输出 Schema 处理。

一次成功的工具往返会使消息历史按下面的顺序增长：

```text
初始 USER 消息
→ Provider 返回带 ToolCall 的 ASSISTANT 消息
→ ToolRuntime 返回结果
→ AgentLoop 把稳定 JSON 包装成 TOOL 消息
→ 下一轮 Provider 同时看到原请求、ToolCall 和 Tool Observation
→ Provider 返回最终 ASSISTANT 文本
```

`_canonical_json()` 会用稳定键序列化参数，因此同名、同参数的重复调用即使字典
键顺序不同也会得到同一签名；`_tool_result_content()` 只把稳定的工具结果信封写入
`TOOL` 消息。这里实现的是有限循环和明确终态，不是让模型拥有无限自治权。

## 10. 5A 原始验收矩阵

5A 在提交 `f9f002e` 中建立时，`tests/test_agent_loop.py` 有六类核心行为；
`tests/test_agent_loop_riftcoach_integration.py` 再增加一条领域纵向。它们分别证明：

| 要求 | 原始测试 | 观察到的行为 | 没有证明什么 |
|---|---|---|---|
| 工具往返后返回最终文本 | `test_agent_loop_executes_tool_then_returns_final_response` | 两次 Provider 请求之间插入一条 `TOOL` 消息；结果含一条工具记录；两次 Usage 被累计 | 不证明真实模型会正确决定何时调工具 |
| 不需要工具时直接完成 | `test_agent_loop_can_finish_without_tools` | 首轮文本响应形成 `completed/final_response`，工具记录为空 | 不证明回答内容正确 |
| 越权工具零执行 | `test_agent_loop_rejects_tool_outside_allowlist` | 模型请求 `system.secret` 时得到 `failed/tool_not_allowed`，`tool_executions` 为空 | 不等于完整应用鉴权或沙箱 |
| 能力不支持时调用前失败 | `test_agent_loop_rejects_text_only_provider_before_calling_it` | 只支持文本的 Provider 在 `chat()` 之前被能力协商拒绝 | 不证明任何真实 Provider 已支持 Tool Calling |
| 达到迭代预算时停止 | `test_agent_loop_stops_at_iteration_budget_before_unbounded_execution` | 当本轮已到上限时不执行新 ToolCall，返回 `stopped/max_iterations` | 不等于跨运行的 Token/金额预算 |
| 相同 ToolCall 不重复执行 | `test_agent_loop_stops_repeated_identical_tool_calls` | 第一次执行被记录，第二次同名同参数调用触发 `duplicate_tool_call` | 只阻止相同签名，不理解业务层“语义重复” |
| RiftCoach 领域工具可接入 | `test_agent_loop_calls_real_riftcoach_knowledge_tool` | Fake Provider 请求真实 `knowledge.search`；RAG 返回 `04_data_boundaries.md` 来源；Observation 再回填给 Provider | Fake Provider 不是模型质量证据，RAG 单例也不是检索泛化证明 |

把同一证据按工程链再压缩一次，便于代码审查和面试复习：

| 要求 | 权威源码 | 测试证据 | CI/限制证据 |
|---|---|---|---|
| 受限且不可变的运行输入 | `app/agent/loop.py` 的 `AgentRunRequest` | 请求校验及迭代/工具预算测试 | `f9f002e` 进入 Actions `31063937488` 成功快照；预算只属于一次内存运行 |
| 模型提议、代码执行 | `AgentLoop.run()`、`ToolRegistry`、`ToolRuntime` | 成功工具往返、越权零执行、能力调用前拒绝 | Fake Provider 隔离了循环正确性，不能证明真实模型决策质量 |
| 可审计的 Observation 与终态 | `ToolExecutionRecord`、`AgentRunResult` | Usage 累计、TOOL 消息回填、直接完成和明确停止原因 | 5A 没有 Harness 发布权、持久 Trace 或 Session |
| 首个 RiftCoach 工具纵向 | `build_knowledge_tools()` 与本地 RAG Adapter | `test_agent_loop_calls_real_riftcoach_knowledge_tool` | 真实本地检索 + Fake Provider；外部 Provider/Riot 调用为 0 |

RQ-067 补齐时在当前 `HEAD` 重新运行两个文件，得到 `16 passed`。当前数量多于
原始七项，是因为后续阶段在同一稳定接缝上加入了批量 ToolCall 的数量/白名单/
重复签名整批预检、Context 预算和总 deadline 等回归。提交 `f9f002e` 与 5B/5C/4M 同期进入公开快照后，
GitHub Actions run `31063937488` 全绿；该公共 CI 证明同一仓库快照可重复测试，
不把 Fake Provider 变成真实 Provider 证据。

### 可亲自观察的命令

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_agent_loop.py `
  tests\test_agent_loop_riftcoach_integration.py -q
```

重点不是背住 `passed` 数字，而是打开集成测试观察两个请求：第一次请求暴露
`knowledge.search`，第二次请求的末尾角色是 `TOOL`，并且工具 call ID 与模型请求
对应。这正是 Agent Loop 区别于“一次普通聊天调用”的地方。

## 11. 后续阶段怎样深化 5A，而不是推翻 5A

5A 是最小循环地基。后来代码仍使用同一个 `AgentLoop`，但责任逐层加固：

| 后续检查点 | 在 5A 之上增加什么 | 为什么仍不属于原始 5A |
|---|---|---|
| 5B/5C | Skill 合同、Catalog 和 Router 决定任务类型、工具白名单和预算 | 5A 只消费显式 `AgentRunRequest`，不理解用户意图或 Skill |
| 5D-1/2 | 把 selected Skill、输入 Artifact 和信任分层 Context 绑定起来 | 5A 不负责选择哪些业务事实进入 Prompt |
| 5D-3 | Manifest-only compiler、完整消息 Context 门和 Provider/Tool 共用总 deadline | 这是把业务合同安全编译成 5A 请求，不是另建循环 |
| 5D-4/5 | 把实际工具记录转换为 Evidence，并把模型文本作为草稿交给唯一 Harness | 5A 的 `final_response` 不是发布许可 |
| 5E | 可选 Observer、统一 Event/Usage/Trace、`run()`/`stream()` parity | 5A 没有持久 Trace、实时消费或完整 Runtime 表面 |
| 5F | 用同一合同审计 Pi；最终拒绝其产品 Runtime，只保留评测资产 | 第三方 SDK 必须适配既有边界，不能取代 ToolRuntime/Harness |

当前 `app/agent/loop.py` 因这些后续增量已经包含 `max_context_tokens`、递减总
deadline、批量 ToolCall 先做数量/白名单/重复签名整批预检再顺序执行，以及可选 Runtime Observer。阅读当前
文件时要区分“5A 首次证明的最小循环”和“后续阶段沿同一合同深化的能力”，不能把
今天的全部代码倒算成 5A 当时一次完成。

相关深化教材：

- `docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`：5D 总体组合；
- `docs/plans/2026-08-07-skill-run-compiler-budget-design.md`：Context 与总预算；
- `docs/plans/2026-08-08-skill-harness-composition-design.md`：草稿如何进入 Harness；
- `docs/plans/2026-08-17-agent-runtime-v1-exit-review.md`：5E Runtime 最终边界。

## 12. 失败与安全边界再归纳

`completed`、`stopped` 和 `failed` 不是好坏分数：

- `completed` 表示循环获得最终文本，不表示文本已经通过事实评测；
- `stopped` 表示预算、重复调用、Context 或 deadline 等代码边界主动结束运行；
- `failed` 表示 Provider、工具配置或越权等运行条件不成立。

5A 没有发布报告的权限。模型文本在后来的 5D 才被明确降格为 `CoachDraft`，再由
`ReviewHarness` 决定发布、降级或拒绝。5A 也没有 Session、Memory、持久任务、
正式 Auth、MCP、Multi-Agent、DAG 恢复或公网部署。

## 13. 面试时怎样讲这段演进

可以说：

> 我先实现了 Provider-neutral 的同步有界 Agent Loop。模型只能提出结构化 ToolCall，
> 代码用白名单和能力协商预检，再由 ToolRuntime 执行并把 Observation 回填；循环用
> 最大迭代、工具调用和重复签名形成明确终态。随后我没有重写循环，而是通过 Skill
> compiler、Context 预算、Harness 和 Runtime observer 逐层深化它。

不可以说：

- 5A 当时已经完成真实 GLM 领域 Tool Calling；
- 得到最终文本就等于报告通过质量门并可发布；
- 有循环和工具就等于 LangGraph、Multi-Agent 或完整 Agent Runtime；
- 当前 `AgentLoop` 中后加的 Context、deadline、Observer 全是 5A 一次实现的；
- `16 passed` 或公共 CI 全绿证明模型回答质量或线上可靠性。
