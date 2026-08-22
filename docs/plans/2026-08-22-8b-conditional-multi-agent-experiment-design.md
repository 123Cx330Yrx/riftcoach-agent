# 8B Conditional Multi-Agent Experiment 设计

## 1. 初学者心智模型

### 这次真正要回答什么

“多个 Agent”不是把同一段代码复制三份。它意味着不同角色拥有不同 Context、工具权限、失败边界，
最后再把各自产出的可验证 Artifact 合并。这样可能更安全，也可能只是更贵、更难调试。

8B 因而只回答一个窄问题：在 RiftCoach 的近期复盘证据获取切片中，角色隔离 Multi-Agent 相比
“同一 Runtime 串行获取证据”和“普通受限并行获取证据”，是否有足够的额外收益值得采用。

### 三个容易混淆的概念

- 串行：Knowledge 完成后才做 Meta，等待时间相加；
- 普通并行：两个固定函数同时执行，但仍属于同一控制器；
- Multi-Agent：Knowledge、Meta、Coach 具有各自独立 Context 和权限，靠 typed Artifact 交接。

`ReviewHarness` 不是第四个 Agent。它仍是确定性的质量控制面和唯一发布者，三个执行角色都没有发布权。

### 本检查点做与不做

做：本地 Scripted/Fake 角色、两路 fixture 工具、三路公平比较、typed/digest-bound Artifact、真实
`ReviewHarness`、development、一次 calibration-excluded holdout、成本/延迟/失败隔离指标和最终 ADR。

不做：真实模型质量测试、真实 Riot/OP.GG/Provider I/O、Key 读取、生产 Runtime 改造、LangGraph/DAG、
Agentic Retrieval、lease/recovery、SSE、前端或部署。

## 2. 方案比较与裁决

| 方案 | 优点 | 主要风险 | 8B 用法 |
|---|---|---|---|
| 只写数学模拟器 | 简单、完全确定 | 不能证明真实 Harness/权限/Artifact 接线 | 拒绝 |
| 直接接真实 LLM/MCP | 更像线上 | 模型随机性、网络和费用会污染架构比较 | 拒绝 |
| evaluation-only Scripted 角色 + fixture 工具 + 真实 Harness | 变量受控，又能执行真实边界 | 只证明编排/隔离，不证明模型质量 | 采用 |
| 修改产品 `AgentRuntimeV1` | 可直接上线 | 在采用结论前先改变生产架构，因果倒置 | 拒绝 |

采用第三种。并行用最多两个 worker 的本地 executor；Multi-Agent 额外要求独立 Context digest、exact
role/tool allowlist 和 Coach 零工具。所有正文只在单次本地进程和临时 Harness run 中存在，持久结果仅含
身份、计数、digest、reason code 和聚合指标。

## 3. 冻结身份与公平性

- adoption gate digest：`88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；
- case-set SHA-256：`d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e`；
- baseline：`single-runtime-serial-v1`；
- comparator：`bounded-parallel-evidence-v1`；
- candidate：`role-isolated-multi-agent-v1`；
- 输入：既有 demo Player Summary/确定性报告的两个冻结 SHA；
- 工具：`knowledge-search-fixture-v1` 与 `opgg-lane-meta-fixture-v1`；
- Harness：score 85、revision 0、允许确定性 fallback；
- external I/O/retry：均为 0；holdout 最多一次且不得覆盖。

三路只允许改变 evidence acquisition 和 Context isolation。案例、fixture body、Coach 草稿合同、Evaluator、
Harness policy、Token/调用模型和判分逻辑完全相同。不得为了让 Multi-Agent 通过而换 Prompt、模型或阈值。

## 4. 类型与权限

每个 evidence 分支先形成内存中的 typed body，再产生公开安全引用：

```text
EvidenceArtifactReference
  artifact_kind
  producer_role
  tool_name
  payload_sha256
  provenance_sha256
  context_sha256
