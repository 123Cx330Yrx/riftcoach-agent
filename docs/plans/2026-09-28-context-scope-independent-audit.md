# Runtime-alignment 首例失败独立审计

日期：2026-09-28。审计者：`scope_execution_check`。工作树：`D:/riftcoach-agent-rq192-pr`；分支：`codex/rq192-provider-stream-contract-ci`；HEAD：`1ecd8cd17a82438cb7cf99264f48f340840d55e9`。

## 结论与确定性

**确定：本次 `claim-scope:1` 是一次真实的 review 语义失败，具体为 false positive。** 有效公开响应把完整上下文已经消解的范围省略升级为 `fact_error`，从而给出 `needs_revision`。这个结论来自本次实际请求、唯一 issue、原报告全文和来源数据之间的核对，不依赖 frozen 标签或旧 run 的 pass。冻结期望与本次 verdict 不符只是关闭运行的机制，不是本审计的语义论据。

**修法关注点：建议中的新增推断不能视为已经证实；不将它另列为第二个确定阻断。** “中单胜局反而更多，故不构成胜负分界点”不是由方向反转直接推出的结论。但“胜负分界点”也可能在报告的教练语境中指可解释的败因或稳定判断，全文的小样本、非因果限制允许谨慎表达。因此本审计确定的是修法需要核清其实际含义，不能把正确的均值当成整个替换断言已获来源支持；不擅自将它强化成作者声称“完全没有统计差异”。本次已确定的 false positive 足以解释失败，无须借此追加独立阻断。

运行已关闭；本说明不是 host decision、补录 stage、修订 draft 或资格授予。旧成功不能迁移至当前 manifest，也不能把本次失败改成通过。

## 审计范围与证据路径

目标是核查首个公开响应是否遵守完整上下文标准，以及 suggested_correction 是否引入未经确认的断言。实施路径为只读核对实际 request/response、source、journal、result、冻结准备数据与同案旧请求；仅将结论写入本文件。未参考主审结论来形成主要判断；与主审交流前已完成本次语义判断及旧请求比较。

- 当前 run：`data/runs/role_task_observation/correction-scope-runtime-alignment-v1`。
- 旧对照 run：`data/runs/role_task_observation/correction-scope-role-qualification-v1`。
- 独立预读记录：`tmp/correction-scope-runtime-alignment-independent-preread.json`。十五例原始来源与报告已覆盖；继承九份预读并全文补读新增六份，两组共享来源逐字段摘要相同，current rows、prepared bytes 与全部十三项源码 fingerprints 对应冻结计划。
- 已用 `q.read_calls` 核对回执和实际请求/响应/usage 绑定，用 `rebuild_stage_prefix` 重建唯一 initial；重建 journal 与保存的 `initial-journal.json` 逐值一致。
- `source.json` 与当前冻结来源构建的 input/report 及相应 digest 逐值一致。实际请求与 prepared 请求只在允许的 timeout 收紧及 `coach_budget_contract=coach-bounded-review-v2` metadata 增加上不同。
- 已读取本次全部公开工具参数、原报告全部 25 个 blocks、有关来源数据与实际请求内政策。未引用或公开隐藏推理。

## 运行事实

`result.json` 记录 `role_pair_initial_semantics_failed`，`initial_verdict=needs_revision`、`initial_score=85`，`tasks_observed=false`，首例 `stages=[]`。case 目录只有 `source.json` 与 `initial-journal.json`；run 中已有的 handoff ready 文件是既存的调用准备材料，不是 host 审查 stage，也不是本审计写入。

仅完成一次 GLM-5.3 review：input 11800 tokens、output 8808 tokens，unknown usage 为 0；run elapsed 192.344 秒，未缓存用量估价 0.341024 元（非账单）。没有 revision/final，没有下一例启动。

`scripts/run_role_qualification_pair.py:161–168` 的顺序是先保存有效 initial journal，再将初评 verdict 与 frozen `expected_initial=accept` 所需 PASS 比较；不符即抛出该错误，`inspect('initial', ...)` 位于其后。因此这是有效 review 的语义判定失败，不是 host 超时、传输失败或 schema failure；无 host stage 与此顺序一致。

## 全文范围核对

