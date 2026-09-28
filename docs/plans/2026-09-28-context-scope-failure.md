# 完整上下文误报：当前实证与方案边界

## 复盘后继续执行：恢复修复与单变量采样准备

2026-09-28，用户授权按复盘计划补缺并继续。历史误报、原15标签和闭批结论不变。

**已修确定性缺陷：** `await_case_ready`在Provider创建前写交接文件，超时留下
`cases=[]`；续接账本却将交接文件计为已启动，产生`parent_boundary_changed`。
`role_continuation._started`现只将绑定正确、顺序正确且无案例/传输痕迹的待命交接
保留为未执行；原等待时间仍累计扣除。已启动、冲突绑定和失败后追加交接仍拒绝。
真实observe＋ready超时离线复现、完整campaign及已有恢复组126通过/1跳过。
硬终止丢失原batch计时仍不能事后补造完成资格；此修复不解决模型误报。

**排除重复路线：** ADR0102的上下文引用及9/19已看见后文却仍误读的反例，说明
补引用不等于解决语义；9/22 target_last完整输入排列已有正例误报及修法引入错数。
额外定向审查挤占正常五调用预算；替代全文则漏审业务义务，因此不重复这些方案。

**待测假设：** 相同输入曾95/pass、又85/needs_revision，当前采样temperature1。
仅把审查请求改为0.2，保持GLM-5.3/high、top_p=.95、全文/来源/schema/规则及额度。
这是未验证的可行性假设；低温可能稳定地产生错误，不能把随机性当已证根因。
历史已提交结果检索未发现非1的真实审查温度；通用temperature0探针不算本任务证据。

厂商材料读取于2026-09-28：
- https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3.md
  内容UTF-8 SHA256 `7731b96335c6a263303240615e3b9f20d433e8bf04565bb04936444691036bcf`；
  始终思考、支持high，示例同时有reasoning_effort与temperature。
- https://docs.bigmodel.cn/api-reference/模型-api/对话补全.md
  内容UTF-8 SHA256 `0b7a2a8af808eb946ec58a61242829f31d1b3e882c726d242a684be8504e82d9`；
  temperature范围[0,1]，建议只调temperature或top_p之一。文档与SDK接受不能证明
  服务端内部确实如何采样，也不证明质量改善。

**完整任务可达性：** 初评/fresh/有界重评可共用request变换，Flash编辑分支保持原值；
不加调用或tokens，正常仍两次生成/工具＋初评＋编辑＋fresh共5次，整体900秒。
五次各300秒不代表必能全部完成，既有超时/恢复占额边界保留。
独立审查发现`CoachBudgetedProvider.chat`目前会重置temperature=1。正式采用前必须
在版本化可信合同及budget发送层按role落实review=.2、generation/revision=1，
同步descriptor、manifest、factory/trace、同版本资格；仅改Workflow不会生效。
本轮不提前注册新候选或改变旧产品身份。

**具体诊断：** `scripts/run_review_sampling_diagnostic.py`复用的是
`run_review_model_comparison.observe`，直接经receipted transport发送，不经过上述
产品budget层；不是`run_role_qualification_pair.observe`。测试实际observer→
bridge.collect→adapter→GLM/high SDK→MockTransport最终JSON，确认只有temperature
改变。十五例原输入逐项绑定；初评/重评和编辑保持性离线核验，不冒充自然任务实测。

两例固定顺序：claim-scope:1正确全文应pass且不改稿；scope:3明确中单早死错句
应needs_revision，解释/引用/修法也须正确。逐例全文主审和独立审查，第一例实质
失败就停止，不重评/编辑/重试，不扫邻近温度。两例成功仅支持后续整任务采用评估，
不证明优于temperature1、稳定性或原15资格。失败则否决低温作为充分修法。

新增批上限2调用/600秒（含审查等待）/150348预留tokens，按已存价格估价2.513504元，
不是账单硬上限。旧闭批余额不作为新授权。执行前须冻结请求、独立代码复核、同提交
公共检查及对应新批成本授权；预览不读凭据、不发网络请求。当前未发新Provider请求。
完整实验请求、来源hash、SDK差异、预算和停止规则将固化于
`data/evaluation/results/golden_review_sampling_preparation_v1.json`。

## 结果及影响

2026-09-28，用户“确认，继续吧”批准修后完整十五例，随后“继续”恢复执行。
不是重新申请原预算：本批上限35调用/3386880tokens/10500秒，含三父历史累计
上限47调用/3556222tokens/13299.094秒。50.03264元为保守预留估价，非账单上限。
原proposal的execution_authorized=false保留其当时状态，实际授权记录在本批公开封存。

执行绑定1ecd8cd17a82438cb7cf99264f48f340840d55e9 / CI36307792122三项成功。
公共pytest5227通过/163跳过/129子测试；PostgreSQL218通过；浏览器40通过。
恢复后治理检查通过；未重复整库测试。重建全部15请求及13项源码摘要、三父239原件
与费用全部相同，主审和独立审查恢复完整来源阅读后才启动。

新run `data/runs/role_task_observation/correction-scope-runtime-alignment-v1`
首例claim-scope:1返回85/needs_revision；原始期望为正确全文通过。执行器在
initial-journal落盘后以role_pair_initial_semantics_failed停止，未产生host stage、
编辑或终评，后14例未执行。没有事后补造阶段或修改期望标签。

当前身份仍严格0/15。旧身份3/15只是历史，8E、自然Agent及产品消费均未完成。
已修知识工具时间能力的工程结论不撤回，但不再把该修复与语义可靠性混为一谈。

## 首次偏离与排除项

