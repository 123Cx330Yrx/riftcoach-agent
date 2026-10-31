# J1/J2之后：同版本与实际消费接线裁决

2026-10-13；普通无付费接续。基于提交 `7f6b9a13`，没有新模型请求、业务run、授权文件、Host任务或资格。J1/J2及旧批原件均保持；批次automation继续PAUSED。

## 已完成的检查

`python -B -m scripts.audit_post_joint_consumption --output <new-file>`只读取提交内封存与源码，以create-only方式输出审计。固定J1/J2 seal和close audit原字节SHA，核二者原件映射与seal绑定；重建四份完整26段来源，核实际发送的正文、policy与两份来源。历史双审按已封存证据引用，不重新产生或补签判断。

实读四个实际Provider响应，使用现有TimedDocumentWorkflow进入编辑请求。每项issue的段号、严重性、分类、来源、解释、修法及顺序完整保留；实际advisories仍在原响应和带原段引用的journal中。`golden_native_partitioned_tool_review.request`有意从编辑输入移除advisories，避免可读性建议升级为必要修改。这不是完整意见丢失，也不应笼统写成所有原始字段都发送给编辑模型。

新机器结果：`data/evaluation/results/post_joint_consumption_20261013.json`。它记录4项实际初评消费、10项明确作者注入的编辑组装，以及原15输入/实际request/schema SHA。作者夹具不是模型编辑或新语义评审，不保存为真实transport回执。

| 离线编辑 | 实际组装与完整终评请求 |
|---|---|
| J1两臂空编辑 | 正确全文逐字保持，仍须完整终评 |
| J2两臂同时修14/15 | 逐字得到J1正确控制，未修改部分和全部非正文输入保持 |
| J2两臂只修14或只修15 | 另一处真错保留；结构组装通过不代表语义通过 |
| J2两臂空编辑 | 两处错误都保留；不能假设有修订调用就已修好 |

每项均核完整新成稿与final request SHA绑定、旧意见不进入独立完整终评、`semantic_approval=false`。没有取得编辑或终评Provider输出。旧H5错误非区分/范围/因果修法的反例继续采用 `audit_correction_consumption.py` 和 `audit_relation_review_failures.py`，不复制为新的模型成功。

## 版本、预算及产品缺口

| 层次 | 当前事实 | 对下一步的约束 |
|---|---|---|
| 教学 | time600原15请求的system逐字等于J1 baseline；baseline本身已有whole-text contrast教学 | 关系教学增量不采用，不能把baseline叫作原始无教学产品或已取得资格 |
| 输入 | 从既有合同重建原15，manifest/input/report绑定保持 | J1/J2不替代原15，不拼历史各版本通过项 |
| 编辑 | 当前time600使用block-keyed编辑；旧qualification绑定review-bound协议和旧300入口 | 对全部15实际请求调用旧身份分类器，均拒绝；需新组合精确证据绑定，不能将新结果塞入旧资格入口 |
| 共享预算 | TimedDocumentBudget已实现同任务5调用、401920 tokens、900秒；GLM600、Flash300受剩余时间截短 | 初评+编辑+终评共享同一账本；三次600/300/600不是各自独立额度。固定15不含自然生成 |
| Host | 旧full15 `wait_reviews`仍用普通dispatch；submit核native但不核run外作者原件；未接当前观测门 | 不直接执行旧full15 CLI；未来三阶段要贯穿作者/库存/观测检查。旧只读replay不能替代发送前门 |
| 默认产品 | native_coach_composition无TimedDocument builder；默认worker组合未接此候选 | 当前可构造请求不等于默认产品已接入，不开放生产 |
| 取消 | ReviewWorker在executor返回后处理maintainer状态，现有timed worker测试只有一次模型调用 | 已有取消/失所有权拦发布；阶段间阻止下一调用尚未证明，须在自然任务接线时补取消信号与两调用回归 |
| 质量 | 四次初评两臂皆过，但旧失败仍成立；尚无同组合完整15和自然消费证据 | 不授资格，不恢复关系教学重试，不用离线组装证明模型编辑正确 |

本次机器文件还固定18个检查源码SHA，便于识别以上结论对应的实现。旧源码没有修补，历史freeze/replay身份不迁移。收尾提交 `7f6b9a13` 的公共CI38381908450本次查询仍in_progress；不是失败，也未宣称已绿。

## 下一工程：前瞻三阶段证据入口

选择这一步是因为当前初评专用入口已有真实作者与观测整链，而完整15入口尚不能安全复用这些门。相比再次换熟悉报告买教学对照，此工程直接解除完整初评→编辑→完整终评验证的执行依赖；它不会解释模型根因或自动解除质量门。

普通无付费实现范围如下，先在隔离入口完成，不改历史runner或封存文件：

1. 保留现有TimedDocumentWorkflow、原15输入和共享预算。前瞻入口使用独立身份及新run命名；无授权时只有prepare/离线测试，禁止借旧run路径执行。
2. 复用HostReviewWorkspace的绝对cwd/Python、checkpoint SHA和run外作者路径，适配`case/{initial,revision,final}`目录。每个业务stage只派唯一任务；后续相同task恢复仍只用MESSAGE。
3. 提交前、native读取之后的提交锁内、等待与下一阶段发送前、transport交接前核同一库存。核独立作者JSON与真实native内容一致；未知文件/作者漂移/身份错配硬停止，不移动文件“修好”旧seal。
4. 每次实际GLM/Flash请求均有run外无正文观测，绑定实际请求、worker与路由SHA。完整响应缺有效观测硬停止；失败尾项允许如实记录缺失，不认成功。replay和create-only seal使用同样规则。
5. 离线覆盖完整initial/revision/final状态机：真实作者文件写入→check-answer→明确标记的模拟native读取→submit→seal；在三个stage分别注入污染、观测缺失/篡改、作者漂移、错误checkpoint、共享预算耗尽，验证无后续发送。模拟native不能冒充真实演练；付费前仍需已有主体的真实无付费路径检验和即时native/启动预检。

完成上述门之后才形成新组合版本和具体验证范围，沿用原质量标准、初评和完整终评；不自动申请历史45次上限、不新开付费批。资格适配必须依赖同组合真实证据，默认产品接线还依赖自然生成/工具、阶段间取消、真实DB/API/UI/journal。阶段8E、Coach/Training、四块联动、前端审美头像、Memory、身份运维、两树整合及独立评估/学习保持未完成。

## 验证

新7项测试覆盖禁网/禁ignored run、两份原件篡改、完整material绑定破坏、错误编辑receipt拒绝，以及四项真实意见到完整终评的消费。首次测试发现审计把journal的带quote建议与原始段号marker直接相比，已按现有合同修正审计断言；未更改模型意见或业务validator。治理与提交检查记录在本次progress。
