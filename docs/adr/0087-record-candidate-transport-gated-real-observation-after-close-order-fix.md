# ADR-0087：记录候选关闭顺序修复后的 transport-gated 一次真实观察（RQ-217）

- 日期：2026-09-03
- 状态：accepted / completed-bounded-real / candidate-only
- 依据：ADR-0084、ADR-0085、ADR-0086；RQ-214、RQ-215、RQ-216

## 背景

RQ-215 在真实 TLS transport 外的受控首帧前闸门中观察到 reader 被唤醒，但旧候选
适配器把跨线程 iterator 关闭投影为 `client_wakeup_close_race`。RQ-216 已在候选隔离
接缝中改为“先关外层 response、由 reader 自己收尾 iterator”，并取得 exact-SHA 公共
CI。用户随后明确授权在该修复身份上只做一次新的真实观察。

## 决策

在实现、观察器和输入计划都固定为
`3e028b1217f1274152ba161993287f29188a1b73` 的提交上，执行一次且仅一次
`zhipu/glm-5.3-flash` 请求。阶段固定为 `before_first_event`；SDK 与 HTTPX retries
均为 0，父进程硬截止为 30 秒，不执行 retry、recovery 或第二请求。官方 TLS
`HTTPTransport` 仅被 evaluation-only gate 包装，候选仍不注册、不打开 streaming。

回执只保留允许列表中的状态、事件类别、布尔生命周期、时长和安全错误码；不保存
Key、Authorization、headers、request ID、请求/响应正文、reasoning、工具参数或 SDK
异常文本。`gate_released=false` 是本协议的预期条件：闸门保持住，直到 close 唤醒
读取器；它不表示资源泄漏。

## 证据

同一实现 SHA 的公共 Actions run `33727163550` 已完成，`pytest`、
`postgres-migrations` 与 `packaging-smoke` 三个 job 均 `completed/success`。
真实回执为

`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`

文件大小 `1284` bytes，SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`。
回执 canonical round-trip 通过，`gate_observation_valid=true`，且只发生
`provider_call_count=1`、`transport_request_count=1`、`network_used=true`。

观察投影为：`observation_state=pending_cancel_returned`、
`pending_reader_observed=true`、`reader_woke=true`、`cancel_status=returned`；
`upstream_event_seen=true`、`gate_entered=true`、`downstream_close_seen=true`、
`upstream_stream_close_seen=true`。三层候选资源关闭报告均为 `closed`，
`shared_resource=false`，最终结论为 `client_wakeup_clean`。

## 解释与限制

这次结果证明：在真实供应商流已经启动、但响应被本机 transport gate 受控停住时，
当前候选客户端的 pending reader 能被 close 唤醒，并能按 RQ-216 的 reader-owned
顺序完成本层 iterator/SDK/composite 收尾。它不证明智谱服务端原生 close/wakeup、
底层 HTTP response 的独立可取消性、任意网络长尾下的非阻塞 close、模型一般能力、
成本/延迟稳定性或生产 streaming 成熟度。它也不替代 G53-7、黄金切片、安全部署合规
或 8F 评估。

## 边界与后续

候选继续 `activation_state=disabled`、未注册、`execution_allowed=false`、
`capabilities.streaming=False`；严格 Flash v1 的 2048/零额外调用、默认模型、产品
Runtime、AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均不变。本 ADR 不授权新的真实请求、候选注册、全局唯一模型切换
或产品链路接线；下一步回到“候选真实观察已完成、等待独立准入/质量决策”的检查点。
