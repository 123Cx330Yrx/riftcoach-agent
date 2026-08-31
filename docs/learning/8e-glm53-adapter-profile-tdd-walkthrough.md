# 8E：GLM-5.3-Flash 适配档案离线 TDD

> 说明：本文前半部分记录 RQ-165 的历史 `enabled + low` 适配；该合同已由
> RQ-171 的 Flash 保留式思考适配取代。旧结果和旧 SHA 仍作为不可变历史证据，
> 不代表当前运行档案。

## 1. 问题与原理

现有智谱适配器为了兼容历史 GLM-5.2，在每个请求里固定发送
`thinking.type=disabled`，并把非空 `reasoning_content` 当成不可接受的响应。
官方普通 API 的 GLM-5.3-Flash 使用精确模型标识 `glm-5.3-flash`，要求启用思考，
因此不能只替换模型字符串。G53-1 的目标是把厂商差异收敛到一个可审计的、不可变的
模型档案，同时不改变 provider-neutral 的 `ChatRequest`/`ChatResponse` 合同。

这一步属于适配器协议层，不是模型质量或 Agent 领域准入。它不读取密钥、不创建真实
网络客户端、不修改默认模型，也不把 Flash 宣称为生产模型。

## 2. 设计与实现

`app/providers/zhipu_profiles.py` 定义 `ZhipuThinkingProfile`。档案包含稳定的
`profile_id`、关联模型、`thinking_type`、`reasoning_effort` 和可选的
`clear_thinking`，构造时拒绝不安全组合。已知模型按精确 ID 解析：

| 模型 | 档案 | 请求扩展 |
|---|---|---|
| `glm-5.2` | `glm-5.2-disabled-thinking` | `thinking=disabled` |
| `glm-5.3` | `glm-5.3-enabled-low` | `thinking=enabled`、`reasoning_effort=low` |
| `glm-5.3-flash` | `glm-5.3-flash-enabled-max-replay` | `thinking=enabled`、`clear_thinking=false`、`reasoning_effort=max` |
| 未知/测试模型 | `legacy-disabled-thinking` | 历史 disabled 回退 |

`ZhipuProvider` 和受控 capability probe 都从档案生成一次性请求体，调用方不能通过
`ChatRequest` 覆盖思考参数。`ZhipuSettings.thinking_profile` 只由模型解析，工厂把同一
档案传入 Provider；CLI 对已知模型使用隔离的结果文件名前缀，避免覆盖旧 GLM-5.2 证据。

## 3. reasoning 与工具边界

RQ-165 的“消费后丢弃 reasoning、拒绝多 ToolCall”是历史安全边界。当前 RQ-171
为 Flash 增加了显式的内部 `reasoning_content` 字段：只允许出现在 assistant 消息，
适配器和 AgentLoop 原样回放，公开日志、证据和结果仍只保留形状/摘要，不保留正文。
多 ToolCall 现在接受并保持返回顺序，由 AgentLoop 先整批预检，再顺序执行；
`parallel_tool_calls` 能力标志仍为 false，因为这里不是并发执行。

非字符串 reasoning、错误的角色携带方式、重复 ToolCall ID、非法 JSON、finish reason
不一致和 usage 缺失仍会 fail closed。当前中立消息仍是文本合同；Flash 官方的图像、
视频和文件输入需要另立多模态适配批次，不能把它们伪装成普通字符串。

## 4. 验证与运行方法

