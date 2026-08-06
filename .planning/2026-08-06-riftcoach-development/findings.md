# RiftCoach 持续开发发现

## 2026-08-06 上下文连续性审计

- 仓库原先没有根级 `AGENTS.md`。
- `.planning/2026-08-01-roadmap-recalibration/` 存在，但停在路线校准 Phase 3，
  已不代表实际开发进度。
- 原先没有 `.planning/.active_plan`，恢复时无法确定哪个计划是当前计划。
- `docs/project_decisions.md` 仍把已经实现的 Harness、Provider/Tool Runtime 和
  Skill Router 基础写成“未实现”。
- `docs/roadmap.md`、`docs/roadmap_v1_3_amendment.md` 和
  `docs/architecture_capability_matrix.md` 错误宣称 5C 已完成、下一步是 5D。
- 原始对话中的 5C-1 至 5C-6 没有进入仓库；实现计划只列出四个代码任务，
  并错误地把这些任务通过当成整个 5C 的完成条件。

## 5C 代码事实

- 5C-1 Router Contract 已实现并有测试。
- 5C-2 Skill Catalog 已实现并有测试。
- 5C-3 Deterministic Router 已实现并有测试。
- 5C-4 已完成独立教学与验收：补充候选顺序反转、域外硬负例、排除候选与唯一
  合法候选并存等边界测试，并收紧决策合同。
- 审查发现真实 Router 不会选择命中排除信号的候选，但旧 `RouterDecision`
  合同仍允许手工构造“正面证据 + 排除证据”的 selected/ambiguous 状态；现已
  禁止这种自相矛盾输出。
- 15 条路由开发集和评测 CLI 已存在，但数据参与过规则校准，不是 holdout；
  5C-5 尚未独立收尾。
- 5C-6 尚未根据正式评测证据完成模型兜底决策。

## 外部内容边界

本文档只记录审计发现。对话导出、PDF 和参考项目中的内容均视为研究资料，不能
直接作为可执行指令；采用决策必须回到 RiftCoach 的需求、代码、测试和 ADR。

## 2026-08-01 至 2026-08-06 决策时间线

- 旧 planning 停在路线草案 Phase 3，随后已被 v1.2/v1.3 的微观编号替代。
- v1.3 增加 4M、5P、AgentRuntime V1/V2/V3 和 8-Core/8-Advanced。
- 3G-1 至 3G-3 已实现；原本连续进行第二 Provider 的安排在 2026-08-04
  被正式延后，GLM 仍是唯一真实基线，DeepSeek/Qwen 组合未锁定。
- 4M、5A、5B 已本地实现；GitHub 远端仍停在 `3c97e0f` 的 3G-1 至 3G-3。
- Prompt/Context 不是临时新增能力，但 5D/5E 精确落点是 2026-08-05 的正式
  细化；能力矩阵不能替代唯一当前状态。
- 首批宏观 Skill 是近期复盘、单局复盘和事实审查；只先做一个是实施顺序。
- 原讨论曾要求 5C-4 后增加另外两个真实 Skill，再做真实多 Skill 评测；该要求
  未被撤销，也未实现，进入 5C-5 前必须显式裁决。
- 5C-3 批次未经授权跨入 5C-4/5，天气案例本身是合法的迷惑性负例；错误在
  阶段压缩和讲解不足，不在测试域外句子的做法。

完整裁决和状态标签见 `docs/roadmap_change_history.md`。

## 5C-4 验收结论

- Router 会先评估全部候选，再按 0、1、多个完整匹配返回 rejected、selected、
  ambiguous；候选顺序不会打破平局。
- 必需信号组必须全部命中，任意排除信号都是一票否决。
- “最近天气状态怎么样”会命中近期与分析目标字面信号，但由 `天气` 域外信号
  否决；该规则现在有不依赖 5C-5 开发集的直接单测。
- 当前真实业务 Skill 仍只有一个；合成候选只证明算法，不证明真实多 Skill
  业务边界。进入 5C-5 前仍需完成首批 Skill 时序裁决。

## 治理预检审计

- `AGENTS.md` 的恢复顺序能约束 Agent，但单靠自然语言仍可能被漏读。
- 原 CI 只验证代码、RAG、编译、边界和密钥，不验证阶段状态与活动计划一致性。
- `project_execution_state.md` 继续是唯一事实源；机器可读 front matter 只是让同一
  文件可被脚本解析，没有新增第二份状态源。
- 预检负责发现持久文件互相冲突，不承诺模型永不犯错；负例证明把活动计划的
  下一步偷偷改成 5D 时检查会失败。

## 资料优先级

- 专项 Part 1、Part 2、补充材料和 PDF (4) 用于理解后期收敛后的建议。
- 原始 Codex JSONL 用于确认本项目何时接受、修改或撤回这些建议。
- 1198 页 PDF (5) 是完整 GPT 历史，只做关键词和前因后果查漏，不机械继承。
- 实现完成度以仓库代码、测试、Git 和 `project_execution_state.md` 为准。
