# 8E Batch E implementation walkthrough（E1/E2/E3/E4 本地阶段）

> 这份材料记录当前实现到哪里、为什么这样拆，以及哪些仍然没有完成。它不是“生产安全已就绪”的声明。

## 1. 问题与原理

Batch E 解决的是产品从“本地/fixture 可展示”走向“可以安全承载用户状态”的边界问题：浏览器不能携带
owner/PUUID/Key，写请求不能只靠 cookie，过大的请求不能进入业务层，Worker 也不能把 provider key 永久放在
settings 的 repr 或日志里。核心原则是 server-side trust：HTTP 只传 opaque session，ActorContext 由服务端
解析；CSRF 绑定同一 session；edge 先做容量和速率预算；secret 在真正构造外部 client 的最后一刻解析。

## 2. 设计与实际实现

- E1：`app/auth/session.py` 的 `AuthSessionBoundary` 组合 store 与 server-side owner callback；`POST /auth/session`
  一次性返回 CSRF token/expiry 并设置 Secure、HttpOnly、SameSite=Lax cookie；启用 auth session 时，所有写请求
  先通过同 cookie 的 `X-CSRF-Token`，`GET` 业务路由再从 session 得到 ActorContext；`DELETE /auth/session` 撤销并清 cookie。
- E2：`RequestBudgetMiddleware` 在 ASGI edge seam 检查 header/body（含无 Content-Length 的 chunk 累计），
  `InMemoryRateLimiter` 提供显式单机 IP fixed-window policy；预算错误仍带 CSP/nosniff 等安全头。
- E3：`SecretMaterial`/`SecretSource` 支持 version、expiry、revoke 和 dual-key overlap；Worker settings 只保存
  endpoint/public config 与 redacted source，PostgreSQL readiness 通过后才读取 Secret 并构造 Riot/LLM client。

## 3. 代码地图

| 责任 | 代码 |
|---|---|
| session primitive / cookie policy | `app/auth/session.py` |
| typed HTTP auth response | `app/api/auth_models.py` |
| Actor + CSRF + auth routes | `app/api/main.py` |
| request budget / rate policy / headers | `app/api/security.py` |
| environment budget composition | `app/api/composition.py` |
| versioned secrets | `app/providers/secrets.py` |
| key-last Worker composition | `app/workers/composition.py` |
| focused contracts | `tests/test_auth_sessions.py`, `tests/test_auth_session_api.py`, `tests/test_task_api_security.py`, `tests/test_secret_source.py`, `tests/test_worker_composition.py` |

## 4. 数据与控制流

```text
POST /auth/session
  → AuthSessionBoundary.issue()
  → store 保存 cookie/csrf digest + owner + expiry
  → response 只返回 csrf_token/expiry + opaque cookie

业务 GET
  → cookie digest resolve
  → ActorContext(owner_id)
  → owner-scoped service/repository

业务 POST/DELETE
  → RequestBudgetMiddleware
  → session cookie + same-session CSRF
  → route validation/service

Worker startup
  → parse public config + SecretSource
  → PostgreSQL readiness
  → SecretSource.read(latest usable)
  → construct Riot/LLM clients
```

## 5. 验证证据

- Auth/session focused tests：`tests/test_auth_sessions.py` 与 `tests/test_auth_session_api.py` 共 10 项。
- Security/composition/adapter focused regression：`tests/test_task_api_security.py`、`tests/test_fastapi_adapter.py`、
  `tests/test_api_composition.py` 共 31 项。
- Secret/Worker composition：`tests/test_secret_source.py`、`tests/test_worker_composition.py` 共 15 项。
- 本轮聚焦合计 `56 passed, 1 warning`；`python -m compileall -q app/api app/auth app/providers app/workers`、
  `git diff --check` 通过。公共 PostgreSQL/Linux exact-SHA 仍未在本材料中宣称。

## 6. 安全运行方法

- 未注入 `auth_session_service` 时，`POST /auth/session` 返回 `auth_unavailable`；这保持 production fail-closed。
- local/test 可显式注入 `AuthSessionBoundary` 与 `InMemorySecretSource` 做合同测试；不要把测试 owner、Riot ID
  或 Secret 写进浏览器、Artifact、Trace、日志或备份。
- 生产需要独立 OIDC/RSO callback、PostgreSQL session repository、HTTPS edge 和 Secret Manager adapter，
  本地 primitive 不能直接替代它们。

## 7. 失败、安全与范围边界

- 缺失/过期/撤销 session 映射为 allowlisted 401；CSRF 不匹配为 403；未知 owner 不从 request body 接受。
- header/body 超限分别为 431/413，fixed-window 超限为 429；内存 limiter 不提供多副本一致性。
- Worker 在 key-last 构造前先过 DB readiness；Secret 失败不会暴露值。环境变量 source 是 local/test-compatible
  fallback，不是 Secret Manager 证据。
- 未实现：OIDC/RSO、正式登录 UI、PostgreSQL session migration、HTTPS/HSTS edge、backup restore/erase、
  deployment packaging、metrics/alerting、完整 Timeline/Training、OP.GG breadth 和 golden slice。

## 8. E4：backup / restore / erase 接缝

E4 把 6B-9 已有的在线 owner deletion marker 延伸到两个仍会留下数据的落点：
`runs_root/<run_id>/` 下的 final Artifact 与 Runtime Trace，以及恢复后的数据集。这里的“备份”
仍然只生成 body-free manifest；真正的加密对象存储和 KMS 由外部适配器承担，代码不会把普通
JSON 当成加密备份。

### 代码地图

