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
