# Stage 8 Multi-Agent、可靠运行时与产品化入口设计
> 本文是 Stage 8 entry design，不是产品实现报告。它冻结边界、顺序、采用门和验收证据；
> 代码能力只有在对应 checkpoint 的实现与公共 CI 后才能宣称完成。

## 1. 初学者心智模型

### 要解决的问题

Stage 7 已经能让 RiftCoach 调用 OP.GG MCP，也能被外部 MCP Client 调用，但系统仍有四个
产品缺口：复杂任务无法安全取消/恢复；Riot 官方事实与 OP.GG Meta 尚未形成可追溯融合；没有
正式前端；没有公开部署、备份和最终回归证据。

### 关键概念

- Tool Runtime：一次工具调用的超时、重试、缓存、熔断和错误边界；
- Agent Runtime：一批 Tool/Provider/Artifact 事件的运行与终态；
- Harness：评测、修订和发布门，不等于 Agent；
- Multi-Agent：多个有独立上下文/权限/失败边界的执行单元；不是“多次调用模型”；
- EvidenceBundle：不同来源的 typed 事实和 provenance，不是一个未经校验的 JSON 大对象。

### 本入口做与不做

本入口做现状审计、架构选择、8A–8F 顺序、Core/Advanced 分工、前端信息架构、资源采用门、
数据/控制流、测试矩阵和 exact-SHA 退出合同。

本入口不实现 Multi-Agent、DAG、lease、cancel、recovery、SSE、React 页面、正式 Auth/RSO、
公网部署、备份删除或真实 Provider/Riot 调用。

## 2. 当前代码接缝与缺口

| 能力 | 已有证据/代码接缝 | Stage 8 缺口 |
|---|---|---|
| 任务控制面 | `app/tasks/models.py`、`service.py`、PostgreSQL Repository、claim/terminal CAS | durable event、lease、fencing、cancel、自动恢复 |
| Runtime 事件 | `app/runtime/recorder.py`、`models.py`、`store.py`、`runtime.py` | 跨进程事件历史、replay cursor、checkpoint |
| Harness/Artifact | `app/harness/*`、`app/product/run_query.py` | 面向前端的安全证据 DTO 和异步生命周期投影 |
| Session/Memory | `app/memory/context_models.py`、training/lifecycle API | 产品化查询聚合、事件触发刷新和备份副本处理 |
| Riot facts | `app/lol/riot_client.py`、`player_summary.py`、`match_analyzer.py` | 版本/patch/update 事实的 typed 适配和融合键 |
| Static facts | `app/lol/data_dragon.py`、`terminology.py` | exact version identity 与 bundle provenance |
| OP.GG | `app/mcp/transport.py`、OP.GG adapter、partial `MetaEvidence` | 与 Riot/Data Dragon 的受限 join 和冲突降级 |
| MCP | `app/mcp/client.py`、`server.py`、7-5 stdio/HTTP evidence | 作为内部 evidence source 的前端安全投影 |
| Web | 当前无正式 React/Next/Vite 产品脚手架 | 五个页面、SSE、Auth、响应式、截图和部署 |

## 3. 8A–8F 职责与出口

| Checkpoint | 主要职责 | 必须产出 | 允许的结论 |
|---|---|---|---|
| 8A | 候选高级能力审计 | Bad Case、候选矩阵、指标、停止条件、实验身份 | candidate / deferred |
| 8B | 条件 Multi-Agent 实验 | 单 Agent vs 并行/多 Agent 对照、消融、成本和失败归因 | adopt / partial / reject |
| 8C | 可靠 Runtime Core | durable events、lease/fencing、cancel、checkpoint、recovery、迟到隔离 | Core implementation |
| 8D | Riot+OP.GG Fusion | typed EvidenceBundle、join/conflict/freshness 降级、个性化建议 | Core implementation |
| 8E | 产品化 | React 五模块、SSE、Auth/RSO、HTTPS、限流、备份、部署 | Core implementation |
| 8F | 最终评测与作品集 | 回归、安全、性能、无障碍、截图、演示、简历事实矩阵 | final exit |

8B 的 reject 不会阻塞 8C/8D/8E；它只表示 Advanced 实验完成且证据不足以采用。8C 的 DAG
实现则受 8B 结果约束：没有可测的并行收益，保持单流程 Runtime。

## 4. 双轨依赖图

```text
                         ┌─ 8A gate ─ 8B experiment ─┐
Stage 8 entry design ────┤                            ├─> conditional DAG choice
                         └─ 8C reliable runtime core ─┘
                                   │
                 Riot/Data Dragon + OP.GG ──> 8D Evidence Fusion
                                   │
                         8E Productization (Web/SSE/Auth/backup)
                                   │
                         8F Eval + Portfolio Exit
```

Core 可靠性不能等待一个 Multi-Agent 结论才开始设计，但 8C 的 executor 复杂度由 8B 的结果
限制。8D 和 8E 都必须消费 8C 的可重放事件/安全投影，而不是各自发明状态。

## 5. Riot + OP.GG EvidenceBundle

### 分层

1. `RiotAccountFact`：地区、Riot ID、PUUID 关系和账号查询时间；
2. `RiotMatchFact`：Match Detail、Timeline、玩家指标和事件；
3. `RiotVersionFact`：game version、Data Dragon version、官方 patch/update identity；
4. `StaticDefinitionFact`：champion、item、rune、spell 的 Data Dragon digest/name；
5. `OppgMetaFact`：获准工具的当前快照、lane/champion/rank 等 allowlisted facts；
6. `EvidenceJoin`：显式 join key、冲突状态、provenance level、bundle digest。

### 组合规则

