# 8E：GLM-5.3 候选评估台实现计划（RQ-200）

## 状态与范围

状态：`implementation-complete-local / candidate-only / public-ci-pending`。

本批只实现 RQ-199 冻结的 fake/local 候选评估台。实现仍在
`app/evaluation/`，不注册 Provider，不打开产品 streaming，不修改默认运行时、
AgentLoop、ToolRuntime、统一 Trace、Workbench、Portal、Account、Auth、路由或
`production_media`。没有读取 Key、真实 API、fresh-recovery、G53-7 或黄金切片。

## 已实现的最小纵向切片

### 1. 分阶段账本

`CandidateEvaluationLedger` 在知道首回合响应形状之前就预留 primary 槽位；收到
真实观察后才映射 `ResponseBoundarySnapshot`、重新运行候选策略并结算。每个预留只
能结算一次，异常、超时、关闭失败也会消耗已预留槽位。当前 activation gate 只有
不可伪造的 `disabled` 值，所以候选形状只会进入 `awaiting_recovery`，不会打开第二
次流。

账本的资源投影区分 `within`、`exceeded`、`unknown`。任一回合 Usage 未知时，
输入/输出累计值保持 `None`，不把未知当作零余额；这与旧的
`ResponseRecoveryLedger`（首回合快照已知）保持分层，而不是用哨兵快照放宽旧合同。

### 2. 单次事件泵

`CandidateEvaluationHarness` 调用注入的 `CandidateStreamTransport` 一次，只迭代
一条 normalized stream。每个事件依次送入 body-free
`CandidateStreamBoundaryObserver` 和仅内存的 `ProviderStreamAssembler`；正常 EOF
之后才分别封存。读取、翻译、身份、序号、终止、Usage 或关闭错误会同时毒化两条
路径并停止消费。`length` 的不完整装配结果只作为内部失败，不会构造成
`ChatResponse`。

完整 `stop`/`tool_calls` 流可被显式 `CandidateContentConsumer` 短暂接收；consumer
错误单独记为安全码，不能改变策略或账本，也不会执行 ToolRuntime。评估结束前会
清除装配结果引用。

### 3. 独立回执

`CandidateEvaluationReceipt` 的 schema 为 `candidate-evaluation-harness/1.0`，只
允许候选身份、尝试顺序、生命周期、字段状态、终止/错误码、ToolCall 数、Usage
数字、耗时、预算确定性和 SHA-256 请求标识。正文、reasoning、工具参数、Prompt、
Key、SDK 对象、原始 request ID 和异常原文均不能从回执、`repr` 或 JSON 得到。

## 验证矩阵

- 完整文本、完整工具调用、精确候选 `length` 形状、部分正文拒绝；
- 缺 EOF/终止/Usage、显式 null 与缺失、model/请求身份/序号错误；
- open/read/close/clock 异常、一次性迭代、资源关闭和未知 Usage；
- exact candidate binding/profile/policy、disabled activation、重复运行和重复预留；
- provider 请求 cap、sampling 与 90/120 秒候选窗口；
- consumer 独立失败、回执/Trace/异常/repr/JSON 的 body-free 断言。

本地聚焦测试为 `15 passed`；连同边界观察、流装配和旧恢复合同相邻回归为
`102 passed`。`compileall`、`git diff --check` 和治理检查
需在最终文档同步后重跑。

## 仍未做的事情

本批不提供真实 recovery 的激活凭据，不调用第二次真实流，不接入产品
`ProviderRegistry`/Runtime，不重跑 G53-3/G53-7，不改变严格 Flash v1 的
2048/零额外调用，也不宣称模型质量、领域采用或公共生产成熟度。下一检查点只取
同一干净提交的 exact-SHA 公共 CI；之后是否允许 fake recovery、真实 recovery、
黄金切片、生产准入或 8F，仍需独立决策与授权。

## 下一检查点

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-public-ci / pending`
