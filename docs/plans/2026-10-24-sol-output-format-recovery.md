# 自然任务响应格式恢复与完成度诊断

2026-10-24。用户要求普通格式故障就地修复、保留成功项后续接，不因接收格式关闭整个任务。

## 工作卡

- 目标：一个完整且唯一的有效工具调用即使附带文本也能正常消费；无可消费工具或坏JSON时暂停当前阶段，手动恢复不重买成功项。
- 起点：冻结2b14583e的前三次请求与facts双审完成；第四次completion-initial为HTTP200、模型/high匹配、21531已知tokens，接收器因伴随一个message误拒收。
- 首次偏离：旧接收器`non_tool_output`，不是HTTP或上游超时。原程序在新指令到达前已终结并封存，历史回执、根及唯一seal不改写。
- 实现：显式`natural-sol-necessity-v2`响应模式只消费唯一合法工具参数，其他message仅计数，不持久化/执行正文；旧v1模式保持严格拒收行为。开发合同1.6.4显式绑定新模式与恢复策略。
- 恢复：真实session将完整且身份匹配的纯文本/缺工具/坏工具JSON结果记为`recoverable_format`，保留已知用量，再以SessionPaused越过业务终结。普通run不发送；`--manual-retry`只允许同一请求一次，使用既有共享补测额度，再失败仍暂停。
- 硬边界：未知输出、多工具、身份/档位冲突、缺有效观测、业务非法补丁及真正语义错误不借格式恢复放行。无可信回执的pending intent仍不得重发。旧冻结树、闭批及预算不重置，不自动延展授权。
- 验收：真实父进程/worker/SDK模拟HTTP、Runtime、会话、native gate及launcher验证；覆盖重复普通resume无Key/无发送，当前阶段补测，成功项只读回放，累计已知/未知费用、唯一应用、同稿双fresh和严格只读封存。

## 本次保留意见的独立语义诊断

第四次保留的公开工具参数通过原业务结构验证，不等于语义通过。message正文未留存，不能称为空消息或前言。
主审与既有独立作者实读全文/全部来源/政策/两项意见及五处补丁，真实native final与run外作者字节逐字相同；诊断只导入Control外层，不补签原闭批。

有效意见：block18只有OP.GG数字和边界，没有把一项指标连接到具体条件建议/待验行动；这是已有资料消费义务的真实缺口。
无效意见：issue1将下一批对局无依据地限定为读者自己的比赛，忽略block2和直接管辖后文的block20观摩限定。可明确措辞，但不能把可选改善升级成必要身份错误。
错误修法：block21删除约8.7–9.0与≤3的观察参照；原胜局8.66/8.95及2/3支持这些值，且原文未将其设为个人达标门槛。修复实际OP.GG缺口不需要删除它们。
五处补丁锚点唯一、不重叠；仍整体不接受。事实初审已接受的两项真错保留，不由完成度重判。

## 当前结果与下一动作

原执行累计4HTTP、66591已知tokens、0未知预留、0重试；没有实际应用、compatibility/edit或fresh请求。前三次成功与facts双审仍有效；不是整批成果作废，也不是完整链路通过。
原guard5668400a、0041 checkpoint aa3c2816、唯一seal24172c4f保留，冻结树clean。automation继续PAUSED。

本包只修确定的格式接收/恢复缺陷，不改业务政策后立刻再买一次。当前completion意见另有实质语义问题，不能通过容错把它变成合格意见，也不能把一次新响应当作旧错误消失。
离线对照已完成：四份完整27段及同一全部来源，仅交叉“OP.GG是否连具体行动”和“是否明确要求个人参赛”。原a基线可重建原真实请求；b/c/d保留已接受的两项事实错误及正确观察参照，避免跨职责标签漂移。7项离线完整性/隔离检查通过，标签未入模型输入；既有独立主体不读标签/主审意见实核四稿及方案，结论一致、材料接受；唯一完整原生final与作者字节一致，submit和只读replay通过，非模型质量证明。
候选仅增加实际义务、全文对象/动作、实际缺口、最小补丁保留的判定顺序，不改当前运行合同或输出schema；它是待否定的假设，不能因提示写好便认定模型会遵守。
具体竞争解释与结果决策见data/evaluation/fixtures/completion_necessity_20261024/README.md。8份配对请求实际离线生成，但不是8次调用计划/授权。

