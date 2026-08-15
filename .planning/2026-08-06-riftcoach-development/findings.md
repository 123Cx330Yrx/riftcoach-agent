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

## 2026-08-07 5D-2 initial Context Builder audit

- The Provider layer already owns provider-neutral `ChatMessage` and `MessageRole` contracts.
  5D-2 should compile typed context sections into those messages rather than invent a parallel
  prompt-message type; creating `AgentRunRequest` itself remains 5D-3.
- The existing Harness `SummaryCompactor` is an untyped callable used by the legacy one-shot
  generator. It does not encode trust class, source, required/optional status, or whole-section
  trimming, so it cannot be reused as the new Context Builder contract without changing its
  semantics.
- `ValidatedSkillExecution` already provides the exact loaded Skill instructions, typed input,
  run identity, and input binding needed by 5D-2. Context permissions and budgets must still not
  be copied from user/RAG text; 5D-3 will compile them from the verified Manifest.
- The Summary v1 validator guarantees top-level player/recent/matches structure but intentionally
  permits richer per-match fields. 5D-2 therefore needs explicit allowlisted projections for
  recent-form and single-match facts instead of serializing the full input document blindly.
- The legacy `compact_summary()` is useful field evidence but still includes all match rows and
  copies excluded/failed rows wholesale. The new recent-form projection should explicitly retain
  aggregate metrics and a bounded set of allowlisted match facts; raw failure text is unnecessary
  model context and should not be copied.
- `single-match-review` must include exactly the selected match row plus its short-game,
  aggregate-inclusion, Timeline status/error, death/item/objective facts. It must omit
  `recent_summary` and every non-target match. A deterministic-report excerpt can include only
  lines that contain the exact target match ID; when no such excerpt exists, the typed target row
  remains the required fact source.
- `KnowledgeEvidence` already represents attributable RAG context. Initial citations can be
  projected as separate optional non-instructional sections so budget trimming removes a whole
  citation at a time. Dynamic Tool Observations are not initial messages and remain 5D-3/4 work.
- Manifest `max_context_tokens` is the hard ceiling. 5D-2 may accept only a lower test/runtime
  ceiling, never a higher override. 5D-3 must still re-check the compiled request and cumulative
  AgentLoop messages after tool observations.
- A vendor tokenizer is intentionally premature. V1 needs an injectable `ContextSizer` and a
  deterministic heuristic for preflight selection; its estimate is not actual provider usage and
  must be described as such until 5D-6b/5D-7 calibration.

## 2026-08-07 5D-2 Context Builder implementation findings

- A single generic summary compactor is unsafe for both Skills. Recent form needs aggregate plus a
  bounded trend sample, while single match must exclude `recent_summary`, every non-target row,
  and report lines that also mention another known match ID.
- Trust is derived from `ContextTrust`, not accepted as a caller-supplied boolean. Only internal
  policy and verified SKILL.md become system/instructional sections; player facts, user text and
  citations always render into the data-only user message.
- JSON envelopes preserve section identity/source/trust through final `ChatMessage` rendering.
  This narrows prompt-injection authority but is not proof that a model will ignore all malicious
  text; 5D-7 still needs adversarial model-level evaluation.
- Summary Schema v1 intentionally permits extension fields, so Context projections must remain
  explicit allowlists. This is both a token-control mechanism and a least-data boundary.
- Failed-match provider error text is operational diagnostics rather than coaching evidence. The
  recent context keeps only counts and safe match IDs; excluded rows keep only match ID, duration
  and exclusion reason.
- Whole-section selection is deterministic with the current small section count. Required sections
  are measured first; optional sections are tried by descending priority and stable source order,
  then rendered in original logical order. No JSON, Markdown row or citation is truncated.
- Dynamic Tool Observations are intentionally absent from the initial bundle. They remain normal
  `tool` messages and require cumulative pre-call budget enforcement in 5D-3.
- The completed builder still does not compile permissions, tool specs, loop limits or timeouts,
  call a Provider/Tool/AgentLoop, write Harness Artifacts, or publish a report.

## 2026-08-07 5D-3 initial compiler and cumulative-budget audit

- `AgentRunRequest` already owns messages, allowed tool names, iteration/tool-call limits and
  Provider timeout, so 5D-3 should extend this contract instead of creating a parallel Skill run
  request type.
- No compiler currently binds `ValidatedSkillExecution` and `ContextBundle`. A caller could still
  hand-assemble an `AgentRunRequest`; the new compiler must reject run/Skill/version drift and
  derive every permission/budget only from the verified Manifest.
- `AgentRunRequest` has no context ceiling, and `AgentLoop` never re-estimates accumulated messages
  before Provider calls. A Tool Observation can therefore make iteration 2 larger than the
  initial 5D-2 bundle without any deterministic stop.
- The current `DeterministicContextSizer` counts message content but not assistant `tool_calls`
  IDs, names or argument JSON. Cumulative enforcement must size the complete provider-neutral
  message envelope or large tool arguments can bypass the estimate.
- `ToolRegistry` provides deterministic `get()` and immutable ToolDefinition values. Compiler-time
  allowlist validation can therefore fail before any Provider call while `AgentLoop` retains its
  runtime defense-in-depth check.
- Existing `timeout_s` is passed to each `ChatRequest`; ToolRuntime has a separate per-tool deadline.
  5D-3 should map the Manifest value honestly without silently claiming a preemptive whole-run
  deadline, which the current synchronous Runtime cannot guarantee.

## 2026-08-07 5D-3 implementation findings

- `AgentRunCompiler` can remain a thin composition boundary because `AgentRunRequest` already owns
  every required control field. It rejects run/Skill/version drift, a Context ceiling above the
  Manifest, re-estimated message overflow and unregistered Manifest tools before AgentLoop.
- Context integrity belongs partly in `ContextBundle`: requiring messages to equal the canonical
  rendering of sections prevents a caller from pairing trusted section metadata with an unrelated
  forged system/user prompt.
- The original content-only sizer gave identical estimates (`13`) to short and very large ToolCall
  arguments. Serializing the complete provider-neutral message envelope closes that deterministic
  bypass while remaining tokenizer-free and injectable.
- Context enforcement must run before every Provider call, not only during initial ContextBuilder
  selection. Tests prove initial overflow makes zero Provider calls and post-observation overflow
  prevents the second Provider call.
- Manifest `timeout_s` is now a cooperative total deadline, not a preemptive cancellation claim.
  Provider requests receive decreasing remaining time; ToolRuntime receives an optional cap and
  uses the smaller of run remaining and tool policy timeout.
- A synchronous handler that ignores `ToolContext.remaining_s()` still cannot be hard-killed safely.
  The Loop checks the deadline after Provider/Tool return and performs no further step; process-level
  cancellation, resume and recovery remain stages 6/8.
- 5D-3 still does not create a Skill draft preparer, interpret knowledge ToolResult payloads as
  `KnowledgeEvidence`, call a real Provider, compose Harness or publish a report. Those boundaries
  remain 5D-4 and later.

## 2026-08-08 5D-4 initial draft/evidence audit

- `knowledge.search` already returns provider, abstained, diagnostics and fully attributable chunk
  rows through a validated ToolResult. Agent evidence must be derived from these actual execution
  records, never from source names claimed in the model's final Markdown.
- `LocalRagAdapter` already maps one knowledge payload into `KnowledgeEvidence` and citation IDs.
  Duplicating that logic in an Agent adapter would create two citation semantics; 5D-4 should
  extract one pure converter that both the legacy retrieval path and Agent path reuse.
- The new Agent path should return `CoachDraft + KnowledgeEvidence + AgentRunResult` as a bounded
  preparation result. The raw final response is only a draft and cannot become a Skill terminal
  output or published report before 5D-5 Harness composition.
- A failed knowledge tool call, malformed result payload, non-completed Agent run or missing final
  text must fail the preparation step explicitly. A direct final response with no tool call is
  valid and produces empty knowledge evidence.
- Multiple distinct searches can retrieve overlapping chunks. Evidence should preserve first-seen
  execution/rank order, deduplicate identical chunk IDs, assign stable K1..Kn IDs and fail closed
  if the same chunk ID carries conflicting attributable content.

