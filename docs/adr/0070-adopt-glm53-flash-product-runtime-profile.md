# ADR-0070：采用 GLM-5.3-Flash 的产品运行时档案

- 状态：Accepted for the 8E product-runtime promotion slice; production admission still pending
- 日期：2026-08-31
- 检查点：`8e-productization / flash-only-runtime-promotion`

## 背景

用户已经明确选择普通智谱 API 的 `glm-5.3-flash` 作为 RiftCoach 产品运行时的目标模型。此前的 G53-6
领域门使用旧 Skill 的 30 秒质量资源阈值和 512/1024 输出上限，不能把由此产生的超时或截断直接解释为
Flash 的能力上限。RQ-175 已完成离线的模型专属档案，但当时仍只接在 G53-7 evaluation-only seam；如果
现在只改 `.env` 或模型字符串，Agent、Harness、Provider、Trace 和 Worker 会出现不同的预算与身份。

## 决策

1. 产品组合的目标路径固定为 Flash-only：精确的 `zhipu` + `glm-5.3-flash` 使用注册的
   `glm-5.3-flash-runtime-v1`；GLM-5.2 只保留为明确的兼容/应急回退，不再维护 Pro/Flash 自动分层或等待
   比较后再决定是否接入。
2. 档案是服务端常量，不接受请求体、环境中任意 profile 字段或模型输出的升权。它固定 Agent/`llm.chat`
   执行窗 90 秒、Provider 传输 120 秒、输出上限 2048、`temperature=1`、`top_p=0.95`，并与
   `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false` 的 Zhipu thinking profile 绑定。
3. Skill manifest 的 `timeout_s=30` 仍表示质量/资源门；Runtime policy 额外记录可信
   `execution_timeout_s=90` 和 profile id/version，不能把任意请求的 timeout 放宽。Trace identity 同步记录
   profile id/version；旧 Trace 的无 profile 形状继续可读。
4. 产品 Worker 使用官方普通 API 基址、SDK `max_retries=0`，Flash 的 lease 默认 360 秒、heartbeat 60 秒，
   显式配置的 lease 少于 300 秒时拒绝启动。切换前必须按 runbook drain/cancel 旧队列；不改变客户端 task
   fingerprint，也不把客户端字段写入身份。
5. 当前本地代码只完成接线和离线回归。正式默认/生产准入还必须在新的干净 exact-SHA 上完成公共 CI、同一
   SHA 的新鲜 G53-3 协议证据、G53-7 领域采用/完整黄金切片，以及安全、部署、合规和可回滚审查。未完成前
   不把本地通过写成公共生产成熟度。

## 取舍与后果

Flash 的较长执行窗和较高输出上限允许它完成真实的思考与工具回合，但会提高单任务占用和 Worker lease
要求；profile 因而同时约束 Agent、Harness、Provider client 和审计身份。旧 GLM-5.2/测试 double 仍可走
无 profile 的兼容路径，便于回滚和离线测试，但不能冒充 Flash 生产证据。

本 ADR 不修改 Portal、Account、Broadcast Workbench、Auth/RSO、Riot routing、媒体采用，也不批准真实
G53-7 调用；这些仍按 8E 既有顺序和独立质量闸门执行。

## 后续观察：RQ-181 响应完成度诊断（2026-08-31）

在 RQ-180 的一次 G53-7 尝试只留下 `incomplete_chat_response` 聚合码后，用户授权了一次独立、正文零留存的
首案例诊断。实现基线 `7cb66d218389c0e7d7aa7b2b1969a4678402f857` 上，首个 `agent_initial` 回合记录到
`finish_reason=length`、input/output `2220/2048`、空正文、非空 reasoning、0 ToolCall；适配器按本 ADR 所依赖的
fail-closed 合同拒绝了未完成响应。脱敏结果文件
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
的 canonical-LF SHA-256 为 `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`。

该观察只说明本案例中 2048 输出上限先被最大 reasoning 消耗，不改变本 ADR 的 Flash-only 路线，也不授权静默
提高全局上限或放宽适配器。RQ-182 已提出并在本地完成版本化响应完成策略与离线 TDD：严格 Flash v1
保持 2048/零额外调用，8192/一次 fresh-recovery 仅为未注册候选；候选要进入实现，仍须另建 runtime、
attempt/Trace、预算合同并取得新 exact-SHA 证据和独立授权。在此之前不重跑领域门、不把诊断写成生产准入。
