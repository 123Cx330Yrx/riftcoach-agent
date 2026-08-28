# 8E Portal Motion Polish 学习与工程证据

- 检查点：`8e-productization / portal-motion-polish`
- 状态：设计门、runtime Tasks 1–4 均 exact-SHA 公共闭环；Task 5 已完成多路线/故障树实测，当前有效 video
  calls `11`、production media `0`。official 即梦 Smart Edit 是高价值 revise-candidate，但 source/seam 未过门；
  zero-cost post-process 只修复 delivery contract，未形成 production loop
- 决策：ADR-0068
- 需求：RQ-108 至 RQ-125
- 视频候选审计：`docs/plans/2026-08-25-8e-image-to-video-candidate-audit.md`（RQ-119）

## 1. 问题与原理

当前 Portal 已能安全地把用户带到 Account，再进入 Workbench，但视觉仍是暗化静态图、CSS 水晶和固定
720ms timer。它证明了旅程合同，没有证明电影感入口。RQ-108 要解决的不是“多加几个动画”，而是把
电影媒体和产品控制流拆开：媒体可以失败，真正的按钮、URL、Auth、profile 和 Workbench 仍必须正确。

核心原理是 progressive enhancement：poster 与语义 DOM 是可用基线，满足设备与用户偏好时才挂载全帧
loop；播放拒绝、解码失败、Save-Data 或 reduced-motion 都降回 poster，不能改变产品状态。

## 2. 设计与实施边界

采用的结构是：

```text
typed media manifest
  → pure media policy
  → poster-first scene media
  → one-shot Portal activation
  → existing ProductJourney
```

Portal 只使用用户确认母图的同源 poster/loop。Account 使用独立场景；其地图以官方参考锁定拓扑，以有意
概括的 Hextech 战术投影表达地形，不伪造写实微细节。五英雄必须逐个场景化重塑、逐个验收，再分层合成。

本设计不实现 Coach、Training full、Data Dragon 产品资产 enrichment、OIDC/RSO、公开部署、跨模块 final
visual QA 或 8F。正式 runtime 实现只有在本设计提交通过 exact-SHA 公共门后才开始。

## 3. 代码地图（计划）

| 职责 | 计划路径 | 当前状态 |
|---|---|---|
| media manifest 与 viewport rendition | `web/src/cinematic/mediaManifest.ts` | implemented-local；strict 4-entry decoder |
| cover/crop 与 focal/hitbox 投影 | `web/src/cinematic/mediaGeometry.ts` | implemented-local；pure cover geometry |
| reduced-motion/Save-Data policy | `web/src/cinematic/mediaPolicy.ts`、`web/src/cinematic/useCinematicMediaPolicy.ts` | implemented-local；preflight-first external store |
| poster/video 与 page-session sticky failure/pause | `web/src/components/CinematicSceneMedia.tsx`、`web/src/cinematic/mediaSession.ts` | implemented-local；controlled session events + attempt/play tokens |
| 激活 latch/overlay | `web/src/cinematic/portalActivation.ts`、`web/src/components/PortalActivationOverlay.tsx` | implemented-local；generation/latch/reduced-motion |
| Portal/Account 组合 | `web/src/components/AwakeningScene.tsx`、`web/src/app/App.tsx` | implemented-local；ProductJourney-owned timer/navigation |
| 视觉与 responsive | `web/src/styles/product-journey.css` | pending |
| 媒体机械门 | `scripts/check_cinematic_media.py`、`tests/test_cinematic_media_contract.py` | pending |
| browser 纵向 | `web/tests/e2e/cinematic-media.spec.ts`、`web/tests/e2e/portal-motion-visual-evidence.spec.ts` | pending |

最终文件名若在红灯审计中调整，implementation plan 和本表必须一起更新，不能让文档指向不存在的接缝。

## 4. 数据与控制流

```text
首次 render
  └─ poster/preflight，0 video requests
       ├─ subscribed reduced-motion / Save-Data → poster only
       └─ subscribed motion eligible → poster + selected viewport video
                           ├─ canplay/play success → video fades in
                           └─ error/rejection → session-sticky poster

Portal button click/Enter/Space
  → single activation latch
  → bounded convergence/burst overlay
  → exactly one navigate(account)
  → Account poster first
  → AuthGate/session/profile I/O starts only now
```

