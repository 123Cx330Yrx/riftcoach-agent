# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

ADR0109角色候选最新在6c100a25完成真实生成/工具/审查/文件发布；来源元数据修复已送达并通过读回。
新成稿经全文独立审查可接受，GLM93/pass的两条建议仍有引用/扩写依据缺口，完整审查输出未通过。
原日期错误未在新稿复现，不等于旧错误稿已自动改好或通用漏检修好；真实改稿/终评仍未发生。
此前另一归因输入的Flash正负对照均通过，不可移作本次日期稿的质量证据；没有证明任一模型更优。

## Active Work Package

**目标：** 修复真实观摩报告中知识来源时间的无依据断言与审查漏检，使生成和审查使用可归属、含义一致的来源时间；不把工程published或单次pass当产品质量证明。

**起点和差距：** 新批实际5调用完成，Flash两控制均接受；混合应用3调用走通，但GLM96/pass漏检block27的知识检索日期。工具和KnowledgeEvidence均只有文档updated_at，真实检索时间仅在Trace；不是转换丢字段或拿错稿。实际改稿/终评、原15资格及产品消费仍未验证。原稿、模型结果和host裁决分别保存在golden_role_application_result_346213c.json。

**本包实现：** 已采用ADR0109，实际入口为build_role_coach_application与ROLE_COACH_CONTRACT；Flash/high生成/工具/改稿，GLM/high首评/重评/终评，共用一个预算和全局调用序号。1.5.0原实测保留；当前1.5.1仅取消可选建议无消费者的强制替换文本，真实issues、编辑与采用标准不变，尚无新版真实质量证据。单个Observer、逐模型Recorder、双传输原回执、可信混合Trace、可逆来源投影及资产指纹复用原Memory/RAG/Harness/Evidence。旧默认不变。实际policy hash与validator hash分别记录。

**本包验收：** 工具原始时间、缓存返回、生成输入、KnowledgeEvidence、审查source catalog、发布来源含义一致；文档更新/知识查询/第三方检索时间分别归属，缺失不补猜。原“正确参考”漏删OP.GG日期的标签已撤回；新参考只删知识及OP.GG两处无依据日期，独立全文核对后才作为应通过控制，不算模型改稿。原15资格和默认入口不因离线检查而通过。

**本次实现选择：** native/role候选启用knowledge.search 2.1的主机UTC检索完成时间；旧默认保留2.0合同。缓存保存原payload，不刷新时间。KnowledgeEvidence增加逐次retrievals(provider/retrieved_at/chunk_ids)，重复chunk仍去重但每次来源记录保留；混合旧数据保留null，全部旧无时间输入保持原投影。审查和落盘共用受限投影，不把provider diagnostics当主机时间；生成沿实际工具返回获取同源数据。活动指纹覆盖适配器/汇总/投影/落盘源码。先检验整链传递，不同时改审查政策或另造报告文字检测器。

**依赖和失败决策：** 核对实际组装、原始回执和资格指纹一致后再做新组合真实验证。不能混报模型身份或复用旧a71eb94五例准入。若新实测出现协议/来源/语义/改坏正确段，停止余下批并按首次偏离诊断，不排列提示变体。方法沿用docs/plans/2026-09-22-agent-delivery-method.md。

**预算和授权：** 单任务5调用/401920tokens/900秒，单次32768/300秒，SDK retry0，一次改稿；两模型共享，预算不变。独立编辑按连续授权执行1次，300秒截止、用量未知；其后Flash日期审查v2实际1次/16169tokens/估价0.0177372元、未知0，两批第二例均未发且已关闭，不借余量。连续授权来自2026-09-10全授权和后续继续诊断修复，不能写成用户本轮逐字新增“两次”批准。Flash v1在0请求时因错误参考撤回。两个实际调用中有一次费用未知，不汇成已知总费用。默认产品未切换，Luna仅Codex开发协作。

**当前状态和下一动作：** 6c100a25 / CI35896981340三项成功后执行冻结的一次角色应用，213.718秒、3次/44654tokens、未知0、未缓存估价0.3872344元。真实生成稿和落盘一致，28段全文的数值/身份/条件训练/知识及外部来源获主Agent和独立复核接受，原日期问题未复现；来源投影与同源存储工作取得本次真实证据。GLM93/pass第二条建议选CS/gold来源却加入damage数值，完整审查输出引用不全；第一条K1扩写也未获完整依据。建议未应用于成稿，不能倒算为报告错误。36份公开原件/hash与重建验证见golden_role_source_metadata_result_v1.json。

**此次反证后的方案边界：** 当前缺口直接存在于原始GLM建议，完整输入与编号映射均正确，不是传输、预算或时间缺失。结束本批，不追加付费或补旧ID；先核对审查引用责任与实际消费，再作最小修法裁决。原15离线恢复保持，每例已有完整比赛和computed根；添加更粗来源没有新增表达能力，不能仅凭12个指标可拼3组就投入完整变体。旧显式编辑路线仍未采用。下一动作不再反复改时间字段或延长输出上限；原15、真实改稿/终评及产品消费依赖保留。

**本轮继续完成的责任精简：** 确认advisory只在原回执/journal/资格审计中保留，没有API、报告或编辑消费者。当前RoleNoteReviewWorkflow保留非阻断通道与block/source_ids/explanation，取消mandatory suggested_correction，真实issue字段不变。旧RoleReviewWorkflow保持原响应回放，旧1.5.0 Trace只读可信且不可重新执行；schema/policy/来源指纹同步，两活动组合可离线加载。62项实际链路、8项新合同、147项周边回归和1项额外历史Trace测试通过；原15完整输入及原意见/ID保持，见golden_role_note_contract_audit_v1.json。新合同没有真实调用。

**下一动作：** 同提交公共检查后，准备原15中明确真错的首评→实际编辑→终评及正确全文控制；复用共享预算/真实回执/原资格校验，不另外安排提示变体或再生成同一自然稿。本轮已经停止付费；旧准备不能执行新身份，也不能由离线减字段宣布质量通过。


## Dependencies and Follow-through

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。