离线验证使用仓库虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_zhipu_thinking_profiles.py `
  tests/test_zhipu_provider.py `
  tests/test_zhipu_capability_probe.py `
  tests/test_probe_zhipu_capabilities_cli.py `
  tests/test_provider_registry_config.py
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts/check_project_governance.py
```

本批聚焦回归为 `70 passed, 29 subtests passed`，compileall 与治理检查通过；没有真实
Provider/Riot/OP.GG 请求。真实 API 仍必须在 G53-2 exact-SHA CI 之后，经单独授权的
G53-3 最多三次协议门执行。

## 5. 失败、安全与面试表述

适配档案错配、非法思考组合、非字符串 reasoning、不可回放的工具 reasoning 和并行
ToolCall 都会在中立响应或外部调用前失败；错误只暴露固定 code，不保存密钥、原始
prompt、响应正文、reasoning 或未哈希请求 ID。普通 API 与 Coding Plan 是不同入口：
本批只记录普通 API 的模型/参数合同，不证明当前账户余额、权限或模型可用性。

可准确表述为：“我为同一 Zhipu adapter 建立了按模型选择的不可变 thinking profile，
保留 GLM-5.2 的 disabled 兼容路径，为 GLM-5.3-Flash 使用
enabled/max/clear-thinking-false；reasoning 只在内部工具回放链路原样传递，公开证据
不泄漏正文，多 ToolCall 由 AgentLoop 安全地顺序消费。该批次证明接缝兼容性，不证明
模型领域质量、生产部署或默认切换。”

官方参考：

- [GLM-5.3-Flash 模型文档](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash)
- [智谱普通 API 介绍](https://docs.bigmodel.cn/cn/api/introduction)
- [智谱 Coding Plan FAQ](https://docs.bigmodel.cn/cn/coding-plan/faq)

## 6. G53-2 exact-SHA 公共验证

G53-1 的实现和测试被隔离为 9 个文件的提交
`0f97b92683e4981842e745a695864deb611bb630`。提交前扩展聚焦回归为
`82 passed, 29 subtests passed`，并通过 compileall、cached diff 与治理检查；现有 Portal、Account、
Workbench、截图、资产和混合文档改动都没有进入该提交。

GitHub Actions run `33325222755` 的 head SHA 与该提交精确一致，`pytest`、
`postgres-migrations`、`packaging-smoke` 三个 job 均成功。公共 clean checkout 的 Python 汇总是
`1912 passed, 145 skipped, 1 warning, 127 subtests passed`。现有 workflow 已覆盖所需门禁，因此
G53-2 没有为了追绿新增 job 或放宽合同。

这一结果把 G53-2 标记为 `completed-public`，但 CI 全程 no-I/O：没有真实 Provider/Riot/OP.GG 调用，
没有读取/输出 Key，也没有修改 `.env`、默认模型、Workbench、Auth、路由或媒体采用。下一项是最多三次
真实调用的 G53-3 有界协议门，必须等待用户另行明确授权；G53-4 领域门、完整 8E 和 8F 仍未完成。

## 7. G53-3 首次真实协议尝试与失败边界

用户明确继续后，使用进程级临时配置启动 `adapter_protocol`，最多允许 3 次调用。第一次 A1 结构化请求
返回脱敏 `authentication_failed`，runner 立即跳过 A2；结果为 `calls_used=1/3`、`admitted=false`，没有重试。

结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol.json` 通过
`AdapterProtocolSliceReport` schema 校验，SHA-256 为
`b10827f18dc810085a0d3883ebb7175709f4c244c30c937d5d220ab1ec1d0d9a`。文件只保存状态、错误码、调用数、
计量和摘要哈希，不保存响应正文、reasoning、Prompt 或 Key。

`authentication_failed` 是当前安全映射的合并错误码，不能单独判断是 Key 无效、账户权限不足还是 endpoint
接缝错误；旧 Key 后来确认已被删除。用户创建普通 API Key 并修正 `.env` 后重开 G53-3：A1 1/1、A2 2/2
通过，总计 `3/3`、`admitted=true`；脱敏结果为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json`，SHA-256
`1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`。该通过只证明普通协议接缝，不等于领域质量或
生产准入；G53-4 仍需单独授权。

## 8. G53-4 新鲜领域门：一次运行与首错边界

G53-4 与 G53-3 使用不同证据层：G53-3 只证明普通 API 的结构化/工具协议接缝，G53-4 必须使用全新匿名
Dataset、Input Plan 和 Prompt/Context snapshot，在同一生产 Executor、RAG、Evidence、Evaluation 与安全发布
合同下检查正常复盘、用户备注注入和知识注入三类案例。执行前的 no-I/O preflight 校验所有 SHA、协议结果、
代码/CI 身份、预算和输出路径；预检不构造 Provider，不读取 Key，外部调用为 `0`。

用户授权后真实门只执行一次，预算是领域最多 `12` calls、每案 `4` calls、总 Token `12,000`、每请求输出上限
`1,024`、无重试/无修订、首错停止。首案第 1 次 Provider 响应含并行 ToolCall，当前 Zhipu Adapter 以
`unsupported_parallel_tool_calls` fail closed；没有规范化响应、工具执行、RAG/Evidence、Evaluation 或发布，
后两案跳过。结果为领域 `1/12` calls、`0` normalized tokens，连同 G53-3 为 `4/15` calls、`1115` tokens，
费用状态 `unknown`。

不可变脱敏结果为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_v1.json`，
SHA-256 `ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`。该结果只说明本次领域门未准入，
不证明模型一般质量，也不授权放宽并行 ToolCall 合同、重跑已见考卷、切换默认模型或进入生产；新 runner/资产
尚未取得 exact-SHA 公共 CI。Workbench、Auth、前端、DeepSeek 和 `production_media=0` 均保持不变。

