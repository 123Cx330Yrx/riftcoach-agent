# ADR-0086：采用候选读取器拥有的关闭顺序（RQ-216）

- 日期：2026-09-03
- 状态：accepted / completed-local / candidate-only
- 依据：ADR-0081、ADR-0084、ADR-0085；RQ-214、RQ-215

## 背景

RQ-214 的离线 transport gate 和 RQ-215 的一次真实 transport-gated 观察都证明，
外层 SDK response close 可以沿当前客户端对象链唤醒挂起的读取器；RQ-215 同时记录了
`iterator=failed`、`sdk_stream=closed` 的 `client_wakeup_close_race`。复核对象链后确认，
失败不是 provider 正文或模型响应问题，而是取消线程在读取线程仍执行 Python 生成器时调用
`generator.close()`。Python 不允许从另一个线程关闭正在执行的生成器。

## 决策

在候选 `ZhipuStreamSession` 内采用“外层响应先关、读取器自有栈收尾”的顺序：

1. 读取开始和结束由会话内部计数，状态更新受锁保护；
2. 有活跃读取时，`close()` 只先关闭外层 SDK stream/response；迭代器不跨线程关闭，
   而是登记为 deferred resource；
3. 读取线程自己的 `finally` 在 `next()` 返回或失败后关闭该迭代器，并更新分资源报告；
4. 没有活跃读取时，继续逐资源最多关闭一次，并保留原有控制异常和安全错误语义；
5. 延迟收尾期间报告保持 `not_observed`，真实资源关闭后才派生 `closed`；任何失败只保留
   body-free 状态，不泄露 SDK 文本。

这只修复候选隔离接缝，不改变 RQ-215 旧回执/schema，不增加持久字段，不打开
`capabilities.streaming`，不注册候选，也不接入产品 Runtime、AgentLoop、Workbench、
Portal、Account、Auth 或默认模型。

## 本地证据

- 两个离线 transport gate 阶段现在均得到 `cancel_status=returned`、`reader_woke=true`、
  iterator/SDK/composite 全部 `closed`，投影结论为 `client_wakeup_clean`；
- 新增阻塞读取回归：外层 stream 关闭后，活跃迭代器在释放前保持
  `not_observed`，读取栈释放后只关闭一次并变为完整 `closed`；
- 候选聚焦集合 `61 passed`，`compileall`、`git diff --check` 和治理检查通过；本轮真实
  API 调用为 0；同 SHA 公共 CI 尚待本地提交后执行。

## 限制与拒绝外推

该修复只说明当前 Python 客户端对象链不再主动制造已知的跨线程生成器关闭竞态；它不证明
智谱服务端原生取消、底层 HTTP response 的独立可取消性、任意同步 opener 都能在硬截止内
返回，或模型一般能力与生产 streaming 成熟度。若外层 response close 本身阻塞，进程边界
仍必须 fail closed。RQ-215 的真实回执保持不可变，不能用本地修复回写历史观察。

## 后续闸门

先取得本实现提交的 exact-SHA 公共 CI，再回到
`candidate-transport-gated-real-observation / pending-next-decision` 做是否重新观察的裁决。
本 ADR 不授权新的真实请求、G53-7、候选注册或 8F。
