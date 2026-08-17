# 5F-2 Offline Protocol Adapter Spike 实施计划

## 1. 目标

用一个完全离线、可删除、可拒绝的纵向切片证明：Python RiftCoach 能否通过严格协议驱动官方 Pi
Agent Core 0.84.2，同时仍由 Python ToolRuntime 执行 `knowledge.search`，且不改变主产品 Runtime。

## 2. 初学者理解

Agent Runtime 的核心循环是：模型提出动作，程序校验并执行动作，再把观察结果交回模型。Pi 和
RiftCoach 自建 AgentLoop 都在做这件事。5F-2 不是比较“谁回答得聪明”，而是比较一个第三方循环
能否遵守我们已经建立的安全和可观测合同。

跨语言 sidecar 可以理解为一个受限的实验室：Python 是实验负责人，Node/Pi 是待测设备。负责人
只给设备一份冻结输入；设备若要调用工具，必须向负责人申请；负责人可以拒绝、计数、超时并终止
设备。设备永远没有产品发布权。

## 3. 范围

实现：

- Pydantic 严格协议模型、版本和 frame 大小限制；
- Python 子进程 controller、最小环境、deadline/terminate/kill；
- exact npm dependency 与 lockfile；
- Node ESM sidecar、一个 Pi Agent/run、Scripted StreamFn；
- 只读 `knowledge.search` Tool proxy；
- 整批 Tool 原子预检、跨轮 duplicate、iteration/tool budget；
- complete/partial/unknown/not-applicable Usage 映射；
- body-free 安全事件和稳定终态；
- 离线协议、进程和真实本地知识工具测试；
- 安装树大小和冷启动测量。

不实现：

- 真实 Provider、模型 Key 或网络模型调用；
- Pi Coding Agent、文件/命令工具、Session、Extension、Skill discovery、MCP；
- 将 Pi 接入 `AgentRuntimeV1` 或 FastAPI；
- ReviewHarness parity、产品采用或真实模型质量结论；
- 阶段 6、Memory、前端或部署。

## 4. 数据流与控制流

```text
frozen request + scripted responses
                │
                ▼
Python PiSidecarController
  ├─ strict request validation
  ├─ safe child environment
  ├─ total deadline
  └─ existing ToolRuntime
                │ run.start JSONL
                ▼
Node sidecar + Pi Agent Core
  ├─ scripted StreamFn
  ├─ batch preflight
  └─ knowledge.search proxy
                │ tool.request
                ▼
Python ToolRuntime → tool.response
                │
                ▼
Pi next turn → safe event/result projection
```

`run.start` 和 `tool.response` 是 Python→Node；`tool.request`、`event` 和 `run.result` 是 Node→Python。
每一帧都必须匹配 protocol version、run ID、类型和大小。最终正文可以作为尚未发布的 draft 返回，
但安全事件不能含正文、Tool 参数或 Tool 结果。

## 5. TDD 批次

### Batch A：协议红灯

- 请求/脚本/Tool/Usage/result 严格模型；
- 非法字段、run ID、版本、超长 frame 和未知类型拒绝；
- complete/partial/unknown/not-applicable Usage 不变量。

### Batch B：供应链冻结

- 创建私有 Node package；
- exact `0.84.2`、official registry lock integrity、无 install scripts；
- CI 安装 Node 24 并执行 `npm ci --ignore-scripts`；
- 记录依赖数量、磁盘大小和冷启动。

### Batch C：sidecar 与 controller

- 直接 final；
- 一次 `knowledge.search` 后 final；
- stdout 非法 JSON、错误 run ID、异常退出、stderr 和 timeout fail closed；
- 子进程环境不含 Key/Token/Secret。

### Batch D：安全与预算

- 未授权 Tool、同批超限和同批/跨轮重复均在 Tool I/O 前停止；
- Tool schema 错误与 Tool failure 返回稳定安全码；
- Provider error/abort、iteration/context/deadline 映射；
- 安全事件不含 Prompt、query、Tool data 或原始异常。

### Batch E：同切片证明与退出

- 使用冻结 recent-form 风格 Context、真实本地 `knowledge.search`、Scripted StreamFn；
- 对照当前自建 AgentLoop 的调用顺序和终态，不接 ReviewHarness；
- 完整回归、两套 RAG、compileall、Node install/测试、治理和 diff 门；
- 形成 5F-2 `pass-with-boundaries` 或 `reject`，只交接 5F-3，不自动实施。

## 6. 验收标准

- 所有 scripted cases 无真实 Provider/Riot I/O；
- 只有一个注册 Tool，且任何非法 batch 的 Python ToolRuntime 调用次数为 0；
- deadline 后无迟到 Tool 执行；
- Usage 不把未知值写成零；
- safe events 不保存数据正文；
- Node 进程失败不会产生成功终态；
- package-lock 可在 Linux CI 以 `npm ci --ignore-scripts` 重建；
- 主 `app.agent.loop`、`app.runtime`、Harness 与 FastAPI 行为不变。

## 7. 当前步骤

Batch A-E 的本地实现、窄 parity、门禁与退出审查已完成，裁决为 `pass-with-boundaries`。提交
`f62f078` / Actions `32022258177` 已完成 exact-SHA 公共 CI，5F-2 正式关闭并只交接
`5F-3-contract-security-harness-evaluation` 准备状态；这不表示 Pi 已采用或真实模型质量已经验证。
