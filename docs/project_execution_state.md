---
state_schema: 1
main_stage: 8
substage_group: "stage-8-multi-agent-reliable-runtime-productization"
current_checkpoint: "8e-productization"
status: in_progress
pause_reason: ""
---

# RiftCoach 当前执行状态

> 本文档是“项目现在做到哪一步”的唯一事实源。路线职责看
> `docs/roadmap.md`，历史需求看 `docs/requirements_change_log.md`，本轮执行
> 细节看 `.planning/.active_plan` 指向的计划，决策演变看
> `docs/roadmap_change_history.md`。

## 状态元数据

- 最后更新：2026-08-23（RQ-086 真实 Riot gate 通过；OP.GG mid replay 暴露严格 adapter schema-drift，8E preflight 继续）
- 主阶段：阶段 8；Stage 7、Stage 8 entry design、8A、8B、8C 与 8D 均已关闭。Multi-Agent 产品候选按 ADR-0053 reject；当前唯一检查点为 `8e-productization / in_progress / preflight`，尚未实现完整 8E/8F。
- 当前子阶段组：`5P-1-product-contract-compiler` 已由提交
  `57bd36adcd289b7cc51c1c430e04398daf0683f3` 与 Actions run `31987501935` 完成 exact-SHA
  公共验证；严格产品 DTO、Catalog-backed typed selection、服务器 run ID、Artifact binding 与
  Manifest-derived Runtime policy 已闭环。唯一下一检查点为
  `5P-2-prompt-program-runtime-composition` 已由提交
  `0a9651f4e305616626c58ea28e2c300a491f2a3b` 与 Actions run `31988837293` 完成 exact-SHA
  公共验证；Prompt Program V1、drift gate、verified Runtime identity 与 composition root 已闭环。
  用户已按 RQ-043 恢复并完成 `5P-3-domain-application-service`；Summary/Report domain
  services、Application Service、安全错误映射和 secure product execution factory 已由提交
  `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 与 Actions run `31998739178` 完成 exact-SHA
  公共验证。用户又按 RQ-044 完成 `5P-4-file-backed-run-receipt-query`；immutable receipt/store、
  strict Trace/manifest/final Artifact query 与 Application receipt 接缝已由提交
  `932a863120a4561f58c477a69becbccd2ec9ff45` 和 Actions run `32002994441` 完成 exact-SHA
  公共验证。用户现按 RQ-045 恢复 `5P-5-thin-fastapi-adapter-no-io-vertical-slice`；本轮先以
  红灯合同冻结四个 HTTP 端点，再安装 FastAPI 并实现薄 Adapter，所有测试保持 Fake/fixture
  no-I/O。`app/api/main.py` 与 `tests/test_fastapi_adapter.py` 已本地实现并通过 24 项 API
  聚焦；完整回归为 `884 passed, 1 warning, 110 subtests passed`。提交
  `6d1e5b0af186f523bee35c24c6873578a149b824` 与 Actions run `32005648179` 已完成 exact-SHA
  公共验证，5P-5 正式关闭。用户已按 RQ-046 恢复
  `5P-6-product-slice-evaluation-exit-review`；十项功能要求、分层/NFR、安全/no-I/O 与
  deferred 边界已形成 exit matrix，面向初学者的退出审查已完成。本地结论为
  `close-with-deferred-boundaries`，聚焦 `121 passed, 1 warning`、相邻 `166 passed`、完整
  `884 passed, 1 warning, 110 subtests passed` 与全部本地门禁通过。退出审查提交
  `8c8acc6911209e645cfaee18bd40870f78d8704f` 已由 GitHub Actions run `32010604551` 完成
  exact-SHA 公共验证，5P-6 与整个 5P 正式关闭；canonical 已按 RQ-047 恢复
  `5F-entry-design` 已完成 Pi-only Runtime 采用实验入口设计；提交
  `ce979752808271696b1dfe499317ead66de6aacb` 与 Actions run `32013948784` 已完成 exact-SHA
  公共验证。本轮未安装 Pi、未写 adapter、未读取 Key、未调用真实 Provider；用户现已按 RQ-048
  恢复 `5F-1-pi-source-license-contract-audit`。官方 release/package/license 与低层合同审计
  的裁决为“允许有条件进入 5F-2 隔离 no-I/O spike”；完整回归
  `884 passed, 1 warning, 110 subtests passed` 与两套 RAG/compileall/governance/安全/dry-run/
  diff 门禁通过；提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 已由 Actions run
  `32016852979` 完成 exact-SHA 公共验证，5F-1 正式关闭。canonical 只交接到
  `5F-2-offline-protocol-adapter-spike` 准备状态；用户现已按 RQ-049 明确恢复 5F-2。本轮先以
  ADR-0035 和实施计划冻结版本化 JSONL sidecar、Scripted StreamFn、单一 Python
  `knowledge.search`、进程/Usage/Trace 安全和 TDD 顺序；exact npm lockfile、官方 Pi 0.84.2
  sidecar、Python controller、真实本地知识 Tool、Usage 四态、安全故障和两项窄 parity 已本地完成。
  聚焦 `35 passed`、相邻 `99 passed`、完整 `919 passed, 1 warning, 110 subtests passed` 与两套
  RAG/compileall/governance/安全/dry-run/diff 门禁通过；本地退出裁决为
  `pass-with-boundaries`；实现提交 `f62f078faca0d93494478011d2fe18cdeb85970f` 与 Actions run
  `32022258177` 已完成 exact-SHA 公共验证，5F-2 正式关闭；状态收尾提交
  `1454f59b0e07d96defedfc093807a8ef03391839` 与 Actions run `32022784855` 也已完成
  exact-SHA 公共验证。用户现已按 RQ-050 明确恢复 5F-3，当前只评估完整合同、安全、
  ReviewHarness 唯一发布权、Trace/Usage/Artifact 语义与跨语言维护成本。评测专用 adapter、
  process-local Tool evidence、per-call Usage/finish reason 和严格 Signal projector 已本地完成；
  Pi 草稿通过现有 Harness/typed output/Artifact，成功路径可组成合法 body-free Trace。45 项聚焦、
  196 项相邻与完整 `929 passed, 1 warning, 110 subtests passed` 通过；Context token-unit/char、
  extended terminal 与 live timing 三项 hard gap 仍存在。本地裁决为
  `harness-compatible-but-runtime-gate-failed`，不准入 5F-4；两套 RAG、compileall、Node
  syntax/tree、Harness/secret/tracked-data、dry-run、governance 与 diff 门禁也已通过，当前只待
  提交/推送与 exact-SHA 公共 CI。实现/退出提交
  `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已由 Actions run `32025522606` 完成
  exact-SHA 公共验证，5F-3 正式关闭；5F-4 因既定前置硬门失败而未进入，不调用真实模型。
  ADR-0037、exit matrix/review 已裁决 `partial-adopt-evaluation-assets-only`：产品拒绝 Pi，只冻结
  保留可执行评测资产与采用门方法。提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已由 Actions run
  `32028206103` 完成 exact-SHA 公共验证，5F 与整个阶段 5 正式关闭。canonical 只交接到
  `6A-entry-design`。用户已按 RQ-052 恢复该检查点；当前已审计 5P 的同步文件/crash gap、多 worker
  限制和 EchoMind API/Memory 参考实现，并明确 PostgreSQL 是唯一生产语义基线：SQLAlchemy 2 映射、
  Alembic 迁移，普通逻辑可用 Fake/单元测试，但事务、迁移和并发领取必须由真实 PostgreSQL Docker/CI
  验证，SQLite 绿灯不能替代。用户随后选择同仓库、同部署的独立 PostgreSQL polling worker：API
  持久化 queued task 并快速返回，Worker 通过 PostgreSQL 事务原子领取；不引入 Redis/Celery/Kafka。
  架构与数据流章节已获用户确认：采用模块化单体、API/Worker 分工、短事务以及 SQL 控制面与
  Artifact/Trace 数据面分离。task_id/run_id 双身份、任务控制字段、四态状态机和不可逆终态规则
  也已获确认。SQL/Artifact 分工、创建/claim/终态短事务、幂等与 ownership 核心也已获确认；但在
  失败边界复核中发现：多 Worker 下不能仅凭新 Worker 启动就把其他无 receipt 的 running task 自动
  判死。用户已选择保守方案 A：有匹配 immutable receipt 时自动补齐成功；正常关闭由 owner Worker
  安全失败；无终态证据的硬崩溃任务只标记 recovery-required，待受限人工确认后条件更新为失败。
  其余失败语义与 HTTP 投影也已获确认：POST 202 只表示可靠入队，任务执行成功与 Harness 发布
  状态分离，not-found/ownership、幂等冲突、DB 不可用、报告未就绪和完整性失败具有不同安全语义。
  作品集规模 NFR 也已获确认：单服务器起步、默认单并发 Worker、真实 PostgreSQL 多 Worker 正确性、
  有限 owner/global 背压、API/claim 延迟目标、退避轮询、分层健康检查以及不冒充 99.9%/容灾。
  安全与数据生命周期章节也已获确认：owner_id 来自可信 ActorContext，查询 owner-scoped，开发固定
  owner 不冒充公网鉴权；CORS/密钥/日志 fail-closed，数据按 7/90/30 天分层保留，terminal task 可删除，
  active task 删除不冒充 cancel。分层测试矩阵也已获确认：纯逻辑/Fake、真实 PostgreSQL migration/
  repository/concurrency、API/Worker、离线产品纵向、安全/生命周期与性能层各自有职责，PostgreSQL CI
  是阻塞门且外部 Provider/Riot 调用为 0。七个 6A 原子实施批次也已获用户确认。ADR-0038、正式设计
  与实施计划现已创建。本地完整回归 `929 passed, 1 warning, 110 subtests passed`、两套 RAG、
  compileall、Harness dry-run、governance、Secret/run-data 与 SDK boundary 均通过；设计提交
  `c0b5af0eec1654c35afddb3c8a66b774a233a688` 已由 Actions run `32041343696` 完成 exact-SHA 公共
  验证。`6A-entry-design` 正式关闭；用户已按 RQ-053 授权
  `6A-1-postgresql-foundation`，当前只实施 PostgreSQL 基础设施、初始 schema/migration 与真库 CI
  门，不实现 Repository、Worker 或 API 行为。本机未安装 Docker，故本地真库测试必须明确 skip，
  真实 PostgreSQL 阻塞证据由 GitHub Actions service 提供。当前本地已实现严格配置、惰性 Engine/
  Session factory、task ORM metadata、可逆 initial migration、PostgreSQL Compose 与独立 CI job；
  6A-2 又已本地实现 task contract、fingerprint、Fake service 与 PostgreSQL create/query Repository；
  聚焦为 `29 passed`，完整回归为 `977 passed, 8 skipped, 1 warning, 110 subtests passed`，两套 RAG、
  compileall、Harness dry-run、governance、Secret/run-data、SDK boundary 与 YAML checks 均通过。
  三个本地 skip 全部已由提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 的 GitHub Actions run
  `32043214500` 在真实 PostgreSQL 17 service 上补齐；`pytest` 与 `postgres-migrations` 两个 job 均
  completed/success，6A-1 正式关闭。用户已按 RQ-054 授权并完成 6A-2；提交
  `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 的 Actions run `32046532695` 中 `pytest` 与
  `postgres-migrations` 均 completed/success，真实 PostgreSQL 已验证 5 项 Repository 测试。6A-2
  正式关闭。用户又按 RQ-055 完成 6A-3；提交
  `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 的 Actions run `32097561436` 中 `pytest` 与
  `postgres-migrations` 均 completed/success，真实 PostgreSQL 已验证 deterministic SKIP LOCKED claim、
  双 Worker 不重复、ownership/terminal CAS、短事务与 timestamp invariant。6A-3 正式关闭，只交接
  6A-4 准备状态；不接真实 Application/Artifact 或 API。用户随后按 RQ-056 恢复 6A-4；trusted run_id、
  真实 Recent Review Task Executor、严格 receipt/Trace/final Artifact terminal、receipt-proven
  reconciliation、recovery-required 与人工 recovery CAS 已实现。提交
  `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 的 Actions run `32102522662` 中 `pytest` 与
  `postgres-migrations` 均 completed/success；完整 pytest 为 `1033 passed, 20 skipped, 1 warning,
  110 subtests passed`，真实 PostgreSQL job 执行 6 个数据库测试文件并得 `40 passed`，其中包含本轮
  5 项 reconciliation/产品纵向测试。6A-4 正式关闭，只交接 6A-5 准备状态。上一子阶段组
  5E AgentRuntime V1 已完整闭环：入口设计与 ADR-0029 冻结为“薄 Runtime
  + 可选观察端口 + completeness-aware Usage + 原子最终 Trace”；5E-1 的严格合同、
  Recorder/Usage 与 Trace Store 已由提交 `d891184e1bf82068188d2fb5715769bdaa3da022`
  和 GitHub Actions run `31942483874` 完成 exact-SHA 公开验证。5E-2 的入口源码审计、
  初学者设计与 ADR-0030 已公开完成：采用 run-scoped `ObservedLLMProvider` 覆盖 Agent
  与 Harness 全部 Provider 边界，AgentLoop 只观察业务 Tool/Agent 终态，Harness 只观察
  持久化后的状态/评测/发布，并用两阶段 terminal commit 消除 Trace 写盘终态悖论；Task D
  已形成并公开验证统一同步 `AgentRuntimeV1.run()`，组合两个真实 Skill、真实本地 RAG、共享
  observed Provider、唯一 Harness、typed output、完整 Usage 与安全最终 Trace；当前 5E-3
  已完成入口审计和进程内 worker/有界 queue 方案冻结；stream item、parity、背压、关闭隔离、
  预期失败和终态测试均已在本地通过，并由提交 `80b76a1` / GitHub Actions run `31960987333`
  完成 exact-SHA 公共验证；5E-3 正式闭环。5E-4 的退出矩阵与
  `close-with-deferred-boundaries` 裁决由提交
  `3d3656195a66adfd4595cffa145c978d24c33628` / GitHub Actions run `31962252231`
  完成 exact-SHA 公共验证，因此 5E-4 与整个 5E 正式完成；这不表示生产就绪。
  Task A 的合同 1.1、合法 1.0
  读取、默认关闭 observation port、missing Usage fail-closed、Harness lifecycle 与
  prospective terminal 已完成并由提交 `2e78c9606fe93b56657d4bb13c8efe0f1eed98fe`、
  GitHub Actions run `31947625293` 完成 exact-SHA 公共验证；聚焦回归为
  `131 passed, 44 subtests passed`，完整回归为 `691 passed, 110 subtests passed`，
  两套 RAG、compileall、安全边界、Harness
  dry-run、治理与差异检查通过。Task B 已完成 TDD：run-scoped
  `ObservedLLMProvider` 在统一 capability preflight 后记录连续 Provider ordinal、phase、
  Usage、有限 finish reason 与 allowlisted error detail；`AgentLoop.run()` 增加 keyword-only
  默认关闭 observer，在整批预检后记录业务 Tool 安全 envelope，并让每个返回结果恰好形成
  一个 Agent terminal。Provider/Tool started 或 completed 观察失败均 fail-fast，且
  `ToolRuntime` 不再把 `RuntimeObservationError` 计入 retry、breaker 或 fallback；
  `observer=None` 与旧行为逐字段一致。聚焦回归为 `81 passed`，完整回归为
  `721 passed, 110 subtests passed`；本地两套 RAG、compileall、安全边界、Harness dry-run、
  治理和差异检查通过。实现提交 `28bd910525a7522be16bd69b6e945846839a4cd8` 已推送，
  GitHub Actions run `31952026988` 对 exact SHA 的全部公开门禁成功；Task B 正式闭环。
  Task C 已完成本地实现、完整门禁和 exact-SHA 公共 CI（提交 `8b69c9b`、Actions
  `31957712118`）。Task D 新增 18 项统一 Runtime 纵向测试，完整本地回归为
  `747 passed, 110 subtests passed`；两套 RAG、compileall、安全边界、Harness dry-run、
  治理和差异检查均通过，本批 Provider/Key/held-out I/O 为 0。实现提交 `d49508e` 已由
  GitHub Actions run `31959646589` 完成 exact-SHA 公共验证，5E-2 正式闭环；随后 5E-3
  已由 `80b76a1` / Actions `31960987333` 完成 stream parity 与公开验证，5E-4 已由
  `3d36561` / Actions `31962252231` 完成退出审查公共验证。
  设计提交
  `3c6f26a4802821548be8d61085552f5b9a790468` 已通过 GitHub Actions run
  `31944389807` 的 exact-SHA 公共验证。5D Python 受限 Agent Loop
  已通过退出审查；以下保留其 entry design、5D-1 至 5D-7 的公开证据链：
  5D-7 Batch A-C 与 Batch D 的 D1-D5 已完成，DeepSeek V4 Pro Adapter 真实
  structured/tool 协议 3/3 calls 已准入；三场领域 held-out 的控制面以及独立输入计划、
  oracle-blind 生产 Executor 和真实门 CLI 已完成离线 TDD，并由提交
  `eb198354b3186f25b7d0455d7ed28725bc17e234`、GitHub Actions run `31799394506`
  完成 exact-SHA 公开验证；真实 DeepSeek 领域 held-out 已执行一次并在首个正常案例因
  `unsupported_parallel_tool_calls` 不准入，后两例按首错停止跳过；不可变结果归档提交
  `26b668d0ce594e648a692cd2caf831c86125fede` 已通过 Actions run `31810164628`；ADR-0022
  的多 ToolCall 批次离线 TDD 已由提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 完成，
  Actions run `31817798170` 对精确 SHA 已成功；ADR-0024 已完成新鲜领域采用门的
  零调用设计，决定复用现有控制面并重新冻结 fixture/Dataset/plan/Context 身份；设计
  提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已通过 Actions run `31859717836`；
  Fresh-Gate 1 已完成本地离线 TDD，旧 V1.0 资产兼容、V1.1 input plan、三案例
  Prompt/Context commitment、历史 `3+1` 调用证据链与 development-only no-I/O
  admission 已实现；提交 `adba965a7f7fb4293020502b4440e9880633e571` 已通过 GitHub
  Actions run `31860874440` 的 exact-SHA 公开 CI；Fresh-Gate 3 已在本地创建全新匿名
  3 局 fixture/确定性报告、正式三案例 held-out、V1.1 input plan 与三个实际案例的
  body-free Prompt/Context snapshot；新旧 fixture/题目/marker/ID 均不复用，交叉身份和
  fixture 数字自洽由离线测试固定；资产提交
  `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已通过 GitHub Actions run
  `31861960565` 的 exact-SHA 公开 CI；Fresh-Gate 4 入口批已完成
  本地 TDD：新 readmission 同时绑定历史 `3+1` 调用证据、
  ADR-0022 修复 CI、Fresh-Gate 3 资产 CI、当前 code/public-CI、新 Dataset/plan/fixture 与
  三案例 Context；现有生产 CLI 已切换到 V2 profile 并增加 prepare-only，Fake Provider
  纵向装配与首错停止通过，本地完整回归为 `580 passed, 103 subtests passed`；实现提交
  `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过 GitHub Actions run `31863341338`，
  同一干净 SHA 的真实 `--prepare-only` 输出 no-I/O admitted、external calls 0、held-out
  未执行；用户随后明确确认，V2 真实门在公开成功提交
  `741e84140f816fb4b06b2812a8d07d3f32eaf4d0` 上只执行一次：首例第一次响应成功
  规范化并使用 3241 input + 199 output tokens，下一调用因 `3440 + 1024 > 4000`
  在 I/O 前以 `token_budget_exhausted` 停止；Harness 降级、后两例 skipped、unsafe
  publication 为 false，最终 `admitted=false`。不可变结果 SHA-256 为
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`；归档提交
  `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 已通过 GitHub Actions run
  `31864370988` 的 exact-SHA 公开 CI；ADR-0025 与 V2 预算可达性离线裁决现已本地完成：
  精确证据证明第二次调用至少要求 4464-token 单例上限，当前 4000 必然不可达；真实
  本地生产路径的三阶段 envelope 长度为 6666/7774/6266，校准 input 投影为
  3241/3780/3047，但明确不是 Provider tokenizer 精确值；完整回归为
  `587 passed, 103 subtests passed`，两套 RAG 与全部本地门禁通过，本批外部调用为 0；
  裁决提交 `78400b9310e512668c81ca41cd65623a92a27226` 已通过 GitHub Actions run
  `31865285994` 的 exact-SHA 公开 CI；ADR-0026 又完成 V3 资源校准设计：正常三调用和
  可选第四次 Evaluation repair 已按真实生产控制流区分；后续只用两个公开 development
  profile 形成四阶段请求，再以最多 8-call、校准输出 64、零重试、首错停止的独立 Usage
  replay 观测资源；V3 单例预算将按逐阶段最大真实 input、25% 工程余量和四次 1024
  output ceiling 推导，若含既有协议成本后超过 `$0.10` 则停止而不创建 held-out；本设计
  Provider/Key/网络调用为 0；本地完整回归为 `587 passed, 103 subtests passed`，两套
  RAG、compileall、Harness/secret/tracked-data、dry-run、治理和 diff check 均通过；
  设计提交 `351c0e64adf9d2ace42c557d40fac81a44ab539e` 已通过 GitHub Actions run
  `31866084382` 的 exact-SHA 公开 CI；V3 资源校准离线实现现已本地完成：两个全新
  development profile 经真实 production Executor 形成精确 8 个四阶段请求，ceiling
  初始/工具后 envelope 为 12206/15279 本地单位且未超过 Skill 16000 ceiling；body-free
  请求快照、安全 Fake 结果、8-call/64-output/64000-token/`$0.10` 账本、首错停止、
  Decimal 预算推导和 no-I/O admission 已由 11 个新增测试固定；本批 Provider/Key/
  网络调用和 V3 held-out 均为 0；本地完整回归为 `598 passed, 103 subtests passed`，
  两套 RAG、compileall、Harness dry-run、SDK/tracked-data、治理与 diff 门禁均通过；实现
  提交 `2d676966915a7967b946880040b59c022283e683` 已通过 GitHub Actions run
  `31867655627` 的 exact-SHA 公开 CI，离线校准基础设施至此公开冻结；用户现已明确确认
  一次真实 8-call development Usage replay；真实运行入口提交
  `6aa8c439a29adafebf1ffe1bb0eef0c1b921ca44` 已通过 Actions run `31868747216`，同一
  干净 SHA 的 prepare-only 为零调用；正式 replay 随后只发送第 1 个 baseline 请求，因
  未形成规范化 `ChatResponse` 以 `provider_response_invalid` 首错停止，后 7 个请求未
  发送。不可变结果 SHA-256 为 `ba33e75af7f8755dc89904fb346f66962fb29e92d08173494053f17ad8e7088b`：
  1 external call、0 normalized responses；账本 0 tokens/`$0` 只代表未取得可结算 Usage，
  实际计费 Token/费用均为 unknown。零调用裁决明确禁止预算推导、补跑和 V3 held-out，
  模型质量仍为 unknown；裁决 SHA 为 `0ce09b52d982f8c03052f1d94fde1da5628af31dbd797ea770522ce092907446`。
  结果/裁决聚焦回归 34/34、完整回归 `611 passed, 103 subtests passed`，两套 RAG、
  compileall、Harness SDK/tracked-data boundary、dry-run、治理和 diff check 已在本地通过；
  归档提交 `421a24393cafdc79a02de4091f569cfb9aa5b721` 已通过 GitHub Actions run
  `31869409106` 的 exact-SHA 公共 CI；ADR-0027 现已零调用裁决关闭当前 DeepSeek V3
  资源校准与领域采用尝试，保留低层协议准入但领域/产品质量继续 unknown；未来真实
  Provider 门必须先离线保留允许列表约束的安全细分错误 provenance；本决策已通过
  51 项聚焦、完整 `611 passed, 103 subtests passed`、两套 RAG 与全部本地门禁，
  本批 Key/Provider/external calls 为 0；决策提交
  `ea91e9697c820c0850db488a93263fc169719515` 已通过 GitHub Actions run
  `31872476103` 的 exact-SHA 公共 CI；随后已在零 I/O 下实现 ADR-0027 要求的安全
  `provider_error_code` 白名单传递和旧结果兼容合同，聚焦回归 89 passed；完整回归为
  `616 passed, 103 subtests passed`，两套 RAG 与全部本地门禁通过；实现提交
  `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a` 已通过 GitHub Actions run
  `31874240935` 的 exact-SHA 公共 CI；ADR-0028 与 5D-7 收尾审查现已区分“评测门完成”
  和“领域模型采用未准入”，接受 5D-7 完成并把 G53 保持为非阻塞 deferred 候选；
  审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已通过 GitHub Actions run
  `31876536179` 的 exact-SHA 公共 CI；5D 退出审查提交
  `2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已通过 GitHub Actions run
  `31877076222` 的 exact-SHA 公共 CI；5E 入口设计提交
  `c91c2d75f85e1315e65e9768894982556053a7b0` 已通过 GitHub Actions run
  `31878052835` 的 exact-SHA 公共 CI；5E-1 实现提交
  `d891184e1bf82068188d2fb5715769bdaa3da022` 已通过 GitHub Actions run
  `31942483874` 的 exact-SHA 公共 CI
