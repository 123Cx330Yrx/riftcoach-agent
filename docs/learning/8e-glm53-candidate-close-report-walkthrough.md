# RQ-210：候选会话关闭报告 walkthrough

## 这次解决什么问题

RQ-209 只有一个组合 `close_state`。当它为 `failed` 时，不能知道是迭代器没有关闭、外层 SDK
stream wrapper 没有关闭，还是根本没有可观察的 hook。本门把“未知”拆成可读的内存状态，
但不把它写成底层网络事实。

## 软件原理

资源所有权要和资源结果同时建模：同一对象只释放一次，不同对象分别尝试；普通异常进入
安全状态，控制异常不能被吞掉；缺少 hook 就是 `not_observed`，不是成功。组合状态是便于
上层 fail-closed 的投影，不能反向推导具体资源原因。

## 代码地图与控制流

- `app/providers/zhipu_stream_adapter.py`：`ZhipuStreamSession` 保存资源并生成
  `ZhipuStreamCloseReport`；`close_report` 只读且不序列化。
- `tests/test_zhipu_stream_adapter.py`：shared/distinct、失败、控制异常、无 hook 和
  context-manager 回退夹具。
- `app/evaluation/candidate_recovery_diagnostic_v2.py`：继续只消费旧的组合投影；RQ-209
  receipt 不变。

```text
session.close()
  ├─ snapshot owned iterator / SDK wrapper
  ├─ deduplicate identical object
  ├─ attempt each close/exit hook once
  ├─ record per-role state + shared_resource
  └─ expose body-free report; legacy close_failed remains compatible
```

## 如何验证

本地 adapter/deadline/v2/real 聚焦共 `73 passed`，扩展相邻集合共 `182 passed, 27 subtests passed`；
compileall、`git diff --check` 和治理检查通过。实现提交与 Actions run 的 exact-SHA 关系必须再由
公共 CI 证明，不能把本地数字当生产成熟度。

## 失败、安全与边界

报告不含正文、reasoning、工具参数、异常原文、headers、Key、完整 request ID 或 HTTP response
句柄。`cancel()` 仍同步调用 SDK close；没有 `cancel_state`/`wakeup_observed`，因此不能说 close
非阻塞、唤醒 pending `next()` 或物理连接已关闭。并发读取应等待拥有者的 close 返回。
旧 supervisor/回执为兼容旧合同，可能把“没有 hook 但也没有失败”聚合成 `closed`；新报告的
`not_observed` 才表示本层没有观察到具体资源的释放，不应把两个投影混为一谈。

## 面试时的准确说法

> 我没有把一个组合关闭错误猜成 HTTP 层失败，而是在候选会话内部增加了 body-free 的分资源
> 关闭报告。它区分迭代器和外层 SDK 包装器、去重共享对象并保留旧回执兼容；这仍不是 provider
> 的取消/唤醒证明，也没有接入产品 Runtime。
