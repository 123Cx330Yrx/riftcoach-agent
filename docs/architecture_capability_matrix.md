# RiftCoach 架构能力覆盖矩阵

> 2026-08-25 当前 8E Task 4 公共证据：`52def9c`/`d58ba15`、Actions `32841900909`，focused `25`、frontend unit `257`；
> 不代表 adopted production media 或完整 8E 已完成。

### 2026-08-31：RQ-185 Flash 候选诊断边界当前校正

RQ-184 已为 RQ-183 候选合同取得实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 exact-SHA 公共 CI（Actions
`33405110692`），在同一 A checkout 完成 G53-3 严格 `3/3` 调用通过（A1 `1/1`、A2 `2/2`，`admitted=true`、
SDK retries `0`），并由直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 只新增脱敏结果；B 的
Actions `33405881172` 三 job 也全部成功。A/B 无 I/O identity preflight 通过，结果 canonical-LF SHA-256 为
`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

2026-08-31 RQ-185 candidate-recovery diagnostic boundary：两次独立有界诊断启动都只进入
`primary` 首回合，未观察到响应/Usage/finish reason/Trace，且没有生成结果 JSON；一次沿用
120 秒传输边界在约 60 秒时中止，另一次使用临时 20 秒客户端传输上限仍在约 60 秒内未结束。
没有发送 `fresh_recovery`，不能判断请求是否抵达供应商或费用状态。候选继续
`activation_state=candidate` / `execution_allowed=false`，严格 Flash v1 仍为 2048/零额外调用；
该诊断不新增生产能力、恢复准入或 G53-7 证据，后续需新的授权进行传输/代理边界复核。

RQ-184 证据只证明公共可复现性与协议身份接缝；RQ-185 又没有形成可用真实诊断结果。两者都不注册候选、
不执行 fresh-recovery/G53-7，也不改变严格 Flash v1 的 2048/零额外调用、默认模型、Portal/Account、Workbench、
Auth、路由或 `production_media=0`；下一步需新的用户授权先复核传输/代理边界。

### 2026-08-31：RQ-176 Flash-only 产品运行时当前校正

用户已明确选择普通智谱 API `zhipu/glm-5.3-flash` 作为产品正常运行目标，GLM-5.2 仅作显式兼容/应急回退。
唯一注册的 `glm-5.3-flash-runtime-v1` 已接入产品组合根、Worker、Runtime、Agent/工具/Harness、Provider、
Runtime policy 与 Trace identity；Root/Factory/Runtime 对精确 Flash 未绑定档案提前拒绝。Flash 的执行窗/传输/
输出上限为 90s/120s/2048，sampling 为 `temperature=1`、`top_p=0.95`，SDK retries=0；Skill 30 秒质量门保持独立。
`.env.example` 与 Compose 模板已对齐 Flash。RQ-179 的最终实现 A 已取得 exact-SHA 公共 CI，RQ-180 又在同一
A/B 证据链上完成一次 G53-7 真实尝试；首例以 `provider_response_invalid/incomplete_chat_response` 停止，
`admitted=false`。RQ-182 已补上版本化响应完成策略与离线 TDD，RQ-183 又补上候选 runtime/attempt/预算/Trace 合同；
RQ-184 已为该候选合同取得实现 A/B 的 exact-SHA 公共 CI，并在同一 A 重取 G53-3（严格 `3/3` 调用通过）；RQ-185
两次候选诊断启动都无可观察响应、未发 fresh-recovery 或生成结果。严格 Flash v1 保持 2048/零额外调用，
8192/一次 fresh-recovery 仍为未注册候选；当前不自动重试，先等待传输/代理边界复核授权，黄金切片和
安全/部署/合规证据继续后置。
本地接线/一次领域尝试不等于生产准入。Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。

### 2026-08-31：RQ-178 G53-7 A/B 身份绑定边界

G53-3 协议执行代码与实现提交 A 分离于承载脱敏结果的证据提交 B。新的 schema 1.1 admission 在本地无 I/O
校验 A 的实现/CI/协议 `code_sha`、B 的独立 CI、当前 `HEAD=B`、B 的 Git blob 与工作树 canonical-LF 摘要；
B 只能新增 capability-result 文件，不能覆盖既有证据。该接缝与 `53 passed` 聚焦回归已完成，但不构成新实现
公共 CI、G53-7 领域采用、黄金切片或生产准入；A 已冻结，B 与同 SHA G53-3 仍待后续，8E coverage 保持 planned。

### 2026-08-31：RQ-179 A 身份公共证据校正

最终实现 A=`9e6d78be51c3a5c512b67f83d2849f9b1261cf77` 已由 Actions run `33378687984` 的三 job
exact-SHA 验证；公共 checkout 具备验证 A/B 父子、blob 与 diff 所需的完整历史。该证据只把 RQ-178 的本地身份
接缝提升为公共验证，不新增领域/生产能力；同 A 的新 G53-3、直接证据子提交 B、G53-7 和 8E exit 仍未完成。

### 2026-08-31：RQ-173 G53-5 F7 诊断历史校正

G53-1/2 的历史离线 profile 与 exact-SHA 公共证据、G53-3 普通 API 协议通过、G53-4 本地首错拒绝均保持原样。
RQ-171 的 Flash 隔离 profile 与适配器修复已由 G53-5 真实矩阵观察：`11/11` calls、`46,151` tokens、`7/8`
cases pass。RQ-173 随后仅将 F7 `max_tokens` 从 512 调至 2048，独立 `1/1` call、`557` tokens，
`finish_reason=tool_calls`、1 个 ToolCall；该结果是 `vendor_raw_transport_only`，只诊断原先的 `length` 截断。
adapter core、AgentLoop 的有序多 ToolCall/思考回放、domain development、vendor text stream 与 vendor multimodal
均有观察证据；F4 缓存 `unproven`，F8 仍是 vendor-only。`production_admitted=false`、
`public_ci_confirmed=false`，因此不能声称 provider-neutral streaming、Agent/领域或生产准入。
默认模型、Workbench、Auth/路由和 `production_media=0` 不变；当前 Agent 主线已完成 RQ-184 的候选合同公共证据链，
下一项须先获用户单独授权，才能考虑一次有界真实候选诊断。

> 说明：下方历史能力行保留 RQ-165 enabled-low、RQ-167/168 旧 Key 认证失败和 RQ-170 G53-4 首错的时间点；
> 当前运行时增量以本节 RQ-184 与后续 RQ-176/RQ-182/RQ-183 为准；下方 RQ-173/RQ-172 等历史能力行只保留时间点，旧考卷与脱敏结果不重写。

### 2026-08-24：8E 视觉层与能力边界

视觉层只消费现有 owner/profile/product-state/evidence/training projections；它不拥有身份认证、Riot RSO
绑定、外部数据检索或报告发布权。Portal 的环境、路线和转场属于 presentation capability，必须在无远程 I/O、
keyboard、mobile、reduced-motion 和 bundle budget 下验证；真实数据和状态仍由后端 typed contracts 决定。
RQ-108 只取代 Task 3 作为最终 Portal 视觉/动效验收，以及可见 CSS/SVG core/route 作为最终 art；Task 3 已有的
zero-early-I/O、Portal→Account→Workbench、原生语义 hit target、keyboard/focus、history、reduced-motion 与
失败 fallback 功能证据继续有效。Batch E E1–E3 `92b7685/32658277570`、E4
`27b9256/32660145945` 与 E5 `ca6da44/32661425379` 已公共闭环：session/CSRF、request budgets/单机 limiter、
SecretSource、marker replay/Artifact-Trace cleanup 和 bounded metrics 已有证据；正式 OIDC/RSO、HTTPS、真实
Secret Manager、共享 limiter、KMS/对象存储/加密备份和部署仍未完成。

RQ-101 Timeline 已由 `794032f/32682243568` exact-SHA 公共关闭。RQ-102/104 与 RQ-105/106 的 typed bilingual
projection、三层 journey、真实 Player Link、母图分层 V1 与 browser/a11y 门又由 `6084937/32757872792`
公共关闭。RQ-108 已按 RQ-109 授权；ADR-0068/设计/TDD plan 采用 poster-first 全帧 loop、透明语义激活和
sticky fallback，RQ-117 又把 Account 地图冻结为官方拓扑准确、地形有意概括、禁止伪写实微细节；RQ-118
固定保留母图原水晶/塔体/构图，不再生成放大或替换水晶；RQ-119/120 又以 Kimi rejected Bad Case 建立
Wan/Seedance/Veo/Luma/Runway、HyperFrames/Remotion 与混合式三路线横评。RQ-108 design
`b3b5280/32812868683` 与 runtime Task 1 `1b146e6/32826953474` 已 exact-SHA 公共关闭；Task 2
poster-first 播放状态/组件已本地完成、待公共门；这些证据不等于连续 Gold/CS/XP 曲线、正式 OIDC/RSO、
最终电影化 Portal 或可追问 Coach。

RQ-107 审计确认现有 Web 只查看最近 Report/Training summary，尚未消费 Conversation-bound Agent 创建链。
bounded review-grounded Coach 是推荐的 8E 补齐项，但插入顺序待用户裁决，矩阵不把建议误写成已实现能力。

2026-08-29 Region Entry Panel 试水补充了 Q10 的局部实现证据：地区是 presentation-only typed hint，
动态候选通过 WebM/MP4/poster/reduced-motion/failure 降级，进入 Account 后不改变身份或 routing。它仍是
research preview，不能替代最终媒体许可、移动端、loop、视觉 QA 或 8E exit。

同日的全量 source 复查把视觉参考按消费者重新绑定：Riot/Universe 负责语义形状和 crest fallback，高级
视觉目录负责构图/字阶/密度，MotionSites 与轻量 CSS/Motion 机制负责局部 spotlight、选择反馈和有限转场；
OP.GG/电竞数据、Agent observability、Training 产品与 Timeline 仍分别归 Workbench、Trace、Training 的后续
消费者。该映射不引入新依赖，也不把研究素材或付费 prompt 视为生产资产。

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
| A02 | 质量门控 Harness | 状态机、Artifact、评测、受限修订、降级 | 阶段 2 | Stage 8 增加恢复与复杂运行治理 | 状态迁移、错误数字、修订越权、发布门禁、恢复终态测试 | 已完成，待深化 |
| A03 | 模型 Provider 抽象 | 统一 ChatRequest/Response、Registry、能力协商；Zhipu/DeepSeek 最小协议有真实证据但领域未准入；DeepSeek V3 calibration 不完整且已由 ADR-0027 关闭；安全错误 provenance 已有离线白名单切片；RQ-165/166 完成 GLM-5.3/Flash profile 本地边界 TDD 与旧 exact-SHA 公共 CI，RQ-169 的 G53-3 协议门通过，RQ-170 的 G53-4 首案因并行 ToolCall 本地拒绝，RQ-171 已补思考回放与有序多 ToolCall 本地合同，RQ-172/173 保留真实观察；RQ-176 已将唯一注册 Flash 运行时档案显式接入产品组合根，RQ-177 又在实现 A 上取得新的 3/3 协议证据，RQ-178 补齐 A/B 本地身份预检，RQ-179 为最终实现 A 取得 exact-SHA 公共 CI，但同 SHA 新协议/B/领域仍未关闭 | 阶段 3 | 5D-7 已以“当前无领域准入”完成采用裁决；G53-0/1/2/3 已完成，G53-4/G53-6 未准入且旧结果不重跑，G53-5/RQ-173/RQ-176/RQ-177/RQ-178/RQ-179 本地或公共证据仍 `production_admitted=false`、`public_ci_confirmed=false`（A 的 CI 仅证明代码验证） | 同一领域案例、Tool Calling、结构化输出、错误合同、调用/Token/金额停止与可达性证明 | 部分完成 |
| A04 | Tool Runtime | Schema、超时、重试、缓存、熔断、fallback、指标 | 阶段 3 | 阶段 7 适配标准 MCP 工具 | 故障注入、缓存、熔断、fallback 和越权测试 | 已完成 |
| A05 | RAG 与证据 | 混合检索、父子块、引用、冲突、拒答、独立保留集 | 阶段 4 | 维护数据集；按规模证据决定是否升级存储 | Recall/MRR/nDCG、abstain、引用支持与冲突测试 | 已完成 |
| A06 | 最小 Agent Loop | Assistant ToolCall、Tool Observation、预算和停止原因；多 ToolCall development TDD 已固定整批数量/白名单/重复零副作用预检、顺序执行、ID/Usage/迭代/deadline 语义 | 阶段 5A | 5E 统一 Runtime；真正并发仅由新的延迟 Bad Case 决定 | Fake Provider + 真实知识工具、重复调用、越权、超预算和批次零副作用测试 | 已完成 |
| A07 | Skill Contract | `recent-form-review` 与 `single-match-review` 均有 Manifest、SKILL.md、Pydantic I/O、工具白名单和预算 | 阶段 5B 基础 + 5C-5 前第二个真实合同 | 阶段 6 加入 Memory 输入，阶段 7 加入 Meta Skill；真实内部 Skill 出现后才设计调用模式 | 坏 Manifest、Schema、权限漂移、预算和发布边界测试 | 已完成 |
| A08 | Skill Router | 5C-1 至 5C-6 与退出复核均完成；development 23/23、holdout 11/12；selected 决策锁定 Skill name/version；ADR-0010 暂缓 LLM fallback | 阶段 5C | 优先类型化入口/澄清；只有新鲜失败族与结构化输出、质量、成本、故障证据成立才重开模型实验 | 正例、负例、歧义、未支持、误路由、版本快照、拒绝测试、退出复核和 ADR | 已完成 |
| A09 | Prompt/Context Engineering | Harness Prompt V0、SKILL.md 指令；5D 已完成 trust-typed Context/预算与 Evaluation 1.1；5E Trace 有 prompt profile 字段；5P 已绑定 verified Prompt Program；6B-8 run-scoped Memory Context decorator/body-free manifest/terminal turns 已由 `aacc11a/32403187972` 公共闭环 | 5D-5P，6B-8 | 8D 已把 Meta/Riot/static/patch 收敛为 body-free data projection；正式 Coach/UI Context composition 留 8E | Prompt 版本、组件摘要、上下文优先级、whole-record ceiling、owner/role 隔离、manifest、Meta provenance、注入、回归和消融测试 | V1 与 8D fusion complete；8E projection 待实现 |
| A10 | 结构化模型输出 | 5D-6a 已建立 Provider-neutral 合同；Zhipu 与 DeepSeek V4 Pro 均真实通过最小协议；DeepSeek V3 首请求规范化失败且当前候选已关闭；RQ-165/166 为 GLM-5.3/Flash 完成 thinking/structured/tool 离线边界与旧 exact-SHA 公共 CI，RQ-169 的 G53-3 A1/A2 已通过，RQ-170 G53-4 首案在规范化前因并行 ToolCall 被拒绝，RQ-171 已实现内部思考回放与有序多 ToolCall，RQ-172/173 保留真实 vendor 观察，RQ-176 将 Flash 运行时预算正式接入产品组合，RQ-177/178 完成新协议的 A/B 身份接缝与无 I/O 预检，RQ-179 完成最终 A 的 exact-SHA CI | 阶段 5D | 新产品接线仍需在 A 上重取协议、由 B 只新增证据、G53-7 与黄金切片；F7 2048 vendor raw 观察不等于 provider-neutral streaming，F4 cache 未证明、F8 vendor-only；生产准入仍关闭 | 合法、缺字段、额外字段、截断、非 JSON、Schema 漂移、Thinking 预算、调用预算、可达性和修复上限测试 | 部分完成 |
| A11 | AgentRuntime V1 | 5D 控制链及 5E-1 至 5E-4 均已公开完成；两个真实 Skill 共用同步 `run()`、进程内 `stream()`、typed output、完整 Trace/Usage、安全失败映射与 exit matrix；5F-1 至 5F-5 已完成 Pi 0.84.2 审计/隔离/Harness/采用对照，最终由 `f8dea66/32028206103` 公共裁决产品拒绝 Pi、冻结保留 evaluation-only 资产 | 阶段 5D-5E | Stage 8 8C 已完成 durable event、cancel、lease/fencing、checkpoint、recovery 与 replay；后续 8D/8E 再扩展证据融合与产品化 | 统一 run/stream、事件、Trace、Usage、终止原因、恢复/迟到结果退出审查，以及 Pi batch/Usage/Trace/sidecar 差异矩阵与采用/归档门 | V1 已完成；8C `2df5349/32587659678` 公共闭环 |
| A12 | 多模型选择与降级 | Provider Registry 已有；DeepSeek V4 Pro 只通过最小协议，当前 V3 领域候选已关闭；GLM-5.3/Flash 已完成本地 profile TDD 与旧 exact-SHA 公共 CI，G53-3 协议门通过、G53-4/G53-6 未准入，RQ-171/172/173 修复与观察完成；RQ-176 已明确 Flash-only 正常产品目标、GLM-5.2 显式回退，并把 profile 接入产品组合；RQ-177/178 完成协议 A/B 身份接缝，RQ-179 已为最终 A 取得 exact-SHA CI，但同 SHA 协议复核、B、G53-7 领域准入、任务级自动路由或自动降级仍未完成 | 5D 完成候选采用决策；8E 当前先完成 Flash-only 产品接线，Flash/Pro 比较不再是前置决策；5F Pi-only 不改变模型路由 | G53-0/1/2/3 已完成；G53-4/G53-6 未准入且不重跑，G53-5/RQ-173/RQ-176/RQ-177/RQ-178/RQ-179 为 `production_admitted=false`、`public_ci_confirmed=false`（A 的 CI 仅验证实现），GLM-5.2 只保留显式回退 | 新鲜同任务评测、故障降级、unsafe publication、成本和 p50/p95 延迟对照 | 部分完成 |
| A13 | Session 与长期 Memory | RQ-060 至 RQ-071 已冻结并实现 PostgreSQL 单一真源、claimed/observed、Conversation、Candidate、typed targets、Plan/Progress、Context、terminal turns 与 lifecycle/export；entry design、6B-1 至 6B-9 和历史教学/工程证据门均已公共闭环，最终 `cbc7cbd/32408101770` | 阶段 6 | Redis/语义索引只由真实 Bad Case 触发，verified 仅在正式 Auth + 安全 RSO callback + `/accounts/me` PUUID 精确匹配后另行采用；备份副本擦除留阶段 8 | 无 CN 路由、claimed/observed、verified 不可创建、两 owner/Conversation/同 PUUID 隔离、Task binding、typed version、Plan/Progress、stable Context、terminal publication、查看/更正/导出/删除/补偿测试 | V1 已完成，后续深化（package schema 1.6） |
| A14 | API 与任务持久化 | 5P/6A/8C 已公开完成；8E Batch B `e844bdd/32622696087` 完成 profile/routing；Batch C `7975dc3/32629160732` 完成 0011 Evidence/Product/SSE；RQ-096 `f441061/32647933692` 完成 owner-scoped latest locator、Recent Summary 与 typed Evidence HTTP composition | 阶段 5P 提供本地同步切片，阶段 6 加 SQL、异步组合、安全与生命周期 | 8E 后续继续 Auth/备份/部署；refresh scheduler 只由独立 writer Bad Case 触发 | receipt/path/Schema/SHA/终态交叉校验；PostgreSQL migration/revision/tamper/concurrency、locator owner/order、HTTP 四态/错误、SSE reconnect、Linux composition smoke | V1、Batch B/C 与 live integration 公共闭环 |
| A15 | 标准 MCP 与动态 Meta | 7-1…7-5 已公共闭环；实现 `a88fbc4/32483521108`、官方 SDK Client→RiftCoach stdio、RiftCoach Client→OP.GG Streamable HTTP 与不可覆盖 evidence `fac6fe0/32484257736` 均通过；8D `a274b7f/32598480400` 又完成 typed EvidenceBundle；8E ADR-0057/0058 已由 live diagnostic、`83fde7d/32615340228`、修复后 body-free bundle 与 evidence `efaccd9/32615821339` 完整闭环 nullable JSON-null Bad Case | 阶段 7 | RQ-094 要求 8F 前另设 useful-breadth gate：champion analysis、lane matchup 为最低评估候选，synergies 按真实消费者；实时刷新、正式 Coach/UI 与公网 Server/Auth/TLS 属 8E；当前 top-10 未命中的 champion join、patch/freshness 继续显式 degraded | initialize、tools/list、tools/call、断线、版本与 owner 边界测试；每个新工具独立 schema/grammar/provenance/cost/degrade；EvidenceBundle provenance/join/conflict/expiry/schema；完整 golden slice 覆盖 Riot/Data Dragon/patch/OP.GG/Training/UI | V1 与 8D typed fusion complete；lane-meta live pass 但 breadth/golden slice 待完成 |
| A16 | Multi-Agent 与 DAG | 8A 已由 `12ad835/32567642315` 公共闭环；8B implementation `180bc8b/32572085065` 与 result/ADR/evidence `783a329/32572610725` 均三 job 成功并唯一执行 holdout。ADR-0053 因 candidate 18.95%<20%、无相对普通并行隔离增益而 reject 产品 Multi-Agent；bounded parallel 22.88% 作为 8D 设计输入 | 阶段 8 Advanced | 不接产品 Multi-Agent；保留 evaluation assets。未来重开需普通并行无法解决的新 Bad Case、新 case/result identity 和 ADR；DAG/Agentic Retrieval 继续 deferred | 同切片三路、Scripted 成本/延迟、失败隔离、body-free immutable result SHA `944258...445e8`、result tests 与 ADR | 8B complete；RQ-083 已授权 8C 设计，Multi-Agent/DAG 不进入 8C |

## 3. 质量、安全与运维能力

| ID | 能力 | 当前基础 | V1 负责阶段 | 后续深化 | 验收证据 | 状态 |
|---|---|---|---|---|---|---|
| Q01 | 端到端 Evaluation | 报告事实评测、RAG/路由评测与 5D-7 分层合同已建立；DeepSeek V2/V3 均未测出质量，当前候选已关闭且质量 unknown；G53-1/2 只有 adapter/probe 离线合同和公共 CI，历史 G53-3 首次认证失败已被后续普通 API 重开取代，RQ-177 的 3/3 协议接缝通过，RQ-178 仅完成 A/B 身份预检，尚无领域质量证据 | 阶段 5C 增加路由 Eval，5D 增加 Prompt Eval | G53-4/7 仍未完成；阶段 8 固定产品回归集和消融，领域质量须另开新鲜门 | 数字忠实度、引用、路由、工具选择、实验身份、注入漏判、失败归因、预算可达性与发布安全 | 部分完成 |
| Q02 | Trace 与 Observability | 5E Runtime Trace 已公开；8C durable event、8E Batch C cursor SSE、RQ-096 browser lifecycle 均公共闭环；E5 `ca6da44/32661425379` 又完成 body-free counter/p50/p95 bounded metrics projection | 阶段 5E | 8E/8F 后续增加长期时序、自动告警、正式容量和部署监控；不复制 raw Trace | run_id 串联版本、模型、工具、证据、耗时、决策、event cursor、reconnect、stream close、bounded metrics 和恢复结果 | 8C/Batch C/live/E5 公共闭环；长期生产观测待后续 |
| Q03 | Prompt/上下文注入防护 | 工具白名单、Schema、data-only sections、累积预算和实际 ToolExecutionRecord 证据；7-3 已公共验证固定远端 description、admitted subset、无 eval AST grammar 和 optional external-meta user section，拒绝代码/指令文本/schema drift；旧真实模型注入缺口仍不变 | 阶段 5D 建立不可信输入边界 | 已知 development 门完成；真实模型验证留给新鲜 Provider 门，阶段 6/7 扩展会话和 MCP 内容 | 恶意用户输入、恶意文档、恶意工具结果、评测漏判和越权测试 | 部分完成 |
| Q04 | 应用安全 | `.env` 隔离、日志脱敏、trusted Actor/owner 404 与 Batch B profile/routing 已有公共证据；E1/E2 又公共验证 opaque session/CSRF、request/header/body budget 与单机 IP limiter | 阶段 6 继续以 trusted ActorContext、owner-scoped Repository/复合约束完成 Session/Memory 隔离并保持公网 fail-closed | Stage 8 8E/8F 建立正式 OIDC/HTTPS edge、共享 limiter、CSP 与响应流程 | 密钥扫描、profile/subject owner 隔离、routing allowlist、限流、CORS/CSP、脱敏和依赖审计 | 单机安全 seam 公共闭环；正式公网安全产品化待完成 |
| Q05 | 数据生命周期与隐私 | 6A/6B-9 owner export、hidden-before-cleanup、marker retry、retention/purge 已公共闭环；E4 `27b9256/32660145945` 又完成 deletion marker restore replay、owner run locator 与 Artifact/Trace cleanup/补偿 | 阶段 6 已完成 Memory 的查看/导出/更正/删除/补偿 V1 | Stage 8 后续补 KMS/对象存储、加密 backup bytes、定时备份、公开隐私说明和 RPO/RTO 实测 | 原始比赛、Run、Memory 的保留、更正、导出、删除失败补偿、marker restore/erase 和真实灾备演练 | 在线/marker/Artifact cleanup 公共闭环；生产加密灾备待后续 |
| Q06 | 知识库更新与回滚 | 来源、版本、有效期和冲突策略已有 | 阶段 4 维护任务，公开部署前完成更新流程 | Stage 8 8D/8E 自动化索引构建、版本切换和回滚 | 新旧版本、失败构建、污染文档、EvidenceBundle 版本冲突和回滚测试 | 需显式补齐，入口已规划 |
| Q07 | 性能、Token 与成本 | 既有 Runtime 预算/实验账本保留；6A-6 在 PostgreSQL 17/Python 3.11 公共环境记录 8 样本 warm create/query p95 `6.220ms` 与 queued→claim p95 `23.359ms`，并验证 owner 3/global 50 可配置背压；这不是 SLA | 阶段 5E 定义运行预算，阶段 6 定义并实测 API SLO | G53 使用独立预算；阶段 6/8 增加真实 p50/p95、队列等待与产品成本趋势 | p50/p95、Token、工具次数、模型成本、背压、预算可达性和超预算停止 | 部分完成 |
| Q08 | 可靠性与故障恢复 | 6A receipt reconciliation/recovery-required/人工 CAS、8C cancel/lease/fencing/checkpoint/recovery/replay/late-result isolation 已公共；E4 又完成 marker restore replay/幂等/partial-failure compensation | 阶段 6 增加持久状态、幂等、短事务、有证据 reconciliation 与安全生命周期 | 真实加密备份和 RPO/RTO drill 仍属于 8E/8F | DB/Artifact 故障、并发 claim、进程中断、重复请求、自动/人工恢复、删除补偿和迟到结果测试 | 8C/E4 公共闭环；真实灾备演练待后续 |
| Q09 | 开源、部署与合规 | MIT、CI、README、SECURITY、匿名化样例；6A/E5 非 root image、Compose migration/readiness、no-I/O smoke 与 rollback boundary 已公共验证 | 横向交付检查点 | Stage 8 8E/8F 完成正式 Auth/HTTPS、加密备份、静态 Web 部署与作品集证据 | Linux/Docker 冒烟、密钥扫描、许可证、CSP/CORS、备份 restore、Web media budget 和公开边界检查 | packaging 公共闭环；公网部署/合规待后续 |
| Q10 | 前端可解释性、双语与可访问性 | Batch D fixture React `f7ebedd/32636771507`、RQ-096 live API/SSE `f441061/32647933692`、production shell `15a3a9e/32663345737`、Timeline `794032f/32682243568` 与 bilingual/product-journey foundation `6084937/32757872792` 已公共闭环 | Stage 8 8E 正式 Web 纵向切片 | RQ-108 design/state closure 与 runtime Task 1–4 已 exact-SHA 公共闭环；Task 5 已完成 official/relay 广筛、HyperFrames no-telemetry 隔离 spike，以及各一次 Wan/Veo 真实负面样本；Veo/RQ-125 已由 `e79a76e/32918278259` 公共关闭，C proof design/negative implementation 已由 `78ae6e3/32919447127` 与 `557dac1/32923151197` 公共关闭。RQ-126 已拒绝机械可控但视觉错误的 C overlay proof；RQ-127/129 将目标收紧为 locked-frame、精细 in-scene multi-depth medium/evident/cool motion；RQ-128 固定 local/request/transport/output-quality/method 五层故障归因，无 output 不评质量。RQ-117/118 固定 Account 拓扑抽象和 Portal 原水晶；RQ-121/122 把用户中转目录限制为 official-first 后的可验证 secondary transport，并要求广筛不等于扩大付费槽位。RQ-108 后 RQ-107 bounded Coach 与 RQ-103 的相对顺序待裁决。Data Dragon asset/detail enrichment、Evidence/Trace、Training full、OP.GG breadth/golden slice 与跨模块 final QA 继续未完成 | desktop/tablet/mobile、中英 text expansion/missing-key、三层 reload/history/zero-early-I/O、Link 四态、strict local manifest、cover/focal/hitBox、poster/preflight、场景内原水晶透明语义 hit target、codec/full-frame loop/poster-only fallback、Save-Data/媒体失败、下载/解码/JS 预算、relay mapping/privacy/compression provenance、layer/mask/inpaint、full-scene motion coverage、Account topology overlay/intentional-abstraction、英雄逐位解剖、键盘/focus、reduced-motion、axe、状态/数据边界和人工 QA | Task 1 focused 71、Task 2 focused 39、Task 3 focused 27、Task 4 focused 25；HyperFrames raw renderer check/重复 SHA 通过但 default MP4 seam/bytes reject；Wan/Veo samples rejected、C overlay proof rejected、Vidu Studio-contract sample rejected、external video calls 5、production media 0；Vidu 证明 API/first-only 可工作但 camera drift 失败，下一 Veo refined preflight 本地冻结，frontend unit 257、typecheck/build、bundle `144.07/18.50 kB` 本地通过；8E coverage 仍 planned |
| Q11 | 所有者学习与工程证据连续性 | RQ-067 已从阶段 0 重审真实缺口，并建立 `docs/learning/README.md`、八维 `coverage.yaml`、实现后 walkthrough/review、README 入口与治理红灯；成熟阶段直接复用既有设计/退出复核；本轮退出复核见 `docs/plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md` | 所有阶段的横向关闭合同，不新增主阶段 | 每个新 checkpoint 开始时可为 planned，关闭前补齐问题/原理、设计/实现、代码地图、数据/控制流、验证、运行、失败/安全/边界和面试表述 | coverage schema/path/sequence/当前 checkpoint/前序 complete 测试，聚焦与全量回归，独立提交和 exact-SHA CI `63435d9/32308631289` | 已完成（文档门公共闭环） |

## 4. 明确补齐项

2026-08-26 Q10 补充：Task 5 external video calls 仍为 `5`、production media `0`。refined Veo POST 的 403 已由
common log 证实为 `$15.008 < $19.712` 的预扣失败；充值后余额 `$65.01`。RQ-130 新增 paid-call content gate：
v5 spatial-orchestration 的 official motion-only/单场景、locked/deep-focus、全空间 simultaneous motion、八秒
闭环、negative phenomena、source/schema/runner/唯一路径必须先 exact-SHA 公共关闭，余额不能替代该门。

v5 preflight 已由 `d57b026/32951125621` 三 job 公共关闭；唯一 task `task_I5...k9Mw` 159 秒/100% generic failed，
无 output，`$19.712` 全额退款。Q10 当前 calls 6、production media 0；按 RQ-128 不评价 prompt/model/method，
先关闭 failure/terminal incident audit。

2026-08-26 Seedance 补充：Veo exact v1 后续也失败，当前通道暂停；Seedance 2.5 `adaptive` first+last task
`task_w6...ULvW` 成功并由 GET-only recovery 下载。Q10 当前 calls 9、production media 0；候选镜头/三大区运动方向
较好，但 source-first 0.864923、seam difference 0.060443、720p 未过门，等待用户 visual review。

RQ-133：用户认可方向但要求静区更丰富；Dragon 专用 Seedance 页已确认 `video_operation=edit`、
`video_with_roles(reference_video)`、`duration=-1`、`aspect_ratio=adaptive`。v6 edit runner/prompt 已冻结并公共
关闭；Studio 的视频参考 input 只收图片 MIME，故不冒充 Studio 编辑。后续 v6.1 task 前 400/费用 0，仍无成功
edit；未来成功输出也需人工静区运动、source/seam/codec 门，不直接 adopted。

v6.1 随后在 task 创建前 HTTP 400：source GET 成功、task id 空、费用 0、无隐藏 task；有效 calls 仍为 9。
原 runner 丢失 response body，因此确切字段 unknown。新增 strict body-free sanitizer/测试与 revised runner
digest 只补 observability，不构成远端修复或 retry 依据；production media 仍为 0。

豆包工作官方 comparator 使有效 calls 增至 10：Skill 以首尾帧+母图重生成，输出 source-first `0.407604`、seam
diff `0.144582`、AAC/移动水印，按视觉与生产门 rejected。RQ-134 将三主体全部增强（右侧单列）与全局环境同步
增强设为双硬门；暖金光轨只保留动作语言并转冷蓝/青蓝主色。下一即梦 `智能编辑` 尚未上传或生成。

RQ-135/即梦 preflight：第一轮只用成功 MP4 + v2 母图，高级编辑区域框选优先，不堆新审美图；v7 prompt
`edbc0d3...6f388` 已冻结。file picker 由用户操作，上传后仍需模式/时长/比例/720P/音频/积分/高级编辑 readback。

以下项目不是新增主阶段，而是进入对应阶段前必须具备的验收项：

1. 阶段 5C：建立路由评测集，覆盖正例、负例、歧义、未支持请求和拒绝原因；
2. 阶段 5D：实现 Prompt/Context Builder V1、结构化输出和不可信上下文边界；
3. 阶段 5E：将 Prompt、Skill、Provider、工具、Token、成本和终止原因写入统一 Trace；
4. 阶段 6：在引入 SQL 与 Memory 前定义数据保留、导出、更正、删除、鉴权和限流；
5. 阶段 7：将 MCP/Meta 返回内容视为外部不可信证据，经过 Adapter、版本和来源校验；
6. 阶段 8 Core：完成知识库更新/回滚、生产安全、备份恢复和完整产品回归。

8E Batch E 已把第 6 项进一步拆成可执行入口：Auth/RSO 身份分离、CSP/CORS/HTTPS/限流、Secret
生命周期、backup restore/erase、隐私说明、观测/容量和部署拓扑；这些仍是“已规划”，不能用现有
local/test Actor、Compose smoke 或静态 Web 截图冒充生产安全证据。

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

### 2026-08-27：Q10 Portal official Smart Edit 与后处理边界

- official 即梦 `Seedance 2.5 / 智能编辑` 有效调用使 Task 5 calls 为 `11`；raw SHA `4d3660b...155b`，
  production media 仍为 `0`。
- locked-camera、三大区和九宫格 coverage 有正向证据，但 source identity `0.889072 < 0.95`、seam
  `0.046536 > 0.03`；不能用“画面都动了”替代 source/seam gate。
- 零费用 FFmpeg 已证明音频、fixed24、BT.709、faststart 与 bytes 可修；最佳 J seam `0.042684` 仍失败并降低
  mother-first，因此不接 runtime、不继续 crossfade 追绿。
- 当前能力状态仍为“素材采用门部分完成”：先做 geometry/material/intended-energy identity fault split；若要
  新生成，必须改 source-side first/last/keyframe contract，不能原样重抽。
- RQ-137 把 GLM-5.3/Flash Provider refresh 排到 Portal Motion Polish 闭环后；A10/A11 的模型与 bounded Coach
  缺口仍保持未完成，不能因当前 Portal-first 顺序从矩阵消失。

2026-08-27 Q10/RQ-141 补充：Seedance 2.5 v3 first-frame-only 12 秒样本已完成 GET-only recovery，输出技术
编码可播放（1280×720、24fps、H.264/yuv420p、无音轨），但视觉门拒绝：左 Rift 硬同心环、道路基础流动延后、
中央 burst 过曝且出现横向穿屏线、右场在 burst 外近乎静止、near/mid/far 缺少持续呼吸。该样本只保留为
 research evidence，Task 5 external video calls 累计 `12`，production media 仍为 `0`；下一步先修订常驻基础运动 + 中央纵向低幅 burst 合同，不付费
重抽、不接 runtime、不据此否定模型。

2026-08-27 Q10/RQ-141 v4 preflight：已将源侧 brief 固定为“首帧即持续的 left/center/right 与 near/mid/far
基础运动 + 4.5–7.0 秒中央局部低幅呼吸”，删除易诱发穿屏连线的关系动词；prompt/manifest/runner digest 与
PowerShell parse/唯一 POST 静态门均通过。当前实际 POST 仍为 `0`，Image2 未使用，production media 仍为 `0`；
需用户明确允许并重新 readback 价格/字段后才可生成，且不降低 source/seam/全幕运动人工门。

`0006858` / Actions `33078261349` 的 exact-SHA pytest、真实 PostgreSQL migrations 与 packaging-smoke 已全绿；
这只证明 v4 合同/manifest/门禁的公共可重建性，不代表生成质量或 runtime 采用。

后续 v4 runner 在 POST 前发现并修复了 Windows CRLF digest 差异（runner SHA
`4aa7459cff78d462779137fed82d7edc84c0a0fc2d9ee539dbb4311b1c6a6dcc`）；pricing readback 为 `¥1.494570/s`、
12 秒估算 `¥17.934840`。实际 POST 在修复公共门完成前保持 `0`。

RQ-142 实际 v4 task 已完成一次并拒绝：source→first SSIM `0.989914`、first→last SSIM `0.994464`，但
center/left/right 每 0.5 秒 MAD `0.014625/0.005851/0.004653`，视觉变化集中为中央平台发光圆顶，右场与
整体环境不活跃。Task 5 calls `13`、production media `0`；当前暂停首帧盲抽，先做 prompt/mode fault split。

`c964016` / Actions `33083670925` 的 exact-SHA pytest、真实 PostgreSQL migrations 与 packaging-smoke 已全绿；
v4 失败审计公共可重建，但视觉采用门仍失败，Task 5 不进入 runtime。

RQ-142 method fault split：v3/v4 共同证明首帧模式的 source identity 较强但区域/时间运动控制不足；即梦 Smart
Edit 的 coverage 更好但 source/seam 失败；C-line 线条 proof 仅证明 HUD 覆层不可取。因此 A 首帧盲抽暂停，B
时间/区域编辑优先，C 纹理/位移混合为 fallback；下一动作是 B contract/no-cost preflight，production media 仍为 `0`。

B1 Smart Edit contract 已完成 no-cost preflight：1,977 字符主 prompt、`00:00/00:04/00:07` 三帧说明、
Video1/mother 双锚点和平台几何不可变规则均已 digest 绑定；当前未上传/未调用，需先做页面模式与输入角色 readback。

B1 readback 当前受即梦 Chrome 扩展/页面超时阻塞；初始页仅确认“全能参考”，Smart Edit 输入槽、积分和音频状态
尚未证实，未进行点击或上传。

C′ proof 已完成但视觉拒绝：结构/覆盖可控，运动仍过轻且 mask 边缘有贴层风险；B1 不重复付费。下一候选为
Kling v3 Omni 单图片引用模式，待专用 schema/prompt/价格 preflight；production media 仍为 `0`。

Kling v3 Omni image-reference comparator 的专用 schema/prompt/价格 preflight 已固定：`std/720p`、8s、16:9、
audio off、`metadata.image_list` + `<<<image_1>>>`，预计 ¥3.696。未调用、未上传旧视频，等待页面/账户 readback。

Kling image-only 结果已拒绝：source-first `0.860618`，左圆环/中央亮柱主导，右场与环境不活跃；Task 5 calls `14`，
production media `0`。停止 image-only 抽卡，下一门评估 reference-video/多模态控制或其他模型，先过 preflight。

Kling B2 video+image preflight 已本地冻结：base video result URL 执行时 GET-only/不落盘，v2 image identity、
1,856-char 专用 prompt、std/720p/8s/16:9/audio omitted、one POST 和 ¥3.696 估算。当前 GET/POST 0，待 public gate。

2026-08-28 Q10/RQ-143/RQ-144 补充：masked-inpaint Rift proof 的局部遮罩/编码机械门通过，但透明层在可见强度下
呈廉价蓝带，候选拒绝且 production media 仍为 `0`；不再通过通用 plate 或 opacity 追绿。用户已授权一次 Wan 3.0
官方 first-frame-only 重开：active v2 母图只作 `first_frame`，`last_frame` 不再复用，使用 adaptive/1080P/12s、
audio/prompt_extend/watermark off 与 motion-only brief。需先完成同区 endpoint/额度/价格/source/prompt SHA
preflight，再执行 one POST；结果仍须通过全幕材质运动和人工视觉门，不能直接接 runtime。Data Dragon、Coach、8F
和最终 Account/Portal visual QA 继续未完成。

RQ-145 条件回退已记录：若 Wan 3.0 官方 first-frame-only 重开仍未通过人工视觉门，停止自制整幕视频，改评估
Riot League Displays 官方地区动态壁纸作为 Portal 候选，并用静态壁纸作为 Account 候选；必须先核对来源/许可、
格式、体积、浏览器/桌面可播放性、移动端与 reduced-motion fallback，当前不算采用。

RQ-146 已激活该回退：Wan 停止在 HTTP 404/no-task 诊断，Demacia WebM 进入研究审计；随后 Bandle City WebM 也以
research-candidate 登记。下一实现切片继续是 region wallpaper catalog 与 no-I/O local preview，不改变现有
Portal→Account→Workbench 业务控制流；两份候选均须通过来源/许可、格式、loop、浏览器与 reduced-motion 门后才可采用。

2026-08-29 UI hygiene 补充：该 presentation capability 现在还验证显式
`surface=wallpaper-lab` 地区 URL、selection `replaceState`、legacy alias fail-closed、Account return marker、
history scroll reset、fixed viewport media layers、semantic landmarks/skip focus、aria selection state、intrinsic
media dimensions 与 stale activation generation。它仍是 research preview；不改变 Auth/
Riot identity、Workbench 消费者、默认 `/` 或 `production_media=0`。

2026-08-29 RQ-157/158 presentation refinement：Portal 现在需要独立的 13-region identity capability 和 optional
wallpaper capability，而不是用 candidate existence 禁用 identity。横向 Focus Rail、selected detail hero、generic
sign-in CTA 与 region-aware handoff 继续使用现有 React/CSS/Motion，无新依赖；presentation region 不进入 Riot
routing。Account Bandle still 与 detail emblems 仍 research-only/rights-unverified，production media 保持 0。

2026-08-29 RQ-159 capability refinement：新增独立 `regionPresentationCopy` registry，把 13 区双语产品文案从
wallpaper/media catalog 和 Riot routing 中拆出；UI 不再从 media readiness 推导人类文案。`ProductJourney` shared shell
暴露 `closing/background-handoff/idle` phase，Portal overlay 与 Account arrival 共用该状态完成可测试的视觉交接，
focus/reduced-motion/Back URL 仍是显式合同。该能力不更改 Auth 或 Workbench 消费者。

2026-08-29 RQ-160 capability refinement：Portal 与 Account heading 采用“完整 accessible name + 显式 visual lines”模型，
中英文分别冻结两行断点并通过 desktop/390px overflow 证据。该能力只增强 i18n typography 的确定性，不改变导航、
Auth、Riot routing、Workbench 或 media adoption。

2026-08-30 RQ-161 capability refinement：Account panel 的桌面垂直位置改用独立 `top` 通道，避免与 handoff
transform 动画耦合；移动端显式归零。Riot ID input 与两个 Account select 共享 Manrope body typography，caption
使用统一可读字阶，并以 computed-style E2E 覆盖 desktop/mobile。该 presentation hygiene 不新增运行时能力、
依赖或 coverage group，不改变 Auth、Riot routing、Workbench、media adoption 或 `production_media=0`。

2026-08-30 RQ-162 capability refinement：Void 详细徽章支持用户提供的透明 WebP 资源，并保留 Universe crest
fallback；Portal/Account 的面板与背景叠层采用较低遮挡的局部 token，恢复背景可读性。仅影响 presentation layer，
不新增 runtime capability、依赖或 coverage group，不改变 Auth、Riot routing、Workbench、media adoption 或
`production_media=0`。

2026-08-31 RQ-173 capability refinement：为诊断 RQ-172 F7 的 `max_tokens=512` length 截断，独立 follow-up 仅将
上限调至 2048；`1/1` call、`557` tokens、`finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15
chunks，source identity stable、`cached=0`。结果标记 `vendor_raw_transport_only`、`production_admitted=false`、
`public_ci_confirmed=false`，不新增 provider-neutral streaming、Agent 生产或领域能力，不改变默认模型、Workbench、
Auth、前端或 `production_media=0`。

