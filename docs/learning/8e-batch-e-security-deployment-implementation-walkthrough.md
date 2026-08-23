# 8E Batch E implementation walkthrough（E1/E2/E3 本地阶段）

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

## 8. 面试准确表述

“我在 8E 先把安全边界拆成可测试的 provider-neutral seams：opaque server session 和 session-bound CSRF，
ASGI 层的 header/body/rate budgets，以及 versioned SecretSource 的 key-last Worker composition。当前证据是
本地 focused TDD 和 fail-closed 行为；我不会把 local in-memory session、environment fallback 或单机 limiter
说成正式 Auth/RSO、Secret Manager、HTTPS 或分布式生产 SLA。”
