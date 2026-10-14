# 8E：版本化 GLM-5.3 候选 recovery 诊断设计计划（RQ-203）

## 状态与边界

状态：`completed-local / candidate-only / implementation-pending`。

本计划只冻结下一版诊断协议的设计。它承接 RQ-202 的离线边界复核，解决“旧同步
诊断器不能复用、但未来又需要一次可解释 recovery 观察”这一问题。当前不实现 v2，
不读取 Key，不发送 primary 或 fresh-recovery，不生成结果 JSON，不注册候选，不修改
产品 Runtime、AgentLoop、Workbench、Portal、Account、Auth、默认模型、
`capabilities.streaming` 或 `production_media=0`。

## 设计目标

1. 让每次真实候选诊断都能回答“使用了哪份合同、发生了几次底层调用、每次为何结束”。
2. 让 Usage、费用和延迟的未知部分保持未知，避免用零值或推测掩盖失败。
3. 让 recovery 明确是一次新的完整请求，并与隐式 retry、API resume 和 ToolRuntime
   副作用分开。
4. 让旧 1.0 结果不可变、新 2.0 记录可由 exact SHA 和脱敏摘要复现。
5. 在未来真实调用前，先通过 fake/local、公共 CI、协议 dry-run 和一次性授权门。

## 冻结的协议形状

### 协议身份

```text
protocol_id: glm-5.3-flash-candidate-recovery-diagnostic-v2
schema_version: 2.0.0
provider/model: zhipu / glm-5.3-flash
runtime_profile: glm-5.3-flash-runtime-v2-candidate / 2.0.0
policy: glm-5.3-flash-fresh-recovery-candidate / 1.0.0
```

一份 run 还要绑定完整的 implementation SHA、diagnostic code SHA、input plan SHA、
上下文形状 SHA 和本地随机 run nonce SHA。SHA 只做身份和追溯，不携带 Prompt、响应
正文或凭证。

### 请求摘要

每个 attempt 的摘要固定记录：序号、`primary`/`fresh_recovery`、消息数量和角色序列、
消息字段存在性/长度/工具数量的形状摘要、工具选择、response-contract 标志、实际
output cap、agent/transport timeout、temperature/top_p、retries=0 以及候选身份。
调用方 metadata 不能动态扩展这些字段，也不能选择 policy、profile 或 activation。

### Attempt 与 activation 时序

```text
reserve -> open -> normalized event pump -> observe/assemble -> settle -> receipt
```

- primary 在打开 transport 前 reserve；任何 open/read/close/取消/超时都算已发出的槽位。
- observer 先产生 body-free `BoundaryObservation`，再由候选 policy 重算决定；不接受
  caller-supplied `candidate_eligible`。
- 只有精确候选形状和一次性 `CandidateRecoveryExecutionPermit` 同时成立，才可 reserve
  `fresh_recovery`。当前 permit 不会生成，activation 仍为 sealed disabled。
- fresh-recovery 重新提交完整消息，标记为新的 attempt；不使用 resume token、SDK retry、
  AgentLoop retry 或 ToolRuntime。
- 最多两次底层调用、一次额外调用；第二次失败或再次 `length` 后立即终止，不创建第三槽位。

## v2 记录字段分组

| 分组 | 允许字段 | 禁止字段 |
| --- | --- | --- |
| 身份 | protocol/schema、provider/model、profile/policy、代码/计划/上下文 SHA、run SHA | Key、账户标识、原始 request ID |
| 请求 | ordinal/kind、角色和形状摘要、cap、timeout、采样与 retry 设置 | Prompt、消息正文、reasoning、工具参数/结果 |
| 观察 | opened/EOF/terminal/close、finish、正文/reasoning/tool 状态、工具数量、model SHA、request ID SHA | SDK 对象、原始响应、异常文本 |
| 资源 | valid/missing/invalid Usage、已知 token、分段毫秒、预算三态 | 以 `0` 代替未知资源 |
| 决定 | disposition、reason/error code、failure class/stage、settled、recovery skip reason | 调用方任意资格布尔值 |
| 费用 | `unknown|estimated|actual`、币种、价格快照 ID/SHA、金额（可空） | 猜测单价、账户账单、密钥信息 |

## 预算、延迟与费用规则

候选硬上限保持单次 output 8192、agent 90 秒、transport 120 秒；累计 input 32,000、
output 16,384、elapsed 180,000ms，最多 2 attempts/1 次额外调用。真正发送的 request cap
要单独记下，避免把请求 cap 和 profile cap 混为一谈。

预算状态为 `within`、`exceeded` 或 `unknown`。只要某个必要资源未知，就不能报告
`within`；input/output 总量用 `null` 表示未知。延迟使用单调时钟的整数毫秒，分别记录
open、首事件、首正文、terminal、close 和 total；未观察到的阶段为 `null`。

费用只有在 Usage 完整且运行前冻结、来源可验证的公开价格快照存在时才可为
`estimated`；供应商提供可核验本次账单凭证时才可为 `actual`。其他情况保持 `unknown`
且金额为 `null`。本门不获取价格或账单。

## 失败聚合

Attempt 的失败类别固定为：
`transport`、`protocol`、`identity`、`usage`、`budget`、`completion`、`consumer`、
`control`。顶层由已结算行推导 `run_state`、第一安全失败 `first_failure`、最后
`terminal_reason` 和 `recovery_skip_reason`；后续异常不得覆盖第一现场。控制异常清理
后继续传播，但槽位仍留下 `interrupted` 的安全结算。

## 实施前测试矩阵

实现门至少要有以下 fake/local 测试：

1. 完整文本、工具流、精确候选形状和 partial-content 拒绝；
2. 缺 EOF/terminal/Usage/model/request identity，显式 null 与字段缺失的区别；
3. open/read/translate/close/clock/取消异常及资源关闭；
4. permit disabled/过期/重复/身份不符、第二次成功/失败/再次 length；
5. 单次 cap、累计 token/time、unknown Usage、第三次和重复 settle；
6. 费用 unknown/verified estimate 的边界、分段延迟与单调时钟错误；
7. receipt/trace/repr/日志/JSON 的 body-free 和原子 create-only 落盘；
8. exact SHA、协议版本、候选身份及跨 run 伪造；
9. 静态确认不导入产品 Runtime、ProviderRegistry、SDK 或网络，不改变默认能力标记。

## 未来执行闸门（本计划不执行）

实现后需先取得新实现的 exact-SHA 公共 CI 和同 SHA 协议 dry-run；再由用户单独授权
一次真实诊断，执行密钥只读存在性检查、费用/延迟停止线和运行后人工审查。真实候选
诊断即使成功，也不能直接改变产品默认、打开 streaming、重跑 G53-7、进入黄金切片
或宣称 Stage 8/8E/8F 完成。

## 本门证据与下一步

本门证据是 ADR-0079、本计划和学习 walkthrough 对协议身份、时序、预算、Usage、费用、
延迟、失败聚合、脱敏和替代方案的完整冻结；没有代码或外部调用变更。RQ-202 的
`18 passed`、`127 passed/1 deselected`、compileall、diff check 和 governance 证据
继续有效，但不被本设计重新计数。

下一精确 checkpoint：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`

只有再次授权后，才实现上述 v2 fake/local 协议。
