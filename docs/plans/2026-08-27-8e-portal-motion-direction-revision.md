# 8E Portal Motion Direction Revision（静态方向与参考模式门）

状态：`preview-generated / direction-rejected`。本文件只冻结下一轮设计与
提示词方向，不把任何新图或视频标为 production media。

## 1. 本轮纠正

Task 5 的 T/X、C-line proof 和即梦 Smart Edit 样本都证明了不同的局部问题：
机械层可以控几何，生成式样本可以让三大区变化，但都没有稳定实现用户要的
“整幕持续呼吸”。因此不沿用现有视频节奏，也不把“偶发 burst、雾层漂移或三处
变亮”继续解释成全局 motion。

目标是基于确认母图的同构静态方向：左 Rift、中央原水晶/平台、右星图/能量场
位置和几何不变；near/mid/far 的空气、道路能量、建筑接缝、地面反射、云层、
星尘和材质光都拥有连续、重叠、中等偏强且可感知的运动潜力。不能新增英雄、
HUD、文字、独立水晶、漂浮金线、暗幕或全局曝光闪烁。

## 2. 无费用静态验证

Image2 只对 `portal-mother-image-source-v2.png` 做 image-to-image，目标产出三张
preview：

1. `material-breathing`：只扩大现有材质高光/反射/空气层的连续性；
2. `depth-separation`：只把 near/mid/far 的遮挡和体积层拉开，保持同一构图；
3. `energy-routing`：只强化道路、建筑缝、Rift、平台和右侧节点之间已有的冷蓝能量响应。

每张都要求无文字/无水印/无 UI/无新物体，并与母图逐项对照。它们是 motion
brief 的视觉沟通稿，不直接替换母图，也不进入 runtime；若 Image2 编辑仍改变
几何或材质，则回退到原母图，只保留文字 brief。

本轮实际得到两张编辑稿（`variant-1`、`variant-2`），第三次请求因余额不足返回
403，未重试。两张成功稿主要表现为亮度/对比度与蓝光增强，未形成可验证的景内
状态变化，因此按“调色稿”拒绝为 motion direction；它们仅保存在用户临时目录，
不写入仓库。

## 3. 即梦参考模式裁决

- **首帧**：只提供母图，模型从单一身份锚点生成运动。下一轮校正 A comparator
  采用它；它最少引入首尾约束冲突，但需要单独检查首帧身份和 loop seam。
- **首尾帧**：理论上利于收口，但相同首尾图会诱发重绘、阶段性 burst 或中间帧
  插值；不同首尾图又改变场景身份。现有实验未过 source/seam 门，因此不作为
  下一轮默认模式。
- **全能参考**：当前即梦页面显示为最多 50 个图/文/音/视频参考的多参考创作
  入口，由模型自行融合条件；它适合概念/风格组合，不是严格的视频编辑合同，
  不能替代 `智能编辑` 的 Video1 temporal anchor，也不适合作为本 Portal 的
  source-preserving 主制片模式。

## 4. 下一次视频 prompt（首帧版，草案）

```text
Animate the supplied image as one coherent 8-second cinematic loop. Keep the exact frame, lens, perspective, composition, architecture, roads, platforms, crystal silhouette, constellation layout, materials and object positions. Motion comes from the scene itself, not camera movement: near/mid/far air and cloud layers, surface-following cyan caustics on stone and metal, road currents and floor reflections, architectural seams, the left Rift's layered internal flow, the original crystal's refraction and platform response, and the complete right constellation field with arcs, nodes, particles and terrain energy. All left/center/right systems are visible from the first frame and overlap continuously with medium-to-strong, clearly perceptible, intricate but stable motion. Preserve crisp deep focus and blue/cyan/electric-blue dominance; use only small warm-gold structural accents. Build closed trajectories so phase, illumination, velocity and light-flow position at 8 seconds return smoothly to the opening state. No pan, zoom, dolly, orbit, shake, reframing, focus breathing, global drift, burst-only timing, alternating focal effects, frozen right side, fog blanket, exposure pulse, HUD, text, logo, watermark, added objects, melting geometry, boiling texture, clipped bloom, fade or black frame.
```

