# RiftCoach Agent 项目决策记录

## 项目定位

RiftCoach Agent 是一个面向英雄联盟公开账号的离线赛后复盘与长期训练助手。

项目只分析已经结束的公开赛后数据，不提供实时对局辅助，不读取客户端内存，不追踪隐藏敌方信息，不自动操作游戏，也不提供不公平竞技优势。

## 能力基线

动态进度和唯一下一步只看 `docs/project_execution_state.md`。截至
2026-08-15，已经实现并有测试证据的本地基础包括：

- Riot ID、PUUID、最近对局与 Timeline 数据链路；
- MatchAnalyzer 确定性指标；
- Data Dragon 静态中文映射；
- 中文确定性报告；
- 质量门控 Harness v1；
- Provider 抽象、能力协商与 Registry；
- 带 Schema、超时、重试、缓存、熔断和指标的 Tool Runtime；
- 本地混合 RAG v1 与 4M 小型独立评测门禁；
- 智谱 GLM 教练报告；
- 最小 Provider-neutral Agent Loop；
- `recent-form-review` 与 `single-match-review` 两个用户 Skill Contract；
- 完整 Skill Router V1（含 5C 退出复核）；development 为 23/23，单次 holdout 为
  11/12，ADR-0010 暂缓 LLM Router fallback；
- 5D-1 Skill 执行前边界：selected name/version、共享安全 run ID、typed input 与
  Harness 输入内容摘要绑定；
- 5D-2 Context Builder V1：两个 Skill 的最小事实 allowlist、信任分层、初始知识
  citation 投影与 Manifest ceiling 内的确定性整段选择；
- 5D-3 Skill Run Compiler & Budget Enforcement：Manifest-only 权限/预算编译、完整
  消息估算、逐轮累计 Context 门禁与协作式总 deadline；
- 5D-4 Evidence-Aware Agent Draft Preparation：只从实际知识工具执行构造共享
  `KnowledgeEvidence`，并把 Agent 最终文本保留为尚未发布的 `CoachDraft`；
- 5D-5 Harness Composition & Typed Terminal Output：统一 `DraftPreparationStep`、旧
  顺序 Adapter、唯一 ReviewHarness 控制流，以及由终态 Artifact 构造的 typed Output；
- 5D-6a Structured Output Contract：请求声明 Provider-neutral JSON Schema，严格
  Pydantic Evaluation 验证、最多一次同合同 repair，以及解析失败的 fail-closed 降级边界；
- 5D-6b 的生产 Zhipu Adapter 与真实最小 structured/tool 协议准入；recent-form
  真实领域运行已尝试但未形成统一响应、工具证据或 Evaluation，ADR-0012 明确领域
  能力不准入并保留确定性 fallback；
- 独立事实评测、受限修订、再评测与发布门控。

当前仍未实现：

- 真实 GLM recent-form 领域 Skill/Harness 准入和通过冻结 held-out 的第二 Provider；
- 统一 AgentRuntime；
- FastAPI 会话入口；
- 玩家长期 Memory；
- 标准 MCP Client/Server；
- 真正具有独立上下文和工具权限的 Multi-Agent；
- LoL 专属前端和完整可观测性。

## 架构母本与参考项目

RiftCoach 保持独立仓库和自主领域核心，不直接 fork 或换皮 EchoMind、AGI-Saber、Sea-Mult-Agent。

- EchoMind 作为应用架构参考，选择性吸收 Tool Manager、用户与会话、Memory、Monitor 和 Evaluation 思想；
- AGI-Saber 作为高级运行时参考，后期选择性吸收 Context Builder、父子块检索、DAG、取消、快照和恢复；
- Sea-Mult-Agent 作为可靠执行参考，阶段 2 吸收 Artifact、预算和终态原则，阶段 8 再评估租约、事件历史、恢复与迟到结果隔离；
- 不迁移到 Go，不引入与 LoL 复盘无关的科研沙箱、论文复现或 Benchmark 业务模块；
- EchoMind 与 AGI-Saber 现有的所谓 MCP 均不视为标准 MCP 实现，RiftCoach 将独立实现标准协议。

## Skill 与事实审查边界

- `recent-form-review` 与 `single-match-review` 是用户请求 Router 选择的两个领域
  Skill；
- 报告事实审查不是第三个 Skill，而是现有 Harness 的强制 `EvaluatorStep`；
- Harness 掌握评测时机、修订预算、阈值、发布、降级和拒绝，Router 不能绕过；
- 不为维持 Skill 数量复制已有 Evaluator 合同，也不在没有真实内部 Skill 时提前
  扩展 Manifest 调用模式；
- 这仍是单 Runtime 的多阶段工作流，不等于 Multi-Agent。

Skill Router V1 继续使用确定性 Manifest 信号，不调用模型。holdout 的唯一设备域
假朋友不足以证明 LLM fallback 的收益；ADR-0010 决定优先类型化入口与会话澄清，
只有新鲜失败族、新数据集、结构化输出、质量/成本/故障证据齐备后才重开模型实验。

原内部 Skill 提案见 ADR-0008，当前决策见 ADR-0009。
模型路由采用决策见 ADR-0010。

## 5D 受限 Skill 执行组合

- `SkillExecutionBoundary` 负责核对 selected RouterDecision、加载同名同版本 Skill
  并验证输入；`SkillReviewExecutor` 只接受该验证结果，核对 Context 身份并协调
  Agent 与 Harness 接缝；
- 其中 5D-1 已实现执行前核对部分：Router 锁定 name/version，Catalog 重新取得
  `LoadedSkill`，Skill input model 验证 payload，并以同一安全 run ID 和规范字节
  SHA-256 绑定未来 Harness 输入；
- 5D-2 已实现 Context 构造：内部 Policy 与 SKILL.md 为 system 指令，玩家事实、
  用户请求和初始 citation 为 user/data-only；近期与单局使用不同 allowlist，预算
  只整段保留或省略；
- 5D-3 已实现请求编译和运行预算：权限与迭代/工具/超时只来自 Manifest，累计消息
  在每次 Provider 调用前检查，Provider/Tool 共用递减的协作式总 deadline；
- 5D-4 已实现证据化草稿准备：新旧路径共用知识 payload 转换器，Agent 最终文本
  只能成为 `CoachDraft`，只有成功且归因合法的实际 `knowledge.search`
  ToolExecutionRecord 才能成为 `KnowledgeEvidence`；
- 5D-5 已实现单一质量控制流：`ReviewHarness` 只消费统一 preparation 合同，旧
  Retriever/Generator 使用顺序 Adapter；Agent 路径的质量阈值和 fallback 只来自
  Skill Manifest；
- terminal Skill Output 不从模型响应直接构造，只读取 terminal Manifest、带摘要校验
  的 FINAL_REPORT、最终 attempt Evaluation、实际 Evidence 和两份输入 Artifact；
- AgentLoop 只负责白名单工具调用和 Coach 草稿准备，不拥有发布权；
- 新 `DraftPreparationStep` 返回同一 `CoachDraft + KnowledgeEvidence`，用于兼容旧
  Retriever/Generator 路径与新 Agent 路径；
- `ReviewHarness` 继续是评测、受限修订、发布、降级和拒绝的唯一控制面；
- Context Builder 把内部策略、Skill 指令、确定性事实、用户文本、RAG 和 Tool
  Observation 分层，权限永远不从不可信文本获得；
- 结构化模型输出先服务机器消费的 EvaluationResult，Coach 报告仍为 Markdown；
- 结构化请求必须经过 capability negotiation；5D-6b 的生产 Zhipu Adapter 已真实准入
  最小 JSON mode 与 Tool Calling 协议，但这不等于领域 Skill 已准入；
- 第二 Provider 候选选择曾被要求等待 5D-7 冻结同一领域任务、指标和失败分类；该条件
  在 D1-D3 后满足，D4 才由 ADR-0017 作出初始候选决策，并由 ADR-0018 基于完整领域
  准入目标更正；
  早期 P1/P2 通过而 P3/P4 暴露默认 Thinking 和旧参数验收边界的结果已保留；
- 最终 P1-P5 在显式 disabled-thinking 后 5/5 低层通过；生产 Adapter 已完成离线双向
  映射；3-call 协议控制器用一个预算 Provider 组合严格 structured request、现有
  AgentLoop 和固定只读知识工具；该切片随后在公开 CI 成功 SHA 上真实 3/3 通过，只
  准入最小 Adapter 协议，仍须领域 Skill/Harness 切片，不能写成 GLM Agent 已上线；
- Recent-form Domain Slice 控制器组合真实 Catalog/Router/Context、AgentLoop、本地
  RAG、唯一 ReviewHarness 和 typed output，并让 Agent/Harness 共用剩余 4 calls；
  真实运行只执行一次，在一个计费请求后没有统一 `ChatResponse` 进入 Agent，故无
  ToolCall、证据、Evaluation 或质量分，Harness 安全降级；
- ADR-0012 分层裁决：Zhipu 最小协议准入，GLM-5.2 recent-form 领域能力不准入；不
  重跑或临场调 Prompt，错误来源丢失与多案例领域质量进入 5D-7；
- ADR-0013 决定 5D-7 使用分层领域评测：Dataset 冻结 Agent/Tool/Evidence/
  Evaluation/Terminal/Resources 期望，Candidate 只保存脱敏观测；development 可用于
  评测器开发，held-out 必须排除校准并显式确认规则冻结；未知延迟、Token 和成本保持
  `null`，不能伪造为 0；
- 5D-7 Batch A 的 10 案例离线基线只证明评测器能识别已知控制观测、故意构造的不安全
  发布负例，不是 Prompt、真实 Provider、报告质量或注入防护的准入结果；
- ADR-0014 要求所有后续领域实验先通过 Prompt/Context 语义身份 admission；ADR-0015
  再把 Batch C 候选升级为 `offline_executable`：只用 Scripted Provider 固定模型响应，
  Catalog/Router/Context、AgentLoop、ToolRuntime、本地 RAG、Evidence 和 ReviewHarness
  全部运行真实实现；
- Batch C 的 7 个 development 场景覆盖缺工具、事实错误、坏引用、用户/RAG 注入和
  Evaluation 漏判；一个含 RAG canary 的报告被实际发布并由分层评测标为
  `unsafe_publication`。这是必须保留的质量门 Bad Case，不是让测试追求全绿的理由；
- `offline_executable` 每个案例必须有 provenance SHA-256，公开 Candidate/Result 只保存
  脱敏结构化观测。它证明本地控制流和实验接线，不证明 GLM/DeepSeek/Qwen 的模型能力；
- ADR-0016 决定不原地改写 `coach_evaluation@1.0.0`，也不把已知 canary 硬编码为生产
  关键词；D1-D2 已以离线 TDD 新建并接入 1.1.0 最小安全输入/输出合同，让 Harness 对
  `prompt_injection` blocking issue 直接降级或拒绝，不交给 Reviser；secure offline
  development 7 场的 task/failure accuracy 均为 `1.0`，unsafe publication 为 `0.0`，
  external calls 为 `0`；
- held-out 只能在 D1/D2 合同、Prompt、snapshot 与规则冻结后创建，D3 已创建 3 场并标记
  `calibration_excluded=true`，但首次结果尚未运行且不得用于反向调当前规则；真实首轮
  固定正常、用户注入、知识注入 3 场，每 Provider 领域最多 12 calls、`max_revisions=0`、
  SDK retry 为 0；
- ADR-0018 已取代 ADR-0017 的候选模型与金额停止线：D5 唯一有界候选改为 DeepSeek
  官方 `deepseek-v4-pro`，要求独立 Adapter、non-thinking、最多 3-call 协议门 +
  12-call 领域门、Token/金额停止线和安全错误归因；D5 已完成离线实现，随后真实最小
  structured/tool 协议只运行一次并以 3/3 calls 准入；该结论不等于领域 held-out、
  报告质量、抗未知注入或产品默认模型已准入；
- DeepSeek 领域 held-out 执行接缝进一步把 no-I/O admission 与 Provider 数据面分开，
  从真实协议账本继承 calls/Token/金额，增加 domain/单例资源门、逐例分层判断、首错
  停止、unsafe 全局停止和 Provider 前结果预留；独立输入计划、oracle-blind 生产
  Executor 与 Key-last CLI 已完成离线 TDD，并由提交 `eb198354b3186f25b7d0455d7ed28725bc17e234`
  和 GitHub Actions run `31799394506` 完成 exact-SHA 公开验证；真实 held-out 结果仍待
  单独授权领域门；
- GLM 是首个真实基准 Adapter，不是永久模型选择；Qwen3.8 Max 因 reasoning/计费入口
  增加首轮变量而暂缓，DeepSeek V4 Flash 因本轮唯一候选还需代表复杂领域能力而暂缓；
  ADR-0019 将 Flash/Pro 分层明确为 5P 后的横向 Provider 优化门，默认等待阶段 6 真实
  成本/时延证据；5F 继续只负责 Pi / Claude Agent SDK Runtime 采用实验；
- 该组合方案由 ADR-0011 接受，分层准入结论由 ADR-0012 接受，领域评测方案由
  ADR-0013 接受，实验身份由 ADR-0014 接受，离线可执行基线由 ADR-0015 接受，版本化
  注入评测与真实实验门由 ADR-0016 接受，第二 Provider 门的原始历史由 ADR-0017
  保留，当前候选与预算更正由 ADR-0018 接受，未来模型分层归属由 ADR-0019 接受；
  领域 held-out 的 no-I/O admission、薄协调器、累计/单例资源门和不可重复输出由
  ADR-0020 接受；未执行考卷的注入成功语义、独立输入计划与 oracle-blind 生产装配由
  ADR-0021 接受；真实领域 Bad Case 后，多 ToolCall 批次由 Adapter 严格解码、
  AgentLoop 整批预检并顺序执行的 development 方案由 ADR-0022 接受，并已完成本地
  Adapter/AgentLoop/真实 RAG-Evaluation-Harness 纵向 TDD；
  D1-D5 与领域执行接缝已完成离线实现且 DeepSeek 最小真实协议已准入，当前仍处于 5D-7，不等于
  整个 5D、领域 held-out、LangGraph 或 Multi-Agent 已实现。

## 数据职责

- Riot API：玩家已经发生的比赛事实；
- Data Dragon：英雄、装备、符文和召唤师技能的静态映射；
- RAG：指标解释、复盘方法、训练规则与可追溯知识；
- OP.GG MCP：后续接入的动态版本 Meta；
- Memory：玩家画像、历史训练目标和进度，不存放全部原始对局数据；
- GLM：当前唯一真实模型基线，负责组织和解释证据，不负责创造比赛事实；
- DeepSeek V4 Pro：D5 唯一有界第二 Provider 候选；独立 Adapter 已实现且真实最小
  structured/tool 协议已准入；真实领域 held-out 随后只运行一次，并在首个正常案例因
  `unsupported_parallel_tool_calls` fail closed；该执行接缝已离线修复但没有新的真实模型
  质量证据，领域仍未准入且未设为默认模型；
- DeepSeek V4 Flash：本轮不测试；最早在 5P 后、默认在阶段 6 以真实产品成本/时延
  Bad Case 触发 Pro-only、Flash-only 与 Flash 默认/Pro 有界升级对照；
- Qwen3.8 Max 等：本轮暂缓，尚未锁定为生产组合。

## 质量原则

任何 LLM Coach 报告必须经过独立评测。评测失败时只允许根据结构化问题做受限修订；达到修订上限仍不通过时，拒绝发布 LLM 报告或降级到确定性报告。

完整阶段路线见 `docs/roadmap.md`，正式架构决策见 `docs/adr/`。

## GLM-5.3 迁移边界（2026-08-15）

智谱官方 GLM-5.3 页面已发布，Coding Plan 已开放，普通模型 API 将逐步上线；GLM-5.3
始终启用 thinking，不能沿用当前 Zhipu Adapter 的 disabled thinking。GLM-5.3 因此被
记录为隔离的同厂商模型迁移候选，而不是 GLM-5.2 结果的替换或自动升级。

- 当前 5D-7 的唯一下一步不变：先设计新的、未污染的真实领域采用门；
- 当前不修改 `.env` 默认模型，不读取 Key，不调用 GLM-5.3；
- G53-0 至 G53-4 必须依次完成可用性审计、Zhipu thinking profile 离线 TDD、公开 CI、
  最多 3-call 协议门和新鲜领域门；
- GLM-5.2 历史证据、DeepSeek Adapter/结果/预算/held-out 均保持只读，GLM-5.3 通过
  领域门前不替换默认模型；
- GLM-5.3 迁移不等于自动模型路由或 Multi-Agent。

详细设计见 `docs/plans/2026-08-15-glm53-provider-adoption-design.md` 和 ADR-0023。

## DeepSeek 新鲜领域采用门（2026-08-15）

旧 Dataset 1.1.0 已经产生一次真实拒绝结果，并直接触发多 ToolCall 兼容性修复。它可以
继续验证已知 Bug 没有回归，但不能再承担未知领域准入。ADR-0024 决定：

- 复用已有 no-I/O admission、薄协调器、预算 Provider、production Executor、分层
  Evaluator 和唯一 ReviewHarness，不复制第二套 Agent 控制流；
- 旧协议、Dataset、输入计划和拒绝结果全部按 bytes SHA 只读保存，不重跑或复制改名；
- 先用合成 development 数据完成兼容合同和 exact-SHA CI，之后才创建新的匿名 fixture、
  三案例 held-out、输入计划和逐案例 Prompt/Context 摘要；
- 新门同时绑定历史真实证据、多 ToolCall 修复 CI、当前代码/CI 和所有新输入身份；
- 未来新鲜范围最多 12 calls、每例 4 calls、12000/4000 tokens、每请求 1024 output、
  `$0.10`、零重试/零修订和首错停止；真实运行仍需单独确认；
- 三例必须全部安全发布，task/failure accuracy 均为 `1.0` 且 unsafe publication 为
  `0.0`，才能准入 Pro 领域能力；通过也不自动设为默认模型。

本设计不改变 Flash、GLM-5.3、5F 或 5P/阶段 6 的归属。详细设计见
`docs/plans/2026-08-15-deepseek-fresh-domain-adoption-gate-design.md` 和 ADR-0024。

### Fresh-Gate 1 实现裁决

Fresh-Gate 1 采用“兼容扩展 + 专用 development admission”，不建立第二套 Runtime：

- input plan 与 Prompt/Context snapshot 保留 V1.0 语义，新能力使用 V1.1；
- 三个案例各自通过真实 Skill 路由和 ContextBuilder 后形成摘要，不能再用一个 demo
  Context 代表整场实验；
- 历史证据链固定旧协议/拒绝结果 bytes、`3+1` 调用、ADR-0022 修复提交与公开 CI；
- 规范化前失败的旧领域 Token/费用写为 unknown，不根据统一记录中的零值推断未计费；
- 当前只产生 `FreshDomainDevelopmentAdmission`，固定禁止 Provider 构造，不提前加入
  held-out/真实运行入口。

该实现已由提交 `adba965a7f7fb4293020502b4440e9880633e571` 与 GitHub Actions run
`31860874440` 完成 exact-SHA 公开验证。下一步才允许单独创建新考卷资产，但创建不等于
运行，且仍不得读取 Key。完整实现计划见
`docs/plans/2026-08-15-deepseek-fresh-domain-gate-offline-implementation.md`。

### Fresh-Gate 3 本地资产冻结裁决

Fresh-Gate 3 不新增第二套执行框架，只发布新的静态评测身份：

- 新匿名 3 局 player summary 和确定性报告与旧 fixture bytes、身份和指标均不同；
- 三案例 held-out 的 case ID、用户请求、知识注入正文和 marker 均不复用旧题；
- Dataset 只保存 oracle，V1.1 input plan 保存实际输入，production Executor 仍只接收
  `case_id + provider`；
- 三个案例分别通过真实 Catalog、Router、ExecutionBoundary 和 ContextBuilderV1，形成
  不含正文的 `recent-form-prompt-context-v1-2` 摘要；
- 本地聚焦回归为 `39 passed`，完整回归为 `574 passed, 103 subtests passed`，外部
  Provider calls 和 held-out executions 均为 0，真实结果文件不存在。

资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已通过 GitHub Actions run
`31861960565` 的 exact-SHA 公开 CI。Fresh-Gate 3 已完成；下一步先实现 Fresh-Gate 4
新资产 no-I/O admission/生产 CLI 接缝并再次公开验证，不能因资产存在而读取 Key 或
宣称领域准入。
设计与实施计划见 `docs/plans/2026-08-15-deepseek-fresh-domain-assets-design.md` 和
`docs/plans/2026-08-15-deepseek-fresh-domain-assets-implementation.md`。

### Fresh-Gate 4 运行入口裁决

新鲜真实门采用“Fresh envelope + 既有领域协调器”的版本化组合：

- 不覆盖旧 CLI 证据，也不复制第二套 Agent/Executor/Harness；
- `FreshDomainHeldOutAdmission` 显式绑定历史协议与拒绝结果、ADR-0022 修复 CI、
  Fresh-Gate 3 资产 CI、当前 code/public-CI 和全部新输入身份；
- 旧协议 Context 与新领域 Context 可以不同，但旧协议 result bytes、Provider/model、
  准入状态、资源和 Evaluation identity 必须不漂移；
- 新 result envelope 保存完整 Fresh admission 和原领域分层结果，旧 V1.0 result 继续
  严格复读；
- CLI 的 `--prepare-only` 必须在输出预留、环境加载和 Provider 构造前返回；真实模式仍
  要求显式确认，并按 output reserve → env/Key → Provider 的 Key-last 顺序执行。

当前只完成本地离线入口。Fake Provider 的正常/失败纵向测试证明控制面，不证明真实
DeepSeek 质量；公开 CI 和同 SHA prepare-only 完成前不能读取 Key，完成后真实 12-call
运行仍需单独明确确认。

该入口现已由提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 和 Actions run
`31863341338` 公开验证；同 SHA prepare-only 也以零调用通过。裁决边界不变：这只让真实
运行“具备被确认的资格”，不授权自动调用，也不等于 Provider 领域准入。

### V2 真实执行裁决

用户明确确认后，V2 在公开成功 SHA `741e84140f816fb4b06b2812a8d07d3f32eaf4d0`
上只执行一次。首例第一次调用使用 3440 observed tokens；下一请求需预留 1024 output，
因此超过单例 4000-token 门并在 I/O 前停止。Harness 只返回确定性 fallback，后两例按
首错停止，最终 `admitted=false`。

这次采用门不把失败简单归因于模型质量：真实 Prompt 长度证明原“4 calls/4000 tokens”
资源合同不能保证必需的工具往返与 Evaluation 可达。V2 结果 SHA
`877b623f...dc62a` 永久保留且不得重跑。下一步只做零调用的预算可达性裁决和现实 Usage
TDD；如果仍要评估领域能力，必须经新 ADR、新输入身份和新结果路径建立后续门，不能
直接调高 V2 预算追绿。

该结果与回归已由提交 `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0`、GitHub
Actions run `31864370988` 完成 exact-SHA 公开验证；CI 没有 Key 或 Provider 调用。

### V2 预算可达性裁决

ADR-0025 将“安全上限”和“可行预算”拆开处理：

- V2 真实 3440 observed tokens 加下一请求 1024 output 预留，精确证明 4000 单例上限
  无法发出第二次调用；所需 next-call 最低上限为 4464，短缺 464；
- 现有生产控制流用本地 Scripted Provider 形成初始 Agent、工具后 Agent、Evaluation
  三种真实 request envelope，只持久化消息角色、数量和长度单位，不保存正文；
- 以首轮真实 input 校准得到的 3241/3780/3047 只是风险投影，不是 DeepSeek 官方
  tokenizer 结果；未来轮次 output 和完整精确需求保持 unknown；
- 因此不关闭 DeepSeek 领域候选，也不直接授权 V3。先完成公开 CI，再用 development
  校准新资源合同；任何 V3 必须使用新预算、新输入身份、新结果路径和独立真实确认。

### V3 development 资源校准裁决

ADR-0026 选择“生产形状请求 + 独立 Usage replay”，而不是直接调高 V2 或让一次随机
development E2E 同时承担资源和质量评测：

- baseline/ceiling 两个公开合成 profile 均用现有 production Executor 构造初始 Agent、
  工具后 Agent、Evaluation 和 Evaluation repair 四阶段请求；
- 未来真实校准最多 8 calls、校准 output 64、observed tokens 64000、`$0.10`、零重试、
  首错停止，只保存安全 Usage/延迟/费用和 digest；
- V3 单例预算只由逐阶段最大真实 input 的 25% 工程余量、四次 1024 output ceiling 和
  固定向上舍入推导；25% 不是统计置信区间；
- 推导成本含历史协议后超过 `$0.10`、Agent 两调用在现有 30 秒 deadline 下不可达、
  calibration 不完整或请求超过 ceiling envelope 时停止，不创建 held-out；
- 校准输出不能用于 Prompt/RAG/Memory 调节或领域准入。新 V3 held-out 只能在校准结果、
  预算裁决和 exact-SHA CI 冻结后创建。

当前离线实现已完成：两个全新 development profile 会经现有 production Executor 形成
8 个四阶段请求，公开 snapshot 不含正文；Fake replay、首错停止、安全结果、预算公式和
no-I/O admission 已有测试。这里的 Fake Usage 不能成为真实预算或模型质量证据。
Provider/Key/网络调用和 V3 held-out 仍为 0；实现已由 `2d67696` / Actions
`31867655627` 公开验证。真实 development replay 仍需单独明确确认。

设计提交 `351c0e64adf9d2ace42c557d40fac81a44ab539e` 已通过 GitHub Actions run
`31866084382` 的 exact-SHA 公开 CI；公开冻结没有扩大真实调用权限。

### 真实 development Usage replay 入口裁决

用户已按 RQ-033 明确确认一次 DeepSeek V4 Pro 8-call development 校准。执行仍分两层：

- 既有 no-I/O admission 保持 `provider_construction_authorized=false`，不因确认而改义；
- 新 run admission 绑定同一冻结请求、code/public-CI、显式确认和受控结果路径后，才允许
  CLI 在结果独占预留之后读取 Key、构造 Provider；
- Fake simulation 与真实 result 使用不同合同，但共用 ledger/首错停止内核；真实记录
  保存实际计费调用数，禁止把 Fake 的 `external_provider_calls=0` 冒充真实 Usage；
- 真实响应正文、Prompt、reasoning、工具/RAG 内容、原始 request ID 和异常不落库；
- 只有 8/8 完整 Usage 才生成绑定结果 bytes SHA 的预算记录；stopped 结果保持不可变且
  不补跑，不创建预算或 V3 held-out。

入口本地聚焦 19、相邻 74、完整 606 tests 已通过，外部调用仍为 0。必须先提交、推送并
取得这条入口的 exact-SHA public CI，再在同一干净 SHA 上执行 prepare-only 和一次真实
回放；校准完成不等于领域质量或产品默认模型准入。

真实入口随后由 `6aa8c43` / Actions `31868747216` 公开验证；同 SHA prepare-only 没有
读取 Key 或创建结果。正式 replay 第 1 个请求没有形成规范化 `ChatResponse`，只保存了
宽泛的 `provider_response_invalid`，然后按首错停止跳过剩余 7 calls。该次请求可能计费，
但 Token/费用均 unknown；资源账本零值不得表述为实际零成本。

因此本次 calibration 裁决为 incomplete：不生成 V3 budget，不创建 held-out，不补跑，
模型质量仍 unknown。独立零调用 adjudication 绑定结果 bytes，显式记录 billable Usage
为 null、rerun false 和详细 Adapter code unavailable。公开归档完成后，下一步只能做
零调用的候选关闭/新版本诊断采用决策，不能直接扩大预算或发起新请求。

该结果与裁决现已通过 34 项聚焦测试、`611 passed, 103 subtests passed` 完整回归及
两套 RAG、compileall、Harness/security、dry-run、governance 和 diff 本地门禁；这些
验证没有再次调用 Provider。下一步仅为不可变证据的公开归档与 exact-SHA CI。

归档提交 `421a24393cafdc79a02de4091f569cfb9aa5b721` 随后通过 GitHub Actions run
`31869409106`。RQ-033 因而以“不完整证据已公开冻结”收口；下一检查点只允许零调用
决策，不能把归档成功解释为 calibration、领域能力或模型质量成功。

### DeepSeek calibration 失败采用裁决

ADR-0027 关闭当前 DeepSeek V3 资源校准与领域采用尝试。关闭的理由不是模型质量差，
而是当前不可变结果已经失去安全细分错误 provenance，继续建立真实诊断版本仍不能直接
产生领域质量证据，边际价值不足以支持围绕同一候选继续追绿。

DeepSeek Adapter 和真实 3/3 最小 structured/tool 协议证据继续保留；不生成 V3 budget、
不创建 V3 held-out、不补跑 V1/V2/calibration，也不准入产品默认模型、自动路由或
Flash/Pro 分层。模型领域质量保持 unknown。

未来任何真实 Provider 门必须先在离线 TDD 中建立双层安全失败记录：跨厂商稳定
`failure_code` 与 allowlisted 可空 `provider_error_code`；Prompt、response、reasoning、
SDK 异常、URL/header 和原始 request ID 均不得落盘。本批外部调用为 0；下一检查点按
ADR-0023 进入 G53-0 GLM-5.3 可用性与合同审计。

该关闭决策提交 `ea91e9697c820c0850db488a93263fc169719515` 已通过 GitHub Actions
run `31872476103` 的 exact-SHA 公共验证；CI 无 Key 或 Provider I/O。

### 5D-7：模型路线与安全错误 provenance 维护

GLM-5.3 普通 API 尚未正式可用，G53-0 暂缓；DeepSeek Pro 当前领域尝试保持关闭，
不因技术性失败立即切换 Flash。GLM-5.2 继续作为开发基线，但不被表述为已完成领域
质量准入。按照 ADR-0027，先实现并测试 allowlisted `provider_error_code` 在 Provider
Adapter、实验停止控制和 calibration adjudication 之间的安全传递；未知错误必须为
null，旧真实结果不改写。

该离线切片提交 `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a` 已通过 GitHub Actions
run `31874240935` 的 exact-SHA 公共验证；616 tests/103 subtests 和全部 CI 门禁通过，
无 Key 或 Provider I/O。
### 5D-7 收尾与领域模型未准入边界

ADR-0028 接受 5D-7 的评测与实验控制面已经完成，同时明确当前没有真实 Provider 获得
领域质量准入。通过的能力包括分层 Dataset/Candidate/Result、Prompt/Context 身份、
Evaluation 1.1 安全阻断、held-out 生命周期、资源门和安全错误 provenance；未通过的
能力仍包括真实模型完整近期复盘、真实注入两例、稳定 Token/成本/延迟和产品默认模型。

因此模型采用的 reject/unknown 不是阶段失败，也不能被改写为模型质量差。G53 保持
deferred 但不再阻塞 5D-7；Flash/Pro 分层继续受 ADR-0019 约束。下一检查点只进行
`5D-exit-review`，不读取 Key、不调用 Provider、不修改默认模型，也不提前实现 5E。

### 5D 退出审查与 5E 交接

5D 退出审查接受整个 Python 受限 Agent Loop 完成。入口设计的十项功能要求均有实现和
跨层测试证据：Router/Skill 身份与输入绑定、最小 Context、Manifest 权限与预算、实际
ToolResult 证据、Agent 草稿、唯一 ReviewHarness、Artifact 驱动 typed output，以及
非法结构化输出、越权、预算、上下文、Provider 和安全评测失败的 fail-closed 终态。

当前没有真实 Provider 获得 RiftCoach 领域质量准入，这仍是明确限制，但不阻塞 5D：
商业模型质量与受限执行控制面是两个独立验收对象，失败时 Harness 已证明不会把草稿
直接发布。5E 将在不调用 Provider、不切换模型的前提下，把已有 run_id、停止原因、
Tool record、Usage 和 terminal Artifact 统一为 `run/stream/event/trace/usage` 合同。

`SkillReviewExecutor.max_revisions` 继续作为 Harness 运行政策参数，而非 Manifest Agent
Loop budget；5E 必须记录实际 policy provenance。未来若要下沉为 Skill 合同，需要独立
ADR 和迁移，不能在退出审查中静默改变。

### 5E AgentRuntime V1 入口决策

ADR-0029 接受“薄 Runtime + 可选观察端口 + completeness-aware Usage + 原子最终 Trace”。
外层仅包装 `SkillReviewExecutor` 会让 `stream()` 退化为事后回放；事件溯源、DAG 或立即
采用 LangGraph/Pi/Claude Agent SDK 又会复制 ReviewHarness 并提前承担恢复和并发复杂度。

Runtime V1 复用 `SkillExecutionRequest`、Boundary、ContextBuilder、AgentLoop、ToolRuntime
和唯一 ReviewHarness。底层组件只发安全类型化 Signal，中央 Recorder 统一 sequence、
时间和 Event schema。同步 `run()` 与流式 `stream()` 必须复用一个执行核心；V1 stream
只是进程内运行状态事件流，不是模型逐 Token 输出，也不承诺 durable replay/cancel。

Runtime 状态与 Harness publication 状态分开；Trace 只保存版本、policy provenance、
安全事件、完整性明确的 Usage、终止原因和 Artifact 引用/哈希。已发送但未观察 Usage 的
Provider call 必须记为 partial/unknown 和 null，不能折算为零。5E 依次执行 5E-1 至
5E-4；当时唯一下一步为 5E-1 合同、Usage、Recorder 与 Trace Store 的纯本地 TDD。

### 5E-1 Runtime 合同与 Trace 存储实现决策

5E-1 使用严格冻结 Pydantic 合同和低依赖 Signal 模块；底层 Signal 只表达安全语义，
Recorder 才添加 run ID、全局 sequence、UTC 时间和 monotonic elapsed。Trace 在加载时
再次校验调用 start/close 配对、连续 ordinal、唯一终态和 Usage 一致性，不能只信任
Recorder 内存状态。

Runtime Usage 不修改旧 `TokenUsage(0, 0)` 的单响应语义，而是新增聚合完整性：无调用为
not_applicable，全部响应可观察为 complete，部分可观察为 partial，全部未知为 unknown。
partial/unknown 的精确总 Token 和成本均为 null；成本只有在完整性允许且注入版本化定价
Profile 时才计算。

最终 `runtime_trace.json` 使用共享安全 run ID、同目录临时文件、flush/fsync 与原子
replace，首个成功文件不可覆盖，读取时先校验 SHA-256。它仍只是最终快照，不提供事件
溯源、崩溃恢复或跨进程锁。实现提交 `d891184e1bf82068188d2fb5715769bdaa3da022`
已通过 GitHub Actions run `31942483874` 的 exact-SHA 公共 CI；5E-1 完成，下一步只进入
5E-2 observer 与同步 run 的入口审计/设计。

### 5E-2 Observable run 入口设计决策

