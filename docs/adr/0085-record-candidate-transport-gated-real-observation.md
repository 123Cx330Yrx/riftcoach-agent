# ADR-0085：记录候选 transport-gated 一次真实观察（RQ-215）

- 日期：2026-09-03
- 状态：accepted / completed-bounded-real / candidate-only
- 依据：ADR-0084；RQ-211、RQ-212、RQ-213、RQ-214

## 背景

RQ-214 的离线闸门已经在真实 OpenAI SDK、智谱候选适配器和观察器对象链上稳定制造
`pending-read`，但它使用的是本机 `MockTransport`。在没有这个条件时重复自然请求只得到
`not_pending`，不能回答取消时读取器是否会醒来。离线回执和同 SHA 公共 CI 完成后，用户
明确授权执行一次真实观察。

## 决策

在 exact-SHA 公共绿灯的候选观察提交上，只发出一次 `zhipu/glm-5.3-flash` 请求，并把
同一 `GateTransport` 包在官方 TLS `HTTPTransport` 外。阶段固定为
`before_first_event`；SDK 与 HTTPX retries 均为 0，父进程硬截止为 30 秒，不执行
recovery、不发送第二请求。当前环境的 HTTPS/ALL proxy 只用于连接，绝不写入输出或回执。

观察器和回执只保存状态、事件类别、时间、gate/close 布尔值和安全错误码，不保存请求体、
响应体、正文、reasoning、headers、Key、Authorization、request ID 或 SDK response。

## 证据

实现、观察器和输入计划身份均为
`2acdf795881733e70c9246c48f7147d5136821b5`；该提交的 Actions run `33721483490`
三 job exact-SHA 全绿（pytest `2296 passed, 145 skipped, 2 warnings, 127 subtests
passed`；PostgreSQL `201 passed, 2 warnings`；packaging-smoke 通过）。真实回执为

`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`

文件大小 `1305` bytes，SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`。
它记录 `provider_call_count=1`、`transport_request_count=1`、`network_used=true`、
`gate_entered=true`、`pending_reader_observed=true`、`reader_woke=true`，读取器在
`31ms` 内被唤醒；`upstream_event_seen=true`、`upstream_stream_close_seen=true`。
取消状态为 `raised`、安全错误码为 `zhipu_stream_close`，关闭投影为
`iterator=failed`、`sdk_stream=closed`、`composite=failed`，结论为
`client_wakeup_close_race`。回执 canonical round-trip 通过。

## 解释与限制

这一次证明的是：真实供应商流已经启动后，在本机受控的首帧前响应停顿中，response close
可以沿当前客户端对象链唤醒 pending reader；同时暴露了客户端适配器的关闭竞态。它不证明
智谱服务端原生 close/wakeup、服务端停止生成、底层 HTTP response 的独立可取消性、模型
一般能力或生产 streaming 成熟度。`reader_woke=true` 与 `composite=failed` 必须分开
理解，不能把前者提升为 clean close。

## 边界

RQ-215 不注册候选、不打开 `capabilities.streaming`，不改变默认模型、产品 Runtime、
AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由或
`production_media=0`，也不构成 G53-7、黄金切片、生产部署或 8F 证据。旧 RQ-211～214
回执保持不可变。

## 后续闸门

当前检查点进入“真实观察已完成、等待下一决策”。若要修复关闭顺序、拆分 provider response
取消，或进行新的真实请求，必须另立实现/证据版本并取得明确授权；不得把本次结果自动提升为
唯一模型或产品准入。
