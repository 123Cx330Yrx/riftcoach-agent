# ADR-0088：记录最新 Flash 协议通过与候选 8192 超时边界

## 状态

已接受为 8E/8-Advanced 的 evaluation-only 证据记录（2026-09-03）。这不是
候选注册、产品默认切换或 8-Core 准入决定。

## 背景

RQ-217 已把候选适配器的本机 reader 唤醒和资源收尾收敛为 clean，但它没有回答
模型响应能否在完整 Agent/工具链中结束。为避免把旧的 2048 上限失败和新的候选
8192 流混为一谈，本批先在最新实现上重取 G53-3，再做一次 8192、90 秒、单请求的
候选真实流观察。

## 决定

1. 在实现 `aa22cea0daeb443b635706144ccbfa66185670c4` 上，普通 API
   `zhipu/glm-5.3-flash` 的 G53-3 严格执行 3 次调用；A1 结构化合同和 A2 Agent
   工具往返均通过。脱敏回执作为实现证据提交 `4b6cd5807f40f6a8dd469f21c688be861261d20c`
   的唯一新增文件保存，回执 SHA-256 为
   `feeb7fd7eec2643ca692bd6182fd94a04abed354b17b892029402c0217641e99`。
2. 在公共 CI 已通过的 `4b6cd5807f40f6a8dd469f21c688be861261d20c` 上，候选
   `glm-5.3-flash-runtime-v2-candidate/2.0.0` 只执行 1 次 primary，输出上限
   8192、Agent 90 秒、传输 120 秒、SDK/HTTPX retries=0。回执在 90 秒硬墙钟处以
   `fail_closed / elapsed_limit` 结束，未发送 recovery、retry 或第二请求；回执 SHA-256
   为 `21350d7883b4d2eea30e0467a7b8c23eed3a3ad5a9deeb309c44f8ded5cf3f84`。
3. 两份回执都只保存 allow-list 状态、预算、调用数和安全错误码，不保存 Key、headers、
   request ID、Prompt、正文、reasoning、工具参数或供应商异常文本。旧回执不可回写。

## 影响与边界

- 这证明“普通 API/基础工具协议可达”，但不证明最大思考档的完整响应、成本/延迟稳定性、
  provider-native streaming、G53-7、黄金切片或生产准入。
- 候选仍 `activation_gate=disabled`、未注册，`capabilities.streaming=False`；严格产品
  Flash v1 仍为 2048/零额外调用。默认模型、AgentLoop、统一 Trace/预算、Portal、Account、
  Workbench、Auth、路由和 `production_media=0` 均不变。
- 下一批先做离线的思考档位、流终态和恢复策略拆分，明确哪些观察可归因于生成预算、哪些
  属于 transport/SDK 边界；完成后再决定是否建立新的候选域门。不得用重复真实请求替代设计。
