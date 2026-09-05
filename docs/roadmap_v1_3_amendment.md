# RiftCoach 路线 v1.3 局部校准

## 2026-08-24：8E 视觉前置的顺序约束

`Rift Awakening → Broadcast Workbench` 是 8E 内的设计前置，不是新的主阶段或新的 canonical checkpoint。
它必须先完成 presentation-state 合同、分层资产/来源账本、入口 storyboard 及 responsive/reduced-motion
验证，再进入对应前端实现；不会绕过 Batch E 安全/部署合同、外部调用门或 8F 真实 golden slice。

2026-08-29 的 RQ-155 复查进一步规定：此前收集的官方设计、视觉 gallery、MotionSites/组件库、电竞数据、
Agent observability、Training 与素材工具必须按具体消费者分配。Portal 只吸收 Riot/Universe 语义、构图/字阶
参照和可逆的轻量交互机制；Timeline、Trace、Training 的来源与数据语义不得因视觉 polish 提前混入。该规则不
改变 8E 内部顺序，也不授权新增重型依赖或未经许可的素材。

2026-08-29 的 Region Entry Panel 只是该前置在两个地区的可运行试水：它验证地区选择、媒体切换、Account hand-off 和降级状态，不推进 adopted media，也不改写 8E/8F 顺序。

本文件只记录对既有阶段 0-8 路线的增量修正，不增加、删除或重排九个主阶段。

## 2026-08-31：RQ-176 Flash-only 产品运行时路线校正

用户已明确选择普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品正常运行目标，GLM-5.2 仅保留为显式兼容/应急
回退；Pro/Flash 横向比较不再是当前路线的前置决策。该路线校正允许把 Flash 专属运行时档案接入产品 Agent
主链，但不跳过公共 CI、同一 SHA 的协议复核、G53-7 领域门、完整黄金切片或安全/部署/合规收口。8E 仍在进行，
8F 尚未开始，`production_media=0` 保持不变；Portal、Account、Workbench、Auth 和路由不在本批范围。

## 1. 决策原则

每项能力以后同时记录：

- 最终目标；
- 当前闭环；
- 下一层深化；
- 高级候选；
- 升级触发条件；
- 最终验收证据。

`V1` 表示首个真实、可测试的闭环，不表示能力上限。高级组件仍必须通过 Bad Case、Eval、成本和运维证据后才能进入生产主链。

## 2. 近期顺序

```text
3G-1 至 3G-3 Tool Calling 契约、能力协商与 Provider Registry
→ 4M RAG 独立评测门禁
→ 5A Agent Loop 教学
→ 5B Skill Contract
→ 5C Skill Router
→ 5D Python 受限 Agent Loop
→ 5E AgentRuntime V1
→ 5P 早期产品纵向切片
→ 5F 第三方 Runtime 采用实验
→ 6A 完整 FastAPI 与 SQL 任务模型
```

原 v1.3 曾把第二 Provider 验证放在 4M 之前。2026-08-04 的后续讨论已调整为：
先冻结 3G-1 至 3G-3，进入 4M 和真实 Skill/Agent 场景；3G-4 至 3G-6 在该场景
形成后再按同一领域评测触发。它们是延后，不是取消。

## 3. 3G 多模型边界

当前首个真实基线是 GLM。ADR-0018 已取代 ADR-0017 的模型选择，DeepSeek V4 Pro 是
下一轮唯一有界候选；其独立 Adapter、失败归因和实验控制器已在 D5 离线实现，真实
最小 structured/tool 协议已以 3/3 calls 准入；真实领域 held-out 随后只执行一次并在
首例因 `unsupported_parallel_tool_calls` 未准入，Qwen、Kimi
等仍未锁定。选择第二
Provider 的触发条件是：
出现真实 Skill/Agent 任务后，候选与 GLM 通过
同一套 Tool Calling、结构化输出、错误、质量、延迟和成本评测。第三家只用于验证
扩展性，不以 Provider 数量代替架构证据。

模型能力需要分成三层：启动配置更换默认 Provider、调用方显式选择 Provider、
系统按任务自动路由。Registry 目前只提供前两者所需的内部解析骨架，产品级选择
和自动路由尚未实现；多模型也不等于 Multi-Agent。

ADR-0019 又明确区分“模型分层”与“第三方 Runtime 采用”：当前 5D-7 只让
`deepseek-v4-pro` 进入准入门；Flash/Pro 分层最早在 5P 后重开，默认等待阶段 6 的真实
API 调用、Trace、成本或延迟 Bad Case，再比较 Pro-only、Flash-only 和 Flash 默认/
Pro 有界升级。该横向 Provider 优化不属于 5F；5F 经 RQ-047 收缩为只比较自建 AgentRuntime
与 Pi，Claude Agent SDK 只保留书面排除分析。

3G 声明 Streaming 能力，但完整流式实现可以随阶段 5 产品切片和阶段 6 SSE 消费者逐步补齐。

## 4. RAG 4M 质量门禁

进入依赖 RAG 决策的 Agent Loop 前，补齐：

- 开发集；
- CI 回归集；
- 独立保留集；
- 无答案集；
- 版本冲突集；
- 引用语义支持集；
- 数据集版本和污染记录。

本任务提高评测可信度，不在此时引入 Milvus、Elasticsearch、Neo4j 等重型基础设施。

## 5. Skill Contract 去重

Skill V1 使用：

```text
skills/<skill_name>/manifest.yaml
skills/<skill_name>/SKILL.md
app/skills/models.py
data/evaluation/skills/
```

- `manifest.yaml` 是机器可读的版本、权限、预算和停止契约；
- `SKILL.md` 是任务方法、边界、步骤和示例；
- Pydantic 模型是输入输出 Schema 的唯一代码权威；
- 评测集集中管理，避免每个 Skill 复制一套格式。

## 6. AgentRuntime 演进

V1（阶段 5）：

- `run()`；
- `stream()`；
- 统一输入输出、事件、终止原因、Usage 和 Trace。

V2（阶段 6）：

- `continue_session()`；
- 持久 Session/Memory 与 owner/conversation 隔离；
- owner-local player subject 与外服账号关系隔离；官方 routing 无中国大陆 CN，Riot ID→PUUID 不是
  归属证明，`claimed_self` 在正式产品 Auth、安全 RSO callback 与精确 PUUID match 前始终未验证；
- MVP 关系同时允许未验证 self claim 与受限 public observation；用途与验证状态分开，verified 写路径
  在未来正式 Auth/RSO 门前不存在；
- conversation 创建时固定一个 owner-local player subject，消息/Context/task/run/Candidate 继承该绑定，
  不同 PUUID 新建 conversation；
- 有界历史选择、摘要和 Context 装配合同。

V3（按证据进入阶段 8）：

- `cancel()`；
- `resume()`；
- Runtime Context Compaction、Checkpoint 与恢复；
- Fork；
- Steering；
- Background Task；
- Subagent；
- 跨进程事件和 Checkpoint 分支。

Stage 8 entry design 已把 V3 能力放入可靠 Runtime Core，并增加一条不依赖 V3 的产品化线：
`8A` 先审计高级候选，`8B` 用同一 Harness 做单流程/并行对照，`8C` 才实施 durable event、
lease/fencing、cancel、checkpoint、recovery 与迟到隔离；`8D` 已由 `a274b7f/32598480400` 以 ADR-0055
和 pure TDD 完成 Riot 官方事实、Data Dragon 静态、official patch/update 与 OP.GG partial Meta 的 typed
fusion；`8E` 已获 RQ-086 授权进入 preflight，RQ-087 又用一次 body-free live diagnostic 把 OP.GG
`mid` drift 收敛到 nullable rank-history JSON `null`，ADR-0058 窄修复已由 `83fde7d/32615340228` 公共闭环，RQ-088 下修复后 live replay 又成功创建 body-free bundle；随后做玩家档案选择合同和 legacy 地区审计，
ADR-0059 的 owner-scoped latest-success profile projection、opaque selection 与逐请求/SQL target 四地区路由
已由 `e844bdd/32622696087` 完成 exact-SHA pytest/PostgreSQL/Linux package 公共闭环；随后先做
EvidenceBundle persistence/refresh/expiry、event replay→SSE DTO 和四态状态合同，再分批实施
Web/Auth/HTTPS/备份与部署；`8F` 做最终 Eval 和作品集退出。DAG、Subagent、Agentic Retrieval 和第三方 Runtime
仍是条件性候选，不因名称进入 Core。

### 2026-08-23：8E Batch B 本地产品合同

- 复用成功 Player Link 作为 owner-scoped 玩家档案，不新增 default/profile table；
- `player_profile_id` 只公开 opaque relationship identity，禁止 PUUID/owner/task/fingerprint 泄漏；
- legacy request 地区进入 payload/fingerprint，Conversation 使用 SQL execution target，Worker exact-select
  `americas/asia/europe/sea`；环境只提供 Riot Key，不再提供默认 region；
- RQ-089 已补齐本机 Docker/PostgreSQL/Linux smoke，历史公共 PostgreSQL/Linux exact-SHA 证据仍保持独立；
- `e844bdd/32622696087` 的公共 pytest 1709、真库 187、Linux package schema 1.6 三 job 全绿；
- coverage 继续 `planned`，因为 Batch C、前端/Auth/SSE/备份/部署与整体退出尚未完成。

### 2026-08-23：8E Batch C Evidence/Product API 公共闭环

- ADR-0060 已落地为 0011 PostgreSQL append-only EvidenceBundle revision、refresh content idempotency、
  query-time expiry 与 strict nested/bundle/snapshot digest rehydrate；
- owner-scoped Evidence/Product API 和 cursor SSE 已完成 TDD，composition/package smoke 继续保持外部
  Riot/OP.GG/Provider/LLM calls 0；
- 实现中额外修复浅拷贝 tamper 假阳性、retry timestamp 误冲突和 import-order circular dependency；
- implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions `32629160732`
  已完成公共 pytest 1750、真实 PostgreSQL 194 与 Linux package 三 job；Batch C 正式关闭；
- 八维材料已登记，整个 8E coverage 继续 `planned`。RQ-091/RQ-092/RQ-093、ADR-0061 与专用计划已
  冻结多来源采用门、五模块连续性、`Rift Command Center`、状态和 a11y；design
  `88a5ab6/32631766013` 与 implementation/evidence `f7ebedd/32636771507` 均完成 exact-SHA 三 job，
  Batch D 静态 fixture screen 正式关闭。下一动作是 API/SSE 接线设计门；不提前接 Auth/部署或 8F。

### 2026-08-23：RQ-094/RQ-095 Live Integration 设计门

- 历史双层视觉组合重新持久化为 `Rift Awakening → Esports Intelligence`；Void 3D 只按 Advanced 风格
  采用门局部实验，不把 Batch D 的工作台优先顺序误写成最终视觉三选一；
- 8-Core 仍要求完整真实 Evidence→Training→UI 纵向。8D pure typed kernel 与 8E degraded replay 是必要
  前置证据，但缺 Data Dragon/official patch/训练/UI 时不能关闭该目标；
- OP.GG breadth 不按工具数量扩张：champion analysis 与 lane matchup 是最低评估候选，synergies 由阵容
  消费者触发；每项继续经过 per-tool schema/provenance/cost/degrade gate；
- 当前接线门只采用 owner-scoped latest locator + existing APIs，在客户端做 strict composition；拒绝大 BFF
  聚合真源和 URL/localStorage-only 身份。ADR/design/plan 已由 `4057c93/32639561338` exact-SHA 三 job
  公共关闭；RQ-096 随后授权 implementation/evidence；
- locator/Summary/typed Evidence、exact wire decoders、generation/abort、single EventSource、default-live React
  与真实 Training 边界均已通过本地 TDD。escaped plain text 因 150 kB bundle 门取代超限 react-markdown；
- implementation/evidence `f441061/32647933692` 已完成 exact-SHA 三 job；公共 pytest 1796、真实
  PostgreSQL 200、frontend unit 66/e2e 17、JS gzip 122.01 kB、可逆 Alembic 与 Linux package schema 1.6 全绿；
- 8E/coverage 继续 in_progress/planned；Auth/部署、入口/Timeline/完整 Training、breadth/golden slice 与 8F
  不随本批进入。唯一下一检查点为 Batch E security/deployment entry design prepared/waiting authorization。

## 7. 产品切片

阶段 5 在本地 AgentRuntime 可运行后，增加不依赖临时数据库的早期 API 切片：

```text
POST /reviews/recent
GET /runs/{run_id}
GET /runs/{run_id}/report
GET /health
```

ADR-0032/0033 已在 5P entry design 中裁决旧清单：同步文件型 V1 不单列重复的 status；
follow-up 需要 Session/Memory/澄清，推迟到阶段 6。该切片复用现有 Runtime Trace 与 Harness
Artifact，但增加 body-free file receipt 作为查询投影，不冒充 SQL、任务恢复或事件日志。

5P 同时承担早已保留的 Prompt Program V1，内部固定顺序为：

```text
5P-1 Product Request & Typed Skill/Runtime Compiler
5P-2 Prompt Program V1 & Runtime Composition Root
5P-3 Domain Pipeline Promotion & Application Service
5P-4 File-backed Run Receipt & Query Projection
5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice
5P-6 Product Slice Evaluation & Exit Review
```

阶段 6 再加入 SQL、用户隔离、Session、Memory、幂等和 owner-scoped 对话/复盘入口；高级
cancel/resume/恢复与 Runtime Compaction、SSE 和完整前端仍属于阶段 8。RQ-060 的入口设计又进一步
限定：正式 Auth/HTTPS、SSE/前端不在当前 checkpoint 内，不能借 Session/Memory 设计提前实现。

## 8. OP.GG 与 Meta

阶段 7 的明确目标包括标准 MCP Client 和 OP.GG MCP 主线接入，但业务层不得依赖 OP.GG 原始字段：

```text
OP.GG MCP
→ Standard MCP Client / Streamable HTTP
→ ToolDefinition / ToolRuntime
→ OPGGMetaAdapter
→ MetaEvidence
→ data-only Context
→ Skill / Agent
→ Quality Harness
```

实施时仍需验证端点、协议版本、许可和公开部署边界。第一批其他来源只考虑官方补丁和 Data Dragon，不为了形式上的多源同时接入大量网站。

## 9. 阶段 8 双轨

`8-Core` 是必须完成的产品、部署、合规、Eval 和作品集交付线。

`8-Advanced` 至少完成一个高级能力采用实验，包含 Bad Case、实现、对照、消融、成本和 ADR。实验可以得出采用、局部采用或拒绝采用；不预先强制 Multi-Agent、DAG、Agentic Retrieval 或微调上线。

入口设计冻结的机器检查点为：

```text
stage-8 entry design
→ 8A advanced-adoption-gate
→ 8B conditional-multi-agent-experiment
→ 8C reliable-runtime-core
→ 8D riot-opgg-evidence-fusion-core
→ 8E productization
→ 8F final-evaluation-and-portfolio
```

8-Core 的前端采用自主 React 设计系统与精选外部资源；MotionSites 只作为公开可检索的视觉/
Prompt 候选源，付费 Prompt/资产必须逐项核验许可、性能、移动端和 reduced-motion 替代后才能
获取。用户提供的离线候选表属于研究输入，不是运行时依赖或路线权威。

## 10. 当前执行状态

当前仓库已经完成：

```text
3G-1 Tool Calling 内部消息契约
3G-2 Provider 能力协商
3G-3 Provider Registry
4M 独立 RAG 保留集首个门禁
5A 最小 Agent Loop 与真实 knowledge.search 领域切片
5B Skill Contract 与 recent-form-review 样板
5C-1 Skill Router 输入输出契约与三态决策约束
5C-2 Skill Catalog 严格发现、稳定快照与候选投影
5C-3 声明式确定性路由
5C-4 拒绝、排除否决与多候选歧义验收
5C-5-prep-2 single-match-review 第二个真实 Skill Contract
5C-5 双 Skill development/holdout Router Evaluation
5C-6 Model Fallback Decision（ADR-0010 暂缓 LLM fallback）
```

