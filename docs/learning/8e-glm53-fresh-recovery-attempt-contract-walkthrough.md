# 8E 学习材料：GLM-5.3-Flash fresh-recovery 尝试合同

日期：2026-08-31
对应需求：RQ-183 / ADR-0072

## 1. 问题与原理

一次 Provider 调用可能只产出 reasoning，最终没有可交付正文。RQ-181 的具体
形状是 `length + 空正文 + 非空 reasoning + 0 ToolCall`。如果为了“继续生成”在
适配器内部悄悄再发请求，系统会把两次网络消耗记成一次，并且把新的完整请求误说成
API 原生续写。

这里采用两个基本原则：每一个真正发出的底层请求都是独立 attempt；任何恢复都必须
由精确版本合同计划，并在失败时停止。reasoning 只能作为脱敏状态参与判定，不能变成
用户答案或公共证据。

## 2. 本批实现什么

`app/providers/response_recovery_contract.py` 提供四层无网络合同：

- `ResponseRecoveryRuntimeProfile`：候选身份、8192 单次上限、90/120 秒边界和
  candidate 激活状态；它不是现有 `ModelRuntimeProfile` 注册项。
- `ResponseAttemptSpec` / `ResponseAttemptOutcome`：把 `primary` 与
  `fresh_recovery` 以及结束原因、字段状态、Usage 数字分开记录，不保存原文。
- `ResponseRecoveryLedger`：预留一次、结算一次，统计每个底层调用和累计资源；最多
  两次，不产生第三次。
- `ResponseRecoveryTrace`：独立 schema 1.0 的脱敏尝试轨迹，记录身份、判定和资源，
  不改既有 `RuntimeTrace`。

`build_response_recovery_plan()` 会重新运行 RQ-182 候选策略。只有精确白名单形状
才会在离线计划中出现第二个槽位；返回的计划始终 `execution_allowed=false`。

## 3. 代码地图

```text
app/providers/response_completion_policy.py
  └─ 脱敏首回合判定
app/providers/response_recovery_contract.py
  ├─ ResponseRecoveryRuntimeProfile
  ├─ ResponseAttemptSpec / Outcome / Record
  ├─ ResponseRecoveryBudget / Ledger
  └─ ResponseRecoveryTrace
tests/test_response_recovery_contract.py
  └─ 30 项纯离线合同测试
```

## 4. 数据与控制流

```text
首回合 Provider 结果（适配器先脱敏）
  → ResponseBoundarySnapshot + ResponseRequestContext
  → 候选策略重新判定
  → offline-only RecoveryPlan
  → Ledger.reserve_next(primary) / settle(primary outcome) 记录已发生回合
  → 若白名单命中，再 reserve_next(fresh_recovery)
  → 外部执行层（本批不存在）
  → Ledger.settle(sanitized recovery outcome)
  → immutable attempt record / RecoveryTrace
```

首回合不是候选形状时，账本直接终止；是候选形状时，账本先把已观察到的 primary
作为一次已发生调用记账，然后也只能描述一次未来 `fresh_recovery`。账本会重新计算每个 Outcome 的策略判定，因此不能靠调用方传入一个
伪造的 `candidate_eligible=true` 打开恢复。

## 5. 预算合同

候选默认最多两次底层调用、一次额外调用，单次输出上限 8192，累计 input 32,000、
累计 output 16,384、累计观察时间 180,000ms。预留阶段检查剩余 attempt/output/
时间空间；结算阶段再检查实际 token、单次输出和单次时间。Provider 错误、Usage 缺失
和超预算都保留已消耗的调用槽位，不能通过重试抹掉。

这些数字只属于未注册候选，用于离线讨论“是否值得一次新诊断”；它们没有提升当前
产品严格 Flash v1 的 2048/零额外调用，也不是供应商硬上限或生产承诺。

## 6. 验证证据

聚焦命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_response_recovery_contract.py -q
```

结果：`30 passed`。相邻响应策略、Flash runtime、Runtime model、Observed Provider
和领域门回归合计 `128 passed`。测试覆盖身份错配、候选未注册、顺序、并发/重复结算、
预算不足、单次/累计超限、失败消耗、判定重算和 Trace 脱敏。

## 7. 运行方法与安全边界

这是纯 Python 对象合同，不需要 Key、服务器、SDK 或网络。模块没有 Provider 参数、
请求构造或可调用的 retry 入口；任何未来执行都必须在另一个明确授权的运行时层完成，
并保留 A/B exact-SHA、同 SHA G53-3、真实诊断和成本/延迟证据。不要把 Prompt、正文、
reasoning、工具参数、请求 ID 或 Key 写入 Outcome、Ledger 或 Trace。

## 8. 当前限制与后续闸门

- 仍没有 API 原生 resume；`fresh_recovery` 只是一次新的完整请求身份。
- 候选没有注册到产品组合根，不能被 metadata、模型输出或默认配置隐式启用。
- 本地合同测试不证明模型一般能力、领域采用、生产安全/部署合规，也不关闭 G53-7、
  黄金切片、OP.GG breadth 或 8F 作品集闸门。
- 真正接 Provider 前，必须取得新的 exact-SHA 公共 CI、在同一新 SHA 重取协议证据、
  再由用户单独授权一次有界真实诊断；结果不能覆盖 RQ-180/RQ-181。

## 9. 面试准确表述

可以说：

> 我把一次可能被 reasoning 耗尽的 Flash 响应拆成版本化的脱敏判定和有界尝试合同；
> 每个底层请求都进入预算账本和独立 Trace，最多只描述一次 fresh recovery，而且
> 候选未注册、不会偷偷重试。

不能说：

> GLM 已经支持自动续写、8192 已成为产品默认、或这组离线测试等于 G53-7/生产准入。
