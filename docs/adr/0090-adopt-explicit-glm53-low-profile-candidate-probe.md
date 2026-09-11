# ADR-0090：采用显式 GLM-5.3 Flash 低思考候选探针

- 日期：2026-09-03
- 状态：`completed-public / candidate-only / observation-recorded / next-decision-pending`
- 范围：Stage 8 / 8E；RQ-221

## 背景

RQ-219 的候选 `max + 8192` 请求在 90 秒硬墙钟以 `fail_closed / elapsed_limit`
收口，RQ-220 又证明了终态、Usage 和恢复动作可以离线分开归因。下一条可验证假设是：
在保持智谱合法思考控制的前提下，`reasoning_effort=low`、`clear_thinking=false`、
4096 输出上限是否能在同一冻结上下文中形成完整的普通响应。这个假设不能由一次
`max + 2048` 或 `max + 8192` 失败直接推出，也不能直接改变产品策略。

## 决策

新增独立的 `FlashCandidateProfilePlan` 和
`run_candidate_profile_probe`。候选档案固定为：

- provider/model：`zhipu / glm-5.3-flash`；
- 思考：`thinking=enabled`、`reasoning_effort=low`、`clear_thinking=false`；
- 输出与时间：4096、Agent/工具 90 秒、传输 120 秒；
- 采样：`temperature=1`、`top_p=0.95`；
- 身份：`activation_state=candidate`、`execution_allowed=false`，不进入正常
  `ModelRuntimeProfile` 解析器。

探针只允许显式调用一次、不开工具、不运行 AgentLoop、不 retry、不 recovery；请求和
回执均以状态/计数/哈希为主，禁止保存正文、reasoning、Prompt、headers、Key、完整
request ID 或工具参数。候选 Provider 只能通过显式 `from_candidate_profile` 构造，
因此不会被普通产品构造路径隐式采用。

## 观察与证据

实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions run `33746833148`
三 job（pytest、postgres-migrations、packaging-smoke）均 `completed/success`，head SHA
精确匹配。随后按一次性授权执行 1 次真实请求，回执提交为
`ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，回执路径为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_profile_probe_rq221_v1.json`，
canonical SHA-256=`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。

该回执记录：`provider_call_count=1`、`network_used=true`、`status=observed`、
`finish_reason=stop`、`usage=valid`，输入/输出 token 为 `1973/498`，延迟约
`20735ms`；没有保存响应正文。这里的“通过”只表示冻结无工具上下文中的一次完整
响应被适配器规范化并记录，不能外推领域质量、工具多轮、成本稳定性或生产能力。

## 不做的事

本 ADR 不注册候选、不打开 `capabilities.streaming`，不改变严格 Flash v1 的
2048/零额外调用、不改变默认模型、AgentLoop、统一 Trace/预算、Portal、Account、
Workbench、Auth、路由或 `production_media=0`。它不覆盖 RQ-219/RQ-220 旧回执，也不把
一次无工具探针当作 G53-7、黄金切片、公共生产成熟度或 8F 完成。

## 下一步

若要判断低思考档是否值得进入更高层候选域门，必须另立版本：先复核新鲜 G53-3 与
输入/身份绑定，再设计独立 held-out 领域门，明确总请求预算、终态/Usage、工具回合和
失败收口。当前只停在
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`，
没有新的决定前不自动发送更多请求或接入产品。
