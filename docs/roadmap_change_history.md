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