2026-08-31 RQ-176 runtime capability refinement：Flash-only 产品接线现在要求 profile 在组合阶段显式绑定，或
仅从已绑定同一注册 profile 的 concrete Provider 自动推断，并把同一 profile 身份写入 Runtime policy/Trace；不允许
通过仅匹配模型名的测试 double 偷渡 90 秒预算。该项
只完成本地实现与回归，不能替代新 exact-SHA 公共 CI、同 SHA G53-3、G53-7 领域门、黄金切片或生产部署合规。

### 2026-08-31：RQ-180 G53-7 领域门结果校正

在最终实现 A=`9e6d78be…`、证据 B=`7cb66d2…` 及各自公共 CI 见证后，G53-7 仅执行一次真实尝试：协议 3/3，
领域 2/12，累计 5/15 calls、领域 3505 tokens。首例以适配器安全聚合码
`provider_response_invalid/incomplete_chat_response` 停止，后两例跳过，`admitted=false`；结果 SHA-256 为
`21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，本地 C=`9157cde…` 承载且未取得公共 CI。
由于底层 finish reason 未保留，不能把失败解释为 `length`；该结果不增加领域/生产能力，8E coverage 仍按未完成处理，
不改变 Portal、Account、Workbench、Auth、路由或 `production_media=0`。当前停止自动重试，后续须新建版本化诊断。

### 2026-08-31：RQ-181 Flash 响应完成度能力边界

独立诊断把 RQ-180 的聚合码拆解为可核验的响应状态：首个 `agent_initial` 回合原始
`finish_reason=length`，input/output Usage 为 `2220/2048`，正文为空、reasoning 非空、ToolCall 为 0，
适配器返回 `incomplete_chat_response`，normalized/settled 为 `0/1`。这证明当前 `enabled/max/clear_thinking=false`
档案在该长上下文案例中先耗尽受控 2048 输出额度，并不证明模型一般能力或账号状态。

结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
的 canonical-LF SHA-256 为 `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`；该文件只保留
脱敏状态字段，不含 Prompt、正文、reasoning、Key、请求 ID 或工具参数。能力矩阵仍将响应完成策略标为待设计，
不把一次诊断提升为 G53-7/生产准入，也不改变默认模型、Stage 8/8E、Portal/Account/Workbench/Auth、路由或
`production_media=0`；下一项是版本化策略的离线 TDD。

### 2026-08-31：RQ-182 response-completion capability boundary

新增独立的 `ResponseCompletionPolicy` 能力，用精确 provider/model/runtime identity、脱敏响应边界快照和受信
请求上下文表达完成、工具回合、截断拒绝及候选形状。当前注册策略保持 Flash 2048/零额外调用；8192/一次
fresh-recovery 仅为未注册候选，不能通过 metadata、模型输出或调用方隐式启用。该能力不修改统一消息模型、
AgentLoop、ToolRuntime、Trace/预算账本、默认模型、Workbench、Auth、媒体采用或 `production_media=0`；
离线 TDD `41 passed` 不等于恢复能力、领域准入或生产成熟度。

### 2026-08-31：RQ-183 candidate-recovery capability boundary

新增独立的候选 runtime/attempt/预算/Trace 合同：`ResponseRecoveryRuntimeProfile`
精确绑定 `zhipu/glm-5.3-flash` 与 `glm-5.3-flash-runtime-v2-candidate/2.0.0`，
`ResponseRecoveryLedger` 将 `primary` 与最多一个 `fresh_recovery` 作为独立底层调用
预留和结算，并累计 input/output/elapsed 资源；`ResponseRecoveryTrace` 使用独立 schema
1.0，仅保留脱敏结束原因、字段状态、ToolCall 数量、判定和资源数字。候选计划始终
`execution_allowed=false`，不修改现有 `RuntimeTrace`，也不进入产品注册表。

聚焦合同测试 `30 passed`，相邻回归 `128 passed`；这些证据只证明本地状态机和边界，
不证明 Provider 恢复、G53-7、领域采用或生产成熟度。严格 Flash v1 的 2048/零额外调用、
默认模型、Portal/Account、Workbench、Auth、路由和 `production_media=0` 不变；候选
后续仍需 exact-SHA 公共 CI、同 SHA G53-3、单独真实诊断授权及成本/延迟/失败审查。

### 2026-08-31：RQ-184 candidate-recovery public evidence boundary

候选合同的实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654` 已由 Actions run `33405110692` 的三 job 公共验证；
同一 A checkout 的 G53-3 严格 `3/3` 调用通过（A1 `1/1`、A2 `2/2`，`admitted=true`，SDK retries `0`）。脱敏结果
由直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 唯一新增，B 的 Actions run `33405881172` 三 job 全绿；
A/B 无 I/O identity preflight 通过，结果 canonical-LF SHA-256=`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

这只证明候选合同的公共可复现性与协议身份接缝，不注册候选、不执行 fresh-recovery 或 G53-7；严格 Flash v1 的
2048/零额外调用、默认模型、Portal/Account、Workbench、Auth、路由及 `production_media=0` 不变。下一项需用户单独
授权一次候选恢复诊断，并审查成本、延迟、失败与脱敏 Trace；8E/8F 仍未完成。

### 2026-09-01：RQ-186 request-deadline capability boundary

隔离诊断能力现在能把受校验的 deadline 直接写入每次 SDK payload，并保证 primary 与唯一可能的 recovery 共享
请求级硬上限；测试和一次真实调用均确认 `timeout_s=30` 生效。真实 primary 在约 30.141 秒以 transport timeout
安全关闭，没有响应、Usage、finish reason 或 recovery；结果 SHA-256 为
`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`。

该能力只补足诊断可终止性，不增加模型、恢复、领域或生产能力；30 秒低于候选 90 秒 Agent 窗口。候选仍
`execution_allowed=false`，严格 Flash v1、统一 RuntimeTrace、产品模块和 `production_media=0` 均不变。

### 2026-09-01：RQ-187 full-window transport boundary

在 90 秒请求级窗口、8192 输出上限和零 SDK retry 下，唯一 primary 仍在 90.188 秒以 transport timeout
安全关闭；没有响应、Usage、finish reason 或 recovery。结果 SHA-256 为
`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`。这排除短窗口假设，但不能区分代理/读取
与服务端生成延迟；能力矩阵不升级候选、领域或生产能力，严格 Flash v1 与产品边界保持不变。

### 2026-09-01：RQ-188 transport/generation split capability boundary

三路 body-free 探针（合法 Flash thinking 最小控制、冻结短同步、冻结流式首块）均观察到响应；同步两路为
`length + 空正文 + 非空 reasoning`，流式路观察到首个 `delta_reasoning` chunk 后主动关闭。正式结果
SHA-256=`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，代码/source identity=
`b67b4500ebdbff934e470fd92c1461184aa7c49b`。这确认 endpoint/model 路径可达并已开始生成，但不证明完整
provider-neutral streaming、长请求根因、领域采用或生产成熟度；候选保持未注册，严格 Flash v1 与产品边界不变。
下一项是 evaluation-only 的输出额度/推理档位校准，不改统一 RuntimeTrace、Provider 接口或默认模型。

