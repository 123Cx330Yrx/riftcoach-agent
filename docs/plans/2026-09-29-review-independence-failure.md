# 2026-09-29 真实批次独立审查身份失败审计

后续状态见2026-09-30-429-recovery-audit.md。本文初始裁决的“下一例零调用”
已被下文“回执更正”推翻，现行事实为1个unknown/incomplete请求；保留初稿作为
历史，不得据其旧陈述重新记账。旧批原件不改，新增真实资格仍为0。

当前冻结批次 golden_boundary_examples_host_timed_preparation_v1 在第一例
claim-scope:4 完成了真实三次模型链：初评 80 / needs_revision，Flash 修订，
GLM fresh 复评 95 / pass。三次回执均完整，已知用量 48,607 tokens，unknown
为 0；报告修订内容和 transport、阶段、SHA 绑定均通过结构回放。

但本例的 independent-initial/revision/final-review.json 与 primary 决定由同一
主执行主体直接写入，没有第二个受审计的独立审查主体或可验证签署。现有
validate_submission 只验证 append-only 链、字段、阶段、报告和回执绑定，不验证
审查主体身份，因此出现了“结构 PASS、双审资格不成立”的缺口。ADR0114 对独立草稿/
主审的语义是独立 human/source inspection，不能用 reviewer 字符串或文件名冒充。

## 裁决

- 这是审查身份/独立性合同失败，按批次 stop rule 停在 claim-scope:4 完成后。
- 不是 Provider、transport、来源 SHA、模型输出或预算失败；模型事实证据保留，但不授
  review_controls 资格，不计入严格 1.5.5。
- claim-scope:3-ready.json 已生成但在任何下一例 Provider 请求前停止；下一例真实调用为 0。
- 不改写或补签三阶段 stage、journal、transport、host、primary、independent、
  decision、task-observation、case-completed、plan 或 handoff 原件。完整文件哈希和公开
  审计保存在 data/evaluation/results/golden_boundary_examples_host_timed_independence_failure_audit_v1.json。

## 后续

先在离线代码和测试中建立可审计的独立审查主体/签署边界，并证明伪造同一主体、缺失主体、
交叉绑定和正常双主体的判别行为。旧批只读，不重新开放；新的真实执行必须使用新冻结身份、
重新核预算，并在新的付费授权明确后进行。不要把本例的模型通过结果、结构回放或本审计
 当作完整十五例资格或产品准入。

## 2026-09-29 离线裁决与修正

曾短暂尝试以 Ed25519 双密钥作为 v2 身份证明，随后撤回。原因是同一个执行者可以在同一
进程内生成两把密钥并自行签署两份意见；这只能证明密钥不同，不能证明审查主体独立，且会
新增不必要的运行依赖。该原型及其依赖没有保留，也没有用于任何回执或资格。

当前保留的最小合同是 `scripts/review_independence_contract.py`：新模式要求冻结 root/independent
主体标识、plan/case/stage/response/source/request 绑定，以及由协作宿主产生的完成事件；提交的
independent 正文必须逐值等于该事件正文，事件作者、派发关系、终态和原始事件哈希都必须匹配。
本地 JSON 自称的 `agent_id`、reviewer 字符串或运行目录里自制的 event 文件不能作为宿主事件。
宿主取证适配器尚未存在，因此 v2 目前 fail closed，不能启动新的付费批次；v1 旧封存仍只读
兼容，当前停止批次不补签、不重开。

当前代码已把 `HostReviewEventSource.fetch(event_id, binding)` 作为显式依赖贯通草稿、正式提交和
恢复校验。没有该依赖时不会读取运行目录里的 event 文件；宿主返回的 event 仍需逐值匹配作者、
派发关系、终态、完整绑定、原始事件哈希和完整 review 正文。离线替身只验证接口行为，不能替代
真实宿主实现或授予资格。

主审一侧也已接线：v2 正式 primary 记录由 writer 自动生成 root 主体绑定，覆盖当前 plan/case/
stage/response/report/request 和 primary 正文摘要；它只证明 root 写入的一致性，不替代 independent
宿主事件。v2 因此仍需两侧同时满足，且真实宿主适配器缺失时保持拒绝。

已加入确定性边界测试：合法宿主事件、缺少宿主取证、主体/计划/阶段/回执绑定篡改、正文篡改、
相同主体均能按预期通过或拒绝。该测试只证明合同和拒绝路径，不能证明真实独立审查已经发生。

## 回执更正

停止主进程后对 transport 清单复查发现，claim-scope:3 已在停止前发出一个
GLM-5.3 review 请求：reserved_calls=1、HTTP requests=1，stream 状态为
reading，events=1344，reasoning_chars=3254，content_chars=0；没有 response、
终态或 usage。该请求按 unknown/incomplete call 计入，不重试、不补造结果。
更正证据见
data/evaluation/results/golden_boundary_examples_host_timed_independence_failure_correction_v1.json。

