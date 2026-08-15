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
| A03 | 模型 Provider 抽象 | 统一 ChatRequest/Response、Registry、能力协商；Zhipu/DeepSeek 最小协议有真实证据但领域未准入；V2 `admitted=false`；V3 真实 calibration 第 1 call 未形成规范化响应并首错停止，实际 Usage unknown；不完整证据已公开归档 | 阶段 3 | 零调用决定关闭还是另立新版本诊断；旧/V2/calibration 均不重跑 | 同一领域案例、Tool Calling、结构化输出、错误合同、调用/Token/金额停止与可达性证明 | 部分完成 |
| A04 | Tool Runtime | Schema、超时、重试、缓存、熔断、fallback、指标 | 阶段 3 | 阶段 7 适配标准 MCP 工具 | 故障注入、缓存、熔断、fallback 和越权测试 | 已完成 |
| A05 | RAG 与证据 | 混合检索、父子块、引用、冲突、拒答、独立保留集 | 阶段 4 | 维护数据集；按规模证据决定是否升级存储 | Recall/MRR/nDCG、abstain、引用支持与冲突测试 | 已完成 |
| A06 | 最小 Agent Loop | Assistant ToolCall、Tool Observation、预算和停止原因；多 ToolCall development TDD 已固定整批数量/白名单/重复零副作用预检、顺序执行、ID/Usage/迭代/deadline 语义 | 阶段 5A | 5E 统一 Runtime；真正并发仅由新的延迟 Bad Case 决定 | Fake Provider + 真实知识工具、重复调用、越权、超预算和批次零副作用测试 | 已完成 |
| A07 | Skill Contract | `recent-form-review` 与 `single-match-review` 均有 Manifest、SKILL.md、Pydantic I/O、工具白名单和预算 | 阶段 5B 基础 + 5C-5 前第二个真实合同 | 阶段 6 加入 Memory 输入，阶段 7 加入 Meta Skill；真实内部 Skill 出现后才设计调用模式 | 坏 Manifest、Schema、权限漂移、预算和发布边界测试 | 已完成 |
| A08 | Skill Router | 5C-1 至 5C-6 与退出复核均完成；development 23/23、holdout 11/12；selected 决策锁定 Skill name/version；ADR-0010 暂缓 LLM fallback | 阶段 5C | 优先类型化入口/澄清；只有新鲜失败族与结构化输出、质量、成本、故障证据成立才重开模型实验 | 正例、负例、歧义、未支持、误路由、版本快照、拒绝测试、退出复核和 ADR | 已完成 |
| A09 | Prompt/Context Engineering | Harness Prompt V0、SKILL.md 指令；5D-2 已实现 trust-typed Context Builder，5D-3 已实现逐轮 Context 门禁；5D-7 已冻结双层语义身份、Evaluation 1.1、安全 blocking policy、隔离 held-out 与独立输入计划；V2 首轮真实输入 3241 tokens；ADR-0026 将正常三阶段和可选 repair 的四阶段 development envelope 纳入校准设计 | 阶段 5D-5E | 先离线冻结 baseline/ceiling profile 和 envelope guard，再用真实 Usage 推导 V3；不把 tokenizer-free 长度或 25% 工程余量冒充统计保证；5E 加 Trace | Prompt 版本、上下文优先级、Token 预算、漂移拒绝、用户/RAG 注入、回归和消融测试 | 部分完成 |
| A10 | 结构化模型输出 | 5D-6a 已建立 Provider-neutral 合同；Zhipu 与 DeepSeek V4 Pro 均已真实通过最小协议；V2 Token 门不可达；V3 calibration 首请求 Adapter 规范化失败，未取得四阶段 Usage | 阶段 5D | 结果公开冻结后零调用裁决；不根据宽泛错误猜测原因或重跑 | 合法、缺字段、额外字段、截断、非 JSON、Schema 漂移、Thinking 预算、调用预算、可达性和修复上限测试 | 部分完成 |
| A11 | AgentRuntime V1 | 5D-1/2 已建立执行与 Context 边界，5D-3 已编译 Manifest 权限/预算并加入有界停止，5D-4 已产生可审计 draft/evidence，5D-5 已通过唯一 ReviewHarness 组合为 typed terminal output | 阶段 5D-5E | 5D-6a/6b/7 补结构化输出、真实 Provider 与领域评测；5E 统一 run/stream/event/trace/usage；阶段 6 持久 Session，阶段 8 取消、快照和恢复 | 统一 run/stream、事件、Trace、Usage 和终止原因 | 部分完成 |
| A12 | 多模型选择与降级 | Provider Registry 已有；DeepSeek V4 Pro 独立 Adapter 已通过真实最小协议，但仍只是 5D-7 单一实验候选，尚无领域/产品准入、任务级选择或自动降级 | 5D 完成单候选领域准入；模型分层为 5P 后横向采用门，默认等待阶段 6 真实业务证据 | 按 ADR-0019 比较 Pro-only、Flash-only 与 Flash 默认/Pro 有界升级；5F 只做 Pi/Claude Agent SDK Runtime 采用实验 | 新鲜同任务评测、故障降级、unsafe publication、成本和 p50/p95 延迟对照 | 部分完成 |
| A13 | Session 与长期 Memory | 尚未实现 | 阶段 6 | 玩家画像、复盘情景和训练进度分层 | 用户隔离、写入条件、更正、过期和删除测试 | 已规划 |
| A14 | API 与任务持久化 | CLI 和文件型 Run Store | 阶段 5P 提供早期切片，阶段 6 加 SQL | 阶段 8 扩展恢复与运行治理 | API 契约、幂等、并发、鉴权、隔离和恢复测试 | 已规划 |
| A15 | 标准 MCP 与动态 Meta | 内部 Tool Runtime，不冒充 MCP | 阶段 7 | OP.GG、官方补丁等通过领域 Adapter 分层 | initialize、tools/list、tools/call、断线和版本边界测试 | 已规划 |
| A16 | Multi-Agent 与 DAG | 当前不需要 | 阶段 8 Advanced | 仅在独立上下文、权限和并行收益成立时采用 | Bad Case、对照、消融、成本和 ADR | 按证据采用 |

