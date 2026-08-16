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

### 2026-08-15：Fresh-Gate 3 新资产冻结发现

- 新 held-out 的新鲜性来自时间顺序和内容差异，不来自文件名。新 fixture bytes、case
  ID、用户措辞、知识注入正文和两个 marker 均与已消费旧题不同；冻结后不得用于调节
  Prompt、Adapter、Evaluator、Harness、Router 或 RAG。
- 第三个初稿请求写成“最近几场”且缺少 Manifest 的第二组显式复盘目标词，真实
  Deterministic Router 正确拒绝。没有修改 Router 迎合考题，而是把用户入口改成明确的
  “分析近期战绩表现/训练重点”，随后三例都通过真实 Boundary/ContextBuilder。
- Dataset oracle、Input Plan 输入和 body-free Snapshot 是三种不同资产。Executor 继续只
  接收 `case_id + provider`；Snapshot 只保存 SHA/section/message 元数据，不含用户、
  fixture、报告、注入或 marker 正文。
- 新 fixture 不是只换名字：样本从 2 局中路改为 3 局上路，指标、对局行和报告全部更新；
  新测试从 match 行重新计算胜率、CS/GPM/DPM/视野/前 15 分钟死亡，并核对报告表格。
- 本地 `39 passed` 聚焦、`574 passed, 103 subtests passed` 全量、两套 RAG、compileall、
  Harness/secret boundary、dry-run、governance 和 diff check 均通过。正式结果不存在，
  Provider calls/held-out executions 为 0；当前仍需 exact-SHA 公开 CI。

### 2026-08-15：Fresh-Gate 4 运行入口发现

- 旧 Adapter 协议与新领域 Context 不应强制相同：前者证明同一 Provider/model 的
  structured/tool transport，后者冻结新任务输入。新 readmission 必须允许这项预期差异，
  但仍严格绑定旧协议 result bytes、准入状态、资源和 Evaluation identity。
- 不能只把旧 CLI 的三个路径改成 V2。新结果还需要显式保存旧拒绝 SHA、修复 commit/CI、
  Fresh-Gate 3 asset commit/CI 和当前 code/public-CI；因此采用外层 Fresh admission/result
  envelope，内层继续复用旧领域协调器和 `ProviderDomainExperimentRecord@1.0`。
- `--prepare-only` 的安全性来自依赖不可达，而不只是“约定不调用”：该分支在形成 no-I/O
  admission 后直接返回，不预留输出、不加载 environment、不创建 Provider。未来真实运行
  必须重复同一 admission，再按 output reserve → env/Key → Provider 的顺序继续。
- Fake Provider 正常路径用 9 次合成调用通过三例，证明 production Executor、RAG、
  Evaluation 1.1 与 Harness 装配可达；受控鉴权失败只调用 1 次且后两例 skipped，证明首错
  停止。两者都不是外部调用或真实 held-out 质量证据。
- 相邻回归 `93 passed`、完整回归 `580 passed, 103 subtests passed`；两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过，新真实结果文件
  仍不存在。
- 实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 的 GitHub Actions run
  `31863341338` exact-SHA 成功；同 SHA、干净工作树的真实 prepare-only 也通过，并明确
  报告 external calls 0 / held-out false。公开 CI 与 prepare-only 是运行前身份门，不是
  DeepSeek 领域能力证据。

### 2026-08-15：V2 真实门预算可达性发现

- 真实运行前 HEAD/origin 均为 `741e84140f816fb4b06b2812a8d07d3f32eaf4d0`，Actions
  `31863519248` 成功、工作树干净、结果不存在、治理通过；用户明确确认后只执行一次。
- 首例第一次规范化响应消耗 3241 input + 199 output = 3440 observed tokens；第二请求
  需要预留 1024 output，因 `4464 > 4000` 在 I/O 前停止。不是 429、鉴权、网络、金额或
  SDK retry 问题。
- `AgentLoop` 只有首轮返回 ToolCall 才进入第二轮 Provider 调用，因此可以从控制流推断
  首轮进入过工具分支；但失败传出的 `AgentFailureObservation` 丢弃部分 ToolCall/
  ToolExecution 语义，公开结果无法证明工具是否成功。这是安全脱敏与可观测性之间的
  真实缺口，后续需要在不保存正文的前提下补安全部分运行摘要。
- V2 的 4-call 上限在 Fake Provider 下可达，但真实首轮 Context 已接近 4000-token 单例
  上限；“调用数足够”不等于“Token 足够”。开发测试缺少真实长度 Usage fixture，导致
  预算策略本身使必需的工具往返/Evaluation 不可达。
