# 时间600 Worker边界与完整15例待冻结方案

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

这份是具体范围/成本提案，没有冒填原生审查身份或生成可执行授权。当前团队仅有主审；
原聊天独立主体不能冒用为新root的子主体。需在本聊天绑定真实可用独立主体，
重读当前source/policy/checkpoint协议并核真实原生输入/final可读性。随后按既有prepare
冻结源/原始请求SHA/审查身份/完整计划SHA及新run目录，同提交公共CI全绿后，
请求此45调用范围的具体付费授权。授权前不创建业务run、不触发Provider。

上一20c77f49/CI38046089854查询仍in_progress；本包提交也需自己CI，不能借旧绿。
若公共数据库反例失败则按最早实际偏离修；CI查询失败不是测试失败。旧固定裁决
c90a73ef…feb5及旧seal76e9a70b…75f30原字节复核一致。
