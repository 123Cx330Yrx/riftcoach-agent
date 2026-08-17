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
- `AT-CHECKPOINT`：5D-6a 完成；当时唯一下一步为 5D-6b Real Provider Capability Gate。该检查点
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
- `AT-CHECKPOINT`：当时 5D-6b 仍进行中；唯一下一步为真实 Adapter 协议切片的离线设计/TDD，
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
- `AT-CHECKPOINT`：当时 5D-6b 仍进行中；下一步先提交并公开验证该控制器，再执行一次精确
  3-call 真实 Adapter 协议切片。不进入领域 Skill、第二 Provider 或 5D-7。

### 2026-08-13：5D-6b Adapter Protocol Slice 真实结果

- `PUBLIC-VERIFIED`：协议控制器提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51`
  已推送；GitHub Actions run `31625669630` 对该精确 SHA 全部通过，CI 不含真实模型调用。
- `REAL-EVIDENCE`：随后只执行一次显式 `adapter_protocol/3`，SDK 自动重试为 0；A1
  structured contract 使用 1 call，A2 现有 AgentLoop + 固定只读 `knowledge.search`
  使用 2 calls，总计 3/3，二者均 passed，`admitted=true`。
- `OBSERVED`：A1 为 427/59 tokens、2344 ms；A2 为 562/36 tokens、5360 ms，两个
  Provider response 的 finish sequence 为 `tool_calls -> stop`，工具调用/执行均为 1。
- `SANITIZED`：结果的 code SHA 指向上述公开 CI 成功提交；公开文件只包含安全状态、
  计数、model/finish metadata 与哈希，不含 Prompt、模型原文、observation、原始 request
  ID、异常或 Key。无可靠单价快照，成本保持 null。
- `BOUNDARY`：这次证据准入生产 Zhipu Adapter 的最小 structured/tool 协议切片，不
  准入 `recent-form-review`、ReviewHarness 报告质量、最终模型选择或 5D 整体。
- `AT-CHECKPOINT`：当时 5D-6b 仍进行中；唯一下一步是 Recent-form Domain Slice 的离线设计/TDD，
  先解决原定累计 7-call 上限与已用 3 calls 的核算，再决定真实领域执行。不进入第二
  Provider 或 5D-7。

### 2026-08-13：5D-6b Recent-form Domain Slice 离线控制器

- `DESIGNED`：领域准入与协议准入、Prompt 质量评测分层；本切片只验证同一生产
  Provider 能否进入真实 recent-form 控制流，不用单个样例选择模型或临场调整 Prompt。
- `BUDGET`：严格复读并哈希已准入的 `zhipu_adapter_slice.json`，确认历史调用精确为
  3、Provider/model 一致；AgentLoop 与 Harness 的 `llm.chat` 共用剩余
  `ExternalCallBudget(max_calls=4)`，累计仍为 7，第 5 个领域调用在底层 Provider 前拒绝。
- `IMPLEMENTED-OFFLINE`：匿名 fixture 经过真实 SkillCatalog、Deterministic Router、
  ExecutionBoundary、ContextBuilder、AgentLoop、本地 `knowledge.search`、唯一
  ReviewHarness 和 typed output；happy path 为 Agent 2 calls + Evaluation 1 call，
  第 4 call 只允许一次 Evaluation 格式 repair。
- `FAIL-CLOSED`：准入专用 SDK 自动重试为 0，Harness `llm.chat` 为单次尝试、无缓存、
  无 fallback；需要 revision 后再评测会耗尽预算并失败关闭，不能作为领域准入成功。
- `SANITIZED`：真实 CLI 要求显式确认与精确累计 `max_calls=7`，只允许批准结果目录并
  要求干净已提交的工作树、拒绝覆盖既有结果；公开 typed report 不保存 Prompt、模型
  正文、Tool Observation、原始 request ID、异常、临时 Artifact 或 API Key。
- `VERIFIED-OFFLINE`：聚焦回归 `23 passed`；相邻纵向回归
  `141 passed, 29 subtests passed`；全量回归 `430 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness SDK/敏感文件边界和 dry-run 全部通过。仓库中没有真实
  recent-form 结果文件，未调用 GLM。
- `AT-CHECKPOINT`：当时 5D-6b 仍进行中；唯一下一步是提交、推送并验证离线控制器精确 SHA 的
  公开 CI，通过后才按 RQ-027 执行一次剩余最多 4-call 的真实领域切片。不得进入第二
  Provider 或 5D-7。

### 2026-08-13：5D-6b Recent-form Domain Slice 公开控制器

- `PUBLIC-VERIFIED`：领域控制器提交
  `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 已推送；GitHub Actions run
  `31657764638` 对该精确 SHA 全部通过。
- `CI-SCOPE`：公开门禁包含全量 pytest、RAG development/independent holdout、
  compileall、Harness SDK boundary、tracked secret/run-data 和 Harness dry-run；CI 没有
  本地 `.env`，未调用真实 Provider。
- `AT-CHECKPOINT`：离线控制器公开可复现后，5D-6b 仍进行中；当时唯一下一步为按 RQ-027
  执行一次累计 7-call、领域剩余最多 4-call 的真实 GLM recent-form 切片并原样保存
  脱敏结果。本离线批次不得直接继续该调用，也不得进入第二 Provider 或 5D-7。

### 2026-08-13：5D-6b 真实领域准入与 ADR-0012

- `REAL-EVIDENCE`：在公开 CI 成功 SHA
  `f5e97ead20c5aa7d4798f308bd60e820842061bc` 上只执行一次真实 recent-form
  领域切片；领域调用为 1，累计为 4/7，没有重试或 Prompt 调整。
- `REJECTED-DOMAIN`：外部请求发生后没有统一 `ChatResponse` 进入 Agent 结果，
  response/tool/evidence 均为 0，未进入 Evaluation，没有质量分；领域
  `admitted=false`，安全错误为 `knowledge_round_trip_incomplete`。
- `FALLBACK-VERIFIED`：Harness 到达 `degraded` 并只输出确定性报告，真实证明外部
  Provider 失败不会发布未经评测的 Agent 草稿。
- `OBSERVABILITY-BOUNDARY`：脱敏证据无法区分 Adapter 规范化拒绝和其他统一响应
  形成前的 Provider 错误；草稿准备接缝没有向 runner 暴露失败的 `AgentRunResult`，
  该错误来源丢失进入 5D-7，而不是通过猜测原文或重跑补齐。
- `ACCEPTED`：ADR-0012 以部分采用收尾 5D-6b：准入 Zhipu 最小 structured/tool
  协议，拒绝 GLM-5.2 recent-form 领域能力，保留确定性 fallback，并在同任务评测
  合同冻结前暂缓第二 Provider。
- `CURRENT`：唯一下一步为 5D-7 Prompt/Context & Domain E2E Evaluation。先冻结
  案例、失败分类、可观测性和基线，再决定是否需要 Prompt 调整或第二 Provider；不得
  进入 5D exit review、5E、LangGraph、Agent SDK 或 Multi-Agent。
- `PUBLIC-VERIFIED`：真实失败结果与 ADR-0012 提交 `34ea5c3` 已推送；GitHub
  Actions run `31659371226` 对精确 SHA
  `34ea5c32e5c124207fcba7b0521a4e5a62af6845` 全部通过。

### 2026-08-13：5D-7 Batch A 分层评测合同与离线基线

- `ACCEPTED`：ADR-0013 在“单样例调 Prompt”“只看最终文本的 Judge”和“分层领域
  评测”之间选择第三种；Provider/Agent、Tool、Evidence、Evaluation、Terminal 与
  Resources 分层观察，失败使用安全白名单枚举，未知值不转换成 0。
- `IMPLEMENTED`：新增严格 Dataset、Candidate 与 Result Pydantic 合同，候选只允许
  保存调用/响应计数、Agent/Tool/Evidence/终态、安全错误码和可空资源指标；Prompt、
  模型正文、思维链、原始 request ID、异常和 Key 都不能进入候选 Schema。
- `LIFECYCLE`：development 可以用于评测器开发但必须记录污染；held-out 必须
  `calibration_excluded=true`、无开发污染，并在 CLI 显式确认规则冻结。Batch A 没有
  创建或运行 held-out。
- `OFFLINE-EVIDENCE`：10 个 development 观测包含成功控制、5D-6b 真实脱敏 Bad Case、
  缺工具、工具执行失败、缺证据、坏引用、注入失败、质量门禁失败和故意不安全发布；
  以及资源超限；任务结果与主失败分类均为 10/10，unsafe-publication 为 1/10，外部
  Provider 调用为 0。
- `LIMITATION`：10/10 是评测器对已知离线观测的分类回归，不是 Prompt、真实 Provider、
  领域报告质量、泛化能力或模型级注入防护成绩；故意不安全发布也不是生产 Harness
  的真实事故。
- `CURRENT`：5D-7 保持进行中。唯一下一步为 Batch B：冻结 Prompt/Context 评测身份
  和可重复实验入口；不调 Prompt、不运行真实 Provider、不接第二 Provider，不进入
  5D exit review 或 5E。
- `PUBLIC-VERIFIED`：Batch A 提交 `9f0d7d1` 已推送；GitHub Actions run
  `31661582544` 对精确 SHA `9f0d7d1177ac84c4d25c3397da85bf8e43859a6f` 全部通过。

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

### 2026-08-13：5D-7 Batch B Prompt/Context 双层身份与实验 admission

- `ACCEPTED`：ADR-0014 在“只靠人工版本”“只哈希最终消息”和“组件 + 案例双层
  语义身份”之间选择第三种；有效行为变化可被发现并定位，注释/import 等无关源码
  变化不自动污染实验身份。
- `COMPONENT-IDENTITY`：Skill Manifest/Instructions、Context Policy、
  `knowledge.search` 版本/Schema/策略、Evaluation Schema/事实投影以及评测、repair、
  revision prompt builders 分别形成规范 SHA-256。
- `CASE-IDENTITY`：真实 recent-form demo 经 Catalog、Router、ExecutionBoundary 与
  ContextBuilder 形成输入 Artifact、typed options、选中/省略 section、最终 system/user
  message 和 Context 预算摘要。
- `BOUND`：Domain E2E Dataset/Candidate/Result 升至 Schema 1.1，并强绑定冻结快照 ID/
  SHA；案例、期望标签和 Batch A 失败分类未变。
- `FAIL-CLOSED`：离线 preparation 会在 Provider 前重建当前快照；当前值、冻结文件或
  Dataset 声明任一漂移都不产生 admission。冻结 admission 为 `admitted=true` 且
  `external_provider_calls=0`。
- `SANITIZED`：公开快照/admission 只含标识、结构化元数据和摘要，不保存 Prompt、玩家
  事实、模型正文、Tool Observation、异常、request ID 或 Key；该身份层不是 5E Trace。
- `VERIFIED-LOCAL`：聚焦测试 `20 passed`，相邻纵向回归
  `87 passed, 4 subtests passed`，完整回归 `450 passed, 103 subtests passed`；两套 RAG、
  compileall、Harness SDK/tracked-data、dry-run、快照正文脱敏、治理和 diff check 通过；
  Domain E2E 1.1 基线/admission 可逐字节复现，外部调用为 0。
- `CURRENT`：5D-7 仍进行中。唯一下一步为 Batch C 入口设计与离线 TDD；先让可执行
  development 候选经过 admission，再验证工具、事实、引用与模型级注入，不直接运行
  真实 Provider、不创建/运行 held-out、不接第二 Provider、不进入 5D exit review 或 5E。
- `PUBLIC-VERIFIED`：Batch B 功能提交
  `e56b00091ef2ab299af692e902945b8342fbc99e` 已推送；GitHub Actions run
  `31690698734` 对该精确 SHA 全部通过，CI 未调用真实 Provider。

### 2026-08-13：5D-7 Batch C 离线可执行领域评测

- `ACCEPTED`：ADR-0015 在继续手填 Candidate、立即真实 Provider 多案例和 Scripted
  Provider + 真实本地控制流之间选择第三种，隔离外部随机性而不复制生产 Agent。
- `CONTRACT`：Domain E2E 兼容升级至 Schema 1.2，新增 `offline_executable`；零外部
  调用且每案例必须携带安全 provenance SHA-256，Dataset/Candidate schema 漂移失败关闭。
- `EXECUTED`：7 个 development 场景先通过 Batch B admission，再真实经过 Catalog/
  Router/Boundary、ContextBuilder、AgentLoop、ToolRuntime、本地混合 RAG、Evidence
  构造和唯一 ReviewHarness；仅 Provider 响应为确定性脚本。
- `COVERAGE`：覆盖 happy path、缺工具、错误 90% 胜率、未知 `[K999]`、用户注入、
  RAG 注入和 Evaluation 漏判注入；fact/citation/injection 从实际 draft、Evidence
  Artifact 和 canary probe 提取，不按 case ID 直接填写 observation。
- `BAD-CASE`：漏判场景的含 RAG canary 报告被 Harness 实际发布，随后由分层评测标记
  `injection_resistance_failed`、`terminal_status_mismatch` 和 `unsafe_publication`。
  task/failure classification 为 7/7，unsafe publication 为 1/7，后者必须原样保留。
- `SANITIZED`：可执行 CLI 与冻结 Candidate/Result 逐字节复现，外部 calls 为 0；公开
  JSON 不含 canary、错误事实、Prompt、报告、工具原文、request ID、异常或 Key。
- `VERIFIED-LOCAL`：聚焦/相邻回归 `25 passed`，完整回归
  `455 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/tracked-data、
  artifact 脱敏、治理、diff check 和 Harness dry-run 通过。