- Riot Match/Timeline 是“这个玩家这场比赛发生了什么”的事实；OP.GG 是“当前快照下外部 Meta
  如何观察”的参考，不能覆盖比赛事实；
- Data Dragon 只能按其版本解释静态 ID，不用最新静态表回写旧局；
- patch 不明的 OP.GG 只能标记 `partial/current_snapshot`，不能继承 Riot patch；
- join 失败、不一致或过期时保留每个来源，建议降级为“事实描述 + 无 Meta 归因”；
- bundle 中只允许 bounded typed facts、source identity、retrieval time、digest、expiry 和限制，
  禁止原始 response/body。

## 6. 前端产品蓝图

### 6.1 电影感入口与 Riot ID

入口使用抽象 Rift 地形、战争迷雾、Lane 能量路径和 Coach Core。鼠标 spotlight、SVG/Canvas
视差和一次性转场服务于“输入账号→进入分析”的叙事；移动端使用轻量静态地图，reduced-motion
关闭位移和粒子。现有 `/player-links` 与可信关系 API 可作为接缝，正式 Auth/RSO 属 8E。

### 6.2 近期复盘工作台

使用 `RecentSummaryView` 的胜率、KDA、CS/min、Gold/min、Damage/min、视野、参团率、占比和
15 分钟前死亡；用最近对局列表与 publication/degraded/rejected 状态建立工作台。已有
`RunQueryService` 和 Run/Task API 是事实来源，前端只能消费安全 DTO。

### 6.3 Rift Timeline

使用现有 `gold_by_minute`、`cs_by_minute`、`xp_by_minute`、`level_by_minute`、死亡、购买和
资源事件。桌面是可拖动时间指针和分阶段事件轨；移动端是横向时间尺+事件抽屉。缺 timeline 时
降级为对局摘要，不绘制伪造的完整曲线。

### 6.4 Evidence/Agent Trace 抽屉

展示来源、版本、digest、事件类型、工具身份、publication、usage completeness 和限制；不展示
隐藏 Prompt、chain-of-thought、原始参数/body、session、Key 或本地路径。事件通过未来 SSE/cursor
提供，断线依靠 replay，不依靠浏览器连接保持真相。

### 6.5 Training Plan/Progress

使用现有 Plan/Progress API 的 active plan、metric baseline/target/current/delta、sample count、
纠错关系、source run/artifact digest 和 candidate accept/reject。动效只反映真实状态，样本不足显示
“证据不足”，不虚构游戏化等级。

## 7. 设计系统与 MotionSites 采用门

推荐视觉主线：黑曜石/深海军蓝底，Hextech 青蓝作为结构强调，克制金色作为 Coach/完成状态，
紫色只用于 Meta/未知 provenance 或 Void 实验区域。动效三级为 120–200ms 反馈、250–450ms
状态切换、700–1200ms 入口叙事。

外部资源组合固定为“自主组件 + 精选效果”：Radix/shadcn、Motion、ECharts 是基础候选；
React Bits/Aceternity/Uiverse/Anime.js 要逐项审查；MotionSites 只提供公开可检索的设计 Prompt、
预览和可选付费完整 Prompt/资产。`motionsites.ai/sections`、`/templates`、`/apps`、`/backgrounds`
是公开检索入口；用户 Excel 是离线全文候选，不是产品依赖。

每个候选必须记录：官方 URL、页面类别、预览截图/视频、免费/付费、Prompt/资产取得方式、许可、
技术栈、依赖、性能、移动端替代、reduced-motion、键盘/对比度风险、RiftCoach 改造点和撤出方案。
不购买会员作为默认前提，不绕过付费墙抓取受限内容；只在候选胜出后让用户获取有权使用的单项材料。

## 8. 测试与退出矩阵

### 入口设计门

- canonical/coverage 顺序与前序完整性由 `check_project_governance.py` 阻塞；
- ADR、设计、实施计划和 walkthrough 含八维证据；
- 现有完整回归、RAG/Harness、compile、secret/tracked-data 和 `git diff --check` 通过；
- 本批外部 Riot/Provider/LLM/Key I/O 为 0，MotionSites 只读公开检索不进入产品代码。

### 后续 checkpoint 门

- 8A/8B：实验身份、同切片对照、零重试/预算、held-out 与消融不可覆盖；
- 8C：真实 PostgreSQL 并发、事件 replay、fencing、cancel/recovery、迟到结果和故障注入；
- 8D：Riot/OP.GG fixture、版本冲突、partial provenance、join key 和建议限制测试；
- 8E：React 单元/集成、API contract、SSE reconnect/replay、Playwright 桌面/移动截图、键盘、
  reduced-motion、CSP/CORS/Auth/HTTPS/backup restore；
- 8F：固定回归集、性能 p50/p95、成本/工具次数、无障碍扫描、依赖/许可证/安全扫描和作品集事实矩阵。

## 9. 面试准确表述

可以说：

> 我把 Stage 8 分成可靠运行时 Core 和证据驱动 Advanced 轨。Multi-Agent 不是默认答案，先用
> 同一 Harness 做单流程与并行对照；同时把 Riot 比赛事实、Data Dragon 版本静态和 OP.GG 当前
> Meta 快照放进有 provenance 的 typed bundle，再让前端展示证据和限制。

不能说：

- “已经完成 Multi-Agent/DAG”；
- “OP.GG 和 Riot 已经完成精确 patch 融合”；
- “已经有正式公网 Auth、SSE、备份恢复或生产前端”；
- “MotionSites Prompt 本身就是 RiftCoach 的生产代码”；
- “Stage 7 的互操作证据等于 Stage 8 产品化完成”。
