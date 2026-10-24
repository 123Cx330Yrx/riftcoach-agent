# ADR0114 — 固定边界示例接入完整审查链

2026-09-28。采用显式工程接线；模型分工、验收标准及阶段顺序不变。质量资格仍待验证。

## 依据与决定

当前失败的首次偏离是审查把全文已消歧的可选范围说明升级为事实错误。低温诊断仍误报，
已停止该路线。固定虚构印刷厂四种边界只示范现有采用标准，不提供目标报告答案或事实来源。
两控制真实完成：正确原稿96/pass保持、明确错组82/needs_revision且解释/修法正确。
随后真实Flash改稿把中单早死改为2.50/0.50，区分全样本2.5/2.67，其他内容保留；
同策略GLM fresh终评96/pass，两个阶段全文主审和独立审查均接受。
尾段封存SHA da0d73a6a3a97c1da225fa591547cdfeaa1be43f6aada8f525436b1b4c4862ab。
这是开发例可行性证据，不是稳定率、因果提升、独立holdout或完整原15资格。

将实测示例逐字保留到app/evaluation/golden_role_boundary_examples.py，新增显式合同1.5.5、
Program3.4.0、evaluation3.8.0，Skill0.6.2业务要求不变。初评、fresh及既有一次格式/来源
恢复审查共用review_policy并指纹化。Flash编辑保留完整意见和原编辑政策。GLM/high、
temperature1/top_p.95、输出结构及来源表示不变；共享5调用/401920tokens/900秒、一次改稿。
默认Worker不切换，产品没有新增Agent、挑战步骤或第二套状态机。

## 数据与控制路径

显式build_boundary_examples_coach_application → RuntimeCompositionRoot核manifest →
现有Agent生成/knowledge.search → 同预算初评 → 必要时Flash编辑 → 相同政策fresh →
既有发布/存储路径。run_role_coach_development的boundary-examples profile绑定同一
contract/builder/candidate_identity；可信Trace按新snapshot校验Program身份，旧snapshot不变。
诊断scripts保留原版本历史；产品不import诊断scripts。新旧政策逐字一致由请求测试校验。

完整原15仍复用连续executor、原标签、真实回执重放、全文双审、逐例耐久完成及封存门。
新版本不接收旧3/15、两控制或离线初评注入尾段；只有同版本完整原15才授review_controls。
独立草稿/主审提交复用已有模式；绑定模块从保存的workflow identity选择受信backend，
再核完整candidate/source/request/response，显式profile冲突拒绝。修复的是旧版本硬编码，
不是放宽审查或允许无人签署。正常、失败、恢复及后续封存回放均需同一绑定。

## 验证与费用边界

验证覆盖全部15请求与实测诊断逐值一致、editor不变、fresh无旧意见、实际应用的工具/
编辑/终评及恢复预算、实际natural入口回执、可信Trace、新旧资格互拒、完整15的真实
执行器与草稿提交/封存审计（网络替身）。这些软件验证不能统计成真实模型通过。
共享源码指纹变更需刷新四个旧可运行manifest与新manifest；旧封存原件及其历史资格不改写。

新完整原15预留35调用，其中Flash编辑10、GLM审查25；3386880tokens/10500秒含人工等待，
按现有价格全未缓存估价37.167104元，非账单硬上限。真实新增请求需本批明确成本授权及
同提交CI成功，首实质失败停批；不重试、不重评、不换示例借余量重跑。当前尚未执行。
资格完成后才验证自然生成/工具/纠错及同组合真实Worker/DB/API/Workbench；前端审美/头像、
四块联动、本人Training、Memory、身份运维、两树整合和学习依赖仍按活动计划保留。

## 本轮验证结果

新runtime/qualification15项通过，含完整15脚本回执、实际草稿双审、跨进程提交、新旧
资格互拒及实际应用工具/恢复/共享预算。旧相关125项中124通过，历史pair preview身份
漂移修复后该套18项全部通过，去重合计140项。独立审查无剩余阻断。以上均非模型质量。
新准备canonical SHA 68ba8615cd18685d1f6be1bdac5fe78ce0a8f589a3a8a693fcf935acb0e927fd。
历史pair先固定seal校验，再恢复执行时身份，实际输入/请求/政策/预算全量比原冻结；
不能重开闭批。原tail封存33份逐件不变，修后export重建仍等于原封存。

补充可信Trace/原native应用/角色回执/粗来源合同等61项通过14.95秒，其中1项与新准备重复；
去重总计200项相关检查通过。冻结准备重建断言另通过，治理/编译/diff检查通过。

