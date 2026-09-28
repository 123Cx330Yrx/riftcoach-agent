# Runtime alignment 首例停批：策略与历史反证审计

2026-09-28；只读审计基线 `1ecd8cd17a82438cb7cf99264f48f340840d55e9`。
对象：`data/runs/role_task_observation/correction-scope-runtime-alignment-v1`。
本文件为临时方法审查，不变更产品标准、原标签、旧回执或 canonical 状态。

## 结论及本轮实际完成的检查

本次足以否定“自然产品已有一次重评，所以可直接补救这个原15初评失败”的方案。
原响应是结构合法的 `needs_revision / 85`，实际工作流不会因此自动重评；严格原15观察器随后因初评结论与原正确控制不符而停批。
不能把测试底座的停止解释成产品本来会重评成功，也不能直接重开编辑尾部，把改过正确报告后的通过换成原样正确控制通过。

已实际完成最小零调用反例，未只停留在静态推断：

- 从原文件反序列化完整 `response-001.json`，作为不透明对象原样交给本地 sender；没有访问或输出私有 reasoning 字段。
- 使用冻结的 `claim-scope:1` 完整 `EvaluationRequest`，调用真实 `RoleCorrectionScopeReviewWorkflow.evaluate`。
- 本地 sender 调用 **1** 次；新 Provider 调用 **0**、新 tokens **0**、新 Provider 秒数 **0**。
- 返回 **needs_revision / 85 / 1 issue**；唯一 phase 为 `native_business_review`；`previous_raw=None`。
- `last_journal` 与本次原 `initial-journal.json` 逐值相同；`stopped=False`、`evaluations=1`、`revisions=0`。
- 原完整响应 SHA256：`6f416243bd3f583e13d2f7debd6a2ac530bf07eec9274347d509bc8fb2a14322`。
- 原公开 tool-arguments raw SHA256：`dceeea8fa7cced1aa6a8b45641f3c02fce5ece02a4017db608032db35441fa2a`。

这项检查区分了两个实际机制：恢复分支本次不触发；严格观察器确实在后续编辑之前停止。没有执行或伪造编辑、终评、第二次评估或后继通过。

## 已读取的公开事实与解释边界

已读完整报告及 `initial-journal.json` 的公开 `parsed_review`。原报告总体结论提到“早期死亡在胜败样本间几乎相同”，后文同指标明确写“全样本口径下早期死亡胜局2.5、败局2.67”。本次 issue 将前一分句按相邻的中单组解释，使用中单2.5/0.5提出反例，并要求补范围及中单描述。这里记录的是响应的选择方式，不替代另一个独立语义裁决任务。

原新旧 journal 的 `policy_sha256` 均为 `33b11c48b25f3a4dc2879743a0d76dd6c60c0afa4cc1b2b596edacfd967ba8f7`；旧初评为95/pass、issues空、block4非阻断advisory。当前真实结果为1调用，11800输入+8808输出=20608 tokens，unknown=0，整批192.344秒，错误码 `role_pair_initial_semantics_failed`。

主审另行完成实际 SDK 无网络 payload 重建：模型payload逐值相同，仅 SDK 本地 timeout 参数不同；temperature=1、top_p=.95、max_tokens=32768、high均相同，payload SHA前后均为819b006c…736e；本次stream完整结束156.344秒。此处引用主审证据，不冒称本人另做了一次SDK核验。

同输入曾有不同公开结果，支持“仅获得一次pass不能证明该机制可靠”。它不单独证明采样、服务端版本变化、注意力或任务负担中的任何一项是根因。既无本次截断证据，也无提示/来源未送达的已知缺口；知识工具运行修复不在这个固定首评的工具执行路径上。

## 为何现有重评不能替代原15初评

实际调用链：

