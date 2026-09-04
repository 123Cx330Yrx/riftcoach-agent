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

> 当前学习指针（2026-09-04，RQ-226）：先阅读 [低思考协议 walkthrough](8e-glm53-low-profile-protocol-and-assets-offline-implementation-walkthrough.md)、
> [ADR-0091](../adr/0091-design-glm53-low-profile-heldout-domain-gate.md) 与 [实施计划](../plans/2026-09-04-glm53-low-profile-protocol-and-assets-offline-implementation.md)。
> RQ-226 已在用户授权下完成一次严格 `3/3` 的真实低思考协议门；当前 checkpoint 是
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-protocol / completed-real-observation / pending-next-decision`，
> 8E coverage 仍 planned，候选注册、领域门、黄金切片、生产准入和 8F 均未进入。

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
| 8E：Productization | 进行中/coverage planned | [G53-1/2/3/4/5/7 适配档案、CI、协议与能力门](8e-glm53-adapter-profile-tdd-walkthrough.md) / [RQ-182 响应完成策略](8e-glm53-response-completion-strategy-walkthrough.md) / [RQ-183 fresh-recovery 合同](8e-glm53-fresh-recovery-attempt-contract-walkthrough.md) / [ADR-0071](../adr/0071-adopt-versioned-response-completion-policy.md) / [ADR-0072](../adr/0072-adopt-bounded-fresh-recovery-attempt-contract.md) / [G53-0 无 I/O 审计](../plans/2026-08-31-g53-0-glm53-no-io-audit.md) / [Flash 运行时晋级 ADR](../adr/0070-adopt-glm53-flash-product-runtime-profile.md) / [preflight](../plans/2026-08-23-8e-productization-preflight.md) / [Batch B](8e-player-profile-selection-explicit-routing-walkthrough.md) / [Batch C](8e-evidence-product-api-walkthrough.md) / [Batch D](8e-batch-d-rift-command-center-walkthrough.md) / [Live 接线](8e-live-workbench-integration-walkthrough.md) / [Batch E implementation](8e-batch-e-security-deployment-implementation-walkthrough.md) / [视觉合同](8e-portal-workbench-visual-contract-walkthrough.md) / [Timeline](8e-timeline-dto-ui-walkthrough.md) / [双语 foundation](8e-bilingual-product-surface-foundation-walkthrough.md) / [三层产品旅程](8e-portal-account-workbench-journey-walkthrough.md) / [Portal Motion Polish](8e-portal-motion-polish-walkthrough.md) / [I2V audit](../plans/2026-08-25-8e-image-to-video-candidate-audit.md) / [Veo v5 failure](../plans/2026-08-26-8e-veo-spatial-v5-upstream-failure.md) / [Seedance candidate](../plans/2026-08-26-8e-seedance25-sample-audit.md) / [Seedance edit preflight](../plans/2026-08-26-8e-seedance25-video-edit-preflight.md) / [Seedance edit 400](../plans/2026-08-26-8e-seedance25-video-edit-400-diagnosis.md) / [豆包 comparator](../plans/2026-08-26-8e-doubao-seedance25-comparator-audit.md) / [即梦 preflight](../plans/2026-08-27-8e-jimeng-seedance25-smart-edit-preflight.md) / [即梦 result/postprocess](../plans/2026-08-27-8e-jimeng-seedance25-smart-edit-result-audit.md) / [ADR-0068](../adr/0068-adopt-mother-image-global-loop-scenes-and-semantic-activation.md) / [RQ-197 边界观察实现](8e-glm53-candidate-boundary-observation-implementation-walkthrough.md) / [RQ-200 候选评估台实现](8e-glm53-candidate-evaluation-harness-implementation-walkthrough.md) / [RQ-202 recovery 诊断边界复核](8e-glm53-candidate-recovery-diagnostic-review-walkthrough.md) / [RQ-204 recovery 诊断实现](8e-glm53-candidate-recovery-diagnostic-version-implementation-walkthrough.md) | 已闭环批次不变；RQ-204 fake/local 实现已完成，候选注册、同一实现 exact-SHA 公共 CI、真实 recovery、领域/生产准入仍未完成；严格策略不续接、8192/一次 fresh-recovery 仍为未注册候选，production media `0`。 |

> 8E 表格中的旧“下一门为传输/代理边界复核”、RQ-195 的
> `candidate-runtime-wiring-design / pending` 以及 RQ-197 的公共 CI 待验证均是历史摘要；RQ-198 已取得
> exact-SHA 公共 CI，RQ-199 已完成隔离候选评估台设计，RQ-200 已完成 fake/local 实现；这些是历史摘要，
> 当前学习指针见本文开头的 RQ-212 校正。

RQ-203 已完成版本化候选 recovery 诊断协议设计（见下方材料）；上表中 RQ-202 的“下一步设计”文字仅保留
历史快照，RQ-204 已完成 fake/local 版本化诊断实现，RQ-205 已完成同 SHA 公共 CI 与协议演练，RQ-206 已完成 1 次
有界真实 primary 观察并以 `fail_closed / elapsed_limit` 收口，RQ-207 已完成候选硬墙钟会话与 Usage 尾帧本地实现；
四文件聚焦回归（deadline 10、v2 24、real 8、adapter 25）统一为 `67 passed`；RQ-208 已完成 RQ-207 的
exact-SHA 公共 CI（提交 `015b022bfce6d03452f753794ac126a377f8355b` / Actions run `33613113829` 三 job
`completed/success`），公共 CI 已闭环；这段“下一门”是 RQ-208 历史快照，当前学习指针见本文开头的 RQ-212 校正。

> 表格中 8E 行较早的“RQ-204 fake/local、公共 CI、真实 recovery 未完成”是历史快照；以本段和下方 RQ-205/RQ-206/RQ-207
> 记录为准。RQ-206 的真实观察和 RQ-207 的本地实现均不提升产品 streaming、默认模型或生产准入；Stage 8/8E 仍为
> `in_progress`，候选保持 disabled/未注册。

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
fake/local 边界观察实现，RQ-198 已完成同 SHA 公共 CI；RQ-199 又完成了 staged ledger、单次事件泵和独立
body-free receipt 的候选评估台设计，RQ-200 已完成 fake/local harness 实现，RQ-201 已完成其 exact-SHA
公共 CI，当前下一精确项为
`candidate-recovery-diagnostic-version-implementation / pending-user-authorization`。

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

### 2026-09-02：RQ-199 隔离候选评估台设计

RQ-199 学习材料：[设计 walkthrough](8e-glm53-candidate-evaluation-harness-design-walkthrough.md) /
[ADR-0077](../adr/0077-design-isolated-glm53-candidate-evaluation-harness.md) /
[实现计划](../plans/2026-09-02-glm53-candidate-evaluation-harness-design.md)。本门说明为什么
真实 primary 必须在 I/O 前预留、但 recovery plan 又只能在真实边界观察后冻结；设计采用
candidate-only staged ledger，拒绝 sentinel snapshot 和结束后才 reserve。一条 normalized
stream 只经一次事件泵，同时喂给 body-free observer 与仅内存 assembler；新的 receipt 不保存
正文、reasoning、工具参数、Prompt、Key 或原始 request ID。

该门只有设计证据，没有 `app/` 实现或真实调用。当前 activation disabled，候选仍未注册、
`execution_allowed=false`、`capabilities.streaming=False`；严格 Flash v1、产品 Runtime、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。

### 2026-09-02：RQ-200 隔离候选评估台本地实现

RQ-200 学习材料：[实现 walkthrough](8e-glm53-candidate-evaluation-harness-implementation-walkthrough.md) /
[实现计划](../plans/2026-09-02-glm53-candidate-evaluation-harness-implementation.md) /
[ADR-0077](../adr/0077-design-isolated-glm53-candidate-evaluation-harness.md)。本门把设计落成
fake/local `CandidateEvaluationHarness`：primary I/O 前先 reserve，单次事件泵同时服务
body-free observer 与临时 assembler，真实边界观察后再重算 policy/settle；完整流才可短暂交给
显式 evaluation consumer，receipt 不保存正文或敏感原文。

聚焦 harness `15 passed`，与边界观察、流装配和旧恢复合同相邻回归 `102 passed`；activation 仍
disabled，候选未注册、不打开 `capabilities.streaming`，严格 Flash v1、产品 Runtime、Portal、
Account、Workbench、Auth、路由和 `production_media=0` 不变。当前下一精确项为
`candidate-recovery-diagnostic-review / pending-user-authorization`；公共 CI 已完成，但这不构成
候选 recovery、领域准入或生产准入。

### 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 Actions run `33536168224` 已三 job
全绿且 `head_sha` 精确匹配，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
该证据只证明隔离 fake/local harness 可公共复现；候选仍 disabled、未注册、不打开产品 streaming，严格
Flash v1、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变。
下一精确项为 `candidate-recovery-diagnostic-review / pending-user-authorization`，需要单独授权后才可
复核传输/预算/失败边界或建立新的诊断版本。

### 2026-09-02：RQ-202 候选 recovery 诊断边界复核

学习材料：[复核 walkthrough](8e-glm53-candidate-recovery-diagnostic-review-walkthrough.md) /
[ADR-0078](../adr/0078-review-glm53-candidate-recovery-diagnostic-boundaries.md) /
[复核计划](../plans/2026-09-02-glm53-candidate-recovery-diagnostic-review.md)。本门复核了回执字段
来源、单次与累计预算、unknown Usage 和旧同步诊断器复用风险，并在隔离 harness 中加固派生
一致性与单次 90 秒截止。

harness 聚焦 `18 passed`，相邻候选集合 `127 passed, 1 deselected`，compileall、diff check、
governance 通过。旧诊断测试因 Windows 隔离工作树的 CRLF fixture 与计划 canonical-LF 摘要
不一致而未作为证据；没有修改冻结资产。候选仍 disabled、未注册，不发真实 recovery。
下一精确项为
`candidate-recovery-diagnostic-version-design / pending-user-authorization`，需要再次单独授权。

### 2026-09-02：RQ-203 版本化候选 recovery 诊断协议设计

学习材料：[设计 walkthrough](8e-glm53-candidate-recovery-diagnostic-version-design-walkthrough.md) /
[ADR-0079](../adr/0079-design-versioned-glm53-candidate-recovery-diagnostic.md) /
[设计计划](../plans/2026-09-02-glm53-candidate-recovery-diagnostic-version-design.md)。本门把
“将来是否允许一次候选 recovery”与“现在是否发送第二次请求”彻底分开，冻结协议
`glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0`、候选身份与 SHA 绑定、
`reserve → open → observe/assemble → settle → receipt` 时序、单次/累计预算、Usage/费用三态、
六段单调延迟、失败第一现场和 body-free 原子回执。

本门只有设计证据，没有新增代码、结果 JSON、真实 API/Key、recovery、候选注册或产品 Runtime 接线。
候选仍 disabled、未注册，严格 Flash v1、默认模型、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变；Stage 8/8E 继续进行中，8F 未开始。下一精确项为
`candidate-recovery-diagnostic-version-implementation / pending-user-authorization`，实现仍需再次授权。

### 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现

学习材料：[实现 walkthrough](8e-glm53-candidate-recovery-diagnostic-version-implementation-walkthrough.md) /
[实现计划](../plans/2026-09-02-glm53-candidate-recovery-diagnostic-version-implementation.md)。本门把
RQ-203 的协议落成 candidate-only fake/local 接缝：primary I/O 前先 `reserve`，一条 normalized
event pump 同时服务 body-free observer 和临时 assembler，完成后才由观察事实推导回执、预算、费用、
延迟和失败。`from_dict()` 与 canonical create-only JSON 都有递归 allow-list；unknown Usage 和
未验证价格保持 `null/unknown`，disabled activation 不会发第二次 recovery 请求。

新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归 `82 passed`，
compileall、静态 no-I/O/import 和 diff check 通过。系统 Python 3.13 用户环境已安装 `pytest 9.1.1`，
项目验证仍使用仓库 `.venv` 的完整依赖。该门仍是 8-Advanced candidate evidence，不是产品 streaming
或生产准入；候选未注册，严格 Flash v1 2048/零额外调用、默认模型、Portal、Account、Workbench、
Auth、路由与 `production_media=0` 不变。下一精确项为
`candidate-recovery-diagnostic-version-public-ci / pending`，真实 recovery、G53-7、黄金切片、
生产安全/部署与 8F 仍需独立授权。

### 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环

RQ-205 的学习材料由 [实现 walkthrough](8e-glm53-candidate-recovery-diagnostic-version-implementation-walkthrough.md)、
[实现计划](../plans/2026-09-02-glm53-candidate-recovery-diagnostic-version-implementation.md) 和公共 CI 记录共同组成。
提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 Actions run `33598541029` 三 job exact-SHA 全绿，
公共 pytest `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`；
前端契约、构建、E2E、RAG、治理和打包冒烟也通过。一次 fake/local primary 协议演练完成临时 body-free 回执写入，
未读取 Key、未发送真实 API、未发起第二次 recovery。

这只是候选评估接缝的公共可复现性，不是产品 streaming 或生产准入。候选仍 disabled、未注册，严格 Flash v1、
默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。下一精确项为
`candidate-recovery-diagnostic-real-call / pending-user-authorization`，真实 recovery、G53-7、黄金切片、
生产安全/部署与 8F 仍需独立授权。

### 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察

本门沿用 [版本化诊断实现 walkthrough](8e-glm53-candidate-recovery-diagnostic-version-implementation-walkthrough.md)
和[实现计划](../plans/2026-09-02-glm53-candidate-recovery-diagnostic-version-implementation.md)，在干净隔离工作树
只执行 1 次普通智谱 `zhipu/glm-5.3-flash` primary。提交
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions `33603143606` 三 job exact-SHA 全绿；SDK retries=0，
没有第二次 recovery。

这次学习重点不是“看到 stop 就算成功”：流确实观察到 reasoning、可见正文、`finish_reason=stop` 与 EOF，
但首个可见正文在 `151453ms`、总延迟 `175875ms`；Usage 缺失、close 失败，90 秒 attempt 门在晚到事件中触发，
所以回执保持 `fail_closed / elapsed_limit`、`assembled_complete=false`、费用 unknown。`open_elapsed_ms=0` 只是
惰性流生成器的计时起点。持久回执是 body-free JSON（`4355` bytes，SHA-256
`2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`）。

该样本只能说明请求到达接口并产生内容，不能裁决 API/Key、模型一般能力、领域准入或生产成熟度；候选仍
disabled/未注册，严格 Flash v1、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变。下一精确项为
`candidate-real-call-timeout-usage-followup / pending-user-authorization`：先离线验证硬墙钟取消、流关闭与
Usage/终态尾帧处理，再决定是否另行授权真实重测。

### 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧

学习材料：[ADR-0080](../adr/0080-adopt-candidate-hard-deadline-session-and-usage-tail.md) / [实施计划](../plans/2026-09-02-glm53-candidate-stream-deadline-usage-followup.md) /
[实现 walkthrough](8e-glm53-candidate-stream-deadline-usage-followup-walkthrough.md)。本门回答一个具体问题：
当 provider 流在预算墙钟附近迟到、关闭可能阻塞且 Usage 可能落在尾帧时，如何让候选评估可取消、可审计并 fail closed，
而不把实验接缝误接成产品 Runtime。

代码地图：`app/evaluation/candidate_stream_contract.py` 定义显式 session、终态/Usage 合同；
`app/evaluation/candidate_stream_deadline.py` 提供 `CandidateStreamDeadlineSupervisor`；
`app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamSession` 负责 SDK 流资源所有权、
`stream_options={"include_usage": true}` 和幂等 close/cancel；`app/providers/zhipu.py` 只在候选显式路径暴露接缝。
控制流以 attempt 起点记录绝对 monotonic deadline，watchdog 发出协作式 cancel，事件泵抑制迟到事件，
终态必须与 Usage 同帧或紧随其后的单个 Usage-only 尾帧；重复、过早、终态后内容和空非 Usage 帧均拒绝。

验证：四文件聚焦测试（deadline 10、v2 24、real 8、adapter 25）统一为 `67 passed`，
并完成 compileall、治理与 diff check；本门不读取 Key、不调用真实 API、不发起重试。Usage/价格缺失保持 unknown/null，
不合成零值；超时主错误保持 `elapsed_limit`，close 失败仅作次级证据且回执不携带 provider body/exception。

边界与面试表述：legacy `open_stream() -> Iterable` 继续兼容，但 hard mode 必须显式 `session_opener`；
显式 opener 返回 legacy iterable 时只能在 opener 返回后校验，不能声称 opener I/O 已预验证。同步 opener 可能越过计时器，
SDK `close()` 是否非阻塞并唤醒 `next()` 尚待 provider/public CI 证明，因此 8E coverage 仍为 planned，Stage 8/8E
保持 `in_progress`，候选 `activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`。

> 历史快照（RQ-207 本地实现完成时）：当时的下一精确 checkpoint 曾为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
> RQ-208 已完成该公共 CI，当前唯一指针以最新学习段落为准。

### 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

RQ-207 的候选硬墙钟会话、取消/关闭资源合同与 Usage 尾帧离线实现，已在提交
`015b022bfce6d03452f753794ac126a377f8355b` 取得 Actions run `33613113829` 的 exact-SHA 公共 CI 闭环；
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均为 `completed/success`。公共 pytest 为
`2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为 `201 passed, 1 warning`；
本地四文件聚焦回归为 `67 passed`，没有新的真实 API、重试或第二次请求。

