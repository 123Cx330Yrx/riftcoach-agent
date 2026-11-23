# ADR-0023：将 GLM-5.3 作为隔离的 Zhipu 模型迁移候选

## 状态

已接受为规划边界；不授权本 ADR 直接切换默认模型或执行真实调用

## 日期

2026-08-15

## 背景

官方 GLM-5.3 文档已发布。文档说明 GLM-5.3 使用与 GLM-5.2 相同的基础模型但有新的
后训练能力，并且当前 Coding Plan 已可使用；普通模型 API 将逐步上线。更重要的是，
GLM-5.3 始终启用思考，不接受 `thinking.type=disabled`，需要 `enabled` 以及
`reasoning_effort` 档位。RiftCoach 当前 Zhipu Adapter 在请求中固定发送 disabled thinking，
并且仍把非空 reasoning 内容视为非法响应。

当前 5D-7 正在处理 DeepSeek 真实领域 Bad Case 的后续采用门。DeepSeek 真实结果已消费
且不可重跑，任何新模型实验都必须与其结果、预算和输入身份隔离。

## 决策

1. GLM-5.2 的历史结果和最小协议证据保持只读，暂不把默认模型改为 GLM-5.3。
2. 当前 5D-7 的唯一下一步仍是设计新的未污染真实领域采用门；不把 GLM-5.3 插入
   DeepSeek 当前运行，不修改 DeepSeek Adapter、配置、结果或 held-out。
3. 在该既定设计/离线 TDD/公开 CI 完成后，单独开启 GLM-5.3 adoption gate：无 I/O
   配置审计 → Adapter profile 离线 TDD → exact-SHA CI → 最多 3-call 协议门 → 新鲜
   领域门。
4. GLM-5.3 首个适配 profile 使用官方要求的 `thinking=enabled` 与 `reasoning_effort=low`；
   具体 endpoint、账号权限和可用模型 ID 必须在 G53-0 核对，不得猜测或硬编码。
5. 只有新鲜领域门在同一 RAG、Skill、AgentLoop、Evaluation、ReviewHarness 和安全合同
   下通过，才另行决定是否替换 GLM-5.2 默认值；这不是自动模型路由，也不是 Multi-Agent。

## 备选方案

### 立即把 `.env` 改成 GLM-5.3

拒绝。当前 Adapter 的 disabled thinking 会与 GLM-5.3 官方迁移要求冲突，同时混淆
DeepSeek 仍在进行的领域采用证据。

### 继续只使用 GLM-5.2，永不测试 5.3

拒绝。新模型的后训练能力可能改善 Agent 工具往返，但不应以版本号或宣传直接采纳；
隔离采用门可以用有限成本获得可审计答案。

### 直接复制 DeepSeek 的 Adapter 修复

拒绝自动复制。不同 Provider 即使都使用 OpenAI-compatible API，也可能在 thinking、
reasoning、ToolCall 批次和 finish reason 上有不同合同，必须各自测试。

## 影响

### 正面

- 保留 GLM-5.2、DeepSeek 和未来 GLM-5.3 的证据可解释性；
- 不会污染或重跑 DeepSeek 已消费的 held-out；
- 把官方 thinking 迁移要求显式化，避免“只改模型名”的假适配；
- 为简历和面试提供清晰的 Provider 迁移与准入门，而非模型堆叠。

### 负面

- 需要增加 Zhipu thinking profile、reasoning 处理和独立结果文件；
- GLM-5.3 在普通 Model API 未开放时只能停在可用性审计；
- 在新鲜领域门通过前不会获得默认模型切换。

## 验收证据

- 官方 GLM-5.3 页面与当前账号 endpoint 权限已核对；
- offline Adapter profile 测试覆盖 enabled/low、结构化、工具、reasoning 和错误边界；
- exact-SHA CI 成功且无真实 Provider 调用；
- 最多 3-call 真实协议结果独立归档；
- 新 Dataset/Input Plan/Prompt Context snapshot 的领域门在同一 Harness 下完成；
- 通过前默认模型、DeepSeek 结果和旧 GLM-5.2 结果均未被覆盖。

## 参考

- https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3
- `docs/plans/2026-08-15-glm53-provider-adoption-design.md`
- `docs/adr/0012-partially-admit-zhipu-provider-capabilities.md`
- `docs/adr/0022-sequentially-consume-multi-tool-call-batches.md`

## 后续执行记录：RQ-165（2026-08-31）

公开资料已经确认普通 API 的 `glm-5.3-flash` 模型标识与标准端点，因此按本 ADR 的既定顺序完成了
G53-1 本地离线适配档案 TDD。该实现只证明 profile/Provider/probe 的请求响应合同，仍未完成
exact-SHA CI、三次协议门或新鲜领域门；默认模型、DeepSeek 证据和生产采用边界保持不变。

## 后续执行记录：RQ-166（2026-08-31）

G53-2 已以提交 `0f97b92683e4981842e745a695864deb611bb630` 完成 exact-SHA 公共验证，Actions run
`33325222755` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 全部成功。该结果只证明
离线适配合同在精确提交上可复现；没有真实 Provider 调用或 Key 读取，也不改变默认模型、DeepSeek 证据、
Workbench 或生产采用边界。下一步为等待独立授权的 G53-3 最多三次真实协议门，随后才可讨论 G53-4 新鲜领域门。

## 后续执行记录：RQ-167（2026-08-31）

G53-3 首次有界协议尝试在 A1 结构化请求的第 1 次调用返回脱敏 `authentication_failed`，A2 按安全合同跳过，
`calls_used=1/3`、`admitted=false`。没有重试、没有保存正文或 Key；该错误码不能区分凭证无效、权限不足或
账户/endpoint 接缝。G53-3 未通过，G53-4 不启动；下一步需用户确认普通 API 接缝并重新明确授权。

## 后续执行记录：RQ-168/169（2026-08-31）

用户确认旧 Key 已删除，创建新的普通 API Key 并修正普通端点配置后，G53-3 重开通过：A1 结构化合同
与 A2 Agent 工具往返均通过，严格 `3/3` 次调用、`admitted=true`。这只证明隔离候选的普通协议接缝，
不改变 GLM-5.2 默认基线，也不跳过 G53-4 新鲜领域门。

## 后续执行记录：RQ-170 G53-4 新鲜领域门（2026-08-31）

用户在 G53-3 普通协议接缝通过后授权一次真实领域门。按 ADR 既定隔离规则，冻结全新匿名三案例、Dataset/Input
Plan、Prompt/Context snapshot 和硬预算；no-I/O preflight 通过后才创建临时 Provider，输出路径先独占预留。
首案第 1 次响应含并行 ToolCall，Zhipu Adapter 以 `unsupported_parallel_tool_calls` fail closed；没有工具执行、
Evidence、Evaluation 或发布，后两案按首错跳过。领域 `1/12` calls、`0` normalized tokens，累计含 G53-3 为
`4/15` calls、`1115` tokens，费用状态为 `unknown`。
不可变脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_v1.json` 的 SHA-256 为
`ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`。结论为 `admitted=false` /
`completed-local-rejected`；该结果不具备 public CI 语义，不改变默认模型、DeepSeek、Workbench、Auth 或
`production_media=0`，也不授权在同一考卷上重跑或放宽并行 ToolCall 合同。
