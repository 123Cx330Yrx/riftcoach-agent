# RQ-215：候选 transport-gated 一次真实观察计划与结果

## 目标

在 RQ-214 离线闸门和同 SHA 公共 CI 完成后，用一次真实
`glm-5.3-flash` 请求检查：真实流启动后，官方 TLS transport 外层的受控停顿是否能让
当前客户端的 pending reader 被关闭唤醒，并把读取器唤醒与资源关闭结果分开保存。

## 固定边界

- 实现、观察器、输入计划身份固定为 `2acdf795881733e70c9246c48f7147d5136821b5`；
- 模型固定 `zhipu/glm-5.3-flash`，阶段固定 `before_first_event`；
- 只允许 1 次 provider/transport 请求，SDK retries=0、HTTP retries=0、父进程 30 秒硬截止；
- 不执行 recovery、不 retry、不发送第二请求；
- 回执只允许状态、类别、时长、布尔生命周期和安全错误码，不保存任何正文或凭据；
- 不注册候选，不改产品 Runtime、默认模型、前端、Workbench 或 `production_media=0`。

## 实施与验收

1. 先确认 exact-SHA 公共 CI 三 job 全绿，再执行一次带显式确认参数的观察器。
2. 将既有 gate 包装在官方 TLS `HTTPTransport` 外，并沿用现有环境 proxy；不打印 proxy 值。
3. 校验 provider/transport 请求数均为 1，回执可 canonical round-trip，且没有敏感键。
4. 只根据 `pending_reader_observed`、`reader_woke`、gate close 和分资源 close report
   解释结果，不把客户端结果写成 provider-native 能力。

## 结果

公共 CI run `33721483490` 在精确提交 `2acdf795881733e70c9246c48f7147d5136821b5` 上三 job
全绿。真实请求恰好 1 次，回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`
为 `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`。
真实网络已使用；gate 进入，pending reader 形成并在 `31ms` 内唤醒。取消抛出安全错误码
`zhipu_stream_close`，iterator/composite 关闭投影为 failed，而 SDK stream 为 closed，
故结论为 `client_wakeup_close_race`。

## 结论与下一门

本批完成了“真实流启动 + 本机受控停顿”的客户端观察，但没有完成 provider-native close、
模型能力、候选注册或生产准入。下一检查点为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`；
后续关闭顺序修复、provider response 取消拆分或新的真实请求均需独立决策和授权。