学习重点是公共可复现性与真实边界的区分：该证据不证明供应商 SDK `close()` 非阻塞/能唤醒 `next()`，也不构成
模型一般能力、领域采用或生产成熟度结论；同步 opener 永久阻塞限制继续保留。候选仍
`activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1
2048/零额外调用，默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变，
Stage 8/8E 继续 `in_progress`，8E coverage 仍 planned。

历史快照中的下一精确 checkpoint 曾为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
当前指针见本文开头的 RQ-212 校正。
RQ-209 已记录/完成 1 次有界真实 primary 并以 `fail_closed / elapsed_limit` 收口，但该门仍未关闭；组合关闭
状态的具体底层资源仍未知，公共 CI 尚未宣称，不能自动注册候选或进入 G53-7。

### 2026-09-02：RQ-209 候选真实流硬墙钟观察后记

这次后记对应一次真实但有界的候选观察，不改写 RQ-207/RQ-208 的历史“无真实请求”段落。按用户“继续”只
发送 1 次普通智谱 `zhipu/glm-5.3-flash` primary：首事件/打开计时 `3421ms`，reasoning 非空；在
`90015ms` 触发 attempt 硬墙钟，未见可见正文、terminal、EOF 或 Usage，组合会话 `close_state=failed`，
回执为 `fail_closed / elapsed_limit`，费用 unknown，无 recovery 或重试。

回执路径为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json`，
文件 `4342` bytes、SHA-256 `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`，由本地提交
`0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存；公共 CI 尚未宣称。最重要的学习边界是：`close_state=failed`
只是组合清理投影，不能直接归因供应商 SDK，也不能据此说 close 已经或没有唤醒挂起读取；
`observation.elapsed_ms=0` 不是零耗时，真实时序以 latency `90015ms` 为准。

候选仍为 activation gate disabled、candidate 未注册，`capabilities.streaming=False`、严格 Flash v1 2048/零额外调用和 8E coverage planned
保持不变。下一次若要拆分 provider response cancel、迭代器清理或重做真实观察，需要新的明确一次性授权；在此
之前不改变产品 Runtime、Workbench、前端或默认模型。

### 2026-09-03：RQ-210 候选会话关闭报告

新增 [RQ-210 关闭报告 walkthrough](8e-glm53-candidate-close-report-walkthrough.md)，记录一个容易被混淆的边界：
组合 `close_state` 不能说明究竟是哪一个资源关闭成功或失败，因此候选会话在内存中分别观察迭代器与外层 SDK
stream wrapper，并用 `shared_resource` 表示对象别名。材料同时区分“取消请求”“资源关闭”和“唤醒挂起读取”，
说明 body-free 约束、异常脱敏、无 hook 时的 `not_observed` 语义及并发读取限制。RQ-209 回执/schema/SHA、候选 gate、
产品 Runtime 和 `production_media=0` 均不变；实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 的 Actions
`33657368435` 已 exact-SHA 三 job 成功，但本地/公共候选证据都不是生产成熟度证明，8E coverage 仍按 planned 维护。

### 2026-09-03：RQ-211 候选 provider close/wakeup 一次观察

新增 [RQ-211 close/wakeup 观察 walkthrough](8e-glm53-candidate-close-wakeup-observation-walkthrough.md)。
这次在 c311 exact-SHA 公共绿灯快照上只发出 1 次真实请求，回执为 `not_pending`：会话打开并观察到
reasoning/content 类别，但没有形成 pending reader，所以没有执行 cancel，`reader_woke=false` 不能
解释为唤醒失败。迭代器、外层 SDK stream wrapper 与组合关闭投影均为 `closed`，回执为 `908` bytes、
SHA-256 `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`，不含敏感字段或正文。
材料特别区分“没有观察到挂起读取”和“provider close/wakeup 已被证明”；后者仍未证实。候选 gate、
产品 Runtime、Portal、Account、Workbench、Auth、路由、`production_media=0` 以及 8E coverage planned
保持不变，下一步等待是否设计新版 pending-read 观察协议的用户裁决。

补充验证：提交 `1c669e0` 为公共能力目录加入 RQ-211 回执的显式 schema 分派，Actions run `33666132282`
三 job exact-SHA 全绿（公共 pytest `2268 passed, 145 skipped, 1 warning, 127 subtests passed`，
PostgreSQL `201 passed, 1 warning`）。这是回执合同的公共可复现性验证，没有新增真实 API 调用；真实观察仍只绑定 c311。

### 2026-09-03：RQ-212 候选 close/wakeup 离线 pending-read 回放

新增 [RQ-212 离线回放 walkthrough](8e-glm53-candidate-close-wakeup-replay-walkthrough.md)、
[ADR-0082](../adr/0082-adopt-offline-candidate-close-wakeup-replay.md) 和
[离线回放计划](../plans/2026-09-03-glm53-candidate-close-wakeup-replay.md)。这批用固定 Event 闸门
重放五种生命周期，复用 RQ-211 观察器，但把回执明确隔离为 `offline_fake`：供应商调用数为 0，
fake session 打开数单独为 1，结果不进入 provider capability 目录。它证明的是本地分类、单次打开、
脱敏和不可变写入可以重复复核，不是 GLM-5.3 的 close/wakeup 或生产能力证据；候选仍未注册，8E
coverage 继续 planned。

### RQ-212 公共闭环事实（2026-09-03）

实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec` 的 Actions `33707313651` 三 job exact-SHA 全绿，
公共 pytest `2284 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
packaging-smoke 通过。最终 v2 回执为
`data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`（`2220` bytes，
SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`）；v1 仅为旧 HEAD 的提交前演练。
学习结论仍限于 `offline_fake` 本地分类/脱敏/不可变写入，真实 provider close/wakeup 未证实；下一步为
`candidate-close-wakeup-real-observation / pending-user-authorization`，8E coverage 继续 `planned`。

