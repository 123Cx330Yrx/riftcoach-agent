# 5F-entry-design：Pi-only Agent Runtime 采用实验设计

## 1. 本轮结论与边界

本设计把 5F 的候选从“Pi / Claude Agent SDK 并列”收缩为 **Pi-only**。这是用户确认后的
技术范围决策，不是 Pi 已被采用。

本轮只建立实验问题、架构接缝、指标、失败门和实施顺序：

- 不安装 Pi 或 Node 依赖；
- 不修改 `app/runtime`、`app/agent`、`app/harness` 或产品 composition root；
- 不读取 `.env`、模型 Key、Riot 数据，不调用 Provider，不运行真实模型；
- 不把 Pi 接入 FastAPI、Application Service 或默认 Runtime；
- 不实现 Claude Agent SDK；它只作为书面替代方案记录。

## 2. 给初学者的核心问题

我们现在的 Agent 并不是一句 Prompt，而是一条运行链：

```text
Prompt/Context
→ AgentLoop 决定是否调用 Tool
→ ToolRuntime 执行白名单 Tool
→ 模型读取 Tool Observation 并继续
→ ReviewHarness 评测/修订/发布
→ AgentRuntime 记录 Usage、Trace 和终态
```

5F 不问“Pi 生成的文字是不是更聪明”，因为那会把模型、Prompt、工具和 Runtime 一起换掉。
5F 先问：

> Pi 能否承担 AgentLoop 的运行职责，同时保留我们已经搭好的 Skill、Tool、Harness、Trace、
> 错误和安全发布合同？

这就是 Runtime 采用实验，而不是模型评测，也不是 Multi-Agent 实验。

## 3. 为什么 Pi 比 Claude Agent SDK 更适合作为唯一候选

Pi 官方项目由 Agent Core 与多 Provider LLM 抽象组成，方向上接近我们当前想审计的 Loop/Tool
运行时；Claude Agent SDK 则把 Claude Code 的内置工具、权限、Hooks、Sessions、Subagents 和
MCP 一并带入。后者当然可能很强，但它会同时改变模型厂商和产品能力边界，无法在当前阶段形成
干净的 Runtime 对照。

Pi 的风险也必须正面写出：官方核心是 TypeScript，而 RiftCoach 是 Python。因而 Pi 的实验不能
只看 Agent Loop 是否跑通，还要测：

```text
Python 主进程
↔ Node/Pi sidecar 或隔离实验进程
↔ Agent events / Tool results / terminal result
```

如果跨语言边界抵消了 Runtime 的维护收益，`reject` 是正确结果。

## 4. 不变的 RiftCoach 外层合同

Pi 实验不能接管以下职责：

| 外层合同 | 仍由 RiftCoach 负责 | 原因 |
|---|---|---|
| Product Request | `RecentReviewProductRequest` 与 typed compiler | 外部输入不能泄漏 Runtime 内部合同 |
| Domain | Summary 与确定性报告 | LoL 事实不是第三方 Runtime 的职责 |
| Prompt Program | Skill/Context/Knowledge/Evaluation/Revision identity | 保证 Prompt provenance 和 drift gate |
| Quality Gate | `ReviewHarness` 唯一评测/修订/发布权 | SDK 不能绕过质量门直接发布 |
| Receipt/Query | Trace、manifest、Artifact、receipt/query | 产品查询与完整性属于 RiftCoach |
| HTTP | FastAPI/Application Service | SDK 不能成为第二个产品编排器 |

Pi 只被允许竞争中间这一小段：

```text
当前 AgentLoop + Tool orchestration
          ↕
Pi Agent Core + 受限 Tool adapter
```

## 5. 建议的实验数据流

### 当前基线

```text
RecentReviewApplicationService
→ RuntimeCompositionRoot
→ AgentRuntimeV1
→ AgentLoop + ToolRuntime
→ ReviewHarness
→ Trace / Artifact / receipt
```

### Pi 隔离候选

```text
同一 Application/Compiler/Prompt/Context
→ PiAdapter（实验边界）
→ Pi Agent Core
→ 只读 knowledge.search adapter
→ PiAdapter 规范化 Agent terminal / Usage / events
→ 同一个 ReviewHarness
→ 同一 Trace/receipt 投影合同
```

如果 Pi 只能产生一段最终文本，却无法提供可验证 Tool、Usage、错误和终态观察，那么它最多是
模型调用包装器，不能作为当前 AgentRuntime 的候选替代。

## 6. 5F 内部实施顺序（待本设计公共闭环后逐项授权）

