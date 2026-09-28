# 1.5.5 首批结果与人审提交前修复

## 实际结果与责任

用户批准的完整15批次68ba8615…27fd，在29fce323、CI36400549646三项success后执行。
CI公共pytest5301 passed / 163 skipped / 129 subtests，不能当作模型质量证据。

1. claim-scope:1：GLM96/pass，全文上下文明确范围，原文保持且双方来源审查接受。
   实际连续任务116.672秒、13569tokens，严格授予本例资格。
2. claim-scope:4：GLM80/needs_revision，正确指出“全五场每个指标都压低”错误。
   Support让输局视野34→52.67、早死0.5→2.67升高，而补刀、经济、伤害降低。
   模型说明与修法正确；独立意见漏target_and_correction_valid，主审未发现，提交器未拦截。
   消费门以role_observation_initial_correction_not_accepted停批；没有Flash编辑或fresh。

第二例是host提交合同缺陷，不是新的语义误报。不能把正确初评算成完成、不能把缺字段
推给模型，也不能给原失败回执补写True。主Agent负责最终提交核对与软件入口完整性。

## 根因与修复范围

同一记录的生产者与消费者要求不一致：草稿只校验结构，formal builder只部分校验独立意见，
消费门才要求显式纠错确认或全部全文检查通过。缺失字段到不可逆submission之后才暴露。

- 复用同一_review检查确认草稿与formal builder：StageAssessment约束accepted/defects，
  accepted真错初评要求布尔True（缺失/False/1均不接受）；正确初评及编辑/终评要求匹配全文SHA
  和四项ReportAssessment全True。明确拒绝意见仍可提交停批，未确认草稿可保留未决意见。
- 主审真错初评也必须显式True。其余主审检查继续经过已有StageDecision/Observer。
- formal builder核独立来源、阶段、报告、输入绑定；legacy可选raw字段一旦提供，必须与
  实际transport ordinal请求/响应和journal输入匹配，不能拿意见自己的值自证。
- 检查发生在append submission或写primary/decision之前；保留原消费门、竞争/中断/恢复检查。
  没有修改产品提示、模型/high、标准或预算。新代码不会凭解释文字自动推定已确认。

## 证据与资格

公开封存：data/evaluation/results/golden_boundary_examples_qualification_result_v1.json，
SHA256 7aa34d62e42379e53985a713319b45ec937514025f85da9ab3673170249d99c2。
对应audit_v1.json严格为1/15。2次请求24477输入+5205输出=29682tokens，unknown0，
含host357.719秒，未缓存已知估价0.341556元非账单。60原件逐一校验，修前修后完全不变。

旧完整15准备保留原code hash，仅只读预览；实际模型请求、来源、身份、预算全部重建比较。
历史首例仍能通过严格回读，失败后缀不授资格。已关闭批既检查原件目录又检查公开封存，不能重开。

验证包括缺失/False/1、意见矛盾、报告false、foreign hash、legacy raw三字段篡改、旧坏草稿、
显式拒绝、正例不要求纠错确认、partial write/race、真实执行器网络替身及严格15结构审计。
离线15结构通过不等于真实15质量通过。最终验证数量以progress.md本次记录为准。

## 具体下一执行与授权边界

复用scripts.run_boundary_examples_qualification --remaining及既有execute_prepared，
冻结golden_boundary_examples_remaining_preparation_v1.json，方案
8eff6222693f61c04479ba8d3d875328de65dd0a199b5ef4e67eee747188f038。
14例实际请求等于旧15去掉已通过首例；身份相同。claim-scope:4从初评重新完整执行，不借旧初评。
执行前严格审全部旧原件确认只有首例可用，再验证新冻结plan、同HEAD公共CI和干净checkout。

新批最大34调用（Flash10、GLM24）、3290112tokens、10200秒含host，未缓存预留估价
35.737600元。旧2调用保留，合计最多36，超过原35；累计10557.719秒超过原10500秒。需要新的明确预算决定，当前未授权/未调用。
首个实质/合同错误即停，无重试、重评或自动新批。成功后用已有严格审计合并同身份连续证据。

完整15合格后才验当前组合自然Agent工具/生成/纠错及真实Worker/DB/API/Workbench消费。
8E未完成；四块联动、本人训练、前端审美/必要重做/头像、Memory、身份运维、两树整合与学习
仍在活动计划。人审提交修复与本批初评证据不等于Agent整体交付。
