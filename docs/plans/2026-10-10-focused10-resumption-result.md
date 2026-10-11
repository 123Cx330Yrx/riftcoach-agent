# 固定10例集中诊断：执行关闭与方案取舍

## 结论与本轮交付

本批经明确授权后首次执行，attribution:1完成初评→编辑→fresh（94/pass），
scope:3完成初评与编辑、fresh实际发送后触及300秒stream_deadline。其余8案未发送。
5个完成阶段均有真实全文双审；超时阶段没有完整回包或Host业务认证。
本批已硬关闭，不重启、重试、补签或把剩余额度借给新批。自动任务riftcoach已PAUSED。

这是有限的候选诊断证据，固定10例扫描未完成；正式同版本15、自然消费及8E未完成。
新资格0、original15_qualified=false、production_admitted=false。
旧文档3/15与另一身份历史2/15各自保留，不拼跨批成功数。

## 执行绑定及原始证据

- Backend：D:/riftcoach-agent-rq192-pr，分支codex/rq192-provider-stream-contract-ci。
- 执行HEAD：d790c15785d10e7df058eec13991bf93a3a6794e；公共CI37968309635全部success。
- 方案SHA：d976aa1ce4dae9dc7fd7e5c2a6051053c650ec68a857036657d9a63778aabbd5。
- run：data/runs/model_comparison/document-focused10-resumption-candidate-20261010。
- Operator：C:/Users/33502/Documents/Agent/outputs/riftcoach-focused10-preflight-20261010。
- authorization.json绑定用户“确认，继续吧”的真实原生消息、提交/CI/方案/身份/预算；
  preparation中的未授权标记保留为授权前快照，不回写历史。
- 原唯一runner6968（wrapper20572）已退出；execution/exit.json为exit1，
  结束UTC2026-10-10T02:31:57.157546+00:00。

授权上限28调用（GLM19/Flash9）、2709504tokens、8400活动秒、86400Host秒，
单次32768输出/300秒、SDK retry0，保守未缓存估价28.4471296元，非账单硬封顶。
语义拒绝停该案依赖、继续独立案；协议/传输/预算/身份/来源/native等硬故障停全批。
本次按硬故障规则停止，没有为收齐其余案例绕过关闭锁。

## 实际案例和语义边界

| 案例 | 实际完成与全文双审 | 未完成部分/判断 |
|---|---|---|
| attribution:1 | initial80/needs_revision；只改block14；final94/pass，issues为空 | 全链已接受；block4泛指仅advisory，未补成全部指标 |
| scope:3 | initial70/needs_revision；只改block4；两阶段通过 | final已发但超时；未建立语义失败，不能把semantic_accepted=false解释为认证拒绝 |
| claim-scope:1、4、6；scope:4；observed:2、3、4、5 | 无Provider发送 | 8案未执行，无质量结论 |

attribution block14明确把补刀和伤害两种差距都主要归因于辅助，伤害归因确实错误；
实际编辑保留正确统计，仅纠正该段。block4概括混合均值拉低没有断言每个指标，
不能因另一指标反向而补造全称错误。fresh保留block4/6的措辞advisory，不升级事实门。

scope block4明确比较中单早期死亡“几乎相同”，与胜2.5/负0.5冲突；
block14正确全样本胜2.5/负2.67不能撤销这句真错。实际编辑用明确数值改写，
没有重现旧修法“并未带来”，因此不能声称已隔离验证旧观测/因果歧义的机制。
两次block-keyed参数及成稿通过，只证明这两次定位/改文有效，不能当协议稳定率。

## 账目与时间

实际6调用：GLM4、Flash2；完成5次，未知用量1次，receiptless本地尝试0。
known_tokens及budget_known_tokens均81642；unknown_reserved_tokens及预算未知预留均77868，
来自超时请求的45100输入上界+32768输出上限，不是测得的实际消耗。
已知用量按未缓存价估算0.6973828元；未知调用不当0或免费，总实际账单未确定。
活动722.094秒、Host1581.64秒、wall2303.734秒，完成Host等待5次；未超本次整批上限。

| 调用 | 传输总耗时秒 | 首事件秒 | 首tool秒 | input/output tokens |
|---|---:|---:|---:|---|
| attribution initial GLM | 200.688 | 8.766 | 190.454 | 12936/6418 |
| attribution revision Flash | 15.984 | 9.250 | 10.187 | 14301/433 |
| attribution final GLM | 90.813 | 22.922 | 89.657 | 12959/3991 |
| scope initial GLM | 52.985 | 7.641 | 45.891 | 12949/2453 |
| scope revision Flash | 22.532 | 7.875 | 13.797 | 14362/840 |
| scope final GLM | 300.016（deadline） | 7.500 | 未出现 | 未知/未知 |

