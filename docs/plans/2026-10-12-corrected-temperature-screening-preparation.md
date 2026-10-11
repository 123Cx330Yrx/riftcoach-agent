# 2026-10-12 修正控制后的温度筛查准备

## 目的

在不改变默认产品入口的前提下，使用已通过离线控制审计的五例，判断 review 温度 `1.0` 与候选 `0.2` 是否出现可解释的质量差异。该文件只记录准备，不授权调用。

## 固定请求

每例发送一次 baseline 和一次 temperature-02，顺序为：`claim-scope:1 initial`、`observed:3 final`、`observed:4 final`、`claim-scope:4 initial`、`scope:4 initial`。前三例为历史正确控制，后两例为历史真错控制。来源与报告绑定见 `docs/plans/2026-10-12-corrected-control-candidate.md`，离线审计产物为 `data/evaluation/results/corrected_temperature_control_candidate_audit_20261012.json`。

除 review 温度和候选 marker 外，模型、reasoning、top_p、完整来源、报告、工具 schema、请求职责、600 秒接缝及原有质量门保持不变。每个实际请求必须重新记录 request SHA、receipt SHA、usage、原生主审和独立全文审查；历史请求和回执只作来源证据。

## 预算与停止

- 最多 10 次 GLM-5.3/high 请求（5 对）。
- 共享上限 967680 tokens、3000 活动秒、86400 Host 秒；未缓存估价约 14.29504 元，非硬计费封顶。
- 不重试、不重评、不补发、不购买第六调用；单个语义拒绝或双审分歧记录后继续独立样本。
- 身份、来源、native、协议、传输、预算或主体不可用立即停整批；Provider 工具参数重复键等 assembly failure 按 receiptless 硬停止处理。

## 采用门

只有 10 次真实回执均完整可核验，且五个候选结果都通过双审：三份正确稿无实质误报、两份真错均检出、无实质漏检/误报和 Host 分歧，才支持下一步准备；即使满足，也不授予正式 15 资格，不拼历史批次。若控制标签、请求绑定或任何硬边界再次失败，停止并回到方案层，不沿旧 r2 重开。

## 当前状态

离线控制审计、报告/来源 SHA 绑定及 10 请求重建均通过；Provider 调用 0。执行需要新的明确成本授权、clean checkout、同 HEAD 公共 CI 和即时真实 native 预检。
