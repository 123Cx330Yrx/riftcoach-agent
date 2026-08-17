# 5F Pi-only Runtime 采用实验总退出审查

## 1. 最终结论

5F 的最终裁决是：

```text
partial-adopt-evaluation-assets-only
```

更完整、不会误解的中文是：

> RiftCoach 拒绝把 Pi 作为产品 Runtime；保留冻结、隔离、可由 CI 复现的 Pi 评测资产，并吸收其
> 严格协议和技术采用门方法。产品继续唯一使用自建 Python `AgentRuntimeV1`。

这不是折中话术。产品、实验和方法三层都有明确不同的生命周期。

## 2. 给初学者：我们到底测了什么

一个 Agent Runtime 不只是“调用模型”的函数。它必须控制：

```text
输入与 Context
→ 模型是否请求 Tool
→ Tool 是否有权限、是否超预算
→ Tool 结果怎样回到模型
→ 何时结束、为什么失败
→ Token/Usage 怎样累计
→ 事件能否实时观察
→ 草稿能否通过质量门发布
```

我们没有把 Pi 接到产品后再看“能不能跑”。我们先把同一个 `recent-form-review` 切片放进隔离
sidecar，用 Scripted StreamFn 排除模型随机性，再让 Tool 请求回到 Python `ToolRuntime`，最后把
草稿送进原 `ReviewHarness`。

因此实验回答的是 Runtime 合同，不是模型聪明程度。

## 3. 5F 各检查点完成了什么

### 5F-entry-design

把候选收缩为 Pi-only，Claude Agent SDK 只作书面排除；冻结同输入、同 Tool、同 Harness、
adopt/partial-adopt/reject 和真实调用前置硬门。

### 5F-1 Source / License / Contract Audit

确认官方来源为 `earendil-works/pi` v0.84.2、MIT、Node `>=22.19.0`，并逐项映射 Agent、Provider、
Tool、event、state、abort 和 Usage。结论只是允许进入隔离 spike。

### 5F-2 Offline Protocol Adapter Spike

实现 exact lockfile、版本化限长 JSONL、Node sidecar、Python controller、真实本地知识 Tool、
整批预检、deadline/kill、Usage 四态和安全事件。裁决 `pass-with-boundaries`。

### 5F-3 Contract / Security / Harness Evaluation

让 Pi 草稿真实经过现有 Harness/typed output/Artifact，并把成功事件投影进现有 Recorder/Trace。
同时发现三项 hard gap：Context 计量、扩展终态、live timing/stream。裁决
`harness-compatible-but-runtime-gate-failed`。

### 5F-4 Bounded Real Slice

没有进入。它是条件分支，不是漏做。真实模型调用不能修复三项结构性差异，因此信息增益为零。

### 5F-5 Adoption Decision / Exit Review

ADR-0037 将产品 Runtime、评测资产和设计方法分开裁决；本审查与 exit matrix 固定长期边界和
重新开启/归档条件。

## 4. 为什么不是完整采用

如果把 Pi 接入产品，至少还要：

1. 在 JavaScript 复制并长期同步 Python Context sizer；
2. 扩展或转换生产 Runtime 终态，并重新验证所有失败语义；
3. 实现在线 event bridge、背压、取消、observer fail-fast 和双终态；
4. 部署 Python + Node，处理 IPC、日志、进程生命周期和供应链；
5. 继续维护 Pi adapter 对 Skill、transcript、evidence、Usage 和 Trace 的重建。

这些正是现有 Python Runtime 已经完成的职责。候选没有减少维护面，反而增加第二套实现，因此产品
采用的净收益为负。

## 5. 为什么不把代码全部删除

只保留一篇“我们试过但没采用”的文档，别人无法验证。当前冻结资产能证明：

- 官方版本和依赖身份；
- sidecar 确实运行过；
- Tool/Harness/Trace 不是纸面对照；
- 不兼容路径确实 fail closed；
- GitHub 公共 CI 能在干净环境复现。

这对学习、面试和架构可信度有价值。当前隔离 CI 成本仍可控，因此保留；若未来安全、兼容、稳定性
或成本触发 ADR-0037 的归档条件，再删除可执行依赖而保留历史证据。

## 6. 最终产品与实验数据流

### 产品路径

```text
HTTP request
→ RecentReviewApplicationService
→ Product compiler / Prompt Program
→ Python AgentRuntimeV1
→ Python AgentLoop + ToolRuntime
→ ReviewHarness
→ Trace / Artifact / receipt
```

### 冻结实验路径

```text
Scripted test fixture
→ evaluation-only Pi adapter
→ isolated Node/Pi sidecar
→ Python knowledge.search
→ existing ReviewHarness / strict Signal projector
→ parity assertion
```

产品路径没有 Pi 分支，也没有用户选择 Runtime 的开关。

## 7. 测试与证据怎样支持结论

5F-3 的已公开证据为：

