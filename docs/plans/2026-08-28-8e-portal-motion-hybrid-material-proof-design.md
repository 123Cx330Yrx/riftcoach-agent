# 8E Portal Hybrid Material Motion Proof（2026-08-28）

状态：`design-prepared / no-paid-call`。

这是在确认“不重复盲跑 Smart Edit”后的下一条可控路线。它不是把旧 C-line 的线条、圆环或 HUD overlay
重新包装，而是让母图已有的材质在各自遮罩内产生低频、连续、可收口的景内运动。

## 1. 目标与边界

- 母图始终是结构底：建筑、道路拓扑、平台、塔体、水晶外轮廓、星图布局和遮挡关系不重绘。
- 从第一帧到最后一帧，左 Rift、中央水晶/现有光柱、右星图/地形、道路、反射和 near/mid/far 空气同时有
  可感知但稳定的运动；中央事件只是在水晶本体内做一次低幅呼吸。
- 研究 proof 先固定 8 秒/24fps/无音频，目的是验证材质运动语义和 loop clock，不代表最终生产时长；通过后
  再决定是否延长至 10–12 秒。
- 不调用模型、不上传母图、不把 proof 接到 `web/public/assets`。Image2/Photoshop 只有在发现某个具体材质
  缺少可用纹理时才提供局部贴图，不生成新的母图。

## 2. 分层与运动载体

| 层 | 遮罩范围 | 只允许的运动 | 明确禁止 |
|---|---|---|---|
| locked base | 全母图结构 | 不动，只提供锐利结构和真实遮挡 | camera transform、整体位移、重绘 |
| Rift interior | 左侧原 Rift 内部 | 宽幅低频纹理流、轻微折射和错相深度 | 新同心环、尖锐线束、黑洞缩放 |
| road current | 现有道路/裂隙下方通道 | 沿已有路面纹理缓慢流动、首尾同相 | 漂浮 HUD 线、跨画面连线 |
| crystal column | 原水晶轮廓与现有光柱 | 晶格亮度、折射、柱内上下呼吸 | 水晶/平台体积变化、圆顶/水池 |
| right field | 现有星图、节点、地形能量面 | 星尘错相漂移、节点微脉冲、地形表面低频起伏 | 事件外冻结、重新绘制星座网络 |
| atmosphere | 建筑后方、层间、前景的 near/mid/far | 分层视差、云雾密度缓慢呼吸、真实遮挡 | 一层全屏雾盖、模糊整图 |
| reflection/light | 石材、金属、平台和地面已有高光 | 沿材质方向扫过的低频焦散/反射 | 全局曝光闪烁、巨型 bloom |

## 3. 具体实现思路

1. 以母图作为不透明 base texture；先用固定多边形/路径建立区域 mask，不把 mask 本身画成可见线条。
2. 每个 mask 只使用低频噪声/流场 UV 位移、局部亮度/折射调制和极小的 near/mid/far 视差；所有参数由
   一个确定性 frame clock 驱动，首尾使用相同相位，避免随机跳变。
3. 运动材质必须来自原区域的颜色/纹理采样或局部静态 tile；不在画面上新增几何发光路径。这样能保持母图
   清晰，同时让“道路、反射、云和空气也在动”有真实承载面。
4. 中央呼吸事件只修改 `crystal_column` 的折射/亮度 envelope，平台只显示已有环面反射响应；不改变平台
   alpha、轮廓或深度。

## 4. 评审门

- **结构门**：base 几何静态、无 camera drift、无可见 mask 边、无新增几何。
- **覆盖门**：left/center/right 与 near/mid/far 在每个 0.5 秒窗口都有非零且自然的变化；不能由一层雾或全局
  曝光脉冲刷分。
