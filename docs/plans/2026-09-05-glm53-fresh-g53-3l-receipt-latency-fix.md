# RQ-233：新鲜 G53-3-L 回执延迟口径修复计划

## 目标

修复真实 G53-3-L 协议完成后因两层延迟口径不同而无法生成脱敏回执的问题。修复只改变回执
`latency_ms` 的取值来源，不改变请求、模型参数、最多 3 次调用、零重试、结构化响应、工具往返
或任何领域质量门。

## 已观察问题

用户授权后，以已通过公共 CI 的实现身份 `f99c142c269df765deb592c463ce6e2555bcc3fe` 发起一次有界
真实协议运行。运行进入回执构造后，被 `latency total does not match protocol` 拒绝，且 create-only
结果文件没有生成。预算包装器只累计 Provider I/O 耗时，协议案例累计端到端耗时；旧测试使用固定
时钟，未暴露两者在真实运行中的毫秒差异。

由于回执未生成，本次外部调用精确数量没有可持久核验证据，只能确认受 3 次硬上限和 SDK 零重试
约束。不得把这次尝试描述为协议通过，也不得自动重跑。

## 实施

1. 增加会单调推进的模拟时钟回归，证明 Provider I/O 与协议端到端耗时可以不同；
2. 让 `GLM53LowProfileProtocolReport.latency_ms` 使用协议案例耗时之和，满足字段既有语义与验证器；
3. 保持预算账本的 Provider I/O 耗时不变，不放宽回执、请求或准入 Schema；
4. 运行协议、预算、V2/V3 相邻回归、compileall、diff check 和治理检查；
5. 提交并取得修复 SHA 的公共 exact-SHA CI。

## 当前边界与下一步

修复提交 `110f9e8008486bfb976643a6abdaa8e88ea334e6` 的 Actions `33897787039` 三任务 exact-SHA
全绿，公共 pytest 2380、PostgreSQL 201、packaging-smoke 通过；尚未形成新的真实协议回执。候选仍
disabled/未注册，默认 Runtime、GLM-5.2 兼容/应急路径、Portal、Account、Workbench、Auth、路由和
`production_media=0` 不变。仍须用户重新授权，才可在该实现 SHA 上再执行一次新鲜 G53-3-L；V3
领域观察继续单独授权。

## RQ-234 执行结果（2026-09-05，取代上节待协议授权动作）

用户继续后已在 `110f9e8008486bfb976643a6abdaa8e88ea334e6` 代码身份完成一次新鲜协议。
A1 `1/1`、A2 `2/2` 均通过，3 次调用、SDK 零重试，输入/输出/总 Token `1008/108/1116`，
累计端到端延迟 `12812ms`。create-only 回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq234_v1.json`
为 2512 bytes，SHA-256=`fd500c57fbdb12ac408625d6c64b1cc0eb506debbb54525e3e8eb612892488eb`；
严格模型解析、canonical 字节一致性和 body-free 校验通过，相邻回归 26 passed。

V3 零调用预检已消费上述回执并返回 ready_for_real_call；本次没有执行 V3 领域题目。下一次
明确继续直接进入一次全新 V3 有界真实领域验收，消费现有代码 CI、该回执及冻结资产，不再
重跑本轮协议。候选注册、产品默认、GLM-5.2 回退和前端边界不变。
