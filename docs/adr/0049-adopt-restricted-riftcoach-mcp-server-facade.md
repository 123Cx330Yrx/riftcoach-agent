# ADR-0049：采用受限 RiftCoach MCP Server Facade

## 状态

Accepted（2026-08-21，RQ-078）。本 ADR 只覆盖 `7-4-riftcoach-mcp-server`；
真实 Streamable HTTP 部署、外部 Client 调用和双向互操作仍属于 7-5。

## 背景

7-1 至 7-3 已建立严格 MCP envelope、transport-neutral Client、OP.GG 单向 Adapter
和 partial `MetaEvidence`。下一步需要让外部 MCP Client 能发现 RiftCoach 的有限能力，
但不能把现有 FastAPI body、数据库、文件或内部运行时细节直接暴露出去。

现有 `ActorContext`、Application Service 和 Query Service 已经有 owner scope 与安全 DTO；
`ToolRuntime` 负责进程内工具的可靠性，不能被 MCP Server 重写一份。MCP Server 因此应是
一个协议适配器，而不是第二套业务服务或 Repository 网关。

## 决策

### 1. Server Session → Application Facade

每个 MCP 会话严格经过：

```text
initialize/version/capability
  -> tools/list 固定快照
  -> tools/call schema/allowlist 校验
  -> trusted ActorContext（服务端注入）
  -> read-only Application Facade
  -> allowlisted DTO / structuredContent
```

Server Session 只负责 JSON-RPC/MCP envelope、版本协商、初始化通知、工具目录、请求
ID、session 生命周期和固定错误投影。Facade 负责把工具名映射到既有 Application/Query
Service，并校验返回 DTO。它不拥有数据库事务、HTTP request body、Provider、Harness
发布或 Memory 写入。

### 2. 四个受限只读工具

目录固定为：

- `riftcoach.recent_summary`：从已验证 `PLAYER_SUMMARY` 投影近期胜负、胜率、主要位置/英雄、
  averages 与胜负对照，不返回玩家身份或 match rows；
- `riftcoach.single_match_review`：查询正确 Skill 的已发布单局分析身份、终态与 final Artifact
  digest，不返回 Markdown 正文；
- `riftcoach.knowledge_search`：调用注入的 provider-neutral knowledge facade；
- `riftcoach.report_evaluation`：查询已验证报告的评测/发布摘要；当前不冒充持久化分数。

客户端不能传 `owner_id`、PUUID、Key、Prompt、Provider/Tool body、文件路径、SQL、URL
或任意内部字段。run identity 只允许 bounded safe ID；服务端从 ActorContext 注入 owner，
不信任客户端自报身份。

### 3. 输出与错误

成功结果使用严格 `structuredContent`，只包含版本化、body-free DTO；content 仅为固定短文，
不回显报告、远端正文或内部异常。Facade 的未知/完整性/未发布/owner scope 失败统一投影
为 allowlisted `isError=true` MCP result，错误只含稳定 code，不含异常文本、路径、SQL、
PUUID、Authorization 或 Provider response。

### 4. 传输边界

本检查点提供 transport-neutral `McpServerSession`，可被 fixture/in-memory client 调用。
不在 7-4 增加普通 HTTP、公开监听端口或 MCP SDK；7-5 再以真实外部 Client/Server、
协议版本、transport、部署和许可证据决定是否做 Streamable HTTP 互操作。

## 备选方案

1. **直接复用 FastAPI route**：会把 HTTP body、状态码和认证细节耦合进 MCP，拒绝。
2. **Server 直连 Repository**：绕过 Application Service、owner scope 和 DTO 合同，拒绝。
3. **暴露通用 `run_sql`/`fetch_url`/原始报告工具**：权限和数据泄露面不可接受，拒绝。
4. **协议 Server + restricted Facade（本 ADR）**：复用现有服务与安全边界，fixture 先可证，
   真实 transport 延后到独立退出门，采用。

## 后果与限制

正面结果是外部 Client 有稳定的标准工具目录，同时业务权限仍由服务端 ActorContext 和
Application Service 控制。代价是每个新增能力都要定义独立 DTO/schema/错误映射；7-4 不证明
公网 TLS、正式 Auth/RSO、真实 Provider、真实 OP.GG 或双向互操作。工具返回的是摘要和证据
引用，不是任意报告正文或内部 Artifact body。现有持久合同没有单独保存结构化 target-match
review 摘要，因此 V1 不解析 Markdown 反推 target/narrative，也不虚构 evaluator score。

## 验证

- strict initialize、协商版本、`notifications/initialized`、tools/list 快照和 call ID；
- 四个工具的 input/output schema、未知工具、schema drift、非法参数、超限和 method 边界；
- owner isolation、actor missing、未发布/完整性失败和安全错误无 body；
- fixture client 通过 `McpClientSession` 调用 Server Session；无网络、Key、Provider 或 Repository 直连；
- 完整 pytest、RAG、Harness、compile/governance/security gates 与 exact-SHA 三 job。
