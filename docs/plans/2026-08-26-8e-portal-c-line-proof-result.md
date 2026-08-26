# 8E Portal C-line Proof 结果

## 裁决

- verdict：`proof_fail_reopen_corrected_a`；
- production adoption：`false`；runtime changes：`0`；external model calls：`0`；
- 下一动作：按 RQ-125 恢复一次校正 A comparator，使用首帧控制、短 motion-only prompt 和成片后
  deterministic seam construction；不再使用当前同图首尾/密集保守 prompt。

## 实现与执行事实

- tracked contract 冻结 v2 SHA、1920×1080/24fps/192 帧、8 systems、repo-excluded media 和 A fallback；
- HTML/CSS/SVG composition、隔离 renderer wrapper 与 6 项 focused tests 已实现；
- wrapper 校验 HyperFrames `0.8.14`、existing headless-shell、no telemetry/auth/network assets、repo 外输出，
  并固定 PNG sequence → H.264 yuv420p/BT.709/no-audio/faststart；
- 第一次 execute 因新 HOME 未显式绑定 cached shell，在 check 120s 超时；第二次已完成 192 PNG，但 wrapper
  把 `frame_000001.png` 错写为 `frame-%06d.png` 且 Windows GBK 解码 subprocess output 失败；两项均已用测试修复；
- v3 完整 wrapper 输出 SHA `64cf285099d6453c4545a9dad02bbd11f63e3b38687ff38ab04e2bc1a730d95b`，
  3,895,112 bytes、8s、1920×1080、24fps、H.264 High/yuv420p/BT.709/no audio；media 只在 research scratch。

## 机械证据与为什么仍失败

- raw frame 1/192 SHA byte-exact；raw source→first SSIM `0.982996`；
- encoded seam DSSIM `0.026613 ≤ 0.03`；encoded source→first `0.927101`，未过 `0.95`；
- first→mid 的 3×3 SSIM 从 `0.792994` 到 `0.936495`，说明九个区域都有变化；
- 以上只证明 frame clock、覆盖和编码可控，不证明视觉语言正确。

人工全尺寸审查和用户裁决优先：v2 明显叠加粗蓝虚线圆环、紫色折线和节点；v3 虽降低不透明度和线宽，
本质仍是母图上覆盖一组会动的 SVG/HUD。原图里的云雾、空间纵深、建筑材质、环境光和反射没有变成真正
连续的有机运动。它不是 MotionSites 类“画面本身活着”，也不是用户要求的全局动态背景。

因此不能拿 grid motion 或 seam 绿灯绕过视觉失败。当前确定性 scene graph 可以在未来作为生成视频的极少量
结构收尾工具，但不能做主运动层；C proof 在当前形态停止。

## 校正 A comparator 的输入门

1. first-frame only，不指定与首帧相同的 last frame；
2. prompt 只描述运动，不重述画面内容/风格；
3. 不使用 `subtle`、`restrained`、`gently`、`almost imperceptibly`、`extremely slow`；
4. 明确 medium、clearly perceptible、continuous full-scene motion，覆盖 left/center/right 与 near/mid/far；
5. 明确禁止 object-by-object spotlighting、HUD overlays、独立线条/圆环/节点贴层；
6. locked camera 与结构保真仍保留，但不要求每个像素稳定；
7. 首错停止、一任务一次 POST，不充值；生成后先审 source/full-scene motion，再做 deterministic seam，不能用
   后期 loop 掩盖运动失败。

RQ-127 又把 motion amplitude 校准为 medium-to-strong / clearly perceptible / dramatic-cool：允许构图锚定的
小幅顺滑 camera float/parallax cycle，让整幅图有统一呼吸；不再使用完全 pixel-stable locked camera。left/
center/right 与 near/mid/far 必须同时持续活着，不能大区静止或三个焦点轮流表演。
