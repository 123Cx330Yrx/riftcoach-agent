# 阶段 5E：AgentRuntime V1 入口设计

## 1. 结论先行

5E 不会重写 5D 已经验证过的 Agent Loop、Tool Runtime 或 ReviewHarness，也不会现在
引入 LangGraph、Pi、Claude Agent SDK。RiftCoach 将先实现一个**框架中立的薄
AgentRuntime V1**：

```text
SkillExecutionRequest
        │
        ▼
AgentRuntimeV1
  boundary → context → restricted agent → ReviewHarness
        │
        ├── run()    → RuntimeRunResult
        └── stream() → ordered RuntimeEvent ... → 同一个 RuntimeRunResult
```

这个 Runtime 只负责五件事：

1. 用同一个 `run_id` 组合已有执行链；
2. 把分散的安全运行信号转成有序事件；
3. 汇总“不把未知写成零”的 Usage；
4. 原子保存不含正文和秘密的最终 Trace；
5. 保证 `run()` 与 `stream()` 经过同一条控制流，并得到同一终态。

ReviewHarness 继续拥有唯一发布权。Runtime 能观察、组合和报告发布结果，但不能绕过
Harness 发布 Agent 草稿。

本入口批只冻结设计、ADR 和实施顺序，不实现 Runtime，不读取 API Key，不调用真实
Provider，也不改变当前“没有领域 Provider 准入，模型质量 unknown”的事实。

## 2. 初学者先理解：为什么有了 Agent Loop 还需要 Runtime

### 2.1 Agent Loop 是任务内部的循环

5D 的 Loop 已经能执行：

```text
模型响应
  ├── 最终回答 → 结束 Loop
  └── ToolCall → 校验权限/预算 → 执行工具 → 把结果送回模型
```

它回答的是“模型这一轮能否调用工具，下一轮要不要继续”。

### 2.2 Runtime 是整次任务的运行壳

一次 RiftCoach 复盘并不只有 Loop。Loop 之前还有输入边界和 Context，Loop 之后还有
事实评测、有限修订、Artifact 落盘和发布决策。现在这些组件各自有信号，但调用方需要
自己拼装：

- `AgentRunResult` 知道 Agent 为什么停止；
- `ToolExecutionRecord` 知道哪些工具实际执行；
- `ToolResult` 知道工具尝试次数和耗时；
- `RunManifest` 知道 Harness 状态转换和最终发布决定；
- `TokenUsage` 只知道成功规范化响应返回的 Token；
- Artifact Store 知道最终文件及其 SHA-256。

没有统一 Runtime 时，未来 API 或网页会遇到三个直接问题：

1. 不知道一次请求当前走到哪一步；
2. 不知道降级到底来自 Provider、Tool、Evaluation 还是发布门；
3. 可能把未取得的 Token/费用错误显示为 `0`。

所以 5E 不是“再造一个 Agent”，而是把已经安全工作的部件装进一个可观察、可追踪的
运行边界。

## 3. 现有代码审计

### 3.1 可以直接复用的事实源

| 现有组件 | 已有事实 | 5E 的处理 |
|---|---|---|
| `SkillExecutionRequest` | 未信任应用输入、Router 决策、Skill 输入、Artifact commitment | 作为 Runtime 的领域请求主体 |
| `SkillExecutionBoundary` | 校验 selected Skill 身份、版本、run_id、输入与哈希 | Runtime 直接调用，不复制规则 |
| `ContextBuilderV1` | 生成信任分层、预算受限的 `ContextBundle` | Runtime 观察成功/失败和安全摘要 |
| `AgentRunRequest` | 工具白名单、迭代/调用/超时/Context 预算 | 继续由 Compiler 从 Manifest 生成 |
| `AgentRunResult` | Agent 状态、停止原因、Provider responses、Tool records | 投影为安全事件、Usage 和 Trace |
| `ToolResult` | success、attempts、latency、cache、fallback、safe error | 投影安全工具元数据，不保存结果正文 |
| `RunManifest` | Harness 转换、Artifact、revisions、final decision | 继续作为发布终态真相源 |
| `SkillReviewExecutionResult` | typed output + terminal manifest + agent outcome | 作为 Runtime 成功组合后的领域结果 |

