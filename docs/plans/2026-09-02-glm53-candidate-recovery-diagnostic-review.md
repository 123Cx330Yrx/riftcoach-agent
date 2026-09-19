# 8E：GLM-5.3 候选 recovery 诊断边界复核计划（RQ-202）

## 状态与范围

状态：`completed-local / candidate-only / diagnostic-version-pending`。

本门承接 RQ-201 的公共 CI，仅做一次离线代码复核和最小安全加固。目标是确认候选
评估台不会接受伪造的终态、错误、装配或预算投影，并确认单次 attempt 不会越过
90 秒窗口。不得读取 Key、调用 SDK/真实 API、发送 recovery、重跑 G53-3/G53-7、
修改产品 Runtime、Workbench、Portal、Account、Auth、默认模型或前端。

## 复核步骤与结论

### 1. 回执来源审计

- 以 `dataclasses.replace()` 对顶层 state/error 和 attempt decision/assembly/budget
  做负例构造；
- 让 `CandidateEvaluationReceipt` 从最后一条观察重新推导 state/action/error；
- 让 attempt receipt 将 disposition、reason、assembly 和 budget projection 绑定到
  body-free observation；
- 保留 consumer error 的独立字段，不让 consumer 异常改变策略判定。

结论：伪造字段在值对象边界被拒绝；回执仍不是签名凭证，只是内部一致的脱敏投影。

### 2. 预算与截止审计

- 每次 primary 先 reserve，继续由 ledger 维护累计预算；
- observer 的 elapsed 上限改为 attempt spec 的 90 秒与累计 180 秒二者较小值；
- unknown Usage 仍保持 `None`/`unknown`，请求方 cap 不被误写成累计 profile 超限；
- 不新增第二次调用，当前 disabled activation 继续拒绝 fresh-recovery。

结论：单次截止与累计预算分层，失败槽位仍只结算一次并 fail closed。

### 3. 旧诊断器复用审计

检查 `glm53_flash_response_recovery_diagnostic.py` 的 import、I/O 入口和账本投影，确认
它直接拥有真实 SDK/Provider 路径，且旧账本把未知 Usage 当零。因此不把旧脚本作为新
诊断版本的实现基础；本轮不改旧文件，避免把历史真实调用入口混入候选控制面。

## 验证矩阵

- harness 聚焦：`18 passed`；
- candidate stream / neutral assembler / recovery contract / Zhipu adapter / Flash profile
  相邻集合：`127 passed, 1 deselected`；
- `compileall`、`git diff --check`、治理检查：通过；
- 旧同步诊断测试未作为本门证据：隔离 Windows 工作树的 CRLF 冻结 fixture 与计划中的
  canonical-LF digest 不一致，先在环境层记录，不改 fixture/plan。

## 不纳入本门

本门不建立新的诊断 schema，不生成新的结果 JSON，不发真实 primary/recovery，不重跑
G53-3/G53-7，不更新默认 Flash v1（2048/零额外调用），不打开
`capabilities.streaming`，不接入 AgentLoop/Worker/统一 Runtime Trace，不触碰
Portal、Account、Workbench、Auth、路由、媒体采用、黄金切片、安全部署合规或 8F。

## 下一检查点

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`

只有获得新的明确授权后，才设计版本化诊断协议；设计完成后还要分别取得 exact-SHA
公共 CI、同 SHA 协议证据、成本/延迟审查和真实调用授权。