媒体事件不写 URL、localStorage、Memory、Artifact 或 Runtime Trace，也不能产生第二次 `pushState`。Account
loop 在 Account stage 之前不下载；Workbench 数据流保持不变。

## 5. 验证证据（计划）

当前 design gate 已通过 governance 12、frontend unit 136/E2E 36/typecheck/build、Python no-DB
1837/146 skipped/127 subtests、两套 RAG、Harness dry-run、compileall 和安全/diff 门；本机 Docker/PostgreSQL
不可达，因此真库/Linux 仍等待独立 design exact-SHA jobs。本节其余项目仍是 runtime 计划，不冒充已执行。

公共门随后已补齐：`b3b5280/32812868683` 的 pytest、真实 PostgreSQL 和 Linux packaging 三 job 全绿；
公共 Python `1838 passed, 145 skipped, 1 warning, 127 subtests`，frontend unit 136/E2E 36、两套 RAG、Harness
和治理/安全同 SHA 通过。该证据关闭 design，不关闭 runtime/media 或整个 8E。

runtime Task 1 当前本地证据：manifest/geometry/policy/hook 聚焦 `71 passed`，frontend 全量 `28 files / 207
passed`、Playwright `36 passed`，typecheck/build 与 governance 12/diff 通过；未被任何组件 import，因此
JS/CSS gzip 保持 `142.68/18.50 kB`。Python no-DB `1837 passed, 146 skipped, 1 warning, 127 subtests`，两套
RAG、Harness、compile/security 也全绿。独立审查先
发现 legacy MediaQueryList crash 与 render→commit preference race；修复后使用 modern/legacy 对称订阅、
`useSyncExternalStore` 和首个 `poster/preflight` commit，最终 blocker/major 为 0。该证据仍不包含 `<video>`、
poster/source、媒体下载或页面视觉变化。

