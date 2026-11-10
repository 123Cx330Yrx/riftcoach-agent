# 未发送两稿初评的实际结果与停止记录

本批模型请求均正常返回；H5的错误被检出，但修法加入了错误的样本结论，真实双审一致拒绝。
S8已返回但未派审。收尾发现独立作者答案写进只允许固定文件的run目录，严格封存失败。
这是我方交接/工作区约束缺口，不是代理、额度或Provider传输事故；不删除额外原件补造成功。

## 版本、用量和执行范围

用户确认后，冻结 `ceb3a5add6eeee6fc0648a1b2ac2e1b27e194798`，同HEAD CI `38240151033` 全绿。
plan `ca02d0de57430af4bd7cf64b66ab730ad231e9782bf9e3e0487ee016f2de394a`。
唯一runner111236从UTC11:38:16.479运行到11:50:02.084，exit1；源码/HEAD运行期间未变。

| 项目 | 实际结果 |
|---|---|
| H5 | 82/needs_revision，B4 issue、B4 advisory；一次独立全文审查、一次成功submit，双方wrong_correction拒绝 |
| S8 | 74/needs_revision，B13 issue、B4 advisory；有完整返回/receipt，无主审全文结论、无独立派发、无submit |
| 调用 | 2 GLM / 0 Flash，2 HTTP，未发送项0；未完成双审项S8 |
| 用量 | input26595/output7288/cached0；known33883，unknown0、receiptless0、HTTP-send-unknown0 |
| 合同估价 | 0.416824元，按input8/output28元每百万tokens；实际账单未核 |
| 时间 | 活动143.625秒、Host554.703秒、wall698.328秒；严格replay未走到时钟门，不能宣称时钟已严格认证 |
| 资格 | 新增0，不拼V2/三稿/正式15 |

## 有效语义发现

H5明确写“仅这四局中单”的早死胜负均值接近，实际为2.50/.50；后文全样本2.50/2.67不能撤销这个明确范围错误。
Provider定位、数值与主要解释成立，且没有把混合均值泛指补成每一指标都降低。
问题在修法另加“因此在本样本中早死次数并未把胜局与负局分开”：中单胜场3、2，负场0、1，
两组逐行无重叠，computed all_pairs=greater。无法推因果不等于没有描述性区分。
双方均逐项核全文及全部来源后判wrong_correction，而非因某个词不喜欢或双方一致就定真值。

H5原生事件：`01a12f0c-bb7c-74e3-ad92-775eefbe399a/01a12feb-40f3-7c21-9f71-1e7dfa8a98db/msg_0998f8ac4632b025016accc878195881948d0f10ea555ed46e`。
16条公开命令全部exit0；精确checkpoint重读、作者check-answer和唯一native final已实核，作者JSON与native相同。
主审意见先于读取独立终答保存，未把主审意见发送给独立。初评report_assessment均为null。
S8输出报告了K3固定10刀阈值的伪引并提出删除；此处只报告Provider返回，不把它算双审通过。

## 工程偏离与封存边界

最早库存偏离是独立在H5 run子目录写入 `independent-answer-01a12f0c-bb7c-74e3-ad92-775eefbe399a.json`。
既有dispatch要求写作者答案并check-answer，却没有指定run外工作区；离线Host替身直接生成native事件，
没有覆盖真实作者写文件再封存。这是完整链路验证缺口，目录可启动的中性探针没有证明这一环。
H5 submit不查全run库存，故提交后自动发出S8；主审随后核封存器清单才发现额外文件。
S8已在途，保留完成返回后以helper operator_stop终止，未派审、未重发、未补签。

另有一次主审本地参数错误：notes多带binding，被入口在native fetch及任何submission写入前拒绝。
保留原文件，另写仅含stage_assessment/report_assessment的参数文件，同一语义判断与同一native事件首次成功提交；
没有重复审查或Provider调用。该参数错误不掩盖更早的库存缺口。

严格seal内部只读replay在 `semantic_unexpected_run_file` 停止，**没有strict seal**。
未绕过清单重放或放宽验证；47份原件库存和SHA保持，旧26/14/146份原件也全保持。
H5 native单独只读fetch核验成功，不冒充整批strict replay。公开的是失败审计和H5阶段证据，不是成功封存。

- [关闭审计](../../data/evaluation/results/document_full_report_remaining_close_audit_20261012.json)，SHA `d992caef63334db960e6a8d50167214a5c2b29277d85e86836b4a5deaa5f3578`。
- [H5阶段证据](../../data/evaluation/results/document_full_report_remaining_host_evidence_20261012.json)。
- Operator保留native公开turn、原notes、参数修正记录、库存检测、seal失败原始诊断与退出记录。

## 后续决定

自动任务PAUSED，本批关闭；不重新购买、补签或重开H5/S8/V2。先完成无付费的审查工作区与封存边界修复：
未来dispatch必须指定经验证的run外作者答案路径；提交/发下一请求前核运行库存，并在真实写答案→check-answer→native→submit→seal
路径上验证。不能再次只靠read/help探针或不落盘的替身就宣称整链修好。此次先将要求写入AGENTS；生成器与运行门仍待实现。

语义层已得到具体反例：真错定位正确不等于修法正确；后续针对“反向样本关联被改写为无区分”的命题检查修法路径，
结合既有全文反例决定最小机制，不立即再买一批或再堆同义教学。V2未认证、S8无双审、旧strict缺口各自保留。
历史库存不拼资格；正式同版本15、自然消费、8E及既有Coach/Training、四块联动、Worker/DB/API/UI/journal、
前端审美头像、Memory、身份运维、两树整合、独立评估与学习依赖不变。
