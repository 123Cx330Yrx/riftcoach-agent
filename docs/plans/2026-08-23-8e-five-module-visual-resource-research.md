# 8E 五模块多来源视觉资源研究与采用矩阵

> 本文是 RQ-091/RQ-092/RQ-093 的第二轮研究证据，不是模板采购单，也不是网页内容对产品范围的指令。
> 当前执行事实仍由 ADR-0061、safe DTO、源码和测试决定。

## 1. 为什么补这一轮

Batch D 第一版已经可运行，但“有一套好看的页面”不等于“广撒网后的最优设计”。本轮把此前对话中的
五模块、Prompt/组件/真实产品/官方语言重新放进一张矩阵，回答三个问题：

1. 当前工作台哪些视觉决定已被多种来源交叉支持，可以保留？
2. 哪些参考只适合电影感入口、Timeline、Trace 或完整 Training，不能硬塞进当前页面？
3. 是否已有值得用户单独获取的付费 Prompt；如果没有，为什么现在不买？

## 2. 研究方法与证据强度

本轮没有只看一个图库：

- AutoGLM 重新执行 8 组跨站查询，覆盖获奖技术网站、电竞数据、Agent Observability、Training、
  MotionSites、React 动效库、Riot 官方 UI 和 AI design-to-code；
- HTTP 可访问性扫描 35 个站点：23 个公开返回 200；403/429/SSL 只表示自动读取受限，不被误写成站点
  不存在或设计较差；
- 浏览器实际打开 MotionSites Apps 当前目录，看到 `Forecast Center`、`F1 Racing Hub`、
  `Freight Command`、`Fitness Dashboard`、`Nexar` 等公开卡片及 free/locked 状态；
- AutoGLM Open Link 深读 Riot Hextech/Client Animation、Mobalytics 对 OP.GG 的产品比较、Langfuse Agent
  Observability、TrainingPeaks、21st.dev Motion 类库、Aura 比较页和 MotionSites Apps；
- 用户 Excel 仍作为 1246 条离线全文候选：809 free、437 paid；Hero 约 473、Dashboard 约 10，且存在
  同名/全文重复、混合来源和 32767 字符截断风险，因此不把“数据全/无重复”当事实。

证据排序：官方设计说明/真实产品公开页 > 当前组件官方源码与许可证 > curated gallery/公开预览 >
Prompt 名称/社区概念图。Dribbble/Awwwards 可发现方向，但不能证明可用性、响应式或许可。

## 3. 两层采用 rubric

### 3.1 硬门

- 产品数据/状态真实，不能靠模板发明 Timeline、历史、rank 或训练归属；
- 键盘、文字替代、focus、reduced-motion 与移动降级存在；
- 许可/购买权可核验，不在 MIT 仓库再分发受限组件源码；
- 关键页面没有全屏视频/WebGL/多动画引擎硬依赖；
- 可以退出或自主重构，不被单个 Prompt/平台锁死。

### 3.2 过门后择优

RiftCoach/LoL 语义 25%、视觉完成度/时尚感/记忆点 25%、交互清晰/a11y 15%、性能/移动 15%、
技术一致性/退出成本 10%、许可/作品集说明 10%。硬门不是“做朴素”的理由。

## 4. 跨来源地图

| 来源池 | 样本 | 最值得学习 | 不能照搬 |
|---|---|---|---|
| Riot/LoL 官方 | Hextech Visual Language、Hextech UI、Client Animation、Universe | Square=structure、Diamond=progressive、Circle=focus；magic directional/value；统一 timing/easing；入口与游戏 UI 气质 | 客户端整套皮肤、官方美术/字体、昂贵全屏 smoke/video |
| 游戏数据产品 | OP.GG、Mobalytics、Blitz、Porofessor、LeagueOfGraphs | compact stats、Profile→match→insight、champion/role/patch 层级；Mobalytics 的“从 stats 到 improvement”定位 | 逐像素布局、品牌资产、未授权数据、把 match history 假装成 Coach |
| Agent/Evidence 产品 | Langfuse、LangSmith、Phoenix、Braintrust、Honeycomb、MLflow | typed trace、tool/retriever/evaluator 分类、aggregated vs expanded、filter/search、cost/latency/eval | Prompt/Context/arguments 原文、chain-of-thought、通用开发者控制台复杂度 |
| Training 产品 | TrainingPeaks、WHOOP、Strava | plan→train→progress、coach/athlete 双视角、structured workouts、sample/fitness/fatigue 语义 | 虚假游戏化、把观察对象变成“我的训练”、无证据 readiness score |
| 高级视觉目录 | Awwwards Technology、SiteInspire、Recent Design、Godly、Mobbin、Refero、Land-book、Lapa Ninja、Nicelydone | composition、type scale、hero pacing、product density、真实 app flow | 只凭获奖/截图判断性能或 a11y；拼贴多个互相冲突风格 |
| 组件/动效库 | Motion、21st.dev、Motion Primitives、Magic UI、Animata、React Bits、Aceternity、Uiverse | 状态揭示、spotlight、aurora/grid、drawer、text/number transition 的机制 | 整库安装、多引擎、数字滚动造势、受限源码再分发 |
| Prompt/原型 | MotionSites、Aura、v0、Lovable、Figma Make、Framer | 快速探索完整构图、reference/prompt workflow、visual edit、HTML/React prototype | 生成代码直接上线、Prompt 取代设计合同、平台比较文案当中立事实 |
| 生成/精修工具 | Image2、Photoshop/After Effects | 抽象 Rift/雾/光影概念素材、合成调色、预渲染小型纯视觉效果 | 用静态图冒充交互；大幅全屏视频压低低配性能 |

