---
state_schema: 1
main_stage: 5
substage_group: "5D"
current_checkpoint: "5D-7"
status: in_progress
blocked_before: "5D-exit-review"
---

# RiftCoach 当前执行状态

> 本文档是“项目现在做到哪一步”的唯一事实源。路线职责看
> `docs/roadmap.md`，历史需求看 `docs/requirements_change_log.md`，本轮执行
> 细节看 `.planning/.active_plan` 指向的计划，决策演变看
> `docs/roadmap_change_history.md`。

## 状态元数据

- 最后更新：2026-08-15
- 主阶段：阶段 5，进行中
- 当前子阶段组：5D Python 受限 Agent Loop，entry design 与 5D-1 至 5D-6b 已完成；
  5D-7 Batch A-C 与 Batch D 的 D1-D5 已完成，DeepSeek V4 Pro Adapter 真实
  structured/tool 协议 3/3 calls 已准入；三场领域 held-out 的控制面以及独立输入计划、
  oracle-blind 生产 Executor 和真实门 CLI 已完成离线 TDD，并由提交
  `eb198354b3186f25b7d0455d7ed28725bc17e234`、GitHub Actions run `31799394506`
  完成 exact-SHA 公开验证；真实 DeepSeek 领域 held-out 已执行一次并在首个正常案例因
  `unsupported_parallel_tool_calls` 不准入，后两例按首错停止跳过；不可变结果归档提交
  `26b668d0ce594e648a692cd2caf831c86125fede` 已通过 Actions run `31810164628`；ADR-0022
  的多 ToolCall 批次离线 TDD 已由提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 完成，
  Actions run `31817798170` 对精确 SHA 已成功
- 唯一下一步：5D-7 零调用设计一个全新、未污染的真实领域采用门；旧 Dataset 1.1.0
  不得重跑，不读取 Key、不实现真正并发或直接宣称 DeepSeek 领域准入
- 禁止越过：5D-7 完成前不得进入 5D exit review、5E 或统一 AgentRuntime；DeepSeek
  领域调用必须先完成执行接缝离线 TDD 与公开 exact-SHA CI，不能用已通过的低层协议、
  候选选择或发布热度替代领域质量证据

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 已完成 | development v2 为 23/23；independent holdout v1 单次运行后为 11/12，唯一失败已原样保存并分类 | 进入维护；holdout v1 永不用于调节当前规则 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 已完成 | ADR-0010 比较排除词、LoL 域信号、澄清、LLM 与 Embedding；决定 V1 暂缓模型兜底并定义重新采用门槛 | 进入维护；新鲜数据满足门槛后才能用新 ADR 重开 |

## 5D 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成证据 |
|---|---|---|---|
| 5D-entry-design | 审计现有接缝、比较组合方案、冻结数据流与教学顺序 | 已完成 | 5D 设计文档、ADR-0011、治理检查 |
| 5D-1 Skill Run Boundary Hardening | 统一 I/O 非空文本、selected identity、run_id 和输入 Artifact 绑定 | 已完成 | 设计/TDD 文档、`SkillExecutionBoundary`、共享 run ID/Artifact 编码、合同与篡改测试 |
| 5D-2 Context Builder V1 | 两个 Skill 的最小上下文、信任标签、确定性裁剪和 ContextSizer | 已完成 | 设计/TDD 文档、`ContextBuilderV1`、两个 Skill allowlist、citation/注入/预算边界测试 |
| 5D-3 Skill Run Compiler & Budget Enforcement | Manifest 权限/预算编译为 AgentRunRequest，并约束累积上下文 | 已完成 | 设计/TDD 文档、`AgentRunCompiler`、完整消息估算、逐轮 Context 门禁与协作式总 deadline 测试 |
| 5D-4 Evidence-Aware Agent Draft Preparation | AgentLoop + knowledge.search 生成 draft 与 KnowledgeEvidence | 已完成 | 共享 evidence converter、`SkillAgentDraftPreparer`、两个真实 Skill + Fake Provider + 真实 `knowledge.search`，成功/拒答/去重/冲突/失败与停止边界测试 |
| 5D-5 Harness Composition & Typed Terminal Output | 通过 DraftPreparationStep 接入单一发布门禁 | 已完成 | 统一 preparation 合同、旧顺序 Adapter、`SkillReviewExecutor`、Artifact 驱动 typed output、两个真实 Skill 的 Fake Provider + 真实 RAG + Harness 端到端测试 |
| 5D-6a Structured Output Contract | Provider-neutral schema、Pydantic 校验和有限修复 | 已完成 | `StructuredResponseContract`、能力门禁、严格 Evaluation Pydantic 模型、一次 repair、fail-closed 与 Harness 降级测试 |
| 5D-6b Real Provider Capability Gate | 实测首个 Provider，并为第二 Provider 决策提供真实证据 | 已完成（部分采用） | P1-P5 5/5、真实 Adapter 协议 3/3 calls 通过；真实 recent-form 领域运行只执行一次并在 1 个领域 call 后未形成统一 `ChatResponse`，无工具/证据/Evaluation，领域 `admitted=false`，Harness 安全降级；ADR-0012 准入最小协议、拒绝领域能力并暂缓第二 Provider |
| 5D-7 Prompt/Context & Domain E2E Evaluation | 工具选择、事实/引用、注入、质量/成本/延迟评测 | 进行中（旧真实 DeepSeek held-out 未准入；多 ToolCall 离线修复已由 `037a47f` / Actions `31817798170` 公开验证） | Batch A：分层合同与 10 个记录型 development 控制样本；Batch B：组件/案例双层 SHA-256 快照和零调用 admission；Batch C：ADR-0015、7 个 `offline_executable` development 场景及一个真实 unsafe publication；D1-D2：`coach_evaluation@1.1.0` 安全合同、不可修订 blocking policy、7 场 secure offline development 基线，task/failure accuracy 均 1.0、unsafe publication 0、external calls 0；D3：3 场独立 held-out，`calibration_excluded=true`；D4-D5：ADR-0018、独立 DeepSeek Adapter、失败观察、预算/停止门与 3-call 真实协议准入；生产领域门在 `205397f` 上只执行一次，首例以 `unsupported_parallel_tool_calls` fail closed，结果由 `26b668d` / Actions `31810164628` 固定；ADR-0022 已以本地 Fake SDK 纵向链证明修复兼容性，下一步必须设计新鲜领域采用门，不重跑旧考卷 |
| 5D-exit-review | 对照全部证据和 5E 前置项 | 未开始 | 5D 各项完成前不得进入 |