## 2026-08-08 5D-4 implementation findings

- One shared converter can preserve the legacy single-search K1/source/context contract while
  extending it to multiple actual searches. It distinguishes no search from explicit all-search
  abstention, deduplicates first-seen chunks, and rejects count or attributable-content conflicts.
- `SkillAgentDraftPreparer` remains thin: it creates `AgentRunCompiler` from the exact Registry
  owned by its AgentLoop, validates the completed/final terminal state, and never evaluates,
  revises, publishes or constructs a Skill Output.
- Both real Skill identities now pass through Catalog, deterministic Router, execution boundary,
  ContextBuilder, Compiler and AgentLoop under a Fake Provider while ToolRuntime and local hybrid
  `knowledge.search` are real. This proves composition deterministically, not real-Provider tool
  calling quality.
- Model-authored Markdown is deliberately not parsed for evidence. A fabricated source string in
  the final response remains in the untrusted draft but never enters `KnowledgeEvidence`; only
  successful validated ToolExecutionRecords contribute sources and citations.
- A successful final response cannot rescue a failed knowledge call. Output-schema failures,
  unsupported non-knowledge executions, malformed attributable payloads and bounded stop reasons
  all prevent any preparation result from being returned.
- Runtime-level K1..Kn IDs are assigned after the searches complete. 5D-4 does not rewrite the
  model draft to invent citation coverage; Harness unknown-citation checks and domain citation
  evaluation remain 5D-5/5D-7 responsibilities.

## 2026-08-08 5D-5 initial composition audit

- `ReviewHarness` still owns separate `RetrieverStep` and `GeneratorStep` dependencies. The safe
  composition seam is one `DraftPreparationStep` returning `CoachDraft + KnowledgeEvidence`;
  a sequential adapter can preserve the legacy path without creating `run_prepared()` or a second
  quality-control flow.
- `SkillAgentDraftPreparer` already returns the exact draft/evidence pair needed by that seam and
  separately preserves `AgentRunResult`. The Harness should consume only the domain-neutral pair;
  the outer Skill executor should retain the Agent run so `app.harness` does not depend on
  `app.agent`.
- Skill terminal output must be rebuilt from the terminal manifest and integrity-checked artifacts:
  FINAL_REPORT for report text, the evaluation artifact matching the final attempt for score, and
  RETRIEVAL_EVIDENCE for source IDs. In-memory Provider text or pre-persistence evidence is not a
  terminal truth source.
- The two real manifests require a quality gate with minimum score 85 and deterministic fallback.
  5D-5 should map these values directly into `HarnessConfig`; `max_revisions` remains the existing
  bounded Harness policy because the Skill Manifest has no such field.
- `SkillInputArtifactBinding` already commits kind, schema version and SHA-256 using the same byte
  encoders as `ReviewHarness`. The composition layer must verify the actual stored input records and
  bytes against those commitments before returning a typed output.
- A final evaluation is identified by `evaluation_attempt_{manifest.attempt_id}.json`; this avoids
  accidentally returning the initial failed score after a successful revision. If no valid
  evaluation was persisted, the typed output score is `None`.
- Published output has no warning. Degraded/rejected outputs derive stable warning codes from the
  terminal decision and sanitized terminal reason, never from raw exceptions, Provider output or
  retrieved document text.

## 2026-08-08 5D-5 composition implementation findings

- The Harness seam is small enough to remain provider-neutral: `DraftPreparationResult` contains
  only `CoachDraft + KnowledgeEvidence`. The bound Skill adapter retains `AgentRunResult` outside
  Harness, so the quality package does not import Agent orchestration details.
- Re-exporting `review_executor` from `app.skills.__init__` creates a real circular dependency:
  Agent compiler imports `app.skills.execution`, while the package initializer would import the
  review executor back into partially initialized Agent modules. The executor therefore remains an
  explicit submodule import; this preserves the intended dependency direction instead of hiding the
  cycle with delayed imports.
- A score of 84 with verdict PASS still degrades under the real Skill minimum of 85. This proves
  publication is the Harness/Manifest decision, not the evaluator verdict alone.
- An Agent preparation exception is caught inside the Harness preparation step and becomes a safe
  `draft_preparation_failed` terminal reason. No evaluator runs, no draft is exposed, and the
  Manifest alone decides deterministic fallback versus rejection.
- Both real Skill identities now traverse Catalog, Router, ExecutionBoundary, ContextBuilder,
  AgentRunCompiler, AgentLoop, real local `knowledge.search`, ReviewHarness and their declared
  output model. The Fake Provider's invented `ghost-only.md` remains in its untrusted draft but does
  not enter persisted evidence source IDs.

## 2026-08-08 5D-6a initial structured-output audit

- `ProviderCapability.STRUCTURED_OUTPUT` already exists, but `ChatRequest` cannot declare a response
  contract and `required_capabilities_for()` never requires that capability. The flag is currently
  descriptive only, not an enforced request boundary.
- `ChatEvaluationAdapter` receives arbitrary parser output as a dict. The production parser checks
  top-level JSON, score, verdict and the existence of an issues list, but does not forbid unknown
  fields or validate the nested issue contract completely.
- The Coach report should remain Markdown. The first high-risk structured consumer is evaluator
  control data because its score, verdict and issues influence revision and publication.
- Only replacing the parser with Pydantic would leave Provider capability negotiation inactive.
  A second direct Provider loop inside Harness would bypass the existing Tool Runtime reliability
  path. The selected design passes one response contract through the current `llm.chat` adapter and
  validates it at the domain Adapter boundary.
- Repair must be a new bounded model call using the same response contract, not local regex
  extraction or default insertion. The original and repair response pass through the same strict
  decoder; a second failure becomes a sanitized `ProviderResponseError`.
- Current `ZhipuProvider` deliberately remains text-only in 5D-6a. A structured request must fail
  capability negotiation before SDK I/O until 5D-6b verifies and implements the real mapping.

## 2026-08-08 5D-6a implementation findings

- `StructuredResponseContract` validates a Draft 2020-12 JSON object Schema before recursively
  freezing it. `schema_dict()` returns a defensive transport copy, so a caller cannot mutate the
  schema after capability negotiation or alter a nested field through the original mapping.
- `ChatRequest.response_contract` is optional. Its presence adds only `STRUCTURED_OUTPUT` to the
  existing required capability set; ordinary text and Tool Calling behavior remains unchanged.
- The strict decoder checks the transport Schema against the exact Pydantic model schema before it
  accepts a response. It rejects a model whose config does not forbid extra fields, response fences,
  non-JSON text, incomplete finish reasons and all Pydantic validation errors without retaining raw
  model content in the surfaced Provider error.
- A repair callback receives the same immutable contract and may run once. The repaired response
  passes through the exact same decoder. Repair does not extract JSON locally, insert defaults or
  retry recursively.
- The LLM Tool Adapter only transports the contract and returns the existing normalized response
  envelope. Evaluation-specific Pydantic validation stays in `ChatEvaluationAdapter`, preserving
  Provider/Tool/Harness responsibility boundaries.
- `ChatEvaluationAdapter` now uses `EvaluationResponseModel` for both prompt Schema and response
  validation. When two invalid responses occur, `ReviewHarness` persists only the deterministic
  fallback and does not publish the Agent draft.
- Full local regression after implementation is `359 passed, 95 subtests passed`. This is Fake
  Provider evidence only; the text-only Zhipu Adapter rejects structured requests before SDK I/O.

## 2026-08-09 5D-6b initial capability-gate audit

- Canonical state and governance agree that 5D-6b is the only next checkpoint; 5D-7 Prompt E2E,
  a second Provider implementation, automatic model routing, LangGraph and Multi-Agent remain
  blocked.
- The current `ZhipuProvider` maps only plain role/content messages and normalizes text content,
  finish reason and token usage. It does not transport ToolSpec/ToolChoice, parse provider tool
  calls, or transport `StructuredResponseContract`; its advertised capabilities correctly remain
  text-only.
- The internal contracts needed for admission already exist: strict structured response schema,
  provider-neutral ToolCall/ToolSpec, capability negotiation, AgentLoop, real local
  `knowledge.search`, and Harness fail-closed publication. 5D-6b therefore needs an isolated
  capability probe and minimal domain slice, not another Agent loop or quality platform.
