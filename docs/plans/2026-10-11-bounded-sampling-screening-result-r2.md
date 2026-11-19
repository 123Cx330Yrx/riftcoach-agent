# 2026-10-11 有界温度筛查 r2 结果

## 结论

本批按授权启动了唯一 runner，但未完成五个样本对照。前两对样本完成真实 Provider 请求、主审和独立 native 双审：

- `sample-1:baseline`：temperature 1.0，score 74，`needs_revision`；预期为 accept，语义不接受。
- `sample-1:temperature-02`：temperature 0.2，score 78，`needs_revision`；预期为 accept，语义不接受。
- `sample-2:baseline`：final，score 96，`pass`，主审和独立审查均接受，四项 ReportAssessment 全真。
- `sample-2:temperature-02`：final，score 95，`pass`，主审和独立审查均接受，四项 ReportAssessment 全真。

第五次 Provider 请求（`sample-3:baseline`）在流式工具参数组装阶段失败，runner 按硬故障规则停止整批。该失败不是 429、401、503 或本地审查路由问题，也不能据此判断温度是语义根因。候选筛查未完成，不支持后续完整15授权或产品入口切换。

## 绑定与运行边界

- checkout：`D:/riftcoach-agent-rq192-pr`
- branch：`codex/rq192-provider-stream-contract-ci`
- HEAD：`465daf92bfaecb47e800ebc343bd23f21c553220`
- 同提交全绿 CI：`38141643942`
- plan/package SHA：`8c8fc50de3159dfc42bd02f2a3c53276dc5f537d9dfda2395de4f16f441b94d7`
- run：`data/runs/model_comparison/document-sampling-screening-20261011-r2`
- runner：wrapper/runner PID `112000`，UTC `2026-10-11T14:13:05.577949+00:00` 启动，`15:33:37.376864+00:00` 以 exit 1 停止；没有第二份 runner。
- 授权上限：最多 10 次 `glm-5.3`，967680 tokens、3000 active seconds、86400 host seconds；未缓存估价 14.29504 元，非硬计费封顶。

## 实际账目与最早偏离

`result.json` 的实际账目为：`attempted_calls=5`、`observed_http_requests=5`、`known_tokens=84081`、`unknown_usage_calls=0`、`http_send_unknown_calls=0`、`receiptless_calls=1`；活动时间 338.234 秒，Host 时间 4486.266 秒。四个已完成阶段均有真实 native final、checkpoint 和 submission；第五次没有业务 response/stage/receipt。

最早偏离是 `sample-3:baseline` 的 `ProviderResponseError`（phase `transport`）。原始证据位于：

- `sample-3-baseline/transport/stream-001/failure.json`：`assembly_rejected/tool_call_arguments`；
- `sample-3-baseline/transport/stream-001/rejected-tool-output.json`：终态 tool-call 参数未能组装为可发布 JSON；
- `sample-3-baseline/transport/stream-001/progress.json`：Provider 流已产生一次 HTTP 请求，但无可发布内容。

因此该调用计入实际预算，并作为 receiptless 硬停止处理；不重试、不重评、不补发、不重开。

## Native 审查与公开封存

四个真实独立终答事件如下，均绑定各自 checkpoint：

- `sample-1:baseline`：`01a12aba-90b1-79d1-a1ea-3764fbb1ab39/01a12b5a-44a9-78d1-a558-f2ffd1b8e84c/msg_0eb2d8b75f559915016acb9eea89ec87d2b3730a263c6c5989`
- `sample-1:temperature-02`：`01a12aba-90b1-79d1-a1ea-3764fbb1ab39/01a12b69-3fff-7261-889b-bb0e995fe80d/msg_0eb2d8b75f559915016acba1047a0487d29c22a4f1c6a9acfc`
- `sample-2:baseline`：`01a12aba-90b1-79d1-a1ea-3764fbb1ab39/01a12b73-bf52-7d21-b3a2-ef79bbab6e2e/msg_0d178bf21623aee1016acba7d882948191a09c3985c3e5d08d`
- `sample-2:temperature-02`：`01a12aba-90b1-79d1-a1ea-3764fbb1ab39/01a12b91-cc54-7e53-ac5f-9e2322882e5b/msg_0d178bf21623aee1016acbabc3a67481919787dc9eda948f6a`

严格只读 replay 已成功，核实 `native_reviews=4`、账目、阶段绑定和未执行边界；create-only seal 已生成：

- seal：`C:/Users/33502/Documents/Agent/outputs/riftcoach-bounded-sampling-screening-20261011-r2/sealed`
- seal SHA：`bc2a89ad08b6c3390dfb2ed9e09df5b0d9ad0d17d362e7033dce02d848d666de`
- close audit：`C:/Users/33502/Documents/Agent/outputs/riftcoach-bounded-sampling-screening-20261011-r2/close-audit.json`，SHA `5823f23dc76c5cfde27eb9d740e8ed7416c41544c70c3325d28efb80cef99f7b`

原始请求、响应、失败流、审查 notes、native event、授权、启动和退出记录均保留；原件和冻结 checkout 未修改。

## 未执行与资格

未执行项为：`sample-3:temperature-02`、`sample-4:baseline`、`sample-4:temperature-02`、`sample-5:baseline`、`sample-5:temperature-02`。本批 `new_qualification=0`，不并入历史 2/15、3/15、remaining11 或完整15，也不改变默认产品入口。正式同版本15、自然消费、8E、Coach/Training、Worker/DB/API/UI/journal、前端、Memory、身份运维、两树整合和八维学习继续保持未完成。