公开结果只有一个 issue：block 4，`medium` / `fact_error`，`source_ids=[22,31,32]`；`advisories=[]`，`issue_resolutions=[]`。

原报告 block 4 先说明五局的整体构成和四局中单，再写：

> 胜局与败局最明显的差异在中单的伤害/分钟（1286.76 对 617.52），而非补刀或视野；早期死亡在胜败样本间几乎相同，不应作为主要胜负分界点 [K1]。

同一报告 block 14 对同一个早期死亡断言明确给出口径：

> 全样本口径下早期死亡胜局 2.5、败局 2.67，差异很小 [K1]；全样本补刀差距受辅助局明显影响；伤害差距则在两场中单胜局与两场中单败局之间已存在，不能主要归因于辅助局。以上统计不能证明个人能力或胜负原因。均值差异也不代表逐局方向一致或因果关系。

block 13 的表格分别列中单胜局、中单败局、辅助败局：补刀为 8.805 / 9.01 / 1.34，伤害为 1286.76 / 617.52 / 538.97，经济为 505.29 / 432.82 / 302.59，视野为 33.5 / 34.0 / 90。block 6 以“中单补刀稳定：4 局中单……”明确主语；其后“这 5 局内”描述样本窗口，不能无视主语自动改读为把辅助局纳入中单均值。

实际请求的政策要求：

> 按完整上下文确定原文实际断言的对象、指标、组别、期间和量词，再对照来源。同一对象的明确上下文可补足省略，不要求每句重复范围或专门定义稳定等词。

> 完整上下文已足以确定含义且符合来源时，仅改善措辞、强调限定或避免脱离上下文误读的建议不作为错误。

本次 explanation 以“按同句同组（中单）读”为关键前提，认为中单 2.5 对 0.5 使“几乎相同”为假；又认为采用全样本口径会与前半中单补刀、视野断言矛盾。前者忽略了 block 14 的明确口径，后者则错误地要求同一复合句的所有指标必须共享一个组别。报告可以同时描述中单伤害与全样本早死，全文已给出各自范围；这两项描述之间没有数值冲突。

在 block 4 重复“全样本”可能改善局部阅读体验，但依当前政策至多适合一个可选 advisory，不能因此升级为 issue。审计没有靠另一种可能解释替明确错误开脱，而是采用报告中已有的、针对同一断言的直接范围说明。

## 来源与修法核对

所选三项 root 均合法且实际内容绑定：22 为 `source/deterministic`，31 为 `derived/computed_evidence`，32 为 `source/facts_and_provenance`。引用来源根存在只证明其可引用，不能自动批准 explanation 或 suggested_correction 的含义。

逐局数据独立重算如下：

| 组别 | 15 分钟前死亡 | 均值 |
|---|---|---:|
| 全样本胜局（也即中单胜局） | 3、2 | 2.5 |
| 全样本败局 | 7、0、1 | 8/3，展示为 2.67 |
| 中单败局 | 0、1 | 0.5 |

公开 suggested_correction 全文为：

> 在 block 4 明确标注口径：写为“全样本口径下早期死亡胜局 2.5、败局 2.67，差异很小 [K1]；但中单内部胜局早期死亡均值 2.5、败局仅 0.5（方向相反，胜局反而更多），故不构成胜负分界点”。即只为本句补足范围限定并如实呈现中单内部 2.5 对 0.5 的实际差异，不改动其他已核实的指标、数值或结论。

数值本身正确。但中单四局满足 `min([3,2]) > max([0,1])`，在这些所选数据中反而逐局完全分离。“胜局早死更多”不能单独推出“没有分界”；它也不能证明早死带来获胜、长期预测力或稳定关系。K1 所给方法是胜败早死差异很小时，不列为主要分界；中单差异为 2.0，不能直接套用“差异很小”的前提。

同时，“不应把更多早死当作败因或长期预测依据”可由小样本与非因果边界支持。因此不把修法强制读成“中单无任何统计差异”后再制造第二个确定错误。本审计仅指出：该替换把“方向相反”与“故不构成分界”连接起来，已超出单纯补范围；其绝对措辞和逻辑关系尚未得到所引来源直接支持，不应作为已核实的确定修法。实际政策同样要求“不能确认的替换断言不要当作确定修法”。

