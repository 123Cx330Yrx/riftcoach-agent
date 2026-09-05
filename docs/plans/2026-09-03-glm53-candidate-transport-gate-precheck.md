# RQ-214：候选 SDK/HTTP transport gate 预检计划

## 目标

在不发真实请求的前提下，验证 OpenAI SDK → Zhipu 适配器 → 观察器的对象链能否在
确定的 SSE 帧边界形成 pending-read，并分别记录读取器唤醒和资源关闭结果。

## 固定输入与边界

- 模型身份固定为 `zhipu/glm-5.3-flash`，但底层只使用 `httpx.MockTransport`；
- 两个固定阶段：`after_first_event`、`before_first_event`；
- 每个阶段一个 SDK 请求，合计供应商调用数为 0，网络连接数为 0；
- 首读/次读窗口 0.5 秒，取消窗口 2 秒，读取器宽限 1 秒，闸门自动保底 5 秒；
- 不写 SSE 正文、request、header、Key、request ID 或 SDK response；
- 回执单独使用 `glm-5.3-flash-candidate-close-wakeup-transport-gate` / schema `1.0.0`。

## 实施步骤

1. 用固定的 reasoning、content、terminal+Usage、DONE 帧构造内存 SSE 流，并计算
   只描述帧类别的 fixture SHA-256。
2. 用 `GateTransport` 包装 `MockTransport`：透传首个完整帧，在指定阶段等待
   `release` 或下游 `close()`；close 传播只记录布尔生命周期事实。
3. 通过真实 OpenAI `Stream` 和候选 `ZhipuStreamSession` 运行既有观察器；不改产品
   Provider/Runtime。
4. 将结果投影为 body-free case，确保 `reader_woke` 与 `close_report` 独立；
   `client_wakeup_close_race` 只表示本地并发关闭投影，不冒充 provider 结论。
5. 运行聚焦测试、compileall、差异检查和治理检查；生成不可覆盖的离线回执。
6. 离线回执公共 CI 闭环后，下一 checkpoint 才是一次性授权的真实 transport-gated
   观察；若未授权，保持暂停。

## 验收条件

- 两个阶段均只产生一次本地 transport 请求，观察器均能进入 pending 并在 close
  后返回；
- `upstream_event_seen`、`gate_entered`、`downstream_close_seen`、
  `upstream_stream_close_seen` 与观察器状态一致；
- 回执可 canonical round-trip，拒绝正文/凭据字段和路径覆盖；
- 候选仍 disabled/未注册、`execution_allowed=false`、`capabilities.streaming=False`，
  产品链路和 `production_media=0` 无变化。
