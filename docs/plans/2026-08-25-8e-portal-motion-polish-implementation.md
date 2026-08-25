# 8E Portal Motion Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 把当前静态 Portal/Account V1 升级为两个同源 poster-first、全帧循环、可访问且可降级的电影场景，
同时保持 Portal 激活前业务 I/O 为零，并让 Portal→Account 导航恰好提交一次。

**Architecture:** 以 typed `CinematicMediaManifest` 和纯 `MediaPolicy` 决定 desktop/mobile 与 motion/poster；
`CinematicSceneMedia` 只管理 poster/video 播放状态，`ProductJourney` 持有跨幕激活状态和唯一导航权。媒体失败
不能改变 Auth、profile、Product State、Memory 或 Runtime Trace。最终 Portal 只消费确认母图的同源输出；
Account 必须先通过 RQ-117 拓扑/抽象门、逐英雄门和 Riot 合规门。

**Tech Stack:** React 19、TypeScript 7、Vite 8、现有 Motion 13、vanilla CSS、Vitest、Playwright、Python 3.11、
FFmpeg/ffprobe；不新增 Three/OGL/GSAP/Anime 或第二媒体 runtime。

---

## Entry gate

本计划只在 ADR-0068、RQ-117/118、设计稿、walkthrough、coverage 和 canonical 状态的独立 design commit 已通过
同一 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke` 后执行。进入 runtime 前确认：

```powershell
cd D:\riftcoach-agent
git status --short --branch
python scripts/check_project_governance.py
git diff --check
```

预期：工作树干净、governance passed、当前 checkpoint 仍是
`8e-productization / portal-motion-polish / authorized / in_progress`。未取得 design exact-SHA 时停止。

## Task 1: 冻结 manifest、viewport 与初始媒体资格

**Files:**

- Create: `web/src/cinematic/mediaManifest.ts`
- Create: `web/src/cinematic/mediaManifest.test.ts`
- Create: `web/src/cinematic/mediaGeometry.ts`
- Create: `web/src/cinematic/mediaGeometry.test.ts`
- Create: `web/src/cinematic/mediaPolicy.ts`
- Create: `web/src/cinematic/mediaPolicy.test.ts`
- Create: `web/src/cinematic/useCinematicMediaPolicy.ts`
- Create: `web/src/cinematic/useCinematicMediaPolicy.test.tsx`

### Step 1: 先写 strict manifest 红灯

冻结：

```ts
type CinematicScene = "portal" | "account"
type CinematicViewport = "desktop" | "mobile"

interface CinematicMediaRendition {
  readonly intrinsicWidth: number
  readonly intrinsicHeight: number
  readonly posterAvif: string
  readonly posterWebp: string
  readonly vp9Webm: string
  readonly h264Mp4: string
  readonly focalPoint: { readonly x: number; readonly y: number }
  readonly hitBox?: {
    readonly x: number
    readonly y: number
    readonly width: number
    readonly height: number
  }
  readonly objectPosition: { readonly x: number; readonly y: number }
}
```

测试必须拒绝缺 scene/viewport、越界 focal/hitbox、空 URL、远程 URL、重复/未知键和 Portal/Account identity
互换。测试 manifest 使用明确的 `test fixture` URL，不得指向 rejected preview。

`mediaGeometry.test.ts` 先冻结 cover scale/crop：intrinsic dimensions、viewport dimensions、objectPosition 与
normalized hitBox 必须产生确定 CSS box；覆盖 1440/1024/390/320 和极端长宽比，button/overlay 共用结果且
误差 <0.5%。

### Step 2: 运行红灯

```powershell
cd D:\riftcoach-agent\web
npm run test:unit -- src/cinematic/mediaManifest.test.ts src/cinematic/mediaGeometry.test.ts
```

预期：FAIL，模块尚不存在。

### Step 3: 写 media policy 红灯

冻结两个分支都携带 viewport：

```ts
type MediaPolicy =
  | { readonly mode: "motion"; readonly viewport: CinematicViewport }
  | {
      readonly mode: "poster"
      readonly viewport: CinematicViewport
      readonly reason: "reduced-motion" | "save-data"
    }
