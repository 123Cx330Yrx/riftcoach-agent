# 十二条范围对照真实验证

## 1.3.26 真实重验结果与执行方式调整

2026-09-15候选1.3.26真实重验停止：c8450dcba64a52a67ff1b28b75d5a67b1e13c7a9/Actions34918468492同SHA三项success；scope-controls-c8450dc-v8-all实际启动7例、完成6例，5有效且目标匹配、1格式无效，第七例纠正超时、后5例未启动。原含混original_stable一次有效85/needs_revision，正确不借邻段并有非空锚点；selected_means纠正后附加第二JSON对象被拒；stable_local_definition首评背景锚点错，唯一整篇纠正292172ms才出正文，父进程300016ms deadline，无finish/usage，不称length。11次预约，10份完整返回137849+133323=271172tokens，另1用量未知，累计Provider至少155；receipt.attempted=6实际是已完成结果数，input证明启动7。标题及其余未跑例不可宣称修好，无全套质量率或准入。用户质疑连续失败后重新审视执行方式：局部提示叠加及整篇重审纠正仍不可靠，停止原样重复真实全套。唯一下一步改为docs/plans/2026-09-15-evaluation-workflow-reassessment.md的最小审查表示与局部纠正流程离线设计/测量/原型决策，减少原文和身份重复抄写但不放宽证据、语义、覆盖或后缀拒绝；完成新流程离线证据和公共验证后再决定有界实测。保持GLM high/32768/300秒，原报告闭环和Workbench人工稿不变，8E仍in_progress、四块设计后置。

详见[流程复核计划](2026-09-15-evaluation-workflow-reassessment.md)。私有manual-verification.json保存逐响应诊断、未接受前缀的尾部错误、流计量和人工裁决。原始完整及中断证据不可覆盖。本次两条正例有效无误报、两条外推有效检出、一条含混句有效澄清；其余均不能补算为成功。

以下为执行前记录。

## 1.3.26 候选实现（待真实重验）

2026-09-15范围对照修复候选：新增隔离evidence_v8/Coach1.3.26/Skill0.5.26/Program2.3.26/evaluation1.19.0，旧1.3.25及所有失败响应冻结。标题须逐个显式判断navigation/assertion，后者必须绑定完整标题的inference claim；含混锚点明确引用触发原词且非空，不得借邻段定义猜成selected_sample。原canonical原句/证据/覆盖/数值/范围校验不放宽。新诊断独立报告清单差异和局部字段，私有诊断投影只用于定位，不接受或修改旧模型输出；给出范围词导航/含混字段修复规则。84项相关回归通过，旧18响应离线诊断全部反馈无遗漏；完整初评输入57464–57522，旧失败诊断请求投影58502–59752，均<64000，非任意未来最大保证。默认预检零I/O，显式--evidence-scope-v8绑定同基准稿和冻结十二例；high/32768/300秒/每组4调用及原批次预算不变。唯一下一步为本实现同SHA公共三项通过后新身份完整十二例真实重验；不得称离线测试已修好语义。Provider仍累计至少144；8E仍in_progress，Workbench人工稿不替换、四块设计后置。

问题/原理：明确审过每段不等于识别了标题断言；将标题分类作为单独、很小的输出清单，并绑定已有claim，让遗漏可定位。分类本身仍由模型判断，误标navigation仍可能漏检，必须真实语义验证，不能声称程序自动证明了标题正确。

代码地图与流程：golden_evidence_scope_v8验证标题完整顺序、断言与原文claim绑定，再调用未放宽的v5 canonical；golden_evidence_requests_v8明确标题内容、ambiguous锚点和本句定义；golden_evidence_diagnostics_v8独立定位inventory与局部字段，再复用v7数值来源导航；golden_evidence_runtime_v8保留现有一次纠正和安全早停。heading_reviews保存在私有raw journal，规范结果中的标题claims/issues/coverage仍走既有消费者。本候选没有新产品默认或第二模型。

验证：tests/test_golden_evidence_v8.py覆盖普通标题通过、标题漏项/重复/过时拒绝、断言缺claim拒绝、含混标题带原文锚点与other issue可进入修订、无锚点仍拒、inventory错误不遮蔽局部错误、原始输入不变、重复字段不扁平化、畸形诊断输入、真实Adapter一次纠正上限和旧快照/容量不变。连同v3–v7、范围入口与容量共84项通过。旧响应投影仅用于检查诊断和输入大小，没有写accepted结果。

