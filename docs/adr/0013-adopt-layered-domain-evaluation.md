# ADR-0013：采用分层领域评测与数据集生命周期

## 状态

已接受

## 日期

2026-08-13

## 背景

ADR-0012 准入了 Zhipu Adapter 的最小协议能力，但拒绝了 GLM-5.2 的真实
`recent-form-review` 能力。领域失败被上层压缩为
`knowledge_round_trip_incomplete`，说明只看最终文本或 terminal status 无法可靠定位
Provider、Agent、Tool、Evidence、Evaluation 与发布门禁中的失败层。

5D-7 还要为后续 Prompt/Context 实验和可能的第二 Provider 提供同任务比较。如果先调
Prompt 或先接新厂商，再补评测，会把案例泄漏、Provider 差异和控制流缺陷混在一起。

## 决策

采用版本化的分层领域评测：

- Dataset 冻结 Agent、Tool、Evidence、Evaluation、Terminal 和资源期望；
- Candidate 只提供脱敏结构化观测，不保存 Prompt、模型正文、思维链或原始异常；
- 每层使用 `pass/fail/unknown/not_applicable`，未知值不转成 0；
- 失败码使用白名单并按控制流确定 primary failure；
- development 可用于评测器开发，held-out 必须排除校准且显式确认规则冻结；
- 离线可控观测先建立评测器基线，之后才允许有限真实 Prompt/Provider 比较。

## 备选方案

### 用 5D-6b 单样例调 Prompt

会让发现问题的案例同时成为调参和验收题，产生明显过拟合。拒绝。

### 只用 LLM Judge 评价最终报告

无法验证工具与证据控制路径，Judge 还会引入额外模型不确定性。拒绝作为唯一方案；
后续可在严格结构化合同下作为其中一个评测步骤。

### 立即比较多个 Provider

没有同任务 Dataset 和失败分类时，比较结果不可归因。暂缓到 5D-7 后续批次。

## 影响

### 正面

- 能区分控制层故障与报告质量问题；
- 后续 Prompt 和 Provider 在同一把尺子下比较；
- 故障注入场景的正确降级不会被误算成领域成功；
- 真实失败可以保留为开发证据，不必恢复敏感原文。

### 负面

- 需要维护版本化 Dataset、Candidate 和结果；
- 第一批离线基线只证明评测器，不提供真实模型质量结论；
- 现有生产接缝仍会丢失部分安全错误来源，后续需基于评测证据最小修正。

### 中性

- 不改变 0-8 阶段、两个 Skill、RAG、Provider 或 Harness 架构；
- 不引入 LangGraph、Agent SDK、Multi-Agent、数据库或第二 Provider；
- 统一 Trace 仍属于 5E。

## 证据

- `docs/plans/2026-08-13-domain-e2e-evaluation-v1-design.md`
- `docs/adr/0012-partially-admit-zhipu-provider-capabilities.md`
- `data/evaluation/results/provider_capabilities/zhipu_recent_form_slice.json`