### 5F-1 Pi Source / License / Contract Audit

- 固定官方仓库 commit、包版本、许可证和运行环境；
- 阅读 Agent Core、Provider abstraction、Tool API、event/state、abort/timeout 和 usage 接缝；
- 记录官方 TypeScript/Node 边界；
- 不以非官方 Python port 代替官方源码证据。

### 5F-2 Offline Protocol Adapter Spike

- 用同一 frozen `recent-form-review` 输入和 Context；
- 只注册只读、幂等的 `knowledge.search`；
- 先使用 Fake/Scripted Provider，不读 Key；
- 把 Pi events/tool results/terminal 映射为 RiftCoach 可观察合同；
- 不进入主产品依赖。

### 5F-3 Contract / Security / Harness Evaluation

- 对比 tool whitelist、迭代/调用预算、Context ceiling、deadline、structured output、错误和
  terminal parity；
- 验证 unauthorized tool、重复 ToolCall、坏输出、Tool failure、Pi process failure 是否 fail closed；
- 验证现有 ReviewHarness 仍是唯一发布权；
- 记录 Python↔Node 进程开销、构建复杂度、日志/Trace 丢失和调试成本。

### 5F-4 Bounded Real Slice（如前置门通过且再次授权）

- 只有 5F-1 至 5F-3 通过且资源/安全合同可达，才设计真实 Provider 调用；
- 使用同一模型、同一 Prompt/Context、同一 Tool、同一 Evaluation 与同一停止规则；
- 真实结果只能评价 Runtime 适配和运行成本，不能把单次报告当作普遍质量结论。

### 5F-5 Adoption Decision / Exit Review

- `adopt`：证据显示 Pi 可安全承接职责且维护收益明确；
- `partial-adopt`：只吸收某些设计或保留隔离 adapter；
- `reject`：语义覆盖不足、跨语言成本过高或安全合同无法保持；
- 任何结论都要写 ADR，并明确主线是否改变。

## 7. 必须冻结的评测维度

| 维度 | 需要证明的行为 | 失败含义 |
|---|---|---|
| Tool safety | 只调用 manifest 允许的 `knowledge.search` | 不能进入采用候选 |
| Loop parity | 相同 scripted responses 下，调用顺序、停止、重复和预算一致 | 需要 adapter 或 reject |
| Structured output | 能得到当前合同可验证的 JSON/typed terminal | 只能算 text wrapper |
| Failure semantics | Provider/Tool/Pi 进程失败不绕过 Harness，能 deterministic degrade | 不得接入产品 |
| Observability | 能保留 event sequence、Usage completeness、terminal reason 和安全错误 | 无法接现有 Runtime/Trace |
| Harness boundary | 发布仍只由 ReviewHarness 决定 | 直接 reject |
| Integration cost | Node sidecar、IPC、构建、日志、部署和调试可量化 | 可能抵消收益 |
| Maintenance benefit | 有可复现的 Runtime 维护面减少或能力补足 | 没有理由替换自建实现 |

强制安全项不是平均分：任何未授权 Tool、unsafe publication 或终态绕过都属于硬失败。

## 8. 成功标准与退出门

入口设计阶段只冻结评测方法，不提前编造通过率。真正开始 5F-2 前必须补齐：

- Pi 源码/包版本/许可证的可复现身份；
- adapter 输入输出和 event/usage/error 白名单；
- 与当前 baseline 一致的 scripted cases；
- 资源上限、进程超时和失败后停止规则；
- 结果中哪些是 protocol evidence，哪些才是 real model evidence；
- 最终 `adopt / partial-adopt / reject` 的判定阈值。

## 9. 面试表述

可以这样解释：

> 我没有为了简历同时堆 Pi 和 Claude Agent SDK。5F 把问题收窄为一个可归因的 Runtime 采用实验：
> 用同一近期复盘切片、同一 Tool、同一 Harness 和同一 Trace 合同，对比自建 Python AgentLoop
> 与 Pi Agent Core。Claude Agent SDK 被书面筛除，是因为它会同时引入 Claude 模型和完整 Claude
> Code Harness，不能回答纯 Runtime 替换问题。实验最终可以采用、局部吸收或拒绝 Pi。

## 10. 当前下一步

本设计完成并经 exact-SHA 公共 CI 后，canonical 只交接到
`5F-1-pi-source-license-contract-audit`，等待下一次明确继续；本轮不安装 Pi、不写 adapter、
不读取 Key、不调用 Provider。
