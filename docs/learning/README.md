# RiftCoach 学习与工程证据索引

## 1. 这份索引解决什么问题

RiftCoach 的代码增长很快，但“代码已经存在”和“项目所有者能解释清楚”是两条不同的进度线。
以前有些能力已经实现、测试并通过公共 CI，却只在聊天、长计划或零散状态记录中讲过。聊天一旦变长，
就容易出现三个问题：

1. 不知道某个阶段究竟解决了什么；
2. 能运行代码，却说不清数据流、控制流和失败边界；
3. 面试时把开发集结果、参考项目能力或未实现的产品能力说得过头。

这个目录把已有材料组织成一条可重复学习的证据链。它不是第二份路线图，也不改变固定的阶段 0—8。
当前执行位置仍以 [项目执行状态](../project_execution_state.md) 为唯一事实源；这里回答的是：
“为了真正理解已经完成的能力，应该读什么、看什么代码、跑什么测试、怎样准确表述？”

本轮补齐的整体裁决、审计方法、验证结果和下一检查点见
[RQ-067 退出复核](../plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md)。

2026-08-31 的 GLM-5.3-Flash A/B 证据身份学习材料已补充 RQ-179 公共 CI 生命周期、RQ-180 领域门边界及 RQ-181
响应完成度诊断、RQ-182 版本化完成策略与 RQ-183 候选 fresh-recovery 合同：最终实现 A=`9e6d78be…`、Actions run `33378687984` 三 job exact-SHA 通过，随后一次 G53-7
真实尝试以 `provider_response_invalid/incomplete_chat_response` 首错停止；一次独立正文零留存诊断确认首回合
`finish_reason=length` 且 2048 输出额度先被 reasoning 耗尽。历史 fixture 与浅克隆失败为何必须保留、以及为什么当前
不自动重试；RQ-184 已为 RQ-183 候选合同取得实现 A/B 的 exact-SHA 公共 CI，并在同一 A 重取 G53-3（严格 `3/3` 调用通过）。RQ-185 的无响应已由 RQ-186 定位为请求级 timeout 覆盖问题，RQ-187 又在完整 90 秒窗口复核仍无响应，RQ-188 再把传输与生成拆开：合法 Flash 控制、冻结短同步和冻结流式首块均观察到响应。RQ-189 进一步固定上下文和采样参数，确认 `low+2048` 可以在 28.344 秒返回可见正文，而两个 8192 同步请求在 45 秒窗口内未完成；这只是候选诊断，不是生产档案升级。策略、候选 runtime/attempt/预算/Trace 合同和离线 TDD 见 [8E Flash 响应完成策略 walkthrough](8e-glm53-response-completion-strategy-walkthrough.md)、
[8E Flash fresh-recovery 合同 walkthrough](8e-glm53-fresh-recovery-attempt-contract-walkthrough.md) 与 [8E Flash 适配与身份 walkthrough](8e-glm53-adapter-profile-tdd-walkthrough.md)。
该记录不把 8E coverage、领域采用或生产成熟度标为完成。

## 2. 建议怎样学习每一个能力

不要一上来逐行背代码。建议对每个覆盖组做四遍：

### 第一遍：先建立心智模型

只回答四个问题：

- 输入是什么；
- 输出是什么；
- 谁决定下一步；
- 失败时系统收敛到哪里。

### 第二遍：沿代码地图走一遍

从入口开始，依次找到合同、核心实现、外部适配器、持久化和输出。此时重点不是记语法，而是理解
“为什么职责要分层”。

### 第三遍：运行最小示例和聚焦测试

先运行文档给出的 no-I/O 或 Fake 示例，再读测试名称。测试不是为了凑数量，而是把设计承诺变成
可重复证据。涉及 PostgreSQL 并发、迁移和约束的结论，只能由真实 PostgreSQL 测试与公共 CI 支持，
不能用本地 SQLite 或本机 skip 代替。

### 第四遍：用自己的话做面试复述

至少能讲清：问题、方案、取舍、一次真实故障、验证方式和一个仍未解决的限制。每篇实现后复盘都给出
“可以说”和“不可以说”，目的是守住证据边界，而不是准备固定话术。

## 3. 当前覆盖地图

