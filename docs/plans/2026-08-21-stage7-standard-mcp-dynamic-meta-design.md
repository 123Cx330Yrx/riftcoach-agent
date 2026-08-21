# Stage 7 Standard MCP + Dynamic Meta Entry Design

## 目标

在不提前写产品 MCP 代码或执行外部 I/O 的前提下，冻结 RiftCoach 的标准 MCP
互操作边界、OP.GG 动态 Meta 准入门、证据分层、权限/失败合同和后续实施顺序。

## 初学者教学：这次到底解决什么

MCP 可以理解为“工具如何被另一个程序发现和调用”的公共语言；它不是一个更响亮
的 Tool Runtime 名称。当前 RiftCoach 的 Tool Runtime 已经能在本进程内对工具做
Schema 校验、超时、重试、缓存、熔断和 fallback，但外部程序还不知道如何初始化
会话、发现工具或表达调用错误。Stage 7 要补的是跨进程/跨产品的协议边界，同时
接收会随 patch 变化的 Meta 数据。

这次 entry design 只做教学、源码接缝审计、方案比较和文档冻结。它不安装 MCP SDK，
不实现 Client/Server，不请求 OP.GG，不读取 Key，不把 HTTP API 当 MCP，也不把外部
Meta 写入 Memory。真正的实现会先做纯协议合同，再做本地 fixture/transport，之后才
做 Meta 规范化和 RiftCoach Server，最后才允许真实外部互操作。

## 已审计的接缝

| 接缝 | 事实 | 设计结论 |
|---|---|---|
| Tool contract | `ToolDefinition` 有名称、版本、JSON Schema、policy、handler | MCP tool 先映射到该合同，再交给 Runtime |
| Tool reliability | `ToolRuntime` 负责 timeout/retry/cache/breaker/fallback/metrics | Adapter 不复制可靠性逻辑 |
| Provider boundary | Provider 有 capability/error/usage 合同 | MCP 不伪装成 LLM Provider；错误单独映射 |
| Application | `app/api/composition.py`、`app/product/*` 已有 owner-scoped Facade | 对外 Server 只调用 Facade，不直达 Repository |
| Context/Memory | Context 有 trust/data-only/ceiling；6B 已有 owner-scoped Memory 与 lifecycle | Meta 只能成为带来源 freshness 的证据，不写 Memory |
| Harness/Runtime | Harness 掌握 evaluation/publication；Runtime 记录安全元数据 | MCP 结果不能绕过 Artifact、评测或发布门 |

## 目标架构

```text
外部 MCP Server
    │ initialize / tools/list / tools/call
    ▼
Standard MCP Client + Transport Session
    │ version/capability/schema/allowlist
    ▼
MCP Protocol Adapter ──► ToolDefinition ──► ToolRuntime
    │                                      │ timeout/retry/cache/breaker
    ▼                                      ▼
Meta Adapter ──► MetaEvidence              existing Skill/Context/Harness

外部 MCP Client ──► RiftCoach MCP Server Adapter
                         │ restricted Application Facade
                         ▼
                 RecentReview / Knowledge / Report services
```

Adapter 是协议防火墙：只允许已发现且 allowlisted 的工具，保存 version/schema
identity 和 body-free trace；Tool Runtime 是可靠执行层；Meta Adapter 是领域翻译层；
Application Service 是业务权限层。四层不可合并成一个“万能 MCP handler”。

## MCP Client V1 合同

1. `initialize` 是唯一会话起点，协商版本必须在 allowlist；版本不兼容立即停止。
2. capability 必须声明 tools，缺失时禁止 discovery/call。
3. `tools/list` 结果必须是有限大小、唯一名称、合法 JSON Schema 的工具目录；目录
     快照带 server identity 和 digest，schema 变化使旧调用失效。
4. `tools/call` 只接受 allowlist 工具和符合 schema 的 arguments；call id、session、
   deadline 和结果上限由 Adapter 绑定。
5. MCP error、`isError`、断线、超时、server restart、malformed JSON 和 oversized
   result 映射为有限内部错误；不暴露原始 body。
