# 三篇完整报告的初评诊断

## 要解决什么

当前阻断仍是模型审查能否保留正确的全文概括，同时检出真实事实与来源错误。
旧温度批的首对Host双拒绝存在全文反证，不能把双方一致当成Provider错误；
六份合成材料及三篇完整报告的Host校准已完成，停止追加同类校准。
本包把已校准的三稿首次交给当前基线Provider，核对其实际意见、解释和修法，
据此决定继续哪种语义修复或更广回归；不沿用旧批余量，也不同时改变温度、教学或来源表示。

## 固定输入及实际接线

入口：`python -m scripts.document_full_report_diagnostic`。
它私有加载已有screening适配器，复用既有初评、单次有界传输、真实双审、checkpoint、
授权检查和只读封存；没有复制另一套运行循环，也没有修改旧批或默认产品路由。
请求使用既有sampling传输的baseline分支，temperature=1.0；名称中的sampling不表示本次比较温度。
此复用标记只留在本地请求身份中，SDK不接收metadata。

公共材料：`data/evaluation/fixtures/host_full_report_calibration_20261012/materials.json`，
SHA `d3930389e748dfe4fb326f19b335242fe95587203890802b9e18b5a7650ab39b`。
已有校准证据：`data/evaluation/results/host_full_report_calibration_20261012/close-audit.json`，
SHA `6ac2e8e0c8962f6268269d37a9c6ee930c325047da91dc4d730a900ffe78042b`。
两者精确冻结。原材料每稿16个逻辑块按两个换行连接，块内字节保持；生产解析器会将两处标题
和表格分开，生成18个实际段号。不得把校准第11段直接当成请求第11段。

完整事实通过已有公开claim-scope:1来源重建；逐字段与已校准source消息比较，仅允许报告参与
计算的三个摘要字段变化：source_index.source_digest、computed_evidence.source_digest、
source_roots.catalog_sha256。所有来源值、成员、知识、用户原话、确定性来源消息和完整policy保持。
不从本机ignored run读取请求。新报告没有历史初评stage/journal，材料如实注明；不造历史回执。

| 顺序 | 新报告 | 需要观察的行为（仅Host端） |
| --- | --- | --- |
| 1 | V2 | 后文已限定全样本早死2.50/2.67，保留正确概括；措辞偏好不升级为事实错 |
| 2 | H5 | 明确中单2.50/.50被写为接近，应检出并给局部修法；不添因果结论 |
| 3 | S8 | K3被伪引为无基准固定10刀线，应纠来源归因；不连带误报正确范围句 |

预期标签、校准结果、主审意见及本方案不进入Provider消息、metadata或独立task。
标签只辅助结果对照，真实全文依据可以推翻预期，不能为获得一致而重派。

## 范围与成本边界

