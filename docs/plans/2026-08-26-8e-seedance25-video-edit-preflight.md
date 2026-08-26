# 8E Seedance 2.5 视频编辑增强 preflight

## 初学者说明

当前 Seedance 成片已经有正确的三块运动：左侧 Rift、中央水晶、右侧能量场；问题是顶部建筑、道路/地面、
反射和远景空气偏静，像只有一层雾在扫。这个检查点不重新从母图生成，而是让模型读取现有成片作为“视频参考”，
在保留已有构图和运动的前提下编辑安静区域。

## 为什么这是真编辑

DragonAPI 的 `seedance-2.5` 专用文档明确提供：

- `video_operation`: `generate | edit | extend`；
- 编辑必须提供 `video_with_roles`，每项 `role: reference_video`；
- 编辑/延长使用 `duration: -1` 自动沿用输入时长；
- 编辑、延长和首尾帧使用 `aspect_ratio: adaptive`；
- 视频最多 10 段参考，公共模型名固定为 `seedance-2-5`。

这与 Studio 主编排器当前的上传 input 不一致：主编排器虽然显示“视频×3参考”，实际 input 只接受图片 MIME，
因此不能把它当成可靠的视频编辑入口。Runner 改为直接调用文档化 API。

## 冻结请求

- source task：`task_w6ggXo15mMMw5Y3KMu9CfLK1QLevULvW`（先 GET，临时取得 result URL，不写 signed URL）；
- model：`seedance-2-5`（页面显示 Seedance 2.5，但公共 API 名按专用文档小写）；
- operation：`edit`；`duration=-1`；`aspect_ratio=adaptive`；`resolution=720p`；`output_format=mp4`；
  `generate_audio=false`；
- reference：`video_with_roles=[{url:<source result>, role:"reference_video"}]`；不混用 image/first/last；
- positive prompt：`portal-motion-v6-edit-seedance25.txt`，1,739 B，SHA
  `68c1aa10b0a12958dfb50826634c780046cd1672f8e4b33608d704534ea61728`；
- runner：`run-dragon-seedance25-video-edit-once.ps1`，SHA
  `6b5c6bef3060cf7111c2cab862a0f67bacaf313a5447c7acee3b92dbe6a9901e`；PowerShell 7 parse 0 errors；
- post：最多 1 次；无 retry、无 top-up、无第二 task；Key/raw response/signed URL 不落盘；
- output/status：唯一新路径，均在 repo 外 research scratch。

## 提示词策略

使用时间段而不是效果清单：0–2s 环境流动建立，2–4s 多层持续，4–6s 达到丰富峰值，6–8s 回到开场相位；
明确“编辑 Video1、保留现有镜头/三个正确主体运动”，把新增运动绑定到道路、地板、建筑缝、反射、远景云层、
星图细节和材质遮挡；禁止 HUD、屏幕空间雾幕、整体漂移、重构图、添删物体和几何融化。

## 费用与停止线

模型广场显示 `$1.4946/秒`，输入成片为 8.041667 秒，预计约 `$12.0191`；但编辑计费单位/最低时长未在页面
单独标明，所以提交前需以余额和实际账单为准。只有公共 preflight 通过并向用户披露估算后才允许一次 POST。

编辑成功也不等于 adopted：仍需人工检查镜头锁定、已有三主体是否保留、静区是否真的产生景内运动，再做 source/
seam/codec 评估。编辑若失败或只加雾层，不自动重试、不立刻换模型；按 RQ-128 保留 fault domain。

## 官方来源

- DragonAPI 专用页：`https://docs.dragon3api.com/#/model/video-seedance-2-5-generation`
- ByteDance Seedance 2.5：`https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5`
