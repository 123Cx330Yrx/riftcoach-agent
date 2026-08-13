# RiftCoach 路线 v1.3 局部校准

本文件只记录对既有阶段 0-8 路线的增量修正，不增加、删除或重排九个主阶段。

## 1. 决策原则

每项能力以后同时记录：

- 最终目标；
- 当前闭环；
- 下一层深化；
- 高级候选；
- 升级触发条件；
- 最终验收证据。

`V1` 表示首个真实、可测试的闭环，不表示能力上限。高级组件仍必须通过 Bad Case、Eval、成本和运维证据后才能进入生产主链。

## 2. 近期顺序

```text
3G-1 至 3G-3 Tool Calling 契约、能力协商与 Provider Registry
→ 4M RAG 独立评测门禁
→ 5A Agent Loop 教学
→ 5B Skill Contract
→ 5C Skill Router
→ 5D Python 受限 Agent Loop
→ 5E AgentRuntime V1
→ 5P 早期产品纵向切片
→ 5F 第三方 Runtime 采用实验
→ 6A 完整 FastAPI 与 SQL 任务模型
```

原 v1.3 曾把第二 Provider 验证放在 4M 之前。2026-08-04 的后续讨论已调整为：
先冻结 3G-1 至 3G-3，进入 4M 和真实 Skill/Agent 场景；3G-4 至 3G-6 在该场景
形成后再按同一领域评测触发。它们是延后，不是取消。

## 3. 3G 多模型边界

当前唯一真实基线是 GLM。DeepSeek、Qwen、Kimi 等均为候选，尚未锁定第二家。
选择第二 Provider 的触发条件是：出现真实 Skill/Agent 任务后，候选与 GLM 通过
同一套 Tool Calling、结构化输出、错误、质量、延迟和成本评测。第三家只用于验证
扩展性，不以 Provider 数量代替架构证据。

模型能力需要分成三层：启动配置更换默认 Provider、调用方显式选择 Provider、
系统按任务自动路由。Registry 目前只提供前两者所需的内部解析骨架，产品级选择
和自动路由尚未实现；多模型也不等于 Multi-Agent。

3G 声明 Streaming 能力，但完整流式实现可以随阶段 5 产品切片和阶段 6 SSE 消费者逐步补齐。

## 4. RAG 4M 质量门禁

进入依赖 RAG 决策的 Agent Loop 前，补齐：

- 开发集；
- CI 回归集；
- 独立保留集；
- 无答案集；
- 版本冲突集；
- 引用语义支持集；
- 数据集版本和污染记录。

本任务提高评测可信度，不在此时引入 Milvus、Elasticsearch、Neo4j 等重型基础设施。

## 5. Skill Contract 去重

Skill V1 使用：

```text
skills/<skill_name>/manifest.yaml
skills/<skill_name>/SKILL.md
app/skills/models.py
data/evaluation/skills/
```

- `manifest.yaml` 是机器可读的版本、权限、预算和停止契约；
- `SKILL.md` 是任务方法、边界、步骤和示例；
- Pydantic 模型是输入输出 Schema 的唯一代码权威；
- 评测集集中管理，避免每个 Skill 复制一套格式。

## 6. AgentRuntime 演进

V1（阶段 5）：

- `run()`；
- `stream()`；
- 统一输入输出、事件、终止原因、Usage 和 Trace。

V2（阶段 6）：

- `continue_session()`；
- `cancel()`；
- `resume()`；
- 持久状态与 Context Compaction。

V3（按证据进入阶段 8）：

- Fork；
- Steering；
- Background Task；
- Subagent；
- 跨进程事件和 Checkpoint 分支。

## 7. 产品切片

阶段 5 在本地 AgentRuntime 可运行后，增加不依赖临时数据库的早期 API 切片：

```text
POST /reviews/recent
GET /runs/{run_id}
GET /runs/{run_id}/status
GET /runs/{run_id}/report
POST /runs/{run_id}/follow-ups
```

