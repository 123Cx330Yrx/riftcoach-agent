# 8E Production Shell / Auth Gate 实施与验证

## Implementation map

- `web/src/api/wire.ts` / `web/src/api/decoders.ts`：冻结 `AuthSessionWire`，严格校验
  schema、csrf token 和 timezone-aware expiry。
- `web/src/auth/session.ts`：只允许 relative `/api/auth/session`、same-origin credentials、
  bounded body 和 allowlisted body-free error code；不把 cookie/token 写入日志或 storage。
- `web/src/auth/AuthGate.tsx`：把 session 结果投影为 checking/authenticated/unavailable/expired；
  retry 会重新发起 session，不带旧 controller。
- `web/src/app/App.tsx`：fixture 和 awakening preview 保持显式路径；默认 live 必须先过
  `ProductionShell → AuthGate`，controller 只在 authenticated 后 mount/start。
- `web/tests/support/liveApiServer.mjs`：仅测试服务器返回确定性 session fixture，不能作为生产认证实现。

## Test-first evidence

1. `session.test.ts` 证明 same-origin POST、typed response、malformed payload fail-closed 和
   provider error 不泄露正文。
2. `AuthGate.test.tsx` 证明 checking 不提前渲染 live、unavailable 可恢复、expired 明确展示。
3. `App.test.tsx` 证明 auth failure 不加载 live profile，已有 fixture/live contract 仍保持。
4. `auth-gate.spec.ts` 证明浏览器中 auth unavailable 和 expired 两条恢复路径。
5. 既有 awakening/live/visual/workbench E2E 继续验证 preview、SSE、四 viewport、axe、reduced-motion
   和 no-overflow。

## Verification commands

```powershell
cd D:\riftcoach-agent\web
npm run test:unit -- --run
npm run test:e2e
npm run typecheck
npm run build
```

本批不调用 Riot、OP.GG、OIDC、RSO 或 LLM；测试 server 的 session fixture 只证明浏览器状态机，
不证明 provider adoption 或 production identity。
