# 5E-3：Live `stream()` & Parity 入口审计与设计冻结

## 1. 目标

5E-2 已经证明 `AgentRuntimeV1.run()` 可以把两个真实 Skill、AgentLoop、真实本地 RAG、
ReviewHarness、RuntimeRecorder 和最终 Trace 组合成一次同步运行。5E-3 要解决的不是再造一
套 Agent，而是让调用方在同一次执行尚未结束时看到安全的 Runtime 事件，并证明：

```text
run(request)
stream(request)
```

两者使用同一个 `_execute()`，得到同一份业务终态和同一套事件语义。

本轮明确不做：Token streaming、SSE/API、durable event log、取消、恢复、Memory、MCP、
Multi-Agent、DAG、LangGraph、Pi/Claude Agent SDK 和真实 Provider。

## 2. 初学者理解

### 2.1 `run()` 与 `stream()` 的区别

`run()` 像把文件送去打印：调用方一直等待，最后一次性拿到 `RuntimeRunResult`。

`stream()` 像查看打印进度：同一个任务仍由 Runtime 完成，但调用方可以依次收到：

```text
run_started
execution_validated
context_built
provider_call_started
provider_call_completed
...
run_completed / run_failed
最终 RuntimeRunResult
```

这里的“流”是 Runtime 事件流，不是模型逐 Token 输出。事件描述的是已经发生的安全状态，
不会携带 Prompt、报告正文、Tool 参数、Tool data、request ID 或原始异常。

### 2.2 为什么不能事后读取 Trace

最终 `runtime_trace.json` 只有在运行结束、终态准备通过、文件原子写入成功后才产生。运行中
读取它既看不到中间事件，也会把“实时执行”伪装成“结束后回放”。因此事件必须从
`RuntimeRecorder.emit()` 成功追加的时刻交付。

### 2.3 为什么终态要最后交付

成功终态遵循：

```text
prepare terminal
→ build prospective Trace
→ atomic Trace write
→ commit terminal
→ deliver terminal event
→ deliver RuntimeRunResult
```

如果 Trace 写入失败，完成候选会被取消，随后只提交并交付
`run_failed(trace_persistence_failed)`。因此调用方不会先看到 `run_completed`，再看到一个
失败结果。

## 3. 现有代码审计

### 3.1 已有执行接缝

- `AgentRuntimeV1.run()` 调用唯一 `_execute(request)`；该核心已经复用 Boundary、Context、
  AgentLoop、Harness 和 Trace Store。
- `_RecorderObserver` 把底层组件发出的 `RuntimeSignal` 交给 `RuntimeRecorder.emit()`。
- `RuntimeRecorder` 负责全局 sequence、UTC/monotonic 时间、调用配对、生命周期、event budget
  和 Usage；它是可信事件事实源。
- `ReviewHarness` 只在 Manifest/Artifact 成功持久化后发 transition、evaluation 和
  publication signal。

### 3.2 当前缺口

`RuntimeRecorder.events` 目前只保存在内存；没有 subscriber、队列或外部 event sink。因此
当前 `run()` 事件虽然在真实执行时产生，但调用方只能在结束后读最终 Trace。

终态还有一条独立的 prepare/commit 路径，不能让普通事件 sink 在 `prepare_terminal()` 时提前
发送完成事件。`_commit_failed_without_trace()` 也需要接入同一个终态交付接缝，保证失败终态
不会漏发或重复发。

## 4. 方案比较

| 方案 | 优点 | 主要问题 | 结论 |
|---|---|---|---|
| 直接 generator | 代码表面简单 | 要把深层同步 observer 变成多层 `yield`；消费者停止/异常会反向打断业务；难以保证终态提交后才交付 | 不采用 |
| 进程内 worker + 有界 `queue.Queue` | 不改 Agent/Harness 控制流；隔离生产者与消费者；可测试实时顺序和背压 | 只有进程内生命周期；慢消费者会让执行阻塞 | **V1 采用** |
| 外部消息队列 | 可跨进程、持久化、重放 | 提前引入 durable log、offset、重试、幂等、部署和运维复杂度；当前没有跨进程恢复 Bad Case | 暂不采用 |

## 5. 冻结的 V1 设计

### 5.1 唯一执行核心

把当前私有核心扩展为概念上的：

```python
_execute(request, event_sink=None) -> RuntimeRunResult
```

`run()` 传入空 sink；`stream()` 的 worker 传入进程内 sink。业务步骤只存在一份，不能为
`stream()` 复制 Agent/Harness 流程。

### 5.2 事件交付顺序

内部 sink 的顺序固定为：

