# 5F-3 Contract / Security / Harness Evaluation 退出审查

## 1. 本地裁决

本地裁决为：

```text
harness-compatible-but-runtime-gate-failed
```

准确含义是：Pi 可以在评测专用 adapter 中产生未发布草稿和实际知识证据，并安全经过现有
`SkillReviewExecutor → ReviewHarness → typed output → Artifact`；成功 Scripted 路径也能投影成
合法、body-free 的 RuntimeTrace。

但是，Pi sidecar 仍不能保持三项强制 Runtime 不变量：精确 Context 计量、完整 Agent terminal
vocabulary、实时事件时序。根据 ADR-0034 的采用门，任一强制合同条件失败都不能进入真实 Provider
切片。因此本地建议是：**5F-4 不准入，不花真实模型调用；公共 CI 成功后直接把证据交给 5F-5 做
最终 adopt/partial-adopt/reject 裁决。**

这不是说 Pi “不能用”，也不是模型质量差。它表示：在当前 Python 产品与现有 Runtime 合同下，
为了让 Pi 成为替代 Runtime，需要维护的跨语言 adapter 和语义补丁已经抵消了预期收益。

## 2. 真实纵向数据流

本阶段实际运行的是：

```text
ValidatedSkillExecution + ContextBundle
→ existing AgentRunCompiler
→ evaluation-only PiSkillDraftPreparer
→ PiSidecarController / official Pi Agent Core 0.84.2
→ Python ToolRuntime / real local knowledge.search
→ ephemeral ToolExecutionRecord
→ CoachDraft + KnowledgeEvidence
→ existing SkillReviewExecutor
→ existing ReviewHarness
→ typed RecentFormReviewOutput
→ immutable Harness Artifacts
```

Trace 对照使用：

```text
PiSafeEvent + PiSpikeRunResult
→ strict PiRuntimeSignalProjector
→ existing RuntimeRecorder
→ existing RuntimeTrace validation
```

评测 adapter 没有加入主 `AgentRuntimeV1`、FastAPI、Application Service 或默认 composition。

## 3. 完整 parity matrix

| 维度 | 结果 | 可执行证据 | 退出影响 |
|---|---|---|---|
| Tool whitelist/contract | exact pass | 5F-2 整批 unauthorized/Schema drift 测试；5F-3 仍先走现有 Compiler/Registry | 不阻断 |
| batch/duplicate | exact pass | batch 内、跨轮重复和失败 Tool 计数均在 Python Tool I/O 前停止 | 不阻断 |
| iteration/tool budget | exact pass | Python/Pi 同脚本成功与最后迭代零副作用；失败 Tool 也占预算 | 不阻断 |
| total deadline/process kill | adapter-covered | Python 持有总 deadline，child timeout 后 terminate/kill；不重置逐步 deadline | 不阻断，但 Tool handler 仍须合作 |
| Context ceiling | hard gap | 现有 Compiler 检查 deterministic token-unit；Node 另用 JSON char guard；`max_context_chars=1` 可在 token 合法后独立停止 | 阻断 5F-4 |
| unpublished draft | exact pass | Pi final text 只构造成 `CoachDraft` | 不阻断 |
| attributable knowledge | exact pass | 只有本次实际 Python `ToolExecutionRecord.data` 能构造 `KnowledgeEvidence`；public result 不含 body | 不阻断 |
| bad citation | exact pass | `[K999]` 在 Harness draft validation 处降级，Evaluator 不运行 | 不阻断 |
| Tool failure | exact pass/fail-closed | Pi 即使继续得到 final text，失败 Tool 不能提供 Evidence，Harness 只发布 deterministic fallback | 不阻断 |
| typed terminal output | exact pass | output 从 terminal Manifest、最终 Evaluation、Evidence 和 SHA 校验 Artifact 重建 | 不阻断 |
| Harness unique publication | exact pass | final Artifact producer 只能是 `review_harness.publisher` 或 deterministic fallback；Pi producer 为 0 | 不阻断 |
| Provider Usage complete | exact pass | per-call input/output + finish reason 进入 Signal；Recorder aggregate 与 Pi RuntimeUsage 逐字段相等 | 不阻断 |
| missing Usage | fail-closed | completed draft + unknown Usage 不被归零，Harness 降级，input/output 继续为 null | 不阻断 |
| common terminal | partial | `final_response`、预算、timeout、`provider_error` 可无损映射 | 仍有下项硬 gap |
| extended terminal | hard gap | `provider_aborted`、`protocol_error`、`process_error` 等不在 Runtime Agent terminal vocabulary；projector 返回 `unsupported_agent_terminal` | 阻断 5F-4 |
| Trace body safety | exact pass | Trace 不含 Prompt、query、chunks、draft、原始异常或 secret；Artifact 只保存引用和 SHA | 不阻断 |
| live timing/stream | hard gap | safe events 当前在 sidecar 完成后批量投影，顺序合法但逐事件时间不是真实发生时间，也不是 5E live stream | 阻断 5F-4 |
| process isolation | partial | allowlisted env、bounded JSONL、stderr、Permission Model defense-in-depth；不是 OS 网络沙箱 | 不单独阻断 no-I/O，但真实 slice 前必须解决 |
| build/dependency cost | unfavorable | exact npm tree 94 packages、11,355 files、约 62 MB；Node 24 + `npm ci --ignore-scripts` | 维护收益未成立 |
| per-run overhead | unfavorable | 5F-2 Windows 本机每 run 新进程约 0.4 秒量级；不是生产 p50/p95 | 维护/性能成本 |
| real model quality | unknown | 本阶段 external Provider/Riot/Key/held-out I/O 为 0 | 不可声称质量 |