## 当前真实能力边界

已经存在的实现：

- 三态路由结果：`selected`、`rejected`、`ambiguous`；
- 无可用 Skill、无匹配 Skill、多 Skill 同时命中的明确原因码；
- Manifest 声明式必需信号组与排除信号；
- 排除信号在 Router 算法与 `RouterDecision` 合同两层都是硬否决；
- `recent-form-review` 与 `single-match-review` 两个真实用户 Skill Contract；
- 单局输入会验证 Summary v1.0、唯一目标 match、短局和 Timeline 缺失边界；
- 两个真实候选的近期选择、单局选择、混合范围歧义、裸 ID 拒绝和域外否决测试；
- 旧 15 条参与过单 Skill 规则校准的案例已归档，并有 SHA-256 来源记录；
- 双 Skill development v2（23 条）与 independent holdout v1（12 条）已建立；
- 评测 CLI 会校验数据集角色、案例数量、候选 Skill name/version 快照；
- development v2 已正式运行并保存到
  `data/evaluation/results/skill_router_v1_development_baseline.json`：23/23 精确匹配，
  selection/rejection/ambiguity accuracy 均为 `1.0`，false-selection rate 为 `0.0`；
- development 明细中没有误路由；该结果只支持冻结当前开发规则，不是泛化证据；
- independent holdout v1 已单次运行并保存到
  `data/evaluation/results/skill_router_v1_holdout_baseline.json`：11/12 精确匹配，
  selection/ambiguity accuracy 为 `1.0`，rejection accuracy 为 `0.8333`，
  false-selection rate 为 `0.1667`；
- 唯一失败 `holdout_device_performance_false_friend` 把“分析一下我最近键盘的表现”
  误选为 `recent-form-review`；实现符合当前字面合同，产品期望拒绝，分类为确定性
  Router 的域语义局限；
- 5C-6 已完成采用决策：确定性 Router V1 保持不变，不根据 holdout 增加“键盘”
  排除词，也不引入 LLM/Embedding；优先等待类型化产品入口、会话澄清与新鲜误路由
  数据，具体重新采用门槛见 ADR-0010；
- 5C 退出复核将命中决策的证据身份收紧为必须与候选 Skill 身份完全一致；
- holdout 冻结点元数据已从不包含双 Skill 合同的 `cfd2084` 更正为实际双 Skill
  合同提交 `4103d42`，没有修改案例、期望、规则或既有结果；
- 5D entry design 已完成源码级接缝审计；ADR-0011 决定 AgentLoop 只作为
  evidence-aware draft preparation，ReviewHarness 保持唯一评测和发布控制；
- 5D 已拆为 5D-1 至 5D-7 和 exit review；拆分本身不是功能实现；
- 两个 Skill 的关键输入输出文本现共享去空白、非空、集合去重规则，Skill 输出
  `run_id` 使用统一安全目录组件合同；
- selected `RouterDecision` 现在同时锁定 Skill 名称与版本，执行前必须与 Catalog
  中当前 `LoadedSkill` 的 Manifest 身份完全一致；
- `RunManifest`、`FileRunStore` 与 Skill 执行请求共享同一跨平台 run ID 规范，拒绝
  路径、盘符、Windows 保留名和超长值；
- `SkillInputArtifactBinding` 使用 Harness 实际 JSON/text 字节编码记录 Summary 与
  确定性报告的 kind、schema version 和 SHA-256；5D-5 已在 terminal output 前逐项
  核对真实落盘记录、物理字节与该内容承诺；
- `SkillExecutionBoundary` 会拒绝非 selected、缺失/漂移 Skill、错误 input model、
  run 不一致和内容/元数据篡改，并返回与调用方 payload 脱钩的输入快照；
- `ContextBuilderV1` 把内部 Policy 与已校验 SKILL.md 固定为 system/instructional，
  把确定性事实、用户请求和初始知识引用固定为 user/data-only；
- 近期复盘只接收 allowlisted scope、aggregate、样本边界、完整确定性报告和最多
  10 个可选 match 投影；单局复盘只接收唯一 target row 与不含其他 match 的精确
  报告行，不注入 `recent_summary`；
- Timeline unavailable 的 null/empty/error 与短局边界保持原义；failed-match 原始异常
  和未知 Summary 扩展字段不会自动进入上下文；
- Manifest context ceiling 不可被调用方提高；required sections 超限时 fail closed，
  optional match/citation 按优先级完整保留或省略，省略 ID 可审计；
- `ContextBundle` 消息必须是 sections 的规范渲染；`AgentRunCompiler` 会重新核对
  run/Skill/version、Manifest ceiling、实际消息大小与工具注册状态；
