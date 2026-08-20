# RiftCoach 持续开发计划

## Goal

在不改变既定阶段 0-8 和用户已确认子阶段的前提下，以可恢复、可审计、逐步
教学的方式推进 RiftCoach；任何当前状态都必须由仓库文件和测试证据支持。

## Current Phase

Phase 20 - `6B-4-conversation-bound-recent-review-identity` is complete at
`d63f908` / Actions `32347834279`. Phase 21 -
`6B-5-memory-candidate-write-gate` is complete at `dd7c9c8` / Actions
`32376405150`. Phase 22 - `6B-6-preferences-profile-review-memory` is in progress
under RQ-070. The design batch is frozen in ADR-0043 and the dedicated 6B-6
design/implementation plans. The local typed-target vertical slice is implemented;
Task 7 is performing final review, regression, and exact-SHA public closure.

## Phases

### Phase 1 - 修复项目治理与上下文连续性

- Status: complete
- 建立根级工作约束、唯一当前状态和追加式需求账本。
- 启用本计划指针，并修正互相冲突的路线状态。
- 验证文档一致性和现有代码回归。

### Phase 2 - 5C-4 Rejection / Ambiguity 检查点

- Status: complete
- 在继续代码复核前，为活动计划、唯一下一步和需求账本增加机器可检查的预检。
- 讲清拒绝与歧义为什么是 Router 的安全边界。
- 审查已经提前写出的代码和测试，不以“代码存在”代替本检查点验收。
- 只在发现缺口时做最小修补，并等待用户确认后推进。

### Phase 2.5 - 5C-5 前置 Skill 时序裁决

- Status: complete
- 本项是进入 5C-5 前的决策门，不是新增主阶段或替代原 5C-5。
- 先形成用户 Skill / 内部 Skill 的初步方案，再回到 Harness/Evaluation 源码复核。
- 发现事实审查已有完整 `EvaluatorStep` 后，用 ADR-0009 取代未实现的内部 Skill
  方案；保留事实审查能力，但不复制为第三个 Skill。

### Phase 2.6 - 5C-5 第二个真实 Skill 准备

- Status: complete
- `5C-5-prep-1`：Skill Invocation Contract，写代码前取消。
- `5C-5-prep-2`：创建用户可路由的 `single-match-review`。
- `5C-5-prep-3`：内部 `report-fact-check` Skill，写代码前取消。
- 明确单局输入输出、触发边界、工具权限、预算、步骤和成功标准。
- 本项完成后才进入 Phase 3；不创建 `report-fact-check` Skill。

### Phase 3 - 5C-5 Router Evaluation 收尾

- Status: complete
- 审计开发集覆盖、指标、门禁和局限。
- 区分 development/calibration 与 independent holdout。
- 记录可复现的最终基线，但不夸大泛化能力。

### Phase 4 - 5C-6 Model Fallback Decision

- Status: complete
- 根据真实 Bad Case 和 5C-5 证据决定暂缓还是引入模型兜底。
- 记录收益、风险、替代方案和采用门槛。
- 本阶段是决策门，不默认需要编写 LLM Router。

### Phase 5 - 进入 5D 前复核

- Status: complete
- 只有 5C-1 至 5C-6 全部完成后，才把唯一下一步改为 5D。
- 对照路线、能力矩阵、需求账本和测试，确认没有遗漏或越级。

### Phase 6 - 5D Python 受限 Agent Loop

- Status: complete
- `5D-entry-design` 已完成：审计现有接缝、比较三种组合方案并接受 ADR-0011。
- `5D-1` 已完成：统一 Skill I/O 文本、selected name/version、安全 run ID、Harness
  规范输入摘要和 Catalog-backed 执行前校验。
- `5D-2` 已完成：两个 Skill 的 allowlisted 最小上下文、信任标签、确定性
  `ContextSizer`、整段预算选择和不可信知识引用投影均已有 TDD 证据。
- `5D-3` 已完成：Manifest-only `AgentRunCompiler`、完整消息估算、逐轮累计 Context
  门禁和协作式总 deadline 均已有 TDD 证据。
- `5D-4` 已完成：共享知识 evidence converter、`SkillAgentDraftPreparer`、两个真实
  Skill 的 Fake Provider + 真实 `knowledge.search` 以及 provenance/失败边界均已有
  TDD 证据。
- `5D-5` 已完成：统一 `DraftPreparationStep`、旧顺序 Adapter、唯一 ReviewHarness
  控制流、`SkillReviewExecutor` 和 Artifact 驱动 typed terminal output 均已有 TDD
  证据；两个真实 Skill 已通过 Fake Provider + 真实本地知识工具的完整组合测试。
- `5D-6a` 已完成：`StructuredResponseContract` 贯通 ChatRequest、Capability
  Negotiation 与 `llm.chat`；严格 Pydantic Evaluation Schema、最多一次同合同
  repair 和 Harness fail-closed 降级均有 Fake Provider TDD 证据。
- `5D-6b` 已完成（部分采用）：disabled-thinking 下 P1-P5 低层协议 5/5 真实通过；生产
  `ZhipuProvider` 已用离线 TDD 映射四类消息、JSON mode、Function Calling、请求级
  工具别名与 fail-closed 响应边界；精确 3-call Adapter Protocol Slice 已经真实
  3/3 passed 并 admitted；Recent-form Domain Slice 真实运行只执行一次，在一个领域
  call 后没有形成统一 `ChatResponse`、工具证据或 Evaluation，领域 `admitted=false`，
  Harness 安全降级；ADR-0012 准入最小协议、拒绝领域能力并暂缓第二 Provider。
- `5D-7` 已完成：Batch A 已以真实 Bad Case 冻结分层 Dataset/Candidate/Result 合同、
  development/held-out 生命周期和 10 案例离线基线；Batch B 已以双层语义指纹冻结
  Skill、Context、知识工具、Evaluation 与 demo 案例身份，并建立零外部调用 admission。
- `5D-7` Batch C 已完成：7 个 `offline_executable` development 场景先通过 Batch B
  admission，再真实经过 Skill、AgentLoop、ToolRuntime、本地 RAG 和 Harness；工具、
  事实、引用、用户/RAG 注入及一个真实 unsafe-publication 开发 Bad Case 均有 TDD 证据，
  外部调用为 0。它不代表真实模型能力或 held-out 结果。
- `5D-7` Batch D 的 D1-D2 已完成：保留 `coach_evaluation@1.0.0` 历史复现，新增并接入
  `coach_evaluation@1.1.0` 安全评测输入/输出与不可修订 blocking policy；secure offline
  executable development 7 场的 task/failure accuracy 均为 `1.0`，unsafe publication 为
  `0.0`，external calls 为 `0`。D3 已创建 3 场独立 held-out，并通过防污染/显式确认门；
  当时尚未运行；本计划后文已记录其后唯一一次真实执行和拒绝结果。
- `5D-7` Batch D D4 已完成并更正候选：ADR-0018 取代 ADR-0017 的模型选择，改用
  DeepSeek 官方 `deepseek-v4-pro` 作为唯一有界第二 Provider 候选；独立 Adapter、同任务
  3 场比较、安全失败分类、最多 15/12 calls、Token/停止规则不变，DeepSeek 金额停止线
  调整为 `$0.10`；D4 及本次更正的外部调用均为 0。
- `5D-7` Batch D D5 已完成离线实现：独立 `DeepSeekProvider`、跨 draft/Harness 的
  安全失败观察、实验级 call/Token/金额 ledger、Provider/global stop 与 no-I/O
  preparation 均有 TDD 证据；完整回归为 `505 passed, 103 subtests passed`，真实
  Provider calls 和 held-out executions 当时均为 0。随后 real-gate execution seam 在
  exact-SHA CI `31767405927` 通过后只运行一次：DeepSeek V4 Pro structured 与 Agent
  tool round trip 均 passed，3/3 calls、1428 tokens、估算 `$0.00221496`，协议
  `admitted=true`；held-out executions 仍为 0。
- `5D-7` 领域 held-out 执行接缝已完成本地设计/TDD 和 exact-SHA 公开 CI：控制面
  admission 不接收
  Provider；已准入协议的 3 calls/Token/金额会继承到累计 ledger；scope 和单案例分别
  固定 12/4 calls 与 12000/4000 observed tokens；逐例分层判分后首错停止，unsafe
  publication 全局停止；输出可在 Provider 前独占预留且只保存白名单观测。合成
  Provider/Executor 不是 held-out 运行或模型质量证据。提交
  `7986e1ade9ab165b4b2916a62b067587c5c3f027` 的 GitHub Actions run `31785253957`
  completed/success。
- `5D-7` 真实 DeepSeek V4 Pro 领域 held-out 已获显式确认并只执行一次：首个正常案例
  消耗 1 个领域调用，Adapter 因响应含未准入的并行工具调用返回
  `unsupported_parallel_tool_calls`；没有规范化响应、工具执行、知识证据或 Evaluation，
  Harness 安全降级，后两场按首错停止跳过，领域 `admitted=false`。结果 SHA-256 为
  `fbd1251af98daa9e767de56a35100025807ce96026d6b3b3497e33dd30ad989e`；不得重跑追绿。
- `5D-7` ADR-0022 本地离线 TDD 已完成：DeepSeek Adapter 可严格双向传输多 ToolCall
  批次且仍不声明并发；AgentLoop 对批次预算、越权和重复做零副作用原子预检，再按顺序
  执行。新 development 案例使用 Fake DeepSeek SDK，真实经过 AgentLoop、本地 RAG、
  Secure Evaluation 1.1 与 ReviewHarness 并发布；外部调用为 0，旧真实拒绝结论不变。
- 该实现已提交为 `037a47fecf058b2430efeeb59858e24cdb3b28eb`，GitHub Actions run
  `31817798170` 对精确 SHA completed/success；公开验证没有读取 Key 或调用 Provider。
- `5D-7` Fresh-Gate 设计已完成：ADR-0024 选择复用现有 no-I/O admission、薄协调器、
  production Executor、分层 Evaluator 与唯一 Harness，同时重新冻结匿名 fixture、
  Dataset、输入计划和三个实际案例的 Prompt/Context 摘要。旧协议/拒绝结果和修复 CI
  组成只读历史证据链；正式新 held-out 必须等兼容合同的 development TDD 与 exact-SHA
  CI 完成后才创建。设计提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已通过
  GitHub Actions run `31859717836`。
- `5D-7` Fresh-Gate 1 本地离线 TDD 已完成：旧 input-plan/Prompt-Context V1.0 保持兼容；
  新 V1.1 plan 必须绑定三个逐案例 Context 摘要；历史 3 次协议 + 1 次失败领域调用、
  ADR-0022 修复 commit/CI 与当前 code/public-CI 已进入 development-only no-I/O
  admission。聚焦 33、相邻 51、完整 `568 passed, 103 subtests passed`，两套 RAG、
  compileall、Harness/secret boundary 和 dry-run 通过；Provider calls/held-out executions
  均为 0。实现提交 `adba965a7f7fb4293020502b4440e9880633e571` 已通过 GitHub
  Actions run `31860874440` 的 exact-SHA 公开 CI。
- `5D-7` Fresh-Gate 3 已本地完成：新的匿名 3 局 fixture/确定性报告、三案例 held-out、
  V1.1 input plan 与三个实际案例的 body-free Prompt/Context snapshot 已创建；新旧
  fixture bytes、case ID、输入措辞、知识注入正文和 marker 均不复用。聚焦 `39 passed`，
  完整回归 `574 passed, 103 subtests passed`，两套 RAG、compileall、Harness/secret
  boundary、dry-run、governance 和 diff check 通过；Provider calls/held-out executions
  均为 0，正式结果文件不存在。资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8`
  已通过 GitHub Actions run `31861960565` 的 exact-SHA 公开 CI，Fresh-Gate 3 已完成。
- `5D-7` Fresh-Gate 4 入口已本地完成：新增完整 readmission/evidence envelope，绑定历史
  `3+1` 调用、修复 CI、资产 CI、当前 code/public-CI、新 Dataset/plan/fixture 与逐案例
  Context；现有生产 CLI 已使用 V2 profile 并提供 `--prepare-only`。Fake Provider 的正常
  纵向装配、1-call 首错停止、脱敏和不可覆盖均通过；相邻 `93 passed`，完整
  `580 passed, 103 subtests passed`，外部调用和真实 held-out 执行均为 0。
- Fresh-Gate 4 实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过 GitHub
  Actions run `31863341338`；同一干净 SHA 的真实 `--prepare-only` 已 no-I/O admitted，
  external calls 0、held-out 未执行且正式结果文件不存在。
- 用户明确确认后，V2 在公开成功 SHA `741e84140f816fb4b06b2812a8d07d3f32eaf4d0`
  上只执行一次：首例 1 call/3440 observed tokens，下一调用因需预留 1024 output 而超过
  单例 4000-token 门，在 I/O 前停止；Harness 安全降级、后两例 skipped、
  `admitted=false`。结果 SHA 为 `877b623f...dc62a`，不得覆盖或重跑。
- 结果归档提交 `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 已推送，GitHub Actions
  run `31864370988` 对精确 SHA completed/success；公开 CI 不含 Key 或 Provider I/O。
- `5D-7` V2 预算可达性离线裁决已在本地完成：ADR-0025 要求未来真实领域门在 Key-last
  之前证明资源合同可达。精确 V2 Usage 证明第二次调用至少需要单例 4464-token 上限，
  当前 4000 必然不可达；现有生产控制流本地形成初始 Agent、工具后 Agent、Evaluation
  三类 request envelope，长度单位为 6666/7774/6266，以首轮真实 3241 input 校准后的
  input 投影为 3241/3780/3047。投影不冒充 Provider tokenizer，也不直接决定 V3 预算。
  新实现、严格 JSON 裁决和 6 个聚焦测试均不接受 Provider/Key/网络输入，外部调用为 0。
- 预算裁决提交 `78400b9310e512668c81ca41cd65623a92a27226` 已通过 GitHub Actions run
  `31865285994` 的 exact-SHA 公开 CI；V2 裁决正式完成，旧结果仍为 `admitted=false`。
- 5D-1、5D-2、5D-3、5D-4、5D-5、5D-6a、5D-6b、5D-7 和 exit review
  均已逐项验收；5D 整体完成但阶段 5 仍在进行中。
- `5D-7 review` 已按 ADR-0028 完成：评测合同、实验身份、注入阻断、held-out 生命周期、
  资源/错误合同和真实负面结果足以完成评测门；当前没有领域 Provider 获得准入，质量
  保持 unknown。G53 deferred 和 Flash 未测试不再阻塞 5D-7，但仍受各自重新采用门约束。
- `5D-exit-review` 已完成：入口设计十项功能要求与 5D V1 非功能边界均有实现和跨层
  测试证据；没有发现必须留在 5D 修复的结构性代码缺口。当前无领域 Provider 准入、
  真实注入未执行和性能/Usage unknown 均保留为限制，不阻塞厂商无关的 5E 入口设计。

### Phase 7 - 5E AgentRuntime V1（父阶段追踪）

- Status: complete
- 入口设计与 ADR-0029 已完成：采用薄 Runtime + 可选观察端口，不采用外层事后回放或
  事件溯源/DAG 重写；
- 5E 内部固定为 5E-1 合同/Usage/Trace Store、5E-2 observable run、5E-3 live stream
  parity、5E-4 evaluation/exit review；
- 5E-1 严格模型、Recorder、不完整 Usage 和原子 Trace Store 已完成并通过 exact-SHA CI；
- 5E-2 入口审计/设计与 ADR-0030 已公开完成；Task A 合同 1.1、1.0 读取兼容、默认关闭
  observation port、missing Usage、lifecycle 与 prospective terminal 已通过
  `2e78c96` / Actions `31947625293` 的 exact-SHA 公共验证；Task B Observed Provider、
  AgentLoop 业务 Tool/terminal 与 ToolRuntime observation fail-fast 已本地完成并通过
  81 项聚焦、721 tests/110 subtests 全量回归，提交 `28bd910` / Actions `31952026988`
  exact-SHA 公共验证成功；该句记录的是 Task B 当时边界，后续 5E-2/5E-3 已完成 Harness observer、
  统一 run 与进程内 stream，并由本计划后续证据闭环；
