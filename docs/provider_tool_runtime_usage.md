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
- 阶段 4 后 RAG 已升级为本地混合检索并有独立门禁，但 Tool Runtime 只负责可靠
  调用 `knowledge.search`，不负责检索算法、索引构建或引用是否语义支持结论；
- 当前是多阶段工作流，不宣称已经实现 Multi-Agent。

## 12. 从设计要求到真实实现的证据矩阵

阶段 3 不是一次大提交完成的。它按合同 → 实现 → Adapter → Harness 迁移 → 故障
验收推进，最后由提交 `592305a7692bfbe538348461a51f07d88524d35f` 收尾。下面把
“设计上应该有”与“仓库中真实在哪里”逐项对齐。

| 要求 | 权威源码 | 直接测试 | 实际证明 | 限制/不能外推 |
|---|---|---|---|---|
| 厂商无关聊天请求、响应、Usage 和错误 | `app/providers/models.py`、`protocol.py`、`errors.py` | `tests/test_provider_contracts.py` | 业务层可依赖 `LLMProvider.chat(ChatRequest) -> ChatResponse`；错误只暴露安全分类字段 | 合同可替换不等于第二 Provider 已通过领域质量门 |
| 智谱 SDK 与通用合同隔离 | `app/providers/zhipu.py`、`config.py` | `tests/test_zhipu_provider.py` | 请求映射、响应规范化、配置缺失、认证、限流、超时、坏结构均有 Fake SDK 边界 | 阶段 3 测试不访问真实网络；后来 Tool Calling/structured mapping 属于 5D 深化 |
| 工具身份、策略、Context、Result 与 JSON Schema | `app/tools/models.py`、`schema.py`、`registry.py` | `tests/test_tool_contracts.py`、`test_tool_registry.py` | 坏输入在 Handler 前失败、坏输出不进入上层、重复/坏定义不进入 Registry | Registry 是进程内目录，不是 MCP `tools/list`，也不是远程服务发现 |
| 有界 TTL/LRU Cache | `app/tools/cache.py` | `tests/test_tool_cache.py` | 等价嵌套参数产生稳定键；TTL、容量淘汰、工具版本隔离和深拷贝有测试 | 进程重启即清空；不是 Redis 或跨实例一致缓存 |
| 每工具三态熔断 | `app/tools/circuit_breaker.py` | `tests/test_circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN、单探针、恢复与不同工具隔离可重复验证 | 状态不跨进程；不是服务网格或分布式健康判断 |
| Schema→Cache→Circuit→Retry→Fallback→Metrics 的可靠执行 | `app/tools/runtime.py`、`metrics.py` | `tests/test_tool_runtime.py` | 仅 retryable 错误有限重试；认证/输入/输出失败不误重试；cache/upstream/fallback 分开计数 | 同步 Runtime 不能强杀任意卡死 Python Handler；底层 Client 必须使用剩余预算 |
| Riot、Data Dragon、RAG、LLM 统一适配 | `app/tools/adapters/*.py` | `tests/test_riftcoach_tool_adapters.py` | 稳定工具名、输入输出 Schema、缓存策略和 `ToolContext.remaining_s()` 传递被固定 | Fake 依赖证明接线，不证明 Riot/模型外网成功或数据许可 |
| Harness 不认识 SDK `choices` | `app/harness/adapters.py` | `tests/test_harness_adapters.py`、`test_provider_tool_harness_integration.py` | 生成、评测、修订和检索经过 `llm.chat`/`knowledge.search`；源码中禁止直接 SDK shape | Harness 通过接线不等于每份模型草稿质量合格 |
| 故障、降级与敏感信息边界 | 上述 Provider/Runtime/Adapter | `tests/test_tool_runtime_fault_integration.py` | 限流后成功、认证失败不重试且脱敏、open circuit fallback、缓存深拷贝均有纵向测试 | 安全错误包不是完整威胁模型、正式 Auth 或公网日志治理 |

### 12.1 实施提交链

| 提交 | 当时完成的切片 |
|---|---|
| `42eb217` | Provider-neutral 模型、Protocol 与安全错误合同 |
| `7fea401` | 注入式 Zhipu Provider 和集中配置 |
| `64e4394` | Tool 模型、JSON Schema 与 Registry |
| `39ba022` | TTL/LRU Cache 与三态 Circuit Breaker |
| `57ffffd` | 可靠 `ToolRuntime` 与分类型 Metrics |
| `1e2d913` | Riot、Data Dragon、Knowledge、LLM Adapter |
| `e706d81` | Harness 与 CLI 从 SDK shape 迁移到 Provider/Tool Runtime |
| `592305a` | 故障纵向、安全/CI 门、本文档与阶段 3 退出收尾 |

这里列提交不是让学习者背哈希，而是说明稳定合同怎样逐层获得消费者。最后一个
提交存在，不代表前七个检查点可以被压缩成“一次把所有东西写完”。

## 13. 公共 CI 与当前可复现观察

### 13.1 阶段 3 当时的公共退出证据

提交 `592305a7692bfbe538348461a51f07d88524d35f` 对应 GitHub Actions run
`29987181410`，结论为 `success`。同一 SHA 的公开 job 记录：

```text
124 passed, 51 subtests passed
compileall passed
Harness SDK boundary passed
tracked Secret/run-data check passed
Harness dry-run: published, 0 revisions
```

这证明阶段 3 的代码、静态边界和无网络 fixture 主链能在干净 Linux CI 重建。
`dry-run published` 使用确定性 Fake/fixture 路径，不是一次真实 GLM 质量验收。

### 13.2 RQ-067 当前聚焦复跑

当前仓库已经在 5D/5E 等后续阶段深化 Provider 模型和 Runtime Observer。为了确认
阶段 3 地基仍然可回归，本次运行：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_provider_contracts.py `
  tests\test_zhipu_provider.py `
  tests\test_tool_contracts.py `
  tests\test_tool_registry.py `
  tests\test_tool_cache.py `
  tests\test_circuit_breaker.py `
  tests\test_tool_runtime.py `
  tests\test_riftcoach_tool_adapters.py `
  tests\test_harness_adapters.py `
  tests\test_provider_tool_harness_integration.py `
  tests\test_tool_runtime_fault_integration.py -q
```

实际结果为 `101 passed, 68 subtests passed`。数字变化来自后续合同加固，不应把
所有当前用例倒算成阶段 3 当时一次完成。

本次还执行了文档第 7 节的 Harness dry-run，实际观察为：

```text
Run ID: provider_runtime_learning_review
Status: published
Decision: published
Revisions: 0
```

要理解的不是“published”这个词本身，而是：CLI 可以在没有真实 Key 和网络调用时，
沿统一 Adapter/Runtime 接缝完成检索、生成、评测和发布状态机。它验证组合接线，
不验证厂商模型、真实 Riot 或公网部署。

## 14. 怎样读一次 Tool Runtime 结果

面对一个 `ToolResult`，不要只看 `success`：

```text
success=true, cached=false, fallback_used=false, attempts>=1
→ Handler 上游成功且输出通过 Schema

success=true, cached=true, attempts=0
→ 复用了未过期缓存，没有调用 Handler

success=true, fallback_used=true, upstream_error!=None
→ 上游或 Circuit 失败，受控降级成功

success=false, error!=None
→ 主路径和可用 fallback 都没有形成合法产物
```

例如 open circuit 场景中，第二次调用可以是 `success=true`，但同时
`fallback_used=true`、`attempts=0`、`upstream_error.code="circuit_open"`。如果监控只
统计 `success`，就会把“上游完全没调用，系统正在降级”误报成服务健康；这正是
Runtime 将三种成功拆开的原因。

## 15. 后续阶段怎样深化这层

- 3G 增加 Tool Calling 消息合同、Provider Capability Negotiation 与 Registry；
- 5D 增加结构化输出、Zhipu/DeepSeek Tool Calling Adapter 采用门和领域评测；
- 5E 通过可选 Observer 把 Provider/Tool 的安全事件和 Usage 汇入统一 Runtime Trace；
- 5F 用既有合同审计 Pi sidecar，最终没有把第三方 Runtime 接入产品主链；
- 阶段 7 才把标准 MCP 远程工具适配为内部 `ToolDefinition`。

因此当前 `app/providers/zhipu.py`、`models.py` 和 `ToolRuntime` 比阶段 3 退出时更强。
阅读当前源码要区分“阶段 3 建立的可靠调用地基”与“后续真实消费者发现 Bad Case 后
加入的结构化输出、Tool Calling、Context deadline 和 Observer”；后者没有推翻前者。

## 16. 面试时可以怎样说

> 我把模型厂商适配和工具可靠执行拆成两层：`LLMProvider` 将厂商 SDK 归一成
> `ChatRequest/ChatResponse` 与安全错误；`ToolRuntime` 对任意注册能力统一做 JSON
> Schema、有限重试、TTL/LRU 缓存、每工具熔断、fallback 和分类指标。Harness 只通过
> Adapter 消费这些合同，仍独立负责工作流和发布。我用 Fake 依赖、故障注入、无网络
> Harness 纵向和 exact-SHA CI 验证了边界。

若被问“为什么不直接复制 EchoMind”，可以回答：

> EchoMind 的缓存、熔断和工具管理思想有价值，但原实现把厂商 Client、查询改写和
> 工具管理混在一起，而且名称容易被误解为标准 MCP。我保留机制思想，重写为独立
> Provider、Schema、Registry、Runtime 和 Metrics，并用故障测试验证主调用、cache hit
> 与 fallback success 的差异。

若被问同步 timeout，可以准确回答：

> Runtime 用 monotonic deadline 决定剩余预算、退避和是否继续，但 Python 同步代码
> 不能安全强杀任意阻塞 Handler。网络 Adapter 必须把 `ToolContext.remaining_s()` 传给
> requests/SDK 的真实 timeout；通用取消、lease 和恢复属于后续 Runtime 阶段。

## 17. 面试时不可以怎样说

- “Tool Runtime 就是 MCP”；它没有 initialize、tools/list、tools/call 或传输会话；
- “有 `ProviderRegistry` 就实现了自动模型路由”；显式解析、自动选择和 Multi-Agent
  是不同问题；
- “同步 timeout 能终止任何卡死函数”；它只提供 deadline 协作边界；
- “fallback 成功说明上游健康”；必须结合 `fallback_used/upstream_error` 解读；
- “缓存、熔断和 Metrics 已经分布式共享”；V1 都是进程内状态；
- “Fake SDK 和 101 项测试证明 GLM/DeepSeek 领域质量”；真实模型采用必须经过后续
  独立协议门与领域评测；
- “Harness dry-run published 代表线上产品已经部署”；它只验证本地无 I/O 组合；
- “阶段 3 已经实现 Session、Memory、正式 Auth、SSE、前端或 Multi-Agent”。

## 18. 阶段 3 的准确退出结论

阶段 3 已完成可替换 Provider 合同和进程内可靠 Tool Runtime V1，并让 Harness 的
生成、评测、修订和 RAG 通过同一抽象主链。其边界有真实代码、故障测试、无网络
纵向和 exact-SHA 公共 CI 支持。

退出结论不包含真实模型领域质量、分布式状态、标准 MCP 或生产部署。这些未完成项
被保留到既定后续阶段，而不是用“Provider/Tool Runtime 已完成”这一句话掩盖。