- 结果仍是合法且不可变的 `admitted=false`：它证明资源控制和 Harness fallback 工作，
  但没有测出完整报告、事实、引用或注入质量。不得据此宣称模型质量差，也不得调预算后
  重跑同一 V2。

### 2026-08-15：V2 预算可达性裁决发现

- “下一调用最低上限”可以由真实账本精确证明：3440 observed + 1024 max output = 4464；
  这与未来完整链路精确 Token 需求不是同一个数。
- 账本的 output 预留只在每次 I/O 前检查，不会作为已用 Token 永久累加；因此不能把两个
  剩余调用的 1024 简单相加，声称完整链路最低是 5488。
- 公开 V2 结果刻意没有原始 ToolCall、工具结果和第二轮请求正文，所以无法回推出后两次
  Provider 的精确 Usage；不应恢复临时输出或用本地估算冒充官方 tokenizer。
- 真实本地控制流仍可安全重建三类 request envelope。`DeterministicContextSizer` 对三次
  请求给出 6666/7774/6266 稳定长度单位；以首轮真实 3241 input 校准后，input 风险投影
  为 3241/3780/3047。它足以暴露原 20/10 Fake Usage 的失真，但只是一阶投影。
- 因此 ADR-0025 既不关闭 DeepSeek 候选，也不授权 V3 I/O：先保留模型能力 unknown，
  后续用未见 held-out 答案的 development 校准新资源合同，再创建全新身份。

### 2026-08-15：V3 development 资源校准设计发现

- 完整生产链的正常路径是 2 次 Agent + 1 次 Evaluation；`decode_structured_response()`
  最多增加一次 Evaluation repair，因此资源合同要让 3-call 正常路径和 4th-call 合法恢复
  都可达。`max_revisions=0` 不会关闭这次格式修复，但会阻止第 5 次报告修订调用。
- 用公开 development plan、本地受控 Provider 和真实 production Executor 已走通四阶段；
  body-free 长度单位为 5956/7064/5749/2510。它们只证明请求形状，不能当 DeepSeek
  tokenizer 或 V3 推荐预算。
- 直接运行一条 development E2E 会让可见阶段取决于模型随机行为；采用“本地生产组装
  冻结请求，再独立 replay 收集 Usage”能把资源测量与质量评测分开。
- ADR-0026 冻结 baseline/ceiling 两个公开 profile、每 profile 四阶段、未来最多 8-call、
  校准 `max_tokens=64`、零重试和首错停止。校准输出永不参与 Prompt、RAG、Memory 或
  模型质量结论。
- V3 预算按逐阶段最大真实 input 的 1.25 倍向上取整，再加四次 1024 output ceiling；
  25% 是预注册工程余量而非统计置信区间。推导成本含已知协议成本后超过 `$0.10`、Agent
  两调用在现有 30 秒 deadline 下不可达或请求超过 ceiling envelope 时，都必须停止而
  不是自动调预算。
- 本设计没有 Provider/Key/网络调用，也没有创建 V3 held-out。下一批先做离线合同/TDD
  和 exact-SHA CI，之后真实 development 校准仍需单独确认。

### 2026-08-15：V3 资源校准离线实现发现

- ceiling 的 10-match 初始 Context 为 12206 本地单位；三次 `knowledge.search` 各取一条
  后第二次 Agent 请求为 15279，真实落在 Skill 16000 ceiling 内。最初每次 `top_k=2`
  会触发 `context_budget_exceeded`，因此保持最大 3 ToolCall、将每次命中收紧为 1，
  而不是放宽 Skill ceiling。
- 三次知识查询经证据去重只形成 K1/K2；受控草稿最初引用 K3 被现有 citation gate 拒绝，
  修正开发草稿只引用实际证据，不放宽引用规则。
- 现有资源账本会限制请求声明的 output cap，但未拒绝 Provider 实际 Usage 超过单请求
  cap；现已在结算并记账后以 `token_budget_exhausted` fail closed，旧 observed-overrun
  语义保持兼容。
- 预算推导必须从完整 8/8 Usage 才能产生；Fake 示例只证明公式和门禁，不能替代未来
  DeepSeek tokenizer/latency 证据，也不允许创建 V3 held-out。

### 2026-08-15：真实 development Usage replay 入口发现

- 离线 `simulate_resource_calibration()` 的显式 Fake 标记是必要隔离门，不能为了真实调用
  直接删除；真实路径需要不同的 run admission 和 result 类型，才能让
  `external_provider_calls=0` 与真实计费次数无法混淆。
