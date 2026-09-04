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

### 2026-08-17：RQ-045 恢复并完成 5P-5 本地实现

- `RESUMED`：用户明确“继续5P-5”，按 RQ-045 只恢复薄 FastAPI Adapter/no-I/O 纵向切片；
  先以红灯测试冻结四个端点与安全错误合同，再加入 FastAPI/httpx 依赖。
- `IMPLEMENTED-LOCAL`：`app/api/main.py` 采用显式 Application/Query Port；OpenAPI 只暴露
  recent POST、run GET、report GET、health；不导入 CLI/Provider/Harness/Runtime implementation，
  不读取 Key 或发网络请求。
- `VERIFIED-LOCAL`：API 聚焦 24，完整 `884 passed, 1 warning, 110 subtests passed`；真实
  no-I/O 纵向测试经过 Catalog、Prompt Program、AgentRuntime、RAG、Harness、Fake Provider、
  receipt/Trace/Artifact 与 Query Service；两套 RAG、compileall、治理、安全边界、Harness dry-run
  和 diff check 通过。warning 为 FastAPI TestClient 的上游 httpx 迁移提示。
- `CURRENT`：5P-5 只待提交、推送和 exact-SHA 公共 CI；公共成功前不交接到 5P-6，不进入 5F/阶段 6。

### 2026-08-17：5P-5 exact-SHA 公共闭环

- `PUBLIC-VERIFIED`：提交 `6d1e5b0af186f523bee35c24c6873578a149b824` 已推送；GitHub Actions
  run `32005648179` completed/success，pytest、两套 RAG、compileall、治理、SDK boundary、
  tracked secret/run-data 与 Harness dry-run 全部成功。
- `CLOSED`：5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice 正式完成；这只证明本地同步 HTTP
  接线、错误合同、文件查询和 Fake Provider 纵向证据，不证明真实模型质量、鉴权、SQL/恢复、
  公网部署或完整前端。
- `CURRENT`：canonical 唯一下一检查点切换为 `5P-6-product-slice-evaluation-exit-review`，
  等待用户明确继续；不自动实现 5P-6/5F/阶段 6。

### 2026-08-17：RQ-046 恢复并完成 5P-6 本地退出审查

- `RESUMED`：用户再次明确“继续”，只授权 canonical 的 5P-6 产品切片退出审查；没有读取 Key、
  调用 Riot/Provider、运行 held-out 或进入 5F/阶段 6。
- `MATRIX`：原设计十项功能要求、分层控制权、NFR/安全/no-I/O 与 deferred/unknown 能力均已
  映射到源码、直接测试、既有 5P exact-SHA Actions、限制和退出影响。
- `TEACHING`：退出 review 已解释数据流/控制流、各层存在原因、测试能证明和不能证明的内容、
  为什么当前是 Agent 产品切片而不只是 RAG，以及参考项目/框架的采用门。
- `VERIFIED-LOCAL`：5P 聚焦 `121 passed, 1 warning`、Runtime/Harness 相邻 `166 passed`、完整
  `884 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、Harness boundary、
  tracked secret/run-data、dry-run、governance 和 diff check 通过，外部 I/O 为 0。
- `DECISION`：本地 `close-with-deferred-boundaries`；当前没有 5P 结构性代码缺口，真实 Riot/
  Provider、SQL/Memory/SSE/鉴权/前端/部署等保持 deferred/unknown。
- `CURRENT`：5P-6 仍 in progress，只待退出审查提交、推送和 exact-SHA 公共 CI；成功前不正式
  关闭 5P，不交接或实施 5F。

### 2026-08-17：5P-6 exact-SHA 公共闭环与 5F 交接

- `PUBLIC-VERIFIED`：退出审查提交 `8c8acc6911209e645cfaee18bd40870f78d8704f` 的 Actions run
  `32010604551` completed/success；pytest、两套 RAG、compileall、governance、SDK/tracked-data
  boundary 与 Harness dry-run 全部通过。
- `CLOSED`：5P-6 Product Slice Evaluation & Exit Review 与整个 5P 正式完成；最终裁决为
  `close-with-deferred-boundaries`，真实 Provider 领域质量、生产 API/部署、安全和后续能力仍
  按矩阵保持 deferred/unknown。
- `HANDOFF`：canonical 唯一下一检查点为 `5F-entry-design` 准备状态；等待用户再次明确继续，
  不自动实施 Pi/Claude Agent SDK、模型切换、真实 Provider 或阶段 6。

### 2026-08-17：RQ-047 Pi-only 5F 入口设计

- `DECISION`：用户确认 5F 只实测 Pi；Claude Agent SDK 不进入代码级对照、依赖安装或真实调用，
  只保留书面替代/排除分析。
- `RATIONALE`：Pi 的轻量 Agent Runtime/多 Provider 方向更接近当前 AgentLoop 采用问题；Claude
  SDK 会同时改变模型、工具、Session 和 Harness 语义，无法形成干净 Runtime 归因。
- `BOUNDARY`：5F 入口设计只冻结官方 Pi source/license audit、同一 recent-form-review 的无 I/O
  protocol spike、合同/安全/Trace/Harness/跨语言成本指标与 adopt/partial-adopt/reject 门槛；
  不安装 Pi、不修改主 Runtime、不读取 Key、不调用 Provider。
- `CURRENT`：canonical 仍为 `5F-entry-design`，当前正在完成 Pi-only ADR/设计文档；完成公共
  验证后才交接到 `5F-1-pi-source-license-contract-audit`，不自动实施下一子阶段。

### 2026-08-17：5F-entry-design Pi-only 公共闭环与 5F-1 交接

- `PUBLIC-VERIFIED`：提交 `ce979752808271696b1dfe499317ead66de6aacb` 的 Actions run
  `32013948784` completed/success；治理、pytest、两套 RAG、compileall、SDK/tracked-data
  boundary 与 Harness dry-run 全部通过。
- `CLOSED`：Pi-only 入口设计正式完成；这不等于 Pi 已安装、已接入、已采用或真实模型质量已验证。
- `HANDOFF`：canonical 唯一下一检查点为 `5F-1-pi-source-license-contract-audit` 准备状态，
  等待用户再次明确继续；不自动实施源码审计、Pi adapter 或真实 Provider 调用。

### 2026-08-17：RQ-048 恢复并完成 5F-1 本地审计

- `RESUMED`：用户再次明确“继续”，只授权 canonical 的
  `5F-1-pi-source-license-contract-audit`；没有安装 Pi、读取 Key、调用 Provider 或修改主 Runtime。
- `IDENTITY`：历史 `badlogic/pi-mono` 当前重定向到 `earendil-works/pi`；实验候选冻结 release
  `v0.84.2` / npm `gitHead` `914cf1472e715297caa30db4b9535d534a9eb718`、两个 `0.84.2` 包、
  official-registry integrity、MIT 与 Node `>=22.19.0`。
- `CONTRACT`：Pi 具备自定义 StreamFn、Tool schema、Agent lifecycle events、Usage 和 Abort 接缝；
  但默认 parallel，且没有 RiftCoach 等价的整批 Tool 原子预检、跨轮 duplicate、总调用/Context/
  deadline 策略、Usage completeness、body-free Trace 或 ReviewHarness 发布权。
- `SECURITY`：只允许低层 Agent Core + Scripted StreamFn + 单一 `knowledge.search`；拒绝 Coding Agent
  默认工具、ResourceLoader、Extension、Session/Auth/ModelRuntime。Node permission 只作 defense-
  in-depth，当前 Node 24 不能据此宣称硬断网；父进程仍持有 deadline/kill 与协议白名单，硬网络
  隔离如有需要必须由 OS/容器提供。
- `VERIFIED-LOCAL`：完整 `884 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、
  governance、Harness SDK/tracked-data boundary、dry-run 与 diff check 全部通过，Pi/Key/Provider
  I/O 为 0。
- `DECISION-LOCAL`：允许有条件进入 `5F-2-offline-protocol-adapter-spike`，不代表采用 Pi；5F-1
  仍待本地门禁、提交、推送和 exact-SHA 公共 CI，成功前不交接 5F-2。

### 2026-08-17：5F-1 exact-SHA 公共闭环

- `VERIFIED-PUBLIC`：提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 已由 GitHub Actions
  run `32016852979` 完成 exact-SHA 公共验证；pytest、两套 RAG、compileall、治理、安全边界与
  Harness dry-run 全部成功。
- `CLOSED`：5F-1 正式完成，裁决仍为“允许有条件进入 5F-2”，不等于采用、安装或接入 Pi。
- `HANDOFF`：canonical 唯一下一检查点为 `5F-2-offline-protocol-adapter-spike` 准备状态，等待
  用户再次明确继续；不自动安装依赖、创建 sidecar/lockfile、读取 Key 或调用 Provider。

### 2026-08-17：RQ-049 恢复 5F-2 与冻结 sidecar 设计

- `RESUMED`：用户再次明确“继续”，只授权 canonical 的 5F-2 离线协议实验；不授权真实 Provider、
  主 Runtime/Harness 接入或 5F-3。
- `DECISION`：ADR-0035 选择低层 Pi Agent Core + 版本化限长 JSONL sidecar，拒绝产品编排迁入
  Node 和完整 Pi Coding Agent RPC；Python 保留 ToolRuntime、deadline 和进程生命周期。
- `NO-IO`：该设计批当时只新增设计/实施计划并准备协议红灯；尚未安装 Pi、创建 package/lockfile、读取 Key、
  调用 Provider/Riot 或修改产品 Runtime。

### 2026-08-17：5F-2 Offline Protocol Adapter Spike 本地退出审查

- `IMPLEMENTED-NO-IO`：exact Pi 0.84.2 lock、Node sidecar、Python controller、版本化限长 JSONL、
  一个真实本地 `knowledge.search` proxy、整批 Tool preflight、Usage 四态、进程 deadline/kill 与
  body-free event 已实现；Scripted StreamFn 是唯一 Provider 接缝，外部 Provider/Riot calls 为 0。
- `CORRECTED`：修复 strict JSON→Pydantic 解码、stderr/EOF reader 竞态、Pi abort 状态、最后迭代
  Tool 零副作用、失败 Tool 预算计数和 pre-spawn Tool contract drift 稳定终态。
- `COST`：本机 `npm ci --ignore-scripts` 约 6063 ms；94 packages / 11,355 files /
  62,364,713 bytes；六次 fresh process 399.75-453.15 ms，后五次中位数 413.71 ms。仅为本机量级，
  不是生产 p50/p95。
- `VERIFIED-LOCAL`：Pi 聚焦 `35 passed`、相邻 `99 passed`、完整
  `919 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、Node syntax/tree、Harness
  SDK/tracked-data、dry-run、governance 和 diff check 通过。
- `DECISION-LOCAL`：`pass-with-boundaries`；协议和控制流足以进入下一评估门，但不构成 Pi adopt、
  主 Runtime/Harness 接入或模型质量证据。
- `CURRENT`：5F-2 仍 in progress，只待实现/退出审查提交、推送和 exact-SHA 公共 CI；成功前不
  关闭 5F-2，不交接或实施 5F-3。

### 2026-08-17：5F-2 exact-SHA 公共闭环与 5F-3 交接

- `VERIFIED-PUBLIC`：实现提交 `f62f078faca0d93494478011d2fe18cdeb85970f` 的 Actions run
  `32022258177` completed/success；Node 24、`npm ci --ignore-scripts`、完整 pytest、两套 RAG、
  compileall、治理、Harness/secret boundary 和 dry-run 全部通过。
- `CLOSED`：5F-2 Offline Protocol Adapter Spike 正式完成，裁决为 `pass-with-boundaries`；这只
  证明隔离协议/控制流，不代表 Pi adopt、真实模型质量或主 Runtime/Harness 接入。
- `HANDOFF`：canonical 唯一下一检查点为 `5F-3-contract-security-harness-evaluation` 准备状态，
  等待用户明确继续；不自动读取 Key、调用 Provider 或实现 5F-3。
### 2026-08-17：RQ-050 恢复 5F-3 并完成本地退出评测

- `RESUMED`：用户再次明确“继续”，只授权 5F-3 完整合同、安全、Harness/Trace 与维护成本评测；
  未授权 5F-4 或真实外部调用。
- `IMPLEMENTED-NO-IO`：evaluation-only Pi draft adapter 复用现有 Compiler/SkillReviewExecutor/
  ReviewHarness；process-local Tool records 构造真实 Evidence，public result/event/Trace 继续 body-free。
- `TRACE`：per-call Usage/finish reason 可进入现有 Recorder，成功纵向路径生成合法 RuntimeTrace；
  missing Usage 不归零，坏 citation/Tool/process failure 不发布 Pi draft。
- `HARD-GAPS`：Context token-unit 与 char guard 不等价；extended Pi terminal 无法进入现有 Agent
  terminal；event 为 child 完成后批量投影，缺少 live timing/stream parity。
- `VERIFIED-LOCAL`：Pi 聚焦 45、相邻 196、完整 `929 passed, 1 warning, 110 subtests passed`；
  external Provider/Riot/Key/held-out I/O 为 0。
- `DECISION-LOCAL`：`harness-compatible-but-runtime-gate-failed`。根据既定条件门，5F-4 不准入；
  当前仍待完整门禁、提交、推送和 exact-SHA CI，公共成功前不关闭 5F-3 或进入 5F-5。
### 2026-08-17：5F-3 exact-SHA 公共闭环，5F-4 未进入

- `VERIFIED-PUBLIC`：实现/退出提交 `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已由 Actions run
  `32025522606` 完成 exact-SHA 公共验证；Node/Python、pytest、RAG、治理、安全边界和 dry-run 全部成功。
- `CLOSED`：5F-3 正式完成，裁决保持 `harness-compatible-but-runtime-gate-failed`；不表示真实模型
  质量失败或 Pi 最终采用裁决已作出。
- `BRANCH-NOT-ENTERED`：5F-4 的 Context/terminal/live timing 前置硬门未满足；真实 Provider slice
  没有信息增益，因此外部 calls 保持 0。
- `HANDOFF`：canonical 唯一下一检查点为 `5F-5-adoption-decision-exit-review` 准备状态，等待用户
  明确继续；不自动作 partial-adopt/reject 决策。

### 2026-08-17：RQ-051 恢复 5F-5 与本地最终采用裁决

- `RESUMED`：用户再次明确“继续”，只授权 canonical 的
  `5F-5-adoption-decision-exit-review`；不补做 5F-4、不读取 Key、不调用 Provider/Riot、不接主
  Runtime/FastAPI，也不自动实施阶段 6。
- `DECISION-LOCAL`：ADR-0037 裁决为 `partial-adopt-evaluation-assets-only`。产品 Runtime 拒绝 Pi，
  Python `AgentRuntimeV1` 保持唯一默认；Pi package/sidecar/evaluation adapter/tests/lockfile/CI 仅作为
  冻结、可复现的评测资产保留。
- `METHOD`：吸收严格版本协议、fail-closed projection、硬采用门和无信息增益停止方法，不迁移
  Pi Session/Provider/Coding tools，也不建立双 Runtime 开关。
- `LIFECYCLE`：安全漏洞、Node 不兼容、持续 CI 不稳定/成本显著或大规模追随维护将触发新 ADR，
  优先归档可执行实验；产品合同不得为了实验变绿而放宽。
- `VERIFIED-LOCAL`：Pi 聚焦 45、完整 `929 passed, 1 warning, 110 subtests passed`；两套 RAG、
  exact Node tree、compileall、governance、Harness dry-run、安全边界和 diff check 通过，外部 I/O 为 0。
- `CURRENT`：5F-5 仍 in progress，当前只待提交、推送与 exact-SHA 公共 CI；公共成功前不关闭
  5F，不交接 `6A-entry-design`。

### 2026-08-17：5F-5 exact-SHA 公共闭环与 6A 交接

- `VERIFIED-PUBLIC`：最终采用/退出提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已由 Actions run
  `32028206103` 完成 exact-SHA 公共验证；Node/Python、完整 pytest、两套 RAG、compileall、治理、
  安全边界和 Harness dry-run 全部成功。
- `CLOSED`：5F-5 与整个阶段 5 正式完成；裁决保持 `partial-adopt-evaluation-assets-only`，即产品
  拒绝 Pi、冻结保留 evaluation-only 资产与采用门方法。
- `HANDOFF`：canonical 唯一下一检查点为 `6A-entry-design` 准备状态，等待用户明确继续；不自动
  实现 SQL、Session、Memory、SSE、鉴权、前端、真实 Provider 或部署。

### 2026-08-17：RQ-052 恢复 6A-entry-design 与首个设计确认门

- `RESUMED`：用户再次明确“继续”，只授权 6A 完整 FastAPI/SQL 任务模型的入口设计；不授权直接
  实现 SQL、Session、Memory、SSE、鉴权、前端、真实 Provider 或部署。
- `AUDIT`：现有 5P 同步 file receipt 存在 Trace/receipt crash gap、无多 worker 原子 claim；正式
  production app/lifespan/worker/SQL 尚不存在。EchoMind 可参考 lifespan/user-conversation 分层，但
  其全局组件、宽泛 CORS、Redis/Chroma Memory 和非持久 background task 不原样迁移。
- `DESIGN-GATE`：数据库生产目标和测试策略会改变事务、并发、迁移、CI 与部署成本；在冻结 ADR 前
  先通过 brainstorming 单项确认，不在实现中默默决定。
- `CURRENT`：canonical 仍为 `6A-entry-design`，当前暂停在 SQL approach 确认；尚无 6A 产品代码或
  外部 I/O。

### 2026-08-17：6A 数据库方案 A 获用户确认

- `ACCEPTED`：PostgreSQL 是 6A 唯一生产语义基线；SQLAlchemy 2 负责映射，Alembic 负责迁移。
- `TEST-BOUNDARY`：普通逻辑允许 Fake/单元测试；事务、迁移和并发任务领取必须在真实 PostgreSQL
  Docker/CI 中验证，SQLite 通过不能替代 PostgreSQL 语义证据。
- `SCOPE`：本决定没有授权安装依赖或实现 SQL；也没有预先选择同步执行、进程内后台任务或独立
  polling worker。
- `CURRENT`：canonical 仍为 `6A-entry-design`，下一单项确认门是任务执行架构。

### 2026-08-17：6A 任务执行方案 3 获用户确认

- `ACCEPTED`：FastAPI 与独立 PostgreSQL polling worker 保持同仓库同部署；API 创建 queued task
  后返回 202，Worker 使用 PostgreSQL 事务原子领取并调用既有 Application Service。
- `REJECTED-FOR-6A`：同步长请求不能解决 HTTP 阻塞/任务追踪；FastAPI 进程内 background task
  不能提供重启持久性或可靠多 worker ownership；Redis/Celery/Kafka 当前没有必要。
- `BOUNDARY`：该选择不等于微服务、完整消息队列或阶段 8 的 lease/retry/cancel/resume；复杂恢复
  不在 6A 入口设计中提前实现。
- `CURRENT`：canonical 仍为 `6A-entry-design`，开始逐节确认架构与数据流；尚无 6A 产品实现或
  外部 I/O。

### 2026-08-17：6A 架构与数据流章节获用户确认

- `ACCEPTED`：保持模块化单体；FastAPI 和 polling Worker 是同仓库/同一产品部署的不同进程角色。
- `TRANSACTION-BOUNDARY`：创建、claim 和终态投影分别使用短事务；Agent/Tool/RAG/Provider/Harness
  执行不得占用数据库锁。
- `DATA-BOUNDARY`：PostgreSQL 保存任务控制面和 Artifact 引用，报告/评测/Trace 正文继续在既有
  Artifact/Trace 数据面；读取时必须按身份和摘要交叉验证。
- `CURRENT`：下一逐节确认项为 task schema 与状态机；完整 ADR/设计和产品实现均未完成。

### 2026-08-17：6A task schema 与状态机章节获用户确认

- `ACCEPTED`：任务使用服务器生成的 `task_id`/`run_id` 双身份；run_id 入队时预留并绑定未来
  Runtime/Artifact。
- `STATE`：V1 只允许 `queued → running → succeeded|failed`；终态不可逆，中断以安全 failed reason
  表达；自动重试、cancel/resume 和 lease 留后续阶段。
- `CONTROL-DATA`：owner、幂等 Key/请求指纹、规范化小输入、Worker claim、终态投影和 Artifact 引用
  属于 SQL 控制面；Prompt、Provider 原响应、报告正文和异常正文不落任务表。
- `CURRENT`：下一逐节确认项为 SQL/Artifact、事务/幂等/ownership 与 crash reconciliation。

### 2026-08-17：6A SQL/Artifact 核心确认与 hard-crash 边界修正

- `ACCEPTED`：创建、claim、终态投影使用独立短事务；Runtime 在事务外；owner-scoped 幂等与 Artifact
  identity/SHA 交叉验证成立。
- `SAFE-RECONCILIATION`：已有匹配 immutable receipt 时可补齐 succeeded。
- `REOPENED`：无 receipt 的 running task 在多 Worker 下不能只凭新 Worker 启动自动判死；没有
  lease/heartbeat 或运维确认就缺少 owner 已死亡证据。
- `CURRENT`：比较保守人工恢复、提前 lease/heartbeat 与单 Worker 限制；选定前不冻结失败边界。

### 2026-08-17：6A hard-crash 方案 A 获用户确认

- `ACCEPTED`：匹配 immutable receipt/identity/SHA 时可自动补齐 succeeded；graceful shutdown 由
  owner Worker 条件失败；无终态证据的 hard crash 只标记 recovery-required，人工确认后受限更新。
- `NO-AUTO-REPLAY`：6A 不自动重跑可能收费或产生副作用的 Runtime 任务。
- `DEFERRED`：lease、heartbeat、fencing token、自动 reclaim 和迟到结果隔离保留阶段 8。
- `CURRENT`：下一逐节确认项为完整失败语义与 HTTP 投影。

### 2026-08-17：6A 失败语义与 HTTP 投影章节获用户确认

- `ASYNC-HTTP`：POST 202 只承诺 durable enqueue；queued/running/succeeded/failed 通过 task resource
  查询，upstream 异步失败不会伪装成同步 POST 成功报告。
- `SEPARATION`：task succeeded 与 Harness published/degraded/rejected 正交，质量拒绝不是系统执行失败。
- `SAFE-ERRORS`：validation、idempotency、DB、ownership/not-found、not-ready 与 integrity failure 分层，
  worker/exception/Provider body 不进入公共响应。
- `CURRENT`：下一逐节确认项为作品集规模性能、容量、可靠性、可观测性和成本 NFR。

### 2026-08-17：6A 作品集规模 NFR 获用户确认

- `SCALE`：单服务器 API+Worker+PostgreSQL 起步；Worker 默认单任务并发，可增加进程且由真库并发
  claim 测试证明不会重复执行。
- `TARGETS`：warm-DB 创建/查询服务端 p95 `<300ms`，有容量时 claim p95 `<2s`；owner 3/global 50
  非终态背压；idle polling 退避+jitter。这些是待验证目标，不是现有测量结果。
- `HONESTY`：liveness/readiness 分离；不承诺 99.9%、跨机容灾、自动 lease 恢复或 Artifact 备份。
- `CURRENT`：下一逐节确认项为 owner trust、安全和 task/run 数据生命周期。

### 2026-08-17：6A 安全与数据生命周期章节获用户确认

- `ACCESS`：owner 只来自可信 ActorContext，全部 task/run/report 查询 owner-scoped；开发固定 owner
  不构成公网 Auth，不存在/越权统一 404。
- `FAIL-CLOSED`：CORS 默认关闭，Secret/env 隔离，参数化 SQL 和 body-free 日志；Auth/HTTPS/限流/
  安全响应头在公开部署前是硬门。
- `RETENTION`：原始缓存、terminal task/run 内容和运维日志默认 7/90/30 天；terminal 可 owner 删除，
  active 删除不替代阶段 8 cancel；长期 Memory 不在 6A 建立。
- `CURRENT`：下一逐节确认项为分层测试矩阵。

### 2026-08-17：6A 分层测试矩阵获用户确认

- `FAST-LAYER`：状态/指纹/owner/error 用纯逻辑与 Fake 测试。
- `POSTGRES-BLOCKING`：SQLAlchemy/Alembic、约束/回滚、幂等、两 Worker 原子 claim、CAS/reconciliation
  必须使用真实 PostgreSQL service/container；SQLite 绿灯不可替代。
- `VERTICAL`：API/Worker 分层集成后，用现有 Application+本地 RAG+Fake Provider+Runtime/Harness+
  Artifact 跑离线纵向；CI 不读取 Key、不调用 Riot/Provider。
- `CURRENT`：下一且最后一个逐节确认项为 6A 原子实施顺序。

### 2026-08-17：6A 原子顺序与 entry-design 资产获用户确认

- `SEQUENCE`：用户确认 6A-1 PostgreSQL Foundation 至 6A-7 Packaging/Exit 七个原子实施批次；每批
  单独教学、TDD、门禁、提交与 exact-SHA CI。
- `DOCUMENTED`：ADR-0038、完整 design 和 implementation plan 已本地创建，覆盖全部逐节确认和边界。
- `NO-IMPLEMENTATION`：当前未安装 SQL 依赖、创建 migration、启动 PostgreSQL、修改产品 API/Worker
  或调用外部服务。
- `CURRENT`：`6A-entry-design` 只待本地门、提交/推送和 exact-SHA 公共 CI；成功后交接 6A-1 准备
  状态且不自动实施。

### 2026-08-17：6A entry-design 本地门禁通过

- `VERIFIED-LOCAL`：完整 `929 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、
  Harness dry-run、governance、tracked Secret/run-data、SDK boundary 和 diff check 通过。
- `COMMAND-CORRECTION`：默认桌面 Python 无 pytest 的首次命令未运行测试；随后明确使用仓库 `.venv`
  完整通过，不能把首次解释器错误计为产品失败或绿灯。
- `NO-I/O`：未安装 SQL 依赖、启动 PostgreSQL、读取 Key 或调用 Riot/Provider。
- `CURRENT`：只待提交、推送与 exact-SHA 公共 CI；成功前 entry design 不关闭。

### 2026-08-17：6A-entry-design exact-SHA 公共闭环

- `VERIFIED-PUBLIC`：提交 `c0b5af0eec1654c35afddb3c8a66b774a233a688` 已由 GitHub Actions run
  `32041343696` 完成 exact-SHA 公共验证；完整 pytest、两套 RAG、compileall、治理、安全边界和
  Harness dry-run 全部成功。
- `CLOSED`：ADR-0038、design、implementation plan 与七批次顺序正式冻结，`6A-entry-design` 完成。
- `NO-IMPLEMENTATION`：未安装 SQL 依赖、创建 migration、启动 PostgreSQL、实现 Repository/Worker/
  async API，外部 I/O 为 0。
- `HANDOFF`：canonical 只交接 `6A-1-postgresql-foundation` 准备状态，等待用户明确继续。

### 2026-08-17：RQ-053 恢复 6A-1 PostgreSQL Foundation

- `RESUMED`：用户明确“开始”，只授权 canonical 的 `6A-1-postgresql-foundation`。
- `SCOPE`：建立 SQLAlchemy 2/Alembic/psycopg 配置、task ORM row、initial migration、Compose 与真实
  PostgreSQL CI；不实现 Repository、claim、Worker、异步 API、Session/Memory/SSE/前端。
- `ENVIRONMENT`：本机无 Docker，迁移测试本地必须明确 skip；GitHub Actions PostgreSQL service 是
  本批唯一可用的真实数据库阻塞证据，SQLite 不得替代。
- `CURRENT`：先同步持久状态与红灯测试，再实现最小 Foundation；完成本地门、提交、推送与 exact-SHA
  公共 CI 前，6A-1 保持 in progress。

### 2026-08-17：6A-1 exact-SHA PostgreSQL 公共闭环

- `VERIFIED-PUBLIC`：实现提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 已由 Actions run
  `32043214500` 完成 exact-SHA 公共验证；`pytest` 与 `postgres-migrations` 两个 job 均成功。
- `REAL-POSTGRESQL`：PostgreSQL 17 service 执行可逆 Alembic migration、JSONB/timestamptz/CHECK
  round-trip 和 metadata drift check，补齐本地无 Docker 的三个 skip。
- `CLOSED`：6A-1 PostgreSQL Foundation 正式完成；没有实现 Repository/claim/Worker/API。
- `HANDOFF`：canonical 只交接 `6A-2-task-contract-repository` 准备状态，等待用户明确继续。

### 2026-08-18：RQ-054 恢复 6A-2 Task Contract & Repository

- `RESUMED`：用户再次明确“继续”，只授权 canonical 的 `6A-2-task-contract-repository`。
- `SCOPE`：实现 task domain/port/fingerprint/service 与 PostgreSQL owner-scoped idempotent create/query、
  capacity/rollback；不实现 claim、Worker、Application/Artifact、HTTP、Memory 或外部 I/O。
- `ATOMICITY`：Service 负责业务政策，Repository 在单 transaction 内处理 replay/conflict/capacity/create；
  不把 count 与 insert 暴露成可竞态的多步 Service 调用。
- `CURRENT`：先完成红灯纯逻辑/Fake 合同，再写真实 PostgreSQL Repository 测试与实现；public CI 前
  6A-2 保持 in progress。

### 2026-08-18：6A-2 本地实现与门禁

- `IMPLEMENTED-LOCAL`：严格 task models、canonical fingerprint、Fake service 与 PostgreSQL
  create/query Repository 已完成；advisory lock 只覆盖 create 短事务。
- `TESTED-LOCAL`：domain/service `29 passed`，完整 `977 passed, 8 skipped, 1 warning, 110 subtests`
  通过；两套 RAG、compileall、Harness、治理、安全和 YAML 门通过；真库 5 项仍待 public CI。
- `BOUNDARY`：不实现 claim、Worker、Application/Artifact、HTTP、Session/Memory 或外部 I/O。
- `CURRENT`：提交/推送并等待 exact-SHA PostgreSQL job；成功前 6A-2 保持 in progress。

### 2026-08-18：6A-2 exact-SHA PostgreSQL 公共闭环

- `VERIFIED-PUBLIC`：提交 `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 已由 Actions run
  `32046532695` 完成 exact-SHA 公共验证；`pytest` 与 `postgres-migrations` 均成功。
- `REAL-REPOSITORY`：PostgreSQL 真实验证 replay/conflict、owner scope、capacity/terminal、rollback
  与 concurrent same-key exactly-one-row 语义。
- `CLOSED`：6A-2 Task Contract & Repository 正式完成；没有实现 claim、Worker、Application/API。
- `HANDOFF`：canonical 只交接 `6A-3-atomic-claim-polling-worker` 准备状态，等待用户明确继续。

### 2026-08-18：RQ-055 恢复 6A-3 Atomic Claim & Polling Worker

- `RESUMED`：用户再次明确“继续下一轮”，只授权 canonical 的
  `6A-3-atomic-claim-polling-worker`。
- `SCOPE`：实现 `FOR UPDATE SKIP LOCKED` deterministic claim、worker ownership/terminal CAS、
  idle backoff/jitter、graceful shutdown 与 Fake Executor Worker 控制流；Agent 执行期间不得持有
  transaction/row lock。
- `DEFERRED`：真实 Application/Artifact/reconciliation、FastAPI、lease/heartbeat/fencing、自动
  retry/reclaim、cancel/resume、Session/Memory 与外部 Riot/Provider I/O 均不在本轮。
- `CURRENT`：先写 Fake polling/Worker 与真实 PostgreSQL claim/CAS 红灯，再做最小实现；public
  PostgreSQL CI 前 6A-3 保持 in progress。

### 2026-08-18：6A-3 本地实现与横向门禁完成

