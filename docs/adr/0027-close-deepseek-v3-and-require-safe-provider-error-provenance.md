# ADR-0027：关闭当前 DeepSeek V3，并要求未来真实门保留安全错误 provenance

- 状态：Accepted
- 日期：2026-08-15
- 阶段：5D-7

## 背景

DeepSeek V4 Pro 已通过最小 structured/tool Adapter 协议，但没有获得领域质量准入。
V2 因 Token 合同不可达而停止；ADR-0026 的 V3 development Usage calibration 又在首个
请求后因响应未形成统一 `ChatResponse` 而首错停止。不可变结果只有高层
`provider_response_invalid`，实际 Usage、费用和具体 Adapter 原因均为 unknown。

源码证明 DeepSeek Adapter 已产生有限的安全细分 `ProviderError.code`，但实验分类器会
把大多数响应错误压缩成统一高层分类。本次原始细分信息已经丢失，且当前结果禁止修改、
覆盖或补跑。

## 决策

1. 关闭当前 DeepSeek V3 资源校准与领域采用尝试；
2. 不生成 V3 budget，不创建 V3 held-out，不重跑 V1/V2/calibration；
3. 保留 DeepSeek Adapter 和已准入的最小协议事实，但不准入领域质量、产品默认模型、
   自动模型路由或 Flash/Pro 分层；
4. DeepSeek 领域质量结论保持 `unknown`；
5. 后续任何真实 Provider 采用门必须在 Provider I/O 前以离线 TDD 建立双层失败记录：
   跨厂商稳定 `failure_code` 与允许列表约束的可空 `provider_error_code`；
6. 公开结果不得保存 Prompt、response、reasoning、SDK 异常、URL/header、原始 request ID
   或其他自由文本；未知细节保持 null/unknown 并 fail closed；
7. 本决策不立即实现新字段，不读取 Key 或调用 Provider；下一检查点按 ADR-0023 进入
   `G53-0` GLM-5.3 可用性与合同审计。

## 备选方案

- 建立 DeepSeek V4 诊断门并再次调用：可能定位原因，但需要新实验/预算/授权，且仍不能
  产生领域质量结论；当前拒绝继续围绕同一候选追绿；
- 无限搁置：成本为零但没有明确终态或重开门槛，会阻塞 5D-7，拒绝；
- 根据宽泛错误猜测并修改 Adapter：没有证据支持具体根因，拒绝。

## 后果

正面后果：

- 当前 DeepSeek 实验获得明确终态，不再追加真实调用；
- 低层协议成功与领域采用失败继续被准确区分；
- 真实可观测性 Bad Case 转化为跨 Provider 的安全前置合同；
- 不需要恢复或公开敏感响应正文。

代价：

- 当前仍没有获得任何真实 Provider 的领域质量准入；
- 本次具体 Adapter 根因永久保持 unknown；
- 未来 GLM-5.3 或其他 Provider 在真实门前需要先增加安全错误 provenance 的离线实现。

## 重新采用门

未来重开 DeepSeek 必须同时具备：新的模型/产品需求或同任务对照价值、全新实验与
development/held-out 身份、安全错误 provenance、资源可达性、固定预算、独立用户确认、
不可变结果和新的 ADR。旧 V1/V2/calibration 不得重新成为考卷。
