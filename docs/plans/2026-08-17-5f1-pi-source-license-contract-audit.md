# 5F-1：官方 Pi Source / License / Contract Audit

## 1. 审计结论

本轮结论是：**允许进入 5F-2 的隔离、无 I/O protocol adapter spike，但不采用 Pi，也不把
Pi 加入主产品依赖。**

Pi 的低层 Agent Core 与 RiftCoach 当前的 AgentLoop 问题确实在同一层：它提供消息状态、
Tool Calling、生命周期事件、Usage 和 Abort 接缝；MIT 许可证也没有阻断实验。然而，它没有
直接提供 RiftCoach 已有的整批 Tool 预检、总迭代/Tool/Context/deadline 政策、Usage 完整性、
安全 Trace 或 ReviewHarness 发布门。跨 Python/Node 的协议与部署成本同样真实存在。

因此 5F-1 只证明“候选值得做一个可拒绝的协议实验”，没有证明“Pi 比自建 Runtime 更好”。

## 2. 给初学者：为什么先读源码，不能先 `npm install`

第三方 SDK 接入会同时带来三类东西：

1. 我们想要的能力，例如 Agent Loop 和 Tool Calling；
2. 我们不一定需要的能力，例如 Coding Agent 的文件工具、Session、扩展和模型注册；
3. 新的失败与安全边界，例如 Node 进程、依赖树、IPC、权限、错误和 Usage 语义。

如果先安装、先写业务代码，再去理解边界，我们很容易把“示例能跑”误认为“产品合同兼容”。
5F-1 反过来先冻结：

```text
官方身份
→ 许可证与运行环境
→ Agent / Provider / Tool / Event / State / Abort / Usage 合同
→ 与 RiftCoach 逐项比对
→ 决定是否值得写最小实验
```

## 3. 可复现的官方身份

### 3.1 仓库迁移

入口设计引用的历史地址：

```text
https://github.com/badlogic/pi-mono
```

当前会重定向到：

```text
https://github.com/earendil-works/pi
```

新的审计和实验不得继续使用旧包名或漂移的 `main` 作为依赖身份。

### 3.2 冻结的发布身份

| 项目 | 冻结值 |
|---|---|
| 官方仓库 | `https://github.com/earendil-works/pi` |
| Release tag | `v0.84.2` |
| Release / npm `gitHead` | `914cf1472e715297caa30db4b9535d534a9eb718` |
| 审计时 `main` | `c7c763f5c48736fa00cdcf0bcbfcae5cbc585e7c` |
| Agent package | `@earendil-works/pi-agent-core@0.84.2` |
| AI package | `@earendil-works/pi-ai@0.84.2` |
| Node requirement | `>=22.19.0` |
| 本机只读检查 | Node `v24.18.0`、npm `11.17.0`，满足最低版本 |

官方 npm registry 对两个包都给出同一 `gitHead`。审计时 `main` 的六个关键文件
（Agent、Agent Loop、Agent types、AI types 和两个 package manifest）与该 release 内容逐字一致，
但 5F-2 仍必须依赖 release tag/package integrity，而不是 `main`。

官方 registry 完整性：

```text
@earendil-works/pi-agent-core@0.84.2
sha512-8Pn3wSCxj0cfo5I6jxQYVB/3uuQRmHhAlEclyjqpOuMEdQMIODHizRogv56FLdbU+dTiGnybeHQ2N+sV1/L2YA==

@earendil-works/pi-ai@0.84.2
sha512-6MzsrYIYNVlE7SfpbL2yYb67Qo58p/7Q+xWG1RZvoX1P80aRCHSod2/13aFpxkow1lPO2LEh3c495J0Gwmyjig==
```

本机全局 npm 当前配置为 `https://registry.npmmirror.com`。这不是失败，但为了让公共实验可复现，
5F-2 必须显式记录 registry 与 lockfile，并以官方 registry metadata/integrity 复核，不能把本机镜像
地址默认为官方供应链身份。

## 4. 许可证结论

仓库和两个候选包均为 MIT License，版权行为 `Copyright (c) 2025 Mario Zechner`。
RiftCoach 本身也是 MIT，因此没有许可证冲突。

如果后续只把 Pi 作为 npm 依赖，保留其随包许可证即可；如果复制或修改 substantial source，
必须在相应分发中保留 Pi 的版权与许可文本。5F-2 不复制 Pi 源码到 Python 模块中。

