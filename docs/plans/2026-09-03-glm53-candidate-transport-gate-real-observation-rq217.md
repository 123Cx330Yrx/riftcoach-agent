# RQ-217：关闭顺序修复后的候选 transport-gated 真实观察计划与结果

## 目标

在 RQ-216 的 reader-owned close 顺序修复和同 SHA 公共 CI 之后，用一个受控真实请求
复核此前的 `client_wakeup_close_race` 是否已收敛为干净的客户端唤醒/关闭投影。

## 固定边界

- 实现、观察器、输入计划身份固定为
  `3e028b1217f1274152ba161993287f29188a1b73`；
- 模型固定为普通 API 的 `zhipu/glm-5.3-flash`，阶段固定为
  `before_first_event`；
- 只允许 1 次 provider 请求和 1 次 transport 请求，SDK/HTTPX retries=0，父进程
  30 秒硬截止；不 retry、不 recovery、不发送第二请求；
- 使用官方 TLS transport 外层的 evaluation-only gate；不注册候选、不打开
  `capabilities.streaming`，不触碰产品 Runtime、Workbench 或前端；
- 回执只能包含安全状态投影，不写入 Key、headers、request/response body、正文、
  reasoning、工具参数、request ID 或异常文本；旧 RQ-215 回执不可变。

## 执行与验收

1. 先确认精确 SHA 的公共三 job CI 全绿，再以显式确认参数启动观察器。
2. 观察器在首帧前保持 gate；只在一次 response close 后观察 pending reader 的唤醒和
   reader-owned 资源收尾。
3. 验收请求数、网络标记、gate 生命周期、取消状态、reader 唤醒、close report 和
   `client_wakeup_clean` 投影；对回执执行 canonical round-trip。
4. 无论结果如何，都不追加调用，并把 provider-native/生产能力保持为未证实。

## 实际结果

公共前置条件满足：提交 `3e028b1217f1274152ba161993287f29188a1b73` 的 Actions
run `33727163550` 三 job 全绿。观察器只发送 1 次真实请求，回执写入

`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`

大小 `1284` bytes，SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`。
回执通过 canonical round-trip，`provider_call_count=1`、
`transport_request_count=1`、`network_used=true`、`gate_observation_valid=true`。

`pending_reader_observed=true`、`reader_woke=true`、`cancel_status=returned`，
观察状态为 `pending_cancel_returned`；上游事件、闸门进入、下游关闭和上游 stream
关闭均被观察到。iterator、SDK stream、composite 的 close report 均为 `closed`，
`shared_resource=false`，结论为 `client_wakeup_clean`。`gate_released=false` 符合
首帧前受控停顿协议，表示没有绕过取消闸门。

## 结论与下一门

RQ-217 关闭了“本地 reader-owned 适配器修复是否能在一次真实 transport-gated 客户端
观察中收敛”的问题，但只是在本机受控响应停顿下的客户端证据。它没有关闭 provider-native
取消、模型能力、G53-7、黄金切片、安全部署/合规、公共生产发布或 8F。候选仍 disabled、
未注册，产品默认和 Workbench/Portal/Account/Auth 边界不变。下一步是独立的准入与质量
决策；没有新的明确授权前不再发送真实请求。
