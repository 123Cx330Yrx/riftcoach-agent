# RQ-244：新报告合同预算与运行时迁移

目标：在 RQ-243 新具名合同的真实本地调用链上复现完整九调用路径，保存不含正文的独立预算证据，并明确产品迁移的版本组合。
方案：复用现有确定性请求测量器、预算账本和开发入口；增加零网络校验脚本及聚焦测试，无新依赖，不改变产品注册。

## 实施计划

1. 新建 `scripts/check_glm53_report_contract_budget.py`，直接调用开发入口 `observe`，显式传入查询指引及报告合同。
   三个匿名 demo 场景分别执行：Agent 初始与三次工具后请求、初评及一次格式修复、一次报告修订、复评及一次格式修复。
   fake Provider 按完整请求估算输入、每次计满 4096 输出，实际经过现有 9 次/205000 预算墙；不能用全零 Usage 证明预算够用。
   保存计划/Context/合同身份、九请求摘要/尺寸、参数、用量账本和预算余量，不保存正文、查询、推理或密钥。
2. 新建 `tests/test_glm53_report_contract_budget.py`：三案完整路径、身份与策略绑定、冻结重建、正文排除、篡改拒绝；
   所有测试断网，相邻回归仅运行报告合同、旧预算、开发入口、版本指纹及实际受影响模块。
3. 新证据保存为 `data/evaluation/contracts/glm53_report_contract_development_budget_v1.json`，与旧正式预算完全隔离。
   校验脚本只打印或核对，不创建 Provider、不读取环境文件、不重考旧真实资产。
4. 核对 Worker、RuntimePolicy/Trace、Skill/Prompt Program、工具重试/回退/lease 的实际接线，完成下方迁移表；
   不在本批注册产品档案、修改默认模型或前端。完成治理、编译、diff 和实现同 SHA 公共验证。

## 证明边界

这证明匿名 demo 下最长控制路径及仓库确定性请求估算预算可达，不是供应商精确计费、延迟或任意玩家/Memory 长度的数学上界。
测量保留旧算法的两倍输入安全系数和前序输出预留；真实响应仍必须由 Usage 账本逐请求结算，超出估算时拒绝。
三案同一 fake 响应只证明控制流，不证明 GLM 质量；RQ-242 经济失败及所有旧领域回执不可变，真实 API=0。
本批按既定 low/4096 同步路线推进；8192 流式恢复、前端、Auth、黄金切片及正式准入不在范围内。

## 迁移版本与学习说明

### 本地结果

| 匿名开发场景 | 九请求合计预留 | 模拟账本实际结算 | 相对 205000 的预留余量 |
| --- | ---: | ---: | ---: |
| 最近状态 | 202346 | 153194 | 2654 |
| 生存调整 | 202310 | 153158 | 2690 |
| 经济调整 | 202250 | 153098 | 2750 |

每案均为九次 fake 调用、36864 输出 tokens，经过实际预算墙，无预算错误；首评 70、修订后 80 是脚本固定值，
最后按 85 分门拒绝，证明“允许修订但不保证发布”。九个实际请求均为输出 4096、请求超时上限 45 秒、
temperature=1.0、top_p=0.95；查询指引与报告合同摘要、执行计划与 Context 均独立绑定。
完整聚焦及相邻验证共 104 项通过（其中新预算测试 12 项）；编译、diff 与治理检查通过。
旧路径和旧预算不修改；实现 `1cd2debf118698fd45e0fe54b2ddc8e2e04445ad` 的
[Actions 34025448118](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/34025448118)
已核对 headSha 且 pytest、postgres-migrations、packaging-smoke 三任务全部成功，不复用 RQ-243 公共结果。

前序输出预留为 49152 tokens，已计入上表“预留”，不能把模拟实际结算数字当成需要的完整上限。
本次仅覆盖固定输入及已执行检索形状；供应商 tokenizer、长推理回放、多工具并列返回、更长资料或玩家/Memory 输入
未被这个样例枚举穷尽。现有 TokenUsage 边界和上下文选择规则继续有效，不能宣传“所有输入都不超预算”。
执行前后的时间参数检查不是等待了最长时间的计时实测；Agent 整段期限仍是 90 秒，初始生成不是四个独立 45 秒总窗口。

### 已核实的当前接线与迁移目标

以下新版本号是本批接受的后续实现目标，不代表已经注册或启用；当前产品文件完全不变。