## 同请求旧结果比较及归因边界

在先独立读本次 issue 和全文后，再比较旧同案：旧结果为 score 95、verdict `pass`、`issues=[]`、`advisories=[{"block":4}]`。

两次 `claim-scope-1-prepared-request.json` 原始字节完全相同。两次实际 request 逐字段比较的唯一差异为 `timeout_s`：旧值 `299.56200000000536`，新值 `299.75`。messages、tools/schema、tool_choice、metadata、temperature、top_p、max_tokens、response_contract 均相同；采样值为 temperature 1.0、top_p 0.95、max_tokens 32768。

这证明同一内容在两次调用中出现不同语义判定。仅凭这一对响应不能断言 knowledge 工具接线修复导致退化，不能确定模型内部原因，也不能估计失败率。新旧 manifest identity 不同，旧成功不授予新运行资格。

## 精确证据绑定

下表文件 SHA 为原始字节 SHA-256；注明 canonical、input、report 或 projection 的条目使用对应既定 digest 表示。

| 证据 | SHA-256 / 标识 |
|---|---|
| HEAD | `1ecd8cd17a82438cb7cf99264f48f340840d55e9` |
| CI run | `36307792122` |
| plan canonical | `7a797831d4e029846bbe2773b85705237e16e293c5e4c5dbc443fe2adc9f322e` |
| qualification manifest | `6be60527f7a8f015737d5afb5a4d67c6151f844affa2be387e283373b93fdebf` |
| candidate | `ac743f164128535a260c1e2a88be02c2dc3ce6aecadb18b873a5c3f6f6d20e54` |
| system policy | `33b11c48b25f3a4dc2879743a0d76dd6c60c0afa4cc1b2b596edacfd967ba8f7` |
| 独立预读记录 | `eb7cebd1470da116a114b48038ad223aca45065c37cb1e235199e95aa2766bb5` |
| 当前 `plan.json` | `97d0a6998660c94497c28d8f8e3845efd3910fc8cd82f488c37a134421648b1d` |
| 当前 prepared request | `f0c89c4338be6d21931e9a6703dd3a9dc5d015d67fc0f2de00e23bafd54db1d8` |
| 当前 actual request | `c825bf9358379b902df5ba3b4bf254ad9c79e8b8ad95c857306d13551149c127` |
| 当前 response | `6f416243bd3f583e13d2f7debd6a2ac530bf07eec9274347d509bc8fb2a14322` |
| 当前 initial journal | `3a7e43453c0ff5f3e42e09e86601af917ef20bf97276810ee96a507464cc31f7` |
| 当前 source 文件 | `ec9d057640a6ca482844296d77c109d43279e99ab45b42158016188b1c221e71` |
| 当前 result 文件 | `4fbf4ac2eb642f98b8c525934cf2f2236a3626e93700d72e4bc102c82931a020` |
| input digest | `f1b773e4f7db1c38fa3e097b1951afa84182ea62ffdee53aba0909ae56ab6227` |
| report digest | `0a07162210fa087073bb8bf881ff883e910b4df57623e7c301e86b3ccc168498` |
| raw tool arguments projection | `dceeea8fa7cced1aa6a8b45641f3c02fce5ece02a4017db608032db35441fa2a` |
| source catalog | `d2d4fd2f8ea5f962695e65be5b0c998f2a57d8f6a64eed7f048a964ffbc37f02` |
| 旧 actual request | `7c60e0413a9a1b6a7d10a24b4b6bc393af20530ca19ca6ed39e40f5d4750b7aa` |
| 旧 response | `72f1d44dae53e3d05847b2f54277b8de51b4761b2aed4131698ebd6ee9fa1853` |

## 交付约束与验证

本审计仅写本说明，没有写入 ready、draft、formal decision 或任何 run 文件，没有修改 tracked 文件，没有发出 Provider 请求。写前与写后均逐件列出当前 run 的 28 个文件并计算 SHA-256；集合与每一项摘要相同。读回说明并计算本说明摘要后交付主 Agent。已有失败保持关闭，剩余十四例未获观察或通过资格；后续封存、canonical/plan/progress、预算及下一步由主 Agent处理。
