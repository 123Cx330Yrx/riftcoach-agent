# 双职责必要修订的同版本评估与Runtime绑定

## 工作卡

- 目标：将已实测的facts及completion必要修订政策绑定到一个动态候选，原15固定报告评估与自然任务Runtime消费同一模块，避免诊断版本与实际运行版本分离。
- 起点：303c21b4诊断闭环已封存成功，但合同1.6.5包含固定对照及继承facts例外，只适用于断点诊断；Runtime仅支持旧Sol与facts政策候选，原15库存仍绑定GLM合同。
- 选择：新增通用双政策合同，复用原session/owned worker/共享预算/唯一逐字应用/双fresh；不把专用诊断合同注册成通用产品，不另造执行引擎。政策逐字复用，不增加调用、字段或source_ids义务。
- 数据流：产品Application→Runtime→同一候选router→Flash生成与Sol双审→唯一实际补丁应用→同稿双fresh；原15离线库存通过同一make_request和manifest生成，标签留在评估元数据。
- 边界：本包仅离线接线，不发送、不读Key、不改旧run/冻结树、不授产品或15项资格。沿用自然逻辑6次、最多10实际请求/739840tokens/3600活动秒，4次手动补测；产品5调用差异未解除。
- 验收：政策与已接受诊断请求的业务输入一致；旧新receiver隔离；实际owned worker+Runtime修订/初审直过/复审拒绝；524和格式故障仅暂停当前项、手动同项恢复且旧费用/成功项保持；原15输入/标签/完整来源不变，30initial库存、fresh待实际稿；真实用户入口首发前捕获0网络/0Key。
- 失败决策：接线或预算/来源错误本地修复；模拟通过不推导模型质量，正式评估须另列明确执行范围并获费用授权。真语义缺陷不能借格式补测掩盖。
- 状态：通用合同1.6.6及离线绑定完成。23项新增检查通过（188.38秒），库存快照另核一致；8配置实际启动通过。87项旧路径回归通过（433.96秒），13个改动Python文件编译、治理及diff检查通过。下一动作是正式同版本15的逐项执行及独立审查方案，不再购买熟悉报告。

## 限制及后续依赖

15项是原固定报告正负例，5accept/10reject；按标签预期为30初审、最多20fresh，共50职责槽，和自然6调用任务不同。该库存不是执行器、结果或holdout证明。产品注册/真实DB/API/UI消费、自然Coach/Training、四块/journal、前端头像与审美、Memory、身份运维、两树整合、独立评估与学习保持原依赖，阶段8E不变。

手动暂停/恢复依赖CandidateSession及其真实native review gate；未提供session的依赖注入入口用于本地成功/失败检查，不是新的可恢复付费启动器。旧冻结303c21b4保持clean，outer seal 1c54efbd未变。政策源文件与冻结版逐字相同；新增上下文/传输标识显式隔离旧请求，旧成功不能迁为新版本资格。

证据：data/evaluation/results/sol_review_runtime_binding_20261025.json；sol_review_qualification_inventory_20261025.json；natural_duty_qualification_inventory_dual_binding_20261025.json。历史库存保留，只有新的legacy当前库存及当前manifest记录共享源码变化。

## 接续工作卡：原15逐项执行

