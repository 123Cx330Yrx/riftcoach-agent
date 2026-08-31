# GLM-5.3-Flash 产品运行时晋级计划

## 目标

把用户已经选定的 `glm-5.3-flash` 从“只用于评估接缝”推进为产品组合中的唯一目标运行时，同时保留
GLM-5.2 的显式应急回退；不牵连 Portal、Account 或 Broadcast Workbench。

## 已完成的本地批次

- `ModelRuntimeProfile` 已注册精确的 provider/model、90 秒 Agent/工具窗、120 秒传输、2048 输出上限和
  Flash sampling。
- Agent 编译、AgentLoop、Harness `llm.chat`、Provider 构造、Runtime policy/Trace identity 和 Worker
  composition 已接收同一份可信档案；组合阶段支持显式传入，或从已绑定同一档案的 concrete Provider 安全推断。
- Flash Provider 强制官方普通 API 基址和 SDK `max_retries=0`；Worker 具备 360 秒默认 lease、60 秒
  heartbeat，并拒绝无法覆盖最坏执行窗的 lease。
- 聚焦 Provider、Runtime、Worker 和产品 compiler 回归已通过；没有在本批发起真实 API 调用。

## 尚未关闭的闸门

1. 将本地改动整理为用户批准的干净提交，并取得该新 SHA 的公共 `pytest`、PostgreSQL migration 和
   packaging CI；当前 dirty worktree 不能作为公共证据。
2. 在同一新 SHA 上重新取得新身份的 G53-3 有界协议证据；旧 `0f97…` 结果不能复用。
3. 在新协议证据基础上执行独立 G53-7 领域门，随后才评估完整 Riot + Data Dragon + official patch +
   OP.GG + 个性化训练建议的无正文黄金切片。
4. 补齐安全/部署/合规、队列切换与回滚 runbook；8F final evaluation/portfolio 仍在后面。

## 停止线

任何一项门失败都保留脱敏结果、停止无界重试，不修改旧 G53-4/G53-6 证据；不自动扩展第三地区、不改
Workbench、不把本地 unit/E2E/build 或真实矩阵观察称为生产准入。
