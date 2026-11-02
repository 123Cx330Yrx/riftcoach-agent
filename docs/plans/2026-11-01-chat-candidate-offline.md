# 本站 Chat 候选的离线可行性与验证准备

2026-11-01 建立离线映射包；2026-11-02 已推进至显式 Chat 产品合同及持久任务接线，最新进展见末节。用户要求在 CI 等待期间同步推进。本包复用现有工具流组装器，检查 Chat 表示能否承载当前产品审查；保持默认采用及原 Responses 合同；新增显式 Chat 合同，旧任务和费用不改。本站公开端点声明支持该候选，实际兼容仍需真实证据。

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

### 上一包约定的产品接线范围（本包结果见下）

下一包完成一个显式 opt-in 的 Chat 产品合同/任务绑定，复用现有 `SolReviewProvider`、`ProductWorkflow`、`CandidateSession` 和 Worker；同一 task 的合同/传输指纹冻结后不得在 resume 中悄然切换。当前 `selected_contract` 白名单、`SolReviewProvider` 的 profile/receipt API 核对和格式恢复分类、`contract_for_worker_profile`、SQL binding 都是实际消费者，不能只替换 URL。此包尚未修改这些消费者。

最便宜且有区分力的验证是让 Chat SDK 替身通过上述真实消费者：直接双审通过；修订分支唯一 application 且两项 fresh 同稿；取消/期限/协议失败保留已知或未知费用，普通 resume 不重发失败步骤；既有 SQL/API/浏览器正确展示暂停与报告，未发布稿不可读。只补 Chat 接线与共享行为覆盖，原 15 和未变功能不重测。通过后再固定完整 P3 取证包：代表性完整输入、观测/去留条件、整任务预算和具体执行入口；真实通道与时延仍需要单独证据，本轮没有发起付费。

收口：原Responses supervisor/恢复/资格清单/产品合同85项全部通过（415.12秒），与候选68项合计153项。11个Runtime和2份当前清单通过；4个manifest仅共享process源码指纹及program摘要变化，sol-review清单create-only更新，历史请求/标签/合同保持。编译通过。本包验证材料见 `data/evaluation/results/sol_product_chat_process_candidate_20261102.json`。


## 2026-11-02 当前工作包：Chat 的持久产品链

起点8a838c58，CI41375428589八项success。目标是让显式选择的Chat产品任务沿既有Worker/SQL/报告页面完成和恢复；生产默认legacy及既有Responses配置保持。没有新增框架或 paid attempt。新合同/worker profile独立冻结，business、来源、用途、默认8/401920/900及发布规则复用现有产品；旧task不迁移、不清账。

实施路径：独立sol_chat_contract → 现有factory/owned process/Chat SDK → 同一ProductWorkflow与CandidateSession → SQL绑定及run_query → 现有浏览器。最初核对发现除provider外还有版本Literal、PromptProgram resolver与费用归属的API证据消费；这些实际消费者一并接线。首轮启动9项被resolver未注册拒绝、1项合同检查通过，零真实请求；修正分派后再做行为验证，不放宽指纹核对。

验收：两职责直接通过；一次修订且双fresh绑定同稿；错误身份/工具/业务拒绝；格式和超时暂停、普通resume零新增发送、明确retry保留前缀/累计费用；显式配置与任务绑定不能互换；实际SQL/API/浏览器覆盖恢复和取消。SQL仅隔离库、模型由socket阻断的SDK替身提供。旧特殊budget/manual补充仍限原合同，不移植为Chat授权。完整新P3取证方案在这些消费验证后形成，真实支持与语义质量仍未验收。

本地完成：68项Chat传输、14项新产品、13项配置/资格清单、60项共享Responses/产品、11项真实SQL/API/Worker、3条真实浏览器及8项页面检查通过；12个Runtime/2份当前清单、typecheck/编译通过。浏览器实际1440/320覆盖继续、手动重试、取消：每条只建一个SQL任务、来源只读取一次；成功时一条assistant turn，取消时零条，observed均无Training事件。普通resume不重购失败；524后手动重试成功仍保留unknown预留。真实模型/凭据0。

修正与局限：resolver注册后，真实RuntimeTrace还需识别独立Chat角色合同；完整失败流程验证暴露了这一遗漏。Chat空HTTP超时观测不能因字典非空就被误判为已收到结构错误；现在仅按明确无响应/超时类别判断。前端恢复白名单补入新profile。测试中的`candidate`误写与过早取消时身份尚未落盘的假设已修正；后者没有放宽账目规则，可信身份不足仍unknown。先前失败日志保留，按受影响用例复核，没有重跑不相关全套。9个旧manifest只同步共享源码/派生program指纹，两份资格清单create-only更新且原15业务字段逐字保持。

