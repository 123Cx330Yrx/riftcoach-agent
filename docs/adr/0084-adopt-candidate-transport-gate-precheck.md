# ADR-0084：采用候选 transport gate 预检（RQ-214）

- 日期：2026-09-03
- 状态：accepted / offline precheck only
- 依据：ADR-0082、ADR-0083；RQ-211、RQ-212、RQ-213

## 背景

RQ-211 与 RQ-213 的真实 `glm-5.3-flash` 请求都在第二次读取前完成，结果为
`not_pending`。RQ-212 已证明观察器的五种状态可以用内存闸门稳定回放，但那条
回放没有经过 OpenAI SDK 或智谱适配器的真实对象链。继续重复自然请求既不能稳定
制造挂起读取，也会无谓消耗真实调用额度。

## 备选方案

1. 通过提示词、思考档位或大输出额度诱导自然长尾。供应商调度不可控，且此前
   已出现长时间窗口；不作为主协议。
2. 仅在适配器外包一层 fake session。成本最低，但无法检查 SDK `Stream`、HTTP
   response 和适配器之间的关闭传播。
3. 在真实 SDK 对象链上注入本机 transport gate：先透传一个完整 SSE 帧，再
   在后续读取处暂停；另外保留“首帧前暂停”作为基准。该方案只在离线预检中使用
   `httpx.MockTransport`，未来若获授权可把同一 gate 换成官方 TLS transport。

## 决策

采用方案 3，并把它拆成两层证据：

- RQ-214 离线层使用真实 OpenAI SDK、`ZhipuProvider` 和候选
  `ZhipuStreamAdapter`，但底层是内存 `MockTransport`，不读密钥、不联网；
- 闸门只按 SSE 帧边界工作，不解析或持久化正文；回执只记录事件类别、读取/取消
  状态、资源关闭投影和 gate 生命周期；
- `reader_woke`、`cancel_status`、`close_report`、`downstream_close_seen` 和
  `upstream_stream_close_seen` 必须分列，不能以一个 `closed` 字段代替唤醒结论；
- 使用独立协议 ID/schema 和 `offline_sdk_transport_fixture` 来源，供应商调用数
  固定为 0，结果只写到 `data/evaluation/results/offline/`。

离线预检暴露出一个可重复的客户端事实：取消关闭响应能够唤醒挂起读取，但当前
适配器在并发关闭生成器时可能把迭代器投影记为 `failed`。这被记录为
`client_wakeup_close_race`，不在本 ADR 中静默修复，也不把它解释成智谱服务端行为。

## 边界

本 ADR 不注册候选、不打开 `capabilities.streaming`，不改变默认模型、产品 Runtime、
AgentLoop、Portal、Account、Workbench、Auth、路由或 `production_media=0`，也不形成
G53-7、黄金切片、生产部署或 8F 证据。离线结果不能证明供应商原生 close 非阻塞、
服务端停止生成或真实网络 response 已取消。

## 后续闸门

离线预检闭环后，如用户明确授权，才可执行一次真实
`zhipu/glm-5.3-flash` 请求，并将 `httpx.MockTransport` 替换为官方
`HTTPTransport` 的诊断包装层。该真实证据只能表述为“真实流启动后、在本机受控响应
停顿下的客户端 close/wakeup”，provider-native 行为仍保持未证实；不重试、不 recovery、
不追加第二请求。
