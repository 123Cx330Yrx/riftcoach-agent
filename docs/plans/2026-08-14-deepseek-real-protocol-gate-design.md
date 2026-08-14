# DeepSeek V4 Pro 真实协议门执行设计

## 1. 具体问题

D5 已经分别实现了 DeepSeek Adapter、协议切片、实验预算/停止控制器和 no-I/O
preflight，但尚无一个正式入口把四者按安全顺序组合起来。若临时在终端直接调用 SDK，
就会绕过公开 SHA、冻结实验身份、三次调用上限和脱敏结果合同。

因此本批不是再造 Adapter，而是补齐 **真实实验执行接缝**。

## 2. Agent / 软件工程原理

真实模型实验必须把“能否发请求”和“是否应该发请求”分开：

1. 本地代码与公开 CI 身份先通过；
2. 数据集和 Prompt/Context 身份先冻结；
3. 才允许读取本地 Key 并创建客户端；
4. 每次请求在出网前占用预算，返回后再按统一 usage 结算；
5. 生产 Adapter 或协议失败即停止，不能继续消耗请求追绿；
6. 磁盘只保存哈希、计数、状态和安全错误码，不保存 Prompt、模型原文、Key 或原始请求 ID。

这是一条 fail-closed control plane：缺少任一前置证据时，默认行为是不调用。

## 3. 本批实现与明确排除

实现：

- 一个 DeepSeek Pro-only 的真实协议门执行入口；
- exact 3-call 上限和 `$0.10` / Token ledger 的组合；
- Provider/global stop snapshot；
- preflight、协议报告、资源账本和停止状态组成的类型化脱敏记录；
- 输出目录和不可覆盖约束；
- Fake Provider 下的离线 TDD。

不实现：

- 不运行三场 held-out；
- 不比较 Flash、Qwen 或 GLM；
- 不调整 Prompt；
- 不切换产品默认模型；
- 不进入 5F、5D exit review 或 5E；
- 不实现 Multi-Agent 或用户模型选择器。

## 4. 数据流与控制流

```text
CLI 显式确认
  -> clean HEAD == public CI SHA
  -> 冻结 held-out / Prompt-Context 身份预检（不执行题目）
  -> 读取 DEEPSEEK_API_KEY
  -> DeepSeekProvider(deepseek-v4-pro, retries=0)
  -> ExperimentBudgetedProvider(adapter_protocol scope)
  -> AdapterProtocolSliceRunner
       A1: 结构化 JSON，一次调用
       A2: knowledge.search 工具请求 + 工具结果后的最终回答，两次调用
  -> 脱敏 Experiment Record
  -> 新文件写入，拒绝覆盖既有证据
```

协议 runner 自己还有独立的三次调用计数；实验 ledger 再从整个候选实验角度记录累计
calls、Tokens、估算费用和停止原因。两层上限方向一致，但职责不同。

## 5. 测试如何证明行为

- 未显式确认时，Provider factory 不会被调用；
- public CI SHA / 冻结身份失败时，Provider factory 不会被调用；
- 输出越界或已存在时，在真实 I/O 前失败；
- 成功脚本必须刚好形成 1 + 2 次请求，并让协议报告和 ledger 的 calls 一致；
- Provider 失败只留下安全错误码，停止器阻断后续调用；
- 序列化结果不得出现 API Key、Prompt、模型原文、工具原文或原始 request ID；
- 真实调用前仍需完整本地回归、公开 exact-SHA CI 和 no-I/O preflight。

## 6. 局限与后续

本门只回答“生产 Adapter 是否能与真实 Pro 完成最小结构化输出和工具往返协议”，不回答
“Pro 的 RiftCoach 报告是否足够好”。若协议通过，下一批仍需单独决定是否运行冻结的
领域 held-out；若失败，则保存证据并停止，不临场调 Prompt 或改模型。Flash/Pro 分层仍
按 ADR-0019 等待 5P 后、默认阶段 6 的真实产品证据。
