# 本站 Chat 候选的离线可行性与验证准备

2026-11-01 建立离线映射包；2026-11-02 推进现有单次执行器接线，最新进展见末节。用户要求在 CI 等待期间同步推进。本包复用现有工具流组装器，检查 Chat 表示能否承载当前产品审查；不改变默认采用、provider 注册、当前合同、旧任务或费用。本站公开端点声明支持该候选，实际兼容仍需真实证据。

## 已完成什么

`scripts/reviewer_chat_contract.py` 是纯请求/分块映射模块，没有客户端构造、凭据参数、网络入口或执行 CLI。数据流为：完整业务请求 → Chat messages/function schema → SDK 分块 → 现有 ProviderStreamAssembler → 原始工具参数 → 既有 product.validate_business。传输/schema 通过不自动触发业务验收或发布。

- 请求保留完整四条消息、角色、工具 schema 和可信用途政策；选择单个工具，申请 high、16384 输出和 usage 尾块。不照搬智谱 thinking/tool_stream 参数，不用 JSON 文本伪装工具调用。
- 复用正式身份、分块工具 ID、参数 JSON、终态、用量和 EOF 检查。仅返回指定工具参数；伴随正文和私有 reasoning 不进入结果。缺失的缓存/推理用量细分保持 unknown，不能补为真实 0。
- 用实际安装的 SDK 2.54.0 和 MockTransport 验证请求序列化与 SSE 解码，测试期间禁用 socket。完整结果、分块、工具/身份冲突、截断、读取中断、缺用量、错误/拒绝、超额、结束后的追加数据均有针对性案例。
- 首次 SDK 正例暴露了 `[DONE]` 后不读取 HTTP 尾部的问题；已有 Responses TailCheckedStream 是通用 SSE 尾部组件，直接复用。没有放宽 EOF 标准：注释尾部允许，追加 data 拒绝，已知用量保留。
- 初轮 39 通过/1 失败，接入现有尾部组件后 42 项通过；当前产品两职责 × initial/fresh 的 4 项绑定/验证额外通过。schema 允许但业务不允许的 needs_revision-without-issues 被原验证器拒绝，改写可信政策的请求被拒绝。

截至 11 月 1 日，该模块尚未接入 owned process、deadline/cancel、实时 usage 落盘、Worker/SQL 或浏览器，也不能让旧任务隐式换传输。后续接线复用这些既有机制；不因离线原型可行就批量改合同、刷新历史材料或声称产品已完成。测试中的 EOF/closed 来自模拟传输观测；纯映射函数本身不认证外部传入的标记。

## 完整请求与资源核对

采用已保存的 attempt-13 第 28 项 intent，只读核对原 SHA，再还原来源/报告，按当前 1.7.3 observed 政策生成两份初审请求。它们仅用于离线测量，原报告、旧意见和账目未改，也未导入诊断意见。结果见 `data/evaluation/results/sol_product_chat_offline_candidate_20261101.json`。

| 项目 | facts | completion |
|---|---:|---:|
| 原有业务估算的输入预留 | 58360 | 53964 |
| 加 16384 输出后的单次预留 | 74744 | 70348 |
| Chat JSON UTF8 字节 | 55405 | 49726 |
| 同内容 Responses JSON UTF8 字节 | 55336 | 49657 |

两接口差异各为 69 字节；消息逐字、schema 和可信上下文往返一致。不能据此推导真实 tokenizer、用量、计费或上游模型相同。

按现有产品估算：历史生成 3 请求/29323 tokens，加双初审 145092、必要双 fresh 最大 160768，形成 **7 请求/335183 tokens** 情景；相对 8/401920 留 1 槽/66737 tokens。新生成、修订后报告大小及实际 Chat 用量尚未测量。将整个 JSON 再当文本测量的压力情景为 357149 tokens；该方法会重复计算序列化开销，Responses 也出现相似增长，因此它不是新增预算规则或 64000 超限证明。

时间更紧：历史生成传输 143.891 秒，加四次历史最慢审查 160.328 秒为 785.203 秒，只剩 114.797 秒处理其余活动；四次均用满 300 秒则为 1343.891 秒，超出默认 900 秒。若其余活动预留 30/60 秒，四次审查平均可用约 181.527/174.027 秒。以上是情景，不保证未来可达，也不是扩大预算的决定。每步的实际剩余量仍由既有 session 预算控制。

## 下一项实证要回答的问题

在选择并完成产品接线前，先用这个离线包明确取证目标；目前不发请求、不请求用户重新授权旧截止。

| 问题 | 有用证据 | 结果对应动作 |
|---|---|---|
| 本站 Sol/企业分组能否承载完整工具请求 | 同一完整业务输入、单工具 schema、high/输出参数的实际请求与返回 | 明确不支持参数/工具则记为路线反证；不自动删参数或退成普通文本 |
| 是否完整返回指定工具 | 真实分块、finish_reason、原始参数、EOF/close 与业务验证 | 格式或来源冲突暂停该步骤；不得现场不断改解析再付费 |
| 失败是否仍有用量 | 成功尾块、错误/中断时已有 usage 与请求归属 | 已知量保留，缺失量保持 unknown 预留，不能当零费用 |
| 能否完成产品任务 | 全程真实时延/消耗、双审、唯一应用、同稿双 fresh 与最终全文核验 | 一次通道成功仅支持继续该任务，不能作为稳定率或日常准入 |

申请 high/输出上限以及回显不冲突，都不能认证网关实际上游配置。实际收款与 Token 用量也分开报告。无需用户去找管理员；公开声明和群助手答复只用于形成待验证假设。

