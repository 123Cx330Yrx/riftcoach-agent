# 8E：GLM-5.3 候选评估台设计计划（RQ-199）

## 状态、范围与授权

状态：`design-complete / candidate-only / implementation-pending`。

本轮“继续”只授权当前 canonical 的
`candidate-evaluation-harness-design`。本轮完成架构设计、接口冻结、失败矩阵、
实现清单和学习材料；不写 `app/` 代码，不读取或修改 Key，不发 API，不执行
fresh-recovery/G53-7，不改 Portal、Account、Workbench、Auth、默认模型或产品
Runtime。

## 要解决的问题

RQ-197/198 已证明边界观察合同可以在本地和公共 CI 复现，但还缺一个协调层：它需要
把一次候选评估中的请求绑定、primary 预留、规范化流消费、完整回答/不完整边界分流、
策略重算、账本结算和脱敏 receipt 连接起来。

关键约束是“首回合快照未知、但调用必须先记账”。现有
`build_response_recovery_plan()` 是首回合观察后的离线计划，不能用伪造 sentinel
快照来提前建账，也不能等请求结束后再 reserve。计划因此采用候选专用 staged ledger：
先预留未知的 primary，收到真实观察后才冻结 policy/plan，再决定是否存在第二槽位。

## 学习目标与核心原则

### 问题

一个 provider 流可能完整结束，也可能只得到 reasoning、缺 Usage、被取消或在读取时
出错。评估台必须把“模型产出了什么形状”和“系统是否允许再发一次完整请求”分成
两件事，不能把 partial body 当成功，也不能把网络异常当候选资格。

### 原理

- **控制面与数据面分离**：可持久化的记录只有状态/计数/安全码；正文只在一次评估
  的内存中短暂存在；
- **先记账、后 I/O、恰好结算一次**：每个真实尝试在打开流前预留，失败也消耗槽位；
- **资格由版本策略重算**：调用方不能传 `candidate_eligible=true` 代替 policy；
- **完整性优先**：EOF、terminal、close 和 Usage 缺一不可；未知 Usage 不是零；
- **候选与产品隔离**：候选 transport/ledger/receipt 不进入 ProviderRegistry、
  AgentLoop、统一 Runtime Trace 或默认配置。

## 设计后的组件边界

```text
CandidateEvaluationHarness
  ├─ CandidateEvaluationRunSpec
  ├─ exact binding/profile/policy validator
  ├─ CandidateEvaluationLedger（staged，candidate-only）
  ├─ CandidateStreamTransport.open_stream()
  ├─ one-pass event pump
  │    ├─ CandidateStreamBoundaryObserver
  │    └─ ProviderStreamAssembler
  ├─ ResponseCompletionPolicy（重新计算）
  ├─ optional CandidateContentConsumer（仅瞬时数据面）
  └─ CandidateEvaluationReceipt（body-free、独立 schema）
```

已有合同的职责不改变：

| 合同 | 继续负责 | 不负责 |
| --- | --- | --- |
| `CandidateZhipuStreamTransport` | 候选 v2 cap/timeout/sampling/retries 与显式 opener | 真实恢复、Provider 注册、重试 |
| `CandidateStreamBoundaryObserver` | O(1) 生命周期/字段/Usage/身份观察 | 保存正文、生成资格布尔值 |
| `ProviderStreamAssembler` | 完整流的临时 `ChatResponse` 和完整流 Trace | 交付不完整响应、恢复 |
| `ResponseCompletionPolicy` | 从完整边界快照重新分类 | 网络 I/O、预算预留 |
| staged ledger | primary/recovery 预留、结算、累计预算 | Provider、Prompt、正文 |
| receipt | 脱敏评估证据 | 产品 Runtime Trace、用户 API |

## 冻结的输入/输出接口

### `CandidateEvaluationRunSpec`

输入只包含：

- 受信 `PRIMARY_CANDIDATE_BINDING`；
- 精确 candidate profile/policy singleton；
- `ResponseRequestContext`；
- 本地随机 nonce 的 SHA-256 运行标识。

原始 `ChatRequest` 只作为内存参数传给 transport，不进入可序列化 spec。不得从
请求 metadata 选择 profile、policy、attempt 或 activation。

### `CandidateEvaluationHarness.evaluate`

```text
evaluate(
    request: ChatRequest,
    run: CandidateEvaluationRunSpec,
    *,
    transport: CandidateStreamTransport,
    activation: CandidateActivationGate = DISABLED,
    clock: MonotonicClock = time.monotonic,
    consumer: CandidateContentConsumer | None = None,
) -> CandidateEvaluationResult
```

最小 API 不接收任意 Provider、SDK client、retry callable、全局 store 或 raw response
body。一个实例只运行一次；所有字段均由值对象验证。

### `CandidateEvaluationReceipt`

顶层 schema `candidate-evaluation-harness/1.0` 只允许：