新run：`data/runs/model_comparison/document-full-report-initial-20261012`。
Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-initial-20261012`。
准备包：`data/evaluation/fixtures/document_full_report_initial_20261012/`。

最多3次GLM-5.3/high初评，Flash0；temperature=1.0、top_p=.95，单次600秒、输出32768，
输入预留64000。总上限290304 tokens、1800活动秒、86400 Host秒，SDK retries=0。
按现有合同单价计算，未缓存保守估价 **4.288512元**；这不是账户硬计费封顶或实际账单。
无生成、编辑、fresh、重试、重评、补发或新资格，三项独立判断均一次。

执行前必须覆盖本具体批次的成本授权、同HEAD全绿CI、clean exact HEAD、完整准备包及
即时真实主体预检。授权绑定plan SHA、HEAD、CI、预算，签发后最多24小时，不能在故障后重签重开。
执行期间不改源码/HEAD，仅一个runner。查询CI失败不等于CI失败；未知发送状态不得重启。

主审：`01a1248f-e18c-7282-92bf-7ceb2eb5dce4`；
独立：既有`/root/host_scope_calibration`，`01a12f0c-bb7c-74e3-ad92-775eefbe399a`。
独立主体曾检查这些原稿，但未接触本次Provider输出的主审意见；本包明确是熟悉来源开发诊断，
不是新盲测或holdout。当前方案不新建Agent。

## 运行与收尾

1. `prepare --directory <准备包> --root-thread-id <主审> --independent-thread-id <独立>`
   创建精确请求和材料；`verify --directory <准备包>`只读重建核验。
2. 获本批授权后，以`run --package <准备包> --authorization <授权JSON> --ci-run <同HEAD CI>
   --env-file <本地既有凭据入口> --codex-executable <指定Codex程序>`首次启动。
   使用`C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`（本机实读0.153.4）。
   不将凭据或其内容放进准备包、公开审计或子任务。
3. 实际stage到达后主审用`material --directory <run> --key <精确key>`读完整任务，
   独立只接收生成的`dispatch.txt`内精确checkpoint路径/SHA。每个stage只一次NEW_TASK；
   同task恢复用MESSAGE。独立只读该任务及固定原件，不读批次构造器/计划/校准意见来算摘要。
4. 两侧逐项核完整报告、实际来源、每项issue/advisory、解释、引用、修法及正确保留内容。
   此次均initial，`report_assessment=null`；接受实际意见不表示错误原稿已修好。
   独立恢复及final前重读同checkpoint，自己的JSON经check-answer后只发唯一多行原生final。
   主审实读原生final事件，再`submit --notes <主审JSON> --event-id <真实事件>
   --checkpoint <路径> --checkpoint-sha <SHA>`，另供directory/key/codex-executable。
   不代写、裁剪、拼终答或伪造native来源。
5. 有效语义拒绝/分歧记录后继续下个独立案例；身份、来源、native、checkpoint、协议、transport、
   预算或主体不可用为硬故障，`abort --directory <run> --key <当前key> --reason <适用原因>`停批。
   传输/协议错误由runner直接停批；尚无review-required时不伪造材料供abort使用。
6. 关闭后`replay`只读严格重建实际回执/来源/任务/native/预算/clock；`seal --output <新公开文件>`
   create-only保存白名单。保留实际calls、HTTP、known/unknown/receiptless、未发送项、最早硬偏离，
   另按逐项Host结果报告最早语义偏离。失败不能伪写strict seal，原件不改。

## 结果如何改变下一步

| 实际证据 | 决策 |
| --- | --- |
| Provider三项解释与修法均正确且真实双审成立 | 停止本包及教学/温度追加，评估当前组合更广同版本业务回归的覆盖与成本；不直接认证15例 |
| V2仍被误报，而两类真错能检出 | 据实际错误命题及全文依据定位误报准入机制，保留原有真错核查能力；不因个别措辞再叠同义教学 |
| H5或S8真错漏检，或修法产生新错 | 检查相应证据选择/来源核验/修法路径，不能用降低误报换取漏检 |
| 主审与独立分歧或与来源反证冲突 | 原样保留具体分歧及命题，不强制重派一致，不将Host一致本身当真值 |
| 传输、协议、身份或计时硬失败 | 停批，定位最早工程偏离；没有语义结果的项不计成模型误报/漏检 |

一次三例只说明该开发组，不能给出稳定率、因果结论或产品采用；正式同版本15、自然消费、8E与
Coach/Training、四块联动、Worker/DB/API/UI/journal、前端审美头像、Memory、身份运维、两树整合、
独立评估及八维学习继续保留。旧146原件/缺strict seal、历史2/15与3/15等各自独立，新资格0。

## 准备阶段验证快照（已由关闭结果取代）

离线验证记录及精确plan SHA见`data/evaluation/results/document_full_report_initial_preparation_20261012.json`。
plan SHA `66dcb5d0f9a1fe43b8cf38442f34da9e4a13e17213fbd3414c2982eba608ee0a`，
准备审计SHA `daf29d4f89882128d9357d68a1f0ccc7a61fc6fcfc32b6312506784898702c6b`。
51项相关离线检查全部通过，旧146原件摘要及库存保持。当前适配器未做独立工程Agent审查。
准备阶段Codex0.153.4只读核验当前主/独立身份及终答通路成功；旧dispatch正文不可读，
current_input_readable=false与已采用FINAL_POLICY的current_route_and_final_available=true均原样留存。
这不是新业务审查、执行时预检或未来可用保证。
准备包不是付费授权；本轮Provider0、业务submit0。当前尚未启动新run，automation保持PAUSED。
必要成本授权来自仓库`AGENTS.md`的“Honor earlier authorization for its actual target, scope and cost boundary”，
以及前一完整报告校准方案明确的新批成本边界。先完成本包可审查准备，再请求这一次新成本决定。

## 实际关闭状态

用户授权后，在冻结6265e14d与同HEAD全绿CI38226883176上首次执行。首项TCP建连超时，1次客户端尝试、known0/unknown1/receiptless1，后2项未发送，无模型输出/Host审查/新增资格；严格只读封存通过，自动任务已暂停。未重试或补发。详见[关闭结果](2026-10-12-full-report-initial-result.md)。上述准备阶段“尚未启动/待授权”仅为历史快照。
