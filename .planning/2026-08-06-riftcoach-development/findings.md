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

- 正式运行前确认治理预检与 12 个生命周期测试通过，输出文件不存在；从两 Skill
  合同实际冻结提交 `4103d4297e17b6dc54fa1402764414b0a1ef542c` 到首次 holdout
  结果提交，Router、文本规范化和两个 Skill Manifest 没有差异。
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
- 5C exit review 发现 holdout 元数据曾误填前一个文档提交 `cfd2084`；该提交尚未
  包含两 Skill 合同。现只更正 provenance 为 `4103d42`，没有改用例、期望标签或
  路由规则，也没有重跑 holdout，因而不会把独立失败污染成开发校准数据。

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

## 5C Exit Review

- 5C-1 至 5C-6 的实现、评测和决策证据齐全；Skill Router V1 可以退出，但该结论
  只涵盖选择层，不包含 Skill 执行、Provider、Tool、Harness 或报告生成。
- `RouterDecision` 原合同只要求候选证据存在，允许夹带非候选 Skill 证据。先补两条
  失败测试后，现要求 selected/ambiguous 的 evidence 身份与 candidate 身份完全
  一致；rejected 的部分证据语义保持不变。
- holdout 的 `rules_frozen_at_commit` 原填 `cfd2084`，但 Git 树证明该提交还没有
  `single-match-review`；真实双 Skill 合同首次完整提交为 `4103d42`。从该提交到
  首次结果提交 `6a0d952`，Router、规范化代码和两个 Manifest 零差异。
- provenance 更正没有改 holdout 案例、标签、规则或结果，也没有重跑 holdout；
  11/12 与设备域 Bad Case 继续作为未污染证据。
- 5C-4 教学文档已增加后续演进说明，区分当时单 Skill 排除边界与当前双 Skill
  混合范围歧义，避免历史快照冒充当前规则。
- 发现 `RecentFormReviewInput.deterministic_report` 和两个 Skill Output 的非空文本
  规范化仍不一致。这不改变 Router 结果，作为 5D 执行输入硬化前置项保留。
- 5D 只能通过现有 Pydantic/Protocol 边界接入 Agent Loop；未来 LangGraph、Pi 或
  Claude Agent SDK 也只能替换 Runtime 编排，不能绕过 Skill 权限、Tool Runtime
  或 Harness 发布门禁。
- 聚焦回归 `66 passed`；完整回归 `256 passed, 57 subtests passed`。5C 通过退出
  复核，唯一下一步变为 5D 的设计和细分，尚未实现 5D。

## 5D Entry Design - Initial Recovery

- Canonical state authorizes only the 5D entry-design checkpoint: audit existing contracts,
  compare integration approaches, and split 5D into teachable checkpoints. No 5D feature code
  is authorized in this turn.
- 5D must connect existing 5A Agent Loop, two Skill contracts, Provider/Tool Runtime and Harness;
  it must not create a second orchestration stack or bypass the Harness publication gate.
- Capability matrix assigns Prompt/Context Builder V1, structured Provider output, untrusted
  context boundaries and Prompt Evaluation to 5D. Unified Trace/Usage/runtime surface remains
  5E; Session/Memory remains stage 6; third-party Runtime adoption remains 5F.
- Current architecture remains framework-neutral. LangGraph, Pi or Claude Agent SDK may later
  replace orchestration only after the same domain contracts and evaluations can be preserved.
- `AgentRunRequest` already owns messages, allowed tool names, iteration/tool budgets, timeout and
  metadata. 5D should translate Skill permissions/budgets into this existing request instead of
  inventing a parallel executor contract.
- `AgentLoop` currently returns raw `ChatResponse.content`; it does not validate a Skill output
  schema, attach Artifact identity, invoke Harness evaluation, or distinguish trusted facts from
  untrusted user/RAG/tool text.
- Provider capability flags already include `STRUCTURED_OUTPUT`, but `ChatRequest` has no response
  schema/format field and capability negotiation cannot yet require it. `ZhipuProvider` honestly
  declares text chat only, so real structured output is a missing end-to-end capability, not a
  switch that can simply be enabled.
- Tool observations are stable JSON envelopes and tool allowlists are enforced before execution,
  but observation text can still contain untrusted external content. 5D needs explicit context
  labels and instructions; JSON serialization alone is not prompt-injection isolation.
- The 5A loop is deliberately synchronous and bounded. Streaming, cancellation, resume, unified
  Trace and session state should not be pulled into 5D because their approved consumers are 5E/6.
- Skill Manifest budgets map directly to existing `AgentRunRequest` iteration/tool/timeout fields;
  `max_context_tokens` has no active enforcer yet. Skill quality-gate fields map to HarnessConfig,
  but no composition layer currently performs either translation.
