# 审查时间候选：完整请求与共享预算接入

## 当前交付及边界

GLM600/Flash300候选已接到完整ChatRequest和既有CoachBudgetedProvider账本，
不再只有四个整数计算测试。代码仍是未准入的显式离线入口，execution_ready=false。
没有新Provider发送、业务run、资格或付费方案；不重开已关闭10例。

先前1d181238只增加未被入口使用的TimingRequest计算函数。它接受非法role、NaN和bool，
没有自有时钟、实际请求校验或账目。58ba12dc回退了此前破坏旧指纹的未提交集成；
58852ee5是有效时间裁决。旧状态里“共享任务时钟/实际身份互拒已完成”过宽，本记录纠正。
本次完整请求校验与自有时钟代码有独立执行证据，不能追溯算作前一提交已实现。

## 设计与调用路径

目标是利用900秒任务墙内剩余时间，避免单次300秒先截断GLM审查；不扩任务、调用或token。
完整原始/contrast请求经prepare_request绑定document_review_timing标记，审查设600，
生成/编辑设300；消息、工具schema、报告和全部来源不改变。非法角色/政策/schema拒绝。

TimedDocumentBudget继承现有CoachBudgetedProvider，构造时核旧组合provider与显式新时间
标记，再在私有候选limits中设request600；不由外部patch旧预算实例，也不注册默认合同。
roles分类在剥离时间标记、投影<=300后核旧完整协议，投影仅用于分类；实际发送、SHA、
回执仍绑定600原请求，不能拿投影当旧交付认证。旧文档审查身份实际拒新标记，旧transport拒600。
旧generation分类器及通用300秒transport不严格枚举metadata，可能接受带新标记的300秒
生成请求；本包没有宣称所有旧入口均互拒。新时间router/transport接入时须封住这个边界。

账本保持5调用、401920tokens、64000单次输入和32768输出。预算器创建时拥有一个时钟，
生成/工具/审查/编辑/fresh共用，发送前取request与900剩余的较小值；时钟倒退拒绝并停止。
调用前预留输入上界+输出，完整匹配ChatResponse结算实际usage；无可信usage的失败保留
预留并停止。完成后再核总时钟，迟到结果不得交给workflow。未知不当零，不作自动重试。

_provider_for_request捕获共享预算实际处理后的issued请求。SharedBudgetReviewSender
可以直接消费这个真实预算对象；只转发delegate的新Exchange，不创建receipt或第二账本。
issued必须逐字段等于捕获请求，SHA必须是完整新时间请求字节；伪造digest、缩短timeout或
修改issued不得交给workflow。准确usage仍记账，回执不合格的结果不作为业务交付。

选择独立子类是因为本包只扩一个候选边界，能复用全部账目且无SDK生命周期复制。
“以后绝不能改指纹覆盖模块”不是用户约束；未来若共享生命周期需要扩展，应显式更新
受影响当前manifest、验证旧入口并保留历史封存。不能静默绕指纹或复制整套transport避检查。
本次没有修改共享指纹模块或任何旧seal/capsule，现有冻结时间审计逐字节重建仍通过。

## 离线验收

25项新完整请求/真实账本检查通过：15例消息/来源/schema保持；新旧请求身份分隔；
错误marker/policy/schema/调用方elapsed/非有限timeout/角色超界发送0；真实产品compiler
生成及工具前缀+初评+编辑+fresh共用5调用账本，时间上限依次300/300/600/300/100；
900耗尽发送0、时钟倒退停止、未知预留不释放、token墙、超输入、错模型、超usage、
迟到完成和实际issued/SHA误绑定拒绝。业务response为明确模拟，不是语义认证。

4项旧标量检查及9项公开时间裁决检查通过，新补非法数值/角色不再被接受。
旧预算/document workflow/contrast/editor相邻53项通过。合计91项，各文件一次最终通过，
不累计中间重复执行。测试禁止网络；无需本机忽略run、.env或真实凭据。
两组最终耗时11.37秒和54.17秒；编译、治理、diff检查与公开冻结时间审计重建通过。

复现：项目Python环境执行tests/test_document_review_timing_adapter.py、
tests/test_document_review_timed_budget.py、tests/test_document_review_timing_decision.py，
以及tests/test_document_review_budget.py、tests/test_report_document_workflow.py、
tests/test_report_contrast_review.py、tests/test_report_block_keyed_editor.py。

## 下一工作及未完成依赖

| 边界 | 当前实际状态 |
|---|---|
| 完整请求/角色/新时间SHA/共享900账本/Exchange sender | 已离线执行；显式候选入口 |
| SDK request policy/父子进程/stream/close/observation600 | 未接入；旧300路径保持 |
| 业务workflow初评/编辑/fresh的新时间摘要 | 未接入；当前测试只是原请求与真实预算接缝 |
| 真实checkpoint/native导入/严格回放/新诊断runner | 未接入；不能用旧native补签 |
| Worker续租/取消/失去所有权后的600消费与发布 | 未验证；尚无生产准入 |

下一动作是把新时间身份贯穿SDK/共享进程生命周期与业务workflow，再核同版本回执、
native回放及Worker边界。不能现在提出execution_ready=true或启动新付费批。
新成本方案齐备后才按具体范围取得授权，不借旧28/45调用余量。
历史2/15及3/15独立，新资格0；正式同版本15、自然消费、8E和原产品下游均未完成。
