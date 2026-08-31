# 8E 学习材料：GLM-5.3-Flash 响应完成策略

日期：2026-08-31
对应需求：RQ-182 / ADR-0071

## 1. 问题与原理

一次模型调用不一定能产生可交付的正文。RQ-181 的真实形状是：结束原因是
`length`，总输出额度已用完，但正文为空、reasoning 非空、没有工具调用。隐藏
思考不是用户答案，所以不能把它“拼”成正文。Agent 系统的基本原则是：只有经过
适配器完整校验的结果才能进入统一 `ChatResponse`；无法证明完整性的响应要安全
拒绝，而不是猜测或无限重试。

## 2. 设计与实现

`app/providers/response_completion_policy.py` 提供三个不可变对象：

- `ResponseBoundarySnapshot`：只记录结束原因、字段状态、工具数量和 Usage 状态；
- `ResponseRequestContext`：只记录受信阶段、合同/工具/副作用开关及剩余预算；
- `ResponseCompletionPolicy`：按精确 provider、model、runtime profile 和语义版本
  计算判定。

当前注册的是严格 `v1`，零额外调用。更高上限的 fresh-recovery 候选被明确标记为
`candidate`，不能被解析器自动选中。

## 3. 代码地图

```text
app/providers/response_completion_policy.py
  ├─ ResponseBoundarySnapshot
  ├─ ResponseRequestContext
  ├─ ResponseCompletionPolicy.decide()
  ├─ 严格 v1 注册项
  └─ 未注册 fresh-recovery 候选
tests/test_response_completion_policy.py
  └─ 41 项纯离线合同测试
```

本批没有修改 `app/providers/zhipu.py`、`app/agent/loop.py` 或统一消息模型。

## 4. 数据与控制流

```text
供应商响应
  → 现有适配器先做解码与脱敏
  → 状态快照 + 受信请求上下文
  → 注册策略 decide()
  → 完整正文 / 工具回合 / fail closed
```

候选恢复只会得到 `candidate_eligible` 这个离线判定；由于候选尚未注册，
`continuation_allowed` 仍为假，不会产生第二次网络请求。

## 5. 验证证据

聚焦命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_response_completion_policy.py -q
```

结果：`41 passed`。测试验证策略不可变、精确身份绑定、输出上限不可升权、
RQ-181 的 reasoning-only 截断、正常文本/工具回合，以及过滤、未知结束原因、
工具/合同/副作用/阶段/时间/token 预算等拒绝路径。

## 6. 运行方法

这是无 I/O 的策略库，不需要 Key、服务器或外部服务。真实诊断证据仍使用既有
脱敏 JSON；不要把 Prompt、正文、reasoning、工具参数、Key 或原始请求 ID 写入
新快照。

## 7. 失败、安全与范围边界

- `finish_reason` 是判断截断的依据，不能用“输出刚好等于上限”自行推断；
- `stop` 但无正文、`tool_calls` 但无调用、无效 Usage 和未知结束原因均拒绝；
- 候选只允许初始 Agent 回合、空正文、非空 reasoning、0 工具、有效 Usage、无
  结构化合同/工具副作用且剩余预算足够；
- 当前不支持续写句柄，也不修改 AgentLoop/Trace/预算账本，因此不宣称恢复能力。

## 8. 面试准确表述

可以说：

> 我把 GLM-5.3-Flash 的响应完成边界做成了精确绑定、版本化的纯策略。它只接收
> 脱敏状态，区分完整正文、工具回合和截断拒绝，并把潜在恢复限制在白名单候选，
> 不会把 reasoning 当答案，也不会偷偷增加模型调用。

不能说：

> GLM 已经支持自动续写、已经通过领域准入，或 8192 候选上限已经成为生产默认。