本结论是工程许可证审计，不是法律意见。

## 5. 审计的真实候选层

Pi 仓库现在同时包含低层 Agent、完整 Coding Agent、Session/Harness、文件工具、搜索等能力。
RiftCoach 只审计和实验：

```text
@earendil-works/pi-agent-core
└── Agent / low-level agent loop / AgentTool / AgentEvent
```

明确不使用：

```text
pi-coding-agent CLI / RPC
默认 read / write / edit / bash 工具
DefaultResourceLoader
Extensions / Skills 自动发现
AuthStorage / ModelRuntime
Pi Session persistence / compaction
Pi 自带 coding-agent Harness
```

原因不是这些能力差，而是它们会把 Runtime、权限、Session、模型和产品编排一起改变，无法形成
干净的 AgentLoop 对照。

## 6. Agent Core 底层数据流

Pi 的低层数据流可以概括为：

```text
AgentState
  ├─ systemPrompt
  ├─ messages
  ├─ model
  └─ tools
        │
        ▼
custom StreamFn（一次 Provider 请求）
        │
        ▼
AssistantMessage
  ├─ text / thinking / toolCall
  ├─ Usage
  └─ stopReason
        │
        ├─ 无 toolCall → agent_end
        └─ 有 toolCall → schema 校验 → Tool execute → ToolResult → 下一轮
```

这与 RiftCoach 自建 AgentLoop 的基本思想一致：模型并不直接执行工具，而是生成 ToolCall；Runtime
验证后调用程序函数，再把 Tool result 作为新消息交回模型。

## 7. 合同映射矩阵

| RiftCoach 要求 | Pi 0.84.2 证据 | 差异与 5F-2 要求 | 判定 |
|---|---|---|---|
| Provider-neutral 调用 | `Agent` 接受自定义 `StreamFn`；`pi-ai` 有统一 Model/stream 合同 | 5F-2 只注入 Scripted StreamFn，不使用模型 Key | 可实验 |
| Tool allowlist | `AgentContext.tools` 是本 run 可见工具；未知 Tool 变为 error result；`beforeToolCall` 可 block | 只能注册 `knowledge.search`；父进程仍需二次核验 | 可实验，有条件 |
| Tool 参数校验 | TypeBox schema + `validateToolArguments` | JSON Schema/TypeBox 与 Python/Pydantic 映射需冻结 | 可实验 |
| 整批原子预检 | Pi 逐个准备/执行；默认并行；没有 RiftCoach 的整批 allowed/duplicate/budget 预检 | 必须在 StreamFn/event adapter 层先检查整批 ToolCall；否则不能保持现有语义 | 明确缺口 |
| 重复 ToolCall 停止 | 未发现跨轮同名同参数去重 | adapter 必须维护 canonical signature 集 | 明确缺口 |
| 最大迭代/Tool 次数 | 有 `shouldStopAfterTurn` 和 Tool hook，但没有同名内建总预算 | adapter 在 Provider 前、整批 Tool 前计数并返回稳定 stop reason | 明确缺口 |
| Context ceiling | 有 `transformContext`，但没有 RiftCoach 的 deterministic fail-closed ceiling | 继续使用 Python compiler/sizer；每次 Provider 请求前复核 | 明确缺口 |
| 总 deadline | `AbortSignal` 贯穿 Provider、hook、Tool；SDK 应用自行持有 deadline | Node 内层 AbortController + Python 父进程超时/kill 双层停止 | 可实验，有条件 |
| Tool 顺序 | 默认 `parallel`，可设为 `sequential` | 首个切片必须显式 `sequential` | 可实验，有条件 |
| Lifecycle event | agent/turn/message/tool start-update-end 事件齐全 | Pi event 含 raw args/result，不能原样持久化到 RiftCoach Trace | 可实验，有条件 |
| Usage | AssistantMessage 必有 input/output/cache/cost；Tool result 可带 Usage | 没有 RiftCoach 的 complete/partial/unknown；失败包装会写零 Usage | 明确缺口 |
| 稳定终态 | `stopReason` 有 stop/length/toolUse/error/aborted/deferred；最终 `agent_end` | 需要映射到 RiftCoach stop reason allowlist；不能暴露 raw error | 可实验，有条件 |
| 质量发布门 | Agent Core 不等价于 ReviewHarness | Pi 只能产生未发布 draft；发布仍由 ReviewHarness 决定 | 外层保留 |
| Trace/receipt | Pi event/state 不是 RiftCoach Trace/receipt | 继续使用现有 Recorder、Trace Store、receipt/query | 外层保留 |

