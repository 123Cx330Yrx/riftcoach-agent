# 8E 学习材料：关闭顺序修复后的 transport-gated 真实观察（RQ-217）

## 1. 先看问题是什么

RQ-215 已经说明“读取器能醒来”，但取消线程同时跨线程关闭 Python iterator，导致
`client_wakeup_close_race`。RQ-216 把责任顺序改成：取消线程先关外层 SDK response，
读取线程退出自己的 `next()` 栈后，在 `finally` 里关 iterator。RQ-217 的目的不是再测
模型好不好，而是用一次真实流启动来复核这条客户端生命周期是否收敛。

## 2. 为什么只允许一次请求

自然请求无法稳定制造 pending-read；transport gate 可以在首个完整 SSE 帧边界暂停，
让观察器确定自己正在测“挂起读取被 close 唤醒”，而不是猜供应商调度。为避免把实验
变成无界重试，本批固定一个模型、一个阶段、一次 provider 请求、一次 transport 请求、
零 retry、零 recovery，并用 30 秒父进程边界兜底。

## 3. 读数与控制流

本次回执绑定实现/观察器/输入计划 SHA
`3e028b1217f1274152ba161993287f29188a1b73`。真实流进入 gate 后形成 pending reader；
close 返回，reader 被唤醒，随后 reader 自己完成 iterator 收尾：

```text
真实 TLS stream → 首帧前 gate 保持 → response close
                                  ↓
                 reader wake → reader finally → 三层 close=closed
```

安全投影为 `pending_cancel_returned`、`reader_woke=true`、
`cancel_status=returned`、三层 close report `closed`，结论码为
`client_wakeup_clean`。`gate_released=false` 是协议设计的成功条件，不是漏关资源。

## 4. 证据如何保存

回执路径是
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`，
大小 `1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`。
它只保存请求计数、网络/gate 生命周期、读取/取消状态、事件类别、时长和安全错误码；
不保存 Key、headers、request ID、请求或响应正文、reasoning、工具参数或 SDK 异常文本。
canonical round-trip 已通过。

## 5. 这能说明什么，不能说明什么

能说明的是：在真实 provider 流已启动但被本机 gate 受控停住的情况下，候选客户端
reader 唤醒和本层资源收尾按 RQ-216 顺序完成。不能说明智谱服务端原生取消、底层
HTTP response 独立可取消、任意长尾网络下的 close 时延、模型一般能力、成本、生产
streaming 或公共成熟度。候选仍未注册，`capabilities.streaming=False`；默认模型、
产品 Runtime、AgentLoop、Portal、Account、Workbench、Auth、路由和 `production_media=0`
均未改变。

## 6. 面试式表述

“我在同 SHA 公共绿灯的候选隔离接缝上只做了一次真实 transport-gated 观察。它形成了
pending reader，close 返回并唤醒 reader，reader-owned 顺序让 iterator、SDK stream 和
composite 都干净关闭，所以客户端结论是 `client_wakeup_clean`；我没有把这条本机受控
证据冒充成 provider-native 能力，也没有接入产品默认链路。”