4M 当前使用 7 个小型保留案例，结果用于证明门禁机制可运行，不代表检索已经具备充分泛化能力。后续应扩充按知识类型、版本和位置分层的保留集，但不因此引入重型向量基础设施。

5C 的完整原始检查点和当前状态为：

```text
5C-1 Router Contract          已完成
5C-2 Skill Catalog            已完成
5C-3 Deterministic Router     已完成
5C-4 Rejection / Ambiguity    已完成
5C-5 Router Evaluation        已完成；development 23/23，holdout 11/12
5C-6 Model Fallback Decision  已完成；ADR-0010 暂缓 LLM fallback
5C-exit-review                已完成；合同、证据、限制和 5D 前置项已复核
5D-entry-design               已完成；ADR-0011 与原子检查点已冻结
5D-1 Skill Run Boundary       已完成；身份、run ID 与输入内容绑定已加固
5D-2 Context Builder V1       已完成；最小事实投影、信任分层与整段预算选择已加固
5D-3 Run Compiler & Budgets   已完成；Manifest-only 编译、累计 Context 与总 deadline 已加固
5D-4 Agent Draft & Evidence   已完成；实际知识工具记录已转换为未发布草稿与可审计证据
5D-5 Harness & Typed Output   已完成；统一 preparation 接缝、唯一质量门禁与 Artifact 驱动终态输出
5D-6a Structured Output       已完成；请求合同、Pydantic 校验、一次修复与 fail-closed 边界已建立
5D-6b Provider Gate           已完成（部分采用）；最小协议准入，GLM recent-form 领域能力不准入，fallback 真实生效
5D-7 Prompt/Context Eval      已完成；评测/安全门通过审查，当前无领域 Provider 准入；ADR-0028 保留质量 unknown，G53-0 deferred
5D-exit-review                已完成；十项功能要求与 V1 NFR 通过，领域 Provider 未准入限制保留
5E-entry-design               已完成；ADR-0029 采用薄 Runtime、可选观察端口与原子 Trace
5E-1 Contract/Usage/Store     已完成；d891184 / Actions 31942483874 exact-SHA 公开通过
5E-2 Observable run()         已完成；Task D `d49508e` / Actions `31959646589` exact-SHA 公共验证成功（747 tests/110 subtests）
5E-3 Live stream() parity     已完成；`80b76a1` / Actions `31960987333` exact-SHA 公共 CI 成功（15 聚焦，762 全量）
5E-4 Evaluation/exit review  已完成；`3d36561` / Actions `31962252231` exact-SHA 公共 CI 成功，决策为 close-with-deferred-boundaries
5P-entry-design              已完成；`49841ec` / Actions `31985199623` exact-SHA 公共成功
5P-1 Product/compiler       已完成；`57bd36a` / Actions `31987501935` exact-SHA 公共成功
5P-2 Prompt Program         已完成；`0a9651f` / Actions `31988837293` exact-SHA 公共成功
5P-3 Domain/Application     已完成；`4bd5c83` / Actions `31998739178` exact-SHA 公共成功
5P-4 Receipt/Query          已完成；`932a863` / Actions `32002994441` exact-SHA 公共成功
5P-5 Thin FastAPI           已完成；`6d1e5b0` / Actions `32005648179` exact-SHA 公共成功，24 API tests、完整 `884 passed, 110 subtests passed`
5P-6 Product Slice Exit     已完成；`8c8acc6` / Actions `32010604551` exact-SHA 公共成功，裁决 `close-with-deferred-boundaries`
5F-entry-design            已完成 Pi-only 采用入口设计；`ce97975` / Actions `32013948784` exact-SHA 公共成功；下一步 `5F-1-pi-source-license-contract-audit`
5F-1 Source/License Audit  已完成；冻结 `earendil-works/pi v0.84.2` / `914cf147...`、MIT/Node/合同差异；有条件允许 5F-2；`5901b09` / Actions `32016852979` exact-SHA 公共成功
5F-2 Offline Adapter Spike 已完成；exact lock/JSONL sidecar/Python controller、35 focused、99 adjacent、完整 919/110 subtests 与本地退出审查完成；`pass-with-boundaries`；`f62f078` / Actions `32022258177` exact-SHA 公共成功；下一检查点 5F-3
5F-3 Contract/Harness Eval  已完成；45 focused、196 adjacent、完整 929/110 subtests；裁决 `harness-compatible-but-runtime-gate-failed`，Context/terminal/live timing 硬门失败；`3d9a081` / Actions `32025522606` exact-SHA 公共成功
5F-4 Bounded Real Slice    未进入；5F-3 前置硬门失败，真实模型调用无信息增益，external calls 0
5F-5 Adoption/Exit         已完成；裁决 `partial-adopt-evaluation-assets-only`；`f8dea66` / Actions `32028206103` exact-SHA 公共成功；产品拒绝 Pi，冻结保留评测资产/CI 复现与采用门方法
6A entry design            已完成；6A-1 至 6A-7 已由 `adf53e5` / Actions `32146760003` 的 pytest、真库与 Linux packaging 三 job 公共闭环；Session/Memory entry design、6B-1 至 6B-9 与 RQ-067 文档门均已公共闭环；6B-9 最终 `cbc7cbd` / Actions `32408101770` 三 job 全绿并关闭阶段 6

阶段 7 入口设计与 7-1 pure contract 已由 `e50a546` / Actions `32436092074`、
`37f16bc` / Actions `32439753589` exact-SHA 公共闭环；7-2 又由 `f121666` / Actions
`32441793585` 完成 transport/session/discovery 三 job 公共闭环。7-3 以
ADR-0048 裁决 OP.GG `admitted_with_restrictions`，并由 `64311a1` / Actions `32455219404`
完成官方 Streamable HTTP、partial MetaEvidence、严格 lane-meta Adapter、data-only Context 与一次
真实 body-free 单向产品 smoke 的 exact-SHA 三 job 公共闭环。RQ-078 授权的 7-4 RiftCoach Server
又由 `431c584` / Actions `32480827952` 完成 strict Server/Facade、四个只读工具与 exact-SHA 三 job
公共闭环。7-5 实现 `a88fbc4` / Actions `32483521108`、clean-SHA 官方 SDK→RiftCoach stdio 与
RiftCoach→OP.GG Streamable HTTP 双向门，以及不可覆盖 evidence `fac6fe0` / Actions `32484257736`
均已通过；Stage 7 正式关闭。Stage 8 entry design、8A 与 8B 已依次公共闭环，ADR-0053 reject 产品
  Multi-Agent；RQ-083 的 8C 已由 `2df5349/32587659678` exact-SHA 公共关闭，8D 又由
  `a274b7f/32598480400` 公共关闭，当前主检查点为 8E productization。
```

Fresh-Gate 4 运行入口已完成版本化 readmission、V2 active CLI、prepare-only 和 Fresh
result envelope；相邻 93、完整 580 tests 通过，实现 `ed3cc94` / Actions `31863341338`
公开成功，同 SHA prepare-only 为 no-I/O admitted。用户确认后 V2 只执行一次：首例
1 call/3440 tokens，下一调用预留 1024 output 后超过单例 4000-token 门并在 I/O 前停止；
后两例 skipped，结果 `admitted=false` 且不可重跑。结果归档 `60b5c86` / Actions
`31864370988` 已公开验证。ADR-0025 随后精确证明第二次调用至少需要 4464-token 单例
上限，并以三阶段真实本地 envelope 建立非 tokenizer 的长度校准投影；裁决实现
`78400b9` / Actions `31865285994` 已公开验证；V3 development 资源校准的双 profile、
四阶段 body-free request snapshot、Fake 8-call/首错停止、安全结果、预算推导和 no-I/O
admission 已由 `2d67696` / Actions `31867655627` 公开验证；真实入口又由 `6aa8c43` /
Actions `31868747216` 公开通过，同 SHA prepare-only 为零调用。正式 replay 第 1 个请求
没有形成规范化响应并首错停止：1 external call、0 Usage observations，实际 Token/费用
unknown，后 7 calls 未发送。预算与 V3 held-out 均未创建；结果/裁决已通过 34 项聚焦、
611 项完整本地回归和全部本地门禁，并由 `421a243` / Actions `31869409106` 完成最终
公共归档。ADR-0027 已零调用关闭当前 DeepSeek V3，不生成 budget/held-out、不补跑，
并把允许列表安全错误 provenance 设为未来真实 Provider 门前置条件；决策提交
`ea91e9697c820c0850db488a93263fc169719515` 已通过 Actions run `31872476103`。
安全错误 provenance 切片已完成本地/公开验证；旧文档当时把 GLM-5.3 G53-0 记为“待普通 API
上线后再审计”。RQ-164 已补做本地无 I/O 静态审计，但账号/Plan 权限、实际 endpoint/region、
正式 model ID 与 `enabled + low` 可用性仍 unknown/deferred；不能把该旧快照当作当前可用性结论。

ADR-0028 随后完成 5D-7 收尾裁决：分层评测、Prompt/Context 身份、Evaluation 1.1、
held-out 生命周期、资源控制和安全失败归因已经构成完整采用门；GLM-5.2/DeepSeek 的领域
质量仍未准入并保持 unknown。模型 reject/unknown 是有效采用结论，不要求围绕旧考题
追绿。G53 deferred 和 Flash/Pro 分层不再阻塞 5D-7；审查提交 `7c8f4e7` 已通过
Actions run `31876536179` 的 exact-SHA 公共 CI。随后 5D 退出审查确认受限执行、
Manifest 权限/预算、实际 Tool evidence、唯一 Harness、类型化终态与安全失败路径均满足
V1，当前无领域 Provider 准入不阻塞厂商无关 Runtime；退出提交 `2f4e4d4` 已通过
Actions run `31877076222`，唯一下一检查点现为 5E 入口设计。

ADR-0026 已进一步冻结校准方法：baseline/ceiling 两个公开 development profile 各形成
初始 Agent、工具后 Agent、Evaluation 和 Evaluation repair 四阶段请求；未来真实校准
最多 8 calls，校准输出 64、零重试、首错停止。V3 单例 Token 上限只允许由逐阶段最大
真实 input Usage、25% 工程余量和四次 1024 output ceiling 推导；含既有协议成本后超过
`$0.10`、现有 Agent deadline 不可达或 envelope 越界时停止，不创建 held-out。当前只
进入离线 TDD/公开冻结，不构造 Provider、读取 Key 或调用模型。

该设计已由提交 `351c0e64adf9d2ace42c557d40fac81a44ab539e` 和 GitHub Actions run
`31866084382` 完成 exact-SHA 公开冻结；这不等于校准实现或真实 Usage 已完成。

5C 路由旧开发集有 15 个参与校准的小型单 Skill 案例，历史精确匹配率为 `1.0`、
错误选择率为 `0.0`。它已原样归档并附带 SHA-256 与重建来源说明。现在 Catalog
已有两个真实 Skill，旧结果因候选集合变化而有意过时；双 Skill development v2
的 23 条已全部精确匹配；independent holdout v1 单次运行结果为 11/12，唯一失败
是设备语义假朋友被误选为近期复盘，且未据此修改规则。

