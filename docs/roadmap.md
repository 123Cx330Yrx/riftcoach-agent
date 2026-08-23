# RiftCoach 主路线 v1.1（阶段 0—8）

本路线是项目唯一主阶段编号，共九个阶段。阶段内部可以继续迭代 `Harness v1.1`、`RAG v1.2` 等小版本，但不再增加、删除或重排主阶段。若必须改变主阶段职责，需先新增 ADR，说明证据、备选方案和迁移影响。

## 不变的总体策略

- 保留当前独立 `riftcoach-agent` 仓库和已经实现的 LoL 领域核心；
- 不删除现有代码后改用 EchoMind，也不把 AGI-Saber 或 Sea 整体套进来；
- EchoMind 是应用层迁移来源，重点吸收 Provider、Tool Runtime、Session、Memory、Monitor 与 Evaluation；
- AGI-Saber 是知识检索和复杂运行时参考，后期选择性吸收父子块、混合检索、DAG、取消与快照思想；
- Sea-Mult-Agent 是可靠执行参考，重点吸收 Artifact 契约、确定性控制面、预算、审批、租约和迟到结果隔离思想；
- 所有外部能力都必须经过本项目接口重构、测试和 ADR 记录，不能通过复制名称制造技术亮点。

## 九阶段总览

| 阶段 | 名称 | 核心问题 | 主要来源 | 当前状态 |
|---:|---|---|---|---|
| 0 | 基线与证据建档 | 我们已经有什么，参考项目真实实现了什么 | 自主审计 | 已完成 |
| 1 | 领域核心 v1 | 能否稳定产生可信、版本化的 LoL 事实 | RiftCoach 自主实现 | 已完成，进入维护 |
| 2 | Harness v1 | 一次报告运行如何被控制、追踪、评测和发布 | 现有质量闭环 + Sea 可靠执行思想 | 已完成，进入维护 |
| 3 | Provider 与 Tool Runtime | 外部模型和工具如何统一、可靠地调用 | EchoMind 迁移重构 | 已完成，进入维护 |
| 4 | RAG v1 | 检索知识如何可引用、可评测、可替换 | 当前轻量 RAG + Saber 检索思想 | 已完成，进入维护 |
| 5 | Skill 系统与路由 | 如何把复盘能力封装成可复用、受约束的工作流 | 自主设计，参考 Agent Skills 思想 | 已完成，进入维护 |
| 6 | API、Session 与 Memory | 如何从脚本变成真正的长期个性化 Coach | 自主实现，选择性吸收 EchoMind Session/Memory 思想 | 已完成；6B-1 至 6B-9 与 RQ-067 前置门均已 exact-SHA 公共闭环，6B-9 为 `cbc7cbd` / Actions `32408101770` |
| 7 | 标准 MCP 与动态 Meta | 如何标准化连接 OP.GG，并向外暴露能力 | 标准 MCP | 已完成；7-5 实现 `a88fbc4/32483521108`、clean-SHA 双向门与 evidence `fac6fe0/32484257736` 完成最终公共闭环 |
| 8 | Multi-Agent、可靠运行时与产品化 | 复杂任务何时并行、恢复、观察和交付 | Saber + Sea 选择性吸收 | 进行中；entry design、8A、8B、8C 与 8D 已公共闭环，ADR-0053 reject 产品 Multi-Agent；当前进行 8E preflight（真实验证与玩家档案合同） |

## 横向能力总账

阶段 0-8 负责纵向实施顺序，[架构能力覆盖矩阵](architecture_capability_matrix.md)负责检查跨阶段基础能力是否具有明确的 V1 落点、后续深化、失败模式和验收证据。

每个子阶段开始前必须核对矩阵；结束后必须以真实代码、测试或实验更新状态。新发现的基础缺口先进入矩阵，再归入现有阶段，不依赖对话记忆，也不因新增技术名词随意增加或重排主阶段。

---

## 阶段 0：基线与证据建档

### 原理

先区分“项目文档声称”“源码已经实现”“测试能够验证”三种证据强度，再决定复用范围，避免因为名词丰富就更换底座。

### 已完成

- 建立干净 Git 基线、README、ADR 和测试入口；
- 对 EchoMind、AGI-Saber Python/Go、Sea-Mult-Agent 及社区资料进行源码/文档对照；
- 确认内部 Tool Manager 不等于标准 MCP；
- 确认 RiftCoach 保持独立仓库，不走换皮路线；
- 确认轻量基础设施优先，复杂组件按需求引入。