1. `app/product/native_coach_composition.py:107` 的 `build_correction_scope_coach_application` 注入 `RoleCorrectionScopeReviewWorkflow`。
2. 该类继承 `app/evaluation/golden_semantic_review.py:263` 的 `NativeBusinessReviewWorkflow.evaluate`。只有 `validate_review` 抛出可恢复 `ValueError`，才构造带原意见和诊断的 `native_business_reassessment`；合法的语义误判不会自行变成校验异常。
3. 本次 `RoleCorrectionScopeReviewWorkflow.validate_review` 接受原raw、返回可操作的单条问题。`app/harness/runtime.py` 的 needs_revision 分支可以走一次编辑；这条分支不是重评原结论。
4. `scripts/run_role_qualification_pair.py:160` 先保存 `initial-journal.json`，再比较原冻结标签和初评 verdict。此例为accept，needs_revision触发本次错误，尚未调用 `inspect('initial', ...)`，也未编辑。
5. 同脚本 `send` 对带 `task_observer` 的严格路径明确拒绝 `native_business_reassessment`。不能通过手工设置 previous_raw 或把合法语义问题伪装成格式错误绕过它。

ADR0113明确区分：产品保留既有一次有界重评；原15禁止重评、重试、错误解释例外和跨身份迁移。ADR0111还明确：原正确控制必须原样通过；错误初评、误报及正确控制需要编辑均停止；只有定位和修法都正确、附属解释有错的特定观察才可能继续，且不自动授严格资格。本例不在该例外内。

预算也不是“免费第二次判断”：现有自然任务的两次生成/工具衔接+首评+编辑+fresh终评已经可能耗尽5调用。`tests/test_correction_scope_runtime.py` 的 recover 场景实际记录 generation/generation/review/review/revision，因共享额度耗尽而拒绝发布，不能宣称原恢复容量保证再做终评。

## 历史反证如何影响当前方案选择

| 证据 | 对本次方案的约束 |
|---|---|
| `docs/plans/2026-09-19-role-attribution-review.md`：同一类原正确稿已被相邻中单口径误读；当时将全文先定范围放在前面，后继正例通过，但另例恢复漏字段、语义仍有缺口 | 当前再加“看完整上下文/不要只看相邻句”的近义句没有新的机制依据。当前实际 policy 已包含该标准。 |
| ADR0110的2026-09-24四条件上下文对照：原稿、解释替换、删引言、双改均无目标误报，按预注册全同向分支停4；部分advisory另有来源错误 | 引言/正文替换未隔离出诱因；不能继续改正确报告来迎合评审，也不能把全同向当作任务负担已排除或已证明。 |
| `docs/plans/2026-09-27-correction-scope-diagnosis.md`：修法责任规则两控制通过、实际编辑/fresh终评通过；文件明确不证明稳定性，出现实质问题不追加近义变体 | 规则解决的是输出修法扩题的候选机制。本次不能凭旧两控制成功转成“规则已普遍稳定”；也不能把新的范围判断误报再用同类文字叠加遮住。 |
| `docs/plans/2026-09-21-issue-identity-contract.md` 及9/22复核：定位臂单例成功，但删建议会合并含义不同的问题；两状态终评仍误报 | 不删除 suggested_correction、不做“新自由文首审+旧终评”、不把旧意见暴露直接定性为根因。当前是fresh独立初评，本就无previous_raw。 |
| ADR0102 source-first/旧scope原型：完整来源、合法引用、完整清单仍可选错组；source-first旧付费入口已退休 | 引用存在不等于语言含义正确。现有computed已经有两组数值，增加计算字段或要求模型重抄范围不能自动修复文本与组的对应。 |

具体政策入口：`golden_native_business_policy.SCOPE_POLICY` 已要求完整上下文可补省略；`golden_role_clarity.MARKER_POLICY` 已区分真实错误与可选措辞；`golden_role_correction_scope.RULE` 已约束完整修法；当前缺口不是没有容纳非阻断意见的字段。

## 已有机制可以复用到哪里