- `AT-CHECKPOINT`：5D-7 当时仍进行中。唯一下一步为 Batch D 入口设计，先裁决 injection
  Evaluation 合同、held-out、有限真实运行和第二 Provider 决策门；不直接调用真实
  Provider、不立即创建/运行 held-out、不接第二 Provider、不进入 5E。
- `PUBLIC-VERIFIED`：Batch C 功能提交
  `06cf769be54c8062aeddcd8c36283306e63bfc9a` 已推送；GitHub Actions run
  `31705232946` 对该精确 SHA 的全测试、两套 RAG、compileall、治理、Harness SDK/
  tracked-data 和 dry-run 门禁全部通过，CI 未调用真实 Provider。

### 2026-08-13：5D-7 Batch D 注入评测与真实 Provider 门设计

- `AUDITED`：`EvaluationResponseModel` 1.0.0 没有注入类别；当前
  `ChatEvaluationAdapter` 只把 fact pack 与报告送入 Prompt，Evaluator 没看到用户原话、
  实际 KnowledgeEvidence 或 Context 信任标签。只增加枚举无法提供判断证据。
- `REJECTED`：不在生产代码中扫描已知 canary/关键词，因为这会硬编码 development
  答案；也不原地修改 `coach_evaluation@1.0.0`，避免破坏 Batch A-C 历史身份。
- `ACCEPTED`：ADR-0016 决定保留 1.0.0，后续以 1.1.0 接收最小 fact/report、data-only
  用户请求与 bounded KnowledgeEvidence，并把 `prompt_injection` 作为不可修订的
  blocking issue；canary 继续只作为实验 oracle。
- `LIFECYCLE`：D1/D2 离线迁移与新 snapshot 冻结后才创建独立 held-out；创建不等于
  运行，首次结果不得用于反向调当前规则。
- `REAL-GATE`：真实首轮只含正常、用户注入、知识注入 3 场，每 Provider 每场最多
  4 calls、领域总计最多 12 calls、`max_revisions=0`、SDK retry 为 0；第二 Provider
  还需新 ADR 和最多 3-call Adapter 协议门。预算是上限，不是当前授权。
- `BOUNDARY`：本入口批只完成设计与 ADR，没有修改生产 Schema/Prompt/Harness、创建
  held-out、调用真实 Provider 或选择第二 Provider，也没有进入 5E。
- `CURRENT`：唯一下一步仍在 5D-7 Batch D，为 D1 离线 TDD：实现兼容的 Evaluation
  1.1 与 blocking policy，同时保护 1.0.0 和 Batch A-C 历史复现。

### 2026-08-14：5D-7 Batch D D1-D3 安全评测迁移与 held-out 创建

- `D1-IMPLEMENTED`：保留 `coach_evaluation@1.0.0` 历史合同，新增并接入
  `coach_evaluation@1.1.0`；安全 Prompt 接收 bounded、data-only 的用户请求与知识证据，
  `prompt_injection` 必须为 high severity。
- `D1-POLICY`：ReviewHarness 对类型化 blocking issue 使用 `security_policy_blocked`
  直接 deterministic fallback/rejection，不交给 Reviser，不在生产代码扫描已知 canary。
- `D2-VERIFIED`：7 个 secure offline executable development 场景通过真实本地
  Skill/Agent/Tool/RAG/Harness 控制流；task outcome accuracy `1.0`、failure
  classification accuracy `1.0`、unsafe publication rate `0.0`、external calls `0`。
  旧 1.0.0 与 Batch C 1/7 unsafe-publication Bad Case 保持可复现。
- `D3-CREATED`：在合同、secure snapshot 与规则冻结后创建 3 场独立 held-out，标记
  `calibration_excluded=true`，通过无污染与显式确认生命周期测试；本批不运行 held-out。
- `BOUNDARY`：D1-D3 不调用真实 Provider、不接入第二 Provider，不代表真实模型抗注入
  或领域质量已准入。
- `AT-CHECKPOINT`：当时唯一下一步改为 D4 候选 Provider 采用门设计；先用新 ADR 固定同任务比较、
  能力/错误归因、调用/成本预算和停止规则，之后才考虑一次有界真实比较。
- `PUBLIC-VERIFIED`：D1-D3 提交
  `e100e4d602891bb6cfb22f25101c53f4621408f8` 已推送；GitHub Actions run
  `31719575766` 对该精确 SHA 全部通过，CI 未调用真实 Provider 或运行 held-out。

### 2026-08-14：5D-7 Batch D D4 第二 Provider 候选采用门

- `AUDITED`：统一 `LLMProvider`、Chat 合同、能力协商和 Registry 已经厂商中立，但
  thinking、工具名、reasoning、finish reason、usage 和错误映射仍属于独立 Adapter；
  “OpenAI-compatible”不能证明只替换 base URL 即可安全复用。
- `OFFICIAL-VERIFIED`：DeepSeek 官方 V4 Flash/Pro 均支持 non-thinking、JSON 与 Tool
  Calls，并公开直接 API 价格；Qwen3.8 Max 已是正式混合思考模型，也支持结构化输出与
  Function Calling，不能再按旧资料称为 preview。Qwen 本轮因 reasoning/计费入口增加
  控制变量而暂缓，不是质量结论。
- `ACCEPTED`：ADR-0017 选择 DeepSeek 官方 `deepseek-v4-flash` 为唯一有界第二
  Provider 候选。DeepSeek V4 Pro 因首轮协议面相同但成本更高暂缓；不增加候选和通用
  OpenAI-compatible Adapter 方案也被拒绝。
- `GATES`：D5 必须先离线实现独立 Adapter、5D-6b 安全错误归因缺口、预算 ledger 和
  no-I/O dry-run；随后 exact-SHA 公开 CI 成功，才可能执行最多 3-call 协议门和同一
  3 场 held-out。DeepSeek 累计最多 15 calls，GLM 领域最多 12 calls，每案例 4000
  total tokens、每请求最多 1024 output tokens，金额停止线分别为 $0.05 和 ¥0.50。
- `STOP`：身份/快照漂移、预算控制失效、公开工件泄密或任一 unsafe publication 会
  停止整个实验；协议、usage、预算或案例期望失败会停止该 Provider，不重跑或调 Prompt。
- `BOUNDARY`：D4 只完成设计和采用决策，没有实现/注册 DeepSeek Adapter、读取密钥、
  调用真实 Provider、运行 held-out、选择生产默认模型或进入 5E。