- 唯一下一步：`8e-productization` preflight 正在进行。8D implementation/evidence
  `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions `32598480400` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全绿，八维 coverage 已 complete。8E 先完成
  有界真实 Riot/OP.GG 验证、脱敏 EvidenceBundle replay、玩家档案选择合同和 legacy 地区审计，
  再分小批实现 React/SSE/Auth/HTTPS/部署；8B holdout 不得再次执行。
- 范围约束：5P-5 只增加本地同步 HTTP Adapter 与 no-I/O 纵向测试，没有实现真实 Riot/Provider、
  SQL/Session/Memory/SSE/恢复、公网部署或进入 5F；
  DeepSeek V2 结果不得覆盖或重跑，不能把安全降级解释为模型质量通过，也不能用低层
  协议、候选选择或发布热度替代领域质量证据

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 已完成 | development v2 为 23/23；independent holdout v1 单次运行后为 11/12，唯一失败已原样保存并分类 | 进入维护；holdout v1 永不用于调节当前规则 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 已完成 | ADR-0010 比较排除词、LoL 域信号、澄清、LLM 与 Embedding；决定 V1 暂缓模型兜底并定义重新采用门槛 | 进入维护；新鲜数据满足门槛后才能用新 ADR 重开 |

## 5D 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成证据 |
|---|---|---|---|
| 5D-entry-design | 审计现有接缝、比较组合方案、冻结数据流与教学顺序 | 已完成 | 5D 设计文档、ADR-0011、治理检查 |
| 5D-1 Skill Run Boundary Hardening | 统一 I/O 非空文本、selected identity、run_id 和输入 Artifact 绑定 | 已完成 | 设计/TDD 文档、`SkillExecutionBoundary`、共享 run ID/Artifact 编码、合同与篡改测试 |
| 5D-2 Context Builder V1 | 两个 Skill 的最小上下文、信任标签、确定性裁剪和 ContextSizer | 已完成 | 设计/TDD 文档、`ContextBuilderV1`、两个 Skill allowlist、citation/注入/预算边界测试 |
| 5D-3 Skill Run Compiler & Budget Enforcement | Manifest 权限/预算编译为 AgentRunRequest，并约束累积上下文 | 已完成 | 设计/TDD 文档、`AgentRunCompiler`、完整消息估算、逐轮 Context 门禁与协作式总 deadline 测试 |
| 5D-4 Evidence-Aware Agent Draft Preparation | AgentLoop + knowledge.search 生成 draft 与 KnowledgeEvidence | 已完成 | 共享 evidence converter、`SkillAgentDraftPreparer`、两个真实 Skill + Fake Provider + 真实 `knowledge.search`，成功/拒答/去重/冲突/失败与停止边界测试 |
| 5D-5 Harness Composition & Typed Terminal Output | 通过 DraftPreparationStep 接入单一发布门禁 | 已完成 | 统一 preparation 合同、旧顺序 Adapter、`SkillReviewExecutor`、Artifact 驱动 typed output、两个真实 Skill 的 Fake Provider + 真实 RAG + Harness 端到端测试 |
| 5D-6a Structured Output Contract | Provider-neutral schema、Pydantic 校验和有限修复 | 已完成 | `StructuredResponseContract`、能力门禁、严格 Evaluation Pydantic 模型、一次 repair、fail-closed 与 Harness 降级测试 |
| 5D-6b Real Provider Capability Gate | 实测首个 Provider，并为第二 Provider 决策提供真实证据 | 已完成（部分采用） | P1-P5 5/5、真实 Adapter 协议 3/3 calls 通过；真实 recent-form 领域运行只执行一次并在 1 个领域 call 后未形成统一 `ChatResponse`，无工具/证据/Evaluation，领域 `admitted=false`，Harness 安全降级；ADR-0012 准入最小协议、拒绝领域能力并暂缓第二 Provider |
| 5D-7 Prompt/Context & Domain E2E Evaluation | 工具选择、事实/引用、注入、质量/成本/延迟评测 | 已完成（当前无领域 Provider 准入） | 分层评测、Prompt/Context 身份、Evaluation 1.1、held-out 生命周期、资源/错误合同和真实负面结果均已审查；ADR-0028 接受评测门完成，同时保留 GLM/DeepSeek 领域质量 unknown、G53 deferred 与 Flash 未测试边界 |
| 5D-exit-review | 对照全部证据和 5E 前置项 | 已完成 | 十项功能要求与 NFR 均满足 5D V1；无领域 Provider 准入的限制保留；未提前实现 5E |

## 5E 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/验收证据 |
|---|---|---|---|
| 5E-entry-design | 审计分散信号、比较组合方案、冻结 Runtime 边界与 NFR | 已完成 | 初学者设计、ADR-0029、四批实施顺序；616 tests/103 subtests、两套 RAG 和全部本地门禁；`c91c2d7` / Actions `31878052835` 公开通过；无产品代码或 Provider I/O |
| 5E-1 Runtime Contract、Usage 与 Trace Store | 严格合同、Recorder、未知 Usage 与原子最终 Trace | 已完成 | 39 项聚焦、166 tests/55 subtests 相邻、655 tests/103 subtests 全量回归和全部门禁；`d891184` / Actions `31942483874` exact-SHA 公开通过；无 Provider I/O |
| 5E-2 Observable `run()` Vertical Slice | observer 接缝与两个 Skill 的统一同步执行/Trace | 已完成 | Task D 实现提交 `d49508e` / Actions `31959646589` exact-SHA 公共 CI 成功；新增 18 项测试，完整回归 `747 passed, 110 subtests passed`，两套 RAG/compileall/安全/dry-run/治理/diff 门禁通过；本批无 Key/真实 Provider/held-out I/O |
| 5E-3 Live `stream()` & Parity | 同一执行核心的进程内实时事件和 run/stream 同终态 | 已完成 | 提交 `80b76a1` / Actions `31960987333` exact-SHA 公共 CI 成功；stream 聚焦 15 项、完整回归 `762 passed, 110 subtests passed`，两套 RAG/compileall/治理/安全/dry-run/diff 门禁通过；无 Key/真实 Provider/held-out I/O |
| 5E-4 Runtime Evaluation & Exit Review | 安全、失败、资源、纵向评测与 5E 退出审查 | 已完成 | exit matrix、Runtime 聚焦 `128 passed`、完整 `762 passed, 110 subtests passed` 和全部本地门禁通过；`3d36561` / Actions `31962252231` exact-SHA 公共验证成功；决策为 `close-with-deferred-boundaries` |

## 5P 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/验收证据 |
|---|---|---|---|
| 5P-entry-design | 同时设计 Prompt Program V1 与早期产品切片，冻结范围/NFR/顺序 | 已完成 | 设计文档、ADR-0032/0033；本地 762 tests/110 subtests、两套 RAG 与全部门禁；`49841ec` / Actions `31985199623` exact-SHA 公共成功；无产品代码/外部 I/O |
| 5P-1 Product Request & Typed Skill/Runtime Compiler | 严格产品 DTO、trusted typed selection、Artifact binding、Manifest-derived policy | 已完成 | `57bd36a` / Actions `31987501935` exact-SHA 公共成功；796 tests/110 subtests；无外部 I/O |
| 5P-2 Prompt Program V1 & Runtime Composition Root | Program manifest/catalog/drift gate 与 secure production composition | 已完成 | `0a9651f` / Actions `31988837293` exact-SHA 公共成功；完整回归 `805 passed, 110 subtests passed`；无外部 I/O |
| 5P-3 Domain Pipeline Promotion & Application Service | 提升 Summary/Report 服务并组合产品用例/安全错误 | 已完成 | `4bd5c83` / Actions `31998739178` exact-SHA 公共成功；完整 `830 passed, 110 subtests passed`；无外部 I/O |
| 5P-4 File-backed Run Receipt & Query Projection | body-free receipt、Trace/manifest/report 安全复读 | 已完成 | `932a863` / Actions `32002994441` exact-SHA 公共成功；聚焦 50、相邻 179、完整 860 tests/110 subtests |
| 5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice | 最小端点、依赖与 Fake Provider HTTP 纵向测试 | 已完成 | 四个固定端点、显式 Port、strict DTO、错误映射与真实 Runtime/Harness/RAG no-I/O 切片；24 API tests，完整 884 tests/110 subtests；`6d1e5b0` / Actions `32005648179` exact-SHA 公共成功 |
| 5P-6 Product Slice Evaluation & Exit Review | 合同、安全、资源、公开证据与限制退出审查 | 已完成 | 十项功能 exit matrix、初学者 exit review、聚焦 121、相邻 166、完整 884 tests/110 subtests 与全部门禁通过；`8c8acc6` / Actions `32010604551` exact-SHA 公共成功；裁决 `close-with-deferred-boundaries`，外部 I/O 为 0 |

## 5F 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/下一步证据 |
|---|---|---|---|
| 5F-entry-design | 收缩 Pi-only 候选，冻结同切片对照、合同、安全、跨语言成本和 adopt/partial-adopt/reject 门槛 | 已完成 | ADR-0034 与 `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`；提交 `ce97975` / Actions `32013948784` exact-SHA 公共成功；无 Pi/Key/Provider I/O |
| 5F-1-pi-source-license-contract-audit | 审计官方 Pi 源码/包版本、许可证、Runtime/Provider/Tool/event/state/abort/Usage 接缝 | 已完成 | 冻结 `earendil-works/pi v0.84.2` / `914cf147...`、MIT、Node `>=22.19.0`；完成合同/安全/依赖/sidecar 映射；裁决允许有条件进入 5F-2；`5901b09` / Actions `32016852979` exact-SHA 公共成功；Pi/Key/Provider I/O 为 0 |
| 5F-2-offline-protocol-adapter-spike | 用同一 recent-form Context、Scripted StreamFn 和单一 `knowledge.search` 建立隔离 Python↔Node 协议对照 | 已完成 | exact lock/sidecar/controller、真实本地知识 Tool、35 focused/99 adjacent/完整 919 tests 与本地退出审查；`pass-with-boundaries`；`f62f078` / Actions `32022258177` exact-SHA 公共成功；不代表 Pi adopt |
| 5F-3-contract-security-harness-evaluation | 对比完整 Tool/Context/deadline/structured output/error/terminal 与 ReviewHarness/Trace parity | 已完成 | 45 focused、196 adjacent、完整 929/110 subtests；Harness/成功 Trace 可适配，但 Context/extended terminal/live timing 硬门失败；`3d9a081` / Actions `32025522606` exact-SHA 公共成功 |
| 5F-4-bounded-real-slice | 前置硬门通过且再次授权后，才运行同模型/同 Context/同 Harness 的真实切片 | 未进入（前置门失败） | 5F-3 hard Runtime parity gate failed；真实模型调用不能修复这些合同差异，外部 calls 保持 0 |
| 5F-5-adoption-decision-exit-review | 根据全部证据裁决 adopt/partial-adopt/reject 并关闭 5F | 已完成 | 裁决 `partial-adopt-evaluation-assets-only`；45 focused、929/110 全量与全部本地门禁通过；`f8dea66` / Actions `32028206103` exact-SHA 公共成功；产品拒绝 Pi，冻结保留评测资产 |

## 当前真实能力边界

已经存在的实现：

- 三态路由结果：`selected`、`rejected`、`ambiguous`；
- 无可用 Skill、无匹配 Skill、多 Skill 同时命中的明确原因码；
- Manifest 声明式必需信号组与排除信号；
- 排除信号在 Router 算法与 `RouterDecision` 合同两层都是硬否决；
- `recent-form-review` 与 `single-match-review` 两个真实用户 Skill Contract；
- 单局输入会验证 Summary v1.0、唯一目标 match、短局和 Timeline 缺失边界；
- 两个真实候选的近期选择、单局选择、混合范围歧义、裸 ID 拒绝和域外否决测试；
- 旧 15 条参与过单 Skill 规则校准的案例已归档，并有 SHA-256 来源记录；
- 双 Skill development v2（23 条）与 independent holdout v1（12 条）已建立；
- 评测 CLI 会校验数据集角色、案例数量、候选 Skill name/version 快照；
- development v2 已正式运行并保存到
  `data/evaluation/results/skill_router_v1_development_baseline.json`：23/23 精确匹配，
  selection/rejection/ambiguity accuracy 均为 `1.0`，false-selection rate 为 `0.0`；
- development 明细中没有误路由；该结果只支持冻结当前开发规则，不是泛化证据；
- independent holdout v1 已单次运行并保存到
  `data/evaluation/results/skill_router_v1_holdout_baseline.json`：11/12 精确匹配，
  selection/ambiguity accuracy 为 `1.0`，rejection accuracy 为 `0.8333`，
  false-selection rate 为 `0.1667`；
- 唯一失败 `holdout_device_performance_false_friend` 把“分析一下我最近键盘的表现”
  误选为 `recent-form-review`；实现符合当前字面合同，产品期望拒绝，分类为确定性
  Router 的域语义局限；
- 5C-6 已完成采用决策：确定性 Router V1 保持不变，不根据 holdout 增加“键盘”
  排除词，也不引入 LLM/Embedding；优先等待类型化产品入口、会话澄清与新鲜误路由
  数据，具体重新采用门槛见 ADR-0010；
- 5C 退出复核将命中决策的证据身份收紧为必须与候选 Skill 身份完全一致；
- holdout 冻结点元数据已从不包含双 Skill 合同的 `cfd2084` 更正为实际双 Skill
  合同提交 `4103d42`，没有修改案例、期望、规则或既有结果；
- 5D entry design 已完成源码级接缝审计；ADR-0011 决定 AgentLoop 只作为
  evidence-aware draft preparation，ReviewHarness 保持唯一评测和发布控制；
- 5D 已拆为 5D-1 至 5D-7 和 exit review；拆分本身不是功能实现；
- 两个 Skill 的关键输入输出文本现共享去空白、非空、集合去重规则，Skill 输出
  `run_id` 使用统一安全目录组件合同；
- selected `RouterDecision` 现在同时锁定 Skill 名称与版本，执行前必须与 Catalog
  中当前 `LoadedSkill` 的 Manifest 身份完全一致；
- `RunManifest`、`FileRunStore` 与 Skill 执行请求共享同一跨平台 run ID 规范，拒绝
  路径、盘符、Windows 保留名和超长值；
- `SkillInputArtifactBinding` 使用 Harness 实际 JSON/text 字节编码记录 Summary 与
  确定性报告的 kind、schema version 和 SHA-256；5D-5 已在 terminal output 前逐项
  核对真实落盘记录、物理字节与该内容承诺；
- `SkillExecutionBoundary` 会拒绝非 selected、缺失/漂移 Skill、错误 input model、
  run 不一致和内容/元数据篡改，并返回与调用方 payload 脱钩的输入快照；
- `ContextBuilderV1` 把内部 Policy 与已校验 SKILL.md 固定为 system/instructional，
  把确定性事实、用户请求和初始知识引用固定为 user/data-only；
- 近期复盘只接收 allowlisted scope、aggregate、样本边界、完整确定性报告和最多
  10 个可选 match 投影；单局复盘只接收唯一 target row 与不含其他 match 的精确
  报告行，不注入 `recent_summary`；
- Timeline unavailable 的 null/empty/error 与短局边界保持原义；failed-match 原始异常
  和未知 Summary 扩展字段不会自动进入上下文；
- Manifest context ceiling 不可被调用方提高；required sections 超限时 fail closed，
  optional match/citation 按优先级完整保留或省略，省略 ID 可审计；
- `ContextBundle` 消息必须是 sections 的规范渲染；`AgentRunCompiler` 会重新核对
  run/Skill/version、Manifest ceiling、实际消息大小与工具注册状态；
- `AgentRunCompiler` 只从已验证 Manifest 映射工具白名单、迭代、工具调用和总超时，
  从 `ContextBundle` 映射消息及有效 Context ceiling，并记录安全输入摘要 metadata；
- `DeterministicContextSizer` 现在计算 role/content、ToolCall id/name/arguments 与 Tool
  result metadata 的完整消息 envelope，仍只是 tokenizer-free preflight；
- `AgentLoop` 在每次 Provider 调用前重新估算累计消息；初始或 Tool Observation 后
  超限均以 `context_budget_exceeded` 停止，不再继续调用 Provider；
- Manifest `timeout_s` 被收紧为协作式总 deadline；Provider 获得递减剩余时间，
  ToolRuntime 取运行剩余时间与工具 policy timeout 的较小值，耗尽后以 `timeout` 停止；
- 旧 `LocalRagAdapter` 与新 Agent 路径共用 fail-closed 的知识 payload 转换器；只有
  实际成功且归因字段合法的 `knowledge.search` ToolResult 才能生成稳定 K1..Kn、
  去重 source IDs 与 `KnowledgeEvidence`，重复 chunk 归因冲突会被拒绝；
- `SkillAgentDraftPreparer` 使用 AgentLoop 的同一 ToolRegistry 编译并执行请求，只在
  `completed/final_response` 且最终文本非空时生成尚未发布的 `CoachDraft`；失败知识
  工具、非知识工具、坏 payload 与预算/重复/超时停止均 fail closed；
- `recent-form-review` 与 `single-match-review` 已在 Fake Provider 下通过真实 Catalog、
  Router、ExecutionBoundary、ContextBuilder、Compiler、AgentLoop、ToolRuntime 与本地
  `knowledge.search`；模型只在 Markdown 声称的虚假来源不会进入 Evidence；
- `DraftPreparationStep` 现在是 ReviewHarness 唯一草稿准备接缝；旧 Retriever/Generator
  通过 `SequentialDraftPreparer` 兼容，新 Agent 路径返回同一 draft/evidence 合同，
  没有第二套 Harness 控制流；
- `SkillReviewExecutor` 校验 execution/context 身份，只从 Skill Manifest 映射质量阈值
  和 deterministic fallback，并把 Agent 草稿交给现有 Evaluator/修订/发布状态机；
- `SkillTerminalOutputBuilder` 只从 terminal Manifest 和完整性校验通过的 FINAL_REPORT、
  最终 attempt Evaluation、RETRIEVAL_EVIDENCE 及输入 Artifact 构造 Manifest 声明的
  Pydantic Output；rejected 不暴露报告，降级只返回确定性报告；
- 两个真实 Skill 已在 Fake Provider 下完整走过 Catalog、Router、ExecutionBoundary、
  ContextBuilder、AgentLoop、真实本地 `knowledge.search`、唯一 ReviewHarness 与 typed
  output；该证据不等于真实 Provider Tool Calling；
- 生产 `ZhipuProvider` 已在离线 TDD 中实现 system/user/assistant/tool 四类消息、
  ToolSpec、AUTO/NONE、JSON mode、请求级 `knowledge.search` 可逆别名和 ToolCall
  规范化；REQUIRED、别名冲突、未知别名、非严格 JSON、重复/并行 ToolCall、非空
  reasoning、坏 content 与尚未准入的 structured+tool 同轮组合均 fail closed；
- `AdapterProtocolSliceRunner` 通过同一个 `BudgetedProvider` 把结构化直调和现有
  `AgentLoop` 两轮往返约束在精确 3 次外部调用内；A1 失败会跳过 A2，第 4 次调用会在
  进入底层 Provider 前被拒绝；
- A1 复用 5D-6a 的 `EvaluationResponseModel` 与严格 decoder；A2 只注册固定、只读、
  幂等、无重试/无缓存的 `knowledge.search` fixture，并要求一次 ToolCall、一次成功执行
  和精确终止标记；
- CLI 新增显式 `adapter_protocol` scope，必须同时提供真实调用确认与精确
  `max_calls=3`，OpenAI-compatible SDK 自动重试固定为 0；公开结果只保存安全错误码、
  调用/Token/响应计数和 SHA-256，不保存 Prompt、模型原文、observation 或原始异常；
- 当前本地完整回归：`415 passed, 103 subtests passed`；协议/CLI/结果合同聚焦回归
  `22 passed`；compileall 与 diff check 通过；
- 协议控制器提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51` 的 GitHub Actions
  run `31625669630` 全部通过后，只执行一次真实 `adapter_protocol/3`：A1 使用 1 call，
  A2 使用 2 calls，总计 3/3，二者均 passed，`admitted=true`；
- 真实 A1 为 427/59 tokens、2344 ms；A2 为 562/36 tokens、5360 ms，finish sequence
  为 `tool_calls -> stop`，工具调用/执行均为 1；未取得可靠单价快照，因此成本保持 null，
  不伪造为 0。
- `DomainSkillSliceRunner` 已离线组合真实 `recent-form-review` Catalog/Router/Boundary、
  Context Builder、AgentLoop、本地 `knowledge.search`、唯一 ReviewHarness 和 typed output；
  历史协议结果必须 `admitted=true`、精确 3 calls、Provider/model 一致，并记录文件 SHA-256；
- Agent 与 Harness 共享 `ExternalCallBudget(max_calls=4)`；happy path 为 Agent 2 calls +
  Evaluation 1 call，剩余 1 call 只允许 Evaluation 格式修复；revision 后再评测会在进入
  底层 Provider 前失败关闭，准入专用 SDK/Tool 自动重试均为 0/单次尝试；
- 真实领域 CLI 必须显式确认累计 `max_calls=7`，只允许批准结果目录，要求干净已提交的
  工作树并拒绝覆盖既有领域证据；Harness 原文只写系统临时目录，公开报告不保存
  Prompt、模型正文、Observation、原始 request ID、异常或 API Key；
- 领域控制器聚焦回归为 `23 passed`，相邻纵向比例回归为
  `141 passed, 29 subtests passed`，完整回归为 `430 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness SDK/敏感文件边界和 dry-run 均通过。所有领域证据仍为
  Fake Provider 离线证据，仓库中尚无真实领域结果文件。
- 领域控制器提交 `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 已推送到
  `origin/main`；GitHub Actions run `31657764638` 对该精确 SHA 的全测试、两套 RAG、
  compileall、Harness SDK/敏感文件边界和 dry-run 全部通过，CI 未调用真实 Provider。