```

覆盖 760px 边界、reduced-motion 优先级、Save-Data、API 缺失、preference/resize listener 更新与 cleanup。

### Step 4: 运行 policy 红灯

```powershell
npm run test:unit -- src/cinematic/mediaPolicy.test.ts src/cinematic/useCinematicMediaPolicy.test.tsx
```

预期：FAIL，模块尚不存在。

### Step 5: 最小实现并绿灯

实现纯 decoder/policy 和 hook。poster-only 从第一次 render 就不得创建 video/source；hook 不读取远程配置，
不写 localStorage。

```powershell
npm run test:unit -- src/cinematic/mediaManifest.test.ts src/cinematic/mediaGeometry.test.ts `
  src/cinematic/mediaPolicy.test.ts src/cinematic/useCinematicMediaPolicy.test.tsx
npm run typecheck
```

预期：全部 PASS。

### Step 6: 小提交

```powershell
cd D:\riftcoach-agent
git add web/src/cinematic/mediaManifest.ts web/src/cinematic/mediaManifest.test.ts `
  web/src/cinematic/mediaGeometry.ts web/src/cinematic/mediaGeometry.test.ts `
  web/src/cinematic/mediaPolicy.ts web/src/cinematic/mediaPolicy.test.ts `
  web/src/cinematic/useCinematicMediaPolicy.ts web/src/cinematic/useCinematicMediaPolicy.test.tsx
git commit -m "feat(web): add cinematic media policy"
```

## Task 2: poster-first 播放状态与 sticky failure

**Files:**

- Create: `web/src/cinematic/mediaSession.ts`
- Create: `web/src/cinematic/mediaSession.test.ts`
- Create: `web/src/components/CinematicSceneMedia.tsx`
- Create: `web/src/components/CinematicSceneMedia.test.tsx`

### Step 1: 写播放状态红灯

状态固定为：

```text
poster → loading → playing
                  ↘ failed-sticky
```

`userPaused: boolean` 与该状态机正交；它只影响 effective play/pause，不允许覆盖 `failed-sticky`。

覆盖：poster-first、WebM→MP4 source 顺序、`autoPlay/muted/loop/playsInline/preload=metadata`、`aria-hidden`、
`disablePictureInPicture`、remote playback 禁用、`canplay` 后才显现、`play()` reject、network/decode error、
迟到 canplay/promise、hidden pause、visible eligible resume、resume reject、user pause/resume 和 unmount cleanup。

### Step 2: 验证红灯

```powershell
cd D:\riftcoach-agent\web
npm run test:unit -- src/cinematic/mediaSession.test.ts src/components/CinematicSceneMedia.test.tsx
```

预期：FAIL。

### Step 3: 最小实现

`mediaSession` 由后续 `ProductJourney` 持有 page-session per-scene state；组件 remount 复用 `failed-sticky` 与
正交的 `userPaused`
且零自动重试，整页 reload 才重置。媒体错误不调用 navigate、Auth API、Memory、Trace 或日志正文。poster
加载也失败时暴露 `data-poster-failed=true`，让场景显示纯色安全背景和可见进入控件。

### Step 4: 绿灯与提交

```powershell
npm run test:unit -- src/cinematic/mediaSession.test.ts src/components/CinematicSceneMedia.test.tsx
npm run typecheck
cd D:\riftcoach-agent
git add web/src/cinematic/mediaSession.ts web/src/cinematic/mediaSession.test.ts `
  web/src/components/CinematicSceneMedia.tsx web/src/components/CinematicSceneMedia.test.tsx
git commit -m "feat(web): add poster first cinematic media"
```

## Task 3: 单次激活与跨幕 overlay

**Files:**

- Create: `web/src/cinematic/portalActivation.ts`
- Create: `web/src/cinematic/portalActivation.test.ts`
- Create: `web/src/components/PortalActivationOverlay.tsx`
- Create: `web/src/components/PortalActivationOverlay.test.tsx`
- Modify: `web/src/components/AwakeningScene.tsx`
- Modify: `web/src/components/AwakeningScene.test.tsx`
- Modify: `web/src/app/App.tsx`
- Modify: `web/src/app/App.test.tsx`

