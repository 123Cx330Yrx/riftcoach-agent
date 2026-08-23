# 8E Remaining Product Modules：Production Shell / Auth Gate 设计

## Teaching contract

问题：Live Workbench 现在可以直接请求 owner-scoped API，但浏览器还没有先确认
“这个请求是否拥有有效的 server session”。如果直接把 401/503 当成普通加载失败，用户
会误以为 Riot ID 是登录凭证，或者看到一个没有身份边界的空工作台。

原则：认证是一个独立的控制边界。浏览器只拿 opaque session cookie 和一次性投影出的
CSRF token，owner 仍由服务端 session 解析；React 只投影状态，不决定 owner，也不把 Riot
ID 当认证信息。

本批实现：同源 `POST /auth/session` 的 typed client、checking/authenticated/unavailable/
expired UI 状态，以及 live controller 对 session 失效的恢复入口。非本批：OIDC/RSO 登录、
PostgreSQL session repository、真实 provider callback、密码/Access Token、production HTTPS
edge 和登录后的 profile mutation。

## State and control flow

```text
浏览器打开 Live Workbench
        │
        ├─ POST /api/auth/session (same-origin, credentials=include)
        │       ├─ 200 → csrf token + expiry → start LiveWorkbenchController
        │       └─ 503/invalid → auth_unavailable boundary + retry
        │
        └─ controller GET /api/player-profiles...
                ├─ 200 → owner-scoped Workbench
                └─ 401 auth_session_expired/revoked → expired boundary + retry
```

Fixture scenario 和 `surface=awakening` preview 继续显式绕过 production auth，且保留
fixture/preview disclosure；这不是把测试 session 伪装成 production login。

## Contracts

| 状态 | 用户看到什么 | 允许的下一步 | 事实边界 |
|---|---|---|---|
| checking | Checking your session | 等待 | 不加载 profile |
| authenticated | Live Workbench | 正常读取 | server session 决定 owner |
| unavailable | Sign-in is not ready | Retry secure session | 不显示 profile/Riot 数据 |
| expired | Your session needs attention | Try session again | 清除当前 controller，不保留旧报告 |

所有错误仍是 body-free allowlist code。CSRF token 只保存在内存中的 session projection，
为后续 mutation seam 预留，不写 localStorage、URL、Trace 或报告。

## Alternatives and trade-offs

- 直接在每个 API 请求里重复登录：拒绝，会产生多套身份语义和竞态。
- 浏览器保存 JWT/owner_id：拒绝，扩大 XSS/伪造 owner 风险。
- 本批直接接 OIDC/RSO：拒绝，provider、redirect、state/nonce、费用和隐私边界尚未过 adoption gate。
- 选择 provider-neutral server session：采用，能先完成真实产品边界，后续接入 provider 不改变 React 合同。

## Exit criteria

- typed auth response/error decoder 和 same-origin credentials；
- checking、auth unavailable、session expired/retry、authenticated 四态有 unit + browser 证据；
- live workbench 不在 auth gate 之前启动；fixture/awakening preview disclosure 不变；
- 1440/1024/390/320、键盘、reduced-motion、axe、no-overflow 和 no-remote-I/O 全部通过；
- 不声称 OIDC/RSO 或真实生产 session 已完成。
