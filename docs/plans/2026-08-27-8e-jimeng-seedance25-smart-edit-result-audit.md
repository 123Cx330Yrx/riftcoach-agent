# 8E 即梦 Seedance 2.5 Smart Edit 结果与后处理审计

## 裁决

- official 即梦 `Seedance 2.5 / 智能编辑` 完成一次有效生成；Task 5 有效视频调用从 `10` 增至 `11`；
- raw output 是当前最接近 locked-camera/full-scene organic motion 的 edit 样本之一，但仍为
  `revise-candidate / not-adopted`；production media 保持 `0`；
- 三主体、尤其右场和九宫格均有变化，镜头/建筑初审稳定；但 v2 source identity 与 loop seam 两个预先冻结的
  硬门失败；
- 零费用 FFmpeg 后处理成功修复固定 24fps、无音轨、BT.709、体积和 faststart，但没有在不牺牲 source identity
  或制造停顿/ghost risk 的情况下通过 seam；不继续用 crossfade 追绿；
- raw、post-process variants、frames、logs 与 previews 全部留在 repo-excluded research scratch，不进入
  `web/src/assets/cinematic/`、manifest、dist 或 Git。

## 实际执行 provenance

### 输入

| Role | Identity |
|---|---|
| Video1 | repo 外 Seedance success MP4，SHA-256 `acf68ba63a3382f4c79bee090ca9c89ff39727e35af26685aba1c9cc1add56c4` |
| Image1 | `portal-mother-image-source-v2.png`，SHA-256 `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e` |
| Mode | official 即梦 `Seedance 2.5 / 智能编辑`，单 Video1 edit + Image1 reference |
| Timeline | `00:00 / 00:04 / 00:07` 三个独立高级编辑帧标注 |

执行顺序出现一个必须披露的偏差：400 diagnosis、豆包 audit 与即梦 preflight 在本地通过治理但尚未取得
exact-SHA 公共闭环时，用户已在官方 UI 完成生成。该偏差不改变输出事实，也不得被改写为“public preflight
先于调用”。本审计把实际顺序原样写入历史，后续先完成持久证据公共闭环，再考虑任何新付费请求。

### 实际 Prompt，而非 preflight 长版

preflight 冻结的长版主 Prompt 为 1,439 chars / SHA `edbc0d3...6f388`；即梦页面把主 Prompt、三个帧引用和
三段说明共同计入 2,000 字上限，因此实际执行前压缩。历史长版继续作为 design intent，不得冒充实际请求。

实际主 Prompt：534 chars / 1,522 UTF-8 bytes / SHA-256
`d003f047a80b22f5a66db71a50a2cafe6e881350e5db4dba276aad45966cff10`。

```text
智能编辑视频1，不要用首尾帧重生成或从头重绘。视频1锁定8秒、16:9、固定机位、构图、物体位置和运动连续性；图片1仅锁定建筑、道路、地面、星图、水晶的几何、材质与蓝金视觉。全片保持单镜头、清晰、稳定、深焦。目标是三个主体与整个环境全程同时、明显、精细地运动，强度中等偏强，右侧不可弱化。
左裂隙：加强多层旋涡、纵深能量流、细丝、电弧、周围云和道路的冷蓝联动，不膨胀变形。中央：加强水晶折射/晶格、上下能量、光柱、平台环和倒影循环，不改变晶体或变成纯白。右场：上方星轨/星尘/细丝与下方地形网/节点/平台同级流动，错开相位并有纵深，不得静止。环境：能量贴建筑接缝和道路流动；地面焦散/反射贴材质运动；云、空气和星尘分层呼吸。主色冷蓝、青蓝、电弧蓝，暖金只少量强调接缝和金属边缘，不做HUD或漂浮光线。
节奏：0–2秒全系统启动；2–4秒同步增强；4秒全幕峰值；4–6秒持续后回落；6–8秒仍运动并平滑回到接近0秒的相位、曝光、速度、光流和状态，使末帧衔接首帧。
禁止镜头移动/缩放/旋转/呼吸、主体漂移、几何融化或重绘、增删物体、右场静止、主体或环境单独表演、全屏雾、曝光脉冲、纹理沸腾、过曝、HUD、文字、logo、水印、切镜、黑屏和淡出。冲突时优先保留几何与材质。
```

三个帧说明：