| 覆盖组 | 状态 | 首选材料 | 你学完后应该能解释 |
|---|---|---|---|
| 阶段 0：基线与参考证据 | 完整 | [阶段 0 证据审计](stage-0-baseline-and-reference-evidence.md) | 为什么 RiftCoach 独立开发，以及 EchoMind、Saber、Sea、Pi 分别采纳/拒绝什么 |
| 阶段 1：领域核心 | 完整 | [领域核心 walkthrough](stage-1-domain-core-v1-walkthrough.md) | Riot ID 到确定性 Summary/Report 的完整链路和指标边界 |
| 阶段 2：Harness V1 | 完整 | [Harness 使用与原理](../harness_v1_usage.md) | 草稿为何不能直接发布，评测、修订、Artifact 和状态机如何配合 |
| 阶段 3：Provider / Tool Runtime | 完整 | [Provider 与 Tool Runtime](../provider_tool_runtime_usage.md) | 模型适配与工具可靠性为什么是不同层，怎样重试、熔断和降级 |
| 阶段 4：RAG V1 / 4M | 完整 | [RAG 实现后复盘](stage-4-rag-v1-implementation-review.md) | 父子块、混合召回、RRF、证据门、引用和独立保留集怎样协作 |
| 5A：最小 Agent Loop | 完整 | [Agent Loop V1](../agent_loop_v1.md) | 模型怎样提出工具调用，程序怎样限制并继续循环 |
| 5B：Skill Contract | 完整 | [Skill Contract 实现后复盘](stage-5b-skill-contract-v1-implementation-review.md) | Skill 为什么是声明式能力合同，而不是另一个 Agent 或任意代码插件 |
| 5C：Skill Router | 完整 | [5C 退出复核](../plans/2026-08-07-skill-router-v1-exit-review.md) | 确定性路由、拒绝、歧义和模型 fallback 决策 |
| 5D：受限 Agent Loop | 完整 | [5D 退出审查](../plans/2026-08-15-5d-constrained-agent-loop-exit-review.md) | Context、预算、证据、结构化输出、Harness 的完整控制流 |
| 5E：AgentRuntime V1 | 完整 | [5E 退出审查](../plans/2026-08-17-agent-runtime-v1-exit-review.md) | `run/stream`、观察、Usage、Trace、终态提交和仍保留的运行时限制 |
| 5P：产品纵向切片 | 完整 | [5P 退出审查](../plans/2026-08-17-product-slice-exit-review.md) | HTTP 到 Application、Runtime、Harness、Receipt/Query 的纵向分层 |
| 5F：Pi 采用实验 | 完整 | [5F 退出审查](../plans/2026-08-17-5f-pi-adoption-exit-review.md) | 如何审计第三方 Runtime，以及为什么只保留评测资产而拒绝产品采用 |
| 6A：PostgreSQL 异步任务产品 | 完整 | [6A 设计](../plans/2026-08-17-6a-fastapi-postgresql-task-model-design.md) / [退出复核](../plans/2026-08-18-6a-exit-review.md) | API、Worker、短事务、claim、Artifact/Trace 和恢复边界 |
| Session/Memory 入口设计 | 完整 | [Session/Memory V1 设计](../plans/2026-08-19-stage6-session-memory-design.md) | Session、消息、玩家身份、长期 Memory 与 RAG 为何不能混为一谈 |
| 6B-1：玩家身份持久化 | 完整 | [6B-1 walkthrough](6b-1-player-identity-link-persistence-walkthrough.md) | PUUID、Alias、Owner Relationship、Link Task 及真库迁移事故 |
| 6B-2：异步玩家绑定 | 完整 | [6B-2 walkthrough](6b-2-async-player-link-worker-api-walkthrough.md) | POST/poll、Worker、事务外 Account-V1、短事务终态和隐私投影 |
| 6B-3：Conversation / Message | 完整/公共闭环 | [6B-3 walkthrough](6b-3-conversation-message-foundation-walkthrough.md) / [专用设计](../plans/2026-08-20-conversation-message-foundation-design.md) / [ADR-0040](../adr/0040-conversation-message-foundation-contract.md) | 固定玩家身份、owner 幂等、连续消息序号、归档/隐藏、真库锁与 trigger；实现 SHA `7e4f233` / Actions `32329686381` 已完成 `pytest`、`postgres-migrations`、`packaging-smoke` 公共闭环。限制：公共 API 仍只写 user，assistant terminal、Agent/Review/Memory/Auth/SSE/前端留在后续阶段 |
| 6B-4：Conversation-bound Review Identity | 完整/公共闭环 | [6B-4 walkthrough](6b-4-conversation-bound-recent-review-identity-walkthrough.md) / [专用设计](../plans/2026-08-20-conversation-bound-recent-review-design.md) / [ADR-0041](../adr/0041-conversation-bound-review-task-identity.md) | schema 2.0 Task 原子绑定服务器 Conversation tuple，并通过可信 PUUID 复用既有 Runtime/Harness；实现 SHA `d63f908` / Actions `32347834279` 已完成真库锁/FK/trigger 与 Linux package 三 job 公共闭环 |
| 6B-5：Memory Candidate & Write Gate | 完整/公共闭环 | [walkthrough](6b-5-memory-candidate-write-gate-walkthrough.md) / [专用设计](../plans/2026-08-20-memory-candidate-write-gate-design.md) / [ADR-0042](../adr/0042-use-transactional-typed-materializer-for-memory-candidates.md) | Candidate gate、0005/Repository/API 与事务内 typed materializer 接缝已由 `dd7c9c8` / Actions `32376405150` 完成真库/Linux 三 job 公共闭环；6B-6 已在其上注册真实 target |
| 6B-6：Preferences / Profile / Review Memory | 完整/公共闭环 | [walkthrough](6b-6-preferences-profile-review-memory-walkthrough.md) / [ADR-0043](../adr/0043-adopt-typed-preference-profile-review-memory-targets.md) / [6B-6 设计](../plans/2026-08-20-memory-types-design.md) | 三类 typed target、版本冲突、self/observed 权限、真实 materializer 与 owner-scoped 查询已由 `5531c81` / Actions `32387026797` 完成 pytest、真实 PostgreSQL 和 Linux package 三 job 公共闭环 |
| 6B-7：Training Plan / Progress | 完整/公共闭环 | [walkthrough](6b-7-training-plan-progress-walkthrough.md) / [专用设计](../plans/2026-08-21-training-plan-progress-design.md) / [ADR-0044](../adr/0044-adopt-candidate-backed-training-plan-progress-events.md) | self-only Plan、单 active、0007、final-Artifact Progress、追加式纠错与确定性趋势已由 `f6d8922` / Actions `32397290175` 完成真库/Linux 三 job 公共闭环 |
| 6B-8：Memory-aware Context / Typed Turns | 完整/公共闭环 | [walkthrough](6b-8-memory-aware-context-typed-turns-walkthrough.md) / [专用设计](../plans/2026-08-21-memory-aware-context-typed-turns-design.md) / [ADR-0045](../adr/0045-adopt-run-scoped-memory-context-and-terminal-turn-writer.md) | bounded legal selector、body-free manifest、同 ceiling data-only Context 与 terminal-only Assistant/Candidate 写入边界已由 `aacc11a` / Actions `32403187972` 完成真库/Linux 三 job公共闭环 |
| 6B-9：Lifecycle / Export / Exit Review | 完整/公共闭环 | [walkthrough](6b-9-lifecycle-export-exit-review-walkthrough.md) / [专用设计](../plans/2026-08-21-lifecycle-export-exit-review-design.md) / [ADR-0046](../adr/0046-adopt-centralized-owner-data-lifecycle-service.md) | owner export、三种删除范围、hidden-before-cleanup、retention/purge/补偿与 Session/Memory V1 exit matrix 已由 `cbc7cbd` / Actions `32408101770` 完成 pytest、真实 PostgreSQL 与 Linux package 三 job 公共闭环 |
| 阶段 7：标准 MCP 与动态 Meta entry design | 完整/公共闭环 | [入口设计学习材料](stage-7-standard-mcp-dynamic-meta-entry-design.md) / [ADR-0047](../adr/0047-adopt-standard-mcp-boundary-and-opgg-meta-adapter.md) / [设计](../plans/2026-08-21-stage7-standard-mcp-dynamic-meta-design.md) | 已冻结 Adapter-first、MetaEvidence、分级 OP.GG 准入和 7-1…7-5 顺序；全部五个子检查点已依次公共闭环，Stage 7 已关闭 |
| 7-1：MCP Client pure contract | 完整/公共闭环 | [walkthrough](7-1-mcp-client-contract-walkthrough.md) / [ADR-0047](../adr/0047-adopt-standard-mcp-boundary-and-opgg-meta-adapter.md) / [实施计划](../plans/2026-08-21-stage7-standard-mcp-dynamic-meta-implementation.md) | initialize/version/capability、bounded tool snapshot、allowlist/Schema/drift 与 body-free error 已由 `37f16bc` / Actions `32439753589` 三 job公共闭环；7-2/7-3 后续已关闭，Server/双向退出门未进入 |
| 7-2：MCP transport / discovery | 完整/公共闭环 | [walkthrough](7-2-mcp-transport-and-discovery-walkthrough.md) / [实施计划](../plans/2026-08-21-stage7-standard-mcp-dynamic-meta-implementation.md) / [ADR-0047](../adr/0047-adopt-standard-mcp-boundary-and-opgg-meta-adapter.md) | 有界 in-memory/stdio session、deadline、disconnect/restart、cursor discovery 和 ToolRuntime 映射已由 `f121666` / Actions `32441793585` 三 job 公共闭环；不证明 OP.GG、Meta、Server 或真实互操作 |
| 7-3：OP.GG Meta Adapter | 完整/公共闭环 | [walkthrough](7-3-opgg-meta-adapter-walkthrough.md) / [ADR-0048](../adr/0048-admit-opgg-with-partial-provenance-and-selected-catalog.md) / [专用设计](../plans/2026-08-21-opgg-meta-adapter-design.md) | 官方 Streamable HTTP、admitted-subset discovery、严格 lane-meta parser、partial MetaEvidence、data-only Context 与真实 body-free 单向产品 smoke 已由 `64311a1` / Actions `32455219404` 三 job 公共闭环；其他 OP.GG 工具、Riot+OP.GG join、Server/双向互操作未实现 |
| 7-4：RiftCoach MCP Server | 完整/公共闭环 | [ADR-0049](../adr/0049-adopt-restricted-riftcoach-mcp-server-facade.md) / [设计](../plans/2026-08-21-riftcoach-mcp-server-design.md) / [walkthrough](7-4-riftcoach-mcp-server-walkthrough.md) | strict Session、owner-scoped Facade、verified recent DTO、single-review digest、knowledge attribution 与 evaluation status 已由 `431c584` / Actions `32480827952` 三 job 公共闭环；不含公网 transport/7-5 互操作 |
| 7-5：双向 MCP 互操作与退出审查 | 完整/公共闭环 | [ADR-0050](../adr/0050-adopt-pinned-official-mcp-client-over-stdio-for-interoperability.md) / [专用设计](../plans/2026-08-21-stage7-mcp-interoperability-exit-review.md) / [walkthrough](7-5-mcp-interoperability-exit-review-walkthrough.md) | 实现 `a88fbc4` / Actions `32483521108` 三 job 全绿；同一 clean SHA 已由官方 SDK 1.30.0 Client 调用 RiftCoach stdio Server，且 RiftCoach Client 调用 OP.GG Streamable HTTP；不可覆盖 evidence `fac6fe0` / Actions `32484257736` 最终三 job 全绿并关闭 Stage 7 |
| 阶段 8：Multi-Agent、可靠运行时与产品化 entry design | 完整/公共闭环 | [入口设计学习材料](stage-8-multi-agent-reliable-runtime-productization-entry-design-walkthrough.md) / [ADR-0051](../adr/0051-adopt-stage8-evidence-gated-runtime-fusion-and-productization.md) / [入口设计](../plans/2026-08-22-stage8-multi-agent-reliable-runtime-productization-entry-design.md) | `3431e8b` / Actions `32564500421` 已冻结 8A–8F、8-Core/8-Advanced、Riot+OP.GG EvidenceBundle、前端和 MotionSites 采用门；这仍不表示 Stage 8 产品能力已实现 |
| 8A：Advanced Adoption Gate | 完整/公共闭环 | [walkthrough](8a-advanced-adoption-gate-walkthrough.md) / [ADR-0052](../adr/0052-admit-role-isolated-multi-agent-to-bounded-stage8-experiment.md) / [设计](../plans/2026-08-22-8a-advanced-adoption-gate-design.md) | strict gate、串行 baseline、受限并行 comparator、角色隔离 Multi-Agent candidate 与 deferred 裁决已由 `12ad835` / Actions `32567642315` 三 job 公共闭环；这不表示 8B 已实现或 Multi-Agent 已采用 |
| 8B：Conditional Multi-Agent Experiment | 完整/公共闭环 | [walkthrough](8b-conditional-multi-agent-experiment-walkthrough.md) / [ADR-0053](../adr/0053-reject-role-isolated-multi-agent-and-prefer-bounded-parallel-evidence.md) / [设计](../plans/2026-08-22-8b-conditional-multi-agent-experiment-design.md) | implementation `180bc8b` / Actions `32572085065` 与 result/ADR/evidence `783a329` / Actions `32572610725` 均三 job 全绿；唯一 holdout 裁决 `reject_multi_agent`：候选 18.95% 未达 20%，且与普通并行无隔离增益。8B 已关闭；RQ-083 随后授权 8C |
| 8C：Reliable Runtime Core | 完整/公共闭环 | [walkthrough](8c-reliable-runtime-core-walkthrough.md) / [ADR-0054](../adr/0054-adopt-postgresql-leased-fenced-task-control-plane.md) / [专用设计](../plans/2026-08-22-8c-reliable-runtime-core-design.md) | clean implementation `2df5349` / Actions `32587659678` 的 pytest、PostgreSQL migration/concurrency、Linux package 三 job 全绿；8C coverage 已 complete。正式 Auth、SSE、前端、备份和 8D fusion 仍留后续 |
| 8D：Riot + OP.GG Evidence Fusion Core | 完整/公共闭环 | [walkthrough](8d-riot-opgg-evidence-fusion-core-walkthrough.md) / [ADR-0055](../adr/0055-adopt-typed-evidence-bundle-fusion.md) / [设计](../plans/2026-08-23-8d-riot-opgg-evidence-fusion-design.md) / [实施计划](../plans/2026-08-23-8d-riot-opgg-evidence-fusion-implementation.md) | implementation/evidence `a274b7f` / Actions `32598480400` 三 job 全绿；typed Riot/Data Dragon/official patch/OP.GG partial fusion、no-I/O adapter、digest/provenance/freshness/join/conflict/gap 与 public projection 已有本地/公共证据。真实刷新、8E Web/Auth/SSE/部署仍未实现 |
| 8E：Productization | 进行中/coverage planned | [G53-1/2/3/4/5/7 适配档案、CI、协议与能力门](8e-glm53-adapter-profile-tdd-walkthrough.md) / [RQ-182 响应完成策略](8e-glm53-response-completion-strategy-walkthrough.md) / [RQ-183 fresh-recovery 合同](8e-glm53-fresh-recovery-attempt-contract-walkthrough.md) / [ADR-0071](../adr/0071-adopt-versioned-response-completion-policy.md) / [ADR-0072](../adr/0072-adopt-bounded-fresh-recovery-attempt-contract.md) / [G53-0 无 I/O 审计](../plans/2026-08-31-g53-0-glm53-no-io-audit.md) / [Flash 运行时晋级 ADR](../adr/0070-adopt-glm53-flash-product-runtime-profile.md) / [preflight](../plans/2026-08-23-8e-productization-preflight.md) / [Batch B](8e-player-profile-selection-explicit-routing-walkthrough.md) / [Batch C](8e-evidence-product-api-walkthrough.md) / [Batch D](8e-batch-d-rift-command-center-walkthrough.md) / [Live 接线](8e-live-workbench-integration-walkthrough.md) / [Batch E implementation](8e-batch-e-security-deployment-implementation-walkthrough.md) / [视觉合同](8e-portal-workbench-visual-contract-walkthrough.md) / [Timeline](8e-timeline-dto-ui-walkthrough.md) / [双语 foundation](8e-bilingual-product-surface-foundation-walkthrough.md) / [三层产品旅程](8e-portal-account-workbench-journey-walkthrough.md) / [Portal Motion Polish](8e-portal-motion-polish-walkthrough.md) / [I2V audit](../plans/2026-08-25-8e-image-to-video-candidate-audit.md) / [Veo v5 failure](../plans/2026-08-26-8e-veo-spatial-v5-upstream-failure.md) / [Seedance candidate](../plans/2026-08-26-8e-seedance25-sample-audit.md) / [Seedance edit preflight](../plans/2026-08-26-8e-seedance25-video-edit-preflight.md) / [Seedance edit 400](../plans/2026-08-26-8e-seedance25-video-edit-400-diagnosis.md) / [豆包 comparator](../plans/2026-08-26-8e-doubao-seedance25-comparator-audit.md) / [即梦 preflight](../plans/2026-08-27-8e-jimeng-seedance25-smart-edit-preflight.md) / [即梦 result/postprocess](../plans/2026-08-27-8e-jimeng-seedance25-smart-edit-result-audit.md) / [ADR-0068](../adr/0068-adopt-mother-image-global-loop-scenes-and-semantic-activation.md) / [RQ-197 边界观察实现](8e-glm53-candidate-boundary-observation-implementation-walkthrough.md) | 已闭环批次不变；G53-0 已完成本地无 I/O 审计，G53-1 已完成普通 API 的离线适配档案，G53-2 已由 `0f97b92` / Actions `33325222755` 完成 exact-SHA 三 job 公共验证，G53-3 已在更换普通 API Key 后通过 A1/A2（严格 3/3 次调用）；G53-4 已执行一次但未准入，G53-5 新鲜矩阵 11/11 calls 中 7/8 通过，RQ-175/176 已完成 Flash 专属运行时的本地接线，RQ-179 已为最终实现 A 取得 exact-SHA 公共 CI，RQ-180 已完成一次 G53-7 真实尝试但首例以 `provider_response_invalid/incomplete_chat_response` 停止且未准入，RQ-181 又确认首回合 `finish_reason=length` 且 2048 输出额度先被 reasoning 耗尽；RQ-182 已完成策略设计与离线 TDD，RQ-183 已完成候选 runtime/attempt/预算/Trace 离线合同，RQ-184 已完成 A/B exact-SHA 公共 CI 与同 SHA G53-3；RQ-185 两次独立诊断启动均无可观察响应，RQ-192–RQ-196 已完成候选流合同/适配器/设计材料，RQ-197 已完成边界观察本地实现与 `163 passed`，同 SHA 公共 CI 待验证。严格策略不续接、8192/一次 fresh-recovery 仍为未注册候选；公共生产准入仍未完成，production media `0`。 |

