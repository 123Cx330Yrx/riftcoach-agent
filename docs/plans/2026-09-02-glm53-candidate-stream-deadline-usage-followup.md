# 8E：GLM-5.3 候选流硬截止与 Usage 尾帧后续计划（RQ-207）

## 状态与边界

状态：`implementation-complete-local / candidate-only / public-ci-pending`。

本计划承接 RQ-206 的一次真实 primary 观察，只处理候选诊断接缝的墙钟、取消、关闭
和 Usage 终态。不会读取新的 Key、不会发真实 API、不会启动服务器，不会注册候选、
切换默认模型、打开产品 streaming、执行 recovery/G53-7/黄金切片，也不改 Portal、
Account、Workbench、Auth、路由或 `production_media=0`。

## 要解决的问题

RQ-206 使用旧的惰性 iterable 时，观察器只有在 `next()` 返回后才能看见时钟。SDK
读超时因此没有形成 attempt 的总墙钟：晚到事件让一次请求拖过 90 秒；同时，供应商
可能把 Usage 放在 terminal 后的空 choices 尾帧，关闭异常也不能被吞成 EOF。

## 冻结的实现方案

1. 保留 legacy `CandidateStreamTransport.open_stream()`，另设显式
   `CandidateStreamSession`（迭代、非阻塞 `cancel`、幂等 `close`）。硬模式先在任何
   legacy opener I/O 前要求显式 `session_opener`；该 opener 返回值随后还要验证，返回
   旧 iterable 就 fail closed。opener 自身的连接截止/取消能力仍是供应商层前置条件。
2. 用 `CandidateStreamDeadlineSupervisor` 以 attempt 开始时的单调时间建立绝对截止。
   watchdog 只调用会话的取消合同；每次 `next()` 前后拒绝晚到事件，不使用线程池等待
   或任意线程强杀。
3. 用 `ZhipuStreamSession` 持有原始 SDK 流和迭代器；候选显式开启
   `stream_options.include_usage`，旧懒惰路径和产品 payload 不变。关闭优先 `close`、
   否则 `__exit__`，重复调用不重复释放，并保留安全 close 状态。
4. 继续使用同一 normalized event pump 驱动 body-free observer 与临时 assembler；
   terminal+Usage 或一个 Usage-only 尾帧才可能完整，缺 Usage/截止/关闭失败保持
   unknown/fail closed。

## 已完成的本地工作

- 增加会话协议、硬截止 watchdog、绝对 `started_at` 和 safe transport error mapping；
- 将 v2 诊断硬模式接到显式会话，legacy 模式行为不变；
- 给智谱 provider 增加候选专用 Usage opt-in 和拥有式会话；
- 真实入口改用会话但不再发第二个请求，RQ-206 回执保持不可变；
- 补齐阻塞读取、晚到事件、普通异常、取消/关闭失败、Usage payload、上下文管理器
  回退和旧 transport 拒绝测试；
- 修正取消触发的关闭失败可能被幂等 close 覆盖的次级证据丢失问题。

## 验证矩阵

| 检查 | 目标 | 本地结果 |
| --- | --- | --- |
| 硬截止/流合同/v2/真实接缝/智谱适配器聚焦 | 行为与脱敏边界 | `67 passed` |
| Python 编译 | 新模块可导入 | 通过 |
| `git diff --check` | 补丁无空白错误 | 通过 |
| 治理检查 | canonical/plan/coverage 一致 | 待文档更新后重跑 |
| 真实 API | 本轮不执行 | `0` 次 |

## 已知限制

- watchdog 只能调用会话明确承诺的非阻塞取消；对没有该合同的旧 iterable 不做“软
  猜测”，legacy 路径在 opener I/O 前失败关闭；若显式 session opener 返回旧 iterable，
  则在 opener 返回后立即失败关闭；
- 同步 opener 若本身永久阻塞，无法由普通 Python 安全强杀，仍需供应商连接截止或
  可取消 opener 的独立证据；
- 当前智谱 wrapper 的 `cancel()` 会调用 SDK `close()`；该 close 是否非阻塞并能唤醒
  阻塞 `next()` 尚未取得供应商层实证，因此真实重测前仍需单独的 provider-level gate；
- Usage 仍以供应商实际尾帧为准，缺失时成本/令牌保持 unknown；本门不估价、不补零；
- 本地 green 只说明候选接缝可复现，不代表模型质量、领域准入、公共生产成熟度或
  8E 完成。

## 当前检查点

实现与离线验证已完成，等待同一干净提交的 exact-SHA 公共 CI：

```text
8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam /
candidate-stream-deadline-usage-public-ci / pending
```

公共 CI 后仍需独立授权，才能决定是否做一次新的真实观察；在此之前不重测、不进入
G53-7、不把候选提升为唯一产品模型。
