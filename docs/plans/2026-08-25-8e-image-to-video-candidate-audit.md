# 8E Image-to-Video 候选审计

## 目的与边界

本文记录 RQ-108 的离线制片候选，不把任何视频生成服务接入 RiftCoach runtime，也不保存用户账号、Prompt
正文、Cookie、Key 或生成平台原始响应。本次只审计用户已在本机预览的一个 Kimi 输出及公开官方能力边界。

## Kimi 候选 v1：rejected Bad Case

- 可见页面：用户 Chrome 中的 `http://localhost:7100/#`；页面本身不是 RiftCoach runtime。
- 媒体：`hero-loop.mp4`，本地临时只读提取；不复制进仓库。
- SHA-256：`57043c606aff149f179b65690096a50c145491bee268724d36f61a0f64ff9c95`。
- container/codec：MP4 / H.264 High / yuv420p；1920×1080；30 fps；12.0 s；360 frames；无音轨。
- 文件/码率：6,048,617 bytes；约 4.03 Mbps。
- 页面：`autoPlay + loop + muted + object-fit: cover`，视频正常解码播放；网页 CSS filter 为 `none`。

因此“网页没播放成功”不是主因。即使文件标称 1080p，人工帧审查仍看到有效纹理发糊、母图左 Rift/右星图
被重新取景、中央水晶/塔体比例漂移，主要运动更像整体重绘/缩放和纹理沸腾，而不是各环境层在锁定构图下
稳定运动。

机械辅助结果只用于定位，不单独决定美术准入：

- 母图等比例缩放到 1920×1080 后与视频首帧 SSIM `0.412818`，说明 first-frame/source identity 严重漂移；
- 首相邻帧 SSIM `0.926658`、末相邻帧 `0.889604`、末→首 seam `0.898857`；seam 没有比末相邻帧明显更坏，
  但“能循环”不能弥补构图、纹理和几何不合格；
- FFmpeg blurdetect 全片 mean `3.6650986` 只作同批比较基线，未冻结为通用清晰度阈值。

裁决：`rejected_for_source_fidelity_and_motion_language`。无法从本次证据区分 Prompt、Kimi 插件底层模型、
生成参数与平台二次压缩各自占比，因此不能简单归因于“教程 Prompt 写错”，也不能据此声称 Kimi 永久不可用。

## 下一轮固定横评

每个候选使用相同的获准 source 和正向 motion brief；不把 negative prompt 支持与否强行等同。第一轮只生成
短片，用低成本模型/档位筛选，胜出者再用高质量档：

| 路线 | 官方可用控制 | 初步角色 |
|---|---|---|
| Google Vertex AI Veo 3.1 | first + last frame、16:9/9:16、API/Console | 首尾同图的 loop/source fidelity 主候选 |
| Luma Ray 系列 | start/end keyframes、Loop、Extend | 原生 loop 与环境运动候选 |
| 阿里云 Wan 2.7 | first frame、first+last、续写；官方 API | 国内可达的首尾同图 loop 主候选 |
| 火山方舟 Seedance 2.x | 2.0 系列官方生成 API 已有；2.5 官方公告强化 reference/edit，但当前 API availability 未证实 | 细节/运动稳定候选；调用前以账户实际 model ID/endpoint 冻结可用版本 |
| Runway Gen-4.5 / multi-model API | image first frame、motion prompt；API 可选 Veo/Runway 等 | 快速多模型同界面对照 |
| Adobe Firefly multi-model workspace | Firefly、Veo、Ray、Runway、Kling；image-to-video 与编辑/upscale | 视觉横评与后处理工作台候选 |
| 本地开源 I2V | 取决于本机 GPU、模型许可和可复现脚本 | 只有硬件/许可/质量门可达时进入 |

### B/C 线：确定性与混合式

- `HyperFrames`：Apache-2.0、HTML/CSS/media + seekable animation、逐帧 Chrome/FFmpeg render；官方主 skill
  在 skills.sh 安装量约 240K，仓库约 41.8K stars。它能锁定每帧，但不能从扁平母图自动恢复遮挡层。
- `Remotion`：React frame clock，生态成熟且项目代码易维护；个人/≤3 人免费，组织扩大或自动化产品要重新
  核对商业许可。当前搜到的第三方 Remotion marketing skill 安装/星标很低，不因名字合适直接采用。
- `remotion-to-hyperframes` 只适用于已有 Remotion composition 的迁移，不是本项目新建动画的入口；若试
  HyperFrames，应从官方 `/hyperframes` 主 skill 开始并先安全审计。

推荐 primary candidate 是混合式：先用 Image2/图像编辑把建筑、水晶、道路、Rift、星图、雾/粒子、反射与
光照 mask 分层并补齐遮挡区；HyperFrames/Remotion 锁定镜头和结构层，只让生成式模型提供少量有机 loop
plates。这样可以让整帧持续变化，同时不允许生成模型重画塔、水晶或地图拓扑。

官方能力入口：

- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames
- https://lumalabs.ai/learning-hub/dream-machine-how-to-generate-with-ray2
- https://help.runwayml.com/hc/en-us/articles/46974685288467-Creating-with-Gen-4-5
- https://docs.dev.runwayml.com/api/
- https://www.adobe.com/products/firefly/features/image-to-video.html
- https://help.aliyun.com/zh/model-studio/image-to-video-general-api-reference
- https://api.volcengine.com/api-docs/view?action=CreateContentsGenerationsTasks&serviceCode=ark&version=2024-01-01
- https://github.com/heygen-com/hyperframes
- https://www.remotion.dev/

## 同一验收表

硬门按顺序执行，任一失败即停，不用后期 upscale/锐化掩盖：

1. source 首帧、构图、原水晶/塔体和左右场景锚点；
2. camera locked，无自动 zoom/reframe/crop；
3. 建筑直线、星图节点、水晶边缘和道路拓扑的时空一致性；
4. 全帧环境有分层运动，但没有纹理沸腾、物体融化、凭空增删或闪烁；
5. 末→首 seam 相对相邻帧不过度跳变；
6. desktop/mobile 独立 source identity；
7. 输出/许可允许本地同源发布，并记录移除路径；
8. 通过后才比较分辨率、码率、费用、生成延迟、返工次数和最终编码预算。

本设计门不实际购买 credits、不创建 API Key、不调用上述付费服务。正式横评的模型版本、最多调用数和金额
上限要在执行前冻结；结果无论好坏都记录，不能换样本追绿。
