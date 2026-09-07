# 真实数据切片接入准备（RQ-253）

**Goal:** 将RQ-251第4节收敛为可执行的摘要与多来源Evidence离线接入批次。

**Architecture:** 复用现有Summary、8D纯融合和Evidence快照合同，不引入第二套Runtime。先补纯转换，后续再将同一份摘要接给RQ-252应用组合与证据持久化；报告检索引用不能替代多来源快照。

**Tech Stack:** Python、现有dataclass/Pydantic合同、pytest；后续持久化复用SQLAlchemy/PostgreSQL。

最新状态：RQ-254已完成第3节离线实现及本地验证，见第6节；唯一下一步为本实现同SHA公共CI。以下第1至5节保留RQ-253准备时态；真实抓取、数据库写入、生产Worker切换和新正式考卷均未执行。

## 1. 问题、原理与核实结果

报告回答“如何训练”，Evidence回答“根据哪批数据、哪些来源、哪些限制”。两者必须来自同一份已获取数据，且保留各自合同：RAG引用/Trace/终态回执与EvidenceBundle不是同一种证据。

| 已检查入口 | 事实与缺口 | 接入要求 |
| --- | --- | --- |
| `app/lol/player_summary.py` | 已能由Riot ID或可信PUUID构建摘要；指定queue无记录时再查queue=None；detail失败留failed_matches，timeline失败留unavailable | 保存requested/effective queue及fallback，禁止冒充原队列样本；不得补造缺失比赛或时间线 |
| `app/lol/match_analyzer.py`、`app/evidence/adapters.py` | analyzer保留原始gameVersion；adapter仅接受2/3段且每段至多3位 | 本地历史版本`16.16.804.9184`调用`_patch_version`实际报`riot_patch_invalid`；需窄修复，不删除原始版本 |
| `app/lol/data_dragon.py` | 构造即创建缓存并读取/获取版本清单及4份目录；缓存存在就直接使用，没有自动过期刷新 | 不能把构造当无I/O预检，不能把缓存读取时刻当上游获取时刻；固定实际版本、language和目录摘要；静态映射不等于官方补丁解读 |
| `app/product/coach_composition.py` | 显式1.2.0应用组合、报告与回执已打通 | 没有自动构建/append多来源快照；本批不声称Evidence展示已贯通 |
| `app/evidence/service.py`、`app/persistence/evidence_snapshot_repository.py` | API读取快照；append核对owner/task/run、RUNNING或SUCCEEDED状态、时间及refresh幂等 | 没有lease token参数，不可声称天然具有Worker失权围栏；实际写入接线须另验发布顺序与失权 |

来源盘点：`data/evaluation/results/riot_external_validation_2026-08-23-v2.json`已有asia路由的公开玩家样本身份及上述四段版本，且明确account_control_not_verified、timeline_not_requested。此前只做account→IDs→一局detail，body-free回执不是完整Summary，不能反推时间线或玩家授权绑定。`scripts/run_riot_opgg_fusion_validation.py`用这类回执投影单局且不含DataDragon/官方补丁，运行会实际访问OP.GG；本次不运行。已盘点的demo/领域/预算摘要是合成输入，未确认可直接复用的完整真实摘要。实际执行前先检查合法本地导出和现有目标；若没有完整输入，仅询问缺失的目标/路由或导出，不重复索要密钥。

## 2. 数据与控制流

未来完整链：可信玩家请求→有界获取一次Summary和真实来源身份→冻结Summary摘要→同一份Summary分别进入Coach应用与纯Evidence桥→报告/Trace/回执及EvidenceBundle→带owner/task/run的快照写入→既有Evidence API/页面投影。

Memory仍走既有可信绑定，不能从Riot ID或PUUID前缀推断账号所有权。真实报告需检查具体训练动作与时长，沿用RQ-252关于“15分钟关键词不等于时长合规”的限制。

## 3. 唯一下一批：Summary→Evidence纯桥接

范围仅以下三项；不新建网络客户端、命令行真实执行器或数据库写入钩子。

