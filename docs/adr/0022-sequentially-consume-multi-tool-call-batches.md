# ADR-0022：接受多 ToolCall 响应批次并由 AgentLoop 顺序执行

## 状态

已接受；只授权离线 development TDD，不授权重跑 held-out 或真实 Provider 调用

## 日期

2026-08-14

## 背景

DeepSeek V4 Pro 的真实领域 held-out 首例返回多个 ToolCall，当前 Adapter 以
`unsupported_parallel_tool_calls` fail closed。DeepSeek 官方合同允许 `tool_choice=auto`
生成一个或多个工具调用，且没有列出关闭该行为的请求参数。当前 AgentLoop 已具有整批
数量、白名单和重复预检，并按返回顺序执行工具。

## 决策

1. DeepSeek Adapter 接受并严格解码多个 ToolCall，允许在后续请求中编码同一 assistant
   批次；
2. AgentLoop 在执行前对整批调用完成预算、白名单和重复检查，然后按返回顺序执行；
3. 不启用真正并发，不宣称 `parallel_tool_calls` capability；
4. 先用 Fake SDK、真实 AgentLoop/ToolRuntime/RAG/Harness 做 development TDD；
5. 当前 held-out 1.1.0 不重跑，真实诊断和新鲜 held-out 必须另过采用门。

## 影响

### 正面

- 与 DeepSeek 官方多工具响应合同兼容；
- 复用现有最小 Runtime，不增加并发基础设施；
- 越权、重复和超预算批次在任何本地工具执行前停止；
- 真实失败结果原样保留，不用调 Prompt 或删结果追绿。

### 负面

- 一个 Provider turn 可能触发多个本地工具工作量；
- 顺序执行不提供真正并发的延迟收益；
- 需要补强 Adapter 历史消息编码和 AgentLoop 原子预检测试；
- 修复后仍不能声称 DeepSeek 已通过领域准入。

## 备选方案

### 永久拒绝多 ToolCall

拒绝作为主方案。虽然最保守，但与厂商正式 `one or more tools` 合同不兼容，并已阻断
正常领域任务。

### 在请求中发送 `parallel_tool_calls=false`

拒绝。DeepSeek 当前官方请求合同没有列出该参数，不能依赖未声明的兼容字段。

### 并发执行全部 ToolCall

暂缓。当前没有延迟 Bad Case 和可取消并发 Runtime，收益不足以覆盖复杂度。

## 参考

- `docs/plans/2026-08-14-multi-tool-call-sequential-consumption-design.md`
- `docs/adr/0021-correct-heldout-injection-admission-before-execution.md`
- https://api-docs.deepseek.com/api/create-chat-completion