### 3.2 当前真实缺口

现有 `SkillReviewExecutor.execute()` 对外仍是一段同步黑盒。若只在它外面计时，Runtime
只能在执行完成后根据结果“补写”事件。这会出现一个看似有 `stream()`、实际却没有实时
进度的假实现。

另一个真实 Bad Case 来自 5D 的 DeepSeek development Usage replay：外部请求已经发送，
但没有形成规范化 `ChatResponse`。当前成功响应的 `TokenUsage(0, 0)` 类型不能单独表达：

```text
确实观察到 0 Token
vs
请求已发送，但 Provider Usage 未知
```

5E 必须显式区分这两种状态。

最后，5D 的 Agent failure 已保留安全 `provider_error_code`，但若草稿准备抛错，外层领域
执行器未必能得到完整 `AgentRunResult`。因此 Runtime 不能只依赖最终正常结果反推失败；
它需要在稳定接缝收到实时、安全、有限的观察信号。

## 4. 参考项目怎样吸收，而不是照搬

### 4.1 EchoMind

可吸收的是“记录调用成功率、耗时并用于运维观察”的思想。其 Monitor 更接近聚合指标，
并不是完整的单次 Runtime Trace，因此 5E 不复制它的动态路由惩罚。

### 4.2 AGI-Saber

Saber 提供 DAG、并发、取消、快照和事件总线参考，但当前 RiftCoach 只有一条受限复盘
链路。现在引入 Kafka、DAG 或线程图会把 5E 变成通用调度平台，并重复已有 Harness
状态机。5E 只吸收“执行过程通过事件对外观察”的思想。

### 4.3 Sea / AGI-OpenResearch

Sea 的有序事件、Artifact 引用和 SSE replay 对后续阶段有价值；但其状态快照更新与事件
追加不是一个原子事务，错误还可能被忽略，因此不能把它直接当作严格事件溯源模板。

5E V1 只实现进程内实时事件和**原子最终 Trace 快照**。跨进程事件、持久 replay、租约、
恢复和 checkpoint 分支继续留在阶段 6/8。

## 5. 三种方案比较

### 方案 A：只包住现有 `SkillReviewExecutor`

```text
start → executor.execute() → 根据最终结果补写 events → end
```

优点：改动最小，几乎没有跨模块接缝变化。

缺点：Provider、Tool 和 Harness 运行时没有真实事件；`stream()` 只能事后回放；Provider
失败发生在哪次调用、Harness 当前在哪个状态都只能猜测或丢失。

结论：拒绝。它会让 API 名字比真实能力更强。

### 方案 B：薄 Runtime + 可选观察端口

Runtime 组合现有边界；AgentLoop 与 ReviewHarness 在稳定位置发出安全语义信号。底层
组件不负责全局 sequence、UTC 时间或 Trace 文件，统一由 Runtime Recorder 处理。

优点：

- 复用全部已验证控制流；
- 真正支持运行中的事件；
- 不让 Agent/Harness 反向依赖产品 API；
- 以后可用同一合同比较自建 Runtime 与第三方 SDK。

代价：AgentLoop、Harness 等稳定接缝需要新增默认关闭的 observer 参数，并增加回归测试。

结论：采用。

### 方案 C：事件溯源/DAG/框架重写

把每个状态变化变成 durable event，由 reducer 重建状态，或直接迁移到 LangGraph、Pi、
Claude Agent SDK。

优点：天然适合暂停、恢复、跨进程订阅、并发和复杂任务图。

缺点：会复制或替代 ReviewHarness 状态机；必须立即处理幂等、事件 schema 迁移、消费者
偏移、租约和 crash recovery；当前没有相应 Bad Case。

结论：拒绝作为 V1。第三方 Runtime 的采用比较属于 5F；持久恢复属于阶段 6/8。

## 6. 冻结的 V1 架构边界

### 6.1 Router 在 Runtime 外面

V1 接受已经包含 `RouterDecision` 的 `SkillExecutionRequest`，但仍由 Runtime 重新通过
`SkillExecutionBoundary` 验证。Router 负责“选哪个 Skill”；Runtime 负责“把已选择任务
安全地运行完”。两者不混为一个模块。

