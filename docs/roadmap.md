# RiftCoach 主路线 v1.1（阶段 0—8）

> 当前校正（2026-09-02，RQ-207）：G53-5 矩阵及 F7 follow-up 的历史观察保持不可变；用户已授权将
> 普通智谱 API `zhipu/glm-5.3-flash` 作为产品正常运行目标，GLM-5.2 仅作显式兼容/应急回退。RQ-176 的
> Flash 目标接线已有本地实现，但当前 RQ-194 适配接缝仍是候选、尚未注册；RQ-177 已在旧实现 A 上取得新的 G53-3 协议证据，RQ-178 完成 A/B 身份绑定，
> RQ-179 又将最终新实现 A=`9e6d78be…` 以 Actions run `33378687984` 三 job exact-SHA 公共冻结；随后
> RQ-180 在 A/B 证据链上只执行一次 G53-7，领域 `2/12` calls 后以 `provider_response_invalid/incomplete_chat_response`
> 首错停止，`admitted=false`；随后 RQ-181 对同一首例做了一次正文零留存诊断，确认原始 `finish_reason=length`、
> `output_tokens=2048`、正文为空而 reasoning 非空；结果 SHA=`050df3fc…`，不表示模型一般质量或账号失败。
> 当前不自动重试，不能直接把任一结果写成生产准入；RQ-182 已完成版本化响应完成策略与离线 TDD，RQ-183 已完成候选
> runtime/attempt/预算/Trace 的离线合同；RQ-184 已为候选合同取得实现 A/B 的 exact-SHA 公共 CI，并在同一 A 重取 G53-3
>（严格 `3/3` 调用通过）；RQ-185 的无响应随后由 RQ-186 定位为客户端默认 timeout 被每请求 90 秒值覆盖。
> RQ-187 又在完整 90 秒请求窗口中复核，唯一 primary 在约 90.188 秒以 transport timeout 安全结束，仍未收到响应或
> Usage、未发 fresh-recovery；这排除了“30 秒过短”，但不能区分代理/读取与服务端生成延迟，也不能裁决模型能力。
> RQ-188 随后以合法 Flash thinking 控制、冻结短同步和冻结流式首块三路拆分，均观察到响应；RQ-189/190/191 又分别
> 完成输出额度校准、首正文和完整终态/Usage 观察。RQ-192 已将原始观察冻结为离线 provider-neutral 流式装配合同；
> RQ-193 又在测试内完成智谱分块到该合同的 conformance（13 项聚焦），提交
> `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA 公共 CI run `33489903978` 三 job 全绿且 head_sha 精确匹配，
> 并包含全部 Trace 脱敏断言。RQ-194 已完成候选级、仅显式调用的真实 `ZhipuStreamAdapter` 接缝：
> `app/providers/zhipu_stream_adapter.py` 提供 `stream_events()`/`assemble()`，`ZhipuProvider.stream_adapter()` 是显式工厂，
> 聚焦测试 `20 passed`；提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588` 三 job exact-SHA 全绿。
> 这只证明候选接缝公共可复现，不等于产品 runtime 或生产准入。严格 Flash v1 仍保持 2048/零额外调用，
> `capabilities.streaming` 仍为 `False`，候选仍未注册；RQ-195 评审、RQ-196 设计、RQ-197 边界观察实现与 RQ-198
> 同 SHA 公共 CI 已完成。RQ-199 又完成了隔离候选评估台设计（两阶段 staged ledger、单次事件泵、独立 body-free receipt），RQ-200
> 已完成 fake/local 候选评估台实现及 `102 passed` 相邻回归，且已取得 RQ-201 exact-SHA 公共 CI（run `33536168224`）；RQ-202 已完成候选 recovery 诊断边界复核与最小离线加固，RQ-203 已完成版本化候选 recovery 诊断协议设计，RQ-204 已完成 fake/local 版本化诊断实现，RQ-205 已完成 exact-SHA 公共 CI 与协议演练，RQ-206 已完成 1 次有界真实 primary 观察并以 `fail_closed / elapsed_limit` 收口；RQ-207 已完成候选硬墙钟会话、取消/关闭与 Usage 尾帧本地实现，四文件聚焦回归（deadline 10、v2 24、real 8、adapter 25）统一为 `67 passed`；RQ-208 已完成 RQ-207 的 exact-SHA 公共 CI：提交 `015b022bfce6d03452f753794ac126a377f8355b` 的 Actions run `33613113829` 三 job `completed/success`，公共 CI 已闭环，但同步 opener 与 SDK `close()` 的真实非阻塞/唤醒能力仍需真实重测验证；当前唯一下一项为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，不能自动重试、注册候选或进入 G53-7；
>
> 历史观察：G53-5 矩阵完成 `11/11` 次真实调用、`46,151` tokens、`7/8` cases pass；
> 随后独立 F7 follow-up 仅将 `max_tokens` 从 512 调至 2048，完成 `1/1` 调用、`557` tokens，
> `finish_reason=tool_calls`、1 个 ToolCall。adapter core、AgentLoop、domain development 与供应商流式/多模态观察通过；
> 原 F7 `tool_stream` 截断诊断不改变其 vendor_raw 边界，F4 缓存仍 `unproven`，F8 仍为 vendor-only；
> `production_admitted=false`、`public_ci_confirmed=false`。Stage 8/8E 继续 `in_progress`，
> 生产准入仍未宣称，`production_media=0`；旧 G53-4 考卷保持不可变。

## 2026-08-24：Stage 8 视觉合同前置（不改变路线顺序）

在 `8e-productization` 内，用户确认 `Rift Awakening / Cinematic Portal →
Esports Intelligence / Broadcast Workbench` 为前端融合方向。该项是实现入口前的设计/验证前置，不新增
主阶段、不改变 8E/8F 顺序，也不把概念图当成已完成页面。实现必须保持现有 typed DTO、relationship/product
state、Evidence 和 Training 边界；Image2/Photoshop 只提供可替换氛围层，CSS/SVG/React 提供真实 UI 和响应式
交互。详见 ADR-0064 与 `docs/plans/2026-08-24-8e-portal-workbench-visual-contract.md`。

本路线是项目唯一主阶段编号，共九个阶段。阶段内部可以继续迭代 `Harness v1.1`、`RAG v1.2` 等小版本，但不再增加、删除或重排主阶段。若必须改变主阶段职责，需先新增 ADR，说明证据、备选方案和迁移影响。

## 2026-08-29：8E 地区入口试水（历史，已被 RQ-157–RQ-162 取代）

当时曾以 `?surface=wallpaper-lab` 做 Demacia 与 Bandle City 的两地区纵向试水；该记录只保留历史证据，
不再作为当前动作。RQ-157–RQ-162 已将其取代为 13 个地区的 horizontal Focus Rail、受控 Portal→Account
handoff 和独立双语 atmosphere 文案；默认 `/`、`production_media` 与来源/许可门仍不变。

## 2026-08-31：RQ-182 响应完成策略（不改变生产默认）

RQ-181 的一次诊断确认 Flash 在 2048 输出额度内先耗尽 reasoning。RQ-182 已在 8E
新增精确绑定、版本化的响应完成策略与离线 TDD：严格 v1 保持 2048 和零额外调用，
只允许完整正文或合法工具回合；8192/一次 fresh-recovery 仅作为未注册候选，不能被
运行时解析或自动发起第二次请求。完整 8E、候选启用、黄金切片、部署/安全/合规和
8F 仍未完成，`production_media=0` 不变。

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
| 8 | Multi-Agent、可靠运行时与产品化 | 复杂任务何时并行、恢复、观察和交付 | Saber + Sea 选择性吸收 | 进行中；entry design、8A–8D、8E Batch B–E、Live integration、production shell/Auth gate、Timeline DTO/UI 与 bilingual/product-journey foundation 已公共闭环，ADR-0053 reject 产品 Multi-Agent；Portal/Account 当前展示切片已按 RQ-163 阶段性收口并交回 Agent 主线，G53-1/2 已完成，RQ-177 的同 SHA G53-3 已通过，RQ-178 完成本地 A/B 预检，RQ-179 已为最终实现 A 取得 exact-SHA CI，RQ-180 已完成一次 G53-7 领域尝试但以 `provider_response_invalid/incomplete_chat_response` 首错拒绝，RQ-181 已确认首回合 `finish_reason=length` 且 2048 输出额度先被 reasoning 耗尽；RQ-182 已完成版本化响应完成策略与离线 TDD，RQ-183 已完成候选 runtime/attempt/预算/Trace 的离线合同，RQ-184 已完成候选 A/B exact-SHA 公共 CI 与同 SHA G53-3；RQ-186 已修复隔离诊断器的请求级截止，RQ-187 在完整 90 秒窗口取得一次 90.188 秒 transport-timeout 脱敏结果，RQ-188/189/190/191 已完成后续有界拆分、预算、首正文和完整流观察；RQ-192 离线装配合同与 RQ-193 智谱 conformance 已完成，RQ-194 已完成本地 `ZhipuStreamAdapter`（`stream_events()`/`assemble()`）及 `ZhipuProvider.stream_adapter()` 显式工厂，聚焦 `20 passed`，提交 `a7580e861cd986c026040c7fcfcc3fa577737961` / Actions `33496237588` 三 job exact-SHA 全绿；RQ-195 已完成候选 runtime 接线架构评审，确认不完整流必须先经 BoundaryObservation，推荐隔离候选评测调用方，不直接接入产品 Runtime。严格 Flash v1 仍保持 2048/零额外调用，`capabilities.streaming` 仍为 `False`，候选未注册；下一项为 `candidate-runtime-wiring-design / pending`，完整 8E/8F 仍未完成 |

