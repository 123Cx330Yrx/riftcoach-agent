# ADR-0053：拒绝角色隔离 Multi-Agent，优先普通受限并行 Evidence

- 状态：Accepted（2026-08-22，RQ-082）
- 裁决：`reject-role-isolated-multi-agent / prefer-bounded-parallel-evidence-design`
- 范围：8B `recent-form-review-evidence-isolation-v1` evaluation experiment；不直接修改产品 Runtime。

## 问题

ADR-0052 允许三路进入 8B：串行 baseline、普通受限并行 comparator、角色隔离 Multi-Agent candidate。
8B 必须在同一 fixture、Coach、Harness、Context ceiling、零重试和 Scripted Usage 模型下回答：Multi-Agent
是否在普通并行之外带来足以覆盖额外调用、Token 和维护面的收益。

## 冻结证据

- 实现/public-CI SHA：`180bc8b452603572d010b6e25b14ed71f6470ce7`；
- implementation Actions：`32572085065`，三个 job completed/success；
- gate digest：`88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；
- case-set SHA：`d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e`；
- development experiment：`73a0cc181f974ace2b1350512ab8e5937f63a24ae5715495e37438b0e345e0d1`；
- holdout experiment：`0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494`；
- 不可覆盖结果：`data/evaluation/results/stage8/role_isolated_multi_agent_holdout_v1.json`；
- 结果 SHA-256：`94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8`；
- holdout executions：1；external I/O、retry 和八个 hard-gate breaches：0。

## 结果

| Strategy | Match | Safe degraded | Isolation | Latency units | 改善 | Token ratio | Extra calls/例 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Serial | 1.0 | 1.0 | 1.0 | 765 | 0% | 1.00 | 0 |
| Bounded parallel | 1.0 | 1.0 | 1.0 | 590 | 22.88% | 1.05 | 0 |
| Role-isolated Multi-Agent | 1.0 | 1.0 | 1.0 | 620 | 18.95% | 1.45 | 2 |

Multi-Agent 的质量、安全和成本上限没有失败，但 modeled latency 未达到 20%，且失败隔离率与普通并行完全
相同。开发集曾达到 27.05% 并获准进入 holdout；独立 holdout 的较慢 Knowledge branch 暴露额外角色开销，
不能用 development 结果覆盖。

## 决策

1. 拒绝把 `role-isolated-multi-agent-v1` 接入产品 Runtime；
2. 保留 8B strict gate、三路 runner、角色/Artifact/result validator 和一次性 lifecycle 作为评测资产；
3. 把 `bounded-parallel-evidence-v1` 作为 8D Riot+OP.GG Evidence fusion 的优先设计输入，但 8B 不提前修改
   产品 Runtime；8D 仍须按自身取消、deadline、预算和 deterministic merge TDD 实施；
4. `ReviewHarness` 继续是唯一发布权，不创建 Review Agent；
5. DAG/第三方 Runtime 与 Agentic Retrieval 继续 deferred。未来重新评估 Multi-Agent 必须有新的、普通并行
   无法解决的 Bad Case、新 case-set/结果路径和独立 ADR，不能重跑本次 holdout。

## 为什么不是 partial-adopt Multi-Agent

独立 Context 和 exact role permissions 在结构上成立，但本次所有安全压力案例都被普通并行的 strict Adapter、
typed Artifact 和原子 tool preflight 同样处理。只证明“可以隔离”不足以证明“值得增加 Agent”。把 evaluation
assets 留下不是产品 partial adoption，因此产品裁决保持明确 reject。

## 后果

正面：产品避免额外 40% Scripted Token、每例 2 次额外调用和角色调试面；8D 仍可获得普通并行的 22.88%
modeled critical-path 收益。

负面：当前不会获得多 Agent 独立演化、独立模型或跨进程角色恢复能力；这些能力也没有相应真实 Bad Case。

中性：本结果只属于冻结 Scripted/fixture 架构实验，不是生产 p95、真实 Token/费用或在线 OP.GG 性能证据。

## 不在本裁决

本 ADR 不实现 8C lease/recovery/cancel/checkpoint，不实现 8D fusion，不实现 8E Web/Auth/SSE/部署，也不改变
Provider、MCP 或产品默认 Runtime。
