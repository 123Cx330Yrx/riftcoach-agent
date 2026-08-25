# 8E Video Bake-off Preflight（Task 5）

## 状态与边界

- 检查点：`8e-productization / portal-motion-polish / runtime Task 5 media bake-off`
- 状态：preflight/design only；没有读取 Key、创建 Key、上传 Portal 母图、购买 credits、安装 HyperFrames/Remotion、
  调用视频模型或把任何生成结果写入仓库。
- 前置：Task 1–4 已由 `1b146e6/32826953474`、`2111a78/32833608622`、`0198fc9/32836430378`、
  `52def9c` + `d58ba15`/`32841900909` exact-SHA 公共关闭；Kimi 12s/1080p 是 rejected Bad Case。

## 目标

回答一个具体问题：哪条制片路线能在确认母图/后续 Account source 上保持构图、几何和材质身份，同时产生真正的全帧循环？
不是比较“哪个模型最火”，也不是用一次网站预览决定采用。

## 三条路线

| 路线 | 候选 | 负责什么 | 当前状态 |
|---|---|---|---|
| A 生成式 I2V | 官方 Veo 3.1、Luma Ray、Wan 2.7；Seedance 2.x 需重新核对官方实际 model ID | 生成环境雾、光线、粒子、能量等有机运动 | candidate-only；任何调用需单独冻结额度/隐私/删除/地域 |
| B 确定性 frame render | HyperFrames 或 Remotion | 锁定镜头、建筑、水晶、道路拓扑、遮挡和循环时间 | deferred；安装前需 skill 安全审计、许可和隔离 spike |
| C 混合式（推荐） | A 只生成低风险有机 plates，B 锁定结构层 | 同时满足全局运动与 source fidelity | primary candidate；尚未采用 |

## 官方能力证据（2026-08-25 定向复核）

- Google Vertex AI 的 Veo 3.1 `veo-3.1-generate-001`/fast 公开文档列出 first+last frame、16:9/9:16、1080p、
  24fps、4/6/8 秒以及 project quota；I2V/first-last 仍带 Preview/Pre-GA 条款。来源：
  <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames>、
  <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate>。
- Luma Dream Machine/Ray 当前公开 API 有 `loop`、`keyframes`、`ray-2`/`ray-flash-2` 和 start/end keyframe 形状；
  官方指南还说明 keyframe/loop/extend 的使用方式。来源：
  <https://docs.lumalabs.ai/reference/creategeneration>、
  <https://lumalabs.ai/learning-hub/how-to-use-keyframes>。
- 阿里云 Wan 2.7 官方 API 明确支持 first-frame、first+last-frame、video continuation；任务异步、API key/endpoint
  与区域绑定，示例 model ID 不能直接当作本项目可用账号的准入证明。来源：
  <https://help.aliyun.com/en/model-studio/image-to-video-general-api-reference>。
- Seedance 2.x、Kling 3、Grok Video、Hailuo、Sora 2、Vidu Q3 和 Wan 2.6/2.7 的中转站 slug/价格只作为用户提供的
  candidate catalog；在官方 model/version mapping 未确认前，不把 `official` 后缀当厂商身份事实。

## 候选准入表

每个候选必须先得到一行可冻结记录；缺一项就保持 `catalog-only`，不上传母图：

| 维度 | 必须记录 |
|---|---|
| identity | 官方 provider、model ID/version、endpoint/region、官方文档 URL；relay 映射证明 |
| controls | first frame、last frame、reference、loop、locked camera、aspect ratio、duration、resolution、fps |
| transport | 官方 API/Console 或 relay；请求/结果是否二次压缩、加水印、保留原图/视频 |
| privacy | 训练用途、保留期、删除接口、跨境/区域、是否可传项目母图；不传玩家/比赛数据 |
| operations | async task/poll、timeout、retry、错误码、调用上限、body-free provenance、费用估算 |
| adoption | license/商用条款、结果移除路径、可复现参数与 raw response 不入仓库 |

## 固定 bake-off 输入与停止线

- 所有路线使用同一获准 Portal source、同一 8 秒 motion brief、同一 16:9/portrait 约束；Account 先不参加，直到
  RQ-117 拓扑与逐英雄 source 通过。
- A 线第一轮每候选最多 1 个低成本样本；同一候选最多 2 次总调用（首尾帧失败或服务错误不自动重试）。
- B/C 线只生成本地 no-runtime preview；任何新 skill/依赖必须先走 `skill-vetter`/安全审计和隔离 spike。
- 任一候选违反 source 首帧身份、camera locked、建筑/水晶/道路几何、全帧运动或隐私门，立即 `rejected`；不靠
  upscale、锐化、暗化或 CSS 假 parallax 补救。

## 评分顺序

1. source→首帧 SSIM ≥ 0.95，poster→首帧 SSIM ≥ 0.98；Portal source SHA/水晶/塔体/左右锚点人工通过；
2. locked camera，不能自动 zoom/reframe/crop；
3. 建筑直线、星图节点、水晶边缘、道路拓扑无时空漂移；
4. 全帧环境层持续运动，不能局部光点冒充全局 loop，不能纹理沸腾、融化、闪烁或凭空增删；
5. 末→首 seam 通过 Task 4 DSSIM 门，Chromium desktop/390 两轮 dropped-frame ≤1%；
6. VP9/H.264、24fps、yuv420p、BT.709、无音轨、faststart、bytes/budget；
7. 许可、隐私、地域、费用、可移除性和返工次数；

质量硬门先于价格/标称分辨率。没有路线通过，就保持 poster-only，不降低 RQ-108 视觉目标。

## 采用门与下一步

Task 5 只在用户明确的费用/敏感图上传边界下进入实际调用。下一动作仍是：

1. 重新读取官方/实际账户可用 model catalog，锁定最多两个 A 线候选和一个 B/C 隔离候选；
2. 为每个候选生成 body-free preflight record（不含 prompt 正文、Key、cookie、原始响应）；
3. 若候选映射/隐私/费用都可接受，再单独请求实际生成授权；
4. 结果全部按 adopted/candidate/rejected 写入不可覆盖 audit，不直接接入 RiftCoach runtime。

## 面试准确说法

> 我没有把视频模型直接塞进前端，而是先做一个可审计的制片 bake-off：生成模型只负责低风险有机运动，结构层由
> 确定性合成锁定；所有候选先过首帧身份、几何漂移、全帧运动、loop seam、编码、隐私和许可门。Task 4 的审计器
> 已公共验证，但当前还没有生产媒体或模型准入。
