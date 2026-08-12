# 5D-6b GLM P3/P4 受控诊断设计

> 状态：用户已授权在 5D-6b 内继续完成有硬上限的真实 Provider 测试。本设计不进入
> 生产 Adapter、第二 Provider、5D-7 或 Prompt 质量调优。

## 1. 当前问题

2026-08-12 的完整 P1-P5 重跑使用 4/5 次真实调用，得到：

- P1 普通文本通过；
- P2 空 `issues` 的 Evaluation JSON 通过；
- P3 嵌套 issue 失败，响应有非空 reasoning、空 content，输出正好 1024 tokens，
  `finish_reason=length`；
- P4 返回一个 Function Call，但参数没有通过当前精确相等校验；
- P5 因 P4 失败而按依赖规则跳过。

这组证据不能解释成“GLM 不支持 JSON 或 Function Calling”。P2 已经证明 JSON mode
可以工作，P4 也已经证明 API 返回了 Function Call。失败分别位于推理预算和本地参数
验收边界。

## 2. 官方文档带来的新事实

截至 2026-08-12，智谱官方文档明确说明：

- GLM-5.2 默认开启 Thinking；
- 可以用 `thinking={"type":"disabled"}` 关闭；
- 使用交错式 Thinking + Tool 时，回传工具结果必须同时回传完整、未修改的
  reasoning content；
- JSON mode 仍是 `response_format={"type":"json_object"}`，Schema 由 Prompt 声明并在
 客户端严格验证；
- Function Calling 的 arguments 是 JSON 字符串，调用函数前必须验证。

RiftCoach 当前有意不持久化或回传模型思维链。因此 V1 不能在 P4 丢弃 reasoning 后
继续 P5。机器控制 JSON 和工具协议轮应显式关闭 Thinking；如果关闭后仍观察到非空
reasoning，探针 fail closed。

## 3. 比较方案

### 方案 A：原样重跑

最少改动，但很可能重复相同失败，无法增加诊断信息，拒绝。

### 方案 B：只提高 P3 `max_tokens`

可能让 P3 生成最终 JSON，但会把大量预算继续花在不需要的思考上，也不解决 P4
验收和 P5 reasoning 回传问题，拒绝。

### 方案 C：受控 Thinking + Schema 参数验收（采用）

- P1-P5 全部显式 `thinking=disabled`。P1 的职责是认证、端点、模型和文本协议基线，
  不是测试不稳定的厂商默认思考策略；
- P2/P3/P4/P5 显式 `thinking=disabled`；
- P2/P3 继续使用相同 JSON mode、Pydantic 模型和严格语义相等校验；
- P4 的 tool name、call ID 和 arguments JSON object 仍严格验证；arguments 改为按
  `_TOOL_SPEC` JSON Schema 验证，不再要求 `query` 文本逐字等于 probe fixture；
- P4 的 `top_k` 仍必须满足 Schema 的整数范围，额外键继续拒绝；
- P4 若在 disabled 模式下仍返回非空 reasoning，返回安全错误码并跳过 P5；
- P5 回传经过验证的实际 arguments 和固定只读 observation，再要求非空最终文本且
  不得再次调用工具。

## 4. 数据流与控制流

```text
冻结请求与最大 5 次预算
→ P1 disabled-thinking 文本基线
→ P2 disabled-thinking 简单 JSON
→ P3 disabled-thinking 嵌套 JSON
→ P4 disabled-thinking Function Call
   → 安全字段观察
   → call ID/name/JSON/Schema/reasoning 边界验证
→ P5 disabled-thinking Tool Observation final
→ 仅保存脱敏指标、状态与哈希
```

P1 失败仍停止 P2-P5；P4 失败仍停止 P5；无 SDK 自动重试。新结果使用独立文件，绝不
覆盖前两次 P1-P5 或 P1 diagnostic 历史证据。

## 5. 测试与成功条件

先用 Fake SDK 证明：

1. P1-P5 请求都带 disabled-thinking；
2. P3 在关闭 thinking 后可通过同一严格 Evaluation Schema；
3. P4 接受 Schema 合法但 query 措辞不同的参数；
4. P4 拒绝额外键、类型错误、范围错误和 disabled 后仍非空的 reasoning；
5. P4 失败时 P5 不调用；全部路径最多 5 次；
6. 结果不保存 Prompt、模型正文、reasoning 正文、原始 request ID 或异常。

离线回归通过后，最多执行一次新的 5-call 探针。五项全部通过才能进入生产 Adapter
离线 TDD；任一项失败都保留 5D-6b，并根据该项的新证据决定下一诊断，而不是盲目重试。

### 2026-08-12 运行后修正

首个受控版本只对 P2-P5 关闭 Thinking，但真实运行在 P1 使用 1/5 calls 后停止：API
返回响应，content 为空、reasoning 非空、`finish_reason=length`，128 output tokens 全部
耗尽。这与早期 P1 失败和 P3 失败属于同一默认 Thinking 故障族，而一次 P1 diagnostic
成功只说明默认行为不稳定。故将 P1 也纳入显式 disabled-thinking；历史结果保留，
不得覆盖或描述成网络/认证故障。

## 6. 当前限制与准确表述

即使新探针全部通过，也只证明当前账号、模型、端点、SDK 和冻结案例的低层协议可用。
它不证明真实 Skill 报告质量、稳定 SLA、Prompt Injection 防护、生产成本或第二 Provider
优劣。生产 `ZhipuProvider` 仍须通过 Task 4 的离线映射 TDD 和后续真实领域切片。