### Task 1：修复真实版本格式

- 修改：`app/evidence/adapters.py`。
- 测试：`tests/test_evidence_fusion_vertical.py`。
- 先加入保留真实格式`16.16.804.9184`的失败用例，再让2/3/4段纯数字版本归一为前两段；限制整体长度、首两段范围和构建段长度，不接受尾缀、URL、注入文本、空段、布尔或超长值。保留旧None语义与旧有效版本行为。
- 不改原始Summary的game_version，不用历史脚本无条件split冒充严格校验。

### Task 2：同源摘要桥

- 新增：`app/evidence/summary_bridge.py`、`tests/test_evidence_summary_bridge.py`。
- 复用：`app/lol/summary_schema.py`、`app/evidence/adapters.py`、`app/evidence/fusion.py`。
- 输入为已物化Summary、显式routing_region、显式观测时刻/来源身份、可选已类型化DataDragon/官方补丁/MetaEvidence和显式now；不得自行取环境变量、时钟、文件或网络。
- 输出包含原Summary规范化内容摘要、转换纳入/排除计数、现有EvidenceBundle；包裹对象保持不可变，不伪称已经持久化。摘要标明是Summary投影摘要，不冒充上游原始响应hash。
- 显式验证Summary容器、局数一致性、重复match_id、region、时间；只将included_in_aggregate=True的有效行用于教练统计对应的融合，保留排除/失败计数，不静默吞掉损坏的有效行。没有有效行时明确拒绝，不生成假成功包。
- 原始比赛版本与每局queue保留在输入；融合按各局实际版本，不拿最新版覆盖全部比赛。显式DataDragon身份必须与Summary request版本/language相符；缺身份时保留缺口，不凭版本字符串捏造catalog_digest/retrieved_at。
- Summary的generated_at_utc最多是摘要生成观测时刻，不是比赛时刻或上游生成时间；注入观测时间需注明语义。OP.GG partial/过期及官方补丁缺失由现有融合规则表达，不添造历史归因或新评分规则。
- 不把SummaryValidationError中的玩家/比赛原值写进公开错误；对外仅稳定安全码。转换不修改调用方输入。

### Task 3：离线验收与应用接缝证明

- 覆盖2/5局、请求5实际2、混合版本、四段构建号、无有效局、短局排除、detail失败、timeline缺失、queue fallback、重复ID、时间缺失、来源身份不匹配、partial/expired/conflicting Meta和输入不变性。
- 加入禁止网络/文件读写的测试，证明导入与转换均零I/O。用合成完整Summary验证规范化摘要稳定且事实改变时摘要改变，不保存真实玩家正文为fixture。
- 复用RQ-252测试模式，确认桥所消费Summary与应用builder返回的同一内容相符；只证明可组合，不假装数据库/页面已收到快照。若需要整链测试，修改`tests/test_coach_application_composition.py`，不得通过改变生产默认完成测试。
- 先跑新增失败用例确认实际坏例，再运行：

```text
python -m pytest tests/test_evidence_summary_bridge.py tests/test_evidence_fusion_vertical.py tests/test_evidence_fusion_contracts.py tests/test_coach_application_composition.py -q
python -m compileall -q app/evidence/adapters.py app/evidence/summary_bridge.py
python scripts/check_project_governance.py
git diff --check
```

预期全部通过；实现后记录实际数量，不预填通过结果。不为本次纯文档改动重复RQ-252的178项或公共全套。

## 4. 后续接线和真实运行边界（本批及下一批不执行）

