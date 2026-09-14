# 直接事实与推断范围：离线设计及失败诊断

状态：离线设计已记录，诊断候选已验证；尚未注册新 Runtime 身份或改变线上验收。

## 问题和决策

scope-v5 的四种 scope 同时承担“陈述是什么”和“推断适用哪里”，导致纯数值表格也必须引用局部范围词。另一方面，模型给 issue 引用了 claim 的子串，虽然人工能理解，严格协议仍拒绝；旧纠正反馈漏掉这个关系错误。两者是不同缺口，不能据此解释全部推理耗时。

新版本拟采用正交表示：`claim_kind=direct_result|inference`，保留原有两类 audit 和逐段 coverage。`direct_result` 的 scope/anchor 为 null，仅表示对指定证据中已观察结果的复述或有明确操作的数值比较；`inference` 必须保留四类 scope 和相应原文锚点。混合“数值 + 稳定/能力结论”的完整原句按 inference 审查，不允许裁掉结论后只报数字。

不采用新增 `direct_observation` scope：它仍把陈述类型混入范围。也不采用放宽正则或给所有句子自动补“本次”：这会偷偷改变待审报告的意思。

重要边界：`direct_result` 不是免检标签。字段校验不能证明自然语言真的属于直接事实。新版本必须继续对完整段落检查遗漏或伪装的推断；未知引用、数值不符、跨位置混算必须拒绝。即使结构通过，也必须通过带“把长期能力伪装成 direct_result”反例的真实语义对照，才可宣称修复。

## 证据引用设计

保留 `scope:limits` 与现有 role 分组键；为实际送达的 generation_facts 建立独立、有版本的可引用索引，而非把模型编造的 `facts:recent_match:*` 自动映射成合法。

每项索引必须绑定实际来源 JSON 路径、被选比赛身份、位置、胜负、字段及值；聚合项另绑定纳入/排除规则、有效/缺失计数、单位和舍入规则。索引由程序从同一份 selected summary 生成，不能由模型填写。单局原始事实可以存在，但未纳入统计的比赛不能进入均值。缺失值不可补零。纯事实至少引用实际值项，不能仅用 `scope:limits` 支持数值。范围内逐行一致需要逐行值或程序计算的方向谓词；仅有均值不证明每场均如此。

实现时复用实际 generation_facts 投影，避免在 prompt 再复制整份事实。新增索引后的首次评估、唯一纠正和修订请求都须重新测量输入上界，保持 high / 16384 输出 / 180 秒 / 5 次调用 / 401920 总上界；本设计不提高预算。

## 开发验收矩阵

以下是人工预期，不是模型测试成绩。

| 原句/情况 | 表示和预期 | 证据要求 |
|---|---|---|
| 中单经济 505.29 vs 432.82 | direct_result；允许没有局部范围词 | 同一 selected summary 的中路赢/输均值、单位及样本身份 |
| 赢局(2)/输局(3)表格 | direct_result；不强迫澄清范围 | 实际全样本分组，不能偷换为四场中路 |
| 这四场中路输局的经济、伤害均低于赢局 | inference / selected_sample；支持 | 四场逐行值，不能仅凭两组均值 |
| 是输局较稳定的差异项 | inference / ambiguous；澄清 | 完整原句 other issue，非 pass |
| 长期经济能力稳定更强 | inference / beyond_sample；当前证据不支持 | 完整原句 unsupported issue，非 pass |
| 一次结果不证明长期能力 | inference / question_or_negation；不因出现能力词拒绝 | 保留否定上下文 |
| 数值正确，末尾却称证明长期能力 | inference；拒绝外推 | 审查完整混合原句 |
| 上句被模型标成 direct_result | 必须作为语义反例检出，不能因结构合法准入 | 真实对照独立判分 |
| 引用不存在的单局编号/只引用 scope:limits 支持数字 | 拒绝证据绑定 | 不推测编号映射 |

已有来源校验脚本重新计算：中路赢局经济均值 505.29、输局 432.815；伤害 1286.755 vs 617.52；两项均满足 max(loss) < min(win)。现有十二条 accept/reject/clarify 各四条为开发集，不是留出集。

## 本次实现与验证

`app/evaluation/golden_scope_diagnostics.py` 是未接 Runtime 的离线诊断器。沿用字段约束，但先独立读取结构，再收集 claim/issue、audit 聚合、coverage 顺序/状态/含混关系，避免第一条 after-validator 把其余错误位置吞掉。不修改响应，不输出验收 verdict，不绕过 canonical。schema/安全 issue 字段不合法仍返回结构错误；它不是对所有自然语言质量问题的完备判定器。

