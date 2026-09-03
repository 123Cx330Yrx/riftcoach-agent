# 8E 学习材料：候选 transport-gated 一次真实观察（RQ-215）

## 1. 为什么要做这一批

RQ-211 和 RQ-213 的自然真实请求都没有形成 pending-read。RQ-214 用离线
`MockTransport` 证明了可控闸门能制造这个状态；因此本批只把同一个闸门包到真实 TLS
transport 外，避免再用提示词或长超时猜供应商调度。

## 2. 一次请求的安全轮廓

观察在 exact-SHA 公共绿灯提交上执行，模型是 `zhipu/glm-5.3-flash`，阶段是
`before_first_event`。SDK/HTTPX retries 都是 0，父进程 30 秒截止，且没有 recovery 或
第二请求。proxy 只作为连接配置存在，Key、headers、请求/响应正文和 request ID 不进入
输出或回执。

## 3. 实际读数

回执记录一次网络请求和一次 transport 请求。真实流已经启动，gate 进入，读取器形成
pending 后在 `31ms` 内醒来；上游事件和 stream close 均被观察到。取消抛出安全码
`zhipu_stream_close`，iterator 与 composite 投影为 `failed`，外层 SDK stream 为
`closed`，所以总结果是 `client_wakeup_close_race`。

## 4. 如何解释

`reader_woke=true` 只回答“本机这条客户端对象链上的 pending reader 醒了”。它和
`composite=failed` 可以同时成立，说明唤醒与清理质量是两个独立维度。该回执不能证明
智谱服务端会主动停止生成、provider close 非阻塞、底层 HTTP response 可单独取消，或
GLM-5.3 已达到产品/生产准入。

## 5. 证据位置

真实回执：
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`
（`1305` bytes，SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`）。
实现/观察器/输入计划身份均为
`2acdf795881733e70c9246c48f7147d5136821b5`；同 SHA Actions run `33721483490` 全绿。

## 6. 当前边界

RQ-215 属于 8E 的 8-Advanced candidate-only 证据，不新增 8-Core capability。候选仍
disabled/未注册，`capabilities.streaming=False`；默认模型、产品 Runtime、AgentLoop、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变，8F、G53-7、黄金
切片和生产准入仍未开始。

## 7. 面试式表述

“我只花一次真实调用，把已在真实 SDK 对象链上验证过的 transport 闸门包到官方 TLS 外；
结果明确显示 reader 唤醒和 iterator close race 同时存在，所以没有把客户端观察冒充成
供应商能力，也没有顺手改生产链路。”
