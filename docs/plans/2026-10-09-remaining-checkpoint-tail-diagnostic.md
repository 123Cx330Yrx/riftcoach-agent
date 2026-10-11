# 未执行五尾链：集中诊断冻结准备

2026-10-09执行状态：用户已明确授权；3954ff16/CI37912659534全绿后首次启动。第一例Flash返回缺required block，协议硬失败关闭，仅1调用/11055tokens、fresh0/认证0/其余四案未发。已严格封存，接续PAUSED；本批不可重开。最终结果与下一动作见2026-10-09-remaining-checkpoint-tail-result.md。以下未授权/Provider0/无run的准备描述保留为授权前快照。

## 目标与取舍

补足claim-scope:6、observed:2、observed:3、observed:4、observed:5的必要编辑/fresh开发观察。它们在两次六尾链Host硬故障批中都没有发出请求。scope:4已有本次真实Flash编辑但无有效native双审，保留覆盖缺口，不重买首案或新签旧意见。

这次首次偏离是Host最终交付不可用，不据此修改Provider提示或断言已找到语义修法。新Host选gpt-6.1-sol（原中转不支持Luna）；通信通过不是完整业务审核证据，仍用真实新子主体、原生final与逐阶段全文检查。旧合同/模型/Provider政策与所有五份请求不变。

沿此前效率策略：先集中暴露未测尾链风险，语义失败停该案依赖阶段并继续独立案；收齐后按实际问题统一修复，必要开发验证后再同版本正式15。首案未认证与attribution:1/scope:3两个分歧不被本批修好或下传；全五案通过也不能补首案、拼跨批成功数或触发资格。

## 最小实现与真实接线

只新增scripts/document_remaining_tail_adapter.py；它用importlib加载四个固定仓库模块的隔离实例，显式绑定五例KEYS、controls、prepare、checkpoint observer、handoff和seal。原sys.modules中的旧模块不改；旧代码/源码摘要/原件保留，旧批沿原入口严格重建。

新controls首先核此前关闭结果的确切SHA及unexecuted库存，再调用原controls完整核六份真正accepted历史输入的来源/request/journal/原件，选择五例。初评只注入完整历史Exchange，不新签历史、不发初评。单一observer复用共享预算、transport真实回执、逐案例停止/继续、Host时钟及finally记账；没有简化任何原生或全文质量核验。

checkpoint observer在下一send前核全部实际task与pin；submit绑定新独立主体、同checkpoint绝对路径/SHA、六字段binding及真正native final。只有有效revision双审且四项ReportAssessment全真才能发fresh；fresh须pass>=85且无实质误报漏检。所有保留和改变内容、事实/解释/修法、reason、引用均审；Host标签不发Provider，泛指不补全称、措辞建议不升级事实门。

新run为document-remaining-checkpoint-tails-20261009；旧observer的experiment仍是历史workload标签，新plan/seal的run_id区分实际目录。既有目录付费前拒绝，source/identity/native/checkpoint/protocol/transport/budget/主体不可用硬停全批；无重试、重评、重开关闭批或资格转授。operator abort只停账，不代造审查意见。

## 范围与预算

| 项目 | 新计划 |
|---|---|
| 顺序 | claim-scope:6 → observed:2 → observed:3 → observed:4 → observed:5 |
| Provider | Flash/high必要编辑5、GLM-5.3/high fresh最多5；新初评0 |
| 总调用 / tokens | 最多10 / 967680 |
| 活动 / Host时限 | 3000 / 86400秒 |
| 单次输出 / 超时 | 32768 tokens / 300秒 |
| 保守未缓存估价 | 7.862272元，非硬计费封顶 |
| 预算独立性 | 新具体授权；不借关闭六例批的剩余预算 |

准备execution_authorized=false，Provider0，新run/等待器不存在，自动接续PAUSED。该文档不授付费权限。

## 检查与证据

新增9项和旧checkpoint11项共20项公开夹具/synthetic IO检查通过，217.66秒；测试禁止读取忽略的本机data/runs。覆盖五例完整10请求往返、语义拒绝继续、显式abort、缺checkpoint、native不可用、来源损坏可停但不可seal、既有目录付费前拒绝、先前seal变化拒绝、旧模块对象/源码隔离。它们不是模型语义质量或真实DB/UI证据。

旧231338b6…cff93aeb准备精确重建及旧已关闭结果strict replay再次核验；新五份cells和原请求SHA/模型identity精确等于旧六案后五项。代码编译与项目治理检查通过。独立代码复核无剩余具体缺陷；实际native final严格导入通过，新真实主体谱系/current-route预检通过。独立另跑41项回归446.82秒通过，与主线程20项有重叠，不相加当独立覆盖。

公开preparation：data/evaluation/results/golden_document_remaining_checkpoint_tails_preparation_20261009.json。
方案SHA：d7bf39c634a603b1bcee299de7e7d87e596e258c6c9b4c5afe8bc9c9329aa3e4
主审：01a0c6c5-01d1-78d0-82fb-e567e0ab7150。
独立Sol原生主体：01a11fea-dc3d-72d0-a07e-90fde8f04f92，/root/sol_connectivity_check。
旧关闭结果SHA：b87882fd3fc86bc1d3dc873930aabe090fc4b63e1ad1c3ae7405d31a32ca7700
Operator目录：C:/Users/33502/Documents/Agent/outputs/riftcoach-document-remaining-checkpoint-tails-20261009。

## 操作入口

新统一入口为python -m scripts.document_remaining_tail_adapter：

- run：原checkpoint runner参数；不带--execute只生成准备，--execute须确切preparation/plan-sha/同HEAD公共CI/clean checkout/实时主体预检。
- handoff material/task/checkpoint：选--key KEY --stage revision或final；读完整实际材料，create-only发布task/checkpoint。
- handoff submit：--notes主审原生JSON路径、--event-id真实独立原生事件、--checkpoint路径/SHA、--codex-executable；不得代写/裁剪独立输出。
- handoff abort：指定当前pending key/stage/reason；硬故障后唯一runner自行关闭，核exit及账目。
- seal：只读严格回放、--output create-only白名单封存，实际native事件核全部已审stage；任何原件变化拒绝。

正式运行前必须最终代码复核、同提交公共CI全绿和当前真实主体/native可用；查询失败不当CI失败。执行期间不改冻结源码/HEAD，绝不启动第二份runner。

旧文档3/15、另一身份历史2/15独立保留，新资格0。正式同批15、自然Coach消费、本人Training/四块联动、Worker/DB/API/UI/journal、前端审美/头像、Memory、身份运维、两树整合、八维学习及8E保持原依赖。来源不因新计划自动变成产品准入。

## 最终开发审查与执行前边界

实际独立代码复核native事件：01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a11ffc-b7e8-7a52-9d6c-c8e8e258d1ce/msg_02fea8690fadd9d9016ac8b58f72408195ada02c671dac7466
精确checkpoint/SHA、原样多行final JSON、当前新Sol作者/root原生谱系及native-final-attestation-v1已实读验证；公开readiness保存真实事件，不造StageAssessment。
新计划重新精确生成相等；旧冻结源码diff0、旧准备及20原件/原封存strict replay精确不变，五份cells/request/identity精确不变；新目录仍不存在、Provider0。

本提交公共CI和该新五例范围的明确付费授权仍是首次执行条件，当前没有runner/等待器。授权后执行前仍重读当前主体状态/精确源码/HEAD/全绿CI，不将本次路由预检缓存为未来保证。自动接续仍PAUSED。
