# 范围裁决的来源、争议与独立对照

日期：2026-09-19。审计基线：`a2bf015cb1d1f881e27e395248e0cbe853c10119`，
公共 CI：`35374657988`。本文是开发侧证据复核，不是新的用户要求、
模型质量证明、生产准入或旧回执改写。Stage 8E 和既定模型/预算边界不变。

## 结论与本次纠正

先前把冻结正例 block10 选择 `selected` 一概断言为“已证语义错误”，
证据强度不足，应撤回这个过强结论。四场中单是有力解释，但文本也容许
受限于全部五场的读法；“只能是四场”目前是有争议的工程预期，
不是已经单独确认的用户金标准。

这不证明本次模型解释正确，也不使失败变为通过。需要区分：

1. 用户已经确认的完整上下文验收原则。
2. 分析者为具体合成案例设定的预期与解释。
3. 实际报告允许哪些理解，以及模型的证据引用能否支持它选定的理解。
4. 与该争议无关、可确定复现的协议、来源和覆盖缺陷。

后续不得因模型失败而临时换标签，也不得因工程文档反复称其“错组”而
把该解释当作无需审查的事实。当前实际生效的工程合同需要显式更新才能改变；
本文本身不修改运行时规则。

## 用户确认了什么

2026-09-15 18:32:15（Asia/Shanghai）的原始问题先描述了报告开头
“四场中单、逐行方向一致、仅本样本、不外推长期”，然后询问是否采用：

> 完整上下文已明确范围且没有无依据外推，就允许通过；额外措辞优化作为建议，
> 真实事实错误、无依据外推和评估内部矛盾仍然阻断。

用户回答：“采用完整上下文标准（推荐）”。

核查的原始用户记录在：

`C:/Users/33502/.codex/sessions/2026/09/15/rollout-2026-09-15T14-50-12-01a09e6c-6e7c-7632-9f40-2be40cf6851d_01a0a3d4-9394-7313-b521-c5b7050c0db7.jsonl`
第 2934 行，类型为 `response_item/message/user`。该行去掉行结束符后、
按 UTF-8 计算的 SHA256：

`ffd6a79c811ca1dab3d04bf19fdc217803f860a29e4ecf8c991312bfd21b9ef1`

恢复指针包括 `docs/requirements_change_log.md` 的 2026-09-15 节、
ADR-0102 的 “Owner-approved whole-context standard” 节，以及大复盘
`key-user-quotes.md` 的 U462。原始记录优先于索引编号或后来的摘要。

这次回答废除了额外的“稳定必须另有专门定义”门槛，保留事实、外推与
评估一致性要求。问题叙述确实提到四场，但已核查的用户回答没有另行裁定：
新插入泛称标题后的 block10 只能引用四场，或任何五场解释都必须失败。
不能把问题中的背景叙述扩张为用户批准了全部后续工程解释。
正常的工程测试可以由执行方制定，但其案例预期仍须可审查。

## 工程预期如何形成

| 文件或提交 | 可确认的作用 | 不能推出的结论 |
|---|---|---|
| `golden_context_controls_v1.json` | 明写 analyst-authored development diagnostics；`stable_unbounded` 原为短片段“所选比赛观察 / 经济和伤害是较稳定的差异项”，旧标签要求澄清词义 | 该旧标签是用户标准，或原短片段独占四场范围 |
| `run_golden_context_controls.assemble` | 删除原第 3 节第一条风险论述，换入片段；其他章节保留 | 模型仍能看到被删除论述里的明确四场限定 |
| `golden_contextual_reports_v2.json` | 为同字节完整报告建立独立 accept/reject 标签；理由采用四场解释；声明是 independent development labels | 包含显式 `expected_cohort=MIDDLE`，或逐项由用户标注 |
| `run_golden_contextual_review.select_cases` | 校验 manifest、报告哈希和 accept/reject 配对 | 校验了唯一 cohort 或证明该语义预期无歧义 |
| `013dbe106c45c0a842a411933dc10b05b0f4db29`（2026-09-16） | 在 correction policy 中新增跨段保留同一角色/样本，以及“泛称所选比赛不能扩大同位置子样本”的规则 | 这是用户原话，或所有出现泛称标题的实际文本均只能继承最窄范围 |

ADR-0102 的 “2026-09-16 V9” 节记录：`68e8670` 运行的正例取得有效
pass，但人工复核认为其五局解释改变了四场对象，随后加入上述规则。
这说明规则的实际演进路径；不是在否认“不能偷偷替换明确对象”这一普遍
正确要求，而是在核查这份文本是否已唯一规定了那个对象。

