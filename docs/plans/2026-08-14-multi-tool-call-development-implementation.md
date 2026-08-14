# 多 ToolCall 批次顺序消费实施计划

## 目标

在零外部调用下复现真实 `unsupported_parallel_tool_calls` Bad Case，扩展 DeepSeek
Adapter 的多 ToolCall 传输兼容性，并用 AgentLoop 与真实本地 RAG/Harness 证明整批预检
和顺序执行。当前 held-out 1.1.0 永不重跑。

## Task 1：Provider Adapter TDD

- 把现有“多个响应 ToolCall 必须拒绝”测试改为先红后绿的严格多调用解码测试；
- 覆盖顺序、别名、唯一 ID、严格 JSON object 和历史 assistant 批次编码；
- 保留重复 ID、未知别名、非法参数、finish reason 不一致等 fail-closed 测试；
- 不打开 `parallel_tool_calls` capability，不发未在官方合同中的请求参数。

## Task 2：AgentLoop 整批原子预检 TDD

- 两个允许调用按响应顺序执行并进入下一轮；
- 总数超过剩余 `max_tool_calls` 时工具执行数为 0；
- 批次含越权或重复调用时工具执行数为 0；
- 每个 Tool Observation 保持正确 `tool_call_id`，累计 Usage/迭代/deadline 语义不变。

## Task 3：Development 纵向复现

- 使用 Fake DeepSeek SDK 产生两个不同知识检索调用；
- 真实经过 DeepSeek Adapter、AgentLoop、ToolRuntime、本地 hybrid RAG、Secure
  Evaluation 1.1 与 ReviewHarness；
- 证明 Evidence 来源可追踪、最终终态安全，并证明没有真实 Provider I/O；
- 不使用已消费 held-out 的案例 ID、注入 marker 或结果作为绿灯答案。

## Task 4：验证与状态同步

- 运行 Provider/AgentLoop/production Executor 聚焦测试和完整 pytest；
- 运行两套 RAG、compileall、Harness dry-run、SDK/secret/run-data、governance 与 diff
  check；
- 更新 canonical state、能力矩阵、决策和活动计划；
- 提交、推送并验证 exact-SHA GitHub Actions。

## 明确不做

- 不读取 DeepSeek Key、不调用真实 Provider；
- 不重跑 Dataset 1.1.0，不修改其不可变失败结论；
- 不实现线程/async 并发、LangGraph、Pi/Claude SDK 或 5E Trace；
- 不把离线 development 通过写成 DeepSeek 领域准入。
