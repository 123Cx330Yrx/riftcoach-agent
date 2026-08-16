# ADR-0029：采用薄且可观察的 AgentRuntime V1

## 状态

Accepted；5E-2 的观察合同与终态提交细节由 ADR-0030 深化

## 日期

2026-08-15

## 背景

5D 已实现受限 Agent Loop、真实 Tool evidence、唯一 ReviewHarness 和 Artifact 驱动的
typed terminal output，但 run identity、Provider/Tool 状态、Usage、Harness transition
和 Artifact 引用分散在不同对象中。现有 `SkillReviewExecutor.execute()` 是同步组合；若
只在最外层包装，`stream()` 只能事后回放，无法表达实时进度或精确失败位置。

5D 的真实 Provider 负面实验还证明：请求已发出但没有规范化 Usage 时，实际 Token 与
费用应为 unknown，不能用默认零值代替。阶段 5E 必须统一 `run/stream/event/trace/usage`，
同时保留 ReviewHarness 的唯一发布权，并为 5F 的第三方 Runtime 比较建立框架中立基线。

## 决策

1. 实现框架中立的薄 `AgentRuntimeV1`，复用现有 `SkillExecutionRequest`、Boundary、
   ContextBuilder、AgentLoop、ToolRuntime、SkillReviewExecutor 和 ReviewHarness；
2. Router 保持在 Runtime 外，Runtime 必须重新验证已选择 Skill 的完整执行边界；
3. 内部只保留一个 `_execute(request, event_sink)` 控制流，`run()` 和 `stream()` 均复用它；
4. 在 AgentLoop 和 ReviewHarness 稳定接缝增加默认关闭的安全 observer；底层只发类型化
   `RuntimeSignal`，中央 Recorder 负责 sequence、时间和 `RuntimeEvent` schema；
5. `stream()` V1 通过进程内 worker/queue 交付实时状态事件，最终项使用与 `run()` 相同的
   `RuntimeRunResult`；它不是事后回放，也不是模型逐 Token streaming；
6. 新增 completeness-aware Runtime Usage，显式区分 complete、partial、unknown、
   not_applicable；没有完整 Usage 或版本化价格表时 Token/费用保持 null；
7. 新增独立 Runtime Trace Store，以原子 replace 保存最终安全 Trace；Trace 只含身份、
   版本、policy provenance、事件、Usage、终态与 Artifact 引用/哈希，不含 Prompt、正文、
   Tool data、原始异常、request ID 或秘密；
8. Runtime 状态与 Harness publication 状态分开，Harness 继续是唯一发布权；
9. 5E 不实现 durable event log、事件溯源、SSE、cancel/resume、DAG、Multi-Agent 或
   LangGraph/Pi/Claude Agent SDK；这些能力仍按 5P、5F、阶段 6/8 的既定门推进；
10. 5E 内部依次执行 5E-1 合同/Usage/Store、5E-2 observable run、5E-3 live stream parity、
    5E-4 evaluation/exit review，每项单独验收并公开验证。

## 后果

### 正面

- 运行过程可以被未来 API/UI 实时消费，而不是结束后伪造事件；
- 已验证的 Agent/Harness 控制流和唯一发布权不被重写；
- Provider 失败、Tool 执行、评测与发布原因能以安全分类统一追踪；
- 未观察 Usage 不再被错误统计为零；
- 5F 可以用同一业务合同客观比较自建 Runtime 与第三方 SDK。

### 负面

- AgentLoop、Harness 等稳定组件需要新增并测试可选 observer 接缝；
- V1 stream 需要一个本地 worker，仍没有硬取消、背压协议或跨进程恢复；
- 最终 Trace 原子快照不能恢复进程崩溃前尚未提交的事件；
- Runtime 与 publication 双状态增加了一些合同复杂度，但避免了语义混淆。

### 中性

- 当前无领域 Provider 准入和模型质量 unknown 的结论不变；
- 不增加真实模型调用、默认模型切换或新基础设施；
- EchoMind、Saber 与 Sea 继续只作为选择性参考；
- Prompt Program、产品 API、Session/Memory、MCP 和 Multi-Agent 的阶段顺序不变。

## 备选方案

### 只在 `SkillReviewExecutor` 外包装

拒绝。实现简单，但无法在 Provider、Tool 和 Harness 执行期间发出真实事件，`stream()`
只能事后回放，也会继续丢失中途失败的安全 provenance。

### 立即改为事件溯源或 DAG Runtime

拒绝。当前没有跨进程恢复、并发任务图或 durable replay 的产品 Bad Case；该方案会复制
ReviewHarness 状态机，并要求同时处理幂等、租约、事件迁移与消费者偏移。

### 立即采用 LangGraph、Pi 或 Claude Agent SDK

拒绝。采用前还没有 RiftCoach 自己冻结的 Runtime 基线与对照指标；5F 才依据具体 Bad
Case 比较能力、侵入性、成本和可移植性。

## 参考

- `docs/plans/2026-08-15-agent-runtime-v1-entry-design.md`
- `docs/adr/0030-refine-runtime-observation-and-terminal-commit.md`
- `docs/plans/2026-08-15-5d-constrained-agent-loop-exit-review.md`
- `docs/roadmap_v1_3_amendment.md`
- `docs/architecture_capability_matrix.md`
- `docs/adr/0011-compose-skill-agent-loop-through-harness-preparation.md`
- `docs/adr/0028-close-5d7-without-domain-provider-admission.md`
