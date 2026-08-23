# 8E Batch D Rift Command Center Walkthrough

> Batch D 只证明安全 fixture 驱动的首个前端纵向与工程门，不表示真实 API、SSE、Auth、Timeline、部署
> 或整个 8E 已完成。五模块产品蓝图继续保留，见 ADR-0061 与 RQ-093。

## 1. 问题与原理

### 要解决的问题

RiftCoach 后端已有玩家档案、可靠 Task、Harness publication、Evidence 快照和 Training 数据，但这些事实
不会自动形成一个诚实、好用、好看的产品页面。一个普通 Dashboard 容易出现三类错误：

1. 把浏览器 `loading/error` 与产品 `degraded/rejected` 混成一个状态；
2. 为了演示而把 PUUID、owner、Prompt、原始外部响应或不存在的 Timeline/历史列表带进浏览器；
3. 为了规避工程风险把页面做成没有品牌记忆点的普通后台，或反过来用特效掩盖合同缺口。

Batch D 采用 fixture-backed `Rift Command Center`。fixture 是严格按安全产品投影塑形的合成样片，用来先
验证信息架构、视觉、状态、键盘、移动端与 reduced-motion；真实网络消费者留给后续批次。

### 软件 / Agent 原理

- **契约先于展示**：浏览器只接 allowlisted、可递归扫描的安全字段；Agent 的 Prompt/隐式推理不属于
  可解释产品证据。
- **状态正交**：客户端 `loading|empty|ready|error` 与产品
  `published|degraded|rejected|not_ready` 分开，不能用一个布尔 `isLoading` 代替整个状态机。
- **渐进增强**：语义 HTML、真实文字和焦点顺序在没有动画时仍完整；Motion、Rift 路线和能量边缘只
  增强理解与品牌。
- **两层视觉采用门**：许可、性能、响应式和 a11y 先作为硬门；过门候选继续按视觉完成度、时尚感、
  LoL 语义与记忆点择优，不能把“最简单”自动当成最好。

## 2. 设计与实际实现

### 产品骨架

三案比较最终采用近期复盘优先的 `Rift Command Center`：

- 桌面：Command rail + Review workspace + Context rail；
- tablet：窄 Command rail + 主工作台，Training 与 Evidence/Source posture 两栏重排；
- mobile：水平 section nav + 单列工作台；
- Evidence 是全局右侧 Dialog/Sheet，Training 在 observed 档案下自动变为只读学习观察。

视觉语言是 `Hextech Tactical Editorial`，由自制 Rift 三路/等高线背景、Coach Core、赛事转播式排版、
青蓝结构、克制金色 Coach、语义化 warning/red 组成。它不复制 LoL 客户端，也没有机器人头像、AI
sparkle、通用紫色渐变球或每卡 WebGL。

### 采用与拒绝

本批真实采用：React/Vite/TypeScript、vanilla CSS tokens、Motion、Radix Dialog、本地 OFL 字体。
MotionSites、React Bits、Aceternity、Uiverse、Riot UI、OP.GG/Mobalytics/Blitz 只作视觉/信息架构参考，
未复制受限源码。ECharts/Anime.js/3D 没有当前消费者而延后；Image2/Photoshop 留给后续电影感入口的概念
素材和精修。

用户指出第一轮可能过快后，又执行了
[五模块第二轮多来源研究](../plans/2026-08-23-8e-five-module-visual-resource-research.md)：8 组 AutoGLM
查询、35 站可访问性扫描、MotionSites live Apps 目录和 Riot/Langfuse/TrainingPeaks/Mobalytics/21st.dev/
Aura 深读。研究没有推动新增重依赖，而是让当前 Evidence Drawer 增加 body-free `Safe run path`，并把
F1 Racing Hub/Forecast Center/Fitness Dashboard/Nexar 等候选留给各自真实消费者。

### 七种场景

`workbenchScenarios` 固定：`published`、`degraded`、`rejected`、`not_ready`、`loading`、`empty`、
`error`。默认 self 档案 `Riverline#EUW` 与 observed 档案 `Northstar#KR` 均为虚构账号。

