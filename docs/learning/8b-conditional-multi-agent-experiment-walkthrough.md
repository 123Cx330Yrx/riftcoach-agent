# 8B Conditional Multi-Agent Experiment walkthrough

> 当前状态：完整/公共闭环。唯一 holdout 已执行并形成 reject 裁决，result/ADR/evidence 已由
> `783a329` / Actions `32572610725` exact-SHA 公共成功；本结果不得覆盖或重跑。

## 1. 问题与原理

8B 要判断的是“角色隔离 Multi-Agent 是否比普通并行更值得”，不是演示三个聊天机器人。普通并行已经能把
两个独立等待从相加变成取最大值；Multi-Agent 只有在独立 Context、工具权限或失败隔离带来额外结果时，
才足以补偿更多调用、Token 和维护面。

因此三路必须共享输入、fixture、Coach 输出、Evaluator 和唯一 `ReviewHarness`。只允许改变 evidence 获取
方式和 Context 隔离方式。真实 Provider/OP.GG 会引入随机性、网络与费用，反而无法解释收益来源，所以本门
使用 Scripted Usage 与本地 fixture，并明确不测试模型质量。

## 2. 设计与当前实现

实现位于独立的 `app/evaluation/stage8_experiment/`，没有修改 `AgentRuntimeV1`、Harness、MCP、Meta 或产品
composition。串行路径按 Knowledge→Meta 获取；普通并行和角色隔离路径都使用最多两个 worker。区别是后者
持有三份 exact role Context，Knowledge/Meta 各只有一个工具，Coach 工具为空。

证据正文只在内存和 ignored Harness run 中存在。每个分支输出 `ArtifactReference`：payload、provenance、
Context 都有 SHA-256。Coach 前重新计算 payload/provenance；公开结果只保留 digest、角色、工具、终态、计数
和 reason code。

跨角色工具探测采用和现有 AgentLoop 一致的整批原子预检：如果 Meta branch 请求 `knowledge.search`，两个
分支都在任何工具副作用前停止。被阻止的尝试不是 `unauthorized_tool_call`；硬门计数仍为 0。

## 3. 代码地图

| 文件 | 责任 |
|---|---|
| `app/evaluation/stage8_experiment/models.py` | strict/body-free Artifact、角色、case、metrics、result、admission 合同 |
| `app/evaluation/stage8_experiment/runner.py` | 三路 acquisition、原子权限预检、digest binding、真实 Harness、聚合与 verdict |
| `app/evaluation/stage8_experiment/lifecycle.py` | bounded strict loader、语义复算、development admission、exclusive output |
| `scripts/run_stage8_multi_agent_experiment.py` | clean/exact-SHA CLI、允许目录、holdout 前预留，不读取 `.env` |
| `tests/test_stage8_multi_agent_experiment.py` | development 三路、故障、权限、指标、body-free 与 synthetic holdout-path |
| `tests/test_stage8_multi_agent_experiment_lifecycle.py` | immutable output、SHA admission、duplicate/tamper/metrics/role 漂移 |
| `tests/test_run_stage8_multi_agent_experiment_cli.py` | exact SHA、confirmation、路径逃逸与不可覆盖 CLI |

## 4. 数据与控制流

```text
8A gate/case SHA + demo fixture SHA + code SHA
                    │
                    ├─ serial branch acquisition
                    ├─ bounded parallel acquisition
                    └─ isolated role acquisition
                              │
                    typed body + body-free digest reference
                              │ verify again
                              v
                    same CoachDraft / KnowledgeEvidence
                              │
                              v
                       real ReviewHarness
                              │
                              v
                case results → recomputed aggregate/verdict
```

正常 case 发布 Coach draft；Meta schema/instruction/timeout 保留合法 Knowledge 引用，但 DraftPreparer fail
closed，Harness 只发布确定性 fallback；tool probe 在 Harness/工具前形成 experiment-level `failed`。结果
loader 会重算 experiment ID、exact role/tool、Artifact→Context、固定 Token/call、metrics 和 verdict，手改
一个字段不能改变裁决。

## 5. 当前验证证据

- 首次聚焦执行：`ModuleNotFoundError: app.evaluation.stage8_experiment`，两个文件 collection 红灯；
- 最小实现后：`14 passed`；
- CLI、预期 holdout identity、语义复算和原子 tool preflight 补强后：`22 passed`；
- synthetic holdout-path 使用重标记的 development 副本，覆盖 timeout/tool-probe/正式 runner 分支，明确没有
  读取或执行三个 calibration-excluded holdout rows；
- 8A/Harness/store/observation/Context/AgentLoop/OP.GG Meta/AgentRuntime 相邻集合：
  `168 passed, 12 subtests passed`。