### 完成标准

- 架构决策可追踪；
- 参考能力有来源和边界；
- 主仓库测试可重复运行。

## 阶段 1：领域核心 v1

### 原理

Agent 的可信上限首先由事实层决定。LLM 不负责计算比赛事实，只负责解释经过 Schema 约束的确定性数据。

### 已完成

- Riot ID、Match Detail、Timeline 数据链路；
- Data Dragon 中文静态映射；
- MatchAnalyzer 指标计算与短局排除；
- Timeline 缺失显式状态；
- `Player Summary Schema v1.0`；
- 中文确定性报告、GLM Coach 草稿；
- 轻量 RAG v0.1 与事实评测/受限修订脚本原型。

### 为什么当时的轻量 RAG 不代表阶段 4 已完成

它当时只是提前验证“知识检索能否改善报告”的业务实验，尚缺来源元数据、稳定引用、混合召回、重排、检索评测和 Provider 抽象。这些能力现已在阶段 4 补齐；该段保留用于说明为什么没有在阶段 1 提前堆叠 RAG。

### 完成标准

- 同一输入能稳定生成兼容 Schema 的事实产物；
- 缺失数据和排除样本不会被伪装成零；
- 领域测试持续通过。

## 阶段 2：Harness v1

### 原理

Harness 是控制一次 Agent 运行生命周期的确定性运行层，不是另一个模型。它负责状态、预算、证据、评测、修订和发布决定。

### 已完成

- 将现有分散脚本统一成一个运行入口；
- 建立 `run_id` 和明确状态机：事实收集、检索、生成、评测、修订、再评测、发布/拒绝/降级；
- 为每个阶段保存版本化 Artifact 清单，而不是靠隐式文件名传递；
- 设置最大修订次数、发布阈值、失败降级与幂等规则；
- 记录模型、Prompt、检索证据、评测结果、耗时和最终决策；
- 测试错误数字、过度因果、评测失败、修订越权和重复运行。

### 从 Sea 吸收什么

- Artifact 驱动协作；
- 模型负责建议、代码负责约束；
- 明确预算和终态；
- 迟到或过期结果不得覆盖当前运行。

本阶段不引入 Sea 的 Go Scheduler、Docker Sandbox 或完整 DAG，只吸收适用于单条报告链路的可靠性原则。

### 完成标准

- 一条命令可以完成整个质量闭环；
- 每次运行可重放、可解释、可审计；
- 失败时只发布确定性报告或明确拒绝，不发布未通过草稿。

## 阶段 3：Provider 与 Tool Runtime

### 原理

Provider 隔离厂商差异；Tool Runtime 统一工具契约和可靠性。它们解决“如何可靠调用”，而不是“调用后如何编排”。

### 已完成

- 抽象 `LLMProvider`，首个实现为智谱 GLM；
- 把 Riot、Data Dragon、RAG 和 LLM 包装为类型明确的工具；
- 参数/返回 Schema 校验；
- 超时、有限重试、缓存、熔断、fallback 和指标；
- 敏感配置与日志脱敏；
- 为各 Provider 编写契约测试和故障测试。

### 从 EchoMind 迁移什么

- 工具注册、参数校验、超时、缓存、熔断和 fallback 思想；
- Monitor 指标思想。

会重写接口并补测试，不复制 `MCPToolManager` 名称，也不把它称为 MCP。

### 完成标准

- 业务代码不直接依赖具体 LLM SDK；
- 工具故障不会让整条链路无边界挂起；
- Provider 可通过契约测试替换。

### 同厂商模型迁移边界（当前不执行）

GLM-5.2 和 GLM-5.3 共享 Zhipu Provider 接口，但不共享所有请求语义。官方 GLM-5.3
要求始终启用 thinking，因此模型升级必须先通过独立的 profile/Adapter 合同测试，
再通过真实协议和领域采用门。模型切换不等于自动路由，也不等于 Multi-Agent。

5D-7 已在没有领域 Provider 准入的情况下完成评测门审查；这不修改默认 GLM，也不把
DeepSeek 结果混入产品能力。GLM-5.3 普通 API 可用后按 ADR-0023 的 G53-0 至 G53-4
顺序隔离推进；通过新鲜领域门前，GLM-5.2 只作为开发基线，历史证据和确定性 fallback
保持有效。

