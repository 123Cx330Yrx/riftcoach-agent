# 8E 学习材料：候选读取器拥有的关闭顺序（RQ-216）

## 1. 问题与原则

一个同步 SDK 流通常有两个对象：外层 stream/response 和内部迭代器。读取线程可能正卡在
迭代器的 `next()`；如果取消线程直接对仍在执行的 Python 生成器调用 `close()`，会得到
跨线程生成器竞态。取消的关键原则是先操作能唤醒 I/O 的外层资源，再让拥有读取栈的线程
在 `finally` 中完成内部资源释放。

## 2. 代码地图

- `app/providers/zhipu_stream_adapter.py`：`ZhipuStreamSession` 记录活跃读取、延迟
  iterator close，并合并 body-free `ZhipuStreamCloseReport`；
- `tests/test_zhipu_stream_adapter.py`：阻塞读取直到拥有者栈退出的回归；
- `app/evaluation/candidate_transport_gate.py`：离线 SDK/transport 闸门；
- `tests/test_candidate_transport_gate.py`：两个闸门阶段的 clean-close 断言。

## 3. 数据与控制流

```text
打开一次候选会话
  -> reader 计数 +1
  -> reader 执行 SDK next()
  -> cancel 关闭外层 response
  -> response 唤醒 reader
  -> reader finally 计数 -1并关闭 iterator
  -> 派生 iterator/sdk/composite 报告
```

若 reader 没有被唤醒，iterator 仍是 `not_observed`，不会凭空生成 `closed`；进程级硬
边界负责最终收口。这样把“读取器醒来”和“资源清理完成”保持为两个可核验事实。

## 4. 验证结果

离线 `before_first_event` 与 `after_first_event` 两场景均只使用一个内存 transport 请求，
现在得到 `cancel_status=returned`、`reader_woke=true`、三层 close=`closed`。新增阻塞
fixture 还验证了：取消瞬间 iterator 不会被跨线程调用，释放后恰好关闭一次。候选聚焦
测试共 `61 passed`，编译、差异格式和治理检查通过；本批没有网络调用。

## 5. 边界与安全

报告只保留状态和安全错误码，不保存正文、reasoning、headers、Key、Authorization 或
request ID。历史 RQ-215 回执不回写；本修复也不意味着智谱服务端支持原生取消，外层
response close 若阻塞仍必须 fail closed。候选仍 disabled/未注册，生产 streaming 和
默认模型均不变。

## 6. 运行手册

先跑 `tests/test_zhipu_stream_adapter.py` 与 `tests/test_candidate_transport_gate.py`，
再跑候选观察器相关回归、compileall、`git diff --check` 和 governance。公共 CI 必须绑定
提交 SHA；新的真实观察若要做，必须另行明确授权并最多执行既定的一次请求。

## 7. 面试式表述

“我把取消拆成唤醒和清理两个阶段：取消线程只关闭外层 response，读取线程在自己的
`finally` 中关闭迭代器，因此不再跨线程关闭正在执行的生成器；未完成的清理仍保持
`not_observed`，不会被误报成成功。”