| 责任 | 代码 |
|---|---|
| manifest、marker digest、restore readiness | `app/lifecycle/backup.py` |
| marker → conversation/relationship → run 的只读定位 | `app/persistence/owner_data_lifecycle_repository.py` |
| run 目录（Artifact + Trace）清理与补偿 marker | `app/tasks/deletion.py` + `app/lifecycle/backup.py` |
| API composition 的 hidden-before-cleanup 接线 | `app/api/composition.py` |
| focused restore/erase drill | `tests/test_backup_restore.py` |

### 数据与控制流

```text
owner delete request
  → PostgreSQL transaction: hide target + immutable deletion marker
  → commit
  → locator finds only matching owner/conversation/relationship run IDs
  → FileRunDataCleaner removes Artifact + Runtime Trace directory
  → success: marker COMPLETE
     failure: body-free cleanup_pending compensation; online rows stay hidden

backup restore
  → validate marker IDs and deterministic digest
  → replay deletion markers (idempotent wrapper may skip an already-applied marker)
  → readiness probe
  → ready only after replay succeeds; otherwise rollback newly-applied markers
```

`OwnerRunArtifactTraceCleaner` 会拒绝错误 owner、错误 conversation/relationship 或无目标的
run reference；因此 locator 出现跨 owner 数据时是 fail-closed，而不是“尽量删”。重复 restore
不会再次提交同一个 marker；readiness 失败也不会把上一次成功恢复的 marker 错误回滚。

### E4 验证与运行方法

- `tests/test_backup_restore.py` 当前覆盖 manifest digest 篡改、重复 marker、restore replay、
  partial failure、compensation failure、readiness failure、幂等重放、owner 目标过滤，以及
  真实 `FileRunDataCleaner` 删除同时包含 Artifact/Trace 的 run 目录。
- lifecycle service 的既有测试证明 SQL 隐藏先于 cleaner，cleaner 失败只留下 pending marker，
  不重新暴露正文；PostgreSQL locator 使用同一真实 `ReviewTaskRecord` control plane。
- 本地 E4 focused：`16 passed`；`compileall` 和 `git diff --check` 通过。

### E4 边界

- 当前没有对象存储、KMS、备份字节、定时备份任务或跨主机 restore drill；`encryption` 固定为
  `external_kms_required`，因此不能宣称“已加密备份”或 RPO/RTO 达标。
- marker replay 的实际数据库写入由部署侧 adapter 提供；本批冻结并验证的是顺序、幂等、
  补偿和 readiness 合同，不伪造 PostgreSQL restore 或外部 I/O。
- 当前仍未完成 OIDC/RSO、PostgreSQL session repository、HTTPS/HSTS edge、多副本 limiter、
  生产 Secret Manager、完整 Timeline/Training、OP.GG breadth 和 golden slice。

## 9. E5：packaging / observability 接缝

E5 的问题是“一个部署包能不能被重复启动、检查、回滚，并且不会把私密正文变成日志”。现有 Compose
已经固定了 PostgreSQL → migration → API → worker/smoke 的依赖顺序、API liveness/readiness、非 root
镜像和 Linux no-I/O smoke；本批只补一个可审计的 metrics 投影，不把它升级成新的监控平台。

- `TaskObservability.emit()` 自动累加 body-free event counter；`public_snapshot(max_samples=1000)`
  对 latency 样本做硬上限，避免 metrics 端点把进程内历史无限暴露。
- `GET /health/metrics` 只返回 allowlisted counter 名称/数值和 p50/p95 latency；不需要 owner、cookie、
  report、Prompt、Riot ID 或 Provider Secret，也不读取数据库或外部网络。
- `health/live` 仍只表示进程可响应，`health/ready` 仍要求 PostgreSQL 连通且 Alembic current=head；
  migration 失败时 API 不会被误判 ready。Compose smoke 继续是 no-I/O 的发布前门。

### E5 runbook（当前单机边界）

```text
docker compose --profile smoke config --quiet
docker compose --profile smoke up --build --detach --wait api
docker compose --profile smoke run --rm --no-deps smoke
docker compose --profile smoke down -v --remove-orphans
```

发布前必须先执行 migration head→base→head 与 `alembic check`，再确认 `/health/ready`；回滚采用
“停止当前 Compose → 选择已验证的旧镜像 tag/digest → 按兼容 migration 顺序启动”，不可在 API 尚未
ready 时接受流量。当前 runbook 不承诺跨区 HA、自动 rollback、99.9% SLA 或长时间指标存储。

### E5 验证与边界

- focused：FastAPI metrics + observability `17 passed`；完整回归和公共 exact-SHA 门继续复用 E4 的
  三 job contract。
- E5 不引入 Prometheus exporter、Redis、Kubernetes、Celery、Kafka 或第二套 metrics runtime；若未来
  多副本/长期告警成为真实 Bad Case，再单独做采用 ADR 和容量评测。
- Web static artifact 仍保持 Batch D 的 fixture-backed boundary，等 Production shell/Auth gate 后再
  决定如何由 edge 提供，不把当前 Python image 说成完整前端部署。

## 10. 面试准确表述

“我在 8E 先把安全边界拆成可测试的 provider-neutral seams：opaque server session 和 session-bound CSRF，
ASGI 层的 header/body/rate budgets，versioned SecretSource 的 key-last Worker composition，以及
hidden-before-cleanup 的 owner marker→Artifact/Trace→restore replay 链。E4 的证据是本地 focused TDD
和 fail-closed/幂等行为；我不会把 local in-memory session、environment fallback、单机 limiter 或
external-kms-required manifest 说成正式 Auth/RSO、Secret Manager、HTTPS、加密备份或分布式生产 SLA。”
