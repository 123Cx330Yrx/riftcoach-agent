# Provider 与 Tool Runtime 设计说明

## 1. 要解决的真实问题

当前 RiftCoach 已经有稳定的领域事实层和 Harness v1，但外部调用仍散落在脚本和业务模块中：

- 多个脚本分别读取 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`；
- 多处直接实例化 OpenAI-compatible Client；
- Riot API、Data Dragon、RAG 与 GLM 没有统一的调用结果和错误分类；
- 超时、重试、缓存、fallback 和统计由各模块自行处理或完全缺失；
- Harness Adapter 仍然知道具体 Chat Completion Client 的响应结构。

这会导致模型厂商难以替换、错误无法统一处理、重试可能失控、日志可能泄漏敏感信息，也无法回答“某个工具为何失败、重试了几次、是否命中缓存、熔断是否打开”。

阶段 3 的目标不是增加新的 Agent 能力，而是建立可靠的外部调用基础设施。

## 2. 需求与边界

### 功能需求

- 定义厂商无关的 `LLMProvider` 契约；
- 实现智谱 GLM Provider，并保留未来 DeepSeek 等实现空间；
- 定义工具注册、参数 Schema、调用上下文和统一结果；
- 支持有限重试、TTL 缓存、熔断、fallback 与运行统计；
- 将 Riot、Data Dragon、本地 RAG 和 LLM 能力逐步包装为工具；
- 让 Harness 不再直接依赖 OpenAI-compatible SDK；
- 使用 Fake Provider/Tool 完成无网络契约和故障测试。

### 非功能需求

- 所有重试和等待都有明确上限；
- 默认不记录 API Key、Authorization Header、完整 PUUID 或模型原始敏感请求；
- 相同输入的缓存键稳定、可解释；
- 每个工具独立熔断，不因一个外部服务故障阻塞其他工具；
- 单元测试不调用 Riot、Data Dragon 或 GLM；
- 不引入数据库、消息队列、Redis 或重型可观测平台。

### 本阶段不做

- 不实现标准 MCP；
- 不改进 RAG 召回算法；
- 不实现 Skill 路由；
- 不实现 Session、Memory 或 FastAPI 对话；
- 不实现 DAG、Multi-Agent、分布式任务、租约或中断恢复。

## 3. 方案比较

### 方案 A：只抽象 LLMProvider

优点是改动最小，可以快速消除脚本中的重复 Client 创建。缺点是 Riot、Data Dragon 和 RAG 仍各自处理错误，缓存、熔断和统计仍然分散，不能满足阶段 3 的 Tool Runtime 目标。

### 方案 B：Provider 与 Tool Runtime 分层（采用）

Provider 是厂商适配层，负责把通用聊天请求转换为智谱/OpenAI-compatible SDK 请求；Tool Runtime 是可靠执行层，负责注册、校验、重试、缓存、熔断、fallback 和指标。Provider 可以被某个 Tool 调用，但两者不合并。

该方案与现有 Harness 的职责最清晰：

```text
Harness：执行顺序、Artifact、质量门控和发布
Tool Runtime：单个能力如何可靠调用
Provider：某个外部厂商具体怎样调用
领域层：比赛事实和复盘规则
```

### 方案 C：直接迁移 EchoMind MCPToolManager

EchoMind 的实现提供了工具注册、TTL 缓存、熔断、fallback 和统计等有价值思想，但它同时持有 Anthropic Client，并混入查询改写和 LLM 重排；参数校验只覆盖 JSON Schema 的少量字段，fallback 成功与主调用成功也没有充分区分。直接复制会保留厂商耦合和职责混杂，并继续造成“内部 Tool Manager 等于 MCP”的命名误导，因此不采用。

## 4. 高层结构

```text
app/
├── providers/
│   ├── models.py          # ChatRequest、ChatResponse、Usage
│   ├── protocol.py        # LLMProvider
│   ├── errors.py          # Provider 错误分类
│   ├── zhipu.py           # 智谱 OpenAI-compatible 适配
│   └── config.py          # 环境变量装配与脱敏配置
│
├── tools/
│   ├── models.py          # ToolDefinition、ToolContext、ToolResult
│   ├── errors.py          # Tool 错误分类
│   ├── schema.py          # 参数/返回 Schema 校验
│   ├── registry.py        # 注册、查找、重复检测
│   ├── cache.py           # 有界 TTL Cache
│   ├── circuit_breaker.py # CLOSED/OPEN/HALF_OPEN
│   ├── runtime.py         # 调用控制面
│   ├── metrics.py         # 次数、延迟、缓存、重试、fallback
│   └── adapters/          # Riot、Data Dragon、RAG、LLM 工具
│
└── harness/
    └── adapters.py        # 改为依赖 Provider/Tool Runtime