- **审美门**：画面仍锐利、冷蓝/青蓝统一、运动像材质和空气在呼吸，不像线条贴纸或廉价粒子特效。
- **循环门**：固定 24fps、无音频、首尾相位自然衔接，encoded seam ≤ `0.03`；任何“复制末帧”方案都拒绝。
- **降级门**：reduced-motion、Save-Data 或弱设备只保留静态母图/poster，不强行运行 shader。

## 5. 与 Smart Edit 的关系

Smart Edit 已经有一次真实 coverage 证据，但 source/seam 失败；B1 只改变 prompt，不新增控制能力，因此先
延期，不烧第二次。混合 proof 若能在不变形的前提下通过审美门，再考虑让生成模型仅提供 Rift/云/星尘的有机
局部 tile；若 proof 仍显贴纸，则停止 C，不再继续换模型抽卡。

## 6. 需求→实现→验收矩阵

| 用户要求 | C′ 的落实位置 | 验收证据 |
|---|---|---|
| 第一帧全局已在动 | 每个 mask 从 frame 0 启用；不存在 event 才开启的 layer | 0–0.5s、每 0.5s window 的 left/center/right 与 near/mid/far 非零变化 |
| 左 Rift 漂亮且有纵深 | 原 Rift 内 source-texture displacement + 低频折射，宽幅流体，不新增轮廓 | 全尺寸抽帧无硬同心环、无尖锐线束、无黑洞缩放 |
| 中央水晶不变形 | 只裁剪 crystal/column mask；不裁剪或位移 platform silhouette | 结构 edge/平台轮廓对照；无 dome/pool/new volume |
| 右侧同级且持续 | 独立 right-field mask + 星尘/地形源像素错相位移 | burst 前/中/后右侧都能看到自然运动，不能只剩几条线 |
| 道路/反射/云空气也动 | road/reflection/near-mid-far masks 各自使用 source texture 低频流 | 九宫格与深度分层人工审查；排除单层雾盖和全局闪烁 |
| 中段温和 burst | 仅 crystal/column local-light envelope，2–3s 圆润 rise/fall | 事件前后基础层连续；无横向光束、白闪、跨屏联动 |
| 整幕 cool 但不廉价 | 冷蓝材质采样与极低占比局部 glow，暖金不作为运动主色 | 人工审美门：锐利、深焦、无 HUD/cheap bloom |
| 固定镜头与自然 loop | base 不做 transform；所有 layer 由 deterministic periodic clock 驱动 | camera lock、raw frame closure、encoded seam ≤ 0.03；禁止复制末帧 |
| 点击转场不混入循环 | Portal click/Account transition 仍由 React activation state 管理，媒体 proof 只验证 loop | 交互测试单独验证 click hit target、focus、reduced-motion |

这张表是施工合同，不是“实现了就算通过”：任何一行的人工视觉失败都会让 C′ proof rejected，不能用像素
变化、SSIM 或 seam 绿灯抵消。

## 7. C′ 实际 proof 结果与路线退出

本地 HyperFrames proof 已完成 192 帧渲染和 H.264/yuv420p/no-audio 编码；`source→first SSIM=0.967628`、
`first→last SSIM=0.998615`，且 left/center/right 的 0→4 秒变化约为 `0.00576/0.00584/0.00584`，说明
几何底图与运动分布技术上可控。但全尺寸人工审查仍认为运动太轻，局部 source-pixel displacement 有 mask
边缘贴层风险，缺少自然的 Rift/道路/右场/空气材质流动，因此 verdict 为
`research-proof-rejected`，详见 `docs/assets/8e-portal/portal-motion-hybrid-material-proof-v1.json`。

这不是“C′ 完全没用”：它保留了母图锁定、确定性 clock、reduced-motion 和可验证结构门的工程资产；但它不
能作为 Portal 的主运动层，也不继续通过加大 opacity/位移追求更强视觉。下一候选改用中转站 `Kling v3 Omni`
的参考视频 + 参考图模式，让模型负责有机材质和全幕运动；仍保留母图/Video1/source/seam/codec 人工门。
