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
| A03 | 模型 Provider 抽象 | 统一 ChatRequest/Response、Registry、能力协商 | 阶段 3 | 真实第二 Provider 在阶段 5 业务场景触发后验收 | 同一领域案例、Tool Calling、结构化输出和错误契约 | 部分完成 |
| A04 | Tool Runtime | Schema、超时、重试、缓存、熔断、fallback、指标 | 阶段 3 | 阶段 7 适配标准 MCP 工具 | 故障注入、缓存、熔断、fallback 和越权测试 | 已完成 |
| A05 | RAG 与证据 | 混合检索、父子块、引用、冲突、拒答、独立保留集 | 阶段 4 | 维护数据集；按规模证据决定是否升级存储 | Recall/MRR/nDCG、abstain、引用支持与冲突测试 | 已完成 |
| A06 | 最小 Agent Loop | Assistant ToolCall、Tool Observation、预算和停止原因 | 阶段 5A | 阶段 5D 接入 Skill，5E 统一 Runtime | Fake Provider + 真实知识工具、重复调用和越权测试 | 已完成 |
| A07 | Skill Contract | `recent-form-review` 与 `single-match-review` 均有 Manifest、SKILL.md、Pydantic I/O、工具白名单和预算 | 阶段 5B 基础 + 5C-5 前第二个真实合同 | 阶段 6 加入 Memory 输入，阶段 7 加入 Meta Skill；真实内部 Skill 出现后才设计调用模式 | 坏 Manifest、Schema、权限漂移、预算和发布边界测试 | 已完成 |
| A08 | Skill Router | 5C-1 至 5C-6 与退出复核均完成；development 23/23、holdout 11/12；selected 决策锁定 Skill name/version；ADR-0010 暂缓 LLM fallback | 阶段 5C | 优先类型化入口/澄清；只有新鲜失败族与结构化输出、质量、成本、故障证据成立才重开模型实验 | 正例、负例、歧义、未支持、误路由、版本快照、拒绝测试、退出复核和 ADR | 已完成 |
| A09 | Prompt/Context Engineering | Harness Prompt V0、SKILL.md 指令；5D-2 已实现 trust-typed Context Builder，5D-3 已实现完整累计消息估算与逐轮 Context 门禁 | 阶段 5D-5E | 5E 加 Prompt 版本/Trace，阶段 6 加 Memory，阶段 7 加 Meta，阶段 8 做 Compaction | Prompt 版本、上下文优先级、Token 预算、回归和消融测试 | 部分完成 |
| A10 | 结构化模型输出 | 5D-6a 已建立 Provider-neutral 合同；5D-6b 隔离微探针在 disabled-thinking 下通过简单/嵌套两类真实 Evaluation JSON，但生产 Adapter 尚未映射 | 阶段 5D | 先做生产 Adapter 离线 TDD 与领域切片；仅在真实阻断时比较一个候选 | 合法、缺字段、额外字段、截断、非 JSON、Schema 漂移、Thinking 预算和修复上限测试 | 部分完成 |
| A11 | AgentRuntime V1 | 5D-1/2 已建立执行与 Context 边界，5D-3 已编译 Manifest 权限/预算并加入有界停止，5D-4 已产生可审计 draft/evidence，5D-5 已通过唯一 ReviewHarness 组合为 typed terminal output | 阶段 5D-5E | 5D-6a/6b/7 补结构化输出、真实 Provider 与领域评测；5E 统一 run/stream/event/trace/usage；阶段 6 持久 Session，阶段 8 取消、快照和恢复 | 统一 run/stream、事件、Trace、Usage 和终止原因 | 部分完成 |
| A12 | 多模型选择与降级 | Provider Registry 已有，任务级选择未实现 | 阶段 5F 或真实业务触发点 | 按质量、能力、成本选择，不按厂商数量堆叠 | 同一评测集、故障降级、成本和延迟对照 | 部分完成 |
| A13 | Session 与长期 Memory | 尚未实现 | 阶段 6 | 玩家画像、复盘情景和训练进度分层 | 用户隔离、写入条件、更正、过期和删除测试 | 已规划 |
| A14 | API 与任务持久化 | CLI 和文件型 Run Store | 阶段 5P 提供早期切片，阶段 6 加 SQL | 阶段 8 扩展恢复与运行治理 | API 契约、幂等、并发、鉴权、隔离和恢复测试 | 已规划 |
| A15 | 标准 MCP 与动态 Meta | 内部 Tool Runtime，不冒充 MCP | 阶段 7 | OP.GG、官方补丁等通过领域 Adapter 分层 | initialize、tools/list、tools/call、断线和版本边界测试 | 已规划 |
| A16 | Multi-Agent 与 DAG | 当前不需要 | 阶段 8 Advanced | 仅在独立上下文、权限和并行收益成立时采用 | Bad Case、对照、消融、成本和 ADR | 按证据采用 |