用户追加Docker报错：旧4.90.0正常重启后仍遇残留socket不可访问，新建独立空socket也复现关闭后重命名失败。桌面/开始菜单现用有限启动兼容脚本，仅Docker完全停止且目录只含已知零字节socket时保留并移开两个临时目录；三次启动及容器检查通过。没有重置镜像/卷/WSL/业务库，无驻留监控器。底层原因未确认，原exe/CLI/应用内restart绕过该入口，安装升级也可能覆盖快捷方式；不是永久修复承诺。旧socket备份保留，删除备份及写独立Docker汇总说明分别被自动审批策略拦截，未绕过。临时测试容器已清理。

结果为 `data/evaluation/results/sol_product_chat_integration_20261102.json`，完整日志/浏览器证明及Docker启动记录在 `outputs/riftcoach-product-chat-integration-20261102`。本包一次合并提交推送并核新CI；下一步仍是下面的P3决定与实际验证，不新增候选路线。


### P3 具体执行方案（准备，不是付费授权）

本包复用正常入口；不再单独购买一份难以转入产品的诊断意见。候选执行目标为 **一个新建的 observed 近期五场复盘任务**：通过现有 Player/Conversation 的普通入口，冻结该次来源、Memory 和可信用途；Flash 生成、Sol 双初审，必要时唯一修订及同稿双 fresh，最后沿 Evidence/Report API 和浏览器消费。这是新的产品取证任务，不能复制旧成功回执冒充新成功，也不改变或扣减旧 attempt-13 的成本账。

准备好的选择与入口：

- Worker 选择 `RIFTCOACH_WORKER_EXECUTION_PROFILE=sol-dual-product-chat-v1`；生成仍为 `glm-5.3-flash`，审查仍申请原企业分组 Sol/high，改用 Chat 工具流。API 选择 `RIFTCOACH_TASK_PUBLICATION_MODE=evidence_bound_v1`。用户界面不暴露协议选择。
- 任务通过 `POST /conversations/{conversation_id}/reviews/recent` 创建，body 为 `{"count":5,"queue":420,"focus":"overall"}`，实际 owner/conversation 必须由正常绑定取得，不能把占位符作为现成身份。
- 使用正常 `python -m scripts.run_review_worker --worker-id chat-product-validation --check` 构造预检，随后同一配置 `--once` 消费一个限定任务。预检会读取明确配置的凭据，但不请求模型；本轮未运行有真实凭据的预检。实际执行前固定新干净 HEAD、同 HEAD 全部必需 CI 检查通过（含 SQL 分片及汇总）及隔离队列，防止领取无关任务。
- 首次执行把合同、用途、来源和 run 绑定持久化；重启后只读回放成功前缀。恢复继续使用正常 resume API，checkpoint 必须取实际最新值；不直接改 SQL/报告/会话账目。

默认整任务上限仍 **8 次 / 401920 tokens / 900 活动秒**，单次最多300秒、16384输出；两次手动重试也占这8槽，本取证方案不自动使用重试。已有材料的7次/335183 tokens只是情景估算；全程时间可能不够，预算暂停也是有效结果，不能现场延时或只为得到成功追加调用。实际日期、明确费用范围、执行对象和凭据读取须在新决定中绑定，旧授权不能复用。

验收记录应同时回答：完整实际wire和来源是否一致；流是否完整、用量及未知量是否可对账；双职责有没有覆盖实质问题；唯一修订和两fresh是否同稿；报告数值、用途和来源能否逐项核实；普通页面刷新/恢复/取消是否不重购成功步骤。模型pass仅为流程输入，不替代这次独立内容核验。全部成立只记一个代表性闭环，后续新案例与日常采用仍按总计划P5。

若遇接口参数/工具不支持、身份或用量矛盾、格式/业务失败，保存完整可公开回执和安全事件证据，停当前步骤；先离线判定，不自动第二次、不猜私有协议、不导入旧诊断。若预算不足，保留进度并明示剩余工作；若通道成功但报告有实质错误，继续考察现有修订覆盖，不能以HTTP200提前发布。需要新的付费决定时，提交上述具体范围和已完成工程证据。


### 2026-11-02 CI收口：SQL完整分片

产品接线已在e84e3a3e推送。CI41402912392的postgres-migrations超过20分钟取消：迁移成功，测试至少288项通过并到88%，未见断言失败；旧日志不能识别最后一项，因此不把超时说成已证业务回归或测试死锁。

本次只修CI执行安排：原51文件/326项逐字清单保留，复用现有四片工具，每片独立数据库；原postgres-migrations仍执行迁移往返和metadata，并汇总同HEAD完整终态，任何失败/漏跑/重复/SQL跳过都不通过。上限仍20分钟，其他jobs保持；未来验收用全部必需检查（当前12任务）。

17项工具检查、326项真实SQL四片（82/82/81/81，390.50/479.95/425.20/452.48秒）及真实迁移往返/metadata通过。实际CLI汇总326/326、零跳过；专属测试容器已清理。业务源码、旧原件和费用不改，模型HTTP/真实Key读取0。结果sol_product_chat_sql_ci_sharding_20261102.json保留基线HEAD及候选文件SHA；新提交远端CI仍待验证，不能用本地耗时保证远端。当前下一步为一次合并提交推送并核新CI；之后仍沿既定P3，不新增诊断路线或付费尝试。