ADR-0030 深化 ADR-0029：Provider 观察不能只放在 AgentLoop，因为 Harness 的 Evaluation、
repair 和 Revision 都会经 `ToolRuntime("llm.chat")` 调用模型。每次 Runtime run 将共享一个
`ObservedLLMProvider`，同时供 AgentLoop 与 Harness 使用；AgentLoop observer 只记录模型
主动请求且通过整批预检的业务 Tool 和 Agent 终态，ReviewHarness 只记录已经成功持久化的
transition、evaluation 和 publication。

5E-1 的 Event/Trace 新写入 schema 将显式升为 1.1，读端保留合法 1.0；修正真实零基
Evaluation attempt、冒号 section ID、可空 finish reason、Harness failure stage 和成功
ChatResponse Usage 合同。Zhipu 缺失 Usage 不再归零，而与 DeepSeek 一样安全失败为
`provider_usage_unavailable`。这只是一项离线合同修正，不改变历史模型实验结论。

Runtime terminal 采用 prepare → prospective Trace → atomic store → commit。只有 Trace
成功落盘后才公开 completed；Store 失败则返回 observability failure，保留已知 Harness
publication，不暴露 output 或 Trace reference。入口设计本身不等于 `run()` 已实现；下一步
只进入 5E-2 Task A 合同 1.1 与 observation port TDD。设计提交
`3c6f26a4802821548be8d61085552f5b9a790468` 已通过 Actions run `31944389807` 的
exact-SHA 公共验证；CI 没有 Key 或 Provider I/O。

### 5E-2 Task A 版本兼容与终态合同决策

Task A 实现确认：Signal 层只负责跨版本共同的安全形状，Event 层依据
`event_schema_version` 决定 1.0 兼容或 1.1 严格语义。这样旧 1.0 的安全厂商 finish
reason、无 Tool failure code 和空 publication digest 仍可读取，而 Recorder 默认创建的
1.1 Event 继续强制有限 finish reason、Tool 成败/错误码一致性和唯一报告摘要。

Runtime 1.1 的 Harness lifecycle 由 Recorder 在线记录与 Trace 离线复读共享；terminal
candidate 是绑定单个 Recorder 的一次性对象，提交前不可见，abort 后不能复用。若 Harness
已经持久化 terminal 状态，Runtime failure 必须保留该 publication truth，即使
`publication_decided` 尚未来得及观察。

该实现已通过 131 项聚焦、149 项相邻和 691 项完整测试及全部本地门禁；提交
`2e78c9606fe93b56657d4bb13c8efe0f1eed98fe` 又由 Actions run `31947625293` 完成
exact-SHA 公共验证。`ObservedLLMProvider`、AgentLoop/Harness 接线和统一 `run()`仍分别
属于后续 Task B-D，不因合同代码存在而提前完成。

### 5E-2 Task B Provider 与 AgentLoop 观察决策

Task B 采用 run-scoped `ObservedLLMProvider`，在 capability preflight 成功后、delegate
调用前后发出 Provider started/completed/failed；Agent、Evaluation、Evaluation repair 与
Revision 共用连续 ordinal。未知 finish reason 收敛为有限 `other`，失败只保存稳定
`provider_failed` 和 Adapter 允许列表内的可空安全 detail。

AgentLoop 只在整批工具数量、白名单和重复预检通过后记录业务 Tool，不全局观察
ToolRuntime，因此 Harness 内部 `llm.chat` 不会冒充 Skill 工具。每个正常返回的 Agent
结果恰好产生一个安全 terminal；observer 默认关闭时不构造 Signal，旧结果与调用保持
不变。`RuntimeObservationError` 必须穿透 ToolRuntime retry、breaker 与 fallback，避免把
观察故障误分类成业务依赖失败。本地 81 项聚焦和 721 项完整回归已通过；实现提交
`28bd910525a7522be16bd69b6e945846839a4cd8` 已由 Actions `31952026988` exact-SHA 公开
验证成功，Task B 正式闭环，Task C/D 未开始。

### 5E-2 Task C Harness/Executor 持久化后观察决策

Task C 将观察端口接入 `ReviewHarness` 和 `SkillReviewExecutor`，但不改变 Harness 的
评测、修订或发布权。Harness transition 只在目标 Manifest 成功写入并重新读取后观察；
Evaluation 只在结构校验通过、Evaluation Artifact 注册成功且真实字节重新校验后观察；
publication 只在 terminal Manifest 成功写入后观察。Evaluation attempt 直接使用 Manifest
的零基值，因此第一次和修订后的 Artifact 分别对应
`evaluation_attempt_0.json` 与 `evaluation_attempt_1.json`。

Runtime signal 只投影安全元数据：评测最多保存 `prompt_injection` blocking category，
publication 对 published/degraded 只保存经真实字节校验的 `final_report` SHA-256，rejected
不保存报告摘要。新增的 Artifact projection helper 会逐条调用 `FileRunStore.read_artifact`
并生成相对路径、Schema、SHA-256 和 producer 引用，绝不把 Artifact 正文复制进 Runtime。

`RuntimeObservationError` 在 Harness、Executor 和 Agent draft preparation 的宽泛异常捕获
前显式穿透；观察基础设施失败不能被误写成 `draft_preparation_failed`、普通 evaluation
失败或 deterministic fallback。`observer=None` 保留旧行为，不额外执行观察期的 Artifact
读取与投影。

Task C 本地聚焦 8 项、完整回归 `729 passed, 110 subtests passed` 和全部本地门禁通过；
提交 `8b69c9b` 已由 GitHub Actions run `31957712118` 对 exact SHA 公共验证成功。Task C
正式闭环，统一 `AgentRuntimeV1.run()` 仍留在下一步 Task D。

### 5E-2 Task D 统一同步 Runtime 本地实现决策

Task D 采用一个薄 `AgentRuntimeV1.run()` 入口和单一 `_execute()` 核心，继续复用既有
Boundary、ContextBuilder、AgentLoop、ToolRuntime、SkillReviewExecutor、ReviewHarness 与
两个文件 Store。`RuntimeExecutionFactory` 只做 run-scoped 依赖注入：Agent 只获得真实本地
`knowledge.search`，Harness 的 `llm.chat` 与 Agent 共用同一个 `ObservedLLMProvider`，因此
Agent、Evaluation 与 Revision 的 Provider ordinal 和 Usage 位于同一 Trace。

`RuntimeRunRequest` 在合同层只接受 selected Router 决策；Runtime 仍重新校验 Catalog
版本、typed input 与 Artifact commitment。Runtime policy 的 `max_revisions` 真实传入
Harness；event budget 按 Agent Provider/业务 Tool、Evaluation + 一次 repair、Revision、
`llm.chat` 最坏三次 retry、Harness transition、Publication 和 Runtime terminal 计算，当前
两个 Skill 在 `max_revisions=1` 时要求最少 61 个 Event slot，并在任何 Provider/Tool I/O
前拒绝不足预算。

成功终态继续采用 prepare → prospective Trace → atomic write → commit。Trace 写失败会
abort 候选 `run_completed`，随后只在内存提交
`run_failed(observability, trace_persistence_failed)`；Recorder/observer 失败返回安全
`observation_failed`、不暴露 output/Trace，并从已持久化 terminal Manifest 恢复已知
publication truth。Artifact reference 再次校验真实文件 bytes/SHA，Trace 不保存报告、
Prompt、Tool data、request/call ID 或异常正文。

本地测试覆盖 recent-form 与 single-match 两个真实 Skill、真实本地 RAG、published/
degraded/rejected、修订 0/1、Agent/Evaluation Provider failure、prompt-injection blocking、
Boundary/Context/typed-output/observation/Trace-store failure、精确事件交错、Usage 与 Artifact
SHA。新增 18 项，完整回归 `747 passed, 110 subtests passed`，两套 RAG、compileall、
Harness SDK/tracked-data boundary、dry-run、治理和 diff check 通过；本批 Key、真实 Provider
与 held-out I/O 为 0。Task D 实现提交 `d49508e` 已由 GitHub Actions run `31959646589`
exact-SHA 公共验证成功，5E-2 正式闭环；`stream()` 仍未实现，当前唯一下一检查点为
5E-3 入口审计/设计。

### 5E-3 `stream()` 入口审计与 Worker/Queue 设计决策

5E-3 审计确认：`AgentRuntimeV1._execute()` 已是唯一同步控制核心，`RuntimeRecorder` 在
真实 Agent、Tool、Harness 和终态控制流中追加安全事件，但当前没有对外交付层；最终 Trace
仍是原子最终快照，不能被当作实时回放。

本轮接受 ADR-0031：`run()` 与未来 `stream()` 共用
`_execute(request, event_sink)`；`stream()` 为每次运行创建进程内 worker 与有界
`queue.Queue`，普通事件在 Recorder 追加成功后投递，terminal 只在 prospective Trace 原子
写入并 commit 后投递，随后投递一个既有 `RuntimeRunResult`。队列满时阻塞保持顺序/完整性；
订阅者关闭只关闭 stream 交付，不取消业务执行，Runtime 继续形成最终 Trace。

直接 generator 因深层同步接缝侵入和消费者失败耦合拒绝；外部消息队列因提前引入 durable
event log、offset、跨进程恢复和运维复杂度拒绝。5E-3 实现阶段按设计文档完成了 TDD、parity、
背压、断开和终态失败测试；本轮没有 Provider/Key/模型/Prompt/RAG I/O。

本地实现已通过 15 项 stream 聚焦测试和 `762 passed, 110 subtests passed` 完整回归；提交
`80b76a1` 已推送，GitHub Actions run `31960987333` 对 exact SHA 的完整 pytest、两套 RAG、
compileall、治理、SDK boundary、secret/run-data boundary 和 Harness dry-run 全部成功，
5E-3 正式闭环。

### 5E-4 Runtime Evaluation & Exit Review 入口决策

按 RQ-038 进入 5E-4。该子阶段不是继续添加框架，而是对 5E-1 至 5E-3 做一次可追溯的
Runtime V1 退出审查：逐项复核合同、两个真实 Skill 的同步/流式纵向路径、success/degraded/
rejected/boundary/observability failure、event budget、Usage completeness、Trace 隐私、
Artifact SHA、背压/关闭和 exact-SHA 公共证据，并把“已实现”“已测试”“公开验证”“仍有限制”
分开记录。

5E-4 不读取 Key、不调用真实 Provider、不切换模型、不改 Prompt/RAG，不引入 LangGraph、
Pi/Claude Agent SDK、API、SSE、Memory、MCP、durable event log、cancel/resume 或 Multi-Agent。
只有退出矩阵和必要的最小修补全部通过，5E 才能关闭并进入 canonical 后续阶段。

5E-4 本地最终审查已经完成：exit matrix 将所有承诺映射到源码、直接测试、公共证据和限制；
Runtime 聚焦 `128 passed`，完整 `762 passed, 110 subtests passed`，compileall、RAG、治理和
差异检查通过，没有发现当前 V1 必须补的结构性代码缺口。退出决策为
`close-with-deferred-boundaries`；真实模型质量、API/SSE、持久恢复、Memory/MCP、SDK 采用和
生产 SLO 保持 deferred/unknown。该决策仍待 exact-SHA 公共 CI，成功前 5E-4 不关闭。

退出审查提交 `3d3656195a66adfd4595cffa145c978d24c33628` 随后由 GitHub Actions run
`31962252231` 完成 exact-SHA 公共验证。5E-4 与整个 5E 因此按
`close-with-deferred-boundaries` 正式关闭。按 RQ-039，canonical 只交接到
`5P-entry-design` 并暂停；本轮不开展 5P 设计或实现。

## 5P Prompt Program 与早期产品切片入口裁决（2026-08-17）

用户随后以 RQ-040 明确恢复 `5P-entry-design`。源码审计确认产品 Riot ID 输入不能直接传给
`AgentRuntimeV1`，而 production prompt identity 也尚未与真实 Context/Skill/Evaluation/
Revision 资产绑定。因此本次不把 5P 简化成“加 FastAPI”。

- ADR-0032 接受版本化 Prompt Program Manifest/Catalog/drift gate，复用现有
  PromptContextSnapshot component fingerprint；production Runtime 从验证后的 program 取得
  prompt profile identity；先只覆盖 recent-form 产品入口；
- ADR-0033 接受薄 FastAPI Adapter + `RecentReviewApplicationService` + 现有 Runtime/Harness；
  typed recent endpoint 不重新调用自由文本 Router，policy 由 Skill Manifest 同源投影；
- V1 端点为 recent POST、run GET、report GET 和 health；旧 status 因同步重复而不实现，
  follow-up 因需要 Session/Memory 推迟到阶段 6；
- 文件型 receipt 只是 body-free 查询投影；无 SQL、事务、恢复、多 worker 或公网安全承诺；
- 5P 固定为 5P-1 至 5P-6，entry design 通过公开验证后只进入 5P-1；本设计没有产品代码、
  FastAPI 依赖、Key、Riot/Provider/held-out I/O，当前仍无领域 Provider 准入。

入口设计提交 `49841ec44832875e65b17770557415113e67b1db` 随后由 GitHub Actions run
`31985199623` 完成 exact-SHA 公共验证。5P entry design 正式完成，canonical 只切换到
`5P-1-product-contract-compiler` 准备状态；按 RQ-040 不在本轮自动实现。

## 5P-1 Product Contract Compiler 本地裁决（2026-08-17）

5P-1 采用单一 `app.product` 编译边界，而不是让未来 HTTP handler 填写 Runtime 内部合同。
产品 DTO 只允许 Riot ID、count、queue、focus；Riot ID 使用最后一个 `#` 拆分和宽松的本地
传输安全上限，不冒充 Riot 账号规则的完整副本。

typed recent 入口不会重新调用自然语言 Router：它从 strict Catalog 读取
`recent-form-review` 当前 name/version，以 `entrypoint:reviews.recent` 形成合法 selected
evidence。Skill Manifest 决定业务预算和质量门，服务器 V1 固定 policy version、event budget
和 revision 上限；客户端不能覆盖。Summary/report 使用既有 Harness 编码与 SHA-256 绑定，
Runtime 前仍由 `SkillExecutionBoundary` 重算并检查 Catalog/version/content 漂移。

本地产品/相邻/跨层/完整回归及两套 RAG、编译、安全、dry-run、治理门禁已通过；本批没有
Key、Riot/Provider/held-out I/O。该结果不表示 Prompt Program、Application Service、FastAPI 或
真实 Coach 质量完成。

提交 `57bd36adcd289b7cc51c1c430e04398daf0683f3` 的 Actions run `31987501935` 已完成 exact-SHA
公共验证。5P-1 正式关闭，canonical 唯一下一检查点为 `5P-2-prompt-program-runtime-composition`，
按 RQ-041 等待用户再次继续。

## 5P-2 Prompt Program V1 与 Runtime Composition 本地裁决（2026-08-17）

用户按 RQ-042 明确继续后，本轮接受并实现 ADR-0032 的最小产品组合边界：

- `PromptProgramManifest` 是 Skill、Context、knowledge tool、Evaluation 1.1 与 Revision 资产的
  组合身份；它只存 program/contract 元数据和复用既有 `PromptContextSnapshot` probe 的组件摘要，
  不存 Prompt 正文，也不把实验 case-context snapshot 冒充产品 Program；
- `PromptProgramCatalog` 严格读取 JSON manifest，要求自身 SHA-256、唯一组件 ID、secure
  `coach_evaluation@1.1.0` 和 `extra=forbid` 合同；任何坏包或不安全 Evaluation 版本立即拒绝；
- `PromptProgramResolver` 在组合和 Runtime identity 解析时重新加载当前 Skill，并重算组件指纹；
  Skill/version、Context contract、Evaluation contract 或任何组件摘要漂移均 fail closed；
- `RuntimeCompositionRoot` 是产品启动装配边界，先 `verify_all()` 再允许 Runtime 构造；
  `AgentRuntimeV1` 从 verified resolver 取得 `prompt_profile_id/version`，不再硬编码
  `<skill>-coach@1.0.0`；
- 旧 direct Runtime 单测显式注入 `LegacyRuntimeIdentityResolver`，这是兼容合同，不是产品准入或
  Prompt Program 证据。

本地证据：Prompt Program/Runtime/identity/产品编译相邻聚焦 `142 passed`，完整回归
`805 passed, 110 subtests passed`；两套 RAG、compileall、Harness dry-run、secret/tracked-data、
governance 和 diff check 全部通过。本批 Key/Riot/Provider/held-out I/O 为 0；这只证明组合与漂移
控制，不证明真实模型 Coach 质量，也不提前完成 FastAPI/Application Service。最终状态仍需提交、
推送和 exact-SHA 公共 CI 后关闭 5P-2。

实现提交最终 exact SHA `0a9651f4e305616626c58ea28e2c300a491f2a3b` 已由 GitHub Actions
run `31988837293` 完成公开验证；5P-2 正式关闭。canonical 只交接到
`5P-3-domain-application-service` 准备状态，不自动实现 Application Service 或 FastAPI。

## 5P-3 Domain/Application Service 本地裁决（2026-08-17）

5P-3 采用模块化单体中的明确三层，而不是让未来 HTTP handler 串 CLI：`app.lol` 负责
Summary 与确定性报告领域逻辑，`app.product` 负责一次近期复盘用例的顺序和安全错误，
`app.runtime` 继续独占 Agent/Harness/Trace/发布。CLI 已改为复用 app-level domain functions，
同一 fixture 的报告保持逐字节一致。

Application Service 只在 Summary Schema 合法且至少一场比赛计入汇总后调用 compiler，因此
上游、零比赛和 renderer 失败不会生成 run_id。Runtime 一旦被调用，结果还要交叉核对服务器
run_id、publication、typed output status 和 Trace reference；失败或不一致只返回 body-free
`review_runtime_failed`。上游异常统一映射 allowlisted code，只有受控 Retry-After、run_id 与
terminal reason 可进入公开错误对象。

5P-2 的 Prompt Program 漂移门证明了声明身份，但原 composition 允许任意 factory。本轮新增
secure product 默认 factory，实际构造 `SecureChatEvaluationAdapter`、`ChatCoachReviser` 和
revision validator；测试专用 factory 仍须显式注入。该深化补充首个消费者证据，不改写
5P-2 已经公开的历史结论。

本地证据为 Domain 7、Application 20、Prompt Program 10、相邻 263、完整
`830 passed, 110 subtests passed`，两套 RAG 与全部门禁通过。本批外部 I/O 为 0，尚不证明真实
Riot/Provider 质量、HTTP、receipt、幂等、事务、并发或恢复；5P-3 仍待 exact-SHA 公共 CI。

实现提交 `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 随后由 GitHub Actions run
`31998739178` 完成 exact-SHA 公共验证，5P-3 正式关闭。canonical 只交接到
`5P-4-file-backed-run-receipt-query`，本轮不实现 receipt/query 或 FastAPI。

## 5P-4 File-backed Run Receipt/Query 裁决（2026-08-17）

5P-4 不创建第二份报告数据库，而是在现有三个证据源上增加安全查询索引：receipt 保存
Runtime terminal 的 body-free 摘要，Trace 保存运行身份/Usage/Artifact 引用，manifest 保存
Harness publication/Artifact 账本，final Artifact 保存唯一正文。查询必须把四者重新交叉校验，
不能按 run_id 直接拼路径读 Markdown。

采用严格 `ApiRunReceipt` 与原子 create-if-absent `FileRunReceiptStore`；completed 必须有 Trace，
rejected/无 Trace 不得声明报告可用。`RunQueryService` 将 overall Runtime terminal 与 Harness
publication terminal 分开核对，再要求 Trace/manifest 中唯一 final report identity 一致，并对
真实字节重算 SHA-256、验证 UTF-8 与非空。公开错误只允许 `run_not_found`、
`report_not_available`、`run_integrity_failed`，RunView 不暴露 Provider、路径、Prompt、Tool、
异常或正文。

Application Service 新增必需的 `RunReceiptWriter` 端口；类型化 completed/failed Runtime result
在对外返回或抛安全错误前写 receipt，错误 run_id、未类型化异常和前置上游失败不伪造 receipt。
本地聚焦 50、相邻 `179 passed, 12 subtests passed`、完整 `860 passed, 110 subtests passed`，
两套 RAG 与全部门禁通过，外部 I/O 为 0。实现提交
`932a863120a4561f58c477a69becbccd2ec9ff45` 已由 Actions run `32002994441` 完成 exact-SHA
公共验证，5P-4 正式关闭并只交接到尚未开始的 5P-5。这不等于 FastAPI、SQL 事务、崩溃恢复、
本机恶意写防护或生产部署已经完成。

## 5P-5 Thin FastAPI Adapter 本地裁决（2026-08-17）

用户按 RQ-045 明确恢复 5P-5。采用显式依赖注入的 `create_app(review_service, query_service)`，
FastAPI 只负责 HTTP 请求/响应、OpenAPI、状态码和 allowlisted 错误；它不导入 CLI，不选择
Skill，不拼 Prompt/Runtime policy，不调用 Provider/Harness，也不读取 API Key。固定端点只有
`POST /reviews/recent`、`GET /runs/{run_id}`、`GET /runs/{run_id}/report` 和 `GET /health`；
status、follow-up、SSE/事件流、单局入口和后台任务均不在本轮。

本轮加入 `fastapi>=0.115,<1` 与 dev `httpx>=0.27,<1`。HTTP 错误只投影固定 code，可带安全
run_id/terminal reason，429 的有限 Retry-After 只放入 header；查询完整性继续由
`RunQueryService` 负责。真实本地纵向测试经过 Catalog、Prompt Program、AgentRuntime、真实
本地 RAG、唯一 ReviewHarness、Fake Provider、receipt/Trace/Artifact 和 Query Service；外部
Provider/Key/Riot/网络/held-out I/O 均为 0。

本地 API 聚焦 24 项，完整回归 `884 passed, 1 warning, 110 subtests passed`；warning 是
FastAPI 0.141.1 TestClient 对 httpx 的上游迁移提示，不改变本轮合同。5P-5 当前本地完成，
尚待提交、推送与 exact-SHA 公共 CI；这不表示真实模型质量、SQL/恢复、鉴权、前端或公网部署完成。

提交 `6d1e5b0af186f523bee35c24c6873578a149b824` 随后由 GitHub Actions run `32005648179`
完成 exact-SHA 公共验证，5P-5 正式关闭。canonical 只交接到
`5P-6-product-slice-evaluation-exit-review`，等待用户明确继续；本轮不自动开展退出审查、5F
或阶段 6。

## 5P-6 Product Slice 本地退出裁决（2026-08-17）

用户按 RQ-046 恢复 5P-6。审查没有用“完整 pytest 很多”替代设计对账，而是把 5P 总设计的
十项功能要求、五层控制权、NFR/安全/no-I/O 与 deferred/unknown 能力逐项映射到源码、直接测试
和 5P-1 至 5P-5 的 exact-SHA Actions。

审查确认 HTTP 只适配协议，Application Service 拥有一次产品用例顺序，Domain 只处理 LoL
事实，typed compiler/Prompt Program 负责可信身份与 policy，AgentRuntime/Harness 负责执行和
唯一发布，Query Service 重新核对 receipt/Trace/manifest/final Artifact。没有发现需要留在 5P
修补的结构性产品代码缺口。

本地裁决为 `close-with-deferred-boundaries`：当前只证明 Fake/fixture 驱动的本地同步产品纵切面，
不证明真实 Riot/模型 Coach 质量、SQL/事务/恢复、Session/Memory、鉴权/限流/CORS、SSE、正式
前端、公网部署或生产性能。EchoMind/Saber/Sea、LangGraph、MCP、Multi-Agent 与 Pi/Claude SDK
仍受各自采用门约束，不因 5P 退出而自动接入。

本地聚焦 `121 passed, 1 warning`、相邻 `166 passed`、完整
`884 passed, 1 warning, 110 subtests passed`，两套 RAG 与全部门禁通过，外部 I/O 为 0。
5P-6 在本退出审查提交获得 exact-SHA 公共 CI 前仍为 in progress；成功后才正式关闭 5P，并只
交接到 `5F-entry-design`，不自动实施第三方 Runtime 对照。

## 5P-6 exact-SHA 公共闭环与 5F 交接（2026-08-17）

退出审查提交 `8c8acc6911209e645cfaee18bd40870f78d8704f` 已由 GitHub Actions run `32010604551`
完成 exact-SHA 公共验证；pytest、RAG、compileall、治理、SDK/tracked-data boundary 与 Harness
dry-run 全部成功。5P-6 与整个 5P 正式关闭，裁决保持 `close-with-deferred-boundaries`。

canonical 只交接到 `5F-entry-design` 准备状态。5F 仍是一个独立的 Runtime 采用实验设计门：
后续将用同一受限产品切片审计自建 Runtime 与 Pi/Claude Agent SDK 的语义覆盖、迁移成本、可观测性、
失败安全、延迟/成本和停止条件；在用户再次明确继续前不接入 SDK、不切换 Runtime、不调用真实
Provider，也不进入阶段 6。

## 5F Pi-only Runtime 采用实验入口裁决（2026-08-17）

用户确认将 5F 的第三方 Runtime 候选从 Pi/Claude Agent SDK 并列收缩为 `Pi-only`。这不是宣布
采用 Pi，而是冻结一个可归因的实验问题：在同一个 `recent-form-review` 切片、同一个 Tool、同一个
ReviewHarness 和同一套 Trace/Usage 合同下，比较自建 Python AgentLoop 与官方 Pi Agent Core。

Claude Agent SDK 只保留书面替代分析，不进入代码级对照。原因不是简单判断其能力不足，而是它会
同时带来 Claude 模型、Claude Code 风格的工具/Session/权限/Harness 语义，无法在当前阶段隔离
Runtime 变量。Pi 的官方核心为 TypeScript，跨语言或 sidecar 成本必须进入一等评测；不采用未经审计
的 Python 移植版。

5F 入口设计只冻结 ADR、官方源码/许可证审计、无 I/O scripted protocol spike、合同/安全/Trace/
Harness 指标、成本和 adopt/partial-adopt/reject 门槛；不安装 Pi、不修改主 Runtime、不读取 Key、
不调用真实 Provider。详细设计见 `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`
与 ADR-0034。

5F-entry-design 提交 `ce979752808271696b1dfe499317ead66de6aacb` 已由 GitHub Actions run
`32013948784` 完成 exact-SHA 公共验证；入口设计正式关闭。canonical 只交接到
`5F-1-pi-source-license-contract-audit` 准备状态，等待用户再次明确继续；本轮不自动安装 Pi、
读取 Key、调用 Provider 或实现 adapter。

## 5F-1 官方 Pi 审计裁决（2026-08-17）

用户按 RQ-048 恢复 5F-1 后，官方身份已从历史 `badlogic/pi-mono` 迁移信息校正为
`earendil-works/pi`，实验候选冻结在 release `v0.84.2` / commit
`914cf1472e715297caa30db4b9535d534a9eb718`。`pi-agent-core` 与 `pi-ai` 均为 MIT、Node
`>=22.19.0`；本机 Node 版本满足要求。许可证不阻断隔离实验。

本地裁决为“允许有条件进入 5F-2”，不是采用 Pi。5F-2 只允许低层 `Agent`、Scripted StreamFn、
一个 `knowledge.search` Tool、显式 sequential、版本化限长 JSONL 与 Python 父进程 deadline/kill；
不得使用 Coding Agent 默认文件/命令工具、ResourceLoader、Extensions、Session/Auth/ModelRuntime。

整批 Tool 原子预检、duplicate/调用/Context 预算、Usage completeness、安全 event projection、
Runtime Trace 与 ReviewHarness 发布权继续由 RiftCoach adapter/外层强制。任一强制项无法保持，
5F 应给出 `partial-adopt` 或 `reject`，不能扩大 Pi 权限补救。完整证据见
`docs/plans/2026-08-17-5f1-pi-source-license-contract-audit.md`。

审计提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 已由 Actions run `32016852979`
完成 exact-SHA 公共验证，5F-1 正式关闭。canonical 只交接到 5F-2 准备状态；本次关闭没有
安装 Pi、创建 sidecar/lockfile、实现 adapter、读取 Key 或调用 Provider。

## 5F-2 sidecar 实验设计（2026-08-17）

用户按 RQ-049 恢复 5F-2。ADR-0035 选择低层 Agent Core + 版本化限长 JSONL sidecar：Python
父进程保留真实 ToolRuntime、总 deadline 和子进程生命周期；Node 每 run 创建一个 Pi Agent，只
注入 Scripted StreamFn 和 `knowledge.search` proxy。产品迁入 Node 与完整 Pi Coding Agent RPC
均因改变变量过多而拒绝。

5F-2 只产生协议与控制流证据；ReviewHarness/Trace 合同对照属于 5F-3，采用裁决属于 5F-5。在
设计冻结时尚未安装依赖、实现 adapter、读取 Key 或调用 Provider/Riot。

## 5F-2 本地实现与退出裁决（2026-08-17）

exact npm lockfile、官方 Pi Agent Core 0.84.2 sidecar、Python controller、版本化限长 JSONL、
真实本地 `knowledge.search`、整批 Tool 预检、Usage 四态、credential-free child environment、
deadline/terminate/kill 和 body-free event 已本地实现。Scripted StreamFn 是唯一 Provider 接缝，
真实 Provider/Riot/Key 调用为 0。

实现过程中修复了 strict Pydantic JSON 解码、stderr/EOF reader 竞态、最后迭代 Tool 零副作用、
失败 Tool 预算计数和 Tool contract drift 的稳定失败边界。35 项 Pi 聚焦、99 项相邻与完整
`919 passed, 1 warning, 110 subtests passed` 通过；两套 RAG、compileall、Harness/secret、
dry-run、Node tree、治理和 diff 门禁通过。

本地裁决为 `pass-with-boundaries`：只准许在 exact-SHA 公共 CI 成功后进入 5F-3 准备状态，不采用
Pi、不接主 Runtime/Harness。当前安装树 94 packages / 62,364,713 bytes，每 run 新进程本机量级约
0.4 秒；完整 Harness/Trace/structured-output parity、真实 Provider 和维护收益仍未证明。

实现提交 `f62f078faca0d93494478011d2fe18cdeb85970f` 已由 GitHub Actions run `32022258177` 完成
exact-SHA 公共验证；5F-2 正式关闭，唯一下一检查点为
`5F-3-contract-security-harness-evaluation` 准备状态，等待用户明确继续。该交接不授权自动实现
5F-3、读取 Key、调用 Provider 或接入主 Runtime。
## 5F-3 合同、安全与 Harness 本地裁决（2026-08-17）

用户按 RQ-050 恢复 5F-3。ADR-0036 选择评测专用 Pi→Harness adapter 和严格 Runtime Signal
projector，不把 Pi 接入主 `AgentRuntimeV1`、FastAPI 或默认 composition。

真实 no-I/O 纵向证据证明：Pi draft/实际 Tool evidence 可以经过原 `SkillReviewExecutor` 和唯一
`ReviewHarness`，passing 后形成 typed output 与 SHA 校验 Artifact；成功 per-call Usage/event 也能
组成合法 body-free RuntimeTrace。坏 citation、失败 Tool、process failure 和 missing Usage 均不能
发布 Pi draft。

但 Context token-unit 与 sidecar char guard 不等价；Pi 的 provider_aborted/protocol/process 等
terminal 无法无损进入现有 Runtime Agent terminal；事件只能在 child 完成后批量投影，缺少真实
live timing/stream。再加 94 packages、约 62 MB 安装树和本机约 0.4 秒每 run 新进程，局部采用没有
显示维护收益。

本地裁决为 `harness-compatible-but-runtime-gate-failed`，不准入 5F-4 真实 Provider slice。该结果
不评价模型质量，也不提前决定 5F-5 的 partial-adopt/reject；公共 CI 成功前 5F-3 仍未正式关闭。
聚焦 45、相邻 196、完整 `929 passed, 1 warning, 110 subtests passed`，外部 I/O 为 0。

实现/退出提交 `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已由 Actions run `32025522606`
完成 exact-SHA 公共验证，5F-3 正式关闭。5F-4 按既定条件分支未进入；canonical 只交接到 5F-5
准备状态，最终 partial-adopt/reject 仍等待单独裁决。

## 5F-5 Pi 最终采用与资产生命周期本地裁决（2026-08-17）

用户按 RQ-051 恢复 5F-5。ADR-0037、最终 exit matrix 与面向初学者的 5F 总退出审查已区分
三个不同问题：产品 Runtime 是否使用 Pi、仓库是否保留可执行实验、哪些工程方法值得吸收。

本地裁决为 `partial-adopt-evaluation-assets-only`：

- 产品明确拒绝 Pi，Python `AgentRuntimeV1` 继续是唯一默认 Runtime；Pi 不进入 FastAPI、
  Application Service、composition、生产依赖、部署或阶段 6；
- `experiments/pi_runtime/`、`app/evaluation/pi_runtime/`、测试、exact lockfile 和当前 CI 复现能力
  冻结保留，只作评测证据，不随业务功能追随扩展；
- 吸收版本化严格协议、fail-closed projection、硬采用门和无信息增益停止方法，不迁移第二套 Runtime；
- 高危实际依赖、Node 不兼容、持续 CI 不稳定/成本显著或大规模追随维护会触发新 ADR，优先归档实验，
  不得反向放宽产品合同。

当前 5F-5 仍在进行中：Pi 聚焦 `45 passed`，完整
`929 passed, 1 warning, 110 subtests passed`，两套 RAG、Node tree、compileall、governance、
Harness dry-run、安全边界和 diff check 均已通过；尚待提交、推送和 exact-SHA 公共 CI。成功前不把
整个 5F 标为完成，也不进入 `6A-entry-design`。

## 5F-5 exact-SHA 公共闭环与阶段 6 交接（2026-08-17）

最终采用/退出提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已由 GitHub Actions run
`32028206103` 完成 exact-SHA 公共验证；Node 24、`npm ci --ignore-scripts`、完整 pytest、两套
RAG、compileall、governance、安全边界和 Harness dry-run 全部成功。

5F-5 与整个阶段 5 正式关闭，裁决保持 `partial-adopt-evaluation-assets-only`。产品唯一 Runtime
仍为 Python `AgentRuntimeV1`，Pi 只保留为冻结的 evaluation-only 资产。canonical 只交接到既有
路线中的 `6A-entry-design` 准备状态；该历史交接当时没有实现阶段 6 的 SQL、Session、Memory、SSE、
鉴权、前端、真实 Provider 或部署。随后用户恢复 6A，当前已确认 PostgreSQL/polling worker、总体
架构与 task schema/状态机，仍未实现产品代码。

## 6A PostgreSQL 持久任务入口设计裁决（2026-08-17）