### 2026-09-01：RQ-189 output-budget calibration capability boundary

三份独立 body-free 观测固定同一冻结上下文和采样参数：`low+2048` 在约 28.344 秒得到可见正文并正常 stop；
`low+8192` 与 `max+8192` 在约 45.5 秒请求截止内无同步响应。能力矩阵因此新增一条“低推理短同步可完成、
高预算同步延迟未定”的候选观察，但不把它投影为 Provider-neutral 完成合同，也不改变当前严格 Flash v1 的
2048/零额外调用。流式首个可见正文、完整终止/Usage、候选注册、G53-7、生产安全/部署/合规仍未观测。

### 2026-09-01：RQ-190 stream-visible-content capability boundary

新增 evaluation-only 原始流式探针，固定低推理/2048 输出上限，并分别记录 `clear_thinking=true` 与 `false` 的首块和
首个可见正文延迟。两路均能打开流并在约 2.5–3.9 秒出现可见正文，但探针会在首正文后主动关闭，终态/Usage 和
观测 token 预算均未知。该能力不能投影为完整 provider-neutral stream、跨轮思考清理、候选注册、领域采用或生产能力；
严格 Flash v1、统一 RuntimeTrace、产品模块和 `production_media=0` 不变。下一项是完整终态/Usage 的候选探针。