- 真实 recent-form 领域切片随后只执行一次：使用 1 个领域 call，累计调用为 4/7；
  该计费请求没有形成进入 Agent 结果的统一 `ChatResponse`，因此 response/tool/evidence
  均为 0，也没有进入 Evaluation；公开结果为 `admitted=false`、
  `knowledge_round_trip_incomplete` 和 terminal `degraded`；
- 这次 `degraded` 证明确定性 fallback 在真实外部失败时阻止了未经评测草稿发布；它不
  证明 GLM 报告质量。当前脱敏证据不能继续区分 Adapter 规范化拒绝或其他统一响应前的
  Provider 错误，且没有质量分或可靠成本估算；
- ADR-0012 据此分层收尾 5D-6b：Zhipu Adapter 最小 structured/tool 协议准入，
  GLM-5.2 recent-form 领域能力不准入；不重跑、不临场调 Prompt、不立即接入第二
  Provider，真实失败进入 5D-7 的评测与错误归因设计。
- ADR-0014 让后续领域实验强绑定 Prompt/Context 语义身份：组件层覆盖 Skill Manifest/
  Instructions、Context Policy、`knowledge.search` 合同、Evaluation Schema/事实投影与
  prompt builders；案例层覆盖输入 Artifact、typed options、实际 section、最终消息与
  Context 预算；
- 冻结快照 `recent-form-prompt-context-v1` 的自摘要为
  `88af3ed94e2458dc67e92c311de3543ca23c5923c0591ad83cfa3d2db6fd95e0`；
  Domain Dataset/Candidate/Result 已升至 Schema 1.1 并强绑定该 ID/SHA；
- `prepare_domain_e2e_experiment.py` 会在 Provider 前从当前真实 Catalog、Router、
  ExecutionBoundary 与 ContextBuilder 重建快照，核对冻结快照与 Dataset 后才产生
  `admitted=true`；当前 admission 的 `external_provider_calls=0`；
- 快照和 admission 只保存安全元数据及摘要，不保存 Prompt、玩家事实、模型正文、
  Tool Observation、异常、request ID 或 Key；它们是实验前置身份，不是 5E Trace。
- Batch B 聚焦测试为 `20 passed`，相邻纵向回归为 `87 passed, 4 subtests passed`，
  完整回归为 `450 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/
  tracked-data、dry-run、快照正文脱敏、治理和 diff check 均通过；
- Domain E2E 1.1 基线与 admission 已从 CLI 临时输出逐字节复现；功能提交
  `e56b00091ef2ab299af692e902945b8342fbc99e` 已推送，GitHub Actions run
  `31690698734` 对该精确 SHA 全部通过。
- ADR-0015 采用脚本 Provider 驱动真实本地控制流，而不是继续手填 Candidate 或立即
  调用真实模型；新增 Schema 1.2 `offline_executable` Candidate，要求零外部调用且每个
  案例都有安全 provenance SHA-256；
- Batch C 的 7 个 development 场景均先通过 Batch B admission，再真实运行 Catalog/
  Router/Boundary、ContextBuilder、AgentLoop、`knowledge.search`、ToolRuntime、本地混合
  RAG、Evidence 构建和唯一 ReviewHarness；只有 Provider 响应为确定性脚本；
- 可执行场景覆盖成功、缺工具、错误 90% 胜率、未知 `[K999]`、用户注入、RAG 注入和
  Evaluation 漏判注入。最后一个场景实际被 Harness 发布，再由分层评测标记
  `unsafe_publication`，因此 1/7 不安全发布率是保留的开发 Bad Case，不是通过率；
- Candidate 中的 fact/citation/injection 结论从实际 draft、evidence Artifact 和 canary
  probe 提取，公开 Candidate/Result 不保存 canary、错误事实、Prompt、报告、工具原文、
  request ID、异常或 Key；CLI 重跑与冻结文件逐字节一致，外部调用为 0；
- Batch C 聚焦/相邻测试为 `25 passed`；完整回归为
  `455 passed, 103 subtests passed`。两套 RAG、compileall、Harness SDK/tracked-data、
  artifact 脱敏、治理、diff check 和 Harness dry-run 均通过；
- 这些结果证明离线实验接线和本地发布边界可复现，不证明任何真实 Provider 的领域
  质量或通用抗注入能力；当前 Evaluation Schema 也没有专用 injection issue category。
- Batch D 入口审计确认，现有 `ChatEvaluationAdapter` 只把确定性 fact pack 与待审报告
  放入 Prompt；虽然 `EvaluationRequest` 携带 `KnowledgeEvidence`，Evaluator 当前看不到
  用户原话、实际知识证据或信任标签。原地增加 issue 枚举既缺输入又会破坏 Batch A-C
  的 `coach_evaluation@1.0.0` 历史身份；ADR-0016 因此保留 1.0.0，D1-D2 已离线迁移并
  接入 1.1.0 安全评测合同与 blocking policy；D3 已创建独立 held-out，已知 canary 只
  作为实验 oracle，不进入生产关键词黑名单；
- ADR-0016 还冻结了后续门：D1/D2 离线迁移通过并冻结后才创建独立 held-out；真实首轮
  只比较同一冻结合同下的正常、用户注入和知识注入 3 场，每 Provider 每场最多 4 calls、
  领域最多 12 calls、`max_revisions=0`、SDK retry 为 0；第二 Provider 另需新 ADR 与最多
  3-call Adapter 协议门；
- ADR-0017 原先以协议成本为主选择 V4 Flash；经用户追问和 D5 目标复核，ADR-0018
  保留其历史并将唯一候选更正为 DeepSeek 官方 `deepseek-v4-pro`。独立 Adapter、
  non-thinking、最多 3-call 协议 + 12-call 领域预算、每案例 4000 tokens、每请求最多
  1024 output tokens、GLM ¥0.50 与全局/单 Provider 停止规则不变；按 Pro 峰值价把
  DeepSeek 停止线更正为 `$0.10`。选择候选不等于已经实现、调用、准入或设为默认模型。
- ADR-0019 保持当前 Pro-only 5D-7 准入门不变，并纠正未来 Flash 分层的归属：该工作
  最早在 5P 后、默认等待阶段 6 的真实 API 调用、Trace、成本或延迟 Bad Case，以横向
  Provider 优化门比较 Pro-only、Flash-only 和 Flash 默认/Pro 有界升级；5F 仍只负责
  Pi / Claude Agent SDK Runtime 采用实验。当前不增加 Flash 配置、调用或自动路由。
- D4 聚焦回归为 `68 passed, 15 subtests passed`，完整回归为
  `460 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/敏感文件边界、
  Harness dry-run、文档密钥模式扫描、governance 和 diff check 均通过，外部调用为 0。
- D5 新增独立 `DeepSeekProvider`，冻结 `https://api.deepseek.com`、
  `deepseek-v4-pro`、non-thinking、non-streaming、JSON mode、请求级工具别名和严格
  finish/usage/错误语义；它没有注册为产品默认 Provider，也没有复用 Zhipu Adapter
  冒充厂商无关实现；
- D5 让 `AgentRunStatus`、`AgentStopReason` 与安全 `error_code` 组成的不可变失败观察
  穿过 draft preparation 接缝。真实 AgentLoop Provider failure 测试证明 Harness 仍只
  返回确定性 `degraded`，同时上层能区分认证等安全来源，不保存 Prompt、模型正文或
  原始异常；
- 实验 ledger 在 I/O 前占用调用并检查 scope/cumulative call、每请求 output、累计
  observed Token 与估算金额；SDK 失败不退还调用，usage 缺失不按 0 结算，任一
  `unsafe_publication` 会触发全局停止。它是应用层实验门，不是厂商账户硬限额或 5E
  统一 Trace；
- D5 no-I/O preparation 只核对干净 Git SHA、公开 CI SHA、冻结 held-out 与
  Prompt/Context snapshot；不加载 `.env`、不读取 Key、不创建 OpenAI client、不运行
  held-out。Fake SDK 的 3-call 协议回归只证明 Adapter 映射和控制流，不证明 Pro 的
  真实能力；
- D5 聚焦/相邻回归已经通过，当前完整回归为 `505 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness dry-run、SDK/tracked-data 边界、governance 与 diff
  check 均通过。功能提交 `e68a8e4542ed72d31d5d46e569a11d9292048540` 的 GitHub
  Actions run `31764109304` 全部通过；同一干净 SHA 的 no-I/O preflight 随后通过，
  `external_provider_calls=0`、`held_out_executed=false`。

当前不能声称：

- GLM 或任何真实 Provider 已完成领域 Skill/Harness 准入；当前生产 `ZhipuProvider`
  只通过最小 Provider-neutral structured/tool 协议切片，真实近期复盘领域链路已尝试
  但未准入；
- 真实模型生成的新 Coach 报告已经通过当前端到端领域评测；本次没有统一响应进入
  Agent，也没有草稿、知识证据、Evaluation 或质量分；
- 默认 ContextSizer 等于真实厂商 tokenizer 或真实 Token Usage；
- trust/JSON 分层已经彻底解决 Prompt Injection；
- Batch C 的脚本 Provider/canary 已证明真实 GLM、DeepSeek 或 Qwen 抗注入；
- DeepSeek V4 Pro 已通过领域 Skill/Harness 准入、成为产品默认模型或普遍优于
  Qwen/GLM；真实领域 held-out 已运行但未准入，当前只准入最小 structured/tool
  Adapter 协议；
- 已经实现 Tool Observation compaction，或协作式 deadline 能硬中断任意阻塞函数；
- 路由对自然语言具有充分泛化能力；
- 小型合成 holdout 已证明路由对自然语言充分泛化；
- 已把 holdout 失败用于调节 Router 规则；
- 已实现 LLM Router fallback 或修复设备域假朋友；
- Router 已执行 Skill、Tool、Harness 或模型调用。
- 5D-1 的内容承诺已经等同于真实 Harness Artifact 落盘或 Agent 执行。
- `user_utterance` 已通过统一 Runtime/Trace 与最初 `RouterRequest` 形成不可变来源链。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-7、Stage 8 entry/8A/8B/8C/8D 已关闭；8D EvidenceBundle、no-I/O adapter、public projection 与现有产品回归已验证；8E preflight 已保存真实 Riot/OP.GG body-free 证据，并记录 mid replay 的严格 adapter 拒绝 | 本地普通测试或一次真实 gate 等于正式 Auth/SSE/前端、真实 refresh 或生产 SLA |
| 项目理解 | Stage 8 entry、8A、8B、8C、8D 均有 walkthrough/ADR/设计材料；8D 已补齐 provenance/freshness/join/conflict/gap/claim 的初学者解释 | 持久材料存在等于用户已能独立讲解所有融合代码；owner mastery 仍需复述、读码和运行验证 |
| 参考资料 | Saber/Sea 的 lease/event/checkpoint 思想只作选择性参考；8B 唯一 holdout 保持 SHA `944258...445e8` 且未重跑；8E 已真实观察 Riot/OP.GG，mid replay 暴露远端内容与严格 grammar 的差异；README 样本研究按 RQ-085 留到 8F | 引用参考思想等于复制其 Runtime/DAG，或 Multi-Agent reject 已被撤销；一次外部观察也不等于长期 freshness/SLA |
| GitHub/部署 | 8C `2df5349/32587659678` 与 8D `a274b7f/32598480400` 的 pytest、真实 PostgreSQL、Linux package 均 exact-SHA 全绿；正式 Auth/SSE/前端/备份/生产 SLA 仍未实现 | 本次公共闭环等于 8E 产品化、正式 Auth/SSE/备份或生产 SLA |

当前 Riot 账号身份边界：官方 LoL routing 列表不含中国大陆 CN；外服 Riot ID 查询只能形成公开账号
引用。用户选择“这是我的账号”在正式 RiftCoach Auth、安全绑定的 RSO callback 和精确 PUUID match 前
只能标记为 `claimed_self`，不得表述为已验证授权。owner-global 偏好按 owner 隔离，玩家相关的私人
Session/Memory 再按 owner-local player subject 隔离。RQ-062 已确认 MVP 同时提供受限
`public_observed`：它只承载公开比赛分析与 owner-local 观察备注/趋势，不冒充被观察者本人的偏好或训练
完成度；任一关系都不增加 Riot 数据权限或跨 owner 合并私人 Memory。

## 已裁决的首批 Skill 与事实审查边界

2026-08-05 的讨论同时确认了两点：

1. 先用一个 `recent-form-review` 样板稳定 Skill Contract 和 Router；
2. 首批宏观能力仍包含近期复盘、单局复盘和报告事实审查，并曾把三者都称为
   Skill，要求在 5C-4 后补齐再完成真实多 Skill 路由评测。

源码级复核发现，事实审查并不是缺失的第三个工作流：`EvaluatorStep`、
`ChatEvaluationAdapter` 和 `ReviewHarness` 已经提供类型化输入输出、复用入口、
修订预算和强制发布门禁。把它再包装成 Skill 只会复制合同。

- `recent-form-review`：已存在的用户可路由 Skill；
- `single-match-review`：已建立的第二个用户可路由 Skill；
- 报告事实审查：继续作为 Harness `EvaluatorStep` 强制执行，不是 Skill。

未实现的调用模式合同和 `report-fact-check` Skill 已在写代码前取消。实施顺序修正
为单局 Skill、真实双 Skill 路由评测、模型兜底决策。详细裁决见 ADR-0008 和
ADR-0009。

## 2026-08-06 阶段漂移事件

### 发生了什么

原计划明确包含 5C-1 至 5C-6，但一次实现批次把 5C-3 的代码、5C-4 的部分
拒绝/歧义行为和 5C-5 的初步开发评测一起完成后，文档被直接更新成“5C
完成，下一步 5D”。这把“代码已提前存在”误写成了“原检查点已经逐项完成”。

### 根因

- 原始 5C-1 至 5C-6 清单只存在于长对话，没有写进仓库；
- 旧 `.planning` 任务停在 2026-08-01，且没有 `.active_plan`；
- 没有根级 `AGENTS.md` 强制恢复上下文和同步状态；
- 多份状态文档并存，却没有唯一当前状态源；
- 实现计划错误地把一个批次的测试通过当成整个 5C 的完成条件。

### 修复原则

- 恢复原有 5C-1 至 5C-6 边界，不回滚已经写出的有效代码；
- 提前实现的内容回到原子阶段逐项讲解、复核和验收；
- 以后“继续”只推进本文件列出的唯一下一步；
- 每次状态变化同时更新当前状态、活动计划和冲突文档。

### 持久化与自动保护

- 本文件头部的机器可读元数据与正文共同构成同一个唯一状态源；
- `.planning/.active_plan` 指向当前任务的计划、发现和进度三份持久记忆；
- `docs/requirements_change_log.md` 追加记录跨轮次长期要求，不静默覆盖旧决定；
- `scripts/check_project_governance.py` 在本地和 CI 核对当前检查点、活动计划、
  九阶段编号、需求编号和工作约束；任何冲突都先阻止功能推进；
- 自动检查降低再次漂移的概率并让错误可见，但不能替代用户对阶段验收的确认。

## 下一检查点的范围

RQ-040 已解除 RQ-039 的暂停；`5P-entry-design` 已由 `49841ec` / Actions `31985199623`
完成 exact-SHA 公共验证。源码审计确认产品输入（Riot ID/少量选项）与 Runtime 输入（selected
Skill、Summary、确定性报告、Artifact binding、policy）之间必须有 Application Service；
同时 5D 退出证据明确把 Prompt Program V1 放在 5P，而 Runtime prompt profile 仍是硬编码身份。

因此 ADR-0032/0033 分别接受：

1. 复用既有 component fingerprint 建立版本化 Prompt Program/Catalog/drift gate，让真实
   Skill、Context、knowledge tool、Evaluation 1.1 与 Revision 组合绑定 prompt identity；
2. 采用薄 FastAPI Adapter + `RecentReviewApplicationService` + 现有 `AgentRuntimeV1`，并以
   body-free file receipt/query projection 复读 Trace/manifest/final Artifact。

5P 已固定为 5P-1 产品合同/typed compiler、5P-2 Prompt Program/composition、5P-3 domain/
application service、5P-4 receipt/query、5P-5 FastAPI/no-I/O vertical slice、5P-6 exit review。
entry design 没有安装 FastAPI、实现产品代码、读取 Key、调用 Riot/Provider 或运行 held-out。
5P-2 已由 `0a9651f` / Actions `31988837293` 完成 exact-SHA 公共闭环；RQ-043 随后恢复并完成
`5P-3-domain-application-service`，提交 `4bd5c83` / Actions `31998739178` 已公开通过。
5P-4 receipt/query 已由 `932a863` / Actions `32002994441` 完成 exact-SHA 公共闭环。5P-5
thin FastAPI/no-I/O vertical slice 又由 `6d1e5b0` / Actions `32005648179` 完成 exact-SHA
公共闭环并正式关闭；5P-6 的 exit matrix/review 与全部门禁裁决为
`close-with-deferred-boundaries`，并由 `8c8acc6` / Actions `32010604551` 完成 exact-SHA
公共验证。整个 5P 正式关闭；canonical 只交接到 `5F-entry-design` 准备状态，等待用户再次明确
继续，不自动实施 SDK 对照或进入阶段 6。

本节后续保留从 5C 到 5D 的历史范围账本；其中旧“下一步”只表示当时顺序，不覆盖本文顶部的
canonical checkpoint。

`5C-5-prep-1 Skill Invocation Contract` 与 `5C-5-prep-3 report-fact-check Skill`
已在功能代码开始前由 ADR-0009 取消，并保留在历史记录中。

`5C-5-prep-2` 已完成：单局 Skill 明确了输入、输出、触发/排除边界、工具权限、
预算、步骤和成功标准，Catalog 现在有两个真实用户候选。

`5C-5` 已完成：旧单 Skill 基线原样归档；development v2 以 23/23 冻结规则；
independent holdout v1 随后只运行一次并得到 11/12。唯一失败是设备语义假朋友，
其期望拒绝、实际选中近期复盘，结果已原样保留且不会用于调节本版本规则。

`5C-6` 已完成：ADR-0010 决定 V1 暂缓 LLM Router fallback。单一小型合成 Bad
Case 不足以抵消模型带来的结构化输出、延迟、成本和故障复杂度；现有 GLM Adapter
也只声明 `text_chat`。未来先采用类型化入口和澄清，再以新鲜数据、新 holdout、
结构化输出与质量/成本证据重开模型实验。

`5C-exit-review` 已通过：完整证据、修复项、限制、框架中立边界和面试安全表述见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`。5C 现已完成。

`5D-entry-design` 已完成。采用 ADR-0011：AgentLoop 负责白名单工具调用和草稿准备，
`ReviewHarness` 仍是唯一评测、修订和发布控制面；通过 `DraftPreparationStep` 接缝
同时兼容旧顺序 Retriever/Generator 和新 Agent 路径。完整设计见
`docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`。

`5D-1 Skill Run Boundary Hardening` 已完成：两个 Skill 的关键文本合同、selected
name/version、共享安全 run ID、Harness 规范输入字节摘要和 Catalog-backed 执行前
校验均已有 TDD 证据。该内容绑定尚未创建真实 Harness Artifact，也没有调用模型或
工具。

`5D-2 Context Builder V1` 已完成：`ValidatedSkillExecution` 被投影为 trust-typed
sections，经 Manifest 硬上限做 required-first、optional whole-section 选择，再渲染为
现有 system/user `ChatMessage`。近期与单局使用不同事实 allowlist；初始 citation
逐条作为 data-only section；设计和 TDD 证据见
`docs/plans/2026-08-07-context-builder-v1-design.md` 与对应 implementation plan。

`5D-3 Skill Run Compiler & Budget Enforcement` 已完成：`AgentRunCompiler` 从已验证
Manifest 与 `ContextBundle` 编译现有 `AgentRunRequest`，不接受权限或预算 override；
完整消息 sizer 覆盖 ToolCall/Tool result envelope；AgentLoop 在每次 Provider 调用前
执行累计 Context 门禁，并把 Manifest timeout 作为 Provider/Tool 共用的协作式总
deadline。设计与 TDD 证据见
`docs/plans/2026-08-07-skill-run-compiler-budget-design.md` 与对应 implementation plan。

`5D-4 Evidence-Aware Agent Draft Preparation` 已完成：知识 payload 转换逻辑已从
旧 `LocalRagAdapter` 抽成共享纯函数；`SkillAgentDraftPreparer` 将受限 AgentLoop 的
最终文本降格为 `CoachDraft`，只从实际成功的 `knowledge.search` 执行记录构造
`KnowledgeEvidence`。两个真实 Skill 已用 Fake Provider + 真实本地知识工具走通；
设计和 TDD 证据见 `docs/plans/2026-08-08-skill-agent-draft-preparation-design.md` 与
对应 implementation plan。该检查点没有运行 Harness 或真实 Provider。

`5D-5 Harness Composition & Typed Terminal Output` 已完成：`ReviewHarness` 只依赖
统一 `DraftPreparationStep`，旧路径由顺序 Adapter 兼容；`SkillReviewExecutor` 把
5D-4 的 Agent draft/evidence 交给同一评测、修订、发布/降级/拒绝控制流；最终 Skill
Output 只从 terminal Manifest 与完整性校验通过的 Artifact 构造。两个真实 Skill
已通过 Fake Provider + 真实本地知识工具的完整组合测试。设计和 TDD 证据见
`docs/plans/2026-08-08-skill-harness-composition-design.md` 与对应 implementation plan。

`5D-6a Structured Output Contract` 已完成：`ChatRequest` 可以显式携带冻结的
`StructuredResponseContract`，能力协商会要求 `STRUCTURED_OUTPUT`；严格 Pydantic
Evaluation 模型同时提供 JSON Schema 和本地验证；非法 JSON、额外/缺失字段、错误嵌套
类型、非法枚举、fence 和截断都会被拒绝。最多允许一次携带同一合同的格式修复，第二次
失败返回安全错误；Harness 只会 deterministic fallback 或 rejected，不能发布 Agent
草稿。该检查点当时保持 `ZhipuProvider` text-only；5D-6b 现已补齐离线厂商映射，
但 Fake SDK 证据仍不等于真实 Adapter 或领域 Skill 准入。

`5D-6b Real Provider Capability Gate` 已由 ADR-0012 收尾。P1-P5 与精确 3-call
Adapter 协议切片通过；真实 recent-form 领域切片只尝试一次，在一个计费请求后未形成
统一 `ChatResponse`，没有工具证据或 Evaluation，并安全降级。结论是最小协议能力
准入、领域能力不准入，而不是 GLM 整体成功或整体失败。

当前检查点为 `5D-7 Prompt/Context & Domain E2E Evaluation`。Batch A 已把上述真实
Bad Case 纳入 development，并建立分层合同和 10 案例离线基线；Batch B 又以 ADR-0014
冻结组件级与案例级 Prompt/Context 语义身份，让 Dataset 1.1 和后续候选绑定相同
Skill、Context、知识工具及 Evaluation 合同。离线 admission 会在 Provider 前重建并
精确核对快照，当前外部调用为 0。它只证明实验条件可重复，不证明 Prompt、真实模型、
未知注入或报告质量已经通过。

Batch C 已用 ADR-0015 建立七场 `offline_executable` development 基线。每场都先经过
Batch B admission，再由 Scripted Provider 驱动真实 Skill/Agent/Tool/RAG/Harness；
事实、引用和注入检查从实际运行产物提取。一个 Evaluation 漏判场景真实发布了含 RAG
canary 的报告，并被分层评测标记为 unsafe publication，明确证明 Harness 的确定性发布
决策仍依赖 Evaluation 输入质量。该结果只验证实验接线，不评价真实模型。

