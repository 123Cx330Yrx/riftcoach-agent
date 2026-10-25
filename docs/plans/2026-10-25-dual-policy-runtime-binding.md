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
- 预算：沿用同候选自然任务包络，不冒充自然任务；固定报告每例最多4逻辑审查+4手动补测，15例最多120实际请求/9646080 tokens；按原标签顺利完成为50逻辑审查，不把50当结构硬上限。最坏未缓存估价8.7552元，非账单限额。当前只准备，未授费用或启动权限。
- 失败分支：524/已知格式错误仅暂停同例同项，手动补测保留所有用量及成功项；真实语义拒绝、输入/身份/补丁完整性错误保留最早停止证据，不靠重试越过。预算耗尽暂停等待明确扩展，不自动循环。
- 当前：入口离线整链10项通过（341.42秒）、27项相关回归通过（254.25秒），编译/治理/diff通过。3b290d9d公共CI40158661587及执行HEAD34abe04e的CI40188299016均全绿；最终clean执行目录、真实作者行政预检和最终PowerShell启动核验完成。Windows内核锁读取及失败库存分隔符差异已修，合成跨case事件ID重复已修，保留失败记录。旧封存保持，不新建Agent、不读取Key或发送模型请求。

运行说明：docs/runbooks/sol-original15-session.md。准备完成必须包含最终clean执行树、同HEAD公共CI、实际cwd/Python启动以及真实独立作者行政预检；测试中的合成事件不代替该预检。

现场准备：34abe04e已冻结于D:/riftcoach-original15-execution-20261025，clean；Operator/control为
outputs/riftcoach-sol-original15-20261025前缀，plan ef53345f。既有真实独立作者/check-answer/native
final与唯一导入及只读核验通过，最初guard eca79f71、最新checkpoint6764fa0a均留原stdout。
未授权正常入口在Key和cases创建前拒发，0新请求。CI40188299016已全绿，最终PowerShell
CheckOnly退出0，未授权正常入口退出1。外层PowerShell未传播Python退出码已修并复核，
Operator/作者SHA不变；冻结源码未改。Control/preparation-complete-v2.json SHA acc65e7b29ef27643ff2fabcec3b703d9af21543f5f21546fab1c21c6a5e2e03。
当前准备完成，下一动作仅本批具体费用授权；不提前签发新grant，不将行政预检算业务质量。旧freeze/seal未变。
