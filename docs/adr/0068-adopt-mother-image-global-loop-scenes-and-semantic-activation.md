# ADR-0068：采用母图直出的全局循环场景与透明语义激活面

- 状态：Accepted for RQ-108 design；runtime media 仍须通过素材、视觉、许可与编码门
- 日期：2026-08-25
- 检查点：`8e-productization / portal-motion-polish`

## 背景

RQ-102/104/105/106 已公共完成双语产品表面和 `Portal → Account → Workbench` 三层旅程，但当前 Portal
仍是静态 WebP、全屏暗化 filter/vignette、大标题和可见 CSS 水晶。RQ-108、RQ-110 与 RQ-112 明确否决该
表现：最终正常模式必须直接从用户确认的高清母图制作全帧循环动态背景，不能用暗幕、模糊或少量 DOM 光点
冒充电影化场景。水晶属于画面；DOM 只拥有透明可访问 hit target 和点击后的状态编排。

RQ-118 取代了早期水晶放大/重绘要求：Portal 保留母图原水晶、塔体和构图，只在全局 loop 与点击 burst 中
让原水晶运动；两张放大 edit 和任何独立/CSS/贴图水晶都保持 rejected。

Account 也不能复用压暗 Portal。RQ-111 要求独立峡谷内殿，并把上路、打野、中路、下路、辅助五个英雄
以全身能量幻影/晶体浮雕融进场景，而不是头像或五张原画卡。当前确认 roster 为 Camille、Kindred、Ahri、
Jinx、Thresh。RQ-117 又校准地图真实性：官方参考只负责锁定拓扑，地形必须做成有意概括的 Hextech 战术
投影，不能生成看似具体却错误的微型树墙塔。具体概念图仍须通过视觉门，公开 runtime 还须通过 Riot 产品/IP 门。

现有 JavaScript gzip 为 `142.68 kB`，低于但接近 150 kB 硬门。仓库已有 Motion 13.1.1 与原生 SVG/CSS，
没有理由再增加 Three/OGL/Anime/GSAP。当前也没有 `<video>`、Save-Data、媒体错误、媒体 manifest 或自动字节门。

## 方案比较

### A. 继续静态母图，以 CSS/SVG/DOM 制造动态

拒绝。它能保留语义和小体积，但已经形成真实 Bad Case：整页像压暗的静态概念图，水晶与环境不属于同一
画面，全局场景没有生命力。

### B. 引入 WebGL/Three 或第二动画引擎重建整景

拒绝当前采用。它会突破 JS 预算，引入 GPU/移动/上下文丢失/降级和长期维护成本；现有需求是播放已制作的
电影化场景，不是建立通用实时 3D 引擎。

### C. 母图同源全帧 loop + 同源 poster + DOM/SVG 激活转场（采用）

Portal 与 Account 各自使用全屏、无音轨、无缝循环视频；帧内所有主要环境层都运动。原始母图/同源导出
poster 始终在视频后方；reduced-motion、Save-Data、播放拒绝或解码失败从第一次 render 就只用 poster。
现有 Motion/SVG 只编排点击后的汇聚、burst 和 diamond aperture，不承担常驻背景动画。

## 决策

### 1. 场景和资产真值

- Portal 唯一源为 `docs/assets/8e-portal/portal-mother-image-source-v1.png`：`1672×941`、
  SHA-256 `552a87453daae53762f56f0cb5f7c7c2fee18256ef6d193c00575283e9b7aada`。
- 该 PNG 是逐字节保留的 archival source。“同源/无损 poster”指构图、裁切、曝光、色彩和水晶身份不被
  二次创作改变，不要求把 2.7 MB PNG 原样作为每次首屏传输。runtime AVIF/WebP poster 只有在固定 source
  SHA、SSIM 与人工原尺寸审查证明感知一致后才可采用；否则提高 poster 预算或拒绝该 rendition，不能靠暗化
  或模糊换体积。
- desktop rendition 必须保持上述构图。mobile 可以从同一 archival master 派生独立 portrait source，以避免
  `cover` 裁掉主要场景；它必须保留原水晶/塔体、左 Rift、右星图和曝光身份，记录新的 source SHA、edit/
  generation provenance 与人工锚点审查。mobile 不冒充 archival PNG 的逐像素/SSIM 等价物。