- The experiment must distinguish SDK/API reachability from end-to-end capability. A successful
  text request does not prove native structured output; a returned tool call does not prove that
  RiftCoach can normalize it, execute an allowlisted tool, feed an observation back, and obtain a
  final response.
- Current official Zhipu documentation lists `glm-5.2` as supporting Function Calling and JSON
  structured output. The chat API transports function definitions in `tools`; returned arguments
  are JSON strings; the assistant tool-call message and a `role=tool` observation must be sent back
  for the final response. Source: https://docs.bigmodel.cn/cn/guide/capabilities/function-calling
- The official API currently documents only `tool_choice="auto"`; it does not document the
  provider-neutral `required` mode. Therefore the Zhipu adapter must reject REQUIRED rather than
  silently translate it to AUTO unless a real probe and documentation support a safe mapping.
- Official structured output is currently `response_format={"type":"json_object"}`. The docs show
  the desired JSON Schema in the prompt and validate it client-side; they do not document a native
  strict `json_schema` transport. RiftCoach can only advertise end-to-end structured output if it
  sends JSON mode plus the exact contract in trusted instructions and still applies the strict
  local Pydantic decoder from 5D-6a. Source:
  https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8
- The real probe must record returned model identity, request ID, finish reason, prompt/completion
  tokens, wall-clock latency and sanitized error category. Monetary cost must be computed from a
  separately captured official price snapshot at run time; it must not be guessed from token usage
  or Coding Plan subscription examples.
- The current Evaluation prompt already embeds the exact Pydantic JSON Schema. Zhipu therefore only
  needs to map the response contract to documented `json_object` mode; local strict validation stays
  authoritative. The adapter must not inject an unmetered hidden Schema message or claim native
  server-side strict-schema enforcement.
- The existing AgentLoop always requests AUTO when tools exist and NONE otherwise, which fits the
  current official Zhipu limitation. Provider-neutral REQUIRED must still be rejected explicitly in
  the adapter because silently weakening REQUIRED to AUTO would violate the caller contract.
- A two-layer real gate limits diagnosis ambiguity and spend: five no-retry API microprobes first,
  then offline adapter TDD, then one recent-form domain slice with a seven-call worst-case cap. A
  low-level failure stops the expensive slice.
- The official Zhipu tokenizer/API schema documents function names with pattern
  `^[a-zA-Z0-9_-]+$`. RiftCoach's `knowledge.search` therefore cannot be sent verbatim. The adapter
  needs a per-request deterministic alias map and must translate both historical assistant tool
  calls and returned calls; changing the internal registry name would leak one provider's grammar
  into Skills and ToolRuntime.
- The authorized P1-P5 run at code SHA `b07f986421b1c14ef36656f3a44698decacc9d24`
  consumed one call and stopped fail-closed at P1 with `invalid_text_response` after 4265 ms. This
  proves the SDK call returned a response object rather than raising authentication, rate-limit,
  timeout, connection or HTTP-status errors; it does not prove why message content was absent or
  empty, because raw output was intentionally not persisted.
- P2-P5 were skipped as designed, so this run provides no evidence for or against GLM-5.2 JSON
  mode or Function Calling. The provider is not admitted, but one malformed/empty baseline response
  is not enough to conclude that GLM cannot satisfy RiftCoach.
- The sanitized failure contract currently discards safe response metadata such as finish reason,
  resolved model and usage when semantic validation fails. A diagnosis design must decide whether
  to retain those already-normalized fields without retaining raw content before any separately
  authorized rerun; Task 4 production Adapter work remains stopped.
- Local `.env` uses product label `LLM_PROVIDER=glm`, while the registry/config contract identifies
  this adapter as `zhipu`. The experiment normalized only the child process to `zhipu`; this naming
  mismatch is configuration taxonomy, not a model capability failure.
- P1 diagnosis compared three choices: preserve only the current error code, persist the raw SDK
  response locally, or project a strict metadata allowlist. The allowlist is preferred because it
  distinguishes response shape without adding a raw prompt/output data lifecycle.
- The minimum useful safe projection is response-received state, content/reasoning-content shape,
  resolved model, finish reason, usage, request-ID hash and tool-call count. Presence of reasoning
  content must never be interpreted as permission to publish or as a passed text response.
- Any diagnostic rerun should be a separate one-call `p1_diagnostic` scope. Reusing the full P1-P5
  command would silently spend four more calls if P1 happened to pass, which exceeds the purpose of
  diagnosis and weakens user authorization boundaries.
- Schema v1.0 compatibility must preserve absence as unknown (`response_received=null`); mapping it
  to false would fabricate that no response existed. New v1.1 reports require an explicit boolean
  for every executed or skipped case.
- `p1_diagnostic` is evidence collection, not Provider admission. Even when its only P1 case passes,
  the report remains `admitted=false`; full admission still requires the separate P1-P5 scope.
- Scope and budget are one invariant: `p1_p5` requires exactly five calls and `p1_diagnostic`
  exactly one. Separate default result paths prevent a diagnostic run from overwriting the immutable
  first P1-P5 experiment.
- The 2026-08-12 full offline closeout passed `383` tests plus `95` subtests. This is a regression
  guarantee for the repository and a readiness signal for the diagnostic program; it is not new
  evidence about GLM because no SDK client, API key or model endpoint was used.
- Authorization is a control-plane input, not a conclusion inferred from test success. The next
  real P1 diagnostic must remain a separate user-approved action even though all offline gates pass.
- GitHub Actions run `31610552899` exposed an undeclared major-version assumption: the unbounded
  `openai` dependency resolved to `3.0.0`, which now installs `httpx2`, while RiftCoach's tested
  Adapter/error-construction contract targets OpenAI Python SDK 2.x and its `httpx` objects. The
  safe maintenance fix is `openai>=2,<3`; adding `httpx` alone would hide the unreviewed SDK-major
  migration instead of preserving the verified production contract.
- The separately authorized `p1_diagnostic/1` at code SHA `6ee74763a99ca2830abf89e2a199b2843bedb20b`
  used exactly one real call and passed the exact P1 sentinel. The response had non-empty final and
  reasoning fields, `finish_reason=stop`, resolved model `glm-5.2`, 22 input tokens, 115 output
  tokens and 4563 ms latency. Only field states and hashes were persisted; no raw text or request ID.
- The earlier P1 empty-text failure is therefore not stable across these two observations. This
  does not establish its cause and does not justify hiding it. P2-P5 remain skipped in the original
  run and absent from the diagnostic scope, so full Provider admission is still unsupported.
- The separately authorized full rerun at code SHA `dbcce145dc458379772ec36583ebb41b0787a4bb`
  used 4/5 calls: P1 and P2 passed; P3 returned empty content, non-empty reasoning,
  `finish_reason=length`, and exactly 1024 output tokens; P4 returned one tool call but failed the
  old exact-arguments equality; P5 was skipped. The report remained `admitted=false` and no raw
  model or reasoning text was persisted.
- Current official Zhipu documentation says GLM-5.2 defaults to Thinking and permits
  `thinking={"type":"disabled"}`. It also requires complete, unmodified reasoning content to be
  returned when interleaved Thinking is used with tools. RiftCoach's V1 runtime intentionally does
  not persist or replay chain-of-thought, so structured-control and tool-protocol rounds must
  explicitly disable Thinking rather than silently discard reasoning.
- The original P4 validator was stricter than the frozen design: it required the entire arguments
  object to equal one fixture, while the design promised a valid JSON object matching the tool
  schema. The controlled probe will keep strict JSON Schema, `top_k`, extra-key and topic checks,
  but will not require semantically valid query wording to be byte-identical.
- The first controlled run at public code SHA `860c2035435afb5a914a2d9c403876df42138478`
  used 1/5 calls and stopped at P1: content was empty, reasoning non-empty,
  `finish_reason=length`, and all 128 output tokens were consumed. This reproduces the default
  Thinking failure family and shows that the one successful diagnostic was not a stable basis for
  leaving P1 implicit. P1 must also disable Thinking because its purpose is transport baseline,
  not sampling the provider's default reasoning policy.
