# 教学对照后的机制取舍与免费边界检查

目标仍是修复完整报告审查的实质误报及错误解释，进入同版本完整15和自然Agent消费。
本轮三种教学均在正确泛指稿上误报，已否定其作为共同修复的充分性。
不是没有送达规则、缺少advisory字段或缺少正确统计；也不能据此证明模型内部根因。
本文件不授权新付费批、不改变产品采用标准或模型组合。

## 复用与淘汰

| 路线 | 当前证据及决定 |
|---|---|
| 再叠全文/量词/修法提醒，或原样再买15 | 本轮三组织均误报同一正确泛指，停止同义教学试错；不采用 |
| 先抽命题，再按来源审查；增加命题字段 | 9月meaning-first、grounded/provisional reading已有真实格式、范围和覆盖失败。10月9日责任probe又证明合法结构可容纳相反标签。不能作为新发现直接重建 |
| 追加定向审查或完整重评 | 10月8日完整重评仍误报；格式合法的误报不触发现有格式恢复。定向前置加完整审查将整任务五调用变六，替换全文则遗漏义务；不直接采用 |
| 让编辑照误报改正确稿，再取fresh通过 | 改变原正确控制、掩盖误报；不符合原15和ADR0110/0111边界，不采用 |
| 改模型/降低标准/用历史成功补签 | 不在本包内；原组合、质量门和两未认证缺口保留 |
| 改解码温度，保持全文与单调用职责 | 与教学后缀是不同的可观察变量，且不天然增加产品调用；只完成免费SDK/身份边界检查，尚未证明有修复价值，不准入 |

历史证据入口：
[source-contract-repair](2026-09-17-review-source-contract-repair.md)、
[workload-partition](2026-09-19-review-workload-partition.md)、
[context-strategy-audit](2026-09-28-context-scope-strategy-audit.md)、
[scope-resolution-result](2026-10-08-scope-resolution-result.md)、
[review-responsibility-decision](2026-10-09-review-responsibility-decision.md)。
这些旧入口仍退休；不得改原响应、提高旧资格或按旧工作队列继续执行。

## 已做的零调用检查

`scripts/audit_document_sampling_boundary.py`只读本轮公开封存中五个expanded基线请求，
精确恢复原issued bytes。用整个本地SDK记录器代替网络客户端，保留实际adapter、工具别名、
GLM-5.3/high profile、tool_stream、usage-tail和600秒接缝。

分别构造temperature=1.0和0.2的SDK参数，断言差异仅temperature，全文消息、工具schema、
模型、high、top_p=.95、32768输出及其余参数完全相等。输入及工具不加Host标签或裁决。
记录器不返回模型报告、usage、receipt或journal，不读取凭据、旧run或private reasoning。
五个低温构造均须被现有冻结request validator拒绝，不能借原transport身份发送。
因此这一检查不修改本轮运行或产品默认配置。

公开产物：
[`document_sampling_boundary_audit_20261011.json`](../../data/evaluation/results/document_sampling_boundary_audit_20261011.json)。
SDK kwargs的本地相等性不是实际HTTP wire、Provider接受、服务端遵循参数或语义正确证据。
temperature=0.2只是可审查的备选值；本轮没有控制该变量，不能称采样是根因，
也不能声称低温比当前配置稳定或正确。低温可能稳定地重复错误。

## 下一工作包及有区分力的结束条件

免费整链入口核查已完成：
[`document_sampling_reachability_audit_20261011.json`](../../data/evaluation/results/document_sampling_reachability_audit_20261011.json)
保留五份完整历史请求，其中sample2/4明确来自历史final，不伪造新fresh。
实际TimedDocumentBudget入口全部在委派前以`document_identity_request_contract`拒绝低温，
attempted/预留/委派均0。另直接运行继承的CoachBudgetedProvider预算方法作为局部见证，
在委派前停止：该方法会把temperature强制重写为1.0。此局部调用不是绕过门的可发送路径。
已有SDK能表达0.2，不代表现有整任务能保留0.2；**当前低温备选整链不可达**。

源代码控制流另已核：TimedDocumentWorkflow的initial和编辑后fresh都使用make_request；
block-keyed编辑校验把final request SHA重新绑定，DocumentReviewWorkflow还比较prepared/issued
全文和最终receipt。TimedDocumentBudget在预算前核身份、预算后核真实issued/receipt，因此不能
只在SDK临时注入温度；那样会造成请求身份或回执不一致。共享预算原方法强制归一化，故修改
候选request而沿旧预算同样不足。现有规范路径generation×2→review→revision→review是五调用，
格式恢复消耗同一上限，必要时fresh因余量不足停止；不是免费第六次审查。
这些是现有代码和本地拒绝分支证据，没有生成/编辑/终评的新业务结果。

下一动作是在免费隔离原型中验证构造→共享预算→角色/transport→receipt→fresh绑定均一致：
候选身份与profile须显式隔离；所有原15完整输入/来源和验收门保留，正常路径与必要
编辑路径仍用既有五调用/共享预算。先检查现有SDK及整任务消费者的覆盖与拒绝分支，
不能仅修改request.temperature却沿冻结身份发送，也不能用“SDK能表达”代替方案采用。
方案须显式替换候选审查角色的归一化约束，不改生产预算类、生成/编辑角色的温度或旧身份；
不能用多个局部monkeypatch拼可发送入口。上述需求未实现，不称新原型已接线或采用。

只有这项完整可达性检查成立，且结果确实能决定是否继续该方向，才准备一次有界筛查的
具体请求、身份、停止条件和成本。对照至少包含本轮正确泛指、明确全称真错、明确中单错组、
正确身份稿和标题能力真错；原样正文与全部来源不变，双审逐项核新增解释和修法。
不得因一项pass便购买完整15，不得换教学和温度同时改变而宣称单变量结论。

预先去留：正确泛指仍误报、真错被放过、解释新增无依据排他断言或实质Host分歧，
均不能成为共同修复；无区分性结果不自动复跑。即便有限筛查全过，也仅支持进一步
同版本验证准备，不证明稳定率或授予资格。协议/身份/来源/传输/native/预算硬故障停批。
当前没有新可执行身份、新runner或新付费授权。

本包不转移到外围产品环节来掩盖质量阻断。已有完整来源、block-keyed编辑、fresh、
Worker/Evidence/API等基础复用；正式15、自然消费、8E及原下游依赖保持未完成。
