# 后四例接续完成与原15覆盖库存

用户要求的第12—15例已实际执行完毕：observed:2..5全部初评、必要编辑和fresh全文双审/
真实native导入通过，四个终评为95、95、96、97/pass。唯一runner正常exit0；本批无未执行、
未完成或认证缺口。第11例旧批关闭没有取消后续四例，原失败事件仍保留。

## 本批实际结果

| 原顺序/案例 | 初评与真错 | 实际修复与fresh |
|---|---|---|
| 12 observed:2 | 80/needs_revision；block10无依据未来全称 | 只修block10未来外推，保留样本观察；95/pass |
| 13 observed:3 | 82/needs_revision；block21把ShowMaker样本归读者 | 只修两处归属措辞，保留8.805中位数和1.5早死均值；95/pass |
| 14 observed:4 | 84/needs_revision；block27将OP.GG检索日期当官方发布日 | 只改官方日期为2026-08-25，source36的published_at实际为2026-08-25T18:00:00Z；96/pass |
| 15 observed:5 | 90/needs_revision；block4标题证明防抓能力 | 只把标题改成样本生存/发育结果观察，保留正文K1能力限制；97/pass |

每案均3调用，完整原稿、全部source/input、实际请求/公开响应、机器journal、全部policy、
修法理由及完整成稿逐项主审与独立审；接受的编辑/终评ReportAssessment四项均真。
初评真错的解释、引用和修法有来源，fresh没有实质误报或漏检。其他正确内容精确保留。
泛指不补全称、措辞不升级事实门、Host标签不发Provider、旧分歧不下传均保持。

## 执行绑定、账目与封存

- Checkout `D:/riftcoach-agent-rq192-pr`；执行HEAD `89f2408c704db9af4221c8fd2ada6874bfc6ac62`。
- 公共CI `38068536698`，同执行HEAD所有jobs实读success；本收尾提交与执行HEAD分开。
- 方案SHA `b44521f21789195e3b9a5ccd5b9108d7ad6a6f725111aead79b5331d47f0de1b`。
- 主审 `01a1261f-94b1-7510-8d72-fd5514789015`；独立 `01a1263f-db97-7e02-bd7e-70b3a11b59ce`。
- run `data/runs/model_comparison/document-remaining4-time600-20261011`。
- Operator `C:/Users/33502/Documents/Agent/outputs/riftcoach-remaining4-20261011`。
- 唯一runner86300/wrapper92504，UTC2026-10-10T17:00:53启动、18:10:06退出exit0。

实际12calls（GLM8/Flash4），known202229tokens、unknown0、receiptless0；按未缓存价保守估算
1.5370744元，非供应商账单。活动550.297秒、Host3582.641秒、墙钟4132.938秒，各案活动均小于900。
授权上限12calls/1161216tokens/3600活动秒/86400Host秒及估价12.0078336元未改；估价不是硬计费封顶。
运行源码与HEAD保持冻结，没有第二runner、重试、重评或旧批重开。同任务恢复只MESSAGE，
只有上一独立任务completed/error=null、唯一原生final且submit完成后才派下一stage。

严格只读replay重新实核全部12个既有认证stage的真实native终答、单dispatch和checkpoint；
create-only封存138个公开白名单JSON，260原件SHA前后及seal清单逐项相同。封存/收尾Provider0。
本批无执行偏离；旧两个认证缺口和三项语义问题并未因此消失，原receipt/journal不改写。

公开seal：[`golden_document_remaining4_time600_result_20261011.json`](../../data/evaluation/results/golden_document_remaining4_time600_result_20261011.json)，
SHA `a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec`。
公开operator审计：[`document_remaining4_time600_close_audit_20261011.json`](../../data/evaluation/results/document_remaining4_time600_close_audit_20261011.json)，
SHA `27d8b6b4920a2d65de97284c01255aa31c04a543cc8e33cb8977edfa2e1d8d83`，保留授权前快照、
实际授权/CI/预检/启动退出及12个真实事件/dispatch/checkpoint证据，不公开私有推理或凭据。
自动任务riftcoach实读PAUSED，保持暂停。

### 收尾跨版本读取差异

首次封存使用本批指定的 `C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`
（0.153.4，SHA `444a3f0008050605cae73cd9b7a2dcac61294062dfaab56dd20430fd6498518b`）。
后续独立工程复核改用当前应用附带的0.162.0-alpha.17.2时，12个事件均只在
`raw_event_sha256`出现差异，严格门报 `review_independence_event_envelope_mismatch`。
逐字段比对首个原生事件，确认新版在 `/turn/rootTurnId` 新增非null字段；thread、
collaboration_dispatch与其余turn字段相同，review摘要、任务投递和终答未变。
新版binary SHA `d13914ced6c7af174d8d638db938284231227312104b06a25e9608c632a7daec`，
路径为 `C:/Users/33502/AppData/Local/OpenAI/Codex/bin/2e5e00daee91c61d/codex.exe`。

