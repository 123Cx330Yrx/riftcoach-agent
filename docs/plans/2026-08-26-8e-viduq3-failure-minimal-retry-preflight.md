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

## 3. Studio-contract Vidu 重试的单一假设

用户登录并绑定同一 NewAPI Key 后，创浪云 Studio 的 Vidu Q3 Pro 表单可见并证明：

- 原生模式含 `首帧生视频`，附件正好 1 张；
- 可选择 8 秒、1080p、16:9；预计消耗 `5.28` 额度；
- `生成音频` 是固定参数而非 toggle；`提示词增强` 可关闭，当前已确认关闭；
- 因此 Studio 实际采用的 Vidu first-only 组合与前两个 API task 的关键差异是 audio 固定 true。

保持：Dragon transport、`viduq3-pro`、source、prompt、one image/first-only、8s、1080p、16:9。

改变：删除可选 `seed=127`；把 `audio=false` 改为 Studio 固定的 `audio=true`；保留 `aspect_ratio=16:9`。
该重试只检验“API audio-off/seed 组合是否偏离 relay 当前 Studio contract”，不是盲重抽质量。下载成功后音轨
在本地用 FFmpeg 移除，不进入 runtime。

- prompt SHA：`a38bdcecaf938f65cceaf56ba925491ddd72c7fd4df2a6a83f3eef4965e7bb72`；
- Studio-contract runner SHA：`7f6d2ef42793d97a31374784c99be1d510fb830ea2f91896f8959ad80e950011`；parse pass；
- one POST、same task、no retry/top-up/seed/metadata/payload/callback/off-peak；用户已确认 5.28 额度；
- 若 completed：进入 RQ-127 visual gate；若 generic failed：停止 API/model 切换，fault domain 提升为
  Dragon relay/upstream/first-only channel，需要平台侧 task-id 诊断或改用官方 transport；不再靠删除更多字段抽卡。