`assemble` 删除的原文含“同位置看，中单输局……此处稳定仅指所选四场
中单”等直接绑定。被替换后的待审报告没有该段。原始作者意图和删除前的
文本不能充当模型在新输入中实际获得的证据。

## 待审报告中，两种读法的证据

冻结正例报告 SHA256：

`84e4b38931255f7a3b7e5ce322987eb997302c7f46d922a7aa8ab4682479b219`

**支持四场中单：**

- block3 的经济、伤害比较明确写“中单同位置差距”“所选四场中单”，
  给出 505.29/432.82 和 1286.76/617.52。
- “仅指本样本，不外推长期”紧接这项四场比较。
- block14 又明确列出同位置中单的对应数值。block10 可合理理解为
  对此前这项经济、伤害观察的概括。

**容许全部五场：**

- block3 开头、结尾都说五局，同段还包含混合五局的补刀、早期死亡比较；
  不能把整个段落无条件解释成只谈四场。
- block9 是“所选比赛观察”，block10 只有泛称经济、伤害差异，没有
  “上述四场中单”“这一同位置差距”等唯一回指。
- block13 明确是两胜三负的五局表格，block14 说明其混合位置性质。
- 该真实样本中，四场与五场的经济、伤害恰好均为逐行同向。五场的
  受限描述不自动等于中单能力或长期规律推断。

因此，单看模型用了 `selected`，不足以证明其语义错误。另一方面，
本次模型将 scope_source 指到 block3 的“仅指本样本，不外推长期”，
却没有解释它为何可以支持五局对象；这个短引用紧接四场论述。
其指代关系仍须复核，不能因引用存在或两组同向就认定解释已获支持。
允许竞争读法，不等于免除模型说明其实际对象、范围和引用关系的责任。

这份旧案例的接受标签与“唯一 cohort”应分开：保留原 accept 标签和全部
历史记录；争议的是额外排他的 cohort 预期，不借本次审计将旧结果补记为成功，
也不把任何轻微措辞多义一律升级为用户必须澄清的阻断问题。

## 本次失败中不依赖此争议的事实

运行：`computed-partition-a2bf015-positive-v1/contextual_01`。
一条完整 stop，192.032 秒（stream result 的 elapsed_ms=192032），
12,901 输入 + 19,106 输出 = 32,007 已返回
tokens。未发生二批或修订复评。

只读审计仅查看 response 的 content 及元数据，没有查看或输出
reasoning_content。首批为 6 标题、12 claims、3 source_checks、0 issues：

- 15 个 quote_ref、4 个 scope_source、14 个 comparisons、2 个 summaries
  均采用仅供 first_partial 输入投影的数组，共 35 处；实际首评拒绝。
- 仅在内存按位置解释这些数组后，Partial schema 可解析；这不是可接受
  回执，也不证明其他检查通过。
- 3 条 source_checks 的 4 个 source path 全部无法定位；
  最后一条带“5局”却没有 literals。
- 首条队列解释声称已核对各局 queue_id，却仅引用聚合和 request scope。
- block6 比较“胜局与整体均值”，却选择胜负 comparison，
  且所引 [6,7,11] 缺其声明全组的 [8,9,10]。
- 本批 7 个正文块都有被提到，但仅覆盖 685/757 字符；只有表格 block13
  完整。block5 的能力推断限制、block11 的“极端分化”判断未覆盖，
  另有标点、前缀和知识标记遗漏。
- block2/4/8/9/12 被列 assertion，却没有完整标题 claim。

以上均足以保留“本次未完成”的结论。来源 kind 的省略符合当时
SourceChoice，不是额外错误；未输出全局 score/verdict 也符合首批职责。

## 新的独立合成对照

新增 `data/evaluation/datasets/golden_scope_contrast_controls_v1.json`，
不改旧冻结数据、报告或标签。全部案例和数字由分析者合成，不是用户金标准、
真实玩家记录、held-out 基准或模型表现证据。

五条合成原始行包括四场 MIDDLE、一次 UTILITY 负局，故意让加入辅助后
结果发生变化：

| 指标 / 关系 | MIDDLE 四场 | selected 五场 |
|---|---:|---:|
| 胜局补刀均值 | 9 | 9 |
| 负局补刀均值 | 10 | 7 |
| 胜负补刀均值方向 | 胜 < 负 | 胜 > 负 |
| 胜局经济均值 | 510 | 510 |
| 负局经济均值 | 460 | 1820/3 → 606.67 |
| 经济逐行关系 | 每胜 > 每负 | overlap |

