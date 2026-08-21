# 7-5 MCP 双向互操作与 Stage 7 退出复盘

## 1. 问题与原理

7-3 已让 RiftCoach 作为 Client 调用 OP.GG，7-4 已让仓库内部 Client fixture 调用 RiftCoach Server，
但后者仍可能是“自己和自己说同一种方言”。7-5 引入官方 TypeScript MCP SDK 作为独立外部 Client，
让它跨进程调用 Python Server；这样版本协商、stdio framing、初始化通知、catalog 和 result schema 中的
共享误解会真实暴露。

Stage 7 的“双向”含义是两条职责相反的链都成立：

```text
RiftCoach Client -> OP.GG Server（远端 Streamable HTTP）
official SDK Client -> RiftCoach Server（本地跨进程 stdio）
```

stdio 不是“假的 MCP”。它是标准 transport，适合本地进程与桌面 Client；Streamable HTTP 适合远端
OP.GG。退出证明不需要为了看起来更“生产”而临时开放公网端口，把 Auth/TLS/部署变量混进协议验收。

## 2. 方案与实际实现

采用 ADR-0050 的官方 SDK 1.30.0/MIT，版本与完整 npm integrity 进入独立 lockfile。SDK 不在
`pyproject.toml` 或 runtime image 中，只由开发/CI 的 interoperability lane 安装。它提出最新协议
`2025-11-25`，RiftCoach 返回自己实际实现且 SDK 同样支持的 `2025-06-18`。

这次真实交叉验证发现，7-4 Server 原来把“Client 提议版本”误当成“必须完全相等的版本”：官方 SDK
因此会被拒绝。TDD 先确认红灯，再把 Server 改成只接受冻结 proposal allowlist
`{2025-06-18, 2025-11-25}`，响应和 session 永远绑定 `2025-06-18`。这既允许标准协商，也不会让未知
未来/过旧版本静默通过。

Python stdio adapter 每行只读一个有界 JSON-RPC object，拒绝非法 UTF-8、重复 key、非有限 JSON、
非 object、过大 request/response；notification 不写 response，EOF 总会关闭 session。runner 注入固定
test Actor 与 no-I/O Facade，外部 Client 只调用一次 `riftcoach.knowledge_search`。owner 仍由 Server 注入，
Client arguments 不能决定身份。

## 3. 代码地图

- `app/mcp/server.py`：冻结 proposal allowlist，响应绑定 Server protocol；
- `app/mcp/stdio.py`：标准 newline JSON-RPC framing、大小门、解析错误和 session close；
- `scripts/run_riftcoach_mcp_stdio_server.py`：真实 Server Session + no-I/O restricted Facade；
- `experiments/mcp_interop/external_client.mjs`：官方 SDK Client、trace wrapper、catalog/call digest；
- `experiments/mcp_interop/package*.json`：1.30.0 隔离依赖与 integrity/license graph；
- `scripts/run_mcp_interoperability_exit.py`：clean-SHA 双向门、body-free evidence validator/writer；
- `tests/test_mcp_interoperability_exit.py`：协议、framing、安全、lock 和官方 SDK subprocess；
- `data/evaluation/results/mcp/stage7_interoperability_exit_v1.json`：真实门通过后创建的不可覆盖摘要。

## 4. 数据流与控制流

外部 Client 方向：

```text
official Client.connect
 -> StdioClientTransport spawn(abs-python argv; no shell)
 -> Python serve_stdio
 -> McpServerSession.initialize returns 2025-06-18
 -> initialized notification (no response)
 -> tools/list four-tool fixed catalog
 -> tools/call knowledge_search
 -> trusted ActorContext + restricted Facade
 -> output-schema checked structured result
 -> external Client validates and keeps digest only
```

外部 Server 方向：

```text
clean-SHA exit runner
 -> existing StreamableHttpMcpTransport
 -> OP.GG initialize / initialized / selected tools-list
 -> one lane-meta tools-call, attempt=1
 -> strict AST + typed partial MetaEvidence
 -> digest/count/provenance/limits only
```

Node trace wrapper不保存 JSON-RPC id、arguments 或 response，只把事件降成
`direction/kind/method/status` 后求 digest。Python exit runner 再把两侧摘要合并并验证禁止字段。

## 5. TDD、验证与证据强度

首个红灯是 `ModuleNotFoundError: app.mcp.stdio`；随后官方 SDK 实测暴露 protocol proposal 问题。
实现后的聚焦集合为 `10 passed`，相邻 MCP/Meta 集合为 `74 passed, 17 subtests passed`，完整本地回归为
`1576 passed, 117 skipped, 1 warning, 127 subtests passed`。npm lock 审计
确认 direct SDK 1.30.0/integrity/MIT、94 个锁定 package、许可证仅 MIT/ISC/BSD-2/BSD-3、无 install
script；使用官方 npm registry 的 audit 为 0 vulnerability。

