# ADR-0058：仅在 OP.GG nullable 历史排名字段接纳 JSON `null`

- 状态：Accepted for `8e-productization` preflight（2026-08-23）
- 关联：ADR-0048、ADR-0055、ADR-0057、RQ-086

## 背景

在新的明确授权窗口中，RiftCoach 复用既有 body-free Riot 结果并执行了一次真实
OP.GG `mid` lane-meta replay。真实调用仍被严格 adapter 拒绝，但 ADR-0057 新增的
诊断把失败收敛到 `Mid.rank_prev_patch`：字段索引 7、AST 节点类型 `Name`。该位置和
节点类型与受控 JSON `null` fixture 一致；真实响应长度和摘要与 fixture 不同，因此
不能把受控样例冒充 live body。

`rank_prev` 与 `rank_prev_patch` 在现有 typed contract 中本来就是 nullable integer。
上游自定义文本使用 JSON 风格 `null` 时，Python AST 会把它解析为 `Name`，而不是
`Constant(None)`，导致语义合法的缺失值在语法边界被拒绝。

## 决策

Lane Meta parser 只在字段索引 6、7 接受 `ast.Name(id="null")`，并立即归一化为
Python `None`。其他字段上的 `null`、大小写变体、任意其他 `Name`、属性访问、调用、
表达式和可执行节点继续 fail closed。

这不是对任意 JSON/AST 的准入，也不改变 OP.GG 的 partial provenance、允许用途、
patch/freshness 限制、最多 10 行、单次调用、deadline 或 body-free 错误合同。

## 备选方案

| 方案 | 裁决 | 原因 |
|---|---|---|
| 接受任意 `Name` 并视为空 | 拒绝 | 会掩盖未知 schema/token 漂移 |
| 对所有八个字段接受 `null` | 拒绝 | champion、rate、tier、rank 的 typed contract 非 nullable |
| 把远端文本改为宽松 JSON/eval | 拒绝 | 扩大代码执行、注入与未审计字段风险 |
| 仅在两个 nullable 字段接纳精确小写 `null` | 采用 | 与 typed 语义一致，变更最小且可负例证明 |

## 证据与限制

- live body-free diagnostic：
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v2.json`；
- controlled pre-fix fixture：
  `data/evaluation/results/mcp/opgg_mid_schema_drift_fixture_v1.json`；
- TDD：`tests/test_opgg_meta_adapter.py` 覆盖两个 nullable 字段成功，以及非 nullable
  字段、未知名称和大小写变体继续拒绝；
- evidence regression：`tests/test_riot_opgg_fusion_validation.py` 证明 live 结果 body-free、
  外部调用计数为 1/0/0，且 live 与受控 fixture 不是同一正文。

本授权窗口只允许并已执行一次真实 OP.GG call，因此本 ADR 证明修复由 live 诊断驱动，
但不把离线绿灯冒充“修复后 live replay 已通过”。若要形成真实两源成功 EvidenceBundle，
仍需新的明确授权执行一次最终验证。
