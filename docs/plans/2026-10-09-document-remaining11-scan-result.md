# 剩余十一例初评集中扫描：已完整执行与封存

本批十一例全部发送、完整返回并完成真实全文双审；十例接受，一例保留分歧。
`scan_completed=true`，`diagnostic_accepted=false`。它证明集中诊断路径实际走完，
没有认证任何原稿修好，也没有新增完整十五例或产品资格。

## 执行与用量

用户“确认，继续”授权冻结方案 `d5aa7c914cb9b30d66422a28c83736afc1cc79313fc32be2d4feced1b73429bf`。
原提交4749c230公共CI一小时超时，后两次CI-only恢复过程及原件保留，未有Provider发送。
模型依赖、业务身份、全部input/report/request、预算和计划未变；恢复目录`ci-recovery-3`
透明记录新执行HEAD `3f3669b98a0db3852944cad7bf3b582a57bd0bbb` 与同提交
[公共CI37823755271](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/37823755271)。
公共四分片及全部非pytest门成功，汇总5983父节点完整终态、165父skip、129子结果，
`exact_full_coverage=true`；该工程结果不是语义质量证明。

唯一等待器46924及执行器45300首次执行，运行期间未改冻结源码或提交。
Provider GLM-5.3/high共11次，Flash0；输入145713、输出34674，合计180387tokens，
未知用量0、无receipt本地尝试0，所有11次有真实transport回执。活动483.233秒，
Host双审等待2138.189秒，墙钟2621.422秒。保守未缓存实际用量估价 **2.136576元**，
不是厂商账单；上限11次/1064448tokens/3300活动秒/86400Host秒/15.724544元均保持。
无重试、编辑、fresh或重评；无未审/未执行尾例，exit_code=0仅表示扫描正常完成。

## 十一例分别怎样

| 案例 | 初评 | 业务判断 | 双审 |
|---|---|---|---|
| scope:4 | 70/needs_revision | 正确检出block14明确中单口径早死2.67真错，中单败均0.5 | 接受 |
| scope:3 | 72/needs_revision | 正确检出block4明确中单近似真错；修法“未带来胜利”有分歧 | 主审接受 / 独立拒绝 |
| claim-scope:2 | 96/pass | 全样本2.5/2.67与中单2.5/0.5明确分别陈述，正确控制 | 接受 |
| claim-scope:5 | 95/pass | 辅助拉低CS、提高视野/早死的方向正确，正确控制 | 接受 |
| claim-scope:6 | 80/needs_revision | 口径未定却断言CS持平的真错正确检出 | 接受 |
| claim-scope:7 | 96/pass | 条件性分别描述中单/全部五局CS，正确控制 | 接受 |
| observed:1 | 96/pass | 完整正确稿、样本内逐局差异/归档快照/观摩训练边界保持 | 接受 |
| observed:2 | 72/needs_revision | 样本正确关系外推为未来所有对局的真错正确检出 | 接受 |
| observed:3 | 72/needs_revision | ShowMaker数据错归阅读者本人的真错正确检出 | 接受 |
| observed:4 | 88/needs_revision | OP.GG检索时间错作官方补丁发布日期的真错正确检出 | 接受 |
| observed:5 | 88/needs_revision | 标题声称证明防抓能力的真错正确检出，正文限制不能撤销 | 接受 |

四份正确稿均pass且>=85；七份带错稿均needs_revision，并检出真实目标。
其中scope:3的检错/解释双方都认可，质量分歧只在建议修法。不能把正确verdict当作
初评全内容合格，也不能把带错原报告当作已经被修复。

## 分歧和Host执行插曲

scope:3的来源中单胜早死(3+2)/2=2.5，败(0+1)/2=0.5；全样本败均2.67。
Provider修法写“本样本中更少的早期死亡并未带来中单胜利”。主审按全文认为这是
受本样本限定的观察性否定，接受初评；独立作者认为“带来”暗示因果，作wrong_correction
拒绝。两份真实意见原样导入，没有重审求一致、换作者或人工改Provider回包。
语义分歧正常记账后，仍执行剩余九个独立初评；资格验收的首失败规则未修改。

独立Host scope:4前两份final抄错绑定hash，claim-scope:5首final审查说明串入上一例
中单早死2.5/0.5比较，均未导入。作者核原件后更正完整final，未变accepted观点；
14份真实native final本地原文保存，包含11份导入和3份未导入。修正这些Host材料
没有Provider调用，没有覆盖原件；不能把Host时间隐藏或说成模型故障。

## 原件和回放

批目录：`data/runs/model_comparison/document-initial-remaining11-scan-20261009`，已关闭，不重开。
公开封存：`data/evaluation/results/golden_document_remaining11_scan_result_20261009.json`。
SHA `8adfa5cea9b56c063ffb0340b726c55d4c3effbfe86c54738d492f48b00c6baa`。
191份原件摘要、90项白名单JSON；严格重建全部精确请求、来源、stage、结果及真实native事件。
公开不含Provider私有推理、stream或凭据；14份Host原final留在本地outputs的live-host。
操作/原授权/恢复/退出及主审notes位于
`C:/Users/33502/Documents/Agent/outputs/riftcoach-document-remaining11-scan-20261009`。
自动接续已暂停；未借剩余预算自行另开批。

六个scope/claim-scope案例除report source_index外的全部来源严格相同；五个observed
案例共享另一完整来源组。每例实际报告及全部初评仍全文读取，不用段号标签代替审查。
来源组摘要见本地`source-groups.json`；实际helper逐例重建来源与原件一致。

## 这批怎样改变下一决定

旧四例与这十一例独立保留，不能合称同期十五例通过率。历史严格2/15、旧文档批3/15
不相互拼接，本批新增资格0；自然消费、review-controls与8E仍未完成。
新发现将后续修复焦点收窄为两个解释边界：旧attribution:1的泛指均值是否补成全称，
和scope:3修法中的样本描述是否写成因果。其余新十一例未暴露漏检/错verdict。
不把这点当通用稳定率或旧第四例已修复；不原样重买完整15。
独立设计复核最初推荐新增每段范围账本；核ADR0116的最终adoption decision后撤回。
不复活已否决的全段解释/自选scope_checks完备性门，也不由单次合法结构推导语义正确。
现有policy已经明确泛指不等于所有指标、样本重分组不等于因果、修法不得扩展未经确认
的断言；当前证据更支持执行裁决不一致，不能宣称补一条提示即可修好。
已用完整来源及九个前瞻性成对控制校准两个Host裁决边界；主审先留意见，再交既有独立
作者分别判断，八项一致、一项C06分歧原样保存。独立解释确认最窄样本描述有来源；
自动关键词门不能冒充发现新来源矛盾。校准不改旧封存或资格，不向Provider注入Host标签。
详见2026-10-09-host-boundary-calibration.md；没有已采用的模型语义修法。
仅近义提示、改正确原稿、人工删issue、放宽双审或增一次重评都不作为本次修法。
只有针对已知失败集合的实证支持后，才冻结下一份同版本完整十五例；本批未提供编辑
或fresh证据，不能以十例初评接受或离线Host校准替代这项前提。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/必要重做/头像、
Memory、身份运维、两树整合和八维学习继续沿原活动计划依赖。
