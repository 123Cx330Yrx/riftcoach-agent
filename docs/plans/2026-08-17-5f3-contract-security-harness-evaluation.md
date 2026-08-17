# 5F-3 Contract / Security / Harness Evaluation 实施计划

## 1. 本阶段要回答的问题

5F-2 证明 Pi 能运行一个受限 Agent loop。5F-3 要回答的是：

> 当 loop 换成 Pi 后，RiftCoach 已经建立的合同、安全门、唯一发布权和运行证据是否仍然成立？

这不是模型质量评测，也不是 Pi 采用决策。Scripted/Fake 通过只能证明控制流与合同，不证明 GLM、
DeepSeek、Qwen 或任何真实模型生成质量。

## 2. 初学者理解：数据流和控制流的区别

数据流描述“什么数据经过哪里”：

```text
Validated Skill + Context
→ Pi request
→ ToolCall / ToolResult
→ unpublished CoachDraft + KnowledgeEvidence
→ ReviewHarness
→ typed output + immutable Artifacts
```

控制流描述“谁有权做决定”：

```text
Agent/Pi：可以提议 ToolCall，可以生成 draft
Python ToolRuntime：决定 Tool 是否允许、参数是否有效、怎样执行
ReviewHarness：决定评测、修订、发布、降级或拒绝
Runtime Recorder：只记录已经发生且可验证的安全事件
```

Pi 返回一段好看的文字，并不等于它有权发布。最终报告必须由 Harness 写入 final Artifact，typed
output 又必须从 terminal Manifest 和经过哈希校验的 Artifact 重建。

## 3. 本轮实现与不实现

### 实现

- 评测专用 `PiSkillDraftPreparer`，复用现有 `AgentRunCompiler`；
- 单次进程内 detailed Tool record，用于构造真实 `KnowledgeEvidence`；
- body-free Pi event → Runtime Signal 严格 projector；
- 成功 Tool round-trip → Harness → typed output → Artifact/Trace 纵向案例；
- 失败、坏 citation、Tool/Provider/process/protocol terminal 的 fail-closed 案例；
- Context 单位、terminal vocabulary、实时事件和跨语言成本的差异矩阵。

### 不实现

- 不修改或替换主 `AgentRuntimeV1`、FastAPI、Application Service 或默认 composition；
- 不读取 `.env`/Key，不调用真实 Provider、Riot API 或 held-out；
- 不复制完整 Python ContextSizer 到 JavaScript；
- 不扩展生产 Runtime terminal 枚举来迎合 Pi；
- 不做 5F-4 真实切片，不作 5F-5 最终采用裁决；
- 不实现 Session、Memory、MCP、Multi-Agent、DAG 或部署。

## 4. 冻结的 parity matrix

| 维度 | Python 基线 | 5F-3 验证方法 | 接受条件 |
|---|---|---|---|
| Tool whitelist | Manifest → Compiler → Registry | unauthorized/batch preflight/contract drift | 任何 Tool I/O 前拒绝 |
| 重复与批次 | 整批原子预检 | batch 内/跨轮重复和第二调用副作用 | 顺序和零副作用一致 |
| iteration/tool | typed integer budgets | 同脚本双路径与边界案例 | stop reason/次数一致 |
| deadline | 一个递减总 deadline | timeout、child terminate/kill、Tool cap | 不重置为逐步新 deadline |
| Context | deterministic token-unit sizer | 与 sidecar char guard 分开记录 | 不得把 char 当 token；无法精确则记硬 gap |
| draft/output | CoachDraft + declared Pydantic output | 成功/坏 citation/Impossible output | 未验证 draft 不得成为 final output |
| Provider/Tool/process error | typed safe terminal | 可映射和不可映射错误族 | 无损才投影；否则显式 parity gap |
| Harness boundary | 唯一 evaluator/reviser/publisher | draft、revision、fallback、producer | Pi 不能直接写 final Artifact |
| Usage | attempt/observed/completeness | complete/partial/unknown + per-call signal | 不得把 missing Usage 记成零 |
| Trace | typed ordered body-free events | Recorder 接受成功序列；拒绝坏序列 | 无 Prompt/Tool body/secret，Usage 与事件一致 |
| Artifact | immutable path + SHA-256 | final producer、digest、tamper check | typed output 只从持久事实重建 |
| 运维成本 | 纯 Python 主线 | Node/lock/安装树/进程/调试矩阵 | 成本必须可见，不能称为免费替换 |

## 5. 方案选择

采用 ADR-0036 的评测专用接缝：

```text
AgentRunCompiler
→ PiSkillDraftPreparer（evaluation only）
→ PiSidecarController
→ ephemeral ToolExecutionRecord
→ AgentDraftPreparationResult
→ existing SkillReviewExecutor
→ existing ReviewHarness
→ typed Skill output
```

Trace 另走严格投影：

```text
PiSafeEvent + PiSpikeRunResult
→ PiRuntimeSignalProjector
→ existing RuntimeRecorder
→ RuntimeTrace validation
```

项目不通过“近似映射”来制造成功。现有 Runtime 枚举无法表达的 Pi 终态，projector 必须拒绝，
退出矩阵据此记录缺口。

## 6. TDD 批次

### Batch A：协议与 detailed evidence 红灯/绿灯

- public result 继续 body-free；
- detailed result 只在内存保存实际 ToolExecutionRecord；
- per-call Usage 只增加数字，不增加正文；
- 失败和 run identity 仍 fail closed。

### Batch B：Harness 纵向切片

- 同一 validated execution/context 先经过 Compiler；
- Pi ToolCall 产生真实本地 KnowledgeEvidence；
- Pi draft 通过 Evaluator 才由 Harness 发布；
- 坏 citation、Pi failure 分别降级/拒绝；
- typed output 和 final Artifact producer/digest 正确。

### Batch C：Signal/Usage/Trace parity

- 成功 Provider/Tool/Agent 事件可进入 Recorder；
- aggregate Usage 与 Recorder per-call Usage 完全一致；
- unsupported Pi terminal 必须得到稳定 parity gap；
- event/result 不含 Prompt、query、chunks、异常正文或 Key。

### Batch D：差异与成本退出矩阵

- 自动化结果与静态合同审计合并；
- 明确 exact pass、adapter-covered、hard gap、deferred；
- 形成 5F-3 本地裁决，只交接 5F-4 的“允许设计”或“阻断”状态；
- 不自动进入 5F-4。

## 7. 验证层级

1. 新增 Pi/Harness/Trace 聚焦测试；
2. Pi、Agent、Tool、Harness、Runtime 相邻回归；
3. 完整 pytest 与 unittest subtests；
4. 两套 RAG、compileall、secret/tracked-data、Harness dry-run、governance、`git diff --check`；
5. 小提交、推送、exact-SHA GitHub Actions。

## 8. 预先声明的限制

- sidecar event 当前在进程结束后投影，能验证顺序/合同，不能证明实时 stream latency；
- Scripted Usage 是冻结输入，不是 Provider 账单；
- 一次 Windows 本机开销不是生产 p50/p95；
- 5F-3 即使成功，也只证明候选具备进入下一道设计门的资格；
- 如果 Context 或 terminal 硬合同无法保持，负面结论是有效实验结果，不应通过扩大范围强行修复。
