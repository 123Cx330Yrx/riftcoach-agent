# 2026-10-12 流式工具参数失败诊断

## 结论

有界温度筛查 r2 的 `sample-3:baseline` 失败不是本地增量拼接丢失，也不是 429、401、503、超时或已证额度问题。保存的 334 个 `argument_parts` 按原顺序拼接为 626 字节、以 `}` 正常结束；普通 JSON 解析会得到一个对象，但同名 `issues` 键出现两次。严格解析器 `object_pairs_hook=_unique_json_object` 在第二个 `issues` 键处拒绝，代码返回 `tool_call_arguments`，并把原始片段保存在不可发布的诊断证据中。

普通解析的结果会保留后一个空 `issues`，从而静默丢掉前一个真实 block 14 issue；放宽或改用普通解析会制造报告数据损失，因此不修 parser 放行。

## 可复现证据

- 原件：`data/runs/model_comparison/document-sampling-screening-20261011-r2/sample-3-baseline/transport/stream-001/rejected-tool-output.json`。
- 拼接 SHA256：`8d4121953bd6ea3d775ac0628f05bd4302e3e679e032f06f77711298361d88e0`；`issues` 键出现 2 次。
- 严格解析：`ValueError: duplicate JSON object key`；普通解析：`issues=[]`，block 14 被覆盖。
- 现有 `ProviderStreamAssembler._decode_tool_calls` 已使用重复键拒绝器，`rejected_tool_arguments()` 保留原片段但不发布；相关测试已覆盖重复键、截断 JSON、非有限数和过深 JSON。
- 终态流的 `finish_reason=tool_calls`、usage 和 close 均已记录；因此这不是 EOF 前半截拼接的假设。

## 决策

本地接收合同保持不变，不添加去重、后者覆盖、自动修复或重试。该失败应继续归类为 Provider 输出合同不合法的 receiptless 硬故障；原批不重开、不补发、不重评。没有新的 Provider 调用。

这次诊断也核正筛查控制：`sample-1` 的预设 `accept` 与主/独立全文审查均发现的真实 block 4 问题冲突，不能把该样本当作“温度能否恢复正确稿”的有效正例。r2 已有 4 个审查阶段和 1 个协议失败，候选效果仍不可判定；任何后续筛查需先重建样本控制与具体授权。

## 限制与后续

本证据确认了本地拒绝行为和 Provider 输出的重复键，但不能从一次响应推断 Provider 的更深层生成原因或温度因果。正式同版本 15、自然消费和 8E 仍未完成。后续若继续，先从 clean checkout、同提交 CI、修正后的正反控制和新 run 重新准备；不得使用 r2 剩余预算或修改旧原件。