- `VERIFIED-LOCAL`：聚焦回归 `68 passed, 15 subtests passed`，完整回归
  `460 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/敏感文件边界、
  dry-run、文档密钥模式扫描、governance 和 diff check 通过，外部调用为 0。
- `CURRENT`：唯一下一步为 5D-7 Batch D D5 的离线 TDD 准备；本轮仍不得自动调用真实
  Provider 或运行 held-out。
- `PUBLIC-VERIFIED`：D4 提交 `02720631aa34aa8556ea445bbd1837c8b562715c` 已推送；
  GitHub Actions run `31761121188` 对该精确 SHA 的完整 pytest、两套 RAG、compileall、
  governance、Harness SDK/敏感文件边界和 dry-run 全部通过，CI 未调用真实 Provider。

### 2026-08-14：D4 唯一候选从 V4 Flash 更正为 V4 Pro

- `TRIGGER`：用户追问新发布的 DeepSeek V4 Pro 后，复核发现原决定过度优化低成本协议
  探针，而 D5 的唯一候选还承担完整领域 held-out 准入。
- `OFFICIAL-VERIFIED`：DeepSeek V4 Pro 正式版于 2026-08-13 GA；官方生产 Agent 基准
  全部高于 V4 Flash，且两者共享本轮所需 non-thinking、JSON、Tool Calls 与 1M 上下文。
- `SUPERSEDED`：ADR-0017 保留为历史并标记被取代；ADR-0018 将唯一候选更正为
  `deepseek-v4-pro`。这仍是一个 DeepSeek Provider、一个模型候选，不是 Multi-Agent、
  自动模型路由或产品模型选择器。
- `BUDGET`：15/12 calls、每案例 4000 total tokens、每请求最多 1024 output tokens 与
  零自动重试不变；按官方 Pro 峰值价，DeepSeek 应用层金额停止线由 `$0.05` 调整为
  `$0.10`，16000 tokens 极端全按输出价约 `$0.06336`。
- `BOUNDARY`：协议门和领域门必须使用同一精确 Pro 模型；不同时测试 Flash，也不以
  Flash 协议证据替代 Pro。当时把 Flash 的后续评估写在 5F；该未来归属已由下方
  ADR-0019 条目修正为 5P 后、默认阶段 6 的横向 Provider 优化门。
- `NO-I/O`：本次更正只改 ADR、设计与持久状态，没有实现 Adapter、读取密钥、调用模型、
  运行 held-out 或进入 5E。唯一下一步仍为 D5 离线 TDD。
- `PUBLIC-VERIFIED`：候选更正提交 `5513928e29ffab4525b356b80845d9be807647bb`
  已推送；GitHub Actions run `31762059181` 对该精确 SHA 全部门禁通过，CI 未调用真实
  Provider 或运行 held-out。

### 2026-08-14：5D-7 Batch D D5 DeepSeek Provider 离线实现

- `IMPLEMENTED-OFFLINE`：新增独立 `DeepSeekProvider`，冻结 V4 Pro、non-thinking、
  non-streaming、JSON mode、工具别名、finish/usage 与脱敏错误语义；没有注册为产品
  默认 Provider，也没有把 Zhipu Adapter 改 base URL 后复用。
- `OBSERVABILITY`：安全 `AgentFailureObservation` 穿过 draft preparation 接缝；真实
  AgentLoop Provider failure 的测试证明 Harness 仍安全降级，同时上层保留状态、停止
  原因和白名单错误码，不暴露 Prompt、模型正文或原始异常。
- `RESOURCE-GATE`：候选实验组合式 ledger 固定 DeepSeek 3+12 calls、16000 observed
  tokens、每请求 1024 output 与 `$0.10` 停止线；GLM 领域为 12 calls/12000 tokens/
  `¥0.50`。调用在 I/O 前占用，usage 缺失和任何越界均 fail closed，unsafe publication
  触发全局停止。
- `NO-I/O`：preparation CLI 只校验干净 Git SHA、公开 CI SHA、冻结 held-out 与
  Prompt/Context 身份，不加载 `.env`、不读取 Key、不创建真实 client、不运行 held-out。
- `EVIDENCE`：完整回归 `505 passed, 103 subtests passed`；两套 RAG 门禁、compileall、
  Harness dry-run、SDK/tracked-data 边界、governance 与 diff check 均通过。Fake SDK
  证据只证明 Adapter/控制器，不证明真实模型能力，外部 Provider calls 为 0。
- `PUBLIC-VERIFIED`：D5 功能提交 `e68a8e4542ed72d31d5d46e569a11d9292048540`
  已推送；GitHub Actions run `31764109304` 对该精确 SHA 的全测试、两套 RAG、compileall、
  governance、安全边界与 Harness dry-run 全部通过。
- `NO-I/O-VERIFIED`：同一干净公开 SHA 的 preparation 通过，明确输出
  `external_provider_calls=0`、`held_out_executed=false`；没有读取 Key 或创建客户端。
- `CURRENT`：唯一下一步为最多 3 calls 的真实 DeepSeek V4 Pro Adapter 协议门；必须
  显式确认真实调用并使用已冻结 budget/stop controller，失败即停止，不直接运行 held-out。

### 2026-08-14：DeepSeek 模型分层移出 5F

- `TRIGGER`：用户确认当前保持 Pro 单候选、未来再考虑 Flash 默认/Pro 升级，并指出
  5F 原本已经固定为 Pi / Claude Agent SDK 采用实验。
- `FIXED`：ADR-0018 与 D4 设计曾把未来 Flash 成本/时延评估写入 5F。该落点会同时改变
  Agent Runtime 与模型策略，破坏实验归因；ADR-0019 修正未来归属，但不改变 ADR-0018
  的当前 Pro 选择、预算和准入门。
- `CURRENT`：5D-7 继续只让 `deepseek-v4-pro` 运行协议门与后续冻结 held-out；Flash
  不加入当前 Adapter allowlist、不产生真实调用，也不触发自动路由。
- `CONDITIONAL`：Flash/Pro 分层是 5P 后的横向 Provider 优化门，默认等待阶段 6 形成
  真实 API、Trace、成本、p50/p95 延迟或容量 Bad Case；届时比较 Pro-only、Flash-only
  与 Flash 默认/Pro 有界升级，并使用新鲜 development/held-out。
- `CURRENT`：5F 仍只用真实切片比较自建 AgentRuntime 与 Pi / Claude Agent SDK，决定
  采用、局部采用或拒绝；模型切换能力可以被观察，但 5F 不实现模型分层策略。
- `BOUNDARY`：本次只同步需求、设计、ADR 和持久状态，不修改 Provider 代码、不运行
  API/held-out、不进入 5E/5P/5F 或阶段 6。当前唯一下一步仍是最多 3-call 的真实 Pro
  Adapter 协议门。

### 2026-08-14：DeepSeek V4 Pro 真实 Adapter 协议准入

- `PUBLIC-VERIFIED`：real-gate execution seam 提交
  `076a5e3558cd68abb545cebdc2542c973b020768` 已推送；GitHub Actions run
  `31767405927` 对该精确 SHA 全部门禁通过，同 SHA no-I/O preflight 通过且为零调用。
- `EXECUTED-ONCE`：随后只执行一次真实 DeepSeek V4 Pro 协议门；A1 strict structured
  contract 使用 1 call，A2 Agent tool round trip 使用 2 calls，二者均 passed，
  总计 3/3 calls 并 `admitted=true`。
- `RESOURCES`：记录 1303 input、125 output、合计 1428 tokens，估算费用
  `$0.00221496`，累计 Provider latency 14844 ms；未触发 Provider/global stop，SDK
  retry 为 0。
- `IMMUTABLE-EVIDENCE`：组合结果通过类型化复读，文件 SHA-256 为
  `575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`；公开内容不含
  Key、Prompt、模型原文、工具原文或原始 request ID。
- `BOUNDARY`：只准入最小生产 Adapter structured/tool 协议；三场领域 held-out 仍未
  运行，不准入报告质量、真实抗注入、产品默认模型或 Flash/Pro 路由。
- `CURRENT`：5D-7 唯一下一步改为审计并设计冻结领域 held-out 执行接缝，先离线 TDD
  和 exact-SHA CI；本批不继续调用 Provider、不进入 5D exit review 或 5E。

### 2026-08-14：5D-7 DeepSeek 领域 held-out 执行接缝

- `DESIGNED`：新增初学者设计与 ADR-0020，拒绝复用带 development canary 的脚本 runner 和把全部
  控制塞入真实 API CLI；采用 no-I/O admission、案例执行 Protocol、既有分层 Evaluator
  与累计资源账本的薄协调器。
- `CONTROL-PLANE`：admission 在类型层不接收 Provider，先绑定当前代码/公开 CI、冻结
  Dataset/Snapshot、真实协议文件字节摘要和案例执行计划摘要；后续输出必须在 Provider
  构造前独占预留。
- `RESOURCE-GATES`：从真实协议已消耗的 3 calls/1428 tokens/费用继续累计；新增
  protocol/domain scope 与单案例 Token/call 边界，保持每例 4 calls/4000 tokens、领域
  12 calls/12000 tokens、累计 15 calls/16000 tokens/$0.10 和 1024 output/request。
- `STOP-AND-SANITIZE`：每例安全观测立即交给现有分层 Evaluator；Provider/案例 mismatch
  停止候选，unsafe publication 全局停止，剩余案例为 skipped。资源由 ledger 差值产生，
  公开记录不保存 Prompt、攻击/模型/RAG/工具正文、request ID、异常或 Key。
- `OFFLINE-EVIDENCE`：合成 Provider/Executor 覆盖协议账本继承、单例第 5 call pre-I/O
  拒绝、Token overrun、首错停止、unsafe 全局停止、计划/预算漂移、原始异常脱敏和输出
  不可覆盖；真实协议文件只复读未重跑，held-out executions 和新增 Provider calls 均为 0。
- `IMPLEMENTED`：接缝提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已通过
  GitHub Actions run `31785253957` 的 exact-SHA 公开 CI；该 CI 没有调用 Provider 或
  运行 held-out。
- `CURRENT`：进入单独真实领域门的装配批，冻结案例执行计划并实现生产 Executor/CLI，
  先离线 TDD 和新的 exact-SHA CI；成功前不得读取 Key、运行 held-out、进入 5D exit
  review 或 5E。

### 2026-08-14：5D-7 领域 held-out 生产装配

- `CORRECTED-BEFORE-EXECUTION`：ADR-0021 在没有真实候选输出、held-out 从未运行的
  窗口内把 Dataset 从 1.0.0 升为 1.1.0；三个案例都要求抗注入后安全发布，旧版本留在
  Git 历史，不伪造执行结果。
- `IMPLEMENTED-LOCALLY`：独立输入计划绑定原始 bytes、fixture、Skill 和 case order；
  production Executor 只接收 case ID，真实组合现有 Skill/Agent/Tool/RAG/Harness，
  并固定 `max_revisions=0`。
- `KEY-LAST`：真实门 CLI 在 no-I/O preflight、Dataset/plan/protocol/fixture admission 和
  输出独占预留完成后才加载环境与构造 Provider；精确协议结果 SHA 仍为
  `575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
- `OFFLINE-EVIDENCE`：Fake Provider 完成正常/两种注入、安全失败、零修订与完整 CLI
  路径；它只证明生产装配，不是 DeepSeek 领域质量或真实 held-out 结果。
- `CURRENT`：唯一下一步是提交、推送并验证本生产装配的 exact-SHA GitHub Actions；
  成功后真实三案例仍需下一次显式确认，不进入 5D exit review 或 5E。

### 2026-08-14：DeepSeek V4 Pro 真实领域 held-out 不准入

- `EXECUTED-ONCE`：用户显式确认后，在公开干净 SHA `205397f0bd87a53291b8a2c62487a8b6d966fdb1`
  上通过 no-I/O preflight，并只执行一次 Dataset 1.1.0 真实领域门。
- `BAD-CASE`：首个正常案例的第一次 Agent 请求消耗 1 call；模型响应触发生产 Adapter
  `unsupported_parallel_tool_calls` 边界，没有统一 `ChatResponse`、工具执行、Evidence
  或 Evaluation。Harness 安全降级，unsafe publication 为 0。
- `STOPPED`：按首错停止，用户注入与知识注入案例均 skipped；最终 `admitted=false`，
  不能声称已测试真实注入抵抗或报告质量。
- `RESOURCES`：领域增量记录 1 call、0 observed tokens、`$0.00`；0 tokens 表示响应在
  规范化前被拒绝、统一 usage 无法结算，不代表厂商一定没有计费。
- `IMMUTABLE-EVIDENCE`：脱敏结果 SHA-256 为
  `fbd1251af98daa9e767de56a35100025807ce96026d6b3b3497e33dd30ad989e`；当前 held-out
  已消费，禁止删除、覆盖或重跑追绿。
- `CURRENT`：先归档结果并完成公开 CI；之后仅在 development 中评估并行 ToolCall 的
  拒绝、顺序执行与并发执行方案，冻结新合同和新鲜评测前不得再次调用领域 held-out。
- `PUBLIC-VERIFIED`：归档提交 `26b668d0ce594e648a692cd2caf831c86125fede` 已通过
  GitHub Actions run `31810164628` 的 exact-SHA 公开 CI；唯一下一步转为零调用 Bad Case
  设计与 development 复现计划，不改变真实拒绝结论。

### 2026-08-14：多 ToolCall 批次采用顺序消费

- `OFFICIAL-EVIDENCE`：DeepSeek 官方 Chat Completion 合同说明 `tool_choice=auto` 可调用
  一个或多个工具，响应为 `tool_calls[]`，且当前请求合同没有关闭多调用批次的参数。
- `DECISION`：ADR-0022 选择由 Adapter 严格解码多个 ToolCall，AgentLoop 在任何工具执行
  前完成整批预算/白名单/重复校验，再按模型返回顺序执行；不启用真正并发或并发 capability。
- `NO-I/O`：本批只新增设计、ADR 与 implementation plan，没有读取 Key、调用 Provider、
  修改 Prompt 或重跑已消费的 Dataset 1.1.0。
- `CURRENT`：唯一下一步是离线 development TDD；离线通过不改变旧真实结果的
  `admitted=false`，真实诊断和新鲜 held-out 需后续独立采用门。

### 2026-08-14：多 ToolCall 顺序消费 development TDD 完成

- `RED-GREEN`：DeepSeek Adapter 测试先在旧实现上复现真实
  `unsupported_parallel_tool_calls`，再在保留严格字段校验的前提下支持多 ToolCall 双向
  编解码；`parallel_tool_calls` capability 仍为 `false`，没有新增未在官方合同中的请求字段。
- `ATOMIC-PREFLIGHT`：AgentLoop 测试证明整批调用先检查剩余预算、白名单和重复签名，
  任一失败时所有工具均不执行；全批通过后按返回顺序执行，并保留 call ID、Usage、迭代和
  总 deadline 语义。
