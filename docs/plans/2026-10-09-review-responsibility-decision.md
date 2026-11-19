# 初评修法责任取舍与离线反例

2026-10-09；基线e0d3437432324f2a10a85a1cc85057a513e8f9b5。
目标是判断转移修法责任能否作用于当前两处分歧，而不是为关闭批准备另一个发送器。
本包Provider0、新初评0、业务重评0、资格0；自动接续保持PAUSED。

## 当前事实与方案取舍

| 当前案例 | 原始响应与事实 | 责任位置 |
|---|---|---|
| attribution:1 | original15封存中transport/attribution-1/review/response-001.json；block14伤害主要归因错误检出及修法正确。block4“混合位置均值受辅助局强烈拉低”泛指被升级为全部指标，列fact_error；主审拒绝、旧独立接受的真实分歧保留 | 原文含义及错误分类；不是9/27旧经济扩题 |
| scope:3 | remaining11封存中scope-3/response.json；block4明确中单，胜2.5/败0.5，“早死几乎相同”是真错，检错和数字正确。修法“本样本中更少的早期死亡并未带来中单胜利”存在观测/因果两种读法 | 修法含义及Host语义一致性；不是旧省略范围误读 |

两者不足以证明同一个“修法扩题”根因。删除suggested_correction至多减少初评自行生成
争议替换句的机会，也可能将争议移交编辑；它不会改变attribution的原文含义误判。
现有全文policy已要求解释实际命题与具体来源冲突，泛指不补全称、措辞不升级事实门、
修法不扩题。没有新证据支持叠同义规则、增加命题字段或重做来源语法。

因此尚无充分共同修法，本轮不建新runner/候选发送器或付费冻结。此前独立方案首答
混入历史失败，经精确封存/path/SHA纠正后已撤回；原错误final保留，不能作为当前定位。
历史反证仍用于淘汰方案，不能替换当前案例或改旧裁决。

## 最小反例及其证明边界

scripts/probe_review_responsibility.py只读三份固定SHA公共封存，不读忽略的历史run。
产物为data/evaluation/results/golden_review_responsibility_probe_20261009.json。

- 旧同段同解释、不同修法范围的两份意见，deepcopy删除修法后完整对象相等，封存witness
  预期处置不同。直接删字段损失指控身份；散列不能恢复缺失的含义。
- 人工在现有explanation内写明“所选全部5局”和“中单”两个指控对象，可保留区别，
  不增加字段。但假想schema也接受带相反witness标签的指控，结构不证明语义。
- 当前两例删修法后原explanation/问题段保持。现行NativeIssuesReview的Pydantic入口
  严格拒绝缺suggested_correction：attribution两处、scope一处。不能填假建议或把投影追认为旧初评。
- 记录Pydantic/jsonschema版本、两schema及七份定义源码指纹；普通Python重建产物相等，
  -O在读证据前拒绝。指纹不是全部传递依赖或完整环境锁。

真假标签来自封存分析者witness，本脚本不重新计算原来源真值或产生Host决定。
人工例只证明指控可区分，未证明完整有源diagnosis；入口拒绝不是完整语义/编辑/fresh验证。
脚本不组装成稿、不生成request/receipt/journal、不改原件，不证明五调用接线或预算可达。
现行原来源、完整初评意见、fresh、全文双审、五调用及ADR0116否决机制保持。

## 实际独立开发复核

Sol主体01a11fea-dc3d-72d0-a07e-90fde8f04f92，parent为主审
01a0c6c5-01d1-78d0-82fb-e567e0ab7150；真实只读Codex API核completed/error=null/唯一final。
以下均为开发取舍/代码复核，不是StageAssessment或旧业务补签。
create-only原生快照位于operator outputs/riftcoach-semantic-responsibility-20261009：

| 证据 | 原生事件 | 快照SHA256 |
|---|---|---|
| 纠正方案 | 01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a12061-1087-7d01-9112-0768403cc61c/msg_03d7b027593b6423016ac8cd80a4d4819583a28b8fd993fe64 | a28957fb36d094a1b746ebd9f2f792e624a558e3b9d6c7f82304f7e0afab0150 |
| 初版代码复核 | 01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a12067-4208-7491-ac5b-533e2e91928b/msg_03d7b027593b6423016ac8ced89eb08195b7e2679fdfab4487 | 5c4f3435b97f1ba7433b286efc4e2429b46b00a5d03a1b1b93e029b92f316c9d |
| 边界修订复核 | 01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a1206b-0f35-7df3-8d04-0a34cfce1ca7/msg_03d7b027593b6423016ac8cfc38564819582900b8fcf15aeaf | ae9cb860e40f4e714885a40c5ad12c8f721ee5e64ae854437a2f1d8ccda12921 |

末次实读脚本SHA f06e3442138b765fe81d4212b7f5bf6d19727783ab5698e6eba28432d6d5014f，
probe重建相等、优化模式拒绝及新增指纹核验通过，无阻断缺陷；未读主审意见、未改文件。
初版的witness真值/入口/依赖边界建议已据实修订，原生正文未代写或裁剪。
最终主审重建产物相等，三输入封存SHA保持；编译、治理与差异检查通过。

## 后续工作与保留依赖

本包结束条件已达到：当前责任位置、可淘汰的直接删字段方案及最小信息反例明确。
下一免费工作包追踪自然Coach现有compiler→Runtime→共享预算review→publication/Evidence
→receipt→Worker终态路径，核哪些接口已有离线覆盖、哪些仍待当前组合/真实资格；明确
本地缺陷直接修，避免继续制造未选语义变体。不能用旧opt-in应用替身通过宣称1.5.6已消费。

旧scope:4缺认证、claim-scope:6缺block及后四例未发送各自保留；关闭批不重开、不借余量。
当前两处分歧不下传，旧3/15与历史2/15不拼，新资格0；共同语义修复、正式同版本15、
自然消费和8E未完成。自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、
前端审美/头像、Memory、身份运维、两树整合和八维学习保留，不靠离线反例完成阶段。
