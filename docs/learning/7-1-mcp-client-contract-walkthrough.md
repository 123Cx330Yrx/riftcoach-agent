# 7-1 MCP Client Pure Contract Walkthrough

## 1. 这一步解决什么问题

RiftCoach 以前只有进程内 `ToolRuntime`：代码已经知道有哪些 Python handler，也能对它们做超时、重试、
缓存、熔断和 fallback。但外部 MCP Server 发来的消息仍然只是“不可信 JSON”。如果没有协议合同，程序会面临：

- 不知道双方使用的 protocol version 是否兼容；
- 服务端没有声明 tools capability，却仍被调用；
- 同名工具、坏 JSON Schema 或过大目录进入运行时；
- 工具发现后 schema 已变化，旧参数仍被发送；
- 远端错误把 Prompt、Key、URL、body 或内部异常带进日志和 Trace。

7-1 把这些 JSON 变成严格、不可变、有大小上限的 pure Python contracts。它没有联网；它只回答
“一条已经到达内存的 MCP 消息是否合法”。

## 2. 核心原理：协议 envelope 不等于 transport

可以把它们类比成“信件格式”和“快递公司”：

- **protocol/envelope** 规定信封上必须有什么：JSON-RPC `2.0`、request id、method、params/result/error，
  以及 MCP 的 version、capability、tool schema；
- **transport/session** 规定信如何到达：stdio、HTTP、进程生命周期、断线、deadline、restart。

7-1 只实现第一层。7-2 才会实现 transport/discovery。这样 malformed message 不会被误报成网络错误，
断线也不会被错误地塞进 schema validator；协议与传输可以分别测试、替换和审计。

## 3. 本轮实现与明确不实现

### 已实现的 pure contract

1. `initialize` request 和 result 的严格 JSON-RPC envelope；
2. 显式 protocol version allowlist 与 tools capability gate；
3. `tools/list` 的唯一名称、合法 Draft 2020-12 object schema、标准 annotations、数量/字节上限；
4. server/protocol/tool schema 的 immutable snapshot 和 SHA-256 digest；
5. `tools/call` 的 discovered + allowlisted + arguments schema + argument size 四道门；
6. 调用前 current catalog/schema drift 检查；
7. `tools/call` content/structured result 的形状、output schema、数量和 canonical byte 上限；
8. JSON-RPC error 与 `isError` 的 body-free 安全投影。

### 本轮没有实现

- stdio、HTTP、Streamable HTTP、SSE 或 subprocess transport；
- session lifecycle、disconnect、timeout、restart、分页聚合或动态刷新；
- MCP SDK 安装或 SDK adapter；
- OP.GG endpoint、Meta Adapter、`MetaEvidence`；
- RiftCoach MCP Server；
- 任何 Key 读取、Riot/Provider/OP.GG 调用或真实外部互操作。

因此，7-1 完成后只能说“pure MCP 协议合同已实现并测试”，不能说“已经接入 OP.GG”或“Stage 7 已完成”。

## 4. 代码地图

| 文件 | 职责 | 不负责 |
|---|---|---|
| `app/mcp/errors.py` | 安全错误码、retryable、request id、整数 remote code；异常只显示 allowlisted message | 不保存 remote message/data/raw body |
| `app/mcp/models.py` | initialize/list/call/result、严格字段、immutable JSON、Schema/digest/limit | 不收发字节，不做 retry/cache/breaker |
| `app/mcp/__init__.py` | 导出 7-1 稳定 pure contract surface | 不创建 Client 或 transport |
| `tests/test_mcp_contracts.py` | 正例、坏 envelope、版本/能力、目录/Schema、drift、大小和安全错误 TDD | 不冒充外部 Server 互操作 |
| `app/tools/*` | 既有内部可靠执行层，后续接收 MCP Adapter 产生的 ToolDefinition | 不解析 MCP envelope |

`app/mcp` 不导入 OP.GG、Riot、Provider、FastAPI、SQLAlchemy 或网络库，说明该边界保持 pure。

## 5. 数据流与控制流

```text
local client identity + proposed version
        │
        ▼
McpInitializeRequest.to_wire()
        │  （7-2 才负责发送）
        ▼
initialize response mapping
        │ exact JSON-RPC id/result
        │ protocol version allowlist
        │ serverInfo + tools capability
        ▼
McpInitializeResult.require_tools()
        │
        ▼
tools/list response mapping
        │ count + canonical bytes
        │ unique names + object JSON Schema
        │ immutable schema snapshot + digest
        ▼
McpToolCatalog
        │ discovered?
        │ allowlisted?
        │ arguments schema + bytes?
        ▼
McpToolCallRequest
        │ current catalog/digest still equal?
        ▼
tools/call response mapping
        │ request id + bytes + result shape
        │ output schema
        ├── success ──► immutable bounded content/structuredContent
        ├── isError ──► safe `mcp_tool_error`, discard content
        └── JSON-RPC error ──► safe `mcp_remote_error`, discard message/data
```

这里的顺序很重要：没有 initialize/tools capability 就不能发现；没有发现快照就不能调用；没有 allowlist 和
arguments schema 就不能构造 call；schema 漂移后不能沿用旧请求。

## 6. 关键设计细节

### 6.1 immutable snapshot