用户逐节确认 ADR-0038：PostgreSQL 是唯一生产语义基线，使用同步 SQLAlchemy 2、Alembic 与
psycopg；FastAPI 和独立 polling Worker 保持同仓库同部署，不引入 Redis/Celery/Kafka。任务在入队
时预留 task_id/run_id，采用 owner-scoped idempotency 与 queued/running/succeeded/failed 不可逆
状态机；执行/发布状态分离，长 Agent 运行不持有 SQL transaction。

SQL 保存 durable task 控制面，Artifact/Trace 保存运行正文与证据。已有 immutable receipt 时允许
reconciliation；无终态证据的 hard crash 不自动判死或重跑，需受限人工确认。lease/heartbeat/
fencing/cancel/resume 留阶段 8。

作品集 NFR、安全/数据生命周期和真 PostgreSQL 测试矩阵已冻结，6A 实施顺序为 6A-1 至 6A-7。
详细设计与计划见：

- `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-design.md`
- `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-implementation.md`

SQL 产品代码、Session、Memory、SSE、正式 Auth、前端、外部 Provider/Riot I/O 和公网部署均未实现。
本地完整回归 `929 passed, 1 warning, 110 subtests passed`，两套 RAG、compileall、Harness dry-run、
governance 与安全边界通过；设计提交 `c0b5af0eec1654c35afddb3c8a66b774a233a688` 又由 Actions run
`32041343696` 完成 exact-SHA 公共验证。`6A-entry-design` 正式关闭，只交接
`6A-1-postgresql-foundation` 准备状态。

## 6A-1 PostgreSQL Foundation 本地实施裁决（2026-08-17）

用户按 RQ-053 启动 6A-1。本批采用 SQLAlchemy 2.0、Alembic 1.x 与 psycopg 3，同步 Engine/Session
保持与现有同步 Runtime/未来 polling Worker 一致。配置只接受 `postgresql+psycopg`，缺 URL、错误方言
和非法 pool 参数安全失败；Engine 构造保持惰性，不在 import/config 测试中连接数据库。

`review_tasks` initial migration 只建立 durable task 控制面：UUID task identity、唯一 run identity、
owner/idempotency、规范化 JSONB 请求、四态与 lifecycle/timestamp CHECK、worker/terminal/publication 和
body-free evidence references。Prompt、报告、Provider/Tool body 与异常栈不进入 row。Repository、claim、
Worker 与 API 行为仍属于后续 6A 子阶段。

本地配置/metadata/deployment 合同 `19 passed`；真实 PostgreSQL migration/constraint 三项因本机无
Docker/测试 DB 明确 skipped。完整回归 `948 passed, 3 skipped, 1 warning, 110 subtests passed`，两套
RAG、compileall、Harness dry-run、governance 与安全边界通过。Alembic offline PostgreSQL SQL 编译只
证明 DDL 可生成，不替代真库执行；因此本地裁决为“实现完成、等待 public PostgreSQL CI”，6A-1 仍未关闭。

实现提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 随后由 GitHub Actions run
`32043214500` 完成 exact-SHA 公共验证；原 `pytest` 与新增 `postgres-migrations` job 均成功。真实
PostgreSQL 17 已验证可逆 migration、JSONB/timestamptz/CHECK round-trip 与 metadata 无漂移，故 6A-1
正式关闭。唯一交接为 6A-2 Task Contract/Repository 准备状态，不自动开始实现。

## 6A-2 Task Contract & Repository 本地实施裁决（2026-08-18）

用户按 RQ-054 恢复 6A-2。本批固定 Provider-neutral `TaskStatus` 四态、严格 Product Request、
canonical JSON/SHA-256 fingerprint、owner-scoped body-free view、owner/global active capacity 和
idempotency replay/conflict 语义。Service 负责业务错误投影，Repository 负责 PostgreSQL 单事务原子
create/replay/conflict/capacity/query；不实现 claim、Worker、Application/Artifact 或 HTTP。

为避免并发 `COUNT → INSERT` 超额，Repository 在 create 短事务内使用固定 transaction-scoped PostgreSQL
advisory lock；锁不跨越 Agent/Provider 执行，也不替代 6A-3 claim 或 6A-6 capacity 压测。数据库错误只
输出 allowlisted safe code，公共 view 不含 owner、幂等 key、请求正文、worker 或证据正文。

本地 domain/service 聚焦 `29 passed`，完整回归 `977 passed, 8 skipped, 1 warning, 110 subtests
passed`；真库 5 项 Repository 测试尚待 public CI，因此 6A-2 尚未关闭。

提交 `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 随后由 GitHub Actions run `32046532695` 完成
exact-SHA 公共验证；`pytest` 与 `postgres-migrations` 均成功，真实 PostgreSQL 通过全部 5 项
Repository 测试。因此 6A-2 正式关闭，唯一交接为 6A-3 Atomic Claim/Worker 准备状态，不自动开始。

## 6A-3 Atomic Claim & Polling Worker 本地实施裁决（2026-08-18）

用户按 RQ-055 再次明确“继续下一轮”，本批只实现 durable task 的搬运控制流，不接真实
`RecentReviewApplicationService`、Artifact/Trace reconciliation、FastAPI、Session/Memory 或外部
Provider/Riot。Repository 新增短事务 `FOR UPDATE SKIP LOCKED` claim，并按
`created_at ASC, task_id ASC` 保持确定性顺序；claim 返回前提交 `queued → running`，所以 Worker
在事务外执行，不持有数据库行锁。

Worker 的终态通过 `task_id + status=running + worker_id` 条件更新实现 CAS。Executor 异常只投影固定
安全原因 `worker_execution_failed`；影响行数为 0 时返回 `ownership_lost`，不自动重试或覆盖迟到结果。
空队列使用有上限的指数退避和受控 jitter，停止信号会结束空闲轮询并在同步执行完成后再领取新任务。
由于 6A-4 尚未接入真实 Application/Artifact Executor，`scripts/run_review_worker.py` 当前故意
fail-closed，不允许直接领取生产任务。

本地聚焦回归为 `30 passed, 7 skipped`（7 项真实 PostgreSQL claim 测试因本机无 DB 明确 skip），
完整回归为 `1008 passed, 15 skipped, 1 warning, 110 subtests passed`；两套 RAG、compileall、Harness
dry-run、governance、秘密/SDK/YAML/diff 门均通过。当前裁决为“本地实现完成，等待 exact-SHA 公共
PostgreSQL CI”；CI 成功前不关闭 6A-3，不进入 6A-4。

提交 `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 随后由 GitHub Actions run `32097561436` 完成
exact-SHA 公共验证；`pytest` 与 `postgres-migrations` 均成功，真实 PostgreSQL 17 补齐 7 项 claim
测试。因此 6A-3 正式关闭，canonical 只交接 `6A-4-application-artifact-integration` 准备状态，
等待用户明确继续。6A-4 才会把预留 `run_id` 接入 Application/Runtime/Artifact，并处理 receipt-proven
terminal/reconciliation；本轮没有提前实现这些能力。

## 6A-4 Application & Artifact Integration 本地实施裁决（2026-08-18）

用户按 RQ-056 恢复 6A-4。SQL 预留 `run_id` 现通过 trusted keyword-only 接缝贯穿 Product compiler、
Application、Runtime input/result、Trace、Artifact 与 immutable receipt；显式 run ID 不会回退随机生成，
任何 task/result/receipt/reference 身份漂移都会 fail closed。

Task success 不再只含 publication 三字段，而必须携带严格 Trace/receipt/final Artifact body-free reference
与 SHA；Repository CAS 同时匹配 task、running、worker 与 run。Application completed 终态必须先形成合法
typed result 才写 completed receipt，避免非法 receipt 被 reconciler 误收。published、degraded、rejected
都是合法运行完成并映射 SQL succeeded，系统未形成合法终态才映射 failed。

reconciler 只将完整、不可变、跨 receipt/Trace/manifest/Artifact/SHA 验证通过的 completed receipt 补齐为
succeeded。无 receipt、坏 receipt 或 failed receipt 都只形成 `recovery_required` 运维投影，不自动 fail、
requeue 或重跑。人工恢复必须二次确认同一 worker，并通过 running+worker CAS 写
`worker_confirmed_dead`；终态后旧 Worker 无法覆盖。

本地聚焦 `130 passed, 12 skipped`，完整
`1033 passed, 20 skipped, 1 warning, 110 subtests passed`，两套 RAG 和全部横向门禁通过；新增 5 个
PostgreSQL reconciliation/离线产品纵向测试因本机无 DB 明确 skipped。当前裁决为“本地实现完成，等待
exact-SHA 公共 PostgreSQL CI”；成功前 6A-4 不关闭，不进入 6A-5。Worker 环境组合 CLI 继续
fail-closed，留给 6A-5 production-like composition/lifecycle。

## 6A-4 exact-SHA 公共闭环与 6A-5 交接（2026-08-18）

提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 已推送；GitHub Actions run `32102522662`
的 `pytest` 与 `postgres-migrations` 两个 job 均 completed/success。公开完整 pytest 为
`1033 passed, 20 skipped, 1 warning, 110 subtests passed`；PostgreSQL 17 job 明确执行
`tests/test_database_config.py`、migration、repository、claim、`test_task_reconciliation_postgres.py`
与 `test_task_product_vertical_postgres.py`，共 `40 passed`。

这确认 6A-4 的生产语义不是只在 Fake 测试中成立：真实数据库验证了完整 receipt 对账成功、无 receipt
保持 `running/recovery_required`、人工 recovery CAS 阻断迟到 Worker，以及 PostgreSQL + 现有
Application/Runtime/RAG/Harness/Artifact 的离线纵向接线。CI 没有读取 Key 或调用 Riot/Provider。

因此 6A-4 正式关闭，canonical 只交接 `6A-5-async-fastapi-composition` 准备状态。下一批才会
讨论并实现异步 FastAPI 202 合同、ActorContext、lifespan、task/run/report query 与 health；当前
不得把 6A-4 的公共闭环描述成完整 Web 产品、自动 crash recovery、Session/Memory 或公网部署。

## 6A-5 Async FastAPI & Composition 本地实施裁决（2026-08-18）

用户按 RQ-057 恢复 6A-5。HTTP 合同已版本化为 V2：POST 只在 PostgreSQL 短事务提交 queued task 并
返回 202 task/run/links，不再同步执行 Agent 或返回报告正文；幂等 replay、请求冲突、不可用和容量错误
均有独立安全投影。task/run/report 查询先通过 trusted ActorContext 做 owner-scoped SQL lookup，只有
succeeded task 才读取严格 receipt/Trace/Artifact；queued/running 为 409，SQL 与文件证据不一致为 500。

固定 owner 只允许显式 local/test profile；production 无 Auth Provider 时 liveness 仍可用于进程管理，
但 readiness 与产品请求 fail closed。composition import/OpenAPI 零 I/O，lifespan 才创建并关闭 Engine/
Session factory；readiness 同时检查 `SELECT 1` 和 Alembic current/head，未采用 async ORM，因为没有同步
数据库成为瓶颈的实测证据。

API 聚焦 `38 passed, 1 skipped`，完整本地回归
`1047 passed, 21 skipped, 1 warning, 110 subtests passed`，两套 RAG 与全部横向门禁通过。新增真库 API
测试已加入 PostgreSQL 阻塞 job，本机无 DB 因而明确 skip；成功前 6A-5 保持执行中。

范围复核同时更正 6A-4 的笼统交接表述：本批正式文件/HTTP目标关闭的是 API process composition；真实
Riot/Data Dragon/Provider Worker executable composition 必须在 6A-7 `API+Worker+PostgreSQL` packaging
中完成。当前 Worker CLI 继续 fail-closed，不能把“API 能可靠入队”描述成“部署后任务已会自动消费”。

提交 `2492951c20dd6ca897d957d03752b6a2585ce469` 随后由 GitHub Actions run `32106378542`
完成 exact-SHA 公共验证：普通 pytest 为 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`，
PostgreSQL 17 job 明确运行新增 API 真库测试并得到 `41 passed, 1 warning`。因此 6A-5 正式关闭，
canonical 只交接 `6A-6-security-lifecycle-nfr` 准备状态；公共验证不改变 Worker packaging、正式 Auth、
Session/Memory、SSE、前端和公网部署仍未完成的边界。

## 6A-6 Security, Lifecycle & NFR 实施授权（2026-08-18）

用户按 RQ-058 明确“继续下一步”，因此 `6A-6-security-lifecycle-nfr` 从准备状态进入实施。这里的
“安全/生命周期/NFR”不是一次泛化的安全大改，而是给已经完成的 PostgreSQL task/API 基座补上可验证
的运行边界：默认关闭 CORS、日志与 Secret 脱敏、owner/global 背压、分层 retention、terminal
delete 和结构化 observability/performance evidence。

### 本批设计不变量

- CORS 默认没有允许来源；production 的 wildcard + credentials 配置必须在启动/配置解析时拒绝；
- 日志和 metrics 只允许低敏元数据（task/run/status/phase/latency/counter 等），不允许 Riot ID、
  Prompt、报告正文、Provider body、异常堆栈、数据库 URL 或任何 Secret；公共错误保持 body-free；
- Riot 原始 cache、terminal task/run/Artifact/Trace、安全运维日志默认分别保留 7/90/30 天；测试使用
  注入时钟验证边界，不等待真实时间；
- terminal delete 先让资源对用户不可见，再清理 SQL 与 Artifact/Trace；删除必须幂等；部分文件清理
  失败记录安全补偿状态，但不能重新让资源对用户可见；active task delete 返回 conflict，不能冒充 cancel；
- owner/global capacity 在真实 PostgreSQL 并发下仍必须正确，容量错误不能返回成功 receipt；性能报告必须
  记录样本数、环境和分位数，不能把 Fake Provider 或 CI 抖动当作模型质量；
- 本批不实现正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume，
  不读取 API Key、不调用 Riot/Provider、不进入 6A-7。

实施计划为 `docs/plans/2026-08-17-6a-fastapi-postgresql-task-model-implementation.md` 的 6A-6 节。
严格顺序为教学、红灯测试、最小实现、聚焦/完整门禁、提交推送和 exact-SHA PostgreSQL CI；公共 CI 成功
前不关闭本批。

### 本地实现交接（尚未关闭）

本地已实现 `app/tasks/retention.py`、`app/tasks/deletion.py`、`app/tasks/observability.py` 和
`scripts/purge_expired_task_data.py`，并把 CORS/capacity/deletion/metrics 接到 API composition 与
Worker。新增 PostgreSQL lifecycle/capacity/performance 测试已加入阻塞 workflow；本机无 PostgreSQL，
因此真实数据库证据仍为空。聚焦 `30 passed, 6 skipped`、完整 `1077 passed, 27 skipped, 1 warning,
110 subtests passed`，RAG、compileall、Harness、秘密/SDK/YAML/diff/governance 门均通过；本轮没有
读取 Key 或调用 Riot/Provider。下一动作是 exact-SHA 提交/推送并等待两个公共 job，成功后再做 6A-6
收尾审查与 6A-7 交接。

### 6A-6 exact-SHA 公共闭环

首个实现 run `32137687527` 已全绿，但成功日志缺 actual p95/sample/environment，且 claim 样本只覆盖
单次 SQL 调用。项目没有用“测试通过”掩盖证据缺口，而是以 evidence-only 提交 `31d5e60` 增加 warm-up、
queued→claim 累计等待和安全日志输出。Actions run `32138025724` 随后两个 job 均成功：完整 pytest
`1077 passed, 27 skipped, 1 warning, 110 subtests passed`，PostgreSQL job `51 passed, 1 warning`。

在 `github-actions-postgresql-17-python-3.11` 环境中，8 个 warm create/query 样本 p95 为
`6.220ms`（目标 `<300ms`），8 个 queued→claim 样本 p95 为 `23.359ms`（目标 `<2000ms`）。这些是
作品集规模 task 控制面基线，不是公网 SLA、Agent/Provider 延迟或模型质量结论。

因此 6A-6/RQ-058 正式关闭。canonical 只交接 `6A-7-packaging-exit-review` 准备状态；6A-7 仍需用户
明确继续，且不得把 6A-6 解释成真实 Worker packaging、正式 Auth、Session/Memory、SSE、前端或公网部署。

## 6A-7 Packaging & Exit Review 实施授权（2026-08-18）

用户按 RQ-059 恢复 6A-7。本批不是增加 Coach 业务能力，而是把已验证的 FastAPI、PostgreSQL、
polling Worker 和既有 Application/Runtime/Harness/Artifact 组合成可在本地/CI 重建的 Linux 运行包。

### 冻结边界

- Compose 顺序为 PostgreSQL health → 一次性 migration → API/Worker；API 与 Worker 是同仓库模块化单体的
  不同进程角色，不引入 Redis/Celery/Kafka；
- 此前 fail-closed 的 Worker CLI 只在数据库/Data Dragon/RAG/Prompt/Artifact 依赖以及 Riot/Provider
  配置与构造合同成功后才能进入 polling；缺配置必须在 claim 前退出，构造 preflight 不冒充在线凭据
  或领域质量验证；
- packaging/Linux smoke/exit matrix 先以红灯合同固定。CI smoke 使用 Fake/no-I/O composition，不读取
  真实 Key、不调用 Riot、Data Dragon 或 Provider；
- exit matrix 必须逐项绑定源码、测试、公开 CI、限制与 deferred，不能用测试总数代替承诺核对；
- 本批不实现正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume、直接
  公网部署、LangGraph、Multi-Agent、MCP 或新 SDK。exact-SHA 公共 CI 成功前不关闭 6A。

### 本地实现与退出裁决

production Worker composition、`--check/--once`、非 root image、Compose 与 no-I/O smoke 已实现。
人工审查进一步要求 worker_id 在 Engine/网络前校验，并让 smoke 使用独立 Compose project/data volumes；
API stack 先以 `up --wait` 完成 migration/readiness，再用 one-off smoke 取得自身退出码，避免一次性
migration 正常退出触发整组提前终止。

在最终公共 run 之前，诊断修补后的本地聚焦为 `48 passed`、完整
`1102 passed, 27 skipped, 110 subtests passed`，RAG、Harness dry-run、compileall 与安全门通过；
由于本机没有 Docker/PostgreSQL，当时裁决正确保持 `keep-open-pending-exact-sha-linux-ci`。该临时裁决
随后由下方 `adf53e5` 的三 job 公共成功取代。

首个 `b0f61ca` / Actions `32145005904` 已让 pytest 与 PostgreSQL job 成功，也证明 Linux image、migration、
API readiness 可运行；one-off smoke 仍失败且旧错误码过宽。项目决定先补允许列表 stage diagnostics 和
有限 service logs，不输出原异常、不调用外部服务，也不凭猜测改 Repository/Worker 语义。

`d8c5063` / Actions `32146113582` 随后给出 `packaging_smoke_database_not_ready`，但同一 API 已用相同
DB 返回 readiness 200 并接受 POST 202。源码路径对照确认 direct script 从 wheel 导入 app，使 Alembic
root 落在 site-packages。采用 `python -m scripts...` 统一 Worker/smoke import root；不硬编码容器路径，
也不删除 migration identity gate。

`adf53e5` / Actions `32146760003` 最终三 job 全绿；Linux smoke 输出外部 Riot/Provider calls 0，并完成
HTTP create、PostgreSQL claim、安全 failed terminal、HTTP query 与 image boundary。6A 以 deferred
边界关闭；下一次只在用户授权后设计 Session/Memory，不把 package CI 误称为长期 Coach 或公网生产。

## Session/Memory 入口设计边界（2026-08-19）

状态收尾 `d1cc2ed` / Actions `32147545753` 的三 job 也已成功；用户随后以 RQ-060 授权
`stage-6-session-memory-entry-design`。本次先做教学、现状/参考源码审计、方案比较和逐节设计确认，
不是直接把 EchoMind 的 MemoryManager 或 AGI-Saber 的 MemoryStack 接入产品。

当前决策边界：

- 6A 的 PostgreSQL task 是运行控制面，不是对话 Session 或长期玩家 Memory；
- 原始比赛事实仍由领域结构化数据负责，RAG 仍存外部知识，二者不能被塞入 Memory 冒充统一存储；
- EchoMind 提供 `user_id + conv_id`、工作/情景/画像分层的参考思想，但 Redis/Chroma、自动画像写入、
  非持久 fire-and-forget 和弱 ownership 不能照搬；
- AGI-Saber 的分类、superseded/quarantine、召回过滤和 consolidation 可作为设计证据，但图数据库、
  自动从 assistant 回复提取偏好、无持久后台线程和跨存储弱事务也不直接采用；
- 长期写入必须在设计中明确来源、置信度、用户确认/确定性事实门、更正、冲突、导出、过期和删除；
- 本入口设计本身不实现产品代码；后续 RQ-064 只授权 entry design→6B-1→6B-2 三个独立公共批次，
  6B-2 后停止在 6B-3 准备态；同时不预先引入 Redis、Chroma、向量库、LangGraph 或其他新基础设施。

### 已确认的第一节：职责与主链

用户已确认 Task/Run、Session、消息派生工作上下文、长期玩家 Memory、原始比赛事实/Artifact 和 RAG
六类数据必须保持独立。未来模型或规则只能产生 Memory Candidate，长期状态必须经过来源、类型、置信度、
冲突与确认写入门；不能让一次 assistant 推断直接污染后续会话。

### 已确认的第二节：PostgreSQL 单一真源

用户确认 Session/Memory V1 继续使用现有 PostgreSQL/SQLAlchemy/Alembic 基座作为唯一权威存储。工作
上下文由消息与 Memory 的有界查询投影形成；Redis 只在真实性能 Bad Case 后作为可重建缓存，语义索引只在
结构化召回不足的评测证据出现后增加。EchoMind 式 Redis/Chroma 双真源和首日全量混合架构均不采用。

### 第三节的已冻结事实：外服账号认领不是归属验证

Riot 官方 LoL routing values 当前不含中国大陆 CN，RiftCoach V1 只能分析官方 API 可路由的外服账号。
Account-V1 的 Riot ID→PUUID 只能证明账号存在，不能证明当前应用 owner 控制该账号。登录 Riot 账号证据
需要获批 Production-level application/API key 与 RSO client 后使用 `/riot/account/v1/accounts/me`；要把
它绑定为当前 RiftCoach owner 的已验证关系，还必须有正式产品 Auth、安全 OAuth/OIDC callback 绑定和
精确 PUUID match。

因此，当前产品即使让用户选择“这是我的账号”，也只能建立未验证 `claimed_self` 关系：界面不得显示
“已验证本人”，不能解锁非公开数据，不能把相同 PUUID 下其他 RiftCoach owner 的目标、备注、训练计划或
Memory 合并进来。语言/展示等 owner-global 偏好只按 `owner_id` 保存；玩家相关状态再绑定
`owner_id × player_subject_id`。PUUID 是稳定的被分析主体身份，Riot ID 是可变显示别名，二者都不是
应用用户身份。

RQ-062 已确认 MVP 同时提供未验证 `claimed_self` 和受限 `public_observed`。前者可以承载 owner 为该
player subject 设置的训练目标、计划和进度，但必须显示未验证；后者用于职业选手、朋友等公开账号分析，
只允许公开比赛事实、owner-local 观察备注/趋势和第三人称语义，不生成被观察者的私人偏好或第一人称训练
完成度。两者都不增加 Riot 数据权限，也不跨 owner 合并私人状态。

底层模型不把三个界面标签硬塞进一个 enum，而是拆为两个维度：

```text
relationship_role = self | observed
verification_status = unverified_claim | not_applicable | rso_verified
```

`self + unverified_claim` 投影为 `claimed_self`，`observed + not_applicable` 投影为
`public_observed`，未来 `self + rso_verified` 才投影为 `verified_self`。当前 verified 写路径必须不存在。
同一 PUUID 改 Riot ID 只更新可审计别名，不新建 subject/Memory；同一显示 Riot ID 解析为不同 PUUID 时
不得静默重绑。

本确认不授权 Auth/RSO 或 Session/Memory 代码实现。Conversation 切换机制随后由 RQ-063 单独裁决。

### 已确认的第三节续：Conversation 生命周期固定一个玩家

RQ-063 接受最小、安全的 V1：conversation 创建时属于 trusted owner，并固定引用该 owner 的一个
player subject/relationship；生命周期内没有切换 endpoint。相同 PUUID 的 Riot ID 改名可以继续，不同
PUUID 返回安全 mismatch 并要求新建 conversation。自由文本、模型、客户端 body 或最新 Riot ID 不能修改
绑定。

消息、工作 Context、review task/run 与 Memory Candidate 都必须从服务器 conversation 继承相同的
`owner_id + conversation_id + player_subject_id`。未来实现使用应用层身份校验和 PostgreSQL owner-scoped
composite foreign key/unique/check 约束双层防线；迟到 task 也只能写回自己冻结的 tuple，不能按当前 UI
选中的玩家重新解释。

源码审计同时发现一个尚未裁决的创建顺序：当前 HTTP task 入队时只有 owner + Riot ID，Worker claim 后
`RecentReviewApplicationService` 才调用 Riot API 并获得完整 PUUID。因此下一节必须比较独立异步
player-link task、首个 review task bootstrap 与 API 同步 lookup；禁止先用可变 Riot ID 创建 provisional
subject 再静默替换。RQ-063 本身没有授权任何产品代码。

### RQ-064 最终入口设计裁决

三案比较后采用独立异步 Player Link：

```text
POST /player-links
→ PostgreSQL link intent
→ PlayerLinkWorker 在事务外调用 Account-V1
→ 一个短事务写 subject + alias + owner relationship + link terminal
→ link 成功后才创建 Conversation
```

不把它塞入 Review Task，因为账号解析没有 publication/Trace/final Artifact 成功语义；不在 API 内同步调用
Riot，因为 API 不应读取 Riot Key、持有长事务或承受上游长尾；不以 Riot ID 建 provisional subject，因为
Riot ID 可改名、重指向。queued task 必须私有持久化严格规范化、bounded 的 `game_name/tag_line`，hash 只能
用于指纹/检索，不能替代 Worker 所需输入。

Memory 采用关系型身份/状态骨架、分类型长期记录与有界严格 JSONB 叶子。所有长期改变先形成带来源、目标
作用域、producer/version、confidence 与 gate policy 的 Memory Candidate；自然语言或模型推断一律 pending，
confidence 不能越过权限，Training Plan 必须确认，确定性 Progress 必须有完整 Artifact。accepted Candidate
与目标记录同事务物化，并用 `source_candidate_id` 唯一和 supersede/version chain 防止重复或原地覆盖。

Context V1 只做 owner/conversation/subject scoped 的确定性有界选择，Message/Memory 永远是 data-only；
PostgreSQL 是唯一真源。Redis、向量检索、RLS、LangGraph、新 SDK、正式 Auth/RSO/HTTPS、SSE/前端、MCP、
Multi-Agent 与自动恢复仍不进入本批。

正式文件为 ADR-0039、`docs/plans/2026-08-19-stage6-session-memory-design.md` 和
`docs/plans/2026-08-19-stage6-session-memory-implementation.md`。全路线拆为 6B-1 至 6B-9，但 RQ-064 的
自动执行范围只到 6B-2：设计、6B-1、6B-2 各自独立验证/提交/推送/exact-SHA CI；6B-2 全绿后只准备
6B-3 并等待新授权。下方公共闭环发生前，这些设计文件仅在本地且尚未创建产品 schema/migration；该临时
状态已由后续 `bc11afe` 公共证据取代。

### Entry design 公共证据与 6B-1 决策状态

设计提交 `bc11afe9f2f85a39f05b7f3d6135b14821ebb17d` 已由 GitHub Actions run `32222531783`
完成 exact-SHA 公共验证，`pytest`、真实 PostgreSQL migration job 与 Linux packaging-smoke 三 job 均成功。
因此 ADR-0039 与两份计划从“本地冻结”升级为公开可复现设计证据；这仍不等于任何 Player/Memory 表已存在。

RQ-064 现只启动 6B-1：复用现有 SQLAlchemy Base/Alembic/PostgreSQL 基座，建立独立 Player Link domain、
四张表、可逆 migration 与事务 Repository。它不复用带 publication/Trace/Artifact 语义的 Review Task
terminal，不在 API/数据库事务内执行 Account-V1，也不提前写 6B-2 Worker/API 或 6B-3 Conversation。

### RQ-065：6B-1 后停止的执行裁决

用户把本轮范围收紧为只完成 `6B-1-player-identity-link-foundation`。因此 6B-1 仍按既定合同完成独立
教学、TDD、本地门禁、提交/推送与 exact-SHA 三 job；公共全绿后只把 6B-2 标为
prepared/waiting authorization 并停止。此裁决只改变自动推进边界，不删除、合并或重排 6B-2 至 6B-9，
也不放宽外部 I/O、Auth/RSO、SSE/前端、MCP、Multi-Agent 或新技术采用门。

### 6B-1 最终公共裁决

实现与两轮定点 migration 修补最终收敛在 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b`；Actions
`32229024069` 的 pytest、真实 PostgreSQL 与 Linux packaging-smoke 三 job 均成功。接受 6B-1 为完成，
包括 stable PUUID subject、subject-local alias、owner-local typed relationship、private Link Task、短事务
Repository、idempotency/capacity、SKIP LOCKED、ON CONFLICT、role-conflict atomic failure、CAS/rollback
与 confirmed display snapshot。该裁决不接受 Resolver/Worker/API、Conversation/Memory 或正式 Auth 已完成；
按 RQ-065 只准备 6B-2 并停止。

### RQ-066：6B-2 实施授权

用户在上述停止点后的新一轮明确“继续开工”，因此只恢复
`6B-2-async-player-link-worker-api`。既有 ADR-0039 方案不变：API 只做 owner-scoped 短事务入队/查询，
专用 Worker 在 claim commit 后、数据库事务外调用窄 Account Resolver，Repository 再以短事务落身份关系
或安全终态。开发、测试与 CI 使用 Fake client/resolver，真实 Riot/Provider/Key I/O 为 0。6B-2 公共
闭环后只准备 6B-3，不实现 Conversation/Memory。

### 6B-2 本地实现收尾决策（等待 exact-SHA）

Task 1–4 已按 ADR-0039 实现并通过本地测试：严格 Account Resolver、事务外 PlayerLinkWorker、
owner-scoped Link API、独立 worker composition/CLI 与 Fake Resolver package smoke。反向审查后保留三项
边界修补：routing policy 必须完整覆盖 API 的四个 regional values；package smoke 使用独立固定 Link
worker ID；Link Worker 自带最小 StopSignal Protocol，不依赖 Review Worker 内部类型。

本地完整回归为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`，RAG 两套门、Harness dry-run、
compileall、YAML、governance、SDK/Secret/run-data 与 diff 门通过。42 个 skip 是本机没有 PostgreSQL/Docker
的限制；真实 migration/API/package 证据必须由同一提交的 GitHub Actions 提供。当前不把本地完成写成
6B-2 已关闭，Task 5 只负责提交、推送和 exact-SHA 三 job；全绿后只准备 6B-3，不实现 Conversation/Memory。

### 6B-2 最终公共裁决

实现提交 `0c13a583ea51a7c18301fc29bf5c2931790d6693` 对应 Actions run `32301852042`；
`pytest`、真实 `postgres-migrations` 与 Linux `packaging-smoke` 三 job 全部 completed/success。
接受 6B-2 为完成：API 短事务只写 Link intent，专用 Worker 在 claim commit 后通过事务外窄 Resolver
解析 Account-V1，Repository 再以短事务写身份关系或安全终态；API composition 不构造 Riot Client。

Linux smoke 同时得到 Review Task 的安全 `failed` 与 Fake Resolver Player Link 的 `succeeded`，并记录
`external_riot_provider_calls=0`。该证据不准入真实 Riot Key、账号所有权、Provider 质量、自动 retry/reclaim、
Conversation/Memory 或正式 Auth。按 RQ-066，下一检查点只置为
`6B-3-conversation-message-foundation` prepared/waiting authorization，本轮停止。

### RQ-067：用覆盖矩阵补齐持久教学与工程证据

本次重新审计没有把“已经在聊天里讲过”或“代码/测试存在”当成项目所有者已经掌握。最早真实缺口在
阶段 0：此前有 ADR 和高层吸收矩阵，但缺少参考快照身份、源码模块、测试事实、文档/实现偏差、采纳/拒绝
映射和面试边界组成的可复核证据链。阶段 1、4、5A、5B、6B-1、6B-2 也有不同程度的实现后教学缺口。

采用覆盖矩阵驱动的混合方案：成熟的设计/实施/退出材料直接复用，真实缺口新增 walkthrough 或
implementation review；不为每个历史原子检查点机械复制文件。`docs/learning/coverage.yaml` 对每个组记录
严格递增 sequence、覆盖 checkpoint、complete/planned 状态及八类证据：问题/原理、设计/实现、代码地图、
数据/控制流、验证、运行、失败/安全/边界和面试表述。治理脚本以红灯测试固定当前 checkpoint、前序 complete、
路径在仓库内且为非空 Markdown，防止后续推进再次依赖长对话记忆。

本批只补说明、索引、README 和治理，不创建 Conversation/Message/Memory 产品代码，不调用 Riot/Provider，
不改变阶段 0—8 或 6B-1 至 6B-9 顺序。RQ-067 已构成 6B-3 的条件实施授权：文档批独立提交、推送并通过
exact-SHA 公共 CI 后，无需再次确认进入 6B-3 初学者设计复核与 TDD；在公共闭环前 canonical 仍保持
`6B-3-conversation-message-foundation`，产品代码门关闭。

### RQ-067 公共验证与 6B-3 交接

文档/工程证据提交 `63435d90f5153309fce98b92a2ff58425d54a684` 已由 GitHub Actions run `32308631289`
精确验证；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部成功。RQ-067 的前置门因此关闭，
Q11 “所有者学习与工程证据连续性”从本地完成升级为公共完成。

这次公共闭环只证明文档、治理、现有代码回归、真实 PostgreSQL migration/metadata 和 Linux package 边界；
不证明 Conversation/Message/Memory 已实现，也不改变此前的外服账号未验证认领、无正式 Auth/RSO、无公网
部署和无真实 Provider 质量准入边界。canonical 现在进入 `6B-3-conversation-message-foundation`：
先进行初学者设计复核和红灯合同，再实现最小 Conversation/Message foundation；Agent、Review Task、Memory、
SSE、前端和新框架仍在本批之外。

### 6B-3 Conversation / Message 设计冻结（2026-08-20）

6B-3 的实现前审计没有改变阶段路线，但把原总设计中的几个隐含点明确化：

- 复合 FK 只证明 relationship identity，创建必须按 relationship→conversation 锁顺序在同一短事务
  检查 `status=active`；读取和追加同时过滤 hidden relationship；
- Conversation 创建沿用现有 POST 控制面的 owner-scoped `Idempotency-Key + fingerprint`，避免网络重试
  创建重复房间；
- Message schema 保留 `user|assistant`，但 6B-3 公共 Service/API 只允许 user，可信 assistant terminal
  延后到 6B-8；system/tool/provider/reasoning 不属于公共 Message；
- 序号从 1 开始，锁 Conversation 行并在同一事务插入/递增，`UNIQUE(conversation_id, sequence_no)`
  做数据库第二道防线；
- `active → archived|hidden`，archived 可读不可写，hidden 对 owner 404-equivalent，V1 无 unarchive/unhide；
- 0003 migration 首次引入 immutable binding/message trigger，必须用真实 PostgreSQL direct SQL、回滚和并发
  测试证明；SQLite/Fake 只能证明纯逻辑或 HTTP 投影。

正式合同与取舍见 [ADR-0040](adr/0040-conversation-message-foundation-contract.md) 和
[6B-3 设计稿](plans/2026-08-20-conversation-message-foundation-design.md)。当前工作树已经具备
domain、Service、0003 migration、Repository、HTTP/composition/package 与分层测试；本地实现仍待
同一提交的 PostgreSQL/package exact-SHA 公共门。它不表示 Agent/Memory 已接入。

### 6B-3 实现 exact-SHA 公共闭环与收尾状态（2026-08-20）

实现批通过 6B-3 聚焦 `85 passed, 25 skipped` 与完整 `1295 passed, 67 skipped, 1 warning,
110 subtests passed`。本地 RAG development/independent holdout、Harness dry-run、compileall、
Provider boundary、tracked secret/run-data、YAML、治理与 `git diff --check` 均通过；本机没有 Docker，
因此 Compose 与真实 PostgreSQL 由提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081` 的 Actions run
`32329686381` 补证。该公共 run 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功，
真实 PostgreSQL 运行 `100 passed, 1 warning`，并通过 migration upgrade/downgrade、`alembic check` 和
Linux package smoke。审查修复了 archive/hide OpenAPI 422 投影和有效 command 后服务故障的 503 投影，
并把生命周期/append 测试改为确定性锁顺序。

