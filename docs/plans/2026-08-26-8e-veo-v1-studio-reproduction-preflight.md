# 8E Veo v1 Studio 原样复现实验

## 问题

同一 `Veo3.1-quality-official`、同一 v2 source 的早期 first+last 任务曾成功；随后 corrected first-only、v5 API
first+last 与 v5 Studio first+last 均 generic failed/no output。需要区分：

1. 当前 Veo/relay/upstream 的时间性故障；
2. 从 v1 克制运动跃迁到 full-frame medium/strong simultaneous motion 后，单次生成约束过重；
3. 自写 API payload 映射问题。

v5 Studio 也失败已经显著削弱第 3 项，但不能区分 1/2。

## 最小变量

只在 Studio 原样复现历史成功版：

- model：`Veo 3.1 Quality Official`；
- mode：`首尾帧生视频`；同一 v2 母图作为 first/last；
- source SHA：`8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`；
- prompt bytes/SHA：历史 `portal-motion-brief-v1.txt`，1,662 B，
  `f324264150a729daad5e7be71d5e762e8fec496d98e94ffebd2fdddcbd2f36fc`；
- 8 秒、1080p、16:9、提示词增强关闭；Studio 固定生成音频；
- 预计 `$19.712`；用户已明确“那消耗呗”，由用户手动上传，Codex 在 2/2 与公共门后执行一次生成；
- no retry/no second task；失败自动退款也不构成再次调用授权。

## 判读

- `v1 success`：说明同一通道此刻可生成，v5/full-frame medium simultaneous constraint 是主因；后续从 v1
  每次只增加一个运动层，不再跳跃到 v5；成片仍按历史弱动效 sample 单独审计，不能直接 adopted。
- `v1 generic failure`：说明当前通道/上游状态变化更可能，无法由 v5 prompt 解释；停止该 Veo 通道新调用。
- `v1 output but different failure`：按 local/request/transport/output-quality 五层另行归因，不套上述二分。

本实验不联系 QQ 支持、不切模型、不修改 source、不改变前端/runtime，不把成功等同生产媒体。