源码审计已修正首批 Skill 分类：`recent-form-review` 与 `single-match-review` 是
两个真实用户任务；报告事实审查继续由已经实现的 `EvaluatorStep` 和
`ReviewHarness` 强制执行，不重复包装为内部 Skill。未实现的调用模式合同已取消。
`single-match-review` 已完成，5C-5 第一批已冻结旧单 Skill 基线并建立双 Skill
development/holdout 的角色、污染和版本快照门禁；第二批 development v2 已以
23/23 精确匹配接受并冻结规则，第三批 holdout v1 已单次运行并以 11/12 原样收尾。
5C-6 已基于唯一设备域 Bad Case 完成方案比较：V1 保持确定性 Router，不根据
holdout 调词，也不立即引入模型；类型化入口和澄清优先，模型重开需满足新鲜数据、
结构化输出与质量/成本门槛。5C 退出复核已通过；5D entry design 选择 AgentLoop
作为 Harness 的 evidence-aware draft preparation，并保持 Harness 唯一发布权。
后续顺序为 5D-1 输入/身份/Artifact 边界、5D-2 Context Builder、5D-3 编译与预算、
5D-4 Agent draft/evidence、5D-5 Harness/终态输出、5D-6a 结构化输出、5D-6b 真实
Provider 准入、5D-7 领域评测和 exit review。5D-1 已实现执行前身份与输入完整性
边界；5D-2 已实现 provider-neutral Context Builder，用两个 Skill 各自的 allowlist
投影事实，以 trust 标签区分 system 指令与 data-only 内容，并在 Manifest ceiling 内
整段选择可选 match/citation。5D-3 已实现 `AgentRunCompiler`，只从 Manifest 映射
工具与运行预算，并在每次 Provider 调用前检查包含 Tool Observation 的完整累计消息；
Provider/Tool 共享递减的协作式总 deadline。5D-4 已让两个真实 Skill 在 Fake Provider
下调用真实本地 `knowledge.search`，并只从实际成功的 ToolExecutionRecord 构造
`KnowledgeEvidence`；最终模型文本仍只是未发布 `CoachDraft`。5D-5 已增加统一
`DraftPreparationStep` 与旧顺序 Adapter，让 Agent draft/evidence 进入现有唯一
ReviewHarness；`SkillReviewExecutor` 从 Manifest 映射质量门禁，terminal Skill Output
只从完整性校验通过的最终 Artifact 构造。5D-6a 已建立 Provider-neutral 结构化输出
合同：请求声明 Schema、能力协商要求 structured output、严格 Pydantic Evaluation 验证、
最多一次同合同 repair 和 fail-closed Harness 降级/拒绝。5D-6b 已完成 disabled-thinking
下 P1-P5 真实微探针、生产 Zhipu Adapter 离线双向映射，以及严格 structured request、
现有 AgentLoop 和固定只读知识工具的精确 3-call 真实协议切片；A1/A2 均通过并
`admitted=true`。真实领域 Skill/Harness 随后只执行一次：一个计费请求后没有统一
`ChatResponse` 到达 Agent，因而无 ToolCall、知识证据或 Evaluation，领域
`admitted=false`，Harness 安全降级到确定性报告。
近期复盘领域切片离线控制器现已完成：它严格复读并哈希已准入的 3-call 协议结果，
让 AgentLoop 与唯一 ReviewHarness 共用剩余 4-call 的 pre-I/O 预算，并只输出脱敏 typed
report。控制器提交 `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 的 GitHub Actions
run `31657764638` 已全部通过。ADR-0012 据此以部分采用收尾 5D-6b：准入最小
Adapter 协议、拒绝 GLM recent-form 领域能力、保留 fallback；不重跑或临场调 Prompt，
也不立即接入第二 Provider。5D-7 Batch A 随后采用 ADR-0013 的分层领域评测，建立严格
Dataset/Candidate/Result 合同、development/held-out 生命周期和 10 案例离线基线；任务
结果与主失败分类均为 10/10，并保留 1 个故意构造的 unsafe-publication 负例与 1 个
资源超限负例。Batch B 再采用 ADR-0014，以组件与案例双层 SHA-256 冻结 Skill、Context、
知识工具、Evaluation 和 demo 输入身份，把 Domain E2E 合同升至 1.1，并建立 Provider
前零调用 admission。Batch C 又以 Scripted Provider 驱动 7 个真实本地控制流场景并
保留 1/7 unsafe-publication Bad Case。Batch D 入口由 ADR-0016 冻结版本化迁移：保留
`coach_evaluation@1.0.0`，以 1.1.0 增加最小用户/RAG 安全上下文和不可修订
blocking policy。D1-D2 已在 7 场 secure offline executable development 基线上验证，
task/failure accuracy 均为 `1.0`、unsafe publication 为 `0.0`、external calls 为 `0`；
D3 已在规则冻结后创建 3 场独立 held-out，但没有运行。上述证据仍不验收真实模型。
ADR-0018 已更正并完成 D4：DeepSeek V4 Pro 是唯一有界第二 Provider 候选，调用/Token/
金额、错误归因和停止规则已经冻结，DeepSeek 停止线为 `$0.10`。D5 已离线实现独立
Adapter、安全错误归因、实验 ledger/stop controller 与 no-I/O preparation；Fake SDK
协议和完整回归通过。real-gate execution seam 的 exact-SHA 公开 CI/no-I/O preflight
通过后，DeepSeek V4 Pro 真实 structured 与 Agent tool round trip 只运行一次并以
3/3 calls、1428 tokens、约 `$0.00221496` 准入；没有运行 held-out。唯一下一步仍在
5D-7 内。领域执行接缝现已完成本地离线 TDD：no-I/O admission 绑定代码/CI、
Dataset/Snapshot、真实协议字节摘要和案例计划摘要；累计 ledger 继承协议消耗，并约束
domain/单例 calls 与 Token；逐例分层判断执行首错停止、unsafe 全局停止及脱敏不可覆盖
记录。本批新增 Provider calls 与 held-out executions 均为 0；接缝提交
`7986e1ade9ab165b4b2916a62b067587c5c3f027` 已通过 GitHub Actions run
`31785253957` 的 exact-SHA 公开 CI。后续生产装配批已把未执行 held-out 版本化更正为
1.1.0，并实现独立输入计划、oracle-blind 生产 Executor 与 Key-last CLI；装配提交已通过
exact-SHA 公开 CI。真实门获确认后只执行一次：首例因 `unsupported_parallel_tool_calls`
未形成统一响应而安全降级，后两例 skipped，领域 `admitted=false`。当前考卷不得重跑，
多 ToolCall 批次现已在 development 中通过严格双向传输、整批零副作用预检和顺序执行
测试，并以 Fake SDK 真实串联本地 RAG/Evaluation/Harness；该离线证据待 exact-SHA 公开
CI，且不能改变旧真实拒绝结果或提前进入 5D exit review/5E。该 CI 已由提交 `037a47f`
和 Actions `31817798170` 验证。ADR-0024 随后接受新鲜领域采用门设计：复用现有控制面，
 先用合成 development 数据实现兼容 input-plan、逐案例 Prompt/Context commitment、历史
证据链和 no-I/O admission；该本地 TDD 现已以 V1.0 兼容读取、V1.1 三案例摘要、历史
`3+1` 调用与禁止 Provider 构造合同完成，完整回归为 `568 passed, 103 subtests passed`；
提交 `adba965` 已通过 Actions `31860874440`。新的匿名 fixture、Dataset、三案例 V1.1
输入计划和实际 Context 摘要又由资产提交 `1e44b13` / Actions `31861960565` 完成
exact-SHA 公开冻结。Fresh-Gate 4 入口又由 `ed3cc94` / Actions `31863341338` 公开验证，
同 SHA prepare-only 通过；V2 随后只运行一次并因真实 Prompt 下的单例 Token 门不准入。
旧 Dataset 1.1.0 与 V2 均不重跑；预算可达性离线裁决已本地完成，下一步先公开验证，
再设计 V3 development 资源校准，仍不直接调用 Provider。
原 `prep-1` 与 `prep-3` 均在写代码前取消；动态状态以
`docs/project_execution_state.md` 为准。
5P-3 已把 Summary/Report 纯业务逻辑提升到 `app.lol`，并建立严格
`RecentReviewApplicationService`、body-free 安全错误映射与 secure product execution factory。
5P-4 已在其后实现 body-free immutable receipt、strict Query 与 Application receipt 接缝，并由
`932a863` / Actions `32002994441` 完成 exact-SHA 公共验证。该证据仍不代表真实 Riot/Provider
质量、SQL/恢复或生产部署已经完成。5P-5 又完成薄 FastAPI Adapter、OpenAPI/错误映射与真实
Runtime/Harness/RAG no-I/O TestClient 纵向切片，并由 `6d1e5b0` / Actions `32005648179` 完成
exact-SHA 公共验证。5P-6 又完成十项功能、分层/NFR、安全/no-I/O 与 deferred 边界审查，裁决为
`close-with-deferred-boundaries`，并由 `8c8acc6` / Actions `32010604551` 完成 exact-SHA 公共
闭环；这些证据仍不能被说成公网部署或真实模型质量。整个 5P 已完成，canonical 只交接到
`5F-entry-design` 准备状态。

`3G-4` 真实第二 Provider、`3G-5` 多 Provider Tool Calling 和 `3G-6` 任务级自动
路由暂不作为连续任务；它们要等 Skill 和 Agent Loop 形成真实调用场景后，按同一
套契约和领域评测重新触发。

## 2026-08-18：6A-6 安全/生命周期/NFR 实施交接

用户按 RQ-058 明确继续，解除 `6A-6-security-lifecycle-nfr` 的准备状态。6A-1 至 6A-5 的
PostgreSQL 与异步 API 公共证据保持不变，本批只补 task 基座的默认关闭 CORS、日志/Secret 脱敏、
owner/global 背压、7/90/30 天数据保留、terminal hidden-before-cleanup 删除、active delete
冲突、结构化可观测性和性能样本。实施顺序固定为“教学 → 红灯 → 最小实现 → 本地门禁 → exact-SHA
公共 PostgreSQL CI”；不进入 6A-7，不实现正式 Auth/HTTPS、Session/Memory、SSE、前端、
lease/heartbeat/reclaim/cancel/resume 或真实 Provider/Riot I/O。

实现与性能证据随后由 `fecbb11` 和 evidence-only 修补 `31d5e60` 完成；Actions run
`32138025724` 的普通与 PostgreSQL job 均成功。真库 job 为 `51 passed`，并在
`github-actions-postgresql-17-python-3.11` 记录 8 样本 create/query p95 `6.220ms` 与
queued→claim p95 `23.359ms`。6A-6 正式关闭，只交接 6A-7 准备状态；这些数值不是 Agent
模型质量或公网 SLA 证据。

## 2026-08-18：6A-7 Packaging/Exit 实施授权

RQ-059 解除 6A-7 等待确认。本批闭环可重建 API+Worker+PostgreSQL package、此前仍 fail-closed 的
真实 Worker executable composition、配置/启动命令、Linux no-I/O smoke 与逐项 exit matrix/review。
smoke/CI 不读取真实 Key 或调用 Riot/Provider；配置不完整时 Worker 必须在 claim 前 fail closed。
正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/reclaim/cancel/resume、直接公网部署和新框架仍按
既定后续检查点处理。exact-SHA 公共 CI 成功前 6A 保持进行中。

在最终公共 run 之前，本地 production Worker composition、隔离 no-I/O smoke、非 root image/Compose/CI
合同已形成；诊断修补后聚焦 `48 passed`、完整 `1102 passed, 27 skipped, 110 subtests passed`，两套 RAG、
Harness dry-run、compileall 与安全门通过。当时本机无 Docker/PostgreSQL 运行证据，因此裁决正确保持
`keep-open-pending-exact-sha-linux-ci`；下文的 `adf53e5` 公共证据随后取代该临时状态。

首个提交 `b0f61ca` / Actions `32145005904` 的 pytest 与真实 PostgreSQL job 已成功，Linux job 也已完成
image build、migration 和 API readiness，但 one-off smoke 只返回过宽 worker failure。当前只增加 body-free
stage code 与 bounded service logs；不能把部分成功改写成 6A 已完成。

诊断提交 `d8c5063` / Actions `32146113582` 将失败定位为 `packaging_smoke_database_not_ready`，而同一
API readiness 200/POST 202、真库 job 成功。根因是 direct script 从 wheel 导入 app 后 Alembic
PROJECT_ROOT 漂移；当前只把 Worker/smoke 改为 `python -m scripts...`，不放宽 migration readiness。

module-entry 修复 `adf53e5` / Actions `32146760003` 随后三 job 全绿：pytest 1102、PostgreSQL 51、
packaging-smoke 成功且 image boundary 通过；状态收尾 `d1cc2ed` / Actions `32147545753` 也已三 job
成功。6A 以 `close-with-deferred-boundaries` 关闭；RQ-064 已将
`stage-6-session-memory-entry-design` 冻结为 ADR-0039/正式设计/实施计划；设计提交 `bc11afe` /
Actions `32222531783` 三 job 已成功；6B-1 又由 `ed8fa58` / Actions `32229024069` 三 job 公共完成；
6B-2 已由 `0c13a58` / Actions `32301852042` 三 job 公共完成。RQ-067 文档/工程证据批随后由
`63435d9` / Actions `32308631289` 三 job 公共闭环。6B-3 Conversation/Message foundation 随后已本地
实现并补齐 walkthrough；实现提交 `7e4f233` / Actions `32329686381` 的真实 PostgreSQL/package 公共门
已全绿；长期 Memory 与公网部署仍未实现。

### 2026-08-20：6B-3 设计冻结

ADR-0040 将 6B-3 的隐含合同正式化：active relationship 必须在创建事务中锁定检查；Conversation
创建继承 owner-scoped 幂等键；Message schema 保留 user/assistant 但公共入口只允许 user；序号从 1
开始由行锁递增；archived/hidden 分开；PostgreSQL trigger 防止绑定字段 direct SQL rebind。实现已经
落到 domain、Service、0003、Repository、HTTP/composition/package 和分层测试；`7e4f233` /
Actions `32329686381` 的 exact-SHA 三 job 已全绿，6B-3 现为 complete，下一检查点为 6B-4；这不表示
Agent 已接入或 Memory 已完成。

## 2026-08-22：8A Advanced 采用门本地裁决

- RQ-081 授权后，8A 将 Advanced 候选收敛为串行 baseline、普通受限并行 comparator 与角色隔离
  Multi-Agent primary candidate；这三路必须复用同一 fixture、Context ceiling、Harness 与发布阈值。
- 角色隔离只允许 Knowledge/Meta 各持一个固定 fixture 工具，Coach 无工具且只消费 typed Artifact；
  `ReviewHarness` 仍是唯一发布权。权限重叠、跨角色泄漏、无 provenance、终态漂移、真实 I/O 或结果覆盖
  任一非零即 reject。
- DAG/第三方 Runtime 与 Agentic Retrieval 继续 deferred；可靠 lease/recovery 明确属于 8C V3 Core，
  不作为 8B Multi-Agent 采用理由。
- 离线 gate TDD 与持久证据已由 `12ad835` / Actions `32567642315` exact-SHA 三 job公共闭环；
  holdout 未运行、外部调用为 0。8B 的收益/成本数字仍是未来停止线，不是当前实测；8B 只 prepared。

### 2026-08-22：8B evaluation-only 实现边界

- RQ-082 已授权 8B；实现隔离在 `app/evaluation/stage8_experiment/`，不接入产品 Runtime/composition。
- 三路均使用 frozen case/input/tool identity、Scripted Usage 与同一真实 Harness；普通并行和角色隔离都做
  atomic exact-tool preflight，角色隔离额外证明独立 Context digest 和 Coach 零工具。
- development/holdout result 会复算 identity、role、Artifact binding、metrics 与 verdict；正式 holdout 只能在
  实现 SHA 公共全绿后执行一次。当前只完成本地 holdout 前 TDD，结果和采用裁决尚不存在。

### 2026-08-22：8B 最终采用裁决

- `180bc8b/32572085065` 公共全绿后唯一 holdout 已执行；result SHA `944258...445e8`、外部 I/O 0。
- Multi-Agent match/safe degraded/hard gates 合格，但 modeled latency 18.95% 未达 20%，Token 1.45、+2 calls；
  普通并行为 22.88%、Token 1.05、无额外 calls，失败隔离同为 1.0。
- ADR-0053 拒绝产品 Multi-Agent，证明 V3 Advanced 的 `reject` 出口真实可用；普通并行仅交给 8D 重新按
  Core 边界实施。DAG/第三方 Runtime/Agentic Retrieval 不因此自动恢复。

### 2026-08-22：8B 关闭条件与 8C 交接

- result/ADR/evidence `783a329/32572610725` exact-SHA 三 job 全绿后，8B 八维 coverage 置 complete。
- 8B 的 reject 结论保持：Multi-Agent 不进入产品；普通并行不在 8B 越级实现，待 8D 重新设计。
- 可靠 Runtime Core（lease/fencing、cancel、checkpoint、recovery、late-result isolation）成为唯一下一
  检查点 `8c-reliable-runtime-core`；该段记录 8C 设计入口时的状态，随后本地实现已完成，公共门仍待验证。

## 2026-08-22：8C 可靠控制面设计裁决

- 继续以 PostgreSQL 为唯一 task control plane，扩展现有 `review_tasks`、Repository 和 Worker；新增 body-free
  append-only task event、global cursor/task-local sequence 与 SHA identity，不复制 Provider/Tool Runtime Trace。
- claim 分配 generation + private token + expiry；heartbeat/checkpoint/terminal 必须携带 fencing identity。
  cancel 是持久请求；过期任务只在 strict Receipt 或 `claimed_safe` checkpoint 证明下自动处理，否则进入
  `recovery_required`。
- 单 Worker/单 Runtime 与 Harness 唯一发布权保持兼容；DAG/第三方 Runtime、Redis/Celery/Kafka、SSE/前端、
  8D fusion 与真实外部 I/O 均不进入 8C。

### 2026-08-22：8C 本地实现收尾

- 0010 migration、durable event/replay、lease/fencing、cancel、checkpoint、proof-based recovery、Worker/API
  与 package event query 已在工作树完成；八维 walkthrough 已进入 coverage ledger，coverage 仍 planned。
- 最新完整本地 pytest `1671 passed, 134 skipped`；真实 PostgreSQL 17、Linux package 和 exact-SHA 三 job
  仍是关闭门，公共成功前不进入 8D。

### 2026-08-23：8E Batch E 安全/部署入口设计

ADR-0063 将 8E 的公开交付边界冻结为 provider-neutral AuthPort、server-side opaque session、
RiftCoach Auth/RSO 分离、edge/static Web + API/Worker/PostgreSQL 单机 Compose，以及在线数据、
Artifact 和加密 backup 共用 deletion marker/restore erase 语义。后续原子顺序为 E1 Auth/session、
E2 edge security/limits、E3 Secret lifecycle、E4 backup/restore/erase、E5 packaging/observability，
然后才施工 Rift Awakening、Timeline、双语产品表面、Data Dragon asset/detail enrichment、Evidence/Trace、
Training 和 OP.GG useful-breadth/golden slice；8E 退出前执行跨模块 final visual QA。双语层保持 API/status
code 单一，不复制后端合同；当前 Timeline 高保真 V1 和截图不等于最终视觉签收。

该入口设计不引入 Auth/HTTPS/备份/部署代码，不读取 Secret 或调用外部服务；8E coverage 继续 planned，
必须等待设计 exact-SHA 公共三 job 后再进入 implementation。

### 2026-08-24：8E 视觉 Task 3 与 Batch E implementation 本地接续

- 视觉合同前置的 Task 3 已完成本地门，不改变 E1→E5 顺序：低对比 atmosphere/instrumentarium layers、
  typed route choreography、state-aware handoff 和 reduced-motion/mobile fallback 均由 React/CSS/SVG 完成。
- 在用户连续推进授权下，Batch E implementation 已进入 E1/E2/E3 的最小本地实现：opaque session/CSRF、
  bounded request/单机 rate policy、versioned SecretSource/key-last Worker composition。生产 Auth/RSO、
  PostgreSQL session、HTTPS、Secret Manager、backup/erase 与公网部署仍待后续原子批和公共门。
- 当前 8E coverage 保持 planned；本地 focused tests 通过但不替代独立 commit、完整比例回归和 exact-SHA
  `pytest`/`postgres-migrations`/`packaging-smoke`。

### 2026-08-24：Timeline 公共关闭与双语原子项

- `794032f/32682243568` 三 job 已关闭 verified Timeline DTO/API/UI；当前截图仍按 RQ-103 定位为高保真 V1。
- 下一原子项是 `zh-CN/en` product-surface foundation；先分离 UI catalog、canonical API code、Data Dragon
  entity locale 和 Coach report language，再进入资产 enrichment 与后续产品模块。
- ADR-0066/design/implementation plan 的零依赖 typed catalog、strict versioned storage、navigator fallback 和
  original-content boundary 已由 `8969aef/32683742229` 完成 design exact-SHA 公共门；当前进入实现，不进入 RQ-103。
- RQ-104/105/106 已在该 implementation 内增加独立双语 copy 审计、Portal→Account→Workbench URL/history、
  真实 Player Link 和母图分层 V1；当前本地门通过但尚无独立 exact-SHA 公共关闭。正式 OIDC/RSO、最终动效、
  RQ-103 资产细节和 8E exit 不随本批完成。
- RQ-107 指出 Web 尚未暴露 Conversation-bound Agent 追问。推荐的 bounded Coach 插入位置仍需用户裁决，
  因此 amendment 目前不重排 Data Dragon/Evidence/Training/OP.GG/final QA 的既有后序。

### 2026-08-25：foundation 后固定进入 RQ-108 Portal Motion Polish

- bilingual product-surface foundation 后来已由 `6084937/32757872792` 公共关闭；在该公共证据之前没有把
  `portal-motion-polish` 标为 in progress。用户随后按 RQ-109 授权，当前为 authorized/in progress。
- 公共关闭后的顺序先固定为 `foundation → RQ-108 portal-motion-polish`。RQ-108 是 8E 内部原子批，不是新主
  阶段或新 coverage group，也不等于 RQ-103 的 Data Dragon enrichment/跨模块 final visual QA。
- Portal 以已确认母图为构图源，水晶留在场景媒体内；透明原生 button 只覆盖点击区域。正常体验必须使用
  同源全帧 loop，poster 只负责首帧/降级；汇聚/burst 和独立 Account 场景幕切必须提供 mobile、Save-Data、
  reduced-motion、媒体失败、许可、性能和移除路径。Three/OGL/Anime 等新 runtime 仍需新的 Bad Case/ADR。
- RQ-108 关闭后再裁决 RQ-107 bounded Coach 与 RQ-103 asset/detail/final-QA 的相对顺序；不提前实现二者。

RQ-117 把 Account 地图的精度边界固定为“官方拓扑准确 + 地形有意概括”：三路、河道、双野区、双坑、基地和
左下蓝/右上红必须可辨，野区/墙体/塔/基地用 terrain masses、轮廓和符号节点表达，不伪造无法由公开参考证明
的微型细节。当前 v3 仍是未签收 preview，不能进入英雄合成或 runtime。ADR-0068、正式设计、implementation
plan 与八维 planned walkthrough 已在本地建立；必须先完成独立 design exact-SHA 公共门，再开始 runtime TDD。

RQ-118 又取代 RQ-108 的水晶放大/重绘细节：Portal source 保留确认母图原水晶、塔体和构图，只有全局 loop/
点击 burst 让原水晶运动；独立、放大、CSS 或贴图水晶均不得进入 poster、fallback 或 runtime。

RQ-119/120 把外部制片从“Kimi 默认”改为证据驱动三路线横评：生成式 Wan/Seedance/Veo/Luma/Runway，
确定性 HyperFrames/Remotion，以及生成式有机层 + 确定性结构合成。用户实测 Kimi v1 因 source/texture/
motion language rejected；本设计不安装 skill、不采购/调用模型，胜出工具仍需独立安全/许可/ADR 门。

design `b3b5280` / Actions `32812868683` 的三 job 已公共关闭该设计门；当前只交接 runtime Task 1 的
manifest/cover geometry/media policy TDD，8E coverage 继续 planned。

RQ-121 允许用户正规中转目录作为 official-first 之后的 secondary transport；目录 slug、`official` 标签和价格
不证明模型身份或能力，必须通过 mapping/capability/compression/privacy/region/error/billing/body-free 门。
该补充不改变 Task 1、8E/8F 顺序或外部调用授权。

runtime Task 1–3 已由 `1b146e6/32826953474`、`2111a78/32833608622`、`0198fc9/32836430378` 公共关闭；
Task 4 媒体审计器与预算门已由 `52def9c`/`d58ba15`、Actions `32841900909` 公共关闭；当前只进入 Task 5 三路线
bake-off，不进入 production media 或视频/relay 调用。

RQ-122 又明确付费槽位上限不是调研池上限。Task 5 已广筛现有 official/relay 视频目录：Wan 3.0 官方 access
由用户 UI 证明，Grok 3 relay 第三代存在但专用 schema 未齐。HyperFrames agent skill as-is 不准入；exact renderer
隔离 spike 证明 raw frames 可确定性闭合，但默认 MP4 seam/bytes 不合格。Wan/Veo 各一个真实样本随后均未过
source/seam/full-scene 门，后续 Seedance、即梦、Kling 与分层 proof 也未形成 production media。Wan first-frame
reopen 因错误 endpoint 在 HTTP 404/no-task 停止；用户随后按 RQ-146 明确转入官方/授权壁纸路线。下一步先做
Demacia 与 Bandle City WebM 的 region catalog/local preview 与来源/许可/格式/loop 门，不改变 RQ-108/8E/8F 顺序，
也不把用户或 Workshop 壁纸直接写入公开 runtime。
C proof 实作虽通过 clock/seam/grid/bytes，但实际仍是母图上的 HUD 覆层；RQ-126 已拒绝并恢复一次校正 A
comparator，禁止用机械指标绕过视觉失败。RQ-127 又把 comparator 固定为 near/mid/far、left/center/right
同时持续 breathing、medium-to-strong/evident/cool，并允许构图锚定小幅 camera parallax。
C proof 已由 `557dac1/32923151197` 公共关闭；corrected A 的 first-only/no-lastFrame 与 one-POST 三 digest 已冻结，
当前先过 executable preflight exact-SHA，不提前调用。
RQ-128 要求 failure 按 local/request/transport/output-quality/method 分层；corrected Veo 无 output 不构成质量或
方法否决。Vidu 只作 model/schema 控制变量；其首个 task 也 generic failed 后，只准一次删除 optional
seed、audio=true 的 Studio-contract request；UI 已证明 first-only/8s/1080p/16:9 与固定音频。仍失败则停止
换模型/API retry 并审计 relay task-id/official transport。
Studio-contract Vidu 随后成功但以 camera drift 取得全帧变化，sample rejected/model open。RQ-129 固定
locked-frame refined in-scene motion；下一最小变量实验保持成功 Veo first+last/model/transport/source，只改
精细 motion storyboard，未通过后才进入 Seedance 2.5。

RQ-130 又把“余额 ready”与“内容 ready”分成两个阻塞门。Dragon common log 已证实 refined 403 是
`$15.008 < $19.712` 的预扣失败，充值后余额 `$65.01`；task log 无隐藏任务。v5 spatial-orchestration 只改变
同一 Veo comparator 的 prompt/negative：遵守 official motion-only/单场景、锁定 camera/deep focus/source
linework，并把 left/center/right、near/mid/far 同时运动和八秒 phase/illumination/velocity 闭环写成单一编排。
source/schema/runner/唯一输出路径与 prompt digest 必须先独立提交并取得 exact-SHA 三 job，之后才 one POST/no retry。

v5 preflight `d57b026/32951125621` 三 job 公共成功后，唯一 task `task_I5...k9Mw` one POST 创建并在 159 秒/100%
generic failed；no output，故 output quality 与 method 仍 unknown/open。预扣 `$19.712` 已全额退款，钱包最终
`$67.01`；calls 6、production media 0。当前只关闭 upstream failure 与本地 terminal incident 审计，不重发或跳模型。

implementation/evidence `6084937` / Actions `32757872792` 已让 foundation 的 pytest、真实 PostgreSQL 与
Linux package 三 job exact-SHA 全绿；foundation 正式关闭。用户随后按 RQ-109 明确授权 RQ-108，当前进入
教学、ADR/设计、素材采用门和 TDD；8E coverage 继续 planned。

RQ-133：用户认可 Seedance 样本三个主体运动方向，但指出静区像雾层覆盖；当前尝试真正的视频编辑而非重抽。
Dragon 专用页面已确认公共名 `seedance-2-5`、`video_operation=edit`、`video_with_roles` 的 `reference_video`、
`duration=-1` 与 `aspect_ratio=adaptive`。Studio 主编排器虽显示视频参考，实际上传 input 只接受图片 MIME，故
不把它冒充 edit。v6.1 又按用户纠正采用 Video1 + immutable Image1 双锚点：前者保存已有 motion，后者锁原始
geometry/material/linework，只补道路、地面反射、建筑缝、远景空气和星图静区，原片永不覆盖。先新 exact-SHA
公共门，再按约 `$12.0191` 估算 one POST；edited sibling 劣化即拒绝，失败不盲重试。

v6.1 实际 submit 在 source GET 后以 HTTP 400 停在 task 创建前；费用 0、task id 空、无隐藏任务。原 runner
没有保存 error body，故当前只能定位到 request/schema 层，不能把旧 ratio 错误或双锚点猜测当成根因。新增
严格 sanitizer 与 revised runner 只修复诊断缺口；公共闭环且取得可证伪字段前不允许新 POST。

豆包工作标准套餐的一次 Seedance 2.5 comparator 已执行；其 Skill 抽首尾帧 + 母图重新生成而非 video edit。输出
因 source-first `0.407604`、seam `0.144582`、AAC、移动水印、暖金轨迹主导和整体 motion stack 不完整 rejected，
不重跑。RQ-134 要求三主体（尤其右侧）和整体环境都增强；光轨只保留为冷蓝/青蓝材质内运动的一层。下一正式
candidate 改用即梦官方 `智能编辑`，用户手动选文件，生成前仍需参数/积分/prompt readback。

RQ-135 固定即梦第一轮仅使用成功 MP4 + v2 母图：两者分别承担时间运动与视觉身份，额外审美图会增加 source
drift；高级编辑区域框选优先。v7 prompt SHA `edbc0d3...6f388` 同时强化三主体（右侧单列）和全局环境；当前
先 exact-SHA 公共关闭 preflight，用户之后手动选文件，Codex不再自动操作 file picker。

official 即梦 Smart Edit 已完成一次有效调用，但发生在上述 preflight batch public-close 前；历史明确记录该
顺序偏差。实际 compact prompt 与 design 长版分离。raw output 在镜头/三大区/九宫格方向上有希望，仍因
v2→first `0.889072` 与 seam `0.046536` fail；FFmpeg 只能修 fixed24/no-audio/BT.709/bytes，最佳后处理 seam
`0.042684` 仍 fail。calls `11`、production media `0`。下一门是本 evidence batch exact-SHA 公共闭环和 no-cost
identity fault split，不改变 8E/8F 顺序，也不授权相同配置再生成。

RQ-137 再固定短期排序：当前先完成 Portal Motion Polish 的 evidence、identity、source-side、runtime 与视觉门，
之后才恢复 GLM-5.3/Flash adoption 和 bounded Coach 等 Agent 产品项；不在一个未提交批中同时改变媒体和 Provider。

RQ-141 对 Seedance 2.5 v3 做了视觉否决：v3 的左 Rift、道路、中央 burst、右侧星图和 near/mid/far 环境没有形成
用户要求的持续全幕呼吸；中段还出现过曝白闪与横向直线。后续 source-side brief 必须把常驻基础运动与事件层
分开：道路/Rift 下方、右场、建筑接缝、地面反射、云和空气从首帧持续，burst 只沿中央垂直轴低幅蓄放约 2–3 秒，
并自然回到基线。该修订不改变 8E/8F 顺序、不允许降低 source/seam 门，也不立即授权新的付费请求。

RQ-156：补充 source 池的细粒度 provenance 记录，并把 Portal→Account handoff 做成可恢复 URL。Design Prompts、PPT/
Photoshop、Radix/shadcn、图表库、付费 UI 候选和 League Displays/Steam Workshop 各自记录 consumer 与采用/撤出门；
Portal 只新增所有本地细徽记的渐进 fallback 和 `from=wallpaper-lab` 返回标记，不提前实现 Workbench/Trace/Training，
也不改变 `production_media=0`。

同一 RQ-156 实现 hardening 进一步固定：新地区链接显式带 `surface=wallpaper-lab`，旧
`?region=` 仅为兼容别名；选区对当前 history entry 做 `replaceState`，push/popstate 复位滚动，generation 绑定 handoff；长页面视觉层固定在 viewport；Portal/Auth
使用语义 main、skip/heading focus、aria 状态和 intrinsic media 尺寸，并保留 poster/
mobile/reduced-motion/error fallback。该增量不新增主阶段或 coverage group，也不把
research candidate 当作 adopted media。

RQ-157/158 进一步修订当前 8E Portal presentation：13 区 `RegionIconId` 与可选 motion candidate 拆分，横向
Focus Rail 使用 Universe crest，选中 hero 才尝试本地高细节研究徽章；CTA 固定为通用“进入登录界面”，并由
selected identity 驱动有界 Portal→Account aperture/crossfade。Bandle Account 静态图替换 frame grab，但仍走
来源/分辨率/权利门。该增量不增加主阶段或 coverage group，不改变 Riot API routing、Workbench 和
`production_media=0`。

RQ-159 收口地区 presentation：13 区各自使用 RiftCoach 自写双语氛围句，正常界面移除 codec、时长、候选/动态
readiness 等内部审计词；真实媒体状态仍由 catalog/data attributes/evidence 维护。Portal→Account 采用 shared shell phase、
选中位置 aperture、Account 分层进入和延迟 focus，reduced-motion 即时提交。该增量不增加主阶段或 coverage group，
不声称官方引文，不改变 Workbench、Riot routing、来源/许可门和 `production_media=0`。

RQ-160 固定 Portal/Account 的双语 display-title 分行：完整句子继续作为语义 heading，视觉层使用显式两行，避免
不同 viewport 下随机断句或留下不自然空白。该排版合同已有 unit/E2E 与 desktop/390px live-DOM 证据，不新增阶段、
coverage group、依赖或产品能力，也不改变 8E in-progress 边界。

RQ-161 只补 Account presentation hygiene：桌面 panel 以独立 `top` 微调上移，移动端归零；Riot ID 与两个原生
select 统一 body 字体和字重，caption 统一可读字号。该增量有 computed-style E2E 与 live-DOM 证据，不改变
handoff transform、Auth、Riot routing、Workbench、媒体权利门或 `production_media=0`，也不新增 coverage group。

RQ-162 继续限定为 Portal/Account visual hygiene：用户提供的 Void crest 替换详细徽章候选，Universe crest 保持
确定性回退；两页右侧面板降低遮挡，Account 的地区背景和氛围层提高可读性。该增量不新增依赖、阶段或 coverage
group，也不改变媒体采用、Auth、路由、Workbench 或 `production_media=0`。

### 2026-08-31：RQ-163 Portal/Account → Agent 主线交接

Portal/Account 当前展示切片经用户确认已达到阶段性收口点，执行顺序回到 Agent 主线。该决定只改变 8E 内部的下一项
工作指针，不改变 0–8 主路线，也不关闭 8E 或把研究媒体当成生产媒体。

交接批先完成 README 事实版与学习/状态材料对齐，然后以 G53-0 无 I/O 可用性和配置审计作为下一候选。RQ-164 已完成
该本地静态审计但停在 blocked/deferred；后续仍须
独立完成 GLM-5.3 G53-1 至 G53-4、受限 Review Coach、Data Dragon/Evidence/Trace/Training、OP.GG useful
breadth/黄金切片、安全部署合规和 8E 退出，最后进入 8F。RQ-154 的两地区/第三地区文字保留为历史，已被 RQ-157–162
的 13 区 Focus Rail 方向取代；Workbench、Auth/RSO、Riot routing 和 `production_media=0` 不变。

### 2026-08-31：RQ-165 G53-1 普通 API 适配档案离线 TDD

RQ-165 在 RQ-164 的本地无 I/O 审计之后落地了第一批 Agent 主线实现：普通智谱 API 使用
`glm-5.3-flash` 与官方基址 `https://open.bigmodel.cn/api/paas/v4/`，不使用 Coding Plan
入口。不可变 profile 将 GLM-5.2 的 disabled thinking 与 GLM-5.3/Flash 的 enabled + low
隔离；Provider、capability probe、CLI 和回归测试共用该合同，工具回合的 opaque reasoning
仍拒绝回传。该批只关闭本地离线适配与回归，不改变默认模型、`.env`、Workbench、前端、Auth、路由或
`production_media=0`，也不构成账号/额度/领域质量/生产准入证据。下一检查点为 G53-2 exact-SHA CI；
8E 仍在进行，8F 尚未开始。

