# 文档呈现完整十五例：本批结果与后续决定

本批前三例完整成功，第四例初评因真实双审不一致被拒绝，执行器按授权停止。
新身份只读严格回放为 **3/15 validated_partial**；不是完整资格，不能与历史严格2/15拼接。
没有解决全部误报问题，未采用生产组合，8E仍未完成。

## 执行与业务结果

用户在 call_1bb7035a69a7497ea4d41440d4e7a6c2 明确允许上限；冻结提交
ffab7c1e4b1f5a2b38928a3c98f7943a9cc18ee2 的公共CI37790363878全部成功，
pytest在2026-10-08T14:57:31Z完成后，已有单次等待器启动执行器。没有第二份执行器。
方案SHA为6c9d36bb3540b17fd88d636db71ac682f41ea53754f11a36d600062b81d0d304；
原35次/3386880tokens/10500活动秒/86400Host秒上限未突破，冻结运行期间未改源码或提交。

| 案例 | 实际路径 | 全文双审及结果 |
|---|---|---|
| claim-scope:1 | 初评97/pass，issues空 | 正确全文保持，初评双审接受，完整完成 |
| claim-scope:4 | 72/needs_revision → Flash → fresh96/pass | 修复明确“所有指标均拉低”的真错；视野/早死方向正确，其他内容保持，三个阶段接受 |
| claim-scope:3 | 78/needs_revision → Flash → fresh96/pass | 修复全部五局补刀持平的真错，给8.8/6.45；保留中单8.805/9.01比较，三个阶段接受 |
| attribution:1 | 初评78/needs_revision | 正确检出伤害归因真错；对block4另一个事实问题，主审拒绝、独立接受。双审不通过，无编辑/fresh |

未执行：scope:4、scope:3、claim-scope:2、claim-scope:5、claim-scope:6、claim-scope:7、
observed:1—5。前三例逐阶段保留真实Codex native final及主审签署，
native-final-attestation-v1未放宽；不存在人工代写独立意见或换作者来求通过。

## 第四例的最早偏离与分歧

双方都认可block14把补刀和伤害差距均主要归于辅助是真错。原值计算中伤害全样本差
695.418333…，中单差669.235，角色构成只改变26.183333…，不能说是主要解释。
GLM正确区分补刀与伤害，来源根31/32支持解释及修法；不是漏检这个目标。

GLM还把block4“混合位置均值受辅助局强烈拉低”列为low/fact_error，理由是辅助视野90
使中单均值33.75升到全样本45。主审认为全文没有“全部指标”断言，明确表格与分位置
建议并未声称视野降低，因此限定具体指标可作advisory，不能升级事实错；独立审查认为
未限定指标的广义方向表述本身不准确，接受该issue。两份不同意见原样导入并保留，
主审拒绝后关闭为role_pair_host_rejected；不能写成“双审一致确认误报”。

沿既有完整上下文标准裁决，没有新增每句必须重复限定的门槛。ADR0102中用户采用标准，
以及ADR0110的2026-09-24同类全称补造失败均保留；历史不同上下文不自动证明本例结论。
本批正确控制和归因错误控制的block4逐字相同，只有block14变化，五份业务来源字段相同；
因此需区分后文真错是否改变实际含义与评审者额外补全量词，不能只按段号判标签。

完整正文和表格实际发送；system已有“不把未写出的全称…补成作者断言”及“不要把仅可选
措辞改善升级为issues”。精确回放排除了本批输入丢失、段号错映射、解析制造问题、旧意见
污染、截流和unknown usage；不能由此证明模型内部根因或JSON/Markdown因果。
表示变化本次帮助通过三个控制，但不足以满足完整十五例资格，不原样付费重跑。

## 用量、时间与封存

8次调用全部完整返回：GLM6次，输入75533/输出19525；Flash2次，输入21693/输出967。
总117718tokens，unknown0，无重试；未缓存估价1.171026元，非实际账单。
活动418.767秒，Host1882.593秒，合计墙钟约2301.360秒。两个编辑案例各自活动127.142、
110.562秒，是这两个冻结案例的整链证据，不证明自然生成或所有案例均可在900秒内完成。

188份批原件摘要及白名单公开封存：
`data/evaluation/results/golden_document_original15_result_20261008.json`，
SHA d225f75e39e850e62c7af2cefab1ec823d837e6c46fd65606e93da373d2ed4c5。
本地seal.py精确重建计划、十五请求、失败初评及真实原生事件；使用
qualify_role_observations的document-review profile严格核前三例、完整失败用量及停止边界。
原件未改；公开response剔除私有推理，未导出凭据。严格记录在
`data/runs/role_task_observation/qualification-document-original15-20261008`。

另有Host合同插曲：claim-scope:4初评独立首final误把原稿错误放进accepted=true的defects；
第二final又缺完整绑定/target确认，均未导入。作者第三final纠正完整envelope后才正式提交。
三份native原件位于本地outputs/riftcoach-document-original15-20261008/live-host，均保留。
仅本地helper后续任务说明澄清现有字段语义，没有修改冻结产品、旧task或作者原件。
这是Host执行问题，不是Provider多调用或GLM语义错误，消耗的Host时间不能隐藏。

可重现的离线比较：`python -m scripts.audit_document_original15_failure`；摘要在
`data/evaluation/results/golden_document_original15_failure_audit_20261008.json`。
它核原件封存、相同来源/引言、真实规则和表格传递、原值差距及双方分歧，Provider0。
批次关闭后已暂停riftcoach自动接续，不能重启本批或用剩余预算自动另开批。

## 下一动作与效率调整

用户指出每次首失败停下、长时间修复再从第一例全测效率低。这是把诊断与资格验收绑在
一起的流程缺陷；不以“严谨”掩饰。先离线完成成批初评诊断及失败集合回归的方案裁决，
使每次诊断能暴露全部独立案例的问题；完整同版本资格留到方案得到证据支持之后。
具体可审查设计见`2026-10-08-review-validation-efficiency.md`。它目前是方案，未执行新调用，
不修改本批首失败停止授权，也不改变产品质量标准；已有审查分歧先核清，不自动改标签。

自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/必要重做/头像、
Memory、身份运维、两树整合和八维学习继续保留原依赖。前三例成功不是这些产品结果。
