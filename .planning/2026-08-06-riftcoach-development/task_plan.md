# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 在完整上下文标准下区分真实错误和措辞建议，让整链可靠完成；减少每次首失败后整十五例重启的重复成本。
**已核起点：** 旧文档批前三例整链双审接受，第四例检出真实伤害归因错，同时对泛指均值是否构成事实错存在主/独立分歧，旧批关闭为3/15。
本次授权剩余11独立初评已全部返回并全文双审，十接受、一scope:3修法分歧；四份正确稿pass>=85、七份带错稿needs_revision。
11GLM/Flash0、180387tokens、unknown0、活动483.233秒、Host2138.189秒，未缓存估价2.136576元。
191原件摘要/90白名单JSON严格封存，scan_completed=true、diagnostic_accepted=false；结果见docs/plans/2026-10-09-document-remaining11-scan-result.md。
CI-only分片恢复后执行HEAD3f3669b9/公共CI37823755271全success，原69项模型依赖/业务请求/身份/方案/预算未变。
历史严格2/15与旧文档3/15独立保留，本次新增资格0；完整15、自然消费、8E未完成。
**当前动作：** 前瞻性九个全文Host控制已分别审查，八项一致、一项C06语义分歧；原native及格式故障保留，没有导入StageAssessment，见docs/plans/2026-10-09-host-boundary-calibration.md。
用户要求先规划下一步，执行顺序已细化到docs/plans/2026-10-08-review-validation-efficiency.md的“扫描完成后的执行计划”：裁决依据/阶段覆盖→共同修复→含代表性编辑及fresh的集中诊断→同版本完整十五例→真实产品消费。
两处实际命题/来源及十五例阶段覆盖已完成：五正确稿无需尾链；十带错稿中二例尾链已观察、六例未测、二例初评分歧。新增Host task按实际request SHA交付完整policy（编辑带两份），旧冻结helper不动；26项检查及19历史阶段/21份原policy传递核验通过。新入口尚未真实开放阶段消费，完整policy校准仍有分歧，不称语义修好。见docs/plans/2026-10-09-review-coverage-and-policy-delivery.md。
下一动作核定六个未测尾链的隔离执行合同及两处分歧的前瞻检验，形成含初评/必要编辑/fresh的集中诊断；旧初评复用先核相容性，不预先承诺。开发诊断一例语义失败只停止该例依赖尾链并继续其他独立案例，硬故障停批；该新模式须单独完成接线/预算/授权，正式15规则不变。
泛指均值不自动等于全部指标；样本描述、否定证据充分性与明确因果断言应区分。真错/未来全称/错误主要归因仍阻断，不能把措辞改善升级事实门。
独立设计复核推荐全段范围账本后，核ADR0116最终否决证据并撤回；不新增全段解释工作或以结构完备性代替语义。
校准只调整未来执行理解，不改旧原稿、Provider回包、双审意见或封存标签，也不认证模型质量；有实际修复证据才准备新完整15。
**边界与失败分支：** 本批已完成授权并关闭，无活跃付费runner，自动接续暂停；无新付费授权、不借本批余量。
校准仍有分歧，保留差异；自动词义门未由既有标准采用，未来Host须先写明实际命题及来源关系，不能关键词判错。不能换作者求一致或原样重买完整15；保留全文双审和初评→必要编辑→fresh质量门。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/重做/头像、Memory、身份运维、两树整合和学习继续保留。
仍在原D盘，迁机包a5ab4625为历史快照，后续提交需另行fetch。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map，当前模型组合消费尚未实测。

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