### Step 1: 写状态机与 timer 红灯

覆盖 `idle → activating → committed`，click/Enter/Space/StrictMode 重复触发只 commit 一次，full motion
600–720ms，reduced-motion 立即 commit，偏好在 activation 中改为 reduced 时取消空间动画并 commit 一次，
popstate/unmount/generation change 取消迟到回调。

### Step 2: 写语义红灯

按钮必须：

- 保留 `进入 RiftCoach / Enter RiftCoach` accessible name；
- 激活后用 `aria-disabled` 和内部 latch，不使用会丢焦点的 native `disabled`；
- 透明覆盖画面水晶，至少 44×44 CSS px；
- 不渲染 CSS crystal、orbit、可见按钮 label、大 H1 或 lede；
- poster 失败时改为可见降级控件，forced-colors 下有真实 outline。

### Step 3: 写跨 mount 红灯

`PortalActivationOverlay` 由 `ProductJourney` 持有。opaque 后恰好一次 `navigate(account)`；Portal unmount 后
overlay 继续，Account H1 在 overlay 退出后接焦点。动画 callback 不能产生第二次 `pushState`。

### Step 4: 运行红灯

```powershell
cd D:\riftcoach-agent\web
npm run test:unit -- src/cinematic/portalActivation.test.ts `
  src/components/PortalActivationOverlay.test.tsx `
  src/components/AwakeningScene.test.tsx src/app/App.test.tsx
```

### Step 5: 最小实现、绿灯与提交

```powershell
npm run test:unit -- src/cinematic/portalActivation.test.ts `
  src/components/PortalActivationOverlay.test.tsx `
  src/components/AwakeningScene.test.tsx src/app/App.test.tsx
npm run typecheck
cd D:\riftcoach-agent
git add web/src/cinematic/portalActivation.ts web/src/cinematic/portalActivation.test.ts `
  web/src/components/PortalActivationOverlay.tsx web/src/components/PortalActivationOverlay.test.tsx `
  web/src/components/AwakeningScene.tsx web/src/components/AwakeningScene.test.tsx `
  web/src/app/App.tsx web/src/app/App.test.tsx
git commit -m "feat(web): add one shot portal activation"
```

## Task 4: 媒体审计器与预算门

**Files:**

- Create: `scripts/check_cinematic_media.py`
- Create: `tests/test_cinematic_media_contract.py`
- Create: `docs/assets/8e-portal/cinematic-media-audit-v1.json`
- Modify: `web/package.json`
- Modify: `.github/workflows/tests.yml`

### Step 1: 写 Python 红灯

用临时 manifest 与 stubbed ffprobe JSON 覆盖：

- exact source/output SHA、bytes、dimensions；
- VP9 WebM/H.264 MP4、24fps、YUV420P、BT.709、no-audio、duration、keyframe interval；
- MP4 faststart 与 metadata removed；
- source→首帧 SSIM `≥0.95`、poster→首帧 SSIM `≥0.98`；
- `DSSIM=1-SSIM`，末→首 seam DSSIM `≤ max(1.5 × 相邻帧 DSSIM p95, 0.03)`；
- desktop/mobile/scene 完整矩阵；
- anti-reference 路径/SHA 不进入 manifest/dist；
- Chromium desktop/390 两轮 dropped/total frames `≤1%` 且无非注入 stall；
- JS ≤150,000 B gzip、CSS ≤22,000 B gzip、非媒体冷启动 gzip ≤220,000 B、ADR 分项/总媒体预算及
  Portal/Account/poster-only 实际传输字节。

### Step 2: 红灯

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest tests/test_cinematic_media_contract.py -q
```

### Step 3: 实现只读检查器

检查器接受显式 manifest/path，不联网、不转码、不写源素材；FFmpeg/ffprobe 版本写入 audit，公共 CI 显式验证
命令存在，不能依赖隐藏 Playwright binary。`web/package.json` 只增加本地检查 script，不增加 runtime dependency。