### 2026-09-03：RQ-213 候选 close/wakeup 第二次有界真实观察

新增 [RQ-213 close/wakeup 真实观察 walkthrough](8e-glm53-candidate-close-wakeup-real-observation-walkthrough.md)。
在 RQ-212 公共闭环后的 exact-SHA 公共绿灯提交上只发出 1 次普通智谱请求，回执为 `not_pending`：会话
在 172ms 内打开并记录 reasoning/content 类别，但没有形成 pending reader，所以 cancel 未尝试。
回执为 909 bytes、SHA-256=`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`，
不含敏感字段或正文；iterator、SDK stream wrapper 和 composite 投影均为 `closed`。

材料强调 `not_pending` 不是 wakeup 成功或失败，`closed` 也不等于底层 HTTP response 已取消；候选 gate、
产品 Runtime、默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变，8E
coverage 继续 `planned`。下一步先裁决是否设计能稳定制造 pending-read 的新版协议，不自动重复真实请求。

### 2026-09-03：RQ-214 候选 SDK/HTTP transport gate 离线预检

新增 [RQ-214 walkthrough](8e-glm53-candidate-transport-gate-precheck-walkthrough.md)、
[ADR-0084](../adr/0084-adopt-candidate-transport-gate-precheck.md) 和
[离线预检计划](../plans/2026-09-03-glm53-candidate-transport-gate-precheck.md)。这批在真实
OpenAI SDK、显式 Zhipu 候选适配器和既有观察器对象链上接入本机 `MockTransport`，按完整 SSE
帧边界固定 `after_first_event` 与 `before_first_event` 两个挂起读取阶段；不读取或保存响应正文。

