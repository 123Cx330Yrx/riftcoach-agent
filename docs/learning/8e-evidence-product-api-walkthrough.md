# 8E Batch C：Evidence 快照、四态产品 API 与 Cursor SSE walkthrough

这份材料解释 8E Batch C 已实现的后端产品接缝。设计依据是
[ADR-0060](../adr/0060-adopt-postgresql-evidence-snapshots-and-cursor-sse.md)、
[专用设计](../plans/2026-08-23-8e-evidence-product-api-design.md)和
[实施计划](../plans/2026-08-23-8e-evidence-product-api-implementation.md)。整个 8E coverage 仍保持
`planned`：Batch C 关闭后还要继续静态/fixture 前端、真实产品纵向、安全部署与最终作品集，不可把本批
等同于完整产品化。

## 1. 问题与原理

8D 已能在内存里生成 `EvidenceBundle`，8C 已把 task lifecycle event 存入 PostgreSQL，但浏览器产品仍有
三个断点：证据没有可重放历史，断线后只能轮询事件，前端也不知道 task、Harness publication 和 evidence
三套状态应怎样组合。

Batch C 使用三个通用原则：

1. **不可变快照**：一次 refresh 追加一条 revision；历史事实不因过期或下一次刷新被覆盖。
2. **送达不是事实源**：SSE 只传 PostgreSQL durable event；浏览器断线后用 cursor 重放，不把连接状态当
   task 状态。
3. **产品状态是确定性投影**：`published/degraded/rejected/not_ready` 由 task、publication、report 和
   evidence freshness/disposition 共同计算，不交给 React 临时猜。

过期采用 query-time projection：数据库中的原始 snapshot 不变，查询时只撤销依赖新鲜 Meta/patch 的
usable claim。这样既保留可审计历史，也不会把过期推荐继续显示为当前事实。

## 2. 设计与实际实现

### 2.1 Evidence snapshot

- `EvidenceBundle.to_storage_projection()` 保存完整 allowlisted typed facts，并保留 claim 顺序用于严格重建；
- `bundle_from_storage_projection()` 重建 Riot/static/patch/Meta/join/conflict/gap，重算 nested Meta digest 和
  bundle digest；任一漂移均 fail closed；
- `EvidenceBundleSnapshot` 绑定 snapshot/task/run/owner/revision/refresh/bundle/time，并以独立 SHA-256 绑定
  snapshot identity；
- migration `0011_evidence_product_api` 使用 JSONB、复合 task FK、revision/refresh 唯一约束、256 KiB
  上限、latest index、`ON DELETE CASCADE` 和禁止 UPDATE 的 PostgreSQL trigger；
- Repository 锁 exact task row 后分配连续 revision。同一 refresh identity + 同一 bundle digest 即使稍后
  重试也 replay 首次提交；相同 refresh + 不同内容 conflict。

### 2.2 Product service/API

`EvidenceProductService` 先通过 owner-scoped task lookup 确认 run，再读取同 owner/run 的 latest snapshot。
公开端点为：

- `GET /runs/{run_id}/evidence`：revision/digest/time/freshness/disposition/confidence/usable claims 与
  body-free public projection；
- `GET /runs/{run_id}/product-state`：四态、reason code、原始 task/publication/evidence 安全枚举。

跨 owner 与未知 run 都返回 404；证据尚未生成返回 409；snapshot/digest identity 漂移返回 500；数据库
不可用返回 503。响应不包含 owner、refresh identity、PUUID、请求正文、Key、Prompt 或上游 raw body。

### 2.3 Cursor SSE

`GET /tasks/{task_id}/events/stream` 在响应开始前做 owner preflight。query `after_cursor` 和
`Last-Event-ID` 可任选一种；同时存在必须相等。每条 lifecycle frame 使用 durable event cursor 作为 SSE
`id`，data 与已有 `TaskEventResponse` 字段 allowlist 一致；worker/operation/checkpoint/token 被移除。

空闲只发 `: keep-alive`，连接窗口有限；终态 event 发出后立即关闭。Repository/服务异常发生在响应开始后
时，只发 `stream.error {"code":"service_unavailable"}` 并关闭，原异常正文不进入网络。

