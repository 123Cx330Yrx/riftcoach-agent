# RQ-223：GLM-5.3 Flash 低思考候选领域门离线实现

## 目标

在不把候选档案注册为产品 Runtime 的前提下，把 RQ-222 设计中的最小请求策略接缝落到
共享执行链，并用零网络假提供商证明边界。这个检查点只关闭离线控制面，不创建新考卷，
不读取 Key，不发送真实请求。

## 实现内容

1. `CandidateEvaluationRequestPolicy` 是独立于 `ModelRuntimeProfile` 的评测能力对象。它由
   私有作用域工厂签发并登记精确对象身份，固定 `low + 4096` 对应的 90 秒 Agent/LLM 工具窗、
   120 秒传输窗、采样参数、零重试和关闭 deterministic fallback；普通产品解析器仍只接受
   已登记的产品档案。
2. Agent 编译器、`llm.chat` 工具、`SkillAgentDraftPreparer` 和
   `ProductionDomainCaseExecutor` 接收显式 `request_policy` 参数。它与 `runtime_profile` 互斥，
   请求方不能用普通参数升高输出、采样或超时。
3. `CandidateEvaluationBudgetedProvider` 在最后一次 Provider 边界重新施加策略，并执行
   每案 4 次、全域 12 次、24,000/72,000 token 墙；先记账再 I/O，异常或越界即停止，
   不做重试、恢复或正文回退。
4. `SkillReviewExecutor` 增加可选的 deterministic fallback 覆盖，候选执行器明确传入
   `False`；没有传入时既有产品行为保持不变。

## 控制流

```text
候选 profile plan
       │ 私有 factory 签发
       ▼
evaluation request policy
       │
AgentRunCompiler ──► AgentLoop ──► llm.chat ──► budgeted Provider ──► Fake Provider
       │                                                │
       └──────── metadata / fixed budgets ──────────────┘
```

候选策略只沿显式评测入口流动；产品 `RuntimeExecutionFactory`、Worker、默认模型解析和
正常 `runtime_profile` 校验没有改动。

## 验收

- 新增 `tests/test_glm53_low_profile_request_policy.py`：验证私有作用域、克隆拒绝、编译器
  和 LLM 工具的预算覆盖、一次尝试/无回退，以及预算包装器的 reserve-before-I/O、调用墙和
  token 墙。
- 离线聚焦测试：5 passed；候选/Runtime/Agent/Provider/工具/Harness 相邻回归：118 passed。
- `compileall`、`git diff --check`、治理检查通过；下一步是在同一提交 SHA 上取得公共三 job
  CI，之后才设计新的 G53-3-L 与 held-out 资产。

## 边界

本检查点不注册候选、不改变严格产品 Flash v1 的 2048 上限、不改 Portal、Account、
Workbench、Auth、路由或 `production_media`，也不宣称模型领域质量、成本稳定性、黄金切片、
安全/部署合规或 8F 完成。公共 CI 之前不能把本地结果当作可复现证据。