该草案先经过 Image2 静态方向检查；没有新的 source-side 证据前，不发起付费视频
请求、不把现有视频复制到 runtime，也不重开 Seedance/Dragon/Grok 横评。

## 5. Seedance v3 时序复盘与 v4 contract

Seedance 2.5 v3（12s、first-frame-only）已实际完成并由 GET-only recovery 下载，但按用户视觉审查拒绝。
九宫格显示：开场约 0–2.5s 左 Rift 主要从小旋涡变成硬同心环，道路/Rift 下方的流动没有持续出现；
中段 burst 变成横向/斜向穿屏直线，中心出现过曝白闪；右侧星图在 burst 外几乎静止；near/mid/far
没有稳定的全幕呼吸。该结果证明通道可工作和审查链可复现，不证明 Seedance 模型能力上限。

上一版 brief 中的“energy gathers / travels along / completes the circuit”容易被模型具象化为跨画面光线。
下一版必须先分离两个层：

1. **常驻基础层（0–12s 永不关闭）**：首帧就能看到道路与 Rift 下方的液态蓝光流、左 Rift 内部宽幅流体
   深度、中央水晶内部折射/垂直能量、右侧星尘/星座节点/地形能量网，以及建筑接缝、地面反射、云和空气的
   near/mid/far 运动。每层独立但持续，右侧不能等 burst 才开始动。
2. **事件层（只影响中央轴）**：约 4.5–7.0s 做一次低幅、圆润的冷蓝纵向蓄放，能量只沿中央水晶现有
   上下轴在晶体内部和平台之间往返，轻柔提升折射、平台响应和地面反射后回到基线；不沿道路、不横跨画面、
   不连接左右主体，不用过曝或白闪制造“明显”。

建议的 v4 首帧 prompt（设计草案，尚未调用）：

```text
Animate the supplied image as one coherent 12-second cinematic loop. The scene is already alive on frame 1 and stays alive for the entire shot. Keep the exact framing, fixed camera, perspective, architecture, roads, platforms, crystal silhouette, constellation layout, materials and object positions. This is an in-scene material-motion pass, not a redraw.

Permanent baseline motion from 0 to 12 seconds: LEFT, keep the existing Rift shape and add only broad, translucent cyan-blue fluid depth moving smoothly inside it, with soft layered flow and sparse filaments, never graphic concentric rings. The road beneath the Rift carries a continuous low-amplitude liquid-blue current inside its existing channel from the first frame. CENTER, the original crystal facets, internal refraction, vertical energy and platform reflection breathe continuously. RIGHT, the complete starfield, constellation nodes, fine arcs, stardust volume and terrain energy field continuously drift and undulate with offset phases; the right side must remain visibly active before, during and after the event. Across the scene, architectural seams, stone/metal reflections, clouds and near/mid/far air move continuously with material-following depth.

At about 4.5–7 seconds, add one restrained rounded cyan-blue pulse only on the existing central vertical crystal axis: a soft wave rises and falls through the crystal and platform, gently increasing refraction and reflection before returning to baseline. It must not shoot along roads, connect left to right, draw straight beams, or become a white flash. The permanent baseline motion never stops during this pulse. From 9–12 seconds, all layers continue moving while their phase, light level and flow position smoothly return to the opening state for a loop.

Keep the image crisp, deep-focus, stable and premium. No camera pan/zoom/dolly/orbit/shake/drift, no redraw or melting geometry, no new circles or line networks, no HUD, no fog sheet, no global exposure pulse, no alternating focal spotlights, no frozen right side, no text/logo/watermark, no cut/fade/black frame.
```

Image2 现在可用，但只在发现静态材质/遮挡/反射需要额外沟通时做有针对性的同构 preview；它不能替代这份
时序 contract，也不应因为可用就自动生成新图。该 v4 草案尚未获得新的付费调用授权。