## 阶段 4：RAG v1

### 原理

RAG 的目标不是“有向量数据库”，而是让知识召回具有来源、适用版本和可测质量。先建立检索评测，再决定是否需要更重基础设施。

### 实施内容

- 文档来源、版本、适用位置、知识类型和更新时间元数据；
- 父子块或等价的上下文回填；
- 本地全文/BM25 与 Embedding 混合召回；
- 去重、RRF/加权融合、可选重排；
- 报告中的证据引用和冲突/过期处理；
- 固定检索评测集：Recall@K、MRR/nDCG、引用正确率和无答案拒答；
- `KnowledgeProvider` 接口，为未来替换存储做准备。

### 从 Saber 吸收什么

- 父子块、查询改写、多查询、混合检索、RRF 和重排思想；
- 不直接部署 PostgreSQL + Elasticsearch + Milvus + Neo4j 全家桶。

### 完成标准

- 每个知识性结论能追踪来源；
- 检索升级以评测结果而非主观观感为依据；
- RAG 不可用时 Harness 能明确降级。

## 阶段 5：Skill 系统与路由

### 原理

Skill 是可复用且受约束的工作流包，不只是 Prompt 文本。它定义触发条件、输入、允许工具、步骤、输出 Schema、成功标准和禁止行为。

### 首批 Skills

- 近期状态复盘；
- 单局复盘。

报告事实审查仍是所有 Coach 报告的强制能力，但它已经由阶段 2 的
`EvaluatorStep + ReviewHarness` 实现，不重复包装成第三个 Skill。未来只有出现
独立输入、工具、预算和复用场景时，才重新评估审查 Skill。

### 实施内容

- Skill 清单与版本；
- 确定性路由优先；只有真实 Bad Case 和评测证明收益时才采用模型兜底；
- 工具白名单和上下文预算；
- 输出 Schema 和验收规则；
- Skill 选择准确率与越权测试。

### 完成标准

- 每个 Skill 可以独立解释“为什么触发、调用了什么、怎样算成功”；
- Skill 不能任意获得所有工具权限；
- 新增 Skill 不需要修改领域核心。

## 阶段 6：API、Session 与 Memory

### 原理

RAG 保存外部知识；Memory 保存玩家相关且可更新的长期状态；原始比赛事实仍保存为结构化数据，三者不能混在同一个向量库里。

### 实施内容

- 5P 已先建立仅本地、同步、无鉴权的近期复盘 HTTP 切片；本阶段负责把它扩展为完整
  FastAPI 产品入口，而不是把 5P 的 Fake/fixture 切片误称为生产 API；
- 6A-1 至 6A-7 已公开建立 PostgreSQL task、原子 claim、Application/Artifact 接线、异步 HTTP、
  CORS/脱敏、背压、生命周期删除、真实性能边界和 Linux package；`adf53e5` / Actions `32146760003`
  修复并验证 direct-script/wheel 的 Alembic import-root，6A 正式完成；状态收尾 `d1cc2ed` /
  Actions `32147545753` 也已三 job 全绿；RQ-064 已本地冻结异步 Player Link、typed Memory/Candidate gate
  和 6B-1 至 6B-9 顺序；设计提交 `bc11afe` / Actions `32222531783` 三 job 已公共成功，6B-1 又由
  `ed8fa58` / Actions `32229024069` 三 job 公共闭环；RQ-066 随后只授权 6B-2，其 Resolver、Worker、
  owner-scoped Link API 与 Linux no-I/O package 已由 `0c13a58` / Actions `32301852042` 三 job 公共闭环；
  RQ-067 已完成历史教学/工程证据补齐、治理、提交与 exact-SHA 公共闭环；Conversation/Message
  foundation 又由 `7e4f233` / Actions `32329686381` 完成真实 PostgreSQL concurrency/trigger 与 Linux
  package 公共闭环；RQ-068 授权的 6B-4 Conversation-bound Review Identity 已由 `d63f908` /
  Actions `32347834279` 完成 exact-SHA PostgreSQL/Linux package 公共闭环；RQ-069 的 6B-5 Candidate gate
  与事务内 typed materializer 接缝又由 `dd7c9c8` / Actions `32376405150` 完成真库/Linux 公共闭环；
  6B-6 typed target 又由 `5531c81` / Actions `32387026797` 完成 pytest、真实 PostgreSQL 和 Linux
  package 公共闭环；6B-7 Training Plan/Progress 又由 `f6d8922` / Actions `32397290175` 完成真库/Linux
  package 公共闭环；当前进入 6B-8 Memory-aware Context/typed turns；这不等于正式 Auth、生命周期或公网部署已完成；