- 原始水晶保持不变。两次无 mask 放大编辑都因水晶遮蔽塔体而 rejected，不进入仓库/runtime。
- `rift-portal-background-v2.webp`、`rift-aperture-plate.webp`、暗化截图和 `portal-motion-keyframe-v2` 不得成为
  RQ-108 poster、loop、fallback 或 Account 来源；前两者从 Portal/Account/Auth 三处 runtime consumer 移除。
- Account 必须是独立 `Rift Attunement Chamber`。两张一次性群像和第一张抽象轨道式无英雄底座都已被
  用户拒绝并移出仓库；当前没有已采用的 Account 母图，不能用任何 rejected preview 或 Portal 图占位。
- 资产状态固定为 `preview → candidate → adopted-source → runtime-complete`；`rejected` 不得重新成为后续
  edit target、fallback 或测试截图。设计门可以在 Account 母图尚未采用时关闭，但实现门只能使用明确的
  test fixture 验证媒体合同，不能把 fixture 或未签收 candidate 打入生产 dist。

### 2. 全局循环而非局部动效

Portal 正常 loop 必须让左侧 Rift、云雾/远景、整条道路、前景反射、中央建筑缝线/平台/水晶、右侧星图/
节点/粒子和环境光形成连续全帧运动。Account loop 必须让峡谷三路、河道、地图能量面、五位英雄幻影、
内殿光线、粒子和地面反射同时运动，只把节奏降得比 Portal 安静。不能用 fade-to-black 隐藏接缝，不能用
整屏抖动、频闪或大幅镜头运动制造“全局”。

Portal 建议 8 秒 locked-camera seamless loop；Account 建议 10 秒。允许极慢景深视差，但首尾几何、曝光、
粒子相位和速度必须连续。

### 3. React/媒体边界

新增三层展示合同：

```text
typed CinematicMediaManifest
  → resolveCinematicMediaPolicy(reduced-motion, saveData, viewport)
  → resolveCoverGeometry(intrinsic dimensions, objectPosition, hitBox)
  → CinematicSceneMedia(poster-first, optional loop, playback state)
  → PortalActivationSequence(idle → activating → committed)
  → existing ProductJourney navigation
```

- `CinematicSceneMedia` 始终渲染同源 poster；仅在 policy eligible 时挂载本地 `<video>`，属性为
  `autoPlay muted loop playsInline preload="metadata"`，无 controls、无音轨、`aria-hidden`。
- media policy 的 motion/poster 两个分支都必须携带 `desktop|mobile`；reduced-motion/Save-Data 只改变是否
  挂载视频，不能让移动端错误回退到 desktop poster。
- rendition 携带 intrinsic width/height、normalized hitBox 和 objectPosition；picture/video/button/burst 必须
  共用与 `object-fit: cover` 一致的纯 geometry resolver，不能直接把 source 百分比当成 viewport 百分比。
- video `canplay` 后才淡入；`play()` rejection、`error`、codec/decode failure 都变成 session-sticky poster，
  不重试风暴、不导航、不隐藏语义按钮。页面 hidden 时 pause，恢复时仅 eligible 状态继续。
- 初始资格与运行期状态分开：`MediaPolicy = motion | poster(preflight|reduced-motion|save-data, viewport)`，
  `PlaybackState = poster | loading | playing | failed-sticky`。首个 commit 固定为 `poster/preflight`，只有浏览器
  preference/network/viewport 订阅完成并再次读取后才允许 motion；偏好在 activating 中切为 reduced-motion
  时取消空间动画并只 commit 一次，visible resume 再失败也进入 `failed-sticky`。
- `ProductJourney` 持有 page-session 内 per-scene failed/paused state；back/forward remount 不重试已失败媒体，
  整页 reload 才重置。提供低视觉权重、可键盘操作的暂停/继续动效控件，满足持续自动运动的用户控制；它不
  改写系统 preference、URL 或业务状态。
