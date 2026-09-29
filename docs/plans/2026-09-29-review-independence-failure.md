# 2026-09-29 真实批次独立审查身份失败审计

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

已加入确定性边界测试：合法宿主事件、缺少宿主取证、主体/计划/阶段/回执绑定篡改、正文篡改、
相同主体均能按预期通过或拒绝。该测试只证明合同和拒绝路径，不能证明真实独立审查已经发生。

## 回执更正

停止主进程后对 transport 清单复查发现，claim-scope:3 已在停止前发出一个
GLM-5.3 review 请求：reserved_calls=1、HTTP requests=1，stream 状态为
reading，events=1344，reasoning_chars=3254，content_chars=0；没有 response、
终态或 usage。该请求按 unknown/incomplete call 计入，不重试、不补造结果。
更正证据见
data/evaluation/results/golden_boundary_examples_host_timed_independence_failure_correction_v1.json。