- FastAPI 对话和复盘入口；
- `user_id`、`conversation_id` 和权限边界；
- 外服 Riot 账号关系：官方 routing 没有中国大陆 CN；公开查询只形成以 PUUID 为稳定身份的
  `player_subject` 引用，Riot ID 只是可变显示别名；用户自我认领在正式产品 Auth、安全 RSO callback
  与精确 PUUID match 前保持未验证，不能把 Riot ID→PUUID 冒充为账号归属证明；
- MVP 同时支持未验证 self claim 与受限 public observation：前者可建立 owner-player 训练目标/计划/进度，
  后者只保存公开比赛分析和 owner-local 观察备注/趋势；两者均不增加 Riot 数据权限；
- Conversation 创建时固定 trusted owner 的一个 player subject，V1 不在同一会话中切换；消息、Context、
  task/run 和 Memory Candidate 继承该绑定，不同 PUUID 必须新建 conversation；
- 会话工作记忆；
- 玩家画像、复盘情景、训练计划与训练进度；
- 记忆写入条件、合并、过期、更正和删除；
- 防止模型将未经确认的推断写入长期记忆；
- 会话与记忆隔离测试。

### 从 EchoMind 迁移什么

- 用户/会话分层、工作记忆、情景记忆、画像更新和 API 主链思想；
- 修正其画像无可靠时间排序、跨会话合并不足和模型厂商耦合问题。

### 完成标准

- 两个用户和两个会话的数据严格隔离；
- 用户可以查看、更正和删除记忆；
- Coach 能基于历史训练目标比较进展，但不会把猜测永久化。
- 同一 PUUID 在不同 owner 下不得共享关系状态、私人 Session 或 Memory；Riot ID 改名不应新建玩家档案，
  同一显示 Riot ID 若解析为不同 PUUID 则不得静默重绑。
- public-observed 报告不得冒充被观察者本人偏好或第一人称训练完成度；verified-self 在正式 Auth + RSO +
  PUUID match 实现前必须不可创建。
- 客户端或模型不能覆盖 conversation subject；相同 PUUID 改名可继续，不同 PUUID 和跨 owner 必须由应用
  与 PostgreSQL 约束拒绝。

## 阶段 7：标准 MCP 与动态 Meta

### 原理

MCP 负责跨系统标准互操作，内部 Tool Runtime 负责本应用可靠执行，两者职责不同。

### 实施内容

- 标准 MCP Client：初始化、工具发现、工具调用、会话/传输和错误处理；
- 接入 OP.GG 等版本 Meta 数据，并记录数据时间和来源；
- 玩家事实、静态映射、RAG 知识和动态 Meta 分层；
- RiftCoach MCP Server：对外暴露近期汇总、单局分析、知识搜索和报告评测；
- 协议互操作与断线/超时测试。

Stage 7 的内部检查点顺序固定为：入口设计 → `7-1-mcp-client-contract` →
`7-2-mcp-transport-and-discovery` → `7-3-opgg-meta-adapter` →
`7-4-riftcoach-mcp-server` → `7-5-mcp-interoperability-exit-review`。
每一项都必须独立教学、TDD、八维证据、本地门禁、提交和 exact-SHA 公共 CI。7-3
允许对获准 OP.GG Server 做一次有界、body-free 的单向产品 smoke；7-5 才执行“外部
Server 被 RiftCoach 调用 + 外部 Client 调用 RiftCoach Server”的双向互操作退出证明。

