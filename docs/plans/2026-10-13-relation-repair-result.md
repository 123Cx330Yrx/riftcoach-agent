# U1/U2关系教学初评对照关闭结果

本批已关闭，候选保持未采用，新增资格0。U1两臂均获真实双审通过，没有改善证据；
U2基线漏检了第14段的真实均值错误，但独立Host在终答前发生workspace `usageLimitExceeded`，
没有native final或双审提交。按已授权硬故障停止规则abort，U2候选未发送。

## 绑定与实际执行

- 执行HEAD：`e1fff5e932dcfb36f0df17533dda34b4da101381`；公共CI `38334154675` 全绿。
- plan SHA：`2bd63a11ff50005803a746c8ecf7cc9e55d73b4c44be96cd9f04808cdc38ad2f`。
- 原授权issued_at和截止保持：2026-10-13T01:59:09.672069Z至2026-10-14T01:59:09.672069Z。
- 实际run于2026-10-13T02:30:39Z启动，02:58:09Z退出1；没有重试、补发或重评。
- 源码、固定9文件包、run外观测及原授权原件保持；冻结执行版本与后续文档提交分别记录。

| 项目 | 实际Provider结果 | 审查终态 |
|---|---|---|
| U1-baseline:initial | 95/pass，issues空，advisory 4/6 | 主审与独立Host接受；真实native已submit |
| U1-relation-contrast:initial | 95/pass，issues空，advisory 6 | 主审与独立Host接受；真实native已submit |
| U2-baseline:initial | 96/pass，issues空，advisory 7/15 | 主审拒绝漏检；独立Host额度失败，未认证、未submit |
| U2-relation-contrast:initial | 未发送 | 未评价 |

全部已发项为initial、report_assessment=null，每篇26实际段；没有生成或编辑请求。
U1两臂保持正确稿只能证明该例正确保留，advisory减少不能当作事实修法改善。

## 语义偏离与主体故障

U2第14段明确限定“四局中单”的早期死亡胜负组均值接近。来源胜场值3、2，负场值0、1；
均值2.50与0.50，差2.00次，逐行关系all_pairs=greater。全部五局的2.50/2.67是另一组比较，
因果未知也不能撤销这里的描述性冲突。主审判为missed_error；模型没有提出修法，不能把
缺失修法算作错误修法，也不能据此评价关系教学候选的修法能力。

独立任务`01a1332a-a084-70c2-b19b-757e3010c52b`确有15条公开命令且exit均0，作者JSON存在，
但真实Host记录status=failed、error=usageLimitExceeded、final_count=0。作者文件不能代替native final，
因此没有导入或补签。停止原因是Host主体可用性故障，本批三个GLM请求均完整返回，未发生旧T9式传输超时。
runner记录的first_deviation为U2-baseline/host/semantic_operator_abort；最早语义偏离另记为该项Provider漏检。

## 用量与封存

actual尝试/HTTP各3；known input39196、output6404、total45600tokens；unknown0、receiptless0、未发1。
按既定价格估算已知部分0.492880元，实际账单未核实。活动165.109秒、Host1477.500秒，在本批预算内。
三项run外无正文观测均有效并核SHA，不能据此对历史上游超时定责。

严格只读replay和create-only seal成功；2项已审真实native复核，66份run原件库存及SHA不变。
封存SHA：`b11d033fabffdec069b0d527a7ec11b55aaa1bb75e87388a6b20228494cf669d`。
旧73/47/26/14/146份原件逐项核验不变，各自认证缺口保留。严格封存不认证未审U2，也不补历史资格。

证据：`data/evaluation/results/document_relation_repair_result_20261013.json`及
`data/evaluation/results/document_relation_repair_close_audit_20261013.json`；真实事件、作者原件、主审笔记与失败记录
保存在原Operator目录。自动任务已实核PAUSED。本次收尾曾尝试委派只读核验，但委派在开始工作前因模型容量失败；
未承担任何独立审查，收尾由主执行者完成。

收尾再次通过指定codex.exe只读核验已审两项和失败turn，确认final_count0、15公开命令exit0；
封存与run原件SHA保持。`git diff --check`及`python -B scripts/check_project_governance.py`通过。
本次只新增结果和更新状态，不扩大测试或发送模型请求；`.planning/.active_plan`仍正确指向当前开发计划。

## 决策与后续

本批不足以采用或否定U2教学候选的实际表现；候选保持未采用，不授产品资格。熟悉来源并非holdout。
后续先用已有U2漏检、H5修法和完整输入做无付费方案裁决；闭批不重开，任何新付费范围须另有明确授权。
正式同版本15、自然生成/工具/编辑/终评消费、8E，以及Coach/Training、四块联动、Worker/DB/API/UI/journal、
前端审美头像、Memory、身份运维、两树整合、独立评估和学习均保留，历史库存不能拼资格。
