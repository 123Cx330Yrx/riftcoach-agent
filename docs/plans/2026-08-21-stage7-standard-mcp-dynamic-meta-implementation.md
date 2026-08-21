# Stage 7 Standard MCP + Dynamic Meta Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 以标准 MCP 协议实现可验证的外部 Client/Server 互操作，并把动态 Meta 作为有来源、新鲜度和安全边界的 `MetaEvidence` 接入现有 Tool Runtime、Context、Skill 与 Harness。

**Architecture:** 协议 Adapter 负责 MCP envelope、版本、能力、发现、调用和 transport/session；所有已发现工具先适配为现有 `ToolDefinition`，再交给 `ToolRuntime` 做可靠执行。Meta Adapter 只产生 data-only `MetaEvidence`，RiftCoach Server 只通过 owner-scoped Application Facade 暴露只读工具。

**Tech Stack:** Python 现有 contracts、JSON Schema/Pydantic、SQLAlchemy/PostgreSQL 既有服务；MCP SDK 只有在 ADR/协议审计证明收益后才允许被 Adapter 包装，默认先用纯 Python/fake transport 完成 TDD。

---

## 入口设计门（当前 checkpoint，no-I/O）

### Task 0: 维护边界与审计资产

**Files:**
- Create: `docs/adr/0047-adopt-standard-mcp-boundary-and-opgg-meta-adapter.md`
- Create: `docs/plans/2026-08-21-stage7-standard-mcp-dynamic-meta-design.md`
- Create: `docs/learning/stage-7-standard-mcp-dynamic-meta-entry-design.md`
- Modify: `docs/project_execution_state.md`, `docs/requirements_change_log.md`, `docs/roadmap.md`, `docs/roadmap_change_history.md`, `docs/architecture_capability_matrix.md`, `docs/project_decisions.md`, `docs/learning/README.md`, `docs/learning/coverage.yaml`, `.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`

**Steps:**

1. 将用户授权记录为 RQ-072，清除 canonical 等待授权原因；
2. 记录 beginner teaching、代码接缝、方案比较、OP.GG admission checklist 和 7-1…7-5 顺序；
3. 保持 coverage `planned`，因为尚无产品代码或真实互操作；
4. 运行 `python scripts/check_project_governance.py`，确认唯一 checkpoint/Next Step 一致。

## 7-1: MCP Client contract（后续 checkpoint）

**Local status (2026-08-21):** implementation and all local gates complete; coverage remains
`planned` pending the implementation commit's exact-SHA public `pytest`, `postgres-migrations`,
and `packaging-smoke` jobs. No SDK, transport, Key, or external I/O was added.

### Task 1: Pure models and envelope tests

**Create:** `app/mcp/__init__.py`, `app/mcp/models.py`, `app/mcp/errors.py`, `tests/test_mcp_contracts.py`

1. [completed] 先写 `initialize`、capability、tool descriptor、call/result/error 的严格红灯；
2. [completed] 运行 `.venv\Scripts\python.exe -m pytest tests/test_mcp_contracts.py -q`，在缺少 `app.mcp` 时确认 collection red；
3. [completed] 实现版本 allowlist、唯一 tool name、immutable schema/catalog digest、参数/结果大小上限和 body-free error projection；
4. [completed] 增加 malformed/oversized/schema-drift/allowlist、standard annotations、strict bool/int 与 repr body-safety cases；
5. [in progress] 独立提交 `feat: add pure standard mcp contracts`，等待 exact-SHA 公共三 job 后关闭 7-1。

## 7-2: Transport and discovery

### Task 2: Fixture session and transport boundary

**Create:** `app/mcp/client.py`, `app/mcp/transport.py`, `tests/test_mcp_transport.py`, `tests/fixtures/mcp_server_*.json`

1. 写 fixture 驱动的 initialize/tools-list/tools-call trace 红灯；
2. 实现 transport-neutral session、deadline、disconnect、server restart 和 capability checks；
3. 先接 in-memory fixture，再隔离 stdio/subprocess；HTTP/streamable HTTP 只在标准版本和部署证据明确后加入；
4. 将已发现 descriptor 转成 `ToolDefinition`，调用交给 `ToolRuntime`，验证 retry/breaker 不在 Adapter 重复；
5. commit `feat: add mcp discovery and transport session`。

## 7-3: OP.GG Meta Adapter

### Task 3: Candidate audit and normalization

**Create:** `app/meta/models.py`, `app/meta/opgg.py`, `tests/test_meta_evidence.py`, `tests/fixtures/meta/opgg_*.json`

1. 先把已审计的 OP.GG tool schema/许可/freshness 证据登记为 admission fixture；若审计不通过，停止并写替代 ADR；
2. 写 MetaEvidence normalization 红灯：missing patch, stale, schema drift, digest mismatch, injection text, oversized facts；
3. 实现 allowlisted facts、digest/freshness、source/tool identity 和安全错误；
4. 集成 Context data-only/trust boundary，证明不写 Memory/Candidate/Plan/Progress；
5. commit `feat: normalize dynamic meta into bounded evidence`。

## 7-4: RiftCoach MCP Server

### Task 4: Read-only server facade

**Create:** `app/mcp/server.py`, `tests/test_mcp_server.py`

1. 对近期汇总、单局分析、知识搜索、报告评测写外部 client fixture 红灯；
2. 通过 `app/api/composition.py`/`app/product/*` 的 Application Service 组合，不直连 Repository；
3. 加 ActorContext owner scope、DTO/error allowlist、body-free response、schema/version tests；
4. 拒绝任意 URL/SQL/file、PUUID/Key/Prompt/Provider body、Memory 写入和未发布 Artifact；
5. commit `feat: expose restricted riftcoach mcp server tools`。

## 7-5: Interoperability exit review

### Task 5: Real external proof and exit matrix

**Files:** `docs/plans/2026-08-21-stage7-mcp-interoperability-exit-review.md`, `docs/learning/stage-7-standard-mcp-dynamic-meta-walkthrough.md`, `tests/test_mcp_interoperability_exit.py`

1. 固定外部 Server/Client identity、protocol version、transport、trace digest、许可和时间窗口；
2. 在 Key-last/no-secret body 规则下执行一次真实 `initialize/tools/list/tools/call`，失败即停且不重试未知错误；
3. 由真实外部 Client 调用 RiftCoach Server，保存 body-free immutable evidence；
4. 复核 disconnect/timeout/schema/security/owner-scope、八维 coverage、本地门禁和 exact-SHA CI；
5. 只有两侧真实互操作和 exit matrix 全部通过才关闭 Stage 7，否则以 deferred/partial decision 收尾并保留失败证据。

## Verification gates for every task

- Pure/fixture tests first; no real OP.GG/Provider/Key calls in local CI unless the exact checkpoint explicitly authorizes one bounded external gate.
- `python scripts/check_project_governance.py`, `.venv\Scripts\python.exe -m compileall app scripts`, full pytest, RAG development/holdout, Harness dry-run, SDK/secret/tracked-data/YAML checks, and `git diff --check`.
- PostgreSQL semantics remain in the existing real-PostgreSQL job; MCP tests must not replace it with SQLite claims.
- Public CI must run on the exact pushed SHA; a green design job never proves product interoperability.