当前状态：入口设计、7-1 pure contract、7-2 transport/discovery 与 7-3 OP.GG Meta Adapter 已公共闭环；
7-3 的 `64311a1` / Actions `32455219404` 证明官方 Streamable HTTP、partial MetaEvidence、严格
lane-meta Adapter、data-only Context 和一次真实 body-free 单向产品 smoke。当前唯一检查点
`7-4-riftcoach-mcp-server` 已由 `431c584` / Actions `32480827952` 完成 strict Server/Facade、
fixture TDD 与 exact-SHA 三 job 公共闭环。唯一下一检查点 `7-5-mcp-interoperability-exit-review`
已由 RQ-079 授权：锁版官方 TypeScript MCP SDK Client 经标准 stdio 调用 RiftCoach Server，另一方向
复用产品 OP.GG Streamable HTTP Client。实现 `a88fbc4` / Actions `32483521108` 三 job 与同一 clean SHA
的双向真实门均已通过并生成 body-free evidence；证据提交 `fac6fe0` / Actions `32484257736` 又完成
exact-SHA 三 job，7-5 coverage 与 Stage 7 已正式关闭。

### 完成标准

- 能与至少一个外部标准 MCP Server 完成真实互操作；
- 能被至少一个外部 MCP Client 调用；
- 不把普通 HTTP POST 适配器称为 MCP。

## 阶段 8：Multi-Agent、可靠运行时与产品化

Stage 8 entry design、8A、8B 与 8C 已完成 exact-SHA 公共闭环；8B 唯一 holdout 由 ADR-0053 拒绝产品
Multi-Agent。8C 已由 clean implementation `2df5349/32587659678` 验证 PostgreSQL durable task event、
lease/fencing、cancel、checkpoint、receipt-proven recovery、Worker/API/package 纵向与八维材料；8D 又由
`a274b7f/32598480400` 完成 Riot/Data Dragon/official patch/OP.GG partial typed EvidenceBundle 公共闭环。
当前唯一检查点为 `8e-productization`，已进入 preflight；这不表示 DAG、SSE、正式 Auth、前端、
备份、8F 或生产部署已经完成。

### 原理

只有当任务出现可以独立并行的上下文、权限和失败边界时才拆 Agent。Multi-Agent 是隔离职责和并发的手段，不是项目完成度标签。

### 实施内容

Stage 8 入口设计冻结为以下双轨顺序：

```text
entry design
  → 8A advanced-adoption-gate
  → 8B conditional-multi-agent-experiment
  → 8C reliable-runtime-core
  → 8D riot-opgg-evidence-fusion-core
  → 8E productization
  → 8F final-evaluation-and-portfolio
```

- `8-Core`：可靠运行时、Riot + OP.GG typed evidence fusion、正式 Web 产品、安全/隐私/备份、完整回归与作品集交付；
- `8-Advanced`：至少一个有 Bad Case、对照、消融、成本和 ADR 的高级能力采用实验；
- Knowledge、Meta、Coach、Review 只有在 8A/8B 证明独立上下文、权限和失败边界有收益时才拆成多 Agent；
- Artifact 契约、DAG、并行、取消、超时、检查点、恢复、租约和迟到结果隔离按对应 checkpoint 逐项实施，DAG 不预先强制；
- LoL 专用前端、SSE/事件流、Trace、成本与延迟监控、部署、安全和作品集材料由 8E/8F 完成。

### 从 Saber 与 Sea 吸收什么

- Saber：任务图、并行节点、取消、快照、上下文装配；
- Sea：显式 Artifact、Ready 条件、预算、审批、租约、事件历史和确定性验证；
- 不把科研沙箱、论文复现、重型知识图谱等无关模块搬进 RiftCoach。

### 完成标准

- 多 Agent 相比阶段 7 的单工作流在质量、延迟或故障隔离上有测得收益；
- 中断后可在安全边界内恢复；
- 前端可以展示证据、工具调用、评测与发布状态；
- 简历中的每项能力都有源码、测试或实验记录支持。

---

## 当前执行位置

本路线只定义阶段职责和顺序，不再保存容易过期的“唯一下一步”。当前主阶段、
子阶段、已有证据、限制和唯一下一步统一见
[`project_execution_state.md`](project_execution_state.md)。路线为何发生过调整、哪些
旧方案已废止，见 [`roadmap_change_history.md`](roadmap_change_history.md)。

任何实现批次、测试通过或对话摘要都不能绕过当前状态文件列出的未完成检查点。

## 贯穿主路线的交付检查点

部署与开源不是额外主阶段，也不改变阶段 0—8 的顺序。它们作为横向检查点，在能力达到最小可交付条件时触发：

