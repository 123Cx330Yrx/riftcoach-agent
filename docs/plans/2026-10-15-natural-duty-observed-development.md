# 一份自然观摩任务的开发验证准备

2026-10-15。当前仅完成零付费工程准备；未读取模型凭据、创建真实run或发送模型请求。
六次候选仍不具备产品资格。此包沿实际Agent任务补生成与检索证据，不重启原15或已关闭的原稿保留研究。

## 目标与范围

此前固定报告链没有证明Agent能自己取知识、生成初稿，再在同一个900秒预算里完成审查与修订。
本包使用真实RecentReviewApplicationService、OBSERVED Memory绑定、AgentLoop、本地RAG、
共享预算、逐字补丁和双fresh；只替换来源获取为已核对的公开历史来源。执行期间没有人工插审、暂停或改稿。

两份原始来源逐字复制到`data/evaluation/fixtures/natural_duty_observed_source_20261015`：

| 文件 | SHA-256 |
|---|---|
| evidence_bundle.json | 6d5ab97ba85f92cf650f05740956b8033e0b8a5093f846268f71ae3c5243dab8 |
| player_summary.json | 13cb231e905c5a7fd2e4edbaa7a6a18be6fb47fbbc6ea7601d7b4d9519ed2132 |

来源为原后端`golden_20260910_compact_1cd694d`；投影时间固定为
`2026-09-10T12:15:28.980990+00:00`。这是历史公开来源的熟悉开发例，不声称当前抓取或holdout。
输入仅包含来源；旧报告、判断、标签和预选知识均不进入模型。本次Agent自主调用knowledge.search。
空OBSERVED Memory仍走真实绑定及manifest，ShowMaker是观摩对象，不是阅读者本人。

typed入口为count=5、queue=420、focus=overall；实际编译任务另存preparation，明确上述观摩限制。
它不是旧自由文本逐字复用。离线prepare实际运行应用，在第一请求到达无网络capture provider时终止，
临时runtime文件随后清除；该证据不假装完整模型执行。

## 实施与预算

- 专用`NaturalDutyProviderFactory`返回exact候选router，Flash/high负责生成，GLM-5.3/high负责两职责审查。
- 专用transport复用GoldenProcessStreamProvider、SDK流组装及子进程关闭；共享global ordinal最多6，
  每次最多300秒、32768输出；整任务6调用／401920tokens／900秒，不分阶段重新计时。
- 双initial pass直接结束；有合法补丁则唯一程序application及双fresh。额外工具轮消耗同一预算，
  不足双fresh slot时在应用前停止。没有Flash编辑调用、字段补填、模型重试或第七次。
- 自然子进程清代理、NO_PROXY=open.bigmodel.cn及trust_env=False；GitHub只在查询子进程使用本机代理。
  不改变用户网络。完整响应必须有严格schema1.3的complete/closed/EOF/terminal、HTTP=1及匹配用量观测。
- 旧产品5次和原transport身份保持。当前manifest更新只描述现有源码；历史原件与旧源码LF归档保留。

保守未缓存估价为**5.7595904元**，按ADR0108/2026-09-22报价快照、最多4GLM审查和共享token上限计算。
不是现价保证或账单硬上限；未知调用不能记免费。未获得这个包的新费用授权，旧授权不挪用。

## 执行入口和不可重开边界

统一入口：`python -m scripts.run_natural_duty_development prepare|execute|replay`。
固定run ID为`natural-duty-observed-20261015`；执行根为`data/runs/model_comparison/`下同名目录。
Operator目录必须与run完全分开，建议工作区outputs下同名目录。没有后台waiter，automation保持PAUSED。

prepare生成create-only准备JSON及可选第一请求文件。execute要求重新生成结果逐字段一致、clean exact HEAD、
同HEAD的web/Postgres/packaging/四个pytest分片及所有返回job全绿；查询失败不能解释为CI失败。
费用授权必须是新格式`natural-duty-observed-development-v1-authorization`，绑定准备SHA、执行HEAD、
run ID、全部预算、估价、真实用户授权证据、issued_at及不超过24小时的expires_at；禁止重试和生产准入。
授权由未来明确用户答复后记录；本包不代写授权。随后才独占claim、载入已授权凭据和运行应用。

每次发送前重验授权、HEAD、源码配置和前序回执。第一请求只允许预算缩短timeout；内容变动在真实
transport claim前阻断。前序传输原件的摘要在run外create-only observation中固定，后续改动会停止。
任何run或claim存在，入口拒绝再次执行；启动失败也保留claim，不删除后重发。

