# 真实黄金切片实施与恢复计划（RQ-258）

**Goal:** 从真实比赛、静态定义、官方版本与 OP.GG，贯通同源 Evidence、合格 Coach/训练报告、持久化及 live Workbench 消费。

**Architecture:** 复用 Summary Builder、Coach 1.2.0、Evidence 桥和 ADR-0099 A/B/C，不切生产默认。外部获取与产品执行分离；冻结可重放数据后先离线检验，再进行有身份与计数的真实观察。

**Tech Stack:** Python、现有 Riot/HTTP/MCP clients、Pydantic、PostgreSQL、现有 Workbench。

## 当前事实与纠正

### 接续离线复现与本批决定（2026-09-10）

保存 v14 Summary、完整本地检索和新增 mid/support 目标的离线对照已复现：初始 11404 单位；四个具名测试查询后为 16409，超过旧 Skill 的 16000。查询为本次测试输入，不是声称恢复了 v14 原始查询。一/二查询能走到模拟评分，不代表真实报告质量。v10 未保存原始回答及检索载荷，无法回溯定位具体准备异常；本批新增严格安全分类，保留旧终态和旧回执。

不再截短知识。为黄金切片建立独立 Coach 1.3.0 / Skill 0.5.0 / Program 2.3.0，给多轮消息 28000 本地估算单位；旧1.2.0/16000资产保持不可变。每请求仍须经过完整包络的64000输入硬门，最多9次模型调用、8次工具、8192输出、649728总token、一次修订及85分/事实/引用/注入门不变。此处是旧总预算内的上下文分配调整，不改变生产默认或总资源墙。用真实形状五局、完整多批检索、满调用修订路径和超限反例验证后，才决定公共与新鲜协议门。

历史需求保留：主树 requirements_change_log.md 的百科助手 RQ-193 与本树适配器一致性 RQ-193 是两个主题，按路径区分，不能用同号互相覆盖；Portal/Account/Workbench后续视觉修缮与长期位置Memory/目标交互仍待完成。本批不编辑主树。

### 2026-09-10 位置语义与接入修复（本地，尚未完成黄金切片）

- 用户补充：玩家可主玩一个位置、偶尔玩其他位置，也可主动转位置；不能把异位置局直接判为补位。单局实际位置、长期位置分布、显式训练目标必须分开。目标支持多个位置，显式当前意愿优先于历史倾向，但不能覆盖历史比赛事实。
- 本次先实现黄金切片的接入层：按已纳入分析的每局实际分路分组，每个分路一次 OP.GG 工具查询；完整解析有大小上限的响应后选择目标英雄，不再先截前十条。旧榜单消费者默认仍保留前十条，未改变其合同。
- 分位置统计本次场次与补刀/经济/早期死亡/视野均值，并保留每项有效样本数；缺失不当零。显式 `--training-position` 可重复指定；未明确目标时保持 unspecified，不把五局当长期画像，不宣称识别出补位意图。
- 缺失诊断区分 request_failed、invalid_response、target_not_in_response；最后一项仅指当前响应未对上目标（含潜在命名差异），不等于 OP.GG 全站无数据。不得改用其他位置或无关热门英雄填充缺口。
- 尚待接线：长期历史窗口/偏好 Memory、通过对话确认或更新目标、正式产品请求与 UI 目标编辑。本次只有候选入口可显式传入目标；不能说完整交互已实现。目标位置无样本时只提示缺口，不用旧位置成绩评价新位置。
- 移除了随意截短查询、知识正文及命中数的 `_CappedKnowledge`，恢复完整本地检索器。候选专用 JSON 事实块压缩保留所有值、可信策略、Markdown、外层 canonical 包装和 16000 上限。保存的 v14 五局离线测量为 12286→10576，节省1710，无省略；这不证明多轮预算已足够，新增位置事实还需计入。
- 完整 Training 持久化/live UI 尚未验证，所以入口一律保留 degraded，不能凭 DTO 和报告 digest 标 passed。真实模型报告、静态版本对齐及官方来源 provenance 仍待修复验证。早期草稿之后已有 b0d469f/b910556/31a9806 三个本地提交，下方“尚未提交”为早期历史，不是这三个提交不存在。

### 本次验证与后续顺序

本地测试覆盖目标在第12条、部分/零命中、请求失败/错误位置、跨位置一次查询、目标转位置不重标历史、辅助不套补刀目标、指标缺失与大小写去重、候选应用模拟发布及 JSON 事实等价。已有聚焦与相邻164项通过；最终数量以本次progress记录为准。未新增真实外部调用。

下一步在同一黄金切片内完成：真实形状上下文+完整检索的离线多轮预算验证，定位报告准备失败；修复历史静态版本与官方来源身份；通过公共验证后做有界真实消费，最后验收 Training 持久化和 live Workbench。不重开 A/B/C，不切生产默认。

八维补充：问题/原则是位置事实与意愿分离；实现地图为 `coach_positions.py`、`opgg.py`、黄金切片入口和 `coach_context.py`；流程为实际对局→分位置样本/目标分离→定向资料→同源报告；验证见位置/适配器/上下文测试；运行入口支持重复 `--training-position`；缺口与安全保持未知不推断；可表述为“候选接入层支持混合位置与明确训练目标”，不能表述成“已实现长期画像和对话目标管理”。

### 早期草稿历史

- A/B/C 的公共闭环仍是 `80ed693` / Actions `34324718617`。当前新增代码尚未提交，不属于该 SHA 的公共验证。
- 当前新入口是未验收草稿。旧 v1/v2/v4/v8/v10 回执无条件写 `passed`，只表明函数返回，不能用于黄金切片通过裁决；保留原文件，撤销其通过含义。
- v10 包含 5 局 Riot、Data Dragon、官方版本 feed 的摘要和 OP.GG。比赛 16.17 与静态 16.18 不一致，且部分英雄/位置不能 join；缺口不应抹平。
- 官方 patch 草稿错误地把抓取时刻当发布时间，版本 feed 未核对目标版本即赋值；必须修复 provenance，不能声称取得官方 patch notes。
- Coach v8 的 Agent 因 `context_budget_exceeded` 停止；v10 为 3 次 Provider 请求、Agent final_response，但 Harness `rejected/draft_preparation_failed`。`_CappedKnowledge` 对 dataclass 使用 `model_copy` 是本轮引入的错误，不能归因模型质量。
- 草稿只校验 UI DTO，未做 live UI 消费、训练持久写入或 A/B/C 联调；完整黄金切片仍未完成。
- 真实获取发生于未提交代码，且前几次未预约/计数，不能用 HEAD=`26a65ed` 冒充执行代码身份或声称准确总调用数。停止盲重试，修好离线入口再继续。