> 阶段 8 表格中的 RQ-195 下一项是历史摘要。RQ-196 已完成候选 runtime wiring design，RQ-197 已完成边界观察本地实现，
> RQ-198 已取得同 SHA 公共 CI，RQ-199 已完成候选评估台设计，RQ-200 已完成 fake/local 候选评估台实现，RQ-201 已取得 exact-SHA 公共 CI，RQ-202 已完成候选 recovery 诊断边界复核与最小离线加固，RQ-203 已完成版本化候选 recovery 诊断协议设计，RQ-204 已完成 fake/local 版本化诊断实现，RQ-205 已完成 exact-SHA 公共 CI 与协议演练，RQ-206 已完成 1 次有界真实 primary 观察并以 `fail_closed / elapsed_limit` 收口，RQ-207 已完成候选硬墙钟会话与 Usage 尾帧本地实现（四文件聚焦 `67 passed`）；RQ-208 已完成 RQ-207 的 exact-SHA 公共 CI（`015b022bfce6d03452f753794ac126a377f8355b` / Actions run `33613113829` 三 job `completed/success`）；当前唯一下一项为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`。Flash 是当前唯一主力候选目标，
> 但仍未注册为产品默认，8E/8F、生产准入和 `production_media=0` 的边界不变。

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

### 同厂商模型迁移边界（历史说明；当前以 RQ-176 为准）

GLM-5.2 和 GLM-5.3 共享 Zhipu Provider 接口，但不共享所有请求语义。官方 GLM-5.3
要求始终启用 thinking，因此模型升级必须先通过独立的 profile/Adapter 合同测试，
再通过真实协议和领域采用门。模型切换不等于自动路由，也不等于 Multi-Agent。

5D-7 已在没有领域 Provider 准入的情况下完成评测门审查；这是该历史阶段的边界，不把
DeepSeek 结果混入产品能力。GLM-5.3 随后按 ADR-0023 的 G53-0 至 G53-4 顺序隔离推进；
 G53-0 已完成本地无 I/O 静态审计，RQ-165 又完成普通 API `glm-5.3-flash` 的本地
 thinking profile/Provider/probe 离线 TDD；RQ-166 已完成 G53-2 exact-SHA 公共 CI，RQ-169 的 G53-3
 有界结构化/工具协议门已通过，RQ-170 的 G53-4 已本地执行但因首错拒绝。通过新鲜领域门前，GLM-5.2 只作为开发基线，历史证据和确定性
fallback 保持有效。RQ-176 已在后续明确 Flash-only 产品路线；本段不再作为当前模型选择依据。

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
  package 公共闭环；随后 6B-8/6B-9 也由 `aacc11a/32403187972`、`cbc7cbd/32408101770` 公共关闭，阶段 6 已完成；这不等于正式 Auth 或公网部署已完成；
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

当前事实：入口设计与 7-1…7-5 均已公共闭环。7-3 的 `64311a1/32455219404` 证明官方 Streamable HTTP、
partial MetaEvidence、严格 lane-meta Adapter 和一次真实 body-free 单向 smoke；7-4 `431c584/32480827952`
完成 strict Server/Facade；7-5 implementation `a88fbc4/32483521108`、clean-SHA 双向真实门和 evidence
`fac6fe0/32484257736` 全绿，Stage 7 已正式关闭。

### 完成标准

- 能与至少一个外部标准 MCP Server 完成真实互操作；
- 能被至少一个外部 MCP Client 调用；
- 不把普通 HTTP POST 适配器称为 MCP。

## 阶段 8：Multi-Agent、可靠运行时与产品化

Stage 8 entry design、8A、8B 与 8C 已完成 exact-SHA 公共闭环；8B 唯一 holdout 由 ADR-0053 拒绝产品
Multi-Agent。8C 已由 clean implementation `2df5349/32587659678` 验证 PostgreSQL durable task event、
lease/fencing、cancel、checkpoint、receipt-proven recovery、Worker/API/package 纵向与八维材料；8D 又由
`a274b7f/32598480400` 完成 Riot/Data Dragon/official patch/OP.GG partial typed EvidenceBundle 公共闭环。
当前唯一主检查点为 `8e-productization`；RQ-087 live diagnostic 已定位
OP.GG `Mid.rank_prev_patch` JSON-null drift，ADR-0058 的窄修复已由 `83fde7d/32615340228` 公共闭环；
修复后 live replay 已创建 body-free bundle，但 Akali Meta join 因 top-10 未命中诚实 degraded。ADR-0059
随后把玩家档案冻结为 successful Player Link 的 owner-scoped latest-success projection，并把 legacy/Conversation
Riot routing 改为逐请求/SQL target exact region；implementation/evidence `e844bdd/32622696087` 已完成
exact-SHA 三 job 公共闭环。后续 Batch C/D、Live、E1–E5、Auth gate 与 Timeline 也已公共关闭；这仍不表示
exact-patch/freshness、DAG、正式 OIDC/RSO、加密备份、前端部署、8F 或生产 SLA 已完成。

### 8E Batch B：玩家档案选择与显式 Riot 路由（已公共闭环）

- owner 可列出自己已成功解析且仍 active 的多个外服玩家/公开观察对象；重复 link 只投影最新一条，公共
  DTO 不含 PUUID、owner/task identity 或 upstream body；
- Conversation 以 opaque `player_profile_id` 固定 player subject，旧 `relationship_id` 只作 strict 输入别名；
- legacy recent review 必须提交 allowlisted routing region；Conversation 使用 SQL execution target region，
  Worker exact-select `americas/asia/europe/sea`，没有 ambient default、CN fallback 或自动探区；
- 本批不包含 profile 昵称/排序/默认项、正式 Auth/RSO、SSE、前端、EvidenceBundle store、HTTPS、备份或部署。
- `e844bdd/32622696087` 的公共 pytest 1709、真库 187 与 Linux package schema 1.6 三 job 全绿；唯一下一
  内部批按 preflight 顺序为 Batch C EvidenceBundle persistence/refresh/expiry、event replay→SSE DTO 和
  四态产品状态合同，之后才进入 Batch D 静态前端。

### 8E Batch C：Evidence/Product API 与 Cursor SSE（已公共闭环）

- 0011 以 PostgreSQL append-only JSONB revision 保存 full typed EvidenceBundle；复合 owner/task/run FK、
  refresh/revision 唯一约束、大小/digest CHECK、UPDATE trigger 与 cascade delete 已由真实 PostgreSQL 验证；
- 同 refresh + 同 bundle content replay 首次 snapshot，即使 retry time 不同；changed content conflict；
  task row lock 分配连续 revision，latest 不回退；
- query-time expiry 保留历史 digest/revision，但撤销依赖当前 Meta/exact patch 的 usable claim；
- `GET /runs/{run_id}/evidence`、`/product-state` 暴露 body-free owner-scoped DTO，四态固定为
  `published/degraded/rejected/not_ready`；
- `/tasks/{task_id}/events/stream` 复用 8C durable cursor，支持 `Last-Event-ID`、keepalive、重连去重、
  terminal close 与 allowlisted stream error；
- composition/Linux smoke 检查缺证据、失败四态和 terminal SSE，本批 Riot/OP.GG/Provider/LLM calls 0；
- implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions `32629160732`
  的公共 pytest `1750 passed, 139 skipped, 1 warning, 127 subtests passed`、真实 PostgreSQL
  `194 passed, 1 warning` 与 Linux package schema 1.6 三 job 全绿；
- 八维 walkthrough 路径已建立但整个 8E coverage 仍 `planned`。RQ-091/RQ-092/RQ-093 与 ADR-0061 已
  冻结多来源两层采用门、五模块连续性、`Rift Command Center`、tokens、客户端/产品状态和 a11y；
  design `88a5ab6/32631766013` 与 implementation/evidence `f7ebedd/32636771507` 均完成 exact-SHA 三 job。
  Batch D 静态前端正式关闭；后续 Live Workbench 接线又由 `f441061/32647933692` 公共闭环。当前下一项
  是 Batch E 安全/部署入口设计；仍不表示 Auth/部署、电影感入口、完整 Timeline/Training 或 8F 已完成。

### 8E Live Workbench 接线（RQ-094–RQ-096，已公共闭环）

- RQ-094 补回最终视觉职责：`Rift Awakening` 电影感入口与 `Esports Intelligence` 工作台组成
  `Cinematic Portal → Broadcast Workbench`，`Void Holographic Lab` 只作受限 Hero 实验；
  `Hextech Tactical Editorial` 是共享语言，Batch D `Rift Command Center` 是工作台施工切片；
- checkpoint 关闭必须给短复盘，连续批次再给总复盘；该节奏不替代八维 coverage；
- Stage 7/8D 不重开，但 8F 前另设 OP.GG useful-breadth gate，并完成一次实际包含 Riot match、Data Dragon、
  official patch、OP.GG、训练建议与 UI Evidence 的 body-free golden slice。现有 lane-meta 与
  `degraded/unjoined` replay 不满足该完整目标；
- RQ-095 设计门冻结薄 latest-review locator、Recent Summary HTTP、typed Evidence HTTP、same-origin exact
  decoder、generation/abort、单 EventSource、restricted report 与真实 Training 字段；
- ADR-0062 与 live integration design/implementation plan 完成本地同步后，必须先经过独立 design SHA 的
  三 job exact-SHA 公共门，才可把 implementation 交为 prepared。该门现已由
  `4057c93/32639561338` 全绿关闭；RQ-096 随后授权实施；
- locator/Summary/typed Evidence、exact decoder/client/controller/EventSource 和 default-live React 已由
  `f441061e7444fa6d1d3c213b81e05a02f0fc68c5` / Actions `32647933692` exact-SHA 三 job 公共闭环；
  公共 pytest 1796、真 PostgreSQL 200、frontend unit 66/e2e 17、JS gzip 122.01 kB 与 Linux package schema 1.6 全绿；
- 该已公共闭环的实现仍不包含完整 Auth/RSO、部署、完整 Timeline/Training、OP.GG breadth、fusion golden slice
  或 8F；整个 8E/coverage 继续 `in_progress/planned`。Batch E implementation 已开始本地 E1/E2/E3，
  已由 `92b7685/32658277570` 完成 exact-SHA 公共门；下一项是 E4 backup/restore/erase。

### 8E Batch E：安全/部署实现（已完成 E1–E5 公共闭环）

Batch E 入口设计冻结在 ADR-0063 与专用 design/implementation plan：RiftCoach Auth 产生可信 owner，
Riot RSO 只负责未来 verified-self 关系证明；首个部署采用 edge/static Web + API/Worker/PostgreSQL
单机 Compose，托管数据库是迁移路径，Kubernetes/Redis/Celery/Kafka deferred。设计覆盖威胁模型、
CORS/CSP/HTTPS/限流、Secret 轮换/撤销、backup restore/erase、隐私、观测与剩余 Web 模块顺序。

E1 session boundary、E2 request budgets/单机 rate policy、E3 SecretSource/key-last composition 已由
`92b7685/32658277570` 公共闭环；E4 `27b9256/32660145945` 完成 marker replay/Artifact-Trace cleanup，E5
`ca6da44/32661425379` 完成 bounded metrics/packaging。它们不等于生产 OIDC/RSO、HTTPS、真实 Secret
Manager、共享 limiter、KMS/对象存储/加密备份、部署或 8F，8E coverage 继续 `planned`。

E4 的历史实现内容为：manifest 只保留 deletion-marker metadata + deterministic digest；PostgreSQL
owner lifecycle repository 按 conversation/relationship 精确定位 run，API composition 在 marker commit
后复用 `FileRunDataCleaner` 清理 Artifact/Runtime Trace。restore 先 replay markers，再通过 readiness；
marker replay 支持幂等和 partial-failure compensation。当前仍没有对象存储/KMS/加密 backup bytes、定时备份
或真实 RPO/RTO 演练，因而不能把 E4 说成生产灾备完成；其公共关闭证据见下一段。

E4 implementation/evidence `27b9256` / Actions `32660145945` 已取得 `pytest`、`postgres-migrations`、
`packaging-smoke` 三 job exact-SHA 全绿，正式关闭。按连续授权下一项是 E5 packaging/observability：
围绕现有 Compose/Docker/health/rollback 和 body-free structured logs 做最小可验证增强；E5 前不扩张到
Kubernetes/Redis/第二套 metrics runtime，也不提前关闭 8E 或进入 8F。

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

## 2026-08-24：8E E4 公共关闭与 E5 metrics 首批

- E4 `27b9256` / Actions `32660145945` 三 job 全绿后正式关闭；owner erase/restore replay/Artifact-Trace
  cleanup 证据已公共验证，KMS/对象存储/RPO-RTO 仍是明确 deferred 边界。
- E5 首批增加 bounded body-free `TaskObservability` projection 与 `/health/metrics`；Compose migration
  order、health/readiness、non-root image 和 no-I/O package smoke 继续复用，不引入新 metrics runtime。
- E5 `ca6da44` / Actions `32661425379` 与 production shell/Auth gate `15a3a9e` / Actions `32663345737`
  均已完成 exact-SHA 三 job 公共闭环；下一项进入 Timeline DTO/UI。按 RQ-102/RQ-103，Timeline 公共关闭后
  先建立 `zh-CN/en` 双语产品表面基础，再以独立原子批建立 Data Dragon 资产合同并补 LoL 视觉/交互细节，
  随后做 Evidence 深化、Training full page 和 OP.GG useful-breadth/golden slice；8E 退出前执行跨模块 final
  visual QA。当前 Timeline 截图不是最终作品集签收，真实 OIDC/RSO 也不因 UI 开始而默认采用，8F 不提前进入。

## 2026-08-24：Timeline exact-SHA 公共关闭与 bilingual foundation 交接

- Timeline implementation/evidence `794032f` / Actions `32682243568` 的 pytest、真实 PostgreSQL 与 Linux
  package 三 job 全绿；strict verified event/phase projection、owner-scoped API、exact decoder/controller、
  responsive/a11y UI 和 partial/unavailable 正式关闭。
- 当前截图按 RQ-103 仍只是高保真 V1；Data Dragon 资产/细节 enrichment 与全站 final visual QA 未完成。
- 当前唯一下一原子项为 RQ-102 bilingual product-surface foundation；Evidence/Trace、Training、OP.GG
  breadth/golden slice 和 8F 不提前进入。

ADR-0066 与专用设计/实施计划已由 `8969aef/32683742229` 完成 design exact-SHA 三 job 公共门；当前从
typed catalog、locale persistence、canonical code 与生成内容语言边界的红灯进入 TDD。RQ-103
Data Dragon 资产/细节 enrichment 和跨模块 final visual QA 继续排在本批之后。

RQ-104/105/106 又在同一原子批纠正 copy、产品拓扑和 Portal 资产：`zh-CN/en` 分别编辑；默认旅程为
零 I/O Portal → Account session/profile/Player Link → 明确 profile 的 live Workbench；母图派生的 runtime
background 不含文字/UI/core，React core 是唯一交互真值。implementation/evidence `6084937` / Actions
`32757872792` 的 exact-SHA 三 job 已公共关闭该 foundation。

RQ-108 已把 foundation 公共关闭后的立即下一原子项固定为独立 `portal-motion-polish`：以确认母图为构图源，
水晶保留在场景媒体内并由透明语义按钮覆盖点击区；正常体验必须使用同源全帧 loop，高清 poster 只负责
首帧/降级，汇聚/burst、独立 Account
动态场景幕切及完整媒体降级/预算门必须单独设计和验证。它不新增主阶段，也不完成 RQ-103 跨模块 final QA。

RQ-117 又校准 Account 地图：Data Dragon map11 与 Riot 2024 near-final concept 只锁定官方拓扑与阵营，
最终画面采用有意概括的 Hextech 战术地形投影，禁止伪造具体树墙塔等写实微细节。ADR-0068、正式设计、
TDD implementation plan 与八维 planned walkthrough 已在本地建立；当前只待独立 design exact-SHA，尚无
runtime media/video 实现，也没有已采用的 Account source master。

RQ-118 同时消除了早期水晶句子的歧义：Portal 不再重绘或放大水晶，确认母图中的原水晶、塔体和构图保持
source truth；全局 loop 与点击 burst 只赋予原水晶运动，透明语义按钮覆盖其真实位置。

RQ-119/120 又用用户 Kimi 12s/1080p 实测建立第一个视频 Bad Case：有效播放/标称分辨率仍可能严重偏离
source composition。Kimi v1 已 rejected；正式横评覆盖 Wan/Seedance/Veo/Luma/Runway 等生成 I2V、
HyperFrames/Remotion 确定性分层 render，以及推荐的混合式。后续 Wan/Veo 各一个真实样本也已执行并拒绝；
RQ-125 明确样本 rejection 不等于模型上限，C 线只作为优先 proof，校正 A comparator 保留。

上述 RQ-108 design 已由 `b3b5280/32812868683` 完成 exact-SHA 三 job 公共闭环。下一动作只进入 runtime
Task 1 manifest/cover geometry/media policy TDD；设计公共绿灯不等于视频、runtime、skill 或模型已采用。

RQ-121 又把用户正规中转目录限定为 official-first 之后的可验证 secondary transport；目录 slug/标签/价格
不是身份事实，未过 mapping、能力、压缩、隐私、地区、错误/计费与 body-free 门时不得上传母图或参加横评。

RQ-108 runtime Task 1–3 已分别由 `1b146e6/32826953474`、`2111a78/32833608622`、`0198fc9/32836430378`
完成 exact-SHA 三 job 公共闭环；Task 4 媒体审计器与预算门已由 `52def9c`/`d58ba15`、Actions `32841900909` 完成
exact-SHA 公共闭环；当前唯一下一动作是 Task 5 三路线 bake-off，不接生产媒体。

Task 5 已按 RQ-122 完成 official/relay 广筛和 HyperFrames 隔离 smoke；Wan 3.0 与 Dragon/Veo 各完成一个
有界真实负面样本，后续又完成 Seedance、即梦、Kling 与本地分层 proof 审计，production media 始终为 `0`。
样本失败不等于模型上限：Wan 早期调用使用同一张图作首尾帧，分层 proof 又暴露了素材贴纸风险。RQ-144 的
first-frame-only 重开因用户填入兼容文本 endpoint 而在 HTTP 404/no-task 停止，随后用户明确转战；当前不再寻找
Wan Host、不再发送第二次 POST，也不把旧 Wan 结果接入 runtime。RQ-146 激活官方/授权壁纸路线，第一候选为
用户提供的 Demacia WebM；随后已核对班德尔城 WebM，二者先做 region catalog/local preview 与来源/许可/格式/loop 门。
其 scene graph/8-system/192-frame/source-seam-grid/manual 三态 design 与实施计划已由 `78ae6e3/32919447127`
完成 exact-SHA 三 job；implementation 已完成机械可控的 v3 研究样片，但用户按 RQ-126 正确拒绝其线条/圆环/
节点 HUD 覆层视觉，裁决 `proof_fail_reopen_corrected_a`。当前先公共关闭负面证据，再执行一次 first-frame-only
短 motion-only 的校正 A comparator。RQ-127 固定该对照为 medium-to-strong、clearly perceptible 的整幕
breathing，并允许构图锚定小幅 camera parallax；不再以三主体轮流或过轻 motion 冒充 cool 动态。
C proof portable fix 已由 `557dac1/32923151197` 三 job 公共关闭；随后 C′、Kling B1/B2 和 source/masked plate
proof 均已按人工材质门拒绝，不能继续通过叠加/opacity 追绿。Wan first-frame reopen 因 endpoint 误填在 404/no-task
诊断停止；当前候选切为 RQ-146 的官方/授权壁纸路线，Demacia 与 Bandle City 先完成 local preview 与 region catalog，
再逐地区过来源/许可/格式/loop 门，不接 runtime。
RQ-128 又固定故障归因五层门：corrected Veo 无 output，request/relay/upstream unresolved、quality unknown；Vidu
只是保持 transport/source/motion/first-only 的 model/schema comparator，不是放弃 Veo/方法。Vidu 若也 generic
failed，必须停下审计 relay/request，不继续换模型。Vidu 首个 task 随后同样 generic failed；当前只允许一次
Studio-contract request：登录态 UI 证明 first-only/8s/1080p/16:9 但 audio 固定 true；唯一重试删除 seed、
audio=true。仍失败则转 relay task-id/official transport 诊断。
Studio-contract Vidu 随后成功，证明 API/first-only/prompt 可用；但样本由 camera push/global drift 主导，按
RQ-129 仅拒绝 sample。当前目标是 locked-frame refined in-scene motion；下一实验保持成功 Veo first+last/
model/transport/source，只替换 multi-depth/material-aware storyboard，Seedance 2.5 后继、Grok 等 mapping/schema。

refined v4 提交后的 403 已由 Dragon common log 证实为 `$15.008 < $19.712` 的预扣失败；它没有创建 task 或
提供质量证据。用户充值后余额 `$65.01`，但 RQ-130 明确余额 ready 不能替代内容 ready。v5 只收敛同一 Veo
comparator 的 prompt/negative：official motion-only/单一连续镜头、locked/deep-focus/source-linework、
left/center/right + near/mid/far 同时运动、八秒 phase/illumination/velocity 闭环、negative phenomena；source/
schema/runner/唯一 retry1 路径必须先独立提交并取得 exact-SHA 三 job，公共成功后才 one POST/no retry。

该 preflight 已由 `d57b026/32951125621` 三 job 公共关闭；唯一 v5 task `task_I5...k9Mw` 随后 one POST 创建，
159 秒/100% generic failed，且没有 output。按 RQ-128，只能裁决 relay/upstream failure，不能评价 v5/Veo/
first=last 或方法质量。`$19.712` 已全额退款，最终钱包 `$67.01`；external calls `6`、production media `0`。
当前先公共关闭 failure/terminal incident audit，不重发或立即换模型。

RQ-107 确认静态 Coach report 不是最终 Agent 产品。RQ-108 关闭后，bounded review-grounded Coach 与 RQ-103
Data Dragon asset/detail/final-QA 的相对顺序仍待集中裁决；在此之前不实现假聊天 UI，也不把当前 Portal V1
称为最终电影化成品。

用户认可 Seedance 样本三大区运动方向，但指出静区像雾层覆盖，按 RQ-133 选择基于成功成片的真正 video edit。
Dragon 专用文档确认 `seedance-2-5` 的 `video_operation=edit`、`video_with_roles(reference_video)`、`duration=-1`、
`aspect_ratio=adaptive`；Studio 主编排器视频参考 input 实测仅接受图片 MIME，故 edit 走文档化 API。v6 edit
prompt/runner 已冻结，先过 exact-SHA 公共门并披露约 `$12.0191` 估算，再 one POST；不混用首尾帧、不自动重试。

该 v6.1 POST 随后在 task 创建前返回 HTTP 400；source GET 成功、`task_id` 为空、费用 0、task log 无隐藏任务。
原 runner 仅持久化 status code，故本次 exact error field 丢失；登录态 common log 的旧 ratio 400 不能替代。
当前先公共关闭严格 body-free error sanitizer 与 incident diagnosis；没有精确 error body/可证伪字段修正前，
不重发、不拆双锚点抽卡、不换模型。

豆包工作标准套餐随后完成一次零新增现金的官方 Seedance 2.5 comparator，但 Skill 无 video-to-video edit，实际
以 Video1 首尾帧 + Image1 做图生视频重生成。输出 source-first `0.407604`、seam diff `0.144582`，带 AAC 和移动
水印；中段暖金光轨明显但重绘/简化 source，且未形成三主体内部与整体环境共同呼吸。样本 rejected/no retry，
有效 video calls `10`、production media `0`。RQ-134 保留“沿真实结构/道路的光轨”动作语言但改为冷蓝/青蓝主色，
并要求下一即梦 `智能编辑` 同时强化左 Rift、中央水晶/平台、尤其右星图/能量场以及全局环境。

RQ-135 又冻结即梦第一轮素材为成功 MP4 + immutable v2 母图，不因支持多参考而生成更多审美图；高级编辑区域
框选优先于第三图。file picker 由用户操作，Codex 只给路径/角色并在上传后 readback。v7 Smart Edit prompt 为
1,439 chars/4,115 bytes/SHA `edbc0d3...6f388`；当前先公共关闭 400 diagnosis、豆包 audit 与即梦 preflight，
全绿后才重新上传和执行唯一生成。

实际 official Smart Edit 随后在该 preflight batch 尚未 public-close 时由用户手动完成；执行顺序偏差已保留。
页面 2,000 字上限使实际 compact main prompt 改为 SHA `d003f047...cff10`，三帧说明另行绑定，长版仅保留 design
intent。raw SHA `4d3660b...155b` 的 locked camera、left/center/right 与九宫格 motion 均有正向证据，但
v2→first `0.889072`、seam DSSIM `0.046536`、AAC 与非 fixed-24 未过门。零费用 FFmpeg 最佳 J 虽完成
fixed24/no-audio/BT.709/3MB，seam `0.042684` 仍 fail 且 source identity 更差。Task 5 calls `11`、production
media `0`；当前先公共关闭 result/audit，再做 no-cost source-identity fault split，不先重抽或接 runtime。

Seedance 2.5 v3 随后完成了一次 12 秒 first-frame-only 生成并由 GET-only recovery 下载。技术编码满足播放要求，
但视觉候选被拒绝：左 Rift 变成硬同心环，道路流动在前段缺失，中央 burst 过曝且出现横向穿屏线，右侧在
burst 外近乎静止，整体 near/mid/far 呼吸不足。RQ-141 因此把下一门收紧为“先改运动合同”：基础层从首帧
持续运动，burst 仅是中央上下贯穿、低幅、约 2–3 秒的呼吸式水晶激发；未过 source/loop/visual gate 前不再
付费重抽、不接 runtime。生产媒体仍为 `0`。

## 2026-08-31：RQ-163 Portal/Account 收口后的 Agent 主线交接

用户确认 Portal/Account 当前展示切片已达到可收口点，8E 的执行重心交回 Agent 主线。该决定不关闭 8E，也不把
研究素材升级为生产素材：`production_media` 继续为 `0`，Workbench、Auth/RSO、路由和正式部署边界不变。

交接批先完成 README 事实版和状态/学习材料对齐，再从 GLM-5.3 G53-0 无 I/O 可用性与配置审计开始。G53-0 已完成本地
静态审计但停在 blocked/deferred，待非敏感账户证据后再决定 G53-1。G53-0 至
G53-4、受限 Review-grounded Coach、Data Dragon/Evidence/Trace/Training、OP.GG useful breadth 与黄金切片、
安全部署合规、8E 退出和 8F 最终评估仍是独立后续闸门。旧 RQ-154 的两地区试水和“决定第三地区”文字只保留为历史，
已由 RQ-157–162 的 13 区 Focus Rail 方向取代。

### 2026-08-31：RQ-165 G53-1 普通 API 适配档案离线 TDD

用户核对官方资料后确认本批走普通智谱 API，而不是 Coding Plan：模型标识为
`glm-5.3-flash`，普通 API 基址为 `https://open.bigmodel.cn/api/paas/v4/`。本地新增按模型精确
选择的不可变 thinking profile，保留 GLM-5.2 的 `disabled` 合同，并为 GLM-5.3/Flash 固定
`enabled + low`；Provider、能力探针和 CLI 共用同一档案，未知测试模型安全回退，工具回合的
不可回传 reasoning 继续 fail closed。聚焦回归 `70 passed, 29 subtests passed`，compileall、
diff 检查和治理通过；没有读取 Key、真实调用、默认模型切换或 Workbench/前端改动。