> 8E 表格中的旧“下一门为传输/代理边界复核”、RQ-195 的
> `candidate-runtime-wiring-design / pending` 以及 RQ-197 的公共 CI 待验证均是历史摘要；RQ-198 已取得
> exact-SHA 公共 CI，当前唯一下一门更新为 `candidate-evaluation-harness-design / pending`。

8E 当前最新候选接缝材料：[RQ-192/RQ-193 walkthrough](8e-glm53-provider-neutral-stream-adapter-walkthrough.md) /
[ADR-0073](../adr/0073-adopt-provider-neutral-stream-assembly-contract.md) /
[实施计划](../plans/2026-09-01-glm53-provider-neutral-stream-adapter-contract.md)；三者记录离线合同、13 项
测试内智谱 conformance 和同 SHA 公共 CI，但不把夹具通过写成产品 streaming 或生产准入。

RQ-194 本地实现材料：[walkthrough](8e-glm53-explicit-zhipu-neutral-stream-adapter-walkthrough.md) /
[ADR-0074](../adr/0074-propose-explicit-zhipu-neutral-stream-adapter.md) /
[计划](../plans/2026-09-01-glm53-explicit-zhipu-neutral-stream-adapter-seam.md)；记录候选级、显式调用的
`ZhipuStreamAdapter`、`ZhipuProvider.stream_adapter()` 工厂及 `stream_events()`/`assemble()` API。
本地聚焦测试为 `20 passed`；提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588`
三 job exact-SHA 全绿。这仍不代表产品已打开 `capabilities.streaming` 或完成生产准入。

RQ-195 候选 runtime 接线评审材料：[walkthrough](8e-glm53-candidate-runtime-wiring-review-walkthrough.md) /
[ADR-0075](../adr/0075-keep-glm53-candidate-stream-caller-isolated.md) /
[评审计划](../plans/2026-09-01-glm53-candidate-runtime-wiring-review.md)；记录了完整流与不完整流边界、
四元身份、BoundaryObservation、候选 ledger/Trace 以及“不直接接入产品 Runtime”的决策。

RQ-196 候选 runtime 接线设计材料：[walkthrough](8e-glm53-candidate-runtime-wiring-design-walkthrough.md) /
[ADR-0076](../adr/0076-freeze-glm53-candidate-boundary-observation-wiring.md) /
[设计计划](../plans/2026-09-01-glm53-candidate-runtime-wiring-design.md)；冻结了候选四元身份、body-free
BoundaryObservation、共享事件校验、隔离 v2 transport、预算/结算顺序和独立 Trace 投影。Flash 是当前唯一主力候选目标，
但候选仍未注册、`execution_allowed=false`，不代表产品默认或生产准入。RQ-197 已将该设计落成
fake/local 边界观察实现，RQ-198 已完成同 SHA 公共 CI；当前下一精确项为 `candidate-evaluation-harness-design / pending`。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 学习材料：[实现 walkthrough](8e-glm53-candidate-boundary-observation-implementation-walkthrough.md)。本轮
新增隔离 `CandidateStreamBoundaryObserver`、body-free `BoundaryObservation`、候选 v2 注入式 transport port 和
`CandidateStreamTrace`；共享事件校验同时服务完整 assembler、智谱翻译与候选观察器。测试覆盖完整/不完整流、身份/工具/
预算/时钟/关闭异常、状态伪造与脱敏序列化，聚焦及相邻回归 `163 passed`。候选仍未注册、`execution_allowed=false`，
不改产品 Runtime、默认模型、Portal、Account、Workbench、Auth 或 `production_media=0`。同一干净实现提交的公共 CI
尚待验证；通过后再决定候选 harness、fresh-recovery、G53-7 与生产准入。

本次交接材料：[8E Agent 主线交接与 README 事实版 walkthrough](8e-agent-mainline-handoff-readme-walkthrough.md)；它只记录当前事实和后续闸门，不把 Portal/Account 的本地视觉切片、GLM-5.3 协议候选或未来 Coach 说成已完成产品。
> 注：上方 8E 表格行只概括当前证据；RQ-170、RQ-172、RQ-173、RQ-175、RQ-182、RQ-183、RQ-184 的完整边界和不可变结果详见对应 walkthrough 与项目状态记录。 |

RQ-176 已将 RQ-175 的 Flash 专属运行时档案接入产品组合根、Worker、Runtime、Agent/`llm.chat`、预算包装器、
Provider、运行时策略和 Trace；Flash 目标是产品正常运行路线，GLM-5.2 只作显式兼容/应急回退。Root/Factory/Runtime
要求精确 Flash 在组合阶段显式绑定，或从已绑定同一注册档案的 concrete Provider 自动推断，避免 30 秒质量门和 90 秒
执行窗隐式分裂。新实现仍需 exact-SHA 公共 CI、
同 SHA G53-3、独立 G53-7、黄金切片与生产安全/部署合规；旧数据集的 30 秒仍是质量资源阈值。

RQ-178 又补齐了 G53-7 的 A/B 身份接缝：实现提交 A、协议 `code_sha`、证据提交 B 及各自 CI 见证分开记录，
本地预检从 B 的 Git blob 核对 canonical-LF 摘要、当前 `HEAD=B` 和只新增证据文件的差异；该接缝本地聚焦
`53 passed`，不等于领域采用、公共生产准入或 8E 完成，A′/B′ 仍需后续冻结。

### 2026-08-31：RQ-170 G53-4 领域门结果校正

G53-4 已按一次性授权执行一次本地真实门：独立三案例输入和 no-I/O preflight 通过，首案因
`unsupported_parallel_tool_calls` 在 Adapter 边界拒绝，后两案跳过，结果为 `completed-local-rejected`；
领域 `1/12` calls、`0` normalized tokens，累计含 G53-3 为 `4/15` calls、`1115` tokens。不可变结果文件为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_v1.json`，不含 Key、Prompt、
响应正文或 reasoning。新 runner/资产尚无 exact-SHA 公共 CI，G53-4 不准入默认；Stage 8/8E 继续进行中。