## 3. 代码地图

| 层 | 主要文件 | 职责 |
|---|---|---|
| pure storage/product contract | `app/evidence/storage.py` | full round-trip、snapshot digest、expiry、usable claims、四态 projector |
| service/port | `app/evidence/ports.py`, `app/evidence/service.py` | owner-scoped latest evidence 与 product state；安全错误边界 |
| PostgreSQL record/repository | `app/persistence/evidence_snapshot_record.py`, `app/persistence/evidence_snapshot_repository.py` | append/replay/conflict、row lock revision、strict rehydrate |
| migration | `migrations/versions/0011_evidence_product_api.py` | JSONB/约束/索引/FK/cascade/append-only trigger |
| SSE | `app/tasks/sse.py` | cursor resolution、allowlisted frame、keepalive、终态/错误关闭 |
| HTTP DTO/route | `app/api/evidence_models.py`, `app/api/main.py` | evidence/product-state/SSE public contract |
| deployment composition | `app/api/composition.py` | lifespan 内绑定 SQL Repository、Product Service 与 SSE Service；构造 no-I/O |
| Linux smoke | `scripts/run_packaging_smoke.py` | 真 PostgreSQL API stack 中检查四态、缺证据 409 与 terminal SSE，外部调用 0 |

## 4. 数据流与控制流

### 4.1 写入与查询

```text
materialized typed EvidenceBundle
  → PendingEvidenceBundleSnapshot(refresh_id)
  → lock owner/task/run row
  → same refresh + same bundle? replay
  → same refresh + changed bundle? conflict
  → else append revision N+1 + snapshot digest
  → GET latest by trusted owner/run
  → strict rehydrate + nested/bundle/snapshot digest checks
  → query-time expiry projection
  → evidence DTO / four-state DTO
```

### 4.2 SSE 重连

```text
browser Last-Event-ID N
  → owner/task preflight
  → PostgreSQL events WHERE event_cursor > N
  → id: cursor + allowlisted task.lifecycle JSON
  → terminal? close
  → idle? keepalive, bounded poll, close/reconnect
```

同一 cursor 之后才读取，因此断线重连不会重复已确认 event。SSE 不创建新 task event，也不从 Trace、日志或
内存猜状态。

### 4.3 四态优先级

```text
queued/running/recovery_required → not_ready
failed/cancelled                → rejected
succeeded + Harness rejected    → rejected
succeeded + missing/expired/degraded evidence or degraded publication
                                → degraded
succeeded + published + report + complete/current evidence
                                → published
```

## 5. 验证证据与真实故障

TDD 不是只补 happy path。本批先后出现并修复了这些有效红灯：

- `ModuleNotFoundError: app.evidence.storage/service/sse`，证明测试先于实现；
- typed storage round-trip 首次暴露 claim order 漂移；canonical digest 继续排序，但 storage 额外保留 typed
  顺序；
- JSONB tamper 测试最初用了浅拷贝，实际没有发出 UPDATE；改为 deep copy 后才真正证明 read-time digest
  防线；
- 同 refresh 的稍后重试最初因 `stored_at` 不同被误判 conflict；合同改为 bundle-content replay，首次
  committed timestamp 保持不变；
- 多文件真库 collection 暴露 import-order circular dependency；`app.api` 改为 lazy convenience export，
  SSE encoder 也不再反向依赖 FastAPI package；
- 0011 成为 head 后，三个旧 migration 测试仍写死 0010，已只更新 current-head 断言，0010 专项行为仍保留。