### 2026-08-31：RQ-166 G53-2 exact-SHA 公共 CI

G53-1 的隔离实现以精确提交 `0f97b92683e4981842e745a695864deb611bb630` 推送到 `main`；Actions
`33325222755` 的 head SHA 精确匹配，`pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 全部成功。
公共 pytest 为 `1912 passed, 145 skipped, 1 warning, 127 subtests passed`。该批没有修改 workflow、默认模型、
`.env`、Workbench、Auth、路由或媒体采用，没有读取/输出 Key，也没有真实 Provider/Riot/OP.GG 调用。

RQ-166 只关闭 G53-2 的公共可复现性；G53-3 有界协议门（最多三次真实调用）必须等待独立明确授权，G53-4
新鲜领域门、完整 8E 与 8F 仍未完成，`production_media=0` 保持不变。

### 2026-08-31：RQ-167 G53-3 有界协议门首次尝试

用户明确继续后，按最多三次的硬预算启动普通 API `adapter_protocol`。进程临时覆盖为 `zhipu`、普通 API
端点和 `glm-5.3-flash`，没有修改 `.env` 或默认模型。A1 在第 1 次请求返回脱敏 `authentication_failed`，
A2 被安全跳过；`calls_used=1/3`、`admitted=false`，没有重试或追加调用。

脱敏结果已通过 schema 校验并保留为独立文件；该错误码不能区分 Key 无效、权限不足或账户/端点接缝错误，
因此 G53-3 未通过，也不产生领域质量证据。下一步先确认凭证接缝，再由用户决定是否重开同一门；不进入 G53-4，
`production_media=0`、Workbench 和完整 8E/8F 边界不变。

### 2026-08-31：RQ-168/169 G53-3 重开通过

前次 Key 已确认被删除；用户创建新的普通 API Key 并修正 `zhipu`、普通 `/api/paas/v4/` 端点和
`glm-5.3-flash` 配置后，按原 3-call 上限重开。A1 结构化合同 1/1、A2 Agent 工具往返 2/2（1 次 ToolCall/执行）
均通过，`admitted=true`。脱敏结果 SHA-256 为
`1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`；该证据只关闭协议接缝，G53-4、领域质量、
生产成熟度和 8F 仍保持独立闸门。

### 2026-08-31：RQ-171 GLM-5.3-Flash 适配器修复与 G53-5

RQ-170 的并行 ToolCall 首错被确认是中立 Zhipu Adapter 的批量接缝缺口，旧领域考卷和结果不得重写。按用户
授权，Flash 隔离 profile 改为 `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`；
`reasoning_content` 仅在内部工具回放链路中保留，多个合法 ToolCall 按 API 顺序进入 AgentLoop 逐个受控执行，
能力矩阵仍不宣称并发。新的 `g53-5-fresh-flash-capability-gate` 需要独立身份、有界预算和脱敏结果，覆盖文本/思考、
结构化、工具批次、上下文与 Agent 链路；真实 Provider 测试尚未执行。该准备不改变 8E/8F 顺序、默认模型、
`.env`、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-172 G53-5 全能力矩阵真实观察

G53-5 新实验已在 dirty worktree 上完成 `11/11` 次真实调用、`46,151` tokens，8 个案例中 `7/8` 通过。adapter
core、AgentLoop 的有序多 ToolCall/思考回放、domain development、vendor text stream 与 vendor multimodal 均有
观察证据；F7 vendor tool_stream 在 `max_tokens=512` 以 `incomplete_chat_response`/`length` 结束，不足以证伪能力；
F4 缓存因 `cached_input_tokens=0`、`cache_status=unproven` 仍未证明，F8 仅为 vendor-only 观察。结果
`production_admitted=false`、`public_ci_confirmed=false`，因此不关闭 Stage 8/8E、生产准入或 8F。下一步等待用户
决定 Agent 主线下一项；不重跑 G53-4，不改默认模型、Workbench、Auth、前端、`production_media=0` 或既有路线顺序。

### 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

为诊断 RQ-172 F7 在 `max_tokens=512` 下的 `incomplete_chat_response`/`length`，新增独立 follow-up，唯一变化
是将上限调至 2048，不修改或覆盖 RQ-172/旧结果。experiment_id 为
`49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`；父矩阵 experiment 为
`4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`，父结果 SHA 为
`bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。唯一 `1/1` 调用消耗 `557` tokens，
`finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source identity stable、`cached=0`。
结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json` 的
SHA-256 为 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`。

该结果仅标记 `vendor_raw_transport_only`，`production_admitted=false`、`public_ci_confirmed=false`；不证明
provider-neutral streaming、Agent 生产、领域采用或公共 CI。Stage 8/8E 继续 `in_progress`，下一步等待用户决定
Agent 主线下一项；不改默认模型、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-176 Flash-only 产品运行时晋级（本地接线）

Flash-only 是当前产品实现方向，不是“等比较后再决定”的候选状态。唯一注册的
`glm-5.3-flash-runtime-v1` 已从组合根显式绑定到 Worker、Runtime、Agent/工具/Harness、Provider、运行时策略和
Trace；精确 Flash 未绑定档案时在组合阶段直接拒绝，避免 Skill 的 30 秒质量资源门与 Flash 的 90 秒执行窗产生
隐式分裂。Flash 运行时使用 120 秒传输、2048 输出上限、`temperature=1`、`top_p=0.95` 和 SDK retries=0；
Worker lease/heartbeat 默认 360/60 秒。`.env.example` 与 Compose 模板已对齐 Flash，真实 `.env` 不由本批改动。

这只改变 8E 内的 Agent 实现指针，不改变主阶段顺序，也不把本地回归写成生产成熟度。新实现仍须先取得自己的
exact-SHA 公共 CI，在同一 SHA 重取 G53-3，之后执行 G53-7、黄金切片和安全/部署/合规闸门；GLM-5.2 可显式
回退，旧证据不可覆盖，Portal/Account/Workbench/Auth/路由及 `production_media=0` 不变。

### 2026-08-31：RQ-178 G53-7 A/B 身份边界

为避免“写入脱敏结果后 `HEAD` 改变”造成协议身份自引用，G53-7 采用两提交模型：实现与协议执行代码固定在
A，脱敏结果只能由 A 的直接单父子提交 B 新增。schema 1.1 admission 的本地预检会核对 A/B、各自 CI 见证、
当前 `HEAD=B`、B 的 Git blob/canonical-LF 摘要、Provider/model 与三调用通过合同，并拒绝改写既有证据或混入
代码。RQ-178 仅完成该无 I/O 接缝和 `53 passed` 回归；新的 A′公共 CI、同 SHA G53-3、B′及后续领域门仍按
8E 顺序执行，不能据此宣称 8E/8F 或生产准入完成。

### 2026-08-31：RQ-179 A 身份公共冻结补充

两提交模型的最终实现 A 已固定为 `9e6d78be51c3a5c512b67f83d2849f9b1261cf77`，Actions run
`33378687984` 三 job exact-SHA 通过。为让公共 runner 真正验证历史父子/blob/diff 身份，CI checkout 读取完整
Git 历史；这不放宽生产 `HEAD=B` 门，也不改变 Stage 8/8E/8F 顺序。新 G53-3、只新增证据的 B、B 的 CI 与
G53-7 仍是后续独立闸门。

### 2026-08-31：RQ-180 G53-7 真实领域尝试边界

RQ-179 的 A/B 证据链完成后，用户授权在干净 LF checkout 上执行一次 G53-7。协议调用 3/3，领域调用 2/12，
累计 5/15 calls、领域 3505 tokens；首例因 `provider_response_invalid/incomplete_chat_response` 停止，后两例
按首错跳过，`admitted=false`。脱敏结果 canonical-LF SHA-256 为
`21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，本地承载提交 C=`9157cde…` 未推送、未有公共 CI。
结果没有保存底层 finish reason、Key、正文或 reasoning，不能把它进一步定性为 `length`，也不产生模型一般质量或生产成熟度结论。
Stage 8/8E 仍 `in_progress`，当前停止自动重试；若继续须另立版本化的 Flash 响应完成/截断诊断，不覆盖旧证据。