RQ-109 已授权启动 RQ-108；ADR-0068、正式设计、implementation plan 和 design-stage walkthrough 已按
八维 planned 路径登记，并由 `b3b5280/32812868683` 与 state closure `b7e63e9/32813407485` 完成 exact-SHA
公共门。runtime Task 1 又由 `1b146e6/32826953474` 公共关闭；当前只进入 Task 2，这些证据仍不能冒充
production media 或视觉签收。

“完整”表示仓库中已经具备八类持久证据，并不表示项目已生产就绪，也不表示项目所有者已经学会。
个人理解进度需要通过实际复述、读码、运行和问答单独确认。

## 4. 八类证据是什么

机器可检查的 [覆盖账本](coverage.yaml) 为每个完成组绑定八类材料：

1. 问题与原理；
2. 设计与实际实现；
3. 代码地图；
4. 数据流与控制流；
5. 源码、测试、CI 与限制证据；
6. 安全运行方法；
7. 失败、安全和范围边界；
8. 面试准确表述。

同一份成熟退出审查可以承担多个维度；没有必要为每个小检查点制造一篇重复文档。反过来，聊天里
“讲过了”、测试总数、提交存在或 README 一句话也不能单独冒充完整覆盖。

## 5. 防复发门怎样工作

运行：

```powershell
.\.venv\Scripts\python.exe scripts\check_project_governance.py
```