```

Coach 在消费前重新计算 payload/provenance digest；任一不一致都在 Harness 前失败。公开结果不保存
knowledge/meta 正文、Player Summary、确定性报告、Prompt、用户文本、绝对路径、线程信息或原始异常。

权限精确冻结为：

| Role | 工具 | Context | 发布权 |
|---|---|---|---|
| Knowledge Agent | `knowledge.search` | deterministic facts + knowledge query | 无 |
| Meta Agent | `opgg.lane_meta` | position/region/queue allowlist | 无 |
| Coach Agent | 无 | deterministic facts + 两个 digest-bound Artifact + user goal | 无 |
| ReviewHarness | Evaluator/Reviser ports | 固定事实/草稿/evidence | 唯一发布权 |

普通并行仍对每个 branch 做 exact expected-tool 检查，因此“Multi-Agent 才会拒绝越权”不能被人为制造成收益。

## 5. 数据与控制流

```text
frozen case + frozen fixtures
          │
          ├─ serial acquisition ───────────────┐
          ├─ bounded parallel acquisition ────┼─ typed/digest check
          └─ isolated role agents ────────────┘          │
                                                        v
                                            same CoachDraft contract
                                                        │
                                                        v
                                                real ReviewHarness
                                                        │
                                                        v
                                       body-free case/aggregate metrics
```

正常案例由 Harness 发布；Meta schema drift、instruction payload 或 timeout 保留合法 Knowledge 引用，
但不让残缺证据生成未审草稿，Harness 只发布确定性 fallback；cross-role tool probe 在工具调用前终止，
不会把一次被阻止的尝试计成真实越权调用。

## 6. 指标、模型与最终裁决

真实墙钟不用于门禁，因为线程调度噪声会让小 fixture 失真。每个 case 使用 8A 冻结的 Knowledge/Meta
latency units：串行为两者相加再加固定 Coach/Harness 单位；并行取两者最大值再加各自固定编排开销。

Scripted Provider Usage 同样是实验模型，不冒充真实 tokenizer：baseline 每例 1 call/1000 units，普通并行
1 call/1050 units，Multi-Agent 最多 3 calls/1450 units。它准确回答预算合同是否可达，但不能推断线上费用。

每条策略必须满足：

- Harness/expected terminal match rate = 1.0；
- safe degraded rate = 1.0；
- 八个硬门计数全为 0；
- candidate Token ratio ≤1.5，单例 Provider calls 最多 baseline +2；
- candidate latency 相对 baseline 改善 ≥20%，或有相对普通并行的增量失败隔离；
- 即使前项通过，若相对普通并行没有增量收益，Multi-Agent 仍 reject。

最终只能是 `adopt`、`partial_adopt` 或 `reject`。development 可以帮助修实现；holdout 不得反向改规则、
重跑或追绿。

## 7. 一次性 holdout 生命周期

1. 先完成 runner、strict validator、development 测试和 no-I/O preflight；
2. 独立提交并取得该 exact SHA 的三个公共 CI job 成功；
3. 工作树/HEAD/origin 精确一致后运行 development，生成 `tmp/` 下不可覆盖 admission evidence；
4. holdout preflight 复读 development result，验证 code SHA = public CI SHA、gate/case/策略身份和全部门；
5. 用 exclusive create 预留正式结果路径；崩溃也留下 sentinel，禁止把同一考卷再跑一次；
6. 唯一执行三个 holdout cases，写 body-free strict JSON；
7. 结果、ADR、walkthrough 和 canonical 状态独立提交，再完成 exact-SHA 三 job。

## 8. 测试矩阵

- identity：gate/case/input/strategy/code/public-CI SHA 漂移全部 fail closed；
- permission：跨角色工具、Coach 工具、Agent 发布、共享 Context、Artifact tamper；
- execution：串行顺序、最多双 worker 并行、独立 role Context、相同 Harness terminal；
- failure：schema drift、instruction payload、timeout、tool probe、Harness fallback；
- metrics：decision/safe-degraded、latency、Token、calls、failure isolation、no incremental benefit；
- lifecycle：development admission、holdout 确认、exclusive reserve、重跑/覆盖拒绝；
- output：strict/body-free、稳定 reason code、无正文/路径/原始异常；
- regression：Harness/Agent Context/Meta/Runtime/8A gate 与完整项目门禁。

## 9. 限制与面试边界

8B 完成后可以说“我做了一个同切片、三路、一次性 holdout 的受控架构实验，并根据证据采用或拒绝
Multi-Agent”。不能说“真实多个模型在线协作”“真实 OP.GG 并行提速”“已经生产部署”“实现 DAG/恢复”，
也不能把 Scripted Token/latency units 当成生产 p95 或费用。
