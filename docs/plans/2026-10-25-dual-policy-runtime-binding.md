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