1. Recorder 校验并追加非终态事件；
2. 追加成功后，把同一个 `RuntimeEvent` 投递到 stream queue；
3. 成功/失败 terminal 只有在 Trace Store 成功后 `commit_terminal()`；
4. commit 成功后投递同一个 terminal `RuntimeEvent`；
5. worker 再投递一次最终 `RuntimeRunResult`，然后发送结束标记。

因此每个 stream 恰好有一个最终 result item，且它前面已经出现与最终 Trace 完全一致的终态
event。`run()` 不增加 stream queue，也不改变旧调用方返回值。

### 5.3 Stream item 与范围

V1 对外暴露一个带判别字段的进程内 item 合同：

```text
event item  → 一个安全 RuntimeEvent
result item → 一个 RuntimeRunResult
```

不把 Prompt、Tool data、报告正文、Provider request/response、原始异常或线程对象放入 item。
最终 result 使用现有 `RuntimeRunResult`，不新增第二套业务终态模型。

### 5.4 Worker、队列和背压

- 每次 `stream()` 创建一个独立 worker 和有界 `queue.Queue`；默认容量是小的、可测试的进程内
  常量，不写入 Runtime Trace，也不改变业务 event budget。
- worker 在第一次迭代开始时启动，避免只创建 iterator 却不消费导致任务立即运行。
- queue 未满时立即投递；queue 满时 worker 阻塞等待，保持事件顺序和完整性，不丢弃已产生
  事件。V1 不用超时丢弃，也不伪造 dropped event。
- 消费者关闭 iterator 后，订阅 session 标记为 closed；worker 不再因无人消费而永久阻塞，
  后续 stream-only item 可以丢弃，但 Runtime 继续完成并保存 Trace。这是“订阅断开”，不是
  业务取消；V1 不提供 cancel/resume。

### 5.5 失败隔离

- Recorder、Trace Store 和内部 observer 属于可信执行面；其失败继续按现有
  `RuntimeObservationError`/`RuntimeRecorderError` 规则映射，影响 Runtime 结果。
- queue sink 只负责把已验证事件交给订阅者；订阅者变慢或关闭不改写 Recorder、Harness 或
  Trace 终态。
- 预期的业务/资源失败仍形成 `RuntimeRunResult`；意外的 Runtime composition exception
  由 worker 以与 `run()` 相同的异常语义传递给 stream consumer，不把原始异常写入 Trace。

### 5.6 与 Trace 的关系

stream 是实时订阅，不是日志存储。最终 Trace 仍只写一次、原子 replace、不可覆盖；stream
结束后可以用 `trace_reference` 读取和校验最终快照。中途进程崩溃时未提交事件不保证可恢复，
这属于阶段 8 的 durable execution/恢复范围。

## 6. TDD 验收顺序

### Task A：stream contract 与 queue session

- event/result item 判别合同、默认 queue capacity 和非法容量拒绝；
- iterator 首次消费才启动 worker，正常结束只产生一个 result item；
- `run()` 无 sink 的旧行为逐字段保持。

### Task B：实时顺序与终态 parity

- 用可控 Fake Provider 在中间暂停，证明第一个事件在 Provider 完成前即可被消费；
- `run()` 与 `stream()` 的 event kind/sequence/terminal reason/publication/Trace digest 一致；
- success、degraded、rejected、Boundary/Context failure 和 Agent/Evaluation failure 均覆盖。

### Task C：背压与消费者断开

- tiny queue 下不丢事件、不乱序，worker 在消费者继续读取后完成；
- 消费者关闭后 worker 不永久阻塞，Runtime 仍完成或诚实失败；
- consumer-side exception 不被计入业务失败、retry、breaker、Usage 或 publication。

### Task D：终态和持久化失败

- Trace write failure 只能收到 failed terminal + failed result，绝不收到 completed terminal；
- terminal event 只在 commit 后出现，并与 Trace 最后一项使用同一 sequence/time；
- stream 的 result reference 与实际 Trace SHA 一致。

## 7. 5E-3 完成标准

- 上述 item、worker、背压、消费者隔离和终态 parity 均有失败优先的自动化测试；
- `run()` 与 `stream()` 共用唯一 `_execute()`，没有复制 Agent/Harness 流程；
- 不增加外部消息队列、第三方 SDK、Provider/Key、Prompt、RAG 或模型调用；
- Runtime Trace 仍是最终快照，不被误称为 durable event log；
- 聚焦/相邻/完整回归、compileall、两套 RAG、治理、diff check 和 exact-SHA 公共 CI 通过；
- canonical 下一步才能切换到 `5E-4 Runtime Evaluation & Exit Review`。