完整 ledger 用于本地复盘；反馈投影最多 12 条、3000 JSON 字符并准确报告遗漏条数。证据清单仍放原事实输入，避免复制一个无界列表破坏反馈上限。原句片段始终是数据，未来接线仍须保留不可信数据封装及 typed 安全早停。

保存响应回放结果（错误数量按 claim 计，可重叠）：

| 响应 | 缺范围锚点 | 未知证据 | 缺逐字 other issue | 反馈遗漏 |
|---|---:|---:|---:|---:|
| 0408809 / response-001 | 3 | 6 | 0 | 0 |
| 0408809 / response-002 | 7 | 4 | 0 | 0 |
| e3826eb / response-001 | 4 | 5 | 1 | 0 |

最后一项精确定位 `audit_index=1, claim_index=3`，为完整“同位置看……是输局较稳定的差异项”；issue 仅取结尾短语。三份响应仍不被原 canonical 接受，没有把回放当成功评估。

58 项诊断/冻结 v5/紧凑覆盖/校准测试通过。正反例测试使用人工标签验证结构行为，其中纯数值例明确重现旧规则仍拒绝；没有假称新事实表示已实现或模型已能正确分类。

## 下一步及完成门

实现上述直接事实证据索引及正交 claim 候选，逐项验证数值绑定、混合陈述、否定、范围外推和输入预算；之后才注册独立 Coach/Skill/Program/evaluation 身份并接入本诊断。冻结 v5、历史回执和 Workbench 人工稿不变。新身份同 SHA 公共检查通过后，执行原报告完整初评→最多一次修订→复评，再做正确事实与伪装外推的真实对照。未完成这些之前，自动漏检修复仍未验收。


## 2026-09-14 候选实现与预算观察

2026-09-14直接事实离线候选：上一批75ecfb07d5c5342de208b8b329e59947837c22c9/Actions34822465677三job success。新增golden_fact_candidate复用实际generation投影并合并role事实，21个事实键/18个来源条目，以完整summary摘要及比赛顺序绑定来源；单局保留排除标志，role均值排除未纳入及无效数值，不混位置。新增claim_kind正交表示及数字到证据字段路径绑定，直接事实无需范围锚点，未知键/错误数值/漏绑数字拒绝；unsupported错误数字仍可携带完整issue，原含混和覆盖门保留。76项聚焦相邻测试通过。明确未解边界：数字正确的长期能力伪装仍可结构合法，返回semantic_approval=false；总体统计仅source_reported非重算，当前数值绑定不支持差值/百分比换算。候选未注册或接Runtime。实际27段请求基础输入估算51486/54496/48088；叠加候选schema及来源索引的离线大小探针60608/63616/57208，纠正仅剩384余量且尚无新策略，不能当完整出站预算通过。下一步先压缩候选重复schema/绑定表示并补齐派生数值操作，测量含策略与纠正反馈的完整候选请求，再决定独立版本接线；保持high/16384/180秒及既有总预算。无新增Provider预约，累计至少108，真实语义闭环未验收，Workbench人工稿不变，8E仍in_progress。

代码入口：`app/evaluation/golden_fact_candidate.py`，测试：`tests/test_golden_fact_candidate.py`。这只是离线结构候选；不输出正式评估结果，不参与自动修订。数值token以ROUND_HALF_UP按原句小数位核对；每个直接事实的阿拉伯数字须有绑定。重复数值是否对应正确对象、非数字限定词是否夸大、所有应审原句是否被列出，仍需要语义审查；测试明确记录伪装外推结构可通过，不冒称已经检出。

可复现大小探针：

```powershell
.\.venv\Scripts\python.exe scripts/check_golden_fact_candidate.py --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --report data/runs/inference_development/inference-dev-11278ba-coverage-report-b/revised-report.md --failed-response data/runs/inference_development/inference-dev-e3826eb-feedback-report/response-001.json
```

探针使用离线Provider，原请求包含同一份generation和role事实，不重复添加其值；额外叠加候选来源及schema是体积观察，不是最终请求接线。不包含新策略，因此63616不能作为实际预算合格回执。源文件在私有data/runs，不进入Git。


## 2026-09-14 派生操作与完整请求测量

