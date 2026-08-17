# 5F-2 Offline Protocol Adapter Spike 退出审查

## 1. 本地结论

本地裁决为：

```text
pass-with-boundaries
```

它的准确含义是：官方 Pi Agent Core 0.84.2 已能在一个隔离、无真实模型 I/O 的 sidecar 中完成
受限 Agent loop、Python ToolRuntime 往返、预算停止、Usage 完整度映射和安全终态投影，因此可以在
本提交获得 exact-SHA 公共 CI 后，交给 5F-3 做更严格的合同、安全和 Harness 对照。

它不表示采用 Pi，不表示 Pi 比当前 Python AgentLoop 更好，也不表示真实模型、ReviewHarness、
AgentRuntime Trace、FastAPI 或产品链已经迁移到 Pi。

## 2. 这一步解决的具体问题

RiftCoach 当前主体是 Python，Pi 官方实现是 TypeScript/Node。如果直接把产品改写到 Node，或直接
启动完整 Pi Coding Agent，那么模型、工具、Session、权限、Harness 和产品编排会一起变化，实验
结果无法归因。

5F-2 因此只回答一个更小的问题：

> 在 Python 继续拥有产品策略和工具权限的情况下，能否把“模型提出 ToolCall、执行 Tool、读取
> ToolResult、继续下一轮”的循环暂时交给 Pi？

采用的边界是：

```text
Python trusted controller
  ├─ strict request / Tool contract
  ├─ total deadline + child terminate/kill
  ├─ credential-free child environment
  └─ existing ToolRuntime
            │ versioned, bounded JSONL
            ▼
Node sidecar
  ├─ official Pi Agent Core 0.84.2
  ├─ one Agent per process
  ├─ Scripted StreamFn（不是在线模型）
  └─ one knowledge.search proxy
```

## 3. 底层原理

Agent loop 本质上不是“连续调用大模型”这句口号，而是一个受控状态循环：

1. Runtime 把当前消息和允许的 Tool 合同交给 Provider；
2. Provider 返回最终文本或一个/多个 ToolCall；
3. Runtime 在产生副作用前检查 Tool 白名单、参数、重复调用和预算；
4. ToolResult 作为新 observation 回到消息历史；
5. 下一轮继续，直到 final、预算、错误或超时终止。

Pi 在本实验中负责第 1、2、4、5 步的 loop/state 推进；RiftCoach adapter 仍控制第 3 步和最终安全
投影。Scripted StreamFn 从冻结脚本产生 Provider 事件，因此本轮测的是 Runtime 协议和控制流，
不是模型智能。

## 4. 已实现的数据流与控制流

### 正常 Tool round-trip

```text
run.start
→ provider_started
→ scripted ToolCall(knowledge.search)
→ whole-batch preflight
→ tool.request
→ Python ToolRuntime
→ tool.response
→ Pi 写入 Tool observation
→ 第二次 scripted response
→ final draft
→ run.result
```

Tool 参数和结果只在进程内 JSONL 中瞬时传输。最终 `safe_events` 只保存事件类型、ordinal、iteration、
Tool name/version、有限失败码和 Usage 完整度；不会保存 Prompt、query、知识 chunks、Tool data、
原始异常或 secret。最终文本仅作为尚未发布的 draft 返回，不拥有发布权。

### 失败路径

非法 JSON、错误 run ID、超长 frame、异常 stderr、子进程崩溃、Tool contract drift 和总 deadline
都会 fail closed。父进程返回稳定错误码，不把 stderr/异常正文写入结果。

## 5. 关键实现

- `app/evaluation/pi_runtime/models.py`：严格、冻结的请求、脚本、Policy、Event、Tool projection、
  Result 与 completeness-aware Usage；
- `app/evaluation/pi_runtime/protocol.py`：协议版本、frame type、run ID、单行和 256 KiB 上限；
- `app/evaluation/pi_runtime/controller.py`：安全环境、Node 子进程、JSONL、ToolRuntime、deadline、
  terminate/kill、stderr 和安全错误映射；
- `experiments/pi_runtime/sidecar.mjs`：官方低层 `Agent`、Scripted StreamFn、整批 preflight、顺序
  Tool proxy 和安全结果；
- `experiments/pi_runtime/package-lock.json`：两个直接依赖和全部传递依赖的 exact lock；
- `.github/workflows/tests.yml`：公共 CI 显式安装 Node 24，并在隔离目录执行
  `npm ci --ignore-scripts`。

## 6. 测试如何证明行为

| 证据组 | 数量 | 证明内容 |
|---|---:|---|
| Protocol/contract | 13 | strict request、Usage 四态、body-free projection、JSONL 版本/大小/非法输入 |
| Sidecar/controller | 20 | direct final、真实本地 RAG Tool、越权/重复/预算/Schema、Provider/Tool/进程/超时/环境错误 |
| Python/Pi narrow parity | 2 | 成功 Tool 顺序/终态，以及最后迭代在 Tool I/O 前停止 |
| 聚焦 + 相邻 | 99 | 以上切片与现有 AgentLoop、ToolRuntime、RuntimeUsage、Recorder 不冲突 |
| 完整 Python 回归 | 919 + 110 subtests | 整个仓库通过；唯一 warning 为既有 TestClient 弃用提示 |

测试中所有“Provider”均为 Scripted/Fake；真实 Provider、Riot API、模型 Key 和 held-out I/O 为 0。