## 9. G53-5 全能力矩阵与工具流上限诊断

RQ-171 的适配器合同修复完成后，用户明确要求在普通 API 上尽可能全面验证 Flash，但这次验证仍必须是
有界、一次性、可脱敏和不可覆盖的实验。新的矩阵使用独立输入/输出身份，在 dirty worktree（HEAD 与
`origin/main` 均为 `0f97b92683e4981842e745a695864deb611bb630`）中执行 11/11 次调用、总计 46,151
tokens，覆盖文本思考、严格 JSON、多 ToolCall 与思考回放、长上下文、开发集 Agent、普通文本流、工具流
和 vendor-only 图像输入。结果文件
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_capability_matrix_v1.json` 的
SHA-256 为 `bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`，8 个案例中 7 个通过。

F1/F2 证明 Flash 的文本与结构化接缝，F3 证明模型可在同一轮返回两个 ToolCall、AgentLoop 可按顺序执行并
精确回放 reasoning，F4 的两个长上下文请求都通过但 `cached_input_tokens=0`，所以缓存只能记为
`unproven`；F5 是开发集合成事实的 Agent 链路，F6 观察到普通 SSE 文本流（194 个 chunk），F8 观察到
vendor raw 图像输入。F7 原矩阵的每请求 512 输出上限下收到 `length`，适配器安全报告为
`incomplete_chat_response`；这不是模型工具流被证伪，也不能把未规范化的 token 计量当作实际消耗。

为区分输出上限截断与协议不兼容，随后另建了唯一一次的工具流 follow-up，只改变 `max_tokens: 512 → 2048`，
其余提示词、`timeout_s=30`、`temperature=1`、`top_p=0.95`、Flash `enabled/max/clear_thinking=false`、
`stream=true`、`tool_stream=true` 和 SDK `max_retries=0` 保持一致。结果
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json` 的
SHA-256 为 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`；唯一一次调用通过，
总计 557 tokens，完整响应 `finish_reason=tool_calls`、1 个 ToolCall、372 个 reasoning chunk、15 个工具
片段。只保存工具顺序/参数摘要哈希、reasoning 哈希、模型和请求 ID 哈希，不保存提示词、参数正文、思考正文、
SSE 原文或 Key；工具没有执行。这个 follow-up 只证明厂商/适配器 transport assembly，不提升 provider-neutral
streaming、Agent 生产链路或公共 CI 状态，`production_admitted=false`、`public_ci_confirmed=false`。

矩阵与 follow-up 都不能宣称生产成熟度：安全/部署/合规、公网发布、OP.GG breadth、完整 Riot+Data Dragon+
official patch+OP.GG+个性化训练的 body-free golden slice，以及 8F final eval/portfolio 仍未完成。Workbench、
Auth、Portal、Account、默认模型、`.env` 和 `production_media=0` 均未改变；旧 G53-4 领域失败证据保持不可变。

## 10. RQ-175：把 Flash 的执行预算从旧考卷中隔离出来

RQ-174 暴露的是两层限制叠在一起：旧考卷把单次输出默认为 512/1024，Skill manifest 又把一次 Agent 运行
截止在 30 秒。前者容易在思考和工具调用尚未结束时截断响应，后者是该 held-out 数据集的质量资源阈值，
不应冒充智谱 Provider 的网络硬上限。RQ-175 不修改旧 Dataset、Plan 或结果，而是新建
`app/model_runtime.py` 的不可变 `ModelRuntimeProfile`，只为精确的 `zhipu/glm-5.3-flash` 注册：

| 层 | Flash profile 值 | 作用 |
|---|---:|---|
| Agent 总执行窗 | 90 秒 | 给思考、工具往返和最终回答留出时间 |
| `llm.chat` 工具窗 | 90 秒 | 让 Harness 的一次 Provider 请求与 Agent 档案一致 |
| SDK/传输超时 | 120 秒 | 覆盖请求级窗口，避免客户端先于业务截止终止 |
| 单次输出上限 | 2048 | 首个受控上限；来自 RQ-173 的 2048 工具流成功观察，不是官方最大值 |
| 采样 | `temperature=1`, `top_p=0.95` | 与官方 Flash 推荐组合一致 |

传递链必须完整：`AgentRunCompiler` 把 profile 变成 `AgentRunRequest`，`AgentLoop` 复制到每次
`ChatRequest`，`llm.chat` 工具和 G53 预算包装器在最终边界再次固定 timeout、sampling 与输出上限，
`create_glm53_provider` 则把 120 秒传输窗口交给 OpenAI-compatible client。这样即使自定义 executor
试图传入更大的 `max_tokens` 或不同的 temperature/top_p，也只能被截断/重置，不能借参数升权。
每个请求的 `runtime_profile_id/version` 和 timeout/sampling 摘要会进入内部审计元数据；公开报告仍不保存
prompt、响应正文或 reasoning。

没有显式 profile 的路径继续保留旧行为，GLM-5.2 不继承 Flash 参数。生产 `RuntimeExecutionFactory`
本批暂不自动注入 profile，因为它的 `RuntimePolicySnapshot` 仍须与 Skill manifest 的 30 秒策略严格相等；
要把 Flash profile 变成产品运行时默认接缝，下一批必须先设计新的 RuntimePolicy/Trace/Skill 版本合同。
真实 G53-7 领域运行还要求新实现取得 exact-SHA 公共 CI；当前 dirty worktree 只允许 no-I/O preflight，
网络化 runner 会直接拒绝，避免把未提交代码伪装成旧公共 SHA。新运行默认写入独立的
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`，
不会复用旧 G53-4/G53-6 结果路径。由于既有 retry2 协议证据绑定旧代码 SHA，新实现取得公共 CI 后还要
在同一新 SHA 上重新完成 G53-3 协议门；runner 会拒绝把旧协议证据冒充新实现的协议证据。

