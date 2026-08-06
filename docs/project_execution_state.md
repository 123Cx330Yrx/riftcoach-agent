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
- 唯一下一步：5C-5 Router Evaluation 第二批，只运行双 Skill development v2 并分析误路由
- 禁止越过：5C-5、5C-6 分别完成前，不得进入 5D

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 进行中 | 旧单 Skill 结果已原样归档；双 Skill development v2 与 holdout v1 已建立并有角色/版本快照门禁，尚未运行正式成绩 | 只运行 development v2，逐条分析误路由并冻结开发规则；之后才运行 holdout 一次 |
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
- 旧 15 条参与过单 Skill 规则校准的案例已归档，并有 SHA-256 来源记录；
- 双 Skill development v2（23 条）与 independent holdout v1（12 条）已建立；
- 评测 CLI 会校验数据集角色、案例数量、候选 Skill name/version 快照；
- 当前本地完整回归：`252 passed, 57 subtests passed`；本批路由数据生命周期定向
  测试 `12 passed`（含 Router 评测基础 `42` 个相关测试）；compileall、治理预检通过。

当前不能声称：

- 5C 已经完成；
- 路由对自然语言具有充分泛化能力；
- 已用 holdout 成绩验证两个真实业务 Skill 的泛化或真实歧义处理；
- 已把 holdout 失败用于调节 Router 规则；
- 已决定或实现 LLM Router fallback；
- Router 已执行 Skill、Tool、Harness 或模型调用。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-4 已形成 V1；阶段 5 完成 5A、5B、5C-1 至 5C-4 和第二个真实 Skill Contract；5C-5 已完成数据生命周期第一批，进行中 | 5C 或阶段 5 已完成 |
| 项目理解 | 已逐步讲解并固化到单局 Skill Contract；本轮已讲清 development/holdout 泄漏边界；5C-5 正式结果和 5C-6 仍需讲解确认 | 测试通过就等于项目所有者已理解 |
| 参考资料 | EchoMind、AGI-Saber、Sea/OpenResearch 已做源码/文档审计并建立选择性映射 | 已经接入或复用了这些项目 |
| GitHub/部署 | 5C-5 数据生命周期第一批已推送到 `main`；修复/属性提交 `8bfb876`、`318755d` 的 Actions run `31076388257`、`31076432192` 均成功；正式 Router 成绩尚未运行，网页产品尚未部署 | 已推送就等于 5C-5 已验收或已有 holdout 成绩 |

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

`5C-5` 第一批已经把旧单 Skill 开发/校准结果原样冻结为历史基线，并建立双 Skill
development v2 与 independent holdout v1 的角色、污染记录、案例边界和 CLI 门禁。
下一批只运行 development v2，分析误路由并决定开发规则是否接受；在规则再次冻结后
才运行 holdout 一次。5C-5 不执行 Skill、不调用 Tool、Harness 或模型，也不完成
5C-6 的模型兜底决策。