- `IMPLEMENTED-LOCAL`：未修改已公开 migration；新增 `TaskTerminal`、Repository
  `FOR UPDATE SKIP LOCKED` deterministic claim、ownership/terminal CAS、PollingPolicy、Fake Executor
  Worker loop、backoff/jitter、graceful drain 与 fail-closed CLI。
- `VERIFIED-LOCAL`：聚焦 `30 passed, 7 skipped`，完整 `1008 passed, 15 skipped, 1 warning, 110 subtests`
；两套 RAG、compileall、Harness dry-run、治理、秘密/SDK/YAML/diff 门全部通过；本机无 PostgreSQL，
  7 项真库 claim 测试待 CI。
- `CURRENT`：本地实现完成但 6A-3 仍 in progress；下一步只提交/推送并等待 exact-SHA PostgreSQL
  job，成功前不关闭、不进入 6A-4。

### 2026-08-18：6A-3 exact-SHA 公共闭环与 6A-4 交接

- `VERIFIED-PUBLIC`：提交 `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 的 Actions run `32097561436`
  中 `pytest` 与 `postgres-migrations` 均 completed/success；真实 PostgreSQL 17 补齐 7 项 claim/
  CAS/concurrency skip。
- `CLOSED`：6A-3 Atomic Claim & Polling Worker 正式完成；证据只覆盖 durable claim、Worker 控制流、
  ownership/CAS、backoff/jitter 和 graceful shutdown，不覆盖 Application/Artifact、HTTP 或 hard-crash
  自动恢复。
- `HANDOFF`：canonical 唯一下一检查点为 `6A-4-application-artifact-integration` 准备状态，等待
  用户明确继续；不自动实现 run_id integration、reconciliation、异步 API、Session/Memory 或前端。

### 2026-08-18：RQ-056 恢复 6A-4 与本地实现门禁完成

- `RESUMED`：用户再次明确“继续”，只授权 `6A-4-application-artifact-integration`；不进入 6A-5
  异步 FastAPI、lease/heartbeat/retry、Session/Memory/SSE/前端或外部真实 I/O。
- `IMPLEMENTED-LOCAL`：trusted run_id 已贯穿 compiler/Application/Runtime/receipt；真实 Recent Review
  Task Executor、严格 TaskTerminal evidence、task/status/worker/run CAS、receipt-proven reconciliation、
  recovery-required 投影和人工 worker-confirmed-dead CAS 已实现。
- `VERIFIED-LOCAL`：聚焦 `130 passed, 12 skipped`，完整
  `1033 passed, 20 skipped, 1 warning, 110 subtests passed`；两套 RAG、compileall、Harness dry-run、
  governance、秘密/SDK/YAML/diff 门通过。新增 5 项真库测试因本机无 PostgreSQL 明确 skip。
- `AT-THE-TIME`：当时 6A-4 保持 in progress；下一步是提交、推送并等待 exact-SHA PostgreSQL CI。
  该临时状态已由下方公共闭环条目取代；本地离线 Fake Provider 纵向不证明真实模型质量。

### 2026-08-18：6A-4 exact-SHA 公共闭环与 6A-5 交接

- `VERIFIED-PUBLIC`：提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 的 Actions run `32102522662`
  中 `pytest` 与 `postgres-migrations` 均 completed/success；完整 pytest 为 `1033 passed, 20 skipped,
  1 warning, 110 subtests passed`，真实 PostgreSQL job 为 `40 passed`。
- `EVIDENCE`：新增 reconciliation 与 Application/Runtime/Harness/Artifact 纵向测试已在 PostgreSQL 17
  service 中实际执行；migration 可逆性和 metadata head 也通过。CI 无 Key、Riot/Provider 调用。
- `CLOSED`：6A-4 正式关闭，保守 `recovery_required`、人工 worker-matching CAS 与迟到结果拒绝边界保持；
  不外推为自动 lease/reclaim、异步 API、Session/Memory 或公网部署完成。
- `HANDOFF`：canonical 唯一下一检查点改为 `6A-5-async-fastapi-composition` 准备状态，等待用户明确
  继续；不得自动开始实现。

### 2026-08-18：RQ-057 恢复 6A-5 Async FastAPI & Composition

- `RESUMED`：用户再次明确“继续吧”，只授权 `6A-5-async-fastapi-composition`；先以 TDD 冻结
  POST 202、task/run/report query、可信 ActorContext、lifespan 与 live/ready，再实现 API composition。
- `BOUNDARY`：本批不进入 6A-6，不实现 JWT/OAuth、Session/Memory、SSE、前端、lease/retry/reclaim，
  也不读取 Riot/Provider Key 或调用外部服务；同步 SQLAlchemy 保持，除非出现可复现性能 Bad Case。
- `AT-THE-TIME`：canonical 与活动计划已清除等待确认状态；产品代码尚未修改，下一步先运行红灯测试。

### 2026-08-18：6A-5 本地实现与门禁完成

- `IMPLEMENTED-LOCAL`：FastAPI V2 POST 202/task query、trusted ActorContext、owner-scoped run/report、
  lifespan API composition 与 DB/Alembic readiness 已实现；同步 SQLAlchemy 保持，POST 不执行 Agent。
- `VERIFIED-LOCAL`：API 聚焦 `38 passed, 1 skipped`，完整
  `1047 passed, 21 skipped, 1 warning, 110 subtests passed`；两套 RAG、compileall、Harness dry-run、
  governance、Secret/SDK/YAML/diff 门通过。新增真库 API 测试因本机无 PostgreSQL 明确 skip。
- `SCOPE-ADJUDICATED`：6A-5 只关闭 API process composition；真实 Riot/Data Dragon/Provider Worker
  executable composition 属于 6A-7 packaging，当前 Worker CLI 继续 fail-closed，不冒充可部署消费链。
- `AT-THE-TIME`：6A-5/RQ-057 保持执行中；下一步只提交、推送并等待 exact-SHA pytest/PostgreSQL CI。

### 2026-08-18：6A-5 exact-SHA 公共闭环与 6A-6 交接

- `VERIFIED-PUBLIC`：提交 `2492951c20dd6ca897d957d03752b6a2585ce469` 的 Actions run
  `32106378542` 中 `pytest` 与 `postgres-migrations` 均 completed/success；完整 pytest 为
  `1047 passed, 21 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL job 为 `41 passed`。
- `EVIDENCE`：新增 async task API 真库测试已在 PostgreSQL 17 实际执行；RAG、compileall、Harness、
  governance、Secret/SDK 与 migration head 门也通过，CI 无 Key/Riot/Provider I/O。
- `CLOSED`：6A-5 正式完成；证据覆盖 POST 202、owner-scoped task/run/report、ActorContext、lifespan 与
  live/ready，不外推为 Worker packaging、正式 Auth、Session/Memory、SSE、前端或公网部署完成。
- `HANDOFF`：canonical 唯一下一检查点为 `6A-6-security-lifecycle-nfr` 准备状态，等待用户明确继续；
  不自动实现 CORS/log/Secret、retention/delete、metrics 或 benchmark。

### 2026-08-18：RQ-058 恢复 6A-6 Security/Lifecycle/NFR

- `RESUMED`：用户明确“继续下一步”，解除 6A-6 的等待确认；这是当前唯一获授权的执行变化，不改变
  阶段 0—8、6A-1 至 6A-7 顺序，也不提前进入 6A-7。
- `SCOPE`：只把既有设计中的 task 基座安全与运行边界落成代码/测试：默认关闭 CORS、日志/Secret
  脱敏、owner/global 背压、7/90/30 天 retention、terminal hidden-before-cleanup 与安全补偿、
  active delete conflict、allowlisted observability 和性能样本。
- `DEFERRED`：正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume、
  真实 Provider/Riot I/O 和 6A-7 packaging 均留在原定检查点；先红灯、再最小实现，真实 PostgreSQL
  并发/删除/性能由阻塞 exact-SHA CI 证明。

### 2026-08-18：6A-6 exact-SHA 公共闭环与 6A-7 交接

- `VERIFIED-PUBLIC`：实现 `fecbb11` 与性能证据修补 `31d5e60` 均已推送；Actions run
  `32138025724` 的 `pytest` 和 `postgres-migrations` completed/success。
- `EVIDENCE`：完整 pytest `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL `51 passed`。PostgreSQL 17/Python 3.11 中 8 样本 create/query p95 `6.220ms`，
  queued→claim p95 `23.359ms`，均低于冻结目标；该证据不外推为 SLA 或模型质量。
- `CLOSED`：6A-6/RQ-058 正式完成；CORS/log/Secret、capacity、retention/delete、补偿、observability
  与 task 控制面性能基线闭环。
- `HANDOFF`：canonical 唯一下一检查点为 `6A-7-packaging-exit-review` 准备状态，等待用户明确继续；
  不自动启动真实 Worker packaging 或实现正式 Auth/Session/Memory/SSE/前端/公网部署。

### 2026-08-18：RQ-059 恢复 6A-7 Packaging & Exit Review

- `RESUMED`：用户明确“继续吧”，解除 6A-7 等待确认；本轮仍只推进 canonical 的单一检查点。
- `SCOPE`：闭环可重建 API+Worker+PostgreSQL package、真实 Worker executable composition、配置与启动
  命令、Linux no-I/O smoke，以及把 ADR-0038/6A 设计逐项映射到实现/测试/公开证据/deferred 的 exit
  matrix/review。
- `FAIL-CLOSED`：真实 Worker 必须在 claim 前完成数据库、Riot、Provider 和产品组合校验；smoke/CI
  使用 Fake/no-I/O 路径，不读取 Key 或调用 Riot/Provider。
- `DEFERRED`：正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume、
  直接公网部署、LangGraph/Multi-Agent/MCP/新 SDK 均不在本批；exact-SHA CI 成功前不关闭 6A。

### 2026-08-18：6A-7 本地实现与退出门完成

- `LOCAL-VERIFIED`：Worker composition、非 root image、Compose、隔离 no-I/O smoke、CI 与 exit assets
  已实现；诊断修补后聚焦 `48 passed`，完整 `1102 passed, 27 skipped, 110 subtests passed`，RAG/Harness/compileall/
  safety 本地门通过。
- `REVIEW-FIX`：无效 worker_id 改为 Engine/网络前拒绝；smoke 改用独立 Compose project/data volumes，
  `up --wait api` 与 one-off `run --no-deps smoke` 分段，避免 migration 正常退出提前终止以及误领普通任务。
- `CURRENT`：6A/RQ-059 仍 in progress；最终本地门已通过，唯一下一动作是提交推送并等待 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。公共成功前不关闭或进入 Session/Memory。

### 2026-08-18：6A-7 首个公共 run 部分失败

- `PARTIAL-PUBLIC`：`b0f61ca` / Actions `32145005904` 的 pytest 与 postgres-migrations 成功；packaging
  已成功 config/build/migration/API ready，但 one-off smoke 以 `packaging_smoke_worker_failed` 失败。
- `DIAGNOSTIC-GAP`：该安全码过宽，不能区分 DB、claim、terminal CAS 或 query；不根据猜测改变业务链。
- `CURRENT`：只增加 body-free allowlisted stage code 与 bounded API/PostgreSQL tail logs，完成本地 TDD
  后提交新 SHA。6A 保持 in progress，正式 Auth/Session/Memory 等范围不变。

### 2026-08-18：第二个 Linux run 定位 import-root 漂移

- `DIAGNOSED`：`d8c5063` / Actions `32146113582` 的安全码为 `packaging_smoke_database_not_ready`；
  API logs 同时为 readiness 200/POST 202，真库 job 成功，排除 DB/migration 本身失败。
- `ROOT-CAUSE`：direct script 从 wheel 导入 app，Alembic PROJECT_ROOT 落在 site-packages；module entry
  从 `/opt/riftcoach` 源码导入。Worker command 具有同一隐患。
- `CURRENT`：只把两条 Compose command 改为 `python -m scripts...`，保持严格 Alembic readiness；新
  exact-SHA 三 job 全绿前 6A 继续 in progress。

### 2026-08-18：6A-7 与整个 6A 公共闭环

- `VERIFIED-PUBLIC`：`adf53e5` / Actions `32146760003` 的 pytest、postgres-migrations、
  packaging-smoke 三 job completed/success；公开 pytest 1102/27 skipped/110 subtests，真库 51 passed。
- `PACKAGE-EVIDENCE`：Linux smoke 输出 `external_riot_provider_calls=0`、task failed terminal；非 root 与
  `.env`/tests/cache/runs/reports/tmp image exclusion 全部通过。
- `CLOSED`：6A-7/RQ-059 与整个 6A 以 `close-with-deferred-boundaries` 完成；不外推 Session/Memory、
  Auth/HTTPS、lease/reclaim、SSE/前端、备份/SLA 或模型质量。
- `HANDOFF`：canonical 只切到 `stage-6-session-memory-entry-design` 准备状态，等待用户明确继续；不自动
  实现，也不提前进入阶段 7/8。

### 2026-08-19：RQ-060 授权 Session/Memory 入口设计

- `STATE-CLOSE-VERIFIED`：6A 状态收尾 `d1cc2ed` / Actions `32147545753` 的 pytest、
  postgres-migrations、packaging-smoke 三 job completed/success；这补齐状态提交自身的公开证据。
- `AUTHORIZED`：用户“继下一步”只授权 canonical 的 `stage-6-session-memory-entry-design`。
- `CURRENT`：先区分 task、Session、工作记忆、长期 Memory、原始事实与 RAG，审计现有
  owner/task/run/API 和 EchoMind/Saber，再比较方案并逐节冻结数据/写入/生命周期/隔离/NFR/测试设计。
- `BOUNDARY`：产品 Memory 代码、新存储依赖、正式 Auth/HTTPS、SSE/前端、MCP、Multi-Agent、
  cancel/resume/恢复和外部 Riot/Provider I/O 均未获本检查点授权。
- `DESIGN-CONFIRMED-1`：用户确认 Task/Session/工作上下文/长期 Memory/原始事实/RAG 六类职责与
  Candidate→write gate 主链。
- `DESIGN-CONFIRMED-2`：用户确认 PostgreSQL 是 Session/Memory V1 唯一真源；Redis/向量能力只作为
  真实 Bad Case 触发的可重建派生优化，不首日引入。

### 2026-08-19：RQ-061 校正外服账号认领与验证边界

- `CONSTRAINT`：当前 Riot 官方 LoL routing values 不含中国大陆国服；RiftCoach V1 只能处理官方 API
  可查询的外服账号。
- `IDENTITY-EVIDENCE`：Riot ID→PUUID 是公开账号解析，不是 owner 的账号归属证明；RSO `/accounts/me`
  可以提供登录 Riot 账号证据；升级 owner-player 关系还必须有正式产品 Auth、安全 callback 绑定和精确
  PUUID match，而当前项目没有这些能力。
- `CURRENT`：外服账号“属于我”只能作为未验证 `claimed_self`；不得显示 verified、不得解锁非公开数据，
  同一 PUUID 在不同 owner 下的私人 Memory 继续隔离。
- `AT-THE-TIME-PENDING`：当时是否并列支持 `public_observed` 及其允许的观察性历史能力仍留给 RQ-060
  身份节确认；下方 RQ-062 随后完成裁决。该临时状态没有触发代码、Auth/RSO 或阶段顺序变化。

### 2026-08-19：RQ-062 确认 MVP 外服玩家关系策略

- `CONFIRMED`：用户接受 MVP 同时提供未验证 `claimed_self` 与受限 `public_observed`；关系用途和验证
  证据拆为 `relationship_role` / `verification_status` 两个维度。
- `SELF-BOUNDARY`：claimed-self 可保存 owner-player 目标、计划与进度，但必须显式未验证，不增加 Riot
  API 权限。
- `OBSERVED-BOUNDARY`：public-observed 只允许公开比赛分析、owner-local 观察备注/趋势和第三人称语义，
  不生成被观察者本人的私人偏好或第一人称训练完成度。
- `FUTURE-ONLY`：verified-self 当前没有创建路径；未来必须经过正式产品 Auth、安全 RSO callback 与
  `/accounts/me` PUUID 精确匹配。任一关系都不允许跨 owner 合并私人 Memory。
- `NO-IMPLEMENTATION`：本确认不授权 schema/migration/Repository/API/Auth/RSO 代码。当前下一设计门是
  conversation 绑定、显式切换与 task 继承语义。

### 2026-08-19：RQ-063 确认 Conversation 固定玩家

- `CONFIRMED`：V1 conversation 创建时固定 trusted owner 的一个 player subject，生命周期不提供切换；
  不同 PUUID 新建 conversation，相同 PUUID 的 Riot ID 改名不算切换。
- `INHERITANCE`：消息、Context、review task/run 与 Memory Candidate 必须继承服务器保存的
  owner/conversation/subject；客户端、自由文本和模型都不能覆盖，未来由应用校验 + PostgreSQL
  owner-scoped composite constraints 双层保证。
- `AUDIT-GAP`：当前 task 在 HTTP 入队时只有 owner + Riot ID，完整 PUUID 由 Worker 内 Application 调用
  Riot API 后才得到；不能在入队点伪造已知 subject。
- `CURRENT`：下一步在同一 entry-design 内比较独立异步 link task、首个 review task bootstrap 和 API
  同步 lookup；未授权产品代码或外部调用。

### 2026-08-19：校正 v1.3 Amendment 的阶段 6/8 陈旧职责

- `RECONCILIATION`：旧 v1.3 增量文本曾把 cancel/resume/恢复、Runtime Compaction、SSE 和完整前端笼统
  留在阶段 6；较晚获用户逐节确认的 RQ-052/ADR-0038、主路线和 6A exit 已明确把这些高级运行时/产品化
  能力保留在阶段 8。
- `SYNC`：本次只让 amendment 与较晚已批准事实一致：阶段 6 V2 负责 Session/Memory、owner/conversation
  隔离和有界 Context；阶段 8 V3 负责 cancel/resume/checkpoint/recovery/compaction/SSE/完整前端。
- `IMPACT`：不新增、删除、重排或重命名任何主阶段，不改变 6A 已完成证据；只是移除陈旧文本对阶段 6
  exit criteria 的错误膨胀，并保留阶段 8 的既定验收责任。

### 2026-08-19：RQ-064 冻结 Session/Memory 总设计与有限自动实施范围

- `AUTHORIZED-SCOPE`：用户允许 Codex 选择剩余设计并在讲清后实施第一步、验证/推送后自动继续第二步；
  固化为 entry design→6B-1→6B-2 三个独立公共批次。6B-2 全绿后只准备 6B-3，不自动实施。
- `BOOTSTRAP-DECISION`：采用独立 PostgreSQL Player Link Task + 专用 Worker；Account-V1 在事务外执行，
  subject/alias/owner relationship/link terminal 在一个短事务收敛，成功后才可创建 Conversation。拒绝
  Review Task 内 bootstrap、API 同步 lookup 和 Riot ID provisional subject。
- `MEMORY-DECISION`：采用 PostgreSQL 单一真源、分类型关系表、有界严格 JSONB 叶子、统一 Candidate
  write gate 和 supersede/version chain；模型/自然语言提取不能直接写 active Memory。
- `LOCAL-ARTIFACTS`：ADR-0039、Session/Memory 正式设计和 6B-1 至 6B-9 实施计划已本地创建；
  `player_link_tasks` 明确私有持久化 bounded `game_name/tag_line`，hash 不能替代 Resolver 输入。
- `CURRENT`：设计内容已本地冻结但尚未提交/推送/exact-SHA CI，产品 migration/schema 尚未开始；先完成
  一致性、本地门禁与设计批公共闭环，再依有限授权进入 6B-1。

### 2026-08-19：Session/Memory entry design 公共闭环与 6B-1 交接

- `VERIFIED-PUBLIC`：设计提交 `bc11afe9f2f85a39f05b7f3d6135b14821ebb17d` 对应 Actions
  `32222531783`，workflow 总状态 success；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均成功，精确 SHA 与提交一致。
- `CLOSED`：entry design 正式关闭；它证明 ADR/design/plan/治理一致和现有产品无回归，不证明 Player
  identity 表、Repository、Worker、Conversation 或 Memory 已实现。
- `HANDOFF`：按 RQ-064 进入 `6B-1-player-identity-link-foundation`，先做 strict domain contracts、
  四表 0002 与事务 Repository；Resolver/Worker/API 留 6B-2，外部 Riot/Provider I/O 保持 0。

### 2026-08-19：RQ-065 将本轮停止点收紧到 6B-1

- `SCOPE-CORRECTION`：用户明确“完成 6B-1 就先截止，下一轮再继续”，取消 RQ-064 中本轮自动进入
  6B-2 的部分；6B-1 当前授权和全部既有架构/安全边界不变。
- `CURRENT`：本轮只允许完成 Player Identity/Link domain、四表 0002、事务 Repository、比例门禁、
  独立提交/推送与 exact-SHA 三 job；公共全绿后停止。
- `HANDOFF-AFTER-CLOSE`：6B-2 只能进入 prepared/waiting authorization，不得在本轮实现 Resolver、
  PlayerLinkWorker、HTTP API、真实 Riot I/O 或 package 接线。

### 2026-08-19：6B-1 首个公共 run 暴露 Alembic revision 长度缺口

- `PUBLIC-FAILED`：实现提交 `656117a` / Actions `32227457202` 总状态 failure；postgres-migrations 停在
  reversible migration，packaging-smoke 停在包含 migration 的 API stack，故 6B-1 保持 open。
- `ROOT-CAUSE`：0002 revision ID 长 35，超过 Alembic 默认 `alembic_version.version_num VARCHAR(32)`；
  无数据库红灯已复现 `35 <= 32` 失败。
- `REPAIR-LOCAL`：revision 缩短为 `0002_player_identity_link`，聚焦 16/13 skipped、完整
  1118/40 skipped/110 subtests 通过；下一动作是修补提交与新的 exact-SHA 三 job，而不是重跑旧 SHA。

### 2026-08-19：6B-1 第二个 run 暴露 CHECK naming-convention 二次格式化

- `PARTIAL-PUBLIC`：`b8fa2e3` / Actions `32227937252` 中 pytest、packaging-smoke 与 reversible migration
  成功；PostgreSQL test step 为 `66 passed, 1 failed`，6B-1 仍保持 open。
- `ROOT-CAUSE`：0002 的显式完整 CHECK 名未用 `op.f()`，含 `constraint_name` token 的 convention 再加一层
  table 前缀并截断为 hash 名；稳定 schema 名称断言正确阻止接受。
- `REPAIR-LOCAL`：新增 offline SQL 红灯并把 0002 全部 CHECK 名标记为已格式化；聚焦 17/13 skipped、
  完整 1119/40 skipped/110 subtests 通过。下一动作是全门与第三个 exact-SHA run。

### 2026-08-19：6B-1 exact-SHA 公共闭环与 RQ-065 停止

- `VERIFIED-PUBLIC`：最终提交 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 对应 Actions
  `32229024069` completed/success；pytest、postgres-migrations、packaging-smoke 三 job 全部成功。
- `CLOSED`：6B-1 Player Identity & Link Persistence Foundation 正式完成；本地完整为
  `1119 passed, 40 skipped, 1 warning, 110 subtests passed`，真库补齐 migration/constraint/Repository/
  concurrency 证据，本批外部 Riot/Provider/Key I/O 为 0。
- `BOUNDARY`：未实现 Resolver、PlayerLinkWorker/CLI、HTTP API、Conversation/Memory、Auth/RSO、SSE/
  前端或真实 Riot 调用；不得从 identity foundation 外推这些能力。
- `HANDOFF`：按 RQ-065 停止，canonical 只把 `6B-2-async-player-link-worker-api` 标为
  prepared/waiting authorization，下一轮用户明确继续前不得实施。

### 2026-08-19：RQ-066 恢复 6B-2

- `RESUMED`：用户在 6B-1 独立公共闭环后的新一轮明确“继续开工”，只授权
  `6B-2-async-player-link-worker-api`；RQ-065 的暂停门已履行，不再阻塞本批。
- `SCOPE`：实现窄 Account Resolver、PlayerLinkWorker、owner-scoped POST/GET Link API、API/Worker
  composition/CLI 与 Fake Resolver Linux no-I/O smoke；不实现 6B-3 Conversation/Memory。
- `BOUNDARY`：API 无 Riot 依赖，Account-V1 在 claim commit 后、数据库事务外；开发/测试/CI 不读取
  真实 Key、不调用 Riot/Provider，也不引入 retry/reclaim、Auth/RSO、SSE/前端或新框架。
- `CURRENT`：先以 Task 1 红灯冻结 Resolver 严格响应和 allowlisted failure mapping；6B-2 exact-SHA
  三 job 全绿前不关闭，闭环后只准备 6B-3 并停止。

### 2026-08-19：6B-2 Tasks 1–4 本地完成，公共验证待执行

- `LOCAL-CLOSED-TASKS`：窄 Account Resolver、专用 PlayerLinkWorker、owner-scoped POST/GET Link API、
  composition/CLI 与 Fake Resolver Linux smoke 均已实现；本地聚焦/相邻为 `149 passed, 2 skipped`，
  完整为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`。
- `BOUNDARY-REPAIR`：routing policy 要求完整覆盖 API 的四个官方 regional values；smoke 使用固定安全
  Link worker ID；Link Worker 自带最小 StopSignal Protocol。三项修补均有红灯/绿灯证据，不改变产品范围。
- `PUBLIC-PENDING`：RAG、Harness、compileall、YAML、治理、SDK/Secret/run-data 与 diff 门已通过；本机无
  PostgreSQL/Docker，真实 migration、API PostgreSQL 集成和 Linux package smoke 必须由同一 exact-SHA CI
  补齐。6B-2 仍为 `in_progress`，Task 5 是提交/推送/等待三 job，不能提前关闭或实施 6B-3。

### 2026-08-20：6B-2 exact-SHA 公共闭环与 6B-3 交接

- `VERIFIED-PUBLIC`：`0c13a583ea51a7c18301fc29bf5c2931790d6693` / Actions `32301852042`
  completed/success；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。
- `EVIDENCE`：公共 pytest `1216 passed, 42 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
  `70 passed, 1 warning` 且 migration/metadata head 一致；Linux smoke 输出 Review Task `failed`、Player
  Link `succeeded`、`external_riot_provider_calls=0`，随后非 root/image exclusion 通过。
- `CLOSED`：6B-2/RQ-066 正式完成；Resolver/Worker/API/composition/CLI/no-I/O package 已闭环。该证据不
  外推真实 Riot、账号所有权、Conversation/Memory、Auth/RSO、retry/reclaim、SSE/前端或 Provider 质量。
- `HANDOFF`：canonical 只切到 `6B-3-conversation-message-foundation` prepared/waiting authorization；
  本轮停止，不创建 Conversation、Message 或 Memory 代码。

### 2026-08-20：RQ-067 历史教学/工程证据补齐门

- `AUDIT`：重新按统一八维标准审计阶段 0 至 6B-2 后确认，最早真实持久说明缺口在阶段 0，而不是
  6B；阶段 1、4、5A、5B、6B-1、6B-2 也分别存在领域 walkthrough、实现后复盘、代码地图、证据矩阵、
  运行示例或面试边界缺口。阶段 2、5C、5D、5E、5P、5F、6A 与 Session/Memory entry design 由成熟
  设计/实施/退出材料组合覆盖。
- `BACKFILL-DESIGN`：采用覆盖矩阵驱动的混合方案，建立 `docs/learning/README.md` 与带严格递增
  sequence 的 `docs/learning/coverage.yaml`；成熟材料复用，真实缺口才新增文档，不按文件数制造重复。
- `GOVERNANCE`：治理脚本和红灯测试现在检查当前 checkpoint、前序 complete、八个证据维度、仓库内
  Markdown 路径、唯一递增 sequence 与 planned/complete 状态，防止以后再次只靠聊天记忆推进。
- `CONDITIONAL-AUTH`：RQ-067 仍不改变阶段 0—8 或 6B-1 至 6B-9 顺序；6B-3 已获条件授权，但在本批
  独立提交、推送和 exact-SHA 公共 CI 全绿前不得创建 Conversation/Message/Memory 产品代码。公共闭环
  后无需再次确认，直接进入 6B-3 初学者设计复核与 TDD。

### 2026-08-20：RQ-067 公共闭环并进入 6B-3

- `VERIFIED-PUBLIC`：文档/工程证据提交 `63435d90f5153309fce98b92a2ff58425d54a684` 对应 Actions
  `32308631289`；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- `CLOSED`：RQ-067 文档前置门正式关闭。公共 run 验证了治理、完整回归、真实 PostgreSQL migration/
  metadata 与 Linux package 边界；不把它外推为模型质量、正式部署或 6B-3 功能完成。
- `HANDOFF`：canonical 正式进入 `6B-3-conversation-message-foundation` 的初学者设计复核与 TDD；
  下一批先冻结 Conversation/Message 合同和红灯测试，仍不接 Agent、Review Task、Memory、Auth/RSO、
  SSE、前端或新框架。

### 2026-08-20：6B-3 设计审计与治理顺序加固

- `DESIGN-AUDIT`：复核现有 ORM/Repository/API/lifespan 后确认不需要引入 EchoMind、Saber、LangGraph、
  Redis、向量库或新 SDK；可沿用 PostgreSQL 唯一真源与短事务边界。
- `ADR-0040`：冻结 active relationship 行锁检查、owner-scoped Conversation 幂等、公共 user-only
  Message、1-based row-lock sequence、archived/hidden 生命周期、source 引用弱绑定和 immutable trigger。
- `GOVERNANCE-HARDENING`：coverage 顺序不再只依赖 YAML 列表和 sequence；固定 canonical group ID order，
  增加重排并重编号负例，防止学习证据门被静默绕过。
- `HANDOFF`：当前仍处于 6B-3 红灯合同，设计文档不等于实现；下一动作是 pure model/Service/API TDD，
  随后才进入真实 PostgreSQL migration/Repository/并发验证。

### 2026-08-20：6B-3 设计批 exact-SHA 公共闭环

- `VERIFIED-PUBLIC`：设计/治理提交 `b6a7112d9c3fa8744b9713737bbbf54fe5011084` 对应 Actions
  `32313707301`；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部成功。
- `BOUNDARY`：该 run 验证设计、治理、既有真库和 package 回归，不把 Conversation/Message、Agent、
  Review Task 或 Memory 写成已实现。
- `HANDOFF`：同一 canonical checkpoint 内进入 pure model/Service/API 红灯，再实现 PostgreSQL 和 API。
### 2026-08-20：6B-3 本地实现收尾，等待公共门

6B-3 已从设计/红灯阶段进入本地实现完成状态：Conversation/Message domain、Service、0003
migration、Repository、六个 HTTP endpoint、composition/package 纵向与分层测试已建立；walkthrough
覆盖八类学习/工程证据。实现批的聚焦为 `85 passed, 25 skipped`，完整回归为
`1295 passed, 67 skipped, 1 warning, 110 subtests passed`，RAG、Harness、compile、secret、YAML、
治理和 diff 门通过。由于本机无 Docker/PostgreSQL，真实 migration/trigger/事务/并发/package 仍必须由
实现提交的 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 公共 job 证明；全绿前不关闭
6B-3、不修改 coverage 为 complete、不进入 6B-4。

### 2026-08-20：6B-3 实现 exact-SHA 公共闭环与 6B-4 交接

- `PUBLIC-CI`：实现修复提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081` 对应 Actions run `32329686381`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部成功。首个实现 SHA `0ca7fde` 的
  PostgreSQL fixture FK 顺序失败已保留，修复只增加父行显式 flush，不改变生产约束或事务语义。