### 6.2 Runtime 拥有组合，不拥有业务真相

```text
应用 / 后续 API
     │
     │ SkillExecutionRequest
     ▼
AgentRuntimeV1
     ├─ validate boundary
     ├─ build context
     ├─ execute SkillReviewExecutor
     │      └─ AgentLoop → ToolRuntime → ReviewHarness
     ├─ collect safe signals
     ├─ build RuntimeUsage + RuntimeTrace
     └─ atomically persist terminal trace
```

- Skill Manifest 仍是 Agent 权限和 Loop 预算来源；
- Harness Config 仍是质量阈值、fallback 和最大修订次数来源；
- `RunManifest` 与最终 Artifact 仍是发布真相；
- Runtime 只记录上述 policy 的实际来源和值，不能私自扩大权限或修改终态。

### 6.3 一个执行核心，两种消费方式

内部只保留一条执行函数：

```text
_execute(request, event_sink) -> RuntimeRunResult
```

`run()` 使用内存 Recorder 收集事件并等待结果。`stream()` 在一个受控 worker 中运行相同
`_execute()`，通过进程内队列逐条交付同一 Recorder 生成的事件；最后一项携带与 `run()`
同合同的终态结果。

V1 不支持取消。若流消费者提前离开，后台执行仍在既有预算内完成，并尽量保存终态 Trace；
`cancel()`、resume 和持久会话属于 V2。

## 7. 合同设计

### 7.1 `RuntimeRunRequest`

它包装而不复制 `SkillExecutionRequest`，并只接受可信 Runtime policy：

```text
execution_request
runtime_policy_version
event_budget
trace_schema_version
```

调用方不能通过普通用户输入提高 Skill 工具、迭代、Token、timeout、评测或修订预算。

### 7.2 两层事件模型

底层组件只发 `RuntimeSignal`：

```text
kind + safe typed payload
```

Recorder 再生成 `RuntimeEvent`：

```text
schema_version
run_id
sequence
occurred_at_utc
elapsed_ms
kind
safe payload
```

这样 AgentLoop 和 Harness 不需要知道时钟、全局顺序或文件存储，也避免循环依赖。所有
payload 采用按事件类型定义的 allowlist，禁止“随便塞一个 dict”。

### 7.3 V1 事件族

| 事件 | 表示什么 | 允许的代表性字段 |
|---|---|---|
| `run_started` | Runtime 接受执行 | Skill name/version、Runtime policy version |
| `execution_validated` | 边界验证通过 | input/artifact commitment 摘要 |
| `context_built` | 最小 Context 构建完成 | contract version、估算大小、省略项 ID |
| `provider_call_started` | 一次模型调用即将发出 | provider、model、iteration、call ordinal |
| `provider_call_completed` | 已得到规范化响应 | finish reason、observed usage |
| `provider_call_failed` | 调用失败或无法规范化 | allowlisted failure/provider error code |
| `tool_call_started` | 白名单 ToolCall 通过预检 | tool name/version、call ordinal |
| `tool_call_completed` | ToolRuntime 返回安全 envelope | success、attempts、latency、cache/fallback |
| `harness_transitioned` | ReviewHarness 状态改变 | from/to、revision count |
| `evaluation_completed` | 一次 Evaluation 已验证 | attempt、score、verdict、blocking categories |
| `publication_decided` | Harness 作出唯一发布决定 | published/degraded/rejected、artifact refs |
| `run_completed` | Runtime 正常获得终态 | runtime/publication status、terminal reason |
| `run_failed` | 在获得正常终态前失败 | safe stage、failure code、publication status if known |

V1 不把每个日志行、每个 Token chunk 或报告文本变成事件。这里的“stream”是运行状态
事件流，不是模型文本逐 Token 输出；文本 Token streaming 需要 Provider 合同和前端消费
证据后另行设计。

### 7.4 明确禁止进入 Event/Trace 的内容