这批仍保持以下边界：公共 API 只能追加 user Message；assistant 必须有未来可信 `source_run_id`
terminal 证明；不接 Agent、Review Task 2.0、Memory、Auth、SSE、前端或新框架。6B-3 现已正式关闭，
coverage 置为 `complete`；下一检查点为 `6B-4-conversation-bound-recent-review-identity`，仅
prepared/waiting authorization，不实施 6B-4。

### RQ-068：6B-4 采用原表 nullable schema 2.0 identity columns

用户明确授权 `6B-4-conversation-bound-recent-review-identity`。本轮保留 6A 已成熟的 Review Task、
claim、Worker、terminal/reconciliation 和 lifecycle 基座，不新建第二套 Conversation Task 系统。

Review Task schema 2.0 在既有 `review_tasks` 上增加 nullable、legacy-compatible 的 Conversation identity
列。创建路径必须在一个 PostgreSQL 短事务中锁定 owner 可见且 active 的 Conversation，服务器派生并冻结
owner/conversation/relationship/player-subject tuple；客户端 body、模型、自由文本、可变 Riot ID 和 UI
后来选择都不能覆盖。schema 1.0 历史 row 的新列保持 null，旧 endpoint 与执行兼容，但不生成 Conversation
或 Memory，也不根据旧 Riot ID 静默回填 subject。

v2 执行通过稳定 subject 的 trusted PUUID 直接进入 Summary/Match-V5，不再次调用 Account-V1；alias 只作
显示。选择该方案是因为“只把 conversation_id 放 JSON”缺少数据库级 identity 约束，而新建第二套 task
表会复制可靠运行基础设施。此裁决不授权 6B-5、assistant Message、Memory、正式 Auth/RSO、SSE、前端、
LangGraph、Multi-Agent 或新 SDK；测试与 CI 外部 Riot/Provider 调用保持 0。

### 6B-4 本地实现裁决（公共验证前）

实现保持 ADR-0041 的原方案，没有因编码便利改为 JSON-only identity 或第二套 Worker。schema 2.0 的
pure/API、0004/ORM、Repository atomic binding、trusted-PUUID Summary/Application、1.0/2.0 Executor、
composition 与 package smoke 已在本地完成；walkthrough 已将问题/原理、代码地图、控制流、验证、运行、
安全边界和面试表述全部登记。

本地完整回归为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`，RAG、Harness、compileall、
SDK/tracked-data、YAML、pip、governance 与 diff 门通过。78 个 skip 是本机没有 PostgreSQL/Docker，不能
替代复合 FK、trigger、锁顺序和 Linux package 证据；因此 6B-4 仍为 in-progress，coverage 仍为 planned，
只有 exact-SHA 三 job 全绿后才能关闭。本轮仍不进入 6B-5。

### 6B-4 exact-SHA 公共闭环与 6B-5 停止点（2026-08-20）

实现提交 `d63f9085f66e49557b4674d0698495dcb7335c82` 对应 GitHub Actions run `32347834279`；
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。公开完整回归为
`1333 passed, 78 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL 为 `113 passed, 1 warning`，
并通过 0004 可逆迁移与 metadata-head 一致性。Linux package smoke 证明 schema 2.0 Task 可由同一 Worker
进入安全失败终态且外部 Riot/Provider 调用为 0；它不证明真实 Coach 报告成功或模型质量。

因此 6B-4 与八维 coverage 正式关闭。下一检查点固定为 `6B-5-memory-candidate-write-gate`，但只处于
prepared/waiting authorization：尚未创建 Candidate migration/model/Repository/API，也未进入具体长期
Memory、assistant terminal、Auth/RSO、SSE、前端或新框架。

### RQ-069：6B-5 采用事务内 typed materializer 接缝（2026-08-20）

用户已明确授权 6B-5。经比较万能 JSONB Memory 表、accepted receipt、额外 approved 中间态和事务内
typed materializer 后，ADR-0042 选择最后一种：Candidate 只能从服务器 Conversation 派生完整 identity；
模型/自然语言 confidence 再高也只能 pending；接受时，Repository 在同一 PostgreSQL Session/事务中调用
已注册的本地 typed materializer，目标写入成功后才把 Candidate 改为 accepted。正式 composition 在
6B-6 具体 target/materializer 存在前保持空 registry 并 fail closed。

6B-5 会用测试专用 typed target 证明事务提交、回滚、并发和重放，但不会把该测试表或 Candidate target
reference 称为长期 Memory。Preference/Profile/Review Memory/Plan/Progress、assistant terminal、Memory
Context、正式 Auth/RSO、SSE、前端和新框架仍在本批之外。

### 6B-5 exact-SHA 公共闭环与 6B-6 停止点（2026-08-20）

实现 `7156cb5` 的首次公共 run 正确暴露测试临时表 teardown 顺序缺口；生产 Candidate、migration、FK 与
materializer 合同未失败，也未被放宽。最小测试清理 `dd7c9c8` 先删除 `test_memory_targets`，再执行
Alembic downgrade。Actions run `32376405150` 的 `pytest`、`postgres-migrations`、`packaging-smoke`
三 job 全绿：普通回归 `1358 passed, 88 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL
`126 passed, 1 warning`，package Candidate 为 `rejected` 且外部调用为 0。

因此 6B-5 与八维 coverage 正式关闭。该结论只覆盖 Candidate control plane、deterministic gate、0005、
owner-scoped Repository/API 和事务内 typed materializer seam；生产 registry 在 6B-6 注册真实 target 前
继续 fail closed。下一检查点 `6B-6-preferences-profile-review-memory` 只 prepared/waiting authorization，
本轮不创建具体长期 Memory 表或进入 assistant terminal/Context/Auth/SSE/前端/新框架。

### RQ-070：6B-6 三类 typed 长期 Memory 设计冻结（2026-08-20）

用户最新“那继续”授权唯一下一检查点 6B-6。经初学者教学和 6B-5 接缝复核，本批采用三张独立 typed
目标表：`memory_preferences`、`player_profiles`、`review_memories`。它们共享 Python 辅助逻辑，但不使用
万能 `memories(kind, payload)` 表；owner/relationship/role/status/version/source candidate/唯一性由
关系型列和 PostgreSQL 约束负责，JSONB 只保存经过严格 Pydantic 校验的有界叶子值。

Preference 是 owner-global（V1 `report_language`）；Profile 是 owner-player 且只允许 `self`（V1
`main_role`/`champion_pool`）；Review Memory 是 owner-player，self/observed 均可，但 observed 只能写
`observation_note`/`public_trend` 的第三人称 `append`。Riot ID 仍只是 alias，`claimed_self` 仍不等于
正式账号所有权验证。

为了不修改已经公共闭环的 0005 Candidate 状态机，typed materializer 解析版本化
`{"value": ..., "expected_version": ...}` envelope。新记录从 version 1 开始；有 active 记录时必须
精确匹配 expected version，旧记录只转 `superseded`/`retired`，不原地覆盖。每个 scope/key 只有一个
active，materializer 使用同一事务的 PostgreSQL advisory lock + active row lock；target 写入、旧版本
supersede 和 Candidate accepted 一次提交，任何失败都 rollback 并保留 pending。

本批将提供 owner-scoped active/history 查询，不提供绕过 Candidate 的 target PATCH；更正必须创建新的
Candidate。正式文件为 [ADR-0043](adr/0043-adopt-typed-preference-profile-review-memory-targets.md)、
`docs/plans/2026-08-20-memory-types-design.md` 与
`docs/plans/2026-08-20-memory-types-implementation.md`。本设计批没有创建产品代码或外部调用；
Training Plan/Progress、Memory Context、assistant terminal、Auth/RSO、SSE、前端、Redis/Chroma、
LangGraph、Multi-Agent、新 SDK 与真实 Riot/Provider 继续 deferred。

### 6B-6 本地实现裁决（公共验证前）

实现保持 ADR-0043 的分表与 Candidate-only correction 决策：pure typed contract、三个 materializer、
三张 ORM 表/0006 migration、PostgreSQL version writer、生产 registry、owner-scoped query Service/API 和
package smoke 1.3 已建立。没有退回万能 JSONB 表，没有开放 target PATCH，也没有把 observed 升级为 Profile。

Candidate accept 的真实控制流是同事务 advisory lock→active row lock→expected-version→supersede/insert→
Candidate accepted。typed payload 和 version conflict 分别映射安全 422/409，Candidate 保持 pending；SQL/
未知错误映射 503 并 rollback。查询只返回 approved normalized payload、owner-local relationship 和版本，
不返回 PUUID、source Candidate/provenance、Prompt 或底层异常。

首轮聚焦/相邻为 `128 passed, 19 skipped, 1 warning`；提交前复核新增两项纯合同和两项真库合同后，完整回归为
`1402 passed, 100 skipped, 1 warning, 110 subtests passed`；本地 skip 来自无 PostgreSQL/Docker。两套 RAG、
Harness dry-run、compileall、YAML、治理、SDK/Secret/tracked-data 与 diff 门通过。实现后 walkthrough 和
八维 evidence 已建立，但 coverage 继续 planned。只有实现 SHA 的 `pytest`、
`postgres-migrations`、`packaging-smoke` 三 job 全绿后才能关闭 6B-6；当前不进入 6B-7。

### 6B-6 exact-SHA 公共闭环与 6B-7 停止点（2026-08-20）

首个实现 `da87cde` / Actions `32386630063` 的 pytest/package 成功，PostgreSQL 唯一失败是
observed `public_trend` 测试夹具错误使用被既定 Gate 禁止的 `user_structured_input`；失败 SHA 保留，
没有放宽生产权限。最小测试修复 `5531c81ec7117f5c454d320e406153086baae3ea` 改为合法
`deterministic_run_fact`，Actions `32387026797` 的三 job 全绿。

公共 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL 为
`142 passed, 1 warning`，Linux package smoke 完成 Candidate accepted→Preference v1 query 且
`external_riot_provider_calls=0`。据此 6B-6/coverage 正式完成。下一检查点
`6B-7-training-plan-progress` 仅 prepared/waiting authorization；尚无 Plan/Progress 产品代码。

### 6B-7 公共闭环与 6B-8 Context/turn 架构（2026-08-21）

6B-7 实现 `f6d89225ac5dbd568b6fad7c3c09b7c497c50762` 已由 Actions `32397290175` 的
`pytest`、`postgres-migrations`、`packaging-smoke` exact-SHA 三 job 全绿验证，coverage 置 complete。
RQ-071 因而自动授权进入 `6B-8-memory-aware-context-typed-turns`，仍不允许越级到 6B-9。

ADR-0045 决定：Conversation-bound schema 2.0 Task 的服务器 binding 是 Context 唯一身份；采用
run-scoped `MemoryAwareContextBuilder` 装饰现有 Builder，而不是原地把 DB 语义塞入 Builder 或在 Runtime
外拼 Prompt。合法 Message/Memory 全部是 data-only whole sections，同一 Skill ceiling 不可提高；私有
manifest 只保存 body-free ID/version/digest/count/omission。Assistant 只有在 SQL Task succeeded、
publication published/degraded 与 final Artifact digest 精确匹配后才能追加。当前 output 没有 typed
proposal，不能从报告自然语言猜 Candidate；只建立显式 proposal seam 并继续经过 Candidate gate。

### 6B-8 公共闭环与 6B-9 lifecycle/export 架构（2026-08-21）

`aacc11a` / Actions `32403187972` 已完成 6B-8 最终 exact-SHA 三 job；selector、body-free manifest、Runtime
binding、0008 terminal writer 和 package schema 1.5 均有公共证据。RQ-071 自动交接 6B-9。

ADR-0046 决定采用 centralized owner lifecycle service：PostgreSQL 同事务先隐藏选中数据并创建 body-free
deletion marker，事务外清理失败只留下 pending compensation，不重新暴露正文。三 scope 固定为
conversation-only、conversation+derived-memory、relationship-private-data；Task/Run/Artifact 与全局 Player
Subject 保持独立生命周期。导出是 owner-scoped bounded snapshot，retention/purge 使用 injected clock 与
FK-aware bounded batch。不采用分散 Repository delete 或 FK cascade hard delete。

### 6B-9 本地实现与退出裁决（2026-08-21）

ADR-0046 已落实为 strict lifecycle contracts、0009、集中式 owner Repository/Service、薄 API/composition 和
package schema 1.6。实现审查补充一项 lifecycle reset 规则：隐藏 active target 后，新链取历史最大 version+1，
但 `supersedes` 保持 null，不把隐藏记录重新连入公开历史。0009 所有已展开 CHECK 名使用 `op.f()`，避免 naming
convention 双前缀。当前退出裁决为 `pass-local-pending-public-ci`；只有实现 SHA 的 pytest、真实 PostgreSQL 和
Linux package 三 job 全绿后，才关闭 6B-9 与 Session/Memory V1。

### 6B-9 exact-SHA 公共闭环与阶段 7 停止点（2026-08-21）

设计提交 `4bdb1bb9e720bd853c677ce2f650476f19ab6e41` / Actions `32404203265` 先完成三 job
公共设计门。实现提交 `2e37bd4e156d750634d67d64c07ddb4784f048f4` / Actions `32407862496`
的 `pytest` 与 `packaging-smoke` 成功；真实 PostgreSQL 唯一失败是测试夹具在 hidden 后把 Conversation
恢复为 active/null hidden，0009 的 irreversible trigger 正确拒绝 `conversation_lifecycle_irreversible`。
生产 trigger、Repository、scope 或隐藏语义均未放宽。

最小修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` 只删除非法 reset；Actions `32408101770`
精确对应该 SHA，三 job 全部 completed/success。公共 pytest 为 `1490 passed, 116 skipped, 1 warning,
110 subtests passed`；真实 PostgreSQL 为 `164 passed, 1 warning`，0009 upgrade/downgrade 与
`alembic check` metadata-head 一致性通过；Linux package schema 1.6 成功断言 owner export、
conversation-only delete 后 Conversation/Message 不可见、Preference/Plan 继续可见，输出外部调用 0。

因此 6B-9、八维 coverage、Session/Memory V1 与阶段 6 正式关闭。唯一下一检查点命名为
`stage-7-standard-mcp-dynamic-meta-entry-design`，当前仅 prepared/waiting authorization；RQ-071 没有
授权阶段 7，尚未开始 MCP Client/Server、Meta Adapter、OP.GG 接入或真实互操作。

### Stage 7 入口设计（2026-08-21，RQ-072）

用户授权开始 `stage-7-standard-mcp-dynamic-meta-entry-design`。ADR-0047 选择
Adapter-first：标准 MCP Adapter 负责 initialize、capability、tools/list、tools/call、
session/transport 和协议错误，先转换为既有 `ToolDefinition` 再交给 `ToolRuntime`；
Meta Adapter 将外部结果规范化为带 source、patch、digest、fetched_at、freshness 的
data-only `MetaEvidence`。对外 RiftCoach MCP Server 只通过 owner-scoped Application
Facade 暴露近期汇总、单局分析、知识搜索和报告评测只读工具。

OP.GG 目前只是首选候选，尚未有仓库证据证明其标准 MCP endpoint、protocol/version、
transport、schema、许可、freshness、限流或真实互操作。缺一项就保持 candidate/deferred，
不得把普通 HTTP POST 改名为 MCP，也不得静默替换来源。入口设计不安装 SDK、不调用 OP.GG、
不实现 Client/Server；后续顺序固定为 pure contract → transport/discovery → OP.GG Meta
Adapter → RiftCoach Server → real interoperability exit review。

### Stage 7 入口设计公共闭环（2026-08-21）

`e50a546` / Actions `32436092074` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job
已精确对应该设计 SHA 并全部成功。ADR-0047、design、implementation plan、学习材料与八维 coverage
正式闭环；这只证明设计与既有基线兼容，不证明 MCP 产品互操作或 OP.GG 已准入。canonical 交接到
`7-1-mcp-client-contract`，等待用户明确授权；授权前不实现 pure MCP contract、transport、MetaEvidence
或 RiftCoach MCP Server。

### 7-1 MCP Client pure contract（2026-08-21，RQ-073）

用户“继续下一步”只授权 7-1。协议 envelope 与 transport 坚持分层：pure contract 负责 JSON-RPC/MCP
method、protocol version allowlist、capability、tool catalog/schema snapshot、call allowlist/arguments 和
有限 result/error；7-2 才负责 stdio/HTTP/session/deadline/disconnect。目录 schema digest 变化时旧 call
必须 fail closed。远端 JSON-RPC message/data、`isError` content 和 raw body 不进入内部错误，只投影有限
code/retryable/request-id/remote integer code。本批不安装 SDK、不调用 OP.GG/Riot/Provider、不实现
MetaEvidence、RiftCoach MCP Server 或真实互操作。

本地实现遵循该裁决：目录和 schema 递归冻结并生成 SHA-256，call 同时绑定 catalog/server identity 与具体
tool schema；standard annotations 严格接收，arguments/result 使用独立 canonical byte 上限。远端 description、
instructions、arguments、content 和 structured content 不进入默认 repr。完整本地回归为 1509 passed/117
skipped，全部横向门通过；公共 exact-SHA 前 coverage 保持 planned，7-1 不关闭。

`37f16bc` / Actions `32439753589` 随后完成三个 exact-SHA 公共 job；公开 pytest 1510/116 skips、真实
PostgreSQL 164 passed、package schema 1.6/external calls 0。7-1 因而关闭，coverage complete；下一检查点只
准备 `7-2-mcp-transport-and-discovery`，未获授权前不写 transport/session/discovery 代码。

### 7-2 MCP transport 与动态 discovery（2026-08-21，RQ-074）

用户明确“继续7-2”，授权在 7-1 pure contract 之上实施本地 transport/session/discovery。Adapter 复用
`McpInitializeResult`、`McpToolCatalog` 与 `McpToolCall*` parser；session 绑定初始化 identity、tools
capability、catalog digest 与 transport generation，generation 变化即 fail closed 并要求重新 initialize。
先采用有界 JSONL stdio 与 in-memory fixture；HTTP/Streamable HTTP 没有标准/部署证据，暂不实现。发现的
descriptor 只映射为 `ToolDefinition` handler，可靠性仍由 `ToolRuntime` 唯一负责。本批不安装 SDK、不接
OP.GG/Riot/Provider、不读取 Key、不实现 MetaEvidence、RiftCoach MCP Server 或真实互操作。

本地 TDD 已证实 11 项 transport/session/discovery 测试通过；完整回归与横向门禁通过，但在 exact-SHA
公共 CI 前仍保持 7-2 open、coverage planned。该本地证据只证明 fixture/in-memory/隔离 stdio 合同，
不把 subprocess fixture 说成真实 MCP 互操作。

`f121666` / Actions `32441793585` 的 exact-SHA 三 job 随后全绿；7-2 coverage 置 complete，
canonical 只交接 `7-3-opgg-meta-adapter` prepared/waiting authorization。该公共 run 证明本地
transport/session/discovery 与既有 PostgreSQL/Linux package 基线兼容，不改变 OP.GG 尚未准入的裁决。

### 7-3 OP.GG Meta Adapter 分级准入与本地实现（2026-08-21，RQ-075/076/077）

官方 `opgginc/opgg-mcp`、`https://mcp-api.op.gg/mcp` 已真实完成 protocol `2025-06-18`
initialize、initialized notification、tools/list 和一次只读 lane-meta tools/call。RQ-076 纠正了
“缺完整 patch/TTL/outputSchema 就整体不接”的二元解释；ADR-0048 采用
`admitted_with_restrictions`：连接能力真实准入，provenance 固定为 partial，只允许当前快照建议，
禁止精确 patch、历史 patch 比较和上游新鲜度声明。

产品实现增加 HTTPS-only/no-redirect Streamable HTTP、获准目录子集、固定远端到本地工具映射、
无 `eval` 的 allowlisted AST lane-meta parser、typed/digest-bound `MetaEvidence`、15 分钟本地使用期限
和 optional user-role data-only Context。真实目录中未获准 Valorant 数组根 outputSchema 的 Bad Case
由“全响应资源门 + admitted subset 严格解析”解决；未获准工具不注册、不调用。

RQ-077 进一步固定 Riot 官方账号/排位/比赛、Data Dragon 版本静态数据、官方 patch/update 与 OP.GG
聚合 Meta 的分层组合边界；7-3 不实现两源 join，缺 patch 的 OP.GG 不继承 Riot patch 身份。当前只有
lane-meta 单向产品链和 body-free smoke；RiftCoach MCP Server、外部 Client 调用与双向退出门仍属于
7-4/7-5。完整本地门和实现 SHA 的 exact-SHA 三 job 前，7-3/coverage 继续 open。

`64311a1` / Actions `32455219404` 随后完成 7-3 exact-SHA 三 job 公共闭环：公共 pytest `1546/116`
（Linux/Windows skip 按环境分开）、真实 PostgreSQL `164 passed`、migration/head 无漂移，Linux package
schema 1.6 成功且外部 Riot/Provider 调用为 0。7-3 coverage 已 complete；该证据只关闭 OP.GG lane-meta
单向产品链，不扩大为全工具、精确 patch/freshness、Riot+OP.GG join、RiftCoach Server 或双向互操作。
canonical 只交接 `7-4-riftcoach-mcp-server` prepared/waiting authorization。

RQ-078 已授权 `7-4-riftcoach-mcp-server`。本检查点采用 strict Server Session → owner-scoped
Application Facade，只暴露四个只读受限工具；协议响应只含 allowlisted DTO/structuredContent，失败只返回
body-free MCP error。它不接受 owner_id/PUUID/Key/Prompt/Provider body，不直连 Repository，不实现公网
transport、真实外部 Client 或 7-5 双向互操作。

7-4 已完成本地 TDD 与全部门禁：Server 独立 Session、固定四工具目录、服务端 ActorContext owner 注入、
Query Facade、verified recent aggregate、single-review digest、knowledge attribution 和诚实 evaluation status
均有聚焦/相邻/完整回归证据。单局报告正文因当前持久合同缺少结构化 published-result Artifact 而不从 Markdown
反推；评测也保持 `score_available=false`，不把 published 虚构为 evaluator score。coverage 在实现 SHA 的
exact-SHA 三 job 前保持 planned；7-5 仍未进入。

实现 `431c584c6f07731233e6e32fd6f98505a661f910` / Actions `32480827952` 随后完成 exact-SHA
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环。公共 pytest 为 `1567 passed,
116 skipped, 1 warning, 127 subtests passed`，真实 PostgreSQL 为 `164 passed, 1 warning` 且 metadata-head
无漂移，Linux package schema 1.6/外部调用 0。7-4 coverage 已 complete；canonical 只交接
`7-5-mcp-interoperability-exit-review` prepared/waiting authorization，不把 fixture/CI 冒充真实外部双向互操作。

### 7-5 官方外部 Client 与 stdio 退出证明（2026-08-21，RQ-079）

RQ-079 已授权唯一检查点。ADR-0050 拒绝继续用仓库自己的 Python Client 冒充独立互操作，也不为本门
临时扩张公网 HTTP/Auth/TLS；采用锁版官方 `@modelcontextprotocol/sdk@1.30.0` Client，经标准 stdio
跨进程调用真实 `McpServerSession`。SDK 及 94-package lock graph 隔离在 evaluation 目录，许可证集合为
MIT/ISC/BSD-2/BSD-3，无 install script，官方 registry audit 当前为 0 vulnerability。

真实 SDK 揭示 Client proposal/Server negotiated version 的兼容缺口。Server 现在只接受
`2025-06-18`/`2025-11-25` proposal allowlist，但总是响应并绑定自身实现 `2025-06-18`；未知版本继续
fail closed。外部 Client 本地已完成 initialize、initialized notification、四工具 list 和一次
owner-scoped knowledge call，trace/catalog/result 只保留 digest/count。另一方向仍复用 7-3 OP.GG
Streamable HTTP 产品链。

实现 `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 已完成 exact-SHA
pytest、PostgreSQL migration/control-plane 与 Linux package 三 job 公共闭环。公共 pytest 为
`1577 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 为 `164 passed, 1 warning`
且 metadata=head；package schema 1.6、外部 Riot/Provider 调用 0。

同一 clean SHA 随后唯一执行一次双向门。官方 SDK→RiftCoach stdio 与 RiftCoach→OP.GG Streamable HTTP
均完成 initialize、initialized notification、tools/list 和一次 tools/call；OP.GG 保持 partial provenance，
不补写 patch、source time 或 freshness。不可覆盖 body-free evidence 绑定 implementation SHA，只保存身份、
时间窗、digest/count 与限制，Riot/LLM/Key I/O 为 0。

不可覆盖 evidence 提交 `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736`
的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。公共 pytest
`1578 passed, 116 skipped, 1 warning, 127 subtests passed`，真实 PostgreSQL
`164 passed, 1 warning` 且 migration/head 一致，Linux package schema 1.6/外部调用 0。7-5 coverage
已 complete，7-5 与 Stage 7 正式关闭。

### Stage 8 入口设计（2026-08-22，RQ-080）

用户明确授权开始 Stage 8 的唯一 canonical 检查点
`stage-8-multi-agent-reliable-runtime-productization-entry-design`。本轮只做入口设计，不把授权外推
为 Multi-Agent、DAG、cancel/resume、恢复、SSE、正式 Auth、前端、付费资源购买或公网部署。

ADR-0051 采用证据门控的双轨顺序：

```text
entry design → 8A gate → 8B advanced experiment → 8C reliable runtime
→ 8D Riot+OP.GG evidence fusion → 8E productization → 8F final eval/portfolio
```

8-Core 必须交付可靠 Runtime、typed EvidenceBundle、正式 Web 产品、安全/备份和完整回归；
8-Advanced 至少完成一个带 Bad Case、对照、消融、成本和 ADR 的高级实验，允许 reject 收尾。
8B 通过前不默认实现 DAG 或 Multi-Agent；8D 中 Riot 官方比赛/版本/Data Dragon 事实优先，OP.GG
保持 partial provenance，不能借用 Riot patch 或伪造 freshness。

前端采用自主 React 设计系统与精选外部资源。MotionSites 只作为公开目录/预览/Prompt 候选源，
每个候选必须经过 URL、许可、技术栈、性能、移动端、reduced-motion、键盘和撤出方案审查；用户提供
的离线 Excel 是研究输入，不是产品依赖，也不能替代官网当前目录核验。

此前治理常量和 ledger 只定义到 7-5，没有现成 Stage 8 机器名。本次不从对话猜子阶段，而是按九阶段路线
标题和既有 entry-design 命名规则显式登记
`stage-8-multi-agent-reliable-runtime-productization-entry-design`，同步治理常量、coverage、活动计划与路线。
该句记录的是 7-5 关闭时的 prepared/waiting authorization 交接；随后 RQ-080 已明确授权 entry design。
当前仍不把该授权外推为 8A–8F 的 Multi-Agent、DAG、可靠恢复、SSE、正式 Auth、前端或部署实现授权。

入口设计提交 `3431e8b47dd992b6c4741e12158855feb64ef917` / Actions `32564500421` 随后完成
exact-SHA 公共三 job：pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实
PostgreSQL `164 passed, 1 warning` 且 0001→0009 可逆、metadata=head；Linux package schema 1.6，
外部 Riot/Provider 调用 0。entry-design coverage complete。该闭环只证明 Stage 8 路线、采用门、
EvidenceBundle 与前端产品蓝图已冻结；当前 canonical 只交接 `8a-advanced-adoption-gate`
prepared/waiting authorization，不证明任何 8A–8F 产品能力已实现。

### 8A Advanced Adoption Gate（2026-08-22，RQ-081）

用户明确“开始”后，8A 只回答“哪些高级候选有资格进入公平实验”，不实现候选本身。ADR-0052
选择三路同切片结构：现有单 Runtime 串行为 baseline、普通受限并行为必要 comparator、角色隔离
Multi-Agent 为 primary candidate。这样未来观察到的等待时间改善不会被错误全部归因给 Multi-Agent。

角色隔离候选固定为 Knowledge、Meta、Coach 三个独立 Context：前两者分别只持有
`knowledge.search` 与 `opgg.lane_meta` fixture 权限，Coach 无工具，只消费 typed/digest-bound Artifact；
任何角色都不能发布，`ReviewHarness` 仍是唯一评测/修订/发布控制面。OP.GG schema drift、instruction-like
payload 与分支故障是安全压力假设，不冒充已发生的真实泄漏事故。

自动 lease/recovery 是真实缺口，但属于 8C Core，不能用来为 Multi-Agent 凑采用理由。通用 DAG/第三方
Runtime 和 Agentic Retrieval 当前分别因 durable core/框架特有 Bad Case、RAG 质量 Bad Case 不足而
deferred；不是永久拒绝，重开需新 Bad Case 和独立 ADR。

离线 gate 已用 strict models、case-set exact SHA、权限/发布/预算/holdout/停止线和 body-free decision
完成本地 TDD；没有启动 Agent、线程或网络，也没有调用 Riot/OP.GG/Provider、读取 Key、安装框架或修改
产品 Runtime。8B 的 20% 延迟、1.5x Token、额外至多 2 次 Provider call 等是预冻结门槛，不是 8A
性能证据。8A 仍等待完整本地门禁和 exact-SHA 公共闭环。

implementation `12ad83532d99990f5523d6ecc6def0b8a325d7d0` / Actions `32567642315` 随后完成
exact-SHA 三 job：公共 pytest `1601 passed, 116 skipped, 1 warning, 127 subtests passed`，真库
`164 passed, 1 warning` 且 migration/head 一致，Linux package schema 1.6/外部调用 0。8A 与八维
coverage 正式关闭；这不会把 candidate 升级为 adopted。8B 只 prepared/waiting authorization。

## 2026-08-22：8B 采用 evaluation-only 三路 runner，生产 Multi-Agent 仍待结果

- RQ-082 只授权 `8b-conditional-multi-agent-experiment`；先实现/验证实验控制面，再由唯一 holdout 决定
  Multi-Agent adopt/partial/reject，不能把 8A candidate 或本地 development TDD 当采用结论。
- 方案采用 Scripted/Fake Knowledge/Meta/Coach roles、fixture tools、typed/digest-bound Artifact 和真实
  `ReviewHarness`；产品 `AgentRuntimeV1`、Harness、MCP/Meta composition 不改。
- 普通受限并行是强制 comparator，也做 exact tool/typed evidence gate；角色隔离不能靠削弱 comparator
  制造收益。DAG/第三方 Runtime、Agentic Retrieval、真实模型/OP.GG I/O 继续排除。
- 实现 SHA 必须先 exact-SHA 三 job 公共成功；随后 clean SHA development admission 和 holdout result 均
  immutable/SHA-bound/body-free。当前 holdout 0 次，最终 ADR 尚未创建。

## 2026-08-22：ADR-0053 拒绝产品 Multi-Agent

- implementation `180bc8b` / Actions `32572085065` 全绿后，development 与 holdout 按冻结顺序各执行一次；
  holdout result SHA `944258...445e8`，不得覆盖或重跑。
- Multi-Agent 的 match/safe degraded/hard gates 都合格，但 latency improvement 18.95% 未达 20%，且
  failure isolation 1.0 与普通并行相同；普通并行自身为 22.88%、Token 1.05、无额外 calls。
- 产品决策是 reject role-isolated Multi-Agent；保留 strict runner/lifecycle/result validator 作为评测资产，
  bounded parallel 作为 8D 优先方案输入。该决定不等于 8D 已实现，也不改变 8C 可靠 Runtime Core 顺序。

## 2026-08-22：8B 关闭，8C 等待授权

- `783a329` / Actions `32572610725` 对 result/ADR/evidence 的 exact-SHA 三 job 全绿；8B coverage complete。
- 当前唯一下一检查点为 `8c-reliable-runtime-core` prepared/waiting authorization。8C 只在用户授权后开始
  lease/fencing、cancel、checkpoint、recovery 和 late-result isolation 的教学/设计/TDD；不把 8B reject
  或普通并行设计输入解释成 8C 已实现。

## 2026-08-22：ADR-0054 采用 PostgreSQL leased/fenced task control plane

- RQ-083 已授权 `8c-reliable-runtime-core`；用户在 8B 复盘后再次确认继续。8C 不重新打开产品 Multi-Agent，
  也不把 8D Riot+OP.GG fusion 偷渡到当前范围。
- 三案比较采用 PostgreSQL 增量可靠控制面；完整事件溯源/DAG Runtime 重写因 8B reject 与迁移成本拒绝，
  Redis/Celery 因没有 PostgreSQL 不足 Bad Case deferred。
- `review_tasks` 保存当前 projection，append-only `review_task_events` 保存 body-free lifecycle history；
  Runtime Trace 继续保存 Provider/Tool/Harness 内部事实。claim 分配 generation + private token + expiry，
  heartbeat/checkpoint/terminal 使用同一 fencing identity。
- cancel 是 owner-scoped 持久请求。自动 recovery 只接受 strict Receipt/Trace/Artifact terminal proof 或最新
  `claimed_safe` checkpoint；已开始未知副作用而没有终态证据时进入 `recovery_required`，不盲目重跑。
