# 完整报告关系教学成对初评：开发诊断准备（历史快照）

本页保留授权前准备快照。用户后续明确授权及CI迁移后，本批4次均已发送，3次双审、第四次传输超时；
严格封存完成，automation PAUSED，未授资格。当前结论和下一动作见[关闭结果](2026-10-12-relation-initial-result.md)。

## 目标与选择

主阻断仍是初评在检出真错后可能提出新的错误修法，阻碍可靠教练报告进入真实消费。
本包保持完整初评职责，检验一个可撤回的教学候选：区分均值方向、逐行组间比较和因果。
旧H5修法同时给出正确数字与错误否定区分；这支持检查关系判读，但尚不证明内部成因。
来源先行替代首评已因ADR0110及历史漏检反证撤回，不恢复这条路线。

新增两个私有入口复用已有600秒worker、原始回执、完整Host审查与工作区库存门。
没有改生产默认、旧共享源码、schema、全部来源或编辑合同。相比直接重跑15例，本诊断只回答
这一个教学差异在新开发材料上的结果；不能证明稳定率、正式15或自然生成/编辑质量。

## 输入和唯一差异

从固定的原始 `claim-scope:1` 完整产品格式报告派生两篇开发稿，只替换总体结论及比较文字，
保留其余章节、逐局来源、知识原文、身份和条件训练建议。每篇实际请求26段；不是旧三稿的18段。
来源与故障机制已熟悉，不称独立holdout，也不重开或补签H5/V2/S8。

- R4：正确样本比较。中单早死胜场3/2、负场0/1，均值2.50/.50，每个胜场都较高；不推因果。
  中单补刀胜场8.95/8.66、负场9.64/8.38，均值8.805/9.01，区间重叠，不能称每个胜场都较高。
- T9：仅两处改成“中单早死胜负组均值相同”和“每个中单胜场补刀都较高”，保留可反证数字。
  审查须核全文，不限定issue数量；正确数字不能抵消同段真错，修法不得否定正确区分或扩大范围。

同稿依次运行baseline和relation-contrast；候选只扩展虚构印刷厂丙3教学。
恢复候选教学后请求必须逐字段等于baseline；实际worker发送候选全文，不发送恢复后的投影。
metadata用于本地身份绑定，不发送Provider；预期答案与Host判断不发给Provider。
报告中的既有HOST_BLOCK标签仅为一基段号，不作为报告事实。
SDK收到的剩余超时随启动耗时变化，两臂均从同一600秒总期限扣除，不能要求剩余秒数完全相等。

## 固定执行边界（尚未授权）

准备包：`data/evaluation/fixtures/document_relation_initial_20261012`；9份文件create-only生成并验证。
plan SHA `8b93463e04a5d4321727ba06188914047d12215d097a12fc0091eabb2e3d0dda`。
准备审计：`data/evaluation/results/document_relation_preparation_20261012.json`，
SHA `a85e3dea75e15d463db6becc066b479ed991faef721ee010ac843f0172cd85fe`。
本机绝对cwd/Python实际启动和当前真实native主体预检通过；不保证未来可用性，付费前必须即时重核。

| 项目 | 具体范围 |
|---|---|
| 顺序 | R4-baseline、R4-relation-contrast、T9-baseline、T9-relation-contrast，均initial |
| 模型 | GLM-5.3/high，最多4次；Flash 0次；temperature 1.0、top_p .95 |
| tokens | 最多387072；每请求输入上界64000、输出32768 |
| 时间 | 每请求600秒；活动总上限2400秒；Host总上限86400秒 |
| 估价 | 5.718016元，按未缓存上界估算，非硬账单封顶 |
| 禁止范围 | 不生成报告、不编辑、不fresh、不重评/重试/补发，不授予新资格 |
| run | `data/runs/model_comparison/document-relation-initial-20261012`，当前不得创建 |
| operator | `C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-initial-20261012` |
| 作者答案 | operator下`author-answers`；必须在所有run证据目录外create-only写入 |

具体授权须绑定固定plan摘要、精确HEAD与该HEAD全绿CI，原24小时期限不延展。
首次run前验证包、授权、干净精确HEAD、无run、当前native主体及绝对cwd/Python实际启动。
路径检查实际启动该解释器并导入checkpoint helper，先于凭据读取或项目Provider调用。
等待器尚未创建，automation保持PAUSED；没有把本包准备或“继续”写成四次付费授权。

