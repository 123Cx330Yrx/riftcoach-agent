# ADR-0071：采用版本化响应完成边界策略

- 日期：2026-08-31
- 状态：accepted-local
- 范围：Stage 8 / 8E 的 GLM-5.3-Flash 响应完成度诊断

## 背景

RQ-181 在一次有界诊断中观察到 `glm-5.3-flash` 首回合以
`finish_reason=length` 结束，输出额度 2048，正文为空、reasoning 非空、没有
ToolCall。现有 `ChatResponse` 和 `LLMProvider` 只接受完整响应，因此适配器返回
`incomplete_chat_response` 是正确的安全边界，但过去没有一个独立、可版本化的
策略来表达“为什么拒绝”和“未来何时才可考虑恢复”。

## 决策

新增纯离线 `ResponseCompletionPolicy`、`ResponseBoundarySnapshot` 和
`ResponseRequestContext`，放在 `app/providers/response_completion_policy.py`。

当前只注册严格 `glm-5.3-flash-response-completion-v1`：

- 精确绑定 `zhipu/glm-5.3-flash` 与 `glm-5.3-flash-runtime-v1/1.0.0`；
- 输出上限保持 2048；
- 额外调用为 0；
- `length`、过滤、未知结束原因和非法字段组合均 fail closed；
- reasoning 只作为状态参与判定，永不转为正文。

另保留一个 `activation_state=candidate` 的 fresh-recovery 候选，用于离线验证
严格白名单（初始 Agent 回合、`length`、空正文、非空 reasoning、0 ToolCall、
有效 Usage、无结构化合同/工具/副作用且预算足够）。候选使用未注册 runtime
identity、8192 候选上限和最多一次额外调用；解析器不会返回它，当前也没有执行
入口。

## 不做的事

本 ADR 不修改 `ChatResponse`/`ChatMessage`/`LLMProvider`、AgentLoop、Structured
Decoder、ToolRuntime retry、Runtime Trace 或领域预算账本；不提高产品默认上限，
不发真实 API 请求，不覆盖 RQ-180/RQ-181 证据。未来若要执行恢复，必须另建
attempt/预算/Trace 合同并标记为 `fresh_recovery`，不能把它称为 API 原生 resume。

## 证据与退出条件

`tests/test_response_completion_policy.py` 以纯对象/Fake 输入覆盖策略身份、
输出上限、RQ-181 失败形状、正常文本/工具回合和所有候选拒绝条件，当前聚焦结果
为 `41 passed`。后续候选启用前必须取得新 runtime profile 的 exact-SHA 公共 CI、
同 SHA 协议证据和单独真实诊断授权；本地测试通过不等于领域准入或生产成熟度。