- `AgentRunCompiler` 只从已验证 Manifest 映射工具白名单、迭代、工具调用和总超时，
  从 `ContextBundle` 映射消息及有效 Context ceiling，并记录安全输入摘要 metadata；
- `DeterministicContextSizer` 现在计算 role/content、ToolCall id/name/arguments 与 Tool
  result metadata 的完整消息 envelope，仍只是 tokenizer-free preflight；
- `AgentLoop` 在每次 Provider 调用前重新估算累计消息；初始或 Tool Observation 后
  超限均以 `context_budget_exceeded` 停止，不再继续调用 Provider；
- Manifest `timeout_s` 被收紧为协作式总 deadline；Provider 获得递减剩余时间，
  ToolRuntime 取运行剩余时间与工具 policy timeout 的较小值，耗尽后以 `timeout` 停止；
- 旧 `LocalRagAdapter` 与新 Agent 路径共用 fail-closed 的知识 payload 转换器；只有
  实际成功且归因字段合法的 `knowledge.search` ToolResult 才能生成稳定 K1..Kn、
  去重 source IDs 与 `KnowledgeEvidence`，重复 chunk 归因冲突会被拒绝；
- `SkillAgentDraftPreparer` 使用 AgentLoop 的同一 ToolRegistry 编译并执行请求，只在
  `completed/final_response` 且最终文本非空时生成尚未发布的 `CoachDraft`；失败知识
  工具、非知识工具、坏 payload 与预算/重复/超时停止均 fail closed；
- `recent-form-review` 与 `single-match-review` 已在 Fake Provider 下通过真实 Catalog、
  Router、ExecutionBoundary、ContextBuilder、Compiler、AgentLoop、ToolRuntime 与本地
  `knowledge.search`；模型只在 Markdown 声称的虚假来源不会进入 Evidence；
- `DraftPreparationStep` 现在是 ReviewHarness 唯一草稿准备接缝；旧 Retriever/Generator
  通过 `SequentialDraftPreparer` 兼容，新 Agent 路径返回同一 draft/evidence 合同，
  没有第二套 Harness 控制流；
- `SkillReviewExecutor` 校验 execution/context 身份，只从 Skill Manifest 映射质量阈值
  和 deterministic fallback，并把 Agent 草稿交给现有 Evaluator/修订/发布状态机；
- `SkillTerminalOutputBuilder` 只从 terminal Manifest 和完整性校验通过的 FINAL_REPORT、
  最终 attempt Evaluation、RETRIEVAL_EVIDENCE 及输入 Artifact 构造 Manifest 声明的
  Pydantic Output；rejected 不暴露报告，降级只返回确定性报告；
- 两个真实 Skill 已在 Fake Provider 下完整走过 Catalog、Router、ExecutionBoundary、
  ContextBuilder、AgentLoop、真实本地 `knowledge.search`、唯一 ReviewHarness 与 typed
  output；该证据不等于真实 Provider Tool Calling；
- 生产 `ZhipuProvider` 已在离线 TDD 中实现 system/user/assistant/tool 四类消息、
  ToolSpec、AUTO/NONE、JSON mode、请求级 `knowledge.search` 可逆别名和 ToolCall
  规范化；REQUIRED、别名冲突、未知别名、非严格 JSON、重复/并行 ToolCall、非空
  reasoning、坏 content 与尚未准入的 structured+tool 同轮组合均 fail closed；
- `AdapterProtocolSliceRunner` 通过同一个 `BudgetedProvider` 把结构化直调和现有
  `AgentLoop` 两轮往返约束在精确 3 次外部调用内；A1 失败会跳过 A2，第 4 次调用会在
  进入底层 Provider 前被拒绝；
- A1 复用 5D-6a 的 `EvaluationResponseModel` 与严格 decoder；A2 只注册固定、只读、
  幂等、无重试/无缓存的 `knowledge.search` fixture，并要求一次 ToolCall、一次成功执行
  和精确终止标记；
- CLI 新增显式 `adapter_protocol` scope，必须同时提供真实调用确认与精确
  `max_calls=3`，OpenAI-compatible SDK 自动重试固定为 0；公开结果只保存安全错误码、
  调用/Token/响应计数和 SHA-256，不保存 Prompt、模型原文、observation 或原始异常；
- 当前本地完整回归：`415 passed, 103 subtests passed`；协议/CLI/结果合同聚焦回归
  `22 passed`；compileall 与 diff check 通过；
- 协议控制器提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51` 的 GitHub Actions
  run `31625669630` 全部通过后，只执行一次真实 `adapter_protocol/3`：A1 使用 1 call，
  A2 使用 2 calls，总计 3/3，二者均 passed，`admitted=true`；
- 真实 A1 为 427/59 tokens、2344 ms；A2 为 562/36 tokens、5360 ms，finish sequence
  为 `tool_calls -> stop`，工具调用/执行均为 1；未取得可靠单价快照，因此成本保持 null，
  不伪造为 0。
- `DomainSkillSliceRunner` 已离线组合真实 `recent-form-review` Catalog/Router/Boundary、
  Context Builder、AgentLoop、本地 `knowledge.search`、唯一 ReviewHarness 和 typed output；
  历史协议结果必须 `admitted=true`、精确 3 calls、Provider/model 一致，并记录文件 SHA-256；
- Agent 与 Harness 共享 `ExternalCallBudget(max_calls=4)`；happy path 为 Agent 2 calls +
  Evaluation 1 call，剩余 1 call 只允许 Evaluation 格式修复；revision 后再评测会在进入
  底层 Provider 前失败关闭，准入专用 SDK/Tool 自动重试均为 0/单次尝试；
- 真实领域 CLI 必须显式确认累计 `max_calls=7`，只允许批准结果目录，要求干净已提交的
  工作树并拒绝覆盖既有领域证据；Harness 原文只写系统临时目录，公开报告不保存
  Prompt、模型正文、Observation、原始 request ID、异常或 API Key；
- 领域控制器聚焦回归为 `23 passed`，相邻纵向比例回归为
  `141 passed, 29 subtests passed`，完整回归为 `430 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness SDK/敏感文件边界和 dry-run 均通过。所有领域证据仍为
  Fake Provider 离线证据，仓库中尚无真实领域结果文件。
