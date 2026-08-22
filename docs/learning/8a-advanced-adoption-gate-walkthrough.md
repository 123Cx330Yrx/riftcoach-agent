# 8A Advanced Adoption Gate 实现后 walkthrough

## 1. 问题与原理

8A 解决的不是“如何写多个 Agent”，而是“什么证据足以允许 Multi-Agent 进入实验”。普通并行只改变
调度；Multi-Agent 还改变 Context、工具权限、失败边界和调用成本。若不放一个普通并行 comparator，
未来测到的提速会被错误归因给 Multi-Agent。

因此本门采用：真实接缝/收益假设 → 同切片身份 → 强制安全门 → 收益/成本门 → candidate/deferred。
安全项不能用平均分抵消，结构性缺口不能靠真实模型 demo 追绿。

## 2. 设计与实际实现

ADR-0052 允许 `role-isolated-multi-agent-v1` 和 `bounded-parallel-evidence-v1` 进入 8B；串行 Runtime
保留为 baseline。通用 DAG/第三方 Runtime 因 durable core 尚未建立且无框架特有 Bad Case deferred；
Agentic Retrieval 因当前 RAG 没有相应质量 Bad Case deferred。

实现只新增 `app/evaluation/stage8_adoption/`：strict Pydantic models、限长 JSON loader、case-set exact
SHA binding、候选/角色/工具/发布/预算/holdout/停止线验证，以及 body-free decision。它没有线程、Agent、
Provider、MCP Client、网络、Key、数据库或产品 composition。

## 3. 代码地图

| 文件 | 职责 |
|---|---|
| `app/evaluation/stage8_adoption/models.py` | case、候选、权限、比较合同、decision 的 immutable strict model |
| `app/evaluation/stage8_adoption/gate.py` | bounded load、SHA/语义门、candidate/deferred 裁决与稳定 digest |
| `app/evaluation/stage8_adoption/__init__.py` | 窄公共 API |
| `data/evaluation/stage8/advanced_adoption_cases_v1.json` | 3 development + 3 calibration-excluded holdout synthetic cases |
| `data/evaluation/stage8/advanced_adoption_gate_v1.json` | baseline/comparator/candidate、权限、预算、硬门和停止线 |
| `tests/test_stage8_adoption_gate.py` | happy path、identity、I/O、holdout、权限、发布、停止线负例 |

## 4. 数据与控制流

```text
case-set bytes ──SHA-256──┐
                         ├─ exact binding → strict semantic gate
gate JSON ────────────────┘                   │
                                             ├─ baseline
                                             ├─ candidate(s)
                                             └─ deferred + reason codes
```

Gate decision 固定为：

- baseline：`single-runtime-serial-v1`；
- comparator：`bounded-parallel-evidence-v1`；
- primary：`role-isolated-multi-agent-v1`；
- deferred：`third-party-dag-runtime-v1`、`agentic-retrieval-v1`；
- gate digest：`88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；
- case-set SHA：`d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e`。

Decision 不含 scenario、fixture body、Prompt、本地绝对路径或原始错误。

## 5. 验证证据

TDD 首次运行因 `app.evaluation.stage8_adoption` 不存在，在 collection 阶段红灯。最小实现后聚焦
`14 passed`；提交前 strict-contract 复核又用 6 个负例证明重复 JSON key、baseline kind 漂移、未登记
active candidate 和角色/工具/Context 漂移原本可穿过，最小补强后聚焦为 `20 passed`。cached diff
复核再以 3 个负例锁定唯一 baseline 及串行/普通并行 exact role contract，最终聚焦为 `23 passed`。与
AgentLoop/Runtime/Context/OP.GG Meta/Harness 相邻回归为 `129 passed`。

本地完整 pytest 为 `1600 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 只表示本机
无 PostgreSQL/Docker/Linux 条件，不冒充真库或 package 成功。RAG development/independent holdout
Recall/MRR/nDCG 均 `1.0`、FPR `0.0`，holdout abstention/citation 均 `1.0`；Harness dry-run 为
`published`/0 revisions。compileall、pip、6 个 YAML、SDK/Secret/tracked-data、governance 和 diff 门均
通过；exact-SHA 公共三 job 前 coverage 保持 `planned`。

## 6. 安全运行方法

```powershell
cd D:\riftcoach-agent
.\.venv\Scripts\python.exe -m pytest tests/test_stage8_adoption_gate.py -q
.\.venv\Scripts\python.exe -c "from app.evaluation.stage8_adoption import load_adoption_gate,evaluate_adoption_gate; print(evaluate_adoption_gate(load_adoption_gate('data/evaluation/stage8/advanced_adoption_gate_v1.json','data/evaluation/stage8/advanced_adoption_cases_v1.json')).model_dump_json(indent=2))"
```

这两条命令只读版本化 JSON 并运行本地 Python，不读取 `.env`，不调用 Riot、OP.GG、Provider 或模型。

## 7. 失败、安全与范围边界

- case SHA、source product、slice、baseline、fixture、Harness 或 Context identity 漂移时 fail closed；
- external I/O、重试、holdout 超过一次、结果覆盖直接拒绝；
- 角色工具权限重叠、Coach 持有工具、任何 Agent 可发布、Multi-Agent 共用 Context 直接拒绝；
- Harness 仍是唯一发布权，BC-8A-02 是安全压力假设，不冒充真实泄漏事故；
- 8A 没有实现 8B 候选，20%/1.5x/+2 是未来工程门，不是测得结果；
- DAG/Agentic Retrieval 是 deferred，不是永久拒绝。

## 8. 面试准确表述

可以说：

> 我先把“并行”和“Multi-Agent”拆开，用当前 AgentLoop 顺序 ToolCall 与 external Meta Context 作为
> 可复核接缝，冻结串行 baseline、普通受限并行 comparator 和角色隔离 Multi-Agent candidate。
> 离线采用门强制同输入/工具/Harness，禁止角色权限重叠和 Agent 发布，并把 DAG 与 Agentic Retrieval
> 在缺少 Bad Case 时明确 deferred。这样 8B 即使 reject，也是一条可验证的工程结论。

不能说：“已经实现或采用 Multi-Agent/DAG”“已经提速 20%”“跑过 heldout/真实 OP.GG/真实模型”或
“发现了真实跨角色泄漏”。