- ReviewHarness 继续是唯一发布权，Runtime 状态与 publication 状态分开，Trace 只保存
  安全元数据和 Artifact 引用；
- 不调用真实 Provider、不切换默认模型、不引入 LangGraph/Pi/Claude Agent SDK；这些采用
  实验仍属于 5F，Prompt Program 属于 5P。

### Phase 8 - 5F-5-adoption-decision-exit-review

- Status: complete
- RQ-051 已清除等待确认状态；当前只作 Pi 最终采用与 5F 退出裁决，不补做 5F-4。
- 5P Prompt Program V1 与早期产品纵向切片已完成；5P-6 退出审查以
  `8c8acc6` / Actions `32010604551` 完成 exact-SHA 公共闭环。
- `5F-entry-design` 已由 `ce97975` / Actions `32013948784` 完成 exact-SHA 公共闭环；用户已按
  RQ-048 恢复 `5F-1-pi-source-license-contract-audit`。
- 本地审计已冻结官方 `earendil-works/pi` release `v0.84.2` / commit `914cf147...`、两个候选包、
  MIT 许可证和 Node `>=22.19.0`，并完成 Agent/Provider/Tool/event/state/abort/Usage 映射。
- 本地裁决为“允许有条件进入 5F-2”：只允许低层 Agent Core、Scripted StreamFn、单一
  `knowledge.search`、sequential 和安全 JSONL sidecar；不允许 coding-agent 默认工具/Session/
  ResourceLoader，且必须补整批 Tool 预检、Usage completeness、deadline/kill 和 body-free event
  projection。5F-1 审计当时未安装 Pi 或实现 adapter。
- 5F-1 审计提交 `5901b09` 已由 Actions run `32016852979` 完成 exact-SHA 公共验证；5F-1
  正式闭环；用户已按 RQ-049 恢复 5F-2。
- ADR-0035 与 5F-2 实施计划已冻结低层 Agent Core + 版本化限长 JSONL sidecar、Scripted
  StreamFn、单一 Python `knowledge.search`、父进程 deadline/kill 和 body-free event 边界；
  exact lockfile、Pi sidecar、Python controller、35 项聚焦协议/接线/窄 parity 测试与退出审查已
  本地完成；裁决为 `pass-with-boundaries`；`f62f078` / Actions `32022258177` exact-SHA 公共验证
  成功，5F-2 正式关闭，下一检查点为 5F-3。
- 5F-3 已由 `3d9a081` / Actions `32025522606` 完成 exact-SHA 公共闭环；Harness/成功 Trace 可适配，
  但 Context 单位、extended terminal 与 live timing 三项 hard gap 使 5F-4 未进入。
- ADR-0037、最终 exit matrix/review 与本地门禁已完成；本地裁决为
  `partial-adopt-evaluation-assets-only`：产品拒绝 Pi，只冻结保留评测资产与采用门方法。
- `5P-entry-design` 与 5P-1 至 5P-6 已公开完成；
- 5P-4 immutable receipt/store、strict query 与 Application receipt 接缝已由 `932a863` / Actions
  `32002994441` 完成 exact-SHA 公共验证；5P-5 薄 Adapter 与 no-I/O 纵向切片又由 `6d1e5b0` /
  Actions `32005648179` 完成 exact-SHA 公共验证；
- 5P-5 薄 FastAPI Adapter 与 no-I/O 纵向切片已由 `6d1e5b0` / Actions `32005648179` 完成
  exact-SHA 公共验证并正式关闭；
- 5P-6 已完成十项功能 exit matrix、初学者 exit review 和比例/完整门禁；裁决为
  `close-with-deferred-boundaries`，提交 `8c8acc6` / Actions `32010604551` exact-SHA 公共成功；
- 入口审计确认 5P 同时承担 Prompt Program V1 与早期产品切片，不能缩成单纯 FastAPI；
- ADR-0032 选择版本化 Prompt Program/Catalog 和 drift gate，复用既有 component fingerprint；
- ADR-0033 选择薄 FastAPI Adapter + Application Service + 现有 AgentRuntime/Harness；
- 5P 内部固定为 5P-1 产品合同/typed compiler、5P-2 Prompt Program/composition、
  5P-3 domain/application service、5P-4 receipt/query、5P-5 FastAPI、5P-6 exit review；
- 5P 产品切片本身不读取 Key、不调用 Riot/Provider、不进入阶段 6；5F 采用实验仍需单独设计和
  用户明确继续。
- entry design 提交 `49841ec` 已通过 Actions `31985199623` exact-SHA 公共 CI；

### Phase 9 - 6A-1-postgresql-foundation

- Status: complete
- Authorization: RQ-053; completed by `854e52d` / Actions `32043214500`.
- 5F-5 决策提交 `f8dea66` / Actions `32028206103` 已完成 exact-SHA 公共验证；阶段 5 正式关闭。
- 6A-entry-design 已由 `c0b5af0` / Actions `32041343696` exact-SHA 公共完成；6A-1 的 SQL
  基础设施、migration、Compose 与真库 CI 又由 `854e52d` / Actions `32043214500` 公共完成。

## Next Step

`6B-5-memory-candidate-write-gate` 已由实现 `7156cb5`、最小真库测试清理 `dd7c9c8` 与 Actions
`32376405150` 完成 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环。
`6B-6-preferences-profile-review-memory` 的 Task 1—6 已在本地实现；唯一下一动作是 Task 7 的最终
代码复核、完整本地门禁、实现提交/推送与 exact-SHA 三 job。公共全绿前 coverage 保持 planned，
不得进入 6B-7。

## 6A-1 Checklist

- [completed] 记录 RQ-053、清除等待确认状态并恢复治理
- [completed] 先写配置与真实 PostgreSQL migration 红灯测试
- [completed] 实现 settings、Engine/Session、metadata/ORM row 与 initial migration
- [completed] 增加 Compose 和 blocking PostgreSQL CI job
- [completed] 运行聚焦/完整/横向门禁并记录本地无 Docker 限制
- [completed] 提交、推送并由 `854e52d` / Actions `32043214500` 完成 exact-SHA 公共 CI

### Phase 10 - 6A-2-task-contract-repository

- Status: complete
- Authorization: RQ-054; completed by `012b066` / Actions `32046532695`.
- 6A-1 已由真实 PostgreSQL service 验证 migration/constraint/metadata drift；6A-2 task contract、
  fingerprint、service 与 Repository 又由真实 PostgreSQL task job 验证；不实现 claim、Worker 或 API。

## 6A-2 Checklist

- [completed] 记录 RQ-054、恢复治理并审计相邻合同/schema
- [completed] 先写 task model/fingerprint/Fake service 红灯
- [completed] 实现 domain models、ports、fingerprint 与 service
- [completed] 写真实 PostgreSQL Repository/transaction 红灯并实现 create/query
- [completed] 修正 6A-1 可逆 migration 测试职责错位并补回归
- [completed] 运行聚焦、完整、两套 RAG 与全部横向门禁
- [completed] 提交、推送并由 `012b066` / Actions `32046532695` 完成 exact-SHA PostgreSQL CI

### Phase 11 - 6A-3-atomic-claim-polling-worker

- Status: complete
- Authorization: RQ-055.
- 6A-2 已公开验证真实 Repository 事务；6A-3 又由 `55e369e` / Actions `32097561436` 公共验证
  claim、Worker control flow、shutdown loop 与真实 PostgreSQL concurrency；不接真实 Application/
  Artifact 或 API。

## 6A-3 Checklist

- [completed] 记录 RQ-055、清除等待确认状态并完成初学者入口教学
- [completed] 审计相邻合同/schema，先写 polling/Worker Fake 与真实 PostgreSQL claim/CAS 红灯
- [completed] 实现 polling policy、ReviewWorker、Repository claim/terminal CAS 与 fail-closed Worker CLI
- [completed] 运行聚焦、完整、两套 RAG 与全部横向门禁
- [completed] 提交、推送并由 `55e369e` / Actions `32097561436` 完成 exact-SHA PostgreSQL CI

### Phase 12 - 6A-4-application-artifact-integration

- Status: complete
- Authorization: RQ-056.
- 6A-3 已正式关闭；6A-4 已实现 run_id/Application/Artifact integration、receipt-proven
  reconciliation 与人工 recovery，不进入 6A-5。

## 6A-4 Checklist

- [completed] 记录 RQ-056、清除等待确认状态并完成初学者入口教学
- [completed] 审计相邻 Application/Runtime/receipt/task/Worker 合同并先写红灯
- [completed] 实现 trusted run_id 贯穿、真实 Recent Review Executor 与 terminal evidence 校验
- [completed] 实现 receipt-proven reconciliation、recovery-required 投影与人工 recovery CAS
- [completed] 运行聚焦、完整、两套 RAG 与全部横向门禁
- [completed] 提交、推送并由 `41ac9c1` / Actions `32102522662` 完成 exact-SHA PostgreSQL CI，随后只交接 6A-5 准备状态

### Phase 13 - 6A-5-async-fastapi-composition

- Status: complete
- Authorization: RQ-057.
- 6A-4 的真实 PostgreSQL 公共门已完成；本批实现异步 task HTTP、ActorContext、API composition/
  lifespan 与 live/ready，但不实现 Session、Memory、SSE、正式 Auth、前端、lease/retry 或公网部署。

## 6A-5 Checklist

- [completed] 记录 RQ-057、清除等待确认状态并完成初学者入口教学
- [completed] 先写 HTTP、ActorContext、readiness 与 lifespan 红灯测试
- [completed] 实现 task API、owner-scoped run/report 与 production-like API composition
- [completed] 增加真实 PostgreSQL API 测试并纳入阻塞 CI job
- [completed] 运行聚焦、完整、两套 RAG 与全部横向门禁
- [completed] 提交 `2492951`、推送并由 Actions `32106378542` 完成 exact-SHA `pytest` 与 PostgreSQL CI，只交接 6A-6

### Phase 14 - 6A-6-security-lifecycle-nfr implementation

- Status: complete
- Authorization: RQ-058; user explicitly said “继续下一步”.
- 6A-5 的异步 task API 与 API process composition 已公开完成；本批只实现其上冻结的 CORS/log/Secret、
  retention/delete、backpressure、structured observability 与 performance baseline。
- 先写红灯测试，再实现最小功能；本机无 PostgreSQL 时明确 skip，真实并发/删除/性能证据必须由阻塞 CI 提供。

## 6A-6 Checklist

- [completed] 记录 RQ-058，更新 canonical、路线/能力矩阵和决策记录，并通过治理检查
- [completed] 讲解 CORS、脱敏、容量/背压、retention/delete、metrics 与 benchmark 的问题、原理、数据流和边界
- [completed] 先写 CORS、日志脱敏、retention/delete、backpressure、observability、PostgreSQL performance 红灯测试
- [completed] 实现默认关闭 CORS 与 production wildcard+credentials fail-closed
- [completed] 实现 allowlisted structured logs/metrics，禁止 Riot ID、Prompt、report、Provider body、异常栈和 Secret
- [completed] 实现 7/90/30 天 retention、terminal hidden-before-cleanup、幂等删除和安全补偿状态；active delete 返回 conflict
- [completed] 在真实 PostgreSQL 下验证 owner/global capacity race、删除生命周期和 warm-DB/claim 性能样本
- [completed] 运行聚焦、完整、两套 RAG、compileall、Harness/security/diff/governance 门禁
- [completed] 提交 `31d5e60`、推送并由 Actions `32138025724` 完成 exact-SHA `pytest` 与 PostgreSQL CI，只交接 6A-7

### Phase 15 - 6A-7-packaging-exit-review implementation

- Status: complete
- Authorization: RQ-059; user explicitly resumed 6A-7.
- 6A-7 只负责可重建 API+Worker+PostgreSQL packaging、Linux smoke、6A exit matrix 与公开证据；
  必须闭环此前 fail-closed 的真实 Worker executable composition，但 CI/smoke 不读取真实 Key 或调用
  Riot/Provider；Session/Memory、SSE、正式 Auth、前端或公网部署仍不在本轮。

## 6A-7 Checklist

- [completed] 记录 RQ-059、清除等待确认状态并恢复治理
- [completed] 审计 API/Worker/PostgreSQL 现有 composition 与 packaging 缺口
- [completed] 先写 packaging contract、Linux no-I/O smoke 与 exit matrix 红灯
- [completed] 实现最小 Dockerfile/Compose/Worker composition/config/startup 文档
- [completed] 运行聚焦、完整、RAG、compileall、Harness/security/YAML/diff/governance 本地门；本机无 Docker/PostgreSQL 的真实运行证据由阻塞 CI 补齐
- [completed] 完成 exit matrix/review、提交推送；`adf53e5` / Actions `32146760003` 的 pytest、PostgreSQL、packaging-smoke 三 job 全绿并关闭 6A

### Phase 16 - stage-6-session-memory-entry-design

- Status: complete
- Authorization: RQ-060 启动设计；RQ-064 取代设计后的再次授权暂停门，允许按冻结计划逐批连续实施。
- 6A 已公开完成；本 checkpoint 只审计 Session/Memory 需求、现有 owner/task/run/API、参考实现可迁移边界、
  数据模型与写入/隐私/更正/导出/过期/删除规则，并分节取得设计确认，不表示已经开始产品实现。
- 正式 Auth、SSE、前端、阶段 7 MCP 或阶段 8 Multi-Agent 不能借此提前进入。

## Session/Memory Entry Design Checklist

- [completed] 恢复 canonical/活动计划/路线/执行日志，确认工作树干净、治理通过，并补记
  `d1cc2ed` / Actions `32147545753` 三 job 公共成功
- [completed] 记录 RQ-060，解除等待授权状态；把 Session/Memory 产品实现、新依赖及后续阶段保持在范围外
- [completed] 面向初学者讲清 task、Session、工作记忆、长期 Memory、原始比赛事实与 RAG 的职责和数据流；用户已确认第一节
- [completed] 审计现有 owner/task/run/API 与 EchoMind、AGI-Saber 的可迁移思想、缺陷和不采用项
- [completed] 比较 PostgreSQL 单一真源、EchoMind 式拆分和首日混合三种方案；用户确认 PostgreSQL 单一真源，Redis/向量索引仅由后续 Bad Case 触发
- [completed] 冻结 owner/player-subject 外服关系：MVP 同时支持 `claimed_self` 与受限
  `public_observed`，关系角色与验证状态分维度建模；future-only verified 必须经过正式 Auth + RSO +
  PUUID match，当前无创建路径
- [completed] 冻结 conversation ownership、单一 player-subject 绑定、Riot ID 改名/PUUID mismatch 与
  无中途切换规则；不同 subject 必须新建 conversation，消息/Context/task/run/Candidate 均继承 trusted
  owner/conversation/subject
- [completed] 冻结在当前 Worker 才解析 PUUID 的前提下，player-subject/relationship 的异步 bootstrap、
  idempotency、失败与 conversation 创建顺序
- [completed] 冻结 Session、消息、owner-global 偏好、owner-player 画像、复盘情景、训练计划/进度的数据
  模型，以及 provenance/confidence/write gate
- [completed] 冻结隔离、冲突/更正、查看/导出、过期/删除、失败补偿、隐私、安全、NFR 和 Context 装配边界
- [completed] 冻结 Fake/真实 PostgreSQL/API/隔离/安全/Context 测试矩阵和 6B-1 至 6B-9 原子顺序
- [completed] 已创建 ADR-0039/design/implementation plan并完成一致性修正及全部本地门禁；设计提交
  `bc11afe` / Actions `32222531783` 的 exact-SHA 三 job 全绿，entry design 正式关闭

### Phase 17 - 6B-1-player-identity-link-foundation