2026-09-14派生数值及完整请求离线推进：新增golden_fact_operations独立候选，numeric binding使用op/operands/token，支持原值、顺序差值、单局比例转百分比及同指标比值百分比；拒绝除零、错误单位、混指标、跨role均值运算、错误顺序/数值，ROUND_HALF_UP只在最后按原句精度舍入。复用紧凑coverage并还原后执行原句/证据/issue/范围/coverage校验；旧candidate/v5不改。新增golden_fact_requests构造含完整新策略、替换而非叠加schema、单一可引用事实表、来源索引及有界纠正反馈的离线请求；修订传入canonical claims/operations。保存27段实际输入测量为56262初评/60764纠正/49156修订示例，输出均16384、超时180秒；纠正含48条候选错误经12条/3000字符裁剪，修订是scripted_not_maximum，非所有后续报告的预算保证。90项聚焦/相邻测试及编译通过；无Runtime注册、真实请求或语义通过，累计Provider预约仍至少108。下一步为将操作候选诊断补齐后注册独立Coach/Skill/Program/evaluation身份，复用这些完整请求构造器并保留实际出站输入预算检查、一次纠正、typed安全早停及canonical修订持久化；完成同SHA公共检查再执行新身份真实report-only，不能将direct_result结构合法当语义准入。8E仍in_progress，Workbench人工稿不变。

代码：`golden_fact_operations.py`负责计算和canonical校验；`golden_fact_requests.py`提供离线完整请求构造；`check_golden_fact_requests.py`提供无网络测量。候选合同名称offline_fact_candidate/0.0.2未注册为正式身份。

操作含义：value取原字段；difference=a-b；percent只支持明确比例字段乘100；ratio_percent=a/b*100，不是增长率或百分比变化。百分比变化尚无操作，禁止把ratio_percent误用为变化率。两元运算检查相同指标；两个role均值必须同位置。单纯正确计算仍不证明自然语言对象、因果或能力归因正确。

完整提示保留安全策略、位置/来源/报告策略、两类audit、逐段覆盖、含混与unsupported对应完整issue、否定上下文、直接事实伪装检查、短解释要求。结构schema在正文仅出现一次，另由response_contract传递给适配器。两个位置的schema都计入预算。事实值仍有基础审查投影，但生成事实不再作为第二个generation_facts注册表重复添加。

复现命令：

```powershell
.\.venv\Scripts\python.exe scripts/check_golden_fact_requests.py --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --report data/runs/inference_development/inference-dev-11278ba-coverage-report-b/revised-report.md
```

测量不是实际模型用量；修订用人工脚本构造的含混标签，只为测量输入形状，不是正式评估。完整真实循环尚未开始；后续修订文本变长、真实issues变多时须重新执行实际输入预算门。当前诊断参数仍由调用方提供；独立版本注册前必须接入适用于新操作/新scope空值的诊断器，不可直接使用只认识v5结构的旧诊断。


## 2026-09-14 独立Runtime版本接线

2026-09-14事实推断独立版本接线：新增fact_v1/Coach1.3.17/Skill0.5.17/Program2.3.17/evaluation1.11.0，合同快照7f1ca3c6b5efe2a449d8ecadb0e98a8591f2eb5e2d2d91563ad2af571d62aa02。复用完整候选请求及实际输入预算门；新增含原句/计算binding位置的固定错误码诊断，与issue/coverage关系共用ledger，最多12条/3000字符。原始JSON保留到canonical展开校验，完整绑定持久化并传入修订；初评/唯一纠正的typed prompt_injection均单次安全早停，超输入预算在I/O前拒绝。--fact-inference仅允许独立expanded-output/report-only，五调用/一次修订/high/16384/180秒/401920上界不变。旧1.3.16快照及资产保留。实际Adapter保存27段首评/纠正/脚本修订输入估算56254/56726/44034，全部16384输出；这里纠正回放旧schema失败，修订脚本为空audit形状，不能当最坏修订预算，完整有界诊断候选上轮60764仍是参考，真实每次重检输入。两组122项及134项回归通过（存在重叠），编译/治理通过；真实入口无I/O预检绑定同一96分稿SHA。上一批cc49f9e/Actions34825603586已三job success；本批待同SHA公共三项后执行新身份fact-inference真实report-only，按完整初评/至多一次修订/复评审查，不运行controls或替换Workbench人工稿。Provider累计至少108，无新增真实预约；语义伪装、真实完整返回与自动漏检修复均未验收，8E保持in_progress。

`golden_fact_runtime.py`连接已测构造器与既有ToolRuntime/CoachBudgetedProvider。`golden_fact_diagnostics.py`先读取字段结构，再收集关系和运算错误；不自动修改任何响应。新资产位于`examples/runtime_profiles/flash_v2_golden_fact`，内容指纹包含事实、运算、提示、诊断及接线实现。新标识不等于默认或生产准入。语义评估仍可能误分类，尤其伪装为direct_result的能力结论，必须通过后续真实对照验证，不能以本批结构测试宣称修复。


## 2026-09-14 实际终态失败及后续边界

