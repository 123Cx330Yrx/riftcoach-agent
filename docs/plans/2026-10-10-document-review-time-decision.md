# 完整15主线：审查时间分配的离线裁决

## 目标与决定

解除当前主线的交付时间阻断，同时保留GLM-5.3/high、Flash/high、完整来源、
真实全文双审和fresh>=85质量门。本包只准备机制和证据，不发送Provider或修改旧批。
本次没有查明供应商推理为何持续300秒；已查清本地截止和资源分配的作用路径。

选择后续隔离候选方向：GLM审查单次最多600秒、Flash仍300秒，产品整任务仍900秒、
最多5调用/401920tokens/32768单次输出；实际请求一律取角色上限与任务剩余的较小值。
600是有界试验参数，不是从一次超时推算出的完成时间或已采用标准。
不把整任务改成5×600、不将Host等待重置为900、不降低high或裁剪原件。
旧1.5.6合同、冻结transport、实际回包/原件与默认入口本包均未修改。
新时间身份的实际发送/原生交接/严格回放尚未实现，execution_ready=false。

为什么选择这个方向：本次前两步scope共75.517秒，单次300先于任务预算用完；
延长有界单次等待能测试“局部截止截断但总资源仍足够”这个具体机制。
更长任务或供应商更换不是当前证据支持的第一步；不宣称新参数能解决任意慢请求。

## 可复现的证据

`scripts/audit_document_review_timing.py`默认只读取两份公开文件：
已关闭10例seal SHA76e9a70b…575f30，以及本包公开metadata capsule。
capsule恰含6调用×reservation/progress/result共18份原生元数据的原始UTF-8字节文本，
逐份SHA与seal的original_file_sha256相符；不含私有reasoning正文、请求正文或凭据。
每项计时和未知用量均可追溯至封存原件，不从历史mtime或聊天推断。

首次导出必须显式提供已关闭run目录，逐项核原件SHA且create-only写入；默认审计和测试
不读取忽略的本机run、不导入.env、不创建模型客户端或业务run。
产物为data/evaluation/contracts/document_review_timing_decision_20261010.json，
绑定seal/capsule原字节及8份相关实现的源码SHA（仅源码按LF规范，跨Windows/Linux可复现），
含6调用计数/用量/计时与以下反例；原封存及元数据字节不作换行转换。
输出不包含来源/报告正文；真实超时的completion_time_known=false、predicted_finish_s=null，
保留未知用量，不用字符数推token，不将模拟消耗混入原账目。

## 三层时钟及产品差异

| 层 | 实际当前值与消费路径 | 对下一候选的约束 |
|---|---|---|
| 单请求 | native request、document identity、workflow、role transport固定<=300；父进程monotonic硬截止 | 新GLM600须独立身份、请求摘要与新观测界限，不能只改CLI |
| 产品整任务 | CoachBudgetedProvider从创建起共享900秒，发送前min(request,contract,remaining)，完成后再核整任务 | 900保留；生成/工具/初评/编辑/fresh共享，不按阶段重建预算器 |
| 开发整批 | focused10 CandidateLimits把execution_timeout_s替换为8400，Host另有86400，跨案共用账本 | 该批没有独立每案900墙且没有自然生成；不据其成功宣称产品900可达 |

旧10例是开发诊断且资格0，其整批时钟是显式执行边界；本包没有把这一差异改写成旧执行违规。
后续需要产品时钟证据时必须实际覆盖生成前缀、工具和失败路径；仅测initial/edit/fresh不够。
Token硬上限仍是已有401920，并不保证任意五次输入64000+输出32768都能发送；
已有逐请求预留继续拒绝不可达路径，本包不顺手放大token墙。

## 真实预算器的离线反例

探针直接调用现有CoachBudgetedProvider，使用完整公开scope请求、fake monotonic时钟和
显式SyntheticProvider。仅探针实例覆盖单次时间，既有transport仍拒绝600秒请求；
这不是新的发送器、回执、业务评估或模型质量证据。
前两步耗时使用本批52.985/22.532秒，fresh450秒是人为边界例，Usage是显式模拟值。