## 3. 质量、安全与运维能力

| ID | 能力 | 当前基础 | V1 负责阶段 | 后续深化 | 验收证据 | 状态 |
|---|---|---|---|---|---|---|
| Q01 | 端到端 Evaluation | 报告事实评测、RAG/路由评测与 5D-7 分层合同已建立；V2 未测出质量；V3 calibration 也在首个 transport/normalization 失败后停止，质量仍 unknown | 阶段 5C 增加路由 Eval，5D 增加 Prompt Eval | 公开归档 calibration；下一步只做零调用采用决策，阶段 8 固定产品回归集和消融 | 数字忠实度、引用、路由、工具选择、实验身份、注入漏判、失败归因、预算可达性与发布安全 | 部分完成 |
| Q02 | Trace 与 Observability | Harness Artifact、工具指标、Usage 基础；5D-1 统一安全 run ID 并绑定输入 kind/schema/digest | 阶段 5E | 阶段 8 增加生产日志、告警和前端轨迹 | run_id 串联 Prompt、模型、工具、证据、耗时和决策 | 部分完成 |
| Q03 | Prompt/上下文注入防护 | 工具白名单、Schema、data-only sections、累积预算和实际 ToolExecutionRecord 证据；Batch C 已验证一个 Evaluation 漏判后的 unsafe publication；D1-D2 已以 1.1.0 阻断安全 issue；V2 结果不泄漏 marker/Key，但两个真实注入案例因首错停止未执行 | 阶段 5D 建立不可信输入边界 | 先完成预算可达性裁决；只有新鲜门成立时再验证真实模型，阶段 6/7 扩展会话和 MCP 内容 | 恶意用户输入、恶意文档、恶意工具结果、评测漏判和越权测试 | 部分完成 |
| Q04 | 应用安全 | `.env` 隔离、日志脱敏、离线赛后合规边界 | 阶段 6 建立鉴权、限流、CORS 与用户隔离 | 阶段 8 部署威胁模型、安全扫描和响应流程 | 密钥扫描、权限、限流、数据越权和依赖审计 | 部分完成 |
| Q05 | 数据生命周期与隐私 | 本地缓存不提交，Memory 尚未落库 | 阶段 6 | 阶段 8 加备份、恢复和公开隐私说明 | 原始比赛、Run、Memory 的保留、更正、导出和删除测试 | 需显式补齐 |
| Q06 | 知识库更新与回滚 | 来源、版本、有效期和冲突策略已有 | 阶段 4 维护任务，公开部署前完成更新流程 | 阶段 8 自动化索引构建、版本切换和回滚 | 新旧版本、失败构建、污染文档和回滚测试 | 需显式补齐 |
| Q07 | 性能、Token 与成本 | Skill 预算、Tool 超时、Token Usage 基础；5D-2/3 Context 门禁和 D5 实验账本已实现；DeepSeek 协议为 3 calls/1428 tokens；V2 首例为 1 call/3440 tokens；ADR-0025/0026 与双 profile/四阶段离线校准门已公开冻结 | 阶段 5E 定义运行预算，阶段 6 定义 API SLO | 真实 8-call development replay 需单独确认且结果不用于质量；5E 统一 Trace | p50/p95、Token、工具次数、模型成本、预算可达性和超预算停止 | 部分完成 |
| Q08 | 可靠性与故障恢复 | Harness 降级、Tool 重试/熔断、Artifact 哈希 | 阶段 6 增加持久状态和幂等 | 阶段 8 增加取消、租约、检查点、恢复和备份 | 依赖故障、进程中断、重复请求和迟到结果测试 | 部分完成 |
| Q09 | 开源、部署与合规 | MIT、CI、README、SECURITY、匿名化样例 | 横向交付检查点 | 阶段 8 完成产品部署与作品集证据 | Linux/Docker 冒烟、密钥扫描、许可证和公开边界检查 | 部分完成 |
| Q10 | 前端可解释性与可访问性 | 尚无正式产品前端 | 阶段 6 首个 Web 切片 | 阶段 8 展示证据、工具、评测、历史和状态 | 桌面/移动截图、键盘操作、错误态和数据边界展示 | 已规划 |

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

## 8. 当前检查点：阶段 5D 受限 Skill Agent Loop

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