- 领域控制器提交 `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 已推送到
  `origin/main`；GitHub Actions run `31657764638` 对该精确 SHA 的全测试、两套 RAG、
  compileall、Harness SDK/敏感文件边界和 dry-run 全部通过，CI 未调用真实 Provider。
- 真实 recent-form 领域切片随后只执行一次：使用 1 个领域 call，累计调用为 4/7；
  该计费请求没有形成进入 Agent 结果的统一 `ChatResponse`，因此 response/tool/evidence
  均为 0，也没有进入 Evaluation；公开结果为 `admitted=false`、
  `knowledge_round_trip_incomplete` 和 terminal `degraded`；
- 这次 `degraded` 证明确定性 fallback 在真实外部失败时阻止了未经评测草稿发布；它不
  证明 GLM 报告质量。当前脱敏证据不能继续区分 Adapter 规范化拒绝或其他统一响应前的
  Provider 错误，且没有质量分或可靠成本估算；
- ADR-0012 据此分层收尾 5D-6b：Zhipu Adapter 最小 structured/tool 协议准入，
  GLM-5.2 recent-form 领域能力不准入；不重跑、不临场调 Prompt、不立即接入第二
  Provider，真实失败进入 5D-7 的评测与错误归因设计。
- ADR-0014 让后续领域实验强绑定 Prompt/Context 语义身份：组件层覆盖 Skill Manifest/
  Instructions、Context Policy、`knowledge.search` 合同、Evaluation Schema/事实投影与
  prompt builders；案例层覆盖输入 Artifact、typed options、实际 section、最终消息与
  Context 预算；
- 冻结快照 `recent-form-prompt-context-v1` 的自摘要为
  `88af3ed94e2458dc67e92c311de3543ca23c5923c0591ad83cfa3d2db6fd95e0`；
  Domain Dataset/Candidate/Result 已升至 Schema 1.1 并强绑定该 ID/SHA；
- `prepare_domain_e2e_experiment.py` 会在 Provider 前从当前真实 Catalog、Router、
  ExecutionBoundary 与 ContextBuilder 重建快照，核对冻结快照与 Dataset 后才产生
  `admitted=true`；当前 admission 的 `external_provider_calls=0`；
- 快照和 admission 只保存安全元数据及摘要，不保存 Prompt、玩家事实、模型正文、
  Tool Observation、异常、request ID 或 Key；它们是实验前置身份，不是 5E Trace。
- Batch B 聚焦测试为 `20 passed`，相邻纵向回归为 `87 passed, 4 subtests passed`，
  完整回归为 `450 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/
  tracked-data、dry-run、快照正文脱敏、治理和 diff check 均通过；
- Domain E2E 1.1 基线与 admission 已从 CLI 临时输出逐字节复现；功能提交
  `e56b00091ef2ab299af692e902945b8342fbc99e` 已推送，GitHub Actions run
  `31690698734` 对该精确 SHA 全部通过。
- ADR-0015 采用脚本 Provider 驱动真实本地控制流，而不是继续手填 Candidate 或立即
  调用真实模型；新增 Schema 1.2 `offline_executable` Candidate，要求零外部调用且每个
  案例都有安全 provenance SHA-256；
- Batch C 的 7 个 development 场景均先通过 Batch B admission，再真实运行 Catalog/
  Router/Boundary、ContextBuilder、AgentLoop、`knowledge.search`、ToolRuntime、本地混合
  RAG、Evidence 构建和唯一 ReviewHarness；只有 Provider 响应为确定性脚本；
- 可执行场景覆盖成功、缺工具、错误 90% 胜率、未知 `[K999]`、用户注入、RAG 注入和
  Evaluation 漏判注入。最后一个场景实际被 Harness 发布，再由分层评测标记
  `unsafe_publication`，因此 1/7 不安全发布率是保留的开发 Bad Case，不是通过率；
- Candidate 中的 fact/citation/injection 结论从实际 draft、evidence Artifact 和 canary
  probe 提取，公开 Candidate/Result 不保存 canary、错误事实、Prompt、报告、工具原文、
  request ID、异常或 Key；CLI 重跑与冻结文件逐字节一致，外部调用为 0；
- Batch C 聚焦/相邻测试为 `25 passed`；完整回归为
  `455 passed, 103 subtests passed`。两套 RAG、compileall、Harness SDK/tracked-data、
  artifact 脱敏、治理、diff check 和 Harness dry-run 均通过；
- 这些结果证明离线实验接线和本地发布边界可复现，不证明任何真实 Provider 的领域
  质量或通用抗注入能力；当前 Evaluation Schema 也没有专用 injection issue category。