- `VERTICAL-DEVELOPMENT`：新的 development case 由 Fake DeepSeek SDK 驱动，但真实组合
  Skill/Context、AgentLoop、ToolRuntime、本地 hybrid RAG、Evidence、Secure Evaluation 1.1
  与 ReviewHarness；最终发布通过，外部 Provider calls 为 0，未使用旧 held-out ID 或 marker。
- `EVIDENCE`：聚焦 `53 passed`，全量 `551 passed, 103 subtests passed`；两套 RAG、
  compileall、Harness dry-run、SDK/secret/run-data、governance 和 diff check 通过。
  该批只证明本地执行链兼容性，不改写真实 Pro 领域拒绝结论。
- `CURRENT`：提交并推送后等待 exact-SHA GitHub Actions；通过后仍留在 5D-7，需另行
  设计/批准新鲜真实领域采用门，不能重跑 Dataset 1.1.0、直接进入 5D exit review 或 5E。

### 2026-08-14：多 ToolCall 顺序消费公开验证完成

- `PUBLIC-VERIFIED`：提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 的 GitHub Actions
  run `31817798170` 对精确 SHA 成功；完整 pytest、两套 RAG、compileall、Harness
  boundary、tracked-data 和 dry-run 均通过，外部 Provider calls 为 0。
- `SCOPE`：该提交只证明 Adapter/AgentLoop 多 ToolCall 顺序消费与本地纵向执行链，
  不改变旧 Dataset 1.1.0 的真实 `admitted=false`，也不准入 DeepSeek 报告质量。
- `CURRENT`：仍在 5D-7；下一步是零调用设计新的 Dataset/输入身份/预算/采用门，之后
  如需真实验证必须再获得单独确认；不得重跑旧考卷、实现真正并发或进入 5D exit review/5E。

### 2026-08-15：GLM-5.3 同厂商模型迁移边界

- `OFFICIAL-EVIDENCE`：智谱官方 GLM-5.3 页面已发布；Coding Plan 已开放，普通模型 API
  将逐步上线；GLM-5.3 始终启用 thinking，不能继续使用当前 Zhipu Adapter 的
  `thinking.type=disabled`，首轮应按官方要求使用 `enabled` 与 `reasoning_effort=low`。
- `DECISION`：新增 ADR-0023，将 GLM-5.3 作为隔离的同厂商模型迁移候选；不把 GLM-5.2
  历史结果改名，不立即改默认模型，不把 DeepSeek 当前 5D-7 工作混入本候选，也不把
  DeepSeek 的多 ToolCall 修复自动复制给 Zhipu。
- `SEQUENCE`：当前唯一下一步仍为 5D-7 零调用新鲜领域采用门设计；其设计/离线 TDD/
  exact-SHA CI 完成后，才按 G53-0 可用性审计、G53-1 Zhipu profile、G53-2 CI、G53-3
  最多 3-call 协议门、G53-4 新鲜领域门推进。
- `BOUNDARY`：本次只更新需求、设计、ADR、状态和计划文件；没有读取 Key、真实调用、
  Provider 代码改动、DeepSeek 结果改动或阶段推进。

### 2026-08-15：DeepSeek 新鲜领域采用门设计

- `PROBLEM`：旧 Dataset 1.1.0 已在首个真实失败后被开发过程看见；多 ToolCall 修复可以
  用旧题做 regression，但复制/改名或重跑不能提供新鲜领域准入证据。
- `DECISION`：ADR-0024 采用版本化复用现有 no-I/O admission、薄协调器、预算 Provider、
  production Executor、分层 Evaluator 与唯一 Harness；拒绝整套重写和旧题改名。
- `LIFECYCLE`：先只用合成 development 数据实现兼容 input-plan、逐案例
  Prompt/Context commitment、历史证据链和实验记录合同；exact-SHA CI 冻结后，才单独
  创建新的匿名 fixture、三案例 held-out 和输入计划，再次 CI 后才可能请求真实调用。
- `EVIDENCE`：新门必须绑定旧协议 bytes SHA、旧拒绝结果 bytes SHA、多 ToolCall 修复
  commit/CI、当前 code/public-CI SHA 和新 Dataset/fixture/plan/Context SHA；旧证据不可
  覆盖或重跑。
- `BUDGET`：历史 3 次协议 + 1 次失败领域调用单独保留；未来新鲜范围每例 4、领域 12
  calls，4000/12000 tokens、1024 output/request、`$0.10`、零重试/零修订和首错停止。
  上限不是当前授权。
- `CURRENT`：仍在 5D-7；唯一下一步为 Fresh-Gate 1 离线 TDD，不创建正式新 held-out、
  不读取 Key、不调用 Provider、不修改 Prompt/Evaluation/Harness，也不进入 5E。
- `PUBLIC-VERIFIED`：设计提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已通过
  GitHub Actions run `31859717836` 的 exact-SHA 全部门禁；该 CI 外部 Provider calls
  为 0，不代表 Fresh-Gate 1 合同代码、新 held-out 或真实领域准入已完成。

### 2026-08-15：DeepSeek Fresh-Gate 1 本地离线合同完成

- `BACKWARD-COMPATIBLE`：input plan 与 Prompt/Context snapshot 均增加 V1.1 能力，
  但旧 V1.0 文件和快照仍按原字段、原摘要与原字节复现；没有覆盖历史资产。
- `CASE-IDENTITY`：三个合成 development case 各自通过真实 Router、ExecutionBoundary
  与 ContextBuilder；V1.1 plan 按固定 case order 绑定每个 Context 摘要，公开合同不含
  用户、fixture、注入、Prompt 或模型正文。
- `HISTORY`：新历史链严格复读旧协议 SHA `575e8f...086e1`、旧拒绝结果 SHA
  `fbd125...989e` 和多 ToolCall 修复 `037a47f` / Actions `31817798170`；历史调用为
  `3 + 1 = 4`，旧协议 1428 tokens/`$0.00221496` 保持已知，旧失败调用的 Token/费用
  保持 unknown。
- `NO-I/O`：`FreshDomainDevelopmentAdmission` 仅接受 development Dataset，prepare
  函数不接收 Provider/Key，输出固定 `provider_construction_authorized=false`、
  `external_provider_calls=0`、`held_out_executed=false`。
- `VERIFIED-LOCAL`：聚焦 33、相邻 51、完整 `568 passed, 103 subtests passed`；两套
  RAG、compileall、Harness SDK/secret/run-data boundary 与 dry-run 均通过。外围计划
  命令的三个名称/参数错误已按真实 CI workflow 更正并重跑，不冒充首次命令成功。
- `CURRENT`：Fresh-Gate 1 目前只有本地证据。唯一下一步为提交、推送和 exact-SHA
  GitHub Actions；公开 CI 成功前不创建正式新 held-out、不读取 Key、不调用 Provider、
  不进入 Fresh-Gate 3、5D exit review 或 5E。

### 2026-08-15：DeepSeek Fresh-Gate 1 公开冻结完成

- `PUBLIC-VERIFIED`：实现提交 `adba965a7f7fb4293020502b4440e9880633e571` 已通过
  GitHub Actions run `31860874440` 的 exact-SHA 全部门禁。
- `SCOPE`：公开 CI 证明 V1.0 兼容、V1.1 input-plan/三案例 Context、历史证据链和
  development-only no-I/O admission 可复现；它没有创建/运行新 held-out，也没有评价
  DeepSeek 报告质量、在线稳定性或注入抵抗。
- `CURRENT`：唯一下一步为 Fresh-Gate 3，只创建全新匿名 fixture、正式三案例 held-out、
  V1.1 input plan 与实际逐案例 Context snapshot，并再次公开冻结；真实运行仍需之后的
  单独确认，不进入 5D exit review/5E。

### 2026-08-15：Fresh-Gate 3 新考卷资产本地冻结

- `DESIGNED`：拒绝旧题改 ID 和重写控制面，采用既有 V1.1 plan/Prompt-Context 合同；
  Dataset 保存 oracle、Input Plan 保存实际输入、Snapshot 保存 body-free 摘要。
- `RED-TO-GREEN`：先以 5 个缺文件红灯证明正式资产不存在，再创建匿名 3 局 fixture/
  确定性报告、三案例 held-out、V1.1 input plan 和 `recent-form-prompt-context-v1-2`；
  聚焦回归最终为 `39 passed`。
- `FRESHNESS`：新旧 fixture bytes、case ID、run ID、用户措辞、知识注入正文和 marker
  均不复用；新 Dataset 是 `held_out`、`calibration_excluded=true`，且没有污染记录。
- `IDENTITY`：三个案例真实经过 Catalog/Router/ExecutionBoundary/ContextBuilderV1，
  Snapshot 可精确重建且不保存用户/报告/fixture/注入正文；plan 按案例顺序绑定 Context
  摘要，Dataset 再绑定 Snapshot ID/SHA。
- `VERIFIED-LOCAL`：完整回归 `574 passed, 103 subtests passed`；两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
- `NO-I/O`：Provider calls 和 held-out executions 均为 0，正式结果文件不存在；当前只欠
  commit/push/exact-SHA CI，公开成功前不得进入 Fresh-Gate 4 或读取 Key。

### 2026-08-15：Fresh-Gate 3 exact-SHA 公开冻结完成

- `PUBLIC-VERIFIED`：资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8`
  已通过 GitHub Actions run `31861960565` 的 exact-SHA 全部门禁。
- `SCOPE`：公开 CI 证明新匿名 fixture、三案例 held-out、V1.1 input plan 和三个实际
  Context 摘要可重建；CI 没有 Key、Provider call、held-out execution 或真实结果。
- `CURRENT`：唯一下一步为 Fresh-Gate 4 no-I/O 入口批，先把新资产绑定到既有 admission/
  production CLI 并公开验证；真实运行仍需之后的单独确认，不进入 5D exit review/5E。

### 2026-08-15：Fresh-Gate 4 运行入口本地完成

- `DESIGNED`：拒绝原地替换旧常量和复制第二套 V2 协调器，采用 Fresh evidence/result
  envelope 包裹现有 domain admission/result，继续复用预算 Provider、production Executor、
  Evaluator 和唯一 Harness。
- `READMISSION`：新 no-I/O admission 同时绑定历史协议/拒绝 bytes、ADR-0022 修复 CI、
  Fresh-Gate 3 asset commit/CI、当前 code/public-CI、新 Dataset/plan/fixture 与三个 Context
  commitment；旧协议 Context 与新领域 Context 的预期差异被显式分层，而不是放宽其他证据。
- `KEY-LAST`：active CLI 使用 V2 profile 并增加 `--prepare-only`；真实模式顺序固定为 output
  conflict → no-I/O admission → output reserve → env/Key → Provider → bounded execution。
- `OFFLINE-EVIDENCE`：Fake Provider 正常路径用 9 次合成调用走通三案例生产链；受控鉴权
  失败路径只调用 1 次并跳过后两例；输出脱敏且不可覆盖。它们不是外部 Provider 或真实
  held-out 执行。
- `VERIFIED-LOCAL`：相邻 `93 passed`，完整 `580 passed, 103 subtests passed`；两套 RAG、
  compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
- `CURRENT`：唯一下一步为提交/推送和 exact-SHA GitHub Actions，随后在同一干净 SHA 上
  执行一次 `--prepare-only`；两步均为零调用，真实 12-call 运行仍需单独明确确认。

### 2026-08-15：Fresh-Gate 4 入口公开冻结完成

- `PUBLIC-VERIFIED`：实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过
  GitHub Actions run `31863341338` 的 exact-SHA 全部门禁。
- `PREPARE-ONLY`：随后在同一干净 SHA 执行真实 no-I/O preflight，输出
  `no_io_admitted=true`、external calls 0、held-out false；正式结果文件不存在。
- `CURRENT`：唯一下一步为真实运行确认门。必须再次展示并确认 Pro、12 calls、12000
  observed tokens、每例 4/4000、1024 output/request、`$0.10`、零重试/零修订和首错停止；
  未确认不得读取 Key，prepare-only 不等于领域准入。

### 2026-08-15：V2 真实门单次执行与预算可达性 Bad Case

- `AUTHORIZED`：用户明确确认运行真实 V2 三案例；执行前再次核对 HEAD/origin
  `741e84140f816fb4b06b2812a8d07d3f32eaf4d0`、Actions `31863519248` success、干净
  工作树、治理通过与结果不存在。
- `OBSERVED`：首例第一次调用形成规范化响应，Usage 为 3241 input + 199 output；下一
  调用因 `3440 + 1024 > 4000` 在 I/O 前以 `token_budget_exhausted` 停止。实际新鲜
  消耗为 1 call/3440 tokens/`$0.00506616`/12125 ms。
- `SAFE-TERMINAL`：Agent `failed/provider_error`，Harness
  `degraded/draft_preparation_failed`，unsafe publication false；后两例按首错停止 skipped。
- `DECISION`：V2 `admitted=false` 且不覆盖、不重跑；该结果证明预算控制与 fallback，
  但没有完成事实、引用、注入或 Evaluation，因此不把它写成模型报告质量失败。
- `EVIDENCE`：结果 SHA-256
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`；结果模型、固定
  指标、首错停止与无敏感正文已进入回归测试。
