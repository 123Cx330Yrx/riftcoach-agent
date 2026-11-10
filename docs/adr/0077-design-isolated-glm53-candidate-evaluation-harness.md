# ADR-0077：设计隔离的 GLM-5.3 候选评估台

- 日期：2026-09-02
- 状态：`completed-public / candidate-only / recovery-review-pending`
- 范围：Stage 8 / 8E；`candidate-evaluation-harness-design`（RQ-199）
- 依据：ADR-0071、0072、0075、0076；RQ-192–RQ-198；
  `app/evaluation/candidate_stream_contract.py`、
  `app/providers/response_completion_policy.py`、
  `app/providers/response_recovery_contract.py`

## 背景与问题

现有候选材料已经分别解决了四件事：

1. `ProviderStreamAssembler` 能把一条规范化流收口成完整的 `ChatResponse`；
2. `CandidateStreamBoundaryObserver` 能在不保存正文的前提下观察 EOF、终止、Usage、
   身份和关闭状态；
3. `ResponseCompletionPolicy` 能从脱敏快照重新计算“完整、工具、拒绝或候选形状”；
4. `ResponseRecoveryLedger` 能记账最多两个有序 attempt 和一次额外调用。

它们目前是独立合同，还没有一个协调层把“一次候选评估”串起来。直接把
`ZhipuStreamAdapter` 包成产品 `LLMProvider` 会让候选能力被默认注册；直接把
`AgentLoop` 改成流式分支会同时改变工具、副作用、统一 Trace 和产品预算。另一个
容易被忽略的问题是时序：现有 `build_response_recovery_plan()` 需要首回合的
`ResponseBoundarySnapshot`，但真正的 primary 尚未发出时不可能知道这个快照。用一个
伪造的“初始快照”先建账本，会让 `settle()` 的精确匹配失去意义；等请求结束后才
`reserve`，又会漏记 open/read/timeout 失败。

本 ADR 只冻结下一步实现所需的隔离评估台设计，不实现它、不注册候选、不读取 Key、
不发真实请求，也不改变产品 Runtime。

## 决策

### 1. 评估台是独立的控制面，正文只在瞬时数据面存在

新增的未来协调器暂定名为 `CandidateEvaluationHarness`，位置为
`app/evaluation/`。它只接受显式传入的候选 transport、`ChatRequest` 和受信
`ResponseRequestContext`，不实现 `LLMProvider`，不进入 `ProviderRegistry`、组合根、
Worker、`AgentLoop` 或 `RuntimeTraceStore`。

评估台有两条严格分开的数据路径：

```text
控制面（可持久化）
  exact binding → 预留/结算 → BoundaryObservation → policy decision
                → ledger/stream allow-list → CandidateEvaluationReceipt

数据面（仅内存、可选）
  normalized event → assembler → 临时 ChatResponse
                                  → 显式 evaluation consumer（若有）→ 立即丢弃
```

没有显式 consumer 时，完整回答也不离开协调器；任何 receipt、日志、异常、`repr` 和
JSON 都不能含正文、reasoning、工具参数、Prompt、Key、SDK 对象或原始 request ID。
若以后需要质量判分，consumer 必须是另一个明确的 evaluation-only 合同：只在内存中
接收完整结果，并返回脱敏的标签/分数；本 ADR 不把任意 callable 或持久化 scorer
偷偷加入评估台。

### 2. 冻结最小公开形状

下一实现应提供以下不可变输入/输出值对象。名称可在实现时保持不变，字段不得借由
调用方 metadata 动态扩展。

#### `CandidateEvaluationRunSpec`

```text
primary_binding: PRIMARY_CANDIDATE_BINDING（必须是受信 singleton）
policy: GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
runtime_profile: GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
context: ResponseRequestContext
run_id_sha256: 仅由本地随机 nonce 派生的 64 位十六进制摘要
```

`run_id_sha256` 不由 Prompt、正文或用户可控 request ID 派生；原始 nonce 只在内存中
存在。`ChatRequest` 作为一次性内存输入，不进入 `RunSpec` 的序列化形式。候选身份
必须同时通过 `require_exact_candidate_binding()`、profile/policy exact equality 和
版本匹配；不接受“同值但不同类型”的替身。

#### `CandidateEvaluationHarness.evaluate(...)`

建议的显式接口为：

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

约束如下：

- `transport` 必须实现已经存在的 `CandidateStreamTransport.open_stream()`，不能传入
  任意 Provider、SDK client、重试函数或可写入全局状态的隐式适配器；
- `activation` 不是一个可由调用方填写的 `bool`。当前唯一实现是不可伪造的
  `DISABLED` 门，未来启用必须来自另一个已审查的注册凭据/证据对象；
