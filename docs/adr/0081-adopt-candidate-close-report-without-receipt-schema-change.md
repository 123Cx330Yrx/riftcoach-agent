# ADR-0081：候选会话分资源关闭报告（不升级回执 schema）

- 日期：2026-09-03
- 状态：`accepted / candidate-only / implementation-complete-public / receipt-schema-unchanged`
- 范围：Stage 8 / 8E；RQ-210
- 依据：RQ-209、ADR-0080、`app/providers/zhipu_stream_adapter.py`

## 背景

RQ-209 的 body-free 回执只有组合 `close_state=failed`。它能说明候选观察未形成可交付完成，
却不能区分会话自己的迭代器和外层 SDK stream wrapper 哪一层提供了关闭钩子。把这种未知
直接写成“HTTP response 关闭失败”会超过现有证据，也会迫使旧回执升级并重写已冻结的 SHA。

## 决策

`ZhipuStreamSession` 增加仅内存、不可变的 `ZhipuStreamCloseReport`，允许诊断调用方在拥有者的
`close()` 返回后读取以下 allow-list 字段：

- `iterator_state`：迭代器的 `not_observed / closed / failed`；
- `sdk_stream_state`：外层 SDK stream wrapper 的同一组状态，不等同于底层 HTTP response；
- `composite_state`：两类资源的保守组合结果；
- `shared_resource`：两个角色是否是同一对象。

关闭过程对每个拥有的对象最多尝试一次；普通异常映射为安全状态，控制类异常在尝试其他资源后
继续抛出。旧 `close_failed`、supervisor 行为和 RQ-209 v2 receipt/schema 2.0.0 保持兼容，
报告不写入持久回执，不携带正文、异常文本、headers、Key、request ID 或 HTTP response 句柄。
因此，旧 supervisor/回执仍可能把“无 hook 但无失败”投影成兼容性的组合 `closed`；这不等于
新报告已经观察到每个资源关闭，读取者应优先看 `close_report` 的 `not_observed` 状态。

## 未决边界与替代方案

`cancel()` 仍同步经过 SDK `close()`。本 ADR 不证明 close 非阻塞、不证明它能唤醒挂起的
`next()`，也不提供 raw-response cancel hook；没有 hook 时使用 `not_observed`，不假报成功。
并发调用者应在拥有者的 close 完成后读取报告，旧的先标记 closed 再清理时序不在本门扩大修复。

若未来需要跨进程审计分资源状态，必须另立 ADR，升级 receipt/schema、allow-list、canonical SHA
和 exact-SHA CI；若要执行 provider-level close/wakeup 真实观察，也必须取得新的明确授权。
因此本项不注册候选、不打开 `capabilities.streaming`，不接入产品 Runtime、AgentLoop、Workbench
或前端，不改变默认模型和 `production_media=0`。