### Step 4: 绿灯与提交

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cinematic_media_contract.py -q
.\.venv\Scripts\python.exe scripts/check_cinematic_media.py --help
git add scripts/check_cinematic_media.py tests/test_cinematic_media_contract.py `
  web/package.json .github/workflows/tests.yml docs/assets/8e-portal/cinematic-media-audit-v1.json
git commit -m "test(web): gate cinematic media assets"
```

## Task 5: 生产 Portal 与 Account 发布资产

进入生产资产前先执行 RQ-119/120 的短片 bake-off：A 线至少两个 first/last/reference 生成模型（优先 Wan/
Seedance/Veo/Luma/Runway 可达项），B 线做 HyperFrames 或 Remotion 分层确定性 spike，C 线做生成式有机
plates + 确定性结构合成。使用同一 source、motion brief、duration 和评分表；没有胜出路线时保持 poster-only，
不为赶进度降低 source/geometry/texture/loop 门。任何 skill 安装先经安全审计；credits/Key/付费调用另行确认。

**Files:**

- Create: `web/src/assets/cinematic/portal-desktop-poster.avif`
- Create: `web/src/assets/cinematic/portal-desktop-poster.webp`
- Create: `web/src/assets/cinematic/portal-desktop-loop.webm`
- Create: `web/src/assets/cinematic/portal-desktop-loop.mp4`
- Create: `web/src/assets/cinematic/portal-mobile-poster.avif`
- Create: `web/src/assets/cinematic/portal-mobile-poster.webp`
- Create: `web/src/assets/cinematic/portal-mobile-loop.webm`
- Create: `web/src/assets/cinematic/portal-mobile-loop.mp4`
- Create: same eight `account-*` renditions only after Account gates pass
- Create before Account adoption: `docs/assets/8e-account/source-provenance-v1.json`
- Modify: `docs/plans/2026-08-24-8e-visual-asset-adoption-ledger.md`
- Modify: `docs/assets/8e-portal/cinematic-media-audit-v1.json`
- Modify: `web/src/cinematic/mediaManifest.ts`

### Step 1: Portal source gate

desktop 输入只能是 SHA `552a87453daae53762f56f0cb5f7c7c2fee18256ef6d193c00575283e9b7aada`
的确认母图。mobile portrait source 必须从该 archival master 单独派生并通过 adopted-source 门，记录新 SHA、
edit/generation provenance 与原水晶/塔体、左 Rift、右星图、曝光锚点审查。Kimi/其他
image-to-video 服务只作为离线制片工具；不接 RiftCoach runtime API，不发送玩家数据。不得用 FFmpeg 静态
缩放、假 parallax 或暗化母图冒充全局 loop。

### Step 2: Account source gate

按顺序阻塞：

```text
annotated official topology overlay
→ intentional-abstraction / no fake precision review
→ flat right-panel safe zone
→ Camille / Kindred / Ahri / Jinx / Thresh per-hero anatomy review
→ composite light/perspective review
→ Riot policy/disclaimer/removal evidence
→ global loop generation
```

当前 v3 是 unaccepted preview；未通过 RQ-117 前不得进入英雄层或成为 source master。
repo provenance manifest 还必须记录 map11/near-final 与五英雄参考的完整 URL/SHA/bytes/version、Riot policy/
disclaimer 状态和 per-layer removal；本地 research 路径不能替代该证据。

### Step 3: 固定编码

从获准 source video 编码 VP9/H.264，使用 24fps、YUV420P、BT.709、无音轨、`-map_metadata -1`、MP4
faststart 和 ≤2 秒 keyframe interval。实际命令与 FFmpeg version 写入 audit；源视频不放进 production dist。

### Step 4: 机械与人工双门

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe scripts/check_cinematic_media.py `
  --manifest docs/assets/8e-portal/cinematic-media-audit-v1.json
cd web
npm run build
```

人工成组查看 Portal/Account 的 desktop/mobile、poster、首尾 loop、reduced/error；阻断性的身份、拓扑、
解剖、许可或可访问性问题必须修复，非阻断偏好进入后序清单。