- Batch D 入口审计确认，现有 `ChatEvaluationAdapter` 只把确定性 fact pack 与待审报告
  放入 Prompt；虽然 `EvaluationRequest` 携带 `KnowledgeEvidence`，Evaluator 当前看不到
  用户原话、实际知识证据或信任标签。原地增加 issue 枚举既缺输入又会破坏 Batch A-C
  的 `coach_evaluation@1.0.0` 历史身份；ADR-0016 因此保留 1.0.0，D1-D2 已离线迁移并
  接入 1.1.0 安全评测合同与 blocking policy；D3 已创建独立 held-out，已知 canary 只
  作为实验 oracle，不进入生产关键词黑名单；
- ADR-0016 还冻结了后续门：D1/D2 离线迁移通过并冻结后才创建独立 held-out；真实首轮
  只比较同一冻结合同下的正常、用户注入和知识注入 3 场，每 Provider 每场最多 4 calls、
  领域最多 12 calls、`max_revisions=0`、SDK retry 为 0；第二 Provider 另需新 ADR 与最多
  3-call Adapter 协议门；
- ADR-0017 原先以协议成本为主选择 V4 Flash；经用户追问和 D5 目标复核，ADR-0018
  保留其历史并将唯一候选更正为 DeepSeek 官方 `deepseek-v4-pro`。独立 Adapter、
  non-thinking、最多 3-call 协议 + 12-call 领域预算、每案例 4000 tokens、每请求最多
  1024 output tokens、GLM ¥0.50 与全局/单 Provider 停止规则不变；按 Pro 峰值价把
  DeepSeek 停止线更正为 `$0.10`。选择候选不等于已经实现、调用、准入或设为默认模型。
- ADR-0019 保持当前 Pro-only 5D-7 准入门不变，并纠正未来 Flash 分层的归属：该工作
  最早在 5P 后、默认等待阶段 6 的真实 API 调用、Trace、成本或延迟 Bad Case，以横向
  Provider 优化门比较 Pro-only、Flash-only 和 Flash 默认/Pro 有界升级；5F 仍只负责
  Pi / Claude Agent SDK Runtime 采用实验。当前不增加 Flash 配置、调用或自动路由。
- D4 聚焦回归为 `68 passed, 15 subtests passed`，完整回归为
  `460 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/敏感文件边界、
  Harness dry-run、文档密钥模式扫描、governance 和 diff check 均通过，外部调用为 0。
- D5 新增独立 `DeepSeekProvider`，冻结 `https://api.deepseek.com`、
  `deepseek-v4-pro`、non-thinking、non-streaming、JSON mode、请求级工具别名和严格
  finish/usage/错误语义；它没有注册为产品默认 Provider，也没有复用 Zhipu Adapter
  冒充厂商无关实现；
- D5 让 `AgentRunStatus`、`AgentStopReason` 与安全 `error_code` 组成的不可变失败观察
  穿过 draft preparation 接缝。真实 AgentLoop Provider failure 测试证明 Harness 仍只
  返回确定性 `degraded`，同时上层能区分认证等安全来源，不保存 Prompt、模型正文或
  原始异常；
- 实验 ledger 在 I/O 前占用调用并检查 scope/cumulative call、每请求 output、累计
  observed Token 与估算金额；SDK 失败不退还调用，usage 缺失不按 0 结算，任一
  `unsafe_publication` 会触发全局停止。它是应用层实验门，不是厂商账户硬限额或 5E
  统一 Trace；
- D5 no-I/O preparation 只核对干净 Git SHA、公开 CI SHA、冻结 held-out 与
  Prompt/Context snapshot；不加载 `.env`、不读取 Key、不创建 OpenAI client、不运行
  held-out。Fake SDK 的 3-call 协议回归只证明 Adapter 映射和控制流，不证明 Pro 的
  真实能力；