- 该段记录设计批完成时的历史事实；随后 0010 migration、Repository、Worker、Recovery 和 API 产品代码已
  在工作树本地完成，coverage 仍在公共 implementation 门前保持 planned。
## 2026-08-22：8C 本地 implementation/evidence 收尾裁决

- ADR-0054 的 PostgreSQL 增量路线已实际落地：task row 是当前 projection，`review_task_events` 是
  append-only body-free lifecycle；Runtime Trace/Harness/Artifact 仍是各自事实源，不复制正文。
- terminal ownership 由 worker + generation + private token + live expiry + status/cancel 共同 fencing；
  Worker success/failure 被最后一瞬 cancel 抢先时再尝试 fenced cancel，new generation 则收敛 ownership lost。
- expired recovery 只接受 strict Receipt 或 `claimed_safe`；missing/drifted/unsafe evidence 进入
  `recovery_required`，不以重跑追求自动恢复率。
- 公共 event DTO 删除内部 operation identity；Linux package smoke 增加 owner-scoped event page 复读，
  不抬高 schema、不引入 SSE。完整本地 pytest `1670 passed, 133 skipped`，公共真库/Linux 尚待证明。
- 当前仍为 `8c-reliable-runtime-core / in_progress`、coverage planned；8D 只有在 implementation/evidence
  exact-SHA 三 job 全绿并完成独立状态收尾后才可 prepared，不能提前实现。

## 2026-08-23：8C 公共 CI 修复裁决

- 公共 run `32579514636` 的 migration downgrade 与 package queued-insert 失败均属于 PostgreSQL 边界实现错误，不改变 ADR-0054 的架构或安全语义；repair run `32584144522` 又暴露了终态兼容与 strict JSONB 读回边界。
- 采用最小修复：Alembic downgrade 对 naming-convention 约束名统一使用 `op.f()`；queued task 的可空 checkpoint 使用 `JSONB(none_as_null=True)`，不放宽 `ck_review_tasks_checkpoint_shape`。
- 修复新增离线与真实真库回归，coverage 继续 `planned`；在 repair implementation SHA 的三 job 全绿前，不关闭 8C、不进入 8D。

## 2026-08-23：8C 第二轮 CI 兼容性裁决

- 终态 `succeeded/failed` 是已结束的控制面投影，heartbeat 只属于运行期租约；为兼容已有合法终态行，lifecycle CHECK 仅要求 `running/recovery_required` 有 heartbeat/generation，终态允许 heartbeat 为空且保留 legacy generation 0。
- JSONB checkpoint 在数据库中是 JSON wire data；strict Pydantic 合同通过 JSON round-trip 解析字符串时间戳，不改为宽松模型验证，也不暴露 checkpoint body。
- 该轮修复继续属于 8C PostgreSQL boundary repair；coverage 保持 `planned`，不提前进入 8D。

## 2026-08-23：8D 采用 typed EvidenceBundle；README 研究留在 8F 横向线

- RQ-084 已授权 `8d-riot-opgg-evidence-fusion-core`；ADR-0055 选择 immutable typed EvidenceBundle +
  deterministic pure fusion kernel，拒绝无类型 JSON merge，暂缓通用 claim graph/event store。
- Riot 官方事实、Data Dragon 静态、official patch/update 与 OP.GG Meta 各自保留 provenance/digest；join
  显式使用 region/queue/position/champion/optional patch。OP.GG partial 只支持 current snapshot，缺失、过期、
  schema drift 或 mismatch 进入 typed gap/conflict，不从 Riot 补 patch/source time/freshness。
- RQ-085 要求 8F README 广泛研究高星和低星但优秀的项目，不限三个示例；总览/架构/流程/展示图按信息目的
  选择 AI 绘图、截图、SVG 或 Mermaid。该横向要求不打断 8D，也不允许生成图冒充真实截图。
- 当前只完成 8D 本地设计、contracts/adapters/fusion TDD；focused 18、相邻 48、完整 1691/134 skips；完整门和
  exact-SHA 公共 CI 前不关闭 8D、不进入 8E。

## 2026-08-23：8D 公共关闭，8E 仅 prepared

- implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions `32598480400`
  的 pytest、PostgreSQL、Linux package 三 job 全绿；8D coverage complete。
- 产品采用结论保持 ADR-0055：typed EvidenceBundle + deterministic pure fusion，不引入 claim graph、DAG、
  Multi-Agent 或新持久化真源。partial OP.GG 只支持 current snapshot，不从 Riot 补 patch/freshness。
- canonical 只交接 `8e-productization` prepared/waiting authorization；Auth/SSE/React/部署、真实刷新和 8F
  README/作品集统一交付尚未开始。

### 2026-08-23：8E schema-drift 诊断边界

- ADR-0057 采用 `OPGGMetaSchemaDiagnostic` 记录字段级结构摘要；错误和持久 evidence 保持 body-free。
- 受控 fixture 只证明 adapter 能安全识别非字面量节点，不证明真实 OP.GG `mid` 的具体字段；live
  字段级诊断与 allowlist 裁决仍待新的明确外部授权。

## 2026-08-23：ADR-0059 玩家档案与显式 Riot 路由

- 采用 successful Player Link 的 owner-scoped latest-success projection 作为玩家档案列表；当前没有独立
  default/profile table 的 Bad Case，因此不新增 migration、默认项、昵称或排序状态。
- `player_profile_id` 是 opaque 公共 selection ID，当前复用 relationship identity。Conversation 新字段以它
  为 canonical；旧 `relationship_id` 仅作严格输入兼容，双字段同时出现拒绝。
- legacy recent review 必须显式提交 allowlisted routing region；Conversation review 从私有 SQL execution
  target 取得 region。Worker 只从环境读取 Key，预建四地区 client 并 exact-select；拒绝 ambient default、
  CN fallback、自动探区和跨区重试。
- RQ-089 后本机 Docker Desktop/PostgreSQL 17/Linux Compose smoke 已可作为提交前反馈；它不取代 exact-SHA
  公共 `pytest`、`postgres-migrations`、`packaging-smoke`，也不把整个 8E 标为完成。
- 本批不实现正式 Auth/RSO、SSE、前端、EvidenceBundle store、HTTPS、备份或部署；ShowMaker 不是默认账号。

## 2026-08-23：8E Batch B 公共关闭与 Batch C 顺序

- `e844bdd673ee051568e8611160f6ba53e8c745c4` / Actions `32622696087` 的 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest 1709、真库 187、Linux package 1.6。
- ADR-0059 的 profile/routing 裁决正式关闭当前批，但不关闭 8E、不把 coverage 改为 complete。
- 按已持久化的 preflight 顺序，下一内部批仍是 Batch C：EvidenceBundle persistence/refresh/expiry、8C
  event replay→SSE body-free DTO 与 `published/degraded/rejected/not_ready` 状态合同；不得静默跳过后直接
  开始 Batch D 前端。Batch C 公共闭环后才进入静态/fixture-backed screen。

## 2026-08-23：8C 第三轮真库兼容裁决

- Repository 的所有 JSONB checkpoint 读回路径（task、event、requeue）统一经过 strict JSON wire parser，并兼容 psycopg `Jsonb` wrapper；不以 `strict=False` 放宽 Pydantic 合同。
- package smoke 已从 claim 推进到 owner-scoped event page，说明前两轮修复有效；event query 仍待最新 SHA 公共 Linux 复验，8C 不提前关闭。
- 一个既有 PostgreSQL-only product vertical test 的 `timedelta` 漏导入是测试接线错误，已补最小导入，不改变产品行为。

## 2026-08-23：8C 第四轮 event JSONB 裁决

- task 与 event 的可空 checkpoint 都必须把 Python `None` 映射为 SQL `NULL`；否则无 checkpoint event 在 psycopg JSONB 边界可能变成 JSON `null` wrapper，破坏 body-free replay 读取。
- 采用 `ReviewTaskEventRecord.checkpoint_reference = JSONB(none_as_null=True)`；不放宽 event parser、不改变 migration schema、不暴露 checkpoint body。
- package smoke 在 event response 失败时只打印 status/code/JSON key 的 body-free diagnostics，便于区分 API service error 与 response-shape error。

## 2026-08-23：ADR-0060 采用 PostgreSQL Evidence revision 与 cursor SSE

- RQ-090 已授权 Batch C。三案比较拒绝 file-backed 双真源和 reconstruct-on-read 网络副作用，采用与
  `review_tasks` owner/run 复合身份绑定的 PostgreSQL append-only typed snapshot；refresh 只追加 revision，
  相同 refresh identity 幂等 replay，旧 revision 不覆盖或自动回退。
- expiry 是 query-time usability projection：快照/digest 保留审计，但 expired Meta/exact-patch claim 不再
  可用，产品至少降级。Batch C 只建立内部 refresh write seam，不调用新的 Riot/OP.GG/LLM 或公开 refresh POST。
- SSE 只包装 8C durable event cursor，支持 Last-Event-ID、有限连接和 keepalive；不复制 Runtime Trace、
  不暴露 owner/worker/checkpoint/token/operation/body。四态由 task + Harness + evidence pure projector 统一。
- 当前只完成教学/ADR/design/implementation plan；下一动作是 pure-contract 红灯。React/Auth/HTTPS/backup/
  deployment 仍不在本批，8E coverage 保持 planned。

## 2026-08-23：Batch C 实施期补充裁决

- refresh idempotency 比较 validated bundle digest，不比较 retry request 的 `stored_at`；首次 committed
  timestamp 属于 immutable snapshot，稍后同内容重试必须 replay，不能误报 conflict。
- JSONB tamper 测试必须 deep-copy nested value 或使用明确 SQL mutation，确保真的发出 UPDATE；浅拷贝造成的
  ORM no-op 不得冒充 read-time digest 证据。
- `app.api` convenience export 改为 lazy，SSE frame 在 task 层使用与 `TaskEventResponse` 等价的显式
  allowlist；拒绝 task/evidence→API→composition 的 import-order cycle。
- Product GET 只读已物化 snapshot，绝不 reconstruct-on-read 调用 Riot/OP.GG；自动 refresh scheduler、
  Auth、前端、备份和生产连接容量仍不在 Batch C。

## 2026-08-23：Batch C 公共关闭与 Batch D handoff

- implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions `32629160732`
  已完成 exact-SHA 三 job：公共 pytest 1750、真实 PostgreSQL 194、Linux package schema 1.6；0011
  可逆迁移、metadata=head、外部调用 0 与非 root/image boundary 均有公共证据。
- 因此 Batch C 可以关闭；该结论只覆盖 Evidence snapshot/Product API/cursor SSE 后端接缝，不等于整个
  8E、正式前端、Auth/RSO、HTTPS、backup/restore、生产长连接容量或部署已完成。
- 下一内部批固定为 Batch D 静态/fixture-backed 前端设计门，当前 prepared/waiting authorization；
  先做信息架构、状态矩阵、可访问性与外部视觉资源采用审计，授权前不创建 React 代码。

## 2026-08-23：ADR-0061 采用 Rift Command Center 与两层多来源视觉门

- RQ-091 已授权 Batch D，并要求 MotionSites 只作候选池；素材/Prompt 站、组件/动效库、成熟产品、
  游戏数据界面与 Riot/LoL 官方视觉语言必须进入同一 rubric，最终自主重构。
- RQ-092 明确采用约束不是过度简约的理由。许可、状态真实性、键盘/reduced-motion、移动降级与性能
  是硬门；所有过门候选继续按视觉完成度、时尚感、品牌记忆点与 LoL 语义择优。
- 三案比较采用近期复盘工作台优先的 `Rift Command Center`；电影感入口保留为后续高影响叙事，完整
  Timeline 因当前缺少公开 DTO 而 deferred。
- 首批采用 React/Vite/TypeScript、vanilla CSS tokens、Motion、Radix Dialog 与本地 OFL 字体。React Bits、
  Aceternity、MotionSites、Riot UI 和游戏数据产品只作机制/信息架构参考；不复制受限源码或品牌美术。
- Batch D 只实现安全 fixture screen 与桌面/移动/键盘/reduced-motion 证据；真实 API/SSE/Auth、HTTPS、
  备份、部署、公网发布和完整 Timeline/历史列表不在本批。

## 2026-08-23：Batch D 实施期合同修正与 RQ-093 连续性裁决

- API 审计确认 `RecentSummaryView` 当前只有聚合 Summary；设计中的逐局 match capsule 在实现前删除，
  改成无顺序胜负占比、Wins-vs-Losses 聚合和主位置/英雄标签，避免 fixture 伪造历史/Timeline。
- 档案 selector 切到 observed 时，不把 self 的 Summary/report 重新绑定到新标题；页面改为明确的只读
  observation surface，个人 Training completion 不出现。
- tablet 断点由单一 900px 改为 `>=1280` 三栏、960–1279 主区 + context 两栏、`<960` 单列；人工
  screenshot QA 又修复 Evidence control 被 grid 拉伸的问题。
- RQ-093 的 session-logs/focused export 回查确认五模块仍完整保留。Batch D 只先完整交付近期工作台，
  并用 Evidence/Training 薄纵切验证共享系统；电影感入口、Rift Timeline 和 8F README 没有被取消。
- 当前无 SSR/复杂路由消费者，因此用 Vite/vanilla CSS 取代旧提案的 Next.js/Tailwind；Motion/Radix
  因有直接用途采用，ECharts/Image2/Photoshop/Anime.js 按入口/Timeline 的未来真实消费者保留。
- 用户质疑第一版研究深度后，没有用既有截图直接关闭 Batch D；第二轮以 8 组 AutoGLM、35 站扫描、
  MotionSites live Apps 和 Riot/Langfuse/TrainingPeaks/Mobalytics/21st.dev/Aura 深读建立五模块采用矩阵。
  采用收益只落为 Evidence Drawer 的 body-free Safe Run Path；其余候选绑定未来真实消费者，不为证明
  “广撒网”而安装库或购买 Prompt。

## 2026-08-23：Batch D 公共关闭与真实数据接线 handoff

- implementation/evidence `f7ebedd7c6cfd135201847a327dfd06c01cc7205` / Actions `32636771507`
  已完成 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job；公共 pytest 1752、真库 194，
  frontend unit 35/e2e 12/typecheck/build 与 Linux package schema 1.6 同 SHA 通过。
- 因此 Batch D 静态/fixture-backed 产品纵切可以关闭；8E coverage 仍 `planned`，且不把静态 screen 写成
  已接真实 API/SSE/Auth、已部署或五模块全部实现。
- 下一步只进入真实数据接线设计门：复用 Batch B/C owner-scoped profile/product/evidence/SSE DTO，先补清
  Summary/report HTTP projection 和 decoder/重连/错误合同。Auth/RSO、部署安全、电影感入口、完整 Timeline/
  Training 与 8F 均不随 Batch D 自动进入。

## 2026-08-23：RQ-094 恢复最终视觉组合与两个未结 Core 目标

- 旧日志中早期 `Hextech Analyst Console / Esports Broadcast Lab / Coach Film Room` 是初稿；后来经用户
  纠正形成的最终三方向是 `Rift Awakening`、`Esports Intelligence`、`Void Holographic Lab`。Batch D 的
  Command/Cinematic/Timeline 三案只决定施工顺序，不能覆盖最终视觉职责。
- 采用 `Cinematic Portal → Broadcast Workbench`：入口承担作品集级电影感，工作台保留统一画风但让动效
  服务数据理解；Void 只允许 Hero 级实验。`Hextech Tactical Editorial` 是共享 design language，
  `Rift Command Center` 是工作台首个纵切。
- 每 checkpoint 关闭给一次问题/取舍/数据流/证据/限制/下一步短复盘；连续 checkpoint 再给批次总复盘。
- Stage 7 V1 不重开，但当前只产品化 lane-meta。8F 前新增 OP.GG useful-breadth gate，最低候选为 champion
  analysis 与 lane matchup，synergies 按阵容消费者；不为数量接满目录工具。
- 8D no-I/O typed fusion 与现有 live `degraded/unjoined` bundle 不等于完整真实纵向。8F 前必须至少一次实际
  覆盖 Riot match、Data Dragon、official patch、OP.GG、个性化 Training advice 与 live UI Evidence；允许
  诚实 degraded，但不得缺来源仍声称完成或覆盖旧负面证据追绿。

## 2026-08-23：ADR-0062 采用薄 latest locator 与客户端组合式 Live Workbench

- RQ-095 只授权当前设计门。三案比较拒绝单一 `/workbench` 大 BFF 和 URL/localStorage-only 身份，采用
  owner-scoped profile→latest review locator，加现有 task/run/product/evidence/training/SSE API 客户端组合。
- 后端补 `/runs/{run_id}/recent-summary`，Evidence HTTP projection 改为 typed nested schema；不改变 storage
  JSON、增加聚合表、cache 或 migration。
- 前端 `unknown wire → exact decoder → identity assertion → view adapter → React`；切 profile 先 abort/close/
  clear，再以 generation/profile/task/run 四重 guard 接收结果。每 task 最多一个 EventSource；transport
  reconnect 不改 Product State。
- verified report 只按 restricted Markdown 显示，不猜 verdict/strength/priority；Training 只显示后端可推导
  的 baseline/current/target/trend/sample count。observed 不请求个人 Training。
- 当前只完成设计与计划，不安装 npm、不写产品代码、不调用外部服务；设计 exact-SHA 公共门成功后才交接
  implementation prepared。

## 2026-08-23：Live Integration design 公共关闭

- design `4057c93f4ac1ac9ebd181528e559b084e3425e89` / Actions `32639561338` 的 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest 1752、真实 PostgreSQL 194，
  frontend unit 35/e2e 12/typecheck/build 与 Linux package smoke 同 SHA 成功。
- 该公共证据接受 ADR-0062/design/implementation plan 与 RQ-094 治理同步，不表示 locator/API/frontend
  已实现。live integration implementation 只交为 prepared/waiting authorization；8E coverage 继续 planned。

## 2026-08-23：RQ-096 Live Integration 实施裁决

- 实施保持 ADR-0062 的 thin locator + existing APIs client composition；不增加 BFF table/cache/query framework，
  不把 component 变成 HTTP/SSE parser。
- browser unknown input 必须先 exact decode，再经过 generation/profile/task/run binding；late response/event、
  cross-binding、bad enum/time/digest/extra key 均 fail closed。SSE transport 不改 Product State。
- `react-markdown@10.1.0` 因 production JS gzip 156.52 kB 超过 150 kB 硬门而不采用；当前使用 React 原生
  escaped plain text。该路径不执行 HTML/link/image，也不宣传为完整 Markdown renderer。
- native fetch receiver 采用 `globalThis.fetch.bind(globalThis)`；默认网络只允许 same-origin `/api` client 和
  task EventSource。fixture 仅在显式 `?scenario=` 使用，live/fixture rail 必须如实标识。
- package smoke 必须在 review task running 时写 Evidence，随后 no-I/O executor 可安全失败；不得放宽
  `PostgresEvidenceSnapshotRepository` 的 running/succeeded-only write invariant 追绿。
- locator route 插入后必须保留既有 `/player-profiles` generic exception→body-free 503 映射；提交前 diff
  审查发现并以 RuntimeError 红灯修复了异常分支错位，不能只依赖 happy-path/OpenAPI 绿灯。
- HTTP body 上限必须在流读取期间执行；不能先 `response.text()` 全量缓冲后才检查。无 Content-Length
  response 超限时立即 cancel reader，并保持错误 body 16 KiB、JSON 2 MiB、report 1 MiB 三种限额。
- profile selection 无论候选是否合法都必须先开启新 generation、abort 旧请求并关闭旧 EventSource；URL 的
  `player_profile_id` 只可作为 owner-scoped server profile list 的 initial candidate，不能指定 task/run。
- 本地验收为完整 pytest 1939、真 PostgreSQL 200、frontend unit 66/e2e 17、JS gzip 122.01 kB、Linux
  package schema 1.6 与横向门全绿；公共 exact-SHA 三 job 成功前只称本地完成。
- 整个 8E coverage 保持 planned；Auth/RSO、部署、电影感入口、完整 Timeline/Training、OP.GG breadth、
  fusion golden slice 和 8F 均不并入本批。

## 2026-08-23：RQ-096 Live Integration 公共关闭与 Batch E 交接

- implementation/evidence `f441061e7444fa6d1d3c213b81e05a02f0fc68c5` / Actions `32647933692`
  的 pytest/PostgreSQL/Linux package 三 job 全绿；RQ-096 正式关闭，既有安全/性能取舍不再只是本地证据。
- 整个 8E coverage 继续 planned，不能因工作台接真数据就声称 Auth、部署或五模块完成。
- preflight 的下一批是 Batch E，但其范围过宽，先固定为
  `8e-batch-e-security-deployment-entry-design`：比较身份/RSO、部署拓扑、CORS/CSP/HTTPS/限流、Secret
  生命周期、backup restore/erase、隐私、观测和剩余五模块施工顺序；设计公共关闭前不实现或配置外部系统。
- OP.GG useful-breadth 和完整 fusion→Training→UI golden slice 继续是 8F 前硬门，不被 Batch E 入口设计吞并。

## 2026-08-23：RQ-097 冻结 Batch E 安全/部署入口设计

- ADR-0063 采用 provider-neutral AuthPort + server-side opaque session；RiftCoach Auth 产生 owner，
  Riot RSO 仅作为未来 `verified_self` 关系证明，不能替代产品登录或把 Riot ID 输入当归属认证。
- 首个公开拓扑采用 edge/static Web + API/Worker/PostgreSQL 单机 Compose；托管 PostgreSQL 是迁移路径，
  Kubernetes/Redis/Celery/Kafka deferred。生产 API 同源 `/api`，CORS/CSP/HTTPS/限流/安全响应头按后续 E2 批次实现。
- 6B-9 deletion marker 必须扩展到 Artifact/backup restore erase replay；RPO≤24h/RTO≤2h 是待演练目标，
  不是当前 SLA。Secret 不进浏览器、DB、Artifact、Trace、日志或 backup。
- 冻结后续 E1 Auth → E2 edge security → E3 Secret → E4 backup/erase → E5 packaging/observability，
  再施工 Rift Awakening、Timeline、Evidence/Trace、Training、OP.GG breadth+golden slice 与 8E exit。
- 当前只完成设计/教学/coverage 路径，8E 仍 planned；不读取 Secret、不调用外部服务、不实施产品代码。

## 2026-08-24：ADR-0064 Portal → Workbench 视觉合同

采用 `Rift Awakening / Cinematic Portal → Esports Intelligence / Broadcast Workbench` 作为 8E 前端融合方向；
`Void Holographic Lab` 限制在 Hero 实验。入口使用抽象 Rift 环境、身份校准核心和路线点亮 handoff，工作台
复用几何/材质/状态语言但优先数据可读性。Image2/Photoshop 只做可替换 preview/氛围层，CSS/SVG/React 才是
真实 UI、数据和交互事实源；默认不引入 Three/GSAP/第二动画栈或购买 Prompt。该项不改变 canonical stage order，
不关闭 8E，也不授权 Auth/RSO、部署或外部调用。

## 2026-08-24：RQ-098 Task 3 polish 与 Batch E implementation 本地边界

- 视觉 Task 3 通过本地门：instrumentarium 只作低对比可移除的 soft-light atmosphere layer；CSS/SVG/React
  继续拥有 route、Core、状态和真实交互，避免机械 overlay 喧宾夺主。路线只在 calibrating 流动，ready/
  degraded handoff 是一次性过渡，reduced-motion 关闭连续动效。
- E1 的 HTTP session seam 采用 opaque Secure/HttpOnly/SameSite cookie；session service 解析 owner，所有写
  请求在启用 session 时要求同 session CSRF。没有绑定 Auth/RSO provider 时 `/auth/session` 返回
  `auth_unavailable`，不把 Riot ID 或请求 body 当认证。
- E2 的 request budget/header/body/单机 IP limiter 是 edge seam；E3 的 SecretSource 只在 Worker DB readiness
  后解析 key 并构造 Riot/LLM client。环境注入仅为 local/test fallback，真实 Secret Manager、多副本 rate
  store、PostgreSQL session repository 与 backup/erase 不随本地实现被宣称完成。

## 2026-08-24：RQ-099 E1/E2/E3 公共关闭与 E4 交接

- `92b768591183e8a7fbe6d12a86359aac862b7efb` / Actions `32658277570` 的 pytest、PostgreSQL migrations、
  Linux packaging-smoke 三 job 全绿，E1/E2/E3 的实现与八维材料取得 exact-SHA 公共证据。
- 该关闭只覆盖 session/CSRF、请求预算/单机 rate、SecretSource/key-last composition；正式 OIDC/RSO、
  PostgreSQL session repository、真实 Secret Manager、HTTPS edge、多副本限流和 backup/erase 仍未完成。
- 按冻结顺序下一项为 E4 backup/restore/erase，先用红灯冻结 restore replay、erase-before-ready 与 partial
  failure compensation，再实施；不进入 E5 或 8F。

## 2026-08-24：RQ-099 E4 owner erase / restore 本地实现

- E4 采用 body-free `BackupManifest`：只记录 deletion-marker 元数据和 deterministic digest，
  `encryption=external_kms_required` 明确要求后续外部 KMS/对象存储适配器；不把普通 JSON 冒充加密备份。
- `PostgresOwnerDataLifecycleRepository.locate()` 按 marker 的 owner + conversation/relationship identity
  只读返回 run 引用；`OwnerRunArtifactTraceCleaner` 在 SQL marker 提交后复用 `FileRunDataCleaner` 清掉
  对应 Artifact/Runtime Trace 目录。跨 owner、错 target 或清理失败均 fail closed，marker 保持 pending。
- restore 先校验 marker digest、再 replay deletion markers、最后通过 readiness；幂等 replayer 对已应用 marker
  不重复执行，并且补偿只撤销本次 restore 新应用的 marker。
- 本地 focused/相邻 lifecycle 为 `31 passed`；该记录不关闭 E4，仍待真实 PostgreSQL locator/migration、
  Linux package smoke、八维材料、独立提交和 exact-SHA 三 job 公共 CI。RPO≤24h/RTO≤2h 仍是待演练目标。

## 2026-08-24：RQ-099 E4 公共关闭与 E5 交接

- `27b9256b8987ade45fbc9eb5f62497cbaef9f518` / Actions `32660145945` 的 `pytest`、`postgres-migrations`、
  `packaging-smoke` 三 job 全绿，E4 正式关闭。
- 公共证据同时确认 owner erase locator/Artifact-Trace cleanup、restore marker replay/幂等/readiness
  compensation、真库 migration 与 Linux package boundary；E4 仍不包含 KMS/对象存储或 RPO/RTO 实测。
- 按用户连续授权进入 E5 packaging/observability：先以 red tests 固定 migration order、health/readiness、
  rollback 和 body-free structured observability，再决定最小实现；不因为“可观测性”引入未经 Bad Case/ADR
  论证的 Redis、Kubernetes 或第二套 metrics runtime。

## 2026-08-24：RQ-099 E5 metrics projection 本地首批

- E5 采用 `TaskObservability.emit()` event counters + `public_snapshot(max_samples=1000)` latency bound，
  由 `GET /health/metrics` 返回 typed p50/p95 projection；不会暴露 owner、Prompt、Report、Riot ID、Secret
  或原始事件 body。
- 继续使用现有 Compose migration order、`health/live`/`health/ready`、non-root image 和 no-I/O package
  smoke；rollback 先以旧镜像/兼容 migration/ready gate runbook 证明，不承诺自动回滚或 HA。
- 当前只完成 focused 本地实现，等待完整回归、独立提交和 exact-SHA 公共 CI；不引入 Prometheus/Redis/
  Kubernetes/第二套 metrics runtime。

## 2026-08-24：RQ-099 E5 公共关闭与 production shell 交接

- `ca6da44be439b0020f231dc0c00d6a70322e723c` / Actions `32661425379` 的三 job 全绿，E5 正式关闭；
  bounded `/health/metrics`、Compose/readiness、真库 migration 和 Linux package boundary 取得公共证据。
- 下一项是 remaining product modules 的 production shell/Auth gate：先把现有 opaque session/CSRF seam
  投影为未登录/加载/过期/拒绝 UI 状态，再独立评估 OIDC/RSO；local/test session 与 Riot ID 输入不等于
  production authentication。
- 入口仍沿用 `Rift Awakening → Esports Intelligence` 视觉合同，机械 atmosphere 层不能改变安全状态事实。

## 2026-08-24：Production shell/Auth gate 本地闭环与视觉 polish

- 视觉 Task 3 根据真实 desktop/mobile 截图完成一轮收敛：instrumentarium 只作为低对比可移除层，
  route/core/panel 光效服务于身份校准和 handoff；未增加第二动画引擎或远程素材。
- Live 默认路径现在是 `ProductionShell → AuthGate → LiveWorkbenchController`。session 未成功时不启动
  controller；`auth_unavailable`、`auth_session_expired`、`auth_session_revoked`、
  `authentication_required` 保持 body-free 且可审计。
- fixture/awakening preview 是明确的本地预览边界，不是 production auth；CSRF token 仅内存保留以供后续
  mutation seam，OIDC/RSO、真实 session repository、HTTPS edge 仍须独立 adoption gate。
- production shell/Auth gate 已由 `15a3a9e` / Actions `32663345737` 完成 exact-SHA 公共闭环；下一项保持
  `Timeline DTO/UI`。时间线必须有真实 DTO/fixture boundary、缺失/部分语义和 source posture，不能用视觉
  series 冒充数据；8E coverage 仍 planned。

## 2026-08-24：RQ-102/104 双语表面实施裁决

- 采用 zero-dependency typed `zh-CN|en` catalog、strict V1 localStorage、navigator/English fallback 与共享
  locale control；切换只重渲染 copy，不重取 API、重连 SSE、改 profile/Product State 或写 Memory。
- UI copy、Data Dragon locale、Coach/Training Artifact language 继续是三个合同。Report/Plan 保留原文；浏览器
  不机翻已经 Harness 验证的内容。
- Workbench 不再显示 `MIDDLE`、Training metric key、Evidence gap/error code、`RSO verified`、`Match-V5`
  transport 名称或 fixture/test 场景术语。地区下拉使用 routing 覆盖长名，卡片使用自然短名；未知 code 使用
  bounded generic copy，不回退 identifier。
- 最新 production build JS/CSS gzip 为 `142.68/18.50 kB`，JS 仍低于 150 kB 硬门；没有新 i18n/animation runtime 或 npm 依赖。

## 2026-08-24：RQ-105/106 三层旅程与母图分层实现裁决

- ADR-0067 取代“默认 AuthGate”与“Portal 内身份表单”：默认 `/` 为零 API/SSE Portal，激活唯一核心后才进入
  Account；session + owner-scoped profiles/Player Link 成功且用户明确选择后，才进入 live Workbench。
- URL/history 只接受 `portal|account|workbench + UUID`；非法/未列 profile fail closed。Account/Workbench
  卸载时 abort/dispose，session failure 回到 Auth boundary；heading focus 随层级交接。
- Player Link 使用 same-origin bounded POST、内存 CSRF、新 idempotency key、严格 queued/running/succeeded/
  failed decoder、有界 poll、generation/abort、terminal profile refresh；202/pending 不冒充成功。
- 母图先派生无文字/UI 的 keyframe，再精确移除烘焙核心/beam 形成 runtime background；React core 是唯一
  clickable/focusable 真值。旧 aperture 只作失败 fallback，旧 instrumentarium 已移出 public runtime。
- 正常模式使用 bounded scene reveal 与 720ms handoff；reduced-motion 立即进入且冻结装饰动画。当前只是 V1
  choreography，不等于最终电影化 Portal 或 RQ-103 final visual QA。
- 最新本地验收为 frontend unit 136/Playwright 36/JS gzip 142.68 kB、完整 Python 1982/1 skip/127 subtests、
  真 PostgreSQL/Alembic、RAG/Harness、npm audit/安全治理与隔离 Linux package 全绿；implementation/evidence
  `6084937` / Actions `32757872792` 又完成 exact-SHA 三 job，foundation 正式公共关闭。

## 2026-08-24：RQ-107 Coach Agent 产品缺口（待用户裁决）

- 当前 Web 是 recent-review viewer：Coach 只显示 published report，Training 只读 active Plan/Progress；前端
  没有调用 Conversation/Message/conversation review create，因此不能说用户可从网页启动 Agent 或追问。
- 后端已有 Conversation、user Message、conversation-bound Recent Review→AgentRuntime/Harness→SSE、
  terminal assistant exactly-once、Memory-aware Context 和 Training Candidate/accept，可复用而不另造聊天 Runtime。
- 推荐在当前批公共闭环后、RQ-103 前插入 8E 内部 `review-grounded-bounded-coach` 原子项：专用 follow-up
  Skill/Prompt/eval，严格 source run/relationship 绑定，生命周期 SSE + terminal whole reply；开放域 LoL chat、
  token streaming 与自动长期 Plan 写入 deferred。
- 该插入会调整既有子项顺序。用户尚未对 bounded/open-domain、插入位置、observed study plan、token streaming
  和 Conversation UX 五项作集中裁决，因此只记录缺口与推荐，不修改 canonical 下一检查点。
## 2026-08-25：RQ-108 Portal Motion Polish 顺序与表现边界

- RQ-102/104/105/106 bilingual/product-journey foundation 已由 `6084937/32757872792` exact-SHA 公共关闭；
  用户随后按 RQ-109 授权 RQ-108，当前为 authorized/in progress。
- 固定先进入 8E 内部 `portal-motion-polish`。它不新增主阶段/coverage group，只取代 Portal Task 3
  作为最终视觉/动效验收；zero-early-I/O、三层旅程、语义 hit target、keyboard/focus、history、
  reduced-motion 与失败 fallback 的既有功能证据保留。
- 本句记录早期 RQ-108 方案，水晶放大/重绘细节已由 RQ-118 取代：确认母图原水晶、塔体和构图保持不变；
  透明原生 `<button>`
  只覆盖水晶点击区，不显示独立贴图或常规按钮。提示只用融景微光点/短脉冲，激活后执行汇聚、一次 burst
  和独立 Account 动态场景幕切。
- 任何视频/ambient media 都必须同源版本化，并有 poster/codec、mobile safe area、Save-Data、
  reduced-motion、播放/解码失败、下载/解码/JS 预算、许可和移除门。不热链、不复制付费素材；Three/OGL/
  Anime 等新 runtime 没有新的 Bad Case/ADR 时不采用。
- RQ-108 不实现 Coach、OIDC/RSO、Data Dragon asset/detail enrichment 或跨模块 final visual QA；RQ-108
  关闭后再裁决 RQ-107 与 RQ-103 的相对顺序。

## 2026-08-25：RQ-110 至 RQ-118 Portal/Account 素材与地图裁决