CI40084544939暴露当前库存遗漏：共享源码/manifest已更新但库存仍指旧摘要。本包新增format_recovery当前库存并更新当前重建测试，保留旧necessity_integration及所有历史快照；6项库存检查通过，只变component_fingerprints/program_sha256。原15输入、30请求、预算、未执行及资格不变。

离线断点入口已实现：`scripts/prepare_completion_continuation.py`先在启动子进程前核外层seal/全库存/计划，再使用原冻结cwd与原Python、合同1.6.3严格replay，不把旧v1回执改标为新v2。临时派生session导入1—9成功操作与事实journal/回执，原host handle仍走原作者目录、原计划和真实native事件，不能仅复制accepted标记。原facts响应不变，仅其临时预算快照显式继承后来失败的attempt/费用，并恢复待完成逻辑职责。
实际Runtime已准确到达原completion-initial发送前；max_new_models=0及发送前拒绝回调双重阻止新IO。4HTTP/66591known/0unknown/0retry、255.657活动秒均保留；145件原封存（含seal）与3件作者原件前后相同。b/c/d/a请求与亲本证明实际输出在`outputs/riftcoach-completion-continuation-20261024-offline`，a基线和原前沿业务请求一致。
13项新增检查覆盖实际Runtime不重检索/生成、原native及作者字节、前沿/账目/接受状态/回执篡改拒绝、启动前亲本及输出路径验证；6项库存检查通过。测试native/HTTP替身只证明工程行为，真实原件/事件另由冻结回放核验。上次提交3902e1ee的CI40087866246现已success。
下一动作：完成候选合同/receiver、继承native路由和共享累计预算调度的运行接线，再离线验证b/c/d→a→兼容/编辑→唯一应用→同稿双fresh。a新真实结果直接消费，不先单测成功a再重买。当前离线入口不是付费启动ready；新具体范围/预算/活动秒/版本/期限须在完整入口可审查后核定。四稿/政策仍是待检假设，不因恢复工程通过便授采用。
没有可交付的当前批付费resume入口；旧Control/resume-authorized.ps1保持拒绝闭批，不再让用户填Key试运气。
真实模型语义、同版本15、产品资格及阶段8E未完成；自然Coach/Training、四块/journal、前端、Memory、身份运维、两树整合、独立评估、学习与自然6调用/产品5调用依赖保持。

## completion诊断接线与零发送恢复（最新）

2026-10-24完成completion诊断续接引擎与显式启动器。合同1.6.5复用既有session、owned worker、共享预算、原生审查及程序逐字补丁；顺序为b/c/d对照→原稿a的completion→兼容/编辑→唯一应用→实际同稿双fresh。它是诊断续接，不是完整产品Runtime注册或产品准入。
原9个成功操作、原facts/作者/native及4HTTP/66591known/0unknown/0retry/255.657秒继承；旧失败保留，不重买生成/检索/facts或首次接受的a。超时及明确格式错误只暂停同项，普通resume不读Key/不重发，手动补测保留费用；身份、来源、真实语义及观测硬错不借此重试。
整链/异常9项、启动/授权/关闭回放9项、相关旧回归67项（包含6库存检查）通过；7受影响配置实际启动校验通过。另以真实原proof/原作者/native实核新引擎，准确停在control-b发送前，原145件及3作者原件不变；新增Provider/Key均0。模拟检查不是新模型语义证明。
显式CLI scripts/completion_diagnostic_launch.py已提供prepare/native/task/submit/run/replay/唯一seal；新计划拟新增最多10请求/803840tokens（6职责+4手动补测），累计14/870431/3600活动秒，新增估价0.7296元非账单硬限。尚未获得本次费用授权，旧grant不扩范围/期限；当前不要填Key。
首个冻结5f46413d的真实作者/check-answer/原生final/导入及最终PowerShell CheckOnly已通过；缺新grant的正常入口也实证拒发、未读Key、未创建execution。其CI40094551645发现测试glob无排序、Linux误取旧预算；生产回放已有排序，本包只修测试取最新账目方式，保留失败记录。
**下一动作：** 用修正测试后的新精确HEAD冻结续接准备并核CI；只有全绿及具体新授权后才交付可填Key入口。旧准备无付费执行，不当作已通过CI。automation保持PAUSED。
证据data/evaluation/results/completion_diagnostic_integration_20261024.json及当前资格库存completion_continuation_20261024。候选语义改善、完整产品链路、正式同版本15与阶段8E均未完成；后续产品依赖保持。
