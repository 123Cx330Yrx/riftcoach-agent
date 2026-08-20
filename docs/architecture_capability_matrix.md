# RiftCoach 架构能力覆盖矩阵

## 1. 用途

本矩阵是阶段 0-8 路线的横向能力总账，不新增主阶段，也不替代 `roadmap.md`。它解决三个问题：

1. 防止某项基础能力只在对话中出现，却没有负责阶段；
2. 区分首个可运行闭环、后续深化和高级候选，避免过早堆叠；
3. 为每项能力指定验收证据，避免用技术名词代替真实实现。

状态含义：

- `已完成`：已有代码和测试证据；
- `部分完成`：已有基础实现，但关键真实场景尚未验收；
- `已规划`：已经明确阶段、边界和完成条件；
- `需显式补齐`：方向曾出现，但此前缺少清晰的 V1 落点或验收项；
- `按证据采用`：不是默认必做，只有 Bad Case 和收益证据成立才引入。

## 2. Agent 核心能力

| ID | 能力 | 当前基础 | V1 负责阶段 | 后续深化 | 验收证据 | 状态 |
|---|---|---|---|---|---|---|
| A01 | LoL 确定性事实 | Riot API、MatchAnalyzer、Schema v1 | 阶段 1 | 阶段 7 增加 Meta，但保持事实分层 | 指标单测、合成样例、Timeline 缺失与短局测试 | 已完成 |
| A02 | 质量门控 Harness | 状态机、Artifact、评测、受限修订、降级 | 阶段 2 | 阶段 8 增加恢复与复杂运行治理 | 状态迁移、错误数字、修订越权、发布门禁测试 | 已完成 |
| A03 | 模型 Provider 抽象 | 统一 ChatRequest/Response、Registry、能力协商；Zhipu/DeepSeek 最小协议有真实证据但领域未准入；DeepSeek V3 calibration 不完整且已由 ADR-0027 关闭；安全错误 provenance 已有离线白名单切片 | 阶段 3 | 5D-7 已以“当前无领域准入”完成采用裁决；G53-0 deferred，旧结果均不重跑 | 同一领域案例、Tool Calling、结构化输出、错误合同、调用/Token/金额停止与可达性证明 | 部分完成 |
| A04 | Tool Runtime | Schema、超时、重试、缓存、熔断、fallback、指标 | 阶段 3 | 阶段 7 适配标准 MCP 工具 | 故障注入、缓存、熔断、fallback 和越权测试 | 已完成 |
| A05 | RAG 与证据 | 混合检索、父子块、引用、冲突、拒答、独立保留集 | 阶段 4 | 维护数据集；按规模证据决定是否升级存储 | Recall/MRR/nDCG、abstain、引用支持与冲突测试 | 已完成 |
| A06 | 最小 Agent Loop | Assistant ToolCall、Tool Observation、预算和停止原因；多 ToolCall development TDD 已固定整批数量/白名单/重复零副作用预检、顺序执行、ID/Usage/迭代/deadline 语义 | 阶段 5A | 5E 统一 Runtime；真正并发仅由新的延迟 Bad Case 决定 | Fake Provider + 真实知识工具、重复调用、越权、超预算和批次零副作用测试 | 已完成 |
| A07 | Skill Contract | `recent-form-review` 与 `single-match-review` 均有 Manifest、SKILL.md、Pydantic I/O、工具白名单和预算 | 阶段 5B 基础 + 5C-5 前第二个真实合同 | 阶段 6 加入 Memory 输入，阶段 7 加入 Meta Skill；真实内部 Skill 出现后才设计调用模式 | 坏 Manifest、Schema、权限漂移、预算和发布边界测试 | 已完成 |
| A08 | Skill Router | 5C-1 至 5C-6 与退出复核均完成；development 23/23、holdout 11/12；selected 决策锁定 Skill name/version；ADR-0010 暂缓 LLM fallback | 阶段 5C | 优先类型化入口/澄清；只有新鲜失败族与结构化输出、质量、成本、故障证据成立才重开模型实验 | 正例、负例、歧义、未支持、误路由、版本快照、拒绝测试、退出复核和 ADR | 已完成 |
| A09 | Prompt/Context Engineering | Harness Prompt V0、SKILL.md 指令；5D 已完成 trust-typed Context/预算与 Evaluation 1.1；5E Trace 有 prompt profile 字段；5P 已用 verified Prompt Program identity、secure factory 和 exit matrix 绑定实际组件 | 5D-5P | 阶段 6-8 再加入 Memory、Meta、Compaction 与隔离上下文 | Prompt 版本、组件摘要、上下文优先级、Token 预算、漂移拒绝、实际 factory 类型、注入、回归和消融测试 | 部分完成 |
| A10 | 结构化模型输出 | 5D-6a 已建立 Provider-neutral 合同；Zhipu 与 DeepSeek V4 Pro 均真实通过最小协议；DeepSeek V3 首请求规范化失败且当前候选已关闭；新实验结果可携带 allowlisted provider error detail | 阶段 5D | G53 按 thinking/structured/tool 新合同隔离审计（API 可用后）；宽泛错误不用于猜根因 | 合法、缺字段、额外字段、截断、非 JSON、Schema 漂移、Thinking 预算、调用预算、可达性和修复上限测试 | 部分完成 |
| A11 | AgentRuntime V1 | 5D 控制链及 5E-1 至 5E-4 均已公开完成；两个真实 Skill 共用同步 `run()`、进程内 `stream()`、typed output、完整 Trace/Usage、安全失败映射与 exit matrix；5F-1 至 5F-5 已完成 Pi 0.84.2 审计/隔离/Harness/采用对照，最终由 `f8dea66/32028206103` 公共裁决产品拒绝 Pi、冻结保留 evaluation-only 资产 | 阶段 5D-5E | 5F-4 因 Context/terminal/live timing 硬门失败未进入；产品继续 Python Runtime；阶段 6 持久 Session，阶段 8 取消、快照和恢复 | 统一 run/stream、事件、Trace、Usage、终止原因、退出审查，以及 Pi batch/Usage/Trace/sidecar 差异矩阵与采用/归档门 | 已完成 |
| A12 | 多模型选择与降级 | Provider Registry 已有；DeepSeek V4 Pro 只通过最小协议，当前 V3 领域候选已关闭；Flash 未测试；尚无领域/产品准入、任务级选择或自动降级 | 5D 完成候选采用决策；GLM-5.2 仅作开发基线；模型分层为 5P 后横向采用门，默认等待阶段 6 真实业务证据；5F Pi-only 不改变模型路由 | G53 deferred；未来仍按 ADR-0019 比较模型分层，5F 只做 Pi Runtime 采用实验 | 新鲜同任务评测、故障降级、unsafe publication、成本和 p50/p95 延迟对照 | 部分完成 |
| A13 | Session 与长期 Memory | RQ-060 至 RQ-067 已冻结 PostgreSQL 单一真源、claimed/observed 关系、固定 subject Conversation、独立异步 Player Link、typed Memory/Candidate gate；entry design、6B-1、6B-2、6B-3 与历史教学/工程证据门均已公共闭环 | 阶段 6 | 6B-4 绑定 Recent Review Identity；Memory Candidate/长期 Memory 在 6B-5 以后；Redis/语义索引只由真实 Bad Case 触发，verified 仅在正式 Auth + 安全 RSO callback + `/accounts/me` PUUID 精确匹配后另行采用 | 无 CN 路由前置拒绝、claimed/observed 权限差异、verified 当前不可创建、两用户/两会话/同 PUUID 隔离、conversation subject 不可变、task 继承、迟到结果、Riot ID 改名/PUUID 重指向、bootstrap 幂等/失败、写入条件与来源、查看/导出、更正、冲突、过期、删除和补偿测试 | 进行中（6B-3 已公共闭环；6B-4/长期 Memory 未实施） |
| A14 | API 与任务持久化 | 5P 与 6A 已公开完成：`adf53e5` / Actions `32146760003` 的 pytest、真库、Linux package 三 job 全绿 | 阶段 5P 提供本地同步切片，阶段 6 加 SQL、异步组合、安全与生命周期 | 阶段 8 扩展 lease、取消、恢复与迟到结果治理 | receipt/path/Schema/SHA/终态交叉校验；PostgreSQL migration、HTTP 幂等、并发 claim、owner 隔离、CORS、删除、性能与 Linux composition smoke | V1 已完成，阶段 8 深化 |
| A15 | 标准 MCP 与动态 Meta | 内部 Tool Runtime，不冒充 MCP | 阶段 7 | OP.GG、官方补丁等通过领域 Adapter 分层 | initialize、tools/list、tools/call、断线和版本边界测试 | 已规划 |
| A16 | Multi-Agent 与 DAG | 当前不需要 | 阶段 8 Advanced | 仅在独立上下文、权限和并行收益成立时采用 | Bad Case、对照、消融、成本和 ADR | 按证据采用 |