- 目标：为原15固定报告提供真实可恢复的逐项入口，使用1.6.6的完整双初审、Host兼容/编辑核验、唯一应用及同稿双fresh；不重新生成报告，不拼接旧版本结果。
- 路径：复用CandidateSession、SessionBudget、SessionWorkflow、SessionReviewGate和owned worker；每例独立session及原stdout根，前例严格只读重放并接受后才能进入下一例，outer seal只创建一次。新模块只负责固定输入和顺序编排，不新建审查引擎。
- 验收：原15逐字构造、标签不入模型或独立任务；实际worker与原生事件适配器的模拟整链；正常暂停/单项手动524及格式恢复、硬错误/错标签阻止后项、原件变动/未决intent拒发、只读回放/唯一封存；缺授权在Key/创建execution前拒绝。
- 预算：沿用同候选自然任务包络，不冒充自然任务；固定报告每例最多4逻辑审查+4手动补测，15例最多120实际请求/9646080 tokens；按原标签顺利完成为50逻辑审查，不把50当结构硬上限。最坏未缓存估价8.7552元，非账单限额。用户本轮明确确认该范围，新grant已激活；尚未输入Key或发请求。
- 失败分支：524/已知格式错误仅暂停同例同项，手动补测保留所有用量及成功项；真实语义拒绝、输入/身份/补丁完整性错误保留最早停止证据，不靠重试越过。预算耗尽暂停等待明确扩展，不自动循环。
- 当前：入口离线整链10项通过（341.42秒）、27项相关回归通过（254.25秒），编译/治理/diff通过。3b290d9d公共CI40158661587及执行HEAD34abe04e的CI40188299016均全绿；最终clean执行目录、真实作者行政预检和最终PowerShell启动核验完成。Windows内核锁读取及失败库存分隔符差异已修，合成跨case事件ID重复已修，保留失败记录。旧封存保持，不新建Agent、不读取Key或发送模型请求。

运行说明：docs/runbooks/sol-original15-session.md。准备完成必须包含最终clean执行树、同HEAD公共CI、实际cwd/Python启动以及真实独立作者行政预检；测试中的合成事件不代替该预检。

现场准备：34abe04e已冻结于D:/riftcoach-original15-execution-20261025，clean；Operator/control为
outputs/riftcoach-sol-original15-20261025前缀，plan ef53345f。既有真实独立作者/check-answer/native
final与唯一导入及只读核验通过，最初guard eca79f71、最新checkpoint6764fa0a均留原stdout。
未授权正常入口在Key和cases创建前拒发，0新请求。CI40188299016已全绿，最终PowerShell
CheckOnly退出0，未授权正常入口退出1。外层PowerShell未传播Python退出码已修并复核，
Operator/作者SHA不变；冻结源码未改。Control/preparation-complete-v2.json SHA acc65e7b29ef27643ff2fabcec3b703d9af21543f5f21546fab1c21c6a5e2e03。
本轮用户明确确认具体提案，已create-only写入新grant 87a471553eb541616ac58df79e9124e219f33c579eb49695ec1b1782463d31cc，绑定原plan且只激活settings授权SHA。
有效期UTC2026-10-25T15:46:27.795344Z至2026-10-26T15:46:27.795344Z；不自动延期。
实际PowerShell/有效grant/CI/真实native复核通过，0Key/0请求，cases未建；下一动作是用户运行既有入口隐藏输入企业Key。
激活证据Control/authorization-activation.json、activation-check.json；原准备快照保留，不将行政预检算业务质量。旧freeze/seal未变。

## 当前实测前沿

## 2026-10-26 第二报告修订及同稿双fresh完成，2/15（当前）

最后completion-fresh成功1HTTP200，19.875秒，输入11991/输出152，共12143known tokens；pass/100，issues/issue_resolutions/advisories均为空。
主审和既有独立作者重新按完整实际稿、完整来源、知识、用户原话及completion政策核验任务与资料消费，均接受；唯一NEW_TASK、run外作者与真实native逐字匹配，正常submit。
观摩身份及条件练习保持，K1—K5实际连到具体回看/记录行动，未因缺OP.GG快照而虚构消费义务；稿SHA cabe09860894fac8814dfb206ac12bf35a3dcd756ba7a2122e3ae058932a6586与唯一application和facts-fresh相同。
程序正常结束claim-scope:4：candidate_repaired_pass_unqualified，matched=true。本例完成双初审、compatibility/edit双审、唯一逐字补丁实际应用和同稿双fresh；说明该固定报告修订成功，不等于15项或产品合格。
只读replay核首例和本例全部真实native（本例6份）、原件/作者SHA、完整响应观测、HTTP和费用通过，Operator/作者库存前后不变；facts-initial原派发事故及显式固定恢复、加密输入等价性未知均保留。
本例4HTTP/70729known，23operations已消费、closed=true、无unresolved；累计6HTTP/110154known，0unknown/0retry/0receiptless/0未发，完成2/15。整批未关闭、未seal，下一例尚未创建/发送。
0022—0024原stdout及最早exit SHA保持；最初guard af6f69a2不变，最新原checkpoint c9cd71c712a808851a8d69143fb1c74c0621d1a8b78a1234e97a0856cfb7b72b；冻结34abe04e clean及CI40188299016不变。
**下一动作：** 用户运行同一Control/start-authorized.ps1隐藏输入企业Key，进入第三份claim-scope:3的facts-initial；不加ManualRetry，不重买已完成两例。
原授权北京时间2026-10-26 23:46:27截止不延展，automation现场核PAUSED。原15是熟悉固定来源，不能称新holdout或产品准入；原后续依赖保持。
证据：Control/claim-scope-4-completed-accepted.json（SHA d5c4d663e753f75f5b67ab063c629f1c540a4787b7a26ad54116f8f885e29901）；Control/claim-scope-4-completed-replay.json（SHA d332fdddbde5017ec5f31e0af791f68490c6719287df102399ab480d66a892a8）。