2026-09-14 fact-v1公共及真实观察：实现3b82b97e72cf73a5f5e109c736d46debf76b7dd4/Actions34826646827三job同SHAsuccess。新身份inference-dev-3b82b97-fact-report/Coach1.3.17/high/16384/180秒仅1次Provider预约；6.735秒首reasoning、130.735秒首正文、164.563秒length/EOF/close，正文12793字符/reasoning33263字符，输出未完成。子progress为12875输入+16384输出=29259已观测tokens，父receipt因没有完整响应仍为0，这不是零费用。失败assembly_rejected/incomplete_stream、provider_code=null；尽管末HTTP事件failed，本次有明确输出耗尽证据，不是180秒截止或已证明网络故障。无accepted evaluation、纠正/修订/复评/controls均未启动；不能判断新版本是否检出两处原漏检。累计Provider预约至少109，历史未知用量继续保留。输入预算与结构接线通过不代表终态可完成；新增逐数字绑定增加输出义务，但尚无证据将全部推理耗时归因于它。旧v5完整响应有13条claim、逐claim去重数字合计52个，仅作历史形状参考，不冒充本次截断正文。停止原样重试，不继续增加预算。下一步离线重审逐数字强制绑定的必要性及代价，比较程序预计算/原句级证据引用与当前模型逐数重述，保留完整段落覆盖、事实/推断区分、原句issue绑定、一次纠正和高档预算；以可复现大小/正反例证据选方案后才发新版本真实请求。Workbench人工稿不替换，自动语义闭环未验收，8E仍in_progress。

私有证据：`data/runs/inference_development/inference-dev-3b82b97-fact-report/plan.json`、`call-001.json`、`receipt.json`、`full-report/stream-001/progress.json`、`failure.json`、`result.json`。未形成response-001.json，不能用截断片段拼接成有效评估，也不能把旧响应改造为新版本的成功证据。上述已观测用量并未计入父receipt，人工账目要单列而非覆盖原回执。

设计复审重点：先确定逐数字绑定相比原句级引用实际多阻止了哪些错误，以及哪些对象/语义错误依旧只能由模型判断；预计算可减少模型算术和输出，但不能悄悄将错误文本正规化。候选比较需保留数值错误、错位置、否定、局部方向和伪装外推反例。当前运算模块可以作为离线证据核对工具保留，不必因为已经实现就强迫每次语义审查输出全部绑定。不得在没有对照证据时再次宣称缩短输入或压缩schema解决了终态预算。


## 2026-09-14 计算支持移至程序侧

2026-09-14用户要求持续定位解决、不再停等确认：新增evidence_v1/Coach1.3.18/Skill0.5.18/Program2.3.18/evaluation1.12.0，移除模型逐数字numeric_bindings输出要求，保留原句、实际证据引用、直接事实/推断分类、局部范围、逐字issue和紧凑coverage。新增程序侧golden_numeric_evidence从实际引用的允许数值字段核对原值、同位置同指标均值差/比值、明确比例字段转百分比等，输出本地候选来源ledger；未知来源、无证据数字、跨位置均值差和错比例仍拒绝，unsupported数字错误仍允许形成对应issue。边界：支持搜索证明可由引用值计算，不证明语义对象或因果/能力；数字重合/错误分类仍须模型语义反例检验，不宣称完整证明。旧运算绑定工具及1.3.17身份冻结。实际适配器27段输入估算53808/54280/43912，纠正回放旧schema失败、修订为脚本形状，真实每请求仍检查64000输入；high/16384/180秒/5次/401920总上界不变。两组63及172项检查通过，编译/治理通过，无I/O入口验证绑定同一原报告；本实现待同SHA公共三项通过后直接执行新身份--evidence-scope --expanded-output --report-only，检验完整初评/至多一次修订/复评，不停等用户授权。Provider累计至少109，此版本尚无真实调用；Workbench人工稿不替换，8E保持in_progress。

选择依据：逐数绑定即使完整，也只证明模型选出的数值与字段对应，不能证明整个自然语言结论正确；让模型重复输出每个数字的运算记录增加了协议成本。新方案从引用证据中的允许数值字段生成候选，按原句精度ROUND_HALF_UP核对，保留来源和操作候选，不修改原句。指标标识、比赛ID、玩家ID等不作数值候选；比例字段的百分比、时长秒转分钟、死亡统计窗口仅使用显式定义。两元均值运算仅同位置同指标，零分母不生成比值候选。

代价与保留边界：不再要求模型指出每个数字的唯一字段路径，程序可能发现多种计算来源；数字巧合或相同数值的对象错配仍必须由模型审核。测试明确保留“数字正确却声称长期能力”的结构可通过例，作为尚未解决的语义反例，不把此结构测试当检出成绩。旧OperationBinding校验工具仍可离线用于人工指定路径的核对。