- no-I/O admission 的 `provider_construction_authorized=false` 保持原义；新的 run
  admission 只有在用户确认、精确 8-call、冻结 request-set 与受控结果路径一致时才显式
  升级，并把 experiment ID 绑定到 no-I/O proof 和输出身份。
- Key-last 不只是“晚一点读环境”：CLI 必须先检查输出冲突、重建并核对 8 个请求、绑定
  code/public-CI、独占预留结果，之后才加载 `.env` 和构造 Provider。
- 真实与 Fake 回放可以共用同一个 ledger/首错停止内核，但只能由外层不同合同赋予证据
  语义；真实结果保存 calls/Usage/latency/finish/request-id digest，不保存任何 response。
- 只有真实 8/8 完整结果才能建立预算记录；预算推导本身外部调用为 0，并绑定真实结果
  bytes SHA。stopped 结果不创建预算文件，也不允许在同一结果身份下补跑。
- 实施聚焦 19、相邻 74、完整 `606 passed, 103 subtests passed`；当前仍未读取 Key 或
  调用 Provider。一次相邻回归先猜错不存在的 `tests/test_provider_adoption.py`，随后先用
  `rg --files` 定位为 `test_provider_adoption_control.py` 并取得 74/74；另一只读复核又沿用
  了不存在的历史辅助脚本名，已改为严格照 `.github/workflows/tests.yml` 执行门禁。

### 2026-08-15：真实 development Usage replay 结果发现

- 真实入口提交 `6aa8c43` 的 Actions `31868747216` 成功；同一干净 SHA prepare-only
  重建并核对请求后返回 external calls 0，正式结果/预算路径仍不存在。
- 正式 replay 第 1 个 baseline 请求实际发送，但 DeepSeek Adapter 没有返回统一
  `ChatResponse`；安全分类只有 `provider_response_invalid`。首错停止使后 7 个请求完全
  没有发送，结果不可覆盖或补跑。
- 没有统一响应就没有 `TokenUsage` 或规范化 latency；账本里的 0 tokens/`$0` 是“没有
  记录到 Usage”，不是厂商账单的已知零。保守裁决因此把 billable input/output/cost
  全部保存为 null，并记录 1 个 unobserved external call。
- 8/8 不完整意味着 ADR-0026 预算公式禁止运行，预算文件不存在，V3 held-out 未创建。
  该结果没有执行报告、工具、RAG、Evaluation 或注入案例，模型领域质量仍为 unknown。
- 结果只保存宽泛分类，没有保留 Adapter 的更细安全 `ProviderError.code`；无法区分截断、
  tool-call 解码、model identity 等子原因，也不得恢复临时原文推断。这是后续零调用采用
  决策必须考虑的 Observability Bad Case，不是本次重跑理由。
- 公开归档需要把“账本记录为零”和“厂商实际计费为零”分成不同字段；只有完整 8/8
  响应才能把账本 Usage 投影到 billable Usage，不完整结果必须保持 null/unknown。
- 全局 Provider 结果扫描器不能把新增 JSON 按旧报告模型猜测解析；现在先按稳定结构键
  分派真实 calibration、保守裁决和 V3 budget 三种合同，再交给严格 Pydantic 校验。
- 纯离线裁决会绑定结果 bytes SHA、code/public-CI 与 request-set，但不恢复 Provider 原文，
  也不会给下一次调用授权；这让“证据解释”与“重新实验”保持不同权限边界。
- `.gitattributes` 必须显式固定真实结果和裁决为 LF；否则 Windows checkout 的换行转换
  可能让 Linux CI 看到不同 bytes。暂存区复算 SHA 与本地结果完全一致，随后 exact-SHA
  Actions `31869409106` 通过，证明公开证据身份稳定。

### 2026-08-15：安全 Provider 错误 provenance 切片发现

- 领域 observation 已保存 Agent 层 `safe_provider_error_code`，但统一
  `ExperimentControlSnapshot` 和 V3 calibration result 仍只保存高层 `failure_code`；
  这正是 ADR-0027 要求补齐的跨接缝缺口。
- 新增 Provider-specific allowlist：DeepSeek/Zhipu Adapter 产生的有限常量可以透传，
  任意 SDK 文本或未知 Provider/code 不得进入公开结果。
- 旧 V3 结果没有细分码，继续解析为 `provider_error_code=null`；本切片不修改旧 JSON、
  不重算 SHA，也不能从源码反推历史根因。
- 本切片所有验证均离线，新增聚焦测试覆盖 allowlist、unknown-to-null、stop snapshot、
  calibration adjudication 和旧结果兼容；尚待完整门禁与公共 CI。

### 2026-08-15：DeepSeek calibration 失败采用决策发现