两套 RAG 满冻结阈值，Harness dry-run 为 `published`/0 revisions；compileall、pip、Node syntax、npm ci/audit、
6 YAML、governance、tracked Secret/run-data、body-free evidence 和 diff 门均通过。实现
`a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 随后完成 exact-SHA 三 job：公共
pytest `1577 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
`164 passed, 1 warning`，0001→0009 migration 可逆且 metadata=head；Linux package schema 1.6，
外部 Riot/Provider 调用为 0。

工作树、HEAD 与 `origin/main` 精确一致后，双向 runner 在 `2026-08-21T12:49:20Z–12:49:25Z`
唯一执行一次。官方 Client→RiftCoach 完成 initialize、initialized notification、tools/list 与一次
knowledge tools/call，目录为 4 个工具，proposal/negotiated protocol 分别为 `2025-11-25`/`2025-06-18`；
RiftCoach→OP.GG 同样各执行一次 initialize/notification/list/call，确认 Server
`OP.GG MCP Server/1.0.0`、protocol `2025-06-18`、1 个获准工具与 3 条规范化事实。最终 exit matrix 七项
全部 pass，Riot/LLM/Key I/O 为 0；OP.GG patch/source time/freshness 继续为 unknown，provenance 继续
为 partial。不可覆盖证据绑定上述 product SHA，且不含 owner、query、session、arguments 或正文。

不可覆盖 evidence 提交 `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736`
随后完成 exact-SHA 三 job：公共 pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`，
真实 PostgreSQL `164 passed, 1 warning` 且 migration/head 一致，Linux package schema 1.6/外部调用 0。
因此八维 coverage、7-5 与 Stage 7 正式关闭；Stage 8 只交接 entry-design 准备态，没有开始实现。

## 6. 安全运行手册

安装隔离依赖与运行本地跨进程门：

```powershell
npm ci --ignore-scripts --prefix experiments/mcp_interop
.\.venv\Scripts\python.exe -m pytest tests\test_mcp_interoperability_exit.py -q
```

单独查看外部 Client 的 body-free 摘要：

```powershell
node experiments/mcp_interop/external_client.mjs `
  --python D:\riftcoach-agent\.venv\Scripts\python.exe `
  --repo-root D:\riftcoach-agent
```

真实双向门只能在实现提交已通过公共 CI、工作树 clean、证据文件尚不存在时执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.run_mcp_interoperability_exit `
  --execute --expected-sha <IMPLEMENTATION_SHA> `
  --output data/evaluation/results/mcp/stage7_interoperability_exit_v1.json
```

脚本拒绝省略 `--execute`、SHA 不匹配、脏工作树、其他输出路径和覆盖已有 evidence。未知失败零重试，
只保存稳定 failure code。

## 7. 失败、安全与范围边界

- stdio stdout 只传协议 frame，任何日志都会破坏 Client 解析；Server runner 不写日志；
- subprocess 使用 argv 数组，不经过 shell；环境不继承应用 Key/Authorization；
- 外部 Client call 只有一次、只读、幂等，结果不含 owner、PUUID、报告/知识正文或内部异常；
- evidence 禁止 session、arguments、query、content/structuredContent、attribution body、路径和 Secret；
- OP.GG 仍是 partial provenance：patch/source time/upstream freshness/稳定限流/底层数据条款未知；
- 一次成功时间窗不是 SLO，不证明 OP.GG 永久在线或全部工具兼容；
- stdio 成功不证明公网 RiftCoach Server、正式 Auth/RSO、TLS、限流、SSE 或多租户部署；
- Riot 官方 patch/静态/比赛事实与 OP.GG 聚合 Meta 的 join 仍未实现；Stage 8 未进入。

## 8. 面试与简历准确表述

可以说：

> 我用锁版官方 MCP TypeScript SDK 作为独立 Client，通过标准 stdio 调用 Python RiftCoach MCP
> Server，并保留 RiftCoach Client 对 OP.GG Streamable HTTP 的真实方向。交叉验证修复了 client-proposed
> version 与 server-negotiated version 的混淆；两侧只持久化 identity、schema/result/trace digest 和调用
> 计数，owner 与正文不出边界。退出门绑定干净 SHA 和 exact-SHA CI。

不能说：

- “RiftCoach MCP Server 已部署公网并有正式认证”；
- “OP.GG 全部工具、精确 patch/freshness 和再分发条款都已准入”；
- “stdio 是模拟协议”或“fixture Facade 证明生产数据库已接通”；
- “一次互操作 smoke 就等于长期 SLA”；
- “Stage 7 已完成 Riot + OP.GG 数据融合”或“Stage 8 已开始”。