Batch D 的 D1-D2 已完成：保留 `coach_evaluation@1.0.0` 历史路径，新增并接入
`coach_evaluation@1.1.0` 安全评测输入/输出、`prompt_injection` blocking issue 与不可
修订的 Harness policy；secure offline executable development 7 场结果为 task outcome
accuracy `1.0`、failure classification accuracy `1.0`、unsafe publication rate `0.0`、
external calls `0`。D3 已在合同、Prompt、snapshot 与规则冻结后创建 3 场独立 held-out，
带 `calibration_excluded=true` 和无污染声明；D3 只完成创建与生命周期测试，没有运行
held-out。上述结果不证明真实模型质量或通用抗注入能力。

D4 已由 ADR-0018 更正并收尾：ADR-0017 的 Flash 选择保留为历史，唯一有界第二
Provider 候选改为 DeepSeek V4 Pro；同任务比较、协议/领域分层准入和成本/停止规则已经
冻结。D5 已离线实现独立 Adapter、安全失败归因、预算 ledger 与 no-I/O preparation；
Fake SDK 和 scripted response 下的协议与失败回归通过，外部调用为 0。Qwen3.8 Max 与
V4 Flash 暂缓，不代表质量较差。ADR-0019 进一步确认 Flash 不进入当前 5D-7，也不占用
5F；未来模型分层最早在 5P 后、默认于阶段 6 由真实产品成本/时延证据触发。

D5 real-gate execution seam 提交 `076a5e3558cd68abb545cebdc2542c973b020768`
已通过 GitHub Actions run `31767405927` 与同 SHA no-I/O preflight；随后只执行一次真实
DeepSeek V4 Pro 协议门。A1 strict structured contract 与 A2 Agent tool round trip
均 passed，总计 3/3 calls、1428 tokens、估算 `$0.00221496`，无 Provider/global stop，
`admitted=true`。脱敏结果 SHA-256 为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
该证据只准入最小 Adapter 协议，不准入领域报告质量或产品默认模型。5D-7 的唯一
后续先完成了冻结三场领域 held-out 的执行接缝设计与离线 TDD；本批没有调用 Provider，
且不得进入 5D exit review 或 5E。协议结果归档提交
`ba1379db6b573d07e6cbe3bd27b9561ea9ca9f6e` 已通过 GitHub Actions run
`31779362817` 的精确 SHA 公开 CI。

领域 held-out 执行接缝现在把控制面和数据面分开：
`prepare_deepseek_domain_heldout_run()` 不接收或构造 Provider，先核对当前 preparation、
冻结 Dataset/Snapshot、执行计划摘要与已准入协议字节摘要；只有 admission 产生且结果
文件已独占预留后，后续入口才可读取 Key/构造 Provider。`ProviderResourceLedger` 可从
旧协议账本继续，新增 protocol/domain scope Token 和单案例 calls/Token 三层边界；领域
协调器逐例生成 ledger-derived 资源、安全语义观测和既有分层 Evaluation，任一 Provider、
案例 mismatch 或 unsafe publication 会停止剩余案例。合成 Fake Provider/Executor 回归
证明第 5 个单例调用在 I/O 前拒绝、首错后剩余 skipped、异常正文不落盘、结果不可覆盖；
真实协议文件仍严格解析为 3 calls，SHA-256 仍为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
执行接缝提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已通过 GitHub Actions
run `31785253957` 的 exact-SHA 公开 CI。后续生产装配批已在零外部调用下把 held-out
修正为 1.1.0 安全成功门，冻结输入计划并接入生产 Executor/CLI；功能提交
`eb198354b3186f25b7d0455d7ed28725bc17e234` 已通过 GitHub Actions run
`31799394506` 的 exact-SHA 公开 CI。用户确认后真实领域门只执行一次；首例返回
`unsupported_parallel_tool_calls` 并由 Adapter fail closed，Harness 降级，后两例
skipped，领域 `admitted=false`。当前结果不可重跑；并行 ToolCall Bad Case 需回到
development 独立处理，仍不得直接进入 5D exit review 或 5E。

ADR-0022 的本地 development TDD 随后移除了 DeepSeek Adapter 对调用数量为 1 的额外
限制，但保留唯一 ID、已声明别名、严格 JSON object、finish reason 和 capability 校验。
AgentLoop 用四类测试固定“整批预算/白名单/重复预检后才顺序执行”的零副作用语义；新的
development 案例又通过 Fake DeepSeek SDK 真实串联本地 RAG、Evidence、Secure
Evaluation 1.1 与 ReviewHarness 并安全发布。完整回归为 `551 passed, 103 subtests
passed`，两套 RAG、compileall、Harness dry-run、安全边界和治理门通过，外部调用为 0。
这些证据只证明执行链兼容性；exact-SHA 公开 CI 已由 `037a47f` / `31817798170` 通过，
但仍不准入真实模型领域质量。ADR-0024 已在其后完成新鲜门设计。

### 2026-08-15：GLM-5.3 模型迁移规划边界

官方 GLM-5.3 文档已确认该模型存在；页面说明 Coding Plan 已开放，普通模型 API 将
逐步上线，并明确 GLM-5.3 始终启用 thinking，不能继续发送当前 Zhipu Adapter 固定的
`thinking.type=disabled`。因此 GLM-5.3 不是只改 `.env` 的透明升级。

本次只记录 ADR-0023 和迁移设计，不读取 Key、不调用 Provider、不修改默认模型，也不
改变 DeepSeek 当前实验。GLM-5.2 的历史结果保持只读；DeepSeek Adapter、DeepSeek
协议/领域结果、预算和 Dataset 1.1.0 保持只读且不可重跑。

GLM-5.3 的未来顺序固定为：当前 5D-7 新鲜领域采用门剩余离线 TDD/公开 CI 完成后，
再做 G53-0 可用性与 endpoint 审计、G53-1 Zhipu thinking profile 离线 TDD、G53-2
公开 CI、G53-3 最多 3-call 协议门、G53-4 新鲜领域采用门。GLM-5.3 通过新鲜领域门前
不替换 GLM-5.2 默认值，不进入自动模型路由，不影响 DeepSeek。

### 2026-08-15：DeepSeek 新鲜领域采用门设计

ADR-0024 选择复用已有 no-I/O admission、薄协调器、预算 Provider、production Executor、
分层 Evaluator 和唯一 ReviewHarness，不重写第二套控制面。旧 Dataset 1.1.0、旧输入
计划、真实 3-call 协议和真实拒绝结果继续按精确 bytes 只读保存，禁止复制改名或重跑。

新门必须在合同实现和规则冻结后才创建新的匿名 fixture、Dataset、输入计划与三个实际
案例的 Prompt/Context 摘要。Fresh-Gate 1 先只用合成 development 数据做向后兼容合同、
历史证据链、身份漂移、预算/停止、Key-last 和脱敏 TDD；通过 exact-SHA CI 后才进入
正式新 held-out 创建批。

历史已观察 3 次协议调用和 1 次失败领域调用；新鲜领域范围未来每例最多 4 calls、总计
最多 12 calls、4000/12000 observed tokens、每请求 1024 output、金额停止线 `$0.10`、
零 SDK/Tool retry、`max_revisions=0` 和首错停止。该预算不是当前调用授权。本设计批没有
读取 Key、调用 Provider、创建新 held-out、修改 Prompt/Evaluation/Harness 或进入 5E。

设计提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已推送；GitHub Actions run
`31859717836` 对该精确 SHA 的治理、完整 pytest、两套 RAG、compileall、Harness
boundary、tracked-data 和 dry-run 全部成功，CI 没有调用真实 Provider。

### 2026-08-15：DeepSeek Fresh-Gate 1 本地离线 TDD

输入计划合同已向后兼容扩展为 V1.0/V1.1：旧 V1.0 计划仍按精确旧字段读取；V1.1 必须
同时声明 Prompt/Context snapshot ID/SHA，并按案例顺序提供一一对应的 Context 摘要。
Prompt/Context snapshot V1.1 会让三个显式 development case 分别经过真实 Catalog、
Router、ExecutionBoundary 与 ContextBuilder，仅保存 section/message/输入摘要，不保存
用户、fixture、注入或 Prompt 正文；V1.0 快照仍可逐字节复现。

新增的 historical evidence 会严格复读旧协议和旧拒绝结果 bytes，保留 `3 protocol +
1 rejected domain = 4 historical calls`；协议已知资源保持 1303/125/1428 tokens 与
`$0.00221496`，规范化前失败调用的 Token/费用则标为 unknown，不会被旧公开记录里的
统一账本零值误解释为已知零。该证据同时锁定多 ToolCall 修复提交
`037a47f...` 与 Actions run `31817798170`。

`FreshDomainDevelopmentAdmission` 只接受 development Dataset、V1.1 plan、三个当前/
冻结 Context 摘要、历史证据和 `code_sha == public_ci_sha` 的零调用 preparation；函数
签名没有 Provider/API Key，输出固定 `provider_construction_authorized=false`、
`external_provider_calls=0`、`held_out_executed=false`。聚焦测试 33 个、相邻 51 个，
完整回归 `568 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/
tracked-data boundary 和 dry-run 已通过。期间实施计划最初写了三个不存在或错误参数的
外围命令，已按 `.github/workflows/tests.yml` 更正并重跑；这是验证命令错误，不是产品
回归。当前没有新 held-out、Key、Provider call 或真实领域结果。实现提交
`adba965a7f7fb4293020502b4440e9880633e571` 已推送，GitHub Actions run
`31860874440` 对精确 SHA 的治理、完整 pytest、两套 RAG、compileall、Harness SDK/
tracked-data boundary 与 dry-run 全部成功，CI 未调用 Provider。下一步单独进入
Fresh-Gate 3 创建/冻结全新资产，仍不运行 held-out。

### 2026-08-15：DeepSeek Fresh-Gate 3 本地资产冻结

新的 `domain-e2e-v2-secure-held-out` 在 Fresh-Gate 1/2 公开冻结后才创建，包含正常复盘、
用户数据指令边界和知识数据指令边界三个案例。它与已消费旧题不复用 fixture bytes、
case/run ID、用户措辞、知识注入正文或 marker；Dataset 为 `held_out` 且
`calibration_excluded=true`，没有污染记录。

新的 V1.1 input plan 只保存实际输入和 fixture/Context commitment，Dataset 单独保存
oracle；production Executor 仍只接收 `case_id + provider`。三个实际案例均通过当前真实
Catalog、Deterministic Router、SkillExecutionBoundary 和 ContextBuilderV1，生成
`recent-form-prompt-context-v1-2` 的 body-free 摘要；Snapshot 自摘要为
`79974fb2089f6c73d66d35d13d419bf9b70e147d5c6890dccf929dc114a50011`。

本地聚焦回归 `39 passed`，完整回归 `574 passed, 103 subtests passed`；两套 RAG、
compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 已通过。
正式结果文件不存在，新增 Provider calls 和 held-out executions 均为 0。当前只完成本地
资产冻结。资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已推送，GitHub
Actions run `31861960565` 对精确 SHA 的治理、完整 pytest、两套 RAG、compileall、
Harness SDK/tracked-data boundary 与 dry-run 全部成功，CI 未调用 Provider。

Fresh-Gate 3 至此完成。唯一下一步为 Fresh-Gate 4 入口批：将新资产绑定到 held-out
no-I/O admission 和现有生产 CLI，先做离线 TDD 与新的公开 CI；该入口批仍不读取 Key、
调用 Provider 或运行 held-out，真实 12-call 上限需在后续再次明确确认。

### 2026-08-15：DeepSeek Fresh-Gate 4 运行入口本地完成

Fresh-Gate 4 采用版本化控制面，不复制第二套 Agent/Executor：

- `FreshDomainHeldOutAdmission` 绑定旧协议与旧拒绝结果 bytes、ADR-0022 修复 CI、
  Fresh-Gate 3 资产 commit/CI、当前 code/public-CI、新 Dataset/plan/fixture 和三个逐案例
  Context commitment；其 no-I/O 结果固定 Provider calls 为 0、held-out 未执行，且单凭
  admission 不授权 Provider 构造；
- 旧 Adapter 协议的 Context 身份与新领域 Context 可以不同，因为两者回答不同问题；
  旧协议模型、准入状态、资源和精确 result SHA 仍必须一致，新 Context 由 readmission
  独立绑定；
- 现有 `run_deepseek_domain_heldout.py` 使用 V2 active profile，增加 `--prepare-only`；
  实际顺序保持 output conflict → no-I/O admission → output reserve → env/Key → Provider →
  bounded execution；
- 新 `FreshProviderDomainExperimentRecord` envelope 同时保存完整 readmission 和原领域分层
  结果；旧 `ProviderDomainExperimentRecord@1.0` 与历史 JSON 未改义、未覆盖；
- Fake Provider 在临时目录完整经过 production Executor、RAG、Evaluation 1.1 和 Harness；
  正常路径 3 例共 9 次合成调用并通过，受控鉴权失败路径只调用 1 次、后两例跳过且结果
  不可覆盖。这些是离线控制流证据，不是 DeepSeek 质量或真实 held-out 证据。

聚焦相邻回归 `93 passed`，完整回归 `580 passed, 103 subtests passed`；两套 RAG、
compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
真实结果文件不存在，API Key 未读取，外部 Provider calls 和真实 held-out executions 均为
0。唯一下一步是提交/推送并验证本实现的 exact-SHA CI，随后在干净同 SHA 上执行一次
真实 `--prepare-only`；真实模型运行仍需再单独确认。

实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过 GitHub Actions run
`31863341338` 的 exact-SHA 全部门禁。随后在同一干净 SHA 执行真实 `--prepare-only`，
输出为 `no_io_admitted=true external_provider_calls=0 held_out_executed=false`；命令未创建
正式结果文件。Fresh-Gate 4 入口至此公开完成，下一步只进入真实运行确认门，不自动读取
Key 或执行 V2 held-out。

### 2026-08-15：DeepSeek V4 Pro V2 真实门单次执行

用户明确确认后，在 HEAD/origin 均为
`741e84140f816fb4b06b2812a8d07d3f32eaf4d0`、工作树干净、GitHub Actions run
`31863519248` completed/success、结果路径不存在且治理通过的条件下，只执行一次 V2
三案例 CLI。

- 首个正常案例实际调用 1 次，得到 1 个规范化响应，Usage 为 3241 input + 199 output，
  latency 12125 ms、估算 `$0.00506616`；
- 下一轮调用需预留 1024 output tokens，而单例已观察 3440 tokens，因
  `3440 + 1024 > 4000` 在 Provider I/O 前以 `token_budget_exhausted` 停止；
- Agent 终态为 `failed/provider_error`，Harness 终态为
  `degraded/draft_preparation_failed`，只返回确定性 fallback；unsafe publication 为
  false；
- 用户注入与知识注入两例按首错停止 skipped，没有新增外部调用；
- 新鲜领域总计 1 call/3440 tokens/`$0.00506616`；本记录连同既有 3-call 协议为
  4 calls/4868 tokens/`$0.00728112`。更早的旧领域失败调用仍由历史证据单独计数，
  Token/费用保持 unknown；
- 结果文件 SHA-256 为
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`，严格合同、
  运行确认、首错停止和脱敏边界已由 `47 passed` 聚焦回归固定；完整回归为
  `581 passed, 103 subtests passed`，两套 RAG、compileall、Harness SDK/tracked-data
  boundary、dry-run 与治理均通过；V2 不得覆盖或重跑。
- 结果、回归和教学裁决已由提交
  `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 推送；GitHub Actions run
  `31864370988` 对该精确 SHA completed/success。CI 无 `.env`/Key，也没有 Provider
  调用。

这次结果正确支持 `admitted=false`，并证明预算与安全控制生效；但由于事实、引用、注入
和 Evaluation 链均未完成，不能归纳为 DeepSeek 报告质量失败。它同时暴露了实验设计
Bad Case：Fake Provider 的小 Usage 没有证明真实 Prompt 下“4 calls/4000 tokens”控制流
可达。当时下一步仍在 5D-7 内，先做零调用的结果裁决与真实长度预算可达性 TDD；不得
直接调高预算重跑 V2、调用其他模型或进入 5D exit review/5E。

### 2026-08-15：5D-7 收尾审查

原始 5D-7 设计将最终 review 定义为评测合同、Prompt/Context 身份、控制流、安全门、
资源和采用决策的证据审查，而不是要求某个真实 Provider 必须通过。当前分层
Dataset/Candidate/Result、development/held-out 生命周期、Evaluation 1.1、已知注入阻断、
资源预算、双层安全错误 provenance 与不可变真实负面结果均已有证据。

ADR-0028 因此接受 5D-7 完成，同时保留当前无领域 Provider 准入：GLM-5.2 仅为开发
基线，DeepSeek 领域质量 unknown，GLM-5.3 G53 deferred，Flash 未测试。相关聚焦回归为
`130 passed, 4 subtests passed`，完整本地回归为 `616 passed, 103 subtests passed`；
两套 RAG 1.0 门禁、compileall、Harness SDK/tracked-data boundary、dry-run、治理和差异
检查均通过，本审查外部调用为 0。下一检查点为
`5D-exit-review`；它必须继续核对两个 Skill、真实模型/注入/性能限制和 5E 前置项，不能
把 5D-7 完成解释为生产模型报告质量已经通过。

审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 随后通过 GitHub Actions run
`31876536179` 的 exact-SHA 公共 CI。5D-7 至此正式闭环；该公共验证没有调用 Provider，
也没有改变当前无领域 Provider 准入的结论。

### 2026-08-15：5D 退出审查

退出审查逐项核对 5D 入口设计的十项功能要求、可靠性/安全性/预算/可测试性/框架中立
等非功能要求，以及 5E 的输入前置。核心执行与 Provider/实验两组跨层离线回归分别为
`173 passed, 34 subtests passed` 和 `176 passed, 22 subtests passed`。

审查未发现必须留在 5D 修复的结构性代码缺口：两个真实 Skill 都能在 Fake Provider、
实际本地 `knowledge.search`、AgentLoop、ToolRuntime 与唯一 ReviewHarness 的组合下形成
类型化终态；非法输出、越权、预算、上下文、Provider 和安全评测失败均不能绕过发布门。
真实 Provider 领域质量仍未准入并保持 unknown，这是一项明确产品限制，而不是 5D 控制
架构的阻塞条件。

因此 5D 状态改为已完成，阶段 5 继续进行中，唯一下一检查点为 `5E AgentRuntime V1`
入口设计。5E 将统一现有 run_id、事件、Trace、Usage 和安全终止原因；它不得自动调用
Provider、切换模型、接入 LangGraph/Agent SDK 或提前进入 5P/5F。退出审查提交
`2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已通过 GitHub Actions run
`31877076222` 的 exact-SHA 公共 CI；5D 的本地与公开退出证据均已闭环。

### 2026-08-18：6A-4 exact-SHA 公共闭环与 6A-5 交接

提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 已推送并由 GitHub Actions run
`32102522662` 完成 exact-SHA 公共验证；`pytest` job 与 `postgres-migrations` job 均
completed/success。公开 `pytest` 为 `1033 passed, 20 skipped, 1 warning, 110 subtests
passed`；真实 PostgreSQL 17 job 执行 6 个数据库测试文件并得到 `40 passed`，包含本轮
5 项 reconciliation/产品纵向测试。治理、两套 RAG、compileall、Harness dry-run、SDK/秘密
边界和 migration head 检查均通过，CI 无 `.env`、Key、Riot/Provider 调用。

因此 `6A-4-application-artifact-integration` 正式完成。它证明 SQL task 的 `run_id` 能安全
贯穿现有 Application/Runtime/Artifact，完整 receipt/Trace/final Artifact 证据能形成 succeeded
投影；没有终态证据时只报告 `recovery_required`，人工恢复通过 worker-matching CAS，不能自动
判死、重跑或 reclaim。它不证明 lease/heartbeat、自动恢复、异步 HTTP、Session/Memory 或公网
部署已经完成。

上述条目记录的是 6A-4 完成时的历史交接；随后 RQ-057 已授权并进入下方 6A-5 执行状态。

## 2026-08-18：6A-5 当前本地证据与下一动作

- RQ-057 已授权；6A-5 本地实现包括 V2 POST 202 task receipt、幂等 replay/conflict、安全错误映射、
  owner-scoped task/run/report、trusted ActorContext、production fail-closed、FastAPI lifespan、惰性
  Engine/Session composition、liveness 与 PostgreSQL/Alembic readiness。
- 本地证据：API 聚焦 `38 passed, 1 skipped`；完整 `1047 passed, 21 skipped, 1 warning, 110 subtests
  passed`；两套 RAG 均为 Recall/MRR/nDCG 1.0，holdout abstention/citation 1.0；compileall、Harness
  dry-run、governance、tracked Secret/run-data、SDK/YAML/diff 门均通过。
- 本机限制：无 PostgreSQL；新增 `tests/test_async_task_api_postgres.py` 的真实 create/replay/owner/
  readiness 证据尚未本地执行，已纳入 `.github/workflows/tests.yml` 的阻塞 `postgres-migrations` job。
- 真实 Worker 的 Riot/Data Dragon/Provider 进程组合仍 fail-closed，按范围裁决留给 6A-7 packaging；本批
  未读取 Key、未调用 Riot/Provider、未进入 6A-6。
- 唯一下一动作：检查 diff 与持久状态后提交/推送，等待 exact-SHA `pytest` 与 PostgreSQL CI；CI 成功后
  才把 6A-5 标为 complete 并交接 6A-6。

## 2026-08-18：6A-5 exact-SHA 公共闭环与 6A-6 交接

- 实现提交 `2492951c20dd6ca897d957d03752b6a2585ce469` 已推送；GitHub Actions run
  `32106378542` 的 `pytest` 与 `postgres-migrations` 均 completed/success。
- 公共完整 pytest 为 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`；PostgreSQL 17 job
  明确包含 `tests/test_async_task_api_postgres.py` 并得到 `41 passed, 1 warning`，真实验证 API create/
  replay、owner 隔离、queued run/report 409 与 current Alembic readiness。
- 两套 RAG、compileall、Harness dry-run、governance、tracked Secret/run-data、SDK boundary 与 migration
  metadata head 均通过；CI 无 `.env`/Key，也没有 Riot/Provider 调用。
- 因此 6A-5 正式完成：HTTP 可以可靠入队并查询 task/run/report，API process lifecycle 与 health 已闭环。
  这不表示 Worker external composition、正式 Auth、Session/Memory、SSE、前端或公网部署已经完成。
- canonical 只交接 `6A-6-security-lifecycle-nfr` 准备状态，等待用户明确继续；不得自动开始 6A-6。

## 2026-08-18：6A-6 Security/Lifecycle/NFR 开始

- RQ-058 已记录；用户明确“继续下一步”，解除 6A-6 等待确认，本轮状态改为实施中。
- 目标是把已冻结的 task 基座边界变成可运行、可测试的最小实现：默认关闭 CORS，日志与 Secret
  脱敏，owner/global 背压，7/90/30 天 retention，terminal delete 的立即隐藏与幂等补偿，active
  delete conflict，allowlisted metrics/log metadata，以及 warm-DB create/query 与 claim 延迟基线。
- 先写红灯测试，再写实现；Retention 使用 injected clock，跨 SQL/Artifact 删除使用安全的
  hidden-before-cleanup 语义。真实 PostgreSQL 并发、删除与性能证据由阻塞 CI 提供，本机无 DB 时明确 skip。
- 本轮不读取 `.env`/API Key，不调用 Riot、Data Dragon、GLM、DeepSeek 或其他 Provider，不实现正式
  Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume，也不进入 6A-7。
- 本地实现已完成：新增 retention/deletion/observability 合同与 purge CLI；API 接入 CORS、容量配置、
  DELETE hidden-before-cleanup 投影；Repository 增加 terminal/expired 删除短事务；Worker 接入安全
  claim/terminal 指标；新增纯逻辑与 PostgreSQL 生命周期/性能测试。
- 本地聚焦 `30 passed, 6 skipped`；完整回归 `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；
  两套 RAG、compileall、Harness dry-run、秘密/SDK/YAML/diff 与 governance 门禁通过。本机无 PostgreSQL，
  真实容量 race、删除和性能样本尚未执行。
