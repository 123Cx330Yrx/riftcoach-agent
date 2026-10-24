# 8E 学习材料：候选 SDK/HTTP transport gate 预检（RQ-214）

## 1. 要解决的误判

真实请求的 `not_pending` 只说明观察窗口内没有挂起读取；它不能回答“取消是否能
唤醒正在等待的 `next()`”。因此需要把读取停顿放在客户端 transport 层，而不是
继续猜供应商会不会自然变慢。

## 2. 三层对象链

预检保留三层真实本地对象：OpenAI SDK 的 `Stream`、智谱候选
`ZhipuStreamSession` 和已有 close/wakeup 观察器。只有最底层 transport 被替换成
内存 `MockTransport`，所以可以检查 SDK response.close() 是否沿对象链传到字节流，
同时保证没有网络和密钥。

## 3. 闸门阶段

- `after_first_event`：首个完整 SSE 帧先交给适配器，第二次 `next()` 在后续字节
  处挂起；这是未来真实观察的主阶段。
- `before_first_event`：首帧已被闸门读入但尚未交给 SDK，作为首读取消基准。

闸门只寻找帧分隔符，不解析正文；它的生命周期布尔值与观察器的事件类别分开保存。

## 4. 本地结果如何读

两阶段都能稳定进入 pending，并在下游 close 后唤醒读取器。当前适配器的并发关闭
投影可能是 `iterator_state=failed`、`sdk_stream_state=closed`、
`composite_state=failed`，因此 case 结论写成 `client_wakeup_close_race`；这同时
说明“reader 已醒”和“清理无竞态”不是同一个字段。该结果是本地客户端合同事实，
不是智谱服务端结论。

## 5. 证据与隐私

离线回执使用独立协议和 `offline_sdk_transport_fixture` 来源，
`provider_call_count=0`、`network_used=false`；只持久化安全状态、事件类别、
关闭投影、fixture 描述 SHA 和三份源码/计划 SHA。SSE 正文、请求头、Key、request ID、
异常文本和 SDK response 均不进入回执。

## 6. 验证方法

用 `tests/test_candidate_transport_gate.py` 检查 SDK 对象链、两阶段、回执往返和
不可覆盖写入；脚本 `scripts/replay_glm53_flash_candidate_transport_gate.py` 只写
offline 目录。公共 CI 只能证明离线预检可复现，不能替代真实 provider 或生产验收。

## 7. 后续边界

若用户授权下一门，可把同一 gate 包装在官方 TLS `HTTPTransport` 外执行一次真实请求。
该证据的措辞必须限定为“真实流启动后、本机受控响应停顿下的客户端 close/wakeup”；
不能写成供应商原生取消、服务端停止生成或生产 streaming 已可用。候选仍 disabled，
产品 Runtime、AgentLoop、Workbench、Portal、Account、Auth、路由和 `production_media=0`
保持不变。

## 8. 面试式表述

“我没有用极小超时伪造 pending，而是在真实 SDK 对象链的字节边界注入可控闸门；
这样既能验证客户端取消传播，又能把 reader wake 与 iterator close race 分开记录，
并明确不把本地 transport 事实冒充供应商能力。”