- API Key、Authorization header、`.env` 值；
- 用户原始 utterance；
- 完整 Prompt、消息正文和模型 reasoning；
- Tool arguments、Tool result data、RAG chunk 正文；
- 草稿、最终报告、Evaluation issue 原文；
- 原始异常、SDK response body、request ID；
- 任意未经过 schema allowlist 的 Provider 字段。

需要正文时，通过已有受控 Artifact 引用和 SHA-256 查找；Trace 不复制正文。

### 7.5 `RuntimeRunResult`

Runtime 自身状态与 Harness 发布状态必须分开：

```text
runtime_status: completed | failed
publication_status: published | degraded | rejected | null
terminal_reason
typed_skill_output: present only when safely built
trace_reference
```

例如边界验证失败时，Runtime 是 `failed`，Harness 尚未开始，所以 publication status 为
`null`。Provider 失败但 Harness 成功发布确定性 fallback 时，Runtime 可以是 `completed`，
publication status 为 `degraded`。这两种情况不能都写成一个模糊的 `failed`。

## 8. Usage：为什么不能简单相加

### 8.1 三种可观测状态

Token 和费用至少有三种语义：

1. `complete`：每个已发送 Provider 调用都有可用 Usage；
2. `partial`：部分已发送调用有 Usage，至少一个没有；
3. `unknown`：有调用发出，但没有任何可结算 Usage。

如果没有发出 Provider 调用，Token 可以是**观测到的零**；如果请求已经发出但响应无法
规范化，Token/费用必须为 `null`，不能因为 Python 默认值是零就声称没有消费。

### 8.2 V1 Usage 组成

```text
provider_calls_attempted
provider_responses_observed
input_tokens: int | null
output_tokens: int | null
token_observation: complete | partial | unknown | not_applicable

tool_calls
tool_attempts
tool_latency_ms

cost: Decimal | null
currency: string | null
pricing_profile_id/version: string | null
cost_observation: complete | partial | unknown | not_configured
```

成本只允许由注入且版本化的价格表结合完整 Token Usage 推导。没有价格表、模型价格随时间
变化或 Usage 不完整时，cost 保持 `null`。5E 不联网抓价格，也不把 5D 实验 ledger 当成
所有产品运行的通用定价真相。

## 9. Trace 与存储语义

### 9.1 `RuntimeTrace`

最终 Trace 至少包含：

- Runtime、Event、Trace schema 版本；
- run/Skill/Prompt/Context/Provider/Tool/Harness 的安全身份与版本；
- 实际采用的 Loop budget、quality threshold、fallback、`max_revisions`；
- 有序安全事件；
- completeness-aware Usage；
- Runtime 与 publication 双终态及安全原因；
- terminal Manifest 和 Artifact 的相对引用、kind、SHA-256；
- 开始/结束时间和总 elapsed，不含原始正文。

### 9.2 原子最终快照，不伪装事件溯源

V1 新增独立 `RuntimeTraceStore`，在现有 run 目录中通过临时文件 + replace 原子提交
`runtime_trace.json`。它能够记录发生在 Harness 创建之前的边界/Context 失败，不要求
Harness manifest 已存在。

V1 的实时事件保存在当前进程和最终 Trace 中，不逐条 durable append，也不承诺进程崩溃
后 replay。最终 Trace 是审计快照，不是可以重建所有业务状态的事件源。

若 Harness 已经形成发布终态，但 Trace 持久化失败：

- 不篡改 Harness 已经落盘的终态；
- Runtime 返回 `runtime_status=failed`、安全原因 `trace_persistence_failed`；
- 同时保留已知 `publication_status`，但不通过 Runtime 返回报告正文；
- 后续 API 可以明确显示“领域结果已落盘，但可观察性提交失败”，而不是谎称整个运行从未发生。

## 10. 失败分类

Runtime 只持久化稳定高层分类和已允许的安全细分类：