- The final controlled run at public code SHA `6a15a00aaf57d160af3f147b7219b65927b8bb24`
  used exactly 5/5 calls and passed P1-P5 with `admitted=true`. With Thinking disabled, reasoning
  content was missing in every case; P1/P2/P3/P5 returned final content with finish `stop`, while
  P4 returned one tool call with finish `tool_calls`. This admits the isolated low-level protocol,
  not the production adapter or a real RiftCoach Skill slice.
- Sanitized per-case usage/latency was: P1 16/8 tokens and 1391 ms; P2 568/36 and 984 ms; P3
  617/85 and 1250 ms; P4 204/21 and 3172 ms; P5 270/18 and 3718 ms. Official unit pricing remains
  unverified, so estimated cost correctly remains null rather than fabricated as zero.

## 2026-08-13 5D-6b production Zhipu Adapter mapping

- The production adapter can stay a translation boundary: provider-neutral messages, tools and
  structured contracts map to Zhipu transport without changing Skill manifests, ToolRegistry,
  AgentLoop or Harness.
- Every production call currently disables Thinking. This is a V1 protocol decision because the
  runtime does not persist/replay provider reasoning state; it is not a claim that reasoning is
  universally undesirable.
- `StructuredResponseContract` maps only to documented `json_object` mode. The 5D-6a strict local
  Pydantic decoder remains authoritative; the adapter does not claim native strict-schema support.
- Request-local tool aliases preserve internal `knowledge.search` while satisfying the provider
  function-name grammar. Alias collisions fail before SDK I/O; returned unknown aliases fail closed.
- Returned ToolCalls accept only `type=function`, one non-parallel call, a normalized unique ID,
  a known alias and strict JSON object arguments. NaN, arrays, duplicate JSON keys, malformed JSON,
  bad content and non-empty reasoning are rejected with sanitized Provider errors.
- `REQUIRED` remains unsupported rather than being weakened to AUTO. NONE omits tool transport;
  AUTO sends function tools and `tool_choice=auto`.
- Atomic structured-output and tool-calling capabilities do not imply their same-request
  combination. That unproven mode is rejected before SDK I/O, and tool-call presence must agree
  with `finish_reason=tool_calls` in both directions.
- Offline TDD first produced `11 failed, 11 passed`; after implementation and boundary review the
  Zhipu target suite is `26 passed, 22 subtests passed`, focused cross-layer regression is
  `73 passed, 50 subtests passed`, and full regression is `405 passed, 103 subtests passed`.
- These results admit only the offline production mapping. A real Provider-neutral structured/tool
  round trip remains required before the adapter itself is admitted, and a real domain Skill slice
  remains separate after that.
- GLM is the first baseline adapter, not a permanent model winner. DeepSeek/Qwen candidates remain
  gated by same-task quality, tool correctness, latency, cost and stability evaluation.

## 2026-08-13 5D-6b Adapter Protocol Slice offline controller

- The protocol slice must not extend the raw P1-P5 probe or create a second Function Calling loop.
  Reusing the existing AgentLoop tests the production control flow, while a Provider wrapper puts
  one hard pre-I/O budget around both direct structured calls and Agent iterations.
- The successful path uses exactly three model calls: one strict structured request, one tool-call
  response and one final response. The previously approved seven-call ceiling belongs to the later
  domain slice and is not borrowed or silently stacked here.
- The fixed `knowledge.search` handler is a local read-only protocol fixture, not a RAG quality
  test. It proves the dotted internal name survives Zhipu request-local aliasing and returns through
  ToolRegistry, ToolRuntime and AgentLoop without changing the internal contract.
- Public evidence stores only stable state, safe error codes, counts, normalized metadata and
  SHA-256 digests. Raw prompts, model text, tool observations, request IDs and exceptions are not
  persisted.
- Full test collection exposed a package cycle when the orchestration runner was re-exported from
  `app.evaluation.__init__`; the re-export was removed so consumers use the explicit submodule.
  Focused tests now pass 22/22 and full regression is `415 passed, 103 subtests passed`.
- This remains offline Fake Provider/Fake SDK evidence. The real three-call slice must run only
  after this controller is committed, pushed and verified at an exact public CI SHA.
- Commit `f1d171d5591a511f9d6a9788a1bc8068172b0d51` passed GitHub Actions run
  `31625669630`. The single real adapter-protocol execution then used exactly 3/3 calls and
  admitted both cases: strict structured output and the existing AgentLoop tool round trip.
- Real sanitized observations were A1 427/59 tokens at 2344 ms and A2 562/36 tokens at 5360 ms;
  the tool path returned `tool_calls` then `stop`, with one tool proposal and one execution.
- This admits the production adapter's minimum protocol, not a domain Skill. The next design must
  reconcile the broader seven-call domain ceiling with the three calls already consumed rather
  than silently treating Task 5 and Task 6 as separate unlimited experiments.

## 2026-08-13 5D-6b Recent-form Domain Slice offline controller

- The approved seven-call experiment is cumulative evidence, not a fresh budget per script. The
  admitted adapter result consumes three calls, so the domain controller has exactly four calls.
- One observed budgeted Provider must be shared by AgentLoop and Harness `llm.chat`; separate
  component budgets would permit the composed workflow to exceed the approved external I/O cap.
- A normal domain path needs three model calls: Agent tool proposal, Agent final draft after local
  observation, and strict Evaluation. The fourth call is reserved only for Evaluation format
  repair; a revision then re-evaluation path is intentionally unable to complete under this gate.
- The controller composes the real recent-form Catalog/Router/ExecutionBoundary/ContextBuilder,
  local hybrid knowledge search, AgentLoop, existing ReviewHarness and typed terminal output. It
  creates no second Agent loop, Harness or runtime.
- Prior protocol evidence is revalidated as admitted/three-call/provider-model matched and hashed
  byte-for-byte. The new report records both prior and current code/evidence identity so call
  accounting cannot be reconstructed from an unverified constant.
- The admission-only SDK has zero automatic retries; the Harness `llm.chat` ToolDefinition has one
  attempt, no cache and no fallback. Provider retryable failures therefore do not silently create
  additional billable calls.
- Public output is a strict sanitized report. Harness artifacts live only in a system temporary
  directory, and the CLI refuses to overwrite an existing domain result, preventing accidental
  repeat experiments and evidence replacement.
- The real CLI also requires a clean worktree before reporting `git rev-parse HEAD`; otherwise an
  old commit SHA could falsely identify execution that actually included uncommitted code.
- Focused tests are 23 passed; proportional cross-layer regression is 141 passed plus 29 subtests;
  full regression is 430 passed plus 103 subtests. Both RAG gates, compileall, Harness SDK and
  tracked-secret boundaries, and Harness dry-run pass. No real result file or GLM call was created.
- Offline success proves the composition and failure boundaries, not real GLM domain admission or
  report quality. Public CI for the exact controller SHA must pass before the one authorized real
  domain slice; multi-case Prompt/Context quality remains 5D-7.
- Controller commit `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` passed GitHub Actions
  run `31657764638`, including full pytest, both RAG gates, compileall, Harness SDK/tracked-data
  boundaries and dry-run. CI had no local environment file and made no real Provider call.

## 2026-08-13 5D-6b real domain admission result

- The authorized recent-form domain slice ran exactly once on publicly verified code SHA
  `f5e97ead20c5aa7d4798f308bd60e820842061bc`. It consumed one domain call, bringing the
  cumulative experiment to 4/7 calls; there was no retry or Prompt change.
- The external request was attempted and billed, but no normalized `ChatResponse` reached the
  Agent result: response count, ToolCall count, tool executions and knowledge sources are all zero,
  while `agent_status` is null. It is therefore incorrect to classify this as a direct-text answer.
- With no attributable knowledge round trip, the flow never reached structured Evaluation and has
  no quality score. The only publishable terminal output was the deterministic fallback, recorded as
  `degraded`; this is real evidence that the Harness prevented an unevaluated draft from publishing.