两阶段都观察到读取器被 response close 唤醒，但适配器并发 iterator 关闭可能出现
`iterator=failed` / `composite=failed`，所以把“读取器醒来”和“关闭干净”分开记录为
`client_wakeup_close_race`，没有静默修改适配器。回执保持 `offline_sdk_transport_fixture`、供应商
调用数 0、无网络，候选仍未注册，8E coverage 继续 `planned`；这不是智谱服务端原生 close/wakeup
或生产 streaming 证据。下一检查点是经公共闭环后，在一次性授权下最多发出 1 次官方 TLS transport
包装的真实观测。

RQ-214 离线回执已绑定实现提交 `4c220c5751288ad77c589d2e0e581690085803c0`，路径为
`data/evaluation/results/offline/zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json`，
`1693` bytes、SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`；
canonical round-trip 通过，三份身份 SHA 相同。该提交的同 SHA 公共 CI run `33712055286` 三 job 全绿：
pytest `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
packaging-smoke 通过。

### 2026-09-03：RQ-215 候选 transport-gated 一次真实观察

新增 [RQ-215 真实观察 walkthrough](8e-glm53-candidate-transport-gate-real-observation-walkthrough.md)、
[ADR-0085](../adr/0085-record-candidate-transport-gated-real-observation.md) 和
[观察计划](../plans/2026-09-03-glm53-candidate-transport-gate-real-observation.md)。在 RQ-214
离线闸门和同 SHA 公共 CI 后，本批只发出 1 次真实 `zhipu/glm-5.3-flash` 请求；官方 TLS
transport 外层 gate 进入，pending reader 在 `31ms` 内被 response close 唤醒。