## 3. 质量、安全与运维能力

| ID | 能力 | 当前基础 | V1 负责阶段 | 后续深化 | 验收证据 | 状态 |
|---|---|---|---|---|---|---|
| Q01 | 端到端 Evaluation | 报告事实评测、RAG/路由评测与 5D-7 分层合同已建立；DeepSeek V2/V3 均未测出质量，当前候选已关闭且质量 unknown | 阶段 5C 增加路由 Eval，5D 增加 Prompt Eval | G53-0 后按可用性决定；阶段 8 固定产品回归集和消融 | 数字忠实度、引用、路由、工具选择、实验身份、注入漏判、失败归因、预算可达性与发布安全 | 部分完成 |
| Q02 | Trace 与 Observability | 5E-1 至 5E-4 已公开；Runtime 时序、Artifact SHA、双终态、两阶段 Trace 提交、实时事件交付、消费者隔离、parity 与 exit matrix 均有证据 | 阶段 5E | 阶段 6/8 增加持久任务、生产指标与恢复；G53 沿用安全错误合同 | run_id 串联版本、模型、工具、证据、耗时和决策 | 已完成 |
| Q03 | Prompt/上下文注入防护 | 工具白名单、Schema、data-only sections、累积预算和实际 ToolExecutionRecord 证据；旧基线保留 Evaluation 漏判后的 unsafe publication，1.1 已阻断已知安全 issue；两个真实注入案例因首错停止未执行 | 阶段 5D 建立不可信输入边界 | 已知 development 门完成；真实模型验证留给新鲜 Provider 门，阶段 6/7 扩展会话和 MCP 内容 | 恶意用户输入、恶意文档、恶意工具结果、评测漏判和越权测试 | 部分完成 |
| Q04 | 应用安全 | `.env` 隔离、日志脱敏、离线赛后合规；6A-5/6 已公开验证 trusted ActorContext、owner 404、production 缺 Auth fail-closed、默认 CORS、日志/Secret allowlist 与容量错误安全投影；正式 Auth、限流、HTTPS 仍未实现 | 阶段 6 继续以 trusted ActorContext、owner-scoped Repository/复合约束完成 Session/Memory 隔离并保持公网 fail-closed | 阶段 8 建立正式 Auth/HTTPS/限流、部署威胁模型、安全扫描和响应流程 | 密钥扫描、权限、限流、数据越权、CORS、脱敏和依赖审计 | 部分完成 |
| Q05 | 数据生命周期与隐私 | 本地缓存不提交；6A-6 已由 `31d5e60/32138025724` 公开验证原始 cache/task-run/log 7/90/30 天保留、terminal hidden-before-cleanup、active conflict 与失败补偿；Memory 尚未落库，RQ-060 正在设计其独立生命周期 | 阶段 6 实现 task/run 与 Memory 的保留、查看/导出、更正、删除 | 阶段 8 加备份、恢复和公开隐私说明 | 原始比赛、Run、Memory 的保留、更正、导出、删除失败补偿测试 | 部分完成 |
| Q06 | 知识库更新与回滚 | 来源、版本、有效期和冲突策略已有 | 阶段 4 维护任务，公开部署前完成更新流程 | 阶段 8 自动化索引构建、版本切换和回滚 | 新旧版本、失败构建、污染文档和回滚测试 | 需显式补齐 |
| Q07 | 性能、Token 与成本 | 既有 Runtime 预算/实验账本保留；6A-6 在 PostgreSQL 17/Python 3.11 公共环境记录 8 样本 warm create/query p95 `6.220ms` 与 queued→claim p95 `23.359ms`，并验证 owner 3/global 50 可配置背压；这不是 SLA | 阶段 5E 定义运行预算，阶段 6 定义并实测 API SLO | G53 使用独立预算；阶段 6/8 增加真实 p50/p95、队列等待与产品成本趋势 | p50/p95、Token、工具次数、模型成本、背压、预算可达性和超预算停止 | 部分完成 |
| Q08 | 可靠性与故障恢复 | Harness/Tool/Artifact 基础与 6A-1 至 6A-6 已公开；receipt-proven reconciliation、recovery-required、人工 CAS、迟到拒绝、删除补偿与 capacity race 已由真实 PostgreSQL CI 验证；自动 reclaim 仍未实现 | 阶段 6 增加持久状态、幂等、短事务、有证据 reconciliation 与安全生命周期 | 阶段 8 增加取消、lease/heartbeat/fencing、检查点、自动恢复和备份 | DB/Artifact 故障、并发 claim、进程中断、重复请求、人工恢复、删除补偿和迟到结果测试 | 部分完成 |
| Q09 | 开源、部署与合规 | MIT、CI、README、SECURITY、匿名化样例；6A 非 root image/Compose/no-I/O smoke 已公共验证 | 横向交付检查点 | 阶段 8 完成正式 Auth/HTTPS/备份/前端部署与作品集证据 | Linux/Docker 冒烟、密钥扫描、许可证和公开边界检查 | 部分完成 |
| Q10 | 前端可解释性与可访问性 | 尚无正式产品前端；阶段 6 只提供 owner-scoped API/Session 合同 | 阶段 8 首个正式 Web 纵向切片 | 阶段 8 同期深化证据、工具、评测、历史、SSE 和状态展示 | 桌面/移动截图、键盘操作、错误态和数据边界展示 | 已规划 |
| Q11 | 所有者学习与工程证据连续性 | RQ-067 已从阶段 0 重审真实缺口，并建立 `docs/learning/README.md`、八维 `coverage.yaml`、实现后 walkthrough/review、README 入口与治理红灯；成熟阶段直接复用既有设计/退出复核；本轮退出复核见 `docs/plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md` | 所有阶段的横向关闭合同，不新增主阶段 | 每个新 checkpoint 开始时可为 planned，关闭前补齐问题/原理、设计/实现、代码地图、数据/控制流、验证、运行、失败/安全/边界和面试表述 | coverage schema/path/sequence/当前 checkpoint/前序 complete 测试，聚焦与全量回归，独立提交和 exact-SHA CI `63435d9/32308631289` | 已完成（文档门公共闭环） |