- 下一动作是提交/推送并等待 exact-SHA `pytest` 与 PostgreSQL CI；CI 成功前不关闭 6A-6。
- 首个实现提交 `fecbb11` / Actions `32137687527` 的两个 job 均成功；完整 pytest 为
  `1077 passed, 27 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL 为 `51 passed`。但成功
  日志未记录 actual p95/sample/environment，claim 采样语义也偏向单次 SQL 调用；当前已做 evidence-only
  修补并等待新的 exact-SHA CI，因此仍不关闭 6A-6。

## 2026-08-18：6A-6 exact-SHA 公共闭环与 6A-7 交接

- 性能证据修补提交 `31d5e6038943bd3eacbeb485300f63ad53e13bfd` 已推送；Actions run
  `32138025724` 的 `pytest` 与 `postgres-migrations` 均 completed/success。
- 公共完整 pytest 为 `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  job 为 `51 passed, 1 warning`，明确执行 lifecycle/capacity/performance 文件。
- PostgreSQL 17 / Python 3.11 环境记录了 8 个 warm create+query 样本，p95 `6.220ms`（目标
  `<300ms`）；8 个 queued→claim 样本，p95 `23.359ms`（目标 `<2000ms`）。这些只证明 task
  控制面基线，不代表 Agent/Provider 质量或公网 SLA。
- 因此 6A-6/RQ-058 正式完成：默认 CORS、日志/Secret allowlist、背压、7/90/30 retention、terminal
  hidden-before-cleanup 与补偿、active delete conflict、结构化 observability 和真实性能证据均闭环。
- canonical 只交接 `6A-7-packaging-exit-review` 准备状态，等待用户明确继续；不得自动开始 6A-7。

## 2026-08-18：6A-7 Packaging & Exit Review 开始

- RQ-059 已记录；用户明确“继续吧”，解除 `6A-7-packaging-exit-review` 的等待确认。
- 本轮只建立可重建 API+Worker+PostgreSQL package、配置/启动命令、Linux no-I/O smoke，以及逐条绑定
  ADR-0038/6A 设计承诺的 exit matrix/review。先写红灯合同，再做最小实现。
- 真实 Worker composition 必须在读取或 claim 前完整校验数据库、Riot、Provider 与产品依赖；配置缺失
  安全失败。CI/smoke 不读取真实 Key、不调用 Riot、Data Dragon 或 Provider。
- 本轮不实现正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume、
  直接公网部署、LangGraph、Multi-Agent、MCP 或新 SDK。exact-SHA 公共 CI 成功前不关闭 6A。

## 2026-08-18：6A-7 本地实现与退出门完成

- production Worker composition、CLI `--check/--once`、非 root Dockerfile、严格 `.dockerignore`、
  migration/API/runtime-worker/no-I/O-smoke Compose、Linux blocking job 与启动/安全说明已实现。
- 人工审查补强了两个边界：无效 `worker_id` 在 Engine/网络构造前拒绝；smoke 使用隔离 Compose
  project/data volumes，并以 `up --wait api` 后 one-off `run --no-deps smoke` 执行，避免正常 migration
  退出提前终止以及诊断 Worker 误领普通本地任务。
- 本地聚焦 `48 passed, 1 warning`；完整 `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；
  两套 RAG 满门槛、Harness dry-run `published`/0 revisions、compileall 与安全边界通过。27 个 skip 和
  Docker/Compose 运行不能在本机冒充成功，必须由 exact-SHA PostgreSQL/Linux CI 补齐。
- 在首个公共 run 前，本地退出裁决保持 `keep-open-pending-exact-sha-linux-ci`；当时最终
  YAML/diff/governance/security 快照已通过，下一动作是提交推送并等待三个同 SHA job。

## 2026-08-18：首个 6A-7 公共 run 部分失败与受限诊断

- 提交 `b0f61caa6b6cb52eb753c6c5493ae51bbe58a600` 的 Actions run `32145005904` 已完成：pytest
  `1100 passed, 27 skipped, 1 warning, 110 subtests passed`、RAG/Harness/安全门成功；真实 PostgreSQL
  `51 passed, 1 warning` 成功。
- packaging job 已成功完成 Compose config、非 root image build、PostgreSQL、migration 与 API ready；
  one-off no-I/O smoke 返回 `packaging_smoke_worker_failed`，image boundary step 因此前失败未执行。
- 由于首版错误码把 DB/claim/CAS/query 多层压成同一值，当前未凭猜测改业务逻辑；已本地 TDD 增加
  body-free allowlisted 分层码，并在 failure 时只输出 bounded API/PostgreSQL logs。聚焦 `48 passed`、
  完整 `1102 passed, 27 skipped, 110 subtests passed`。
- 在该诊断检查点，6A 正确保留 `in_progress`；当时下一动作是提交诊断修补并等待新 exact-SHA 三 job，
  以真实 stage code 决定是否还需产品修复。

## 2026-08-18：第二个 6A-7 run 定位 Alembic import-root

- 诊断提交 `d8c5063f8e21af02a35450812fa20b47c6e21f53` / Actions `32146113582` 的 pytest、真实
  PostgreSQL、image build、migration 与 API ready 均成功；one-off 输出精确为
  `packaging_smoke_database_not_ready`，bounded logs 显示同一 API 已对同 DB readiness 200 且 POST 202。
- 根因不是 PostgreSQL 或 migration：API 以模块入口从 `/opt/riftcoach/app` 导入，能用工作目录下
  `alembic.ini`；`python scripts/run_packaging_smoke.py` 把 `scripts/` 放在 `sys.path[0]`，优先导入已安装
  wheel 中的 `app`，其 `PROJECT_ROOT` 不含镜像的 Alembic 文件。真实 Worker 同样存在该启动风险。
- 已用红灯合同要求两条 Compose 命令都使用 `python -m scripts.<module>`，随后最小修改 Worker/smoke
  command；聚焦 48 项与两个 module `--help` 入口通过。未放宽 readiness、复制 migration 或改 DB 语义。
- 在该根因检查点，当时下一动作是完成横向门、提交 module-entry 修复并等待新 exact-SHA 三 job。

## 2026-08-18：6A-7/6A exact-SHA 公共闭环

- module-entry 修复提交 `adf53e56d1eb624746b493ad8b281598c9a0dd32` 的 Actions run
  `32146760003` 三 job 全部 completed/success：pytest `1102 passed, 27 skipped, 1 warning,
  110 subtests passed`；真实 PostgreSQL `51 passed, 1 warning`；packaging-smoke 完整成功。
- Linux smoke 的安全输出为 `task_status=failed`、`external_riot_provider_calls=0`：它真实覆盖 HTTP 202、
  PostgreSQL claim、安全 failure terminal 与 HTTP query；随后 image boundary 确认非 root，且镜像不含
  `.env`、tests、cache/runs、reports、tmp。
- 6A 退出裁决为 `close-with-deferred-boundaries`：持久异步 task API 基座与可重建 package 已完成；
  Session/Memory、正式 Auth/HTTPS、SSE/前端、lease/reclaim/cancel/resume、备份/SLA 和真实模型领域质量
  继续 deferred。
- `6A-7-packaging-exit-review` 与整个 6A 正式完成。canonical 只交接
  `stage-6-session-memory-entry-design` 准备状态，等待用户明确继续，不自动实施。

## 2026-08-19：Session/Memory 入口设计获授权

- 6A 状态收尾提交 `d1cc2ed4e021a2fa14ed477d17f00e18578eebb2` 已推送；Actions
  `32147545753` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功。这补齐状态提交
  自身的公共证据，不改变 `adf53e5` 作为 6A module-entry/package 实现证据的角色。
- 用户“继下一步”构成 RQ-060，解除 `stage-6-session-memory-entry-design` 的等待授权状态。
- 本检查点只审计现有 owner/task/run/API、EchoMind/Saber 可迁移思想与缺陷，并逐节确认概念边界、
  数据模型、写入/更正/导出/过期/删除、隔离、隐私/NFR/测试和后续原子实施顺序。
- 当前没有 Session/Memory 产品代码；不复制 EchoMind Redis/Chroma，不把 RAG 或原始比赛事实当 Memory，
  不自动引入向量库/LangGraph，也不提前进入 Auth/SSE/前端、阶段 7 或阶段 8。

## 2026-08-19：RQ-061 外服账号认领边界

- Riot 官方 LoL routing values 当前没有中国大陆 CN；`ASIA` 是包含 KR/JP 等平台的区域路由，不等于
  中国大陆服务器支持，`zh_CN` Data Dragon 本地化也不是服务器路由。
- Riot ID→PUUID 只解析可查询账号主体，不证明应用 owner 控制账号。当前只能形成未验证 self claim。
- future verified 必须同时经过正式 RiftCoach Auth、安全绑定到该 owner 的 RSO OAuth/OIDC callback，
  并让 `/accounts/me` PUUID 与 subject 精确匹配；当前没有这条产品路径。
- 该条记录当时仍待 `public_observed` 裁决；后续 RQ-062 已确认采用。本次修正没有创建表、接口或
  RSO/Auth 代码。

## 2026-08-19：RQ-062 外服玩家关系策略确认

- MVP 同时支持 `self + unverified_claim → claimed_self` 与
  `observed + not_applicable → public_observed`；role 与 verification 不混成单一含糊枚举。
- claimed-self 可形成 owner-player 训练目标/计划/进度但必须显示未验证；public-observed 只允许公开分析、
  owner-local 观察备注/趋势和第三人称语义，不生成被观察者的私人偏好或训练完成度。
- future `self + rso_verified → verified_self` 当前无创建路径；任一关系不增加 Riot 权限，不跨 owner
  合并私人数据。
- 下一步仍在同一 entry-design 内，只确认 conversation 固定/切换与 task 继承；没有实现产品代码。

## 2026-08-19：RQ-063 Conversation 固定玩家确认

- Conversation 创建时属于 trusted owner 并固定引用该 owner 的一个 player subject；V1 不提供中途切换，
  不同 PUUID 必须新建 conversation，相同 PUUID 的 Riot ID 改名可继续。
- 消息、Context、task/run 和 Memory Candidate 继承服务器保存的 owner/conversation/subject；client body、
  自由文本或模型均不能覆盖，未来以应用校验和 PostgreSQL owner-scoped composite constraints 双层强制。
- 当前异步入队只有 Riot ID，Worker 内才解析 PUUID；下一设计门先裁决 subject/link/conversation bootstrap
  顺序。没有创建 schema、migration、Repository、API 或外部调用。

## 2026-08-19：RQ-064 与 Session/Memory 设计本地冻结

- RQ-064 取代 RQ-060 当时的“设计后另行授权”暂停门，但自动范围严格止于三个独立批次：entry design、
  6B-1、6B-2；6B-2 exact-SHA 全绿后只把 6B-3 置为 prepared/waiting authorization。
- 三案裁决采用独立异步 Player Link：API 先持久化 bounded Riot ID link intent，专用 Worker 在事务外调用
  Account-V1，随后以一个 PostgreSQL 短事务收敛 subject、alias、owner relationship 和 link terminal；
  link 成功后才能创建 Conversation。首个 Review 内 bootstrap 与 API 同步 lookup 被拒绝。
- Memory 采用“关系型身份/状态骨架 + 分类型长期记录 + 严格 JSONB 叶子 + Candidate write gate”；模型或
  自然语言提取不能直接永久写入，PostgreSQL 是唯一真源，Redis/向量索引仍需真实 Bad Case 才评估。
- ADR-0039、`docs/plans/2026-08-19-stage6-session-memory-design.md` 与
  `docs/plans/2026-08-19-stage6-session-memory-implementation.md` 已在本地创建，并按 6B-1 至 6B-9 冻结
  全阶段顺序；本次自动实施仍只覆盖 6B-1/6B-2。
- 当前只完成本地设计内容，尚未提交、推送或取得 exact-SHA CI，也没有创建 migration/schema、读取 Key、
  调用 Riot/Provider。本地完整回归为 `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；两套 RAG
  均满阈值，Harness dry-run `published`/0 revisions，compileall、SDK/Secret/run-data、YAML、governance 与
  diff 门均通过。27 个 skip 不冒充真实 PostgreSQL/Docker 成功；下一动作是设计批独立提交/推送和
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 公共闭环，全绿前不进入 6B-1。

## 2026-08-19：Session/Memory entry design exact-SHA 公共闭环

- 设计提交 `bc11afe9f2f85a39f05b7f3d6135b14821ebb17d` 已推送；GitHub Actions run
  `32222531783` 总状态 success，精确对应的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均成功，公开页面显示 workflow 总耗时 1m07s。
- 入口设计退出条件全部满足：RQ/ADR/design/implementation/canonical 一致，本地 1102 tests/两套 RAG/
  Harness/安全门通过，真库与 Linux package 又由同 SHA 补齐；设计批外部 Riot/Provider 调用为 0。
- `stage-6-session-memory-entry-design` 正式关闭，但这只证明设计可审计且旧系统未回归，不表示四张 Player
  表、Repository、Worker、Conversation 或 Memory 已实现。
- 按 RQ-064，canonical 进入 `6B-1-player-identity-link-foundation`；本批先做严格 domain 合同与持久身份
  地基，不实现 6B-2 的 Resolver/Worker/API，也不读取 Key 或调用外部服务。

## 2026-08-19：RQ-065 与 6B-1 本地实现门

- 用户用 RQ-065 将本轮停止点收紧为 6B-1 公共闭环；6B-2 不再自动实施，完成后只准备并等待下一轮授权。
- 已建立 strict Player/Relationship/Link Task domain、Riot ID normalization/fingerprint、public body-free View、
  allowlisted failure、Service/Port、四张 PostgreSQL ORM 表、可逆 Alembic 0002 与事务 Repository。
- Repository 覆盖 owner-scoped create/replay/conflict/capacity、deterministic `FOR UPDATE SKIP LOCKED` claim、
  stale-worker CAS、PUUID/alias/relationship `ON CONFLICT` 收敛、同 PUUID 并发和整事务回滚；角色冲突在
  `resolve_link()` 同一事务写 `failed/relationship_role_conflict`，不写 alias、不修改 relationship。
- pure domain 红灯曾为 `ModuleNotFoundError: app.players`；Repository 红灯曾为
  `ModuleNotFoundError: app.persistence.player_repository`。当前 6B-1 聚焦为 `17 passed, 13 skipped`，相邻为
  `35 passed, 28 skipped`，完整为 `1119 passed, 40 skipped, 1 warning, 110 subtests passed`。skip 全因本机
  无 PostgreSQL，不能冒充真库成功。
- 两套 RAG 均满阈值，Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/
  run-data、YAML、governance、diff 与 Alembic offline SQL 编译通过。离线编译曾抓到两个超过 PostgreSQL
  63 字符的 constraint 名并已同步修复；本批外部 Riot/Provider/Key I/O 为 0。
- 实现提交 `656117a` 的首个公共 run `32227457202` 未通过：PostgreSQL 与 packaging 共同暴露 35 字符
  Alembic revision 无法写入默认 32 字符 version column；该缺口已由新增红灯固定并缩短 revision 修补。
- revision 修补 `b8fa2e3` / Actions `32227937252` 已使 pytest、packaging 和 reversible migration 通过；
  真库 67 项仅剩一个 CHECK 名断言失败。日志证明完整 CHECK 名被 naming convention 二次前缀后截断；现已
  用 offline SQL 红灯和全部 CHECK `op.f(...)` 修补，不放宽稳定 schema 名称合同。
- 在第三个公共 run 前仍是 `6B-1-player-identity-link-foundation / in_progress`；该临时状态已由下方
  `ed8fa58/32229024069` 公共闭环取代。

## 2026-08-19：6B-1 exact-SHA 公共闭环并按 RQ-065 停止

- 最终修补提交 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 对应 Actions `32229024069`，总状态
  completed/success；`pytest`、真实 `postgres-migrations` 与 Linux `packaging-smoke` 三 job 均成功。
- 6B-1 正式完成：严格 Player/Relationship/Link Task 合同、四张表、可逆 0002、事务 Repository、
  幂等/容量、SKIP LOCKED、PUUID/alias/relationship 收敛、role-conflict 单事务失败、CAS/rollback 与
  confirmed display snapshot 均已有本地和真实 PostgreSQL 证据。
- 本批没有实现 Resolver、PlayerLinkWorker、HTTP API、Conversation/Memory、Auth/RSO 或外部 Riot/
  Provider I/O；成功证据不能外推到这些边界。
- RQ-065 的本轮目标已经满足。canonical 现为 `6B-2-async-player-link-worker-api / pending`，只表示下一批
  设计已准备，等待下一轮用户明确授权；本轮停止，不实施 6B-2。

## 2026-08-19：RQ-066 恢复 6B-2

- 用户在独立的新一轮明确“继续开工”，随后恢复真实仓库写权限；RQ-066 解除 6B-2 的 waiting 状态，
  但授权严格止于本批，6B-3 不在范围内。
- 已完成初学者入口教学与既有 ADR/design/implementation plan 复核：API 只持久化意图并返回 202，
  PlayerLinkWorker 在 claim 已提交后、数据库事务外调用 Account-V1，Resolver 只返回严格 account 或
  allowlisted failure，Repository 再用短事务提交身份关系/终态。
- 当前先执行 Task 1 Resolver TDD；开发/测试/CI 使用 Fake client/resolver，真实 Riot/Provider/Key I/O
  保持 0。不实现 Conversation/Message/Memory、Review Task subject binding、自动 retry/reclaim、
  verified-self/Auth/RSO、SSE/前端或新框架。

## 2026-08-19：6B-2 Tasks 1–4 本地完成，等待公共闭环

- Task 1 已完成：`RiotAccountResolver` 通过注入 Fake client/factory 做严格 Account-V1 响应校验，
  将 404、认证失败、429、timeout、连接/其他上游错误和坏响应映射为 allowlisted body-free failure；
  构造与 API composition 不读取 Key 或发起网络请求。
- Task 2 已完成：`PlayerLinkWorker` 使用 claim 短事务提交→事务外 Resolver→终态 CAS 短事务，覆盖安全
  失败、坏结果、role conflict、ownership loss、终态异常、退避轮询与 graceful stop；不实现自动 retry、
  lease、reclaim 或 recovery。
- Task 3 已完成：`POST /player-links` 与 `GET /player-links/{link_task_id}` 使用 trusted ActorContext、
  owner-scoped service、202/replay/409/404/503 投影和 PUUID-free DTO；API composition 只构造 PostgreSQL
  Repository/Service，不构造 Riot Client/Resolver。真实 PostgreSQL API 测试已加入阻塞 CI，本机因无 DB 明确 skip。
- Task 4 已完成：独立 `player-link-worker` Compose service、`--check/--once` CLI、完整配置/DB readiness
  fail-closed 与 Fake Resolver packaging smoke 已接入。routing policy 要求完整覆盖四个官方 regional
  values，避免 API 可入队但 Worker 永远拒绝；smoke 使用固定安全 worker ID，避免拼接越界。
- 本地证据：6B-2 聚焦/相邻 `149 passed, 2 skipped, 1 warning`；完整 `1216 passed, 42 skipped, 1 warning,
  110 subtests passed`；RAG development/holdout 均 Recall/MRR/nDCG `1.0`，holdout abstention/citation
  `1.0`；Harness dry-run `published`/0 revisions；compileall、YAML、SDK boundary、tracked Secret/run-data、
  governance 与 `git diff --check` 均通过。42 个 skip 仅因本机没有 PostgreSQL/Docker，不能冒充真库/package 证据。
- 本批开发、测试和本地 smoke 的 Riot/Provider/Key I/O 为 0；真实 Riot 调用仍只存在于生产 Worker composition，
  不得把 Fake Resolver smoke 描述为外部 API 成功。
- 当前唯一下一动作是提交/推送本批并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；
  在三 job 全绿前保持 `6B-2 / in_progress`，不得把 6B-2 标为 complete。公共闭环后只把 6B-3 标为
  prepared/waiting authorization，不实施 Conversation/Memory。

## 2026-08-20：6B-2 exact-SHA 公共闭环并按 RQ-066 停止

- 实现提交 `0c13a583ea51a7c18301fc29bf5c2931790d6693` 已推送；Actions run `32301852042`
  精确对应该 SHA，workflow 与 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。
- 公共 `pytest` 为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`；两套 RAG 指标满门槛，
  Harness dry-run 为 `published`/0 revisions。真实 PostgreSQL 17 job 为 `70 passed, 1 warning`，并通过
  可逆 migration 与 metadata-head 一致性。
- Linux package smoke 真实输出 `task_status=failed`、`link_status=succeeded`、
  `external_riot_provider_calls=0`；这证明 Review Task 安全失败路径与 Fake Resolver Player Link 成功路径
  可在可重建 package 中共同运行，不证明真实 Riot Key、账号归属或 Provider 质量。
- 6B-2 正式完成：窄 Account Resolver、专用 PlayerLinkWorker、owner-scoped Link API、composition/CLI、
  PostgreSQL API integration 与 Linux no-I/O smoke 已闭环。未实现 Conversation/Message/Memory、Review
  Task subject binding、自动 retry/reclaim、verified-self/Auth/RSO、SSE/前端或真实 Riot/Provider 调用。
- RQ-066 的授权目标已经满足。canonical 现只把 `6B-3-conversation-message-foundation` 标为
  prepared/waiting authorization；本轮停止，不创建 Conversation、Message 或 Memory 代码。

## 2026-08-20：RQ-067 持久教学/工程说明补齐前置门

- 用户要求重新确认缺口是否确实从 6B 才开始，并从阶段 0 起以统一标准审计；不能用文件数量、聊天长度、
  canonical 或 progress 中“已讲过”的一句话替代可独立复习的成品。
- 补齐范围包含全部已识别材料，而非仅初学者文章：设计/实现复盘、实际代码地图、数据流与控制流、事务/
  失败/安全边界、需求→源码→测试→CI→限制证据矩阵、运行示例、面试安全表述、README/学习索引，及
  AGENTS/治理防复发门。
- 采用覆盖矩阵驱动的混合方案：充分材料链接复用，真实缺口新增 walkthrough/implementation review；
  不按文件数量重复已有内容，也不以一篇笼统总览掩盖原子子阶段缺口。
- 当前仍以 `6B-3-conversation-message-foundation` 作为唯一产品检查点，但它受本横向文档门阻塞；补齐批
  独立通过治理、比例回归、提交/推送和 exact-SHA 公共 CI 后，RQ-067 允许无需再次确认直接进入 6B-3。
  文档门闭环前不创建 Conversation/Message schema、migration、Repository、API 或产品测试。

## RQ-067 本地退出复核（公共验证前）

- 新增整体退出复核 `docs/plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md`；覆盖账本登记 17 组，当前 6B-3 为 `planned`，所有前序组为 `complete`。
- 本地聚焦：治理 `10 passed`；Agent Loop/Skill `34 passed`；Provider/Tool `101 passed, 68 subtests`；领域/RAG 代表性集合 `37 passed`。
- 完整回归：`1224 passed, 42 skipped, 1 warning, 110 subtests passed`。两套 RAG、Harness dry-run、compileall、secret/tracked-data、SDK boundary、Markdown/YAML/link 与 diff 门均通过。
- 本地裁决：`pass-local-pending-public-ci`。42 个 skip 仍仅因本机无 PostgreSQL/Docker；尚未提交/推送本批，不能把文档闭环写成公共完成。

## 2026-08-20：RQ-067 文档门公共闭环，进入 6B-3

- 文档/工程证据提交 `63435d90f5153309fce98b92a2ff58425d54a684` 已推送；GitHub Actions run `32308631289` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success`。
- 这次公共验证补齐了文档批的治理、完整回归、真实 PostgreSQL migration/metadata 复核和 Linux package 边界；它不把本地 42 个 PostgreSQL/Docker skip 改写为本地真库证据，也不表示 6B-3 功能已完成。
- RQ-067 前置门正式关闭，`docs/learning/coverage.yaml` 的 Q11/complete 证据获得公共 CI 支持；canonical 现在正式进入 `6B-3-conversation-message-foundation` 的初学者设计复核与 TDD。
- 当前仍没有 Conversation/Message/Memory 产品代码；下一批先讲并冻结 6B-3 的 owner/relationship/subject 绑定、消息角色/长度、并发序号、归档/隐藏和 owner-scoped 查询合同，再写红灯测试。