stdout首次输出guard SHA，结束输出closure SHA；Operator保存原stdout。closure绑定run所有原件和
run外observations。replay要求这两个原始摘要并严格只读，不重算成新的信任根、不改文件或补回执。
坏回执继续标invalid_receipts；receiptless、未知用量、已知未接受响应、HTTP未知和未预留slot分别保留。
completed_unqualified仅表示模型链完成；stopped_unqualified、failed、cancelled分别保留，不代表发布成功。

## 结果如何改变判断

| 观察 | 结论和动作 |
|---|---|
| 初稿双pass，事后两审均接受完整任务 | 一次自然生成/初审证据；没有修订证据 |
| 真问题、正确补丁、实际同稿双fresh，事后两审均接受 | 一次自动修订整链开发证据 |
| 漏报、误报、错修、删坏正确内容或fresh误放 | 保留最早语义反例，否定本例候选；不按字段修补后续购 |
| 检索耗掉slot或token/900秒用尽 | 自然任务与预算匹配证据；不扩额、跳fresh或重试 |
| 身份、协议、传输、持久化或观测故障 | 工程失败和未知账目，不能冒充语义结论 |
| 主审与独立审查分歧 | 未决原样保留，不拼成通过 |

运行后主审和复用的独立审查者必须完整实读：公开来源、实际编译任务、工具选择及知识、初稿、全部
请求/响应、两职责意见与补丁、程序preview/application及实际终稿。审核前固定对应checkpoint与SHA，
作者在run外写自己的答案，真实native final及event-id按现有工具导入；不得用工程审查替代业务审查。
没有强制修订、为了凑满六次发送或正向结果预设。即使正向，此熟悉单例仍不授产品资格或重判旧15。

## 验证与下一动作

结果记录`data/evaluation/results/natural_duty_observed_offline_20261015.json`；具体准备及首请求
由同一入口生成，待提交精确HEAD公共CI通过后才进入最终新费用授权。
模型网络全部阻断的离线检查覆盖实际四/六次应用、额外检索、错误授权、首请求漂移、重复claim、
真实子进程worker/SDK编码/收流/关闭、缺观测、超时及只读回放；替身响应不作模型质量证据。

正式同版本15、自然Coach/本人Training、四块联动/journal、前端审美和头像、Memory、身份运维、
两树整合、独立评估和学习八维仍在原依赖表，8E未完成。Docker已恢复且原Postgres健康，未重置业务卷。

准备文件SHA：`3c7a650191d17f0412955a4d1fd63d6d967624f54b12b46458666abe6c09fa0b`；
其内部plan SHA：`5849dac91ff0b4df6bdaa8ff9b874042547b383f974d2734644fbbf73ee8aaac`。
771份源码/配置/知识与来源文件绑定；第一请求SHA：
`830a9b8a09024ba81d4f652971dab5392df4f66b3a553ea0f5e40ff8fe9f10a8`。
这些摘要不构成用户费用授权。

独立工程复核提出并修复：终态输入归档重新绑定原guard摘要，防止运行中改档被closure覆盖；
发送前磁盘检查结束后按同一共享预算拒发或缩短timeout，未另起900秒时钟。
对应第4响应后改三类原件、899→901拒发及899→899.5缩短到0.5秒反例均通过。
后续完整响应缺观测仍可只读回放为invalid_receipts，不能把错误账目转换成成功。


## 2026-10-15 公共CI续查与Docker复发恢复

准备提交4d37e344的CI38685915747分片2在旧保留研究方案重建断言失败；其余分片、Web、Postgres、打包通过。
仅natural_duty_contract.py源码摘要变化，方案请求、预算、契约保持。旧方案不能跟随新transport重写；
测试从452972e7固定原LF源码，校旧SHA后在临时目录重建历史库存，仍由当前请求构造核全部原请求和预算。
本机修复前1项失败（6.08秒）、后相关24项通过（38.02秒），socket阻断；准备重建相等且SHA3c7a6501保持。
无运行源码改动、凭据读取、新run或模型调用，automation PAUSED，旧裁决不改；等待修复提交自身公共CI。
Docker再启动遇到同类AF_UNIX残留，官方停止后备份并重建两运行目录，原容器ebffdb0a8f3e和业务卷保持，
29.7.2/healthy/15432/SELECT1/0014_message_projection_status已核；未证明上游永久修复。
详见data/evaluation/results/natural_duty_preservation_ci_recovery_20261015.json及outputs/riftcoach-docker-recovery-20261015续记录。