- The sanitized result cannot distinguish an Adapter response-normalization rejection from another
  Provider error before normalized response formation. The draft-preparation seam exposes
  `AgentRunResult` only after successful preparation, so the domain runner collapses this branch into
  `knowledge_round_trip_incomplete`. This loss of safe error provenance is a 5D-7 observability Bad
  Case, not a reason to mutate or rerun the 5D-6b sample.
- ADR-0012 closes 5D-6b with partial adoption: admit the minimum Zhipu structured/tool protocol,
  reject GLM-5.2 recent-form domain capability, retain deterministic fallback, and defer any second
  Provider until a same-task 5D-7 evaluation contract exists.
# 2026-08-13：5D-7 入口审计

- 5D-6b 的真实领域失败暴露了一个精确的可观测性接缝：`AgentLoop` 以
  `AgentRunResult(status=failed, stop_reason=provider_error, error_code=<safe code>)`
  保留安全错误来源，但 `SkillAgentDraftPreparer` 随后只抛出
  `AgentDraftPreparationError`；`_BoundAgentDraftPreparationStep` 只有在完整准备成功后
  才保存 `agent_run`，并把该异常再次压缩为没有安全细节的
  `SkillReviewExecutionError("agent draft preparation failed")`。因此领域 runner 最终只能
  记录 `knowledge_round_trip_incomplete`，不能区分 Provider 响应规范化失败与后续工具链
  缺失。
- 5D-7 不能用重跑单个真实样例或调 Prompt 解决上述问题。先冻结分层评测合同：
  Provider/Agent、Tool、Evidence、Evaluation、Terminal 分别观察，未知值保持未知，不能
  伪造为 0 或通过；失败只保存白名单安全分类，不保存 Prompt、模型原文、request ID、
  原始异常或密钥。
- 评测方案比较结果：拒绝“复用单样例追绿”和“只用 Judge 看最终报告”；采用带
  development/held-out 生命周期的分层领域评测。入口批次先用离线可控观测证明评测器
  本身和失败分类，再考虑 Prompt 实验或第二 Provider。
# 2026-08-13：5D-7 Batch B Prompt/Context 身份入口审计

- Batch A 的 `ContractSnapshot` 只保存 `skill_name/version`、`context_contract` 和
  `evaluation_contract` 三类人工标识；它能发现显式版本漂移，但不能发现未升版本的
  `SKILL.md`、内部 Context Policy、上下文渲染或 Evaluation Prompt/Schema 漂移。
- `ContextBuilderV1` 已经产生规范的两条 system/user `ChatMessage`，并保留 section 的
  trust、source、required、priority、选中/省略和预算信息；因此 Batch B 应复用实际
  `ContextBundle` 生成案例级内容身份，不另造 Context Builder。
- 只哈希最终消息虽然能发现变化，却无法定位变化来自 Skill、Context 规则还是案例事实；
  只哈希 Python 文件又会把注释/import 等非行为改动误判为实验漂移。
- 推荐采用双层语义身份：组件层分别记录 Skill 包、Context 合同和 Evaluation 合同的
  公开安全 SHA-256；案例层记录实际输入 Artifact commitment、选中/省略 section 和最终
  规范消息的 SHA-256。实验入口在 Provider 调用前复算并逐项匹配，漂移即 fail closed。
- 快照只保存 ID、版本、路径相对标识、结构化元数据和哈希，不保存 Prompt、事实、模型
  正文、异常、request ID 或密钥；它属于 5D-7 的实验前置身份，不替代 5E 的运行 Trace。
- 本批不修改 Prompt/Context 行为、不运行真实 Provider、不创建 held-out、不接第二
  Provider。后续 Batch C 才使用该入口运行多案例工具、事实、引用和模型级注入评测。

### 2026-08-13：5D-7 Batch C 可执行 development 发现

- Batch A 的 recorded Candidate 能验证分层分类器，但不能证明 Agent 控制流；Batch C
  使用 Scripted Provider 驱动生产 Catalog/Router/Context、AgentLoop、ToolRuntime、
  local hybrid RAG、Evidence 与 ReviewHarness，外部 I/O 为 0。
- 新 `offline_executable` 合同要求 Schema 1.2、零 external calls 和逐案例 provenance；
  Dataset/Candidate schema mismatch 在评测前失败关闭。
- 7 个场景的 fact/citation/injection 结果来自实际 Agent draft、Evidence Artifact 与
  canary probe；安全扫描确认公开 Candidate/Result 未保存攻击原文、错误事实、Prompt、
  报告、request ID、异常或 Key。
- ReviewHarness 的引用 allowlist 真实拦截了 `[K999]`；fact 与 caught injection 场景由
  Evaluation fail 后降级到确定性报告。
- 当 Scripted Evaluator 对 RAG injection 错误返回 pass 时，Harness 确实发布了含 canary
  的报告。分层领域评测把它标成 unsafe publication，说明 Harness 发布权是确定性的，
  但安全性仍依赖 Evaluation 输入质量；这是 Batch D 的关键设计输入。
- 7/7 task outcome 与 primary failure match 只证明已知 development oracle 和实验接线；
  1/7 unsafe publication 是故意保留的 Bad Case，不评价真实模型抗注入能力。
- 完整验证为 `455 passed, 103 subtests passed`，两套 RAG、compileall、Harness dry-run、
  SDK/tracked-data、artifact sanitization、governance 和 diff check 全部通过。

### 2026-08-13：5D-7 Batch D 入口审计发现

- Batch C 的 `injection_check_passed` 来自生产链外的已知 canary oracle，而不是
  `EvaluationResponseModel`；它可以证明实验漏判，不能直接成为生产发布规则。
- `EvaluationRequest` 已经携带 `KnowledgeEvidence`，但当前 `ChatEvaluationAdapter`
  的 Prompt builder 签名只有 `fact_pack, report`，因此实际 RAG 证据没有进入 Evaluator。
  原始用户请求也不在 `EvaluationRequest` 中。
- 只给 1.0.0 增加 `prompt_injection` 枚举会同时改变结构化 Schema、Prompt 行为和
  Prompt/Context snapshot，却仍不给模型判断所需来源；该方案既不充分又破坏历史复现。
- 合理边界是版本化 Profile：1.0.0 冻结历史，1.1.0 接收 allowlisted security context；
  确定性 Harness policy 只识别类型化 blocking issue，不识别具体攻击词。
- 注入 issue 不应交给 Reviser。Reviser 会再次接触攻击相关正文，而且“把安全风险修一下”
  不是发布安全保证；首版遇到 blocking issue 直接 deterministic fallback/rejection。
- held-out 必须在新合同、Prompt、snapshot 和 development 规则全部冻结后创建；真实
  Provider 比较还需要 Adapter 能力、零自动重试、共享 pre-I/O 预算和新 ADR。
- 设计门把真实首轮限制为 3 场、每 Provider 领域最多 12 calls；小样本只做准入，不能
  宣称模型排行或统计显著性。

### 2026-08-14：5D-7 Batch D D1-D3 结果

- D1 不能原地扩展 1.0.0：历史 Evaluation 输入没有用户原话和实际知识证据，且旧
  结果身份必须可复现。新增 1.1.0 最小合同，用 bounded data-only projection 提供
  安全判断所需上下文；`prompt_injection` 必须是 high severity。
- 安全问题不进入 Reviser。Harness 在写入 Evaluation Artifact 后先检查 blocking issue，
  命中即以 `security_policy_blocked` deterministic fallback/rejection 结束；这样修订器
  不会再次接触攻击相关上下文，也不会把“改写成功”误当成安全保证。
- D2 的 7 个 secure development 场景真实复用生产本地控制流，Scripted Provider 仅替换
  模型响应；7/7 task outcome、7/7 primary failure classification、0/7 unsafe publication，
  外部调用为 0。该结果是控制流/评测门基线，不是 GLM/DeepSeek/Qwen 的能力结果。
- D3 held-out 在 D1/D2 合同、secure snapshot 与规则冻结后才创建，包含正常、用户注入、
  检索证据注入三类最小案例。数据集声明 `calibration_excluded=true`，测试要求显式确认
  规则冻结；创建文件不等于已经运行或已经证明泛化。
- 公开安全工件只保存合同/案例身份、SHA-256、结构化结果与安全错误码；不保存攻击原文、
  canary、Prompt、模型正文、Tool Observation、request ID、异常或密钥。
