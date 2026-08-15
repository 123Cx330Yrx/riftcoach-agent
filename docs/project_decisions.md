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