### Step 5: 资产提交

```powershell
cd D:\riftcoach-agent
git add web/src/assets/cinematic web/src/cinematic/mediaManifest.ts `
  docs/assets/8e-account/source-provenance-v1.json `
  docs/assets/8e-portal/cinematic-media-audit-v1.json `
  docs/plans/2026-08-24-8e-visual-asset-adoption-ledger.md
git commit -m "feat(web): add approved cinematic scene media"
```

## Task 6: Portal/Account/Auth 生产组合与 anti-reference 清除

该 Task 只能在 Task 5 的 Portal 与 Account production manifest/renditions 全部通过后执行；禁止把 test fixture、
404 URL、未签收 candidate 或 rejected preview 接入 App/dist。

**Files:**

- Modify: `web/src/app/App.tsx`
- Modify: `web/src/components/AccountAccess.tsx`
- Modify: `web/src/auth/AuthGate.tsx`
- Modify: `web/src/styles/product-journey.css`
- Modify: `web/src/app/App.test.tsx`
- Modify: `web/src/components/AccountAccess.test.tsx`
- Modify: `web/src/auth/AuthGate.test.tsx`
- Modify: `web/src/app/noNetworkBoundary.test.ts`
- Modify: `web/src/app/packageBoundary.test.ts`
- Modify: `app/api/security.py`
- Modify: `tests/test_security_headers.py`
- Delete after replacement is verified: `web/public/assets/awakening/rift-portal-background-v2.webp`
- Delete after replacement is verified: `web/public/assets/awakening/rift-aperture-plate.webp`

### Step 1: 写 journey/I/O 红灯

- activation commit 前 Auth/profile/Player Link/SSE 请求均为 0；
- Portal stage 不挂 Account video/source，且不请求/预取任何 Account media；
- Account stage 才挂 Account media，并在其上方启动 Auth checking/failure/Profile UI；
- overlay opaque 后 Account poster `load` 或有界 timeout 才退出，避免露出空白背景；
- 返回 Portal 后 Account video 清理；Workbench 不挂 Portal/Account media；
- Auth failure 和 Account 不再复用 Portal 暗图。

### Step 2: 写 CSS/资产/CSP 红灯

扫描生产 DOM/CSS/dist，拒绝旧暗图、aperture、brightness/blur/vignette/全屏暗幕、独立水晶/orbit/大文案、
远程媒体和新动画 runtime。安全头必须显式含 `media-src 'self'`，不放宽其他 CSP source。

### Step 3: 实现组合和 CSS

使用已获准 production manifest 的 `CinematicSceneMedia` 作为 Portal、Account、Auth checking/failure 的 scene
background；DOM 面板保持独立层级，不靠整屏暗幕获得可读性。保留 locale control、安全 skip link、focus 和
现有 Account/Workbench 数据控制流。

### Step 4: 绿灯与提交

```powershell
cd D:\riftcoach-agent\web
npm run test:unit -- src/app/App.test.tsx src/components/AccountAccess.test.tsx `
  src/auth/AuthGate.test.tsx src/app/noNetworkBoundary.test.ts src/app/packageBoundary.test.ts
npm run typecheck
npm run build
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest tests/test_security_headers.py -q
git add web/src web/public/assets/awakening app/api/security.py tests/test_security_headers.py
git commit -m "feat(web): integrate cinematic product journey"
```

## Task 7: Browser 纵向、视觉证据与失败注入

**Files:**

- Create: `web/tests/e2e/cinematic-media.spec.ts`
- Create: `web/tests/e2e/portal-motion-visual-evidence.spec.ts`
- Modify: `web/tests/e2e/awakening.spec.ts`
- Modify: `web/tests/e2e/product-journey.spec.ts`
- Modify: `web/tests/e2e/auth-gate.spec.ts`
- Modify: `web/tests/e2e/locale.spec.ts`
- Modify: `web/tests/support/liveApiServer.mjs`

### Step 1: 写 browser 红灯

覆盖：

