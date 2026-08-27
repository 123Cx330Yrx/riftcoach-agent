# 8E Portal regeneration preflight（首帧单锚点）

状态：`prepared / waiting request readback`。本计划只准备下一次视频请求，不代表已经创建任务或采用媒体。

## 1. 选择

- **源**：`portal-mother-image-source-v2.png`，SHA-256 `8134c0ca...`，作为唯一首帧图像。
- **模式**：Seedance 2.5 的普通首帧生视频；不上传现有失败视频，不用首尾帧，不用“全能参考”多参考融合。
- **时长/画幅**：8 秒、16:9；分辨率按页面实际可用档位 readback，优先能稳定过 source/seam 门的档位。
- **调用纪律**：先 readback 模式/价格/附件/SHA/音频设置，再执行恰好一次 POST；失败不盲重试。

首帧单锚点的理由是减少同图首尾约束导致的重绘和“中段停滞/峰值”问题。它不保证自动无缝闭环，
所以生成后仍要做首帧身份、全幕运动覆盖、loop seam、编码和人工观感审查。

## 2. Motion brief（正向、短、无矛盾）

```text
Animate this exact image into one coherent 8-second cinematic loop. Preserve the original framing, lens, architecture, roads, platforms, crystal silhouette, constellation layout, materials and object positions. Keep the camera locked and let the scene itself move with a steady, clearly visible, medium-amplitude breathing rhythm from the first frame to the last; do not stage a single crescendo or isolated flashes.

All three regions and all depth planes move together continuously. In the left Rift, layered translucent currents circulate with depth while nearby air and the road respond. At center, the original crystal keeps its silhouette while internal refraction, vertical energy, platform rings and floor reflections circulate. On the right, the complete constellation field remains equally active: arcs, filaments, nodes, terrain network and near/far stardust flow with offset phases. Across the whole frame, foreground surfaces, road energy, architectural seams, reflections, clouds and volumetric air shift subtly but continuously, with real occlusion and material-following light rather than a fog overlay.

Keep the existing dark blue, cyan and electric-blue palette with restrained warm-gold structural accents. Motion must feel intricate, stable, crisp and premium, with no global color grading. Close every motion trajectory so the final phase, illumination and light-flow positions return naturally to the opening state for a seamless loop.
```

## 3. Negative brief

```text
No camera pan, zoom, dolly, orbit, shake, reframe, lens breathing or global drift. No geometry or texture redraw, melting, boiling, morphing, added objects, removed objects, isolated three-part flashing, frozen right side, burst-only timing, fog blanket, exposure pulse, color shift, HUD, text, logo, watermark, giant bloom, floating neon lines, cut, fade or black frame.
```

相比上一版，这次把“持续运动”放在正向描述中，用“steady / continuously / all three regions and all depth planes”
表达节奏；negative 只保留会直接破坏构图、材质、全局感和交付的现象，避免用过密条款把模型压回静止。

## 4. 生成后验收

1. 先确认 source→first SSIM、poster→first、seam、fixed-24/no-audio/BT.709/codec/bytes；
2. 再按 3×3 网格与 left/center/right、near/mid/far 观察是否全程有自然运动；
3. 人工检查是否是景物自身在动，而不是相机漂移、雾层盖住或三处闪光；
4. 任何一项失败都只记录 fault layer，不把单样本失败外推为模型上限；不自动重试。

Image2 静态编辑降为可选辅助，不再要求充值或生成第三张图；当前 production media 仍为 `0`。

