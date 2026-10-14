# 互补职责与编辑消费：离线实现及下一验证范围

2026-10-14。当前完成的是离线合同原型，设计见
[ADR0117](../adr/0117-proposed-complementary-review-duties.md)。
上批关闭提交8a69e4ec的公共CI38507399305成功；本轮无模型发送。

## 已解决的工程问题

事实专责排除了“是否引用/使用知识”的任务完成度义务，但旧完整校验器仍会以
`native_missing_knowledge_citation_unreported`拒绝缺引用的pass。离线反例已复现。
新隔离校验器明确区分职责，同时保留未知引用、来源、段号、协议和注入检查。
原完整校验器及冻结源码保持，旧五次初评结果没有重判。

`scripts/review_duty_composition.py`把同一完整报告/来源交给facts与completion；
用input/report/request SHA及stage绑定两份原样意见，不平均分数、不合并问题。
准备编辑要求明确的兼容状态；调用者填clear并不构成真实语义认证。
两份意见进入原block editor，沿实际锚点/重叠/回执校验组装新稿，再为新稿构建两份fresh。
fresh不带旧意见；结构双pass始终不能打开产品发布门。

这使“评价→意见传递→改文组装→新稿复查”能在软件层表达。completion政策仍未实测，
真实兼容裁决、Host绑定、观测、共享预算与取消接线、实际模型编辑均未完成。
原三处语义问题仍未证明稳定解决；真实full分歧不改签，熟悉材料不充当holdout。

## 验证与复现

- 19项新离线测试覆盖完整来源、职责边界、污染/协议拒绝、原样双意见、实际组装和fresh绑定。
- 47项既有预算/editor相关回归通过；均为软件验证，不是模型调用或Host审查。
- `scripts/audit_review_duty_composition.py`从15份完整固定输入构建30份请求，核正文/来源/schema
  保持，并核旧live身份全部拒绝。结果为
  `data/evaluation/results/review_duty_composition_offline_20261014.json`。
- 审计保存五份相关源码SHA。已有131本批原件、11件包、77源码及历史证据按旧清单复核；
  canonical历史字节保持。本轮不创建或改写任何业务run。

复现测试：

```powershell
./.venv/Scripts/python.exe -m pytest tests/test_review_duty_composition.py tests/test_document_review_timed_budget.py tests/test_report_block_keyed_editor.py -q --tb=short --show-capture=no
./.venv/Scripts/python.exe -m scripts.audit_review_duty_composition --output <new-path-outside-data/runs.json>
```

审计输出create-only，应使用新的临时输出路径并在比对后清理；不要覆盖已封存证据。

## 最小真实消费验证提案与执行缺口

只复用上批duty-3的完整输入快照，重新取得facts/completion初评；若两份均经真实审查接受、
有实际可修问题且修法兼容，则一次Flash编辑，再对实际新稿分别fresh。最多4 GLM-5.3/high
加1 Flash/high，共5请求、483840tokens、2700活动秒、86400Host秒，单次600/300秒与32768输出。
未缓存合同上界估价5.8609664元，实际账单不以此为硬封顶。没有生成、重试、补发或资格授予。
双方initial都pass则结束，不能硬造一次编辑来声称消费成功。

下一工作包须先完成隔离开发入口：

1. 新请求/回执身份绑定完整政策、来源、职责、阶段、编辑协议及预算，旧入口继续拒绝。
2. 将主审/独立真实native接受与两份修法的兼容裁决绑定到同一稿和原样意见；clear不能自签代替。
3. 每次发送前核run库存、run外观测/作者、完整请求和共享账本；取消/硬故障停止后不得恢复发送。
4. 用离线整链验证双pass跳过、拒绝/冲突停止、实际改文、两fresh、预算耗尽与未知用量，
   再形成执行包、preflight、同提交CI、具体新授权。当前尚未达到执行准备完成。

任何facts实错、completion无依据要求、错误修法、fresh失败或冲突均否定该链在此例的充分性；
协议/native/transport/预算故障停止，不将缺失当成功。正向结果仅支持开发方向，不能重启原15。

自然产品含两次生成时最坏7调用，当前5调用/401920tokens/900秒不自动扩容。
以后必须复用`CoachBudgetedProvider`的同一账本/时钟和真实Worker取消/租约门。
仅提高调用数而保留token/时间上限也可能走不完；当前不能承诺自然任务完成。
automation保持暂停；本提案未请求也未取得新付费授权。8E和下游产品依赖保持未完成。

## 2026-10-14 后续接线：同进程开发链与原生兼容裁决

`scripts/review_duty_execution.py`新增固定报告的顺序执行核心，
`scripts/review_duty_host_gate.py`复用现有Codex原生事件导入、checkpoint和run外作者文件。
每次初评、实际编辑及fresh独立审查；两初评通过且需要编辑时另作一次Host兼容裁决，
只提供两份Provider原意见、完整报告/来源，不泄露主审或其他Host判断。
兼容裁决本身没有新增GLM请求。主/独立均接受且无冲突才能调用一次编辑。

初评双pass跳过编辑；任何意见被拒绝、兼容冲突、坏编辑或fresh未通过即终止该固定报告链。
错误请求/回执、观测缺失、预算、取消、身份/作者/库存漂移截断后续发送。关闭目录和同一实例
不能重启。响应公开存储剔除reasoning，故障只记录异常类别，不记录SDK异常文本。

