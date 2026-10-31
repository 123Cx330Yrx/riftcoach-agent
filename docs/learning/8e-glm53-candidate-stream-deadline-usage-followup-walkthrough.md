# RQ-207：候选流硬截止与 Usage 尾帧 walkthrough

## 先说这次解决什么问题

RQ-206 不是“模型拒绝了”，而是一次真实流在很晚才出现正文，旧观察器又只能在
`next()` 返回时检查时钟。于是“每次读最多等多久”和“这次尝试总共最多等多久”被混成
了一件事：流不断吐出晚到事件时，请求可能超过 90 秒仍继续。另一个事实是，流的
Usage 可能不在 `stop` 那一帧，而在后面一个没有 choices 的尾帧；关闭失败也不能被
当成正常 EOF。

本轮只把这些事实做成候选评估层可测试的控制合同，不把它接进产品。

## Agent/软件原理

可以把一次流想成“借来的资源”：

1. **先记账，再打开。** primary 在任何 I/O 前 reserve，超时和关闭失败仍有结算行。
2. **墙钟是整次尝试的预算。** 用 attempt 起点加 90 秒的绝对截止，而不是每次
   `next()` 重新给一段时间。
3. **取消必须是资源合同。** watchdog 不杀任意线程，只调用会话声明的非阻塞
   `cancel`；会话负责让阻塞读取醒来，并负责 `close` 自己拥有的资源。
4. **未知就保持未知。** 没看到 Usage 就不能算成本或把 token 写成零；看到 stop/EOF
   也不能越过缺 Usage、截止或 close 失败。

## 代码地图

- `app/evaluation/candidate_stream_contract.py`：`CandidateStreamSession` 与
  `CandidateStreamDeadlineSupervisor`。它保留旧 iterable 接口，同时给硬截止路径一
  个明确的 cancel/close 能力门；没有显式 session opener 时会在 legacy opener I/O 前
  拒绝，session opener 返回值仍要在调用后验证。
- `app/evaluation/candidate_recovery_diagnostic_v2.py`：硬模式在 opener 前验证会话，
  用 supervisor 包住一次事件泵；普通离线模式仍走旧接口。
- `app/providers/zhipu_stream_adapter.py`：`ZhipuStreamSession` 预先打开并拥有 SDK
  流，逐块转成中立事件，支持 `close`/`__exit__` 回退和安全关闭状态。
- `app/providers/zhipu.py`：只有显式候选调用才发送
  `stream_options={"include_usage": true}`。
- `app/evaluation/candidate_recovery_diagnostic_real.py`：真实候选入口只接显式会话，
  不改变产品 Provider 注册或默认模型。

## 数据和控制流

```text
reserve(primary)
      │
      ├─ 记录 attempt_started_at
      ├─ 验证 CandidateStreamSession
      ├─ 打开 ZhipuStreamSession（候选显式请求 Usage）
      ├─ watchdog 等待绝对截止
      │      └─ 到点只调用 cancel("elapsed_limit")
      ├─ 一次事件泵 → body-free observer + 内存 assembler
      ├─ 每次 next 前后检查截止，晚到事件不下游
      ├─ terminal + Usage / 一个 Usage-only 尾帧才可完整
      ├─ close/settle（关闭失败保留为次级证据）
      └─ body-free receipt；activation disabled，不发 recovery
```

这里有一个重要的工程边界：如果 opener 自己永久卡住，Python 没有安全的通用强杀
方式；如果 SDK 的 `close()` 也会阻塞，watchdog 同样不能凭空制造唤醒能力。因而“可
取消会话 + 供应商连接/关闭截止”是硬截止的前提；不满足前提时，系统必须 fail closed，
而不是声称已经有全路径硬墙钟。

## 为什么 Usage 尾帧要单独处理

供应商常把终止原因放在有 choices 的帧，把 token 用量放在随后一个空 choices 帧。
装配器因此允许严格的两种完成形状：同一帧 terminal+Usage，或 terminal 后恰好一个
Usage-only 帧。任何重复、提前、带正文的尾帧都毒化本次装配。这样“看到 stop”不会
被误报成“已经知道成本且可交付”。

## 测试如何证明行为

- 阻塞 `next()` 的 fake 会在 watchdog 到点后被 cancel 唤醒，并只关闭一次；
- 已过 `started_at` 的会话立即触发截止，证明预算从 attempt 起算；
- 取消后才返回的晚到事件不会被 yield；
- 普通 provider 异常只留下安全 `stream_read_failed`，不泄露异常正文；
- deadline 是主错误时，close 错误不会覆盖它；取消内部触发的 close 失败也会保留；
- 候选会话请求 Usage 字段，重复 close 和仅有 `__exit__` 的资源都能安全收口；
- 没有显式会话的旧 transport 在 opener I/O 前得到 `hard_deadline_unsupported`。

本轮四个候选/适配器测试文件共 `67 passed`；没有新的真实请求。完整项目测试如果
碰到本机 PostgreSQL 未启动，只能说明环境缺口，不能改写上述离线证据。

## 当前边界与下一步

候选仍 `activation_state=disabled`、`execution_allowed=false`，严格 Flash v1 仍为
2048/零额外调用，`capabilities.streaming=False`；没有产品 Runtime、AgentLoop、
Workbench、Portal、Account、Auth、路由、G53-7、黄金切片或生产准入变化。

下一项是同一实现提交的 exact-SHA 公共 CI。公共 CI 之后，是否重新做一次真实观察仍
要单独授权；如果真实 opener 的可取消性不能被证明，就继续 fail closed。

## 面试时的准确说法

> 我为候选评估增加了一个显式可取消流会话和绝对墙钟监督器。它从 attempt 起点计时，
> 到点只调用会话承诺的 cancel，并用一次事件泵同时做脱敏边界观察和临时装配；Usage
> 缺失、晚到事件或关闭失败不会被伪造成成功。旧 iterable 和产品 Provider 保持兼容，
> 候选仍未注册，所以这不是“产品已经接入 streaming”的结论。

## RQ-209 真实观察后记（2026-09-02）

RQ-209 在上述离线实现上只执行 1 次有界真实 primary。公共闭环树
`015b022bfce6d03452f753794ac126a377f8355b` 作为实现/诊断身份，普通智谱
`zhipu/glm-5.3-flash` 使用 `max_tokens=8192`、attempt 90 秒、transport 120 秒、SDK retries=0，显式请求
Usage。首事件/打开计时 `3421ms`，reasoning 非空；`90015ms` 触发硬墙钟，未见正文、terminal、EOF 或 Usage，
回执为 `fail_closed / elapsed_limit`，组合会话 `close_state=failed`，没有 recovery/重试。

回执由本地证据提交 `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存，SHA-256
`56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`、`4342` bytes；公共 CI 尚未宣称。
这里的组合 `close_state=failed` 不是供应商 SDK 具体资源的判决，不能证明 response close 的成败或唤醒能力；
截止前 `observation.elapsed_ms=0` 也不是零耗时，真实时序以 latency `90015ms` 为准。

这次观察只证明诊断层在 attempt 墙钟到点作出 fail-closed 决定；候选仍为 activation gate disabled、
activation_state=candidate 且未注册，产品 Runtime、默认模型、
Workbench、前端、Auth、路由和 `production_media=0` 不变。下一精确 checkpoint 仍需新的明确一次性授权，才能
设计/拆分 provider close/wakeup 资源状态或再次观察。