## 4. 明确补齐项

以下项目不是新增主阶段，而是进入对应阶段前必须具备的验收项：

1. 阶段 5C：建立路由评测集，覆盖正例、负例、歧义、未支持请求和拒绝原因；
2. 阶段 5D：实现 Prompt/Context Builder V1、结构化输出和不可信上下文边界；
3. 阶段 5E：将 Prompt、Skill、Provider、工具、Token、成本和终止原因写入统一 Trace；
4. 阶段 6：在引入 SQL 与 Memory 前定义数据保留、导出、更正、删除、鉴权和限流；
5. 阶段 7：将 MCP/Meta 返回内容视为外部不可信证据，经过 Adapter、版本和来源校验；
6. 阶段 8 Core：完成知识库更新/回滚、生产安全、备份恢复和完整产品回归。

## 5. 明确不默认采用

以下技术不是基础能力缺口，不能因为流行就自动加入：

- 微调和自训练；
- 多 Agent；
- 通用 DAG 调度器；
- Kubernetes、Kafka、Milvus、Neo4j 等重型基础设施；
- 让模型自由修改长期 Memory；
- 无验收证据的自动模型路由；
- 把本地 Tool Manager 或普通 HTTP 调用称为 MCP。

只有当现有实现出现可复现 Bad Case，候选方案通过质量、成本、延迟和运维对照后，才通过 ADR 采用。

