# 5E-2：Observable `run()` 纵向切片设计

## 1. 结论先行

5E-2 将实现 RiftCoach 第一个统一同步运行入口：

```text
RuntimeRunRequest
  → SkillExecutionBoundary
  → ContextBuilderV1
  → 受限 AgentLoop + 业务 Tool
  → ReviewHarness 评测 / 有界修订 / 唯一发布
  → typed Skill output
  → 安全 RuntimeTrace
  → RuntimeRunResult
```

它不是再造一套 Agent，也不是把现有步骤改写成 LangGraph。它只是把 5D 已验证的组件
组合为一个可观察的 `AgentRuntimeV1.run()`，并保证每个事件来自真实执行时刻，而不是任务
结束后根据结果猜出来。

本轮源码审计发现：**Provider 调用不只发生在 AgentLoop**。Harness 的 Evaluation、
Evaluation repair 和 Revision 都会通过 `ToolRuntime("llm.chat")` 调用同一个 Provider。
所以最终采用：

```text
run-scoped ObservedLLMProvider
  ├─ 供 AgentLoop 使用
  └─ 供 Harness 的 llm.chat 使用

AgentLoop observer
  └─ 只记录模型主动选择的业务 Tool 和 Agent 终态

ReviewHarness observer
  └─ 只记录已成功持久化的状态、评测和发布事实
```

这样 RuntimeUsage 才能包含 Agent、Evaluation、repair、revision 的所有 Provider 边界
调用；同时 `llm.chat` 不会被重复算成 Agent 的业务 Tool。

5E-2 仍只用 Fake Provider + 真实本地 RAG + 真实 Harness 做离线纵向测试，不读取 Key、
不调用真实 Provider、不调整 Prompt、不实现 `stream()`。`stream()` 仍属于 5E-3。

## 2. 初学者先理解：我们现在究竟缺什么

### 2.1 5D 已经有“会做事的零件”

当前代码已经能完成：

```text
选定 Skill
→ 校验输入和 Artifact 哈希
→ 构造最小 Context
→ 模型决定是否调用 knowledge.search
→ 形成未发布草稿
→ 独立事实评测
→ 必要时有限修订
→ published / degraded / rejected
```

但是调用方仍要自己分别认识 `SkillExecutionBoundary`、`ContextBuilderV1`、
`SkillReviewExecutor`、`RunManifest` 和 Artifact Store。对未来 API 来说，这还不是一个
统一的“运行一个 Agent 任务”接口。

### 2.2 Runtime 解决的是整次任务的控制与观察

AgentLoop 只负责模型和工具之间的循环。Runtime 负责更外层的问题：

- 一次任务从哪里开始、在哪里结束；
- 当前处于 Boundary、Context、Agent、Evaluation 还是 Publication；
- 实际调用了几次 Provider 和业务 Tool；
- Token/费用是完整、部分、未知，还是没有调用；
- 最终报告究竟 published、degraded 还是 rejected；
- 哪些 Artifact 是这次运行的持久化事实；
- 失败时能否只暴露安全原因，而不泄漏 Prompt、正文和 SDK 错误。

所以 5E-2 的本质是：

> 用一条统一、可测试的控制流把已有组件接起来，并把真实发生的安全事实变成有序事件。

## 3. 本轮源码审计得到的真实调用图

### 3.1 Agent 草稿路径

```text
SkillReviewExecutor
  → _BoundAgentDraftPreparationStep
  → SkillAgentDraftPreparer
  → AgentLoop
      → provider.chat()
      → knowledge.search（若模型提出 ToolCall）
      → provider.chat()
  → Draft + KnowledgeEvidence
```

AgentLoop 在每轮 Provider 调用前做 Context、deadline 和 capability 检查；在执行 Tool 前，
先对整批调用做数量、白名单和重复检查。Observer 必须放在这些预检之后，否则会把没有
发生的副作用记成一次调用。

### 3.2 Harness 评测与修订路径

```text
ReviewHarness
  → SecureChatEvaluationAdapter
      → ToolRuntime.execute("llm.chat")
          → provider.chat()
  → 可选 evaluate_repair
      → ToolRuntime.execute("llm.chat")
          → provider.chat()
  → 可选 ChatCoachReviser
      → ToolRuntime.execute("llm.chat")
          → provider.chat()
```