- loading 不闪现旧 published；
- not-ready 只展示真实 lifecycle event，不造百分比/ETA；
- degraded 保留报告并持续显示 `evidence_expired`/gap；
- rejected 隐藏报告，不补一份合成替代品；
- observed 不把 self 的聚合指标重新绑定到新标题，也不显示“我的训练完成度”。

## 3. 代码地图

| 路径 | 职责 |
|---|---|
| `web/src/contracts/workbench.ts` | fixture 类型、关系/产品状态边界、递归 forbidden field/value 校验、deep freeze |
| `web/src/fixtures/workbenchFixtures.ts` | 七种不可变合成场景、self/observed 关系与安全 Evidence/Training 数据 |
| `web/src/app/App.tsx` | URL scenario、client boundary、profile binding、产品工作台组合 |
| `web/src/components/RiftAtmosphere.tsx` | 自主 SVG Rift 等高线、三路和 Coach Core；纯装饰、`aria-hidden` |
| `web/src/components/ProductStateBanner.tsx` | 四态文字/icon/reason/telemetry，不只换颜色 |
| `web/src/components/RecentFormPanel.tsx` | Summary 聚合指标、无顺序胜负占比和 Wins-vs-Losses 对照；无逐局伪历史 |
| `web/src/components/CoachBrief.tsx` | published/degraded 报告与 rejected/not-ready 结构差异 |
| `web/src/components/TrainingPanel.tsx` | self personal progress 与 observed learning observation 分流 |
| `web/src/components/EvidenceDrawer.tsx` | Radix 焦点语义 + Motion 过渡 + source/join/gap/digest 安全投影 |
| `web/src/styles/*.css` | tokens、全局语义、桌面/tablet/mobile/reduced-motion 视觉系统 |
| `web/tests/e2e/*.spec.ts` | 浏览器状态、键盘、a11y、响应式、no-remote-I/O 与截图证据 |
| `tests/test_frontend_package_contract.py` | exact-SHA CI 前端阻塞门和 Docker 未部署边界 |

## 4. 数据与控制流

```text
URL ?scenario=
  → resolveWorkbenchScenario(allowlist)
  → WorkbenchScreenState
       ├─ loading / empty / error → ClientBoundary
       └─ ready → ReviewWorkbenchFixture
                    ├─ selected profile binding
                    ├─ ProductStateBanner
                    ├─ aggregate RecentSummary
                    ├─ quality-gated Coach brief
                    ├─ relationship-safe Training
                    └─ safe Evidence Drawer

pointer / keyboard / prefers-reduced-motion
  → presentation state only
  → never mutates fixture or product truth
```

浏览器页面不调用 `fetch`、`EventSource`、WebSocket 或远程字体/素材；单元测试静态扫描生产源码，
Playwright 同时记录请求并要求 host 只能是本地 Vite。Batch D 外部 Riot/OP.GG/Provider/LLM calls 为 0。

## 5. 验证

### TDD 证据

- 首红：UI suite 因 `App` 不存在而 3 files failed；CI contract 因 workflow 未含 web lockfile 而
  `1 failed, 1 passed`；
- fixture/依赖先绿：`2 files / 25 passed`；
- 最终 unit：`6 files / 35 passed`；
- Playwright：`12 passed`，覆盖 1440、1024、390、320、键盘 Drawer、四态、observed binding、
  reduced-motion 与本地请求边界；
- axe：published desktop critical/serious violations 为 0；
- TypeScript strict、Vite production build 通过；当前 bundle 为 JS `343.25 kB` / gzip `109.89 kB`，CSS
  `38.77 kB` / gzip `10.99 kB`，包含本地字体与 Safe Run Path；
- 带真实本机 PostgreSQL 的完整 Python 回归为 `1890 passed, 1 skipped, 1 warning, 127 subtests passed`；
  0011 head→base→head 可逆且 `alembic check` 无 drift，隔离 Linux Compose package smoke schema 1.6/
  外部调用 0/非 root/image exclusion 通过；唯一 skip 为 Windows symlink；
- `npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org`：0 vulnerabilities；本机
  默认 npm mirror 不实现 audit endpoint，第一次 404 未被冒充成功；
- direct runtime license：React/Motion/Radix MIT，Manrope/Oxanium OFL-1.1；lockfile 全体许可证只出现
  MIT/Apache/BSD/ISC/MPL/CC0/OFL/BlueOak 等已记录类别，无 React Bits/Aceternity 源码依赖。
