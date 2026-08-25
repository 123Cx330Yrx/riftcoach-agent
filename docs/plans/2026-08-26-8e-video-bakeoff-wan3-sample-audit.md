# 8E Video Bake-off：Wan 3.0 Portal v2 单样本审计

## 1. 裁决

- checkpoint：`8e-productization / portal-motion-polish / runtime Task 5 media bake-off`；
- transport/model：千问AI平台第一方体验面，`wan3.0-video`；
- verdict：`rejected_for_source_identity_seam_coherent_full_frame_motion_watermark_and_encoding_contract`；
- external model calls：`1`；没有自动重试、充值或第二个 Wan 任务；
- production adoption：`false`；本地结果和抽帧只保存在 research scratch，不进入 repo/runtime。

该结果证明 Wan 3.0 能接受同图首尾帧并完成 1080P 档 8 秒视频，但不证明它能在相同约束下制作 RiftCoach 所需
的全帧无缝 loop。

## 2. 冻结输入与调用事实

- source：`portal-mother-image-source-v2.png`；SHA-256
  `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`；首帧和尾帧均为同一文件；
- prompt：1661 rendered characters；UTF-8 source body 1662 bytes；SHA-256
  `f324264150a729daad5e7be71d5e762e8fec496d98e94ffebd2fdddcbd2f36fc`；
- controls：首尾帧、1080P、8 秒、声音关闭；
- UI preflight Bad Case：扩展重连后首轮尝试的 prompt 未落入 Lexical editor，随后页面发生 React hydration
  error 并退回首页；免费额度保持 100%、无 task/result，因此计为 UI 操作失败、external model calls `0`；
- effective call：发现“模式切换会清空 prompt”后，固定模式/参数，回读 prompt 1661 chars，再上传两帧；提交后
  页面同时证明 frozen prompt、两张 v2 与 `生成中`，因此这是唯一有效调用；
- cost evidence：现有免费额度由 100% 降为 73.33%，未发生充值或账单购买；
- remote result URL/Key/cookie/task body 未持久化。

## 3. 输出机械证据

本地 research path：
`C:\Users\33502\Documents\Agent\tmp\riftcoach-task5-video-bakeoff\wan3-portal-v2-first-last-1080p-8s.mp4`

| 项目 | 实测 | 门/裁决 |
|---|---:|---|
| output SHA-256 | `030a60f106555fa2f77d19865805adc0811a64ebe676df783f85657c1861f58a` | provenance only |
| bytes | `2,057,453` | 低于 5.5 MB H.264 budget |
| duration / frames | `8.000s / 240` | duration pass |
| dimensions | `1918×1080` | reject；目标 1920×1080/manifest identity |
| codec / pix_fmt | H.264 / yuv420p | codec pass |
| fps | `30` | reject；发布合同为 24fps，后期可转码但不能修复生成质量 |
| audio streams | `0` | pass |
| BT.709 metadata | 未声明 | reject until normalized/verified |
| source v2→first SSIM | `0.860852` | reject；要求 ≥0.95 |
| first→last SSIM | `0.902413` | seam DSSIM `0.097587` |
| adjacent DSSIM p95 | `0.005222` | seam threshold `max(1.5×p95,0.03)=0.03` |
| seam | `0.097587 > 0.03` | reject |
| blurdetect mean | `3.7757382` | descriptive；未冻结通用 blur threshold |
| watermark | 可见 `AI生成` | reject for runtime/source master |

## 4. 视觉与运动证据

抽帧时间：0/2/4/6/7.967 秒。first→4s regional SSIM：左 `0.898092`、中 `0.884466`、右 `0.861069`；
全帧 first→2/4/6s 为 `0.894769/0.881635/0.873028`。

这些数值说明输出并非逐像素静止，但人工播放与 contact sheet 看到的变化主要是：

- 局部亮度呼吸、细碎纹理/雾光重绘；
- 中央光束和局部节点微变；
- 没有形成清晰可读的左 Rift 循环、道路能量传播、右星图整体缓慢运动和多层空间视差；
- 因此“像素变化”不能冒充 RQ-112 的 coherent full-frame motion。

本地 visual sheet：
`C:\Users\33502\Documents\Agent\tmp\riftcoach-task5-video-bakeoff\wan3-audit\contact-sheet.png`。

## 5. 原因分析与下一步

这是一项基于证据的推断，不声称知道闭源模型内部行为：

1. 相同首尾图给 first/last interpolation 一个强“回到原图”边界，模型可通过小幅呼吸而不是大范围周期运动满足；
2. prompt 同时要求大量几何/纹理稳定和所有层运动，模型优先满足更容易的保真/低风险部分；
3. 实际首帧/尾帧仍被生成 decoder 重绘，因此既没有得到严格保真，也没有得到足够运动；
4. 第一方 UI 不暴露 watermark-off、seed、lossless/resize policy，并强制 30fps/1918px 结果，适合作为 bake-off
   diagnostic surface，不适合作为生产 export surface。

按首错停止，Wan 不自动重抽。下一候选为 DragonAPI `Veo3.1-quality-official`，继续使用同一 v2、同一 prompt
digest 和同一硬门。如果 Veo 的相同首尾图也只能产生低价值微动，则拒绝“扁平整景 + 同图首尾帧”作为主制片
方法，转向 C 线：生成模型只制作有机 motion plates，HyperFrames/FFmpeg 用周期函数锁结构/镜头/seam。