治理检查会验证：

- `coverage.yaml` schema 与状态是否合法；
- coverage `sequence` 是否唯一并严格递增，防止靠移动列表项绕过前序门；
- coverage group ID 及 YAML 中的人类可读镜像是否符合脚本内固定的 canonical order，防止同时重排并重编号绕过前序门；
- canonical 当前 checkpoint 是否被登记；
- 当前 checkpoint 之前的覆盖组是否全部完成；
- complete 组是否具备八个维度；
- 证据是否指向仓库内存在、非空的 Markdown 文件。

因此，6B-3 完成后如果没有把它从 `planned` 改为 `complete`、补齐八类证据，就不能在治理绿灯下把
canonical 推进到 6B-4。这能防止“代码写完就一路往后走，教学与工程说明以后再补”的问题再次发生。

## 6. 证据强度排序

遇到资料冲突时，按下面顺序判断：

```text
当前 RiftCoach 源码 + 可重复测试 + exact-SHA CI
    > 已确认 ADR / 设计 / 退出复核
    > 参考项目真实源码与测试
    > 参考项目文档
    > 导出的历史对话与聊天建议
```

历史对话和外部项目能帮助提出方案，但不能自动改变当前路线或证明 RiftCoach 已实现某个能力。

## 7. 本索引不代表什么

