# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

2026-10-19：原批第六项HTTP524保持封存；用户单独授权的s03-completion补测HTTP200，22094已知tokens。补测意见与唯一block21修订后的全文均双审接受，真实native/作者字节导入和只读回放通过。三稿六职责由原五项加独立补测取得语义覆盖，不是原六次全成功。累计7HTTP、132730已知tokens、80384未知预留、421.704活动秒；未发布、未授资格，automation PAUSED。

## Active Work Package

**目标：** 区分请求/日志high、渠道响应字段与SDK解析分歧，避免再次付费后只得到不明冲突。
**事实：** 控制台公开JS直接显示log.other.reasoning_effort；公开New API请求转换写该日志，未核实部署版本相同。
截图不证明API响应high；本机SDK默认None，实际mock HTTP未复现high被自动改值。旧具体值/意见已失且不可补签。
**实现：** 使用SDK公开raw-response接口，单HTTP先记原JSON白名单分类及响应体SHA，再比较SDK身份字段；
不同明确response_decode_mismatch，SDK解析失败仍留原分类。既有公开意见留存保持，不存原HTTP正文/私有推理，接收标准不变。
**保留：** 旧seal1d0a2f49及70项库存再核未变；6HTTP/80137known/145824unknown/retry1与原稿、生成、检索保留。
**验证：** 107项最终接收/SDK/实际worker/应用/恢复/只读封存检查通过（419.37秒），含此前93项分组不相加；模拟SDK漂移/解析失败、已知用量、不重试、唯一应用和库存防篡改覆盖，治理/编译/diff通过。
**下一动作：** 用户运行outputs/riftcoach-sol-reasoning-single-20261022-control/start-authorized.ps1；脚本先等待冻结364db0ba/CI39746293864全绿再隐藏输入Key，最多一次原facts-initial。
**实际准备：** 干净执行树D:/riftcoach-sol-reasoning-single-execution，计划22f77653、入口a86ce1ea；原件/绝对cwd/Python/原生路由prepare/check通过，真实终端隐藏哨兵/取消和日志UTF8/退出SHA通过，CI实际等待/取消通过，无残留waiter/claim/call。CI08:23UTC仍运行，打包/数据库已success。
**诊断分支：** raw high且SDK一致才查新意见语义；raw非high且SDK一致处理渠道映射；不一致修本地解析；
非标准字段形成有证据的兼容决策；超时不回答本疑点。单次1HTTP/80384tokens/300秒，估价0.058368元，不自动重试。
**入口：** sol_reasoning_single复用既有owned worker；新增13项实际worker/SDK及入口检查通过（19.80秒），四分支/费用/原件/单claim/取消/过期/只读封存防篡改覆盖。不重跑已通过107项。
**授权：** 当前继续指令与原必要预算授权显式缩窄绑定新诊断HEAD/计划，原grant只作来源证据；仍截止北京时间10月23日11:54:18，最多一次/80384tokens，不延长。
**边界：** 未开始新付费/未读Key；实际冻结准备完成，精确HEAD CI尚运行，不重开旧封存，不证明渠道已恢复或业务合格。
449ec45f/CI39740910236尚运行；95718581/CI39737779367已success，不能冒充本次新版本CI。
工作卡/事实仍为原2026-10-22-sol-credential-wait-recovery.md及sol_reasoning_identity_diagnostic_20261022.json；automation PAUSED。

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

以canonical和上方工作卡为准：同HTTP对照及单次入口检查通过；实际冻结准备及安全命令已完成；用户运行入口，先等精确HEAD CI再隐藏输入Key，做一次原请求诊断；客服非硬前提。GLM产品采用保持，厂商迁移未决定。
复用原稿与历史成本，不重开旧封存；当前发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。