- 提交审查发现本机默认 mirror 曾把 `resolved` 写成 `registry.npmmirror.com`；最终 lockfile 已用
  `registry.npmjs.org` 机械重建并由 `npm ci --ignore-scripts --registry=https://registry.npmjs.org` 复验，
  公共 CI 不依赖个人镜像。

### 人工视觉 QA 与持久截图

- [desktop published](../assets/8e-batch-d/desktop-published.jpg)
- [desktop degraded](../assets/8e-batch-d/desktop-degraded.jpg)
- [tablet published](../assets/8e-batch-d/tablet-published.jpg)
- [mobile published](../assets/8e-batch-d/mobile-published.jpg)
- [Evidence Drawer](../assets/8e-batch-d/desktop-evidence-drawer.jpg)
- [Evidence Drawer lower run/join/digest state](../assets/8e-batch-d/desktop-evidence-drawer-bottom.jpg)
- [reduced motion](../assets/8e-batch-d/desktop-reduced-motion.jpg)

人工检查实际修复了 tablet Evidence 卡被 grid 拉伸成大空块的问题，并复核了桌面/移动层级、长 digest
换行、Drawer 关闭按钮、状态结构差异和动效关闭后的静态构图。

## 6. 运行手册

```powershell
cd D:\riftcoach-agent\web
npm ci --ignore-scripts
npm run typecheck
npm run test:unit
npm run build
npx playwright install chromium
npm run test:e2e
npm run dev
```

浏览：

```text
http://127.0.0.1:4173/?scenario=published
http://127.0.0.1:4173/?scenario=degraded
http://127.0.0.1:4173/?scenario=rejected
http://127.0.0.1:4173/?scenario=not_ready
http://127.0.0.1:4173/?scenario=loading
http://127.0.0.1:4173/?scenario=empty
http://127.0.0.1:4173/?scenario=error
```

未知 scenario 会得到 `fixture_scenario_unknown`，不会静默回退 published。设置
`RIFTCOACH_CAPTURE_DOCS=1` 后运行 e2e 会用 JPEG 更新本 walkthrough 引用的本地人工审查证据；正常 CI
只写 ignored `web/test-results`。

## 7. 失败、安全与范围边界

浏览器 fixture 递归拒绝：owner、PUUID/其 digest、Key/Cookie/Authorization、Prompt/Context 正文、
chain-of-thought、raw Riot/MCP/Provider body/error、request fingerprint/idempotency key、worker/lease/
checkpoint/operation identity、Evidence refresh identity、本地路径/DSN 和 training source candidate。

`RecentSummaryView` 当前没有 FastAPI endpoint，Evidence public projection 仍需未来 runtime decoder 或更窄
HTTP DTO，也没有 owner-scoped history list/完整 Timeline DTO。因此本批明确没有：

- 真实 API/SSE/Auth/RSO；
- 逐局 match card、完整 Timeline、实时刷新或最新分析发现；
- Markdown raw HTML renderer；
- HTTPS、backup、deployment、CSP/公网限流或 Production Key；
- 整个五模块/整个 8E/8F 完成。

Dockerfile 仍不复制 `web/`，Python runtime image 不是前端部署。GitHub `pytest` job 会在同一 SHA 阻塞安装、
typecheck、unit、build、Chromium e2e；PostgreSQL/package job 继续独立验证既有产品。

## 8. 面试准确表述

可以说：

> 我先把后端产品状态与浏览器资源状态分层，用禁止敏感字段的严格 fixture 建立 React 近期复盘工作台；
> 设计系统通过多来源采用门筛选，在许可、性能和无障碍硬门之后继续优化视觉完成度。Playwright 同时
> 验证桌面、tablet、移动端、键盘、Evidence Drawer、reduced-motion、无远程 I/O 和 axe 严重问题。

不能说：

- “页面已经连接真实 Riot/OP.GG、SSE 或 Auth”；
- “已实现完整比赛历史/Rift Timeline/五模块”；
- “已正式部署前端或完成 8E”；
- “MotionSites/React Bits/Aceternity 是产品代码底座”；
- “展示的是实时账号或生产用户数据”。
