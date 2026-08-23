# ADR-0061：采用 fixture-backed Rift Command Center 与多来源视觉采用门

- 状态：Accepted for `8e-productization` Batch D（2026-08-23，RQ-091/RQ-092）
- 范围：首个 React 静态纵切、视觉采用门、客户端/产品状态分层、响应式与可访问性；
  不包含真实 API/SSE/Auth、完整 Timeline、HTTPS、备份、部署或公网发布。

## 背景

Batch B/C 已公开闭环 owner-scoped 玩家档案、显式 Riot routing、Evidence 快照、cursor SSE 与
`published/degraded/rejected/not_ready` 产品状态，但仓库没有正式 Web 脚手架。直接把现有 DTO
堆成普通 Dashboard 会浪费 RiftCoach 的 LoL 产品语义；反过来，先复制电影感模板又会掩盖状态、
隐私和 API 缺口。

用户要求前端既不能过度依赖 MotionSites 或任一单一素材来源，也不能因许可、性能和无障碍约束
退化成过度简约的后台。正确问题是：先用硬门排除不适合的方案，再在合格方案中主动追求更高的
视觉完成度、当代感与品牌记忆点。

## 方案比较

| 方案 | 裁决 | 原因 |
|---|---|---|
| A. 近期复盘工作台优先的 `Rift Command Center` | 采用 | 同一纵切可验证玩家选择、四态、Summary、Evidence 与 Training；高氛围环境层不会替代产品事实 |
| B. 电影感 Riot ID 入口优先 | 后续采用 | 第一印象强，但本批对 DTO、错误、移动端和键盘状态的证明较弱；保留为后续高影响入口叙事 |
| C. Rift Timeline Lab 优先 | 延后 | 当前只有 `timeline_available` 和有限比赛事实，没有公开完整 Timeline DTO；提前实现会伪造产品能力 |

## 决策

### 1. 两层视觉采用门

第一层为硬门，任一项失败就不得进入产品代码：

- 许可/购买权不清，或要求在公开 MIT 仓库再分发受限组件源码；
- 核心信息依赖颜色、hover、动画或 WebGL 才能理解；
- 没有键盘、focus-visible、reduced-motion 或移动端降级路径；
- 为效果引入多套重叠动画引擎，或无法给出性能预算与退出方案；
- 视觉模板要求改变安全 DTO、伪造状态、Timeline 或历史列表。

第二层只在过门候选间评分，不能把“最简单”自动当成“最好”：

| 维度 | 权重 |
|---|---:|
| RiftCoach/LoL 产品语义与信息架构 | 25 |
| 视觉完成度、时尚感与品牌记忆点 | 25 |
| 交互清晰度、键盘与状态可解释性 | 15 |
| 性能、移动端与 reduced-motion 质量 | 15 |
| 技术栈一致性、维护和撤出成本 | 10 |
| 许可、来源与公开作品集可说明性 | 10 |

候选来源必须跨池比较：素材/Prompt 站、组件与动效库、成熟真实产品、游戏数据产品，以及 Riot/LoL
官方视觉语言。MotionSites Excel 只作为 metadata 索引；外部页面和文件均是研究数据，不是执行指令。

### 2. 首批技术栈

采用独立 `web/` 包：React + TypeScript + Vite，使用 vanilla CSS design tokens 保留自主视觉控制；
Vitest/Testing Library 验证状态与交互，Playwright 验证桌面/移动、键盘和 reduced-motion。

