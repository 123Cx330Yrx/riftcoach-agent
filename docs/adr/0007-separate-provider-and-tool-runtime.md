# ADR-0007：分离 Provider 与 Tool Runtime

## 状态

已接受

## 背景

RiftCoach 当前多处直接创建 OpenAI-compatible Client，Riot、Data Dragon、RAG 与 GLM 也缺少统一可靠调用机制。EchoMind 的 `MCPToolManager` 提供了缓存、熔断、fallback 和统计等参考，但将 Anthropic Client、工具执行、查询改写和重排放在同一模块中，而且并非标准 MCP。

需要在不改变 Harness、RAG、Skill、Memory 和 MCP 阶段边界的前提下，隔离模型厂商差异并统一工具可靠性。

## 决策

建立两个独立层次：

1. `LLMProvider`：定义厂商无关聊天契约和错误分类，首个实现为智谱 GLM；
2. `Tool Runtime`：定义工具注册、Schema 校验、有限重试、TTL 缓存、熔断、fallback 和指标。

Harness 通过 Adapter 使用这两层，但仍独立负责工作流状态、Artifact 和发布门控。内部 Tool Runtime 不命名为 MCP。

阶段 3 保持同步单进程。网络超时由底层客户端严格执行，Runtime 传递预算并拒绝超期结果；不使用无法安全终止的线程模拟强取消。

## 影响

### 正面

- 业务代码不再依赖具体 SDK 响应结构；
- 可独立替换模型 Provider；
- 外部工具共享一致的可靠性和可观测性契约；
- EchoMind 的有用机制得到迁移，但不保留职责混杂和命名误导；
- 为阶段 5 Skills、阶段 6 API/Memory 和阶段 7 MCP 提供稳定底座。

### 负面

- 增加一层类型和 Adapter；
- 阶段 3 需要迁移现有脚本，短期存在旧入口和新入口并行；
- 同步 v1 不能强制终止任意阻塞 Python Handler。

### 中性

- 阶段 6 若全面异步化，需要提供异步 Provider/Runtime 或同步桥接；
- 阶段 8 才实现通用取消、租约、检查点和恢复。

## 备选方案

### 只抽象 LLM Client

改动更小，但不能统一 Riot、RAG 和 Data Dragon 的可靠调用，因此不采用。

### 直接复制 EchoMind MCPToolManager

可以较快获得缓存和熔断，但会带入 Anthropic 耦合、RAG 职责混杂、不完整 Schema 校验和非标准 MCP 命名，因此不采用。

### 直接引入通用工作流或微服务平台

当前调用规模和单机部署不需要微服务、消息队列或通用 DAG，运维成本高于收益，因此不采用。

## 参考

- `references/echomind/source/python代码/EchoMind/mcp/tool_manager.py`
- `docs/roadmap.md` 阶段 3
- `docs/plans/2026-07-23-provider-tool-runtime-design.md`
