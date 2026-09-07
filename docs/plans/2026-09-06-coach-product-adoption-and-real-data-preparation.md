# RQ-251：Coach 产品采用与真实数据衔接计划

**目标：** 将已通过的显式组合接入可验证的产品应用链，明确真实比赛黄金切片所需证据；本批交付接入设计，不启用生产默认。

**架构：** 复用 RecentReviewApplicationService、现有 Runtime、Memory 和 EvidenceBundle，不复制评测循环或新增框架。先用注入式离线产品组合证明接线，再在既有真实调用门内准备真实数据观察。

**技术：** Python、现有 typed contracts / pytest；沿用 PostgreSQL Worker 和 React Evidence 展示，当前无新依赖。

## 1. 已核实事实与采用边界

- RQ-250 的组合 1.2.0 / Skill 0.4.0 / 程序 2.2.0 已在已知两局合成 demo 上通过四案真实开发。它证明开发路径，不证明真实玩家覆盖或默认产品已迁移。
- `app/workers/composition.py:load_worker_composition_settings` 仍调用旧 `resolve_model_runtime_profile`；构造时使用普通 `build_runtime`、ContextBuilderV1 和默认编译器。不能只设置同一个模型名就宣称选中了新组合。
- `app/runtime/composition.py:build_offline_coach_runtime` 与 `app/product/recent_review.py:RecentReviewRuntimeRequestCompiler` 已支持显式合同；因此下一批需要的是应用装配与回归，不是再造 Runtime。
- `app/product/recent_review_service.py` 已统一 review / review_by_puuid：取摘要→编译→Runtime→报告投影及回执。Worker 通过 `app/tasks/recent_review_executor.py` 使用该服务，保留失去 lease 后不得提交用户可见终态的规则。
- `app/workers/composition.py` 已构造 RoutedRiotPlayerSummaryBuilder 和 DataDragonService；当前该装配没有接入 OP.GG Meta。`app/meta/context.py`、`app/evidence/fusion.py`、`app/evidence/service.py` 与 `web/src/components/EvidenceDrawer.tsx` 是可复用接缝，而非证明整条真实链已连通。
- 记忆开发案的 `memory_preference_acknowledged` 仅正则匹配训练段的“15 分钟”，不是整份训练计划时长求和或语义遵守证明。历史回执不回填，后续产品审查必须区分两者。

## 2. 接入决定

沿用 ADR-0098 的显式未准入接缝。下一批新建 `app/product/coach_composition.py`，提供仅接收已构造依赖的应用装配函数：summary_builder、provider、knowledge_provider、runs_root、memory_context_builder（可选）。本函数不读环境、不创建网络客户端、不启动 Worker。

装配固定使用 `BATCH_COACH_CONTRACT`、`examples/runtime_profiles/flash_v2_batch/skills` 和对应 `prompt_programs`；由现有目录解析器及合同校验验证版本，不能接受任意路径冒充此组合。使用 CoachContextBuilder 作为可信内层，MemoryAwareContextBuilder 只在明确提供隔离依赖时包裹它；可选项优先采用显式 Memory repository / manifest store 依赖，不能让任意外层 builder 丢掉可信内层。编译器、Runtime 和 Trace 必须绑定同一合同摘要；runtime_profile 不伪造已注册身份。

返回现有 RecentReviewApplicationService，保留 receipt writer / report renderer 的现有语义。生产 Worker、默认解析器、GLM-5.2、前端不在下一批修改范围；后续正式采用时再将已经验证的装配接入显式产品入口。

资源沿用合同 1.2.0：high、8192 输出、单请求60秒、Agent120秒、模型调用计时480秒、9模型调用/8本地工具/649728 tokens；保持85分、事实/引用/注入门与原修订额度。480秒不声称是所有非模型步骤的任务总期限；360秒 lease 是可续租所有权窗口，不与任务耗时简单等同。

## 3. 唯一下一执行批：离线产品应用组合