## 同日后续：实际入口及原生宿主适配

此前“接口已贯通、只剩外部集成”不成立。新增完整正例首次在initial阶段复现
host_review_primary_binding_mismatch：writer用准备请求SHA，binding用实际transport请求SHA，
二者不同；不能只修revision/final。现取实际阶段回执。event_source也已从execute_prepared
传入adjudicate_file、validate_handoff、_stage、_case和inspect_runs。新执行的模式/身份/来源
检查在CI、目录创建、凭据读取和Provider工厂之前；缺依赖不再先付费再失败。

完整qualification会通过冻结的product API再次调用inspect_runs。直接修改该API触发
manifest指纹漂移，已撤回该app改动；现以ContextVar作用域传递该宿主依赖，保留完整回读，
finally恢复原上下文，无来源时v2仍拒绝。没有更新manifest、换产品版本或迁移历史资格。
新的prepare_fresh将身份合同与原生读取器源码一起冻结；旧prepare仍回读旧封存SHA。

### 原生取证候选与验证边界

从安装的Codex CLI生成本机schema，并实际验证stdio app-server的thread/read、
thread/turns/list可用。Windows的daemon生命周期命令不支持，不等于宿主API不可用。
新scripts/codex_review_event_source.py只允许initialize和上述两个读取方法，禁止turn/start、
thread/start、resume、fork；不会代用户重启桌面宿主或启动模型。

证据来自冻结root的真实child：thread.id、parentThreadId、source.subAgent.thread_spawn
一致；选定turn必须completed且itemsView=full；只有一条绑定任务userMessage及一条
final_answer，任务在前、回复在后，二者binding与本次阶段逐值相等。独立正文来自最终回复，
事件引用为child/turn/final-message；dispatch_id取原始任务item.id。raw_event_sha256由
宿主返回的身份投影及完整turn规范化计算，不采用调用者声称的摘要。线程updatedAt/status等
可变元数据不入该摘要。历史丢失、分页循环、错父子、未完成、无绑定旧任务、错阶段/请求、
缺完整正文或后续原文改变均拒绝；本地event不能替代该读回。

此方案尚未通过真实成功事件验收，不宣称宿主历史具有额外密码学签名或永久留存保证。
本机真实读取本轮失败child 01a0ecfa-2af8-78e3-ac2f-4296c5b673f8，
turn 01a0ecfa-2c95-7a22-bb26-ed4ec9b37541，被候选适配器拒绝为turn_not_completed_full。
工程独立复核两次尝试均遇429，未完成；不反复重试、不记成代码通过或产品人审完成。

调用方法：先通过review_task生成绑定任务，由独立子审查者真实完成；取其原生事件引用。
使用CodexReadOnlyClient上下文和CodexHostReviewEventSource读取事件，再将事件中的review
及independent_source_event传给write_independent_draft；同一来源依赖传入正式提交、批次
入口和资格回读。执行文件路径由宿主配置提供，不由候选数据或运行目录指定。没有一条真实
完成事件的导入/主审/回读证明之前，不开始新付费批次。

### 本轮检查记录

- 关联七文件：194 passed / 1 failed，1496.64秒，原JUnit保留于
  tmp/review-identity-wiring-tests.xml。旧失败用例缺实际transport字段且预期prepared SHA，
  修为缺字段拒绝和实际回执成功两分支，2 passed / 8.94秒。
- v2完整十五例的实际连续执行器→draft→正式提交→封存→qualification重入通过，
  **Provider与宿主均为离线替身，不是15/15真实模型资格**。
- 原生schema适配器16 passed / 0.36秒；其接入实际三阶段consumer的离线测试
  1 passed / 49.20秒，JUnit为tmp/native-review-wiring-tests.xml。
- 第一组36 passed是上述相关测试的重叠运行，不重复累加。治理检查通过。
- 本轮无新GLM请求；无旧批补签、重开、候选/Worker开关切换。全局路线与严格1/15不变。

后续先完成工程独立复核和一条真实成功事件整链，确认实际宿主完整派发/最终消息字段；
若字段缺失则按具体证据调整候选读取器。之后才准备新身份/同HEAD CI/累计预算/具体授权。
完整原15后仍有自然Agent与同run真实Worker/DB/API/Workbench，以及原路线中的四块联动、
本人Training、审美/头像、Memory、身份运维、两树整合与学习；本轮不宣称项目只剩一个问题。

补充：身份合同和原生读取器加入新准备的源码冻结清单后，准备/闭批预览相关11项通过（39.61秒）；治理、编译、diff检查通过。三份JUnit已复制到C:/Users/33502/Documents/Agent/outputs/riftcoach-review-identity-2026-09-29，保留包含旧失败的原始整组结果。临时schema目录清理命令被自动审批拒绝（仅返回blocked by policy），目录保留；不改产品状态。
