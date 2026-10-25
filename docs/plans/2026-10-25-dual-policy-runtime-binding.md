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