- `EVIDENCE`：公共 PostgreSQL 运行 `100 passed, 1 warning`；公开 pytest、migration upgrade/downgrade、
  `alembic check`、Linux package smoke 和边界门均通过。本机无 Docker 的 skip 仍未被改写为本地真库证据。
- `CLOSED`：6B-3 Conversation/Message foundation 正式关闭，`coverage.yaml` 与学习索引升级为完整/公共闭环。
- `HANDOFF`：唯一下一检查点为 `6B-4-conversation-bound-recent-review-identity`，当前仅
  prepared/waiting authorization；不实现 6B-4，不把 Agent、Review Task、Memory、Auth/RSO、SSE、前端或
  新框架写成已完成。

### 2026-08-20：RQ-068 恢复 6B-4 Conversation-bound Review Identity

- `AUTHORIZED`：用户明确“继续 6B-4”，只授权
  `6B-4-conversation-bound-recent-review-identity`；6B-5 未获授权。
- `DECISION`：复用既有 `review_tasks`，增加 nullable schema 2.0 identity columns；创建时在单一短事务
  锁定 active Conversation，由服务器派生 owner/conversation/relationship/subject tuple。拒绝只把身份藏在
  JSON，也拒绝复制第二套 task/Worker/terminal 基础设施。
- `COMPATIBILITY`：legacy schema 1.0 新列保持 null，旧 endpoint/query/execution 继续兼容但不创建
  Conversation/Memory；不根据可变 Riot ID 回填历史 subject。
- `EXECUTION`：v2 使用 trusted PUUID Summary path，不再调用 Account-V1；alias rename 不改变 subject，
  late task 只绑定创建时 Conversation。测试/CI 使用 Fake Riot/Provider，外部 calls 为 0。
- `BOUNDARY`：assistant Message、Memory Candidate/长期 Memory、正式 Auth/RSO、SSE、前端、LangGraph、
  Multi-Agent 与新 SDK 均不在 6B-4。

### 2026-08-20：6B-4 本地实现完成，等待 exact-SHA 公共门

- `IMPLEMENTED-LOCAL`：schema 2.0 contract/fingerprint、0004/ORM、单事务 Conversation binding、私有
  PUUID target、trusted-PUUID Summary/Application、1.0/2.0 Executor、Conversation-bound API/composition
  与 no-I/O package smoke 已建立；没有复制 Worker/Runtime/Harness。
- `EVIDENCE-LOCAL`：聚焦 `114 passed, 11 skipped, 1 warning`；完整
  `1333 passed, 78 skipped, 1 warning, 110 subtests passed`。两套 RAG、Harness dry-run、compileall、
  SDK/tracked-data、YAML、pip、governance 与 diff 门通过。
- `LIMIT`：本机无 PostgreSQL/Docker，78 个 skip 不证明复合 FK、trigger、事务锁或 Linux image；两个新
  真库文件已加入阻塞 job，package 已覆盖 v2 Task 经同一 Worker 到 safe failed terminal，外部调用为 0。
- `PENDING`：walkthrough/八维 evidence 已登记但 coverage 保持 planned；只待 cached diff、提交、推送与
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`。全绿前不关闭 6B-4、不进入 6B-5。

### 2026-08-20：6B-4 exact-SHA 公共闭环与 6B-5 交接

- `PUBLIC-CI`：实现提交 `d63f9085f66e49557b4674d0698495dcb7335c82` 对应 Actions run
  `32347834279`；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- `EVIDENCE`：公开完整回归为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL 为 `113 passed, 1 warning`，0004 upgrade/downgrade、完整迁移链、`alembic check` 和 Linux
  package smoke 通过。package 中 v2 Review 安全失败，`external_riot_provider_calls=0`。
- `CLOSED`：6B-4 Conversation-bound Review Identity 与八维 coverage 正式关闭；本地无
  PostgreSQL/Docker 的 skip 仍保持原义，不冒充本地真库成功。
- `HANDOFF`：唯一下一检查点为 `6B-5-memory-candidate-write-gate`，仅 prepared/waiting authorization；
  不创建 Candidate/Memory/assistant terminal 代码，不进入 Auth/RSO、SSE、前端或新框架。

### 2026-08-20：RQ-069 授权 6B-5 并冻结 materialization 方向

- `AUTHORIZED`：用户明确“继续 6B-5”；只授权 `6B-5-memory-candidate-write-gate`，不进入 6B-6。
- `PROBLEM`：6B-5 尚无具体长期 Memory 表，不能把 Candidate accepted 或 receipt 冒充真实物化。
- `DECISION`：ADR-0042 采用事务内 typed materializer；同一 Session 写 target 后才更新 Candidate terminal。
  生产 composition 在 6B-6 注册真实 materializer 前为空 registry/fail closed。
- `BOUNDARY`：本批实现 Candidate/gate/migration/Repository/API/真库与 package 证据；不创建具体长期
  Memory、assistant terminal、Context、Auth/RSO、SSE、前端、LangGraph、Multi-Agent 或新 SDK，不调用
  Riot/Provider，不读取 Key。

### 2026-08-20：6B-5 首次公共 teardown 失败与最小修复

- `FAILED-EVIDENCE`：实现 `7156cb5` / Actions `32372854457` 的 `pytest` 与 `packaging-smoke` 成功；
  PostgreSQL 三个 materializer 测试的业务断言完成后，测试专用 `test_memory_targets` 仍引用
  `memory_candidates`，导致 fixture 的 Alembic downgrade 在 teardown 失败。
- `FIX`：`dd7c9c8` 只在共享真库 fixture 中先 `DROP TABLE IF EXISTS test_memory_targets`，再 dispose/downgrade；
  没有修改生产 migration、使用 `CASCADE`、放宽 FK 或改变 Candidate/materializer 语义。
- `PUBLIC-CI`：Actions `32376405150` 精确对应修复 SHA，三个 job 均 completed/success；普通回归
  `1358 passed, 88 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL `126 passed, 1 warning`，
  metadata head 无漂移，Linux package Candidate rejected 且外部调用为 0。
- `CLOSED`：6B-5 与八维 coverage 正式完成；测试 target 仍不是生产 Memory。
- `HANDOFF`：唯一下一检查点为 `6B-6-preferences-profile-review-memory`，仅 prepared/waiting authorization；
  不自动实施具体长期 Memory 或任何更后能力。

### 2026-08-20：RQ-070 授权 6B-6 并冻结 typed target 设计

- `AUTHORIZED`：用户最新“那继续”只恢复 canonical 的
  `6B-6-preferences-profile-review-memory`；不自动进入 6B-7。
- `ADR-0043`：选择三张 typed target 表而非万能 JSONB Memory 表；Preference owner-global，Profile
  self-only，Review Memory self/observed 受限。
- `VERSIONING`：Candidate payload 使用严格 `value + expected_version` envelope；新版本 supersede 旧
  active，Review append 在 V1 中保留历史但同 key 只有一个 active 最新版本。
- `TRANSACTION`：真实 materializer 继续复用 6B-5 同一 Session；PostgreSQL advisory lock、active row lock、
  partial unique 与 source candidate UNIQUE 共同证明冲突/幂等边界。
- `BOUNDARY`：设计批尚未创建 migration/model/Repository/API；Training Plan/Progress、Memory Context、
  assistant terminal、Auth/RSO、SSE、前端、Redis/Chroma/向量库、LangGraph、Multi-Agent、新 SDK 与真实
  Riot/Provider 调用继续 deferred。

### 2026-08-20：6B-6 设计批 exact-SHA 公共闭环

- `PUBLIC-CI`：设计提交 `e44d48f0531f0ee1786cba9b38c8fc8b2589af00` 对应 Actions `32381553145`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部成功。
- `EVIDENCE`：公共 run 验证 ADR/计划/治理与既有 PostgreSQL/package 基线兼容；它不把设计稿写成已存在的
  Preference/Profile/Review Memory，也不改变本机无 PostgreSQL/Docker 的 skip 含义。
- `HANDOFF`：设计批关闭，继续同一 6B-6 的 Task 1 pure typed payload/version contract；不进入 6B-7。

### 2026-08-20：6B-6 本地实现完成，等待公共验证

- `IMPLEMENTED-LOCAL`：strict envelope/key/role policy、三个 materializer、三张 ORM 表/0006、advisory
  lock/expected-version writer、production registry、owner-scoped active/history GET 与 package smoke 1.3 已建立。
- `TRANSACTION`：target supersede/insert 与 Candidate accepted 继续由 6B-5 同一事务管理；payload/version
  冲突保持 Candidate pending，未知 SQL 回滚并安全映射。
- `EVIDENCE-LOCAL`：当前比例回归 `128 passed, 19 skipped, 1 warning`；walkthrough 与八维路径已建立，
  coverage 仍 planned。19 skip 来自无 PostgreSQL/Docker，不是通过证据。
- `PENDING-PUBLIC`：完整门禁后提交实现 SHA，等待 `pytest`、`postgres-migrations`、`packaging-smoke`；
  全绿前不关闭 6B-6、不进入 6B-7，也不宣称正式 Auth/RSO、Plan/Progress、Context 或 lifecycle 已实现。

### 2026-08-20：6B-6 提交前复核与最终本地门禁

- `REVIEW-FIX`：发现 typed payload/version 异常 disposition 被误置于 Candidate create 异常块；已最小移入
  `accept_candidate()`，恢复 422 payload invalid、409 version conflict 与 Candidate pending/rollback 语义。
- `EVIDENCE-HARDENING`：为 Review Summary metrics、100 条 page 上限、terminal Candidate source 和跳号
  supersedes chain 增加直接合同；后两项本机因无 PostgreSQL 明确 skip，仍只由公共真库 job 补证。
- `VERIFIED-LOCAL`：最终完整回归 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；两套 RAG、
  Harness dry-run、compileall、YAML、governance、SDK/Secret/tracked-data 与 diff 门通过。
- `CURRENT`：6B-6 保持 in progress/coverage planned；下一动作只有实现提交、推送和 exact-SHA 三 job，
  公共全绿前不进入 6B-7。

### 2026-08-20：6B-6 首个实现公共门保留测试夹具失败

- `FAILED-EVIDENCE`：`da87cde` / Actions `32386630063` 的 pytest 与 packaging-smoke 成功；PostgreSQL
  为 `141 passed, 1 failed`。
- `ROOT-CAUSE`：observed `public_trend` 测试夹具沿用 `user_structured_input`，违反 6B-5 已冻结的 Gate；
  Repository 正确返回 `SOURCE_INVALID`，不是 migration/materializer/事务放宽或失效。
- `MINIMAL-FIX`：只把该案例来源改为 `deterministic_run_fact`，保留生产 Gate 与失败 SHA；新 exact-SHA
  三 job 全绿前 6B-6 继续 open、coverage 继续 planned。

### 2026-08-20：6B-6 exact-SHA 公共闭环与 6B-7 交接

- `PUBLIC-CI`：最小测试修复 `5531c81ec7117f5c454d320e406153086baae3ea` 对应 Actions
  `32387026797`；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- `EVIDENCE`：公共 pytest `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
  `142 passed, 1 warning`，0006 可逆迁移、trigger/index/FK、版本并发、事务回滚与 metadata-head 通过；
  Linux package 为 Candidate accepted→Preference v1 query，外部调用 0。
- `CLOSED`：6B-6 与八维 coverage 正式关闭；失败 `da87cde/32386630063` 继续保留，不改写为成功。
- `HANDOFF`：唯一下一检查点为 `6B-7-training-plan-progress` prepared/waiting authorization；没有实施
  Plan/Progress、6B-8/6B-9 或其他 deferred 能力。

### 2026-08-21：RQ-071 授权 6B-7→6B-8→6B-9，进入 6B-7 设计门

- `AUTHORIZATION`：用户明确要求本轮连续完成三个 canonical checkpoint，不再逐步等待批准；顺序门、
  TDD、八维证据、独立提交和 exact-SHA 公共 CI 仍逐项成立。
- `DESIGN`：ADR-0044 与专用 design/implementation plan 冻结 Candidate-backed self-only Plan、每关系一个
  active Plan、完整 final Artifact 支撑的 Progress、追加式纠错与非因果确定性趋势。
- `BOUNDARY`：当前仍没有 6B-7 产品 schema/Repository/API/tests；设计批公共闭环前不写实现，6B-7 正式
  公共闭环前不进入 6B-8，6B-8 闭环前不进入 6B-9。

### 2026-08-21：6B-7 设计 exact-SHA 公共闭环

- `PUBLIC-CI`：`d678a7a93e7b5f04d5733b9c0abae4a26dc4dd1b` / Actions `32394585411` 的
  pytest、PostgreSQL migration/control-plane 与 Linux package 三 job 全绿。
- `HANDOFF`：仍在 6B-7 内进入 pure model/trend 红灯；设计绿灯不计作产品实现，不进入 6B-8。

### 2026-08-21：6B-7 本地实现完成，等待公共验证

- `IMPLEMENTED`：pure contract/materializer/registry、0007、Plan/Progress writer、final Artifact gate、
  query/trend、两个 GET、lifespan 与 package Plan 纵向均已本地建立。
- `LOCAL-EVIDENCE`：聚焦 `103 passed, 6 skipped`；完整 `1445 passed, 106 skipped, 1 warning,
  110 subtests passed`，两套 RAG/Harness/compile/security/governance/diff 全绿。
- `BOUNDARY`：106 skip 仍表示本机无 PostgreSQL/Docker；公共三 job 全绿前 6B-7/coverage 不关闭，
  不进入 6B-8。

### 2026-08-21：6B-7 exact-SHA 公共闭环与 6B-8 设计冻结

- `PUBLIC-CI`：`f6d89225ac5dbd568b6fad7c3c09b7c497c50762` / Actions `32397290175` 的
  pytest、PostgreSQL migration/control-plane 与 Linux package 三 job 全绿；公共 pytest 1445 passed，
  真库 151 passed，package schema 1.4 且外部调用 0。
- `CLOSED`：6B-7 与八维 coverage 正式关闭；Plan/Progress 的 public exact-SHA 证据不外推为 Context 或
  lifecycle 已完成。
- `DESIGN`：RQ-071 自动交接 6B-8。ADR-0045 选择 run-scoped Context decorator、owner-scoped legal
  selector、body-free manifest 与 terminal-only Assistant writer；不修改 Prompt Program output schema，
  不从 report 文本猜 Candidate。
- `BOUNDARY`：当前只有 6B-8 ADR/design/implementation plan，没有产品 migration/selector/Runtime/turn
  writer；设计批 exact-SHA 公共闭环前不写实现，6B-8 正式闭环前不进入 6B-9。

### 2026-08-21：6B-9 exact-SHA 公共闭环、阶段 6 关闭与阶段 7 交接

- `6B-8-BASE`：6B-8 最终 evidence 提交 `aacc11a1993e9d7d660f9d8d15b761dc641954b1` /
  Actions `32403187972` 三 job全绿；公共 pytest `1465 passed, 112 skipped`、真库 `157 passed`，
  package schema 1.5 输出三类 Context、terminal Assistant 0、外部调用 0，随后才进入 6B-9。
- `DESIGN-PUBLIC`：`4bdb1bb9e720bd853c677ce2f650476f19ab6e41` / Actions `32404203265`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，只关闭设计门。
- `FAILED-EVIDENCE`：实现 `2e37bd4e156d750634d67d64c07ddb4784f048f4` / Actions `32407862496`
  的普通/package job 成功，真库为 `163 passed, 1 failed`；唯一失败是测试非法 unhide Conversation，
  PostgreSQL 正确拒绝 `conversation_lifecycle_irreversible`，未放宽产品合同。
- `PUBLIC-CI`：最小测试修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` / Actions
  `32408101770` 三 job completed/success。公共 pytest `1490 passed, 116 skipped, 1 warning,
  110 subtests passed`；真实 PostgreSQL `164 passed, 1 warning`，0009 可逆且 metadata=head；Linux
  package schema 1.6 成功断言 export→conversation-only delete、Preference/Plan 存续和外部调用 0。
- `CLOSED`：6B-9、coverage、Session/Memory V1 与阶段 6 正式关闭；本地 `1489 passed/117 skipped`
  与公共 `1490/116` 分开记录，不把本机无 PostgreSQL/Docker 的 skip 冒充成功。
- `HANDOFF`：唯一下一检查点为 `stage-7-standard-mcp-dynamic-meta-entry-design`，仅 prepared/waiting
  authorization。RQ-071 不授权阶段 7；不开始 MCP/Meta 设计、实现或真实互操作。

### 2026-08-21：RQ-072 授权 Stage 7 入口设计

- `AUTHORIZED`：用户明确“那开始 stage7”，恢复 canonical 的
  `stage-7-standard-mcp-dynamic-meta-entry-design`；本轮只做入口设计，不把授权外推为产品实现或真实 I/O。
- `AUDIT`：现有 `ToolDefinition`/`ToolRuntime` 是内部可靠工具执行层，缺少标准 MCP initialize、capability、
  tools/list、tools/call、session/transport；Application/Context/Harness 接缝支持 Adapter-first 组合。
- `DECISION`：ADR-0047 选择 MCP Protocol Adapter → existing ToolRuntime，动态 Meta 经 Meta Adapter 规范化为
  source/patch/digest/freshness/data-only `MetaEvidence`；对外 Server 只经 owner-scoped Application Facade。
- `OPGG-GATE`：OP.GG 仅为首选候选，尚未证实标准 Server/endpoint、protocol/version、transport、schema、许可、
  freshness、限流或真实互操作；不满足合同时必须另立 ADR，不能把普通 HTTP POST 称为 MCP或静默替换来源。
- `SEQUENCE`：后续固定为 `7-1-mcp-client-contract` → `7-2-mcp-transport-and-discovery` →
  `7-3-opgg-meta-adapter` → `7-4-riftcoach-mcp-server` → `7-5-mcp-interoperability-exit-review`。
- `BOUNDARY`：入口设计阶段不安装 SDK、不实现 MCP Client/Server、不读取 Key、不调用 OP.GG/Riot/Provider；
  当前 coverage 仍 planned，待设计 exact-SHA 公共闭环后才进入 pure TDD。

### 2026-08-21：Stage 7 入口设计 exact-SHA 公共闭环与 7-1 交接

- `PUBLIC-CI`：设计提交 `e50a54618157c84a545ad5786e6c820502f967ee` / Actions `32436092074` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `CLOSED`：ADR-0047、entry design、implementation plan、学习材料与八维 coverage 正式关闭；公共证据
  不外推 MCP 产品代码、OP.GG 准入或真实外部互操作。
- `HANDOFF`：新增治理顺序 `7-1-mcp-client-contract`，canonical 标为 prepared/waiting authorization；
  未获下一授权前不写 pure contract、transport、Meta Adapter 或 RiftCoach Server。

### 2026-08-21：RQ-073 授权 7-1 MCP Client pure contract

- `AUTHORIZED`：用户明确“继续下一步”，只授权 canonical 的 `7-1-mcp-client-contract`；7-2 及以后未授权。
- `CONTROL-FLOW`：本批冻结 `initialize → tools capability → tools/list snapshot → allowlisted tools/call`；
  envelope/model 与 transport/session 分开，7-1 不实现 stdio、HTTP、断线或外部发现。
- `TDD-BOUNDARY`：先覆盖 protocol version allowlist、严格 JSON-RPC/额外字段、唯一有界 tool catalog、
  Draft 2020-12 arguments/result schema、schema drift、malformed/oversized result 和 body-free remote error。
- `NO-IO`：不安装 SDK、不读取 Key、不调用 OP.GG/Riot/Provider、不创建 MetaEvidence 或 RiftCoach MCP Server；
  pure/fixture 证据不能称为真实互操作，7-1 exact-SHA 公共闭环前不交接 7-2。

### 2026-08-21：7-1 本地实现与门禁完成

- `IMPLEMENTED-LOCAL`：strict initialize/version/capability、bounded immutable catalog/schema digest、
  discovered+allowlisted call、argument/output validation、catalog/schema drift 与 body-free remote error 已建立。
- `EVIDENCE-LOCAL`：聚焦 `20 passed/17 subtests`，相邻 `55/62 subtests`，完整
  `1509 passed, 117 skipped, 1 warning, 127 subtests passed`；RAG/Harness/compile/pip/YAML/governance/security/diff 全绿。
- `BOUNDARY`：实现仍 pure no-I/O；没有 SDK、transport、OP.GG/Meta、RiftCoach MCP Server、Key 或真实互操作。
- `PENDING`：walkthrough 已覆盖八维但 coverage 继续 planned；只待独立提交/推送与 exact-SHA 三 job，
  公共全绿前不关闭 7-1、不登记 7-2 为当前 checkpoint。

### 2026-08-21：7-1 exact-SHA 公共闭环与 7-2 停止点

- `PUBLIC-CI`：`37f16bc54de1d6e41c3ae65ddc9d9c5e11efa4cb` / Actions `32439753589` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `EVIDENCE`：公共 pytest `1510 passed/116 skipped/127 subtests`，真库 `164 passed`、migration metadata=head；
  Linux package schema 1.6 且 `external_riot_provider_calls=0`。本地 1509/117 与公共 1510/116 分开记录。
- `CLOSED`：7-1 与八维 coverage 正式关闭；只证明 pure protocol contracts，不证明 transport/OP.GG/Server。
- `HANDOFF`：唯一下一检查点为 `7-2-mcp-transport-and-discovery` prepared/waiting authorization；当前停止。

### 2026-08-21：RQ-074 授权 7-2 transport/discovery

- `AUTHORIZED`：用户明确“继续7-2”，恢复 canonical 的 `7-2-mcp-transport-and-discovery`；等待原因清除。
- `SCOPE`：先以 fixture/in-memory 和隔离 stdio/subprocess 证明 initialize/tools/list/tools/call 的
  transport/session/deadline/disconnect/restart/capability 合同，并将 descriptor 适配为既有 ToolDefinition，
  执行交给 ToolRuntime；不复制 retry/cache/breaker/fallback。
- `NO-IO`：不安装 MCP SDK、不接 OP.GG/Riot/Provider、不读 Key、不实现 MetaEvidence、RiftCoach MCP Server，
  不实现普通 HTTP/Streamable HTTP，也不把 fixture/subprocess 视为真实外部互操作。

### 2026-08-21：7-2 exact-SHA 公共闭环与 7-3 交接

- `PUBLIC-CI`：实现 `f12166665d437a9479afff508709435a23096dd2` / Actions `32441793585` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `CLOSED`：7-2 coverage 与八维 walkthrough 正式 complete；证据只证明本地 in-memory/隔离 stdio
  transport/session/discovery，不证明 OP.GG、MetaEvidence、RiftCoach Server 或真实互操作。
- `HANDOFF`：唯一下一检查点为 `7-3-opgg-meta-adapter` prepared/waiting authorization；授权前不做
  OP.GG 准入、MetaEvidence、Key 读取、普通 HTTP 或外部调用。

### 2026-08-21：RQ-075/076/077 与 7-3 本地真实接入

- `ADMISSION`：官方 endpoint 已真实完成标准 MCP handshake/list/call；缺 outputSchema/patch/source time/TTL
  被 ADR-0048 解释为 partial provenance 限制，不再被错误解释成整体拒绝。
- `BAD-CASE`：首个产品 smoke 发现当前 30-tool 目录的两个未获准 Valorant 数组 outputSchema 会阻断获准
  LoL 工具；修复为完整 response 总量门后只严格解析 admitted subset，未获准工具仍不可注册/调用。
- `IMPLEMENTED-LOCAL`：Streamable HTTP/session、远端→本地 ToolDefinition、ToolRuntime、allowlisted AST、
  typed/digested/expiring MetaEvidence 与 optional data-only Context 已建立；真实 body-free smoke 成功。
- `RIOT-BOUNDARY`：RQ-077 固定 Riot 官方账号/排位/比赛、Data Dragon 版本静态数据和 patch/update 与
  OP.GG 聚合 Meta 分层；7-3 不实现两源 join，缺 patch 的 OP.GG 不冒充精确版本。
- `PENDING`：7-3 coverage 仍 planned；完整本地门、独立提交与实现 SHA 的 exact-SHA 三 job 前不关闭，
  不进入 7-4 Server 或 7-5 双向互操作。

### 2026-08-21：RQ-078 授权 7-4 RiftCoach MCP Server

- `AUTHORIZED`：用户在 7-3 exact-SHA 公共闭环后明确继续完整开发，恢复唯一 canonical 检查点
  `7-4-riftcoach-mcp-server`。
- `SCOPE`：Server 采用 strict protocol/session → owner-scoped Application Facade；工具目录固定为
  近期汇总、单局分析、知识搜索、报告评测四个只读入口，owner 身份由可信 ActorContext 注入。
- `DENY`：不接受 owner_id/PUUID/Key/Prompt/Provider body，不暴露 Repository、文件、SQL、任意 URL、
  未发布 Artifact 或 Memory 写入；公网 transport、真实外部 Client 与 7-5 双向互操作仍未进入。
- `NEXT`：先以 external-client fixture 写 Server envelope/session、工具 schema、owner scope、错误和
  bounded DTO 红灯，再实现最小 Facade/Server 并完成本地与 exact-SHA 公共门。

### 2026-08-21：7-4 本地实现与全部门禁完成

- `IMPLEMENTED-LOCAL`：strict initialize/initialized/list/call、独立 Session、restart generation、固定四工具
  catalog、owner-scoped Query Facade 与 in-process external-client fixture 已完成。
- `BUSINESS-TRUTH`：近期汇总从 verified `PLAYER_SUMMARY` 投影，单局只公开发布 digest，知识搜索只公开
  attribution，评测不虚构 score；owner_id/PUUID/Key/Prompt/URL/SQL/path/open I/O 字段均拒绝。
- `VERIFIED-LOCAL`：聚焦 33、相邻 `109 passed, 17 subtests passed`、完整
  `1566 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG、Harness dry-run、compileall、pip、
  YAML、SDK/Secret/tracked-data、body-free evidence、governance 与 diff 门全绿。
- `PENDING`：coverage 保持 planned；唯一下一动作是独立提交/推送并等待该 exact SHA 的三 job。公共全绿前
  不关闭 7-4，不进入 7-5。

### 2026-08-21：7-4 exact-SHA 公共闭环与 7-5 交接

- `PUBLIC-CI`：实现 `431c584c6f07731233e6e32fd6f98505a661f910` / Actions `32480827952` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `EVIDENCE`：公共 pytest `1567 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`，0001→0009 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`。
- `CLOSED`：7-4 与八维 coverage 正式关闭；这些证据不证明公网 Server、正式 Auth/TLS/限流、
  Riot+OP.GG join 或真实外部 Client 双向互操作。
- `HANDOFF`：唯一下一检查点为 `7-5-mcp-interoperability-exit-review` prepared/waiting authorization；
  授权前停止。

### 2026-08-21：RQ-079 授权与 7-5 官方 Client 方案

- `AUTHORIZED`：用户明确“那继续7-5”，清除 pause；唯一 checkpoint 保持 7-5，不进入 Stage 8。
- `DECISION`：ADR-0050 选择 `@modelcontextprotocol/sdk@1.30.0`/MIT/固定 integrity 作为独立外部 Client，
  经标准 stdio 启动 Python RiftCoach Server；SDK/lockfile 隔离在 evaluation 目录，不进入产品 runtime。
- `REAL-BAD-CASE`：官方 SDK 首先提出 `2025-11-25`，7-4 Server 原先只接受请求值恰为 `2025-06-18`；
  红灯后改为冻结 proposal allowlist，响应/session 仍绑定 Server 实际实现的 `2025-06-18`。
- `IMPLEMENTED-LOCAL`：有界 stdio framing、no-I/O restricted runner、body-free trace/evidence validator 与
  clean-SHA 双向 runner 已建立；官方 SDK initialize/notification/list/一次 knowledge call 本地通过。
- `PENDING`：尚未提交实现、取得 exact-SHA CI 或执行本检查点的 clean-SHA OP.GG 真实门；coverage planned，
  Stage 7 未关闭。

### 2026-08-21：7-5 实现公共门与 clean-SHA 双向真实门通过

- `PUBLIC-CI`：实现 `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success；公共 pytest
  `1577 passed, 116 skipped, 1 warning, 127 subtests passed`，真库 `164 passed, 1 warning` 且
  metadata=head，Linux package schema 1.6/外部 Riot Provider 调用 0。
- `REAL-EXIT`：仅在 HEAD/工作树/origin 精确一致的上述 implementation SHA 上执行一次双向门；官方
  SDK→RiftCoach stdio 与 RiftCoach→OP.GG Streamable HTTP 均完成 initialize/notification/list/一次 call。
- `EVIDENCE`：`stage7_interoperability_exit_v1.json` 不可覆盖、body-free、绑定 product SHA；两侧目录、
  schema/result/trace 只保留 digest/count。OP.GG 仍为 partial provenance，patch/source time/freshness unknown；
  Riot/LLM/Key I/O 为 0。
- `PENDING-EXIT`：当前只提交 evidence、自动验证与退出材料；该 SHA 的三 job 和随后独立 state SHA 的三 job
  均全绿前，不关闭 7-5/coverage/Stage 7，也不进入 Stage 8 产品开发。

### 2026-08-21：7-5 evidence 公共闭环、Stage 7 关闭与 Stage 8 交接

- `EVIDENCE-PUBLIC`：不可覆盖 evidence `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions
  `32484257736` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真库
  `164 passed, 1 warning`，0001→0009 migration 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`。
- `CLOSED`：7-5 八维 coverage complete；实现、唯一一次 clean-SHA 双向真实门与 evidence 均有独立
  exact-SHA 证据，7-5 和 Stage 7 正式关闭。OP.GG partial provenance 与全部产品边界继续保留。
- `ORDER-CONTRACT`：原治理顺序止于 7-5；按固定 Stage 8 路线标题和既有 entry-design 命名规则，显式新增
  `stage-8-multi-agent-reliable-runtime-productization-entry-design` 到治理常量与 coverage ledger。
- `HANDOFF`：Stage 8 checkpoint 仅 prepared/waiting authorization；RQ-079 不授权 Stage 8，不开始
  8-Core/8-Advanced 教学、设计、Multi-Agent/DAG、恢复、SSE/前端或部署实现。

### 2026-08-22：RQ-080 授权并完成 Stage 8 entry design 本地收尾

- `AUTHORIZED`：用户明确“那开始吧”，授权唯一 canonical 检查点
  `stage-8-multi-agent-reliable-runtime-productization-entry-design`；这次授权只覆盖入口设计，
  不自动打开 8A–8F 产品实现。
- `DECISION`：ADR-0051 冻结 `entry design → 8A → 8B → 8C → 8D → 8E → 8F`。8-Core 必须交付
  可靠 Runtime、Riot+OP.GG typed EvidenceBundle、正式 Web 产品、安全/备份与完整评测；8-Advanced
  至少做一个有 Bad Case、对照、消融、成本和 ADR 的实验，`reject` 是合法出口。
- `BOUNDARY`：Multi-Agent/DAG 只有在 8A/8B 证明独立上下文、权限、失败隔离和可测收益后才采用；
  OP.GG 保持 partial provenance，不能继承 Riot patch 或伪造 upstream freshness；MotionSites 与用户
  Excel 只作为逐项资源审计输入，不成为运行时依赖。
- `LOCAL-EVIDENCE`：已完成初学者教学、现有 Runtime/Task/Harness/Memory/MCP/Riot/Data Dragon/OP.GG
  接缝审计、前端五模块蓝图、采用门、实施计划、八维 coverage 映射和治理同步；本批无产品代码、无
  Key/Provider/Riot/OP.GG 调用、无付费资源购买。
- `NEXT`：入口设计只剩本地门禁、独立提交/推送和 exact-SHA 公共三 job。公共全绿后将 entry-design
  coverage 置为 `complete`，并把唯一下一检查点交接为 `8A-advanced-adoption-gate`。

### 2026-08-22：Stage 8 entry design exact-SHA 公共闭环与 8A 交接

- `PUBLIC-CI`：`3431e8b47dd992b6c4741e12158855feb64ef917` / Actions `32564500421` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`，0001→0009 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`。
- `CLOSED`：entry-design 八维 coverage complete；教学、ADR、8A–8F 顺序、Core/Advanced、EvidenceBundle、
  前端五模块与 MotionSites 采用门正式冻结。该闭环没有写 Stage 8 产品代码。
- `HANDOFF`：唯一下一检查点为 `8a-advanced-adoption-gate` prepared/waiting authorization；授权前不开始
  候选审计、实验，也不提前实现 8B–8F。

### 2026-08-22：RQ-081 授权并完成 8A 本地采用门

- `AUTHORIZED`：用户明确“开始”，授权唯一 canonical 检查点 `8a-advanced-adoption-gate`；本批授权
  不外推为 8B 实验或 8C–8F 产品实现。
- `DECISION`：ADR-0052 保留 `single-runtime-serial-v1` 为 baseline，允许
  `bounded-parallel-evidence-v1` 作为必要 comparator、`role-isolated-multi-agent-v1` 作为 8B primary
  candidate；`third-party-dag-runtime-v1` 与 `agentic-retrieval-v1` 因缺少独立 Bad Case deferred。
- `IDENTITY`：case-set SHA-256 为 `d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e`，
  gate digest 为 `88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；development 与
  calibration-excluded holdout 分离，当前 holdout executions 和 external I/O 均为 0。
