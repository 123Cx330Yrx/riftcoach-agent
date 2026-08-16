# 5E AgentRuntime V1 退出审查

## 1. 结论

5E 可以按 **`close-with-deferred-boundaries`** 关闭，但需要先让本退出审查提交通过
exact-SHA GitHub Actions。

这里的“关闭”只表示 RiftCoach 已建立并验证一个厂商无关的 AgentRuntime V1：

```text
selected Runtime request
→ Boundary / Context
→ AgentLoop + business Tool
→ ReviewHarness quality gate
→ typed terminal output
→ run() / in-process stream()
→ complete/partial/unknown Usage
→ safe atomic final Trace
```

它不表示真实模型领域质量、API/SSE、Session/Memory、MCP、Multi-Agent、持久事件、取消恢复、
前端或生产部署已经完成。

## 2. 为什么可以关闭

### 合同与事实源

- selected-only request、Signal/Event、Schema 1.0/1.1、Runtime/publication 双状态、Artifact
  reference 和 terminal 不变量有严格 Pydantic/Recorder/Trace 复读测试；
- Usage 明确区分 complete、partial、unknown、not_applicable，不把缺失 Usage 伪装为零；
- Trace Store 原子、不可覆盖、按真实 bytes 校验 SHA-256，并且不保存 Prompt、报告正文、
  Tool data、request ID 或原始异常。

### 纵向运行

- `recent-form-review` 与 `single-match-review` 通过同一个 `AgentRuntimeV1.run()`；
- Agent 与 Harness 共用一个 run-scoped observed Provider，但业务 Tool 与内部 `llm.chat`
  不混计；
- ReviewHarness 继续掌握唯一评测、修订、降级和发布权；Runtime 不复制质量门。

### 实时交付

- `run()` 与 `stream()` 共用唯一 `_execute()`；
- stream 在真实执行时交付 Event，不读取最终 Trace 伪装实时；
- terminal 只在 prospective Trace 原子写入并 commit 后交付；
- 有界 queue 保持顺序和背压，订阅关闭不取消 Runtime，worker 不永久阻塞。

### 失败和资源

- Boundary、Context、Agent/Evaluation Provider、rejected publication、observation、typed
  output、Artifact integrity 和 Trace persistence 均有安全失败路径；
- event budget 在 Provider/Tool 副作用前按可信最坏上界拒绝；
- runtime status 与 publication status 分开，Agent 失败后安全 fallback 可形成
  `completed + degraded`，不会被误写成 Runtime failure 或 unsafe publish。

## 3. 证据

| 层级 | 证据 |
|---|---|
| 5E-1 | `d891184` / Actions `31942483874` |
| 5E-2 Task A | `2e78c96` / Actions `31947625293` |
| 5E-2 Task B | `28bd910` / Actions `31952026988` |
| 5E-2 Task C | `8b69c9b` / Actions `31957712118` |
| 5E-2 Task D | `d49508e` / Actions `31959646589`；`747 passed, 110 subtests passed` |
| 5E-3 | `80b76a1` / Actions `31960987333`；stream 聚焦 15，完整 `762 passed, 110 subtests passed` |
| 5E-4 本地审查 | Runtime 聚焦 128；完整 `762 passed, 110 subtests passed`；compileall、RAG、治理、diff 通过 |

逐条映射见 `docs/plans/2026-08-17-agent-runtime-v1-exit-matrix.md`。

## 4. 保留的限制

| 限制 | 正确归属 |
|---|---|
| 当前无真实 Provider 领域质量准入 | 后续新鲜 Provider 采用门；不阻塞 Runtime V1 |
| `stream()` 不是 Token streaming 或 SSE | 5P/阶段 6 API 消费层 |
| Trace 不是 durable event log | 阶段 8 或出现恢复 Bad Case 后 |
| 没有 cancel/resume、Session、Memory、SQL | 阶段 6/8 |
| 没有标准 MCP/Meta | 阶段 7 |
| 没有 Multi-Agent/DAG | 阶段 8 Advanced，仍需 Bad Case |
| 没有生产 p50/p95、真实成本与 SLO | 5P/阶段 6 出现真实 API 消费者后 |
| 没有 LangGraph/Pi/Claude SDK 采用结论 | 5F 独立对照实验 |

这些限制是诚实边界，不是把 5E 强行判失败的理由；同样也不能在简历或面试中省略。

## 5. 为什么不继续补功能

5E 的目标是建立 Runtime V1 合同和厂商无关控制面。继续在退出审查里加入 FastAPI、真实模型、
Memory、MCP 或第三方 SDK，会同时改变消费层、数据层和运行时，使失败无法归因，并违反已冻结的
5P/5F/阶段 6-8 顺序。

因此本轮没有产品代码缺口需要修补；正确动作是公开验证退出裁决，然后进入 5P 的早期产品
纵向切片入口设计。

## 6. 面试表述

> 我先用受限 Agent Loop 和唯一质量门跑通两个领域 Skill，再抽出薄 AgentRuntime。底层组件只
> 发安全 Signal，中央 Recorder 统一事件顺序、Usage 和 Trace；同步 `run()` 与进程内
> `stream()` 共用一个执行核心。为避免 Trace 落盘失败后先发成功终态，我使用 prepare、
> prospective Trace、atomic write、commit 的两阶段 terminal。Runtime V1 仍不声称拥有 SSE、
> 持久恢复或真实模型领域质量，这些被明确放到后续独立阶段和采用门。

## 7. 唯一后续

本退出审查提交通过 exact-SHA 公共 CI 后：

```text
5E-4 complete
→ 5P-entry-design
```

根据 RQ-039，该箭头只表示 canonical 状态交接：完成 5E-4 公共闭环和最终状态回写后立即
停止，不实际开展 5P 入口设计。不得跳到 5F、阶段 6，也不得在状态交接时读取 Key 或调用
真实 Provider；后续等待用户再次明确“继续”。
