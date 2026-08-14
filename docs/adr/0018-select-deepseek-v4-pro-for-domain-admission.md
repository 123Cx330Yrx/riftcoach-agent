# ADR-0018：选择 DeepSeek V4 Pro 作为唯一领域准入候选

## 状态

已接受；取代 ADR-0017 的候选模型与金额停止线；未来 Flash 归属由 ADR-0019 修正

## 日期

2026-08-14

## 背景

ADR-0017 以“用较低成本验证第二个 Provider Adapter 是否可移植”为首要目标，选择了
`deepseek-v4-flash`。这个考虑对单纯协议探针是合理的，但不足以覆盖 D5 的完整目的。

D5 的唯一候选不仅要通过 JSON 与 Tool Calling 协议门，还会在协议通过后参加同一 3 场
领域 held-out，验证 Skill、Context、RAG、AgentLoop、Evaluation 和 ReviewHarness 的
完整控制流。若只因更便宜而选择 Flash，得到的领域证据不能充分代表我们真正关心的
复杂生产 Agent 能力。

DeepSeek 官方在 2026-08-13 发布 V4 Pro 正式版，并把它定位为复杂生产 Agent 与代码
任务的高能力模型。官方同页对比中，V4 Pro 在 Terminal Bench 2.1、NL2Repo、Cybergym、
DeepSWE、Toolathlon、AutomationBench 和 DSBench-Hard 上都高于 V4 Flash。两者同时
支持本轮需要的 non-thinking、JSON output、Tool Calls 和 1M 上下文，因此从 Flash
改为 Pro 不要求另一套 Agent、Skill、Harness 或 Provider 抽象。

## 决策

选择 DeepSeek 官方直接 API 的 `deepseek-v4-pro` 作为 D5 唯一第二 Provider 模型候选。

实现仍命名为厂商级 `DeepSeekProvider`，模型 ID 由受控配置提供；本次协议门和领域门
必须绑定同一个精确模型 `deepseek-v4-pro`，不能用 Flash 通过协议后再换 Pro 跑领域集。

继续沿用 ADR-0017 和 D4 设计中的以下边界：

- 只增加一个 DeepSeek Provider 和一个候选模型，不做 Multi-Agent、自动模型路由或
  网页模型选择器；
- non-thinking、非流式、SDK retry=0、Tool retry=0、`max_revisions=0`；
- DeepSeek protocol 最多 3 calls，领域最多 12 calls，累计最多 15 calls；
- GLM 领域最多 12 calls；
- 每个领域案例最多 4000 observed tokens，每请求输出最多 1024 tokens；
- 先离线 TDD、完整回归和 exact-SHA 公开 CI，再决定是否执行真实协议门；
- 协议通过后才能运行冻结 held-out，首次结果不得反向调 Prompt；
- usage 缺失、身份漂移、预算失效、公开工件泄密或 unsafe publication 仍按原停止规则
  fail closed。

唯一预算更正是：DeepSeek 协议加领域实验的应用层金额停止线由 `$0.05` 提高到 `$0.10`。
官方公布的 2026-08-16 起 V4 Pro 峰值价为输入未命中缓存 `$1.32/M tokens`、输出
`$3.96/M tokens`。即使把 DeepSeek 的 16000-token 总上限极端地全部按输出价估算，
成本也约为 `$0.06336`；`$0.10` 能覆盖该最坏估算并保留小额余量，同时调用数、每请求
输出和累计 Token 仍是更硬的出网前边界。

## 方案比较

### 保留 V4 Flash

Flash 更快、更便宜，适合协议 smoke test 或以后按成本/时延分层的简单任务。但本次只有
一个候选且要承担领域准入，优先选择它会继续混淆“Adapter 能否工作”与“复杂领域任务
是否值得采用”。因此拒绝作为本次唯一候选。

### 同时测试 Flash 与 Pro

这会把一个第二 Provider 准入门扩大成同厂商模型排行，增加真实调用、解释分支和首次
held-out 暴露面。当前没有证据需要两个 DeepSeek 模型同时进门，因此拒绝。

### Flash 跑协议、Pro 跑领域

协议准入证据必须绑定精确模型。拆用模型会让 Pro 的结构化输出、工具调用和响应规范化
未经同一门验证，因此拒绝。

### 只测试 V4 Pro

它保留一 Provider、一模型和同一控制变量，同时让唯一领域候选更贴近未来生产目标。
绝对实验费用仍受很小的硬边界控制。接受。

## 影响

### 正面

- 候选选择与 D5 的领域准入目标一致；
- 不增加 SDK、Provider 数量或 Agent 控制流复杂度；
- 协议与领域证据绑定同一精确模型；
- 以后若需要 Flash，按 ADR-0019 在 5P 后、默认于阶段 6 依据真实成本/时延 Bad Case
  单独评估任务分层；该实验不属于 5F。

### 负面

- 单 Token 价格高于 Flash；
- 三场 held-out 仍只是小样本准入，不能证明 Pro 普遍优于所有模型；
- `$0.10` 是应用层停止线，不是厂商账户级硬消费限额。

### 不变边界

- 本 ADR 没有实现 Adapter、读取密钥、调用真实 Provider 或运行 held-out；
- GLM 仍是首个真实基准，尚未选出生产默认模型；
- Qwen3.8 Max 仍是以后可重新评估的候选，不因本决定被判定为较差；
- 不改变阶段 0-8，也不进入 5E、5F、MCP、Memory、Multi-Agent 或前端。

## 证据与后续门

- DeepSeek 官方更新记录（V4 Pro GA 与官方 Agent 基准）：
  <https://api-docs.deepseek.com/updates/>
- DeepSeek V4 官方说明（Pro/Flash 定位）：
  <https://api-docs.deepseek.com/news/news260424/>
- DeepSeek 官方模型能力与价格：
  <https://api-docs.deepseek.com/quick_start/pricing/>
- DeepSeek Thinking Mode：
  <https://api-docs.deepseek.com/guides/thinking_mode/>
- `docs/plans/2026-08-14-second-provider-adoption-gate-design.md`
- `docs/adr/0017-select-deepseek-v4-flash-as-bounded-second-provider-candidate.md`
- `docs/adr/0019-defer-deepseek-model-tiering-until-product-evidence.md`

本 ADR 接受时的唯一下一步是 D5 离线 TDD；D5 现已完成离线实现。动态唯一下一步只看
`docs/project_execution_state.md`，ADR-0019 不改变当前 Pro-only 准入顺序。