该切片复用现有 Harness Artifact。阶段 6 再加入 SQL、用户隔离、Session、Memory、幂等、恢复、SSE 和完整前端。

## 8. OP.GG 与 Meta

阶段 7 的明确目标包括标准 MCP Client 和 OP.GG MCP 主线接入，但业务层不得依赖 OP.GG 原始字段：

```text
OP.GG MCP
→ OPGGMetaAdapter
→ MetaProvider / MetaEvidence
→ ToolRuntime
→ Skill / Agent
→ Quality Harness
```

实施时仍需验证端点、协议版本、许可和公开部署边界。第一批其他来源只考虑官方补丁和 Data Dragon，不为了形式上的多源同时接入大量网站。

## 9. 阶段 8 双轨

`8-Core` 是必须完成的产品、部署、合规、Eval 和作品集交付线。

`8-Advanced` 至少完成一个高级能力采用实验，包含 Bad Case、实现、对照、消融、成本和 ADR。实验可以得出采用、局部采用或拒绝采用；不预先强制 Multi-Agent、DAG、Agentic Retrieval 或微调上线。

## 10. 当前执行状态

当前仓库已经完成：

```text
3G-1 Tool Calling 内部消息契约
3G-2 Provider 能力协商
3G-3 Provider Registry
4M 独立 RAG 保留集首个门禁
5A 最小 Agent Loop 与真实 knowledge.search 领域切片
5B Skill Contract 与 recent-form-review 样板
5C-1 Skill Router 输入输出契约与三态决策约束
5C-2 Skill Catalog 严格发现、稳定快照与候选投影
5C-3 声明式确定性路由
5C-4 拒绝、排除否决与多候选歧义验收
5C-5-prep-2 single-match-review 第二个真实 Skill Contract
5C-5 双 Skill development/holdout Router Evaluation
5C-6 Model Fallback Decision（ADR-0010 暂缓 LLM fallback）
```

4M 当前使用 7 个小型保留案例，结果用于证明门禁机制可运行，不代表检索已经具备充分泛化能力。后续应扩充按知识类型、版本和位置分层的保留集，但不因此引入重型向量基础设施。

5C 的完整原始检查点和当前状态为：

```text
5C-1 Router Contract          已完成
5C-2 Skill Catalog            已完成
5C-3 Deterministic Router     已完成
5C-4 Rejection / Ambiguity    已完成
5C-5 Router Evaluation        已完成；development 23/23，holdout 11/12
5C-6 Model Fallback Decision  已完成；ADR-0010 暂缓 LLM fallback
5C-exit-review                已完成；合同、证据、限制和 5D 前置项已复核
5D-entry-design               已完成；ADR-0011 与原子检查点已冻结
5D-1 Skill Run Boundary       已完成；身份、run ID 与输入内容绑定已加固
5D-2 Context Builder V1       已完成；最小事实投影、信任分层与整段预算选择已加固
5D-3 Run Compiler & Budgets   已完成；Manifest-only 编译、累计 Context 与总 deadline 已加固
5D-4 Agent Draft & Evidence   已完成；实际知识工具记录已转换为未发布草稿与可审计证据
5D-5 Harness & Typed Output   已完成；统一 preparation 接缝、唯一质量门禁与 Artifact 驱动终态输出
5D-6a Structured Output       已完成；请求合同、Pydantic 校验、一次修复与 fail-closed 边界已建立
5D-6b Provider Gate           进行中；P1-P5 与真实 3-call Adapter 协议切片已通过，近期复盘领域控制器离线完成、真实运行待公开 CI 后执行
```

5C 路由旧开发集有 15 个参与校准的小型单 Skill 案例，历史精确匹配率为 `1.0`、
错误选择率为 `0.0`。它已原样归档并附带 SHA-256 与重建来源说明。现在 Catalog
已有两个真实 Skill，旧结果因候选集合变化而有意过时；双 Skill development v2
的 23 条已全部精确匹配；independent holdout v1 单次运行结果为 11/12，唯一失败
是设备语义假朋友被误选为近期复盘，且未据此修改规则。

