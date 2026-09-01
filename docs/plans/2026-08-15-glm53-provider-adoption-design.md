# GLM-5.3 Provider 迁移门设计

## 这份设计解决什么问题

当前 RiftCoach 已经有两类互不等价的 Zhipu/GLM 证据：

1. GLM-5.2 的最小 structured/tool Adapter 协议曾通过；
2. GLM-5.2 的 recent-form 领域切片没有形成完整的 Agent 结果，因此领域能力没有准入。

GLM-5.3 是同一厂商的新模型，但官方迁移要求改变思考参数：GLM-5.3 始终启用
thinking，不能使用当前 GLM-5.2 适配器固定发送的
`{"thinking":{"type":"disabled"}}`；官方要求使用 `enabled`，并可设置
`reasoning_effort=low/high/max`。官方页面还说明 Coding Plan 已开放，而普通模型 API
将逐步上线。因此不能把 GLM-5.3 当成已经通过原有 GLM-5.2 证据的透明升级。

官方资料：

- https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3
- https://docs.bigmodel.cn/cn/guide/coding-plan/latest-model

## 已确认的边界

- 当前唯一进行中的检查点仍是 `5D-7`；本设计不改变 DeepSeek 新鲜领域采用门的顺序。
- 当前 DeepSeek Adapter、DeepSeek 结果、DeepSeek 预算和旧 held-out 结果不修改、不覆盖、
  不重跑。
- GLM-5.3 暂时是“同厂商新模型候选”，不是默认 Provider、不是自动路由、不是
  Multi-Agent，也不是把 GLM-5.2 的结果改名。
- 本设计本身不读取 API Key、不调用 Provider、不修改生产默认模型。

## 选择的迁移时机

### 现在不切换默认模型

当前 5D-7 的唯一下一步是先设计新的、未污染的真实领域采用门。若此时把默认 GLM
从 5.2 改为 5.3，会同时改变 Provider、thinking、响应格式和模型行为，破坏正在进行的
DeepSeek 实验变量隔离，也让旧 GLM-5.2 证据难以解释。

### 允许切入的检查点

在当前 5D-7 新鲜领域采用门完成设计/离线 TDD/公开 CI 后，单独开启一个
`GLM-5.3 adoption gate`，按以下顺序推进：

1. **G53-0 无 I/O 可用性与配置审计**：核对账号类型、endpoint、正式模型 ID、thinking
   参数和 API/Plan 权限；没有这些信息不读取 Key。
2. **G53-1 Adapter Profile 离线 TDD**：把思考配置从 Provider 硬编码中抽出，保留
   GLM-5.2 `disabled` 兼容 profile，增加 GLM-5.3 `enabled + low` profile；验证
   structured output、ToolCall、多个 ToolCall、reasoning 字段、finish reason、usage
   和错误脱敏。
3. **G53-2 公开 exact-SHA CI**：只有离线合同和隔离测试通过后，才允许任何真实请求。
4. **G53-3 有界真实 Adapter 协议门**：最多 3 次调用，独立结果文件，先验证文本、
   structured、tool round-trip 和 thinking/usage；这是协议准入，不是领域准入。
5. **G53-4 新鲜领域采用门**：使用新的 Dataset/Input Plan/Prompt Context snapshot，
   不复用 DeepSeek 或 GLM-5.2 的旧结果。通过正常复盘、用户注入、知识注入、事实/引用、
   资源和安全发布分层检查后，才讨论是否把 GLM-5.3 设为默认。

## 需要改什么

### 必须改造的地方（G53-1 才做）

- `app/providers/zhipu.py`：不再全局固定 disabled thinking；按模型 profile 构造请求，
  严格解析 GLM-5.3 的 enabled thinking 响应。reasoning 内容不能进入报告、公开结果或
  证据；若后续请求需要回传厂商要求的 reasoning 字段，必须先做明确的 provider-neutral
  合同设计。
- `app/providers/config.py`：增加显式、可审计的 thinking profile 配置，不能让调用方
  随意覆盖安全参数；GLM-5.2 与 GLM-5.3 使用不同 profile。
- `scripts/probe_zhipu_capabilities.py`：结果和默认文件名按实际 model/profile 生成，
  不再把所有实验写进 `zhipu_glm52_*`；旧结果只读保留。
- Zhipu Adapter 测试：新增 GLM-5.3 enabled/low、reasoning、structured/tool、
  多 ToolCall 和错误边界；当前 Zhipu 仍拒绝多个 ToolCall，是否采用顺序批次必须先
  由离线合同和真实响应决定，不能因为 DeepSeek 已修复就自动复制。

### 不需要改造的地方

- Riot API、MatchAnalyzer、RAG、Skill、AgentLoop、ReviewHarness 的领域合同不因换模型
  而重写；它们只消费 provider-neutral `ChatRequest/ChatResponse`。
- DeepSeek 文件、DeepSeek 独立配置、DeepSeek 结果与 DeepSeek 新鲜采用门不因 GLM-5.3
  迁移而改变。

