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
**已核起点：** 新文档批授权后真实执行，前三例整链双审接受，第四例正确检出归因真错而block4判断主/独立分歧，按首失败停。
8次调用117718tokens、unknown0、活动418.767秒、估价1.171026元；188原件封存及document-review strict回放为本批3/15。
历史严格2/15独立保留，不能拼接；默认产品未采用，新身份完整资格/自然消费/8E未完成。
结果、原件/Host插曲和后续依赖：docs/plans/2026-10-08-document-original15-result.md。
**当前动作：** 剩余11独立扫描工程包完成，新21项/相邻旧30项离线检查通过，真实独立代码复核发现的封账缺口已修、末次无阻断，当前native主体预检通过。
原15业务identity/input/report/request等于旧封存；每例独立transport，共享预算，语义失败收集继续、硬边界失败即停；无编辑/重评/资格授予。
冻结d5aa7c91…73429bf，11次GLM/1064448tokens/3300活动秒/86400Host秒/估价15.724544元；细节与运行入口见docs/plans/2026-10-09-document-remaining11-scan.md。
取得该具体新付费授权并核本提交CI全绿、clean HEAD、真实主体后首次执行；扫描结果用于归类共同修法与正确控制回归，再准备最终同版本完整15。
本轮Provider0，不把工程测试说成语义已修好；不把扫描和旧批拼成资格。原质量门和全文标准保持，最终15仍首失败停止。
**边界与失败分支：** 本批已关闭，自动接续暂停，无重试、重评或余量重开；其余十一例及第四例编辑/fresh均未执行。
完整规则和来源确实发送，表示改变不足以解决所有问题；不能把主审误报裁决写成双方一致，也不能由单次对照宣称内部原因已明。
新诊断语义失败可收集，但硬身份/传输/协议/来源/预算失败须停，独立账本不得授原15资格；具体冻结及新授权前Provider0。
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