对照包含：

1. 显式四场中单的正确补刀比较。
2. 显式全部五场的正确混位描述，不推中路能力。
3. 跨段唯一指向四场，并使用“较稳定”；不强加专门词义定义。
4. 将五场负局均值冒充四场中单，须发现数值与方向错误。
5. 正确四场观察后添加未来全称预测，须单独拒绝。
6. 明确并列但未消解两种口径，且两者改变真假；要求限定而非挑选能过的组。
7. 明确回到五场总样本，前面四场旁注不能自动抢占指代。

第 6 条的实质歧义与旧 contextual_01 不能混为一谈：新案例明确留下
未消解口径，且真假随口径变化；它不为旧案例强加新拒绝标签。
第 7 条明确包含无效 scope_source 的反例：只引用四场旁注，不能支持
目标明确回到总样本的范围。

支持性事实比较没有新增强制 direct/sample 二选一标签；
未来外推和实质不明范围分别记录 beyond_sample/ambiguous。
评估须同时检查对象、运算、全部操作数和 scope_source 关系，不能仅看
最终 pass。数据内的 expected/rationale/预设组别不得送入模型；
可按方法需要从原始行独立生成覆盖全部组/指标的中立算术目录。

## 证据哈希与复核边界

以下文件哈希在审计基线读取，SHA256 对原文件字节计算：

| 文件 | SHA256 |
|---|---|
| `data/evaluation/datasets/golden_contextual_reports_v2.json` | `35892dc275b4b172edb3fa0a54af8625a59829a39002247b1cf59b0d10d34742` |
| `data/evaluation/datasets/golden_context_controls_v1.json` | `2db781fa8ee7d0bb1ae4c20264c206a8812ccf8561e0e34fd80c77bdb5eb7150` |
| `scripts/run_golden_contextual_review.py` | `093eb47ac4b5bf183f31fb1cc7f0ccaab86e7353ee09ce1a378fdb55e7a36fde` |
| `scripts/run_golden_context_controls.py` | `c3cb53f2479e72d62e367fd9373d274d68da1b4edc978c01a9ecfeb6d1f33e31` |
| 本次 `contextual_01/input.json` | `782d06a1ef9ea47c13227689ec54181ff7aa1ba17f95f8a9e848666f85c467a6` |
| 本次 `contextual_01/response-001.json` | `420be6ed50111cd9e1b81491507080e22d1713c8c541f952a0f32751e315f3d3` |

新数据集文件 SHA256：
`414b5a482786494ecc869a02c035995a51bf0455b1648deced9834107551c841`。
每条 report 有独立 UTF-8 文本哈希，原始 fixture 有明确 JSON 规范化哈希规则；
它们用于定位内容，不提升标签权威性。

本次只校验 JSON、哈希、原文目标唯一性、原始行运算和对照方向。
没有 Provider/网络请求，没有新运行时适配，也没有真实质量或泛化结论。
后续仍须独立审读这些分析者标签，验证评估器是否能在完整上下文中
采用正确口径、修正坏首评并保留全部问题。旧正例“唯一四场”的语义
oracle 仍未确立；用户完整上下文原则本身无需被重新改写。

## 同一观摩语境中的受众归属审计

后续逐字复核发现：旧正例训练段写“同位置自我对比”“自身 4 局中位数”
和“你的手感”；建议段另有“若你想延续中单”。这不是后来改了用户原话
而导致旧标签过期。`run_golden_context_controls.py` 在创建提交
`9c5aad9`（2026-09-15 14:16:44 +0800）就使用：

> 复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。

`68e8670` 实际运行与本次 `a2bf015` 请求中的 user_utterance、完整
report_blocks、source_digest、player、position 和确定性来源摘要逐项相同。
两份实际请求原文件字节的 SHA256 为：

| 路径 | SHA256 |
|---|---|
| `data/runs/inference_development/contextual-review-68e8670-source-v8/contextual_01/request-001.json` | `d95343eb27066edfc7566f08e3a38ee9d3cf98ac8060cf3b37705ac14433fc37` |
| `data/runs/inference_development/computed-partition-a2bf015-positive-v1/contextual_01/request-001.json` | `0dd855d951a78b51f762ae6488adee9802ac7faafe298bb009509f02ec0324ae` |