取消抛出安全码 `zhipu_stream_close`，iterator/composite close 投影为 `failed`、SDK stream
为 `closed`，所以结论是 `client_wakeup_close_race`。这只说明真实流启动后本机受控停顿下的
客户端行为，不是 provider-native close/wakeup 或生产 streaming 证据。回执保持 body-free，
路径为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`，
大小 `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`。
候选仍 disabled/未注册，8E coverage 继续 `planned`；当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

### 2026-09-03：RQ-216 候选 reader-owned close 顺序修复

新增 [RQ-216 walkthrough](8e-glm53-candidate-reader-owned-close-order-walkthrough.md)、
[ADR-0086](../adr/0086-adopt-candidate-reader-owned-close-order.md) 和
[修复计划](../plans/2026-09-03-glm53-candidate-reader-owned-close-order.md)。本批解释并修复
`client_wakeup_close_race`：取消线程不再跨线程关闭正在执行 `next()` 的 Python iterator，先关闭
外层 SDK response，让 reader 自己在 `finally` 中完成 iterator close；没有活跃 reader 时仍逐资源
最多关闭一次。

阻塞读取回归与 RQ-214 两阶段离线 transport-gate 聚焦测试共 `61 passed`，并通过 compileall、
差异检查和治理校验；本批真实 API 调用为 0。该修复仍是候选 evaluation-only 客户端合同，不代表
provider-native 能力或生产 streaming；候选未注册、8E coverage 继续 `planned`。当前下一检查点为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`。

