# 完整15 time600：执行结果与分支恢复关闭

本批按用户“授权”首次执行，现已关闭：前六例有终态，三例通过、三例语义拒绝或分歧；
第七例初评96/pass完整返回但没有独立审，后八例未发送。完整15未完成，新资格0。
不是把三个成功拼成历史3/15，也不是因一个语义拒绝主动停止其余独立案。

## 实际绑定与关闭

- Backend `D:/riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`。
- 执行HEAD `febe2e7f6dcbefa9fda0df73983fb95c0f3474ce`；公共CI `38048400763` 全success，收尾再核一致。
- 方案SHA `cd737c2b191ce494260c90fbd1f48b0e65766cdd6aaeec6f6febbc34544f75cb`。
- run `data/runs/model_comparison/document-full15-resumption-candidate-20261009-time600`。
- Operator `C:/Users/33502/Documents/Agent/outputs/riftcoach-full15-time600-20261010/switch-recovery-routing-probe`。
- 冻结主审 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4`、独立 `01a1257a-2c8b-7f11-9a86-da3e0b6068b6`。
- runner88932 / wrapper84884退出；exit1，UTC 2026-10-10T14:05:43.132274（北京时间22:05:43）。

原授权UTC12:09:55、Host截止次日UTC12:09:55；最多45调用（GLM30/Flash15）、4354560tokens、
13500活动秒/86400Host秒，单案900秒/5调用/401920tokens，GLM600/Flash300受单案剩余截短。
估价45.029376元不是硬计费封顶。运行期间没有改源码/HEAD、重试、重评、重开或替换主体。
授权前execution-target/recovery-readiness里的未授权标记保留原样，不能盖过后来的authorization。

旧主审最后原生turn为failed/systemError，错误为“exceeded retry limit, last status: 429 Too Many Requests”。
用户在新分支恢复主审后，协作库存只剩root；followup_task不能找到既有独立路径，
向同一真实子thread的应用投递又明确拒绝“direct app-server input is not allowed for multi-agent v2 sub-agents”。
子thread存在、上一turn completed且有final_answer，并不说明新分支能给它派下一个任务。
依本批路由/主体硬故障停止规则，helper在claim-scope:2 initial写入routing_failure，runner关闭。
没有新建独立主体、篡改父子lineage/计划、冒用旧主审身份、代写独立终答或补签第七例。
此次是Codex恢复路由故障，不是RiftCoach GLM超时或语义失败；429本身也不证明账号额度耗尽。

## 七例分别怎样

| 顺序/案例 | 实际结果 | 裁决 |
|---|---|---|
| 1 claim-scope:1 | initial94/pass | 双审接受，正确稿未编辑或fresh |
| 2 claim-scope:4 | initial70/needs_revision | 真错检出，但额外早死issue为误报；双审拒绝，未编辑/fresh |
| 3 claim-scope:3 | initial78→block6必要编辑→fresh94/pass | 三阶段真实全文双审接受 |
| 4 attribution:1 | initial85→block14必要编辑→fresh96/pass | 三阶段真实全文双审接受 |
| 5 scope:4 | initial84/needs_revision | 主审接受、独立认为摘要早死句漏修，分歧原样导入；未编辑/fresh |
| 6 scope:3 | initial80→block4必要编辑→fresh82/needs_revision | 初评/编辑通过；报告本身四项全真，fresh新增泛指误报，双审拒绝 |
| 7 claim-scope:2 | initial96/pass完整返回 | 分支恢复后无法派冻结独立主体，无双审/业务认证 |

未执行：claim-scope:5、6、7、observed:1、2、3、4、5。第七例不是语义拒绝，不能拿false终态
推断报告或模型意见错误，也不把96分替代独立审。第四例的有限成功没有解锁产品准入。

第二例新增issue将“早期死亡胜败几乎相同”强制读成中单，但第14段已明确全样本2.5/2.67；
正确中单2.5/0.5不能反证已限定的全样本命题。该实质误报是本批最早语义偏离。
第五例不同：第14段实际错写“中单2.5/2.67”，独立审认为这还影响未明确口径的总结句，
不能只将总结列advisory。主审原接受观点与独立漏检观点均保留，没有重审求一致。
第六例正确修复明示中单近似句，仅替换block4一句，其他字节不变；fresh却把泛指
“混合位置均值受辅助局强烈拉低”扩成早死/视野方向，忽略表格和第14段对补刀/伤害的区分。
这是实质误报；成稿四项全真也不能抵消fresh评审不合格。

## 用量、原件与核验

13次调用：GLM10/Flash3，全部完整返回；known226429tokens、unknown0、receiptless0。
按未缓存价估算2.5300928元，非供应商账单；实际缓存11776tokens未从保守估价扣除。
活动1146.984秒、Host5654.110秒、墙钟6801.094秒；13次Host等待含最后abort等待。
单案/整批账目和发送时限严格回放通过。scope:3 initial/revision/final发送约50.437/24.641/135.172秒，
本次没有触发原300秒超时；不能由这次135秒断言600保证完成或证明历史超时根因。

公开封存 `data/evaluation/results/golden_document_full15_time600_result_20261010.json`，
SHA `30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576`。
现有helper只读重建请求/来源/报告/stage/账目，实读核全部12个已审阶段的真实native final，
create-only输出156项白名单JSON；302份原件SHA逐项再核一致。封存、收尾Provider0。
原件、receipt、journal及分歧未改写，未公开Provider私有推理、stream或凭据。
操作授权、执行前快照、退出、分支路由故障及历史对照公开留存于
`data/evaluation/results/document_full15_time600_close_audit_20261010.json`；真实事件ID列表也在其中。
独立主体在分支中不可投递，不能声称新增独立收尾复核已经完成；严格回放使用已存在真实事件。
自动任务riftcoach实读PAUSED并保持暂停，没有让旧固定10例自动指令再开新批。

## 历史对照和下一决定

历史2/15、3/15的第二例确实分别84→96/pass、72→96/pass，三个阶段均接受。
本轮同原稿/来源反而新增错误issue，必须保留为回退正反对照，不能只围绕旧第四例加教学。
两份历史seal SHA与本批对照见close audit；没有证明教学扩展、时间标记、随机性或中转是语义根因。

剩余11例旧扫描已完整执行初评和双审：10接受、scope:3修法一处分歧；Flash/编辑/fresh均0。
本次实核其seal SHA `8adfa5cea9b56c063ffb0340b726c55d4c3effbfe86c54738d492f48b00c6baa`，
11份完整原稿和input_json均等于当前冻结controls输入，适合作为逐案参考而非拼成同期15通过。
旧scope:4也只有block14 issue、block4 advisory，但修法显式保留两口径并要求后续相应区分；
新意见与Host分歧分别保留，不把旧接受自动套新输出。后八例依然没有当前版本质量结论。

下一动作是免费核对固定证据中的完整范围解释、摘要/正文修复一致性与Host分歧，
结合旧成功、旧11扫描、本批第二例误报和第六例fresh回退选择机制；先说明策略替换什么负担、
最强反证及最小区分检查，不继续叠近义提示或原样买完整15。另保留分支恢复时冻结协作路径
不可移植的工程依赖；未来批须先证明新root的真实独立路径可执行，但不改旧批身份门。
修复/诊断可独立继续；此关闭批及其剩余额度不得复活，不自动新开付费方案。

默认产品入口未切换。历史2/15与3/15独立、新资格0，正式同版本15、自然消费和8E未完成。
Coach/Training/Review/Evidence四块联动、Worker-DB-API-UI-journal、前端审美/必要重做/头像、
Memory、身份运维、两树整合、独立评估与八维学习仍沿原依赖，不因本批关闭取消或冒认完成。

## 收尾免费核验与策略裁决

本次恢复再次逐项核302原件SHA、12份operator原字节/公开JSON及seal SHA一致；
CI38048400763实读completed/success且head=febe2e7f。没有重新购买或重评任何案例。
执行目录的早期exit.json是付费前退出；实际runner关闭以
preexecution-network-recovery/exit.json的UTC14:05:43为准，二者原件均保留。

已从公开seal读取三处实际issued-request的完整system policy及公开响应，
核的是实际发出的文本，不从当前源码模块名推断旧请求包含什么。

| 固定证据 | 实际请求已经要求什么 | 公开输出的首次偏离 | 能支持的决定 |
|---|---|---|---|
| claim-scope:4 initial | 全文确定对象；同对象上下文可补省略；甲1后文消歧/甲2明确错误不可撤销 | explanation已知道第4节全样本2.5/2.67，却优先按邻近中单解释，新增早死issue | 不能归因于没有后文或缺少消歧教学；保持旧两轮成功作正控制 |
| scope:3 fresh | 不补未写全称；乙1泛指可通过/乙2明确全称须拒绝 | 按最近早死/视野语境扩展泛指，要求修改正确报告 | 同义示例扩充尚未证明充分；先检查实际命题选择而非新增数字证据 |
| scope:4 initial | 修法只修已确认问题及直接影响，不让正确内容抵消真错 | 数值错标被检出，但只给block14修法；Host对摘要是否充分修复分歧 | 独立于前两项误报保留，不将整个范围规则放宽，也不自动重审求一致 |

当前computed_evidence已提供明确两种口径和各指标方向；两个误报解释也引用了正确数字。
因此“补更多统计来源”不是本次已定位的修法。数字查找正确与命题选择正确是两种能力。
现有全文政策已要求先确定实际断言，但这不等于模型稳定执行该顺序。

取舍：停止继续增加同义教学；保留block键编辑和共享预算的有效接线。
下一免费准备比较两条真实可用路径：恢复既有较短教学作为历史对照，以及以紧凑的
“实际命题→全文范围证据→来源冲突/影响结论的未解歧义→直接修法”流程替换扩展示例。
后者仍只调用现有工具、保持现有字段和完整报告/来源，不新增逐段账本或第二次模型调用。
这只是待区分的机制假设，没有选择其为生产修复，也不直接进入新付费批。

最强反证是：较短旧教学并未让旧完整15全过，扩展教学也已有第三/第四例全链正证据；
因此不能从第二例回退直接推导“扩展示例导致失败”或恢复旧教学就能解决全部问题。
最小区分材料应固定同一原稿/来源、实际模型及时间身份，仅变教学/决策组织；同时覆盖
旧成功第二例、当前scope:3修后正确稿、明确全称真错和scope:4摘要/正文混合错。
Host标签只留评测端；后续真实检查才可区分命题选择负担与输出波动，离线政策核验不能。
若正确稿仍被最近语境扩义，或真错被后文正确数字撤销，就否定该简化方向；
不能只按协议通过、字数减少或单例分数择优。新批需另行形成具体可审查方案与授权。