该结果只关闭 G53-1 的本地适配合同，不代表账号额度、权限、领域质量或生产准入。

### 2026-08-31：RQ-166 G53-2 exact-SHA 公共 CI

G53-1 的 9 个 Provider/CLI/测试文件以独立提交
`0f97b92683e4981842e745a695864deb611bb630` 推送；Actions run `33325222755` 的 head SHA
精确匹配，`pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 全部成功。公共 clean checkout
的 pytest 为 `1912 passed, 145 skipped, 1 warning, 127 subtests passed`；本批未修改 workflow，也未混入
Portal、Account、Workbench、截图、资产或其它脏工作树内容。

G53-2 只证明该离线适配合同在精确提交上通过公共 CI；没有读取/输出 Key、真实 Provider/Riot/OP.GG
调用或默认模型切换，不代表账号权限、真实协议、领域质量或生产准入。下一检查点为等待用户单独授权的
`g53-3-bounded-protocol-gate` 的凭证接缝复核；Stage 8/8E 仍为 `in_progress`，`production_media=0`，8F 尚未开始。

### 2026-08-31：RQ-167 G53-3 有界协议门首次尝试

用户明确继续后，使用进程级临时配置执行一次 `adapter_protocol`，有效模型为 `glm-5.3-flash`，不修改
`.env` 或默认模型。A1 结构化合同在第 1 次调用返回脱敏 `authentication_failed`，A2 tool round trip
按 runner 合同跳过；结果 `calls_used=1/3`、`admitted=false`，没有重试或追加请求。

脱敏结果已写入 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol.json`，
schema 校验通过，未保存响应正文、reasoning 或 Key。该错误码不能区分 Key 无效、权限不足或账户/端点接缝
错误，因此不进入 G53-4；下一步需用户确认/修正凭证接缝并另行决定是否重开同一协议门。