### 2026-09-01：RQ-191 complete-stream capability boundary

在当前 `clear_thinking=false`、低推理、2048 形状下，原始流完整消费成功：首块/首正文约 2.203s/3.531s，
24.140s 以 `stop` 结束并取得有效 Usage。该证据只支持“此冻结上下文的供应商流可完整终止并可计量”，不支持一般模型
质量、长上下文/高预算延迟、跨轮思考语义、工具流或 provider-neutral runtime 已接入；候选、严格 Flash v1、统一 Trace、
产品模块和 `production_media=0` 均不变。下一项是离线流式装配合同。

### 2026-09-01：RQ-192 provider-neutral stream assembly capability boundary

新增离线候选接缝，将供应商分块映射为规范化事件，再由单次装配器在 EOF、terminal 和有效 Usage 齐备时生成
`ChatResponse`。合同固定终止后 Usage-only 尾帧、序号/model/请求摘要稳定性、正文与工具互斥、工具 JSON
连续索引/重复键/有限数字/深度及字符数量上限，并在错误后毒化；工具状态 copy-on-write、参数字符增量计数，
内部结果 repr 隐去正文与工具参数。聚焦测试 `29 passed`，相邻回归 `147 passed, 27 subtests passed`。

能力矩阵只把它记为 candidate-only offline seam：不代表 `capabilities.streaming`、产品 runtime、工具流、跨轮
思考回放、领域或生产准入；不注册候选、不改严格 Flash v1 2048/零额外调用、统一 Trace、产品模块或
`production_media=0`。下一项是同一实现 SHA 的公共 CI 与 provider conformance。