外部 dict/list 会递归复制为 `MappingProxyType`/tuple。调用方后来修改原始 dict，不会改变已批准的 schema；
需要发到 wire 时再生成新 mutable copy。tool schema digest 绑定 input/output schema，catalog digest 还绑定
protocol version、server identity 和整页工具身份。

### 6.2 大小边界

`McpContractLimits` 默认限制 tool count、catalog/schema/argument/result canonical bytes、content items、cursor
和 description。pure contract 只能测内存对象的 canonical JSON 大小；transport 收到的原始 frame/body byte
上限仍属于 7-2，不能把本轮限制冒充网络层 DoS 防护已经完整。

### 6.3 strict bool/int

Python 中 `bool` 是 `int` 的子类，但 JSON 中 boolean 和 integer 是不同类型。因此 request id、远端 error code
和所有整数 limits 都显式拒绝 `True/False`；`listChanged`、`isError` 和 annotation hints 又必须是真正 boolean。

### 6.4 body-free error

远端 `error.message`、`error.data` 和 `isError` content 都是不可信正文。7-1 会验证它们的 envelope/JSON 形状，
但内部异常/失败结果只保留有限字段：

```text
code + retryable + local request_id + optional integer remote_code
```

错误对象没有 raw body/message/data 构造参数，`str(error)` 只来自本地 allowlist；`repr` 不包含 tool content、
structured content、arguments、description 或 server instructions。

## 7. 需求到测试的证据矩阵

| 要求 | 主要测试 | 当前证明 | 仍不证明 |
|---|---|---|---|
| initialize/version | initialize request/result、unsupported version、strict envelope | 只有 allowlisted YYYY-MM-DD version 可进入 | 真实 server 支持哪个版本 |
| capability | missing tools capability | discovery 前 fail closed | transport session 已初始化 |
| tools/list | immutable/unique/schema/count/bytes/annotations | 有界合法目录快照 | 跨页聚合与 listChanged refresh |
| tools/call | discovery/allowlist/args/argument bytes | 越权或坏参数不形成 wire call | 网络 deadline/retry |
| drift | changed catalog/schema | 旧请求在 I/O 前失败 | server restart 检测 |
| result | shape/output schema/content count/bytes | malformed/oversized/typed mismatch fail closed | 外部内容可直接进入 Context |
| safe error | JSON-RPC error、`isError`、bool/int、extra fields | remote正文不进入异常/结果 repr | transport/logging 全链路脱敏 |

聚焦命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_contracts.py -q
```

相邻合同命令：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_mcp_contracts.py `
  tests/test_tool_contracts.py `
  tests/test_tool_registry.py `
  tests/test_provider_contracts.py `
  tests/test_provider_tool_calling_models.py -q
```

本地聚焦为 `20 passed, 17 subtests passed`，相邻为 `55 passed, 62 subtests passed`，完整回归为
`1509 passed, 117 skipped, 1 warning, 127 subtests passed`。两套 RAG、Harness、compile、pip、YAML、治理、
SDK/Secret/tracked-data 与 diff 门也通过。实现 `37f16bc` / Actions `32439753589` 的三个公共 job 全绿；
公共 pytest `1510 passed/116 skipped/127 subtests`、真实 PostgreSQL `164 passed`、package schema 1.6 且外部
调用 0。coverage 已 complete；这些证据仍不外推为 transport 或真实 MCP 互操作。

## 8. 安全运行与排障

1. 先确认当前 checkpoint 是 `7-1-mcp-client-contract`；
2. 不配置或读取任何 OP.GG/Riot/Provider Key；
3. 只运行 pure tests，不启动 server、subprocess 或端口；
4. 失败时先看 safe `info.code`，不要为了排障把 raw remote message/body 加回异常；
5. schema drift 应重新 discovery 并重新走 allowlist，而不是跳过 digest；
6. 若真实标准字段不在 V1 allowlist，保留 fixture/版本证据，在 7-2 评估兼容扩展，不能用任意 extra-fields
   放开代替标准审计。

常见安全错误码包括 `mcp_protocol_version_unsupported`、`mcp_tools_capability_missing`、
`mcp_tool_catalog_invalid`、`mcp_tool_not_allowed`、`mcp_tool_arguments_invalid`、
`mcp_tool_schema_drift`、`mcp_result_invalid`、`mcp_result_too_large` 与 `mcp_remote_error`。

## 9. 面试安全表述

可以说：

> 我先把 MCP 的协议合同和 transport 分层。7-1 用 pure dataclass + Draft 2020-12 Schema 建立
> initialize/version/capability、tool catalog snapshot、allowlisted call、schema drift 和 bounded result，
> 并把远端 message/data/body 投影为有限安全错误。这样后续换 stdio、HTTP 或 SDK 时，业务层和既有
> ToolRuntime 不依赖传输实现。

不可以说：

- “已经接入 OP.GG MCP Server”；
- “已经完成 stdio/HTTP session 和断线恢复”；
- “fixture/pure tests 证明了真实 MCP 互操作”；
- “MCP SDK 已采用”或“RiftCoach 已对外提供 MCP Server”；
- “所有外部 Meta 都可以安全进入 Prompt/Memory”。

更诚实的限制是：7-1 只建立协议防火墙。transport/discovery、OP.GG 准入、MetaEvidence、对外 Server 和双方
真实互操作仍要按 7-2 到 7-5 独立完成。
