# RiftCoach 路线变更历史

本文记录 2026-08-01 以来路线为什么变化，以及每条历史结论目前是否仍有效。
它不替代 `docs/project_execution_state.md` 的当前状态，也不把对话中的每个建议
都升级为项目需求。

## 状态标签

- `CURRENT`：当前仍有约束力；
- `IMPLEMENTED`：已有代码或文档，并有可重复验证证据；
- `SUPERSEDED`：曾经提出，但已被后续明确纠正或替代；
- `CONDITIONAL`：只有真实 Bad Case、评测和 ADR 支持时才采用；
- `UNRESOLVED`：历史上存在明确承诺或冲突，尚需在原检查点裁决。

## 证据裁决规则

1. 最新的用户明确纠正或确认优先于更早的助手提案。
2. 用户的疑问、偏好举例、PDF、网页端 GPT 建议和参考项目都不是自动需求。
3. 代码和测试证明“已经实现了什么”，不能自行改写教学顺序或完成标准。
4. 仓库的当前状态只看 `docs/project_execution_state.md`；本文件解释其来历。
5. 专门导出的 Part 1、Part 2、补充材料和后续 Codex 讨论用于重建最新决策；
   1198 页的完整 GPT 导出只做定向查漏，因为其中同时保留了大量已废止方案。

## 时间线

### 2026-08-01：旧 planning 检查点

- `IMPLEMENTED`：建立了路线校准计划和技术采用分析。
- `SUPERSEDED`：该计划停在“0-8 详细规划 Phase 3”，其中 Skill、Loop 等微观
  编号随后被 v1.2/v1.3 改写，不能继续作为当前状态源。
- `CURRENT`：固定 0-8 九个主阶段；平衡技术亮点、实现风险和面试可解释性；
  参考项目必须筛选，不能整体搬入。

### 2026-08-01：v1.2 阶段内细化

- `CURRENT`：形成 `3G -> 5A -> 5B -> 5C -> 5D -> 5E -> 5F` 的阶段内
  顺序；SDK、LangGraph、Multi-Agent 既不能硬塞，也不能不经分析一律拖到最后。
- `CURRENT`：多模型首先属于 Provider 层；Agent SDK 不替代领域核心、质量
  Harness 或 Tool Runtime。
- `SUPERSEDED`：Pi 曾短暂被当成默认主线候选；后来改为真实业务上的采用实验。

### 2026-08-02：v1.3 校准

- `CURRENT`：增加 `4M` RAG 独立门禁、`5P` 早期产品纵向切片、
  AgentRuntime V1/V2/V3 和阶段 8 的 `8-Core`/`8-Advanced` 双轨。
- `CURRENT`：早期 API 切片在本地 Runtime 可运行后开展；完整 SQL、Session、
  Memory、SSE 和前端仍属于阶段 6 及以后。
- `CURRENT`：OP.GG 标准 MCP 通过领域 Adapter 接入，不能让业务层依赖原始字段。

### 2026-08-02 至 2026-08-04：3G-1 至 3G-3

- `IMPLEMENTED`：Tool Calling 内部消息协议、Provider Capability Negotiation、
  Provider Registry 已实现并测试。
- `CURRENT`：Registry 只支持显式解析和选择，不执行任务级自动模型路由，也不
  偷偷 fallback。
- `SUPERSEDED`：曾短暂提出 GLM+Qwen 或 DeepSeek+Qwen 作为核心双模型，并把
  3G-4/5/6 改成连续接入任务；用户质疑过度后，该方案撤回。
- `CURRENT`：GLM 是当前唯一真实基线；DeepSeek、Qwen 等仍是候选。真实第二
  Provider、跨 Provider Tool Calling 和自动模型路由等真实 Skill/Agent 场景出现后
  再用同一评测集触发。
- `CURRENT`：显式模型选择、任务级自动路由和 Multi-Agent 是三个不同概念。

### 2026-08-04：4M RAG 独立评测门禁

