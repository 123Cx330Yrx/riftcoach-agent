# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：本地修复完成；三稿六审材料和断网验证完成，独立材料审查usable。无付费执行批，8E未完成。

## Active Work Package

**目标：** 用全文正对照、事实单错和完成度单缺口，判断该候选配置是否值得继续投入，不再追逐分类偏好。
**状态：** 三份新写报告、六份原业务请求/非流式wire、逐段主审、评测侧标准及人工修法见证已保存。
**来源：** 熟悉的原五局完整材料，非holdout、非自然新生成；旧r01/r02不重测、不改标签拼成原筛选完成。
**实施与证据：** docs/plans/2026-10-18-reviewer-semantic-materials.md；
 data/evaluation/results/reviewer_semantic_materials_20261018.json。11项断网检查通过，模型调用0。
**判读：** 逐项核完整意见/修法/正确保留；合法category不因偏好否定。材料真错或争议先停设计；
真实语义失败停止配置筛选；协议失败为语义未决。全部六审成立只支持继续有限评估，不授资格或迁移。
**边界：** 六次482304tokens/1800秒为未授权新提案；无新live入口、无新公共CI、不调用旧四次launcher。
用户授权全新独立审查上下文，作者实际全文审读并自行交付，六职责判断一致；普通材料审查不是业务native认证。
**本轮结果：** 新六审控制层及成对补丁预览审查已接线，14项新增离线检查、6项旧配置关键回归通过。用户确认报价，六次估价0.350208元非硬账单上限；模型调用0。
**下一动作：** 补齐受控live入口，完成干净精确提交公共CI和真实作者/账户/路径绑定，再申请本批新费用授权。详见docs/plans/2026-10-18-reviewer-semantic-execution.md。
**后续实际接入条件：** 真实作者/事件、当前账户报价、精确HEAD/CI/路径/网络和新费用授权；不把此材料包称ready。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map；当前组合已完成一份自然观摩真实消费，业务验收拒绝，不能外推产品可用。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。

以canonical和上方工作卡为准：本地合同修复与裁决更正完成；GLM采用保持，厂商迁移未决定。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。
