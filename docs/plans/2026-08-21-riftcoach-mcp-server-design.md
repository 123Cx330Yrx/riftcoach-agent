# 7-4 RiftCoach MCP Server 设计

## 1. 初学者要解决的问题

内部 Python 函数能被 RiftCoach 自己调用，不等于另一个 MCP Client 知道如何初始化、发现
工具、传参数和处理错误。Server 是“把能力以标准协议说出来”的边界；Application Facade
则是“决定这些能力到底能做什么”的业务边界。7-4 组合两者，但不把协议层变成数据库或
Agent Runtime。

本检查点的最小成功标准是：一个 fixture Client 完成 initialize → tools/list → tools/call，
四个只读工具都能经过 schema 和 owner scope；恶意字段、错误身份、内部异常和未发布报告
都 fail closed。真实外部 Client 和网络 transport 不在本检查点。

## 2. 方案与取舍

方案 A 是直接把 FastAPI route 包成 MCP：实现快，但会暴露 HTTP request/owner 语义并复制
错误映射。方案 B 是 Server 直连 Repository：看似少一层，但绕过 owner-scoped service、
生命周期和产品 DTO。方案 C（采用）是 strict MCP Session + `McpApplicationFacade` port，
由既有 Query/Application Service 提供数据；它多一个显式适配层，却使协议、业务和安全
可以分别测试，并为 7-5 复用同一 session contract。

## 3. 组件地图

- `app/mcp/server.py`：Server implementation、session state、固定 catalog、input validation、
  tool dispatch、safe result/error projection；
- `app/api/actor.py`：可信 ActorContext provider，绝不从 MCP arguments 读取 owner；
- `app/product/run_query.py` 与 `app/api/composition.py`：receipt/Trace/manifest/Artifact 交叉验证、
  安全业务 DTO 与既有 Application 接缝，Server 只能通过 Facade port 使用；
- `app/tools/adapters/knowledge.py`：provider-neutral knowledge contract，Server 不接受 URL/path；
- `tests/test_mcp_server.py`：fixture client、Fake Facade、owner isolation、协议和安全负例。

## 4. 数据与控制流

```text
fixture/external MCP client
  -> McpServerSession.initialize
  -> negotiated protocol + tools capability
  -> tools/list fixed catalog/digest
  -> tools/call(name, arguments)
  -> McpToolCallRequest schema/size/allowlist
  -> ActorContextProvider()
  -> McpApplicationFacade method
  -> typed body-free projection
  -> structuredContent + fixed content marker
```

Server 的每次调用都使用当前 session 的 catalog digest；初始化前、未知 method、未知工具、
schema drift、actor 缺失、facade 返回错误或结果超限都会返回固定安全错误。成功结果不携带
owner_id、PUUID、报告 Markdown、Prompt、Provider/Tool body 或内部异常。

## 5. 工具合同

四个工具均使用 bounded object arguments，并额外拒绝未知字段：

| 工具 | 输入 | 输出摘要 |
|---|---|---|
| `riftcoach.recent_summary` | `run_id` | verified run/Skill/publication + games/wins/losses/win rate/main role/champions/bounded averages/comparison |
| `riftcoach.single_match_review` | `run_id` | verified single-match Skill/publication + `review_available`/final report SHA-256；无正文 |
| `riftcoach.knowledge_search` | `query`, `top_k`, optional safe `filters` | provider/abstained/count/attribution refs |
| `riftcoach.report_evaluation` | `run_id` | run/publication/evaluation status；`score_available=false` |

run_id 由既有 normalizer 验证；输出 schema 是严格 `additionalProperties: false` 的版本化
DTO。近期汇总必须验证 receipt、Trace、manifest、Execution input commitment 与
`inputs/player_summary.json` 的 path/producer/schema/SHA；玩家 Riot ID、PUUID 和 match rows 不进入
DTO。当前 Query seam 能证明 Harness 的 publication/evaluation 裁决，但不持久化独立分数，
因此明确返回 `score_available=false`，不虚构 score band。Facade 可以返回更丰富的内部对象，
但 Server 只复制 allowlisted 字段；任何类型或大小不符都转为安全工具错误。

## 6. 测试策略

1. 先写 fixture client 红灯，确认 `app.mcp.server` 尚不存在或 dispatch 未实现；
2. pure session：initialize/version/capability/notification/list/call/idempotent close；
3. schema/security：未知字段、owner_id/PUUID/Key/Prompt/URL/SQL/path、oversized、未知 tool、
   malformed envelope、未初始化和错误 facade；
4. integration seam：Fake Facade 记录 actor 与调用参数，证明 owner 由 provider 注入且四工具不写入；
5. 相邻 7-1/7-2/7-3 回归和完整项目门禁；本批外部调用、Key、Provider、Repository I/O 均为 0。

## 7. 限制与后续

7-4 的 fixture Client 不是公网部署证明，不证明 OP.GG/Riot join、正式 Auth/RSO、TLS、限流、
SSE/Streamable HTTP 或双向互操作。7-5 才固定真实 Client/Server identity、transport、时间窗口，
并保存 body-free immutable evidence；若真实门失败，必须以 deferred/partial 结论收尾。单局 V1
只给出已发布分析身份与 digest；在未来有结构化 published-result Artifact 前，不解析 Markdown
反向猜 target、narrative 或 evaluator score。
