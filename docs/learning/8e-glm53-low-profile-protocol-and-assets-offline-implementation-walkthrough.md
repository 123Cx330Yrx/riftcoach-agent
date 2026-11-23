# 学习复盘：低思考 G53-3-L 协议与新鲜资产

## 为什么要再拆一层

RQ-221 只观察过一次无工具响应完成，RQ-223 只完成了请求策略和预算墙的离线控制面。
这两者都不能替代新的三次协议门，更不能把旧考卷换档重跑。因此本批把协议门和资产
冻结分别做成可审计的离线步骤。

## 协议接缝

`AdapterProtocolSliceRunner` 现在可接收显式 `request_policy`。低思考候选由私有策略
绑定 4096 输出、固定采样和 90 秒 Agent/工具时限；普通产品仍使用已登记的
`runtime_profile`，两类入口互斥。协议顺序保持：结构化响应 1 次，再执行一次
`knowledge.search` 工具往返 2 次，总计 3 次。

`GLM53LowProfileProtocolReport` 只保留安全身份、调用/Token/延迟计数和每个协议案例的
摘要。它要求实现 SHA 与协议 SHA 一致，拒绝伪造策略，并把真实来源的显式确认与离线
Fake 来源分开；报告不能注册候选或授予生产准入。

## 新鲜资产准入

`glm53_low_profile_assets` 只读取三份冻结文件和两个合成 fixture，交叉检查 Dataset、
Input Plan、Context Snapshot 的 SHA 与 case 顺序，并确认新 case/marker 不复用历史门。
准入函数要求规则已冻结，但返回的 `external_provider_calls` 永远为 0；它不加载环境、
不创建客户端，也不写结果文件。

## 测试证明了什么

- Fake Provider 的三次协议会被固定为 4096/90 秒/`temperature=1`/`top_p=.95`；
- body-free 序列化不会泄漏正文、工具参数或 request ID，重复写入会被拒绝；
- 缺少真实确认、伪造策略、资产身份或上下文指纹漂移都会 fail closed；
- 新资产准入在没有任何 Provider 调用时完成。

## 还没有证明什么

本批没有真实 G53-3-L 回执，也没有执行 held-out 领域案例；不证明模型领域质量、
streaming 生产能力、成本/延迟稳定性、黄金切片、安全/部署合规或 8F。公共 CI 只会
关闭这批离线实现的可复现性闸门。提交
`411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的公共 Actions `33787508488` 三 job 已全绿，
公共 pytest `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`；下一步是在明确授权
下最多执行 3 次真实低思考协议门，之后才可另行运行三案例领域门。

## RQ-226：真实协议门复盘

用户在 RQ-225 公共闭环后授权一次有界真实运行。候选 profile 保持
`reasoning_effort=low`、4096 输出、90/120 秒、固定采样和零重试；协议只包含结构化合同
一调用与一次 `knowledge.search` 工具往返（首回合和终回合各一调用），因此严格为 `3/3`
次 provider 调用。

真实结果为 A1/A2 均 `passed`、`admitted=true`，终态序列为 `stop`、`tool_calls`、`stop`；
输入/输出/总 token `1007/84/1091`，累计延迟 `12062ms`。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json`
为 `2511` bytes、SHA-256=`a3077ce6d4729e676d0c0ce0d9a6429153075ca59e0850529dee4e29c0376e35`，
只保存安全身份、计数、终态和摘要哈希。

这证明的是“低思考候选能完成这组固定适配器协议”，不是“模型已进入产品”或“领域质量已通过”。
候选仍 disabled/未注册，产品 Runtime、默认模型、Workbench、Portal、Account、Auth、路由和
`production_media=0` 不变；held-out 三案例领域质量、成本/延迟稳定性、streaming 生产能力、
黄金切片、安全/部署/合规与 8F 仍未验证。下一步必须另行授权后才可运行领域门。

## RQ-227：真实领域门复盘

RQ-227 在实现 SHA `659757eca7ff1b658dfd164631512d3964c5a2ff` 的公共 exact-SHA CI
`33826568517` 全绿后，按用户授权执行一次且仅一次三案例观察。运行使用低思考/4096、无重试和
首个不安全失败即停止；领域调用 `6/12`，累计调用 `9/15`，领域/累计 token `17834/18925`。

结果要分层看：第 1 案的 Provider、工具、证据和评测均通过，Evaluation=96；第 2 案的 Provider、
工具、事实和引用仍完成，Evaluation=97，但最终 Skill 输出没有证据来源 ID，且禁用标记检查为 false，
因此命中 `evidence_missing` 与 `unsafe_publication`。第 3 案不是再次失败，而是遵守冻结规则被跳过。
这说明失败发生在“能否安全发布”这一输出合同，而不是请求是否到达模型；Provider 错误、超时和预算墙均
没有触发。由于脱敏策略不保存正文，不能仅凭收据判断模型是否执行了注入，还是在拒绝时复述了标记，
但当前门对两种情况都 fail closed。

回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
（7537 bytes，SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`）。结论为
`admitted=false`、候选未注册、生产准入 false；这不是 API 崩溃，也不等于模型一般能力已被判死刑。
下一步是离线检查证据 ID 传播和注入检测边界，随后再决定是否另立版本；不重跑同一考卷，不改变默认
Runtime、Portal、Account、Workbench、Auth、路由或 `production_media=0`。