## 2026-08-20：6B-3 设计冻结与红灯交接

- 6B-3 接缝审计确认可复用现有 SQLAlchemy Base、Player relationship 复合 identity、短事务
  Repository、FastAPI Port/proxy/lifespan 与 PostgreSQL CI；没有采用参考项目或新框架。
- ADR-0040 与 `docs/plans/2026-08-20-conversation-message-foundation-design.md` 已冻结：active
  relationship 必须在同一短事务锁定检查；Conversation 创建采用 owner-scoped Idempotency-Key；
  公共 API 只允许 user Message；序号从 1 开始由 Conversation 行锁分配；archived/hidden 语义分离；
  binding trigger 防 direct SQL rebind；source task/run 不设阻塞性强 FK。
- 为防止持久覆盖账本被“重排并重编号”绕过，治理脚本增加固定 canonical group order，coverage YAML
  增加并校验人类可读镜像，回归测试当前为 `12 passed`；README 前置条件和日期审计无须额外修补。
- 当前代码事实仍是“没有 Conversation/Message schema、migration、Repository、API 或产品测试”；
  设计文件不算实现证据。本地完整回归为 `1226 passed, 42 skipped, 1 warning, 110 subtests passed`；
  RAG development/holdout、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff
  门均通过。下一动作是设计批独立提交/推送和 exact-SHA 三 job；全绿后才进入红灯与最小实现。

## 2026-08-20：6B-3 设计批公共闭环，进入红灯合同

- 设计/治理提交 `b6a7112d9c3fa8744b9713737bbbf54fe5011084` 已推送；Actions run
  `32313707301` 精确对应同一 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。
- 这次公共证据证明 ADR/design/governance 与既有真库/package 边界兼容，不证明 Conversation/Message
  产品代码已经存在，也不证明 Agent、Review 或 Memory 接入。
- canonical 保持同一 6B-3 checkpoint，但内部从“设计门”转入“红灯→最小实现”；第一批先冻结 pure
  model/Service/API 合同，随后才实现 PostgreSQL schema/Repository/并发与 API composition。

## 2026-08-20：6B-3 本地实现、审查修复与公共验证前状态

- Conversation/Message strict domain、Port/Service、SQLAlchemy metadata、可逆 Alembic 0003、事务
  Repository、六个 HTTP endpoint、lifespan composition、Linux no-I/O package 纵向与 pure/API/真库/
  并发测试已在工作树建立；没有接 Agent、Review Task 2.0、Memory、Auth、SSE、前端或新框架。
- scoped advisory lock 只串行同 `owner_id + idempotency_key`；Service 又防御 CREATED 投影伪造服务器
  conversation ID/active 初态；assistant 数据合同必须有 `source_run_id`，公共 API 仍只能写 user。
- 最终只读审查未发现 P0/P1，修复两项 P2：archive/hide 的 OpenAPI 422 现在与实际
  `ConversationErrorResponse` 一致；有效 command 之后的 UUID factory/clock 故障按服务器 503，而非误报
  客户端 422。对应红灯为 `5 failed, 35 passed`，最小修复后为 `40 passed`。
- 原 lifecycle/append Barrier 测试被确定性调度取代：blocker 先锁 Conversation，事件确认第一操作已持
  relationship、第二操作已尝试相同 relationship 锁，再释放 blocker；archive/hide 各自证明 append-first
  与 lifecycle-first。该真库测试本机因无 PostgreSQL 明确 skip，只能由阻塞 CI 补证。
- 新增干净 Python 子进程 import/OpenAPI no-I/O 测试；`docs/learning/6b-3-conversation-message-foundation-
  walkthrough.md` 已补齐八维材料，coverage evidence 路径已完整但在公共三 job 全绿前保持 `planned`。
- 当前仍未提交/推送实现批，也没有该实现 exact-SHA 的 PostgreSQL/package 公共证据。唯一下一动作是完成
  全部本地门禁与最终 diff，随后提交/推送并等待三个同 SHA job；全绿后再用独立状态批关闭 6B-3，只把
  6B-4 标为 prepared/waiting authorization，不实施 6B-4。

## 2026-08-20：6B-3 本地实现收尾与公共验证前复核

- 已完成 6B-3 实现批的聚焦与完整复核：聚焦 `85 passed, 25 skipped`；完整
  `1295 passed, 67 skipped, 1 warning, 110 subtests passed`。本机 skip 全部是没有 PostgreSQL/Docker，
  仍不替代公共真库/package 证据。
- RAG development/independent holdout、Harness dry-run（published/0 revisions）、compileall、
  Provider boundary、tracked Secret/run-data、YAML、治理与 `git diff --check` 均通过；Docker Compose
  本机不可执行，保持为 `packaging-smoke` 公共门。
- 本地状态仍为 `in_progress`：实现、测试、walkthrough 和八维证据路径已建立，但实现提交尚未取得
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。coverage 继续保持 `planned`。
- 唯一下一动作：独立暂存/cached diff、提交、推送并等待同一 SHA 三 job；全绿后再单独提交状态收尾，
  将 6B-3 置为 complete、coverage 置为 complete，并只把 6B-4 标为 prepared/waiting authorization。

## 2026-08-20：6B-3 实现 exact-SHA 公共闭环与状态收尾

- 首个实现提交 `0ca7fdebe4bf038685ff24691f2d5091e6ffbe4f` 的 `postgres-migrations` 曾失败；真实日志定位为
  测试 fixture 未先 flush `player_subjects` 父行，导致 PostgreSQL FK 顺序竞争。失败 SHA 保留为审计证据，
  未重跑或放宽生产约束。
- 最小测试 fixture 修复提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081` 已通过 Actions run `32329686381` 的
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。公开证据包括完整回归
  `1295 passed, 67 skipped, 1 warning, 110 subtests passed`、PostgreSQL `100 passed, 1 warning`、migration
  upgrade/downgrade、`alembic check`、package smoke 与边界检查。
- 本机没有 Docker/PostgreSQL，所以本地 skip 仍如实保留；公共 CI 才补齐真实 PostgreSQL trigger、FK、事务、
  并发和 Linux package 证据。没有读取 Key、调用 Riot/Provider，也没有接入 Agent、Review Task、Memory、
  Auth/RSO、SSE、前端或新框架。
- 6B-3 现正式关闭，`docs/learning/coverage.yaml` 置为 `complete`，学习索引改为完整/公共闭环；下一检查点
  是 `6B-4-conversation-bound-recent-review-identity`，仅 prepared/waiting authorization，不实施 6B-4。

## 2026-08-20：RQ-068 授权并进入 6B-4

- 用户明确“继续 6B-4”；canonical 由已完成的 6B-3 交接到
  `6B-4-conversation-bound-recent-review-identity / in_progress`，不进入 6B-5。
- 本批采用既有 `review_tasks` 上的 nullable schema 2.0 identity columns，由服务器在 PostgreSQL 短事务中
  锁定 active Conversation 并派生 owner/conversation/relationship/subject tuple；旧 schema 1.0 row 保持
  新列为 null 且继续可读/可执行，不根据旧 Riot ID 回填身份。
- 新 endpoint body 只允许 count/queue/focus；v2 Worker 通过稳定 subject 的 trusted PUUID 直接构建
  Summary，不再次调用 Account-V1。测试/CI 保持 Fake/no-I/O。
- 当前只完成教学、方案裁决和状态/coverage 治理迁移；产品 migration、Repository、API、Executor 与纵向
  测试尚未实现。6B-5、assistant Message、Memory、Auth/RSO、SSE、前端和新框架继续 deferred。

## 2026-08-20：6B-4 本地实现与完整门禁，等待公共闭环

- Review Task schema 2.0 pure contract、identity-aware fingerprint、Conversation-bound 202 route、0004/ORM、
  PostgreSQL 单事务 server-derived binding、私有 PUUID target、trusted-PUUID Summary/Application、1.0/2.0
  Executor 和 composed API 已在未提交工作树完成；旧 1.0 查询/执行/删除保持兼容。
- package smoke 已升级为 Link→Conversation→Message→schema 2.0 Task→同一 ReviewWorker→safe failed
  terminal，结果明确 `external_riot_provider_calls=0`；两个新真库测试文件已加入阻塞 PostgreSQL job。
- 6B-4 聚焦为 `114 passed, 11 skipped, 1 warning`；完整回归为
  `1333 passed, 78 skipped, 1 warning, 110 subtests passed`。本机 skip 全部来自无 PostgreSQL/Docker，
  不能冒充真库锁、FK、trigger 或 Linux package 成功。
- RAG development/independent holdout 指标均满既定阈值，Harness dry-run 为 `published`/0 revisions；
  compileall、SDK boundary、tracked Secret/run-data、YAML、pip、governance 与 diff 门通过。
- `docs/learning/6b-4-conversation-bound-recent-review-identity-walkthrough.md` 已覆盖八维 evidence，
  但 coverage 在 exact-SHA 三 job 全绿前保持 `planned`。唯一下一动作是 cached diff、提交、推送与公共
  CI；6B-5 未授权且未实施。

## 2026-08-20：6B-4 exact-SHA 公共闭环与 6B-5 交接

- 实现提交 `d63f9085f66e49557b4674d0698495dcb7335c82` 已推送；Actions run `32347834279`
  精确对应该 SHA，workflow 与 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  `completed/success`。
- 公共 `pytest` 为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  job 为 `113 passed, 1 warning`，并通过 0004 upgrade/downgrade、完整 migration 链与
  `alembic check` metadata-head 一致性。
- Linux package smoke 真实执行 Link→Conversation→Message→schema 2.0 Review Task→同一 ReviewWorker，
  Review 安全终态为 `failed`、Conversation 保持 `active`、`external_riot_provider_calls=0`。这证明安装后
  控制流和安全失败边界，不证明真实 Riot/Provider 成功或模型质量。
- 6B-4 正式关闭，`docs/learning/coverage.yaml` 已置为 `complete`。本机没有 PostgreSQL/Docker 的 78 个
  skip 仍如实保留，公共 CI 只是补齐真库/Linux 证据，没有把它们改写成本地成功。
- 下一检查点是 `6B-5-memory-candidate-write-gate`，仅 prepared/waiting authorization；尚未创建 Candidate
  migration/model/Repository/write gate，也未实现 assistant terminal、具体长期 Memory、Auth/RSO、SSE、
  前端或新框架。

## 2026-08-20：RQ-069 授权 6B-5，进入设计/TDD

- 用户明确“继续 6B-5”；canonical 现为 `6B-5-memory-candidate-write-gate / in_progress`，不进入 6B-6。
- ADR-0042 选择事务内 typed materializer：Candidate 与 target 必须同事务提交；没有真实 target 时生产
  fail closed。测试专用 target 只证明协议，不冒充具体长期 Memory。
- Candidate identity 从服务器 Conversation 派生；模型/自然语言 confidence 再高也只能 pending；observed
  只能提出受限 review observation。公开 DTO 不泄露 payload、完整 provenance、PUUID 或 Message body。
- 当前已完成治理/专用设计/实施计划，产品代码尚未开始。下一动作是 pure model/gate 红灯；本批外部
  Riot/Provider/Key I/O 固定为 0。

## 2026-08-20：6B-5 本地实现完成，等待 exact-SHA 公共门

- Candidate pure contract/Gate、Service/Port、0005 ORM/migration、owner-scoped Repository、reject/expire/
  accept、restricted materializer session、薄 API/composition 与 no-I/O package smoke 已实现；不创建具体
  Preference/Profile/Review Memory/Plan/Progress 表。
- 新增 `docs/learning/6b-5-memory-candidate-write-gate-walkthrough.md`，覆盖八维学习/工程证据；coverage
  仍保持 `planned`，直到同一实现 SHA 的公共三 job 全绿。
- 本地聚焦 `50 passed, 10 skipped, 1 warning`；完整回归待本轮最终复跑。RAG、Harness dry-run、compileall、
  SDK/secret/tracked-data、YAML、governance 与 diff 门需一并复核。
- 10 个 skip 全因本机无 PostgreSQL/Docker；公共 `postgres-migrations` 新增 0005/FK/trigger/Repository/
  materializer 测试，package smoke 新增 Candidate pending→reject。没有读取 Key、调用 Riot/Provider。
- 唯一下一动作：完成完整本地门禁和 cached diff，提交/推送后等待 exact-SHA `pytest`、`postgres-migrations`、
  `packaging-smoke`；公共全绿后再状态收尾 6B-5 并只交接 6B-6 prepared/waiting authorization。

## 2026-08-20：6B-5 exact-SHA 公共闭环与 6B-6 交接

- 实现提交 `7156cb52e1ab2a976828b5a0a164c163943b56f3` 的 Actions run `32372854457` 中，普通
  `pytest` 与 `packaging-smoke` 成功；真实 PostgreSQL 的三个 materializer 测试只在 teardown 失败：测试
  临时表仍以 FK 引用 `memory_candidates`，fixture 却先执行 Alembic downgrade。失败保留为审计证据，
  没有放宽 migration、FK、Repository 或 materializer 合同。
- 最小清理修复 `dd7c9c8f43bac19756272aaf9555f0519e22341c` 在 downgrade 前显式删除测试专用 target；
  Actions run `32376405150` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。
- 公共完整回归为 `1358 passed, 88 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17 为
  `126 passed, 1 warning`，0005 可逆迁移、materializer commit/rollback/replay/concurrency 与
  `alembic check` metadata-head 一致性均通过。Linux package smoke 中 Candidate 为 `rejected`，
  `external_riot_provider_calls=0`。
- 6B-5 与八维 coverage 正式关闭。它只完成 Candidate 控制面、deterministic gate 和 transactional typed
  materializer 接缝，不等于 Preference/Profile/Review Memory 已存在；生产 registry 在 6B-6 前仍为空并
  fail closed。
- 用户最新“那继续”按 AGENTS 规则只授权唯一下一检查点 `6B-6-preferences-profile-review-memory`。

## 2026-08-20：RQ-070 授权 6B-6，完成设计批冻结

- canonical 已从 `pending/waiting authorization` 恢复为 `in_progress`；当前只处理 6B-6，不能跳到 6B-7。
- 设计批新增 ADR-0043、`docs/plans/2026-08-20-memory-types-design.md` 与
  `docs/plans/2026-08-20-memory-types-implementation.md`，冻结三张 typed target 表、scope/role/key
  allowlist、严格 `value + expected_version` envelope、版本 supersede、Review append 的单 active 最新
  版本语义、PostgreSQL advisory lock/partial unique、查询 API 和错误映射。
- 设计提交 `e44d48f0531f0ee1786cba9b38c8fc8b2589af00` 已由 Actions run `32381553145` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job exact-SHA 公共验证；设计批正式关闭，
  该 run 不证明 6B-6 业务 target 已实现。
- 当前尚未创建 6B-6 migration/model/Repository/materializer/API 产品代码；本轮仍然不进入 Training
  Plan/Progress、Memory-aware Context、assistant terminal、Auth/RSO、SSE、前端、Redis/Chroma/向量库、
  LangGraph、Multi-Agent、新 SDK 或真实 Riot/Provider 调用。
- 设计批公共闭环后，下一动作是按实施计划 Task 1 先写 typed payload/version pure contract 红灯测试；coverage 继续
  `planned`，直到实现、本地门禁和 exact-SHA 三 job 公共闭环。

## 2026-08-20：6B-6 本地实现完成，等待 exact-SHA 公共门

- Pure typed envelope/key/role policy、三个 materializer、三张 ORM 表、0006 migration/trigger、PostgreSQL
  version writer、生产 registry、owner-scoped query Service/API 和 package smoke schema 1.3 已在工作树完成。
- Candidate accept 现在可在同一事务中执行 advisory lock、expected-version、supersede/insert，再写 accepted；
  typed payload/version 失败安全返回并保持 pending。更正仍走 Candidate，没有开放 target PATCH。
- 首轮聚焦/相邻测试为 `128 passed, 19 skipped, 1 warning`；提交前复核又新增 metrics/page 两项纯合同和
  terminal-source/supersedes-chain 两项真库合同，并修正 accept 事务的 typed error disposition 接线。真实
  migration/FK/trigger/partial unique/advisory lock/并发/rollback 与 Linux package accept→query 必须由公共
  job 补证，当前不能声称 6B-6 已完成。
- 最终完整本地回归为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；100 个 skip 全因本机没有
  PostgreSQL/Docker。两套 RAG 指标满门槛，Harness
  dry-run 为 `published`/0 revisions，compileall、YAML、治理、SDK/Secret/tracked-data 与 diff 门通过。
- `docs/learning/6b-6-preferences-profile-review-memory-walkthrough.md` 已覆盖八维 evidence，coverage 仍为
  `planned`。外部 Riot/Provider/Key I/O 为 0；6B-7 及后续能力未进入。
- 首个实现提交 `da87cdeefc6b104b8f9faf3546091ec8b80c1bfb` 的 Actions run `32386630063` 中，普通
  `pytest` 与 `packaging-smoke` 成功；PostgreSQL 为 `141 passed, 1 failed`。唯一失败是测试夹具让
  observed `public_trend` 使用被 6B-5 Gate 禁止的 `user_structured_input` provenance，Repository 正确
  返回 `SOURCE_INVALID`；生产 Gate/migration/materializer 未放宽，失败 SHA 保留为审计证据。
- 唯一下一动作：提交最小测试 provenance 修复、推送并等待新 SHA 的 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke`。三 job 全绿后才允许状态收尾和 6B-7 交接。

## 2026-08-20：6B-6 exact-SHA 公共闭环与 6B-7 交接

- 最小测试 provenance 修复提交 `5531c81ec7117f5c454d320e406153086baae3ea` 已推送；Actions run
  `32387026797` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。
- 公共 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  为 `142 passed, 1 warning`，0006 upgrade/downgrade、FK/CHECK、source/supersedes trigger、partial
  unique、advisory lock、并发 expected-version、事务回滚和 `alembic check` metadata-head 均通过。
- Linux package smoke 真实执行 Candidate pending→accepted→Preference v1 active query；schema 1.3，
  value `zh-CN`，`external_riot_provider_calls=0`。这不证明真实 Riot/Provider、正式 Auth/RSO 或容量 SLA。
- 6B-6 与八维 coverage 正式关闭。当前只把 `6B-7-training-plan-progress` 标为
  prepared/waiting authorization；没有创建 Training Plan/Progress 产品代码，也未进入 6B-8/6B-9、
  SSE/前端、Redis/向量库、LangGraph、Multi-Agent、新 SDK 或真实外部调用。

## 2026-08-21：RQ-071 授权连续完成 6B-7/8/9，当前进入 6B-7

- 用户明确要求本轮连续完成 `6B-7→6B-8→6B-9`，无需逐步骤批准；RQ-071 已持久化。该授权不合并
  checkpoint，前一项仍须 exact-SHA 三 job 公共闭环后才能进入下一项。
- 6B-7 初学者教学和接缝审计已完成。ADR-0044 与专用 design/implementation plan 冻结：pending Candidate
  作为唯一 Plan draft；用户 accept 才物化 self-only active Plan；Progress 必须绑定 succeeded、published/
  degraded、report-available 的 final Artifact；纠错追加 superseding event；趋势只做确定性数值比较。
- 当前没有新增 Plan/Progress schema、migration、Repository、API 或产品测试；coverage 继续 `planned`，
  6B-8 Memory-aware Context 与 6B-9 lifecycle/export 仍未进入。
- 唯一下一动作：完成 6B-7 设计批本地门禁、独立提交/推送和 exact-SHA 三 job；全绿后按实施计划 Task 1
  写 pure Plan/Progress/trend 红灯。

## 2026-08-21：6B-7 设计批本地验证完成，等待公共门

- 完整本地 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；本机 PostgreSQL/Docker
  skip 如实保留。治理聚焦最终 `12 passed`，governance、两套 RAG、Harness dry-run、compileall、SDK/
  Secret/tracked-data、YAML 与 diff 门均通过。
- 当前裁决 `pass-local-pending-public-ci`。这只证明 ADR/design/plan 与既有回归兼容，不证明 Training
  Plan/Progress 产品能力已经实现。
- 唯一下一动作：设计批独立提交/推送并等待 exact-SHA 三 job；全绿后当前 checkpoint 保持 6B-7，内部
  动作切换为 Task 1 pure contract 红灯，不进入 6B-8。

## 2026-08-21：6B-7 设计 exact-SHA 公共闭环，进入 pure TDD

- 设计提交 `d678a7a93e7b5f04d5733b9c0abae4a26dc4dd1b` / Actions `32394585411` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- 该公共证据只关闭 6B-7 设计门，不表示 Plan/Progress 已实现。唯一下一动作是实施计划 Task 1：先写
  strict Plan/Progress payload、self-only shape、纠错与 deterministic trend 的 pure 红灯；不进入 6B-8。

## 2026-08-21：6B-7 本地实现完成，等待 exact-SHA 公共门

- Candidate-backed self-only Plan、一个 active partial unique、0007、同事务 lifecycle、完整 final Artifact
  Progress gate、不可变 correction event、deterministic trend、owner-scoped Service/API 和 production
  composition 已在工作树完成；不含 6B-8 Context 或 6B-9 lifecycle/export。
- 聚焦/相邻 `103 passed, 6 skipped, 1 warning`；完整 `1445 passed, 106 skipped, 1 warning,
  110 subtests passed`。新增 6 skip 均为本机无 PostgreSQL；真库 migration/FK/trigger/Artifact/concurrency/
  rollback 只能由公共 `postgres-migrations` 补证。
- package smoke 已扩为 schema 1.4 的 Candidate pending→user accepted→active Plan query，外部 Riot/Provider
  调用为 0；Progress 不借 package 的故意 failed Review 伪造成功 Artifact，真库测试单独构造严格 terminal fixture。
- walkthrough 已补八维 evidence 路径，coverage 在公共三 job 全绿前继续 `planned`。两套 RAG、Harness
  dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff 门通过。
- 唯一下一动作：独立提交/推送 6B-7 实现并等待 exact-SHA `pytest`、`postgres-migrations`、
  `packaging-smoke`；全绿后才将 coverage 置 complete 并进入 6B-8。

## 2026-08-21：6B-7 exact-SHA 公共闭环并进入 6B-8 设计门

- 6B-7 实现提交 `f6d89225ac5dbd568b6fad7c3c09b7c497c50762` 已推送；Actions run
  `32397290175` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。公共 pytest 为 `1445 passed, 106 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL 为 `151 passed, 1 warning`，0007 可逆且 `alembic check` 无新操作；Linux package schema
  1.4 完成 Candidate→active Plan query，`external_riot_provider_calls=0`。