| Frame | Chars / bytes | SHA-256 |
|---|---:|---|
| `00:00` | 77 / 227 | `0a08104a664bb90b7c21257a62ec1f8e1588c9ed9e1e14ebee3529620492bccc` |
| `00:04` | 84 / 240 | `5048e313784914378dd841b1ac451dd5197dd678330a5d592627659011f944b6` |
| `00:07` | 80 / 220 | `b9011e0f9b24589238a744fde73ac04cb7ff48ac9d025a39b98fc7c1e1fa7712` |

```text
[FRAME 00:00]
三框对应左裂隙、中央水晶/光柱/平台、完整右场，三者与环境从首帧同步启动。道路箭头为冷蓝能量沿材质流向裂隙；定位处建筑接缝、云、空气、地面和反射同步呼吸。

[FRAME 00:04]
00:04全幕峰值：三框内运动同级清晰；箭头沿裂隙旋涡、水晶光柱、右侧星轨/地形及道路流动；定位处建筑、云、地面焦散和反射同步最丰富。保持锐利稳定，勿漂移、重绘、过曝。

[FRAME 00:07]
00:07进入循环回收：三框、道路及定位环境继续运动，不冻结、不倒放；相位、亮度、速度、光流、反射和云层平滑接近00:00，末帧接首帧；勿淡出、黑屏或移动镜头。
```

为避免把页面本地 ephemeral `@video-frame-saved-*` ID 写成可复现业务身份，审计使用稳定
`[FRAME 00:xx]` placeholder 组成下方 canonical request projection：822 chars / 2,256 bytes / SHA-256
`6dcd29d4af7e172a0439bd8f5cb8ce690edd336e7cc3e2bde22db4029a49d411`。页面实际可见总字符约 877；三个帧引用
均由高级编辑 UI 生成，不是普通文本伪造。

## Raw output

文件 SHA-256：`4d3660bb1eba609cd2773520d0b3d5e124ad6120b5000c2185db4d06d6be155b`。

| Field | Observed |
|---|---|
| bytes | 9,641,527 |
| container/video | MP4 / H.264 / yuv420p |
| dimensions | 1280×720 |
| duration | 8.063991 s container；8.016667 s video |
| decoded frames | 193 |
| frame rate | nominal `60/1`、average `11580/481`；不是发布所需 fixed 24fps |
| audio | AAC present；Portal runtime 禁止音轨 |
| visible watermark | 抽帧人工审查未发现 |
| cost/credits | 本轮页面实际积分未形成可信 body-free 读数，保持 unknown；不猜测 |

### Source、运动与接缝

| Metric | Result | Gate / meaning |
|---|---:|---|
| v2 mother → first | 0.889072 | `< 0.95`，source identity fail |
| input Video1 first → output first | 0.874379 | Smart Edit 仍改变开场，不是逐帧 copy |
| aligned full stream input → output | 0.967997 | edit 大体保留 input，但不等于 v2 identity |
| first → 4 s full frame | 0.888277 | 有明显画面变化 |
| first → 4 s left / center / right | 0.858797 / 0.917767 / 0.889054 | 三大区均参与；center 相对最弱 |
| adjacent DSSIM p95 | 0.011254 | 正常相邻运动基线 |
| last → first DSSIM | 0.046536 | `> max(1.5×p95, 0.03)=0.03`，seam fail |

first→4 s 九宫格 SSIM 为：

```text
0.899748  0.937756  0.863152
0.779295  0.866782  0.869711
0.900317  0.949680  0.934832
```

九格都有变化只能证明 coverage，不能单独证明自然 motion。人工抽帧确认：左 Rift/道路、中央水晶/平台、右侧
上方星轨与下方能量地形都参与；镜头和大建筑未见明显 push/melt/reframe。相对 prompt 目标，整体建筑接缝、
地面焦散和多层空气仍偏保守，中央内部折射弱于左/右。该结果支持 official Smart Edit/motion direction 继续
开放，不支持当前 raw asset 进入 production。

## 零费用后处理实验

实验从 raw output 单次解码分别构造：

1. fixed 24fps/no-audio normalization；
2. 6/9/12-frame `xfade`；
3. 显式 tail→head blend 与 8s retime；
4. 不 retime 的 7.75/7.625/7.5s native overlap；
5. 尾段向首帧 settle 与 exact-anchor diagnostics。

所有实验为 repo 外 sibling，不串行压缩，不覆盖 raw。最佳机械 seam 是 12-frame native overlap `J`：