因此只在 AgentLoop 发 `provider_call_*` 会漏掉后半段调用。漏记之后，Recorder 仍可能把
已观察到的少量响应标为 `complete`，这比“没有 Trace”更危险，因为它会给出一个看似
精确、实则不完整的成本结论。

## 4. 三种组合方案比较

### 方案 A：AgentLoop 和 Harness 各自直接记录 Provider

做法：AgentLoop 围绕 `provider.chat()` 发事件；Harness 在 Evaluation/Revision 外层估算
调用。

问题：Harness 外层不知道 `llm.chat` 的 ToolRuntime retry 实际调用了几次，也拿不到每次
真实 `ChatResponse.usage`。repair 和 retry 很容易被少算。

结论：拒绝。

### 方案 B：共享 Provider 装饰器 + 定点 Agent/Harness observer

做法：每次 Runtime run 创建一个 `ObservedLLMProvider`，用它包装同一个底层 Provider，
并同时交给 AgentLoop 与 Harness 的 `build_llm_tools()`。AgentLoop 只记录业务 Tool 和
Agent 终态；ReviewHarness 只记录持久化后的业务状态。

优点：

- 每次实际进入 Provider Adapter 的调用只有一个观察点；
- Agent、Evaluation、repair、revision 共用连续 Provider ordinal；
- ToolRuntime retry 的每次 Provider 尝试都会被记录；
- 不修改 Zhipu/DeepSeek 的厂商协议；
- 不会把内部 `llm.chat` 重复算成业务 Tool；
- observer 关闭时，现有组件行为不变。

结论：采用。

### 方案 C：给整个 ToolRuntime 增加全局 observer

做法：所有 `ToolRuntime.execute()` 都发 Tool 事件。

问题：Harness 把 Provider 包装成内部 `llm.chat` Tool；全局观察会让一次 Evaluation 同时
成为 Provider call 和“业务 Tool call”，污染 Skill Tool 使用量，也容易让人误以为模型
主动选择了 `llm.chat`。

结论：拒绝。Tool 事件只表示 Agent 经 Manifest 允许后主动请求的业务工具。

## 5. 冻结的 5E-2 架构

### 5.1 组合关系

```text
AgentRuntimeV1
  ├─ Boundary
  ├─ ContextBuilderV1
  ├─ trusted Runtime composition profile
  ├─ RuntimeExecutionFactory
  │    ├─ one ObservedLLMProvider
  │    ├─ AgentLoop(observed provider)
  │    ├─ business ToolRuntime(knowledge.search)
  │    ├─ Harness llm ToolRuntime(observed provider)
  │    └─ SkillReviewExecutor
  ├─ RuntimeRecorder
  └─ RuntimeTraceStore
```

`RuntimeExecutionFactory` 是普通依赖注入接缝，不是新框架。它的作用是保证同一次运行中的
Agent 和 Harness 使用同一个 observed Provider 与同一个 signal observer，避免可变全局
observer、线程串线或事后替换私有字段。

### 5.2 身份来源

Trace 身份不能从用户正文猜测：

| 身份 | 可信来源 |
|---|---|
| run_id | 已有安全 `SkillExecutionRequest.run_id` |
| Skill name/version | selected `RouterDecision`，Boundary 成功后再与 Catalog 对齐 |
| Context contract | `ContextBuilderV1` 版本常量 |
| Prompt profile | Skill 指令 profile，ID/version 由可信 composition profile 映射 |
| Provider/model | 实际被包装的 `LLMProvider.provider_name/model_name` |
| Harness version | `ReviewHarness` 版本常量 |
| Runtime policy | Runtime 自有 policy version + Skill Manifest/HarnessConfig 的真实预算 |

Router 仍在 Runtime 外。`RuntimeRunRequest` 只接受 selected 决策；rejected/ambiguous 是
Router 的正常结果，不应该伪装成一次 Agent run。Runtime 仍会重新执行 Boundary，因此
版本漂移、输入篡改和 Artifact 哈希不一致仍能形成 boundary failure Trace。

## 6. Observer 的职责和失败规则

### 6.1 低依赖端口

组件只认识一个默认关闭的端口：

```python
observer: RuntimeSignalObserver | None = None
```