### 2026-08-31：RQ-181 响应完成度诊断补充

RQ-180 的聚合错误不足以判断供应商结束原因。用户授权一次独立、正文零留存的诊断后，首个冻结案例在
`agent_initial` 回合记录到有效 Usage（input `2220`、output `2048`）、原始 `finish_reason=length`、正文为空、
reasoning 非空且无 ToolCall；适配器因此按 fail-closed 合同返回 `incomplete_chat_response`，未形成 normalized/settled
response。脱敏结果的 canonical-LF SHA-256 为
`050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，experiment 为
`b1e4a1fc51bed23803b5f94acbd2a652330d5847061dbb7b60022c88da4ff1b9`，实现基线为
`7cb66d218389c0e7d7aa7b2b1969a4678402f857`，诊断代码为 `447c11e85b6da53fe678d68e25d96b589c0d6ca2`。

该证据只确认本次 2048 输出额度先被最大推理档案耗尽，不覆盖 RQ-180 的旧回合，也不把模型或账号判为不可用。
它不改变 8E/8F 顺序、生产准入、Portal/Account/Workbench/Auth/路由或 `production_media=0`；下一项是先设计
版本化响应完成策略并补离线 TDD，是否实现需新的明确授权，不自动提高全局上限或重跑领域门。

### 2026-08-31：RQ-182 版本化响应完成策略

用户明确继续 canonical 的下一项后，8E 新增纯离线、精确身份绑定的响应完成策略与 TDD。严格 Flash v1 仍使用
当前 runtime profile 的 2048 输出上限和零额外调用；8192/一次 fresh-recovery 只作为未注册候选，用于验证
`length + 空正文 + 非空 reasoning + 0 ToolCall` 的白名单形状，不会自动发起第二次请求。该项不改变主阶段顺序，
不改消息/AgentLoop/Trace/预算合同，也不替代 G53-7、黄金切片、安全部署合规或 8F；后续候选启用必须重新取得
exact-SHA 公共证据与独立授权。

### 2026-08-31：RQ-183 候选 fresh-recovery 合同

RQ-183 继续 8E 的同一 Agent 主线，把候选运行时、底层调用尝试、预算和脱敏 Trace
做成独立离线合同。候选 profile 精确绑定 `zhipu/glm-5.3-flash` 与
`glm-5.3-flash-runtime-v2-candidate/2.0.0`，计划最多包含序号 1 的 `primary`
和序号 2 的 `fresh_recovery`；第二个槽位只在候选策略重新判定白名单形状后出现，且
计划永远标记 `execution_allowed=false`。账本把每次预留都视为一个底层调用，结算
实际 token/时间，失败或超预算也不抹掉消耗；独立 Trace 不修改既有 Runtime Trace
schema，也不保存 Prompt、正文、reasoning、工具参数、Key 或 request ID。

这只是 `30 passed` 的本地合同实现，不是恢复能力或生产准入。严格 Flash v1 的
2048/零额外调用、默认模型、Workbench、Portal/Account、Auth、路由和
`production_media=0` 均保持不变；后续仍需新 exact-SHA 公共 CI、同 SHA G53-3、
单独真实诊断授权及成本/延迟/失败审查，8F 不提前开始。

### 2026-08-31：RQ-184 候选合同公共证据链

RQ-184 已完成 RQ-183 合同的公共可复现性和同 SHA 协议接缝：实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654`
的 Actions run `33405110692`，以及只新增脱敏结果的直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 的
Actions run `33405881172`，三 job 均成功。同一 A checkout 的 G53-3 严格 `3/3` 调用通过（A1 `1/1`、A2 `2/2`，
SDK retries `0`、`admitted=true`）；结果 `code_sha` 为 A，A/B 无 I/O 预检通过，结果 canonical-LF SHA-256 为
`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

该项只提升候选合同的公共证据，不注册 `glm-5.3-flash-runtime-v2-candidate/2.0.0`，不执行 fresh-recovery 或
G53-7，不改变严格 Flash v1 的 2048/零额外调用、默认模型、产品模块或 `production_media=0`。下一项仍需用户单独
授权一次有界候选恢复诊断，并审查成本、延迟、失败与脱敏 Trace；完整 8E/8F、安全/部署/合规顺序不变。

### 2026-08-31：RQ-185 候选恢复诊断中断

RQ-185 记录了两次独立的有界候选恢复诊断启动：隔离诊断代码为
`76de589a128b7a71f1def3316da3f30ebdd3a4c8`，实现基线为
`eca01ce1393286dbbe83992c2985f600ea2b30b0`。两次都只进入 `primary` 首回合，
没有发送 `fresh_recovery`；第一次沿用 120 秒传输边界并在约 60 秒无返回时中止，
第二次使用全新结果名和临时 20 秒客户端传输上限，仍在约 60 秒内未结束后终止。
两次都没有可观察响应、Usage、finish reason、Trace 或结果 JSON，不能把请求是否抵达供应商、
费用或模型能力写成结论。候选继续保持未注册，严格 Flash v1 的 2048/零额外调用不变；
后续若要重开，必须先复核传输/代理边界并取得新授权，不得自动重试或提前进入 G53-7/生产收口。

### 2026-09-01：RQ-186 请求级截止结果

RQ-185 的 20 秒客户端值被每请求 90 秒 timeout 覆盖；隔离诊断器现已把受校验的请求级 deadline 写入 SDK
payload。代码提交 `94629161c5d3230629210444b5a1a38212799997` 通过 `82 passed` 相邻回归；唯一 30 秒
primary 在约 30.141 秒后以 transport timeout 安全关闭，未产生响应、Usage 或 fresh-recovery。脱敏结果
canonical-LF SHA-256=`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`。
这只证明诊断截止生效；30 秒低于候选 90 秒窗口，不构成模型能力拒绝、候选激活、G53-7 或生产成熟度。
v1.3 的 8-Core/8-Advanced、完整 8E/8F、安全/部署/合规和 `production_media=0` 顺序均不变。

### 2026-09-01：RQ-187 完整候选窗口结果

RQ-186 之后按用户授权执行一次完整候选窗口：请求级 `timeout_s=90`、`max_tokens=8192`、SDK retries `0`，
只发出一个 primary。90.188 秒后仍以 transport timeout 安全关闭，无响应、Usage、finish reason 或
fresh-recovery；脱敏结果 canonical-LF SHA-256=`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，
由本地提交 `50ce5be` 承载。该结果排除 30 秒窗口过短，但不能在无响应时区分传输链路与服务端生成延迟，
不增加模型/候选/领域能力，也不改变 8-Core/8-Advanced、完整 8E/8F 或 `production_media=0` 边界。

### 2026-09-01：RQ-188 候选传输/生成拆分结果

