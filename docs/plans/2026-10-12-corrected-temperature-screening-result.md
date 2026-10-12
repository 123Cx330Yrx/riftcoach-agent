# 2026-10-12 修正控制温度筛查：关闭结果与执行修复

## 结论与产品影响

本批已硬停止，不能采用 temperature=0.2，也未取得同版本完整15或产品资格。
实际7次请求，前6项有原生双审，第7项有完整Provider回执但没有合规独立终答；余下3项未发。
停止原因是Host误读预期标签。随后严格回放另发现旧时钟回执不一致，因此**严格seal未生成**。
审查隔离问题、时钟记录问题、语义判读争议分别记录，不能归因于GLM限额或传输失败。

## 冻结执行与账目

- HEAD：`51923f4b95e0e17f6bec9aea8d622fd65e2fbce4`；CI：`38160991496`。
- plan：`1c9b0eebb5ac6a2957ccb9fc3a47369a2ea1554ab0aef20fb1051dc61c24237a`。
- run：`data/runs/model_comparison/document-sampling-screening-20261012-corrected-v2`。
- 已授权最多10次、967680 tokens、3000活动秒/86400 Host秒；授权到期为2026-10-12T18:00:00Z，未延长。
- 实际7 HTTP / 7 attempted；known tokens **117826**，unknown usage **0**、unknown send **0**、receiptless **0**。
- 原summary记录活动669.703秒、Host44102.266秒、wall44771.969秒；下述计时一致性校验未通过，不能冒充合规计时证据。
- 额度恢复接续的是相同runner和独立主体；没有重发已完成请求。此前Codex workspace credits中断与本次Provider回执分开。

| 样本 | baseline / 0.2 | 原生审查及限制 |
| --- | --- | --- |
| claim-scope:1 initial | 95/pass、96/pass | 原记录双方拒绝，指漏检；与历史accept及当前全文policy有判读冲突，保留原记录，不回填通过 |
| observed:3 final | 95/pass、95/pass | 两项双方接受，四项ReportAssessment全真 |
| observed:4 final | 96/pass、96/pass | 两项双方接受，四项ReportAssessment全真 |
| claim-scope:4 initial | 72/needs_revision、未执行 | baseline检出“每一个指标都被辅助局拉低”真错，主审接受；独立过程受标签暴露污染，未submit |
| scope:4 initial | 未执行、未执行 | 无请求，无结果 |

自动结果的`first_deviation`是硬停止：sample-4:baseline / host / semantic_operator_abort。
最早的已记录语义拒绝在sample-1:baseline，但它是有反证的Host判读，不能直接写成最早Provider语义错误。
新资格0；历史2/15、3/15、remaining11、完整15前段/后8/后4及教学对照各自保留，不拼接资格。

## 两项执行缺陷

独立任务明确要求不读预期标签。主体`01a12aba-90b1-79d1-a1ea-3764fbb1ab39`在turn
`01a12ed6-8128-7062-b5d6-93b6dd703fd9`中，为查请求摘要读了整个corrected wrapper，暴露`SAMPLES`标签。
原生命令事件`exec-b880c2fe-bd1b-48bc-905b-6199402bf0f2`在语义commentary之后、check-answer与认证终答之前。
即使结论已形成，commentary也不能代替独立final；按原边界abort，未补签、换主体重评或续发。
incident审计仅保存相关公开消息和命令事件，不导出私有推理。

严格只读replay依次核验了6项真实native提交、7项回执和账目，最终在时钟门报
`semantic_clock_inconsistent`。sample-3:baseline的finished回执活动差与等式残差为+0.015/-0.015秒，
sample-4:baseline为+0.046/-0.046秒，超过未修改的0.01秒容差。
生产者先取`finished`，后又用`self()`另读一次时钟；线程调度跨tick时两个字段描述不同瞬间。
用每次调用递增0.05秒的时钟对冻结版本复现了同类矛盾；修正版本残差为0。
这证明软件机制，不证明原机器当时具体是哪次调度造成延迟。

本次修复仅影响后续记录：waiting、finished和summary各自用同一次时钟观测计算相关字段。
严格消费者、预算、原始回执、已提交裁决和旧run均未修改。旧回执无法追溯恢复同一时刻，
因此不放宽容差、不开后门封存，也不宣称本批严格replay/seal成功。

## 全文判读反证

claim-scope:1与claim-scope:4的事实、知识、用户原话、确定性来源和实际policy完全一致；
正文只改block4末句，由泛指“混合位置均值受辅助局强烈拉低”变成明确的“每一个指标……包括视野和早死”。
两稿block14都明确全样本早死2.5/2.67。policy甲1允许后文消解范围，乙1禁止把泛指补成全称；
乙2要求拒绝明确全称。首对旧审查却把邻近中单语境视为不可由后文消解，构成共享判读错误的具体反证。
本轮没有重评或替换首对认证记录，也不能用后续主审接受来覆盖旧裁决；结论是其温度质量解释存在争议。
尚无足够合规配对证据证明降低温度解决共同语义问题，不继续购买相同筛查或靠提示微调重置失败历史。

