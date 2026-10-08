# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 将已验证的必要编辑能力接回现有原15与自然Coach验证，保证实际错误被修正而正确内容保留。
**当前动作与边界：**

2026-10-08：用户授权的完整原15批已执行并关闭；同提交0f6069c4公共CI37705382449三项成功。
新身份严格回放有效2/15：claim-scope:1正确稿96/pass；claim-scope:4初评84/needs_revision，
Flash仅修正必要句，精确成稿GLM96/pass。五个阶段均有真实主审/独立审查及宿主事件取证。
第三例claim-scope:3返回78/needs_revision，正确检出block6混合补刀均值错误，却对block4
增加事实误报：第14块已明确全样本早死2.5/2.67，不能以局部中单读法强制修改正确描述。
双审均拒绝，执行器以role_pair_host_rejected正常结束；未启动第三例Flash、未重试或续批。
本批5调用72461tokens、unknown0，未缓存估价0.7274096元；活动约296.47秒，host约1160.27秒。
127原件摘要封存golden_review_bound_original15_result_20261008.json（SHA c1c3bfda…ed525）；
公开回包白名单不含私有推理。严格资格validated_partial/2，review_controls与产品资格仍false。
配对诊断确认：两例只有block6文本及派生摘要不同，事实、规则、工具、输出预算相同；
完整限定确实送达，公开错误解释还明确提及第14块。不是缺上下文、编辑破坏、超时或额度耗尽。
尚不能区分随机波动与另处真错对判断的影响，不能宣称模型内部根因或可靠修法已被证明。
已复用现有previous_raw/issue_resolutions生成实际混合例及明确中单反例，离线映射检查与独立复核通过；
它仍是完整重评，不是窄裁决，不能把人工构造输出当模型正确。没有新提示或schema、没有额外Provider。
下一动作：基于这两个具体输入准备现有重评的有界实测及失败分支，不原样重跑15或只追加提醒。
新方案尚未冻结执行，旧批剩余额度不转授；新付费需具体冻结后另获授权。
当前默认产品不变，8E未完成。自然Coach、当前组合Worker/DB/API/Workbench、四块联动、
本人Training、审美/必要重做/英雄头像、Memory、身份运维、两树整合与学习沿原依赖保留。
详细结果、排除项和待决策见docs/plans/2026-10-08-review-bound-original15-result.md。

上一批真实三阶段全部通过，3调用45538tokens、unknown0、约0.4230100元；
封存及适用范围见docs/plans/2026-10-01-review-bound-edit-result.md。

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