- DeepSeek Adapter 已经产生有限、安全、无正文的细分错误码；信息丢失发生在
  `classify_provider_error()` 将大部分 `ProviderResponseError.code` 压成统一
  `provider_response_invalid` 的实验分类层。
- 当前结果没有保存当时的细分码，因而不能通过读源码反推实际根因；“可能是哪一种”仍然
  不是证据，旧结果必须保持 unknown。
- 立即建立新 DeepSeek 诊断门只能改善根因可见性，仍不能取得领域质量，而且会继续形成
  围绕同一候选的版本循环；无限搁置又没有清晰终态。
- ADR-0027 因此关闭当前 V3，保留低层协议事实，并把双层失败分类设为未来任何真实
  Provider 门的前置条件：稳定高层 `failure_code` + allowlisted 可空细分码。
- 这项要求属于最小实验 provenance，不提前实现 5E 的统一 Trace；本批外部调用为 0。

## 2026-08-15：5D-7 收尾审查发现

- 原始 `2026-08-13-domain-e2e-evaluation-v1-design.md` 明确把 5D-7 最后一批定义为
  `5D-7 review`，而不是要求某个 Provider 必须通过；评测基础设施与模型采用结果是两个
  可独立裁决的对象。
- 分层 Dataset/Candidate/Result、Prompt/Context 双层身份、Evaluation 1.1、held-out
  生命周期、资源门和安全错误 provenance 已有代码、测试和不可变结果证据。
- 旧 Evaluation 1.0 可执行 development 基线保留 1/7 unsafe publication；1.1 安全基线
  在同类 7 场中为 0/7，且任务/失败分类准确率保持 1.0。这只证明已知开发攻击回归，
  不能表述为普遍抗注入。
- GLM-5.2 与 DeepSeek V4 Pro 都没有领域质量准入。协议层通过、Harness 安全降级和
  模型领域质量是三件不同的事；当前质量必须保持 unknown。
- 等待 GLM-5.3 会把内部阶段绑定外部发布时间；立即切 Flash 或追 Pro 又缺少新需求并
  违反既有重开门。ADR-0028 因而接受 5D-7 完成，将 Provider 采用留给条件化新门。
- 相关聚焦回归为 `130 passed, 4 subtests passed`，没有读取 Key、构造 Provider 或发起
  外部调用。

## 2026-08-15：5D 退出审查发现

- 5D 入口设计的十项功能要求均有实现与跨层测试证据；两个真实 Skill 在 Fake Provider、
  实际本地 `knowledge.search`、AgentLoop、ToolRuntime 和唯一 ReviewHarness 的组合下能
  形成类型化终态。
- 真实 Provider 领域质量未准入不会破坏控制链：非法/不完整响应不能形成工具证据，
  Agent 草稿不能直接发布，Harness 会降级或拒绝。因此“模型质量 unknown”是产品限制，
  不是受限 Agent Loop 的结构性失败。
- 5D 已有安全 run_id、Agent stop、Tool execution record、Harness terminal Artifact、
  Usage 和安全错误码，但它们分散在不同合同中；这正是 5E 统一
  `run/stream/event/trace/usage` 的真实需求，而不是先造框架再找用途。
- `SkillReviewExecutor.max_revisions` 是现有 Harness 政策参数，不属于 Manifest 的 Agent
  Loop budget，也未暴露给不可信用户。当前不改合同；5E 应把实际 runtime/Harness policy
  provenance 纳入 Trace，未来若下沉到 Skill 再通过 ADR 迁移。
- 核心执行与 Provider/实验两组跨层离线回归分别为 `173 passed, 34 subtests passed`
  和 `176 passed, 22 subtests passed`；没有读取 Key、构造真实 Provider 或发起外部调用。

## 2026-08-15：5E AgentRuntime V1 入口设计发现

- `SkillReviewExecutor.execute()` 对外是同步黑盒；只在最外层包装只能结束后重建事件，
  不能形成真实 `stream()`，也会丢失草稿准备失败前的部分安全 provenance。
- Agent stop、ToolResult、Harness transition/Artifact 已有足够稳定的事实源，不需要重写
  执行链；在稳定接缝增加默认关闭 observer 是最小且可测试的方案。
- 底层组件若直接构造全局 RuntimeEvent，会反向依赖 sequence、时钟和存储；更合适的
  边界是底层只发类型化安全 Signal，中央 Recorder 生成 Event 和最终 Trace。
- DeepSeek calibration 的真实 Bad Case 证明“已发送调用但没有规范化 Usage”必须表示为
  unknown/null，而不是复用 `TokenUsage(0, 0)` 误报实际零消费。
