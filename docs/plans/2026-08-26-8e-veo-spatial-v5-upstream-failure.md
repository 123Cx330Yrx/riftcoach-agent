# 8E Veo spatial-orchestration v5 上游失败审计

## 执行事实

- 付费前门提交 `d57b026c45993a41437a7fc4dd35cb2680445048` 已由 Actions run `32951125621` 的
  `pytest`、`postgres-migrations` 与 `packaging-smoke` 三 job exact-SHA 全绿；
- 提交前 Dragon 权威余额 `$65.01`，task log 为原 4 项；v5 source/prompt/negative/runner/唯一路径门全绿；
- runner 只执行一次 POST，创建唯一 task `task_I5iJQDEiEOpZtsQCSOi3qELNTMFAk9Mw`；
- model `Veo3.1-quality-official`、same v2 first=last、8s/1080p/16:9、audio false、lossless/pad；
- source SHA `8134c0ca...1a06e`；positive SHA `99cce1b...e72a6`；negative SHA `310b281...b8ab`；
- task 159 秒后以 `Generation failed: task processing failed`、100% 进入 failed；没有 result URL 或 output；
- Dragon 先预扣 `$19.712`，随后以 `异步任务退款` 全额退还 `$19.712`；最终权威钱包余额 `$67.01`；
- external video calls 累计 `6`，production media 仍为 `0`。

## 本地终端操作事故

第一次尝试用 Windows PowerShell 弹窗时进程因版本/控制台问题退出且未 POST。第二次 Codex terminal 等待 Key 但
UI 没有把 session 正确显示给用户。第三次可见 pwsh 与用户输入发生竞态：父窗口被误判为不可见并关闭；用户已
输入后，子 runner 仍成功创建唯一 task，但随后退出，令本地 status 暂留在 50% polling。没有第二次 POST。

远端 task log 是终态事实源。本地 status 已按同一 task 更正为 `failed / remote_terminal / 100% /
task_processing_failed`。该操作事故影响本地轮询/下载体验，不影响远端 task 的唯一性或退款事实。后续任何安全
Key runner 必须先证明用户可见且不得在输入窗口存在时按进程窗口句柄猜测并关闭。

## RQ-128 故障树裁决

| 层 | 裁决 |
|---|---|
| local runner / prompt files | POST 已完成；digest、one-POST 与 task_id 证明请求身份；后续本地轮询被终端事故中止 |
| request/schema/parameters | relay 接受并创建 task；不足以证明所有上游字段语义都正确，但不是 403/billing failure |
| relay/upstream processing | task 在 159 秒、100% 后 generic failed；这是当前唯一可证实失败层 |
| output/model quality | unknown；没有 output，不能评价 v5 motion、Veo 质量或 first=last 效果 |
| method/architecture | open；单个无输出 task 不能否定生成式路线或 prompt 方法 |

## 停止线

1. 不重发同一 v5，不创建第二个 Veo task；
2. 不把 generic upstream failure 写成 prompt/模型质量失败，不因此立即切 Seedance/Grok；
3. 下一动作先持久化本审计并取得 exact-SHA 公共 CI；
4. 后续只有在获得 task-id 级平台诊断、证实 transient fault，或提出能区分 schema/transport 的新可证伪实验时，
   才能重新讨论一次调用；否则保持 poster-only/production media 0。