- `IMPLEMENTED`：加入 7 条小型独立保留案例、数据集角色、污染记录、拒答和
  引用支持门禁。
- `CURRENT`：这些结果证明门禁可运行，不证明 RAG 已充分泛化；近期不因此
  引入 Milvus、Elasticsearch、Neo4j 等重型基础设施。

### 2026-08-04：5A 最小 Agent Loop

- `IMPLEMENTED`：完成 Provider-neutral 的单进程受限 Loop，并用 Fake Provider
  加真实 `knowledge.search` 验证 ToolCall、白名单、预算、Observation 和停止原因。
- `CURRENT`：它不证明任何真实 Provider 已完成 Tool Calling。

### 2026-08-05：5B Skill Contract

- `IMPLEMENTED`：建立 `manifest.yaml + SKILL.md + Pydantic I/O`，并完成唯一
  真实样板 `recent-form-review`。
- `SUPERSEDED`：曾把近期复盘、单局复盘和报告事实审查都归类为 Skill；后续
  源码审计确认事实审查已由 Harness Evaluator 完整承担，分类由 ADR-0009 修正。
- `CURRENT`：简单查询不必包装为 Skill；后续 Skill 数量由多步骤、独立权限、
  I/O、成功标准和评测价值决定。

### 2026-08-05：Prompt 与横向能力审计

- `CURRENT`：Prompt/Context Engineering 不是临时新增能力，但下面的精确落点是
  当天根据依赖关系做的正式细化：阶段 2 Prompt V0；5B Skill 指令；5D Context
  Assembly V1、结构化输出和不可信边界；5E 版本、Trace、Usage 和预算；阶段 6
  加 Session/Memory；阶段 7 加外部 Meta；阶段 8 加 Compaction 和隔离上下文。
- `IMPLEMENTED`：建立架构能力覆盖矩阵。
- `SUPERSEDED`：仅靠能力矩阵即可防止漂移的隐含假设。矩阵后来也被错误更新，
  因此它只能做横向检查，不能替代唯一当前状态和活动计划。

### 2026-08-05：5C 原始六个检查点

- `CURRENT`：5C-1 Router Contract；5C-2 Skill Catalog；5C-3 Deterministic
  Router；5C-4 Rejection/Ambiguity；5C-5 Router Evaluation；5C-6 Model
  Fallback Decision。
- `IMPLEMENTED`：5C-1、5C-2、5C-3、5C-4 已分别完成；5C-4 独立补充了
  排除合同不变量、候选顺序和域外硬负例验证。
- `IMPLEMENTED` 但未收尾：5C-5 已有 15 条参与校准的开发集、CLI 和基线，
  不是独立 holdout。
- `CONDITIONAL`：5C-6 只做是否需要模型兜底的正式决策，不默认实现 LLM Router。
- `UNRESOLVED`：当日曾明确“5C-1 至 5C-4 稳定后增加另外两个真实 Skill，再做
  真实多 Skill 评测，5C 不应只靠一个真实 Skill 完成”。当前尚未实现，且没有被
  后续明确撤销。进入 5C-5 收尾前必须向用户解释并确认维持还是修订这一时序。

### 2026-08-06：5C 压缩事件与治理修复

- `SUPERSEDED`：一次实现批次将 5C-3、部分 5C-4 和初版 5C-5 合并后，文档
  错误宣称“5C 完成，下一步 5D”。
- `CURRENT`：用户指出阶段压缩；现已恢复六个检查点并独立完成 5C-4。进入
  5C-5 前的唯一下一步是首批真实 Skill 时序裁决，不能进入 5D。
- `IMPLEMENTED`：新增根级工作约束、唯一执行状态、追加式需求账本和活动计划。
- `IMPLEMENTED`：为唯一执行状态增加机器可读元数据，并把治理一致性预检接入
  pytest 与 CI；活动计划偷跳到 5D 的负例会失败。
- `CURRENT`：每次需求或检查点变化后必须同步状态、计划、路线冲突和测试证据。

