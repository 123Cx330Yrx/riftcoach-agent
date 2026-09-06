# RQ-239：带查询指引的新候选领域资产设计计划

当前后续（2026-09-06）：RQ-243 已完成 [生成/修订合同对齐](2026-09-06-candidate-generation-revision-contract-alignment.md) 的 144 项回归及 `57c73e5` / CI `34023099294` 三任务验证。下一步完整预算证明与产品迁移版本对齐；本文下方“待对齐”顺序为历史，旧真实失败不改写。

## 目标

为 GLM-5.3 Flash 建立与 RQ-237 隔离的新鲜领域验证资产，验证候选 Context 是否能稳定携带
`coaching-query-guidance-v1`，并保留现有来源、安全、事实和 85 分质量门。

## 执行批次

1. 设计新的四案例 Dataset、输入计划、Context 快照、协议、marker、预算和回执身份；重建新匿名 fixture，
   做旧 RQ-227/230/235/237 的 case/run/utterance/marker/fixture 排重。
2. 实现 no-I/O 资产准入，检查快照中确实包含指引摘要、输入计划逐案承诺与候选策略；运行最坏路径预算证明。
3. 加入聚焦测试和公共 CI；同 SHA 获取新鲜 G53-3-L 后，才执行一次真实领域观察。

历史进度：V4 资产已完成，实际领域运行绑定 `b71dfa1`（公共 CI `34014412211` 全绿）。
该 SHA 的协议回执记录 3 次真实调用、`admitted=true`、1096 tokens、11750ms，回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_guided_g53_3l_rq239_v1.json`。
领域回执实际记录四案全部执行，各 3 次调用，分别取得 3/3/1/3 个来源，均以 `evaluation_failed` 拒绝且无评分。
旧文档“后三案跳过”错误；实现没有在逐案质量失败后停止，与 ADR 的首错停止约束不符，任何后续正式领域版本须修正。
旧回执和已消费资产保持不变，不能从这些记录断言空正文、超时或模型质量是根因。

## RQ-241：诊断闭环与下一步

已确认的接线缺口是 `ToolRuntime → ToolResult → _require_success` 把错误变为普通 RuntimeError，
导致 Harness 无法保留具体类别。适配器现在抛出既有 ToolError；Harness 只保存固定安全码，
Manifest 的可选 `failure_code` 没有值时省略，语义观察和开发回执可读取该码。终态/重试/85 分门不变。
移除此前无证据支持、且不能越过 ChatResponse 不变量的空正文放宽。未知错误文本和不合规 code 不公开。

验证覆盖真正的工具—适配器—Harness—落盘—开发回执链路：超时、无效 Provider 响应、
工具输出校验失败、两次 JSON 校验仍失败；失败没有最终报告，格式修复仍最多一次。
相邻成功、一次报告修订、持久化和历史公共回执回归同跑；这证明工程诊断，不证明真实模型质量。

当前决策：先用已存在的匿名开发探针验证 `survival_adjustment`，不再创建或消费一套新考卷。
在本次代码通过公共 CI 后最多执行一次；沿用已批准普通智谱 API、候选 low/4096、
每案 9 次/205000 token 墙、开发请求 45 秒与一次修订，不自动重试失败的整轮。
结果写入新的 development 文件；无论通过或拒绝都保留，临时正文随探针退出删除，
不冒充 G53-3-L、独立领域准入或生产准入。若再失败，依安全码做针对性修复；
若成功，下一批再推进代表场景稳定性和正式运行时接入条件。

### 实际结果与明确下一步

实现 `88682fc` / CI `34021213331` 三项全绿；用户明确授权后 survival_adjustment 一次真实开发验证通过：
3 次调用、11116 tokens、41016ms、2 来源、首评 96 分、零修订、published。
新开发回执 `glm53_survival_diagnostic_rq241_01.json` 保留原始生成内容，类型/资源/body-free 校验通过。
来源为 `01_metric_interpretation.md` 与 `03_training_plan.md`；不把开发评分等同于盲评准入或线上可靠性。

接下来只补已有 economy_adjustment 一次开发场景（沿用上方边界、独立新文件、失败不自动重跑），
随后汇总代表场景结果及候选低思考档正式接入 RuntimePolicy / Trace / Skill 版本合同的缺口。
旧 V4 具体失败仍未知，不再为已经消费的旧考卷回填新分数；其逐案首错停止和匿名 fixture 一致性
问题须在任何后续正式领域版本中单独修正。普通产品默认模型与前端本批均不变。

## 验收

### RQ-242：经济观察后的修订诊断补全（2026-09-06）

经济开发观察在 `7c931f6` / CI `34021621810` 三项全绿后仅执行一次：4 调用、13892 tokens、
37548ms、3 来源，终态 rejected/revision_failed、revision_count=1，最终评分不可用。
真实正文已按既定规则清除，不能恢复具体修订错误或首次评测分数；不得回填原回执。

离线复核确认：修订开始就增加 attempt_id；修订失败时只有第 0 次评测，现有完整评测投影因缺第 1 次
而清空全部诊断。标题/篇幅/引用校验又是普通 ValueError，未进入固定安全码。
本批先用 fake Provider 复现，再补固定校验码及仅开发回执 1.1 的独立 evaluation_history；
历史正式回执、最终评分语义、发布门、一次修订、请求上限均不变。只保留经过文件完整性/严格类型验证的
连续评测摘要（分数、类别和计数），不把中间评分当最终评分，不保存正文或异常文本。
测试覆盖三种修订拒绝、未知错误不泄漏、历史评测文件损坏、修订成功及第二次评测失败。
随后收口到本地/公共验证和产品接入差异清单；本批不再调用真实 Provider。

本地验证：三种修订失败的完整链路测试先失败后通过；聚焦 35 项/4 subtests、相邻 82 项/12 subtests。
经济回执 `data/evaluation/results/development/glm53_economy_diagnostic_rq241_01.json` 为 2673 bytes，
SHA-256 `f9f61100d104015a4cb18be03d1862c36678f531bf0e9fa8445df61dea95dc0b`；严格类型、资源、身份、body-free 校验通过。
新诊断尚未经新的真实模型调用，不能据此把经济场景改写成已修好。实现
`a64331b25dcc4612b83bbe13d12b1b9f1f2ebf11` / Actions `34022245397` 三任务 exact-SHA 成功，
关闭本批公共验证；下一精确项是候选生成/修订合同对齐的离线设计与回归。

### 已核验的产品接入差异与后续顺序

| 环节 | 仓库当前实现 | 后续需交付的结果 |
| --- | --- | --- |
| Provider / 模型档案 | `app/model_runtime.py` 解析到 Flash v1、2048；`app/providers/zhipu_profiles.py` 普通解析器返回 max，low 是显式候选。`glm53_flash_candidate_profile.py` 的 4096 策略只允许评测作用域 | 为选定的 low/4096 建立独立版本的可信产品绑定，不改写旧 v1 证据，不靠改模型字符串或偷开候选标志接入 |
| 生成与修订 | Skill 要求可归因 Markdown；`validate_revised_report` 固定八个标题及最低长度比例，`build_revision_prompt` 只要求保留原标题。当前真实失败具体是哪项仍未知 | 先在候选作用域统一生成/修订的明确报告结构，测试标题、过度删减、未知引用及事实修正；只修复合同不一致，不放宽事实/来源/85 分门 |
| Context / 检索 / 来源 | 候选执行器带安全附录、查询指引、CoachingQueryKnowledgeProvider、至少 1 来源与 draft guard。Worker 仍组合普通 ContextBuilderV1 / LocalHybridKnowledgeProvider；产品 Runtime 创建 SkillReviewExecutor 时未传这些覆盖项 | 把可信教练策略作为有版本的服务端组合能力接入，并保持真实来源映射、拒绝条件及 Memory 上下文边界；不能直接把评测执行器当 Worker |
| 预算与回退 | 候选 SDK/工具单次、无确定性回退；产品 `llm.chat` 仍有最多 3 attempts，Skill 允许确定性回退，质量 timeout=30、执行窗=90；Worker 有 lease/heartbeat 规则 | 对齐 Agent、评测/修订、工具重试、总预算和 Worker lease；明确失败结果，不把回退文本当作 Flash 成功，不自动删除 GLM-5.2 兼容路径 |
| 运行记录 / Skill 版本 | RuntimePolicySnapshot、RuntimeIdentitySnapshot 已绑定 profile id/version；recent-form Skill 0.2.0、Prompt Program 1.0.0，现有指纹锁定旧组件 | 新策略身份同时进入 RuntimePolicy / Trace / Skill / Prompt Program，旧记录保持可读；离线证明 Worker→任务→报告/Evidence/Trace 使用同一组合 |
| 正式领域与产品验收 | 三个开发场景并非全绿，且不同 SHA：recent_review guided_03 为 95 分/3 来源，survival 为 96 分/2 来源，本次 economy 修订拒绝/3 来源。V4 旧 fixture 的 5 局/3 胜与报告 4 局/2 胜矛盾，逐案循环也未按案例失败停止 | 新正式版本先离线验证 fixture 事实一致性、首错停止及预算，再绑定新协议与独立案例；旧失败不覆盖。黄金切片与实际任务端到端后置，不能由开发分数替代 |

明确下一批：先完成候选生成/修订合同对齐的离线设计及回归，同时冻结产品迁移的版本/预算清单。
不重复证明能连接 API，不循环重跑首例，不直接切默认；具体新合同先落地到可检查的候选路径，
再做独立正式观察与 Worker 接线。流式 8192/recovery 实验不是同步 low/4096 产品接入的前置任务。
Auth/RSO、安全/部署/合规、OP.GG breadth、完整黄金切片、研究素材权利与 8F 仍属后续，
本批不修改 Portal、Account、Workbench 或 `production_media=0`。

### 学习与复现

数据流：真实模型→检索→初稿→评测→最多一次修订→重新评测→质量门。修订失败时不会产生重评，
因此“已尝试一次修订”不等于“有两次评测”；开发历史与最终评分必须分开。
代码地图：`app/report_validation.py` 固定校验码；`app/harness/runtime.py` 写安全失败类别；
`app/evaluation/provider_domain_production.py` 验证评测文件完整性并投影；开发探针写 1.1 独立历史。
复现：运行 `python -m pytest tests/test_glm53_development_retrieval_probe.py tests/test_coach_report_evaluation.py -q`，
使用 fake Provider、真实本地检索和持久化，无网络。新观察保留新文件、不得覆盖旧回执；正文仍只在临时目录。
准确表述：已打通多个真实开发场景，经济场景仍失败；本次修复可观测性，不宣称修复真实生成质量或生产准入。

资产身份、预算、Context 和协议全部可重建；候选入口在漂移/旧资产/指引身份不一致时于 Provider 调用前拒绝；
旧资产测试保持通过。真实领域回执只保存枚举、计数、SHA 和终态，不保存问题正文、答案、reasoning、工具参数或凭据。

## 非目标

不把 RQ-238 单样本结果升级成正式准入，不改默认模型或产品 Runtime，不修改前端，不重跑任何已消费考卷，
不新增模型依赖或放宽现有质量门。
