# ADR-0075：候选流调用方保持隔离并先补边界观察设计

- 日期：2026-09-01
- 状态：`review-complete / candidate-only / implementation-pending`
- 范围：Stage 8 / 8E；GLM-5.3-Flash 候选流接线评审（RQ-195）
- 依据：RQ-194 实现提交 `a7580e861cd986c026040c7fcfcc3fa577737961`、
  Actions `33496237588` 三 job exact-SHA 全绿

## 背景

RQ-194 已把智谱 OpenAI-compatible 分块落成显式的
`ZhipuStreamAdapter`，并由 `ProviderStreamAssembler` 负责完整流的终态、Usage、
工具和隐私边界。当前产品仍使用同步 `LLMProvider`、严格 Flash v1（2048 输出、
零额外调用），候选 profile v2 和 fresh-recovery policy 仍未注册。

本轮评审要回答的不是“能不能再发一次请求”，而是“如果未来允许候选运行时，
它应接到哪里、如何绑定身份、如何结算和撤出”。

## 关键发现

现有 `ZhipuStreamAdapter.assemble()` 只交付完整的 `stop` 或 `tool_calls` 流。
遇到 `length`、缺失终止、缺失 Usage 或其他不完整形状时，它会毒化并安全拒绝，
不会返回部分正文或 reasoning。这是正确的完整回答合同，但不能直接产生候选策略
所需的 `ResponseBoundarySnapshot`：候选白名单要识别“`length` + 空正文 + 非空
reasoning + 有效 Usage + 初始 Agent 阶段”。因此不能把 `assemble()` 的异常当作
恢复资格，也不能从私有字段或错误文本倒推资格。

## 决策

1. **不把候选接缝接入现有产品 Runtime。** 不修改 `LLMProvider`、
   `AgentLoop`、`AgentRuntimeV1`、`build_llm_tools`、Worker、统一 Runtime Trace、
   产品预算或默认 composition root；`capabilities.streaming` 继续为 `False`。
2. **未来若获单独授权，采用隔离的候选评测调用方。** 推荐新增
   `app/evaluation/` 下的 `CandidateStreamEvaluationHarness`（名称可在下一设计门
   冻结），而不是给生产 Runtime 增加隐式分支。它只接收显式的
   `ZhipuStreamAdapter` 和受信候选合同，不能实现 `LLMProvider`，也不能被默认注册表
   自动发现。
3. **四元身份必须精确绑定。** 调用方同时校验
   `provider_id=zhipu`、`model=glm-5.3-flash`、
   `ResponseRecoveryRuntimeProfile`（v2 candidate）和
   `ResponseCompletionPolicy`（candidate fresh-recovery v1）及其版本；任一错配、
   伪造对象、未注册/非 candidate 状态都 fail-closed。
4. **先设计独立的边界观察投影。** 在任何候选调用方实现前，新增一个只输出
   `ResponseBoundarySnapshot`、Usage 数字、耗时和安全错误码的观察接缝。它必须复用
   与 adapter 相同的分块校验，绝不返回或持久化部分正文、reasoning、工具参数；
   完整流仍交给 `assemble()`，不完整流只产生脱敏状态，不把异常伪装成完整响应。
5. **预算与 Trace 分层。** 每个候选 attempt 先向
   `ResponseRecoveryLedger` 预留，再无论成功/失败结算；候选 profile 的最多 2 个
   attempt、最多 1 个额外调用、32,000 输入、16,384 输出和 180,000ms 总预算不得
   泄漏到严格 Flash v1。`StreamAssemblyTrace` 不能直接冒充统一 Runtime Trace，
   未来须用显式 allow-list 投影成 `ResponseRecoveryTrace`；request ID 只能保存
   SHA-256。
6. **回退与撤出由调用方控制，adapter 不负责。** 当前 candidate 的
   `execution_allowed=False` 意味着即使策略判断形状可恢复，也不能预留第二槽位、
   不能发 fresh-recovery、不能 retry、不能执行 ToolRuntime；第三次调用始终拒绝。

## 推荐数据与控制流

```text
显式候选调用方
  ↓ 校验 zhipu / glm-5.3-flash / profile-v2 / policy-v1 四元身份
CandidateStreamEvaluationHarness（未来实现，隔离于 app/runtime）
  ↓ reserve primary（当前只允许离线/fake；真实调用需新授权）
ZhipuStreamAdapter
  ├─ 完整 stop/tool_calls → ProviderStreamAssembler → StreamAssemblyResult
  └─ length/不完整 → 未来 BoundaryObservation（只给状态/Usage/安全码）
  ↓ 由 completion policy 分类，再 settle ledger
ResponseRecoveryTrace（显式脱敏投影，独立于 RuntimeTraceStore）
```

## 不可放宽的边界

- 严格 Flash v1 仍是 2048 输出上限、零额外调用；候选 v2 的 8192/一次恢复不改写
  生产档案。
- 候选 profile、policy 和 recovery 均未注册，`execution_allowed=False` 不变。
- 不改变默认模型、同步 `chat()`/既有 `chat_stream()`、`capabilities.streaming`、
  AgentLoop、Workbench、Portal、Account、Auth、路由、生产媒体或真实部署。
- 不执行 G53-7、黄金切片、真实 API、Key 读取、领域采用或生产准入；RQ-188–191
  的供应商观察不升级为产品 streaming 能力。

## 备选方案与取舍

### 方案 A：把 adapter 包成 `LLMProvider`

拒绝。同步合同要求一次完整 `ChatResponse`，而候选流还需要不完整边界状态；包装
会掩盖 `length` 与 EOF 语义，并可能被默认 ProviderRegistry 误选。

### 方案 B：给 `AgentLoop` 增加 streaming 分支

拒绝。会同时改工具调用、重试、Runtime Trace、截止时间和消息回放，扩大到生产
主线，且无法解决候选 profile v2 与已注册 v1 的身份冲突。

### 方案 C：隔离候选评测调用方（推荐）

保留现有产品合同，能把候选预算/Trace/授权开关放在一处；代价是要先实现独立的
边界观察投影和完整的身份/失败矩阵。

### 方案 D：直接重用现有诊断脚本

拒绝。诊断脚本是一次性 evaluation-only 入口，没有可复用的 provider-neutral
attempt 生命周期，也不能把 stream trace 安全投影成候选 ledger。

## 下一门与退出条件

RQ-195 评审完成，但不包含代码实现。下一精确 checkpoint 为
`candidate-runtime-wiring-design / pending`，先冻结 BoundaryObservation 的 API、
不完整流状态机、四元身份校验和 Trace 投影；通过该设计门后才考虑单独的 fake/local
调用方实现。该设计取得独立公共 CI 后，仍需另行授权才可执行真实候选诊断或注册运行时。

