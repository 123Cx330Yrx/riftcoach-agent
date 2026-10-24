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

**目标：** 减少把可选表达升为必要修订的误报，同时保留真错检出，不重跑原生成。
**起点：** 全源与独立诊断确认block10误报、block21阈值问题有效；原六项接受保持，旧seal不变。
**实现：** 离线隔离候选scripts/review_necessity_candidate.py复用现有Sol请求，在facts initial/fresh引入
“补丁改变什么实质含义”的判定及虚构物流正反例；不改schema/职责/旧接收器，不按关键词删意见。
**证据：** 原稿a、只修目标b、再加明确因果错c，完整来源相同、逐处唯一对照；生成不读标签/旧意见。
7项新隔离/完整性与58项既有职责/补丁测试通过。旧真实误报仍结构合法，程序没有冒充语义裁判。
**限制：** b/c已由主线程全源核对标签，无独立Agent整稿接受；模型改善未证，候选未接入付费或产品自然任务。
**接线：** 现有owned worker新增显式候选模式，父/子端均重建核完整请求；high/max/524及拒发/回执129项检查通过。最终提示候选22项、导出/原自然绑定2项通过。
high/max问题独立未解决；旧UTC授权不延展。Provider/Key新增0，automation PAUSED。
**失败决策：** 有限实测如仍误报或漏报，否定此提示候选，不继续逐句加字重买；超时保留其他有效观察。
**入口：** 已实现review_necessity_launch，复用owned worker/ExactNativeGate；三项各一次，超时保留前项，
共享至多一次显式补测，完整回执中断只读协调；三项加补测最多4尝试/321536 tokens，估价0.233472元。
high/max公开意见仅诊断审查后停，不继续为档位购买；语义实错停止该候选，不加字续买。
**实际预检：** 干净执行树冻结6052be74，独立Agent /root/necessity_independent已完成真实行政作者原件→check-answer→唯一native final→导入；
只读回查31件原件SHA/mtime不变，0尝试/真实Key/Provider。首次另一检查点尾LF不符保持拒绝；不修改原件或normalize接受。
当前plan f3c2c586、原submit stdout checkpoint 09dd5c9e；Windows PowerShell CheckOnly/缺授权拒绝/隐藏哨兵与UTF8日志均已核。
这是行政交接，b/c仍非独立黄金标签；工程入口通过不证明模型改善。
**授权及前检：** 2026-10-24用户已授权，grant SHA85c771e3，截止北京时间10月25日10:56:33；
原计划/原stdout根绑定完成。冻结6052be74的CI39895429952全绿，完整原生/源码/材料/UTC前检通过，原件未变、仍0请求。
**最新实际结果：** a已1HTTP/131.094秒远端524；无完整意见，用量未知预留80384，worker已回收。
原stdout/exit SHA及checkpoint77132319只读核过，retry_available不封批，未发第二次。
**新用户决定：** 允许多次手动补测，第一补测切企业0.25×；原grant/Pro回执原样保持，新授权绑定追加变更。
**实现及验证：** amend追加新HEAD/source/cwd/Python、企业Profile/比例估价及无固定次数手动补测；
仍每次1HTTP/80384预留/300秒/自动重试0。20项原入口及企业连续补测/拒绝混用/保留账目/只读封存检查通过151.60秒。
独立Agent已实际确认可复用；mock检查不是企业稳定性或业务质量证明。
**实际企业准备：** 执行树D:/riftcoach-review-necessity-enterprise-execution冻结2bd7e08e，原Operator追加amendment0001及checkpoint0006，
根b2bb4ab9来自原stdout；旧原件SHA/mtime保持。新企业Control的start-enterprise.ps1实际CheckOnly/CI等待取消通过，
Pro入口已保留原字节并退役；新Key/HTTP/claim0，无残留waiter，原累计1HTTP/80384unknown预留保持。
**下一动作：** 用户运行企业入口，先等精确代码CI40057680511（当前in_progress）全绿再隐藏输入企业Key，仅发a第一补测。
不再使用原Pro首补测入口，不改原plan/receipt/源码树；原UTC截止不延展，企业比例估价0.07296元/次非账单。
high/max完整意见诊断审完即停，不为档位补买，可能不会跑完三项。
不自动恢复旧15、不开新生成、不把旧六项拼为同版本资格。
**依据：** data/evaluation/fixtures/review_necessity_20261023/README.md及
 data/evaluation/results/review_necessity_launch_preparation_20261023.json；独立原诊断checkpoint1355e97a。

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

以canonical和上方工作卡为准：候选/三稿/worker/有限恢复/真实行政作者交接及本机入口均已验证；
新费用范围已获2026-10-24用户授权，首项已发送后远端524；父根77132319保持原件。
企业分组及多次手动超时补测已经实现，真实新入口准备完成；恢复根b2bb4ab9，执行代码冻结2bd7e08e。
用户运行企业Control/start-enterprise.ps1，脚本先等40057680511全绿后隐藏输入Key，只补当前a一次；不自动循环。
准备证据review_necessity_enterprise_recovery_20261024.json；授权仍至北京时间10月25日10:56:33。
原Pro首补测准备文件只作历史证据；未证明企业稳定性或模型改善，原发布门、8E与后续依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。
