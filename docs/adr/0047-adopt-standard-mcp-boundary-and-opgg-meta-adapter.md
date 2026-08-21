# ADR-0047：采用标准 MCP 边界与受限 OP.GG Meta Adapter

## 状态

Accepted for Stage 7 entry design（2026-08-21）。本 ADR 冻结边界与准入条件，
不代表已安装 SDK、已准入 OP.GG 或已完成真实互操作。

## 背景

阶段 7 要解决两件容易被混淆的事：一是让 RiftCoach 能与外部标准 MCP Server
交换工具，二是把随补丁变化的动态 Meta 数据送入 Coach。现有仓库已经有稳定的
`ToolDefinition`、`ToolRegistry` 和负责超时、重试、缓存、熔断、fallback、指标的
`ToolRuntime`，但它只执行进程内工具，不具备 MCP 的 `initialize`、能力协商、
`tools/list`、`tools/call`、session 或 transport 合同。普通 HTTP POST、任意 JSON
RPC 或本地 Tool Manager 都不能因此被称为 MCP（ADR-0005）。

OP.GG 是首选的动态 Meta 候选，但在入口设计阶段尚未证明存在可公开准入的标准
MCP Server、协议版本、transport、工具 schema、许可/再分发条款或稳定部署条件。
因此不能把 OP.GG 网页/API 推测为 MCP，也不能在没有准入记录时静默换成另一个来源。

## 决策

### 1. 采用 adapter-first 的双向边界

外部调用方向固定为：

```text
外部 MCP Server
  -> StandardMcpClient / Protocol Adapter
  -> ToolDefinition + existing ToolRuntime
  -> MetaAdapter
  -> MetaEvidence
  -> Context / Skill / Harness
```

对外暴露方向固定为：

```text
外部 MCP Client
  -> RiftCoach MCP Server Adapter
  -> restricted Application Facade
  -> owner-scoped existing services
```

MCP Adapter 只负责 JSON-RPC/MCP envelope、版本、capability、工具发现、调用、
session/transport 和协议错误。`ToolRuntime` 继续负责 deadline、retry、cache、
circuit breaker、fallback、metrics 和安全的内部错误映射；业务代码不得直接依赖
MCP SDK。若未来采用 SDK，它只能被包在该 Adapter 后面并通过同一合同测试。

### 2. MCP Client V1 的最小合同

Client 必须先完成 `initialize`，验证协商出的 protocol version 与服务端能力，
再允许 `tools/list` 和 allowlist 内的 `tools/call`。每次调用都绑定 session、
call id、deadline 和工具 schema 快照；未知工具、缺少 capability、版本不兼容、
schema drift、非法 envelope、过大/畸形结果、断线、超时和 server error 均映射为
有限安全错误，不能把原始 body 写入 Trace、日志或响应。

V1 先用本地 fixture/subprocess 证明协议与 transport 边界；真实外部 Server 和
真实外部 Client 只在退出门执行，不用 fixture 冒充互操作。

### 3. MetaEvidence 是唯一进入业务上下文的动态 Meta 形状

Meta Adapter 将外部工具结果规范化为有界、data-only 的 `MetaEvidence`，至少包括：

- `source`、server/tool identity；
- patch/version；
- `fetched_at` 与 `expires_at`/freshness 状态；
- canonical content digest；
- allowlisted normalized facts；
- safe error code（成功时为空）。

动态 Meta 不得覆盖玩家 subject、owner、Conversation、Preference、Profile、Plan、
Progress 或 RAG 原文；不得成为 system instruction，也不能直接写 Memory。它只能
作为带来源和新鲜度的外部证据，经过既有 Context trust/data-only 规则进入 Skill 或
Harness。stale、schema invalid、digest mismatch、身份/patch 缺失或超出大小上限时
fail closed。

### 4. OP.GG 的条件准入

只有下列证据全部具备，OP.GG 才能成为真实 Provider：官方 endpoint/server 身份、
标准 MCP protocol/version、transport 与 session 语义、`initialize`/`tools/list`/
`tools/call` trace、工具 schema、许可和再分发边界、patch/freshness 字段、限流/可靠性、
公开部署和可重复互操作记录。若任何一项不满足，必须新增 ADR 选择替代标准 MCP
Server 或保持动态 Meta deferred；不得把普通 OP.GG HTTP 接口改名为 MCP。

### 5. 对外 RiftCoach MCP Server 的权限

RiftCoach Server 只投影已有 Application Service 的 owner-scoped、安全 DTO，候选工具
为近期汇总、单局分析、知识搜索和报告评测。它不暴露数据库、文件、任意 URL/SQL、
PUUID、Key、Prompt、Provider/Tool body 或内部异常，也不绕过现有 ActorContext、
Task/Artifact/Harness 发布门。

## 备选方案

### A. 直接在业务代码中调用 OP.GG HTTP

拒绝：无法证明 MCP 互操作，容易绕过 ToolRuntime 可靠性、权限和 freshness 边界，
也会把普通 HTTP 误报成标准 MCP。

### B. 让业务层直接依赖某个 MCP SDK

拒绝：SDK 版本、transport 和错误模型会渗透所有 Skill/Application，难以测试和替换；
也没有解决 Meta 的来源、patch、TTL 和安全投影问题。

### C. Adapter-first（本 ADR）

采用：保留现有可靠性资产，能用纯合同/fixture 先验证协议，真实 Server/Client 只在
退出门接入；代价是需要维护一层严格映射和真实互操作证据。

## 后果

### 正面

- MCP 命名与普通 Tool Runtime/HTTP 清晰分离；
- 协议、可靠性、业务权限和 Meta 规范化可以分别测试和演进；
- 外部动态数据不会直接污染长期 Memory、RAG 或 system prompt；
- OP.GG 若不满足合同，可以有证据地拒绝，而不是静默替换。

### 负面

- 需要维护协议 envelope、transport/session 和 schema drift 合同；
- 真实互操作依赖外部 Server/Client、许可和部署条件，可能保持 deferred；
- V1 的 freshness、allowlist 和 body-free observability 会限制可接收数据范围。

## 失败与安全边界

版本不兼容、capability 缺失、未发现工具、allowlist 越权、参数/结果 schema 失败、
过大结果、断线、超时、限流、digest/freshness 失败和 prompt injection 均必须可观测
为有限错误并 fail closed。任何外部内容均是不可信 data，不得改变执行身份、工具权限、
系统指令、Memory 写入或 owner scope。

## 参考

- `docs/adr/0005-standard-mcp-only.md`
- `docs/roadmap.md` 阶段 7
- `docs/architecture_capability_matrix.md` A15/Q03
- `app/tools/models.py`, `app/tools/registry.py`, `app/tools/runtime.py`
- `app/api/composition.py`, `app/product/*`, `app/agent/*`, `app/harness/*`
