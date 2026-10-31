# 8E 学习记录：GLM-5.3 候选运行时接线评审（RQ-195）

状态：`review-complete / candidate-only / implementation-pending`。

## 1. 这轮要解决什么问题

RQ-194 已经能把一条完整智谱流变成中立回答，但“能装配完整回答”不等于“可以
接到 Agent 运行时”。候选恢复策略还需要识别一次不完整的 `length` 响应是否符合
白名单；如果把所有异常都当成可恢复，就会把半流、缺 Usage 或错误模型误放行。

## 2. 评审得到的核心结论

产品现有 Runtime 只认识同步 `LLMProvider` 和已注册的 Flash v1。候选 profile v2
和恢复 policy 是另一套身份，不能靠请求 metadata 或更大的 `max_tokens` 偷换。
因此未来应有一个隔离的候选评测调用方，先校验 provider/model/profile/policy 四元
身份，再使用候选 ledger 结算；本轮不实现它。

更重要的是，`ZhipuStreamAdapter.assemble()` 对 `length` 会 fail-closed，不会泄露部分
正文或 reasoning。这对完整回答是正确的，但说明下一门必须单独设计“边界观察”：只
返回字段状态、finish code、Usage、耗时和安全错误码，不返回任何正文或工具参数。

## 3. 数据流

```text
候选调用方（未来）
  → 四元身份校验
  → ledger reserve primary
  → adapter 完整装配 / 边界观察
  → completion policy 分类
  → ledger settle
  → 脱敏 ResponseRecoveryTrace
```

候选仍是 `execution_allowed=False`，所以当前流程最多得到“等待恢复”的状态，不能
真的发第二次请求；严格 Flash v1 的 2048/零额外调用完全不变。

## 4. 测试应该证明什么

- profile/policy/provider/model 任一不匹配都会在 I/O 前拒绝；伪造对象不能冒充注册常量；
- 完整流必须同时有 EOF、terminal 和有效 Usage；
- 不完整流只产生脱敏边界状态，不能生成 `ChatResponse`；
- open/read/translate/close/identity/工具错误都 fail-closed，不隐式 retry；
- ledger 不允许第三次调用，Trace 不可表示 Prompt、正文、reasoning、工具参数、Key
  或原始 request ID；
- 现有 AgentLoop、同步 Provider、默认模型、Workbench 和 `capabilities.streaming=False`
  回归不变。

## 5. 面试表述

可以说：“我把供应商流接缝和产品运行时接线拆开；完整流由中立装配器收口，候选
不完整形状先通过只输出状态的边界观察，再由独立 ledger 和版本化策略决定，避免把
一次错误或半流误当成可恢复回答。”

不能说：“RQ-194 已经把 GLM-5.3 streaming 接进 Agent 生产运行时。”