- 本节原始裁决的 v1 SHA `552a874...aada` 仍作 archival parent；RQ-124 后 active source master 已迁移为
  轻清噪 v2 SHA `8134c0ca...1a06e`。旧暗图、aperture、keyframe、大标题、
  CSS/贴图水晶、filter/vignette/blur 均是 anti-reference，不进入最终 poster/loop/fallback。
- Portal 与 Account 正常体验都必须是全帧全局 loop；poster 只服务首帧、reduced-motion、Save-Data 和媒体
  failure。媒体 policy 两个分支都携带 viewport，播放失败进入 session-sticky poster。
- Account 固定 Camille/Kindred/Ahri/Jinx/Thresh 五个场景原生全身回响；一次性群像、splash 抠图换色、
  畸形人物和通用机械底座均拒绝。先验收无英雄底座，再逐英雄验收、合成和 loop。
- RQ-117 取代伪写实追求：map11 与 Riot 2024 near-final concept 锁定三路、河道、双野区、双坑、基地、
  朝向和红蓝方；森林/岩壁/墙体/塔只用 terrain masses、轮廓、材质区和符号节点概括，禁止生成无法由公开
  参考证明的微型细节。当前 v3 是未签收 preview，不得进入英雄层或 runtime。
- RQ-118 取代早期“重绘/调大水晶”：确认母图的原水晶、塔体与构图保持 source truth，只在全局 loop 与
  点击 burst 中让原水晶运动；放大 edit、独立/CSS/贴图水晶不得进入任何发布路径。
- archival PNG 逐字节保留；runtime poster 可做同源感知压缩，但必须绑定 source SHA、通过 SSIM 和人工原
  尺寸审查，不能用暗化/模糊换体积。

## 2026-08-25：ADR-0068 design gate 本地裁决

- 采用 typed manifest → viewport-aware media policy → poster-first playback → ProductJourney-owned activation，
  拒绝 CSS-only 假全局动态和无 Bad Case 的 WebGL/第二动画引擎。
- ADR、正式 design、详细 TDD implementation plan、asset ledger 和八维 planned walkthrough 已建立；本批
  没有 `web/` runtime 修改、正式 loop adoption 或外部产品调用。
- 唯一下一动作是 design 独立提交、push 和 exact-SHA 三 job；公共成功后才执行 runtime TDD。

## 2026-08-25：RQ-119/120 视频制片路线裁决

- 用户 Kimi v1 是有效 12s/1080p 视频而非播放故障，但 source→首帧 SSIM `0.412818` 且人工构图、纹理和
  motion language 不通过；只作为 rejected Bad Case，不以新 Prompt 盲目补跑。
- A 线比较 Wan/Seedance/Veo/Luma/Runway/Firefly 等 first/last/reference I2V；B 线比较 HyperFrames/
  Remotion 分层 frame render；C 线以生成式有机 plates + 确定性建筑/水晶/拓扑合成为推荐候选。
- HyperFrames 的 Apache-2.0、seekable HTML 和成熟主 skill 支持优先隔离 spike；Remotion 保留 React 对照但
  需复核 source-available 许可。任何 skill 安装、credits/Key/付费调用前另行安全、费用与凭据门。

## 2026-08-25：RQ-108 design 公共闭环

- `b3b5280/32812868683` 的 pytest、真实 PostgreSQL 与 Linux package 三 job 全绿；ADR-0068、RQ-117–120、
  provenance/I2V audit/详细 TDD plan 获公共设计证据。
- 下一动作仅为 runtime Task 1 manifest/cover geometry/media policy 红灯；production asset 与外部视频工具仍未采用。

## 2026-08-25：RQ-121 中转站只作 secondary transport

- 官方 API/Console 保持优先。用户正规中转目录可参加后续 bake-off，但 model slug、`official` 后缀和价格只
  是目录证据；必须先验证映射、first/last/reference、压缩/水印、隐私/删除、地区、错误/重试/计费和调用上限。
- 本裁决不安装 skill、不配置 relay、不上传母图、不创建 Key、不调用模型，也不改变当前 runtime Task 1。

## 2026-08-25：RQ-108 runtime Task 1 本地裁决

- strict schema 1.0 manifest + exact 4-rendition matrix、pure cover/focal/hitBox geometry 和 viewport-aware media
  policy 已完成；首个 commit 固定 poster/preflight，订阅后才允许 motion，避免偏好竞态触发视频请求。
- focused 71、frontend unit 207、typecheck/build/bundle 全绿，两轮独立复核 blocker/major 0；无生产 manifest、
  asset、video、network/storage/model call。下一动作只做独立提交与 exact-SHA 三 job。

## 2026-08-25：RQ-108 runtime Task 1 公共裁决

- implementation/evidence `1b146e6` / Actions `32826953474` 三 job 全绿，Task 1 strict manifest/geometry/
  preflight policy 正式关闭。
- 下一裁决面只限 Task 2：page-session playback state、poster-first component、sticky failure 与 user pause；
  production media/模型/relay 采用仍留 Task 5 独立门。

## 2026-08-25：RQ-108 runtime Task 2 本地裁决

- `mediaSession` 采用 controlled semantic events；`CinematicSceneMedia` 只在 motion policy 且非 sticky failure
  时挂载视频，poster 永远先渲染。当前有效 attempt 才能改变状态，旧 Promise/DOM 事件、暂停中止和 StrictMode
  cleanup 全部 no-op。
- 聚焦 `39 passed`、frontend `246 passed`、typecheck/build/Playwright `36` 全绿；当前只待独立提交与公共 CI，
  不接 App、生产素材或视频模型。

## 2026-08-25：RQ-108 runtime Task 2 公共裁决

- `2111a78/32833608622` exact-SHA 三 job 全绿，Task 2 `mediaSession`/`CinematicSceneMedia` 公共关闭。
- 下一裁决面只限 Task 3：单次激活 latch、reduced-motion、generation/跨幕 overlay 与唯一导航；生产 media/
  视频模型/relay 采用仍留后续独立门。

## 2026-08-25：RQ-108 runtime Task 3 本地裁决

- Portal 激活由 `ProductJourney` 持有 timer 与 navigation latch，`AwakeningScene` 只发 semantic activation intent；
  overlay 跨 Portal→Account mount，generation 使迟到 timer/popstate/StrictMode no-op。
- 聚焦 `27 passed`、frontend `257 passed`、typecheck/build/Playwright `36` 全绿；当前只待独立提交与公共 CI，
  不接生产视频、Account source 或视频模型。

## 2026-08-25：RQ-108 runtime Task 3 公共裁决

- `0198fc9/32836430378` exact-SHA 三 job 全绿，单次 activation/overlay/focus/navigation seam 公共关闭。
- 下一裁决面只限 Task 4：只读媒体审计器与预算门；production media、HyperFrames、视频模型/relay 仍不采用。

## 2026-08-25：RQ-108 runtime Task 4 本地裁决

- 只读 `check_cinematic_media.py` 采用 planned/adopted manifest 两态：planned 只验证合同和固定策略，不读取
  媒体；adopted/fixture 才验证 local digest/bytes/ffprobe/provenance/预算。CLI 固定 PATH `ffprobe`，不接受任意
  可执行路径；SSIM/seam/dropped-frame 作为显式测量证据，不伪装成 ffprobe 自动推断。
- 聚焦 `25 passed`、frontend `257 passed`、Python no-DB `1862 passed, 146 skipped, 1 warning, 127 subtests`、
  RAG/Harness/compile/governance/npm official audit 全绿；Task 4 仍待独立 exact-SHA 公共门。

## 2026-08-25：RQ-108 runtime Task 4 公共裁决

- `52def9c`/`d58ba15`、Actions `32841900909` 三 job 全绿，媒体审计器/预算门公共关闭；`32841579832` 的 ffprobe
  缺失失败作为环境 Bad Case 保留，CI 只补安装 ffmpeg。
- 下一裁决面只限 Task 5 三路线 bake-off；没有 adopted asset 前，不把模型/skill/relay 变成生产依赖。

## 2026-08-26：Task 5 Wan/Veo 样本与 RQ-125 裁决

- Wan 与 Dragon/Veo 各执行一个有界真实样本，均因 source/seam/full-scene motion 等硬门 rejected；external
  video calls 为 2，production media 为 0。Veo raw output 另因 yuv444p/254MB/预算拒绝，兼容转码不改变裁决。
- Dragon `metadata.lastFrame` 字段经专用文档复核正确；`/content` 对成功 task 403 是 transport Bad Case，
  query result URL 已恢复同一 output，没有第二 POST。
- 当前冻结 prompt 重述源图并用多个 subtle/slow/restrained 词，未充分遵守 Google official motion-only I2V
  guidance。因此裁决是 sample reject/provider open，禁止把负面样本冒充模型上限。
- C 线优先做 no-paid-call layer/mask/inpaint + deterministic frame-clock proof；只有自然整幕 motion、source/seam
  与维护成本过门才采用。失败时重开一次短 motion-only、首帧控制 + deterministic seam 的 A comparator。

### RQ-126 C overlay proof 结果

- proof 的 raw clock/source、encoded seam、3×3 motion coverage 与 3.90MB 编码均可控；这只证明制片工具链。
- 用户审查确认 v2/v3 仍是母图上叠加诡异线条、圆环、节点，不是图和环境自身的全局运动。人工目标优先，
  verdict 为 `proof_fail_reopen_corrected_a`。
- tracked contract/composition/renderer 保留为负面证据，不接 runtime；下一项恢复一次 corrected A comparator，
  first-frame only、short motion-only、medium full-scene environmental motion，seam 后处理。
- RQ-127 要求 motion 不是三主体轮流或 grid 有变化，而是整幕 breathing：near/mid/far 空气与大尺度光影、
  建筑/地面/反射、道路、Rift、水晶和整片星空同时持续参与；允许锚定构图的小幅 camera float/parallax，
  amplitude 必须 clearly perceptible/cool，不再使用 subtle/almost-imperceptible wording。

### RQ-128 Failure adjudication

- Failure attribution 固定为 local client → request/schema → relay/upstream → successful-output quality → cross-sample
  method。无 output 不评模型质量；单个 Bad Case 不自动否定路线。
- Vidu 是保持 transport/source/motion/first-only、只改变 schema/model 的 comparator。它若 generic failed，下一步
  是 relay/request audit；它若 completed 才进入 visual gate。Veο 和 first-only 方法当前未被拒绝。
- Vidu 首个 task 后续也 generic failed。Studio 登录态证明 first-only/8s/1080p/16:9、音频固定 true；只允许
  一次删除 seed、audio=true 的 Studio-contract request 作为参数映射假设。若仍失败，停止模型/API 切换，
  转 relay/upstream/official transport 诊断。

### RQ-129 Vidu sample 与 refined locked-scene

- Studio-contract Vidu 成功，证明 API/first-only/prompt 可用；此前 generic failures 与参数/relay mapping 有关。
- 输出以 camera push/global drift 获得显著变化，source/seam/resolution provenance 失败；sample rejected/model open。
- 目标不是 Veo v1 简单加大，而是 locked frame 下的 multi-depth fog/occlusion、surface-following caustics、Rift
  layered fluids、route/reflection currents、crystal material light、tower seams 和 volumetric star field 同时精细运行。
- 下一实验保持成功 Veo first=last/model/transport/source，只改 storyboard；若仍不合格才进 Seedance 2.5。

### Veo refined submit 403

- refined Veo request 在 POST 阶段直接 403，task_id 为空；没有生成输出，因此质量保持 unknown。
- Dragon common log 已证实当时余额 `$15.008`、8 秒预扣 `$19.712`，故 403 是预扣失败；同时间重复 pipeline
  日志不是额外 task。充值后余额 `$65.01`，billing gate 已满足。
- RQ-130 决定余额不能替代内容 preflight。v5 必须先以 official motion-only、单一连续镜头、locked/deep-focus、
  全空间 simultaneous motion、八秒闭环、negative phenomena、source/schema/runner/唯一输出门完成公共闭环。
- 只有 exact-SHA 三 job 成功后才 one POST/no retry；不自动重抽或换模型归因。

### Veo spatial v5 上游失败

- `d57b026/32951125621` 三 job 全绿后才创建唯一 task `task_I5...k9Mw`；159 秒/100% generic failed，无 output。
- 按 RQ-128，relay/upstream failure 是唯一可证实层；v5 prompt、Veo output quality、first=last 与方法保持 unknown/open。
- `$19.712` 已全额退款；不重发同一 v5，不因此直接切 Seedance/Grok。
- 本地终端误关是独立操作事故，影响轮询体验但没有创建第二 task；后续 Key runner 禁止按窗口句柄猜测并关闭。
- audit 已由 `ac76f74/32952793297` exact-SHA 三 job 公共关闭。下一决策门只允许零成本 task-id/platform
  diagnosis packet；代表用户联系支持仍需发送时确认，不能把“继续开发”泛化为对外沟通授权。
- 用户按 RQ-131 选择 Studio；QQ 视频管理员 support 草稿保持未发送。Studio 手动对照保持同一模型/source/
  first+last/8s/1080p/16:9，合并单框 prompt、enhancement off；最终 19.71 按钮只由用户点击。
- v5 Studio 同样 generic failed/no output；因此自写 API payload 不是必要根因。用户按 RQ-132 拒绝 QQ 并授权
  exact v1 reproduction：若成功，支持运动包络过重；若失败，支持当前 Veo 通道变化。任何结果都不重试。
- exact v1 也 generic failed，因此暂停当前 Veo 通道。Seedance 2.5 以 first+last + exact 8s 合同优先于
  Kling 10s 和 Grok first-only；但 Studio price `--` 必须与 catalog 预计 11.9568 一并披露后再获确认。
- Seedance ratio `adaptive` 修复后任务成功；Studio 403 只在结果拉取层。GET-only recovery 证明不需重生成。
  样本只升为 awaiting visual review candidate：三大区运动/camera lock promising，source identity/seam/720p 不过门。

### Seedance video edit v6

- 用户认可三主体运动方向但要求静区真实参与，选择基于成功成片的文档化编辑。
- Dragon 专用文档确认 `seedance-2-5` + `video_operation=edit` + `video_with_roles(reference_video)`，编辑用
  `duration=-1`/`aspect_ratio=adaptive`；Studio 主编排器视频参考 input 只接受图片 MIME，因此 edit 走 API。
- v6.1 改为 double-anchor：Video1 保留已有 motion，Image1 锁原几何/材质，只编辑热图静区，原片永不覆盖。
- prompt/runner SHA `9cdcf28e...64ac8` / `08834b8a...173b0`；预计约 `$12.0191`，必须先新 exact-SHA
  公共门，one POST/no retry。edited sibling 任一核心维度劣化即拒绝并回退原片。

### Seedance v6.1 submit 400 与官方 UI 候选

- source GET 成功、POST 在 task 创建前 HTTP 400；费用 0、task id 空、无隐藏 task，故不是模型/画质失败。
- 原 runner 丢失 response body；旧 ratio 400 不得代替。当前 decision 为
  `request_or_schema_rejected_before_task_creation / exact_field_unknown`。
- 采用 strict body-free sanitizer + revised runner 的最小诊断修复；公共闭环前不再 POST，公共闭环后也只有
  精确 error body 或可证伪字段修正才能重开 relay。
- 即梦官方 `智能编辑` 作为条件替代 transport：它直接支持 Seedance 2.5 单视频 edit + 多参考素材，UI 管理
  自动比例/时长。先不购买会员/API；只有上传后实际积分和参数读回、用户确认费用，再允许一次官方 UI edit。
- 豆包工作当前标准套餐作为更低现金成本的第二官方入口：只在读回剩余额度、Seedance 2.5 与附件角色后，
  才可用一次附件+prompt edit；因无即梦式显式智能编辑/全能参考/首尾帧模式，不把它视为逐字段等价替代。

### 豆包 comparator 退出与 RQ-134

- 实际 Skill 无 video-to-video，按首尾帧+母图进行一次 Seedance 2.5 image-to-video；只执行一次，现金新增 0。
- 输出 `e4b2f91...352cf` 因 source/seam/AAC/移动水印/暖金主导和整体 motion stack 不完整 reject；不重跑豆包。
- 保留“沿真实道路/结构接缝运动的光轨”思路，但下一版以冷蓝/青蓝为主，暖金只作结构强调。左 Rift、中央
  水晶/平台、尤其右星图/能量场都必须加强，并与建筑、反射、空气、云和星空整体同步；两组门缺一不可。
- 下一正式 candidate 改用即梦 `智能编辑` 真正视频编辑；文件选择由用户执行，Codex 负责费用/参数/prompt 门。

### 即梦 Smart Edit 素材与 v7 prompt

- 选择双参考最小集：成功 MP4 锁时间/运动/构图，v2 PNG 锁几何/材质/色彩；不生成更多审美图稀释 source。
- 若高级编辑可用，用区域框选表达左/中/右与静区；只有真实识别失败才新设计纯功能 motion mask。
- v7 prompt SHA `edbc0d3...6f388`，三主体尤其右侧 + 全局环境双硬门，光轨冷蓝/青蓝主色、暖金低占比。
- file picker 由用户执行；Codex 不盲点即梦页面，上传后依据截图/读数完成 readback。当前先独立公共门。

### 即梦 Smart Edit result 与 post-process 裁决

- 用户在 preflight batch public-close 前手动完成一次 official Smart Edit；该真实执行顺序保留，不倒写历史。
- 2,000 字上限使实际 main prompt 压缩为 SHA `d003f047...cff10`；长版 `edbc0d3...6f388` 只表示 design intent。
- raw SHA `4d3660b...155b` 保持 camera/大建筑并覆盖三大区/九宫格，右场不再遗漏；因此 official Smart Edit
  和 motion direction 保持 open。
- raw 仍因 mother-first `0.889072`、seam `0.046536`、AAC/non-fixed-fps 不准入。FFmpeg 可修 delivery contract，
  不能修 source identity；最佳 J seam `0.042684` 仍 fail。所有 media 留 repo 外，production media `0`。
- 不降低冻结阈值、不继续 xfade 追绿、不原样重抽。先 exact-SHA 公共关闭 audit，再拆 geometry/material 与
  intended light/energy 差异；只有新 source-side 控制合同才允许下一生成 preflight。

### Portal 与模型迁移顺序

用户复核 Agent 产品仍缺 bounded Coach、默认仍请求 GLM-5.2 且 GLM-5.3/Flash 已正式可用后，选择先完成当前
Portal。RQ-137 因此不改变当前 checkpoint：Portal evidence/identity/source-side/runtime/visual gate 完成后，
GLM-5.3/Flash adoption 才作为下一高优先横向批恢复；不能在当前未提交证据上同时改 Provider，也不能借此无限
延长视觉抽卡或声称 Agent 已收工。

### RQ-138：Portal motion direction revision

用户明确拒绝继续沿用当前视频的 burst/局部节奏，要求先重述并验证整幕持续呼吸的目标，再决定是否重生成。
本轮 AutoGLM 方向稿因重新绘制、风格漂移和水印仅作反例；Image2 编辑必须以确认母图为 edit target，保持
左 Rift/中央原水晶/右星场的几何和构图。即梦“全能参考”是多参考融合入口，不是严格 Video1 edit；下一次
校正 A comparator 采用首帧单锚点，首尾帧不作为默认模式，因为当前同图首尾实验同时暴露 source redraw、
阶段性 burst 和 seam 风险。Image2 代理不可达时保持等待，不改用未经用户选择的替代接口。
### RQ-139：Image2 预览不是调色验收

Image2 两张母图编辑稿经用户复核后只表现为亮度/对比度/蓝光变化，未证明裂隙、道路反射、水晶折射、右侧星图
和 near/mid/far 空气层的景内状态变化。故两张均标为 `direction-rejected`，确认母图仍是唯一 source；第三次
请求因余额不足不重试。下一次静态预览若继续进行，必须保持全局色调与几何，仅改变可供 I2V 理解的材质、遮挡、
反射和相位状态。
### RQ-140：skip Image2、prepare first-frame regeneration

用户允许跳过 Image2 静态稿，直接准备新视频生成。下一候选不沿用现有视频，不用首尾帧和全能参考，只把确认
母图作为首帧单锚点；prompt 改为短的正向 motion brief，强调 steady/continuous、三大区与 near/mid/far
同时运动，negative 只保留 camera drift、重绘、局部闪烁、雾层伪全局和交付破坏项。先完成页面参数、价格、
source SHA 和 prompt readback，再恰好一次调用；不自动重试。

### RQ-141：Seedance v3 视觉失败后的运动合同修订

Seedance 2.5 v3 的 12 秒 first-frame-only 输出已完成下载与逐帧复核。它证明 DragonAPI 请求、GET-only
恢复、编码和审查链可工作，但不满足 Portal 视觉目标：左 Rift 先形成硬同心环，道路流动直到中段才出现，
中央 burst 变成过曝白闪和横向穿屏直线，右侧在 burst 外近乎静止，near/mid/far 缺少持续呼吸，末帧也未充分
回到首帧相位。因此候选保存为 `research-candidate-rejected`，不进入 runtime，也不能据此否定 Seedance 模型。

用户纠正后，下一运动合同拆为两层：常驻基础层从首帧起持续驱动道路/Rift 下方、右侧星尘与地形、建筑接缝、
地面反射、云和空气；事件层只在中段约 2–3 秒沿中央垂直轴做低幅、平滑的蓄放，轻柔激发水晶并回到基线。
禁止跨画面直线网络、HUD 式线条、全局白闪、burst-only 右侧和用同心环代替 Rift 深度。未完成该 source-side
brief、循环相位和视觉门前，不再付费重抽、不静默切换模型、不接 runtime。

### RQ-141 v4 preflight 裁决（2026-08-27）

v4 采用“常驻基础层 + 中央局部事件层”的 source-side contract：常驻层从首帧开始，左 Rift、道路下方、
中央水晶/平台、右星图/地形以及 near/mid/far 的建筑接缝、反射、云和空气同时运动；事件层只在约 4.5–7.0 秒
沿中央已有垂直轴做低幅、圆润的呼吸式蓄放，且不暂停基础层。为减少模型把关系词变成穿屏图形，brief 删除
`gather/travel/circuit`，明确禁止跨画面直线、HUD、白闪和 burst-only 右侧。

合同与 no-cost preflight 已分别固定到 `docs/assets/8e-portal/portal-motion-brief-v4.txt` 和
`docs/assets/8e-portal/portal-motion-preflight-v4.json`；实际 POST 仍为 0，Image2 未使用，production media 仍为 0。
只有重新完成价格/请求 readback 并获得付费调用授权后，才允许 v4 runner 单次生成；成功也必须先通过
source identity、全幕运动分布、loop seam、编码和人工视觉门，不能直接接入 runtime。

`0006858` / Actions `33078261349` 已为该 source-side contract/preflight 完成 exact-SHA 三 job 公共闭环。
该公共证据不改变实际 POST `0`、Image2 未使用、production media `0` 和付费调用门。

首次 v4 runner 启动在 POST 前因 Windows 换行 digest mismatch 安全停止；修复后 runner SHA 为
`4aa7459cff78d462779137fed82d7edc84c0a0fc2d9ee539dbb4311b1c6a6dcc`。Dragon pricing readback 为
`¥1.494570/s`（720p、文本/图片参考），12 秒预算 `¥17.934840`；换行修复与价格回读须先公共闭环，
再执行唯一一次付费调用。

### RQ-142：Seedance v4 候选拒绝与方法层暂停（2026-08-27）

v4 的唯一任务成功下载且编码正常，但视觉审查拒绝：中央平台被生成成大面积发光圆顶，左 Rift 只有弱变化，
右侧星图/地形与整体环境近乎静止。指标显示 center 每 0.5 秒 MAD `0.014625`，left/right 为
`0.005851/0.004653`，变化集中在中心而非全幕。

该结果暴露的是我们 prompt/mode 的控制缺口：`platform response`、`fluid depth`、`breathing` 等抽象词与
“平台几何不可变”产生语义竞争；静态首帧又没有区域/时间控制，模型选择中心显著物变形来制造运动。v4 作为
`research-candidate-rejected` 保留，production media 仍为 0。下一步先做 prompt/mode fault split 与方法裁决，
暂停首帧盲抽；不靠堆形容词、不立即换模型、不接 runtime。

v4 rejection audit `c964016` / Actions `33083670925` 已完成 exact-SHA 三 job 公共闭环。该证据确认失败样本、
指标和 fault split 可复现；它不把 v4 变成可采用媒体，也不允许在未完成方法裁决前继续付费抽卡。

### RQ-142 method fault split 裁决（2026-08-28）

v3/v4 连续显示首帧单锚点能较好保持源图，却缺乏把运动分配到左/中/右和 near/mid/far 的真实控制；v4 的
`platform response`、`fluid depth`、`breathing` 等抽象词又与平台几何不可变产生语义竞争。故不能把问题简化为
“换模型”或“再加形容词”。

当前路线顺序冻结为：A 首帧 I2V 暂停；B 带时间/区域控制的真实视频编辑作为下一优先候选；C 改为锁母图的
纹理/位移型混合制片 fallback。旧 C-line 线条/HUD proof 只保留负面证据。下一步先完成 B 窄版三时间点
mask/prompt contract 与 no-cost preflight，未完成前不再付费、不接 runtime。

### B1 Smart Edit contract（2026-08-28）

B1 已把上一轮 Smart Edit 的控制收窄为双锚点与三个时间点：Video1 只保留节奏，v2 母图锁定结构；中央只
允许水晶/现有光柱内部呼吸，平台几何不可变；左/右/道路/反射/云空气从首帧持续。主 prompt 压至 1,977 字符，
三份 annotation 与 source/video SHA 已 digest 绑定。当前只完成 no-cost preflight，未上传、未付费、未调用。

B1 页面 readback 当前受浏览器扩展超时阻塞：即梦标签可发现且初始页为“全能参考”，但 DOM/CUA/截图无法稳定
返回；不把该阻塞误判为 Smart Edit 不可用，也不猜测模式/积分/音频状态。恢复后只做一次只读核对。

### C′ proof 与候选切换（2026-08-28）

C′ 本地材质 proof 通过结构/覆盖的机器门，但人工审查认为运动过轻、source-pixel mask 边缘有贴层风险，不能
满足 Portal 的明显、cool、整幕呼吸目标；因此不再提高 opacity/位移追绿。B1 与已执行 Smart Edit 形态重复，
也不再付费复跑。下一候选改评估 Kling v3 Omni 的单图片引用模式，使用其专用 `metadata.image_list` 与
`<<<image_1>>>` 占位符和 prompt，先过 schema/价格/source/单次调用 preflight。

Kling v3 Omni image-reference comparator 已完成专用 schema/prompt/价格 preflight：`std/720p`、8s、16:9、
audio off、`metadata.image_list` + `<<<image_1>>>`，预计 ¥3.696。未调用、未上传旧视频；下一步只做一次
页面/账户 readback，结果仍须通过 source/seam/全幕运动和人工视觉门。

Kling image-only 实际 task 已完成但拒绝：source-first `0.860618`，左 Rift 变成厚塑料圆环，中央强光柱，右场与
整体环境近乎静止。该结果不证明 Kling reference-video/Omni 多模态模式无效，但证明不应再为 image-only prompt
付费；下一步必须先核对 temporal/reference-video 输入能否获得、费用和隐私边界，再决定候选。

Kling B2 选择 base video + image reference，而不是另一个 image-only prompt。历史 Seedance task 只提供临时 Video1
URL 与时间节奏，v2 母图锁视觉；URL GET-only、不持久化。prompt 专门禁止 B1 的塑料圆环/金色星点/实心光柱，
runner 只有一个 POST。独立 public gate 前不读取 Key、不调用模型。

### RQ-143：分层材质门与 masked-inpaint proof（2026-08-28）

source-derived 位移和五张未遮罩 ImageGen plate 均不能同时满足明显、清晰、无重影。故先做一个 bounded Rift
proof：确认母图保持底图，ImageGen 清洁背板只在 Rift 内遮罩使用，独立 RGBA 流体层只在该遮罩内运动。机械
合成门通过，但透明层可见时像贴上的蓝带、不可见时运动不足；ImageGen 整图输出还有轻微全局差异，不能成为新母图。
候选 `portal-motion-candidate-masked-inpaint-plate-v1` 判为 `research-proof-rejected`，不进入 runtime 或
production media。

### RQ-144：Wan 3.0 官方 first-frame-only 重开（2026-08-28）

在局部分层 proof 被拒后，用户明确要求重新使用此前未公平利用的 Wan 3.0 官方通道。只做一次有界诊断：active
v2 母图作为 `first_frame`，不再把同图设为 `last_frame`；使用 `ratio=adaptive`、1080P、12 秒、audio/
prompt_extend/watermark off、固定 seed 127 与新的 motion-only brief。先核对同区 endpoint/账号额度/价格、
source/prompt digest 和 one-POST runner，再执行；无论结果如何都不自动重试、不接 runtime、不把输出直接当作
production media。成功输出还必须过三大区/near-mid-far 全幕运动、source/loop/编码和人工材质审查。
### RQ-145：Riot 官方壁纸/屏保作为条件回退（2026-08-28）

这不是当前已采用路线，而是 Wan 3.0 重开失败后的明确止损选项：停止继续生成整幕 Portal 视频，改评估 Riot
官方 League Displays 的地区主题动态壁纸作为 Portal 候选，并用一张静态壁纸作为 Account 背景；用户在 Portal
开始前选择地区。Portal/Account 的 MotionSites 风格只影响界面结构与转场，不能绕过来源、许可、格式、体积、
移动端、reduced-motion 和本地白名单门。当前先完成 Wan 一次公平对照，只有其人工视觉门失败才进入该回退评估。

### RQ-146：立即转入官方/授权壁纸路线（2026-08-28）

用户已明确“转战”。Wan first-frame reopen 停止在错误 endpoint 的 HTTP 404/no-task 诊断，不再继续寻找 Host
或发送第二次 POST。`animated-demacia.webm` 作为第一份真实候选进入审计；随后又核对了班德尔城 WebM。下一步建立
region wallpaper catalog 和本地研究预览，Portal 先选择地区再加载动态壁纸，Account 使用独立静态壁纸。League
Displays、Wallpaper Engine/Steam Workshop、Riot 官方素材及其它来源继续按来源/许可、格式/体积、浏览器/移动端/
reduced-motion 与 loop 门分别准入，未经核验不得进入公开 runtime。

### RQ-147：补充 Bandle City 候选与静态清晰度门（2026-08-28）

用户在桌面 `RIFTCOACH` 素材中找到班德尔城动态壁纸。它与 Demacia 一样先作为本地研究候选；WebM 原文件带 Opus
音轨，已额外生成无音频 H.264 sibling 和 poster，但 `rights` 仍为 `unverified`。用户同时指出
`runeterra-bandlecity-03.jpg` 只有 926×1080 且压缩痕迹明显。静态 Account 图的处理采用非破坏性 sibling：先查找
更高分辨率官方源；本轮 AI 修复候选因纹理脆硬、AI 重绘感和质感不一致已判 rejected，并同时保留原图、记录 hash 与人工视觉裁决。任何修复图或
动态壁纸在来源/许可、格式、清晰度、浏览器/移动端/reduced-motion 与 loop 门完成前都不进入 adopted media。

### RQ-148：纠正匿名静态图地区映射（2026-08-28）

用户复核确认：`ab3c2d4...-1920x726.jpg` 属于暗影岛，`ef261f0...-1920x900.jpg` 属于比尔吉沃特。此前按画面
猜测的相反映射作废；后续以用户核对和官方 Universe JSON 索引为依据，匿名文件保持原名，直到最终映射审核完成。
以绪塔尔在当前桌面素材集合中没有可确认的静态图，不能借用其它地区素材填充。

### RQ-149：补齐 Ixtal 静态 Account 候选并单独评估动态（2026-08-28）

用户随后补充了 `1a75d072...-5000x2811.jpg`，该图是 5000×2811 的 Ixtal 丛林/建筑场景，适合作为 Account 静态候选；
本地已生成 `account-ixtal.jpg` 研究副本。Ixtal 仍没有现成 Portal 动态壁纸，因此只能另做一次有界 first-frame-only
试验：利用藤蔓、叶片、云雾、光束、悬浮晶体和远景雾层这些自然 motion carriers，保持中央建筑、地形拓扑、镜头与色彩身份
不变。该试验不授权付费调用、采用或把静态图伪装成动态素材。

### RQ-151：Void 详细徽章以原创候选补位（2026-08-28）

旧 LoR 支持页的详细徽章附件中没有可稳定获取的 Void 版本。用户允许自行绘制补位，但要求材质不要霓虹化，也不能暗到
失去 Void 识别度。当前保留一枚真实透明 RGBA 的平衡版：黑曜石/深靛主体、低饱和紫色内腔、少量冷色边缘高光。它只作为
 selected-region hero/transition 候选，13 个 Universe 小 crest 仍是选择器默认；在用户确认前不进入 runtime。

用户随后提供了 Image2 网页端生成的 Void 徽章，结构与其它立体徽章更接近。当前优先候选改为
`badge-void-image2-v1.png`，并保留 `badge-void-image2-v2-muted.png` 的轻微降高光版本。它们都是不透明 RGB 图，
只适合先作为 selected-region hero 视觉候选；若最终要放进小卡，需要另做透明 cutout，并重新检查边缘、尺寸和背景融合。

### RQ-150：Ixtal 动态制作采用 first-frame-only 自然运动方案（2026-08-28）

用户认可生成的 Ixtal 静态概念方向，同时明确原 5000×2811 图用于制作动态。职责分离为：原图是动态首帧，生成图是独立
Account 静态候选。动态不复用 Portal 的三主体/中心 burst prompt，而是只驱动现有景物的可解释运动：前景叶片与藤蔓小幅
摆动，云与远景薄雾持续平移/升降，光束缓慢呼吸，悬浮晶体原地轻微漂浮，近中远景有轻微视差；中心建筑、山体轮廓、镜头、
构图和色彩身份保持稳定。先完成源图下采样、参数/费用/输入 SHA/prompt preflight，再决定一次受控 I2V 调用；不盲目重试，
不把失败视频接入 runtime。

### RQ-153：Ixtal Seedance 候选暂准使用但保留替换提醒（2026-08-29）

Ixtal first-frame-only Seedance 2.5 请求已按预检执行 exactly one POST，并下载为 10.041667 秒、1280×720、无音频的
H.264 候选。逐段抽帧确认官方 splash 的建筑、山体、构图与材质身份保持稳定，叶片/藤蔓、云雾、光束、植被层和悬浮晶体
有连续但偏低幅的运动；没有把整张图蒙成纱罩，也没有出现明显镜头漂移或黑屏。用户判断“差不多可以先用”，但指出动效稍轻，
因此该结果只能作为可替换研究候选继续进行 Portal/Account 布局与播放降级联调，不能视为最终视觉签字或来源/再分发权利确认。

