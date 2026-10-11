# 后8例实际执行与恢复操作硬关闭

用户要求继续完整15批从未发送的后8例。本轮已经真实执行，不是只封存旧批或转移到其他产品工作。
在冻结`49010a337a79e1dc34e3a94ae89bca3b78dab8cf`、全绿CI`38062139250`上首次启动，
方案`fcc5adf8af0e37cc38add2cc4dbc9ae947deb5a0e676ad96eaa2b9d2a02cf556`；唯一runner91176/
wrapper77052于UTC2026-10-10T15:34:46启动，16:23:23退出exit1。日期标题按本机UTC+8。

| 案例 | 实际结果 |
|---|---|
| claim-scope:5 | 初评96/pass；完整全文双审和真实native导入通过，无无必要编辑 |
| claim-scope:6 | 初评80/needs_revision；只改block6口径，编辑全文双审通过；fresh96/pass和全文双审/native通过 |
| claim-scope:7 | 初评96/pass；完整全文双审/native通过，无无必要编辑 |
| observed:1 | 初评96/pass；主审与独立全文接受，真实completed唯一final可读，但同turn两个NEW_TASK，导入被拒；未认证，不记语义拒绝 |
| observed:2..5 | 四例从未发送，保留接续目标 |

claim-scope:6的真错是口径未定却说补刀均值持平：中单8.805/9.01近同；全样本8.805/
6.453333…差2.351667，不能统称持平。Flash只替换这一句为两个口径分别解释，其他全文逐字
保留，editor reason有依据。fresh96/pass没有实质误报漏检，编辑与fresh四项ReportAssessment
均真。claim-scope:7原文已经条件区分口径，因此直接通过。这是本版本的有限正证据。

observed:1的原文28段，明确所选四场中单，经济/伤害每个胜局均高于每个败局，限定本次
的“较稳定差异”不能补成长期能力断言；混合视野/补刀、早死、身份、K1—K3、归档OP.GG
中单/辅助条件观摩用途与官方版本边界都经本次完整双审。此判断和96/pass不弥补native导入缺口。

## 首次偏离与责任

首次submit的claim-scope:5采用相对run路径，使重建task路径与原绝对task不同，触发
`full15_checkpoint_changed`，未写submission。核原checkpoint/SHA/task/event/opinion均未改后，
仅改CLI为绝对run路径提交成功。Provider调用和Host重评均0；该operator路径纠正公开保留。

本批终止点是observed:1 initial的恢复操作，不是Provider质量或容量故障：

- root恢复后只读看到独立turn`01a12698-f152-7121-aa93-3e588f927eac`为interrupted、final0，
  live协作库存同时显示running。root先发MESSAGE，随后错误地又发followup_task。
- 原生rollout同一turn真实包含两个NEW_TASK（`amsg_01a12698-f272-7f22-a05b-b4ce8cfaca86`、
  `amsg_01a1269e-0499-77e1-94f9-2503a9ef19bb`）和一条普通MESSAGE。
- 独立沿同checkpoint恢复并完成，唯一真实final为
  `01a1263f-db97-7e02-bd7e-70b3a11b59ce/01a12698-f152-7121-aa93-3e588f927eac/msg_0d4010adabb2cede016aca65f84a288194a2f7343fdfe09dcd`。
  真实response final与item_completed各一，9个实际工具items，completed/error=null。
- frozen校验器要求该turn恰好一个NEW_TASK，实际submit拒绝
  `codex_review_host_rollout_dispatch_or_final_ambiguous`；没有review-submission、host-reviews或认证。
  主审没有修改校验器、裁剪记录、另求终答或补签；helper实际routing_failure abort，runner退出。

责任在主审恢复操作。interrupted不是另派任务的依据，同任务只能普通MESSAGE恢复与等待，
不能对active/interrupted turn使用followup_task。只有前任务真正completed且新stage精确checkpoint
已发布时，才派下一NEW_TASK。原始重复dispatch保持失败，不以未来修法追认。
这里没有证据说明Provider429、额度耗尽、401、503或transport超时；也不能据本次成功返回解释
历史300秒超时。关闭旧批不取消未发送独立案例，下一动作仍是后四例准备。

## 原件与账目

run：`data/runs/model_comparison/document-remaining8-time600-20261010`。
Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-remaining8-20261010`。

严格封存：[`golden_document_remaining8_time600_result_20261011.json`](../../data/evaluation/results/golden_document_remaining8_time600_result_20261011.json)，
SHA`75c8c04dbb6f045de4e24993cae0fa28d192f510fb6726bf68ca99f494ec2bf8`。
公开operator审计：[`document_remaining8_time600_close_audit_20261011.json`](../../data/evaluation/results/document_remaining8_time600_close_audit_20261011.json)。

实际6调用GLM5/Flash1、known98,364tokens、unknown0、receiptless0。未缓存保守估价
1.038154元不是账单；活动433.812秒/Host2459.875秒，未超批或案上限。严格只读replay核5个已认证
stage的真实native事件，create-only封存74个公开白名单JSON，138原件SHA再次一致，收尾Provider0。
observed:1的final只公开事件标识/原生条目计数/摘要和无法认证原因，不能冒认第6个通过stage。
审计保留授权、实际CI、启动/退出和首例路径纠正。自动任务实读PAUSED，不另启执行器。

## 接续决策与未完成项

按用户后8例目标，准备四个从未发送observed:2..5的入口，复用完整来源、实际policy、时间预算、
真实双审与唯一native dispatch门；不先改教学或转外围工作。见
[`2026-10-11-remaining4-continuation.md`](2026-10-11-remaining4-continuation.md)。
准备不等于开启新付费批；旧批硬故障停止、无重试重开约束保持，新的具体执行预算需在准备可审查后确认。
observed:1不重买/重评/补签，旧完整15第7例claim-scope:2未审缺口同样保留。

历史2/15、3/15、remaining11、完整15 time600与本批各自独立；不能相加成为同版本完整15。
新增资格0，正式同版本15、自然消费、8E、Coach/Training/四块联动、Worker-DB-API-UI-journal、
前端审美头像、Memory、身份运维、两树整合与八维学习均未完成，依赖保留。

收尾独立工程审查实际再核138原件/47冻结源码及5认证native事件通过，observed:1仍拒绝；
没有重评业务或新增认证。结果见后4计划中的原生工程终答。后4七项离线接缝、编译、治理和
diff检查通过；公开CI仍需新提交核验。这些工程检查不增加模型质量或资格。
