# 本站 Chat 候选的离线可行性与验证准备

2026-11-01 建立离线映射包；2026-11-03 同一P3任务已完成正式四审查与正常产品消费，仍有产品收口项，终局和当前行动见末节。用户要求在 CI 等待期间同步推进。本包复用现有工具流组装器，检查 Chat 表示能否承载当前产品审查；保持默认采用及原 Responses 合同；新增显式 Chat 合同，旧任务和费用不改。本站公开端点声明是最初候选依据，本次真实兼容证据限于下述实际任务，不推广为所有场景已验收。

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


### 2026-11-02 SQL远端验证与遗漏消费者修正

ed1ad9c0 / CI41407947133已终局：SQL326项分片和迁移汇总均成功，零跳过，最慢356.92秒；Web、打包及另外三片pytest成功。片2只失败1条packaging契约断言，仍读取旧job内联SQL文件；pytest汇总因此失败。上一轮消费者检索范围遗漏该文件，不能把它说成业务或中转故障。

本地复现后仅修正该断言，检查迁移依赖/分片入口/实际清单中的原五项必测文件。全仓直接workflow消费者三个文件共28项通过，业务源码/CI工作流/SQL清单不动，旧成功证据复用，不重复SQL/浏览器。结果sol_product_chat_ci_contract_followup_20261102.json。下一动作合并提交推送该测试修正，核新HEAD全必需CI；当前无付费、旧任务恢复或Docker操作。


### 2026-11-02 P3工作卡：CI收口与单任务启动准备

**目标与当前证据。** 0a99c28a9594a012cc8e72ff5bbe68c72d358f4e / CI41430754834的12项检查全部success。固定执行目录`D:/riftcoach-chat-product-validation-execution-20261102`干净且同HEAD；Python为`D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`。这次正常API、PlayerLink Worker及Review Worker的实际`--check`已通过独立Postgres，迁移0015，任务/会话表均0；Chat合同1.7.4摘要07249021…与冻结模块一致。预检使用明确假凭据，全部模型/玩家API拦截，未加载真实.env。它证明部署依赖能组装，不证明真实凭据或上游可用。

首轮预检的worker_dependency_invalid来自操作者把公共字典联网也拦住：原异常链定位到DataDragonService._get_json。仅预先读取五份无需密钥的官方静态数据、保留URL/摘要后，同一预检脚本通过；未修改产品代码或放宽模型限制。启动字典16.21.1不得冒充比赛版本。该次临时空数据库容器已清理；Docker从已停状态经既有兼容入口启动，底层问题的既有局限保持。

**具体范围。** 一次新建`DK ShowMaker#KR1`、asia、observed任务；正常近期复盘body为`count=5, queue=420, focus=overall`。正式运行时重新解析官方身份、抓取当时最新可用来源，保存真实比赛日期/版本/有效数量；若发生队列回退或不足五场，必须显式记录，不能宣称五场单排验收成立。既有ShowMaker只是选定对象依据，旧报告/意见/成功回执不导入。observed只做观摩结论，不向阅读者派发个人训练任务。

**资源与时间。** 一个任务最多8次模型HTTP、401920tokens（含unknown预留）、900活动秒，每次300秒/16384输出；拟由新明确确认起24小时有效。成功路径允许生成→双初审→必要时唯一应用与同稿双fresh，不自动重买失败或另开第二个任务。历史7请求/335183tokens仅为情景；当前公开计价查询未成功，不承诺人民币金额或900秒足够。现有Riot、Flash和Sol凭据只在该新决定涵盖后读取，旧已到期许可不复用。

**正常入口执行顺序。** 复用现有应用，不写第二套评测/恢复driver：

