# DeepSeek 多 ToolCall 批次顺序消费设计

## 1. 真实问题

DeepSeek V4 Pro 的第一次真实领域 held-out 在正常案例中返回多个 ToolCall。当前
`DeepSeekProvider` 在响应解码阶段要求 `len(tool_calls) <= 1`，因此返回
`unsupported_parallel_tool_calls`，没有形成统一 `ChatResponse`。Agent、工具、证据和
Evaluation 均未继续，Harness 安全降级。

DeepSeek 当前官方 Chat Completion 合同说明：`tool_choice="auto"` 可以调用一个或多个
工具，响应字段也是 `tool_calls[]`；官方请求合同没有列出关闭多工具调用的
`parallel_tool_calls=false` 参数。因此当前 Bad Case 是 RiftCoach Adapter 的传输合同比
厂商正式合同更窄，不应把它解释为模型输出非法。

本设计只处理 Provider 响应中的多 ToolCall 批次。它不重跑已消费的 Dataset 1.1.0，不
调整 Prompt，不增加模型，不实现真正并发，也不进入 5D exit review 或 5E。

## 2. 原理：生成和执行是两层职责

模型一次生成多个 ToolCall，只表示它提出了一批工具请求；是否并发执行属于 Agent
Runtime，而不是 Provider Adapter 的决定。

```text
厂商响应
  -> Provider Adapter：语法、工具别名、参数 JSON、调用 ID
  -> ChatResponse.tool_calls
  -> AgentLoop：白名单、重复、调用预算、deadline
  -> ToolRuntime：逐个实际执行
  -> 下一轮 Provider 请求
```

Adapter 只负责把有效厂商响应翻译成统一合同。AgentLoop 必须在执行任何一个工具前先
检查整批调用，避免第一项已经产生副作用后才发现第二项越权、重复或超预算。

## 3. 方案比较

### 方案 A：继续拒绝多个 ToolCall

优点是零改动、边界最保守。缺点是与 DeepSeek 官方 `one or more tools` 合同不兼容，
真实正常任务可能在第一轮就无法进入知识工具链。保留为失败关闭回退，不作为主方案。

### 方案 B：接受批次，由 AgentLoop 受控顺序执行

采用。Adapter 严格解码所有调用；AgentLoop 复用现有工具白名单、重复签名、
`max_tool_calls` 和总 deadline，先验证整批，再按模型返回顺序执行。无需线程池、并发
取消或新的 Runtime 抽象，且能兼容厂商正式响应合同。

### 方案 C：真正并发执行

暂缓。当前唯一工具是本地只读 `knowledge.search`，没有延迟证据证明并发收益足以覆盖
共享状态、取消、超时、结果顺序和部分失败处理的复杂度。未来只有 5E/5P 后出现可重复
延迟 Bad Case 才重新评估。

## 4. 采用后的控制流

假设模型返回两个知识检索：

```text
assistant.tool_calls = [search_A, search_B]
  -> Adapter 检查：ID 唯一、名称可逆、arguments 是唯一键 JSON object
  -> AgentLoop 检查：A/B 都在 Skill 白名单
  -> AgentLoop 检查：A/B 不重复，累计数量不超过 max_tool_calls
  -> ToolRuntime 顺序执行 A，再执行 B
  -> messages 追加 tool(A)、tool(B)
  -> 下一轮请求保留原 assistant 双调用和两个匹配的 tool_call_id
```

如果批次中任一调用越权、重复或导致预算超限，整批在工具执行前停止。Provider 请求已经
发生，因此仍计入 Provider 资源；但本地工具副作用保持为零。

如果某个已准入工具执行失败，ToolRuntime 返回类型化失败 Observation；AgentLoop 继续把
该结果交回模型，仍受总迭代和 deadline 约束。当前知识工具只读，不引入事务回滚承诺。

## 5. 合同变化

`DeepSeekProvider`：

- 移除响应 `len(tool_calls) > 1` 的绝对拒绝；
- 继续拒绝空 ID、重复 ID、非 function 类型、未知别名、重复 JSON key、非 object 参数；
- 历史 assistant message 可以编码多个 ToolCall，使第二轮请求能原样续接；
- 不设置或宣称 `ProviderCapabilities.parallel_tool_calls=True`，因为本实现没有并发执行。

`AgentLoop`：

- 保持现有“先检查数量，再检查全部工具名/重复签名，最后执行”的顺序；
- 用测试固定整批原子预检和按返回顺序执行，不因现有代码碰巧满足就省略合同证据；
- 不把 Provider Adapter 的限制复制成第二套工具数量上限。

## 6. Development 复现与测试

第一批全部离线，不读取 Key、不调用 Provider：

1. Fake DeepSeek SDK 返回两个不同 `knowledge.search` ToolCall，Adapter 解码并保序；
2. 第二轮历史 assistant 双调用和两个 tool result 能正确编码；
3. 重复 ID、未知工具、非法参数仍 fail closed；
4. AgentLoop 对两个允许调用按顺序执行，并把两个结果交回下一轮；
5. 批次总量超预算、任一越权、任一重复时，整批工具执行数为 0；
6. development 纵向切片用 Fake DeepSeek SDK + 真实本地 RAG + Harness，证明多个检索
   调用可以形成 Evidence、Evaluation 与安全终态；
7. 现有 GLM 单调用合同和所有历史结果必须继续可读。

## 7. 非功能与安全边界

- **安全**：所有调用在执行前完成整批白名单、重复和预算检查；模型正文不能授予权限。
- **可靠性**：任何解码失败仍返回安全 Provider error，Harness 保留确定性降级。
- **成本**：多 ToolCall 不增加 Provider 请求本身，但可能增加本地工具工作量；仍受
  Manifest `max_tool_calls` 和 deadline 约束。
- **可观测性**：现阶段复用 `AgentRunResult.tool_executions` 保留每个调用结果；统一 Trace
  仍属于 5E。
- **兼容性**：不修改 Skill、Prompt/Context Snapshot、Dataset 1.1.0 或产品默认 Provider。

## 8. 后续准入边界

离线 development 通过只能证明合同和本地控制流被修复，不能把当前 DeepSeek 领域结果
改写成通过。Dataset 1.1.0 已消费，永久保留 `admitted=false`。

若后续需要真实验证，先用新的 development 请求做有界协议诊断；只有获得公开 CI、资源
门和新鲜案例后，才能创建新的 held-out 版本。不得删除旧结果或在旧三题上重跑追绿。

## 参考

- DeepSeek Create Chat Completion：
  https://api-docs.deepseek.com/api/create-chat-completion
- `app/providers/deepseek.py`
- `app/agent/loop.py`
- `data/evaluation/results/provider_capabilities/deepseek_v4_pro_domain_heldout.json`