公共闭环补充：提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions `33726209532` 三 job
exact-SHA 全绿；pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL
与 packaging-smoke 通过。学习边界仍保持不变，当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`，
是否重新执行真实观察需另行决定。

### 2026-09-03：RQ-217 关闭顺序修复后的 transport-gated 一次真实观察

新增 [RQ-217 walkthrough](8e-glm53-candidate-transport-gate-real-observation-rq217-walkthrough.md)、
[ADR-0087](../adr/0087-record-candidate-transport-gated-real-observation-after-close-order-fix.md)
和[观察计划](../plans/2026-09-03-glm53-candidate-transport-gate-real-observation-rq217.md)。
在 RQ-216 的实现/观察器/输入计划 SHA
`3e028b1217f1274152ba161993287f29188a1b73` 及公共 Actions `33727163550` 绿灯后，按用户
授权只发送 1 次真实 `zhipu/glm-5.3-flash` 请求。首帧前 gate 形成 pending reader，
`cancel_status=returned`、`reader_woke=true`，iterator/SDK/composite close report 全为
`closed`，结论为 `client_wakeup_clean`。

回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`
（`1284` bytes，SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`），
只含脱敏状态且 canonical round-trip 通过；`gate_released=false` 是受控停顿协议的预期
条件。该证据只说明真实流启动后本机客户端的唤醒与 reader-owned 收尾，不证明 provider-native
close/wakeup、模型一般能力或生产 streaming。候选仍 disabled/未注册，8E coverage 继续
planned，默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变；当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`。