1. 核冻结HEAD、绑定、同HEAD已终局CI；检查没有本次执行者/claim。建立本次独立空数据库与runs根，迁移head，队列全局/owner并发上限1，API为local/evidence_bound_v1。未来正式库不从此次预检空库或任何旧任务dump恢复。
2. 明确配置Chat Worker profile及凭据，沿现有两类Worker的`--check`预检。以`POST /player-links`发上述observed绑定，再由普通PlayerLink Worker `--once`解析；从真实返回取得relationship/player_profile_id，不预造PUUID或task/run身份。
3. `POST /conversations`创建该profile的会话，再`POST /conversations/{conversation_id}/reviews/recent`提交上述body；保存真实返回的task_id。每次写入使用该任务的稳定Idempotency-Key，遇到客户端不确定不得换Key重复创建。
4. 同配置运行`python -m scripts.run_review_worker --worker-id chat-product-validation --once`。成功边界按现有会话逻辑推进；错误/预算暂停保存最新checkpoint、完整回执和数据库，不改SQL来放行，不自动点击手动重试。
5. 实读实际请求、完整来源、报告、两职责意见、修订应用和fresh；逐项核数值/舍入、版本和用途、事实与推断边界。检查HTTP/known/unknown/receiptless/未发明细；有修订时要求唯一应用与两fresh同稿。模型pass或Worker succeeded不替代独立全文验收，严重内容错误不能记通过。
6. 核`/tasks/{task_id}/continuation`及`/runs/{run_id}/report|evidence|usage`，用1440/320实际浏览器验收正常展示、来源/费用和刷新不触发重复付费；拒绝/暂停稿不可被当作已通过报告。保存可恢复快照及真实终态，清理本次进程和容器。只记一个代表性闭环，不升级默认准入或宣称全部产品完成。

**尚未完成与失败决定。** 当前没有真实官方玩家解析、当前样本、模型鉴权/调用、实际内容/时延验收。出现通道或语义失败先保留证据、离线判定，只停受影响付费步骤；不猜事件、不不断改解析后再买、不追加授权上限。独立本地修复可继续。该新任务费用决定是下一行动；在此之前不启动paid worker、waiter或monitor。

结果与具体提案：`data/evaluation/results/sol_product_chat_p3_prepared_20261102.json`；外置Control `C:/Users/33502/Documents/Agent/outputs/riftcoach-chat-product-validation-20261102`中binding、decision-ready、environment-readiness、公共字典请求、首次错误链及cleanup齐全。decision-ready明确authorized=false。当前仅更新记录，不修改已全绿0a99c28a执行源码，不为记录提交重新等待同一业务CI。


### 2026-11-03 P3实际结果与局部修复

新授权“确认继续”后，以已绿0a99c28a从普通API/Worker执行一次ShowMaker observed任务。Riot实际新取5场queue420，比赛为10月13—15日/16.20；3次Flash成功、29849 tokens/61.047活动秒、unknown/retry/receiptless为0。草稿标题“训练计划（观摩性质）”被报告识别器误判缺节，业务拒绝且未进入Sol；原manifest保存report_missing_headings，同原稿/冻结guard离线复现。

开发树只修完整括号限定语识别，保留正文和真假标题边界；111项章节/补丁/fresh/发布消费检查及12Runtime/2清单通过。实际桌面/手机只读验收拒绝稿不可见、费用一致、刷新不新发；SQL assistant/Training均0。102原件及最新DB已做103项ZIP逐字核验，容器/进程已清理，原件/授权未改。

账目实读发现启动预检遗漏：方案承诺每次16384输出，Flash实际配置32768；三次实际输出327/115/2327未超，但请求上限不能记合规。外置只读scope检查正确拒绝该配置，不改历史合同来掩盖。后续新发送必须直接核实际请求和角色边界。

内容也未通过全文验收：混合位置的输局均值不能支撑所有输局“发育塌陷”，两个中路负局CS均值7.695反高于中路胜局7.56；已用静态名称映射与缺失历史版本证据需要区分。本地分析不作为审查意见导入。闭环仍缺首审/修订/fresh/发布；session closed，历史恢复器不适用。下一包先做同任务保留前缀恢复与零发送边界验证，不重买生成，不自动追加付费。结果sol_product_chat_p3_draft_rejected_20261103.json。

### 2026-11-03 同任务草稿拒绝恢复准备完成

2026-11-03，按用户“继续”完成同一P3任务的标题误拒绝恢复准备；未新增真实模型或来源请求。开发树仍为`D:/riftcoach-review-route-diagnostics` / `codex/reviewer-route-diagnostics`。P1_complete / P2_partial_verified / P3_not_accepted，Stage8E、原15完成和默认准入不变。