### 2026-08-31：RQ-168/169 G53-3 凭证修正与重开通过

用户确认前次 Key 已删除，重新创建普通 API Key，并将 `.env` 改为 `zhipu`、普通端点
`https://open.bigmodel.cn/api/paas/v4/` 和 `glm-5.3-flash`。重开时没有覆盖旧结果；A1 结构化合同 1/1
通过，A2 Agent 工具往返 2/2 通过（1 次 ToolCall/执行），总调用 `3/3`、`admitted=true`。
脱敏结果为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json`，
SHA-256 `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`，schema 与聚焦回归 `36 passed`。
G53-3 只关闭普通协议接缝；G53-4 新鲜领域门、完整 8E/8F、默认模型切换、生产媒体和部署合规仍未完成，
需用户另行授权。
 G53-3 只关闭普通协议接缝；G53-4 已完成一次本地尝试但未准入，完整 8E/8F、默认模型切换、生产媒体和部署合规仍未完成。
 结果 `zhipu_glm53_flash_domain_adoption_v1.json` 的 SHA-256 为
 `ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`；不在已见考卷上重跑，不放宽并行 ToolCall 合同。

### 2026-08-31：RQ-170 G53-4 新鲜领域门本地拒绝

用户授权后先完成 no-I/O preflight，确认独立三案例、Dataset/Input Plan/Prompt-Context snapshot、协议证据和预算；
预检外部调用为 `0`。真实门严格使用领域 `1/12` 次调用、`0` 个规范化 Token，首案收到并行 ToolCall 后由 Adapter
以 `unsupported_parallel_tool_calls` fail closed，后两案按首错停止跳过；累计含 G53-3 为 `4/15` calls、`1115` tokens，
费用状态 `unknown`。不可变脱敏结果不含 Key、Prompt/响应正文、reasoning、完整请求标识或注入 marker；新 runner/资产
尚无 exact-SHA 公共 CI，因此只是 `completed-local-rejected`，不改变默认模型、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-171 适配器修复与 G53-5 全能力验证准备

旧 G53-4 的并行 ToolCall 首错现在按适配器合同缺口处理，不在原考卷上重跑。Flash 隔离 profile 使用
`thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`；中立 `reasoning_content` 仅在内部回放链路
保留，多个合法 ToolCall 按原顺序由 AgentLoop 逐个执行，能力声明不虚报并发。新的
`g53-5-fresh-flash-capability-gate` 将以独立输入/输出身份和有界预算覆盖文本/思考、结构化、工具批次、上下文
与 Agent 链路；真实 Provider 测试尚未执行。该准备批不改变默认模型、`.env`、Workbench、Auth、前端、
`production_media=0` 或 8E/8F 顺序。

### 2026-08-31：RQ-172 G53-5 全能力矩阵真实观察

新的 `g53-5-fresh-flash-capability-matrix-v1` 已完成一次有界真实矩阵：`11/11` calls、`46,151` tokens、
8 个案例中 `7/8` 通过。adapter core、AgentLoop 的有序多 ToolCall/思考回放、domain development、vendor text
stream 与 vendor multimodal 均有观察证据；F7 vendor tool_stream 在 `max_tokens=512` 以
`incomplete_chat_response`/`length` 结束，不足以证伪能力；F4 缓存未证明（`cached_input_tokens=0`、
`cache_status=unproven`）；F8 仅为 vendor-only 观察。结果为本地真实观察，`production_admitted=false`、
`public_ci_confirmed=false`，不关闭 Stage 8/8E 或生产准入。下一步等待用户决定 Agent 主线下一项；不重跑 G53-4、
不改默认模型、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

为诊断 RQ-172 F7 在 `max_tokens=512` 下的 `incomplete_chat_response`/`length`，新建独立 follow-up；仅把
`max_tokens` 调至 2048，未修改或覆盖 RQ-172/旧结果。实验 `49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`
执行唯一 `1/1` 次真实调用、`557` tokens，`finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15
chunks，source identity stable、`cached=0`。结果文件
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json` 的 SHA-256 为
`105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`，父矩阵 experiment 为
`4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`、父结果 SHA 为
`bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。