## 6. 阶段检查规则

每个子阶段开始前：

1. 查看本矩阵中由该阶段负责的所有 `已规划` 和 `需显式补齐` 项；
2. 写明本轮实现、不实现、失败模式和验收证据；
3. 确认没有跨过必要前置契约；
4. 确认没有为了技术名词引入当前不需要的基础设施。

每个子阶段结束后：

1. 更新状态和真实测试证据；
2. 未完成项不得因代码存在就标记为完成；
3. 新发现的基础缺口先进入矩阵，再决定阶段归属；
4. 不因新增缺口随意增加或重排 0-8 主阶段。

## 7. 已完成检查点：阶段 5C Skill Router V1

5C 只负责 Skill 选择，不执行 Skill，不调用 Tool，不生成报告。其最小契约应为：

```text
用户请求 + 可用 Skill 元数据
→ 选择一个 Skill，或明确拒绝
→ 返回结构化原因、匹配证据和歧义状态
```

5C V1 优先采用确定性规则，并为未来模型兜底保留接口。只有当真实路由评测证明规则无法覆盖自然表达时，才引入模型路由；模型路由也不能绕过 Skill 输入、权限和质量契约。

5C-1 已经固化上述输入输出边界：`RouterRequest` 只接收用户表达和最小 Skill 路由元数据，`RouterDecision` 只能返回 `selected`、`rejected` 或 `ambiguous`，并强制检查原因码、候选和证据的一致性。当前尚未扫描 `skills/`、尚未匹配用户请求，也不会执行任何 Skill。

