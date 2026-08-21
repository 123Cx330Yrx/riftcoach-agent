# ADR-0050：采用锁版官方 MCP Client + stdio 完成 Stage 7 互操作退出证明

## 状态

Accepted for `7-5-mcp-interoperability-exit-review`（2026-08-21，RQ-079）。本 ADR
授权一个隔离的外部 Client 评测依赖和标准 stdio Server runner；它不等于公网部署、正式
Auth/TLS、生产 Actor bootstrap 或把 TypeScript SDK 加入 Python 产品运行依赖。

## 初学者解释

7-4 已证明“RiftCoach 自己写的 Client 能调用自己写的 Server”，但同一套代码可能在消息格式、
初始化顺序或版本处理上犯相同错误。真正的互操作需要一个独立实现来交叉验证。这里选择 MCP
项目官方 TypeScript SDK 作为外部 Client，让它启动 Python RiftCoach Server，并严格走
`initialize → notifications/initialized → tools/list → tools/call`。如果两边对协议的理解不同，
它们会在真实进程边界上失败，而不是被共享测试 helper 掩盖。

另一方面，RiftCoach 调用外部 Server 的方向已经由 7-3 产品化：Python Client 通过官方
Streamable HTTP endpoint 调用 OP.GG。7-5 会在干净实现 SHA 上再做一次有界、零重试、
body-free 调用，与外部 Client→RiftCoach 的 stdio 证明合并成双向退出证据。

## 审计身份

### 外部 Client

- npm package：`@modelcontextprotocol/sdk`；
- 固定版本：`1.30.0`，不使用浮动 semver；
- npm integrity：
  `sha512-xKd8OIzlqNzcqcNumGAa6g+PW2kjD5vrpcKOnfldAUPP3j7lnqMPwlTXQm8gF+UwH72z0lqaRbjr9hqGz0eITA==`；
- repository：`https://github.com/modelcontextprotocol/typescript-sdk`；
- package license：MIT，tarball 内许可证为 2024 Anthropic, PBC；
- Node contract：package 要求 `>=18`，本项目 CI 固定 Node 24；
- SDK 支持版本包含 `2025-06-18`，1.30.0 的最新提议版本为 `2025-11-25`；
- transport：官方 `StdioClientTransport`，newline-delimited JSON-RPC，无 shell。

SDK 与完整 lockfile 位于 `experiments/mcp_interop/`，CI 使用 `npm ci --ignore-scripts`。
它不进入 `pyproject.toml`、Docker runtime image、Application Service 或业务领域模型。

### 外部 Server

- repository：`https://github.com/opgginc/opgg-mcp`；
- 已审计 repository head：`039904bf655927402c28717c12bb51fe949e2d61`；
- endpoint：`https://mcp-api.op.gg/mcp`；
- server identity：`OP.GG MCP Server / 1.0.0`；
- protocol/transport：`2025-06-18` / HTTPS Streamable HTTP；
- 获准工具：只读 `lol_list_lane_meta_champions`；
- 准入仍为 ADR-0048 的 `admitted_with_restrictions`，不升级 patch/freshness/数据条款声明。

## 决策

### 1. 外部 Client 使用官方 SDK，经 stdio 调用真实 RiftCoach Server Session

新增 Python stdio adapter，只负责有限 JSON frame、每行一条消息、response flush 和 EOF/关闭；
所有 initialize、catalog、schema、owner scope、Facade dispatch 与安全错误仍由
`RiftCoachMcpServer` / `McpServerSession` 负责。runner 注入固定 test Actor 与 no-I/O restricted
Facade，只调用 `riftcoach.knowledge_search` 一次。测试身份不会进入证据，客户端不能传 owner。

这证明的是跨语言协议、Server catalog/schema、安全投影和标准生命周期；它不声称生产数据库、
真实知识 Provider、正式登录或公网可达已经部署。

