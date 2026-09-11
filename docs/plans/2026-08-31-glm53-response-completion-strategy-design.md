# 8E GLM-5.3-Flash 响应完成策略设计

日期：2026-08-31  
状态：`authorized / implemented-local`  
范围：RQ-182；只做离线策略合同与 TDD，不发真实 Provider 请求。

## 1. 要解决的问题

RQ-181 在一次正文零留存诊断中观察到：`glm-5.3-flash` 的首个 Agent 回合以
`finish_reason=length` 结束，输出额度为 2048，正文为空、reasoning 非空、没有
ToolCall。当前 Provider-neutral `ChatResponse` 只允许完整正文或合法工具调用，
因此适配器安全地返回 `incomplete_chat_response`。

这里不能把 reasoning 当作正文，也不能单纯看到输出额度到顶就猜测发生了截断：
是否截断必须以供应商的 `finish_reason` 为准。还需要避免在 Provider、AgentLoop
和 ToolRuntime 之间偷偷追加一次请求，因为当前调用预算、Trace 和消息合同都只
描述一次同步 `chat()`。

## 2. 可选方案与取舍

### 方案 A：只把当前 `max_tokens` 调大

实现最简单，但不能说明如何处理仍然被 reasoning 耗尽、被过滤或返回非法组合的
响应；也会把未验证的新预算直接带入产品运行时。暂不采用。

### 方案 B：在适配器里自动续接或重试

智谱普通接口没有可证明的续写句柄，应用层只能重新提交完整消息。当前统一消息
合同不能安全保存“正文为空但 reasoning 非空”的不完整 assistant 消息；此外，
工具/评测请求的第二次调用会绕过现有预算和 Trace 语义。暂不采用。

### 方案 C：版本化边界判定器（本批采用）

新增纯函数式、不可变的响应完成策略。它只接收脱敏状态快照和受信的有限请求
上下文，输出四种可审计判定：完整正文、工具回合就绪、安全拒绝、候选可恢复。
当前唯一注册策略为严格 `v1`；一个更高上限的 fresh-recovery 候选只用于离线
验证白名单形状，不会被运行时解析或发起请求。

## 3. 合同设计

实现文件：`app/providers/response_completion_policy.py`。

### 3.1 策略身份

严格策略 `glm-5.3-flash-response-completion-v1`（`1.0.0`）必须同时绑定：

- provider：`zhipu`；
- model：`glm-5.3-flash`；
- runtime profile：`glm-5.3-flash-runtime-v1` / `1.0.0`；
- 当前输出上限：2048；
- 允许的额外调用：0。

候选 `glm-5.3-flash-fresh-recovery-candidate-v1` 使用未注册的 runtime identity、
8192 候选上限和最多一次额外调用。它的 `activation_state` 是 `candidate`，
`resolve_response_completion_policy()` 不会返回它，防止用户 metadata、模型输出
或调用方自行把候选提升为产品策略。

### 3.2 脱敏输入

`ResponseBoundarySnapshot` 只保存：

- `finish_reason` 的安全枚举码；
- content/reasoning 的字段状态；
- ToolCall 数量；
- Usage 是否有效。

`ResponseRequestContext` 只保存受信阶段、是否有结构化合同/工具/副作用，以及剩余
时间和 token 预算。两者都不接收 Prompt、正文、reasoning 原文、工具参数、Key 或
原始 request ID。

### 3.3 判定规则

| 输入形状 | 判定 |
| --- | --- |
| `stop` + 非空正文 + 0 ToolCall | `complete_text` |
| `tool_calls` + 至少一个 ToolCall | `tool_calls_ready` |
| `length` + 空正文 + 非空 reasoning + 0 ToolCall，且严格策略 | `fail_closed / length_reasoning_only` |
| 同一形状，候选策略且阶段、预算、无工具等白名单均满足 | `candidate_eligible`，但当前候选仍不允许执行 |
| `content_filter`、`insufficient_system_resource`、未知/缺失 finish、Usage 无效 | `fail_closed` |
| `length` 带正文、ToolCall、空 reasoning、结构化合同、工具、副作用或非初始阶段 | `fail_closed` |

候选白名单是精确交集，不根据 `output_tokens == max_tokens` 自行推断；`stop` 即使
刚好碰到上限也不自动续接。任何未来二次请求必须另行定义为 `fresh_recovery`，
不能声称 API 原生 resume。

## 4. 数据与控制流

```text
Provider 原始响应
  → 适配器已有解码/脱敏
  → ResponseBoundarySnapshot
  + 受信 ResponseRequestContext
  → 已注册策略 decide()
  → complete_text / tool_calls_ready / fail_closed

候选策略（仅离线）
  → 精确白名单形状
  → candidate_eligible
  → 当前 activation_state=candidate，停止，不发第二次请求
```

本批不改 `ChatResponse`、`ChatMessage`、`LLMProvider`、AgentLoop、Structured
Decoder、ToolRuntime、Runtime Trace 或领域预算账本。

## 5. TDD 与验收

测试文件：`tests/test_response_completion_policy.py`。

离线 Fake/纯对象测试覆盖：

1. 策略冻结、语义版本、精确 provider/model/runtime identity；
2. 当前严格策略的输出上限截断与调用数为零；
3. 候选策略未注册、不能隐式激活，最多只有一个未来调用槽位；
4. RQ-181 的 reasoning-only `length` 失败路径；
5. 完整正文与正常工具回合不被误判为隐藏重试；
6. filter、未知 finish、空正文、工具/合同/副作用/阶段/时间/token 预算等拒绝；
7. 快照和上下文只允许脱敏状态，禁止把原文塞进策略对象。

本地聚焦结果：`41 passed`。本批不执行真实 API，不覆盖 RQ-180/RQ-181 证据，
不改变默认模型、Portal、Account、Workbench、Auth、路由或 `production_media=0`。

## 6. 后续入口与限制

若要真正尝试候选恢复，新的 runtime profile 与预算/Trace attempt 合同、公共
exact-SHA CI 和同 SHA G53-3 已由 RQ-183/RQ-184 完成；仍需一次单独真实诊断授权，以及
对二次请求的成本、截止时间和失败语义审查。二次请求不得依赖 SDK 或 ToolRuntime 的
通用 retry，且只能返回新的完整 `ChatResponse`；当前策略没有执行入口，因此仍不能宣称
恢复能力、领域准入或生产成熟度。
