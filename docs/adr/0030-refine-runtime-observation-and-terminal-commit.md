# ADR-0030：修订 Runtime 观察合同并采用两阶段终态提交

## 状态

Accepted

## 日期

2026-08-16

## 背景

ADR-0029 与 5E-1 已冻结薄 Runtime、类型化 Signal、完整性明确的 Usage 和原子最终
Trace Store。5E-2 首次把这些合同对接真实 Agent/Harness 控制流时，源码审计发现：

1. Evaluation、Evaluation repair 和 Revision 通过 `ToolRuntime("llm.chat")` 调用
   Provider，只观察 AgentLoop 会漏记调用与 Usage；
2. `ProviderCallStartedSignal.iteration` 不能表达非 Agent Provider 调用；
3. 当前 Context omission ID 正则不接受真实的冒号层级 ID；
4. 当前事件族缺少 Agent terminal、失败 Tool completion 的安全码和一般 Harness failure；
5. Zhipu 缺失 Usage 时返回 `TokenUsage(0, 0)`，会把 unknown 误写为 complete zero；
6. 若先提交 `run_completed` 再写 Trace，写盘失败后无法改为诚实的 Runtime failure；
7. Recorder/Trace 尚未校验 Harness transition、Evaluation attempt 与 Publication 顺序。

这些问题在第一个 Runtime consumer 实现前必须修正，否则 5E-2 即使“能跑”也会产生不完整
或互相矛盾的 Trace。

## 决策

1. 每次 Runtime run 创建一个 `ObservedLLMProvider`，包装同一个底层 Provider，并同时供
   AgentLoop 与 Harness `llm.chat` 使用；Provider ordinal 和 Usage 在一个位置统一记录；
2. AgentLoop observer 只记录模型主动请求且通过整批预检的业务 Tool，以及安全 Agent
   terminal；不全局观察 ToolRuntime，不把内部 `llm.chat` 算成业务 Tool；
3. ReviewHarness 只在 Manifest/Artifact 成功持久化后发 transition、evaluation 和
   publication Signal；Harness 继续拥有唯一发布权；
4. 内部 observer 错误包装为 `RuntimeObservationError` 并穿透现有 broad catch，不能被
   Harness 误分类为业务 fallback；外部 stream consumer 隔离留在 5E-3；
5. Event/Trace 写入 schema 升为 `1.1`，读端保留合法 1.0 兼容；增加 Provider phase +
   optional iteration、安全 section ID、有限且可空 finish reason、
   `agent_run_terminated`、失败 Tool completion 的安全 failure code 和
   `RuntimeFailureStage.HARNESS`；
6. Evaluation attempt 直接使用零基的 `manifest.attempt_id`，与
   `evaluation_attempt_0.json` 一一对应；blocking category 只投影当前
   真正阻断策略的安全类别；
7. 成功 `ChatResponse` 必须显式携带观察到的 `TokenUsage`；Zhipu 缺失/非法 Usage 时与
   DeepSeek 一样 fail closed 为安全 `provider_usage_unavailable`；
8. Recorder/Trace 增加 Harness transition 连续性、Evaluation phase/attempt 和
   Publication/terminal 一致性检查；
9. Runtime terminal 使用 prepare → prospective Trace → atomic store → commit。只有 Trace
   成功持久化后才公开完成 terminal；写盘失败改为内存 observability failure，不改写已存在
   的 Harness terminal truth，也不返回 output/Trace reference；
10. Runtime 在 Provider/Tool 副作用前验证 event budget 能覆盖可信预算下的最坏事件数，
    Recorder 同时为 Runtime terminal 永久保留最后一个 slot。

## 为什么不是其他方案

### 只在 AgentLoop 记录 Provider

拒绝。会漏掉 Evaluation/repair/revision，Usage 可能错误标为 complete。

### 在 Harness 外层估算模型调用

拒绝。外层不知道 `llm.chat` retry 的实际 Provider 尝试次数，也拿不到每次响应 Usage。

### 全局观察 ToolRuntime

拒绝。会把 Harness 内部 `llm.chat` 误计为 Agent 根据 Skill Manifest 选择的业务 Tool。

### 先发 Runtime terminal，再处理 Trace 写盘错误

拒绝。它会让实时事件、最终 result 和持久 Trace 出现不可恢复的终态分裂。

## 兼容与迁移

- observer 默认关闭；未进入 AgentRuntime 的现有 AgentLoop、Harness 和 Executor 行为必须
  保持不变；
- 当前仓库没有已持久化的 Runtime Trace；新写入使用 1.1，读端仍检查并接受合法 1.0，
  Trace reference 与真实 Trace schema 必须一致；
- 5E-1 的提交与 CI 仍是历史地基证据，ADR-0030 明确记录首次真实接线前的合同深化；
- Provider/Prompt/模型选择、真实调用和 held-out 结论均不改变。

## 后果

### 正面

- Agent 与质量门全部 Provider 调用进入同一 Usage；
- Agent、Tool、Harness 和 Runtime failure 不再被一个模糊原因折叠；
- missing Usage 不会伪装成零成本；
- 5E-3 可以复用不会先成功后失败的 terminal 语义；
- ReviewHarness 的发布权与现有领域控制流不被重写。

### 代价

- 5E-2 Task A 需要先修订已公开但尚无消费者的 Runtime schema；
- 需要一个 run-scoped composition factory，确保同一 observed Provider 同时进入 Agent 和
  Harness；
- Observer 错误传播点、prospective terminal 和 event-budget 公式需要额外测试；
- Zhipu 的 missing-usage 历史测试必须改为 fail-closed 语义。

## 参考

- `docs/plans/2026-08-16-agent-runtime-v1-observable-run-design.md`
- `docs/adr/0029-adopt-thin-observable-agent-runtime-v1.md`
- `docs/plans/2026-08-15-agent-runtime-v1-entry-design.md`
- `app/agent/loop.py`
- `app/harness/runtime.py`
- `app/harness/adapters.py`
- `app/tools/adapters/llm.py`
- `app/runtime/`
