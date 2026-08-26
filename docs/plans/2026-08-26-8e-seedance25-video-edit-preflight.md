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
- references：Video1 使用 `video_with_roles=[{url:<source result>, role:"reference_video"}]` 保存已有节奏/三个正确
  主体动效；Image1 使用 immutable v2 `image_with_roles=[{url:<v2>, role:"reference_image"}]` 锁定建筑、道路、
  地面、星图、材质与线稿。双锚点不混用 first/last frame；image URL HEAD 200、image/png、2,268,033 B，
  SHA `8134c0ca...1a06e`；
- positive prompt：`portal-motion-v6-edit-seedance25.txt` v6.1，2,368 B，SHA
  `9cdcf28e007a8c5a52a8692d4bcaea288b024e2c57fede393f0f9edf4f664ac8`；
- runner：`run-dragon-seedance25-video-edit-once.ps1`，SHA
  `08834b8a3f5198adf6c0fa520a82fcbcc295c6a1b865a20c907b2a64a38173b0`；PowerShell 7 parse 0 errors；
  静态审计恰好 1 个 POST callsite、2 个 GET callsite（source/poll）；
- post：最多 1 次；无 retry、无 top-up、无第二 task；Key/raw response/signed URL 不落盘；
- output/status：唯一新路径，均在 repo 外 research scratch。

## 提示词策略

采用官方示例风格的 `Edit Video1. Use Image1 ... Keep ... unchanged. Adjust only ...`。Video1 不是运动目标的
唯一来源：Image1 单独约束静态身份，避免把现有雾带放大成主要语言。新增运动只绑定差分热图证明偏静的顶部建筑、
底部中央地面、道路反射、远景云层和星图细节；显式禁止通过增强 Rift/水晶/右能量场来冒充改善。

时间轴只控制同一周期的丰富度，不让区域轮流表演：全部层 0–8s 同时运行，4s 达材质运动峰值，8s 回到开场相位；
雾必须分成位于前景之后、建筑之间和远景之前的多层 wisps，不允许单层 screen-space fog sheet。

## 干扰风险与采用门

`video_operation=edit` 仍是生成式编辑，不保证逐像素保留 Video1。控制方式是：

1. 原片独立保留，编辑输出是 sibling candidate，永不覆盖；
2. Video1 锚定已有时间运动，Image1 锚定原始几何/材质，prompt 限制“只改静区”；
3. 若 edited output 的 camera/主体/geometry/source identity 任一劣于原片，即拒绝 edited sibling 并回退原片；
4. 只有静区实质改善且不牺牲三主体/镜头时，才继续 seam/rendition proof。

## 费用与停止线

模型广场显示 `$1.4946/秒`，输入成片为 8.041667 秒，预计约 `$12.0191`；但编辑计费单位/最低时长未在页面
单独标明，所以提交前需以余额和实际账单为准。只有公共 preflight 通过并向用户披露估算后才允许一次 POST。

编辑成功也不等于 adopted：仍需人工检查镜头锁定、已有三主体是否保留、静区是否真的产生景内运动，再做 source/
seam/codec 评估。编辑若失败或只加雾层，不自动重试、不立刻换模型；按 RQ-128 保留 fault domain。

## 官方来源

- DragonAPI 专用页：`https://docs.dragon3api.com/#/model/video-seedance-2-5-generation`
- ByteDance Seedance 2.5：`https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5`
