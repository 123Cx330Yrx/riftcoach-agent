# 新自然任务的手动超时续测

2026-10-24。接续必要修订政策自然接线，不重开已封存的三项或六项，不发送新付费请求。

## 目的与实现

一个自然任务仍是两次Flash生成、四次Sol初审/fresh。成功的生成、检索、审查、唯一应用和Host决定都按原操作回读。
网络超时不是语义否定：只有原监督进程已回收，且完整观测把故障确定为超时，才持久保存`reaped_timeout`并暂停。
没有可靠回执的pending intent继续阻止发送；完整响应后的身份、来源、协议或语义拒绝不能进入这个补测分支。

`SessionBudget`把超时作为已提交的失败尝试留在原session里，`NaturalDutySuspended`越过业务失败收尾，故不写outcome或terminal。
普通run只报告等待手动续测；显式`run --manual-retry`绑定原guard、最新checkpoint、原计划和有效授权，追加一次manual-retry决定。
决定绑定前一失败结果SHA、原发出请求、回执SHA及累计预算。再次超时仍暂停，不自动循环，不恢复未知费用额度。
恢复成功后继续原阶段；成功回执已到但操作未提交时，使用`reconcile`只读回执协调，不能再次发送。

新合同`natural-flash-sol-necessity-development-v1`采用manual-reaped-timeout-v1；旧Sol合同保持原行为。
新合同明确预留4次手动重试、最多10次物理调用、739840累计tokens、3600活动秒，每次最多300秒；逻辑调用仍为2+4。
这只是一个待授权新任务的初始包络，不是用户允许补测的永久次数上限；用尽则保持暂停，按原记录另行准备预算扩展。
等待人工Key不计活动时间，UTC授权继续按真实时间校验；不自动延期、不常驻保存第三方Key。

## 入口与来源

复用`scripts.sol_natural_launch`，prepare时显式`--candidate necessity`。新计划与grant都必须含candidate_contract、retry_mode和企业review_profile；
动态全文、同政策facts initial/fresh、completion完整职责、实际应用及同稿fresh保持上包的业务定义。
企业Key提示使用`GPT-企业专线`；Profile只是本地约束，实际路由仍由用户Key绑定，不能冒充上游独立核验。
执行/恢复/回放均按计划选择同一合同；与baseline或旧三项grant不混用。所有Key只在本机隐藏输入。

## 验证与交付条件

用真实Runtime、worker与SDK配模拟HTTP，验证重复超时每次只放行一项、不重买成功项、累计未知预留、单次应用、同稿双fresh和闭批只读回放。
额外检查补测成功后父进程中断，仅协调原回执；补测返回身份错误立即拒绝；活动预算耗尽保持暂停。
实际launcher贯穿原生任务gate/作者导入/submit/同阶段补测/replay/create-only seal的离线验证不等于真实Host业务审查。
本包同时修复公共CI发现的测试脚本漏传CONTRACT_MODULE，不放宽生产worker的失败或身份规则。

提交源码后用干净独立执行树冻结精确HEAD/来源/新计划，绑定该HEAD公共CI及当前原生作者预检。
真实作者必须按精确checkpoint及SHA自行写run外JSON、check-answer、唯一完整native final，主审读事件后导入自己的审查。
旧独立主体的lineage/final只读探针可用，不等于下一任务能实际调度。没有真实预检成功，不交付付费ready声明。
当前尚无新任务费用授权，prepare/native/replay均零Key零Provider；automation继续PAUSED。
本包不授新模型语义、正式同版本15项或产品资格；后续自然Coach/Training、产品5调用差异及原产品依赖保持。
