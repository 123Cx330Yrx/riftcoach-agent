# 8E 学习记录：新鲜 G53-3-L 回执延迟口径修复（RQ-233）

## 1. 问题与原则

一次模型调用是否成功，和我们能否生成可信回执，是两件不同的事。本次真实协议运行没有暴露
Provider/API 错误，却在最后的回执校验阶段失败。原则是：没有持久化、可复核的回执，就不能宣称
协议通过；同时也不能把本地计时口径缺陷误判为模型能力失败。

## 2. 设计与实现

`CandidateEvaluationBudgetedProvider` 的延迟用于资源账本，只覆盖 Provider I/O；
`AdapterProtocolSliceRunner` 的案例延迟覆盖 Provider I/O、响应解析和本地工具执行。回执字段
`latency_ms` 原本就由验证器定义为所有协议案例延迟之和，因此修复应当采用协议层数值，而不是
放宽相等校验或删除计时证据。

## 3. 代码地图

- `app/evaluation/glm53_low_profile_protocol.py`：从协议案例计算回执总延迟；
- `tests/test_glm53_low_profile_protocol.py`：新增推进时钟，覆盖真实时间会流逝的情况；
- `app/evaluation/glm53_low_profile_budget.py`：Provider I/O 账本保持原样；
- `app/evaluation/provider_adapter_protocol.py`：协议案例端到端计时保持原样。

## 4. 数据与控制流

```text
真实 Provider 调用 → 预算层记录 I/O 耗时
                  → 协议层完成解析/工具往返并记录案例耗时
                  → 回执取案例耗时总和
                  → 严格 Schema 校验 → create-only 落盘
```

## 5. 验证

真实失败是本次红灯证据：`latency total does not match protocol`，且目标回执不存在。新增推进时钟
测试会让旧实现稳定失败；修复后聚焦回归 `18 passed`，协议、预算和 V2/V3 相邻回归 `32 passed`。
公共 exact-SHA CI 尚待完成，因此当前只能标记为本地完成。

## 6. 运行手册

先运行 `tests/test_glm53_low_profile_protocol.py` 和 V3 gate 相邻测试，再执行 compileall、
`git diff --check` 与治理检查。公共 CI 全绿后，必须由用户重新授权；新的真实运行必须使用新文件名、
create-only 写入和与公共 CI 相同的实现 SHA。

## 7. 失败、安全与边界

首次尝试没有生成回执，所以精确调用数不可持久核验，只能确认最多 3 次且 SDK 零重试。不得补写
猜测结果、覆盖旧证据或自动重跑。修复不改变 Prompt、响应正文、工具参数、密钥的禁止落盘规则，
也不改变候选注册、默认模型、领域门或生产准入状态。

## 8. 面试表达

> 我把“模型调用完成”和“证据可接受”分开处理：真实协议在回执阶段暴露 Provider I/O 与端到端
> 计时口径混用。我没有放宽 Schema 或重跑追绿，而是用推进时钟复现，令回执采用协议案例总耗时，
> 保留预算账本原语义，并要求新实现重新通过公共 CI 和获得真实调用授权。