候选审计、SHA、区域运动统计和未关闭门记录在
`docs/assets/8e-portal/portal-ixtal-wallpaper-candidate-seedance25-v1.md`。待真实布局可见后保留一次明确回看：由用户选择
保留柔和版、进行一次有界调优或替换更强官方动态源；不自动再次付费生成、不覆盖现有文件，`production_media` 继续为 `0`。

### RQ-154：两地区 Region Entry Panel 试水（2026-08-29）

用户要求先用两个地区验证“选区—背景切换—进入账号”的完整产品链路，并提醒 MotionSites 研究要继续公开广筛，不能只重复已保存案例。当前采用 `Demacia + Bandle City` 两个本地研究候选；13 个 Universe crest 仍全部展示，但没有动态候选的 11 区显示 pending 并禁用，避免把图标存在误报成壁纸可用。

试水保持独立 `?surface=wallpaper-lab`，不替换默认 `/`。选中候选后立即重挂 WebM/MP4/poster；Enter 通过既有语义转场，以 `/?stage=account&region=...` 进入 Account，Account 只读取地区作为低对比静态氛围层，Back/Continue 保留同一地区参数。所有候选仍是 `research-candidate`、rights `unverified`，不进入 adopted manifest。

MotionSites 的公开 browse/catalog 继续作为模式库：只吸收全幅媒体英雄、紧凑选择器、即时反馈、聚焦动作和完整 hover/focus/reduced-motion/failure 状态；不复制页面、不购买或引入新依赖。实现与验证设计见 `docs/plans/2026-08-29-8e-region-entry-panel-trial-design.md`。

### RQ-155：全量来源池按消费者复查（2026-08-29）

用户补充此前的参考来源不止 MotionSites，要求回看并实际利用适配内容。复查后固定分工：Riot/Universe 提供
Hextech 形状语法和 crest fallback；Awwwards、SiteInspire、Recent Design、Godly、Mobbin、Refero、Land-book、
Lapa Ninja、Nicelydone、Dribbble、Behance 只提供构图、字阶、节奏和密度参照；MotionSites、Motion、21st.dev
Motion/Primitives、Magic UI、Animata、React Bits、Aceternity、Uiverse 只提供可逆的局部交互机制。OP.GG 与
电竞数据产品、Langfuse/LangSmith/Phoenix 等、TrainingPeaks/WHOOP/Strava 分别绑定 Workbench、Trace、Training，
不在 Portal 偷做；Aura/v0/Lovable/Figma Make/Framer 只作隔离原型比较；Image2/Photoshop/视频模型/HyperFrames/
Remotion/GSAP/Anime/Three/Steam Workshop 继续受素材、许可、性能和退出门约束。当前代码只采用轻量 CSS/React
实现的 spotlight、crossfade、aperture handoff 和 badge fallback，不新增依赖、不复制来源、不改变 `production_media=0`。

### RQ-156：细粒度来源记录与可恢复的地区 handoff（2026-08-29）

再次复查旧日志后，补充记录此前被大类合并的来源：Design Prompts 只提供
brief/情绪板；Photoshop/After Effects 与 PPT 只服务离线修图、演示和 README
mockup；Radix Dialog 保持已采用的焦点/Esc 行为；shadcn、ECharts、Tremor、visx、
Tailwind Plus、Untitled UI 仍需真实消费者与许可/成本门；League Displays、
Wallpaper Engine/Steam Workshop 的每个壁纸文件都必须独立通过来源、再分发、codec、
移动端、reduced-motion 和 loop 审查。历史检索 lead（Cult UI、DesignRocket、
Anima、Envato 等）没有具体 consumer/provenance 的只留检索记录，不膨胀产品范围。

Portal/地区/Account 代码不因此引入第二套 UI 或动效引擎：所有已有本地细徽记可渐进显示，
缺失文件回退 Riot Universe crest；spotlight、crossfade、diamond marker 与 aperture
仍由现有 React/CSS 实现。地区入口进入 Account 时写入受限 `from=wallpaper-lab` URL 标记，
解析器在刷新/复制链接后恢复返回地区选择语义；新的地区链接显式带
`surface=wallpaper-lab`，旧 `?region=` 仅作兼容 presentation alias，未知参数仍
fail-closed。Portal 选区对当前 history entry 做 `replaceState`，浏览器 Back 不会丢失已选地区；
1000–1199px 短桌面使用三列卡片，<=420px 手机使用单列，长页面的媒体/遮罩/转场层固定在 viewport。push/popstate 会复位全页滚动，activation generation 绑定地区以避免 stale
handoff；Portal/Auth 使用语义 main、skip/heading focus、aria 状态和 intrinsic media
尺寸，且保留 poster/mobile/reduced-motion/error fallback。以上是 RQ-156 的可逆 UI
hardening 证据，不是 8E 完成声明。工作台、Trace、Training 的 source 消费者继续留在
后续设计，`production_media` 保持 `0`。

### RQ-157/158：13 区 Focus Rail 与有因果的登录交接（2026-08-29）

旧 compact atlas/grid 不再是当前批准的地区入口。13 个 presentation identity 全部进入可滑动的 Universe crest
rail，selected hero 才使用本地高细节研究徽章；motion readiness 作为独立可选证据，缺失时 poster fallback，
不能再 disabled 身份。主按钮位于 rail 下并固定为“进入登录界面”/“Continue to sign in”。

Portal→Account 由 selected identity 驱动 bounded 760–1000ms handoff，保留 generation guard、URL return marker、
Back/reload/focus 和 reduced-motion immediate path。Bandle Account 使用用户新选的 1200×600 WebP sibling；它与
扩展名错误的本地 WebP emblems 都只能作 research preview。该决策不引新 UI 引擎、不碰 Workbench/Riot routing，
也不改变 `production_media=0`。

### RQ-159：产品文案与媒体审计语言分层（2026-08-29）

地区世界观文案、presentation identity 和 media readiness 是三条不同轴。用户看到的 Portal/Account 只展示地区名、
RiftCoach 自写的双语氛围句和真实动作；codec、尺寸、时长、候选/采用状态继续留在 typed catalog、data attributes、
证据文件和测试，不再作为正常界面说明。任何未来的“官方台词”都必须逐条核验来源和使用边界；在此之前不得假引。

Portal→Account 采用 shared shell phase 和选中位置驱动的 aperture/crossfade，而不是 route swap 后再叠一个无关特效。
Account heading 的 focus 延后到 overlay 不再占据表面；reduced-motion 保持即时导航。该决策不修改 Auth、Riot routing、
Workbench、媒体来源/许可或采用状态。

### RQ-160：展示标题必须显式分行，不由容器随机断句（2026-08-29）

Portal 中文标题固定为 `从一方之地，`／`启程。`，不得继续保留“先选一处落脚点”；Account 中文标题固定为
`选择一位`／`召唤师。`。英文分别使用 `Begin from a region`／`of your choice.` 和 `Choose a`／`player.`。
实现保留完整 heading accessible name，并用独立 block/nowrap 表达设计分行；响应式通过字号而不是改变语义或任意换行
来适配。该决策不扩展到 Workbench，也不改变 Auth、路由和媒体采用状态。

### RQ-161：Account panel 与控件字阶的局部卫生修补（2026-08-30）

Account 右侧表单在桌面只用独立 `top` 通道小幅上移，避免和既有 handoff `transform` 动画互相覆盖；移动端显式
回到 `top: 0`。Riot ID 输入与查询区域、账号关系两个原生 select 共享 Manrope body 字体、560 字重和 0.95rem，
三条字段 caption 使用同一可读字阶。该决策只校正构图和字阶，不改变 Auth、路由、地区语义、Workbench 或媒体采用；
computed-style E2E、全量 unit/E2E、typecheck/build 和 live DOM 是本批证据。

### RQ-163：Portal/Account 收口后交回 Agent 主线（2026-08-31）

用户确认 Portal/Account 当前视觉切片已经达到可收口点，后续优先恢复 Agent 主线，而不是继续做地区目录或把前端
展示工作无限延长。该交接不关闭 8E：研究媒体仍为 research-only，`production_media=0`，8F 仍未开始。

本批先做事实对齐：保留 RQ-154–162 的历史和 supersession 关系，补齐 README 的当前阶段、Agent 底座、真实缺口和
后续闸门，并把 G53-0 设为下一执行候选。GLM-5.3 仍须通过 G53-0 至 G53-4，受限 Review Coach 必须绑定 owner、
Conversation、source run 和玩家身份；Data Dragon、Evidence/Trace、Training、OP.GG 黄金切片、安全部署与 8F
继续按独立闸门推进。该决策不改变 Workbench、Auth/RSO、Riot routing、默认模型或任何媒体运行时。

### RQ-164：G53-0 本地审计停在 blocked/deferred（2026-08-31）

G53-0 已完成无 I/O 的静态核对，但没有足够的当前非敏感账户证据证明 GLM-5.3 可用。产品默认仍为
`zhipu`/`glm-5.2`，Zhipu Adapter 仍固定 `thinking=disabled`；本机被忽略的 `.env` 只做遮罩式字段核对，
其 `LLM_PROVIDER=glm` 与仓库 loader 的严格 `zhipu` 合同不一致。账号类型、Plan 权限、实际 endpoint/region、
正式 model ID 和 `enabled + low` 可用性均保持 unknown。

因此 G53-0 的状态是 `completed-local / adoption blocked-deferred`，不是模型质量失败或准入成功。不得读取
Key、调用 Provider、修改 `.env`/默认模型或重写 GLM-5.2/DeepSeek 旧结果；取得可核验的非敏感账户信息后，
才另行决定 G53-1 离线 profile TDD。

### RQ-165：普通 API GLM-5.3-Flash 适配档案先行（2026-08-31）

用户核对官方资料后明确本批使用普通智谱 API，不使用 Coding Plan。Flash 模型标识冻结为
`glm-5.3-flash`，普通 API 基址冻结为 `https://open.bigmodel.cn/api/paas/v4/`。实现采用按模型
精确解析的不可变 thinking profile：历史 `glm-5.2` 继续 `disabled`，GLM-5.3/Flash 使用
`enabled + low`；Provider、能力探针和 CLI 不再各自复制 vendor 字段。Flash 文本/结构化响应的
reasoning 在适配器边界内消费后丢弃，工具回合或异常类型仍拒绝，避免把厂商状态泄漏进中立合同。

RQ-165 只授权本地离线 TDD 与回归，不授权读取/输出 Key、真实调用、默认模型切换、`.env` 修改、
Workbench/前端改动或生产采用。聚焦回归 `70 passed, 29 subtests passed`，下一步为
`g53-2-exact-sha-ci`；G53-3/G53-4、领域质量、部署合规和 8F 仍需独立闸门。

### RQ-166：G53-2 exact-SHA 公共 CI 通过（2026-08-31）

用户明确继续 G53-2 后，只把 G53-1 的 9 个 Provider/配置/probe/CLI/测试文件冻结为提交
`0f97b92683e4981842e745a695864deb611bb630` 并推送。Actions run `33325222755` 的 head SHA 精确匹配，
`pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 均成功，公共 pytest 为
`1912 passed, 145 skipped, 1 warning, 127 subtests passed`。

该决策不修改现有 workflow、`.env`、默认 `zhipu`/`glm-5.2`、Workbench、Auth、路由或
`production_media=0`，也不读取/输出 Key 或发起真实 Provider/Riot/OP.GG 调用。G53-2 现在是
`completed-public`；下一指针为等待单独授权的 G53-3 有界协议门（最多三次真实调用），不把 CI 绿灯写成
领域质量或生产准入。

### RQ-167：G53-3 首次有界协议尝试因认证失败停下（2026-08-31）

用户明确继续后，按 G53-3 硬预算执行一次 `adapter_protocol`。只在进程内临时使用普通 API
`glm-5.3-flash`；A1 第 1 次请求返回脱敏 `authentication_failed`，A2 跳过，报告为
`calls_used=1/3`、`admitted=false`，无重试。结果文件已通过 schema 校验且不含正文、reasoning 或 Key。

该结果只能证明当前凭证/账户/端点接缝未能完成首个协议请求，不能区分具体根因，也不能推出模型质量或领域准入。
保留 `production_media=0`、默认模型、Workbench、Auth 和路由不变；下一步先确认凭证接缝，是否重开 G53-3
必须再次获得用户明确授权，G53-4 暂不启动。

### RQ-168/169：旧 Key 删除后的 G53-3 重开通过（2026-08-31）

用户确认前次 Key 已删除，重新创建普通 API Key，并将本机 `.env` 修正为普通 API 端点和
`glm-5.3-flash`。重开严格执行 3 次调用且无 client 重试：A1 结构化合同通过，A2 Agent 工具往返通过（1 次
ToolCall/执行），`admitted=true`。该证据只证明 GLM-5.3-Flash 的普通协议接缝可用，不授权默认模型切换、领域采用或生产发布；
下一步仍是单独授权的 G53-4。

### RQ-170：G53-4 新鲜领域门首错拒绝（2026-08-31）

用户已在 G53-3 普通协议接缝通过后明确授权一次 GLM-5.3-Flash 新鲜领域采用门。执行前采用独立匿名三案例、
Dataset/Input Plan/Prompt-Context snapshot 和 no-I/O preflight；真实运行严格限制为领域最多 12 次调用、每案 4 次、
总 Token 12,000、无重试/无修订、首错停止。首案第 1 次响应含并行 ToolCall，当前 Zhipu 中立适配合同以
`unsupported_parallel_tool_calls` fail closed，后两案跳过；结果为领域 `1/12` calls、`0` normalized tokens、
累计含 G53-3 为 `4/15` calls 与 `1115` tokens，费用状态 `unknown`。

不可变脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_v1.json` 的 SHA-256 为
`ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`。结果不含 Key、Prompt/响应正文、reasoning、
完整请求标识或注入 marker。该门标记 `completed-local-rejected`，不进入默认模型、不放宽并行 ToolCall 合同、
不在已见考卷上重跑；新 runner/资产尚无 exact-SHA 公共 CI。Workbench、Auth、前端、DeepSeek 与 `production_media=0` 不变。

### RQ-171：GLM-5.3-Flash 适配器修复与 G53-5 全能力验证准备（2026-08-31）

旧 G53-4 的并行 ToolCall 首错被判定为适配器合同缺口，不能直接归因模型质量；旧输入、结果和预算保持不可变。
按用户授权，Flash 隔离 profile 采用 `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`，
中立 `reasoning_content` 仅在内部保留并跨工具回合精确回放，公开投影不泄漏；Zhipu Adapter 接受多个合法
ToolCall 并保持顺序，由 AgentLoop 逐个受控执行，能力声明仍不承诺并发。该批离线合同与回归已完成，但新的
`g53-5-fresh-flash-capability-gate` 真实 Provider 全范围测试尚未执行，必须使用新实验身份、唯一脱敏输出路径和
有界预算；不改默认模型、`.env`、Workbench、Auth、前端或 `production_media=0`，不把 G53-5 结果预先写成领域/生产准入。

### RQ-172：G53-5 全能力矩阵本地真实观察（2026-08-31）

新的 `g53-5-fresh-flash-capability-matrix-v1` 在 dirty worktree 上完成一次有界真实矩阵：`11/11` calls、
`46,151` tokens、`7/8` cases pass。adapter core、AgentLoop 的有序多 ToolCall/思考回放、domain development、
vendor text stream 与 vendor multimodal 均取得观察证据；F7 vendor `tool_stream` 在 `max_tokens=512` 以
`incomplete_chat_response`/`length` 结束，不足以证伪能力；F4 `cached_input_tokens=0`、`cache_status=unproven`，
不宣称缓存命中；F8 仅为 vendor-only 观察。结果文件 SHA-256 为
`BFFF564CF4C6E7B2DD05F88542FD7A872D1565442B6D35C795EC6892CC84BE0C`，`production_admitted=false`、
`public_ci_confirmed=false`。该决策不关闭 Stage 8/8E、公共 CI、领域/生产准入或 8F；下一步等待用户决定 Agent
主线下一项，不重跑 G53-4，不改默认模型、Workbench、Auth、前端或 `production_media=0`。

### RQ-173：G53-5 F7 工具流上限独立诊断（2026-08-31）

为诊断 G53-5 原 F7 在 `max_tokens=512` 下的 `incomplete_chat_response`/`length`，按用户要求新建独立
follow-up，不修改或覆盖 RQ-172 及旧证据；唯一变化是把上限从 512 调至 2048。实验
`49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b` 仅执行 `1/1` 次真实调用、`557` tokens，
`finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source identity stable、`cached=0`。
结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json` 的
SHA-256 为 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`，父矩阵 experiment 为
`4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`、父结果 SHA 为
`bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。

该结果只提供 vendor raw transport 观察，标记 `vendor_raw_transport_only`、`production_admitted=false`、
`public_ci_confirmed=false`；不证明 provider-neutral streaming、Agent 生产能力、领域采用或公共 CI。Stage 8/8E
继续 `in_progress`，下一步等待用户决定 Agent 主线下一项；不改默认模型、Workbench、Auth、前端或
`production_media=0`。

### RQ-175：GLM-5.3-Flash 专属运行时预算档案（2026-08-31）

用户决定继续使用普通智谱 API 的精确模型 `glm-5.3-flash`，并要求旧的统一 30 秒执行截止与 512/1024
输出上限不再误伤 Flash。本批新增不可变、版本化 `ModelRuntimeProfile`，只匹配 `zhipu/glm-5.3-flash`：
Agent 总执行窗与 `llm.chat` 工具窗各 90 秒，Provider 传输超时 120 秒，单次输出上限 2048，采样固定
`temperature=1`、`top_p=0.95`；思考档案沿用 RQ-171 的 `enabled/max/clear_thinking=false`。

档案由可信组合代码显式注入 Agent 编译、AgentLoop、`llm.chat`、G53 预算包装器和 Provider 构造；调用方
不能升权或覆盖，GLM-5.2、无档案路径和旧结果继续保持原行为。2048 是本项目首个受控上限，不是厂商官方
最大输出；旧 held-out Dataset 的 30 秒仍是质量资源阈值，不能用新档案回写旧证据。G53-7 当前只完成
evaluation-only 离线接缝与回归，真实运行必须使用独立结果路径
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`，
取得 exact-SHA 公共 CI 且工作树干净后才可执行；本批没有真实 API 调用、默认模型切换、Workbench/前端/Auth
或 `production_media` 变化。

### RQ-176：Flash-only 产品运行时晋级（2026-08-31）

用户明确决定把普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品正常运行目标，不再把 Pro/Flash
比较当作前置决策；GLM-5.2 只保留为明确的兼容/应急回退。该决定引用
`docs/adr/0070-adopt-glm53-flash-product-runtime-profile.md`，并不把尚未完成的公共 CI、领域质量、
黄金切片或生产部署合规闸门视为已通过。

- 唯一注册的 `glm-5.3-flash-runtime-v1` 从产品组合根显式传入 Worker、RuntimeExecutionFactory、
  Agent compiler/Loop、Harness `llm.chat`、Zhipu Provider、Runtime policy 和 Trace identity；对已绑定同一
  注册档案的 concrete Provider，Root/Factory/Runtime 允许安全自动推断，否则对精确 Flash 未绑定档案一律提前
  拒绝，避免编译器继续使用 30 秒策略而 Runtime 偷偷升级到 90 秒；
- Flash 使用 Agent/工具执行窗 90 秒、Provider 传输 120 秒、2048 输出上限、`temperature=1`、
  `top_p=0.95`、SDK `max_retries=0`，Skill 的 30 秒质量资源门独立保留；Worker 默认 lease/heartbeat
  为 360/60 秒并拒绝少于 300 秒的 lease；
- `.env.example` 与 Compose 模板对齐 Flash；GLM-5.2 的兼容路径、旧 Trace、测试 double 和显式无档案
  历史路径继续可读，但不能悄悄获得 Flash 预算。Portal、Account、Broadcast Workbench、Auth、路由和
  `production_media=0` 不在本批范围内；新实现须先取得自己的 exact-SHA 公共 CI，再在同一 SHA 重取
  G53-3，随后才可执行 G53-7、完整黄金切片及安全/部署/合规收口。

### RQ-177/178：协议证据与 G53-7 身份分离（2026-08-31）

G53-3 的协议执行代码身份固定为实现提交 A，脱敏结果另由直接子提交 B 承载；不能把 B 的提交 SHA 误当成
`protocol code_sha`，也不能靠修改结果正文追赶变化后的 `HEAD`。RQ-178 的 `GLM53ABIdentityBinding` 和
schema 1.1 admission 只做本地无 I/O 预检：确认 A/B 及各自公共 CI 见证、当前 `HEAD=B`、B 的 Git blob 与
工作树 canonical-LF 摘要、Provider/model 和严格三调用通过合同；B 只允许新增 capability-result 文件。
当前只完成这道接缝的本地实现与 `53 passed` 聚焦回归，未运行 G53-7 领域 API，也未改变 Portal、Account、
Workbench、Auth、默认模型或 `production_media=0`。下一步必须先冻结新的 A′、取得 A′ exact-SHA CI、在 A′
重取 G53-3，再新增 B′，之后才评估领域门。

### RQ-179：最终实现 A 及公共 Git 历史见证（2026-08-31）

最终 A 冻结为 `9e6d78be51c3a5c512b67f83d2849f9b1261cf77`，Actions run `33378687984` 三 job
成功且 `head_sha=A`。身份测试在新 checkout 上暴露两类可审计失败：历史 fixture 不能把旧 B 当任意当前 HEAD，
公共浅克隆也无法验证旧 A/B 的直接父子与 blob。最终方案仅在测试中隔离历史 reader，并让 CI 获取完整 Git 历史；
生产 `actual HEAD == evidence B`、A→B 直接子提交和 B 只新增证据的门均未放宽。下一决策点仍在新 G53-3/B 证据链之后。

### RQ-180：G53-7 首次真实领域尝试未准入（2026-08-31）

用户在 RQ-179 的 A/B 公共证据链完成后明确授权执行一次 G53-7。运行在干净 LF checkout 上，协议 3/3、领域 2/12，
累计 5/15 calls、领域 3505 tokens；首例 `flash_gate_baseline_01` 以
`provider_response_invalid` / `incomplete_chat_response` 停止，后两例按首错跳过，`admitted=false`。
脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`
的 canonical-LF SHA-256 为 `21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment 为
`236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；本地 C=`9157cde…` 只承载结果，未推送、无公共 CI。
底层 vendor finish reason、Key、响应正文和 reasoning 未保存，不能把安全聚合码进一步解释为 `length`，也不构成模型一般质量
或生产成熟度结论。旧结果不覆盖，当前停止自动重试；若继续须另立版本化的 Flash 响应完成/截断诊断。Stage 8/8E 继续
`in_progress`，Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。

### RQ-181：Flash 响应完成度诊断（2026-08-31）

RQ-180 只留下 `provider_response_invalid/incomplete_chat_response` 聚合码，不能据此猜测供应商结束原因。
用户授权一次独立、正文零留存的首案例诊断后，产品实现基线 `7cb66d218389c0e7d7aa7b2b1969a4678402f857` 上的
`agent_initial` 回合记录到 `finish_reason=length`、input/output `2220/2048`、空正文、非空 reasoning、0 ToolCall；
Usage 有效，但 Zhipu 适配器按既有 fail-closed 合同返回 `incomplete_chat_response`，normalized/settled 为 `0/1`。

这次证据确认的是“最大推理档案先耗尽 2048 输出额度”的具体失败路径，不是账号失败、模型不可用或一般质量结论；
它也不改写 RQ-180 的旧第二回合。脱敏结果
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
的 canonical-LF SHA-256 为 `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，不含 Prompt、正文、
reasoning、Key、请求 ID 或工具参数。决策保持：不自动提高全局上限、不放宽生产适配器、不重跑领域门；下一项先
设计版本化响应完成策略并补离线 TDD，进入实现需新的明确授权，Stage 8/8E、Portal/Account/Workbench/Auth、路由和
`production_media=0` 均不变。

### RQ-182：版本化响应完成策略（2026-08-31）

用户明确继续后，采用独立纯离线策略而不是马上改适配器或暗中续接。`ResponseCompletionPolicy` 以精确
`zhipu/glm-5.3-flash`、runtime profile 身份和语义版本绑定；严格 v1 保持 2048 输出/零额外调用，
`length` 的空正文/非空 reasoning 仍 fail closed。8192/一次 fresh-recovery 仅是未注册候选，只有在新的
runtime、attempt、Trace、预算合同和真实证据完成后才可能另行启用。RQ-180/RQ-181 证据、默认模型、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；离线 `41 passed` 不构成领域或生产准入。

### RQ-183：候选 fresh-recovery runtime/attempt/预算/Trace 合同（2026-08-31）

用户明确继续 RQ-182 的唯一下一项后，先建立独立的候选合同，不把第二次请求直接
塞进 Provider 或 AgentLoop。`ResponseRecoveryRuntimeProfile` 精确绑定
`zhipu/glm-5.3-flash` 的未注册 `glm-5.3-flash-runtime-v2-candidate/2.0.0`；
离线计划最多描述 `primary` 与一次 `fresh_recovery`，而且始终
`execution_allowed=false`。`ResponseRecoveryLedger` 对每个底层调用执行一次预留和
一次结算，累计 input/output/elapsed，失败、Usage 缺失、单次或累计超限均保留已用
槽位并 fail closed；账本重算策略判定，调用方不能伪造 eligibility。独立
`ResponseRecoveryTrace` 只保留脱敏状态和资源数字，不改现有 Runtime Trace。

聚焦测试 `30 passed`，相邻回归 `128 passed`；这只是本地合同证据，不是恢复能力、
G53-7、领域采用或生产成熟度。严格 Flash v1 的 2048/零额外调用、默认模型、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；后续仍需
新 exact-SHA 公共 CI、同 SHA G53-3、一次单独真实诊断授权和成本/延迟/失败审查。

### RQ-184：候选合同公共证据链（2026-08-31）

用户明确“继续”后，完成 RQ-183 候选合同的公共验证和同 SHA 协议证据。实现提交
A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 Actions run `33405110692` 与只新增脱敏结果的直接子提交
B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 的 Actions run `33405881172`，均以 `pytest`、`packaging-smoke`、
`postgres-migrations` 三 job 全绿；同一 A checkout 的 G53-3 严格 `3/3` 调用中 A1 `1/1`、A2 `2/2`，
`admitted=true`，SDK retries `0`。结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`
的 `code_sha` 为 A，A/B 无 I/O identity preflight 通过，canonical-LF SHA-256 为
`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

该决策只确认候选合同的公共可复现性，不注册候选、不发 fresh-recovery、不执行 G53-7，不改变严格 Flash v1 的
2048/零额外调用、默认模型、Portal、Account、Workbench、Auth、路由或 `production_media=0`。下一步仍需用户单独
授权一次有界候选恢复诊断，并审查成本、延迟、失败与脱敏 Trace；8E/8F、黄金切片和安全/部署/合规闸门不提前。

### RQ-185：候选恢复诊断中断（2026-08-31）

用户在 RQ-184 后明确继续，并在第一次无响应中止后再次明确继续。两次独立启动均使用隔离诊断代码
`76de589a128b7a71f1def3316da3f30ebdd3a4c8` 与实现基线
`eca01ce1393286dbbe83992c2985f600ea2b30b0`，都只进入 `primary` 首回合，
SDK `max_retries=0`，没有发送 `fresh_recovery`。第一次沿用 120 秒传输边界并在约 60 秒无返回时中止；
第二次用全新结果名和临时 20 秒客户端传输上限，仍未在约 60 秒内结束，随后终止。

两次都没有可观察响应、Usage、finish reason、Trace 或结果 JSON，不能推断请求是否抵达供应商或是否计费；
费用状态保持 `unknown`。因此本轮决策不是拒绝候选能力，而是把下一门收窄为传输/代理边界复核；候选继续未注册、
严格 Flash v1 继续 2048/零额外调用。未经新授权不再重试，也不进入 G53-7，不改变默认模型、AgentLoop、
RuntimeTrace、Portal、Account、Workbench、Auth、路由或 `production_media=0`。

### RQ-186：请求级截止修复与候选延迟边界（2026-09-01）

RQ-185 的临时 20 秒客户端 timeout 被 Zhipu 请求 payload 中的 `ChatRequest.timeout_s=90` 覆盖。项目决定只修
隔离诊断器：新增显式请求级 deadline，primary 与可能的 fresh-recovery 均受同一上限；不改生产 Provider 默认档案。
代码提交 `94629161c5d3230629210444b5a1a38212799997`，相邻测试 `82 passed`。

唯一一次新 primary 明确使用 30 秒请求截止，在约 30.141 秒后以 transport timeout 安全关闭；没有响应、Usage、
finish reason、request ID 或 recovery，费用仍 unknown。脱敏结果 SHA-256 为
`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`。决策结论是“截止已可核验”，不是
“模型能力失败”；是否使用候选完整 90 秒窗口需另做延迟预算裁决。候选、严格 Flash v1、默认产品接线和
`production_media=0` 不变。

### RQ-187：完整候选窗口仍无响应（2026-09-01）

RQ-186 已证明请求级 deadline 能生效后，用户授权一次完整候选窗口。唯一 primary 使用 `timeout_s=90`、
`max_tokens=8192`、SDK retries `0`，在 90.188 秒以 transport timeout 安全结束；没有响应、Usage、finish reason
或 recovery，费用 unknown。结果 SHA-256 为
`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，由 `50ce5be` 承载。

决策是：不能再把问题归因于 30 秒过短，也不能把无响应归因于模型能力失败；下一步若继续，应设计传输/生成路径
拆分诊断并重新授权。候选保持未注册，严格 Flash v1、默认模型、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均不变。

### RQ-188：传输与生成路径拆分诊断（2026-09-01）

