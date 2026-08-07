---
state_schema: 1
main_stage: 5
substage_group: "5D"
current_checkpoint: "5D-2"
status: in_progress
blocked_before: "5D-3"
---

# RiftCoach 当前执行状态

> 本文档是“项目现在做到哪一步”的唯一事实源。路线职责看
> `docs/roadmap.md`，历史需求看 `docs/requirements_change_log.md`，本轮执行
> 细节看 `.planning/.active_plan` 指向的计划，决策演变看
> `docs/roadmap_change_history.md`。

## 状态元数据

- 最后更新：2026-08-07
- 主阶段：阶段 5，进行中
- 当前子阶段组：5D Python 受限 Agent Loop，entry design 与 5D-1 已完成
- 唯一下一步：5D-2 Context Builder V1，只构造两个 Skill 的最小分层上下文、信任标签、确定性裁剪和 ContextSizer
- 禁止越过：5D-2 完成前不得进入 5D-3；5D-1 没有编译 `AgentRunRequest`、调用 AgentLoop/Tool/Provider 或接入 Harness

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 已完成 | development v2 为 23/23；independent holdout v1 单次运行后为 11/12，唯一失败已原样保存并分类 | 进入维护；holdout v1 永不用于调节当前规则 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 已完成 | ADR-0010 比较排除词、LoL 域信号、澄清、LLM 与 Embedding；决定 V1 暂缓模型兜底并定义重新采用门槛 | 进入维护；新鲜数据满足门槛后才能用新 ADR 重开 |

## 5D 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成证据 |
|---|---|---|---|
| 5D-entry-design | 审计现有接缝、比较组合方案、冻结数据流与教学顺序 | 已完成 | 5D 设计文档、ADR-0011、治理检查 |
| 5D-1 Skill Run Boundary Hardening | 统一 I/O 非空文本、selected identity、run_id 和输入 Artifact 绑定 | 已完成 | 设计/TDD 文档、`SkillExecutionBoundary`、共享 run ID/Artifact 编码、合同与篡改测试 |
| 5D-2 Context Builder V1 | 两个 Skill 的最小上下文、信任标签、确定性裁剪和 ContextSizer | 唯一下一步 | 尚无代码或测试 |
| 5D-3 Skill Run Compiler & Budget Enforcement | Manifest 权限/预算编译为 AgentRunRequest，并约束累积上下文 | 未开始 | 尚无代码或测试 |
| 5D-4 Evidence-Aware Agent Draft Preparation | AgentLoop + knowledge.search 生成 draft 与 KnowledgeEvidence | 未开始 | 尚无代码或测试 |
| 5D-5 Harness Composition & Typed Terminal Output | 通过 DraftPreparationStep 接入单一发布门禁 | 未开始 | 尚无代码或测试 |
| 5D-6a Structured Output Contract | Provider-neutral schema、Pydantic 校验和有限修复 | 未开始 | 尚无代码或测试 |
| 5D-6b Real Provider Capability Gate | 实测 GLM，并按同任务证据决定一个第二 Provider 候选 | 未开始 | 尚未选择厂商或模型 |
| 5D-7 Prompt/Context & Domain E2E Evaluation | 工具选择、事实/引用、注入、质量/成本/延迟评测 | 未开始 | 尚无新数据集或结果 |
| 5D-exit-review | 对照全部证据和 5E 前置项 | 未开始 | 5D 各项完成前不得进入 |

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
- development v2 已正式运行并保存到
  `data/evaluation/results/skill_router_v1_development_baseline.json`：23/23 精确匹配，
  selection/rejection/ambiguity accuracy 均为 `1.0`，false-selection rate 为 `0.0`；
- development 明细中没有误路由；该结果只支持冻结当前开发规则，不是泛化证据；
- independent holdout v1 已单次运行并保存到
  `data/evaluation/results/skill_router_v1_holdout_baseline.json`：11/12 精确匹配，
  selection/ambiguity accuracy 为 `1.0`，rejection accuracy 为 `0.8333`，
  false-selection rate 为 `0.1667`；
- 唯一失败 `holdout_device_performance_false_friend` 把“分析一下我最近键盘的表现”
  误选为 `recent-form-review`；实现符合当前字面合同，产品期望拒绝，分类为确定性
  Router 的域语义局限；
- 5C-6 已完成采用决策：确定性 Router V1 保持不变，不根据 holdout 增加“键盘”
  排除词，也不引入 LLM/Embedding；优先等待类型化产品入口、会话澄清与新鲜误路由
  数据，具体重新采用门槛见 ADR-0010；
- 5C 退出复核将命中决策的证据身份收紧为必须与候选 Skill 身份完全一致；
- holdout 冻结点元数据已从不包含双 Skill 合同的 `cfd2084` 更正为实际双 Skill
  合同提交 `4103d42`，没有修改案例、期望、规则或既有结果；