### 2026-08-06：首批 Skill 调用边界裁决

- `SUPERSEDED`：默认把首批三个真实 Skill 全部作为用户 Router 候选的隐含假设。
- `SUPERSEDED`：曾决定把 `report-fact-check` 做成内部 Skill，并先增加 Manifest
  调用模式；该方案只完成 ADR-0008 草案，没有进入功能代码。

### 2026-08-06：事实审查源码复核与分类修正

- `IMPLEMENTED`：复核 `EvaluatorStep`、`ChatEvaluationAdapter`、
  `ReviewHarness`、独立评测 CLI 和对应测试，确认事实审查已有完整、可复用边界。
- `CURRENT`：首批 Skill 为 `recent-form-review` 与 `single-match-review`；事实审查
  是强制 Harness Evaluation Policy，不是第三个 Skill，也不进入 Router。
- `SUPERSEDED-BEFORE-CODE`：取消 `Skill Invocation Contract` 和
  `report-fact-check` Skill 两个未实现准备项；未来只有真实独立用例才重新评估
  内部 Skill 调用模式。
- `IMPLEMENTED`：`single-match-review` 已建立，事实审查仍按 ADR-0003 强制
  执行，没有被删除或降级。
- `IMPLEMENTED`：ADR-0008 保留被取代方案，ADR-0009 记录最终裁决。

### 2026-08-06：第二个真实用户 Skill Contract

- `IMPLEMENTED`：新增 `single-match-review` Manifest、SKILL.md 和独立 Pydantic
  I/O；复用 Summary v1.0，目标 match ID 必须唯一，不向 Skill 开放 Riot API。
- `IMPLEMENTED`：短局仍可单局审查；Timeline 缺失保持显式未知；两个真实候选的
  近期选择、单局选择、混合范围歧义、裸 ID 拒绝和域外否决已有直接单测。
- `SUPERSEDED-BEFORE-COMMIT`：初版“更具体单局范围优先 + 连接词排除双任务”被
  双任务语序 Bad Case 推翻；最终规则是两种范围同时出现一律 `ambiguous`。
- `IMPLEMENTED`：`recent-form-review` 触发合同变化后由 `0.1.0` 升级为 `0.2.0`。
- `CURRENT`：5C-5 正式进行中。旧 15 条单 Skill 开发/校准结果先冻结为历史基线，
  再建立双 Skill development 与 independent holdout；不得提前进入 5C-6 或 5D。

### 2026-08-06：5C-5 第一批数据生命周期

- `IMPLEMENTED`：旧单 Skill 15 条案例和结果已原样移入 history 目录，并以 SHA-256
  和重建来源 Manifest 固定；精确未提交运行 SHA 不可恢复，未被伪装成已知证据。
- `IMPLEMENTED`：双 Skill development v2（23 条）与 independent holdout v1（12 条）
  已建立，数据集强制声明 role、污染记录、案例数量和候选 Skill 版本快照。
- `IMPLEMENTED`：development CLI 默认拒绝 held-out 数据，holdout 运行需要显式
  确认规则已冻结；本批只验证生命周期门禁，没有运行新数据集正式 Router 成绩。
- `CURRENT`：下一批只运行 development v2 并分析误路由；holdout 仍不得用于调规则，
  `5C-6` 与 `5D` 继续被阻止。

### 2026-08-06：5C-5 第二批 development 验收

- `IMPLEMENTED`：双 Skill development v2 已正式运行并保存结果；23 条全部精确
  匹配，selection/rejection/ambiguity accuracy 均为 `1.0`，错误选择率为 `0.0`。
- `CURRENT`：该开发集参与过规则校准，成绩只作为回归与规则冻结证据，不能表述为
  自然语言泛化成绩。
- `CURRENT`：当前候选版本与确定性规则已经冻结；下一批只单次运行 independent
  holdout v1，失败原样保存且不得用于反向调规则；`5C-6` 与 `5D` 仍被阻止。