**文件：** 新建 `app/product/coach_composition.py`、`tests/test_coach_application_composition.py`；复用而不重写 `app/runtime/composition.py`、`app/product/recent_review_service.py`、`app/tasks/recent_review_executor.py`。只有实际测试揭示接缝缺陷才窄改已有模块。

1. 先写装配测试：入口仅接受依赖，不读取 Key / 环境或发网络；默认 Worker 配置不受影响；旧组合与旧记录仍可读。
2. 实现上述薄装配，测试 Provider 档案、Skill/程序、编译 policy 与 Trace 摘要一致；错误档案在首次 Provider 调用前拒绝。
3. 注入 Riot-compatible summary builder 和 fake Provider，使用真实应用服务完成 review / review_by_puuid→编译→检索→报告→评测→回执；覆盖请求五局仅两局、完整五局、无有效局、版本混合、长输入。
4. Memory 测试覆盖有记忆/省略/跨 owner 隔离；训练偏好测试同时放入“提及15分钟但安排明显超过15分钟”的反例，不能用旧正则当完整符合判定。先明确观察/人工审查语义，不偷加未经验证的模型评分。
5. 经 RecentReviewTaskExecutor 验证成功、质量拒绝、一次修订与失去 lease。检查返回结果、磁盘回执和终态引用一致；失权可留内部诊断，不可提交用户可见成功。
6. 聚焦测试通过后运行相邻回归、治理及 diff 检查；不重跑开发四案或旧正式资产。公共证据仍需对应新实现 SHA，旧 RQ-250 CI 只证明旧实现。

预期命令（下一批新文件存在后）：

```text
python -m pytest tests/test_coach_application_composition.py tests/test_offline_coach_runtime.py tests/test_recent_review_application_service.py tests/test_recent_review_product_compiler.py tests/test_worker_composition.py -q
python scripts/check_project_governance.py
git diff --check
```

预期：离线测试全部通过、无外部请求、治理成功、diff 无空白错误。实际测试数在执行后记录，不预填。

## 4. 真实数据黄金切片衔接（后续范围，不是本批已执行）

一条代表性产品请求应沿以下已有链路走通，不以更多合成考卷替代：

`玩家请求 → Riot比赛/摘要 + DataDragon版本 → 来源融合 + Memory → 同一产品Runtime → 教练报告/训练计划 → 回执/任务终态 → Evidence展示`

| 输入/产物 | 必须保留的判断 | 对应接缝与完成证据 |
| --- | --- | --- |
| Riot 比赛 | 玩家/地区/队列与过滤后实际局数；无比赛不造事实 | `app/lol/player_summary.py`、`app/lol/riot_client.py`；真实摘要与报告事实对照 |
| Data Dragon / 官方 patch | 静态版本与官方变动分开；不能把名称映射当版本变动事实 | `app/lol/data_dragon.py`、`app/evidence/fusion.py`；版本匹配/缺失/冲突的可见投影 |
| OP.GG | 当前快照与历史归因分开；partial 来源不补造 upstream patch/time | `app/meta/opgg.py`、`app/meta/models.py`；过期/缺失按既有融合规则降级 |
| OP.GG 后续宽度 | 英雄分析、对线数据仍需逐项映射；协同数据仅在有真实消费者时加入 | 不能将现有 lane-meta adapter 写成全部工具已支持 |
| Memory / 训练计划 | 真实隔离与用户偏好落实；总时长检查不同于关键词出现 | `app/agent/memory_context.py`、应用装配；检查计划具体训练动作与时间预算 |
| 报告与 Evidence | 来源、缺口、冲突、质量结论一致，不能 UI 显示完整而后端已降级 | `app/evidence/service.py`、`app/evidence/storage.py`、`web/src/components/EvidenceDrawer.tsx`；后续浏览器核对与接口对照 |

