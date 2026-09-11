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

## 9. RQ-184 证据状态

RQ-184 已为后续候选合同取得实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 exact-SHA 公共 CI，
并在同一 A checkout 完成 G53-3 严格 `3/3` 调用；只新增脱敏结果的直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0`
也取得了三 job 公共 CI，A/B identity preflight 通过。该进展只证明公共可复现性和协议身份接缝，候选仍未注册；
下一步需要单独授权一次真实候选诊断，严格策略的 2048/零额外调用保持不变。

## 10. RQ-188 / RQ-189 真实诊断怎样校正策略假设

RQ-188 先证明普通 API 的 Flash endpoint/model 路径可达且生成已开始：冻结上下文的流式请求约 687ms 收到首个
reasoning chunk，但探针随即关闭，因此没有声称完整流、终止 Usage 或可交付正文。RQ-189 随后固定同一上下文、
`temperature=1`、`top_p=0.95` 和合法 thinking 形状，分别执行三次独立同步请求：

- `low+2048` 在 28.344 秒返回 `stop` 和可见正文，Usage 为输入 1973、输出 724；
- `low+8192` 在 45.594 秒截止内没有完整响应；
- `max+8192` 在 45.500 秒截止内没有完整响应。

这组证据否定了“输出上限越大就一定越容易完成”的简单假设，也说明同步超时不能直接解释成模型、账号或计费失败。
策略层仍不应把 reasoning 当正文、不应隐藏重试或静默扩大 token 上限。下一项只在 evaluation-only 范围观察流式
首个可见正文与 `clear_thinking` 请求形状；在取得完整终止状态、Usage 和后续领域证据前，候选保持未注册，严格
Flash v1 继续 2048/零额外调用。

## 11. RQ-190 / 首个可见正文与完整完成的区别

RQ-190 的两条单路流式观察都先出现 reasoning，再在几秒内出现首个可见正文；`clear_thinking=true` 和 `false` 都被
供应商接受。这说明流式路径可以降低用户等待首正文的时间，但探针在首正文出现后就主动关闭，所以没有终态
`finish_reason`、Usage 或完整正文。报告把预算状态写成 unknown，避免把未观测的 token 当成零。

这道实验不能证明 `clear_thinking` 的跨轮因果，也不能替代产品适配器的完整装配合同。后续若要接入 runtime，至少还要
分别证明：完整流终止、Usage 一致、正文/工具边界、reasoning 回放和统一 Trace；在此之前严格 Flash v1 仍是 2048/零额外调用，
候选保持未注册。

## 12. RQ-191 / 完整终态、Usage 与早退的边界

RQ-191 不在首个可见正文出现时关闭流，而是把 `clear_thinking=false`、低推理、2048 的冻结上下文流读到结束。它在
约 2.203 秒出现首块、3.531 秒出现正文，24.140 秒以 `finish_reason=stop` 终止，并收到有效 Usage（1973/652/0）。
因此可以把“首正文延迟”和“完整流终止/计量”分别写入证据。

报告仍只保留状态、计数、延迟和 token 数，不保留正文或 reasoning。这个成功案例不能推出高额度、长上下文、工具流、
跨轮 `clear_thinking` 语义或产品 runtime 已经接线；后续离线合同必须继续验证终态与 Usage 的一致性，并保持严格 Flash
v1 的 2048/零额外调用边界。