## 收口与后续

11 月 1 日包到离线映射、正反例、当前业务验证复用和上述资源清单为止，不扩成第二套运行框架。当时下一行动是处理 CI 并选择后续接线，现已推进至下节。现有 P2 其他产品能力与后续 P3/P4 保持，不把候选原型当作默认采用。旧授权已到期，本包没有模型 HTTP、真实凭据读取、恢复或发布。

本包编译、治理、diff、JSON、原件摘要与预算算术检查通过。旧产品源码/合同/Runtime指纹未改，未重复既有SQL/浏览器或历史15例测试。

## 2026-11-02：选择 Chat 候选，接入既有单次执行机制

基线4ca90c6b的CI41297485491八项全绿，SQL315项通过（692.68秒）；上一包工程修正收口。本包选择Chat作为下一条取证候选：其完整消息/工具映射与实际SDK分块已有离线证据，本站公开声明曾列出该入口；继续猜Responses未知事件仍缺原始类型/内容。此为后续工程与取证路线选择，不是本站Chat已真实通过或默认采用决定。

目标是补齐候选的单请求执行链：完整业务请求→现有owned subprocess→Chat SDK流→增量工具组装/即时usage落盘→原业务验证→现有receipt。复用原超时、取消、一次性目录、尾部EOF及用量观测；不新建进程/任务框架。生产profile/业务合同仍使用Responses，旧task/run不得隐式换传输。

验证覆盖正常两职责initial/fresh、可信上下文拒绝、HTTP/截断/关闭错误、usage后卡住、启动/读取/关闭期限与取消、同目录拒绝重发、已知/未知/未发送账目和私密内容不落诊断。模型使用替身、socket阻断；本包不需要新模型费用。共用process变动后检查原Responses消费、Runtime指纹和当前资格清单，历史快照不改。完成后固定取证入口与完整请求材料，明确剩余Worker/SQL/页面接线及真实支持缺口；不以单次传输成功替代P2/P3完整产品验收。

### 接线与检查边界

现有 `reviewer_responses_process.run_once` 增加显式模式 `natural-sol-product-chat-candidate-v1`，调用 `reviewer_chat_stream.collect`；父、子进程均验证当前 product 业务上下文及原企业分组 profile。默认模式、`app/product/sol_contract.py` 和现有 provider 注册均不改。凭据仍由调用方经 stdin 显式传入，本模块不发现或读取真实凭据。

纯映射改为增量 Decoder：收到 usage 即通过原 create-only 写入器落盘；发现冲突另存两份用量，取消/期限杀进程后仍保留 unknown 判定。已知用量在格式拒绝、读取/关闭失败后保留。SDK 的 DONE 后仍核 HTTP 尾部，实际 EOF/close 由原观测器负责，工具 schema 后还有原产品业务验证。

候选 68 项检查通过（原 46 项加 22 项进程检查）。第一次进程检查 15 通过/7 失败：一项凭据测试使用了 schema 不允许字段、一项期待错误码与原组装器不同、四项把立即取消前未持久的发送次数误断为 1，均修正测试；另一个 close 错误在 SDK 迭代内部触发，transport 现保留观测到的 close_failed 类别。初始日志保留，没有真实调用。立即取消后的实际 HTTP 次数允许未知，绝不凭旧采样零值认定没发出。

另以原 intent 的完整来源/报告派生两职责请求，实际 owned process + SDK + MockTransport 执行通过，与上一包两份 business/wire 摘要完全一致。回执/可信上下文已保存；每份模拟 usage=20 只是夹具值，不参与真实预算估算。合成 pass 不裁决历史报告中的错误，不导入旧意见、不发布、不恢复任务。外置证据为 `outputs/riftcoach-product-chat-process-20261102/complete-inputs-result.json`；离线核对脚本保留以便复现。首次读取使用了当前 metadata key，而原 intent 使用历史 `sol_review_validation`；改为对应历史还原函数后再施加当前 observed 政策，摘要吻合。首次本地键错误发生在进程/网络前。

### 下一项产品接线的明确范围

下一包完成一个显式 opt-in 的 Chat 产品合同/任务绑定，复用现有 `SolReviewProvider`、`ProductWorkflow`、`CandidateSession` 和 Worker；同一 task 的合同/传输指纹冻结后不得在 resume 中悄然切换。当前 `selected_contract` 白名单、`SolReviewProvider` 的 profile/receipt API 核对和格式恢复分类、`contract_for_worker_profile`、SQL binding 都是实际消费者，不能只替换 URL。此包尚未修改这些消费者。

最便宜且有区分力的验证是让 Chat SDK 替身通过上述真实消费者：直接双审通过；修订分支唯一 application 且两项 fresh 同稿；取消/期限/协议失败保留已知或未知费用，普通 resume 不重发失败步骤；既有 SQL/API/浏览器正确展示暂停与报告，未发布稿不可读。只补 Chat 接线与共享行为覆盖，原 15 和未变功能不重测。通过后再固定完整 P3 取证包：代表性完整输入、观测/去留条件、整任务预算和具体执行入口；真实通道与时延仍需要单独证据，本轮没有发起付费。

收口：原Responses supervisor/恢复/资格清单/产品合同85项全部通过（415.12秒），与候选68项合计153项。11个Runtime和2份当前清单通过；4个manifest仅共享process源码指纹及program摘要变化，sol-review清单create-only更新，历史请求/标签/合同保持。编译通过。本包验证材料见 `data/evaluation/results/sol_product_chat_process_candidate_20261102.json`。