真实运行前需要明确玩家/地区或已有合法导出、可用来源及单次调用预算，届时先检查上下文已有信息，不重复索要。当前没有读取密钥或抓取数据。新增/变化的 OP.GG 工具和官方 patch 接口届时需核对真实接口，不按本文猜测网络合同。

数据衔接完成后再做独立采用裁决：输入身份、组合指纹、实际调用用量、报告及来源一致性、训练偏好落实和产品终态均需要新证据。这里的“独立”指不把开发调参结果当采用结论，不自动创建另一套 held-out、重考旧案或改变默认。默认注册、部署/Auth与8F保持原门和原顺序。

## 5. 本批交付与八维学习

- 问题/原理：模型在开发入口成功，不等于产品后台选择了同一版本；装配身份必须贯穿输入到终态。
- 设计/实现：选择现有应用服务的薄装配；本批仅完成设计，代码尚未新增。
- 代码地图：第1至4节给出已经核对的实际文件与待建文件。
- 数据/控制流：第3节应用链与第4节真实数据链；生产 Worker 默认不变。
- 验证：本批只做仓库接线核对、治理和差异检查；不重复已通过的开发测试，不把计划中的测试计为通过。
- 运行手册：第3节是下一批可执行步骤；第4节是真实衔接证据清单，不是调用授权。
- 失败/边界：版本混用、事实缺失、Meta过期、时长偏好假阳性、失去所有权分别验证，不以静默回退掩盖。
- 面试表述：已定位“显式开发组合到产品装配”的差异并形成接入计划；不能说真实黄金切片或生产默认已上线。

四线状态：本地代码保持 RQ-250，新增可执行接入设计；学习材料已提供但所有者理解未新增确认；参考来源未新增在线审计；公共实现证据保持 RQ-250、无新部署证据。Stage8/8E仍in_progress，production_media=0。

## 6. RQ-252：离线应用组合实现（2026-09-06）

状态：本地与公共验证均完成；下一步为第4节真实数据切片接入准备。上方第1至5节保留RQ-251设计时态，其中第3节离线批已完成；真实数据衔接仍未执行。

公共证据：实现 `afda1934f699c5de5110ccbef67533b84e62d8e9` 的 [Actions 34076953653](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/34076953653) 已核对精确headSha，三个任务全部success；后端2735 passed、145 skipped、127 subtests passed，数据库201 passed，前端单元270 passed、端到端38 passed，打包与检索/代码边界门通过。下方未提交/推送记录为历史，本条取代其待办；后续纯文档收口提交不能冒充此已核验实现SHA。真实API=0，无部署或默认启用。

### 实际实现与代码地图

新增 `app/product/coach_composition.py:build_coach_application`，直接返回既有 RecentReviewApplicationService。固定仓库内 `flash_v2_batch` 资产及 BATCH_COACH_CONTRACT，复用目录/指纹核验、Coach Runtime、请求编译和 FileRunReceiptStore。没有修改旧 Runtime、服务、Worker、默认注册、前端或任何版本化资产。

将设计中的可选任意 builder 收紧为 `memory_repository` / `memory_manifest_store` 成对依赖，由装配自己构造 MemoryAwareContextBuilder，确保它始终包住绑定1.2.0合同的 CoachContextBuilder。只给一项时构造失败；不配置Memory却传binding时沿既有Runtime边界失败，不静默丢弃。入口不读环境或Key、不创建外部客户端、不启动Worker，构造时不创建runs目录；真正调用发生在显式 review/review_by_puuid 之后的注入依赖中。

该入口目前依赖完整仓库的固定资产路径，不宣称单独安装wheel即可使用或已经具备生产启动选项。SDK/Provider、Riot-compatible summary builder、知识库均由调用方提供，未新增网络便捷入口。

### 数据流与证明

产品请求→摘要builder→现有验证/确定性报告→绑定新合同的编译器→Memory包装的可信Context→实际Runtime检索/生成/评测/一次修订→报告及Trace→不可变API回执→实际TaskExecutor核验证据→Worker所有权检查→终态与可选对话消息。

