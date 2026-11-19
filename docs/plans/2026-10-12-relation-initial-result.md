# 关系教学四次初评对照：关闭结果

本批已关闭：4次GLM-5.3/high初评全部发送，3次完整返回并完成真实双审，最后一次600秒超时。
正确稿上出现候选减少误报的单次差异；错误稿候选没有完整响应，不能据此确认修法改善、采用候选或授予资格。
没有编辑、fresh、重评、重试、补发或新Agent。自动任务`riftcoach`已实核PAUSED。

## 实际结果及裁决

| 实际任务 | Provider结果 | 主审/独立审查 | 本次证据 |
|---|---|---|---|
| R4-baseline:initial | 85 / needs_revision；第6段一个issue | 双方拒绝，false_positive | 把明确中单语境中的五局窗口读成全部位置，正确数字不支持该范围解释 |
| R4-relation-contrast:initial | 95 / pass；无issue | 双方接受 | 正确稿被保留；可选措辞澄清不升级为事实错误 |
| T9-baseline:initial | 60 / needs_revision；第15、14段issue | 双方接受 | 检出补刀逐对全称错误及早死均值相同错误；解释、来源、修法和正确保留均核实 |
| T9-relation-contrast:initial | ProviderTimeoutError / transport | 无完整响应、无派审、无提交 | 已发送，非未发；不能判为语义通过或失败 |

最早语义偏离是R4基线第6段误报；最早硬偏离是第四项传输超时。三项双审没有分歧，
共3次业务submit，第四项没有Host checkpoint，不能补签。所有stage均initial、report_assessment=null；
T9基线的意见被接受不表示原稿已修好。第4段advisory未掩盖第14/15段真实错误。

R4对照只支持本次正确稿保留差异。T9基线已给出正确关系修法，未重现旧H5的错误否定区分；
候选T9无结果，因此本批不能隔离或证明旧H5修法机制已改善，也不能估计稳定率。
熟悉来源和已做开发校准不称holdout。裁决是保留候选为未采用的开发材料，不改生产默认；
不因传输失败自动追加同义教学或付费重跑，不把不同版本历史成功拼成正式15。

## 授权迁移和运行证据

原授权绑定549220ab1b8c7a4edcd93dd74ab6c366c9c2a733及CI38254464870；Linux测试把合法绝对Python
误判为裸命令，发送前停止旧waiter。用户随后明确确认迁移到1039fb50184aebdcbc9401da3b33b594b92919b7
及全绿CI38258297688。修复仅测试/状态，28项相关测试通过；新CI全部8个job成功。
原树clean后仅该次fast-forward，所有绑定源码/包逐项SHA一致，真实native及cwd/Python启动预检通过。
原authorization.json与确认/重绑定/迁移记录均保留；issued_at与截止2026-10-13T13:18:08.784319Z不延展。
固定plan为8b93463e04a5d4321727ba06188914047d12215d097a12fc0091eabb2e3d0dda。

唯一runner于14:20:04 UTC启动，14:57:32 UTC以exit1结束；第四项worker终态deadline，elapsed_ms600079。
最后进度为reading、last_event_ms30672、768事件、无工具参数、无终态usage；这说明响应流未完整结束，
不能仅据此定位网络或Provider内部根因。前三项的complete回执优先于last_http_event的关闭事件字符串。

## 账目和封存

- actual calls 4、observed HTTP 4、HTTP发送未知0；Flash0。
- known tokens 50893；unknown usage calls 1、receiptless 1；未发送0。
- 已知用量按输入8/输出28元每百万tokens估算0.637484元；超时请求费用未知，未核真实账单，不能当总费用或硬封顶。
- 活动时间796.016秒，Host1442.062秒，墙钟2238.078秒；均在原2400/86400秒批预算内。
- 严格只读replay通过，create-only白名单seal成功，3份真实native复核，73份原件清单与SHA完全不变。
- seal SHA：d31a205897bdd1ba8da543d639e4b1305d2c3b65bf5d891b425effc7a2c36e13。
- 旧47/26/14/146原件清单及SHA逐项不变，旧缺口不修饰、不补签。

每项独立任务唯一NEW_TASK，复用既有主体；完整生成dispatch明确cwd/Python/checkpoint/SHA及run外作者路径。
作者各自create-only落盘、final前重读checkpoint、check-answer通过，唯一多行JSON原生final与作者文件一致
（仅末尾空白差异）。主审意见先保存，随后实读真实API final和全部公开命令，再submit。
公开命令数为16/14/14，全部exit0，独立材料阅读输出无截断；主审一次重复来源展示截断已逐字段核等并补读。
Host库存门贯穿提交、native读取后的锁内和下一发送；本批无意外run文件。
原生策略核真实主体路由/API final；不声称读到加密派发正文，不把公开命令记录当OS沙箱证明。

可复核证据：
- `data/evaluation/results/document_relation_initial_result_20261012.json`：严格seal与完整公开业务证据。
- `data/evaluation/results/document_relation_initial_close_audit_20261012.json`：迁移、CI、账目、原件及旧批核验。
- `data/evaluation/results/document_relation_host_evidence_20261012.json`：3项主审、原生final及公开工具记录，不含私有推理。
- 本机operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-initial-20261012`。

## 下一动作与保留依赖

本批授权用完并关闭，不重开。后续先基于这些已封存证据形成具体的无付费方案裁决：
区分正确稿的范围误报与旧H5关系修法错误，判断哪个未决问题值得新增验证；不能直接宣称采用候选或跳到15已过。
任何新付费范围须另行明确授权。正式同版本15、自然生成/工具/编辑/终评消费和8E仍未完成；
Coach/Training、四块联动、Worker/DB/API/UI/journal、前端审美头像、Memory、身份运维、两树整合、
独立评估与学习均保留。历史2/15、3/15、remaining11、分段15和旧教学对照不合并资格。

## 收尾检查

本次只新增已关闭证据及状态文档，未修改运行源码。严格回放/封存、公开native/作者一致性、
新旧原件SHA、跨结果账目与3项审查数对账、治理检查及git diff --check均通过。
修复提交已有公共CI全绿；收尾提交的公共CI是新状态，不沿用该结论。