完整 pytest 为 `1622 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 仅表示本机无
PostgreSQL/Docker/Linux 条件。两套 RAG 的 Recall/MRR/nDCG 均 1.0、FPR 0，independent holdout 的
abstention/citation 均 1.0；Harness dry-run `published`/0 revisions。compileall、pip、39 YAML、Harness SDK、
tracked Secret/run-data、governance 和 diff check 均通过。exact-SHA 公共 CI 仍待本批后续记录。以上测试均
未读取 Key、调用 Riot/OP.GG/Provider 或执行正式 holdout。

实现提交 `180bc8b452603572d010b6e25b14ed71f6470ce7` / Actions `32572085065` 随后完成
exact-SHA 公共闭环：pytest `1623 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
`164 passed, 1 warning`、migration/head 一致；Linux package schema 1.6、外部调用 0。

同一 clean SHA 的 development 只执行一次，experiment ID 为
`73a0cc181f974ace2b1350512ab8e5937f63a24ae5715495e37438b0e345e0d1`，裁决
`eligible_for_holdout`。随后正式 holdout 唯一执行一次：

| Strategy | Latency units | 改善 | Token ratio | Extra calls/例 | Isolation |
|---|---:|---:|---:|---:|---:|
| Serial | 765 | 0% | 1.00 | 0 | 1.0 |
| Bounded parallel | 590 | 22.88% | 1.05 | 0 | 1.0 |
| Role-isolated Multi-Agent | 620 | 18.95% | 1.45 | 2 | 1.0 |

三路 decision match/safe degraded 均 1.0、hard gates 均 0。Multi-Agent 低于 20% 延迟门且没有相对普通
并行的隔离增益，最终 `reject_multi_agent`。experiment ID 为
`0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494`，结果 SHA-256 为
`94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8`。结果 validator/body-free scan 通过；
结果归档提交 `783a329537682b5413d74af4cc3e1ac818f75da2` / Actions `32572610725` 随后完成
exact-SHA 公共闭环：pytest `1626 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
`164 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6、外部调用 0。8B coverage complete。

归档提交前新增 3 个冻结结果回归，聚焦总数变为 `25 passed`；完整本地 pytest 为
`1625 passed, 117 skipped, 1 warning, 127 subtests passed`。两套 RAG、Harness、compileall、pip、39 YAML、
SDK/Secret/tracked-data、result body-free、governance 与 diff 门再次通过。

## 6. 安全运行手册

holdout 前只允许运行测试。实现提交取得 exact-SHA 公共成功且工作树干净后，先运行 development：

```powershell
.\.venv\Scripts\python.exe scripts\run_stage8_multi_agent_experiment.py `
  --split development `
  --public-ci-sha <IMPLEMENTATION_SHA> `
  --confirm-public-ci-success
```

它在 `tmp/stage8/` 生成不可覆盖 development admission。复读通过后才可执行一次：

```powershell
.\.venv\Scripts\python.exe scripts\run_stage8_multi_agent_experiment.py `
  --split holdout `
  --public-ci-sha <IMPLEMENTATION_SHA> `
  --confirm-public-ci-success `
  --confirm-holdout
```

CLI 在运行 case 前先以 `x` 模式预留正式 JSON；本次结果已存在，以上两条命令现在都属于历史 runbook，
不得再次执行。不要删除/覆盖结果追绿，不要把 `tmp/` development 结果提交，不要在公共 CI 中运行 holdout。

## 7. 失败、安全与范围边界

- gate/case/input/code/public-CI/admission/experiment identity 任一漂移 fail closed；
- 角色工具或发布权扩大、Artifact→Context 不匹配、metrics/verdict 被改写 fail closed；
- 八个硬门任一非零不生成合法 record；
- `external_io_calls=0` 指没有网络/Provider，不表示没有本地 fixture、线程或文件 I/O；
- Scripted Token 与 latency units 只用于公平预算模型，不是 tokenizer、费用、p95 或线上 SLA；
- 当前没有安装/采用 DAG、LangGraph、第三方 Runtime 或 Agentic Retrieval；没有修改产品 Runtime；
- holdout executions = 1，最终产品裁决为 reject Multi-Agent；普通并行仅作为 8D 优先设计输入，尚未接产品。

## 8. 面试准确表述

完成结果后可以说：

> 我把 Multi-Agent 采用问题拆成串行、普通并行和角色隔离三路，用同一 fixture 与真实 Harness 做一次性
> holdout。候选安全门都过了，但延迟改善 18.95% 未达 20%，且没有比普通并行更强的失败隔离，所以我拒绝
> 产品采用 Multi-Agent，并把更小的普通并行方案留给后续 Evidence fusion。

仍不能说：“Multi-Agent 已采用/上线”“真实模型或 OP.GG 已并行”“生产实测提速”“实现 DAG/恢复”。
18.95%/22.88% 是 frozen modeled units，不是生产 p95；reject 是本实验的完整、可信结论。