- D5 聚焦/相邻回归已经通过，当前完整回归为 `505 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness dry-run、SDK/tracked-data 边界、governance 与 diff
  check 均通过。功能提交 `e68a8e4542ed72d31d5d46e569a11d9292048540` 的 GitHub
  Actions run `31764109304` 全部通过；同一干净 SHA 的 no-I/O preflight 随后通过，
  `external_provider_calls=0`、`held_out_executed=false`。

当前不能声称：

- GLM 或任何真实 Provider 已完成领域 Skill/Harness 准入；当前生产 `ZhipuProvider`
  只通过最小 Provider-neutral structured/tool 协议切片，真实近期复盘领域链路已尝试
  但未准入；
- 真实模型生成的新 Coach 报告已经通过当前端到端领域评测；本次没有统一响应进入
  Agent，也没有草稿、知识证据、Evaluation 或质量分；
- 默认 ContextSizer 等于真实厂商 tokenizer 或真实 Token Usage；
- trust/JSON 分层已经彻底解决 Prompt Injection；
- Batch C 的脚本 Provider/canary 已证明真实 GLM、DeepSeek 或 Qwen 抗注入；
- DeepSeek V4 Pro 已通过领域 Skill/Harness 准入、成为产品默认模型或普遍优于
  Qwen/GLM；真实领域 held-out 已运行但未准入，当前只准入最小 structured/tool
  Adapter 协议；
- 已经实现 Tool Observation compaction，或协作式 deadline 能硬中断任意阻塞函数；
- 路由对自然语言具有充分泛化能力；
- 小型合成 holdout 已证明路由对自然语言充分泛化；
- 已把 holdout 失败用于调节 Router 规则；
- 已实现 LLM Router fallback 或修复设备域假朋友；
- Router 已执行 Skill、Tool、Harness 或模型调用。
- 5D-1 的内容承诺已经等同于真实 Harness Artifact 落盘或 Agent 执行。
- `user_utterance` 已通过统一 Runtime/Trace 与最初 `RouterRequest` 形成不可变来源链。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 阶段 0-4 已形成 V1；阶段 5 完成 5A、5B、5C、5D entry design 与 5D-1 至 5D-6b；5D-7 已形成安全离线基线、DeepSeek 独立 Adapter/真实最小协议、领域控制接缝与真实门，并在 development 中补齐多 ToolCall 批次严格传输、整批预检和顺序执行 | 阶段 5、整个 5D、DeepSeek 领域质量、生产默认切换或报告质量准入已完成；离线 Fake SDK 通过也不改写旧真实 held-out 的拒绝结论 |
| 项目理解 | 已区分控制面 admission 与数据面 Provider 调用、Dataset oracle 与案例执行计划，也已区分 Provider/Model/Multi-Agent、协议/领域/产品三层门，以及累计/范围/单例调用与 Token 预算 | 离线合成 executor 能评价模型智力/在线可用性，执行接缝等于真实领域准入，或 3 场 held-out 能证明通用生产质量 |
| 参考资料 | EchoMind、AGI-Saber、Sea/OpenResearch 已做源码/文档审计并建立选择性映射 | 已经接入或复用了这些项目 |
| GitHub/部署 | 领域执行接缝提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已公开，exact-SHA CI run `31785253957` 成功；正式网页仍未部署 | 执行接缝公开可复现等于真实案例计划/领域 held-out 已运行、最小 Adapter 协议等于领域/产品准入、最终厂商选型或 Web Agent 可用 |

## 已裁决的首批 Skill 与事实审查边界

2026-08-05 的讨论同时确认了两点：

1. 先用一个 `recent-form-review` 样板稳定 Skill Contract 和 Router；
2. 首批宏观能力仍包含近期复盘、单局复盘和报告事实审查，并曾把三者都称为
   Skill，要求在 5C-4 后补齐再完成真实多 Skill 路由评测。

源码级复核发现，事实审查并不是缺失的第三个工作流：`EvaluatorStep`、
`ChatEvaluationAdapter` 和 `ReviewHarness` 已经提供类型化输入输出、复用入口、
修订预算和强制发布门禁。把它再包装成 Skill 只会复制合同。

- `recent-form-review`：已存在的用户可路由 Skill；
- `single-match-review`：已建立的第二个用户可路由 Skill；
- 报告事实审查：继续作为 Harness `EvaluatorStep` 强制执行，不是 Skill。

未实现的调用模式合同和 `report-fact-check` Skill 已在写代码前取消。实施顺序修正
为单局 Skill、真实双 Skill 路由评测、模型兜底决策。详细裁决见 ADR-0008 和
ADR-0009。

## 2026-08-06 阶段漂移事件

### 发生了什么

原计划明确包含 5C-1 至 5C-6，但一次实现批次把 5C-3 的代码、5C-4 的部分
拒绝/歧义行为和 5C-5 的初步开发评测一起完成后，文档被直接更新成“5C
完成，下一步 5D”。这把“代码已提前存在”误写成了“原检查点已经逐项完成”。

### 根因

- 原始 5C-1 至 5C-6 清单只存在于长对话，没有写进仓库；
- 旧 `.planning` 任务停在 2026-08-01，且没有 `.active_plan`；
- 没有根级 `AGENTS.md` 强制恢复上下文和同步状态；
- 多份状态文档并存，却没有唯一当前状态源；
- 实现计划错误地把一个批次的测试通过当成整个 5C 的完成条件。

### 修复原则

- 恢复原有 5C-1 至 5C-6 边界，不回滚已经写出的有效代码；
- 提前实现的内容回到原子阶段逐项讲解、复核和验收；
- 以后“继续”只推进本文件列出的唯一下一步；
- 每次状态变化同时更新当前状态、活动计划和冲突文档。

### 持久化与自动保护

- 本文件头部的机器可读元数据与正文共同构成同一个唯一状态源；
- `.planning/.active_plan` 指向当前任务的计划、发现和进度三份持久记忆；
- `docs/requirements_change_log.md` 追加记录跨轮次长期要求，不静默覆盖旧决定；
- `scripts/check_project_governance.py` 在本地和 CI 核对当前检查点、活动计划、
  九阶段编号、需求编号和工作约束；任何冲突都先阻止功能推进；
- 自动检查降低再次漂移的概率并让错误可见，但不能替代用户对阶段验收的确认。

## 下一检查点的范围

`5C-5-prep-1 Skill Invocation Contract` 与 `5C-5-prep-3 report-fact-check Skill`
已在功能代码开始前由 ADR-0009 取消，并保留在历史记录中。

`5C-5-prep-2` 已完成：单局 Skill 明确了输入、输出、触发/排除边界、工具权限、
预算、步骤和成功标准，Catalog 现在有两个真实用户候选。

`5C-5` 已完成：旧单 Skill 基线原样归档；development v2 以 23/23 冻结规则；
independent holdout v1 随后只运行一次并得到 11/12。唯一失败是设备语义假朋友，
其期望拒绝、实际选中近期复盘，结果已原样保留且不会用于调节本版本规则。

`5C-6` 已完成：ADR-0010 决定 V1 暂缓 LLM Router fallback。单一小型合成 Bad
Case 不足以抵消模型带来的结构化输出、延迟、成本和故障复杂度；现有 GLM Adapter
也只声明 `text_chat`。未来先采用类型化入口和澄清，再以新鲜数据、新 holdout、
结构化输出与质量/成本证据重开模型实验。

`5C-exit-review` 已通过：完整证据、修复项、限制、框架中立边界和面试安全表述见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`。5C 现已完成。