覆盖包括 pure round-trip/digest/expiry/四态、真 PostgreSQL migration/repository/并发/tamper/cascade、服务和
HTTP error matrix、SSE reconnect/terminal/keepalive/failure、composition no-I/O、真实 PostgreSQL HTTP
纵切和 Linux package smoke。最终本地证据为 focused `79 passed`、CI-equivalent PostgreSQL
`194 passed, 1 warning`、完整 `1888 passed, 1 skipped, 1 warning, 127 subtests passed`；唯一 skip 是
Windows symlink 创建。Linux Compose 又证明 schema 1.6、Memory Context 3 records、外部调用 0、非 root 和
image exclusion。implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` 随后由 Actions
`32629160732` 完成 exact-SHA 公共闭环：公共 pytest `1750 passed, 139 skipped, 1 warning,
127 subtests passed`、真实 PostgreSQL `194 passed, 1 warning`，Linux package schema 1.6、外部调用 0、
非 root/image boundary 与资源清理均通过。

最后一次 Linux smoke 还捕获了部署组合 Bad Case：API 的默认 owner 是 `local-demo-owner`，smoke 曾硬编码
`packaging-smoke-owner`，严格 Memory binding 因此正确拒绝。修复不是放宽查询，而是让 API/smoke 共用
validated `RIFTCOACH_LOCAL_OWNER_ID`；缺失或非法 owner 在网络/数据库前 fail closed。

## 6. 运行手册

本机 PostgreSQL 17 容器为 `riftcoach-local-postgres`，只绑定 `127.0.0.1:54329`。新 PowerShell 终端要把
用户级 URL 同时加载到测试变量和 Alembic 使用的变量；只设置前者会让一部分旧 fixture 在 migration 时因
缺 `DATABASE_URL` 失败。

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' start riftcoach-local-postgres
$url = [Environment]::GetEnvironmentVariable('RIFTCOACH_TEST_DATABASE_URL', 'User')
$env:RIFTCOACH_TEST_DATABASE_URL = $url
$env:DATABASE_URL = $url

.\.venv\Scripts\python.exe -m pytest `
  tests/test_evidence_snapshot_contracts.py `
  tests/test_evidence_snapshot_repository_postgres.py `
  tests/test_evidence_product_service.py `
  tests/test_evidence_product_api.py `
  tests/test_evidence_product_api_postgres.py `
  tests/test_task_sse.py -q

.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe scripts/check_project_governance.py
git diff --check
```

数据库 URL/密码不得写入仓库；真实 Riot/OP.GG/Provider/LLM 也不属于这组 runbook，本批外部调用必须为 0。

## 7. 失败、安全与范围边界

- JSONB 只保存已验证的 body-free Evidence projection，并同时受 Python 与 PostgreSQL size/digest/shape 门；
- append-only trigger 防普通 UPDATE，digest verification 防绕过 trigger 后的存储漂移；digest 证明内容身份，
  不证明第三方来源本身永远真实；
- expiry 不删除历史，也不自动回退旧 revision；过期只限制当前 usable claim；
- SSE cursor 来自 durable SQL event；keepalive、连接持续时间和 stream error 都有界；这不是生产级海量长连接
  容量或消息队列；
- 404 owner hiding 依赖 trusted ActorContext；本批没有实现公网 Auth/RSO、限流、HTTPS/CSP 或审计后台；
- 没有 refresh scheduler，也没有在 GET 中调用 Riot/OP.GG；真实上游刷新仍须后续 writer/调度设计；
- 没有 React、视觉动效、正式 dashboard、备份 restore、生产发布或 SLA；这些仍在 8E 后续批/8F；
- Batch C 没有重新运行 8B holdout，也没有采用 Multi-Agent、DAG 或第三方 Agent Runtime。

## 8. 面试准确表述

可以说：

> 我把 8D 的 typed EvidenceBundle 保存成 PostgreSQL 追加式不可变快照。refresh identity 提供幂等，
> task row lock 分配连续 revision，nested/bundle/snapshot digest 与 append-only trigger 共同 fail closed；
> 过期在查询时撤销时效性 claim，不改写历史。前端可以用 cursor SSE 重放 durable lifecycle event，并通过
> 一个确定性 projector 区分 published、degraded、rejected 和 not-ready。合同由 pure、真 PostgreSQL、
> API、reconnect 和 Linux package 纵向共同验证。

不能说：

- GET 会实时刷新 Riot/OP.GG，或已经存在自动 scheduler；
- SSE 已达到生产级连接规模、跨实例 fan-out 或消息队列 SLA；
- digest/OP.GG 数据等于 Riot 官方事实；
- 已完成正式 Auth、React 前端、视觉打磨、备份恢复或公网部署；
- Batch C 本地测试完成就等于整个 8E 或 Stage 8 已关闭。
