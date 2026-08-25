# 8E Portal Motion Polish 设计

## 1. 初学者心智模型

这次不是给页面“加动画类名”，而是把两个不同职责的画面分开：

```text
媒体层：Portal/Account 的全帧循环场景、Poster 和失败降级
交互层：真实按钮、语言控件、账号表单、焦点和 URL/history
```

媒体层可以让峡谷、英雄和水晶动起来，但不能产生 session、选择玩家、发布报告或改变产品状态。透明按钮
覆盖画面内水晶，只把 click/Enter/Space 转成一次受控导航；Account 才启动真实 Auth/profile I/O。

## 2. 已确认的视觉事实

### Portal

- 唯一母图为 `docs/assets/8e-portal/portal-mother-image-source-v1.png`；保持原水晶和原曝光。
- RQ-118 取代早期放大/重绘要求：原水晶、塔体和构图不再做生成替换；loop/burst 只让画面内原水晶运动。
- 正常模式是整张画面都在运动的无缝全屏 loop：Rift、云雾、道路、反射、建筑、水晶、星图、节点、粒子和
  环境光均参与；点击后才从全局 idle 收敛为汇聚/burst。
- 当前暗化 screenshot、`rift-portal-background-v2`、aperture、keyframe-v2 与两张过大水晶 edit 均是
  anti-reference/rejected，不得作 Poster、视频首帧或 fallback。
- 可见 UI 只保留小型自有 `RIFTCOACH` 字标、轻量 `中 / EN`、水晶微光提示；不显示大 H1、lede、边框、
  可见按钮标签、CSS 水晶或 orbit。

### Account

- RQ-117 固定地图精度边界：官方参考锁定拓扑，地形有意概括，禁止伪写实微细节。
- 右侧低细节平墙是给真实 DOM Account/玩家选择面板留的，不出现过道/门洞/隧道，也不靠暗幕。
- 左侧必须是一眼可辨的 Summoner's Rift 战术投影：三路、斜河道、双野区、男爵/小龙坑、蓝方左下、
  红方右上和双方基地稳定可读。野区、墙体、塔与基地用概括 terrain masses、轮廓和符号节点表达，不伪造
  逐树、逐墙、逐塔或写实微缩峡谷。
- 五英雄固定为 Camille、Kindred、Ahri、Jinx、Thresh，但不做头像、原画墙或抠图换蓝。先验收无英雄峡谷
  底座，再逐个重塑为从对应地貌中形成的全身能量回响，逐位检查解剖/标志物，最后分层合成。
- 当前 v1/v2 群像与机械架底座均 rejected。红蓝峡谷底座 v3 仍是 preview candidate，未签收前不采用。
- 所有视觉文件标记为 `preview/candidate/adopted-source/runtime-complete/rejected`；rejected 不再作为 edit target，
  candidate 不得进入生产 dist。设计门不要求先伪造 Account runtime 素材，媒体代码测试使用明确的 test fixture。

## 3. 媒体与组件架构

```text
ProductJourney
├─ Portal stage
│  ├─ CinematicSceneMedia(scene=portal)
│  ├─ Portal brand/locale layer
│  ├─ transparent crystal button
│  └─ PortalActivationOverlay
├─ Account stage
│  ├─ CinematicSceneMedia(scene=account)
│  └─ existing AuthGate → AccountAccess
└─ Workbench stage (unchanged)
```

### `cinematicMedia.ts`

保存 typed manifest，而不是组件里散落 URL：

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
  readonly hitBox?: { readonly x: number; readonly y: number; readonly width: number; readonly height: number }
  readonly objectPosition: { readonly x: number; readonly y: number }
}
```

构建期 manifest 另记录 source SHA、rendition SHA/bytes/codec/dimensions/duration/fps/pix_fmt/color/no-audio、
first-frame/poster 和 loop seam 证据；运行时只携带必要 URL/focal geometry，避免把审计数据打入 bundle。

`mediaGeometry.ts` 用与 `object-fit: cover` 相同的 scale/crop 算法，把 source-normalized hit box、intrinsic
dimensions 和 objectPosition 投影为 viewport CSS box；picture、video、透明 button 与 burst overlay 共用该
resolver。1440/1024/390/320 及极端长宽比必须做数值测试，不能直接把 source 百分比当 viewport 百分比。

### `mediaPolicy.ts`

纯函数先决定是否允许视频：

```ts
type MediaPolicy =
  | { readonly mode: "motion"; readonly viewport: "desktop" | "mobile" }
  | {
      readonly mode: "poster"
      readonly viewport: "desktop" | "mobile"
      readonly reason: "preflight" | "reduced-motion" | "save-data"
    }