## 执行顺序与完成判据

1. 修复入口真实性与资源边界：只读预检，输出/运行身份在网络前预约，持久失败/调用计数，严格来源/结果校验，默认关闭外部 I/O；测试无来源、模型拒绝、重复运行、错误路径时都不能标通过。
2. 保存私有真实 Summary/typed 来源快照供重放；公开只保留摘要与允许字段。读取旧合法工件而非反复获取同一玩家，不能把公开 DTO 校验说成 UI 已运行。
3. 先复用现有完整检索器修复错误；定位上下文超限，以显式事实投影/既有预算合同处理，不能截断知识正文却沿用原摘要或默认降低质量门。
4. 离线用真实形状 Summary + fake Provider 走实际 Coach、报告/引用/评分、同源清单、A/B/C；补齐 4 类来源在建议中的实际消费者。公开 CI 及新鲜协议门满足后再做一次有界真实观察。
5. 将同一产物通过现有 API/Workbench 呈现，验证 Evidence/Trace/Training 可追溯；只在报告质量、四来源 provenance、持久化、UI 全部可复核时认定 golden slice 完成。

## 验证

聚焦：`python -m pytest tests/test_coach_real_data_golden_slice.py tests/test_evidence_fusion_vertical.py tests/test_coach_application_composition.py`。
随后根据实现范围运行 PostgreSQL/前端测试、编译、diff 与 `scripts/check_project_governance.py`。旧 24 项测试仅覆盖预检与 adapter，不能证明执行器安全或完整。

## 八维学习与边界

问题/原理：会回答合成样本不等于真实产品闭环，外部来源、模型、存储和界面必须由同一份事实连接。
设计/实现：复用现有能力，不另造 Runtime；入口负责冻结来源和计数。
代码地图：`app/evaluation/coach_real_data_golden_slice.py`、`scripts/run_coach_real_data_golden_slice.py`、`app/evidence/summary_bridge.py`、`app/product/coach_composition.py`、ADR-0099。
数据/控制流：请求→有界获取→冻结 Summary/来源→Coach/训练→同源发布→事务→API→Workbench。
验证：上述逐层退出条件，开发观察/公共 CI/生产准入分开。
Runbook：默认预检，失败留痕，修好本地证据后才新增运行身份，不重写失败回执。
失败/安全/边界：缺源/未知发布时间/过期/跨版本诚实降级；无报告或无 UI 消费不算完成；不重置 Docker、不删除卷、不切生产默认。
面试表述：当前可说“已打通并公开验证同源事务与恢复，正在补真实黄金切片”；不能说“真实黄金切片和 8E 已完成”。

### 接续实现与验证记录

RQ-258 接续离线加固：新增黄金切片专用 Coach 1.3.0 / Skill 0.5.0 / Program 2.3.0，上下文28000但64000输入/9调用/8工具/8192输出/649728总token及质量门不变；旧1.2.0身份保留。完整RAG与保存五局的脚本重放达到8工具/9模型/一次修订，模拟低分仍拒绝，不构成真实质量证据。报告准备安全分类、调用前持久预约计数、真实Trace摘要读取、按实际比赛选择历史静态版本和官方文章时间校验已本地实现。无新增外部调用、数据库或前端修改。官方页面元数据/显示版本映射仍待来源实证，跨版本单快照与Training/live UI仍有缺口。下一步为本批公共验证，随后按计划补新鲜协议与保存数据的真实Coach观察；不重开四场景或A/B/C。

验证：本批聚焦和相邻回归254 passed；随后针对真实目录含lolpatch旧条目的修复18 passed。保存v14输入重放：旧1.2.0初始11404、四工具后16423超16000；新1.3.0同初始输入，8工具后最终23212、九模型请求最高完整输入估算46654，输出保守预约73728，模拟评分拒绝。测试查询是具名离线输入，不是恢复历史原始查询；v10仍无原始回答/工具载荷，具体历史根因未知。

来源边界：标准静态版本严格同major.minor选择，旧lolpatch条目只作为可识别历史目录项，不参与当前匹配；单快照不能表达多版本时返回缺失，不捏造统一版本。官方文章要求版本标题和唯一带时区发布时间，不再回退版本feed；16.xx内部版本到26.xx显示版本尚无本轮直接证据，不硬编码映射。

运行边界：新schema1.2区分evidence_projection_verified与workbench_projection_verified；DTO校验不能把live UI标成已验证。持久reservation在客户端构造前创建，来源及Provider每次调用前fsync计数，失败/中断留终态；真实Trace用既有摘要校验读取，不猜调用次数。黄金入口在获取前关闭不限队列回退；排位记录为空即停止，不追加其他队列请求。获取预算仍按预检上限。回执分离/队列停止相关65项与原Summary默认行为9项回归通过。


### 官方版本来源实证补齐（2026-09-10，首批提交之后）

`a921e573ba71cf1a609c5403eb5d7275d4b23116`已推送，Actions 34440769118正在验证，尚不宣称通过。其后仅增补真实页面解析和已核对版本对，不复用该SHA为后续改动背书。

来源审计读取一次官方文章、两份官方静态目录，均调用前持久计数并保存原件到私有data/runs/source_audits；另有搜索工具的官方页面检索，不计成Coach执行调用。Riot玩家API、OP.GG与真实Provider新增调用均为0。网页查阅是来源审计，不是黄金切片已消费证明。

