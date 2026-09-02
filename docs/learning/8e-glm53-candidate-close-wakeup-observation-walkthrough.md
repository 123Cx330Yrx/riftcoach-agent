# RQ-211：候选 provider close/wakeup 观察 walkthrough

## 这次真正回答了什么

RQ-210 已经能把候选会话的迭代器、外层 SDK stream wrapper 和组合状态分开记录。RQ-211
进一步在一个有 exact-SHA 公共证据的干净快照上做了一次真实观察，但重点不是“再试一次模型”，
而是确认当前探针是否真的进入了可以测试取消唤醒的挂起读取状态。

## 观察合同

这次只允许一个普通智谱 `zhipu/glm-5.3-flash` 请求，SDK retries 为 0，父进程有 30 秒硬边界，
不允许 retry、recovery 或第二个请求。回执只保存状态、类别、耗时和安全错误码，不保存 Key、
Authorization、request ID、正文、reasoning 原文或 provider body。

```text
父进程（30 秒硬边界）
  └─ 子进程：打开一次候选 session
       ├─ 首段读取
       ├─ 只有形成 pending reader 才进入 cancel/wakeup 观察
       └─ 退出、回收、写入不可变 body-free 回执
```

## 这次看到了什么

回执绑定的 implementation、diagnostic 和 input-plan SHA 都是
`c31127b3c780fe4c493966d8b60f942d3b773fd4`，对应 Actions run `33661910096`。
单次调用成功打开会话，首段读取耗时 `78ms`，只记录 `reasoning_seen` 与 `content_seen` 类别；
状态是 `not_pending`，`pending_reader_observed=false`，所以没有执行 cancel，
`reader_woke=false`。子进程正常退出，迭代器、SDK stream wrapper 和组合关闭投影均为 `closed`，
且两类资源不是同一对象。

不可变回执位于
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq211_v1.json`，
大小 `908` bytes，SHA-256 为
`9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`。

## 不应得出的结论

`not_pending` 不是“取消成功”，也不是“取消失败”。它表示这一次有限窗口没有形成第二次挂起
读取，因而没有可供 cancel 唤醒的 reader。资源投影为 `closed` 也只说明候选 session 自己拥有的
对象完成了关闭报告；它不能证明底层 HTTP response 可取消、SDK close 非阻塞，或 close 能唤醒
另一次真实的 pending `next()`。

后续测试加固提交 `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c` 的公共 run 被外部取消，不能把它
写成公共通过；这不改变本次回执绑定的 c311 证据。

## 当前边界与下一步

候选仍 `activation_state=disabled`、未注册，`execution_allowed=false`、
`capabilities.streaming=False`；严格 Flash v1 仍为 2048/零额外调用，产品 Runtime、AgentLoop、
Portal、Account、Workbench、Auth、路由与 `production_media=0` 均不变。

当前 checkpoint 是
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`。
如果还要回答 provider-level wakeup，下一步应先由用户决定是否设计一个能稳定制造 pending-read 的
新版本协议，而不是自动重复同一真实请求。

## 面试时的准确说法

> 我用一个有父进程硬边界、单次调用、body-free 回执的候选探针验证了“是否真的进入挂起读取”。
> 这次结果是 `not_pending`，所以没有把 `reader_woke=false` 误说成供应商取消失败；它只说明
> 观察条件没有成立，provider-level close/wakeup 仍然是未证实的独立闸门。