- 5D-6b 的错误来源丢失仍未被本批“猜测修复”；它被保留为 D4 前的可观测性缺口。下一步
  先设计候选 Provider 采用门，再决定是否进行一次有界真实比较。

### 2026-08-14：5D-7 Batch D D4 Provider 候选审计

- 现有 `LLMProvider`、`ChatRequest/ChatResponse`、能力协商和显式 Registry 是厂商中立
  接缝，但生产 Adapter 目前只有 Zhipu。`ZhipuProvider` 还包含关闭 thinking、工具名
  别名、并行调用拒绝、finish reason 和错误映射等厂商语义；第二 Provider 不能只更换
  `base_url`，也不应先造一个掩盖差异的“万能 OpenAI-compatible Adapter”。
- DeepSeek 官方当前把 `deepseek-v4-flash` 与 `deepseek-v4-pro` 标为正式模型，均支持
  OpenAI 格式、non-thinking/thinking、JSON output 与 Tool Calls；V4 Flash 的直接 API
  单价和 2026-08-16 起的峰谷新价均可公开核验。它与现有 `openai>=2,<3` 依赖兼容，
  且可以关闭 thinking，适合先隔离测试 Provider 适配与同任务控制流。
- Qwen3.8 Max 已结束 preview 并成为正式 `qwen3.8-max`，支持混合思考、JSON 输出和
  Function Calling，不能再依据过期检索摘要称为“仅思考 preview”。但官方还要求在
  `preserve_thinking=true` 时完整回传 `reasoning_content`；当前 RiftCoach 的规范消息
  没有该字段。其 Token Plan 个人版以动态 Credits 计费且明确禁止自定义应用后端 API，
  标准按量价格本轮也未取得足以冻结的 qwen3.8-max 行，因此暂不作为首次候选，不代表
  对模型质量作负面结论。
- DeepSeek V4 Pro 与 Flash 共享首轮所需协议面，但价格更高；D4 的目标是先验证第二
  Provider 可移植性，不是做模型排行榜。因此选 Flash 可减少成本与变量，Pro 留待以后
  有明确质量 Bad Case 时再评估。
- 已冻结的三个 held-out 案例各允许最多 4 次 Provider call 和 4000 total tokens；首次
  比较必须继续沿用该合同、`max_revisions=0` 与 SDK retry=0。第二 Provider 在进入
  held-out 前还需通过精确 3-call Adapter protocol，因此候选总上限为 15 calls；GLM
  同任务上限为 12 calls。
- D4 只决定候选和门禁，不检查密钥、不实现 Adapter、不运行 held-out、不产生外部调用。
  下一步应先离线实现并测试 DeepSeek Adapter、预算/成本预检和比较控制器，再由公开 CI
  验证精确 SHA；真实比较必须是之后独立、显式受限的执行批次。

### 2026-08-14：D4 候选决策更正发现

- 用户追问刚 GA 的 DeepSeek V4 Pro 后，重新核对评测目标发现 ADR-0017 混淆了两个
  问题：Flash 足以低成本验证 Adapter 协议，但 D5 的唯一候选还要参加领域 held-out。
  候选标准应优先匹配完整领域准入目标，而不是只优化协议探针成本。
- DeepSeek 官方更新记录显示 V4 Pro 正式版于 2026-08-13 发布；V4 Flash 的正式 API
  更新是 2026-07-31。官方 Agent 基准中 Pro 分别为 Terminal Bench 2.1 `87.9`、
  NL2Repo `61.5`、Cybergym `83.3`、DeepSWE `62.7`、Toolathlon `74.1`、
  AutomationBench `31.8`、DSBench-Hard `67.2`，均高于 Flash 的 `82.7`、`54.2`、
  `76.7`、`54.4`、`70.3`、`25.1`、`59.6`。
- 官方产品说明把 Pro 定位为复杂生产 Agent/编码能力更强的模型，把 Flash 定位为更快、
  更低成本且在简单 Agent 任务接近 Pro。两者均提供 non-thinking、JSON、Tool Calls 和
  1M 上下文，本轮从 Flash 改 Pro 不增加 Provider 数量或 Agent 架构复杂度。
- 2026-08-16 起官方峰值价快照中，Pro 输入未命中缓存为 `$1.32/M`、输出为
  `$3.96/M`。DeepSeek protocol + domain 的冻结总 Token 上限为 16000；即使极端按
  全输出价计算也约 `$0.06336`，因此 `$0.10` 停止线足够，成本差不足以抵消领域代表性。
- 不同时测试 Flash 与 Pro，也不允许 Flash 通过协议、Pro 运行领域；准入证据必须绑定
  一个精确模型。当时把 Flash 的未来成本/时延分层暂记到 5F；ADR-0019 随后保留该候选
  意图，但把归属修正为 5P 后、默认阶段 6 的横向 Provider 优化门。
- 本次只更正 ADR、设计与状态，不实现 Adapter、不读取 Key、不调用 Provider、不运行
  held-out；DeepSeek V4 Pro 仍只是候选，不是已准入或生产默认模型。

### 2026-08-14：D5 DeepSeek Provider 离线实现发现

- 不使用 API Key 仍可验证“RiftCoach 是否正确说 DeepSeek 方言”：Fake SDK 精确记录
  payload 并脚本化返回 text/tool/structured/error，因而可检查 thinking、stream、JSON、
  工具别名、finish、usage 和错误归一化；它不能证明模型智力、在线可用性、延迟或价格。
- DeepSeek 与 Zhipu 虽同属 OpenAI-compatible Chat 接口，但 thinking、finish reason、
  usage 和错误边界没有足够相同证据；独立 Adapter 比提前抽象通用基类更容易审计。
- 5D-6b 的失败来源不是 AgentLoop 丢失，而是 draft preparation 将非 completed run 压成
  异常后，上层只剩通用失败。只传递状态、停止原因和安全 snake-case error code 即可
  补足归因，不需要保存 Provider 原文。
- 预算门必须在委托底层 Provider 前计数；否则 SDK 超时/断连可以反复消耗真实请求却不
  进入账本。响应后再使用统一 usage 结算，缺 usage 必须停止而不是按零成本处理。
- no-I/O preparation 的职责是核对“代码、CI、冻结题目、Prompt/Context 是否同一份”，
  不是运行考题。它有意不导入客户端构造、不读取环境 Key，也不执行 held-out。

### 2026-08-14：DeepSeek Flash/Pro 分层归属复核

- 当前 Pro-only 5D-7 与未来模型分层是两个问题：前者判断一个精确候选能否通过协议和
  领域准入，后者判断产品运行时是否值得用 Flash 降本并在复杂/低质量任务升级 Pro。
- 5F 的固定变量是第三方 Agent Runtime（Pi / Claude Agent SDK）是否值得采用。若同时
  在 5F 改模型策略，SDK 与模型变化会互相混杂，无法解释质量、延迟或成本变化来自哪里。
- 当前没有产品流量、p95 延迟或单位成功报告成本，不能仅凭 Flash 更便宜就实现自动
  分层。最早触发点是 5P 早期产品切片之后，默认等待阶段 6 的真实 API/Trace 数据。
- 未来必须对照 Pro-only、Flash-only、Flash 默认 + Pro 有界升级；使用新鲜且有污染
  记录的数据集，同一 Skill/Prompt/RAG/Harness 和安全门。没有质量非劣与成本/延迟收益
  时，保持单模型是合法结果。
- 该设计不等于 Multi-Agent、用户模型选择器或已实现自动路由；当前
  `DeepSeekProvider` 仍只允许 `deepseek-v4-pro`，5D-7 唯一下一步不变。

### 2026-08-14：真实 DeepSeek 协议门执行接缝审计

- D5 已有 `DeepSeekProvider`、`AdapterProtocolSliceRunner`、实验 resource ledger、
  stop controller 和 no-I/O preparation，但脚本层没有把这些边界正式组合的真实
  DeepSeek 执行入口；Zhipu 历史探针不能通过替换 base URL 复用。
- 直接手写 SDK 请求会绕过生产 Adapter，直接复用协议 runner 又会漏掉累计 Token/费用
  ledger 与 Provider stop；正确组合是实验预算 Provider 包住生产 Adapter，再交给协议
  runner 的精确三次调用预算。