### 2026-08-07：5C-5 第三批 holdout 验收

- `IMPLEMENTED`：在确认冻结点到当前规则零差异后，independent holdout v1 只运行
  一次并原样保存；12 条中 11 条精确匹配，错误选择率为 `0.1667`。
- `IMPLEMENTED`：唯一失败把“最近键盘的表现”误选为近期复盘；实现符合字面合同，
  期望拒绝正确，分类为确定性 Router 的域语义局限，未据此调整规则。
- `CURRENT`：5C-5 已完成。小型维护者合成 holdout 不证明生产泛化，也不单独证明
  必须采用模型；下一检查点为 5C-6 Model Fallback Decision，5D 继续被阻止。

### 2026-08-07：5C-6 模型兜底采用决策

- `IMPLEMENTED`：ADR-0010 比较设备排除词、强 LoL 域信号、类型化入口/澄清、
  LLM 语义复核和 Embedding/分类器，并检查结构化输出、延迟、成本和故障边界。
- `CURRENT`：5C V1 暂缓 LLM Router fallback，保持冻结的确定性 Router 与
  Manifest 不变；单一小型合成失败不足以引入模型。
- `CONDITIONAL`：只有新鲜数据出现多个独立语义失败族，新 development/holdout、
  Provider 结构化输出、质量/成本/延迟/故障评测和 fail-closed 合同均通过后，才用
  新 ADR 重开模型方案。
- `CURRENT`：5C-1 至 5C-6 已分别完成；下一步只做 5C 退出复核，尚未进入 5D。

### 2026-08-07：5C Skill Router V1 退出复核

- `FIXED`：`RouterDecision` 原先允许 selected/ambiguous 夹带非候选 Skill 证据；
  现要求 evidence 身份与 candidate 身份完全一致，并由先失败后通过的合同测试保护。
- `FIXED`：holdout 的冻结点误标为尚未包含双 Skill 合同的 `cfd2084`；Git 审计确认
  实际冻结提交为 `4103d42`，且到首次结果提交前 Router、规范化和两个 Manifest
  零差异。只更正 provenance，不改案例、规则、标签或结果，也没有重跑 holdout。
- `DOCUMENTED`：旧 5C-4 单 Skill 文档增加双 Skill 演进说明；退出复核统一记录
  数据/控制流、层间边界、评测解释、已知限制、框架替换边界和面试安全表述。
- `IMPLEMENTED`：聚焦回归 `66 passed`，完整回归 `256 passed, 57 subtests passed`；
  5C-1 至 5C-6 和退出复核均完成，A08 Skill Router 状态改为已完成。
- `CURRENT`：阶段 5 仍进行中，唯一下一检查点为 5D。5D 只被设置为下一步，尚未
  开始实现；进入时先拆分 Context Builder、结构化输出、权限预算和不可信边界。

### 2026-08-07：5D 受限 Skill Agent Loop 入口设计

- `AUDITED`：现有 Harness 使用 eager retrieval + one-shot generation，AgentLoop
  支持 dynamic tool use；简单叠加会形成两套检索/证据路径。
- `REJECTED`：仅给旧 Harness 套 Skill 外壳，因为它没有接入 5A AgentLoop；也拒绝
  让 AgentLoop 接管评测/发布，因为会复制 Harness 并扩大模型控制面。
- `ACCEPTED`：ADR-0011 采用 AgentLoop 作为 evidence-aware `DraftPreparationStep`；
  它输出 CoachDraft + KnowledgeEvidence，现有 ReviewHarness 保持唯一质量和发布门禁。
- `CURRENT`：Context Builder 对内部策略、Skill 指令、事实、用户、RAG 和 Tool
  Observation 分层；权限只来自同名同版本 Manifest，不从文本推断。
- `CURRENT`：真实 Provider 准入位于 5D-6b。先稳定结构化输出和领域评测，再实测
  GLM 并至多比较一个候选，不提前锁定 DeepSeek、Qwen 或 Kimi。