- `LOCAL-TDD`：首个红灯为缺少 `app.evaluation.stage8_adoption`；最小 strict/body-free evaluator 后聚焦
  14 项通过；strict-contract 复核的 6 个负例先红后绿，最终聚焦 `20 passed`，相邻回归 `129 passed`。
  cached diff 又以 3 个先红后绿负例锁定唯一 baseline 与串行/普通并行 exact role contract，最终
  `23 passed`。
  20% 延迟、1.5x Token 与 +2
  Provider calls 是未来 8B 工程门，不是当前实测结果。
- `LOCAL-GATES`：完整 pytest `1600 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG 满门、
  Harness published/0 revisions，compileall、pip、6 YAML、安全/治理/diff 门全绿。
- `PENDING`：8A coverage 保持 planned；当前只准备独立 implementation SHA。
  exact-SHA 公共三 job 全绿前不关闭 8A，不实现/运行 8B，不调用 Riot/OP.GG/Provider 或读取 Key。

### 2026-08-22：8A exact-SHA 公共闭环与 8B 交接

- `PUBLIC-CI`：implementation `12ad83532d99990f5523d6ecc6def0b8a325d7d0` / Actions
  `32567642315` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `COUNTS`：公共 pytest `1601 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`，0001→0009 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`。
- `CLOSED`：8A 八维 coverage complete。该证据只证明候选采用门与 8B 实验合同，不证明 Multi-Agent、
  普通并行、DAG、holdout、真实 Provider 或任何 Stage 8 Core 产品能力已实现/运行。
- `HANDOFF`：唯一下一检查点为 `8b-conditional-multi-agent-experiment` prepared/waiting authorization；
  RQ-081 不授权 8B，授权前停止。

### 2026-08-22：RQ-082 授权并完成 8B holdout 前本地实现

- `AUTHORIZED`：用户明确“继续推进”，授权唯一检查点 `8b-conditional-multi-agent-experiment`；无需逐小步
  重复审批，但不外推到 8C–8F。
- `DESIGN`：采用 evaluation-only Scripted/Fake role runner + fixture tools + 真实 `ReviewHarness`；拒绝在
  架构比较中混入真实模型、OP.GG 网络、产品 Runtime 改造或第三方 DAG。
- `TDD`：首次为 2 个 module-not-found collection errors；最小实现后 14 passed。补 expected experiment ID、
  semantic result recomputation、CLI 与原子整批 tool preflight 后聚焦 22 passed；相邻 168/12 subtests。
- `LIFECYCLE`：implementation exact-SHA 公共成功前不执行 holdout；clean SHA development result 位于 ignored
  `tmp/`，正式 result 在 case 前 exclusive reserve，crash sentinel 也禁止重跑。
- `BOUNDARY`：截至本记录正式 holdout/external I/O 均为 0，采用结论未知；当前下一动作是完整本地门、实现
  提交与 exact-SHA 三 job，不进入 8C。

### 2026-08-22：8B implementation CI、唯一 holdout 与 ADR-0053

- `PUBLIC-CI`：`180bc8b452603572d010b6e25b14ed71f6470ce7` / Actions `32572085065` 三 job
  completed/success；pytest 1623/116 skips/127 subtests，真库 164，package schema 1.6/外部调用 0。
- `DEVELOPMENT`：同一 clean SHA 得到 `eligible_for_holdout`；candidate latency 27.05%、Token 1.45、+2 calls，
  quality/safety 门全过。
- `HOLDOUT-ONCE`：预留不可覆盖路径后唯一执行；结果 experiment `0be05e...50494`、文件 SHA
  `944258...445e8`、external I/O/retry/hard gates 0，裁决 `reject_multi_agent`。
- `DECISION`：candidate holdout latency 18.95%<20%，普通并行 22.88%；二者 isolation 均 1.0。ADR-0053
  拒绝产品 Multi-Agent、保留评测资产，bounded parallel 作为 8D 优先设计输入而非 8B 产品改动。
- `PENDING`：result/ADR/tests/walkthrough 尚待独立 evidence SHA 三 job；coverage planned，8C 未进入。

### 2026-08-22：8B evidence 公共闭环与 8C 交接

- `PUBLIC-CI`：`783a329537682b5413d74af4cc3e1ac818f75da2` / Actions `32572610725` 三 job
  completed/success；pytest `1626 passed, 116 skipped, 1 warning, 127 subtests passed`，真库 `164 passed`，
  package schema 1.6/外部调用 0。
- `CLOSED`：result SHA `944258...445e8`、ADR-0053、结果回归和八维 walkthrough 均有持久证据；8B coverage
  complete。Multi-Agent 产品 reject，bounded parallel 只作为 8D 输入。
- `HANDOFF`：唯一下一检查点为 `8c-reliable-runtime-core` prepared/waiting authorization；不自动实现 8C。

### 2026-08-22：RQ-083 授权 8C Reliable Runtime Core

- `AUTHORIZED`：用户明确“继续啊，咋停了”，授权 canonical 唯一检查点 `8c-reliable-runtime-core`，无需逐小步重复审批。
- `SCOPE`：只推进 durable lifecycle event/replay cursor、lease/heartbeat/fencing、cancel request、safe
  checkpoint/recovery、late-result/duplicate-terminal rejection、owner/global backpressure 与观测；沿用 PostgreSQL
  单一控制面、单 Runtime 与 Harness 唯一发布权。
- `BOUNDARY`：8B holdout 不覆盖、不重跑；不接产品 Multi-Agent、DAG/第三方 Runtime、Redis/Celery/Kafka、
  SSE/前端、8D fusion 或真实 Provider/Riot/OP.GG I/O。
- `NEXT`：先完成教学、现有代码接缝审计、替代方案比较、ADR/专用设计与实施计划，再进入 pure contract 红灯。

### 2026-08-22：8C 本地实现与 evidence 路径完成

- `LOCAL-IMPLEMENTATION`：Task 1–6 已完成 strict contracts/projector、0010/ORM、Repository event/lease/
  fencing/cancel/replay、lease-aware Worker、proof-based recovery 与 owner-scoped HTTP；不引入第二控制面。
- `TDD`：既有红灯覆盖合同、status 宽度、event identity、Worker terminal/cancel 与 recovery 竞态；最终
  public operation identity/package replay 两项补强先 `2 failed` 后 `29 passed`。
- `LOCAL-REGRESSION`：最新完整 pytest `1670 passed, 133 skipped, 1 warning, 127 subtests passed`；133 skip
  不冒充真实 PostgreSQL/Docker/Linux 成功。
- `EVIDENCE`：8C walkthrough 与 coverage 八维路径已齐，coverage 仍 `planned`。
- `NEXT`：完成全部横向门、独立 implementation/evidence SHA 与 exact-SHA 三 job；公共全绿前不关闭 8C、
  不进入 8D。

### 2026-08-23：8C clean implementation 公共闭环与 8D 准备态

- `ROOT-CAUSE`：package smoke 的 Repository 直接返回合法 6-event `TaskEventPage`；API 503 根因是
  deployment composition `_TaskServiceProxy` 漏掉 `request_cancel` / `read_events` 转发。补齐后新增
  composed-app cancel/event 回归，未改变 owner scope、lease token 隐私或 Runtime/Harness 边界。
- `PUBLIC-CI`：clean implementation `2df5349d85e48138c05d6293d4e3885b6b4756ec` / Actions
  `32587659678` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- `LOCAL-GATES`：完整 pytest `1673 passed, 134 skipped, 1 warning, 127 subtests passed`；两套 RAG、
  Harness dry-run、compileall、pip、SDK/Secret/tracked-data、governance 与 diff 全绿。
- `CLOSED`：8C 八维 coverage 置 `complete`，PostgreSQL 0010、lease/fencing、cancel、checkpoint/recovery、
  event replay 与 Linux package 纵向获得公共证据；这不等于正式 Auth、SSE、前端、备份或生产 SLA。
- `HANDOFF`：唯一下一检查点为 `8d-riot-opgg-evidence-fusion-core` prepared/waiting authorization；授权前
  不调用 Riot/OP.GG/Provider/LLM、不读取 Key、不实现 8D。8B holdout SHA `944258...445e8` 不得覆盖或重跑。

### 2026-08-23：RQ-084 启动 8D；RQ-085 固定 README 广泛研究边界

- `AUTHORIZED`：用户明确继续正常下一步，授权唯一 checkpoint `8d-riot-opgg-evidence-fusion-core`；8E/8F
  未授权或开始。
- `DECISION`：ADR-0055 采用 immutable typed EvidenceBundle + pure fusion kernel；Riot、Data Dragon、
  official patch 与 OP.GG 各自保留 provenance/digest，partial Meta 不继承 patch/freshness，冲突降级不覆盖。
- `LOCAL`：strict contracts、existing Summary/Data Dragon no-I/O adapter、canonical digest 与 public projection
  已按 red→green TDD 本地实现；focused 18、相邻 48 通过，完整/公共门待完成。
- `PORTFOLIO`：README 研究不局限高星或三个示例，也采纳星数较低但信息架构优秀的项目；图可按目的混用
  AI 概念图、真实截图、SVG、Mermaid 等，但研究持续积累到 8F，不阻塞 8D，不把生成图冒充真实产品。

### 2026-08-23：8D exact-SHA 公共闭环与 8E 交接

- `PUBLIC-CI`：implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions
  `32598480400` 三 job completed/success；公共 pytest 1692/133 skips/127 subtests，真库 186，package
  schema 1.6/外部调用 0。
- `CLOSED`：ADR-0055、strict EvidenceBundle、no-I/O source adapters、partial-provenance/non-inheritance、
  conflict/gap/freshness/claim、public projection 和八维 walkthrough 均有本地/公共证据；coverage complete。
- `BOUNDARY`：真实 refresh、全部 OP.GG、SQL bundle store、React/SSE/Auth/HTTPS/备份/部署仍未实现。
- `HANDOFF`：唯一下一 checkpoint `8e-productization` prepared/waiting authorization；本批停止。

### 2026-08-23：RQ-086 授权 8E preflight 与真实 OP.GG 验证

- `AUTHORIZED`：用户授权一次真实 Riot + OP.GG 验证并进入 8E preflight，同时要求账号由用户选择、支持外服和公开观察对象，前端分小批推进。
- `ADR`：ADR-0056 将真实 external validation 与 8D 公共 CI 分离，冻结 body-free evidence、Key-last、错误分类和不自动跨区重试；玩家档案使用 `Riot ID + routing_region + self|observed`，Conversation 固定 player subject。
- `OPGG-REAL`：官方 OP.GG Streamable HTTP endpoint 的 initialize/list/selected lane-meta call 真实通过 1 次，3 facts，body-free digest `24b49ea9eb9c4c6c6ee682ad21309c7a643fbdde70a8ea18ba8fdf1d26a8c1ec` 已归档；partial provenance 限制保持不变。
- `IDENTITY-GAP`：仓库没有 ShowMaker 硬编码，`/player-links` 已支持显式 Riot ID/region/role；旧 `/reviews/recent` 仍从环境默认地区读取，owner-scoped profile list/selection DTO 留给 8E preflight。
- `NEXT`：等待准确测试 Riot ID + regional routing，执行一次受限 Riot Account/Match gate；随后用脱敏 typed output 做 EvidenceBundle replay/fusion，再进入前端第一小批。
- `PUBLIC-CI`：preflight commit `8c0cc187e93e76c26e9d03f9e8f2371333c783a3` / Actions `32611044101` 的 pytest、PostgreSQL migration 和 Linux package 三 job 均 success；该 CI 不执行外部网络调用。

### 2026-08-23：RQ-086 真实 Riot gate 通过与 OP.GG mid schema-drift

- `SEARCH`：AutoGLM token 服务恢复；公开网页与 OP.GG 当前页面交叉核验 `DK ShowMaker#KR1` 的 KR、Dplus KIA/ShowMaker 关联；不把它写入产品默认。
- `RIOT-REAL`：`DK ShowMaker#KR1 / asia / observed` 的 Account-V1、recent match IDs、Match Detail 共 3 calls 通过；结果只保存 PUUID/match digest 和 allowlisted facts。
- `FUSION-REAL`：使用脱敏 Riot projection 调用一次真实 OP.GG `mid` Meta 并尝试进入 8D adapter；真实响应以 `opgg_meta_result_invalid` 被 fail-closed，未创建 bundle，raw body 未持久化。
- `DECISION`：该真实 Bad Case 归类为上游响应与严格 grammar 的 schema-drift；不放宽 parser、不把分别通过说成融合通过，先补安全诊断/回归样例。
- `NEXT`：schema-drift 处理裁决后再冻结玩家档案选择 DTO，之后进入前端首个静态小批。

### 2026-08-23：8E body-free schema-drift diagnostic 接缝

- `ADR-0057` 采用字段级 body-free 结构诊断；受控 fixture 只验证 fail-closed 诊断合同，不能冒充 live schema。
- 真实 `mid` 结果仍只保留 `opgg_meta_result_invalid` 与 stack-level `row_field` 事实；没有新的外部授权不重跑服务、不扩大 parser。
- 前端、player profile selection 与 legacy 地区修正继续排在 live drift 裁决之后。

### 2026-08-23：RQ-087 live diagnostic 与 ADR-0058 JSON-null 裁决

- `AUTHORIZED`：用户明确新授权“把问题修复好”；本窗口复用既有 body-free Riot result，只执行一次
  OP.GG `mid` tools/call，Riot/LLM/Key calls 为 0，raw response 不持久化。
- `LIVE-EVIDENCE`：`riot_opgg_fusion_validation_2026-08-23-v2.json` 将失败定位到
  `Mid.rank_prev_patch` / field 7 / AST `Name`；live length/digest 与受控 fixture 不同。
- `DECISION`：ADR-0058 只在 `rank_prev`/`rank_prev_patch` 接纳精确小写 JSON `null` 并投影为 `None`；
  其他 Name、字段、大小写和表达式继续 fail closed，不改变 partial provenance/freshness/patch 边界。
- `TDD`：nullable 正例先红；实现后 OP.GG/fusion 16 项、相邻 MCP/Evidence 60 项通过。完整本地和 exact-SHA
  公共门待执行；该授权 call 已用完，修复后最终 live replay 仍需新的明确授权。

### 2026-08-23：ADR-0058 exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `83fde7d014aae8fdccf2ebd91929967868101075` / Actions
  `32615340228` 三 job completed/success；公共 pytest 1700、真实 PostgreSQL 186、Linux package schema 1.6。
- `BOUNDARY`：公共 CI 外部 Riot/Provider calls 0，也不调用 OP.GG；因此它证明代码/回归/部署兼容，不证明
  修复后 live bundle 成功。8E 继续 in progress，唯一下一动作是等待新授权的一次最终 `mid` replay。

### 2026-08-23：RQ-088 持续授权与 ADR-0058 修复后 live 通过

- `POLICY`：必要、有界、低费用、隐私可控的只读真实调用不再逐次等待授权；高费用/批量、敏感数据发送、
  不可逆写入与权限扩大仍需确认。每次调用继续记录次数、停止条件和 body-free 结果。
- `LIVE-PASS`：修复后单次 OP.GG `mid` call 解析 10 facts，创建 EvidenceBundle `69ed8a...fff1a`；
  OP.GG/Riot/LLM/Key calls `1/0/0/0`，无重试/raw body。
- `HONEST-DEGRADE`：Akali 未命中 top-10 Meta，Data Dragon/official patch 未进入 replay，因此 bundle 为
  `degraded/unjoined`；这是正确 gap，不换样本、不扩大抓取、不继承 patch 追绿。
- `NEXT`：frozen success evidence regression、比例本地门、独立 evidence SHA 与三 job；随后进入 player
  profile selection DTO/legacy region，不再阻塞于 OP.GG parser。

### 2026-08-23：修复后 live-success evidence 公共闭环

- `PUBLIC-CI`：evidence `efaccd9a8022f0d75e9baca5470450be6a1a3357` / Actions `32615821339`
  三 job completed/success；公共 pytest 1701、真实 PostgreSQL 186、Linux package schema 1.6。
- `CLOSED-BATCH`：OP.GG nullable JSON-null Bad Case 已完成从 live diagnosis 到 post-fix live/public evidence 的
  全链闭环；8E 继续 in progress，下一批转为 player profile selection DTO/legacy region。

### 2026-08-23：RQ-089 与 8E Batch B 本地收尾

- `REQUIREMENT`：用户要求消除各阶段可避免的本机 skip；已配置 Docker Desktop/WSL2、持久 PostgreSQL 17
  与用户级测试 URL。历史 skip 主要延迟本地反馈，相应 exact-SHA PostgreSQL/Linux job 仍是完成事实源，
  不因今天补环境而重写历史。
- `DECISION`：ADR-0059 复用成功 Player Link 投影 owner-scoped latest profile；不新建 default/profile table。
  `player_profile_id` 是 opaque relationship-backed selection，公共 DTO 保持 PUUID-free。
- `IMPLEMENTED-LOCAL`：`GET /player-profiles`、Conversation canonical selection/legacy alias、legacy required
  region、SQL target region propagation、四地区 exact-select builder 与 Compose 去 ambient `RIOT_REGION` 已完成。
- `LOCAL-EVIDENCE`：CI-equivalent PostgreSQL collection `187 passed`、focused `268 passed`、完整
  `1842 passed, 1 skipped, 1 warning, 127 subtests passed`、Alembic upgrade/check 与 Linux Compose
  package schema 1.6/外部调用 0/image boundary 已通过。Windows symlink 单项 skip 继续由
  exact-SHA Linux pytest 补证，不扩大系统权限追求零 skip。
- `STATUS`：两套 RAG、Harness、compile/pip/YAML、安全/治理/diff 门均全绿。8E 保持 `in_progress`，coverage
  保持 `planned`；唯一下一动作是独立提交/push
  和 exact-SHA 三 job。公共全绿前不进入静态前端小批。

### 2026-08-23：8E Batch B exact-SHA 公共关闭

- `PUBLIC-CI`：implementation/evidence `e844bdd673ee051568e8611160f6ba53e8c745c4` / Actions
  `32622696087` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1709 passed, 134 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `187 passed, 1 warning`、migration/head 一致；Linux package schema 1.6/外部调用 0/image boundary 全绿。
- `CLOSED`：ADR-0059、profile/routing implementation、八维 walkthrough 与本机基础设施补齐正式关闭 Batch B；
  8E/coverage 继续 in progress/planned。
- `HANDOFF`：按 preflight 既定顺序唯一下一内部批为 Batch C EvidenceBundle persistence/refresh/expiry、
  event replay→SSE body-free DTO 与四态产品状态合同；不得静默跳过 Batch C 进入 Batch D 前端。

### 2026-08-23：RQ-090 8E Batch C 本地实现与门禁闭环

- `DESIGN/IMPLEMENTED`：ADR-0060 下 PostgreSQL immutable Evidence revision、query-time expiry、四态
  Product API、cursor SSE、0011/composition/package 与八维 walkthrough 已按 TDD 完成；8E coverage 继续
  `planned`。
- `BAD-CASE/FIX`：本地 Compose 默认 API owner 与 smoke 硬编码 owner 漂移导致严格 Memory Context
  unavailable；当前改为同源 validated owner，未放宽 owner/relationship/conversation checks。
- `LOCAL-EVIDENCE`：focused 79、CI-equivalent PostgreSQL 194、完整 1888/1 skipped/127 subtests、可逆
  Alembic、两套 RAG、Harness、compile/pip/YAML/security/OpenAPI 与 Linux schema 1.6/外部调用 0/image
  boundary 全绿；Windows symlink 单项由 exact-SHA Linux pytest 补证。
- `NEXT`：独立 implementation/evidence commit/push 与同 SHA 三 job；公共成功前 Batch C 保持 open，
  不进入 Batch D React。

### 2026-08-23：8E Batch C exact-SHA 公共闭环与 Batch D 准备态

- `PUBLIC-CI`：implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions
  `32629160732` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest 1750/139 skips/127 subtests，真实 PostgreSQL 194，0011 可逆且 metadata=head；
  Linux package schema 1.6/外部调用 0/非 root/image boundary 与资源清理全绿。
- `STATUS`：Batch C 正式关闭；整个 8E coverage 保持 planned。唯一下一内部批为 Batch D
  静态/fixture-backed 前端设计门，prepared/waiting authorization；不静默进入 React/Auth/部署。

## 2026-08-23：8E Batch D 静态前端公共闭环

- implementation/evidence `f7ebedd7c6cfd135201847a327dfd06c01cc7205` / Actions `32636771507` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest 1752、真 PostgreSQL 194，
  frontend unit 35/e2e 12/typecheck/build 与 Linux package schema 1.6 均在 exact SHA 通过。
- 因此 Batch D fixture-backed Rift Command Center 正式关闭，但 `8e-productization` 与 coverage 仍为
  `in_progress/planned`。真实 API/SSE/Auth、电影感入口、完整 Timeline/Training、部署和 8F 没有被完成。
- 唯一下一动作改为真实数据接线设计门：盘点 Batch B/C owner-scoped DTO 与 Summary/report HTTP
  projection 缺口，再冻结 decoder、Last-Event-ID 重连、错误和状态保持合同；不自动进入 Batch E/8F。

## 2026-08-23：RQ-094/RQ-095 上下文纠偏与 Live Integration 设计

- `CORRECTED`：RQ-093 只恢复五模块和资源池仍不够。定向复核“五项裁决→开工”后，补回最终 A/B/C
  视觉职责、A→B combination、checkpoint 小复盘、OP.GG breadth gate 与完整真实 fusion golden slice。
- `NOT-REOPENED`：Stage 7 V1、8D typed fusion 与现有 live parser Bad Case 均保持关闭；补的是未排期的产品
  广度/纵向验收，不改写历史提交或重跑负面结果。
- `ADOPTED-DESIGN`：ADR-0062 选择 thin latest-review locator + existing APIs client composition；新增 Recent
  Summary HTTP 和 typed Evidence schema，前端冻结 exact decoder、generation/AbortController、one
  EventSource、restricted Markdown 与真实 Training 字段。
- `REJECTED`：当前不采用大 Workbench BFF、URL/localStorage-only run binding、Zod/OpenAPI codegen、第二
  SSE parser/动画栈，亦不因接线门提前进入 WebGL、Auth、部署、完整 Timeline/Training 或外部调用。
- `STATUS`：整个 8E/coverage 继续 `in_progress/planned`。当前只待设计文档/治理本地门、独立 design SHA 与
  exact-SHA 三 job；公共成功前 implementation 未获授权。

## 2026-08-23：Live Integration design exact-SHA closure

- `PUBLIC-CI`：`4057c93f4ac1ac9ebd181528e559b084e3425e89` / Actions `32639561338` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 全绿；pytest 1752、PostgreSQL 194、frontend
  unit 35/e2e 12/typecheck/build 与 Linux package 同 SHA 通过。
- `CLOSED`：RQ-095 设计门正式关闭；未写产品代码、未调用外部服务、未进入 Auth/部署/五模块其余页面。
- `HANDOFF`：live integration implementation 仅 prepared/waiting authorization；整个 8E/coverage 继续
  in_progress/planned，RQ-094 breadth/golden-slice 仍是后续待办而非本批完成项。

## 2026-08-23：RQ-096 Live Integration 本地完成

- `AUTHORIZED`：用户继续授权完整执行既有 implementation plan，无需逐 Task 再批准；边界仍排除 Auth、
  部署、入口/Timeline/完整 Training、OP.GG breadth、fusion golden slice 与 8F。
- `IMPLEMENTED`：PostgreSQL latest locator、Recent Summary、typed Evidence HTTP、composition/package 与前端
  exact decoder/client/adapter/controller/EventSource/default-live UI 均按 TDD 完成；外部调用和 8B holdout 为 0。
- `DECISION`：react-markdown bundle 超 150 kB 后移除，以 escaped plain text 保持安全/性能门；不提高预算。
- `BAD-CASES`：修复 browser fetch receiver、OpenAPI exact paths、E2E ledger reuse/local worker pressure、
  failed-task Evidence smoke order、`/player-profiles` generic exception 映射错位、chunked body 延迟限额、
  invalid-selection stream cleanup 与 URL initial profile composition 漏项；严格 decoder、server-list membership、
  Evidence write status 与 Product State 语义未放宽。
- `LOCAL-EVIDENCE`：focused 58、package 59、完整 pytest 1939/1 skip/127 subtests、真 PostgreSQL 200、
  frontend unit 66/e2e 17、JS gzip 122.01 kB、可逆 Alembic、RAG/Harness/security/governance 与 Linux package
  schema 1.6 全绿；八维 walkthrough/coverage paths 完成。
- `NEXT`：独立 implementation/evidence commit/push 与同 SHA 三 job。公共成功前 live integration 批保持
  open，8E/coverage 继续 in_progress/planned。

## 2026-08-23：RQ-096 Live Integration exact-SHA closure

- `PUBLIC-CI`：`f441061e7444fa6d1d3c213b81e05a02f0fc68c5` / Actions `32647933692` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest 1796/144 skips/127 subtests、真实 PostgreSQL 200、frontend unit 66/e2e 17、
  JS gzip 122.01 kB、Linux package schema 1.6/Memory Context 3/外部调用 0 同 SHA 通过。
- `CLOSED`：RQ-096 批正式关闭；整个 8E/coverage 仍 in_progress/planned，Auth/部署、入口/Timeline/完整
  Training、breadth/golden slice 与 8F 未完成。
- `HANDOFF`：唯一下一检查点为 `8e-batch-e-security-deployment-entry-design` prepared/waiting
  authorization；先原子化安全/部署与剩余模块顺序，不自动实施或配置生产环境。

## 2026-08-23：RQ-097 Batch E 安全/部署入口设计

- `AUTHORIZED`：用户最新“那继续做你觉得接下来应该做的事”恢复唯一检查点
  `8e-batch-e-security-deployment-entry-design`；不把授权外推为 Auth/RSO、HTTPS、备份或部署实现。
- `DESIGN`：ADR-0063 采用 provider-neutral AuthPort + server-side opaque session，明确 RiftCoach
  Auth 与 Riot RSO 分离；首个公开拓扑采用 edge/static Web + API/Worker/PostgreSQL 单机 Compose，
  托管 PostgreSQL 保留为迁移路径，Kubernetes/Redis/Celery/Kafka deferred。
- `SECURITY`：冻结 same-origin/CORS/CSP/安全响应头、body/connection/SSE/限流容量、Secret
  key-last/rotation/revocation、owner/observed/self 隔离、deletion marker→backup restore erase replay、
  隐私说明、readiness/observability 和待演练 RPO≤24h/RTO≤2h 目标；这些是后续实施合同，不是当前证据。
- `PRODUCT-ORDER`：冻结 E1 Auth → E2 edge security → E3 Secret → E4 backup/erase → E5 packaging/observability，
  再按 secure shell/Rift Awakening、Timeline、Evidence/Trace、Training、OP.GG breadth+golden slice、8E exit/8F handoff
  施工。视觉继续遵守多来源两层采用门，不能因安全门退化成普通后台。
- `BOUNDARY`：新增 ADR/design/implementation plan/walkthrough 并登记 8E planned coverage；本轮不读 Secret、
  不调用外部服务、不写产品代码、不部署。公共设计 SHA 全绿后才把 Batch E implementation 标为 prepared。

## 2026-08-24：RQ-098 视觉合同前置

- 用户确认 A/B 融合方向 `Rift Awakening → Broadcast Workbench`，并要求在保持 suitable、可访问、可维护和
  数据真实的前提下提高 visual completion、fashion、cool 和互动叙事。
- 该决定只在 Stage 8 `8e-productization` 下增加一个不改变主阶段顺序的视觉前置：先冻结 ADR-0064、分层
  资产/来源账本、presentation state、动效 storyboard 与多来源采用账本，再实现入口 preview；不把它重新命名成
  新主阶段或提前关闭 Batch E。

## 2026-08-24：RQ-099 视觉 Task 3 后连续进入 Batch E implementation

- 用户要求先继续 polish 入口，降低机械 overlay 的喧宾夺主，再不需每个小步骤重新授权地进入后续 Batch E
  原子工作；该授权不改变 Stage 8 顺序，也不把连续推进等同于完成公共闭环。
- Task 3 已通过本地视觉与前端门；E1/E2/E3 进入本地 TDD：opaque session/CSRF、request budgets/单机
  rate、versioned SecretSource/key-last Worker composition。每批仍保留八维 evidence、完整比例回归、独立
  commit 和 exact-SHA 三 job 公共 CI；正式 Auth/RSO、HTTPS、Secret Manager、备份/部署与 8F 继续后续。

## 2026-08-24：RQ-099 E1/E2/E3 exact-SHA 公共闭环

- `92b768591183e8a7fbe6d12a86359aac862b7efb` / Actions `32658277570` 的 pytest、PostgreSQL migrations、
  Linux packaging-smoke 三 job 全绿，E1/E2/E3 取得公共代码证据。
- canonical 继续停在 `8e-productization` implementation；下一项按原子顺序进入 E4 backup/restore/erase，
  不因连续授权跳过八维证据、独立提交或把未实现的 Auth/RSO/HTTPS/Secret Manager/备份说成完成。
- 生成图不可冒充真实 UI、数据或产品截图；MotionSites、React/动效库、Riot 官方语言、成熟游戏数据产品与
  Image2/Photoshop 继续按 RQ-091/RQ-092 两层采用门横评。

## 2026-08-24：RQ-099 E4 本地实现记录

- E4 首轮实现把 6B-9 owner deletion marker 接到真实 run data locator/cleaner：PostgreSQL
  `ReviewTaskRecord` 提供 body-free run identity，API composition 在 marker commit 后才删除 Artifact/Trace
  目录，cleanup failure 仍保留 hidden-before-cleanup compensation。
- restore 合同增加 deterministic manifest digest、幂等 marker replay 和 readiness-before-ready；当前只做
  本地/离线 drill，不读取 Secret、不调用 Riot/OP.GG/LLM、不写外部 backup，不宣称 KMS、对象存储或 RPO/RTO
  实测。
- 下一动作是比例门和公共 exact-SHA 闭环；E5/8F 不提前进入。

