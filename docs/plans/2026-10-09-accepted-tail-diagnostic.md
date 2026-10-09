# 六个未测编辑/fresh尾链的集中诊断

目标是在下一次完整15之前，一次暴露六种未测修订的实际问题。输入来自已关闭并严格
封存的十一初评扫描；只采用原双审接受、needs_revision的六例，不重开旧批。
此方案检验现有编辑器和fresh路径的覆盖缺口，不能解决或重新评级两处分歧。

## 选择与数据流

| 案例 | 要检验的未测能力 | 新阶段 |
|---|---|---|
| scope:4 | 明确中单范围却用了全样本死亡数值 | Flash必要编辑→GLM fresh |
| claim-scope:6 | 未解决的样本范围 | 同上 |
| observed:2 | 未来外推 | 同上 |
| observed:3 | 阅读者与观摩对象身份 | 同上 |
| observed:4 | 官方来源日期 | 同上 |
| observed:5 | 标题能力断言和正文一致性 | 同上 |

扫描封存SHA为`8adfa5cea9b56c063ffb0340b726c55d4c3effbfe86c54738d492f48b00c6baa`。
`controls()`按旧计划、真实transport receipt、原件SHA、完整source/journal/双审
submission及真实native事件绑定重建六个输入。旧初评的当前完整请求/政策、报告和
来源与当前DocumentReviewWorkflow精确相容；编辑器读取完整已接受review，不删问题。
历史首审Exchange只是显式历史输入，不创建新transport、调用或用量，也不签新初评。
`attribution:1`和`scope:3`存在分歧，被排除在历史输入之外，不能直接交编辑。

每案新建独立DocumentRoleProviderFactory/router，走原DocumentReviewWorkflow的
evaluate→revise→evaluate状态机；历史首审注入只占工作流逻辑阶段，不计新IO。
六案使用同一个共享budget对象，累计calls、known/unknown tokens和活动时长。
每案的真实transport ordinal是编辑1、fresh2；编辑后必须通过真实全文双审才发fresh。
fresh只读实际新稿、完整来源，不注入旧初评、Host标签或“应该通过”的答案。

## 质量与故障边界

主审和独立审查均读完整来源、原稿、全部改动/保留内容、edit reason、引用和fresh
意见；task通过实际request SHA附完整原policy，编辑阶段同时附历史初评及编辑规则。
接受报告须四项ReportAssessment全真；fresh须pass且>=85，无实质误报或漏检。
独立意见只通过真实native-final-attestation-v1导入，主审不能代写。

有效语义拒绝停该案依赖尾链并继续下一独立案；错误来源/身份/native/协议/transport/
预算/审查不可用停全批。没有重试、重评或关闭批重启。每案终态持久化，迟到提交受
case-result、host-reviews与全批result/OS关闭锁约束。首阶段付费前预检原生主/独立
主体可用；每案按实际待审阶段接续，人工离线期间由原Host时钟计时。

十二次预算：Flash6、GLM-5.3/high6；最多1,161,216 tokens、3,600活动秒、86,400
Host秒，每请求最多32,768输出tokens和300秒。保守未缓存估价9.4347264元，非硬计费
封顶；失败未知用量按保守reservation保留。SDK零重试由既有role factory/contract强制。

本批最初准备时没有付费授权；用户随后明确允许上述具体边界。执行需要最终同提交公共CI全绿，
以及执行前真实主体预检；离线构建和检查已在用户“继续”授权内。
本轮只读原生预检已确认主/独立真实谱系及当前native-final路由可用；不保证未来
可用性，执行前仍重新检查，任一阶段无法取得真实独立final即停。
冻结准备文件为`data/evaluation/results/golden_document_accepted_tails_preparation_20261009.json`，
方案SHA为`33ce91c802bea1eb0c247fea85d9fc988ca616cdf32869730f913a176caab8ce`。

## 实际入口与验证

- `scripts/run_document_accepted_tails.py`：准备、冻结、单次执行及共享预算/失败分流。
- `scripts/document_accepted_tail_handoff.py`：重建pending材料、交付完整policy、导入真实双审。
- `scripts/seal_document_accepted_tails.py`：关闭后只读回放、known/unknown账目、白名单封存。
- `tests/test_document_accepted_tails.py`：替身控制流与真实receipted factory的离线往返。

封存严格重建已审阶段和native意见；硬失败pending source、historical journal、实际
edit/fresh请求仍需校验。pre-transport身份失败的单个真实local issued文件可表示未知
reservation，明确不造call receipt；未认证Host正文只留摘要，不进公开JSON白名单。
原件包括失败记录全部留SHA，公开内容拒绝秘密字段和私有推理。

工程测试不证明真实编辑或模型质量。九个Host控制收到完整policy后仍C06分歧，继续
作为“完整规则交付并非充分语义修法”的反证，不宣称本方案已解决它。
新增20项离线测试全部通过，包括单例语义拒绝继续、硬故障停批、真实回执/native
替身导入、原件篡改、pre-transport无回执未知用量及summary篡改拒绝；既有role factory
身份/SDK合同相关6项通过。独立代码复核指出历史注入计数未核，已补；另补hard-failed
pending的source、历史journal、预期request及public response核对。相关封存回归通过。
历史注入后若workflow在落journal前出现内部异常，原件和result保留，但严格封存会拒绝
宣称已完整回放；不能补造journal或把失败批当成功。当前已验证历史输入不触发该路径。

## 结果如何改变下一步

六尾链有语义失败时，收齐其他独立例后按实际失败集中修复，避免逐例重买正式15；
硬故障则先修确切工程缺陷，不自动开新付费批。全通过也只缩小尾链覆盖缺口：
两处原文/修法含义分歧仍需前瞻证据，正确与明确真错控制也必须保持。
原文档3/15、另一身份历史2/15独立保留，本方案新增资格0；达到进入条件后才准备
同版本完整15。自然Coach/本人Training/四块联动/前端与Memory等产品依赖仍在原计划。

## 授权后的CI资料修复

dd870b63的新增测试直接调用live controls，读取忽略的本机历史run；干净检出没有这些
文件，缺目录实证为FileNotFoundError。公共CI37875366571已在Provider0时主动取消。
只改测试，从已提交公开seal的完整来源/实际业务输入/公开初评构建synthetic IO夹具；
按当前请求重建并核原issued SHA，保留journal中的公开原始arguments顺序，不造transport
receipt或native事件。测试禁止读取本机data/runs，live controls仍拒绝缺失的原件。
该CI-only修复不改变已授权源码身份、业务输入、请求、政策、原件、预算或双审标准；
冻结33ce91c8…caab8ce精确重建不变。首次执行依赖修复提交自己的CI全绿和即时真实预检，
不是复用旧CI通过结果，也没有开启或重试付费批。
禁止本机data/runs读取条件下，本模块21项全部通过（251.90秒），治理检查通过。
这验证公开检出资料足够用于离线测试，不表示真实模型语义已改善。
