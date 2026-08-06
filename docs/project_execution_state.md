---
state_schema: 1
main_stage: 5
substage_group: "5C"
current_checkpoint: "5C-5"
status: in_progress
blocked_before: "5D"
---

# RiftCoach 当前执行状态

> 本文档是“项目现在做到哪一步”的唯一事实源。路线职责看
> `docs/roadmap.md`，历史需求看 `docs/requirements_change_log.md`，本轮执行
> 细节看 `.planning/.active_plan` 指向的计划，决策演变看
> `docs/roadmap_change_history.md`。

## 状态元数据

- 最后更新：2026-08-06
- 主阶段：阶段 5，进行中
- 当前子阶段组：5C Skill Router，进行中
- 唯一下一步：5C-5 Router Evaluation 第一批，冻结旧单 Skill 基线并重建双 Skill 数据集角色
- 禁止越过：5C-5、5C-6 分别完成前，不得进入 5D

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 进行中 | 第二个真实 Skill 合同已完成；旧 15 条单 Skill 开发/校准案例仍是未验收 WIP | 冻结旧基线，建立双 Skill 开发集与独立保留集，再记录可重复评测结论 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 未正式开始 | 设计文档仅记录了暂不引入模型的倾向 | 基于 5C-5 证据做正式“采用/暂缓”决策并记录理由 |

## 当前真实能力边界

已经存在的实现：

- 三态路由结果：`selected`、`rejected`、`ambiguous`；
- 无可用 Skill、无匹配 Skill、多 Skill 同时命中的明确原因码；
- Manifest 声明式必需信号组与排除信号；
- 排除信号在 Router 算法与 `RouterDecision` 合同两层都是硬否决；
- `recent-form-review` 与 `single-match-review` 两个真实用户 Skill Contract；
- 单局输入会验证 Summary v1.0、唯一目标 match、短局和 Timeline 缺失边界；
- 两个真实候选的近期选择、单局选择、混合范围歧义、裸 ID 拒绝和域外否决测试；
- 15 条参与过旧单 Skill 规则校准的开发集和可重复执行的评测 CLI；
- 当前已跟踪本地回归：`240 passed, 57 subtests passed`；单局合同、Catalog 与
  Router 定向测试 `37 passed`。

当前不能声称：

- 5C 已经完成；
- 路由对自然语言具有充分泛化能力；
- 已有独立路由 holdout；
- 已用独立评测集验证两个真实业务 Skill 的泛化或真实歧义处理；
- 已决定或实现 LLM Router fallback；
- Router 已执行 Skill、Tool、Harness 或模型调用。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-4 已形成 V1；阶段 5 完成 5A、5B、5C-1 至 5C-4 和第二个真实 Skill Contract；5C-5 进行中 | 5C 或阶段 5 已完成 |
| 项目理解 | 已逐步讲解并固化到单局 Skill Contract；5C-5、5C-6 仍需按原检查点讲解和确认 | 测试通过就等于项目所有者已理解 |
| 参考资料 | EchoMind、AGI-Saber、Sea/OpenResearch 已做源码/文档审计并建立选择性映射 | 已经接入或复用了这些项目 |
| GitHub/部署 | 单局 Skill 提交 `4103d42` 已推送到 `main`，Actions run `31068654700` 成功；未验收 5C-5 评测继续留在本地；网页产品尚未部署 | 本地 WIP 已全部同步到 GitHub 或线上 |

## 已裁决的首批 Skill 与事实审查边界

2026-08-05 的讨论同时确认了两点：

1. 先用一个 `recent-form-review` 样板稳定 Skill Contract 和 Router；
2. 首批宏观能力仍包含近期复盘、单局复盘和报告事实审查，并曾把三者都称为
   Skill，要求在 5C-4 后补齐再完成真实多 Skill 路由评测。

源码级复核发现，事实审查并不是缺失的第三个工作流：`EvaluatorStep`、
`ChatEvaluationAdapter` 和 `ReviewHarness` 已经提供类型化输入输出、复用入口、
修订预算和强制发布门禁。把它再包装成 Skill 只会复制合同。

- `recent-form-review`：已存在的用户可路由 Skill；
- `single-match-review`：已建立的第二个用户可路由 Skill；
- 报告事实审查：继续作为 Harness `EvaluatorStep` 强制执行，不是 Skill。

未实现的调用模式合同和 `report-fact-check` Skill 已在写代码前取消。实施顺序修正
为单局 Skill、真实双 Skill 路由评测、模型兜底决策。详细裁决见 ADR-0008 和
ADR-0009。

## 2026-08-06 阶段漂移事件

### 发生了什么

原计划明确包含 5C-1 至 5C-6，但一次实现批次把 5C-3 的代码、5C-4 的部分
拒绝/歧义行为和 5C-5 的初步开发评测一起完成后，文档被直接更新成“5C
完成，下一步 5D”。这把“代码已提前存在”误写成了“原检查点已经逐项完成”。

### 根因

- 原始 5C-1 至 5C-6 清单只存在于长对话，没有写进仓库；
- 旧 `.planning` 任务停在 2026-08-01，且没有 `.active_plan`；
- 没有根级 `AGENTS.md` 强制恢复上下文和同步状态；
- 多份状态文档并存，却没有唯一当前状态源；
- 实现计划错误地把一个批次的测试通过当成整个 5C 的完成条件。

### 修复原则

- 恢复原有 5C-1 至 5C-6 边界，不回滚已经写出的有效代码；
- 提前实现的内容回到原子阶段逐项讲解、复核和验收；
- 以后“继续”只推进本文件列出的唯一下一步；
- 每次状态变化同时更新当前状态、活动计划和冲突文档。

### 持久化与自动保护

- 本文件头部的机器可读元数据与正文共同构成同一个唯一状态源；
- `.planning/.active_plan` 指向当前任务的计划、发现和进度三份持久记忆；
- `docs/requirements_change_log.md` 追加记录跨轮次长期要求，不静默覆盖旧决定；
- `scripts/check_project_governance.py` 在本地和 CI 核对当前检查点、活动计划、
  九阶段编号、需求编号和工作约束；任何冲突都先阻止功能推进；
- 自动检查降低再次漂移的概率并让错误可见，但不能替代用户对阶段验收的确认。

## 下一检查点的范围

`5C-5-prep-1 Skill Invocation Contract` 与 `5C-5-prep-3 report-fact-check Skill`
已在功能代码开始前由 ADR-0009 取消，并保留在历史记录中。

`5C-5-prep-2` 已完成：单局 Skill 明确了输入、输出、触发/排除边界、工具权限、
预算、步骤和成功标准，Catalog 现在有两个真实用户候选。

`5C-5` 的第一批工作先把五个未跟踪文件中的旧单 Skill 开发/校准结果冻结为历史
基线，再明确双 Skill development 与 independent holdout 的角色、污染记录和案例
边界。随后才运行正式双 Skill 评测并分析误路由。5C-5 不执行 Skill、不调用 Tool、
Harness 或模型，也不完成 5C-6 的模型兜底决策。
