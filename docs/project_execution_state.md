---
state_schema: 1
main_stage: 5
substage_group: "5C"
current_checkpoint: "5C-5-precondition"
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
- 唯一下一步：5C-5-precondition 首批真实 Skill 时序裁决
- 禁止越过：在前置裁决以及 5C-5、5C-6 分别完成前，不得进入 5D

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 初步实现，未收尾 | 15 条开发/校准案例；精确匹配率 `1.0`，错误选择率 `0.0` | 独立审计覆盖、指标和门禁；明确开发集不是 holdout；先裁决首批真实 Skill 与真实多 Skill 评测时序 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 未正式开始 | 设计文档仅记录了暂不引入模型的倾向 | 基于 5C-5 证据做正式“采用/暂缓”决策并记录理由 |

## 当前真实能力边界

已经存在的实现：

- 三态路由结果：`selected`、`rejected`、`ambiguous`；
- 无可用 Skill、无匹配 Skill、多 Skill 同时命中的明确原因码；
- Manifest 声明式必需信号组与排除信号；
- 排除信号在 Router 算法与 `RouterDecision` 合同两层都是硬否决；
- 15 条参与过规则校准的开发集和可重复执行的评测 CLI；
- 当前本地回归：`232 passed, 57 subtests passed`；5C-4 定向测试 `23 passed`；
  排除未验收 5C-5 WIP 的公开快照为 `228 passed, 57 subtests passed`。

当前不能声称：

- 5C 已经完成；
- 路由对自然语言具有充分泛化能力；
- 已有独立路由 holdout；
- 已用多个真实业务 Skill 验证歧义处理；
- 已决定或实现 LLM Router fallback；
- Router 已执行 Skill、Tool、Harness 或模型调用。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-4 已形成 V1；阶段 5 完成 5A、5B、5C-1 至 5C-4；5C-5 只有未验收的本地提前实现 | 5C 或阶段 5 已完成 |
| 项目理解 | 已逐步讲解并固化到 5C-4；5C-5、5C-6 仍需按原检查点讲解和确认 | 测试通过就等于项目所有者已理解 |
| 参考资料 | EchoMind、AGI-Saber、Sea/OpenResearch 已做源码/文档审计并建立选择性映射 | 已经接入或复用了这些项目 |
| GitHub/部署 | 本轮将公开基线同步到已验收的 4M、5A、5B 和 5C-4；未验收的 5C-5 开发评测继续留在本地；网页产品尚未部署 | 本地 WIP 已全部同步到 GitHub 或线上 |

## 待裁决的首批 Skill 时序

2026-08-05 的讨论同时确认了两点：

1. 先用一个 `recent-form-review` 样板稳定 Skill Contract 和 Router；
2. 首批宏观目标仍是近期复盘、单局复盘和报告事实审查，并曾明确提出在
   5C-4 后增加另外两个真实 Skill，再完成真实多 Skill 路由评测。

当前代码只满足第一点。合成候选可以证明歧义算法，但不能证明三个真实业务
Skill 的触发边界合理。该历史要求没有被明确撤销，也不应在本轮治理修复中直接
强制实现。5C-4 现已完成；进入 5C-5 前，必须向用户讲清“维持原时序”与
“按调用性质调整真实 Skill 扩展”的架构与工作量差异，并取得明确裁决。

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

## 当前决策门的范围

`5C-5-precondition` 不是新增产品子阶段，而是执行 RQ-018 已记录的进入条件：
判断 `single-match-review` 是否应成为第二个用户可路由 Skill，以及
`report-fact-check` 应由用户 Router 选择还是由 Harness/Runtime 内部确定性调用。
取得用户明确裁决前，不实现新 Skill，不收尾 5C-5，也不进入 5D。
