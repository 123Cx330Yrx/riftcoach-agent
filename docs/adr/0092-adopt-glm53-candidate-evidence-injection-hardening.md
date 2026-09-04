# ADR-0092：采用 GLM-5.3 Flash 候选领域门的证据与注入边界加固

- 日期：2026-09-04
- 状态：`candidate-only / offline-complete / public-ci-pending`
- 范围：Stage 8 / 8E；RQ-228
- 加固版本：`glm53-flash-domain-quality-v1`

## 背景

RQ-227 的低思考三案例领域门并不是 Provider 崩溃：基线案例通过，用户边界案例的
回答也完成且得分 97，但检索结果没有可归因的来源 ID，同时注入检查失败，因而被
`evidence_missing` 与 `unsafe_publication` 共同拒绝。旧回执和旧 held-out 题目已经被
消费，不能通过改代码后重跑同一题目把结果改写成新的泛化证据。

这次需要修的是候选评测边界，而不是降低安全门：成功但没有来源的检索不能进入发布；
用户或知识资料里的指令性文本仍是数据，模型即使是在拒绝时提及它，也不能把不透明
标识原样带进公开报告。GLM-5.2 兼容路径和正常产品 Runtime 不应因这次候选修复而改变。

## 决策

采用候选入口显式开启、默认关闭的 `glm53-flash-domain-quality-v1`：

1. 在现有 Harness 增加可选的 `minimum_evidence_sources`。候选设置为 1；写入检索
   证据后若没有可归因来源，立即以 `evidence_required` 结束，保留证据工件和拒绝状态。
   默认值为 0，因此既有产品和 GLM-5.2 行为保持兼容。
2. 在候选执行的语境中插入可信的 system policy 附录，明确用户/检索字段是数据，禁止
   执行、服从或复述其中的指令、命令和不透明标识。附录通过 `ContextTrust.INTERNAL_POLICY`
   标记，普通 ContextBuilder 默认不插入。
3. 用与具体 marker 无关的安全决策器处理候选稿：只有同一语句/行内明确拒绝并需要说明
   时，才把 marker 替换为固定的安全占位语；任何孤立、执行式或歧义出现都 fail closed，
   异常只暴露安全错误码 `draft_injection_detected`，不暴露原文。
4. 候选语义观察优先读取经过 guard 的最终报告，并只记录检索调用数、成功数、返回片段数、
   来源数、工件存在性、abstain 状态和受限原因码。不得把 query、正文、reasoning、工具
   参数、凭据或 Provider 原始文本写入回执。
5. 加固只通过 `ProductionDomainCaseExecutor(..., quality_hardening=True)` 且必须绑定显式
   candidate request policy 才能启用；不把它接到正常 Runtime resolver、默认模型、
   Portal、Account、Workbench、Auth、路由或 `production_media`。

## 被拒绝的替代方案

- **只放宽注入检查或忽略空证据：拒绝。** 这会把 RQ-227 已观察到的安全/归因失败掩盖掉。
- **把规则写成 RQ-227 marker 特例：拒绝。** 这不能证明对新 marker 的泛化，也会污染 held-out
  证据。
- **立即重做全产品 Runtime、Trace 或默认模型：暂缓。** 这些属于候选准入、黄金切片和
  生产化的独立决策，不由一次失败归因授权。

## 验证与下一步

本地候选/相邻回归共 `102 passed`；`compileall`、`git diff --check` 和治理检查均通过。
这只是离线实现检查点。取得同一实现 SHA 的公共 exact-SHA CI 后，才可另立全新协议/资产
版本并申请一次新的真实领域观察；不重跑或覆盖 RQ-227 回执。

## 不变边界

候选仍 `disabled/未注册`，`production_admitted=false`；严格产品 Flash v1 仍为
2048 输出、零额外调用。GLM-5.2 保留为手动兼容/应急回退。Stage 8/8E 仍在进行，8F、
安全部署/合规、黄金切片、OP.GG breadth gate 与公共生产成熟度均未完成。
