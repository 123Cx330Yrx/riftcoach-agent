# 8E：GLM-5.3 候选 runtime 接线设计（RQ-196）

## 状态与目标

`design-complete / implementation-public / candidate-only`。本计划冻结的实现门已由 RQ-197 落地，并由 RQ-198 取得
同 SHA 公共 CI；所需接口和不变量已有公共可复现证据，但仍不注册候选、不改变产品 Runtime，也不发送真实 API 请求。

目标是让后续实现能够安全回答两个不同问题：

1. 这条流是否已经满足完整 `ChatResponse` 合同？
2. 如果没有，它是否准确落在候选策略允许观察的截断形状？

两个问题必须共享校验核心，但不能共享“把部分响应交付给产品”的语义。

## 已确认的代码接缝

- `ZhipuStreamAdapter.assemble()` 只在 EOF、合法 terminal 和有效 Usage 齐全时返回
  `StreamAssemblyResult`；不完整流会 `abort()`/fail-closed。
- `ProviderStreamAssembler` 已经负责 model、sequence、tool fragment、JSON、Usage、
  request identity 和完整回答边界，但内部保存正文/reasoning 以便组装，不能直接当作
  body-free observer。
- `ResponseBoundarySnapshot`/`ResponseCompletionPolicy` 已能做同步形状分类；它们缺少
  EOF、terminal 生命周期、close 状态和流耗时，且 policy 结果不能由 caller 伪造。
- `ResponseRecoveryLedger` 已有最多两个槽位和一次额外调用的离线合同；未来调用方必须
  先 reserve、后 open、最终恰好一次 settle。现有同步 Runtime、`AgentLoop`、Worker、
  `RuntimeTraceStore` 和默认 profile 不得被改成候选分支。

## 冻结的候选接口（实现时的最小形状）

### `CandidateRuntimeBinding`

不可变值对象，包含四元身份和尝试身份。构造时只接受以下 exact constants：

```text
provider_id = zhipu
model = glm-5.3-flash
runtime_profile = glm-5.3-flash-runtime-v2-candidate / 2.0.0
policy = glm-5.3-flash-fresh-recovery-candidate-v1 / 1.0.0
attempt_kind ∈ {primary, fresh_recovery}
attempt_ordinal = 1 or 2 (kind 与 ordinal 必须一致)
```

它不能从模型输出、请求 metadata 或环境变量动态解析；I/O 前须使用受信候选常量做
完整 equality/identity 校验。

### `BoundaryObservation`

不可变、可序列化但只允许白名单字段的单次流观察。拟定字段及规则如下：

| 类别 | 字段/规则 |
| --- | --- |
| 身份 | binding、resolved model、request ID SHA-256；不保存原始 ID |
| 生命周期 | `opened`、`eof_observed`、`terminal_observed`、`close_state` |
| 形状 | finish code、content/reasoning field state、bounded tool count |
| 资源 | `usage_state`；valid 时才有 input/output/cached 数字，否则全为 `None` |
| 时钟 | 单调 `elapsed_ms`，不允许负数、NaN、无界值 |
| 结论 | 内部推导的 observation state、next action、safe error code/stage |

`candidate_eligible` 不作为字段。只有在 EOF、terminal、close=closed 和 valid Usage
全部成立后，才调用既有 policy，将观察映射成 `ResponseBoundarySnapshot`；policy 的
输出才是唯一资格来源。

观察累积只保留布尔状态和计数。正文/reasoning 的值、工具参数和 SDK chunk 不得跨事件
保存；字段状态聚合必须区分 missing/null/empty/non-empty/non-string，不能把缺失当空。

### `CandidateZhipuStreamTransport`（下一门实现的端口）

这是 evaluation-only 的 transport port，不实现 `LLMProvider`。它将候选 v2 的请求
参数绑定到一个普通 API client：8192 单次 cap、90 秒 Agent/工具、120 秒 transport、
`temperature=1`、`top_p=0.95`、`max_retries=0`。它必须拒绝已绑定产品 v1 profile 的
Provider，避免 2048 cap 被悄悄当作候选 v2；同时不能接受未绑定的任意 profile。