| 单次审查上限 | 任务先前耗时 | fresh可用时间 | 结果 |
|---|---:|---:|---|
| 300 | 0 | 300 | synthetic stream_deadline，任务用375.517秒，未知预留77868保留 |
| 600 | 0 | 600 | synthetic450秒完成，任务用525.517秒；不预测真实fresh完成 |
| 600 | 500 | 324.483 | synthetic stream_deadline，总时间900，预留不释放、停止，不重试 |
| 600 | 900 | 0 | 发送前timeout，Provider尝试0 |

现有transport实际拒绝仅改timeout=600（stream_request_budget）；现有CapacityBridgeObservation
实际拒绝elapsed_ms=450000。证明旧硬边界真实存在，不能因预算探针通过就开启新调用。
未来600以上继续返回也必须有界终止；没有结果/usage就继续按未知结账，不能当免费。

## 方案比较与实现边界

| 方案 | 裁决 |
|---|---|
| 原样重试scope fresh/切剩余8例新批 | 不选；旧批关闭，仍受同一300秒限制且无新机制 |
| 减输出cap或再叠“简洁思考”提示 | 不选；未证达到32768，可能改变交付/语义，本次不是语义反证 |
| 压缩来源/裁掉对照教学 | 不选；没有已证明可删的语义等价冗余，不能用字符减少冒充提速因果 |
| 600单次并扩大总任务/批预算 | 暂不选；先验证利用已有剩余时间，超总预算是独立问题 |
| GLM600/Flash300，任务900不变 | 选为下一隔离候选；仍有总预算耗尽反例，非保证成功 |

下一实现复用现有预算器和进程生命周期，避免另造Provider SDK/重试器：

1. 新显式时间身份绑定GLM600/Flash300、单次输出、total900及原有token/call上限。
   原300身份/default解析器继续原样；新版请求/收据不能假称旧身份。
2. prepared/issued/request SHA、role校验、workflow、process、observation上限与实际SDK
   request policy共同接入。不得通过探针中的timeout归一化把新请求认证成旧交付。
3. 开发批预算与单任务时间都在新冻结方案中明示；发送前同时裁剩余值，Host暂停只排除
   人工审查等待，不能排除Provider/本地计算时间。全局预算不因换案、换阶段或恢复重置。
4. 真实Worker已有独立续租线程围绕executor运行；lease为所有权，不是整任务墙钟。
   本包只核代码，未实测600秒lease、取消或丢所有权后的发布，因此相关回归仍需覆盖。
5. 新阶段摘要/checkpoint/native导入、unknown预留、硬关闭、严格只读回放和公开白名单
   都绑定新时间身份；不把旧成功/旧native认证迁移为新候选资格。

离线重点验收：300不变兼容；600单次仍被900/批剩余截短；启动/流/close纳入同一截止；
已超总时发送0；失败尝试只计1且未知不释放；假回包/身份混用/Host重置/换案重置拒绝；
真实生成前缀消费同账本。假时钟能证状态机，不能证明供应商耗时或语义。
新完整方案与同提交CI齐备后才提出明确成本范围，不复用本批28调用余额。

## 本包验证与依赖

9项公开夹具/断网检查通过：原始字节/元数据篡改、清单外元数据拒绝、未知保留、
真实预算器的总时钟截断/发送前拒绝、旧transport/observation拒绝及冻结产物重建。
含源码跨平台换行摘要回归，证据仍按原始字节核SHA。29项既有预算检查通过。
本包Provider0、DB0、资格0；未派业务审查或补签scope final。
前一ed445256公共CI38018028991已核全success，本包仍需自己的提交检查。

复现：`python -m scripts.audit_document_review_timing`核公开冻结证据；
`python -m pytest tests/test_document_review_timing_decision.py -q`运行离线反例。
旧2/15与3/15独立；正式同版本15、自然Coach/Training/四块联动、Worker/DB/API/UI/journal、
前端审美/头像、Memory、身份运维、两树整合及学习仍按原依赖推进，当前不切Training。
