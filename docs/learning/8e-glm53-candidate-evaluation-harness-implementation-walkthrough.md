# 8E 学习材料：GLM-5.3 候选评估台实现（RQ-200）

## 1. 问题与原理

流式模型可能只返回 reasoning、以 `length` 截断、缺少 Usage，或者在正常结束前
被网络/客户端打断。产品响应合同要求完整 EOF、合法终止、关闭和有效 Usage，不能
把“看见过一段正文”当成成功。另一方面，评估又必须在发出请求前记账，才能诚实
记录 open/read/timeout 失败。

本实现用控制面/数据面分离解决矛盾：控制面只保存状态、计数、哈希和安全码；数据面
只在一次本地评估内短暂保存完整 `ChatResponse`。候选资格始终由版本化策略从脱敏
边界快照重算，调用方不能填写资格布尔值。

## 2. 设计与实现

入口是 `CandidateEvaluationHarness.evaluate()`。它先校验精确候选四元身份、请求
metadata 和候选 cap，再让 `CandidateEvaluationLedger` 预留 primary。事件泵只迭代
一次：观察器保留 O(1) 的字段状态，装配器仅在内存中拼接完整响应。正常 EOF 后，
观察器和装配器各自封存；不完整装配永远不交付。

`CandidateEvaluationLedger` 不复用要求“首回合快照已知”的旧恢复账本来制造哨兵，
而是先预留、后观察、再结算。当前 activation gate 是 sealed `disabled`，所以精确
`length + 空正文 + reasoning + valid Usage` 只得到 `awaiting_recovery`，不会发第二
次请求。资源投影把未知 Usage 保持为 `unknown`/`None`。

## 3. 代码地图

- `app/evaluation/candidate_evaluation_harness.py`：RunSpec、staged ledger、事件泵、
  body-free receipt 和一次性结果；
- `app/evaluation/candidate_stream_contract.py`：候选 binding、边界观察器、候选
  transport port 和 `CandidateStreamTrace`；
- `app/providers/stream_adapter_contract.py`：normalized event 校验与临时装配器；
- `app/providers/response_completion_policy.py`：候选完成/拒绝策略的单一事实源；
- `tests/test_candidate_evaluation_harness.py`：fake/local 正常与失败矩阵。

## 4. 数据与控制流

```text
ChatRequest + exact RunSpec
        │
        ├─ 校验 metadata/cap → ledger.reserve(primary)
        │
        └─ 一次 normalized stream
             ├─ BoundaryObserver → 状态/计数/哈希
             └─ StreamAssembler  → 仅内存完整结果
                    │
          EOF + terminal + close + Usage
                    │
          policy 决策 → ledger.settle → Receipt
                    │
          可选显式 consumer（仅完整结果）
```

任何普通 provider/迭代/关闭错误都转成有限的 `error_code/error_stage`；控制异常在
清理后继续传播。候选回执不进入统一 `RuntimeTraceStore`。

## 5. 验证与证据

本地 harness 聚焦测试 `15 passed`，覆盖完整文本/工具、候选截断、部分正文、缺
Usage、open/read/close/clock、一次性迭代、身份、请求 cap、consumer 和脱敏。与
`candidate_stream_contract`、`stream_adapter_contract`、`response_recovery_contract`
相邻回归合计 `102 passed`。另有 Python 3.11/3.13 编译检查、`git diff --check` 和
治理预检；公共 exact-SHA CI 尚待下一检查点，不能把本地数字写成生产成熟度。

## 6. 运行方式

当前只应从测试或显式 evaluation-only 调用方注入 fake/local
`CandidateStreamTransport`。不要把它加入 ProviderRegistry，不要把任意 SDK client
或重试函数传入，不要在回执中落盘正文。若要做真实 recovery 或领域门，必须先取得
独立授权、更新候选 activation/安全合同，并在新的 exact-SHA 上重新验证。

## 7. 失败、安全与边界

- 缺 EOF、终止、Usage、model 或 request identity：`fail_closed`；
- `length` 带部分正文、工具或错误上下文：拒绝候选资格；
- Usage 未知：token 总额为 `None`，预算状态为 `unknown`，不当作零；
- 重复 reserve/settle、第三次调用或跨身份回执：拒绝；
- stream/consumer 的原始异常文本、正文、reasoning 和工具参数不进入诊断；
- 没有自动 retry、resume token、后台任务、ToolRuntime 或产品运行时注册。

本实现仍是 8E 的候选控制面证据：严格 Flash v1、默认模型、Workbench、Portal、
Account、Auth、路由和 `production_media=0` 均不变；8F、公共部署、合规、领域黄金
切片与模型生产准入仍未完成。

## 8. 面试表述

可以这样解释：

> 我没有把一个不完整的流直接塞进产品响应，而是在 I/O 前预留一次候选调用，
> 用同一条事件泵同时生成 O(1) 边界观察和一次性内存装配；只有 EOF、终止、关闭和
> Usage 齐全时才交付临时响应。策略从脱敏快照重新计算，Usage 不确定就保留未知，
> 最终只输出独立的 body-free 评估回执，候选也不会通过注册表偷偷变成生产模型。