## 2026-08-24：RQ-099 E4 exact-SHA 公共关闭，交接 E5

- implementation/evidence `27b9256b8987ade45fbc9eb5f62497cbaef9f518` / Actions `32660145945` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；E4 正式关闭。
- E4 公共证据覆盖 owner marker→run locator→Artifact/Trace cleanup、restore marker replay/幂等、readiness
  compensation、真库 migration 和 Linux package image boundary；无外部 Riot/OP.GG/Provider/LLM I/O。
- 下一项按连续授权进入 E5 packaging/observability，仍维持单机 Compose 与 body-free observability 边界；
  KMS/对象存储、Kubernetes/Redis、8F 和 OP.GG golden slice 不因 E4 关闭而提前完成。

## 2026-08-24：RQ-099 E5 metrics projection 本地首批

- 在现有 Compose/Docker/readiness/structured logging 基础上增加 bounded event counters、latency snapshot
  和 `/health/metrics` typed projection；未新增外部监控 runtime、Secret、网络 I/O 或前端部署。
- E5 当前只完成 focused 本地实现，完整回归、独立提交和 exact-SHA 三 job 公共 CI 仍是关闭门；不把
  `/health/metrics` 写成 Prometheus/长期存储/自动告警能力。

## 2026-08-24：RQ-099 E5 exact-SHA 公共关闭，交接 production shell

- `ca6da44` / Actions `32661425379` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；
  E5 正式关闭，metrics/readiness/Compose/package 证据已公开。
- 下一产品切片是 production shell/Auth gate，先连接 opaque session/CSRF 的 UI 状态合同；OIDC/RSO、
  HTTPS、完整 frontend modules、OP.GG breadth/golden slice 和 8F 仍按独立门推进。

## 2026-08-24：Production shell/Auth gate 本地实现与视觉 polish

- Rift Awakening 的 mechanical atmosphere 降为低对比可移除层，真实截图确认标题、校准表单与 handoff
  成为主层；reduced-motion、CSS/SVG fallback 和资产 ledger 边界保持不变。
- Live 默认路径新增 typed same-origin auth session gate：checking 不加载 controller；auth unavailable
  和 session expired/revoked/required 各自投影为安全 UI 状态；fixture/preview 不伪装生产登录。
- 本地 frontend unit/e2e/typecheck/build 全绿，下一步是独立提交与 exact-SHA 公共 CI；CI 通过后交接
  `Timeline DTO/UI`，不提前进入 OP.GG golden slice 或 8F。

## 2026-08-24：RQ-100 production shell/Auth gate 公共闭环，交接 Timeline DTO/UI

- `15a3a9e` / Actions `32663345737` 的三 job 全绿，production shell/Auth gate 正式关闭；本地缺少真库的
  skip 由公共 PostgreSQL service 补齐，Linux package/no-I/O smoke 也取得证据。
- 下一检查点是 Timeline DTO/UI：优先冻结 match/timeline identity、available/partial/missing、source
  freshness 和 owner/observed relationship 语义，再实现 typed decoder 和视觉呈现；不提前做 Evidence 深化、
  Training full page、OP.GG golden slice 或 8F。

## 2026-08-24：RQ-101 Timeline 采用 verified event/phase projection

- 当前 Summary Artifact 没有持久化 Gold/CS/XP/level series，因此 ADR-0065 拒绝前端假曲线和请求时重拉
  Riot；只采用 persisted death/item/objective events 与 early/mid/late phase。
- local implementation 已覆盖 strict bounded DTO、owner/publication/integrity gates、exact decoder/controller、
  responsive/a11y UI、partial/unavailable 与 durable screenshot；本批无 migration、外部调用或新 chart library。
- 当前路线顺序不变：Timeline exact-SHA 三 job 公共关闭后，才交接 Evidence/Trace 深页；Training full、
  OP.GG useful-breadth + golden slice、8E exit 和 8F 继续保持后序独立门。

## 2026-08-24：RQ-102 在后续模块前建立中英双语产品表面

- 用户明确当前英文 UI 不是最终语言边界；8E 必须正式支持 `zh-CN/en`。
- 为避免 Evidence/Trace、Training 完成后整站返工，Timeline 公共关闭后的唯一下一原子项调整为 bilingual
  product-surface foundation；随后恢复 Evidence/Trace → Training → OP.GG breadth/golden slice 顺序。
- UI catalog、Data Dragon entity locale、Coach report language 三层分离；API enum/status/reason code 保持唯一
  canonical 值。语言切换持久化、missing-key fallback、text expansion、mobile/a11y/bundle 都是阻塞门。

## 2026-08-24：RQ-103 当前高保真 V1 不等于最终视觉签收

- 用户明确当前截图、UI、色调、背景、布局和细节都要继续 polish；英雄头像只是缺口示例，当前 Timeline
  不得写成最终作品集视觉成品。
- RQ-102 双语基础后新增 LoL asset/detail enrichment 原子批：先建立 Data Dragon version/locale/fallback
  合同，再补英雄/装备/目标资产、加载失败回退与 hover/focus/selection 联动。
- 8E 退出前必须完成入口、工作台、Timeline、Evidence/Trace、Training 的跨模块色彩、背景、布局、动效、
  响应式、双语和 a11y final visual QA；该纠正不改变当前 Timeline 先完成 exact-SHA 公共关闭的顺序。

## 2026-08-24：RQ-101 Timeline exact-SHA 公共关闭

- `794032f055f2fa37173f9525279870f0adbe5220` / Actions `32682243568` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job completed/success；Timeline DTO/UI 正式关闭。
- 公共 pytest 1837/145 skips、frontend unit 92/e2e 25、真 PostgreSQL 201、Linux package schema 1.6 同 SHA
  全绿；Riot/OP.GG/Provider/LLM calls 0。
- 该闭环不覆盖双语、LoL 资产 enrichment、Evidence/Trace、Training、breadth/golden slice 或最终视觉签收；
  唯一下一原子项按 RQ-102 更新为 bilingual product-surface foundation。

## 2026-08-24：RQ-102 bilingual foundation 设计冻结

- ADR-0066 与专用 design/implementation plan 采用 `zh-CN | en` typed local catalog + React context；不引入
  i18n runtime，不把浏览器机翻用于 Coach report/Evidence，也不翻译 API canonical code。
- versioned localStorage、navigator fallback、document lang、English missing-key fallback、text expansion、
  mobile/a11y/bundle 和“不重取 API/不重连 SSE”成为实现阻塞合同。
- 当前只完成本地设计/八维 planned evidence；产品代码、API/Memory、依赖、Data Dragon 资产和外部调用均未
  改变。下一动作是独立 design SHA 三 job；公共关闭后才进入 locale contract/catalog TDD。

design `8969aef` / Actions `32683742229` 的三 job 已全部成功；设计门正式关闭，当前只进入 bilingual
foundation implementation，不提前进入 RQ-103 或后续产品模块。

## 2026-08-24：RQ-104/105 双语 copy 与三层产品旅程纠偏

- 用户否决直译、AI 说明腔和 `裂谷指挥中心` 等生硬命名，并确认母图应是可操作的动态 Portal：中央核心
  → 独立账号访问 → Workbench；AuthGate 和 Riot ID 表单都不是开屏。
- 新增 ADR-0067 与专用计划；ADR-0064 的视觉语言保留，但“Portal 内 identity calibration”被部分取代。
- 本地实现 typed bilingual catalog/strict persistence/structured copy、`portal|account|workbench` history、
  semantic core、Auth/Account、真实 Player Link client/controller、profile fail-closed 与 session failure cleanup。
- fake API/E2E 已覆盖 core 前 0 API、Link queued/running/succeeded、reload/back/forward、fixture 隔离和 unlisted
  profile；后端又增加 session owner→CSRF Link→terminal→profiles 纵向测试。该记录仍是本地实施，不是公共关闭。

## 2026-08-24：RQ-106 母图分层与旧素材降级

- 用户再次拒绝围绕旧 aperture/instrumentarium 反复打磨。采用母图三段构图生成无文字/UI 的 V2 keyframe，
  再移除烘焙 core/beam 得到 runtime background；DOM core 保持唯一 focus/click/handoff 真值。
- keyframe 只进 `docs/assets/8e-portal` 作设计证据；122.7 kB background 进入 same-origin public asset；aperture
  是加载失败 fallback，instrumentarium 已移出 public runtime。正常 handoff 为 bounded 720ms，reduced-motion
  立即进入。当前仍不是最终电影化动效或 RQ-103 final visual QA。

## 2026-08-24：RQ-107 Coach/Training Agent 产品缺口待裁决

- 只读审计确认后端已有 Conversation/Message、AgentRuntime/Harness、terminal assistant、Memory-aware Context
  与 Training Candidate/Plan/Progress，但 Web 仍只是 report viewer + read-only Training summary。
- 推荐当前批先闭环，再在 RQ-103 前插入 8E 内部 bounded review-grounded Coach；开放域聊天、token stream、
  observed 持久 Plan 和自动长期写入不默认采用。
- 该推荐会调整已持久化子项顺序，用户尚未集中裁决，因此 canonical 下一检查点保持当前 foundation，不自动
  插入或实施 Coach。

## 2026-08-25：RQ-108 固定 foundation 后的 Portal Motion Polish

- `CURRENT`：canonical 唯一原子项仍是 bilingual product-surface foundation；design 已公共关闭，implementation
  与本地全门完成，只待独立提交、push 和 exact-SHA 三 job。RQ-108 尚未进入设计或实现。
- `DECIDED-NEXT`：foundation 公共关闭后固定进入独立 `portal-motion-polish`，不能先跳到 RQ-103、Coach 或
  其它产品模块，也不能把当前静态 V1 冒充最终动效。
- `SCOPED-SUPERSESSION`：RQ-108 只取代 Portal Task 3 作为最终视觉/动效验收，以及可见 CSS/SVG core/route
  作为最终 art；zero-early-I/O、Portal→Account→Workbench、原生语义 hit target、keyboard/focus、history、
  reduced-motion 和失败 fallback 等功能证据继续有效。
- `CURRENT-DESIGN`：确认母图是构图源；水晶在场景内重绘/调大并参与 ambient media，透明原生 button 只提供
  click/keyboard/读屏语义，不显示独立贴图或常规按钮。轻微光点/短脉冲提示进入，激活后汇聚、一次 burst 并
  幕切到独立 Account 动态场景。媒体必须通过 codec/poster、移动安全区、Save-Data、reduced-motion、错误
  fallback、下载/解码/JS 预算、许可和移除门；不热链、不复制付费素材、不默认增加 Three/OGL/Anime。
- `UNRESOLVED`：RQ-108 之后，RQ-107 bounded Coach 与 RQ-103 Data Dragon asset/detail/final-QA 的相对顺序
  仍待用户裁决。RQ-108 不实现 Coach、OIDC/RSO、Data Dragon enrichment 或全站 final visual QA。

## 2026-08-25：bilingual/product-journey foundation 公共关闭

- `PUBLIC-CI`：implementation/evidence `6084937833beed625dbc64fdcd4c8175edbc9d8f` / Actions
  `32757872792` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `CLOSED`：RQ-102/104 typed bilingual product surface 与 RQ-105/106 Portal→Account→Workbench、Player Link、
  owner-scoped selection、history/focus/fail-closed、母图分层 V1 取得公共证据；8E parent/coverage 仍未完成。
- `HANDOFF`：RQ-108 `portal-motion-polish` 现在是 prepared/waiting authorization。公共 CI 不把静态 Portal
  升级成最终视觉，也不授权自动开始媒体/素材实现。

## 2026-08-25：RQ-109 授权启动 Portal Motion Polish

- `AUTHORIZED`：用户明确“开始”，授权唯一原子项 `portal-motion-polish`；当前从教学、现有 motion/media
  seam 审计、方案比较、ADR-0068、正式设计和实施计划开始。
- `BOUNDARY`：设计门完成前不写 runtime 动效实现、不采用生成资产、不改变 Portal→Account 的 Auth/API
  生命周期；不进入 Coach、Data Dragon enrichment、跨模块 final QA 或 8F。

## 2026-08-25：RQ-110 将暗化 Portal 固定为 anti-reference

- `SUPERSEDED-FOR-FINAL`：当前 `rift-portal-background-v2`、全屏暗幕/vignette/blur 和左上说明字不进入
  RQ-108 最终 runtime；它们只保留历史 V1/回归反例价值。
- `CURRENT`：确认高清母图是唯一画面源。正常体验从它制作同构全屏循环 background，同母图 poster 负责
  reduced-motion、Save-Data 和媒体失败；只保留融景小字标、语言控件、不可见可访问名和水晶微光提示。
- `CURRENT`：此前多来源研究继续有效，必须广泛筛选后少量自主重构，不依赖 MotionSites 或任何单一来源。

## 2026-08-25：RQ-111 至 RQ-114 Account 五英雄分层制作边界

- `RQ-111`：Account 可固定 Camille/Kindred/Ahri/Jinx/Thresh 五个位置英雄，但必须以场景原生全身能量回响
  融入峡谷，不使用头像、卡片、英雄名或假个性化。
- `RQ-113/114`：一次性群像 v2 因人物解剖畸形、splash 抠图换蓝感被拒绝。流程改为无英雄底座 → 单英雄
  场景化重塑与逐项解剖验收 → 分层透视/光照合成 → 全局 loop；rejected 图不再作为 edit target。
- `BOUNDARY`：可识别英雄进入公开 runtime 前仍须 Riot 产品政策、免责声明、来源/hash 和移除路径；概念预览
  不能冒充采用或许可完成。

## 2026-08-25：RQ-115 至 RQ-117 Account 地图真实性收敛

- `RQ-115` 拒绝把峡谷做成机械轨道；`RQ-116` 固定左下蓝方、右上红方、河道中性蓝、男爵紫与小龙暖色。
- 用户随后指出红蓝 v3 宏观看似峡谷、细看仍是模型臆造。RQ-117 因此采用“官方精确拓扑 + 有意概括的
  Hextech 战术地形投影”：map11 与 Riot 2024 near-final concept 锁定三路、斜河道、双野区、双坑、双方
  基地和阵营方向；野区/墙体/塔/基地只用 terrain masses、轮廓、材质区与符号节点表达。
- `REJECTED`：任何位置看似具体却无法由官方参考支持的微型树、墙、草丛、坡道、道路或建筑；当前 v3 继续
  是未签收 preview，不得成为 Account source、英雄合成底座或 runtime。

## 2026-08-25：RQ-108 design gate 本地冻结

- ADR-0068、正式 design、TDD implementation plan、asset ledger 与八维 planned walkthrough 已建立；媒体架构
  为 typed manifest → viewport-aware policy → poster-first/sticky playback → ProductJourney-owned activation。
- RQ-118 正式取代早期水晶放大/重绘要求：保留确认母图的原水晶、塔体和构图，只在全局 loop/burst 中让
  原水晶运动；两张放大 edit、独立/CSS/贴图水晶保持 rejected。
- archival PNG 逐字节保留；runtime poster 可压缩，但必须绑定 source SHA、通过 SSIM 和人工原尺寸审查，
  不得用暗化/模糊换体积。Save-Data/reduced-motion 首次 render 为 0 video requests。
- `NEXT`：完成所有 canonical/stale 同步和本地 design 门，创建独立 design commit/push 并等待 exact-SHA 三
  job。公共全绿前不写 runtime，不继续生成 Account candidate，也不进入 Coach/RQ-103/8F。

## 2026-08-25：RQ-119/120 Kimi Bad Case 与三路线视频横评

- 用户在 Chrome `localhost:7100` 展示按教程生成的 Kimi loop；媒体实际为有效 12s/1080p H.264，但母图→
  首帧 SSIM `0.412818`，人工审查确认重新取景、有效细节发糊和几何/纹理重绘。裁决 rejected，不入仓库媒体。
- `DECISION`：Kimi 降为未准入候选；同源 bake-off 增加 Wan 2.7、Seedance、Veo、Luma、Runway/Firefly。
  同时比较 HyperFrames/Remotion 确定性 frame render，推荐“生成式有机层 + 确定性结构合成”为 primary candidate。
- `BOUNDARY`：本批只完成官方资料/skill 质量审计和 body-free audit；没有安装 skill、购买 credits、创建 Key、
  调用付费模型或修改 `web/` runtime。工具采用仍需安全审计、隔离 spike 和新 ADR。

## 2026-08-25：RQ-108 design exact-SHA 公共关闭

- `b3b5280/32812868683` 的 pytest、PostgreSQL migrations/control-plane 与 Linux packaging 三 job 全绿；设计门
  正式关闭，8E coverage 仍 planned，Portal/Account runtime media 仍未实现。
- 唯一下一动作是 implementation Task 1 manifest/cover geometry/media policy TDD；不把设计授权外推为 skill
  安装、credits/Key、付费视频调用或 production asset adoption。

## 2026-08-25：RQ-121 正规中转目录补充

- 用户提供 Seedance/Kling/Grok/Hailuo/Sora/Veo/Vidu/Wan 的中转候选；采用门保持 official first、relay second。
- relay slug/`official` 标签/价格不作身份事实；必须先验证 mapping、能力、压缩、隐私、地区、错误/计费和
  body-free provenance。该补充不打断 runtime Task 1，也不授权上传或付费调用。

## 2026-08-25：RQ-108 runtime Task 1 本地完成

- manifest/geometry/policy/hook 已 red→green；独立审查暴露并修复 legacy MQL crash 与 render→commit motion
  race，采用 useSyncExternalStore + poster/preflight。
- focused 71、frontend 207、typecheck/build、bundle/governance/diff 全绿；当前只待独立 SHA/公共三 job，
  Task 2、production media、skill/model/relay calls 均为 0。

## 2026-08-25：RQ-108 runtime Task 1 exact-SHA 公共关闭

- implementation/evidence `1b146e6116587b855a6208e998b5254eac8cba1d` / Actions `32826953474` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；Task 1 正式关闭。
- `HANDOFF`：唯一下一动作是 Task 2 poster-first playback/session-sticky failure TDD；公共绿灯不授权 App 集成、
  production media、HyperFrames 安装或视频/relay/model 调用。

## 2026-08-25：RQ-108 runtime Task 2 本地完成

- `mediaSession` 与 `CinematicSceneMedia` 已以 39 项聚焦 TDD 完成；覆盖 poster-first、single-flight play、
  sticky failure、visibility/user pause、attempt/play token、mounted/StrictMode/旧 rendition 隔离和 poster 事件。
- frontend unit `246`、typecheck/build、Playwright `36` 与 bundle 门通过；当前仍无 App import、production media、
  视频 skill/model/relay 调用。唯一下一步是 Task 2 implementation/evidence exact-SHA 公共闭环。

## 2026-08-25：RQ-108 runtime Task 2 exact-SHA 公共关闭

- `2111a78/32833608622` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；Task 2 正式关闭。
- `HANDOFF`：唯一下一动作切为 Task 3 单次 Portal 激活与跨幕 overlay TDD；App 组合、production media、
  视频 skill/model/relay 与 Task 4/5 仍未进入。

## 2026-08-25：RQ-108 runtime Task 3 本地完成

- `portalActivation`、`PortalActivationOverlay` 与 ProductJourney-owned activation seam 已以 23 项聚焦测试
  完成；覆盖 generation/latch、reduced-motion、popstate cancellation、唯一 navigation、aria/pointer isolation
  和 Account 跨幕退出。
- frontend unit `257`、typecheck/build、Playwright `36` 全绿，JS/CSS gzip `144.07/18.50 kB`；当前只待 Task 3
  implementation/evidence exact-SHA 公共闭环，不进入 Task 4 或生产媒体。

## 2026-08-25：RQ-108 runtime Task 3 exact-SHA 公共关闭

- `0198fc9/32836430378` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；Task 3 正式关闭。
- `HANDOFF`：唯一下一动作切为 Task 4 媒体审计器与预算门 TDD；旧 V1 视觉、production media、视频模型/relay
  仍不准入。

## 2026-08-25：RQ-108 runtime Task 4 本地完成

- 新增只读媒体审计器、planned ledger 与 25 项合同测试；固定 source/codec/SSIM/seam/budget/anti-reference/toolchain
  边界。没有 adopted rendition、视频生成调用或外部上传。
- `NEXT`：独立 implementation/evidence commit 与 exact-SHA 三 job；公共成功前不进入 Task 5 bake-off。

## 2026-08-25：RQ-108 runtime Task 4 exact-SHA 公共关闭

- `52def9c`/`d58ba15`、Actions `32841900909` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；
  Task 4 正式关闭。首个 run `32841579832` 因 Ubuntu 缺 ffprobe 失败，随后只补 CI 工具安装，不放宽审计门。
- `HANDOFF`：唯一下一动作切为 Task 5 三路线 bake-off；官方优先、中转 secondary，先冻结映射/许可/隐私/费用/
  调用上限，再决定是否安装工具、创建 Key 或发起付费调用。

## 2026-08-25：RQ-122 候选广筛纠偏与 Task 5 隔离 spike

- `CORRECTION`：两个 A 线付费槽位不是封闭调研池；已广筛 DragonAPI 当前 Wan/Veo/Vidu/Kling/MiniMax/
  Seedance/Grok 等目录并与官方资料交叉核对。DragonAPI 缺 Wan 3.0 只影响 transport；用户官方 UI 证明
  `wan3.0-video` 邀测通过。`grok-video-3` 第三代 relay 条目存在，不因 xAI 公布的命名体系降回 1.5；专用 schema
  缺失仍诚实保留。
- `VETTING`：HyperFrames `general-video` skill as-is 因 online update/auth/provider 与默认 PostHog telemetry 被拒；
  Apache-2.0 renderer 只在 exact version、临时 HOME、no telemetry/no auth/no cloud 下准入一次隔离 spike。
- `SPIKE`：系统 Chrome profile singleton 两次失败后改用本机 cached headless shell，check 全绿；raw frame 重复
  SHA 精确一致、seam SSIM `0.999600`。默认 MP4 超 H.264 bytes 门且 decoded seam DSSIM `0.039327 > 0.03`，
  裁决 `renderer-conditional-pass/default-encoder-reject`，不形成生产媒体。
- `NEXT`：只做 Wan 3.0 官方 endpoint/region/Key presence body-free preflight；不先上传母图或调用模型。

## 2026-08-25：Task 5 candidate admission/spike exact-SHA 公共闭环

- `PUBLIC-CI`：`7067ea1/32862942549` 的 pytest、真实 PostgreSQL migrations/control-plane 与 Linux package
  smoke 三 job 全绿。
- `CLOSED-SCOPE`：候选准入与 HyperFrames 隔离 spike 批公开可复核；Task 5、RQ-108、8E 和生产媒体仍未关闭。
- `HANDOFF`：唯一下一动作进入 Wan 3.0 官方 endpoint/region/Key presence body-free preflight。

## 2026-08-26：RQ-124 Portal active source v2 migration

- `PUBLIC-PREDECESSOR`：executable preflight `7fe47db/32869447853` 三 job 全绿，但绑定 v1。
- `USER-CORRECTION`：用户指出 v1 点状碎光过密并签收轻清噪 edit；v2 SHA `8134c0ca...1a06e` 成为 active
  source，v1 保留 archival parent，强清噪与旧大水晶 edit 均 rejected。
- `LOCAL`：审计器/manifest/provenance/ADR/ledger/plan 与 exact path fallback test 已同步；focused 26 passed。
- `NEXT`：v2 source migration 独立 exact-SHA 公共门；绿灯前不上传或调用 Wan。

## 2026-08-26：Wan 3.0 Portal v2 单样本负面裁决

- `PUBLIC-PRECONDITION`：v2 migration `2a2da0e/32872452053` 三 job 全绿后才执行。
- `REAL-CALL`：一次有效 first-party Wan call，free quota 100%→73.33%，无重试/充值；UI 空 prompt/hydration
  预操作未形成 task，calls 0，不冒充模型结果。
- `REJECTED`：有效 output `030a60f...1f58a` 的 source→first、seam、coherent full-frame motion、水印与发布
  dimensions/fps/color metadata 未过门；不重抽 Wan。
- `NEXT`：负面证据独立 exact-SHA 公共门；随后严格进入 Dragon/Veo A2。

## 2026-08-26：Wan negative audit 公共闭环与 Veo 交接

- `PUBLIC-CI`：`69fc4ab/32876134114` 三 job 全绿；Wan rejection 取得公开 provenance。
- `HANDOFF`：唯一下一项为 DragonAPI `Veo3.1-quality-official`，同一 v2/prompt/scorecard，一次 POST、同 task
  poll/download、不自动重试；Key 仅在用户本地 secure prompt 中存在。

## 2026-08-26：Dragon/Veo A2 负面样本与 RQ-125 路线纠偏

- `REAL-CALL`：Dragon/Veo 一个 task、一 POST，成功/100%；`/content` 对成功 task 403，query result URL 恢复
  output，未重复生成。external video calls 累计 2，production media 0。
- `REJECTED-SAMPLE`：raw output 的 source→first `0.587962`、seam DSSIM `0.161631`、full-scene motion
  distribution、yuv444p/254MB 和预算未过门；转 yuv420p preview 只修复播放器兼容。
- `CORRECTION`：用户指出两次模型试用本身未完美利用，不能直接切路线。复核确认 lastFrame 字段正确，但
  prompt 大量重述画面且用多个 slow/subtle 词，与官方 motion-only I2V guidance 冲突。本样本不能代表 Veo/
  A 线上限。
- `CURRENT`：C 线成为优先 no-paid-call proof，而不是不可逆切换：先证明分层/mask/inpaint、整幕 motion、
  seam/source 和维护成本；不合格则以新采用门恢复一次校正 A comparator。其他视频模型不永久拒绝，也不再
  复制当前失败配置抽卡。
- `NEXT`：先以独立提交/exact-SHA 公共门关闭 Veo 样本审计，再进入 C proof。

## 2026-08-26：Veo sample audit exact-SHA 公共闭环

- `PUBLIC-CI`：`e79a76e/32918278259` 的 pytest、PostgreSQL migration/control-plane 与 Linux package 三 job
  全绿；Veo sample rejection、Dragon `/content` Bad Case 与 RQ-125 纠偏可公共复核。
- `HANDOFF`：唯一下一项为 no-paid-call C-line Portal proof；先冻结 scene graph、mask/inpaint、full-scene
  motion coverage、deterministic seam 与 corrected-A fallback gate，不先调用新模型或接入 runtime。

## 2026-08-26：C-line Portal proof 设计门

- `DESIGN`：比较校正 A、局部 CSS 与 hybrid scene graph；C 只获优先 proof。冻结 8 systems、192 帧闭合时钟、
  source/seam/region/grid/manual/budget 门、repo-excluded output 和 pass/fail/inconclusive verdict。
- `BOUNDARY`：设计批未写 composition/renderer/tests、未生成媒体、未调用模型；校正 A comparator 仍是 C proof
  失败后的唯一回退。
- `NEXT`：design 独立 exact-SHA 公共门；全绿后才开始 contract TDD。

## 2026-08-26：C-line proof design exact-SHA 公共闭环

- `PUBLIC-CI`：最终设计 `78ae6e3/32919447127` 三 job 全绿；`be75112` 仅因 EOF 空行 warning 被修订，不作
  最终门。
- `HANDOFF`：implementation 正式进入 strict contract → deterministic scene graph → isolated renderer；
  不调用模型、不接 runtime，样片仍为 research-only。

## 2026-08-26：C-line overlay proof 失败与 RQ-126

- `IMPLEMENTED`：contract/8-system composition/isolated renderer/6 tests 与真实 v3 研究样片完成；external calls 0。
- `MECHANICAL`：raw clock byte-exact、seam/grid/bytes 可控；这些只证明 frame engineering。
- `REJECTED`：用户正确指出实际视觉仍是母图上叠加诡异线条/圆环/节点，不是图和环境自身全局运动；不得拿
  metrics 追绿。裁决 `proof_fail_reopen_corrected_a`，停止 C overlay 微调。
- `NEXT`：先公共关闭负面 proof；随后一次 corrected A comparator，first-frame only + short motion-only +
  clearly perceptible full-scene environmental motion，seam 后处理。

## 2026-08-26：RQ-127 全幕 breathing 与 cool 动态校准

- `CORRECTION`：全局不是三个主体更明显，也不是每格有像素变化；是 near/mid/far、left/center/right 的体积
  空气、环境光、建筑/地面/反射、道路、Rift、水晶和整片星空同时持续参与。
- `CURRENT`：corrected Veo 使用 medium-to-strong、clearly perceptible、dramatic/cool motion-only direction；
  允许构图锚定的小幅 camera float/parallax，禁止 static large regions、焦点轮流、HUD 与过轻动作。MotionSites/
  B站只作观感 reference，不复制资产/Prompt/源码。

## 2026-08-26：C proof 公共关闭与 corrected A executable preflight

- `PUBLIC-CI`：portable fix `557dac1/32923151197` 三 job 全绿；`e215f7e/32922688081` 的 Linux fixture failure
  保留，不把首个红 run 隐藏。
- `PREFLIGHT`：冻结 first-only/no lastFrame、819B positive、357B negative、one-POST runner 三 digest，PowerShell
  parse pass；motion-only 与 RQ-127 全幕强度门一致。
- `NEXT`：preflight 独立 exact-SHA；绿灯后才启动 secure Key runner 创建一次 corrected Veo task。

## 2026-08-26：Corrected Veo upstream failure 与 Vidu Q3 Pro 交接

- `LIVE-FAILED`：corrected Veo one POST 在 158s/100% 后 `task processing failed`，无 output；不把 transport/upstream
  failure写成 motion quality，按首错停止不重跑。external calls 3，production media 0。
- `PREFLIGHT`：Vidu Q3 Pro 文档明确单 image first-frame、8s/1080p、audio false；motion-only/full-scene prompt、
  seed 127 与 one-POST runner digests 已冻结，不用 opaque metadata。
- `NEXT`：合并 failure/preflight 独立 exact-SHA；全绿后一次 Vidu task。

## 2026-08-26：RQ-128 failure adjudication 纠偏

- `CORRECTION`：禁止把单次失败直接归因成 Provider/工具/方法错误。依次检查 local runner、request schema、
  relay/upstream、successful-output quality、跨样本 method；无 output 时 quality unknown。
- `CURRENT`：Vidu 是控制变量 comparator，不是放弃 Veo/first-only。若 Vidu 也 generic failed，停止换模型并
  审计 relay/request；只有明确修复或新可证伪假设才允许重试，避免 blind retry 与无界死磕。

## 2026-08-26：Vidu generic failure 与 minimal request gate

- `LIVE-FAILED`：Vidu one POST queued 160s 后 generic failed，无 output/quality unknown；calls 4。
- `FAULT-TREE`：source URL、auth/create、model ID/core schema 正常；两个不同模型 first-only 在同 relay 同形失败，
  优先 request/relay/upstream，不评价方法。
- `STUDIO-EVIDENCE`：登录态 UI 证明 Vidu first-only/8s/1080p/16:9，但 audio 固定 true；提示词增强已关闭，
  预计 5.28 并获用户确认。UI 上传 chooser 连接失败，未形成任务或扣费。
- `NEXT`：只执行一次 Studio-contract Vidu request：删除 seed、audio=true，其他变量不变。若仍 generic failed，
  停止换模型/API retry，转 Dragon task-id/official transport 诊断。

## 2026-08-26：Vidu completed sample 与 RQ-129 refined locked-scene

- `LIVE-COMPLETED`：audio=true/no-seed 后 Vidu 成功，证明 API/image/first-only/prompt 可用；此前 failures 至少与
  request/relay mapping 有关。