源码审计已修正首批 Skill 分类：`recent-form-review` 与 `single-match-review` 是
两个真实用户任务；报告事实审查继续由已经实现的 `EvaluatorStep` 和
`ReviewHarness` 强制执行，不重复包装为内部 Skill。未实现的调用模式合同已取消。
`single-match-review` 已完成，5C-5 第一批已冻结旧单 Skill 基线并建立双 Skill
development/holdout 的角色、污染和版本快照门禁；第二批 development v2 已以
23/23 精确匹配接受并冻结规则，第三批 holdout v1 已单次运行并以 11/12 原样收尾。
5C-6 已基于唯一设备域 Bad Case 完成方案比较：V1 保持确定性 Router，不根据
holdout 调词，也不立即引入模型；类型化入口和澄清优先，模型重开需满足新鲜数据、
结构化输出与质量/成本门槛。5C 退出复核已通过；5D entry design 选择 AgentLoop
作为 Harness 的 evidence-aware draft preparation，并保持 Harness 唯一发布权。
后续顺序为 5D-1 输入/身份/Artifact 边界、5D-2 Context Builder、5D-3 编译与预算、
5D-4 Agent draft/evidence、5D-5 Harness/终态输出、5D-6a 结构化输出、5D-6b 真实
Provider 准入、5D-7 领域评测和 exit review。5D-1 已实现执行前身份与输入完整性
边界；5D-2 已实现 provider-neutral Context Builder，用两个 Skill 各自的 allowlist
投影事实，以 trust 标签区分 system 指令与 data-only 内容，并在 Manifest ceiling 内
整段选择可选 match/citation。5D-3 已实现 `AgentRunCompiler`，只从 Manifest 映射
工具与运行预算，并在每次 Provider 调用前检查包含 Tool Observation 的完整累计消息；
Provider/Tool 共享递减的协作式总 deadline。5D-4 已让两个真实 Skill 在 Fake Provider
下调用真实本地 `knowledge.search`，并只从实际成功的 ToolExecutionRecord 构造
`KnowledgeEvidence`；最终模型文本仍只是未发布 `CoachDraft`。5D-5 已增加统一
`DraftPreparationStep` 与旧顺序 Adapter，让 Agent draft/evidence 进入现有唯一
ReviewHarness；`SkillReviewExecutor` 从 Manifest 映射质量门禁，terminal Skill Output
只从完整性校验通过的最终 Artifact 构造。5D-6a 已建立 Provider-neutral 结构化输出
合同：请求声明 Schema、能力协商要求 structured output、严格 Pydantic Evaluation 验证、
最多一次同合同 repair 和 fail-closed Harness 降级/拒绝。5D-6b 已完成 disabled-thinking
下 P1-P5 真实微探针、生产 Zhipu Adapter 离线双向映射，以及严格 structured request、
现有 AgentLoop 和固定只读知识工具的精确 3-call 真实协议切片；A1/A2 均通过并
`admitted=true`。尚未执行真实领域 Skill/Harness，Prompt E2E Evaluation 也未开始。
近期复盘领域切片离线控制器现已完成：它严格复读并哈希已准入的 3-call 协议结果，
让 AgentLoop 与唯一 ReviewHarness 共用剩余 4-call 的 pre-I/O 预算，并只输出脱敏 typed
report。唯一下一步仍在 5D-6b：先提交并验证精确 SHA 的公开 CI，再按 RQ-027 执行
一次受控真实领域运行；尚未选择第二 Provider，也未进入 5D-7。
原 `prep-1` 与 `prep-3` 均在写代码前取消；动态状态以
`docs/project_execution_state.md` 为准。
`3G-4` 真实第二 Provider、`3G-5` 多 Provider Tool Calling 和 `3G-6` 任务级自动
路由暂不作为连续任务；它们要等 Skill 和 Agent Loop 形成真实调用场景后，按同一
套契约和领域评测重新触发。