它不进入用户 payload、Context、`AgentRunRequest.metadata`、Tool 参数或 Provider 请求
正文。`observer=None` 时，现有 AgentLoop、Harness 和 Executor 的返回值、调用次数和
发布行为必须逐字段不变。

### 6.2 Recorder 故障不能伪装成业务失败

内部 observer 是 Runtime 的可信 Recorder。它的异常统一包装为
`RuntimeObservationError`，并必须穿过以下宽泛捕获：

- Agent draft preparation；
- Harness draft/evaluation/revision；
- `_BoundAgentDraftPreparationStep`；
- `SkillReviewExecutor.execute()`。

如果不这样做，event budget 或 schema 故障可能被 Harness 写成
`draft_preparation_failed`，甚至发布 deterministic fallback。这会把“监控坏了”错误地
描述成“业务模型失败”。

5E-2 采用 fail-fast：

- started 事件在副作用前记录失败 → 不执行该 Provider/Tool；
- completed 事件在副作用后记录失败 → 停止后续业务步骤；
- 若 Harness 已形成 terminal Manifest，Runtime 保留已知 publication status；
- Runtime 不暴露 typed output，也不伪造完整 Trace。

5E-3 的外部 stream 消费者属于另一层。消费者回调失败应由 Runtime fan-out 隔离，不能
反向破坏 Recorder 或领域执行。

## 7. 各观察点的精确语义

### 7.1 Provider

`ObservedLLMProvider` 在 capability preflight 成功后、调用 delegate 前发 started；成功获得
规范化 `ChatResponse` 后发 completed；`ProviderError` 或未知异常则发 failed 并重新抛出。

Provider phase 使用 allowlist：

```text
agent | evaluation | evaluation_repair | revision
```

Agent phase 才携带 `iteration`；其他 phase 不伪造“第 1 轮 Agent”。phase 只从内部
`agent_loop_iteration` 或 `harness_step` 映射，不保存完整 metadata。

不进入事件：messages、Prompt、content、tool_calls、request_id、reasoning、异常文本。

### 7.2 Agent 业务 Tool

Tool started 位于整批数量、白名单和重复检查全部通过之后，紧邻
`ToolRuntime.execute()`；completed 使用 `ToolResult` 的安全 envelope：

```text
name/version/success/attempts/latency/cache/fallback
```

Tool 参数、结果 data、error message、call ID 不进入 Trace。ToolRuntime 的正常失败仍返回
`ToolResult(success=False)`，所以它是 completed，而不是基础设施异常。

当前 ToolRuntime 的公开合同会把 handler、输入/输出校验、retry、circuit breaker 和
fallback 的正常失败全部收敛为 `ToolResult`；因此 V1 不另造 `tool_call_failed`。失败的
`tool_call_completed` 增加安全 `failure_code`，并继续携带真实 attempts/latency。

若未来出现一个可复现的 ToolRuntime 契约外抛异常，届时必须把 `tool_call_failed` 与
Tool Usage completeness 一起设计，不能单独加一个 failed 事件却把未知 attempts 写成 0。
`llm.chat` 不计入这里，因为它不是 Agent 根据 Skill Manifest 主动选择的业务 Tool。

### 7.3 Agent 终态

5E-1 没有 Agent terminal Signal，导致 Context budget、timeout、max iterations、非法工具
等停止原因最终可能都折叠成 Harness 的 `draft_preparation_failed`。5E-2 增加一个安全的
`agent_run_terminated`：

```text
status + stop_reason + iterations + optional safe error code
```

它不等于 Runtime terminal。Agent 失败后 Harness 仍可能安全发布确定性 fallback，最终
Runtime 可以是 `completed + degraded`。

### 7.4 Harness

Harness 只在持久化事实成立后发事件：

- `harness_transitioned`：Manifest 写成功后；
- `evaluation_completed`：结构校验通过且 evaluation Artifact 注册成功后；
- `publication_decided`：terminal Manifest 写成功后。

第一轮 Harness `attempt_id=0`，Runtime Signal 直接保留这个真实 ID：

```text
evaluation attempt = manifest.attempt_id
```

这样 `evaluation_completed.attempt=0` 能直接对应
`evaluations/evaluation_attempt_0.json`，不会同时维护一套“人类第 1 次”和一套 Artifact
第 0 次编号。