### 2. 修正协议协商，而不是锁死 Client 的首选版本

官方 Client 1.30.0 初始化会提出 `2025-11-25`；RiftCoach Server 当前实现版本为
`2025-06-18`。按 MCP 协商语义，Server 可返回自己支持的版本，Client 若支持则继续，否则必须
断开。因此 Server 接受锁定 allowlist 中的 `2025-06-18`/`2025-11-25` client proposal，但响应固定为
`MCP_SERVER_PROTOCOL_VERSION = 2025-06-18`。后续所有 session 状态与证据均绑定响应版本。

Server 不因此宣称实现 2025-11-25，也不接受任意版本完成会话：未知/过旧 proposal 仍拒绝，
真正的决定权由外部 Client 的 supported-version check 保留。RiftCoach 内部 Client 仍只接受显式
allowlist 中的响应版本。

### 3. body-free trace 是退出证据，不保存协议正文

外部 Client transport wrapper 只观察：方向、request/notification/result 类型、method、成功/失败，
不保存 id、arguments、catalog body 或 tool result。证据只保留：

- product SHA、观察时间窗、package/version/integrity/license；
- offered/negotiated protocol、server identity、transport；
- tool count、catalog digest、selected tool 与 schema/result digest；
- initialize/list/call/notification 次数和 trace digest；
- OP.GG partial provenance 摘要、调用次数与既有限制；
- exit matrix 的 pass/fail 和安全限制。

session ID、raw JSON-RPC、description/content/structuredContent、query、attribution、玩家身份、Key、
Authorization、路径和异常正文不得持久化。真实失败也只写稳定 failure code，并立即停止，不对未知
失败重试。

### 4. 真实门必须绑定干净实现 SHA

实现与离线测试先提交并通过 exact-SHA 三 job。随后 exit runner 要求工作树 clean、当前 HEAD 与
`--expected-sha` 一致、目标证据不存在；先执行外部 SDK→RiftCoach，再执行一次
RiftCoach→OP.GG。结果不可覆盖。只有两侧通过、八维 coverage、本地门禁和证据提交本身的
exact-SHA 三 job 全绿后，才允许 Stage 7 关闭。

## 备选方案

### A. 继续用仓库自己的 Python Client 调用 Server

拒绝作为退出证明：适合回归，但 Client/Server 可能共享同一错误假设，独立性不足。

### B. 部署公网 Streamable HTTP，再用 Inspector/外部 Client

本阶段拒绝：会同时引入公网监听、正式 Auth、TLS、部署、限流和运维变量，无法把协议互操作与
部署成熟度分开；Stage 7 最小退出门不需要这些扩权。

### C. 官方 SDK Client + 本地 stdio（采用）

采用：标准 transport、跨语言/跨进程、官方独立解析器、无公网权限扩张；代价是增加一个隔离
lockfile、CI npm install 与小型 stdio adapter。

## 失败、安全与限制

- frame 过大、非法 UTF-8/JSON、非 object、重复 key、Server response 过大均安全失败；
- stdout 只允许 JSON-RPC，外部 Client summary 由父进程单独捕获；Server stderr 非空即失败且不回显；
- Client/runner 使用 argv 数组，不经过 shell；环境只传 Python 启动所需最小变量，不传应用 Secret；
- 只有一个 read-only/idempotent tool call；无 Riot、LLM Provider、数据库、文件或 Memory 写入；
- OP.GG 调用仍只有 partial provenance，不证明精确 patch、上游 freshness、长期稳定或商业再分发条款；
- stdio 互操作不证明公网可达、正式多租户认证、TLS、SSE 或生产会话运维。

## 参考

- ADR-0047、ADR-0048、ADR-0049
- `docs/plans/2026-08-21-stage7-mcp-interoperability-exit-review.md`
- `app/mcp/server.py`, `app/mcp/transport.py`
- `data/evaluation/results/mcp/opgg_meta_admission_v1.json`
