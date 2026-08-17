# ADR-0036：5F-3 使用评测专用 Pi→Harness 适配层

- 状态：Accepted for evaluation only
- 日期：2026-08-17
- 范围：`5F-3-contract-security-harness-evaluation`

## 背景

5F-2 已证明官方 Pi Agent Core 0.84.2 可以在隔离 Node sidecar 中运行受限 loop，并把
`knowledge.search` 调回 Python `ToolRuntime`。但它没有证明 Pi 能保持 RiftCoach 的完整
Agent、Harness、Trace、Usage 和 Artifact 合同。

本阶段需要同时避免两个错误：一是只写文档对照，缺乏真实纵向证据；二是为了取得证据直接把 Pi
接入主 `AgentRuntimeV1` 或产品 composition，使实验污染默认路径。

## 比较的方案

### 方案 A：只做静态合同表

成本最低，但无法证明 Pi 草稿能否经过现有 Harness、typed output 和 Artifact 完整性门。拒绝。

### 方案 B：直接把 Pi 接入主 AgentRuntime

可以得到最接近产品的结果，但会在采用决策前修改默认 Runtime、错误枚举和部署路径，也违反 5F-3
隔离边界。拒绝。

### 方案 C：评测专用 DraftPreparer + 严格 Signal projector

使用评测命名空间中的 adapter 把 Pi 成功结果降格为现有 `AgentDraftPreparationResult`，通过现有
`SkillReviewExecutor` 和唯一 `ReviewHarness` 运行；另用严格 projector 检查安全事件能否进入现有
Runtime Signal/Recorder。无法无损表示的终态必须显式拒绝，不能近似映射。采用。

## 决策

1. 新代码只位于 `app/evaluation/pi_runtime/` 和对应测试，不加入主 Runtime、FastAPI 或默认
   composition。
2. Python controller 可新增一个进程内 detailed result，临时保留本次真实 `ToolExecutionRecord`；
   公共 `PiSpikeRunResult` 仍只保存 body-free projection，不保存 query、chunks 或 Tool body。
3. Pi adapter 必须先使用现有 `AgentRunCompiler` 校验 Skill identity、Tool allowlist、迭代、Tool、
   deadline 和初始 Context 合同，然后才构造 sidecar request。
4. Pi 文本永远只是 `CoachDraft`。只有现有 `ReviewHarness` 可以写入 producer 为
   `review_harness.publisher` 或 `review_harness.deterministic_fallback` 的 final Artifact。
5. 安全事件可以补充逐调用 token 数字，以支持 completeness-aware Usage；不得加入 Prompt、消息、
   Tool 参数/结果、原始异常、request ID 或 secret。
6. Signal projector 只做无损映射。`provider_aborted`、`tool_failed`、`protocol_error`、
   `process_error` 等当前 Runtime Agent terminal 无法表达的结果必须返回明确 parity gap。
7. 5F-2 的字符 Context 门不能冒充现有 token-unit ceiling。5F-3 将其记录为硬合同差异，不在本阶段
   复制 Python sizer 到 JavaScript，也不扩展生产 Runtime 合同。
8. 本 ADR 只决定评测结构，不作 `adopt / partial-adopt / reject` 最终裁决；最终裁决仍属于 5F-5。

## 后果

### 正面

- 能用真实现有 Harness、typed output 和 Artifact Store 验证唯一发布权；
- 兼容路径与不可兼容路径都由可执行测试固定，不会为了“实验成功”而伪造 parity；
- 主 Runtime 和产品 composition 保持不变，Pi 失败不会影响现有产品切片；
- detailed Tool body 只存在于单次 Python 进程对象，安全 Trace/Result 继续 body-free。

### 负面

- 需要维护额外 adapter、逐调用 Usage 投影和跨语言测试；
- sidecar 事件当前是运行后批量投影，能证明顺序合同但不能提供真实实时 Trace 延迟；
- Context 单位和部分失败终态仍可能阻止 Pi 进入 5F-4；
- 成功 Scripted/Fake 纵向切片仍不能证明真实模型质量。

## 安全与非功能要求

- 外部 Provider、Riot、Key 和 held-out I/O 必须为 0；
- 子进程继续使用 allowlisted environment、限长 JSONL、总 deadline 和 terminate/kill；
- Artifact 必须经现有 SHA-256 校验后才能投影到 Trace；
- 每 run 新进程、Node/npm 构建、依赖树、日志和调试成本必须进入退出矩阵；
- 任一 unauthorized Tool、unsafe final Artifact 或伪造终态都属于硬失败，不能用平均分抵消。

## 参考

- ADR-0034、ADR-0035
- `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`
- `docs/plans/2026-08-17-5f2-offline-protocol-adapter-spike-exit-review.md`
- `docs/plans/2026-08-17-5f3-contract-security-harness-evaluation.md`
