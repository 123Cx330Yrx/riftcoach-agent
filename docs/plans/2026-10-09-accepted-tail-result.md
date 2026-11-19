# 六例尾链诊断：首案独立审查绑定硬故障，已关闭

本批只完成首案Flash编辑返回，未取得当前任务的有效独立全文审查。
按已授权硬故障边界全批停止，未发fresh及其余五案。它没有提供新增双审尾链质量或资格。
现有绑定校验拒绝了旧批意见，未把旧成功借给本批；当前下一工作是免费定位任务交付。

## 执行与用量

用户明确允许方案`33ce91c802bea1eb0c247fea85d9fc988ca616cdf32869730f913a176caab8ce`，
最多12新调用、1161216tokens、3600活动秒、86400Host秒；语义拒绝仅停该案，硬故障停全批。
原dd870b63/CI37875366571在Provider0时因离线测试依赖本机run取消；CI资料修复保持模型
冻结源码diff0及原计划不变。执行HEAD为`62154124488bf35369cd0d78ad9c37875fdf6067`，
[公共CI37876307787](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/37876307787)
各门全部success。唯一等待器实际PID48292，runner包装PID4956首次执行，运行期间clean exact HEAD。
两者已退出，execution/exit.json记录exit_code=1；`riftcoach`接续已确认PAUSED。

| 实际账目 | 数值 |
|---|---:|
| Flash编辑 / GLM fresh新调用 | 1 / 0 |
| 输入 / 输出 / cached tokens | 10824 / 917 / 0 |
| known tokens | 11741 |
| unknown usage / 无回执本地尝试 | 0 / 0 |
| 活动 / Host等待 / 总墙钟秒 | 24.359 / 803.266 / 827.625 |
| 按实际已知用量估算的未缓存费用 | 0.0112268元 |
| 已认证阶段 / 完成案例 / 新增资格 | 0 / 0 / 0 |

费用是合同价格估算，未核账单。唯一call-001有真实transport回执；没有SDK重试、重评、
关闭批重开或新的Provider批。仅一份已接受历史初评实际注入，不是新调用或新初评认证。

## 改文、保留内容与fresh分别判定

`scope:4`唯一替换block14。原中单口径败局早死2.67错误，编辑明确中单败局0和1，
均值0.5；胜局3和2，均值2.5。原全样本胜2.5、败2.67作为另一个正确口径保留。
“不能据此解释胜负”仍为证据不足以确定原因的边界，没有新增胜负因果结论。

已保存的主审全文意见接受该改文及reason，四项ReportAssessment为真：核算其他块的
逐局/位置/全样本数据、伤害和补刀解释、身份/未知目标、知识引用、日期和来源限制，
未发现正确内容丢失或新错。该意见先于独立答复保存，是主审暂定判断。
它没有通过本批双审，不认证修复合格；fresh完全未执行，pass/分数/误报漏检均未知。

## 最早偏离与原生取证

当前期待`scope:4`/方案`33ce91c8…caab8ce`/revision，helper精确task文件已保存。
独立新完成turn却回答旧`claim-scope:4`/方案`b2eb550d…5261b7`，并返回旧格式的review。
该结果不是旧mailbox通知误看：通过安装Codex只读API读取最新completed turn的真实final，
再次调用`CodexHostReviewEventSource.fetch`，真实失败为
`codex_review_host_dispatch_or_answer_binding`。

- independent：`01a0ebaf-790b-70b2-9f02-9e354d9ea50b`。
- turn：`01a11eaf-fb13-7910-82e2-29ee7ab7f47b`。
- final：`msg_0f1ffc23fbabd630016ac85ee110d08191b199b56428748f26`。
- dispatch：`amsg_01a11eaf-fb3a-7c22-b067-ba3b6ae15e2b`，内容opaque。

真实主体谱系和native-final路由预检通过，只证明当时可读和主体正确，不能保证随后
回答当前任务。当前可以确证答复绑定错批；不能区分实际派发内容错配与作者沿用旧任务，
也不能断言加密导致该故障。未读取或公开私有推理，没有改写独立意见、绑定或事件。
Provider编辑完整返回，首次可见偏离发生在Host独立审查答复，而非GLM/Flash业务响应。

## 关闭与封存

有效submit所需的native fetch已实际拒绝，未导入有效审查；现有runner无独立operator-abort接口，等待文件
仅接收review-submission.json。操作员保留真实错误final，发布明确标为
`operator-invalid-native-binding-stop-v1`的无效失败交接。它附真实主审意见及原样错误
答复，故意不提供有效独立attestation；先离线确认既有validator会拒绝，然后原子发布。
runner自身校验抛`coarse_diagnostic_host_binding`，走原finally记录账目/时钟/未执行案并关闭。
这不是成功submit、有效语义reject或伪造native事件。跨盘hardlink发布曾失败，未写入
run；随后在同一D盘以相同原字节原子发布，不涉及Provider重试或原件修改。

`scripts.seal_document_accepted_tails`只读重建来源、历史注入journal、真实编辑请求/响应
及账目通过，create-only封存21份原件SHA、8项公开白名单JSON、已认证阶段0。
无效review-submission/host-reviews只保留原件哈希，不公开未经认证的Host正文。
结果原件、Provider回执、stage/journal未修改。封存写出首次因误选不存在输出目录失败，
修正为既有results路径后成功；不影响只读回放或原件。

公开文件：

- `data/evaluation/results/golden_document_accepted_tails_result_20261009.json`，
  SHA256 `cd3cbe29a9d27ff09dfe560d6272a40f67f54a8e83e6138a0b5ae6a4734c5f4c`。
- `data/evaluation/results/golden_document_accepted_tails_native_failure_20261009.json`，
  仅公开预期/实际绑定、真实事件引用和本地证据摘要，没有替代native原件。

本地operator目录为`C:/Users/33502/Documents/Agent/outputs/riftcoach-document-accepted-tails-20261009`，
含授权、CI恢复/成功、预检、进程退出、精确task、主审notes、真实native failure与停止决策。
真实run为`data/runs/model_comparison/document-accepted-tails-20261009`。

## 未执行与下一决定

`scope:4` fresh未发送；`claim-scope:6`、`observed:2`、`:3`、`:4`、`:5`全阶段未执行。
六尾链覆盖仍缺有效双审编辑/fresh。先免费定位当前任务交付，证明精确绑定可达，
避免继续付费定位Host故障；没有明确机制证据时不猜修法、不修改模型policy。
当前关闭批不能重开，剩余预算不能转成自动新批，不重新审查来求通过。

两处初评分歧`attribution:1`、`scope:3`原样保留，不下传。旧文档3/15与另一身份历史2/15
各自保留、不拼接；正式同批15、review-controls、自然产品消费及8E仍未完成。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/重做/头像、
Memory、身份运维、两树整合及八维学习保持活动计划依赖。

收尾只改状态/计划/结果文档和公开证据，不改冻结模型源码、Provider原件或主树前端。
真实只读封存回放、原件摘要一致性、治理检查及git diff --check通过；未为文档改动
重复21项已通过工程回归，也未启动新Provider验证。