- ReviewHarness 的 publication 状态与 Runtime 自身状态不能合并：Harness 前失败没有发布
  状态，Agent 失败又可能被 Harness 安全降级为已发布确定性报告。
- Sea 的有序事件/Artifact 引用和 Saber 的事件观察思想可选择性吸收，但事件持久化、DAG、
  租约、恢复和并发没有当前 V1 Bad Case；EchoMind 的聚合指标也不能替代单次 Trace。
- 5E V1 采用进程内实时事件 + 原子最终 Trace 快照，不声称事件溯源、durable replay、
  cancel 或 Token streaming；这些边界让 5F 能用同一业务合同客观比较第三方 Runtime。

## 2026-08-15：5E-1 合同与存储源码审计发现

- 仓库使用 Python 3.11、Pydantic 2.x；机器消费的新合同普遍采用
  `ConfigDict(extra="forbid", frozen=True)`，5E-1 应保持同一严格风格。
- Provider 的旧 `TokenUsage` 是 frozen dataclass 且默认 0/0，只适合已经规范化的单次
  `ChatResponse`；Runtime Usage 不能修改它的历史语义，而应新增完整性明确的聚合合同。
- `FileRunStore` 已提供临时文件、flush/fsync、`os.replace` 和 run 目录内路径校验；
  `RuntimeTraceStore` 应复用这些成熟原则，但独立存在，以便 Harness 创建前失败也能落 Trace。
- 5E-1 不需要新增第三方依赖，也不应顺手重构现有 Harness store 或 Provider models。
- 共享 run ID 的实际权威位于 `app/harness/run_ids.py`，Runtime 请求与 Store 必须直接复用
  `normalize_run_id()`，不能复制正则或只依赖目录 resolve。
- `SkillExecutionRequest` 已是严格、冻结、绑定 Artifact commitment 的 Pydantic 输入；
  `RuntimeRunRequest` 应包装该对象，不重新定义 utterance、Router 或 payload 字段。
- 现有存储测试采用 `unittest` + `TemporaryDirectory`，覆盖不可变路径、篡改与失败后保留旧
  文件；5E-1 测试应沿用这一风格并额外验证 Trace 的严格复读。
- `app.harness.__init__` 会重导出 `ReviewHarness`，未来 Harness 若导入整个 Runtime package
  容易形成循环依赖；5E-1 应让 `app/runtime/__init__.py` 保持轻量，并把 Signal 合同放在
  不导入 Harness/Skill 的低依赖模块中。
- Harness Evaluation verdict 实际为 `pass/needs_revision/fail`；运行信号可以定义对应的
  Runtime 枚举，在 5E-2 接缝显式映射，避免底层 Signal 模块反向导入 Harness。
- 当前两个真实 Skill 都是 4 iterations / 3 tool calls，但 Manifest 合同允许最高
  20 iterations / 50 tool calls；默认 256-event 预算能覆盖最坏成对 Provider/Tool 信号、
  Harness 状态和 Runtime 边界，并保留余量。该预算仍是可信 Runtime policy，不是用户输入。

## 2026-08-15：5E-1 实现与验证发现

- Artifact `schema_version` 沿用项目现有 `1.0` 数据合同，不能误用要求三段式的应用 semver；
  Skill/Provider/Prompt/Harness policy 等软件版本仍使用三段式版本。
- Trace 必须独立校验 Provider/Tool start-close 生命周期，不能假定所有 JSON 都由 Recorder
  产生；否则手工构造或磁盘输入可以保存“没有 start 的 failure/completion”。
- `ToolResult` 的缓存命中允许 `attempts=0`，latency 也是 float；Runtime Signal/Usage 必须
  保真，而不能为了整数统计收窄既有 Tool 合同。
- Provider 已发请求但没有规范化响应时，`provider_calls_attempted>0`、response 为 0、
  Token/成本 total 为 null；observed lower bound 与精确 total 是两个不同字段。
- Store 的原子最终快照能防止半写和顺序覆盖，但 ADR-0029 已明确不承诺跨进程竞争、
  逐事件 durability 或进程崩溃恢复；这些不能从一次 `os.replace` 推导出来。
- Publication event 的 Artifact digest 必须能在 Trace 的相对引用中找到；只记录裸 SHA
  会让调用方无法定位或复核产物，因此由 Trace 复读合同强制这一关联。
- 本批 39 项聚焦、166 tests/55 subtests 相邻、655 tests/103 subtests 全量回归及全部门禁
  通过，外部 Provider I/O 为 0；下一步仅为公开验证。

## 2026-08-16：5E-2 入口恢复约束