## 2026-10-26 第二报告facts-fresh双审通过，待最后completion-fresh（此前检查点）

本次facts-fresh成功1HTTP200，36.86秒，输入17776/输出867，共18643known tokens；pass/100，issues及issue_resolutions为空，仅advisories block4/6。
主审和既有独立作者重新实读实际25段新稿、完整来源/知识/用户任务/事实政策及真实响应，均接受；唯一NEW_TASK、真实native与run外作者逐字一致并正常submit。
重算确认中单→全五局补刀8.9075→7.394、经济469.0525→435.76、伤害952.1375→869.504下降，视野33.75→45及早死1.5→2.6升高；实际补丁已修正方向。
全样本早死2.5/2.67、局部补刀观察、伤害差归因、timeline与K1—K5建议及观摩身份均符合来源；可选措辞标记不升级为事实错误。
唯一application及实际稿cabe09860894fac8814dfb206ac12bf35a3dcd756ba7a2122e3ae058932a6586保持；最后completion-fresh离线重建与该实际稿及完整来源一致，尚未发送。
累计5HTTP/98011known，0unknown/0retry/0receiptless/0未发；第二例3HTTP/58586known，18operations、无unresolved、未关闭；完成仍1/15，整批未seal。
首例及当前五个真实native（facts-initial显式固定恢复保留）、原transport/完整响应观测/费用严格只读核验通过，Operator与作者库存不变，冻结34abe04e clean。
0019—0021原stdout及最早exit SHA留存，最初guard af6f69a2不变，最新原checkpoint220e94895918d3b4d36e7307ef8e5ecce9b359c3abff39a3ac2a6df6f248441c。
**下一动作：** 用户运行原Control/start-authorized.ps1隐藏输入企业Key，只续本例最后completion-fresh；不加ManualRetry，不重发已接受项或再次应用。
原授权北京时间2026-10-26 23:46:27截止不延展，CI40188299016不变，automation PAUSED；尚未完成同稿双fresh，不称本例修订成功或15项/产品合格。
证据：Control/claim-scope-4-facts-fresh-accepted.json（SHA 74eba10e50dcb694f1e658a1247379333bfd287a02dc28a2a05b318859ee7f2d）；Control/claim-scope-4-frontier-0021.json。

## 2026-10-26 第二报告双初审及唯一应用完成，待facts-fresh（此前检查点）

