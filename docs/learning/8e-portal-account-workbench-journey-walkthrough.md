# 8E Portal → Account → Workbench 三层旅程 walkthrough

> 本文覆盖 RQ-105/RQ-106 在当前 8E 原子批中的实现证据。它不把整个 8E、正式登录、最终视觉或可追问
> Coach 宣称为完成。

## 1. 问题与原理

旧页面把三件不同的事混在了一起：品牌开场、登录/玩家绑定和复盘工作台。结果是默认 `/` 会提前申请
session，视觉预览会跳进 fixture，Riot ID 表单又被误当成开屏。修正采用两个简单原则：

1. **互斥产品层**：任一时刻只挂载 Portal、Account、Workbench 中的一层；
2. **最晚启动 I/O**：视觉开屏不需要身份数据，因此核心激活前 Auth、profile、Player Link 和 SSE 调用必须为 0。

这不是“多做一个欢迎页”。它把网络和资源生命周期与用户旅程对齐：进入 Account 才申请 session，明确选中
owner-scoped profile 后才构造 live controller。

## 2. 设计与实现

Design Read：LoL 战术教练 · 电影感 Hextech、克制电竞转播 · Portal register=brand / SPECTACLE=6 /
CSS + generated layered plate；Account/Workbench register=product / SPECTACLE=3。这里不声称 Three/WebGL 级
SPECTACLE 7。反默认方向同时拒绝普通深色 AI Dashboard、泛冰晶宫殿和齿轮管线喧宾夺主；中央 core 只保留
一个，视觉服务于进入层级而不是展示引擎本身。

ADR-0067 采用 query/history 编排而没有引入 React Router：

```text
/?
  Portal: zero API/SSE
    → core click / Enter / Space
/?stage=account
  Auth session → profiles
    ├─ choose existing profile
    └─ POST player-links → queued/running/succeeded|failed → refresh profiles
/?stage=workbench&player_profile_id=<UUID>
  revalidate session → create/start one LiveWorkbenchController
```

`?surface=awakening` 仍是显式 no-I/O visual/demo preview；`?scenario=...` 仍是显式 fixture。两者在
`ProductJourney` 外处理，不能污染默认 production URL 或成为真实 Auth/Player Link 的证据。

## 3. 代码地图

- `web/src/app/productJourney.ts`：只接受 `portal|account|workbench`，非法或未绑定 workbench URL fail closed；
- `web/src/app/App.tsx`：history/popstate、三层互斥挂载、session 失效回退和 controller 生命周期；
- `web/src/components/AwakeningScene.tsx`：唯一原生 core button、单次 720ms handoff、系统/显式 reduced motion；
- `web/src/auth/AuthGate.tsx`：checking/signed-out/expired/unavailable，不把 session bootstrap 叫 Riot 登录；
- `web/src/components/AccountAccess.tsx` 与 `web/src/account/playerAccessController.ts`：已有档案、真实 Player Link、
  generation/AbortController、有界轮询和成功后刷新；
- `web/src/api/{client,wire,decoders,playerLinkApi}.ts`：同源 POST、CSRF/idempotency、严格四态 decoder；
- `web/src/styles/product-journey.css`：Portal/Account/Auth 共享材质、bounded motion、focus/mobile/reduced-motion；
- `web/tests/support/liveApiServer.mjs` 与 `web/tests/e2e/product-journey.spec.ts`：真实浏览器 fake API 纵向；
- `tests/test_player_link_api.py`：真实 HTTP session owner → CSRF Link → terminal → profiles 组合证据。

## 4. 数据与控制流

Account controller 的一次新增玩家不是“提交表单就成功”：

```text
UI input
→ public_observed 显式映射为 wire observed
→ POST /player-links (session cookie + CSRF + fresh idempotency key)
→ GET returned owner-scoped link URL
→ queued/running 只显示等待
→ succeeded 要求完整 subject/relationship/Riot ID
→ GET /player-profiles
→ relationship_id 必须出现在刷新后的 owner list
→ 用户再次明确继续，才把 relationship_id 放进 workbench URL
```

任何新提交、离开 Account 或 dispose 都会 abort 上一代请求；迟到 terminal 不得覆盖新状态。Workbench 深链的
profile 不在 server list 时，controller 返回 unavailable，绝不静默选择第一项。

## 5. 验证证据

- 后端组合/Player Link focused：`26 passed, 1 warning`；
- 前端 strict typecheck、unit `24 files / 136 passed` 与 production build 通过；JS/CSS gzip
  `142.68/18.50 kB`，JS 低于 `150 kB` 硬门；
- 完整 Playwright `35 passed`，包含
  core 前 API=0、真实 Link 三态、reload/back/forward、未列 profile fail closed、四视口、axe 和 reduced motion；
- 完整 Python `1982 passed, 1 skipped, 1 warning, 127 subtests passed`，真 PostgreSQL 17 migration/head check、
  两套 RAG、Harness、compile/pip/YAML、npm audit、SDK/Secret、governance/diff 与 Linux package smoke 全绿；
- finesse detector 对 Portal CSS/TSX `P0=0`；唯一 P2 是 `mask-image` 必需的黑色 alpha stop，不是页面的纯黑
  视觉 token。真实 1440/390 与 reduced-motion 截图已确认 layered plate/Core 有像素输出且无横向溢出；
- 产品 Riot/OP.GG/Provider/LLM 调用为 0。视觉生成使用两次项目资产生成调用；本地 gptimage2 因代理未监听在
  请求前失败，因此 gptimage2 image request 为 0。

## 6. 运行与回退

```powershell
cd D:\riftcoach-agent\web
npm run typecheck
npm run test:unit
npm run build
npm run test:e2e
```

本地真实旅程需要同源 `/api` 有 AuthSessionService 与 owner-scoped services；默认 composed app 未接 provider 时
会诚实显示“登录暂不可用”。视觉背景可删除 `rift-portal-background-v2.webp`，CSS 会先退到 aperture fallback，
再可退到纯 CSS/SVG；任何退回都不改变数据和身份控制流。

## 7. 失败、安全与限制

- `/auth/session` 仍是 provider-neutral seam，不是 OIDC/RSO；`self` 仍是 `unverified_claim`；
- Player Link 超时保持 pending，不伪造 failed；terminal retry 需要新 idempotency key；
- Link path、response schema、partial identity、impossible claimed/terminal timestamp 组合全部拒绝；
- Portal bitmap 无文字、UI 或核心；DOM 是唯一交互和 copy 真值；旧 instrumentarium 已退出 runtime；
- 当前 motion 是 bounded V1 choreography，不是最终电影化分层引擎；RQ-103/final visual QA 仍需继续；
- 当前 Coach 仍只展示 published report，不能从 Web 提问；RQ-107 的 bounded Coach 顺序待用户裁决。

## 8. 面试表述

可以说：

> 我把电影开屏、账号访问和数据工作台拆成互斥层，并用 URL/history 固定可恢复状态；网络 I/O 按层最晚启动。
> Player Link 使用 CSRF、幂等、有界轮询、Abort/generation 和 owner-list revalidation，浏览器 E2E 覆盖了完整
> Portal→Account→live Workbench，而不是只测组件。

不能说：

- “完成了 Riot 登录/本人验证”；
- “图片生成完成了动态 Portal”；
- “Coach 已经可以聊天”或“Training 已能由 Agent 自动更新”；
- “三层旅程完成等于整个 8E/产品已完成”。
