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

## 12. RQ-178：为什么要把实现提交 A 和证据提交 B 分开

### 要解决的具体问题

G53-3 会在某个已经冻结的实现提交上真实调用模型。调用结束后，脱敏 JSON 通常要再提交进仓库；这个新提交
的 `HEAD` 已经变了。如果门禁把“当前 HEAD”同时当成“协议执行代码”，就会把证据提交 B 错认成执行提交，或
逼着我们修改结果里的 SHA 来追上 B，形成不可审计的循环。

### 代码地图与数据流

- `app/evaluation/glm53_domain_gate.py` 的 `GLM53ABIdentityBinding` 保存 A、B、两次 CI 运行号、协议 `code_sha`
  和 canonical 结果摘要。
- `build_glm53_ab_identity_binding` 只做本地检查：读 B 的 Git blob，校验脱敏三调用合同；检查 B 是 A 的直接
  单父提交且只新增 capability-result 白名单文件（不允许改写既有结果）；再比较当前工作文件与 B blob 的 LF 规范摘要。
- `build_glm53_preflight` 将通过的绑定嵌入 schema 1.1 admission；旧 schema 1.0 结果在摘要时省略新增的空字段，
  所以历史 G53-4/G53-6 仍能读取，但不会被新身份复用。
- CLI 的真实领域路径必须显式提供 A 的实现 SHA/CI 运行号和 B 的证据 SHA/CI 运行号；缺任何一项时在读取 `.env`
  或构造 Provider 之前停止。

可以把控制流记成：`A 的代码 → G53-3 结果(code_sha=A) → 只新增证据的 B → HEAD=B 的无 I/O 预检 → 才有资格构造 Provider`。
CI 运行号是已核对的外部见证，不在这个本地函数里联网查询；这不会把“本地预检”夸大成公共生产准入。

### 测试如何证明边界

`tests/test_glm53_identity_binding.py` 覆盖 A/B 分离、真实 Git 父子与 blob、旧协议错配、摘要篡改、路径穿越/代码
混入、当前 HEAD 错配、缺身份 CLI 和 Provider 构造前停止；配合既有 gate/runtime 回归，当前聚焦为 `53 passed`（身份绑定文件
`18 passed`）。生产入口不接受可注入的 diff reader，证据路径始终由 Git 的 A→B 差异读取。
这里的 `1fda…` 是提交 Git blob 的 canonical LF 摘要；Windows 工作副本因 CRLF 得到的 `6c6e…` 只用于解释环境
差异，不能填入准入绑定。

### 这一步没有解决什么

本批随后按 RQ-180 在 A/B 证据链完成后执行了一次 G53-7 真实领域尝试：协议 3/3、领域 2/12，首例以
`provider_response_invalid/incomplete_chat_response` 停止，后两例跳过，`admitted=false`。这不表示领域采用、
生产成熟度或 Stage 8 完成；底层 vendor finish reason 未保留，不能进一步断言为 `length`。结果由本地 C=`9157cde…`
承载且未推送/未取得公共 CI。Portal、Account、Workbench、Auth、默认模型和 `production_media=0` 均不变。

### 面试时的安全表述

“我把实现身份和证据身份拆成 A/B 两个提交：协议结果内部永远指向执行代码 A，B 只承载脱敏证据。门禁在本地
读取 B 的不可变 blob、检查直接父子关系和文件摘要，并在缺 CI 见证或工作树不一致时 fail closed；这证明的是证据链
完整，不是把一次本地领域实验包装成生产上线。”

## 13. RQ-179：为什么公共 CI 必须拿到 Git 历史

RQ-178 的测试最初只在本机完整仓库通过。代码提交后出现两层红灯：第一层是历史 fixture 把旧证据 B 当成了
任意新 checkout 的当前 HEAD；第二层是 Actions 默认浅克隆只有最新提交，无法执行历史 A→B 的 `merge-base`、
blob 与 diff 检查。修复没有放宽生产规则：测试只为旧 A/B 样例替换私有 HEAD reader，公共 CI 则获取完整 Git 历史。

最终实现 A 是 `9e6d78be51c3a5c512b67f83d2849f9b1261cf77`，Actions run `33378687984` 三 job 全绿；
`fe7d577…` 和 `3ccd827…` 的失败 runs 保留为验证环境故障证据。随后在 A/B 证据链上按 RQ-180 执行一次 G53-7，
结果 SHA=`21e664d…`、`admitted=false`；这个公共 CI 仍只证明身份校验可复现，不证明领域或生产准入。当前不自动重试，
若继续须另立版本化 Flash 响应完成/截断诊断。

## 14. RQ-180：一次有界领域尝试为何停止

G53-7 使用已完成 A/B 见证的干净 LF checkout，只运行一次，协议 3/3、领域 2/12、累计 5/15 calls，领域 3505
tokens。首例 `flash_gate_baseline_01` 的两次 Provider 请求没有形成可用的完整响应，适配器因此只暴露脱敏的
`provider_response_invalid` / `incomplete_chat_response`；Agent 状态为 failed/degraded，后两例按首错停止跳过，
最终 `admitted=false`。这是当前运行链的响应完整性失败，不是 G53-3 的认证失败，也不能推出模型一般质量结论。

结果文件 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`
的 canonical-LF SHA-256 为 `21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment 为
`236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；本地 C=`9157cde…` 仅承载脱敏结果，未推送且
没有公共 CI。为避免敏感信息和误判，底层 vendor finish reason、Key、Prompt、响应正文和 reasoning 都没有持久化，
所以不能把 `incomplete_chat_response` 进一步解释为 `length`。当前停止自动重试；若要继续，必须另建版本化的
响应完成/截断诊断并重新取得授权。Stage 8/8E 仍 `in_progress`，`production_media=0`，旧结果和产品前端边界不变。

## 15. RQ-181：把“响应不完整”拆成可学习的失败路径

RQ-180 的领域尝试只暴露了 `provider_response_invalid/incomplete_chat_response`，所以不能仅凭聚合码判断是
网络、权限还是输出截断。用户授权后，我们在独立工作树对同一个冻结首例做了一次正文零留存诊断，不重跑旧领域门。
诊断结果记录了适配器已经看到、但不会泄露内容的状态字段：

- `finish_reason=length`；
- `input_tokens=2220`，`output_tokens=2048`，Usage 结构有效；
- `content_state=empty`，`reasoning_content_state=non_empty`，ToolCall 为 `0`；
- 适配器在结束原因校验处返回 `incomplete_chat_response`，所以 normalized/settled 都是 `0/1`，Agent 状态为
  `failed/provider_error`。

这说明在本案例里，`enabled/max/clear_thinking=false` 的最大推理档案先把受控的 2048 输出额度用在了 reasoning，
还没生成可交付正文就被供应商以 `length` 结束。它不是“把 reasoning 当答案”的理由，也不能把 RQ-180 的旧第二回合
追溯成同样原因；一次观察也不能证明模型一般质量或账号不可用。

脱敏结果文件为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`，
canonical-LF SHA-256=`050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`；它不含 Prompt、正文、
reasoning、Key、请求 ID 或工具参数。当前教学结论是：先把“响应完成策略”做成版本化合同，再用离线 TDD 固定预算、
截断、继续请求和 fail-closed 行为；在此之前不静默提高全局上限、不自动重试、不把一次诊断写成 G53-7 或生产准入。