`blocking_categories` 当前只投影真正触发阻断策略的 `prompt_injection`，不保存 quote、
summary、explanation 或 correction。

Harness reason 如 `evaluation_failed:RuntimeError` 只映射为冒号前的
`evaluation_failed`。published/degraded 的 publication 只引用唯一 final report SHA；
rejected 没有 final report，所以 SHA 列表为空。

## 8. 5E-1 合同必须显式修订的地方

这些不是推翻 5E-1，而是第一次接入真实消费者时发现的必要兼容修正。由于 5E-1 已公开
冻结，修订由 ADR-0030 记录，写入默认的 Event/Trace schema 从 `1.0` 升到 `1.1`。
读端继续接受合法 1.0 Trace，`RuntimeTraceReference` 的 schema version 必须与真实 Trace
一致。仓库目前没有任何已持久化 Runtime Trace，因此没有生产数据迁移或旧 Trace 被
覆盖的问题。

### 8.1 Provider phase 补全必填 Agent iteration

`ProviderCallStartedSignal` 保留字段名 `iteration` 以兼容 1.0，同时增加 phase 并允许
非 Agent phase 的 iteration 为 null：

```text
phase: agent | evaluation | evaluation_repair | revision
iteration: int | null
```

只有 agent phase 要求非空 iteration。

### 8.2 Context omission ID 允许安全冒号层级

真实 ID 包含：

```text
facts:recent_match:01
knowledge:citation:003
```

Signal 使用专门的安全 section-ID 正则允许冒号分段，而不是把真实 provenance 改写或
丢掉；空白、路径字符和任意正文仍被拒绝。

### 8.3 finish reason 使用有限枚举并保留 null

Provider 没有返回 finish reason 时保留 `null`，不伪造 `stop` 或 `unknown`；非空值只保留
`stop`、`tool_calls`、`length`、`content_filter`、`other` 等安全枚举，不直接持久化任意
厂商字符串。

### 8.4 增加 Agent terminal、Tool 失败码与 Harness failure stage

新增：

- `agent_run_terminated`；
- `tool_call_completed.failure_code`（仅 `success=false` 时存在）；
- `RuntimeFailureStage.HARNESS`。

Recorder/Trace 同时增加 Harness transition、Evaluation attempt、Publication 顺序不变量。

### 8.5 成功 ChatResponse 必须有真实观察到的 Usage

当前 Zhipu Adapter 在响应缺少 Usage 时返回 `TokenUsage(0, 0)`；这会把“未知”错误写成
“完整零值”。5E-2 将与 DeepSeek 对齐：

- `ChatResponse.usage` 变为调用方必须显式提供，不再用默认零值掩盖遗漏；
- Zhipu 缺失或非法 Usage 时抛安全 `provider_usage_unavailable`；
- 该安全码进入共享 Provider allowlist；
- Provider call 形成 failed，Recorder 据此得到 partial/unknown，而不是 complete zero。

这项修正不需要真实调用；用 Fake SDK 和 Provider 合同测试即可完成。

## 9. Runtime 与 Harness 双终态

| 实际情况 | Runtime | Publication | output |
|---|---|---|---|
| Boundary/Context 失败 | failed | null | null |
| Agent 失败，Harness 发布 fallback | completed | degraded | typed output |
| Evaluation 合法判 fail，Harness 降级 | completed | degraded/rejected | typed output |
| Harness 正常发布 | completed | published | typed output |
| terminal Manifest 已有，但 typed output 构造失败 | failed | 保留已知值 | null |
| Trace 持久化失败 | failed | 保留已知值或 null | null |

“Agent 失败”不自动等于“Runtime 失败”。Runtime 的成功标准是：已有 terminal Harness
真相、typed output 安全重建成功、最终 Trace 成功提交。

Runtime 的稳定失败映射：

```text
boundary      execution_validation_failed
context       context_build_failed
harness       harness_execution_failed
publication   typed_output_build_failed / artifact_integrity_failed
observability observation_failed / trace_persistence_failed
```

原始异常类名、message 和响应正文不进入 Signal、Trace 或 result reason。

## 10. 终态为什么要“准备—持久化—提交”

### 10.1 旧顺序的矛盾

如果这样执行：

```text
emit run_completed
→ Recorder 封口
→ build Trace
→ write Trace 失败
```

