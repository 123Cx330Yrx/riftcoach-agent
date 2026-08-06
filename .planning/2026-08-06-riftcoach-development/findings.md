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
- 历史提案曾把近期复盘、单局复盘和事实审查都称为 Skill；只先做一个是当时的
  实施顺序。该分类后来必须接受源码级独立价值复核，不能因历史数字自动保留。
- 原讨论曾要求 5C-4 后增加另外两个真实 Skill，再做真实多 Skill 评测；进入
  5C-5 前已显式复核，最终保留单局 Skill，事实审查回归既有 Harness Evaluator。
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

## 5C-5 前置事实审查分类裁决

- Skill 是独立任务工作流合同；Router、EvaluatorStep 和 Harness 分别负责用户
  意图选择、结构化质量判断和确定性发布控制，不能只因都调用模型就统称 Skill。
- `recent-form-review` 和 `single-match-review` 是两个真实用户任务，应进入 Router。
- 事实审查已有 `EvaluationRequest/Result`、`EvaluatorStep`、
  `ChatEvaluationAdapter`、独立 CLI 和强制 Harness 控制流，并有异常、复评和
  降级测试；复用能力已经存在。
- 把它包装成内部 Skill 不会增加新的循环、工具、预算或消费者，反而复制 I/O、
  Prompt/Parser，并让 Skill 自身 `quality_gate` 出现递归含义。
- 当前 `EvaluationRequest` 携带 `KnowledgeEvidence`，但评测 Prompt 尚未消费它；
  现阶段只能声称确定性事实和推断边界审查，不能夸大为完整 RAG 引用忠实度检查。
- 最终采用两个用户 Skill + Harness Evaluator；取消未实现的调用模式合同和内部
  事实审查 Skill。下一步直接建立 `single-match-review`。

## 资料优先级

- 专项 Part 1、Part 2、补充材料和 PDF (4) 用于理解后期收敛后的建议。
- 原始 Codex JSONL 用于确认本项目何时接受、修改或撤回这些建议。
- 1198 页 PDF (5) 是完整 GPT 历史，只做关键词和前因后果查漏，不机械继承。
- 实现完成度以仓库代码、测试、Git 和 `project_execution_state.md` 为准。

## 5C-5-prep-2 单局 Skill Contract

- 单局 Skill 不应接收 Riot ID 后自行拉取数据；它复用阶段 1 已验证的 Player
  Summary v1.0，并用 `target_match_id` 在 `matches` 中锁定恰好一行。
- 只传裸 match row 会丢失 Schema 版本、玩家身份和请求来源；传完整 Summary 是
  输入验证边界，不等于未来把所有 match rows 注入模型。最小上下文抽取属于 5D。
- 短局排除只影响近期聚合，不影响单局事实存在，因此短局可以复盘但必须提示
  外推限制。
- Timeline 缺失不能阻止所有单局分析，但错误原因必须非空，Timeline 派生标量
  保持 `None`、集合保持为空，不能把未知编码为零。
- Manifest 仍只授权 `knowledge.search`；玩家事实、Data Dragon 和发布决定分别由
  上游领域核心与下游 Harness 负责。
- 初版曾让“最近十局里这一场”优先单局，并尝试用连接词排除真正双任务。只读
  复核构造出“分析最近十局状态，再复盘这一场”等漏网语序，会静默选择单局并
  丢失半个请求。确定性字面 Router 无法可靠做句法优先级，因此最终边界改为：
  两种范围同时出现一律返回 `ambiguous`，由未来上层澄清。
- `summary_schema.md`、`validate_summary_document()` 与部分旧 fixture 对
  `timeline_error`、`is_short_game` 等辅助字段的严格度存在历史差异。本轮只在单局
  目标 Timeline 缺失时增加必要验证，不越级重写阶段 1 Schema。
- 旧 15 条路由开发集按一个真实 Skill 校准；第二个 Skill 加入后预期已过时，必须
  在 5C-5 冻结为历史基线后重建双 Skill development 和 independent holdout。