## 4. 为什么“成功 Trace”仍不等于完整 Trace parity

成功 Scripted 案例已经证明：逐调用 Provider start/completed、Tool start/completed、Agent terminal、
Harness transitions、Evaluation、publication 和 Runtime terminal 可以组成合法 Trace，且 Usage 与事件
一致。

但 Trace parity 不是“有一条 Trace 能通过 Pydantic”这么简单。生产观测还要求：

- 所有合法失败原因都能表达；
- 每个事件的发生时间可信；
- `stream()` 能在运行中交付，而不是结束后重放；
- Context 上限与主 Runtime 使用同一单位和算法。

当前三项都不满足，所以不能用成功 happy path 抹掉 hard gap。

## 5. 为什么不在 5F-3 继续修到通过

理论上可以：

1. 把 Python `DeterministicContextSizer` 在 JavaScript 重写一份，并长期保证两边不漂移；
2. 扩展生产 Runtime terminal enum 和 lifecycle 来容纳 Pi 特有终态；
3. 把 controller 改成在线 event bridge，重新解决 observer fail-fast、背压、child cancel 和双终态；
4. 再把 sidecar 加入产品部署、日志和故障排查。

但这些工作正是我们原有 Python Runtime 已经完成的职责。若为了采用 Pi 再维护一套跨语言实现，Pi
没有减少 Runtime 维护面，反而增加协议、依赖和部署成本。继续修不是“小补丁”，而是在采用决策前
先承担迁移成本，违反技术采用门。

## 6. 测试证明什么

### 本轮新增/聚焦

- Pi protocol/sidecar/narrow parity/Harness/Trace：`45 passed`；
- Agent/Compiler/Tool/Harness/Runtime/Pi 相邻：`196 passed`；
- 完整回归：`929 passed, 1 warning, 110 subtests passed`。

唯一 warning 是既有 FastAPI TestClient 的 Starlette/httpx 迁移提示，与 Pi 实验无关。

### 能证明

- Fake/Scripted 控制流、Tool/Harness/Trace 合同与安全失败边界；
- 主 Python 路径未被替换，既有完整回归保持通过；
- 成功/失败结果中哪些可无损投影，哪些必须拒绝；
- no-I/O、body-free、唯一发布权和 missing Usage 语义。

### 不能证明

- 任何真实模型的 Coach 质量、成本或延迟；
- Pi 在并发、Session、恢复、SSE、公网部署下的可靠性；
- Node Permission Model 是网络沙箱；
- Windows 单机进程测量等于生产 SLO；
- Pi、Claude SDK、LangGraph 或自建 Runtime 的普遍优劣。

## 7. 安全结论

- `.env`/Key 未读取，真实 Provider/Riot/held-out 调用为 0；
- child environment 仍是 allowlist，最终 public result/event/Trace 不含 Tool body；
- Tool body 只存在于单次 `PiSidecarExecution.tool_records` 内存对象，用完后不写盘；
- 坏 citation、Tool failure、process failure、missing Usage 都不能产生 Pi 发布；
- projector 不通过近似 stop reason 制造 Trace 成功。

## 8. 对 5F-4 与 5F-5 的交接

5F-4 的入口条件没有满足，因此建议将其标记为：

```text
not-entered: 5F-3 hard Runtime parity gate failed
```

这不是“做了一半跳过”，而是 5F-entry-design 已冻结的条件分支。真实模型调用不能回答 Context、
terminal vocabulary 或 live event bridge 问题，所以执行 5F-4 没有信息增益。

公共 CI 成功后，唯一下一检查点应为 `5F-5-adoption-decision-exit-review`。5F-5 才正式决定：

- `partial-adopt`：保留已吸收的设计思想/测试方法，不保留产品 Pi sidecar；或
- `reject`：连隔离 adapter 也不保留，只保留审计和 ADR 证据。

本退出审查不提前替 5F-5 作最终选择。

## 9. 初学者与面试表述

可以这样解释：

> 我们没有因为 Pi Agent Core 的 demo 能跑就替换自建 Runtime。先用官方 0.84.2 做隔离 JSONL
> sidecar，再把同一草稿接回原 ReviewHarness，并用现有 Recorder 验证 Trace/Usage。实验确认 Tool、
> Harness、Artifact 和成功 Trace 可以适配，但也发现 Context 计量单位、失败终态词汇和实时事件三项
> 硬差异。再加上 94 个 npm 包、约 62 MB 依赖和每 run 约 0.4 秒进程开销，真实模型调用无法修复
> 这些 Runtime 问题，因此我们在真实调用前停止。这展示的是技术采用门和负面实验能力，而不是为了
> 简历硬塞 SDK。

## 10. exact-SHA 公共闭环

实现/退出提交 `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已由 GitHub Actions run
`32025522606` 完成 exact-SHA 公共验证；Node 24、`npm ci --ignore-scripts`、完整 pytest、两套 RAG、
compileall、治理、Harness/secret boundary 与 dry-run 全部成功。

5F-3 正式关闭；5F-4 因前置 hard Runtime parity gate 失败而未进入。canonical 只交接到
`5F-5-adoption-decision-exit-review` 准备状态，等待用户明确继续，不自动作最终采用裁决。