标题修复afe24661 / CI41486674481十二项全绿已核，不再轮询。新增窄范围create-only恢复，仅接受Chat、report_missing_headings、首审前完整成功生成前缀，并核原终态/trace/全部回执和当前标题结构。102父原件、12项操作、3次生成和原拒绝完整归档，父目录/最新父DB不改。SQL沿现有恢复事务保留失败事件、绑定新Evidence refresh_id；随后普通resume（manual_retry=false）与Worker回放，不删除terminal或重开任务。

实际原任务`04c9a865-db03-4edb-af9e-70cb8d719db0` / `review_ee91ab480ecf4c4992f82ec08cc4bbf4`从最新fb970618…DB恢复并零发送到facts-initial：3HTTP/29849known、unknown/receiptless/retry/未决均0，活动62.078秒。5场原来源和草稿逐字保留，source/model/真实Key读取均0。仍1任务/1会话、assistant/Training均0，旧拒绝证据快照保留，报告仍未发布。正式审查/应用/fresh仍0，实际内容问题未验收，也未导入本地诊断意见。

新request guard在发送意图写入前核实际待发送请求：只允许review，max_tokens<=16384、timeout<=300；历史生成32768配置违规保留，只能回放不能新发。实际首审待发请求预留78924（62540输入上界+16384输出），这只是待发请求摘要而非已发送HTTP。总上限8HTTP/401920含unknown/900活动秒不变；余5槽/372071tokens/837.922秒。

最新runs_root=`D:/rc-chat-guard-recovery-20261103/verified-runs`；checkpoint0004 SHA a7f34dc7deed3f4a6757ece025a608eae4230d3d7a9a68a641f4754585d351b8。Control=`C:/Users/33502/Documents/Agent/outputs/riftcoach-chat-guard-recovery-20261103`，`recovered-db.dump` SHA8e720688c06832f23c71c97a6eafce9039ab9ec659130b7b2c6986df9ef38076；恢复proof SHA06fcf4b902db3ad481a69802ff3e636f5d918736de30a60d5354c62ab5244f9c。64项恢复ZIP逐项/CRC已核；其内父归档包含102原件。未来必须采用这些最新材料，不退回父DB或原closed session。

本包验证覆盖47项SQL恢复（旧36、新11）、38项Chat产品/绑定及12Runtime/2当前清单；真实模型均为替身。测试曾与源码编辑重叠造成指纹漂移，已固定源码后逐项复核；一次read_error用量断言未稳定复现，原因未证，不归咎上游；取消用例改用正常服务修正错误的SQL形状。详细结果`data/evaluation/results/sol_product_chat_draft_recovery_prepared_20261103.json`。本包已提交a7045106并推送，新CI41558836855进行中；旧绿CI不代替它。

当前授权与下一行动：用户最新明确“确认并且开个任务等”，已批准Control/decision-ready.json的同任务续接方案；新增create-only continuation-authorization.json（SHA3f4d5ef8be4e1d45c1c136c4b0c9003957e290da9ede1c1249bb0595e14aa65e）绑定原提案和execution-binding，旧authorized=false准备记录保留。开发提交a70451060c9d0f5201bd0b154b96a85f2567c9ef已推送，冻结执行D:/riftcoach-chat-guard-recovery-execution-20261103；CI41558836855最新实查7项通过、4个pytest分片运行、聚合项待生成，需全部12项同HEAD成功。已创建本聊天heartbeat riftcoach-ci，每5分钟检查；无付费driver/新请求。全绿后在原预算8HTTP/401920tokens含unknown/900活动秒、每次300秒/16384输出及北京11月4日00:30:06截止内，普通resume且manual_retry=false，最多新增4次review（双初审及必要同稿双fresh），不重发生成、不新任务、不自动付费重试。先核唯一执行claim/实际进程与最新DB/checkpoint；执行结果经全文、账目、浏览器和恢复快照核验后收尾。新确认已满足本提案授权条件，无需重复询问；P3仍未验收，默认准入不变。

等待期间已准备外置run_review_segment.py：复用正常SQL resume/Worker，每段只允许1个新审查，按实际请求校验后惰性读取Sol Key；源请求和生成禁发。实际持锁只读预检及8个范围负例通过，真实Key/模型0；尚未执行该外置driver的实际Worker路径。runner-ready.json固定脚本SHA0a7e45ec3f9eab9f61f68e0613a0ead7e18a7e2926584daf461f05b05e5d4095。监控已更新启动、段间全文验收和最新DB/快照/只读浏览器收尾路径，CI仍待全绿。