- 不代表 RiftCoach 已经完整接入 EchoMind、Saber、Sea、Pi、LangGraph 或 Claude Agent SDK；
- 不代表当前有正式公网 OIDC/RSO 账号验证、HTTPS edge、已部署 Web 或生产级运维；SSE 与前端代码已有公共切片证据，但不等于公网部署；
- 不代表 RAG 开发集满分等于未知问题上的泛化满分；
- 不代表 GLM、DeepSeek 或其他 Provider 已通过全部领域质量准入；
- 6B-9 与 Session/Memory V1 已完成公共 PostgreSQL/package 闭环；这仍不表示正式 Auth/RSO、备份副本擦除、
  公网部署或 Stage 8 已实现。Stage 7 入口与 7-1…7-5 已公共闭环；实现、clean-SHA 双向真实门和
  evidence exact-SHA 均有独立证据。OP.GG 仍只证明 lane-meta partial provenance，不证明全工具、精确
  patch/freshness 或 Riot+OP.GG 数据融合；Stage 8 entry design、8A 与 8B 已公共闭环，8B 唯一 holdout 形成
  reject Multi-Agent 结论。8C 已由 `2df5349/32587659678` 公共闭环；RQ-084 授权的 8D 已有本地
  EvidenceBundle contracts/fusion/adapters 已由 `a274b7f/32598480400` 公共闭环并完成八维 coverage；8E 已有
  Batch B/C/D、Live、E1–E5、Auth gate、Timeline 公共证据与当前 foundation 本地实现，但完整 8E、Portal
  Motion Polish、可追问 Coach、正式实时 refresh、已部署 Web 与 8F 尚未完成。

这些边界既是工程事实，也是项目在面试中保持可信度的重要部分。README/作品集研究按 RQ-085 持续广泛采样
高星与低星但信息架构优秀的项目；架构图、流程图、产品展示图按信息目的选择真实截图、AI 概念图、SVG 或
Mermaid，并在 8F 统一审查许可、真实性和可访问性。

### 2026-08-27：Seedance v3 运动合同复盘

Seedance 2.5 v3 的 12 秒输出（task `task_kOu...v6tW`）技术上可播放，但视觉上被拒绝：左 Rift 形成硬同心环，
道路基础流动延后，中央 burst 过曝并画出横向直线，右侧在 burst 外近乎静止，整体 near/mid/far 呼吸不足。
这次复盘的关键学习点是：区域/九宫格“有变化”不等于全幕持续运动；必须分别验证常驻基础层、事件层、右场独立
活动和首尾相位。下一版先重写 source-side motion contract，不降低 source/seam 门、不付费盲重抽、不接 runtime。

### 2026-08-31：RQ-185 候选恢复诊断中断

候选恢复合同、公共 CI 与同 SHA 协议通过不等于真实恢复已经可用。RQ-185 的两次独立启动均只进入
`primary` 首回合，约 60 秒内没有可观察响应，也没有 Usage、finish reason、Trace 或结果文件；没有发送
`fresh_recovery`。学习记录因此必须把“外层进程未返回”“SDK/代理传输边界”和“模型响应失败”分开，
不能把没有响应的进程直接归因于模型。后续若获授权，先复核传输/代理截止；严格 Flash v1 的
2048/零额外调用与候选未注册状态不变。