- 1440/1024/390/320 与 `zh-CN/en`；
- normal、reduced-motion、Save-Data、media 404、play reject、poster failure；
- reduced/Save-Data 为 0 video requests；Portal commit 前业务 API/SSE 与 Account media 请求为 0；
- click/Enter/Space/重复激活、activation 中 popstate、history/back/forward；
- media failure 经 Account→back 不重试，整页 reload 才建立新 session；暂停/继续控件键盘可达且不改变 URL/
  Auth/Product State，暂停后 video frame 保持、继续后有条件恢复；
- Portal/Account/Workbench 恰好一幕、Account H1 focus、transparent hitbox 对齐；
- computed/runtime 无旧 URL、filter、vignette、blur、暗幕；
- axe critical/serious 0、无 horizontal overflow、forced-colors focus。

### Step 2: 聚焦绿灯

```powershell
cd D:\riftcoach-agent\web
npx playwright test tests/e2e/cinematic-media.spec.ts `
  tests/e2e/portal-motion-visual-evidence.spec.ts `
  tests/e2e/product-journey.spec.ts tests/e2e/awakening.spec.ts `
  tests/e2e/auth-gate.spec.ts tests/e2e/locale.spec.ts
```

人工查看每组截图和 loop；截图有问题先修复再交付，不把已知缺陷截图当证据。

### Step 3: 完整 frontend 门与提交

```powershell
npm run typecheck
npm run test:unit
npm run build
npm run test:e2e
cd D:\riftcoach-agent
git add web/tests web/src web/package.json
git commit -m "test(web): verify cinematic journey"
```

## Task 8: 八维证据、比例回归与 exact-SHA 公共关闭

**Files:**

- Modify: `docs/learning/8e-portal-motion-polish-walkthrough.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: `docs/learning/README.md`
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`

### Step 1: 更新真实结果

把 planned code map、验证数、媒体 SHA/bytes/codec、visual review、失败注入、限制和 runbook 更新为实际证据。
RQ-108 只有在 Portal 与 Account 两幕真实发布资产、媒体/浏览器门、Riot 合规门和八维材料全部完成时才关闭；
代码接缝绿而 Account 媒体缺失时必须保持 `in_progress`。

### Step 2: 完整本地门

```powershell
cd D:\riftcoach-agent\web
npm run typecheck
npm run test:unit
npm run build
npm run test:e2e

cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest tests/test_cinematic_media_contract.py tests/test_project_governance.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_cinematic_media.py `
  --manifest docs/assets/8e-portal/cinematic-media-audit-v1.json
python scripts/check_project_governance.py
git diff --check
```

再按 `.github/workflows/tests.yml` 运行两套 RAG、Harness、compile/secret/tracked-data、真实 PostgreSQL/Alembic
与隔离 Linux package 比例门。外部 Riot/OP.GG/Provider/LLM calls 保持 0；视频生成调用与结果单独记录，不能
混入产品 API 计数。

### Step 3: 独立 implementation/evidence commit

```powershell
git status --short
git diff --cached --check
git commit -m "feat(web): close cinematic portal motion polish"
git push origin main
```

记录精确 commit SHA；等待该 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部
`completed/success`。公共 CI 未全绿前不得把 RQ-108 或八维 coverage 标 complete，也不得进入 bounded Coach、
RQ-103、OP.GG breadth 或 8F。

## 退出标准

- Portal/Account 实际 full-frame loop 均通过机械与人工门；
- Portal 只使用确认母图同源输出，Account 通过 RQ-117、逐英雄与 Riot 合规门；
- reduced-motion/Save-Data 为 0 video requests；媒体失败仍可完成产品旅程；
- Portal commit 前业务 API/SSE=0，Account/Workbench 生命周期无回归；
- 四视口、双语、键盘、focus、axe、overflow、history 全绿；
- 旧暗图、aperture、CSS 水晶、filter/vignette/blur 不在 runtime/dist；
- JS/CSS 与全部媒体满足 ADR-0068 预算；
- 八维证据、本地门、独立 SHA 与 exact-SHA 三 job 全绿。
