# 编辑协议免费审计与方案选择

2026-10-09；开发审计基线fbc249fc6263a8210c6e33c19a071ce31205bfe5。
目标是区分已关闭五尾链的缺字段、请求构造和可用约束能力，选择有证据支持的下一条路径。
本轮Provider0，不重开旧批、不借余量；没有业务重评、成稿组装或资格授予。

## 结论与去留

未发现本地请求编码、IPC或返回组装主动删除block的缺陷。实际请求规则和工具schema
都要求block/before/after/reason；实际返回缺block，严格校验正确拒绝。
本地strict是接收校验，不能保证远端生成必填字段。本例已经调用正确工具，强制工具调用
也不能解释遗漏。当前保留四字段编辑合同与严格拒绝，不补旧输出，不再付费测试近义提醒
或schema展开；没有依据直接开启远端strict或把JSON对象模式当充分修法。

三字段before/after/reason加全文唯一锚点只作为未采用的候选。历史建议的before在各自
source blocks中均唯一，说明这些具体文本可定位；这不证明一般表达力。相同文本出现在
两块、同块重叠锚点、无匹配和空锚点均形成明确反例。省略block会失去对重复文本的定位能力，
不能因旧例刚好唯一就实现通用合同，更不能给旧缺字段返回补签。该候选也不解决初评的含义误报。

## 可复现公共证据

scripts/audit_editor_protocol.py固定9份已提交公共封存的SHA与11个实际编辑请求路径，
只选一次实际调用，排除prepared/stage/transport重复副本，不读取本机忽略的data/runs。
按当时发送的完整schema执行Draft202012Validator，不拿后继schema追认旧输出。
通过ZhipuProvider._open_stream_for_adapter的本地记录stub重建SDK参数，逐项核完整
function.parameters保持不变；不创建真实客户端、加载凭证或网络请求。

| 实际合同 | 调用数 | 格式合规 | 已观察格式偏离 |
|---|---:|---:|---|
| 五字段submit_source_edits | 2 | 0 | 两次缺source_ids，含inline版本 |
| 四字段submit_review_edits | 9 | 8 | 本次缺block |

库存是选定的真实开发调用，不是随机样本，不估稳定失败率。格式合规不等于语义正确或
有效Host认证；8次合规包含一次空edits，不代表8次成功修复。完整路径/schema/参数摘要及锚点计数见
data/evaluation/results/golden_editor_protocol_audit_20261009.json。
审计不会改任何原参数、组装报告、生成receipt/journal或授予资格。

7项离线测试覆盖公共输入/禁网络、真实缺block与Pydantic错误一致、nested required与IPC
保留、REQUIRED能力拒绝、混合文字通道拒绝、原封存SHA漂移拒绝和锚点歧义反例。
它们检验工程证据链，不替代真实模型质量门。

## 能力证据与边界

2026-10-09从智谱官方llms.txt定位并读取以下公共文档，原文HTTP200已保存于operator
C:/Users/33502/Documents/Agent/outputs/riftcoach-editor-protocol-audit-20261009。
摘要只说明当次文档内容；未声明供应商未来能力或未文档化能力不存在。

| 文档 | 实际证据 | 原文SHA256 |
|---|---|---|
| [Function Calling](https://docs.bigmodel.cn/cn/guide/capabilities/function-calling.md) | 第16行：`tool_choice`“默认且仅支持auto” | 7273e3419ebac5451a8d6deedd0abfbdf454650e30ff8c2476f16eac5b4b52f3 |
| [结构化输出](https://docs.bigmodel.cn/cn/guide/capabilities/struct-output.md) | 第15行：`response_format={"type":"json_object"}`；第152行起为客户端Schema验证示例 | fb632636a5e8bcc14530131625b8a88f891abf4f7ff5c8a2e90f4b4f3a54b5f8 |
| [GLM-5.3-Flash](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash.md) | 核模型文档，未取得可直接采用的远端strict/json_schema合同 | 3deb4f13dd5d6a22970ac7486f7afb7a9bf22e382920a5189e3bdfea836767ad |

当前实现REQUIRED在SDK发送前明确抛required_tool_choice；json_object不发送schema约束，
且与AUTO工具组合被本地拒绝。不能通过猜开参数绕过这些边界。
本地SDK参数重建不是历史HTTP body或原始SSE取证；封存未含两者，未观测线上行为仍未证。

## 独立工程审查

现有Sol主体独立检查完整请求→角色/回执→IPC→SDK→stream翻译/组装→公开导出，
没有发现主动删除block的代码；安装SDK的maybe_transform及合成含block/实际缺block
两类参数的stream/IPC往返保持一致。合成检查不追认关闭批。
真实原生final引用：
01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a12031-2e3c-7402-b6f7-99db3fc6b476/msg_02fea8690fadd9d9016ac8c175ae748195b03e4ff99392c1f5。
只读事件快照independent-transport-review.native.json的SHA为
46865b0a6a84843cab71791bd55f0affaceab8a302f84261d080fd18b4ce2dab。
新增审计脚本/测试按精确SHA独立复核无缺陷，7项测试3.15秒通过、产物重建完全相等；
原生final实读引用：
01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a1203b-0a43-7422-be86-ee042c626f7a/msg_02fea8690fadd9d9016ac8c39c0ed481958075c90739404fc9。
independent-audit-code-review.native.json快照SHA为
17f51f47960dedafeb1be950a12df6eaa9e2bc2b8e71ef0064f85a509cc01a06。
脚本只针对固定历史库存；扩展清单需重新核调用谱系，不能当任意坏响应通用分类器。
锚点计数按源blocks而非全文拼接；schema合规不核block与实际文本一致、编辑重叠或成稿。
上述均不是StageAssessment。
最终离线重建与公开产物一致，9份输入封存SHA不变；编译、治理与差异检查通过。
只新增审计脚本/测试/结果并更新状态，没有改app或已冻结runner/helper/模型政策。

## 后续工作卡

本包决定停止对最后一个缺字段做无区分性重试，回到完整初评→必要编辑→fresh的业务任务。
下一免费工作包对照现有表示、attribution:1/scope:3真实分歧与旧混合/正确/真错反证，
明确报告实际断言、来源最窄支持和建议修法的范围，再比较能作用于共同语义问题的机制。
结束条件是可审查的方案取舍与能区分解释的最小验证范围，不是多加规则或默认再买剩余例。
清楚的本地缺陷直接修；新机制需说明生产者/消费者、正反例和真实实测边界后才进入新冻结准备。

旧scope:4缺认证、claim-scope:6缺字段及后四例未执行独立保留，两处分歧不下传。
历史严格2/15与旧文档3/15不拼，本轮新增资格0；共同语义修复、正式同版本15、自然消费和8E
仍未完成。真实全文双审/fresh>=85且无实质误报漏检保持；泛指不补全称、措辞不升级事实门、
历史初评不重签/重买。ADR0116否决机制不复活。自动任务保持PAUSED。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/头像、Memory、
身份运维、两树整合与八维学习继续按活动计划依赖推进。