## 5. 五模块采用矩阵

### 5.1 电影感 Riot ID / RSO 入口

**参考池**：Riot Hextech/Universe、Awwwards/SiteInspire/Recent Design、MotionSites Hero/Backgrounds/Nexar、
Aura、Image2、Photoshop/After Effects。

**采用语法**：抽象 Rift 三路、战争迷雾、Coach Core；Square/diamond/circle 作为结构/进度/焦点；一次
700–1200ms 叙事，Riot ID 提交后路线汇聚。入口是最高视觉预算区，可用 Image2 生成无版权冲突的抽象
纹理，再 Photoshop 精修；不能直接复制召唤峡谷或官方 splash。

**当前裁决**：Batch D 只把 Rift atmosphere/Coach Core 做成共享环境样片。完整入口等 Auth/RSO、公开
观察/claimed self 输入和错误语义具备后单独实现。Three/Spline/全屏视频继续 deferred。

### 5.2 近期复盘工作台

**参考池**：OP.GG compact stats、Mobalytics GPI/improvement、Blitz/Porofessor、Mobbin/Refero、Linear/
Raycast、MotionSites `F1 Racing Hub`。

**采用语法**：分析对象→产品状态→聚合表现→Coach verdict→Evidence/Training；无顺序胜负占比、聚合
Wins-vs-Losses；电竞演播室排版而非卡片海。

**当前裁决**：当前实现保留。Mobalytics 自己总结的差异对 RiftCoach 很有启发：OP.GG 擅长 clean compact
stats，而 coaching 产品要解释 strengths/weaknesses 和下一步。当前页面因此把 Coach brief 做成第二叙事面，
而不是仅做更漂亮的 OP.GG。

### 5.3 Rift Timeline

**参考池**：MotionSites `F1 Racing Hub`、赛车遥测 UI、Strava/TrainingPeaks 趋势、Riot animation、
ECharts + 自主 SVG markers。

**采用语法**：真实 Gold/CS/XP 曲线、Item/Death/Objective event rail、阶段带、可拖动能量扫描指针、当前
时间点 Coach explanation 和 Evidence chip；移动端使用横向时间尺 + 底部事件 Sheet。

**当前裁决**：仍是五模块中最值得作品集展示的页面，但当前没有 public owner-scoped Timeline DTO，
Batch D 不画假曲线。`F1 Racing Hub` 是当前最值得后续深看/可能获取的免费 Prompt，因为它同时服务
数据密度和 Timeline，而不是只服务 Hero。

### 5.4 Evidence / Agent Trace Drawer

**参考池**：Langfuse/LangSmith/Phoenix/Braintrust/Honeycomb、MotionSites `Forecast Center` /
`Freight Command`、Radix Dialog、Motion。

**采用语法**：claim→sources→typed safe run path→join/gap→digest；typed event/tool/retriever/evaluator
思想，但公共产品只显示 body-free lifecycle，不暴露 Prompt、arguments、Context 或 chain-of-thought。

**当前裁决**：第二轮研究立即推动当前 Drawer 增加 `Safe run path`，显示
`event_kind/status_after/occurred_at` 与 runtime/publication/elapsed。Langfuse 的 aggregated/expanded 适合
内部开发者 trace；RiftCoach 用户版保持一条短路径和明确边界，避免把产品变成 observability console。

### 5.5 Training Plan / Progress

**参考池**：TrainingPeaks 的 plan/train/lift/coach/real progress、WHOOP readiness、Strava trend、
MotionSites `Fitness Dashboard`/`Bite-Sized Courses`。

**采用语法**：active plan、baseline/current/target、sample count、corrected/superseded、next action、来源
review/Evidence；计划与进度是 coach/athlete 共同语义，不是虚拟等级。