## 7. 实验中发现并修正的问题

### 7.1 严格合同与 JSON 反序列化不是同一件事

Pydantic strict Python 模式要求 Enum 和嵌套模型已经是 Python 类型，但 JSONL 天然传来字符串和
对象。第一版 controller 因而把合法的 `"complete"`/`"unknown"` 误判为 `invalid_event`。

修复不是放宽模型，而是在 JSON 边界使用 `model_validate_json`；进入模型后仍保持 strict。这体现
了“传输解析”和“领域合同”要分层。

### 7.2 stdout/stderr 存在并发到达顺序

stdout 和 stderr 由两个 reader thread 读取。子进程退出时 stdout EOF 可能先入队；如果父进程只
取一个队列项，可能漏掉 stderr 并错误接受成功结果。controller 现在等待唯一、限长的 stderr
payload，再只暴露 `unexpected_stderr` 安全码。

### 7.3 最后迭代必须在 Tool 副作用前停止

当前 Python AgentLoop 在最后一个允许迭代收到 ToolCall 时不会执行 Tool。Pi 默认会执行 Tool 后
再请求下一轮。adapter 已把 `max_iterations` 放入整批 preflight，恢复零副作用语义。

### 7.4 失败 Tool 也必须消耗调用预算

第一版 sidecar 只计成功 Tool，失败 Tool 可能绕过 `max_tool_calls`。现在预算依据全部
`toolExecutions`，不是成功数。

### 7.5 abort 不是普通 provider failure

Pi 的 scripted abort 已映射为 `stopped/provider_aborted`，而普通 Provider 错误仍为
`failed/provider_error`；二者不会被压成同一终态。

## 8. 依赖和进程成本

本机 Node 为 24.18.0、npm 为 11.17.0。`npm ci --ignore-scripts` 的第二次本地测量约 6063 ms；
安装树为 94 packages、11,355 files、62,364,713 bytes。两个传递依赖声明 install script，但本轮
安装命令禁止执行；`node-domexception@1.0.0` 有 deprecated 警告。

六次每 run 新建 sidecar 进程的 direct-final 测量为 399.75-453.15 ms；首次 408.54 ms，后五次
中位数 413.71 ms。这只是当前 Windows 开发机的量级，不是生产 benchmark，也不代表 Linux CI、
真实 Provider 或并发负载。

该结果已经表明：Pi 不是“免费替换一个 Python 类”。跨语言依赖、约 62 MB 安装树和每 run 新进程
延迟都必须进入最终采用裁决。

## 9. 当前限制

- Node Permission Model 是 defense-in-depth，不是网络沙箱；当前 no-I/O 依赖无 Key、无真实
  Provider、Scripted StreamFn 和不构造网络 Adapter；
- ToolRuntime 是同步且依赖 Tool handler 遵守 `ToolContext` deadline；本实验不能硬杀正在 Python
  线程中不合作的 Tool handler；
- 只比较了一个成功 Tool round-trip 和关键预算切片，尚未证明完整 Runtime event/Trace parity；
- 尚未把 typed structured output、ReviewHarness、revision/publication、Artifact/receipt 接入 Pi；
- 尚未测真实 Provider、真实模型质量、真实流式输出、并发、Session、恢复或部署；
- `external_provider_calls=0` 是由构造路径与测试输入保证的实验属性，不是网络抓包结论。

## 10. 为什么现在不能 adopt

Pi Agent Core 已证明“能跑受限 loop”，但采用一个第三方 Runtime 还需回答：

- 能否保持我们现有 Tool/Context/deadline/structured output 的精确合同；
- 能否让 ReviewHarness 继续拥有唯一发布权；
- Pi events 能否无损映射到 Runtime Trace/Usage/terminal；
- 跨语言成本是否换来了真实维护收益，而不只是多一层协议。

这些属于 5F-3 和最终 5F-5。5F-2 只能给出进入下一道评估门的资格。

## 11. 初学者/面试表述

可以这样说明：

> 我们没有直接把主项目迁到 Pi，而是把 Pi 当作受测 Runtime 放在 Node sidecar 中。Python 父进程
> 保留 Tool allowlist、ToolRuntime、总 deadline 和错误投影；Pi 只运行 Scripted Agent loop。我们
> 用版本化限长 JSONL 做 ToolCall/ToolResult 往返，并测试越权、重复、预算、Usage 缺失、崩溃和
> stderr。结果证明协议可行，但也量化出 94 个依赖、约 62 MB 安装树和约 0.4 秒新进程开销，所以
> 下一步是合同/Harness 对照，而不是立刻替换自建 Runtime。

## 12. 当前验收状态

- [x] 严格协议、Usage、frame 合同
- [x] exact Node dependency/lockfile 与 ignore-scripts 安装
- [x] 官方 Pi Agent Core + Scripted StreamFn sidecar
- [x] Python ToolRuntime 往返和真实本地知识工具
- [x] 越权、重复、预算、失败、进程、stderr、deadline 和环境边界
- [x] 窄范围 Python/Pi call-order/terminal 对照
- [x] 本地完整回归、RAG、compileall、Harness/secret/governance/diff 门禁
- [ ] 实现提交、推送和 exact-SHA GitHub Actions
- [ ] 公共成功后正式关闭 5F-2，并只交接 5F-3 准备状态