6. 本地 fixture 必须覆盖 `initialize`、`tools/list`、`tools/call`、版本/能力/Schema
   失败和断线/超时；fixture 只能证明合同，不算真实互操作。

## MetaEvidence 与数据分层

四类数据保持分层：

1. 玩家事实：Riot/MatchAnalyzer 的确定性公开事实；
2. 静态映射：Data Dragon 等版本化本地映射；
3. RAG 知识：有引用的教练知识；
4. 动态 Meta：外部 MCP 工具返回的 patch/freshness 证据。

`MetaEvidence` 的最小字段为 `source`、`server_id`、`tool_name`、`tool_version`、
`patch`、`fetched_at`、`expires_at`/`freshness`、`digest`、allowlisted facts 和
安全 error code。禁止保存 PUUID、Key、Prompt、Provider/Tool body、任意 URL/SQL/
文件路径。Meta 不能覆盖 owner/player/conversation identity，不能写 Preference、
Profile、Plan、Progress 或 Candidate；只有显式 typed proposal 才能走既有 Candidate
gate，默认没有 proposal。

## OP.GG 准入审计门

Entry design 只建立审计清单，不宣称 OP.GG 已满足：

- 可验证的官方 MCP Server/endpoint 身份；
- protocol version、transport、session 生命周期；
- `initialize`、`tools/list`、`tools/call` trace 与 schema；
- patch、版本、时间戳、TTL/freshness 和 digest 可用性；
- 许可、缓存、再分发、商标和公开部署限制；
- 认证、限流、错误、可靠性和可观测性；
- 可在脱敏环境复现、并由真实外部 Client 调用的互操作证据。

RQ-076/ADR-0048 后，本清单按两层裁决：标准 endpoint/protocol/list/call 与获准工具合同
是连接硬门；patch/freshness/限流/底层数据条款缺口将 provenance 降为 partial，并限制
可支持的声明，不再自动整体 deferred。普通 OP.GG HTTP endpoint 仍不能满足 MCP 硬门。

## RiftCoach MCP Server 范围

候选 read-only tools：近期汇总、单局分析、知识搜索、报告评测。它们通过现有
Application Service 和 ActorContext 做 owner scope，返回 body-safe typed DTO、
引用/摘要和安全错误。V1 不开放写 Memory、任意 SQL/URL/文件、原始比赛/PUUID、
Provider/Tool body、内部堆栈或管理操作。

## 方案比较

| 方案 | 结论 | 原因 |
|---|---|---|
| 直接 HTTP/网页抓取 | 拒绝 | 不是 MCP，无法证明 initialize/discovery/session 互操作 |
| 业务层直依赖 SDK | 拒绝 | 版本/transport/错误泄漏，复制 Runtime 可靠性 |
| Adapter-first + existing Runtime | 采用 | 可离线 TDD、替换实现、复用安全与可靠性，真实 I/O 后置 |

## 阶段边界与验收

本检查点通过条件：ADR、设计、实施计划、学习材料、canonical/roadmap/coverage
同步；治理、完整回归、compile、RAG、Harness、secret/tracked-data、diff 和 exact-SHA
三 job 全绿。它不通过任何产品互操作条件。

后续阶段 7 原子顺序：

1. `7-1-mcp-client-contract`：pure envelope/capability/tool/error models；
2. `7-2-mcp-transport-and-discovery`：fixture、stdio/HTTP transport、session/error；
3. `7-3-opgg-meta-adapter`：仅在 OP.GG 审计通过后实现 MetaEvidence 映射；
4. `7-4-riftcoach-mcp-server`：受限 Application Facade 对外工具；
5. `7-5-mcp-interoperability-exit-review`：真实外部 Server + Client、八维证据和退出门。

## 已知限制

尚未确认 OP.GG 的标准 MCP 部署、许可、版本或工具 schema；尚未选择 SDK/transport
实现；没有真实外部调用、质量、延迟、限流或部署证据。阶段 7 不改变现有正式 Auth/
RSO、HTTPS、SSE、前端和阶段 8 恢复/Multi-Agent 的 deferred 状态。
