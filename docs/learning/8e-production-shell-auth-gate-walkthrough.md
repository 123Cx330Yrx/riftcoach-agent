# 8E Production Shell / Auth Gate 学习 walkthrough

## 1. 问题与原则

认证和数据读取是两件事。Riot ID 是分析对象的标识，不能作为谁拥有这个工作台的证据。
因此页面先请求 provider-neutral 的 server session，再启动 live controller；session 失效时
旧页面不能继续显示旧 owner 的数据。

## 2. 设计与代码地图

- `AuthSessionWire` 是浏览器能看到的最小成功投影：schema、CSRF token、expiry。
- `BrowserAuthSessionClient` 负责同源 POST、bounded response 和错误 allowlist。
- `AuthGate` 负责 presentation state，不持有 owner 决策。
- `ProductionShell` 控制 controller 的 mount 时机；fixture/awakening preview 是明确的测试/预览边界。

## 3. 数据和控制流

```text
POST /auth/session → AuthSessionWire → AuthGate(authenticated)
                                      ↓
                              LiveWorkbenchController.start()
                                      ↓
                              owner-scoped GET/SSE
```

expired/revoked/required 被映射到可重试 boundary；auth_unavailable 被映射为配置缺失，
而不是假装“没有玩家资料”。

## 4. 验证与运行

本地证据：frontend unit `87 passed`，Playwright `22 passed`，typecheck/build 通过；JS gzip
保持在既有约束内。浏览器门覆盖 auth unavailable、expired、preview、live SSE、四个 viewport、
keyboard、reduced-motion、axe 和 no-overflow。

运行 `npm run dev -- --host 127.0.0.1` 可查看页面。没有配置 AuthSessionService 时，默认 live
页面会显示 `auth_unavailable`；这是 fail-closed 的预期结果。`?scenario=published` 是显式
fixture，不应被当成生产登录。

## 5. 失败、安全与边界

- cookie 由 server 设置，浏览器代码不读取 cookie 值；
- CSRF token 只在内存 projection，当前只为后续 mutation 接缝准备；
- 不保存 JWT、owner_id、Riot ID 或 report 到 localStorage/URL；
- OIDC/RSO callback、state/nonce、真实 provider、PostgreSQL session repository 和 HTTPS edge
  仍未在本批采用；
- 测试 server 的 deterministic session 只用于浏览器状态机，不是生产认证方案。

## 6. 面试表述

“我把认证做成独立的 server-side opaque session boundary。React 先通过 typed same-origin
session gate，再启动 owner-scoped live controller；401 过期和 503 provider 未配置分别投影为
可恢复或 fail-closed 状态。Riot ID 只代表分析对象，不参与身份授权。OIDC/RSO 仍作为独立 adoption
gate，避免把测试 session 或 UI 画面包装成生产登录。”