在用户新授权下，隔离诊断器只执行固定 `3/3` 次真实调用（SDK retries `0`）：合法 Flash
`thinking=enabled`/`reasoning_effort=low` 最小控制、冻结上下文 256 token max 同步请求、冻结上下文 8192 token max
流式首块请求。三路均 observed；同步两路有效 Usage 且 `finish_reason=length`、正文为空、reasoning 非空；流式路
约 `687ms` 观察到首个 reasoning chunk 后按合同关闭。正式结果 SHA-256 为
`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，代码/source identity 为
`b67b4500ebdbff934e470fd92c1461184aa7c49b`。该证据只把 endpoint/model 路径确认到“可达且已开始生成”，不升级
8-Core/8-Advanced、候选、领域或生产能力；严格 Flash v1 仍为 2048/零额外调用，下一项是 evaluation-only
`candidate-output-budget-calibration`，完整 8E/8F、安全/部署/合规与 `production_media=0` 顺序不变。

### 2026-09-01：RQ-189 候选输出预算校准

同一冻结上下文的三次独立调用显示：`reasoning_effort=low`、`max_tokens=2048` 在 28.344 秒内以
`finish_reason=stop` 产生可见正文（输出 724）；`low+8192` 与 `max+8192` 两路在约 45 秒请求截止内没有
同步响应。该观察支持“运行档位要同时考虑推理档位、输出预算和传输形状”，但没有证明 8192 需要更长时间、
也没有证明模型一般质量。v1.3 仍要求 8-Core/8-Advanced 分离、候选证据和生产闸门逐项通过；严格 Flash v1
继续 2048/零额外调用，下一步只做流式可见正文与 `clear_thinking` 的 evaluation-only 探针。

### 2026-09-01：RQ-190 候选流式可见正文探针

在连续推进授权下，项目以固定冻结上下文分别运行 `clear_thinking=true` 与 `false` 的单路流式请求，均使用
`thinking=enabled`、`reasoning_effort=low`、`max_tokens=2048`、SDK retries `0`。两路都先观察 reasoning，再在
约 2.547 秒/3.875 秒出现首个非空正文并立即关闭；没有把未观测的终态 Usage 当作零值，预算状态明确为 unknown。

该证据只把“短同步可完成”扩展为“流式可在短时间给出首个可见正文”，不改变 8-Core/8-Advanced 分层，不注册候选，
不把 `clear_thinking` 写成已验证的跨轮因果，也不接入产品默认、Workbench、Portal、Account、Auth 或生产媒体。下一项
继续验证完整流式终态与 Usage，随后再决定是否值得设计 provider-neutral 装配接缝。

### 2026-09-01：RQ-191 完整流式终态证据

RQ-191 在 `clear_thinking=false`、低推理、2048、stream 形状下完整读取一条冻结上下文流；首块 2.203 秒、首正文
3.531 秒、终态 24.140 秒，`finish_reason=stop` 且 Usage valid（1973/652/0）。这补足了 RQ-190 主动早退留下的
终态缺口，但仍不是一般质量或生产准入证据，也没有验证跨轮思考回放、工具流或 provider-neutral runtime 接入。
8-Core/8-Advanced 分层、候选未注册、严格 Flash v1 2048/零额外调用和 `production_media=0` 均不变；下一项转为
离线流式装配合同。

### 2026-09-01：RQ-192 提供商无关流式装配合同

RQ-192 在 v1.3 的 8-Core/8-Advanced 分层内新增一个候选适配接缝，但不把高级流式能力强塞进生产：
供应商分块先归一化，单次装配器要求真实 EOF、合法终止和有效 Usage，工具/正文互斥并对 JSON、序号、身份、
资源和失败状态做 fail-closed 校验。实现与 29 项聚焦测试均为本地证据；Trace 采用白名单，内部结果默认 repr
不暴露正文或工具参数。

该合同不注册 GLM-5.3-Flash 候选、不改变严格 Flash v1 的 2048/零额外调用、不打开产品 streaming，也不改变
8-Core 必需项、8-Advanced 证据门、Portal/Account/Workbench/Auth、部署/合规或 `production_media=0`。下一项
仍是同一实现 SHA 的公共 CI 与供应商一致性测试；8E 未完成，8F 未开始。

### 2026-09-01：RQ-193 智谱流式适配器一致性接缝

RQ-193 在 v1.3 的候选接缝范围内完成测试内 provider conformance：用 fake OpenAI-compatible 智谱分块验证
正文/reasoning、工具别名和参数分片、坏形状与未知工具、空 choices、model/terminal 边界、异常 `abort()`、
正文空白保留及 Trace 脱敏，再与既有同步 `ZhipuProvider.chat_stream()` 的 fake-client 结果逐字段对照。
conformance 聚焦为 `13 passed`，不改变任何生产 Provider 或能力标记。

提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA 公共 CI run `33489903978` 已三 job 全绿且 head_sha
精确匹配，并包含全部 Trace 脱敏断言。该证据只完成候选接缝的
公共可复现性，不把高级 streaming 强塞入 8-Core 生产要求；候选仍未注册，严格 Flash v1 仍 2048/零额外调用。
公共验证后，下一项是候选接线裁决（是否接入 runtime、范围、预算/Trace/回退/失败门），8E 仍 `in_progress`，
8F 尚未开始，`production_media=0` 不变。

### 2026-09-01：RQ-194 候选级显式智谱→中立适配接缝（公共闭环完成）

RQ-194 继续遵守 v1.3 的 8-Core/8-Advanced 分层：这是候选级、仅显式调用的高级适配接缝，不是 8-Core 生产必需项，
也不把 streaming 强制升级为默认能力。早期设计中的占位模块/API 已落为
`app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamAdapter`；`ZhipuProvider.stream_adapter(*, tool_stream=False)`
是显式工厂，`stream_events()`/`assemble()` 分别负责事件翻译和单次完整装配。

本地实现把可信 provider runtime profile 的输出上限（1–8192）与请求 cap 绑定，只能收紧预算；默认要求 request identity，
Trace/错误只保留 SHA-256 摘要，不含 Prompt、正文、reasoning、工具参数、Key 或 SDK 对象。单流必须正常 EOF、合法 terminal
并有有效 Usage；取消、迭代器/翻译/关闭异常均 `abort()`/fail-closed，不 retry、不 recovery、不执行 ToolRuntime。
只允许 fake/local evidence；`capabilities.streaming` 继续 `False`，严格 Flash v1 仍 2048/零额外调用，默认模型、AgentLoop、
Workbench、Portal、Account、Auth、路由、预算/Trace 与 `production_media=0` 均不变，候选未注册。

提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588` 已三 job 全绿且 head_sha 精确匹配；
`tests/test_zhipu_stream_adapter.py` 聚焦 `20 passed`。这只证明候选接缝公共可复现，不等于产品 runtime 接线或生产准入。下一门是独立
裁决候选 runtime 接线范围；RQ-194 不改变 Stage 8/8E 的 `in_progress` 顺序，
8F 尚未开始，不提前进入 G53-7、黄金切片或生产准入。

### 2026-09-01：RQ-195 候选 runtime 接线架构评审（历史状态）

RQ-195 继续遵守 v1.3 的 8-Core/8-Advanced 分层：候选 streaming 接缝仍是受控高级实验，不能因为本地 adapter
和公共 CI 通过就写成 8-Core 生产能力。评审确认完整流装配与候选恢复资格是两种不同合同：`assemble()` 对
`length`、缺终止、缺 Usage 和异常路径 fail-closed，不能把异常当作恢复资格。

因此下一设计门只冻结隔离的 `CandidateStreamEvaluationHarness`、四元身份绑定、`BoundaryObservation` 状态机、
候选 ledger/Trace 投影和回退矩阵；不改 `LLMProvider`、`AgentLoop`、默认模型、`capabilities.streaming`、Workbench、
Portal、Account、Auth、路由或生产媒体。候选 profile 仍未注册且 `execution_allowed=false`，严格 Flash v1 仍为
2048/零额外调用；8E 继续 `in_progress`，8F 尚未开始。当时下一精确项为 `candidate-runtime-wiring-design / pending`，
现已由 RQ-196 更新。

### 2026-09-01：RQ-196 候选 runtime 接线设计

RQ-196 在用户基本决定采用 GLM-5.3-Flash 后完成候选 runtime wiring design。按照 v1.3 的 8-Core/8-Advanced 分层，
Flash 记录为唯一主力候选目标，但本轮仍是受控高级实验设计，不把 streaming、recovery 或 8192 上限写成 8-Core 生产能力。

本轮冻结 `CandidateRuntimeBinding` 四元身份、body-free `BoundaryObservation`、共享事件校验、完整流/不完整流分流、
隔离 v2 transport 和独立 Trace 投影；候选预算为最多 2 attempts、1 次额外调用、32,000 input、16,384 output、180,000ms，
unknown Usage 不得当零，当前 `execution_allowed=false`。严格 Flash v1 2048/零额外调用、默认 Runtime、
`capabilities.streaming=False`、产品模块和 `production_media=0` 不变。

当时唯一下一精确项为 `candidate-boundary-observation-contract-implementation / pending`；该门已由 RQ-197
推进，8E 仍进行中，8F 尚未开始。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 按 v1.3 的 8-Core/8-Advanced 分层完成了候选高级实验的离线实现门，但没有把候选写成 8-Core
生产能力。新增隔离 `app/evaluation/candidate_stream_contract.py`，提供精确 candidate binding、body-free
`BoundaryObservation`、不可变状态快照、字段 presence 聚合、候选 v2 注入式 transport port 和独立 Trace
allow-list；`ProviderStreamEvent` 的显式 null/缺失标记与完整 assembler、智谱翻译共同使用事件级校验核心。

本地失败矩阵覆盖完整 `stop`/`tool_calls`、`length` reasoning-only、缺 EOF/terminal/Usage、身份/序号/工具/预算/
时钟/关闭异常和状态伪造；不完整或异常流均 fail-closed，不构造 `ChatResponse`，unknown Usage 不当零。候选仍
`activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 2048/零额外调用，
`capabilities.streaming=False`，默认模型、AgentLoop、Workbench、Portal、Account、Auth、路由和
`production_media=0` 不变。聚焦/相邻回归为 `163 passed`，compileall、diff check、governance 已通过；全量本地
首错是缺少 PostgreSQL 测试环境变量 `RIFTCOACH_TEST_DATABASE_URL`。

当前唯一下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-public-ci / pending`：
先取得同一干净实现提交的 exact-SHA 公共 CI，再另行裁决 candidate harness、fresh-recovery、G53-7、黄金切片和生产准入。

### 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

RQ-197 实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 已取得 Actions run `33507627615` 的
exact-SHA 公共证据；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，公共 pytest 为
`2178 passed, 145 skipped, 1 warning, 127 subtests passed`。这只是 8-Advanced 候选实验的公共可复现性证据，
不把候选写成 8-Core 生产能力；候选仍未注册、`execution_allowed=false`，严格 Flash v1、默认模型、产品模块、
`capabilities.streaming=False` 与 `production_media=0` 均不变。

收口后的唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
本轮暂停，后续需用户明确继续。

### 2026-09-02：RQ-199 隔离候选评估台设计

RQ-199 继续遵守 v1.3 的 8-Core/8-Advanced 分层：候选评估台是 8-Advanced 的受控设计，
不是把流式恢复能力强塞进 8-Core 生产。新增 ADR-0077、实现计划和学习 walkthrough，
采用 candidate-only staged ledger（primary I/O 前预留，真实边界观察后才重算 policy）、
单次 normalized event pump（observer 与 assembler 共用）和独立 body-free receipt；拒绝
sentinel snapshot、首回合后才 reserve、隐式 Provider/AgentLoop streaming 和产品 Trace
迁移。当前 activation 仍关闭，候选 `execution_allowed=false`，严格 Flash v1 2048/零额外
调用、`capabilities.streaming=False`、默认模型和 `production_media=0` 不变；没有真实 API、
fresh-recovery、G53-7、黄金切片或公共生产准入。

设计门完成后的唯一下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`；
后续实现仍须 fake/local、聚焦测试和 exact-SHA 公共 CI，真实候选执行与 8F 继续独立排队。

## 2026-09-02：RQ-200 候选评估台实现边界

RQ-200 继续遵守 v1.3 的 8-Core/8-Advanced 分层：只把 RQ-199 的候选协调设计落成
fake/local evaluation seam，不把流式恢复写入 8-Core 生产。实现使用 candidate-only staged
ledger、单次 normalized event pump、临时内存 assembler 和独立 body-free receipt；完整结果
必须经显式 evaluation consumer 短暂交付，不完整流或未知 Usage 不得伪装成产品响应或可用余额。

本地 harness 聚焦 `15 passed`，与边界观察、流装配和旧恢复合同相邻回归 `102 passed`，并通过
编译、diff check 与治理预检。activation 仍 disabled，候选不注册、不打开
`capabilities.streaming`，严格 Flash v1、默认模型、产品 Runtime、Portal、Account、Workbench、
Auth、路由和 `production_media=0` 不变；没有真实 API/Key、recovery、G53-7、黄金切片或 8F 证据。
当前唯一下一门为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-public-ci / pending`，
先取得同一干净提交的 exact-SHA 公共 CI，再另行裁决高级候选是否继续。

## 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 Actions run `33536168224` 已三 job
全绿且 `head_sha` 精确匹配，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
这只把候选评估台提升为可公共复现的 8-Advanced evidence，不改变 8-Core 生产矩阵；候选仍未注册、
`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1、默认模型、产品 Runtime、
Portal、Account、Workbench、Auth、路由与 `production_media=0` 均不变。下一精确门为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`，
只允许在单独授权后复核 recovery 的传输/预算/失败边界。

### 2026-09-02：RQ-202 对 8-Core / 8-Advanced 边界的补充

RQ-202 仍归入 8-Advanced 的受控候选证据：只修补隔离评估台的回执派生一致性和单次 90 秒
截止，不把 fresh-recovery、streaming 或 8192 上限提升为 8-Core 生产能力。旧同步诊断器不再
作为新版本基础，unknown Usage 继续不得当零；候选 activation 仍 disabled，`production_media=0`
和 8E/8F 的生产、合规、黄金切片闸门不变。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`，
必须再次单独授权。

## 2026-09-02：RQ-203 版本化候选 recovery 诊断设计边界

RQ-203 将候选 recovery 继续留在 8-Advanced 受控实验层：新增独立的
`glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0` 设计，绑定候选身份、版本与 SHA，
并冻结 `reserve → observe → settle`、未知资源三态、分段延迟、失败第一现场和 body-free 原子回执。
这只是评估证据设计，不是 8-Core 的产品部署、合规、评测或 portfolio 能力；不把候选包装成产品
`LLMProvider`，不打开 `capabilities.streaming`，不改变严格 Flash v1、默认模型、AgentLoop、Portal、
Account、Workbench、Auth、路由或 `production_media=0`。实现、真实 recovery、G53-7、黄金切片、生产准入
和 8F 仍需各自的证据与授权，不能因设计完成而提前宣称 Stage 8 完成。

下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`。

## 2026-09-02：RQ-204 版本化候选 recovery 诊断实现边界

RQ-204 继续遵守 v1.3 的 8-Core/8-Advanced 分层：只把 RQ-203 的版本化诊断协议落成
candidate-only fake/local evaluation seam，不把 recovery、streaming 或 8192 输出上限提升为
8-Core 产品能力。实现使用 primary I/O 前 reserve、一次 normalized event pump、body-free
observer/receipt、Usage/预算/费用三态、失败类别和 create-only canonical JSON；不包装为
`LLMProvider`，不注册候选，不修改 AgentLoop、默认模型、统一 Runtime Trace 或前端。