`5D-entry-design` 已完成。采用 ADR-0011：AgentLoop 负责白名单工具调用和草稿准备，
`ReviewHarness` 仍是唯一评测、修订和发布控制面；通过 `DraftPreparationStep` 接缝
同时兼容旧顺序 Retriever/Generator 和新 Agent 路径。完整设计见
`docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`。

`5D-1 Skill Run Boundary Hardening` 已完成：两个 Skill 的关键文本合同、selected
name/version、共享安全 run ID、Harness 规范输入字节摘要和 Catalog-backed 执行前
校验均已有 TDD 证据。该内容绑定尚未创建真实 Harness Artifact，也没有调用模型或
工具。

`5D-2 Context Builder V1` 已完成：`ValidatedSkillExecution` 被投影为 trust-typed
sections，经 Manifest 硬上限做 required-first、optional whole-section 选择，再渲染为
现有 system/user `ChatMessage`。近期与单局使用不同事实 allowlist；初始 citation
逐条作为 data-only section；设计和 TDD 证据见
`docs/plans/2026-08-07-context-builder-v1-design.md` 与对应 implementation plan。

`5D-3 Skill Run Compiler & Budget Enforcement` 已完成：`AgentRunCompiler` 从已验证
Manifest 与 `ContextBundle` 编译现有 `AgentRunRequest`，不接受权限或预算 override；
完整消息 sizer 覆盖 ToolCall/Tool result envelope；AgentLoop 在每次 Provider 调用前
执行累计 Context 门禁，并把 Manifest timeout 作为 Provider/Tool 共用的协作式总
deadline。设计与 TDD 证据见
`docs/plans/2026-08-07-skill-run-compiler-budget-design.md` 与对应 implementation plan。

`5D-4 Evidence-Aware Agent Draft Preparation` 已完成：知识 payload 转换逻辑已从
旧 `LocalRagAdapter` 抽成共享纯函数；`SkillAgentDraftPreparer` 将受限 AgentLoop 的
最终文本降格为 `CoachDraft`，只从实际成功的 `knowledge.search` 执行记录构造
`KnowledgeEvidence`。两个真实 Skill 已用 Fake Provider + 真实本地知识工具走通；
设计和 TDD 证据见 `docs/plans/2026-08-08-skill-agent-draft-preparation-design.md` 与
对应 implementation plan。该检查点没有运行 Harness 或真实 Provider。

`5D-5 Harness Composition & Typed Terminal Output` 已完成：`ReviewHarness` 只依赖
统一 `DraftPreparationStep`，旧路径由顺序 Adapter 兼容；`SkillReviewExecutor` 把
5D-4 的 Agent draft/evidence 交给同一评测、修订、发布/降级/拒绝控制流；最终 Skill
Output 只从 terminal Manifest 与完整性校验通过的 Artifact 构造。两个真实 Skill
已通过 Fake Provider + 真实本地知识工具的完整组合测试。设计和 TDD 证据见
`docs/plans/2026-08-08-skill-harness-composition-design.md` 与对应 implementation plan。

`5D-6a Structured Output Contract` 已完成：`ChatRequest` 可以显式携带冻结的
`StructuredResponseContract`，能力协商会要求 `STRUCTURED_OUTPUT`；严格 Pydantic
Evaluation 模型同时提供 JSON Schema 和本地验证；非法 JSON、额外/缺失字段、错误嵌套
类型、非法枚举、fence 和截断都会被拒绝。最多允许一次携带同一合同的格式修复，第二次
失败返回安全错误；Harness 只会 deterministic fallback 或 rejected，不能发布 Agent
草稿。该检查点当时保持 `ZhipuProvider` text-only；5D-6b 现已补齐离线厂商映射，
但 Fake SDK 证据仍不等于真实 Adapter 或领域 Skill 准入。

`5D-6b Real Provider Capability Gate` 已由 ADR-0012 收尾。P1-P5 与精确 3-call
Adapter 协议切片通过；真实 recent-form 领域切片只尝试一次，在一个计费请求后未形成
统一 `ChatResponse`，没有工具证据或 Evaluation，并安全降级。结论是最小协议能力
准入、领域能力不准入，而不是 GLM 整体成功或整体失败。

当前检查点为 `5D-7 Prompt/Context & Domain E2E Evaluation`。Batch A 已把上述真实
Bad Case 纳入 development，并建立分层合同和 10 案例离线基线；Batch B 又以 ADR-0014
冻结组件级与案例级 Prompt/Context 语义身份，让 Dataset 1.1 和后续候选绑定相同
Skill、Context、知识工具及 Evaluation 合同。离线 admission 会在 Provider 前重建并
精确核对快照，当前外部调用为 0。它只证明实验条件可重复，不证明 Prompt、真实模型、
未知注入或报告质量已经通过。

Batch C 已用 ADR-0015 建立七场 `offline_executable` development 基线。每场都先经过
Batch B admission，再由 Scripted Provider 驱动真实 Skill/Agent/Tool/RAG/Harness；
事实、引用和注入检查从实际运行产物提取。一个 Evaluation 漏判场景真实发布了含 RAG
canary 的报告，并被分层评测标记为 unsafe publication，明确证明 Harness 的确定性发布
决策仍依赖 Evaluation 输入质量。该结果只验证实验接线，不评价真实模型。

Batch D 的 D1-D2 已完成：保留 `coach_evaluation@1.0.0` 历史路径，新增并接入
`coach_evaluation@1.1.0` 安全评测输入/输出、`prompt_injection` blocking issue 与不可
修订的 Harness policy；secure offline executable development 7 场结果为 task outcome
accuracy `1.0`、failure classification accuracy `1.0`、unsafe publication rate `0.0`、
external calls `0`。D3 已在合同、Prompt、snapshot 与规则冻结后创建 3 场独立 held-out，
带 `calibration_excluded=true` 和无污染声明；D3 只完成创建与生命周期测试，没有运行
held-out。上述结果不证明真实模型质量或通用抗注入能力。