5C-2 已建立 `SkillCatalog`：它从本地根目录严格加载可见 Skill 包，遇到坏包立即失败，允许空目录，并生成名称唯一、顺序稳定的不可变快照。它向 Router 只投影最小候选元数据，不把工具权限或任务指令混入路由输入。

5C-3 已加入 Manifest 声明式必需信号组与排除信号，使用统一 Unicode 规范化进行可解释字面匹配，并严格生成三态决策。多个候选同时成立时返回 `ambiguous`，不会按候选顺序擅自打破平局。

5C-4 已独立验收无 Skill、无完整匹配、排除否决和合成多候选歧义，并在决策
合同层禁止带排除证据的匹配候选。`single-match-review` 已作为第二个真实用户
Skill 加入 Catalog，并直接测试近期、单局、混合范围歧义、裸 ID 拒绝和域外边界。
5C-5 的旧 15 个开发/校准案例仍基于旧单 Skill 状态，精确匹配率 `1.0` 和错误
选择率 `0.0` 已原样归档为历史结果；它不是独立保留集，也不能代表当前双 Skill
泛化。双 Skill development v2 已以 23/23 精确匹配接受并冻结当前规则；independent
holdout v1 已按冻结规则单次运行并得到 11/12；唯一设备域假朋友失败原样保留，
未反向调节规则。5C-6 已由 ADR-0010 决定暂缓模型兜底，并定义重新采用门槛。