### 2026-09-03：RQ-218/RQ-219 Flash 协议与候选 8192 响应完成度

新增 [RQ-218/RQ-219 walkthrough](8e-glm53-protocol-and-candidate-timeout-walkthrough.md)、
[ADR-0088](../adr/0088-record-glm53-flash-protocol-and-candidate-timeout.md) 和
[计划/结果记录](../plans/2026-09-03-glm53-flash-protocol-and-candidate-timeout.md)。
RQ-218 在最新实现上以精确 3 次调用完成 G53-3，A1/A2 均通过；RQ-219 只发送 1 次候选
8192 primary，在 90 秒硬墙钟以 `fail_closed / elapsed_limit` 结束，未 recovery、retry
或第二请求。学习重点是把“协议可达”和“长响应终态完成”拆开归因；候选、默认模型、产品
Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。RQ-219 的
证据提交 Actions `33735717434` 三 job 已 `completed/success`；下一步是零网络 fake/fixture 拆分。

### 2026-09-03：RQ-220 响应档位—终态—恢复离线拆分

新增 [RQ-220 walkthrough](8e-glm53-response-profile-terminal-recovery-split-walkthrough.md)、
[ADR-0089](../adr/0089-adopt-offline-response-profile-terminal-recovery-split.md) 和
[实施计划](../plans/2026-09-03-glm53-response-profile-terminal-recovery-split.md)。
9 个固定场景全部通过，相关聚焦回归为 `133 passed`，明确区分正常终态、候选 `length` 形状、
缺/非法 Usage 与超时；候选恢复动作仍被 activation gate 阻断，provider calls=0。
实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` / Actions `33738050233` 与回执提交
`ebb09a525b3340f31ba71821b894b4a142dfb4e7` / Actions `33738673832` 均三 job
`completed/success`，回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
该公共闭环只证明评测实现可复现，不是产品成熟度或候选准入；当前 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

### 2026-09-03：RQ-221 GLM-5.3 Flash 低思考候选探针

新增 [RQ-221 walkthrough](8e-glm53-low-profile-candidate-probe-walkthrough.md)、
[ADR-0090](../adr/0090-adopt-explicit-glm53-low-profile-candidate-probe.md) 和
[探针计划](../plans/2026-09-03-glm53-low-profile-candidate-probe.md)。本批把低思考档
作为显式 candidate-only profile（`thinking=enabled`、`reasoning_effort=low`、
`clear_thinking=false`、4096 输出），只在候选构造器中可见，不进入产品 Runtime resolver。

实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions `33746833148` 三 job
exact-SHA 全绿；候选聚焦 `25 passed`，本次相关候选/流/智谱回归 `357 passed`。按授权
只发送 1 次真实无工具请求，得到 `observed / finish=stop / usage=valid`，输入/输出
`1973/498`，延迟约 `20735ms`。body-free 回执提交
`ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，SHA-256=
`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。

这只是冻结上下文的一次响应完成观察，不是领域质量、G53-7、黄金切片、生产准入或 8F
证据；候选仍 disabled/未注册，严格 Flash v1、默认模型、Portal、Account、Workbench、
Auth、路由和 `production_media=0` 不变。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`；
下一步先设计/裁决独立低档候选 held-out 领域门，不自动追加真实请求。

### 2026-09-03：RQ-222 低思考候选独立领域门设计

新增 [RQ-222 walkthrough](8e-glm53-low-profile-domain-gate-design-walkthrough.md)、
[ADR-0091](../adr/0091-design-glm53-low-profile-heldout-domain-gate.md) 和
[设计计划](../plans/2026-09-03-glm53-low-profile-domain-gate-design.md)。本批把 RQ-221
的一次无工具响应完成与领域任务准入明确拆开：旧 G53-4/G53-7 考卷不重跑，低思考档不注册到
产品 Runtime，而是采用只有评测入口能持有私有令牌的候选作用域，以及共享请求策略接缝。