## 2026-09-29 后续裁决：独立审查身份合同仍未满足

上一节的“独立审查无剩余阻断”只描述 2026-09-28 的离线/结构验证，不能覆盖随后真实批次的
身份审计。2026-09-29 首例 `claim-scope:4` 虽完成初评→Flash 修订→GLM fresh 复评，三阶段
独立意见和主审决定却由同一主执行主体写入；原 v1 只检查 JSON、SHA、append-only 和阶段绑定，
没有受审计的第二主体，因此按 stop rule 停止，模型事实证据不授予 review_controls 资格。
完整回执、下一例的一个 unknown/incomplete 请求和只读审计见
`docs/plans/2026-09-29-review-independence-failure.md`；旧批不补签、不重开。

已撤回“同一进程生成双密钥”作为伪独立证明。当前 v2 要求冻结 root/independent 主体、完整
case/stage/request/response/source 绑定，以及由协作宿主产生的 completed event；事件正文必须
逐值等于独立审查正文。`HostReviewEventSource.fetch(event_id, binding)` 已贯通草稿、正式提交和
恢复校验，`freeze_v2_identity` 统一生成身份注册表副本，但真实宿主适配器尚未实现，故 v2
保持 fail closed；这不是新的 Provider 资格或产品准入。

同日整链复查更正：此前只覆盖了接口局部。现补齐实际请求SHA、批次调用方和严格回读，
冻结product资格API通过task-local宿主依赖重入，保留原代码身份与全量审计。
候选Codex原生适配器已能通过只读app-server读取实际child metadata与完整turn，验证
真实父子/作者/任务绑定/最终正文，并从宿主记录计算摘要。离线完整15及适配整链通过；
真实失败审查被正确拒绝，但实际成功事件未验证，两次工程复核均429，不能采用为可付费
执行的成功证据。具体路径、验证及限制见上述身份失败审计后续段。旧批继续只读。


## 2026-09-30：身份修补的真实宿主工程验收与兼容范围

原生协作派发可能未投影为userMessage，现从API指定的宿主rollout交叉核对；
私有transport turn ID可能不同于API turn，使用真实item_completed严格关联
thread/turn/message/正文。两种最终投影均晚于派发，无需规定它们的落盘先后。
旧事件摘要保持，新加密派发因无法核验任务绑定而明确拒绝，不采用本地替代。
qualify保持有效来源至冻结API重入；全部profile的新签发写入前要求v2，历史
v1仅只读兼容。模型、high、产品版本及采用标准未改变。

169项相关回归、42专项、3整链聚焦分别通过（有重叠）；最终八文件独立代码
复核通过。新明文派发已在独立主体下实际完成取证、草稿、主审、正式提交、封存
回读且原件不变。此为合成Provider接受样例，不证明真实GLM质量、原15或8E完成。
旧加密事件不补签，其他宿主格式须先验证。详细证据与中断审计见
docs/plans/2026-09-30-429-recovery-audit.md。用户当前要求在审查修补后汇报，
没有据此启动新付费批次或迁移旧资格。

## 2026-10-01 工程取证调整：显式原生最终确认策略

旧明文派发策略在宿主正文加密时阻断。四种只读来源无明文；原生输入替代入口受现有
multi-agent父线程写锁约束，未实际生成模型请求。继续修改字段不能恢复这一路径。
经独立方案和代码复核，在既有工程修复授权内采用显式native-final-attestation-v1策略：
仍从宿主核对冻结父子身份、真实作者、派发路由/turn/顺序、唯一完成final和完整六字段绑定，
用独立final对实际原件作出的确认提供任务绑定，不再要求独立重建加密派发正文。
可读派发若与final矛盾仍拒绝；正文各原件摘要、全文检查、主审决定和封存回读照旧。

host_review_evidence_policy进入冻结计划SHA、事件和原始证据摘要，消费门逐值验证。
缺省仍dispatch-and-final-v1，未知值拒绝，不在旧取证失败后自动切换。旧封存、失败结果和
历史资格不改写，产品模型/high/1.5.5/共享预算及完整上下文质量标准未变。不另建v3签署体系。
新策略不声称证明派发逐字内容或审查者阅读行为；详细取舍见
docs/plans/2026-10-01-native-final-evidence-proposal.md。

新工程样例已完成真实独立审查→宿主取证→草稿→主审→封存→回读，实际密文派发可用；
Provider为合成，真实GLM请求0，不授review_controls或产品资格。完整原15仍1/15。