本批验证：聚焦 profile/domain `98 passed, 27 subtests passed`，额外 runtime/provider 回归
`108 passed, 8 subtests passed`，compileall、`git diff --check` 与 governance 通过；没有真实 API 调用。

## 11. RQ-176：把 Flash 档案接入产品主链

用户随后明确决定不再等待 Pro/Flash 横向比较：产品正常运行目标改为普通智谱 API 的
`zhipu/glm-5.3-flash`，GLM-5.2 只作为显式兼容/应急回退。RQ-176 在 RQ-175 的离线合同之上完成本地产品接线，
不改变 Portal、Account、Broadcast Workbench、Auth、路由或媒体采用状态。

组合路径现在要求同一个已注册 profile 同时绑定 Root、RuntimeExecutionFactory、AgentRuntime、Recent Review
compiler、Agent/工具/Harness、Zhipu Provider、Runtime policy 和 Trace。精确 Flash 如果没有显式 profile，
在组合阶段直接拒绝；这样不会出现 compiler 仍按 Skill 的 30 秒策略编译请求、Runtime 却偷偷采用 90 秒预算的
分裂。GLM-5.2 与测试 double 的无档案路径仍保持兼容，不会悄悄获得 Flash 预算。

产品模板已把 `.env.example` 与 Compose 默认对齐到 Flash；Flash 的 90 秒执行窗、120 秒传输、2048 输出上限、
`temperature=1`、`top_p=0.95`、SDK retries=0 和 Worker 360/60 秒 lease/heartbeat 都由受信代码固定，调用方
不能升权。这里的“产品目标”不等于“生产准入”：新实现仍须自己的 exact-SHA 公共 CI、同 SHA G53-3、独立 G53-7
领域门、完整黄金切片和安全/部署/合规证据；旧 G53-3/G53-4/G53-6 结果不可覆盖。