新实现：`golden_numeric_evidence.py`、`golden_evidence_scope.py`、`golden_evidence_requests.py`、`golden_evidence_runtime.py`。新资产目录`examples/runtime_profiles/flash_v2_golden_evidence`；合同SHA `ef2f3852912fea2ed68296564a75f538dba8e2abdac67e6e38344cc6ce3a3141`。沿用实际出站预算、一次纠正、安全早停与canonical修订传递。真实接口只增加独立evidence-scope选项，不能混用旧scope/fact标志。


## 2026-09-14 真实完整返回后的提示及窗口修复

2026-09-14 evidence-v1真实失败定位与v2修复：07d777225db594b171173faa591d36deacff129a/Actions34828768377三项success。inference-dev-07d7772-evidence-report两次完整stop返回，分别72.641秒/12641输入+7515输出、80.078秒/13254输入+8360输出，共41770 returned tokens；累计Provider预约至少111，历史未知用量保留。两份raw均pass/95/issues为空，仍漏两处稳定措辞；canonical均拒绝，没有accepted evaluation或修订。确定缺陷：提示“原句1到20字符”被两次机械理解为前20字符，每份6条selected_sample_anchor_missing；总体统计deaths_before_15没有生成窗口15支持，正确表格被误拒。新增独立evidence_v2/Coach1.3.19/Skill0.5.19/Program2.3.19/evaluation1.13.0，明确从原句内部选真正范围短语及稳定含义须在判断处定义，不能借同段其他位置场次数；总体统计补实际10/15分钟窗口支持，伪造16仍拒绝。旧身份/资产冻结。旧两份响应离线回放只剩各6条范围错误，没有改写或接受旧结果。两组50及144项测试通过；无I/O预检绑定原报告9687ea5b4c91eb962dc9f88f0b93f1b408ed3c9c64cc2fb2422f11e72b59fd82。实际Adapter输入上界54316/56332/44420，纠正用真实旧失败，修订仅脚本形状；真实每请求仍重检输入。high/16384/180秒/5次/一次修订/401920及900秒整批不变。下一步本实现同SHA三项公共检查通过后直接执行--evidence-scope-v2 --expanded-output --report-only，验证完整初评/修订/复评和两处实际issue；不等待额外授权，不将结构通过等同语义通过。Workbench人工稿不替换，Stage8E仍in_progress。

代码：golden_evidence_requests_v2.py、golden_evidence_scope_v2.py、golden_numeric_evidence_v2.py、golden_evidence_runtime_v2.py；新资产flash_v2_golden_evidence_v2，合同SHA ad87caaa870f2975e5fc84121c38d4c26e89fe7a8588c9b0bdf97054b961333e。数字计算支持仍不证明语义对象或能力归因，伪装外推真实对照仍待后续验证。


## 2026-09-14 单次容量与整批上界分离

2026-09-14 evidence-v2真实截断及容量修复：db9567eead3939e00dd292520ee4ed4145f0e5aa/Actions34830493778同SHA三项success。inference-dev-db9567e-evidence-v2-report仅1次Provider预约，8.906秒首reasoning、126.453秒首正文、155.141秒length，16384输出用满、JSON未完成；输入12793+输出16384=29177已观测tokens，父receipt因未交付完整响应仍0，非零费用。累计Provider预约至少112。无accepted evaluation/修订/复评，v2两处提示/窗口修复尚无真实语义验收。基于再次实证截断，执行方决定为独立Coach1.3.20/Skill0.5.20/Program2.3.20增加单请求容量32768/300秒，替代此前本次任务“保持16384/180秒”的执行选择；用户未指定这些数值，亦与Luna无关。high、5次调用、一次修订、401920整批tokens及900秒整批上界不变；这不是保证5次都能满额，后续请求必须满足实际已用+输入估算+本次输出预留，否则I/O前拒绝，单次超时也取整批剩余时间。语义提示/schema1.13.0/evidence_v2完全沿用，旧身份/快照/资产不改。新capacity_v1接线与独立golden-process-stream-high-32768-v1贯穿策略、预算、父子进程、SDK、assembler及1.3进度观察；只该白名单策略可使用360秒外层工具/传输包络。离线57项聚焦测试通过，证实240秒/20000输出完整响应可交付、32768/high实际到SDK、length及超额仍拒绝，总token/时间/调用限制仍生效；相邻176项及策略/工具预算18项回归通过（与聚焦组有重叠），编译/治理通过。无I/O预检绑定同原报告9687ea5b4c91eb962dc9f88f0b93f1b408ed3c9c64cc2fb2422f11e72b59fd82和401920总额。下一步本实现同SHA公共三项通过后直接以--capacity-output --evidence-scope-v2 --expanded-output --report-only执行完整初评/修订/复评，按原两处含混问题实际处理情况验收；不能仅凭完整响应或结构通过准入。Workbench人工稿不替换，8E仍in_progress。