Runtime 最终只能返回 failed，但已发出的事件却说 completed；Recorder 又禁止追加
`run_failed`。5E-3 一旦实时输出事件，就会出现不可修复的自相矛盾。

### 10.2 冻结的新顺序

Runtime terminal 使用两阶段提交：

```text
1. prepare_terminal(signal)
   └─ 生成但不公开、不封口的 terminal candidate

2. build prospective Trace
   └─ Trace 使用同一个 candidate event

3. RuntimeTraceStore.write_trace()
   ├─ 成功：commit_terminal(candidate)，再对外发布 terminal event
   └─ 失败：取消 candidate，提交内存 run_failed(trace_persistence_failed)，不返回 Trace
```

commit 不再次读取时钟，也不重新创建事件，所以内存事件与已保存 Trace 的 sequence、时间
完全相同。单线程 `_execute()` 在 prepare 和 commit 之间禁止追加其他事件。

Trace 写失败时，Harness 已落盘的 terminal Manifest/Artifact 不会被改写；Runtime 只返回
failed、保留已知 publication status、不暴露 output、`trace_reference=null`。该次失败
终态可供 5E-3 的进程内消费者看到，但不会冒充已有 durable Trace。

## 11. Event budget 怎样避免在副作用中途耗尽

V1 不允许随意给一个过小 event budget 后再碰运气。Runtime 在任何 Provider/Tool 副作用
前，根据可信预算计算最坏事件数：

- Boundary/Context 基础事件；
- Agent `max_iterations` 的 Provider start/end；
- Agent `max_tool_calls` 的 Tool start/end；
- Evaluation、最多一次 repair、Revision 与 `llm.chat` retry；
- Harness transitions、Evaluation、Publication、Agent/Runtime terminal。

若 `RuntimePolicySnapshot.event_budget` 小于该上界，Runtime 在执行前以 policy failure 停止，
不进入 Provider 或 Tool。Recorder 还会为 Runtime terminal 保留一个位置；普通事件不能
吃掉最后一个 slot。当前全局上限下 256 能覆盖最坏 V1 路径；测试会固定计算公式，未来
增加 Signal、retry 或预算时必须显式更新，而不是等运行中爆掉。

## 12. Artifact 与 Trace

Runtime 从 terminal Manifest 投影 Artifact reference，但对每条记录都先调用
`FileRunStore.read_artifact()` 校验真实字节和 SHA-256。Trace 保存：

```text
kind + schema_version + relative_path + sha256 + producer
```

不保存正文，也不把 `manifest.json` 虚构成一个 Artifact record。若 Artifact 已篡改，
Runtime fail closed；无法形成自洽 Trace 时允许 `trace_reference=null`，不能为追求“总有
Trace”而登记未经验证的哈希。

## 13. 一个成功路径的事件顺序示例

```text
run_started
execution_validated
context_built

harness_transitioned        created → facts_ready

provider_call_started       phase=agent, iteration=1
provider_call_completed
tool_call_started           knowledge.search
tool_call_completed
provider_call_started       phase=agent, iteration=2
provider_call_completed
agent_run_terminated        completed/final_response

harness_transitioned        facts_ready → knowledge_ready
harness_transitioned        knowledge_ready → draft_ready
harness_transitioned        draft_ready → evaluating

provider_call_started       phase=evaluation
provider_call_completed
evaluation_completed        attempt=0
harness_transitioned        evaluating → passed
harness_transitioned        passed → published
publication_decided         published

run_completed               published
```

`facts_ready` 在 Harness 写入输入 Artifact 后、进入 draft preparation 前出现；Agent
provider/tool 事件发生在这次 preparation 内。测试将按这条真实交错顺序断言，不会在任务
结束后重排事件。

## 14. TDD 实施顺序

### Task A：合同 1.1 与 observation port

- 新 Signal/枚举、section ID、finish reason、Harness stage；
- `RuntimeObservationError` 与默认关闭 observer；
- Provider Usage 必填和 Zhipu missing-usage fail closed；
- Recorder/Trace 的新 lifecycle、Harness 顺序和 prospective terminal 红绿测试。

### Task B：Provider 与 AgentLoop 观察

- `ObservedLLMProvider`；
- Agent provider phase、连续 ordinal、safe error allowlist；
- Agent Tool start/completed/failed；
- Agent terminal；
- observer=None 完整兼容回归。

