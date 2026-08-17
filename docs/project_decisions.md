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