- Status: complete
- Authorization: RQ-064 启动本批，RQ-065 进一步收紧为本轮只闭环 6B-1；全绿后停止，不自动进入 6B-2。
- Outcome: strict Player/Relationship/Link Task contracts、四张 PostgreSQL 表、可逆 Alembic 0002、
  transaction-safe Repository/Service 与 Fake/真实 PostgreSQL 证据。
- Boundary: 不实现 Riot Account resolver、PlayerLinkWorker/HTTP API、Conversation/Memory、Auth/RSO，
  不读取 Key 或调用 Riot/Provider。

## 6B-1 Checklist

- [completed] 面向初学者完成问题/原理/范围/数据流/测试/限制教学，并先写 pure domain 红灯
- [completed] 实现 strict player/link models、normalization、public View 与 allowlisted error contract
- [completed] 以红灯冻结 fingerprint、Fake service、idempotency/capacity 与独立 repository port
- [completed] 先写真实 PostgreSQL migration/metadata 红灯，再实现 ORM 与可逆 0002
- [completed] 先写真库 create/query/claim/resolve/CAS/concurrency/rollback 红灯，再实现 Repository
- [completed] 运行聚焦/相邻/完整/RAG/compile/Harness/security/governance/diff 门并同步持久状态
- [completed] 独立提交/推送 6B-1；最终 `ed8fa58` / Actions `32229024069` 的 pytest/PostgreSQL/package 三 job 全绿，已按 RQ-065 停止

### Phase 18 - 6B-2-async-player-link-worker-api

- Status: complete
- Authorization: RQ-066；用户在 6B-1 公共闭环后的新一轮明确“继续开工”，只授权本批。
- Prepared outcome: narrow Account resolver、专用 PlayerLinkWorker、owner-scoped POST/GET Link API 与
  Fake Resolver Linux no-I/O smoke；Conversation/Memory 仍留 6B-3。

- [completed] Task 1：RiotAccountResolver strict response/error contract 与 Fake-client TDD
- [completed] Task 2：PlayerLinkWorker claim→resolve/fail、polling、graceful stop 与 body-free observability
- [completed] Task 3：owner-scoped POST/GET Link API、OpenAPI、Fake 与真实 PostgreSQL 集成
- [completed] Task 4：API/Worker composition、CLI、Compose 与 Linux Fake Resolver no-I/O smoke
- [completed] Task 5：聚焦/相邻/完整/横向门禁、状态同步、独立提交推送与 exact-SHA 三 job；
  `0c13a58` / Actions `32301852042` 的 pytest/PostgreSQL/package 三 job 全绿
- [completed] 6B-2 公共闭环后只准备 6B-3 并停止，不实现 Conversation/Memory

### Phase 19 - 6B-3-conversation-message-foundation

- Status: complete
- Authorization: RQ-067 文档前置门已由 `63435d9` / Actions `32308631289` 公共闭环；本批正式进入 6B-3，按教学→设计复核→红灯→最小实现推进。
- Prepared outcome: immutable owner/relationship/subject Conversation、ordered user/assistant Message
  persistence/API 与真实 PostgreSQL constraint/concurrency 证据；不接 Agent、Review Task 或 Memory。