### 2026-09-01：RQ-193 Zhipu provider conformance capability boundary

在 RQ-192 的候选接缝上，测试内 `_FixtureZhipuStreamAdapter` 将代表性的 OpenAI-compatible 智谱分块安全翻译为
`ProviderStreamEvent`，并与现有 `ZhipuProvider.chat_stream()` 的 fake-client 结果逐字段核对。覆盖正文/reasoning、
工具别名与参数分片、坏形状/未知工具/空 choices、model/terminal 边界、迭代器异常 `abort()`、正文空白保留与
Trace 脱敏；conformance 聚焦 `13 passed`。

提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的 Actions run `33489903978` 三 job 全绿且 head_sha 精确匹配，
因此该提交范围（含全部 Trace 脱敏断言）的公共可复现性已确认。
矩阵仍只标记 candidate-only seam：不把 `capabilities.streaming` 改为 true，不宣称产品 runtime、工具流、跨轮
思考回放、领域/生产准入或公共部署；候选、严格 Flash v1 2048/零额外调用、统一 Runtime Trace、产品模块和
`production_media=0` 均不变。下一项为候选接线裁决，而非自动启用。

### 2026-09-01：RQ-194 explicit Zhipu→neutral adapter seam capability boundary

RQ-194 已从设计占位落为候选级、调用方显式触发的本地接缝：
`app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamAdapter`（不实现 `LLMProvider`）提供
`stream_events(request)` 与 `assemble(request, *, max_output_tokens=None, require_request_identity=True)`；
`ZhipuProvider.stream_adapter(*, tool_stream=False)` 是显式工厂，底层通过
`_open_stream_for_adapter()` 和 `_validate_stream_response_for_adapter()` 连接现有 provider。
适配器把已绑定的 Zhipu raw chunks 翻译为 `ProviderStreamEvent`，再交给 `ProviderStreamAssembler`，并保证单次开流。

