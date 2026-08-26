# 8E Vidu Q3 Failure 与 Minimal Request Retry Preflight

## 1. 首个 Vidu 控制实验结果

- predecessor `e5422fc662315680def2b5c9e495838127ccacbd` / Actions `32938852472` 三 job 全绿；
- task `task_yaHFcfReplOYwgJ0pZ7zQQbIpslOKF90`；`viduq3-pro`、one image/first-only、8s/1080p、
  aspect_ratio `16:9`、audio false、seed 127、prompt SHA `a38bdc...bb72`；
- one POST，queued 160s 后 failed/100%；控制台唯一错误为 `Generation failed: task processing failed`；
- 无 output/result URL，quality unknown；没有自动 retry 或第二 task；
- external video calls 累计 `4`，production media `0`。

## 2. RQ-128 fault-tree 结果

- local runner：task identity/body-free status 正常，Key/auth/JSON create 已通过；
- source URL：当前 HEAD 200 `image/png`、2,268,033 bytes，Range 206；不需要登录；
- request schema：Vidu 专用文档明确 one `image_urls` 是 first-frame、1080p/audio/seed/aspect_ratio 均存在；
- transport/upstream：corrected Veo 与 Vidu 两个 first-only task 在同 Dragon transport 均约 158–160s generic
  failed；Dragon task log 无细分 code；
- quality/method：两次都无 output，保持 unknown，不能判 Veo/Vidu/prompt/first-only/method 失败。

Dragon error 文档把 500/502 归为 channel/upstream anomaly 并建议稍后重试，但 task log 没暴露本次 HTTP code。
因此不能直接断言 transient；只允许一个 request-minimization 假设，不继续换模型。

## 3. Minimal Vidu 重试的单一假设

保持：Dragon transport、`viduq3-pro`、source、prompt、one image/first-only、8s、1080p、audio false。

删除：可选 `aspect_ratio=16:9` 与 `seed=127`。理由是 Vidu 文档写明图生视频比例通常由图片决定；最小官方
图生请求不要求这两个字段。该重试只检验“可选字段/over-specified request 是否触发 relay/upstream 失败”，
不是盲重抽质量。

- prompt SHA：`a38bdcecaf938f65cceaf56ba925491ddd72c7fd4df2a6a83f3eef4965e7bb72`；
- minimal runner SHA：`503a3904fb81ba7c9b6174102118cb8c22168975344ad51cdba0e22694b817b4`；parse pass；
- one POST、same task、no retry/top-up/metadata/payload/callback/off-peak；
- 若 completed：进入 RQ-127 visual gate；若 generic failed：停止 API/model 切换，fault domain 提升为
  Dragon relay/upstream/first-only channel，需要平台侧 task-id 诊断或改用官方 transport；不再靠删除更多字段抽卡。