- 6B-7 coverage 已置 complete。RQ-071 允许自动进入
  `6B-8-memory-aware-context-typed-turns / in_progress`，但不合并 checkpoint，也不进入 6B-9。
- 6B-8 接缝审计比较三种方案后，选择 run-scoped Memory-aware Context decorator：服务器派生 binding，
  PostgreSQL selector 只返回 legal active records，既有 ContextBuilder/ceiling 负责整记录预算，私有 manifest
  只保存 body-free identity/digest；terminal turn writer 只在 Task/Artifact/publication 全部验证后追加 Assistant。
- 当前只冻结 ADR-0045、专用设计和实施计划；没有 6B-8 migration/selector/context/turn-writer 产品代码。
  唯一下一动作是设计批本地门禁、独立提交/推送与 exact-SHA 三 job；全绿后从 pure contracts 红灯开始。

## 2026-08-21：6B-8 设计批本地门禁完成，等待公共验证

- 完整本地 pytest 为 `1445 passed, 106 skipped, 1 warning, 110 subtests passed`；106 skip 仍全部来自本机
  无 PostgreSQL/Docker，本设计没有新增真库成功声明。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均为 1.0、FPR 0.0，holdout abstention/citation
  均为 1.0；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/run-data、
  YAML、pip、governance 与 diff 门通过。
- 当前裁决 `pass-local-pending-public-ci`。这只证明 ADR/design/plan 与既有基线兼容，不证明 selector、
  manifest、Runtime binding 或 terminal Assistant 已实现。唯一下一动作是独立提交/推送设计批并等待
  exact-SHA 三 job；全绿后当前 checkpoint 保持 6B-8，内部进入 Task 1 pure contract 红灯。

## 2026-08-21：6B-8 实现、失败证据与 exact-SHA 公共闭环

- 初始实现 `65e69c8` 的普通/真库 job 在 governance 发现 walkthrough 漏提交，package 又暴露 Context smoke
  binding 失败；后续 `e4a7840` 的真实 PostgreSQL 发现 Profile fixture 使用非法 `MID`，正确合同为 `MIDDLE`。
  失败 SHA 均保留，没有放宽 schema、Gate、selector 或 owner scope。
- `f5130ca` 修正 fixture 并让 smoke 从服务器持久 Task binding 派生 Context；真库 157 项已绿。随后发现 Compose
  API/smoke owner 配置不一致，经 `c12f4db` 统一隔离 owner 后三 job 首次全绿。
- 最终 evidence 输出提交 `aacc11a1993e9d7d660f9d8d15b761dc641954b1` / Actions `32403187972` 也三 job
  completed/success。公共 pytest `1465 passed, 112 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
  `157 passed, 1 warning`；package schema 1.5 输出 Message+Preference+Plan 三类 Context、terminal Assistant 0、
  `external_riot_provider_calls=0`。故意 failed Review 不冒充成功模型回复。
- 6B-8 coverage 已 complete。当前按 RQ-071 进入 `6B-9-lifecycle-export-exit-review / in_progress`。

## 2026-08-21：6B-9 教学、接缝审计与设计冻结

- 对比“各 Repository 分散删除”“中央 lifecycle service + hidden_at + marker”“数据库 cascade hard delete”，
  ADR-0046 选择中央编排：同一 SQL 短事务先隐藏并创建 body-free marker，事务外文件清理，失败保持可幂等补偿。
- 三 scope 冻结为 `conversation_only`、`conversation_and_derived_memory`、`relationship_private_data`；Task/Run/
  Artifact 和全局 Player Subject 仍是独立生命周期。owner-global Preference 不因单 relationship 删除而消失。
- owner export 为有界 schema 1.0 snapshot；保留 decision/supersede/provenance 与 body-free Artifact refs，排除
  PUUID、Key、Prompt、Provider/Tool body 和内部异常。retention/purge 使用 injected clock、bounded batch 和
  Progress→Plan→typed target→Candidate→Message 的 FK-aware 顺序。
- 当前只有 ADR/design/implementation plan 与 coverage planned；0009、Repository/Service/API/package 产品代码
  尚未开始。唯一下一动作是设计批完整本地门禁、独立提交/推送和 exact-SHA 三 job。

## 2026-08-21：6B-9 设计批本地门禁完成

- 首次完整回归发现治理负例测试硬编码旧 6B-8 checkpoint；改为从 canonical front matter 动态读取后，治理
  聚焦 `12 passed`，未放宽 coverage/order 规则。
- 最终完整本地回归 `1464 passed, 113 skipped, 1 warning, 110 subtests passed`；113 skip 仍来自本机无
  PostgreSQL/Docker 与 Windows symlink，不冒充真库/Linux 证据。
- 两套 RAG 满冻结阈值，Harness dry-run `published`/0 revisions；compileall、pip、governance、SDK/Secret/
  tracked-data 与 diff 门通过。当前裁决 `pass-local-pending-public-ci`。
- 唯一下一动作：独立提交/推送设计批并等待 exact-SHA 三 job；公共全绿后才开始 Task 1 pure contracts 红灯。

## 2026-08-21：6B-9 本地实现与退出复核完成，等待公共门

- strict lifecycle contracts、0009 hidden columns/active unique/marker、owner-scoped export、三 scope visibility、
  cleanup compensation、retention/purge、薄 API/composition 与 package schema 1.6 已实现。
- 实现审查发现并修正 0009 CHECK 名的 naming-convention 双前缀风险；offline PostgreSQL SQL 已证明 0009
  使用真实 `ck_<table>_*` 名。隐藏 active target 后新链使用历史最大 version + 1，但不引用隐藏 predecessor。
- 首次完整回归仅有两个 OpenAPI exact-path 基线未登记三条新 endpoint；同步合同后最终完整回归为
  `1489 passed, 117 skipped, 1 warning, 110 subtests passed`。新增
  walkthrough/exit matrix 已覆盖八维 evidence，coverage 在公共三 job 全绿前保持 `planned`。
- 本机 PostgreSQL 测试仍明确 skip；真库 upgrade/downgrade、Repository scope/idempotency 与 Linux package
  export→conversation-only delete 必须由实现 SHA 的公共 job 补证。外部 Riot/Provider/Key I/O 为 0。
- 唯一下一动作：完成最终本地门禁、提交/推送实现 SHA 并等待 exact-SHA 三 job；全绿后才能把 coverage
  置 complete、正式关闭 6B-9/Session-Memory V1，并交接阶段 7 的 canonical 准备态。

## 2026-08-21：6B-9 exact-SHA 公共闭环、阶段 6 关闭与阶段 7 准备态

- 设计提交 `4bdb1bb9e720bd853c677ce2f650476f19ab6e41` / Actions `32404203265` 已完成
  exact-SHA 三 job，只证明设计门兼容。
- 实现提交 `2e37bd4e156d750634d67d64c07ddb4784f048f4` / Actions `32407862496` 的
  `pytest`、`packaging-smoke` 成功，真实 PostgreSQL 为 `163 passed, 1 failed`；唯一失败是测试夹具非法
  把 hidden Conversation 改回 active/null hidden，数据库正确拒绝 `conversation_lifecycle_irreversible`。
  产品 trigger/Repository/scope 未放宽。
- 最小测试修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` 删除非法 reset；Actions
  `32408101770` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部
  completed/success。公共 pytest `1490 passed, 116 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL `164 passed, 1 warning`，0009 upgrade/downgrade 和 `alembic check` metadata-head 通过。
- Linux package schema 1.6 在成功退出前断言有界 owner export、conversation-only delete 后 Conversation/
  Message 不可见、Preference/Plan 存续；console 输出 `external_riot_provider_calls=0`。这不证明真实
  Riot/Provider、正式 Auth/RSO、备份副本擦除、公网部署或容量 SLA。
- 6B-9 coverage 已 complete，6B-9、Session/Memory V1 与阶段 6 正式关闭。当前只交接
  `stage-7-standard-mcp-dynamic-meta-entry-design` prepared/waiting authorization；尚未开始标准 MCP/Meta
  教学、设计、实现或真实互操作。

## 2026-08-21：RQ-072 授权 Stage 7 入口设计

- 用户明确“那开始 stage7”，授权唯一 canonical 检查点
  `stage-7-standard-mcp-dynamic-meta-entry-design`；已清除等待授权原因，阶段 7 保持 `in_progress`。
- 初学者材料、现有 `ToolDefinition`/`ToolRegistry`/`ToolRuntime`、Application Service、Context/Memory、
  Harness/Runtime 接缝审计已完成；ADR-0047 选择 Adapter-first：MCP 协议 Adapter → 既有 ToolRuntime，
  外部动态 Meta → 有来源/patch/digest/freshness 的 data-only `MetaEvidence`。
- OP.GG 只登记为首选候选，尚未证明标准 endpoint/server、protocol/version、transport、schema、许可、
  freshness、限流或真实互操作；缺任一项就保持 candidate/deferred，不能把普通 HTTP POST 称为 MCP。
- 本检查点明确不安装 MCP SDK、不实现 Client/Server、不创建 Meta 产品代码、不读取 Key、不调用 OP.GG/Riot/
  Provider；后续顺序冻结为 pure contract → transport/discovery → OP.GG Meta Adapter → RiftCoach Server →
  real interoperability exit review。
- 四条进度线：本地代码仍无 Stage 7 产品实现；项目理解已有持久入口设计材料但 owner mastery 尚待复述；参考
  资料只完成路线/现有接缝审计，OP.GG 官方准入尚未完成；GitHub/部署仍只有设计门证据，尚无 Stage 7 真实互操作。
- 当前本地裁决：`entry-design-in-progress-no-external-io`。唯一下一动作是完成设计文档/coverage/治理与
  完整本地门禁，独立提交并等待 exact-SHA 三 job；公共全绿后才进入 `7-1-mcp-client-contract` 的 pure TDD。

## 2026-08-21：Stage 7 入口设计 exact-SHA 公共闭环与 7-1 交接

- 设计提交 `e50a54618157c84a545ad5786e6c820502f967ee` / Actions `32436092074` 精确对应，
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success；本地完整回归为
  `1489 passed, 117 skipped, 1 warning, 110 subtests passed`，117 skip 仍来自本机环境限制。
- ADR-0047、Stage 7 entry design、implementation plan、学习材料与八维 coverage 已正式闭环；该证据只证明
  边界/设计与既有基线兼容，不证明 MCP 产品代码、OP.GG 准入或真实外部互操作。
- 入口设计保持 no-I/O：未安装 MCP SDK、未实现 Client/Server、未读取 Key、未调用 OP.GG/Riot/Provider；
  OP.GG 仍是未经 endpoint/protocol/许可/freshness/互操作审计的 candidate/deferred。
- canonical 已交接到 `7-1-mcp-client-contract`，状态为 prepared/waiting authorization；其前置 coverage
  已 complete，新增 7-1 planned/order contract。授权前不得写 pure MCP contract 产品代码或接入 transport。
- 四条进度线：本地代码仍无 Stage 7 产品实现；项目理解有入口设计持久材料但 7-1 尚未教学；参考资料只完成
  现有接缝和 OP.GG 准入清单，未完成官方准入；GitHub/部署只有入口设计 exact-SHA 证据，尚无真实互操作。

## 2026-08-21：RQ-073 授权 7-1 MCP Client pure contract

- 用户明确“继续下一步”，授权 canonical 的 `7-1-mcp-client-contract`；等待授权原因已清空，checkpoint
  保持 `in_progress`。该授权不外推到 7-2 transport/discovery 或任何外部 I/O。
- 初学者控制流固定为 `initialize → capability gate → tools/list snapshot → allowlisted tools/call`：
  envelope 只描述消息是否合法，transport 才负责消息如何到达；两者必须分开测试和演进。
- 当前实施范围只含严格 pure models/errors：protocol version allowlist、tools capability、唯一有界目录、
  JSON Schema/arguments、schema drift、malformed/oversized result，以及不保存 remote message/data/body 的安全错误投影。
- 不安装 MCP SDK，不实现 stdio/HTTP/session transport，不调用 OP.GG/Riot/Provider，不读取 Key，不创建
  MetaEvidence 或 RiftCoach MCP Server，也不把 fixture/pure test 称为真实互操作。
- 唯一下一动作是先写 `tests/test_mcp_contracts.py` 红灯，再以 `app/mcp/models.py`、`app/mcp/errors.py`
  做最小实现；完成 walkthrough、全部本地门禁与实现 SHA 的 exact-SHA 三 job 前不关闭 7-1。

## 2026-08-21：7-1 本地实现与完整门禁完成

- `app/mcp` 已实现 transport-neutral initialize/list/call/result/error contracts：strict JSON-RPC、version
  allowlist、tools capability、immutable bounded schema/catalog、discovery+allowlist+arguments、server/catalog/schema
  drift 和 body-free JSON-RPC/`isError` 投影；没有 SDK、socket、subprocess、HTTP 或外部调用。
- 红灯先在 `ModuleNotFoundError: app.mcp` 处确认；最小实现与审查增强后，聚焦为
  `20 passed, 17 subtests passed`，相邻 Tool/Provider contracts 为 `55 passed, 62 subtests passed`。
- 完整本地回归为 `1509 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 仍来自既有本机
  PostgreSQL/Docker/Linux 限制。两套 RAG 满阈值，Harness dry-run `published/0 revisions`；compileall、pip、
  YAML、governance、SDK/Secret/tracked-data 与 diff 门全部通过。
- walkthrough 已覆盖八维 evidence，但 `coverage.yaml` 继续 `planned`。唯一下一动作是最终 cached diff 审查、
  独立提交/推送并等待 exact-SHA 三 job；全绿前 7-1 保持 open，不进入 7-2。

## 2026-08-21：7-1 exact-SHA 公共闭环与 7-2 交接

- 实现提交 `37f16bc54de1d6e41c3ae65ddc9d9c5e11efa4cb` 对应 Actions run `32439753589`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1510 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 为
  `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` 无漂移；Linux package schema 1.6
  成功且 `external_riot_provider_calls=0`。公共与本地计数按环境分别记录。
- 7-1 walkthrough/八维 coverage 已置 complete。证据只关闭 pure contract，不证明 transport、OP.GG、
  MetaEvidence、RiftCoach MCP Server 或真实外部互操作。
- 唯一下一检查点为 `7-2-mcp-transport-and-discovery` prepared/waiting authorization；当前停止，不写 7-2 代码。

## 2026-08-21：RQ-074 授权与 7-2 本地实现

- 用户明确“继续7-2”，等待原因清除；canonical 仍为
  `7-2-mcp-transport-and-discovery / in_progress`。
- 已先确认 `ModuleNotFoundError: app.mcp.client` 红灯，随后实现 transport-neutral
  `McpClientSession`、in-memory fixture、隔离 JSONL stdio、总 deadline、capability/discovery、
  disconnect/restart generation 和 `ToolDefinition` adapter；没有 SDK、普通 HTTP、OP.GG、Key 或外部 I/O。
- 7-2 聚焦 `11 passed`；7-1/7-2/ToolRuntime 相邻集合 `43 passed, 17 subtests passed`；完整本地回归
  `1520 passed, 117 skipped, 1 warning, 127 subtests passed`。RAG 两套门、Harness dry-run、compileall、
  governance、SDK/Secret/tracked-data/YAML/diff 门均通过；Docker 不可用，package smoke 仍待公共 CI。
- 八维 walkthrough 已写入 `docs/learning/7-2-mcp-transport-and-discovery-walkthrough.md`，coverage
  在 exact-SHA 公共三 job 前保持 `planned`。唯一下一步是最终 diff 审查、独立实现提交/推送与 exact-SHA
  三 job；全绿后才关闭 7-2，并只登记 `7-3-opgg-meta-adapter` prepared/waiting authorization。

## 2026-08-21：7-2 exact-SHA 公共闭环与 7-3 交接

- 实现提交 `f12166665d437a9479afff508709435a23096dd2` 对应 Actions run `32441793585`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest、真实 PostgreSQL migration/control-plane 与 Linux package smoke 均成功；package
  仍是既有 no-I/O smoke，不能外推 OP.GG、真实外部 MCP 或公网部署证据。
- 7-2 八维 walkthrough/coverage 已置 complete。证据只关闭本地 fixture/in-memory/隔离 stdio
  transport/session/discovery，不证明 OP.GG、MetaEvidence、RiftCoach MCP Server 或真实互操作。
- canonical 唯一下一检查点切换为 `7-3-opgg-meta-adapter` prepared/waiting authorization；授权前
  不执行 OP.GG 候选准入、MetaEvidence、Key 读取或外部调用。

## 2026-08-21：RQ-075 授权 7-3 OP.GG Meta Adapter

- 用户在确认官方候选仓库 `opgginc/opgg-mcp` 后明确要求继续正常下一步；该消息授权 canonical 的
  `7-3-opgg-meta-adapter`，不外推到 7-4 RiftCoach MCP Server 或 7-5 双向互操作退出门。
- 当前先核验官方 endpoint、协议/transport、工具 schema、许可、freshness、限流和部署边界；只有准入
  证据足够时才按 TDD 实现 bounded/data-only `MetaEvidence` 与 OP.GG 领域 Adapter。
- 本检查点不读取 Key，不调用 Riot/LLM Provider，不写 Memory/Candidate/Plan/Progress；有限外部探针只作
  候选准入，不冒充 7-5 exact-SHA 真实双向互操作证据。
- 唯一下一动作：完成候选准入审计并形成可版本化 fixture/裁决；若通过则写 pure normalization 红灯，
  若关键合同缺失则按 ADR-0047 fail closed 并记录 deferred/替代决策。

## 2026-08-21：RQ-076 修正 OP.GG 准入语义

- 用户明确指出“缺完整 provenance 就完全不接”会错误拒绝有价值的标准 MCP 能力。该纠正取代本轮早先
  `adapter_implementation_allowed=false` 的二元解释，但不删除真实缺口。
- 新裁决为 `admitted-with-restrictions`：实际 handshake/list/call 已证明官方 Streamable HTTP MCP 可达；
  7-3 继续实现真实 transport 与固定 lane-meta Adapter。因为 LoL 工具没有 outputSchema/structuredContent，
  只允许锁定 schema/字段并以无 `eval` 的 bounded grammar 解析。
- 本地 `retrieved_at/expires_at` 只证明“何时取回/本地缓存何时过期”，不能冒充上游数据生成时间；
  `upstream_patch` 与 `source_freshness` 明确为 unknown。允许 current snapshot recommendation，禁止精确
  patch 归因、跨 patch 历史比较和上游新鲜度声明。
- 唯一下一动作：先写 Streamable HTTP/session 与 partial-provenance MetaEvidence 红灯，再做最小实现；
  不进入 7-4，不读取 Key，不调用 Riot/LLM Provider，不写长期 Memory。

## 2026-08-21：7-3 本地产品实现与真实 smoke

- HTTPS-only/no-redirect Streamable HTTP、opaque session、initialized notification、bounded JSON/SSE、
  fixed local description/alias、admitted-subset catalog snapshot 与 ToolRuntime 单一可靠性所有权已实现。
- OP.GG lane-meta 文本经固定字段和 allowlisted AST grammar 变成 typed facts；partial MetaEvidence 记录
  digest/retrieved/expires/unknown patch/source time，只允许 current snapshot recommendation。Context 新增
  optional/non-instructional/user-role `external_meta_evidence`；不写 Memory/Candidate/Plan/Progress。
- 首次真实产品 smoke 在 tools/list 暴露 30-tool 目录中两个未获准 Valorant 数组 outputSchema；最小修复
  保留全响应 bytes/count 资源门，只严格解析业务 allowlist。相邻回归当前 `83 passed, 17 subtests passed`。
- 第二次产品 smoke 从官方 endpoint 到 Meta Context 全链成功并持久化 body-free 结果；只记录 protocol/
  catalog/evidence/context identity、fact count 与限制，不保存 session/raw text/事实正文。累计外部账本见专用设计；
  Riot/LLM Provider calls 与 Key reads 为 0。
- RQ-077 已持久化 Riot 官方账号/比赛/版本静态/patch update 与 OP.GG 聚合 Meta 的分层融合边界；本批不做
  两源 join，缺 patch 的 OP.GG 不继承 Riot patch 身份。
- ADR-0048、7-3 专用设计、walkthrough 与八维路径已建立，但 coverage 继续 `planned`。唯一下一动作是完整
  本地回归/全部治理门与 cached diff；通过后独立提交/推送并等待 exact-SHA 三 job。公共全绿前不关闭 7-3，
  不进入 7-4/7-5。

## 2026-08-21：7-3 最终本地门完成

- 最终聚焦/相邻为 `95 passed, 1 skipped, 17 subtests passed`；恢复后的提交前审查又补 negotiated
  protocol header、strict numeric scalar、真正的 admitted-subset parsing 与 complete-provenance identity 红灯，
  相关集合 `94 passed, 17 subtests passed`；完整 pytest 更新为
  `1545 passed, 117 skipped, 1 warning, 127 subtests passed`。117 skip 仍来自本机 PostgreSQL/Docker/
  Linux 环境限制，不视为真库或 package 成功。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation
  均 1.0；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/run-data、pip、
  YAML、governance、body-free evidence scan 与 diff check 全部通过。
- roadmap 总览、learning 索引、ADR-0047、Stage 7 设计/实施计划与 project decisions 的当前状态已同步；
  7-3 只证明单向 OP.GG lane-meta 产品链，不证明 7-4 Server 或 7-5 双向互操作。
- coverage 继续 `planned`。唯一下一动作是最终 cached diff、独立提交/推送并等待实现 SHA 的 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke`；三 job 全绿前不关闭 7-3、不进入 7-4/7-5。

## 2026-08-21：7-3 exact-SHA 公共闭环与 7-4 交接

- 实现提交 `64311a1751ed1c988b6ae6c2c67bdbe757fb9a94` 对应 Actions run `32455219404`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1546 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` metadata-head 无漂移；
  Linux package schema 1.6 成功且 `external_riot_provider_calls=0`。公共与本地计数按环境分别记录。
- 7-3 walkthrough/八维 coverage 已置 complete。该闭环证明官方 Streamable HTTP、获准目录子集、
  strict lane-meta Adapter、partial MetaEvidence、data-only Context 和一次 body-free 单向产品 smoke；
  不证明 OP.GG 全工具、精确 patch、上游 freshness、Riot+OP.GG join、RiftCoach Server 或双向互操作。
- 用户已按 RQ-078 授权当前唯一检查点 `7-4-riftcoach-mcp-server`；本批只实现协议 Server Session、
  owner-scoped read-only Application Facade、四个受限工具和 fixture TDD，不进入 7-5 真实双向互操作。

## 2026-08-21：7-4 本地实现与全部门禁完成

- 新增 transport-neutral `RiftCoachMcpServer`、独立 Session、in-process Client/Server transport、固定四工具
  catalog 与 `QueryMcpApplicationFacade`；owner 只从服务端 `ActorContext` 注入，Server 不监听网络、不直连
  Repository、不读取 Key，也不接受 PUUID、Prompt、URL、SQL、路径或开放 I/O 字段。
- `recent_summary` 交叉验证 receipt、Trace、manifest、`ExecutionValidatedSignal` 与 `PLAYER_SUMMARY` Artifact，
  只返回近期聚合、主要位置/英雄和胜负对照；`single_match_review` 只返回已发布报告 digest；知识搜索只返回
  attribution；评测工具明确 `score_available=false`，不从 publication 虚构 evaluator score。