1. **GitHub 开源基线**：阶段 2 期间完成许可证、敏感信息检查、README、CI 和匿名化示例；
2. **静态展示页**：域名备案完成后可以先发布项目介绍、架构、示例报告和 GitHub 链接，不冒充完整产品；
3. **部署冒烟测试**：阶段 3 后可用 Docker 部署最小健康检查，验证 Linux、环境变量和日志；
4. **首个 Web 纵向切片**：阶段 6 完成后部署“输入 Riot ID → FastAPI → 对局摘要 → 页面展示”；
5. **完整展示版**：阶段 8 增加 SSE、运行轨迹、历史复盘、监控、备份和恢复。

云服务器在首个可部署切片前保持轻量和待命，不提前安装与当前阶段无关的数据库、向量库或通用 Agent 平台。

## 每个阶段的教学交付要求

进入任何阶段时，必须先说明：

1. 要解决的真实问题；
2. 底层原理与关键概念；
3. 为什么现在做、为什么不提前做后续能力；
4. 目录、接口和数据如何流动；
5. 测试如何证明它工作；
6. 失败模式和安全边界；
7. 面试时如何准确描述，哪些表述属于夸大。

代码由 Codex 协助实现，但每一个阶段必须保留面向学习者的设计说明、运行示例、测试证据和 ADR，使项目既能运行，也能被项目所有者真正讲清楚。

持久教学/工程证据统一从 [`docs/learning/README.md`](learning/README.md) 进入，并由
[`coverage.yaml`](learning/coverage.yaml) 逐覆盖组登记问题/原理、设计/实现、代码地图、数据/控制流、
验证、运行、失败/安全/边界与面试表述八个维度。聊天里讲过、测试总数或代码存在不能代替该证据；
当前 checkpoint 可以暂列 `planned`，但 canonical 继续向后推进前必须改为 `complete`，并通过治理门。

### 6B-3 当前实现门

6B-3 的 Conversation/Message 设计已由 ADR-0040 和专用设计稿冻结；pure model/Service/API、0003
migration/Repository、并发测试、六个 HTTP endpoint、composition/package smoke 与实现后八维复盘均已
在本地建立。实现提交 `7e4f233` / Actions `32329686381` 的 exact-SHA `pytest`、
`postgres-migrations`、`packaging-smoke` 三 job 已公共闭环，coverage 已置为 `complete`。
Conversation 创建固定 owner/relationship/subject，公共 Message 首批只写 user；这一步没有提前接 Agent、
Review Task、Memory、Auth/RSO、SSE、前端或新框架。下一检查点为 6B-4。

### 6B-4 exact-SHA 公共闭环与 6B-5 交接

6B-4 已实现既有 `review_tasks` 的 schema 2.0 Conversation identity、服务器单事务派生 tuple、
trusted-PUUID Summary/Application、1.0/2.0 Executor、Conversation-bound HTTP/composition 与 no-I/O
package 纵向；实现后 walkthrough 已登记八维 evidence。本地完整回归为
`1333 passed, 78 skipped, 1 warning, 110 subtests passed`，横向门禁通过。78 个 skip 只反映本机无
PostgreSQL/Docker；实现 SHA `d63f908` 对应 Actions `32347834279` 的 `pytest`、
`postgres-migrations`、`packaging-smoke` 已全绿，真实 PostgreSQL 为 `113 passed, 1 warning`，Linux
package smoke 的外部调用为 0。6B-4 与 coverage 已关闭；6B-5 Memory Candidate & Write Gate 只登记为
prepared/waiting authorization，尚未实施。

### 6B-5 Memory Candidate & Write Gate（RQ-069，已完成）

用户已明确授权 6B-5。当前已完成专用 ADR-0042、设计与实施计划，并按 TDD 建立 Candidate pure contract、
deterministic gate、0005 ORM/migration、owner-scoped Repository、薄 API/composition 与 no-I/O package
smoke。本批选择事务内 typed materializer 接缝：没有 6B-6 的具体 typed target 时，生产 accept fail closed，
Candidate 保持 pending；测试专用 target 只用于证明同事务 commit/rollback、并发和 replay，不冒充长期 Memory。