- Canonical 状态、活动计划、RQ-001/002/003/006/009/011/012/014/017/019/028 与能力矩阵
  一致：5E-2 只负责 observer 接缝和统一同步 run 的纵向切片，5E-3 才负责 stream parity。
- ReviewHarness 必须继续是唯一发布权；Runtime 只能观察、组合和映射终态，不能复制评测、
  修订或发布决策。
- 5E-1 只提供安全语言、Recorder、Usage 与最终 Trace Store；它尚未证明底层信号来自实际
  执行时刻，也没有证明两个真实 Skill 能通过同一 Runtime `run()` 得到 Trace 与 typed output。
- 当前无领域 Provider 准入，因此 5E-2 应使用 Fake Provider + 真实本地 Tool/RAG/Harness
  验证控制流；不得把本检查点变成新的模型评测或读取 Key。
- 5P/5F/阶段 6/8 边界保持：Prompt Program、Pi/Claude SDK 对照、Session/Memory、durable
  event log、cancel/resume、DAG、Multi-Agent 与前端均不进入本轮。

## 2026-08-16：5E-2 接缝初步清单

- 现有主组合入口是 `SkillReviewExecutor.execute()`；它在 Harness 前完成 Boundary、Context、
  Compiler 绑定，并通过 `_BoundAgentDraftPreparationStep` 把 Agent draft/evidence 交给
  `ReviewHarness.run()`，最后由 `SkillTerminalOutputBuilder` 从 terminal Manifest/Artifact
  重建 typed output。
- Agent 内部真实接点位于 `AgentLoop.run()` 的 Provider 调用前后和 ToolRuntime 返回后；
  ToolRuntime 自身已有 attempts/latency/cache/fallback 安全 envelope，observer 不应复制
  Tool 参数或结果正文。
- Harness 的真实接点集中在 `ReviewHarness._transition()`、每次 Evaluator 返回并通过校验后、
  `_finish_terminal()`/`_publish()`；直接从最终 Manifest 事后补写会丢失实时 provenance。
- 5E-2 需要解决 `_BoundAgentDraftPreparationStep` 当前把 `AgentDraftPreparationError` 再包装后
  丢失完整 `AgentRunResult` 的 Bad Case；更合适的是实时 Signal，而不是把异常对象落 Trace。

### AgentLoop 具体接点发现

- `AgentLoop.run(request)` 当前只有同步 request 参数；增加 keyword-only、默认 no-op observer
  可保持所有旧调用方兼容，且 observer 不能进入 `AgentRunRequest.metadata`，避免被当作
  Provider/Tool 数据传播。
- `provider_call_started` 必须在 capability negotiation 成功后、`provider.chat()` 紧前发出；
  若在 capability 检查前发出，会把未发生的外部调用错误计入 attempted Usage。
- Provider completion 的 `ChatResponse` 已提供 finish reason/TokenUsage；observer 只投影这些
  安全字段，不传 response content、tool arguments 或 SDK payload。
- Tool started 应位于整批权限/预算/重复预检全部通过之后、每个 `ToolRuntime.execute()` 紧前；
  completed 使用 `ToolResult` 的 name/version/success/attempts/latency/cache/fallback，不能传 data。
- 当前事件族没有独立 Agent terminal Signal。这样 Provider/Tool 发生前的 context budget、timeout、
  invalid tool configuration 等 Agent stop 只能最终折叠为 Harness `draft_preparation_failed`；需在
  5E-2 方案比较中明确是接受该 V1 粒度，还是以显式合同修订增加安全 Agent terminal 观察。

### Provider、Tool 与 Harness 合同对齐

- `LLMProvider` 已公开 `provider_name` 与 `model_name`，AgentLoop 无需从响应正文或外部配置
  猜 Provider identity；completion 还可核对 normalized response 的 provider/model 是否一致。
- capability negotiation 抛出的 `ProviderCapabilityError` 是 `ProviderError` 子类但发生在 I/O 前。
  它应形成 Agent 安全失败/停止观察，但不能形成 provider started/failed 对，因为那会把零调用
  错记为一次 attempted call。
- Tool Signal 最小接点应放在 AgentLoop 对整批 ToolCall 完成原子预检之后、每次
  `ToolRuntime.execute()` 前后；不需要修改 ToolRuntime。这样一个 Agent 逻辑工具调用只记一对
  started/completed，而内部 retry/cache/fallback 由 `ToolResult` envelope 汇总，不会重复计数。
- `ReviewHarness._transition()` 在成功持久化 Manifest 后最适合发 `harness_transitioned`；source
  必须从写入前 Manifest 取得，revision count/attempt 已由状态机更新。
