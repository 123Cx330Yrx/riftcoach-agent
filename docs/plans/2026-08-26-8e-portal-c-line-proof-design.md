# 8E Portal 混合 C 线运动导演样片设计

## 1. 要解决的问题

Wan 与 Veo 的两个单次整景 I2V 样本都没有同时满足三件事：母图保真、整幕持续运动、无缝循环。Veo 样本
还暴露了输入策略问题：一条过长 prompt 同时重述场景、要求几乎像素级稳定，并用多个 slow/subtle 词压低
运动。RQ-125 因此拒绝样本，但不拒绝 Provider 或生成式 A 线。

本 proof 不制作最终 Portal，也不调用第三个视频模型。它只回答一个可证伪问题：把场景显式拆成运动系统，
用同一个确定性 8 秒时钟控制，能否比整景 I2V 更自然地让整幕持续运动，同时保持结构和 loop 可控？

## 2. 三种方案与裁决

### A. 立即用校正 prompt 再跑整景 I2V

优点是快、可能得到更有机的运动；缺点是仍让单个模型同时承担结构、遮挡、运动和 seam，且新调用无法先
证明分层路线是否更可控。保留为 C proof 失败后的单次 comparator，不作为当前动作。

### B. 纯扁平图 + 少量 CSS 光点

最可控、最便宜，但已被 RQ-112 明确否决为最终路线：几个光点或局部水晶动画不能冒充全局动态。只可作为
结构工具 smoke，不值得再做。

### C. 显式 scene graph + deterministic frame clock + 后续有机 plates

推荐先做。母图始终是结构底；本 proof 先用离线 SVG/mask/gradient 建立完整 motion direction。只有运动节奏
通过后，才将云雾、Rift 内层、星空等占位层替换为生成模型的有机 loop plates。浏览器 runtime 最终仍只播放
普通本地 WebM/MP4，不引入 HyperFrames、Canvas 或第二动画引擎。

## 3. Scene graph 与运动覆盖

所有系统共享 `T=7.958333s` 的离散 192 帧闭合时钟；0/191 帧必须相同，24fps 输出名义时长 8 秒。

| 系统 | 画面职责 | proof 运动 | 最终可能替换 |
|---|---|---|---|
| base structure | 全母图、塔体、平台、建筑 | 完全锁定，不 zoom/reframe | 永远保留 source truth |
| left atmosphere | 云雾、远景空间 | 两层错相漂移、亮度呼吸 | 有机 fog plate |
| Rift interior | 左侧传送门内部 | 环流、内层折射、深度波 | 生成式 Rift plate |
| route energy | 左→中完整道路及支路 | 连续传播、尾迹、平台汇聚 | 确定性 SVG/plate 混合 |
| crystal/tower | 原水晶、竖向能量与金缝 | 内折射、呼吸、金缝追光 | 确定性 mask |
| star map | 右侧星图、节点、紫核 | 整组慢漂、连线流光、节点错相 | 星空/粒子 plate + SVG |
| foreground | 台阶、地板、镜面、近景粒子 | 横向扫光、反射回流、景深粒子 | 确定性 + organic overlay |
| global light | 左中右环境统一 | 大尺度低频蓝/紫/金光场游移 | 最终 color/grade pass |

“全局”不表示每个像素同速度移动；它表示左/中/右、远/中/近景始终都有可感知但不抢戏的独立运动，任何
连续两秒都不能只剩一个局部对象表演。

## 4. 文件与控制流

```text
repo mother image + tracked proof composition/contract
  → render wrapper verifies source SHA + exact HyperFrames 0.8.14
  → isolated HOME / no telemetry / no auth / no network assets
  → HyperFrames check + PNG sequence
  → fixed FFmpeg yuv420p/BT.709/24fps/no-audio/faststart preview
  → source/first + seam + regional/grid motion metrics
  → contact sheet + human full-size review
```

Tracked files只保存 composition、contract、renderer 与测试；PNG sequence、MP4、logs 和 node_modules 全部输出到
repo 外 research scratch。proof 失败可以整批移除，不改变 React、manifest 或产品旅程。

## 5. TDD 与通过门

先写失败测试，冻结：source SHA、8 秒/24fps、8 个 motion systems、禁止 remote URL/audio/randomness、exact
HyperFrames version、repo-excluded output、corrected-A fallback 条件。实现后依次运行 contract tests、HyperFrames
check、raw snapshots/PNG render、FFmpeg probe 与视觉审查。

机械门：

- source→first SSIM `≥0.95`；
- raw frame 0/191 byte-exact 或 SSIM `≥0.999`；encoded seam DSSIM `≤max(1.5×adjacent p95,0.03)`；
- left/center/right 以及 3×3 grid 没有完全冻结的大区；数字只作辅助，不能用全屏闪烁刷覆盖率；
- locked camera、1920×1080、24fps、yuv420p、BT.709、no audio、faststart；
- proof preview 建议 `≤20MB`，但生产仍必须回到 ADR-0068 `≤5.5MB` 门；
- 人工审查必须同时满足：整幕持续运动、无机械 HUD 拼贴、无明显 mask 边、无结构漂移、无焦点轮流亮的生硬感。

## 6. 失败与 A 线回退

以下任一成立，C proof 失败并停止深挖：运动仍像覆盖层贴纸、mask/inpaint 边缘明显、source/seam 失败、七个以上
专用层仍无法获得自然节奏、或继续提升必须维护一套接近实时 3D 的复杂工程。失败不降低 RQ-112 视觉目标。

回退只允许一次新采用门下的 A comparator：首帧控制、短 motion-only prompt、明确中等幅度环境运动、不过度
重述画面或禁止一切变化，生成后用确定性 seam construction 收口。它不是重跑当前同图首尾 prompt。

## 7. 范围外

本 proof 不进入 `web/src/assets/cinematic/`，不修改 runtime manifest，不实现 Account、Coach、Training、RQ-103
或 Task 6，不调用视频 API，不创建/读取 Key，不购买 credits。Account 仍等 Portal 工艺胜出后按既定拓扑与
五英雄逐位流程继续。