- 一个 harness 实例只运行一个 run，完成或失败后拒绝再次使用；不创建后台任务，
  不并发跑两个 attempt；
- `consumer` 省略时丢弃临时 `ChatResponse`。即使提供，也不得改变 ledger、policy
  或 recovery 决策，不能执行 ToolRuntime。

返回值只含 `CandidateEvaluationReceipt`（以及可选的内存 consumer 结果，不进 receipt）。
调用方不能从返回值取得“继续发请求”的任意 callable。

### 3. 采用两阶段账本，避免伪造初始快照

现有 `ResponseRecoveryLedger` 的离线 API 保持兼容，继续服务“已有首回合快照”的
合同测试。评估台实现时新增一个候选专用的 staged ledger 接缝（可命名为
`CandidateEvaluationLedger`，或在现有 ledger 内增加 candidate-only session API），
规则如下：

```text
CREATED
  → PRIMARY_RESERVED       # 尚无 response snapshot
  → PRIMARY_OBSERVING
  → PRIMARY_SETTLED        # 此时才冻结真实 snapshot/context/decision
      ├─ COMPLETE_TEXT
      ├─ TOOL_CALLS_READY
      ├─ FAIL_CLOSED
      └─ AWAITING_ACTIVATION
             → RECOVERY_RESERVED（只有显式激活门通过）
             → RECOVERY_OBSERVING
             → RECOVERY_SETTLED
             → COMPLETE_TEXT / TOOL_CALLS_READY / FAIL_CLOSED
```

具体不变量：

1. staged ledger 在 primary I/O 前就预留 ordinal=1；open 失败、读取异常、取消和
   close 失败均消耗这一槽位；
2. primary 结算时把真实 `BoundaryObservation` 映射为
   `ResponseBoundarySnapshot`，重新调用候选 policy，再冻结 recovery plan；绝不使用
   sentinel snapshot，也不接受 caller 的 eligibility 字段；
3. 只有观察满足 EOF、terminal、`close=closed`、有效 Usage 且 policy 返回
   `candidate_eligible` 时，才可能出现 recovery 槽位；当前 `DISABLED` activation
   会把结果固定为 `awaiting_recovery`，不发第二条流；
4. future recovery 也必须先 reserve、再 open、再 settle；第二次仍失败、再次
   `length`、Usage 未知或预算触顶，都直接 `fail_closed`，不产生第三槽位；
5. 账本的资源判定和 identity 校验复用现有合同的纯函数/值对象。不得为协调器复制
   一套“宽松 policy”或把 `ResponseRecoveryLedger` 的零值总额解释成已知余额。

这样既保留了“reserve-before-I/O”的审计事实，也保留了现有 plan 对真实首回合快照
的精确匹配。实现时如果选择扩展现有 ledger，必须保持旧构造器和旧测试语义；如果
选择独立 staged ledger，必须抽出共享的预算/状态校验，而不是复制后各自演化。

### 4. 一次流只消费一次，观察器与装配器用同一事件泵

`CandidateZhipuStreamTransport` 或显式 `ZhipuStreamAdapter.stream_events()` 返回的
规范化事件只允许被迭代一次。评估台建立一个内部事件泵：

```text
transport.open_stream(binding, bounded_request, caps)
  → iter(raw normalized events)
  → shared event validation
      ├─ CandidateStreamBoundaryObserver.accept(event)   # 只留状态
      └─ ProviderStreamAssembler.accept(event)            # 暂存正文/工具，仅内存
  → 正常迭代结束：observer.mark_exhausted + assembler.mark_exhausted
  → finally：关闭 iterator/resource
```

事件级错误先使共享泵停止并同时毒化两条路径；不能让 assembler 的异常文本覆盖
observer 的安全码，也不能在 observer 失败后继续消费不可信事件。若只是终态为
`length`，assembler 可以在最终收口时返回“不可交付”的内部失败，而 observer 仍可
根据完整生命周期识别候选形状；只有真实 `stop`/`tool_calls`、EOF、合法 Usage 和
必要身份全部齐全时，才向可选 consumer 交付临时 `StreamAssemblyResult`。

这要求实现复用 RQ-192 的 `validate_provider_stream_event()` 和 RQ-197 的观察器，
而不是再写 vendor parser。任何正常 EOF 之前的取消、超时或 iterator 异常都不能被
改写成 candidate shape。

### 5. 关闭、取消和异常的统一结算顺序

每个 attempt 的协调顺序固定为：

1. 校验 exact identity、请求类型、上下文和剩余预算；
2. `ledger.reserve(ordinal)`；
3. 调用 transport 一次并打开事件泵；
4. 观察/装配到 EOF，或在普通异常/取消路径中安全 abort；
5. 生成 body-free observation；
6. 对完整边界重新运行 policy，构造 `ResponseAttemptOutcome`；
7. 对 reservation 恰好调用一次 `settle()`；
8. 生成 stream trace、ledger trace 和顶层 receipt；
9. 清除内存中的 response、工具参数和 vendor iterator。

