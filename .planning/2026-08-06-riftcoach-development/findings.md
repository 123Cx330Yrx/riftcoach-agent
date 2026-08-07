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

## 5C-5 第一批数据生命周期复核

- 旧 15 条案例和结果已原样归档；SHA-256 分别记录在
  `data/evaluation/history/skill_router_v1_single_skill_baseline_manifest.json`，
  没有重新生成或改写旧 `1.0` 结果。
- 旧运行的精确未提交工作树 SHA 无法从 Git 恢复；可由结果、单候选行为、
  `recent-form-review@0.1.0` Manifest 和公开提交 `02528db` 重建兼容快照，
  因此 provenance 明确标记为 reconstructed。
- 双 Skill development v2 共 23 条，保留旧案例但逐条记录 Manifest 示例、历史
  校准、Bad Case、直接单测或边界设计等污染来源；它只用于调试和回归。
- independent holdout v1 共 12 条，声明 `role=held_out`、
  `calibration_excluded=true`，并要求规则冻结确认；它是小型维护者编写的合成集，
  不是生产自然语言泛化证明。
- Router 评测现在校验数据集角色、案例数量和 `(Skill name, version)` 快照；开发
  CLI 默认拒绝 holdout，防止误用。该批只验证生命周期门禁，没有运行任何新数据集
  的正式 Router 成绩。

## 5C-5 第二批 development v2 结果

- 在治理预检通过、工作树干净且候选快照仍为 `recent-form-review@0.2.0` 与
  `single-match-review@0.1.0` 后，只运行了 development v2，没有运行 holdout。
- 23 条案例全部精确匹配：10 条 selected、11 条 rejected、2 条 ambiguous；
  selection、rejection、ambiguity accuracy 均为 `1.0`，false-selection rate 为 `0.0`。
- 逐条结果没有 mismatch，因此没有触发词、排除词、期望标签或产品歧义需要修改。
- 结果文件 SHA-256 为
  `1e57bcdf6f8727c28ea0f733817fd2a17705db99816d28f3afb7b3da4a6ab586`。
- 该数据集明确参与过开发校准，`1.0` 只证明当前规则覆盖已知开发案例；它不足以
  证明自然语言泛化，也不构成引入 LLM Router fallback 的证据。
- 当前开发规则可以冻结。下一步只能单次运行 independent holdout v1；其失败必须
  原样保存，不能反向用于修改本版本规则。

## 5C-5 第三批 independent holdout v1 结果

- 正式运行前确认治理预检与 12 个生命周期测试通过，输出文件不存在；从数据集声明的
  `cfd20847788810d5781312e03aaeab0eff8011bd` 冻结点到当前 HEAD，Router、文本规范化
  和两个 Skill Manifest 没有差异。
- holdout v1 只运行一次：12 条中 11 条精确匹配；selection accuracy `1.0`、
  rejection accuracy `0.8333`、ambiguity accuracy `1.0`、false-selection rate
  `0.1667`。
- 唯一失败为 `holdout_device_performance_false_friend`：期望拒绝“分析一下我最近
  键盘的表现”，实际选中 `recent-form-review`。
- 该句同时命中 `recent_scope=最近` 和 `review_goal=表现/分析`，又未命中任何排除词；
  Router 实现符合当前 Manifest 字面合同。由于目标实体是键盘设备而非 LoL 对局，
  期望标签正确，产品要求也明确，因此分类为确定性 Router 的域语义局限，不是实现
  bug、错误标签或需求歧义。
- 结果文件 SHA-256 为
  `b21a03c61a865df62997c0a110105de872d83b50c49734e92e77df6614430d88`。
- holdout v1 不得用于补“键盘”排除词或修改规则。5C-6 应比较域信号、开放式排除
  列表、澄清和模型兜底，但本轮不预先选择方案。
- 这是 12 条维护者合成案例，不是外部盲测或生产流量；11/12 不能证明自然语言
  充分泛化，也不能单凭一条案例证明必须引入 LLM Router。

## 5C-6 Model Fallback Decision

- 这次错误是 `selected`，因此“只在 rejected/ambiguous 时问模型”的常见兜底方案
  无法捕获它。若用模型修复，必须先定义低领域证据 selected，或复核所有 selected。
- 给排除词添加“键盘”会直接利用 holdout 调规则，并把开放世界域外概念变成无穷
  黑名单；强制所有请求含 LoL 专属词又会误拒绝“最近状态怎么样”等合法简写。
- 类型化产品入口能直接提供可信任务范围；当前 5P 明确的是近期复盘 API，其他
  复盘范围和对话澄清由阶段 6 的完整入口继续承接。它们比在当前路由层增加网络
  模型更符合产品依赖顺序。
- 当前 `ZhipuProvider.capabilities` 只有 `text_chat=True`，结构化输出尚未端到端实现。
  直接接 LLM Router 需要文本解析、非法输出、越界候选、429/超时和成本处理，不能
  只因为 Provider Registry 已存在就声称前置条件齐备。
- 决策为暂缓模型兜底，保持 `DeterministicSkillRouter` 与 Manifest 不变。设备域
  假朋友继续作为已知限制，而不是被隐藏或伪装修复。
- 重开门槛包括：新鲜数据中的多个独立失败族、新 development/holdout、Provider
  结构化输出、false-selection 改善且无硬排除/歧义回退、延迟/Token/成本/故障指标，
  以及越界或 Provider 失败时 fail closed。
- 详细教学与非功能需求见
  `docs/plans/2026-08-07-skill-router-model-fallback-decision.md`，最终决策见 ADR-0010。
