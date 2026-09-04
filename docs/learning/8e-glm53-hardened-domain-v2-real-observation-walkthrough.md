# RQ-230：GLM-5.3 Flash 加固领域 V2 真实观察复盘

## 1. 要解决的问题

RQ-229 只证明一套全新考卷可以在零网络条件下安全开考。RQ-230 增加独立的真实运行入口，
把这套考卷、质量加固策略、请求预算、既有协议证据和公共 CI 身份绑定在一起，再执行一次
有界观察。它仍是 8-Advanced 的 candidate-only 实验，不是产品上线开关。

## 2. 设计与代码地图

- `app/evaluation/glm53_hardened_domain_gate.py`：V2 Admission/Result、运行器和 CLI。
- `scripts/run_glm53_hardened_domain_gate.py`：命令行入口。
- `app/evaluation/glm53_hardened_domain_assets.py`：RQ-229 六文件资产准入与 SHA 绑定。
- `app/evaluation/glm53_low_profile_domain_gate.py`：复用的串行预算、逐案执行和 body-free 投影。
- `tests/test_glm53_hardened_domain_gate.py`：身份、预算、质量加固和序列化边界测试。

真实执行固定 `zhipu/glm-5.3-flash`、low + 4096、每案最多 4 次/全域 12 次、
24,000/72,000 token 墙、零重试/恢复/修订；执行器必须 `quality_hardening=True`。

## 3. 数据与控制流

先检查六类资产和 Context commitment，再核对实现 SHA 与公共 CI SHA；只有全部通过才允许
构造 Provider。领域案例串行执行，每次 I/O 前预留预算；Provider、工具、证据和评测结果只
投影为安全计数、状态和原因码。首个质量/安全失败会停止后续案例，回执 create-only 且不保存
Prompt、正文、reasoning、工具参数、Key 或请求 ID。

## 4. 本次真实证据

实现 SHA `5fe8606f205d49ca5dde969a5823a0eb75587c35` 的 Actions `33846260144` 三任务
exact-SHA 全绿；no-I/O preflight 通过后按用户授权执行一次观察。首案
`hardened_form_control_41` 消耗 3 次领域调用（累计 6/15），领域/累计 token 为
`10993/12084`，网络真实使用。`knowledge.search` 成功并返回 2 个来源，注入检查通过；
但事实核验与质量门失败，修订预算耗尽，终态为 `rejected / revision_budget_exhausted`，
失败码为 `fact_check_failed`、`quality_gate_failed`、`terminal_status_mismatch`，运行器
以 `domain_case_outcome_mismatch` 停止；另外两案 skipped。

回执：
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_hardened_domain_v2_rq230_v1.json`

- 7156 bytes
- SHA-256：`d1739c5d76da21c1109808b128e8ef82df251df32ea7355836f202d850e01c18`
- schema `1.0`、canonical round-trip、body-free 均通过
- `admitted=false`、`candidate_registered=false`、`production_admitted=false`

## 5. 如何解释失败

失败发生在领域输出质量/发布合同，不是 API 认证失败、Provider 崩溃或适配器异常；证据检索
与工具回合可用，也不能据此外推模型一般能力失败。由于回执不含正文，不能进一步判断事实
核验失败的具体文本原因。RQ-227、RQ-229 资产和本次回执均不可重跑或覆盖。

## 6. 验证与运行手册

```powershell
.\.venv\Scripts\python.exe scripts/run_glm53_hardened_domain_gate.py `
  --preflight-only `
  --implementation-sha 5fe8606f205d49ca5dde969a5823a0eb75587c35 `
  --public-ci-sha 5fe8606f205d49ca5dde969a5823a0eb75587c35
```

本地 no-I/O preflight、聚焦与相邻回归 `107 passed`、compileall、schema/canonical/body-free
校验和治理检查均通过；真实观察只执行一次。公共 CI 证明可复现性，不等于领域准入。

## 7. 边界与后续

候选仍未注册，默认 Runtime、GLM-5.2 手动兼容/应急路径、Portal、Account、Workbench、Auth、
路由和 `production_media=0` 不变。黄金切片、安全/部署/合规和 8F 仍未完成。当前下一步是
失败归因与是否另立版本的裁决，不能重跑已消费考卷或直接把候选设为唯一生产模型。

## 8. 面试式表述

“我为新鲜 held-out 考卷建立了独立、可审计的真实运行入口：先做零 I/O 的六文件 SHA 和
公共 CI 身份准入，再以固定预算串行执行。一次真实观察中 Provider 和证据工具都完成，但
事实核验/质量门失败，所以首错停止并保持候选未注册；公共可复现性、模型可达性和生产准入
被严格分开。”
