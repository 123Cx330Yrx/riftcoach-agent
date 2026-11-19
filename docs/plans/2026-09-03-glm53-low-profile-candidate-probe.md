# RQ-221：GLM-5.3 Flash 低思考候选探针计划/结果

## 目标

在不改产品 Runtime 的前提下，回答一个窄问题：`low + 4096` 是否能让当前
GLM-5.3 Flash 适配器在冻结、无工具上下文中完成一次可规范化响应。结果只用于决定
是否值得另立领域闸门，不直接授予候选准入。

## 实施范围

- 增加独立的低思考候选 profile，保持 `thinking=enabled`、`clear_thinking=false`；
- 通过显式候选构造器调用 Provider，避免普通产品解析器隐式采用；
- 固定 4096 输出、90 秒 Agent/工具窗口、120 秒传输窗口、`temperature=1`、
  `top_p=0.95`；
- 只允许一笔真实请求，关闭工具、retry、recovery、AgentLoop 和 Workbench；
- 写入 provider capability 目录中的 create-only、body-free JSON 回执；
- 不改 Portal、Account、Workbench、Auth、路由、默认模型或 `production_media`。

## 本地与公共验证

候选 profile/探针聚焦测试 `25 passed`，本次相关候选/流/智谱集合为 `357 passed`；
compileall、`git diff --check` 和治理校验通过。实现提交
`c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions run `33746833148` 三 job
exact-SHA 全绿。

## 一次真实观察

在同一实现身份上，探针只发送 1 次 `zhipu/glm-5.3-flash` 请求，SDK retries=0。
回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_profile_probe_rq221_v1.json`，
提交 `ef8d4b4`，canonical SHA-256=`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。
观察状态为 `observed`；`finish_reason=stop`、Usage 有效、输入/输出 token 为
`1973/498`、延迟约 `20.7s`。回执没有正文、reasoning、Key 或完整请求标识。

## 退出条件与限制

本批退出条件是：候选身份不可伪造、最多一次调用、回执不可覆盖、CI 精确匹配，且
能明确区分“无网络/客户端失败”和“真实响应观察”。这些条件已满足，但一次冻结无
工具探针不能关闭 G53-7，也不能证明低思考档在工具、多轮、领域任务中的质量、成本或
延迟稳定性。

候选仍 `activation_state=candidate`、`execution_allowed=false`、未注册；严格 Flash
v1 仍 2048/零额外调用，`capabilities.streaming=False`。下一步是另立低思考候选领域门
设计并取得明确决策，不自动追加真实请求。

当前精确指针：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`
