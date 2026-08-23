# 8E Batch D Rift Command Center 设计

多来源第二轮研究与五模块采用矩阵见
[`2026-08-23-8e-five-module-visual-resource-research.md`](2026-08-23-8e-five-module-visual-resource-research.md)。

## 1. 初学者教学

### 具体问题

RiftCoach 后端已经能区分玩家档案、任务生命周期、报告发布质量、Evidence 新鲜度和训练计划，但这些
并不是同一种“状态”。如果前端只写一个 `if loading else dashboard`，就会把“任务仍在运行”“报告被
质量门拒绝”“报告可看但证据过期”和“浏览器请求失败”混为一谈。漂亮的页面也可能因此说谎。

Batch D 先建一个 fixture-backed 近期复盘工作台。fixture 像电影拍摄用的安全样片：字段形状严格按
产品 DTO，但不访问真实用户、Riot、OP.GG、Provider 或数据库。这样能先验证信息层级、视觉语言、状态、
键盘和移动端，再在后续批次接真实 API。

### Agent / 软件原则

1. **契约先于界面**：UI 消费 allowlisted projection，不读取底层对象或原始外部响应。
2. **状态分层**：客户端资源状态描述“浏览器拿没拿到数据”，产品状态描述“结果能否以何种限制展示”。
3. **渐进增强**：文字、语义结构和焦点顺序先完整；动效与环境层增强体验，但关闭后不损失信息。
4. **采用门而非素材崇拜**：先排除不适合的来源，再在适合者中追求最高视觉完成度。

### 本批做与不做

做：独立 React/Vite/TypeScript 包、design tokens、自制 Hextech/Rift 环境层、fixture 合同、近期复盘
工作台、Evidence Drawer、Training 摘要、四态/客户端状态、桌面/移动/键盘/reduced-motion 自动验证和
人工截图 QA。

不做：真实 API/SSE/Auth、完整 Timeline/历史列表、Riot ID 创建流程、Markdown raw HTML、ECharts、
入口视频/粒子/WebGL、HTTPS、备份、部署、公网页面或 Stage 8F README 美化。

## 2. 页面信息架构

### 2.1 桌面骨架

```text
┌ Command rail ┬──────────────── Review workspace ────────────────┬ Context rail ┐
│ brand/core   │ player + region + fixture disclosure + status  │ training     │
│ review       │ state notice / lifecycle                       │ evidence CTA │
│ evidence     │ recent form metrics                            │ source stack │
│ training     │ match capsules + tactical coach brief          │              │
└──────────────┴──────────────────────────────────────────────────┴──────────────┘
```

- Command rail 是导航和品牌锚点，不做假多页面 router；锚点链接到本页真实区域。
- 主区顶部先回答“分析谁、哪个地区、是什么模式、结果能否展示”，再展示指标和 Coach brief。
- Context rail 只放 Training 概览和 Evidence 入口；完整来源/冲突/缺口在 Drawer 中展开。
- 页面显式显示 `Fixture preview`，避免把合成样片冒充实时账号结果。

### 2.2 移动骨架

`>=1280px` 使用三栏；`960–1279px` 使用窄 Command rail + 主区，Context 模块移到主区下方两列；
`<960px` 改为单列和水平 section nav；`<560px` 主指标全宽、次指标两列；`<360px` 全部单列。
没有 hover-only 行为，Evidence Drawer 在手机改为接近全屏但仍保留可见标题和关闭按钮。

## 3. 视觉系统

### 3.1 设计 tokens

| token 族 | 决策 |
|---|---|
| surface | `obsidian-950`、`navy-900`、半透明 `navy-800`；避免纯黑平面 |
| structure | `hex-cyan-400/500`，用于路径、焦点和 active navigation |
| coach | `coach-gold-300/500`，只用于 Coach、published 与关键完成信息 |
| meta | `meta-violet-400`，只用于 OP.GG/unknown provenance，不作通用 AI 紫色渐变 |
| risk | `rift-red-400`，只用于 rejected/真实风险 |
| type | Oxanium display + Manrope body；长报告不使用 display font |
| radius | 6/10/16/24px；面板外轮廓偏切角，内容 control 保持可触达圆角 |
| spacing | 4px 基线，常用 8/12/16/24/32/48 |
| motion | 160ms feedback、320ms state、900ms atmosphere；统一 easing tokens |

### 3.2 可记忆的视觉时刻

页面唯一主视觉是自制 Rift field：低对比 SVG 等高线、三路能量路径、战争迷雾 mesh 与 Coach Core。
指针只改变局部 radial focus，键盘焦点有等价边缘光；移动端保留静态层。页面进入时，环境层、标题、
状态和数据按一次编排顺序揭示，之后工作台保持稳定，不让每张卡持续闪动。

卡片不使用模板化玻璃拟态堆叠。Evidence/Coach 卡可有克制的青蓝或金色能量边缘；degraded/rejected
改变文字、图标、标签和说明，不对指标做 glitch。LoL 识别来自 Lane、版本、英雄/比赛语义、Rift 路径
与来源标签，不复制 LoL 客户端皮肤。

## 4. 前端合同与 fixture