新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归 `82 passed`，
并通过编译、静态 no-I/O/import 与 diff check。activation 仍 disabled，严格 Flash v1 2048/零额外
调用、`capabilities.streaming=False`、`production_media=0` 和 8E/8F 的生产、合规、黄金切片闸门
不变；没有真实 API/Key、第二次 recovery、G53-7、黄金切片或生产准入证据。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`；
先取得同一干净实现提交的 exact-SHA 公共 CI 与协议 dry-run，不能把本地 fake 证据写成生产成熟度。

## 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环边界

RQ-205 完成 RQ-204 的 exact-SHA 公共 CI 和 fake/local 协议演练：提交
`90242822df0e47304700644572bc12f0a3aa88ad` / Actions `33598541029` 三 job 全绿，公共 pytest
`2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`；
前端契约、构建、E2E、RAG、治理与打包冒烟均通过。该证据只说明 8-Advanced 候选评估接缝可复现，
不把 recovery、streaming 或 8192 输出上限提升为 8-Core 产品能力。

本地协议演练只使用 fake transport，一次 primary 调用即可生成临时 body-free 回执；没有读取 Key、
真实 API、第二次 recovery 或持久结果。候选仍 disabled、`execution_allowed=false`、
`capabilities.streaming=False`，严格 Flash v1、默认模型、AgentLoop、统一 Trace/预算、Portal、
Account、Workbench、Auth、路由和 `production_media=0` 不变；8E/8F 的生产、合规、黄金切片闸门不变。

下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
真实 recovery 只能在新的明确一次性授权后执行。

## 2026-09-02：RQ-206 版本化候选 recovery 诊断真实观察边界

RQ-206 在同一干净隔离工作树只执行 1 次有界真实 primary：提交
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run `33603143606` 三 job exact-SHA 全绿。
普通智谱 `zhipu/glm-5.3-flash` 流观察到 reasoning、可见正文、`stop` 和 EOF，但首个可见正文在
`151453ms`、总延迟 `175875ms`；Usage 缺失、close 失败，90 秒 attempt 门在晚到事件中触发，
因此回执为 `fail_closed / elapsed_limit`，没有第二次 recovery。持久 body-free 回执 SHA-256 为
`2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`（`4355` bytes）。

该观察属于 8-Advanced 候选证据，不是 8-Core 产品能力，也不是 API/Key、模型一般质量、领域准入或生产
成熟度结论；候选仍 disabled、未注册，严格 Flash v1、默认模型、产品 Runtime、前端、
`production_media=0` 和 8F 边界不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
先离线设计/测试硬墙钟取消、流关闭与 Usage/终态尾帧处理，再另行裁决真实重测。

## 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧边界

RQ-207 只推进 `8e-productization` 的 8-Advanced candidate-only 证据：以显式
`CandidateStreamSession`/`CandidateStreamDeadlineSupervisor` 固定 attempt 起点的绝对 monotonic 墙钟，
并为协作式取消、幂等关闭、迟到事件抑制及终态/Usage 尾帧建立可测试合同。四文件聚焦回归（deadline 10、v2 24、
real 8、adapter 25）统一为 `67 passed`；
这不改变 8-Core 与 8-Advanced 的分层，不新增或重排主阶段，也不接入产品默认、Runtime、路由、
`capabilities.streaming` 或其他生产模块。

legacy `open_stream() -> Iterable` 继续兼容，但 hard mode 仅接受显式 session opener；若显式 opener 返回
legacy iterable，兼容性校验在 opener 返回后执行并 fail closed。同步 opener 的阻塞，以及 SDK `close()` 是否
非阻塞/能唤醒 `next()`，仍是公共 CI/真实重测闸门；Usage 缺失保持 unknown/null，禁止合成零值、重试或第二次请求。
Stage 8/8E 仍为 `in_progress`，候选仍 disabled、未注册。

> 历史快照（RQ-207 本地实现完成时）：当时的下一精确 checkpoint 曾为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
> RQ-208 已完成该公共 CI，当前唯一指针以最新 RQ-208 段落为准。

## 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

RQ-207 的候选硬墙钟会话、取消/关闭资源合同与 Usage 尾帧离线实现，已在提交
`015b022bfce6d03452f753794ac126a377f8355b` 取得 Actions run `33613113829` 的 exact-SHA 公共 CI 闭环；
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均为 `completed/success`。本地四文件聚焦回归为
`67 passed`，公共 pytest 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为
`201 passed, 1 warning`。

该公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 的非阻塞/唤醒能力，也不构成模型一般能力、
领域采用或生产成熟度结论；同步 opener 永久阻塞与 SDK close 无法唤醒 `next()` 仍需真实 provider 验证。候选仍
disabled、未注册，`activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`，
严格 Flash v1 2048/零额外调用，默认模型、产品 Runtime、路由和 `production_media=0` 不变，Stage 8/8E 继续
`in_progress`。

> 历史快照（RQ-208）：当时的下一精确 checkpoint 为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
> 公共 CI 已闭环。当前指针见下方最新 RQ-212 段落。

## 2026-09-02：RQ-209 候选真实流硬墙钟观察的分层边界

RQ-209 只补充 8-Advanced candidate-only 的真实传输证据，不改变 v1.3 的 8-Core/8-Advanced 分层。按用户
“继续”仅发送 1 次普通智谱 `zhipu/glm-5.3-flash` primary；候选显式请求 Usage，attempt 90 秒、transport
120 秒、`max_tokens=8192`、SDK retries=0。首事件/打开计时为 `3421ms`，reasoning 非空；`90015ms` 触发
应用硬墙钟，未见可见正文、terminal、EOF 或 Usage，最终 `fail_closed / elapsed_limit`，组合会话
`close_state=failed`，费用 unknown，无 recovery/重试。

body-free 回执由本地证据提交 `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存，文件 SHA-256 为
`56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`、大小 `4342` bytes；公共 CI 尚未宣称。
`close_state=failed` 仅是组合会话清理结果，不能归因到供应商 response、迭代器或其他具体资源，也不能
证明底层 close 非阻塞或唤醒挂起读取；`observation.elapsed_ms=0` 只是截止前未结算的初始投影。

候选 activation gate 仍 disabled、`activation_state=candidate` 且未注册，`capabilities.streaming=False`、严格 Flash v1 2048/零额外调用、默认模型、产品
Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变；Stage 8/8E 仍 `in_progress`，
8F、G53-7、黄金切片和生产准入不因本观察提前完成。当时的下一精确 checkpoint 保持原值，后续 provider
close/wakeup 拆分或真实请求必须另行授权；当前指针见下方最新 RQ-212 段落。

### RQ-210 边界澄清（2026-09-03）

RQ-210 不新增、重排或重分类阶段，也不把候选流关闭报告提升为 8-Core 能力。它属于 8-Advanced 的 candidate-only
证据：仅在 `ZhipuStreamSession` 内存中区分迭代器和外层 SDK stream wrapper，旧 receipt/schema 与产品 Runtime
保持不变。公共 CI 已完成；provider-level cancel/wakeup 与生产准入仍是独立闸门，8E coverage 继续按既有 planned 状态维护。

### RQ-211 边界澄清（2026-09-03）

RQ-211 仍属于 8-Advanced 的 candidate-only 观察，不改变 8-Core 必做项、8E/8F 顺序或 coverage 状态。
一次真实请求的结果为 `not_pending`：有限窗口没有形成挂起读取，因此没有执行 cancel，不能证明或否定
provider close/wakeup。body-free 回执与 c311 exact-SHA 公共证据已固定；候选仍 disabled/未注册，产品
Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。若继续，先裁决是否设计
能稳定制造 pending-read 的新版协议；不得把重复真实请求当作路线推进。

公共验证补充：`1c669e0` / Actions `33666132282` 已三 job exact-SHA 全绿，确认 RQ-211 回执被既有
provider capability 合同扫描正确识别。此验证不增加 8-Core 能力、不新增真实请求，8E/8F 与候选边界不变。

## 2026-09-03：RQ-212 候选 close/wakeup 离线回放分层边界

RQ-212 继续遵守 v1.3 的 8-Core/8-Advanced 分层：只新增 candidate-only、evaluation-only 的离线回放，
不把恢复、streaming 或供应商 close/wakeup 能力强塞进 8-Core。固定 Event 闸门覆盖正常 EOF、取消后唤醒、
取消返回但未唤醒、取消超时和取消抛出五种场景；回执强制 `offline_fake`、供应商调用数 `0`、不联网，
并隔离到 `data/evaluation/results/offline/`。它只证明本地观察器分类、单次 fake 打开、脱敏和不可变写入，
不证明 SDK close 非阻塞、HTTP response 取消或真实 pending `next()` 唤醒。入口不读 dotenv/凭据、不创建或
调用 SDK client（既有包导入可能加载依赖模块）。

候选仍 disabled/未注册，`capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、默认模型、
产品 Runtime、Portal、Account、Workbench、Auth、路由、`production_media=0`、G53-7、黄金切片、生产准入
和 8F 均不变。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-real-observation / pending-user-authorization`；
公共验证已完成；是否进行一次参数明确的真实 provider 观察仍需单独授权。

## RQ-212 公共闭环事实（2026-09-03）

RQ-212 已完成 candidate-only 离线回放的 exact-SHA 公共闭环：实现 `1a32012d9dc6424aa012f160d48c8847e21b00ec`、
Actions `33707313651` 三 job 全绿，v2 回执为 `data/evaluation/results/offline/
zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`（`2220` bytes，SHA-256
`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`）。回执仍标记 `offline_fake`、0 provider
calls、无网络；它不证明 SDK/HTTP close/wakeup，候选不注册，8-Core/8-Advanced 分层和 `production_media=0`
边界不变。下一精确 checkpoint 为 `candidate-close-wakeup-real-observation / pending-user-authorization`。

## RQ-213：候选 close/wakeup 第二次真实观察分层边界（2026-09-03）

RQ-213 仍属于 8-Advanced 的 candidate-only 证据，不新增 8-Core 能力，也不改变 8E→8F 顺序。
在 exact-SHA 公共绿灯提交 `a396412f7cd0f2e923536cf55f715dd56251aae5` 上只发送 1 次
`zhipu/glm-5.3-flash` 请求；回执为 `not_pending`，会话首段 172ms，未形成 pending reader，
因此没有执行 cancel。回执保持 body-free（909 bytes，SHA-256
`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`），不含 Key、正文或 request ID。

该样本不能证明或否定 SDK close 非阻塞、取消唤醒或 HTTP response 关闭；候选仍 disabled/未注册，
`capabilities.streaming=False`，严格 Flash v1、默认模型、产品 Runtime、Portal、Account、Workbench、
Auth、路由与 `production_media=0` 不变。下一精确 checkpoint 改为
`candidate-close-wakeup-follow-up-decision / pending-user-decision`；先裁决是否设计可稳定制造
pending-read 的新版协议，不以重复真实请求替代实验设计。

## 2026-09-03：RQ-214 transport gate 仍属 8-Advanced

RQ-214 只新增 candidate-only、evaluation-only 的离线 SDK/HTTP transport gate 预检，继续遵守
8-Core（product/deployment/compliance/eval/portfolio）与 8-Advanced 分层。预检通过真实本地
OpenAI SDK/Zhipu 适配器对象链和 `MockTransport` 固定 pending-read，供应商调用数为 0、网络为 0；
它不把 streaming、provider close/wakeup 或取消能力强塞进 8-Core，也不改变默认模型或产品 Runtime。

预检发现本地并发 iterator close race，故把 reader 唤醒与关闭投影分列并保持未决，不静默宣称成功。
下一步若获明确授权，最多执行一次官方 TLS transport 包装的真实观察；该证据仍只能说明本机
受控响应停顿下的客户端行为，不能替代 provider-native、G53-7、黄金切片、生产部署或 8F。

本地回执已固定在实现提交 `4c220c5751288ad77c589d2e0e581690085803c0`（`1693` bytes，
SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`）；同 SHA Actions
`33712055286` 三 job 全绿（pytest `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`；PostgreSQL `201 passed, 2 warnings`；packaging-smoke 通过），8E coverage 继续 `planned`。
## 2026-09-03：RQ-215 transport-gated 真实观察仍属 8-Advanced

RQ-215 在 RQ-214 离线预检和同 SHA 公共 CI 后，只执行 1 次真实
`zhipu/glm-5.3-flash` 请求。实现/观察器/输入计划身份为
`2acdf795881733e70c9246c48f7147d5136821b5`，Actions `33721483490` 三 job exact-SHA 全绿；
pytest `2296 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
packaging-smoke 通过。官方 TLS transport 外层 gate 已进入，pending reader 在 `31ms` 内被
response close 唤醒，但取消安全码为 `zhipu_stream_close`，iterator/composite 关闭投影为
`failed`、SDK stream 为 `closed`，结论为 `client_wakeup_close_race`。

该结果仍是 8-Advanced 的 candidate-only/evaluation-only 客户端证据，不新增 8-Core
(product/deployment/compliance/eval/portfolio) 能力；不证明 provider-native close/wakeup、
模型一般能力或生产 streaming。候选仍 disabled/未注册，默认模型、产品 Runtime、Portal、
Account、Workbench、Auth、路由和 `production_media=0` 不变。当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`；
后续修复关闭顺序或新的真实请求必须另立证据版本并重新授权。

## 2026-09-03：RQ-216 关闭顺序修复仍属 8-Advanced

RQ-216 只修复候选适配器的本地 `client_wakeup_close_race`：活跃 reader 存在时先关闭外层
SDK response，把 iterator close 交还给 reader 线程的 `finally`；非活跃路径仍逐资源最多一次关闭。
阻塞读取回归与离线 transport-gate 聚焦测试 `61 passed`，真实 API 为 0。此修复不新增 8-Core
能力，不改变严格 Flash v1、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由或
`production_media=0`，候选继续 disabled/未注册。当前唯一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`；
公共 CI 通过后再回到真实观察决策点。

RQ-216 公共闭环事实：提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions
`33726209532` 三 job exact-SHA 全绿；pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，
PostgreSQL 与 packaging-smoke 通过。该证据仍仅属于 8-Advanced candidate-only 适配器修复，
不把候选提升为 8-Core 或生产模型。当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`。

## RQ-217：关闭顺序修复后的 transport-gated 真实观察（2026-09-03）

RQ-217 继续按 v1.3 的 8-Core/8-Advanced 分层，属于 8-Advanced 的 candidate-only、
evaluation-only 客户端证据，不新增 8-Core 能力，不改变 8E→8F 顺序。用户在 RQ-216
公共 CI 闭环后授权一次真实观察；实现/观察器/输入计划身份均为
`3e028b1217f1274152ba161993287f29188a1b73`，Actions `33727163550` 三 job exact-SHA
全绿。

观察在官方 TLS transport 外的 `before_first_event` gate 中只发送 1 次请求；
`pending_reader_observed=true`、`reader_woke=true`、`cancel_status=returned`，
iterator/SDK/composite close report 均为 `closed`，结论为 `client_wakeup_clean`。
回执 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`
为 `1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`，
body-free 且 canonical round-trip 通过；`gate_released=false` 是受控停顿协议的预期条件。

