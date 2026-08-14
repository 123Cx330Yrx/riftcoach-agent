# 5D-7 Batch D D5：DeepSeek Provider 离线实现计划

## 1. 目标与证据边界

本批实现 D4 已冻结的离线纵向切片：独立 `DeepSeekProvider`、安全 Agent 失败观察、
实验级调用/Token/成本控制器，以及不创建真实客户端的 no-I/O dry-run。所有 Provider
行为由 Fake SDK 或 Scripted Provider 驱动，外部 Provider 调用必须为 `0`。

本批只能证明 RiftCoach 的 Adapter 映射、失败边界和实验仪器可运行，不能证明
`deepseek-v4-pro` 的真实可用性、质量、延迟、成本或领域准入。

## 2. 选定方案

### 2.1 Provider Adapter

选择独立 `DeepSeekProvider`，复用现有 provider-neutral `ChatRequest/ChatResponse`，
但不继承或通过修改 base URL 复用 `ZhipuProvider`。两者当前只有消息、工具和严格 JSON
解析的部分实现相似；thinking、usage、finish reason 和错误语义仍按厂商分别测试。

暂不抽取通用 OpenAI-compatible 基类。只有两个 Adapter 的测试证明一段逻辑拥有相同
前置条件、错误语义和演进方向后，才允许后续小范围提取 helper。

### 2.2 失败归因

新增只包含 `AgentRunStatus`、`AgentStopReason` 和安全 `error_code` 的不可变失败观察。
`AgentDraftPreparationError` 可以携带该观察，但不携带消息、Prompt、模型正文、Tool
Observation 或原始异常。Harness 仍捕获草稿准备失败并按原策略降级；外层
`SkillReviewExecutionResult` 同时取得安全观察，解决 5D-6b 的来源丢失。

### 2.3 资源控制

新增实验专用、组合式 Provider 包装器，不把 D5 的价格快照写入通用 AgentLoop：

1. 每次 I/O 前检查全局/Provider 停止状态、调用上限、每请求 `max_tokens` 和最坏输出成本；
2. 检查通过后先占用一次调用，再委托底层 Provider；
3. 统一响应返回后要求可用 usage，按实际输入/输出 Token 结算成本；
4. 累计 Token 或金额越界时不把该响应交给 Agent，并停止该 Provider；
5. `unsafe_publication` 触发全局停止。

此 ledger 是应用层实验停止器，不冒充厂商账户硬限额，也不替代 5E 的统一 Usage/Trace。

### 2.4 no-I/O dry-run

新增准备 CLI，只读取公开冻结的 Dataset/Prompt-Context snapshot、Git SHA 和显式传入的
公开 CI SHA；不加载 `.env`、不读取 Key、不实例化 OpenAI Client、不运行 held-out。
SHA、模型、base URL、retry 或冻结身份不匹配时在任何 Provider 对象创建前失败。

## 3. 实现顺序（TDD）

### Task 1：DeepSeek Adapter 红灯与实现

- 新增 Fake SDK 测试，覆盖四类消息、`thinking=disabled`、非流式、JSON mode、
  `AUTO/NONE`、请求级工具别名和 usage；
- 覆盖 `REQUIRED`、structured+tools、并行调用、未知别名、重复 JSON key、空 content、
  非空 reasoning、缺 usage、未知/不一致 finish reason 和脱敏 SDK 错误；
- 新增严格 DeepSeek 配置与 client factory，冻结官方 base URL、Pro 模型和 `max_retries=0`。

### Task 2：安全失败观察红灯与实现

- Agent Provider failure 产生安全观察；
- 观察穿过 `_BoundAgentDraftPreparationStep`；
- Harness 仍返回 deterministic degraded/rejected，不发布 Agent 草稿；
- 结果与 warnings 不含 Provider 原文或异常。

### Task 3：预算 ledger 与停止控制器红灯及实现

- 第 16 次 DeepSeek 和第 13 次 GLM 调用在底层 Provider 前失败；
- 每请求输出上限、累计 observed tokens 和金额停止线不可绕过；
- 调用在委托前计数，SDK 失败不退还；
- usage 缺失不按零结算；
- Provider stop 与 unsafe-publication global stop 使用白名单码；
- 公开 snapshot 只含计数、Token、估算金额、状态和安全码。

### Task 4：no-I/O dry-run 红灯与实现

- 精确校验 `deepseek/deepseek-v4-pro/https://api.deepseek.com/retry=0`；
- 精确校验 held-out、Prompt/Context snapshot、Evaluation 版本和当前/公开 CI SHA；
- 默认路径只准备实验，不执行协议案例或 held-out；
- 测试注入一个会在创建客户端时失败的工厂，证明 dry-run 没有触碰它。

### Task 5：回归与公开证据

- 聚焦测试、相邻 Provider/Agent/Harness/Domain 回归与完整 pytest；
- 两套 RAG 门禁、compileall、Harness dry-run、安全/敏感数据检查、governance、
  `git diff --check`；
- 更新唯一执行状态、活动计划、findings/progress、路线历史、能力矩阵和项目决策；
- 提交、推送并核验 exact-SHA GitHub Actions；
- CI 成功后运行一次 no-I/O dry-run。该动作仍不读取 Key 或调用 Provider。

## 4. 失败模式

- 配置/身份漂移：`provider_configuration_invalid`、`experiment_identity_mismatch`、
  `dataset_not_frozen` 或 `public_ci_sha_mismatch`；
- Provider：映射为 D4 白名单 `provider_*` 分类；
- Agent：`agent_provider_failed` 或 `agent_control_flow_incomplete`；
- 资源：`external_call_budget_exhausted`、`token_budget_exhausted`、
  `cost_budget_exhausted`、`latency_budget_exhausted`；
- 安全：任一 `unsafe_publication` 全局停止。

未知值保持 unknown/安全未知码，不能猜测原始响应，也不能转换为成功或零成本。

## 5. 明确不做

- 不读取 API Key，不调用 DeepSeek、GLM 或 Qwen；
- 不运行 held-out，不调 Prompt，不修改冻结期望；
- 不注册生产默认模型，不做网页模型切换或自动模型路由；
- 不进入 5D exit review、5E、5F、LangGraph、Agent SDK、MCP、Memory、Multi-Agent
  或前端。
