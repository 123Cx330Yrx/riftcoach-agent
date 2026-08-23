# ADR-0057：记录 body-free 的 OP.GG schema-drift 诊断并保持 fail-closed

- 状态：Accepted for `8e-productization` preflight（2026-08-23）
- 关联：ADR-0048、ADR-0055、ADR-0056

## 背景

8E 的一次真实 `mid` lane-meta replay 在严格 adapter 的字段字面量边界失败。
异常只暴露 `opgg_meta_result_invalid`，原始 MCP 正文按既定隐私合同没有保存；
因此我们知道存在上游内容/grammar drift，却不能凭猜测扩大解析器。

## 决策

adapter 在 fail-closed 的同时生成可选的 `OPGGMetaSchemaDiagnostic`。诊断只允许
保存：阶段、已知 position/row 名、allowlist 内的字段名和索引、AST 节点类型、文本
长度与摘要 hash。它不保存正文、字段值、异常正文、Prompt、Key 或网络响应。

受控回归 fixture 用一个 null-like 非字面量节点验证该诊断合同，但明确标记为
`controlled_schema_drift_regression`，不能被解释为真实 OP.GG 已确认采用该字段/令牌。
在真实 replay 产生足够的字段级诊断前，生产 parser 不扩大 allowlist；产品只能把该
工具投影为 `degraded/unavailable`。

## 取舍

| 方案 | 裁决 | 原因 |
|---|---|---|
| 直接接受任意 JSON/AST | 拒绝 | 会把未审计字段和潜在指令内容带入证据/Context |
| 只保留一个通用错误码 | 不足 | 无法在不泄露正文的情况下判断是否存在可审计 drift |
| 记录 body-free 结构摘要并等待新鲜证据 | 采用 | 可审计、可回归，且保持 fail-closed |

## 后果

- 真实网络结果仍与公共 CI 分离；没有新的授权就不重跑外部服务。
- 诊断样例可以进入测试/证据，但不能冒充 live schema 结论。
- 一旦获得新的有界授权，下一次 replay 应读取诊断并由 ADR/fixture 评审决定是否扩大字段合同。