```

Hook 订阅 `matchMedia('(prefers-reduced-motion: reduce)')` 和存在时的 `navigator.connection.saveData/change`。
Save-Data API 缺失不等于开启；poster 分支仍携带 viewport，以选择正确的 desktop/mobile poster。首个 commit
使用 `poster/preflight`，`useSyncExternalStore` 完成订阅后才解析实际 motion/reduced/save-data；因此
poster-only 从首次 render 就不创建 `<video>/<source>`，不会先请求再撤回。

### `CinematicSceneMedia`

- `<picture>`/poster 永远先渲染；视频绝对定位 `inset:0;width/height:100%;object-fit:cover`。
- `canplay` 后发起 single-flight `play()`，只有当前 attempt 的 Promise resolve 才淡入；当前 attempt 的真实
  rejection/error 进入 sticky poster，卸载或 source/policy replacement 后的迟到结果忽略。
- `<video autoPlay loop muted playsInline preload="metadata" aria-hidden="true">`，无 controls、无音轨，关闭
  picture-in-picture/remote playback。
- hidden tab pause；visible 时只有 motion policy 才 resume。Account stage mount 前没有 Account loop 请求。
- Portal stage 不预取 Account poster/video；Account mount 后由跨幕 overlay 等待 poster `load` 或有界 timeout
  再退出，从而同时保持零提前 Account 请求和无空白幕切。

初始资格和运行期播放状态是两个合同：

```text
MediaPolicy   = motion | poster(preflight|reduced-motion|save-data, viewport)
PlaybackState = poster | loading | playing | failed-sticky
```

当前有效 media attempt 的 `play()` rejection、network/decode error 或 visible resume failure 才进入
session-sticky poster；卸载、policy→poster、viewport/source replacement 后旧 `canplay`/Promise resolve/reject
必须忽略，不能让正常导航、暂停或 StrictMode cleanup 毒化 page session。failure 后迟到 success 也不能复活。
偏好在激活中切成 reduced-motion 时取消空间动画并只提交一次。

sticky failure 由 `ProductJourney` 的 page-session media controller 持有，而不是组件局部 state；back/forward
remount 不重试已失败 scene，整页 reload 才重置。字标/locale chrome 旁提供低视觉权重、44×44 的暂停/继续
动效控件；暂停只冻结当前媒体/ambient overlay，不改变 URL、Auth、Memory 或系统 reduced-motion preference。
`userPaused` 是与 `PlaybackState` 正交的 boolean，不新增或改写 `failed-sticky` terminal。

## 4. 激活状态与控制流

旧 `idle/editing/calibrating/...` 只服务历史 preview，不再控制生产 Portal。RQ-108 新增三态：

```text
idle → activating → committed
```

1. click/Enter/Space 进入 `activating`，ref latch 立即阻止重复；语义按钮使用 `aria-disabled` 保留焦点，而不是
   720ms 内因原生 disabled 丢焦点。
2. full motion：0–300ms 全局 idle loop 的能量路线逐步向水晶收敛；300–560ms 单次 burst；560–720ms
   diamond aperture 覆盖画面。
3. overlay 由 `ProductJourney` 持有，因此 Portal unmount/Account mount 时仍连续；opaque 后只调用一次
   `navigate({stage:'account'})`。
4. Account poster 先出现，loop 可播放后替换；overlay 约 320–420ms 淡出，现有 Account H1 接收焦点。
5. reduced-motion：不播放 loop/burst，立即导航；Save-Data 可保留极短、不位移的颜色反馈后导航。
6. activation 中 popstate/unmount 会取消 timer/generation；迟到回调不得重新进入 Account。

## 5. 全局 loop storyboard

### Portal，约 8 秒

- 整个左侧 Rift 旋涡、云层和远景空间持续运动；道路能量与前景反射贯穿全周期。
- 中央建筑金缝、平台和水晶有独立但同步的呼吸/折射节奏。
- 右侧星图缓慢整体转动，连线、节点、紫色核心和远景粒子持续变化。
- 多层景深可有极慢视差，但镜头不晃、不大幅 zoom；首尾相位/速度连续，不 fade-to-black。

### Account，约 10 秒

- 河道、三路双方能量、概括地形层、坑区雾气、符号塔/基地光和墙面反射形成全帧低频运动。
- 五位英雄分别从对应地貌中呼吸/显形，始终同材质、无选中态；每位动作很小但全身层持续有能量变化。
- 红蓝阵营保持固定地图语义；角色运动不得遮蔽地图识别或右侧表单区。

## 6. Responsive 与焦点几何

- desktop source 沿用 1672:941/16:9。mobile 使用从同一 archival master 派生、单独采用的 portrait source：
  必须保留原水晶/塔体、左 Rift、右星图和整体曝光，但允许为安全区重新构图/扩展画布；记录新 source SHA、
  生成/edit provenance 与人工 identity review。mobile 不直接套用 desktop SSIM，而做母图身份锚点审查。
- Portal 水晶 anchor、Poster、视频首帧、透明 hit box 和 burst SVG 通过共享 cover geometry resolver 后误差
  小于视口 0.5%；hit target 至少
  44×44 CSS px，推荐桌面约 96×220、移动约 88×180。
- desktop 字标左上、locale 右上；mobile 加 safe-area inset。语言控件保持同一屏幕坐标跨 Portal→Account，
  删除 glass capsule/blur/整块青色选中底，只用文字明度和金色短线。
- forced-colors 下 hit target 使用真实 outline；reduced-motion 保留可感知点击反馈但删除空间运动。

## 7. 资产、许可与生成流程

- Portal source 是用户确认的项目自有生成图；把 prompt、SHA、dimensions、消费者、fallback 和移除路径写入 ledger。
- 原 PNG 作为 archival source 原样保存。runtime AVIF/WebP poster 不得改变构图、裁切、曝光、色彩或水晶身份；
  必须绑定 source SHA，并通过 SSIM 与人工 100% 原尺寸审查后才可在既定首屏预算内采用。
- Account map 参考 pinned Data Dragon `16.16.1 map11`；五英雄身份参考来自同一官方 CDN 的 base splash，所有
  URL/bytes/SHA 已在本地研究目录固定。
- `map11` 与 Riot 2024 near-final concept 只锁定拓扑和阵营方向。Account base 候选先做锚点叠合：双方基地、
  三路汇合、河道交叉和两坑必须落在正确关系；随后人工拒绝任何看似写实却无法由公开参考支持的微型树墙塔。
- 官方 splash 不直接进入最终合成。单英雄流程是“身份参考 → 场景原生姿态重塑 → 单体解剖验收 → 分层合成”。
- 可识别角色公开 runtime 必须满足 Riot product/API policy、醒目免责声明和可移除 fallback；不满足时不把
  preview 伪装为已准入资产。
- Account source 与五英雄参考在采用前必须进入 repo-resident provenance manifest，记录完整官方 URL、完整
  SHA、bytes、版本、用途、免责声明/许可状态和逐层移除路径；只存在本地 research 目录不满足发布门。
- MotionSites/React Bits/Magic UI/Aceternity/21st.dev/Uiverse 只提供 pacing、微光提示和 tracing-energy
  机制参考；实现使用现有 Motion/SVG/CSS，不复制付费 prompt/源码，不拼组件。
- RQ-119 的 Kimi v1 已因 source/composition/texture/motion 不合格 rejected；正式视频不绑定单一平台。先按
  `2026-08-25-8e-image-to-video-candidate-audit.md` 用同一 source/brief 横评至少三类路线，硬门先查 first-frame
  identity、锁定镜头、几何/纹理时空一致性、全帧分层运动和 seam，再比较分辨率、费用、延迟与许可。
- RQ-120 增加生成式、确定性、混合式三线：Wan/Seedance/Veo/Luma/Runway 提供 I2V 候选；HyperFrames/
  Remotion 提供分层逐帧 render；推荐候选用生成式有机 plates + 确定性建筑/水晶/拓扑合成。任何 framework/
  skill 采用前仍需安全审计、隔离 spike、许可/性能/维护成本与新 ADR。

## 8. 失败、安全与性能

- Poster 失败仍保留可访问字标/语言/进入按钮与纯色背景；这保证可用性，但不能通过视觉签收。
- 媒体错误不进入 Auth/Product state，不写 URL/localStorage/Memory/Trace，不自动重试。
- Portal 正常资源请求不计为业务/API I/O；远程媒体/CDN 仍禁止，所有 runtime 文件同源并 content-hashed。
- JS ≤150,000 B gzip、CSS ≤22,000 B gzip；全帧运动视频采用重新校准的每场景/viewport/codec 预算，见 ADR。
- 自动脚本验证 codec/bytes/hash/dimensions/24fps/YUV420P/BT.709/no-audio/faststart/loop seam/poster 首帧、
  anti-reference 不进 dist 和 bundle gzip。

## 9. 验收

单元测试覆盖 policy、listener cleanup、poster-first、play/error/unmount、重复激活、timer/generation 和语义 DOM。
Playwright 覆盖 normal/reduced/Save-Data/media 404、1440/1024/390/320、keyboard/focus、history/back/forward、
Account 独立 media、API/SSE 仍按阶段启动、axe、overflow 和 computed style 无 filter/overlay。

视觉 QA 只做两轮成组审查：第一轮同时检查桌面/移动/reduced/error、Portal loop 与 Account 拓扑/抽象层级；
批量修复后再确认一次。阻断性的身份、解剖、许可、拓扑、可访问性或媒体错误不受“两轮”豁免，必须修复；
非阻断偏好进入后序模块清单，不再逐张打断。动态质量不靠逐帧 screenshot diff，使用首尾/首帧机械门加人工
loop 审查。

## 10. 本批不做

不实现 Coach 对话、Data Dragon 产品级英雄头像/装备/目标 enrichment、正式 OIDC/RSO、公开 static edge、
跨模块 final visual QA、OP.GG breadth/golden slice 或 8F。媒体 edge header 只有真实服务存在后才能声称已验证。