- 获取预算：现有RiotClient每方法一个请求、无内建重试、默认15秒。5局且服务端返回不超count时，Riot ID路径最多1账号+2次IDs（含空队列fallback）+5detail+5timeline=13次；可信PUUID路径最多12次。现有builder遍历上游全部IDs，并非本地硬上限，因此未来有界入口必须在detail前检查数量、重复并做全局调用计数，不能直接把13当已实施保证。短局当前仍取timeline。
- DataDragon全冷缓存最多5次请求，每次20秒；缓存命中可减少，但不证明新鲜。未来入口需冻结目录身份/实际获取时间，未知则显式降级；不要偷偷全局刷新缓存。
- 现有OP.GG脚本含initialize、discover、一次lane-meta工具及close；一次业务工具调用不等于一次HTTP。未来执行需分别计数握手/发现/工具请求并设置总预算，禁止展开champion analysis/matchup等未接消费者的广度。
- Provider沿用1.2.0、high/8192/60秒、最多9调用/649728 tokens；本地工具最多8，不含外部数据获取预算。真实输入必须先过输入预算，不能为了塞下数据静默删事实。协议/同SHA证据按执行时已有规则复核，不以本计划替代。
- 需要后续实现默认零I/O预检和显式执行入口；先冻结player/routing/queue/count/来源/预算/不可覆盖run身份，再创建网络依赖。失败、中断记录已用调用数，不自动追加新批。
- 持久化复用`PendingEvidenceBundleSnapshot`和既有repository/API；独立验证owner/task/run、重放冲突、失权与快照失败时终态顺序。不要在纯bridge里append，不能把RUNNING检查等同lease围栏。
- 私有Summary/报告与公开body-free回执分开；公开只保留必要版本、计数、安全码、摘要和预算，不扩散raw PUUID、错误正文、提示词或Memory。旧公开样本不证明该玩家属于当前用户。

## 5. 本批验证与八维学习收口

- 问题/原理：同源数据与来源真实性，不把两种Evidence混同，见第1节。
- 设计/实现：本批为已完成设计，桥尚未实现；取最小复用方案，见第3节。
- 代码地图：第1、3、4节的实际文件与拟新增文件严格区分。
- 数据/控制流：见第2节，外部获取、纯转换与持久化各守边界。
- 验证：只读代码和本地历史回执；已离线复现真实版本抛`riot_patch_invalid`，未修复；治理及diff检查通过后方可收口。
- 运行手册：第3节精确命令仅用于下一实现批；本次只运行治理/diff，无真实调用、未重跑开发四案。
- 失败/安全/边界：queue扩域、timeline缺失、缓存时间未知、partial Meta、所有权/lease、公开摘要边界见第1/3/4节。
- 面试表述：可以说“从真实回执定位格式不兼容并设计同源摘要到类型化证据的离线桥接”；不能说“真实黄金切片、Evidence发布或生产默认已上线”。

四线状态：本地实现维持RQ-252，新增RQ-253准备证据；学习材料完成但所有者理解未新增确认；仅审查本地源码/历史回执，无新外部来源审计；公共证据维持RQ-252实现afda193 / Actions34076953653，无新部署。Stage8/8E仍in_progress、production_media=0，默认模型、GLM-5.2和前端不变。

## 6. RQ-254：离线桥接实现与验证

用户“继续”授权第3节后，已在隔离工作树完成该批，不扩大为外部运行。使用Code与karpathy-guidelines组织可验证步骤并保持最小范围；不引入新依赖、网络入口或生产默认。

### 设计、代码与数据流

- `app/evidence/adapters.py`仅调整版本表达式和输入长度：首两段各1—3位ASCII数字，后续0—2段各1—10位，总输入至多32字符；四段16.16.804.9184归一16.16，旧None/两段/三段行为保留。拒绝空段、尾缀、超长和非ASCII数字，不修改原Summary。
- 新增`app/evidence/summary_bridge.py`，入口`summary_to_evidence`和不可变结果`SummaryEvidenceProjection`。纯JSON Summary→容器/计数/身份/时间/队列核对→有效行转换→现有`fuse_evidence`→结果，不取系统时间、不读环境或文件、不发网络、不append快照。
- 结果带完整Summary规范JSON的SHA-256、included/excluded/failed计数、requested/effective queue、fallback与观测语义、现有不可变EvidenceBundle。digest_scope明确为summary_projection；不是原始Riot响应hash，也不是用户身份验证。每行source_digest沿用现有允许字段投影的摘要；完整Summary摘要变化不要求每行事实摘要都变化。
- 复用`validate_summary_document`后补局数/重复ID/失败重叠/排除集合核对。仅布尔True纳入；无有效局明确拒绝。有效行损坏不静默跳过；未知timeline_status拒绝，unavailable保留。指定队列与每局实际queue一致；扩大查询必须满足requested queue非空、effective queue为空及fallback=True。
- observed_at未提供时明确标记summary_generated_at，提供时标记caller_observed_at；时间必须带时区且不晚于显式now。DataDragon身份与Summary版本/language一致，缺身份不捏造来源。官方补丁与Meta沿用既有类型、缺口/过期/冲突规则；未来获取时间拒绝。
- 私有输入只参与本地摘要和允许字段投影；错误输出用EvidenceAdapterError安全码，不转发旧验证器中的玩家/比赛正文。结果不包含原Summary、Memory、raw body或失败正文。