新增 `tests/test_coach_application_composition.py` 的34项断网测试覆盖：

- 装配不发调用、不建外部依赖或runs目录；模型/重试/档案错误、旧资产替换和Memory半配置在运行前拒绝。
- `review` 与 `review_by_puuid` 均进入真实服务、Runtime、RAG与回执；合同1.2.0、Skill0.4.0、程序2.2.0和8工具上限在Trace中一致，不伪造已注册runtime_profile。
- 请求5局仅返回2局、完整5局、混合版本在Context保留各自边界；空局/全部排除/聚合数不一致在模型前拒绝；长必需输入留下安全失败回执且模型调用为0。模拟摘要不证明真实Riot抓取或混合版本的模型判断质量。
- Memory内容只进data-only用户区，可信政策保留；长记录整条省略并落盘清单；无binding不查Memory；owner/run/conversation/player绑定漂移均在模型前拒绝。没有声称仅凭此测试替代数据库层的owner隔离验证。
- schema1与schema2任务各覆盖发布、质量拒绝、失去所有权；实际Executor核验报告/Trace/回执，同意提交后才写终态对话消息。Worker的执行成功不等于质量发布成功：拒绝任务正常终止但 `report_available=false`；失权不得提交终态或消息，内部诊断产物可保留。

报告文件以SHA-256验证实际字节；与应用输出比较时仅忽略既有的文件末尾换行，未放宽内容或摘要一致性。

### 训练偏好的反例与边界

两份脚本报告都写“每天最多15分钟”，随后分别安排5+5+5分钟和10+10+10分钟；模拟评测器均可给通过。测试按明确动作逐项求和，确认后者实际30分钟，而旧关键词确认仍为真。产品输出没有新增“训练预算符合”字段，不把关键词出现或fake评测当作完整语义验证。

因此本批证明Memory可传递与隔离，不声称训练计划已自动遵守所有偏好。真实采用时需对具体动作/时长做内容审查；若要新增结构化时长约束，应独立版本化设计，而非在本装配批偷偷改变既有报告/评分合同。

### 验证、运行手册与八维收口

2026-09-07恢复记录：额度中断时代码和178项相邻测试已完成，仅文档指针未同步。恢复后针对最后的类型标注/成对依赖整理复核34项，全部通过；编译、治理及diff检查通过。没有重复178项完整相邻批或开发四案；本地变更未提交/推送，下一步仍是本实现同SHA公共CI。

先获得新模块不存在的预期红灯，再实现薄装配；最初正文比较仅因末尾换行失败，核实发布格式后修正测试。新增34项通过；连同旧离线组合、应用服务、编译器、Worker装配、任务证据核验、可靠Worker及Memory边界的相邻回归，共178项通过。本批没有真实Riot/模型/OP.GG请求，也未重复开发四案或旧正式考卷；未提交/推送，不能借用RQ-250公共CI证明新代码。

复现（项目Python环境）：

```text
python -m pytest tests/test_coach_application_composition.py tests/test_offline_coach_runtime.py tests/test_recent_review_application_service.py tests/test_recent_review_product_compiler.py tests/test_worker_composition.py tests/test_task_reconciliation.py tests/test_reliable_review_worker.py tests/test_memory_aware_context_builder.py -q
python -m compileall -q app/product/coach_composition.py tests/test_coach_application_composition.py
python scripts/check_project_governance.py
git diff --check
```

八维对应：问题/原理是产品装配身份一致性；设计/实现和代码地图见本节前两段；数据/控制流、验证、运行手册及失败/边界见本节；面试可说“通过显式依赖装配把新Coach组合接入既有产品服务，并用断网整链测试验证Memory隔离与终态所有权”，不能说“真实黄金切片、训练偏好语义验证或生产默认已上线”。所有者理解未新增确认，参考来源无新增在线审计，公共/部署证据没有提升；Stage8/8E仍in_progress，production_media=0。
