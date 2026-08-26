# 8E Video Bake-off：Dragon/Veo Portal v2 单样本审计

## 1. 裁决

- checkpoint：`8e-productization / portal-motion-polish / runtime Task 5 media bake-off`；
- transport/model：DragonAPI relay，`Veo3.1-quality-official`；
- verdict：`rejected_for_source_fidelity_loop_seam_full_scene_motion_distribution_raw_encoding_and_budget`；
- external model calls：`1` 次 POST；没有自动重试、第二个 Veo 任务、充值或订阅；
- production adoption：`false`；原片、兼容预览、抽帧与统计只保存在 research scratch，不进入 repo/runtime。

Veo 相比 Wan 让左侧 Rift、道路能量和右侧星图出现更明显变化，但画面仍像几个焦点对象轮流发光，未形成
MotionSites 类整幕持续运动。更明显的局部动画不能弥补 source 首帧、loop seam、运动分布和发布编码硬门失败。

## 2. 冻结输入与调用事实

- source：`portal-mother-image-source-v2.png`；SHA-256
  `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`；首帧和尾帧均使用同一公开 exact-SHA URL；
- prompt：UTF-8 1662 bytes；SHA-256
  `f324264150a729daad5e7be71d5e762e8fec496d98e94ffebd2fdddcbd2f36fc`；与 Wan 使用同一 semantic brief；
- request：8 秒、16:9、1080p、audio false、`compressionQuality=lossless`、`resizeMode=pad`，同图 first/last；
- task：公开 task ID `task_UaNhoqYyuwc5J72zsqfQSH6vnQrKEQSX`；控制台记录 162 秒、成功、100%；
- Key 只由用户在本机可见 PowerShell secure prompt 输入，清零后退出；Key、prompt 正文、签名 URL与 raw
  response 未写入 repo 或状态文件。

Dragon 文档声称 `GET /v1/videos/{task_id}/content` 返回二进制，但该成功任务在该端点实际返回 HTTP 403。
任务查询响应另有 `result.data[0].url`，host 为 `files.toapis.com`；只读恢复脚本从同一成功 task 下载该 URL，
`post_attempts=0`。因此 403 是 relay 下载合同 Bad Case，不是模型任务失败。一次错误剪贴板输入造成 body-free
401 查询后已停止；它没有创建任务、上传素材或产生生成费用。

## 3. 输出机械证据

原始研究文件：
`C:\Users\33502\Documents\Agent\tmp\riftcoach-task5-video-bakeoff\dragon-veo31-quality-portal-v2-first-last-1080p-8s.mp4`

| 项目 | 实测 | 门/裁决 |
|---|---:|---|
| output SHA-256 | `b707bb177c17dcfb0af09a1bd8fb6d55adf2f3a7c876f238ea6c497d4cbfa913` | provenance only |
| bytes | `254,156,130` | reject；Portal desktop H.264 门 `≤5,500,000` |
| duration / frames | `8.000s / 192` | pass |
| dimensions / fps | `1920×1080 / 24fps` | pass |
| codec / profile / pix_fmt | H.264 / High 4:4:4 Predictive / `yuv444p` | reject；Windows/常见浏览器兼容性与发布合同要求 `yuv420p` |
| audio streams | `0` | pass |
| BT.709 metadata | 未完整声明 | reject until normalized/verified |
| source v2→first SSIM | `0.587962` | reject；要求 `≥0.95` |
| first→last SSIM | `0.838369` | seam DSSIM `0.161631` |
| adjacent DSSIM p95 | `0.009446` | seam threshold `max(1.5×p95,0.03)=0.03` |
| seam | `0.161631 > 0.03` | reject；约为 adjacent p95 的 17.1 倍 |
| visible watermark | 未观察到 | pass for this item only |

为方便人工播放，另做 research-only 兼容预览：H.264 High / `yuv420p` / 24fps / faststart / no audio，
SHA `795202e2570cc0aaa53b118e95df941742dbb86c5a510420cfdba734586949a8`，9,599,406 bytes。它仍高于发布
预算，只解决本机解码，不改变 source/seam/motion 裁决，也不进入 runtime。

## 4. 视觉与运动证据

抽帧时间为 0/2/4/6/末帧。first→4s regional SSIM：左 `0.793970`、中 `0.879543`、右 `0.884153`。

人工播放与 contact sheet 的结论：

