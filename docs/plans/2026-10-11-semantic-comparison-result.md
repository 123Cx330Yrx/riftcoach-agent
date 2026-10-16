# 五份完整请求 × 三种教学组织：真实对照结果

## 决定与范围

本轮15次独立初评全部执行并完成真实全文双审：**10项语义接受、4项双方拒绝、1项Host分歧**。
三种教学在正确修后稿`scope:3`上都误报，因此均不足以作为共同修复，不切换默认产品入口。
运行中一条进度消息误写9/5/1；本结果以实际15个双审submission及严格replay的10/4/1为准。
这不是15份报告的生成→审查→必要编辑→fresh验收，不授予正式完整15或新资格。

用户已授权的本轮只比较5份完整历史请求的教学后缀，GLM-5.3/high、来源、正文、业务政策、
schema、temperature=1.0、top_p=.95和600秒保持，不编辑/fresh/重试/重开旧批。
样本是已见开发材料，不是独立holdout；单次分数或配对差异不证明稳定率或内部根因。

## 逐项结果

“接受/拒绝”评的是实际模型审查意见的正确性，不是源报告是否合格。

| 完整样本 | 原扩展教学 | 既有短例 | 决策顺序 |
|---|---|---|---|
| sample1 / claim-scope:4 | 80/needs_revision；主接受、独拒，分歧 | 82/needs_revision；双方拒绝 | 72/needs_revision；双方接受 |
| sample2 / scope:3正确修后稿 | 80/needs_revision；双方拒绝 | 90/needs_revision；双方拒绝 | 90/needs_revision；双方拒绝 |
| sample3 / scope:4 | 78/needs_revision；双方接受 | 78/needs_revision；双方接受 | 78/needs_revision；双方接受 |
| sample4 / observed:3正确身份修后稿 | 97/pass；双方接受、四项全真 | 93/pass；双方接受、四项全真 | 95/pass；双方接受、四项全真 |
| sample5 / observed:5标题能力真错 | 84/needs_revision；双方接受 | 84/needs_revision；双方接受 | 88/needs_revision；双方接受 |

- sample2三变体都把正确泛指补成早死或全部指标；来源/完整规则已送达，格式合法不撤销误报。
- sample1 expanded/short解释新增“只有补刀/经济/伤害下降”的排他断言，完整来源还有KDA等下降。
  expanded保留真实主审/独立分歧，不重审求一致、不向下一请求传Host标签。
- sample3 decision只有issue14/advisory4，但实际修法补齐正确全样本2.5/2.67、独立中单2.5/0.5
  及小样本限制，全文消歧可以补足摘要范围，不能机械追加摘要事实改动；不追改旧批分歧。
- sample5三变体都检出标题“所选数据已证明ShowMaker防抓能力优秀”。正文限制不能撤销明确
  标题真错；改标题为样本结果表述充分。decision解释中的`facts:scope/limits`对应规范
  `scope:limits`，内容准确且合法引用27/30支持，不把路径简写升级成实质错误。

## 真实执行与关闭证据

冻结HEAD `a9a68049aac6db9a53d8d1f3c30d0a32627e0907`，同HEAD全绿CI `38104135494`，
方案SHA `4f864b162f6da2a98e41ca6841241f1c10d4b315837d60af6615bab2e23b539c`。
唯一runner92020/wrapper89788，UTC02:42:51首次启动，
`2026-10-11T04:33:23.063968+00:00`正常exit0；运行期间tracked源码/HEAD未改、无第二runner。
主审原生`01a1248f-e18c-7282-92bf-7ceb2eb5dce4`，同一独立主体
`01a1274d-67fd-7ac3-b9f2-e2a3432dff60`。每项绑定精确checkpoint/原件SHA，作者check-answer、
唯一多行JSON原生final实读后submit，不代写/裁剪/补签。同任务恢复只MESSAGE。

实际attempted15/observed_http15，input198834/output71846/known270680 tokens；
unknown_usage0/http_send_unknown0/receiptless0，未执行0，硬执行偏离0。
活动1394.985秒、Host5230.078秒、wall6625.063秒，均在授权边界内。
按未缓存输入8元/百万、输出28元/百万估价**3.602360元**，非账单或硬计费封顶。
最早语义偏离为sample1 expanded的Host分歧；`first_deviation=null`只表示无硬执行偏离。

指定Codex **0.153.4**严格只读replay核15个真实native事件；306原件SHA前后相等，
create-only公开290白名单JSON。原件、旧receipt和journal不改，private reasoning不公开。

- [公共seal](../../data/evaluation/results/document_semantic_comparison_result_20261011.json)，
  SHA `370efc13800d8c16ac1265af7686e8cad674903e3431625c65ac905b08461a5d`。
- [关闭审计](../../data/evaluation/results/document_semantic_comparison_close_audit_20261011.json)，
  SHA `9ae7f5be8e1651ded4c942e3b2093d8d1d64846c913de6a9be7c9669307c9805`。
- 本机operator为`outputs/riftcoach-semantic-comparison-20261011`，保留授权前快照、真实授权/
  CI/启动退出、checkpoint、主审notes与实际native捕获；sample1 expanded事件在submission内
  经严格replay核验，没有补造不存在的operator捕获。

收尾Provider0，自动任务`riftcoach`实读PAUSED并保持暂停。

独立工程收尾已完成，accepted=true/阻断0，32份实查文件SHA在原生final读取时逐一相等；
另核61冻结源码摘要、两免费审计内存重建、白名单和全部账目。工程终答/唯一dispatch与final
membership按已有native final policy实核，
[公开复核记录](../../data/evaluation/results/document_semantic_comparison_close_engineering_review_20261011.json)
SHA `b665f537f0c8e6fb3dcc1052b2a494743e7b504fc7f16abf52682181bd7df653`。
Host将工程dispatch正文加密，明文task SHA不可恢复，记录null而不代填；不是新业务审查或补签。
导入依赖有一次本地IPv6 bind能力探测，审计本体无socket事件/无外发，不能称整个进程绝对系统I/O零。

## 后续取舍与未完成项

[机制取舍](2026-10-11-post-comparison-mechanism-decision.md)停止同义教学付费试错、编辑迎合误报
及增加第六调用。免费SDK边界审计已精确复建5份issued请求，只改变temperature构造，
全部低温请求仍被冻结身份拒绝；它只证明本地表达能力，未证明Provider接受/遵循或语义改善。
免费整链核查进一步证历史initial/final在委派前拒低温，继承共享预算还强制重写1.0，当前不可达。
下一免费动作准备隔离原型核构造/共享预算/角色transport/receipt/fresh一致，保留整任务五调用；
原型尚未实现，无采用、新可执行身份或付费授权。

原15跨批覆盖库存10通过/3语义拒绝或分歧/2未认证，与本轮10/4/1不是同一计数。
历史2/15、3/15、remaining11、full15、remaining8、remaining4分别独立；旧第7/11缺口保留。
新资格0，正式同版本15、自然消费、8E、Coach/Training/四块联动、Worker-DB-API-UI-journal、
前端审美头像、Memory、身份运维、两树整合和八维学习均未完成，原依赖及已交付基础保留。