这是原生读取schema的版本兼容限制，不能解释成Provider语义失败或429，也不能把不同
schema的读取当作原合同严格复核通过。保留首次成功封存与新版失败两项事实，不覆盖seal、
run原件或既有认证摘要；后续升级native客户端须显式处理读取schema与版本绑定。

独立工程随后用指定0.153.4完整只读replay，exit0、重建结果与整个seal完全相等，12事件
逐一相等、260原件前后相等、138白名单JSON相等；实际账目、授权与旧两缺口也独立核过。
5×3静态准备在禁network/Provider、禁run读取及凭据读取条件下精确复建，没有新增业务认证。
其唯一原生终答已实际读取（completed/error=null、单dispatch、任务SHA一致），create-only存为
[`document_remaining4_close_engineering_review_20261011.json`](../../data/evaluation/results/document_remaining4_close_engineering_review_20261011.json)，
SHA `c328f7e852433af127ef57dca69b813081c81eeacabedd719c4e97409adf19a2`。
工程结论accepted=true，唯一nonblocking finding为上述跨版本schema限制，不冒充再次业务双审。
提交前逐字节核Git index；新增四份公开证据用精确 `.gitattributes -text` 保留原CRLF，
避免本机autocrlf转换改变已记录SHA。封存/审计/工程终答/静态准备原字节均未修改。

## 原15例到底推进到哪里

下面是三个独立执行批的覆盖库存，不是合并资格或同批通过率。所有15例均已有初评发送；
10例有其所在批的通过证据，3例语义拒绝/分歧，2例未认证。没有剩余从未发送案例。

| 原顺序 | 案例 | 所在批及真实状态 |
|---|---|---|
| 1 | claim-scope:1 | 完整15批；initial94/pass，双审认证 |
| 2 | claim-scope:4 | 完整15批；初评额外早死误报，语义拒绝，未编辑/fresh |
| 3 | claim-scope:3 | 完整15批；必要编辑，fresh94/pass，完整认证 |
| 4 | attribution:1 | 完整15批；必要编辑，fresh96/pass，完整认证 |
| 5 | scope:4 | 完整15批；摘要/正文修法充分性Host分歧，未编辑/fresh |
| 6 | scope:3 | 完整15批；编辑正确，fresh泛指误报拒绝 |
| 7 | claim-scope:2 | 完整15批；initial96/pass返回，分支路由故障未独立审/认证 |
| 8 | claim-scope:5 | 后8批；initial96/pass，双审认证 |
| 9 | claim-scope:6 | 后8批；必要编辑，fresh96/pass，完整认证 |
| 10 | claim-scope:7 | 后8批；initial96/pass，双审认证 |
| 11 | observed:1 | 后8批；initial96/pass、全文双审，但operator重复NEW_TASK导致native认证拒绝 |
| 12—15 | observed:2..5 | 本后4批；全部必要编辑/fresh通过，12stage认证 |

完整15批与后8批各自结果见
[`full15-time600-result`](2026-10-10-full15-time600-result.md)及
[`remaining8-time600-result`](2026-10-11-remaining8-time600-result.md)。历史2/15、3/15和旧remaining11
也各自独立。第7、11例不重买、补签或追认；第三类Host分歧不能抹成一致。
新增资格0，正式同版本完整15、自然消费与8E仍未完成，默认产品入口未切换。

## 方案决定与下一动作

本批为未来外推、身份、官方来源和标题明确能力断言提供正证据；保留现有完整来源、block键
编辑和fresh接线。不能由四例成功认定旧“按邻近语境扩义”和摘要修法问题已修复，也不能解释
历史300秒超时、中转或429原因。本批没有transport超时，角色600仍受任务900剩余截短。

继续免费准备实际命题与直接修法的共同机制检查，已构造5固定完整请求×3教学组织的静态
对照，业务规则/来源/schema/输出字段/时限不变，仅替教学后缀。具体材料、反证和结果去留见
[`semantic-decision-preparation`](2026-10-11-semantic-decision-preparation.md)。这是可审查准备，
不是新可发送候选或付费授权，不能原样再买完整15，也不先转外围工程掩盖三个语义阻断。

Coach/Training/四块联动、Worker-DB-API-UI-journal、前端审美头像、Memory、身份运维、两树整合、
独立评估与八维学习依赖均保留。已实现基础复用，解除各自依赖后继续，不因本批封存取消。
