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

## 2026-08-16：5E-2 Task B 本地实现发现

- `ObservedLLMProvider` 必须自己在 started 前复核 capability；只依赖 AgentLoop 预检会让
  Harness `llm.chat` 的结构化请求在 delegate 内失败前已被错记为 attempted call。
- Provider phase 只接受内部 `agent_loop_iteration` 或 `evaluate/evaluate_repair/revise`；
  缺失、冲突、布尔/非正迭代和未知 Harness step 均在 Provider I/O 前以 observation failure
  停止，不把完整 metadata 或正文写入 Signal。
- Adapter-owned `provider_error_code` 允许列表原先位于 Evaluation 实验模块。Task B 将其
  下沉到低依赖 `app.providers.error_safety`，Runtime 与旧实验共同调用同一投影；既有公开
  函数导入和允许列表语义由回归保持不变。
- AgentLoop 公共 `run()` 用 keyword-only、默认 `None` observer 包住内部 `_run()`；这样每个
  正常返回的 `AgentRunResult` 统一发一个 terminal，而 observer 关闭时甚至不构造 Signal，
  旧结果和 Provider 请求可逐字段相等。
- 业务 Tool started 位于整批数量、白名单和重复预检之后；completed 只投影 ToolResult 的
  name/version/success/attempts/latency/cache/fallback 与允许列表错误码，不投影 arguments、
  data、call ID、错误文本或 upstream error。未知 Tool 错误码收敛为 `tool_failed`。
- 实现后审查发现 `ToolRuntime` 会把 `RuntimeObservationError` 当普通 handler 失败并进入
  retry/fallback。新增红灯后在 retry、breaker 和 fallback 前显式穿透：started 观察失败
  对 Provider/Tool 为零副作用，completed 观察失败只保留已经发生的一次副作用且不继续。
- Task B 当前聚焦回归为 `81 passed`，完整回归为 `721 passed, 110 subtests passed`；两套
  RAG、compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check
  已在本地通过。没有读取 Key、调用真实 Provider、运行 held-out、修改 Prompt/模型或进入
  Harness observer/统一 `run()`；Task C/D 仍未开始。

## 2026-08-16：5E-2 Task B 公共证据

- 实现与状态提交 `28bd910525a7522be16bd69b6e945846839a4cd8` 已推送；GitHub Actions
  `31952026988` 对 exact SHA 的完整 pytest、两套 RAG、compileall、SDK/tracked-data 边界、
  Harness dry-run 与治理全部成功。
- Task B 只公开证明 Provider/AgentLoop 观察合同和 observation fail-fast 的工程接线，
  不证明 Harness observer、统一 `run()`、真实 Provider 领域质量、模型切换或 5E 完成。

## 2026-08-17：5E-2 Task C 本地实现发现

- `ReviewHarness` 新增可选 `RuntimeSignalObserver`，但继续保持唯一评测、修订和发布权；
  observer 关闭时不额外读取/投影 Artifact，以保持旧 Harness/Executor 行为。
- Harness transition 在 `write_manifest()` 成功并（开启 observer 时）重新读取 Manifest 后
  才发出，初始 `created → facts_ready`、修订边和 terminal transition 均使用真实
  `from_status`、`to_status` 与 `revision_count`。
- Evaluation 先校验返回对象、写入并重新读取 `evaluation_attempt_<attempt>.json`，再发出
  `evaluation_completed`；attempt 直接取零基 `manifest.attempt_id`。blocking projection
  只允许当前真正阻断策略的 `prompt_injection`，不保存 quote/解释/修正文本。
- terminal Manifest 写入成功后，开启 observer 的 Harness 会重新校验所有已登记 Artifact，
  publication 对 published/degraded 只投影真实 `final_report` SHA-256，rejected 为空。
  `app/runtime/artifacts.py` 提供 body-free `RuntimeArtifactReference` 投影，依赖
  `FileRunStore.read_artifact()` 发现篡改并 fail closed。
- `RuntimeObservationError` 在 Harness、`SkillReviewExecutor` 和
  `SkillAgentDraftPreparer` 的 broad catch 前穿透；不会被转成普通业务失败或
  deterministic fallback。
- 新增 Task C 聚焦测试 8 项；本地完整回归为 `729 passed, 110 subtests passed`。
  RAG development/holdout、compileall、tracked-data boundary、Harness dry-run、治理和
  diff check 通过；Provider/Key/held-out I/O 为 0。Task C 尚待提交、推送和 exact-SHA CI。

## 2026-08-17：5E-2 Task C 公共证据

- 提交 `8b69c9b` 已推送到 `origin/main`；GitHub Actions run `31957712118` 对 exact SHA
  完成并成功。
- 公共 CI 通过治理、`729 passed, 110 subtests passed`、两套 RAG、compileall、Harness
  SDK/tracked-data boundary 与 dry-run；没有 Key、真实 Provider 或 held-out I/O。
- Task C 至此正式闭环；Task D 是 5E-2 的唯一下一步，不能把 Task C 的观察接缝或 Artifact
  projection 解释成统一 `AgentRuntimeV1.run()` 已完成。

## 2026-08-17：5E-2 Task D 恢复审查

- 未提交的 `AgentRuntimeV1` 初稿已经能组合 Boundary、Context、共享
  `ObservedLLMProvider`、真实本地 RAG、Harness、typed output 与最终 Trace；新增首轮
  纵向测试为 `7 passed`，既有相邻回归为 `121 passed`。
- 对照已接受的 5E-2 设计发现三个尚不能带入验收的缺口：
  1. `RuntimeRunRequest` 还没有在合同层拒绝 rejected/ambiguous Router 结果；
  2. `run()` 尚未抽出供 5E-3 复用的单一 `_execute()` 核心；
  3. Trace 写入失败目前只返回 failed result，却没有按 ADR-0030 取消 prospective
     terminal 后提交内存 `run_failed(trace_persistence_failed)`。
- 当前成功路径使用同一个 run-scoped observed provider，实测 Provider phase 为
  `agent, agent, evaluation`，连续 ordinal 和完整 Usage 可以由最终 Trace 重建；这仍是
  Fake Provider 证据，不代表任何真实模型领域质量。

## 2026-08-17：5E-2 Task D 本地验收发现

- 成功路径真实事件交错为 Runtime 基础事件 → `created→facts_ready` → Agent Provider/
  knowledge Tool → Agent terminal → Harness knowledge/draft/evaluation → publication → Runtime
  terminal；不是任务结束后的日志重排。
- 一次修订路径的共享 Provider phase/ordinal 为
  `1 agent, 2 agent, 3 evaluation, 4 revision, 5 evaluation`，Evaluation Artifact attempt 为
  `0, 1`；证明 Agent 与 Harness 使用同一 observed Provider，但不证明真实厂商行为。
- Agent 或 Evaluation Provider 失败仍可由 Harness 产生 deterministic fallback，因此是
  `Runtime completed + publication degraded`；Boundary/Context、typed output、observation 或
  Trace 提交失败才是 `Runtime failed`。Runtime 状态与报告发布状态不能混为一谈。
- Trace 只保存真实 Artifact 的 path/schema/producer/SHA，并逐文件复算摘要；报告正文与
  Prompt 不进入 Trace。rejected publication 不含 final report digest。

## 2026-08-17：5E-3 Live `stream()` 入口审计

- 当前 `AgentRuntimeV1.run()` 已把全部业务控制流集中在 `_execute(request)`；`run()` 只负责
  类型检查、调用 `_execute()` 以及把可信 Recorder/观察失败映射为安全失败结果。该单一核心
  是后续 `run()`/`stream()` parity 的正确复用点，不能复制第二套执行流程。
- `_RecorderObserver.observe()` 目前只调用 `RuntimeRecorder.emit()`；Recorder 的事件只保留
  在内存 `events`，没有事件订阅者、队列或对外回调。因此当前 `run()` 的事件是真实执行时刻
  产生的，但外部调用方只能在返回后读取最终 Trace，不能实时消费。
- 非终态事件由组件 observer 产生，终态事件有特殊的两阶段路径：`prepare_terminal()` 先生成
  候选，Trace 通过 `RuntimeTraceStore.write_trace()` 后才 `commit_terminal()`。任何 stream
  设计都必须在 commit 后再交付成功终态；不能在 prepare 阶段把 `run_completed` 发出去。
- Trace 写失败和 Recorder/observer 失败会产生安全的内存 `run_failed`，但当前
  `_commit_failed_without_trace()` 直接调用 Recorder，尚无统一事件交付接缝；5E-3 实现时须
  确保这条失败终态也只交付一次，并与 `RuntimeRunResult` 的 failed 状态一致。
- `RuntimeRecorder` 是单线程顺序状态机：它负责 sequence、UTC/monotonic 时间、调用配对、
  lifecycle、event budget 和 Usage。stream 消费者不能直接修改 Recorder，也不能在消费者线程
  中重建事件或重新读取 Trace。
- `ReviewHarness`、`SkillReviewExecutor`、`AgentLoop` 的 observer 接缝均为同步调用；内部
  observer 失败按 `RuntimeObservationError` fail-fast，不能被外部消费者失败污染。5E-3 必须
  把“可信 Recorder 失败”和“非可信订阅者失败”分成两层错误边界。
- 方案比较初步结论：直接 generator 会把深层同步回调改造成侵入式协程/生成器并难以隔离消费
  者失败；外部消息队列会提前引入 durable/retry/offset/跨进程语义；最小可验证方案是进程内
  worker + 有界 `queue.Queue`，由 Runtime 在同一 `_execute()` 中产生事件，stream 线程只负责
  读取并交付。背压 V1 采用“队列满时阻塞执行、保持事件不丢失”的明确语义，不承诺取消/恢复。
- 本轮只做入口审计和方案冻结，没有新增依赖、没有读取 Key、没有 Provider I/O、没有修改
  Prompt/模型/RAG，也没有实现完整 `stream()`。

## 2026-08-17：5E-3 第一批 stream TDD

- 新增 `RuntimeStreamItem` 严格 item 合同：`kind=event` 只能携带一个 `RuntimeEvent`，
  `kind=result` 只能携带一个既有 `RuntimeRunResult`；不新增第二套业务输出模型。
- `AgentRuntimeV1._RecorderObserver` 现在在 Recorder 成功追加事件后调用可选 sink；
  `run()` 传 `None`，旧调用路径不增加队列和线程。
- `stream()` 使用每次运行独立的 daemon worker 和有界 queue；第一次 `next()` 前不启动
  worker。worker 复用 `_run_with_sink()`，所以预期失败映射与 `run()` 相同。
- terminal 交付已接入成功 Trace commit、失败 Trace commit 以及内存
  `trace_persistence_failed` 路径；成功/失败 terminal event 都在 commit 后才进入 queue。
- 第一批聚焦 `tests/test_agent_runtime_stream.py` 为 `5 passed`；第二批补充 parity、tiny queue
  背压、订阅关闭、worker 异常、queue capacity、degraded/rejected/boundary 失败后为
  `15 passed`；相邻 Runtime/Agent/Harness
  合同与 Store 回归为 `70 passed`；compileall 通过。

## 2026-08-17：5E-3 公共闭环与 5E-4 入口

- 提交 `80b76a1` 的 GitHub Actions run `31960987333` exact-SHA 公共 CI 成功，完整 pytest、
  两套 RAG、compileall、治理、SDK/tracked-data boundary 和 Harness dry-run 均通过；5E-3
  正式闭环。
- canonical 已切换到 `5E-4`。5E-4 的职责是 Runtime V1 退出审查和 exit matrix，
  不是继续堆功能；矩阵必须把承诺、源码、测试、公开证据、限制和退出结论逐项绑定。
- 本轮仍不读取 Key、不调用真实 Provider、不切换模型、不修改 Prompt/RAG，不进入 5P/5F/API/
  Memory/MCP/durable log/cancel-resume。

## 2026-08-17：5E-4 首轮 exit matrix 审计

- 按 `docs/plans/2026-08-17-agent-runtime-v1-exit-matrix.md` 建立逐项矩阵；每条承诺都区分
  源码、直接测试、exact-SHA 公共证据、当前限制和退出影响。
- Runtime 相关聚焦集合为 `128 passed`；没有发现当前 V1 合同必须立即补的结构性缺口。
- 明确 deferred/unknown：真实厂商领域质量、API/SSE、durable event log、崩溃恢复、
  cancel/resume、Memory、MCP、Multi-Agent、LangGraph/SDK 采用和生产 p50/p95/SLO。
- 这只是入口审计和首轮矩阵，不是 5E 关闭结论；仍需完整回归和最终退出决策。

## 2026-08-17：5E-4 本地退出结论

- 完整回归 `762 passed, 110 subtests passed` 与全部本地门禁通过；没有发现当前 Runtime V1
  必须补的结构性代码缺口。
- 本地退出决策为 `close-with-deferred-boundaries`，不是“production-ready”：真实模型质量、
  API/SSE、durable recovery、cancel/resume、Memory/MCP/Multi-Agent/SDK 和生产 SLO 继续按
  既定阶段处理。
- 5E-4 仍需 exact-SHA 公共 CI；通过前不切换到 `5P-entry-design`。

## 2026-08-17：5E-4 公共闭环与暂停交接

- 退出审查提交 `3d3656195a66adfd4595cffa145c978d24c33628` 已由 GitHub Actions run
  `31962252231` 完成 exact-SHA 公共验证；完整 pytest、两套 RAG、compileall、治理、安全
  边界和 Harness dry-run 均成功。
- `close-with-deferred-boundaries` 因而成为 5E 的最终退出结论：Runtime V1 合同完成，真实
  Provider 领域质量、API/SSE、durable recovery、Memory/MCP/Multi-Agent/SDK 与生产 SLO
  继续保持 deferred/unknown。
- canonical 只交接到 `5P-entry-design`。按 RQ-039，本轮没有开始 5P 设计或代码，等待用户
  再次明确“继续”。

## 2026-08-17：5P-entry-design 首轮范围恢复

- 用户已用“继续下一步”解除 RQ-039 的暂停，当前只授权 `5P-entry-design`，尚未授权
  FastAPI 实现或 5F。
- 仓库当前没有 `app/api` 或 FastAPI 应用代码；`pyproject.toml` 也需要在后续依赖审计中
  确认是否已有 FastAPI/Pydantic Web 依赖，不能把路线中的接口清单误当作现有实现。
- v1.3 路线列出 recent、run/status/report 和 follow-up 五类端点，但较晚的专项发现又明确
  5P 只承诺类型化近期复盘入口，单局/对话式澄清属于阶段 6。该差异是入口设计必须先裁决的
  范围问题，不能直接按五个端点全部实现。
- 5P 必须复用现有 `AgentRuntimeV1`、`RuntimeTraceStore` 与 Harness Artifact，不应创建第二套
  运行状态或让 API 绕过唯一发布门；SQL、Session、Memory、鉴权、SSE 和完整前端继续属于
  阶段 6/8。

## 2026-08-17：5P Runtime/API 接缝初审

- `pyproject.toml` 当前没有 FastAPI、Starlette 或 ASGI Server 依赖；5P 若采用 FastAPI，属于
  需要 ADR 和独立依赖批次验证的新运行表面，不能假设已经安装。
- `AgentRuntimeV1` 的输入不是 Riot ID，而是已经 selected、通过 Schema 约束并携带
  `player_summary + deterministic_report` 的 `RuntimeRunRequest`；其构造还需要 Catalog、
  Provider、Knowledge Provider、Evaluator/Reviser factory 和 runs root。API 前面仍缺一个
  composition/application-service 边界，不能把 HTTP handler 写成新的业务编排器。
- Runtime 已提供同步 `run()` 和进程内 iterator `stream()`；5P 可以先消费 `run()` 形成
  类型化 HTTP 结果。直接把 iterator 暴露成 SSE 会提前承担断连、异步桥接、重放和生命周期
  语义，仍应留在阶段 6。
- Harness 与 Runtime 分别在同一 run namespace 下保存业务 Artifact 和最终
  `runtime_trace.json`；API 读取端应通过现有严格 Store/模型复读，而不是直接 `open()` 任意
  用户路径，也不能从 Trace 重建被明确排除的报告正文。
- 5P 的真正首个设计问题不是“选哪个 Web 框架”，而是明确应用服务怎样把一个可信的近期复盘
  请求转换为现有 RuntimeRequest，以及哪类结果可以安全映射为 HTTP response。

## 2026-08-17：5P 产品请求到 Runtime 请求的断层

- `build_player_summary()` 已把 RiotClient/DataDragon 作为参数注入，领域计算可复用；但产品入口
  仍需为 Riot/API 限流、404、超时和部分比赛失败建立安全错误映射，不能把脚本打印或原始异常
  直接变成 HTTP 正文。
- 确定性报告的核心 `build_report()` 仍位于 `scripts/generate_markdown_report.py`。API 不应导入
  CLI 脚本作为产品依赖；5P 实现阶段需要把纯报告渲染提升到 `app` 内的稳定服务，再让 CLI
  兼容调用同一实现。
- 当前真实 `AgentRuntimeV1` composition root 主要由测试中的 `_runtime()` 辅助函数展示；生产
  CLI `run_review_harness.py` 仍是旧 Harness 入口。5P 需要新增一个明确的应用 composition root，
  统一构造 Catalog、Knowledge Provider、LLM Provider、Evaluator/Reviser 与 Runtime，避免路由
  函数自行拼装基础设施。
- 类型化 `POST /reviews/recent` 已经可信地声明任务是近期复盘，不应再把用户的 Riot ID 或固定
  句子送入自由文本 Router 猜测任务。入口设计需提供一个受信任的 typed Skill selection/compiler，
  同时继续经过 Catalog 版本、Pydantic Input、Artifact binding 和 Runtime boundary 校验。
- 推荐的最小产品流是同步 POST：HTTP Request → application service → Riot/DataDragon → Summary
  → deterministic report → typed recent Skill request → AgentRuntimeV1.run() → terminal response。
  这能产生真实 Runtime/Artifact 证据，但不承诺后台任务、SSE、恢复或多用户隔离。

## 2026-08-17：5P 类型化选择与端点范围补充审计

- 现有 `RouterDecision` 的终态只覆盖 matched/no-available/no-match/multiple-match 语义；
  `POST /reviews/recent` 已由端点类型可信地确定任务，不应构造一条固定自然语言再让
  `DeterministicRouter` 猜测。5P 设计需要定义受信任的 typed selection/compiler：从当前
  Catalog 精确取得 `recent-form-review` name/version，构造带真实 evidence 的 selected
  decision，并继续接受 Skill Input、Artifact binding 与 Runtime boundary 的全部校验。
- 历史 v1.3 曾列出 recent、run、status、report、follow-up 五类端点；较晚专项约束又把单局、
  对话和澄清推迟到阶段 6。当前最小边界应排除 `follow-ups`；5P 可评估保留同步 recent POST、
  只读 run/report 查询与 health，`status` 是否单列必须以它相对 run 详情的独立价值裁决，不能
  因旧清单存在就全部照搬。
- Trace 按安全合同不保存报告正文，因此 `/runs/{run_id}/report` 必须只从 Harness final
  Artifact 复读；`/runs/{run_id}` 只能通过受控 Store/严格模型返回允许字段，不能接受或拼接
  用户提供的任意路径。
- 5P 审计起点 HEAD 与 `origin/main` 同为 `5de949d0...`；除活动计划的 findings/progress 外
  工作树无其他改动，治理预检再次通过。Runtime/Store/数据/报告/旧 Harness 的精确源码位置已
  定位，下一批只读审计可以避免从 CLI 文件名推测边界。
- `RuntimeRunResult` 是调用结束时的严格终态 envelope，但当前没有独立的 Result Store；落盘事实
  是 Harness `manifest.json`、不可变 Artifact 与 `runtime_trace.json`。`RuntimeTraceStore.read_trace()`
  还要求可信的 `RuntimeTraceReference`（含 SHA），不能仅凭 URL run_id 直接宽松解析文件。因此
  5P 查询服务要么安全地从严格 manifest/trace bytes 重建引用并校验，要么补一个受控查询
  repository；不能声称现有 Store 已直接提供 `get_run(run_id)`。
- `FileRunStore` 已防绝对路径、目录穿越、跨 run Artifact、摘要篡改和覆盖写；5P 可以复用这些
  不变量。报告查询必须先从 manifest 选择唯一允许的 final-report record，再调用
  `read_artifact()` 校验真实 bytes，不能把 manifest 的路径直接返回给 handler 自行打开。
- `RuntimeRunRequest` 强制 selected Router decision；完成态 `RuntimeRunResult` 必须同时具有
  publication、typed output 和 Trace reference，失败态不得暴露 output。HTTP 映射应保留这个
  fail-closed 语义，而不是在 Runtime failed 时退回未经门禁的草稿或报告正文。
- Runtime 的成功/失败终态与 Harness publication 是两条维度：极少数可观测性或 typed-output
  失败可能在 Harness 已持久化 publication 后让 Runtime 返回 failed。5P 查询合同应原样展示
  `runtime_status`、`publication_status` 和安全 `terminal_reason`，不能把任意 published manifest
  简化成“Runtime 成功”，也不能仅凭 HTTP 200/500 丢掉这一区别。
- 现有 Runtime 的 typed output 来自 `SkillReviewExecutor`，Artifact 由 manifest 重新校验后投影；
  `run()` 已是可复用的唯一同步执行核心。因此 Application Service 应只负责编译产品输入和组装
  Runtime 依赖，不重写 Agent/Harness 生命周期、Artifact 投影或 publication 判断。
- RiotClient 是有 15s request timeout 的薄 transport；重试/缓存/熔断和安全错误码实际存在于
  `build_riot_tools()` 的 Tool Runtime adapter 中。但当前 `build_player_summary()` 直接调用
  RiotClient，而不是经过这些 Tool。5P 设计必须诚实说明：若首批复用 summary builder，只能在
  Application Service 顶层做安全异常映射，不能声称已经获得 Tool Runtime 的全部可靠性语义；
  若把数据收集也迁入 Tool Runtime，则是更大的重构批次，需单独测试。
- 当前 summary builder 对 timeline/detail 的局部失败会把 `str(error)` 写进 summary 的
  `timeline_error`/`failed_matches.error`；CLI 可诊断设计不等于公网安全响应。5P API DTO 不得
  透传这些字段，上游异常只映射 allowlisted 错误码；未来若公开 summary Artifact，还需单独做
  脱敏/公共投影。
- `DataDragonService` 初始化时会同步加载版本和多份静态数据，缓存未命中时进行最多 20s 的
  HTTP 请求；把它按请求构造会增加阻塞和失败面。composition root 应将其作为长生命周期依赖
  注入，并把冷启动/缓存失败映射为 upstream-unavailable，而不是由 handler 临时实例化。
- 确定性 `build_report()` 是纯渲染逻辑，但仍位于 CLI 脚本且 main 会额外构造 terminology 与
  DataDragon。实现批应先把纯渲染提升到 `app`，让 CLI/API 共用；本设计批只冻结此边界。
- `scripts/run_review_harness.py` 不能充当 5P composition root：它仍组装旧
  `SequentialDraftPreparer + ReviewHarness`，默认只创建 ZhipuProvider，并不构造
  `AgentRuntimeV1`、Catalog、ContextBuilder 或 Runtime policy。5P 需要新的 app-level
  composition module；CLI 可后续迁移复用，但 handler 不能导入这个脚本。
- `.env.example` 仍声明单一默认 Zhipu/GLM-5.2 配置；本轮没有领域 Provider 准入。5P 的
  composition 设计应支持注入 Fake Provider 做 API 测试，并把真实启动时的 Provider 配置失败
  映射为服务不可用；不能因新增 HTTP 入口而把 GLM-5.2 宣称为生产默认质量已通过。
- `SkillExecutionRequest` 仍要求非空 `user_utterance`，即使 typed endpoint 已可信确定任务。设计
  应明确该字段只保存一条服务器生成、不可用于重新路由的审计描述（或在未来版本化合同中新增
  typed task origin），不能把它解释成用户自由文本、更不能再次调用 Router。
- Catalog 已提供严格、不可变、按 name 的 Skill 快照与 `get(name)`；typed selector 可以基于它
  绑定当前 `recent-form-review` 版本。所有 input payload 与 Artifact digest 仍必须由
  `SkillExecutionBoundary` 重算校验，所以受信任选择不会绕过执行安全边界。
- 现有 `RouteEvidence.positive_signals` 是通用机器可读字符串，不要求它一定来自自然语言；因此
  V1 无需为了 typed endpoint 新建第二套 selection 模型。compiler 可以产生明确的
  `entrypoint:reviews.recent` 信号、`MATCHED_SKILL` reason 与 Catalog 当前版本，并在说明中标记
  trusted typed entrypoint；禁止使用某句中文模板制造关键词命中，也不调用 Router。
- typed selection 仍需测试 Catalog 缺失、Skill 版本漂移、证据/候选不一致和 input schema
  不匹配；`RouterDecision` 自身已经强制 selected 只能有一个候选、一个对应正证据且不能带
  negative signal，这些合同可直接复用。
- `RecentFormReviewInput` 只需要完整 Summary、确定性报告和五选一 focus；产品请求因此可以保持
  小而严格：Riot ID 拆分字段、count/queue/min-duration/focus，不暴露 Runtime policy、Prompt、
  Skill version、run_id 或任意文件路径。Skill 预算/质量阈值应由服务器从 manifest 编译。
- `RecentFormReviewOutput` 已有产品级 `status/report/evaluation_score/evidence_source_ids/warnings`，
  且 rejected 禁止 report。同步 POST 可以在 Runtime completed 时返回这个 typed output；失败时
  返回 body-free 的 run 状态与安全错误，而不是另造一份“看似成功”的报告 DTO。
- 当前 recent Skill 固定 `knowledge.search`、4 iterations、3 tool calls、30s、16000 context、85
  分和允许确定性 fallback；HTTP 层不应让客户端覆盖这些安全/质量策略。同步 POST 在最坏情况下
  还叠加 Riot/DataDragon I/O，因此 5P 必须明确这是早期阻塞式切片，不承诺低延迟 SLO。
- 全仓搜索确认 `RuntimePolicySnapshot` 目前只在测试/评测装配中手工构造，没有生产 policy
  compiler。5P 的 typed request compiler 必须从已选 Skill manifest 同源投影 iterations、tools、
  timeout、context、quality threshold 和 fallback，再加服务器固定的 runtime policy version、
  event budget、max revisions；客户端不能提交 policy。
- `AgentRuntimeV1` 构造只依赖 runs_root、Catalog、LLMProvider、RuntimeExecutionFactory 和可选
  ContextBuilder，适合由单一 composition root 长生命周期创建。每个请求只编译新的
  RuntimeRunRequest；不应每次重新加载 Skill/RAG/Provider，也不应让 HTTP handler知道
  evaluator/reviser factories。
- 路线证据存在两层而非简单冲突：主 roadmap 的完整 Web 纵向切片仍归阶段 6；v1.3 amendment
  在阶段 5 加的是“不依赖临时数据库的早期 API 切片”。因此 5P 可以验证真实 HTTP→Runtime
  接缝，但不能把它包装成完整会话产品，也不改变阶段 6 的 SQL/Session/Memory/SSE/前端职责。
- v1.3 的旧五端点清单包含 follow-up，但 follow-up 天然需要会话语义、上一轮上下文和澄清；在
  没有 Session/Memory 的 5P 中保留会造成伪会话或隐式文件状态。应由新 ADR 明确把它推迟到
  阶段 6，而不是静默遗漏旧清单。
- `GET /runs/{run_id}/status` 相对 `GET /runs/{run_id}` 在同步、无后台任务的 V1 没有独立状态轮询
  价值；推荐不单列，避免两个相同事实的 API 合同。若后续引入后台任务/SSE，再按真实消费者
  需求增加轻量 status endpoint。
- RQ-026 已明确“优先类型化入口”，为 5P typed compiler 提供最新需求依据；RQ-039 只暂停到
  用户再次明确继续，本轮必须新增 RQ-040 记录暂停已解除，但不能删除或倒写 RQ-039 历史。
- RQ-017 本身只列 2/5B/5D/5E 与 6-8，但 ADR-0029 和 5D exit review 另有明确的
  `5P Prompt Program V1` 归属；因此不能把 5P 缩成纯 HTTP。下一步要读取该历史裁决的精确
  目标，再决定 5P 内部顺序：应先完成早期产品入口，让 Prompt Program 有真实产品消费者，
  随后仍在 5P 内单独设计/验收，不能与 FastAPI 接缝一次混合实现，也不能推迟到 5F。
- 本轮查 ADR-0031 时误猜了文件名 `0031-agent-runtime-live-stream-delivery.md`；真实文件应先从
  列表读取后再打开。该只读错误没有文件影响，后续不重复猜路径。
- 精确证据确认 `5P Prompt Program V1` 是 5D 退出时已冻结的后续能力名，不是本轮临时补项；
  ADR-0029 也明确其顺序保持不变。因此 5P-entry-design 必须同时给出早期产品入口与 Prompt
  Program 的内部子阶段顺序，不能设计完 API 就直接进入 5F。
- 5E 已把 `prompt_profile_id/version` 写入 Runtime identity，但并未提供 Prompt 资产加载、版本
  解析或产品级 program 编译。这意味着 Prompt Program V1 应深化现有 provenance，而不是重写
  AgentRuntime：它的真实消费者会是 5P composition/runtime request，而发布权仍在 Harness。
- 当前 Agent 的实际初始 Prompt 由 `ContextBuilderV1` 里的 `_INTERNAL_POLICY`、Skill
  `SKILL.md` 指令、确定性事实、用户请求和知识证据共同渲染；Evaluation/Revision 又由独立
  prompt builder/factory 组装。Runtime 却把 `prompt_profile_id/version` 写死为
  `<skill>-coach@1.0.0`，尚未证明该 identity 与实际 Prompt 资产字节绑定。Prompt Program V1
  应先解决“可加载、可版本化、可校验 provenance”，而不是单纯润色提示词。
- 5P 内部顺序推荐先完成 application/compiler/composition 的无 HTTP 核心，再做 Prompt Program
  V1 的合同化，之后接 FastAPI：这样真实 composition 是 Prompt Program 的消费者，HTTP 纵向
  测试又能验证最终 identity；若先把 FastAPI 完成再补 Prompt，API 终态会先暴露虚假的硬编码
  prompt provenance。
- 本轮 Prompt 符号搜索的正则因 PowerShell 引号导致 `role=\"system\"` 被截断并报 unclosed
  group；成功的 Context/Compiler 源码读取仍有效。后续改用多个 `-e` 固定字符串，不重复该正则。
- 实际 Prompt 资产比一个 system prompt 更分散：Context internal policy、Skill instructions、
  secure Evaluation 1.1 system/user/repair/schema、Revision system/user/validator 都参与最终控制流；
  CLI 中还残留旧 Evaluation 1.0 和重复 system prompt 常量。Prompt Program V1 应为生产
  composition 选择唯一安全组合并记录各资产 identity/digest，避免不同入口悄悄采用不同版本。
- 5P production composition 应明确使用 `SecureChatEvaluationAdapter` 与 Evaluation 1.1，而不是
  旧 `run_review_harness.py` 的 `ChatEvaluationAdapter` 1.0；这不是调 Prompt 文案，而是延续已
  通过的 prompt-injection blocking policy。Reviser 仍只能处理可修订事实问题，不能修订
  blocking injection issue。
- `app.evaluation.prompt_context_identity` 已经有可复现的 component fingerprint：Skill
  manifest/instructions、Context contract、knowledge tool、Evaluation schema/system/user/repair、
  fact pack、Revision system/user 均能生成 SHA。Prompt Program V1 应提取/复用这套逻辑形成
  产品 program manifest，而不是手写第二种摘要算法；实验 case-context snapshot 继续保留为
  Dataset 身份，不直接充当产品 program。
- 现阶段没有真实 API 延迟、并发或可用性数据，因此 NFR 不能编造 200ms/p95/99.9% 等生产目标。
  5P 只承诺有界输入、同步阻塞、单进程文件存储、失败安全和可测试性；p50/p95、吞吐、SLO、
  多 worker、一致性/恢复都必须以阶段 6/8 的真实消费者和测量再定。
- 当前 stale 搜索区分了历史证据与动态状态：5E exit review、RQ-039、旧 progress/findings 必须
  保留原文；需要更新的是 canonical、活动计划 Current Phase/Next Step、amendment 当前状态、
  capability matrix 尾部和 project decisions 的新增裁决。不能用全局替换抹掉暂停曾经发生过。
- 首轮状态同步后治理检查和 `git diff --check` 通过；stale 搜索剩余三处均是 5E 当时暂停的
  历史 progress/change-history/exit-matrix，不是当前状态冲突，因此保留。新设计/ADR 尚为
  untracked 文件，最终提交前必须用 `git status` 纳入，不能只看 `git diff --stat`。
- 5P entry 本地门禁通过：完整 `762 passed, 110 subtests passed`、两套 RAG 满足全部 1.0/
  0.0 阈值、governance/2 tests、compileall、secret/SDK boundary、Harness dry-run 和 diff check；
  本批外部调用为 0。Prompt fingerprint 与 file digest 的威胁模型已在设计中收窄，不能表述为
  形式化程序等价或抵御拥有本机写权限者对正文和全部元数据的联合篡改。
- 设计 SHA `49841ec44832875e65b17770557415113e67b1db` 的 Actions run `31985199623`
  completed/success；5P entry 设计、两份 ADR 和全部状态已获得 exact-SHA 公共证据。下一检查点
  只能是 5P-1 typed product/compiler，当前仍没有 Prompt Program/FastAPI 产品代码或外部 I/O。
- canonical 治理枚举只接受 `in_progress/paused/complete/blocked`；“ready”只能写在解释文本，不能
  成为机器状态。活动计划历史结构还包含不止一个 Next Step heading，治理读取第一节，因此每次
  checkpoint 切换必须搜索并统一全部同名动态节，不能只补尾部详细账本。

## 2026-08-17：5P-1 产品合同与编译器接缝审计

- 用户再次明确“继续”后，canonical 唯一授权为 `5P-1-product-contract-compiler`；恢复脚本无
  未同步上下文，治理预检通过，起始 HEAD/origin 均为 `a2c3ba7` 且工作树干净。
- 产品 DTO 只允许 Riot ID、count、queue、focus；Riot ID 的本地长度/控制字符约束只负责传输
  安全和资源有界，不冒充 Riot 账号规则的完整副本。
- typed recent endpoint 应直接从 Catalog 绑定 `recent-form-review` 当前版本，以
  `entrypoint:reviews.recent` 作为机器证据；不得调用自然语言 Router 或制造中文关键词请求。
- 当前 Runtime 已在执行时逐字段复核 Manifest budget/quality policy，但生产侧尚无同源 policy
  compiler；5P-1 将 Manifest 六个业务字段与服务器固定的 policy version/event budget/revision
  上限分层映射，客户端不能覆盖任一项。
- `SkillInputArtifactBinding.from_content()` 已提供 Harness 同源 JSON/text 编码与 SHA-256；新编译器
  应复用它，并继续让 `SkillExecutionBoundary` 发现内容、版本或 Catalog 漂移，不建立第二套摘要。
- 最小实现放入新的 `app.product` 边界；Application Service、Prompt Program、FastAPI、Riot/
  Provider I/O 和文件查询仍分别留在 5P-2 至 5P-5。
- 产品请求中的 Riot ID/count/queue 是上游 Summary 收集参数；compiler 位于 Summary/报告形成后，
  因此只有 focus 进入 `RecentFormReviewInput`。这不是丢字段：5P-3 Application Service 会消费
  前三者，5P-1 只负责把已形成的事实产物编译进 Runtime。
- 为避免“测试只碰巧等于当前 Manifest”，policy 测试会修改 Catalog 中的合法 budget/quality
  快照并验证 Runtime policy 同步变化，同时确认 policy version/event budget/max revisions 保持
  服务器固定；由此区分 Manifest-derived 与硬编码当前数值。

## 2026-08-17：5P-2 关键发现

- Prompt Program 不是一条 Prompt 文案，而是 ContextBuilder 信任/裁剪策略、Skill manifest 与
  instructions、knowledge.search 合同、Evaluation 1.1 schema/system/user/repair、fact-pack
  probe、Revision system/user/validator 的可执行组合身份。
- `PromptContextSnapshot` 适合做 component probe，但包含实验 case-context 身份；产品 Program
  必须只复用其中的 component fingerprint，不把案例快照或 Prompt 正文塞进产品 manifest。
- Pydantic `strict=True` 下 JSON array 不会自动转 immutable tuple，因此 Program 模型在 transport
  边界先把 list 规范化为 tuple，再对内保持 frozen/extra-forbid；这保留严格字段同时兼容 JSON。
- 组合根是产品启动边界：加载 Skill/Program Catalog 后立即 `verify_all()`，任何组件漂移在 Runtime
  或 Provider 构造前失败；Runtime 每次 identity resolve 仍复核 selected Skill/version，防止长期对象
  期间发生目录漂移。
- 旧 Runtime 测试并不代表产品 Program 已接入。为保持证据诚实，`AgentRuntimeV1` 的 resolver
  参数必须显式提供；旧测试传入命名清楚的 `LegacyRuntimeIdentityResolver`，产品根传入真正的
  `PromptProgramResolver`。
- `program_sha256` 绑定的是 manifest 元数据和组件摘要的规范 JSON；它能检测 manifest/组件摘要
  不一致，但不声称能抵御拥有本机写权限者同时改源码、manifest 和 digest 的联合篡改。

## 2026-08-17：5P-3 入口发现

- `scripts/build_player_summary.py` 已支持 client/ddragon 注入，但领域函数仍由 CLI 文件拥有；
  `scripts/generate_markdown_report.py` 的 renderer 也是纯业务逻辑却位于脚本。未来 HTTP 若直接导入
  两个脚本，会让 adapter 依赖 CLI 并复制异常/路径规则，因此应先提升到 `app.lol`。
- Application Service 不等于 Agent Runtime：前者组织一次产品用例的上游数据、确定性报告、
  compiler 和 Runtime 顺序；后者只管理已经验证的 Skill 执行、工具、Harness、Trace 与发布。
- run_id 由 5P-1 compiler 在 Summary 和 deterministic report 成功后生成，因此账号/上游/零比赛
  失败不能伪造一个 Runtime run；Runtime 一旦开始，失败才可携带安全 run_id/terminal reason。
- Summary 内部 `failed_matches`/`timeline_error` 目前可含本地 `str(error)`，但 Application result/
  error 绝不能透传这些字段；5P-3 只暴露 allowlisted code 和受控元数据。
- 5P-2 `RuntimeCompositionRoot` 证明 Program manifest/当前组件一致，却接受任意调用者提供的
  `RuntimeExecutionFactory`；这不足以单独证明执行路径实际采用 `SecureChatEvaluationAdapter`。
  首个产品消费者应提供 secure factory 默认值并测试实际 evaluator/reviser 类型。

## 2026-08-17：5P-3 本地实现发现

- Summary/确定性 Report 原逻辑可逐字节提升到 `app.lol`，CLI 只保留参数、真实依赖、文件和
  打印；短局排除、timeline unavailable 与旧报告字节均由直接测试固定，没有业务语义漂移。
- Application Service 的唯一正确顺序是 Summary → Schema/有效比赛门 → deterministic report →
  compiler/run_id → Runtime。这样账号、上游、坏 Schema 和零比赛失败都不会伪造 Runtime run。
- 上游异常可能携带 URL、Key、响应正文和本机路径；应用错误只保存固定 code、可空安全 run_id、
  allowlisted terminal reason 和 1-300 秒数字 Retry-After。畸形 match row 的 Python 异常也被
  额外红灯证明并收敛为 `service_configuration_invalid`。
- completed Runtime 结果仍需在应用边界交叉检查 run_id、publication、typed output status 与
  Trace reference；failed/不一致结果只形成 `review_runtime_failed`，不返回草稿或原始异常。
- secure product factory 真实构造 `SecureChatEvaluationAdapter`、`ChatCoachReviser` 与 revision
  validator；这补上 5P-2 Program identity 与实际执行 factory 的相邻缺口，不改写 5P-2 历史证据。
- 本地全量为 `830 passed, 110 subtests passed`；RAG/compileall/Harness/secret/dry-run/governance/
  diff 门禁通过。全部使用 fixture/Fake，Key/Riot/Provider/held-out I/O 为 0，不能评价模型质量。
- 实现提交 `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 已由 Actions run `31998739178`
  exact-SHA 公开验证成功；这些公共门禁同样无 Key/外部 I/O。5P-3 因而正式完成，5P-4
  receipt/query 仅成为下一检查点，尚未实现。

## 2026-08-17：5P-4 入口审计发现

- receipt、Trace、manifest 与 final Artifact 不是重复存储：receipt 是产品查询索引，Trace 是
  Runtime 黑匣子，manifest 是 Harness Artifact 账本，final Artifact 才是报告正文。
- `RuntimeRunResult` 的 completed 结果必有 Trace，failed 结果则允许 Trace 为 null；failed 也可能
  保留 Harness publication。因此 Query 必须分开校验 Runtime terminal 与 publication terminal，
  不能错误地要求 failed Runtime 的 overall terminal reason 等于 manifest 的发布 reason。
- Harness terminal transition 保存 publication reason，Trace 的 `PublicationDecidedSignal` 保存同一
  reason；Trace overall terminal reason在后置 Runtime failure 时可能是 `typed_output_build_failed`
  等 Runtime code。正确交叉关系是 receipt overall ↔ Trace overall、manifest publication ↔ Trace
  publication，而不是把两种 reason 混成一个字段。
- Runtime 可能在 Harness manifest 建立前因 Boundary/Context 失败，但仍形成失败 Trace；严格查询
  需要允许“failed + no publication + no report”的 manifest-missing 组合，同时拒绝 completed 缺
  Trace、rejected 有报告和任何有报告却没有 Trace 的暴露。
- Application Service 当前会在 `_project_result()` 遇到 failed Runtime 时立即抛安全错误；5P-4
  必须在该投影前增加显式 receipt writer，让类型化 failed 结果也留下查询凭证。原始异常、错误
  run_id 或 Program 启动漂移不能据猜测伪造 Runtime receipt。

## 2026-08-17：5P-5 开始审计发现

- `fastapi` 当前尚未安装；`httpx 0.28.1` 已在环境中存在，但 dev 依赖仍未声明，因此先以
  import 红灯冻结 API 合同，再增加显式依赖并验证兼容性。
- 薄 Adapter 的唯一业务依赖应是 `RecentReviewApplicationService` 与 `RunQueryService`；
  handler 不应导入 CLI、`RuntimeRunRequest`、Prompt、Provider、Harness 或 Skill Router。
- `RecentReviewApplicationService` 已将应用错误压缩为 allowlisted code/run_id/reason/retry-after；
  Adapter 只负责 HTTP 状态和受控 header，不重新解释上游异常。
- `RunQueryService` 已提供 body-free `RunView`、Markdown report 和 `run_not_found` /
  `report_not_available` / `run_integrity_failed`，因此 FastAPI 不应读取 receipt/Trace/Artifact
  文件或复制完整性逻辑。
- 5P-5 只能证明 HTTP 接线和本地安全合同；同步、文件型、无鉴权环境不能被称为公网生产部署。
- 红灯聚焦运行按预期在 `app.api` 导入期失败（`ModuleNotFoundError`）；这不是旧实现通过，
  而是新 Adapter 尚不存在的直接证据。系统解释器已有 FastAPI，但项目 `.venv` 尚未安装，
  因此依赖声明与虚拟环境安装仍是本轮实现步骤。
- Adapter 首轮聚焦收集暴露一个 Python 3.11 导入错误：`Protocol` 被误从 `collections.abc`
  导入；已改为 `typing.Protocol`，属于局部接线修复，不改变 HTTP 合同或边界。
- 第二轮聚焦暴露 FastAPI 路由注册错误：`Response | JSONResponse` 被错误推断为 Pydantic
  response model；报告端点已明确 `response_model=None`，保留 Markdown/JSONResponse 的
  HTTP 返回语义，不改变端点合同。
- 第三轮聚焦只剩一个测试断言错误：`RecentFormReviewOutput` 的既有文本合同会规范化并去掉
  报告末尾换行；测试已改为断言 HTTP JSON 中的规范化值，独立 Markdown 查询仍保留原始
  `text/markdown` 正文合同。
- 初版 no-I/O 测试禁止了全部 `os.getenv`，误伤 Pydantic 自身的插件环境读取；已收窄为只
  禁止 Riot/Zhipu/DeepSeek/OpenAI/Anthropic Key 变量，并继续禁止任何 requests HTTP 调用。
  这让测试证明产品秘密边界，而不是错误地要求第三方框架完全不读任何环境变量。
- 最终 HTTP Adapter 通过显式 Port 注入保持薄边界；OpenAPI 只含四个冻结路径，业务错误只
  映射 allowlisted code/run_id/terminal reason，429 的数值只进入受控 `Retry-After` header。
- 真正的 no-I/O 纵向测试证明不是“Fake Service 自己返回成功”：请求实际触发 typed compiler、
  verified Prompt Program、AgentRuntime、真实本地知识检索、Harness publication、Trace/Artifact/
  receipt 写入和 Query 交叉校验；Fake Provider 只替代外部模型网络边界。
- FastAPI 0.141.1 的 TestClient 当前给出 httpx 迁移 deprecation warning；`pip check` 和全部测试
  均通过。本轮不为了消除非失败警告盲目加入 `httpx2` 或压低依赖版本，留待上游稳定迁移时维护。

## 2026-08-17：5P-6 入口审计发现

- 5P-6 是证据审查与退出门，不是再实现一个产品端点；主要事实源为 ADR-0032/0033、5P 总设计、
  5P-1 至 5P-5 计划/源码/测试和 exact-SHA Actions。
- 退出结论必须分别回答功能链、层次边界、失败/脱敏、资源/no-I/O、公开证据与 deferred 能力；
  不能只列测试总数，也不能把 TestClient/Fake Provider 当成真实模型或公网部署。
- 路线明确 5P-6 通过后才轮到 5F 第三方 Runtime 采用实验；5F 不等于多模型分层，后者仍默认
  等待阶段 6 的真实产品成本/延迟证据。

## 2026-08-17：5P-6 本地退出审计发现

- 原设计十项功能要求都能映射到实际实现、直接负例测试与既有 exact-SHA Actions；HTTP 没有
  绕过 Application/Runtime/Query，Prompt identity 对应真实组件，查询也不会只相信 receipt。
- 当前没有必须留在 5P 修补的结构性产品代码缺口；继续加入真实 Provider、SQL、Memory、SSE、
  鉴权或前端会改变退出范围并让失败归因混乱。
- 本地 `close-with-deferred-boundaries` 只证明本地同步产品纵切面；真实 Riot、模型 Coach 质量、
  生产容量/成本和公网安全仍是 deferred/unknown，不能由 884 项回归反推。

## 2026-08-17：5P-6 exact-SHA 公共闭环

- 退出审查提交 `8c8acc6911209e645cfaee18bd40870f78d8704f` 已由 Actions run `32010604551`
  完成 exact-SHA 公共验证；pytest、两套 RAG、compileall、治理、SDK/tracked-data boundary
  与 Harness dry-run 全部通过。
- 5P-6 与整个 5P 正式关闭，最终裁决为 `close-with-deferred-boundaries`；这只关闭本地产品
  纵向切片的证据审查，不提升真实 Provider、生产部署或公网安全成熟度。
- canonical 只交接到 `5F-entry-design` 准备状态；Pi/Claude Agent SDK 仍需用户再次明确后，
  以同一产品切片做采用实验设计，不能在交接时自动接入。

## 2026-08-17：5P-4 本地实现发现

- `api_run_receipt.json` 使用同目录临时文件 + flush/fsync + atomic create-if-absent hard link；这在
  Windows 本地测试真实通过，并同时满足“读者不见半文件”和“第二个写者不能覆盖”。它仍是单机
  文件语义，不替代数据库事务或恶意本机写权限防护。
- `RunQueryService` 不能把 manifest 的 publication reason 和 Runtime overall terminal reason
  直接比较；当前实现改为 receipt ↔ Trace overall、manifest terminal transition ↔ Trace
  `PublicationDecidedSignal`，因此能正确表达 Harness 已发布后发生的 Runtime 后置失败。
- completed Runtime 强制有 Trace；早期 failed Runtime 可无 Trace/manifest，但只能返回 receipt
  可证明的最小视图，identity/time/Usage 为 null，报告永远不可用。failed Trace 在 Harness 建立前
  形成且 manifest 缺失也是合法的无报告查询场景。
- available report 必须在 Trace 与 manifest 中各恰好有一份同 identity 引用，并通过真实字节
  SHA-256、UTF-8 和非空检查；rejected、重复记录、终态不一致或任一字节篡改都 fail closed。
- Application Service 现在要求显式 `RunReceiptWriter`；类型化 completed/failed result 在外部投影
  前写 receipt，wrong run_id、未类型化 Runtime 异常和上游失败不写。真实 File Store 接缝与 Fake
  writer 顺序均有测试。
- 新增聚焦共 50 tests；5P/Runtime/Harness 相邻为 `179 passed, 12 subtests passed`，完整回归
  `860 passed, 110 subtests passed`。两套 RAG、compileall、Harness dry-run、SDK/secret/run-data、
  governance 和 diff 门禁通过；Key/Riot/Provider/held-out I/O 为 0。

## 2026-08-17：5F Pi-only 采用范围确认

- 用户已明确“继续”，确认把先前的 Pi/Claude Agent SDK 并列候选收缩为 `Pi-only` 采用实验；
  本轮不安装、不调用、不把 Pi 接入主 Runtime。
- 官方 Pi 资料显示其核心关注轻量 Agent Runtime、Tool Calling、消息/状态管理与多 Provider
  LLM 抽象，概念上比 Claude Code 风格的完整 Agent SDK 更适合回答“是否替换/吸收当前 AgentLoop”。
- 官方 Claude Agent SDK 提供 Claude Code 同源的内置工具、Hooks、Sessions、Subagents 和 MCP，
  若现在对照会同时改变 Runtime、模型厂商和工具体系，不能形成干净的 Runtime 归因；因此只保留
  为 ADR 中的书面排除项。
- Pi 的主要风险是官方核心为 TypeScript，而 RiftCoach 主仓库为 Python；5F 必须把跨语言/sidecar
  成本作为一等评测指标，不得直接采用未审计的 Python 移植版。

## 2026-08-17：5F-entry-design exact-SHA 公共闭环

- Pi-only 入口设计提交 `ce979752808271696b1dfe499317ead66de6aacb` 已由 Actions run
  `32013948784` 完成 exact-SHA 公共验证；治理、完整 pytest、两套 RAG、compileall、SDK/
  tracked-data boundary 和 Harness dry-run 全部通过。
- 5F-entry-design 正式完成，但没有安装 Pi、写 adapter、读取 Key 或调用 Provider；这只是采用
  实验入口设计的公共闭环，不是 Pi 采用结论。
- canonical 下一步为 `5F-1-pi-source-license-contract-audit`，等待用户明确继续；该步必须先审计
  官方 TypeScript 源码/包与许可证，再决定是否值得进行离线 adapter spike。

## 2026-08-17：5F-1 官方 Pi 身份与低层合同初审

- 用户再次明确“继续”，只授权 canonical 的 `5F-1-pi-source-license-contract-audit`；本轮仍不
  安装 Node/Pi、不写 adapter、不读取 Key、不调用真实 Provider。
- 旧入口材料中的 `https://github.com/badlogic/pi-mono` 当前会重定向到官方
  `https://github.com/earendil-works/pi`。审计入口先记录当时 `main`
  `c7c763f5c48736fa00cdcf0bcbfcae5cbc585e7c`，随后用 npm registry 的 `gitHead` 与 tag 复核，
  最终候选身份冻结为 `v0.84.2` / `914cf1472e715297caa30db4b9535d534a9eb718`，而不是漂移的 `main`。
- 冻结 release 的 `@earendil-works/pi-agent-core` 与 `@earendil-works/pi-ai` 均为 `0.84.2`；
  package 与仓库许可证为 MIT，Node engine 为 `>=22.19.0`。旧 `@mariozechner/*` 包名只能作为
  历史资料，不能写入新的实验合同。
- 低层 Agent Core 与当前采用问题相关：`AgentContext` 明确携带 system prompt/messages/tools；
  Tool 使用 TypeBox schema 并在执行前验证参数；事件覆盖 agent/turn/message/tool 生命周期；
  AssistantMessage 和 Tool result 均有 Usage 接缝；`AbortSignal` 贯穿 Provider、hook 和 Tool。
- Pi 的 Tool 列表可以作为 allowlist，未知 Tool 会转成 error result，`beforeToolCall` 还能 block；
  但默认 tool batch 为 parallel，RiftCoach 首个 spike 必须显式选择 sequential，避免重现既有
  parallel tool-call 语义差异。
- 暂未发现 Agent Core 自带 RiftCoach 等价的总 Provider/Tool 调用次数、总 Token/Context ceiling、
  单 run deadline 或质量发布门。`shouldStopAfterTurn` 与 `AbortSignal` 是可实现这些政策的接缝，
  不是已经存在的产品策略；预算、deadline、Trace 和 ReviewHarness 仍必须由 RiftCoach adapter/
  外层强制。
- 官方 README 明确 Pi 默认继承启动进程权限且没有内建 filesystem/process/network/credential
  权限系统。5F 不能引入 coding-agent 默认 tools/extensions；只允许低层 Agent Core + 一个显式
  `knowledge.search` adapter，并由父进程/IPC 白名单守住权限边界。
- Pi 默认 parallel 且按调用逐个准备/执行，不具备当前 RiftCoach 的“整批 Tool 数量/allowlist/
  duplicate 零副作用预检”；仅设 sequential 或 `beforeToolCall` 仍不完全等价，5F-2 必须在整个
  AssistantMessage 进入 Tool executor 前预检 ToolCall batch。
- Pi 的 `Agent.handleRunFailure()` 会用合成 `EMPTY_USAGE` 构造 error/aborted assistant message；
  这不能区分“未发请求”和“已发请求但 Usage 缺失”。5F-2 必须独立记录 attempt/response，并映射
  RiftCoach 的 complete/partial/unknown，而不能把合成零当成 complete zero。
- Pi Tool events 携带 raw arguments/result，不能原样进入 RiftCoach body-free Trace；事件只允许
  投影 tool/provider identity、ordinal、allowlisted error、Usage completeness 与 terminal。
- `pi-agent-core` 依赖 `pi-ai`，而 `pi-ai` 即使在 Scripted Provider 实验中也会带入 Anthropic、
  OpenAI、Google、AWS 等 SDK 依赖。5F-2 必须用 release tag、official-registry integrity、exact
  lockfile、`npm ci --ignore-scripts` 记录真实安装/冷启动成本；本机 npm 默认 registry 为
  `npmmirror`，不能把镜像地址冒充官方包身份。
- 本机 Node `v24.18.0` 的 `--permission` 可限制 write/child-process/worker/addon 等，但本机帮助
  没有 `--allow-net`；不能用较新 Node 文档反推当前进程已硬断网。它只能作为 defense-in-depth，
  no-I/O 还需依赖无 Key、Scripted StreamFn、不构造真实 Provider，并在需要硬隔离时使用 OS/容器。
  Node 官方也明确 Permission Model 不是抵御恶意代码的沙箱。
- 只读源码检索曾因 PowerShell 插值字符串中的 `$path:` 解析失败；已改用 `${path}`。第二次组合
  检索输出过大并被截断，因此后续改为按合同主题和精确行窗分批读取，不把截断输出当完整证据。
- 比较 release/main 文件摘要的首个 PowerShell pipeline 因 `foreach` 后直接管道出现空管道解析错误；
  改为先累计 `$out` 再输出。审计本地源码的组合行窗函数又因单区间数组被 PowerShell 展平而对
  `[Math]::Min` 传入错误类型；后续改用 `rg -C`/精确文件行窗，已取得所需合同证据。
- 首次准备提交时，Codex 会话权限只允许写入 C 盘参考工作区，Git 因无法在 D 盘活动仓库创建
  `.git/index.lock` 而停止；已确认没有残留 lock 或并发 Git 进程。用户恢复完整权限后再继续，
  没有绕过仓库权限或复制工作树。
- 权限恢复后的首次活动计划恢复把 `.active_plan` 的结尾换行直接拼入路径，导致三次只读
  `Get-Content` 找不到文件；已改为先对 pointer 使用 `.Trim()`，随后成功读取真实活动计划。

## 2026-08-17：5F-1 公共证据裁决

- 审计提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 与 Actions run `32016852979`
  exact-SHA 对齐且全部公共门禁成功；5F-1 的 source/license/contract 结论因此可正式关闭。
- 公共 CI 验证的是 RiftCoach 文档/既有回归没有漂移，不是 Pi adapter 已工作；Pi 仍未安装，真正
  protocol parity 必须由 5F-2 的离线 scripted cases 单独证明。

## 2026-08-17：5F-2 入口架构发现

- 产品内直接嵌入 Pi 或调用完整 Coding Agent 都会把 Runtime 对照污染为语言/Session/工具/Harness
  迁移；版本化 JSONL sidecar 是唯一能保持当前外层合同并量化跨语言成本的最小方案。
- Tool 参数和结果只允许作为本地瞬时 IPC 数据传输给 Python ToolRuntime/Pi 下一轮；它们不能进入
  safe event/result projection。最终 draft 正文与 body-free Trace 元数据必须继续区分。
- 父进程必须使用总 deadline 和不合作子进程 terminate/kill；只靠 Pi AbortSignal 或 Node
  Permission Model 不能证明进程或网络硬隔离。
- 5F-2 的成功是 protocol/control-flow evidence，不是 Pi 模型质量、Harness parity 或采用结论。
- 5F-2 启动状态首次治理检查失败，因为“唯一下一步”先写了实施计划路径，解析器将第一个反引号
  值当作 human-readable checkpoint；已改为先写 canonical `5F-2-offline-protocol-adapter-spike`，
  再引用计划路径，没有放宽治理规则。
- 当前 `AgentLoop` 已具备整批 Tool 数量/allowlist/duplicate 预检、逐轮 Context ceiling、总 deadline
  与顺序 ToolRuntime 执行；5F-2 不能另造更弱的安全规则，协议层必须保持这些可观察语义。
- 当前 CI 只设置 Python；5F-2 若跟踪 Node lockfile 和真实 sidecar tests，必须显式设置满足 Pi engine
  的 Node 24 并运行 `npm ci --ignore-scripts`，不能让开发机已安装的 `node_modules` 掩盖公共缺口。
- 只读参考测试时误猜 `tests/test_provider_protocol_experiment.py`，实际相关文件为
  `test_provider_adapter_protocol.py`、`test_deepseek_protocol_experiment.py` 和 CLI 测试；错误命令没有
  修改文件，后续使用 `rg --files tests | rg protocol` 获取真实路径。
- 现有 `RuntimeUsage` 把 `provider_responses_observed` 定义为具备可观察 Usage 的响应数：少于 attempt
  且大于零为 partial，零为 unknown；5F-2 因此把 scripted `None` Usage 视为未形成可计量 response，
  而不是把其 Token 记为零。
- Batch A 已证明协议对象能拒绝多余字段、未知 Tool、非法失败码、超长/多行/未知 JSONL frame，并
  能返回 draft 但禁止 event/result 保存 query 或 chunks；这还没有证明 Node/Pi 真实接线。
- Batch B official-registry lockfile v3 精确锁定 Agent Core/AI 0.84.2，integrity 与 5F-1 审计值一致；
  `npm ls --all` 通过。Agent Core 自身对 pi-ai/telemetry 使用 caret，但根 package 的两个直接依赖和
  整棵传递树已由 lockfile 固定。
- 首次 `npm ci --ignore-scripts` 安装 94 个包，耗时约 4844 ms，产生 11,355 个文件、62,364,713
  bytes；这说明跨语言依赖成本不可忽略，必须进入最终 adoption 评价。
- lockfile 标出 `@google/genai@1.52.0` 与 `protobufjs@7.6.5` 两个传递依赖有 install script；
  `--ignore-scripts` 已阻止执行。npm 同时报告 `node-domexception@1.0.0` deprecated，但安装成功；
  这些是供应链/维护成本证据，不等于当前漏洞结论。
- 安装后的官方声明确认低层 `Agent` 直接接收 `streamFn`，并支持 `toolExecution="sequential"`；
  因此无需 Pi Coding Agent/Harness 即可实现本实验。
- Batch C 红灯第一轮因测试误导入未导出的 `PiSpikeStatus` 类型别名而在 collection 阶段停止；已
  删除无用导入，第二轮红灯正确暴露尚未实现的 `PiSidecarController`。两次均无产品运行影响。

## 2026-08-17：5F-2 Batch C 首次 sidecar 诊断

- sidecar 的共同失败与 Permission Model 无关；在 `use_permission_model=True/False` 两种模式下，
  最小 direct-final case 都在第一帧事件处以 `invalid_event` fail closed。
- 根因是 Python controller 在 JSONL 解码后使用 `PiSafeEvent.model_validate(dict)`；严格 Pydantic
  合同要求 `TokenObservation` 已经是 Enum 实例，而 JSON 传来的 `"unknown"`/`"complete"` 是
  字符串。修复为 `model_validate_json` 只作用于 JSON→合同的边界，未放宽模型 strict 配置。
- 修复后 child `run.result` 又暴露同类嵌套问题：严格对象校验拒绝 `response_usages` 中的 JSON
  字典。controller 同样改用 `model_validate_json`，保持请求/结果模型本身 strict。
- Pi sidecar 原本把脚本化 `provider_aborted` 映射为 `failed`；这与 RiftCoach 的停止语义不一致。
  已将该 forced stop 映射为 `stopped`，并保留 `provider_error` 为 `failed`。
- 修复后的协议+sidecar 聚焦回归为 `24 passed`；这证明 JSONL/Agent/Tool/Usage 控制流已经进入
  可测试路径，不代表 ReviewHarness parity、真实 Provider 或模型质量。
- stdout EOF 与 stderr reader 是两个线程，原先只采样一个队列项会在 EOF 先到时漏掉异常 stderr；
  controller 现于进程退出后等待唯一的 bounded stderr payload，并把正文丢弃、只返回
  `unexpected_stderr`。本地 6 次新进程直出测试在去除无意义固定等待后为 399.75-453.15 ms，
  首次 408.54 ms、后五次中位数 413.71 ms；这是本机协议/进程开销，不是生产 p50/p95。
- 第二次 `npm ci --ignore-scripts` 为约 6063 ms；安装树仍为 94 packages、11,355 files、
  62,364,713 bytes，`npm ls --all` 成功。这些数值受机器/缓存影响，只作为跨语言成本量级。
- 与当前 Python AgentLoop 对照时发现：在最后一个允许迭代中返回 ToolCall，Python 会先
  `max_iterations` 停止且不执行 Tool；Pi sidecar 原先先执行 Tool 再于下一轮停止。adapter 已在整批
  preflight 前置同一判断，并新增成功 Tool round-trip 与最终迭代零副作用的显式 parity 测试。
- sidecar 原先只用成功 Tool 数量计算 `max_tool_calls`，失败 Tool 可能不占预算；现改用所有
  `toolExecutions` 数量，失败尝试同样占用预算。新增测试证明首个失败后第二个 batch 在 Python Tool
  I/O 前停止。
- Tool contract 预检原在 controller 的统一错误边界之外，schema drift 会抛异常而不是形成稳定结果；
  现已移入 fail-closed 边界，返回 body-free `tool_contract_mismatch`，Provider/Tool calls 均为 0。
## 2026-08-17：5F-3 Contract/Security/Harness 评测发现

- 现有 `SkillReviewExecutor` 的窄 draft preparer seam 足以让 Pi 成功文本降格为 `CoachDraft`，无需
  修改 ReviewHarness；实际纵向测试确认 final Artifact producer 仍只属于 Harness。
- 5F-2 public result 为安全起见不保存 Tool body，但 Harness 构造 `KnowledgeEvidence` 必须使用实际
  chunks。controller 因此新增单次进程内 `PiSidecarExecution.tool_records`；它与 body-free
  projection 逐项核对，不写入 result/event/Trace。
- RuntimeTrace 的 Usage 由 per-call Provider signals 推导，旧 Pi event 只有 aggregate completeness，
  不能重建 Trace。safe event 增加数字型 input/output 和 finish reason 后，成功 Trace 的 Recorder
  Usage 与 Pi RuntimeUsage 可以逐字段一致；missing Usage 仍显式 unknown/null，不能归零。
- Context parity 不成立：Python 使用 `DeterministicContextSizer` token-unit，sidecar 使用 Pi state 的
  JSON char length。现有 Compiler 先验门仍保留，但 Node guard 只能标记
  `approximate_char_guard`；复制 sizer 会新增跨语言漂移维护面。
- terminal parity 不完整：现有 Runtime Agent terminal 能表达 final/预算/timeout/provider_error，不能
  表达 provider_aborted/protocol_error/process_error 等 Pi 结果。严格 projector 对这些返回
  `unsupported_agent_terminal`，不近似映射。
- safe event 目前在 child 完成后批量投影到 observer；顺序和 aggregate Trace 合法，但逐事件时间不是
  原始发生时间，也没有 5E `stream()` 的实时交付语义。改成在线 bridge 将重新引入 fail-fast、背压、
  cancel 和双终态问题。
- 评测专用 adapter 还必须重建完整 Assistant/Tool transcript、拒绝失败知识 Tool、坏 citation 和
  incomplete Usage；这进一步说明 Pi 不是替换一个 Python loop 类即可。
- 45 项 Pi 聚焦、196 项相邻和完整 `929 passed, 1 warning, 110 subtests passed` 已本地通过；
  Scripted/Fake/本地 RAG 是全部运行输入，外部 Provider/Riot/Key/held-out I/O 为 0。
- 本地裁决为 `harness-compatible-but-runtime-gate-failed`：5F-4 无信息增益且不准入；需待公共 CI
  后由 5F-5 决定保留设计思想还是删除隔离 adapter。

## 2026-08-17：5F-5 最终采用与资产生命周期发现

- `adopt` 已被 5F-3 的三项强制 Runtime gap 排除；真实模型调用不会改变 Context 单位、terminal
  vocabulary 或 live event bridge，因此 5F-4 不应补做。
- “产品是否采用 Pi”与“是否保留可执行负面实验”不是同一个问题。Pi 进入产品会增加 Node/IPC/部署
  和语义复制成本；保留冻结测试资产则能让拒绝结论持续可验证。
- 当前 `node_modules` 不跟踪且不进生产，exact lock + `npm ci --ignore-scripts` 能控制一部分研究
  供应链风险；但 94 个包仍不是零成本，必须有归档触发条件。
- 把 Pi 测试移出 CI 会降低持续复现性；当前约数秒安装成本尚可接受，所以本地裁决暂保默认 CI。
  若出现高危实际依赖、Node 不兼容、持续不稳定或显著成本，再用新 ADR 分离/归档，不能让产品迁就。
- 最准确的裁决名是 `partial-adopt-evaluation-assets-only`：产品拒绝 Pi，冻结保留实验和采用门方法；
  它不表示双 Runtime、用户可选 Runtime、真实模型质量或生产部署。

## 2026-08-17：6A FastAPI/SQL 入口初审发现

- 5P 的 FastAPI 是显式注入 ports 的同步薄 Adapter，没有 module-level production app/lifespan、SQL、
  worker、鉴权或公网配置；这使 import/OpenAPI no-I/O 很安全，但不能直接部署完整产品。
- `RecentReviewApplicationService` 已提供可复用的 Summary → report → compiler → Runtime → receipt
  顺序；6A 不应把业务重新搬进 handler，而应在它外面增加持久 task/application boundary。
- 当前 file receipt 在 Trace 与 receipt 之间存在 crash gap，也不支持多 worker 原子 claim；SQL 的
  首要用途是任务身份、ownership、状态和事务，不是保存全部 Prompt/报告正文。
- EchoMind 使用 lifespan 初始化全局组件、Redis 工作记忆和 Chroma 情景/画像；没有 SQL task model，
  `/chat` 内 `asyncio.create_task(update_profile)` 也没有 durable claim/recovery。其组件生命周期思想
  可参考，但宽泛 CORS、全局可变对象和 Memory 存储方案不能原样迁移。
- 6A 需要先确认 PostgreSQL/SQLite 的生产与测试定位；这一选择会影响事务、并发 claim、迁移、CI 和
  部署成本，不能在实现中默默决定。

## 2026-08-17：6A 数据库基线确认

- 用户选择方案 A：PostgreSQL 是唯一生产语义基线，ORM/映射使用 SQLAlchemy 2，迁移使用 Alembic。
- 普通领域和 Application 逻辑仍可通过 Fake/单元测试快速验证；但事务边界、Alembic migration、
  唯一约束/幂等和多 worker 并发 claim 必须在真实 PostgreSQL Docker/CI 中验收。
- SQLite 不进入生产路径，也不作为上述 PostgreSQL 语义的替代绿灯；这避免测试通过但部署后因锁、
  隔离级别或 SQL 方言差异失效。
- 该选择只冻结数据库目标与验证标准，尚未决定同步执行、进程内后台任务或独立 polling worker。

## 2026-08-17：6A 任务执行方案 3 获确认

- 用户选择同仓库、同部署的独立 PostgreSQL polling worker：FastAPI 只验证请求、持久化 queued task
  并返回 202；Worker 使用数据库事务原子 claim，再调用既有 Application Service。
- 该方案是模块化单体中的两个进程角色，不是拆微服务；PostgreSQL task table 同时承担 durable queue
  与查询状态源，不增加 Redis、Celery、Kafka 或 RabbitMQ。
- `FOR UPDATE SKIP LOCKED` 的意义是让多个 Worker 跳过已被其他事务锁定的 task，从而避免双重执行；
  这项语义必须由真实 PostgreSQL 并发测试证明。
- 6A 不提前承诺完整 lease、自动重试、cancel/resume 或迟到结果隔离；这些复杂恢复能力仍需后续单独
  需求和采用门。当前只进入完整设计的逐节确认，尚未写产品实现。

## 2026-08-17：6A 架构与数据流章节获确认

- 用户确认模块化单体边界：API 和 Worker 是同一代码库/同一产品部署中的不同进程角色，不形成
  独立业务微服务。
- API 事务只创建任务；Worker claim 事务只改变 ownership/status；Agent/Tool/RAG/Provider/Harness
  长操作在事务外运行；最终投影再用短事务回写，禁止长时间持有数据库行锁。
- PostgreSQL 保存小型任务控制数据；现有 Artifact/Trace 继续保存报告、评测和运行正文。查询路径
  必须通过 run_id/reference 交叉验证两层，而不是信任任一孤立记录。
- 异步任务引入独立 `task_id`；为避免 Runtime Artifact 在中断后失去 SQL 归属，下一设计节需裁决
  是否在创建任务时一并预留稳定 `run_id`，而不是延续当前编译中后置生成。

## 2026-08-17：6A task schema 与状态机章节获确认

- 任务表固定采用 `task_id`（排队任务）与 `run_id`（Runtime/Artifact 执行）双身份；二者均服务器
  生成，`run_id` 在入队时预留并传入现有 compiler/Application Service。
- V1 任务状态为 `queued → running → succeeded|failed`；终态不可逆，不在 6A 添加自动重试、取消、
  恢复或 `running → queued`。中断用安全的 `failed/worker_interrupted` 终态表达。
- 任务控制表需要 owner、类型/版本、规范化输入与指纹、幂等 Key、Worker ownership、时间戳、安全
  terminal reason、publication projection 和 Artifact 引用；不保存 Prompt、原始 Provider 响应、
  完整报告或异常正文。
- `owner_id` 是可信上下文字段，不由用户正文直接指定；本地测试可用固定 owner，但不能把它宣称为
  已完成的公网鉴权。

## 2026-08-17：6A hard-crash 自动判死风险

- 用户确认了 SQL/Artifact 分工、创建/claim/终态短事务、幂等、ownership 与读取时交叉校验核心。
- 进一步失败复核发现上一节的“Worker 启动后，无 receipt 的 running task 自动标记 interrupted”在
  多 Worker 下不安全：新 Worker 不能仅凭启动事件证明旧 owner Worker 已死亡。
- receipt 已存在且 identity/SHA 完整时，reconciler 可以安全补齐 succeeded，因为有不可变终态证据；
  无 receipt 时若没有 lease/heartbeat、进程注册或运维确认，只能知道“结果未知”，不能自动判死。
- 当前需显式比较保守人工恢复、6A 提前引入 lease/heartbeat、部署期限制单 Worker 三种方案；该发现
  不推翻 PostgreSQL polling worker，只约束 hard-crash 自动恢复声明。

## 2026-08-17：6A hard-crash 方案 A 获确认

- 用户选择保守人工恢复：只有匹配 immutable receipt/identity/SHA 的确定终态证据才允许自动补齐
  succeeded；正常 shutdown 可由 owner Worker 条件更新为 `failed/worker_interrupted`。
- 无 receipt 的硬崩溃任务保持 running，并投影 `recovery_required` 运维条件；受限管理命令在人工
  确认 owner Worker 已死后，以 status/worker_id 条件更新为 failed。
- V1 不自动重跑，不新增 lease、heartbeat、fencing token 或迟到结果隔离；这些仍属于阶段 8。
- 该方案保持多 Worker claim 安全和真实限制可见，代价是极少数硬崩溃任务需要人工介入。

## 2026-08-17：6A 失败语义与 HTTP 投影章节获确认

- POST `/reviews/recent` 的 202 只表示任务已可靠持久化，不代表报告完成；task 查询对 queued/running/
  succeeded/failed 均返回资源状态，异步执行失败不 retroactively 改写原 POST。
- `task_status=succeeded` 表示 Runtime/Harness 形成合法可信终态；`publication_status` 仍可为 published、
  degraded 或 rejected。系统执行失败和质量门拒绝发布必须分开。
- validation、idempotency conflict、database unavailable、not-owned/not-found、report unavailable 与
  Artifact integrity failure 使用不同 allowlisted HTTP/错误语义，且不泄露 worker/异常/Provider 正文。
- owner 越权和不存在统一返回 404；hard-crash recovery_required 只进入管理投影，普通响应不暴露
  worker_id。

## 2026-08-17：6A 作品集规模 NFR 获确认

- 初始产品部署目标为单服务器上的 API、Worker、PostgreSQL 组合；默认每 Worker 一次执行一个任务，
  通过增加 Worker 进程扩展，但不承诺微服务或高可用。
- 温热 DB 下创建/查询服务端 p95 目标 `<300ms`；容量可用时 queued→running p95 `<2s`。这些是后续
  必须测量的目标，不是当前已有性能证据，且不包含 Agent/Riot/Provider 执行时长。
- 背压默认每 owner 3 个、全局 50 个非终态 task，可配置；空闲 polling 使用退避+jitter，避免惊群。
- liveness 只表明进程活着；readiness 必须核对 PostgreSQL 连接和 Alembic schema head。当前单 DB/
  单主机是明确单点，不写 99.9%、跨机容灾或 Artifact 自动备份承诺。

## 2026-08-17：6A 安全与数据生命周期章节获确认

- `owner_id` 必须来自服务器可信 `ActorContext`，所有 task/run/report 查询 owner-scoped；不存在与
  越权统一 404。固定 `local-owner` 只允许开发/测试，不冒充公网鉴权。
- CORS 默认关闭，生产禁止 wildcard+credentials；SQLAlchemy 参数化查询；Key/DB password 只来自
  Secret/env；日志 body-free，不记录 Riot ID、Prompt、报告、异常栈或 Provider 原响应。
- 公开部署前真实 Auth、HTTPS、限流和安全响应头是硬门；6A 设计这些接口/边界但不宣称已实现。
- 默认保留策略为 Riot 原始缓存 7 天、terminal task/run/Artifact/Trace 90 天、运维日志 30 天；
  terminal owner delete 使内容立即不可访问并清理正文，active delete 不冒充 cancel。
- 长期 Memory 不在 6A 创建；后续只保存用户确认的画像/目标/进度，不永久化全部原始对局或模型猜测。

## 2026-08-17：6A 分层测试矩阵获确认

- 纯逻辑/Fake 测状态、指纹、owner 与错误；真实 PostgreSQL 测 SQLAlchemy/Alembic、约束、事务和
  `FOR UPDATE SKIP LOCKED`；SQLite 不得替代这些语义。
- API 层用真库+Fake Application，Worker 层用真库+Fake Application/Artifact；离线纵向再复用现有
  Application、真实本地 RAG、Fake Provider、Runtime/Harness/Artifact，外部网络为 0。
- hard-crash 测试必须覆盖匹配 receipt 自动补齐、无 receipt 不自动重跑、人工 recovery CAS 和旧
  Worker 终态拒绝；并发测试使用 barrier/独立 Session，不靠脆弱 sleep 猜时序。
- 安全/生命周期和性能各有门禁；CI 使用 PostgreSQL service container，migration 和 concurrent claim
  为阻塞项，Fake Provider 结果不推导模型质量。

## 2026-08-17：6A 原子顺序与正式 entry-design 资产获确认

- 用户确认 6A-1 PostgreSQL Foundation、6A-2 Task Contract/Repository、6A-3 Atomic Claim/Worker、
  6A-4 Application/Artifact、6A-5 Async FastAPI、6A-6 Security/Lifecycle/NFR、6A-7 Packaging/Exit。
- ADR-0038 接受同步 SQLAlchemy 2 + Alembic + psycopg、PostgreSQL-only 生产语义、polling worker、
  conservative recovery 和阶段 8 deferred。同步 ORM 与当前同步 Runtime/Worker 一致，未来只有实测
  DB bottleneck 才重开 async ORM。
- 正式 design 汇总所有逐节确认；implementation plan 给出每批 exact files、TDD、门禁和明确排除项。
- 当前仍是本地文档/治理状态，未安装依赖、创建 migration、启动 PostgreSQL 或写产品代码；公共 CI
  成功前不能关闭 entry design。

## 2026-08-17：6A-1 实施入口环境发现

- 用户以“开始”明确授权 RQ-053；授权仅覆盖 PostgreSQL Foundation，不覆盖 Repository/claim/Worker/API。
- 仓库解释器为 `.venv\\Scripts\\python.exe`（Python 3.11.9）；桌面默认 Python 不作为门禁入口。
- 本机没有 `docker` 命令，当前不能提供本地真实 PostgreSQL migration 证据，也不在本批擅自安装
  Docker Desktop。迁移测试本地必须以明确原因 skip，GitHub Actions PostgreSQL service 必须作为阻塞门。
- `create_engine()` 是惰性的，6A-1 可在不连接数据库时测试 URL 方言、连接池配置、Engine 与 Session
  factory；Alembic 必须引用应用 `Base.metadata`，PostgreSQL schema 使用 UUID/JSONB/带时区时间。
- psycopg 3 的安装包名是 `psycopg`；开发/CI 基线采用自包含的 `psycopg[binary]`，SQLite 不进入依赖或
  PostgreSQL 关键语义测试。

## 2026-08-17：6A-1 本地实现发现

- 第一轮 editable install 因终端遗留的不可用 `127.0.0.1:7890` 代理无法取得 build dependency；只在
  pip 子进程清除代理后依赖成功安装。随后 `--no-build-isolation` 暴露 `.venv` 缺 `wheel`，安装构建工具
  后 editable project 成功重装。产品代码与系统代理配置均未因两次失败而改变。
- 实际解析版本为 SQLAlchemy 2.0.52、Alembic 1.19.1、psycopg/psycopg-binary 3.3.4，均落在冻结范围。
- 首次 Alembic offline SQL 编译发现 migration 给 CHECK 传完整名时又被 metadata naming convention
  加前缀，形成双 `ck_review_tasks_`。改为语义后缀后，SQL 生成冻结的单前缀名称；测试合同未放宽。
- 本地可证明配置 fail-closed、URL 错误不泄密、Engine/Session 构造无 I/O、ORM metadata 与部署/CI
  配置；不能证明 migration/JSONB/timestamptz/CHECK 真库执行，三个测试因此明确 skip。
- 完整回归为 `948 passed, 3 skipped, 1 warning, 110 subtests passed`；两套 RAG 指标均达到冻结阈值，
  compileall、Harness dry-run、governance、Secret/run-data 与 SDK boundary 通过。6A-1 必须等待 public
  PostgreSQL service job 后才能关闭。

## 2026-08-17：6A-1 真实 PostgreSQL 公共证据

- 实现提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 的 Actions run `32043214500` 已
  completed/success；原 `pytest` 与新增 `postgres-migrations` 两个独立 job 均成功。
- 真库 job 使用 PostgreSQL 17 service，执行 Alembic upgrade/downgrade/upgrade、三个 migration/
  constraint round-trip 测试和 `alembic check`，因此补齐本地无 Docker 的三个 skip。
- 该证据只证明 Foundation/schema，不证明 Repository transaction、idempotent create/query、claim、
  Worker 或异步 API；这些仍按 6A-2 及后续批次逐项实施。

## 2026-08-18：6A-2 真实 PostgreSQL 公共证据

- 实现提交 `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 的 Actions run `32046532695` 已
  completed/success；`pytest` 与 `postgres-migrations` 两个 job 均成功。
- PostgreSQL job 真实通过 5 项 Repository 测试：replay 原始 task/run identity、冲突/owner 隔离、
  active capacity 与 terminal 排除、PK rollback、以及两个并发同 key 调用只产生一行并正确 replay。
- 这证明 6A-2 的 Repository 语义，不证明 `FOR UPDATE SKIP LOCKED` claim、Worker loop、Artifact/Runtime
  执行、HTTP 202 或恢复能力；这些交接给 6A-3 及后续批次。

## 2026-08-18：6A-2 入口审计发现

- 用户以“继续”授权 RQ-054；范围只到 task domain/service 与 PostgreSQL create/query Repository。
- 已确认 `RecentReviewProductRequest` 是严格、冻结、已规范化的客户请求合同；6A-2 fingerprint 应直接对其
  JSON-mode canonical projection 加 task kind/schema identity，不重新实现 Riot ID 规范化。
- Service 必须拥有 idempotency/capacity 业务语义，Repository 必须在一个数据库 transaction 中原子执行
  replay/conflict/capacity/create；把 count 与 insert 拆成两个公开调用会留下并发竞态。
- 6A-1 migration test 中“downgrade and upgrade”函数只执行到 downgrade，而后一个类型/constraint test
  末尾存在职责错位的额外 upgrade。Workflow 已独立证明可逆 migration，结论不受影响；6A-2 会以最小
  测试修正让每个函数名与证据一致。

## 2026-08-18：6A-2 本地实现发现

- 纯逻辑合同先红后绿：task models、严格四态/时间/发布投影、body-free view、capacity policy、
  canonical fingerprint、Fake Repository service 共 `29 passed`。
- `PostgresTaskRepository` 采用固定 transaction-scoped advisory lock 串行化短 create transaction；先
  replay/conflict，再 owner/global active count，最后插入并在 commit 后返回。这样不把 count 与 insert
  拆成两个可竞态的 Service 调用，也不让 Agent/Provider 执行持有 DB 锁。
- Repository 查询始终带 owner 条件；数据库/完整性错误只转换为 allowlisted safe code，Service 不传播
  SQL、URL、约束正文或异常对象。
- 真库测试覆盖 replay 原始 task/run identity、不同 owner 隔离、容量与 terminal 计数、PK rollback 和
  同 key 并发单行语义；本机无 PostgreSQL 时 5 项明确 skip，必须由 CI 验证。
- 为保持 Alembic 配置层轻量，`PostgresTaskRepository` 不从 `app.persistence` 聚合导出，只通过显式
  `app.persistence.task_repository` 使用；避免 migration import 牵连 product/task service。
- 本轮两次并行门编排的一行 JavaScript/PowerShell 引号错误只导致工具命令 syntax error，没有执行门或
  修改文件；随后拆分命令重新运行，RAG/compileall/governance/YAML/Harness/安全门均获得真实结果。

## 2026-08-18：6A-3 本地实现发现

- 既有 `review_tasks` migration 已包含 `worker_id`、`claimed_at`、终态字段和 claim index；本批没有
  修改已公开 migration，避免产生无必要的 schema drift。
- 新增 `TaskTerminal` 作为 Worker→Repository 的最小成功终态合同；它只允许安全 reason、合法
  publication status 和 report projection，拒绝 `rejected + report_available=true`。Artifact/Trace
  references 仍留给 6A-4，避免本批提前模拟内容数据面。
- `claim_next()` 在一个 Session transaction 内完成 deterministic `SELECT ... FOR UPDATE SKIP LOCKED`、
  ownership 写入和 commit；返回 `ReviewTask` 后 Session 已结束。`succeed()`/`fail()` 使用同一
  `task_id + running + worker_id` CAS 条件，更新行数不是 1 时不改变状态。
- Worker 的 control loop 与真正的产品 Executor 分开：纯 Fake Executor 测成功、异常、安全失败、
  ownership lost、idle backoff、成功后 backoff reset 和 graceful drain。Executor 异常不会自动重试；
  Repository 基础设施异常会以 allowlisted `ReviewWorkerError` 停止 loop。
- 真实 PostgreSQL 测试使用独立 Session、barrier、有限 future timeout；额外锁住第一 queued row，
  确定性验证另一 Worker 会跳过它领取第二行，而不是依赖长 sleep 猜时序。由于本机无 Docker，7 项
  真库测试必须由 PostgreSQL 17 CI 补齐。
- 6A-3 收尾时 Worker CLI 故意 fail-closed：当时 6A-4 尚未提供真实 Application/Artifact Executor，
  直接启动会返回 `review_worker_executor_not_configured`，不会误领 queued task。这不是生产 Worker
  完成声明；6A-4 后的最新边界见本文件后续发现。
- 人工差异审查发现首版补丁曾把 helper 插入 `_record_to_task()` 中间；语法/纯 Fake 门仍会通过，但真库
  row mapping 会返回 `None`。修正函数边界后新增无需数据库的 mapping 回归，使这类结构错误不再只能
  等公共 CI 暴露。
- terminal CAS 使用 PostgreSQL `GREATEST(now(), claimed_at)`，即使 Worker 时钟暂时领先数据库，也
  保证 `finished_at/updated_at >= claimed_at`；真库测试固定该 timestamp invariant。

## 2026-08-18：6A-3 exact-SHA 公共证据

- 提交 `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 的 Actions run `32097561436` 已完成；`pytest` 和
  `postgres-migrations` 均成功，真实 PostgreSQL 17 补齐本机 7 个 skip。该证据支持 6A-3 claim、
  Worker ownership/CAS、退避控制和 graceful loop 的关闭，不外推为 Application/Artifact、HTTP 或
  hard-crash 自动恢复已完成。
- 公共 CI 没有读取 `.env`、调用 Riot/Provider 或执行真实 Agent；Fake Executor 仍只证明 Worker
  控制流，不能证明模型质量。

## 2026-08-18：6A-4 本地实现发现

- 5P compiler 原先总生成新 run ID；6A-4 增加 keyword-only trusted run_id，同时保留旧同步调用的默认
  factory。显式值非法时不能回退生成，避免 SQL task 与 Runtime/Artifact 分裂。
- Application 原先忽略 receipt writer 的返回值，且 completed Runtime 会先写 receipt、后验证 typed
  ApplicationResult。差异审查确认后改为 completed 先验证合法投影再写 receipt；typed failed Runtime 仍先
  写 failed receipt 供审计，但 verifier 永远不会把 failed receipt 对账为 success。
- receipt reference 是对 `api_run_receipt.json` 精确 bytes 的 SHA-256，而不是 receipt JSON 字段的摘要；
  verifier 在完整 query 后再次复读同一 receipt/reference，阻断验证期间字节替换的 TOCTOU 假证据。
- SQL 成功投影现在保存严格 Trace/receipt/final Artifact 模型；Repository CAS 额外匹配 run_id。Artifact
  本身没有 run_id 字段，但它必须来自同 run Trace，RunQueryService 已交叉验证 Trace/manifest/path/SHA。
- hard crash 没有 lease/heartbeat，故 `recovery_required` 只是运维投影，不是第五种 task 状态。missing、
  invalid 或 failed receipt 均不自动判死/重跑；只有 completed publication receipt 可自动 success。
- 6A-4 已提供真实 `RecentReviewTaskExecutor` 组合边界；`scripts/run_review_worker.py` 仍故意 fail-closed，
  因环境/Provider/Riot/DB 的 production-like composition 与进程 lifecycle 属于 6A-5，而不是让本批脚本
  import 时读取 Key 或误领任务。
- 新真库测试共 5 项：完整 receipt reconciliation、无 receipt 保持 running、人工恢复阻断迟到 Worker、
  无证据不变更，以及 PostgreSQL + Application + local RAG + Fake Provider + Runtime/Harness/Artifact 纵向。
  本机明确 skip，GitHub PostgreSQL 17 job 是阻塞证据。

## 2026-08-18：6A-4 exact-SHA 公共证据

- 提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 的 Actions run `32102522662` 已完成；`pytest` 与
  `postgres-migrations` 均 completed/success。公开完整 pytest 为 `1033 passed, 20 skipped, 1 warning,
  110 subtests passed`。
- PostgreSQL 17 job 明确执行 6 个数据库测试文件并得到 `40 passed`，其中新增
  `tests/test_task_reconciliation_postgres.py` 与 `tests/test_task_product_vertical_postgres.py` 的 5 项
  测试已在真实 PostgreSQL 中执行，不再是本机 skip。migration upgrade/downgrade/upgrade 与 metadata
  check 同样通过。
- 因此 6A-4 的 receipt-proven success、保守 recovery-required、worker-confirmed-dead CAS、迟到 Worker
  拒绝和 SQL + Application/Runtime/Harness/Artifact 纵向接线获得公共真库证据。CI 没有读取 `.env`/Key，
  没有 Riot/Provider I/O；Fake Provider 仍只代表离线控制流，不代表模型质量。
- 6A-4 正式关闭；唯一交接为 `6A-5-async-fastapi-composition` 准备状态。6A-5 的异步 HTTP、ActorContext、
  composition/lifespan 与 health 尚未开始，不能由本轮证据提前声称完成。

## 2026-08-18：6A-5 Async FastAPI & Composition 本地发现

- 产品“异步”由 durable task 边界实现，不要求 async ORM：POST 只做同步 SQLAlchemy 短事务并返回 202，
  长 Agent 执行属于独立 Worker。当前没有同步 DB 成为 p95 瓶颈的 Bad Case，不引入 async Session。
- FastAPI 工厂内部路由若同时使用 postponed annotations 与指向局部 dependency 的 `Annotated`，当前
  FastAPI/Pydantic 组合会产生未解析 ForwardRef 并把请求误投影为 422；改用默认值式 `Depends`/`Header`
  后 OpenAPI 与依赖解析稳定。这是框架接缝问题，不是业务异步语义问题。
- lifespan 的 setup exception 必须在 yield 前收敛；不能用同一个 try/except 包住 yield，否则应用运行期
  异常可能被误当 setup failure 并导致 asynccontextmanager 二次 yield。当前实现把 setup 与运行/cleanup
  分开，Engine 在所有已创建路径最终 dispose。
- SQL task 是 HTTP ownership/状态事实源，Artifact/Trace 仍是 run 内容事实源：queued/running 不访问文件；
  succeeded 后文件缺失不降格成 404，而是 `run_integrity_failed` 500，避免掩盖跨存储不一致。
- production 缺 Auth Provider 采用“进程活着但产品未就绪”的 fail-closed 语义；local/test 固定 owner 必须
  显式 profile + owner 配置，不能由 JSON 或任意 header 注入。
- 6A-4 findings 曾把 environment-backed DB/Riot/Provider composition 笼统归到 6A-5；与用户确认的
  6A-5 正式文件/HTTP目标及 6A-7 `API+Worker+PostgreSQL` packaging 对照后，当前裁决为：6A-5 关闭 API
  composition/lifespan，真实外部 Worker 启动组合留 6A-7 并保持 CLI fail-closed。该限制必须在 6A-5
  退出和 6A-7 checklist 中显式验证，不能静默遗忘。
- 本地 API 聚焦 `38 passed, 1 skipped`；完整 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`。
  新增 PostgreSQL API 测试只在本机 skip，必须由 exact-SHA public PostgreSQL job 补齐。

## 2026-08-18：6A-5 exact-SHA 公共证据

- Actions `32106378542` 对提交 `2492951c20dd6ca897d957d03752b6a2585ce469` completed/success；普通
  pytest 与真实 PostgreSQL 两个阻塞 job 均成功。
- PostgreSQL job 日志明确执行 `tests/test_async_task_api_postgres.py`，总计 `41 passed`；因此 API
  create/replay、owner 404、queued run/report 409 和 Alembic readiness 不再只是 Fake/本机 skip 证据。
- 公共完整 pytest 与本地一致为 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`；RAG、编译、
  Harness、安全/治理和 migration metadata 也成功，外部 Riot/Provider I/O 为 0。
- 6A-5 可以关闭，但 Worker CLI 的 fail-closed packaging 限制继续有效；下一检查点只是 6A-6 准备状态。

## 2026-08-18：6A-6 授权恢复核对

- canonical 状态在本轮开始时仍停在 `6A-6-security-lifecycle-nfr`，旧 `pause_reason` 是等待用户确认；
  用户最新“继续下一步”满足进入该精确子阶段的授权，不允许据此跳到 6A-7。
- 6A-6 的冻结目标来自 `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-implementation.md`
  与 6A design：CORS、日志/Secret 脱敏、背压、retention/delete、结构化 metrics 和 benchmark。
  正式 Auth/HTTPS、Memory、SSE、前端、lease/reclaim/cancel/resume 与真实外部 I/O 明确排除。
- 关键安全语义：terminal delete 必须先隐藏用户可见资源再清理跨存储数据；清理失败只能留下安全补偿
  状态，不能使资源重新可见；active task delete 不是 cancel，必须返回 conflict。
- 生命周期默认值为 Riot 原始 cache 7 天、terminal task/run/Artifact/Trace 90 天、安全运维日志 30 天；
  retention 测试要用 injected clock，避免等待真实时间并避免把系统时钟漂移当成逻辑证据。
- 性能目标是作品集级基线而非 SLA：warm-DB create/query server p95 `<300ms`、容量可用 claim delay
  p95 `<2s`；必须记录样本数和运行环境，不能把 Fake Provider 或 CI 抖动解释成模型质量。

## 2026-08-18：6A-6 本地实现发现

- CORS middleware 必须在 `create_app()` 组合时安装，而 DB/Session/Repository 仍只能在 lifespan 创建；
  因此 composition 只提前解析无 I/O 的 API 安全配置，并用绑定式 deletion proxy 跨 lifespan 传递真实服务。
- 删除的安全顺序不是“先删文件再删 SQL”：PostgreSQL `delete_terminal()` 在 owner-scoped 短事务中
  锁行并只删除 terminal row；事务提交后才清理 run 目录。清理失败写入只包含 run_id/时间/重试标志的
  内部补偿 marker，SQL 已隐藏所以 marker 不会让用户重新看到内容。
- `TaskObservability` 对 event metadata 做字段和安全值双重 allowlist；即使调用者把 Prompt、报告、
  URL 或 Secret 作为未知字段传入，也会被丢弃，不把异常字符串交给 logger。
- 性能 percentile 采用确定性的 nearest-rank 并返回 `sample_count`/`target_name`；测试只把数据库
  create/query 与 claim control-plane latency 纳入目标，不把 Agent/Provider 时长混入 p95。
- API capacity 配置沿用现有 Repository advisory-lock 语义，新增环境变量只改变 owner/global 上限，
  不改变幂等 replay 或 terminal 不占容量规则。
- 首个 exact-SHA run `32137687527` 已证明全部测试与真实 PostgreSQL 语义通过，但成功日志只显示
  `51 passed`，没有记录 actual p95/sample/environment；且最初 claim 样本只测单次 SQL 调用耗时，
  不足以完整表达 queued→running 等待。6A-6 因此保持 in progress，先增加 warm-up、累计队列等待样本
  和安全 CI 输出，再以新 exact-SHA 证据关闭。
- 新 run `32138025724` 已补齐上述证据：8 样本 warm create/query p95 `6.220ms`，8 样本
  queued→claim p95 `23.359ms`，环境与目标均记录在 PostgreSQL job；6A-6 可以关闭。该数据只表示
  同机 CI PostgreSQL task 控制面基线，不能外推到公网网络、Provider 调用、Agent 质量或 99.9% SLA。

## 2026-08-18：6A-7 授权恢复与 packaging 原理

- 用户以“继续吧”明确授权 RQ-059；范围只到可重建 API+Worker+PostgreSQL package、真实 Worker
  executable composition、Linux no-I/O smoke 与 6A exit matrix/review。
- packaging 不增加 Coach 推理能力；它固定镜像、进程角色、依赖顺序、配置校验、启动/关闭和重建证据。
  API、Worker、PostgreSQL 是同一模块化单体的三个进程职责，不是 Multi-Agent 或微服务。
- 真实 Worker 必须先构造并验证 DB、Riot、Provider、RAG、Artifact、Application 全部依赖，再进入
  polling/claim；缺配置时 claim 前 fail closed，避免制造无证据 running task。
- Linux smoke 只证明干净 Linux 中 migration、API liveness/readiness、POST 202 与 Fake/no-I/O Worker
  消费链可重建，不证明真实 Key、Riot/Provider 质量、公网 Auth/HTTPS、备份或 SLA。
- exit matrix 必须把每条 ADR-0038/6A 承诺映射到源码、测试、公开 CI、限制与 deferred；测试总数不能
  替代逐项退出审查。正式 Auth/Session/Memory/SSE/前端和阶段 8 恢复能力仍不在本批。

## 2026-08-18：6A-7 composition/package 缺口审计

- 当前没有 `Dockerfile`/`.dockerignore`；`compose.yaml` 只有 PostgreSQL。Python 依赖也没有 Uvicorn，
  因而已存在的 `create_composed_app()` ASGI factory 尚无可声明的 Linux server 启动命令。
- `scripts/run_review_worker.py` 仍固定输出 `review_worker_executor_not_configured` 并返回 2；它没有读取
  配置或 claim，这个历史 fail-closed 正是 6A-7 必须闭环的执行缺口。
- 可复用零件完整：Database settings/Engine/Session/Repository、RiotClient、DataDragonService、
  RiotPlayerSummaryBuilder、LocalHybridKnowledgeProvider、RuntimeCompositionRoot、Zhipu Provider/Registry、
  RecentReviewApplicationService、FileRunReceiptStore、terminal evidence verifier 与 ReviewWorker。
- 生产 composition 将只组装上述稳定接缝，不复制 Agent/Harness。全部设置先解析；DB/Alembic readiness、
  本地 RAG/Skill/Prompt drift、Data Dragon 和 Provider 构造完成后才返回可 polling Worker；失败时销毁
  Engine 并只暴露 allowlisted code。
- Linux smoke 采用独立、显式启用的 no-I/O 诊断进程：HTTP POST 202 → PostgreSQL claim → 故意不访问
  Riot/Provider 的 Executor → 安全 failed terminal → HTTP task poll。它证明 package/control plane，
  不冒充 Agent 成功；6A-4 现有离线成功纵向继续证明 Application/Runtime/Harness/Artifact 接线。
- 本机仍无 Docker CLI，Docker build/Compose Linux smoke 只能由新增阻塞 GitHub Actions job 提供公共
  证据；本地先用文件/Compose合同、纯逻辑和现有 PostgreSQL skip 机制验证。

## 2026-08-18：6A-7 人工 package 审查发现

- Docker 官方 `compose up` 合同明确：`--exit-code-from` 会隐含 `--abort-on-container-exit`，而本项目
  migration 是预期成功退出的一次性服务。为避免它被当成“任一容器退出”而提前停止整组 smoke，CI 改为
  先 `up --detach --wait api`，再 `run --rm --no-deps smoke`，由 one-off 进程直接返回诊断退出码。
- no-I/O Worker 使用真实 `claim_next()`，若与普通本地 Compose 共用 project/volume，可能先领到已有 queued
  task。smoke 因此固定独立 `COMPOSE_PROJECT_NAME=riftcoach-packaging-smoke`，README 也要求同一 project
  name；这是数据隔离要求，不只是容器命名美化。仅靠脚本环境自称 `test` 也不足以阻止误用，因此 API 与
  PostgreSQL host 进一步限制为 Compose service/localhost/loopback，远端目标在任何 HTTP/DB I/O 前拒绝。
- `worker_id` 原先到 `ReviewWorker` 最后构造时才验证，可能在无效配置下先建 Engine/访问 Data Dragon。
  现在 composition 在任何 Engine/网络动作前用既有 `WorkerId` 合同验证并映射为
  `worker_configuration_invalid`，新增测试阻止回归。
- Worker preflight 对 Riot/Provider 证明的是 Secret/region/model/base URL/capability 等配置与构造合同，
  不额外付费调用模型，也不证明凭据在线有效或领域质量准入；文档已收紧表述。Data Dragon 构造会读取缓存
  或网络，仍在 claim 前完成。
- 额外的大小写不敏感 `sk-*` 形态扫描误命中实施文件名中的 `task-model-implementation` 和一个专门验证
  脱敏的 fake test token；既定 tracked `.env`/runs/cache 门通过。该宽扫描不是泄漏证据，不能为了追求
  “零命中”删除安全负例测试。

## 2026-08-18：首个 Linux smoke 的证据边界

- `b0f61ca` / Actions `32145005904` 证明 Dockerfile 可在 Ubuntu 构建、migration 可完成、API readiness
  可达，且隔离 project/volume 生效；pytest 与真实 PostgreSQL 也独立成功。它没有证明 one-off Worker
  链，因为该步以 `packaging_smoke_worker_failed` 退出，image boundary 也未执行。
- 首版 smoke 对外没有泄漏异常正文，但把 HTTP transport、DB preflight、claim、terminal CAS 和 query
  的意外异常最终都压成一个 worker code，导致公共证据只能定位到宽层。安全脱敏和可诊断性必须同时满足：
  新合同保留 body-free，只增加固定 allowlisted stage code，不打印 URL、SQL、异常或请求正文。
- workflow 在失败时新增的 diagnostics 只运行 `compose ps` 与 API/PostgreSQL 最后 100 行；不执行
  `compose config`（会展开环境）或输出容器 env，避免为排错泄漏数据库口令。

## 2026-08-18：为什么 API ready 而 smoke DB preflight 不 ready

- Docker 镜像同时有 `/opt/riftcoach/app` 源码和 site-packages wheel。`python -m uvicorn ...` 从
  WORKDIR 导入前者；`python scripts/run_packaging_smoke.py` 的 `sys.path[0]` 却是 `/opt/riftcoach/scripts`，
  会从 wheel 导入后者。
- `PostgresReadinessProbe` 不只执行 `SELECT 1`，还通过 `app.api.composition.PROJECT_ROOT/alembic.ini`
  读取代码 migration head。wheel import 下 PROJECT_ROOT 落在 site-packages，DB 明明在线仍会安全返回
  readiness failure；这正是 d8c5063 Linux 日志呈现的组合。
- 正确修复是用 `python -m scripts...` 让 WORKDIR 保持 import root，对 Worker 与 smoke 一致生效；错误修法是
  删除 migration 检查、把 not-ready 当 ready，或在脚本里硬编码 `/opt/riftcoach`。

## 2026-08-18：最终 Linux package 证据能证明什么

- `adf53e5` / Actions `32146760003` 证明干净 Ubuntu Runner 能构建非 root image，按 health/dependency
  执行 PostgreSQL → migration → API ready，并由独立 one-off 容器经 HTTP 创建 task、真实 claim、写入
  `failed/worker_execution_failed`、再通过 HTTP 复读同一 task。
- 输出中的 `external_riot_provider_calls=0` 是由 smoke 路径结构和结果字段共同支持的“本次调用数为零”，
  不是生产 Worker 永远不访问外部服务；真实 Worker 仍会在处理玩家任务时访问 Riot/Data Dragon/Provider。
- image boundary 证明运行用户非 root，且 `/opt/riftcoach` 不含 `.env`、tests、本地 cache/runs、reports、
  tmp；它不证明运行时 Secret manager、备份、HTTPS、Auth 或漏洞管理已经完成。
- 因此 6A 可关闭的是“持久异步 task API 基座 + 可重建控制面 package”。长期 Session/Memory 与个性化
  Coach 是同一主阶段 6 的后续问题，不能由本次 smoke 前推完成。

## 2026-08-19：Session/Memory 入口恢复与概念边界

- 状态收尾提交 `d1cc2ed` 自身的 Actions `32147545753` 也已让 pytest、PostgreSQL、packaging-smoke
  三 job 成功；活动文件此前漏记。用户“继下一步”构成 RQ-060，入口设计已获授权，但产品实现未获授权。
- `session-catchup.py` 只寻找仓库根目录 `task_plan.md/findings.md/progress.md`，不会自动解析本仓库
  `.planning/.active_plan`；本次静默是假阴性风险，不能再单凭无输出宣称无遗漏。人工 JSONL/Git 审计确认
  工作树干净、没有半写产品代码，遗漏仅为上述公共状态与授权记录。
- 6A `review_tasks` 保存的是 task/run 状态、claim ownership、终态与 Artifact 引用；它回答“工作做到哪”，
  不保存一段对话包含哪些消息、玩家长期目标是什么，因此 task persistence 不等于 Session/Memory。
- 本阶段必须继续分开六类数据：当前对话 Session/消息、可丢弃的工作上下文、玩家确认画像、历史复盘/训练
  情景、原始 match facts/Artifact、RAG 外部知识。只有前四类中的合格子集可能属于 Session/Memory。

## 2026-08-19：EchoMind 与 AGI-Saber Memory 源码初审

- EchoMind 的 `user_id + conv_id`、工作/情景/画像三分法和读取后装配 Context 的主链值得吸收；但其同步
  Redis client 位于 async API、请求体自带 user/conv、Chroma profile `limit=1` 无可靠排序/合并、24h TTL、
  `asyncio.create_task(update_profile)` 无 durable claim/恢复，以及模型推断自动长期写入均不满足 RiftCoach。
- EchoMind 没有用户可查看/更正/导出/删除合同，也没有写入 provenance/confidence/confirmation；Redis、
  Chroma 与 LLM 写入之间无事务或补偿。复制技术栈会放大缺陷，不能等同于“迁移 EchoMind”。
- AGI-Saber 的 typed category/tags、active/superseded/quarantine、filter recall、dedup/merge/expiry 和安全检查
  提供更丰富的设计参考；但它会从 assistant 回复或规则/LLM 自动写 preference/LTM，后台线程无 durable
  queue/flush，跨 PG/图/内存错误多为 warning，Graph/Neo4j/Milvus 对当前作品集规模过重。
- 当前没有语义召回 Bad Case，故 PostgreSQL 结构化真源应进入备选比较；Redis/向量/图只能作为出现真实
  性能或检索缺口后的派生索引候选，不能在 entry design 前预设采用。
- 现有 HTTP 已证明 owner 不能来自请求 body/header，task/run/report 先做 trusted ActorContext ownership
  查询，另一 owner 对同一 task/run 得到 404；这些测试是未来 Session/Memory ownership 的可复用安全基线，
  但当前没有 `conversation_id`、消息、画像或训练进度表，不能把 owner-scoped task 查询外推成会话隔离。

## 2026-08-19：第一节概念与数据流获确认

- 用户确认六类职责边界：Task/Run 管执行状态，Session 管对话身份，消息派生有界工作上下文，长期 Memory
  管跨会话玩家状态，原始比赛事实/Artifact 管已发生事实，RAG 管共享外部知识。
- 用户确认长期写入不应由模型直写；正常方向是报告/对话后先产生 Memory Candidate，再经过来源、类型、
  置信度、冲突和用户确认等写入门，最后才进入 active/pending/rejected/superseded 状态。
- 下一设计问题是存储与写入架构，不重新讨论已确认的职责边界；任何存储选择都必须保持上述分层。

## 2026-08-19：第二节 PostgreSQL 单一真源获确认

- 用户采用推荐方案 A：Session、消息、Memory Candidate、长期 Memory、训练计划与进度以 PostgreSQL
  为权威真源；工作上下文初版由有界查询/投影构建，不单独依赖 Redis。
- EchoMind 式 Redis + Chroma 拆分和 PostgreSQL + Redis + 向量索引首日混合均不进入 V1。原因不是这些
  技术无价值，而是当前没有延迟或语义召回 Bad Case 足以支付双写、删除传播和额外运维成本。
- Redis 后续只能作为可丢失、可重建缓存；向量能力只能作为 PostgreSQL 权威记录的派生索引。任何索引
  丢失后必须可从真源重建，索引命中不能绕过 ownership、状态和 write gate。
- 关系模型仍必须解决两层主体：应用 owner 与被分析 Riot 玩家不是天然同一对象；否则同一 owner 分析
  多个公开账号时，玩家画像、复盘情景和训练进度会交叉污染。

## 2026-08-19：外服账号认领不等于账号归属验证

- 用户明确提醒当前产品无法使用中国大陆国服 API，只能分析 Riot 官方 API 路由覆盖的外服账号。Riot
  官方 LoL 文档当前列出的 platform routing values 为 BR1/EUN1/EUW1/JP1/KR/LA1/LA2/NA1/OC1/TR1/
  RU/PH2/SG2/TH2/TW2/VN2，regional routing values 为 AMERICAS/ASIA/EUROPE/SEA，没有中国大陆 CN
  路由。证据：[Riot LoL Developer Docs](https://developer.riotgames.com/docs/lol)。
- Account-V1 `/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` 可以把 Riot ID 解析为 PUUID，
  但该查询没有当前 RiftCoach 用户的授权证明，只能说明账号存在且可通过公开 API 查询。
- Riot 官方用于识别“哪个 Riot 账号完成登录授权”的机制是 RSO 和
  `/riot/account/v1/accounts/me`；RSO client 只向已有获批 Production-level application/API key 的应用
  开放。证据：[Riot RSO FAQ](https://developer.riotgames.com/docs/faqs)。
- 因而 V1 的“这是我的账号”只能保存为未验证 `claimed_self`，不能命名为 `verified_self`，不能解锁
  非公开数据，也不能把同一 PUUID 下另一个 RiftCoach owner 的私人目标、备注或 Memory 合并过来。
- 当前身份设计应比较“只允许 claimed-self”与“同时支持 claimed-self/public-observed”两案；后一案更
  能覆盖职业选手或朋友等公开账号分析，但具体裁决仍待用户确认。未来 RSO 只能把匹配 PUUID 的关系升级
  为 verified，不能无审计地合并既有 owner-local Memory。
- 更精确地说，RSO 本身仍不足以把关系升级：必须先有正式 RiftCoach owner Auth，再用 state/nonce 等
  安全机制把 OAuth/OIDC callback 绑定到该 owner，并要求 `/accounts/me` 的完整 PUUID 与当前 subject 精确
  匹配。当前 Auth/RSO 都未实现，因此 verified 创建路径必须不存在。
- 推荐的数据模型把两个维度分开：`relationship_role=self|observed` 表示用途，
  `verification_status=unverified_claim|not_applicable|rso_verified` 表示证据。用户界面的 `claimed_self` 是
  `self + unverified_claim` 的投影，未来 `verified_self` 是 `self + rso_verified` 的投影；这仍是待确认设计，
  不是当前产品代码或已创建的 enum。
- `player_subject` 应以完整 PUUID 作为稳定外部身份，Riot ID 只作可变显示别名。相同 PUUID 改名不新建
  Memory；相同显示 Riot ID 日后解析为不同 PUUID 时不得静默重绑。完整 PUUID 不进入公共响应、日志或
  Prompt。当前 `Summary` 只输出 PUUID 前缀，符合展示最小化，但尚无持久 subject 表。
- 隔离还需区分 `owner_global` 偏好（如语言/报告详细度）和 `owner_player` 状态（目标、计划、复盘情景、
  进度）。同一 PUUID 被两个 owner 使用时，最多共享公开上游事实缓存，不能共享关系状态或私人 Memory。
- 当前 `RIOT_REGION` 只做字符串形状校验；未来实现必须改成官方 regional routing allowlist，并在任何
  网络 I/O 前拒绝 `cn` 等无效值。`zh_CN` 只是 Data Dragon 中文本地化代码，不是中国大陆服务器路由。

## 2026-08-19：第三节外服玩家关系策略获确认

- 用户明确“确认吧”，接受同时提供 `claimed_self` 与受限 `public_observed` 的推荐方案；该确认记录为
  RQ-062，只冻结设计，不授权 schema、migration、Repository、API、Auth 或 RSO 实现。
- 两维模型正式成为当前设计：`relationship_role=self|observed` 与
  `verification_status=unverified_claim|not_applicable|rso_verified`。前两个当前组合分别投影为
  `claimed_self` 和 `public_observed`；`rso_verified` 是 future-only，当前任何写入均应 fail closed。
- `claimed_self` 可承载 owner 为该玩家主体输入的训练目标、计划与进度，但 UI/API 必须保留未验证标记；
  `public_observed` 只承载公开比赛分析、owner-local 观察备注/趋势，报告使用观察语义，不推断被观察者的
  私人偏好，也不声称对方完成了训练。
- 任一关系都不增加 Riot API 权限，也不允许相同 PUUID 下跨 owner 合并关系、Session 或私人 Memory。
- 本确认没有涵盖 conversation 中途切换语义。下一设计问题必须独立比较“会话固定一个 subject”与
  “显式可切换 + CAS/event/context reset”；自由文本、模型或最新 Riot ID 静默切换必须排除。

## 2026-08-19：Conversation 单一玩家绑定获确认

- 用户确认方案 A：conversation 创建时固定一个 owner-local player subject，V1 生命周期内不可切换；分析
  不同 PUUID 必须新建 conversation。该确认记录为 RQ-063，只冻结设计，不授权实现。
- 同一 PUUID 的 Riot ID 改名不是切换；同一显示 Riot ID 解析成不同 PUUID 必须返回安全 mismatch，不能
  更新旧 subject。自由文本、模型、客户端 payload 或最新请求都不能改变绑定。
- 消息、工作 Context、task/run、Memory Candidate 必须从服务器端 conversation 继承同一
  `owner_id + conversation_id + player_subject_id`。未来 PostgreSQL 设计应用 owner-scoped composite
  FK/unique/check 约束，应用层仍做友好错误；任一层不能只按 PUUID 查询私人数据。
- 当前代码暴露一个必须先解决的 bootstrap 接缝：`CreateReviewTaskCommand`/`PendingReviewTask` 入队时只有
  owner + Riot ID request，Worker claim 后 `RecentReviewApplicationService._build_summary()` 才经 Riot
  API 获得完整 PUUID。因而不能在 HTTP 入队时假装已有稳定 subject/conversation。
- 下一设计门应比较：(A) 独立异步 player-link task 先解析 PUUID，再创建 conversation/review；(B) 首个
  review task 在 Worker 解析 PUUID 后原子引导 relation/conversation；(C) API 同步调用 Account-V1。
  任何方案都不得创建以可变 Riot ID 作为稳定身份的 provisional subject。

## 2026-08-19：RQ-064 设计审计后的两项关键修正

- 自动推进授权只能按用户最后一句精确解释为 entry design→6B-1→6B-2；此前“每批继续下一批”的宽泛文字
  会误授权 6B-3 至 6B-9，已统一收紧。6B-2 公共全绿后只准备 6B-3 并等待新授权。
- `player_link_tasks` 不能只存 Riot ID hash：Worker 必须读取 bounded normalized `game_name/tag_line` 才能
  调 Account-V1。它们是私有 SQL 输入，可参与 fingerprint/claim，但不进入公共 View、日志、Trace 或 Prompt。
- lookup 后/resolve 事务前 crash 只证明没有身份副作用，不等于 V1 已有自动恢复；原 running task 仍需
  recovery-required/显式处置，自动 lease/reclaim 留阶段 8。
- ADR-0039、正式设计和实施计划核心分层一致；当前只是本地设计产物，尚无公共 CI 或产品 migration。

## 2026-08-19：6B-1 实现审计发现

- PostgreSQL identifier 最长 63 字符；SQLAlchemy metadata 能构造超长名称，但 PostgreSQL dialect 在 DDL
  编译时才拒绝。因此 migration 批除 metadata assertions 外还应保留 offline SQL/真库 upgrade 证据。
- Link success 必须保存 Riot 响应确认后的 `confirmed_game_name/tag_line`，不能只回显请求 Riot ID；否则
  Account-V1 规范化/改名后，成功 View 无法说明实际链接到的显示身份。PUUID 仍只存私有 subject 表。
- Link Task 到 relationship 使用 owner/relationship/subject/role 复合 FK；这让一个合法 relationship_id
  也不能被另一 owner、subject 或 role 错绑。target 端需要对应 composite unique，不能只依赖 PK。
- Alias 唯一性是 subject-local `(subject, routing, normalized_riot_id_hash)`，不是全局 Riot ID→subject；
  Riot ID 历史上可能重指向，Conversation 稳定身份只认 PUUID subject。
- `resolve_link()` 的网络边界通过参数类型而不是 callback 保证：Repository 只接收已解析
  `ResolvedRiotAccount`，所以 Account-V1 无法在 SQL transaction/row lock 内执行。
- role conflict 必须在同一个 resolve transaction 把 running task 变成 failed；抛异常后让 Worker 再调用
  `fail_link()` 会留下“关系冲突已知但 task 永久 running”的 crash window。
- 本机没有 PostgreSQL 时，domain/metadata/mapping 可以绿，但 migration/CHECK/FK/ON CONFLICT/SKIP LOCKED/
  并发与 rollback 必须明确 skip，并由 exact-SHA PostgreSQL 17 job 补齐；SQLite 不具备等价证据。
- RQ-065 只收紧本轮自动推进，不改变九个 6B 批次设计：6B-2 仍是下一批，但必须在下一轮重新授权。
- Alembic 默认 version table 的 `version_num` 是 `VARCHAR(32)`；revision 标识符与 migration 文件名不是
  同一约束。文件名可以保持可读，`revision` 必须独立控制在 32 字符内，并应有不依赖数据库的回归测试。
- PostgreSQL migration job 与 package stack 同时在 migration 前置阶段失败，是共享基础设施根因信号；
  在这种情况下不应先改两个 job 或 Repository，而应先审计二者共同的 Alembic 路径。
- 使用含 `ck_%(table_name)s_%(constraint_name)s` 的 naming convention 时，migration 若传入已带完整前缀的
  CHECK 名，必须用 `op.f(full_name)` 标记为已格式化；否则会再次套 convention，超长后由 SQLAlchemy/Postgres
  截断并加 hash。UQ/FK convention 不使用 `constraint_name` token，行为不能想当然类推。
- 单修日志中第一个 role-verification CHECK 会留下其他 21 个潜在同类错误；正确修复是审计 0002 全部
  CheckConstraint，并用 offline SQL regression 断言既有完整名存在且双前缀不存在。

## 2026-08-19：6B-2 入口源码审计发现

- 现有 `RiotClient` 是薄 `requests.Session` 传输，显式 `api_key + region` 构造时不会读取 dotenv；
  Resolver 可以用注入 client factory 复用它，不需要新 HTTP SDK，也不能进入 API composition。
- `ReviewWorker` 的 claim-commit→事务外 execute→terminal CAS、PollingPolicy 与 StopSignal 模式可复用
  思想，但 Link 的 account/failure/role-conflict terminal 不同；当前新建窄 PlayerLinkWorker 比提前泛化
  通用 Worker 更小、更可审计。
- 6B-1 Repository 已把网络边界固定为严格 `ResolvedRiotAccount` 参数，因此 Resolver/Worker 无需也不得
  把 callback 传入事务；API composition 只需共享 Session factory 构造 Player Repository/Service。
- 本轮主线程再次出现 Codex `prompt_cache_retention` 参数兼容错误；本地 `config.toml` 未设置该字段，
  全局状态中的命中只是用户粘贴的错误文本。该平台问题不产生项目命令或文件修改，6B-2 禁用子代理。

## 2026-08-19：6B-2 本地完成审查发现与修补

- 当前 API 的四个 routing enum 与 Worker policy 若允许任意子集，会出现请求成功入队但 Worker policy 在
  claim 后拒绝的隐性失败。由于本批没有 API policy 配置端点，采用最小一致性修补：配置必须精确覆盖
  `americas,asia,europe,sea`；未来若需要区域限制，必须同时设计 API/Worker 共享 policy 版本，不在这里
  静默放宽。
- packaging smoke 原先使用 `f"{worker_id}-link"` 构造第二 worker ID；合法的最大长度 Review worker ID
  会因此生成非法 Link ID。smoke 现在使用独立固定的 `packaging-link-smoke-worker`，不改变生产部署 ID。
- `PlayerLinkWorker` 只需要 `is_set()/wait()` 两个方法；将该小 Protocol 放在 Link Worker 模块，解除对
  `ReviewWorker` 内部协议的类型依赖，同时不抽象两个具有不同终态语义的 Worker。
- 聚焦回归基线在修补前为 `109 passed, 2 skipped`（Resolver/Worker/API/package 集合）；修补后扩大为
  `149 passed, 2 skipped, 1 warning`，完整为 `1216 passed, 42 skipped, 1 warning, 110 subtests`。
- RAG、Harness、compileall、YAML、治理、SDK boundary、tracked data 与 diff 门均通过；本机 42 个 skip
  仍明确归因于没有 PostgreSQL/Docker。没有读取 Key、真实 Riot/Provider 调用或生成可公开的私人运行数据。

## 2026-08-20：6B-2 公共证据与边界发现

- `0c13a58` / Actions `32301852042` 的三个独立 job 全绿，证明本机条件 skip 与 Linux package 空白均已由
  同一 SHA 补齐，而不是由本地 Fake 测试替代：真实 PostgreSQL job 为 `70 passed`，migration 可逆且
  ORM metadata 与 head 一致。
- package smoke 同一进程链真实产生 Review Task 安全 `failed` 与 Fake Resolver Player Link `succeeded`，
  并输出 `external_riot_provider_calls=0`；这证明两个异步控制面能共存，不证明生产 Resolver 的 Riot
  凭据、限流或网络成功。
- 公开 pytest 与本地最终结果一致：`1216 passed, 42 skipped, 1 warning, 110 subtests passed`；RAG 与
  Harness 横向门也保持通过。因而 6B-2 可关闭，但 Conversation/Message/Memory 仍没有任何实现证据。

## 2026-08-20：持久教学/工程说明缺口审计启动

- 用户指出最近独立文档颗粒度下降，并进一步要求确认缺口是否真的从 6B 才开始；不能沿用上一轮初判，
  必须从阶段 0 起按统一标准重新审计。
- “已有文档”不自动等于“教学/工程说明完整”。本轮使用七项核心覆盖：问题与原理、实际代码地图、
  数据/控制流、测试/公共证据、事务/失败/安全边界、运行示例、面试安全表述；聊天、canonical 和
  progress 中一句“已讲过”只能作为过程记录，不能单独验收持久学习资产。
- 三种补齐方式中选择覆盖矩阵驱动的混合方案：拒绝为全部历史子阶段机械复制几十篇文档，也拒绝只写
  一篇笼统总览；先复用已经充分的 learner artifact，只对真实缺口新增 walkthrough/implementation review。
- 已确认 6B 总体 ADR/design/implementation plan 很完整，但 6B-1/6B-2 缺实际落地后的独立代码地图、
  证据矩阵、运行示例和面试表述；README 也尚未介绍 Player Link 当前能力。更早阶段仍在审计，当前不能
  宣称最早缺口就是 6B。
- 用户补充要求不是只补初学者文章，还要补齐上一轮列出的全部设计、实现、证据、边界、公共说明和防复发
  治理材料；RQ-067 将其设为 6B-3 实施前置门。补齐 exact-SHA 公共闭环后可直接进入 6B-3，无需再确认。

## 2026-08-20：RQ-067 覆盖账本与防复发门实现

- 覆盖账本采用显式八维 evidence：问题/原理、设计/实现、代码地图、数据/控制流、验证、运行、失败/安全/边界、面试表述；成熟退出复核可以承担多个维度，不按历史原子检查点机械复制文档。
- `docs/learning/coverage.yaml` 为每组增加唯一、严格递增的 `sequence`。治理脚本不再只相信 YAML 列表位置；重排覆盖组、遗漏当前 checkpoint、前序 planned、complete 维度为空、证据在仓库外/不存在/非 Markdown 均有红灯测试。
- 本地已新增阶段 0/1/4、5B、6B-1、6B-2 独立材料，扩充阶段 3/5A、补 5C 入口链接，建立统一 README；尚未创建 6B-3 产品代码。
- README Player Link 运行说明已区分“只启动 API + Link Worker”和“完整 runtime 还需 LLM Provider 配置”，不再让示例暗示仅 Riot Key 就能启动完整 review Worker。

## 2026-08-20：本地退出复核结果

- 完整回归为 `1224 passed, 42 skipped, 1 warning, 110 subtests passed`；治理覆盖门为 `10 passed`，Agent Loop/Skill 为 `34 passed`，Provider/Tool 为 `101 passed, 68 subtests`。
- RAG development 八题和 independent holdout 七题均通过既有阈值；Harness dry-run 为 `published`/0 revisions；所有本批临时输出已清理，未产生 tracked run data。
- 本地结论只能是 `pass-local-pending-public-ci`：本机 PostgreSQL/Docker 缺失造成的 42 skip 不能替代公共真库/package 证据；文档公共完成仍需独立提交 exact-SHA 三 job。

## 2026-08-20：公共闭环结果

- `63435d9` / Actions `32308631289` 三 job 全绿，文档/工程证据批正式公共完成；Q11 从本地 pending 升级为完成。
- RQ-067 的条件授权已兑现，canonical 进入 6B-3 初学者设计复核与 TDD；仍保持 Conversation/Message/Memory 尚未实现的边界。

## 2026-08-20：6B-3 设计审计发现

- 现有 `owner_player_relationships` 的复合唯一键可以作为 Conversation 的复合 FK parent，但 FK
  不能检查跨表 `status='active'`；创建必须锁 relationship 行后检查 active，读取/追加还要过滤 hidden relationship。
- 现有 POST 控制面都使用 Idempotency-Key；若 Conversation 不继承该合同，HTTP 超时重试会产生重复
  Coach 房间。因此 6B-3 增加 owner-scoped key + request fingerprint，并定义 created/replayed/conflict。
- 设计稿原先同时写了 `user|assistant` 和“6B-3 不运行 Agent”，存在公共写入边界歧义。冻结为 schema
  保留 assistant、公共 Service/API 只允许 user；未来 terminal assistant 另在 6B-8 接入。
- `MAX(sequence_no)+1` 在并发下不安全；固定首条为 1、锁 Conversation、同事务递增
  `next_message_sequence`，并用 unique(conversation_id, sequence_no) 做第二道防线。回滚同时回滚计数器和消息。
- 当前项目没有既有 PostgreSQL trigger，0003 将首次引入 immutable binding/message trigger；必须有 direct
  SQL、upgrade/downgrade 和真实 PostgreSQL 17 证据，ORM metadata/alembic check 不能单独证明。
- source task/run 引用不设阻塞性强 FK，因为 Task/Run 生命周期独立；公共 user API 不接这些字段，未来
  assistant terminal 才能设置 body-free 引用。

## 2026-08-20：backfill 治理复核

- README 的 Player Link 启动说明已正确区分只启动 Link Worker 与完整 LLM runtime，旧 finding 不再成立。
- 记录中的 `2026-08-20` 与当前仓库日期一致，不回写为错误的未来日期。
- 原 coverage 检查只验证 YAML 列表位置和递增 sequence；通过重排并同步重编号仍可能绕过。已增加固定
  `LEARNING_COVERAGE_CANONICAL_ORDER`、受检的 coverage 人类镜像和两项回归测试，验证治理聚焦 `12 passed`。

## 2026-08-20：6B-3 设计公共证据

- `b6a7112` / Actions `32313707301` 三 job 全绿，证明设计与治理加固没有破坏现有 Linux、PostgreSQL、
  RAG、Harness 或 package 边界；它仍是 design evidence，不是 Conversation/Message implementation evidence。
- 6B-3 现可按 ADR-0040 进入 TDD；若红灯暴露设计矛盾，必须先更新 ADR/计划，不能静默让代码定义需求。

## 2026-08-20：6B-3 实现恢复审查与补强门

- 当前工作树已有 Conversation/Message domain、Service、PostgreSQL ORM/migration/Repository、六个 HTTP
  端点、composition、Linux package smoke 与分层测试，但尚未提交或取得实现 SHA 的公共 PostgreSQL/package
  证据；canonical 继续保持 `6B-3 / in_progress`。
- 只读 persistence 审查未发现 P0/P1；发现原 archive/append 与 hide/append 只用 Barrier 同时起跑，未确定
  两种锁顺序，可能让错误实现碰巧通过。提交前必须用可控事务锁与事件分别证明 append-first 和 lifecycle-first。
- `list_messages()` 当前为保证“可见性检查与分页读取”线性一致，会锁 relationship 与 Conversation；语义正确但
  普通读取会与 append/archive/hide 串行。6B-3 先明确记录这一作品集规模取舍，不在无真实性能 Bad Case 时引入
  更复杂的单查询投影。
- Conversation trigger 保护 binding 与生命周期不可逆，Message trigger 保护 append-only 字段；连续序号由
  Repository 的同事务行锁、计数器更新与唯一约束保证，不能误称为 trigger 保证。
- 既有 import/OpenAPI no-I/O 测试受 Python 模块缓存影响；已新增独立干净 Python 子进程门，在 import 前阻断
  Secret env、数据库 Engine 与 HTTP I/O，再构造 OpenAPI。聚焦 composition 回归为 `10 passed, 1 warning`。
## 2026-08-20：6B-3 本地实现收尾审查

- 6B-3 聚焦集合为 `85 passed, 25 skipped`；完整回归为 `1295 passed, 67 skipped, 1 warning,
  110 subtests passed`。本机 skip 仍全部来自缺少 PostgreSQL/Docker，不能冒充公共真库或 package 证据。
- RAG development/independent holdout、Harness dry-run、compileall、Provider boundary、tracked
  secret/run-data、YAML、治理和 `git diff --check` 均通过；Docker Compose 本机不可执行，保留为 CI 阻塞门。
- 审查修复的两个 P2 是 archive/hide 422 的公开错误 DTO 与有效 command 后 UUID/clock 故障的 503 投影；
  并发测试改成 blocker transaction + SQLAlchemy event 的确定性锁顺序，覆盖 lifecycle-first 与 append-first。
- 当前只剩独立提交/推送和同 SHA 三个公共 job；全绿前不改变 coverage `planned`，不关闭 6B-3，也不进入 6B-4。

## 2026-08-20：6B-3 首次公共 PostgreSQL 门失败

- `0ca7fde` 的 `pytest` 与 `packaging-smoke` 公共 job 成功；`postgres-migrations` 失败于 18 个
  Conversation Repository/concurrency 测试。
- 根因是测试 fixture 在一次 ORM flush 中同时加入 `PlayerSubjectRecord` 与
  `OwnerPlayerRelationshipRecord`，但两者没有 ORM relationship 声明，真实 PostgreSQL 可能先插入
  子表并触发 FK violation；本机 PostgreSQL 缺失使该问题只表现为 skip。
- 最小修复是在测试 fixture 插入 relationship 前显式 `session.flush()`，保留生产复合 FK 与约束，不放宽
  schema、跳过测试或修改事务语义。失败 SHA 保留为审计证据，不重跑追绿。

## 2026-08-20：6B-3 公共闭环后的最终事实

- 修复提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081` 的 Actions run `32329686381` 三 job 全绿；失败的
  `0ca7fde` 只保留为 PostgreSQL 顺序问题的审计证据。
- 真实公共 PostgreSQL job `100 passed, 1 warning`，并补齐 migration upgrade/downgrade、`alembic check`、
  trigger/FK/事务/并发和 Linux package smoke 证据；本机 67 个 skip 仍是无 Docker/PostgreSQL 的环境事实。
- 6B-3 的产品闭环只包括 Conversation/Message 控制面。assistant terminal、Agent、Review Task 2.0、Memory、
  Auth/RSO、SSE、前端和新框架仍是后续边界；6B-4 只登记为 prepared/waiting authorization。

## 2026-08-20：收尾验证环境记录

- 首次收尾命令误用系统 Python；该解释器没有 `pytest`，命令在测试收集前以 `ModuleNotFoundError` 退出，
  没有代码副作用。随后改用仓库 `.venv\Scripts\python.exe`，聚焦与完整回归均通过；以后仓库测试统一显式
  使用虚拟环境解释器。

## 2026-08-20：RQ-068 与 6B-4 入口裁决

- 用户明确“继续 6B-4”；起始 `HEAD == origin/main == 4fb66a8`、工作树干净，AGENTS 恢复顺序与治理
  预检通过。授权只覆盖 `6B-4-conversation-bound-recent-review-identity`，不进入 6B-5。
- 当前断点不是 Agent/Memory 缺失，而是 6B-3 Conversation identity 与既有 6A Review Task/Worker 尚未
  相连：旧 schema 1.0 仍从客户端 Riot ID 入队，Worker 后续 Account-V1 解析，不能证明复盘任务继承固定
  Conversation subject。
- 比较三种方案后选择在既有 `review_tasks` 增加 nullable legacy-compatible schema 2.0 identity columns，
  由单一 PostgreSQL 短事务锁定 active Conversation 并派生 tuple。只把 `conversation_id` 放进 JSON 缺少
  数据库 identity 约束；新建第二套 task 表会复制 claim/Worker/终态/恢复基础设施。
- schema 1.0 row 的新增身份列保持 null 且旧端点/执行可读兼容；schema 2.0 要求完整 trusted tuple。新的
  body 只能有 `count/queue/focus`，客户端、模型、UI 当前选择和可变 alias 都不能覆盖 identity/PUUID。
- v2 Executor 应走 trusted PUUID Summary path，不再调用 Account-V1；别名只作显示。测试/CI 继续使用
  Fake Riot/Fake Provider，真实外部调用为 0。
- 恢复时发现 `docs/roadmap.md` 与 `docs/learning/README.md` 各有一处 6B-3 公共闭环前的陈旧表述；已随
  状态迁移修正，不改历史证据。

## 2026-08-20：6B-4 专用设计冻结后的精确接缝结论

- 不能由 Service 先读 Conversation、再调用现有 `create_or_replay()`；两个事务之间会留下
  archive/hide 竞态。schema 2.0 必须由 Repository 新增原子 create 方法，在 relationship→Conversation
  一致锁顺序下派生 tuple、计算 identity-aware fingerprint 并插入 Task。
- schema 2.0 fingerprint 必须覆盖 owner/conversation/relationship/subject/role，不能只覆盖公共
  count/queue/focus；否则同 owner/key 跨 Conversation 会错误 replay。
- 现有 `ReviewTask` 可以增加私有 execution target，由 Repository 通过 subject/alias 装配；公共 View
  只投影 `conversation_id`。保留 `_record_to_task(record)` 的 legacy 1.0 helper 可避免已有直接测试失效。
- Summary/Application 不需要复制 Runtime/Harness 后半段：新增 `build_by_puuid()` 与
  `review_by_puuid()`，Executor 按 1.0/2.0 分支，之后共用 compiler/runtime/receipt/evidence。
- schema 2.0 已排队 Task 在 Conversation 后来 archive/hide 后仍应按冻结 subject 执行；6B-4 不写
  assistant Message/Memory，因此“完成原 Task”不等于“向已隐藏 Conversation 写终态”。
- 已冻结 ADR-0041、专用教学设计与六任务实施计划；未引入新依赖或外部 I/O。

## 2026-08-20：6B-4 Repository 恢复审计

- 本机未配置 `RIFTCOACH_TEST_DATABASE_URL`，所以新增 Repository 真库测试按合同得到 `4 skipped`；这不是绿灯，也不能在本地直接观察缺方法红灯，当前实现语义仍必须由阻塞 PostgreSQL CI 补证。
- 现有 `task_repository.py` 的 create/get/claim/replay 全部直接调用模块级 `_record_to_task()`；要支持 schema 2.0，必须新增 session-aware `_map_record()` 装配 subject/最新 alias，同时保留模块级 helper 对 legacy 1.0 无数据库测试的兼容。
- `PlayerSubjectRecord` 已提供稳定 PUUID/current routing，`PlayerAliasRecord` 已提供带 `last_seen_at` 的可变显示 alias；最新 alias 应使用 `last_seen_at DESC, player_alias_id ASC` 确定性选择，Conversation archive 后 claim 只按冻结 subject 装配 target，不重新要求 Conversation active。
- 6B-3 已有可复用的确定性并发证明模式：先由独立连接锁 Conversation 行，让第一操作取得 relationship lock 后阻塞，再观察第二操作尝试同一 relationship lock；释放 blocker 后即可分别证明 create-first 允许建 Task、lifecycle-first 让新 Task 安全拒绝，而不是用不稳定 Barrier 猜调度顺序。
- Summary 现有 `build_player_summary()` 把 Account-V1 解析和 Match-V5 汇总写在同一函数；可信 PUUID 路径应抽取共享的“已知 account/PUUID 后半段”，让 legacy `build()` 仍先 Account-V1，而 `build_by_puuid()` 只构造显示 account 后直接复用 Match-V5/aggregate 逻辑。
- Application Service 的 validate/render/compile/runtime/receipt 后半段已经集中在 `review()`；6B-4 应新增一个小的 `review_by_puuid()` 入口并复用私有 `_review_from_summary()`，而不是复制 Harness 控制流。Executor 则必须先按 schema 1.0/2.0 校验不同 request/fingerprint，再汇入同一 terminal evidence 校验。

## 2026-08-20：6B-4 部署组合接缝结论

- 新 route 只存在于 `create_app()` 不等于 composed 部署可用；lifespan 使用的 `_TaskServiceProxy` 必须显式
  实现同一 `TaskServicePort.create_conversation_review()`。真实 composed TestClient 红灯先返回 503，证明
  该缺口不是纸面推断。
- 不需要第二套 Worker：Repository claim 已能投影 1.0/2.0，升级后的 Executor 已按 schema 分支，所以
  package 只需第二次调用现有 ReviewWorker，并验证 v2 Task 进入安全终态。
- package smoke 的可执行结果增加字段后属于新 envelope，故内部版本由 1.0 升到 1.1；它仍只证明
  PostgreSQL/API/Worker 控制流和 external calls=0，不伪造 Agent/Harness 成功或模型质量。
- 两个新真库文件即使会被完整 pytest 收集，也必须显式加入 `postgres-migrations` job，才能让最关键的
  migration/FK/trigger/事务锁语义成为阻塞公共证据。

## 2026-08-20：6B-4 exact-SHA 公共证据裁决

- `d63f9085f66e49557b4674d0698495dcb7335c82` / Actions `32347834279` 的三个阻塞 job 全绿，补齐本机
  无 PostgreSQL/Docker 时无法取得的复合 FK、trigger、锁、迁移与 Linux package 证据。
- PostgreSQL job 为 `113 passed, 1 warning`；0004 upgrade/downgrade、完整 migration 链和
  `alembic check` 均通过。公开普通回归为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`。
- package smoke 中 schema 2.0 Review Task 经同一 Worker 得到 allowlisted `failed` 终态，Conversation
  仍 active，外部调用为 0。这是安全失败和安装后组合证据，不是 Agent/Provider 质量证据。
- 6B-4 可以关闭；6B-5 只准备并等待用户授权，不能因为总设计已存在就视为已开始。

## 2026-08-20：RQ-069 与 6B-5 materialization 裁决

- 用户已明确授权 6B-5；起始 `HEAD == origin/main == 405e109`、工作树干净，治理预检通过。
- 6B-5 的关键矛盾是“需要证明 exactly-once acceptance，但本批不创建具体长期 Memory 表”。万能 JSONB
  表会破坏 typed 权限/生命周期，单独 receipt 不能证明 Memory 存在，新增 approved 中间态又会擅改已冻结
  状态机。
- 选择事务内 typed materializer：Repository 锁 Candidate，在同一 Session 调用已注册的本地持久化策略；
  target 成功后才写 accepted。6B-5 用测试专用 target 证明事务，生产 registry 在 6B-6 前为空并 fail closed。
- Candidate 必须从服务器 Conversation 派生 owner/relationship/subject/role；客户端、模型、正文无字段覆盖。
  observed 只允许受限第三人称 review observation；confidence 不提供写权限。

## 2026-08-20：6B-5 本地实现与测试证据

- Pure/Gate/Service/API/package 聚焦全部通过；全量回归首次只剩旧 OpenAPI exact-path 断言，补入 4 条
  Candidate 路由后恢复通过。
- 0005 migration 为 Candidate 增加 Conversation/source message/source v2 task composite FK、status/CHECK、
  owner/key 唯一、source identity unique、expiry/pending/history index 和 immutable trigger；0005 同步更新
  现有 Conversation Message/Review Task source unique 合同。
- Repository 采用 relationship→Conversation→Candidate 锁顺序；accept 缺少 materializer 返回
  `target_unavailable` 且无写入；materializer 仅收到 restricted Session view；测试 target 证明 target+accepted
  同事务、异常 rollback、并发第二请求 replay。
- public API 只接受 user structured provenance，并固定 producer；DTO 不返回 proposal payload、confidence、
  producer、subject/relationship/source body。package smoke 证明 Candidate pending→reject，外部 calls=0。
- 本机无 PostgreSQL/Docker，真库测试明确 skip；不能把本地 50 passed 或测试 target 写成公共 exactly-once。

## 2026-08-20：6B-5 公共 PostgreSQL 证据裁决

- 首个实现 run 的三个失败均是同一个 teardown 缺口，不是三种业务失败：测试专用 target 表的 FK 仍依赖
  Candidate 表，fixture 在删除测试表前先 downgrade。失败日志保留，避免把测试清理误写成生产缺陷。
- 最小修复没有使用 `CASCADE`，而是显式按 ownership 释放测试创建的表；这保持 migration 对未知依赖
  fail closed，同时让每个测试真正从干净 schema 开始。
- `dd7c9c8` / Actions `32376405150` 的 PostgreSQL `126 passed` 同时补齐 migration、FK/trigger、owner、
  terminal、materializer 原子回滚/重放/并发和 metadata-head 证据。普通 pytest 与 package 也全绿。
- 6B-5 可关闭，但只能声称“长期写入控制面和 typed materializer seam 已完成”；具体 Preference/Profile/
  Review Memory 仍属于 6B-6，当前未授权。

## 2026-08-20：6B-6 设计冻结发现

- 6B-5 的 `MaterializedMemoryReference` 只是 Candidate 的审计引用；只有 6B-6 三张真实 target 表存在时，
  `accepted` 才能代表具体长期记忆已物化。
- Owner Preference 必须按 `owner_id + memory_key` 做全局作用域；Candidate 仍保留 Conversation provenance，
  但不能把某次 Conversation 的 player subject 误当成 Preference 业务作用域。
- Player Profile 必须绑定 owner/relationship/subject，数据库和 materializer 都只允许 `self`；
  `public_observed` 不能因 candidate kind 名称而升级权限。
- Review Memory 的 `append` 语义若直接允许多个 active 行，会让 Context 选择和并发更难解释；6B-6 V1 采用
  “新版本成为 active、旧版本 superseded、历史可查”的 append，未来多 active 事件流需新 ADR。
- 由于 0005 Candidate 已公共闭环，本批不增加通用 Candidate 列；typed materializer 解析严格
  `value + expected_version` envelope，将 expected version 保持在提案层，目标只存规范化 value。
- 目标表需要 partial unique active index、source candidate UNIQUE、复合 FK、immutable trigger 和
  PostgreSQL transaction advisory lock；Fake/SQLite 不能证明这些数据库语义。
- 6B-6 更正不增加绕过 Candidate 的 PATCH；客户端先读取版本，再创建带 expected_version 的新 Candidate，
  由同一 gate/materializer 链完成审计和冲突返回。

## 2026-08-20：Task 1 合同发现

- 项目全局 Pydantic strict model 会拒绝普通字符串直接解析 StrEnum；公开 JSON 又天然是字符串，因此需要在
  allowlist 边界显式转换为 Enum，再交给 strict payload model，不能简单关闭 strict。
- 先做 shape policy 再做 payload schema 能产生稳定安全原因码；未知 key 应与允许 key 的错误 operation 分开，
  否则客户端无法区分“功能不支持”和“调用方式错误”。
- `expected_version` 是写控制字段，不进入 normalized target payload；bool 在 Python 中是 int 子类，必须显式
  拒绝，避免 `true` 被误解释为 version 1。

## 2026-08-20：6B-6 实现发现

- 只有 active row lock 无法串行“当前还没有行”的首次写入；scope/key 的 transaction advisory lock 与
  partial unique index 必须同时存在，前者提供确定顺序，后者兜住应用错误。
- target insert trigger 必须在 Candidate 仍为 pending 时验证 source kind/scope/key/operation/identity；外层
  Repository 随后才把 Candidate 改 accepted，这个顺序正好与同事务 materializer 合同一致。
- Owner Preference target 保存 Candidate 的 Conversation identity 作为 provenance/FK，但查询业务作用域只按
  owner+key；从不同 Conversation 更新偏好仍进入同一版本链。
- active/history API 如果开放直接 PATCH，会绕过 Candidate 来源/确认/版本审计；6B-6 因此只提供 GET，更正
  通过新 Candidate 的 expected_version 完成。
- public typed response 可以返回已批准 normalized payload，但不返回 PUUID、source Candidate、提案原文、
  producer/confidence、Prompt 或 SQL；这与 Candidate body-safe DTO 的边界不同但不冲突。

## 2026-08-20：6B-6 提交前复核发现

- typed payload/version 异常最初被误放在 Candidate create 的异常块；真实异常发生于 accept 内的
  materializer/write 路径，因此会被过宽映射为 Repository 503。最小修复把两项 disposition 转换移入
  `accept_candidate()`，让 payload invalid 保持 422、stale version 保持 409，事务回滚后 Candidate 仍 pending。
- 最后加入的 Review Summary metrics 和 100 条 page 上限需要直接合同测试；finite value、20 metrics 上限与
  101 条 page 拒绝现已固定，不能只依赖间接 API limit。
- insert trigger 已校验 pending Candidate 和 supersedes chain，但原真库测试只覆盖 kind mismatch/payload
  mutation；新增 terminal Candidate source 与跳号 version chain 两类 direct-SQL 负例，交由公共 PostgreSQL
  job 补证。它们不把本机 skip 冒充通过。

## 2026-08-20：6B-6 首个实现公共门发现

- Actions `32386630063` 的 PostgreSQL 唯一失败不是 target persistence 错误，而是测试案例 provenance 与
  6B-5 Gate 不一致：observed `public_trend` 不能使用 `user_structured_input`。这次失败反而证明 Gate 在
  server-derived observed identity 下没有被 materializer 绕过。
- 修复应调整测试输入为 `deterministic_run_fact`，不能为了让测试变绿而放宽 `evaluate_candidate_gate()`；
  其余真库合同当次为 141 passed，失败 SHA 必须保留。

## 2026-08-20：6B-6 公共闭环发现

- 最小测试修复后的 PostgreSQL `142 passed` 证明 observed trend 在合法 deterministic provenance 下可完成
  Candidate→typed target→accepted，同时非法来源仍由已有 Gate 测试拒绝；修复没有改变生产权限。
- package schema 1.3 的 accept→Preference query 是安装后真实纵向证据，但外部调用固定为 0；它不能外推
  Riot/Provider 质量、账号所有权验证或公网部署成熟度。
- 6B-6 关闭只完成 Preference/Profile/Review Memory；Training Plan/Progress 必须作为 6B-7 新检查点单独
  教学、设计、TDD 和公共验证，不能因共享 materializer 思想而自动算完成。

## 2026-08-21：6B-7 接缝审计与设计裁决

- 6B-5 gate 已为 `training_plan` 冻结 structured-input + user confirmation，为 `training_progress` 冻结
  deterministic-run-fact；6B-6 registry/writer 提供同 Session materializer 模式，无需新框架。
- 现有 Candidate source 检查只证明 task/run/Conversation identity，尚未证明 task succeeded、publication、
  report availability 与 final Artifact digest；6B-7 writer 必须在同一事务补上完整 Artifact gate。

## 2026-08-21：6B-8 Context 与 terminal turn 接缝裁决

- `ContextBuilderV1.build()` 只有 execution/knowledge/ceiling；Runtime request 也没有 Conversation identity。
  直接在 Runtime 外拼 ChatMessage 会绕过 canonical rendering、trust label 和预算，因此不可采用。
- `app/runtime/composition.py` 已允许注入 context builder，最小路线是 server-derived optional binding +
  run-scoped decorator；legacy request 保持 null/default Builder parity，不需要第二套 Runtime。
- Conversation schema 已允许 assistant 并强制 `source_run_id`，但公开 Repository/Service 只写 user；需增加
  internal terminal writer，并以 Task succeeded/publication/report/final Artifact/binding 重新验证后才写。
- `RecentFormReviewOutput` 当前没有 typed Memory proposal。为避免 Prompt Program identity 漂移和自然语言
  猜测，生产 6B-8 只持久化 terminal assistant；Candidate seam 只接受显式 typed proposal，默认空。
- Context manifest 适合作为 run data-plane body-free JSON：记录 ID/version/digest/count/omission，不保存正文；
  selector PostgreSQL 短事务在 Provider 前结束，manifest 写失败应在 Context 阶段 fail closed。
- pending Candidate 作为 Plan draft，可避免新增绕过 Candidate 的 draft CRUD；accepted Plan 才物化为 active。
- Progress 必须保留多次正常测量；只有纠错事件 supersede 指定旧 event，不能把“只保留最新 active key”的
  6B-6 Review Memory 版本模型错误套到时间序列。
- 趋势由 Plan direction/tolerance 和有限数值纯函数决定，只输出 improving/declining/stable/insufficient，
  不推断原因、心理或习惯。

## 2026-08-21：6B-8 公共门与 6B-9 lifecycle 接缝发现

- package smoke 必须让 API ActorContext owner 与 direct Repository/selector owner 来自同一隔离配置；只给 smoke
  容器设 owner 仍会与 API 的默认 owner 漂移。workflow job env 统一两侧才是正确证据。
- Profile fixture 的 `MID` 不是允许值；合法枚举是 `MIDDLE`。真实 PostgreSQL 失败证明 typed materializer 没有
  接受近似/别名，修复应改 fixture 而非放宽合同。
- Conversation/Message 与 Relationship 已有 hidden state，但 Candidate/typed target/Plan/Progress 没有；仅靠
  central tombstone join 会让 active partial unique 仍占位，删除后无法重建同 key active record。因此 0009 需要
  业务表 `hidden_at`，并同步 unique predicate 和所有 read/write source filters。
- FK 使 cascade hard delete 不适合：Task 独立引用 Conversation，target 引 Candidate，Progress 引 Plan/Task。
  正确顺序是先统一隐藏，再按 Progress→Plan→typed target→Candidate→Message 物理 purge；Conversation/
  Relationship/Player Subject 可以因审计/Task 引用保留 body-free hidden row。
- `relationship_private_data` 只删除 player-scoped 私有数据；owner-global Preference 不能因一个玩家关系退出而丢失。
  `conversation_and_derived_memory` 则按明确 provenance 删除该 Conversation 派生的 owner-global record。

## 2026-08-21：6B-9 实现审查发现

- Alembic 使用 `ck_%(table_name)s_%(constraint_name)s` 时，把已展开的 `ck_table_name` 直接传给
  `drop_constraint/create_check_constraint` 会再次套 convention；0009 必须用 `op.f()`，offline SQL 门能在
  无 PostgreSQL 本机提前发现双前缀。
- `conversation_only` 必须区分“历史可读”与“继续写入”：已确认 Candidate/长期 target 仍可查，但 Candidate
  accept 继续锁 source Conversation，hidden 后安全拒绝，避免删除后通过旧来源追加写。
- active partial unique 排除 hidden 还不够；版本 unique 仍存在。新链必须取历史最大 version + 1，同时让
  supersedes 为 null，明确表示 lifecycle reset 而不是把已删除记录重新连回公开历史。
- idempotency 并发 winner 写 marker 后，loser 的 unique race 应重新读取同 tuple 并 replay；只有 key 对应不同
  scope/target 才是 conflict。
- purge 遇 FK 阻塞应报告本批被阻塞 ID 数量，不应只按“一个表失败”计 1，也不能临时关闭 FK/cascade。

## 2026-08-21：6B-9 公共门与阶段 7 checkpoint 裁决

- 首个实现 SHA 的唯一真库失败不是产品缺陷：测试在 hidden 后执行 `status=active, hidden_at=NULL`，
  正确触发 `conversation_lifecycle_irreversible`。幂等/scope conflict 不需要重置 Conversation；删除该夹具
  比放宽 trigger 更符合产品合同。
- 修复 SHA 的公共普通回归为 `1490 passed/116 skipped`，与实现前本地 `1489/117` 不同；原因是该真库
  测试不再在非法 reset 处失败/跳过。两组计数必须分别按环境和 SHA 记录。
- package console 的 JSON 只打印 schema 1.6 与既有摘要字段，但同 SHA 的 executable 在成功返回前已严格
  断言 export schema/record kinds、conversation-only delete、Preference/Plan 存续；证据应表述为“job 成功
  执行这些断言”，不能声称所有 lifecycle 字段都出现在 console JSON。
- 路线已固定阶段 7 名称但未预建 checkpoint label。按既有 entry-design 命名规则新增
  `stage-7-standard-mcp-dynamic-meta-entry-design` 与 planned coverage/order contract，只作 prepared handoff；
  RQ-071 不授权阶段 7，因此不创建 ADR、代码或真实 MCP/Meta I/O。

## 2026-08-21：Stage 7 入口设计审计与裁决（RQ-072）

- 用户“那开始 stage7”只恢复 canonical 的入口设计检查点；`pause_reason` 已清空，但不等于授权直接实现
  MCP Client/Server 或执行真实 OP.GG I/O。
- `ToolDefinition`/`ToolRegistry`/`ToolRuntime` 已提供稳定的内部工具合同与 timeout/retry/cache/breaker/
  fallback/metrics；缺少 initialize、capability、tools/list、tools/call、session/transport，因此必须增加
  协议 Adapter，不能把内部 Runtime 或普通 HTTP 命名为 MCP。
- Application Service、Context/Memory、Harness/Runtime 接缝允许“Adapter → ToolRuntime → MetaEvidence →
  data-only Context/Skill/Harness”和“外部 Client → RiftCoach Server → owner-scoped Facade”两条边界；外部
  Meta 不得直接写 Memory、覆盖 owner/player 或改变发布门。
- OP.GG 尚未有仓库准入证据证明标准 endpoint/server、protocol/version、transport、schema、许可、patch/
  freshness、限流和真实互操作；当前只能是 candidate/deferred，若合同不满足必须另立 ADR 选替代方案。
- 推荐 Adapter-first 而非业务直 HTTP 或 SDK 渗透；后续固定 pure contract → transport/discovery → OP.GG
  Meta Adapter → RiftCoach Server → real interoperability exit review。

## 2026-08-21：Stage 7 入口设计公共闭环与交接

- `e50a546` / Actions `32436092074` 的三个公共 job 全绿，证明入口设计资产、治理和既有产品基线兼容；
  不证明 MCP Client/Server、OP.GG 准入或真实外部互操作。
- 入口设计 coverage 已完整登记八维材料并置 `complete`；按固定顺序新增
  `7-1-mcp-client-contract` planned coverage/order contract。
- canonical 下一检查点为 `7-1-mcp-client-contract` prepared/waiting authorization；授权前只保持文档，
  不写 pure MCP contract、transport、MetaEvidence 或 Server 产品代码。

## 2026-08-21：7-1 pure contract 接缝审计（RQ-073）

- 协议 envelope 与 transport 是两个独立失败域：前者验证 JSON-RPC/MCP method、版本、capability、schema
  和有限结果；后者才处理 stdio/HTTP、断线、deadline、restart 与 session 生命周期。本轮只实现前者。
- 现有 `ToolDefinition`/`schema.py` 已使用 Draft 2020-12 JSON Schema，Provider contracts 已示范 immutable
  schema snapshot、strict bool/int 与安全错误；7-1 可复用这些原则，但不能把 MCP 外部工具名强行当作
  内部 dotted-lowercase ToolDefinition，也不能提前复制 ToolRuntime retry/cache/breaker。
- `tools/list` 必须生成有界、唯一名称且 immutable 的 schema snapshot/digest；`tools/call` 同时检查发现目录、
  业务 allowlist、arguments schema 与 snapshot digest。目录变化时旧调用 fail closed，而不是按新 schema 猜测。
- JSON-RPC `error.message/data` 与 `tools/call isError` 内容都可能含 secret、Prompt 或上游 body；内部错误对象只保留
  allowlisted code、retryable、request id 和合法整数 remote code，不接受 raw body/message/data 字段。
- 7-1 测试/实现保持 pure no-I/O；没有 SDK、transport、OP.GG、MetaEvidence、Server 或真实互操作证据。

## 2026-08-21：7-1 实现审查发现

- 初版 focused green 后补齐标准 `Tool.annotations` 严格形状，同时让 description/title/annotations、arguments、
  result content、structured content 和 server instructions 从 repr 隐藏；必要业务数据仍可显式读取，但默认日志
  不会因打印 dataclass 泄露外部正文。
- 只限制 catalog/result 不够：arguments 即使满足 JSON Schema 也可能过大，因此 `McpContractLimits` 增加
  `max_argument_bytes` 并在生成 wire request 前检查 canonical JSON bytes。
- 只比较单 tool schema digest 会允许另一个 Server 的同形工具替换；最终 drift gate 同时绑定 catalog digest
  （含 protocol/server/tool identities）和 tool schema digest。任何 catalog refresh 都要求重新构造 call。
- pure Mapping 无法证明原始 HTTP/frame bytes；当前 canonical byte 限制只保护解析后的内存合同。raw frame/body、
  pagination aggregation、disconnect/restart/deadline 必须在 7-2 transport tests 单独证明。

## 2026-08-21：7-1 公共闭环裁决

- `37f16bc/32439753589` 三 job 全绿；公共 pytest 1510/116 skips 与本地 1509/117 的差异来自 Linux/Windows
  环境，必须分别记录，不能把公共较少 skip 改写成本机真库成功。
- PostgreSQL job 的 164 passed 和 package 1.6 是既有阶段 6 回归兼容证据；7-1 本身没有 migration/SQL/package
  业务变化，不能把这些 job 表述为 MCP transport 或外部互操作。
- 7-2 将负责 raw transport/session/discovery refresh，但当前仅 prepared；7-1 public success 不授权提前实现。

## 2026-08-21：7-2 transport/discovery 接缝审计（RQ-074）

- 7-1 的 `McpInitializeResult`、`McpToolCatalog`、`McpToolCallRequest/Result` 已足够作为
  transport-neutral parser；7-2 不应重新解析 JSON-RPC 或复制 schema/allowlist 逻辑。
- session 必须把初始化后的 protocol/server identity、tools capability、catalog digest 和
  transport generation 绑定在一起；generation 变化后旧 call 必须失效并要求重新 initialize。
- stdio 只采用受限 JSONL framing：单帧有界、串行 request/response、stderr 不进入业务结果；
  EOF、写失败、畸形 frame 和 deadline 都映射为 body-free MCP transport error。
- discovered descriptor 映射内部 `ToolDefinition` 时使用显式 adapter handler；handler 单次调用
  `McpClientSession.call`，重试、cache、breaker、fallback 仍只由 `ToolRuntime` 执行。
- 当前没有 MCP HTTP/Streamable HTTP 的标准版本与部署证据；本批只做 in-memory 与隔离 stdio，
  不把普通 HTTP 或 subprocess fixture 宣称为真实外部互操作。

## 2026-08-21：7-2 本地实现发现

- 分页 tools/list 的总 deadline 必须跨所有 cursor page 复用；每页重新开始 timeout 会让远端用大量
  cursor 消耗未受控时间。合并后的 catalog 重新按 protocol/server/schema identity 计算 digest。
- Stdio reader 使用单请求串行锁和 daemon readline worker；超时必须终止隔离进程，否则 reader 会在
  EOF 前继续占用 pipe。stderr 丢弃，不把 subprocess 诊断当作业务结果。
- Session generation 变化时先清空 initialization/catalog，再返回 `mcp_session_restarted`；重新
  initialize 是唯一重新绑定 server identity 的路径。disconnect 本身则保持 `mcp_transport_disconnected`。
- `McpContractError` 现在暴露 allowlisted `code/retryable/request_id` 属性，使 ToolRuntime 能按
  现有 `_safe_error` 合同处理 transport timeout；异常文本仍来自固定安全消息。

## 2026-08-21：7-2 公共闭环裁决

- `f121666/32441793585` 的三个 job 全绿；公共 `pytest`、真实 PostgreSQL migration/control-plane 和
  Linux no-I/O package smoke 均成功。该证据按环境记录，不把本机 117 skip 改写成真库成功。
- 7-2 只关闭本地 fixture/in-memory/隔离 stdio transport/session/discovery；OP.GG endpoint、协议、许可、
  freshness、限流与真实互操作仍缺证据，7-3 必须先做 admission audit。

## 2026-08-21：RQ-075 与 7-3 起始边界

- `opgginc/opgg-mcp` README、package 与源码已确认它是指向 `https://mcp-api.op.gg/mcp` 的官方
  OP.GG MCP 项目；仓库内 Node 入口是 Streamable HTTP → stdio proxy，不是数据后端完整源码。
- RQ-075 只授权 7-3。候选必须继续用 endpoint 协议响应、真实工具 schema、patch/freshness 和部署/限流
  证据复核；官方组织名与 README 单独不足以证明 Meta Provider 准入。
- 若准入通过，采用 strict per-tool anti-corruption adapter；若缺关键合同则按 ADR-0047 fail closed，
  不以普通 HTTP、推测字段或动态任意 JSON 规避门槛。

## 2026-08-21：RQ-076 对二元拒绝的纠正

- 用户正确指出：标准 MCP handshake/list/call 已真实成功，“没有上游 patch/TTL/outputSchema”证明的是
  provenance 等级有限，而不是 transport 或工具价值不存在。早先把两者合并为完全 deferred 过度保守。
- 新设计采用 partial provenance：本地 receipt time/TTL 可证明取回时间和缓存期限，但不能证明源数据生成
  时间；`upstream_patch/source_freshness` 必须为 unknown。应用只允许当前快照建议，不允许精确 patch/
  历史比较声明。
- 文本结果不能直接注入或 `eval`；必须锁定 remote schema digest、固定 desired fields、限制大小/数量，
  只遍历 allowlisted AST grammar。任何漂移、额外节点、非法数值或注入均 fail closed。

## 2026-08-21：7-3 真实目录 Bad Case 与产品 smoke

- 初次产品 smoke 在 tools/list 安全失败：当前 30-tool 全目录中两个未获准 Valorant 工具声明数组根
  outputSchema，而 7-1 parser 只接受对象根。OP.GG 可达、目标 LoL 工具也没有 outputSchema；失败发生在
  目录全量预解析，不是 lane-meta call 或 endpoint 故障。
- 采用最小权限修复：完整 response 仍先受 bytes/tool-count 上限约束，随后只对业务 allowlist descriptor
  建立严格不可变 catalog/schema snapshot。未获准工具不注册、不调用，也不再以异构 schema 阻断获准工具；
  新回归固定该 Bad Case。
- 第二次真实产品 smoke 从 Streamable HTTP initialize/notification/list 经本地 dotted ToolDefinition、
  ToolRuntime、allowlisted AST、typed MetaEvidence 到 data-only Context 全链成功；只调用 lane-meta 一次。
  `opgg_meta_product_smoke_v1.json` 保存 protocol/catalog/evidence digest、fact count 和限制，不保存 session、
  remote text 或英雄事实正文。
- 截至成功 smoke，本检查点合计 initialize 4、notification 4、tools/list 6、tools/call 2、DELETE attempt 4；
  其中包含初始 admission、一次失败前置 smoke、一次仅名称/schema 顶层形状的脱敏诊断和一次成功产品 smoke。
  Riot/LLM Provider calls 与 Key reads 仍为 0；这些单向调用不能冒充 7-5 双向互操作。
- RQ-077 又固定 Riot 官方事实并非只有 Match：账号/排位/比赛、Data Dragon 版本化静态定义与官方 patch/update
  应和 OP.GG 聚合 Meta 分层组合。7-3 不实现 join；缺 patch 的 OP.GG 不能继承同日 Riot patch 身份。
- 首轮完整回归的 26 项失败全部由基础 Context descriptor 指纹漂移触发：把 optional Meta extension 加进
  既有 Prompt Program V1 会正确阻断 composition，并连带使不可重跑的历史 held-out/资源校准身份失败。
  最小修复不是重写这些资产，而是让 external-meta 保持显式 extension；基础 descriptor/policy/fingerprint
  原样不变，未来生产注入必须发布新的 Meta-enabled Program identity。

## 2026-08-21：7-3 最终一致性与安全审查

- roadmap 总览、learning 索引、project decisions 与 ADR-0047 仍有入口设计时期的二元准入/7-2 当前句；
  已统一为“7-3 单向真实 OP.GG smoke + partial provenance，7-5 才是双向退出证明”，没有扩大到 7-4。
- `data/evaluation/results/mcp` 只有 admission 与 product-smoke 两个 JSON；定向扫描确认无 session id、raw
  response/result/content、PUUID、Key、Authorization、英雄事实正文或 class-like 远端文本。
- 最终聚焦/相邻为 `95 passed, 1 skipped, 17 subtests passed`；完整回归为
  `1542 passed, 117 skipped, 1 warning, 127 subtests passed`。唯一聚焦 skip 与其余本机 skip 继续表示
  无 PostgreSQL/Docker/Linux 对应环境，不能冒充真库/package 证据。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation
  均 1.0；Harness dry-run published/0 revisions；compileall、SDK boundary、tracked Secret/run-data、pip、
  YAML、governance、持久 evidence 脱敏和 diff 门均通过。

## 2026-08-21：7-3 恢复后的提交前合同补强

- Streamable HTTP 初版把 initialize 请求中的 client-offered version 写入后续 protocol header；当 Server 在
  Client allowlist 内选择另一个版本时会形成 header/已解析 session 不一致。新增红灯后改由 Client 在
  `McpInitializeResult` 严格验证成功后显式绑定 server-negotiated version，transport 不再窥探 MCP method。
- 初版 lane-meta parser 会用 `float(...)` 接受字符串 rate；这弱于“固定 typed scalar”合同。新增数值字符串
  负例并要求 rate AST Constant 原生为 int/float，bool/string/其他类型全部 fail closed。
- admitted-subset 初版虽跳过未获准工具的 outputSchema，却仍在 allowlist 前执行 descriptor exact-fields，
  未获准的缺字段/额外字段/非 mapping 条目仍可阻断 LoL 工具。新 Bad Case 先红灯，再改为“全响应 JSON bytes/
  tool-count 资源门 + 只按名称筛选执行权限 + 仅对获准 descriptor 严格解析”；无权限条目仍不能注册或调用。
- `MetaProvenance.COMPLETE` 初版没有反向要求 patch/source-generated identity，未来调用者可能仅凭枚举值高估
  证据等级。新增构造红灯后，complete 必须同时携带 patch 与 source time；partial 的 null/单用途合同保持不变。
- 补强后 MCP/Meta/Context 相关集合 `94 passed, 17 subtests passed`，完整回归
  `1545 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG、Harness、compileall、pip、全部 YAML、
  SDK/Secret/tracked-data、body-free evidence 与 governance 均再次通过。本轮没有新增 OP.GG/Riot/Provider/Key I/O。

## 2026-08-21：7-4 Server 接缝审计（RQ-078）

- 现有 FastAPI routes 已将 trusted `ActorContext` 注入 owner-scoped service；MCP Server 不应复用 HTTP
  body/owner 字段，也不应直接调用 Repository。最小接缝是独立的 `McpApplicationFacade` protocol，内部
  接收 ActorContext，外部只投影 allowlisted DTO。
- Server 复用 7-1 的 strict envelope/schema/result models；新增 Server Session 只负责请求方法、版本/能力、
  cursor、session lifecycle 和固定 error projection，不复制 ToolRuntime 的 retry/cache/breaker/fallback。
- 四个路线能力固定为 read-only `riftcoach.recent_summary`、`riftcoach.single_match_review`、
  `riftcoach.knowledge_search`、`riftcoach.report_evaluation`。前两个/后一个只接受可信 run identity，
  结果不含报告正文、Prompt、Provider/Tool body、PUUID 或内部异常；knowledge search 只经注入的
  provider/facade，不能由客户端指定 URL/路径。
- 7-4 本地 fixture 可以证明外部 client 与 Server envelope 的互相解析和 owner isolation；它不证明
  Streamable HTTP 部署或真实外部 Client，这些保持 7-5。
- Query seam 当前只能验证 Harness publication/evaluation 终态，不能恢复独立 evaluator score；第四个工具
  因此明确返回 `score_available=false`，不能因 published 自造 fact-check 分数。

## 2026-08-21：7-4 安全业务投影与本地退出发现

- 初版 `recent_summary`/`single_match_review` 只投影 run/publication 状态；协议虽正确，但不足以证明路线中的
  近期汇总。修正后 `RunQueryService` 交叉验证 receipt、Trace、manifest、Execution input commitment 与
  `PLAYER_SUMMARY` SHA，再输出无玩家身份/match rows 的真实 aggregate DTO。
- 单局 Skill 的 typed `target_match_id` 当前未作为独立 published Artifact 持久化；从 Markdown 反向解析会
  伪造结构化合同。V1 因此只返回正确 `single-match-review` Skill 的发布终态和 final report digest，明确
  不返回 narrative/target/score；未来若需要内容，先新增可审计 published-result Artifact。
- owner gate 在任何 Query 前执行；RunQuery 的 `run_not_found/report_not_available/integrity_failed` 分别映射为
  `not_found/not_published/integrity_failed`。Server 只复制 allowlisted DTO，Facade 额外字段被丢弃。
- TDD 红灯先后为缺少 `app.mcp.server` 和缺少两个安全 Query 方法的 `AttributeError`；最终聚焦 `33 passed`，
  相邻 `109 passed, 17 subtests passed`，完整 `1566 passed, 117 skipped, 1 warning, 127 subtests passed`。
- 两套 RAG 全部冻结指标为 1.0/FPR 0.0，Harness `published`/0 revisions；compileall、pip、6 YAML、SDK、
  tracked-data、body-free evidence、governance 与 diff 门全绿。本机 skip 不替代真库/Linux package 公共证据。

## 2026-08-21：7-4 exact-SHA 公共证据与边界

- `431c584c6f07731233e6e32fd6f98505a661f910` / Actions `32480827952` 的三个阻塞 job 全绿；
  exact SHA 与本地审查内容一致。
- 公共 pytest `1567 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning` 且 `alembic check` 无新 upgrade；Linux package schema 1.6/外部调用 0。
- package smoke 仍走既有 no-I/O 产品纵向，没有调用或部署 RiftCoach MCP Server；因此它不能替代 7-5
  真实外部 Client 证明。7-4 可以关闭，7-5 只 prepared/waiting authorization。

## 2026-08-21：RQ-079 与 7-5 互操作方案审计

- 官方 `@modelcontextprotocol/sdk` 当前固定候选为 `1.30.0`：npm package 与源码仓库身份一致，MIT，
  Node `>=18`；SDK 支持 `2025-06-18`，但初始化会首先提出最新 `2025-11-25`。RiftCoach 现有 Server
  只接受请求值恰好为 `2025-06-18`，这是真实外部 Client 才暴露的协商缺口，须先写红灯后按标准返回
  Server 支持的 `2025-06-18`，由 Client 决定是否接受。
- SDK stdio wire 是每行一个 JSON-RPC message；最小跨语言边界可用独立 Node Client 启动 Python runner，
  不需要为了退出证明新增公网端口、Auth 或 TLS。SDK/lockfile 保持在隔离 evaluation 目录，不进入 Python
  产品依赖；runner 使用 test actor 与 no-I/O restricted facade，只证明协议/权限投影，不冒充生产数据部署。
- 外部 Server 方向继续使用已产品化的 OP.GG Streamable HTTP lane-meta 链；RQ-079 只允许一次有界、零重试、
  body-free 重建。两侧证据均不得保存 session ID、raw content/result、arguments、PUUID、Key、路径或异常正文。

## 2026-08-21：7-5 TDD、SDK 交叉验证与本地门

- 首个红灯为缺少 `app.mcp.stdio` 的 collection error。官方 SDK 随后真实揭示协议 proposal gap：SDK 1.30.0
  提出 `2025-11-25`，Server 旧逻辑以严格相等拒绝；最小修复只准入冻结 proposal allowlist，响应/session
  仍绑定 `2025-06-18`，`2020-01-01` 既有负例继续 fail closed。
- `serve_stdio` 覆盖 newline framing、notification silence、duplicate key/invalid UTF-8/JSON/non-object、request/
  response size 和 EOF close。官方 SDK subprocess 实测固定 1 initialize/notification/list/call、3 responses，
  四工具目录与 knowledge result schema 通过；summary 只有 package/protocol/digest/count/limitations。
- lock graph 固定 public npm URLs、94 packages、MIT/ISC/BSD-2/BSD-3、无 install script；官方 registry audit
  为 0 vulnerability。该依赖只在 `experiments/mcp_interop` 和 pytest CI，不进入 Python/Docker runtime。
- 聚焦 `10 passed`，相邻 MCP/Meta `74 passed, 17 subtests passed`；完整
  `1576 passed, 117 skipped, 1 warning, 127 subtests passed`。两套 RAG 满阈值，Harness dry-run
  `published`/0 revisions；compileall、pip、Node、npm、YAML、governance、tracked-data、evidence 与 diff 门通过。
- 快速门首轮有三条无效组合命令：Node 在子目录重复路径、YAML `-c` 引号错误、证据 regex 把安全的
  `raw_body_persisted=false`/说明文字当泄漏；Node 组合还被后续 npm 成功掩盖 exit code。三者均无文件影响，
  已拆成独立命令并以 Node syntax、6 YAML、exact forbidden-key scan 真正通过；后续不把组合输出当证据。
- 本机 117 skip 仍是 PostgreSQL/Docker/Linux 环境限制；真实 OP.GG 7-5 调用尚未执行。下一动作是实现提交与
  exact-SHA 三 job，全绿后才允许 clean-SHA 双向门。

## 2026-08-21：7-5 实现公共门与 clean-SHA 双向真实证据

- 实现 `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 三 job 全绿：公共 pytest
  `1577 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL `164 passed, 1 warning`、
  migration metadata=head；Linux package schema 1.6/外部 Riot Provider 调用 0。
- 工作树、HEAD、origin/main 精确一致后，exit runner 在 2026-08-21T12:49:20Z–12:49:25Z 仅执行一次。
  官方 SDK→RiftCoach 完成 1 initialize/notification/list/call，4-tool catalog；Client 提议 2025-11-25，
  Server 协商 2025-06-18。摘要不含 actor/query/attribution/session/body。
- RiftCoach→OP.GG 完成 1 initialize/notification/list/call；Server `OP.GG MCP Server/1.0.0`、protocol
  2025-06-18、1 admitted tool、3 normalized facts。evidence 仍为 partial，patch/source time/freshness
  保持 unknown；Riot/LLM/Key I/O 为 0。
- 双向 evidence 绑定 product SHA `a88fbc4`，只含 identity、time window、catalog/schema/result/trace digest、
  count 与限制，目标文件拒绝覆盖。当前下一动作是证据/自动验证提交和 exact-SHA 公共门，Stage 7 尚未关闭。

## 2026-08-21：7-5 evidence 公共闭环与 Stage 8 canonical 命名

- evidence `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736` 三 job 全绿：
  公共 pytest 1578/116 skips/127 subtests，真库 164 且 migration/head 一致，package schema 1.6/外部调用 0。
- Stage 7 的实现/双向真实门/evidence 退出矩阵全部成立；7-5 coverage 与 Stage 7 可以正式关闭。
- 治理常量和 coverage 原先只到 7-5，仓库没有预存 Stage 8 checkpoint 名。为避免从聊天猜测，按固定
  路线标题“Multi-Agent、可靠运行时与产品化”和已有 stage-entry convention 登记
  `stage-8-multi-agent-reliable-runtime-productization-entry-design`，同时修改治理常量、ledger、路线和活动计划。
- 该登记只表示 prepared/waiting authorization；Stage 8 的 8-Core/8-Advanced 分解仍须入口设计，不提前
  选择 Multi-Agent/DAG，也不开始 cancel/resume、恢复、SSE/前端或部署。

## 2026-08-22：Stage 8 entry design 恢复与本地收尾发现

- 当前仓库证据与用户授权一致：Stage 7 已由 `fac6fe0` / Actions `32484257736` 正式关闭；唯一活动
  检查点是 `stage-8-multi-agent-reliable-runtime-productization-entry-design`，状态 `in_progress`。
- Stage 8 不是“默认上 Multi-Agent”。8A/8B 必须先记录 Bad Case、同切片对照、消融、成本、失败隔离
  与安全证据；没有独立上下文/权限/并行收益时，单流程 Runtime 或 `reject` 都是正确结果。
- Riot 官方账号/排位/比赛/Timeline、Data Dragon 静态和 patch/update 是事实层；OP.GG 只提供获准工具的
  当前聚合 Meta，缺 patch 时保持 `partial/current_snapshot`，绝不继承 Riot patch 或声称 upstream freshness。
- 前端五个模块必须把真实状态做成可解释展示：电影感 Riot ID 入口、近期复盘工作台、Rift Timeline、
  Evidence/Agent Trace 抽屉、Training Plan/Progress。视觉可采用自主 React 设计系统与逐项审查的外部
  效果，但 MotionSites 官网/用户 Excel 都只能是候选研究输入，不是产品运行时依赖。
- entry design 的八维证据已全部映射到有效持久 Markdown；本地门禁和 exact-SHA 公共 CI 是唯一剩余
  关闭条件。入口设计闭环前不得写 Multi-Agent、DAG、cancel/resume、recovery、SSE、正式 Auth、前端
  或真实外部调用代码。

## 2026-08-22：Stage 8 entry design 公共闭环发现

- `3431e8b/32564500421` 三 job 全绿，证明入口设计在 Linux、真实 PostgreSQL、完整回归、RAG、Harness、
  SDK/Secret/tracked-data 和 no-I/O package 边界下自洽；它没有把设计事实升级成产品实现事实。
- 本机完整回归为 `1577 passed, 117 skipped`，公共 pytest 为 `1578 passed, 116 skipped`；差异来自环境
  skip，真实 PostgreSQL 结论只由公共 `164 passed` 支持。
- npm 默认镜像的 audit API 返回 404；显式切到官方 npmjs registry 后为 0 vulnerabilities。这是镜像能力
  差异，不是依赖漏洞证据，也没有改 lockfile。
- canonical 可以安全前移到 `8a-advanced-adoption-gate`，但 RQ-080 没有授权 8A；prepared 状态不能解释为
  已开始候选研究或 Multi-Agent 实验。

## 2026-08-22：8A 候选审计与离线采用门发现

- 当前 `AgentLoop` 的多 ToolCall 会先整批做零副作用预检，再按返回顺序执行；独立 Knowledge/Meta
  evidence 的等待时间相加是可测收益假设，但它首先支持“普通并行 comparator”，不能直接证明需要 Multi-Agent。
- OP.GG Meta 最终以 optional data-only section 进入 Coach Context。schema drift、instruction-like payload、
  timeout 与跨角色工具探测适合作为隔离压力案例，但当前没有真实泄漏事故，证据等级必须保持 hypothesis。
- `ReviewHarness` 已拥有唯一发布控制流；把它改名为 Review Agent 会改变实验变量且扩大权限面，因此 8A
  固定所有执行角色 `can_publish=false`，Coach 也不得持有工具。
- running task 缺自动 lease/recovery 是 observed Bad Case，但正确路由为 8C Core。Saber/Sea 归档可作为
  role/DAG/Artifact/scheduler 方案检查，缺 Git 元数据且未执行，不能声称其 upstream commit 或运行质量。
- strict gate 的 case-set SHA 与 decision digest 稳定；当前 `external_io_calls=0`、`holdout_executions=0`。
  它只证明实验设计可执行，不证明 Multi-Agent 已实现、提速 20% 或通过 holdout。

## 2026-08-22：8A 公共闭环发现

- `12ad835/32567642315` 三 job 全绿，证明 strict adoption gate 在 Linux 完整回归、真实 PostgreSQL、
  no-I/O package、RAG/Harness 与安全边界下自洽；公共 pytest 与本地差 1 pass/1 skip 仍来自环境条件。
- 8A 输出中的 `candidate` 只表示“有资格进入 8B”，不是 adopted/production；DAG/Agentic Retrieval
  继续 deferred，lease/recovery 继续属于 8C Core。
- holdout executions 仍为 0，8B 的 20% latency/1.5x Token/+2 calls 没有被实测。canonical 前移到 8B
  prepared 不构成执行授权。

## 2026-08-22：8B 接缝审计与设计发现

- `ReviewHarness` 已经提供不可覆盖 artifact path、实际 bytes SHA 复核、唯一 publication decision 和安全
  deterministic fallback；8B 应注入 `DraftPreparationStep`，不能复制或弱化第二套 Harness。
- 现有 Harness 只原生持久化 `KnowledgeEvidence`，不应为了 evaluation experiment 修改产品 Artifact enum。
  8B 在隔离 evaluation namespace 内维护 Knowledge/Meta 的 typed materialized body 与 body-free digest reference，
  Coach 消费前复算 digest；Harness 仍接收其既有 `DraftPreparationResult`。
- 实际墙钟会被线程和机器噪声主导；8A case 已冻结 latency units，因此门禁使用确定性 critical-path 模型，
  同时真实执行最多双 worker 的并行控制流。Token/Provider calls 使用 Scripted Usage，不能冒充 tokenizer/费用。
- ordinary parallel 也必须做 branch exact-tool 和 typed Adapter 检查，不能故意削弱 comparator 来制造
  Multi-Agent 价值；如果 holdout 没有相对普通并行的增量收益，最终 reject 是正确工程结论。
- 正式 holdout 在实现 SHA 三 job 公共成功前禁止执行；development result 进入 ignored `tmp/` 并作为同 SHA
  holdout admission，正式结果用 exclusive create，crash sentinel 也会消费唯一执行机会。

## 2026-08-22：8B holdout 裁决发现

- development 的 candidate modeled latency improvement 为 27.05%，足以进入 holdout；calibration-excluded
  holdout 改为 slow Knowledge branch 后只有 18.95%，低于冻结 20% 门。不能拿 development 覆盖 holdout。
- 普通并行在同一 holdout 为 22.88%，Token ratio 1.05、无额外 Provider calls；Multi-Agent 为 1.45 和
  +2 calls/例。两者 match/safe degraded/isolation 都是 1.0，strict Adapter + typed Artifact + atomic tool
  preflight 已解决全部压力案例，没有观察到角色隔离的增量结果。
- 所以 ADR-0053 必须明确 reject 产品 Multi-Agent，而不是用“结构更先进”做 partial adoption；保留 runner
  是评测资产，不是生产采用。bounded parallel 只作为 8D 优先设计输入，8B 不提前改产品 Runtime。
- 结果绑定 code/public-CI SHA `180bc8b...0ce7`，文件 SHA `944258...445e8`，body-free scan/strict loader
  通过，holdout executions=1；任何删除、覆盖或重跑都会破坏证据链。

## 2026-08-22：8B 关闭与下一检查点

- result/ADR/evidence exact-SHA `783a329/32572610725` 公共三 job 全绿后，8B 的 reject 结论具备完整公开证据；
  不能因为普通并行有 modeled latency 收益就把它提前接入 8B 产品。
- 8B 的 `bounded-parallel-evidence-v1` 是 8D 的候选输入，8D 仍需独立考虑 Riot+OP.GG typed fusion、取消、
  deadline、预算、merge 和证据 provenance；Multi-Agent reject 不自动决定 8D 设计。
- 当前唯一下一检查点是 `8c-reliable-runtime-core` prepared/waiting authorization；8C 才处理 durable event、
  lease/fencing、cancel/checkpoint/recovery/late-result，不能被 8B runner 代替。

## 2026-08-22：RQ-083 授权 8C

- 用户明确“继续啊，咋停了”，授权 canonical 唯一检查点 `8c-reliable-runtime-core` 连续推进，不要求逐小步重复审批。
- 授权不改变 ADR-0053：8B holdout 不得覆盖或重跑，产品 Multi-Agent 继续 reject；8C 只扩展现有单 Runtime、
  PostgreSQL task/worker 与 Harness 接缝的可靠控制面。
- 当前先进行教学、源码接缝审计、2–3 方案比较、ADR/专用设计和实施计划；在红灯测试前不写产品实现，
  不进入 8D fusion、8E 前端/部署或真实外部 I/O。

## 2026-08-22：8C 设计复核发现

- task durable event 必须与 Runtime Trace 分层：前者是 PostgreSQL control-plane lifecycle/cursor，后者继续是
  immutable Provider/Tool/Harness terminal Trace；复制正文会制造双真源并扩大隐私面。
- 当前同步 Runtime 无法撤回已发出的外部 HTTP 请求，因此 cancel 的诚实语义是持久请求 + terminal fencing；
  不能宣称强制中断。自动 recovery 也只覆盖 `claimed_safe` 或 strict terminal Receipt，未知副作用 fail closed。
- 设计批完整/横向门未发现与现有 1625-test 基线冲突；真实 lease/fencing 并发仍必须等 0010 TDD 和公共
  PostgreSQL 17 job，设计绿灯本身不证明 8C 产品能力。

## 2026-08-22：8C 实现审查发现

- generation + private token + live expiry + status/cancel 共同组成 terminal fencing；只检查 worker_id 会在
  同名 Worker 重启时接受旧结果。token 必须留在私有 lease 对象与 Repository seam，不进入公共 replay。
- task event 与当前 row projection 必须同事务写；事件重试若 operation identity 相同但 envelope 不同，
  必须回滚整个 mutation。global cursor 不进入 SHA，才能在数据库分配 cursor 后保持内容 identity 稳定。
- Worker 的最后一次 heartbeat 与 terminal CAS 之间仍可能到达 cancel，因此 success/fail 返回 false 后要再做
  fenced cancel；若失败来自 recovery/new generation，该 cancel 也会失败并正确收敛为 ownership_lost。
- package 原先真实写入事件但未查询 replay；新增一次 owner-scoped event page 验证即可覆盖安装后纵向，
  无需提高 package schema 或引入 SSE。公共 DTO 也无需暴露内部 operation identity。
- Windows 最新完整回归 `1670 passed, 133 skipped` 不能替代真实 0010、concurrency 或 Linux image；这些仍是
  implementation exact-SHA 三 job 的阻塞关闭证据。

## 2026-08-23：8C 公共 CI 根因与修复

- PostgreSQL 0010 downgrade 使用裸 `ck_review_tasks_*` 名称时，Alembic naming convention 会再次生成 `ck_review_tasks_ck_review_tasks_*`；修复必须在 helper 内调用 `op.f()`，而不是放宽或重命名约束。
- SQLAlchemy PostgreSQL JSONB 默认将 Python `None` 编码为 JSON `null`；`checkpoint_reference` 的数据库 shape 需要 SQL `NULL` 才能满足 queued invariant，因此 ORM 使用 `JSONB(none_as_null=True)`。
- 新增 offline downgrade SQL、metadata 与 PostgreSQL queued-insert 回归；本机没有 PostgreSQL，queued-insert 测试按环境 skip，公共 job 是阻塞证据。
- 修复后本地完整回归为 `1672 passed, 134 skipped, 1 warning, 127 subtests passed`，两套 RAG、Harness、compileall、pip、SDK/Secret/tracked-data、governance 与 diff 门全绿。

## 2026-08-23：第二轮公共 CI 兼容性发现

- repair run `32584144522` 的 migration downgrade 与 pytest 已通过；PostgreSQL 真库仍有 34 个失败，根因是旧的 `succeeded/failed` 终态 fixture 没有 heartbeat 且 generation 保持旧默认 0，而 0010 CHECK 错误把运行期字段设为终态必填。
- 另一个链路问题是 Repository 把 `model_dump(mode="json")` 产生的 checkpoint 时间戳字符串直接用 strict `model_validate(dict)` 读取，导致 claim 在真库中变成 `task_repository_integrity_failed`；package smoke 因此报告 claim failed。
- 修复策略是终态 heartbeat 可空、运行期 heartbeat 仍必填，并在 JSONB 边界用 `model_validate_json` 严格解析；不改放宽业务 DTO、不删除 lifecycle CHECK。

## 2026-08-23：第三轮真库收敛

- `b2b4737/32584944802` 的真库结果为 `184 passed, 2 failed`；剩余 recovery requeue 仍调用旧 `model_validate(dict)`，与 claim 已修复的路径不一致。
- package smoke 的错误已从 claim 推进到 event query，说明 fencing/terminal/JSONB claim 接缝已成立；event replay 需要兼容 psycopg `Jsonb` wrapper 的统一 parser。
- `tests/test_task_product_vertical_postgres.py` 的 `timedelta` 漏导入只在公共真库执行时暴露，已补最小测试导入，不修改生产代码。

## 2026-08-23：第四轮 event replay 边界

- `424ba43` 的 migration 与 PostgreSQL job 已全绿，package smoke 报 `packaging_smoke_task_event_query_failed`；task JSONB parser 已通过 claim/requeue，event row 仍可能把 `None` 绑定为 JSON `null`。
- event ORM 现使用 `JSONB(none_as_null=True)`，保持 task/event 两个 control-plane projection 的空值语义一致；下一次公共 package job 是最终证据。
- 为定位仍未解释的 event query failure，smoke 仅增加 status/code/JSON-key diagnostics，明确不打印正文或敏感字段。

## 2026-08-23：8C clean implementation 根因与公共闭环

- `packaging-smoke` 的 Repository 诊断返回合法 `TaskEventPage` 且包含 6 个事件；API 503 的根因是
  composed deployment 的 `_TaskServiceProxy` 漏掉 `request_cancel` / `read_events` 两个可靠任务转发方法，
  不是数据库事件解码或公开 DTO 合同问题。
- 修复后新增 composed-app cancel/event 回归；`c7699f0/32587355051` 曾以临时安全诊断验证 package 通过，
  随后 clean implementation `2df5349/32587659678` 移除诊断并让三个公共 job 全部 exact-SHA 成功。
- 本地完整回归为 `1673 passed, 134 skipped, 1 warning, 127 subtests passed`。本机 134 skip 仍只代表没有
  PostgreSQL/Docker/Linux；真实 migration/concurrency/package 事实只采用 `32587659678` 公共证据。

## 2026-08-23：8D typed EvidenceBundle 本地发现

- RQ-084 已授权 8D；RQ-085 明确 README 研究需广泛采样且图不限定 SVG/Mermaid，但该横向任务不阻塞 8D。
- 现有 `app/lol` Summary 与 Data Dragon 仍是 dict/服务对象边界；Stage 7 `MetaEvidence` 已严格限制 partial
  provenance、TTL 和 allowed use，可直接复用，不应再写第二个 OP.GG schema。
- 无类型 JSON merge 会让 OP.GG 意外继承 Riot patch；通用 claim graph 又超出当前作品集规模。ADR-0055 选择
  immutable typed EvidenceBundle + pure fusion kernel，并保留来源 digest、join key、gap/conflict 和 claim。
- Pydantic 2 对带 `init=False digest` 的标准库 dataclass `MetaEvidence` 重新校验时会把 digest 当构造参数；bundle
  因而把已经验证的 immutable dataclass 作为 opaque tuple，再在 model validator 中显式做 `isinstance`，避免复制
  Stage 7 合同或放宽 arbitrary mapping。
- Riot/Data Dragon 中文名称需要 Unicode-safe label，而不能沿用 OP.GG 英文 champion regex；当前边界允许无控制字符
  Unicode 文本，并继续拒绝 instruction-like English label。public projection 不携带 PUUID、Key、raw MCP body 或 Prompt。
- focused TDD 首红为缺模块，修复 dataclass seam 后 `18 passed`；相邻 Meta/Context 合计 `48 passed`。尚未完成
  full regression、walkthrough、coverage 或 public CI，8D 不能关闭。

## 2026-08-23：8D 公共闭环事实

- implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` 的 Actions `32598480400`
  三 job 全绿；pytest 1692/133 skips/127 subtests，PostgreSQL 186，package schema 1.6/外部调用 0。
- 公共门只证明 typed fusion contract、no-I/O adapter 和现有产品/package 回归兼容；没有读取 Key 或调用本轮
  Riot/OP.GG/Provider/LLM，也不证明实时刷新、全工具、EvidenceBundle SQL 持久化或 8E 产品化。
- 8D coverage 可置 complete；唯一 handoff 是 `8e-productization` prepared/waiting authorization。

## 2026-08-23：8E preflight 发现

- 用户担心 fixture-only 会闭门造车；结论是 Stage 7 已有历史真实 OP.GG smoke，但 8D 纯融合内核仍需要独立的真实外部验证门。真实调用不能进入公共 exact-SHA CI，否则会把 Key、网络、限流和远端 schema 漂移混入可复现门。
- 本次真实 OP.GG smoke 使用官方 Streamable HTTP endpoint 和已准入只读 `lol_list_lane_meta_champions`，结果为 body-free、partial provenance、3 facts；没有 patch/source time/upstream freshness，因此只能 current snapshot recommendation。
- Riot 验证不能猜账号。仓库 `.env` 只检查到 Key 存在性，没有读取值；代码/文档没有 ShowMaker 硬编码。必须等待用户提供准确 Riot ID 与 regional routing。
- `CreatePlayerLinkRequest`/`CreatePlayerLinkCommand` 已有 `riot_id + routing_region + relationship_role`，并且 owner/player subject、Conversation 固定关系和 self/observed 语义已落地；但最终产品仍缺 owner-scoped profile list/selection DTO。
- 旧 `/reviews/recent` 的产品请求只含 Riot ID/count/queue/focus，summary builder 的 Riot region来自部署配置（默认 `asia`）。它应保留兼容性，但不能成为最终多地区 profile UX；8E 必须让选定 player subject/region 成为服务器可信来源，并禁止自动跨区探测。
- 前端按用户要求采用“合同和真实状态先行、动效后置”的批次：先静态/fixture-backed loading/empty/error/degraded/rejected/not-ready 状态和键盘/reduced-motion，再接 API/SSE/Auth，最后做入口叙事和高质量动效。

## 2026-08-23：真实 Riot/OP.GG preflight 结果

- AutoGLM token 服务恢复后，三个查询均返回 OP.GG 当前页面；`DK ShowMaker#KR1` 的 OP.GG 页面显示 Dplus KIA/ShowMaker 关联、KR、Challenger 和最近更新时间，TrackingThePros 也列出同一账号。`showmaker#KR126` 虽可查询，但页面显示低段位且没有职业关联，不采用为 ShowMaker 验证样本。
- Riot 官方 API 有界 probe 成功：Account-V1、recent match IDs、Match Detail 各一次；`DK ShowMaker#KR1` 解析为自身请求相同 Riot ID，目标比赛是 `MIDDLE/Akali`，game version `16.16.804.9184`。结果文件只含 PUUID/match digests 和 allowlisted gameplay facts。
- 为实现真实两源 join，第二次 Riot probe只补齐 `champion_id=84` 的 allowlisted projection，随后调用一次真实 OP.GG `mid` Meta。远端返回内容无法通过现有 grammar，适配器以 `opgg_meta_result_invalid` 安全拒绝；这说明“协议可达”不等于“当前字段解析与产品合同兼容”。
- 当前最重要的真实 Bad Case 是 `mid` lane-meta response shape drift。不要抓取或打印 raw body，也不要将 parser 放宽到任意 JSON/`eval`；应先做安全、字段级 schema-drift 诊断并用脱敏 case 固化。

## 2026-08-23：OP.GG schema-drift 诊断边界

- 真实 replay 的可复核 stack-level 事实是失败发生在 lane row 的字面量字段解析；没有持久化 raw MCP body，因此不能从一次失败臆测具体字段或 token。
- `OPGGMetaSchemaDiagnostic` 只暴露阶段、position/row、allowlisted 字段名/索引、AST 节点类型、长度和摘要 hash；`OPGGMetaError.__str__`/`repr__` 继续 body-free。
- 受控 `null` fixture 证明 `Name` AST 节点会在字段字面量边界 fail closed，但不证明 live OP.GG mid 使用该确切形状；live 字段级证据仍需新的明确外部授权。

## 2026-08-23：RQ-087 live 字段裁决与最小兼容边界

- 新授权窗口只复用既有 Riot body-free projection，执行一次 OP.GG `mid` call；结果仍失败，但新诊断明确为
  `Mid.rank_prev_patch`、field index 7、AST `Name`。live 正文长度 `2421`、digest `76b1f9...0820`，与
  受控 fixture 的长度/digest 不同，因此证据不是 fixture 回放。
- `rank_prev`/`rank_prev_patch` 的 typed contract 原本允许 `None`；JSON `null` 被 Python AST 表示为
  `Name(id="null")`，这是安全、可枚举的语法兼容点。ADR-0058 只在字段 6/7 接受精确小写 `null` 并立即
  投影为 `None`，不接受任意 Name、大小写变体、非 nullable 字段或表达式。
- 该授权窗口唯一 live call 已用于诊断；当前实现可由离线正/负例和公共 no-I/O CI 验证，但在新的明确授权
  进行最终 replay 前，不能声称真实两源 EvidenceBundle 已成功创建。

## 2026-08-23：RQ-088 修复后 live replay 结果

- 修复后一次 OP.GG `mid` replay 成功解析 10 条 facts，创建 body-free EvidenceBundle；这证明 JSON-null
  窄兼容命中了真实上游 Bad Case，且不需要放宽任意 Name/AST。
- bundle 仍为 `degraded`：Riot 样本英雄 Akali 没有出现在本次 OP.GG top-10 mid facts，故 join 为
  `unjoined/meta_join_missing`；replay 也刻意未加入 Data Dragon 与 official patch。该降级是正确业务语义，
  不能为了得到绿色 join 而换样本、扩大抓取或让 OP.GG 继承 Riot patch。
- 本次外部计数：OP.GG tools/call 1，Riot/LLM/Key 0，无重试；bundle digest
  `69ed8a...fff1a`，结果文件 SHA-256 `1dd803...54d1d`。
## 2026-08-23：8E Batch B 玩家档案与显式 Riot 路由

- 成功 Player Link 已经拥有 owner relationship、stable subject、显示 Riot ID、地区、角色与验证语义；复用它做 latest-success profile projection 比新增默认档案表更小、更一致，且没有 migration。
- `player_profile_id` 当前是 `relationship_id` 的 opaque 公共名称；Conversation 新字段以它为 canonical，旧 `relationship_id` 只作输入 alias。双字段同时出现必须 422，输出不暴露 PUUID、owner、task 或 fingerprint。
- legacy `/reviews/recent` 的 ambient `RIOT_REGION` 是真实跨区缺口。地区现在进入严格 HTTP DTO、task payload/fingerprint、Application/Executor 接缝；Conversation 路径从私有 SQL execution target 取地区。
- Worker 预建 `americas/asia/europe/sea` 四个 Riot Client 并 exact-select；没有 default、自动探区或 CN fallback。ShowMaker 只保留为历史 live validation 样本，产品不存在默认账号。
- 本机历史 PostgreSQL/Docker skip 的主要风险是提交前反馈慢，而不是公开关闭门缺失：相应阶段均有 exact-SHA PostgreSQL/Linux job。RQ-089 后已补齐 Docker Desktop、PostgreSQL 17 与 Linux Compose smoke；当前仅 Windows symlink 创建仍单项 skip。
- 本地数据库 URL/密码只保存在用户环境，不进入仓库；持久容器 `riftcoach-local-postgres` 绑定 `127.0.0.1:54329` 并采用 `unless-stopped`。

## 2026-08-23：8E Batch C 接缝审计与设计发现

- 8D `EvidenceBundle` 已有 full canonical projection/digest 和 safe public projection，但 `MetaEvidence` 是带
  `init=False digest` 的 frozen dataclass，不能把普通 JSONB dict 直接当作已验证对象；持久读回必须逐层
  重建 Meta fact/evidence 并重算 nested/bundle digest。
- 8C 的 `review_task_events` 已拥有 owner scope、global cursor、task sequence、event identity 和安全 HTTP DTO；
  SSE 应复用 `TaskEventResponse` 与 Repository replay，不能另造进程内队列或把 Runtime stream 当 durable truth。
- existing task deletion 先删除 SQL task row，event 已由 composite FK cascade；Evidence snapshot 使用同样
  `(task_id, run_id, owner_id) ON DELETE CASCADE` 可以自动遵守 terminal delete/retention，不必增加文件清理双写。
- Artifact/file store 会重复历史 SQL/文件 crash gap；reconstruct-on-read 会让 GET 隐含外部费用和 schema drift。
  ADR-0060 因此采用 PostgreSQL append-only revision + query-time expiry。
- 四态不能只照抄 TaskStatus：active=`not_ready`；failed/cancelled/Harness rejected=`rejected`；报告可用但
  publication/evidence 有限制=`degraded`；published + complete/current evidence=`published`。

## 2026-08-23：8E Batch C 实现发现

- 本机 PostgreSQL 容器正常运行，但新 PowerShell 不自动继承用户级变量；必须同时设置
  `RIFTCOACH_TEST_DATABASE_URL` 和 Alembic 使用的 `DATABASE_URL`。只设置前者会使旧 API migration fixture
  error，这不是数据库 skip 或产品缺陷。
- 第一轮 JSONB tamper 测试用 top-level shallow copy 后修改 nested list，ORM 比较到的值实际未变化；改为
  deep copy 后才真正写入篡改并证明 get_latest digest fail closed。
- refresh snapshot digest 包含首次 stored time，但 idempotency 的“相同内容”不能包含 retry time；Repository
  已改为 bundle digest replay，changed bundle 仍 conflict。
- evidence-first 多文件 collection 暴露 `app.api.__init__` eager composition 的循环导入；lazy package export
  与 task-local SSE allowlist 让 import order 不再影响 collection。
- package smoke 现在真实查询 product-state、missing evidence 与 terminal SSE，保持外部调用 0；前端仍未开始。

## 2026-08-23：8E Batch C Linux smoke 根因与本地关闭发现

- 首次本地 Compose smoke 的 `memory_context_unavailable` 不是 Memory Repository 回归：数据库 allowlisted
  identity 查询证明 API 以默认 `local-demo-owner` 写入 relationship/conversation/schema-2.0 task，而 smoke
  直连复核仍硬编码 `packaging-smoke-owner`；公共 CI 因 job env 显式对齐两者而没有暴露这个本地默认缺口。
- 修复让 smoke 与 API 共用同一个 `RIFTCOACH_LOCAL_OWNER_ID` 插值，并把 validated owner 放入
  `PackagingSmokeSettings` 后用于 task lookup、Memory binding 与 export assertion；没有放宽 owner 隔离或
  `_binding_exists()`。缺失/非法 owner 现在在网络和数据库前 fail closed。
- 无额外环境覆盖的全新 Compose project 已通过 schema 1.6 smoke，Memory Context 包含
  owner preference/training plan/message 共 3 条、terminal assistant 0、外部调用 0；容器非 root UID 999，
  `.env`/tests/cache/runs/reports/tmp 均未进入镜像，临时容器/volume/network 已清理。
- 最终本地为 focused `79 passed`、package contracts `39 passed`、CI-equivalent PostgreSQL
  `194 passed, 1 warning`、完整 `1888 passed, 1 skipped, 1 warning, 127 subtests passed`；唯一 skip 仍是
  Windows symlink 创建，必须由 exact-SHA Linux pytest 补证，不能在本机冒充通过。

## 2026-08-23：8E Batch C exact-SHA 公共关闭发现

- implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions `32629160732`
  的三个 job 均 completed/success；公共 pytest 为 `1750 passed, 139 skipped, 1 warning,
  127 subtests passed`，真实 PostgreSQL 为 `194 passed, 1 warning`。
- Linux package schema 1.6 延续 Memory Context 3 records、terminal assistant 0、外部调用 0，并通过
  非 root/image exclusion 与 Compose 资源清理；这补齐本地唯一 Windows symlink skip 的 Linux 侧证据，
  不把 Windows 本机结果改写为成功。
- Batch C 正式关闭，但整个 8E coverage 保持 `planned`。唯一 handoff 是 Batch D 静态/fixture-backed
  前端设计门 prepared/waiting authorization；Auth/RSO、HTTPS、备份、部署和生产 SSE 容量仍未实现。

## 2026-08-23：8E Batch D 合同与跨来源视觉审计发现

- 首批静态 screen 最适合 `Rift Command Center / 近期复盘工作台`：它能同时验证 profile、task/product
  四态、安全 Summary、Evidence 和 Training；电影感入口保留为后续高影响叙事，完整 Timeline 因缺 DTO
  不能提前伪造。
- 客户端资源状态必须是 `loading/empty/ready/error`，与产品
  `published/degraded/rejected/not_ready` 分开。`runtime completed` 不等于 `published`；Evidence rejected
  可能只让产品 degraded；observed 玩家不能展示“我的训练完成度”。
- `RecentSummaryView` 是 PUUID-free 安全投影但尚无 FastAPI endpoint；原始
  `examples/fixtures/player_summary_demo.json` 含不适合浏览器的字段，不能直接导入。Evidence public
  projection 的 OpenAPI 仍是自由 object，未来 API 接线前要加 runtime decoder 或收紧 DTO。
- 多来源两层采用门：许可/状态真实性/键盘/reduced-motion/移动降级/性能先作硬门；过门后视觉完成度、
  时尚感和记忆点占显著权重，不能把“最简单”自动判为最好。
- Motion 可直接采用；Radix 只承担 Dialog 语义。React Bits 当前 MIT + Commons Clause、Aceternity
  自定义 end-product license，均只学习机制不复制源码；Uiverse 逐项审查；Anime.js、GSAP、OGL/Three、
  ECharts 本批无真实需要而 deferred。MotionSites Excel 只作 metadata 索引且明显偏 Hero，不得决定工作台。
- UI 批评复核发现 `RecentSummaryView` 只有聚合指标、胜负聚合对照、主位置和英雄名称，没有逐局 DTO；
  因此原设计中的 match capsules 已在实现前删除，改为无顺序胜负占比与聚合对照。响应式也从单一 900px
  折叠改为 `>=1280` 三栏、960–1279 tablet 两栏、`<960` 单列，防止 1024px 拥挤。
- RQ-093 触发的 session-logs 定向回查确认，旧任务已完整冻结五模块：电影感入口、近期工作台、Rift
  Timeline、Evidence/Agent Trace、Training Plan/Progress。当前 Batch D 的工作台 + Drawer/Training 薄纵切
  是第一施工批，不是范围缩减；Image2/Photoshop 仍归后续入口素材，ECharts 仍归真实 Timeline 消费者。
- 旧技术组合中的 Next.js/Tailwind/shadcn 是早期建议，不是用户硬性指定；当前静态门用 Vite/vanilla CSS
  能减少 SSR/路由/模板依赖且保留自主视觉控制。Motion/Radix 已有直接消费者，其他库继续按采用门 deferred。
- 提交审查发现首个 web lockfile 继承本机 `registry.npmmirror.com` resolved URL；最终用 npm 官方 registry
  重建并 clean `npm ci`，避免 exact-SHA 公共门依赖个人镜像。第一次 mirror audit 404 同样没有冒充成功。

## 2026-08-23：RQ-094 上下文差异与 Live Integration 接缝发现

- 历史中存在三组容易混淆的“三案”：早期 visual draft、最终 `Rift Awakening / Esports Intelligence /
  Void Holographic Lab` 三方向，以及 Batch D 施工优先级三案。只有第二组及其
  `Cinematic Portal → Broadcast Workbench` combination 是最终视觉职责；`Rift Command Center` 只是 B 的
  首个施工切片，`Hextech Tactical Editorial` 是共享语言。
- 五项裁决中 Stage 8 顺序、Stage 7 V1、五模块和资源门已持久化；checkpoint 小复盘、OP.GG breadth 最低
  候选和完整真实 fusion golden slice 没有。当前只产品化 lane-meta；真实 replay 缺 Data Dragon/official
  patch、训练建议与 UI trace，仍为 `degraded/unjoined`。
- 后端已有 profiles、task/event/SSE、run/report、Product/Evidence 和 Training；缺的 identity seam 是
  profile→latest conversation-bound review。只靠 URL/localStorage 会串号，单一大 BFF 又会建立 UI 聚合真源，
  因此采用薄 locator + 现有 API 客户端组合。
- `RecentSummaryView` 已经通过 Artifact/Trace/manifest 严格查询，但没有 HTTP route；
  `EvidenceSnapshotResponse.projection` 仍是自由 object；这两处应在浏览器消费前收紧，不让前端解析内部文件。
- fixture 的战术 headline、Markdown 猜造 verdict/strength/priority/next-session、`2/5 sessions`、completion
  percent 与 next action 均没有现行后端字段。live 模式必须删除或改成可推导 Summary、verified Markdown 与
  baseline/current/target/trend/sample count。
- profile 切换必须先 abort fetch 和 close EventSource，再用 generation/profile/task/run guard 接受响应；
  SSE reconnect 是 client transport 状态，不是 Product State rejected。observed 不请求 personal Training。
- 当前消费 DTO 足够小，手写 exact decoder 比引入 Zod/codegen 更小；原生 EventSource 足够，不引入 parser。
  `react-markdown@10.1.0` 只有在 restricted elements、无 raw HTML/image/link 且总 JS gzip ≤150 kB 时采用。
## 2026-08-23：Batch D 公共关闭前 AutoGLM 可用性复核

- 本地 token 服务和 AutoGLM Web Search API 已连通；首轮 Windows GBK 输出因搜索摘要含 `U+00A0`
  发生 `UnicodeEncodeError`，设置 `PYTHONUTF8=1` 后同批查询正常返回。这是控制台编码问题，不是登录、
  token 或搜索服务失败，也不需要修改产品仓库脚本。
- 新查询继续返回 reduced-motion、dashboard/motion inspiration 与 agent observability 资源，但没有出现能
  推翻现有五模块矩阵或需要立即新增依赖/购买 Prompt 的新模式。当前合理裁决仍是跨来源筛选并把候选
  绑定到真实消费者；电影感入口、Timeline、完整 Training 各自在后续设计门再深挖。

## 2026-08-23：Live Integration implementation 发现

- 原生 browser `fetch` 不能直接保存后再作为 `ApiClient` 实例方法调用；Chromium 会以错误 receiver 抛
  `Illegal invocation`。用 `globalThis.fetch.bind(globalThis)` 保留 receiver，并增加 default-fetch 单测；
  network-boundary 仍只允许批准的 client seam。
- exact decoder 与 deterministic server DTO 并无首错；浏览器最初连第一条 `/api/player-profiles` 都未发出。
  先按 network ledger/trace 收敛到 pre-fetch，再用短暂本地诊断得到 receiver 根因，诊断日志未留在产品。
- E2E fixed test id 会让复用 server 的 terminal/request ledger 跨重跑污染；每次使用 UUID test identity 后，
  active→terminal 与 Training request count 可重复。Windows 10-worker 同时跑 live 与全页截图会整体资源饥饿；
  本地封顶 4，CI 保持 1，不提高断言 timeout 掩盖。
- `react-markdown@10.1.0` 安全配置正确，但 production JS gzip 156.52 kB 超过 150 kB 硬门；按 ADR 移除后
  使用 React 原生转义纯文本；提交前流式 body/selection hardening 后最终 122.01 kB。不能把该 fallback
  写成完整 Markdown renderer。
- 首次 Linux package smoke 在 conversation review 已进入 failed 后写 Evidence；production repository 正确
  返回 not-writable。修复把 write hook 放到 Worker claim 后、no-I/O executor 故意失败前，保留
  running/succeeded-only 写入 invariant、最终 failed task 和 typed Evidence 查询；事件顺序红灯与真实 Compose
  均通过。
- 提交前逐行 diff 审查发现，新 locator route 插入时把原属于 `/player-profiles` 的 generic exception 映射
  移到新 route 尾部并形成重复 `except Exception`。先补 RuntimeError 红灯复现异常泄漏，再把 body-free 503
  映射归位并删除重复分支；这证明完整绿灯仍不能替代提交前代码审查。
- 安全审查发现 `boundedText()` 只在 `response.text()` 完整缓冲后检查实际字节数；无 Content-Length 的
  chunked body 因而不是真正有界。新流式红灯证明旧实现会读过边界并失去 `api_body_too_large` 语义；现按
  chunk 累计字节、超限立即 cancel reader，保留 2 MiB JSON/1 MiB report 与 16 KiB error 原门槛。
- Controller 对合法 profile switch 会先 abort/close，但 invalid ID 原先直接进入 error，遗留 active stream。
  新红灯要求任何 selection 都先 begin 新 generation 并清理旧资源，再做 server-list membership 判断。
- Design/walkthrough 已写明“URL-valid profile else first”，Controller 也预留 `initialProfileId`，但默认 App
  composition 没有传入。浏览器红灯后，App 只读取 `player_profile_id` 作为候选，并仍由 owner-scoped profile
  list exact match 决定；URL 不能提供 task/run，也不会使 observed 请求个人 Training。
- 本机只有 `RIFTCOACH_TEST_DATABASE_URL`，完整 suite 中使用 Alembic 的旧 fixture 还要求同进程
  `DATABASE_URL`。按 CI 同源映射后完整 1939 与真库 200 通过；这不是产品配置放宽。
- exact-SHA `f441061/32647933692` 公共 pytest 为 1796/144 skips，而本地为 1939/1 skip；差异来自公共主 job
  不连接 PostgreSQL，真实 DB 语义由同 SHA 独立 `postgres-migrations` 的 200 项阻塞集合承担。Linux 主 job
  同时补齐 Windows symlink skip，因此不能只比较单个 pytest 数字判断证据变弱。
- preflight 的真实接线交接已经完成，按既定批次下一项是 Batch E 安全/部署；但其范围横跨 Auth/RSO、
  HTTPS/CSP/CORS/限流、backup/erase、隐私、观测和剩余五模块，必须先做独立 entry design/atomization，
  不能把一条“继续”解释成一次性配置生产系统。

## 2026-08-23：RQ-097 Batch E 安全/部署入口设计发现

- 当前 production API 的 `ActorContext` 只有可注入 provider；local/test 才允许静态 owner，production 无
  actor 时 readiness fail-closed。因此 Auth 实现应接在 Actor port，而不是在路由 body 接收 owner。
- 当前 `compose.yaml` 的 API/Worker/PostgreSQL 是模块化单机包，Dockerfile 未复制 `web/`；首个公开拓扑应由
  edge 提供静态 Web 和 TLS，API 只提供同源 `/api`，不要为了开发方便放宽公网 wildcard CORS。
- RQ-061/062 的关系语义继续有效：RiftCoach owner、Riot RSO 和 public observed 不是同一身份；RSO 未来
  必须 callback + `/accounts/me` 精确 PUUID match，CN/自动跨区/ShowMaker 默认均不允许。
- 6B-9 已有 online owner lifecycle marker，但 Artifact/backup 尚未纳入；Batch E 必须规定 restore 先重放
  deletion marker，未证明 erase 一致性前 readiness 不得通过。
- 当前 8C event、8E Evidence/SSE 和 Live Workbench 可作为观测事实源；新增指标必须保持 body-free，不能复制
  Runtime Trace、Prompt、raw upstream body 或 lease token。
- 视觉连续性不因安全批收缩：安全 hard gate 之后仍保留 `Rift Awakening → Esports Intelligence`，MotionSites
  只是候选池，Void Holographic Lab 仍是受限 Hero 实验。

## 2026-08-24：E4 restore/erase 接缝发现

- 6B-9 的 marker 只负责 PostgreSQL 在线数据隐藏；若 owner-scoped task 的 run 目录仍留在 Artifact/Trace
  volume，恢复或文件读取仍可能重新暴露已删除内容。因此 E4 locator 必须以同一 owner + conversation/
  relationship identity 精确筛选 `ReviewTaskRecord.run_id`，不能按 owner 全目录删除。
- `OwnerRunArtifactTraceCleaner` 复用已有 `FileRunDataCleaner`，保留 hidden-before-cleanup 顺序和
  body-free compensation marker；cleaner 只接受匹配目标，跨 owner 或错 scope 直接 fail closed。
- backup manifest 目前只保存 marker 元数据和 digest，`encryption=external_kms_required` 是明确的采用门。
  不创建伪加密文件，不读取 Secret，不宣称对象存储、KMS、RPO≤24h/RTO≤2h 已实测。
- restore 的幂等包装需要区分“本次 restore 新应用的 marker”和“历史已应用 marker”；readiness 失败时只能
  补偿前者，否则重复 drill 会把历史成功状态错误撤销。

## 2026-08-24：E4 公共闭环与 E5 进入

- `27b9256` / Actions `32660145945` 的三个阻塞 job 全绿，E4 的本地合同取得 exact-SHA 公共证据；
  这次公共闭环没有新的 Riot/OP.GG/Provider/LLM 调用。
- 下一批 E5 的真实问题不是再加一个基础设施名词，而是证明现有 Compose 的 migration order、API/Worker
  readiness、非 root image、rollback/structured body-free observability 在一次 package 交付中保持一致；
  Redis/Kubernetes/第二套 metrics stack 仍需 Bad Case 和 ADR 才能采用。

## 2026-08-24：E5 metrics seam 发现

- 现有 `TaskObservability` 已有 allowlist/event/latency 基础，但没有对外的 bounded projection；直接暴露
  内存历史会造成无界 payload 和隐私边界漂移。
- 最小闭环是 event counter + 最近 1000 个 latency 样本的 p50/p95 `/health/metrics`，仍然只输出 safe
  metric names/values；不把它扩展成 Prometheus exporter 或长期时序库。
- Compose 已有 PostgreSQL→migration→API/Worker 依赖与 readiness gate；E5 的 rollback 先固化为可审计
  runbook（旧镜像/兼容 migration/ready 后接流量），不声称自动回滚或跨区 HA。
## 2026-08-24：Portal → Workbench 视觉合同发现

- 当前 `web/` 已具备 live/fixture workbench、relationship-safe Training、Evidence drawer、Motion/Radix
  接缝；入口仍未实现，不能把 Batch D 的截图称为完整视觉产品。
- Image2 概念图适合表达深度、三路路径、Coach Core 和工作台 handoff，但其中伪文字/伪图表不能进入产品；
  必须拆为 atmosphere plates 与 CSS/SVG/DOM 层。
- 用户确认融合方向后，视觉复杂度可以主动提高，但采用门仍是硬门：真实状态、键盘/focus、mobile、
  reduced-motion、bundle、许可和可移除性。

## 2026-08-24：视觉 Task 3 与 Batch E implementation 发现

- 机械感的主要来源不是 Hextech 几何本身，而是 instrumentarium plate 的 `screen` 混合、高透明度和
  calibration panel 的重复网格叠加；改为低透明 `soft-light`、saturation/contrast 收敛、去掉重复网格后，
  金属结构仍在但不再压过 Rift atmosphere 与 Coach Core。
- Route 是产品状态 choreography，不是常驻装饰：idle/editing 静态或低频，calibrating 才流动，ready/degraded
  才显示一次 handoff；状态文案和 DOM 仍是事实源，reduced-motion 关闭连续/transform 动画。
- Session HTTP boundary 必须与 ActorContext 分层：cookie 只承载不可读 opaque token，owner 从 server-side
  session 解析；`POST /auth/session` 只返回一次 CSRF token 与 expiry，不接受 body owner；启用 session 后所有
  写请求由同一 cookie 绑定的 `X-CSRF-Token` 通过后才进入业务路由。未注入 Auth/RSO adapter 时返回
  `auth_unavailable`，production 不因为 local/test session primitive 而假装登录完成。
- Request budget 的 chunk/body/header 预算与单机 IP rate limiter 放在 ASGI edge seam；CSP 等安全头也覆盖预算
  rejection。该 limiter 没有多副本一致性，不能把内存 bucket 说成生产分布式限流；SSE 仍由有限 poll service
  保持终止，不额外引入第二 runtime。
- SecretSource composition 的关键是 key-last：Worker settings 只保留 provider endpoint/public config 与
  redacted SecretSource；PostgreSQL readiness 通过后才 resolve Riot/LLM secret 并构造 client。默认环境注入只
  是 local/test-compatible fallback；外部 Secret Manager adapter、PostgreSQL session repository、OIDC/RSO
  callback 和 backup/erase 仍未完成。

## 2026-08-24：Production shell/Auth gate 实施发现

- `create_composed_app` 已有 provider-neutral opaque session seam，但默认未注入 AuthSessionService 时必须
  返回 `auth_unavailable`；前端不能因为能渲染 live shell 就把 local/test session 说成生产登录。
- `AuthGate` 必须在 live controller mount 前完成 session issuance；否则 401 期间 controller 可能先读到
  profile，造成状态闪烁和错误的“无玩家资料”解释。
- auth failure code 必须和普通 `run_not_found`/`service_unavailable` 区分：expired/revoked/required 可
  重试且会卸载旧 controller，provider unavailable 则 fail closed 并保留配置缺失事实。
- CSRF token 本批只在内存中的 typed session projection 中保留，为下一 mutation seam 预留；不进入 URL、
  localStorage、report、Trace 或浏览器可读 cookie。

## 2026-08-24：E5 公共闭环与 production shell 交接

- `ca6da44` / Actions `32661425379` 三 job 全绿，E5 的 bounded metrics projection、Compose/readiness/
  package boundary 取得公共证据；没有新增外部 Provider、Riot、Secret 或网络 I/O。
- 下一产品施工切片是 production shell/Auth gate：先复用真实 API 的 session/CSRF seam 和现有 live/fixture
  decoder，明确未登录、加载、auth_unavailable、session expired 与安全拒绝状态，再决定前端引入方式。
- 真实 OIDC/RSO provider 仍需独立许可/费用/安全 adoption gate；不能因为做登录页面就把 local/test session
  或输入 Riot ID 说成 production authentication。

## 2026-08-24：RQ-103 视觉签收边界发现

- 当前 Timeline 已有真实几何、partial/unavailable、mobile、keyboard、reduced-motion 和截图证据，因此是
  可运行的高保真 V1；但冠军卡片只有 champion name、事件只有通用 marker，尚无版本化英雄/装备/目标资产，
  不能称为最终视觉成品。
- 直接拼 Data Dragon CDN URL 会把版本、locale、加载失败和缓存语义散落进组件。后续 enrichment 必须先
  建立单一 asset resolver/manifest 合同，再让 Timeline 与其它模块消费，才能安全补头像、图标和 fallback。
- 最终 polish 不只等于“加图”：还要统一色调、背景深度、布局节奏、面板材质、hover/focus/selection、
  中文 text expansion、移动降级和跨模块视觉叙事，并以全站截图/交互/a11y/bundle 门签收。

## 2026-08-24：RQ-102 bilingual foundation 入口发现

- 当前前端没有 locale runtime，静态 copy 分散在 App、Portal/Auth 和多个 Workbench 组件；同时 Evidence adapter
  还会把 canonical source/gap 数值提前拼成英文句子。双语不能只加开关，必须让 adapter 保留结构化值、组件
  render 时翻译。
- 现有 Memory 已有 `report_language=zh-CN|en-US`，但 final report Artifact/receipt 没有 run-scoped language
  provenance。UI 切换不能据此重写或猜测旧报告语言；本批只冻结“原文不机翻”和未来 producer 映射边界。
- 两 locale 暂不需要第三方 i18n runtime。typed local catalog 可用编译时 key completeness、版本化 localStorage、
  English fallback 和小 bundle 完成当前真实需求；未来 ICU plural/远程翻译平台 Bad Case 再评估依赖。

## 2026-08-24：RQ-105 三层旅程与 Player Link 发现

- 后端已有真实 `POST /player-links`、`GET /player-links/{id}`、`GET /player-profiles`，成功 Link 的
  `relationship_id` 就是 `player_profile_id`；前端旧代码丢弃 Riot ID 输入并跳 fixture，缺口在 browser
  mutation/controller/journey，而不是需要另造账号后端。
- POST 的 `public_observed` UI 语义必须显式映射 wire `observed`；202/replayed 不是成功。queued/running 只等待，
  succeeded 必须完整 identity 且刷新 owner profiles，failed 必须全 identity null + allowlisted failure。
- 默认 `create_composed_app()` 没注入正式 provider，因此 `/auth/session` 可返回 `auth_unavailable`。这证明
  Account UI 只能叫 provider-neutral access，不能画假密码框或宣称 OIDC/RSO 已完成。
- Product journey 不需要新 Router dependency；严格 query/history + mutually-exclusive mount 已足以验证 reload/
  back/forward，同时让 Portal zero-I/O 与 controller/EventSource 生命周期可审计。

## 2026-08-24：RQ-104 copy 与 RQ-106 视觉资产发现

- 用户表面最危险的“直译”不是单个词，而是 adapter/component 把 canonical role/metric/gap/status 直接当文案。
  保留 structured model、render 时 allowlisted mapping，才能让两种语言独立编辑且切换不重取数据。
- 一张含中央 core 的漂亮 keyframe 不能直接当 runtime background，否则与 DOM core 形成“双核心”。正确分层是：
  keyframe 只作 art-direction evidence，再精确移除 core/beam，React 提供唯一 interactive core。
- 老 instrumentarium 即使 opacity 很低，仍会把机械细节当作长期设计依赖。当前已移出 public；aperture 只在新
  background 加载失败时作为第二 background layer，最终仍可回退 CSS/SVG。
- 动效 V1 使用 bounded scene reveal 与一次性 handoff，避免用多组永久循环冒充高级感；reduced-motion 同时
  控制 CSS 与 JS 导航延迟。

## 2026-08-24：RQ-107 Coach/Training Agent 产品缺口

- 后端已有 Conversation、Message、conversation-bound Recent Review、AgentRuntime/Harness、SSE、terminal
  assistant、Memory-aware Context 与 Training Candidate/Plan/Progress；Web API client 却全是 GET，Coach 只是
  report 锚点。因此“项目有 Agent”与“用户能在产品里用 Agent”是两条不同证据线。
- 推荐方案不是开放域 LoL chat，而是 source-run/relationship-bound follow-up Skill + 专门 eval；生命周期 SSE
  后 terminal whole reply，Harness reject 不写 assistant。Training draft 先经用户编辑确认，再复用 Candidate/
  accept；observed 只给非持久学习清单。
- 该插入会调整 RQ-103/Evidence/Training 的后序，必须等用户集中裁决；当前批不临时塞聊天输入框。

## 2026-08-25：RQ-108 Portal Motion Polish 与母图水晶纠正

- 用户明确当前静态 WebP、压暗/虚化、大标题和可见 CSS/贴图 core 不能作为最终 Portal；foundation 公共关闭后
  固定先做独立 `portal-motion-polish`，当前 checkpoint 仍不变。
- 母图真值是左 Rift 旋涡 / 中央海克斯水晶 / 右战术星图的完整场景。水晶必须在这张场景内部重绘/调大并
  参与 ambient media，不能另生成一颗透明 cutout 再塞进可见按钮。
- 可访问交互仍由透明原生 `<button>` 覆盖水晶 hit area；视觉提示只用融景微光点/短脉冲，focus-visible 也应
  采用场景同材质的轻量能量轮廓。点击后由画面内水晶汇聚、burst 并幕切到独立 Account 动态场景。
- 正常体验候选是同源高清 poster + 有界 ambient motion/video；必须从首次 render 处理 mobile safe area、
  reduced-motion、Save-Data、codec/source、autoplay/playback/decoder failure、页面隐藏暂停、下载/解码/JS
  预算、许可和移除路径。当前 JS gzip 余量不足以无证据引入 Three/OGL/Anime。
- 早先生成的独立水晶候选明确不采用、不进入 foundation commit。RQ-108 只专项修正 Portal，不完成 Coach、
  OIDC/RSO、Data Dragon asset/detail enrichment 或跨模块 final visual QA。

## 2026-08-25：foundation 前端门最新结果

- 遗留 Vite 进程占用 `4173` 已确认来自 `D:\riftcoach-agent\web\node_modules\vite` 并清理；隔离 E2E
  随后完整通过，不使用旧服务。
- 最新可重复结果为 unit `136`、Playwright `36`、typecheck/build 通过，JS/CSS gzip `142.68/18.50 kB`。
- 这只证明当前双语与三层旅程 V1 的合同/状态/可访问性门；截图仍显示 Portal 视觉 V1，不是 RQ-108 成品。

## 2026-08-25：foundation 公共证据与 handoff

- `6084937/32757872792` 三 job 全绿让 bilingual/product-journey foundation 取得 exact-SHA 公共证据；本地
  截图的视觉不足仍由 RQ-108 处理，不能用公共 CI 反向宣称视觉成品。
- RQ-108 现在只进入 `prepared / waiting authorization`；它仍需自己的教学、设计、素材采用门、TDD、八维
  证据和公共 CI，不能复用 foundation 的绿灯冒充完成。

## 2026-08-25：RQ-109 授权启动 Portal Motion Polish

- 用户明确“开始”，授权 RQ-108；当前只先完成 motion/media 接缝审计、方案比较、ADR-0068、正式设计、
  实施计划和素材采用门，不把授权直接解释为视觉成品已实现。
- 采用候选先比较 full-video、CSS-only 与 hybrid poster/media + semantic hit target；既有证据倾向 hybrid，
  仍须用当前 bundle、移动/Save-Data/reduced-motion 和 asset provenance 审计正式冻结。

## 2026-08-25：RQ-110 高清母图与 anti-reference 纠正

- 用户明确当前暗化 Portal 截图绝不能沿用；`rift-portal-background-v2` 只保留历史 V1/anti-reference 身份。
- 正常体验应直接从确认高清母图制作全屏循环 background；同一母图导出的高清 poster 是 reduced-motion、
  Save-Data 与媒体失败 fallback。不得再加全屏阴影、vignette、blur 或为文字压暗画面。
- Portal 文案继续减到融景小型自有字标、语言控件和不可见可访问名称；水晶可点性只用微光点/短脉冲。
- 此纠正让 full-screen loop 成为主候选，而不是仅把媒体拆成局部小层；最终仍需 codec/下载/解码/mobile 门。

### 视觉文件复核

- 确认母图源完整保留左 Rift 旋涡、中央带水晶的高塔/基座、右侧战术星图和前景金蓝地面；亮度与局部对比
  已足以直接作为画面，不需要全屏暗幕。
- 当前 runtime background 已删除水晶，无法满足 RQ-110“直接从高清母图做动态 background”；它只能保留为
  历史 V1，不应作为 RQ-108 poster、loop 首帧或失败 fallback。
- `portal-motion-keyframe-v2` 比 runtime background 更接近母图，但仍是后续生成的不同版本；RQ-110 要求
  最终资产以用户确认原始母图为 edit target，不能用 keyframe-v2 悄悄替代。
- anti-reference 截图的问题来自整页暗化、边框/左上说明字和独立语言面板共同遮蔽画面，不只是水晶缺失。

### Account 第二幕母图候选

- 推荐“激活后的核心内殿”：Portal 水晶爆发后镜头穿入同一建筑内层；左侧保留稳定 Rift 能量窗/悬浮晶片，
  中间金蓝路径延续，右侧由画面构图形成安静金属/玻璃负空间给真实账号面板，不靠暗幕制造可读性。
- Hexgate 门廊转场顺但更像通用科幻登录；战术观星台视觉强但会抢占 Workbench 的战术语义，均列替代。
- Account loop 应比 Portal 更低频，只有稳定能量流、晶片微浮和远景呼吸；Portal transition 末帧需匹配
  Account loop 首帧。该项仍是设计推荐，需在 ADR-0068/概念母图审查后才采用。

### Account 与召唤师峡谷/英雄联动建议

- 推荐把核心内殿细化为 `Rift Attunement Chamber`：左侧能量窗呈现自主重构的高空峡谷拓扑，地面光路形成
  上/中/下三路与斜向河道，男爵侧用受限紫色节点、龙侧用青金节点；不复制官方地图 bitmap。
- 右侧仍由场景构图保留账号面板负空间，不靠 overlay。Account loop 只让三路/河道能量与少量节点低频呼吸。
- 用户随后纠正：固定英雄不构成问题；Account 可为上路/打野/中路/下路/辅助各固定一位英雄，但不得用头像。
- 五位英雄应成为峡谷光路周围的全身能量幻影/晶体浮雕/建筑级全息剪影，以姿态、轮廓和标志性物件识别；
  不放原画卡、头像框、英雄名或选角 UI，也不暗示用户主玩英雄。
- 当前视觉候选为 Camille/Kindred/Ahri/Jinx/Thresh，对应腿刃、双面具与弓、九尾、长辫与火箭炮、灯笼/钩链；
  roster 仍需结合概念图密度与许可边界正式冻结。

### 本地媒体能力与母图身份

- 用户确认母图为 `1672×941` RGB PNG、2,708,544 bytes，SHA-256
  `552a87453daae53762f56f0cb5f7c7c2fee18256ef6d193c00575283e9b7aada`；现有暗化 runtime background
  尺寸相同，但文件/画面身份不同，不能互换。
- 本机 FFmpeg 具备 `libx264`、`libvpx-vp9`、`libaom-av1`、`libsvtav1`；实现阶段可本地编码 MP4/H.264 与
  WebM/VP9 双 source，不需要为 codec 新增 JS 依赖。AV1 可作离线对照，不作为 V1 唯一格式。

### Riot 英雄形象采用门（官方公开政策，2026-08-25 复核）

- Riot `Legal Jibber Jabber` 为符合规则的非商业社区项目提供可撤销、有限的衍生使用许可，同时明确角色外观、
  地图、图标等进入 game/app 受更严格限制；公开项目必须清楚声明不是 Riot 官方项目。
- Riot Developer General Policies 要求第三方产品持续遵守最新政策、完成产品注册/合法 API 条件，并把
  Data Dragon 与 Press Kit 列为产品开发/营销可用来源；产品不得冒充或高度仿制 Riot 客户端。
- 当前仓库没有产品注册或官方免责声明证据。因此 RQ-111 可先制作/审查五英雄场景概念，但可识别角色形象
  进入 public runtime 前必须单独证明 API product/policy 条件、加入官方免责声明、记录来源/移除路径；否则
  使用同构原创五位置 archetype fallback。不能因“只是装饰”跳过许可门。
- 官方来源：`https://www.riotgames.com/en/legal`、`https://developer.riotgames.com/policies/general`。

### 第一轮 ImageGen 概念母图自审

- Portal edit `exec-b05c20ba-c796-4b37-9d75-0a74ffa9fa20.png` 保留了母图三段构图与曝光，但中央水晶远超
  要求，遮蔽塔体并改变视觉主次；拒绝作为 final/master，只保留 research rejected 记录。下一轮必须回到
  原母图，仅把原水晶放大约 15%，不能从巨型水晶候选继续漂移。
- Account concept `exec-1eca4fa8-66c0-4504-b19b-7fe34da3dbe5.png` 成功形成独立内殿、峡谷三路/河道
  能量盆地、五个全身英雄晶体幻影与右侧天然负空间；没有头像卡/名字/UI/暗幕。它可进入 preview 候选，
  仍需 16:9 crop、安全区、角色许可和用户视觉审查后才可成为 runtime source。
- 两次均使用 built-in imagegen；此时没有 runtime 采用、视频生成或前端代码变化。

### Account v2（官方原画参考）自审

- `exec-16a1f087-2e7a-42a2-b4e8-2b25671f4ddd.png` 虽使用确认母图与官方五英雄 splash 参考，并消除
  右侧走廊，但用户指出整体怪异、金克丝右脚/千珏下半身失真，人物仍像 splash 抠图换蓝后贴在地图上。
- v2 因此直接 rejected 并移出仓库；不再讨论“压低对比即可修复”，也不从该图继续迭代。
- 官方 splash 只是图像身份参考；可识别角色进入公开 runtime 仍受 Riot product/policy/disclaimer 采用门约束。

### RQ-113/114 Account 分层重塑流程

- 后续先生成无英雄、无右侧走廊的干净内殿/峡谷母图；五位英雄一次只处理一位并逐项验收解剖、手脚、
  武器、尾巴、面具与羊狼双体关系。
- 官方原画只锁定身份，不直接抠图或沿用 pose。每位要重新设计成与对应路线/基座/建筑遮挡/投影/反射一体的
  场景原生全身能量回响，材质由内部晶体、金色结构骨架、雾化边缘和环境光组成。
- 单体通过后再分层合成并做全局 loop；禁止单次生成同时解决场景、地图、五人和合成，也禁止简单蓝色滤镜。

### Account 无英雄底座 v1

- `account-rift-attunement-base-v1.png` 曾是分层流程第一张 preview candidate：
  1672×941、2,338,850 B、SHA-256 `ff70d6472f1376bee74e31a0498418d89248257b90891b86c0cc828de7e00af2`。
- 左侧为无英雄的峡谷三路/河道/紫色男爵侧/青金龙侧能量装置，右侧为无门洞/无走廊/无消失点的平整内殿
  墙面；没有暗幕、文字、UI 或人物，适合作为单英雄分层合成底座。
- 用户指出它几乎没有召唤师峡谷、只剩机械架子，因此已 rejected 并移出仓库，不作为后续生成底图。

### RQ-115 可辨识召唤师峡谷底座

- 下一底座必须以 Riot 官方 Data Dragon Summoner's Rift map 作地理参考，保留三路、斜向河道、两片野区、
  男爵/小龙坑、双方基地、防御塔以及森林/岩壁/河水关系；Hextech 只改变材质/照明，不能取代地貌。
- 内殿建筑应包围立体峡谷沙盘，五位英雄以后从对应路线/地貌中形成，不再设置五个通用机械 plinth。
- 官方 Data Dragon `versions.json` 当前首版本为 `16.16.1`；已校验并下载官方
  `cdn/16.16.1/img/map/map11.png`：512×512、70,985 B、SHA-256
  `5b446777c3e8491c1ab1860bc8fd448ad58f46cf3630d909f74dd3dc3dda8cd1`。它只作地理参考，
  不直接放大贴进背景；外部 URL 已通过 ClawDefender。

### Account 可辨识峡谷底座 v2

- `exec-146c7b66-cecc-4794-9a21-fa53836ad1e6.png` 使用确认母图作材质参考、官方 map11 作地理参考，
  已形成可辨识三路、斜河道、双野区、两坑、基地/塔/森林/岩壁/河水的立体峡谷，并由内殿建筑包围。
- 右侧约三分之一为无门洞/无走廊/无消失点的平整 obsidian 墙面，未用全屏 overlay；当前只等待用户对
  峡谷底座本身的视觉签收，未加入任何英雄、UI 或 runtime 动画。
- 若底座签收，后续五位英雄需从各自路线/野区地貌中逐个形成；不得遮蔽地图到再次不可辨识。

### Account 红蓝峡谷底座 v3

- `exec-2dd82754-04ec-43e3-821e-cc377816b24f.png` 只对 v2 做阵营语义修正：左下蓝方基地/塔/线路为
  青蓝，右上红方为绯红/暖橙；河道保持中性蓝、男爵坑紫色、小龙坑暖色，地形和右侧平墙未改变。
- 当前一眼可读 Summoner's Rift 地貌和双方阵营，没有 whole-frame 双色滤镜；仍是 preview candidate，等待
  用户对地形/阵营/留白整体签收后才保存为 Account source 并进入单英雄重塑。

### Riot 官方峡谷细节公开资料复核

- Riot 2024 map changes 官方文章确认墙体、草丛、路口与双方对称性需要大量精确迭代，并公开“接近最终的
  俯视地图概念”；公开图仍为 512×512 平面布局，不是可供精确重建每棵树/墙/塔的高分辨率正射地形母版。
- Data Dragon 16.16.1 map11 与官方 2024 near-final concept 足以锁定拓扑、河道、墙/草丛块和阵营方向，
  但不足以支持模型伪造写实微缩峡谷。用户提出的“笼统一点”因此是更诚实的视觉路线。
- 下一方案应把地图明确表达为精确拓扑的 Hextech 战术地形投影：保留可辨轮廓/三路/河道/两坑/基地和
  红蓝方向，用概括 terrain masses/contours 表达野区，不画位置看似具体却错误的微型树墙塔。
- 官方来源：`https://www.leagueoflegends.com/en-us/news/dev/dev-season-2024-map-changes/`；near-final
  concept SHA `8529f1b40b4d116082ba4f5ca6a4638c4ff9ca2d64d4deb57c486a2d54422459`。

### 用户提供 B 站 Kimi/MotionSites 流程复核

- 短链解析到 BVID `BV1AHd6BdEH7`，标题《跟我学，做个好看的网站不是很简单吗？》，时长 243.3 秒；
  研究副本为 1280×720 H.264/AAC、20,154,885 B、SHA-256
  `1e049dfa2932ff3df9b0b95d529e09d13d7d7cd131bb7d01b529eee5d8157310`，只存 workspace research。
- 视频实际流程分两条：先从 MotionSites 取得整站/动效 prompt 并交给 Kimi 等 coding agent 生成网站；再找到
  自己喜欢的图片上传 Kimi，要求“根据上传图片转化为循环视频”，生成/指定 ≤15 秒 MP4，随后把 MP4 上传
  到 Kimi Code 文件区并要求“帮我在首页替换成我上传的视频”。
- 因此 MotionSites prompt 主要提供网页视觉/交互模板，image-to-video 是独立资产生产步骤；视频最后仍作为
  普通本地文件进入网页。该演示没有展示 codec 双格式、真正首尾 seam、Save-Data/reduced-motion/media-error、
  文件/解码预算或 static edge header 门，这些是 RiftCoach 必须补的生产化差异。
- B 站页面无公开字幕，内容通过官方 metadata/playurl API、固定时间帧和画面字幕复核；短链/页面/API/CDN
  均先过 ClawDefender 或严格官方 hostname/size/类型校验。

### RQ-112 全局循环动态纠正

- 用户明确“动态 background”是全帧循环动态，不是全屏 video 容器内只有 Rift/水晶/星图几个局部在动。
- Portal loop 必须同时覆盖 Rift/云雾/远景、整条道路/前景反射、建筑缝线/平台/水晶、星图/节点/粒子和
  多层环境光；Account 也要覆盖峡谷路径、英雄幻影、内殿光线、粒子和反射，只是运动节奏更安静。
- poster 仅限首帧/降级；DOM/SVG 只承担可访问提示与点击后的收敛/burst，不能成为主要动画来源。
- 全帧运动会提高码率与解码成本，ADR-0068 必须放宽旧“局部运动”估算并以实际编码质量/文件大小裁决，
  不能为了旧预算把视觉目标悄悄缩回静态。

## 2026-08-25：RQ-117/118 与 RQ-108 design gate 收口

- RQ-117 将 Account 地图冻结为“官方精确拓扑 + 有意概括的 Hextech 战术地形投影”：map11/near-final
  concept 只支持三路、河道、双野区、双坑、基地、朝向和阵营等宏观锚点，不支持模型臆造写实微细节。
- 当前 v3 即使缩略图可辨识，仍因 pseudo-real terrain 未通过 100% 细看与 annotated topology overlay，保持
  unaccepted preview；不进入英雄层、视频层或 runtime。
- RQ-118 取代早期水晶放大/重绘要求：确认母图原水晶、塔体和构图保持 source truth；两张放大 edit 以及
  独立/CSS/贴图水晶均不能成为 edit target 或发布资产。
- 媒体初始资格与播放状态必须分开；motion/poster 两个 policy 分支都携带 desktop/mobile。reduced-motion/
  Save-Data 首次 render 不创建 video/source，play/decode/resume failure 进入 session-sticky poster。
- 母 PNG 是逐字节 archival source；runtime poster 可以压缩，但必须绑定 source SHA 并通过 SSIM/人工原尺寸
  感知一致性，不能用暗化/模糊换体积。
- ADR-0068、正式 design、详细 TDD implementation plan、asset ledger 与八维 planned walkthrough 已建立；
  当前没有 `web/` runtime 变更。下一动作是 design commit/exact-SHA，不再被逐张 preview 打断。

### RQ-119/120 Kimi Bad Case 与视频路线扩展

- Chrome `localhost:7100` 实际播放 `hero-loop.mp4`：H.264 High/yuv420p、1920×1080、30fps、12s、约
  4.03Mbps/6.05MB；video ready/play 正常、CSS filter none，因此问题不只是网页没加载或 CSS 模糊。
- 生成首帧相对母图等比 resize SSIM `0.412818`，人工帧组看到 left Rift/right star map 被重新取景、水晶/
  塔体和纹理随时间重绘；loop seam 本身不比末相邻帧显著更坏，但能循环不能弥补 source fidelity 失败。
- Kimi v1 记录为 rejected Bad Case，不把所有 Kimi 配置永久判死，也不再默认采用。正式 bake-off 使用同一
  source/brief/scorecard，比较 Wan 2.7、Seedance、Veo、Luma、Runway/Firefly 等生成路线。
- HyperFrames 与 Remotion 不是 I2V 模型，而是确定性逐帧制片框架。HyperFrames 为 Apache-2.0、HTML/
  seekable animation、官方主 skill 安装量约 240K/仓库约 41.8K stars；Remotion React 生态成熟但许可需按
  组织规模复核。推荐候选是先分层/inpaint，再用生成式有机 loop plates + deterministic architecture composite。
- 当前只记录候选，不安装 skill、不购 credits、不创建 Key、不调用付费模型；任何 adoption 仍需安全审计、
  隔离 spike、质量/许可/维护成本和新 ADR。

### RQ-121 官方优先与中转 secondary transport

- 用户正规中转目录扩大了 Seedance/Kling/Grok/Hailuo/Sora/Veo/Vidu/Wan 的可达候选，但截图里的 model slug、
  `official`/quality/vip 后缀和单价不是厂商身份、能力或直连证据。
- bake-off 仍 official first；relay 必须先验证 model/version mapping、首尾帧/reference 合同、无静默压缩/水印、
  隐私/保留/删除/训练、地区、错误/重试/计费和有界 body-free provenance，无法验证则 catalog-only。
- 站内列表可能滞后，正式横评前重新查官方最新模型；本补充不打断 Task 1，也不授权上传母图、创建 Key 或付费调用。

## 2026-08-25：RQ-122 official/relay 广筛与 HyperFrames 隔离 spike

- `RELAY`：DragonAPI 专用文档证明统一异步 `/v1/videos`、显式 first/last/reference、轮询/下载与多模型页面；
  但目录计数、通用响应示例、Grok 广场 API 页和价格币种存在不一致，已写入
  `docs/plans/2026-08-25-8e-video-bakeoff-relay-admission.md`，不把这些矛盾隐藏成准入事实。
- `OFFICIAL`：用户官方 Model Studio UI 显示 `wan3.0-video`、`立即体验`、`调用 API`，并确认邀测已通过；
  Wan 3.0 成为 A1，relay 未启用不再被误读成不可用。Grok `grok-video-3` 第三代由模型广场/价格页/通用视频
  示例证实，站内全文仍缺专用 schema；上游官方当前公开名称是 `grok-imagine-video` 系列，故暂不假设 alias。
- `HYPERFRAMES`：general-video 全文件审计发现强制 online update/auth/provider 与默认 PostHog telemetry，skill
  as-is 不准入；exact `hyperframes@0.8.14` 隔离安装、临时 HOME/no telemetry/no auth/no cloud 下 cached
  headless shell check 通过。系统 Chrome profile singleton 是可复现 Windows Bad Case；默认 MP4 bytes/seam
  失败，raw snapshots 逐字节确定且 seam SSIM `0.999600`。裁决 renderer conditional pass/default encoder reject。
- `NEXT`：Wan 3.0 官方 endpoint/region/Key presence body-free preflight；不读取 Key 值，不上传母图，不创建付费任务。

## 2026-08-25：RQ-123 executable preflight

- `IDENTITY`：千问AI平台签约主体/阿里云账号体系与官方 DashScope endpoint 已核对；Wan standard/prime 可用，
  用户邀测 access、当前免费视频额度与 existing Key presence 均成立。DragonAPI 也有 existing masked Key。
- `AUTHORIZATION`：用户明确 official 与正规 relay 都可实际试用，不因补充某一模型遗忘候选；不逐调用再问。
  安全收敛仍是一候选一调用、首错停止、不充值/订阅/批量重抽。
- `PROMPT`：source SHA `552a874...aada`；本地 prompt 1662 bytes，SHA
  `f324264150a729daad5e7be71d5e762e8fec496d98e94ffebd2fdddcbd2f36fc`。内容逐层绑定左 Rift、道路/反射、
  原水晶/塔体、右星图/节点/粒子/环境光，locked camera、8 秒首尾同相位。
- `NEXT`：preflight exact-SHA 公共门；公共成功后先 Wan，再 Dragon/Veo。
- `ACCOUNT-ORDER`：当前 v3 仍 preview/blocking。Portal bake-off 只选制片方法；完成两个样本后必须回 Account
  source gate→五英雄逐位→adopted source→10s loop，不能跳 Task 6/Coach/RQ-103/8F。

## 2026-08-26：RQ-124 Portal source v2 migration

- hash 证明用户再次贴出的“小水晶图”与 v1 canonical 逐字节相同；“大水晶图”是另一 SHA 的后生成、后拒绝 edit。
- 强清噪与轻清噪两项 built-in ImageGen edit 分别得到 parent SSIM `0.753497/0.859593`；用户签收轻版。
- v2 SHA `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`、2,268,033 bytes、1672×941；
  v1 保留 archival parent，RQ-118 小水晶/塔体/构图不变。
- auditor 新增非-fixture exact path gate，避免 planned/adopted ledger 只换 SHA 却回退 v1 文件；红灯 22 failed 后
  绿灯 26 passed。下一动作是 v2 source migration public gate，不先上传 Wan。

## 2026-08-26：Wan 3.0 v2 first/last 单样本

- `2a2da0e/32872452053` 三 job 全绿后才上传 v2。首轮 UI prompt 未落盘并水合失败，quota 100%、无结果，calls 0；
  修正为 mode-first→prompt readback 1661 chars→两帧→六项核对后只创建一次有效 task。
- output `030a60f...1f58a`，2,057,453 B，8s/240 frames/1918×1080/30fps/H.264/yuv420p/no-audio；quota
  100%→73.33%。
- source→first `0.860852`，first→last `0.902413`；adjacent DSSIM p95 `0.005222`，seam DSSIM
  `0.097587 > 0.03`；AI watermark 可见。
- first→4s regional SSIM left/center/right `0.898092/0.884466/0.861069`，像素有变但人工只见局部亮度/纹理
  微动，未形成 RQ-112 的 coherent full-frame motion。Wan 结果 rejected，不重抽；下一项 Dragon/Veo。

## 2026-08-25：RQ-108 runtime Task 1 TDD 发现

- strict runtime manifest 采用 schema `1.0` + 四项 scene/viewport matrix；asset file identity 固定
  `scene-viewport-poster|loop`，兼容当前 Vite root/dev 与 `name-hash.ext`，拒绝 remote/data/query/fragment/
  traversal 和重复 URL。当前不支持未来 `base: './'`，因 Vite 仍为根基址，记录为非阻断兼容边界。
- cover geometry 的关键公式是 `scale=max(container/source)` 与 `offset=(container-rendered)*objectPosition`；
  object-position 百分比作用于剩余空间而不是把 source 点直接放到 viewport 点。hitBox 不裁切以保持像素对齐。
- 初版 hook 的 passive-effect subscription 真实允许 render→commit 竞态先提交 motion；独立审查红灯复现后，
  改为 cached `useSyncExternalStore` + `poster/preflight`，subscribe-then-read 才允许 motion。旧 Safari/iOS 的
  `addListener/removeListener` 也增加对称 fallback。
- 低优先级边界：decoder readonly 是 TypeScript 不变量，未 deep-freeze；当前仅内部可信消费，不扩大实现。

### Task 1 公共证据与 Task 2 接缝

- `1b146e6/32826953474` 的三项公共 job 全绿，证明 Task 1 在 Linux、真实 PostgreSQL 与完整前端/后端门上没有
  隐藏平台回归；该公共证据不增加 `<video>`、媒体下载或视觉完成度。
- Task 2 必须保持两个维度分离：`PlaybackState` 是不可逆失败终态，`userPaused` 是正交用户选择。暂停、
  visibility 或 policy 改变都不能把 `failed-sticky` 恢复成 loading/playing；整页 reload 才建立新 session。
- 独立只读审查纠正了设计中的迟到失败歧义：只有当前有效 attempt 的真实 error/play rejection 才 sticky；
  unmount、policy/source/viewport replacement 后旧事件和 Promise 结果必须忽略。否则 React StrictMode 的
  setup→cleanup→setup、正常导航或 `pause()` 中止 pending play 都可能错误毒化 session。
- Task 2 实现复核又发现两个具体接缝：poster/video 兄弟节点不能共享 React key；卸载保护不能只依赖 ref
  自动清空，必须显式维护 mounted 与 active-attempt 门。两项已修复并由 detached `canplay`、detached poster
  error 和 StrictMode 测试固定。
- `2111a78/32833608622` 的 exact-SHA 三项公共 job 全绿；Task 2 的公共证据确认这些生命周期门在 Linux、真实
  PostgreSQL 与完整回归组合下没有破坏既有产品。Task 3 是唯一下一项，不能因组件已存在而提前接入 App。
- Task 3 审计确认 timer 必须由 `ProductJourney` 持有：子场景卸载不应丢失 committed overlay，且 StrictMode
  effect 重跑不能再次 `pushState`。generation ref、navigation latch 和 popstate cancellation 已固定该边界。
- Task 3 不签收最终视觉：现有 AwakeningScene 的旧 CSS crystal/orbit/label/H1/lede 与临时 overlay 暗场仍是
  V1 fallback，明确留到后续 production media/Task 5–6 组合门；本批只签收 activation semantics、focus 和
  navigation 生命周期，不能把它写成 RQ-110/RQ-118 的最终画面。
- `0198fc9/32836430378` 的 exact-SHA 三项公共 job 全绿；Task 3 的公共证据确认 focus handoff、Save-Data 短路径
  和 Workbench 导航清理没有破坏既有 PostgreSQL/Linux/全量回归。下一检查点严格切为 Task 4。
- Task 4 设计审查确定：planned ledger 必须保留可验证的 Portal source SHA、阈值、预算和 anti-reference SHA，
  不能用全空 pending 文件；审计 CLI 不接受任意可执行路径，固定使用 PATH `ffprobe`，避免命令注入边界。
- 本机无 numpy/PIL/skimage，故 SSIM/seam/dropped-frame 作为外部测量证据字段做阈值校验；审计器不伪装成图像
  质量生成器。真实 adopted media 的 ffprobe JSON 仍须在 Task 5/6 资产门产生并绑定 provenance。
- 首个 Task 4 公共 run `32841579832` 证明 GitHub Ubuntu job 未预装 ffprobe；CI toolchain fix `d58ba15` 安装
  ffmpeg 后，run `32841900909` 三 job 全绿。该失败保留为可解释的环境 Bad Case，审计门与 planned ledger 未放宽。
- Task 4 exact-SHA 公共闭环确认 planned ledger、审计器、前端 bundle 和既有 PostgreSQL/Linux 门可在同一 SHA
  重建；Task 5 才允许进入真实候选横评，不提前上传母图或读取 relay/provider Key。
- Task 5 官方资料复核得到三个可用但层级不同的候选：Veo 3.1 的 first/last API 控制明确，Luma 当前 API 有 loop/keyframes，Wan 2.7 支持 first/last/continuation 但区域绑定；Seedance/中转目录暂列 catalog-only，不把 slug、价格或 `official` 后缀当作 provider capability 证据。

## 2026-08-26：Dragon/Veo 样本、motion prompt 与 RQ-125 纠偏

- Dragon/Veo 仅创建一个 task；控制台记录成功/100%/162s。公开 `/content` 对同一成功 task 返回 403，query
  response 的 `result.data[0].url` 才可下载；脚本最初把下载失败覆盖为 task failed，是 transport 观察缺陷，
  不是模型失败。恢复下载 `post_attempts=0`，未重复生成。
- raw output 为 1920×1080/24fps/8s/H.264 High 4:4:4/yuv444p/no-audio，254,156,130 B，SHA
  `b707bb1...fa913`；常见 Windows 播放器不支持 yuv444p。research-only yuv420p preview 能播放但仍 9.6MB，
  转码不能修复 source/seam/motion。
- source→first `0.587962`；seam DSSIM `0.161631`，adjacent p95 `0.009446`、允许值 `0.03`。left/center/right
  first→4s SSIM 为 `0.793970/0.879543/0.884153`。左 Rift/道路/水晶/右星图较 Wan 明显，但其余主要层仍
  冻结或只有亮度纹理变化，整幕节奏像少数焦点轮流表演。
- Dragon 专用文档复核确认 `image_urls` 首帧与 `metadata.lastFrame` 尾帧字段正确；参数名不是根因。更关键的
  prompt Bad Case 是 1662-byte brief 重述源图并同时使用 `subtle/slow/restrained/gently/almost imperceptibly/
  extremely slow`。Google official I2V best practice 建议源图已给场景/风格时 prompt motion only，故本样本
  没有充分代表 Veo 上限。
- RQ-125 的裁决是 sample reject/provider open：不再用当前同图首尾/密集保守 brief 换模型抽卡；先做无付费
  C proof，证明层分离、整幕 motion coverage、source/seam 和维护成本。C proof 不佳则恢复一次短 motion-only、
  首帧控制 + deterministic seam 的 A comparator。该纠偏使混合路线更可控，但不把 A 线降为永久备胎。

## 2026-08-26：RQ-133 Seedance video edit

- 用户认可 Seedance 样本的左 Rift/中心水晶/右能量方向，但观察到顶部建筑、道路、地面反射、远景空气主要由
  一层雾带覆盖，要求保留已有动效并丰富静区。
- Dragon 专用页 `#/model/video-seedance-2-5-generation` 明确公共模型名 `seedance-2-5`、上游
  `doubao-seedance-2-5-260628`、`video_operation=edit`、`video_with_roles` 的 `reference_video`、编辑用
  `duration=-1` 与 `aspect_ratio=adaptive`；同时说明最多 10 段视频参考。该证据消除了之前“只支持图片参考”的猜测。
- Studio 主编排器的参考模式实际 input 仍只接受 image MIME，但这只是 UI 接缝；v6 runner 直接走文档化 API，先
  GET 成功 task 的临时 result URL，再单次 edit POST。它只发视频给同一 Dragon relay，不把签名 URL 写盘。
- 用户进一步指出 Video1 也可能干扰模型、放大现有雾带。v6.1 因此采用 double-anchor：Video1 只提供已有 motion
  rhythm，immutable Image1 锁定原始 geometry/material/linework；prompt 使用 `Edit Video1 / Use Image1 /
  Keep unchanged / Adjust only`，且禁止增强三个主体来冒充改善。
- v6.1 时间轴要求全部层全程同时运行，只让 4s 达丰富峰值；新增运动绑定道路、地面、反射、建筑缝、云层、星图
  和材质遮挡，雾必须是不同深度的 wisps，不是 screen-space sheet。费用仍按 8.041667×$1.4946 估算 `$12.0191`。

### v6.1 submit 400、诊断缺口与即梦官方模式

- source GET 成功后，edit POST 在 task 创建前返回 HTTP 400；task id 空、output 不存在、费用 0、task log 无
  隐藏任务，有效 calls 仍为 9。
- 登录态 common log 没有本次 400；18:49 的 ratio 错误是旧生成请求，不能替代。原 runner 只保存 status code，
  因而本次 exact field 已丢失。这是本地 observability gap，不是 400 根因本身。
- strict sanitizer 只投影 allowlisted nested error；未知/敏感/额外字段 digest-only。三项 red→green 测试通过。
  revised runner `e7eb8c9...c0807f` self-test no-I/O、1 POST/2 GET、唯一 output/status 均不存在。
- 即梦官方 UI 五模式中，`智能编辑` 是 Seedance 2.5 的专用单视频 edit 槽，另有多参考素材槽，比例/时长
  自动、720P；最符合 Video1+Image1。全能参考/首尾帧会重新生成，智能多帧当前切到 1.0 Fast，超长视频为
  30s。未上传、未购买、未生成；不先买会员/API 套餐。
- 当前不猜 Image1+Video1、duration 或 reference URL；先公共关闭诊断修复。后续若走官网，只允许先读回
  上传后的实际积分与参数，再决定一次官方智能编辑；没有可证伪字段或费用门前不重发 relay。
- 豆包工作 30 天订阅活动有客户端/公关公开信息交叉支持，当前账号 UI 显示标准套餐；客户端检索称可用月度
  额度调用 Seedance 2.5。它没有即梦式五模式按钮，而以附件+prompt 触发同源能力，故只作为零新增现金但
  控制较弱的 comparator；到期/剩余额度/素材角色未读回前不执行。

### 豆包 Seedance comparator 结果与 RQ-134

- 用户授权后上传既有 MP4 + v2 母图；Skill 明确无 video-to-video，抽 Video1 首尾帧 + Image1 作为三图参考，
  读回 8s/16:9/seedance_2.5/prompt unchanged 后 only one generation。
- 输出 4 个下载副本 SHA 都为 `e4b2f91...352cf`，确认只是重复下载；有效 calls 只增 1 到 10。视频为
  720p/24fps/193f/8.041667s/yuv420p + AAC，778,877B。
- source-first 0.407604、old-candidate-first 0.464484、first-mid 0.732047、left/center/right
  0.727645/0.723375/0.742591、seam diff 0.144582。移动水印污染指标且生产 hard fail。
- 人工确认主要语言是宽暖金轨迹/中段全局亮起；相较 C overlay 更贴材质但与蓝 Rift/水晶/右场不协调，且
  重绘 source、右侧主要只多几条金弧，云/反射/材质/星尘深度不足。sample reject/no retry。
- RQ-134：下一版三主体都增强，尤其右侧独立验收；全局环境也增强。允许三主体升级但不得替代全局；光轨
  只保留为冷蓝/青蓝主色的一层，暖金降低占比。下一正式路线为即梦官方 Smart Edit 真 video edit。
- RQ-135：多参考不是越多越稳。第一轮 MP4 负责时间/运动/构图，v2 PNG 负责几何/材质/色彩，职责已完备；
  新审美图会引入构图和材质漂移。高级编辑区域标记优先于第三图；真实识别 Bad Case 后才评功能性 mask。
- 即梦 v7 prompt 1,439 chars/4,115 bytes/SHA `edbc0d3...6f388`；当前 Chrome extension 重装/重启后可连接，
  但即梦标签的 DOM/reload/screenshot 仍页面级超时，故 file picker/上传由用户，Codex不盲点。
- 用户截图已证实高级编辑可用；后续研究确认帧标注表示“从该时间点开始修改”，可添加多个。旧单帧五标注方案
  作废；采用 00:00 启动、00:04 峰值、00:07 回收三个独立帧标注，每次单独添加至输入框。三矩形均保留完整
  右场，00:00 另有道路箭头/建筑点；不用画面文字，不增加第三张审美图。

## 2026-08-27：official 即梦 Smart Edit 与 post-process fault tree

- 即梦实际把主 prompt、三个 UI frame reference 和三段说明共同计入 2,000 字；执行版 main 压缩为
  534 chars/SHA `d003f047...cff10`。preflight 长版仍是 design intent，不能作为 result provenance。
- official output `4d3660b...155b` 是有效 call 11。1280×720/H.264/yuv420p/8.064s/193f+AAC；nominal 60、
  average 24.07，不是 clean CFR。镜头/建筑稳定、三分区和九宫格都变化，说明高级编辑确实没有只复制 input。
- raw mother→first 0.889072、input-first→output-first 0.874379、aligned stream 0.967997；这表明“整体延续 Video1”
  与“首帧仍被重新解释”同时成立。source identity fail 不能被 full-stream 高相似度覆盖。
- first→4s left/center/right 0.858797/0.917767/0.889054，center 相对最弱；右场已参与。adjacent p95
  0.011254、seam 0.046536>0.03，raw 不能 loop。
- FFmpeg normalization 能安全去 AAC、固定24、写 BT.709/faststart 并压到约3MB；这证明 delivery 问题可修。
  6/9/12f xfade、显式 blend、native overlap、settle/exact-anchor 都没有在 source/seam 双门下胜出。最佳 J
  seam 0.042684 仍 fail，且 phase rotation 把 mother-first 降到0.849216。
- 不能把最后一帧硬复制为首帧来刷 seam：它会产生 1/24s duplicate 或尾段 freeze/ghost，违反持续运动回收。
  停止 FFmpeg 追绿是 fault-tree 结论，不是把 official Smart Edit/model 判死。
- 下一可证伪问题是 0.889 的差异究竟来自 geometry/material drift，还是冻结 full-frame SSIM 同时惩罚了预期
  energy/light motion；回答前不调门、不付费重抽。

## 2026-08-27：Portal T/X identity fault split

- 对已存在的 source-anchored T (H.264) / X (VP9) 研究候选，统一使用 active v2 缩放到 1280×720 后的
  yuv420p/BT.709 口径，补齐了 geometry/edge、material/color、intended energy/light 三层证据。
- 母图直接编码→解码 baseline SSIM 为 `0.995139`；T/X 首帧分别为 `0.954464/0.958294`，edge correlation
  为 `0.995571/0.997081`，说明大结构仍稳定，不能把 source-first loss 简化成“整图重绘”。
- q95 WebP poster 的母图 SSIM 为 `0.987838`；poster→T/X 首帧为 `0.992257/0.988248`。AVIF 候选低于
  poster gate，暂不选用。T/X seam `0.027807/0.029357` 均在 `0.03` floor 内，但仍未过浏览器两轮与人工签收。
- 三大区及 near/mid/far 的时域亮度变化均大于 0；该证据证明 coverage，不证明自然材质运动。完整数值写入
  `docs/assets/8e-portal/portal-motion-candidate-tx-v1.json`，候选仍是 research-only/not-adopted。

## 2026-08-26：RQ-130 Paid-call content preflight

- Dragon common log 精确解释 refined 403：当时余额 `$15.008`、8 秒 Veo 预扣 `$19.712`；同一时间四条
  common-log pipeline 行不是四个 task，runner `post_attempts=1` 且 task log 总数仍为原 4。充值后余额
  `$65.01`，因此 billing 已从 hypothesis 变为 resolved/ready。
- 用户明确“万事俱备”还包括提示词、要求与约束尽可能达到理想效果。Google official I2V guidance 支持
  高质量 source、motion-only prompt、单一短场景和 unwanted-phenomena negative；不支持用密集场景重述或
  `no/not` 清单替代运动编排。
- v5 把 v4 并列效果清单收敛为一个 spatial choreography：固定 camera/frame/lens/deep focus/source linework，
  以 left Rift / center crystal-platform / right constellation 与 near/mid/far 三深度同时运行；八秒末回到同
  phase/illumination/velocity。它不改变 Veo/model/transport/source/first=last，只提高同一 comparator 的 art direction。
- 付费门必须同时满足余额、无隐藏 task、source URL/SHA、schema、prompt/negative digest、runner parse、one POST/
  no retry、唯一 output/status 和 exact-SHA public CI；任何单项不能替代另一项。

## 2026-08-26：Veo v5 upstream failure / terminal incident

- RQ-130 preflight 的公共证据是 `d57b026/32951125621` 三 job 全绿；因此本次不是未过治理门就付费。
- task `task_I5...k9Mw` 被 relay 接受并在 159 秒/100% generic failed；no output 意味着不能用结果评价 v5 或 Veo。
- 失败任务先扣 `$19.712` 后同额退款；钱包最终 `$67.01`。计费事实不能把 generic failure 细化成模型质量。
- 终端事故的根因是用进程窗口句柄判断可见性并在用户输入竞态中关闭父进程；后续不能在 prompt 窗口可能被用户
  操作时自动关闭。远端 task 与账单页优先于停在 50% 的本地 status；status 只能按同一 task body-free 更正。
### 2026-08-27：Portal motion direction revision

- Public run `33042204532` for the prior audit/evidence SHA is green; this closes the mechanical evidence batch, not the
  visual adoption decision.
- AutoGLM generated three concept images successfully, but all are preview-only: one has a full-width title/watermark,
  one overemphasizes the crystal and warm orbital lines, and one splits the scene into literal red/blue halves. None is a
  valid Portal mother or I2V source.
- Image2 credentials are present; the configured proxy was corrected from stale port `7890` to the user's active HTTP
  proxy port `12000`, which passed a read-only connectivity check. Two mother-image edit previews completed successfully;
  a third request returned `403 insufficient balance` and was not retried.
- Official JiMeng current page readback shows a Seedance 2.5 `全能参考` input accepting up to 50 mixed image/text/audio/video
  references. This is a multi-reference generation surface, not evidence of strict source-preserving video edit.
- Recommended next method is first-frame-only generation from the confirmed mother image, with continuous in-scene
  near/mid/far + left/center/right motion and no camera drift. Static Image2 direction previews must precede any paid call.
- Visual review of Image2 variants 1/2 found mostly brightness/contrast/blue-light grading rather than meaningful material,
  occlusion, reflection or phase changes. They are rejected as motion-direction evidence; no third retry after the balance
  403.
- User allowed skipping Image2. The next candidate therefore returns to a source-only first-frame video request with a
  shorter positive brief, avoiding the previous over-dense timeline/negative wording that may have suppressed motion.

## 2026-08-27：Seedance 2.5 v3 失败模式

- 12 秒 v3 的时序九宫格显示，开场约 0–2.5 秒主要只有左 Rift 形状从小旋涡逐步变成硬同心环，
  道路与 Rift 下方流动没有作为持续基础层出现；3 秒后才逐渐出现道路亮线。
- 4–7 秒所谓 burst 不是中央纵向的温和蓄放，而是横向/斜向穿过画面的直线网络，中心在约 7 秒过曝成白色光柱，
  右侧星图同时被画成高亮几何连线。该事件明显但不符合材质跟随、克制和可用于点击后转场的设计。
- burst 之外右侧星图/地形场变化很小，near/mid/far 也没有稳定的全幕呼吸；因此“区域有像素变化”不能作为
  “全局动态成立”的替代证据。v3 视觉 verdict 为 rejected，保留作 fault evidence，不进入 runtime。
- 下一 brief 应拆成常驻基础层和小幅事件层：常驻层从首帧起持续让道路、裂隙下方、右侧星尘/地形、建筑接缝、
  地面反射、云和空气有独立的中等幅度运动；事件层只在中段约 2–3 秒沿中央垂直轴上行/下行，轻柔激发水晶并
  平滑回到基线。禁止跨画面直线联动、过曝白闪、burst-only 右侧和把同心环当作 Rift 深度。

## 2026-08-27：v4 brief 的可证伪修订

- 失败原因更像是语义编排而非“模型不会动”：`gather/travel/circuit` 会把场景关系具象化为穿屏光线，
  “burst”也容易被实现为一次白闪。因此 v4 使用“每个观察点已经在动”的正向陈述，并把事件命名为
  `gentle central breathing swell`，限定在已有水晶垂直轴。
- 评审顺序固定为 baseline coverage → three-region balance → near/mid/far material motion → central swell
  locality → phase recovery → source/seam/codec。这样不会再用一处明显闪光掩盖道路、右场或环境静止。
- Image2 不是本轮必要工具：静态变色稿不能提供时序证据，继续调用只会增加成本和 source drift 风险；若有明确
  occlusion/reflection 表达问题，再单独提出受限同构 keyframe 假设。
- `0006858` / Actions `33078261349` 的 exact-SHA 三 job 全绿，证明 manifest、prompt digest、runner 静态门和
  canonical 状态可在公共环境重建；它没有增加外部视频调用，也没有把 v4 变成质量已证实的候选。
- v4 首次启动的 digest mismatch 是换行规范化缺失而非 prompt 内容漂移；runner 现在把 CRLF/CR 统一为 LF 并保留
  terminal newline，再与 manifest SHA 比较。该故障在 POST 前发现，external video calls 与费用均不变。
- 当前 Dragon pricing readback 为 Seedance 2.5 720p 图片参考 `¥1.494570/s`，12 秒估算 `¥17.934840`；这只是
  预算证据，生成结果仍需独立质量审查。
- v4 输出技术上稳定但视觉错误：中心每 0.5 秒 MAD `0.014625`，left/right 仅 `0.005851/0.004653`；
  九宫格显示平台变成大圆顶，右侧与 near/far 远景几乎不动。根因不是随机 prompt typo，而是“不可变几何”与
  “平台呼吸响应”正向冲突、抽象运动词缺少可观察载体、静态首帧缺少区域/时间控制。按 RQ-142 先做 method fault
  split，不继续付费抽卡。
- v4 rejection evidence `c964016` / Actions `33083670925` 三 job 全绿；这只证明观测与审计链可重建，不能把
  center-only 的高 MAD 或 first→last 高 SSIM 误写成全局动态成功。

## 2026-08-28：RQ-142 method fault split

- v3/v4 的共同模式是：首帧身份/构图容易保持，运动却向中央显著物坍缩；v4 还把平台变成圆顶。由此不能只说
  “prompt 不够详细”，更准确的归因是抽象运动语义 + 单静态首帧缺少区域/时间控制。
- 即梦 Smart Edit 虽然三大区 coverage 更好，但 source/seam 仍失败；因此 B 值得窄化后再验证，不可原样复制。
  C-line 的失败只针对线条/HUD 覆层，下一 C proof 必须改为材质纹理/遮罩位移，否则不再深挖。

## 2026-08-28：B1 contract 收窄

- B1 删除抽象的 `platform response` 与跨画面能量关系，只保留可定位到现有材质的动作：Rift 内宽幅流、道路
  通道流、晶体折射/现有光柱、右侧星尘/节点/地形表面、云/空气/反射。
- 三时间点不再描述“开始/峰值/回收”的新物体，而是同一组完整区域在三个时刻的状态约束；中央事件只作用于
  晶体和现有光柱，避免 v4 圆顶复现。
- B1 页面 readback 受阻：即梦标签能被发现且初始状态为全能参考，但语义 DOM、可见 DOM 和截图在扩展层连续
  超时。未进行任何点击/上传；该事实属于 browser transport blocker，不是 Smart Edit 能力结论。

## 2026-08-28：B1 非新方法与 C' 迁移

- 旧 Smart Edit 实际执行已经包含 Video1 + Image1 + 三个时间点帧标注；B1 只减少抽象词、增加平台不可变说明，
  不能冒充新的控制能力。为避免重复付费，B1 deferred。
- C' 不再使用可见 vector line/节点作为运动主体；运动载体改为母图材质的 mask 内低频流场、折射、反射和分层空气，
  这才是对旧 C-line 失败的实质修正。若仍显贴纸，直接停止，不继续堆 shader。

## 2026-08-28：C′ proof 结果

- C′ 的 192 帧结果在指标上均衡，但人工观看仍偏静态，source-pixel displacement 的区域边界存在 ghosting 风险；
  这解释了为什么“全区有 MAD”仍不等于 MotionSites 类全幕动效。
- C′ 保留为工程参考，不进入 runtime；下一候选采用 Kling v3 Omni 的单图片引用模式，并为该模型重写
  `<<<image_1>>>` placeholder prompt，避免把 Seedance/Smart Edit 的语义直接搬过去。

## 2026-08-28：Kling v3 Omni image-reference preflight

- Dragon 文档明确 Kling v3 Omni 的 image-only schema：`metadata.image_list` 中的图片由 `<<<image_1>>>` 引用，
  `mode=std` 为 720P，`duration=8`，`aspect_ratio=16:9`，`audio=false`；有视频参考时才使用 `video_list`，
  本轮刻意不上传旧视频。
- 价格页当前为 ¥0.462000/s，8 秒约 ¥3.696。专用 prompt/runner digest 已静态验证；没有外部 POST，等待页面/账户
  readback 后再决定是否执行一次模型对照。
- `cc35fae` / Actions `33098493865` exact-SHA 三 job 全绿；该公共门只证明请求合同可重建，不改变未调用/未扣费状态。

## 2026-08-28：Kling image-only 失败归因

- Kling image-only 技术链成功，但 source-first `0.860618`，左区 MAD `0.018846` 远高于 center/right
  `0.007312/0.006353`；视觉是厚塑料圆环 + 中央亮柱，右侧和环境没有持续运动。
- 这次说明“换模型”本身不够：只给静态图时，Kling 仍选择显著主体重绘来制造 motion。下一候选必须提供真正的
  temporal/reference-video 控制，或转入新的可控制片路线；不再重复同类 image-only prompt。

## 2026-08-28：Kling video+image B2 preflight

- Kling Omni 文档允许 `video_list` 与 `metadata.image_list` 联用；占位符顺序必须对应 `<<<video_1>>>` / `<<<image_1>>>`，
  有视频输入时 audio 字段应省略。B2 采用 base video 而非 feature，目标是保留已有 camera/tempo 而非角色特征。
- source task result URL 通过执行时 GET-only 获取，signed URL 不写状态文件；若 URL 过期/缺失，B2 在 POST 前失败，
  这把 transport/source readiness 与模型质量分开。

## 2026-08-28：Kling v3 Omni video+image B2 result review

- B2 的唯一付费 task 在轮询阶段遇到两次瞬时 `HttpRequestException`，GET-only recovery 最终完成；
  `post_attempts=1`、`recovery_post_attempts=0`，证明恢复没有重复计费。
- 输出技术完整且首帧身份良好（source→first SSIM `0.989310`），但人工审查仍拒绝：左 Rift 塑料厚环、
  中央硬亮柱、右场/远景与道路环境偏静。每 0.5s MAD left/center/right 为 `0.008926/0.007587/0.004271`，
  只能证明像素变化分布，不能证明材质运动成立。
- 根因不是单一模型或单一 prompt typo：base video temporal anchor 本身不均衡；Kling video+image 接缝没有
  可靠的区域/时间控制；正向 `vertical swell`/arc/node 语言仍允许 beam/ring/star shortcut；母图首帧身份并非
  当前主缺口。该证据不永久判死 Kling，也不支持立即再付费。
- 过程纠正：重复“扁平母图 + 整幕生成”会把 motion 坍缩到显著主体。下一次必须先验证每个可见层有独立、
  可逆的运动载体和审查证据，再决定是否值得新的模型调用；用户已要求停下做完整复盘，当前为
  `method-review-hold`。

## 2026-08-28：source-derived layer assets proof v1

- 直接移动整张母图会产生纱罩/建筑双影；改为从源图提取高频蓝青亮部，底图永不移动，mask 内只移动透明亮部。
- 1920×1080 proof 的 source→first SSIM `0.997556`，首尾 `0.998919`，三大区和三深度均有变化；人工确认清晰度、
  结构、无全屏雾/圆环/硬柱通过。
- 视觉仍偏 restrained shimmer，缺少实际遮挡和材质 plate，不能把均衡 MAD 当作 MotionSites 级全局运动。下一步不是
  再加 opacity，而是 `material-plate-generation-gate`，先补独立 plate/backplate，再回到确定性合成。

## 2026-08-31：RQ-171 适配器修复后的验证边界

- 旧 G53-4 的 `unsupported_parallel_tool_calls` 首错暴露的是中立适配器的批量 ToolCall 接缝，不足以判断
  GLM-5.3-Flash 一般能力；因此保留旧考卷和结果，另建 G53-5 身份，不在原输入上追绿。
- Flash 官方思考参数现在由隔离 profile 统一生成：`enabled`、`max`、`clear_thinking=false`。非空
  `reasoning_content` 仅在内部消息/工具回放链路中保留，公开结果和脱敏产物不得含原文；上下文估算需计入其长度。
- Zhipu Adapter 可接受多个合法 ToolCall 并保留顺序，AgentLoop 仍按原子预检后逐个执行；这不是并发能力，
  所以 `parallel_tool_calls=false` 声明保持诚实。非法 ID/参数、非字符串思考内容和公开泄漏仍应 fail closed。
- 离线合同回归已经完成，但真实 Provider 全范围测试尚未执行。G53-5 需覆盖文本/思考、结构化输出、工具批次、
  上下文和 Agent 链路，并记录调用/Token/错误与脱敏证据；不改变默认模型、Workbench、Auth、前端或
  `production_media=0`。

## 2026-08-31：G53-4 GLM-5.3-Flash 新鲜领域门发现

- 独立三案例 Dataset、Input Plan 与 body-free Prompt/Context snapshot 已由真实 ContextBuilder 路径重建一致；
  fixture、快照、G53-3 协议结果和代码/CI 身份均在 no-I/O preflight 中校验，预检外部调用为 `0`。
- 一次真实运行的首个正常复盘案例收到并行 ToolCall 响应。当前 Zhipu Adapter 的中立合同拒绝该批次，脱敏为
  `unsupported_parallel_tool_calls`；因此没有规范化响应、工具执行、知识证据、评测或发布，后两例按首错跳过。
- 资源账本只消耗领域 `1/12` 次调用、`0` 个规范化 Token；连同已通过的 G53-3 为累计 `4/15` 次、`1115` Token。
  这是 Adapter/Provider 响应接缝的领域门坏例，不足以判断一般模型质量，也不应通过放宽合同或重跑同一考卷追绿。
- 结果文件不可覆盖且只含脱敏状态/计量/哈希；不含 Key、原始 Prompt/响应、reasoning、完整请求标识或注入 marker。
  本地 runner/新资产尚未取得 exact-SHA 公共 CI，故结论为 `completed-local-rejected`，GLM-5.3 仍不准入默认。

## 2026-08-31：G53-1 适配档案离线 TDD 发现

- 官方公开资料已经足以冻结普通 API 的非敏感协议面：模型标识为 `glm-5.3-flash`，普通端点为
  `https://open.bigmodel.cn/api/paas/v4/`；Coding Plan 端点属于另一条产品通道。账户额度、权限和真实
  region 仍不能从文档推断。
- 不能把 GLM-5.3 当作 GLM-5.2 的字符串升级。按 ADR-0023，将 thinking 参数抽成不可变 profile；Flash 与
  `glm-5.3` 使用 `enabled + low`，历史 GLM-5.2 和未知测试模型保留 disabled 回退，调用方不能覆盖。
- 当前 provider-neutral 消息没有 reasoning 字段。Flash 普通文本/结构化结果可安全丢弃非空 reasoning；若
  reasoning 是非字符串，或出现在需要下一轮工具回传的响应中，沿用固定错误码 fail closed，避免把内部推理写入
  ChatResponse、日志或证据。多 ToolCall 仍由现有适配器拒绝，不能因为官方宣称支持工具就放宽本地合同。
- 受控 probe 和 CLI 必须与生产 Provider 共用 profile，否则离线绿灯会掩盖真实请求体差异；已补齐模型隔离的默认
  结果文件名。流式、图片/视频/文件输入与 reasoning 回传合同留给后续独立批次。
- 本批没有真实 I/O；`70 passed, 29 subtests passed`、compileall、diff/governance 通过。下一验证是 G53-2
  exact-SHA CI，而不是直接读取 `.env` 或切换默认模型。

## 2026-08-31：G53-2 exact-SHA 公共 CI 发现

- 现有 `.github/workflows/tests.yml` 已覆盖 `pytest`、真实 PostgreSQL migration/concurrency 与 Linux
  `packaging-smoke` 三个 job；G53-2 无需新增或改写 workflow。
- G53-1 的 9 个代码/测试文件被隔离为提交 `0f97b92683e4981842e745a695864deb611bb630`；该提交没有
  Portal、Account、Workbench、截图、资产或现有脏文档内容，远端 `main` 与 Actions head SHA 均精确匹配。
- Actions run `33325222755` 三个 job 全部成功。clean checkout 的完整 Python 结果为
  `1912 passed, 145 skipped, 1 warning, 127 subtests passed`；其中前端 fixture 是仓库提交内的 270 tests，
  不能与本地脏工作树的 297 tests 混写。
- 该公共绿灯只证明离线 adapter/profile 合同可在精确提交上复现。CI 没有真实 Provider/Riot/OP.GG 调用，
  不证明账号权限、模型可达性、领域质量、默认切换或公共生产成熟度；下一候选 G53-3 仍需用户单独授权。

## 2026-08-31：G53-3 有界协议门首次尝试发现

- 用户明确继续后，按硬预算启动一次 `adapter_protocol`；只临时使用普通 API 端点和 `glm-5.3-flash`，
  未修改 `.env` 或默认模型。OpenAI client 的 `max_retries=0`，不会自动重试。
- A1 结构化合同在第 1 次请求返回脱敏 `authentication_failed`；runner 立即跳过 A2，报告为
  `calls_used=1/3`、`admitted=false`。没有第二次或第三次请求，因此不能把失败归因到结构化 schema、thinking 或工具能力。
- 结果文件只含版本化状态、调用数、错误码、哈希和计量字段；schema 验证通过，SHA-256 为
  `b10827f18dc810085a0d3883ebb7175709f4c244c30c937d5d220ab1ec1d0d9a`。未保存正文、reasoning、Key 或完整请求 ID。
- `authentication_failed` 是当前安全映射的合并错误码，仍需用户侧确认普通 API Key、账户权限和端点接缝；
  不能仅凭这一次判断模型质量或 API 是否支持该合同。G53-4 不得在此结果上启动。

## 2026-08-31：G53-3 更换普通 API Key 后重开通过

- 用户确认此前 Key 已被删除，随后在普通 API Keys 页面创建新 Key，并把 `.env` 的 provider、普通端点和模型名改正；
  Key 值未输出或写入任何结果。
- 进程预检确认 `zhipu` + `https://open.bigmodel.cn/api/paas/v4/` + `glm-5.3-flash`，OpenAI client 重试为 0。
- A1 结构化合同通过（1 次调用）；A2 Agent 工具往返通过（2 次调用、1 次 ToolCall/执行）；总计 `3/3`，
  `admitted=true`。脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json`
  SHA-256 为 `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`。
- 结论：前两次失败由已删除的旧 Key 解释；G53-3 协议门现在通过，但不产生领域质量或生产准入证据。
  不自动启动 G53-4，等待单独授权。

## 2026-08-31：RQ-163 Agent 主线交接事实核对

- Portal/Account 的当前展示切片可以按用户决定阶段性收口；RQ-154 的两地区试水和“决定第三地区”只属于历史，
  RQ-157–162 已将当前 presentation 固定为 13 区 Focus Rail，不再扩地区。
- Agent 底座并未因为前端工作停滞：`app/agent/`、`app/runtime/`、`app/harness/`、Conversation-bound Review、
  Memory-aware Context、typed terminal turn 和 MCP/EvidenceBundle 均已有实现与证据。真正缺口是 GLM-5.3 采用闸门、
  面向用户的受限 Review Coach，以及 Data Dragon/Evidence/Training/OP.GG 的完整消费闭环。
- README 需要两次处理：RQ-067 的早期回填已完成；本批补事实版，RQ-085 的广泛研究、截图和作品集编排继续留给 8F。
- 下一候选应从 G53-0 无 I/O 审计开始；不读取 Secret、不改默认模型、不改 Workbench，不把本地 UI 回归或研究媒体
  解释成生产成熟度。

## 2026-08-30：Account panel / native control typography finding

- 视觉复查确认 Account 右侧 panel 的垂直偏低是布局位置问题，不应通过改 handoff `transform` 或转场时序解决。
  使用独立的相对定位 `top` 通道可以把桌面 panel 小幅上移，并在 `<=760px` 明确归零，避免移动端继承桌面偏移。
- 原生 `input` 的默认字体与已有 `select { font: inherit }` 行为不一致：input 会回退浏览器 Arial，而 select 继承
  应用字体。把三项控件显式统一到 Manrope body、560/0.95rem，并统一 caption 字阶，解决了用户看到的两组控件
  视觉断层，同时没有扩大全局 CSS 影响面。
- 这类 computed-style 断言比截图像素阈值更能稳定捕捉回归；本批 desktop/mobile live DOM 与 E2E 已证明 panel
  偏移、移动归零和 input/select 字体一致。它仍是 Portal/Account presentation hygiene，不等于 8E 或媒体采用完成。

## 2026-08-29：display title line-control finding

- 高字阶双语标题不能依赖浏览器自动折行：同一句话会因语言、viewport 和 font metrics 出现错误断句或大块尾部空白。
- 可靠合同是把完整句子保留为 heading accessible name，同时以显式 block spans 表达视觉行；每行 nowrap，响应式只调整
  字号与容器宽度。Portal/Account 中英文在 desktop/390px 的 live DOM 均验证无 overflow。

## 2026-08-29：Region Focus Rail / product-copy / handoff findings

- 地区 identity、媒体 readiness 和产品文案必须是三条独立轴。媒体是否有 WebM、尺寸/时长和 rights 状态可以留在
  catalog/data attributes/evidence，但把这些字直接展示给用户会让产品像内部验收台。
- 世界观氛围句应按中英文各自产品语境编写，而不是互译模板；未核验逐字来源时只能声明为 RiftCoach authored copy，
  不能借“官方/英雄台词”提升权威感。
- route commit 前后若没有一个 shared shell phase，Portal 离场和 Account 进场容易变成两段互不相干的动画。显式
  `closing/background-handoff/idle` 状态同时解决了 aperture 所有权、Account arrival、focus timing 和 E2E 可观察性。
- 当前 Vite bundle 仍有约 503 kB raw 的 chunk warning；它不是本切片回归失败，但应作为后续 code-splitting/performance
  debt 处理，不能在当前 Portal/Account polish 中顺手扩展到 Workbench 重构。

## 2026-08-29：Focus Rail 设计前诊断

- 当前 `RegionWallpaperLab` 的 selected state 绑定 `RegionWallpaperCandidate.id`，不是 13 区 identity；11 个无 catalog
  candidate 的地区被 disabled，因此不可能完成“点哪个就显示哪个详细徽章”。scene-preview 又重复当前 wallpaper，
  而 detail badge 只在约 29–43px mark 中显示并被压暗。
- Desktop `RIFTCOACH/*_emblem.png` 才是用户指的高细节徽章；当前 runtime 从未引用。12 个文件可解码且带 alpha，
  但 magic 是 WebP/VP8X 而不是 PNG，且无来源/许可 metadata。接入前需改为真实 `.webp` path 或转码；只作本地
  research hero，clean checkout 继续 Universe fallback。Void 没有同族文件，保留生成候选/crest fallback。
- 本地 ignored candidate pool 已有 12 区 Portal WebM/MP4/poster 和 Ixtal first-frame poster；所以 typed catalog 可以
  表达 optional motion，而不把 13 区 identity existence 冒充 13 份 adopted media。Account still pool 已有其它地区，
  Bandle 新 still 为 1200×600 WebP、SHA `f1da72...27cb`。
- 外部检索结论收敛为原生 React buttons + CSS scroll-snap + existing Motion。Motion Primitives/Aceternity/React Bits/
  Uiverse/MotionSites/Aura 只提供行为或视觉参考；Tailwind/GSAP/Anime/Embla/付费 Motion+ 均不进入当前 bundle。

## 2026-08-29：Portal/Account UI hygiene findings

- CSS 的历史媒体查询在末尾发生 cascade 覆盖：720px 以下 scene preview 曾被恢复成两列，
  390px 以下 selection 也可能被覆盖。最终规则集中在文件尾部，scene 在 `<=720px` 单列、
  selection 在 `<=720px` 两列且 `<=420px` 单列；721–980px 两列卡片避免窄到无法读。
- 产品路由的 presentation state 与 URL 必须同时表达 surface 和 region。新的 builder 始终输出
  `surface=wallpaper-lab`；旧 region-only URL 只保留兼容别名，未知键/阶段/地区不进入研究面。
  Account 的 `from` marker 是返回 UI 的提示，不是身份或路由权限；push/popstate scroll reset
  和 generation token 分别解决全页 handoff 裁切与旧 timer 竞态。
- 可访问性修复不靠视觉猜测：Portal/Atlas/Auth 有 labelled semantic landmarks，skip link
  真正移动焦点，标题使用 `tabindex=-1` 而非移除键盘语义；按钮暴露 pressed/current/disabled。
  `h2` 不再嵌套在 phrasing `span` 中，避免无效 HTML 结构。
- intrinsic width/height 已覆盖 RegionWallpaperLab、RegionBadgeMark、CinematicSceneMedia 的
  poster/video/crest 节点；这只降低布局位移，不改变研究媒体的 rights/production 状态。细徽记仍
  可能在 clean clone 缺失，因此必须保留 Universe fallback。
- 短桌面复测发现另一层 cascade 边界：1000–1199px 若沿用四列，最小卡片约 109–135px，地区名和
  状态接近不可读。最终在 `1000–1199.98px` 使用三列、`1200px+` 才使用四列，并加入 1000/1100/1199
  回归断言；实测最小卡宽约 147px 以上且无横向溢出。
- 无 region 起点的 Portal 选区也需要与 URL 对齐：卡片选择现在对当前 entry 做 `replaceState`，不增加
  历史层级；因此 CTA 后 `goBack()` 会恢复所选地区，而不是默认德玛西亚。该行为由独立 Playwright
  回归覆盖，Account 的受限 `from=wallpaper-lab` marker 仍由 `pushState` 生成。
- 长页面视觉复测发现 `.wallpaper-lab__media`/scrim/transition 若用 absolute 会继承 atlas 文档高度，
  在 390/768 宽度把 16:9 背景严重裁切并造成滚动漂移。改为 fixed viewport layers；E2E 现在断言
  390/360/320 与 768/800 的媒体层位置为 fixed、高度等于视口且无横向溢出。
- 常见 393/414px 手机若只在 390px 切单列会重新落入窄两列，中文地区状态不可读；单列阈值扩至
  `420px`，并覆盖 420/414/393/390/360/320 的回归，保留移动端背景 fixed 语义。
- 键盘激活 E2E 不再等待 720ms 瞬时 CSS 类；该类由组件时钟单测覆盖，浏览器层只断言稳定的
  Account URL、地区标记和可见边界，避免并行执行时在成功卸载 Portal 后产生假阴性。

## 2026-08-29：全量 source 池复查与 Portal 机制落点

- 用户此前列出的资源并不只包含 MotionSites。回读矩阵与旧日志后，确认可复用的来源分成四种职责：Riot/Universe
  提供形状语法与地区语义；高级视觉目录提供构图、字阶和密度参照；MotionSites/ Motion/21st.dev Motion
  /Motion Primitives/Magic UI/Animata/React Bits/Aceternity/Uiverse 提供局部交互机制；OP.GG/电竞数据、
  Langfuse 等 observability、TrainingPeaks/WHOOP/Strava 则分别服务 Workbench、Trace 和 Training。
- 本轮 Portal/地区/Account 只采用了可逆、可测试的机制：ready 卡片局部 spotlight + diamond marker、
  poster-first 双层 crossfade、共享且可中断的 aperture/burst handoff、详细徽章渐进加载失败回退，以及
  Auth 错误态上的地区背景语义 tint。没有安装新库、复制付费 prompt/页面源码、把静态图当交互或把后续模块
  的数据语义提前塞入入口。
- 小卡继续以 Universe crest 为稳定语义底标；用户提供的 LoR 风格徽章只作为 local research overlay，
  失败时仍显示 crest。这个取舍同时满足“不要过度简约”和来源/许可可替换边界，并避免把 Piltover/Zaun
  合并徽章误称为官方独立徽章。
- 视觉复查发现 390px 的 8E override 把入口说明文案拉到按钮上方过近；已在移动媒体查询中恢复正间距，并
  为 activation aperture/burst 增加可审计层标记。下一步以测试和真实浏览器截图验证，不扩展 Workbench 或生产媒体。

## 2026-08-29：MotionSites 广筛与 Region Entry Panel 试水

- MotionSites 的公开 browse/catalog 不只是已保存 prompt 的重复清单；当前可见的方向包括 Cinematic Landing
  Hero、Container Scroll Animation、Interactive Hover Button、Background Paper Shaders 和 Neon Nebula，
  并按 hero/landing/technology/interactive-media 等类型组织。它们适合提炼信息层次、交互状态与运动节奏，
  不足以替代 RiftCoach 的产品合同或授权素材。
- 两地区试水选择 Demacia/Bandle City，是因为二者已有本地 WebM、无音频 H.264 sibling 和 poster 三件套；
  其余地区虽有 crest 或 Account still，缺少同等级 ready 动态候选，继续 pending 更诚实。
- `region` 必须是 product journey 的 typed allowlist，而不是任意 query string；这样背景选择不会顺带改变
  routing region、player identity 或 owner scope。Account 背景是展示层 hint，不能被误解为账号验证或地区路由。
- 研究预览先以 poster 作为稳定底层，再叠加 video；播放失败/reduced-motion 时只隐藏视频，保持同一构图和操作层。
  这使视觉实验不依赖网络或远程 Provider，也保留了后续来源/许可替换空间。

## 2026-08-28：Bandle City wallpaper candidate and static still quality

- 桌面 `RIFTCOACH` 文件夹中已核对 `animated-bandlecity.webm`：1920×1080、25fps、15.04s、VP8 video +
  Opus audio。它展示了持续的树林、蘑菇荧光、萤火与空间层次；5fps 低分辨率采样的相邻帧 mean absolute diff 为
  `0.0043761693`，p95 为 `0.006180584`，采样首尾差为 `0.0062992894`。这些是候选技术证据，不是视觉签收或许可证明。
- 已生成本地无音频 H.264/`yuv420p` sibling 和 poster；原 WebM、MP4、poster 均隔离在 ignored candidates 目录，
  不进入公开 runtime。完整审计见 `docs/assets/8e-portal/portal-region-wallpaper-candidate-bandle-city-v1.json`。
- `runeterra-bandlecity-03.jpg` 只有 926×1080，压缩/低清感明显。已用内置 imagegen 做一个非破坏性高分辨率修复候选并另存于
  用户桌面素材目录；人工复核认为它虽然更锐但纹理偏脆、存在 AI 重绘感，与其它地区静态图不在同一质感层级，已判为
  `rejected`，原图保留，不能替代更高分辨率的官方源，也未进入 adopted media。

## 2026-08-28：full region media inventory review

- 桌面目录已包含除 Ixtal 外的 12 份动态 WebM。11 份为 1920×1080/15.04s，Harrowing 是 1280×720/5s；Bandle City
  唯一带 Opus 音轨。动态文件名已经能稳定指向地区，但 `animated-harrowing.webm` 需要单独作为 Shadow Isles 的
  低清/短时长备选，不把它与标准 15s 候选混为同一等级。
- 15 张静态图中，匿名哈希文件名需要靠画面内容与地区动态交叉核对。暂定优先映射为：Piltover=`6c774...-4681x2114`,
  Shadow Isles=`94e4...-2503x1080`（`ab3c...-1920x726` 为同地区备选，已由用户纠正确认），Ionia=`72ad...-1920x1079`,
  Bilgewater=`ef261...-1920x900`（已由用户纠正确认），Zaun=`3b6d...-1920x1057`, Void=`7107...-1920x1064`,
  Noxus=`6310...-1920x1080`；当前不为 Ixtal 硬分配静态图，Demacia、Freljord、Targon、Shurima
  优先使用已有命名文件，保留匿名图作 alternate/review evidence。完整暂定表见
  `docs/assets/8e-portal/portal-region-media-inventory-review-v1.md`。
- 当前只形成审计/推荐，不执行桌面批量改名。待用户确认后再做原文件不覆盖的 normalized sibling 与 manifest。

## 2026-08-28：Ixtal static candidate added

- 用户补充了 `1a75d072fa01ec3d0cda3f87fc1bf18dce736424-5000x2811.jpg`，原始 5000×2811，画面为 Ixtal 的丛林、远景建筑、
  悬浮晶体和前中后景层次；这正好补齐 Account 静态候选，但不代表已有 Portal 动态文件。
- 已复制为本地研究副本 `account-ixtal.jpg`；Portal 的 Ixtal 动态仍保持 pending。该图比 Bandle 低清图更适合做一次有界
  image-to-video 试验，因为它有明确的树叶/藤蔓、云雾、光束、悬浮晶体和远景雾层等自然 motion carriers，同时中心建筑
  仍可作为几何锚点。
- 依据用户希望静态图与其它地区处于同一质感层级，已用 Ixtal 官方图作视觉参考生成一张原创 16:9 Account 概念
  `ixtal-account-generated-v1.png`（1672×941）。它与原图职责分离：原图保留作动态首帧，生成图只作静态候选；是否采用需
  通过纹理匹配、构图、原创/许可与用户视觉裁决，不能把生成图称为 Riot 官方素材。
- Badge source audit：Riot LoR 支持页仍列出详细地区徽章附件，但旧 `article_attachments` URL 当前重定向到支持首页，
  无法作为稳定下载/runtime 源。它们可作为设计参考；当前小卡继续使用稳定的 Universe crest，详细徽章等待用户提供高清文件
  或新的稳定来源。
- Void gap：用户确认旧详细徽章集合缺少虚空，允许自行绘制。imagegen 首版过亮，第二版/第三版出现棋盘格背景；最终采用
  原版真实 Alpha + FFmpeg 确定性色彩分级的 `badge-void-generated-v3-balanced.png` 研究候选（1254×1254 RGBA），
  黑曜石/深靛主体保留可识别的低饱和紫色。它尚未进入 selector/runtime。
- 用户又提供 Image2 网页端 Void 徽章，人工观感优于前述自绘版本；原图与轻微 muted sibling 均为 1254×1254 RGB 深色
  不透明背景，当前优先作为 selected-region hero 候选，但尚未做透明 cutout 或 runtime 接入。

## 2026-08-28：official wallpaper fallback preview

- RQ-146 已激活：Wan 3.0 停止在 HTTP 404/no-task，避免继续消耗额度；用户提供的 Demacia WebM 成为第一份真实
  地区壁纸候选。
- `RegionWallpaperLab` 以本地 catalog 驱动动态 WebM/MP4、poster、reduced-motion/播放失败降级和独立入口转场；
  研究路径 `/?surface=wallpaper-lab` 不触发 Auth/API，也不改变默认 Portal。
- 候选文件仍被 `.gitignore` 隔离；只有来源/许可、loop、格式/体积、浏览器/移动端和公开再分发门全部通过后，才
  允许接入默认 Portal。

## 2026-08-28：masked-inpaint Rift proof 与 Wan 3.0 重开判断

- ImageGen 的“去掉 Rift 旋涡”编辑并非只修改目标区域，整图存在轻微像素差异；把它限制到 Rift 遮罩内可以
  避免污染母图，但不能自动修复材质不匹配。
- 独立 RGBA wisps 层在可见强度下像一条贴上的蓝色带，压低透明度则运动消失；因此 bounded proof 的机械
  遮罩门通过、视觉门拒绝。这个结果不是继续调 alpha 的理由。
- 官方 Wan 3.0 当前文档已明确区分 `first_frame`、`last_frame` 和 `reference_*` 模式，且首尾帧模式与同图
  约束会把运动压成插值/微动。RQ-144 允许一次公平的 first-frame-only 对照：adaptive、1080P、12s、
  audio/prompt_extend/watermark off，motion-only brief，暂不加入 burst。

- 用户补充了 RQ-145 条件回退：若这次 Wan 仍然廉价或运动错误，停止自制整幕视频，转评估 Riot 官方 League
  Displays 的地区主题动态壁纸；Portal 开始前选择地区，Account 使用独立静态壁纸。该路线目前只作为止损
  方案，必须先核对素材来源/许可、格式、体积、浏览器可播放性、移动端和 reduced-motion，再决定是否采用。

- Wan first-frame runner 首次启动收到 HTTP 404，因为输入是 OpenAI-compatible 文本地址
  `/compatible-mode/v1`，不是视频生成路径；状态文件无 task_id/结果。修复后从输入 URL 只取 allowlisted
  Alibaba scheme/host，并固定重建 `/api/v1/services/aigc/video-generation/video-synthesis` 与
  `/api/v1/tasks/{task_id}`，同时接受用户粘贴的 Markdown 链接形式。

- 用户随后明确转战官方/授权壁纸路线。`animated-demacia.webm` 是 1920×1080、15.04s、25fps、VP8、无音轨的
  高清动态场景，连续运动可见但首尾 SSIM 约 `0.941`，不能直接当无缝 loop；来源/公开再分发权限尚未核验。
- League Displays 官方页面提供 HD wallpaper/screen saver 与 Animated Art，但桌面应用不等于公开再分发许可；
  Wallpaper Engine 官方文档说明场景壁纸不能直接导出成视频，下载作品再发布可能需要原作者许可。下一步先做
  region catalog/local preview，不把 Workshop 或用户文件直接写进公开 runtime。

- 用户补充了 Universe 与 League Displays 的素材差异：Bandle City 在 Universe 页面存在网页动态背景，但
  League Displays 目前只有静态图。故 region crest、Account 静态图和 Portal 动态壁纸必须拆成三个独立资源状态；
  网页动画若不能取得允许再分发的独立文件，只能作为设计参考，不能直接抓取注入。
- 用户提供的另一类 3D 立体徽章更接近 Legends of Runeterra 的详细 region emblem；其中 Targon 版本可在 Riot
  官方支持附件中核对。小卡片仍优先 Universe crest，详细 emblem 保留为后续 selected-region hero 资产候选，
  先核对每张的官方来源和许可。

## 2026-08-28：独立材质 plate 生成预检

- built-in imagegen 的 5 张 plate 均不能直接进入合成：Rift 大水团像贴纸，wisps 只能做研究控制场；右场/道路仍有宽泛
  蓝底，晶体改变原始几何。alpha 存在不等于 plate 与场景材质相容。
- 直接叠加要么产生蓝雾，要么需要压低到不可见；问题仍是缺少真实 mask/inpaint backplate。下一步必须从一个 bounded
  Rift 区域开始做 `masked-inpaint-plate-proof`，不再批量生成、不再尝试整体 source 位移。
- RQ-143 已生效：后续 proof 必须底图像素锁定、只移动源图高光/独立透明 plate，禁止 source duplicate 纱罩、全局
  tint 和建筑边缘双影；Image2 只有在代理恢复且用于具体 plate/backplate 时才调用。

## 2026-08-28：source-derived visible variant rejection

- `replace-shifted` 通过局部模糊背板尝试消除原高光，再以 `motion_scale=2.5` 移动源亮部；低分辨率 contact sheet
  的运动比默认版本明显，但 Rift/道路/晶体边缘仍然 ghost/soft，右场和 far 不足。
- 结论：该方法不能同时满足 bold、sharp、no-ghost 三个要求；不继续提升倍率或修补边缘。下一步必须获取独立
  透明材质 plate 与真实 occlusion/backplate，再回到确定性合成。

## 2026-08-28：分层材质 proof v2 result

- Phase 0/1 的第一版可控 proof 通过结构、源图和技术编码门，三大区/三深度的像素变化也达到均衡，但人工观感仍然
  过轻，主要像 source image duplicate 的低幅亮度/纹理调制。Rift 内部、道路、晶体折射、右场和 near/mid/far
  没有出现清晰的空间流动或遮挡关系。
- 结论：控制时钟和 mask plumbing 是可复用工程资产；问题不在“再把 opacity 加大”，而在缺少真实的 layer
  backplate、遮挡补全、材质纹理和可观察 motion carrier。继续调参会产生贴层/ghosting 或整体蓝雾。
- 下一动作收窄为 `layer-assets-and-occlusion-proof`，仍不产生外部模型调用；若真实分层 proof 仍显廉价，停止生成式
  Portal 动效并保留高质量 poster，不把低质视频放入 runtime。
- 本机完整回归的 `--maxfail=1` 在第 127 项 PostgreSQL API fixture setup 因 `DATABASE_URL` 未配置而停止：
  `126 passed, 1 warning, 1 error`。该错误发生在真实数据库环境初始化，不涉及 v2 proof 文件；聚焦 proof/相邻媒体测试
  仍通过，公共 PostgreSQL job 负责真实数据库补证。

## 2026-08-31：G53-0 无 I/O 审计发现

- G53-0 只读取了仓库设计/ADR、非敏感模板、代码和历史脱敏元数据；没有创建 OpenAI client、调用 Provider/Riot/OP.GG，
  也没有输出或记录 `.env` 中的 Key 值。
- `compose.yaml` 与 `.env.example` 的产品默认仍是 `zhipu` + `glm-5.2`。`app/providers/config.py` 只做字段非空/超时检查，
  没有账号类型、Plan、region、model allowlist 或 thinking profile；`app/providers/zhipu.py` 与 probe 全局发送
  `thinking.type=disabled`，并把非空 reasoning 视为错误。
- 本机 `.env` 被忽略；遮罩式核对只确认 Key 存在，并观察到 `LLM_PROVIDER=glm`、Coding Plan 形态端点和 `glm-5.2`。
  当前 loader 要求 `provider=zhipu`，因此该配置在现有产品接缝会被拒绝；不能把端点字符串或用户历史线索当成权限证明。
- 账号/Plan 权限、真实 endpoint/region、正式 GLM-5.3 model ID 和 `enabled + low` 可用性均 unknown。旧 GLM-5.2 与
  DeepSeek 结果保持只读，不能外推新模型质量。
- 结论：`G53-0 completed-local / adoption blocked-deferred`。下一安全候选是取得非敏感账户信息后另行执行 G53-1 离线
  profile TDD；本批不改默认模型、`.env`、`app/` 或 `web/`。

## 2026-08-28：source-derived layer assets proof v1

- 直接移动整张母图会产生纱罩/建筑双影；改为从源图提取高频蓝青亮部，底图永不移动，mask 内只移动透明亮部。
- 1920×1080 proof 的 source→first SSIM `0.997556`，首尾 `0.998919`，三大区和三深度均有变化；人工确认清晰度、
  结构、无全屏雾/圆环/硬柱通过。
- 视觉仍偏 restrained shimmer，缺少实际遮挡和材质 plate，不能把均衡 MAD 当作 MotionSites 级全局运动。下一步不是
  再加 opacity，而是 `material-plate-generation-gate`，先补独立 plate/backplate，再回到确定性合成。

## 2026-08-31：RQ-172 G53-5 全能力矩阵发现

- 新实验共 11 次真实调用、46,151 tokens，8 个案例中 7 个通过。adapter core、AgentLoop 的有序多 ToolCall 与
  思考回放、domain development、vendor text stream 和 vendor multimodal 均有观察证据；结果为本地真实观察，
  不是生产准入。
- F7 的 vendor `tool_stream` 在 `max_tokens=512` 返回 `incomplete_chat_response`/`length`；这是该预算下的未完成
  响应，不能单独证伪 tool_stream 能力。F4 的 `cached_input_tokens=0` 且 `cache_status=unproven`，因此缓存能力
  仍未证明。F8 是 vendor-only multimodal 观察，provider-neutral 消息合同仍为 text-only。
- 结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_capability_matrix_v1.json`
  的 SHA-256 为 `BFFF564CF4C6E7B2DD05F88542FD7A872D1565442B6D35C795EC6892CC84BE0C`；其
  `production_admitted=false`、`public_ci_confirmed=false`。HEAD 与 `origin/main` 均为
  `0f97b92683e4981842e745a695864deb611bb630`，工作树保持 dirty。
- 结论：G53-5 关闭一次本地真实矩阵观察，但不关闭 Stage 8/8E、领域采用、公共 CI、安全部署或生产成熟度；下一步
  等待用户决定 Agent 主线下一项，不重跑 G53-4，不改默认模型、Workbench、Auth、前端或 `production_media=0`。

## 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

- 独立 follow-up `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json`
  （SHA-256 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`）绑定父矩阵 experiment
  `4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb` 与父结果 SHA
  `bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`；自身 experiment_id 为
  `49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`。
- 唯一 `1/1` 调用只把原 F7 的 `max_tokens` 从 512 调至 2048，得到 `557` tokens、`finish_reason=tool_calls`、
  1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source identity stable、`cached=0`。这说明在更高上限下
  观察到完整工具调用结束，但传输仍是 `vendor_raw_transport_only`，不能外推为 provider-neutral streaming。
- 结果标记 `production_admitted=false`、`public_ci_confirmed=false`；不证明 Agent 生产、领域采用或公共 CI，且不
  覆盖/重写 RQ-172 或旧结果。Stage 8/8E 保持 `in_progress`，下一步等待用户决定 Agent 主线下一项；默认模型、
  Workbench、Auth、前端和 `production_media=0` 不变。

## 2026-08-31：RQ-175 专属运行时档案审计结论

- [architecture] 旧 30 秒是 Skill/held-out 质量资源阈值，不能与 Provider SDK 的网络超时混为一谈。新 Flash
  profile 将 Agent/`llm.chat` 执行窗设为 90 秒、传输超时设为 120 秒；旧 Dataset 的 30 秒仍会在资源层诚实
  报告超时质量失败，若要移除必须另建版本化考卷。
- [trust] 仅按精确 `zhipu/glm-5.3-flash` 解析注册 profile；G53 预算包装器会在最终 Provider 边界重新绑定 profile、
  截断 `max_tokens`、固定 sampling/timeout 并写入 profile 身份，防止自定义 executor 绕过。无 profile 的旧 wrapper
  路径继续使用历史 1024 上限。
- [replay] Agent 和 Harness `llm.chat` 请求都带 `runtime_profile_id/version`；请求摘要同时纳入 `temperature`、
  `top_p`、`max_tokens` 与 `timeout_s`。旧 G53-4/G53-6 JSON 通过 legacy digest fallback 严格复读，新身份不会
  覆盖旧文件。
- [boundary] 当前工作树包含未提交用户成果，而公共 CI SHA 仍是旧实现提交；真实 G53-7 runner 必须先取得新实现的
  exact-SHA 公共 CI，且会拒绝 dirty worktree。no-I/O preflight 仍可在 dirty tree 运行。
- [evidence] 聚焦 profile/domain 回归 `98 passed, 27 subtests passed`，额外 runtime/provider 回归 `108 passed,
  8 subtests passed`，compileall、diff/governance 均通过；本批没有真实 API 调用。

## 2026-08-31：RQ-176 产品运行时晋级接线

- [decision] 用户明确选择 Flash-only 产品目标：普通智谱 API 的 `zhipu/glm-5.3-flash` 使用唯一注册的
  `glm-5.3-flash-runtime-v1`；GLM-5.2 只作为明确兼容/应急回退，不再等待 Pro/Flash 比较后决定。
- [composition] 产品组合根、Worker、RuntimeExecutionFactory、Agent compiler、Harness `llm.chat`、
  Provider、Runtime policy 和 Trace identity 现在共享同一受信 profile。Skill manifest 的 30 秒仍是质量
  资源门，profile 的 90 秒是执行窗；两者不再混用。
- [provider] Flash 产品构造强制普通 API 标准基址、传输 120 秒和 SDK `max_retries=0`；直接绑定的
  `ZhipuProvider` 也会截断超出 profile 的 timeout/max_tokens/sampling。Worker 仅接受已登记的 GLM-5.2/
  Flash，Flash 默认 lease/heartbeat 为 360/60 秒，lease 少于 300 秒拒绝。
- [compatibility] 旧 Trace 的无 profile 形状、GLM-5.2、测试 double 和显式无 profile 路径保留；通用
  composition 自动推断 Flash 时要求 Provider 已绑定相同 profile，避免同名伪适配器隐式获得预算。
- [boundary] 这是本地产品接线，不是公共生产准入。当前工作树仍 dirty；新实现须先取得干净 exact-SHA 公共
  CI，再在同一 SHA 重取 G53-3，并另行执行 G53-7 领域门、完整黄金切片、安全/部署/合规与 8F。旧 G53-3、
  G53-4、G53-6 证据不可复用或覆盖。

## 2026-08-31：RQ-178 G53-7 A/B 身份绑定与无 I/O 预检

- G53-3 的协议执行代码属于实现提交 A；把脱敏结果入库会形成证据提交 B。若只比较当前 `HEAD`，B 会错误地
  取代 A 并造成自引用。因此新 schema 1.1 admission 记录 `implementation_sha=A`、`protocol_code_sha=A`、
  `evidence_commit_sha=B`，并分别记录 A/B 的公共 CI 运行号与成功见证。
- 预检从 B 的 Git blob 读取协议文件，按仓库 canonical LF 计算 SHA-256，再要求工作树对应文件与 B 一致；同时
  检查 A→B 是直接单父关系、B 只新增 capability-result 白名单、当前 `HEAD=B`、Provider/model 和严格 `3/3`
  通过合同。缺确认、错配、路径穿越、代码混入、非祖先、blob 篡改和旧协议 `code_sha` 均在 Provider 构造前拒绝。
- 旧 schema 1.0 结果的摘要计算显式省略新增空字段，保持历史 G53-4/G53-6 可读且不可改写。Windows 工作副本
  的 CRLF 摘要 `6c6e…` 与 Git canonical LF 摘要 `1fda…` 只作不同层次记录，准入绑定使用 canonical 值。
- [历史边界，已由 RQ-179 更新] 当时身份代码仍在 dirty 工作树，`f0d5ee2→407ee` 仅用于验证规则；后续已
  形成最终 A=`9e6d78be…` 并取得 exact-SHA CI。下一步改为从干净 A 重取 G53-3，再由只含证据的 B 承载。

## 2026-08-31：RQ-179 A 身份冻结的 CI 生命周期发现

- 历史 A/B fixture 不能把旧 B 直接冒充任意新 checkout 的真实 HEAD；测试必须显式隔离历史 reader，而生产
  `actual HEAD == evidence B` 仍保持 fail closed。
- `actions/checkout` 的默认浅克隆不足以验证 A→B 直接父子、Git blob 与 diff 身份；执行该证据门的公共 CI 必须
  取得完整 Git 历史。最终 A=`9e6d78be51c3a5c512b67f83d2849f9b1261cf77`、run `33378687984` 三 job 全绿。
- `fe7d577…` 与 `3ccd827…` 的失败 run 是发现验证环境接缝的证据，不是最终 A。下一次协议结果的内部
  `code_sha` 必须使用 `9e6d78…`，并从干净 checkout 生成；不能把当前 dirty 工作树或旧协议结果复用为 B。

## 2026-08-31：RQ-180 G53-7 首次真实领域尝试结果

- [execution] 在 A=`9e6d78be…`、B=`7cb66d2…` 的干净 LF checkout 上，按用户明确授权只执行一次正式 G53-7；
  协议调用 3/3，领域调用 2/12，累计 5/15 calls，领域消耗 3505 tokens，墙钟 36625ms。
- [failure] 首例 `flash_gate_baseline_01` 在两次 Provider 请求后由适配器安全归类为
  `provider_response_invalid` / `incomplete_chat_response`；规范化响应计数为 1，Agent 进入 failed/degraded，
  后两例按首错停止跳过，最终 `admitted=false`。这不是认证失败（G53-3 已通过），也不足以推出模型一般质量结论。
- [evidence] 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`
  的 canonical-LF SHA-256 为 `21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment 为
  `236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；随后由本地 C=`9157cde…` 仅承载结果，
  C 未推送、无公共 CI。结果没有保存底层 vendor finish reason、Key、请求/响应正文或 reasoning，因此不能把
  `incomplete_chat_response` 进一步断言成 `length`。
- [boundary] 旧结果不可覆盖，当前不自动重试、不改 Dataset/Plan、不改产品默认或 Portal/Account/Workbench/Auth；
  若需要继续，必须另建版本化的响应完成/截断诊断并取得新授权。Stage 8/8E 仍 `in_progress`，`production_media=0`。

## 2026-08-31：RQ-182 版本化响应完成策略

- 当前 Provider-neutral `ChatResponse` 只接受完整正文或合法 ToolCall；因此 RQ-181 的空正文/非空 reasoning
  形状应继续 fail closed，而不是把内部 reasoning 塞进 AgentLoop。
- 官方接口层没有独立 reasoning token 预算或可证明的 `continue`/`previous_response_id` 句柄；应用层若将来尝试恢复，
  只能另发一次 fresh completion，并需要新的预算、attempt 和 Trace 合同。当前 `GLM53BudgetedProvider` 对一次逻辑
  `chat()` 记账，适配器内隐式第二次请求会少算真实调用。
- 最小安全实现是纯策略模块：脱敏快照 + 受信上下文 → 版本化判定。严格 Flash v1 只允许完整文本/工具回合，
  `max_additional_calls=0`；候选策略只在精确白名单形状下返回 `candidate_eligible`，并因未注册而保持不可执行。
- 不应在本批改 `ChatResponse`/`ChatMessage`/`LLMProvider`、AgentLoop、Structured Decoder、ToolRuntime retry、
  Runtime Trace 或公共错误 allowlist，也不应根据 `output_tokens == max_tokens` 自行推断截断。
- 离线 TDD 已验证 41 条路径；候选真正启用前需要新的 runtime profile、预算/Trace attempt schema、exact-SHA CI、同 SHA
  G53-3 和独立真实授权。

## 2026-08-31：RQ-181 Flash 响应完成度诊断

- 原因已从适配器聚合码中拆出：独立探针在首个冻结案例的 `agent_initial` 回合捕获到原始
  `finish_reason=length`，`input_tokens=2220`、`output_tokens=2048`；正文为空、reasoning 非空、ToolCall 为 0，
  Usage 结构有效。适配器在结束原因校验处抛出 `incomplete_chat_response`，所以没有 normalized/settled response。
- 这说明当前 `enabled/max/clear_thinking=false` 档案会在长领域上下文中把 2048 输出额度耗尽于推理阶段；它不证明
  RQ-180 的第二回合也是同一原因，也不证明模型或账号不可用。生产适配器继续 fail closed，不应把 reasoning 当正文发布。
- 脱敏诊断结果 `zhipu_glm53_flash_response_completion_diagnostic_v1.json` 的 canonical-LF SHA-256 为
  `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，由本地提交 `baa9cc756ff9e3dfc5eac19119315b7f9f0b56da` 承载；
  不含 Prompt、响应/推理正文、Key、原始请求 ID 或工具参数。下一步先做版本化响应完成策略设计和离线 TDD。

## 2026-08-31：RQ-183 候选 fresh-recovery 合同发现

- RQ-181 的空正文/非空 reasoning 只能通过 RQ-182 的脱敏策略识别；若未来真的发第二个完整请求，必须把它
  当作独立 `fresh_recovery` attempt，而不是 API 原生续写或 Provider 内部 retry。
- 候选 runtime 的身份必须同时绑定 provider、model、runtime profile/version、policy/version、8192 单次输出上限和
  candidate 激活状态；只靠模型名或配置 metadata 不能取得执行权。
- 预算需要分成预留与结算两个时点：预留防止并发/第三次调用和明显不足的剩余空间，结算记录实际 token/时间并
  在单次或累计超限后 fail closed；已发出的失败请求不能从账本中抹掉。
- Trace 采用独立 schema，只记录安全状态码、attempt 身份、Usage 是否有效和资源数字；任何 Prompt、正文、
  reasoning 原文、工具参数、Key 或 request ID 都不进入合同。候选本地合同完成不改变严格 Flash v1、统一 RuntimeTrace
  或产品默认。

## 2026-08-31：RQ-184 公共证据接缝发现

- 候选合同的公共验证必须把实现代码和脱敏结果拆成两次提交：A 固定实现与协议代码，B 作为 A 的直接子提交只新增
  结果文件。A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 Actions run `33405110692`、B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 的 Actions run `33405881172` 均三 job 全绿。
- 同一 A checkout 的 G53-3 严格 `3/3` 调用通过（A1 `1/1`、A2 `2/2`，SDK retries `0`）；结果 `code_sha` 仍为 A，A/B 无 I/O 预检通过，canonical-LF 文件摘要为 `275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。
- 这只证明公共可复现性和协议身份接缝；候选依旧未注册、不可执行，不能把一次协议通过解释为恢复能力或领域/生产准入。下一步若获授权，才执行一次有界 fresh-recovery 诊断并审查成本、延迟、失败和 Trace。

## 2026-08-31：RQ-185 候选恢复诊断中断发现

- 隔离诊断代码 `76de589a128b7a71f1def3316da3f30ebdd3a4c8` 的离线状态机测试通过，并不保证
  HTTP/代理层会在 OpenAI 客户端的数值 timeout 内及时退出；第二次将传输上限临时收窄为 20 秒后，进程仍未在
  约 60 秒内返回，说明下一轮必须先把代理/连接/读取各阶段的截止和强制终止做成可观察的独立边界。
- 两次独立启动都只进入 `primary`，没有观察到供应商响应，也没有生成 Usage、finish reason、Trace 或结果 JSON；
  因而既不能把它归类为模型超时，也不能判断请求是否抵达供应商或是否计费。费用状态只能保留 `unknown`。
- 没有 `primary` 的脱敏快照就不能合法打开 `fresh_recovery` 槽位；本轮没有发送第二回合。正确状态是“诊断中断、
  无可用结果”，不是“候选恢复失败”或“模型失败”。严格 Flash v1 和候选注册状态均不变。

## 2026-09-01：RQ-186 请求级截止与延迟边界发现

- OpenAI 客户端构造时的默认 timeout 不是最终真相；`ZhipuProvider.chat()` 会把
  `ChatRequest.timeout_s` 作为请求级 timeout 传入 SDK。RQ-185 的 20 秒客户端值因此被 90 秒请求值覆盖。
- 修复后脱敏请求摘要和测试都确认 `timeout_s=30` 真正进入 primary SDK payload；真实调用在约 30.141 秒以
  transport timeout 返回，说明进程不再失控，也排除了“20 秒 SDK 截止本身失效”的猜测。
- 本次没有供应商响应、Usage、finish reason 或 request ID，无法判断生成是否已经开始、是否计费或模型内容能力；
  `cost_status=unknown` 必须保留。30 秒又低于候选 90 秒 Agent 窗口，所以这不是候选能力拒绝。
- 若继续，下一决策是是否值得用完整候选延迟预算做一次受监督诊断，而不是再次调低 timeout、改写旧失败结果，
  或把 transport timeout 当成模型质量结论。

## 2026-09-01：RQ-187 完整窗口发现

- 90 秒请求级截止在完整候选档案上也真实生效；唯一 primary 在 90.188 秒安全返回 transport timeout，
  因而 RQ-185 的问题不是“客户端 20 秒设置未生效”之外的简单短窗口误判。
- 仍没有供应商响应、Usage、finish reason 或 request ID，`budget_exceeded=true` 只表示超时后的结算超过精确
  90 秒边界，不能当作模型输出超预算。候选恢复槽位没有打开，费用保持 unknown。
- 现有 G53-3 短协议通过与本次长上下文无响应之间存在请求形状/延迟差异，但当前证据不足以归因到代理、首字节、
  服务端推理或上下文长度中的任何一项。下一步应做传输/生成路径拆分，而非盲目再跑同一请求。

## 2026-09-01：RQ-188 传输/生成拆分发现

- 合法的 Flash 控制请求必须保持 `thinking=enabled`；首次 disabled-thinking 结果是请求形状无效，不能拿来证明
  endpoint 不可达。随后合法 `enabled/low` 控制收到响应，说明最小供应商接缝可达；marker 未匹配只表示 16 token
  额度被 reasoning 占用，不等于无响应。
- 冻结上下文的 256 token max 同步请求同样收到有效 Usage，但以 `length + 空正文 + 非空 reasoning` 结束；这与
  RQ-181 的 2048 形状方向一致，支持“同步请求的输出额度先被推理消耗”的假设，但不确定需要多少额度才能产生可见正文。
- 同一冻结上下文、8192 token max 的流式请求在约 `687ms` 观察到首个 `delta_reasoning` chunk。首块探针主动关闭，
  所以不能把它解释为完整流式完成、Usage 正常或 provider-neutral stream 合同；它只把“传输不可达”和“已开始生成”分开。
- 正式结果三路均 `observed`，合计 `3` calls、`2265` tokens；代码/source identity 同为
  `b67b4500ebdbff934e470fd92c1461184aa7c49b`，结果 SHA=`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`。
  中间结果保留但不作为正式证据：一个是无效 thinking 控制，另一个的 diagnostic SHA 元数据有输入笔误。
- 下一实验应先做 evaluation-only 的输出额度/推理档位校准，优先观察可见正文是否出现，再决定是否需要设计完整
  stream assembly；不得直接改生产同步接口、全局上限或候选注册状态。

## 2026-09-01：RQ-189 输出额度/推理档位校准发现

- 同一冻结上下文下，合法 `thinking=enabled`、`reasoning_effort=low`、`max_tokens=2048` 的同步请求在约
  `28.344s` 返回可见正文，`finish_reason=stop`，同时存在 reasoning，Usage 输入 `1973`、输出 `724`。因此，
  “2048 必然只会耗尽 reasoning”不是普遍结论；RQ-181 的形状与本次结果的差异至少包含推理档位/请求时机因素。
- 将同一上下文的 `low+8192` 和 `max+8192` 各自单独执行后，两路都在约 `45.5s` 请求截止内没有收到同步响应。
  没有首字节/Usage 时，唯一可判定的是该窗口内未完成 transport 观察，不能把它写成模型拒绝、权限错误、模型质量
  失败或计费结论。
- 诊断器增加单路选择和前缀执行后，可以把长矩阵拆成可监督的单次调用；输出文件只在完整脱敏报告准备好后以独占方式创建，
  中断不会留下零字节伪证据。第一路结果使用修补前的诊断 SHA，后两路使用修补后的 SHA；请求载荷和 body-free
  规则没有改变，三份结果应作为相互独立的 companion observations，而不是伪造一个同 SHA 单次矩阵。
- 这组结果支持下一步先验证 streaming 的首个可见正文及 `clear_thinking` 组合，再决定是否需要新的响应装配或
  自适应预算；不应直接把 `8192` 写入生产上限，也不应因为两个同步 timeout 自动切换 Provider/默认模型。

## 2026-09-01：RQ-190 流式首个可见正文发现

- 同一冻结上下文、低推理、2048 上限下，`clear_thinking=true` 在 1.813 秒收到首块、2.547 秒出现首个非空正文；
  `false` 在 1.500 秒收到首块、3.875 秒出现首个非空正文。两路都先产生 reasoning，说明“先 reasoning、后正文”是可
  观察的流式形状，而不是同步空正文的唯一表现。
- 探针在首正文后立即关闭，故没有终态 finish reason、Usage 或完整正文；资源数字为未知而非零，不能用这批结果做成本或
  token 预算结算。单轮共现也不能证明 `clear_thinking` 的因果效果或跨轮思考清理/回放。
- 原始 transport 探针必须与当前产品 `clear_thinking=false` exact profile 分离；强行改 profile 会越过模型身份边界。
  下一项应只补完整终态/Usage 观察，不把首正文证据直接接入 Provider-neutral runtime 或候选注册。

## 2026-09-01：RQ-191 完整流式终态发现

- 当前 `clear_thinking=false`、低推理、2048 的一条冻结上下文流在 2.203 秒给出首块、3.531 秒给出首正文，
  24.140 秒以 `finish_reason=stop` 完整结束并提供有效 Usage（1973 输入、652 输出）。这证明 RQ-190 的早退路径
  可以延伸到完整终态，但只覆盖一个上下文和一个档位。
- 完整流共有 642 chunks，其中 30 个 reasoning、571 个可见正文、41 个空/其它块；解析器必须允许 Usage-only/空 choices
  终态块，同时持续校验 model 与 request identity，不保存任何正文或 reasoning。
- 该结果不能替代领域黄金切片、工具流、跨轮 reasoning replay 或 provider-neutral runtime 合同。下一步应把“完整流装配”
  做成纯离线合同，明确终态、Usage、正文/工具互斥和超时 fail-closed，再决定是否接线。

## 2026-09-01：RQ-192 提供商无关流式装配合同发现

- 将供应商原始 chunk 先归一化为 `ProviderStreamEvent`，再由纯离线 `ProviderStreamAssembler` 装配，能够把
  终止、Usage、模型/请求身份、正文与工具互斥和失败毒化固定在一个可测试的候选接缝；该接缝不等同于现有
  同步 `LLMProvider`，也不自动宣称 streaming capability。
- 完成条件必须是“底层迭代器已经 EOF + 已观察 terminal + Usage valid”；terminal 后最多接受一个 Usage-only
  帧，空尾帧、正文/推理/工具迟到、重复终止或重复 Usage 都 fail closed。任何首次合同错误都会毒化装配器，
  防止把同一坏流静默转成 recovery。
- 工具片段按连续 index、唯一 id/name 和严格 JSON 对象解码；拒绝重复键、NaN/Infinity、过深嵌套以及超过
  事件/正文/推理/工具数量和参数字符上限的输入。事件处理采用 copy-on-write，只复制被触及的工具 index，
  并以增量计数替代每帧全量求和，同时保留原子提交语义。
- 正文只用 `strip()` 判断“是否全为空”，交付时保留供应商正文的首尾空白；错误对象只允许安全错误码，拒绝把
  SDK/供应商自定义消息写进异常文本。底层迭代器异常或取消必须走 `abort()`，只有正常 EOF 才能 `mark_exhausted()`。
- `StreamAssemblyTrace` 是显式 allow-list、body-free 的可持久化投影；内部 `StreamAssemblyResult` 的默认
  repr 也不再包含响应正文或工具参数，避免调试日志绕过边界。聚焦测试共 29 项，与相邻套件合计
  `147 passed, 27 subtests passed`。
- 这批只完成离线候选合同；没有 SDK、网络、重试、真实供应商适配器、产品默认、Workbench、Portal、Auth 或
  `production_media` 改动。下一步是同一新实现 SHA 的公共 CI 与 provider conformance，不能把本地回归当作生产准入。

## 2026-09-01：RQ-193 智谱流式适配器一致性接缝发现

- 测试内 `_FixtureZhipuStreamAdapter` 足以验证“厂商分块翻译”和“中立装配”之间的边界，而不需要把真实
  SDK 客户端、Key 或网络带入合同。它从 OpenAI-compatible fixture 只提取 model、序号、请求 ID 摘要、正文/
  reasoning、工具片段、终止原因和 Usage，再交给 `ProviderStreamAssembler`。
- 正文 fixture 与现有 `ZhipuProvider.chat_stream()` 的 fake-client 结果逐字段一致；工具 fixture 验证
  `knowledge_search` 别名还原为内部 `knowledge.search`、跨分块参数拼接和 `tool_calls` 终态。中立 Trace 只保留
  白名单计数/摘要，正文、reasoning、工具参数和内部工具名不会进入 JSON 投影。
- 坏 choices、delta、content、reasoning、tool、usage、未知工具和空非 Usage 帧均在供应商翻译层以安全错误码
  拒绝；model 冲突、终止后载荷和供应商迭代器异常则由中立装配器 fail closed，异常路径必须 `abort()`，不能
  把异常误封为 EOF。中立合同交付正文时保留首尾空白，只用 `strip()` 判断全空，和旧智谱整流面的行为差异已被
  显式记录。
- `8bcbaa5` 的 conformance 聚焦为 `13 passed`；同 SHA 公共 CI run `33489903978` 已三 job 全绿且 `head_sha`
  精确匹配，包含全部 Trace 脱敏断言，因此该提交范围的本地/公共证据均已闭环，但仍不是真实 streaming 生产能力。
  候选继续未注册，下一项是候选接线裁决，而不是自动把 `capabilities.streaming` 打开。

## 2026-09-01：RQ-194 显式智谱→中立适配接缝设计发现（历史设计阶段）

- RQ-193 的 fake conformance 只能证明分块翻译和中立装配合同相容；是否建立可被调用方显式触发的候选 adapter，
  仍需先冻结调用者身份、请求/模型绑定、事件转换和错误撤出边界。实现文件/API 尚不确定，本轮使用
  `app/providers/<zhipu-neutral-stream-adapter>.py`、`<ZhipuNeutralStreamAdapter>` 和
  `<stream_candidate(request)>` 作为占位符，不能当作现有代码路径。
- 设计候选是单向 `raw chunks → ProviderStreamEvent → ProviderStreamAssembler`：单次只消费一条流，必须观察正常 EOF、
  合法 terminal 和有效 Usage；迭代器异常/取消走 `abort()`，任何合同错误 fail closed，不隐式 retry、recovery 或 ToolRuntime。
- 该接缝只针对 fake/local evidence；不调用真实 API、不读取 Key、不注册 recovery，`capabilities.streaming` 继续为 `False`，
  严格 Flash v1 的 2048/零额外调用和默认路径保持不变。AgentLoop、Workbench、Portal、Account、Auth、路由、预算、统一
  Runtime Trace 与 `production_media=0` 均不动。
- 下一门必须是设计评审；只有评审冻结后才可实现 fake/local 最小版本，再以同一干净 SHA 取得公共 CI。不得把设计草案、
  fake 通过或 CI 通过外推为候选启用、G53-7、领域采用或生产成熟度。后续实现已采用真实 API，以下历史占位符不再
  代表当前代码。

## 2026-09-01：RQ-194 显式智谱→中立适配接缝本地实现发现

- 设计评审后的实现位于 `app/providers/zhipu_stream_adapter.py`，真实类为 `ZhipuStreamAdapter`；
  `ZhipuProvider.stream_adapter(*, tool_stream=False)` 是显式工厂，返回独立的 `ProviderStreamAdapter` port，
  不把 adapter 变成 `LLMProvider` 或自动能力。
- `stream_events(request)` 将一条 OpenAI-compatible 智谱流翻译为 `ProviderStreamEvent`；
  `assemble(request, *, max_output_tokens=None, require_request_identity=True)` 只打开一次流，交给
  `ProviderStreamAssembler` 并返回 `StreamAssemblyResult`。私有 `_open_stream_for_adapter(...)` 负责请求校验、
  thinking/runtime profile、工具 alias 与 SDK open。
- 输出 cap 受 `1..8192` 限制；runtime profile cap、显式 cap 与 `ChatRequest.max_tokens` 取最小值并同时传到
  payload/assembler，不能越过 trusted cap。provider 必须是 `zhipu`，event model 必须匹配绑定 model，默认要求
  request identity；Trace 只保留 request ID SHA-256。
- 只有正常 EOF 才 `mark_exhausted()`/`finalize()`；异常、取消、翻译错误或 close 失败会 `abort("stream_aborted")`、
  保留 typed `ProviderError` 或安全 `zhipu_stream_close`。iterator/raw stream 在 `finally` 关闭，错误/repr/Trace
  均不含正文、reasoning、工具参数、Key 或原始 request ID；适配器无 retry/recovery/ToolRuntime。
- `tests/test_zhipu_stream_adapter.py` 仅用 fake SDK/client，聚焦 `20 passed`（含参数化坏 chunk）；提交
  `a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588` 三 job exact-SHA 全绿，
  证明候选接缝可公共复现但不等于产品/生产能力。默认模型、`capabilities.streaming=False`、严格 Flash v1 2048/零额外
  调用、AgentLoop、Workbench、Portal、Account、Auth、路由、统一 Trace/预算和 `production_media=0` 均不变。
- 下一门是独立裁决候选 runtime 接线范围；不注册候选、不注册 recovery、不执行 G53-7/黄金切片，也不宣称
  生产 streaming 或领域准入。

## 2026-09-01：RQ-195 候选 runtime 接线架构评审发现

- `ZhipuStreamAdapter.assemble()` 的完整合同与候选恢复资格不是同一个判定：它只在真实 EOF、合法 terminal 和有效
  Usage 同时存在时交付 `stop`/`tool_calls`；`length`、缺终止、缺 Usage、读取/翻译/关闭异常会安全拒绝。
- 因此不能捕获 `StreamAdapterError` 就触发 recovery，也不能读取 adapter 私有部分正文/reasoning 来补资格；这样会把半流、
  错误模型或传输失败混入候选白名单。下一设计门需要独立 `BoundaryObservation`，只输出字段状态、finish code、Usage 数字、
  耗时和安全错误码，并复用同一分块/model/sequence/tool/Usage 校验。
- 现有产品 Runtime 只接受同步 `LLMProvider`/已注册 v1 profile；候选 v2 profile 与 fresh-recovery policy 是不同身份，
  直接包装或在 `AgentLoop` 增加分支会扩大预算、Trace、工具回放和默认注册边界。推荐未来使用隔离的
  `CandidateStreamEvaluationHarness`，由调用方精确绑定四元身份并经 `ResponseRecoveryLedger` 结算。
- 当前候选 `execution_allowed=false`，即使未来观察到白名单形状也只能记录 `awaiting_recovery`，不能发第二次请求；严格
  Flash v1 2048/零额外调用、默认模型和全部产品模块保持不变。下一精确 checkpoint 为
  `candidate-runtime-wiring-design / pending`，本轮不新增代码、不做真实 I/O。

## 2026-09-01：RQ-196 候选 runtime 接线设计发现（历史状态）

- 用户已基本决定采用 GLM-5.3-Flash；本轮授权的是候选接线设计门，不是把它静默提升为全产品默认或立即执行真实 recovery。
- 候选必须由不可变 `CandidateRuntimeBinding` 精确绑定 `zhipu`、`glm-5.3-flash`、candidate v2 profile/policy 及
  `primary`/`fresh_recovery` 尝试序号；调用方不能通过 metadata 或资格布尔值伪造身份。
- `BoundaryObservation` 只能保存 body-free 的生命周期、终止码、字段状态、工具计数、有效 Usage 数字、单调耗时、
  model/request SHA-256 和安全错误码。部分正文、reasoning、工具参数、Prompt、Key、SDK 对象和异常原文不进入观察、Trace 或 repr。
- 完整流仍由 `ProviderStreamAssembler` 交付；不完整流只能进入观察/fail-closed。事件的 model、sequence、tool 和 Usage 校验
  必须共享同一核心或通过逐字段 conformance 证明一致，不能捕获异常后直接推导候选资格。
- 候选 v2 transport 必须在 `app/evaluation/` 隔离，承载 8192 单次 cap、90/120 秒窗口、`temperature=1`、`top_p=0.95`、
  SDK retries=0；预算最多 2 attempts/1 次额外调用/32,000 input/16,384 output/180,000ms，unknown Usage 不可当零。
- 当时唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-implementation / pending`；
  先做 fake/local 合同实现与测试，再取得同 SHA 公共 CI，之后才另行裁决 harness、fresh-recovery、G53-7 或生产准入；该实现门已由 RQ-197 推进。

## 2026-09-01：RQ-197 候选边界观察合同实现发现

- `BoundaryObservation` 必须是不可变、body-free 的值对象：只允许生命周期、终止码、字段状态、工具计数、有效 Usage
  数字、单调耗时、model/request SHA-256 和安全错误码；直接构造时也要验证状态与生命周期的一致性，不能让调用方伪造
  `candidate_shape` 或 `complete_text`。
- 完整 assembler 与候选观察器共享事件级验证核心，并保留供应商字段“缺失”和“显式 null”的 presence 区别；这样
  `length + reasoning-only` 可以被准确识别，而不会因 `None` 语义合并而误判。观察路径仍不保存正文、reasoning 或工具参数。
- 观察器采用 fail-closed 与 sticky poison：缺 EOF/terminal/Usage、model/sequence/request identity 冲突、工具元数据不全、
  输出或耗时越界、迭代/关闭异常和状态伪造均不能构造 `ChatResponse`；unknown Usage 不得按零，用户中断类异常必须继续传播。
- 候选 v2 transport 只接受注入 opener，强制 `glm-5.3-flash` candidate profile/policy、8192 cap、90/120 秒窗口和 retries=0，
  不注册 `LLMProvider`、不打开 `capabilities.streaming`，也不触发 recovery 或真实 API。
- 本地候选及相邻回归为 `163 passed`，compileall、diff check、governance 已通过；全量本地首错来自缺少
  `RIFTCOACH_TEST_DATABASE_URL` 的既有 PostgreSQL fixture。当前仍需同一干净提交的 exact-SHA 公共 CI，不能把本地证据写成
  生产准入。

## 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环发现

- RQ-197 实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run `33507627615` 已完成
  exact-SHA 公共验证；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，公共 pytest 摘要为
  `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
- 公共 CI 没有改变候选边界：仍不注册 Provider/Runtime、不打开 `capabilities.streaming`、不发真实 API、
  不执行 recovery/G53-7/黄金切片；严格 Flash v1、默认模型和 `production_media=0` 保持不变。
- 收口后的唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
  下一轮只设计隔离 harness/ledger/Trace，需用户明确继续后才进入。

## 2026-09-02：RQ-199 隔离候选评估台设计发现

- 现有 `ResponseRecoveryLedger` 的构造前提是首回合 `ResponseBoundarySnapshot` 已知；真实
  harness 在 primary I/O 前无法满足该前提。不能用 sentinel snapshot，也不能把 reserve 推迟到
  响应结束后，否则会漏记 open/read/timeout 失败。下一实现需要 candidate-only staged ledger
  session，或在保持旧构造器语义的前提下增加等价的 staged API。
- 一条 normalized stream 只能消费一次。未来 harness 应以单次事件泵共享事件级校验，然后分别
  喂给 `CandidateStreamBoundaryObserver`（O(1)、不保存正文）与 `ProviderStreamAssembler`（一次
  run 内临时保存完整结果）；`length` 可由 observer 观察，但不完整 assembler 结果不能交付。
- receipt 应是新的 body-free envelope，不能直接冒充 `RuntimeTrace` 或把旧 ledger 的 `or 0`
  汇总解释为可用余额。Usage unknown 时要保留 unknown/下界语义，预算状态允许 `within`、
  `exceeded`、`unknown` 三态。
- 当前 activation 必须是不可伪造的 disabled gate；命中候选形状只记录 `awaiting_recovery`，
  不发第二条流。未来若激活，仍须独立凭据、一次额外调用上限和第二次完整请求，不称为 API resume。
- 设计门不改变严格 Flash v1（2048/零额外调用）、`capabilities.streaming=False`、默认
  Runtime、Workbench、Portal/Account、Auth、路由或 `production_media=0`；没有真实 API/Key、
  recovery、G53-7、黄金切片或 8F 证据。下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。

## 2026-09-02：RQ-200 隔离候选评估台本地实现发现

- staged ledger 需要把 `reserve` 与真实边界快照解耦：primary 先占用槽位，观察器封存后
  才构造 `ResponseBoundarySnapshot`、重算候选策略并 settle；这样 open/read/timeout/close
  失败不会漏记，也不必用 sentinel 快照污染旧恢复合同。
- 单次事件泵可以让 observer 与 assembler 共享同一 normalized stream；observer 保持 O(1)
  且 body-free，assembler 只在本次 fake/local 评估内存中暂存完整响应。只有 EOF、终止、关闭
  和有效 Usage 全齐时才允许显式 evaluation consumer 接收，评估结束立即清理正文引用。
- `CandidateEvaluationReceipt` 必须独立于统一 `RuntimeTrace`，只记录候选身份、生命周期、
  字段状态、终止/错误码、ToolCall 计数、Usage/耗时、预算确定性与 SHA-256；未知 Usage 保持
  unknown/None，不能用 `or 0` 推导余额或成本。
- 15 项 harness 聚焦与边界观察、流装配、旧恢复合同相邻回归共 `102 passed`；异常矩阵还覆盖
  显式 null/缺失、重复 reserve/settle、disabled activation、consumer 独立失败和时钟异常。
  Python 3.11/3.13 编译、diff check、governance 均通过。
- 当前实现仍是 candidate-only fake/local seam；没有真实 API/Key、fresh recovery、G53-7、
  Provider/AgentLoop 注册或产品 streaming。下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`。

## 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环发现

- 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的公共 Actions run `33536168224`
  三 job 均成功且 `head_sha` 精确匹配；公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
- 该证据确认 RQ-200 的 fake/local staged ledger、单次事件泵、临时装配和 body-free receipt 在干净公共环境可复现，
  但不证明候选已能进入产品 Runtime，也不证明 recovery、领域质量或生产成熟度。
- 下一步不能由 CI 自动推导为真实调用；候选仍 disabled，下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`。

## 2026-09-02：RQ-202 候选 recovery 诊断边界复核发现

- `CandidateEvaluationReceipt` 的 frozen dataclass 仍可被 `dataclasses.replace()` 重新构造；
  若不在 `__post_init__` 重算，顶层 state/error、attempt decision/assembly 和 budget flag
  都可能脱离真实观察。已增加派生一致性校验，并用负例测试锁住这些边界。
- observer 的 elapsed 限制必须按 attempt spec 的 90 秒执行，不能直接使用候选账本累计
  180 秒；账本仍负责累计预算，二者不能混成一个截止。当前 candidate activation 关闭，
  因而没有第二次请求路径。
- 旧 `glm53_flash_response_recovery_diagnostic.py` 直接导入 SDK/dotenv/Provider，并复用
  `ResponseRecoveryLedger` 的 `or 0` Usage 投影；它是历史真实诊断入口，不适合作为新
  candidate-only 诊断版本，旧文件保持不动。
- 隔离 Windows 工作树的冻结 fixture 原始 CRLF SHA 为
  `fe93c7bab57218cee03371bd1351f8edf52cfb318259045679f68e7f9cad6f02`，计划记录的
  canonical-LF SHA 为 `804520031606cd0a7875fd2287e948a44e9b0100e38e1c44e5ed2619eaffc147`；
  相关旧诊断/运行时测试因此不作为本轮证据，不修改 fixture 或 plan。
- 下一精确项收紧为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`；
  是否建立新诊断版本仍需再次授权。

## 2026-09-02：RQ-203 版本化候选 recovery 诊断协议设计发现

- 新协议必须与旧同步诊断器隔离：旧入口把供应商 SDK、真实 I/O、恢复决定和落盘混在一起，不能通过增加开关获得可追溯的 v2。
- v2 的身份先于请求摘要冻结，摘要只允许角色、字段存在性、长度和工具数量等形状信息；任何调用方可控字段都不能选择 profile、policy、activation 或资格布尔值。
- `reserve` 必须发生在每次潜在 I/O 之前，`settle` 只能由可信观察推导；fresh recovery 是完整新请求，不能沿用 resume、SDK retry、AgentLoop retry 或 ToolRuntime 副作用。
- 资源证据必须三态：Usage 或预算未知时保持 `null/unknown`，费用只有冻结且可验证的单价快照才能标为估算，不能用零值或历史价格补齐。
- 分段单调延迟和第一失败现场比单一总耗时更能解释 transport/protocol/completion 差异；原始异常、正文、reasoning、Prompt、工具参数、Key 和 request ID 均不进回执。
- 设计退出后，下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`；实现仍需另行授权。

## 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现发现

- 将新诊断器与旧同步诊断器、产品 Provider 和统一 Runtime Trace 分离是必要条件；
  `app/evaluation/candidate_recovery_diagnostic_v2.py` 只依赖 provider-neutral 模型/策略/
  流合同与标准库，静态导入检查未发现 SDK、网络、Key loader 或产品 Runtime 依赖。
- 请求和回执的 allow-list 必须在值对象构造、`from_dict()` 和最终 JSON 三层同时执行；
  仅检查顶层 JSON 会让嵌套正文或工具字段漏出。字段存在性与长度也要分开保存，不能把
  缺失和显式 `null` 合并。
- `reserve`/`settle` 的时序与延迟采样相互独立：时钟反转或不可用时延迟保持 `null`，但
  预留槽位仍必须结算；关闭/控制异常不能被普通 close 错误覆盖，控制异常要在安全回执后继续抛出。
- 未验证价格快照不能生成估算费用；Usage、预算和成本都需要明确的 unknown 状态，不能
  用 `or 0` 制造可用余额。disabled activation 命中候选形状只能留下等待 recovery 的诊断，
  不能发第二次请求。
- 新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归
  `82 passed`；compileall、diff check 和静态 no-I/O/import 检查通过。系统 Python 3.13
  已补装 `pytest 9.1.1`，但项目依赖仍由仓库 `.venv` 提供。
- 当前唯一下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`；
  公共 CI 与协议 dry-run 需要绑定同一干净实现提交，不能把本地 fake 证据写成生产准入。

## 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环发现

- 提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 Actions run `33598541029` 对同一干净实现完成
  exact-SHA 公共验证：`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest
  `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，数据库控制面 `201 passed, 1 warning`。
- 本地 fake transport 演练确认 v2 生命周期可在一次 primary 调用内完成 reserve/open/observe/settle/receipt，
  回执可写为临时 canonical body-free JSON（3900 bytes），且 disabled gate 不产生第二次调用。
- 公共 CI 与协议演练只证明候选评估接缝可复现，不提升为产品 Runtime capability；真实 recovery、G53-7、
  黄金切片、生产安全/部署/合规和 8F 仍需单独授权与证据。
- 当前唯一下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`。

## 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察发现

- 在实现提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的干净隔离工作树上，诊断代码提交
  `0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run `33603143606` 三 job exact-SHA 全绿；
  一次性授权只产生 1 次 primary，SDK retries 为 0，未发生第二次 recovery。
- 普通智谱 `zhipu/glm-5.3-flash` 流实际到达并产生 reasoning、可见正文、`finish_reason=stop` 与 EOF；
  首事件为 `3078ms`，首个可见正文为 `151453ms`，总延迟为 `175875ms`。但 Usage 缺失、close 失败，
  单次 90 秒 observer 门在晚到事件中触发，故不能把 stop/EOF 单独解释为完整成功。
- 回执为 `fail_closed / elapsed_limit`，`assembled_complete=false`、`calls_reserved/settled=1/1`、
  成本 unknown；持久 canonical body-free 文件 SHA-256 为
  `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`（`4355` bytes）。
  `open_elapsed_ms=0` 是惰性流生成器计时起点，不是网络握手零耗时。
- 该样本排除了“完全没打到接口”这一解释，但不能裁决 API/Key、模型一般能力、领域质量或生产成熟度；
  它暴露了 SDK 读超时和总墙钟截止的差异：事件持续到达时，observer 直到晚到事件才发现 90 秒门，
  物理请求可延长到约 176 秒。候选 activation 仍 disabled，产品默认和前端/Workbench 边界不变。
- 下一精确项改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  先离线验证硬墙钟取消、流关闭和 Usage/终态尾帧处理，之后才讨论新的真实请求授权。

## 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧发现

- 旧的同步 iterable 只能在 `next()` 返回后采样时钟；要让 attempt 的 90 秒窗口覆盖
  整个读取过程，必须提供显式 `CandidateStreamSession`，由 watchdog 监督绝对
  `started_at + deadline`，并要求会话的 `cancel` 能非阻塞地唤醒挂起读取。
- 不能把“有 `open_stream_session` 方法”当成 opener 已被证明可取消：没有显式
  `session_opener` 时可在 legacy opener I/O 前拒绝；显式 opener 返回值仍须在调用后
  验证，且 opener 自身永久阻塞时普通 Python 没有安全强杀路径。
- 智谱候选流需要显式 `stream_options.include_usage` 才有机会收到 Usage-only 尾帧；
  terminal+Usage 或 terminal 后一个合法 Usage-only 尾帧才可完整，缺 Usage、迟到内容、
  关闭失败都不能被补成成功/零成本。
- `ZhipuStreamSession.cancel()` 目前通过 SDK `close()` 协作收口；本地 fake 已证明
  取消/关闭状态和失败主次可记录，但 SDK close 的非阻塞性与唤醒能力尚无供应商层实证，
  必须保留为真实重测前置闸门。
- 本轮修正了取消内部 close 失败被幂等 follow-up 覆盖的次级证据丢失，并为显式 opener
  返回 legacy iterable 增加 fail-closed 回归；没有发新的真实 API。
- 当前唯一下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
  先做同 SHA 公共 CI，再决定是否授权新的真实观察。

## 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共验证发现

- RQ-207 实现提交 `015b022bfce6d03452f753794ac126a377f8355b` 的 Actions run `33613113829`
  三 job 均 `completed/success` 且 `head_sha` 精确匹配；公共 pytest 为
  `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为
  `201 passed, 1 warning`。
- 同一公共 run 的网页契约/生产包、媒体审计工具链、RAG v1/独立 4M holdout、治理、compileall
  与 Harness dry-run 均通过；本地四文件聚焦仍为 `67 passed`，本轮真实 API 调用为 `0`。
- 公共 CI 只证明 candidate-only 接缝可复现，不能证明同步 opener 可被安全中断，也不能替供应商
  SDK close 的非阻塞/唤醒证据；候选继续 disabled，产品默认、Workbench、Portal、Auth、路由、
  `capabilities.streaming` 与 `production_media=0` 不变。
- 当前唯一下一精确项推进为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  新的真实观察必须获得单独一次性授权，不能因 CI 通过自动重试或注册候选。

## 2026-09-02：RQ-209 候选真实流硬墙钟与关闭边界发现

- 真实候选 primary 在 `90015ms` 由诊断层记录为 attempt 硬截止并安全收口为 `fail_closed / elapsed_limit`；
  这证明诊断层在墙钟到点作出 fail-closed 决定，但底层事件泵/SDK 读取是否已经收口仍未知，不能据此改写
  旧 RQ-206 的约 `176s` 物理读取窗口。
- 本次只观察到首事件/打开计时 `3421ms` 和非空 reasoning；没有可见正文、terminal、EOF 或 Usage。回执为
  `calls_reserved/settled=1/1`、Usage missing、费用 unknown，未执行 recovery 或重试。
- `close_state=failed` 是组合会话的资源清理投影；不能从 body-free 回执推断是供应商 SDK response、Python
  generator/迭代器还是其他资源失败，也不能把截止后约 15ms 的收口单独解释为 SDK `response.close()` 已唤醒读取。
  provider-level close/wakeup 仍是未证实闸门。
- 回执 `observation.elapsed_ms=0` 只是截止前未结算的初始观察值，真实时序应读取 latency 的 `90015ms`；
  attempt `budget_state=exceeded` 与累计 token unknown 的整体预算状态不矛盾。
- 证据提交 `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 目前只代表本地保存，未宣称公共 CI；候选、产品 Runtime、
  默认模型、Workbench、前端与 `production_media=0` 边界不变。下一精确项仍等待新的明确一次性授权。

## 2026-09-03：RQ-210 候选会话分资源关闭报告发现

- RQ-209 的组合 `close_state` 无法归因到某个底层资源；在不改变旧回执的前提下，`ZhipuStreamSession` 现在只在内存中分别记录迭代器与外层 SDK stream wrapper 的关闭状态，并用 `shared_resource` 标明对象别名。这里的 “SDK stream” 是外层 SDK 包装器，不是底层 HTTP response 的证明。
- close 会继续尝试已拥有的资源，控制类异常不会阻止其他资源的清理；旧 `close_failed`/supervisor/receipt 投影保持兼容。没有 close/exit hook 时报告保持 `not_observed`，而不是假报成功。
- 兼容性意味着旧 supervisor/receipt 在“无 hook 且无失败”时仍可能聚合出 `closed`；这只是历史组合投影，新报告的 `not_observed` 才是本层资源观测状态，不能互相替代。
- `cancel()` 仍同步经过 SDK close；本门没有 `cancel_state`、`wakeup_observed` 或 raw-response handle，因此不能宣称非阻塞、唤醒挂起 `next()` 或物理连接已关闭。并发 close 先标记 closed 后再清理的旧时序仍存在，报告应在拥有者 close 返回后读取。
- RQ-209 v2 receipt/schema 2.0.0、canonical JSON/SHA、候选 gate 和产品边界均未改变；同一实现提交的 exact-SHA 公共 CI 已成功，之后若讨论 provider-level 观察或持久 schema，仍需单独授权。

## 2026-09-03：RQ-211 候选 provider close/wakeup 观察发现

- 探针在 exact-SHA 公共绿灯的 `c31127b3c780fe4c493966d8b60f942d3b773fd4` 干净快照上只发送
  1 次真实请求；会话打开并在 `78ms` 内得到首段，安全类别为 `reasoning_seen/content_seen`。
- 这次读取路径没有形成 pending reader，结果只能记为 `not_pending`；因此 cancel 没有执行，
  `reader_woke=false` 也不是“唤醒失败”，而是本次没有可供唤醒的挂起读取。
- 退出时迭代器、外层 SDK stream wrapper 与组合关闭投影都为 `closed`、两资源不同对象；这能说明
  当前拥有资源的关闭报告，但不能证明底层 HTTP response 已取消或 close 在 pending-read 情形下非阻塞。
- body-free 回执为 `908` bytes，SHA-256
  `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`，绑定同一个 c311
  implementation/diagnostic/input-plan SHA；不含正文、reasoning 原文、Key、Authorization 或 request ID。
- 后续测试加固提交 `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c` 的公共 run 被外部取消，
  不应混入 c311 的真实回执证据。若还要裁决 wakeup，需要先设计能稳定制造 pending-read 的新版本协议，
  而不是重复同一请求；候选与产品边界保持不变。

- 随后提交 `1c669e0` 为公共 provider capability 扫描补上 RQ-211 receipt/schema 分派；Actions
  `33666132282` 三 job exact-SHA 全绿（pytest `2268 passed, 145 skipped, 1 warning, 127 subtests passed`，
  PostgreSQL `201 passed, 1 warning`）。这验证的是持久回执的合同识别，不是新的模型调用；c311 回执仍唯一真实样本。

## 2026-09-03：RQ-212 离线 close/wakeup 回放发现（公共闭环完成）

- RQ-211 的 `not_pending` 不能通过重复真实请求稳定变成 pending；固定内存 Event 闸门拆出的五种生命周期，
  让观察器分类问题与供应商行为保持分离。
- 回放入口不读取 dotenv/凭据、不实例化或调用 SDK client、不建立网络连接；普通包导入可能加载 SDK 依赖模块，
  因此文案保持这一准确边界。
- 离线回执使用独立 `offline_fake` 来源、供应商调用数 `0` 和离线路径；`observer_call_count=1` 与
  `fake_session_open_count=1` 只是本地夹具计数。writer 以显式 offline root、canonical JSON 和 create-only
  方式阻止误写 provider capability 目录或覆盖既有证据。
- 最终 v2 回执为 `data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`，
  `2220` bytes，SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`，三身份 SHA 绑定
  实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec`；v1 仅为旧 HEAD 的提交前演练。
- 实现提交的公共 Actions `33707313651` 三 job exact-SHA 全绿（pytest `2284 passed, 145 skipped, 2 warnings,
  127 subtests passed`；PostgreSQL `201 passed, 2 warnings`；packaging-smoke 通过），本地聚焦 `37 passed`、
  compileall、diff check、governance 均通过。
- 离线结果仍不能推导 provider-level close/wakeup、候选注册、G53-7、黄金切片或生产成熟度；下一精确 checkpoint
  为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-real-observation / pending-user-authorization`，
  是否执行真实观察需单独授权。

## 2026-09-03：RQ-213 候选 close/wakeup 第二次真实观察发现

- 在 RQ-212 公共闭环后的 exact-SHA 公共绿灯提交
  `a396412f7cd0f2e923536cf55f715dd56251aae5` 上，只发送 1 次普通智谱
  `zhipu/glm-5.3-flash` 请求；SDK retries 为 0，父进程边界为 30 秒，没有 retry、recovery 或第二请求。
- 新回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`，
  909 bytes、SHA-256=`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`；实现、诊断和
  输入计划身份均绑定该 SHA，且回执仍不含正文、reasoning 原文、Key、Authorization、request ID 或 body。
- 会话在 172ms 内打开并产生 `reasoning_seen/content_seen`；仍为 `not_pending`，没有 pending reader，
  所以 cancel 未执行。`reader_woke=false` 不能解释为唤醒失败；iterator、SDK wrapper 和 composite
  close 投影均为 `closed`，只是本层资源事实。
- 第二次样本仍没有回答 provider close/wakeup 问题。重复同形状请求不会稳定制造 pending-read；若继续，
  应先另立能控制读取闸门的协议/实验，而不是无界消耗真实调用。候选 gate、产品 Runtime、默认模型、
  Portal、Account、Workbench、Auth、路由和 `production_media=0` 均保持不变。

## 2026-09-03：RQ-214 SDK/HTTP transport gate 离线预检发现

- 直接重复自然请求无法稳定制造 pending-read；本批改用本机 `MockTransport`，但仍走真实
  OpenAI SDK、显式 Zhipu 候选适配器和既有观察器，因而可以把客户端读取生命周期与 provider
  服务端行为分开。
- 固定 SSE 帧边界的 `after_first_event`、`before_first_event` 两阶段都形成 pending reader；
  response close 能唤醒读取器，transport stream 也看到下游关闭。回执只保留状态/布尔投影，
  不保留正文、原始帧、请求头、异常文本或凭据。
- 适配器在并发生成器关闭时暴露 `iterator=failed`、`sdk_stream=closed`、
  `composite=failed` 的 close race；这不是 reader wake 失败，也不是 provider-native 结论，
  当前不在评估预检中擅自改顺序。
- 离线协议标记 `offline_sdk_transport_fixture`、`provider_call_count=0`、`network_used=false`，
  与 provider capability 回执目录隔离。候选仍 disabled/未注册，产品 Runtime、默认模型、
  AgentLoop、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。
- 下一精确 checkpoint 是 `candidate-transport-gated-real-observation / pending-user-authorization`；
  公共 CI 闭环后才考虑一次受控的官方 TLS transport 包装真实请求。

### RQ-214 回执身份与公共闭环

- 离线回执 `data/evaluation/results/offline/zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json`
  为 `1693` bytes，SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`；
  canonical round-trip 通过，三份身份 SHA 均为实现提交
  `4c220c5751288ad77c589d2e0e581690085803c0`。
- 同 SHA Actions run `33712055286` 三 job 全绿：pytest `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`，
  PostgreSQL `201 passed, 2 warnings`，packaging-smoke 通过。
## 2026-09-03：RQ-215 SDK/HTTP transport gate 一次真实观察发现

- RQ-214 的本机 `MockTransport` 预检在同 SHA 公共 CI 后得到一次真实验证；只发送 1 次
  `zhipu/glm-5.3-flash` 请求，SDK/HTTPX retries=0，父进程 30 秒硬截止，没有 retry、recovery 或第二请求。
- 官方 TLS transport 外层 gate 在首帧前进入；真实流启动后形成 pending reader，response close 后
  `reader_woke=true` 且耗时 `31ms`，同时 `upstream_event_seen=true`、`upstream_stream_close_seen=true`。
- 取消抛出安全错误码 `zhipu_stream_close`；iterator/composite close 投影为 `failed`、SDK stream 为
  `closed`，所以结论是 `client_wakeup_close_race`。reader 唤醒和清理竞态必须分开解释。
- 真实回执为 body-free、canonical 的
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`，
  `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`；
  provider/transport 请求数均为 1，网络标记为 true。
- 该样本只证明真实流启动后本机受控停顿下的客户端行为，不证明 provider-native close/wakeup、
  底层 HTTP response 独立可取消、模型一般能力或生产 streaming。候选仍 disabled/未注册，产品
  Runtime、默认模型、Workbench、前端和 `production_media=0` 不变；下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

## 2026-09-03：RQ-216 候选 reader-owned close 顺序修复

- [diagnosis] `client_wakeup_close_race` 的本地根因是取消线程在 reader 线程仍阻塞于 `next()` 时跨线程调用 Python iterator `close()`；外层 SDK response 已能唤醒 reader，但迭代器关闭会与生成器栈交叉。
- [decision] `ZhipuStreamSession` 记录活跃 reader；有活跃读取时先关闭外层 SDK response，并把 iterator close 延后到 reader 自己的 `finally`。没有活跃读取时保持逐资源、最多一次关闭；共享资源仍只关闭一次。
- [evidence] 新增阻塞读取回归，收紧 RQ-214 两阶段 transport-gate 断言；候选聚焦回归 `61 passed`，compileall、`git diff --check`、governance 通过，真实 API 调用为 0。
- [boundary] 这是候选适配器本地协议修复，不是 provider-native 能力或生产 streaming 结论；候选仍 disabled/未注册，产品 Runtime、默认模型、Portal、Account、Workbench、Auth、路由、G53-7、黄金切片与 `production_media=0` 不变。旧 RQ-215 回执不可变。
- [next] 当前唯一精确 checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`；先提交并做同 SHA 公共 CI，再回到真实观察决策点，不自动发新请求。

## 2026-09-03：RQ-221 低思考候选 profile 与真实探针发现

- RQ-219 的 `max + 8192` 超时只能说明那组预算/档位没有在 90 秒内交付；不能直接把
  `low + 4096` 当作默认修复。为保持归因，候选 profile 只改变思考档位与输出上限，
  provider/model、采样、冻结上下文和调用次数均显式记录。
- 正常产品 `ModelRuntimeProfile` resolver 不认识该 profile；只有显式候选构造器能绑定，
  且 `execution_allowed=false`。这把“候选实验允许发一笔请求”和“产品可以自动采用”
  分成两个不可混淆的开关。
- 一次真实无工具探针在 `20.735s` 得到 `finish=stop` 和有效 Usage，说明该窄上下文
  能完整规范化；它没有覆盖工具回合、AgentLoop、多轮恢复、领域质量、成本/延迟稳定性
  或 provider-native streaming。
- 回执提交后的 Actions `33747392719` 首次暴露了公共 capability contract registry 仍按旧
  schema 解析新候选回执；这不是 API/模型失败。已在测试入口增加显式低档候选 schema 分支，
  本地聚焦回归通过；该失败 run 不作为绿色证据，后续公共 CI 必须绑定修复后的 exact SHA。
- 回执必须 create-only、body-free；旧 RQ-219/RQ-220 证据不可覆盖。候选仍 disabled，
  严格 Flash v1、默认模型和产品边界不变。下一步应先设计独立 held-out 领域门，重新
  绑定新鲜 G53-3、预算与终态/Usage 判定，再决定是否执行。

### RQ-216 公共闭环补充

- [public-ci] 实现提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions run `33726209532` 三 job exact-SHA 全绿；公共 pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL 与 packaging-smoke 通过。
- [accepted] 公共 CI 只证明候选关闭顺序修复可复现；不改变 RQ-215 旧回执，不增加真实请求，不提升候选注册、provider-native close/wakeup、生产 streaming 或 8-Core 能力。
- [next] 当前唯一精确 checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`；下一动作是等待用户对是否重新做一次受控真实观察的明确决定。

### RQ-216 公共 CI 与 RQ-217 真实观察的衔接

- RQ-216 的公共 CI 只证明候选关闭顺序修复可复现；它本身不提供 provider-native 或产品准入证据。
- RQ-217 在同一修复后的干净身份
  `3e028b1217f1274152ba161993287f29188a1b73` 上只发送 1 次真实请求。官方 TLS transport
  外层首帧前 gate 进入，pending reader 形成并被 close 唤醒；`cancel_status=returned`，
  iterator/SDK/composite close report 均为 `closed`。
- `gate_released=false` 是 gate 持住首帧前停顿、等待 close 唤醒的协议成功条件；不能把它
  误报成未释放资源或网络泄漏。
- 回执为 body-free、canonical round-trip 可复核，`provider_call_count=1` 与
  `transport_request_count=1` 一致；没有把响应正文、Key、headers、request ID 或异常文本
  写入证据。
- 该样本把 RQ-215 的客户端竞态收敛为 `client_wakeup_clean`，但仍只回答本机受控客户端
  生命周期问题；provider-native close/wakeup、模型一般能力、生产 streaming、G53-7、
  黄金切片和 8F 仍未证实。候选、默认模型和产品链路边界保持不变。

## 2026-09-03：RQ-218/RQ-219 Flash 协议与候选 8192 诊断

- RQ-218 在实现 `aa22cea0daeb443b635706144ccbfa66185670c4` 上重新完成 G53-3，精确
  3/3 通过；A1 结构化合同用时 `20234ms`，A2 工具往返用时 `14938ms`。回执 SHA 为
  `feeb7fd7eec2643ca692bd6182fd94a04abed354b17b892029402c0217641e99`，对应证据提交
  `4b6cd5807f40f6a8dd469f21c688be861261d20c` 的公共 CI 已闭环。
- RQ-219 在同一公共绿灯身份上只发送 1 次候选 primary；8192 输出/90 秒硬墙钟在
  `fail_closed / elapsed_limit` 收口，未执行 recovery、retry 或第二请求。回执 SHA 为
  `21350d7883b4d2eea30e0467a7b8c23eed3a3ad5a9deeb309c44f8ded5cf3f84`；证据提交的 Actions
  run `33735717434` 已 `completed/success`，三 job exact-SHA 公共闭环完成。
- 归因边界：G53-3 的协议可达与长响应的终态完成度必须分开。8192 超时不能直接归因于
  模型质量、账号权限或 provider-native streaming；下一批先用 fake/fixture 独立观察
  思考档位、流终态、Usage 尾帧和恢复决策。
- 下一精确 checkpoint：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

## 2026-09-03：RQ-220 响应档位—终态—恢复离线拆分

- 新增离线矩阵 `app/evaluation/glm53_flash_response_profile_split.py`，只组合既有候选
  observer 与 response policy；不构造 SDK client、不读环境 Key、不联网。
- 9/9 fixture 通过：正常 stop/tool_calls、候选 `length` reasoning-only、部分正文、
  缺/非法 Usage 与 elapsed timeout 的状态和安全码均按预期分开；候选恢复动作明确为
  `blocked_activation`，没有第二调用。
- 该结果只说明本地合同的归因能力。实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` /
  Actions `33738050233` 与回执提交 `ebb09a525b3340f31ba71821b894b4a142dfb4e7` /
  Actions `33738673832` 均三 job `completed/success`；回执为 `6209` bytes、SHA-256
  `32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`，provider calls=0、
  network=false。当前下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

## 2026-09-03：RQ-222 低思考候选独立领域门设计裁决

- [decision] 不重跑已消费的 G53-4/G53-7 旧考卷，也不把 RQ-221 的窄探针成功升级为产品准入；采用版本化的 evaluation-only 候选作用域和共享请求策略接缝，正常产品 Runtime resolver 继续拒绝候选。
- [boundary] 新门使用全新的 oracle-blind 三案例 held-out 资产；每案最多 4 次、全域最多 12 次，单次 4096 输出、Agent/工具 90 秒、传输 120 秒，token 墙为 24,000/72,000；无 retry/recovery/revision，首个不安全失败停止，评测关闭 deterministic fallback。设计阶段 provider calls=0。
- [evidence] 设计记录为 `docs/adr/0091-design-glm53-low-profile-heldout-domain-gate.md`、`docs/plans/2026-09-03-glm53-low-profile-domain-gate-design.md`、`docs/learning/8e-glm53-low-profile-domain-gate-design-walkthrough.md`；没有新增真实回执或产品代码。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / pending`；下一步只做候选作用域/请求策略的离线 TDD，之后才考虑同 SHA 的 G53-3-L 和新考卷冻结。