- 聚焦 `33 passed`，相邻 MCP/Product `109 passed, 17 subtests passed`；完整本地回归为
  `1566 passed, 117 skipped, 1 warning, 127 subtests passed`。117 skip 仍来自本机 PostgreSQL/Docker/Linux
  环境限制，不冒充真库或 package 成功。
- 两套 RAG 满冻结阈值，Harness dry-run `published`/0 revisions；compileall、pip、6 个 YAML、SDK boundary、
  tracked Secret/run-data、body-free MCP evidence、governance 与 diff check 全绿。八维 evidence 已齐，
  coverage 在实现 SHA 的公共三 job 全绿前保持 `planned`。
- 唯一下一动作：最终 diff/cached 审查、独立提交/推送并等待 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke`；公共全绿前不关闭 7-4，不进入 7-5。

## 2026-08-21：7-4 exact-SHA 公共闭环与 7-5 交接

- 实现提交 `431c584c6f07731233e6e32fd6f98505a661f910` 对应 Actions run `32480827952`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1567 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` metadata-head 无漂移。
- Linux package schema 1.6 成功且 `external_riot_provider_calls=0`。该 package 仍是既有 no-I/O 产品纵向，
  不冒充公网 MCP Server 或外部 Client 互操作证明。
- 7-4 walkthrough/八维 coverage 已置 complete。该证据关闭受限 transport-neutral Server/Facade，
  不证明正式 Auth/RSO、TLS/限流、公网 transport、Riot+OP.GG join 或 7-5 双向互操作。
- canonical 只交接 `7-5-mcp-interoperability-exit-review` prepared/waiting authorization；授权前停止。

## 2026-08-21：7-5 exact-SHA 公共闭环、Stage 7 关闭与 Stage 8 准备态

- 实现 `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest
  `1577 passed, 116 skipped, 1 warning, 127 subtests passed`，真库 `164 passed, 1 warning`，
  Linux package schema 1.6/外部 Riot Provider 调用 0。
- 同一 clean implementation SHA 在 `2026-08-21T12:49:20Z–12:49:25Z` 唯一执行一次双向门：官方
  `@modelcontextprotocol/sdk@1.30.0` Client→RiftCoach stdio 与 RiftCoach Client→OP.GG Streamable HTTP
  均完成 initialize、initialized notification、tools/list 和一次 tools/call。OP.GG 继续为 partial
  provenance，不伪造 patch、source time 或 freshness；Riot/LLM/Key I/O 为 0。
- 不可覆盖 evidence 提交 `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736`
  精确对应该 SHA，三 job completed/success。公共 pytest
  `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`，migration 可逆且 metadata=head；Linux package schema 1.6、外部调用 0。
- 7-5 八维 coverage 已 complete，7-5 与 Stage 7 正式关闭。治理顺序原先终止于 7-5；本次按固定九阶段
  路线和既有 entry-design 命名规则，显式追加
  `stage-8-multi-agent-reliable-runtime-productization-entry-design` 到治理常量与 coverage ledger，
  作为唯一 prepared/waiting authorization 检查点，不把交接解释为 Stage 8 已开始实施。
- Stage 8 仍按 `8-Core` 必做交付线与 `8-Advanced` 至少一个证据驱动采用实验双轨；用户明确授权前，
  不开展教学/设计，不实现 Multi-Agent、DAG、cancel/resume、恢复、SSE/前端或生产部署。

## 2026-08-22：RQ-080 授权并启动 Stage 8 entry design

- 用户明确“那开始吧”，授权当前唯一检查点
  `stage-8-multi-agent-reliable-runtime-productization-entry-design`；本批不外推为 8A–8F 产品实现授权。
- 已完成初学者教学、现有 task/Runtime/Harness/Memory/MCP/Riot/Data Dragon/OP.GG/API 接缝审计；确认当前没有正式
  React/Next/Vite 前端脚手架，现有 Timeline、Run Query、Training Plan/Progress、Evidence 和 partial Meta 接缝可复用。
- ADR-0051 采用“可靠 Runtime Core + 证据驱动 Advanced”双轨，冻结
  `entry design → 8A → 8B → 8C → 8D → 8E → 8F`；Multi-Agent/DAG 仅在 Bad Case、对照、消融、成本和安全证据通过后采用，reject 也是合法结论。
- 8D 冻结 Riot 官方账号/比赛/Timeline、Data Dragon 静态、官方 patch/update 与 OP.GG partial Meta 的分层
  `EvidenceBundle`；缺 patch 的 OP.GG 不继承 Riot patch，不能声称 upstream freshness。
- 8E 冻结五个前端模块：电影感 Riot ID 入口、近期复盘工作台、Rift Timeline、Evidence/Agent Trace 抽屉、
  Training Plan/Progress；采用自主 React 设计系统，MotionSites 公开目录/预览和用户离线表只作为逐项资源审计输入。
- 本批入口设计没有读取 Key、调用 Riot/OP.GG/Provider/LLM、购买付费资源、修改产品 API/Runtime/DB 或创建前端代码。
- 当时本地裁决为 `entry-design-in-progress-no-product-io`，尚待本地门禁、独立提交/推送和 entry design
  exact-SHA 公共三 job；该条件随后已由下一节记录的 `3431e8b/32564500421` 满足。

## 2026-08-22：Stage 8 entry design exact-SHA 公共闭环与 8A 交接

- 入口设计提交 `3431e8b47dd992b6c4741e12158855feb64ef917` / Actions `32564500421` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 migration 可逆且 `alembic check` 为 metadata=head。
- Linux package smoke schema 1.6 成功，`external_riot_provider_calls=0`；两套 RAG、compileall、Harness
  SDK/Secret/tracked-data 边界与 dry-run 均通过。
- entry-design 八维 coverage 已置 `complete`。本检查点只关闭教学、设计、治理和采用门，不证明
  Multi-Agent、DAG、可靠恢复、Riot+OP.GG fusion、正式 Web/Auth/SSE、备份或部署已实现。
- canonical 唯一交接为 `8a-advanced-adoption-gate` prepared/waiting authorization；授权前停止。

## 2026-08-22：RQ-081 授权与 8A 本地实现门

- 用户明确“开始”后，当前唯一 checkpoint `8a-advanced-adoption-gate` 进入实施；8B–8F 未获授权且未开始。
- ADR-0052 固定串行 baseline、普通受限并行 comparator、角色隔离 Multi-Agent primary candidate；
  DAG/第三方 Runtime 与 Agentic Retrieval deferred，可靠 lease/recovery 路由到 8C Core。
- strict/body-free/no-I/O evaluator 绑定 case-set SHA
  `d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e` 与 gate digest
  `88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；holdout executions=0，
  external I/O=0。
- TDD 首红为缺模块；提交前两轮合同补强共 9 个负例也先红后绿，最终聚焦 `23 passed`、相邻 `129 passed`。
  完整本地 pytest `1600 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG 满门、Harness
  published/0 revisions、compileall/pip/YAML/安全/治理/diff 门通过。
- coverage 仍 planned。唯一下一动作是独立 implementation 提交/推送与该 exact SHA 的三 job；公共全绿后
  才关闭 8A，并只把 `8b-conditional-multi-agent-experiment` 置 prepared/waiting authorization。

## 2026-08-22：8A exact-SHA 公共闭环与 8B 准备态

- implementation `12ad83532d99990f5523d6ecc6def0b8a325d7d0` / Actions `32567642315` 三 job
  completed/success；公共 pytest `1601 passed, 116 skipped, 1 warning, 127 subtests passed`。
- 真库 `164 passed, 1 warning`，0001→0009 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`，image boundary 全绿。
- 8A coverage complete；其 `candidate` 结果不等于 Multi-Agent 已采用，holdout 仍未执行。
- canonical 唯一交接 `8b-conditional-multi-agent-experiment` prepared/waiting authorization；RQ-081 不授权
  8B。当前只完成独立状态收尾提交与 exact-SHA 三 job，授权前不写 8B 实验代码。

## 2026-08-22：8B holdout 前本地实现与完整门禁

- RQ-082 授权后已完成专用设计/实施计划、evaluation-only 三路 runner、typed/digest-bound Artifact、
  exact role/tool/Context、真实 `ReviewHarness`、strict semantic result validator、clean-SHA admission 与
  exclusive development/holdout output；产品 Runtime、Harness 与 MCP/Meta composition 未修改。
- TDD 从 2 个 collection error 到 14 passed；原子跨角色 tool preflight、expected holdout identity、CLI、
  duplicate/tamper/result recomputation 补强后聚焦 `22 passed`。正式 holdout path 只用重标记 development
  副本验证，三个 calibration-excluded rows 未执行。
- 相邻回归 `168 passed, 12 subtests passed`；完整 pytest `1622 passed, 117 skipped, 1 warning,
  127 subtests passed`。117 skip 仍是本机无 PostgreSQL/Docker/Linux 条件，不能冒充公共真库/package。
- 两套 RAG 满冻结阈值；Harness dry-run `published`/0 revisions；compileall、pip、39 YAML、SDK boundary、
  tracked Secret/run-data、governance 与 diff 门通过。external I/O 与正式 holdout executions 均为 0。
- 唯一下一动作：当前 checkpoint 仍为 `8b-conditional-multi-agent-experiment`；完整/cached diff 终审，
  独立提交/推送实现并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`。三 job 全绿前
  不得运行 clean-SHA development/holdout。

## 2026-08-22：8B implementation 公共门与唯一 holdout 裁决

- implementation `180bc8b452603572d010b6e25b14ed71f6470ce7` / Actions `32572085065` 三 job
  completed/success；公共 pytest 1623/116 skips/127 subtests，真库 164，package schema 1.6/外部调用 0。
- 同一 clean SHA 的 development 得到 `eligible_for_holdout` 后，正式路径在 case 前 exclusive reserve，
  calibration-excluded holdout 唯一执行一次；结果 strict/body-free validator 通过。
- holdout candidate latency improvement 18.95% 未达 20%，普通并行为 22.88%；二者 match/safe degraded/
  isolation 都是 1.0，hard gates 均 0。ADR-0053 裁决 `reject_multi_agent`，不重跑追绿。
- 结果 SHA `94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8`，experiment ID
  `0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494`，holdout executions=1、external I/O=0。
- result tests 后完整本地 pytest `1625 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG、
  Harness、compileall、pip、39 YAML、安全/治理/body-free/diff 门全绿，测试只复读结果。
- 唯一下一动作：当前 checkpoint 仍为 `8b-conditional-multi-agent-experiment`；独立提交/推送 result、
  ADR-0053、结果回归和 walkthrough，并等待该 exact SHA 三 job。全绿后再做 coverage/canonical 状态收尾。

## 2026-08-22：8B 关闭与 8C 交接

- result/ADR/evidence 提交 `783a329537682b5413d74af4cc3e1ac818f75da2` / Actions `32572610725` 三 job
  completed/success；公共 pytest `1626 passed, 116 skipped, 1 warning, 127 subtests passed`，真库
  `164 passed, 1 warning`，Linux package schema 1.6/外部调用 0。
- 8B coverage 已补齐八维并置 `complete`。ADR-0053 的产品裁决为 reject role-isolated Multi-Agent；bounded
  parallel 仅作为 8D 设计输入，不能解释为 8D 已实现。
- canonical 只交接 `8c-reliable-runtime-core` prepared/waiting authorization；8C 尚未实现，不能自动开始。

## 2026-08-22：8C 本地实现与八维证据完成，等待公共门

- RQ-083 已授权；Task 1–6 依次完成 pure contracts/projector、0010/ORM、Repository lease/event/fencing/
  cancel/replay、lease-aware Worker、proof-based recovery 与 owner-scoped HTTP seam。8B holdout 文件/SHA
  未覆盖、未重跑，外部 Riot/OP.GG/Provider/Key I/O 为 0。
- 真实 TDD 红灯覆盖缺模块/缺路由、event 时间篡改、`varchar(16)` 装不下 `recovery_required`、Worker
  terminal/cancel 最后一瞬竞态、queued cancel lifecycle，以及公共 operation identity/package replay 缺口；
  最后两个窄补强由 `2 failed` 变为 `29 passed`。
- 最新完整本地 pytest 为 `1670 passed, 133 skipped, 1 warning, 127 subtests passed`。133 skip 仍来自本机
  无 PostgreSQL/Docker/Linux 环境，不能冒充 0010 真迁移、并发 fencing/recovery 或 Linux package 成功。
- `docs/learning/8c-reliable-runtime-core-walkthrough.md` 与 coverage 八维路径已建立；公共三 job 全绿前
  coverage 保持 `planned`，checkpoint 保持 `in_progress`。
- 唯一下一动作：运行两套 RAG、Harness dry-run、compileall/pip/YAML、SDK/Secret/tracked-data/body-free、
  governance 与 diff/cached diff 全部门禁，独立提交/推送 implementation/evidence，再等待 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke`。公共全绿后才关闭 8C 并只交接 8D prepared。

## 2026-08-23：8C 公共 CI 修复批本地完成

- 公共 run `32579514636` 的两个失败根因已由真实日志确认：0010 downgrade 裸约束名触发 naming convention 双前缀；queued task 的 JSONB Python `None` 被写成 JSON `null`，违反 checkpoint shape。
- 最小修复已完成：`_drop_reliable_task_constraints()` 统一使用 `op.f(...)`；`ReviewTaskRecord.checkpoint_reference` 使用 `JSONB(none_as_null=True)`。
- 新增离线 downgrade 约束名回归、ORM metadata `none_as_null` 回归与真实 PostgreSQL queued-insert 回归；最新完整本地 pytest 为 `1672 passed, 134 skipped, 1 warning, 127 subtests passed`。
- 两套 RAG 均满门，Harness dry-run 为 `published`/0 revisions，compileall、pip、SDK/Secret/tracked-data、governance 与 diff check 通过；本机 PostgreSQL/Linux skip 仍不能冒充公共证据。
- 当前唯一下一动作：提交并推送 repair implementation，等待同一 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job；公共全绿前 coverage 保持 `planned`，不进入 8D。

## 2026-08-23：8C 第二轮公共 CI 兼容性修复

- 最新 repair run `32584144522` 的 migration downgrade 已通过，`pytest` 已通过；真库仍发现三类兼容性缺口：既有终态 fixture/legacy row 的 heartbeat 为空且 generation 为旧默认 0，以及 JSONB checkpoint 以 JSON 字符串时间戳读回时被 strict Pydantic 误拒。
- 终态不再把运行期 heartbeat 误设为必填，并允许旧终态 generation 0；`running/recovery_required` 仍要求 heartbeat/generation。Repository 通过 strict JSON wire parsing 读取 JSONB checkpoint，保留字段/类型合同，不放宽任意 Python coercion。
- 当前新增本地回归覆盖 checkpoint JSON round-trip；最新完整本地回归和横向门需在此轮修复后重跑，公共全绿前 coverage 继续 `planned`，不进入 8D。

## 2026-08-23：8C 第三轮真库兼容修复

- `b2b4737` 对应公共 run `32584944802` 已通过 pytest；migration 真库由 34 个失败收敛至 2 个，证明终态 generation/heartbeat 与 checkpoint claim 修复有效。
- 新发现并已修复：recovery requeue 仍有一处旧 strict dict parse；package smoke 已走到 owner-scoped event query，JSONB wrapper 兼容路径已补强；既有纵向测试缺 `timedelta` 导入也已修正。
- 当前待提交最新 repair；coverage 保持 `planned`，不进入 8D。

## 2026-08-23：8C 第四轮 event JSONB 边界修复

- 最新 SHA 的 migration 与完整 PostgreSQL job 已全绿，package smoke 唯一失败为 event replay query；task checkpoint 已修复但 event checkpoint 仍默认把 Python `None` 当 JSON `null`。
- `ReviewTaskEventRecord.checkpoint_reference` 现与 task row 一样使用 `JSONB(none_as_null=True)`；这是无 schema 变更的存储映射修复，公共 event DTO 仍 body-free。
- 当前待提交/推送该最小修复；coverage 继续 `planned`，不进入 8D。

## 2026-08-23：8C clean implementation exact-SHA 公共闭环与 8D 交接

- 根因最终定位为 deployment composition 的 `_TaskServiceProxy` 漏掉了新可靠任务 API 的
  `request_cancel` 与 `read_events` 转发；Repository、`ReviewTaskService`、事件解码和公开 DTO
  本身均已通过真库/聚焦测试。修复同时新增 composed-app cancel/event 回归，未扩大权限或公开内部 lease 字段。
- clean implementation `2df5349d85e48138c05d6293d4e3885b6b4756ec` / Actions `32587659678`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success；公共 job
  验证了 PostgreSQL 0010 可逆迁移、真实 claim/heartbeat/fencing/cancel/checkpoint/recovery/event replay、
  Linux package no-I/O vertical 与非 root/image boundary。
- 本地完整回归为 `1673 passed, 134 skipped, 1 warning, 127 subtests passed`；两套 RAG 的
  Recall/MRR/nDCG/FPR 均 `1.0/0`，independent holdout 的 abstention/citation 均 `1.0`；Harness
  dry-run 为 `published`/`0 revisions`；compileall、pip、SDK/Secret/tracked-data、governance、diff
  全部通过。134 skip 只表示本机没有 PostgreSQL/Docker/Linux，真实结论由该 exact-SHA 公共 job 提供。
- 8C 八维 learning/engineering coverage 已置为 `complete`，checkpoint 正式关闭。下一检查点只登记为
  `8d-riot-opgg-evidence-fusion-core / prepared / waiting authorization`；授权前停止，不读取 Key、
  不调用真实 Riot/OP.GG/Provider/LLM，不实现 8D、8E 或 8F。Multi-Agent 产品 reject 与 8B 唯一 holdout
  SHA `944258...445e8` 保持不可覆盖、不可重跑。

## 2026-08-23：RQ-084 授权并启动 8D Evidence Fusion

- 用户明确继续正常下一步，授权唯一 checkpoint `8d-riot-opgg-evidence-fusion-core`；README/作品集的广泛
  样本研究按 RQ-085 留作 8F 横向输入，不插队或阻塞 8D。
- 已完成初学者教学、现有 Riot/Data Dragon/OP.GG Meta/Context 接缝审计与三方案比较。ADR-0055 采用
  immutable typed `EvidenceBundle` + pure fusion kernel，拒绝无类型 JSON merge，暂缓通用 claim graph。
- `app/evidence/` 已本地实现 strict Riot match、Data Dragon、official patch、join/conflict/gap/claim/
  confidence contracts、existing Summary no-I/O adapter、canonical bundle digest 与 allowlisted public projection。
- TDD 首红为 `ModuleNotFoundError: app.evidence`；最小实现和 Pydantic dataclass 边界修复后 focused 为
  `18 passed`，相邻 OP.GG Meta/Context 合计 `48 passed`。partial OP.GG 可支持 current snapshot，但不能继承
  Riot patch 或取得 exact-patch claim；missing/expired/mismatch 均结构化降级。
- 当前 8D 仍 `in_progress`，coverage `planned`。唯一下一动作是独立提交/推送当前 implementation/evidence，
  等待 exact-SHA 三 job；公共全绿前不关闭 8D、不进入 8E。

## 2026-08-23：8D exact-SHA 公共闭环与 8E 交接

- implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions `32598480400` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1692 passed, 133 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17 为
  `186 passed, 1 warning`，0001→0010 migration 可逆且 `alembic check` 无新 upgrade；Linux package
  schema 1.6、`external_riot_provider_calls=0`、非 root/image boundary 全绿。
- 8D 以 strict Riot/Data Dragon/official patch/OP.GG partial source contract、canonical EvidenceBundle digest、
  explicit join/provenance/freshness/conflict/gap/claim、Summary/Data Dragon no-I/O adapter 与 public projection
  完成八维证据。partial OP.GG 不能继承 Riot patch/source time/freshness，版本冲突保留双方并降级。
- 该闭环不证明真实刷新、全部 OP.GG 工具、Riot/OP.GG 本轮网络 I/O、EvidenceBundle 持久化、React/SSE/Auth/
  HTTPS/备份或公网部署。8D coverage 置 `complete`；canonical 交接 `8e-productization` prepared/waiting
  authorization。

## 2026-08-23：RQ-086 授权 8E preflight 与一次真实 OP.GG 验证

- 用户授权一次真实 Riot + OP.GG 验证并进入 8E preflight，同时要求前端分小批推进；用户账号不能硬编码
  为 ShowMaker，必须支持用户自填外服 Riot ID、选择自己的账号或以 `observed/public_observed` 分析
  职业选手/高手账号。该要求已持久化为 RQ-086，ADR-0056 和 preflight 计划已创建。
- 本轮只读检查确认仓库没有 ShowMaker 硬编码；`POST /player-links` 已支持 `riot_id`、
  `routing_region` 和 `relationship_role`，Conversation 绑定稳定 player subject；旧 `/reviews/recent`
  仍受环境 `RIOT_REGION` 默认影响，列为 8E legacy 地区审计缺口。
- 真实 OP.GG gate 已执行一次并通过：endpoint `https://mcp-api.op.gg/mcp`，协议 `2025-06-18`，
  server `OP.GG MCP Server 1.0.0`，只调用 `lol_list_lane_meta_champions` 1 次，top 位置 3 条 fact，
  body-free evidence digest `24b49ea9eb9c4c6c6ee682ad21309c7a643fbdde70a8ea18ba8fdf1d26a8c1ec`；结果文件为
  `data/evaluation/results/mcp/opgg_external_validation_2026-08-23.json`。限制仍为 partial provenance、
  patch/source time/upstream freshness unknown，只允许 current snapshot recommendation。
- Riot Key 存在但未输出；`DK ShowMaker#KR1 / asia / observed` 的 Account/Match gate 已通过，结果为
  `data/evaluation/results/riot_external_validation_2026-08-23-v2.json`，3 次 Riot calls、1 局详情、
  PUUID digest only。随后真实 OP.GG `mid` replay 以 `opgg_meta_result_invalid` fail-closed，结果为
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23.json`；不保存 Key、PUUID、原始 response，
  不自动跨区重试，也不放宽 8D parser。
- 当前 preflight 下一动作改为：对真实 OP.GG mid schema drift 做安全诊断/回归裁决，之后再冻结 player
  profile list/selection DTO；该上游适配问题解决或被明确降级前，不把 8E 前端接到未解释的 Meta 数据上。
- preflight 文档/脱敏证据提交 `8c0cc187e93e76c26e9d03f9e8f2371333c783a3` 的公共 Actions run `32611044101`
  已完成 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job success；该 run 只验证持久合同/现有
  no-I/O package，没有把 OP.GG 网络调用放入 CI。

## 2026-08-23：8E schema-drift 诊断接缝完成（live 字段级证据仍待授权）

- `app/meta/opgg.py` 现在可在 fail-closed 时生成 `OPGGMetaSchemaDiagnostic`；只允许 stage、position/row、allowlisted 字段位置、AST 节点类型、长度和摘要 hash，原始正文/字段值不进入异常或持久结果。
- `data/evaluation/results/mcp/opgg_mid_schema_drift_fixture_v1.json` 与 `tests/test_opgg_meta_adapter.py` 固化受控 null-like 非字面量回归；该 fixture 明确不是 live upstream 证据。
- ADR-0057 记录“先诊断、后裁决；不因真实失败放宽 parser”的边界。现有真实结果仍只承认 `opgg_meta_result_invalid` 与 stack-level `row_field` 失败；没有新的明确外部授权时不重跑 OP.GG。
- 当前唯一下一动作：若获新的有界授权，执行一次真实 `mid` replay 读取字段级 body-free diagnostic；随后再裁决扩大 allowlist/degraded，并冻结 player profile selection DTO。前端仍未开始。
