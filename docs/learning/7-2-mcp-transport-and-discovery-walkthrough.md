# 7-2 MCP Transport / Discovery 学习与工程复盘

## 1. 问题与原理

7-1 只回答“一个 MCP 消息是否合法”：它校验 JSON-RPC envelope、protocol version、
tools capability、工具 schema、allowlist 和结果大小。7-2 回答“消息如何在一次会话
中可靠到达”：请求必须经过 initialize 才能 discovery，tools/list 目录要绑定服务端
identity 和 generation，tools/call 只能使用当前目录快照；超时、EOF、断线、畸形 frame
和服务端重启都必须 fail closed。

核心分层是：

```text
JSONL/in-memory transport -> McpClientSession -> 7-1 pure models
                                          -> ToolDefinition -> ToolRuntime
```

Transport 只负责有界消息收发；Session 负责生命周期、deadline、generation 和 discovery；
ToolRuntime 继续独占 retry、cache、circuit breaker、fallback 与 metrics。把这些层混成
一个 handler 会导致协议重试与业务重试重复、旧 schema 被静默复用，以及原始 frame 泄露。

## 2. 代码地图

- `app/mcp/transport.py`：`McpTransport` port、`InMemoryMcpTransport` fixture transport、
  `StdioMcpTransport` 隔离 JSONL subprocess transport；无 MCP method 解析和业务权限。
- `app/mcp/client.py`：`McpClientSession` 的 initialize/discover/call 状态机、分页目录合并、
  generation 失效和 `ToolDefinition` adapter；`McpClient` 是兼容别名。
- `app/mcp/models.py`：7-1 的 strict initialize/list/call/result envelope、schema digest 和
  body-free parser，7-2 直接复用而不重新实现。
- `app/mcp/errors.py`：新增 session/transport 的 allowlisted code 和安全消息；原始 frame、
  subprocess stderr 和远端 body 不会进入异常文本。
- `tests/test_mcp_transport.py`：fixture trace、能力 gate、分页、刷新后的 schema、断线/重启、
  deadline、ToolRuntime retry 接缝、stdio happy/malformed/timeout。
- `tests/fixtures/mcp_server_happy.json`：只包含可重复的本地 server identity、工具 schema 和
  deterministic result，不代表 OP.GG 或真实外部服务。

## 3. 数据与控制流

1. `initialize()` 生成 request id，向 transport 发送 JSON-RPC initialize；成功后保存
   protocol/server identity 和 transport generation。
2. `discover()` 先检查 initialized 与 tools capability，再发送 tools/list。分页 cursor 在同一
   总 deadline 内读取，所有 descriptor 合并成一个有界 `McpToolCatalog`，目录 digest 由
   protocol/server/tool schema identity 计算。
3. `call()` 先检查 generation、目录存在、工具 allowlist 和 arguments schema，再把 catalog/tool
   schema digest 绑定进 `McpToolCallRequest`，最后由 7-1 parser 解析响应。
4. `to_tool_definition()` 创建一个只调用 `session.call()` 一次的 handler。它不实现 retry/cache/
   breaker/fallback；这些由 `ToolRuntime.execute()` 根据 `ToolPolicy` 决定。
5. generation 改变时清空初始化与目录；旧 session 的 call 返回 `mcp_session_restarted`，必须
   重新 initialize/discover。disconnect、EOF、write failure、frame invalid 和 timeout 都只投影
   allowlisted error code。

## 4. 验证证据

- 11 项 7-2 聚焦测试覆盖 initialize → tools/list → tools/call 顺序、能力缺失、未 discovery、
  cursor 分页、schema refresh、断线、restart、deadline、Runtime retry 接缝以及 stdio
  happy/malformed/timeout。
- 7-1 合同与 7-2/ToolRuntime 相邻集合为 `43 passed, 17 subtests passed`；7-2 只使用本地
  fixture/subprocess，外部 OP.GG/Riot/Provider/Key 调用为 0。
- stdio 使用显式 argv、无 shell、stderr 丢弃、单请求串行和有界 JSONL frame；这证明隔离进程
  合同，不等于真实 MCP Server/Client 互操作。

## 5. 本地运行手册

```powershell
Set-Location D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_transport.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_contracts.py tests/test_mcp_transport.py tests/test_tool_runtime.py -q
python scripts/check_project_governance.py
```

真实 external endpoint、Key、OP.GG 网页/API 或普通 HTTP POST 不应被填入这些 fixture。
需要真实互操作时，必须等待 7-5 exit review 的独立 identity、许可、脱敏 trace 和 Key-last 门。

## 6. 失败、安全与范围边界

- 不兼容 protocol、缺 tools capability、未发现/未 allowlist 工具、schema drift、坏参数和坏结果：
  fail closed。
- deadline 是一次 session 操作的总预算；stdio timeout 会终止隔离进程，避免后台 reader 无限等待。
- 原始 JSON-RPC `message/data`、stdio frame、stderr、Prompt、Key、PUUID 和任意 URL/SQL/file
  都不进入安全异常；transport error 只保留 code、retryable、request id。
- 本批没有普通 HTTP/Streamable HTTP，因为仓库尚无对应标准版本与部署证据；没有安装 SDK，也不
  实现 MetaEvidence、OP.GG Adapter、RiftCoach MCP Server 或真实外部互操作。

## 7. 面试安全表述

“我把 MCP 的协议合同与 transport/session 分开：7-1 负责 strict envelope，7-2 用有界 in-memory
和隔离 stdio fixture 验证 initialize、discovery、deadline、断线与 generation 失效。发现的工具
只映射到现有 `ToolDefinition`，重试、缓存和熔断仍由 `ToolRuntime` 唯一负责。这个证据证明本地
transport 边界，不宣称已经接入 OP.GG，也不把普通 HTTP 或 fixture 当成真实 MCP 互操作。”
