# ADR-0017：选择 DeepSeek V4 Flash 作为有界第二 Provider 候选

## 状态

已被 ADR-0018 取代

## 日期

2026-08-14

## 取代说明

本文保留 2026-08-14 当时以“低成本验证 Adapter 可移植性”为首要目标的决策历史。
随后复核发现，D5 不只验证协议接缝，还会让唯一候选进入同一领域 held-out 准入；因此
候选必须优先代表复杂生产 Agent 的领域能力。DeepSeek V4 Pro 正式版与 Flash 共享本轮
所需协议面，却在官方生产 Agent 基准上更强，且有界实验的绝对费用差仍很小。

ADR-0018 因而把唯一候选更正为 `deepseek-v4-pro`，并把 DeepSeek 金额停止线调整为
`$0.10`。除模型 ID 和金额停止线外，本文冻结的独立 Adapter、non-thinking、调用/Token
上限、同任务比较、停止规则与“候选不等于准入”边界继续有效。

## 背景

ADR-0012 只准入了 Zhipu Adapter 的最小结构化输出与工具协议，没有准入 GLM-5.2 的
近期复盘领域能力。ADR-0016 随后要求先版本化安全 Evaluation、建立安全 development
基线和冻结独立 held-out，才能选择最多一个第二 Provider 候选。

这些前置条件现已满足：`coach_evaluation@1.1.0` 和不可修订安全门已接入，7 场离线
development 为 0 unsafe publication，3 场 held-out 已在规则冻结后创建且尚未运行。

现在需要选择一个候选来验证 Provider-neutral 架构是否可移植，但不能把模型热度、单个
样例或“OpenAI-compatible”标签当作准入证据。

## 决策

选择 DeepSeek 官方直接 API 的 `deepseek-v4-flash` 作为 D5 唯一第二 Provider 候选。

这项决定只授权后续离线实现和有界准入设计，不在本 ADR 中接入或调用模型，也不把它设为
生产默认模型。后续执行顺序固定为：

1. 离线实现独立 `DeepSeekProvider`、安全失败归因和实验预算控制器；
2. 本地回归和 exact-SHA 公开 CI 通过；
3. 最多 3 calls 的 Adapter protocol gate；
4. 协议通过后，DeepSeek 与 GLM 分别运行同一 3 场冻结 held-out；
5. 用新的结果 ADR 决定接受、部分接受或拒绝，不根据首次 held-out 调 Prompt。

固定约束：

- DeepSeek 使用 non-thinking、非流式模式；
- SDK retry=0，Tool retry=0，`max_revisions=0`；
- DeepSeek protocol 最多 3 calls，领域最多 12 calls，累计最多 15 calls；
- GLM 领域最多 12 calls；
- 每场最多 4000 total tokens，每请求输出最多 1024 tokens；
- GLM 估算金额停止线 ¥0.50；DeepSeek 协议加领域估算金额停止线 $0.05；
- usage 或可靠价格缺失时停止，不能把成本记为 0；
- 任一 unsafe publication、身份漂移、预算控制失效或公开工件泄密会停止整个实验；
- 5D-6b 的安全错误来源丢失必须先用离线 TDD 修复，不能通过保存原始响应解决。

三层结论保持分离：Adapter protocol admission、domain admission、production adoption。
三个小样本只能作为准入门，不能支持模型排行或统计显著性声明。

## 备选方案

### 不增加第二 Provider

复杂度最低，但不能验证现有 Provider 合同的跨厂商可移植性，也不能帮助区分 GLM 特有
问题与公共控制流问题。在已有真实 Bad Case 和冻结评测合同后继续推迟，信息收益不足。

### Qwen3.8 Max

`qwen3.8-max` 已是正式模型，支持混合思考、Function Calling 和结构化输出。本轮不选
不是质量判断，而是因为 reasoning 回传语义、Token Plan 后端使用限制和标准按量价格快照
会引入更多变量。待这些边界清楚或出现相应 Bad Case 后再通过新 ADR 评估。

### DeepSeek V4 Pro

与 Flash 共享首轮需要验证的协议面，但费用更高。当前目标是验证 Adapter 可移植性而非
最高质量榜单，因此不先引入 Pro；Flash 通过协议后若出现明确质量 Bad Case，再评估。

### 通用 OpenAI-compatible Adapter

拒绝。thinking、reasoning、函数名、JSON、finish reason、usage 和错误语义并不统一。
过早共用 Adapter 会隐藏失败来源。只允许以后抽取被两个独立 Adapter 测试证明等价的纯
helper。

## 影响

### 正面

- 只增加一个候选，控制实现面和外部费用；
- 复用现有 OpenAI SDK，无需引入新 SDK；
- non-thinking 避免当前消息合同立刻承担 reasoning 跨工具回传；
- 价格、调用和 Token 门可在真实请求前复核；
- 同一冻结任务和 Harness 能隔离 Provider 差异。

### 负面

- 仍需维护第二个厂商 Adapter 和错误映射；
- 三个 held-out 只能作小样本准入，不能证明长期质量；
- 应用层金额停止线不是厂商账户级硬消费限额；
- 暂时不能回答 Qwen3.8 Max 与 DeepSeek 的质量优劣。

### 中性

- Zhipu Adapter 和既有失败证据原样保留；
- 用户界面不会因此出现模型选择器；
- 这不是 Multi-Agent、模型自动路由或生产 fallback；
- 不改变阶段 0-8，不进入 5E、MCP、Memory、Multi-Agent 或前端阶段。

## 证据与后续门

- `docs/plans/2026-08-14-second-provider-adoption-gate-design.md`
- `docs/adr/0012-partially-admit-zhipu-provider-capabilities.md`
- `docs/adr/0016-version-injection-evaluation-before-real-provider-comparison.md`
- `data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json`
- DeepSeek 官方 Models & Pricing：
  <https://api-docs.deepseek.com/quick_start/pricing/>
- DeepSeek 官方 Thinking Mode：
  <https://api-docs.deepseek.com/guides/thinking_mode/>
- 智谱官方价格：<https://bigmodel.cn/pricing>
- Qwen 官方深度思考与正式模型：
  <https://help.aliyun.com/zh/model-studio/deep-thinking>
- Qwen Token Plan 使用边界：
  <https://help.aliyun.com/zh/model-studio/token-plan-personal-overview>

唯一下一步是 D5 的离线 TDD 准备：不调用真实 Provider，不运行 held-out。只有离线门、
完整回归、安全扫描和 exact-SHA 公开 CI 均通过后，才可进入单独的有界真实执行批次。
