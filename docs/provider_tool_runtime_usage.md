# Provider 与 Tool Runtime：使用方式、原理与边界

## 1. 这一层解决什么问题

RiftCoach 会调用多种外部或可替换能力：

- 智谱 GLM；
- Riot API；
- Data Dragon；
- 本地知识检索；
- 后续可能增加的 DeepSeek、远程检索与标准 MCP 服务。

如果每个脚本分别读取环境变量、创建 SDK Client、实现重试和解析错误，项目会产生多套不一致的调用逻辑。阶段 3 将这些职责分成三层：

```text
Harness
→ Tool Runtime
→ Provider / 具体业务 Client
```

- **Provider** 隔离模型厂商的请求、响应和错误差异；
- **Tool Runtime** 统一工具 Schema、缓存、重试、熔断、fallback 和指标；
- **Harness** 控制整次复盘任务的检索、生成、评测、修订和发布。

## 2. 目录结构

```text
app/
├── providers/
│   ├── models.py          # ChatRequest / ChatResponse 等厂商无关契约
│   ├── protocol.py        # LLMProvider Protocol
│   ├── errors.py          # 安全且可分类的 Provider 错误
│   ├── config.py          # 智谱配置与组装
│   └── zhipu.py           # 智谱 OpenAI-compatible 适配实现
│
└── tools/
    ├── models.py          # ToolDefinition / Context / Result / Policy
    ├── schema.py          # 输入与输出 JSON Schema 校验
    ├── registry.py        # 工具注册表
    ├── cache.py           # 有界进程内 TTL/LRU Cache
    ├── circuit_breaker.py # CLOSED / OPEN / HALF_OPEN 熔断器
    ├── metrics.py         # 工具结果分类和延迟计数
    ├── runtime.py         # 可靠执行顺序
    └── adapters/
        ├── riot.py
        ├── data_dragon.py
        ├── knowledge.py
        └── llm.py
```

## 3. Provider 数据流

上层只构造统一请求：

```python
ChatRequest(
    messages=(
        ChatMessage(
            role=MessageRole.USER,
            content="请生成复盘报告。",
        ),
    ),
    temperature=0.2,
    timeout_s=30,
)
```

`ZhipuProvider` 将它转换为智谱兼容请求，再把响应转换为：

```python
ChatResponse(
    content="...",
    model="...",
    provider="zhipu",
    usage=TokenUsage(...),
)
```

Harness 不允许访问 `response.choices` 或 `client.chat.completions`。这条边界由自动化测试和 CI 静态检查共同保护。

## 4. Tool Runtime 执行顺序

```text
查找工具
→ 输入 Schema 校验
→ 查询缓存
→ 检查熔断器
→ 在总预算内执行 Handler
→ 仅对可重试错误进行有限重试
→ 输出 Schema 校验
→ 写入缓存
→ 记录指标
→ 返回 ToolResult
```

### 4.1 为什么先校验再调用

模型或调用方产生的参数不一定正确。JSON Schema 是代码层约束，不是 Prompt 建议。错误参数在进入 Riot API 或模型前即被拒绝，并且不会被误记为上游服务故障。

### 4.2 为什么缓存位于熔断检查之前

上游故障时，已经存在且未过期的安全缓存仍可使用。缓存结果会标记：

```text
success = true
cached = true
attempts = 0
```

### 4.3 重试与熔断的区别

- 重试处理同一次调用中的短暂故障；
- 熔断器跨多次调用保存某个工具的近期健康状态。

只有 `retryable=True` 的错误会自动重试并计入熔断，例如限流、超时和服务不可用。认证失败、配置错误、输入错误和输出 Schema 错误不会自动重试，也不会使熔断器打开。

### 4.4 timeout 的真实边界

同步 Runtime 使用 `deadline_monotonic` 控制总预算和是否继续退避。它不会强杀任意卡死的 Python 函数。网络硬超时必须由底层 HTTP/SDK Client 使用 `ToolContext.remaining_s()` 执行。

