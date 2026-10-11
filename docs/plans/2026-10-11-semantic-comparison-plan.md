# 语义教学组织对照：执行前方案

## 目标

区分“正确全文被扩义误报、真错修法遗漏、摘要与正文修法分歧”是否受教学组织影响，
为后续同版本完整 15 例选择一个有证据的最小机制。该对照不改变验收标准、不重开历史批次，
也不授予产品资格。

## 固定范围

使用 5 个已公开封存的完整请求，各构造 3 个教学后缀，共 15 个独立初始审查请求：

- `expanded_examples`：原扩展示例，作为基线；
- `short_examples`：既有短例；
- `decision_sequence`：实际命题 → 全文范围 → 来源冲突/行动歧义 → 直接修法的顺序说明。

固定样本覆盖 `claim-scope:4`、`scope:3`、`scope:4`、`observed:3`、`observed:5`。
完整报告、来源、业务规则、工具 schema、输出字段、模型、解码参数和请求时限保持逐字一致，
只替换教学后缀。案例标签与预期结果只存在于 Host 侧材料，不进入 Provider 请求。

## 执行与取证边界

新请求使用独立的 `document-semantic-comparison-request-v1` 身份和显式 transport，
默认产品入口拒绝该身份。每个请求只做一次 initial 审查；不自动编辑、不做 fresh、不重试。
每个阶段必须保存实际 issued bytes、transport receipt、完整 response 和请求 SHA，随后由当前
真实主审与独立原生主体全文审查。恢复同一检查点只发送 MESSAGE；身份、来源、native、checkpoint、
协议、transport、预算或可用性故障停止剩余全部请求。语义拒绝只记录该对照，不重试，并继续其他
独立对照请求。

计划边界：15 次 GLM 审查、1,451,520 tokens、9,000 活动秒、86,400 Host 秒，未缓存保守估价
21.44256 元；估价不是硬计费封顶。用户随后对该具体成本方案明确“继续”，本轮成本授权已取得，
无需再次确认。静态准备包的 `execution_authorized=false` / `execution_ready=false` 只表示准备本身
不能发送；首次执行必须另附 create-only 授权记录、同 HEAD 全绿 CI、即时真实主体预检。
目前没有 Provider 调用，`new_qualification=0`。旧准备包原样保留，不把准备当成执行证据。

## 执行接缝与恢复

`scripts.document_semantic_comparison` 提供唯一 `run` 入口，以及 `material` / `submit` / `abort` /
`replay` / `seal`。单次传输复用已有进程桥和 SDK；每 cell 使用独立实例并保留实际 issued bytes、
reservation、完整 response、terminal、body-free progress 与 transport receipt，不套用产品45调用流程。
全局15次、1,451,520 tokens、9,000活动秒为唯一总边界；每请求600秒/96768tokens。
已观察HTTP发送、尝试、known/unknown用量和receiptless分开记录，缺回执不冒认为已认证。

Host等待从活动时钟中扣除，wait/finish逐cell与六字段binding绑定。停止信号和cell完成共用短锁，
导入后再次检查停止状态才能发下一个独立请求。同任务恢复只MESSAGE；前任务真实final并导入后
才发新NEW_TASK。作者必须读取精确checkpoint并check-answer；主审只写自己的notes，submit实读
原生final事件，不代写独立意见。ReportAssessment四真门与原source/引用/修法门保持。

关闭后只读严格重建请求、传输、协议、双审、原生事件、clock和failure库存，按精确相对路径及
字段schema公开白名单；private reasoning与rejected fragments不公开，原件仍以SHA保留。
成功流不得带worker failure；不完整结果必须有唯一最早失败，禁止把发送后失败改记为付费前停止。

## 反证与决策

若某变体仍把正确泛指补成全称，或借正文限定放过标题明确真错，则它不足以作为共同修复。
若它只改善分数/字数而没有同时保留正例、真错和直接影响覆盖，也不采用。只有在隔离身份、
完整请求、真实回执和双审接缝均可核验后，按用户已确认的本轮成本授权首次执行真实对照。
失败、分歧和未执行项均保留，不能与旧批成功拼接为完整 15 资格。

## 运行前验证（真实调用0）

本机新准备/执行接缝34项、相关native/checkpoint/worker/transport108项、额外入口门禁3项均通过；
后续变更仅加强preflight字段绑定和入口反例精确code，完整15单审/严格封存与慢门禁等5项再核通过。
治理、编译和diff检查通过。最终独立工程唯一原生final实际读取、5个生产script及新测试SHA逐项
一致，blocking_findings=[]。工程原件：outputs/riftcoach-semantic-comparison-20261011/engineering-native-final.json
（本机operator，非业务回执）；旧工程final和旧准备包保持独立。下一步提交同HEAD公共CI、
新prepared子目录精确31文件、外置授权/预检记录后首次唯一runner。暂不宣称实际语义结果。
