---
state_schema: 1
main_stage: 8
substage_group: "stage-8-multi-agent-reliable-runtime-productization"
current_checkpoint: "8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption"
status: in_progress
pause_reason: ""
---

# RiftCoach 当前执行状态

## 当前行动

2026-09-22：business v1实测两例；核心混合例完整成功，全称例修订成功但格式恢复新增范围误报，整链失败，已停止付费批。v2已离线修复此类尾文的自动恢复分支：保留协议失败，避免额外业务重判；不是语义修好。入口关闭，后两例未运行。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。ADR0103工具提交实验已完成前两例：第一例一次工具调用96/pass；第二例合法工具调用正确发现真错但新增范围误报，按规则停止批次，第三例未执行。协议问题已改善，语义主阻断仍在；不接产品、不恢复旧批，不对工具通道原样重试。下一动作改做误报机制诊断。
- 工具实验提交 `3fa81a3` 的精确CI `35687655648` 三项均通过；其两例公共receipt冻结在 `data/evaluation/results/golden_native_tool_result_3fa81a3.json`。当前HEAD为 `51b6bf6`（仅证据/状态记录），工作树干净。

活动工作卡：`.planning/2026-08-06-riftcoach-development/task_plan.md`。
执行方法：`docs/plans/2026-09-22-agent-delivery-method.md`。
实际后端：`D:\riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`，
真实验证基线 `d41c0bda19312a20e48d674683defe4badec1cf3`；主库前端工作保留，未合并/重置。

## 已验证事实与阻断

- 核心混合例：初评只报真实补刀错误，实际修正五局合并胜8.81/败6.45，保留正确原block4；终评96/pass，独立全文审查接受。本次3调用完整走通，不代表稳定率或完整资格。
- 全称例：初评和改稿正确；第一次终评96/pass后附Markdown，严格解析拒绝；唯一完整重评合法返回93/needs_revision，把正确中单句的五局观察窗口补成全部五局分母。整链拒绝。第3/4请求共同报告/来源一致，恢复新增判断，不是旧issue映射丢失。
- 实际7次调用、103955tokens、未知0，累计至少284次（沿用历史台账）。全部stop；最长首评248.719秒，未触发300秒/32768限额。结果见golden_native_business_result_d41c0bd.json；不改失败回执、不执行剩余两例。
- JSON模式已在同一SDK路径离线重建确认；官方文档仅列text/json_object及auto工具选择。不能靠补开JSON、猜strict schema参数或丢弃自然语言尾文修复。格式/语义职责重新划分尚无已验证通用解法。
- d41c0bd的公共三项通过；此前76项聚焦回归通过。07cd6c7全测发现旧治理负例依赖已删除章节，已修复并验证12项治理测试；该遗漏与模型语义失败分开记。
- v2的93项聚焦回归通过：真实混合例离线3调用/pass保持；全称例在第3调用明确协议拒绝，不再发第4次错误重评。原7次费用/失败保留。这项修复改善终止行为，不赋予产品资格；纯JSON坏字段仍保留既有显式映射恢复。
- 新终止码已接入Harness安全诊断，仍拒绝发布模型稿；另17项Harness测试及2个子用例通过，独立审查通过。本轮相关检查共110项及2个子用例；当前v2没有真实Provider调用。

- 最近 6c22e93 实际编辑修正五局混合补刀错误，并保留正确段落；两状态终评仍把泛指判成全称，
  且缺字段、混入原稿问题的恢复映射。两请求完整 stop，2次/36011tokens/197.732秒、未知0。
  本例不是断流或输出额度耗尽；单例编辑成功不代表首评或整链合格。
- 483f91d 定位臂实际 apply/withdraw，完整意见臂 apply/apply；前者未获得通用采用资格因为信息保真局限，
  不能误称两臂都误报。因果机制和通用修法仍未确定。
- business、two-state、旧native/editor/product live入口均关闭。新business仅干预分阶段system策略，
  复用旧完整来源、Schema、验证器及工作流；GLM/high、预算、采用标准和产品默认未改。
- 最近审计重建回执和80项相关回归已通过；5578685的公共三项通过记录是此前核验。
  上轮方法核查55项离线测试及产品预览通过，首输入上界33240，真实生成/语义准入均为false。
  上述不冒充本轮重跑、真实 DB/UI 或模型质量证明。
- 现有 native application、RAG、Memory 注入和同源发布可复用；native Worker 离线测试使用 fake repository。
  默认 Worker 并非显式 native 组合。产品实测入口关闭，其内部硬编码旧五例证据仍是发布前待修项，
  不是当前发生的错误发布，也不应抢占核心误报诊断。

证据及撤回结论：`docs/plans/2026-09-22-last-push-audit.md`。
源回执入口：golden_native_editor_pair_result_483f91d.json、golden_blind_edit_result_6c22e93.json、
golden_blind_edit_failure_audit_6c22e93.json（均在 data/evaluation/results/）。

## 既有要求与后续

采用完整上下文语义标准；事实错误、无依据外推和内部矛盾阻断，措辞建议不能自行升级为门槛。
当前 ShowMaker 为公开 observed 观摩，不是阅读者本人的训练基线。Luna 只属于 Codex 开发协作。
模型/预算执行时以当前实际合同为准，开发协作不改变产品策略。

同版本完整资格、真实产品生成/来源发布、Worker/DB/API/Workbench 消费、独立评估及学习仍未全部完成。
Coach/Review/Training/Evidence、个性化训练、整体前端审美/必要重做/英雄头像、知识与 Memory、
身份运维和两树整合持续追踪。总体路线及62主题入口见
`docs/plans/2026-09-16-astra-restart-plan.md` 的“全局后续”，不以本次方法调整取消或更改阶段。

## 历史与恢复

本文件仅存当前事实和行动。整理前5907行全文已按原字节归档至
`docs/archive/2026-09-22-execution-method/execution-state-before.md`，SHA256见同目录manifest.json。
旧“唯一下一步”只按历史日期解读，不能恢复为当前任务；新结果更新本页并在progress留历史。
治理检查只验证状态结构一致，不保证语义正确或工作方法一定有效。