- `LoadedSkill` already bundles validated Manifest, SKILL.md instructions and Pydantic input/output
  model classes. Loading intentionally grants no execution authority; 5D needs a consumer that
  validates input first, then derives the least-privilege run request.
- Skill outputs are terminal product contracts (`published/degraded/rejected`, run_id, report,
  score, evidence IDs and warnings). A raw AgentLoop final message therefore cannot be returned as
  a Skill output; only the Harness terminal decision and final Artifact may populate that contract.
- `ReviewHarness` already owns retrieval, draft generation, evaluation, bounded revision and the
  sole publication/fallback decision. It currently has no Skill identity, target-match/focus input,
  or AgentLoop integration, so 5D should adapt a Skill execution into existing Harness steps rather
  than create a second quality gate.
- Existing chat generator/evaluator/reviser adapters call the LLM through the `llm.chat` tool path.
  5D must deliberately decide where the AgentLoop participates to avoid two nested or competing
  model execution paths.
- The current CLI composition pre-retrieves RAG, then calls a one-shot `ChatCoachGenerator` through
  `llm.chat`; it never uses `AgentLoop`. Simply wrapping this unchanged path in a Skill would satisfy
  naming but would not produce the approved 5D bounded Agent execution.
- Conversely, letting AgentLoop call `knowledge.search` dynamically conflicts with the current
  Harness order (`retrieve -> generate`) unless collected tool evidence is converted back into the
  same `KnowledgeEvidence`/Artifact contract before evaluation. This is the central 5D integration
  seam, not a reason to replace Harness.
- The safest likely direction is one outer Skill execution coordinator: validate Skill input,
  assemble trusted context, run the bounded AgentLoop as draft generation with only the Skill
  allowlist, normalize its tool evidence, then hand the draft/evidence into the existing Harness
  evaluation/publication path. Exact method boundaries require a small Harness extension rather
  than a second Harness or nested LLM ToolRuntime.
- `FileRunStore` already gives immutable run namespaces and Artifact digests. 5D should attach
  selected Skill/input/context artifacts to this existing run identity rather than create a new
  unrelated run ID. Adding the richer unified event/usage Trace remains 5E.
- Three approaches were compared. Wrapping the legacy Harness path would not use AgentLoop;
  letting AgentLoop own evaluation/publication would duplicate Harness; using AgentLoop as an
  evidence-aware `DraftPreparationStep` preserves both dynamic tool choice and one quality gate.
- ADR-0011 adopts the third approach. `SkillReviewExecutor` validates selected identity and typed
  input, Context Builder/Compiler derive messages/permissions/budgets, AgentLoop returns a draft
  plus actual tool evidence, and ReviewHarness alone constructs terminal publication state.
- Structured output is intentionally scoped first to machine-consumed `EvaluationResult`; the
  Coach report remains Markdown and terminal Skill Output is built from Harness artifacts. Real
  Provider admission is delayed until the schema and domain evaluation contract are stable.
- 5D is now split into entry design, 5D-1..5D-7 (with 5D-6a/6b separated), and exit review. The
  exact next checkpoint is 5D-1 input/identity/run binding only; no Context Builder or model call.

## 2026-08-07 5D-1 execution-boundary audit

- `RecentFormReviewInput.deterministic_report` still accepts whitespace-only text, while the
  single-match input already strips and rejects it. Both Skill outputs also accept blank-looking
  `run_id`/`report` values and unnormalized blank or duplicate evidence/warning strings.
- `SkillRouteCandidate` carries the Manifest version, but `RouterDecision` currently retains only
  the selected name. An execution boundary therefore cannot prove that the routed version is the
  same `LoadedSkill` version obtained from the Catalog immediately before execution.
- `RunManifest.new()` and `FileRunStore` validate run IDs separately. The store blocks obvious path
  traversal, but the duplicated rules can drift and do not define one portable, bounded run-name
  grammar.
- 5D-1 needs an immutable pre-execution contract that binds a selected Router decision, the exact
  Catalog Skill name/version, a validated typed input, a safe run ID, and content digests for the
  player summary and deterministic report.
- This binding is a content commitment for future Harness input Artifacts. It must not create a
  second run namespace, write `FileRunStore` records, build model context, compile an
  `AgentRunRequest`, call a model/tool, or compose the Harness; those remain later 5D checkpoints.
- 5D-1 can validate non-blank `user_utterance`, but `RouterDecision` does not carry the originating
  `RouterRequest` identity. The application currently passes both in one call; an immutable
  route-request-event provenance chain remains a 5E Runtime/Trace concern and must not be claimed
  as solved by the input Artifact binding.