- 5D entry design 已完成源码级接缝审计；ADR-0011 决定 AgentLoop 只作为
  evidence-aware draft preparation，ReviewHarness 保持唯一评测和发布控制；
- 5D 已拆为 5D-1 至 5D-7 和 exit review；拆分本身不是功能实现；
- 两个 Skill 的关键输入输出文本现共享去空白、非空、集合去重规则，Skill 输出
  `run_id` 使用统一安全目录组件合同；
- selected `RouterDecision` 现在同时锁定 Skill 名称与版本，执行前必须与 Catalog
  中当前 `LoadedSkill` 的 Manifest 身份完全一致；
- `RunManifest`、`FileRunStore` 与 Skill 执行请求共享同一跨平台 run ID 规范，拒绝
  路径、盘符、Windows 保留名和超长值；
- `SkillInputArtifactBinding` 使用 Harness 实际 JSON/text 字节编码记录 Summary 与
  确定性报告的 kind、schema version 和 SHA-256；5D-5 仍需核对真实落盘 Artifact；
- `SkillExecutionBoundary` 会拒绝非 selected、缺失/漂移 Skill、错误 input model、
  run 不一致和内容/元数据篡改，并返回与调用方 payload 脱钩的输入快照；
- 当前本地完整回归：`276 passed, 80 subtests passed`；compileall、diff check 与治理
  预检均通过。

当前不能声称：

- 5D-2 Context Builder 或任何更后的 5D 功能已经实现；
- 路由对自然语言具有充分泛化能力；
- 小型合成 holdout 已证明路由对自然语言充分泛化；
- 已把 holdout 失败用于调节 Router 规则；
- 已实现 LLM Router fallback 或修复设备域假朋友；
- Router 已执行 Skill、Tool、Harness 或模型调用。
- 5D-1 的内容承诺已经等同于真实 Harness Artifact 落盘或 Agent 执行。
- `user_utterance` 已通过统一 Runtime/Trace 与最初 `RouterRequest` 形成不可变来源链。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-4 已形成 V1；阶段 5 完成 5A、5B、5C、5D entry design 与 5D-1，下一步为 5D-2 | 阶段 5 或整个 5D 已完成 |
| 项目理解 | 5D-1 已讲清路由版本锁定、安全 run identity、Artifact 规范字节/摘要和执行前 fail-closed 验票；Context 构造仍需在 5D-2 单独教学 | 输入绑定完成就等于 Agent 已经运行 |
| 参考资料 | EchoMind、AGI-Saber、Sea/OpenResearch 已做源码/文档审计并建立选择性映射 | 已经接入或复用了这些项目 |
| GitHub/部署 | `main` 已包含 5D-1 实现提交 `6bc4309`；GitHub Actions run `31179571780` 对该精确 SHA 全部通过；仍没有正式网页部署 | 代码与 CI 通过就等于已有可运行 Web Agent |

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

`5C-5` 已完成：旧单 Skill 基线原样归档；development v2 以 23/23 冻结规则；
independent holdout v1 随后只运行一次并得到 11/12。唯一失败是设备语义假朋友，
其期望拒绝、实际选中近期复盘，结果已原样保留且不会用于调节本版本规则。

`5C-6` 已完成：ADR-0010 决定 V1 暂缓 LLM Router fallback。单一小型合成 Bad
Case 不足以抵消模型带来的结构化输出、延迟、成本和故障复杂度；现有 GLM Adapter
也只声明 `text_chat`。未来先采用类型化入口和澄清，再以新鲜数据、新 holdout、
结构化输出与质量/成本证据重开模型实验。

`5C-exit-review` 已通过：完整证据、修复项、限制、框架中立边界和面试安全表述见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`。5C 现已完成。

`5D-entry-design` 已完成。采用 ADR-0011：AgentLoop 负责白名单工具调用和草稿准备，
`ReviewHarness` 仍是唯一评测、修订和发布控制面；通过 `DraftPreparationStep` 接缝
同时兼容旧顺序 Retriever/Generator 和新 Agent 路径。完整设计见
`docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`。

`5D-1 Skill Run Boundary Hardening` 已完成：两个 Skill 的关键文本合同、selected
name/version、共享安全 run ID、Harness 规范输入字节摘要和 Catalog-backed 执行前
校验均已有 TDD 证据。该内容绑定尚未创建真实 Harness Artifact，也没有调用模型或
工具。

唯一下一检查点为 `5D-2 Context Builder V1`。它只负责为近期复盘和单局复盘构造
不同的最小上下文，标记内部策略、Skill 指令、确定性事实、用户文本和外部证据的
信任语义，并用确定性 `ContextSizer` 裁剪。不得提前编译 `AgentRunRequest`、执行
AgentLoop 或进入 5D-3。
