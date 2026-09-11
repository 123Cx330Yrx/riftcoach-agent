# RQ-216：候选读取器拥有的关闭顺序修复计划与结果

## 目标

修复 RQ-214/RQ-215 暴露的候选并发关闭竞态：当一个线程阻塞在 SDK 迭代器的
`next()` 时，取消线程不能跨线程调用正在执行的 Python 生成器 `close()`；应先关闭
外层 response 唤醒读取，再由读取线程完成迭代器收尾。

## 固定边界

- 只改候选 `ZhipuStreamSession` 和对应离线测试；
- 不改变 RQ-215 真实回执、协议/schema、请求预算或历史 SHA；
- 不发真实请求、不读取 Key、不做 retry/recovery；
- 不注册 `glm-5.3-flash`，不打开 `capabilities.streaming`；
- 不修改产品 Runtime、AgentLoop、Workbench、Portal、Account、Auth、路由或媒体状态。

## 控制流

```text
reader: begin_read -> SDK next() ---------------------> end_read/finally
                                                  \       |
cancel: close outer response -> wake reader --------> deferred iterator close
```

会话记录活跃读取数量。关闭时如果仍有读取，外层 SDK stream 是立即可用的唤醒句柄，
迭代器只登记为 deferred；`end_read()` 看到最后一个读取退出后，才在拥有者线程调用
迭代器关闭。报告在这之前保持 `not_observed`，避免把未完成收尾写成成功。

## 实施结果

- `app/providers/zhipu_stream_adapter.py` 增加读取计数、延迟迭代器收尾和线程安全的
  分资源报告合并；无并发读取仍沿用原逐资源关闭路径；
- `tests/test_zhipu_stream_adapter.py` 增加阻塞读取/延迟收尾回归；
- `tests/test_candidate_transport_gate.py` 将两个 SDK transport gate 场景收紧为 clean close，
  直接防止旧竞态回归。

## 验收

- 候选/观察器/transport gate 聚焦：`61 passed`；
- `python -m compileall -q app scripts tests`：通过；
- `git diff --check`：通过；
- `python scripts/check_project_governance.py`：通过；
- 实现提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions `33726209532` 三 job
  exact-SHA 全绿；公共 pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，
  PostgreSQL 与 packaging-smoke 通过；
- 离线 transport gate 两阶段：一次请求预算保持不变、reader 唤醒、三层关闭均为
  `closed`；
- 本批真实 API 调用：0。

## 未完成事项

公共 CI 已通过；现在只回到“是否重新做一次受控真实观察”的决策点，不自动重发请求。
即使未来真实观察 clean，也不能代替 G53-7、黄金切片、生产
安全/部署/合规或 8F。
