# 必要编辑诊断：真实结果与后续决定

## 结果

用户“确认”批准冻结 `71f544b522ad8e6fd60d390d45a1b0006f18f25b8ea9f06b428547aa10c1b9be`。
执行提交 `d2b080b155363eaba74fb7ad6ee907cb3df9c838` 的 CI `36811529513` 三项成功；
公共 pytest 为 5565 passed、163 skipped、129 subtests，测试步骤耗时 42分19秒。
这段等待不是 Provider 调用或模型超时。

真实诊断仅执行第一笔 Flash 必要编辑，18.562 活动秒，10901 输入＋541 输出＝11442 tokens，
unknown 为 0，未缓存估价 0.0102356 元（非账单）。正常 tool_calls 终态，没有402/429或断流。
唯一操作遗漏必填 `edits[0].source_ids`，在组装全文前被严格校验拒绝，批次正常结束。
没有 host 阶段、GLM fresh 或正确保持对照；没有成功修订、原15新增资格或产品准入。

13份原件封存于 `data/evaluation/results/golden_coarse_edit_diagnostic_result_20261001.json`，
SHA256 `a344b5f00b0e8ed4277a2adba08beea4a257af055ee99cbacb20494ed9f53500`。
封存只导出公开内容；transport原响应中的私有字段不导出。旧批、请求和失败回包不修改、不补签。

## 首次偏离与根因边界

- 实际保存的请求及 transport request 的工具 schema一致：TextEdit.required含五个字段，
  source_ids非空、唯一，且仅允许22/23/24/25/31/32。Provider编码原样传递input_schema；
  这是代码路径与本地回执核验，不冒称独立抓取HTTP正文。
- 最早的transport公开工具参数已缺source_ids，与阶段response逐项一致。
  组装器拼接JSON并保留整个参数字典，没有找到Host删除字段的路径。
- Pydantic仅报告这一处missing。引用校验并未执行，不能说模型“引用了错误来源”。
- 主审和/root/recovery_patch_check独立核对before、after、reason与完整来源：原句唯一定位block4；
  全样本/中单伤害均值869.504/952.1375、视野45/33.75、早期死亡2.6/1.5正确；
  辅助局补刀、经济、伤害拉低，视野和早死拉高。没有发现此前的内部指令复制。
  这是失败后文字内容审查，不是缺失的正式阶段通过或全文fresh。

所以本次是工具结构遵循失败；未证明局部编辑可靠，也未重现上次全文指令污染。
一次遗漏不能区分嵌套schema表示、采样波动或一般工具遵循能力；不能直接宣布$ref为根因。
已有官方能力调查见2026-09-22-last-push-audit及ADR0103：未找到可采用的strict schema/
required tool能力，本地strict校验不等于服务端约束解码。本轮不猜测开启未支持参数。

## 已修补与方案选择

原诊断result只记ValidationError，丢掉定位信息；现增加稳定schema错误码和无input/context的
字段错误记录。用本次原始公开回包作为离线回归，验证1调用停止、用量保存、原回包不变、
无stage/host/fresh；诊断入口12项通过。这是可诊断性修补，不改变生成请求、校验或质量标准。

保留必要替换机制的诊断价值，暂不注册产品、不回退整稿重写、不重开十五例、不追加提示原样重试。
已离线准备一个有区分力的替代表示：将唯一无兄弟字段/递归的本地$ref精确展开为同一TextEdit。
必填、枚举、长度、额外字段约束完整保留；22个正反向检查一致，原失败在两种schema下都拒绝。
结果见 `data/evaluation/results/golden_coarse_edit_schema_comparison_20261001.json`。
这仅证明表示等价，不证明能提高模型成功率，未修改实际工具schema。

下一动作：据此准备一次仅改变工具schema表示的有界诊断，先绑定相同完整输入、当前预算和
实际Provider编码，再按新增调用授权执行；不把本批未用的两次调用当作失败后自动重试许可。
观察仍缺字段则否定“展开schema已足以修复”的判断，重新评估编辑协议的必要负担；成功也
只允许接着验证当前全文fresh和正确保持，不能从一个输出推导稳定性或原15资格。
当前没有准备完成并获准启动的新批，没有活动Provider。

完整原15、自然Coach生成/工具/纠错、同run Worker/DB/API/Workbench及8E仍未完成。
四块联动、本人Training、审美/必要重做/英雄头像、Memory、身份运维、两树整合及学习要求
沿活动计划保留；当前工作没有替代这些交付。

## 公共CI封存字节修复

公共CI36820293915因旧封存被Git规范化为LF而拒绝coarse_inline_prior_seal，等待进程正常退出、未启动Provider。已对该单文件指定-text并重新入库原CRLF，index与本地原始SHA均为a344b5f0…53500；原13件未改，冻结不变。新11项回归通过；待修复提交CI全绿后沿原授权启动。
首次普通git add沿用了缓存，index核验仍失败；使用该文件的git add --renormalize后逐字节相等。只恢复原始保存字节，不换期望哈希或放松校验。