D4 已由 ADR-0018 更正并收尾：ADR-0017 的 Flash 选择保留为历史，唯一有界第二
Provider 候选改为 DeepSeek V4 Pro；同任务比较、协议/领域分层准入和成本/停止规则已经
冻结。D5 已离线实现独立 Adapter、安全失败归因、预算 ledger 与 no-I/O preparation；
Fake SDK 和 scripted response 下的协议与失败回归通过，外部调用为 0。Qwen3.8 Max 与
V4 Flash 暂缓，不代表质量较差。ADR-0019 进一步确认 Flash 不进入当前 5D-7，也不占用
5F；未来模型分层最早在 5P 后、默认于阶段 6 由真实产品成本/时延证据触发。

D5 real-gate execution seam 提交 `076a5e3558cd68abb545cebdc2542c973b020768`
已通过 GitHub Actions run `31767405927` 与同 SHA no-I/O preflight；随后只执行一次真实
DeepSeek V4 Pro 协议门。A1 strict structured contract 与 A2 Agent tool round trip
均 passed，总计 3/3 calls、1428 tokens、估算 `$0.00221496`，无 Provider/global stop，
`admitted=true`。脱敏结果 SHA-256 为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
该证据只准入最小 Adapter 协议，不准入领域报告质量或产品默认模型。5D-7 的唯一
后续先完成了冻结三场领域 held-out 的执行接缝设计与离线 TDD；本批没有调用 Provider，
且不得进入 5D exit review 或 5E。协议结果归档提交
`ba1379db6b573d07e6cbe3bd27b9561ea9ca9f6e` 已通过 GitHub Actions run
`31779362817` 的精确 SHA 公开 CI。

领域 held-out 执行接缝现在把控制面和数据面分开：
`prepare_deepseek_domain_heldout_run()` 不接收或构造 Provider，先核对当前 preparation、
冻结 Dataset/Snapshot、执行计划摘要与已准入协议字节摘要；只有 admission 产生且结果
文件已独占预留后，后续入口才可读取 Key/构造 Provider。`ProviderResourceLedger` 可从
旧协议账本继续，新增 protocol/domain scope Token 和单案例 calls/Token 三层边界；领域
协调器逐例生成 ledger-derived 资源、安全语义观测和既有分层 Evaluation，任一 Provider、
案例 mismatch 或 unsafe publication 会停止剩余案例。合成 Fake Provider/Executor 回归
证明第 5 个单例调用在 I/O 前拒绝、首错后剩余 skipped、异常正文不落盘、结果不可覆盖；
真实协议文件仍严格解析为 3 calls，SHA-256 仍为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
执行接缝提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已通过 GitHub Actions
run `31785253957` 的 exact-SHA 公开 CI。后续生产装配批已在零外部调用下把 held-out
修正为 1.1.0 安全成功门，冻结输入计划并接入生产 Executor/CLI；功能提交
`eb198354b3186f25b7d0455d7ed28725bc17e234` 已通过 GitHub Actions run
`31799394506` 的 exact-SHA 公开 CI。用户确认后真实领域门只执行一次；首例返回
`unsupported_parallel_tool_calls` 并由 Adapter fail closed，Harness 降级，后两例
skipped，领域 `admitted=false`。当前结果不可重跑；并行 ToolCall Bad Case 需回到
development 独立处理，仍不得直接进入 5D exit review 或 5E。

ADR-0022 的本地 development TDD 随后移除了 DeepSeek Adapter 对调用数量为 1 的额外
限制，但保留唯一 ID、已声明别名、严格 JSON object、finish reason 和 capability 校验。
AgentLoop 用四类测试固定“整批预算/白名单/重复预检后才顺序执行”的零副作用语义；新的
development 案例又通过 Fake DeepSeek SDK 真实串联本地 RAG、Evidence、Secure
Evaluation 1.1 与 ReviewHarness 并安全发布。完整回归为 `551 passed, 103 subtests
passed`，两套 RAG、compileall、Harness dry-run、安全边界和治理门通过，外部调用为 0。
这些证据只证明执行链兼容性，等待 exact-SHA 公开 CI；不准入真实模型领域质量。

### 2026-08-15：GLM-5.3 模型迁移规划边界

官方 GLM-5.3 文档已确认该模型存在；页面说明 Coding Plan 已开放，普通模型 API 将
逐步上线，并明确 GLM-5.3 始终启用 thinking，不能继续发送当前 Zhipu Adapter 固定的
`thinking.type=disabled`。因此 GLM-5.3 不是只改 `.env` 的透明升级。

本次只记录 ADR-0023 和迁移设计，不读取 Key、不调用 Provider、不修改默认模型，也不
改变 DeepSeek 当前实验。GLM-5.2 的历史结果保持只读；DeepSeek Adapter、DeepSeek
协议/领域结果、预算和 Dataset 1.1.0 保持只读且不可重跑。

GLM-5.3 的未来顺序固定为：当前 5D-7 新鲜领域采用门设计/离线 TDD/公开 CI 完成后，
再做 G53-0 可用性与 endpoint 审计、G53-1 Zhipu thinking profile 离线 TDD、G53-2
公开 CI、G53-3 最多 3-call 协议门、G53-4 新鲜领域采用门。GLM-5.3 通过新鲜领域门前
不替换 GLM-5.2 默认值，不进入自动模型路由，不影响 DeepSeek。