首批能力分类已经完成源码级复核：近期复盘和单局复盘是两个用户 Skill；事实审查
继续由现有 Harness `EvaluatorStep` 强制调用，不重复包装为 Skill。单局 Skill
Contract 已完成，5C-5 已建立数据生命周期、接受 development 并单次运行 holdout；
5C 退出复核已经通过，并补强命中证据身份不变量、更正 holdout 冻结点 provenance、
记录 5D 前置硬化和框架中立边界。5C 仍然没有执行 Skill、调用 Tool 或调用 LLM；
这些不是遗漏，而是下一检查点 5D 的职责。完整结论见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`。

## 8. 已完成检查点：阶段 5D 受限 Skill Agent Loop

`5D-entry-design` 已完成。ADR-0011 选择如下组合边界：

```text
selected Skill + validated input
→ Context Builder / AgentRunRequest compiler
→ AgentLoop + Skill allowlisted ToolRuntime
→ CoachDraft + KnowledgeEvidence
→ existing ReviewHarness quality gate
→ typed terminal Skill Output
```

5D-1 已完成第一段真实组合切片：统一两个 Skill I/O 文本；selected RouterDecision
锁定 name/version；Manifest、Store 与执行请求共享安全 run ID；
`SkillExecutionBoundary` 从 Catalog 重新核对 Skill、验证 typed input，并比较采用
Harness 真实字节编码的输入 kind/schema/digest。该步骤只产生
`ValidatedSkillExecution`，没有写 Harness Artifact 或执行 Agent。

5D-2 已完成第二段组合切片：两个 Skill 分别构造最小 allowlisted facts；内部 Policy
和 SKILL.md 是 instructional/system，用户、事实和 citation 是 data-only/user；
Manifest ceiling 驱动 required-first 与 optional whole-section 选择。单元攻击测试只
证明信任标签和角色不会被文本提升，不证明模型级 Prompt Injection 已解决。

5D-3 已完成第三段组合切片：`AgentRunCompiler` 只从 Manifest 映射白名单与运行预算，
完整消息 sizer 覆盖 ToolCall/Tool result envelope，AgentLoop 在每次 Provider 调用前
检查累计 Context，并让 Provider/Tool 共用递减的协作式总 deadline。

5D-4 已完成第四段组合切片：`SkillAgentDraftPreparer` 运行上述请求，把最终模型文本
降格为尚未发布的 `CoachDraft`，并只从实际成功、Schema 合法的
`knowledge.search` ToolExecutionRecord 构造共享 `KnowledgeEvidence`。两个真实
Skill 已用 Fake Provider + 真实本地知识工具验证；模型自称来源不会成为证据。

5D-5 已完成第五段组合切片：`ReviewHarness` 只依赖统一 `DraftPreparationStep`，旧
Retriever/Generator 由顺序 Adapter 兼容；`SkillReviewExecutor` 把 Agent 草稿/证据
交给同一 Evaluator、受限修订和发布/降级/拒绝状态机。typed terminal output 只从
terminal Manifest、最终 Artifact、最终 attempt Evaluation、实际 Evidence 与输入
commitment 构造，并再次通过 Skill 声明的 Pydantic Output Model。

因此 A09、A11、Q03 与 Q07 继续是部分完成；A10、Q01 的关键真实场景仍未验收。
Provider-neutral 结构化响应、真实 Provider Tool Calling 和 Prompt E2E Evaluation
5D-6a 已补齐 provider-neutral 结构化响应合同：`ChatRequest` 声明冻结 JSON Schema，
Capability Negotiation 因此要求 `STRUCTURED_OUTPUT`；Evaluation Adapter 用同一
Pydantic 模型生成 Schema 并严格验证结果，非 JSON、fence、截断和 Schema 错误最多
修复一次，第二次失败交回 Harness 降级/拒绝。最终真实微探针在 P1-P5 全部显式关闭
Thinking 后 5/5 通过并 `admitted=true`；生产 Zhipu Adapter 随后已用离线 TDD 映射
四类消息、JSON mode、Tool Calling、可逆工具别名和严格坏响应边界。精确 3-call
`AdapterProtocolSliceRunner` 又用共享预算 Provider 组合严格 structured request、现有
AgentLoop 和固定只读 `knowledge.search`；在公开 CI 成功 SHA `f1d171d` 上真实执行后，
A1/A2 都 passed 且 `admitted=true`。这准入最小生产 Adapter 协议，不准入领域 Skill。
统一 `run/stream/event/trace/usage` 表面继续属于 5E。

近期复盘 Skill/Harness 控制器已把累计 7-call 与历史 3 calls 对齐；真实运行随后只使用
一个领域 call，但没有统一响应进入 Agent，也没有工具证据或 Evaluation，Harness 安全
降级。ADR-0012 因此准入最小 Adapter 协议、拒绝 GLM recent-form 领域能力并收尾
5D-6b。5D-7 Batch A/B 已建立分层合同与 Prompt/Context 身份；Batch C 又让 7 个
development 场景在零外部调用下真实经过 Skill/Agent/Tool/RAG/Harness，覆盖工具、事实、
引用、用户/RAG 注入和 Evaluation 漏判。Batch D 的 D1-D2 已接入版本化安全评测与不可
修订 blocking policy，D3 已创建 3 场隔离 held-out 但未运行；D4 已由 ADR-0018 将
唯一有界候选更正为 DeepSeek V4 Pro，并冻结成本/停止规则。D5 已完成离线 Adapter、
错误归因、控制器和 no-I/O 入口；真实最小协议随后以 3/3 calls 准入。真实领域 held-out
只执行一次并在首例因 `unsupported_parallel_tool_calls` 未准入；结果安全降级且当前
考卷不可重跑。ADR-0022 已以 development TDD 和公开 CI 采用严格解码、整批原子预检
与顺序消费；ADR-0024 又完成新鲜领域采用门设计。下一步只用 development 假数据实现
兼容合同、历史证据链和 no-I/O admission 的工作已经完成并公开冻结，新考卷也已随后
公开冻结；Fresh-Gate 4 又在本地完成 V2 readmission、prepare-only、Fresh result envelope
与生产 CLI 组合，并由 `ed3cc94` / Actions `31863341338` 公开验证，同 SHA no-I/O
prepare-only 已通过；这些运行前证据不能把低层协议、Fake Provider 或离线修复当成真实
模型报告质量。

V2 随后经用户明确确认只执行一次。首例第一次调用得到 1 个规范化响应并使用 3440
observed tokens；下一请求预留 1024 output 后会超过单例 4000-token 门，因此在 I/O 前
停止。Harness 安全降级、后两例 skipped、最终 `admitted=false`。结果不可重跑；当前
5D-7 的缺口已经从“等待真实确认”变为“用真实 Context/Usage 证明多轮控制流预算可达，
再决定关闭候选或建立全新 V3 门”。

## 9. 已完成检查点：阶段 5E AgentRuntime V1

5E 入口设计与 ADR-0029 已完成，选择薄 Runtime + 可选观察端口：复用 5D 的 Boundary、
Context、AgentLoop、ToolRuntime 与唯一 ReviewHarness，底层只发类型化安全 Signal，中央
Recorder 统一 sequence、时钟、Event、Usage 和最终 Trace。外层事后包装因无法提供真实
stream 被拒绝；事件溯源/DAG/第三方框架因会提前承担恢复和并发复杂度而留到后续证据门。

V1 必须区分 Runtime 自身状态与 Harness publication 状态，并把已发送但未观察到
Provider Usage 的调用写成 partial/unknown 和 null，而不是默认零。Trace 只保存版本、
policy provenance、安全事件、终止原因及 Artifact 引用/哈希，不保存 Prompt、正文、
Tool data、原始异常、request ID 或秘密。

5E 固定为四个内部检查点：5E-1 合同/Usage/Trace Store、5E-2 observable `run()`、
5E-3 live `stream()` parity、5E-4 evaluation/exit review。5E-1 已由 `d891184` / Actions
`31942483874` 完成 exact-SHA 公开验证；5E-2 的 Task A-D 已由 `d49508e` / Actions
`31959646589` 公开完成共享 Observed Provider、定点 Agent/Harness observer、Event/Trace 1.1、
missing Usage、selected-only request、统一同步 `run()` 与两阶段 terminal commit，并通过
`747 passed, 110 subtests passed`。5E-3 已由 `80b76a1` / Actions `31960987333` 公开完成
进程内 `stream()`、背压、关闭隔离和 run/stream parity；5E-4 的 exit matrix 与
`close-with-deferred-boundaries` 退出结论已由 `3d36561` / Actions `31962252231` 完成
exact-SHA 公共验证。整个 5E 正式完成。RQ-040 已恢复 `5P-entry-design`；ADR-0032/0033 已
设计 Prompt Program V1 与薄产品 API/Application Service，并由 `49841ec` / Actions
`31985199623` exact-SHA 公开验证；5P-1 产品合同/compiler 已由 `57bd36a` / Actions
`31987501935` 完成 exact-SHA 公共验证；5P-2 Prompt Program/composition 又由 `0a9651f` / Actions
`31988837293` 完成 exact-SHA 公共验证。5P-3 Domain/Application Service 又由 `4bd5c83` /
Actions `31998739178` 完成 exact-SHA 公共验证；5P-4 receipt/query 又由 `932a863` / Actions
`32002994441` 完成 exact-SHA 公共验证。5P-5 FastAPI 薄 Adapter 又由 `6d1e5b0` / Actions
`32005648179` 完成 exact-SHA 公共验证，24 项 API 聚焦与 `884 passed, 110 subtests passed`
已公开通过；Provider I/O 仍为 0，完整生产 API/部署仍属后续阶段。5P-6 已在本地用原设计十项
功能、分层/NFR、安全/资源和 deferred/unknown matrix 复核全链，裁决为
`close-with-deferred-boundaries`；`8c8acc6` / Actions `32010604551` 已完成退出审查 exact-SHA
公共闭环，整个 5P 正式完成并只交接到 `5F-entry-design` 准备状态。
5F、阶段 6/8 的 SDK 对照、SQL/Session/Memory/SSE、持久事件、
cancel/resume、DAG 和 Multi-Agent 边界不变。

### 2026-08-18：6A-6 安全/生命周期/NFR 公共证据

6A-6 已由 `31d5e60` / Actions `32138025724` 完成公共真库验证：CORS 默认关闭与
wildcard+credentials 拒绝、allowlisted body-free logs/metrics、7/90/30 天 injected-clock
retention、terminal hidden-before-cleanup 与补偿 marker、active delete conflict、owner/global
capacity race 以及 PostgreSQL lifecycle/performance 均有测试。完整 pytest 为 `1077 passed,
27 skipped, 1 warning, 110 subtests passed`，真库为 `51 passed`；8 样本 create/query 与
queued→claim p95 分别为 `6.220ms`/`23.359ms`。Q04/Q05/Q07/Q08 仍是“部分完成”，因为正式
Auth、Memory lifecycle、SLA、自动 reclaim 和公网部署尚未完成。

### 2026-08-18：6A-7 Packaging/Exit 开始

RQ-059 已授权 A14/Q09 的当前增量：可重建 API+Worker+PostgreSQL package、claim 前完整配置
fail-closed、Linux no-I/O smoke 与逐条 6A exit matrix。该实施不改变 A13 Session/Memory 未实现、
Q04 正式 Auth/HTTPS 未实现，也不提前采用 MCP、Multi-Agent、LangGraph 或新 SDK。

本地实现与完整门禁已通过；smoke 使用隔离 Compose project/data volumes，并把 API stack readiness 与
one-off 诊断进程分开。A14/Q09 仍保持“部分完成”，直到同一提交的 Linux packaging-smoke 与真库 job
公开成功；这也不改变 Session/Memory、Auth/HTTPS 和公网部署仍未实现。

首个 run `32145005904` 已把缺口收窄到 one-off smoke：pytest/真库/image build/migration/API ready 成功，
smoke 失败。A14/Q09 继续“部分完成”；当前仅增加允许列表 stage diagnostics，不以日志正文换取可观测性。

第二个 run `32146113582` 已安全定位到 Alembic import-root，而非 DB 故障；两条容器脚本入口现统一为
module execution。新 exact-SHA Linux job 成功前，A14/Q09 仍不能升级状态。

修复提交 `adf53e5` / Actions `32146760003` 已让 pytest、PostgreSQL 与 packaging-smoke 全绿；A14 的
阶段 6 V1 task/API/package 落点完成。Q09 仍为部分完成，因为正式公网 Auth/HTTPS、备份、前端和运维
不属于 6A，也尚无部署证据。

### 2026-08-20：6B-3 实现公共能力状态

- `Conversation identity binding`：本地 domain/Service/Repository/HTTP 已实现固定
  owner/relationship/subject/role，active 行锁、scoped idempotency 与复合 FK/trigger 已接线。
- `Ordered Message control plane`：本地实现公共 user append、1-based row-lock sequence、archive/hidden、
  有界查询与 assistant provenance schema；公共 assistant terminal 仍未开放。
- `Conversation/Message PostgreSQL evidence`：migration、trigger、回滚和双 writer/生命周期确定性并发测试
  已写入阻塞 job；`7e4f233` / Actions `32329686381` 的真实 PostgreSQL job 已通过（`100 passed`）。
- `Agent/Review/Memory integration`：明确 deferred 到后续 6B 批次，不能把本设计稿写成已接入。