### Task C：Harness 与 Executor 观察

- 持久化后 transition/evaluation/publication；
- observer error 穿透所有 broad catch；
- attempt 0/1、blocking category、published/degraded/rejected；
- Artifact 引用投影与篡改失败。

### Task D：`AgentRuntimeV1.run()` 纵向切片

- 一个 `_execute(request, event_sink)` 核心，`run()` 调用它；
- Boundary、Context、execution factory、Recorder、Trace Store 组合；
- prospective terminal commit；
- 两个真实 Skill 的 published/degraded/rejected 与 Harness 前失败；
- Fake Provider + 真实本地 RAG + 真实 Harness；
- 不实现 `stream()`。

Task A-D 属于同一个 5E-2，不是新增主阶段。每批都先写失败测试，再最小实现；只有整个
纵向切片、完整门禁和 exact-SHA CI 通过后，5E-2 才能完成。

## 15. 重点测试矩阵

### Provider/Usage

- Agent 两轮 tool round-trip 的 Provider ordinal 与 phase；
- Agent + Evaluation + repair + Revision 使用同一连续 ordinal；
- Harness `llm.chat` retry 的每次 Provider 边界调用均可见；
- capability preflight 失败为零 attempted call；
- typed/unknown Provider failure 关闭 lifecycle 且不泄漏正文；
- Zhipu missing usage → failed/unknown，不是 complete zero；
- finish reason 缺失/未知使用安全枚举。

### Tool/Agent

- Tool success、正常 failure、cache、fallback、retry envelope；
- max calls、越权、重复批次在任何 Tool started 前停止；
- Tool 的正常失败仍是 completed(success=false + safe failure code)；
- 契约外 ToolRuntime 异常不伪造 attempts，记录为当前 V1 的显式限制；
- Context budget、timeout、max iterations、非法工具配置有 Agent terminal；
- 任何事件中不存在 arguments、data、call ID、request ID 或 error message。

### Harness/Runtime

- transition 只有在 Manifest 已写成目标状态后才出现；
- evaluation exception 不产生 evaluation completed；
- revision 路径 attempt 为 0、1；
- publication 与 terminal Harness transition 一致；
- Agent failure + fallback = Runtime completed + degraded；
- typed output failure = Runtime failed + publication known + output null；
- Boundary/Context failure 在 Harness 前形成可持久化失败 Trace；
- Trace write failure 不先公开 run completed；
- observer failure 不被 Harness 吞成业务 fallback；
- observer=None 的现有 Agent/Harness 行为逐字段不变。

### 纵向业务

- `recent-form-review`：Fake Provider + 真实 `knowledge.search` + Harness published；
- `single-match-review`：同一 Runtime 合同与正确 target identity；
- Provider failure + deterministic fallback；
- Evaluation fail / prompt injection blocking；
- Runtime Trace Artifact SHA 与真实落盘字节一致。

## 16. 明确不做什么

- 不调用 GLM、DeepSeek、Qwen 或其他真实模型；
- 不重跑任何 held-out，不改变当前领域模型质量 unknown；
- 不实现模型自动切换、多模型分层或 Multi-Agent；
- 不实现 `stream()`、SSE、Token streaming、cancel/resume；
- 不引入 LangGraph、Pi、Claude Agent SDK；
- 不实现 API、前端、Memory、SQL、MCP、DAG 或 durable event log；
- 不调整 Prompt 内容或 RAG 数据。

## 17. 本设计完成后项目处于哪里

本设计完成只表示 5E-2 的接线、合同修正、失败语义和 TDD 顺序已经冻结；
`AgentRuntimeV1.run()` 仍尚未实现。下一步是 Task A 的本地 TDD，而不是 5E-3、5P 或 5F。

面试时可这样解释本次设计判断：

> 我审计后发现 Provider 不只在 Agent Loop 中调用，独立评测和修订也会经 ToolRuntime
> 调模型。因此我用一次运行共享的 Provider decorator 统一观察真实 Provider 边界，
> AgentLoop 只记录 Manifest 允许的业务工具，Harness 只记录持久化后的质量门事实。
> Runtime 用两阶段 terminal commit 保证 Trace 写失败时不会先发成功事件，同时把未知
> Usage 保持为 unknown/null，而不是默认零。
