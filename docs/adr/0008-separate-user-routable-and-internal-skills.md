# ADR-0008：分离用户可路由 Skill 与系统内部 Skill

## 状态

已由 ADR-0009 取代，未进入功能实现

## 背景

RiftCoach 首批业务目标曾包含：

- `recent-form-review`：复盘多场近期对局；
- `single-match-review`：深度复盘一场指定对局；
- `report-fact-check`：检查报告与确定性事实、RAG 证据和推断边界是否一致。

前两个 Skill 对应用户主动提出的任务。第三个候选是报告生成后的内部质量步骤。
本 ADR 当时假设它具有独立 Skill 价值，因此试图解决它不应进入用户 Router 的
调用边界。

## 原决策

原计划为 Skill Manifest 增加 `user_routable` 与 `internal` 两种调用模式：Catalog
加载全部 Skill，但只把 `user_routable` 投影成 Router Candidate；事实审查作为
`internal` Skill 由 Harness/Runtime 显式调用。

## 被取代原因

后续源码级复核发现，事实审查已经由 `EvaluatorStep`、`ChatEvaluationAdapter`、
`ReviewHarness` 和独立评测 CLI 完整实现并复用。它没有第二套独立循环、工具集合、
预算或成功控制流；再包装成 Skill 会复制已有合同，并产生质量检查器自身是否还要
经过 `quality_gate` 的递归语义。

因此问题不再是“内部 Skill 如何隔离”，而是“事实审查是否应该成为 Skill”。
ADR-0009 裁决为否，并取消尚未实现的调用模式扩展。

## 影响

- 本 ADR 只记录曾经形成但未落地的方案，不能作为当前实现依据；
- 没有 Manifest、Catalog、Router 或 Skill 功能代码依赖本 ADR；
- 当前决策、替代方案与源码证据见 ADR-0009。

## 参考

- `docs/adr/0009-keep-report-fact-check-in-harness.md`
- `docs/requirements_change_log.md` RQ-023、RQ-024
