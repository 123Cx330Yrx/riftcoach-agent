# 5E-1：Runtime Contract、Usage 与 Trace Store 实施计划

## 1. 目标

在不接入 AgentLoop、ReviewHarness 或真实 Provider 的前提下，建立 AgentRuntime V1 的
纯本地地基：严格合同、事件 Recorder、完整性明确的 Usage 汇总和不可覆盖的原子最终
Trace Store。

本批完成后可以证明“未来各组件有同一套安全语言和存储语义”，但还不能声称
`AgentRuntimeV1.run()` 或 `stream()` 已可执行复盘。

## 2. 实现边界

新增：

```text
app/runtime/
├── __init__.py       # 保持轻量，避免未来 observer 循环导入
├── signals.py        # 低依赖、强类型的安全运行信号
├── models.py         # request/result/event/usage/trace 合同
├── recorder.py       # 序列、时钟、事件预算、运行不变量和 Usage 汇总
└── store.py          # runtime_trace.json 原子、不可变存储
```

不修改：

- `app/agent/loop.py`；
- `app/harness/runtime.py`；
- `app/skills/review_executor.py`；
- Provider/Prompt/模型配置；
- API、前端、SSE、Session 或 Memory。

## 3. 合同原则

### 3.1 Signal 与 Event 分离

Signal 只表达安全语义，例如：

```text
ProviderCallStarted(provider, model, ordinal, iteration)
```

Recorder 才补上：

```text
run_id, sequence, occurred_at_utc, elapsed_ms
```

底层组件因此不负责全局顺序、时钟和持久化。

### 3.2 强类型 allowlist

每一种 Signal 都是 `extra="forbid"` 的冻结 Pydantic 模型。不存在自由 `metadata: dict`，
所以 Prompt、Tool arguments、响应正文、异常文本或 request ID 不能通过“顺手加字段”
混入 Event/Trace。

### 3.3 Runtime 与 publication 双状态

Runtime 只有 `completed/failed`；Harness publication 单独为
`published/degraded/rejected/null`。Harness 前失败时 publication 为 null；模型失败但
确定性 fallback 成功时可以是 Runtime completed + publication degraded。

### 3.4 Usage 不把未知当零

Recorder 根据 Provider start/complete/fail 信号形成：

| 场景 | token observation | total tokens |
|---|---|---|
| 没有 Provider 调用 | `not_applicable` | 0/0 |
| 所有调用都有规范化 Usage | `complete` | 精确总数 |
| 部分调用有 Usage | `partial` | total 为 null；另存 observed lower bound |
| 已调用但一个 Usage 都没有 | `unknown` | total 为 null |

成本只有在 Token complete 且注入版本化定价表时才计算；否则为 null。

### 3.5 最终 Trace 是审计快照

Store 写入：

```text
<runs_root>/<run_id>/runtime_trace.json
```

写入采用同目录临时文件、flush/fsync 和原子 replace。第一次成功后路径不可覆盖；读取时
按返回的 SHA-256 reference 验证内容。它不是逐事件 durable log，也不能在进程崩溃后
恢复尚未提交的事件。

## 4. TDD 任务

### Task 1：合同与安全红灯

输出：`tests/test_runtime_models.py`

先验证：

- request 包装真实 `SkillExecutionRequest`，run_id 必须一致；
- Signal/Event/Trace 全部拒绝额外字段和非法枚举；
- Artifact path 必须为安全 POSIX 相对路径；
- Trace 必须从 sequence 1 开始、单调递增、恰好一个 terminal；
- Runtime/publication 状态与最后事件一致；
- raw prompt、response、tool data、request ID 不能成为 schema 字段。

红灯原因应为 `app.runtime` 尚不存在，而不是测试自身语法错误。

### Task 2：Recorder 与 Usage 红灯/绿灯

输出：`tests/test_runtime_recorder.py`、`app/runtime/signals.py`、
`app/runtime/models.py`、`app/runtime/recorder.py`

验证：

- 首事件只能是 `run_started`；
- sequence、UTC 时间和 monotonic elapsed 可注入并可复现；
- Provider/Tool ordinal 必须 start 后才能 complete/fail，不能重复关闭；
- terminal 后不能再发事件，open call 不能直接 terminal；
- event budget 到达上限前 fail closed；
- complete/partial/unknown/not_applicable Usage 精确；
- 版本化 Decimal 定价只在 complete 时形成 cost。

### Task 3：Trace Store 红灯/绿灯

输出：`tests/test_runtime_store.py`、`app/runtime/store.py`

验证：

- Harness 目录不存在时也能写 Trace；
- JSON 可由严格 `RuntimeTrace` 复读；
- reference SHA 与真实字节一致；
- 重复写入被拒绝且旧文件不变；
- 错误 run_id、篡改内容、路径逃逸和序列化失败 fail closed；
- 临时文件在成功/失败后清理。

## 5. 验证顺序

```text
1. 新增测试并确认红灯
2. 最小实现使聚焦测试变绿
3. 运行 Runtime 聚焦测试
4. 运行 Skill/Agent/Harness 相邻回归
5. 运行完整 pytest
6. 两套 RAG、compileall、安全边界、Harness dry-run
7. stale-state scan、governance、git diff --check
8. 持久化同步、提交、推送、exact-SHA CI
```

## 6. 完成标准

只有同时满足以下条件，5E-1 才能完成：

- 设计中的严格合同、Recorder、Usage 与 Store 均有实现；
- 所有成功和失败不变量都有测试；
- 没有修改 AgentLoop/Harness observer 或实现完整 Runtime；
- 没有 Key、Provider I/O、模型/Prompt 变化或新依赖；
- 全部门禁与 exact-SHA 公共 CI 通过；
- canonical 下一步准确切换为 5E-2，而不是 5P/5F。
