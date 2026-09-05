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

本地候选合同由 `tests/test_response_recovery_contract.py` 覆盖。RQ-184 已完成新的
exact-SHA 公共 CI 与同 SHA G53-3 协议证据（实现 A/B 及其公共 Actions 见项目状态记录），
但真正启用前仍必须有一次单独授权的真实诊断，以及成本、延迟、重复请求、失败和生产
Trace 的审查；这些未完成项存在时继续保持候选状态。RQ-185 的两次独立启动均在首回合
无可观察响应后中断，未生成结果或发送 `fresh_recovery`，因此不满足真实诊断退出条件；
后续需先复核传输/代理边界并取得新授权。

## RQ-186 诊断补充（2026-09-01）

RQ-185 的 20 秒客户端默认值被每请求 `ChatRequest.timeout_s=90` 覆盖。隔离诊断器现已把受校验的
请求级 deadline 同时用于 primary 与可能的 fresh-recovery，代码提交为
`94629161c5d3230629210444b5a1a38212799997`。一次新的 30 秒 primary 在约 30.141 秒后以
transport timeout 安全结算，未收到响应或 Usage，也未打开 recovery 槽位；脱敏结果 SHA-256 为
`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`。

该结果满足“截止必须真实进入请求并可观察退出”的诊断条件，但不满足真实恢复能力退出条件：30 秒低于候选
90 秒 Agent 窗口，且没有候选形状或恢复回合。因此 ADR 的 candidate-only 状态不变；是否执行完整候选窗口需
新的延迟预算裁决与授权。

## RQ-187 诊断补充（2026-09-01）

按授权使用候选完整 `timeout_s=90`、`max_tokens=8192`、SDK retries `0` 执行一次 primary。请求在 90.188 秒
以 transport timeout 安全结束，没有响应、Usage、finish reason 或 recovery；脱敏结果 SHA-256 为
`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，证据提交 `50ce5be`。

该结果排除“30 秒窗口过短”，但仍不能区分代理/连接/读取与服务端生成延迟，故不构成恢复能力或模型能力结论。
候选继续保持未注册；若继续，必须另立传输/生成路径拆分诊断与授权。

## RQ-188 诊断补充（2026-09-01）

用户扩大授权后，隔离诊断器执行了固定三路而非重跑长同步请求：合法 Flash thinking 最小控制、冻结短同步请求、冻结流式首块请求，最多三次调用且 SDK retries 为 0。三路均 observed；同步两路都是 `length + 空正文 + 非空 reasoning`，流式路约 687ms 观察到首个 reasoning chunk 后主动关闭。

正式脱敏结果 SHA-256 为 `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，诊断/source identity 为 `b67b4500ebdbff934e470fd92c1461184aa7c49b`。该结果把“endpoint/model 可达且生成已开始”与“长同步请求完整完成”分开，但不改变候选未注册、严格 Flash v1 的 2048/零额外调用，也不构成完整 provider-neutral streaming、G53-7 或生产准入。下一项是 evaluation-only 的输出额度/推理档位校准。