执行核心使用真实`CoachBudgetedProvider`和`SharedBudgetReviewSender`，只在该实例覆盖开发
预算；沿同一账本保留实际用量与未知预留，共享活动时钟，复用`DevelopmentHostClock`记录Host等待。
每个实际发出的请求必须等于当前完整prepared请求，只允许共享预算标记和缩短timeout；
回执SHA绑定实际issued字节，失败后的已知用量仍结算，未知用量不释放。

此处依赖注入的sender、观测读取及Host交接用于离线整链测试，尚未接真实observed worker、
外层新授权/同提交CI/native preflight、持久化严格replay/seal或付费CLI。
当前同进程`replay`会重核原件和重新读取各个native事件，但不冒充跨进程严格封存。
这是开发执行核心，`execution_ready=false`。实际产品Worker的租约/取消仍需在真实发送边界接线；
测试中的停止钩子只证明该接口会截断后续调用，不是生产Worker验收。

接下来的执行准备只剩上述真实适配和闭合审计；本轮不申请或消耗新模型费用。


本次新增45项场景通过（40项整组及受影响增量复核）；实际编辑接受还要求原有四项
ReportAssessment全部通过。错误回执也先保留公开响应、结算匹配身份的已知用量；超时未知
预留保留。观测库存中的孤立文件会阻止下一步。保存的开发核准备为
`data/evaluation/results/review_duty_execution_preparation_20261014.json`，摘要
`44c798178929b4ea70f3d3284bcf6e6d354cc5c6f7e8ec60a3aea3e8da50bb7d`，明确不具备付费执行条件。


## 2026-10-14 真实子进程传输与跨进程回放

本节接续并替代上节“真实worker/跨进程封存未接”的实现状态；付费入口仍未就绪。
`scripts/review_duty_transport.py`私有加载既有stream bridge，使用独立开发transport身份，
不改变旧生产校验器或历史worker。父/子进程核当前stage的完整prepared/issued请求；
仅共享预算标记和缩短timeout允许变化。子进程复用真实SDK、零重试、high、600/300秒
父进程deadline及kill/reap，direct代理清理只作用于子进程环境副本。

run内新增精确白名单的transport回执、独立receipt和call-state；body-free HTTP观测保持在run外。
每次submit、下一发送和回放都核原件与观测SHA。硬失败尾项可保留缺失但不能算完整响应成功；
意外文件/链接、请求和身份漂移仍拒绝。公开response不保存私有reasoning。

`scripts/review_duty_replay.py`用Operator在关闭时另存的closure SHA作为起点，在新进程重新构造
原请求、两份原样意见、兼容材料、真实编辑组装、新稿两fresh和停止顺序；重取每项独立native，
核run外作者/checkpoint和观测。逐项重算同一预算账本的已知/未知预留及Host/活动时钟，
不从当前磁盘临时重建一个库存并直接信任。缺少可信closure SHA或不完整关闭记录时拒绝封存。
replay不创建锁/临时证据；seal重新replay，只允许在三个证据根及data/runs之外create-only输出。
HTTP不可用时保持null，不能用脚本调用数冒充真实HTTP次数。所有结果production_admitted=false。

关闭调用者应保留session.closure_sha256到run外Operator记录；尚未接外层wrapper，当前不运行真实批。
只读CLI使用明确--run、--closure-sha、--codex-executable，可选run外--seal。新进程测试用显式
SCRIPTED native事件；真实native客户端是正式CLI唯一来源，测试事件不能作为业务审查。

本轮发现两处持久化问题：超时整数读回浮点导致重新序列化SHA不同；排序公开响应中的工具参数
导致兼容/编辑输入的原样意见字符串变化。分别改为核实际issued字节、从prepared恢复允许字段，
以及create-only保留公开响应字段顺序。不是通过放宽旧证据SHA消除失败。

新的开发准备记录为`data/evaluation/results/review_duty_transport_preparation_20261014.json`。
旧44c79817…准备只保留历史，不再作为当前源码的可执行摘要。下一步仍须完整transitive源码/包冻结、
新授权绑定、同HEAD公共CI、即时native及绝对cwd/Python启动预检、唯一执行占位和Host交接wrapper。
本轮没有请求新授权，没有付费调用，automation保持PAUSED；本机HTTP测试不证明三处语义问题已解决。

本轮稳定代码相关整组67项通过（438.17秒），受影响收尾13项通过（111.80秒），共68个不同场景通过；公网Provider=0。
新准备plan SHA为`7703a20328c1eca57d43cef1a453045151fc982b125a3edeeaf164a481730c57`。

## 2026-10-14 外层执行准备接续

上述“外层wrapper和完整冻结待接”的状态由本节更新：现已接唯一执行claim、24小时授权、
同HEAD公共CI、即时native和实际绝对cwd/Python启动、父/子发送门、完整Host mailbox及外层
只读replay/create-only seal。完整输入三文件包和847份源码/配置已固定；具体准备摘要、
命令、停止规则、费用与证据见[执行准备](2026-10-14-review-duty-launch.md)。
92项相关整组通过，收尾受影响检查见progress；真实路径/native准备探针通过，未发新业务任务。
这些完成的是执行边界，不改变Proposed状态，未证明原三处语义稳定解决。
下一步只在新授权和当前提交公共CI全绿后执行该固定报告链；不沿用旧授权，不启动原15。