该结果仅是 `vendor_raw_transport_only` 诊断，标记 `production_admitted=false`、`public_ci_confirmed=false`；不证明
provider-neutral streaming、Agent 生产能力、领域采用或公共 CI。Stage 8/8E 继续 `in_progress`，下一步等待用户决定
Agent 主线下一项；不改默认模型、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-176 Flash-only 产品运行时晋级（本地接线）

用户已明确选择普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品正常运行目标，不再等待 Pro/Flash 横向比较；
GLM-5.2 只保留为显式兼容/应急回退。该决定改变的是当前实现路线，不是对尚未完成闸门的跳过。唯一注册的
`glm-5.3-flash-runtime-v1` 已从产品组合根显式传入 Worker、Runtime、Agent/工具/Harness、Provider、Runtime
policy 与 Trace identity，并在未绑定时提前拒绝，避免 30 秒质量策略与 90 秒执行窗分裂。Flash 采用 90 秒执行窗、
120 秒传输、2048 输出上限、`temperature=1`、`top_p=0.95` 和 SDK retries=0；Skill 的 30 秒质量门仍独立保留，
Worker lease/heartbeat 默认 360/60 秒。

`.env.example` 与 Compose 模板已对齐 Flash，真实 `.env` 未由本批修改。新实现尚需自己的 exact-SHA 公共 CI，
并在同一 SHA 重取 G53-3，随后才能执行独立 G53-7、完整黄金切片和安全/部署/合规收口；工作树 dirty，旧 G53-3
证据不可复用。Portal、Account、Broadcast Workbench、Auth、路由和 `production_media=0` 均不变。

### 2026-08-31：RQ-177/178 G53-3 证据分离与 G53-7 A/B 身份预检

RQ-177 的新协议结果固定记录实现提交 A=`f0d5ee2…`，证据提交 B=`407ee75…`；RQ-178 又完成了
`GLM53ABIdentityBinding` 的本地无 I/O 预检，明确分离 A 的实现/协议 `code_sha`、B 的独立 CI 和当前
`HEAD=B`，并从 B 的 Git blob 校验 canonical-LF 摘要及只新增 capability-result 文件的差异。相关聚焦回归
`53 passed`；随后 RQ-179 已将最终实现 A=`9e6d78be…` 取得 exact-SHA 公共 CI，因此下一步是该 A 上
重取 G53-3 → 只新增证据 B → B 的 CI，之后才评估 G53-7 领域门；8E/8F、生产准入和
`production_media=0` 不变。

### 2026-08-31：RQ-180 G53-7 首次真实领域尝试

在 RQ-179 的最终实现 A、同 SHA G53-3 和证据 B 公共 CI 均完成后，用户明确授权执行一次 G53-7。运行在干净
LF checkout 上，协议 3/3 加领域 2/12，累计 5/15 calls、领域 3505 tokens；首例
`flash_gate_baseline_01` 以适配器安全聚合码 `provider_response_invalid` / `incomplete_chat_response` 停止，
后两例按首错跳过，`admitted=false`。脱敏结果
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`
的 canonical-LF SHA-256 为 `21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment
为 `236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；结果由本地 C=`9157cde…` 承载，
未推送、未取得公共 CI。底层供应商结束原因、Key、正文和 reasoning 未保留，不能进一步断言是 `length`。
本次不产生领域/生产准入，Stage 8/8E 仍 `in_progress`，`production_media=0`；当前停止自动重试，若继续须另立
版本化的 Flash 响应完成/截断诊断并取得用户授权。

### 2026-08-31：RQ-181 Flash 响应完成度诊断

RQ-180 的安全聚合码只说明适配器拒绝了不完整响应，不能解释底层结束原因。用户随后授权一次独立、正文零留存的
首案例诊断：在产品实现基线 `7cb66d218389c0e7d7aa7b2b1969a4678402f857` 上，使用诊断代码
`447c11e85b6da53fe678d68e25d96b589c0d6ca2`，只调用 `flash_gate_baseline_01` 一次（供应商调用 `1/4`，SDK
重试为 0）。首个 `agent_initial` 回合的有效 Usage 为 input `2220` / output `2048`，原始
`finish_reason=length`，正文为空、reasoning 非空、ToolCall 为 0；适配器按现有 fail-closed 合同返回
`incomplete_chat_response`，因此 normalized/settled 均为 `0/1`，Agent 状态为 `failed/provider_error`。

脱敏结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
的 canonical-LF SHA-256 为 `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，experiment 为
`b1e4a1fc51bed23803b5f94acbd2a652330d5847061dbb7b60022c88da4ff1b9`，由本地证据提交
`baa9cc756ff9e3dfc5eac19119315b7f9f0b56da` 承载；不保存 Prompt、正文、reasoning、Key、请求 ID 或工具参数。
这只确认本次“最大推理档案先耗尽 2048 输出额度”的失败路径，不覆盖 RQ-180 的旧响应，也不表示模型或账号不可用。
下一步先设计版本化的响应完成/截断策略并补离线 TDD；在得到新的明确授权前，不提高全局上限、不改适配器生产合同、
不重跑领域门，不改 Dataset/Plan、Portal、Account、Workbench、Auth、路由或 `production_media=0`。