- `NEXT`：继续留在 5D-7，先零调用分析真实 Context 下的多轮 Token 可达性并补现实
  Usage fixture，再决定关闭候选或以新 ADR/新输入身份建立 V3 门；不立即调用任何模型。
- `PUBLIC-VERIFIED`：结果归档提交
  `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 已通过 GitHub Actions run
  `31864370988` 的 exact-SHA 全部门禁；CI Provider calls 为 0。

### 2026-08-15：ADR-0025 与 V2 预算可达性离线裁决

- `EXACT`：V2 首例 3440 observed tokens 加下一请求 1024 output 预留，精确最低门槛
  为 4464；相对 4000 单例上限短缺 464，因此完整必经路径当前必然不可达。
- `PROJECTED`：真实本地生产路径形成 3 个 body-free request envelope，稳定长度单位为
  6666/7774/6266；以首轮真实 input 校准后的 input 投影为 3241/3780/3047。该投影
  不是官方 tokenizer，未来两轮 output 仍 unknown。
- `DECISION`：不重跑 V2，也不把结果写成模型质量失败；允许继续设计 V3 development
  资源校准，但在新预算、新输入/结果身份和公开 CI 冻结前不授权 Provider I/O。
- `NO-I/O`：裁决器不接受 Provider、Key 或网络客户端；严格结果 JSON 可离线逐字段重建，
  本批外部调用为 0。
- `CURRENT`：先完成本批完整门禁、提交、推送和 exact-SHA CI，再进入 V3 资源合同设计；
  仍不得进入 5D exit review/5E。

### 2026-08-15：预算裁决 exact-SHA 公开验证完成

- `PUBLIC-VERIFIED`：提交 `78400b9310e512668c81ca41cd65623a92a27226` 已通过
  GitHub Actions run `31865285994` 的全部门禁。
- `BOUNDARY`：公开 CI Provider calls 为 0；该证据关闭 V2 资源裁决，不授权 V3 I/O。
- `CURRENT`：唯一下一步为 V3 development 资源校准设计，先冻结校准数据、Usage 观测、
  预算推导与安全余量，再决定是否值得创建全新真实门。

### 2026-08-15：ADR-0026 冻结 V3 development 资源校准设计

- `AUDITED`：生产正常路径为两次 Agent + 一次 Evaluation；结构化 Evaluation 非法时
  最多增加一次同合同 repair，报告内容修订仍为 0，因此资源合同必须容纳 3-call 正常
  路径和可选第 4 call。
- `OFFLINE-EVIDENCE`：公开 development 输入经真实 production Executor 与本地受控
  Provider 形成四阶段请求；body-free 本地长度为 5956/7064/5749/2510。该证据不是
  Provider tokenizer 或模型质量证据，外部调用为 0。
- `DECISION`：拒绝直接抬高 V2、只跑一次行为依赖的 development E2E 或立即关闭候选；
  采用 baseline/ceiling 两个公开 development profile，经生产组装冻结四阶段请求，再
  独立 replay 收集真实 Usage。
- `RESOURCE-POLICY`：未来校准最多 8 calls、每请求校准 output 64、observed tokens
  64000、金额 `$0.10`、零重试和首错停止；V3 预算按逐阶段最大 input 的 25% 工程余量、
  四次 1024 output ceiling 和固定向上舍入推导。25% 不是统计置信保证。
- `STOP`：推导成本含既有协议成本后超过 `$0.10`、现有 30 秒 Agent deadline 不可达、
  校准不完整或未来请求超过 ceiling envelope 时，不创建 V3 held-out，不自动加预算。
- `CURRENT`：唯一下一步仍在 5D-7，只实现校准 development 资产/合同、四阶段 Fake
  Provider 路径、预算推导和 no-I/O admission，并完成完整门禁与 exact-SHA public CI；
  真实 development replay 仍需后续单独确认。

### 2026-08-15：V3 资源校准设计 exact-SHA 公开冻结

- `PUBLIC-VERIFIED`：设计提交
  `351c0e64adf9d2ace42c557d40fac81a44ab539e` 已通过 GitHub Actions run
  `31866084382` 的治理、完整 pytest、两套 RAG、compileall、Harness SDK/tracked-data
  boundary 与 dry-run。
- `BOUNDARY`：CI 不含 Key 或 Provider I/O；公开设计不等于校准实现、真实 Usage、V3
  预算或领域准入。
- `CURRENT`：唯一下一步为 V3 development 资源校准离线 TDD 与公开冻结；真实最多
  8-call Usage replay 仍需其后单独明确确认。

### 2026-08-15：V3 资源校准离线实现完成，等待公开冻结

- `IMPLEMENTED-LOCAL`：两个全新 development profile 与独立 fixture 已冻结，加载器会
  在 Provider 前拒绝 V2 case/run/body/marker/digest 复用；ceiling 使用 10 条 match
  投影和现有 Skill 最大 3 次 ToolCall。
- `IMPLEMENTED-LOCAL`：现有 production Executor 确定性形成 baseline/ceiling 各四阶段
  请求；公开合同只保存 digest、角色、消息数、本地长度和 tool/response-contract 身份，
  完整 Prompt/知识/草稿/非法 Evaluation 只存在于内存。
- `IMPLEMENTED-LOCAL`：离线 Fake replay 显式拒绝未标记 Provider，复用现有资源账本固定
  8 calls、64 output/request、64000 observed tokens、`$0.10`、首错停止，并补上 Provider
  实际 output Usage 违反单请求上限时的 fail-closed 结算门。
- `IMPLEMENTED-LOCAL`：纯整数/Decimal 推导器实现逐阶段 max input ×1.25 与固定向上
  舍入；7/8 不产生预算，成本超过 `$0.10` 或两次 Agent 带余量超过 30 秒均拒绝 V3。
- `BOUNDARY`：新增 11 tests 只证明离线控制与请求形状，不是 DeepSeek Usage 或质量证据；
  完整本地回归为 `598 passed, 103 subtests passed`，两套 RAG 和全部本地门禁通过；
  Provider/Key/外部调用/V3 held-out 均为 0。
- `PUBLIC-VERIFIED`：实现提交 `2d676966915a7967b946880040b59c022283e683` 已通过
  GitHub Actions run `31867655627` 的 exact-SHA CI；公开运行没有 Key/Provider I/O。
- `CURRENT`：唯一下一步仍在 5D-7，只展示冻结上限并等待用户对真实 8-call DeepSeek
  V4 Pro development Usage replay 的单独明确确认；确认前不读取 Key或创建 V3 held-out。

### 2026-08-15：真实 8-call development Usage replay 已确认，入口本地 TDD 完成

- `USER-CONFIRMED`：用户明确确认 RQ-033 的 DeepSeek V4 Pro 2 profiles × 4 stages
  真实校准；64 output/request、64000 observed tokens、`$0.10`、零重试和首错停止不变。
- `IMPLEMENTED-LOCAL`：新增真实 run admission、真实/Fake 分型结果、共享预算 replay、
  Key-last CLI、prepare-only、不可变结果和完整 8/8 后的预算记录；不修改 Prompt、RAG、
  Harness、V2 或默认模型。
- `VERIFIED-LOCAL`：聚焦 19、相邻 74、完整 `606 passed, 103 subtests passed`、两套
  RAG、compileall、Harness/security、dry-run、governance 与 diff check 已通过；当前
  Key/Provider/外部调用仍为 0。
- `CURRENT`：唯一下一步仍为 5D-7，先完成其余门禁并让真实入口通过新的 exact-SHA
  public CI；随后在同一干净 SHA 上 prepare-only，再只执行一次已确认的真实 replay。

### 2026-08-15：真实 development Usage replay 首错停止

- `PUBLIC-VERIFIED-ENTRY`：`6aa8c43` / Actions `31868747216` 已通过；同 SHA
  prepare-only 为 external calls 0，正式结果路径仍不存在。
- `REAL-RESULT`：正式 replay 第 1 个请求未形成规范化 `ChatResponse`，以
  `provider_response_invalid` 停止；1 external call、0 normalized responses，后 7 calls
  未发送，结果 SHA 为 `ba33e75a...e7088b`。
- `UNKNOWN`：账本没有取得 Token/latency/cost；序列化零值不能解释为厂商实际零计费。
  保守裁决把 billable Usage/费用标为 null，详细 Provider code unavailable，模型质量
  unknown。
- `STOP`：8/8 不完整，V3 budget 不可推导；budget 文件和 V3 held-out 不存在；结果不可
  覆盖或补跑。
- `CURRENT`：唯一下一步仍为 5D-7，只完成结果/裁决回归、持久化和 exact-SHA 公共归档；
  之后进入零调用的资源校准失败采用决策，不进入 5E。

### 2026-08-15：真实 calibration 不完整证据完成本地验证

- `VERIFIED-LOCAL`：结果、裁决、CLI 与全局结果合同聚焦 34/34；完整回归
  `611 passed, 103 subtests passed`，两套 RAG、compileall、Harness/security、dry-run、
  governance 与 diff check 全部通过。
- `BOUNDARY`：本批只解释既有不可变结果，外部调用为 0；账本零 Usage 不转写为实际
  零计费，billable Usage/费用保持 unknown，budget/held-out/rerun 继续禁止。
- `CURRENT`：唯一下一步仍为 5D-7，只提交、推送并完成该归档的 exact-SHA 公共 CI；
  公共冻结后才进入零调用采用决策。

### 2026-08-15：真实 calibration 不完整证据 exact-SHA 公开冻结

- `PUBLIC-VERIFIED`：归档提交 `421a24393cafdc79a02de4091f569cfb9aa5b721` 已通过
  GitHub Actions run `31869409106` 的治理、完整 pytest、两套 RAG、compileall、Harness
  SDK/tracked-data boundary 与 dry-run。
- `BOUNDARY`：公开 CI 无 Key/Provider I/O；该结果证明安全失败记录可复现，不证明 Usage
  校准或模型质量通过，也不授权补跑。
- `CURRENT`：唯一下一步仍在 5D-7，只做零调用的资源校准失败采用决策；不进入 5E。

### 2026-08-15：关闭当前 DeepSeek V3，采用安全错误 provenance 前置条件

- `DECISION`：ADR-0027 比较继续诊断、无限搁置与关闭当前 V3，接受关闭；不生成
  budget/held-out，不补跑旧结果，不作模型质量负面推断。
- `PRESERVED`：DeepSeek Adapter 与 3/3 最小 structured/tool 协议证据保留；领域、产品
  默认模型、自动路由和 Flash/Pro 分层仍未准入。
- `ADOPTED-REQUIREMENT`：后续真实 Provider 门必须先离线保留稳定高层 failure code 与
  allowlisted 可空细分错误码，且不得落盘原始响应、reasoning、异常或 request ID。
- `NO-IO`：本决策 Key/Provider/external calls 为 0，不实现 5E Trace。
- `VERIFIED`：51 项聚焦、完整 611 tests/103 subtests、两套 RAG 与全部本地门禁通过；
  决策提交 `ea91e9697c820c0850db488a93263fc169719515` 已由 Actions run
  `31872476103` 完成 exact-SHA 公共验证。
- `THEN-CURRENT`：当时下一步仍在 5D-7，按 ADR-0023 进入 G53-0 GLM-5.3 普通 API 与合同
  可用性审计；不调用模型。

### 2026-08-15：GLM-5.3 deferred，先补 Provider 错误 provenance

- `ROUTE`：普通 GLM-5.3 API 尚未正式可用，G53-0 标记 deferred；DeepSeek Pro 当前尝试
  关闭，不立即改测 Flash；GLM-5.2 作为开发基线继续。
- `IMPLEMENTED-OFFLINE`：ADR-0027 的安全错误 provenance 已在 Provider stop snapshot、
  resource calibration result/adjudication 中加入 allowlist 传递；未知错误归 null，旧
  V3 结果字节不变。
- `VERIFIED`：实现提交 `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a` 已由 Actions run
  `31874240935` 完成 exact-SHA 公共验证；616 tests/103 subtests、两套 RAG 和安全门禁
  通过，CI 无 Key/Provider I/O。
- `THEN-CURRENT`：本切片闭环后曾计划等待 GLM-5.3 普通 API 上线或新的明确 Pro/Flash 对照需求，
  不读取 Key、不调用 Provider。
### 2026-08-15：5D-7 以“评测门完成、领域 Provider 未准入”收尾

- `USER-CONFIRMED`：用户确认开始 5D-7 review，不让尚未上线的 GLM-5.3 普通 API 阻塞
  项目，也不因此自动切换 Flash 或补跑 DeepSeek。
- `REVIEW`：原始 5D-7 设计的退出对象是分层评测、Prompt/Context 身份、held-out
  生命周期、注入阻断、资源/错误合同和采用决策能力，不要求某个 Provider 必须通过。
- `DECISION`：ADR-0028 接受 5D-7 完成；当前 GLM/DeepSeek 领域质量仍未准入并保持
  unknown。G53 deferred 和未来 Flash/Pro 分层继续受既有重开门约束。
- `NO-IO`：本审查没有读取 Key、构造 Provider、调用模型、修改 Prompt 或默认模型。
- `VERIFIED-FOCUSED`：相关 Domain E2E、Prompt/Context、Coach Evaluation、Provider
  Domain/Adoption/Calibration 回归为 `130 passed, 4 subtests passed`。
- `VERIFIED-LOCAL`：完整回归 `616 passed, 103 subtests passed`，两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、治理和差异检查通过。
- `PRE-PUBLIC`：唯一下一检查点改为 `5D-exit-review`；完整本地门禁和 exact-SHA 公共 CI
  完成前，不得表述为公开收尾，也不得进入 5E。
- `PUBLIC-VERIFIED`：审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已通过
  Actions run `31876536179`；公共 CI 无 Key/Provider I/O。5D-7 正式闭环，下一检查点
  保持 `5D-exit-review`。

### 2026-08-15：5D 退出审查通过，转入 5E 入口设计

- `REVIEW`：逐项核对 5D 入口设计十项功能要求、非功能要求、两个真实 Skill 的组合
  控制链、Provider 负面实验、限制和 5E 前置项；未发现必须留在 5D 修复的结构性缺口。
- `VERIFIED-FOCUSED`：核心执行跨层回归为 `173 passed, 34 subtests passed`；Provider/
  实验控制跨层回归为 `176 passed, 22 subtests passed`。
- `BOUNDARY`：当前无领域 Provider 准入、真实注入未执行、性能/Usage unknown、G53
  deferred 和 Flash 未测试均继续保留；5D 完成不代表生产模型质量或阶段 5 完成。
- `DECISION`：5D 状态改为已完成；阶段 5 保持进行中；唯一下一检查点改为
  `5E AgentRuntime V1` 入口设计，先统一 run/stream/event/trace/usage 语义。
- `NO-IO`：本审查没有读取 Key、构造 Provider、调用模型、修改 Prompt 或默认模型，
  也没有提前采用 LangGraph、Pi 或 Claude Agent SDK。
- `PRE-PUBLIC`：本地退出裁决仍需完整门禁、提交推送和 exact-SHA 公共 CI；完成前不能
  表述为公开验证完成。
- `PUBLIC-VERIFIED`：退出审查提交 `2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493`
  已通过 GitHub Actions run `31877076222`；公共 CI 无 Key/Provider I/O。5D 正式闭环，
  下一检查点保持 5E 入口设计。

### 2026-08-15：5E AgentRuntime V1 入口设计

- `AUDIT`：现有 run_id、Agent stop、ToolResult、Harness transition/Artifact 和 Provider
  Usage 可复用，但分散在多个合同；外层只包 `SkillReviewExecutor` 无法产生实时事件，
  已发送却未规范化的 Provider 调用也不能用默认零表示 Usage。
- `ALTERNATIVES`：比较外层事后回放、薄 Runtime + observer、事件溯源/DAG/第三方框架
  三种方案；后两类重型能力没有当前 Bad Case，外层回放又不满足真实 stream。
- `DECISION`：ADR-0029 接受薄 Runtime；复用 5D 控制链和唯一 Harness，底层发安全
  Signal，中央 Recorder 生成有序 Event、完整性明确的 Usage 和原子最终 Trace。
- `BOUNDARY`：V1 stream 是进程内状态事件，不是 Token chunk；durable replay、cancel、
  resume、DAG、Multi-Agent 和跨进程恢复仍属于 5P/6/8；LangGraph/Pi/Claude Agent SDK
  仍只在 5F 依据 Bad Case 比较。
- `NO-IO`：入口批没有修改产品代码、读取 Key、构造 Provider、调用模型、切换默认模型
  或运行 held-out。
- `VERIFIED-LOCAL`：完整回归 `616 passed, 103 subtests passed`，两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、治理和 diff check 全部通过。
- `CURRENT`：5E 内部固定为 5E-1 至 5E-4；唯一下一步为 `5E-1 Runtime Contract、
  Usage 与 Trace Store` 的纯本地 TDD，不接 observer 或完整 `run/stream()`。
- `PUBLIC-VERIFIED`：入口设计提交
  `c91c2d75f85e1315e65e9768894982556053a7b0` 已通过 GitHub Actions run
  `31878052835`；公共 CI 无 Key/Provider I/O。5E-entry-design 正式闭环，下一检查点保持
  5E-1。

### 2026-08-15：5E-1 Runtime Contract、Usage 与 Trace Store 本地实现

- `IMPLEMENTED`：新增低依赖强类型 Signal、严格 request/result/event/usage/trace 合同、
  中央 Recorder 和不可覆盖的原子 `runtime_trace.json` Store；没有修改 AgentLoop、
  ToolRuntime、ReviewHarness 或 Provider。
- `INVARIANTS`：sequence/UTC/elapsed 由 Recorder 统一生成；Provider/Tool 调用必须按连续
  ordinal start 后关闭；唯一 terminal 后不得追加；Trace 复读会独立重验调用生命周期、
  Runtime/publication 双状态和 Usage 一致性。
- `USAGE`：无 Provider 调用、全部响应、部分响应和无响应分别为 not_applicable、complete、
  partial、unknown；partial/unknown 不伪造 Token 总数或成本，版本化 Decimal 定价只对
  可完整计算的 Usage 生效。
- `STORE`：最终 Trace 采用安全 run ID、同目录临时文件、flush/fsync、原子 replace、
  首写不可覆盖与 SHA-256 回读完整性；它不是 durable event log 或 crash recovery。
- `VERIFIED-LOCAL`：Runtime 聚焦 `39 passed`，Skill/Agent/Tool/Harness 相邻回归
  `166 passed, 55 subtests passed`，完整回归 `655 passed, 103 subtests passed`；两套
  RAG 1.0、compileall、Harness SDK/tracked-data boundary、dry-run 与治理均通过。
- `NO-IO`：未读取 Key、构造或调用 Provider、运行 held-out、修改 Prompt/模型或引入新依赖。
- `CURRENT`：唯一下一步仍是 5E-1，只做提交、推送与 exact-SHA 公共 CI；成功前不得
  进入 5E-2 observable run。
- `PUBLIC-VERIFIED`：实现提交 `d891184e1bf82068188d2fb5715769bdaa3da022` 已通过
  GitHub Actions run `31942483874` 的 exact-SHA 全部门禁；CI 无 Key 或 Provider I/O。
  5E-1 正式完成，唯一下一步切换为 5E-2 的入口审计/设计，不能把合同存在当成 run 已实现。

### 2026-08-16：5E-2 Observable run 入口审计与合同深化设计

- `AUDIT`：确认 AgentLoop 之外的 Evaluation、repair、Revision 均会通过内部
  `llm.chat` 调用同一 Provider；只观察 AgentLoop 会漏记调用、Token 和成本。
- `ALTERNATIVES`：比较组件分别估算 Provider、共享 observed Provider、全局 ToolRuntime
  observer；采用共享 Provider + 定点 Agent/Harness observer，拒绝漏记和业务 Tool 重复计数。
- `CONTRACT-GAPS`：确认真实零基 Evaluation attempt、冒号 section ID、可空 finish reason、
  Agent terminal、Harness failure、Zhipu missing Usage 和 Harness 事件顺序均需显式修正。
- `TERMINAL`：发现 emit completed 后再写 Trace 会在 Store 失败时产生双终态悖论；
  ADR-0030 采用 prepare/prospective store/commit，两阶段提交成功 terminal。
- `SCHEMA`：新写 Event/Trace 使用 1.1，读端保留合法 1.0，Runtime 产品版本仍为 V1；当前
  没有已持久化 Runtime Trace 需要迁移。
- `NO-IO`：本设计没有修改产品代码、读取 Key、构造/调用 Provider、运行 held-out、调整
  Prompt/模型或引入依赖。
- `VERIFIED-LOCAL`：聚焦 `122 passed, 37 subtests passed`，完整回归
  `655 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/tracked-data、
  dry-run、治理和 diff check 通过。
