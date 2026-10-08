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

2026-10-08：四字段必要编辑协议已接回原15执行、阶段双审、前缀/完整回放及严格资格审计。
独立 review-bound 身份隔离旧资格；原始15数据、初评请求及GLM/Flash/high保持，默认产品未注册。
修复编辑journal丢失/独立文件漏写，并拒绝阶段记录或journal篡改。另修Windows宿主返回
扩展路径前缀导致的目录误判；先解析链接再统一路径，原目录/后缀/大小/身份检查保持。
相关本地验证163项通过：旧入口/资格/编辑器75、新接线6、封存回放和执行路由2、宿主80。
新完整15是替身执行与审计证据，不是模型质量；真实封存编辑及93/pass成稿请求仅离线复核。
独立代码审查及路径补丁复核无阻断；早两次审查断流无结论，未计通过。
真实只读预检确认主线程与/root/identity_contract_design父子身份、当前路由及终态证明可用；
派发正文仍不可读，沿已采用native-final-attestation-v1，不降低或替换证明标准，不保证未来可用。
冻结golden_review_bound_original15_preparation_20261008.json，方案SHA b2eb550ddc6766a26e98a1f7e0af8d404495af9733718e29d2d7ee6b605261b7。
新增完整15最多35调用（Flash10、GLM25）、3386880tokens、10500活动秒、86400host秒；
保守未缓存估价37.167104元，不是计费硬封顶。首失败停、不重试、不借旧1/15或诊断初评。
下一动作：提交/推送并核对最终公共CI；取得这份新冻结方案的明确付费授权后才执行。
本轮Provider0，旧三阶段授权已用完。原15真实质量、自然Coach、当前组合Worker/DB/API/
Workbench和8E仍未完成；四块联动、本人Training、审美/必要重做/头像、Memory、身份运维、
两树整合与学习沿原依赖保留。详情见docs/plans/2026-10-08-review-bound-original15-integration.md。

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
