# 8E 学习材料：GLM-5.3 候选评估台设计

日期：2026-09-02
对应需求：RQ-199 / ADR-0077

## 1. 这一门要解决什么

前几门已经分别有了“把完整流装配出来”的能力、“只观察边界不保存正文”的能力、
“按版本策略判定是否可能恢复”的能力，以及“最多两次尝试如何记账”的能力。缺的
不是再写一个 Provider，而是一个协调者把它们按正确顺序接起来。

最容易犯的错误有两个：

- 等首回合结束后才记账，导致超时/断流看起来像没有发生过；
- 为了提前建账而塞一个假的首回合快照，随后被迫放宽精确结算检查。

所以本门冻结的是“先预留未知 primary，观察完后才判定形状”的两阶段设计。

## 2. 先理解两个平面

```text
控制平面：身份、预留、结算、状态、Usage、耗时、安全错误码
             ↓ 可形成脱敏 receipt
数据平面：规范化事件、临时正文/reasoning、临时工具参数
             ↓ 只在一次评估内存中存在，消费后立即丢弃
```

控制平面可以审计，但不能回答“正文具体是什么”；数据平面可以供未来的评估器
短暂判分，但不能自动变成产品回答、Runtime Trace 或工具副作用。

## 3. 组件职责

- `CandidateEvaluationHarness`：协调一次 run，不被默认发现；
- staged candidate ledger：在 I/O 前预留，在真实观察后结算；
- `CandidateZhipuStreamTransport`：锁定候选 v2 的 cap、超时和 sampling；
- `CandidateStreamBoundaryObserver`：O(1) 记录生命周期和字段状态；
- `ProviderStreamAssembler`：只有完整流才暂存并构造临时 `ChatResponse`；
- `ResponseCompletionPolicy`：从真实、完整的 boundary snapshot 重新判定；
- `CandidateEvaluationReceipt`：只输出白名单证据，不冒充产品 Trace。

## 4. 一次 run 的数据流

```text
ChatRequest（仅内存） + exact candidate RunSpec
  → 校验身份/上下文/预算
  → staged ledger.reserve(primary)
  → transport.open_stream（只一次）
  → 一次事件泵
       ├─ observer：丢弃正文，只聚合状态
       └─ assembler：暂存完整结果所需正文
  → EOF/close 或安全 abort
  → BoundaryObservation
  → 若 boundary 完整：policy 再计算
  → ledger.settle(primary)
  → 当前关闭 activation：awaiting_recovery；否则终止
  → receipt + 清理内存
```

第二次（将来才可能）仍是一个新的完整请求，不是 API 原生续写，也不是 SDK retry。
它必须再次经过 reserve→open→observe→settle；第二次失败后没有第三次。

## 5. 为什么要 staged ledger

现有 `ResponseRecoveryLedger` 的旧合同适合“已经有首回合快照”的离线测试：它会
要求 primary outcome 与 plan 的 initial snapshot 完全相等。真实评估台在发 primary
前没有这个 snapshot，因此不能直接拿旧构造器配一个 sentinel。

设计解决方法是增加候选专用 staged session（可以是 ledger 的 candidate-only 扩展，
也可以是共享校验核心之上的薄包装）：

1. `reserve_primary()` 只依据受信 profile 的静态预算；
2. 请求结束后把真实观察映射成 snapshot/decision；
3. 冻结 recovery plan，再结算 primary；
4. 只有激活凭据和 policy 同时允许时才出现第二槽位。

这样“失败也记一次”和“资格必须由真实快照重算”两个原则可以同时成立。

## 6. 完整流与候选形状如何分开

`stop` 或 `tool_calls`、真实 EOF、合法 Usage 和必要身份齐全时，assembler 才能
产生临时 `StreamAssemblyResult`。`length`、缺 EOF、缺 Usage、读取异常等情况不能
包装成 `ChatResponse`；observer 只在生命周期完整且形状精确时报告候选形状。

候选形状仍然很窄：

```text
finish=length
content=empty
reasoning=non_empty
tool_calls=0
phase=agent_initial
response contract/tools/side effects=false
剩余时间和 token 足够
Usage valid + EOF + close=closed
```

即使命中，当前 activation 仍关闭，所以结果是 `awaiting_recovery`，不是自动再次请求。

## 7. receipt 里能不能看到正文

不能。receipt 只允许身份、生命周期、字段状态、finish/error code、工具数量、Usage
数字、耗时和预算确定性。正文、reasoning、工具参数、Prompt、Key、SDK 对象和原始
request ID 永不进入 receipt、日志、`repr` 或 JSON。

未来如果需要评价答案质量，必须显式提供 evaluation-only consumer：它在内存中短暂
接收完整结果，返回脱敏标签/分数，不能改变 policy、ledger 或调用 ToolRuntime。这个
consumer 不是本门的实现内容。

## 8. 失败时怎样说才准确

| 观察到的情况 | 准确结论 |
| --- | --- |
| 正常完整 `stop` | 一次完整候选流完成，可作离线评估输入 |
| `length` + reasoning-only 且完整边界 | 命中候选恢复形状，但当前未激活 |
| 90/120 秒内无响应 | 在受控窗口未形成可观察边界，Usage/费用未知 |
| 缺 EOF/Usage 或 close 失败 | 完整性不足，fail closed，不是模型质量结论 |
| 第二次仍失败 | 两次尝试均已记账，禁止第三次 |

这些表述不能升级成“模型已通过领域准入”或“产品已经自动续写”。

## 9. 下一实现要证明什么

下一门只用 fake/local transport，测试：完整文本、完整工具终态、候选形状、各种缺失
边界、取消/关闭异常、unknown Usage、预算溢出、重复结算、身份伪造、body-free
序列化和产品导入隔离。通过后还要同 SHA 公共 CI；真实 API、fresh-recovery、G53-7、
黄金切片、部署合规和 8F 仍是独立闸门。

## 10. 当前边界

Stage 8/8E 仍在进行，8F 尚未开始，`production_media=0`。严格产品 Flash v1 仍为
2048 输出上限和零额外调用；本设计中的候选 8192/一次额外调用只属于未注册、未激活
的评估合同。Portal、Account、Workbench、Auth、路由、默认模型和统一 Runtime Trace
均不改。
