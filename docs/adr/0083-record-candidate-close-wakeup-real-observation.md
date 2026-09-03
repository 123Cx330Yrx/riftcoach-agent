# ADR-0083：记录候选 close/wakeup 真实观察（RQ-213）

- 日期：2026-09-03
- 状态：accepted / bounded candidate evidence
- 依据：ADR-0081、ADR-0082；RQ-211、RQ-212

## 背景

RQ-211 在一次真实 `glm-5.3-flash` 请求中得到 `not_pending`：流很快产生了
reasoning/content 事件，没有形成可取消的挂起 `next()`。RQ-212 已用离线 fake
Event 闸门覆盖了五种生命周期，但离线回放不能替代供应商行为。用户允许继续推进，
因此需要把一次新的真实观察保存为独立、不可变、无正文的证据，而不是重复解释旧回执。

## 决策

1. 在 RQ-212 完成的隔离候选接缝上，只执行一条普通智谱
   `zhipu/glm-5.3-flash` 请求。
2. 使用 `max_retries=0`、父进程 30 秒边界，不发送 retry、recovery 或第二条请求。
3. 真实回执继续只保留允许列表字段：调用次数、事件类别、读取状态、取消状态、
   关闭投影和时间数字；不保存 Key、Authorization、request ID、正文、reasoning
   原文或原始 provider body。
4. 回执使用新的 RQ-213 文件名，不覆盖 RQ-211，也不把同一次请求改写成 RQ-212
   的 `offline_fake` 证据。

## 证据

真实观察从 exact-SHA 公共绿灯的 `a396412f7cd0f2e923536cf55f715dd56251aae5`
隔离快照启动；该提交的 Actions run `33708492921` 三个 job 均成功。回执为：

`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`

- schema `1.0.0`，909 bytes；SHA-256=
  `8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`；
- `call_count=1`、`session_opened=true`、`initial_read_elapsed_ms=172`；
- 事件类别为 `reasoning_seen`、`content_seen`；
- `observation_state=not_pending`、`pending_reader_observed=false`，所以
  `cancel_status=not_attempted`、`reader_woke=false`；
- 子进程正常退出，未被强制终止；iterator、SDK stream wrapper 和 composite
  close 投影均为 `closed`，`shared_resource=false`。

## 边界与后续

`not_pending` 只说明这次有限窗口没有形成可测的挂起读取；它既不能证明也不能
否定供应商 close 的非阻塞性、取消能否唤醒 pending `next()`，或底层 HTTP response
是否被取消。候选仍 `activation_state=disabled`、未注册，
`execution_allowed=false`、`capabilities.streaming=False`；默认模型、产品 Runtime、
AgentLoop、Portal、Account、Workbench、Auth、路由与 `production_media=0` 均不变。
G53-7、黄金切片、生产准入和 8F 不因本回执完成。下一精确 checkpoint 改为
`candidate-close-wakeup-follow-up-decision / pending-user-decision`；若继续，
应先决定是否设计能稳定制造 pending-read 的新版观察协议，而不是无界重复请求。
