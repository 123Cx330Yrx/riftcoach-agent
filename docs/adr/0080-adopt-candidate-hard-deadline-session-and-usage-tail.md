# ADR-0080：采用候选流硬墙钟会话与 Usage 尾帧接缝

- 日期：2026-09-02
- 状态：`implementation-complete-local / candidate-only / public-ci-pending`
- 范围：Stage 8 / 8E；`candidate-real-call-timeout-usage-followup`（RQ-207）
- 依据：ADR-0071、0072、0073、0074、0079；RQ-181、RQ-191、RQ-206；
  `app/evaluation/candidate_stream_contract.py`、
  `app/providers/zhipu_stream_adapter.py`

## 背景

RQ-206 的一次真实 `glm-5.3-flash` primary 已经观察到 reasoning、可见正文、
`finish_reason=stop` 和 EOF，但首个可见正文约在 151 秒、总耗时约 176 秒；Usage
缺失，且关闭供应商流失败。旧的候选观察器只在同步迭代器的 `next()` 返回后检查
时钟，因此 SDK 的“单次读取超时”并不等于整个 attempt 的墙钟截止：只要晚到事件
持续返回，请求就可能越过 90 秒门。

本门只修复候选评估接缝的控制与资源语义。它不改变产品 Provider、默认模型、
严格 Flash v1、统一 Runtime、Workbench、Portal、Account、Auth 或生产媒体状态。

## 决策

### 1. 为需要硬截止的路径增加显式会话合同

保留既有 `CandidateStreamTransport.open_stream() -> Iterable`，以免破坏旧的
fake/local 夹具。只有显式提供下列能力的 `CandidateStreamSession` 才能进入硬截止
路径：

```text
__iter__() -> Iterator[ProviderStreamEvent]
cancel(code="elapsed_limit") -> None
close() -> None
```

`cancel` 必须是非阻塞的，并保证被取消的 `next()` 能尽快返回；`close` 必须拥有并
幂等释放会话的迭代器和供应商响应。硬模式只会在调用 legacy `open_stream` 前检查
是否存在显式 `session_opener`；如果该 opener 返回旧 iterable，返回值会在 opener 调用
后立即验证并 fail closed，绝不能把它冒充成有硬截止的真实传输。同步 opener 本身的
可取消性仍需由具体供应商层证明。

### 2. 硬截止从 attempt 起点计算，不用线程强杀

`CandidateStreamDeadlineSupervisor` 在 reserve 后、打开会话前记录单调时钟起点，
以绝对截止时间监督整个 attempt。后台 watchdog 只调用会话已经承诺的 `cancel`；
不使用会等待阻塞线程的线程池上下文，也不尝试强杀任意 Python 线程。

每次读取前后都再次检查截止；截止竞争中到达的事件不会被交给 observer 或 assembler。
截止错误始终保留为首要 `elapsed_limit / budget`，取消或关闭失败只能作为次级资源
证据，不能把晚到的 `stop`/EOF 变成成功。

会话 opener 本身若无限阻塞，普通 Python 代码无法安全强杀它；因此本合同要求真实
实现为可取消/有自身连接截止的 opener，并把这项限制记录为未完成的生产门，而不是
伪造“全路径已硬截止”。

### 3. 智谱候选会话显式请求 Usage 尾帧

`ZhipuStreamSession` 只在候选显式调用 `stream_session(...,
include_usage_tail=True)` 时把 `stream_options: {"include_usage": true}` 加入
供应商请求。现有懒惰 `stream_events()` 和产品请求不带该字段，保持旧 payload 与
能力标记不变。

会话拥有原始流及其迭代器，逐块翻译为 `ProviderStreamEvent`；取消/关闭均幂等，
优先调用 `close()`，没有时回退到 `__exit__`，并保存安全的关闭失败状态。供应商
异常只转换为 allow-list 错误码，不把响应正文、reasoning、Key 或异常文本带入回执。

### 4. Usage/终态规则保持严格而不合成事实

沿用 RQ-192/191 的装配合同：