- `CURRENT`：5D 拆为 5D-1 至 5D-7 与 exit review；唯一下一步是 5D-1 Skill Run
  Boundary Hardening，本设计批没有实现 5D 功能代码，不得进入 5D-2。
- `VERIFIED`：本批未改功能代码；完整回归 `256 passed, 57 subtests passed`，
  compileall、diff check 与治理预检通过。

### 2026-08-07：5D-1 Skill Run Boundary Hardening

- `IMPLEMENTED`：两个 Skill 对确定性报告、terminal report、run ID、evidence IDs
  与 warnings 使用一致的去空白、非空和去重合同。
- `IMPLEMENTED`：selected `RouterDecision` 锁定 Skill name/version；执行边界从
  Catalog 重新取得同名 Skill，版本漂移或缺失时 fail closed。
- `IMPLEMENTED`：`RunManifest`、`FileRunStore`、Skill 输出与执行请求共享跨平台
  安全 run ID，拒绝路径、盘符、Windows 保留名和超长值。
- `IMPLEMENTED`：输入绑定复用 Harness 实际 JSON/text 字节编码，记录 Summary 与
  确定性报告的 kind、schema version 和 SHA-256；`ValidatedSkillExecution` 保存与
  调用方可变 payload 脱钩的 typed input 快照。
- `BOUNDARY`：本检查点只承诺未来 Artifact 内容，没有创建 FileRunStore run、构造
  Context/`AgentRunRequest`、调用 Tool/Provider/AgentLoop 或接入 Harness 发布。
- `VERIFIED`：聚焦回归 `107 passed, 25 subtests passed`；完整回归
  `276 passed, 80 subtests passed`；compileall、diff check 与治理预检通过。
- `CURRENT`：5D-1 完成；唯一下一步为 5D-2 Context Builder V1，不得进入 5D-3。

### 2026-08-07：5D-2 Context Builder V1

- `IMPLEMENTED`：新增 provider-neutral `ContextSection`、`ContextBundle`、可注入
  `ContextSizer` 与 `ContextBuilderV1`；复用现有 system/user `ChatMessage`，没有创建
  第二套消息协议或提前编译 `AgentRunRequest`。
- `IMPLEMENTED`：内部 Policy 与已校验 SKILL.md 是 instructional/system；确定性
  事实、用户请求和知识 citation 是 data-only/user。恶意文本单测证明角色与标签
  不会被内容提升，但不把该结果夸大为模型级 Prompt Injection 已解决。
- `IMPLEMENTED`：近期复盘使用 allowlisted aggregate、样本边界、确定性报告和最多
  10 条可选 match 投影；单局复盘只含 target row，不含 `recent_summary`、其他 match
  ID 或同时引用其他已知对局的报告行。
- `IMPLEMENTED`：Manifest context ceiling 不可提高；required context 超限 fail
  closed，optional match/citation 按 priority 与稳定原顺序整段选择，并记录省略 ID。
- `BOUNDARY`：默认 sizer 是可重复的 tokenizer-free preflight，不等于真实 Provider
  Usage；动态 Tool Observation、权限/预算编译和每次 Provider 调用前的累积预算仍属于
  5D-3。
- `VERIFIED`：聚焦回归 `61 passed, 17 subtests passed`；完整回归
  `292 passed, 80 subtests passed`；compileall 与 diff check 通过。
- `CURRENT`：5D-2 完成；唯一下一步为 5D-3 Skill Run Compiler & Budget
  Enforcement，不得进入 5D-4。

### 2026-08-07：5D-3 Skill Run Compiler & Budget Enforcement

- `IMPLEMENTED`：新增薄 `AgentRunCompiler`，只从已验证 Manifest 与
  `ContextBundle` 编译现有 `AgentRunRequest`；run/Skill/version 漂移、Context ceiling
  提高、重新估算溢出和 Manifest 工具未注册均在 Loop 前 fail closed。