新合同SHA d5a7a36859be4973fa13b0aa260d9707b72a607b6e7086c2e5e0510a23d6e1bf。32768位于已查官方128K输出上限内；按最新约155秒消耗16384的观察增加单次等待余量，不保证Provider速度或语义质量。CLI真实回执直接记录冻结整批401920，不能错误写成5*(64000+32768)。现有CoachBudgetedProvider在每次I/O前检查累计实际用量加本次输入估算及最大输出，并在异常时停止；不会把未知失败用量归零后继续花费。


## 2026-09-14 进度计数与引用统计缺口

2026-09-14容量真实观察与进度/数值补全：fd0bdffb7ebc9da6f85570ccfb523971e50d9abd/Actions34832094213三项同SHAsuccess。inference-dev-fd0bdff-capacity-report初评159.235秒完整stop，12793输入+16247输出=29040 returned tokens，raw needs_revision/82，已正确提出两处完整稳定措辞的other澄清issue；canonical因4项缺口拒绝。唯一纠正154.328秒中断，events恰为16384、无finish/usage，费用未知；累计Provider预约至少114。无accepted evaluation/修订/复评。发现并离线复现：进度模型继承events<=16384，实际通道允许32768/65536，第16385次赋值即ValidationError，足以解释真实边界中断；旧failure仅worker_failed/provider_code=null，不能冒称保存了真实异常类型或Provider根因。修复两个进度子类事件上限与各自assembler一致；真实流形状17002事件测试完整交付且关闭资源。新evidence_v3/Coach1.3.21/Skill0.5.21/Program2.3.21/evaluation1.14.0补引用单局的同位置mean/median，去重、排除未纳入及无效数值，不跨位置/补零；队列ID按原句标签和实际引用queue_id核对，不拿巧合统计数字或request.queue顶替；局数候选只用于局/场计数。上表锚点须存在前置表格，混合位置均值仍不是有效范围词。旧raw回放均值/中位数两项误拒消失，只剩引用不充分的queue及旧非范围锚点，未改写或接受旧响应。high/32768/300秒/5次/一次修订/401920整批tokens/900秒不变。155项相关回归通过；实际Adapter27段输入54680/55610/44782，输出32768，纠正回放真实失败、修订仅脚本形状，非最坏保证。下一步同SHA公共三项通过后直接--evidence-scope-v3 --expanded-output --report-only真实初评/修订/复评；必须核实两处issue、修订保留正确事实及复评完整有效。Workbench人工稿不替换，8E保持in_progress。

新合同SHA 730bca4032e386b2c3d44fa0c2425f8dc53a91dcfda1afc3f59d369b980e1eea。数值支持仍只证明可计算性；选错对象、只引用部分比赛却声称全部或将正确数字伪装成长期能力，仍须完整语义审查及后续真实反例，不声称已彻底解决这些语义边界。


## 2026-09-14 单一结论来源与展示精度

2026-09-14覆盖协议及展示精度修复：4fb5b82b614acc84c53438e15d40b96386b3cb43/Actions34834017775三项success。inference-dev-4fb5b82-evidence-v3-report两次均完整stop，150.344秒/12892+15999及142.765秒/13148+14701，共56740 returned tokens，累计预约至少116。初评80/needs_revision有两处稳定澄清，但模型抄表格时移位分隔行、混合样本2.35差值未被现核对支持；唯一纠正JSON尾部多两个反引号，完整对象另有coverage与claim不一致，仍无accepted evaluation、未修订。纠正raw对象74/needs_revision共5issues，其中3条把8.805展示8.81错误要求改8.80；只从JSON完整前缀做离线诊断，不改写或接受旧回执。新增evidence_v4/Coach1.3.22/Skill0.5.22/Program2.3.22/evaluation1.15.0：模型输出完整顺序reviewed_blocks及逐条claims，程序派生coverage与audit聚合状态；不再重复要求模型填写冗余状态，原句/证据/unsupported及ambiguous逐字issue/nonpass/完整段落清单仍验证。仅允许完整JSON对象外的1至3个尾反引号，额外文本/第二JSON/重复键仍拒绝；Counted原始journal保留，typed安全停止与一次纠正不变。明确混合样本可核对同来源同指标赢输均值差，但不支持跨位置能力推断。明确来源half_even_6dp与展示ROUND_HALF_UP不同，8.805两位为8.81，不把合法展示报事实错误。旧纠正响应只做新表示投影的离线比较：claims及5issues逐字保留，派生27段后结构可校验；其中3条舍入误报仍是语义错误，该投影不是真实评估或质量通过。176项相关回归通过，最终精度提示/资产更新后15项聚焦再次通过。实际Adapter输入54050/54534/45206，输出32768；纠正来自旧schema失败、修订脚本形状，非最坏保证。high/32768/300秒/5次/一次修订/401920整批tokens/900秒均保持。下一步本实现同SHA公共三项通过后直接--evidence-scope-v4 --expanded-output --report-only真实初评/修订/复评，人工复核两处澄清及舍入误报没有污染修订；Workbench人工稿不替换，8E仍in_progress。

