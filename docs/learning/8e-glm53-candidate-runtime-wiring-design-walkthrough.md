# 8E 学习记录：GLM-5.3 候选 runtime 接线设计（RQ-196）

状态：`design-complete / candidate-only / historical-design`。RQ-197 已完成本设计所列的本地实现门，当前公共 CI
检查点见 [边界观察实现 walkthrough](8e-glm53-candidate-boundary-observation-implementation-walkthrough.md)。

## 1. 先分清两个问题

想象快递员送来一箱东西。产品接口只有在“箱子完整、封条正确、清单齐全”时才签收；
这相当于 `ZhipuStreamAdapter.assemble()` 返回完整 `ChatResponse`。如果箱子在运输中断了，
我们仍可能需要知道“是否看到封条、是否到了结尾、清单是否有数字”，但不能把半箱货当成
产品结果。这就是候选的 `BoundaryObservation`：只记录外形状态，不保存里面的文字。

RQ-194 已经解决了“完整流怎样装配”的问题，RQ-196 解决的是“候选流怎样被安全观察和
计费”。把两者混成一个接口，最容易出现两个错误：把网络中断当成可恢复，或把候选的
8192 上限偷偷带进严格产品 v1。

## 2. 为什么要四元身份

只写 `model=glm-5.3-flash` 不够。相同模型名可能对应不同的预算、策略和代码版本。
因此每次候选尝试都同时锁定：

```text
zhipu
 + glm-5.3-flash
 + runtime-v2-candidate / 2.0.0
 + fresh-recovery policy-v1 / 1.0.0
```

再加上第几次尝试（primary 或 fresh-recovery）。如果有人把 v1 的 2048 档案、别的
policy 或第三次调用塞进来，应该在发请求前就失败，而不是请求发出后才在日志里解释。

## 3. `BoundaryObservation` 会记录什么

它只记录可以安全复核的“仪表盘读数”：

- 流是否打开、是否真的读到 EOF、是否看到终止码、关闭是否成功；
- 正文和 reasoning 是缺失、空、非空还是类型错误；
- 工具调用数量（不含名称和参数）；
- Usage 是否有效，以及有效时的 token 数字；
- 单调耗时、解析出的安全 model 和 request ID 的 SHA-256；
- 由这些事实推导的状态和安全错误码。

它不记录 Prompt、正文、reasoning 原文、工具参数、Key、SDK 对象和异常原文。特别要
注意：Usage 不知道时不是“用了 0 token”，而是 `None + unknown`。这让成本审计诚实，也
避免恢复调用误以为还有预算。

## 4. 数据和控制流

```text
候选调用方
  ↓ 校验四元身份和预算
ledger 先预留 primary
  ↓
独立候选 transport 打开一条流
  ↓
共享的 chunk 校验/翻译核心
  ├─ 完整 EOF + terminal + Usage → 现有 assembler → 临时完整结果
  └─ length/缺终态/中断 → BoundaryObservation（无正文）
  ↓
完整边界才交给 ResponseCompletionPolicy 分类
  ↓
ledger 恰好结算一次 → CandidateStreamTrace 脱敏投影
```

当前候选仍 `execution_allowed=false`。所以即便第一回合刚好符合“length + 空正文 +
非空 reasoning + 有效 Usage”，结果也只能是 `awaiting_recovery`，不会真的发第二个请求。
严格 Flash v1 仍是 2048 输出、零额外调用；产品 AgentLoop 继续只走同步合同。

## 5. 状态机怎么读

```text
not_started → awaiting_primary → observing_primary
    ├─ complete_text / tool_calls_ready
    ├─ candidate_shape → awaiting_recovery（当前停在这里）
    └─ fail_closed
```

“候选形状”不是调用方填的布尔值，而是观察事实满足 EOF、终态、close 和 Usage 后，
再由版本化策略计算出来。缺 EOF、缺 Usage、关闭失败、模型冲突或工具形状错误都走
`fail_closed`，不能因为“看到了 reasoning”就放行。

## 6. 下一门怎样验证（历史设计出口）

下一门只做 fake/local：先用红灯测试固定值对象和状态转移，再实现共享验证核心、候选
transport port 和脱敏 Trace。测试必须覆盖：

1. 完整文本/工具流与不完整流分流；
2. open、read、translate、EOF、terminal、Usage、close、model、request identity 和工具
   错误；
3. 预留后失败仍只结算一次，重复结算和第三次预留被拒绝；
4. unknown Usage 不伪装成零，任何 `repr`/JSON/异常不出现敏感正文；
5. 既有同步 Provider、AgentLoop、默认 profile 和 `capabilities.streaming=False` 不变。

上述实现任务已由 RQ-197 在隔离分支完成；当前只等待同一干净提交的 exact-SHA 公共 CI，之后才会再讨论是否实现
候选 harness 或允许真实 fresh-recovery。本轮设计本身不等于 streaming 已进入生产，也不等于 G53-7、黄金切片或
Stage 8 完成。

## 7. 面试表述

可以说：“我把完整回答和候选边界观察拆成两条语义路径，共享供应商分块校验；候选
通过四元身份和有界账本显式控制，未知用量不当作零，Trace 只保存状态和数字。”

不能说：“我已经把 GLM-5.3 的 streaming 和自动恢复接入生产 Agent。”
