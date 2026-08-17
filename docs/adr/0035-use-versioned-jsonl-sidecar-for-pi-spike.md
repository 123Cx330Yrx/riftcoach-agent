# ADR-0035：5F-2 使用版本化 JSONL 隔离 Pi Agent Core

- 状态：Accepted for experiment only
- 日期：2026-08-17
- 范围：`5F-2-offline-protocol-adapter-spike`

## 背景

RiftCoach 的产品 Runtime 是 Python；官方 Pi Agent Core 0.84.2 是 TypeScript/Node。5F-2 需要证明
Pi 能否在不改变 Prompt、Tool 安全、Usage、Trace 和 ReviewHarness 边界的前提下承接 Agent Loop，
而不是把完整 Pi Coding Agent 引入产品。

## 比较的方案

### 方案 A：把产品编排迁入 Node

优点是调用 Pi 最直接；缺点是会同时迁移 ToolRuntime、Harness、Trace 和产品组合，无法归因，也会
形成一次跨语言重写。拒绝。

### 方案 B：通过 Pi Coding Agent RPC/CLI 调用

优点是现成功能多；缺点是同时引入 Session、默认工具、资源发现、扩展、模型与权限语义，实验不再
只是 Runtime 对照。拒绝。

### 方案 C：低层 Agent Core + 版本化 JSONL sidecar

Python 父进程保留策略、真实本地 `knowledge.search`、deadline 和子进程生命周期；Node 子进程每
run 创建一个低层 Pi `Agent`，只注入 Scripted StreamFn 和一个 Tool proxy。双方使用严格、限长、
逐帧 JSONL。采用。

## 决策

5F-2 只允许方案 C，并固定以下边界：

- Pi 依赖位于 `experiments/pi_runtime/`，使用 exact version、lockfile 和 `npm ci --ignore-scripts`；
- 只允许 `@earendil-works/pi-agent-core@0.84.2` 与配套 `pi-ai@0.84.2`；
- 一个子进程只处理一个 run，不使用 Pi Session、ResourceLoader、Extensions 或 Coding Agent tools；
- stdout 只能输出版本化 JSONL；stderr 限长收集且不得进入产品 Trace；
- 子进程环境使用 allowlist，不传 `.env`、Riot Key 或 Provider Key；
- Tool request 必须回到 Python，由现有 `ToolRuntime` 执行；Node 不拥有本地知识库；
- Node 事件只投影安全元数据，不能把 Prompt、Tool 参数/结果、原始异常或 secret 写入结果事件；
- Python 父进程持有总 deadline，子进程不合作时 terminate/kill；
- Node Permission Model 只作为 defense-in-depth，不宣称硬网络隔离；
- Scripted StreamFn 是本阶段唯一“模型”，`external_provider_calls` 必须为 0。

## 失败语义

整批 Tool 数量、allowlist、重复签名和迭代预算必须在任何 Tool request 发出前完成。Provider 已尝试
但没有可验证 Usage 时必须记为 `partial` 或 `unknown`，不能把 Pi 合成零映射为 complete zero。
非法 JSON、超长 frame、错误 run ID、未知 frame、子进程崩溃、超时或异常 stderr 都 fail closed。

## 后果

该方案增加 Node、npm lockfile、IPC 和进程管理成本，但能把跨语言成本本身变成可测证据。5F-2
通过也只说明协议 spike 可运行；是否保持完整 Runtime/Harness 合同属于 5F-3，最终采用决策属于
5F-5。