- `REJECTED-SAMPLE`：Vidu 主要以 camera push/global drift 制造全帧变化，source/seam/resolution provenance
  也失败；只拒绝 sample，不拒绝模型。
- `CURRENT`：目标是 locked-frame refined in-scene motion，不是仅加强 Veo v1。下一最小变量实验保持成功
  Veo first=last/model/transport/source，只改 multi-depth/material-aware refined storyboard；Seedance 2.5 后继，
  Grok 等 exact mapping/schema。

## 2026-08-26：Veo refined submit 403 账单/权限门

- `LIVE-SUBMIT-REJECTED`：refined Veo 在 POST 阶段直接 403，task_id 为空，无 output/quality unknown；与已有 task
  的 `/content` 403 不同。
- `EVIDENCE`：common log 已证实当时余额 `$15.008`、需要预扣 `$19.712`，故 403 为预扣失败；文档 402/实现
  403 仍不一致。task log 保持原 4 项，无隐藏 task。用户充值后余额为 `$65.01`。
- `RQ-130`：用户要求付费前的“万事俱备”同时包含提示词/约束尽量理想。v5 spatial-orchestration 按官方
  motion-only/单一场景/negative phenomena 收敛，并固定 locked/deep-focus/source-linework、3×3+三深度同时运动、
  八秒闭环、source/schema/runner/唯一路径门。
- `CURRENT`：先独立 commit/push/exact-SHA 三 job；公共成功后 one POST/no retry。余额 ready 不得绕过内容门。

## 2026-08-26：Veo spatial v5 无输出上游失败

- `PUBLIC-PREFLIGHT`：`d57b026/32951125621` 三 job全绿。
- `LIVE-UPSTREAM-FAILED`：唯一 task `task_I5...k9Mw` one POST，159s/100% generic failed；无 output，quality unknown。
- `BILLING`：`$19.712` 预扣后同额异步退款，最终钱包 `$67.01`；calls 6、production media 0。
- `INCIDENT`：本地父终端在用户输入后被误关，子 runner 已 POST 后退出；无第二 POST，status 按远端终态更正。
- `CURRENT`：先公共关闭审计；不重发、不把失败归因 prompt/model/method、不立即换模型。
- `PUBLIC-CLOSED`：`ac76f74/32952793297` 三 job 全绿；下一项为 zero-cost task-id/platform diagnosis decision
  gate，只准备 body-free packet，不自动联系支持或产生新调用。
- `RQ-131`：support packet/QQ 草稿已准备但未发送；用户选择 Studio 手动生成。参数保持同一 Veo/v2 first+last/
  8s/1080p/16:9/v5 目标，enhancement off；用户本人上传/点击 19.71 生成。自动 upload 失败时不改权限或替用户扣费。
- `V5-STUDIO-FAILED`：`task_Rdr...maHP` 93s/100% generic failed/no output，19.712 全退；排除自写 runner 为必要根因。
- `RQ-132`：用户拒绝 QQ 支持并授权一次 exact v1 Studio reproduction。只复现早期成功 prompt/参数，以区分
  当前通道变化与 full-frame medium/strong constraint；no retry。
- `V1-RESULT`：`task_v8g...PDW9` 81s/100% generic failed/no output、19.712 全退；Veo 当前通道暂停。
- `SEEDANCE-PREFLIGHT`：first+last/8s/720p/no-audio/v5/2 images 已 readback；按钮 price `--`，catalog 推导
  11.9568。用户接受 price mismatch 前不提交；Kling fallback、Grok 无尾帧 reject。
- `SEEDANCE-CLIENT-BAD-CASE`：首次 submit no task/no charge，以 TaskTypeConstraint 拒绝显式 ratio。Studio 已改
  `adaptive`，其余变量不变；重新 2/2/public gate 后只允许一次修复提交。
- `SEEDANCE-SUCCESS-CANDIDATE`：`task_w6...ULvW` 137s/100% success、11.9566；Studio result-fetch 403 由同 task
  GET-only 恢复。locked camera/full-scene direction promising，但 source-first 0.864923、seam diff 0.060443、720p
  未过门；先用户 visual review，再决定 no-generation postprocess proof。
- `SEEDANCE-EDIT-400`：RQ-133 v6.1 source GET 成功后，POST 在 task 创建前 HTTP 400；费用 0、task id 空、
  task log 无隐藏任务。原 runner 丢失 response body，旧 ratio common-log 行不得冒充。strict body-free sanitizer
  三项 red→green、revised runner no-I/O self-test 已完成，尚未重试。
- `OFFICIAL-JIMENG-PREFLIGHT`：即梦官方五模式只读比较后，Seedance 2.5 `智能编辑` 的单 MP4/MOV edit 槽、
  多参考槽、自动比例/时长和 720P 最贴合 Video1+Image1；全能参考/首尾帧会重生成，智能多帧当前为 1.0 Fast，
  超长视频 30s。未上传/购买/生成；先公共关闭诊断，后续只在读回实际积分/参数后决定一次官方 edit。
- `DOUBAO-COMPARATOR`：豆包工作标准套餐 only one Seedance 2.5 task completed；Skill 无 video-to-video，实际
  抽 Video1 首尾帧 + Image1 做 image-to-video。输出 `e4b2f91...352cf`、720p/24fps/8.041667s/AAC/移动水印；
  source-first `0.407604`、seam diff `0.144582`。宽暖金光轨沿道路/结构运动有局部启发，但重绘 source、三主体
  内部与全局环境 motion stack 不完整，sample rejected/no retry。calls 10、production media 0。
- `RQ-134`：下一即梦 Smart Edit 必须同时强化 left Rift、center crystal/platform、right constellation/field，
  右侧单列 hard gate；建筑/道路/地面反射/云与空气/星空纵深也须同步增强。光轨改为冷蓝/青蓝主色、暖金低占比，
  只作为一层而非全部效果。文件选择改由用户执行，Codex 负责上传后的费用/参数/prompt readback。
- `RQ-135/JIMENG-V7`：即梦第一轮只用成功 MP4 + immutable v2 PNG，不追加审美概念图；高级编辑区域框选
  优先于第三图。v7 prompt 1,439 chars/4,115 bytes/SHA `edbc0d3...6f388` 已冻结。Chrome 插件重装/重启后
  general connection 恢复，但即梦页仍页面级读控超时；file picker 由用户，当前先 exact-SHA 公共关闭 preflight。

## 2026-08-27：official 即梦 Smart Edit 与零费用后处理结果

- `ORDER-DEVIATION`：用户在 400/豆包/即梦 preflight batch 尚未取得 exact-SHA 公共闭环时手动生成；事实顺序
  原样披露，不改写为 public-gate-first。
- `ACTUAL-PROMPT`：页面 2,000 字上限使 main prompt 压缩为 534 chars/SHA `d003f047...cff10`，三个 timestamp
  instruction 有独立 digest；长版 `edbc0d3...6f388` 继续作为 design intent，不能冒充实际请求。
- `LIVE-OUTPUT`：official Smart Edit raw SHA `4d3660b...155b`；三大区/九宫格均变化、camera/建筑初审稳定，
  但 v2→first `0.889072`、seam `0.046536`、AAC 与 non-fixed-fps fail。calls `11`、production media `0`。
- `POSTPROCESS`：fixed24/no-audio/BT.709/bytes 可修；最佳 J SHA `dadd7c3...a0b37`、seam `0.042684` 仍高于
  `0.03` 且 mother-first 降至 `0.849216`。停止普通 crossfade/settle 追绿，所有 outputs 留 repo-excluded。
- `NEXT`：先完成本 diagnosis/preflight/result evidence batch 的本地门、提交与 exact-SHA 三 job；公共成功后
  做 no-cost geometry/material/energy identity fault split。不先付费重抽、不接 runtime、不进入 Account。
- `RQ-137/SEQUENCE`：用户明确先把 Portal 做好；GLM-5.3/Flash migration gate 不插入当前脏批，改为 Portal
  Motion Polish 正式闭环后的高优先横向项。该顺序不降低媒体门、不授权无界调用，也不把 bounded Coach/8F
  标成完成。
## 2026-08-27：RQ-138 Portal motion direction revision

- Task 5 的公共 evidence 与 T/X identity split 已完成，但用户明确拒绝继续沿用当前视频节奏；“全局”重新定义为
  左/中/右与 near/mid/far 全程重叠、稳定、可感知的景内材质运动，而不是 burst、雾层或局部变亮。
- AutoGLM 三张文生图只作反例；Image2 只在代理恢复后对确认母图做 image-to-image 静态方向稿。即梦当前页面显示
  “全能参考”可混合最多 50 个图/文/音/视频输入，故不把它当严格 Video1 temporal edit。
- 下一校正视频先用首帧单锚点；首尾帧作为后置对照。新 source-side brief 未通过静态门前不重生成、不接 runtime。

## 2026-08-27：RQ-141 Seedance v3 motion contract correction

## 2026-08-28：RQ-143 masked-inpaint proof 与 RQ-144 Wan 官方重开

- RQ-143 的 bounded Rift proof 使用局部 ImageGen 背板 + 独立 RGBA 流体层；遮罩/编码机械门通过，但视觉像廉价蓝带，判 `research-proof-rejected`，不再通过 opacity 或通用 plate 数量追绿。
- 用户随后明确要求重新公平测试此前未充分利用的 Wan 3.0 官方通道。RQ-144 冻结 first-frame-only、adaptive、1080P、12s、audio/prompt_extend/watermark off、motion-only brief；同图 last-frame 不再使用。先做同区 endpoint/额度/价格与 SHA 预检，再只允许一次 POST；不自动重试、不接 runtime，结果仍需三大区/near-mid-far 与人工材质运动门。

- `LIVE-OUTPUT`：DragonAPI `seedance-2-5` first-frame-only v3 任务 `task_kOu...v6tW` 已完成并由 GET-only
  recovery 下载；12.041667s、1280×720、24fps、H.264/yuv420p、无音轨，唯一生成 POST，恢复阶段 POST 为 0。
- `VISUAL-REJECTED`：左 Rift 从小旋涡变成硬同心环；道路/裂隙下方流动在前段缺失；中央中段出现过曝白闪与横向穿屏线；右侧非 burst 时近乎静止；near/mid/far 没有稳定的全幕呼吸；末帧与开场相位仍不够接近。该结果只证明这次请求产生了可审查输出，不证明模型或方法已达标。
- `CURRENT`：下一候选必须先重写 brief：基础运动从首帧持续到末帧，burst 只做中央上下贯穿的低幅、约 2–3s 呼吸式蓄放，左/中/右和环境层在 burst 前后保持同级可感知；禁止跨画面直线联动、HUD 式线条、过曝闪白与 burst-only 右侧。未完成 source/loop/visual contract 前不再付费重抽、不接 runtime。

## 2026-08-29：RQ-155 全量来源池复查落到 Portal 机制

- `SOURCE-REVIEW`：按用户提醒重新回读此前整理的官方设计、视觉 gallery、MotionSites/组件库、电竞数据、
  Agent observability、Training、原型和素材制片来源。每个来源现在都绑定具体消费者与采用门，而不是只列
  名称；Portal 本轮只取 Riot/Universe 语义、构图/字阶参照和可逆局部交互机制。
- `IMPLEMENTATION-BOUNDARY`：地区卡 spotlight/菱形标记、poster crossfade、localized activation aperture、
  详细徽章 fallback 与 Account 状态 tint 均沿用现有 React/CSS，无新依赖；OP.GG、Trace、Training、Timeline
  的专属视觉与数据语义保持后置，production media 仍为 0。

## 2026-08-29：RQ-156 补齐细粒度 source provenance 与 handoff 恢复

- 历史复查补登记 Design Prompts、PPT/Photoshop/After Effects、Radix/shadcn、ECharts/Tremor/visx、
  Tailwind Plus/Untitled UI、League Displays/Wallpaper Engine/Steam Workshop 及无 consumer 的旧检索 lead；
  每项都绑定用途、许可/预览状态、性能与撤出门，不因“广撒网”引入依赖或购买受限模板。
- Portal/Account 代码只增加两项可逆落点：所有已有本地细徽记的渐进显示/Universe fallback，以及带
  `from=wallpaper-lab` 的受限 Account URL，使刷新/复制链接仍保留返回地区选择语义。工作台 source 消费者与
  `production_media=0` 不变。

## 2026-08-29：RQ-156 Portal/Account UI contract hardening

- 细化同一批实现证据：新建地区链接统一使用显式
  `?surface=wallpaper-lab&region=...`；旧 `?region=...` 只作为受限兼容别名，未知
  query/stage/region 仍 fail-closed。Account 的 `from=wallpaper-lab` 返回标记、
  `pushState`/`popstate` scroll reset 与 generation-bound activation 共同保证复制、
  刷新和返回不会丢地区或带入旧滚动位置；Portal 选区对当前 entry 做 `replaceState`，不制造
  瞬时历史层级。1000–1199px 短桌面使用三列、<=420px 手机使用单列，避免地区文案被压扁；长页面的视觉层固定在 viewport，
  不随 atlas 文档高度裁切或滚动漂移。
- Portal/Auth/地区选择器补齐 semantic `main`/labelled section、skip/heading focus、
  pressed/current/disabled 状态和 intrinsic media dimensions；WebM→MP4→poster、
  mobile/reduced-motion/error fallback 与细徽记 Universe fallback 仍保持研究候选边界。
- 该 hardening 不改变主阶段/检查点、默认 `/`、Workbench 顺序或 `production_media=0`，
  也不把未核验壁纸或旧 anti-reference 资产升级为 adopted media。

## 2026-08-29：RQ-157/158 地区 Focus Rail 与 handoff 修订

- 用户用新视觉裁决取代 RQ-154/156 中旧的 compact atlas/card-grid 表现：13 个地区 identity 全部可选，简单 Universe
  crest 进入横向 rail，高细节本地研究徽章只进入 selected hero，scene-preview 缩略图和右下角小 CTA 删除。
- CTA 固定为 `进入登录界面`/`Continue to sign in`；Portal→Account 改为 selected identity 驱动的 bounded handoff，
  Bandle Account 使用新静态候选。该修订不把 13 区 identity 解释成 13 份 adopted motion、不改变 Riot routing、
  Workbench 顺序、主阶段或 `production_media=0`。

## 2026-08-29：RQ-159 地区叙事文案与登录交接收口

- 13 个 presentation region 改用各自独立的中英双语氛围句；它们是 RiftCoach 基于地区设定编写的产品文案，
  不冒充 Riot 官方句子或英雄逐字台词。地区选择、登录页与无障碍名称不再显示“动态素材、本地候选、分辨率、
  时长”等内部媒体审计语言。
- Portal→Account 交接由 shared journey shell 显式驱动 `closing → background-handoff → idle`，选中地区附近的
  aperture 接管画面，随后 Account 背景、地区身份和表单分层进入；focus 只在目标表面可接收后移动，reduced-motion
  立即提交。该本地收口不碰 Workbench，不改变主阶段、媒体权利门或 `production_media=0`。

## 2026-08-29：RQ-160 Portal/Account 标题改为受控双语分行

- Portal 不再保留“先选一处落脚点”，也不依赖 viewport 触发随机折行；中文固定为 `从一方之地，`／`启程。`，
  英文固定为 `Begin from a region`／`of your choice.`。
- Account 标题同步改为中文 `选择一位`／`召唤师。`、英文 `Choose a`／`player.`。视觉行与完整无障碍 heading
  名称分离，桌面和 390px 中英文均通过无溢出复核。该修订只收口 Portal/Account typography，不改变 Workbench、
  Auth、路由、媒体权利门或 `production_media=0`。

## 2026-08-30：RQ-161 Account panel 与原生控件字阶修补

- Account 右侧 panel 在桌面使用不干扰 handoff transform 的受控 `top` 上移，移动端回到 `top: 0`；这样只校正
  页面构图，不改变转场时序或路由。
- Riot ID input、查询区域 select、账号关系 select 统一 Manrope/560/0.95rem，三条字段 caption 统一字阶；
  新增浏览器 computed-style 回归覆盖桌面上移、移动端归零和三控件一致性。unit `297/297`、E2E `50/50`、
  typecheck/build 与治理门通过。该微调不扩展 8E、不碰 Workbench，也不提升任何媒体采用状态。

## 2026-08-30：RQ-162 Void crest 与 Portal/Account 透明度修补

- 将用户提供的官方虚空徽章候选接入详细徽章映射，保留 Universe crest 作为失败回退；本地资源仍受 provenance/许可门约束。
- Portal atlas 与 Account panel 改为更透的分层表面，Account 地区背景的亮度与氛围遮罩同步回调，使背景保持可见；只改视觉层，不改变 handoff、Auth、路由或 Workbench。

## 2026-08-31：RQ-163 Portal/Account 收口后交回 Agent 主线

- 用户确认 Portal/Account 当前视觉切片已达到可收口点，执行重点转回 Agent；这不是 8E 关闭，也不把研究媒体、Auth 或公网部署升级为生产能力。
- 新的交接批只做事实和文档对齐：README 补充 8A–8D 的 Agent/Runtime/Evidence 完成边界、8E 开放任务、GLM-5.3 G53-0 至 G53-4 闸门和受限 Review Coach 缺口；新增计划与八维学习 walkthrough。
- 后续候选顺序为 G53-0 → G53-4 → 受限 Coach → Data Dragon/Evidence/Trace/Training → OP.GG breadth/黄金切片 → 安全部署合规 → 8E 退出 → 8F；旧 RQ-154 两地区/第三地区动作由 RQ-157–162 取代，Workbench 和 `production_media=0` 保持不变。

## 2026-08-31：RQ-164 G53-0 无 I/O 审计停点

- `EVIDENCE`：本地只读核对确认产品默认仍是 `zhipu`/`glm-5.2`，现有 Zhipu Adapter 与探针固定
  `thinking=disabled`；历史 Zhipu 结果均属于 GLM-5.2，不能外推 GLM-5.3。
- `CONFIG`：被忽略的本机 `.env` 仅做遮罩式非敏感字段检查，Key 未输出/记录；其中 `LLM_PROVIDER=glm` 与当前
  `load_zhipu_settings()` 要求的 `zhipu` 不一致。该配置接缝不授权修改用户 `.env`。
- `BOUNDARY`：账号/Plan 权限、实际 endpoint/region、正式 GLM-5.3 model ID 与 `enabled + low` 可用性没有当前
  可核验的非敏感证据。用户历史线索与旧文档“API 尚未上线”快照均只作为待核对资料，不能判定当前准入。
- `DECISION`：G53-0 标记为 `completed-local / adoption blocked-deferred`；不读取 Key、不调用 Provider、不改默认
  模型、不改 `app/`/`web/`。获得非敏感账户证据后，才另行授权 G53-1 离线 profile TDD。

## 2026-08-31：RQ-165 G53-1 普通 API 适配档案离线 TDD

- `CONTRACT`：用户核对智谱公开资料后确认采用普通 API，不套用 Coding Plan；普通基址为
  `https://open.bigmodel.cn/api/paas/v4/`，Flash 正式模型标识为 `glm-5.3-flash`。
- `IMPLEMENTATION`：新增不可变、按精确模型选择的 thinking profile；GLM-5.2 保留
  `thinking=disabled`，GLM-5.3/Flash 使用 `enabled + low`。Provider、受控 capability probe
  和 CLI 共享档案，已知模型的诊断产物隔离命名，未知测试模型保留安全历史回退。
- `BOUNDARY`：Flash 文本/结构化响应的非空 reasoning 只在适配器内消费并丢弃；非字符串或工具回合
  reasoning 继续 fail closed。未扩展中立消息、多模态或流式合同，不改默认模型、`.env`、Workbench、
  Auth、路由或 `production_media=0`。
- `EVIDENCE`：新增 profile/provider/probe/CLI 离线测试，聚焦回归 `70 passed, 29 subtests passed`，
  `compileall`、`git diff --check` 与治理检查通过；无 Key 读取/输出和真实 Provider/Riot/OP.GG 调用。
- `NEXT`：仅推进 `g53-2-exact-sha-ci`；CI 和后续明确授权前，不把本地绿灯写成生产准入或领域质量证据。

## 2026-08-31：RQ-166 G53-2 exact-SHA 公共 CI

- `IMPLEMENTATION`：G53-1 的 9 个 Provider/配置/probe/CLI/测试文件被隔离为提交
  `0f97b92683e4981842e745a695864deb611bb630`，没有混入 Portal、Account、Workbench、截图、资产或其它脏文档。
- `PUBLIC-VERIFIED`：Actions run `33325222755` 的 head SHA 精确匹配；`pytest`、`postgres-migrations`、
  `packaging-smoke` 三个 job 均 `completed/success`，公共 pytest 汇总为
  `1912 passed, 145 skipped, 1 warning, 127 subtests passed`。
- `BOUNDARY`：现有 workflow 已足够，未新增 job；CI 全程 no-I/O，没有读取/输出 Key 或真实 Provider/Riot/OP.GG
  调用，不改默认模型、`.env`、Workbench、Auth、路由或 `production_media=0`。该结果只关闭 G53-2，
  不等于账号权限、真实协议、领域质量或生产成熟度。
- `NEXT`：等待用户独立授权 `g53-3-bounded-protocol-gate`（最多三次真实协议调用）；G53-4、完整 8E 和 8F 仍未完成。

## 2026-08-31：RQ-167 G53-3 有界协议门首次尝试

- `AUTHORIZATION`：用户以“继续”明确授权本批最多三次真实普通 API 调用；使用进程级临时覆盖，未改 `.env`、
  默认 `zhipu`/`glm-5.2` 或任何前端/Workbench 代码。
- `RESULT`：`adapter_protocol` 的 A1 结构化合同第 1 次调用返回脱敏 `authentication_failed`；A2 tool round trip
  按 runner 合同跳过，`calls_used=1/3`、`admitted=false`。OpenAI client 重试为 0，没有第二次或第三次调用。
- `EVIDENCE`：脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol.json` 已通过
  `AdapterProtocolSliceReport` schema 校验，SHA-256 为 `b10827f18dc810085a0d3883ebb7175709f4c244c30c937d5d220ab1ec1d0d9a`；
  只含状态、错误码、调用数、计量和哈希，不含正文、reasoning 或 Key。
- `BOUNDARY`：该错误码合并了认证失败/权限拒绝，不能单独区分 Key、账户权限或端点接缝，也没有产生模型质量证据。
  不把 G53-3 标为通过，不启动 G53-4；下一步等待用户确认凭证接缝并另行决定是否重开。

## 2026-08-31：RQ-168/169 G53-3 凭证修正与重开通过

- 用户确认前次 Key 已删除，重新创建普通 API Key，并修正本机 `.env` 的 `zhipu`、普通端点和
  `glm-5.3-flash` 配置；没有把 Key 值写入仓库或结果。
- 重开使用固定 3-call 预算且 client 重试为 0：A1 结构化合同通过，A2 Agent 工具往返通过（1 次 ToolCall/执行），
  `calls_used=3/3`、`admitted=true`。脱敏结果 `zhipu_glm53_flash_adapter_protocol_retry2.json` 的 SHA-256 为
  `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`，schema 与聚焦回归 `36 passed`。
- 该结果只关闭 G53-3 普通协议接缝，不代表领域质量、默认切换、生产媒体或 8E/8F 完成；G53-4 仍需单独授权。

## 2026-08-31：RQ-170 G53-4 新鲜领域门本地拒绝

- 用户在 G53-3 通过后明确授权一次真实 GLM-5.3-Flash 领域门。执行前先完成 no-I/O preflight，校验全新匿名
  三案例 Dataset、Input Plan、Prompt/Context snapshot、协议结果、代码/CI 身份和不可覆盖输出路径；预检外部调用为 `0`。
- 真实运行严格按最多 12 次领域调用、每案最多 4 次、总 Token 12,000、无重试/无修订、首错停止执行。首案第 1 次
  Provider 响应含并行 ToolCall，当前 Zhipu Adapter 以 `unsupported_parallel_tool_calls` fail closed；没有工具执行、
  RAG/Evidence、Evaluation 或发布，后两案跳过。领域 `1/12` calls、`0` normalized tokens，累计含 G53-3 为 `4/15`、
  `1115` tokens，费用记为 `unknown`。
- 脱敏结果不可覆盖，文件 SHA-256 为 `ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`；
  结果不含 Key、Prompt/响应正文、reasoning、完整请求标识或注入 marker。G53-4 标记 `completed-local-rejected`，
  不是 public CI 关闭，也不触发默认模型切换；不自动重跑当前考卷，Workbench/Auth/前端与 `production_media=0` 不变。

## 2026-08-31：RQ-171 GLM-5.3-Flash 适配器修复与 G53-5 待执行

- `CONTRACT`：旧 G53-4 的 `unsupported_parallel_tool_calls` 首错被复核为中立适配器的批量 ToolCall 接缝，
  不能单独推出 GLM-5.3-Flash 的一般质量；旧考卷与结果保持不可变。
- `IMPLEMENTATION`：Flash profile 统一为 `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`；
  `reasoning_content` 只在内部消息/工具回放链路保留，公开投影不泄漏；多个 ToolCall 按 API 顺序由 AgentLoop
  逐个受控执行，能力声明仍不承诺并发。
- `BOUNDARY`：本地离线合同/回归已完成，但新的 `g53-5-fresh-flash-capability-gate` 真实 Provider 全范围
  测试仍 pending。G53-5 需新实验身份、唯一脱敏输出路径和有界预算，不重跑 G53-4，不改默认模型、`.env`、
  Workbench、Auth、前端或 `production_media=0`。

## 2026-08-31：RQ-172 G53-5 全能力矩阵本地真实观察

- `RESULT`：新的 `g53-5-fresh-flash-capability-matrix-v1` 在 dirty worktree 上完成 `11/11` 次真实调用、
  `46,151` tokens，8 个案例中 `7/8` 通过；结果文件为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_capability_matrix_v1.json`，
  SHA-256 `BFFF564CF4C6E7B2DD05F88542FD7A872D1565442B6D35C795EC6892CC84BE0C`。
- `EVIDENCE`：adapter_core、AgentLoop 的有序多 ToolCall/思考回放、domain development、vendor text stream
  与 vendor multimodal 均观察通过。F7 vendor tool_stream 在 `max_tokens=512` 以
  `incomplete_chat_response`/`length` 结束，不足以证伪能力；F4 `cached_input_tokens=0`、`cache_status=unproven`，
  不宣称缓存命中；F8 仅是 vendor-only 观察。
- `BOUNDARY`：结果标记 `production_admitted=false`、`public_ci_confirmed=false`；HEAD 与 `origin/main` 均为
  `0f97b92683e4981842e745a695864deb611bb630`，工作树保持 dirty。该观察不关闭 Stage 8/8E、公共 CI、领域采用、
  安全部署或生产成熟度；下一步等待用户决定 Agent 主线下一项，不重跑 G53-4，不改默认模型、Workbench、Auth、
  前端或 `production_media=0`。

## 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

- `DIAGNOSIS`：为定位 RQ-172 F7 在 `max_tokens=512` 下的 `incomplete_chat_response`/`length`，新建独立
  follow-up；唯一改动是把 `max_tokens` 从 512 调至 2048，不修改或覆盖 RQ-172/旧结果。
- `RESULT`：experiment_id `49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`，唯一 `1/1`
  调用、`557` tokens、`finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source
  identity stable、`cached=0`。结果文件为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json`，SHA-256
  `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`；父矩阵 experiment
  `4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`、父结果 SHA
  `bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。
- `BOUNDARY`：结果标记 `vendor_raw_transport_only`、`production_admitted=false`、`public_ci_confirmed=false`；
  不证明 provider-neutral streaming、Agent 生产、领域采用或公共 CI。Stage 8/8E 继续 `in_progress`，下一步等待用户
  决定 Agent 主线下一项；不改默认模型、Workbench、Auth、前端或 `production_media=0`。

## 2026-08-31：RQ-175 GLM-5.3-Flash 专属运行时档案

- `DECISION`：旧 G53-6 的 30 秒执行截止和 512/1024 输出上限不能直接当作 Flash 的模型能力结论；为精确
  `zhipu/glm-5.3-flash` 建立独立、版本化的运行时档案。官方 Flash 文档给出的推荐采样为
  `temperature=1`、`top_p=0.95`、`reasoning_effort=max`、`thinking.type=enabled`、
  `clear_thinking=false`，项目将其与受控执行预算分开记录。
- `IMPLEMENTATION`：档案在 Agent 编译、AgentLoop、`llm.chat`、G53 预算包装器和 Provider 构造间显式传递；
  本地 profile 使用 Agent/工具 90 秒、传输 120 秒和 2048 输出上限，超出请求只能被截断到档案上限，不能由
  模型或调用方升权。GLM-5.2、未知模型和无档案调用继续走旧路径。
- `BOUNDARY`：这是 G53-7 evaluation-only 接缝，不是默认生产 Runtime 切换；旧领域 JSON 保持只读兼容，
  新真实运行必须在该实现取得 exact-SHA 公共 CI、在同一新 SHA 上重新取得 G53-3 协议证据且工作树干净后
  另建证据。默认结果路径为独立的
  `zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`；旧 held-out Dataset 的 30 秒仍是
  质量资源阈值，不是新 Provider 执行截止；若需取消，必须另冻 Dataset/Plan 版本。Stage 8/8E、Workbench、
  Portal/Account、Auth、路由和 `production_media=0` 均不变。

## 2026-08-31：RQ-176 Flash-only 产品运行时晋级（本地接线）

- `DECISION`：用户明确选择普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品正常运行目标，不再等待 Pro/Flash
  横向比较；GLM-5.2 仅保留为显式兼容/应急回退。旧 G53-3、G53-4、G53-5、G53-6 证据保持不可变。
- `IMPLEMENTATION`：唯一注册的 `glm-5.3-flash-runtime-v1` 已从产品组合根显式传入 Worker、Runtime、Agent/工具/
  Harness、Provider、Runtime policy 和 Trace identity；已绑定同一注册档案的 concrete Provider 可在组合阶段安全
  自动推断，未绑定时 Root、Factory、Runtime 三层对精确 Flash 提前 fail-fast，避免编译器继续使用 30 秒策略而
  Runtime 偷偷升级到 90 秒。Flash 执行窗为 90 秒、传输 120 秒、
  输出上限 2048、`temperature=1`、`top_p=0.95`、SDK retries=0；Skill 的 30 秒质量门独立保留，Worker
  lease/heartbeat 默认 360/60 秒。
- `TEMPLATE`：`.env.example` 与 Compose 模板已对齐 Flash；真实 `.env` 未由本批修改。Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 不变。
- `BOUNDARY`：本地接线和回归不等于公共生产准入。工作树仍 dirty，不能复用旧提交的 G53-3；需先取得新实现的
  exact-SHA 公共 CI，在同一 SHA 重取 G53-3，再单独执行 G53-7、完整黄金切片和安全/部署/合规收口。

## 2026-08-31：RQ-177/178 G53-3 证据分离与 G53-7 A/B 身份预检

RQ-177 的新协议证据仍绑定实现提交 A=`f0d5ee2…`；脱敏结果提交 B=`407ee75…` 的 canonical-LF
摘要为 `1fda5b…`（Windows CRLF 工作副本摘要 `6c6e…` 只作环境说明）。RQ-178 新增无 I/O
`GLM53ABIdentityBinding` 与 schema 1.1 admission：A 的实现/CI/协议 `code_sha`、B 的独立 CI、当前
`HEAD=B`、B 的 Git blob 与工作树摘要必须一致，且 B 只能新增 capability-result 文件，不得改写既有证据。
该本地接缝已通过身份绑定及相邻回归（`53 passed`）；当时尚未冻结新的 A′（历史状态，已由 RQ-179
更新），Stage 8/8E、生产准入和 `production_media=0` 均不变。

## 2026-08-31：RQ-179 最终实现 A exact-SHA 公共冻结

RQ-178 的身份实现最终冻结为 A=`9e6d78be51c3a5c512b67f83d2849f9b1261cf77`；Actions run
`33378687984` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 全绿且 `head_sha=A`。较早候选
`fe7d577…`/`3ccd827…` 分别暴露历史 HEAD fixture 与浅克隆缺 Git 历史，失败 runs 保留。该修正只完善证据身份的
公共验证环境，不完成新 G53-3、证据 B、G53-7、黄金切片或生产部署；下一项仍是干净 A 上重取协议并只新增 B。

## 2026-08-31：RQ-180 G53-7 首次真实领域尝试

- `AUTHORIZATION`：RQ-179 的实现 A、同 SHA G53-3 与证据 B 的 exact-SHA 公共 CI 完成后，用户明确授权“继续/授权”执行一次 G53-7。
- `RESULT`：在干净 LF checkout 上只执行一次；协议 3/3，领域 2/12，累计 5/15 calls、领域 3505 tokens、
  墙钟 36625ms。首例 `flash_gate_baseline_01` 以 `provider_response_invalid` / `incomplete_chat_response`
  停止，后两例按首错跳过，`admitted=false`。
- `EVIDENCE`：脱敏结果路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`，
  canonical-LF SHA-256=`21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment
  `236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；随后由本地 C=`9157cde…` 承载，C 未推送、无公共 CI。