runtime Task 1 的 implementation/evidence `1b146e6116587b855a6208e998b5254eac8cba1d` 随后由 Actions
`32826953474` 完成 exact-SHA 公共闭环：`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。
因此 manifest/geometry/policy 接缝可以交接 Task 2；这仍不证明 `<video>` 组件、production media 或最终视觉。

Task 2 本地实现随后以 `mediaSession` reducer 和 `CinematicSceneMedia` 完成：poster 永远先出现，只有 motion
policy 且 session 未失败时才挂载 `<video>`；`canplay` 只启动一次 play request，Promise resolve 才显示视频。
当前 attempt、play request、mounted 和 rendition identity 四道门让卸载、viewport 切换、暂停中止和 StrictMode
迟到结果全部 no-op。聚焦 `39 passed`，frontend 全量 `246 passed`；Task 2 implementation/evidence
`2111a78/32833608622` 随后取得 exact-SHA 三 job 公共闭环。该证据仍不代表 App 组合、生产 media 或最终视觉。

- unit：manifest exactness、viewport、policy、listener cleanup、poster-first、canplay/play/error、sticky fallback、
  hidden/visible pause、重复激活和迟到 callback；
- browser：1440/1024/390/320、normal/reduced/Save-Data/media failure、keyboard/focus、back/forward、Account
  独立媒体、Portal 前业务 API/SSE=0、axe 与 overflow；
- media：source/output SHA、bytes、dimensions、codec、fps、pix_fmt、BT.709、no-audio、faststart、duration、
  首尾 seam、poster/首帧、archival source→poster SSIM/人工感知一致性和 dist content hash；
- Account art：map11/near-final reference SHA、拓扑锚点叠合、红蓝方向、无伪写实微细节、五英雄逐位解剖；
- proportional：frontend typecheck/unit/build/E2E、Python focused/full、RAG/Harness、安全/治理、真 PostgreSQL
  和 Linux package；设计门不把未来媒体结果写成已通过。

Task 2 本地新增的结构性证据包括：poster/reduced/Save-Data 下 DOM 中没有 video/source、WebM→MP4 顺序和媒体
属性、play reject/error sticky、旧 Promise/DOM 事件隔离、hidden/visible、user pause 正交性、poster load/error
与 StrictMode listener cleanup。真实网络 0-request、codec fallback 和浏览器 autoplay 仍留后续 Playwright/媒体门。

Task 3 本地证据覆盖：纯状态机 generation/latch/cancel、overlay 的 aria-hidden/pointer isolation、按钮
`aria-disabled` 保持焦点、720ms full-motion commit、reduced-motion immediate commit、重复输入、popstate 取消、
唯一 `pushState` 和 Account mount 后 overlay 有界退出。Task 3 implementation/evidence `0198fc9/32836430378`
已取得 exact-SHA 三 job 公共闭环。
该批不签收最终 Portal 视觉；旧 CSS crystal/orbit/label/H1/lede 仅作为临时 V1 fallback，production media、
原水晶同源 loop 与最终少字/无暗幕画面仍由后续 Task 4–6 独立门处理。Task 3 聚焦 `27 passed`、frontend
`257 passed`，JS/CSS gzip 为 `144.07/18.50 kB`。
Task 5 的 preflight 设计见 `docs/plans/2026-08-25-8e-video-bakeoff-preflight.md`：官方 first/last/keyframe/loop 能力先做 capability mapping，再比较生成式、确定性和混合式；中转只作 secondary transport。当前仍没有任何实际模型调用或母图上传。

Task 4 证据新增只读媒体审计器和 planned ledger：25 项测试覆盖 exact scene/viewport matrix、Portal source
SHA、codec/fps/pix_fmt/color/audio、faststart/metadata/keyframe、SSIM/seam/dropped-frame、预算、anti-reference
和固定 PATH ffprobe；`52def9c`/`d58ba15`、Actions `32841900909` 已取得 exact-SHA 三 job 公共闭环。当前没有
adopted loop、视频生成调用或 production media。

Task 5 当前证据把“调研池”与“实际付费槽位”分开：Wan/Veo/Vidu/Kling/MiniMax/Seedance/Grok 均进入广筛，
首轮调用仍最多两个。Wan 3.0 官方邀测 access 已由用户 UI 证明；Grok 3 relay 存在，但专用 schema 尚缺。
HyperFrames skill as-is 因 update/auth/provider/telemetry 越权而不安装；exact renderer 隔离 check 通过，重复 frame
SHA 精确一致、raw seam SSIM `0.999600`，但默认 MP4 bytes/seam 门失败，所以只能作结构帧生成器，不能把本地
smoke 说成最终 loop。
上述 admission/spike evidence `7067ea1/32862942549` 已取得 exact-SHA 三 job 公共闭环；它不等于 Task 5、
production media 或 RQ-108 完成。

Wan 3.0 v2 first/last 单样本随后以一次有效 free-quota call 完成：文件可播放且 bytes/no-audio 合格，但
source→first `0.860852`、seam DSSIM `0.097587`、1918×1080/30fps、BT.709 metadata missing、AI watermark 以及
人工 coherent full-frame motion 全部未过门，因此 rejected 且不重抽。重要学习点是：pixel change 不等于有
方向的全局运动；相同首尾图和高密度保真约束可能把闭源 I2V 引向低价值呼吸/纹理变化。下一对照为 Veo。
该负面审计已由 `69fc4ab/32876134114` 完成 exact-SHA 三 job 公共闭环。

Dragon/Veo A2 随后只创建一个成功 task。raw output 为 1920×1080/24fps/8s/H.264 yuv444p/no-audio，SHA
`b707bb1...fa913`，但 source→first `0.587962`、seam DSSIM `0.161631`、254MB、播放器兼容与整幕 motion
distribution 均失败。`/content` 对成功 task 返回 403，query 的 result URL 可恢复，证明 transport contract
偏差不能误写成模型失败；yuv420p preview 只解决播放，不改变质量裁决。

RQ-125 的关键教学不是“生成模型不行”，而是“样本失败与能力上限不同”。本次 lastFrame 字段映射正确，但
prompt 既重述源图又用多个 subtle/slow/restrained 词；这没有充分遵守官方 motion-only I2V guidance。所以下一
步先用 C 线把 scene graph 显式化：结构层锁 source，生成模型只制作有机 plates，frame clock 锁相位/seam。
这是优先 proof，不是不可逆架构采用；若 layer/inpaint、自然度或维护成本不合格，恢复一次短 motion-only、
首帧控制 + deterministic seam 的 A comparator。

C proof 随后用 tracked 8-system scene graph、HyperFrames 0.8.14 与固定 FFmpeg 成功证明 raw frame clock、
source、seam、3×3 motion coverage 和 3.90MB 编码可控；但这次必须反过来学习：自动指标全绿也不等于视觉
目标正确。v2/v3 的运动来自叠在母图上的线、圆环、节点与光带，环境自身没有动。用户明确拒绝后，裁决为
`proof_fail_reopen_corrected_a`；不继续把 HUD 做细，而是按 RQ-126 回到正确利用 I2V 的 motion-only 对照。
RQ-127 还区分了“全局”和“到处放一点变化”：目标是整幕空间从第一秒持续呼吸，近中远景和左右中区同时
有体积空气、大尺度光影与反射；允许锚定构图的小幅 camera parallax，动作必须明显且 cool，而不是 subtle。

corrected Veo 使用 first-only、短 motion-only prompt 后在 upstream 158s/100% 失败且无成片。这里的工程原则是
“缺输出就不评质量”：不能说 prompt 无效，也不能说 Veo 通过/失败视觉门。按首错停止切到 schema 更明确的
Vidu Q3 Pro 单样本，而不是重抽同一模型追结果。
RQ-128 进一步防止“切太快”：Vidu 不是路线切换，而是保持 transport/source/motion/first-only、只改变
model/schema 的控制实验。只有 successful output 才进质量门；若 Vidu 也只给 generic failure，必须回查
request/relay，而不是继续在模型名单上向后跳。

Vidu 首个控制实验随后也无 output/generic failed。Studio 登录态进一步暴露真实合同：first-only/8s/1080p/
16:9 存在，但音频固定开启；因此唯一重试不再随意删字段，而是精准对齐 Studio：删除 seed、audio=true，其他
变量保持。它若仍失败，就停止 API 抽卡并请求 relay task-id 诊断或切到官方 transport。

Studio-contract Vidu 随后成功，说明 API/first-only 方法本身可用。它也形成新的教学 Bad Case：九宫格变化很大，
但主要来自相机推进和整体漂移，不是景物内部全局运动。RQ-129 把目标收紧为 locked-frame refined animated
matte painting：环境多层同时明显运动，镜头/构图不动；Veo v1 的方向较近但效果槽粗、轻且不精细。下一样本
回到 Veo first+last 只改 refined prompt，不是因为 Vidu 品牌不行而换模型。

## 6. 运行手册（设计阶段）

1. 生成素材前核对采用账本，确认 source 和 candidate 状态；
2. 先按冻结 source/brief/scorecard 做多路线短片横评；Kimi v1 只作 rejected Bad Case，不能作为后续 edit target；
3. Portal 只从固定母图生成 loop；Account 先通过拓扑/抽象底座，再进入单英雄流程；
4. 原始视频保存为研究输入，发布资产由固定 FFmpeg 参数编码为 VP9 WebM 与 H.264 MP4，并导出同源 poster；
5. 运行媒体检查器和 frontend gates；失败资产不进入 `web/src/assets/cinematic/`；
6. 成组审查 desktop/mobile/reduced/error 与 loop；阻断问题修复，非阻断偏好进入后序清单；
7. 最终只提交 adopted/runtime 资产及 manifest，不提交 rejected preview、Key、玩家数据或远程热链。

具体命令与红绿顺序见
`docs/plans/2026-08-25-8e-portal-motion-polish-implementation.md`。

## 7. 失败、安全与边界

- poster/video 都失败时仍保留纯色背景、字标、语言控件和可访问进入按钮；这保证可用，不算视觉验收通过；
- video 失败 session 内不自动重试，避免请求风暴；
- Save-Data/reduced-motion 首次 render 不创建 video/source，不能先下载再隐藏；
- media 同源、content-hashed、无音轨；远程 CDN、付费 Prompt/源码复制和第二动画 runtime 不采用；
- 可识别 Riot 角色公开前必须有来源/hash、产品政策、免责声明和移除路径；否则不进入 runtime；
- fixture/candidate/rejected 不能冒充 production asset；公共 edge headers 在真实 edge 验证前保持 unknown。

## 8. 面试表述

可以这样解释：

> 我没有用 Three.js 重做一个实时 3D 首页，而是把高质量全帧循环媒体封装成可替换的 presentation layer。
> React 继续拥有语义按钮、焦点、URL 和业务生命周期；媒体按 reduced-motion、Save-Data 和播放失败做
> poster-first 降级。这样既保留视觉完成度，也能证明入口在媒体失败时仍可访问、不会提前启动 Auth/API。

Account 地图还可以补充：

> 官方低分辨率地图只足以约束拓扑，不足以证明每棵树和每堵墙。我把它做成拓扑准确、地形有意概括的
> 战术投影，并把“看似写实但位置错误”设为拒绝条件，避免用生成细节冒充数据真实性。

当前不能说 runtime 已完成、loop 已生成、Kimi/API 已接入、Riot 角色已获公开准入，或完整 8E 已关闭。

official 即梦结果补充了一个新的面试 Bad Case：真实 edit 可以同时让三大区与九宫格运动、保持 camera/建筑
稳定，却仍因 v2 source identity `0.889072` 和 seam `0.046536` 失败。FFmpeg 可以把音轨、VFR、颜色 metadata
和 9.64MB 修成 fixed24/no-audio/BT.709/约3MB，却不能从错误 phase/identity 中恢复 production source。最佳 J
seam `0.042684` 仍失败，因此工程上停止 crossfade 追绿，先把 geometry/material 与预期 energy/light 差异分开。
完整 actual prompt/output/post-process 证据见
`docs/plans/2026-08-27-8e-jimeng-seedance25-smart-edit-result-audit.md`。

Task 1 面试表述可以补充：

> 我先把媒体路径做成严格本地 manifest，并复刻 `object-fit: cover` 的裁切数学，让透明按钮和画面像素共享
> 同一坐标真值。媒体策略首个 commit 固定为 poster/preflight，浏览器偏好订阅后才允许 motion，因此
> reduced-motion 或 Save-Data 在 render→commit 竞态下也不会先下载视频再撤回。

## 9. 为什么“遮罩 + 背板 + 独立透明层”仍然没有直接过门

这一轮做了一个很小但关键的验证。先让 ImageGen 只负责生成一个“去掉 Rift 内部能量”的底图候选，
再在真实母图的 Rift 内部画一块有边界的遮罩；遮罩外继续使用原母图。最后把一张真正带 alpha 的
Rift 流体层放到这块背板上，并让它做小幅周期位移。

这比“把整张母图复制一份再移动”更安全：建筑边缘不会跟着移动，理论上可以消除之前的重影。结果也
证明了这个工程方向是对的——底图确实只在指定区域替换，结构没有被整张重绘。但视觉材料仍不合格：
透明流体层一旦提高到肉眼可见，就像贴了一条蓝色布带；一旦降低到不露边，又几乎看不出运动。
因此这次的机械门可以通过，视觉门必须拒绝。这个结论不是“ImageGen 没用”，而是这个透明层的
形状、材质和 Rift 的真实遮挡关系还没有对上。

证据保存在 `docs/assets/8e-portal/portal-motion-candidate-masked-inpaint-plate-v1.json` 和
`docs/plans/2026-08-28-8e-portal-masked-inpaint-plate-proof-result.md`。该视频仍是研究文件，
没有进入 `web/public/assets`、runtime manifest 或 production media。下一步应先取得真正贴合 Rift
边界的人工/分段材质层，或使用明确支持区域遮罩的视频编辑模式，再考虑其它区域或新的付费生成。
