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
关闭这批离线实现的可复现性闸门。下一步是在同一实现身份上最多执行 3 次真实低思考
协议门，之后才可在另一次明确授权下运行三案例领域门。