## 8. 三个最重要的语义差异

### 8.1 Pi 默认并行，当前 RiftCoach 是整批预检后顺序执行

RiftCoach 当前在执行任何 Tool 前，会先检查整个模型响应中的：

```text
总 Tool 数
是否全部在 allowlist
是否出现重复调用
```

Pi 默认 `parallel`；即使改为 `sequential`，它也按调用逐个准备和执行。只靠 `beforeToolCall`，
可能先执行前面的合法 Tool，之后才发现同一批后面有非法 Tool。这与当前“整批原子预检”不等价。

所以 5F-2 必须在 AssistantMessage 进入 Pi Tool executor 前检查整批 ToolCall。做不到就不是 parity，
不能因为 Tool 最终被 block 就写“安全合同通过”。

### 8.2 Pi 的失败零 Usage 不等于“确定使用了 0 Token”

Pi `Agent.handleRunFailure()` 会构造一个 `EMPTY_USAGE` 的 error/aborted assistant message。
这能保持类型稳定，但无法单独区分：

```text
Provider 根本未发出请求
Provider 已发出但没有返回 Usage
Provider 确实返回 0
```

RiftCoach 的 `RuntimeUsage` 已把 token observation 分成 complete/partial/unknown/not_applicable。
5F-2 必须独立记录 Provider attempt/response 事实；不能把 Pi 的合成零直接映射为 complete zero。

### 8.3 Pi 的事件正文不能成为产品 Trace

Pi 的 Tool event 会携带 raw arguments、partial result 和 result，AgentState 还保存完整消息与错误。
RiftCoach Trace 的设计恰恰是不保存 Prompt、正文、Tool data、原始异常和 secret。

因此事件 adapter 只能投影安全元数据：

```text
tool name/version/ordinal
success/failure allowlisted code
attempt/latency/cache/fallback
Provider ordinal/phase/finish reason/Usage completeness
Agent terminal
```

## 9. 安全与供应链边界

Pi 官方安全文档明确：Coding Agent 默认运行在启动用户权限内，没有内建 sandbox，并把本地文件、
扩展、Skill 和工作区视为可信边界。它也明确不把 Prompt Injection 当作自身可完全解决的问题。

这意味着 5F-2 不能启动一个带默认文件/命令工具的 Pi Coding Agent。隔离 spike 必须：

- 只导入低层 `Agent`；
- 只注册一个自定义 `knowledge.search`；
- 不加载 extensions、skills、AGENTS 文件或 Pi 配置；
- 子进程使用最小环境变量 allowlist，不传 Riot/Provider Key；
- JSONL frame 有版本、类型、大小和字段白名单；
- Python 父进程保留总 deadline，并在子进程不合作时终止；
- Node `--permission` 作为减少误操作面的 defense-in-depth，不授予 write、child process、worker、
  addon；只允许加载实验入口与固定依赖目录所需的 read；
- 不把 Node Permission Model 描述为恶意代码安全沙箱。Node 官方同样把它定位为 seat belt，
  仍需要 OS/容器级隔离才能防恶意代码。

本机 Node `v24.18.0` 的 `node --help` 没有 `--allow-net`，所以当前 `--permission` 不能被写成
“已硬断网”。5F-2 的 no-I/O 证据来自不传任何 Key、只注入 Scripted StreamFn、不构造真实
Provider，以及对外部调用路径的测试；若 5F-3 要求硬网络隔离，必须另用 OS/容器 `network none`
边界验证，不能借用较新 Node 版本的文档过度宣称。

候选包没有 preinstall/postinstall；但 `pi-agent-core` 依赖 `pi-ai`，后者会带入 Anthropic、OpenAI、
Google 与 AWS SDK 等依赖，即使 Scripted Provider 不使用它们也需要在实际安装树中评测。5F-2
必须使用 exact dependency + lockfile + `npm ci --ignore-scripts`，并记录安装大小与冷启动时间。

## 10. 5F-2 允许的隔离架构