`KeyboardInterrupt`、`SystemExit`、`GeneratorExit` 等控制异常要在清理后继续传播，
但 reservation 仍必须留下“已发出/未知资源”的安全结算记录；普通 provider 异常则
映射成稳定的 `error_code/error_stage`。没有隐式 retry、指数退避、resume token 或
后台恢复。

### 6. 新的 receipt 采用独立 envelope，不冒充产品 Trace

未来实现应定义 `CandidateEvaluationReceipt`（schema `1.0`），而不是把现有
`RuntimeTrace` 或 `StreamAssemblyTrace` 直接写入产品存储。建议白名单字段为：

```text
schema_version
run_id_sha256
provider_id / model
runtime_profile_id / runtime_profile_version
policy_id / policy_version
activation_state = candidate
execution_allowed = false
attempts: tuple[AttemptReceipt, ...]       # ordinal/kind 连续且最多两行
terminal_state
next_action
calls_reserved / calls_settled
resource: {input_tokens, output_tokens, elapsed_ms,
            usage_certainty, budget_state}
stream_observations: tuple[CandidateStreamTrace, ...]
safe_error_code / safe_error_stage
```

每行只能引用 `BoundaryObservation` 的字段状态、finish/error code、工具数量、Usage
状态/数字、耗时和身份。`input_tokens`/`output_tokens` 在任一 attempt Usage 未知时
必须是 `None` 或明确标记为“已知下界”，不能把现有 ledger 的 `or 0` 聚合当作余额；
`budget_state` 允许 `within`、`exceeded`、`unknown` 三态。receipt 的状态和 totals
全部由已结算 rows 推导，构造器重新检查 ordinal、identity、调用数和资源一致性。

该 envelope 只作为 candidate evaluation evidence，可由显式调用方选择落盘；本阶段
不设计数据库表、生产日志 sink、用户可见 API 或统一 Trace 迁移。落盘前必须再过
body-free 序列化检查。

## 失败矩阵

| 场景 | 控制面结果 | 是否继续/恢复 |
| --- | --- | --- |
| `stop` + 正常 EOF + 有效 Usage + 正确身份 | `complete_text`，可选 consumer 收到临时结果 | 否 |
| `tool_calls` + 正常 EOF + 有效 Usage | `tool_calls_ready`，只作评估观察 | 否；不执行 ToolRuntime |
| `length` + 空正文 + 非空 reasoning + EOF/close/Usage 完整 | policy 得到候选形状；当前 receipt=`awaiting_recovery` | 否，activation disabled |
| `length` 但正文非空、带工具、非初始阶段或预算不足 | `fail_closed`，保留具体安全原因 | 否 |
| 缺 EOF、terminal、Usage、model 或 request identity | `fail_closed`，Usage/费用保持 unknown | 否 |
| open/read/translate/close/clock 异常 | 当前槽位结算为失败/未知资源 | 否 |
| provider 返回第三方/非候选身份 | I/O 前拒绝，零 provider call | 否 |
| staged ledger 重复 reserve/settle 或跨 run 使用 | 状态错误，receipt 不可发布 | 否 |
| 第二次仍失败或累计预算达到上限 | `fail_closed`，保留两次已发生调用 | 不得第三次 |
| consumer 抛错或试图写产品存储 | consumer 失败独立记录；不得改变候选结算 | 否 |

## 预算、非功能与安全约束

- 候选 profile 固定单次 8192、Agent 90 秒、transport 120 秒、
  `temperature=1`、`top_p=0.95`、SDK retries=0；累计 input 32,000、output 16,384、
  elapsed 180,000ms，最多 2 attempts/1 次额外调用；
- 观察器继续 O(1) 保存字段状态、计数、哈希和时钟，事件/正文/工具参数有硬上限；
  assembler 的正文缓存只存在一次评估的内存生命周期，不能进入 ledger、receipt 或
  异常 repr；
- 任何未知 Usage 都保持 unknown，不以零换取恢复资格或余额；时钟必须单调，负数、
  NaN、溢出和第三次调用全部 fail closed；
- 身份使用 exact singleton/equality 双重校验；请求 metadata 只能被检查，不能选择
  profile、policy 或 activation；
- 没有网络重试、线程、队列、隐式全局单例或自动发现，便于 fake transport 做确定性
  测试和在评估完成后释放资源；
- 生产 `ZhipuProvider`、同步 `chat()`、`AgentLoop`、Workbench、Portal/Account、
  Auth、路由、默认模型、`capabilities.streaming` 和 `production_media=0` 均不变；