### 2026-08-31：RQ-183 候选恢复合同（不改变生产默认）

RQ-183 在 8E 内把 RQ-182 的候选进一步拆成可审计的离线合同：精确绑定
`glm-5.3-flash-runtime-v2-candidate/2.0.0`，只允许 `primary` 与一次
`fresh_recovery`；账本按每个底层调用预留/结算并累计 token、时间和失败消耗，独立
Trace 只保留脱敏状态。候选计划始终 `execution_allowed=false`，不进入产品注册表，严格
Flash v1 的 2048/零额外调用不变。`30 passed` 与相邻回归不能替代 exact-SHA CI、同 SHA
G53-3、一次真实诊断授权、G53-7、黄金切片或安全/部署/合规；8E/8F 与
`production_media=0` 仍未完成。

### 2026-08-31：RQ-184 候选合同公共证据链（不改变生产默认）

RQ-184 完成了 RQ-183 候选合同的公共可复现性与协议身份接缝。实现提交
A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 Actions run `33405110692`，以及只新增脱敏结果的直接子提交
B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 的 Actions run `33405881172`，均由 `pytest`、`packaging-smoke`、
`postgres-migrations` 三 job 全部成功见证。同一 A checkout 的 G53-3 严格 `3/3` 次调用通过：A1 `1/1`、A2 `2/2`，
`admitted=true`，SDK retries 为 `0`；结果文件的 `code_sha` 为 A，A/B 无 I/O identity preflight 通过，canonical-LF
SHA-256=`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

这组证据只提升候选合同的公共可复现性，不注册候选、不发 fresh-recovery、不构成 G53-7/领域采用/生产成熟度，也不改变
严格 Flash v1 的 2048/零额外调用、默认模型、Workbench、Portal/Account、Auth、路由或 `production_media=0`。下一项
仍是用户单独授权的一次有界候选恢复诊断，随后审查成本、延迟、失败和脱敏 Trace；完整 8E/8F 与安全/部署/合规顺序不变。

### 2026-08-31：RQ-185 候选恢复诊断中断（不改变生产默认）

用户在 RQ-184 后明确继续，重开一次候选恢复诊断；第一次无响应后再次明确继续。隔离诊断代码为
`76de589a128b7a71f1def3316da3f30ebdd3a4c8`，实现基线为 `eca01ce1393286dbbe83992c2985f600ea2b30b0`。
两次独立启动都只进入 `primary` 首回合，SDK `max_retries=0`，没有发送 `fresh_recovery`；首次沿用
120 秒传输边界并在约 60 秒无返回时中止，第二次使用全新结果名和临时 20 秒客户端传输上限，仍在约
60 秒内未结束后终止。两次均没有可观察响应、Usage、finish reason、Trace 或结果 JSON，不能判断请求是否
抵达供应商，费用/计费状态为 `unknown`。

该中断不注册候选、不改变严格 Flash v1 的 2048/零额外调用，也不改变默认模型、AgentLoop、RuntimeTrace、
Portal/Account、Workbench、Auth、路由或 `production_media=0`。当前精确下一项是传输/代理边界复核，需新的
明确授权；G53-7、黄金切片、完整 8E/8F 与安全/部署/合规顺序不提前。

### 2026-09-01：RQ-186 请求级截止诊断（不改变生产默认）

RQ-185 的 20 秒客户端默认值被 `ZhipuProvider` 传入的每请求 `ChatRequest.timeout_s=90` 覆盖。隔离诊断器已新增
受校验的请求级截止，代码提交 `94629161c5d3230629210444b5a1a38212799997`，相关测试 `82 passed`。在实现基线
`eca01ce1393286dbbe83992c2985f600ea2b30b0` 上只发出一个 8192 输出上限、30 秒 timeout、零 SDK retry 的 primary；
约 30.141 秒后以 transport timeout 安全关闭，没有响应、Usage、finish reason、request ID 或 recovery。

脱敏结果 canonical-LF SHA-256=`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`，
由本地提交 `a7874b0` 承载。30 秒低于候选 90 秒 Agent 窗口，因此本结果不拒绝模型能力，也不激活候选；下一项是
候选延迟预算裁决，未经新授权不重试、不进入 G53-7，不改变产品模块或 `production_media=0`。

### 2026-09-01：RQ-187 完整候选窗口诊断（不改变生产默认）

在 RQ-186 已确认请求级截止生效后，用户明确继续执行一次完整候选窗口。隔离诊断代码仍为
`94629161c5d3230629210444b5a1a38212799997`，实现基线为 `eca01ce1393286dbbe83992c2985f600ea2b30b0`；
请求使用 `max_tokens=8192`、`timeout_s=90`、SDK retries `0`，只发出一个 primary。90.188 秒后仍以
`transport timeout` 安全关闭，未收到响应、Usage、finish reason 或 request ID，也未打开 fresh-recovery，费用状态
为 `unknown`。结果 SHA-256=`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，由本地提交
`50ce5be` 承载。

该结果排除了“30 秒诊断过短”，但无响应仍不能区分代理/连接/读取路径与服务端生成延迟，不能写成模型能力失败。
候选继续未注册，严格 Flash v1、产品默认、Portal/Account/Workbench/Auth、G53-7 和 `production_media=0` 均不变；
下一项是传输/生成路径拆分诊断，需新的明确授权。

### 2026-09-01：RQ-188 传输与生成路径拆分诊断（不改变生产默认）

用户新授权后，在隔离工作树只执行固定三路、最多 `3` 次真实调用，SDK `max_retries=0`：合法
`thinking=enabled`/`reasoning_effort=low` 的最小控制、冻结上下文 `max_tokens=256` 的同步请求，以及冻结上下文
`max_tokens=8192` 的流式首块请求。三路均 observed；前两路有效 Usage 且 `finish_reason=length`、正文为空、
reasoning 非空，流式路约 `687ms` 观察到首个 `delta_reasoning` chunk 后按探针合同关闭。总计 `3` calls、输入
`1993`、输出 `272`、缓存输入 `1920`、总计 `2265` tokens、累计延迟 `17172ms`。