- Pi/Harness/Trace 聚焦：45 passed；
- 相邻 Agent/Compiler/Tool/Harness/Runtime/Pi：196 passed；
- 完整：929 passed、1 个既有 FastAPI warning、110 subtests passed；
- 两套 RAG、compileall、Node syntax/tree、Harness boundary、tracked secret/run-data、dry-run、
  governance 和 diff 门禁通过；
- 提交 `3d9a081...` / Actions `32025522606` exact-SHA 成功；
- 真实 Provider、Riot、Key、held-out I/O 为 0。

5F-5 已重新运行本地门禁：Pi 聚焦 `45 passed`；完整回归
`929 passed, 1 warning, 110 subtests passed`；development 与 independent RAG 的全部指标达到
`1.0`，no-answer FPR 为 `0.0`；Node exact tree、compileall、governance、Harness dry-run、SDK/
tracked-data boundary 和 diff check 均通过。唯一 warning 仍是既有 FastAPI TestClient 的
Starlette/httpx 迁移提示。

这些结果证明最终文档/生命周期裁决没有破坏代码，也证明冻结实验仍可复现。测试通过不会把 hard
gap 变成 pass；这些差异被特意保留为拒绝证据。本检查点没有读取 Key，外部 Provider、Riot 和
held-out I/O 为 0。

## 8. 当前限制与 deferred 边界

- 当前没有任何领域 Provider 获得产品准入；GLM-5.2 仍只是开发基线；
- Pi 真实模型质量、生产并发/延迟、Session、恢复和公网部署均 unknown；
- 阶段 6 的 SQL、用户隔离、Session、Memory、SSE、鉴权和前端尚未实现；
- 阶段 7 标准 MCP/动态 Meta、阶段 8 Multi-Agent/DAG/恢复/产品化尚未实现；
- 保留 Pi CI 意味着继续承担额外开发供应链面，但不增加生产依赖；
- 未来框架或 Pi 新版本不能继承本次 0.84.2 结论，必须重新经过采用门。

## 9. 5F 退出条件核对

| 条件 | 状态 | 证据 |
|---|---|---|
| 官方身份/许可证/依赖审计 | 满足 | 5F-1 / `5901b09` / Actions `32016852979` |
| 隔离协议与 Tool 往返 | 满足 | 5F-2 / `f62f078` / Actions `32022258177` |
| Harness 唯一发布权 | 满足 | 5F-3 vertical tests |
| Usage/Trace/Artifact 成功路径 | 满足 | 5F-3 projector/Recorder tests |
| 强制 Runtime parity | 不满足，已正确阻断采用 | Context/terminal/live timing hard gaps |
| 真实切片是否必要 | 不必要，正确未进入 | 无法修复结构差异、无信息增益 |
| 维护/依赖/进程成本 | 已量化 | 94 packages / 约 62 MB / 约 0.4 秒进程 |
| 最终采用与资产生命周期 | 满足 | ADR-0037 |
| 产品主线是否清楚 | 满足 | Python Runtime 唯一默认，阶段 6 不使用 Pi |
| 本地与 exact-SHA 公共门禁 | 满足 | 45 focused、929/110 全量与全部本地门禁通过；`f8dea66` / Actions `32028206103` exact-SHA 公共成功 |

## 10. 对阶段 6 的交接

5F 公共闭环成功后，唯一下一检查点是既有路线中的 `6A-entry-design`。它只负责重新审计 5P 的
同步文件切片与阶段 6 的 FastAPI/SQL 任务模型缺口，先设计后实现。

交接不代表自动开始 6A，也不预先冻结阶段 6 的全部微观拆分；更不把 Pi、Claude Agent SDK、
LangGraph、Multi-Agent、MCP 或模型分层带入 6A。

## 11. 面试时怎样准确表述

可以说：

> 我们在已有 Python AgentRuntime 上，对官方 Pi 0.84.2 做了隔离 Runtime 采用实验。通过版本化
> JSONL sidecar，把 Pi 的 Tool 请求交回 Python ToolRuntime，再让草稿经过原 ReviewHarness 和
> Runtime Recorder。实验确认工具安全、发布门和成功 Trace 可适配，但发现 Context 计量、失败终态
> 和实时事件三项硬差异；跨语言依赖和进程成本也没有换来维护收益，所以在真实模型调用前停止，
> 拒绝产品采用。我们保留冻结、CI 可复现的评测资产，让这个负面结论可验证。

不能说“项目基于 Pi”“实现双 Runtime”“Pi 模型效果更差”或“真实调用证明 Pi 不行”。

## 12. exact-SHA 公共闭环

最终采用/退出提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已由 GitHub Actions run
`32028206103` 完成 exact-SHA 公共验证。5F-5 与整个阶段 5 正式关闭；canonical 只交接到
`6A-entry-design` 准备状态，等待用户明确继续，不自动实施阶段 6。