可信 provider runtime profile 的 `max_output_tokens` 上限（1–8192）是硬边界，请求/显式 cap 只能收紧；默认要求
request identity，Trace/错误只保存 SHA-256 摘要。只有真实 EOF、合法 terminal 和有效 Usage 同时成立才完成；取消、
迭代器/翻译/关闭异常均 `abort()`/fail-closed，不 retry、recovery 或 ToolRuntime，不注册 recovery，只支持 fake/local evidence。
提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588` 已三 job 全绿且 head_sha 精确匹配；
`tests/test_zhipu_stream_adapter.py` 为 `20 passed`。这只证明候选接缝公共可复现，仍不标记为产品或生产 capability。

`capabilities.streaming` 仍为 `False`；严格 Flash v1 2048/零额外调用、默认模型、同步/既有流接口、AgentLoop、ToolRuntime、
Runtime Trace、预算、Workbench、Portal、Account、Auth、路由和 `production_media=0` 均不变，候选未注册。下一项是独立的
候选 runtime 接线裁决；矩阵不将其标为生产能力、领域准入或 8-Core 必需项。

### 2026-09-01：RQ-195 候选 runtime 接线架构能力边界（历史状态）

RQ-195 把“候选 adapter 可装配完整流”和“候选 runtime 可安全恢复”分成两项能力。现有
`ZhipuStreamAdapter.assemble()` 只交付 EOF、terminal、Usage 齐全的完整 `stop`/`tool_calls` 流；不完整流和异常
必须 fail-closed。候选资格不能由 `StreamAdapterError`、私有正文或 reasoning 反推。

未来若获单独授权，能力矩阵要求隔离的 `CandidateStreamEvaluationHarness` 精确绑定 zhipu/model/profile/policy 四元
身份，并先提供 body-free `BoundaryObservation`、ledger 生命周期和 allow-list `ResponseRecoveryTrace` 投影；不得
自动注册为 `LLMProvider` 或打开产品 streaming。候选仍未注册、`execution_allowed=false`，严格 Flash v1 2048/零额外调用，
默认 Runtime、Workbench、Portal、Account、Auth、路由和 `production_media=0` 不变。下一项为
`candidate-runtime-wiring-design / pending`，不标记为生产能力、领域准入或 8-Core 必需项；该下一项已由 RQ-196 更新。

### 2026-09-01：RQ-196 候选 runtime 接线设计能力边界（历史状态）

RQ-196 将 GLM-5.3-Flash 记录为当前唯一主力候选目标，但仍属于 8E 内受控高级实验设计，不是 8-Core 生产能力或默认模型。
能力矩阵冻结 `CandidateRuntimeBinding` 的四元身份与尝试序号、body-free `BoundaryObservation`、共享事件校验、完整流/不完整
流分流、隔离 v2 transport 和独立 Trace 投影。候选 v2 的单次 8192 cap、90/120 秒窗口和累计预算只对显式 evaluation 调用方
有效；未知 Usage 不得当零，当前 `execution_allowed=false`。

未改 `LLMProvider`、AgentLoop、Worker、统一 Runtime Trace/预算、`capabilities.streaming`、默认模型、Portal、Account、
Workbench、Auth、路由或 `production_media=0`。当时下一项为
`candidate-boundary-observation-contract-implementation / pending`；该门已由 RQ-197 推进。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 将 RQ-196 冻结的边界落成隔离的 fake/local 实现：新增
`app/evaluation/candidate_stream_contract.py`，提供精确 `CandidateRuntimeBinding`、body-free
`BoundaryObservation`、不可变状态快照、字段 presence 聚合、候选 v2 注入式 transport port 和独立
`CandidateStreamTrace`。`ProviderStreamEvent` 的显式 null/缺失标记与
`validate_provider_stream_event()` 让完整 `ProviderStreamAssembler` 和候选观察器共享事件级 model、sequence、tool、Usage
及大小限制；观察器只保留计数、状态、耗时和 SHA-256，不保存正文、reasoning、Prompt、工具参数、Key 或 SDK 对象。

本地失败矩阵覆盖完整 `stop`/`tool_calls`、`length` reasoning-only、缺 EOF/terminal/Usage、身份/序号/工具/预算/时钟/关闭
异常及状态伪造；不完整或异常流均 fail-closed，不构造 `ChatResponse`，unknown Usage 不当零。候选仍
`activation_state=candidate`、`execution_allowed=false`，`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用、默认
模型、AgentLoop、Workbench、Portal、Account、Auth、路由和 `production_media=0` 均不变。聚焦与相邻回归为 `163 passed`；同一
干净实现提交的 exact-SHA 公共 CI 尚待验证，因此本地实现不标记为生产能力、领域准入或 8-Core 必需项。

RQ-198 已取得同 SHA 公共 CI：提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run
`33507627615` 三 job 全绿，公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
RQ-199 已完成 candidate harness 设计；当前唯一下一项是 `candidate-evaluation-harness-implementation / pending`，
之后才另行裁决 fresh-recovery、G53-7 和生产准入；候选仍未注册，`execution_allowed=false`，`capabilities.streaming=False`，
`production_media=0` 不变。

### 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

本公共 CI 只证明 RQ-197 的隔离 fake/local 边界合同可复现，不改变 8E/8-Core 生产能力矩阵，也未触发真实 API、
recovery、G53-7 或产品 Runtime 接线。本轮到此暂停。

### 2026-09-02：RQ-199 候选评估台设计能力边界

RQ-199 新增的是 `design-complete / implementation-pending` 的候选协调能力，不是已实现的
Runtime capability。设计把现有 observer、assembler、completion policy 与 recovery budget 连接为：

```text
exact candidate RunSpec
  → staged ledger reserve(primary)
  → one-pass normalized event pump
      ├─ body-free BoundaryObservation
      └─ ephemeral complete assembler
  → real snapshot + policy reclassification
  → settle + independent CandidateEvaluationReceipt
```

staged ledger 解决首回合快照在 I/O 前未知的问题；禁止 sentinel snapshot、结束后才 reserve、
caller eligibility 和隐式 retry。receipt 只保留身份、生命周期、字段状态、Usage/耗时、预算和
安全码，unknown Usage 不当零；完整正文只可经显式 evaluation consumer 短暂使用。当前 activation
仍 disabled，候选不注册、不打开 `capabilities.streaming`、不接产品 Runtime/AgentLoop/统一 Trace，
也没有真实 API、fresh-recovery、G53-7 或黄金切片证据。因此 capability matrix 仍把它列为
8-Advanced candidate design，8E/8-Core 生产成熟度不变，`production_media=0`。

唯一下一项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`；
下一门只允许 fake/local 实现和公共 CI。

### 2026-09-02：RQ-200 候选评估台本地实现能力边界

RQ-200 将上述候选设计实现为隔离的 `CandidateEvaluationHarness`，但仍不是 Runtime capability。
candidate-only staged ledger 在 primary I/O 前预留槽位，单次 normalized event pump 同时驱动
body-free observer 与一次性内存 assembler，真实边界观察后才重算 completion policy 并 settle；
独立 `CandidateEvaluationReceipt` 只保留身份、生命周期、字段状态、Usage/耗时、预算确定性与
安全码。完整 stop/tool 流才可交给显式 evaluation consumer，不完整流、未知 Usage、资源/身份/
序号/预算/时钟异常均 fail-closed，不构造产品 `ChatResponse`。

本地 harness 聚焦 `15 passed`，与边界观察、流装配和旧恢复合同相邻回归 `102 passed`；编译、
diff check、governance 通过。RQ-201 已补齐实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的
exact-SHA 公共 CI run `33536168224`（三 job 全绿，公共 pytest `2193 passed, 145 skipped, 1 warning, 127 subtests passed`）。
activation 仍 disabled，候选不注册、不打开 `capabilities.streaming`，严格 Flash v1 2048/零额外调用、
默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。该项仍属于
8-Advanced candidate evidence，不是 8-Core 或公共生产准入；当前下一项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`，
只允许在单独授权后复核 recovery 边界。

### 2026-09-02：RQ-202 候选 recovery 诊断复核能力边界

RQ-202 新增的是 `completed-local / candidate-only` 的审计加固，不是新的 Runtime capability。
`CandidateEvaluationReceipt` 现在从观察重新推导顶层 state/action/error、attempt decision/assembly
和 budget projection；observer 以单次 90 秒 attempt 窗口为上限，ledger 仍维护累计 180 秒。旧同步
诊断器的 SDK/真实 I/O 与 unknown-Usage 零值投影被明确排除在新版本之外。