```text
Python test/controller（可信策略层）
  ├─ frozen AgentRunRequest / Context
  ├─ existing ToolRuntime + knowledge.search
  ├─ deadline / process lifecycle
  └─ ReviewHarness（后续仍是唯一发布权）
             │ JSONL，版本化且限长
             ▼
Node sidecar（实验层）
  ├─ @earendil-works/pi-agent-core@0.84.2
  ├─ one Agent per run，no Pi Session
  ├─ Scripted StreamFn，no Provider I/O
  ├─ only knowledge.search AgentTool
  ├─ sequential mode
  └─ safe event/terminal projection
```

不采用 Pi Coding Agent 自带 RPC，是因为它会连同 Session、资源发现、默认工具和 Coding Agent
产品语义一起进入实验。我们需要的是低层 Runtime 对照，不是从 Python 遥控另一个完整产品。

## 11. 5F-2 开始前必须冻结的协议

至少包含：

```text
protocol_version
run_id
message type
request_id / ordinal
payload schema
maximum frame bytes
allowed terminal reasons
allowed error codes
usage observation
parent/child timeout
unexpected stdout/stderr handling
```

Scripted case 至少覆盖：

1. 直接 final；
2. 一次 `knowledge.search` 后 final；
3. 未授权 Tool；
4. 同批 Tool 超限；
5. 重复 Tool；
6. Tool schema 错误；
7. Tool failure；
8. Provider error/aborted；
9. Context/iteration/deadline 超限；
10. 子进程异常退出或输出非法 JSON。

这些都是协议/控制流证据，不是模型质量证据。

## 12. 退出判定

| 判定项 | 5F-1 结果 |
|---|---|
| 官方身份可冻结 | 通过 |
| 许可证允许隔离实验 | 通过 |
| 本机运行版本可达 | 通过 |
| Agent/Tool/Event/Abort 接缝存在 | 通过 |
| 与当前预算/Trace/Usage 完全同构 | 不通过，需要 adapter |
| 可以无 Key 使用 Scripted StreamFn | 通过 |
| 可以直接替换主 AgentRuntime | 不通过 |
| 是否值得进入 5F-2 | **通过，有强制条件** |

5F-2 只有在协议 adapter 通过离线测试后，才有资格进入 5F-3 合同/安全/Harness 对照。若整批
Tool 预检、Usage completeness、deadline、错误脱敏或 Harness 单一发布权无法保持，应当停止并
给出 `reject` / `partial-adopt`，而不是扩大实验范围。

## 13. 本轮没有做什么

- 没有安装任何 Pi/Node 包；
- 没有创建 `package.json`、lockfile 或 sidecar；
- 没有读取 `.env` 或模型 Key；
- 没有调用 Riot、GLM、DeepSeek、Qwen 或其他 Provider；
- 没有修改 AgentRuntime、ToolRuntime、Harness、FastAPI 或产品 composition；
- 没有证明真实模型质量、性能收益或 Pi 已被采用。

## 14. 参考证据

- [Pi 官方仓库](https://github.com/earendil-works/pi)
- [Pi release v0.84.2](https://github.com/earendil-works/pi/tree/v0.84.2)
- [Agent package manifest](https://github.com/earendil-works/pi/blob/v0.84.2/packages/agent/package.json)
- [Agent implementation](https://github.com/earendil-works/pi/blob/v0.84.2/packages/agent/src/agent.ts)
- [Agent loop](https://github.com/earendil-works/pi/blob/v0.84.2/packages/agent/src/agent-loop.ts)
- [Agent types](https://github.com/earendil-works/pi/blob/v0.84.2/packages/agent/src/types.ts)
- [AI types / Usage](https://github.com/earendil-works/pi/blob/v0.84.2/packages/ai/src/types.ts)
- [Pi security policy](https://github.com/earendil-works/pi/blob/v0.84.2/SECURITY.md)
- [Node Permission Model](https://nodejs.org/api/permissions.html)

## 15. 本地验证

审计与状态同步后运行：

- 完整 pytest：`884 passed, 1 warning, 110 subtests passed`；
- RAG development gate：Recall/MRR/nDCG `1.0`，no-answer FPR `0.0`；
- 独立 RAG 4M holdout：全部指标 `1.0`；
- compileall、governance、Harness SDK boundary、tracked secret/run-data、Harness dry-run 与
  `git diff --check` 全部通过。

这些测试证明现有 RiftCoach 没有因审计/路线同步而回归；它们没有执行或测试 Pi，因为本轮没有
安装 Pi。Pi 合同是否能落地只能由 5F-2 的离线 adapter tests 证明。