- [completed] 审计阶段 0 至 6B-2 的持久教学/工程说明覆盖，确认最早真实缺口在阶段 0，并记录阶段 1/4/5A/5B/6B-1/6B-2 的不同补强级别
- [completed] 采用覆盖矩阵驱动的混合补齐：复用充分材料，只对真实缺口新增 learner walkthrough / implementation review
- [completed] 补实际代码地图、数据/控制流、事务/失败/安全边界、证据矩阵、运行示例与面试表述
- [completed] 更新 README、学习索引、AGENTS 教学成品规则、coverage schema 与治理红灯；同步 canonical/RQ/路线/能力矩阵/决策历史
- [completed] 运行文档/治理/比例回归/安全/diff 门；本地完整 `1224 passed, 42 skipped, 1 warning, 110 subtests passed`，两套 RAG、Harness、compileall、secret/tracked-data 与 SDK boundary 均通过
- [completed] 独立提交/推送文档批 `63435d9`，并完成 exact-SHA Actions `32308631289` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job
- [completed] 进入 6B-3 的只读接缝审计：确认 Base/ORM metadata、复合 parent identity、API proxy/lifespan、锁顺序和 PostgreSQL CI 入口
- [completed] 创建 ADR-0040 与 6B-3 专用设计稿，冻结 active relationship 行锁、Conversation 幂等、user-only 公共 Message、1-based 行锁序号、archived/hidden 和 trigger 合同
- [completed] 加强 coverage 治理：固定 canonical group ID 顺序、校验 YAML 镜像，并增加“重排同时重编号/镜像漂移”红灯测试；治理聚焦现为 `12 passed`
- [completed] 设计批本地门禁：完整 `1226 passed, 42 skipped, 1 warning, 110 subtests passed`；RAG 两套、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff 均通过
- [completed] 设计批独立提交 `b6a7112`、推送并由 Actions `32313707301` 的 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共验证
- [completed] pure model/Service/API 红灯 → migration/Repository/PostgreSQL 并发红灯 → 最小实现；当前不接 Agent、Review Task 或 Memory
- [completed] 6B-3 最小实现、实现后 walkthrough/coverage 更新、本地门禁；本地完整 `1295 passed, 67 skipped, 1 warning, 110 subtests passed`，横向 RAG/Harness/compile/security/governance/diff 门通过
- [completed] 实现提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081`、推送并完成 Actions `32329686381` 的 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 公共 CI；PostgreSQL fixture 父行 flush 修复保留失败→修复证据链
- [completed] 独立状态/coverage 收尾：6B-3 置为 complete，覆盖账本与学习索引升级为完整/公共闭环
- [completed] 交接到 `6B-4-conversation-bound-recent-review-identity`；后续 RQ-068 已在独立新轮授权

### Phase 20 - 6B-4-conversation-bound-recent-review-identity handoff

- Status: complete
- Authorization: RQ-068; implement only 6B-4 and stop before 6B-5.
- [completed] 严格恢复 AGENTS/canonical/活动计划/RQ/路线/能力/coverage，治理预检通过，起始工作树干净且 `HEAD == origin/main == 4fb66a8`。
- [completed] 面向初学者讲清问题、服务器派生身份原则、范围、数据/控制流、测试策略、限制与面试边界；比较三种方案并选择 nullable v2 columns + atomic server-derived binding。
- [completed] 同步 RQ-068、canonical/路线/能力/决策历史、6B-4 planned coverage 与治理固定顺序；修正两处已被 6B-3 公共证据取代的陈旧表述。
- [completed] 完成 ADR-0041、6B-4 专用设计与逐任务实施计划；精确审计 Task/Conversation/Summary/API/Worker 接缝。
- [completed] pure domain/API 红灯与最小实现：schema 2.0、body 仅 count/queue/focus、客户端不能伪造 identity/PUUID、legacy 1.0 兼容。
- [completed] PostgreSQL 0004/Repository 红灯与最小实现：单事务 active tuple 锁定、v2 mapping/private target、alias rename、late claim、capacity/rollback 与双向 lifecycle 锁顺序合同已建立；本机真库项因无 PostgreSQL 明确 skip，待阻塞 CI 补证。
- [completed] `build_by_puuid()`、`review_by_puuid()` 与 v2 Executor 红灯/最小实现；51 项聚焦证明 v2 不调用 Account-V1、alias 只影响显示、篡改在 Application 前拒绝，legacy 1.0 保持兼容。
- [completed] composed API、existing Worker、package no-I/O 纵向与 blocking PostgreSQL CI：proxy 已转发 v2 创建；同一 Worker 处理两个 schema；smoke 覆盖 Link→Conversation→v2 Task→safe terminal；两个新真库文件已加入 job，本地 114 passed/11 PostgreSQL skips。
- [completed] walkthrough/八维 evidence、路线/canonical 与全部本地门禁完成；coverage 在公共门前保持 planned。
- [completed] 实现提交 `d63f9085f66e49557b4674d0698495dcb7335c82` 已推送，Actions `32347834279` 的 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；6B-4 与 coverage 正式关闭。
- [deferred] 不实现 6B-5、assistant Message、Memory Candidate/长期 Memory、正式 Auth/RSO、SSE、前端、LangGraph、Multi-Agent 或新 SDK；测试/CI 外部 Riot/Provider calls 为 0。

### Phase 21 - 6B-5-memory-candidate-write-gate handoff

- Status: complete
- Authorization: RQ-069; implement only 6B-5 and stop before 6B-6.
- Prepared outcome: Candidate source/target/provenance/gate contracts 与 exactly-once acceptance 接缝；具体长期 Memory 表不在本批。
- [completed] 按教学合同复核问题、原理、范围、数据/控制流、测试和边界；比较 receipt、万能表与事务内 typed materializer，并冻结 ADR-0042、专用 design/implementation plan。
- [completed] Candidate pure contract 与 deterministic gate TDD；本地聚焦 17 passed。
- [completed] 0005 migration/ORM 与 owner-scoped Repository TDD；本地聚焦真库套件明确 skip，offline SQL/metadata 通过。
- [completed] reject/expire/user acceptance、事务回滚和 exactly-once materializer TDD；测试 target 的 PostgreSQL 证据待 blocking CI。
- [completed] 薄 API、composition、package no-I/O 纵向；本地 API/package 聚焦通过，生产 empty registry 对 accept fail closed。
- [completed] 八维 walkthrough、本地完整 `1358 passed, 88 skipped, 1 warning, 110 subtests passed` 与横向门禁均已闭环。
- [completed] 实现 `7156cb5` 的首个公共 run 保留 teardown 失败证据；最小测试清理 `dd7c9c8` / Actions `32376405150` 的 pytest/PostgreSQL/package 三 job 全绿，6B-5 与 coverage 正式关闭。
- [deferred] 不顺带实现 6B-6 长期 Memory、6B-8 assistant terminal 或其他后续能力。

### Phase 22 - 6B-6-preferences-profile-review-memory handoff

- Status: in_progress
- Authorization: RQ-070; user said “那继续”, which authorizes only this checkpoint.
- Prepared outcome: typed owner Preference、Player Profile 与 Review Memory，注册真实 materializer，并保持 self/observed 权限与 supersede/conflict 边界。
- [completed] 按教学合同重新审计 6B-5 接缝；已冻结 ADR-0043、专用设计和原子实施计划。
- [completed] 设计提交 `e44d48f` / Actions `32381553145` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job exact-SHA 全绿；设计批正式关闭。
- [completed] Task 1：typed payload/version envelope、scope/role/key policy pure contract；首轮 3 个失败经显式 Enum 规范化/未知 key 原因码修复后，聚焦 11 passed、相邻 30 passed。
- [completed] Task 2：三个 materializer pure contract 与 Fake Session/writer 边界证据；聚焦 19 passed。
- [completed] Task 3：三张 typed target ORM、0006 migration、FK/CHECK/partial unique/immutable/source/supersedes trigger；本机真库测试明确 skip。
- [completed] Task 4：PostgreSQL writer、advisory lock、supersede/version conflict/exactly-once；真库首写/并发/rollback 合同已加入阻塞 CI。
- [completed] Task 5：生产 composition 注册三个真实 materializer，registry 构造 no-I/O 且不可变。
- [completed] Task 6：owner-scoped active/history query API；更正继续走 Candidate，不提供 target PATCH。
- [in_progress] Task 7：八维 walkthrough 已建立、coverage 保持 planned；执行完整门禁、提交/推送/exact-SHA 三 job，公共全绿后关闭 coverage 并只交接 6B-7。
- [deferred] 不提前进入 Training Plan/Progress、assistant terminal、Memory-aware Context、Auth/RSO、SSE、前端或新框架。

## 6A Entry Design Checklist

- [completed] 审计 5P FastAPI/Application/receipt/query 与文件 crash/multi-worker gap
- [completed] 复核 EchoMind API/lifespan/Redis/Chroma Memory 源码，区分可吸收思想与不可照搬实现
- [completed] 确认 PostgreSQL 是唯一生产语义基线；SQLAlchemy 2 + Alembic；关键语义由真实 PostgreSQL Docker/CI 验证
- [completed] 比较三种任务执行方案并选择同仓库同部署的独立 PostgreSQL polling worker
- [completed] 确认模块化单体、API/Worker 分工、短事务和 SQL 控制面/Artifact 数据面架构
- [completed] 确认 task schema、task_id/run_id 双身份、四态状态机和不可逆终态规则
- [completed] 确认保守 hard-crash reconciliation：有终态证据自动补齐，无证据需受限人工确认，不自动重跑
- [completed] 确认请求/数据库/Worker/Runtime/Artifact 失败语义、HTTP 投影和执行/发布状态分离
- [completed] 冻结作品集 NFR、安全、数据生命周期与 Fake/真实 PostgreSQL/API/Worker/纵向/安全性能测试矩阵
- [completed] 冻结 6A-1 PostgreSQL Foundation 至 6A-7 Packaging/Exit 的原子实施顺序
- [completed] 创建 ADR-0038、正式 design 和 implementation plan
- [completed] 本地门禁：929 passed/110 subtests、两套 RAG、compileall、Harness dry-run、governance、安全与 diff
- [completed] 提交、推送和 exact-SHA 公共 CI：`c0b5af0` / Actions `32041343696`
- [completed] 关闭 6A-entry-design，只交接 6A-1 准备状态，未自动实施

## 5P-6 Exit Review Checklist

- [completed] 冻结功能、NFR、安全、资源和明确排除项的退出标准
- [completed] 建立 5P-1 至 5P-5 源码/测试/public-CI exit matrix
- [completed] 运行聚焦、相邻、完整回归与全部本地门禁
- [completed] 形成退出结论、限制、教学/面试表述并同步本地持久状态
- [completed] 提交、推送和 exact-SHA CI；只交接到 5F，不自动实现

## 5P-5 Implementation Checklist

- [completed] 红灯冻结四个 HTTP 端点、OpenAPI、错误映射和 no-I/O 边界
- [completed] 安装并声明 FastAPI/dev httpx 依赖
- [completed] 实现显式依赖注入的薄 Adapter 与 allowlisted DTO
- [completed] 完成 Fake/fixture 和真实 Runtime/Harness/RAG 本地纵向测试
- [completed] 完成本地状态同步、提交/推送和 exact-SHA CI

## 5F-entry-design Checklist（Pi-only）

- [completed] 冻结 Pi-only 候选范围、Claude SDK 书面排除理由和技术采用 ADR
- [completed] 设计同一 `recent-form-review` 切片的 no-I/O Pi protocol spike
- [completed] 冻结合同、安全、Trace/Harness、跨语言成本和 adopt/partial-adopt/reject 指标
- [completed] 提交、推送并验证 entry design 的 exact-SHA 公共 CI
- [completed] 公共闭环后交接 `5F-1-pi-source-license-contract-audit`，不自动实施

## 5F-1 Source / License / Contract Audit Checklist

- [completed] 复核仓库迁移、官方 release/tag/npm `gitHead`、包版本、integrity 与 Node requirement
- [completed] 审计 MIT license 和再分发义务
- [completed] 映射 Agent/Provider/Tool/event/state/abort/timeout/Usage 与 RiftCoach 合同
- [completed] 记录 parallel/batch preflight、Usage completeness、Trace body 与权限/依赖差异
- [completed] 形成有条件进入 5F-2 的隔离 sidecar 边界和十类 scripted cases
- [completed] 运行完整 pytest、两套 RAG、compileall、governance、安全边界、dry-run 与 diff check
- [completed] 提交/推送并完成 exact-SHA 公共验证：`5901b09` / Actions `32016852979`
- [completed] 公共闭环后交接 5F-2，等待下一次明确继续

## 5F-2 Offline Protocol Adapter Spike Checklist

- [completed] RQ-049 恢复、教学说明、方案比较、ADR-0035 与实施计划
- [completed] Batch A：严格 Python protocol/frame/Usage 红灯与最小实现；13 focused / 50 adjacent
- [completed] Batch B：exact npm package/lockfile、`npm ci --ignore-scripts` 与供应链/成本记录
- [completed] Batch C：Node Pi sidecar + Python controller + 真实本地 `knowledge.search`
- [completed] Batch D：scripted 安全/预算/失败案例、Usage 四态与 body-free event
- [completed] Batch E：窄同切片对照、本地完整门禁和退出裁决、提交/公共 CI 已完成；只交接 5F-3 准备状态

## 5F-3 Contract / Security / Harness Evaluation Checklist

- [completed] 复用 5F-2 同切片，对比完整 Tool/Context/deadline/structured output/error/terminal 合同
- [completed] 验证 ReviewHarness 仍是唯一发布权，并核对 Trace/Usage/Artifact parity
- [completed] 量化 sidecar/IPC/日志/调试/部署维护成本与安全差异
- [completed] 完成本地门禁、提交与 exact-SHA 公共 CI；硬门失败，5F-4 未进入

## 5F-5 Adoption Decision / Exit Review Checklist

- [completed] 冻结产品职责、合同、安全、NFR、维护、教学和复现价值的最终比较矩阵
- [completed] 用 ADR-0037 分别裁决产品 Runtime、隔离可执行资产与可吸收设计思想
- [completed] 形成 5F 总退出审查并同步 canonical、路线、能力矩阵和项目决策
- [completed] 本地门禁、提交、推送和 exact-SHA 公共 CI：`f8dea66` / Actions `32028206103`
- [completed] 关闭 5F，只交接 `6A-entry-design`，未自动实施阶段 6

## Decisions Made

| Decision | Rationale |
|---|---|
| 保留阶段 0-8 和原始 5C-1 至 5C-6 | 防止实现批次反向篡改已经确认的教学与验收顺序 |
| 建立唯一当前状态源 | 多份路线文档不能同时承担动态进度真相源 |
| 不回滚提前实现的 5C-4/5 代码 | 有效实现可以保留，但必须回到原检查点审查和验收 |
| 5C-6 作为证据驱动决策门 | 模型兜底不是默认功能，只有真实 Bad Case 才可能触发 |
| 完整 GPT 导出只用于定向查漏 | 全量历史混有早期和已撤回方案，专项导出与后续明确确认更适合判定当前路线 |
| 首批三 Skill 时序标为待裁决 | 历史承诺没有被撤销，但治理修复也不能直接替用户决定继续维持还是调整 |
| 5C-4 只补合同不变量和边界测试 | 保留已正确的匹配算法，同时让排除信号在算法与决策合同两层都成为硬否决 |
| 两个用户任务进入 Router，事实审查保留为 EvaluatorStep | Router 选择用户意图；Harness 的强制质量端口不是第三种用户任务 |
| 5F 最终只保留 Pi evaluation assets，产品拒绝 Pi Runtime | 三项 hard parity gap 与跨语言成本使产品净收益为负；冻结可执行证据仍有复现、教学和作品集价值 |
| 不实现 Skill Invocation Contract | 当前没有真实内部 Skill；为一个重复包装扩展 Manifest 会增加无消费者的抽象 |
| 用 ADR-0009 取代 ADR-0008 原方案 | 保留决策历史，同时确保最终路线由源码证据而不是“三个 Skill”数字驱动 |
| 单局 Skill 接收完整 Summary、确定性报告与唯一 target_match_id | 复用版本化事实契约，同时避免给 Agent Riot API 权限；5D 再抽取最小上下文 |
| 近期与单局范围同时出现时返回 ambiguous | 字面 Router 无法可靠判断语序语义；澄清优于静默丢失其中一个任务 |
| 旧单 Skill 评测先归档，再重建双 Skill 数据集 | 旧 15 案例参与过规则校准且候选集合已变化；保留历史证据，不能冒充当前泛化成绩 |
| development 与 held_out 由数据角色和候选版本快照强制区分 | 防止把旧题库或新 Skill 版本静默放入错误评测，降低人工调规则造成的泄漏 |
| development v2 以 23/23 精确匹配接受并冻结当前规则 | 没有误路由需要修改；继续调词只会增加过拟合风险，下一步应按既定门禁单次运行 holdout |
| 5C-5 以 holdout 11/12 和原样 Bad Case 收尾 | Evaluation 的目标是获得可信证据而不是强制满分；唯一失败已分类且未用于调规则，足以进入 5C-6 方案决策 |
| 5C V1 暂缓 LLM Router fallback | 只有一个小型合成域语义失败；立即引入模型必须复核 selected，且当前 GLM Adapter 没有端到端结构化输出，收益不足以覆盖延迟、成本和故障复杂度 |
| 类型化入口和澄清优先于模型语义复核 | 显式任务上下文比猜测自由文本更可靠；未来只有新鲜数据出现多个独立失败族并通过新 Eval/ADR 时才重开模型方案 |
| 5C 退出复核通过，5D 成为唯一下一步 | 六个检查点均有实现、评测或 ADR 证据；退出审计修复了命中证据身份与冻结点标注，已知执行缺口明确归入 5D |
| 5D 先设计和拆分再实施 | Context、结构化输出、权限预算和 Harness 接线都需要独立教学验收，不能再次把一个大批次等同于整个子阶段完成 |
| AgentLoop 作为 Harness 的 evidence-aware draft preparation | 保留 Agent 的动态白名单工具选择，同时让现有 Harness 继续掌握唯一评测、修订和发布权 |
| 用 `DraftPreparationStep` 作为唯一新接缝 | 旧 Retriever/Generator 可通过顺序 Adapter 兼容，新 Agent 路径返回同一 CoachDraft + KnowledgeEvidence，不制造第二套质量平台 |
| Provider 厂商选择放在 5D-6b 准入门 | 先稳定结构化输出和领域评测合同，再实测 GLM 并最多比较一个候选；不按视频热度提前锁定 DeepSeek/Qwen/Kimi |
| 5D-1 用 selected name + version 锁定路由身份 | 只保留名称无法发现路由后 Catalog Skill 版本漂移；权限仍从当前同名同版本 Manifest 重新取得 |
| run ID 使用一个跨 Harness/Skill 的可移植规范 | Manifest、Store 和执行入口若各自校验会产生安全与兼容漂移；ASCII 单组件同时适配 Windows 和 Linux |
| 输入绑定复用 Harness 真实 Artifact 字节编码 | 对同一语义采用不同 JSON 格式会得到不同哈希；共享编码才能让 5D-5 的真实 Artifact 与 5D-1 内容承诺逐字节对上 |
| 5D-1 只做内容承诺，不创建 Harness run | 真实落盘、状态迁移和 terminal output 属于 5D-5；当前先建立可独立测试的执行前 fail-closed 边界 |
| 5D-2 使用 trust-typed section 再渲染现有 ChatMessage | 先保留来源、指令权限、必需性和优先级，才能机器检查不可信边界；不另造 Provider 消息协议 |
| 近期与单局使用不同 allowlist 投影 | Summary 允许扩展字段；整份序列化会静默扩大模型可见数据，并让单局上下文混入近期聚合与其他对局 |
| 必需段超预算失败，可选段只整段保留或省略 | Policy、Skill 指令和核心事实不能静默截断；完整 section 选择避免半截 JSON、表格行和 citation |
| 默认 ContextSizer 是可注入的确定性 preflight | 真实 Provider 尚未在 5D-6b 准入；当前估算保证可重复选择，不冒充厂商 tokenizer 或真实 Usage |
| 5D-3 采用薄 `AgentRunCompiler` 并扩展现有请求/Loop | 现有 `AgentRunRequest` 已拥有大部分权限预算字段；包装或平行请求会复制控制面 |
| Context ceiling 成为 `AgentRunRequest` 一等字段 | 只写 metadata 无法阻止第二轮 Provider 调用；Loop 必须在累计消息增长后仍能读取硬上限 |
| 完整消息估算包含 ToolCall envelope | 大参数存在于 `tool_calls.arguments` 而非 content；只估 content 会留下可绕过的预算缺口 |
| Manifest `timeout_s` 收紧为 cooperative total deadline | 每次外部调用只获得 remaining budget；同步函数不可硬抢占的限制保留，不伪装成强制取消 |
| 5D-4 新旧路径共用一个 KnowledgeEvidence converter | citation 编号、来源去重与冲突拒绝必须只有一套语义，避免旧 Harness 和 Agent 路径漂移 |
| Agent 证据只来自实际 ToolExecutionRecord | 模型 Markdown 中声明的来源不可作为 provenance；无工具回答合法但 Evidence 必须为空 |
| 5D-4 不重写模型文本补 K1 引用 | 运行后 citation ID 与模型生成时观察到的工具 payload 尚未统一；引用覆盖和支持度留给 5D-5/5D-7 验证 |
| ReviewHarness 只依赖一个 DraftPreparationStep | 新旧路径都进入同一评测、修订与发布状态机，避免可选构造器组合或 `run_prepared()` 形成第二套控制流 |
| AgentRunResult 保留在 SkillReviewExecutor 外层 | Harness 只消费领域中立 draft/evidence，不反向依赖 Agent 模块；Trace 持久化仍留给 5E |
| typed output 只从 terminal Manifest 与已验证 Artifact 构造 | 模型返回和内存对象不是发布真相源；最终报告、最终 attempt 分数、证据来源与输入 commitment 均可独立审计 |
| 5D-5 不从 `app.skills` 根包重导出 executor | 显式子模块导入保持 Agent compiler → Skill execution 的依赖方向，避免 package initializer 循环引用 |
| 5D-6a 采用请求声明 + capability + Adapter 严格验证 | 只替换 parser 不能让 Provider 知道结构化要求；另造 Harness 调用路径又会复制控制面 |
| Coach 报告继续使用 Markdown | 结构化输出首先保护机器消费的 Evaluation 控制数据，不为 JSON 形式牺牲报告可读性 |
| Schema repair 最多一次且必须重新严格验证 | 修复是受限的第二次模型调用，不允许正则抽取、默认补字段或无限自愈 |
| 5D-6a 首先接入 Evaluation 控制数据 | 评测 score/verdict/issues 会影响发布；Coach Markdown 继续使用现有质量门禁而非被强制 JSON 化 |
| 5D-6a 不改 Zhipu SDK 映射 | 合同和本地验证可先稳定；真实厂商能力、响应格式和成本必须由 5D-6b 实测决定 |
| 5D-6b 使用请求级工具别名表 | 智谱函数名不允许点号，而 RiftCoach 内部使用 `knowledge.search`；Adapter 编解码隔离厂商约束，不污染 Manifest 与 ToolRuntime |
| GLM 作为首个生产 Adapter，不是最终厂商锁定 | 先用一套真实实现证明 Provider-neutral 边界；DeepSeek/Qwen 等只在同任务同评测决策门打开后比较，不能把适配正确性与模型优劣混成一个变量 |
| Adapter Protocol Slice 复用现有 AgentLoop 并在 Provider 边界计数 | 避免 raw 微探针绕过生产 Adapter，也避免另写两轮循环；结构化直调与 Agent 两轮共享精确 3-call 预算，第 4 次在出网前拒绝 |
| Recent-form Domain Slice 复读历史证据并共享剩余预算 | 已用 3-call 协议结果必须严格复读并哈希；Agent 与 Harness 共用剩余 4-call 的 pre-I/O 预算，不能把累计 7 次重新解释为额外 7 次 |
| 领域准入与 Prompt 质量分开 | 本切片只证明真实领域控制流可由 Provider 完成；多案例工具选择、事实、引用、注入、质量、延迟与成本属于 5D-7，不在单样例上临场调 Prompt |
| 5D-6b 按部分采用收尾 | 真实准入门的合法输出可以是拒绝；低层协议通过不能覆盖领域失败，领域失败也不能抹除协议证据。保留确定性 fallback，不重跑或调 Prompt 追绿，ADR-0012 将 Bad Case 交给 5D-7 |
| 5D-7 采用分层领域评测 | 最终文本无法证明工具、证据与发布路径；ADR-0013 用 development/held-out 生命周期和 Provider/Agent、Tool、Evidence、Evaluation、Terminal、Resources 分层观测，为后续 Prompt/Provider 提供同一把尺子 |
| 离线分类基线不等于模型质量 | 10 个可控观测用于验收评测器，故意保留 unsafe-publication 和资源超限负例；外部调用为 0，不能宣称 Prompt、真实 Provider 或注入防护已准入 |
| 5D-7 Batch B 采用组件 + 案例双层语义身份 | 人工版本号会漏掉未升版漂移，只哈希最终消息又无法定位来源；实际 Skill、Context、知识工具与 Evaluation 形成组件指纹，demo Artifact/section/message 形成案例指纹 |
| 任何执行型候选必须先取得离线 admission | 当前代码重建值、冻结快照和 Dataset 声明必须精确一致；漂移在 Provider 前失败关闭，公开证据只保存哈希与安全元数据 |
| 5D-7 Batch C 采用 Scripted Provider + 真实本地控制流 | 继续手填 observation 不能证明系统执行，立即调用真实模型又会混入费用、随机性与调参污染；只替换 Provider 响应，复用生产 Skill/Agent/Tool/RAG/Harness |
| unsafe publication 作为开发 Bad Case 原样保留 | Harness 只能依据 EvaluationResult 决策；脚本评测器漏判注入时实际发布，分层评测必须报告而不能修改终态追绿 |
| Batch D 采用版本化安全评测 Profile | 原地修改 1.0.0 会破坏历史身份，单加枚举又缺用户/RAG 来源上下文；保留 1.0.0，以 1.1.0 增加最小安全输入和 blocking policy |
| Canary 只作为实验 oracle | 硬编码已知 canary 只能通过考题；生产策略识别类型化 blocking issue，不维护攻击关键词黑名单 |
| held-out 与真实 Provider 分阶段开门 | D1/D2 冻结后才创建独立 held-out；第二 Provider 需新 ADR，真实首轮使用同一 3 场、每 Provider 领域最多 12 calls、零 SDK retry |
| D1-D2 采用安全评测 1.1 并保留 1.0.0 | 历史结果必须可复现；新版本需要接收用户请求与 bounded KnowledgeEvidence，并由 Harness 对 `prompt_injection` 直接阻断，不交给 Reviser |
| D3 只创建 held-out，不在同一批运行 | 防止数据集创建与规则调节互相污染；首次运行必须在规则冻结后由显式确认触发 |
| D4 先设计 Provider 采用门，再决定是否调用 | 5D-6b 暴露了统一响应/错误归因缺口；第二 Provider 不能在同任务合同、预算与失败分类未冻结前接入 |
| 用 ADR-0018 将唯一候选更正为 DeepSeek V4 Pro | D5 同时验证协议和唯一候选的领域能力；Pro 与 Flash 共用本轮协议面但官方生产 Agent 基准更强，额外绝对费用仍受 16000-token、15-call 和 `$0.10` 小额停止线约束 |
| 暂缓 Qwen3.8 Max 与 DeepSeek V4 Flash | Qwen 的 reasoning/计费入口仍增加首轮变量；Flash 保留为以后出现成本/时延 Bad Case 时的简单任务分层候选，本轮不同时测试两个 DeepSeek 模型 |
| 用 ADR-0019 将模型分层移出 5F | 当前 5D-7 保持 Pro-only；Flash/Pro 对照最早在 5P 后、默认等阶段 6 真实成本/时延证据再重开。5F 只比较 Pi Runtime，避免同时改变编排框架和模型导致无法归因 |
| D5 用独立 DeepSeek Adapter 而非通用 OpenAI-compatible 基类 | 当前只有两个厂商实现，thinking、finish、usage 与错误语义仍不同；先用分别测试守住差异，出现经过测试的稳定重复后再提取 helper |
| D5 离线测试不读取 API Key | Fake SDK 用可编程返回验证请求/响应映射、工具往返和失败分支；真实模型质量、在线可用性、延迟与实际费用必须留给公开 SHA 上的有界 API 门 |
| 预算 ledger 组合在候选 Provider 外层 | D4 价格与调用上限是实验政策，不应污染通用 AgentLoop；I/O 前占用调用、响应后按 usage 结算，同时保持 5E Trace 职责未提前实现 |
| 真实协议门使用正式执行接缝而非临时 SDK 脚本 | D5 的 Adapter、preflight、ledger 和 protocol runner 已分别存在，但没有入口保证它们按“先身份、后 Key、再 I/O、最后脱敏记录”的顺序组合；本批只补接缝，不改变实验或阶段 |
| DeepSeek V4 Pro 最小 Adapter 协议准入 | exact-SHA `076a5e3` 上一次真实运行以 3/3 calls 完成严格 JSON 与一次知识工具往返，资源/停止/脱敏合同均通过；该结论不能覆盖尚未运行的三场领域 held-out |
| DeepSeek V4 Pro 领域 held-out 不准入且不重跑当前考卷 | 首个正常案例暴露 `unsupported_parallel_tool_calls`，系统安全降级且没有发布错误内容；这是 Provider/Adapter 能力 Bad Case，不允许删除不可变结果或在已见考卷上临时放宽合同追绿 |
| 多 ToolCall 批次由 AgentLoop 受控顺序消费 | DeepSeek 官方 `auto` 允许一个或多个工具且没有关闭批次的正式参数；Adapter 应翻译合法响应，AgentLoop 复用整批白名单/重复/预算预检，当前无证据承担真正并发复杂度 |
| GLM-5.3 作为隔离的同厂商迁移候选 | 官方页面要求始终启用 thinking，当前 Zhipu Adapter 固定 disabled thinking，不能只改模型名；G53 继续按 ADR-0023 做独立 profile/协议/领域采用门，但 API 未上线时不阻塞已完成的 5D-7，也不影响 5D-exit-review |
| 新鲜领域采用门复用控制面并重建实验身份 | 重写控制面会复制 Harness/Evaluator/预算，旧题改名又是假新鲜；ADR-0024 保留产品链路，先用 development TDD 冻结兼容合同，之后才创建新 fixture/Dataset/plan/Context，并把历史真实证据与当前 CI 串成不可改写链 |
| V3 资源合同采用四阶段 development Usage replay | 直接调高 V2 会污染考卷，单次端到端运行又不保证进入 repair；ADR-0026 用 baseline/ceiling 两个公开 profile 经真实生产组装形成四类请求，最多 8 次独立 replay 只测 Usage，再按逐阶段最大 input、25% 工程余量和硬 output cap 推导新门 |
| 5E 采用薄 Runtime + 可选观察端口 | 外层包装只能事后回放，事件溯源/DAG 又会复制 Harness 并提前进入 5F/8；ADR-0029 复用现有执行链，让中央 Recorder 统一安全事件、Usage 与 Trace |
| Runtime 状态与 publication 状态分离 | Harness 前失败没有发布状态；Provider 失败后 Harness 仍可能安全降级。拆开两者才能准确表达终态而不篡改唯一发布权 |
| V1 Usage 显式区分 complete/partial/unknown | 真实请求可能已发送却没有规范化 Usage；把默认零当成实际零会让 Token 和费用证据失真 |
| V1 stream 是进程内状态事件流 | 5P 需要实时进度，但当前没有 cancel、durable replay 或 Token chunk Bad Case；这些继续留给 5P/6/8 |
| Task B 用 run-scoped Provider decorator 统一真实调用边界 | Agent 与 Harness 会共享同一 Provider；装饰器在 capability preflight 后记录连续 ordinal，既不修改厂商 Adapter，也不会漏掉后续 retry |
| AgentLoop 只观察整批预检后的业务 Tool 与返回终态 | 避免把内部 `llm.chat` 算成 Skill 工具；started 前失败零副作用，completed 后失败停止后续工作，`observer=None` 保持旧行为 |
| `RuntimeObservationError` 穿透 ToolRuntime retry/breaker/fallback | 观察系统失败不是业务依赖失败；若被普通 ToolRuntime 捕获，会制造重试、错误熔断或 deterministic fallback，污染 Trace 语义 |
| 5P 先建立版本化 Prompt Program V1 | 当前 prompt identity 硬编码而真实行为跨 Skill/Context/Knowledge/Evaluation/Revision；ADR-0032 复用既有 component fingerprint 建立 drift gate，不复制 Prompt 控制流 |
| 5P 产品入口采用薄 FastAPI + Application Service | handler 串脚本会复制编排，暴露 RuntimeRequest 又泄漏内部合同；ADR-0033 让产品输入经 typed compiler 进入唯一 Runtime/Harness |
| typed recent endpoint 不重新运行自由文本 Router | 端点本身已是可信任务信号；用 Catalog 当前 name/version 和 `entrypoint:reviews.recent` evidence 保留执行边界，不伪造关键词用户句子 |
| 5P V1 不实现 status/follow-up | 同步 run view 已覆盖 status；follow-up 需要阶段 6 的 Session/Memory/澄清，旧五端点清单不能压过较晚边界 |
| 文件 receipt 只是 body-free 查询投影 | 它绑定 Runtime result/Trace reference 并支持 report 复读，但不冒充 SQL、事务、durable event log 或崩溃恢复 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 6B-4 Summary schema 审计的首个 `rg` 正则转义不完整 | 1 | 只读搜索报 unclosed group，但随后同一命令的精确行读取已取得 `player.puuid_prefix` 合同；停止重复该正则，按真实 schema 修正测试 |
| 6B-4 alias 查询审计再次把 Windows `*repository.py` glob 直接传给 `rg` | 1 | 只读搜索部分成功后该路径参数报错；改为实际目录 `app/persistence` 加 `-g '*repository.py'`，未改源码 |
| 6B-4 Repository 接缝恢复时猜测单数 `conversation_record.py` / `player_record.py` | 1 | 只读命令中两个路径不存在且未改文件；用 `rg --files app/persistence` 定位实际复数文件，后续按真实路径读取 |
| 6B-4 恢复状态补丁连续两次组合了错误的同文件 operation 或陈旧上下文 | 2 | 两次 `apply_patch` 均原子拒绝且未部分修改；读取真实行后拆成独立精确补丁，不改变产品代码或阶段范围 |
| 6B-4 Task 5 findings 补丁使用了不存在的旧表格行作为上下文 | 1 | `apply_patch` 原子拒绝且未改文件；读取 findings 尾部后改为追加独立小节并记录真实组合结论 |
| 6B-4 设计冻结后的首个组合 plan/findings/progress 补丁使用了不存在的 findings 标题 | 1 | `apply_patch` 原子拒绝且未部分修改；读取三个文件真实尾部后拆分精确补丁，不改变产品设计 |
| 6B-3 恢复审计在 Windows 把 `tests\test_conversation_*` 直接作为 `rg` 路径 | 1 | 该命令只读失败、没有修改文件；改用真实 `tests` 目录加 `-g 'test_conversation_*.py'`，后续不再依赖 Windows shell glob 展开 |
| 6B-3 composition 失败测试首次漏写 readiness 的 `schema_version`/`api_version` | 1 | 生产响应合同未变；修正测试对完整安全响应的期望后通过，不放宽 readiness DTO |
| 6B-3 设计批首次 cached diff 发现 ADR-0040 末尾多一个空白行 | 1 | cached 门阻止提交；只删除 ADR 尾部空白并重新暂存，未改变设计语义 |
| 6B-3 设计门把 TEMP 递归清理与验证组合，随后两次精确 TEMP cleanup 都被终端策略在进程创建前拒绝 | 3 | 四项验证改为无清理的独立安全命令并全部通过；确认产物只在用户 TEMP、不在仓库或 Git，停止重复删除；该错误未修改项目、读取 Key 或产生外部 I/O |
| 三个 6B-1 并行子任务在模型开始前被平台以 `prompt_cache_retention is not supported on this model` 拒绝；一次指定 `gpt-5.3-codex` 又被当前 ChatGPT 账户判定不支持 | 4 | 先检查共享工作树确认已存在的 domain/schema 产物未丢失；停止重复派发，主线程接管 Repository、审查与验证。该错误没有运行项目命令、调用 Key/Riot/Provider 或产生测试结论 |
| 6B-1 首次 Alembic offline SQL 编译发现 alias unique 与 relationship composite FK 名称超过 PostgreSQL 63 字符 identifier 上限 | 1 | 同步缩短 ORM、migration、Repository `ON CONFLICT` 与测试中的两个名称；全 metadata identifier 扫描通过，offline `upgrade head --sql` 生成 11930 bytes SQL |
| 6B-1 首个公共 run `32227457202` 的 PostgreSQL migration 与 packaging API stack 同时在 migration 阶段失败 | 1 | 审计发现 revision `0002_player_identity_and_link_tasks` 长 35，超过 Alembic 默认 `version_num VARCHAR(32)`；先加无 DB 红灯得到 `35 <= 32` 失败，再缩短为 `0002_player_identity_link`。不修改 Repository 合同 |
| 6B-1 第二个公共 run `32227937252` 中 pytest/packaging 成功，但 PostgreSQL 67 项仅 schema 名称断言 1 项失败 | 1 | 通过已登录 GitHub 只读日志确认 migration CHECK 名被 naming convention 二次加前缀并截断；先加 offline SQL 红灯，再对 0002 的全部 CHECK 使用 `op.f(...)`，保留稳定完整名称而不放宽断言 |
| 6B-1 首次 push 经 OpenSSL+SOCKS 7897 返回 TLS unexpected EOF，read-only `ls-remote` 同路径也失败 | 3 | curl 证明 mixed port 存活后改用单命令 Schannel+HTTP proxy+HTTP/1.1；`ls-remote` 成功后 push `656117a` 成功。未修改全局 Git/系统代理 |
| 6B-1 首次 100 字符行扫描发现 `PlayerLinkTask` 两个 confirmed display 字段为 103/105 字符 | 1 | 只做等价多行格式化，未改变 Schema；随后重新执行行长、compile 与测试门 |
| 恢复已登录 GitHub 仓库标签页时首次 `goto` 在 10 秒导航等待上超时 | 1 | 只读检查确认 URL 已实际恢复为仓库首页；未重复导航、未重跑 job 或改变 GitHub 状态 |
| 第二个公共 run 状态回写的首个组合 `apply_patch` 在 canonical/history 文件边界处含无效 hunk | 1 | 工具原子拒绝且无文件被部分修改；拆为活动计划三文件与 canonical/history 两个精确补丁完成同步 |
| 6B-1 closure 后首次把 Phase 18 标为 pending，governance 要求活动计划必须恰有一个 in_progress phase | 1 | 将 6B-2 标为治理指针上的 in_progress，同时保留 prepared/waiting authorization 和“不得实施”边界；不把状态键外推为代码已开工 |
| 并行路线审计子任务被平台以 `prompt_cache_retention is not supported on this model` 在模型开始前拒绝 | 1 | 该子任务无命令、无文件修改、无项目 Provider/Key 调用；复用同一子任务发起受限重试并取得完整只读审计结果，主任务未受影响 |
| planning-with-files `session-catchup.py` 对本仓库无输出，被初步解释为无遗漏 | 1 | 人工审计确认脚本只检查根目录三文件，未解析 `.planning/.active_plan`；改用活动计划、Git/JSONL 手工恢复，补记 `d1cc2ed/32147545753` 与 RQ-060，不再把无输出当充分证据 |
| 统计 AGI-Saber Memory 文件的 `functions.exec` JavaScript 模板含 PowerShell反引号，脚本在命令执行前语法失败 | 1 | 改用 PowerShell `-f` 格式化且不含反引号，成功取得文件行数；没有文件或项目状态变化 |
| 5P entry 公共闭环后首次治理检查拒绝 `status: ready`，并发现活动计划有多个 Next Step 时第一节仍是旧 checkpoint | 1 | canonical 状态改回治理支持的 `in_progress`，保留正文“准备/未实现”；定位并统一所有 Next Step 为 `5P-1-product-contract-compiler` 后重跑，不放宽治理规则 |
| 5P 设计首次 cached diff check 发现 ADR-0032/0033 多余 EOF 空行 | 1 | cached 门禁阻止提交；删除两份 ADR 尾部空白，重新暂存后独立复跑 cached diff check |
| 5P 本地门禁临时文件清理被终端策略静态拒绝 | 2 | 首次组合命令和验证后的 literal Remove-Item 均在进程创建前被拒绝；目标已只读确认位于仓库 `tmp/` 且被 Git 忽略，停止重复删除并保留为本地临时产物 |
| 5E-1 源码审计误写 `app/harness/run_id.py` | 1 | 只读命令报告文件不存在，其他读取继续完成；后续按实际模块 `app/harness/run_ids.py` 定位，不重复错误路径 |
| 5E-1 审计在 Windows 直接把 `skills/*/manifest.yaml` 传给 `rg` | 1 | 前序文件均已读，只有该 glob 失败；后续用 `rg ... skills -g manifest.yaml`，不重复 Windows 路径通配写法 |
| 授权后的 P1 diagnostic 首次启动被本地 `LLM_PROVIDER=glm` 与内部 ID `zhipu` 的配置门禁拒绝 | 1 | 在 client factory 前失败，真实调用数为 0；沿用首轮实验的子进程级规范化为 `zhipu`，不改 `.env`、不打印 Key，再执行唯一获授权请求 |
| 干净环境验证把 TEMP 内旧 venv 的递归清理与安装串在同一 PowerShell 命令，被终端安全策略拒绝 | 1 | 命令未执行、无文件变化；改用带随机 ID 的全新 TEMP 目录且不做任何递归删除 |
| Task 4 首次公开 CI 因无上界 `openai` 解析到 3.0.0、缺少 SDK 2.x 的 `httpx` 合同而收集失败 | 1 | 不用额外 `httpx` 掩盖大版本漂移；把当前已验证合同收紧为 `openai>=2,<3`，用全新临时环境重装、回归并重新验证 CI |
| Task 4 收尾把唯一下一步写成授权门时漏掉 canonical `5D-6b` 字面键 | 1 | 治理预检阻止接受状态；保持授权范围不变，只在唯一下一步补回检查点键后重跑 |
| Task 4 陈旧状态扫描把 `*` 直接放进 Windows `rg` 路径参数 | 1 | 命令在只读扫描阶段返回路径语法错误且未运行后续门禁；改为显式列出两个设计文件，不重复通配路径 |
| 5D-6b 状态/决策同步补丁把 `截至` 误当独立一行 | 1 | `apply_patch` 原子拒绝且无部分修改；拆为 canonical state 与真实相邻日期文本两个补丁 |
| canonical status 改为进行中时移除了治理要求的“唯一下一步”固定元数据行 | 1 | 保留 `status: in_progress`，恢复唯一一条“唯一下一步”并在该行注明当前只做实验设计 |
| 提交前把多个 Git 检查用分号串行，cached diff 的 EOF 空行失败未阻止后续 commit | 2 | 5F-3 再次复发：commit 在 push 前已产生；立即删除三份文档尾部空行并 `--amend`，未把坏 SHA 推到远端。以后 cached diff check 必须作为独立工具调用成功后，下一调用才允许 commit |
| 5D-6b 实施计划 Next Step 只写实施文件与 Task，漏掉 canonical checkpoint 字面键 | 1 | 治理预检在功能代码前阻止；补回 `5D-6b` 后重跑，不改变阶段或任务范围 |
| 5D-6b 宽回归命令猜测了不存在的 `tests/test_provider_structured.py` | 1 | pytest 未收集任何测试；先列出真实测试路径，再改跑 `test_structured_output.py` 与实际评测测试，获得有效回归证据 |
| 5D-6b 受控诊断提交前 cached diff 发现两份新设计文档 EOF 多余空行 | 1 | 检查阻止 commit；用小补丁删除尾部空白，并重新暂存后独立复跑 cached diff check |
| P1 改为精确哨兵校验后，P4 失败案例的旧夹具仍返回泛化 `ok` | 1 | 严格边界正确让案例提前停在 P1；只把该夹具改为精确哨兵，保留 P4 才是目标失败点并重跑完整回归 |
| 5D-7 入口审计猜测了不存在的 `scripts/evaluate_skill_router.py` | 1 | 只读并行命令提前停止且未改代码；先用 `rg --files` 定位为 `scripts/evaluate_skill_routing.py`，后续按真实路径读取 |
| 5D-7 首次红灯测试使用当前 PATH 的 Hermes `python`，该环境没有 pytest | 1 | 未安装或修改全局环境；确认仓库 `.venv` 含 pytest 9.1.1，后续测试显式使用 `.venv\\Scripts\\python.exe` |
| 5D-7 最终验证猜测 CI 文件为 `.github/workflows/ci.yml` | 1 | 只读并行命令提前停止且未改代码；用 `rg --files .github scripts` 定位真实文件为 `.github/workflows/tests.yml`，后续复用其精确门禁 |
| 5D-7 暂存快照检查发现 ADR-0013 与领域评测 CLI 多余 EOF 空行 | 1 | cached diff check 阻止提交；删除两个多余空行并重新暂存，只有 cached check 成功后才提交 |
| 5D-7 GitHub Actions 的 `gh run watch` 遇到 unexpected EOF，随后两次短查询遇到 TLS handshake timeout | 3 | 停止重复 `gh` 路径；改用带 10 秒连接/20 秒总上限的公开 REST 查询，确认 run `31661582544` 对精确 SHA completed/success |
| V2 预算裁决首次把严格结果放入 `provider_capabilities/` | 1 | 完整回归的版本化结果扫描器正确拒绝非能力报告；不放宽扫描器，把裁决移动到独立 `budget_reachability/` 结果域并复跑全量，587 tests 通过 |
| 5D-7 Batch B 入口审计把 Windows 通配符直接作为 `rg` 路径参数 | 1 | 只读命令返回路径语法错误且未改文件；后续先用 `rg --files` 获取真实文件名再读取 |
| 5D-6b P1 诊断恢复时猜错 ADR-0011 文件名 | 1 | 只读命令未改文件；先用 `rg --files docs/adr` 列出真实路径，再读取 `0011-compose-skill-agent-loop-through-harness-preparation.md` |
| 原始 5C-1 至 5C-6 未持久化，文档误写 5C 完成 | 1 | 恢复完整账本，建立根级约束和活动计划，并修正所有冲突状态 |
| 旧规划目录无 active pointer 且停在 2026-08-01 | 1 | 新建持续开发计划并写入 `.planning/.active_plan` |
| `session-logs` 说明依赖的 `jq` 在本机不可用 | 1 | 使用 `rg` 和 PowerShell `ConvertFrom-Json` 流式读取同一原始 JSONL |
| PowerShell 默认读取 UTF-8 中文出现乱码 | 1 | 所有中文审计统一显式使用 `Get-Content -Encoding utf8` |
| 最终并行一致性扫描因 `rg` 无匹配返回退出码 1 | 3 | 5D-3 收尾再次复发但未修改文件；无匹配搜索必须单独运行并显式输出 `NO_STALE_MATCHES`，严禁与测试、编译或治理门禁共享失败传播 |
| 治理文件已有读取协议，但缺少机器可执行的一致性预检 | 1 | 在继续 5C-4 前增加仓库预检脚本、测试和 CI 门禁 |
| 状态源使用 `5C-5-precondition`，活动计划 Current Phase 只写中文简称 | 1 | 在 Current Phase 保留同一机器键，预检随后通过 |
| 治理负例测试硬编码旧检查点 `5C-4`，状态正常推进后失败 | 1 | 改为断言稳定的“Next Step 与 canonical checkpoint 不一致”语义 |
| V3 资源校准设计全量回归首次使用终端默认 `python`，实际指向 Hermes venv 且没有 pytest | 1 | 未安装或修改全局环境；改用仓库 `.venv\Scripts\python.exe`，随后 587 tests/103 subtests 全部通过 |
| 暂存区快照命令把计算路径和递归清理写在同一调用，被终端策略拒绝 | 1 | 改用仓库内固定临时目录，先验证快照，再校验绝对路径并分步清理 |
| 假定 `docs/adr/README.md` 存在，实际仓库只有编号 ADR 文件 | 1 | 改读最新 ADR 实例；以后先用 `rg --files docs/adr` 确认文件 |
| 推测 ADR-0003 文件名时使用了不存在的 `quality-gated-review-harness` | 1 | 先列出 `docs/adr`，按真实文件名 `quality-gated-agent-harness` 读取 |
| 恢复 5C-5 第三批时再次直接猜错 ADR-0009 文件名 | 2 | 停止该并行读取，先运行 `rg --files docs/adr`，再按真实文件名读取；将“列目录后读取”继续作为强制恢复动作 |
| 5C-5 收尾多文件补丁因末尾文档换行上下文不匹配而原子拒绝 | 1 | 确认无部分文档修改后，将补丁拆为状态、计划、路线和项目决策小组分别应用 |
| 初步把事实审查分类为内部 Skill，未先核对既有 EvaluatorStep | 1 | 暂停实现，完整审计 Harness/Evaluation 与测试；用 ADR-0009 取代方案并取消重复代码 |
| `python -m pytest` 命中桌面应用 Hermes Python，缺少 pytest | 1 | 改用仓库 `.venv\\Scripts\\python.exe` 执行项目测试，不重复错误解释器 |
| `gh run view/list` 连续两次遇到 GitHub API TLS 握手超时 | 2 | 等待后改用 PowerShell REST 客户端查询同一公开 run，确认 CI 成功 |
| 静态搜索把复杂正则和 PowerShell 双引号混用，导致解析错误 | 2 | 5D-1 状态扫描再次复发但未修改文件；立即改用单引号与多个 `rg -e` 模式，后续禁止把含 `|` 的 rg 表达式放进 PowerShell 双引号 |
| 合并测试补丁时把 Router 测试上下文误指到 Contract 测试文件 | 1 | `apply_patch` 原子拒绝、未产生部分修改；按真实文件拆成小补丁后成功 |
| 历史结果的 Windows CRLF 字节哈希在 Linux CI checkout 后变化 | 1 | 仅将该不可变归档标为 Git binary，保留原始字节；两个后续 Actions run 均成功 |
| 5C-6 首次陈旧短语扫描把“不得进入 5D”和“不能声称 5C 已完成”等保护语句误报为陈旧状态 | 1 | 收窄为检查旧 checkpoint、旧唯一下一步和 5C-6 未开始/进行中等精确矛盾短语，结果为 `NO_CURRENT_STALE_MATCHES` |
| 5C-6 首次暂存区格式检查发现 ADR-0010 文件末尾有多余空白行 | 1 | 删除尾部空行，重新暂存后再运行 cached diff check |
| 5C 退出复核发现 `RouterDecision` 允许命中候选夹带无关证据 | 1 | 先补失败测试，再要求 selected/ambiguous 的 evidence 身份与 candidate 身份完全一致；rejected 仍保留部分证据 |
| holdout 元数据把双 Skill 冻结点误写为前一个文档提交 `cfd2084` | 1 | 用 Git 树确认真实双 Skill 合同首次位于 `4103d42`，只更正 provenance 并加回归断言，不改案例、规则或结果 |
| 治理负例把 `5D` 硬编码为陈旧检查点，状态合法推进到 5D 后不再失败 | 1 | 改用不可能与正式路线重合的 `stale-checkpoint`，让测试验证不一致语义而非某个阶段名 |
| 5D-2 初始并行读取猜测 `app/agent/models.py` 存在，导致命令组返回非零 | 1 | 没有修改文件；停止猜测 Agent 路径，先用 `rg --files app` 列出真实模块再读取 |
| 5D-2 首个合同补丁假设 `app/agent/__init__.py` 的 docstring 文本，原子校验拒绝 | 1 | 确认没有创建半个 context 模块；读取真实小文件后将新增模块与导出补丁拆开 |
| 恢复活动计划时把 `.active_plan` 值误当成仓库根相对路径，漏掉 `.planning/` | 2 | 两次命令均只读且未改文件；以后固定先读值，再显式从 `.planning/<name>` 拼接活动计划目录，不从仓库根直接解析 |
| 读取执行边界测试时猜测不存在的 `tests/test_skill_execution.py` | 1 | 先用 `rg --files tests` 查到真实 `test_skill_execution_boundary.py` 后读取；未改测试或源码 |
| 领域生产装配入口审计再次把 `tests\\test_*` 作为 Windows `rg` 路径，并猜测不存在的 `app/tools/knowledge.py` | 2 | 两次均为只读失败且未改代码；立即改用显式 `tests` 目录、`rg --files` 和符号搜索定位 `app/tools/adapters/knowledge.py`，不再猜路径 |
| 5D-2 聚焦回归猜测不存在的 `tests/test_provider_models.py` | 1 | 该次 pytest 未收集任何测试；列出真实 Provider 测试后改跑 `test_provider_tool_calling_models.py` 与 `test_provider_contracts.py` |
| 5D-4 共享证据转换首个补丁假设了 Harness `__init__` docstring | 1 | `apply_patch` 原子拒绝且没有产生部分源码修改；读取真实文件后把新增模块、Adapter 与导出拆成独立小补丁 |
| 5D-4 直接回答 Fake Provider 只声明 text chat | 1 | 编译后的 Skill 请求仍携带白名单工具规范，能力协商正确拒绝；修正测试 Provider 声明 `tool_calling`，不放宽生产门禁 |
| 5D-4 聚焦回归猜测不存在的 `tests/test_rag_provider.py` | 1 | pytest 在收集前退出、没有测试运行；先用 `rg --files tests` 获取真实 RAG 文件，再重跑实际测试集合 |
| 5D-4 ToolRuntime 失败测试的 Fake Provider 无条件读取成功 payload | 1 | 真实失败 Observation 的 `data` 为 null，测试 double 先按 `success` 分支，再验证 Preparer 从失败执行记录拒绝草稿并只暴露安全 code |
| 5D-4 项目决策同步补丁假设 `截至` 独占一行 | 1 | `apply_patch` 原子拒绝且无部分修改；按真实相邻日期行拆小补丁后同步 |
| 5D-4 收尾猜测 workflow 名为 `.github/workflows/ci.yml` | 1 | 只读失败且未执行脚本；先用 `rg --files .github/workflows` 找到真实 `tests.yml` 后按其门禁核对 |
| 5D-5 初始并行审计再次让无匹配 `rg` 的退出码 1 传播到整个批次 | 4 | 无文件修改；立即拆分治理预检与只读审计，后续无匹配搜索继续单独运行并显式处理 |
| 5D-5 审计猜测 Skill 输出模型位于独立 `output_schema.py`/聚合 `schemas.py` | 1 | 无文件修改；先读真实 Manifest 的模型引用并用 `rg` 定位到两个现有 Skill 模块 |
| 5D-5 terminal builder 测试 helper 用规范化前报告计算输入 commitment | 1 | 生产边界正确拒绝全部 7 个案例；测试改为先经过真实 Skill Input Model，再生成与未来 Harness 字节一致的 binding |
| 5D-5 从 `app.skills` 根包重导出 review executor 形成 Agent/Skill 循环 import | 1 | 收集阶段失败且无运行时产物；移除根包重导出，保持 executor 仅从显式子模块导入并记录依赖方向 |
| 5D-5 dry-run 临时目录的 `Remove-Item -Recurse` 被终端策略拒绝 | 1 | 已先验证绝对路径位于仓库 tmp；随后用 `apply_patch` 删除本轮生成的全部文件，未改用跨 shell 删除或放宽权限 |
| 5D-5 首次 cached diff check 发现两份新增计划文档尾部多余空白行 | 1 | 删除尾部空白行并重新暂存两份文档，再独立复跑 cached diff check |
| 5D-5 功能提交的 Git smart-HTTP 连续遇到 TLS 握手失败/EOF | 5 | schannel、OpenSSL、HTTP/1.1 与 TLS1.2 均未降低校验且失败；改用 GitHub Git Database API，逐 blob/tree/commit SHA 校验后原子更新 main |
| 5D-6a 恢复时把工具返回包装误当成 `.active_plan` 内容 | 1 | 只读命令未改文件；改为在同一 PowerShell 进程内读取并拼接 `.planning/<active>`，不再从工具展示字符串解析路径 |
| 5D-6a 审计时猜测不存在的 `app/tools/contracts.py` | 1 | 只读失败且未改文件；先用 `rg --files app/tools` 获取真实路径，确认合同位于 `models.py` 与 `schema.py` |
| 5D-6a 首个设计/状态合并补丁猜错错误账本的精确行 | 1 | `apply_patch` 原子拒绝，未创建半份设计；先独立新增设计文件，再读取计划尾部并用小补丁更新状态 |
| 5D-6a Adapter 初稿错误地从函数注解推导 output model | 1 | 在运行测试前发现；改为显式 `EvaluationResponseModel`，保证 transport Schema 与本地验证模型可审计对应 |
| 5D-6a Harness 失败路径测试遗漏 `CoachDraft` 导入 | 1 | 首次只覆盖 draft-preparation failure；补导入后重跑，确认真实覆盖两次非法结构化响应后的 deterministic fallback |
| SSH 诊断在 accept-new 后返回 `Permission denied (publickey)` | 1 | 只新增 GitHub host key，未修改 remote 或上传密钥；确认现有 SSH key 未获 GitHub 授权后停止 SSH 路径 |
| Git Database API 首个内联脚本含 PowerShell backtick，触发 JS 解析错误 | 1 | 脚本未执行、没有外部写入；改用字符串拼接构造 `HEAD:path` 后再运行 |
| GitHub commit API 首次把 PowerShell 多行消息序列化为数组并返回 422 | 1 | blobs/tree 已通过 SHA 校验，remote ref 未更新；改用单行 subject 重做 commit 步骤 |
| GitHub API commit 与本地 CLI commit 因消息尾部换行得到不同 SHA | 1 | 证明 tree/parent/作者/时间/消息均一致，定位仅差最后一字节；精确重建 API commit 对象并用 expected-old 原子同步本地/远端 refs，原提交仍在 reflog |
| 5D-5 公开验证记录组合补丁假设错误账本行顺序 | 1 | `apply_patch` 原子拒绝且没有部分修改；读取真实尾部后拆成状态/历史与计划/进度两组补丁 |
| 5D-6b 严格 JSON 补强补丁把两个文件更新块错误写进同一 hunk | 1 | `apply_patch` 原子拒绝且没有部分修改；立即拆为测试与实现两个小补丁，再单独运行 Zhipu 测试 |
| 5D-6b 能力组合边界补丁两次假设错误的源码相邻顺序 | 2 | 两次 `apply_patch` 均原子拒绝；读取精确行后把请求组合、参数编码与响应 finish reason 拆为独立补丁，不重复猜测上下文 |
| 5D-6b 收尾差异审查把“无陈旧措辞”的 `rg` 退出码 1 直接透传为整条命令失败 | 1 | 差异输出已完整生成且没有陈旧匹配；后续 stale scan 显式把无匹配视为通过，不再与长差异输出串成一个成功条件 |
| 5D-6b Real Adapter Protocol Slice 初始审计猜测 `app/agent/models.py` 存在 | 1 | 只读批次失败且没有文件修改；先用 `rg --files app/agent app/tools` 获取真实模块，确认 Agent 合同位于 `loop.py`，不再沿用猜测路径 |
| 5D-6b 计划复读按日期猜测了不存在的 real-provider 文件名 | 1 | 代码与测试读取成功，只有文档读取失败且无写入；立即用 `rg --files docs/plans` 定位 canonical 名称，后续引用文件前先查清单 |
| 5D-6b Adapter protocol runner 从 `app.evaluation.__init__` 重导出导致全量测试循环导入 | 1 | 聚焦测试通过但全量收集揭示 `evaluation -> agent -> skills -> harness -> evaluation`；移除门面重导出，编排型 runner 只从具体模块导入，并把全量测试作为必过门禁 |
| 5D-7 真实门入口审计的组合读取命令因最终 `rg` 无匹配返回 1 | 1 | 前置文件读取和脚本清单有效、无文件修改；将“未找到 DeepSeek factory 的执行脚本”作为实际缺口继续精确审计，不把预期无匹配解释为业务失败 |
| 新 DeepSeek 组合结果首次进入公开结果目录后，旧全目录合同测试把它误解析为 P1 报告 | 1 | 保留红灯；按结构键分派到 `ProviderAdapterProtocolExperimentRecord`，并新增固定文件 SHA/准入边界测试，聚焦回归 9/9 通过 |
| 协议结果同步后的陈旧短语扫描再次让 `rg` 无匹配返回退出码 1 | 1 | 无文件修改且语义实际为通过；后续将该扫描改为显式捕获无匹配并输出 `NO_STALE_MATCHES`，不再把预期空结果当作命令错误 |
| 5D-6b canonical 收口复读沿用不存在的旧文档名称和 PowerShell 通配写法 | 1 | 已读取的 execution state 有效，缺失路径无写入；用 `rg --files docs` 与 planning 文件清单定位 `requirements_change_log.md`、`roadmap.md`、`roadmap_v1_3_amendment.md`、`architecture_capability_matrix.md`，后续只访问真实路径 |
| 5D-6b 活动计划 findings/progress 追加补丁错误假设两文件共享同一尾部上下文 | 1 | `apply_patch` 原子拒绝且没有半写入；分别读取真实尾部并拆成两个追加块，功能与 canonical 状态不受影响 |
| 5D-6b 领域状态追加补丁错误假设路线历史尾句，工作树安全补丁又错误假设设计列表措辞 | 2 | 两次 `apply_patch` 均原子拒绝且无半写入；先读取各文件真实尾部/匹配行，再把代码测试、路线历史和教学文档拆开更新 |
| 5D-6b 提交前安全扫描再次把复杂引号正则放入 PowerShell 字符串 | 1 | 只读批次在解析阶段失败，无暂存或文件修改；改为多个简单固定字符串扫描，禁止在 PowerShell 命令参数中内嵌混合单双引号密钥正则 |
| 5D-6b 最终陈旧状态扫描把多个含空格模式放在 PowerShell 双引号命令中 | 1 | 扫描未执行且无文件修改；改为单引号 `rg -e` 模式并将治理检查、扫描和差异审查分开运行 |
| 5D-7 Batch C 恢复时猜测治理脚本、ADR、tool adapter 和 planning 物理路径 | 4 | 所有失败均为只读定位且未改文件；逐次用 `rg --files`/目录清单确认真实路径。后续把 canonical 名称与物理路径分开，不从交接简称推导文件名 |
| Batch C 首次测试命中桌面 Hermes Python，缺少 pytest | 1 | 未改全局环境；改用仓库 `.venv\\Scripts\\python.exe`，取得预期模块缺失红灯并完成 TDD |
| Harness dry-run 命令含递归清理，被终端策略阻止 | 1 | 命令在执行前被拒绝、没有删除或运行；改用独立 TEMP 目录并保留产物，dry-run published |
| Batch C 批量审查让预期无匹配 `rg` 的退出码 1 传播 | 1 | 拆分候选、结果和安全扫描；显式把无 case-id 硬编码匹配记录为通过，不掩盖其他检查 |
| Batch C 状态写回三次假设 roadmap/planning 尾部上下文 | 3 | `apply_patch` 原子拒绝，无半写入；读取每个文件真实尾部后分别追加，并将矩阵/决策拆开更新 |
| Batch D 入口审计把不存在的 `app/providers/chat_adapter.py` 加入只读 `rg` 路径 | 1 | 命令未改文件；用 `rg --files app` 定位实际 `ChatEvaluationAdapter` 在 `app/harness/adapters.py`，再完整读取真实接缝 |
| D1 首次测试补丁把旧 Harness 断言插入新安全测试 | 1 | 聚焦测试及时发现断言位置错误；移动断言回原测试并单独验证 1.0.0/1.1.0 两条路径 |
| D4 更正回归再次用桌面 Hermes Python 启动 pytest，环境缺少 pytest | 1 | 测试未启动且无文件变化；显式改用仓库 `.venv\Scripts\python.exe`，完整回归随后通过 |
| D4 更正复核再次猜测 workflow 名为 `ci.yml` | 1 | 只读失败且无脚本执行；先列出 `.github/workflows`，按真实 `tests.yml` 复核全部门禁 |
| DeepSeek 协议证据归档收尾的 GitHub CI 查询路径间歇性 TLS/HTTP timeout | 5+ | push 与 Actions run 创建均成功且无功能漂移；停止密集重复不稳定的 `gh`/jobs 查询，同类只读失败归入本行，固定用有界 PowerShell REST 核验最终精确 SHA，不把观测失败误报为测试失败 |
| 生产装配设计提交前 diff check 发现三份新文档 EOF 多余空行 | 1 | 检查阻止提交；用小补丁移除多余行并重新运行 staged/working-tree diff check，不改变设计语义 |
| 生产装配聚焦回归首次使用 30 秒 shell timeout，测试尚未完成即被终止 | 1 | 没有断言失败或代码变化；同一组改用 60 秒上限重跑，24/24 通过 |
| 生产装配首次完整回归仍保留 held-out `1.0.0` 预检常量 | 1 | 543 tests/103 subtests 已通过、2 个 no-I/O 预检失败；按 ADR-0021 只把冻结常量更新为 `1.1.0`，相邻 25/25 随后通过 |
| 生产装配安全扫描再次把 `docs\security*` 作为 Windows `rg` 路径 | 1 | `.gitignore` 已成功读取且暴露真正的 runs 目录边界，只有通配扫描失败；改用显式文件清单，并把真实门默认运行目录移入已忽略/受 CI 保护的 `data/runs/` |
| 生产装配 CI 状态回写把唯一下一步只写成自然语言动作 | 1 | governance 在提交前拒绝，因为正文没有显式包含 canonical `5D-7`；补回检查点名并重新验证，没有改变执行状态或发起外部调用 |
| 真实领域门恢复时猜测 ADR-0020 的简称文件名 | 1 | 只读命令报告文件不存在，其他检查无写入；立即用 `rg --files docs/adr` 定位真实文件 `0020-use-no-io-admission-and-thin-coordinator-for-domain-heldout.md`，未触发 Provider 调用 |
| Fresh-Gate 4 相邻回归猜测不存在的 `tests/test_provider_adoption.py` | 1 | pytest 在收集前退出且没有运行测试或改文件；用 `rg --files tests` 定位真实文件为 `tests/test_provider_adoption_control.py`，随后实际相邻集合 93/93 通过 |
| Fresh-Gate 4 复核再次猜测 workflow 为 `.github/workflows/ci.yml` | 1 | 只读失败且没有执行 CI 命令；立即用 `rg --files .github` 定位 `tests.yml`，随后按真实 workflow 门禁完成本地验证 |
| 真实 calibration 归档收尾在 TEMP dry-run 前加入递归清理 | 1 | 终端安全策略在执行前拒绝整组命令，没有删除文件或调用 Provider；改用全新 TEMP 路径并完成全部只读/临时验证 |
| 真实 calibration 安全扫描把 Windows 通配符直接传给 `rg` | 1 | 扫描在读取文件前失败，没有改文件或调用 Provider；改用两个显式 JSON 路径并单独执行 |
| 6A-7 首次独立 cached diff check 发现 Dockerfile EOF 多余空行 | 1 | 检查在 commit 前阻止提交；用最小补丁删除空行、重新暂存，并独立重跑 cached diff check，不改变镜像语义 |
| 6A-7 首个 Linux one-off smoke 只返回过宽 `packaging_smoke_worker_failed` | 1 | pytest/真库/build/migration/API ready 均已成功，不猜测业务根因；用红灯增加 allowlisted stage code 与 bounded service logs，再以新 exact-SHA CI 定位 |
| module-entry 状态回写时 canonical“唯一下一步”漏写 checkpoint 字面键 | 1 | governance 在提交前阻止；把 `6A-7-packaging-exit-review` 补回同一行，不改变根因、修复范围或阶段状态 |
| direct script 在 Linux image 中从 wheel 导入 app，导致 Alembic PROJECT_ROOT 漂移 | 1 | d8c5063 安全码与 bounded logs 定位；用 `python -m scripts...` 统一 import root，adf53e5 packaging-smoke 全绿且未放宽 readiness |
| 6B-2 首次 cached diff check 发现 Link Worker 测试 EOF 多余空行 | 1 | cached 门在 commit 前阻止；只删除尾部空行并重新暂存，cached diff/governance 通过后才提交，不改变行为 |

### 5D-7 V3 资源校准离线实现（2026-08-15）

- [x] 写入 ADR-0026 对应的详细 implementation plan；
- [x] 创建两套全新 development fixture/profile 并拒绝 V2 内容/digest 复用；
- [x] 用现有 production Executor 捕获 baseline/ceiling 各四阶段请求；
- [x] 冻结不含正文的 8-request public snapshot；
- [x] 用显式 Fake Provider 验证 8-call、64-output、首错停止和资源账本；
- [x] 实现 25% 余量、固定向上舍入、成本/30 秒 deadline 拒绝的纯预算推导；
- [x] 实现不接收 Provider/Key/client 的 no-I/O admission；
- [x] 完成 598 tests/103 subtests、两套 RAG、compileall、Harness/安全/治理本地门禁；
- [x] 提交、推送并由 `2d67696` / Actions `31867655627` 完成 exact-SHA 公开验证；
- [x] 展示真实 development replay 上限并获得用户单独确认；

### 5D-7 V3 development Usage 真实回放（2026-08-15）

- [x] 写入真实回放实施计划，保持 5D-7、ADR-0026 与 RQ-033 边界；
- [x] 增加 no-I/O proof 到一次真实 run admission 的显式升级；
- [x] 分开 Fake simulation 与真实 result 类型，保留真实计费调用数；
- [x] 增加 Key-last CLI、prepare-only、不可变结果和完整 8/8 后的预算记录；
- [x] 聚焦 19、相邻 74、完整 606 tests 与 compileall 通过；
- [x] 完成两套 RAG、Harness/security/governance/diff 等剩余本地门禁；
- [x] 提交、推送并由 `6aa8c43` / Actions `31868747216` 验证真实入口；
- [x] 在同一干净 SHA 上运行 prepare-only，确认 external calls 0 且无结果文件；
- [x] 执行一次真实 replay；第 1 call 未形成规范化响应后首错停止，保存不可变结果且不生成预算；
- [x] 更新持久状态并完成聚焦 34、完整 611 tests/103 subtests 与全部本地门禁；
- [x] 提交、推送不可变结果/裁决，并由 `421a243` / Actions `31869409106` 完成
  exact-SHA public CI。

### 5D-7 DeepSeek calibration 失败采用决策（2026-08-15）

- [x] 复读不可变结果、裁决、ADR-0025/0026 与 Adapter/分类器源码；
- [x] 比较关闭、建立新诊断门和无限搁置三种方案；
- [x] 接受 ADR-0027：关闭当前 V3，不作模型质量负面结论；
- [x] 将允许列表安全 `provider_error_code` 设为未来真实 Provider 门前置条件；
- [x] 保持本批 Key/Provider/external calls 为 0；
- [x] 完成 51 项聚焦、611 tests/103 subtests、两套 RAG 与全部本地门禁；
- [x] 决策提交 `ea91e9697c820c0850db488a93263fc169719515` 已推送并通过
  Actions run `31872476103` 的 exact-SHA public CI。

### 5D-7 安全 Provider 错误 provenance 离线切片（2026-08-15）

- [x] 记录 GLM-5.3 普通 API 尚未上线，G53-0 deferred；不立即切 Flash，GLM-5.2 仅作开发基线；
- [x] 建立 Provider-specific allowlist，未知细分错误自动变为 `null`；
- [x] 将允许列表安全码接入 Provider stop snapshot 与资源 calibration result/adjudication；
- [x] 保证旧真实 V3 JSON 能读取且不修改历史结果 bytes；
- [x] 新增允许、拒绝、公开边界与兼容性聚焦测试，聚焦 Provider/Calibration/Domain 回归 89 passed；
- [x] 完成完整回归 `616 passed, 103 subtests passed`、两套 RAG、compile/security/dry-run、治理和 diff 门禁；
- [x] 提交 `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a`、推送并通过 Actions run
  `31874240935` 的 exact-SHA public CI。

### 5D-7 Prompt/Context 与领域评测收尾审查（2026-08-15）

- [x] 对照原始 5D-7 设计逐项审查 Tool、Evidence、事实/引用、注入、终态和资源合同；
- [x] 区分“评测门完成”与“领域 Provider 准入”，保留当前无模型准入和质量 unknown；
- [x] 比较等待 GLM-5.3、立即切 Flash/追 Pro、诚实关闭评测门三种方案；
- [x] 接受 ADR-0028：G53 deferred 不阻塞 5D-7，Flash/Pro 分层不自动重开；
- [x] 5D-7 相关聚焦回归 `130 passed, 4 subtests passed`；
- [x] 完成本地完整回归 `616 passed, 103 subtests passed`、两套 RAG、安全、治理和差异检查；
- [x] 审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已推送并通过 Actions
  run `31876536179` 的 exact-SHA public CI；
- [x] 公开验证后进入唯一下一检查点 `5D-exit-review`，不得直接进入 5E。

### 5D Python 受限 Agent Loop 退出审查（2026-08-15）

- [x] 对照 5D 入口设计逐项核对十项功能要求和非功能要求；
- [x] 验证两个真实 Skill 的受限执行、实际本地知识工具、唯一 Harness 和 typed terminal output；
- [x] 运行核心执行跨层回归 `173 passed, 34 subtests passed`；
- [x] 运行 Provider/领域采用与资源控制回归 `176 passed, 22 subtests passed`；
- [x] 区分 Adapter 协议、模型领域质量与系统安全终态，保留当前无领域 Provider 准入；
- [x] 审查 5E 前置，确认现有 run_id、停止原因、Usage、Tool record 与 Artifact 可被统一；
- [x] 记录 `max_revisions` 为 Harness 运行政策并要求 5E 暴露其 provenance，不静默扩张 Manifest；
- [x] 完成初学者退出审查文档，并把唯一下一检查点切换到 5E 入口设计；
- [x] 完整本地门禁通过：`616 passed, 103 subtests passed`、两套 RAG 1.0、compileall、
  Harness SDK/tracked-data boundary、dry-run、治理和 diff check；
- [x] 退出审查提交 `2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已推送并通过
  Actions run `31877076222` 的 exact-SHA public CI。

### 5E AgentRuntime V1 入口设计（2026-08-15）

- [x] 审计 Boundary、Context、Agent/Provider/Tool、Harness 与 Artifact 的现有运行信号；
- [x] 比较外层事后包装、薄 Runtime + observer、事件溯源/DAG/第三方框架三种方案；
- [x] 以 ADR-0029 接受薄 Runtime，并保留 ReviewHarness 唯一发布权；
- [x] 冻结 request/result、Signal/Event、Runtime/publication 双状态和安全失败分类；
- [x] 冻结 complete/partial/unknown Usage 与版本化定价边界；
- [x] 冻结进程内 live stream、原子最终 Trace 及不保存正文/秘密的安全边界；
- [x] 拆分 5E-1 至 5E-4，保持 5P/5F/阶段 6/8 边界不变；
- [x] 完成本入口设计批本地门禁：`616 passed, 103 subtests passed`、两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、治理和 diff check；
- [x] 设计提交 `c91c2d75f85e1315e65e9768894982556053a7b0` 已推送并通过 Actions
  run `31878052835` 的 exact-SHA public CI；
- [x] 进入 5E-1 前先讲解合同、Usage 和原子 Trace Store 的原理与 TDD 证明范围。

### 5E-1 Runtime Contract、Usage 与 Trace Store（2026-08-15）

- [x] 初学者解释具体问题、Signal/Event、Usage unknown、数据流、测试与排除项；
- [x] 审计 Pydantic、共享 run ID、SkillExecutionRequest、Harness Store 与预算上界；
- [x] 写入可执行的 5E-1 TDD 实施计划；
- [x] 先写合同、Recorder/Usage、Store 失败测试并确认红灯；
- [x] 实现低依赖 Signal、严格 Runtime 模型、Recorder/Usage 与 Trace Store；
- [x] 完成聚焦、相邻、完整回归和全部本地门禁；
- [x] 同步状态，提交、推送并完成 exact-SHA public CI。

### 5E-2 Observable run() Vertical Slice（2026-08-16）

- [x] 初学者解释 observer、同步 Runtime、失败映射和 Trace 提交边界；
- [x] 审计 AgentLoop、ToolRuntime、SkillReviewExecutor、ReviewHarness 稳定接缝；
- [x] 比较方案并写入入口设计与 ADR-0030，不以 5E-1 代码存在代替设计；
- [x] Task A：合同 1.1、1.0 读取兼容、observation port 与 prospective terminal TDD；
- [x] Task B：共享 Observed Provider 与 AgentLoop 观察；`28bd910` / Actions `31952026988`
  exact-SHA 公共 CI 通过；
- [x] Task C：Harness/Executor 持久化后观察与 Artifact 投影；`8b69c9b` / Actions
  `31957712118` exact-SHA 公共 CI 通过；
- [x] Task D：两个真实 Skill 的统一同步 `run()` 纵向切片；新增 18 项测试，完整回归
  `747 passed, 110 subtests passed` 与全部本地门禁通过；
- [x] 完整本地门禁与持久状态同步；
- [x] 实现提交、推送与 exact-SHA CI：`d49508e` / Actions `31959646589`；
- [x] 5E-2 正式闭环，未实现 `stream()`。

### 5E-3 Live `stream()` & Parity 实现与验收（2026-08-17）

- Status: complete
- 5E-2 已由 `d49508e` / Actions `31959646589` exact-SHA 公共验证完成；本阶段先完成
  `run()` 的事件交付接缝、同步/流式终态一致性、消费者失败隔离和背压边界审计，再进行 TDD；
- 先解释为什么“实时事件”不等于 Token streaming，也不等于 durable event log；
- 先比较最小进程内 worker/queue、直接 generator、外部消息队列三种方案，再写 ADR 和
  失败测试；不实现真实 Provider、SSE、取消/恢复、API、Memory 或第三方 SDK。
- 入口审计已完成：Recorder 是可信事实源；普通事件在追加后交付，terminal 必须在
  Trace 原子写入并 commit 后交付；消费者失败与可信 Recorder 失败分层。
- ADR-0031 已冻结：采用进程内 worker + 有界 `queue.Queue`，不采用直接 generator 或外部
  消息队列；背压为满时阻塞，订阅关闭不取消业务执行。
- stream item、worker/queue、实时顺序、run/stream parity、success/degraded/rejected/boundary
  failure、背压、关闭和 unexpected worker error 测试均已通过；本地聚焦 `15 passed`，完整
  回归 `762 passed, 110 subtests passed`。
- 提交 `80b76a1` 已推送；GitHub Actions run `31960987333` exact-SHA 公共 CI 成功，5E-3 正式闭环。

### 5E-4 Runtime Evaluation & Exit Review（2026-08-17）

- Status: complete
- 先审计 5E-1 至 5E-3 的功能合同、失败语义、资源/Usage、Trace 隐私、stream parity、
  公开证据和教学边界；不把测试数量直接等同于生产可用。
- 建立一张可追溯的 exit matrix：每项要求绑定源码、测试、结果、限制和是否允许关闭 5E；
  发现缺口时只做当前阶段所需的最小修补，不引入新框架或真实 Provider。
- 明确 5E 关闭后唯一下一阶段仍由 canonical 状态决定；本检查点不进入 5P、5F、阶段 6/8。
- 首轮矩阵已完成，Runtime 相关聚焦集合 `128 passed`；当前没有必须立即补的结构性缺口，
  deferred/unknown 边界已单独列出。
- 完整回归 `762 passed, 110 subtests passed` 与全部本地门禁通过；退出决策为
  `close-with-deferred-boundaries`；提交 `3d36561` 已由 Actions `31962252231` 完成
  exact-SHA 公共验证，5E-4 与整个 5E 正式完成。

### 5P-entry-design（2026-08-17）

- Status: complete
- 用户已明确“继续下一步”，解除 RQ-039 的暂停；本检查点只授权设计，不授权实现或 5F；
- 已审计 Runtime request/result、Artifact/Trace Store、Riot/DataDragon、Summary/Report CLI、
  Skill/Catalog/Boundary、Prompt/Context identity、Evaluation/Revision 与路线范围；
- 已比较 handler 串脚本、暴露 Runtime 内部合同、薄 Adapter + Application Service 三种方案；
- 已新增完整设计和 ADR-0032/0033；本地 762 tests/110 subtests、两套 RAG 与全部门禁通过；
- 提交 `49841ec` 已通过 Actions `31985199623` exact-SHA 公共 CI，entry design 正式完成。

### 5P-1 Product Request & Typed Skill/Runtime Compiler

- Status: complete
- 用户授权范围已完成：严格产品 DTO、typed selection、Artifact binding、Manifest-derived policy、
  教学、TDD、本地门禁和 exact-SHA 公共 CI 均通过；
- 只建立严格产品请求、trusted typed selection、Artifact binding 与 Manifest-derived policy；
- 不安装 FastAPI、不实现 Prompt Program/Application Service、不读取 Key、不调用 Riot/Provider；
- TDD 实施计划：`docs/plans/2026-08-17-5p1-product-contract-compiler-implementation.md`；
- 公开证据：提交 `57bd36adcd289b7cc51c1c430e04398daf0683f3`，Actions `31987501935`；
- 5P-1 不包含 Prompt Program、FastAPI、Riot/Provider I/O；已停止在 5P-2。

### 5P-2 Prompt Program V1 & Runtime Composition Root

- Status: complete
- 用户已明确继续；按实施计划先以 TDD 建立严格 manifest/catalog/resolver，再接 Runtime identity；
- 已实现：版本化 Prompt Program、组件 fingerprint/drift gate、secure Evaluation 1.1 限制、
  产品 manifest、verified Runtime identity 和薄 composition root；
- 不安装 FastAPI、不读取 Key、不调用 Riot/Provider、不进入 5P-3 或 5F；
- 本地完整回归 `805 passed, 110 subtests passed`；提交 `0a9651f` / Actions `31988837293`
  已完成 exact-SHA 公共验证，5P-2 正式闭环。

## 5P-2 当前实施说明

`5P-2-prompt-program-runtime-composition / complete`：Prompt Program manifest 不保存
Prompt 正文，只保存 program/Skill/Context/Evaluation 身份与现有 canonical component fingerprints。
`PromptProgramResolver` 在 composition 创建和每次 Runtime identity 解析时重算指纹；Skill、Context、
Evaluation 或 Revision 资产漂移时 fail closed。旧 direct Runtime 测试通过显式
`LegacyRuntimeIdentityResolver` 兼容，不等于产品路径已经绕过 drift gate。

### 5P-3 Domain Pipeline Promotion & Application Service

- Status: complete
- 用户已明确继续；入口审计、教学说明、TDD、Domain/Application Service 和 secure product
  execution factory 已本地完成；
- Summary/Report 已提升为 app-level domain service；Application Service 严格组合 5P-1
  compiler、5P-2 verified composition 与 `AgentRuntimeV1.run()`；
- 不安装 FastAPI、不实现 receipt/query、不读取 Key、不调用 Riot/Provider、不进入 5P-4 或 5F；
- 领域/应用/组合聚焦与相邻回归通过，完整回归 `830 passed, 110 subtests passed`，两套 RAG、
  compileall、Harness/secret、dry-run、governance 和 diff 门禁通过；实现提交 `4bd5c83` 已由
  Actions `31998739178` exact-SHA 公共验证成功。
- 5P-3 闭环时 canonical 只交接到 `5P-4-file-backed-run-receipt-query`；该历史暂停已由 RQ-044
  解除，5P-4 现已公开完成并只交接到尚未开始的 5P-5。

本批错误日志：

- 只读审计时误猜 `app/harness/run_id.py`，实际共享实现为 `run_ids.py`，已改用真实路径；
- Windows PowerShell 未展开 `skills/*/manifest.yaml`，已改用 `rg ... skills -g manifest.yaml`；
- 第一次组合补丁含空的 Update hunk，`apply_patch` 原子拒绝、没有文件被部分修改；已拆成
  有实际上下文的补丁继续；
- 继续只读审计时误猜 `app/harness/artifacts.py`，实际 Artifact Store 位于
  `app/harness/store.py`；已读取真实实现并保持复用其原子写入约定；
- 查找 5E 设计时误猜简写文件名并在 Windows 给 `rg` 传了未展开通配符；命令只读失败，
  已改为先列出真实文件名再定向读取；
- 首轮绿灯为 `28 passed, 6 failed`：Artifact schema 被误按三段软件 semver 校验，且测试
  fixture 的 RouterDecision 缺少已有合同要求的 evidence；已分别兼容既有 `1.0` Schema
  版本并补真实路由证据，没有削弱产品合同；
- 第二轮绿灯为 `33 passed, 1 failed`：Pydantic 在 Python dump 中按合同保留 tuple，负例
  fixture 却直接 `.append()`；已先复制为 list，再构造 terminal 后事件的非法输入；
- 实现后审查发现 ToolResult 允许缓存命中 `attempts=0` 且现有 latency 为 float，初版 Runtime
  Signal 错误收窄为 attempts>=1/int；新增缓存路径测试，并新增 Usage 完整性与 Trace 调用配对
  负例，先确认这些遗漏会红灯再修实现；
- 审计 ToolResult 时再次在 Windows 向 `rg` 传未展开的 `tests/test_tool*`；同一组合命令仍返回
  真实目标文件结果，后续统一改用目录加 `-g`，不依赖 shell glob；
- 首次相邻回归误猜 `tests/test_agent_context.py` 等文件名，pytest 在收集前以 file not found
  退出、没有测试结果；已改为先用 `rg --files tests` 获取真实测试文件名再运行；
- 项目门禁审计误猜工作流名为 `.github/workflows/ci.yml`，实际为 `tests.yml`；只读组合
  命令其余结果有效，已改读真实工作流后逐项执行；
- 最终全量 pytest 首次通过延迟 cell 返回时没有暴露可继续轮询的 PTY session，只有 39%
  进度且无 exit code，不能作为证据；已用显式保留 session_id 的新运行重新执行并完整得到
  `655 passed, 103 subtests passed`。并行残留使该次耗时变长，但结果与测试内容未受影响；
- 首次尝试一次性回写全部 5E-1 public 状态时，一处跨行上下文与真实长段落不完全一致，
  `apply_patch` 原子拒绝且没有部分修改；已拆成精确小补丁完成状态交接；
- 5E-2 符号清单命令在 Windows 直接传入 `app/runtime/*.py`，该 glob 未展开，Runtime 部分
  报路径错误但其余模块结果有效；后续改用目录加 `-g '*.py'` 或真实文件列表，不重复该写法。
- Task A 恢复审查再次把 `tests/test_runtime*.py` 直接传给 Windows `rg`，glob 未展开；
  命令只读失败且无文件变化，随后改用 `tests -g 'test_runtime*.py'` 并完成真实检索。
- legacy 兼容绿灯第一次因 `RuntimeFinishReason` 漏导入而出现一个 `NameError`；这是实现
  接线错误，不是合同裁决，补显式导入后 22/22 合同测试通过。
- Task D 首次全量回归误用了当前 Codex/Hermes 的系统 `python`，该解释器没有安装 pytest；
  没有产生测试结果或文件变化。随后按仓库约定显式使用 `.venv\\Scripts\\python.exe`，
  完整得到 `747 passed, 110 subtests passed`。
- Task D 审查时尝试调用未安装的 `ruff`，PowerShell 在执行前明确报 command not found；
  没有代码分析结果。改用 compileall、101 字符行扫描、聚焦/完整 pytest 和 `git diff --check`
  完成现有仓库比例验证，没有为本阶段临时增加依赖。
- 5E-3 设计与状态同步第一次组合 `apply_patch` 假设 `project_decisions.md` 的尾句与实际
  文本完全一致，补丁原子拒绝且无部分修改；先用 `rg` 定位真实上下文，再拆分状态、决策、
  路线矩阵和计划补丁，随后治理检查通过。
- 5P 审计误猜 ADR-0031 文件名为 `0031-agent-runtime-live-stream-delivery.md`；只读失败后改为
  先列真实文件名，并读取 `0031-adopt-in-process-stream-worker-and-parity-contract.md`。
- 5P Prompt 符号搜索第一次因 PowerShell 引号截断正则并报 unclosed group；没有产生文件影响，
  随后改用多个 `rg -F -e` 固定字符串完成检索。
- 6A-6 红灯首次收集因 retention/observability/deletion 模块尚不存在而在 pytest collection 阶段
  产生 4 个 ImportError；这是预期的 TDD 红灯，随后按计划创建三个模块并重新运行聚焦测试。
- 6A-6 composition 初版把 deletion service 直接赋给 lifespan 内局部变量，导致 app 创建时仍是
  `None`；审查发现后改为绑定式 `_TaskDeletionProxy`，并在无 DB/配置失败时 fail closed。
- 6A-6 observability worker 测试首轮 fixture 向 `RuntimeArtifactReference` 传入不存在的 `run_id`
  字段，Worker 正确把执行映射为 failed；修正 fixture 后测试通过，没有放宽生产合同。
- 6A-6 首次 PowerShell 行长扫描使用了带冒号的插值变量表达式，Shell 在执行前报变量解析错误；
  没有文件影响，改用 format 字符串重新运行并通过。
- 6A-7 首次跨 roadmap/amendment/capability/history/decisions 的持久状态补丁假设能力矩阵末尾换行与
  实际文本完全一致，`apply_patch` 原子拒绝且没有部分修改；已先读取真实尾部，再拆成小补丁同步。
- 6A-7 本地 Uvicorn foreground 验证期间，桌面环境对临时端口发出多次无关 root/WebSocket upgrade 探测，
  plain Uvicorn 输出 unsupported-upgrade 与 Windows connection-reset noise；目标 live/ready 实测正确，
  项目当前不实现 WebSocket/SSE，使用 Ctrl-C 正常完成 application shutdown，未据噪声增加无关依赖。
## 2026-08-17：5F-3 Contract / Security / Harness Evaluation

### 当前授权与边界

- [completed] RQ-049 从“执行中”收口为 5F-2 exact-SHA 已执行；新增 RQ-050，清除等待确认状态。
- [completed] 审计 ADR-0034/0035、5F-1/5F-2 证据与 Agent/Compiler/Harness/Runtime 接缝。
- [completed] 用 ADR-0036 和实施计划冻结“评测专用 adapter + 严格 projector”，不接主 Runtime。
- [completed] Batch A：detailed evidence、per-call Usage/finish reason 和安全投影已完成 TDD。
- [completed] Batch B：Pi → existing SkillReviewExecutor/ReviewHarness → typed output 纵向案例通过。
- [completed] Batch C：成功 Signal/Usage/Trace 可投影；Context/terminal/live timing hard gap 已固定。
- [completed] Batch D：形成合同、安全、NFR、维护成本退出矩阵；本地裁决
  `harness-compatible-but-runtime-gate-failed`，5F-4 不准入。
- [completed] 两套 RAG、compileall、Node syntax/tree、Harness/secret/tracked-data、dry-run、governance、
  diff 与最终完整 929/110 subtests 本地门禁通过。
- [completed] 实现/退出提交 `3d9a081` 已由 Actions run `32025522606` 完成 exact-SHA 公共 CI。
- [completed] 5F-3 正式关闭；5F-4 因前置硬门失败未进入；只交接 5F-5 准备状态，不自动执行。

### 冻结的不变量

- 外部 Provider、Riot、Key、held-out I/O 为 0；Scripted/Fake 证据不称为模型质量。
- Pi 文本始终是 draft；只有 ReviewHarness 可以产生 final Artifact 和 publication decision。
- 字符 Context guard 不冒充 token-unit ceiling；无法无损表示的 terminal 不做近似映射。
- 新代码只进入 evaluation namespace 和测试，不修改默认 composition 或生产 Runtime 合同。