## 5. 当前注册工具

| 工具名 | 能力 | 默认缓存 |
|---|---|---:|
| `riot.account_by_riot_id` | Riot ID 解析 | 60 秒 |
| `riot.recent_match_ids` | 最近比赛列表 | 15 秒 |
| `riot.match_detail` | 已结束比赛详情 | 300 秒 |
| `riot.match_timeline` | 已结束比赛时间线 | 300 秒 |
| `data_dragon.lookup_name` | 官方静态名称映射 | 24 小时 |
| `knowledge.search` | 本地复盘知识检索 | 300 秒 |
| `llm.chat` | Provider-neutral 模型调用 | 不缓存 |

玩家动态数据使用短缓存；已结束比赛与静态数据使用更长缓存；LLM 输出默认不缓存，避免不同上下文误用同一段生成内容。

## 6. ToolResult 的三种成功

```text
upstream success：Handler 真实成功
cache hit：未调用 Handler，直接命中缓存
fallback success：上游失败，但受控降级成功
```

三者必须分别计数。否则全部走 fallback 时，系统仍可能错误显示“上游成功率 100%”。

## 7. 本地运行

安装：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

先执行不消耗模型额度的完整 Harness：

```powershell
python scripts\run_review_harness.py `
  --summary examples\fixtures\player_summary_demo.json `
  --deterministic-report examples\fixtures\deterministic_report_demo.md `
  --run-id provider_runtime_demo `
  --dry-run
```

全量验证：

```powershell
python -m pytest -q
python -m compileall -q app scripts tests
```

## 8. 安全边界

- `.env`、API Key、本地玩家缓存和运行产物不得提交；
- Runtime 不把原始异常正文、Prompt 或工具参数写入 `ToolErrorInfo`；
- 缓存键只保存参数规范化后的 SHA-256 摘要；
- 缓存读写使用深拷贝，调用方修改结果不会污染缓存；
- PUUID 等玩家标识不得进入通用错误消息；
- Provider 配置错误使用安全错误码，不回显 credential。

## 9. 与 EchoMind 的关系

阶段 3 从 EchoMind 吸收：

- Tool 注册与参数校验思想；
- 超时、缓存、熔断和 fallback 思想；
- Monitor/指标思想；
- 模型与业务编排分离的方向。

阶段 3 对这些能力进行了重构：

- 将 Provider、Registry、Schema、Cache、Circuit Breaker、Runtime 和 Metrics 拆成独立模块；
- 使用 `LLMProvider` 隔离智谱厂商接口，而不是让各模块直接创建 SDK Client；
- 让评测、修订和 RAG 真正经过同一 Harness 主链；
- 使用自动化故障测试验证重试、熔断、缓存污染与敏感信息边界。

尚未从 EchoMind 迁移：

- Session 与用户隔离；
- 玩家长期 Memory；
- API 主链与用户画像；
- 更完整的在线 Monitor 和回归面板。

这些属于固定路线的阶段 6 或阶段 8，不在阶段 3 提前实现。

## 10. 与 MCP 的区别

当前 Tool Runtime 是 RiftCoach **进程内部**的执行层，不包含：

- MCP `initialize`；
- `tools/list`；
- `tools/call`；
- 协议版本协商；
- Streamable HTTP 会话与传输。

因此不能把它称为 MCP。标准 MCP Client、OP.GG 动态 Meta 和 RiftCoach MCP Server 属于阶段 7。未来 MCP 调用也应先适配为内部 ToolDefinition，再接受相同的可靠性和权限控制。

## 11. 当前限制

- Cache、熔断和 Metrics 是单进程内存状态，重启会清空；
- 尚未实现多实例共享或 Redis 后端；
- Runtime 是同步执行，不提供线程强杀；
- 指标尚未导出到 Prometheus 或 Web 面板；
- 当前 RAG 仍是 v0.1 轻量检索，正式检索评测和混合召回属于阶段 4；
- 当前是多阶段工作流，不宣称已经实现 Multi-Agent。

