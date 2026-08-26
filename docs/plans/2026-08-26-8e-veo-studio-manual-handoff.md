# 8E Veo Studio 手动生成交接

## 当前界面

- Studio：创浪云 `模型广场 → 视频`
- 模型：`Veo 3.1 Quality Official`
- 模式：`首尾帧生视频`
- 时长：`8 秒`
- 分辨率：`1080p`
- 画幅：`16:9`
- 提示词增强：关闭（按钮没有 `active`）
- 预计消耗：`19.71` 额度
- Studio 对此模型显示“生成音频”为固定能力；成片通过视觉门后再本地移除音轨，不为音频改 prompt。

## 上传

首帧和尾帧都选择同一个文件：

`D:\riftcoach-agent\docs\assets\8e-portal\portal-mother-image-source-v2.png`

确认上传计数从 `0/2` 变为 `2/2`，并检查两个缩略图确实相同。该文件 SHA-256：

`8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`

## Studio 单文本框提示词

```text
Single uninterrupted wide shot, motion-only image animation. The camera is locked off: preserve the exact frame, lens, perspective, scale, architecture, silhouettes, object positions, deep focus, and crisp source linework. Create a premium living matte-painting loop with continuous, clearly visible, medium-amplitude environmental motion in every third of the frame and every depth plane at the same time, never as a sequence of focal effects. Across foreground, midground, and distance, volumetric mist curls with gentle occlusion while broad blue-gold caustic light travels along existing stone and metal surfaces and through floor reflections. On the left, the existing Rift's translucent energy strata circulate at complementary speeds while soft luminous currents flow through the complete pathway. At center, internal refraction and subsurface light circulate inside the crystal's fixed silhouette; the platform reflection answers continuously and warm-gold tower seams breathe. On the right, the existing constellation filaments and arcs ripple locally, violet nodes breathe asynchronously, and fine particles advect through the fixed deep star volume without shifting the background. All motion systems overlap from the opening instant, share one coherent rhythm, retain restrained cinematic contrast, and complete smooth closed trajectories. At exactly eight seconds, every motion phase, illumination level, and velocity matches the opening frame for a seamless loop. Maintain rigid architecture, stable geometry and textures, controlled highlights, and a clean cinematic plate free of camera drift, reframing, focus breathing, motion blur, interface graphics, added or missing objects, flicker, boiling textures, melting forms, clipped bloom, watermarks, and fades.
```

## 点击前六项检查

1. 模型仍为 `Veo 3.1 Quality Official`；
2. 模式为 `首尾帧生视频`；
3. 上传计数 `2/2`，两张都是 v2 母图；
4. `8 秒 / 1080p / 16:9`；
5. 提示词增强关闭，文本首句为 `Single uninterrupted wide shot`；
6. 按钮显示预计 `19.71`，由用户本人点击“立即生成”。

生成后不要立即重抽。把任务状态或完成页面留在 Studio，通知 Codex；Codex 负责下载、去音轨兼容预览、抽帧，
并先人工审 camera lock、全幕 simultaneous motion 和材质精细度，再计算 source/seam/codec 指标。

## 当前边界

Chrome 扩展未启用 file URL access，自动 file chooser 没有上传成功；Studio 仍是 `0/2`。如以后要让 Codex 自动
上传，需要在 Chrome 扩展详情中启用 `Allow access to file URLs`，但本次无需改权限，用户手动上传即可。

Dragon QQ 管理员私聊里有一份未发送的 support 草稿；用户已选择先走 Studio，草稿不发送。