本次completion-initial成功1HTTP200，输入18541/输出263，共18804known tokens，pass/100且所有意见数组为空。
主审和既有独立作者实读完整25段、全部来源/知识/用户任务/政策/实际响应后接受；真实native与作者逐字匹配，
单次NEW_TASK正常导入。观摩身份及条件练习未被误读为本人参赛，K1—K5实际消费，缺OP.GG不补造外部要求。
compatibility随后双审clear；edit完整新稿四项ReportAssessment双审均true，原生原件逐字核验及submit通过。
程序已唯一应用block_4一处原样补丁，纠正视野/早死方向，其他正文逐字保留；实际稿SHA cabe09860894fac8814dfb206ac12bf35a3dcd756ba7a2122e3ae058932a6586。
两个fresh请求已离线重建并核与实际同一新稿绑定，尚未发送。application原静态flags保留，真实Host接受另留原件。
累计4HTTP/79368known、0unknown/0retry/0receiptless/0未发，仍完成1/15；第二例14operations、无unresolved、未关闭/未seal。
首例严格只读replay、当前四个真实native（含显式恢复的facts）、原收据/观测/用量和原文件/作者SHA回查通过，库存不变。
最初guard af6f69a2保持，0012—0018原stdout及最早exit留根，最新checkpoint0063bef1；冻结34abe04e clean及CI40188299016不变。
**下一动作：** 用户运行原Control/start-authorized.ps1隐藏输入企业Key，只续facts-fresh；不加ManualRetry、不重发初审/应用。
原授权北京时间2026-10-26 23:46:27截止不延展，automation PAUSED。实际同稿双fresh尚未完成，不能称本例修订成功或15项/产品合格。
证据：Control/claim-scope-4-initials-and-application-accepted.json（SHA ac847335a0ae200f69465b80ed758a8f186fb7575a5c351b03fcb6c0ec9905a3）；Control/claim-scope-4-frontier-0018.json。

## 2026-10-26 第二报告facts交接恢复（此前检查点）

用户明确要求“处理”后，已通过固定事件/SHA的外部Host适配器导入原facts意见，不重派发、不重买。
原reader仍复现重复NEW_TASK拒绝；四条派发、唯一真实final/membership、作者原件、精确checkpoint
及material均重新核验。加密输入等价性仍未验证，不能声称原校验通过；原失败原件保留。
20项恢复反例/正例及102项原native/checkpoint/独立合同回归通过。实际submit accepted，
随后原入口HostOnly消费接受结果，停在claim-scope:4/completion-initial发送边界，0新Provider/0Key。
只读重放首例及当前native、原transport/观测/费用通过；原文件和作者全部SHA保持，库存前后不变。
累计3HTTP/60564known、0unknown/0retry/0receiptless/0未发，仍完成1/15。当前4operations、无unresolved、
closed=false；未实际应用补丁、未发送completion、整批未关闭/未seal。最初guard af6f69a2保持，
最新checkpoint917a7ade来自0011原stdout/最早exit；0010真实导入stdout及exit也保留。
冻结HEAD34abe04e clean、CI40188299016及原plan/grant未改；automation现场核PAUSED。
**下一动作：** 用户运行同一Control/start-authorized.ps1，隐藏输入企业Key，只续同稿completion-initial；
不加ManualRetry。授权北京时间2026-10-26 23:46:27截止不延展。后续submit/run/replay/seal均经
外部Control/operator.py固定恢复适配器，其他事件仍走原reader。未授产品或15项资格。
证据：Control/claim-scope-4-recovery-accepted.json（SHA cb0c39fadec218da8bdbf472f07c7e078f3631df7ebba5f6b975b86e2b629205）；
manifest fa14c730、module97805fa3；data/evaluation/results/sol_original15_live_20261025.json。

## 2026-10-26 第二报告native派发冲突（恢复前原记录）

claim-scope:4/facts-initial新增1HTTP200/34.219秒/21139known（输入20114、输出1025），
needs_revision/92、唯一issue及block_4逐字补丁。主审和独立作者均全文核验并接受：原稿明确的
“每一个指标均值都被辅助局拉低”与视野33.75→45、早死1.5→2.6冲突；补刀8.9075→7.394、
经济469.0525→435.76、伤害952.1375→869.504确实下降。补丁仅纠正该句，保留正确内容及观摩身份。
模型请求、结构、身份echo high、完整响应观测、收据及已知用量均通过；这不是模型语义失败。

实际导入未执行：主线程误用collaboration.followup_task恢复同任务，即使正文写MESSAGE，工具
仍实际产生第二条NEW_TASK。真实同turn有两条NEW_TASK和两条MESSAGE；唯一native final与作者原件
逐字一致（SHA12a652bc），但冻结reader按既有规则拒绝codex_review_host_rollout_dispatch_or_final_ambiguous。
最早偏离是主线程恢复工具用法，不是API超时或模型质量；此前将interrupted快照当作需再次followup
的信号也不充分。不能删/裁剪原dispatch、覆盖final、伪称native导入成功或偷偷改冻结reader。

