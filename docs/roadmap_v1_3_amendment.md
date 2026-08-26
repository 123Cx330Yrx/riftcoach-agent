# RiftCoach 路线 v1.3 局部校准

## 2026-08-24：8E 视觉前置的顺序约束

`Rift Awakening → Broadcast Workbench` 是 8E 内的设计前置，不是新的主阶段或新的 canonical checkpoint。
它必须先完成 presentation-state 合同、分层资产/来源账本、入口 storyboard 及 responsive/reduced-motion
验证，再进入对应前端实现；不会绕过 Batch E 安全/部署合同、外部调用门或 8F 真实 golden slice。

本文件只记录对既有阶段 0-8 路线的增量修正，不增加、删除或重排九个主阶段。

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
安全错误 provenance 切片已完成本地/公开验证；GLM-5.3 G53-0 待普通 API 上线后再审计，
或在出现明确 Pro/Flash 对照需求后另立实验。

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
source/seam/full-scene 门，external calls `2`、production media `0`。RQ-125 又防止过度外推：当前 Veo prompt
未充分遵守 motion-only guidance，故 C 线只作为优先 no-paid-call proof；失败时恢复一次校正 A comparator，
不改变 RQ-108/8E/8F 顺序。

implementation/evidence `6084937` / Actions `32757872792` 已让 foundation 的 pytest、真实 PostgreSQL 与
Linux package 三 job exact-SHA 全绿；foundation 正式关闭。用户随后按 RQ-109 明确授权 RQ-108，当前进入
教学、ADR/设计、素材采用门和 TDD；8E coverage 继续 planned。
