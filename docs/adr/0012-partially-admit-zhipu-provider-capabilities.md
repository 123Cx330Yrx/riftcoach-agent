# ADR-0012：分层准入 Zhipu Provider 能力

## 状态

已接受

## 日期

2026-08-13

## 背景

5D-6b 把真实 Provider 准入拆成两层，避免用一个微探针或一个领域样例概括全部能力：

1. Adapter 协议层：结构化输出和一次工具往返能否通过生产 `ZhipuProvider`；
2. 领域层：同一 Provider 能否进入 `recent-form-review` 的真实 Skill、RAG、
   AgentLoop、ReviewHarness 和 typed output 控制流。

在显式关闭 Thinking 后，P1-P5 微探针 5/5 通过。随后，真实 Adapter Protocol
Slice 精确使用 3/3 calls：结构化响应使用 1 call，Agent 工具往返使用 2 calls，
两个案例均通过并得到 `admitted=true`。

Recent-form Domain Slice 在公开 CI 成功的代码
`f5e97ead20c5aa7d4798f308bd60e820842061bc` 上只执行一次。该运行使用 1 个领域
call，累计为 4/7，但 Provider 请求之后没有统一 `ChatResponse` 到达 Agent 结果：

- `response_count=0`、`agent_status=null`；
- 没有 ToolCall、工具执行或知识来源；
- 没有进入结构化 Evaluation，因此不存在质量分数；
- Harness 到达 `degraded`，只返回确定性报告；
- 公开错误码为 `knowledge_round_trip_incomplete`；
- 没有可靠单价快照，因此成本估算保持 `null`。

现有脱敏证据不能进一步区分 Adapter 响应规范化拒绝和其他发生在统一响应形成前的
Provider 错误。`AgentLoop` 会保留安全 `error_code`，但草稿准备失败时
`_BoundAgentDraftPreparationStep` 无法暴露尚未成功返回的 `AgentRunResult`，领域
runner 因此只能记录上层失败分类。这是 5D-7 的可观测性 Bad Case，不能通过猜测模型
原文或重跑来补证据。

## 决策

5D-6b 以“协议能力准入、领域能力不准入”的部分采用结论收尾：

- 准入 Zhipu Adapter 的最小结构化输出与工具调用协议能力；
- 不准入 GLM-5.2 的 `recent-form-review` 真实领域执行能力；
- 保留确定性 fallback，因为它在真实失败中阻止了未经评测的 Agent 草稿发布；
- 不重跑该样例，不修改 Prompt 追求一次通过，也不删除或改写失败证据；
- 不立即接入第二 Provider；5D-7 先基于同一任务合同建立多案例 Prompt/Context、
  工具选择、事实/引用、注入、质量、延迟、成本与失败归因评测；
- 第二 Provider 只有在 5D-7 明确同任务评测设计和候选门槛后，才通过新的采用决策
  引入。

`5D-6b completed` 表示准入门已经作出可审计的接受/拒绝决定，不表示领域运行成功，
也不表示 GLM 是最终生产模型。

## 备选方案

### 重跑或临场调整 Prompt

可能碰到一次成功结果，但会覆盖真实 Bad Case、扩大调用预算并把准入实验变成追分。
拒绝。

### 因协议切片通过而整体准入 GLM

协议夹具没有经过真实领域 Context、RAG 与 Harness。真实领域证据已经反驳该推断，
拒绝。

### 因领域样例失败而整体移除 Zhipu Adapter

低层 P1-P5 和生产协议切片已经证明 Adapter 的最小合同可用。领域失败尚不能归因到
模型、Prompt、上下文或规范化中的单一因素，整体移除证据不足，拒绝。

### 立即同时接入 DeepSeek 与 Qwen

没有冻结同任务数据集和比较合同会把厂商差异、Prompt 差异与 Adapter 缺陷混在一起，
也会扩大当前检查点。暂缓。

## 影响

### 正面

- 真实失败被保存为后续设计输入，而不是被一次绿色样例掩盖；
- Provider 协议、领域执行和报告质量保持三个独立结论；
- 确定性 fallback 的价值获得真实外部故障证据；
- 5D-7 有了具体的 Prompt/Context 与错误归因 Bad Case。

### 负面

- 当前没有可准入的真实近期复盘 LLM 路径；
- 领域结果无法给出模型质量分、可靠成本或精确底层错误分类；
- 在 5D-7 完成并作出后续 Provider 决策前，产品只能安全降级到确定性报告。

### 中性

- 不改变 0-8 主路线、两个 Skill、RAG 或 Harness 架构；
- 不引入 LangGraph、Pi/Claude Agent SDK、Multi-Agent 或第二 Provider；
- Zhipu 仍是首个实现的真实 Adapter，不等于最终厂商锁定。

## 证据

- `data/evaluation/results/provider_capabilities/zhipu_glm52_p1_p5_final.json`
- `data/evaluation/results/provider_capabilities/zhipu_adapter_slice.json`
- `data/evaluation/results/provider_capabilities/zhipu_recent_form_slice.json`
- `docs/plans/2026-08-13-zhipu-recent-form-domain-slice-design.md`
- `docs/plans/2026-08-13-zhipu-recent-form-domain-slice-review.md`
- GitHub Actions run `31657986279`，精确 SHA
  `f5e97ead20c5aa7d4798f308bd60e820842061bc`