操作：沿用本页十二条运行命令，增加--evidence-scope-v8及全新scope-controls-*身份、对应实现ci-run。保持每例一次纠正、无报告修订，invalid继续独立例、其他运行错误停止。真实结果逐例人工核对及用量审计后才作质量结论，不拼接旧批次。可以表述为“基于完整真实失败证据修复诊断和明确审查合同”，不能说“准确率已改善”。

以下为上一候选真实结果与此前计划。

## 2026-09-15 全套结果：未通过

实现 `d8576beed1622404e2dcc25c5d104526b29275ab`，公共 Actions `34869512903` 的 pytest、postgres-migrations、packaging-smoke 均为同 SHA success。真实身份 `scope-controls-d8576be-v7-all` 已完成全部十二例，未修改候选 1.3.25、基准修订报告、标签或运行中的规则。以下入口准备状态均为历史。

| 类别 | 计划/完成 | 有效评估 | 有效结果符合标签 | 无效评估 |
|---|---:|---:|---:|---:|
| accept | 4/4 | 4 | 4 | 0 |
| reject | 4/4 | 3 | 3 | 1 |
| clarify | 4/4 | 1 | 0 | 3 |
| 合计 | 12/12 | 8 | 7 | 4 |

四个正例没有有效误报。三个有效反例都逐字命中目标，分别拒绝长期、未来及带免责声明的外推。因果反例的两次原始响应均检出因果跳跃，但最终结构无效，不计入有效检出率。唯一有效的 clarify 结果是标题漏检：95/pass、issues=[]，`b09-377608be` 的两类 coverage 均为 not_applicable、scope_ambiguous=false，没有目标 claim。完整覆盖清单并不保证模型识别了标题中的实际断言，不能把 7/8 包装为整体质量通过。

| 案例 | 最终结果 | 人工核验 |
|---|---|---|
| selected_pairs | 有效96/pass | 四局逐行方向正确，明确仅描述本样本 |
| long_term | 有效74/needs_revision | 明确检出四场外推长期 |
| selected_means | 有效93/pass | 617.52 与 1286.755 正确，否定长期外推 |
| original_stable | invalid | 纠正提出正确 other 澄清，但 ambiguous 的 scope_anchor=null |
| stable_negation | 有效96/pass | 合理否定保留 |
| future_without_keyword | 有效74/needs_revision | 没有“稳定”字样仍检出未来全称预测 |
| stable_local_definition | 有效95/pass | 四场逐行方向定义及不外推均保留 |
| original_reliable | invalid | 仍借邻段 b10 定义支持当前含混句，锚点为空；另有数字引用不足 |
| disclaimer_conflict | 有效76/needs_revision | “一贯”外推被拒；附带场次口径意见不作为目标判分依据 |
| reliable_without_keyword | invalid | 两次都正确要求澄清可靠范围，锚点始终为空；最终另有 0.17 引用不足 |
| causal_leap | invalid | 因果问题检出，但背景补刀描述的 selected_sample 锚点不合规 |
| persistent_heading | 有效95/pass但不匹配 | “持续存在”暗示被当作普通标题漏掉，属于明确语义漏检 |

18 次请求均以 stop 完整返回，包含六次结构纠正；其中十份原始响应未过 canonical。逐流 usage 与整套 receipt 一致：241553 输入 + 235050 输出 = **476603 returned tokens**。本批无未知 usage，历史未知仍未知；累计 Provider 预约至少 144（126+18）。单次中位耗时 106.586 秒、最长 279.984 秒，请求耗时合计约 2181.657 秒；最长一例输出 29785 tokens。没有本批断流、length 或超时证据，也不据此认定历史连接问题永久消失。

私有目录保存 plan、每例输入/结果、八份有效 evaluation、十八份原始响应与流进度、每组/全套 receipt 和 `manual-verification.json`；不修改失败稿，不将手工投影写成真实 accepted。原报告的既有自动修订闭环仍然有效，但不足以证明评估器对其他表述可靠。Workbench 人工稿未替换；观摩保存/API/重启回读已完成的事实保持，四块设计继续后置，8E in_progress、8F 未进入。

## 唯一下一步：失败导向的离线修复及回归

先修下列已观察问题，再按新实现公共检查和新运行身份验证；保持 high/32768/300秒及有界纠正，不因本批失败继续加输出额度，也不再重跑原报告修订。

