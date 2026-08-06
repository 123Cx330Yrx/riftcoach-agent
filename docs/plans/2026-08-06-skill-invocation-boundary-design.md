# 已取代设计：Skill 调用模式合同

## 状态

本设计在功能代码开始前由 ADR-0009 取代。

## 原提案

原提案准备为 Manifest 增加 `user_routable` 与 `internal` 两种调用模式，使
`report-fact-check` 作为内部 Skill 被 Catalog 加载但不进入用户 Router。

## 为什么没有实施

源码复核确认报告事实审查已经是 Harness 的 `EvaluatorStep`，并由同一 Adapter
同时服务 Harness 和独立评测 CLI。它没有缺失的独立执行能力，也没有新的工具、
循环或预算边界。为它增加内部 Skill 只会重复现有合同，并使 Skill 自身的
`quality_gate` 语义变得递归。

因此：

- `5C-5-prep-1 Skill Invocation Contract` 在写代码前取消；
- `5C-5-prep-3 report-fact-check Skill` 在写代码前取消；
- 事实审查能力本身保留在 Harness，不是被删除；
- 当前实施依据改为 ADR-0009 和事实审查分类复核文档。

## 参考

- `docs/adr/0008-separate-user-routable-and-internal-skills.md`
- `docs/adr/0009-keep-report-fact-check-in-harness.md`
- `docs/plans/2026-08-06-report-fact-check-classification-review.md`