### 2026-09-01：RQ-186 请求级 timeout 的层级教训

客户端默认 timeout 可能被具体请求的 timeout 覆盖；诊断“20 秒为何没停”时，必须检查最终 SDK payload，而不是只看
client factory。RQ-186 用 payload 断言和一次真实调用确认 30 秒请求截止在约 30.141 秒生效，并生成 body-free
fail-closed 结果。与此同时，transport timeout 只说明该窗口内没有收到响应；没有 Usage、finish reason 或正文时，
不能推断模型能力、生成阶段或计费。因为 30 秒低于候选 90 秒 Agent 窗口，下一步属于延迟预算决策，不是自动重试。

RQ-187 又用候选完整 90 秒请求窗口复核：唯一 primary 在 90.188 秒仍无响应并以 transport timeout 结束。
这排除了“只是诊断窗口太短”，但仍不能把无响应直接解释成模型失败；必须把连接、代理读取、首字节和服务端生成
阶段分开观测。没有 Usage 时，费用仍只能记为 unknown；候选也不能因超时结果自动升级。

### 2026-09-01：RQ-188 如何把“不可达”与“已开始生成”分开

这批诊断先纠正一个容易误判的实验形状：GLM-5.3-Flash 的 thinking 必须保持 enabled，不能用 disabled 控制去判断网络是否可达。合法的低推理档位最小请求收到响应，说明 endpoint/model 路径确实可达；16 token 只够产生 reasoning，marker 未出现是额度耗尽，不是认证失败。

接着对同一冻结上下文做两路观察：256 token 的同步请求收到有效 Usage，但以 `length + 空正文 + 非空 reasoning` 结束；8192 token 的流式请求在约 687ms 先给出 `delta_reasoning` 首块。第二路只读首块便关闭，因此学习时必须区分“首字节/首块已到”和“完整流已装配并收到终止 Usage”。

正式结果 `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51` 只支持三个结论：传输路径可达、生成已经开始、小额度同步请求会先耗尽 reasoning。它不支持完整 streaming、长请求根因、模型一般质量或生产准入结论。下一步是版本化的输出额度/推理档位校准；严格 Flash v1 的 2048/零额外调用和候选未注册状态不变。

### 2026-09-01：RQ-189 为什么更高输出上限不等于更容易完成

RQ-189 在相同冻结上下文、采样参数和合法 thinking 形状下分别观察三路请求。`low+2048` 在 28.344 秒返回
`finish_reason=stop` 和可见正文；`low+8192`、`max+8192` 都在 45 秒请求截止内没有完整同步响应。这个结果说明
“允许更多输出”并不会自动降低首个完整响应的延迟，也不能用更高上限替代流式观测或明确的请求截止。

三份结果都不保存 Prompt、正文或 reasoning，只记录状态、Usage 数字、延迟和哈希。两次 8192 超时没有 Usage，
所以不能据此断言模型质量差、账号没权限或一定发生了计费；`low+2048` 成功也只证明这份冻结上下文可完成，不能直接
升级为领域或生产准入。下一批应验证流式请求何时出现首个可见正文，并把 `clear_thinking` 的请求形状与产品的
保留推理合同分开记录；严格 Flash v1 继续保持 2048/零额外调用。

### 2026-09-01：RQ-190 为什么“首个正文”不能等同于“完成”

RQ-190 在冻结上下文上分别测试了 `clear_thinking=true` 和 `false` 的低推理、2048、流式请求。两路都在约 1.5 秒
收到首块，并在约 2.5–3.9 秒出现首个非空可见正文；这证明用户可见输出可以早于完整终态到达。探针随后主动关闭，
因此没有终态 finish reason 或 Usage，预算状态必须记为 unknown，不能把资源数字写成零或宣称完整流式能力。

`clear_thinking` 在这里只是单轮请求形状的共现变量。真正的跨轮思考保留/清理和 reasoning 精确回放仍未测，当前产品
profile 也没有被改写。学习时应把“首块”“首个可见正文”“终态/Usage”“完整 provider-neutral 装配”分成四道证据门。

### 2026-09-01：RQ-191 如何证明“完整流”而不是只看到首正文

RQ-191 沿用当前产品的 `clear_thinking=false`、低推理、2048、流式形状，把一条冻结上下文流完整读到结束。首块约
2.203 秒、首正文约 3.531 秒，24.140 秒收到 `finish_reason=stop` 和有效 Usage（1973 输入、652 输出），说明供应商
流本身可以在这个案例中完整终止并计量。与 RQ-190 的主动早退结果相比，关键差别是本次不在首正文处关闭，并允许读取
末尾 Usage-only 块。

这仍不是产品已接入 streaming 的证明：只覆盖一个上下文/档位，不包含工具流、跨轮 reasoning 回放或公共 provider-neutral
接口。学习和面试表述要分清“原始供应商流完整”“适配器合同通过”“产品 runtime 接线”“领域/生产准入”四个层级。

### 2026-09-01：RQ-192 提供商无关流式装配合同

RQ-192 把 RQ-191 的原始流观察落成一个不依赖 SDK 的候选接缝：先把厂商分块翻译成
`ProviderStreamEvent`，再由单次装配器在真实 EOF、终止原因和有效 Usage 都成立时生成完整回答。
工具片段按连续索引装配，正文/工具互斥，JSON 重复键、非有限数字、深度和数量上限均拒绝；
首次合同错误会毒化实例，Trace 与结果默认 repr 都不泄露正文或工具参数。聚焦测试为 `29 passed`，
但这仍不是产品 streaming 接入或生产准入。详见 [RQ-192 walkthrough](8e-glm53-provider-neutral-stream-adapter-walkthrough.md)、
[ADR-0073](../adr/0073-adopt-provider-neutral-stream-assembly-contract.md) 与
[实施计划](../plans/2026-09-01-glm53-provider-neutral-stream-adapter-contract.md)。