耗时来自各stream/result.json；首事件、首tool和usage来自progress.json。
持续前缀仅是本地已接收事件，字符数不是token计量，也不读取或公开私有reasoning正文。

## 超时控制路径核验与技术取舍

最早硬偏离：transport/scope-3/review/stream-003/result.json为deadline。
末次progress在299.094秒仍reading，last_reasoning同为299.094秒；HTTP请求1，
reasoning_chars22656、tool_delta_count0、usage未知。max_inter_event_gap1.015秒，
open5.578秒、advance290.655秒、processing0.922秒、progress_write0.847秒。
这支持“持续读取至整次截止”，不支持网络全程无响应或本地写盘耗去300秒。
不证明长推理的原因、供应商后台最终结果或600秒必能完成；不是503/401/429证据。

免费实读控制路径：现有factory保留实际request后调用GoldenProcessStreamProvider；
golden_stream_bridge.transport_limits对该GLM transport固定32768/300，
validate_request/run_child拒绝超限。父进程monotonic截止包含启动、读取和清理，
子进程只在完整EOF/close及assembly通过后交付ChatResponse；此次父进程到期kill/reap。
本地progress未记录close不等于进程仍活跃；result为deadline，未出现unreaped/cleanup_failed。
SDK读超时/候选内部330/360秒配置不能覆盖父进程的300秒硬截止。
未发现需要修复的本地计时/预算/重复发送缺陷，本轮不改模型或传输源码。

实际GLM initial/fresh均4条消息、1个tool、相同3838字符system政策；source消息16350字符、
knowledge消息2823字符相同，无assistant历史累积。attribution fresh报告消息2914字符、
scope fresh2917字符，输入上界45056/45100、wire44889/44950bytes。
本次差异不足以支持“fresh无限拼历史”或单靠缩短3字符解决超时；完整来源不裁剪。
3个完成GLM调用输出2453—6418tokens，终端tool参数106—751字符；未证触及输出上限。

| 可选方向 | 当前取舍及所需证据 |
|---|---|
| 原样重买scope fresh或剩余8例 | 不采用：已关闭，无重试授权，且不改变已暴露的300秒可达性疑点 |
| 立即叠加语义警告/修改编辑协议 | 不采用：5个已审阶段通过，超时不是语义反证；候选充分性仍未成立 |
| 降high/减输出cap/截来源 | 不采用：改变既有模型或完整审查边界；减cap也未证明可加快合法交付 |
| 直接把300改600 | 不采用现批：300是跨transport/observation/预算/身份的冻结约束，非一个CLI旋钮；更长时间是否足够未知 |
| 准备新的时间合同方案 | 下一主线准备：沿既有GLM/high、完整来源及质量门，先核每请求/整任务/Worker时钟和资格身份，比较有界延时与输入等价简化；只在能表达合法失败/恢复且能区分解释时提交具体新方案 |

本批收尾后先处理审查交付时间与任务预算的匹配，不立即另买尾链或全15，
不把请求可编码/CI成功视为时间或语义可达。若没有可证的冗余，不为凑变体裁剪政策或来源。
新时间合同如涉及采用标准/预算/传输身份改变，先完成影响、候选实现及相称免费检查，
再请求其具体授权；旧余量和本文件均不授权新Provider发送。

## 封存与独立收尾核验

full15_resumption_evidence seal使用绝对run路径严格只读回放、真实native核5阶段，
create-only生成data/evaluation/results/golden_document_focused10_resumption_result_20261010.json，
SHA76e9a70b808ce297d7d57c8f226a26daaa72f1f932de15f0c39467c582575f30。
103份原件SHA逐项重核全部一致，46个白名单JSON公开投影；原件未改，封存自身Provider0。
公开内容不含密钥或私有reasoning；无超时response/stage/journal/receipt补造。
提交后逐字节核验发现Git默认CRLF→LF转换，已按仓库现有做法为此单份封存设置-text，
保留最初seal的原始CRLF字节；公开Git对象与本机seal的上述SHA须相同，run原件未改。

现有独立主体只读收尾复核通过，再次严格回放核真实5个native事件、checkpoint、账目、
封存和原件不变；这是工程收尾判断，不补作业务认证。主审实读唯一completed原生final：
01a121b7-8b8d-79b0-897e-9e1307e2c983/01a123a9-1622-73e2-b78d-d9f39adbfe1b/msg_09d251f989eea676016ac9a4937c788191ab6c71493b163e8d。
Operator closeout-native-final.json SHA9b24b6baa9d6e7338f6f03da1d05d48f0aafb57588b93d7cb97694649c5bd71e。

自然Coach、本人Training、四块联动、Worker/DB/API/UI/journal、前端审美/头像、Memory、
身份运维、两树整合及八维学习保留原依赖。既有Training成果不替代当前15例主线，
本轮未改变阶段/准入/生产默认入口。