新合同SHA c4043c1f1625cc30353e6a6718d747f95826ff66aa615ec4d5d42605b3f63a27。程序派生不会添加或删除claim/issue，unsupported优先，范围含混仍要求具体问题；完整reviewed_blocks核对顺序、数量及内容摘要。但清单本身不证明模型真的理解或未遗漏陈述，原coverage也不具备该证明能力，仍须后续真实语义对照。尾部格式容错只作用于完整对象外无语义字符，原始响应保留，不拼接截断JSON。


## 2026-09-14 单局范围别名

2026-09-14单局范围误拒修复：562d5c672e22c1e41e0faf5dfe74d694d23f417e/Actions34835954691三项success。inference-dev-562d5c6-evidence-v4-report两次完整stop：142.187秒/12936输入+15940输出，141.421秒/13291输入+16124输出，共58291 returned tokens，累计预约至少118。初评78/needs_revision/3issues因表格漏分隔行及queue引用不充分拒绝；唯一纠正已修表格/queue且只有原两处other澄清问题（80/needs_revision），没有舍入误报，但“单局复盘”被旧范围正则误拒，故仍无accepted evaluation/修订/复评。新增独立evidence_v5/Coach1.3.23/Skill0.5.23/Program2.3.23/evaluation1.16.0，仅补单局合法范围及其提示，拒绝单局限/同位置等非范围词；派生coverage、格式边界、数值/引用/逐字issue/安全/预算保持。未修改的旧纠正响应在新规则下离线校验为80/needs_revision/2issues/27段，未写入真实accepted结果，不冒充模型实测。168项相邻回归通过；无I/O入口绑定同一原报告及high/32768/300秒/5次/一次修订/401920/900秒。额外测量带完整真实2issue及全部canonical audits/coverage的修订输入60920<64000，输出32768；只是实际旧响应形状，不是任意后续结果最大保证，真实每次仍检查。下一步本实现同SHA公共三项通过后直接--evidence-scope-v5 --expanded-output --report-only真实初评/修订/复评，确认两处原问题澄清且正确数字保留。Workbench人工稿不替换，8E仍in_progress。

新合同SHA 8c4a7c289ed8d9334b61d25455000f10e185937f63149c844a73184de1d839cb。


## 2026-09-14 分类、重复字段与修订阶段输入

2026-09-14评估误分类与修订输入修复：6adc473cfcfdd530ced16708b180b5b02841e35f/Actions34837483428三项success。inference-dev-6adc473-evidence-v5-report两次完整stop，141.625秒/12953+16787、185.453秒/13197+21035，共63972 returned tokens，累计Provider预约至少120。两个响应均检出原两处稳定措辞；首评另有风格接近问题但issue截句，以及引用目录误标推断且缺scope_anchor。唯一纠正修了完整issue却将目录标ambiguous/supported无issue，并在issues[2]重复evidence键；canonical拒绝，无accepted evaluation/修订/复评。新增独立evidence_v6/Coach1.3.24/Skill0.5.24/Program2.3.24/evaluation1.17.0：明确全篇审查与两类claims的区别，目录仍审查来源安全，混入实际推断仍须列claim；禁止同audit同句重复scope和issue截句，区分指代含混与明确事实错误；新增重复JSON字段路径诊断，重复值相同也拒绝，不删除模型claim/issue或放宽canonical。修订改用阶段专属说明，完整评估/报告/证据仍逐字传入；最新响应去重且移除错误目录claim的离线大小投影（非真实accepted结果）保留4issues/28claims，旧修订66504、新62912<64000，初评54816/纠正55332。只是此响应形状，实际每请求仍重检。165项回归通过，预检绑定同原报告及high/32768/300秒/5次/一次修订/401920/900秒。下一步同SHA公共三项通过后执行--evidence-scope-v6 --expanded-output --report-only，核对两处含混实际澄清、正确事实保留与有效复评。Workbench人工稿不替换，8E仍in_progress。

程序不根据“内部知识引用”前缀删除claims，不自动修正文案、不合并重复键；真实旧响应保持拒绝。离线投影只用于测量后续修订大小，不能算真实审查通过。独立合同SHA eb17649af753c63bd96ca30a02b4e993f2fc2a287b9cb99040261418bec139d5。


