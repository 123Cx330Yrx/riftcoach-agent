# ADR-0047：采用标准 MCP 边界与受限 OP.GG Meta Adapter

## 状态

Accepted for Stage 7 entry design（2026-08-21）。本 ADR 冻结边界与准入条件，
不代表已安装 SDK、已准入 OP.GG 或已完成真实互操作。

2026-08-21 修订：RQ-076 与 ADR-0048 已把“缺任一 provenance 合同就整体 deferred”
修正为分级准入。OP.GG 现允许以 partial provenance 真实接入；patch/freshness/数据条款
缺口继续限制可支持的声明，而不再否定已经验证的标准 MCP transport/list/call。

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

V1 先用本地 fixture/subprocess 证明协议与 transport 边界。RQ-076 后，7-3 可以对
获准 OP.GG Server 做一次有界、body-free 的单向产品 smoke；外部 Client 调用
RiftCoach Server 以及两侧组合退出证明仍只在 7-5 执行。fixture 和单向 smoke 都不能
冒充双向互操作退出证据。

### 3. MetaEvidence 是唯一进入业务上下文的动态 Meta 形状

Meta Adapter 将外部工具结果规范化为有界、data-only 的 `MetaEvidence`，至少包括：

- `source`、server/tool identity；
- patch/version（未知时显式为 `null`）；
- `retrieved_at`、本地 `expires_at` 与上游 freshness 状态；
- canonical content digest；
- allowlisted normalized facts；
- safe error code（成功时为空）。

动态 Meta 不得覆盖玩家 subject、owner、Conversation、Preference、Profile、Plan、
Progress 或 RAG 原文；不得成为 system instruction，也不能直接写 Memory。它只能
作为带来源和明确 provenance 等级的外部证据，经过既有 Context trust/data-only 规则
进入 Skill 或 Harness。stale、schema invalid、digest mismatch、身份缺失或超出大小
上限时 fail closed；patch/freshness 缺失时只能产生受限 partial evidence，不能支持
精确 patch 或上游新鲜度声明。

### 4. OP.GG 的条件准入

OP.GG 准入分两层。官方 endpoint/server、标准 MCP protocol/version、transport、
`initialize`/`tools/list`/`tools/call` 和获准工具的固定输入合同属于“可连接/可调用”硬门；
缺失时整体 deferred。patch、source time、上游 TTL、稳定限流和底层数据条款属于“可支持
哪些声明”的 provenance 门；缺失时按 ADR-0048 只准入 partial evidence，而不是伪造字段
或整体拒绝。只有这些 provenance 合同也齐全时，才可升级为 complete provenance。
任何情况下都不得把普通 OP.GG HTTP 接口改名为 MCP。

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
- OP.GG 的连接能力和 provenance 等级可以分别裁决，不会静默替换或伪造完整来源。

### 负面

- 需要维护协议 envelope、transport/session 和 schema drift 合同；
- 双向互操作仍依赖外部 Server/Client、许可和部署条件，可能保持 deferred；
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