实现 `7156cb5` 的首次公共真库 teardown 缺口由最小测试清理 `dd7c9c8` 修复；Actions `32376405150` 的
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，公共完整回归为
`1358 passed, 88 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL 为 `126 passed, 1 warning`。
6B-5 与 coverage 已关闭。RQ-070 随后授权 `6B-6-preferences-profile-review-memory`；其实现与公共闭环状态见下节。
Training Plan/Progress、assistant terminal、Memory Context、Auth/RSO、SSE、前端、LangGraph、Multi-Agent
和新 SDK 均仍 deferred。

### 6B-6 Preferences / Profile / Review Memory（RQ-070，已公共闭环）

用户最新“那继续”已授权唯一下一检查点 6B-6。设计与本地实现现已建立：三张 typed target 表、严格
`value + expected_version` envelope、self/observed 权限、active/superseded/retired 版本链、Review
append 的单 active 最新版本语义、事务内真实 materializer、owner-scoped active/history 查询。
设计文件为 ADR-0043 与 `docs/plans/2026-08-20-memory-types-{design,implementation}.md`。

本地首轮比例回归为 `128 passed, 19 skipped, 1 warning`；提交前复核新增两项纯合同和两项真库合同后，
完整回归为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`。首个 `da87cde` / Actions
`32386630063` 保留 provenance 夹具失败；不放宽生产 Gate 的最小修复 `5531c81` / Actions
`32387026797` 已让 pytest、真实 PostgreSQL migration/concurrency 和 Linux package accept→query 三 job
全绿，真库为 `142 passed, 1 warning`。6B-6 已关闭；6B-7 后续由 `f6d8922` / Actions `32397290175`
完成 Training Plan/Progress 公共闭环。Memory-aware Context、assistant terminal、
Auth/RSO、SSE、前端、Redis/Chroma/向量库、LangGraph、Multi-Agent、新 SDK 与真实 Riot/Provider 调用不在本批。

### 6B-7 Training Plan / Progress（RQ-071，已公共闭环）

self-only Candidate-backed Plan、每 relationship 一个 active、0007、final-Artifact Progress、追加式纠错和
确定性非因果趋势已由 `f6d89225ac5dbd568b6fad7c3c09b7c497c50762` / Actions `32397290175` 的
pytest、真实 PostgreSQL 与 Linux package 三 job 全绿验证。公共 pytest `1445 passed, 106 skipped`，
真库 `151 passed`，package schema 1.4 且外部调用为 0。当前按 RQ-071 进入 6B-8；6B-9 尚未进入。

### 6B-8 Memory-aware Context / Typed Turns（RQ-071，已公共闭环）

ADR-0045 与专用设计/实施计划选择 run-scoped decorator：服务器 Task binding 驱动 owner-scoped selector，
合法 Message/Memory 只作为 data-only whole sections 进入既有 ContextBuilder/Runtime/Harness，同一 ceiling
不可抬高；私有 manifest 只保存 ID/version/digest/count/reason。Assistant 只在 succeeded Task、published/
degraded publication 与 final Artifact digest 全部匹配后持久化。最终 `aacc11a` / Actions `32403187972`
的 pytest、真实 PostgreSQL 与 Linux package 三 job 已全绿，当前进入 6B-9。

### 6B-9 Lifecycle / Export / Exit Review（RQ-071，已公共闭环）

