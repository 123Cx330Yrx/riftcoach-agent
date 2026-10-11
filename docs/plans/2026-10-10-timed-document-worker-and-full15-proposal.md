# 时间600 Worker边界与完整15例待冻结方案

> 本文保留授权前准备快照。后续time600完整15已在febe2e7f/CI38048400763授权首次执行并关闭；当前结果见[执行结果](2026-10-10-full15-time600-result.md)，不以本文Provider0/待冻结表述恢复旧行动。


本包接续time600执行链，解决其长等待能否保持任务所有权、取消或失去所有权后
是否仍会发布的问题，再回到完整15例真实质量证据。没有新Provider调用或新业务run。

## Worker核验与限制

复用ReviewWorker独立heartbeat线程、TimedDocumentBudget、候选真实role router/
create-only回执factory及原子发布入口；不新建Worker或将候选注册到默认产品。
7个离线反例使用真实线程、完整公开请求和factory，只替换网络transport与数据库。
压缩时钟下190/380秒分别续租360秒，调用590秒返回，超过最初租约但仍可通过
最终所有权检查。600单次与900任务墙保持独立；901秒迟到回包结算30已知tokens，
预算器拒绝交付，Worker只提交失败。续租不重置任务开始时点。

取消/LOST/续租异常均拦住成功及证据提交；最终heartbeat之后取消或换代，
原子提交返回False，Worker收敛取消或ownership_lost，不回退legacy succeed。
7新例与42既有Worker/组合/可靠任务合同共49项通过（33.77秒）；联网被禁止。
这不是模型语义审查、真实600秒运行或默认产品消费证明。

生产PostgresTaskRepository锁任务行后核活租约、worker/generation/token和取消状态，
然后在同事务写snapshot/terminal/event。新增3项真实Postgres反例：连续续租后取消、
错generation、到最新租约精确到期点，均应返回False且snapshot/terminal/event无新增。
本机Docker启动遇sailor-ingest.sock重命名失败，官方stop已关闭；本机2项无数据库检查
通过、15项数据库检查明确skip，新增3项未声称通过。公共postgres-migrations负责实际执行。
没有重置、删除或恢复业务数据库，也没有拿业务库跑降级/升级的测试夹具。

现有同步executor没有取消信号传入模型调用或阶段间sender：取消/LOST/heartbeat异常
会挡发布，但执行器可能继续内部后续阶段，正在付费的调用不能因此撤回。当前诊断runner
并不由ReviewWorker驱动，它按每次发送/Host提交边界的abort和硬故障停止规则执行。
自然Coach的阶段间停止/在途取消是产品接线依赖；本次不把发布保护说成节省后续调用已实现。

## 下一批具体范围与选择

推荐新时间身份下的完整15例开发验证：复用现有runner的selection=full15、
timing-mode=time600。它回答同版本完整初评→必要编辑→fresh能否收齐，符合用户
恢复完整15主线的目标。此前10例已提供attribution的有限正证据；再买同一10例仍缺
5项覆盖，且硬故障停止成本并未消失，因此不增加另一轮10例作为固定前置。

原公开15例顺序保持：claim-scope:1、claim-scope:4、claim-scope:3、attribution:1、
scope:4、scope:3、claim-scope:2、claim-scope:5、claim-scope:6、claim-scope:7、
observed:1、observed:2、observed:3、observed:4、observed:5。全文来源、教学政策、
high/32768、block键必要编辑和fresh质量门保持；Host预期标签不发Provider。

| 边界 | 待授权新批 |
|---|---|
| 新请求身份 | document-review-request-identity-time600-v1 |
| 最大实际调用 | GLM30 + Flash15 =45（初评/最多一次必要编辑/fresh） |
| 单次时限 | GLM review600秒；Flash generation/edit300秒，受同案剩余截短 |
| 单案上限 | 900活动秒 /5调用 /401920tokens，初评至fresh共用同一账本 |
| 整批上限 | 13500活动秒 /45调用 /4354560tokens /86400 Host秒 |
| 保守未缓存估价 | 45.029376元；输入64000、输出32768逐调用计，非硬计费封顶 |
| 失败分支 | 有效语义拒绝停该案依赖阶段，继续独立案；身份/来源/native/checkpoint/协议/transport/预算/主体不可用停全批 |
| 重做规则 | 无重试、重评、重开、借旧余量、旧native补签或旧批成功迁移 |

每个完成阶段需要真实全文主审与独立审；接受编辑/fresh时ReportAssessment四项全真，
fresh pass>=85且无实质误报漏检。实际native final事件导入、精确checkpoint路径/SHA、
只读严格回放/create-only公开白名单仍沿既有流程。旧2/15与3/15各自保留；
即使新开发批收齐，也不自动授予资格、自然消费或8E完成。自然生成未包含在本诊断。

## 执行前剩余项

这份是具体范围/成本提案，没有生成可执行授权。原聊天独立主体不能冒用为新root子主体。
新独立主体/root/full15_independent（01a1257a-2c8b-7f11-9a86-da3e0b6068b6）
已真实创建，lineage匹配本root01a1248f-e18c-7282-92bf-7ceb2eb5dce4，模型Sol/custom。
但两次只返回规则确认、工具0、任务主体encrypted、native agentMessage phase=null，
实际read-only Host门拒codex_review_host_dispatch_or_final_ambiguous；没有HTTP错误，
不将其推断成429/额度，也不能只因加密断言模型未读。不能将其视为可执行双审。
完整15的30份材料已create-only导出，manifest7402b53d…e1870，业务run未创建。
需先恢复真实可执行/产native final的独立Host路径，
重读当前source/policy/checkpoint协议并核真实原生输入/final可读性。随后按既有prepare
冻结源/原始请求SHA/审查身份/完整计划SHA及新run目录，同提交公共CI全绿后，
请求此45调用范围的具体付费授权。授权前不创建业务run、不触发Provider。

9e1c4442/CI38046840121公共DB234过/1失败：新增cancel测试调用漏必填reason，
错generation/精确expiry两新例已过。现补reason并核实际签名；93cdf82a/CI38047477843
公共DB job114199807184已success，web/packaging已success，四pytest片待完成，整CI未全绿；
没有放宽生产门或改事务。公开预检元数据见
data/evaluation/results/document_full15_time600_preexecution_readiness_20261010.json。
上一20c77f49/CI38046089854现已全success，本提交需自己全绿；查询失败不是测试失败。旧固定裁决
c90a73ef…feb5及旧seal76e9a70b…75f30原字节复核一致。

另一消息路径第三turn仍未执行任务且phase=null；当前root亦缺phase，旧成功Sol保留终答标记。
网关配置已经Responses，不能凭此猜修法或根因。停止同类试发，待Host通道修复/更换后再核
精确checkpoint；具体证据/恢复条件见2026-10-10-full15-native-host-path-diagnostic。
30材料SHA复核全一致，自动任务实读PAUSED；准备材料不回写为当前HEAD已冻结付费计划。