- 左 Rift 有明显旋转/亮度变化，道路出现单条能量传播，中央水晶/光柱呼吸，右星图节点阶段性显隐；
- 建筑主体、远景空间、云雾层、前景平台、反射和环境光没有形成持续、互相错相的分层运动；
- 视觉注意力在少数命名焦点之间切换，像“几个灯轮流亮”，不是整张场景始终活着；
- 0→8 秒的状态/细节没有闭合，循环点相对普通相邻帧产生明显跳变；
- 全局构图大体保留，但模型重新生成了大量细线、纹理、亮度与局部形状，因此原尺寸 source identity 硬门失败。

本地 evidence：

- `...\dragon-veo-audit\contact-sheet.png`；
- `...\dragon-veo-audit\source-vs-first.png`；
- `...\dragon-veo-audit\source-first.log`、`first-last.log`、`adjacent.log` 与三分区 log。

## 5. 原因分析与制片路线裁决

以下是由输入、两个真实样本和成片行为支持的工程推断，不声称知道闭源模型内部机制：

1. prompt 已明确要求所有层运动，但按 Rift/道路/水晶/星图逐项重述画面，又同时使用 `subtle`、`slowly`、
   `restrained`、`gently`、`almost imperceptibly` 和 `extremely slow`；模型把高显著对象当成主要动作清单，
   并被 motion language 主动压低了幅度；
2. Google 的 I2V 官方 best practice 要求源图已提供场景/风格时以 motion-only prompt 为主，避免重复描述画面。
   本次 1662-byte brief 没有充分遵守该原则；因此本样本不能代表 Veo 在正确 motion-only direction 下的上限；
3. “同一图精确首尾 + 像素稳定结构 + 整帧持续运动”在单次扁平 I2V 中互相拉扯；模型用局部亮灭和形变满足
   容易的部分，既没有恢复 exact source，也没有得到自然全局 motion；
4. 扁平母图没有 background/midground/foreground、遮挡、反射和光照 mask，模型不能稳定恢复 MotionSites
   类分层视差；
5. Wan 选择低价值纹理/呼吸，Veo 选择更明显但焦点化的局部动作和重绘。它们拒绝的是当前“扁平整景 +
   同图 first/last + 过度密集/保守 prompt”样本，不构成对 Wan/Veo 或整条生成式 A 线的永久拒绝。

因此不继续用 Vidu/Kling/MiniMax/Seedance/Grok 原样复制同一 prompt/首尾策略换模型抽卡。它们仍可在 C 线中
只制作有机 motion plates；也保留为校正后 A 线 comparator，须使用短 motion-only brief、明确可读的全幕环境
运动和不过度互斥的稳定约束。其单样本采用门和调用边界继续有效。

## 6. 唯一下一动作：混合 C 线 Portal 分层 proof（A 线不永久关闭）

Task 5 留在 Portal，不把失败方法带到 Account，也不跳 Task 6：

1. 先完成 no-paid-call proof：从 v2 建立可移除的分层/mask/inpaint 资产门，至少覆盖远景/云雾、Rift 内层、
   道路/反射、水晶/塔体、右星图、前景
   粒子/环境光；结构轮廓始终由母图锁定；
2. 冻结全幕 motion coverage：背景雾/星轨慢循环，中景 Rift/远景视差，道路/平台反射贯穿传播，水晶内部
   折射与塔体金缝错相，右星图整体漂移+节点脉冲，前景粒子/镜面扫光持续运动；没有单一静态大区；
3. 生成模型只提供不含建筑拓扑的有机 loop plates；HyperFrames exact renderer 或等价 frame clock 负责结构
   合成，使用自定义 FFmpeg encoder，不采用已失败的默认 MP4；
4. 各层使用不同周期/相位/缓动，首尾位置、相位、曝光和速度严格相同；镜头视口锁定，允许层间微视差，
   不允许 free-camera zoom/reframe；
5. 先做一个 8 秒 1080p Portal proof，仍通过同一 source/seam/full-frame/manual/codec/budget 门；如果分层
   质量、整幕自然度或维护成本不合格，则以一次新采用门重开校正后的 A 线：只给首帧、短 motion-only prompt、
   明确大幅环境运动，生成主体后由确定性 seam construction 收口，不再把相同 source 同时强塞为尾帧；
6. C proof 或校正 A comparator 通过后才恢复 Account source gate → 五英雄逐位 → Account loop 的既定顺序。

官方复核：

- Google I2V best practice：<https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/best-practice>；
- Google first/last frame contract：
  <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-first-and-last-frames>；
- Dragon Veo 专用文档明确 `image_urls` 是首帧、`metadata.lastFrame` 是尾帧，且必须配合使用；本次字段映射
  与文档一致，不能把成片问题归因于字段名错误。