- [官方26.17文章](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-17-notes/)：HTML SHA256 `cf7b426c7860329488678ab7324f3f9df06c4cc7d8d3feae9e85175871009956`。2026-09-10T05:22:55Z读取；317159字节。og:title存在，article:published_time不存在；application/ld+json的TechArticle含version=26.17和datePublished=2026-08-25T18:00:00Z。
- [16.16.1静态目录](https://ddragon.leagueoflegends.com/cdn/16.16.1/data/en_US/champion.json)：SHA256 `970c2b0ead25bd132ff9df260a42130c02e4d1cf3adbeb62f32bc3dc8178a324`。
- [16.17.1静态目录](https://ddragon.leagueoflegends.com/cdn/16.17.1/data/en_US/champion.json)：SHA256 `056275dcddac3ecc81c497d269b10e7abe6a66ceaa0d6d965f1fc8d00943760b`。
- 两份目录的Xerath生命596→575、Nocturne生命655→640/护甲38→36、Vayne生命550→580/成长103→98/回复3.5→4/回复成长.55→.5与26.17公告一致。据此作显式、有限的16.17↔26.17工程对应推断；不声称官方文档直接宣布所有版本major+10的通用规则，也不自动扩展16.18。

解析器现读取目标文章的结构化日期，拒绝冲突日期/错误headline/version；无审计映射时不猜URL、不发请求。Evidence patch_version保留16.17匹配比赛，update_id保留riot-patch-26-17显示身份，内容SHA绑定完整文章。真实保存HTML离线解析通过，38项来源及入口测试通过。四来源实际建议消费、保存输入真实重放、Training和live UI仍待接线；本条取代上文“官方页面元数据与此版本映射仍未知”，旧记录保留。


### 保存事实重用、来源消费与真实执行门（接续本地）

第一批a921e573ba71cf1a609c5403eb5d7275d4b23116 / Actions34440769118、来源解析dde2fa5a5d6b5a67a8e55b7dd482d091f66231c5 / Actions34441108689均已核对同SHA三job成功。本节代码在二者之后，不能继承其公共证据。

问题/原则：保存过来源清单与模型收到来源事实不同；复用对局事实也不能延续错误静态版本或伪官方快照。实现复用既有FileEvidencePublicationStore完整验签链，通过原运行ID、原Summary摘要、玩家、区域、队列和局数绑定读取；路径/摘要/请求不符即停止。旧五局原件和采集时间保留，仅在分离JSON值上重新补历史静态名称，旧Meta/官方快照不直接重新准入。

代码地图：golden_saved_input.py负责读取与静态补充；golden_source_context.py只投影允许字段，过滤不同位置/目标和过期Meta；黄金入口组装实际Coach。Riot指标仍来自Summary，静态信息解释名称，官方版本/时间只支持版本对齐，OP.GG以位置、有效期、允许用途和胜率等数据进入模型上下文。无改动正文不宣称buff/nerf，无段位/区域不宣称同段位比较。报告质量和来源实际用得正确仍待真实观察。

Runbook：新增--saved-run-id与--saved-summary-digest成对指定，预检schema1.3显示Riot调用上限0，不读取Riot密钥或创建其客户端；仍允许有界静态/官方/OP.GG更新。真实--with-provider还必须传--ci-run与--protocol-report；复用既有严格验证器，当前提交同SHA三job成功、随后真实三调用协议通过，才进入预约和来源工作。Provider固定标准Flash端点、高档合同60秒及既定预算。安全回执未知异常code归入coach_execution_failed，不保存任意异常载荷。

验证/数据流：保存v14原件经完整发布链离线读取成功，5局，原观察时间2026-09-10T02:39:15.484653Z；不重抓Riot。加载→验证→静态补充→新来源投影→完整RAG/Coach→同源清单。篡改、错误区域/玩家/摘要、空门证据、过期/无关Meta分别拒绝。完整来源夹具与8工具/9模型/一次修订保留低分拒绝。旧v14来源包只作负面/预算重放（不重新准入）：初始12739、最终24547/28000，最高完整输入49324/64000，9次模拟调用，evaluation_failed；不是新的真实报告结果。

当前不新增真实Provider/玩家API/OP.GG调用，数据库与live Workbench仍未执行，8E继续in_progress。下一步为本节同SHA公共验证及保存数据的实际有界来源/Coach消费准备。面试可说已实现可验签重放、分位置来源投影和真实执行门，不可说已完成黄金切片或生产准入。

本节聚焦与相邻回归106 passed；治理、改动Python编译和diff检查通过。


### 同源评分与修订补齐（Coach 1.3.1，接续本地）

d605c04abedd9796fab8b466f3cfff11dd3a12fb / Actions34441904153三job已同SHA成功。公开验证后本地进一步检查发现，1.3.0只有初稿读取扩展来源，评分fact pack和修订knowledge仍缺这份输入；在新增真实模型调用前修复。

新独立Coach1.3.1 / Skill0.5.1 / Program2.3.1 / flash_v2_golden_sources显式开启include_deterministic_source_facts，将同一个既有deterministic_report作为数据传给评分、评分纠正、修订和复评；没有另造获取或解释来源的链。旧1.3.0摘要cb2d1293578cadf08e9a302c40c3f67de3210ec7117e8b08a375a280b4a7f5c2与旧资产保留，默认1.2.0不变。新合同摘要f11f2755d19b2c670f86b54dce50ef60e1786fa29f0dacecb2c692572861d60f绑定该行为，所有质量/预算/次数墙不变。

断网对照证明旧版仅前4个请求含来源包身份，新版9个请求全部包含，同一完整检索及低分拒绝路径未变。保存v14来源仅作预算负面对照，新版各请求上界26402/36440/42882/49324/34108/34342/17202/34108/34342，输出预约73728，总额仍低于649728。没有新增真实Provider/玩家API/OP.GG请求。

Training完整持久化还需要本人档案，当前保存的ShowMaker是观摩对象，不能把它宣称为用户本人。已向用户询问本人Riot ID/区服或观摩范围；问题未回复前只推进可独立完成的报告和来源工作。旧观摩数据不自动写个人Training。

同源评分补丁聚焦/相邻115 passed，治理、改动Python编译、diff检查通过。


### 47e8914真实观察与单次等待分配（接续）

47e89145800b4defb293003af3c6993ba4a83e03 / Actions34442973048已同SHA三job成功。之后真实三调用协议通过：输入1007、输出90 tokens。独立运行golden_20260910_saved_47e8914复用v14五局，Riot请求0；静态5、官方文章1、OP.GG两位置各一次工具（各自初始化/目录一次）。中路Vex/Anivia/Locke/Syndra与辅助Camille全部目标命中，比赛16.17.810.4348与静态16.17.1、官网显示26.17对应；官方文章日期来自JSON-LD。

Bundle 754070df2233b35d8ddf6716064812d309dfd5122fd10be584d59a6e2580b015为complete/medium，无冲突或gap；OP.GG仍partial、没有upstream_patch，只支持其允许的当前快照用途，不能因此声称是精确16.17同段位基准。

报告未生成：第一请求14.75秒后返回4个工具调用，四次检索全部成功；第二请求已发出，60.01秒时provider_error_code=timeout，Agent provider_error、Harness rejected/agent_loop_incomplete、terminal draft_preparation_failed。不是旧context_budget_exceeded，也没有进入评分。仅观察到第一请求输入6401/输出335 tokens；第二请求用量未知，不宣称完整token总额。本轮协议3+Coach2=5次真实Provider尝试，全部有调用前持久计数，旧回执不重写。原因限定为客户端等待超时，不能断言上游内部为何缓慢。

在既有Agent120秒/整次480秒内，以独立Coach1.3.2、Skill0.5.2、Program2.3.2、flash_v2_golden_latency将单次最大等待60→90秒；仍取调用者剩余Agent时限、整次剩余时限与90的最小值，SDK额外重试0。9调用、8工具、28000上下文、64000输入、8192输出、649728总token、85分及一次修订不变。新身份67ae847819a64dc009e448b518e0fe3564bd395dfc4aed34aff3509cd2b854cc，旧1.3.1资产/摘要冻结。这是根据实际60秒失败在原外层时限内调整分配，不增加整体执行时限，不代表上游90秒必然成功。

验证：116项相邻检查通过；新时限夹具最初误用字符串MessageRole导致3项测试构造失败，修正为实际枚举后4项时限测试通过。无真实睡眠，模拟75秒响应分别触发旧60秒拒绝/新90秒接收，调用者12秒和全局剩余5秒仍收紧请求、失败不重试。下一步为本补丁同SHA公共验证、新鲜协议，然后一次有界观察。Training仍等待本人档案/观摩范围答复；尚无数据库或live UI验收。


### 2531f7a真实报告与人工语义复核（2026-09-10）

2531f7a7f62473a95aed54b7f4e4cdbf18c36a63 / Actions34444395200三job已同SHA成功；新鲜协议3调用、输入1007/输出96 tokens通过。保存五局运行golden_20260910_saved_2531f7a使用Riot0、静态1（其余命中已核对缓存）、官方1、OP.GG两位置各一次工具/初始化/目录。源Bundle 09d47a7e5ff61a29ccf7c55503bad025e7c3e7b4ef83fd234b9556fbaa23338d，旧观察时间保留。

Coach实际5调用全有响应、4检索、一次修订；输入40476/输出7393 tokens完整观测。Agent第二请求60.94秒返回，Agent共73.67秒，整次112.38秒，没有扩大120/480秒外层预算。自动评分88发现03:04/03:47被误写为3分钟内，修订后98/pass；报告摘要74733248689306cced62022eea8652022690bbe8db988003a5adb62e103846ec，Runtime published、Evidence投影验签成功。这里published仅指本地Harness产物，未写数据库或live UI，黄金回执仍degraded。

人工不予黄金验收：报告第6节明知goal_source=unspecified却写“默认延续当前中单主位”“暂不安排辅助位”，与当前样本不等于长期主位/训练意愿冲突；第1节还把死亡均值升高笼统写成数值拖低。自动评分漏检，不能用98分替代业务语义验收。OP.GG仅在边界段落出现，未以具体事实形成建议，因此四来源建议消费尚不完整。旧报告/评分/回执不改写，私有data/runs/golden_manual_reviews保存绑定报告摘要的独立否决记录。

修复原则：新独立Coach1.3.3 / Skill0.5.3 / Program2.3.3 / flash_v2_golden_positions，trusted POSITION_POLICY区分样本位置、长期位置和显式训练意愿。目标未知只给条件式分位置选项，不能默认最多场次的位置或排除其他位置；明确多目标都须尊重，缺样本保持缺口；评分检查正文实际建议，不能被末尾免责声明覆盖。策略以合同context_policy摘要绑定，初稿作为INTERNAL_POLICY输入，评分/纠正/修订/复评在数据块之外接收；默认关闭，旧1.3.2及更早资产/摘要保留。新摘要fb6df08655395d17e85be097b5a4cd859e18c8bee22b98167329892da4d2246f。全部模型/工具/时限/token/85分/一次修订预算不变，不新增自动重试。

验证：96项相邻回归通过；新策略3项断言最初未考虑Context JSON换行转义导致测试漏识别，检查完整原文或其JSON编码后4项全部通过。涵盖未知目标、多目标、无样本新位置的9请求/8工具/一次修订路径，模拟低分仍拒绝。保存本次真实Summary/Bundle仅做离线预算重放：初始13993、最终25801/28000；完整请求上界28910/38948/45390/51832/36572/36806/19666/36572/36806，全部低于64000，总上界与73728输出预约低于649728，9个请求均含同源身份及位置策略。这是送达与预算证据，不是真实语义效果证明。

本次新增协议3+Coach5=8个Provider请求；本接续合计13次（此前5次），先前超时请求用量仍未知，不宣称累计token完整。下一步为1.3.3同SHA公共验证及新鲜协议后的一次有界语义观察。Training等待本人档案或观摩范围；真实OP.GG建议消费和live Workbench仍未验收，8E不前移。


公共验证补记：7ce4e09fc4cbfe7961e6ea4f095e06446e351b14 / Actions34446228757 的打包和数据库成功，完整测试2954 passed、152 skipped、127 subtests passed、1 failed。唯一失败是test_golden_call_journal的入口合同断言仍为1.3.2，实际1.3.3的调用计数/报告/证据路径已通过；修正测试预期后相关10项通过。没有新增真实请求；修正提交仍需自身公共验证。


### e39cb6e真实拒绝与生成/评分事实一致性修复（2026-09-10接续）

e39cb6e9fbdc4cf9867ae118a70b3528d21f333e / Actions34446812086三job成功：pytest 2955 passed、152 skipped、127 subtests passed；PostgreSQL 208 passed。随后新鲜三调用协议输入1007/输出95 tokens通过。golden_20260910_saved_e39cb6e复用原五局，Riot0、静态1、官方1、OP.GG两位置各一次工具/初始化/目录。Bundle 7a909e33d9ac74b18bdaf9d69b6930b99e5d544d2887e4bd9cc45b9aaa09a154。Coach 5调用全响应、3检索、一次修订，输入42390/输出9817 tokens，整次156.5秒；62→82分，rejected/revision_budget_exhausted，无最终发布报告。旧失败不改写，手工归因另存私有golden_manual_reviews并绑定原摘要字节SHA。

位置约束真实起效：未知目标时给中/辅条件选项，未替用户默认主位；第一轮评分拦下把全样本输局6.45 CS/min误标为中单输局的问题。实际中单输局均值9.01、赢局约8.81，结论方向不同；修订已改正。第二轮却称单局伤害占比22.3%/27.5%及2026-09-10T02:39:15Z没有事实依据。原Summary实际有damage_share=0.2232/0.2753和metadata.generated_at_utc=2026-09-10T02:39:15.484653+00:00；初稿Context也含这些字段，但build_fact_pack和deterministic_report遗漏，导致评分看不到依据。这是可重现的资料差异，不能降门槛或改写已拒绝回执。

实现：新增独立Coach1.3.4/Skill0.5.4/Program2.3.4/flash_v2_golden_fact_parity，include_generation_facts显式开启。app.agent.context.project_recent_form_facts复用原Context字段白名单/10局投影cap，原初稿构建改为调用同一函数，内容保持兼容；评分、纠正、修订和复评把同一份生成事实作为data-only JSON送入既有消息，deterministic_report/来源上下文仍保留。没有另做一份手选字段，也没有读取额外秘密/发请求。旧1.3.3摘要fb6df08655395d17e85be097b5a4cd859e18c8bee22b98167329892da4d2246f与旧资产保留；新摘要2f498babc867a984db82f4777064b2de82c42b40566aa35fea3b593b2c691c47。

预算/替代方案：最初直接追加完整原始Summary JSON，在真实保存五局上评分请求上界116856，原64000门在发请求前正确拒绝；放弃该做法。当前方案对齐生成实际可见的事实投影，不把原始冗余字段额外灌入模型，也不截断任何已经送入初稿的值。满路径离线重放9调用、8工具、一次修订；初始13993/最终25801上下文单位，完整请求上界28910/38948/45390/51832/47654/47888/26466/47654/47888，加73728输出预约仍在649728内。所有请求携带原来源身份/位置策略；测试逐字段比较首个真实形状请求的事实JSON与后续全部5个评分/修订请求，含采集时间与伤害占比，旧版保持缺失差异。模拟低分仍拒绝，不能据此宣称真实报告已合格。

本接续真实Provider尝试累计21次（前13+本次协议3/Coach5），更早60秒超时的token仍未知。下一步为本补丁比例回归/公共CI及新鲜协议后有界真实观察；OP.GG仅边界声明、四来源实际建议消费尚不足。个人Training需要本人档案及已确认目标；数据库/Workbench应在模型运行前确定真实任务身份，不能把已有golden-slice本地文件事后改绑到另一个owner/run。原接口闭环A/B/C不重开，生产默认不变，8E不前移。

本批最终聚焦与相邻回归136 passed；生成事实投影/旧Context与Program身份/位置策略/完整RAG修订均通过，治理和diff检查通过。


### 6facdf6公共验证与90秒超时观察（2026-09-10）

实现6facdf6bc37bc72feef64ecc227f87cf36d2552a / Actions34456915878三job成功；pytest2958 passed、152 skipped、127 subtests passed，PostgreSQL208 passed。其后新鲜协议3调用通过，输入1007/输出125 tokens，协议摘要5cc3fcbddcb4f73f2d7dd39a0ccff884ed436565f89dcc6798b41f180a69c846。

golden_20260910_saved_6facdf6使用1.3.4原合同；Riot0、静态1、官方1、OP.GG两位置各一次工具/初始化/目录。Bundle 1a85868ac1ec60f87eecb5d9387d1c6d2205cea7dcaffce258c8eaae995dfc8d，五个英雄均命中；OP.GG仍partial/未知精确上游版本，不能当历史同版本基准。原五局与采集时间保留。

Coach3次尝试、2次完整响应、5检索成功；首两请求11.56秒/8.44秒，第三次90.02秒后provider_error_code=timeout。Runtime110.09秒，Harness rejected/draft_preparation_failed、failure_code=agent_loop_incomplete，无初稿/评分/修订/最终报告。不是评分否决，也不是上下文超限；新事实同步未到达真实评分环节，效果仍未知。已知输入15566/输出516 tokens，超时请求用量未知，不能以已知部分当完整总量。本轮协议3+Coach3共6次，本接续累计27次Provider尝试；两次超时用量未知。

保留原回执/Trace/预约，不放宽90/120/480秒墙，不新增自动重试或连续重复实跑。90秒也会超时，说明前次60→90秒仅改善一个观察，未证明可靠性解决；当前只能归因为客户端等待超时，缺少上游处理和网络分段证据。下一步先审查既有候选延迟证据与最小有界诊断方案，再决定是否值得新实跑。个人Training仍等本人档案/目标，数据库与live Workbench未验收，8E不前移。本文后续文档提交不冒用实现6facdf6的实跑身份。


### 有界HTTP分阶段诊断与Luna配合（2026-09-10接续）

用户要求可行时沿用Luna配合省额度保质量。执行方式为明确输入/输出的独立只读任务交给gpt-5.6-luna，主Agent负责实现、共享文件修改与最终证据核验；不宣称已量化节省比例。本次Luna核对四次原始Trace并审阅补丁，主Agent重新计算每次延迟和已知token合计，结果一致。独立工作结束即收口，不开重复Agent或扩大任务。

问题/依据：47e8914初稿请求60.015秒超时，2531f7a初稿60.937秒完成，e39cb6e初稿75.735秒完成，6facdf6第3次请求90.016秒超时。成功检索分别4/4/3/5次；现有事件只有请求总耗时与笼统timeout，未记录TCP/TLS/响应头/响应体阶段。不能把“请求慢”直接归因为模型思考、代理或网络，也不能据此扩大90/120/480秒墙。

实现/数据流：GoldenCallJournal先持久预约Provider序号→JournaledProvider启动单次诊断→OpenAI DefaultHttpxClient既有请求钩子附加httpcore trace回调→只按固定白名单保存阶段名和单调耗时→请求成功/失败/中断均以create-only http-NNN.json写在原预约目录。最多64事件，超量只计数；不读取info中的请求、响应、异常、headers、URL或密钥。事件缺失保持未知，连接复用不凭空补建连耗时；响应头等待时间也不能区分网络与上游处理。诊断文件写入失败仍暴露持久化失败，不把它冒充原Provider根因；硬进程退出可能只有原预约而无诊断终态。

范围/兼容：仅黄金候选入口启用，普通Provider与协议原路径不变；glm-5.3-flash/high、非流式payload、HTTP默认连接池/代理、SDK max_retries=0、合同1.3.4身份、9调用/8工具/一次修订/质量门保持不变。HTTP客户端在构造、应用构建、执行和验签任一失败时均关闭。没有新增库、流式产品接入或生产默认变更。

验证：使用真实OpenAI SDK→httpx→httpcore及测试专用假网络后端，直接得到连接超时、响应头超时、响应体超时与成功阶段事件；所有情况只有1请求，无外网、无实际等待。额外验证私密哨兵不落盘、未知事件拒绝、64条上限、逐次隔离、中断留痕、原请求正文/stream保持、完整Coach假Provider未发HTTP时记录0且资源已关闭。相关102 passed与27 subtests passed；资源释放最终调整后聚焦12 passed，改动Python编译/diff通过。真实调用新增0、累计仍27次（历史两次超时用量未知）。

下一步：本补丁同SHA公共检查通过后，重新绑定新鲜3调用协议与一次带诊断的保存五局观察。只有阶段事实可观察，不承诺必然找到上游原因；若再次失败保留完整回执，不连续重试。本轮不重新运行旧四场景或A/B/C；Training与live Workbench仍未完成，8E不前移。


### 8c02112带诊断真实报告与剩余消费缺口（2026-09-10）

实现8c02112aeb8e8be4df2669f57d1f076f8065f36e / Actions34458836398三job同SHA成功：pytest2964 passed、152 skipped、127 subtests passed，PostgreSQL208 passed。随后新鲜协议3调用通过，输入1011/输出113 tokens。golden_20260910_saved_8c02112仍以合同1.3.4运行；Riot0、静态1、官方1、OP.GG两位置各一次工具/初始化/目录。Bundle 1db7b2e7712c35b73ec02b626df40ac550b0dcc11e62f019d6ccf91dda10ff90，原五局观察时间保留。

Coach5调用均响应、4检索成功、一次修订；首轮90/needs_revision只发现“中RD路”错字，修订后95/pass。输入49002/输出6938 tokens完整观测，Runtime112.125秒；Harness本地published/quality_gate_passed，最终报告SHA f938a13d573f2da7e368e36e9e9a6bd5c58113b440ddfc80735f52dea12a1726。伤害占比27.5%本次被复评正确核对，生成/评分资料一致性得到一次真实正面观察；不能以一次成功宣称模型普遍可靠。

HTTP5个诊断文件均各1次实际HTTP请求、无事件超限。初稿请求2总62578ms，receive_response_headers从0到62563ms，正文62563到62578ms；本次主要在等待响应头而非接收正文。没有超时，所以不能把本次阶段归因回填60/90秒旧失败，更不能区分上游处理时间与网络传输。首次连接的代理TLS事件未记录，核对已安装httpcore源码发现真实logger前缀proxy，原白名单误写http_proxy。修正为proxy.start_tls并新增真实httpcore HTTPProxy/假网络CONNECT+TLS测试，聚焦13项通过；不更改旧诊断或声称其TLS耗时为0，该小补丁待自身公共检查，不再为它重跑真实模型。

主Agent与Luna各自复核最终报告：分路数据、未知主位和训练目标保持条件选项，辅助单局不当作能力差，混合位置指标不直接论证位置短板；引用和伤害占比与输入一致。但OP.GG在第7节仍只作为边界声明，没有任何具体快照数值用于第5/6节建议。因此自动95分不能代替四来源实际建议消费，黄金人工验收仍不通过；Training持久化/live Workbench也未验证。独立人工记录保存在golden_manual_reviews并绑定报告SHA，原运行/报告/评估不改写。用户可审阅副本导出至outputs/riftcoach-review-8c02112.md。

新增实际Provider协议3+Coach5=8次，本接续累计35次（此前27次）；历史两次超时用量仍未知，累计完整成本不作宣称。下一步先补“来源存在”到“来源支持具体建议”的可检查契约，允许部分provenance下合规使用当前Meta，不能迫使无依据的版本/段位比较或为了凑四源编造建议。已授权Luna配合继续用于有独立输入输出的任务，由主Agent最终核验；本人Training仍需本人档案与目标答复，8E保持in_progress。


### 具体来源建议的可信策略（Coach1.3.5，2026-09-10）

上轮代理TLS小修复9b10c12096f3fb75d6fd00d0dead3476a431380f / Actions34460091480三job成功。95分报告未使用OP.GG具体事实仍为本轮问题；没有改写旧报告或重评分。Luna独立审计边界与五类反例，主Agent决定并实现最小可信策略接线。

设计：新SOURCE_USE_POLICY作为INTERNAL_POLICY进入初稿，并放在评分/纠正/修订/复评数据块之外；与原POSITION_POLICY、generation_facts和deterministic_source_facts共同送达。只在独立ADVICE_COACH_CONTRACT1.3.5、Skill0.5.5、Program2.3.5、flash_v2_golden_advice启用。新合同摘要ad83fbff7dd2b49e253d8698a649c632b50bd7062cacc54277eb7c5e7dd26e0d绑定策略；旧1.3.4摘要2f498babc867a984db82f4777064b2de82c42b40566aa35fea3b593b2c691c47、所有旧资产及默认1.2.0不变。黄金入口显式使用新合同，历史重放默认仍1.3.2；不是更改生产模型或另建评测框架。

验收口径：有可用且适配位置/英雄/训练目标的OP.GG事实时，正文建议至少包含一条具体tier/rank/rate事实、来源/位置/检索时间/当前快照适用范围、条件式行动，以及事实如何支持这项候选选择或待验证问题。未知意愿保持条件选项，已指定目标不能为了消费来源而改位。评分的passed_checks需指出实际事实与报告行动/范围原文；只列来源或免责声明必须给出具体遗漏问题，通过既有一次修订修复。没有可用facts或目标不匹配时保留具体缺口并不生成该建议；诚实缺口可以是安全报告，不能冒充四来源消费成功。Riot描述所选比赛；Data Dragon解释历史版本名称；官方身份/日期仅版本对齐，无正文不得声称加强削弱。没有新增检索或API请求。

人工语义反例（待真实观察核验，不当作离线模型已通过）：①中路Meta用于辅助建议；②用当前外部胜率解释历史输赢或暗示同段位同版本；③facts为空/过期/英雄缺失仍强推；④按混合分路Meta推断玩家适合位置；⑤未知训练意愿因中路最多而排定中路计划。以上均不合格。只有来源声明的旧95分报告按新口径属于消费遗漏。没有确定性自然语言判定器：策略要求模型做语义审查，主Agent继续人工核验；不能用字符串标记或模拟pass代替建议正确性。

代码流：coach_contract.source_use_policy→CoachContextBuilder的可信addendum；RuntimeCompositionRoot把同策略注入GroundedChatEvaluationAdapter/GroundedCoachReviser，纠正沿原prompt复用。Program资产经实际SkillCatalog和组件指纹重建、resolver验证。测试捕获实际9个请求，核对初稿可信section、后5个请求策略在数据块前、旧版无新增策略；生成事实与初稿逐字段一致测试新增1.3.5。无适用/过期/错位事实过滤复用已有source_context测试，不改原白名单。

验证118 passed。保存8c02112的真实Summary/Bundle仅离线预算重放：9模拟请求、8成功工具、一次修订，低分仍evaluation_failed；初始14966/最终26774（限28000），输入上界30856/40894/47336/53778/49536/49768/28344/49536/49768，全部低于64000，加输出预约73728低于649728；所有请求含原来源身份和位置策略。原85分/9调用/8工具/一次修订/90秒单次/120秒Agent/480秒总执行限制均不变。

本批真实调用新增0，累计仍35次Provider尝试，旧超时用量未知。下一步本提交公共检查与新鲜协议后的一次有界语义观察；OP.GG到建议是否成立仍待实际报告，Training需要本人档案与目标，live Workbench尚未验证，8E不前移。


### c4a169b真实响应头等待超时（2026-09-10）

实现c4a169b5d1663677b796ef16711beff501d3f187 / Actions34460944693三job成功：pytest2969 passed、152 skipped、127 subtests passed，PostgreSQL208 passed。之后新鲜协议3调用、输入1009/输出115 tokens通过。运行golden_20260910_saved_c4a169b，合同1.3.5，仍复用原五局；Riot0、静态1、官方1、OP.GG两位置各一次工具/初始化/目录。Bundle 00a7059dd79751079a6a34ba4676cb24975ca87c1ccd48b2639f0bb198099b17。

Coach2次尝试、1次响应、4检索全部成功。第一请求21.437秒返回tool_calls，已知输入7114/输出584 tokens；第二请求90.016秒timeout，用量未知。Runtime111.516秒，rejected/draft_preparation_failed，无初稿、评分或修订。不能称1.3.5语义策略失效或通过；尚未进入能观察效果的阶段。本轮协议3+Coach2共5次，本接续累计40次Provider尝试；累计三次超时请求用量未知，不宣称完整累计成本。

新增直接阶段证据：http-002.json在elapsed16ms完成send_request_body并开始receive_response_headers，elapsed90016ms触发receive_response_headers.failed，等待90000ms；没有receive_response_body阶段。http-001.json实际记录proxy.start_tls.started/complete（1875→1922ms），TCP1875ms前完成且第一响应成功；TLS事件名修复已在真实环境生效。第二请求没有新建连接/TLS事件，符合复用连接路径，缺失阶段不能补写0ms。此次只能定位客户端等待响应头超时，不能从该记录区分代理、网络与上游排队/推理/生成，亦不回填此前两次无阶段记录的超时根因。

原预约、诊断、Trace与失败回执保留；独立golden_manual_reviews绑定Trace摘要并记录未进入评分。没有追加重试、增加90/120/480秒限制、改模型默认或重跑旧四场景。下一步先审查已有候选stream adapter的首个事件/文本/完整响应诊断能力和有界使用条件，以决定是否能取得更有区分力的证据；不能把流式可用直接当作生产采用或延迟已修复。OP.GG具体建议效果仍待观察，Training与live Workbench仍未验收，8E不前移。


### 现有流式能力审查与单请求诊断规范（2026-09-10）

结论：可以复用底层ZhipuStreamAdapter与父子进程隔离模式；不能直接执行旧流式探针，也不能把流式接入当前Coach产品Runtime。当前记录只证明等待响应头90秒超时；首个SSE事件、首正文和终态分别记录，才能判断是否先有输出而整体生成较慢，但仍不能辨别供应商内部排队/推理原因。

来源核查：glm53_flash_stream_visible_completion_probe固定low/2048、45秒、首正文即关闭；terminal_completion_probe同样low/2048且固定旧输入。candidate_stream_contract.CandidateZhipuStreamTransport严格绑定独立fresh-recovery candidate identity（90秒Agent/120秒transport等），不是当前Coach1.3.5。直接换入会混淆模型策略和历史实验身份。底层provider-local stream_adapter.stream_session可显式使用当前high候选Provider，include_usage_tail仅诊断选项。

生命周期证据复核：ADR-0083/RQ-213为not_pending，未测到挂起读取；RQ-215见2026-09-03-glm53-candidate-transport-gate-real-observation.md，受控首帧闸门出现client_wakeup_close_race；RQ-217见同名-rq217.md，经reader-owned修复后受控闸门得到client_wakeup_clean。主Agent已直接读原记录。RQ-217是有价值的客户端证据，不能省略或否定；但不等于真实自然阻塞SDK读取一定能被close唤醒，所以独立诊断仍需父进程硬截止兜底。

零网络可行性验证：使用现有tests/test_zhipu_stream_adapter.py的ClosableStream/FakeClient，创建high候选Provider与max_tokens8192/timeout90请求，通过stream_session(include_usage_tail=True)消费reasoning/content/stop/usage四个模拟事件。检查真实生成的SDK payload仍high/8192/90、stream=true、恰好1次create、资源已close、产品capabilities.streaming仍false。未打印任何正文；这是参数/事件兼容性验证，不是真实延迟或质量证据。当前没有新代码实现或测试套件修改。

最小诊断规范（待离线实现，尚不可真实执行）：

1. 使用新独立实验ID，绑定当前Coach1.3.5摘要与实现SHA。失败c4a169b只留Summary/确定性报告/Trace，没有完整第二次模型消息和检索回包，不能重建为同一请求。可从已验签的保存报告输入及检索证据构造一个新的报告形状请求，记录新的完整请求摘要、输入来源摘要和构造方式；明确newly_constructed_diagnostic，不叫精确失败重放。历史快照只作为诊断材料，绝不重新宣称为当前Meta建议。
2. 默认零网络；单次显式执行只允许1个模型请求、0次Riot/静态/官方/OP.GG请求、0次工具执行，不进入Agent/RAG重查/评分/修订/发布流程。固定high、输出8192、输入不超64000、合计上界72192、SDK额外重试0，不启recovery。若输入不完整或不能验签，调用前拒绝。
3. 请求90秒上界不增加；父进程从子进程启动开始计总时限，子进程打开流/读取/收尾都用剩余时间，父进程到期终止并回收子进程，不能依赖一个可能阻塞的close实现总时限。结束后不得自动再发请求；终止本地进程不代表上游已停止或计费已取消。
4. 复用HTTP阶段白名单，加单调first_event_ms、first_reasoning_ms、first_visible_content_ms、terminal_ms、eof_ms、close_ms、total_ms；首事件不等于首正文，非空reasoning不等于可用报告。保留安全事件计数/字符数/finish枚举/实际Usage和资源状态，缺失为null/unknown，不存正文、reasoning、工具参数、headers、request ID或异常文本。调用前持久预约；父进程负责create-only最终回执，即使子进程被杀仍记录已尝试和未知用量。
5. stop、EOF、Usage与成功close分别判断；只有首正文不算完整生成，finish=length/tool_calls或缺Usage不算完整报告质量通过。正常流结束也仅是延迟观察，不能发布为黄金报告或采用产品streaming。
6. 离线必须验证：开启前阻塞、首事件前阻塞、已有reasoning但无正文、已有正文无终态、终态无Usage、关闭阻塞、子进程异常/超限、敏感哨兵过滤，以及输入身份拒绝前零调用。以假SDK和受控子进程验证，不用真实睡眠或重复模型请求模拟失败。

本轮主Agent独立复核Luna结果；无新增真实Provider调用，累计仍40次，历史三次超时用量未知。48de155文档提交Actions34462088969已成功；本审查未变更产品默认或旧合同。下一步仅实现上述独立诊断的离线入口和比例测试；公共检查后才考虑一次真实诊断。OP.GG具体建议、Training和live Workbench仍未完成，8E不前移。


### 单请求诊断实现与连续执行（2026-09-10）

单请求流式诊断已实现：新身份golden-stream-timing-v1绑定Coach1.3.5与保存输入摘要，默认零网络；high/8192、输入上界31264、实际仅1请求、90秒父进程硬截止、零来源获取/工具/评分。父最终回执保留子最后快照，不能把未知阶段补成已完成；关闭只投影简化状态。Luna独立复核已完成，主Agent验证21项新增故障/隐私/SDK参数测试通过；相邻回归和公共检查接续进行。用户最新授权连续完成实现、验证及有界真实推进，取代逐小步等待授权；下一步本实现同SHA公共CI及新鲜协议后直接做一次真实诊断，不连续重试。真实新增0、累计40，OP.GG建议效果、本人Training/live Workbench仍未验收，8E保持in_progress。

运行入口：python -B -m scripts.diagnose_coach_golden_stream --config <local-input-config> 默认零网络；执行另需 --execute --run-id <new-id> --ci-run <exact-sha-run> --protocol-report <fresh-proof>。配置仅inputs映射：saved_run_id、summary_sha、manifest_sha、riot_id、region；输入路径固定data/runs/golden_slice。父子两次核验输入、HEAD及公共证据；子进程读取凭据后仅使用标准GLM5.3Flash端点、SDK retries=0。回执位于data/runs/golden_stream_diagnostics/<new-id>，reservation/provider-001/result均不可覆盖。最后progress是实际观测快照，parent_deadline或child_unreaped是父层结果，不能外推上游取消/计费已结束。包含Usage尾帧参数的新请求并非失败请求精确重放，历史OP.GG不重新宣称新鲜。

提交前验证：新增21项、聚焦与相邻合计72项通过；实际保存输入默认预检零网络，输入保守上界31264，request SHA 9b62bc42b4736790356ec0f1a887987c81a6198d6d1100b13dbe3a4a9adf9254。语法、治理及diff检查通过。


### 869e4b3单请求流式真实观察与裁决（2026-09-10）

独立流式诊断完成真实观察。实现869e4b38c48b1a8f5c18c9fc2532c4042165528e / Actions34467329663三job同SHA成功（pytest2990 passed、152 skipped、127 subtests；PostgreSQL208）。新鲜协议3请求通过（输入1007/输出105）；诊断stream_20260910_869e4b3恰好1请求/1HTTP，首事件及reasoning5453ms、首正文20093ms、stop43312ms、normalized EOF与close43328ms、父收口43515ms，输入8328/输出3850，complete且closeclosed。仅证明这次新请求可完整流式返回，不是旧请求精确重放或黄金质量通过。本轮新增4次、接续累计44次Provider尝试，历史三次超时用量仍未知。下一步在显式候选范围设计完整流响应组装及绝对截止接线，先离线验证工具往返/终态/Usage/关闭，不盲目重跑报告。OP.GG具体建议、本人Training/live Workbench仍未验收，8E保持in_progress。

回执SHA-256=c0783bb1ffc5f71f4a998eac7c33cf6ee0fa09dd8dec215d9a7a726d5f0d3462；原reservation/protocol/provider-001/progress/result保留不回填。新请求摘要9b62bc42b4736790356ec0f1a887987c81a6198d6d1100b13dbe3a4a9adf9254；3823个规范化事件、正文3679字符、reasoning4020字符，均未保存正文。总新增用量为输入9335/输出3955 tokens，仅为本批完整观测，不代表包含历史未知超时的完整累计成本。

HTTP末事件为http11.receive_response_body.failed，error=null且stop/normalized EOF/Usage/close均成立。主Agent及Luna只读核查本地OpenAI Stream.__stream__遇到[DONE]跳出并在finally关闭response；httpcore Trace.__exit__以异常退栈会发failed，包含生成器清理路径。主Agent用真实OpenAI/httpx/httpcore与MockBackend假网络、固定SSE正文/Usage/[DONE]离线复现state=complete与同一body.failed末事件共存，network_used=false。该复现证明字段不能单独判响应失败，不证明真实事件的确切异常类型；未读取或保存trace info。eof_ms是规范化SDK迭代结束，不是独立网络EOF证明。

裁决：此次提供流式high报告形状请求可完整收口的正面时序证据；不同请求构造与运行时刻禁止推导相对旧c4a169b的因果加速比例。显式Coach仍同步，不能直接切生产streaming或放宽90秒。下一批直接做候选完整流组装/绝对截止接线设计与离线兼容验证，保留工具往返、完整Usage、质量门和部分输出不发布的要求；真实观察须在后续新实现独立公共检查后有界进行，无需为常规步骤再次询问。


### 完整候选进程流式桥（2026-09-10）

显式候选进程流式桥golden-process-stream-v1已离线实现并接入黄金入口可选参数；Coach1.3.5语义与资源墙不变。复用中立组装器、每请求子进程/私有JSON管道、完整终态/Usage/EOF/close才交付；9调用上限且一次失败后禁止再发。结构化规则mappingproxy序列化缺陷与Coach身份属性接线缺口已修复；完整9调用/8工具/一次修订离线回放仍按低质量拒绝。下一步本实现同SHA公共检查后新鲜3调用协议及一次保存五局完整流式Coach观察，不连续重试。当前真实新增0、累计44，Training/live Workbench待验收，8E保持in_progress。

设计与边界见ADR-0100。入口添加--provider-transport golden-process-stream-v1且必须--with-provider；未指定时旧默认及旧回执序列化不变，新identity由preflight摘要及receipt显式字段绑定，Coach合同摘要不变。Provider API仍同步chat；stdio仅进程间私有内存，未把模型正文/reasoning/工具参数写入临时文件或诊断，已有产品最终报告输出仍按原规则保存。每请求进度保留HTTP安全事件名及首事件/正文/终态/Usage/关闭，父回执保存真实墙钟与终态。进程创建、IPC或回收失败均保留安全回执，不能交付partial。

比例验证覆盖真实本地子进程+假SDK、工具片段与reasoning回放、结构化评分规则、缺Usage/截断/超限/关闭失败、partial pipe/崩溃/截止、失败后无第二次请求及默认隔离。完整9调用回放覆盖实际Coach/RAG/评测/一次修订，脚本低质量仍evaluation_failed且无报告；该验证不代表模型质量通过。

提交前比例回归：126 passed；新增进程流式桥测试20项，语法、治理、diff检查通过。当前无新增真实调用。