- `CURRENT`：5E-2 仍进行中；唯一下一动作是 Task A 的失败测试与最小实现，不进入 5E-3。
- `PUBLIC-VERIFIED`：设计提交 `3c6f26a4802821548be8d61085552f5b9a790468` 已通过
  GitHub Actions run `31944389807` 的 exact-SHA 全部门禁；CI 无 Key/Provider I/O。
  5E-2 仍未完成，下一步保持 Task A。

### 2026-08-16：5E-2 Task A 合同与 observation port 本地实现

- `IMPLEMENTED-LOCAL`：Event/Trace/Reference 默认写入 Schema 1.1，同时显式读取合法
  Schema 1.0；版本相关严格规则位于 Event 边界，不会因嵌套 Signal 提前校验而误拒旧数据。
- `IMPLEMENTED-LOCAL`：新增默认关闭的 observation port、Agent terminal、真实零基
  Evaluation attempt、冒号 section ID、有限且可空 finish reason、Tool failure code、
  Harness failure stage 与 Recorder/Trace 共用的 Harness lifecycle reducer。
- `IMPLEMENTED-LOCAL`：Recorder 永久保留 terminal slot，并实现 prepare → prospective
  Trace → commit/abort；Trace Store 失败后不会先公开 completed，已知 Harness publication
  也不能在 Runtime failure 中丢成 null。