- `BOUNDARY`：安全聚合码不包含底层 vendor finish reason，不能将其解释为 `length`；Key、Prompt、响应正文和 reasoning
  未保存。该尝试不产生领域或生产准入，Stage 8/8E 继续 `in_progress`，Portal/Account/Workbench/Auth/路由及
  `production_media=0` 不变；停止自动重试，后续若继续必须另立版本化响应完成/截断诊断。

## 2026-08-31：RQ-181 Flash 响应完成度诊断

- `AUTHORIZATION`：RQ-180 未准入且只留下适配器安全聚合码后，用户授权对同一首例执行一次独立、正文零留存的诊断；不重跑旧领域门，SDK 重试为 0。
- `RESULT`：产品实现基线为 `7cb66d218389c0e7d7aa7b2b1969a4678402f857`，诊断代码为
  `447c11e85b6da53fe678d68e25d96b589c0d6ca2`。首个 `agent_initial` 回合收到有效 Usage（input `2220`、output `2048`），
  原始 `finish_reason=length`；正文为空、reasoning 非空、ToolCall 为 0。Zhipu 适配器在结束原因校验处按既有
  fail-closed 合同返回 `incomplete_chat_response`，未形成 normalized/settled response（`0/1`）。
- `EVIDENCE`：结果文件
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json` 的
  canonical-LF SHA-256=`050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，experiment
  `b1e4a1fc51bed23803b5f94acbd2a652330d5847061dbb7b60022c88da4ff1b9`，由本地证据提交
  `baa9cc756ff9e3dfc5eac19119315b7f9f0b56da` 承载。结果只保留安全状态字段，不含 Prompt、正文、reasoning、Key、
  原始请求 ID 或工具参数。
- `INTERPRETATION`：本次证据确认的是“最大推理档案下 2048 输出额度先被 reasoning 耗尽”的具体失败路径；不把
  RQ-180 的旧第二回合改写为同一原因，也不表示模型一般质量、账号失败或生产成熟度。
- `BOUNDARY`：不提高全局上限、不放宽适配器、不覆盖旧结果、不改 Dataset/Plan、默认模型、Portal、Account、Workbench、
  Auth、路由或 `production_media=0`。下一步先设计版本化响应完成策略并补离线 TDD，是否进入实现另待用户授权。

## 2026-08-31：RQ-182 版本化响应完成策略

- `AUTHORIZATION`：用户在 RQ-181 后明确“继续下一步”，授权完成 canonical 指定的策略设计与离线实现；本批不发真实 Provider 请求。
- `DECISION`：新增 `ResponseCompletionPolicy`、脱敏响应边界快照和受信请求上下文。唯一注册 Flash 严格 v1 精确绑定
  当前 runtime profile，保持 2048 输出和零额外调用；8192/一次 fresh-recovery 仅为未注册候选，不能自动激活。
- `EVIDENCE`：策略聚焦测试 `41 passed`，compileall、`git diff --check` 与治理检查通过。该本地证据不改变 8E/8F
  顺序，不构成恢复能力、领域准入或生产成熟度；旧 RQ-180/RQ-181 证据保持不可变。
- `BOUNDARY-NEXT`：若启用候选，必须先建立 attempt/预算/Trace 合同、取得 exact-SHA 公共 CI 与同 SHA 协议证据，
  再由用户单独授权真实诊断；Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。

## 2026-08-31：RQ-183 候选 fresh-recovery runtime/attempt/预算/Trace 合同

- `AUTHORIZATION`：用户明确继续 RQ-182 的唯一下一项；本批只做离线合同，不发真实 Provider 请求。
- `DECISION`：新增未注册的 `ResponseRecoveryRuntimeProfile`，精确绑定
  `zhipu/glm-5.3-flash` 与 `glm-5.3-flash-runtime-v2-candidate/2.0.0`；计划只描述
  `primary` 和最多一个 `fresh_recovery`，不称 API 原生 resume。`ResponseRecoveryLedger`
  在每个底层调用前预留、之后只结算一次，按累计 input/output/时间和单次上限 fail closed；
  `ResponseRecoveryTrace` 使用独立 schema 1.0，只有脱敏状态和资源数字。
- `EVIDENCE`：`tests/test_response_recovery_contract.py` 聚焦 `30 passed`；与响应完成策略、
  Flash runtime、Runtime models、Observed Provider 和领域门相邻回归 `128 passed`，
  compileall、差异检查和治理检查通过。模块不导入 Provider/SDK，也没有网络入口。
- `BOUNDARY-NEXT`：候选仍 `activation_state=candidate`，不进入产品注册表、不改变严格
  Flash v1 的 2048/零额外调用。后续需新的 exact-SHA 公共 CI、同 SHA G53-3、一次单独
  真实诊断授权及成本/延迟/失败审查；G53-7、黄金切片、安全部署合规、8E/8F 和
  `production_media=0` 均不变。

## 2026-08-31：RQ-184 候选合同公共证据链

- `AUTHORIZATION`：用户明确“继续”，授权完成 RQ-183 候选合同的 exact-SHA 公共 CI 与同一实现 SHA 的 G53-3；本批不自动执行 fresh-recovery 或 G53-7。
- `IMPLEMENTATION-CI`：实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654`，Actions run `33405110692` 的 `pytest`、`packaging-smoke`、`postgres-migrations` 三 job 全部成功。
- `PROTOCOL`：同一 A checkout 严格执行 G53-3 `3/3` 次真实调用，A1 结构化合同 `1/1`、A2 Agent 工具往返 `2/2`，`admitted=true`，SDK retries `0`；脱敏结果 `code_sha=A`。
- `EVIDENCE-CI`：直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 只新增
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`，Actions run `33405881172` 三 job 全部成功；A/B 无 I/O identity preflight 通过，结果 canonical-LF SHA-256=`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。
- `BOUNDARY-NEXT`：这组证据证明候选合同的公共可复现性与同 SHA 协议接缝，但不激活候选、不改变严格 Flash v1 的 2048/零额外调用，也不构成恢复能力、G53-7、领域采用或生产成熟度。下一步需用户单独授权一次有界候选恢复诊断，并审查成本、延迟、失败与脱敏 Trace；8E/8F、黄金切片、安全/部署/合规和 `production_media=0` 不变。

## 2026-08-31：RQ-185 候选恢复诊断中断

- `AUTHORIZATION`：用户在 RQ-184 后明确继续，重开一次候选恢复诊断；第一次无响应后再次明确继续，允许一次新的有界启动。
- `EXECUTION`：隔离诊断代码 `76de589a128b7a71f1def3316da3f30ebdd3a4c8` 以候选证据提交
  `eca01ce1393286dbbe83992c2985f600ea2b30b0` 为实现基线。两次独立启动都只进入 `primary` 首回合，
  SDK `max_retries=0`，没有发出 `fresh_recovery`；第一次沿用 120 秒传输边界，第二次使用全新结果名和
  临时 20 秒客户端传输上限。
- `INTERRUPTION`：两次均在约 60 秒内没有可观察响应，按工具等待边界终止；没有 Usage、finish reason、
  脱敏 Trace 或结果 JSON，不能判断请求是否抵达供应商，费用/计费状态为 `unknown`。没有重试。
- `BOUNDARY-NEXT`：候选继续 `activation_state=candidate` / `execution_allowed=false`，严格 Flash v1 继续
  2048/零额外调用；下一项改为传输/代理边界复核，需新的明确授权。默认模型、AgentLoop、RuntimeTrace、
  Portal/Account、Workbench、Auth、路由、G53-7、黄金切片、8E/8F 与 `production_media=0` 均不变。

## 2026-09-01：RQ-186 请求级截止修复与有界结果

- `ROOT-CAUSE`：RQ-185 的 20 秒客户端默认 timeout 被 `ZhipuProvider` 的每请求
  `ChatRequest.timeout_s=90` 覆盖；旧两次中断不能继续解释为 20 秒 SDK deadline 失效。
- `IMPLEMENTATION`：隔离诊断器新增受校验的 `--request-timeout-s`，primary 与可能的 fresh-recovery 均受同一
  请求级截止约束；代码提交 `94629161c5d3230629210444b5a1a38212799997`，相邻测试 `82 passed`。
- `RESULT`：唯一一次 primary 的 payload 为 8192/30 秒/零 SDK retry，约 30.141 秒后以 transport timeout
  安全关闭；无响应、Usage、finish reason、request ID 或 recovery，费用状态 `unknown`。
- `EVIDENCE`：脱敏结果由本地提交 `a7874b0` 承载，canonical-LF SHA-256=
  `0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`。
- `BOUNDARY-NEXT`：30 秒低于候选 90 秒 Agent 窗口，不能据此拒绝候选能力。候选仍未注册，严格 Flash v1、
  产品模块和 `production_media=0` 不变；下一项为候选延迟预算裁决，未经新授权不自动重试或进入 G53-7。

## 2026-09-01：RQ-187 完整候选窗口诊断

- `AUTHORIZATION`：用户明确“继续”，授权在 RQ-186 请求级截止修复后执行一次完整候选窗口；不扩大到 G53-7。
- `EXECUTION`：隔离诊断代码 `94629161c5d3230629210444b5a1a38212799997`，实现基线
  `eca01ce1393286dbbe83992c2985f600ea2b30b0`；请求 `max_tokens=8192`、`timeout_s=90`、SDK retries `0`，
  只进入一个 `primary`。
- `RESULT`：90.188 秒后以 `sdk_error_class=timeout` / `adapter_error_stage=transport` 安全结算；无响应、Usage、
  finish reason、request ID 或 `fresh_recovery`，`provider_calls_attempted=1`、`candidate_eligible=false`、
  `terminal_state=fail_closed`、费用状态 `unknown`。
- `EVIDENCE`：结果由本地提交 `50ce5be` 承载，canonical-LF SHA-256=
  `3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`。
- `BOUNDARY-NEXT`：这排除“30 秒过短”，但无响应不能区分代理/连接/读取与服务端生成延迟，也不构成模型能力失败。
 候选、严格 Flash v1、产品模块与 `production_media=0` 不变；下一项是传输/生成路径拆分，需新的明确授权。

## 2026-09-01：RQ-188 传输/生成路径拆分

- `AUTHORIZATION`：用户新授权连续推进候选诊断；本批固定最多 3 次真实调用，不重跑 RQ-187，不改产品默认。
- `IMPLEMENTATION`：隔离诊断代码与运行时 source identity 均为 `b67b4500ebdbff934e470fd92c1461184aa7c49b`；聚焦及相邻
  回归 `86 passed`，compileall、diff check 与治理通过。
- `RESULT`：合法 `enabled/low` 最小控制、冻结上下文 256 token max 同步请求、冻结上下文 8192 token max 流式首块请求
  三路均 observed；同步两路为 `length + 空正文 + 非空 reasoning`，流式路约 687ms 观察到首个 reasoning chunk 后关闭；
  资源合计 3 calls / 2265 tokens / 17172ms。
- `EVIDENCE`：正式结果 SHA-256=`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，
  experiment=`41901515decc6d8768abd56ee3fd49ac1d1a4402f3cc1cef497720995fa80c8e`。首次 disabled-thinking 控制与带代码
  SHA 输入笔误的中间结果均保留为不可变审计，不作正式证据。
- `BOUNDARY-NEXT`：这只确认 endpoint/model 路径可达且已开始生成，不证明完整 streaming、长请求根因、领域采用或
  生产成熟度。候选仍未注册，严格 Flash v1 仍 2048/零额外调用；下一项为 `candidate-output-budget-calibration`，
  不改 Provider-neutral 接口、Workbench、Portal、Account、Auth、路由或 `production_media=0`。

## 2026-09-01：RQ-189 输出额度/推理档位校准

- `RESULT`：同一冻结上下文和采样参数下，`thinking=enabled`、`low+2048` 一次调用约 28.344 秒返回可见正文，
  `finish_reason=stop`，Usage 输入 1973、输出 724；`low+8192` 与 `max+8192` 各自一次调用在约 45.5 秒请求截止内
  无响应并安全记为 timeout。三路 SDK retries 均为 0，未发 recovery。
- `EVIDENCE`：三份 body-free 结果的 canonical-LF SHA-256 分别为
  `1e001b49370f734404bc56896610d73d94057203aebf8de172d54787728e7c32`、
  `42339af9af71db3e63f2ba8e8773898a7f6b60cd8e5ceab06269ec6aca37f32`、
  `fc54d9479db60cef585b216d0b11dd36e511180b485ea00c2ebced60d528379f`；结果只保留状态、资源数字、延迟和哈希，
  不含 Prompt、正文、reasoning、Key 或 request ID。
- `BOUNDARY-NEXT`：这表明低推理短同步路径在该冻结上下文可完成，而高额度同步路径在 45 秒内未完成；不能把
  timeout 写成模型质量或账号失败，也不升级候选、生产或全局默认。下一项为 evaluation-only 的
  `candidate-stream-visible-completion-probe`，同时验证 `clear_thinking` 形状。

## 2026-09-01：RQ-190 流式首个可见正文

- `AUTHORIZATION`：用户继续授权候选边界内的有界诊断；每个结果只发出一条真实请求，不自动重试。
- `IMPLEMENTATION`：隔离探针/CLI 最终 SHA=`5ec622c4b651f9aa5e12f54b1e5a4a0dc253a4c7`，聚焦测试 `7 passed`；
  直接读取原始 OpenAI-compatible 流，不强行改用产品当前 exact `clear_thinking=false` profile。
- `RESULT`：固定冻结上下文、`low`、2048、stream、SDK retries `0`。`clear_thinking=true` 在 `1813ms` 首块、
  `2547ms` 首个可见正文；`false` 在 `1500ms` 首块、`3875ms` 首个可见正文。两路都先输出 reasoning，首正文后立即关闭，
  因此终态/Usage 未观测，预算状态 unknown。
- `EVIDENCE`：v2 结果 SHA 分别为 `23e3954c2be65d70b24186a3deba35047e3925b2fc2fde1eb3cfeec82631141a` 和
  `fae64899daaffbd2e9a2a5369ee8d396ea912065f2b7351a782a91eb74a0c77e`；v1 保留审计但不作正式结论。
- `BOUNDARY-NEXT`：该批证明两种单轮请求形状都能在短时间内出现可见正文，不证明 `clear_thinking` 因果、跨轮语义、
  完整 provider-neutral stream 或生产能力。下一项为 `candidate-stream-terminal-completion-probe`，仍不改默认模型、Workbench、
  Portal、Account、Auth 或 `production_media=0`。

## 2026-09-01：RQ-191 完整流式终态与 Usage

- `AUTHORIZATION`：用户继续授权候选边界内的单次诊断；SDK retries 固定 `0`，不打开 recovery。
- `IMPLEMENTATION`：隔离完整流探针/CLI SHA=`2a01edf58e9f5b11619553a9eeb4448a4cdb87d0`，聚焦测试 `6 passed`。
- `RESULT`：当前产品形状 `clear_thinking=false`、低推理、2048、stream 在 `2203ms` 首块、`3531ms` 首正文，
  `24140ms` 完整结束，`finish_reason=stop`、Usage valid（1973 输入 / 652 输出 / 0 缓存）；642 chunks。
- `EVIDENCE`：结果 SHA-256=`a57fec105859241ea71e32eb8073b4c33b934262a7793b6a47a7b6e4efb4b3c9`，
  experiment=`dba57e5316058336dbc0e497d01b115e337ce6367acbb967b5e6760e270b3f46`；source identity stable，public CI 未宣称。
- `BOUNDARY-NEXT`：这只证明一份冻结上下文的原始完整流可结束，不证明一般质量、高预算/长上下文、跨轮思考语义、工具流或
  provider-neutral runtime 接入。下一项为离线 `candidate-provider-neutral-stream-adapter-contract`，不改默认模型、Workbench、
  Portal、Account、Auth 或 `production_media=0`。

## 2026-09-01：RQ-192 提供商无关流式装配合同

- `IMPLEMENTATION`：新增纯 Python `ProviderStreamEvent`、`StreamToolCallDelta`、独立
  `ProviderStreamAdapter` 协议、单次 `ProviderStreamAssembler`、`StreamAssemblyResult` 与 body-free
  `StreamAssemblyTrace`；无 SDK、网络、重试和产品接线。
- `BOUNDARY`：底层必须真实 EOF 后显式 `mark_exhausted()`，并同时观察合法终止与有效 Usage；终止后最多一个
  Usage-only 帧，正文/reasoning/工具迟到、重复终止/Usage、序号/model/请求摘要冲突和预算/边界错误均 fail closed
  并毒化实例。工具片段按连续索引和严格 JSON 装配，copy-on-write 与增量字符计数避免长参数分片的重复全量求和；
  结果默认 repr 不泄露正文或工具参数。
- `EVIDENCE`：`tests/test_stream_adapter_contract.py` 聚焦 `29 passed`；相邻 Provider、响应完成策略、恢复合同和
  runtime stream 回归为 `147 passed, 27 subtests passed`。该证据只证明离线候选接缝，不证明 streaming 产品接入、
  候选/领域/生产准入。
- `BOUNDARY-NEXT`：下一项为同一新实现 SHA 的公共 CI 与 provider conformance；候选未注册，严格 Flash v1 仍
  2048/零额外调用，Stage 8/8E 仍 `in_progress`，8F 与 `production_media` 状态不变。

## 2026-09-01：RQ-193 智谱流式适配器一致性接缝

- `IMPLEMENTATION`：提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 在测试模块内加入
  `_FixtureZhipuStreamAdapter`，将代表性 OpenAI-compatible 智谱 chunks 翻译为 `ProviderStreamEvent`，
  并与现有 `ZhipuProvider.chat_stream()` 的 fake-client 结果逐字段对照；生产 Provider、同步接口和
  `capabilities.streaming` 未改。
- `VERIFICATION`：conformance 聚焦 `13 passed`，覆盖正文/reasoning、工具别名与分片、坏形状/未知工具/空 choices、
  model/terminal 边界、迭代器异常 `abort()`、正文空白保留及 Trace 脱敏。该提交 Actions run `33489903978` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success`，`head_sha` 精确匹配。
- `BOUNDARY`：该公共证据仍只说明测试夹具级候选接缝可复现，不证明真实供应商 streaming 或产品 runtime 接入。
  候选未注册，严格 Flash v1 仍 2048/零额外调用，未改默认模型、AgentLoop、ToolRuntime、
  Runtime Trace、预算、Portal、Account、Workbench、Auth、路由或 `production_media=0`。
- `BOUNDARY-NEXT`：下一项是候选接线裁决（runtime 接入范围、预算/Trace/回退/失败门）；
  不自动打开 streaming、执行 G53-7 或黄金切片，Stage 8/8E 继续 `in_progress`，8F 尚未开始。

## 2026-09-01：RQ-194 候选级显式智谱→中立适配接缝（公共闭环完成）

- `DESIGN-HISTORY`：早期记录只起草由调用方显式触发的 seam，并将模块/API 写成占位符；该历史设计保留，
  已由本地实现更新，不能再作为“尚无代码”的当前状态。
- `IMPLEMENTATION`：`app/providers/zhipu_stream_adapter.py` 新增 `ZhipuStreamAdapter`（非 `LLMProvider`），
  `ZhipuProvider.stream_adapter(*, tool_stream=False)` 提供显式工厂；`stream_events(request)` 将 raw chunks 翻译为
  `ProviderStreamEvent`，`assemble()` 交给 `ProviderStreamAssembler`，底层端口为
  `_open_stream_for_adapter()` / `_validate_stream_response_for_adapter()`。
- `BOUNDARY`：适配器继承可信 provider profile 的 `max_output_tokens` 上限（1–8192），请求 cap 只能收紧预算；
  默认要求 request identity，Trace/错误仅存 SHA-256 摘要。单流必须真实 EOF、合法 terminal、有效 Usage 才完成；
  取消、迭代器/翻译/关闭异常均 `abort()`/fail-closed，不 retry、不 recovery、不执行 ToolRuntime，不注册 recovery，
  只允许 fake/local evidence。
- `VERIFICATION`：提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588` 已完成，
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success` 且 head_sha 精确匹配；
  `tests/test_zhipu_stream_adapter.py` 聚焦 `20 passed`。这只证明候选接缝公共可复现，不等于产品 runtime 接线或生产准入。
- `UNCHANGED`：`capabilities.streaming` 仍为 `False`，严格 Flash v1 仍 2048/零额外调用；默认模型、同步 `chat()`、
  既有 `chat_stream()`、AgentLoop、ToolRuntime、Runtime Trace、预算、Workbench、Portal、Account、Auth、路由及
  `production_media=0` 均不变，候选未注册，Stage 8/8E 仍 `in_progress`，8F 尚未开始。
- `BOUNDARY-NEXT`：exact-SHA 公共 CI 已完成，下一门是独立裁决候选 runtime 接线范围；
  不自动打开 `capabilities.streaming`、执行 G53-7/黄金切片或进入生产准入。

## 2026-09-01：RQ-195 候选 runtime 接线架构评审

- `REVIEW`：复核 RQ-194 的显式 `ZhipuStreamAdapter` 与现有产品 Runtime 的合同边界；
  `assemble()` 只交付真实 EOF、合法 terminal、有效 Usage 齐全的完整 `stop`/`tool_calls` 流，
  不完整形状和异常均 fail-closed。
- `DECISION`：不把 adapter 包装成 `LLMProvider`，不在 `AgentLoop` 增加隐式 streaming 分支，
  不修改默认注册、统一 Trace/预算或 `capabilities.streaming`。未来若单独授权，采用隔离的
  `CandidateStreamEvaluationHarness`，由调用方精确绑定 provider/model/profile/policy 四元身份。
- `BOUNDARY-OBSERVATION`：下一设计门先冻结只输出字段状态、finish code、Usage 数字、耗时和安全错误码的
  `BoundaryObservation`，复用分块/model/sequence/tool/Usage 校验；不得暴露或持久化部分正文、reasoning、工具参数，
  也不得把不完整流包装成 `ChatResponse`。
- `UNCHANGED`：候选仍 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 仍 2048/零额外调用；
  Portal、Account、Workbench、Auth、路由、默认模型和 `production_media=0` 不变，8E 仍进行中，8F 未开始。
- `BOUNDARY-NEXT`：下一精确项为 `candidate-runtime-wiring-design / pending`；不执行真实 API、recovery、G53-7 或黄金切片。

## 2026-09-01：RQ-196 候选 runtime 接线设计

- `AUTHORIZATION`：用户确认继续推进且基本决定采用 GLM-5.3-Flash；本条授权完成设计门，记录唯一主力候选目标，
  不等于静默改成全产品唯一默认或立即发起真实 recovery。
- `DESIGN`：冻结 `CandidateRuntimeBinding` 的 provider/model/runtime-profile/policy/attempt 四元身份，body-free
  `BoundaryObservation` 的生命周期、终止码、字段状态、工具计数、有效 Usage 数字、单调耗时、model/request SHA-256
  与安全错误码，并规定完整流/不完整流共享校验后分流。
- `ISOLATION`：未来候选 v2 transport 与 `CandidateStreamEvaluationHarness` 只放在 `app/evaluation/`，不实现
  `LLMProvider`，不进入 registry、composition、AgentLoop、Worker 或统一 Runtime Trace；v1 的 2048 cap 不得泄漏到 v2。
- `BUDGET`：reserve→open→observe/assemble→settle 每槽位恰好一次，最多 2 attempts/1 次额外调用/32,000 input/
  16,384 output/180,000ms；unknown Usage 不按零，第三次调用拒绝；当前 `execution_allowed=false`。
- `UNCHANGED`：未改 `app/` 产品 Runtime、默认模型、`capabilities.streaming`、Portal、Account、Workbench、Auth、路由或
  `production_media=0`，未执行真实 API、recovery、G53-7 或黄金切片。
- `BOUNDARY-NEXT`：当时唯一下一精确项为
  `candidate-boundary-observation-contract-implementation / pending`；该门已由 RQ-197 推进，后续状态以最新条目为准。

## 2026-09-01：RQ-197 候选边界观察合同本地实现

- `IMPLEMENTATION`：按 RQ-196 的隔离边界新增 `app/evaluation/candidate_stream_contract.py`，落地精确
  candidate binding、body-free `BoundaryObservation`、不可变快照、字段 presence/状态聚合、候选 v2 注入式
  transport port 与独立 `CandidateStreamTrace`。观察对象只保留生命周期、终止码、字段状态、工具计数、有效 Usage
  数字、单调耗时、model/request SHA-256 和安全错误码。
- `SHARED-VALIDATION`：`ProviderStreamEvent` 保留显式 null 与缺失的区别；完整 assembler、智谱翻译和候选观察器共享
  `validate_provider_stream_event()` 的 model/sequence/tool/Usage/大小校验，避免两条路径漂移。
- `FAILURE-MATRIX`：覆盖完整 `stop`/`tool_calls`、`length` reasoning-only、缺 EOF/terminal/Usage、身份/序号/工具/预算/
  时钟/关闭异常、状态伪造和 body-free 序列化。不完整或异常流均 fail-closed，不构造 `ChatResponse`，unknown Usage 不当零；
  用户中断类异常不会被清理路径吞掉。
- `VERIFICATION-LOCAL`：候选、assembler、智谱 adapter、响应策略和恢复合同聚焦/相邻回归 `163 passed`，compileall、
  diff check 和 governance 通过；全量本地首错是环境缺少 `RIFTCOACH_TEST_DATABASE_URL`，不归因于本批。
- `UNCHANGED`：候选仍 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 2048/零额外调用，
  `capabilities.streaming=False`、默认模型、AgentLoop、Workbench、Portal、Account、Auth、路由、统一 Trace/预算和
  `production_media=0` 均不变；没有真实 API/Key、recovery、G53-7 或黄金切片。
- `BOUNDARY-NEXT`：当前唯一下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-public-ci / pending`；
  先在同一干净实现提交上取得 exact-SHA 公共 CI，再另行裁决 candidate harness、fresh-recovery、G53-7、黄金切片和生产准入。

## 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

- `PUBLIC-CI`：RQ-197 实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run
  `33507627615` 三 job（`pytest`、`postgres-migrations`、`packaging-smoke`）均 `completed/success`，
  `head_sha` 精确匹配；公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
- `BOUNDARY`：候选仍 `activation_state=candidate`、`execution_allowed=false`，不注册、不打开
  `capabilities.streaming`，不改默认模型、产品 Runtime、Portal、Account、Workbench、Auth 或
  `production_media=0`，没有真实 API/Key、recovery、G53-7 或黄金切片。
- `CURRENT`：收口后的唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
  本轮暂停，后续需用户明确继续。

## 2026-09-02：RQ-199 隔离候选评估台设计

- `DESIGN`：用户“继续”只授权当前 `candidate-evaluation-harness-design`；新增 ADR-0077、
  候选评估台实现计划和学习 walkthrough。本轮没有产品代码、真实 API/Key、recovery、G53-7 或前端改动。
- `DECISION`：采用隔离的 `CandidateEvaluationHarness`，以 candidate-only staged ledger
  解决“primary 预留时还不知道首回合快照”的时序问题；primary 先 reserve，观察完成后才
  映射真实 snapshot、重算 policy 和冻结 recovery plan。拒绝 sentinel snapshot、首回合结束后
  才 reserve、隐式 `LLMProvider`/AgentLoop streaming 分支。
- `DECISION`：一条 normalized stream 只经一次事件泵，同时喂给 body-free observer 与仅内存
  assembler；完整结果只可交给显式 evaluation consumer，新的 `CandidateEvaluationReceipt`
  只保留身份、生命周期、字段状态、Usage/耗时、预算和安全码，不进入统一 Runtime Trace。
- `BOUNDARY`：当前 activation disabled，候选仍 `execution_allowed=false`；严格 Flash v1
  2048/零额外调用、`capabilities.streaming=False`、默认模型、Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 不变，Stage 8/8E 仍进行中、8F 未开始。
- `CURRENT`：设计门完成后的唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`；
  后续只在明确继续后实现 fake/local staged ledger/harness，再做聚焦测试和公共 CI。

## 2026-09-02：RQ-200 隔离候选评估台本地实现

- `IMPLEMENTATION`：按 RQ-199 的设计新增隔离 `CandidateEvaluationHarness`、candidate-only
  staged ledger、单次 normalized event pump、一次性内存 assembler 接缝和独立
  `CandidateEvaluationReceipt`；实现位于 `app/evaluation/`，不包装成 `LLMProvider`，不进入
  ProviderRegistry、AgentLoop、Worker 或统一 Runtime Trace。
- `FAIL-CLOSED`：primary 在 I/O 前预留，观察完成后才映射真实 snapshot、重算 policy 并 settle；
  缺 EOF/终止/Usage、`length` 不完整、身份/序号/工具/预算/时钟/打开/读取/关闭异常均不构造
  产品 `ChatResponse`，unknown Usage 保持 unknown，不执行 ToolRuntime 或隐式 retry。
- `VERIFICATION-LOCAL`：harness 聚焦测试 `15 passed`，与边界观察、流装配和旧恢复合同相邻回归
  `102 passed`；Python 3.11/3.13 编译、`git diff --check` 和治理预检均通过。测试只使用
  fake/local transport，不读 Key、不发真实 API。
- `UNCHANGED`：activation 仍为不可伪造的 `disabled`，候选仍
  `execution_allowed=false`；严格 Flash v1 2048/零额外调用、`capabilities.streaming=False`、
  默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0`
  均不变，未执行 fresh-recovery、G53-7、黄金切片或生产准入。
- `BOUNDARY-NEXT`：实现提交取得同 SHA 公共 CI 前，唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-public-ci / pending`；
  CI 之后是否启用 fake/真实 recovery、重跑 G53-7、黄金切片或生产准入仍须独立授权。

## 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

- `PUBLIC-CI`：RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 GitHub Actions run
  `33536168224` 已完成且 `head_sha` 精确匹配；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 全部成功，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
- `BOUNDARY`：该证据只验证隔离候选评估台的可复现性；候选仍未注册、`execution_allowed=false`、
  `capabilities.streaming=False`，严格 Flash v1、默认产品 Runtime、Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 均不变，没有真实 API/Key、recovery、G53-7、黄金切片或 8F 证据。
- `BOUNDARY-NEXT`：当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`；
  先复核候选 recovery 的传输、预算、失败和脱敏边界，是否建立新诊断版本仍需单独授权。

