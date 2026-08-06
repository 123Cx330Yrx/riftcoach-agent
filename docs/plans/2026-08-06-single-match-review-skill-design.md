# 阶段 5C-5-prep-2：single-match-review Skill Contract

## 1. 本轮要解决的问题

`recent-form-review` 处理多场近期对局的趋势，`single-match-review` 处理用户明确
指定的一场对局。二者会共享“复盘、表现、问题”等目标词，但数据范围、证据边界
和成功标准不同。若没有第二个真实 Skill，Router 只能证明规则算法可运行，不能
证明相邻业务意图能够被真实合同区分。

本检查点只定义并验证 Skill Contract。Catalog 加载合同不授予执行权限；Router
选择合同也不会调用 Skill、Tool、模型或 Harness。

## 2. 输入方案比较

### 方案 A：Riot ID + match_id，由 Skill 自己拉数据

不采用。它会把 Riot API 和 Data Dragon 权限重新授予 Agent，重复阶段 1 的确定性
事实链路，并让单局复盘受网络状态影响。

### 方案 B：只传一条 match row

不采用。裸记录缺少 Summary Schema 版本、玩家身份、请求来源和审计上下文，无法
确认记录来自兼容的领域产物。

### 方案 C：完整 Summary + 确定性报告 + target_match_id

采用。输入为：

```text
SingleMatchReviewInput
├── player_summary: Player Summary Schema v1.0
├── deterministic_report: 非空的确定性报告
├── target_match_id: 在 matches 中恰好出现一次
└── focus: overall / laning / survival / economy / vision
```

完整 Summary 用于验证来源和唯一目标，不代表未来要把全部对局放入模型上下文。
阶段 5D 的 Context Builder 只抽取玩家身份、目标 match row、必要的报告片段和有界
知识证据。

## 3. 数据与控制流

```text
用户文本
  → Catalog 只投影 Manifest 路由元数据
  → DeterministicSkillRouter 选择 single-match-review
  → 未来 Runtime 构造 SingleMatchReviewInput
  → Pydantic 验证 Summary v1.0 和唯一 target_match_id
  → 未来 5D 才执行受限 Agent Loop
  → 既有 Harness Evaluator 强制评测并决定发布
```

本轮只实现前三层合同和验证，不实现未来 Runtime 部分。

## 4. 单局证据边界

- 玩家特定结论只能来自目标 match row 和对应确定性报告事实；
- 其他 match rows 与 `recent_summary` 不能被偷换成目标单局事实；
- 短局仍可复盘，因为 `included_in_aggregate=false` 只禁止它进入近期平均值；报告
  必须提示时长限制，不得外推为长期水平；
- Timeline 为 `unavailable` 时仍可使用 Match Detail 指标，但必须有明确错误原因；
  死亡时间、购买事件等未知数据不能写成零；
- Match Detail 失败或目标 ID 不存在/重复时直接拒绝输入；
- 不推断对线对手、隐藏信息、实时状态、版本 Meta、主流出装或符文胜率。

## 5. 权限、预算与质量策略

唯一允许工具是 `knowledge.search`。它只解释指标、数据限制和通用训练原则，不负责
拉玩家事实。合同预算为：

| 项目 | 上限 | 作用 |
|---|---:|---|
| Agent iterations | 4 | 防止无界循环 |
| Tool calls | 3 | 限制知识检索次数 |
| Timeout | 30 秒 | 限制运行时间 |
| Context | 16000 tokens | 限制上下文规模 |
| Quality score | 85 | 由既有 Harness 统一判断 |

质量门禁失败时允许发布确定性降级报告；Skill 自己没有发布权。

## 6. 路由边界

单局 Skill 要同时命中：

1. `match_scope`：这一局、这一场、单局、match id、比赛编号等；
2. `review_goal`：复盘、分析、表现、问题等。

近期范围与单局范围不互相作为排除信号。只要两组真实 Skill 同时满足，Router 就
返回 `ambiguous`，不根据语序或候选顺序擅自选一个。因此“分析最近十局里这一场
的状态”和“比较这场和最近十局的表现”都需要未来上层澄清。V1 的字面 Router
没有句法能力，无法可靠区分“用近期列表定位一局”和“要求两个任务”。

裸 `复盘 KR_8287337995` 暂时拒绝，因为 `KR_...` 本身没有稳定的范围标签；用户
需要说 `复盘 match id KR_...` 或 `复盘比赛编号 KR_...`。是否安全支持裸 ID 交给
5C-5 的评测证据决定，不在 Manifest 中加入宽泛的 `KR` 子串。

版本、实时、敌方冷却和天气等领域继续是一票否决。

## 7. 测试证据

- Contract：两个 Skill 包均可严格加载，模型引用、工具白名单和说明一致；
- Input：目标 ID 必须非空且恰好命中一行；
- Missing data：短局可审查，Timeline 缺失必须显式表示且不能伪造零；
- Output：发布/降级必须有报告，拒绝状态不能暴露未通过草稿；
- Catalog：真实目录稳定产生两个按名称排序的候选；
- Router：近期、单局、混合范围歧义、裸 ID 拒绝和域外请求均有确定结果；
- Versioning：近期 Skill 触发语义改变后由 `0.1.0` 提升为 `0.2.0`。

这些测试证明合同边界，不证明自然语言路由已充分泛化。双 Skill 开发集和独立
保留集仍属于下一检查点 5C-5。

## 8. 当前限制

- 还没有 Skill Executor 或 Context Builder；
- 还没有调用真实 Provider、Tool 或 Harness；
- Pydantic 只能确认目标行属于传入 Summary，不能独立证明确定性 Markdown 与该
  Summary 来自同一个 Artifact；该关联由后续 Harness/Artifact 输入负责；
- 当前 Player Summary 文档、校验器和部分旧 fixture 对 Timeline 辅助字段的严格度
  并不完全一致。本轮在单局目标为 `unavailable` 时收紧必要边界，但不借此越级
  重写阶段 1 Schema。
