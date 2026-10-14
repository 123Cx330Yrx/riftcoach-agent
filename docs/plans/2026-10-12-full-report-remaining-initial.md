# 未发送两稿的初评诊断

## 当前问题和选择

原三稿要区分正确概括、明确范围错误和伪造来源。V2已有一次97/pass的Provider输出，
但独立主体在读取前误用目录而终止，旧批已封存，不能补签或计通过。
H5/S8始终未发送。本包只首次观察这两篇的实际审查意见、解释和修法，
避免再购买V2；结果也不能拼成完整三稿或正式15通过。

主线的证据门不变：不得为减少误报而漏掉真错，也不能给错误修法放行。
若两篇的实际解释和局部修法均正确，则结合仍缺V2认证的事实决定更广同版本回归覆盖；
若出现漏检、错误解释或越界修法，按完整来源定位相应机制。有效语义拒绝继续下一独立案，
工程硬故障停批。不据此前目录故障更改教学、温度、来源或600秒时限。

## 固定范围和费用

- 入口：`python -m scripts.document_full_report_remaining_initial`。
- 包：`data/evaluation/fixtures/document_full_report_remaining_initial_20261012`。
- run：`data/runs/model_comparison/document-full-report-remaining-initial-20261012`。
- Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-remaining-initial-20261012`。
- 顺序：`report-H5:initial`、`report-S8:initial`，各一次；V2不在包中。
- 最多2次GLM-5.3/high，Flash0；temperature1.0/top_p0.95，输出32768/次、单次600秒、SDK retries0。
- 总上限193536 tokens、1200活动秒/86400 Host秒；未缓存保守估价 **2.859008元**，
  不是账户硬计费封顶。旧批用量和unknown1各自保留，不从原授权扣除或继承余量。
- 无编辑、fresh、重评、重试、补发或新资格。两份request/material与旧准备包逐字节一致。

## 交接如何避免目录假设

复用原完整报告builder/runner；只对本新入口私有的checkpoint模块加路径前缀，
不修改冻结helper或旧源码。实际observe生成dispatch时，核repository root和当前Python
存在，输出明确绝对cwd/Python，并将生成命令中的python换为绝对可执行路径。
旧checkpoint摘要、全文task和artifact校验仍先执行，失败不发布dispatch或进入Host等待。
主审完整原样转交这份dispatch，独立不得追加backend或寻找其他任务。

前轮中性探针已由相同独立主体真实执行5条公开命令、两次读同checkpoint、自己check-answer、
唯一native final，未调用项目模型或重审旧报告；证据固定为
`data/evaluation/results/host_explicit_cwd_probe_20261012.json`。
这只证当前明确路径可启动，不证明未来可用或长文审查正确。

## 授权、审查和停止

新授权类型`document-full-report-remaining-authorization-v1`，须覆盖本具体两次范围、
绑定精确plan、同HEAD全绿CI和24小时时限。clean exact HEAD、包未变、新run不存在、
即时真实native预检及明确路径检查通过后，唯一runner首次执行。目录和代理配置不自动改动。
旧授权无效；“继续准备”不视为旧批故障后继续消费的授权。

主审`01a1248f-e18c-7282-92bf-7ceb2eb5dce4`；复用`/root/host_scope_calibration`
（`01a12f0c-bb7c-74e3-ad92-775eefbe399a`），不新建Agent。
沿用[完整报告初评审查合同](2026-10-12-full-report-initial-diagnostic.md)：material读取
实际完整stage/request/response、18实际段号报告、全部来源/policy；逐项核命题、范围、
引用、解释、修法和正确保留内容。独立只收精确checkpoint/SHA及明确启动路径，不收主审、
标签、校准意见或批次代码。每stage一次NEW_TASK，同task恢复仅MESSAGE；恢复及final前
重读同checkpoint，独立自己check-answer后唯一多行JSON原生final；主审实读原生事件后
submit，必含event-id/checkpoint路径/SHA，指定Codex0.153.4读取程序。
均initial，report_assessment=null；不把带错原稿当已修复，不将泛指补成全称，不升级措辞偏好。

语义拒绝/分歧有据记录后继续独立案；身份/来源/native/checkpoint/协议/transport/预算/
主体硬故障停整批，不换人补签或重发。关闭后严格只读replay、create-only白名单seal，
实核native、原件SHA、实际调用/known/unknown/receiptless、未发和最早偏离，更新状态并提交。
旧26/14/146原件及各自缺口保留；历史库存不拼资格，正式同版本15、自然消费、8E及既有
Coach/Training、四块联动、Worker/DB/API/UI/journal、前端审美头像、Memory、身份运维、
两树整合、独立评估和学习依赖保留。

## 准备证据

精确plan SHA、逐字节比较、离线实际dispatch路径/停止/只读封存和主体预检结果，
记录在`data/evaluation/results/document_full_report_remaining_preparation_20261012.json`。
准备不产生Provider调用或业务submit；同HEAD公共CI在提交后确认。

准备plan SHA `ca02d0de57430af4bd7cf64b66ab730ad231e9782bf9e3e0487ee016f2de394a`；审计SHA `dfb22dd75d737112e38145e3417f4a4bb492d14b55f058fa015abe7c9fdeb9be`。原入口14项与新入口5项相关离线检查已通过；首轮旧替身的python字面断言不适用绝对命令，已在新私有替身修正，未改旧测试或放宽产品门。26+14+146旧原件/库存和冻结源码保持。原主体当前native只读预检通过，current_input_readable=false/current_route_and_final_available=true，不保证未来可用；未新建或派发Agent，Provider0/业务submit0。

## 实际关闭状态

用户确认后本批已执行2次；H5双审拒绝错误修法，S8返回未派审。run多出作者答案文件导致strict seal失败，47原件保持；无重试、补签或资格。自动任务PAUSED。以上准备状态仅作历史，详见[实际结果](2026-10-12-full-report-remaining-result.md)。