本批累计3HTTP/60564known、0unknown/0retry/0receiptless/0未发；已完成首份1/15保持。
第二例closed=false、3operations、unresolved为空，原guard af6f69a2/checkpoint7b26c37a来自0009原stdout/最早exit；
严格只读库存前后不变，无submission、无实际补丁应用、无completion发送。整批保持未关闭/未seal。
**下一动作：** 准备显式零付费native交接恢复，保留两条真实派发及原作者/final、原收据和全部费用；
现冻结协议无法导入，不再派发/重买或运行下一项。独立作者不重新写final；后续新任务首次用followup_task，
同任务仅send_message且先核协作状态，不能把正文MESSAGE当作工具层MESSAGE。授权不延期，automation PAUSED。
证据：Control/claim-scope-4-native-dispatch-failure.json；data/evaluation/results/sol_original15_live_20261025.json。

以下为此前检查点。

## 2026-10-26 原15首份报告双初审完成，1/15（此前检查点）

claim-scope:1的completion-initial新增1HTTP/14.641秒/18771已知tokens（输入18524、输出247），
pass/100、issues/resolutions/advisories/repairs均为空。主审和既有独立作者实读完整25段、全部来源、
知识、用户请求、政策和实际意见后均接受，真实native与run外作者逐字一致并唯一导入。
已核K1—K5在正文的实际使用、缺失OP.GG资料的条件义务，以及ShowMaker观摩/阅读者身份；
没有补造训练位置、个人参赛、阈值或篇幅要求。双initial pass后程序正常结束首例，
outcome candidate_initial_pass_unqualified与原预期一致；无编辑/应用/fresh，不称修订成功。

本批累计2HTTP/39425known/0unknown/0retry/0receiptless/0未发，完成1/15。
严格只读replay实核两个真实native、作者、原收据、完整响应观测及费用，Operator/作者库存不变。
原stdout guard faa6d5a1保持，最新checkpoint59b83542；0006—0008 stdout与最早exit SHA已留证。
仅首例关闭，整批未seal；冻结HEAD34abe04e、CI40188299016及原plan/授权不变。
**下一动作：** 用户运行同一control/start-authorized.ps1，隐藏输入企业Key，继续下一报告
claim-scope:4的facts-initial；不加ManualRetry、不重发首例。授权北京时间2026-10-26 23:46:27
截止不延展；automation PAUSED。尚未完成15项或产品资格，后续产品依赖保持。
证据：data/evaluation/results/sol_original15_live_20261025.json；Control/claim-scope-1-completed-replay.json
（SHA a09715f772888ce24bc6d93941a90b07b736ea40fcd057888288d73330a55854）。

以下为此前检查点，不是当前下一动作。

### 2026-10-25 原15首例facts-initial已双审接受

首例claim-scope:1的facts-initial新增1HTTP/33.141秒/20654已知tokens（输入20097、输出557），
模型pass/100、issues/resolutions/repairs为空，仅advisories4/6。主审和既有独立作者实读完整25段、
全部来源/知识/用户请求/政策/实际意见后均接受；真实native final与run外作者逐字一致并唯一导入。
核对中单均值、全样本早死2.5/2.67、混合位置补刀与伤害差异、局部稳定及观摩身份；
不补造全称、不把可选措辞升级为错误。此次没有编辑，不能声称修订成功或整例已完成。

原stdout guard faa6d5a1、最新checkpoint f670d25e及0003—0005 stdout/exit SHA均保留。
只读回查真实native/作者/原收据/完整响应观测及已知用量通过，库存不变；1实际请求、
0unknown/0retry/0receiptless/0未发，4operations已消费，无unresolved，closed=false。
冻结执行HEAD34abe04e与CI40188299016、原plan/授权不变，Key未保存到文件。
**下一动作：** 用户再次运行同一control/start-authorized.ps1，隐藏输入企业Key，只续同稿
completion-initial；不加ManualRetry，不重发已接受facts。返回后逐项全文双审，再继续该例。
本批授权北京时间2026-10-26 23:46:27截止保持，automation PAUSED；未完成首例、15项或产品资格。
证据：data/evaluation/results/sol_original15_live_20261025.json；Control/claim-scope-1-facts-initial-accepted.json。
