# 8E：版本化 GLM-5.3 候选 recovery 诊断实现计划（RQ-204）

## 状态与边界

状态：`completed-public / candidate-only / real-observation-fail-closed`。

本计划把 RQ-203 冻结的 v2 协议落成一个只供 fake/local 使用的评估接缝。它不是
产品运行时、不是 `LLMProvider`、不是默认模型切换，也不是对真实 GLM-5.3 请求的
授权。实现不会读取 Key、访问网络、发送 primary/fresh-recovery、注册候选、打开
`capabilities.streaming`、写统一 Runtime Trace，亦不会修改 Portal、Account、
Workbench、Auth、路由或 `production_media=0`。

## 要解决的问题与原则

旧诊断器把 SDK/I/O、同步账本和未知 Usage 的旧投影绑在一起，不能安全解释一次新的
候选 recovery 观察。本门用四个原则拆开它：

1. 先 `reserve` 再做任何 transport I/O，确保打开、读取、关闭或取消失败也有结算行；
2. 一条 normalized stream 只经过一次事件泵，同时驱动无正文观察器和仅内存的完整装配器；
3. 决定、失败类别、预算和费用都从观察结果重新推导，调用方不能填资格布尔值；
4. 所有持久化只保留 allow-list 的身份、形状、状态、数字和安全码，未知资源保持
   `null/unknown`。

## 实现内容

- 新增 `app/evaluation/candidate_recovery_diagnostic_v2.py`：
  - 精确绑定协议、profile、policy、实现/诊断/输入计划/上下文/nonce SHA；
  - 记录 ordinal/kind、角色和字段形状、工具数量、response-contract 标志、真实 cap、
    timeout、sampling 与 `retries=0`；
  - 使用 `CandidateStreamBoundaryObserver` 和 `ProviderStreamAssembler` 的同一事件泵，
    只把完整结果短暂交给显式 consumer；
  - 通过 staged ledger 保证 primary 预留、一次结算、最多两槽位；当前 disabled gate
    始终拒绝第二次调用；
  - 记录 Usage 三态、累计预算三态、unknown/estimated/actual 费用、六段单调延迟、
    八类失败和第一现场；
  - 提供严格的 body-free JSON 解析、canonical UTF-8/LF 和 create-only 原子落盘。
- 从 `app/evaluation/__init__.py` 导出上述评估 API，但不接入 Provider 注册表或产品组合根。
- 新增 `tests/test_candidate_recovery_diagnostic_v2.py`，使用完全本地的 normalized fake
  transport，覆盖完整文本、工具流、候选形状、缺边界、身份/工具/时钟/关闭/控制异常、
  permit、预算、费用、延迟、伪造回执、嵌套解析、原子落盘和静态导入边界。

## 验证契约

实现门的本地证据应至少包括：

- 新模块聚焦测试全绿；
- 候选流观察、provider-neutral 装配、候选评估台、恢复合同相邻回归全绿；
- Python 3.11/3.13 编译、`git diff --check`、治理检查和静态 no-I/O/import 检查通过；
- 不把本地 fake/local 测试写成公共生产成熟度，也不生成真实诊断结果 JSON。

本门完成后，RQ-205 已完成同一干净实现提交的 exact-SHA 公共 CI 与协议 dry-run；RQ-206
又在新的诊断提交上按一次性授权只执行 1 次真实 primary。即使该观察完成，也不能自动执行
G53-7、黄金切片、生产准入或 8F。

## 失败、恢复与回滚

- 任何不安全字段、未知 metadata、身份不符、形状哈希不符或回执派生矛盾都 fail closed；
- transport、protocol、identity、usage、budget、completion、consumer、control 只保存
  安全类别和 code/stage，不保存异常原文；
- 控制异常在安全结算后继续抛出，便于调用方停止；
- 既有 v1 严格 completion policy、旧诊断结果和产品 Runtime 不变，因此回滚只需移除
  本门隔离模块/测试，不涉及用户数据、数据库迁移或线上配置。

## 当前检查点

本地实现与聚焦验证已完成；候选 activation 仍为 `disabled`、`execution_allowed=false`，
`capabilities.streaming=False`，严格 Flash v1 仍为 2048/零额外调用。下一精确 checkpoint：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`

## RQ-206 真实观察结果与后续边界

RQ-206 使用本计划落成的 v2 诊断接缝，在干净隔离工作树只发送 1 次普通智谱
`zhipu/glm-5.3-flash` primary（SDK retries=0）。提交
`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的 Actions run `33603143606` 三 job exact-SHA 全绿，
实现基线为 `90242822df0e47304700644572bc12f0a3aa88ad`。流观察到 reasoning、可见正文、`stop` 和 EOF，
但首个可见正文为 `151453ms`、总延迟 `175875ms`；Usage 缺失、close 失败，单次 90 秒 attempt 门在晚到事件中触发，
所以回执为 `fail_closed / elapsed_limit`、`assembled_complete=false`，没有第二次 recovery，费用 unknown。
`open_elapsed_ms=0` 只是惰性流生成器的计时起点。

持久回执路径为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`，
`4355` bytes，SHA-256 `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`。
该样本只是候选传输/完成度证据，不裁决 API/Key、模型一般能力、领域准入或生产成熟度；候选 activation
仍 disabled，严格 Flash v1、默认模型与产品 Runtime 不变。

当前后续不再直接重测：先建立一个离线计划，解决惰性流无法被 observer 总墙钟硬中断、close 失败的
资源收口，以及 Usage-only 终态尾帧的显式接收/拒绝规则；完成聚焦测试和公共 CI 后，再由独立授权决定是否
进行新的真实观察。