- `evaluation_completed` 应在 evaluator 返回且 `_validate_evaluation()` 通过后发出；blocking
  categories 只保存 issue category allowlist/安全码，不保存 issue 原文。
- `publication_decided` 应在 `_finish_terminal()` 成功写入 terminal Manifest 后发出，状态来自
  Harness terminal truth；`_step_failure_reason()` 的 `:ExceptionClass` 不得进入 Runtime Trace，
  只保留冒号前的稳定 reason code。
- 组件 observer 异常不应被当成业务失败静默吞掉。5E-2 内部 observer 是 Recorder，异常需由
  Runtime 显式映射为 observability failure；5E-3 的外部消费者隔离应由 Runtime event sink
  处理，而不是让 Agent/Harness 猜 observer 类型。

### Runtime 外层组合所需事实

- `ContextBuilderV1.build()` 已接受可信 `max_context_tokens` 并与 Manifest ceiling 取最小值；
  Runtime 可以直接传 `RuntimePolicySnapshot.max_context_tokens`，但不能改写 Skill 的工具、
  iteration、tool-call 或 timeout budget，这些仍由 `AgentRunCompiler` 从 Manifest 产生。
- Boundary、Context、Review Executor 分别有明确异常类型，足以在 Runtime 外层映射
  boundary/context/publication failure；原始异常 message 和类名不应进入 Signal/Trace。
- 两个真实 Skill 的 typed output 已统一包含 run_id/status/report/evaluation/evidence/warnings；
  RuntimeRunResult 可以泛型承载，不需要复制近期/单局业务字段。
- 5E-2 还必须明确 `RuntimeIdentitySnapshot` 的可信构造来源。Skill/version 可从 validated
  execution 取得，Provider/model 可从 LLMProvider 取得；Context、Prompt profile 与 Harness
  version 需要复用现有版本常量或由可信 composition root 显式注入，不能从用户 payload 推断。
- `RuntimeTrace` 当前要求 publication event 的 artifact SHA 都能在 Trace artifact references
  中找到，因此 Runtime 必须把 terminal Manifest records 投影为安全相对引用，而不是只保存
  final report 或直接复制 Artifact 正文。

## 2026-08-16：5E-2 入口审计最终裁决

- 只在 AgentLoop 观察 Provider 不完整：Harness 的 Evaluation、repair、Revision 经
  `ToolRuntime("llm.chat")` 再调用 Provider，且 Tool policy 可 retry。采用 run-scoped
  `ObservedLLMProvider` 作为唯一 Provider 观察点，同一实例同时注入 Agent 与 Harness。
- Tool 事件只表示 Agent 依据 Manifest 主动请求的业务 Tool；若全局观察 ToolRuntime，内部
  `llm.chat` 会被重复算成业务 Tool。AgentLoop 应在整批预检后发 started，并从 `ToolResult`
  投影 completed；正常失败为 `success=false + safe failure_code`。
- 当前没有可复现的 ToolRuntime 契约外抛 Bad Case，因此不单独增加 `tool_call_failed`。
  将来若出现，必须与 Tool Usage partial/unknown 一起设计，不能把未知 attempts 写成 0。
- 需要新增 `agent_run_terminated`，否则 context budget、timeout、max iterations、越权和非法
  Tool 配置会被 Harness 折叠成相同的 `draft_preparation_failed`。
- Harness observer 的真实接点是持久化成功后的 `_transition()`、Evaluation Artifact 注册后、
  terminal Manifest 写入后；state machine、Store 和 output builder 都不是业务观察点。
- Observer/Recorder 错误需包装为 `RuntimeObservationError` 并穿透 Agent/Harness 的 broad
  catch。5E-2 采用 fail-fast；5E-3 的外部 subscriber 隔离仍由 Runtime fan-out 处理。
- Evaluation Signal 直接使用零基 `manifest.attempt_id`，与 `evaluation_attempt_0.json`
  对齐；Context omission 使用独立冒号 section-ID 正则；missing finish reason 保留 null。
- Zhipu 当前把 missing Usage 写成 `TokenUsage(0,0)`，与 completeness-aware Runtime 冲突；
  5E-2 Task A 将使成功 ChatResponse 必须显式携带 Usage，并令 Zhipu missing/invalid Usage
  fail closed 为 allowlisted `provider_usage_unavailable`。本裁决不需要真实 Provider I/O。
- 当前 Recorder 存在 terminal/store 自指悖论。ADR-0030 决定用 prepare terminal candidate、
  prospective Trace、原子写盘、commit exact event；Store 失败时取消 candidate，只形成进程内
  observability failure，不递归重试同一 Store。
