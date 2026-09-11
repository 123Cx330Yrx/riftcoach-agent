# ADR-0078：复核并加固 GLM-5.3 候选 recovery 诊断边界

- 日期：2026-09-02
- 状态：`completed-local / candidate-only / diagnostic-version-pending`
- 范围：Stage 8 / 8E；`candidate-recovery-diagnostic-review`（RQ-202）
- 依据：ADR-0071、0072、0075、0076、0077；RQ-181–RQ-201；
  `app/evaluation/candidate_evaluation_harness.py`、
  `app/evaluation/candidate_stream_contract.py`、
  `app/evaluation/glm53_flash_response_recovery_diagnostic.py`

## 背景

RQ-201 已证明隔离的候选评估台可以在 exact-SHA 公共 CI 中复现，但这只证明
fake/local 控制面，不等于 recovery 已经可以发出第二条真实请求。本轮按授权复核
传输、预算、失败和脱敏边界，并检查旧的同步诊断器是否可以作为新版本的基础。

复核范围严格限定在 `app/evaluation/` 的候选控制面：不读取 Key、不调用 SDK 或真实
API、不注册候选、不改变产品 Runtime、默认模型、Workbench、Portal、Account、Auth、
路由、`capabilities.streaming` 或 `production_media=0`。

## 发现

### F1：回执的若干终态字段可以被调用方替换

`CandidateEvaluationReceipt` 和 `CandidateEvaluationAttemptReceipt` 是 frozen dataclass，
但 frozen 不等于字段来源可信。此前可以用 `dataclasses.replace()` 替换顶层
`terminal_state`/`next_action`、顶层安全错误、attempt 的 `disposition` 或
`assembled_complete`，在不重新观察流的情况下构造看似合法的回执；`budget_exceeded`
也缺少与受信观察值的绑定。

本轮在值对象构造边界增加派生校验：

- 顶层终态和下一动作从最后一个已结算 attempt 的决定重新计算；
- 顶层安全错误和 consumer 错误必须与最后一条观察/attempt 精确一致；
- `complete_text`、`tool_calls_ready`、`candidate_eligible`、`fail_closed` 的决定、
  原因、错误和装配完成状态必须与观察到的状态一致；
- budget projection 只能由候选 profile 的可信上限和观察到的资源推导，不能由调用方
  单独置位。

这些校验只保护 body-free 证据的内部一致性，不声称它提供了密码学签名或真实供应商
证明。

### F2：单次截止曾错误地复用累计窗口

候选 profile 的累计 elapsed 上限是 180 秒，但每个 attempt 的 agent 窗口是 90 秒。
此前评估台把 observer 的 `max_elapsed_ms` 直接设为累计上限，导致单次流可能活过
其 attempt 合同。现在 observer 使用
`min(profile.max_total_elapsed_ms, reservation.spec.timeout_s * 1000)`；账本仍独立
维护累计预算。这样不会把一次 90 秒超时误判为可继续，也不会改变累计账本的数值。

### F3：旧同步诊断器不具备新 recovery 版本所需的边界

`app/evaluation/glm53_flash_response_recovery_diagnostic.py` 直接导入 `OpenAI`、dotenv
和 `ZhipuProvider`，在 `confirm_real_call=True` 时可以发 primary 及 fresh-recovery；
它还复用旧的同步 `ResponseRecoveryLedger`，该账本对未知 Usage 使用 `or 0`，且
`execution_allowed` 的报告语义不能作为新候选控制面的 activation 证明。因此本 ADR
明确拒绝把它复制或小修后当作新诊断版本。旧脚本和旧账本保留为历史/兼容材料，不在
本轮修改。

## 决策

1. 保留 `CandidateEvaluationHarness` 为 fake/local、candidate-only 控制面；当前唯一
   activation 仍是 sealed `disabled`，最多一次 primary 观察，不发送 recovery。
2. 采用本轮的回执派生校验和 per-attempt deadline 修补，作为后续诊断设计的前置质量门。
3. 不在本轮建立新的诊断 schema、结果文件或真实调用授权。下一步必须先单独设计并
   审批一个新版本，明确请求身份、超时、Usage unknown、失败聚合、成本/延迟记录和
   脱敏规则；设计完成后仍需新的 exact-SHA CI/协议证据与真实调用授权。

## 证据与限制

- `tests/test_candidate_evaluation_harness.py`：`18 passed`；新增回执字段伪造、装配/决定
  绑定、budget projection 和单次 90 秒截止红绿测试。
- 候选流、装配、恢复合同、智谱 adapter 和 Flash profile 相邻集合：`127 passed，1 deselected`。
  被排除的单测只因 Windows 隔离工作树把冻结 JSON 检出为 CRLF；计划记录的是 canonical-LF
  SHA `804520031606cd0a7875fd2287e948a44e9b0100e38e1c44e5ed2619eaffc147`，该工作树原始
  CRLF SHA 为 `fe93c7bab57218cee03371bd1351f8edf52cfb318259045679f68e7f9cad6f02`。这不是
  本轮代码失败，也不修改冻结 fixture 或计划。
- `compileall`、`git diff --check`、`scripts/check_project_governance.py` 通过。
- 没有真实 API/Key、recovery、G53-7、黄金切片、生产准入或模型质量结论。

## 下一检查点

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`

在该授权前，不执行新诊断版本、真实 recovery、G53-7 或产品 Runtime 接线。