- `USAGE`：成功 `ChatResponse` 必须显式携带 Usage；Zhipu missing/invalid Usage 安全失败为
  allowlisted `provider_usage_unavailable`，不再伪造完整零 Token。
- `VERIFIED-LOCAL`：聚焦 `131 passed, 44 subtests passed`，相邻
  `149 passed, 38 subtests passed`，完整 `691 passed, 110 subtests passed`；两套 RAG、
  compileall、安全边界、Harness dry-run、governance 和 diff check 均通过。
- `BOUNDARY`：本批没有接入 `ObservedLLMProvider`、AgentLoop/Harness observer 或实现统一
  `run()`；没有读取 Key、调用 Provider、运行 held-out、改 Prompt/模型或进入 5E-3。
- `PUBLIC-VERIFIED`：实现提交 `2e78c9606fe93b56657d4bb13c8efe0f1eed98fe` 已通过
  GitHub Actions run `31947625293` 的 exact-SHA 全部门禁；CI 无 Key/Provider I/O。
- `CURRENT`：Task A 已闭环；唯一下一步为用户确认后的 Task B run-scoped Observed
  Provider 与 AgentLoop 观察，不自动进入 Task C/D 或 5E-3。

### 2026-08-16：5E-2 Task B Provider 与 AgentLoop 观察本地实现

- `TDD`：Observed Provider 首个测试以缺模块红灯开始；AgentLoop 首批 14 个案例又以缺
  keyword-only observer 红灯开始；ToolRuntime 对 observation failure 的两个实现后红灯
  真实暴露 retry/fallback 误分类，均在最小修正后转绿。
- `IMPLEMENTED-LOCAL`：新增 run-scoped `ObservedLLMProvider`，记录连续 Provider ordinal、
  四类 phase、Usage、有限 finish reason、稳定 failure 与 allowlisted detail；capability 或
  非法 phase 在 delegate I/O 前停止。
- `IMPLEMENTED-LOCAL`：AgentLoop 只观察整批 preflight 后的业务 Tool 安全 envelope 和
  每个返回结果的唯一 terminal；started/completed/terminal observer failure 均 fail-fast，
  `observer=None` 与旧结果及 Provider 请求逐字段一致。
- `SAFETY`：Provider 错误允许列表下沉为 Runtime/Evaluation 共用低依赖投影；ToolRuntime
  在 retry、breaker、fallback 之前穿透 `RuntimeObservationError`，不保存 Prompt、response、
  arguments、Tool data、call/request ID、异常文本或 upstream detail。
- `VERIFIED-LOCAL`：聚焦 `81 passed`，完整 `721 passed, 110 subtests passed`；两套 RAG、
  compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
- `BOUNDARY`：本批 Provider/Key/held-out I/O 为 0；Harness observer、Artifact 投影、统一
  `run()` 与 `stream()` 未实现。唯一下一步仍是 Task B 的提交/推送与 exact-SHA 公共 CI，
  成功前不进入 Task C。

### 2026-08-16：5E-2 Task B exact-SHA 公共验证完成

- `PUBLIC-VERIFIED`：实现与持久状态提交 `28bd910525a7522be16bd69b6e945846839a4cd8` 已
  推送到 `origin/main`；GitHub Actions run `31952026988` 对该精确 SHA 的治理、721 tests/
  110 subtests、两套 RAG、compileall、Harness SDK boundary、tracked secret/run-data boundary
  与 dry-run 全部成功。
- `CURRENT`：Task B 正式闭环，Provider/Key/held-out I/O 仍为 0；唯一下一步切换为
  `5E-2 Task C` 的 Harness/Executor 持久化后 transition/evaluation/publication/Artifact
  observer TDD，不进入统一 `run()`/stream 或 5F。

### 2026-08-17：5E-2 Task C 公共闭环与 Task D 本地实现

- `PUBLIC-VERIFIED`：Task C 提交 `8b69c9b` 已由 GitHub Actions run `31957712118` 对
  exact SHA 完成全部公共门禁；Harness/Executor 持久化后观察与安全 Artifact 投影正式闭环。
- `IMPLEMENTED-LOCAL`：Task D 新增统一 `AgentRuntimeV1.run()` 与单一 `_execute()`；
  RuntimeExecutionFactory 为 Agent 与 Harness 创建同一个 run-scoped observed Provider，
  同时保持业务 Tool 与内部 `llm.chat` 计数边界。
- `CONTRACT`：`RuntimeRunRequest` 只接受 selected Router 决策；Boundary 继续发现版本/输入/
  Artifact 漂移；Runtime policy 的 `max_revisions` 真实传入 Harness。
- `RESOURCE`：event budget 绑定实际 `llm.chat` 三次 retry、每轮 Evaluation + 一次 repair、
  Revision 和全部 lifecycle Signal；当前 V1 一次修订的最坏上界为 61，副作用前不足即拒绝。
- `TERMINAL`：Trace 写失败不提交 `run_completed`，只提交内存
  `run_failed(trace_persistence_failed)`；observer/Recorder 故障安全映射为
  `observation_failed`，若 terminal Manifest 已存在则保留 publication truth。
- `VERIFIED-LOCAL`：新增 18 项 Task D 测试；完整回归 `747 passed, 110 subtests passed`，
  两套 RAG、compileall、Harness SDK/tracked-data boundary、dry-run、治理与 diff check 通过。
- `NO-IO`：本批没有读取 Key、调用真实 Provider、运行 held-out、修改 Prompt/模型、引入
  LangGraph/Agent SDK 或实现 stream。
- `CURRENT`：5E-2 仍进行中；唯一下一动作是 Task D 实现提交、推送与 exact-SHA 公共 CI，
  成功前不得进入 5E-3。

### 2026-08-17：5E-2 Task D exact-SHA 公共闭环，进入 5E-3

- `PUBLIC-VERIFIED`：Task D 提交 `d49508ef46876da6653ddcbe63a3584bdcbba711` 已推送到
  `origin/main`；GitHub Actions run `31959646589` 的完整 pytest、两套 RAG、compileall、
  Harness SDK/tracked-data、dry-run 与治理全部成功。
- `CLOSED`：5E-2 统一同步 `AgentRuntimeV1.run()` 正式完成；本地完整回归为
  `747 passed, 110 subtests passed`，新增 18 项纵向测试，当前没有真实 Provider/Key/held-out
  I/O。Task D 的 selected-only、共享 Provider、最坏 event budget、失败映射、Artifact SHA
  与两阶段 terminal 证据已进入公开仓库。
- `CURRENT`：根据 RQ-037，唯一下一检查点切换为 `5E-3 Live stream() & Parity` 入口审计/设计；
  只研究进程内实时事件与 run/stream 终态一致性，不自动实现 SSE、Token streaming、取消/恢复、
  API、Memory、真实 Provider、LangGraph 或 Agent SDK。

### 2026-08-17：5E-3 入口审计与进程内 Worker/Queue 设计冻结

- `AUDIT`：确认当前 `_execute()` 是唯一同步控制核心，Recorder 是可信实时事件事实源；
  事件尚无 subscriber/queue，对外只能在结束后读取最终 Trace。
- `DECISION`：接受 ADR-0031，采用进程内 worker + 有界 `queue.Queue` 作为 V1 stream
  交付层；`run()`/`stream()` 共用 `_execute(request, event_sink)`，普通事件在 Recorder
  追加后交付，terminal 在 Trace 原子写入并 commit 后交付，最后给出同一 `RuntimeRunResult`。
- `BOUNDARY`：队列背压采用满时阻塞；订阅关闭不取消任务，后续 stream-only item 可以停止
  投递；不引入外部消息队列、durable log、SSE、Token streaming、cancel/resume 或第三方 SDK。
- `VERIFIED-LOCAL`：stream item、worker/queue、实时顺序、run/stream parity、背压、订阅关闭、
  预期失败和 Trace 终态测试通过；聚焦 15、完整 `762 passed, 110 subtests passed`，compileall、
  RAG、治理和 diff 门禁通过。
- `CURRENT`：5E-3 仍进行中；下一动作是提交/推送实现并完成 exact-SHA 公共 CI，成功后才切换
  到 5E-4，不进入 5P/5F，不读取 Key 或调用真实 Provider。

### 2026-08-17：5E-3 exact-SHA 公共闭环，进入 5E-4

- `PUBLIC-VERIFIED`：提交 `80b76a1` 的 GitHub Actions run `31960987333` 完成完整 pytest、
  两套 RAG、compileall、治理、SDK/tracked-data boundary 与 Harness dry-run；本地 stream
  聚焦 15 项，完整回归 `762 passed, 110 subtests passed`。
- `CLOSED`：5E-3 `Live stream() & Parity` 正式完成。`run()`/`stream()` 共用 `_execute()`，
  进程内 worker/有界 queue、terminal commit 后交付、背压、关闭隔离和 parity 均有代码/测试/
  公开证据；没有 Provider/Key/held-out I/O。
- `CURRENT`：按 RQ-038，canonical 下一检查点切换为 `5E-4 Runtime Evaluation & Exit Review`
  入口审计；不进入 5P/5F，不读取 Key，不调用真实 Provider。

### 2026-08-17：5E-4 本地退出审查

- `MATRIX`：建立 5E-1 至 5E-3 的 Contract/Functional/Failure/Stream/Resource/Security/
  Delivery exit matrix，逐项绑定源码、测试、public CI、限制和退出影响。
- `VERIFIED-LOCAL`：Runtime 聚焦 `128 passed`，完整 `762 passed, 110 subtests passed`，
  compileall、两套 RAG、治理和 diff 门禁通过；没有当前 V1 必须补的结构性代码缺口。
- `DECISION`：本地决定 `close-with-deferred-boundaries`；真实模型领域质量、API/SSE、durable
  log、cancel/resume、Memory/MCP/Multi-Agent/SDK 与生产 SLO 保持 deferred/unknown。
- `CURRENT`：5E-4 仍进行中；下一动作只做退出审查提交、推送和 exact-SHA 公共 CI，成功后
  才关闭 5E 并进入 `5P-entry-design`。

### 2026-08-17：5E-4 exact-SHA 公共闭环与 RQ-039 暂停

- `PUBLIC-VERIFIED`：退出审查提交 `3d3656195a66adfd4595cffa145c978d24c33628` 已由
  GitHub Actions run `31962252231` 完成 exact-SHA 公共验证，全部公开门禁成功。
- `CLOSED`：5E-4 与整个 5E AgentRuntime V1 按 `close-with-deferred-boundaries` 正式完成；
  这不准入真实 Provider 领域质量，也不声称 API/SSE、持久恢复或生产 SLO 已完成。
- `CURRENT-PAUSED`：canonical 交接到 `5P-entry-design`，但 RQ-039 覆盖 RQ-038 的自动继续；
  当前没有开始 5P 设计、代码或 Provider I/O，等待用户再次明确“继续”。

### 2026-08-17：RQ-040 恢复 5P-entry-design 并冻结内部顺序

- `RESUMED`：用户再次明确“继续下一步”，RQ-040 满足并解除 RQ-039 的暂停条件；本轮只授权
  `5P-entry-design`，不授权直接实现或进入 5F。
- `AUDIT`：产品输入只有 Riot ID/少量选项，Runtime 输入却要求 selected Skill、Summary、
  确定性报告、Artifact binding 和 policy；当前还没有生产 composition root、Runtime policy
  compiler、app-level report renderer 或 API 查询投影。
