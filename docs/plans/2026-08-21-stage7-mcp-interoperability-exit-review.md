# 7-5 MCP Interoperability Exit Review 设计与实施计划

## 1. 目标与不变量

本检查点用两个独立方向完成 Stage 7 的真实互操作退出证明：

```text
RiftCoach Python Client
  -> OP.GG official Streamable HTTP Server
  -> initialize / initialized / tools-list / one lane-meta tools-call

official TypeScript MCP SDK Client 1.30.0
  -> standard stdio process boundary
  -> Python RiftCoach MCP Server Session
  -> one restricted knowledge-search tools-call
```

两侧都必须是真协议实现，不能用 fixture 冒充；同时不能借退出审查扩张到公网部署、正式 Auth/TLS、
真实 Riot/LLM Provider、数据库、Memory 写入或 Stage 8。原始 body 永不落盘。

## 2. 为什么这样组合

“双向”不是让同一个进程来回调用两次，而是 RiftCoach 同时扮演标准 MCP Client 和 Server：作为
Client，它能使用外部 OP.GG；作为 Server，它能被一个独立官方 Client 发现和调用。OP.GG 最适合
HTTPS Streamable HTTP，因为它本来就是远端服务；RiftCoach 的退出证明最适合 stdio，因为它能验证
跨进程 wire contract，又不会把公网认证/部署混入协议验收。

## 3. 组件与文件

- `app/mcp/stdio.py`：有界 newline JSON-RPC Server transport adapter；
- `scripts/run_riftcoach_mcp_stdio_server.py`：test Actor + no-I/O restricted Facade composition；
- `experiments/mcp_interop/external_client.mjs`：官方 SDK Client、body-free trace wrapper；
- `experiments/mcp_interop/package.json` / `package-lock.json`：隔离锁版依赖；
- `scripts/run_mcp_interoperability_exit.py`：clean-SHA 双向真实门与 immutable result writer；
- `tests/test_mcp_interoperability_exit.py`：协议协商、stdio、安全、真实外部 SDK no-I/O 和 evidence contract；
- `data/evaluation/results/mcp/stage7_interoperability_exit_v1.json`：最终不可覆盖证据；
- ADR-0050、本计划、最终 walkthrough/exit matrix：八维持久说明。

## 4. TDD 批次

### Batch A：真实 Client 暴露的协议协商红灯

1. 构造 client proposal `2025-11-25`，预期 Server 返回自身 `2025-06-18`；
2. 现实现会返回 JSON-RPC error，先保存红灯结果；
3. 最小修改 `_initialize`：proposal 必须是合法有界字符串，session/response 绑定 Server 版本；
4. 保持旧 2025-06-18 Client、重复 initialize、未初始化 call、非法 envelope 全部回归。

### Batch B：有界 stdio Server adapter

1. 用 BytesIO 写 initialize/notification/list/call 序列；
2. 断言 notification 不产生 response，三个 request 各一条 response，flush/EOF 后 session 关闭；
3. 非 UTF-8、非法/重复 JSON、非 object、超大 request/response 返回稳定 JSON-RPC error 或安全终止；
4. stdout 不写日志，错误不含输入正文。

### Batch C：官方外部 SDK Client no-I/O 互操作

1. 固定 `@modelcontextprotocol/sdk@1.30.0` 与完整 lockfile；
2. `npm ci --ignore-scripts` 后由 Node Client 用绝对 Python argv 启动 runner；
3. 验证 negotiated protocol、Server identity、四工具目录与一次 knowledge-search structured result；
4. transport 只记录 method/status trace，输出 catalog/result/trace digest 与计数；
5. 断言无 owner/session/body/query/attribution/路径/Secret 字段，Server stderr 为 0。

### Batch D：clean-SHA 双向真实门

1. 实现提交通过 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；
2. 在该 clean SHA 上运行 exit runner，先做外部 SDK→RiftCoach；
3. 再对 OP.GG 做一次 15 秒、一次 attempt、top lane/top 3 的真实产品调用；
4. 首错停止，成功/失败都只写 body-free immutable evidence；
5. 不覆盖 7-3 admission/product smoke，7-5 使用独立结果文件。

## 5. Exit Matrix

| 维度 | 通过条件 | 不能外推 |
|---|---|---|
| 外部 Server identity | OP.GG repo/endpoint/server/version 固定 | 底层数据条款完整 |
| RiftCoach Client protocol | initialize/notification/list/call 一次成功 | 永久在线/全工具支持 |
| 外部 Client identity | 官方 SDK package/version/integrity/license 锁定 | 任意 Client 永久兼容 |
| RiftCoach Server protocol | SDK 跨进程 stdio 完成完整生命周期 | 公网 HTTP 部署 |
| schema/drift | 四工具 catalog digest 与 selected schema digest 固定 | schema 可无版本演进 |
| security/owner | client 不传 owner；body/identity/Secret 不落盘 | 正式 Auth/RSO 已完成 |
| reliability | timeout/disconnect/oversize/malformed/close 回归通过 | HA、SLO、长期限流已完成 |
| data provenance | OP.GG evidence 仍为 partial/本地 TTL | 精确 patch/upstream freshness |
| regression | full pytest、RAG、Harness、compile/governance/security gates | 本地 skip 等于真库 |
| public evidence | 实现和最终状态的 exact-SHA 三 job 全绿 | CI 等于真实公网生产 |

任一双向硬门失败，Stage 7 不关闭；证据保留为 `partial` 或 `deferred`，不得用已有 7-3/7-4
fixture 或旧 smoke 替代。

## 6. 本地与公共验证

聚焦：

```powershell
npm ci --ignore-scripts --prefix experiments/mcp_interop
.\.venv\Scripts\python.exe -m pytest tests\test_mcp_interoperability_exit.py tests\test_mcp_server.py -q
```

全门禁：治理、完整 pytest、两套 RAG、Harness dry-run、compileall、pip、YAML、SDK boundary、
tracked Secret/run-data、body-free evidence、Node dependency/license、`git diff --check`。PostgreSQL 和
Linux package 仍由公共阻塞 job 补证。

真实门只能在干净实现 SHA 上显式执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.run_mcp_interoperability_exit `
  --execute `
  --expected-sha <IMPLEMENTATION_SHA> `
  --output data/evaluation/results/mcp/stage7_interoperability_exit_v1.json
```

## 7. 关闭顺序

1. RQ-079/ADR/设计/TDD/实现/初版 walkthrough；
2. 完整本地门，独立实现提交与 exact-SHA 公共 CI；
3. clean implementation SHA 上执行一次真实双向门；
4. 持久化证据与 exit matrix，提交并通过 exact-SHA 公共 CI；
5. 独立状态收尾记录最终 SHA/run，coverage `complete`，Stage 7 关闭；
6. 只交接 Stage 8 的 prepared 状态，不自动实施。