- `userPaused: boolean` 与 `PlaybackState` 正交；暂停不会把已失败媒体改回可播放，也不会伪造新的 playback
  terminal。effective playback 由 policy、sticky failure 与 userPaused 共同决定。
- Account media 只在 Account stage 挂载；Portal 不预取 Account poster/video，确保 activation commit 前
  Account media 与业务 API/SSE 请求均为 0。幕切 overlay 在 Account mount 后等待 poster `load` 或有界 timeout
  再退出，不能用提前请求换取转场。
- `ProductJourney` URL 合同、owner/profile 选择和 Auth/Live identity 保持原样。

### 4. 水晶激活与跨幕连续性

- 透明原生 `<button>` 覆盖视频/Poster 中的水晶轮廓；不渲染独立图片、CSS crystal、orbit、可见 label 或
  常规按钮底。accessible name 保留 `进入 RiftCoach / Enter RiftCoach`，hint 可 sr-only。
- idle 只允许水晶附近 3–5px 微光提示；hover/focus 通过局部能量/暖金短括号表达，forced-colors 回退真实 outline。
- 激活使用单一 latch：重复 click/Enter/Space、StrictMode 或迟到事件只能 commit 一次。full motion 约
  `600–720ms` 完成三路汇聚、一次 burst、diamond aperture；reduced-motion 立即导航。
- transition overlay 由 `ProductJourney` 持有以跨 Portal/Account mount 持续；Account mount 后淡出并把焦点交给
 真实 H1。视觉 animation 不能产生第二次 `pushState`。

### 5. Account 峡谷与五英雄

- 叙事场景集中在左侧约 60–65%；右侧是平整、浅景深、低细节的同材质墙面，不出现过道、门洞、隧道或
  消失点，也不靠 overlay 压暗。
- 左侧主体以官方 Data Dragon `map11` 与 Riot 2024 near-final concept 锁定拓扑身份：三路、斜向河道、
  双野区、男爵/小龙坑和双方基地必须稳定可辨；不能用抽象机械轨道替代地图。
- 地形采用有意概括的 Hextech 战术投影：用 terrain masses、轮廓、层级、材质区和符号节点表达野区、墙体、
  塔与基地。它不声称逐树、逐墙、逐塔或写实正射精度，也不得生成位置看似具体却与官方拓扑不符的微型
  植被、建筑、道路或地貌。候选必须先通过官方参考的拓扑叠合审查，再通过“无伪写实细节”人工门。
- 阵营按官方地理固定为左下蓝方、右上红方；基地、塔和半区线路分别使用青蓝与绯红/暖橙，河道保持中性
  蓝、男爵坑紫色、小龙坑暖色。阵营颜色不能变成 whole-frame tint，也不表示当前用户队伍或比赛结果。
- roster 固定为 Camille / Kindred / Ahri / Jinx / Thresh。先制作无英雄内殿/峡谷母图；再一次只处理一位，
  依据官方 Data Dragon 原画锁定脸型、发型、服装结构、武器与关键轮廓，同时重新设计与路线/基座/建筑
  遮挡、接触、投影和反射一体的姿态，并从对应路线/野区地貌中形成。每位必须单独验收解剖、手脚、武器、
  尾巴、面具及羊狼双体关系；不再站在五个通用机械底座上。
- 单体通过后才分层合成并统一内部晶体、金色结构骨架、雾化边缘和环境光。禁止直接抠 splash、沿用 splash
  pose、套蓝色滤镜、一次性生成人物群像，或用整体风格掩盖畸形。不得显示头像、卡片、原画窗、名字、
  选角状态或用户推荐。
- 官方 General Policies 把 Data Dragon/Press Kit 列为第三方产品可用来源，并要求产品注册条件与醒目免责声明；
  `Legal Jibber Jabber` 许可可撤销。可识别角色进入公开 runtime 前必须登记 pinned 官方来源/hash、产品/API
  合规证据、免责声明和移除路径；未满足时只保留 preview，不冒充已准入。

官方政策：

- https://developer.riotgames.com/policies/general
- https://www.riotgames.com/en/legal

### 6. 编码、预算与发布合同

