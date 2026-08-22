# ADR-0052：允许角色隔离 Multi-Agent 进入有界 8B 实验

- 状态：Accepted for `8a-advanced-adoption-gate`（2026-08-22，RQ-081）
- 裁决：`candidate-with-bounded-parallel-comparator`
- 范围：只决定哪些高级候选有资格进入 8B；不表示 Multi-Agent、并行或 DAG 已实现或采用。

## 问题

Stage 8 需要至少完成一个高级能力采用实验，但“项目需要 Multi-Agent”不能作为实验前提。
8A 必须先从当前 RiftCoach 工作流中找到可复核的缺口或收益假设，并确保实验能够把角色隔离的
收益与普通并行的收益区分开。

当前源码给出三条事实：

1. `AgentLoop` 会先对一批 ToolCall 做完整白名单/预算/重复预检，再按返回顺序调用
   `ToolRuntime`。ADR-0022 也明确没有启用真正并行；
2. OP.GG `MetaEvidence` 经严格 Adapter 后作为 optional、data-only、user-role Context 进入同一个
   Coach Context。当前没有上下文泄漏事故，但可以构造外部 Meta schema drift、注入文本和分支失败压力案例；
3. 任务硬崩溃后仍缺少自动 lease/recovery。这是可靠 Runtime Core 的真实缺口，应进入 8C，不能
   被包装成 Multi-Agent 的采用理由。

## 候选比较

| 方案 | 能回答什么 | 主要代价 | 8A 裁决 |
|---|---|---|---|
| 现有单 Runtime 串行 | 当前质量、安全、调用与发布基线 | 独立证据源等待时间相加 | 8B baseline |
| 单 Runtime 受限并行 evidence ports | 并行本身能否降低关键路径 | 需要分支取消、合并和预算统计 | 8B comparator |
| Knowledge/Meta 角色隔离 Multi-Agent | 独立 Context/工具权限是否增加失败隔离，及是否有超出普通并行的收益 | 额外 Provider 调用、Context、合并和维护面 | 8B primary candidate |
| 通用 DAG/第三方 Runtime | 图、恢复和复杂依赖是否值得新框架 | 变量过多，且 8C 尚未建立 durable core | deferred |
| Agentic Retrieval | 多轮查询能否改善知识召回 | 当前 RAG development/holdout 没有相应 Bad Case | deferred |

## 决策

8B 固定比较三条路径：

```text
single-runtime-serial-v1
    ├─ bounded-parallel-evidence-v1
    └─ role-isolated-multi-agent-v1
```

Multi-Agent 候选只允许三个执行角色：

- `knowledge_agent`：只读 `knowledge.search`，只看到确定性事实与知识查询；
- `meta_agent`：只读 `opgg.lane_meta` fixture，不能看到长期 Memory、用户自由文本或知识正文；
- `coach_agent`：只消费两个 typed/digest-bound evidence Artifact，不直接调用工具。

`ReviewHarness` 继续是唯一评测、修订和发布权，不被改名为 Review Agent，也不能被任何候选绕过。

## 8B 硬门与收益门

下列任一项非零即立即 reject：未授权工具调用、跨角色 Context 泄漏、无 provenance evidence、
unsafe publication、终态身份不一致、真实外部 I/O、结果覆盖或评测身份漂移。

候选还必须满足：Harness 决策匹配率 `1.0`、安全降级率 `1.0`、总 Token 不高于串行基线的
`1.5x`、Provider 调用最多比基线多 2 次，并至少证明以下一项：

- 冻结延迟模型下关键路径改善不少于 `20%`；或
- 在一个证据分支失败/污染时，另一个合法 Artifact 得以保留且最终安全降级，而串行基线无法做到。

这些数字是 8B 的工程预算和停止线，不是当前性能结果，更不是生产 SLA。

## 评测身份

- gate：`stage8-advanced-adoption-gate-v1`；
- slice：`recent-form-review-evidence-isolation-v1`；
- baseline：`single-runtime-serial-v1`；
- primary candidate：`role-isolated-multi-agent-v1`；
- comparator：`bounded-parallel-evidence-v1`；
- development 与 `calibration_excluded=true` holdout 分开；
- 8B 使用 Fake/Scripted Provider、OP.GG fixture、零重试和零真实外部调用；holdout 只执行一次，结果不可覆盖。

## 后果

正面：8B 能区分“并行更快”和“多 Agent 隔离更有价值”，不会把所有收益归给 Multi-Agent。

负面：即便进入 8B，Multi-Agent 仍可能因额外调用、合并复杂度或无增量收益被 reject。

中性：DAG、LangGraph、Saber/Sea 整体 Runtime、Agentic Retrieval 和真实 Provider 均未被永久拒绝，
只是当前没有足够独立信息增益。重新开启必须有新 Bad Case 与独立 ADR。

## 不在本检查点

8A 不实现并行调度、Agent runner、DAG、lease/recovery、Riot+OP.GG fusion、SSE、正式 Auth、前端或
部署；不安装依赖，不调用 Riot/OP.GG/Provider，不读取 Key。