## 3. 质量、安全与运维能力

| ID | 能力 | 当前基础 | V1 负责阶段 | 后续深化 | 验收证据 | 状态 |
|---|---|---|---|---|---|---|
| Q01 | 端到端 Evaluation | 报告事实评测、RAG 独立保留集、路由开发评测 | 阶段 5C 增加路由 Eval，5D 增加 Prompt Eval | 阶段 8 固定产品回归集和消融 | 数字忠实度、引用、路由、工具选择、建议边界 | 部分完成 |
| Q02 | Trace 与 Observability | Harness Artifact、工具指标、Usage 基础；5D-1 统一安全 run ID 并绑定输入 kind/schema/digest | 阶段 5E | 阶段 8 增加生产日志、告警和前端轨迹 | run_id 串联 Prompt、模型、工具、证据、耗时和决策 | 部分完成 |
| Q03 | Prompt/上下文注入防护 | 工具白名单、Schema、RAG 来源过滤；5D-2 固定 data-only sections，5D-3 约束完整 ToolCall/Tool result 累计预算，5D-4 只从实际成功 ToolExecutionRecord 构造证据并拒绝模型自称来源 | 阶段 5D 建立不可信输入边界 | 5D-7 做模型级攻击评测，阶段 6 覆盖会话，阶段 7 覆盖外部 MCP 内容 | 恶意用户输入、恶意文档、恶意工具结果和越权测试 | 部分完成 |
| Q04 | 应用安全 | `.env` 隔离、日志脱敏、离线赛后合规边界 | 阶段 6 建立鉴权、限流、CORS 与用户隔离 | 阶段 8 部署威胁模型、安全扫描和响应流程 | 密钥扫描、权限、限流、数据越权和依赖审计 | 部分完成 |
| Q05 | 数据生命周期与隐私 | 本地缓存不提交，Memory 尚未落库 | 阶段 6 | 阶段 8 加备份、恢复和公开隐私说明 | 原始比赛、Run、Memory 的保留、更正、导出和删除测试 | 需显式补齐 |
| Q06 | 知识库更新与回滚 | 来源、版本、有效期和冲突策略已有 | 阶段 4 维护任务，公开部署前完成更新流程 | 阶段 8 自动化索引构建、版本切换和回滚 | 新旧版本、失败构建、污染文档和回滚测试 | 需显式补齐 |
| Q07 | 性能、Token 与成本 | Skill 预算、Tool 超时、Token Usage 基础；5D-2 初始 preflight 与 5D-3 完整累计消息门禁/协作式总 deadline 已实现 | 阶段 5E 定义运行预算，阶段 6 定义 API SLO | 5D-6b/7 校准真实 Usage，阶段 8 增加监控和成本告警 | p50/p95、Token、工具次数、模型成本和超预算停止 | 部分完成 |
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
修复一次，第二次失败交回 Harness 降级/拒绝。当前 Zhipu Adapter 仍 text-only，尚未有
生产 Provider SDK 映射尚未实现。最终真实微探针在 P1-P5 全部显式关闭 Thinking 后
5/5 通过并 `admitted=true`；这只准入隔离低层协议，不是生产 Adapter 或领域 Skill
准入。
统一 `run/stream/event/trace/usage` 表面继续属于 5E。

唯一下一步仍为 5D-6b：进入生产 Zhipu Adapter 离线映射 TDD，再做真实 Adapter 与领域
切片。不得提前进入 5D-7，或把微探针准入称为完整 Provider/Skill 准入。