## 2026-09-14 可操作的数值与原文诊断

2026-09-14纠正反馈补齐：37c65b907bed8c524de2ec2f3ff5f87045b0efff/Actions34839342262三项success；inference-dev-37c65b9-evidence-v6-report两次完整stop（148.343秒/13162+16147；157.656秒/13346+17337），共59992 returned tokens，累计Provider预约至少122。目录误分类/重复字段未再出现，原两处含混稳定均检出；首评只剩队列420未引用实际单局queue_id，唯一纠正仍只引aggregate/scope并抄漏表格分隔行，canonical拒绝，无accepted初评/修订/复评。纠正建议另把505.29赢局均值写成单局经济，是语义错误，失败稿未进入修订。现新增独立evidence_v7/Coach1.3.25/Skill0.5.25/Program2.3.25/evaluation1.18.0，保持v5 canonical及v6阶段专属修订，补具体unsupported_numbers、实际来源字段候选及抄错quote相似原文块；来源候选仅导航，不证明语义对象/胜负/单位，程序不修改旧响应或自动接受。旧两份失败回放精确定位420及五场/queue_id、完整原始表格，现有12条/3000字符边界无遗漏；提示明确表格需连续逐字复制。142项相关回归通过，原响应仅作离线输入大小投影54978初评/56958纠正/57868修订（非最坏保证，非真实accepted）。预检绑定同原报告，high/32768/300秒/5次/一次修订/401920/900秒不变。下一步本实现同SHA公共三项通过后直接--evidence-scope-v7 --expanded-output --report-only真实初评/修订/复评，核对错误建议未污染正确数据。Workbench人工稿不替换，8E仍in_progress。

数据流：失败原文→严格JSON诊断→列出原引用不支持的数字→在允许来源中搜索可计算候选→有界反馈→模型重新审查→原canonical再次校验。相似块仅提示回看原文，不做模糊匹配验收；没有来源的421测试不会拿request.queue=421冒充比赛事实。独立合同SHA 086cf0b4150de5cd1c28f319d37353b06c832e90b57c2efc490af8c4ae769655。


## 2026-09-14 原报告自动闭环验收

2026-09-14原报告自动闭环真实通过：c69cb3ea560a2ff6a10f105ed3a366843d2161d6/Actions34840972315同SHA三项success。inference-dev-c69cb3e-evidence-v7-report共4次完整stop：初评113.672秒/13211+12396，修订15.734秒/15647+1692，复评97.703秒/13303+10353，复评唯一纠正106.047秒/13539+12255；合计55700输入+36696输出=92396 returned tokens，累计Provider预约至少126，历史未知用量仍未知。有效初评72/needs_revision/3issues：原两处稳定范围含混及风格接近无证据/输赢指代含混；直接进入唯一报告修订。第一次复评raw93/pass因一条selected_sample锚点不合规被拒；唯一纠正为有效96/pass/issues=[]、27段完整coverage，receipt.stopped=false。独立逐行人工/算术核对：只改原报告第5/15/32行，其余行完全相同；两处判断都定义所选四场中单逐局方向一致且不外推；删去风格接近，明确洛克负/辛德拉胜及36.4%/55.8%、605.5/1430.11对照，数字与真实行一致；8.81及其他正确值保留，未把赢局均值当单局值。修订稿SHA a1cef8b4af58b6e241ba9bb683bb814c7a603d3d4ce9e56b61ad9a8af6e07088。有效初评/修订稿/有效复评/receipt/manual-verification均保存在私有run目录，未修改原失败证据。此原报告的有效初评→修订→有效复评目标已完成；不代表独立语义准确率、长期可靠性或生产准入。下一步为基于当前候选的独立真实正反例及含混对照验证，区分正确样本事实、合理否定/假设和伪装长期能力；不再重跑已通过的原报告，Workbench人工稿不自动替换，四块设计仍后置，8E保持in_progress。

验收教训：传输完整、模型raw verdict、canonical接受、修订内容正确和独立语义质量是不同证据层。此次原报告四步均有实际文件，不把此前失败或离线投影追认为通过。v7新增数值/原文诊断已由离线回放和运行时模拟验证；本批首评直接通过，复评纠正修的是范围锚点，因此不能声称此次真实使用并证明了新数值/表格反馈的有效性。最后一批执行耗时约333.156秒（四流之和，不是精确整批墙钟）；high及既有单次/整批上界未再增加。此接续新启动v6/v7共6次，152388返回tokens；接收上轮v5最终回执另63972，三批观察总216360，不能把旧未知用量记零。
