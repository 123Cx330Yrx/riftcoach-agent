# 逐场 Training Progress 生产合同

2026-10-09，沿 ADR0044 的确定性 Candidate→用户 accept→事务物化路径。
这是免费产品接线工作，Provider0；不完成8E、真实训练效果或模型资格。

## 选择及边界

窗口均值存在重叠样本与分母歧义，先选逐场测量。新增显式指标键
`match.deaths_before_15`（count）与 `match.vision_score`（score）：本次复盘纳入的
每场完整比赛、所有实际分路；不是近期均值、特定分路目标或长期习惯。
旧 `deaths_before_15`/`vision_score` 及任意用户指标继续原合同，不自动映射。
只有用户已接受、当时active的self Plan列出新键和正确unit时才生成。

`observed_at`只取 Riot Match-V5 `gameEndTimestamp` 的整数毫秒UTC。
缺失/非法/未来时间跳过，不用generated_at或时长推算。比赛结束必须在Plan创建之后，
且不晚于源task创建；历史比赛不回填为新Plan训练。早死指标要求timeline available，
缺值/非有限/负值/布尔/非整数跳过，真实0保留。短局/未纳入/未知分路跳过。
同Summary重复match身份视为来源错误，整笔投影回滚。

value五字段保持原样；可选measurement envelope保存match_id、实际position、queue_id、
结束毫秒与已核验的Summary文件字节SHA、规范化投影SHA，两者不能互换。
显式match键必须带这个证据；泛指旧键不带。
源task/run/final Artifact保持Candidate已有不可变身份。

首次候选按owner/relationship/Plan/metric/match稳定key占位，用已有数据库唯一约束与锁
保证并发及跨run去重。第二次观察（即使不同Conversation、数值变化、旧候选已拒绝/过期/
隐藏）不重发、不修改原来源、不假称replay，也不增加样本。
不自动纠错；本生产者不产生supersedes。旧追加纠错路径保留；新的逐场key先不提供纠错
生产，未来需要明确同match身份与重新核验来源后单独接续，不借普通新样本绕过。

## 控制流与恢复

Worker终态CAS成功后，terminal writer在消息事务中核当前身份和完整run证据。
仅evidence_bound_v1任务具备持久的主体绑定投影摘要；legacy任务不生产/不回填。
沿既有RunQuery完整验签读Summary，并对源task的规范化Summary digest与final报告digest。
同事务创建确定性pending Candidates、最后标记projection completed。消息结果可带最多
200服务器候选加8模型提案ID；模型提案上限仍8，原模型提案的独立写事务未在本轮扩大。
任何测量来源/数据库异常回滚消息、候选与completed标记；既有pending恢复读同run重做，
不调用模型。completed任务不补产新候选，重放不受之后换Plan影响。
终态模型proposal仍不得自报deterministic；公开POST不能指定服务器来源；不增加路由
或自动accept。accept再次核active Plan/metric/unit与来源，目标表继续已有事务物化。

## 验证及未证

公开正反例应覆盖真实0、未知/过期/未来时间、缺timeline、单位、泛指键、重复match、
跨run/跨Conversation/跨身份、拒绝/隐藏去重、换Plan和中断事务恢复。
实际文件Harness/Trace/receipt与可销毁Postgres链是工程证据，不是实际Riot/Provider消费。
不迁移业务库、不改主树前端、旧run/付费回执与评级原件。

实际结果：公开测量/时间/单位/范围/重复/采纳解析23项通过，1.96秒；相邻纯合同、
API、Worker、RunQuery与Stage1共157项，5.81秒，Evidence桥/装配/terminal/候选API与
nullable整链另70项，4.04秒。23项中的原19项在157组内，新4项另核，复跑不累计。
真库11项新生产整链与既有terminal/training/Candidate/物化/Memory消费20项共31项，
28.34秒；使用真实文件Store/Trace/receipt与可销毁Postgres，全部业务数值仍为公共夹具。

真实反例推动两处修正：pending batch用scalars读取task_id/run_id双列，实际无法解包，
改execute并中断后恢复通过；task.summary_digest来自Evidence规范化Summary投影，不是
含换行的文件字节SHA。复用桥原编码函数，保留并分别验证两身份，测试显式断言不同。
投影的锁序也对齐Candidate（relationship→Conversation→Plan→stable key），并发跨聊天
只生成一组候选。数据库临时库每次create-only且最终删除，业务库仍0014；没有迁移变化。
初轮夹具误更新不可变task身份被trigger拒绝，改在insert时提供完整身份；后续夹具漏传
reject reason_code已修正。来源损坏异常已收敛为安全错误，不把原始路径/摘要泄露到API。

代码入口：match_analyzer保留原始end time；memory/training_measurement定义范围与身份；
training_progress_producer从完整验签来源提案；terminal_turn_writer保证服务器候选原子恢复；
memory_repository复用单事务Candidate gate/锁与唯一约束；training_writer再次核采用合同。
CI数据库job已加入新11项文件，纯测量随原全套shards收集。此前6c9f1f67的四shards/DB/
packaging成功、web仍运行；不能替代本次新提交CI。

下一免费工作包核现有HTTP/UI的本人计划、测量候选说明及accept是否实际可达，补最短
产品断点。生产接线工程已完成，但没有实际用户比赛/Provider生成/页面自然消费或训练效果证据。