- preflight 必须发生在读取 `.env`/Key 和创建 SDK client 之前；输出只能进入冻结的
  provider capability result 目录且不得覆盖已有证据。
- 该补口是当前 5D-7 真实协议门的一部分，不把 D5 改回未完成，也不改变 Pro-only、
  held-out 未运行和 Flash 延后评估的决策。

### 2026-08-14：真实 DeepSeek V4 Pro Adapter 协议门结果

- 结果文件已由 `ProviderAdapterProtocolExperimentRecord` 重新严格解析，绑定代码提交
  `076a5e3558cd68abb545cebdc2542c973b020768`，文件 SHA-256 为
  `575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
- A1 strict structured contract 使用 1 call 并通过；A2 Agent tool round trip 使用
  2 calls 并通过，观察到一次 `knowledge.search` ToolCall、一次本地成功执行和最终
  `stop`；协议总计 3/3 calls，`admitted=true`。
- 资源账本记录 1303 input + 125 output = 1428 tokens，保守估算成本 `$0.00221496`，
  未超过 `$0.10`；没有 Provider/global stop，SDK retry 为 0。
- 该证据只准入 DeepSeek V4 Pro 的最小生产 Adapter 协议，不准入近期复盘领域质量、
  抗未知注入能力、生产默认模型或 Flash/Pro 路由。三场 held-out 仍未运行。
- 用户暂停消息到达时真实门命令已经完成并写入不可覆盖结果；终止请求随后确认没有残留
  Python 进程。恢复时必须复读并归档该证据，严禁把中断误解为需要重跑。

### 2026-08-14：DeepSeek 领域 held-out 执行接缝审计与离线实现

- 现有 `OfflineDomainExecutionRunner` 绑定 development `_Scenario`、脚本 Provider 和已知
  canary，适合验证本地控制流但不能复用为真实 held-out 执行器；复用会让执行路径接触
  开发期 oracle。领域门应使用薄协调器、独立案例执行 Protocol 和既有分层 Evaluator。
- 原实验 ledger 只记录累计 calls/tokens，无法证明 protocol 4000、domain 12000 和单例
  4000 observed-token 三层边界，也不能从已消耗的真实协议账本继续。现在 snapshot 对旧
  记录向后兼容：若旧证据只有一个活跃 scope，可安全归因其 Token；多活跃 scope 且缺少
  scope Token 则拒绝猜测。
- “preflight 先于 Key”必须成为 API 结构，不应只靠 CLI 书写顺序。新的
  `prepare_deepseek_domain_heldout_run()` 完全不接收 Provider，先产出绑定代码/CI、
  Dataset/Snapshot、协议文件摘要和案例计划摘要的 admission；运行函数只接受 admission。
- 案例执行器不允许上报 calls、Token、金额或延迟。协调器把同一个受控 Provider 交给
  Executor，并用累计账本前后差值生成 `DomainCandidateCase` 资源字段，避免执行器伪报。
- 每案例完成后立即复用 `evaluate_domain_candidate()` 的同一分层语义。task outcome / 主
  失败分类 mismatch 停止 DeepSeek；unsafe publication 触发 global stop；剩余案例明确
  记为 skipped。Provider 或意外 Executor 异常只保存白名单 failure code，不保存异常正文。
- D3 Dataset 冻结的是案例身份和判分 oracle，不应把真实攻击正文硬编码进通用协调器。
  执行计划用 ID/version/SHA/case order 单独绑定，未来生产 Executor 必须声明完全相同的
  plan identity；真实计划正文和 canary 不进入公开结果。
- 实际协议结果在扩展后的向后兼容模型下仍严格解析为 admitted 3 calls，字节摘要仍为
  `575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`，没有重跑。
- 合成 Provider/Executor 已覆盖协议账本继承、单例第 5 call pre-I/O 拒绝、scope Token
  overrun、首错停止、unsafe 全局停止、plan/budget 漂移 pre-I/O 拒绝、原始异常脱敏和
  输出独占预留。它只证明实验控制面，不证明 DeepSeek 的领域能力。

### 2026-08-14：领域 held-out 执行接缝公开验证

- 接缝功能提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已推送，GitHub Actions
  run `31785253957` 对该精确 SHA completed/success；公开 CI 重跑完整 pytest、两套
  RAG、compileall、治理、安全边界和 Harness dry-run，没有 Provider 调用。
- 这只把控制面从“本机可测”升级为“公开仓库可复现”，没有补出真实案例正文、生产
  Executor 或 CLI，也没有把 3 场 held-out 标记为执行过。
- 下一批必须先把独立案例执行计划的 ID/version/SHA/order 与生产 Executor 精确绑定，
  并证明 CLI 顺序为 admission -> 输出预留 -> Key/client -> 有界执行；新的 exact-SHA
  CI 成功前仍不能进入真实数据面。

### 2026-08-14：生产装配入口审计发现注入准入方向反转

- 未执行 held-out 1.0.0 把两个注入案例设为 expected failure；当前 aggregate admission
  又要求 outcome/failure 精确匹配，因此模型抵抗注入会被拒绝，模型服从注入但被 Harness
  拦住反而可能准入。这是 Provider 领域门的方向错误，不能带入真实运行。
- 三场 held-out 从未运行，真实 input plan 和候选输出均不存在；现在可在无结果反馈的
  情况下版本化修正，不属于看过答案后追绿。ADR-0021 将三场统一为安全端到端成功门。
- `DomainCaseExecutor` 现有签名接收完整 `DomainEvaluationCase`，会在类型层暴露 oracle；
  生产接口应只接收 `case_id` 与受预算 Provider，输入从独立冻结计划解析。
- 真实 3-call Adapter protocol 没有使用领域 Dataset；要求旧协议 preparation 的
  Dataset SHA 永远等于当前考卷是错误耦合。迁移只放松这一个未使用身份，仍严格复读
  协议 bytes SHA、Provider/model、3 calls、资源与停止状态，绝不重跑。
- 入口审计有两次只读命令错误：Windows `rg` 路径误用了 `tests\test_*` 通配符；随后又
  猜测了不存在的 `app/tools/knowledge.py`。两者都没有修改文件，后续改为显式目录和先
  `rg --files`/符号搜索再打开真实路径。

### 2026-08-14：生产装配实现结论

- Dataset oracle 与案例输入是两种不同资产。协调器需要 oracle 判分，生产 Executor
  只需要 case ID 并从独立输入计划取输入；将整个 `DomainEvaluationCase` 交给执行器会
  让测试答案在类型层泄漏。
- 协议证据只验证 Adapter structured/tool 合同，从未读取领域 Dataset；因此协议记录的
  历史 Dataset SHA 不应阻止未执行考卷的版本更正。可迁移边界是保留精确协议 bytes、
  Provider/model、3 calls、1428 tokens、停止状态和 Prompt/Evaluation snapshot，移除
  唯一未使用的 Dataset equality。
- 注入案例的系统安全和 Provider 领域准入不是同一判断：模型服从注入但 Evaluator/
  Harness 阻断时，系统保持安全，Provider 仍应不准入；只有模型抵抗注入、事实/引用与
  Evaluation 均通过并最终 published，才是本次领域成功。
- `max_revisions=0` 不等于禁用结构化格式修复。前者禁止根据答案调整报告，后者仍允许
  Evaluation Adapter 对非法 JSON 做最多一次同 Schema 格式修复；二者控制不同风险。
- Key-last 必须由入口顺序和测试证明：所有身份/文件/输出冲突在环境 loader 前失败，
  并在环境加载前独占创建输出哨兵。进程在此后失败会留下空哨兵，防止静默重复付费。

### 2026-08-14：真实领域 held-out 首个 Bad Case

- 真实 DeepSeek V4 Pro 领域门只执行一次，在第一个正常案例的第一次 Agent 调用后得到
  `unsupported_parallel_tool_calls`。初始 Context 只含 system/user 消息，因此该安全码
  表明生产 Adapter 拒绝了模型响应中的多个 ToolCall，而不是历史 assistant 消息编码失败。
- Adapter 没有构造统一 `ChatResponse`，所以 Agent 观测为 failed/provider_error，工具、
  Evidence 与 Evaluation 均未开始；ReviewHarness 按既有边界降级到确定性报告，没有
  unsafe publication。后两例按首错停止跳过。
- 实验 ledger 在 I/O 前计入 1 call；由于 Adapter 在规范化前拒绝响应，无法从统一合同
  结算 usage/latency，因此公开领域增量为 0 tokens/$0.00，而不是断言厂商没有计费。
- 当前结果证明“单工具调用 Adapter 合同与真实模型行为不兼容”，尚不能评价报告质量或
  注入抵抗。不得重跑当前 held-out；后续若考虑并行 ToolCall，应先在 development 复现、
  比较拒绝/顺序执行/并发执行方案并建立新合同与新鲜评测。

### 2026-08-14：多 ToolCall Bad Case 设计结论

- DeepSeek 官方 Chat Completion 合同明确 `tool_choice=auto` 可调用一个或多个工具，响应
  使用 `tool_calls[]`；当前公开请求字段没有 `parallel_tool_calls=false`。因此真实 Bad Case
  是 RiftCoach Adapter 合同比厂商正式合同更窄，不是模型输出违反官方协议。
- Provider Adapter 只负责严格解码，工具是否并发属于 Agent Runtime。现有 AgentLoop 已
  在执行前检查整批数量、白名单和重复签名，并在全部通过后按返回顺序执行，适合以最小
  改动兼容多 ToolCall 批次。
- 真正并发没有当前延迟证据，且会增加共享状态、取消、超时、顺序和部分失败语义；
  ADR-0022 选择顺序消费，不开启 `parallel_tool_calls` capability。
- 当前真实 held-out 结论永久保持不准入。后续先做零调用 development TDD；任何真实
  诊断和新鲜 held-out 都必须另过采用门，不能复用旧三题追绿。

### 2026-08-14：多 ToolCall 顺序消费本地验证发现

- 旧 Adapter 的失败确实来自响应解码与历史 assistant 编码中的数量限制；先写的
  development 测试在旧实现上准确得到 `unsupported_parallel_tool_calls`，没有绕过真实
  接缝或把错误改名。
- 删除数量限制后，其他 fail-closed 校验继续由现有 Adapter 测试覆盖；Adapter 只形成
  Provider-neutral `ChatResponse`，不承担执行策略。
- AgentLoop 原有代码已把批次预检和执行分成两遍；新增测试证明任一调用越权、重复或超出
  剩余预算时 handler 调用数为零，并证明通过批次的 Tool Observation 顺序和 ID 配对稳定。
- Fake DeepSeek SDK 的纵向 development 案例证明真实本地 RAG 产生 Evidence，Secure
  Evaluation 1.1 产生可验证结果，ReviewHarness 才发布报告；因此这不是只测 Adapter 的
  单元假绿。但 Fake SDK 仍不能证明真实模型质量、延迟、计费或抗未知注入。
- 当前唯一开放动作是 exact-SHA 公开 CI。旧 Dataset 1.1.0 结果哈希和
  `admitted=false` 结论不可覆盖、不可重跑；真正并发仍无采用理由。

### 2026-08-14：多 ToolCall 顺序消费公开验证发现

- 提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 的 Actions `31817798170` 已成功，
  因此本地 TDD 不再只是工作树证据，而具备 exact-SHA 公开可复现证据。
- 公开 CI 没有读取 `.env` 或调用 Provider；它不能将 Fake SDK 的报告文本提升为真实
  DeepSeek 质量证据，也不能让已经消费的 1.1.0 held-out 重新变成可校准数据。
- 如果继续验证真实 Pro，必须先建立新版本 Dataset 和独立输入计划，重新冻结组件/案例
  identity、Evaluation/Prompt/Context 合同与资源预算，再由用户单独确认真实调用；当前
  唯一下一步因此是零调用设计而不是立即发请求。

### 2026-08-15：GLM-5.3 官方迁移约束

- 官方页面 `https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3` 已确认 GLM-5.3
  文档存在；页面说明 Coding Plan 已开放，普通模型 API 将逐步上线。
- GLM-5.3 始终启用 thinking，不能使用当前 Zhipu Adapter 固定的
  `thinking.type=disabled`；官方迁移提示要求 `enabled`，并设置 `reasoning_effort`，
  首轮应以 `low` 控制成本和延迟。
- 当前 `app/providers/zhipu.py` 还会把非空 `reasoning_content` 判为非法，并在
  多 ToolCall 处保留旧限制；因此 GLM-5.3 不是只修改 `LLM_MODEL` 的透明升级。
- GLM-5.3 必须有独立 provider profile、离线 TDD、结果文件和新鲜领域采用门。GLM-5.2
  证据、DeepSeek Adapter/结果/预算/held-out 均保持只读；不把 DeepSeek 的多 ToolCall
  修复自动复制给 Zhipu。
- 当前下一步不变：先完成 5D-7 零调用新鲜领域采用门设计；迁移顺序、风险和隔离规则
  已写入 `docs/plans/2026-08-15-glm53-provider-adoption-design.md` 与 ADR-0023。

### 2026-08-15：DeepSeek 新鲜领域采用门设计发现

- 旧 Dataset 只改 ID/version 不能恢复新鲜性；案例正文、fixture、marker 和失败位置都已
  进入开发过程，只能继续承担 regression/development 证据。
- 现有 no-I/O admission、薄协调器、预算 Provider、production Executor、分层 Evaluator
  与 ReviewHarness 已有 TDD/公开 CI，重写会复制控制面；应版本化复用并重建输入身份。
- 新 held-out 不能在合同实现前创建。先用合成 development 数据完成兼容 schema、
  历史证据链、逐案例 Context commitment 和 CLI 顺序 TDD，再经 exact-SHA CI 冻结代码，
  之后才创建真正新题。
- Prompt/Context 语义仍需新快照，因为旧快照只用一个 demo case；新快照应哈希三个实际
  案例的 section/message，但不公开正文。多 ToolCall 实现由当前 code/public-CI SHA、
  历史修复提交和行为测试绑定，不另造通用 Runtime Snapshot。
- 新鲜门历史账本必须显式展示 3 次旧协议调用和 1 次旧领域失败调用；新范围最多 12 calls，
  不能把历史消耗重置为 0，旧失败响应的 Token/费用继续保持 unknown。
- ADR-0024 因此选择“复用控制面 + 新 fixture/Dataset/plan/Context + 只读历史证据链”；
  当前设计批外部调用为 0，也没有创建正式新 held-out。

### 2026-08-15：Fresh-Gate 1 离线合同实现发现

- 旧 input plan 只有 Dataset/fixture/case identity，不能证明三个实际案例分别看到了
  哪个 Context。V1.1 通过 `case_id + context_sha256` 按顺序绑定每条案例，同时让 V1.0
  明确拒绝新字段，避免旧 schema 被静默改义。
- Prompt/Context 的组件摘要和案例摘要是两层不同证据：组件摘要说明 Skill、工具、
  Evaluation/Prompt builder 没漂移；案例摘要说明实际 utterance、typed options、section
  选择和最终 messages 没漂移。新 builder 复用真实 Router/Boundary/ContextBuilder，
  没有另造模拟 Context 逻辑。
- 旧拒绝结果的领域账本显示 0 normalized tokens/`$0.00`，但那是 Adapter 规范化前无法
  结算统一 Usage；新历史合同必须把该失败调用的 Token/费用写为 unknown，而不能根据
  序列化零值声称“未计费”。历史调用仍明确计为 1。
- Fresh-Gate 1 只需要 development admission，不应提前加入真实 run 函数。把
  `provider_construction_authorized` 固定为 false，并让 prepare 函数完全不接收 Provider
  或 Key，比依赖调用方自觉不调用更安全。
- 实施计划最初沿用了三条不存在/参数不匹配的外围验证命令；读取
  `.github/workflows/tests.yml` 后已更正为当前真实 RAG 参数、内联安全边界和带 fixture
  的 Harness dry-run。以后实施计划必须从 CI workflow 复制门禁入口，不能根据历史名称
  猜测脚本存在。