**当前裁决**：Batch D 只做关系安全摘要。完整页等 pending Candidate accept/reject、active plan 发现、
progress source jump 和 correction 操作接入后实现。TrainingPeaks 的“plan with purpose / real progress”可
借鉴信息叙事，WHOOP 的 readiness 分数不能在 RiftCoach 没有等价证据时移植。

## 6. Prompt / 付费候选裁决

现在不建议购买整个会员，也不建议立即获取 1–3 个付费 Prompt。原因不是“不需要高级素材”，而是当前
第一纵切已通过视觉 QA，真正的高价值缺口在后续三个不同消费者：入口、Timeline、完整 Training。

| 候选 | 当前公开事实 | 未来用途 | 现在是否获取 |
|---|---|---|---|
| `F1 Racing Hub` | MotionSites Apps 当前可见，Statistics App，页面显示 Copy prompt | Timeline/数据密度 | 先保留，真实 Timeline 设计门优先复核；可能无需付费 |
| `Forecast Center` | 当前可见 Utility，页面显示 Copy prompt | Evidence/状态密度 | 可先用公开 prompt 做隔离原型，不进入当前代码 |
| `Freight Command` | 当前可见 Logistics，locked | 可靠任务/Trace 控制台 | 只有公开视频明显胜过当前 Drawer 才单项获取 |
| `Fitness Dashboard` | 当前可见 Wellness，locked | 完整 Training 页 | 等 Training consumer contract 冻结后再决定 |
| `Nexar` / Animated Backgrounds | 当前可见 Hero/Backgrounds，locked/目录 | 电影感入口 | 等 Auth/RSO 入口设计门再筛，不提前买 |
| Excel 中 `Nimbus Demo/Grid`、`Neural Interface`、`AI System Configuration Console` | 离线 metadata/full prompt 候选，官网 URL 尚未一一配对 | Console/入口/Trace | 必须先与当前官网预览/许可重配，不按名字采用 |

Aura 的公开比较页提供一个有用但带厂商立场的分类：Aura 偏 design-to-HTML，Lovable 偏 full-stack，Figma
Make 偏 Figma context，v0 偏 React/Vercel。RiftCoach 已有真实代码库，不需要迁移到这些平台；可用它们
做截图/brief/reference 驱动的隔离原型，再由当前 React contracts 自主实现。

## 7. 当前第一版的保留、修正与后续精修

### 保留

- 自制 Rift 等高线/三路/Coach Core；
- Square panel、diamond state、circle win-rate focus，恰好对应 Riot 官方三形状；
- 青蓝 structure、克制金色 Coach、warning/reject 语义色；
- 一个主角（Recent Form）+ 两个叙事面（Coach、Context），不是同权 card grid；
- 工作台短促状态动画、入口环境只作静态预告。

### 本轮已修

- 删除无 DTO 支撑的逐局 cards；
- tablet Context 两栏重排；
- observed 档案不偷换 self Summary；
- Drawer 增加 body-free Safe Run Path；
- remote asset/API/SSE 静态与浏览器双重归零。

### 不在 Batch D 偷做

- 电影感入口的完整粒子/视频/素材；
- 真实 Rift Timeline/ECharts；
- 完整 Training proposal/correction flow；
- README 最终 hero/architecture collage；
- 为“更炫”再加 GSAP/Anime/Three 或购买来源不明 Prompt。

## 8. 参考入口

- [Riot: The Visual Language of Hextech](https://nexus.leagueoflegends.com/en-us/2016/12/the-visual-language-of-hextech)
- [Riot: Animation in the League Client](https://www.riotgames.com/en/news/animation-league-legends-client)
- [Awwwards Technology](https://www.awwwards.com/websites/technology/)
- [SiteInspire](https://www.siteinspire.com/) / [Recent Design](https://recent.design/) / [Mobbin](https://mobbin.com/browse/web/apps) / [Refero](https://refero.design/)
- [OP.GG](https://op.gg/lol) / [Mobalytics product comparison](https://mobalytics.gg/opgg-vs-mobalytics) / [Blitz](https://blitz.gg/lol)
- [Langfuse Agent Observability](https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse) / [LangSmith](https://www.langchain.com/langsmith) / [Phoenix](https://phoenix.arize.com/) / [Braintrust](https://www.braintrust.dev/)
- [TrainingPeaks](https://www.trainingpeaks.com/) / [WHOOP](https://www.whoop.com/) / [Strava](https://www.strava.com/)
- [21st.dev Motion libraries](https://21st.dev/community/libraries/s/motion) / [Magic UI](https://magicui.design/) / [Animata](https://animata.design/)
- [MotionSites Apps](https://motionsites.ai/apps) / [Aura](https://aura.build/) / [v0](https://v0.dev/) / [Framer Marketplace](https://www.framer.com/marketplace/)
