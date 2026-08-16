# ADR-0031：采用进程内有界 Worker/Queue 实现 Runtime `stream()` V1

## 状态

Accepted；5E-3 实现与验收仍未完成

## 日期

2026-08-17

## 背景

5E-2 已完成唯一同步 `AgentRuntimeV1.run()`。真实事件由 `RuntimeRecorder` 在 Agent、Tool、
Harness 和终态控制流中产生，但当前只保存在内存，调用方无法在任务结束前消费。最终
`runtime_trace.json` 是原子最终快照，不能代替实时事件。

同时，Runtime terminal 有 prepare → prospective Trace → atomic write → commit 的两阶段语义。
如果 `stream()` 在 prepare 阶段发送 `run_completed`，Trace 写失败就会造成“事件说成功、
结果说失败”的不可修复矛盾。

## 决策

1. `run()` 与 `stream()` 复用同一个 `_execute(request, event_sink)`；不复制 Agent/Harness
   控制流，不把 stream 做成事后 Trace 回放。
2. `stream()` V1 使用每次运行独立的进程内 worker 与有界 `queue.Queue`。不引入外部消息队列、
   durable offset、跨进程重放或新运行时依赖。
3. Recorder 成功追加普通事件后才投递同一个 `RuntimeEvent`；terminal 只在 Trace 原子写成功
   并 `commit_terminal()` 后投递。随后恰好投递一个现有 `RuntimeRunResult`，再结束 stream。
4. queue 满时 worker 阻塞等待，保持事件完整和顺序；订阅者关闭后，stream-only 事件可以停止
   投递以避免后台 worker 永久阻塞，但不取消业务执行，Runtime 仍按原规则完成并保存 Trace。
5. Recorder/Trace/内部 observer 失败属于可信执行面，继续影响 Runtime 结果；订阅者慢、关闭或
   消费侧异常不改写业务终态、Usage、retry、breaker 或 publication。
6. V1 stream 是 Runtime 事件流，不是 Token streaming、SSE、durable event log、cancel/resume、
   Memory、MCP、Multi-Agent、DAG、LangGraph、Pi 或 Claude Agent SDK。

## 方案取舍

### 直接 generator：拒绝

它要求把深层同步 observer 链路改成多层 `yield`，会把消费方停止/异常直接耦合到业务执行，
并且很难在 Trace commit 后才交付 terminal。

### 外部消息队列：拒绝

它会提前引入持久事件、重试、offset、幂等、跨进程生命周期和部署运维语义。当前没有跨进程
恢复或并发消费的可复现 Bad Case；这些能力留给阶段 8。

## 后果

### 正面

- 事件来自真实执行时刻，`run()`/`stream()` 有同源控制流；
- queue 把可信执行面与消费面隔开，慢消费者只形成明确背压；
- Trace 写失败不会先公开成功终态；
- 不新增第三方依赖或模型调用。

### 代价与限制

- stream 只在当前进程内有效；进程崩溃前的中间事件不可恢复；
- 订阅者关闭后 stream item 可能丢失，但业务结果/Trace 不丢失；
- queue 满会暂时阻塞执行，V1 不提供丢弃、取消或多订阅者广播策略；
- API/SSE 和产品前端需要在后续阶段建立自己的连接生命周期合同。

## 验收证据

见 `docs/plans/2026-08-17-agent-runtime-v1-stream-design.md` 的 5E-3 TDD 矩阵；只有
item 合同、实时顺序、run/stream parity、背压、消费者断开和终态持久化测试全部通过，才能
把 5E-3 标为完成并进入 5E-4。