- terminal 与同一帧 Usage 可以完成；
- terminal 后最多接收一个 Usage-only 尾帧；
- 重复 Usage、终态后的正文/推理/工具/空非 Usage 帧、Usage 早于 terminal、EOF
  缺 Usage 均 fail closed；
- 截止或关闭失败时，Usage 保持 `missing/unknown`，不补零、不重试、不把 EOF 当成
  可交付完成。

### 5. 仍是候选评估，不是产品启用

真实诊断入口只使用显式会话和一次事件泵，仍固定 `max_tokens=8192`、单次
agent 90 秒、transport 120 秒、SDK retries=0；activation 仍为 `disabled`，不
发送第二次 recovery。公共 CI、一次新的真实观察、G53-7、黄金切片和产品注册必须
分开记录、分开授权。

## 实现与验证

- `app/evaluation/candidate_stream_contract.py`：会话协议、硬截止监督器、绝对起点、
  安全错误映射和幂等资源状态。
- `app/evaluation/candidate_recovery_diagnostic_v2.py`：硬模式只接受会话，旧模式
  继续接受 iterable；attempt reserve/open/settle 语义不变。
- `app/providers/zhipu_stream_adapter.py`、`app/providers/zhipu.py`：候选会话、
  Usage opt-in、iterator/`__exit__` 回退和关闭失败投影。
- `app/evaluation/candidate_recovery_diagnostic_real.py`：真实候选入口改用显式会话，
  结果文件名升级为 RQ-207 预留名；旧 RQ-206 回执不可变。
- 新增/更新离线测试覆盖阻塞 `next()`、晚到事件、绝对起点、普通异常脱敏、取消/关闭
  幂等、关闭失败主次关系、Usage opt-in、上下文管理器回退和 legacy transport 拒绝。

本地候选相关回归为 `67 passed`（本轮四个文件集合），另有 compileall、diff check
和治理检查；没有新的真实 API 调用。完整项目测试仍受本机 PostgreSQL 控制面未启动
影响，不能把该环境限制写成代码失败。

## 明确边界与下一步

本 ADR 的本地实现不打开 `capabilities.streaming`，不注册候选，不改变 Flash v1 的
2048/零额外调用，也不修改 AgentLoop、Workbench、前端、Auth、路由或
`production_media=0`。当前下一精确 checkpoint 为：

```text
8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam /
candidate-stream-deadline-usage-public-ci / pending
```

先取得同一干净实现 SHA 的 exact-SHA 公共 CI；只有公共证据审查后，才另行决定是否
授权一次新的真实观察。供应商 SDK 的 close 非阻塞性、对阻塞 `next()` 的唤醒能力和
同步 opener 的连接截止仍是新的前置闸门；若这些能力不能证明，必须保持
`hard_deadline_unsupported`/fail closed，不能以“线程已启动”替代硬截止证据。

## RQ-209 验证后记（2026-09-02）

RQ-209 在本 ADR 所述合同上完成 1 次有界真实 primary：普通智谱
`zhipu/glm-5.3-flash` 在 attempt `90015ms` 触发硬墙钟，首事件/打开计时 `3421ms`，reasoning 非空，未见
正文、terminal、EOF 或 Usage，回执为 `fail_closed / elapsed_limit`，组合会话 `close_state=failed`，无 recovery
或重试。body-free 回执（`4342` bytes，SHA-256
`56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`）由本地证据提交
`0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存，公共 CI 尚未宣称。

该结果只验证诊断层在 attempt 墙钟到点作出 fail-closed 决定；组合 `close_state=failed` 不能归因到供应商 response、
迭代器或其他具体资源，不能证明底层 close 非阻塞或唤醒挂起的 `next()`。回执中的
`observation.elapsed_ms=0` 是截止前未结算的初始投影，不是零耗时。原 ADR 的候选隔离、Usage 缺失保持 unknown、
不注册产品 Runtime 的决定继续有效；任何新的关闭资源拆分应另立 ADR-0081，不修改本 ADR 的原始决定。