- `IMPLEMENTED`：`ContextBundle.messages` 必须是 sections 的规范渲染；默认 sizer
  计算 role/content、ToolCall id/name/arguments 与 Tool result metadata 的完整消息
  envelope，大参数不能再绕过确定性 preflight。
- `IMPLEMENTED`：AgentLoop 在每次 Provider 调用前检查累计 Context；初始越界时
  Provider 调用为 0，Tool Observation 导致越界时不会进行第二次 Provider 调用。
- `IMPLEMENTED`：Manifest timeout 被收紧为协作式总 deadline；Provider 获得递减
  剩余时间，ToolRuntime 使用运行剩余与工具 policy timeout 的较小值。
- `BOUNDARY`：该 deadline 不能硬中断任意阻塞同步函数；5D-3 没有调用真实 Provider、
  创建 draft preparer、转换 KnowledgeEvidence、组合 Harness 或发布报告。
- `VERIFIED`：聚焦回归 `85 passed, 17 subtests passed`；完整回归
  `308 passed, 80 subtests passed`；compileall 与 diff check 通过。
- `CURRENT`：5D-3 完成；唯一下一步为 5D-4 Evidence-Aware Agent Draft
  Preparation，不得进入 5D-5。

### 2026-08-08：5D-4 Evidence-Aware Agent Draft Preparation

- `IMPLEMENTED`：知识搜索 payload 到 `KnowledgeEvidence` 的映射已抽成新旧路径共享
  的 fail-closed 转换器；单/多检索、稳定 K1、source 去重、显式拒答、count 与重复
  chunk 归因冲突均有直接测试。
- `IMPLEMENTED`：新增 `SkillAgentDraftPreparer`，只从同一 AgentLoop Registry 编译
  并执行请求；仅接受 `completed/final_response` 与非空最终文本，返回尚未发布的
  `CoachDraft + KnowledgeEvidence + AgentRunResult`。
- `VERIFIED`：`recent-form-review` 与 `single-match-review` 均通过真实 Catalog、
  Router、ExecutionBoundary、ContextBuilder、Compiler、AgentLoop、ToolRuntime 与
  本地 `knowledge.search`；Provider 为确定性 Fake，模型虚构来源不会进入 Evidence。
- `BOUNDARY`：知识工具失败、坏 payload、非知识工具和预算/重复/超时停止均 fail
  closed；本检查点没有修改 ReviewHarness、构造 terminal Skill Output、调用真实
  Provider 或发布报告。
- `VERIFIED`：聚焦回归 `102 passed`；完整回归 `325 passed, 80 subtests passed`；
  compileall 与 diff check 通过。
- `CURRENT`：5D-4 完成；唯一下一步为 5D-5 Harness Composition & Typed Terminal
  Output，不得进入 5D-6a。

### 2026-08-08：5D-5 Harness Composition & Typed Terminal Output

- `IMPLEMENTED`：新增 provider-neutral `DraftPreparationStep`；旧 Retriever/Generator
  通过 `SequentialDraftPreparer` 适配，`ReviewHarness` 不再维护两套草稿入口或新增
  `run_prepared()` 控制流。
- `IMPLEMENTED`：新增 `SkillReviewExecutor`，校验 validated execution 与 Context
  identity，只从 Skill Manifest 映射发布阈值和 deterministic fallback，并把 5D-4
  Agent draft/evidence 交给现有 Evaluator、受限修订和终态状态机。
- `IMPLEMENTED`：新增 `SkillTerminalOutputBuilder`；最终报告、最终 attempt 分数和
  evidence source IDs 只从完整性校验通过的 Artifact 读取，两份输入 Artifact 必须与
  5D-1 commitment 的 run/kind/schema/SHA 一致，最后再由 Manifest 声明的 Output Model
  校验。
- `VERIFIED`：published、修订后 published、deterministic degraded、rejected、篡改、
  identity 漂移与错误 Output Model 均有直接测试；两个真实 Skill 通过 Fake Provider、
  真实本地 `knowledge.search` 和唯一 ReviewHarness 到 typed terminal output。
