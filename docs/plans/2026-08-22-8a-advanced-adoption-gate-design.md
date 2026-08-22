# 8A Advanced Adoption Gate 设计

## 1. 初学者心智模型

### 真实问题

Multi-Agent 会增加模型调用、Context、合并逻辑、失败状态和调试面。若只是让两个独立工具同时跑，
普通受限并行就可能足够；若真正价值来自权限和上下文隔离，才有理由引入多个 Agent。

8A 因而不是“实现 Multi-Agent”，而是建立一扇可执行的门：证据完整的候选可以进入 8B，缺少
Bad Case、公平对照、安全边界或停止条件的候选必须 deferred。

### 底层原则

- 并发是调度方式，Multi-Agent 是职责/Context/权限/失败边界；二者不能混称；
- Harness 是质量控制面，不是 Review Agent；
- 恢复、lease 和 durable event 是 8C Core，不是 Advanced 的简历装饰；
- 采用门验证“实验设计是否有资格”，8B 才验证“候选是否有收益”。

### 本检查点做与不做

做：源码/参考快照审计、Bad Case、候选矩阵、case set、同切片比较合同、硬门、收益门、停止线、
离线 deterministic evaluator、ADR、八维证据。

不做：启动 Agent、运行并行、调用外部服务、安装框架、修改产品 Runtime、创建 migration 或前端。

## 2. 事实接缝

8A 绑定产品 SHA `c5385120f6f32cbfc93a149be59658ea731ec581`。入口审计时的 Git blob 身份为：

| 接缝 | Git blob | 能证明什么 |
|---|---|---|
| `app/agent/loop.py` | `d20ec61f...` | ToolCall 整批预检后按序执行 |
| `app/agent/context.py` | `e9a7097b...` | trust-typed Context 与 data-only section |
| `app/meta/context.py` | `b211d731...` | partial MetaEvidence 只作 optional user data |
| `app/runtime/runtime.py` | `e7532273...` | 单 Skill、单同步执行核心与进程内 stream |
| `app/harness/runtime.py` | `f9684335...` | Harness 唯一发布控制流 |

参考快照只作方案检查：AGI-Saber Python 归档 SHA-256 `5A693A...149` 可看到 role registry、
topological levels、并行线程和 snapshot；Sea 归档 SHA-256 `6903A0...5F0` 可看到 Artifact、Ready 条件、
Scheduler 和 recovery。两者均缺 Git 元数据，本检查点不执行其代码，也不把其 README 能力当作 RiftCoach 事实。

## 3. Bad Case 与路由

| ID | 证据等级 | 问题 | 进入哪里 |
|---|---|---|---|
| BC-8A-01 | observed | 多 ToolCall 当前顺序执行，独立 evidence latency 相加 | 8B 并行 comparator |
| BC-8A-02 | safety hypothesis | 外部 Meta 与知识最终进入 Coach Context，需要验证污染/失败隔离是否有增量价值 | 8B Multi-Agent candidate |
| BC-8A-03 | observed | running task 无自动 lease/recovery | 8C Core，禁止拿来支撑 8B |

BC-8A-02 明确是压力假设，不是“项目发生过泄漏”。8B 如果发现 strict Adapter + typed Artifact 已足够，
Multi-Agent 应 reject。

## 4. 冻结实验结构

```text
匿名 Player Summary + deterministic report
              │
              ├─ knowledge fixture ─┐
              └─ OP.GG Meta fixture ├─> typed evidence artifacts
                                    │
                         same Coach/Harness contract
                                    │
                         body-free comparison result
```

三条路径只能改变 evidence 获取/Context 隔离方式。输入 fixture、工具结果、Context ceiling、Harness policy、
发布阈值、零重试和零真实 I/O 不变。质量差异不能用换 Prompt、换模型、换工具输出或调 Harness 阈值制造。

角色隔离候选的权限：

| Role | 可见输入 | 工具 | 可发布 |
|---|---|---|---|
| Knowledge | 确定性事实、知识 query | `knowledge.search` | 否 |
| Meta | position/region/queue allowlist | `opgg.lane_meta` fixture | 否 |
| Coach | 两个 typed Artifact、用户目标 | 无 | 否 |
| Harness（非 Agent） | 草稿、事实、证据 | 固定 Evaluator/Reviser ports | 唯一发布权 |

## 5. 数据与控制流

`advanced_adoption_cases_v1.json` 保存匿名 synthetic development/holdout case 元数据；
`advanced_adoption_gate_v1.json` 保存候选、权限、比较身份、预算、硬门、收益门和 case-set SHA。

```text
load case set → canonical SHA-256
               ↓ exact match
load gate → Pydantic strict validation
          → validate baseline/comparator/candidate identity
          → validate role/tool/publication boundaries
          → validate metric/stop/holdout rules
          → candidate/deferred decisions + gate digest
```

Evaluator 只检查实验是否设计完整，不预测性能，也不运行候选。错误只返回稳定 reason code，不把原始
fixture/body/路径写进公开 decision。

## 6. 指标与停止条件

硬门：`unauthorized_tool_calls`、`cross_role_context_leaks`、`unprovenanced_evidence`、
`unsafe_publications`、`terminal_identity_mismatches` 必须全为 0。

收益/预算门：Harness decision match 和 safe-degraded rate 均为 1.0；Token ratio ≤1.5；额外 Provider
调用 ≤2；延迟改善 ≥20% 或证明分支失败隔离有增量收益。

立即停止：case/gate digest 漂移、真实 I/O、重试、holdout 重跑、角色工具重叠、Coach 持有工具、任何
Agent 发布、Harness/Prompt/Context ceiling 不同、硬门失败、成本越界或没有相对普通并行的增量收益。

## 7. 测试矩阵

- happy path：一个 primary candidate、一个 comparator、DAG/Agentic Retrieval deferred；
- identity：case-set digest、baseline/slice/Harness/Context/budget 精确一致；
- permission：重复工具权限、Coach 工具权限、Agent publication fail closed；
- dataset：development/holdout 均存在，holdout `calibration_excluded=true` 且 max executions=1；
- stop：零真实 I/O、零重试、完整硬门、收益阈值和停止条件；
- output：稳定 digest、固定 reason code、body-free decision；
- regression：Agent/Context/Meta/Harness/Runtime 相邻测试与完整项目门禁。

## 8. 限制与面试表述

8A 完成后只能说：“我用可执行采用门把角色隔离 Multi-Agent 选为 8B 候选，并用普通受限并行作
必要 comparator。”不能说已经实现 Multi-Agent、测得 20% 提速、通过 holdout、采用 DAG/框架或完成恢复。