正式结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_final_v1.json`
的 experiment 为 `41901515decc6d8768abd56ee3fd49ac1d1a4402f3cc1cef497720995fa80c8e`，canonical-LF SHA-256 为
`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`；诊断代码与 source identity 均为
`b67b4500ebdbff934e470fd92c1461184aa7c49b` 且 stable。该批确认 endpoint/model 路径可达并已开始生成，提示小额度
同步请求会先耗尽 reasoning；不证明完整 provider-neutral streaming、长请求根因、模型一般质量、领域采用或生产成熟度。
候选仍未注册，严格 Flash v1、默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；
下一项为 evaluation-only 的 `candidate-output-budget-calibration`。

### 2026-09-01：RQ-189 输出额度/推理档位校准（不改变生产默认）

在同一冻结上下文、`thinking=enabled`、`temperature=1`、`top_p=0.95` 下，`low+2048` 一次调用在约
28.344 秒返回可见正文并以 `stop` 结束；`low+8192` 和 `max+8192` 各一次调用在约 45.5 秒请求截止内
没有同步响应。结果只证明一条短同步候选路径可完成，不能说明高预算路径是模型失败、账号失败或生产应采用的
固定上限。严格 Flash v1、候选未注册、8-Core/8-Advanced 闸门、完整 8E/8F 和 `production_media=0` 均不变；
下一项为 evaluation-only 的流式可见正文与 `clear_thinking` 组合探针。

### 2026-09-01：RQ-190 流式首个可见正文（不改变生产默认）

RQ-190 在同一冻结上下文上分别执行两条单路原始流式请求：`thinking=enabled`、`reasoning_effort=low`、
`max_tokens=2048`、SDK retries `0`，只改变 `clear_thinking` 的布尔形状。`true` 在 1.813 秒收到首块、2.547 秒出现
首个非空正文；`false` 在 1.500 秒收到首块、3.875 秒出现首个非空正文。两路在正文出现后主动关闭，终态和 Usage
没有被观测，预算状态因此保持 unknown。

这证明单轮两种请求形状都能较快产生可见正文，但不证明 `clear_thinking` 的因果效果、跨轮清理/回放、完整流式装配、
成本或领域/生产能力。结果与代码保持 evaluation-only，严格 Flash v1 仍为 2048/零额外调用，候选不注册；下一项为
完整终态/Usage 探针。

### 2026-09-01：RQ-191 完整流式终态/Usage（不改变生产默认）

在当前产品形状 `clear_thinking=false`、低推理、2048 输出上限下，RQ-191 只发出一条原始流式请求并完整消费到结束。
首块约 2.203 秒、首个可见正文约 3.531 秒，24.140 秒收到 `finish_reason=stop` 和有效 Usage（1973 输入、652 输出、
0 缓存），共 642 个 chunks。该证据把“首正文可达”与“完整终态/Usage 可达”分开确认，但仍只覆盖一份冻结上下文，
不改变严格 Flash v1、候选状态或任何产品接线；下一项为离线 provider-neutral 流式装配合同。

### 2026-09-01：RQ-192 提供商无关流式装配合同（候选接缝）

RQ-192 已将 RQ-191 的原始供应商分块观察落为纯离线候选合同：`ProviderStreamEvent` 负责统一事件形状，
单次 `ProviderStreamAssembler` 只有在底层 EOF、合法终止原因和有效 Usage 同时成立时才交付完整响应。
合同覆盖序号/model/请求摘要稳定性、终止后 Usage-only 尾帧、正文与工具互斥、工具 JSON 安全、字符/数量上限、
失败毒化和 body-free Trace；工具状态采用 copy-on-write，结果默认 repr 不含正文或工具参数。适配器聚焦 `29 passed`。

该项仍是 evaluation-only，不导入 SDK、不发网络请求、不注册候选、不改变 `capabilities.streaming`、严格 Flash v1
2048/零额外调用、Portal/Account/Workbench/Auth、默认模型或 `production_media=0`。下一项为同一新实现 SHA 的公共
CI 与供应商适配器一致性测试，8E 继续 `in_progress`，8F 尚未开始。

### 2026-09-01：RQ-193 智谱流式适配器一致性接缝（不改变生产默认）

RQ-193 在测试模块内以 fake OpenAI-compatible 分块验证智谱到中立合同的翻译：正文/reasoning、工具别名与分片、坏
形状/未知工具/空 choices、model/terminal 边界、异常 `abort()`、正文空白和 Trace 脱敏均有覆盖，conformance 聚焦
`13 passed`。旧 `ZhipuProvider.chat_stream()` 只作为 fake-client 对照，生产 Provider、`capabilities.streaming`、
默认模型和产品模块均未改。

提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA Actions run `33489903978` 已三 job 全绿且 head_sha 精确
匹配，并包含全部 Trace 脱敏断言。公共证据完成后，下一精确项为
候选接线裁决（runtime 范围、预算/Trace/回退/失败门），不自动注册候选、打开 streaming、执行 G53-7 或黄金切片；
Stage 8/8E 继续 `in_progress`，8F 尚未开始，`production_media=0` 不变。

### 2026-09-01：RQ-194 候选级显式智谱→中立适配接缝（公共闭环完成）

RQ-194 已把早期设计草案落成本地实现：`app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamAdapter` 不是
`LLMProvider`，而是调用方显式取得的候选接缝；`ZhipuProvider.stream_adapter(*, tool_stream=False)` 是唯一显式工厂。
`stream_events(request)` 将已绑定的 OpenAI-compatible raw chunks 翻译为 `ProviderStreamEvent`，`assemble()` 再交给
`ProviderStreamAssembler`，并保证单次开流、正常 EOF/合法 terminal/有效 Usage 才交付完整响应。

适配器继承可信 provider runtime profile 的 `max_output_tokens` 上限（范围 1–8192），请求/显式 cap 只能收紧预算；
请求身份默认必需，Trace 与错误只保留 SHA-256 摘要，不含 Prompt、正文、reasoning、工具参数、Key 或 SDK 对象。
取消、迭代器/翻译/关闭异常均安全 `abort()`/fail-closed；不 retry、不 recovery、不执行 ToolRuntime，不注册 recovery。
提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588` 已三 job 全绿且 head_sha 精确匹配；
`tests/test_zhipu_stream_adapter.py` 聚焦 `20 passed`。这只证明候选接缝公共可复现，不等于产品 runtime 接线或生产准入。

`ZhipuProvider` 既有同步接口、`chat_stream()`、默认模型和 `capabilities.streaming=False` 均不变；AgentLoop、Workbench、
Portal、Account、Auth、路由、预算、Trace、严格 Flash v1 2048/零额外调用及 `production_media=0` 不动，候选未注册。
早期占位符设计保留作历史记录，已由本地实现更新；下一门是独立裁决候选 runtime 接线范围。
Stage 8/8E 仍 `in_progress`，8F 尚未开始，不提前进入 G53-7、黄金切片或生产准入。

### 2026-09-01：RQ-195 候选 runtime 接线架构评审（历史状态）

RQ-195 复核了 RQ-194 的接缝与现有 Agent Runtime 的边界。`ZhipuStreamAdapter.assemble()` 只在 EOF、合法终止和有效
Usage 齐全时交付完整结果；`length`、缺终止、缺 Usage 或读取/翻译/关闭异常都 fail-closed，不能把异常当作恢复资格。
因此不把 adapter 包成 `LLMProvider`，也不改 `AgentLoop` 或默认注册表。未来若单独授权，先在 `app/evaluation/` 设计
`CandidateStreamEvaluationHarness`，精确绑定 provider/model/candidate profile/completion policy 四元身份，并先冻结
只输出字段状态、finish code、Usage 数字、耗时和安全错误码的 `BoundaryObservation`；完整流仍由 assembler 收口。

该评审不改变 `capabilities.streaming=False`、严格 Flash v1 2048/零额外调用、候选未注册、产品模块和
`production_media=0`。当时下一精确项为 `candidate-runtime-wiring-design / pending`；该状态已由 RQ-196 更新，8E 仍进行中，8F 尚未开始。

### 2026-09-01：RQ-196 候选 runtime 接线设计

RQ-196 在用户确认继续推进且基本决定采用 GLM-5.3-Flash 后完成候选 runtime wiring design。该确认被记录为唯一主力
候选目标，不等于静默改成全产品默认。设计冻结 `CandidateRuntimeBinding` 的四元身份与尝试序号、body-free
`BoundaryObservation`、共享事件校验、完整流/不完整流分流、候选 v2 transport 和独立 Trace 投影。

未来候选调用方只在 `app/evaluation/` 显式持有 v2 profile/policy，使用 8192 单次 cap、90/120 秒窗口、`temperature=1`、
`top_p=0.95`、SDK retries=0；按 reserve→open→observe/assemble→settle 结算最多 2 attempts、1 次额外调用、32,000
input、16,384 output、180,000ms，unknown Usage 不当零。完整流仍由 assembler 收口，不完整流不得构造 `ChatResponse`。

本轮新增 ADR-0076、设计计划与学习 walkthrough，未改产品 Runtime、默认模型、`capabilities.streaming`、Portal、Account、
Workbench、Auth、路由或 `production_media=0`，未发真实 API。当时下一精确项为
`candidate-boundary-observation-contract-implementation / pending`；该项已由 RQ-197 推进，先做 fake/local 合同与同 SHA
公共 CI，再另行决定候选 harness、fresh-recovery、G53-7、黄金切片与生产准入。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 将 RQ-196 的设计落成隔离的 fake/local 实现：`app/evaluation/candidate_stream_contract.py`
提供精确 candidate binding、body-free `BoundaryObservation`、不可变快照、字段 presence/状态聚合、候选 v2
注入式 transport port 和独立 Trace 投影；共享事件级校验同时被完整 assembler 与观察器使用，智谱翻译保留
显式 `null` 与字段缺失的区别。

本地聚焦与相邻回归为 `163 passed`，并通过 compileall、`git diff --check` 和 governance。覆盖完整 stop/tool-call、
reasoning-only length、缺 EOF/终态/Usage、身份与序号冲突、工具/输出预算、时钟和资源关闭失败；所有不完整或异常流
均 fail-closed，不构造 `ChatResponse`，用户中断类异常不被吞掉。全量本地首错是 PostgreSQL fixture 缺少
`RIFTCOACH_TEST_DATABASE_URL`，公共 CI 尚待在干净提交上验证。

本批没有真实 API/Key、fresh-recovery、G53-7、候选注册或产品 streaming 接线；严格 Flash v1 2048/零额外调用、
默认模型、AgentLoop、Workbench、Portal、Auth、路由、统一 Trace/预算和 `production_media=0` 均不变。RQ-198 已取得
同 SHA 公共 CI；RQ-199 已完成候选 harness 的两阶段账本/事件泵/receipt 设计；当前唯一下一项为
`candidate-evaluation-harness-implementation / pending`，后续才另行裁决 fresh-recovery、G53-7 与生产准入。

### 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

RQ-197 实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run `33507627615` 三 job
（`pytest`、`postgres-migrations`、`packaging-smoke`）均 `completed/success`，`head_sha` 精确匹配；公共 pytest
为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。候选仍未注册、`execution_allowed=false`，
不打开 `capabilities.streaming`，不发真实 API，不执行 recovery/G53-7，严格 Flash v1、产品模块和
`production_media=0` 不变。当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
本轮在此暂停。

### 2026-09-02：RQ-199 隔离候选评估台设计

RQ-199 在 8E 内新增的是一个候选协调设计门，不是新的生产能力。设计采用隔离的
`CandidateEvaluationHarness`，以 candidate-only staged ledger 解决 primary 发出前
尚未知晓首回合边界、但又必须先 reserve 的时序问题；拒绝 sentinel snapshot 和首回合
结束后才记账。一次 normalized stream 只经一个事件泵，同时服务
`CandidateStreamBoundaryObserver` 与临时 `ProviderStreamAssembler`；完整结果只可经
显式 evaluation consumer 短暂使用，不完整流不构造成产品 `ChatResponse`。

新增 ADR-0077、实现计划和学习 walkthrough，冻结独立 body-free
`CandidateEvaluationReceipt`、Usage unknown/预算/取消/关闭/重复结算失败语义和 fake/local
测试矩阵。当前 activation 仍关闭，候选仍 `execution_allowed=false`；严格 Flash v1 的
2048/零额外调用、`capabilities.streaming=False`、默认模型、AgentLoop、Workbench、
Portal、Account、Auth、路由和 `production_media=0` 不变。该设计不注册候选、不发真实
API、不执行 fresh-recovery、G53-7 或黄金切片。当前唯一下一项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。