- run SHA、候选身份和 activation/execution 状态；
- 连续的最多两行 attempt（ordinal/kind、生命周期、finish/error code、字段状态、
  ToolCall 数量、Usage 状态/数字、耗时）；
- `terminal_state`、`next_action`、调用计数；
- `usage_certainty`（`complete`/`partial`/`unknown`）和 `budget_state`
  （`within`/`exceeded`/`unknown`）；
- 独立 `CandidateStreamTrace` allow-list。

不允许 Prompt、正文、reasoning、工具参数、Key、SDK 对象、原始 request ID、任意
caller message 或异常原文。若 Usage 未知，resource token 字段为 `None` 或注明
“已知下界”，绝不能把观察总和当作可用余额。

## 具体控制流

### 阶段一：准备与 primary

1. 验证类型、exact candidate identity、上下文阶段、request metadata 和 profile
   预算；
2. 创建一次性 staged ledger，预留 ordinal=1；
3. 以候选 profile 强制的 8192/90/120 秒和 sampling 打开一条流；
4. 只迭代一次 normalized event，逐事件送入共享校验、observer 和 assembler；
5. 正常 EOF 时分别 seal observer/assembler；异常、取消、超时或关闭失败时 abort；
6. 生成一个 body-free `BoundaryObservation`。完整 `stop`/`tool_calls` 结果若有
   consumer，只短暂交付其内存数据，随后清除。

### 阶段二：真实快照与候选判定

1. 只有 `complete_boundary` 为真时，才调用
   `BoundaryObservation.to_response_boundary_snapshot()`；
2. 用原始 `ResponseRequestContext` 重新运行精确 candidate policy；
3. 将真实 snapshot、decision、Usage 和 elapsed 映射为一次
   `ResponseAttemptOutcome`，结算 primary；
4. `complete_text`/`tool_calls_ready`/`fail_closed` 立即终止；
5. `candidate_eligible` 但 activation 为 `DISABLED` 时，receipt 终态为
   `awaiting_recovery`，不打开第二条流；
6. 只有未来显式 activation 凭据通过且剩余预算足够时，才生成 recovery spec，
   再重复“reserve→open→observe→settle”；第二次任何失败或再次截断均终止。

### 阶段三：收口

1. 从 ledger rows 与 stream observations 推导 receipt；
2. 重新校验 attempt ordinal、身份稳定、调用计数、资源确定性和 body-free 白名单；
3. 清理 response、工具参数、vendor iterator 和 consumer 临时引用；
4. 任何再次调用同一个 harness、ledger 或 reservation 都失败。

## 状态与失败矩阵

| 阶段/事件 | 记录 | 终止动作 |
| --- | --- | --- |
| 创建 | `created` | 等待 primary reserve |
| primary 已预留 | `primary_reserved` | 才可 open |
| `stop` 完整 | `complete_text` | 不恢复 |
| `tool_calls` 完整 | `tool_calls_ready` | 不执行工具 |
| 精确 `length` 候选形状 | `awaiting_recovery` | 当前 activation disabled，停 |
| 非候选 `length` | `fail_closed` + reason | 停 |
| 缺 EOF/terminal/Usage/identity | `fail_closed` + unknown | 停 |
| open/read/translate/close/clock 错误 | 当前槽位已结算失败 | 停 |
| 第二次成功 | `complete_text`/`tool_calls_ready` | 停 |
| 第二次失败/预算超限 | `fail_closed` | 禁止第三次 |
| 重复 reserve/settle/跨 run | 状态错误 | receipt 不发布 |

## 预算与退出条件

### 固定预算

- 单次 output：8192；
- Agent/工具窗口：90 秒；transport：120 秒；
- sampling：`temperature=1`、`top_p=0.95`、SDK retries=0；
- 累计 input/output/time：32,000 / 16,384 / 180,000ms；
- 最多 2 attempts、最多 1 次额外调用。

### 设计门退出清单

- [x] ADR-0077 明确两阶段账本与一次事件泵；
- [x] 冻结输入/输出类型、状态机、receipt allow-list 和异常语义；
- [x] 给出失败、安全、预算、替代方案和测试矩阵；
- [x] 明确当前 activation disabled、候选未注册、产品边界不变；
- [x] 新增学习 walkthrough，并更新状态/路线/coverage 索引；
- [ ] 实现 staged ledger/harness（下一检查点，尚未授权）；
- [ ] 在实现后取得同 SHA 公共 CI；
- [ ] 单独授权真实 fresh-recovery、G53-7、生产准入或 8F。

## 下一检查点

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`

下一轮即使获“继续”，也只实现 fake/local harness 与 staged ledger，并跑聚焦测试、
compile、diff check、governance 和 exact-SHA 公共 CI；不自动发送真实候选请求。真实
恢复、领域黄金切片、OP.GG breadth、安全部署/合规和 8F 仍按原路线另行排队。