| 环节 | 当前证据 | 后续同批迁移的目标 |
| --- | --- | --- |
| 模型与运行档案 | `app/model_runtime.py` 精确解析 Flash v1@1.0.0，2048；`app/providers/zhipu_profiles.py` 解析 max/replay。候选 low/replay 在独立表 | 产品目标档案 `glm-5.3-flash-runtime-v2`@2.0.0；4096、enabled/low/clear_thinking=false。先实现显式本地组合，保持默认解析器旧值；不可将候选 execution_allowed 改为 true 冒充产品注册 |
| Skill / Prompt Program | `skills/recent-form-review/manifest.yaml` 0.2.0；`prompt_programs/recent-form-review/manifest.json` 程序 1.0.0；评测 schema 1.1.0 | Skill 0.3.0、程序 2.0.0，旧版本可读；评测 schema 1.1.0 不变。程序指纹必须包括实际报告生成/修订、查询/恢复策略，不只换版本字符串 |
| Context 与知识 | `app/workers/composition.py` 用 MemoryAwareContextBuilder 包普通 ContextBuilderV1，并用 LocalHybridKnowledgeProvider | 保留 Memory 外层的数据隔离；内层可信策略消费查询指引、报告合同与安全附录，知识层消费 coaching-query-recovery-v1。新组合身份 `recent-form-review-flash-v2`@1.0.0，在政策快照和 Trace 中同值绑定 |
| 发布与修订 | `app/runtime/runtime.py` 构造 SkillReviewExecutor 仅传 max_revisions，未传候选来源/guard/回退覆盖项 | 同一产品组合传入最低 1 来源、初稿结构/引用检查、对齐修订提示、最多一次修订、85 分与安全门；关闭确定性报告冒充模型成功。不能把评测执行器直接挂成 Worker |
| 重试和用量 | `app/tools/adapters/llm.py` 产品默认最多 3 attempts；候选为 1。候选预算元数据仍标 hardened-v3-bounded-revision | 新产品预算身份 `coach-bounded-review-v1`，SDK/工具均零额外重试，先复用最多九调用控制流。所有失败调用也计数，评测格式修复占已有名额；不得把诊断默认 205000 直接作为所有玩家总预算 |
| 时间与 Worker 所有权 | Skill 声明 timeout=30；Flash Agent execution=90，工具=90，transport=120；开发观察另压至45。Worker 默认 lease=360、heartbeat=60，至少300 | 区分单请求、Agent 整段与整任务期限，消除开发45与产品90的隐式差异。lease 是续租所有权窗口而非整任务计时器，不应简单相乘后任意放大。离线接线需测试慢请求、心跳与失去所有权后不发布 |
| 历史与兼容 | 旧 RuntimePolicy/Trace 已有运行档案 ID/version；GLM-5.2 兼容/应急仍在 | 新运行记录同时绑定新档案、Skill/程序、查询/报告/预算组合；旧记录继续解码，GLM-5.2 保持显式兼容，既不能静默删掉，也不能将其成功算作 Flash 成功 |

### 唯一后续执行批

本批公共验证已完成，下一项进入“新产品执行组合的离线接线”：把上述参数/策略接到实际 Runtime 执行工厂与请求/Trace 合同，
默认解析器保持旧值，通过 fake Provider 的产品任务→上下文/检索→报告/Evidence/Trace 验证，包含一次修订、拒绝和失去 lease。
把较长玩家数据与 Memory 放入产品预算试验，再据实际请求冻结产品总预算；当前 205000 是已通过的 demo 墙，不是产品普适值。
该批不发真实 Provider 请求、不重考旧领域、不打开生产默认；不是再设计一套首例考卷。
完成离线接线与公共验证后，才做新版本独立真实验收及默认启用的正式裁决，经济旧失败仍保留。

### 八维学习与复现

问题/原理：提示多出一段后，原来已证明的请求大小不再自动有效；必须测量带策略的真实本地链。
设计/实现：沿用确定性尺寸、两倍系数、前序输出预留和逐请求账本，增加版本明确的独立检查器。
代码地图：检查器/冻结 JSON/测试见实施计划；被测入口为 `scripts/probe_glm53_development_retrieval.py`，
候选接线为 `app/evaluation/glm53_guided_candidate.py`，资源墙为 `glm53_bounded_revision_budget.py`。
数据/控制流：开发计划→Context 核验→具名合同→三轮检索→初评/格式修复→报告修订→复评/格式修复→质量拒绝→仅数字/摘要证据。
验证：冻结重建、三场景九请求、满额 Usage 结算、低预算调用前拒绝、旧入口替换拒绝、重算摘要后仍拒绝字段篡改。
运行手册：`python scripts/check_glm53_report_contract_budget.py` 校验冻结证据；`--json` 只打印，不自动覆盖；
`python -m pytest tests/test_glm53_report_contract_budget.py -q` 可断网复现，无 Key、数据库或服务器。
失败/边界：证据不含正文；临时运行目录自动删除。估算或身份漂移必须重新审查，不能降低门槛使旧数字通过。
面试表述：“用同一候选链证明三类匿名输入的一次修订预算可达，并发现产品组合迁移缺口”；不能说“所有用户低延迟、经济真实成功或生产已准入”。
所有者理解：本材料已提供，但没有新增用户理解确认；参考来源审计、生产/作品集成熟度不因本地预算结果提升。
8E 仍在进行；production_media=0。
