# 六次职责对照关闭结果

2026-10-14。**第二次请求HTTP429硬停止；职责分离假设未检验，核心语义问题未解决。**
本批不重试、补发或续跑。automation已设PAUSED并实读确认，不另开付费批。

## 执行与语义结果

执行HEAD `85a37432a7b1613f13de9ca527379cb37dba17d9`，公共CI `38433654680`全绿。
原授权签发UTC2026-10-13T16:45:50.259394，截止24小时未延展；SHA
`0d55955473cda11babb2928b8fc945ac93c4eb9fcea2259cabea46aba2014e6a`。
plan `f2ebfd7b7e1193d6143a21591d36450a1d6e8c38065f177dcc383b7d30da712b`，唯一run
`data/runs/model_comparison/document-review-duty-20261014`，runner退出1，UTC17:43:46关闭。

| 项目 | 实际结果 |
|---|---|
| duty-1-full:initial | 完整响应82/needs_revision；主审与原独立主体真实native均接受意见，submit成功 |
| duty-1-facts:initial | 1次HTTP429；worker8.703秒失败，无模型流式事件、有效回答或usage |
| duty-2-full/facts、duty-3-full/facts | 全部未发，无业务审查 |

第一项实际报告25块、report_assessment=null。正确检出“每一个指标均被辅助局拉低”的真错：
视野分与早死反而被拉高，补刀/经济/伤害降低；修法与来源支持一致。
全文限定下的早死摘要没有被误报；解释、实际建议、修法范围及正确内容保留获双审接受。
接受初评意见不表示错误报告已被编辑修好。本轮full未复现旧误报，facts无回答，
所以不能证明改善、否定候选的语义能力或解释模型内部成因。熟悉来源非holdout，无新资格。

第二项有效无正文观测记录status429、raw_bytes84、eof/closed真；有效观测不等于请求成功。
无错误正文/provider code可供区分限速、配额或其他原因，具体上游原因undetermined。
最早硬偏离是该项transport/ProviderResponseError；不是600秒截止。

## 用量、封存与保全

actual/HTTP各2；HTTP发送未知0，known17250tokens（12953输入/4297输出）、unknown_usage1、
receiptless1、未发4。已知部分按输入8/输出28元每百万估价0.223940元；失败调用用量与总账单未知，不能填0。
活动79.953秒、Host484.203秒、墙钟564.156秒。无重试、补发、编辑、fresh或资格。

统一入口只读replay及create-only seal通过，1项真实native重取验证，作者JSON与导入意见相同。
checkpoint SHA `9e0e2dbec34c747d91ec2bfadeb6e2405bba782e7ceeb6d0aa010e6df4d6a750`；
event ID与完整SHA库存见关闭审计。34 run原件+8外部观测+1作者共43文件，封存前后库存与SHA不变。
13件执行包、全部冻结源码、原7件授权输入保持；另核8个旧批760原件、53份full-chain源码和旧readiness不变。
历史缺口与原分歧不补签。原15单run实际302原件，计数以审计逐批清单为准。

- [严格封存](../../data/evaluation/results/document_review_duty_result_20261014.json)
- [关闭审计与逐批SHA](../../data/evaluation/results/document_review_duty_close_audit_20261014.json)
- [原方案与反证条件](2026-10-14-review-duty-design.md)

执行前64项离线/相关回归及该执行HEAD公共CI通过。本次收尾仅增加证据和状态文档，
运行治理、JSON/链接与diff检查；不把执行HEAD绿灯当收尾HEAD的CI结果。

## 技术决定与后续

保留职责分离为未检验假设，不接入生产，不重启15。先只读核对已有服务端可用性/限额证据；
无证据则明确未知，不通过付费探活补齐本批。新实测须另有具体方案与授权，旧批永不续跑。
若后续有正向差异，仍须验证互补职责、真实编辑消费及5到7调用的完整合同，局部pass不能替代产品pass。
正式同版本15、自然Coach/Training、四块联动/journal、前端审美头像、Memory、身份运维、
两树整合、独立评估与学习仍保留，8E未完成。