- 新写 Event/Trace schema 为 1.1，读端保留合法 1.0 并核对 TraceReference 版本；Runtime
  产品版本保持 1.0。当前没有持久化 Runtime Trace，因此无生产数据迁移。
- Event budget 需在副作用前按可信 Agent/Harness/retry 预算验证，并为 Runtime terminal 保留
  slot；不能让两个非终态事件吃满预算后再尝试记录失败。
- Harness 生命周期规则应由 Runtime 1.1 内部冻结的纯 reducer 共享给 Recorder 在线检查与
  Trace 离线复读，不能分别复制，也不能直接依赖未来可能变化的 Harness 状态图。
- Harness 的 `llm.chat` 位于 ToolRuntime 宽泛异常捕获内；Task B/C 接入 Observed Provider
  时必须让 `RuntimeObservationError` 在 retry、fallback 和 breaker 计数前穿透。该问题不属于
  Task A 的合同/端口实现，当前只记录为后续接线验收项。
- `ChatResponse` 的全部仓库调用均使用关键字参数，`usage` 移到默认字段前并改为必填没有
  位置参数兼容风险；生产 Zhipu Adapter 缺失/非法 Usage 应与 DeepSeek 一样返回安全
  `provider_usage_unavailable`。历史 `zhipu_probe.py` 不是 Runtime Provider 路径，本批不改其
  历史实验语义。

## 2026-08-16：5E-2 Task A 中断恢复审查

- 按 `AGENTS.md` 完整恢复 canonical state、活动计划、需求/路线/能力矩阵、ADR-0029/
  0030 与 5E-2 设计后，治理预检通过；当前仍只是 Task A，不进入 Task B。
- 上轮未提交实现已经包含 Runtime 1.1 lifecycle reducer、默认关闭 observation port、
  prospective terminal candidate、Trace/Reference 版本一致性和 Zhipu missing Usage
  fail-closed；恢复后首次聚焦回归为 `114 passed, 44 subtests passed`。
- 该绿灯尚不足以验收 Task A。实现审查仍需补五类直接证据：Trace Store 失败后的
  candidate abort、1.0 Event 对 1.1-only 语义的拒绝、Runtime/Harness transition 图同步、
  terminal candidate 重复 commit/abort、publication digest 必须指向 `final_report`。
- 本轮恢复没有读取 Key、构造/调用 Provider、运行 held-out、修改 Prompt/模型或进入
  `ObservedLLMProvider`/AgentLoop/Harness 接线。

## 2026-08-16：5E-2 Task A 本地收尾发现

- 旧 Schema 1.0 的合法形状比最初兼容测试更宽：Provider finish reason 可为任意安全
  厂商码，Tool 失败没有 `failure_code`，published/degraded publication 的摘要列表可以
  为空。若把 1.1 严格规则直接放在嵌套 Signal 上，父级 Event 尚未读取版本就会误拒旧数据。
- 最小修正是让 Signal 保留跨版本可表达能力，把有限 finish reason、Tool 成败/错误码一致性
  和 publication 摘要数量放到 `RuntimeEvent.event_schema_version` 边界。Recorder 默认写
  1.1，因此新事件仍严格；合法 1.0 只在显式旧版本读取时兼容。
- 两阶段 terminal 还必须保留已经落盘的 Harness 终态。若 Harness 已 transition 到
  degraded/published/rejected，即使 Runtime 在 publication signal 前失败，`run_failed`
  也不能把已知 publication 写成 null；新增红绿测试后由共享 lifecycle reducer 强制。
- Task A 当前聚焦回归为 `131 passed, 44 subtests passed`，完整回归为
  `691 passed, 110 subtests passed`；两套 RAG、compileall、Harness SDK/tracked-data
  boundary、dry-run、governance 和 diff check 通过。它只证明合同/端口/终态地基，
  不证明 AgentLoop/Harness 已发信号或统一 `run()` 已存在。
- 本地收尾全程没有读取 Key、构造/调用真实 Provider、运行 held-out、调整 Prompt/模型或
  进入 Task B。

## 2026-08-16：5E-2 Task A 公共证据

- 实现提交 `2e78c9606fe93b56657d4bb13c8efe0f1eed98fe` 已由 GitHub Actions run
  `31947625293` 对 exact SHA 完整验证；公共 CI 无 Key、真实 Provider I/O 或 held-out。
- Task A 只冻结合同、端口、Usage 和 terminal 地基。下一步 Task B 才让真实 Agent 执行点
  发出这些 Signal；因此公共 CI 不能解释为 observable `run()` 已完成。
