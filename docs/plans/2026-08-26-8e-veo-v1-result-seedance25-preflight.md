# 8E Veo v1 复现结果与 Seedance 2.5 preflight

## Veo v1 结果

- preflight `b09d0a5b67bc58dbd6ca105edbf389e552a09d79` / Actions `32957685924` 三 job 全绿；
- Studio readback：2 张同一 v2 source、v1 prompt 1,662 B/SHA `f324264...36fc`、enhancement off、
  first+last、8s/1080p/16:9；
- task `task_v8gAX2IvJT786Y79BLwxeukNx5HHPDW9` one submit，81 秒/100% generic failed；
- 无 output，`$19.712` 已全额异步退款；external video calls `8`，production media `0`。

该结果使“v5 运动约束过重”不足以解释失败：历史成功 v1 的 exact prompt 也失败。当前
`Veo3.1-quality-official` 通道/上游时间状态变化成为主因；Veo 当前暂停，不重试。

## Studio 候选实测

| 模型 | first+last | 时长 | 分辨率 | 音频 | 价格证据 | 裁决 |
|---|---|---|---|---|---|---|
| Seedance 2.5 | 支持 | 4–30s；可选 8s | 480/720p | 可关闭 | 模型广场 `$1.4946/秒`；8s 预计 `$11.9568` | primary |
| Kling V3 | 支持 | Studio 默认 10s | 720p | 可关闭 | `$0.462/秒`；10s `$4.62` | fallback |
| Grok Video 3 | 不支持尾帧；first-only/3 images | 10s | 720p | 无独立显示 | Studio `$0.46` | loop 主候选 reject |

Seedance 不是按热度选择：它是当前 Studio 中同时保持 first+last 与精确 8 秒的候选。Kling 便宜但改变为 10 秒；
Grok 缺尾帧控制。

## Seedance 2.5 请求冻结

- 同一 v2 source 两张，页面 readback `2`；
- mode `首尾帧生视频`、8s、720p、16:9、`不生成音频`、enhancement off；
- Studio v5 prompt 1,776 B/SHA `91ca48b714d7aa7c7263416e8371205e2d0b78a26aeefaeb442a4d080853b322`；
- 目标保持 locked-frame、left/center/right + near/mid/far simultaneous medium motion 与八秒闭环；
- 页面按钮费用显示 `--`，而不是数字；模型广场计价推导为 `$11.9568`。因此当前不得直接点击，必须向用户明确
  披露 price-calculator mismatch，并在用户接受预计金额后才 one submit；no retry。

## Seedance Studio ratio client Bad Case 与修复

- 用户接受预计 `$11.9568`，preflight `81fe9ef/32959781395` 三 job 全绿后只点击一次；
- Studio/NewAPI 在创建 task 前返回 HTTP 400 `TaskTypeConstraint`：first/first+last 输出比例跟随首帧，显式
  `ratio=16:9` 非法；task_id 不存在、费用 `$0`、external calls 仍为 `8`；
- 这是精确 client/UI mapping bug，不是模型 quality/upstream failure；按 RQ-128 可在修复后继续同一授权实验；
- Studio ratio 下拉存在 `adaptive`。已切 `adaptive`，它必须使 first-frame 决定输出比例；其余 model/source/
  prompt/8s/720p/no-audio/enhancement-off 不变；
- 失败会清空附件，用户须重新上传同一 v2 两次。只有 2/2、`adaptive` 与其余 readback 通过后才重新提交一次；
  若仍返回 ratio error，停止 Studio Seedance mapping，不再尝试。
