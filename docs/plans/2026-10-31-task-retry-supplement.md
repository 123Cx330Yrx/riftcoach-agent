# 同一产品任务的一次补充重试准备

用户报告上游曾故障、现可准备重试；该恢复尚未由当前模型路由独立验证。继续原非流式，同一facts-initial请求，保留三次生成、三次524和所有费用，不另开模型批。

原授权最多2次手动补测已耗尽，Runtime同样拒绝第3次。准备限定到task/run/owner、最新checkpoint和失败结果SHA的一次行政补充许可；产品默认2次不变。许可不会由HTTP resume接受，只有显式配置的Operator/Worker可传入。授权、有效期、旧授权SHA、旧累计重试数及原总预算须核对；未授权草案不能发送。

补充只增加一次手动动作，不改变8总请求/401920tokens/900活动秒/单次300秒、10月31日15:45北京时间截止。当前6请求、29323 known、220146 unknown预留、553.594活动秒完整继承。只剩2总请求槽；若初审要求修稿，双fresh不能容纳时保存审查并暂停，不偷加预算。

新许可随同manual-retry操作追加到原日记，消费后重启只回放。旧操作、失败、费用不改；缺许可、错误任务/检查点/失败、过期、扩大总预算、重复使用均零发送。已提交操作即使许可过期仍可只读回放，不能据此重发。

完成判据：真实Session/预算的禁网回归、默认2次不变、成功前缀/未知预留保持、当前库存一致、真实原件与数据库的零发送预检，冻结新执行版本及其CI。执行前再激活针对该具体方案的补充授权；本准备不自行扩大原授权。

## 准备验证

2026-10-31 用户报告上游恢复并要求准备重试：同一任务的一次补充manual retry已实现，保持原非流式；产品默认2次不变，仅该task/run/owner、最新checkpoint和失败结果SHA可使用一次补充许可。草案authorized=false，尚无新增付费请求；上游恢复仅为用户报告，未独立验证。

真实数据库零发送预检已通过，原154份上一快照原件保持；当前142份运行库存核验通过。预检生成最新checkpoint a8ec5dc9bdf5ad697b6d67a977d10b0ec5bb2cc8ecff8f4ffcc817f255f2054a，后续须用Control/manual-retry-extension-ready-20261031/recovered-db.dump（SHA f22b154d55056bccd3eee5c61309c8c49e7a2228cfee34999160026b6bb6c3f6），不能退回attempt-7数据库。累计仍6HTTP/29323 known/220146 unknown预留/2retry，活动554.500/900秒，未发布。

验证：补充许可及既有产品合同27项通过；过期许可的已提交操作只读回放补测1项通过；库存/Worker等11项通过，11个Runtime入口匹配。4份当前Sol清单和新库存仅更新实现摘要，旧清单/原15/历史冻结不改。工作卡docs/plans/2026-10-31-task-retry-supplement.md；机器记录sol_product_retry_supplement_prepared_20261031.json。

下一动作：一次提交推送、冻结新执行树并绑定同HEAD CI；Control/binding与ci-success为执行依据，旧56cd86b2的CI41151387633全绿不能代替新CI。准备完成后取得明确的一次补充许可再执行，automation保持PAUSED。原8总请求/401920tokens/900活动秒和10月31日15:45北京时间截止不延长；仅余2总请求槽，初审需修订而双fresh放不下时保存结果暂停。Stage8E/默认产品入口/玩家稿与Evidence消费目标保持。

## 授权后CI故障处理

2026-10-31 14:47北京时间，用户“继续呗”明确触发上一答复列明的一次同项补充重试。Control/manual-retry-extension-ready-20261031/supplemental-authorization.json已激活（SHA 26a6d33c49653157b06525eee606eea99b0a70f06645dcad1765067c2e64e1e1），原8请求/401920tokens/900活动秒和15:45截止不变。尚无attempt-8或新增付费。

CI41166396355实际失败：四个pytest分片、打包、迁移通过，web-checks的真库浏览器resume场景等待“检查并继续”90秒超时；retry/cancel通过，汇总pytest仅继承web失败。截图显示恢复详情加载失败；原CI未保留trace/失败HTTP，不能把根因直接追认为已证。

已独立稳定复现同类本地缺陷：恢复详情与用量同时只读核验会争用CandidateSession非阻塞独占锁，第二请求抛session_executor_active，被API当作完整性错误。修复只在只读入口有界等待锁5秒，仍核原checkpoint/全部证据；耗尽返回503，真正损坏仍500，不发送模型或重试业务。新增争用/有界等待/损坏不重试及双API分类回归，28项通过；11个Runtime清单与治理通过。CI增加fixture trace、attempt-state和错误上下文保留。

真实Chromium→API→临时Postgres→Worker的resume/retry/cancel三场景均通过（116.61秒，模型/来源替身，零外部模型请求），保留前缀、费用与发布边界；结果sol_product_session_read_lock_repair_20261031.json。下一动作：一次提交推送、冻结新版本及CI绑定；已授权的同项补测仅在新CI通过且未过15:45时执行。当前仍原checkpoint a8ec5dc9…、6HTTP/29323 known/220146 unknown预留/2retry、554.500活动秒；历史成功/失败不重写，Stage8E和automation PAUSED保持。工作卡docs/plans/2026-10-31-task-retry-supplement.md。

## 本次执行结果

2026-10-31 16:13同HEAD CI41178505872八项全绿后，唯一执行器完成已授权补测；call-007真实HTTP524，130.407秒，request/wire SHA与前三次完全一致，closed/reaped。新增观测cf-ray a5313371ac6bc5bf-NRT，发送后约126.563秒才同时收到响应头和首字节；本地配置300秒，没有本地读取超时异常。仍无Sol语义意见，不能宣称该路由上游已经恢复，也不能仅凭524确定源站内部根因。

本轮新增1HTTP，累计7HTTP/29323 known/293528 unknown预留/3retry，receiptless0、unresolved0，第8次未发；活动690.172/900秒。额外一次补测已消费，不再自动重试。原142份运行库存、上轮154份快照及原成功生成逐字保持。最新checkpoint 1006173c2969d9eb981fccddb1febb975290a17e15e58bcba488341eb205a7c1，最新数据库Control/attempt-8/terminal-db.dump SHA d03bae291a606529f003a469401ee589ecaf6a85afdd8537cba0bdac0f066b51；attempt-8-snapshot.json追加保留，session未封闭，可按新决定恢复，不退回旧DB。

真实浏览器1440/320已核用量和3次补测、刷新不POST恢复、无横向溢出，未审查正文不可读；当前paused时usage独立端点409，页面从continuation显示真实用量。真库任务1/暂停1，assistant/Training/Evidence snapshot均0。inspection-complete后执行器与waiter均已退出，exit原件确认临时容器已移除；riftcoach监控已实际删除。结果data/evaluation/results/sol_product_extra_retry_timeout_20261031.json、Control/attempt-8/audit-proof.json保留完整证据。

下一动作：本次补测与监控收尾，删除automation；暂停受影响的首审步骤，保留整链，等待用户对传输方案及后续验证范围的新决定，不重复同一付费请求。原总预算仅余1请求槽，不能把它当作额外补测授权或保证可完成双初审。原15完成、Stage8E和产品准入保持，玩家稿发布/Evidence实际消费尚未完成。旧失败/到期/续授权原件不改。