- `BOUNDARY`：该端到端证据不包含真实 Provider；尚未实现 Provider-neutral 结构化响应、
  Prompt E2E Evaluation、统一 Trace/Session、LangGraph、Agent SDK 或 Multi-Agent。
- `VERIFIED`：聚焦回归 `179 passed, 25 subtests passed`；完整回归
  `343 passed, 80 subtests passed`；旧 Harness CLI dry-run published，compileall、
  diff check 与治理预检通过。
- `PUBLIC-VERIFIED`：5D-5 功能提交为 `7662dea`；GitHub Actions run
  `31232630971` 对精确 SHA `7662dea335e28f76edb78a7c0ac3d07680412cc1`
  完成且结论为 `success`。
- `CURRENT`：5D-5 完成；唯一下一步为 5D-6a Structured Output Contract，不得进入
  5D-6b。

### 2026-08-08：5D-6a Structured Output Contract

- `IMPLEMENTED`：新增不可变、Provider-neutral `StructuredResponseContract`；结构化
  请求会使 Capability Negotiation 明确要求 `STRUCTURED_OUTPUT`，普通文本和 Tool
  Calling 请求保持原行为。
- `IMPLEMENTED`：新增严格 Pydantic Evaluation 模型，作为 Prompt Schema、transport
  Schema 和本地验证的共同来源；非法 JSON、fence、缺/多字段、嵌套类型错误、非法枚举
  与截断都会 fail closed。
- `IMPLEMENTED`：一次格式 repair 使用与首次调用相同的合同，修复结果必须重新严格
  验证；第二次失败返回安全错误。Harness 集成测试确认此时只发布确定性 fallback，
  不会发布 Agent 草稿。
- `AT-CHECKPOINT`：5D-6a 收尾时 Zhipu Adapter 仍只声明 text chat，结构化请求在 SDK
  I/O 前被拒绝；该历史 Fake Provider 合同测试不是 GLM 原生结构化输出或真实 Tool
  Calling 的证据。后续离线映射状态见下方 5D-6b 条目。
- `VERIFIED`：聚焦回归 `89 passed, 40 subtests passed`；完整回归
  `359 passed, 95 subtests passed`；compileall、diff check 与治理预检通过。
- `CURRENT`：5D-6a 完成；唯一下一步为 5D-6b Real Provider Capability Gate。该检查点
  先设计真实 GLM 准入实验和第二 Provider 决策门，不得直接进入 5D-7。

### 2026-08-12：5D-6b P1-P5 部分证据与受控诊断

- `REAL-EVIDENCE`：完整重跑使用 4/5 calls；P1 文本和 P2 简单 Evaluation JSON 通过。
  P3 在默认 Thinking 下以 1024 output tokens、`finish_reason=length` 和空 final content
  失败；P4 返回一个 ToolCall，但未通过旧的 fixture 精确参数相等；P5 依赖跳过。
- `DECISION`：不原样重试。官方文档确认 GLM-5.2 默认 Thinking，且交错式工具思考
  需要回传完整 reasoning；RiftCoach V1 不保存思维链，因此 P2-P5 受控复核显式关闭
  Thinking，并继续由本地 Pydantic/Tool JSON Schema 掌握严格验收。
- `BOUNDARY`：Schema 合法的 query 不再要求与 fixture 逐字相同；额外键、类型/范围、
  主题语义和 disabled 后仍出现 reasoning 均 fail closed。新的真实调用仍最多 5 次、
  零 SDK 自动重试，先提交探针并通过公开 CI。
- `REAL-EVIDENCE`：首个受控版本在公开 SHA `860c203` 上只使用 1/5 calls；P1 因仍采用
  默认 Thinking 而耗尽 128 output tokens，content empty、reasoning non-empty、finish
  `length`，P2-P5 依赖跳过。P1 随后也纳入 disabled-thinking，历史失败原样保留。
