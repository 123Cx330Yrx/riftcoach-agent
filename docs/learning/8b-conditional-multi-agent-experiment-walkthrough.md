# 8B Conditional Multi-Agent Experiment walkthrough

> 当前状态：holdout 前 implementation。本文先记录已经存在的设计、源码与本地 TDD；最终 development、
> 唯一 holdout、ADR、结果 SHA 和两次公共 CI 证据将在真实发生后补齐。coverage 在此之前保持 `planned`。

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

CLI 在运行 case 前先以 `x` 模式预留正式 JSON；失败留下空 sentinel，同一目标不能重跑。不要删除/覆盖结果
追绿，不要把 `tmp/` development 结果提交，不要在公共 CI 中运行 holdout。

## 7. 失败、安全与范围边界

- gate/case/input/code/public-CI/admission/experiment identity 任一漂移 fail closed；
- 角色工具或发布权扩大、Artifact→Context 不匹配、metrics/verdict 被改写 fail closed；
- 八个硬门任一非零不生成合法 record；
- `external_io_calls=0` 指没有网络/Provider，不表示没有本地 fixture、线程或文件 I/O；
- Scripted Token 与 latency units 只用于公平预算模型，不是 tokenizer、费用、p95 或线上 SLA；
- 当前没有安装/采用 DAG、LangGraph、第三方 Runtime 或 Agentic Retrieval；没有修改产品 Runtime；
- 当前 holdout executions = 0，最终 adopt/partial/reject 仍未知。

## 8. 面试准确表述

当前可以说：

> 我把 Multi-Agent 采用问题拆成串行、普通并行和角色隔离三路，用同一 fixture 与真实 Harness 做
> evaluation-only TDD，并为角色工具、Context、Artifact digest、结果防篡改和一次性 holdout 建了硬门。

当前不能说：“Multi-Agent 已采用/上线”“真实模型或 OP.GG 已并行”“实测提速 20%”“holdout 已通过”。最终
表述必须等待不可覆盖结果和 ADR，且 reject 仍是完整、可信的实验结论。