用户新授权后，决策是把“没有长请求响应”拆成可观察的传输与生成阶段，而不是继续盲目重跑同一 90 秒请求。
隔离诊断固定最多三次调用且 SDK retries 为 0：合法 Flash thinking 最小控制、冻结短同步请求和冻结流式首块请求。
三路均观察到响应；同步请求在小额度下以 `length + 空正文 + 非空 reasoning` 结束，流式路先观察到 reasoning 首块后
主动关闭。正式脱敏结果 SHA-256 为 `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，
代码/source identity 为 `b67b4500ebdbff934e470fd92c1461184aa7c49b`。

本条只确认 endpoint/model 路径可达且已开始生成，不把首块观察写成完整流式能力，也不把同步截断写成模型一般
质量或生产故障。候选仍未注册，严格 Flash v1 的 2048/零额外调用、默认模型、Portal、Account、Workbench、Auth、
路由和 `production_media=0` 不变；下一项为 evaluation-only `candidate-output-budget-calibration`。

### RQ-189：输出额度/推理档位校准（2026-09-01）

决策是把三路结果作为独立 companion observations 保留，而不是把不同诊断 SHA 拼成一个伪造的同 SHA 矩阵。
在同一冻结上下文下，`low+2048` 已观察到可见正文并正常结束；`low+8192`、`max+8192` 在 45 秒请求截止内
无同步响应。诊断器支持单路选择、零重试和完成后独占落盘，避免长请求串行拖过监督窗或留下零字节伪证据。

该结果只影响候选评测假设：低推理短同步可能是可行响应路径，高预算同步的延迟/流式形状仍需验证。不得据此
注册候选、把 8192 写入生产档案、改默认模型、改 Workbench/Portal/Auth，或宣称领域/生产成熟度；下一项为
evaluation-only 的流式可见正文与 `clear_thinking` 探针。

### RQ-190：流式首个可见正文（2026-09-01）

决策是新增独立 evaluation-only 原始传输探针，而不是把 `clear_thinking=true` 塞进当前产品 profile。两种单轮形状
（低推理、2048、stream、`clear_thinking=true/false`）各只发一条请求；一旦出现首个非空正文就主动关流，终态和 Usage
按未观测处理。实测首正文分别约 2.547 秒和 3.875 秒，说明流式可见正文路径可行，但没有证明跨轮清理、完整装配、
成本或生产准入。因此严格 Flash v1 继续 2048/零额外调用，候选不注册，下一项只做完整终态/Usage 观察。

### RQ-191：完整流式终态与 Usage（2026-09-01）

决策是先用独立 evaluation-only 探针验证当前产品形状的完整流，再讨论 runtime 接线。单条低推理/2048、
`clear_thinking=false` 流在 24.140 秒以 `stop` 结束并取得有效 Usage（1973 输入、652 输出），证明该冻结上下文
存在可完整消费和计量的供应商路径。这个结果不等于一般质量、长上下文、高预算、工具流或跨轮思考能力，也不授权
把 streaming 能力静默接入产品；下一步只做离线 provider-neutral 装配合同和边界测试，严格 Flash v1 与候选状态不变。

### RQ-192：提供商无关流式装配合同（2026-09-01）

决策是先冻结一条不依赖 SDK 的候选接缝，而不是把 RQ-191 的智谱原始流直接接入产品。供应商适配器将分块翻译为
`ProviderStreamEvent`，单次装配器要求真实 EOF、合法终止和有效 Usage；终止后只允许一个 Usage-only 尾帧，
正文与工具请求互斥，工具 JSON、身份、序号、资源边界和错误毒化均有显式规则。长工具参数使用 copy-on-write
和增量计数，`StreamAssemblyResult` 默认 repr 不泄露正文或工具参数。

聚焦测试为 `29 passed`，相邻回归为 `147 passed, 27 subtests passed`。这只是本地候选合同，不改变现有同步
`LLMProvider`、`capabilities.streaming=False`、严格 Flash v1、候选注册、默认模型、AgentLoop、Workbench、
Portal、Account、Auth、路由或 `production_media=0`。下一步先取得同一实现 SHA 的公共 CI 与供应商一致性证据，
再决定是否值得进入真实适配器接线；不得把本地合同通过写成领域或生产准入。

### RQ-193：智谱流式适配器一致性接缝（2026-09-01）

在不修改生产 Provider 的前提下，先用测试内 fake translator 验证智谱分块能否稳定落到 RQ-192 的中立事件合同。
`_FixtureZhipuStreamAdapter` 对正文/reasoning、工具别名与参数分片、坏形状/未知工具/空 choices、model/terminal
边界、异常 `abort()`、正文空白和 Trace 脱敏做逐项断言，并与现有 `ZhipuProvider.chat_stream()` fake-client 结果对照；
conformance 聚焦 `13 passed`。

提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA Actions run `33489903978` 已三 job 全绿且 head_sha 精确
匹配，且包含全部 Trace 脱敏断言。
因此决策仍是 candidate-only：不注册候选、不打开 `capabilities.streaming`、不改严格 Flash v1 2048/零额外调用、
默认模型、AgentLoop、ToolRuntime、Runtime Trace、预算、Portal、Account、Workbench、Auth、路由或
`production_media=0`。公共验证完成后进行候选接线裁决，决定 runtime 接入范围及预算/Trace/回退/失败门，
而非自动启用或进入 G53-7/黄金切片。

### RQ-194：候选级显式智谱→中立适配接缝（公共闭环完成，2026-09-01）

决策是把早期设计草案落成一个仍需显式取得、但已经可离线核验的接缝，而不是把它注册为产品默认能力。
`app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamAdapter`（非 `LLMProvider`）提供
`stream_events(request)` 和 `assemble(request, *, max_output_tokens=None, require_request_identity=True)`；
`ZhipuProvider.stream_adapter(*, tool_stream=False)` 是显式工厂，底层使用
`_open_stream_for_adapter()` / `_validate_stream_response_for_adapter()`，单次把 raw chunks 翻译成
`ProviderStreamEvent` 并交给 `ProviderStreamAssembler`。

实现遵守这些不可放宽的边界：可信 provider runtime profile 的输出上限为 1–8192，显式/请求 cap 只能收紧；默认要求
request identity；Trace、错误、repr 只保留 SHA-256 摘要，拒绝 Prompt、正文、reasoning、工具参数、Key 和 SDK 对象。
只有 EOF、合法 terminal、有效 Usage 同时出现才完成；取消、迭代器/翻译/关闭异常均 `abort()`/fail-closed；不 retry、
不 recovery、不执行 ToolRuntime、不注册 recovery，只允许 fake/local evidence。

提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588` 已完成，
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success` 且 head_sha 精确匹配；
`tests/test_zhipu_stream_adapter.py` 聚焦 `20 passed`。这只证明候选接缝可公共复现，不等于产品 runtime 接线或生产准入。
`capabilities.streaming` 继续 `False`，严格 Flash v1 仍 2048/零额外调用；默认模型、同步/既有流接口、AgentLoop、
ToolRuntime、Runtime Trace、预算、Workbench、Portal、Account、Auth、路由和 `production_media=0` 均不变，候选未注册。
下一门改为独立裁决候选 runtime 接线范围；不把该公共接缝写成 8-Core 生产能力，
也不宣称 8E/8F 完成。

### RQ-195：候选 runtime 接线架构评审（2026-09-01）

本轮决定不把 RQ-194 的显式 `ZhipuStreamAdapter` 直接包装成产品 `LLMProvider`，也不在 `AgentLoop` 增加隐式
streaming 分支。评审发现 `assemble()` 只交付拥有真实 EOF、合法 terminal 和有效 Usage 的完整 `stop`/`tool_calls` 流；
`length`、缺终止、缺 Usage、读取/翻译/关闭异常均 fail-closed，不能把 `StreamAdapterError` 当作候选恢复资格。

未来若获单独授权，先在 `app/evaluation/` 设计隔离的 `CandidateStreamEvaluationHarness`，调用前精确校验
`provider_id=zhipu`、`model=glm-5.3-flash`、candidate runtime profile v2 与 fresh-recovery policy v1 四元身份，
再通过只输出字段状态、finish code、Usage 数字、耗时和安全错误码的 `BoundaryObservation` 分类，交给独立 ledger 和
allow-list Trace 投影结算。观察接缝不得返回或持久化部分正文、reasoning、工具参数，也不得把不完整流包装成
`ChatResponse`；候选当前 `execution_allowed=false`，不得发送 recovery。

严格 Flash v1 的 2048/零额外调用、默认模型、`capabilities.streaming=False`、AgentLoop、Workbench、Portal、Account、
Auth、路由、预算/Trace 和 `production_media=0` 均不变。RQ-195 只完成架构评审；下一精确项是
`candidate-runtime-wiring-design / pending`，不宣称产品 streaming、领域准入或生产成熟度。

### RQ-196：候选 runtime 接线设计冻结（2026-09-01）

用户确认继续推进且基本决定采用 GLM-5.3-Flash。本轮将其记录为唯一主力候选目标，但只完成设计闸门，
不把候选静默提升为全产品唯一默认。冻结的 `CandidateRuntimeBinding` 必须精确绑定 provider/model、candidate
v2 runtime profile/policy 及 `primary`/`fresh_recovery` 尝试身份；错配、伪造和不连续 ordinal 在任何 Provider I/O 前拒绝。

候选流先经过共享事件校验，再分成完整 assembler 或 body-free `BoundaryObservation`。观察只允许生命周期、终止码、
字段状态、工具计数、有效 Usage 数字、单调耗时、model/request SHA-256 和安全错误码；正文、reasoning、工具参数、
Prompt、Key、SDK 对象和异常原文永不进入观察、Trace 或 repr。未来调用方隔离在 `app/evaluation/`，承载 v2 的 8192
单次 cap、90/120 秒窗口、`temperature=1`、`top_p=0.95`、SDK retries=0，并以 reserve→open→settle 严格结算最多
2 attempts、1 次额外调用、32,000 input、16,384 output、180,000ms；unknown Usage 不得当零，当前仍 `execution_allowed=false`。

本轮新增 ADR-0076、设计计划和学习 walkthrough，未改产品 Runtime、默认模型、`capabilities.streaming`、Portal、
Account、Workbench、Auth、路由或 `production_media=0`；当时下一精确项为
`candidate-boundary-observation-contract-implementation / pending`，该门已由 RQ-197 推进。

### RQ-197：候选边界观察合同本地实现（2026-09-01）

本轮将 RQ-196 的设计落成隔离 fake/local 合同。新增 `app/evaluation/candidate_stream_contract.py`，包含精确
`CandidateRuntimeBinding`、body-free `BoundaryObservation`、不可变终态快照、字段 presence/状态聚合、候选 v2
注入式 transport port 和独立 `CandidateStreamTrace`。`ProviderStreamEvent` 增加显式 null/缺失标记，并由完整
`ProviderStreamAssembler`、智谱翻译和候选观察器共同调用 `validate_provider_stream_event()`，统一 model、sequence、
tool、Usage 与大小限制。

观察器只保留生命周期、终止码、字段状态、工具计数、有效 Usage 数字、单调耗时、model/request SHA-256 和安全错误码；
正文、reasoning、Prompt、工具参数、Key、SDK 对象及异常原文不进入观察、Trace 或 repr。完整 `stop`/`tool_calls`、
`length` reasoning-only、缺 EOF/terminal/Usage、身份/序号/工具/预算/时钟/关闭异常及状态伪造均有矩阵断言；不完整
或异常流 fail-closed，不构造 `ChatResponse`，unknown Usage 不当零。

候选继续 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 2048/零额外调用，
`capabilities.streaming=False`，默认模型、AgentLoop、Worker、统一 Trace/预算、Portal、Account、Workbench、Auth、
路由和 `production_media=0` 不变；本批已改 evaluation/共享事件合同与相邻测试，但未改产品 Runtime，也未执行真实 API、
recovery、G53-7 或黄金切片。聚焦与相邻回归 `163 passed`，compileall、diff check、governance 已通过；全量本地首错
是未配置 `RIFTCOACH_TEST_DATABASE_URL` 的 PostgreSQL fixture。

RQ-198 已完成该公共 CI 门：提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run `33507627615`
三 job 全绿，公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。候选仍未注册、
`execution_allowed=false`，严格 Flash v1、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变，没有真实 API/Key、recovery、G53-7 或黄金切片。

当前唯一下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`；
下一轮只设计隔离 harness/ledger/Trace 接缝，本轮暂停，后续需用户明确继续。

### RQ-198：候选边界观察合同公共 CI 闭环（2026-09-01）

该证据只关闭公共可复现性检查，不构成候选注册或 8-Core 生产准入。

### RQ-199：采用 staged ledger 的隔离候选评估台设计（2026-09-02）

决定在 `app/evaluation/` 设计独立 `CandidateEvaluationHarness`，不把候选 adapter
包装成产品 `LLMProvider`，也不修改 `AgentLoop`。评估台采用 candidate-only staged
ledger：primary 必须在 I/O 前预留；真实 `BoundaryObservation` 形成后，才映射
`ResponseBoundarySnapshot`、重新运行精确 candidate policy 并冻结 recovery plan。
拒绝用 sentinel snapshot 预建账本，也拒绝请求结束后才 reserve。

一条 normalized stream 只经一次事件泵，共享事件校验后分别送入
`CandidateStreamBoundaryObserver` 与 `ProviderStreamAssembler`。observer 只保留状态；
assembler 只在单次评估内存中暂存完整结果。完整结果只能交给显式 evaluation-only
consumer，独立 `CandidateEvaluationReceipt` 只保存候选身份、生命周期、字段状态、
Usage/耗时、预算确定性和安全码；unknown Usage 不当零，不写入统一 `RuntimeTrace`。

当前 activation 仍 disabled，命中候选形状只记录 `awaiting_recovery`，不会发送第二条
流。严格 Flash v1 2048/零额外调用、`capabilities.streaming=False`、默认模型、产品
Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。本轮
只有 ADR-0077、实现计划与学习材料，没有产品代码、真实 API/Key、fresh-recovery、
G53-7 或黄金切片。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。

### RQ-200：实现隔离候选评估台（2026-09-02）

按 RQ-199 的设计，新增 `CandidateEvaluationHarness`，但不把它包装成产品
`LLMProvider` 或接入 `AgentLoop`。评估台采用 candidate-only staged ledger：primary
在 I/O 前预留，单次 normalized event pump 同时服务 body-free observer 与临时内存
assembler，真实边界观察完成后才重算 policy 并 settle；每个槽位严格只结算一次。

完整 `stop`/`tool_calls` 流才可经显式 evaluation-only consumer 短暂接收；缺 EOF/终止/Usage、
`length` 不完整、身份/序号/工具/预算/时钟或资源异常均 fail-closed，不构造产品
`ChatResponse`，不执行 ToolRuntime、隐式 retry 或 recovery。独立
`CandidateEvaluationReceipt` 只允许候选身份、生命周期、字段状态、终止/错误码、计数、
Usage/耗时、预算确定性和 SHA-256，unknown Usage 保持 unknown/None。

当前 activation 仍为 sealed `disabled`，候选未注册、不打开 `capabilities.streaming`；严格
Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均不变。harness 聚焦 `15 passed`，相邻回归 `102 passed`；RQ-201 已取得实现
提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 exact-SHA 公共 CI run `33536168224`（公共 pytest
`2193 passed, 145 skipped, 1 warning, 127 subtests passed`）。下一精确门是
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`，
先在单独授权后复核候选 recovery 的传输/预算/失败边界，再决定高级候选是否继续。

### RQ-202：候选 recovery 诊断边界复核（2026-09-02）

决定先把候选评估台的证据来源加固，再谈新的诊断版本。顶层回执状态、错误、attempt 决定/装配
和预算投影不得由调用方单独填写，必须由 body-free 观察与候选硬上限推导；单次 observer 截止为
90 秒，累计账本仍为 180 秒。旧同步诊断器直接持有真实 SDK/I/O 且把 unknown Usage 投影为零，
不作为新 recovery 诊断的实现基础。

本轮只做 fake/local 代码和测试，activation 继续 sealed `disabled`，不发真实 recovery、不注册候选、
不改产品 Runtime、默认模型、Workbench、Portal、Account、Auth、路由或 `production_media=0`。下一
精确项是
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`，
需新的明确授权。

### RQ-203：版本化候选 recovery 诊断协议设计（2026-09-02）

决定把候选 recovery 的下一步先冻结为独立的 evaluation 协议，而不是在旧同步诊断器上继续加开关。
ADR-0079、设计计划和学习材料共同定义 `glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0`，
绑定 provider/model、runtime profile、policy 与实现/计划/上下文/运行 SHA；请求只保存脱敏形状摘要。

协议时序固定为 `reserve → open → observe/assemble → settle → receipt`，每次潜在 I/O 先占槽位，
fresh recovery 是完整新请求，禁止 resume、SDK/AgentLoop retry 和 ToolRuntime 副作用。预算、Usage、费用、
分段延迟和失败第一现场都采用可审计的派生规则；未知资源保持 `unknown/null`，回执为原子 create-only、
canonical UTF-8/LF、body-free JSON，不写产品 Runtime Trace。

本门只有设计文档，没有实现、真实 API/Key、候选注册或产品接线；严格 Flash v1、默认模型、Portal、Account、
Workbench、Auth、路由和 `production_media=0` 不变，Stage 8/8E 继续进行中，8F 未开始。下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`，
实现需再次明确授权。

### RQ-204：实现版本化候选 recovery 诊断接缝（2026-09-02）

按 RQ-203 的协议设计完成隔离实现：`app/evaluation/candidate_recovery_diagnostic_v2.py`
负责 candidate-only staged ledger、primary I/O 前 reserve、一次 normalized event pump、
临时 assembler、body-free 派生 receipt、预算/费用/延迟/失败投影和 canonical create-only
JSON；`app/evaluation/__init__.py` 只导出评估 API，不把它包装成 `LLMProvider`，不注册
Provider 或产品 Runtime。

新模块聚焦 `22 passed`，候选相关回归 `67 passed`，流式/适配器/恢复合同相邻回归 `82 passed`，
compileall、静态 no-I/O/import 和 diff check 通过。unknown Usage 与未验证价格保持
`null/unknown`，控制异常在安全结算后继续抛出，disabled activation 永远不发送第二次请求。

该项仍属于 8-Advanced candidate evidence，不是 8-Core 生产能力；候选未注册、
`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用、
默认模型、AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变。没有真实 API/Key、fresh-recovery、G53-7、黄金切片、生产准入或 8F
证据。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`。

### RQ-205：版本化候选 recovery 诊断公共闭环（2026-09-02）

接受 RQ-204 实现提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 exact-SHA 公共证据和本地协议演练：
Actions run `33598541029` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，公共 pytest
`2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`；
fake transport 的一次 primary 演练写入临时 canonical body-free 回执。该决定只关闭公共可复现性门，
不等于真实模型质量、生产准入或 recovery 已开启。

候选仍 `activation_state=disabled`、`execution_allowed=false`、`capabilities.streaming=False`；严格
Flash v1 2048/零额外调用、默认模型、AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、
路由和 `production_media=0` 不变。当前下一精确项为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
真实 recovery、G53-7、黄金切片、生产安全/部署/合规与 8F 必须另行授权。

### RQ-206：候选 recovery 诊断一次真实主请求观察（2026-09-02）

接受在干净隔离工作树上对版本化候选诊断执行 1 次有界真实 primary 的结果：诊断提交
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run `33603143606` 三 job exact-SHA 全绿，
实现基线为 `90242822df0e47304700644572bc12f0a3aa88ad`。普通智谱 `zhipu/glm-5.3-flash` 流观察到
reasoning、可见正文、`stop` 与 EOF；首事件 `3078ms`、首个可见正文 `151453ms`、总延迟 `175875ms`。

由于 Usage 缺失、close 失败，且 90 秒 attempt 墙钟门在晚到事件中触发，回执必须保持
`fail_closed / elapsed_limit`、`assembled_complete=false`、费用 unknown；`calls_reserved/settled=1/1`，
不发第二次 recovery。`open_elapsed_ms=0` 只代表惰性流生成器的计时起点。持久 body-free 回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`，
`4355` bytes，SHA-256 `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`。

该决定只记录传输/完成度事实，不把它解释为 API/Key 失败、模型一般质量、领域准入或生产成熟度结论。
候选仍 activation disabled、未注册，`capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、
默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变，G53-7、
黄金切片、安全/部署/合规与 8F 均未开始。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
先离线设计/测试硬墙钟取消、流关闭和 Usage/终态尾帧处理，再另行裁决真实重测。

### RQ-207：候选流硬墙钟会话与 Usage 尾帧（2026-09-02）

接受 RQ-207 的本地实现证据，但不把它解释为产品 Runtime 或生产准入：四文件聚焦回归（deadline 10、v2 24、
real 8、adapter 25）统一为 `67 passed`，
本轮不读取 Key、不调用真实 API、不重试或发第二次请求。决策如下：

- 保留 legacy `CandidateStreamTransport.open_stream() -> Iterable` 兼容路径；hard mode 只有显式
  `session_opener` 才可用，若该 opener 返回 legacy iterable，必须在 opener 返回后校验并 fail closed。
- `CandidateStreamSession` 负责资源所有权；`CandidateStreamDeadlineSupervisor` 使用 attempt 起点的绝对
  monotonic deadline，超时只允许显式、协作式、非阻塞且幂等的 cancel/close，并丢弃截止后的迟到事件。
- 终态必须与 Usage 同帧，或终态后恰好一个 Usage-only 尾帧；重复/过早/终态后内容和空非 Usage 帧拒绝。
  缺失 Usage/价格保持 unknown/null，禁止合成零值；close 失败仅作次级证据，回执不得携带 provider body/exception。
- 同步 opener 可能阻塞越过计时器，SDK `close()` 是否非阻塞并唤醒 `next()` 尚未被 provider/public CI 证明，
  这是下一闸门；不得以本地 watchdog 推断硬截止已获生产保证。
- 8E 候选边界不变：`activation_state=disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`、未注册；严格 Flash v1 2048/零额外调用，默认模型、产品 Runtime、
  Portal/Account/Workbench/Auth、路由和 `production_media=0` 不变，Stage 8/8E 仍 `in_progress`。

> 历史快照（RQ-207 本地实现完成时）：当时的下一精确 checkpoint 曾为
> `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
> RQ-208 已完成该公共 CI，当前唯一指针以最新 RQ-208 决策段落为准。

### RQ-208：RQ-207 候选流硬墙钟与 Usage 尾帧公共闭环（2026-09-02）

接受 RQ-207 实现的 exact-SHA 公共 CI 证据，但不把它解释为产品 Runtime 或生产准入：提交
`015b022bfce6d03452f753794ac126a377f8355b` 的 Actions run `33613113829` 中 `pytest`、
`postgres-migrations`、`packaging-smoke` 三 job 均为 `completed/success` 且 `head_sha` 精确匹配；公共 pytest
为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为 `201 passed, 1 warning`，
本地四文件聚焦仍为 `67 passed`。本轮没有新的真实 API、重试或第二次请求。

该公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 非阻塞/能唤醒 `next()`，也不构成模型一般能力、
领域采用或生产成熟度结论；同步 opener 永久阻塞限制继续保留。候选仍 `activation_state=disabled`、
`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1 2048/零额外调用，默认模型、产品 Runtime、
Portal/Account/Workbench/Auth、路由和 `production_media=0` 不变，Stage 8/8E 仍 `in_progress`。

当前唯一下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
公共 CI 已闭环，真实重测或候选注册仍需新的明确一次性授权。

### RQ-209：候选真实流硬墙钟与关闭边界观察（2026-09-02）

接受本次一次性真实观察提供的“应用层硬墙钟触发并安全 fail closed”证据：在公共闭环树
`015b022bfce6d03452f753794ac126a377f8355b` 的实现/诊断身份下，只发送 1 次普通智谱
`zhipu/glm-5.3-flash` primary；`90015ms` 到达 attempt 截止，回执为 `fail_closed / elapsed_limit`，
首事件/打开计时 `3421ms`，reasoning 非空，但正文、terminal、EOF、Usage 均未见，费用 unknown。

拒绝把组合会话 `close_state=failed` 直接解释成供应商 SDK 成败；回执不足以区分 response、迭代器或其他资源，
也不足以证明 close 非阻塞/唤醒挂起读取。证据由本地提交
`0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存（回执 SHA-256
`56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`，公共 CI 尚未宣称）。

候选继续 activation gate disabled、activation_state=candidate 且未注册，默认模型、产品 Runtime、Workbench、前端、Auth、路由和
`production_media=0` 不变；不注册候选、不发 recovery/重试、不进入 G53-7 或 8F。若要拆分关闭资源状态或再次
真实观察，另立后续决策/ADR 并重新取得明确一次性授权；当前唯一下一 checkpoint 保持
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`。

### RQ-210：采用候选会话分资源关闭报告（2026-09-03）

决策：在不改 RQ-209 v2 receipt/schema 2.0.0 的前提下，为 `ZhipuStreamSession` 暴露仅内存、不可变、body-free
的 `ZhipuStreamCloseReport`。它区分 `iterator_state`、外层 `sdk_stream_state`、`composite_state` 和
`shared_resource`，close 逐资源最多一次并继续保留旧 `close_failed` 投影。范围严格限于候选评估接缝；不注册候选、
不打开 `capabilities.streaming`、不接入 AgentLoop/产品 Runtime，也不修改 Portal、Account、Workbench、Auth、
路由或 `production_media=0`。`cancel()` 仍同步调用 SDK close，因此不宣称底层 response cancel、非阻塞或唤醒能力；
若未来要持久化分资源状态或将报告作为稳定公共合同，必须另立 ADR 并升级 schema/allow-list/CI。

### RQ-211：接受一次 close/wakeup 观察，但不接受唤醒结论（2026-09-03）

接受在 exact-SHA 公共绿灯的 `c31127b3c780fe4c493966d8b60f942d3b773fd4` 干净快照上执行一次
candidate-only 真实探针；该 SHA 的 Actions run `33661910096` 三 job 成功。探针只发出 1 次普通智谱
`zhipu/glm-5.3-flash` 请求，SDK retries=0、父进程硬边界 30 秒，无 retry/recovery。canonical body-free
回执为 `908` bytes、SHA-256
`9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`。

接受的事实只有：会话已打开、调用数 1、首段读取 `78ms`、观察到 reasoning/content 类别，退出时 iterator、
SDK stream wrapper 和 composite 报告均为 `closed`。拒绝把 `observation_state=not_pending` 与
`reader_woke=false` 解读为唤醒成功或失败；本次没有形成 pending reader，所以 cancel 根本没有执行，底层
HTTP response 取消、非阻塞 close 和 pending `next()` 唤醒仍未被验证。

后续测试加固提交 `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c` 的公共 run `33662730304`
被外部取消，不记为成功，也不替换 c311 回执身份。候选仍 disabled/未注册，`execution_allowed=false`、
`capabilities.streaming=False`；严格 Flash v1、默认模型、AgentLoop、产品 Runtime、Portal、Account、
Workbench、Auth、路由和 `production_media=0` 不变。下一步等待用户裁决是否设计能稳定制造 pending-read
的新版协议；不自动追加真实请求、G53-7、黄金切片、生产准入或 8F。

公共验证补充：提交 `1c669e0` 的 Actions run `33666132282` 三 job exact-SHA 全绿（pytest
`2268 passed, 145 skipped, 1 warning, 127 subtests passed`；PostgreSQL `201 passed, 1 warning`）。
它只修复新回执在既有 provider capability 扫描中的显式分派，不构成第二次真实调用或 wakeup 结论；c311
仍是 RQ-211 唯一真实观察身份。

### RQ-212：采用候选 close/wakeup 离线 pending-read 回放

接受一个与真实 provider 回执完全分开的 evaluation-only 回放协议
`glm-5.3-flash-candidate-close-wakeup-replay` / schema `1.0.0`。固定的内存 Event 闸门
覆盖正常 EOF、取消后 reader 唤醒、取消返回但未唤醒、取消超时和取消抛出五种场景，并复用
RQ-211 的观察器派生每个 case 的结果。回执必须标记 `evidence_origin=offline_fake`、
`real_provider_observed=false`、`provider_call_count=0`、`network_used=false`，同时单独记录
`fake_session_open_count=1`；它不能进入 provider capability 结果目录，也不能复用 RQ-211
的协议或路径。

这项决定只证明本地 pending-read 分类、单次打开、脱敏和不可变回执可重复；不证明供应商
SDK close 非阻塞、底层 HTTP response 可取消或真实 pending `next()` 能唤醒。候选仍
disabled/未注册，`capabilities.streaming=False`，严格 Flash v1、默认模型、产品 Runtime、
Workbench、Portal、Account、Auth、路由和 `production_media=0` 不变。RQ-212 公共闭环已完成；
是否执行新的真实 provider 观察仍需单独决定。

### RQ-212 公共闭环事实（2026-09-03）

RQ-212 实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec` 的 Actions `33707313651` 三 job exact-SHA 全绿；
v2 离线回执 `data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`
为 `2220` bytes、SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`，三个身份 SHA 均绑定该实现提交。
这只关闭本地回放合同，不改变候选 gate、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由或
`production_media=0`；下一精确 checkpoint 为 `candidate-close-wakeup-real-observation / pending-user-authorization`。

### RQ-213：接受一次新的真实观察，但不接受 wakeup 结论（2026-09-03）

接受在 RQ-212 公共闭环后的 exact-SHA 公共绿灯提交
`a396412f7cd0f2e923536cf55f715dd56251aae5` 上执行一次 candidate-only 真实观察，
SDK retries=0、父进程边界 30 秒、无 retry/recovery/第二请求。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`
为 909 bytes，SHA-256=`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`。

接受的事实只有：会话打开、首段 172ms、观察到 reasoning/content 类别、状态为 `not_pending`，
以及 iterator/SDK stream/composite 投影均 `closed`。拒绝把 `reader_woke=false` 写成唤醒失败，
因为本次没有 pending reader、cancel 未执行；也拒绝把 `closed` 写成底层 HTTP response 或 provider
close 已证明。候选 gate、产品 Runtime、默认模型、Workbench、前端、Auth、路由和 `production_media=0`
保持不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`，
先裁决是否另立能稳定制造 pending-read 的新版协议。

### RQ-214：采用候选 SDK/HTTP transport gate 离线预检（2026-09-03）

接受一个独立于 provider capability 的 evaluation-only transport-gate 协议
`glm-5.3-flash-candidate-close-wakeup-transport-gate` / schema `1.0.0`。它在真实 OpenAI SDK、
显式 Zhipu 候选适配器和既有观察器对象链上接入本机 `MockTransport`，在完整 SSE 帧边界暂停，
分别覆盖 `after_first_event` 与 `before_first_event`；每阶段只允许一次内存请求。

预检的结论拆成两层：response close 后 reader 确实被唤醒，但并发 iterator 关闭可能出现
`client_wakeup_close_race`。因此不把本地 transport 结果当成智谱服务端原生能力，不在该预检中
静默修复适配器，也不把它提升为候选注册或产品默认模型。回执必须标记
`offline_sdk_transport_fixture`、`provider_call_count=0`、`network_used=false`，并保存在离线目录。

公共闭环后，如需继续，只允许在一次性授权下用同一 gate 包装官方 TLS transport 发出最多 1 次
真实候选请求；下一精确 checkpoint 为
`candidate-transport-gated-real-observation / pending-user-authorization`。Portal、Account、
Workbench、Auth、路由、AgentLoop 和 `production_media=0` 均不变。

RQ-214 离线回执已绑定实现提交 `4c220c5751288ad77c589d2e0e581690085803c0`，路径为
`data/evaluation/results/offline/zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json`，
`1693` bytes、SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`；
同 SHA Actions run `33712055286` 三 job 全绿：pytest `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`；PostgreSQL `201 passed, 2 warnings`；packaging-smoke 通过。
### RQ-215：接受一次 transport-gated 真实观察，但不接受生产能力结论（2026-09-03）

接受在 RQ-214 离线预检和 exact-SHA 公共 CI 后，以实现/观察器/输入计划身份
`2acdf795881733e70c9246c48f7147d5136821b5` 只发送 1 次真实 `zhipu/glm-5.3-flash` 请求；
SDK/HTTPX retries=0、父进程 30 秒、阶段 `before_first_event`，无 retry、recovery 或第二请求。
官方 TLS transport 外层 gate 进入，pending reader 形成并在 `31ms` 内唤醒；取消安全码为
`zhipu_stream_close`，iterator/composite 为 `failed`、SDK stream 为 `closed`，因此接受的结论
仅为 `client_wakeup_close_race`。

回执 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`
为 `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`，
保持 body-free。该结果只描述真实流启动后本机受控停顿下的客户端行为，不证明 provider-native
close/wakeup、模型一般能力、候选注册或生产 streaming。候选 gate、默认模型、产品 Runtime、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

### RQ-216：采用 reader-owned close 顺序修复（2026-09-03）

接受候选适配器对 `client_wakeup_close_race` 的本地修复：当 reader 正在执行 `next()` 时，取消
路径先关闭外层 SDK response，避免跨线程调用 iterator `close()`；reader 在自己的 `finally` 中
完成 iterator 收尾。无活跃读取时继续执行逐资源、最多一次的关闭。阻塞读取与两阶段离线 gate
聚焦回归 `61 passed`，compileall、差异检查和治理通过，真实 API 为 0。

该决定只覆盖候选 evaluation-only 生命周期合同，不改变候选 disabled/未注册、默认模型、产品
Runtime、Portal、Account、Workbench、Auth、路由、8-Core、G53-7、黄金切片或 `production_media=0`。
RQ-215 旧回执不可变；当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`。

#### RQ-216 公共验证补充

提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions `33726209532` 三 job exact-SHA
全绿；公共 pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL
与 packaging-smoke 通过。该证据只关闭候选本地关闭顺序修复的公共可复现性，不改变候选
disabled/未注册、默认模型、产品 Runtime 或 RQ-215 旧回执。当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`；是否重新执行真实观察需另行决定。

### RQ-217：接受关闭顺序修复后的单次 transport-gated 真实观察（2026-09-03）

接受在 RQ-216 公共 CI 闭环后，以实现/观察器/输入计划 SHA
`3e028b1217f1274152ba161993287f29188a1b73` 只发送 1 次真实
`zhipu/glm-5.3-flash` 请求。阶段固定为 `before_first_event`，SDK/HTTPX retries=0，父进程
30 秒，无 retry、recovery 或第二请求；候选仍不注册、不打开 `capabilities.streaming`。

官方 TLS transport 外层 gate 进入并形成 pending reader；`reader_woke=true`、
`cancel_status=returned`，iterator/SDK/composite close report 均为 `closed`，结论为
`client_wakeup_clean`。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`
为 `1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`，
body-free 且 canonical round-trip 通过；`gate_released=false` 是受控停顿协议的预期条件。

该决定只接受“本机受控客户端的唤醒与 reader-owned 收尾”这一层事实，不把它升级为
provider-native close/wakeup、模型一般能力、生产 streaming、G53-7、黄金切片或 8F 证据。
候选、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均不变。当前下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`；
没有新的独立授权前不再发送真实请求。

### RQ-218/RQ-219：接受协议通过与候选 8192 超时的分层结论（2026-09-03）

接受 RQ-218 的 G53-3 3/3 为普通 API/基础工具协议可达证据；接受 RQ-219 的单次候选
8192 观察为 `fail_closed / elapsed_limit`，不把它升级为模型质量、账号权限或生产 streaming
结论。候选保持 disabled/未注册，旧 Flash v1 的 2048/零额外调用合同、默认模型、AgentLoop、
Portal、Account、Workbench、Auth、路由及 `production_media=0` 均不变。下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / pending`；
先完成 fake/fixture 的档位—终态—Usage—恢复拆分，再决定是否另立域门。

### RQ-220：接受离线响应分层矩阵（2026-09-03）

接受 9/9 零网络场景作为解释 RQ-219 的本地合同证据：正常 stop/tool_calls、候选
`length`、缺/非法 Usage 与 elapsed timeout 各自保留独立状态；候选可识别不等于可执行。
不修改严格 Flash v1、默认模型、产品 Runtime 或前端边界。实现提交
`14254048f6ad2faea5c7b15801e5c7c11e0ceba4` / Actions `33738050233` 与回执提交
`ebb09a525b3340f31ba71821b894b4a142dfb4e7` / Actions `33738673832` 均三 job exact-SHA
全绿；回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
当前进入候选域门裁决，不自动追加真实请求。

### RQ-221：接受低思考候选探针观察（2026-09-03）

接受显式 candidate-only `low + 4096` profile 的一次真实无工具观察：实现提交
`c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions `33746833148` 三 job exact-SHA
全绿；只发送 1 次请求，结果为 `observed / finish=stop / usage=valid`，输入/输出
`1973/498`，延迟约 `20735ms`。回执提交
`ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，canonical SHA-256=
`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`，保持 body-free、
create-only。

该接受只覆盖冻结无工具上下文中的响应完成事实，不把低思考档提升为产品默认或候选准入；
不证明领域质量、工具多轮、成本/延迟稳定性、G53-7、黄金切片、生产准入或 8F。候选仍
`activation_state=candidate`、`execution_allowed=false`、未注册，严格 Flash v1、默认模型、
产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变。
当前唯一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`；
下一步先设计/裁决低档候选 held-out 领域门，不自动追加真实请求。
### RQ-222：接受低思考候选独立领域门设计（2026-09-03）

接受“显式评测作用域 + 共享请求策略 + 全新 held-out 资产”方案；拒绝重跑已消费的旧考卷，
也拒绝在领域证据前把低思考档注册为产品 Runtime。实现时保留产品注册校验，候选作用域
固定 `low + 4096`、90/120 秒、4/12 次调用、24,000/72,000 token 墙、无重试/恢复/修订和
首错停止，并关闭 deterministic fallback。当前只完成设计，provider calls=0；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`。

### RQ-223：接受低思考候选领域门离线控制面（2026-09-04）

接受先实现、不先真实调用的路线：用私有签发的 `CandidateEvaluationRequestPolicy` 与显式
`request_policy` 接缝复用共享 Agent 链，再由最后预算包装器执行 reserve-before-I/O、4/12 次
调用及 24,000/72,000 token 墙。LLM 工具重试为一次、deterministic fallback 关闭；产品
Runtime 注册表、严格 Flash v1、默认模型和前端/Workbench 边界不变。Fake Provider 新测试
5/5、相邻回归 118 passed，provider calls=0；下一步只做同 SHA 公共 CI，之后才另立 G53-3-L
和全新 held-out 资产。

### RQ-224：接受低思考候选领域门公共 CI 闭环（2026-09-04）

接受 RQ-223 的 exact-SHA 公共可复现性证据：实现提交
`d823cc40c3fcafb7167edccded87e185be4cae8a` 对应 Actions `33781369322`，pytest、
PostgreSQL migrations、packaging-smoke 三项均成功，公共 pytest 为
`2326 passed, 145 skipped, 2 warnings, 127 subtests passed`。本批 provider calls=0，
只关闭离线控制面的公共验证闸门，不授予候选领域采用或生产能力。候选继续
`candidate-only/disabled`，默认模型、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变；下一步才是新的 G53-3-L 与全新 held-out 资产，且需明确授权。

### RQ-225：接受低思考 G53-3-L 协议与新鲜资产离线实现（2026-09-04）

接受先完成离线控制面、再进入真实协议门的顺序：显式 `request_policy` 接入协议切片，
低思考候选固定 `low + 4096`、90 秒工具窗、最多 3 次调用，并以 body-free/create-only
报告收口；新三案例 Dataset、V1.1 Input Plan、Prompt/Context Snapshot 和合成 fixture
通过 no-I/O 身份及历史 marker 隔离校验。聚焦协议/资产与相邻回归 `20 passed`，
provider calls=0。候选仍未注册，产品 Runtime、默认模型、Portal、Account、Workbench、
Auth、路由和 `production_media=0` 不变；公共 exact-SHA CI 通过后仍须另一次明确授权，
不能自动执行真实协议或领域门。