- 真实 API、Key、fresh-recovery、G53-7、黄金切片、OP.GG breadth、公共生产部署和
  8F 仍是独立后续闸门，不能由本地 harness 设计或 fake 测试代替。

## 备选方案与取舍

### 方案 A：把候选 adapter 包成 `LLMProvider`

拒绝。默认注册表会看到候选，且完整流与 `length` 边界会被一次同步响应合同混淆。

### 方案 B：把 `AgentLoop` 改成隐式 streaming/retry

拒绝。会把候选预算、ToolRuntime 副作用、统一 Trace 和产品截止时间耦合在一起，
也无法解决 v1/v2 身份冲突。

### 方案 C：等首回合结束后才创建并 reserve 账本

拒绝。open/read/timeout 失败无法成为已发生 attempt，审计与成本会被低报。

### 方案 D：用 sentinel snapshot 预建现有 `ResponseRecoveryLedger`

拒绝。`settle()` 要求 primary outcome 与初始快照精确相等，哨兵会迫使实现放宽该
检查，反而制造伪造资格的入口。

### 方案 E：staged candidate ledger + 单次事件泵 + 独立 receipt（采用）

采用。它把“预留时点”和“策略判定时点”分开，同时保留现有 policy、observer、
assembler 和预算合同的单一事实源；代价是下一实现需要一个 candidate-only staged
ledger 接缝和一组完整的 fake 失败矩阵，但不会扩大产品主线。

## 下一实现的测试矩阵

实现 checkpoint 只允许 fake/local 输入，至少覆盖：

1. text complete、tool-call complete、candidate shape、partial-content rejection；
2. 缺 EOF/terminal/Usage/model/request identity，以及显式 null 与缺失的区别；
3. open/read/translate/close/clock/取消异常，资源关闭和一次性 reservation；
4. activation disabled、未来 fake activation、第二次成功/失败/再次 length；
5. 单次 cap、累计 input/output/time、unknown Usage、第三次和重复 settle；
6. exact binding/profile/policy/attempt 伪造与跨 run 复用；
7. receipt、trace、异常、`repr`、日志捕获和 JSON 的 body-free 断言；
8. 证明没有导入产品 Runtime/ProviderRegistry，没有改变 `capabilities.streaming`，
   且 consumer 不能执行 ToolRuntime 或改写 ledger。

## 本设计门退出条件与下一步

RQ-199 设计门完成的证据是：本 ADR、实现计划和学习 walkthrough 明确了两阶段账本、
一次事件泵、精确 API/状态机、receipt 白名单、失败矩阵、预算/NFR、替代方案和后续
测试矩阵；本批不改 `app/`、不发真实 API、不注册候选、不改变严格 Flash v1。

下一个精确检查点为：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`

该实现门仍只允许 fake/local 与公共 CI；实现完成后，是否执行真实 fresh-recovery、
G53-7 或将 Flash 提升为产品唯一运行时，必须分别获得新的授权和新的 exact-SHA/领域
证据。Stage 8/8E 继续 `in_progress`，8F 尚未开始，`production_media=0`。

## RQ-200 实现回填（2026-09-02）

设计已在隔离工作树落成为 `app/evaluation/candidate_evaluation_harness.py`：
`CandidateEvaluationRunSpec` 精确绑定候选身份，`CandidateEvaluationLedger` 在
primary I/O 前预留并在真实观察后结算，`CandidateEvaluationHarness` 以一条事件泵
同时驱动边界观察器和临时装配器，`CandidateEvaluationReceipt` 提供独立的
body-free envelope。当前 activation 只有 sealed `disabled`，候选形状不会触发第二条
流；产品 Provider/Runtime、统一 Trace 和默认模型均未改变。

fake/local 聚焦测试为 `15 passed`，与边界观察、流装配和旧恢复合同相邻回归为
`102 passed`；编译检查通过。公共 exact-SHA CI 仍是下一门，故本 ADR 不把本地实现
写成公共生产准入或模型能力证据。

## RQ-201 公共证据回填（2026-09-02）

实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 GitHub Actions run
`33536168224` 已完成且 `head_sha` 精确匹配；`pytest`、`postgres-migrations`、
`packaging-smoke` 三个 job 均成功，公共 pytest 为
`2193 passed, 145 skipped, 1 warning, 127 subtests passed`。这只证明候选评估台在干净
公共环境中的可复现性，不改变其 candidate-only、sealed `disabled` activation 或任何
产品能力边界。

下一精确检查点为：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`

该检查点只复核候选 recovery 的传输、预算、失败和脱敏边界；是否建立新诊断版本、发起
真实 recovery、重跑 G53-7 或进入生产准入，仍需单独授权与新的证据链。