本地证据为 harness `18 passed`、相邻集合 `127 passed, 1 deselected`、compileall/diff/governance
通过；加固提交 `67031145d3b3e5c864e881576c69e2fda931e950` 的 Actions run `33582049836` 三 job
exact-SHA 全绿，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。候选仍未注册、
activation disabled、`execution_allowed=false`、`capabilities.streaming=False`。
严格 Flash v1、默认 Runtime、产品模块、Portal/Account/Workbench/Auth、路由和 `production_media=0`
不变；不宣称领域、生产或 8F 能力。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`。

### 2026-09-02：RQ-203 版本化候选 recovery 诊断设计能力边界

RQ-203 只新增 `design-complete / candidate-only` 的评估协议设计，不新增 Runtime capability。
协议 `glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0` 绑定候选身份与 SHA，冻结
`reserve → observe → settle`、单次/累计预算、Usage/费用三态、分段延迟、失败第一现场和
body-free 原子回执。该设计不包装 `LLMProvider`、不注册候选、不打开 `capabilities.streaming`，不写
统一 Runtime Trace；实现、真实 recovery、G53-7、黄金切片、生产准入和 8F 仍未发生。

严格 Flash v1、默认模型、AgentLoop、Portal、Account、Workbench、Auth、路由和 `production_media=0`
不变，Stage 8/8E 继续 `in_progress`。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`。

### 2026-09-02：RQ-204 版本化候选 recovery 诊断实现能力边界

RQ-204 将 RQ-203 的协议设计实现为 `completed-local / candidate-only` 的评估证据，仍不是
Runtime capability。新模块位于 `app/evaluation/candidate_recovery_diagnostic_v2.py`，以
candidate-only staged ledger、一次 normalized event pump、body-free observer/receipt 和
派生预算/费用/失败投影组成；没有 Provider/AgentLoop/产品 Runtime 注册或真实网络入口。

新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归 `82 passed`，
compileall、静态 no-I/O/import 与 diff check 通过。候选 activation 仍 disabled、
`execution_allowed=false`、`capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、
默认模型、Portal/Account/Workbench/Auth、路由和 `production_media=0` 不变。未知 Usage 或未
验证价格保持 unknown/null；没有真实 recovery、G53-7、黄金切片、生产准入或 8F 证据。

下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`，
先取得同一干净实现提交的 exact-SHA 公共 CI 与协议 dry-run。

### 2026-09-02：RQ-205 版本化候选 recovery 诊断公共能力边界

RQ-205 已为 RQ-204 的 candidate-only 评估接缝取得同一实现提交的 exact-SHA 公共证据：
`90242822df0e47304700644572bc12f0a3aa88ad` / Actions `33598541029` 三 job 全绿；公共 pytest
`2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`，
并完成一次 fake/local body-free 协议演练。该项仍是 8-Advanced evaluation evidence，不新增 Runtime capability，
不包装 `LLMProvider`、不注册候选、不打开 `capabilities.streaming`，不写统一 Runtime Trace。

候选 activation 仍 disabled、`execution_allowed=false`；严格 Flash v1 2048/零额外调用、默认模型、
AgentLoop、Portal/Account/Workbench/Auth、路由与 `production_media=0` 不变。没有真实 recovery、G53-7、
黄金切片、生产准入或 8F 证据。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`。

### 2026-09-02：RQ-206 候选真实主请求观察能力边界

RQ-206 只新增一次有界真实观察证据，不新增 Runtime capability。干净隔离工作树上的
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` / Actions `33603143606` 三 job exact-SHA 全绿；
普通智谱 `zhipu/glm-5.3-flash` primary 只调用 1 次，流观察到 reasoning、可见正文、`stop` 和 EOF，
但 Usage 缺失、close 失败，90 秒 attempt 门在晚到事件中触发，最终 `fail_closed / elapsed_limit`。
首事件 `3078ms`、首个可见正文 `151453ms`、总延迟 `175875ms`；`open_elapsed_ms=0` 仅是惰性流计时起点。

持久回执是 canonical body-free JSON（`4355` bytes，SHA-256
`2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`），`calls_reserved/settled=1/1`、
费用 unknown。该证据不构成 API/Key、模型一般能力、领域准入或生产成熟度结论；候选仍 disabled、未注册，
`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用、默认模型、产品模块和
`production_media=0` 不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
先离线验证硬墙钟取消、流关闭与 Usage/终态尾帧处理。

### 2026-09-02：RQ-207 候选流硬墙钟/Usage 尾帧能力边界

RQ-207 在本节形成时的能力状态为 `candidate-only / completed-local / public-ci-pending`；该状态是历史快照，
RQ-208 已完成其 exact-SHA 公共 CI，但不新增产品 Runtime capability。显式 `CandidateStreamSession` 持有流资源，`CandidateStreamDeadlineSupervisor` 以 attempt
起点的绝对 monotonic deadline 做直接检查；超时采用协作式、幂等 cancel/close，抑制截止后的迟到事件。
完成合同要求终态与 Usage 同帧，或终态后恰好一个 Usage-only 尾帧；重复/过早/终态后内容和空非 Usage 帧
fail closed，Usage 缺失与价格保持 unknown/null，close 失败仅为次级证据，安全映射不暴露 provider body/exception。

legacy `open_stream() -> Iterable` 仍受支持；hard mode 必须显式提供 session opener。显式 opener 返回 legacy
iterable 时，校验只能在 opener 返回后完成；同步 opener 可能阻塞越过 timer，SDK `close()` 的非阻塞/唤醒
保证仍待真实 provider 验证；公共 CI 只证明候选接缝可复现，不能把本地实现当作生产超时保证。四文件聚焦回归（deadline 10、v2 24、real 8、
adapter 25）统一为 `67 passed`，
未调用真实 API。候选仍 `activation_state=disabled`、`execution_allowed=false`、
`capabilities.streaming=False`，未注册；Stage 8/8E 保持 `in_progress`，产品模块、默认模型、路由和
`production_media=0` 不变。

> 历史快照（RQ-207 本地实现完成时）：当时的下一精确 checkpoint 曾为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
> RQ-208 已完成该公共 CI，当前唯一指针以最新 RQ-208 段落为准。

### 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

RQ-207 的候选硬墙钟会话、取消/关闭资源合同与 Usage 尾帧离线实现，已在提交 exact SHA
`015b022bfce6d03452f753794ac126a377f8355b` 取得 Actions run `33613113829` 的 exact-SHA 公共 CI 闭环；
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均为 `completed/success`。本地四文件聚焦回归为
`67 passed`，公共 pytest 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为
`201 passed, 1 warning`。

该公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 的非阻塞/唤醒能力，也不构成模型一般能力、
领域采用或生产成熟度结论；同步 opener 永久阻塞与 SDK close 无法唤醒 `next()` 仍需真实 provider 验证。候选仍
`activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1
2048/零额外调用，默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变，
Stage 8/8E 继续 `in_progress`。

> 上述 `public-ci-pending` 与旧 checkpoint 仅记录 RQ-207 当时状态；当前唯一下一精确 checkpoint 以紧随其后的 RQ-208 段落为准。

> 历史快照（RQ-208）：当时的下一精确 checkpoint 为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
> 公共 CI 已闭环。当前指针见下方最新 RQ-212 段落。

### 2026-09-02：RQ-209 候选真实硬墙钟观察能力边界

RQ-209 新增的只是一次 candidate-only 真实观察，不新增 A03/A10/Q02 或任何产品 Runtime capability。单次
`zhipu/glm-5.3-flash` primary 在 `90015ms` 触发 attempt 硬墙钟并 `fail_closed / elapsed_limit`；首事件/打开
计时 `3421ms`，reasoning 非空，但没有可见正文、terminal、EOF 或 Usage。组合会话 `close_state=failed` 只
表示清理结果，不能归因到某个供应商 SDK 资源，也不能证明 close 非阻塞或唤醒 `next()`。

回执路径为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json`，
SHA-256 `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`、`4342` bytes，由本地证据提交
`0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存；公共 CI 尚未宣称。候选仍为 activation gate disabled、
`activation_state=candidate`、`execution_allowed=false`、`capabilities.streaming=False`，且未注册，严格 Flash v1
2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0`
不变；当时的下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
当前指针见下方最新 RQ-212 段落。

### RQ-210：候选关闭报告能力边界（2026-09-03）

RQ-210 新增的只是候选内部内存 seam：`ZhipuStreamCloseReport` 为迭代器和外层 SDK stream wrapper 提供 body-free
的分资源状态投影，并维持旧 `close_failed` 兼容。A03/A10/Q02 及其他产品 capability 均 unchanged；没有新增
持久 receipt 字段、raw HTTP response 控制、非阻塞 close 或 wakeup 证据。实现本地聚焦 73 passed、相邻集合
182 passed/27 subtests；这些是候选可复现性证据，不是 provider 或公共生产能力。Actions `33657368435` 三 job 已
`completed/success` 且 head SHA 精确匹配；公共 pytest `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，
PostgreSQL 控制面 `201 passed, 1 warning`。

### RQ-211：候选 close/wakeup 观察能力边界（2026-09-03）

RQ-211 不新增 A03/A10/Q02 或任何产品 Runtime capability。一次真实 candidate-only 探针在 c311
exact-SHA 公共绿灯快照上得到 `not_pending`：会话打开并观察到 reasoning/content 类别，但没有形成 pending
reader，因而没有执行 cancel。迭代器、外层 SDK stream wrapper 与组合关闭投影均为 `closed`，这仍不能证明
底层 HTTP response 可取消、close 在挂起读取时非阻塞或能唤醒 `next()`。

回执为 `908` bytes、SHA-256
`9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`，只含允许列表状态。
候选继续 disabled/未注册，`capabilities.streaming=False`；能力矩阵和 `production_media=0` 均不变。

公共验证补充：提交 `1c669e0` / Actions `33666132282` 三 job exact-SHA 全绿，provider capability 扫描
已能解析 RQ-211 的 schema；这只是合同识别证据，不是新的 provider 或产品 capability，也没有新增真实 API。

### 2026-09-03：RQ-212 候选 close/wakeup 离线回放能力边界

RQ-212 仍属于 8-Advanced 的 candidate-only evaluation evidence，不新增或重排主阶段，也不把离线回放
提升为 8-Core 产品能力。固定 Event 闸门重放正常 EOF、取消后唤醒、取消返回但未唤醒、取消超时和取消抛出
五种场景，回执独立标记 `evidence_origin=offline_fake`、`real_provider_observed=false`、
`provider_call_count=0`、`network_used=false`，并把 `fake_session_open_count=1` 与观察器调用次数分开。
它只证明本地分类、单次 fake 打开、脱敏和不可变回执可重复；不证明供应商 SDK close 非阻塞、底层 HTTP
response 可取消或真实 pending `next()` 能被唤醒。回放入口不读取 dotenv/凭据、不创建或调用 SDK client，
但既有包导入可能加载依赖模块。

候选仍 disabled/未注册，`capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、默认模型、
产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变，G53-7、黄金切片、
生产准入和 8F 仍未完成。当前唯一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-real-observation / pending-user-authorization`；
公共 CI 已闭环；是否执行一次参数明确的真实 provider 观察仍需单独授权。

### RQ-212 公共闭环事实（2026-09-03）

