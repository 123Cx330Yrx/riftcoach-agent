# Training Progress生产路径与时间线缺失修复

2026-10-09；审计基线4e87e28c。沿ADR0044与RQ258追踪完整复盘如何成为本人训练进度，
Provider0、数据库调用0；不是新一轮业务评分或产品资格。

## 实际路径与结论

- RecentReviewTaskExecutor的schema2.0分支构造TerminalAssistantTurn，但明确传入
  candidate_proposals=()。公开夹具实际执行也返回零候选。
- TerminalCandidateProposal只接受model_inference/published_review_observation；
  deterministic_run_fact实际被模型验证器拒绝。不能靠给模型提案换标签生成测量。
- terminal_turn_writer可从proposal动态写PendingMemoryCandidate，但上游没有Progress提案。
  全app的另外一个构造点在MemoryCandidateService.create；公开POST固定user_structured_input，
  Progress按现有gate拒绝。内部Service可接受合法确定性命令，但未找到生产调用者。
- TrainingProgressMaterializer与writer已有同事务采用、active self Plan/metric allowlist、
  succeeded task/publication/report/final Artifact digest核验、追加与纠错；这是消费者合同，
  不能据此称真实服务器测量生产已经接线。测试直接构造确定性Candidate也不是生产者。

动态审计证据为operator outputs/riftcoach-training-context-20261009/producer-audit.json，
SHA256 ce98cace740948d0f03aaa4098fa1d1b1d9ea0e51ebebbdd557d6e6cea0c89c6。
它固定11份源码/合同摘要，记录v2零候选、terminal拒绝、公开gate及下述数值反例。
所有值来自公共替身，无真实比赛、模型或数据库；源SHA是修复前基线，不冒充修复后摘要。
已有v2执行/公开身份provenance/terminal合同5项检查通过，1.96秒。
第一次错误选择系统Python缺pytest，未产生证据；改用仓库.venv后执行。

## 发现的确定性数值缺陷与修复

timeline_fallback正确保留deaths_before_15=None。aggregate_recent_matches的通用avg却在
没有有效值时返回0.0；部分缺失时又只平均有值的行，字段没有标出换过的分母。
因此全缺失被说成零死亡，部分缺失的子集均值被说成本次整组均值。
同一公共夹具中，旧汇总是0.0，已有按位置投影却是None/sample_count0；反例实际复现。

修法只作用于该时间线指标的整体、赢局、输局均值：命名样本为空、任一行明确timeline
unavailable或指标缺失时，返回None；完整样本仍按既有规则计算，真正测得0保留为0。
不将部分可用的子集冒充整个样本。已有分位置投影有明确有效样本数，保持其部分样本合同。
其他指标不在本次修复范围；不宣称空胜负组的所有旧指标都已表达缺失。

数据流：实际Summary Builder→match_analyzer→确定性报告/保存Summary→验证摘要的RunQuery
→HTTP DTO/MCP只读投影→web decoder/adapter→RecentFormPanel。
RunQuery两种DTO、MCP输出schema与web类型允许必填的number|null；缺字段、负值与非有限值
仍拒绝。Report renderer已有N/A和跳过未知事实的行为，复用它；页面中英文显示数据不完整，
不再调用数值格式化器把null变成0。没有新增表、路由、依赖、模型政策、接受权限或默认准入。
这是同名V1字段缺失语义修正；外部只接受number的旧客户端需随nullable合同更新。

原历史run/报告/付费请求/封存不改、不重新渲染；新鲜Summary才采用新聚合行为。
查询不重新计算旧已保存聚合，旧错误零值仍是历史证据；不把此次代码修复当旧业务重新评级。

## 验证与复现

- 新公开整链6例：修前5 failed/1 passed，2.06秒，失败分别落在全缺失、赢局缺失、输局缺失、
  unavailable残留数值与空胜负组；完整已知正例通过。
- 修后6 passed/1.86秒。真实文件Store/Trace/Artifact摘要查询与MCP client都在替身链内运行；
  不是真实Provider、DB或用户比赛。
- 新例及相邻Summary/Stage1/RunQuery/MCP/live HTTP/位置/Coach装配合计131 passed/12.10秒。
- web decoder/adapter15 passed/1.85秒；中英文组件与真实零3 passed/1.44秒；typecheck通过。
- 新nullable输出另核MCP合同/传输/Streamable HTTP，40 passed/17 subtests/2.17秒；
  与上列131项文件不重叠。编译、治理与diff检查通过。
- 前一提交4e87e28c的公共web/数据库/packaging检查成功，pytest shards仍运行；
  不将其CI当本次新修改的验证。

运行：仓库.venv的pytest执行tests/test_recent_timeline_missingness.py及上述相邻文件；
web中npm run test:unit指定decoder/adapter/RecentFormPanel三个文件，npm run typecheck。
本轮无SQL变更，不重新创建或迁移数据库。

## 下一动作与取舍

自动生产Progress仍缺测量范围、时间和跨run去重合同，不直接复制recent_summary数值：

| 候选测量 | 可复用来源 | 尚须明确的含义 |
|---|---|---|
| 每场指标 | 已纳入matches的确定性数值与实际分路 | 原Summary没有比赛发生时间；多次复盘相同match如何避免假新增样本 |
| 近期窗口均值 | recent_summary或带有效样本数的位置投影 | 窗口/位置/有效分母、重叠窗口含义；不能与每场事件混用 |

ADR0044的metric_key/unit允许列表没有定义上述范围；示例deaths_before_15/vision_score也不足以
推断范围。Summary generated_at_utc是生成/获取时刻，不能冒充比赛发生时间；Evidence桥明确
保留这个区别。source Candidate唯一只防同Candidate replay，不防新run重复观察相同比赛。

下一免费工作包形成服务器测量生产的最小合同和公开正反例，选清楚来源/范围/时间/去重后
复用Candidate pending→用户accept→现有writer。不要放宽TerminalCandidateProposal允许模型
自报确定性，也不要增加Progress写路由或自动接受。observed不产生self训练。
共同语义修法/正式同版本15/当前组合自然消费与8E仍未完成，新增资格0；旧3/15与历史2/15
各自保留，关闭付费批和PAUSED自动任务不重开。四块联动、前端审美头像、Memory、身份运维、
两树整合与八维学习依赖仍保持。

学习表述：我沿生产者和消费者追踪了训练进度，识别出“能存储”与“实际有测量生产”之间的缺口，
并修复了时间线缺失被汇总成零的确定性错误。不能说已经实现自动训练进度或证明训练效果。