ADR-0046 与专用设计/实施计划选择 centralized owner lifecycle service、各私有业务表 `hidden_at`、body-free
deletion marker、owner-scoped bounded export 与 FK-aware purge。三 scope 为 conversation-only、conversation+
derived Memory、relationship private data；Task/Artifact 与全局 Player Subject 保持独立生命周期。设计门
`4bdb1bb` / Actions `32404203265` 已先独立全绿；实现 `2e37bd4` 的真库唯一失败证明 irreversible trigger
正确拒绝非法 unhide 测试夹具，最小测试修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` / Actions
`32408101770` 的三 job 全绿。公共 pytest `1490 passed, 116 skipped, 1 warning, 110 subtests passed`，
真实 PostgreSQL `164 passed, 1 warning`，Linux package schema 1.6 验证有界 export、conversation-only
隐藏、Preference/Plan 存续与外部调用 0。6B-9、八维 coverage、Session/Memory V1 和阶段 6 正式关闭。

## 2026-08-22：RQ-081 授权与 8A 本地采用门

- 8A 已从当前源码接缝冻结三个可复核问题：顺序 ToolCall 的独立 evidence latency、外部 Meta
  schema/instruction/failure 隔离压力假设，以及明确路由到 8C 的 durable recovery 缺口。
- 8B 的公平比较必须同时包含串行 baseline、普通受限并行 comparator 与角色隔离 Multi-Agent
  candidate；只有相对普通并行仍有增量失败隔离收益，或满足同一质量/安全/成本门的可测收益，才可采用。
- DAG/第三方 Runtime 与 Agentic Retrieval 当前 deferred；`ReviewHarness` 保持唯一发布权，所有 Agent
  均无发布权限，Coach 无工具权限。
- 8A strict adoption gate、ADR、计划与八维证据已由 `12ad835` / Actions `32567642315` 三 job
  exact-SHA 公共闭环，coverage complete。当前只交接 8B prepared/waiting authorization；此状态不表示
  8B 已实现或运行。

## 2026-08-22：RQ-082 授权与 8B holdout 前实现

- 8B 已选择隔离的 evaluation-only 实验包：本地 Scripted/Fake 角色和两个 fixture 工具，三路统一经过
  真实 `ReviewHarness`；不修改产品 Runtime，不接真实 Provider/MCP endpoint。
- 串行、普通并行、角色隔离只改变 acquisition/Context；输入、Coach/Evaluator、Harness、latency/Usage
  模型和阈值不变。普通并行同样执行 exact branch tool gate，不能故意做弱 comparator。
- 聚焦 `22 passed`、相邻 `168 passed, 12 subtests passed`；正式 holdout 仍为 0 次。实现 SHA 先取得
  exact-SHA 公共三 job 后，才在 clean SHA 运行 development admission 和一次不可覆盖 holdout。
- 最终 Multi-Agent adopt/partial/reject 未知；8C–8F 未进入，DAG/第三方 Runtime/Agentic Retrieval 继续 deferred。

## 2026-08-22：8B 唯一 holdout 与 Multi-Agent reject

- implementation `180bc8b` / Actions `32572085065` 三 job 全绿后，同一 clean SHA 先运行 development，
  再唯一执行 calibration-excluded holdout；外部 I/O、retry、hard-gate breaches 均为 0。
- holdout 中普通并行 latency improvement 22.88%、Token ratio 1.05；角色隔离 Multi-Agent 为 18.95%、
  Token ratio 1.45、额外 2 calls/例。两者 match/safe degraded/isolation 均为 1.0。
- ADR-0053 因未达 20% 且没有相对普通并行的隔离增益，拒绝产品采用 Multi-Agent；保留评测资产，普通并行
  只作为 8D 优先设计输入。结果 SHA `944258...445e8`，不得覆盖或重跑。
- 当前仍是 8B in_progress：result/ADR/evidence 提交的 exact-SHA 三 job 和独立状态收尾尚未完成；8C 未进入。

## 2026-08-22：8B 关闭并交接 8C

- result/ADR/evidence `783a329` / Actions `32572610725` 三 job 全绿；公共 pytest `1626 passed, 116 skipped`，
  真库 `164 passed`，Linux package schema 1.6/外部调用 0；8B coverage 已置 complete。
- ADR-0053 正式拒绝产品 Multi-Agent；普通并行只保留为 8D Evidence fusion 的设计输入，不是 8D 实现。
- canonical 唯一交接为 `8c-reliable-runtime-core` prepared/waiting authorization；lease/recovery/cancel/checkpoint、
  DAG、SSE、前端和 8D–8F 均未开始。

## 2026-08-22：RQ-083 授权并启动 8C 设计

- 用户明确“继续啊，咋停了”并在 8B 小复盘后再次确认继续 8C；当前唯一 checkpoint 为
  `8c-reliable-runtime-core / authorized/in progress`。
- ADR-0054 与专用设计采用 PostgreSQL 增量可靠控制面：append-only body-free task event、generation+private
  token fencing、heartbeat、持久 cancel、safe checkpoint、receipt-proven recovery、late-result/duplicate-terminal
  rejection；现有 Runtime Trace 与 Harness 保持各自事实源。
- 完整事件溯源/DAG Runtime 重写和 Redis/Celery 外部队列因缺少 Bad Case 被拒绝/deferred；8B holdout 不覆盖、
  不重跑，8D Riot+OP.GG fusion、SSE/前端和真实外部 I/O 不进入本检查点。
- 该段记录设计入口时的历史事实；随后 0010、Repository/Worker/recovery/API 与八维材料已本地完成，
  当前仍等待 implementation exact-SHA 公共闭环，不进入 8D。