实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec` 的 Actions `33707313651` 三 job exact-SHA 全绿；
公共 pytest 为 `2284 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL 为 `201 passed, 2 warnings`，
packaging-smoke 通过。v2 离线回执 `data/evaluation/results/offline/
zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json` 为 `2220` bytes，SHA-256 为
`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`，三个身份 SHA 均绑定该实现提交。
它仍只证明 `offline_fake` 的本地分类与证据隔离，不提升为 provider capability；下一步需单独授权真实观察。

### RQ-213：候选 close/wakeup 第二次真实观察能力边界（2026-09-03）

RQ-213 不新增 A03/A10/Q02 或任何产品 Runtime capability。一次真实 candidate-only 请求绑定
`a396412f7cd0f2e923536cf55f715dd56251aae5`，回执为 `not_pending`：首段 172ms，事件类别为
`reasoning_seen/content_seen`，没有 pending reader，cancel 未尝试。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`
为 909 bytes，SHA-256 为 `8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`。

`not_pending` 与资源 `closed` 投影都不能证明 provider close 非阻塞、pending `next()` 唤醒或底层
HTTP response 取消；候选仍 disabled/未注册，`capabilities.streaming=False`，默认模型、产品 Runtime、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。下一步为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`，
先决定是否建立新版本实验协议。

## RQ-214：candidate transport gate 预检边界（2026-09-03）

新增的 `glm-5.3-flash-candidate-close-wakeup-transport-gate` 是 8E/8-Advanced 的
evaluation-only seam，不是 A03/A10/Q02 或任何产品 Runtime capability。它使用真实 OpenAI
SDK、候选 Zhipu 适配器和本机 `MockTransport`，固定两个 SSE 闸门阶段，供应商调用数为 0、
`network_used=false`，并把 `reader_woke`、cancel、gate close 和 iterator close 分开投影。

本地结果可观察到 response close 传到 transport 并唤醒读取器，但可能伴随并发 iterator close
竞态；这不等于 provider-native close 非阻塞、服务端停止生成或生产 streaming 已可用。候选仍
disabled/未注册，默认模型、产品 Runtime、AgentLoop、Portal、Account、Workbench、Auth、
路由与 `production_media=0` 不变。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / pending-user-authorization`。

RQ-214 离线回执已绑定实现 SHA `4c220c5751288ad77c589d2e0e581690085803c0`，大小 `1693` bytes，
SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`；Actions
`33712055286` 同 SHA 三 job 全绿，未形成真实 provider 或产品 capability 准入。
## RQ-215：candidate transport-gated 一次真实观察（2026-09-03）

RQ-215 是 8E/8-Advanced 的 evaluation-only 客户端观察，不新增 A03/A10/Q02 或任何
产品 Runtime capability。它在 exact-SHA 公共绿灯提交
`2acdf795881733e70c9246c48f7147d5136821b5` 上只发送 1 次真实
`zhipu/glm-5.3-flash` 请求，并在官方 TLS transport 外使用首帧前 gate。

回执记录 `provider_call_count=1`、`transport_request_count=1`、`network_used=true`，
gate 已进入，pending reader 已形成并在 `31ms` 内唤醒；取消安全码为
`zhipu_stream_close`，iterator/composite=`failed`、SDK stream=`closed`，结论为
`client_wakeup_close_race`。这只描述真实流启动后本机受控停顿下的客户端行为，不证明
provider-native close/wakeup、底层 HTTP response 独立可取消、模型一般能力或生产
streaming。回执路径为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`，
`1305` bytes，SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`。

候选仍 disabled/未注册，`capabilities.streaming=False`；默认模型、产品 Runtime、
AgentLoop、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。当前
精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

## RQ-216：候选 reader-owned close 顺序（2026-09-03）

能力状态仍为 `candidate-only / evaluation-only`。`ZhipuStreamSession` 在活跃读取期间先关闭
外层 SDK response，并由 reader 线程在 `finally` 中关闭 iterator；非活跃读取保持逐资源最多一次关闭。
本地阻塞读取及两阶段 transport-gate 回归为 `61 passed`，真实 API 调用为 0。该修复只改变候选
客户端资源生命周期合同，不授予 provider-native close/wakeup、streaming、默认模型或产品 Runtime
能力；候选仍 disabled/未注册，Portal、Account、Workbench、Auth、路由、8-Core、G53-7、黄金切片
和 `production_media=0` 均不变。当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`。

RQ-216 公共闭环：提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` / Actions `33726209532`
三 job exact-SHA 全绿（pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`；
PostgreSQL 与 packaging-smoke 通过）。能力矩阵仍不授予 provider-native close/wakeup、生产
streaming、候选注册或默认模型能力；当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`。

## RQ-217：关闭顺序修复后的 transport-gated 真实观察能力边界（2026-09-03）

RQ-217 不新增 A03/A10/Q02 或任何产品 Runtime capability，仍是 8E/8-Advanced 的
candidate-only、evaluation-only 客户端证据。实现/观察器/输入计划 SHA 均为
`3e028b1217f1274152ba161993287f29188a1b73`，Actions `33727163550` 三 job exact-SHA 全绿。

一次 `zhipu/glm-5.3-flash` 请求在官方 TLS transport 外的 `before_first_event` gate 中
形成 pending reader；`reader_woke=true`、`cancel_status=returned`，iterator/SDK/composite
close report 均为 `closed`，结论为 `client_wakeup_clean`。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`
为 `1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`，
body-free 且 canonical round-trip 通过；`gate_released=false` 是受控停顿协议的预期条件。

这只证明本机客户端的唤醒和 reader-owned 收尾，不证明 provider-native close/wakeup、
底层 HTTP response 独立取消、模型一般能力、成本/延迟稳定性或生产 streaming。候选仍
disabled/未注册，`capabilities.streaming=False`；默认模型、产品 Runtime、Portal、Account、
Workbench、Auth、路由、8-Core、G53-7、黄金切片和 `production_media=0` 均不变。当前精确
checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`。

## RQ-218/RQ-219：Flash 协议与候选长响应能力边界（2026-09-03）

RQ-218 的 3/3 G53-3 只为普通 API/基础工具协议增加可达性证据；RQ-219 的候选 8192
真实观察在 90 秒以 `fail_closed / elapsed_limit` 结束，未授予任何新的产品能力矩阵项。
RQ-219 证据提交 `3f35d150b2f17f919f2be1597c08c6db0178c461` 的 Actions `33735717434`
三 job exact-SHA 已全绿。
候选仍 disabled/未注册，`capabilities.streaming=False`，严格 Flash v1 与默认模型不变；
当前下一精确 checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

## RQ-220：Flash 响应分层评测能力边界（2026-09-03）

新增的 9 场景离线矩阵仅验证现有 response policy 与候选 stream observer 的组合归因，
不授予新的 A/Q 能力项；provider calls=0、network=false，候选仍 disabled/未注册，
`capabilities.streaming=False`。实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` /
Actions `33738050233` 与回执提交 `ebb09a525b3340f31ba71821b894b4a142dfb4e7` /
Actions `33738673832` 均三 job exact-SHA 全绿；回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
当前 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。

## RQ-221：低思考候选探针能力边界（2026-09-03）

RQ-221 不新增任何 A/Q 产品能力项。显式 `low + 4096` profile 只能由 candidate-only
构造器绑定，`execution_allowed=false`，正常产品 Runtime resolver、AgentLoop、
Workbench 与统一 Trace/预算均未改变。

实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` / Actions `33746833148` 三 job
exact-SHA 全绿；一次真实无工具请求的回执记录 `provider_call_count=1`、
`network_used=true`、`finish_reason=stop`、有效 Usage（`1973/498` tokens），SHA-256=
`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。这只关闭一个冻结
上下文的响应完成观察，不授予领域采用、streaming、生产或 8F 能力。

候选仍 disabled/未注册，严格 Flash v1 仍 2048/零额外调用，`capabilities.streaming=False`；
默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。当前精确
checkpoint 为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`。
## RQ-222：低思考候选独立领域门能力边界（2026-09-03）

RQ-222 仍是 8-Advanced candidate-only 设计，不新增 A/Q 产品能力。后续实现必须通过私有
评测作用域把 `low + 4096` 请求策略传入共享 Agent/RAG/Evaluation/Harness 组合；普通产品
解析器、Worker、默认模型和 `require_registered_model_runtime_profile()` 不得接受该档案。
新领域门使用全新 oracle-blind 三案例资产，固定 4/12 次调用、90/120 秒、24,000/72,000
token 墙和首错停止，评测作用域关闭 deterministic fallback。

当前只完成设计，provider calls=0，Portal、Account、Workbench、Auth、路由、生产默认和
`production_media=0` 不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。

## RQ-223：低思考候选请求策略离线实现

新增的 `CandidateEvaluationRequestPolicy` 及 `CandidateEvaluationBudgetedProvider` 只属于
8E/8-Advanced 的 evaluation-only 接缝。它们证明候选可以在不改产品注册表的情况下复用
Agent/RAG/Evaluation/Harness 的请求控制，并把 4096、90/120 秒、零重试、无回退与 4/12 次及
24,000/72,000 token 墙在最后边界重新施加。Fake Provider 测试通过、provider calls=0；不新增
任何产品 A/Q 能力，不开启 streaming，不改变默认模型、Portal、Account、Workbench 或
`production_media=0`。当前精确检查点为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。

## RQ-224：低思考候选领域门公共 CI 闭环

RQ-223 的实现提交 `d823cc40c3fcafb7167edccded87e185be4cae8a` 已通过 Actions
`33781369322` 的 exact-SHA 三 job 公共 CI（pytest、PostgreSQL migrations、packaging-smoke）。
公共 pytest 报告 `2326 passed, 145 skipped, 2 warnings, 127 subtests passed`；本批
provider calls=0。该证据只关闭可复现性闸门，不新增 8-Core 能力、不改变产品默认、
Workbench 或 `production_media=0`，也不证明领域质量、G53-3-L、黄金切片、生产准入或 8F。
下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / pending-user-authorization`。

## RQ-225：低思考协议与新鲜资产离线控制面（2026-09-04）

RQ-225 继续保持 8-Advanced candidate-only，不新增 8-Core 或产品 A/Q 能力。显式
`request_policy` 已接入协议切片运行器，低思考 G53-3-L 组合器固定 `low + 4096`、
90 秒工具窗和最多 3 次调用，报告只保留 body-free 安全身份与计数；真实来源仍需显式确认。
新三案例 held-out Dataset、V1.1 Input Plan、Prompt/Context Snapshot 与合成 fixture 已通过
no-I/O 资产准入，`external_provider_calls=0`。聚焦协议/资产及相邻回归 `20 passed`，
compileall、diff check、governance 通过；不改变产品 Runtime、默认模型、Portal、Account、
Workbench、Auth、路由或 `production_media=0`。实现提交
`411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的 Actions `33787508488` 三 job exact-SHA
全绿，公共 pytest 为 `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`。
当前精确检查点为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`；
真实协议门仍需明确授权。