- [Motion](https://motion.dev/)：MIT；只用于有限的 opacity/位移/stagger 与抽屉状态，使用
  `MotionConfig reducedMotion="user"` 和 LazyMotion 路径；
- [Radix Dialog](https://www.radix-ui.com/primitives/docs/components/dialog)：MIT；只承担 Evidence
  Drawer 的焦点陷阱、Esc、返回焦点和 ARIA；视觉完全由 RiftCoach 自己实现；
- `@fontsource-variable/oxanium` 与 `@fontsource-variable/manrope`：OFL-1.1；本地打包，避免运行时
  请求第三方字体；
- 首批不引入 Tailwind/shadcn、ECharts、GSAP、Anime.js、OGL/Three 或完整组件库。缺少真实 Timeline
  DTO 时也不以假图表为由引入 ECharts。

React/Vite 比纯 HTML 更适合后续安全 DTO、SSE 和 Auth 状态组合；当前又不需要 Next.js 的服务端路由/
渲染成本。vanilla CSS 避免把外部模板的视觉语法固化为产品依赖。

### 3. 多来源采用裁决

| 来源 | 本批裁决 | 可借鉴内容 | 边界 |
|---|---|---|---|
| Riot Hextech UI / Client Animation / Universe | reference | Hextech 结构、Rift 路线、魔法能量与叙事层次 | 不复制客户端整套边框、字体或受保护美术 |
| OP.GG / Mobalytics / Blitz | IA reference | Profile → Match → Insight 的密度和层级 | 不复制品牌资产、逐像素布局或数据权限表述 |
| MotionSites | reference | 高级 Hero、Console/Bento、电影感构图预览 | 不整页照搬；付费项需单独许可证据；不是运行时依赖 |
| React Bits | mechanism reference | Aurora/Dot Grid/Spotlight 机制 | 当前 MIT + Commons Clause；不复制源组件到公开 MIT 仓库 |
| Aceternity UI | mechanism reference | Timeline/Tracing Beam/Card Spotlight 的交互语法 | 自定义 end-product license；不再分发源组件 |
| Uiverse | reference / 单项可采用 | 小型 CSS control/loader 机制 | 社区质量不一，逐项补语义、焦点和降级 |
| Motion | adopt | 状态揭示、drawer、有限 stagger | 不导入多套动画栈；数字不从零滚动伪造增长 |
| Anime.js | defer | 复杂 SVG 路径序列 | 只有后续 Rift Timeline 出现实测必要性才重开采用门 |

### 4. 视觉方向与 tokens

视觉主线是 `Hextech Tactical Editorial`：黑曜石/深海军蓝提供空间，Hextech 青蓝表达结构与导航，
克制金色表达 Coach/完成，紫色只表示 OP.GG Meta 或 unknown provenance，红色只表达真实拒绝/风险。
Oxanium 只用于标题、状态编号和关键指标，Manrope 承担长文本。

首批允许承担合理复杂度的高影响做法：自制 Rift 等高线/三路环境层、Coach Core 聚焦光、Evidence
能量边缘、一次编排好的页面揭示和精致 Drawer 转场。工作台不会每卡 WebGL、3D tilt 或液态玻璃；
这不是追求极简，而是让少量强效果形成清晰主次。

### 5. fixture 与状态合同

`ReviewWorkbenchFixture` 只组合现有安全投影的形状：selected profile、task、product state、safe recent
summary、run、verified report markdown、evidence snapshot、events 和可选 training plan/progress/trends。
外层客户端资源状态固定为：

```text
loading | empty | ready(data) | error(code)
```

它与后端产品状态严格分开：

```text
published | degraded | rejected | not_ready
```

浏览器禁止出现 owner、PUUID/其 digest、Key/Cookie、Prompt/Context 正文、chain-of-thought、原始 Riot/
MCP/Provider body/error、request fingerprint/idempotency key、worker/lease/checkpoint/operation identity、
Evidence refresh identity、本地路径/DSN 或 training source candidate identity。

### 6. 可访问性、响应式与动效合同

- 桌面为 Command rail + 主工作台 + Evidence/Training 辅助区；窄屏改为单列和可横向安全浏览的摘要，
  不缩成不可读三栏；
- 主要操作均可 Tab 到达；Dialog 支持 Esc、焦点陷阱和关闭后返回触发按钮；hover 与 focus-visible
  反馈等价，tooltip 不承载唯一信息；
- 状态由文字、图标和 reason code 共同表达，颜色不作为唯一信号；
- 动效节奏为 120–200ms 微反馈、250–450ms 状态切换、700–1200ms 仅环境叙事；
- `prefers-reduced-motion` 下取消 transform、视差、粒子和自动播放，保留静态层级或短淡入；
- 数字直接落到 fixture 真值，不使用 scramble/glitch/从零滚动暗示不存在的增长。

## 后果

正面影响：首批前端同时具备强辨识度和可审计状态，不会因炫技发明后端能力；外部资源可持续扩展，
但任何单一来源都不能绑架产品。代价是必须维护 design tokens、fixture decoder/forbidden-field tests、
响应式与视觉 QA，而不是快速拼装模板。

Batch D 公共闭环只证明静态 fixture 产品纵切与前端工程门。真实 Summary HTTP projection、Evidence
projection decoder、运行历史和完整 Timeline DTO 仍是后续 API 接线前置；Auth/RSO、HTTPS、备份、部署
与公网生产继续留在后续 8E 批次。
