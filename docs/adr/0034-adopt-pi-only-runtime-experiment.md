# ADR-0034：5F 采用 Pi-only Runtime 实验

## 状态

Accepted（仅接受实验范围，不代表采用 Pi）

## 日期

2026-08-17

## 背景

5P 已完成一个本地同步产品切片。RiftCoach 当前已经拥有自己的 Python
`AgentRuntimeV1`、受限 AgentLoop、ToolRuntime、ReviewHarness、Trace、Usage 和
Prompt Program。5F 的问题不是“再找一个模型”，而是判断外部 Agent Runtime 是否能在不
破坏这些产品合同的前提下减少我们需要维护的运行时复杂度。

此前 5F 曾把 Pi 与 Claude Agent SDK 并列为候选，但二者不是同一层面的干净对照：

- Pi 的官方核心更接近轻量、可组合的 Agent Runtime 与多 Provider LLM 抽象；
- Claude Agent SDK 是 Claude Code 同源的完整 Agent Harness，带内置文件/命令工具、Hooks、
  Sessions、Subagents、MCP 和权限模型，并且会同时引入 Claude 模型/平台变量；
- RiftCoach 的主仓库是 Python，而 Pi 官方核心是 TypeScript，跨语言成本本身就是重要实验变量。

## 决策

1. 5F 的唯一实测候选改为 **Pi-only**；Claude Agent SDK 不进入代码级对照、依赖安装或真实调用。
2. Claude Agent SDK 只在本 ADR 和入口设计中作为书面替代方案记录：它不是“质量较差而淘汰”，而是
   当前会同时改变 Runtime、模型、工具和 Session 语义，无法形成清晰的 Runtime 归因。
3. 5F 只评估 Pi 是否能在一个冻结的 `recent-form-review` 受限切片中承担 AgentLoop/Tool
   orchestration 的部分职责；HTTP、Application Service、Domain、Prompt Program、ReviewHarness、
   receipt/query 仍属于 RiftCoach 自己的外层合同。
4. 第一批实验必须使用 Fake/Scripted Provider 和本地知识工具，先证明协议、工具白名单、预算、终态、
   错误、Usage、Trace 和 Harness 接缝；未经新的真实调用授权，不读取模型 Key、不调用 Provider。
5. Pi 只使用官方 TypeScript 包/源码进行审计。未经单独安全与语义审查，不把非官方 Python 移植版
   当作官方 Pi 证据。
6. 实验结果只能导向三种结论：`adopt`、`partial-adopt`、`reject`。无论结果如何，Pi 都不会
   自动成为产品默认 Runtime。

## 非目标

- 不比较 GLM、DeepSeek、Qwen 等模型质量；模型选择仍由独立 Provider 采用门负责；
- 不实现 Multi-Agent、DAG、Memory、MCP、SSE、前端或公网部署；
- 不把 Pi 的工具/UI/编码代理能力搬进 RiftCoach；
- 不因为 Pi 支持多 Provider 就实现任务级模型路由；
- 不用 Fake Provider 的通过结果宣称真实模型效果。

## 采用门

Pi 只有在以下条件全部满足后才有资格进入下一步的局部采用讨论：

- 安全不变量：未经允许的 Tool、超预算、错误终态、未验证输出和 Trace 缺失均不能发布；
- 合同不变量：能映射到当前 `AgentRunRequest`、Agent terminal、Usage、Trace 和 Harness 状态；
- 纵向不变量：同一 frozen `recent-form-review` 切片可从输入经过 Pi adapter 到现有 Harness；
- 运行成本：TypeScript/Node sidecar、进程通信、构建和调试成本必须被实际记录；
- 维护收益：必须有可复现的 loop/runtime 维护面收益，不能只凭“代码更少”或宣传功能判断；
- 失败安全：Pi 进程、工具、Provider 或协议失败时仍能回到当前 deterministic fallback/degraded；
- 评测公平：先使用同一输入、同一工具、同一 Fake/Scripted Provider 和同一质量门合同。

任一强制安全或合同条件失败，默认结论为 `reject` 或停留在“仅吸收设计思想”，不得强行接入。

## 备选方案

### Pi 与 Claude Agent SDK 都实测

拒绝。两个候选会同时引入不同模型、语言、工具、Session 和权限语义，实验成本高且无法清楚回答
“Runtime 是否更合适”。

### 只实测 Claude Agent SDK

拒绝。它更适合 Claude Code 风格的文件/命令 Agent，而不是当前 LoL 领域、Provider-neutral、
外部质量门已冻结的 Python Runtime。

### 完全不做第三方 Runtime 实验

暂不采用。Pi 的轻量 Runtime/多 Provider 方向与当前 AgentLoop 问题有足够相关性，做一个受限、
无 I/O、可拒绝的实验能给出比主观判断更可靠的简历和架构证据。

## 后果

### 正面

- 5F 的实验变量更少，能回答一个清晰问题；
- 保留当前 Python 产品核心和质量门，Pi 失败不会污染主线；
- 跨语言集成成本会被显式评测，而不是藏在“SDK 很方便”的描述中；
- Claude SDK 不会因为名气或功能数量被硬塞进项目。

### 负面

- Pi 官方核心的 TypeScript/Node 边界可能让局部采用成本高；
- 5F 仍需维护一套隔离实验适配层；
- Pi-only 不能证明其他 Runtime 不适合，只能证明当前候选的证据。

## 参考

- [Pi 官方仓库](https://github.com/badlogic/pi-mono)
- [Pi Agent Core 文档](https://www.mintlify.com/badlogic/pi-mono/api/agent/core)
- [Claude Agent SDK 官方概览](https://code.claude.com/docs/en/agent-sdk/overview)
- `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`
- ADR-0029、ADR-0030、ADR-0032、ADR-0033