运行时每个 viewport 只下载一个 codec：VP9 WebM 优先，H.264 MP4 fallback；8-bit YUV420P、BT.709、24fps、
无音轨、关键帧间隔不超过 2 秒，编码时移除 metadata。AV1 当前不作为唯一格式。

初始设计门：

| 项目 | 硬门 |
|---|---:|
| JS gzip | ≤150,000 B |
| CSS gzip | ≤22,000 B |
| 非媒体基础冷启动 | ≤220,000 B |
| Portal desktop/mobile poster | ≤500/350 kB |
| Portal desktop/mobile VP9 | ≤4.5/2.4 MB |
| Portal desktop/mobile H.264 | ≤5.5/3.0 MB |
| Account desktop/mobile poster | ≤450/320 kB |
| Account desktop/mobile VP9 | ≤4.0/2.2 MB |
| Account desktop/mobile H.264 | ≤5.0/2.8 MB |
| 全部发布媒体 | ≤25 MB |

这些门为全帧全局运动重新校准，不得拿早先局部运动预算降低视觉目标；实际首轮编码仍要用 SSIM/人工观感/
解码性能决定是否进一步收紧。reduced-motion/Save-Data 必须产生 0 个视频请求。

媒体通过 Vite static import/content hash 进入 `web/src/assets/cinematic/`。公开 edge 必须正确返回 MIME、
immutable cache、ETag、`Accept-Ranges: bytes` 与 `206/416`；CSP 显式增加 `media-src 'self'`。在真实 static edge
尚未实现前，只能声称 build/browser 合同通过，不能声称部署 header 已验证。

### 7. 自动门

新增只读检查器固定 manifest SHA/bytes、poster/video dimensions、codec/fps/duration/pix_fmt/color/no-audio、
MP4 faststart、首尾 loop seam、poster/首帧一致性、dist content hash 和 anti-reference 排除；同时自动测 JS/CSS
gzip。Account 素材另保留 map11/near-final reference SHA、拓扑锚点叠合结果、阵营方向和人工“无伪写实细节”
裁决。Playwright 覆盖 normal、reduced-motion、Save-Data、media 404/play reject、四视口、keyboard/focus、
重复激活、activation 中 unmount、history/back/forward、Account 独立 media、axe 和无暗化 computed style。

首批机械阈值在看正式候选前固定：input source→生成首帧 SSIM `≥0.95`；poster→视频首帧 SSIM `≥0.98`；
令 `DSSIM=1-SSIM`，末→首 seam DSSIM 必须 `≤ max(1.5 × 全片相邻帧 DSSIM p95, 0.03)`。这些数值只是
阻断下限，不能替代构图、纹理沸腾、几何漂移和 motion language 人工审查。Chromium desktop/390 各播放
两轮后 dropped/total frames `≤1%` 且无非注入 stall；非媒体冷启动 gzip `≤220,000 B`，并分别记录 Portal
首屏、Account 进入、poster-only 的 transferred bytes。

## 后果与边界

收益：画面本身承担高级感，DOM 继续承担真实交互与状态；两个场景可独立替换，失败时仍完整可用；不增加
第二动画 runtime。成本：需要外部高质量 image-to-video 资产生产、双 codec/双 viewport、媒体 QA 和未来
static edge。RQ-119 已把用户实测 Kimi 12 秒/1080p 输出裁决为 source fidelity 与 motion language 不合格的
rejected Bad Case；Kimi 不再是默认路径。正式 loop 前按同一 source/brief/验收表横评至少三类路线，优先
first+last/keyframe/loop 可控的 Veo、Luma Ray 与 Runway/Firefly 多模型工作流；质量门先于价格/分辨率。
RQ-120 又增加 Wan/Seedance 与确定性/混合式对照。当前推荐 primary candidate 是“生成式有机层 +
HyperFrames/Remotion frame-driven 结构合成”，但尚未采用任何新工具；HyperFrames 若胜出须先安全/许可/隔离
spike 与新 ADR。当前设计/代码可继续，但不得用静态缩放/假 parallax 或单次平台预览冒充完成。

本 ADR 不实现 Coach、Data Dragon 产品 asset enrichment、OIDC/RSO、跨模块 final visual QA、公开部署或 8F。