```

Provider 和 Tool Runtime 是普通 Python 模块，不是单独服务，也不是微服务。

## 5. Provider 契约

通用输入只保留 RiftCoach 当前真正使用的能力：

```python
ChatRequest(
    messages=(ChatMessage(role="system", content="..."), ...),
    temperature=0.0,
    max_tokens=None,
    timeout_s=30.0,
    metadata={"operation": "coach_evaluation"},
)
```

输出转换为：

```python
ChatResponse(
    content="...",
    model="glm-...",
    provider="zhipu",
    finish_reason="stop",
    usage=TokenUsage(...),
    request_id="...",
)
```

业务代码不能读取 `response.choices[0].message.content`。Provider 将厂商异常转换为稳定错误：

- `ProviderConfigurationError`
- `ProviderAuthenticationError`
- `ProviderRateLimitError`
- `ProviderTimeoutError`
- `ProviderUnavailableError`
- `ProviderResponseError`

错误对象只保存安全元数据，不保存 Key 或完整请求正文。

## 6. Tool Runtime 契约

工具定义包含：

- 唯一名称、版本和描述；
- 输入/输出 JSON Schema；
- Handler；
- 超时和重试策略；
- 缓存策略；
- 熔断策略；
- 可选 fallback；
- `idempotent` 标记。

调用返回统一 `ToolResult`：

```python
ToolResult(
    success=True,
    data={...},
    tool_name="lol.riot.recent_matches",
    attempts=1,
    latency_ms=82.4,
    cached=False,
    fallback_used=False,
    error=None,
)
```

主调用失败后 fallback 返回的数据必须标记 `fallback_used=True`，不能伪装成上游服务正常。只有幂等操作或明确允许的错误才能重试。缓存命中不触发 Handler，也不计为上游成功调用。

## 7. 超时、重试与迟到结果

阶段 3 保持同步运行。对于 HTTP/LLM 工具，真实超时由 `requests`、OpenAI-compatible SDK 等底层客户端执行，ToolContext 向 Handler 传递剩余预算。Runtime 不使用无法安全终止的后台线程来制造“假取消”。

重试使用有界退避：

```text
attempt 1
→ retryable error
→ delay
→ attempt 2
→ 最多达到 max_attempts
```

默认只重试限流、临时不可用和网络超时；认证失败、参数错误、Schema 错误不重试。每次调用携带 `call_id` 和 deadline，超过 deadline 的返回不能写入缓存或被当作成功结果。

## 8. 缓存、熔断与 fallback

TTL Cache 使用稳定 JSON 序列化计算键，并设置最大条目数。只缓存成功且通过输出 Schema 校验的结果。含用户敏感数据或动态强一致要求的工具默认禁用缓存。

熔断器按工具实例隔离：

```text
CLOSED
→ 连续可计数失败达到阈值
→ OPEN
→ 恢复窗口结束
→ HALF_OPEN
→ 探测成功回 CLOSED，失败回 OPEN
```

fallback 是明确的降级产物，例如 GLM 不可用时 Harness 可使用确定性报告。fallback 不负责掩盖参数错误或认证配置错误。

## 9. 测试策略

- Provider 契约：Fake SDK 响应、空响应、超时、限流、认证和非法结构；
- Schema：必填、类型、额外字段、返回值不合法；
- Retry：仅可重试错误重试，次数和延迟受控；
- Cache：命中、过期、不同参数、容量上限；
- Circuit：三态转换、恢复探测和工具隔离；
- Fallback：成功、失败和显式标记；
- Metrics：调用、上游成功/失败、缓存、重试、fallback 和延迟；
- Integration：Harness 通过 Provider/Tool Runtime dry-run，不直接创建 SDK Client。

所有时间、睡眠和 Client 都通过依赖注入控制，测试不等待真实时间。

## 10. EchoMind、Saber 与 Sea 的吸收边界

从 EchoMind 吸收：

- 工具注册与统一结果；
- TTL 缓存、熔断、fallback 和统计思想；
- Monitor 使用运行指标的思想。

修正 EchoMind：

- 去掉 Anthropic Client 与 Tool Manager 的耦合；
- 不把 Tool Runtime 称为 MCP；
- Schema 使用独立组件；
- 区分主调用成功、缓存命中和 fallback 成功；
- 不把 RAG 查询改写/重排放进通用 Runtime。

本阶段暂不迁移 Saber 的 DAG、取消和快照，也不迁移 Sea 的 Scheduler、租约和沙箱；只保留 `call_id`、预算和迟到结果不可污染当前调用的可靠性原则。
