# ADR-0072：采用有界 fresh-recovery 尝试合同（候选）

- 日期：2026-08-31
- 状态：accepted-local / candidate-only
- 范围：Stage 8 / 8E；GLM-5.3-Flash 响应完成度候选运行时

## 背景

RQ-181 证明过一种具体失败形状：`finish_reason=length`、正文为空、reasoning
非空、没有 ToolCall。RQ-182 已把这个形状做成脱敏的版本化策略，但当前统一
`ChatResponse`、AgentLoop、预算和 Runtime Trace 都只描述一次同步 Provider
调用。如果以后在适配器里偷偷再发一次请求，调用数、token、截止时间和失败原因
都会被低报，且无法区分“新的完整请求”和 API 原生续写。

## 决策

新增 `app/providers/response_recovery_contract.py`，只提供无 I/O 的候选合同：

1. `ResponseRecoveryRuntimeProfile` 精确绑定
   `zhipu/glm-5.3-flash`、`glm-5.3-flash-runtime-v2-candidate/2.0.0` 和
   RQ-182 候选策略；候选保持 `activation_state=candidate`，不进入现有注册表。
2. `ResponseAttemptSpec` 只允许两个有序身份：`primary`（序号 1）和
   `fresh_recovery`（序号 2）。第二次调用是重新提交的完整请求，不称为 API
   resume，也不复用 SDK 或 ToolRuntime retry。
3. `ResponseRecoveryBudget` 固定最多两次底层尝试、最多一次额外尝试，并对累计
   input/output token 与墙钟时间设置硬上限。`ResponseRecoveryLedger` 在每次尝试前
   预留、之后只结算一次；Provider 错误、Usage 缺失和超预算都消耗已经发出的槽位。
4. `ResponseAttemptOutcome` 和 `ResponseRecoveryTrace` 只接受结束原因、字段状态、
   ToolCall 数量、脱敏判定和资源数字，不接受 Prompt、正文、reasoning 原文、工具
   参数、Key 或 request ID。账本重新计算判定，不能信任调用方伪造的可恢复布尔值。
5. Trace 使用独立 schema `1.0`，不改写既有 `RuntimeTrace` schema。未来若要接线，
   必须显式注册新的 runtime profile、升级公共 CI/协议证据并重新审查生产 Trace。

## 为什么不直接改 Provider

智谱普通接口没有在当前合同中可证明的续写句柄；应用层第二次请求必须重新提交
完整消息。若现在把它塞进 `ZhipuProvider.chat()`，会绕过 AgentLoop 的一次调用
语义、ToolRuntime 的副作用边界和现有预算。先做可测试的尝试合同，能在无网络情况下
证明计数、拒绝和审计字段，再决定是否值得一次独立真实诊断。

## 预算与终止语义

- 首回合只有在 RQ-182 候选策略重新判定为精确白名单形状时，离线账本才会出现第二
  个计划槽位；结构化输出、工具、副作用、过滤、Usage 无效或非初始阶段均终止。
- 每个槽位的 8192 是候选单次输出上限，不是当前产品默认值；累计上限、时间上限和
  尝试数任何一个触顶都 fail closed。
- 第二次仍不完整、出错或再次达到 `length` 时，不得创建第三次尝试；Trace 保留两
  次已发出的尝试和实际观察到的资源。

## 不做的事

本 ADR 不修改 `ModelRuntimeProfile` 注册表、`ChatResponse`、`ChatMessage`、
`LLMProvider`、`ZhipuProvider`、AgentLoop、ToolRuntime、统一 Runtime Trace、
默认模型、Workbench、Portal/Account、Auth、路由或 `production_media`；不发真实
Provider 请求，不改变 RQ-180/RQ-181 旧证据，不宣称恢复能力、G53-7 领域准入、
公共生产成熟度或 8E/8F 完成。

## 退出条件

本地候选合同由 `tests/test_response_recovery_contract.py` 覆盖。真正启用前必须有
新的 exact-SHA 公共 CI、同 SHA G53-3 协议证据、一次单独授权的真实诊断，以及成本、
延迟、重复请求、失败和生产 Trace 的审查；任何一项未完成都保持候选状态。