## 核验入口与后续执行方式

新增`python -m scripts.verify_host_review_artifacts --checkpoint <精确路径> --checkpoint-sha <精确SHA>`。
它只读取该checkpoint、task及同目录issued-request/response/stage：请求与响应按原始文件字节算SHA，
报告按原文算SHA，stage按现有稳定投影算SHA。不加载批次标签配置，不搜索其他任务，
不输出意见、不写原件、不授予语义或native认证。已对本批未认证第七项实读验证摘要一致；这不补回其资格。
现已在实际`observe`生成dispatch时先调用校验，再给出该精确命令；若不匹配，在创建dispatch/Host等待前停止，向operator报具体绑定错误，不让盲审者自行翻批次配置。semantic和sampling未来plan的source清单均已纳入checkpoint与校验器，旧计划不重建覆盖。
全文material/policy阅读、作者check-answer、原生事件submit仍不可省；此helper也不能阻止有全文件权限的主体主动越界。

下一工作包先解决盲审执行的可操作边界和上述全文判读争议，完成无付费干跑与独立检查后，
再提出能区分剩余解释的具体验证方案。不得重开本批、补发后三项或沿用污染主体认证新任务。
正式同版本15、自然消费、8E、Coach/Training、四块联动、Worker/DB/API/UI/journal、前端审美头像、
Memory、身份运维、两树整合及八维学习均未完成，原依赖保留。automation保持PAUSED。

### 本次接线与后续技术决定

对未认证第7项的固定checkpoint运行新dispatch命令，request/response/report摘要核验成功，
stage投影与pin task一致；全部146原件前后SHA一致，Provider0、审查0、native认证0。
只读干跑记录位于operator的`dispatch-wiring-offline-audit.json`，
SHA `35931d80278904cb1ac488573c6d09d225711215dc8037e509b9823a2749fc63`。

前提交`bfd68cbf`/CI`38215203511`四个pytest分片均在remaining4历史测试setup报
`remaining8_frozen_program_changed`；打包、DB迁移、web检查通过。旧测试拿当前源码去核旧封存，
时钟修复后自然不匹配。测试现以提交内核过旧seal/LF摘要的历史源码资料构造临时快照，
沿用仅限该临时目录的旧换行投影；当前执行代码继续独立测试，生产SHA门不改。
另加当前新代码及未投影LF副本仍被生产prior拒绝的反例，不宣称旧批可在新HEAD严格回放。

这次明确选择：保留已有完整来源和业务policy，不再添加同义教学或重买原五对温度筛查。
先校准Host如何应用现有规则，再决定Provider机制试验是否有可判定的真值。
后续新校准需将“后文明确消歧”“明确全称与事实冲突”“全文仍有实质歧义”分开，
主审与新独立主体各自引用完整来源和实际policy，记录所判命题及可核事实冲突。
若只剩措辞偏好，不升级事实门；若仍无法一致适用既有规则，保留未决并停止据此选温度。
这些是新流程验证的判定分支，不是对旧六项的重新裁决或未来通过承诺。
现有helper只减少查源码的必要，不具备操作系统文件隔离能力，也不能证明Host今后不会越界。

## 证据与检查

公开事故审计：`data/evaluation/results/corrected_temperature_screening_close_audit_20261012.json`，
SHA `862367d9ef801651f065720b97573e73bc7000c2e03dc54022337b3c57ca0aba`；明确标记strict_replay=false、strict_seal_created=false。
146份原文件SHA清单前后相同。完整原件仍在本机run；事故审计不是严格seal的替代品。
在冻结提交复现旧回放需使用上述HEAD的代码；新时钟修复不回迁旧计划的source SHA。
operator目录：`C:/Users/33502/Documents/Agent/outputs/riftcoach-corrected-temperature-screening-20261012-v2`。
时钟/新核验入口/原checkpoint相关33项、筛查及提交封存链回归17项通过，共50项。
治理和`git diff --check`通过；没有因本次修复重发Provider。CI仅作代码回归，不弥补本批strict seal或产品资格。

本次实际接线/checkpoint/semantic/sampling回归54项通过；修复后的remaining4/8历史回归17项通过，共71项。
初轮因旧dispatch替身报TypeError、历史夹具尝试重建混合换行失败均已定位修复；最终分组退出0。
两类未来plan已实建并确认新helper/source绑定，未创建业务run。治理及diff检查通过；新提交公共CI待核。
