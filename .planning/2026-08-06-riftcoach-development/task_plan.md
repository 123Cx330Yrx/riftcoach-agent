# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：本地合同修复/裁决更正完成，真实质量尚未验证；无新付费包，automation PAUSED，8E未完成。

## Active Work Package

**目标：** 修复审查候选诊断的请求/接收矛盾与失败观测丢失；纠正分类偏好被当作业务失败。
**状态：** 本地实施及离线验证完成；原模型筛选未完成，产品资格未变。
**实施：** 新nonstream-tool-v1明确选择审查工具，保留全文/schema，复用owned process及业务validator；
失败先记录终态、输出类型/数量与已知用量，再拒收；旧stream模式及封存回执不改。
**实际消费：** 原r02响应的三种合法category产生完全相同修订稿；缺修法/错误块/坏锚点/重叠拒绝。
预览中的另一职责pass是测试替身，不是completion真实响应或独立语义认证。
**裁决：** r02正确检出不因other作废；r01原合法对照前提失效，首次误报与后续单次正确结果各自保留。
历史10次HTTP尝试、96307已知tokens/4次未知，不能拼成原四项筛选完成或供应商账单。
**证据：** docs/plans/2026-10-18-reviewer-route-recovery.md 与
 data/evaluation/results/reviewer_route_recovery_20261018.json；无新模型请求或native业务认证。
**边界：** 原backend封存、主树前端保持；GLM采用不变，第三方未获资格，不因标签偏好淘汰。
**下一动作：** 重新确定有限语义评估的材料与去留决策；先审完整来源/修法/正确保留，不继续旧分类复测。
当前无付费执行包；任何后续真实请求须回答明确问题并沿用既有授权/冻结/CI/路径/独立审查要求。
不以本地通过声称端点遵守新模式或模型质量过关。

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