下一步先做零网络离线 TDD，固定低思考/4096 输出、90/120 秒超时、每案 4 次/全域 12 次、
24,000/72,000 token 墙、首错停止、无恢复/重试/修订和关闭 deterministic fallback；之后才在
同一实现身份上取得新的 G53-3-L，再创建全新的 oracle-blind held-out 资产。设计阶段
provider calls=0，候选仍未注册，8E coverage 继续 `planned`。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。

### 2026-09-04：RQ-223 低思考候选领域门离线实现

本批把 RQ-222 的设计落成可复用但不越权的控制面：候选使用私有签发的
`CandidateEvaluationRequestPolicy`，共享 Agent/LLM/Domain 链只通过显式 `request_policy`
接收它；最后一层预算包装器执行 reserve-before-I/O、每案 4 次/全域 12 次和
24,000/72,000 token 墙。重试和 deterministic fallback 均关闭，产品 Runtime 注册表和严格
Flash v1 不变。Fake Provider 新增测试 5/5、相邻回归 118 passed，provider calls=0；实现细节
见 [RQ-223 walkthrough](8e-glm53-low-profile-domain-gate-offline-implementation-walkthrough.md)
与 [实施计划](../plans/2026-09-04-glm53-low-profile-domain-gate-offline-implementation.md)。
该段记录实现阶段的待验状态；随后已完成同 SHA 公共 CI，进入 G53-3-L 与新鲜 held-out 资产前置。

公共 CI 已于实现提交 `d823cc40c3fcafb7167edccded87e185be4cae8a` 的 Actions
`33781369322` 完成 exact-SHA 三 job 闭环；公共 pytest 为
`2326 passed, 145 skipped, 2 warnings, 127 subtests passed`，本批 provider calls=0。
这只关闭离线控制面的可复现性闸门，不改变候选 disabled/未注册状态。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / pending-user-authorization`，
再后面才可冻结新鲜领域资产。

### 2026-09-04：RQ-225 低思考 G53-3-L 协议与新鲜资产离线实现

本批把下一步拆成两个可复核的离线控制面：协议侧通过显式 `request_policy` 复用既有
结构化响应与 `knowledge.search` 往返，固定 `low + 4096`、90 秒工具窗、最多 3 次调用，
并以 body-free/create-only 报告收口；资产侧冻结全新三案例 Dataset、V1.1 Input Plan、
Prompt/Context Snapshot 和合成 fixture，准入时交叉核对 SHA、case 顺序、marker 隔离与
上下文 commitment。聚焦协议/资产及相邻回归 `20 passed`，compileall、diff check、治理
通过，provider calls=0；没有读取 Key 或发真实请求。

学习重点是：候选策略只能经私有签发的 evaluation-only 入口进入共享链，产品 Runtime
注册表保持封闭；资产“准入”不等于资产“执行”；真实协议门仍需同 SHA 公共 CI 和明确授权。
详见 [RQ-225 walkthrough](8e-glm53-low-profile-protocol-and-assets-offline-implementation-walkthrough.md)
与[实施计划](../plans/2026-09-04-glm53-low-profile-protocol-and-assets-offline-implementation.md)。
当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`。

随后修复了新模块的顶层导入环；提交 `411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的
Actions `33787508488` 三 job exact-SHA 全绿，公共 pytest 为
`2332 passed, 145 skipped, 2 warnings, 127 subtests passed`。这只关闭离线控制面的公共
可复现性，provider calls 仍为 0；真实 G53-3-L 仍需明确授权。

### 2026-09-04：RQ-226 低思考 G53-3-L 真实协议门

在 RQ-225 公共 exact-SHA CI 闭环后，用户“继续”授权一次最多 3 次的真实候选协议。实现/协议
SHA 为 `ac63bf4ee70d61fca78813b200cf7775e5ca61d8`；A1 结构化合同和 A2 工具往返均通过，
精确 `3/3` calls，输入/输出/总 token `1007/84/1091`，累计延迟 `12062ms`。
脱敏 body-free/create-only 回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json`
（`2511` bytes，SHA-256=`a3077ce6d4729e676d0c0ce0d9a6429153075ca59e0850529dee4e29c0376e35`）。

这只证明固定协议可达性与适配器归一化；候选仍 disabled/未注册，默认 Runtime、Workbench、
Portal、Account、Auth、路由及 `production_media=0` 不变。held-out 领域质量、成本/延迟稳定性、
streaming 生产能力、黄金切片、安全/部署/合规与 8F 仍未验证；下一步如继续需另行授权领域门。