### 2026-09-01：RQ-193 智谱流式分块 conformance

RQ-193 在学习材料的测试模块内建立 fake `_FixtureZhipuStreamAdapter`，把代表性的
OpenAI-compatible 智谱分块投影为 `ProviderStreamEvent`，再交给同一个
`ProviderStreamAssembler`；正文/reasoning、工具别名与参数分片、坏形状、终态边界、异常
`abort()`、正文空白保留和 Trace 脱敏都有可复现断言。聚焦测试为 `13 passed`，并用 fake
client 与旧 `ZhipuProvider.chat_stream()` 做语义对照。

该 translator 只是测试夹具，不是生产适配器；`8bcbaa5` 的同 SHA 公共 CI run
`33489903978` 三 job 全绿且 `head_sha` 精确匹配，并包含全部 Trace 脱敏断言。后续候选接线仍须单独裁决 runtime、预算、
Trace、回退和失败门；在裁决前不打开 `capabilities.streaming`、不注册候选或执行 G53-7。

### 2026-09-01：RQ-194 显式智谱→中立适配接缝（公共闭环完成）

RQ-194 已把早期设计草案（其中的占位模块/API 仅作历史记录）落成调用方显式取得的
`ZhipuStreamAdapter`：`stream_events(request)` 将已绑定的 Zhipu raw chunks 翻译为 `ProviderStreamEvent`，
`assemble(request, *, max_output_tokens=None, require_request_identity=True)` 再交给
`ProviderStreamAssembler`；`ZhipuProvider.stream_adapter(*, tool_stream=False)` 是显式工厂。

学习时仍应按四层区分：原始供应商流、适配器合同、产品 runtime 接线、领域/生产准入。实现继承可信 provider profile
的 `max_output_tokens` 上限（1–8192），请求 cap 只能收紧；默认要求 request identity，Trace/错误/ repr 只保留
SHA-256 摘要。单流必须正常 EOF、terminal 与有效 Usage，取消或迭代器/翻译/关闭异常均 `abort()`/fail-closed；
不 retry、不 recovery、不执行 ToolRuntime，只支持 fake/local evidence。聚焦测试为 `20 passed`；提交
`a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588` 三 job exact-SHA 全绿。这只证明候选
接缝公共可复现，不能写成产品 runtime 或生产准入。

`capabilities.streaming` 仍为 `False`，严格 Flash v1 仍 2048/零额外调用，默认模型、AgentLoop、Workbench、Portal、
Account、Auth、路由、预算、Trace 和 `production_media=0` 均不变，候选未注册。下一门是独立裁决 runtime 接线范围。

### 2026-09-01：RQ-195 候选 runtime 接线架构评审

RQ-195 复核了 RQ-194 的适配器和产品 Runtime 合同，确认 `assemble()` 只交付真实 EOF、合法终止和有效 Usage 齐全的
完整 `stop`/`tool_calls` 流；`length`、缺终止、缺 Usage、读取/翻译/关闭异常均 fail-closed，不能把异常当作候选恢复资格。
因此不把 adapter 包装成 `LLMProvider`，也不在 `AgentLoop` 增加隐式 streaming 分支。未来若单独授权，先设计隔离的
`CandidateStreamEvaluationHarness` 和只输出字段状态、finish code、Usage 数字、耗时、安全错误码的
`BoundaryObservation`，再由独立 ledger/allow-list Trace 投影处理候选预算与撤出。候选仍未注册且
`execution_allowed=false`，严格 Flash v1 2048/零额外调用、产品 Runtime、Workbench、Portal、Account、Auth、路由和
`production_media=0` 均不变。下一精确项为 `candidate-runtime-wiring-design / pending`。

### 2026-09-01：RQ-196 候选 runtime 接线设计（历史状态）

RQ-196 把用户对 GLM-5.3-Flash 的选择落实为“唯一主力候选目标”，但仍保留候选/生产边界：设计门已完成，尚未注册
为全产品默认，也未执行 recovery、G53-7 或真实新一轮调用。学习重点是四元身份绑定、body-free `BoundaryObservation`、
完整流与不完整流的分流、共享事件校验、隔离 v2 transport、严格预算结算和独立 Trace 投影。

新增材料见 [RQ-196 walkthrough](8e-glm53-candidate-runtime-wiring-design-walkthrough.md)、
[ADR-0076](../adr/0076-freeze-glm53-candidate-boundary-observation-wiring.md) 与
[设计计划](../plans/2026-09-01-glm53-candidate-runtime-wiring-design.md)。当时下一精确项为
`candidate-boundary-observation-contract-implementation / pending`；该实现门已由 RQ-197 推进。
不改产品 Runtime、默认模型、Portal、Account、Workbench、Auth 或 `production_media=0`。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 已在隔离分支完成 fake/local 边界观察合同：新增精确 candidate binding、body-free
`BoundaryObservation`、不可变终态快照、字段 presence/状态聚合、候选 v2 注入式 transport port 和
`CandidateStreamTrace`，并让完整 assembler、智谱翻译与观察器共享事件级校验。完整/不完整流、身份/工具/预算/时钟/
关闭异常和状态伪造矩阵均通过，聚焦及相邻回归为 `163 passed`；同一干净实现提交的 exact-SHA 公共 CI 尚待验证。
候选仍未注册、`execution_allowed=false`，不改产品 Runtime、默认模型、Portal、Account、Workbench、Auth 或
`production_media=0`。通过公共 CI 后才另行裁决候选 harness、fresh-recovery、G53-7 与生产准入。

### 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

RQ-197 的实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 已由 Actions run `33507627615` 完成
exact-SHA 公共验证；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，公共 pytest 为
`2178 passed, 145 skipped, 1 warning, 127 subtests passed`。该证据不改变候选/生产边界，仍不注册候选、
不打开 `capabilities.streaming`、不发真实 API 或执行 recovery/G53-7。收口后的下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
本轮到此暂停，后续需用户明确继续。
