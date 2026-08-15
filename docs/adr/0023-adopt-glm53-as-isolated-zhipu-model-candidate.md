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