### 测试证据与运行手册

先得到新模块不存在的收集失败，独立版本用例得到真实四段版本拒绝及非ASCII版本错误码不一致的失败；完成窄修复后首轮96项通过。再补同源应用整链和显式输入边界，并运行相邻快照/产品投影测试，最终128 passed（7.76秒）。新增测试共52项：版本16项、纯桥35项、应用整链1项；数量按pytest收集结果核对。

整链首次失败来自旧demo英雄ID900001超过既有Riot合同上限10000；新增整链测试使用合法范围内的合成ID75，保留合成标签和旧fixture，不扩张合同。报告经过实际本地Runtime、检索、假Provider及回执链，SummaryBuilder只调用一次；证据摘要与builder交付前的完整JSON一致，输入不变。此测试不等于真实模型/数据库/页面采用。

覆盖2/5局、请求5实际2、混合版本、排除及detail失败、缺失时间线、队列fallback、重复ID/计数布尔伪装/未知状态、缺失/无时区/未来时间、来源身份不符、partial/expired/conflict Meta、安全码、不可变结果及输入不变性。禁用文件open、环境getenv、socket连接后重载桥模块并转换通过；Python导入器自身的源码加载不算业务零I/O证明。

```text
python -m pytest tests/test_evidence_summary_bridge.py tests/test_evidence_fusion_vertical.py tests/test_evidence_fusion_contracts.py tests/test_coach_application_composition.py tests/test_evidence_snapshot_contracts.py tests/test_evidence_product_service.py -q
python -m compileall -q app/evidence/adapters.py app/evidence/summary_bridge.py tests/test_evidence_summary_bridge.py tests/test_evidence_fusion_vertical.py tests/test_coach_application_composition.py
python scripts/check_project_governance.py
git diff --check
```

最终128项通过，编译、治理与diff检查通过。没有重复开发四案、全套公共测试或真实请求，没有本批需清理的项目临时产物。

### 八维与边界收口

问题/原理是让报告与来源证据来自同一份摘要；设计/实现、代码地图和数据/控制流见本节前半；验证与运行手册见上述命令及实际红绿证据；失败/安全/边界见本节和第4节。面试可表述为“实现无I/O的同源摘要证据桥，并用真实版本格式坏例和假Provider产品整链验证”，不能说真实黄金切片或生产Evidence已经发布。

桥只返回内存结果，不承诺现有应用自动调用它、不冻结并发调用方、不替代数据库owner/task/run与Worker lease校验；后续应用装配须消费同一不可变输入/核对摘要。它不重新计算所有游戏统计、不审计训练时长语义，不解决DataDragon缓存新鲜度、OP.GG英雄名别名或广度接入。

四线状态：本地RQ-254实现和128项验证完成；八维学习材料已提供，所有者理解未新增确认；仅本地源码/历史证据，无新增在线参考审计；公共证据仍为RQ-252，RQ-254未提交/推送、待本实现同SHA公共CI，无新部署。Stage8/8E仍in_progress、production_media=0；默认模型、GLM-5.2、前端和生产Worker不变，真实API=0。