原始 player 和每场 riot_id 都指向 `DK ShowMaker#KR1`。
position_context 为 `training_positions=[]`、`goal_source=unspecified`，
没有阅读者自己的比赛、训练目标或手感信息。四场中单补刀中位数 8.805
及早期死亡均值 1.5 属于 ShowMaker，不能直接转给阅读者作个人基线。

这里仍须区分文体与事实：若明确采用“模拟教练对 ShowMaker 说话”的框架，
第二人称本身可以成立。旧报告没有明确这种框架，作为观摩者阅读的报告则
存在实际归属歧义。因此不能仅凭“你”字一律判事实错误，也不能把旧的
whole-report accept 视为已经独立审核过受众问题。原标签的理由主要讨论
“稳定”的完整上下文，不足以证明全部受众表达无争议。本次保留原数据、
标签与回执，不追溯改判，不引入所有报告必须使用第三人称的规则。

## 独立完整观摩报告控制样本

新增 `data/evaluation/datasets/golden_observed_review_controls_v1.json`。
它从原 28 块完整正例派生，使用相同 user_utterance 和原始来源，
不替换旧 frozen pair。原编号 1–6 的产品章节与原第 7 节来源全部保留；
原标题保留修订校验要求的 `# RiftCoach 教练式复盘报告` 前缀。

新正例明确四场中单经济/伤害范围，清理建议及训练部分的受众归属：
ShowMaker 的数值是观摩基线，阅读者可以做数值核对、选择观摩方向，
拿到录像后才记录具体场景；未提供阅读者数据或目标时不生成个人阈值或
训练日程。OP.GG 的实际 tier/rank/rate 仍连接观摩对象和待验行动，
但只按指定检索时点的归档快照使用，不作当前英雄推荐或单局原因证明。
没有删除 K1/K2/K3 的知识适用性、官方发布日期与版本职责边界。

作者逐段复读时一并清理了缺乏明确比较口径的“极端分化”、不充分的
“发育正常/影响不了战局”表达，并将实际数字保留为待验录像问题。
所有 16 块修改均有完整 before/after 和理由，不将这些修订伪装成
原报告或模型产物；数据内另有全部 28 块的作者审读记录。

| 新案例 | 相对新正例唯一改变的行为 | 预期 |
|---|---|---|
| `observed_01` | 无；明确范围和受众的完整观摩报告 | 分析者拟定 accept |
| `observed_02_future` | 在四场观察后新增未来所有输赢局的全称伤害关系 | 拒绝无依据未来外推 |
| `observed_03_reader_identity` | 把四场 ShowMaker 比赛明确声称为阅读者本人比赛 | 拒绝明确数据所有者错误，不依赖第二人称猜测 |
| `observed_04_official_date` | 将 OP.GG 检索时间直接声称为官方补丁发布日期 | 拒绝来源角色及日期错误 |
| `observed_05_heading_ability` | 只在亮点标题新增“已证明防抓能力优秀” | 拒绝标题中的指标到能力外推 |

四个反例分别只改变一个正文块或标题块，其他全部正文与新正例一致。
目标原文唯一，报告独立哈希；expected_categories 是可接受问题类别，
定位及类别匹配只能证明检出位置，解释是否正确仍须人工审核。
标签、目标、理由、编辑记录和作者审读内容不得进入模型请求。

新数据集 SHA256：
`8ca4a39f18bb1dca872f9cf1f72cfaba3c92cddb63f36743d59eed7f26bdb132`。
新正例完整报告的 UTF-8 SHA256：
`f6a6c508d2ad86763d01c59edc74a5885ca59867d5a5bfc336072434132a655a`。
source_bindings 逐文件绑定原 source-run 的 player_summary、
deterministic_report、retrieval_evidence、evidence_bundle，原 base_report、
旧 frozen manifest 与原正例输入；路径和原字节哈希写在数据集中。

本次已离线验证来源文件哈希、按编辑记录重建新正例、全部报告哈希、
每个目标唯一、全部 28 块与原章节保留、各反例只有一块变化，以及实际
角色/身份/比赛数、四场均值/中位数/逐行关系、官方日期、OP.GG 检索时点
和知识引用。原表 8.8 是一位小数，四场的 8.81 是同一原始均值 8.805
保留两位小数的显示，不将显示精度差异冒充数据错误。

所有新报告是 analyst-authored/synthetic 开发材料，`held_out=false`、
`model_evaluated=false`、`production_admitted=false`。作者审读状态为
独立复核待完成，不是用户金标准。未调用 Provider 或网络，未形成真实
模型质量结论；数学和结构验证也不能自动证明自然语言接受标签。