| 阶段 | 高层例子 | 终态含义 |
|---|---|---|
| boundary | `execution_validation_failed` | Harness 未开始，publication null |
| context | `context_build_failed` | Harness 未开始，publication null |
| agent | `provider_failed`、`agent_budget_exhausted` | 由 Harness 决定降级或拒绝 |
| tool | `tool_failed`、`tool_not_allowed` | 由 Agent/Harness 既有规则决定 |
| evaluation | `evaluation_failed`、`prompt_injection_blocked` | Harness 降级或拒绝 |
| publication | `typed_output_build_failed` | Manifest 终态存在，但 Runtime 无 typed output |
| observability | `trace_persistence_failed`、`event_budget_exceeded` | 不改写已存在的 Harness 终态 |

未知异常不把类名、message 或响应正文写入 Trace，只映射为所在阶段的安全
`*_failed`。外部事件订阅者抛错不得中断核心领域执行；Runtime 自己的 Recorder/Store
失败则必须显式进入 observability failure，不能静默吞掉。

## 11. 非功能要求

### 11.1 安全

- Event payload 采用强类型 allowlist；
- Trace 不保存 Prompt、正文、Tool data、异常或 request ID；
- 路径继续复用共享安全 run ID；
- 新增测试扫描 secret marker、raw body 和不允许字段；
- 未信任用户数据永远不能直接决定 event kind、policy 或 Trace 路径。

### 11.2 可靠性

- 每次运行恰好一个 `run_started` 和一个 Runtime terminal event；
- sequence 从 1 严格递增，terminal 后不能再有事件；
- 事件数量受可信 Runtime policy 限制，初版默认上限需覆盖 Manifest 最大 Loop/Harness
  路径，并通过边界测试；
- Trace 使用原子 replace，不覆盖已存在的不可变终态 Trace；
- V1 没有 crash recovery、分布式锁或跨进程幂等承诺。

### 11.3 性能

- `run()` 不增加网络调用；
- Recorder 只保存有界元数据；
- `stream()` 使用进程内队列，不引入 Kafka/Redis；
- 当前不承诺生产 p50/p95、吞吐或 SLA；阶段 5P/6 有真实 API 消费者后再测。

### 11.4 可维护性

- Observer 是可选端口，未提供时现有 Agent/Harness 行为不变；
- 中央 Recorder 负责 sequence、时钟和 schema，底层组件只产生领域信号；
- Provider、Tool、Skill、Harness 和 Runtime 名词及职责保持分离；
- Pi/Claude SDK/LangGraph 必须在 5F 用本合同做对照，不能反过来改写业务合同以迁就框架。

## 12. 怎样用测试证明，而不是只看代码存在

### 12.1 合同与安全测试

- 所有 Runtime request/result/event/usage/trace 模型严格拒绝额外字段和非法枚举；
- event sequence、唯一 terminal、terminal 后禁止追加；
- payload 无法携带 Prompt/body/tool data/异常/request ID；
- run ID、相对 Artifact 引用和路径越界继续 fail closed。

### 12.2 Usage 测试

- 无 Provider call → observed zero / not applicable；
- 全部成功规范化 → complete totals；
- 成功 + 未观察失败 → partial，缺失部分不能折算为零；
- 只有未观察失败 → unknown/null；
- 无版本化价格表 → cost null；
- Decimal 定价可复现且绑定 profile version。

### 12.3 `run()` 纵向测试

两个真实 Skill 至少覆盖：

- Fake Provider + 真实本地 RAG + Harness published；
- Provider failure + deterministic degraded；
- Evaluation 拒绝；
- boundary/context 在 Harness 前失败；
- Tool failure、预算停止和 typed output 失败；
- 每条路径的 Runtime/publication 双终态和 Artifact hash 正确。

### 12.4 `stream()` 同源测试

在注入确定性时钟和 Fake Provider 后：

- 事件在执行期间可被消费，而不是结束后一次性出现；
- `run()` 与 `stream()` 除 wall-clock 外产生同样的安全事件语义；
- stream 最后一项中的 `RuntimeRunResult` 与同步运行合同相同；
- 慢消费者不会让事件无限增长，因为事件总数受预算限制；
- 消费者提前退出不等于 cancel，后台仍完成受限执行。

### 12.5 回归与门禁

- 现有 AgentLoop、ToolRuntime、Harness、Skill 两条链行为不变；
- 完整 pytest、两套 RAG、compileall、Harness SDK/tracked-data boundary、dry-run、
  governance 和 `git diff --check` 全部通过；