| Field | J result |
|---|---|
| SHA-256 | `dadd7c3df02f6c44d3d0516e1a72c055db8fcad072a05d99dd18d199f3aa0b37` |
| bytes / duration | 2,991,793 / 7.5 s |
| contract | H.264, 1280×720, fixed 24fps, 180 frames, yuv420p, BT.709, no audio |
| mother → first | 0.849216；因 phase rotation 比 raw 更差 |
| first → mid left / center / right | 0.847764 / 0.906754 / 0.832192；运动仍保留 |
| adjacent p95 / seam / allowed | 0.010712 / 0.042684 / 0.03；仍 fail |

8.000s normalization 约 3.34MB，但 seam 反而为 0.062851；其他 xfade/blend/settle 候选约
0.0455–0.0539，错误权重诊断最差到 0.0917。强制复制首帧可以机械压低 last→first，但会形成 1/24s duplicate
或尾段静止/ghost 风险，违反“持续运动下自然回收”意图，未作为采用候选继续追绿。

## 下一动作

1. 先把本 result/audit 与 400 diagnosis、豆包 audit、actual-prompt correction 完成本地门和 exact-SHA public CI；
2. no-cost 拆分 v2→first 差异为 geometry/edge anchor、material/color 与 intended energy/light 三层；
3. 不静默降低 `0.95`。若 full-frame SSIM 同时惩罚预期动态与错误结构，只能以新 ADR 增加结构硬门，不能事后
   调低旧门保样本；
4. geometry/material 若稳定，raw 只可作为 motion donor，后续研究真正 source-aware motion/loop contract；
   若结构漂移，停止后处理，下一 paid call 必须改变 source-side first/last/keyframe 控制，不原样重抽；
5. 在新 source-side preflight 公共闭环前不发起新生成、不接 runtime、不进入 Account media。

## 零费用 identity fault split（T/X source-anchored candidates）

为避免把 raw Smart Edit 的 `0.889072` 直接解释成“模型一定重绘了结构”，本轮对已经存在的
source-anchored T (H.264) / X (VP9) 研究候选做了单独的三层拆分。测量先把 active v2 mother 用 Lanczos
缩放到 `1280×720`，再统一到 `yuv420p/BT.709`；因此不会把 RGB/full-range PNG 与视频 limited-range 解码
差异误记成内容漂移。

| Signal | T / H.264 | X / VP9 | Interpretation |
|---|---:|---:|---|
| Mother → first SSIM | `0.954464` | `0.958294` | 两个候选均越过冻结的 `0.95` source gate |
| Mother 直接编码→解码 baseline | `0.995139` | `0.995139` | 颜色/量化本身的可接受上限参照 |
| Mother → WebP poster SSIM | `0.987838` | `0.987838` | 同一张 q95 WebP 海报越过 `0.98` poster gate；AVIF 未采用 |
| Poster → first SSIM | `0.992257` | `0.988248` | poster 与两种 codec 的开场身份一致 |
| Edge correlation | `0.995571` | `0.997081` | 建筑/道路/水晶/星图的大边缘仍高度对齐 |
| Luma MAE (8-bit) | `1.3935` | `1.3371` | 剩余差异主要是动态与编码，而非大面积结构错位 |
| Seam DSSIM | `0.027807` | `0.029357` | 两种 codec 均在 `0.03` floor 内；仍需浏览器两轮审查 |

时域能量也按三大区和近/中/远景分别统计：T 的 left/center/right 为 `4.452/3.238/2.472`，X 为
`4.408/3.188/2.450`；T 的 near/mid/far 为 `2.456/5.495/2.195`，X 为 `2.426/5.436/2.169`。
这证明运动没有只落在单一主体或单一雾层，但它只是 coverage/energy 证据，不能替代人工审片对
“景内材质真的在动、而不是叠加特效”的判断。

完整机器记录见 [`portal-motion-candidate-tx-v1.json`](../assets/8e-portal/portal-motion-candidate-tx-v1.json)。
该文件将 T/X 明确标为 `research-candidate`/`not-adopted`：scratch 视频仍不在 Git，poster SHA 在真正
复制进 adoption package 前保持 pending，Account 四个 rendition 和浏览器/static-edge 证据也尚未补齐。
因此本拆分只收窄了“geometry/material 是否稳定”的问题，不改变 Portal 仍未进入 runtime、也不改变
GLM-5.3/Flash 必须排在 Portal 闭环后的顺序。