## 2026-09-02：RQ-202 候选 recovery 诊断边界复核

- `REVIEW`：在 RQ-201 公共 CI 之后完成一次离线复核；`CandidateEvaluationReceipt` 的顶层
  state/action/error、attempt 决定/装配和 budget projection 均改为从受信观察推导，单次
  observer 截止绑定 90 秒 attempt 窗口，累计账本仍为 180 秒。
- `NON-REUSE`：旧同步 recovery 诊断器仍直接拥有 SDK/真实 I/O，并复用把 unknown Usage
  当零的旧账本；明确不把它作为新诊断版本基础，旧文件保持历史兼容。
- `EVIDENCE`：harness `18 passed`，候选相邻集合 `127 passed, 1 deselected`，compileall、
  diff check、governance 通过；Windows CRLF fixture 与 canonical-LF 计划摘要差异只作环境
  限制记录，不修改冻结资产。
- `BOUNDARY-NEXT`：唯一下一精确 checkpoint 改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`；
  不注册候选、不发 recovery、不进入 G53-7/黄金切片/生产准入或 8F。

## 2026-09-02：RQ-203 版本化候选 recovery 诊断协议设计

- `DESIGN`：在 RQ-202 加固后，按用户授权完成独立协议设计
  `glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0`。协议绑定 provider/model、runtime profile、policy 与实现/计划/上下文/运行 SHA；请求摘要只保存脱敏形状。
- `LIFECYCLE`：冻结 `reserve → open → observe/assemble → settle → receipt`，每个潜在 I/O 先占槽位；fresh recovery 是完整新请求，禁止 resume、隐式 retry、AgentLoop retry 和 ToolRuntime 副作用。当前 activation 仍 sealed disabled。
- `EVIDENCE`：设计明确单次/累计预算、Usage/费用三态、六段单调延迟、失败第一现场和 body-free 原子 create-only 回执；新增 ADR-0079、设计计划和学习 walkthrough。没有新增代码、结果 JSON、真实 API/Key 或产品接线。
- `BOUNDARY-NEXT`：候选仍未注册、`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1、默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变；唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`，不进入 G53-7、黄金切片、生产准入或 8F。

## 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现

- `IMPLEMENTATION`：将 RQ-203 协议落成隔离的 `candidate_recovery_diagnostic_v2.py`，并在
  `app/evaluation/__init__.py` 仅导出评估 API。实现 candidate-only staged ledger、primary
  I/O 前 reserve、一次 normalized event pump、临时 assembler、派生 receipt 和 canonical
  create-only JSON；不接 ProviderRegistry、AgentLoop 或统一 Runtime Trace。
- `FAIL-CLOSED`：缺 EOF/terminal/Usage、身份/序号/工具/预算/时钟/关闭/控制/consumer 异常和
  伪造回执均安全结算或拒绝；unknown Usage/未验证价格保持 `null/unknown`，disabled gate 不
  发送第二次 recovery 请求，正文、reasoning、工具参数、Key 和异常原文不进回执。
- `VERIFICATION-LOCAL`：新模块 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同
  相邻回归 `82 passed`；Python 3.11/3.13 compileall、静态 no-I/O/import 与 diff check 通过。
  系统 Python 3.13 用户环境已安装 `pytest 9.1.1`，项目测试仍由仓库 `.venv` 提供依赖。
- `BOUNDARY-NEXT`：activation 仍 disabled，候选未注册、不打开 `capabilities.streaming`，严格
  Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
  `production_media=0` 不变；没有真实 API/Key、第二次 recovery、G53-7、黄金切片、生产准入或 8F。
  当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`，
  先取得同一干净实现提交的 exact-SHA 公共 CI 和协议 dry-run。

## 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环

- `PUBLIC-CI`：RQ-204 实现提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 Actions run
  `33598541029` 已 `completed/success`，三 job（`pytest`、`postgres-migrations`、`packaging-smoke`）均成功且
  `head_sha` 精确匹配；公共 pytest `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，
  PostgreSQL 控制面 `201 passed, 1 warning`。
- `DRY-RUN`：本地 fake transport 完成一次 primary 协议生命周期并写入临时 canonical body-free 回执，
  `calls=1`、`body_free=true`、`3900` bytes；前端契约/typecheck/unit/build/E2E、RAG 和治理也随公共门通过。
- `BOUNDARY`：没有读取 Key、真实 API、第二次 recovery、候选注册或产品 Runtime 接线；严格 Flash v1、
  默认模型、`capabilities.streaming=False`、Portal/Account/Workbench/Auth、路由和 `production_media=0` 不变。
- `BOUNDARY-NEXT`：当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
  真实 recovery、G53-7、黄金切片、生产准入与 8F 仍需新的明确授权。

## 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察

- `PUBLIC-CI`：诊断接缝提交 `0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run
  `33603143606` 三 job exact-SHA 全绿；实现基线为 `90242822df0e47304700644572bc12f0a3aa88ad`。
- `REAL-OBSERVATION`：在干净隔离工作树按一次性授权仅发出 1 次普通智谱
  `zhipu/glm-5.3-flash` primary，SDK retries=0；流观察到 reasoning、可见正文、`stop` 和 EOF，
  首事件 `3078ms`、首个可见正文 `151453ms`、总延迟 `175875ms`。
- `FAIL-CLOSED`：Usage 缺失、close 失败，单次 90 秒 attempt 门在晚到事件中触发；回执为
  `fail_closed / elapsed_limit`、`calls_reserved/settled=1/1`、费用 unknown，没有第二次 recovery。
  `open_elapsed_ms=0` 仅代表惰性流计时起点。
- `EVIDENCE`：持久 canonical body-free 回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`，
  `4355` bytes，SHA-256 `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`。
- `BOUNDARY`：该结果只证明本次请求到达接口并产生内容，不裁决模型一般质量、领域准入或生产成熟度；
  候选仍 disabled/未注册，严格 Flash v1、默认模型、产品 Runtime、Portal/Account/Workbench/Auth、
  `production_media=0`、G53-7、黄金切片和 8F 均不变。
- `BOUNDARY-NEXT`：当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  先离线设计和测试硬墙钟取消、流关闭与 Usage/终态尾帧处理，再讨论新的真实调用。

## 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧后续

- `VERIFICATION-LOCAL`：候选 `CandidateStreamSession` 与
  `CandidateStreamDeadlineSupervisor` 已完成本地实现；四文件聚焦回归（deadline 10、v2 24、real 8、adapter 25）
  统一为 `67 passed`，未读取 Key、未调用真实 API、未发起重试或第二次请求。
- `DESIGN`：deadline 固定为 attempt 起点的绝对 monotonic 墙钟；超时只发显式、协作式、非阻塞意图，
  cancel/close 幂等，截止后的迟到事件丢弃；终态必须与 Usage 同帧，或终态后恰好一个 Usage-only 尾帧，
  缺失 Usage 保持 unknown/null，close 失败只作为次级证据。
- `COMPATIBILITY`：legacy `open_stream() -> Iterable` 保持可用；hard mode 只接受显式 session opener。
  显式 opener 若返回 legacy iterable，兼容性校验发生在 opener 返回后并 fail closed，不能宣称 opener I/O 已预验证。
- `LIMITATION`：同步 opener 仍可能越过计时器；SDK `close()` 是否非阻塞且能唤醒 `next()` 尚无 provider/public CI
  证明，故本地实现不能提升为产品 Runtime 能力或生产准入证据。
- `BOUNDARY`：Stage 8/8E 继续 `in_progress`；候选保持 `activation_state=disabled`、
  `execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用，产品模块、
  路由、默认模型和 `production_media=0` 不变。
- `BOUNDARY-NEXT`（历史快照）：RQ-207 本地实现完成时的下一精确 checkpoint 曾为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
  RQ-208 已完成该公共 CI，当前指针以 RQ-208 条目为准。

## 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

- `PUBLIC-CI`：RQ-207 实现提交 exact SHA `015b022bfce6d03452f753794ac126a377f8355b` 的 Actions run
  `33613113829` 三 job（`pytest`、`postgres-migrations`、`packaging-smoke`）均为 `completed/success`，
  `head_sha` 精确匹配，RQ-207 公共 CI 已闭环；该门仍不等于真实 provider 重测。
- `VERIFICATION`：公共 pytest 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL
  控制面为 `201 passed, 1 warning`；网页契约/生产包、媒体审计工具链、RAG v1/独立 4M holdout、治理、
  compileall 与 Harness dry-run 均通过；本地四文件聚焦保持 `67 passed`，没有新的真实 API、重试或第二次请求。
- `BOUNDARY`：公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 非阻塞/能唤醒 `next()`，也不构成
  模型一般能力、领域采用或生产成熟度结论；同步 opener 永久阻塞限制继续保留。候选仍 disabled、未注册，严格
  Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal/Account/Workbench/Auth、路由和 `production_media=0`
  不变，Stage 8/8E 继续 `in_progress`。
- `BOUNDARY-NEXT`：当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  真实重测只能在新的明确一次性授权后进行，不能自动注册候选或进入 G53-7。

## 2026-09-02：RQ-209 候选真实流硬墙钟与关闭边界观察

- `OBSERVATION`：按用户“继续”只发送 1 次普通智谱 `zhipu/glm-5.3-flash` primary；候选显式请求 Usage，
  `max_tokens=8192`、attempt 90 秒、transport 120 秒、SDK retries=0。首事件/打开计时 `3421ms`，reasoning
  非空；`90015ms` 到达硬墙钟，未见可见正文、terminal、EOF 或 Usage，回执为
  `fail_closed / elapsed_limit`，`calls_reserved/settled=1/1`，费用 unknown，无 recovery/重试。
- `EVIDENCE`：body-free 回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json`，
  `4342` bytes，SHA-256 `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`，由本地提交
  `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存；公共 CI 尚未宣称。
- `BOUNDARY`：组合会话 `close_state=failed` 不能归因到供应商 response、迭代器或其他具体资源，不能证明
  底层 close 非阻塞/唤醒 `next()`，也不能推出模型、API/Key、领域采用或生产成熟度。`observation.elapsed_ms=0`
  是截止前未结算的初始投影，不能当作零耗时。
- `BOUNDARY-NEXT`：候选仍 disabled/未注册，产品 Runtime、默认模型、Workbench、前端、Auth、路由和
  `production_media=0` 不变；唯一下一精确 checkpoint 仍为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，
  后续 provider close/wakeup 拆分或真实请求需新的明确一次性授权。

### 2026-09-03：RQ-210 候选会话分资源关闭报告边界裁决

接受在候选内部增加仅内存、body-free 的 `ZhipuStreamCloseReport`：它分别投影迭代器和外层 SDK stream wrapper
的关闭状态、组合状态与对象别名，逐资源尝试清理，并保留旧 `close_failed`/RQ-209 回执兼容性。拒绝把该投影
解释为底层 HTTP response 已关闭、close 非阻塞或已唤醒 pending `next()`；`cancel()` 仍同步经过 SDK close。
本批不升级 receipt/schema、不改变 8E 路线或产品能力；实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 的
公共 CI `33657368435` 三 job 已 exact-SHA 成功；后续 provider-level 观察或持久分资源字段仍需另立决策并获明确授权。

### 2026-09-03：RQ-211 候选 provider close/wakeup 一次观察裁决

- `EXECUTION`：接受在 exact-SHA 公共绿灯的 `c31127b3c780fe4c493966d8b60f942d3b773fd4`
  干净快照上执行一次真实观察；Actions run `33661910096` 三 job成功，探针只发 1 次请求、SDK retries=0，
  无 recovery 或第二请求。
- `EVIDENCE`：body-free 回执为 `908` bytes、SHA-256
  `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`；状态为
  `not_pending`，会话打开、首段读取 `78ms`、只见 reasoning/content 类别，cancel 未执行。迭代器、SDK stream
  wrapper 与组合关闭投影均为 `closed`。
- `REJECTED-CLAIM`：拒绝把 `not_pending` 写成 close/wakeup 通过或失败；本次没有形成 pending reader，
  所以没有验证 close 是否非阻塞、能否唤醒 `next()` 或底层 HTTP response 是否取消。
- `BOUNDARY-NEXT`：候选/产品边界不变。下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`，
  等待用户决定是否另立新版协议，不自动重试、注册候选或进入后续成熟度闸门。

### 2026-09-03：RQ-211 公共回执分派补充

提交 `1c669e0` 为 provider capability 全目录扫描加入 RQ-211 schema 的显式解析分支；Actions run
`33666132282` 三 job exact-SHA 全绿，公共 pytest `2268 passed, 145 skipped, 1 warning, 127 subtests passed`，
PostgreSQL `201 passed, 1 warning`。该修复只让持久 body-free 回执可被公共合同识别，没有新增真实调用；
真实观察仍绑定 c311，候选 gate 与产品边界不变。

### 2026-09-03：RQ-212 候选 close/wakeup 离线 pending-read 回放

- `DESIGN/IMPLEMENTATION`：针对 RQ-211 真实样本为 `not_pending` 的条件缺口，新增独立
  `glm-5.3-flash-candidate-close-wakeup-replay` / schema `1.0.0`。固定五个内存 Event
  闸门场景并复用既有观察器，验证正常 EOF、取消后唤醒、取消返回但未唤醒、取消超时和
  取消抛出五种生命周期。
- `EVIDENCE-SEPARATION`：离线回执只允许放在
  `data/evaluation/results/offline/`，强制 `evidence_origin=offline_fake`、
  `real_provider_observed=false`、`provider_call_count=0`、`network_used=false`；
  `fake_session_open_count=1` 与 `observer_call_count=1` 不被解释为供应商调用。固定
  场景 SHA 为 `8a389a9796b0407b3e209ddaab5134b140d4c8379ba659380ae031229011fe26`。
- `BOUNDARY`：本批只证明本地观察分类、单次打开、脱敏和不可变回执可重复，不能证明供应商
  SDK close 非阻塞、底层 HTTP response 可取消或真实 pending `next()` 能唤醒；候选仍 disabled、
  不注册、不打开 `capabilities.streaming`，产品 Runtime/前端/Workbench/默认模型和
  `production_media=0` 不变。
- `BOUNDARY-NEXT`：当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-real-observation / pending-user-authorization`；
  聚焦回归、公共 CI 和治理闭环均已完成；是否执行一次参数明确的真实 provider 观察仍需单独授权。

### 2026-09-03：RQ-212 公共闭环事实

- 实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec` 的 Actions `33707313651` 三 job exact-SHA 全绿：
  pytest `2284 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
  packaging-smoke 通过。
- v2 回执为 `data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`，
  `2220` bytes、SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`；
  三个身份 SHA 均绑定实现提交，v1 仅为旧 HEAD 的提交前演练。
- 该回执仍是 `offline_fake`/0 provider calls/no network，只关闭本地回放合同，不关闭 provider-level close/wakeup；
  下一精确 checkpoint 为 `candidate-close-wakeup-real-observation / pending-user-authorization`。

### 2026-09-03：RQ-213 候选 close/wakeup 第二次有界真实观察

- `EXECUTION`：在 RQ-212 公共闭环后的 exact-SHA 公共绿灯提交
  `a396412f7cd0f2e923536cf55f715dd56251aae5` 上，只执行 1 次普通智谱
  `zhipu/glm-5.3-flash` 请求；SDK retries 为 0、父进程边界 30 秒，无 retry、recovery 或第二请求。
- `EVIDENCE`：回执
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`
  为 schema `1.0.0`、909 bytes、SHA-256
  `8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`；会话打开、首段 172ms，
  只记录 reasoning/content 类别，`observation_state=not_pending`。
- `REJECTED-CLAIM`：没有 pending reader，因此 cancel 未尝试；`reader_woke=false` 不是唤醒失败，
  三层 `closed` 也不等于 provider close 或 HTTP response 取消已被证明。
- `BOUNDARY-NEXT`：候选/产品边界不变。下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`；
  先裁决是否设计能稳定制造 pending-read 的新版协议，不自动追加真实请求。

### 2026-09-03：RQ-214 候选 SDK/HTTP transport gate 离线预检

- `DESIGN`：RQ-213 的两次真实样本都为 `not_pending`。比较自然长尾、适配器外 fake 和
  SDK/HTTP 闸门后，选择在真实 OpenAI SDK/Zhipu 候选适配器对象链上注入本机
  `MockTransport`；闸门只按完整 SSE 帧边界暂停。
- `IMPLEMENTATION/EVIDENCE-SEPARATION`：新增独立 transport-gate 模块、脚本和测试，
  固定 `after_first_event`、`before_first_event` 两阶段；每阶段 1 次内存 transport 请求，
  回执使用独立 schema、`offline_sdk_transport_fixture`、0 provider calls 和 no network，
  不保存正文、Key、headers、request ID 或异常文本。
- `OBSERVATION`：两阶段均形成 pending reader，并在 SDK response close 后唤醒；当前适配器
  并发关闭生成器的投影可能为 `iterator=failed`、`sdk_stream=closed`、`composite=failed`，
  单独标记 `client_wakeup_close_race`。这只是本地客户端事实，不是 provider-native 结论，
  本批不静默修复关闭顺序。
- `BOUNDARY-NEXT`：离线回执提交并取得同 SHA 公共 CI 后，下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / pending-user-authorization`；
  只有新的明确一次性授权才执行最多 1 次官方 TLS transport 包装的真实请求，不重试、
  不 recovery、不注册候选、不改产品 Runtime/Workbench/前端或 `production_media=0`。

### RQ-214 回执记录（2026-09-03）

离线回执已绑定实现提交 `4c220c5751288ad77c589d2e0e581690085803c0`，路径为
`data/evaluation/results/offline/zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json`，
`1693` bytes、SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`。
Actions run `33712055286` 同 SHA 三 job 全绿：pytest `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`；PostgreSQL `201 passed, 2 warnings`；packaging-smoke 通过，真实请求仍未执行。

### 2026-09-03：RQ-215 候选 transport-gated 一次真实观察

- `PRECONDITION`：RQ-214 离线回执和实现提交 `4c220c5751288ad77c589d2e0e581690085803c0` 的
  Actions `33712055286` 已 exact-SHA 三 job 全绿；因此本批在新的精确提交
  `2acdf795881733e70c9246c48f7147d5136821b5` 上执行。
- `BOUNDED-REAL`：按用户一次性授权只发送 1 次 `zhipu/glm-5.3-flash` 请求，SDK/HTTPX retries
  均为 0，父进程 30 秒硬截止，阶段为 `before_first_event`；不 retry、不 recovery、不发送第二请求。
- `OBSERVATION`：官方 TLS transport 外层 gate 进入，真实流启动并形成 pending reader；
  response close 后 reader 在 `31ms` 内唤醒，`upstream_event_seen=true`、
  `upstream_stream_close_seen=true`。取消抛出安全码 `zhipu_stream_close`，iterator/composite
  close 投影为 `failed`、SDK stream 为 `closed`，结论为 `client_wakeup_close_race`。
- `EVIDENCE-SEPARATION`：回执
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`
  为 `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`，
  `provider_call_count=1`、`transport_request_count=1`、`network_used=true`，canonical round-trip 通过，
  不含正文、凭据或 request ID。
- `BOUNDARY-NEXT`：该证据只说明真实流启动后的本机受控客户端行为，不新增 8-Core 能力，
  不证明 provider-native close/wakeup、模型一般能力或生产 streaming。候选仍 disabled/未注册，
  默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变；
  当前精确 checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

### 2026-09-03：RQ-216 候选 reader-owned close 顺序修复

- `DECISION`：将 `client_wakeup_close_race` 定位为客户端 reader 与取消线程跨线程关闭 Python iterator 的竞态；活跃读取时先关外层 SDK response，iterator 由 reader 线程在 `finally` 中收尾。
- `EVIDENCE`：新增阻塞读取回归并收紧 RQ-214 两阶段离线 gate 断言；候选聚焦 `61 passed`，compileall、差异检查和治理通过，真实 API 为 0。
- `BOUNDARY-NEXT`：RQ-216 仍是 8-Advanced candidate-only 修复，不提升候选注册、默认模型、8-Core、生产 streaming 或任何 Portal/Account/Workbench/Auth 能力。当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`；公共 CI 后才回到真实观察决策点。

### RQ-216 公共闭环（2026-09-03）

- `PUBLIC-CI`：提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` / Actions
  `33726209532` 三 job exact-SHA 全绿；pytest `2297 passed, 145 skipped, 2 warnings,
  127 subtests passed`，PostgreSQL 与 packaging-smoke 通过。
- `BOUNDARY-NEXT`：公共闭环只证明候选关闭顺序修复可复现，不新增真实请求或产品能力；当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`，等待是否重新观察的用户决定。

## 2026-09-03：RQ-217 关闭顺序修复后的 transport-gated 真实观察

RQ-217 仍属于 8E/8-Advanced 的 candidate-only、evaluation-only 证据，不新增 8-Core
（product/deployment/compliance/eval/portfolio）能力，也不改变 8E→8F 顺序。用户在
RQ-216 的 exact-SHA 公共 CI 通过后授权只做一次真实观察；实现、观察器和输入计划均绑定
`3e028b1217f1274152ba161993287f29188a1b73`，Actions `33727163550` 三 job 全绿。

官方 TLS transport 外层 gate 在 `before_first_event` 进入并形成 pending reader；只发生
1 次 provider/transport 请求，`reader_woke=true`、`cancel_status=returned`，iterator、
SDK stream 和 composite close report 均为 `closed`，结论为 `client_wakeup_clean`。
回执为 `1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`，
保持 body-free、canonical round-trip 可复核；`gate_released=false` 是受控停顿协议的
预期条件。

该样本只说明真实流启动后本机客户端的唤醒和 reader-owned 收尾，不证明 provider-native
close/wakeup、底层 HTTP response 独立取消、模型一般能力、成本/延迟稳定性或生产
streaming。候选仍 disabled/未注册，`capabilities.streaming=False`；默认模型、产品
Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变。当前唯一
精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`；
没有新的独立授权前不再发送真实请求。

## 2026-09-03：RQ-218/RQ-219 Flash 协议复核与候选 8192 超时

- `CURRENT`：RQ-218 在最新实现上重取 G53-3，精确 3/3 通过；证据提交
  `4b6cd5807f40f6a8dd469f21c688be861261d20c` / Actions `33735039437` 三 job 全绿，
  回执 SHA=`feeb7fd7eec2643ca692bd6182fd94a04abed354b17b892029402c0217641e99`。
- `OBSERVATION`：RQ-219 只发 1 次候选 8192 primary，在 90 秒硬墙钟以
  `fail_closed / elapsed_limit` 收口；回执 SHA=`21350d7883b4d2eea30e0467a7b8c23eed3a3ad5a9deeb309c44f8ded5cf3f84`。
  证据提交 `3f35d150b2f17f919f2be1597c08c6db0178c461` 的 Actions `33735717434` 三 job
  已 `completed/success`。
- `BOUNDARY-NEXT`：候选保持 disabled/未注册，严格 Flash v1、默认模型和产品链路不变；
  当前唯一 checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / pending`，
  先做零网络档位、终态、Usage 与恢复决策拆分，不重复真实请求。

## 2026-09-03：RQ-220 响应档位—终态—恢复离线拆分

- `IMPLEMENTED-LOCAL`：新增固定 9 场景的零网络矩阵与 body-free receipt，复用候选
  stream observer、严格 policy 和 candidate policy；9/9 通过，provider calls=0。
- `BOUNDARY-NEXT`：该批只增加评测归因能力，候选仍 disabled/未注册，严格 Flash v1 和
  产品链路不变；实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` / Actions
  `33738050233` 与回执提交 `ebb09a525b3340f31ba71821b894b4a142dfb4e7` / Actions
  `33738673832` 均三 job `completed/success`，回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
  当前 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`，
  下一动作是候选域门裁决，不自动追加真实请求。

## 2026-09-03：RQ-221 低思考候选 profile 一次性探针

- `IMPLEMENTED`：新增显式 candidate-only `low + 4096` profile 与探针；
  `thinking=enabled`、`reasoning_effort=low`、`clear_thinking=false`，不进入正常
  Runtime resolver，也不改变严格 Flash v1。
- `PUBLIC-CI`：实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions
  `33746833148` 三 job exact-SHA 全绿；候选聚焦 `25 passed`、本次相关候选/流/智谱回归
  `357 passed`。
- `REAL-OBSERVATION`：按授权只发 1 次无工具请求，`retries=0`；结果为
  `observed / finish=stop / usage=valid`，输入/输出 `1973/498`，延迟约 `20735ms`。
  回执提交 `ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，SHA-256=
  `c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`，body-free、
  create-only。
- `BOUNDARY-NEXT`：这只是冻结无工具上下文的一次响应完成观察，不是领域采用、G53-7、
  黄金切片、生产准入或 8F 证据；候选仍 disabled/未注册，默认模型、产品 Runtime、
  Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。当前唯一精确
  checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`，
  下一步先设计/裁决低档候选 held-out 领域门。
## 2026-09-03：RQ-222 低思考候选独立领域门设计裁决

RQ-222 比较了旧考卷换档重跑、提前注册产品档案和独立评测作用域三种路线，接受第三种：
新的候选作用域只在评测组合器中建立，通过共享请求策略复用现有 Agent/RAG/Evaluation/
Harness，不削弱产品 Runtime 注册校验。旧 G53-4/G53-7 结果不重跑，规则冻结后创建全新的
三案例 oracle-blind held-out 资产。

候选领域合同固定 `low + 4096`、90/120 秒、4 次/案例与 12 次/全域、无重试/恢复/修订、
首错停止，以及 24,000/72,000 token 墙；deterministic fallback 在评测作用域关闭。当前只
完成设计，provider calls=0；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。

## 2026-09-04：RQ-223 低思考候选领域门离线实现

RQ-223 按 RQ-222 的设计先落地零网络控制面。新增私有签发的候选
`CandidateEvaluationRequestPolicy` 与显式 `request_policy` 接缝，Agent 编译器、LLM 工具、
Draft/Domain executor 和最后预算包装器共享同一组 `low + 4096`、90/120 秒、固定采样、零重试
和无回退约束；reserve-before-I/O 账本执行 4/12 次调用与 24,000/72,000 token 墙。Fake
Provider 测试 5/5、相邻回归 118 passed，provider calls=0。该实现仍属 8-Advanced
candidate-only，未改变 8-Core、默认模型、Portal、Account、Workbench、Auth 或
`production_media=0`；下一步是同 SHA 公共 CI，不是 G53-3-L 或领域真实调用。

## 2026-09-04：RQ-224 低思考候选领域门公共 CI 闭环

实现 `d823cc40c3fcafb7167edccded87e185be4cae8a` 的 Actions run `33781369322` 三 job
均 `completed/success` 且 head SHA 精确匹配；公共 pytest 为 `2326 passed, 145 skipped,
2 warnings, 127 subtests passed`。本批仍 provider calls=0，候选未注册，8-Core、默认模型、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。下一精确项是低思考
G53-3-L 与全新 held-out 资产。

## 2026-09-04：RQ-225 低思考 G53-3-L 协议与新鲜资产离线实现

RQ-225 将 RQ-224 之后的前置工作落成可审计的离线控制面：协议切片显式消费候选
`request_policy`，低思考 G53-3-L 固定 `low + 4096`、90 秒工具窗和最多 3 次调用，报告
只保留 body-free 安全身份与计数；新三案例 held-out Dataset、V1.1 Input Plan、
Prompt/Context Snapshot 与合成 fixture 通过 no-I/O 交叉准入。聚焦协议/资产及相邻回归
`20 passed`，provider calls=0。候选未注册，8-Core、默认模型、Portal、Account、Workbench、
Auth、路由和 `production_media=0` 不变。随后修复新模块顶层导入环；提交
`411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的 Actions `33787508488` 三 job exact-SHA
全绿，公共 pytest 为 `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`。当前
checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`；
下一步是明确授权后的真实协议门。

## 2026-09-04：RQ-226 低思考 G53-3-L 真实协议门

RQ-226 在 RQ-225 公共 CI 闭环后按用户“继续”授权，执行一次严格有界的真实候选协议：
`zhipu/glm-5.3-flash`、`reasoning_effort=low`、4096 输出、SDK retries=0，最多 3 次调用。
在 `ac63bf4ee70d61fca78813b200cf7775e5ca61d8` 上，结构化合同 1 次和 `knowledge.search`
工具往返 2 次均通过，协议 `admitted=true`；输入/输出/总 token 为 `1007/84/1091`，累计
延迟 `12062ms`。脱敏回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json`
为 `2511` bytes、SHA-256=`a3077ce6d4729e676d0c0ce0d9a6429153075ca59e0850529dee4e29c0376e35`，
body-free 且 create-only。

该结果只关闭固定三调用协议的真实可达性和归一化，不等于 held-out 领域质量、黄金切片、生产
准入或 8F；候选仍 disabled/未注册，默认模型、产品 Runtime、Portal、Account、Workbench、
Auth、路由和 `production_media=0` 不变。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-protocol / completed-real-observation / pending-next-decision`；
下一步若继续，需另行授权独立三案例 held-out 领域门。

## 2026-09-04：RQ-227 低思考三案例 held-out 领域门真实观察

RQ-227 在 RQ-226 协议门完成后按用户“继续”执行一次冻结的独立领域门。入口修复提交
`659757eca7ff1b658dfd164631512d3964c5a2ff` 的 Actions `33826568517` 三 job
（pytest、PostgreSQL migrations、packaging-smoke）均 `completed/success` 且 head SHA 精确匹配。

真实运行固定 `zhipu/glm-5.3-flash`、低思考/4096、零重试/无恢复/无修订；领域实际调用
`6` 次，累计（含 RQ-226 协议）`9/15` 次，领域 token `17834`、累计 token `18925`，网络已使用。
回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
为 `7537` bytes、SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`，
只保存安全状态/计数/评分和摘要哈希，不含正文、reasoning、Prompt、工具参数、Key 或完整请求标识。

`low_gate_baseline_17` 通过（Evaluation `96`）；`low_gate_user_boundary_23` 的回答完成且评分
`97`，但证据来源为空、注入检查失败，触发 `evidence_missing/unsafe_publication`，因此按首个不安全
失败停止；`low_gate_knowledge_boundary_31` skipped。领域门最终 `admitted=false`，候选仍
disabled/未注册、`production_admitted=false`；这不是 API/适配器崩溃，也不证明模型一般能力。
同一 held-out 资产和回执不可重跑或覆盖；不因该结果静默改变产品 Runtime、默认模型、Portal、
Account、Workbench、Auth、路由、streaming 或 `production_media=0`。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-heldout-domain-gate / completed-real-observation / pending-next-decision`，
下一步先做失败归因/是否另立版本的裁决。

## 2026-09-04：RQ-228 候选领域证据与注入边界离线加固

RQ-228 将 RQ-227 的首个失败拆成两个不可合并的质量边界：检索调用成功不代表存在可归因
来源；数据块中的指令性文本也不能越过数据边界进入公开报告。采用版本化、仅候选启用的
`glm53-flash-domain-quality-v1`，增加最低来源数硬门、可信 system policy 附录、拒绝性脱敏
和 body-free `EvidenceDiagnostics`。本地相关/相邻回归 `102 passed`，provider calls=0；实现
`e2efe8fd75e8cf27cbee7e90484fc90d288ce065` / Actions `33832025848` 三 job exact-SHA 全绿；
默认 Runtime、GLM-5.2 兼容路径、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均不变。当前唯一 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-evidence-injection-hardening / completed-public / pending-next-decision`；
下一步另立全新协议/资产版本并先做 no-I/O 准入，不重跑 RQ-227；真实观察仍需明确授权。
