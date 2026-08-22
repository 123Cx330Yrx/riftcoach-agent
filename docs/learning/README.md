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
| 8C：Reliable Runtime Core | 本地实现完成/待公共闭环 | [walkthrough](8c-reliable-runtime-core-walkthrough.md) / [ADR-0054](../adr/0054-adopt-postgresql-leased-fenced-task-control-plane.md) / [专用设计](../plans/2026-08-22-8c-reliable-runtime-core-design.md) | 0010、durable event/replay、lease/fencing、持久 cancel、checkpoint/receipt recovery、Worker/API/package 纵向与两轮 PostgreSQL CI 修复已本地完成；最新完整回归 `1672 passed, 134 skipped, 1 warning, 127 subtests passed`，真库/Linux 与 coverage complete 仍等待 repair implementation exact-SHA 三 job |

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
- 不代表当前有正式公网 Auth、RSO 账号验证、HTTPS、SSE、前端或生产级运维；
- 不代表 RAG 开发集满分等于未知问题上的泛化满分；
- 不代表 GLM、DeepSeek 或其他 Provider 已通过全部领域质量准入；
- 6B-9 与 Session/Memory V1 已完成公共 PostgreSQL/package 闭环；这仍不表示正式 Auth/RSO、备份副本擦除、
  公网部署或 Stage 8 已实现。Stage 7 入口与 7-1…7-5 已公共闭环；实现、clean-SHA 双向真实门和
  evidence exact-SHA 均有独立证据。OP.GG 仍只证明 lane-meta partial provenance，不证明全工具、精确
  patch/freshness 或 Riot+OP.GG 数据融合；Stage 8 entry design、8A 与 8B 已公共闭环，8B 唯一 holdout 形成
  reject Multi-Agent 结论。RQ-083 授权的 8C 已完成本地产品实现与八维材料，但在 implementation exact-SHA
  公共 PostgreSQL/Linux 三 job 前仍保持 in progress/planned；8D–8F、前端和 EvidenceBundle 仍不存在。

这些边界既是工程事实，也是项目在面试中保持可信度的重要部分。
