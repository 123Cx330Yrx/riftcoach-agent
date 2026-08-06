# RiftCoach 路线校准任务计划

> **历史计划，已被替代。** 本文件保留 2026-08-01 的规划现场，不代表当前执行
> 状态。当前计划由 `.planning/.active_plan` 指向；唯一下一步见
> `docs/project_execution_state.md`。

## Goal

基于三份对话导出 PDF、当前 RiftCoach 仓库、EchoMind、AGI-Saber 与 OpenResearch/Sea 的已审计能力，形成一份不更改 0-8 主阶段编号、但能明确技术落点、实施顺序、验收证据和教学交付的统一路线。

## Current Phase

Phase 3 - 0-8 详细阶段规划（in_progress）

## Phases

### Phase 1 - 材料与现状复核

- Status: complete
- 逐份复核 Part 1、学习路线补充、Part 2。
- 核对当前仓库阶段 0-4 的真实实现与测试证据。
- 提取所有对后续路线具有约束力的主张。

### Phase 2 - 技术点决策矩阵

- Status: complete
- 将 Skill、Agent Loop、Agent SDK、LangGraph、RAG、Memory、MCP、Subagent/Multi-Agent、Eval、Observability、Sandbox、Fine-tuning 映射到真实需求。
- 标记为核心必做、阶段性实验或条件性能力。
- 明确 Pi、Claude Agent SDK、EchoMind、Saber、OpenResearch/Sea 的吸收边界。

### Phase 3 - 0-8 详细阶段规划

- Status: in_progress
- 为每个阶段写明问题、原理、子阶段、代码产物、测试、失败模式、教学交付、简历证据和退出门槛。
- 保持阶段编号稳定，必要时用 A/B/C 子阶段展开。

### Phase 4 - 冲突审查与路线定稿

- Status: pending
- 检查学习路线与项目路线是否混淆。
- 检查是否存在技术堆砌、过度后置、重复运行时或无法解释的简历亮点。
- 形成推荐路线与被拒绝方案。

### Phase 5 - 正式文档与 ADR

- Status: pending
- 用户认可设计后，更新 `docs/roadmap.md`。
- 新增 Agent Runtime / SDK / LangGraph 分工 ADR。
- 修正 `docs/project_decisions.md` 的过时状态。

## Next Step

编写 0-8 详细阶段规划草案，包含子阶段、产物、测试、教学和退出门槛。

## Decisions Made

| Decision | Rationale |
|---|---|
| 保持 0-8 九个主阶段 | 用户已要求阶段编号稳定，变化通过子阶段和 ADR 表达 |
| 先规划、后改代码 | 避免在技术落点仍不清楚时进入阶段 5 实现 |
| Pi/Claude SDK 不再只作为末尾对照 | 对照是采用门槛，真实产品职责必须提前明确 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| PowerShell 默认编码读取中文文档出现乱码 | 1 | 后续统一使用 UTF-8 或 Python 读取 |