该结果只说明本机客户端的 reader 唤醒和 reader-owned 收尾，不证明 provider-native
close/wakeup、模型一般能力、生产 streaming、G53-7、黄金切片或 8F。候选仍 disabled/
未注册，产品 Runtime、默认模型、Portal、Account、Workbench、Auth、路由与
`production_media=0` 不变；当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`。

## RQ-218/RQ-219：Flash 协议与长响应完成度的分层记录（2026-09-03）

按 v1.3 的 8-Core/8-Advanced 分层，RQ-218 的 G53-3 3/3 通过只属于协议身份观察；
RQ-219 的候选 8192 单次真实流在 90 秒以 `fail_closed / elapsed_limit` 收口，只属于
8-Advanced candidate-only 诊断。两者均不改变 8-Core、8E→8F 顺序、默认模型或产品 Runtime。
RQ-219 的证据提交 `3f35d150b2f17f919f2be1597c08c6db0178c461` 已取得 Actions `33735717434`
三 job exact-SHA 全绿；下一步固定为零网络的思考档位、流终态、Usage 尾帧和恢复决策拆分，
checkpoint：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

## RQ-220：响应完成策略的离线分层（2026-09-03）

RQ-220 属于 8-Advanced 的 evaluation-only 实现：9 个 fake/fixture 场景把请求档位、
terminal/EOF、Usage 和 recovery action 分开验证，provider calls=0。实现提交
`14254048f6ad2faea5c7b15801e5c7c11e0ceba4` / Actions `33738050233` 与回执提交
`ebb09a525b3340f31ba71821b894b4a142dfb4e7` / Actions `33738673832` 均三 job exact-SHA
全绿，回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
它不增加 8-Core、不改变 8E→8F 顺序，也不把候选提升为默认模型；当前进入候选域门裁决，
不自动追加真实请求。

## RQ-221：显式低思考候选探针仍属 8-Advanced（2026-09-03）

RQ-221 继续遵守 v1.3 的 8-Core/8-Advanced 分层：新增的 `low + 4096` profile 和一次
真实无工具探针只是 candidate-only、evaluation-only 观察，不新增 8-Core 能力，不改变
8E→8F 顺序。profile 通过显式候选构造器使用，`activation_state=candidate`、
`execution_allowed=false`，不进入正常 Runtime resolver。

实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions `33746833148` 三 job
exact-SHA 全绿；一次真实观察得到 `observed / finish=stop / usage=valid`，输入/输出
`1973/498`、延迟约 `20735ms`。body-free 回执提交
`ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，SHA-256=
`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。

该窄结果不证明领域质量、工具多轮、成本/延迟稳定性、provider-native streaming、
G53-7、黄金切片、生产准入或 8F；严格 Flash v1、默认模型、产品 Runtime、Portal、
Account、Workbench、Auth、路由与 `production_media=0` 均不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`，
需先另立低档候选领域门设计并取得裁决。
## RQ-222：低思考候选领域门仍属 8-Advanced（2026-09-03）

RQ-222 不新增 8-Core 能力，也不把一次低思考探针升级为产品准入。设计采用显式评测作用域
和共享请求策略，保持产品 Runtime 注册表封闭；旧领域考卷不重跑，规则冻结后创建新的匿名
held-out 三案例资产。`low + 4096`、90/120 秒、4/12 次调用和 24,000/72,000 token 墙只
属于 candidate-only 评测边界，deterministic fallback 在该作用域关闭。

本批 provider calls=0、没有新考卷或真实回执；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。G53-3-L、资产冻结、领域真实观察、黄金切片、安全/部署/合规与 8F 仍在后面。

### RQ-223：离线请求策略与预算墙（2026-09-04）

RQ-223 完成了上述 candidate-only 作用域的离线实现：私有能力对象不进入产品 Runtime 注册表，
共享链路通过显式 `request_policy` 消费固定预算，最后 Provider 边界先记账再 I/O，并在候选
执行器中关闭 deterministic fallback。Fake Provider 聚焦与相邻回归均通过，尚无真实调用或
领域质量结论；同一 SHA 公共 CI 仍是下一闸门。该批不改变 8-Core/8-Advanced 分层，也不把
候选当作唯一生产模型。

### RQ-224：低思考候选领域门公共 CI 闭环（2026-09-04）

RQ-223 的实现提交 `d823cc40c3fcafb7167edccded87e185be4cae8a` 已通过 Actions
`33781369322` 的 exact-SHA 三 job 公共 CI。该证据仍只属于 8-Advanced candidate-only
控制面，不新增 8-Core 能力，不改变产品默认或 Workbench；下一步才是新鲜 G53-3-L 和
held-out 资产，候选不能因此自动注册或成为唯一模型。

### RQ-225：低思考协议与新鲜资产离线前置（2026-09-04）

RQ-225 在 8E/8-Advanced 内完成低思考 G53-3-L 协议组合器和全新三案例资产的离线实现。
显式 `request_policy` 复用共享协议切片并固定 `low + 4096`、90 秒工具窗、最多 3 次调用；
新 Dataset、V1.1 Input Plan、Prompt/Context Snapshot 和合成 fixture 通过 no-I/O 身份、
上下文 commitment 与历史 marker 隔离校验。聚焦协议/资产及相邻回归 `20 passed`，
provider calls=0。该批不新增 8-Core 能力、不改变产品默认、Portal、Account、Workbench、
Auth、路由或 `production_media=0`；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`。
提交 `411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的 Actions `33787508488` 三 job exact-SHA
全绿；公共 pytest 为 `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`，之后仍需明确授权才可真实执行。

### RQ-227：低思考 held-out 领域门的失败归因边界（2026-09-04）

RQ-227 继续遵守 v1.3 的 8-Core/8-Advanced 分层：一次协议门通过不能替代领域质量门，
也不能把候选注册成产品唯一模型。用户授权后，在入口修复提交
`659757eca7ff1b658dfd164631512d3964c5a2ff` 及其 exact-SHA 公共 Actions `33826568517`
上执行一次全新的三案例低思考领域门；三 job 均成功，真实领域调用 6 次，累计（含协议）9/15
次，领域/累计 token 为 17834/18925。

脱敏回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
（7537 bytes，SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`）显示：
首案 Evaluation 96 通过；第二案回答完成、Evaluation 97，但没有证据来源且注入检查失败，
触发 `evidence_missing/unsafe_publication`，按首错停止，第三案 skipped；最终
`admitted=false`。该失败说明领域发布安全/证据链未闭合，不能归因成 API 不可达或直接推断模型
一般能力。候选仍 disabled/未注册，8-Core、默认模型、产品 Runtime、Portal、Account、Workbench、
Auth、路由、streaming、黄金切片和 `production_media=0` 不变；同一 held-out 考卷与回执不得重跑/覆盖。
当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-heldout-domain-gate / completed-real-observation / pending-next-decision`，
下一步先做失败归因与是否另立版本的裁决，8F 仍在后面。

### RQ-228：候选领域证据与注入边界离线加固（2026-09-04）

RQ-228 仍属于 8-Advanced 的 candidate-only 归因修复，不增加或重排 8-Core。针对 RQ-227
第二案的两条独立失败，采用版本化 `glm53-flash-domain-quality-v1`：候选执行器要求至少
一个可归因检索来源；Context 增加可信数据边界策略；明确拒绝时才允许对不透明 marker 做
固定占位符脱敏，其他出现继续 fail closed；公开观察只保留 body-free 计数和安全原因码。

本地相关/相邻回归 `102 passed`，provider calls=0；实现
`e2efe8fd75e8cf27cbee7e90484fc90d288ce065` 的 Actions `33832025848` 三 job
exact-SHA 全绿，公共 pytest 2344、PostgreSQL 201、packaging-smoke 通过。
候选仍 disabled/未注册，GLM-5.2 兼容路径、默认 Runtime、Portal、Account、Workbench、
Auth、路由、`production_media=0`、8E→8F 顺序和 8-Core/8-Advanced 分层均不变。当前精确
checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-evidence-injection-hardening / completed-public / pending-next-decision`；
下一步另立新协议/资产并先做 no-I/O 准入，不能重跑 RQ-227；任何真实观察仍需明确授权。

### RQ-229：加固领域 V2 资产离线准入（2026-09-04）

RQ-229 仍属于 8-Advanced candidate-only，不增加或重排 8-Core。它用全新协议计划、问题、
匿名数据、case/run ID、marker 和带 RQ-228 policy 的 Context Snapshot 取代“原题重考”；
no-I/O 准入绑定质量版本、来源下限和原有预算/停止规则，`external_provider_calls=0`。

候选仍 disabled/未注册，GLM-5.2 手动应急/兼容路径、默认 Runtime、前端、Workbench、Auth、
路由、`production_media=0` 和 8E→8F 顺序均不变。实现
`c50cf231957bc54201d0207b99110fcf4b2897b3` 的 Actions `33843064715` 三个任务
exact-SHA 全绿（公共 Python 2349、PostgreSQL 201、前端 270）。当前为
`completed-public / pending-user-authorization`；下一步等待用户明确授权一次新的 V2 有界真实领域观察。
真实模型观察、黄金切片、生产安全/部署/合规与 8F 都不能由资产公共闭环替代。

### RQ-230：加固领域 V2 专用真实运行器（2026-09-04）

RQ-230 仍属于 8-Advanced candidate-only，不增加或重排 8-Core。用户已授权一次 V2 真实观察，
但执行前先用独立 V2 Admission/Result/CLI 把 RQ-229 资产、RQ-228 质量加固、既有真实协议证据、
资源墙和 exact-SHA 公共证明绑定；本地 no-I/O preflight 与 `107 passed` 相邻回归通过，
provider calls=0。

此前为 `completed-local / pending-public-ci`；公共绿灯后已在同一干净 SHA 上执行一次观察，当前为
`completed-real-observation / pending-next-decision`；
GLM-5.2 手动应急/兼容路径、默认 Runtime、前端、Workbench、Auth、`production_media=0`、
8E→8F 顺序及生产安全/部署/合规边界不变。

#### RQ-230 真实观察结论

实现 SHA `5fe8606f205d49ca5dde969a5823a0eb75587c35` 的 Actions `33846260144` 三任务
exact-SHA 全绿；no-I/O preflight 通过后按授权执行一次 V2 观察。首案完成 3 次调用，
证据来源数为 2、注入检查通过，但事实核验与质量门失败，修订预算耗尽，终态为
`rejected / revision_budget_exhausted`，首错 `domain_case_outcome_mismatch`；后两案跳过。
领域/累计 token 为 `10993/12084`，真实网络已使用。脱敏回执 SHA-256=
`d1739c5d76da21c1109808b128e8ef82df251df32ea7355836f202d850e01c18`，`admitted=false`。
该结论只影响 8-Advanced 候选领域质量观察，不增加 8-Core、不注册候选，也不改变默认 Runtime、
GLM-5.2 回退、Portal、Account、Workbench、Auth、路由、`production_media=0` 或 8F 顺序；
当前进入 `candidate-hardened-domain-v2-real-observation / completed-real-observation / pending-next-decision`。

#### RQ-230 离线失败归因裁决

本次失败可核验地落在 8-Advanced 领域质量合同：Provider/工具/证据检索和注入检查完成，独立
事实核验为假，评分 `80` 未达到 `85` 发布门，零修订预算收敛为拒绝；终态和案例不匹配码是派生
结果。由于回执不保存正文或评测 issues，具体错误句不能判定。保持 candidate-only，不另立版本、
不重跑或放宽门槛；任何未来假设验证都必须取得新授权并建立全新版本化证据链。

### RQ-231：加固领域 V3 有界修订设计（2026-09-04）

RQ-231 继续属于 8-Advanced candidate-only，不增加、删除或重排 8-Core。用户在 RQ-230 归因后
授权新的版本化设计；采用最多一次 Harness 原生修订与安全计数诊断，继续保持 85 分及事实、引用、
注入、来源硬门。该决定不把一次候选实验变成必选生产架构。

调用上界按完整可达控制流固定为 9 次/案、27 次/域；Token 墙必须在离线实现中根据新 V3 请求包络
证明后冻结。V3 题目、匿名数据、case/run ID、marker、Context、协议和回执身份全部新建；
RQ-227/RQ-230 不重跑。真实运行前还需 no-I/O 准入、exact-SHA 公共 CI、新鲜 G53-3-L 和单独授权。

当前为 `candidate-hardened-domain-v3-bounded-revision-design / completed-design /
pending-offline-implementation`。本批 provider calls=0；默认 Runtime、GLM-5.2 回退、前端、
Workbench、Auth、`production_media=0`、8E→8F 顺序及生产安全/部署/合规边界不变。

### RQ-232：V3 离线实现与资产准入（2026-09-04）

RQ-232 仍属于 8-Advanced candidate-only，不增加或重排 8-Core。实现保留共享执行器的默认零
修订路径，V3 才显式启用最多一次修订；评测只公开 body-free 枚举计数。新预算证明把每案/全域
调用墙冻结为 `9/27`，Token 墙为 `203000/608000`；全新 Dataset、Context、fixture、marker、
协议和输入计划通过 no-I/O SHA 准入。

初始实现 `730c32d074269fb45e5a5351b1af591ecaa35de1` 的公共运行 `33894351184` 暴露旧输入计划
零修订隔离和 V2 回执分流两处遗漏；修复提交 `f99c142c269df765deb592c463ce6e2555bcc3fe`
保持旧调用方默认零修订，只有 V3 显式启用一次修订。相关与相邻回归 `93 passed`，compileall、
diff check、治理检查通过；Actions `33895602378` 三任务 exact-SHA 全绿，公共 pytest 2379、
PostgreSQL 201、packaging-smoke 通过。exact-SHA 预检为 `pending_protocol_evidence`、provider calls=0。
当前为 `candidate-hardened-domain-v3-bounded-revision-implementation / completed-public /
pending-fresh-g53-3l-authorization`；候选未注册，默认 Runtime、GLM-5.2 回退、Portal、Account、
Workbench、Auth、路由、`production_media=0`、安全/部署/合规和 8F 边界不变。下一步仅在明确
授权后取得新鲜 G53-3-L，不能自动发起 V3 领域观察。

### RQ-233：新鲜 G53-3-L 回执延迟口径修复（2026-09-05）

本条仍属于 8-Advanced candidate-only，不增加、删除或重排 8-Core。已授权的新鲜 G53-3-L 在
回执构造阶段因预算 I/O 延迟与协议端到端延迟口径不一致而失败，没有生成证据文件；最多 3 次和
零重试边界成立，但精确调用数不能在无回执时补写。

本地修复只让回执采用协议案例延迟之和，并增加推进时钟回归；请求参数、预算、结构化/工具合同、
候选注册和质量门均未改变。修复 `110f9e8008486bfb976643a6abdaa8e88ea334e6` 的 Actions
`33897787039` 三任务 exact-SHA 全绿。当前为 `candidate-fresh-g53-3l-receipt-latency-fix /
completed-public / pending-fresh-g53-3l-reauthorization`；默认 Runtime、GLM-5.2 回退、前端、
Workbench、Auth、`production_media=0`、8E→8F 顺序及生产安全/部署/合规边界不变。

### RQ-234：修复后协议证据已取得（2026-09-05）

新鲜 G53-3-L 在公共已验证代码 `110f9e8` 上通过，A1/A2 共 3 次真实调用，回执严格校验
通过；V3 零调用预检就绪。本条仅关闭 RQ-233 的下一动作，不增加或重排 8-Core，不把协议
可达性等同于领域/生产准入。下一次明确继续执行一次全新 V3 有界领域验收；候选仍未注册，
前端、GLM-5.2 回退、黄金切片、生产安全/合规与 8F 边界不变。

### RQ-235：V3 检索边界真实观察（2026-09-05）

一次 V3 验收首案检索零片段，evidence_required 安全拒绝，未进入评分或修订；后两案跳过。
下一步是候选检索合同离线诊断/加固，不降低支持或安全门、不重跑已消费考卷，不把这次失败
归为模型一般能力结论。8-Core、8E→8F、产品/前端、GLM-5.2 回退和生产成熟度边界不变。

## RQ-236：候选检索合同加固（2026-09-05）

本批仍属于 8-Advanced candidate-only，不新增 8-Core。新增版本化的
`coaching-query-recovery-v1`，仅在单一已登记教练主题的零命中/`insufficient_evidence` 情况下
补查一次；原查询、`top_k`、过滤条件、BM25 `15.0`、查询覆盖率 `0.18` 和来源/安全硬门均保持不变。
执行器默认关闭该策略，V2 入口前置拒绝，V3 候选入口显式开启；安全诊断只公开枚举、计数和过滤
键名，并区分模型工具调用与本地补查。未知、混合、注入式、冲突、无适用资料和异常查询不补查。

本地聚焦及相邻回归 `51 passed`，compileall、diff check、治理通过，provider calls=0。实现提交
`ed62dbbc80506a8bcfae7eefb132348b21e587e0` 的 Actions `33943854904` 三任务 exact-SHA 全部成功。
候选仍未注册，默认 Runtime、GLM-5.2 回退、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变；当前检查点为 `candidate-retrieval-contract-hardening / completed-public /
pending-next-decision`，不能据此重跑旧领域考卷或宣称生产准入。