- 本地通过后提交、推送，并核验 exact-SHA GitHub Actions。

这些离线测试证明 Runtime 控制流、可观察性和安全边界，不证明真实商业模型领域质量。

## 13. 5E 原子实施顺序

5E 保持一个用户批准的子阶段组，内部按四个可验收检查点推进，避免一个大提交同时改变
合同、组件和流式并发：

### 5E-1 Runtime Contract、Usage 与 Trace Store

- 实现严格 request/result/signal/event/usage/trace 模型；
- 实现 Recorder、不完整 Usage 汇总与原子 Trace Store；
- 先用纯单元测试固定安全、不变量和存储语义；
- 尚不改 AgentLoop/Harness，不声称已有完整 Runtime。

### 5E-2 Observable `run()` 纵向切片

- 在 Runtime、AgentLoop 和 ReviewHarness 稳定接缝加入默认关闭 observer；
- 组合 boundary → context → executor；
- 让两个真实 Skill 的 Fake Provider + 本地 RAG + Harness 路径生成真实 Trace；
- 覆盖发布、降级、拒绝和 Harness 前失败。

### 5E-3 Live `stream()` 与 run/stream parity

- 复用同一个 `_execute()`，通过进程内 worker + queue 实时交付事件；
- 验证事件确实在运行中出现、顺序/终态唯一、结果合同相同；
- 不加入 cancel、SSE、跨进程 replay 或 Token chunk streaming。

### 5E-4 Runtime Evaluation 与退出审查

- 冻结 Runtime development/negative cases；
- 检查安全 Trace、Usage unknown Bad Case、资源上限和两个 Skill 纵向回归；
- 对照 5E 入口设计与 NFR，明确遗留问题；
- 只有通过后才进入 5P 早期 API 纵向切片。

每个检查点都需先讲清原理与范围，再 TDD、完整门禁、持久化更新、提交、推送和
exact-SHA CI；不得仅因代码提前存在就跳过验收。

## 14. 5E 明确不做什么

- 不选择或调用 GLM、DeepSeek、Qwen 等真实模型；
- 不重跑 5D held-out，不调整 Prompt，不把 unknown 改成 passed/failed；
- 不实现 FastAPI、网页或 SSE；这些从 5P 开始；
- 不实现 Session、Memory、SQL、continue/cancel/resume；这些属于阶段 6；
- 不实现标准 MCP；它属于阶段 7；
- 不实现 Multi-Agent、DAG、持久恢复或跨进程事件；它们属于阶段 8 或证据门后的高级能力；
- 不在 5E 采用 LangGraph、Pi、Claude Agent SDK；5F 才用已冻结的 Runtime 合同做对照实验。

## 15. 面试时可以怎样解释

可以说：

> 我没有在 Agent Loop 之外简单包一个日志器，而是把输入边界、Context、Provider、Tool、
> Harness 和 Artifact 的安全信号统一成版本化事件。同步 run 和流式 stream 复用同一执行
> 核心；Trace 只保存策略、版本、Usage 完整性、终止原因和 Artifact 哈希，不复制 Prompt
> 或正文。Harness 仍是唯一发布权，因此 Runtime 增强可观察性但不削弱质量门。

不能说：

- 已实现事件溯源、跨进程恢复或分布式调度；
- stream 已是模型逐 Token 输出；
- 已采用 LangGraph/Pi/Claude Agent SDK；
- Trace 中的未知 Token/费用等于零；
- Runtime 通过代表某个真实模型已通过领域质量门。

## 16. 入口设计验收结论

方案 B 同时满足当前真实需求、5D 已有资产、阶段边界和后续可替换性：它解决假流式、
失败归因和 Usage 失真，又不提前承担事件溯源、DAG、会话恢复或第三方 SDK 的复杂度。

因此接受“薄 Runtime + 可选观察端口 + 原子最终 Trace 快照”，并按 5E-1 至 5E-4 推进。
当前唯一下一步是 **5E-1 Runtime Contract、Usage 与 Trace Store**；它只建立合同和纯本地
基础设施，不读取 Key、不调用 Provider、不进入 5P/5F。