- `REAL-EVIDENCE`：最终版本在公开 SHA `6a15a00` 上使用 5/5 calls；P1 文本、P2 简单
  JSON、P3 嵌套 issue JSON、P4 Function Call、P5 Tool Observation final 全部通过，
  `admitted=true`，且所有 case 的 reasoning state 都为 missing。
- `PUBLIC-VERIFIED`：最终脱敏结果提交 `880ba1b` 的 GitHub Actions run `31615159223`
  对精确 SHA `880ba1b4e9fd74fcfbd8d568a3c16218bad48ad4` 全部通过。
- `IMPLEMENTED-OFFLINE`：生产 `ZhipuProvider` 已映射 disabled-thinking、四类消息、
  JSON mode、ToolSpec/ToolCall、AUTO/NONE 与请求级可逆工具别名；REQUIRED、别名冲突、
  未知别名、非严格 JSON、重复/并行 ToolCall 和不可回放 reasoning 均 fail closed。
- `VERIFIED-OFFLINE`：聚焦回归 `73 passed, 50 subtests passed`，完整回归
  `405 passed, 103 subtests passed`；这仍是 Fake SDK 映射证据，不是生产 Adapter 或
  领域 Skill 真实准入。
- `CURRENT`：5D-6b 仍进行中；唯一下一步为真实 Adapter 协议切片的离线设计/TDD，
  不进入领域 Skill、第二 Provider 或 5D-7。GLM 是首个基准 Adapter，不是最终厂商锁定。

### 2026-08-13：5D-6b Adapter Protocol Slice 离线控制器

- `DESIGNED`：拒绝继续扩展 raw 微探针和另写两轮 Function Calling 循环；采用一个
  `BudgetedProvider` 组合生产 Provider、现有 AgentLoop 与固定只读工具，保持单一
  Agent 控制流和 Adapter 边界。
- `IMPLEMENTED-OFFLINE`：A1 通过生产 Provider-neutral structured request 与 5D-6a
  严格 decoder；A2 运行 `AgentLoop(max_iterations=2, max_tool_calls=1)`，只允许一次
  `knowledge.search`，成功 observation 后要求精确终止标记。
- `BOUNDARY`：两案共享精确 3-call 预算，第 4 次会在底层 Provider 前被拒绝；A1 失败
  跳过 A2。CLI 必须显式确认真实调用、使用 `adapter_protocol` scope、精确预算 3，
  且 SDK 自动重试为 0。
- `SANITIZED`：公开结果只保存 case 状态、安全错误码、调用/Token/响应/工具计数、
  resolved model、finish reason 与 SHA-256；不保存 Prompt、模型原文、工具 observation、
  原始 request ID 或原始异常。
- `VERIFIED-OFFLINE`：协议/CLI/结果合同聚焦回归 `22 passed`；完整回归
  `415 passed, 103 subtests passed`。全量测试曾发现 package 重导出造成的循环 import，
  已通过只允许显式子模块导入 runner 修复。
- `CURRENT`：5D-6b 仍进行中；下一步先提交并公开验证该控制器，再执行一次精确
  3-call 真实 Adapter 协议切片。不进入领域 Skill、第二 Provider 或 5D-7。

## 当前不变的宏观路线

```text
0 Baseline
1 LoL deterministic domain core
2 Quality-gated Harness
3 Provider + Tool Runtime
4 RAG Evidence V1
5 Skills + constrained Agent execution
6 API + Session + Memory
7 Standard MCP + dynamic Meta
8 Advanced runtime + conditional Multi-Agent + productization
```

EchoMind、AGI-Saber 和 Sea/OpenResearch 继续作为选择性来源：EchoMind 主要提供
应用、会话、Memory 和工具可靠性思路；Saber 提供检索、Context、DAG、取消和
快照候选；Sea/OpenResearch 提供 Artifact、预算、租约、事件与恢复候选。任何
吸收都必须回到 RiftCoach 的真实问题、对照实验、成本和 ADR。
