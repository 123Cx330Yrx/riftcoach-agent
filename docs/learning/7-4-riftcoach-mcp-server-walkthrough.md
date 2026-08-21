# 7-4 RiftCoach MCP Server 实现后讲解

## 1. 问题与原理

RiftCoach 内部已经有 Tool、Application Service 和 Query Service，但外部 MCP Client 不认识
Python 对象，也不应该获得数据库、文件或 HTTP body。7-4 解决的是“怎样把少量已审核能力用
标准 MCP 说出去”，不是再造一套业务后端。

核心原则是协议 Adapter 与 Application Facade 分层：Server Session 只判断消息是否合法、
会话是否初始化、工具是否存在、参数和结果是否满足 schema；Facade 再用服务端可信
`ActorContext` 做 owner scope，并调用已有只读 Query/Application Service。MCP arguments 永远
不能决定 owner，也不能携带 PUUID、Key、Prompt、URL、SQL 或文件路径。

## 2. 设计与实际实现

Server 固定暴露四个只读、幂等、closed-world 工具：

- `riftcoach.recent_summary`：只对 `recent-form-review` 的已发布/降级 run 返回 games、胜负、
  胜率、主要位置/英雄、有界 averages 和胜负对照；不返回玩家身份或 match rows；
- `riftcoach.single_match_review`：只对 `single-match-review` 的已发布/降级 run 返回 Skill
  identity、终态和 final report SHA-256，不返回 Markdown 正文，也不从正文猜 target/分数；
- `riftcoach.knowledge_search`：只返回 attribution，知识正文留在服务端；
- `riftcoach.report_evaluation`：返回 Harness publication/evaluation 终态，并明确
  `score_available=false`，不把 published 虚构成持久化 evaluator score。

`RunQueryService.get_recent_summary()` 会交叉验证 receipt、Runtime Trace、manifest、
`ExecutionValidatedSignal` 的第一个 input digest、`PLAYER_SUMMARY` path/producer/schema 和文件
SHA，再把 `recent_summary` 投影成严格 DTO。`get_single_match_review()` 校验正确 Skill、发布状态
和 final Artifact digest。MCP Server 不导入 Repository，也不直接打开 Artifact。

## 3. 代码地图

- `app/product/run_query.py`：`RecentSummaryView`、`SingleMatchReviewView` 和跨存储完整性校验；
- `app/mcp/server.py`：固定 catalog、Server Session、schema、safe projector、Facade 与 in-process
  transport；
- `app/mcp/__init__.py`：公开 Server 合同；
- `tests/test_run_query_service.py`：Artifact/Trace/manifest/Skill/publication 投影红绿测试；
- `tests/test_mcp_server.py`：真实 `McpClientSession` fixture、协议生命周期、owner、schema、大小和
  body-free 负例。

## 4. 数据与控制流

```text
MCP Client
  -> initialize 2025-06-18
  -> notifications/initialized
  -> tools/list fixed snapshot
  -> tools/call strict arguments
  -> server-side ActorContext
  -> QueryMcpApplicationFacade owner gate
  -> RunQueryService / knowledge provider
  -> allowlisted safe DTO
  -> output JSON Schema + result byte gate
  -> structuredContent + fixed text marker
```

近期汇总的文件数据流是：receipt 定位可信 run → Trace/manifest 对齐 terminal 和 Artifact
identity → 文件 SHA 校验 → Summary Schema 1.0 → bounded DTO。任何一层漂移都会变成稳定的
`integrity_failed` 工具错误；原异常、路径和内容不会进入 MCP result。

## 5. 验证证据

- `tests/test_run_query_service.py`：正确 Skill、published/degraded、rejected、input commitment、
  manifest identity 和文件 digest 漂移；
- `tests/test_mcp_server.py`：initialize/initialized、固定目录、四工具、owner 注入、非法身份字段、
  未初始化/关闭/重启、错误 body safety、知识 attribution、输出 schema 和 result budget；
- `tests/test_mcp_contracts.py`、`tests/test_mcp_transport.py`：7-1/7-2 envelope、catalog snapshot 和
  Client session 回归；
- `tests/test_mcp_streamable_http.py`、`tests/test_opgg_meta_adapter.py`：7-3 transport/Meta 邻接回归。

TDD 先在缺少 `app.mcp.server` 的 collection error 和缺少 Product Query 方法的六个
`AttributeError` 上确认红灯。当前聚焦 `33 passed`，MCP/Product 相邻集合
`109 passed, 17 subtests passed`；完整本地回归为
`1566 passed, 117 skipped, 1 warning, 127 subtests passed`，横向本地门禁全绿。实现
`431c584` / Actions `32480827952` 的 exact-SHA 三 job 随后全部成功：公共 pytest
`1567 passed, 116 skipped, 1 warning, 127 subtests passed`，真实 PostgreSQL `164 passed`，
Linux package schema 1.6/外部调用 0；coverage 已置 `complete`。

## 6. 运行手册

聚焦与相邻验证：

```powershell
.venv\Scripts\python.exe -m pytest tests\test_mcp_server.py tests\test_run_query_service.py -q
.venv\Scripts\python.exe -m pytest tests\test_mcp_server.py tests\test_run_query_service.py tests\test_mcp_contracts.py tests\test_mcp_transport.py tests\test_mcp_streamable_http.py tests\test_opgg_meta_adapter.py -q
```

7-4 没有监听端口，也没有真实外部 I/O。fixture Client 使用 `McpServerTransport` 调用独立
`McpServerSession`；`restart()` 会关闭旧 Session、增加 generation，Client 必须重新 initialize
和 discover。

## 7. 失败、安全与范围边界

- `owner_id` 只来自 `ActorContextProvider`；客户端自报 identity 被 schema 拒绝；
- owner 不匹配在 Query 前失败，外部只看到 not-found 语义；
- rejected/unpublished、Skill identity mismatch、Trace/manifest/file drift 均 fail closed；
- 玩家 Riot ID、PUUID、match rows、报告/知识正文、Prompt、Provider/Tool body、路径和 SQL 不输出；
- result 先过 output schema，再过 byte limit；Facade 的额外内部字段不会被复制；
- 单局 V1 只输出已发布分析的身份与 digest。现有持久合同没有结构化保存 target-match review
  摘要，故不能安全返回 narrative、target 或 evaluator score；解析 Markdown 反推会伪造合同；
- 本检查点不增加 MCP SDK、普通 HTTP/Streamable HTTP Server、TLS、正式 Auth/RSO、限流、
  外部 Client、Riot+OP.GG join、Provider 调用或 Memory 写入；这些不能由 fixture 绿灯外推。

## 8. 面试表述

准确说法：

> 我实现了一个 transport-neutral 的受限 MCP Server。协议层负责 initialize、工具目录、schema、
> lifecycle 和大小门，业务层通过服务端 ActorContext 与 Application Facade 做 owner-scoped
> 只读查询。近期汇总来自 receipt、Trace、manifest 和 Artifact SHA 的交叉验证；单局与评测
> 不返回正文或虚构分数。所有错误都做 body-free allowlist 投影，并用真实 MCP Client fixture
> 验证。

不能说：

- “已经部署公网 MCP Server”；
- “已经完成真实外部 Client 双向互操作”；
- “单局工具会返回完整报告正文或 target-match narrative”；
- “published 就等于有持久化 evaluator score”；
- “7-4 证明 Riot 与 OP.GG 已合并，或正式 Auth/TLS/限流已经完成”。
