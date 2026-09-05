# 8E：GLM-5.3 候选运行时接线评审（RQ-195）

## 状态

`review-complete / candidate-only / implementation-pending`。本计划只完成架构
评审和边界冻结，不新增产品代码、不注册候选、不打开 streaming，也不发送真实 API
请求。

## 评审问题

RQ-194 的显式 `ZhipuStreamAdapter` 已经可以把完整供应商流装配成中立
`ChatResponse`。本轮要确认未来候选运行时是否能安全消费它，以及如何与 RQ-182/183
的完成策略、候选 runtime profile、attempt ledger 和 Trace 对齐。

## 现状证据

- `ZhipuProvider` 和 `ZhipuStreamAdapter` 仍位于 provider 层；产品 `LLMProvider` 是
  同步接口，`capabilities.streaming=False`。
- `AgentRuntimeV1`、`AgentLoop`、`build_llm_tools` 和 `RuntimeExecutionFactory`
  只接受已绑定的 `ModelRuntimeProfile` v1；候选恢复合同使用独立的
  `ResponseRecoveryRuntimeProfile` v2 candidate。
- `ResponseRecoveryLedger` 已能预留/结算最多两个 attempt，并生成 body-free
  `ResponseRecoveryTrace`，但其当前设计是离线合同，`execution_allowed=False`。
- `ProviderStreamAssembler` 对不完整终态 fail-closed；这使它适合完整回答，却不能
  直接提供候选策略判定所需的 `length` 边界快照。

## 评审结论

推荐未来在 `app/evaluation/` 增加隔离的候选调用方，而不是改生产 Runtime。调用方
需要先精确校验以下四元身份：

| 身份 | 要求 |
| --- | --- |
| provider | `zhipu` |
| model | `glm-5.3-flash` |
| runtime profile | `glm-5.3-flash-runtime-v2-candidate` / `2.0.0` |
| completion policy | `glm-5.3-flash-fresh-recovery-candidate-v1` / `1.0.0` |

任何字段错配、候选对象被伪造、状态不是 `candidate` 或 policy/profile 不是精确注册
常量，都必须在 provider I/O 前拒绝。

## 必须先解决的设计缺口

`assemble()` 只返回完整 `stop`/`tool_calls` 结果。候选资格需要观察合法 Usage、
`finish_reason=length`、正文状态和 reasoning 状态；把 `StreamAdapterError` 当成
候选资格会混淆“完整合同拒绝”和“候选白名单形状”。下一门必须定义
`BoundaryObservation`（暂定名）或等价 API：

1. 复用 adapter 的 chunk/model/sequence/tool/Usage 校验；
2. 只输出 field state、finish code、tool count、Usage 数字、耗时和安全错误码；
3. 不返回部分正文/reasoning/工具参数，不让默认 `repr` 暴露它们；
4. 完整流继续走 `assemble()`，不完整流不能被包装成 `ChatResponse`；
5. 观察失败、取消、close 失败和缺 Usage 均标成 fail-closed/unknown，不能触发隐式
   retry 或 recovery。

## 预算、生命周期与回退

未来调用方的最小流程应为：校验身份 → 创建候选 plan → `reserve_next()` → 发出一次
primary → 将完整/边界观察转换为 `ResponseAttemptOutcome` → `settle()` → 生成
`ResponseRecoveryTrace`。当前 candidate profile 的硬上限为 2 attempts、1 次额外
调用、32,000 输入、16,384 输出、180,000ms；任何第三次预留都拒绝。由于
`execution_allowed=False`，即使首回合形状返回 `candidate_eligible`，本轮也只记录
`awaiting_recovery`，不能发第二次请求。

`StreamAssemblyTrace` 只能作为内部来源，不能直接写入统一 Runtime Trace。未来要有
明确的 allow-list projection，保留四元身份、状态码、Usage/耗时数字和 attempt 序号，
删除 Prompt、正文、reasoning、工具参数、Key、原始 request ID 和 SDK 对象。

## 失败矩阵（设计要求）

| 边界 | 必须结果 |
| --- | --- |
| open/read/translate 异常 | 关闭流、fail-closed、消耗当前槽位，不 retry |
| close 失败 | 安全错误码；不能伪造 EOF |
| 无 EOF、无 terminal 或无 Usage | 不完成；不能生成完整回答 |
| `length` + 不符合白名单 | `fail_closed`，不恢复 |
| model/request identity 错配 | 立即拒绝并毒化观察 |
| 工具/结构化合同存在 | 当前 recovery policy 拒绝 |
| 第二槽位/第三次调用 | 未注册 candidate 直接拒绝 |

## 退出条件与下一步

本轮只完成设计评审，退出时保持 Stage 8/8E `in_progress`、8F 未开始、
`production_media=0`。下一门是 `candidate-runtime-wiring-design / pending`：冻结
BoundaryObservation 的具体 API 和与 `ResponseAttemptOutcome` 的映射，再决定是否做
独立 fake/local 实现。未取得新授权前不做真实调用、不注册候选、不改产品 Runtime。