实现可通过显式 adapter port 打开一次 raw stream，但翻译/校验必须调用 RQ-194 的共享
核心或通过完整 conformance 矩阵证明等价。transport 不进入 registry、composition root、
Worker、Runtime policy 或 unified Trace。

## 计划的控制流

```text
caller
  → validate binding + request shape + remaining budget
  → ledger.reserve_next()
  → transport.open_stream()          (open error also settles slot)
  → shared validation/translation
      ├─ complete branch → assembler → ephemeral complete result
      └─ boundary branch → body-free BoundaryObservation
  → policy reclassification (only for a complete boundary)
  → ledger.settle() exactly once
  → CandidateStreamTrace allow-list projection
```

`execution_allowed` 目前恒为 `False`。primary 即便得到候选形状，也只能写入
`awaiting_recovery`；不得打开第二条流。若未来另行激活，第二次只能是
`fresh_recovery`，最多两次尝试、最多一次额外调用、总 input 32,000、总 output 16,384、
总耗时 180,000ms；第三次预约必须失败。Unknown Usage 不得按零计入“可用余额”，而应
保留 unknown 标记并 fail closed。

## 实现任务（RQ-196 历史设计出口；已由 RQ-197 执行）

1. 先写 `BoundaryObservation` 值对象和共享验证核心的红灯测试；
2. 实现字段状态聚合、生命周期转移、EOF/terminal/Usage/close 规则和安全错误映射；
3. 实现只接受 exact candidate binding 的 transport port（fake client only）；
4. 为完整流/候选截断/中断/错配/工具/Usage/预算矩阵补 fake 测试；
5. 证明所有 `repr`、JSON、异常和 Trace 都不含 body、reasoning、tool args、Prompt、
   Key 或原始 request ID；
6. 回归现有 `ProviderStreamAssembler`、同步 Provider、AgentLoop、默认 composition、
   `capabilities.streaming=False` 和现有 response-recovery 合同；
7. 在干净提交上跑治理、compile、diff check、聚焦/相邻回归，并取得 exact-SHA 公共 CI。

## 失败与回滚策略

- 任一共享验证错误都毒化当前观察，关闭底层流并结算当前 reservation；不 retry。
- 没有真实 EOF 的取消/超时永远不能变成 candidate shape；费用和 Usage 保持 unknown。
- close 失败不能伪造 EOF；model/request identity conflict 不能继续消费。
- 若 fake conformance 发现 translator 漂移，撤回候选 observer 实现，保留 RQ-194 完整
  装配器，不修改生产 Provider。
- 若公共 CI 失败，只修复实现分支的离线合同；不把未通过的实现接到 Runtime 或发真实
  G53-7。

## RQ-197 实现证据（2026-09-01）

上面的七项实现任务已在隔离分支完成 fake/local 版本：新增
`app/evaluation/candidate_stream_contract.py`，包括精确 candidate binding、body-free
`BoundaryObservation`、不可变终态快照、字段 presence/状态聚合、候选 v2 注入式 transport port、
共享 `validate_provider_stream_event()` 和独立 `CandidateStreamTrace`。完整/不完整流、身份/序号/工具/
Usage/预算/时钟/关闭异常与状态伪造均有矩阵测试；不完整或异常流 fail-closed，不构造 `ChatResponse`。
聚焦及相邻回归为 `163 passed`，compileall、diff check、governance 通过；全量本地首错为缺少
`RIFTCOACH_TEST_DATABASE_URL` 的 PostgreSQL fixture。候选仍未注册、`execution_allowed=false`，没有真实 API 或产品 Runtime 接线。

## 退出条件与下一步

RQ-197 实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 已由 RQ-198 / Actions run `33507627615`
取得 exact-SHA 公共三 job 全绿证据，公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
Stage 8/8E 仍 `in_progress`、8F 未开始、`production_media=0`；严格 Flash v1 2048/零额外调用，GLM-5.2
仅作显式回退。当前唯一精确 checkpoint 是：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`

下一轮只设计独立 harness/ledger/Trace 接缝；fresh-recovery 真实诊断、G53-7、黄金切片或生产准入均未获自动授权。
本轮在此暂停。