1. 标题按内容判断是否携带能力、因果、群体或持续性断言；“纯标题可不列 claim”不得扩展成标题全部豁免。用普通章节标题与断言式标题做成对回归，不采用“持续”关键词黑名单。
2. 明确 ambiguous 的锚点应引用原文里触发含混判断的词，即使没有有效样本范围也不能 null；selected_sample 仍必须引用本句实际范围词。对背景补刀和单局建议的错误锚点给出可操作诊断，不降低原文匹配要求、不替模型补语义标签。
3. 修正“邻段定义自动覆盖本句”的判断，保留完整上下文用于理解，但要求明确关联和范围证据；当前冻结案例按既定就地定义规则判定，不改标签迁就输出。
4. 诊断需同时报告全局清单和局部字段问题：original_reliable 首次把 b18 的 hash 抄成 b19 的 hash，通用 inventory 错误掩盖了同响应的 selected_sample 锚点错误。错误反馈不能只剩笼统码。直接结果/推断字段搭配和引用不足也要保留具体位置。

新候选保持旧身份、旧响应和基准报告不可变。离线回放只能证明错误定位和协议行为，不能证明新语义已经修复；真实全套重验必须明确记录版本和所有十二条结果，不与旧批次选择性拼接。此前有效反例中附带的措辞意见不自动成为修订要求，例如不得将“中单四场”误改成全部五场。

下面为执行前设计与历史准备记录。

2026-09-15独立对照入口：原ShowMaker报告闭环已于1.3.25有效96/pass验收，本次沿用该候选与修订稿SHA a1cef8b4af58b6e241ba9bb683bb814c7a603d3d4ce9e56b61ad9a8af6e07088，不改模型提示/schema或重跑原报告修订。新增scripts/run_golden_scope_controls.py，将冻结golden-stability-calibration-v1十二条人工开发标签（accept/reject/clarify各4）逐条嵌入已验证完整报告，标签/rationale不送模型。六组每组两例顺序执行，共最多24次、每例至多一次纠正、零修订/SDK重试；每组共享现有high/32768/300秒/401920tokens/900秒预算且另限4调用，全套预约上限2411520tokens/5400秒模型执行预算，不是单报告预算增加。结构无效单列invalid后继续独立案例，传输/认证/额度/其他运行错误停止后续全套；有效漏检/误报/澄清遗漏与invalid分母分开，目标原句绑定避免其他问题冒充检出。28项聚焦及容量回归通过；十二份完整初评输入55378–55436<64000，真实纠正仍逐请求重检，预检零I/O。下一步本实现同SHA公共三项通过后直接执行全套十二例，逐条人工核对目标判定并保存完整结果，不能当独立held-out/生产准入。Stage8E仍in_progress；Workbench四块设计后置且人工稿不替换。

## 问题与原理

原报告修好只证明一个已知案例；用已冻结的不同说法检查评估器是否既漏检又误杀。沿用开发集，绝不称held-out。完整报告每次只嵌入一条案例，完整证据和新候选不变，expected/rationale仅用于返回后的本地判分。

## 执行与验收

入口默认预检无外部I/O；execute检查干净checkout与同SHA三项CI后创建不可覆盖run目录，才加载本地配置。每组复用一个CoachBudgetedProvider，Counted在I/O前预约并私有保存raw。每例保存输入摘要/有效evaluation或invalid结果/调用区间；组与整套均保存回执，中途故障也保留已完成例。整套必须分别报告计划12、实际尝试、有效数和无效数；accept误报、reject漏检、clarify遗漏仅在有效响应中统计，不可用“没输出”当正确拒绝。12/12有效且每类4/4匹配才可声称此开发集通过；仍需人工逐项审查，且不是生产准入。

## 数据与控制流

已验证修订报告+一条待测陈述+原五局/RAG→原1.3.25评估器→必要时一次纠正→canonical校验→绑定目标原句判分→私有原始/有效结果和公共摘要。运行不调用修订器、不改报告或产品默认。结构无效继续独立例，任何其他运行失败停止全套，未知usage保留未知。

## 测试与操作

28项聚焦验证原句匹配、含混other绑定、invalid分母、标签隔离、独立例继续、传输停止、十二例覆盖及原高档容量墙。预检：python -m scripts.run_golden_scope_controls --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md。实际使用全新scope-controls-*身份、execute/env-file/ci-run。可显式选择pair用于后续有依据的局部验证，不允许覆盖旧结果或选择性合并为同批全通过。

## 边界与讲述

代码地图：scripts/run_golden_scope_controls.py（组预算/评估/判分/回执）、app/evaluation/golden_evidence_runtime_v7.py（不变评估路径）、tests/test_golden_scope_controls.py（入口行为）。能够准确表述为“设计有真实返回证据、把结构失败和语义错误分开统计的开发对照”；不能说模型因此从此不会犯错。下一步按完整真实结果决定质量修复或可信报告产品接入。