业务执行复用主审 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4` 与独立主体
`01a12f0c-bb7c-74e3-ad92-775eefbe399a`。每stage唯一NEW_TASK，恢复只MESSAGE。
独立只收完整生成dispatch及精确checkpoint/SHA、cwd/Python、run外作者路径；不收主审、标签、
校准结果或批次代码。作者自己落盘/check-answer，唯一多行JSON native final；主审实读原生事件
后submit。均为initial，report_assessment=null。校准不是这些未来业务stage的预签名。

有效语义拒绝或Host分歧保留并继续下一独立项，不把失败传入编辑。
身份/来源/native/checkpoint/协议/transport/预算/主体硬故障停全批；无重试。
submit前、native读取后的锁内、下一请求及transport前检查run库存，意外文件不移删以过门。
关闭后只读严格replay、create-only白名单seal，记录actual/HTTP/known/unknown/receiptless/未发及最早偏离。

## 判定如何改变下一步

候选在任一稿误报、漏检或给出实质错误修法，则否定本候选的当前修复主张，不自动追加同义教学购买。
两臂均过只说明这两稿没有暴露差异，没有改善证据；两臂均错则共同问题仍在。
只有baseline暴露目标错误、候选完整审查正确且正确稿被保留，才得到这次开发对照的有限支持。
即使候选两稿全过，也不采用生产默认、不跳到完整15完成结论；还须按既有合同准备同版本质量证据及真实消费。
传输或Host故障只回答执行可用性，不能回答语义；已发送或未知请求不重开。

## 验证记录

新增26项离线检查通过：请求单变量/身份拒绝、真实worker子进程到SDK边界（网络被替身禁止）、
授权/路径/native/包先于凭据、run不能重开、作者文件及合成原生事件导入、语义分歧继续、硬故障停批、
只读回放与create-only封存。该原生事件为明确合成fixture，不冒充新的真实业务独立审查。
前次工作区真实native短稿演练另保留原证据，本轮不重复或升级其适用范围。

联合旧入口/Host工作区/关系工作流共66项通过；随后将校准原件及真实结果绑定到新包，
新入口最终29项通过，包含材料/校准摘要漂移拒绝。旧共享代码与已关闭业务证据未修改。

两稿全文开发校准已复用既有独立主体完成。主审先保存独立前意见并逐行重算，独立只读指定两份文件，
按原样写自己的run外答案；其19个可见工具调用均已核读，输出无截断。完整来源、current_input_json、
两篇全文及policy均有完整读取记录；恢复后及终答前核了相同路径与SHA。材料block字段为内部b01-…标识，
派发补充说明仅解释其顺序对应1..26，不更改原件或事实判断。
R4未发现实质错误，T9定位14/15段两处真错；修法保留正确数值、范围与因果限制。第6段仅advisory。
主审核了全部解释和修法，未发现需要更改标签的反证；一致本身不是正确性的依据。

材料SHA `53bea63165bc5eebfdbd8793c56e801b741f852b5f6738fea9b34a7fb6025f85`；
校准审计 `data/evaluation/results/host_relation_material_calibration_20261012/close-audit.json`，
SHA `9fc5ce547889deb7208b4a4a4b6260e3b400bac0e500e61ba40d706b9e7fb670`。
真实原生turn `01a13031-f27a-78b3-8026-3b3278b5a7cf`，API唯一final
`msg_0d3b9daa49f66152016accdb1f2e6c87d08c84c0e54c037645` 已实读并逐字核作者文件（仅末尾换行不同）。
原始历史含一次压缩摘要，未用它作为判断；派发正文加密，现有FINAL policy核的是主体路由及API选定终答，
不能声称读到了加密正文。公开可见读写记录也不证明OS沙箱。该校准不产生业务stage/receipt/journal/submit。

当前没有项目Provider/HTTP、业务submit或新资格；本轮复用独立任务1次、新Agent 0。
所有旧47/26/14/146原件和认证缺口独立保留；
历史2/15、3/15、remaining11、分段15及教学对照不拼资格。正式同版本15、自然消费、8E和既有下游仍未完成。