- **当前回放底座**：`correction_scope_qualification.frozen_cases`、`Workflow.build_inputs/validate_review/evaluate`、`golden_integrated_runtime.Exchange` 已完成本次原响应零调用反例。它验证确定性控制路径，不证明模型会纠错。
- **非阻断标记**：`RoleClarityReview` 已有仅block的advisories，旧95/pass也确实用了它。不能再扩一套“可能错误”schema；真正缺的是在既有通道中正确分类。
- **编辑/fresh终评**：`Workflow.revise` 将完整意见交给编辑，之后fresh评估不传旧意见；在已有真错尾部观察中有单例成功。它不是本次原正确稿的合规救援入口，ADR0111边界不覆盖本例。
- **旧定向scope seam**：`app/evaluation/golden_bound_scope_review.py` 可做零调用prepare及目标/回执绑定，其decode只有sample_defined/needs_clarification/beyond_sample/negated，且未注册真实CLI。它不能原样充分表达本次“样本内部组别矛盾”负例，不应为了复用它扩schema或重开已退休probe。
- **旧四条件runner**：`scripts/diagnose_role_context.py` 的封存、计费、无重试及预注册停止方式可参考；旧计划固定旧资料/旧版本，关闭批不能直接复用为新实验。

## 下一动作与仅供选择的最小诊断设计

本轮已完成的零调用检查足以排除“现成自动重评能处理此例”的方案。眼下不增加提示、不修schema、不重跑15，不把一次重新pass当成修复。主审先结合独立语义裁决定性本次首评；若人工预期被新证据推翻，则按既有决策记录处理，不因历史标签而预设模型必错。

若该语义裁决确认误报、且下一工作包确实要决定“是否继续研究审查任务划分”，可预先制作以下**未执行、未授权**的4单元筛选设计；它不是拟采用的产品结构：

| 因子 | 冻结内容 |
|---|---|
| 报告 | 现有原始 `claim-scope:1` 与现有 `scope:3`。后者只在同一句明确加“中单口径下”，其后仍有全样本正确说明；两份完整报告、数据、原标签均不改。它能阻止“看到后文正确数字便一概宽放”。 |
| 审查任务 | 当前完整审查；或仅审指定早期死亡断言与全文关系。定向条件保留全部来源、完整报告、相同模型/参数及既有工具输出schema，只改变本次审查责任范围；不提供正确组别、预期答案、旧意见或建议修法。 |
| 输出与审计 | 仍保存完整issues/explanation/suggested_correction、原始公开响应和真实用量；不加范围/证明/中间思维schema；定向结果显式 `qualification_evidence=false`，不交给产品发布或严格资格入口。 |
| 规模 | 一次预注册4单元，固定交错顺序，不重试、不自动反向第二轮、不重评、不编辑/终评。作为上界设计不超过4调用，每请求300秒/32768输出；冻结前逐请求核容量，总不超过387072tokens/1200秒含host。此数字不是执行授权。 |

与9/24设计的新增信息：旧实验更换了引言和正文表达，却保留全稿审查责任；本设计完全不改两份既有报告，改变“发现所有问题、判断、生成修法”这项责任覆盖范围，并增加同指标明确错组的现有负例。它只能比较两种任务形态的表现，不单独隔离注意力、提示长度、目标显著性或随机性，不能自称任务负担的因果实验。

预先固定去留：

- 完整任务误报，而定向任务能同时正确接受原稿、拒绝明确错组：仅支持对任务拆分做下一步零调用覆盖/预算可行性审查；不接产品、不替代首评，也不增加常驻第二审查调用。
- 定向任务仍误报原稿：停止“单纯缩小审查目标即可解决”的方向；不修一句同义提示再测。
- 定向任务两份都接受：不是成功，是放宽或丢掉明确反例；停止该方向。
- 两任务两报告都符合预期，或不形成上述区分：观察未复现/不确定，不能转入新15宣称修复，也不自动重复求显著性。
- 任何协议、传输、身份、安全或预算失败按既有规则停止；无效响应不能成为语义通过。新的实质问题保留并单独裁决。

若项目此时不会因任何结果改变任务划分选择，则这个诊断也不值得付费，应停在已完成的零调用证据；不能为了“继续推进”再做一个所有分支都导向改提示的实验。

## 审计范围

未改tracked代码、提示、数据、标签、资格或封存；未发Provider、未启动Docker、未commit/push。仅新增本临时审计文档。完整响应只作为本地重放的不透明对象使用，没有读取或输出私有reasoning正文；没有伪造后继通过。历史资料按其当时身份解释，不合并成当前质量率。