### 2026-11-03 当前结果：四审查及产品消费完成

a7045106 / CI41558836855十二项全绿，授权的4个新review均已完成：facts初审94/needs_revision提出2项有依据的修订，completion初审100/pass；唯一application后两项fresh对相同修订稿100/pass。事实fresh的表格精度提醒仅advisory，不引发另一轮。修订为原始均值差2.75的口径及15分钟指标缺基线的说明，未导入本地诊断意见。完整请求/来源/报告/意见/回执均实读。报告e714e552…在隔离验证任务内published，SQL1任务/1会话/1条assistant、Training0，API和1440/320浏览器消费一致。

本节更正上面历史P3结果中的过强判断：原稿已经说明混合位置、非逐局一致和非因果，不能把它转述为所有输局都塌陷。国服称呼也不能按官方名字面完全一致来验：米利奥/米利欧是否通用别名尚未证，当前没有认错英雄的证据。原报告与失败材料不回写；独立审计的名称结论由Control/player-language-inspection-addendum.json追加更正。

累计7HTTP/100656known/243.406活动秒，unknown/receiptless/retry/未决0；本次4HTTP/70807tokens，4次真实review守16384/300。保留原102文件/12操作/3成功生成及其32768请求配置违规。最新checkpoint0039、DB5b98b57c…和恢复ZIP38b92f59…的219项已核；inspection完成，driver/API/web/container清理，monitor删除，无待观察工作。原最多4次新审查许可用完，余1个总槽不授权下一请求；原截止不延长。P3未全量验收，Stage8E/旧15/默认准入不变。完整摘要和pin见`data/evaluation/results/sol_product_chat_review_continuation_completed_20261103.json`。

### 下一离线工作卡：让当前报告按玩家熟悉的称呼与口吻呈现

**目标与依据。** 落实早期国服称呼与2026-10-30玩家表达要求，以及用户本轮再确认；用本次完整来源/报告作为只读参照，把实际生成、审查、页面消费对齐。达到玩家能认出英雄装备、看懂重点和行动、核查依据的质量，不改变事实和本人/观摩关系。

**起点与差距。** 旧TerminologyStore/name_naturalizer已有ID与confirmed术语机制，当前Worker未接入，词库不是全量；稿中仍有位置代码和重复限定语。SafeMarkdown只渲染转义纯文本，标题/表格不可结构化阅读。来源应区分已用静态名称映射与缺失历史外部比较材料。当前工作不重新解释全部历史试验，不因名称风格另设付费门槛。

**实施路径与取舍。** 先沿Worker→生成数据/提示→正式双审→CoachBrief/SafeMarkdown核当前消费者；复用现有ID/官方名/自然称呼分离机制，避免新造平行词库或强制全量外号替换。约定常用名优先、歧义/未知名回退与版本绑定；在生成输入与要求里提供自然称呼和简短教练表达，审查基于同一映射/来源判断实体，不能把合理别名误判为错误。前端按原文安全排版，不生成第二份未审展示稿。先用真实报告的局部离线示例说明预期，不直接改已发布原件。

**相称验证与验收。** 检查既有常用名/简称、未知名、歧义名、改名/版本不符的代表用例；ID、数值、来源和用户关系保持。用当前完整稿核重点、证据和行动是否自然明确、限制可见；别名与可选措辞不造成误拒绝。实际1440/320页面核标题/短段/列表/表格可读、安全边界和证据定位，展示仍对应受审原文。仅补真实受影响链路的离线/模拟检查，不重跑旧15、不另加付费润色；离线结果不能声称真实新生成口吻已改善。

**依赖与失败分支。** 任何未来新generation前，必须修正常生成请求的实际输出上限并验证意图/Key/provider IO前拒绝超限；当前review guard不替代它。当前无新增付费授权，不改冻结执行源码/原件/终局成本；若别名无共识或有歧义，优先清晰官方名而非猜测。若排版改变文本/证据含义则修消费层，若语言改写需要新模型实证先完成可审查方案。先完成本包授权与终局记录的一次合并提交，再执行这张离线工作卡，不恢复旧CI/monitor。