## 隔离规则

- GLM-5.3 实验使用独立 model/profile/result 文件和新的 experiment ID；不能覆盖
  `zhipu_glm52_*` 或 `deepseek_*` 结果。
- 真实实验前使用临时环境覆盖或显式 profile，不直接把工作树 `.env` 的默认模型改成
  GLM-5.3。
- 每次 Provider 结果都记录 provider、model、profile、code SHA、CI SHA、dataset/snapshot
  SHA、调用/Token/费用和安全错误码；不保存 Key、Prompt、模型正文或 reasoning 原文。

## 采用判定

| 层级 | 通过意味着什么 | 不意味着什么 |
|---|---|---|
| Adapter profile | 能正确发请求和归一化响应 | 不代表 Agent 能完成复盘 |
| 3-call protocol | 生产接缝能完成结构化与工具往返 | 不代表报告质量或抗注入 |
| 新鲜领域门 | 在同一 Harness、RAG、评测和安全门下完成任务 | 不自动证明比 GLM-5.2 或 DeepSeek 更好 |
| 默认切换决策 | 质量、成本、延迟、失败率达到明确阈值 | 不等于实现自动模型路由 |

## 风险与回退

- API 只对 Coding Plan 开放或普通模型 API 尚未开放：停在 G53-0，不读取 Key、不伪造
  失败为模型质量问题。
- GLM-5.3 的 reasoning/ToolCall 结构与当前 Adapter 不同：停在 G53-1 的离线红灯，
  只改 Zhipu 接缝，不触碰 DeepSeek。
- 多 ToolCall 再次出现：先复用 AgentLoop 的整批原子预检原则，但是否修改 Zhipu
  Adapter 仍需独立 ADR/测试。
- 领域门失败：保留 GLM-5.2 基线和确定性 fallback，GLM-5.3 不设为默认。

## 初学者理解

换模型有两层工作：

1. **接头兼容**：我们的 Provider Adapter 能否把请求和响应翻译正确；
2. **实际能力**：模型能否在 RAG、工具、评测和发布门里完成真实复盘。

GLM-5.3 只因为“版本号更新”不能跳过这两层。当前我们只记录迁移路线，下一步仍先完成
5D-7 既定的零调用新鲜领域采用门设计。

### 后续执行记录：RQ-165（2026-08-31）

后续公开资料核对确认普通 API 的 `glm-5.3-flash` 与标准端点，G53-1 已按本设计完成本地
thinking profile 离线 TDD。原文中的 G53-0/普通 API 未开放是当时的历史状态；当前仍不代表
账号权限、真实协议、领域质量或默认切换。随后 G53-2 已以
`0f97b92683e4981842e745a695864deb611bb630` / Actions `33325222755` 完成 exact-SHA 三 job 公共验证；
下一检查点为等待独立授权的 G53-3 有界协议门。

### 后续执行记录：RQ-167（2026-08-31）

用户明确继续后，G53-3 以最多三次硬预算启动一次普通 API `adapter_protocol`。A1 结构化合同第 1 次调用
返回脱敏 `authentication_failed`，A2 跳过，`calls_used=1/3`、`admitted=false`；客户端无重试，未追加请求。
该结果不区分 Key、权限或端点接缝，也不代表模型质量。下一步需用户确认凭证接缝并另行决定是否重开同一协议门，
G53-4 仍保持关闭。

### 后续执行记录：RQ-168/169（2026-08-31）

前次 Key 已确认被删除。用户创建新的普通 API Key 并修正 `.env` 后，G53-3 以普通端点和
`glm-5.3-flash` 重开；A1 结构化合同与 A2 Agent 工具往返均通过，严格 `3/3` 次、`admitted=true`。
脱敏结果保留在 `zhipu_glm53_flash_adapter_protocol_retry2.json`；G53-4 仍是独立、待授权的新鲜领域门。

### 后续执行记录：RQ-170 G53-4（2026-08-31）

用户授权后，按本设计使用全新匿名 Dataset、Input Plan 与 Prompt/Context snapshot 执行一次真实领域门；
no-I/O preflight 先校验全部身份、预算和不可覆盖输出路径，未在预检阶段构造 Provider 或发起外部调用。
真实运行首案第 1 次响应触发当前适配器的 `unsupported_parallel_tool_calls` 安全拒绝，后两案按首错停止跳过；
领域使用 `1/12` calls、`0` normalized tokens，累计含 G53-3 为 `4/15` calls、`1115` tokens，费用状态 `unknown`。
不可变脱敏结果 `zhipu_glm53_flash_domain_adoption_v1.json` SHA-256 为
`ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`；不含 Key、Prompt/响应正文、reasoning、
完整请求标识或注入 marker。结论为 `completed-local-rejected`，不改变默认 GLM-5.2；新领域 runner/资产尚未
通过 exact-SHA 公共 CI，因此不得将本地结果描述为公共生产准入，也不自动重跑已见考卷。