初评唯一issue/block4将“早期死亡在胜败样本间几乎相同”强制继承前半句的中单口径。
报告第4节block14已明确“全样本口径下早期死亡胜局2.5、败局2.67，差异很小”。
前文中单伤害比较与后文全样本早死描述可分别成立；全文没有声称中单早死几乎相同。
按已采用完整上下文标准，局部重复范围可作为措辞建议，不能据此认定事实错误。
明确写“中单口径”仍是另一个真错控制scope:3，不能把两者混同。

同一原报告、source.json及prepared request与旧1.5.4首例逐字相同：
prepared SHA f0c89c4338be6d21931e9a6703dd3a9dc5d015d67fc0f2de00e23bafd54db1d8。
旧完整返回95/pass、issues空、block4仅advisory；本次85/needs_revision。
通过当前实际SDK适配器用无网络client重建请求，两者除本地timeout外payload逐值相同，
包含模型、high、temperature1.0、top_p0.95、32768输出上限、schema及全部消息。
重建payload SHA819b006c0fb1f1dbc8b1a8ee5f2a14f013e11b210553b4f7b1176abbbbed736e。
这是当前代码的离线序列化核对，不是原始HTTP wire捕获；不能据此排除Provider内部变化。

- 本次流完整结束tool_calls，156.344秒，11800输入/8808输出，未触及32768上限。
- 原公开tool arguments与parsed journal逐值相同；误报并非解析器或host新增。
- 同一输入曾通过又失败，证明已观察到结果不一致，不证明采样是唯一成因或可估算稳定率。
- 目前能确定的是实际判断错误：局部范围继承被提升为事实门，未正确使用全文已有消歧。
  未证明模型内部注意、温度、负载或任务长度的因果作用，不把这些猜测当根因结论。
- 修法又给出“中单胜局反而早死更多，故不构成胜负分界点”。数值本身正确；
  反向差异不自动推出没有区分性。该额外措辞需全文复核，不靠它替代已经成立的误报证据。

## 真实产品路径检查

现有一次有界重评处理validate_review报出的无效结果；本次完整合法needs_revision
不会进入该恢复分支。严格固定报告验收是在错误verdict处阻断；自然产品通常会将
该意见交给编辑。因此“有重评”不是本次误报的现成修法，不能绕过原15直接上线。
同样不能把手工加范围后的正确稿通过、Flash可能容错或旧版本成功当成当前准入。

## 本次去留及下一动作

独立语义结论及完整证据见[独立审计](2026-09-28-context-scope-independent-audit.md)；
实际恢复反例、历史否定结果和备选筛选见[策略审计](2026-09-28-context-scope-strategy-audit.md)。
主审认可确定误报；修法的“故不构成分界”仍按有待核清的推断保存，不另立第二确定阻断。

本批关闭，不执行剩余14例，不自动重跑首例或换目录借余额开新批。
不再以一项局部成功支持“误报已消失”，也不追加一条同义全文规则再跑15。
当前policy已明确完整上下文、不能为作者补量词及advisory边界，规则缺失不是本次证据。
已有9月24日上下文四条件全同向、meaning-first/两状态终评等反证必须带入方案选择。

下一工作包先完成单调用审查职责的机制诊断设计，明确正反例及结果对应的去留。
必须直接作用于正确全文的实际首评与最终核验，而非将相同误报后移；不删除来源、
不自动改写正确稿、不靠特定段号/数字放行、不增加产品调用或悄悄修改原15标准。
新诊断执行前要有冻结请求、完整任务预算可达性、停止条件及明确授权范围；
本次预算确认不作为无限新批许可。当前没有选择已验证的语义修法或发布新候选。

### 对备选四单元诊断的实施前检查

策略审计提出的“完整审查/单目标审查 × 正确省略/明确错组”可以比较两种任务形态，
但单目标审查本身不能满足身份、建议、知识、数值、来源和全报告错误的完整义务。
若直接加在完整审查前，最坏路径变成2生成+定向审查+全文审查+编辑+终评=6调用，
超过当前5调用；替换全文审查则留下未审部分，终评继续用原全文任务又会重现同一风险。
这与历史“新首审+旧终评”的反证一致。因此当前**不批准为这一裸设计付费**，也不
把“最多4次”冒充实施价值；先找覆盖完整任务、作用于首评和终评、预算可达的责任划分。
现有格式恢复/引用检查不能确定性识别此次合法语义误判，不得硬编码原例放行。
这一检查否决的是未经闭环设计的新增实验，不改变产品预算或用户标准，也不证明问题无解。

## 封存与费用

- 28份原件封存：golden_correction_scope_runtime_alignment_result_v1.json，
  SHA12f38fdac658644c7fc29d86012d57f82965f7116482ca950ee0b285593b6965。
- 严格adapter实际运行，拒role_observation_continuous_completion_missing；没有创建资格目录。
- SDK请求/来源/公开响应/数值只读核对：golden_correction_scope_runtime_alignment_failure_audit_v1.json。
- 新增1调用20608tokens/192.344秒（含批前ready等待），unknown0，未缓存估价0.341024元。
  三父加本批累计13调用189950tokens/2991.438秒，估价1.9803756元，非账单或项目全历史用量。
- 本批无活动Provider；旧239原件与本批原件保留，开发协作用量不混入项目Provider用量。

后续自然Coach/工具、同run存储/Worker/API/Workbench，四块联动与本人Training、
前端整体审美/英雄头像、Memory、身份运维、两树整合、学习仍在原计划。
本次不修改主树未完成前端，也不把公共PostgreSQL成功说成本机Docker恢复。