### 2026-09-02：RQ-200 隔离候选评估台本地实现

RQ-200 将 RQ-199 的设计落成隔离 fake/local 实现：`CandidateEvaluationHarness` 先在 primary I/O
前通过 candidate-only staged ledger 预留槽位，再以同一条 normalized event pump 同时驱动
body-free 边界观察器和一次性内存 assembler，观察完成后重算策略并结算。完整 stop/tool 流只可
经显式 evaluation consumer 短暂使用；不完整流、未知 Usage、open/read/clock/close 异常和身份/
预算冲突均 fail-closed，不构造产品 `ChatResponse`，不执行 ToolRuntime 或隐式 retry。

本地 harness 聚焦 `15 passed`，与边界观察、流装配及旧恢复合同相邻回归 `102 passed`；Python
3.11/3.13 编译、diff check、governance 通过。RQ-201 已补齐实现提交
`f2a80320123d80a6441f3fcac310014a9bd4550e` 的 exact-SHA 公共 CI run `33536168224`（三 job 全绿，
公共 pytest `2193 passed, 145 skipped, 1 warning, 127 subtests passed`）。activation 仍 disabled，
候选未注册，严格 Flash v1 2048/零额外调用、`capabilities.streaming=False`、默认模型、产品 Runtime、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。当前唯一下一项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`；
只允许在单独授权后复核 recovery 的传输/预算/失败边界。

### 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 Actions run `33536168224` 已完成，
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功且 `head_sha` 精确匹配；公共 pytest
为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。该证据只证明 fake/local 候选评估台可公共复现，
不注册候选、不打开 `capabilities.streaming`，不改变严格 Flash v1、默认模型、产品 Runtime、Portal、Account、
Workbench、Auth、路由或 `production_media=0`。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`，需单独授权。

### 2026-09-02：RQ-202 候选 recovery 诊断边界复核

RQ-202 在 RQ-201 公共 CI 后完成了候选 recovery 的离线边界复核。回执的顶层终态/动作/安全错误、
attempt 决定/装配状态与 budget projection 现在都从 body-free 观察和候选硬上限推导；observer 的
单次 elapsed 截止绑定 90 秒，账本继续独立维护累计 180 秒。旧同步诊断器因直接持有 SDK/真实 I/O
并复用 unknown Usage 当零的旧账本，不作为新诊断版本基础。

本门 harness 聚焦 `18 passed`，相邻候选集合 `127 passed, 1 deselected`，compileall、diff check、
governance 通过。加固提交 `67031145d3b3e5c864e881576c69e2fda931e950` 的 Actions run `33582049836`
三 job exact-SHA 全绿，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
候选仍 disabled、未注册、不打开 `capabilities.streaming`；严格 Flash v1、默认
Runtime、AgentLoop、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变，没有真实
API/recovery/G53-7/黄金切片/8F 证据。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`，
需再次单独授权后才设计新诊断协议。

### 2026-09-02：RQ-203 版本化候选 recovery 诊断协议设计

RQ-203 在 RQ-202 的离线边界加固与公共验证之后，完成了独立的版本化诊断协议设计：协议 ID 为
`glm-5.3-flash-candidate-recovery-diagnostic-v2`，schema 为 `2.0.0`，并把 provider/model、runtime
profile、policy、实现/计划/上下文/运行 SHA 绑定为不可替代的候选身份。请求只留下角色、字段存在性、长度和
工具数量等形状摘要，不保存 Prompt、正文、reasoning、工具参数、Key 或原始 request ID。

设计冻结 `reserve → open → observe/assemble → settle → receipt`，每次潜在 I/O 先占用槽位；fresh
recovery 是完整的新请求，不是 resume、SDK retry、AgentLoop retry 或 ToolRuntime 副作用。预算、Usage、
费用和延迟均采用可解释的三态/分段记录，失败聚合保留第一现场，回执只允许原子 create-only 的 body-free
JSON。该门只有文档设计，没有实现、真实 API、候选注册或产品 Runtime 变化；严格 Flash v1、默认模型、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变，8E 仍进行中、8F 尚未开始。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`。
下一门只实现 fake/local v2 协议和聚焦测试；真实 recovery、G53-7、黄金切片、生产准入与 8F 仍须后续独立裁决。

### 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现

RQ-204 已把 RQ-203 冻结的版本化诊断协议落成隔离的
`app/evaluation/candidate_recovery_diagnostic_v2.py`。它在 primary I/O 前预留候选槽位，
用一次 normalized event pump 同时驱动 body-free observer 与临时 assembler，并从可信观察
重新推导 attempt/预算/费用/延迟/失败和最终回执；`from_dict()` 与 canonical JSON 落盘均执行
递归 allow-list，已有文件不会被覆盖。

本地新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归 `82 passed`，
Python 3.11/3.13 compileall、静态 no-I/O/import 和 diff check 通过。系统 Python 3.13 用户环境已
安装 `pytest 9.1.1`，项目测试仍使用仓库 `.venv` 的完整依赖。该实现仍属于 8-Advanced candidate
evidence：activation disabled、候选未注册、不打开 `capabilities.streaming`，严格 Flash v1 2048/
零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0`
不变；没有真实 API/Key、第二次 recovery、G53-7、黄金切片、生产准入或 8F 证据。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`；
先取得同一干净实现提交的 exact-SHA 公共 CI 和协议 dry-run。

### 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环

RQ-205 已完成 RQ-204 的同 SHA 公共验证与 fake/local 协议演练：提交
`90242822df0e47304700644572bc12f0a3aa88ad` 的 Actions run `33598541029` 三 job 全绿，公共 pytest
为 `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为 `201 passed, 1 warning`；
前端契约、typecheck、unit、build、E2E、RAG、治理和打包冒烟均通过。一次本地 fake primary 演练写入临时
canonical body-free 回执，未读取 Key、未发真实 API、未执行第二次 recovery。

候选仍是 8-Advanced evaluation evidence，不是 8-Core 产品能力：activation disabled、
`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用、默认模型、
产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变。当前唯一下一精确
checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
真实 recovery、G53-7、黄金切片、生产安全/部署/合规与 8F 仍需另行裁决。

### 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察

RQ-206 在同一干净隔离工作树只执行 1 次有界真实 primary：提交
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run `33603143606` 三 job exact-SHA 全绿，
实现基线为 `90242822df0e47304700644572bc12f0a3aa88ad`。普通智谱
`zhipu/glm-5.3-flash` 流观察到首事件、reasoning、可见正文、`stop` 和 EOF；首事件 `3078ms`、
首个可见正文 `151453ms`、总延迟 `175875ms`。Usage 缺失、close 失败，单次 90 秒 attempt 门在晚到事件中触发，
因此回执为 `fail_closed / elapsed_limit`，没有第二次 recovery，费用 unknown。`open_elapsed_ms=0` 仅是惰性流计时起点。

该结果确认请求确实到达接口并产生内容，但不构成 API/Key 失败、模型一般质量、领域准入或生产成熟度结论。
候选仍 disabled、未注册，严格 Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、
Auth、路由、`production_media=0`、G53-7、黄金切片和 8F 边界均不变。持久 body-free 回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`
（`4355` bytes，SHA-256 `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`）。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
先离线设计和测试硬墙钟取消、流关闭与 Usage/终态尾帧处理，再另行裁决真实重测。

### 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧后续

RQ-207 在 8E 内完成候选 GLM-5.3 Flash 的显式 `CandidateStreamSession` 与
`CandidateStreamDeadlineSupervisor` 本地实现：以 attempt 起点的绝对 monotonic deadline 控制墙钟，
只允许显式、协作式且可重复调用的 cancel/close，抑制截止后的迟到事件，并严格处理终态与 Usage 尾帧。
四文件聚焦回归（deadline 10、v2 24、real 8、adapter 25）统一为 `67 passed`；
本轮不读取 Key、不调用真实 API、不发起重试或第二次请求。

该证据仍是 8-Advanced candidate-only：候选 `activation_state=disabled`、
`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用，
产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变，Stage 8/8E 保持
`in_progress`。硬模式必须提供显式 session opener；若其返回 legacy iterable，兼容性校验只在 opener 返回后进行，
不能声称 opener I/O 已被预验证。同步 opener 可能越过计时器，SDK `close()` 是否非阻塞并唤醒 `next()` 仍未由
provider/public CI 证明；超时必须 fail closed，Usage 缺失保持 unknown/null，close 失败只作次级证据。

> 历史快照（RQ-207 本地实现完成时）：当时的下一精确 checkpoint 曾为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
> RQ-208 已完成该公共 CI，当前唯一指针见下方最新段落。

### 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

RQ-207 的候选硬墙钟会话、取消/关闭资源合同与 Usage 尾帧离线实现，已在提交
`015b022bfce6d03452f753794ac126a377f8355b` 取得 Actions run `33613113829` 的 exact-SHA 公共 CI 闭环；
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均为 `completed/success`。本地四文件聚焦回归仍为
`67 passed`，公共 pytest 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为
`201 passed, 1 warning`。本轮没有新的真实 API、重试或第二次请求。

该公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 的非阻塞/唤醒能力，也不构成模型一般能力、
领域采用或生产成熟度结论；同步 opener 永久阻塞与 SDK close 无法唤醒 `next()` 仍需真实 provider 验证。候选仍
`activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1
2048/零额外调用，默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由与 `production_media=0` 不变，
Stage 8/8E 继续 `in_progress`。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
公共 CI 已闭环，真实重测只能在新的明确一次性授权后执行，不能自动注册候选或进入 G53-7。