```text
WorkbenchScreenState
├─ client: loading | empty | ready | error
└─ data? ReviewWorkbenchFixture
   ├─ selectedProfile
   ├─ task
   ├─ productState
   ├─ summary?
   ├─ run?
   ├─ report?
   ├─ evidence?
   ├─ events[]
   └─ training?
```

fixture 提供 `published`、`degraded`、`rejected`、`not_ready`、`loading`、`empty` 和 `error` 场景。
默认 `published` 使用完全合成的 `Riverline#EUW`，另有 `public_observed` 档案验证“观察对象不显示我的训练
完成度”。场景通过 `?scenario=` 选择，仅用于静态 QA；未知场景安全回到 error，不静默显示 published。

`RecentSummaryView` 当前没有 FastAPI endpoint，因此 fixture 只按其 safe allowlist 手工塑形。原始
`examples/fixtures/player_summary_demo.json` 不可整体导入浏览器。Evidence projection 只实现本批需要的
V1 安全子集；后续接 API 前仍需 runtime decoder 或收紧 HTTP DTO。

## 5. 组件职责

| 组件 | 职责与边界 |
|---|---|
| `RiftAtmosphere` | 自制 SVG/CSS 环境层；`aria-hidden`，reduced-motion 静态 |
| `CommandRail` | 品牌、section navigation、fixture disclosure；不伪装 router |
| `ProfileSelector` | 切换合成 self/observed 档案；显示 region/relationship/verification |
| `ProductStateBanner` | 四态文字、icon、reason 与限制；最终颜色来自 ProductState，而非 runtime completed |
| `RecentFormPanel` | 安全 Summary 指标、无顺序胜负占比、Wins vs Losses 聚合对照、主位置/英雄文字标签；无逐局卡片或假 Timeline |
| `CoachBrief` | 展示 verified fixture brief；rejected 时不读取/显示报告 |
| `TrainingPanel` | self 显示计划/进度；observed 改为只读“学习观察”说明 |
| `EvidenceDrawer` | Radix Dialog 焦点管理；展示 source/join/gap/digest，不展示隐藏推理 |
| `ScenarioBoundary` | loading/empty/error 与产品四态分层；未知/非法 fixture fail closed |

## 6. 数据与控制流

```text
URL ?scenario=
  → allowlisted scenario parser
  → immutable typed fixture
  → recursive forbidden-field assertion (test/build evidence)
  → client-state boundary
  → product-state banner
  → summary / coach / training / evidence projections

pointer / keyboard / prefers-reduced-motion
  → presentation state only
  → never changes fixture or product truth
```

档案切换只切换本地 fixture 关系视图，不生成 task、不读账号、不冒充 owner 选择已经持久化。Drawer 的
打开/关闭也只是客户端展示状态；Evidence digest 和 disposition 始终来自 fixture。

## 7. 失败与安全行为

| 情况 | 行为 |
|---|---|
| loading | 保留页面骨架与档案区域，不短暂闪现 published |
| empty profiles | 明确“尚无玩家档案”与未来动作，不写“系统错误” |
| not_ready | 展示 queued/running/recovery reason 和真实事件，不伪造百分比 |
| degraded | 报告可显示，但顶部限制条和 Evidence gap 同时可见 |
| rejected | 隐藏 Coach report，区分 cancel/execution/quality reason |
| client error | 显示安全 code 和重试占位；不把产品状态改成 rejected |
| invalid fixture | 测试/开发时 fail closed；不渲染潜在私有字段 |

Markdown 本批用已写死的安全 React 结构，不引入 raw HTML renderer。任何后续 Markdown 库必须重新审查
HTML/link sanitization。

## 8. 验证矩阵

- Vitest：scenario parser、四态矩阵、observed training 边界、Evidence Drawer、forbidden fields、unknown
  scenario 与报告隐藏；
- TypeScript/build：严格类型、无未使用字段、production bundle 成功；
- Playwright desktop：1440×1000 页面层级、Drawer focus/Esc/return focus、无横向溢出；
- Playwright responsive：1440 三栏、1024 tablet 重排、390×844 单列、320 最窄宽度，nav/control 可触达且
  Drawer 不越界；1920 超宽内容保持最大宽度；
- reduced-motion：emulated media 下 environment/transform 动效关闭，信息仍可见；
- accessibility：landmark/heading/name/role、Tab 顺序、focus-visible、颜色非唯一信号与 axe critical/serious 0；
- visual QA：实际查看 desktop/mobile/published/degraded/reduced-motion 截图，发现问题先修再保存证据；
- 仓库门：现有完整 pytest、RAG/Harness、compile、secret/tracked-data、governance、diff 与 exact-SHA
  public CI 保持通过。

## 9. 当前限制与面试表述

可以说：

> 我先把后端产品状态与浏览器资源状态分层，用严格 fixture 建立 React 近期复盘工作台；设计系统通过
> 多来源采用门筛选，在许可、性能和无障碍硬门之后主动优化视觉完成度，并用 Playwright 验证桌面、
> 移动、键盘和 reduced-motion。

不能说：页面已连接真实 Riot/OP.GG、SSE、Auth，已支持完整 Timeline/运行历史，或已经生产部署。