- `PROMPT-GAP`：5D 退出证据明确保留 `5P Prompt Program V1`；实际 Prompt 由 Skill、Context、
  knowledge tool、Evaluation 1.1 与 Revision 共同组成，但 Runtime prompt profile 仍硬编码。
- `ALTERNATIVES`：拒绝 handler 串 CLI 和原样暴露 RuntimeRunRequest；接受 ADR-0032/0033 的
  版本化 Prompt Program + 薄 FastAPI/Application Service + 现有 AgentRuntime/Harness。
- `SCOPE`：V1 只设计 recent POST、run/report GET、health；status 因同步重复不单列，follow-up、
  单局、SQL、Session/Memory、SSE、鉴权、前端、MCP/SDK/Multi-Agent 均留在既定后续阶段。
- `SEQUENCE`：5P 固定为 5P-1 typed product/compiler、5P-2 Prompt Program/composition、
  5P-3 domain/application service、5P-4 receipt/query、5P-5 FastAPI、5P-6 exit review。
- `NO-I/O`：entry design 没有安装依赖、实现产品代码、读取 Key、调用 Riot/Provider 或运行
  held-out；唯一下一动作是完成文档/治理验证、提交与 exact-SHA 公共 CI。

### 2026-08-17：5P-entry-design exact-SHA 公共闭环

- `PUBLIC-VERIFIED`：设计提交 `49841ec44832875e65b17770557415113e67b1db` 的 GitHub
  Actions run `31985199623` completed/success；完整 pytest、两套 RAG、compileall、治理、
  SDK/tracked-data boundary 与 Harness dry-run 全部通过，CI 无 Key/Provider I/O。
- `CLOSED`：5P entry design 正式完成；ADR-0032/0033、5P-1 至 5P-6 顺序、端点/NFR/错误/
  测试边界均公开冻结，但没有 Prompt Program/FastAPI 产品代码或真实模型质量证据。
- `CURRENT`：canonical 切换到 `5P-1-product-contract-compiler` 准备状态；按 RQ-040 等待用户
  再次明确继续，不自动实现 5P-1 或进入 5P-2/5F。

### 2026-08-17：5P-1 Product Contract Compiler 本地实现

- `IMPLEMENTED-LOCAL`：新增 strict/frozen/extra-forbid recent 产品 DTO；客户端只控制 Riot ID、
  count、queue 与 focus，不能提交 run ID、Skill、Provider、Prompt、policy、路径或 digest。
- `TRUSTED-COMPILATION`：typed recent 入口从当前 Catalog 绑定
  `recent-form-review@0.2.0`，只生成 `entrypoint:reviews.recent` 机器证据，不调用自然语言 Router；
  服务器生成 run ID，并复用 Harness 规范字节编码形成 Summary/report Artifact binding。
- `POLICY`：Skill Manifest 映射 iterations/tool calls/timeout/context/quality/fallback，服务器固定
  Runtime policy version、event budget 与 V1 revision 上限；动态 Manifest 快照测试证明不是碰巧
  硬编码当前数值。
- `FAIL-CLOSED`：Catalog 缺失/输入合同漂移在 compiler 拒绝；payload/digest 或编译后 Skill version
  漂移继续由既有 `SkillExecutionBoundary` 拒绝，没有建立第二套执行安全边界。
- `VERIFIED-LOCAL`：产品聚焦 `32 passed`，相邻 `63 passed`，跨层 `213 passed`，完整回归
  `796 passed, 110 subtests passed`；两套 RAG、compileall、Harness SDK/tracked-data boundary、
  dry-run 与治理门禁通过。
- `NO-IO`：本批 Key/Riot/Provider/held-out I/O 为 0；Prompt Program、Application Service、
  receipt/query 和 FastAPI 未实现。当前仍需提交、推送与 exact-SHA 公共 CI，成功前不关闭 5P-1。

### 2026-08-17：5P-1 exact-SHA 公共闭环与 5P-2 交接

- `PUBLIC-VERIFIED`：提交 `57bd36adcd289b7cc51c1c430e04398daf0683f3` 的 Actions run
  `31987501935` 通过完整 pytest、两套 RAG、compileall、治理、SDK/tracked-data boundary 与
  Harness dry-run；CI 无 Key/Provider/held-out I/O。
- `CLOSED`：5P-1 Product Request & Typed Skill/Runtime Compiler 正式完成；这只证明产品输入到
  Runtime 请求的安全编译合同，不证明 Riot 数据链路、Prompt Program、FastAPI 或真实模型质量。
- `CURRENT`：canonical 唯一下一检查点切换为 `5P-2-prompt-program-runtime-composition`；按
  RQ-041 等待用户再次明确继续，不自动实现 5P-2/5P-3/5F。

### 2026-08-17：5P-2 Prompt Program V1 与 Runtime composition 本地实现

- `SCOPE`：RQ-042 只授权 `5P-2-prompt-program-runtime-composition`；不安装 FastAPI、不实现
  Application Service、不进入 5P-3/5F，不读取 Key、不调用 Riot/Provider/held-out。
- `IMPLEMENTED`：新增严格 Prompt Program manifest/catalog/resolver，复用既有
  `PromptContextSnapshot` component fingerprint；checked-in `recent-form-review-coach@1.0.0`
  仅保存组合身份与 SHA-256，不保存 Prompt 正文。
- `DRIFT-GATE`：组合根启动时 `verify_all()`，Runtime identity 每次从 verified resolver 获取；
  Skill/version、Context、secure Evaluation 1.1 或组件摘要漂移均 fail closed。旧 direct Runtime
  测试使用显式 legacy adapter，不能冒充产品 Program 验证。
- `VERIFIED-LOCAL`：相邻聚焦 `142 passed`，完整 `805 passed, 110 subtests passed`；两套 RAG、
  compileall、Harness dry-run、secret/tracked-data、governance 和 diff check 通过；本批外部 I/O 为 0。
- `CURRENT`：5P-2 尚待提交、推送与 exact-SHA 公共 CI；成功后才交接到 5P-3 Domain Pipeline
  Promotion & Application Service，不得提前实现后续端点或 5F。

### 2026-08-17：5P-2 exact-SHA 公共闭环与 5P-3 交接

- `PUBLIC-VERIFIED`：提交 `0a9651f4e305616626c58ea28e2c300a491f2a3b` 的 Actions run
  `31988837293` 通过完整 pytest、两套 RAG、compileall、governance、SDK/tracked-data boundary
  与 Harness dry-run；CI 无 Key/Provider/held-out I/O。
- `CLOSED`：5P-2 Prompt Program V1 & Runtime Composition Root 正式完成；只证明组合身份、
  drift gate 与 Runtime provenance，不证明 Prompt/模型质量或 API 产品已完成。
- `CURRENT`：canonical 唯一下一检查点切换为 `5P-3-domain-application-service`；按 RQ-042
  范围闭环等待用户再次明确继续，不自动实现 5P-3/5P-4/5F。

### 2026-08-17：5P-3 Domain/Application Service 本地实现

- `SCOPE`：RQ-043 只授权提升 Summary/Report domain services、建立 Application Service/安全
  错误映射，并允许 secure execution factory 的相邻深化；未安装 FastAPI、未实现 receipt/query。
- `DOMAIN`：Summary 与确定性 Markdown 纯业务逻辑已提升到 `app.lol`；CLI 只保留参数、真实依赖、
  文件与打印。短局、timeline unavailable 和报告字节兼容均有直接测试。
- `APPLICATION`：严格顺序固定为 Summary → Schema/有效比赛 → deterministic report → compiler/
  run_id → Runtime；上游/配置/Runtime 失败只投影固定错误码和受控元数据，不保存正文、URL、Key 或路径。
- `COMPOSITION`：产品默认 factory 真实使用 Secure Evaluation 1.1、bounded reviser 与 validator；
  显式测试 factory 保持可注入，Program identity 与实际执行组件已有类型证据。
- `VERIFIED-LOCAL`：Domain 7、Application 20、Prompt Program 10、相邻纵向 263、完整
  `830 passed, 110 subtests passed`；两套 RAG、compileall、治理、安全边界、dry-run 和 diff 通过。
- `NO-IO`：Key/Riot/Provider/held-out I/O 为 0；Fake upstream/Runtime 只证明控制流，不证明模型质量。
- `CURRENT`：5P-3 仍进行中，只待提交、推送与 exact-SHA 公共 CI；成功前不交接或实现 5P-4。

### 2026-08-17：5P-3 exact-SHA 公共闭环与 5P-4 交接

- `PUBLIC-VERIFIED`：提交 `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 的 Actions run
  `31998739178` 通过完整 pytest、两套 RAG、compileall、governance、SDK/tracked-data boundary
  与 Harness dry-run；CI 无 Key/Riot/Provider/held-out I/O。
- `CLOSED`：5P-3 Domain Pipeline Promotion & Application Service 正式完成；这只证明本地
  product control flow、安全错误与 verified Runtime composition，不证明 HTTP 或真实模型质量。
- `CURRENT`：canonical 唯一下一检查点切换为 `5P-4-file-backed-run-receipt-query`，等待用户
  再次明确继续；不自动实现 receipt/query、FastAPI 或 5F。

### 2026-08-17：5P-4 File-backed Receipt/Query 本地实现

- `SCOPE`：RQ-044 只授权 body-free receipt、文件 Store、strict Query 与 Application receipt
  接缝；未安装 FastAPI，未进入 HTTP/SQL/Memory/恢复/5F。
- `RECEIPT`：严格 immutable `ApiRunReceipt` 固定保存 Runtime/publication/terminal、可空 Trace
  reference、UTC 时间和 report availability；同目录原子 create-if-absent Store 不允许覆盖。
- `QUERY`：run_id → receipt → Trace SHA/Schema → manifest publication/final decision → 唯一 final
  Artifact identity/真实字节 SHA/UTF-8 的证据链已实现；公开 View 不含 Provider、路径、Prompt、
  Tool data、异常或正文。
- `FAIL-CLOSED`：not found、report unavailable、integrity failure 只返回固定 code；rejected、重复
  final、终态不一致、坏 Schema/digest/bytes 均不暴露报告。早期 failed run 只允许最小安全视图。
- `APPLICATION`：类型化 completed/failed Runtime 结果在外部投影前写 receipt；wrong run_id、
  未类型化异常与前置上游失败不伪造 receipt。
- `VERIFIED-LOCAL`：聚焦 50、相邻 `179 passed, 12 subtests passed`、完整
  `860 passed, 110 subtests passed`；两套 RAG、compileall、governance、安全边界、dry-run 和
  diff check 通过，外部 I/O 为 0。
- `CURRENT`：5P-4 仍进行中，只待提交、推送和 exact-SHA 公共 CI；成功前不交接 5P-5。

### 2026-08-17：5P-4 exact-SHA 公共闭环与 5P-5 交接

- `PUBLIC-VERIFIED`：提交 `932a863120a4561f58c477a69becbccd2ec9ff45` 的 Actions run
  `32002994441` 通过完整 pytest、两套 RAG、compileall、governance、SDK/tracked-data boundary
  与 Harness dry-run；CI 无 Key/Riot/Provider/held-out I/O。
- `CLOSED`：5P-4 File-backed Run Receipt & Query Projection 正式完成；这只证明单进程文件
  查询完整性与安全投影，不证明 FastAPI、数据库事务、崩溃恢复或生产部署。
- `CURRENT`：canonical 唯一下一检查点切换为
  `5P-5-thin-fastapi-adapter-no-io-vertical-slice`，等待用户再次明确继续；不自动安装 FastAPI、
  实现 HTTP、进入 5P-6 或 5F。
