# 阶段 1 学习复盘：LoL 确定性领域核心 v1

> 本文解释 RiftCoach 最底层的事实链怎样工作。它描述当前仓库中的真实代码，而不是把
> 早期聊天、一次 API 探针或模型生成结果当成稳定能力。当前项目检查点仍以
> [`project_execution_state.md`](../project_execution_state.md) 为准。

## 1. 为什么 Agent 先要有确定性事实层

RiftCoach 要回答“最近为什么输、下一步练什么”。如果让大模型直接读取杂乱的 Riot JSON
并心算 KDA、每分钟补刀、输出占比，它可能算错数字、忽略 Timeline 缺失，或把相关性说成
因果。再好的 Prompt 也不能把这种不稳定计算变成可靠事实。

阶段 1 因而采用一个简单但关键的原则：

> **程序负责取数和计算；Schema 负责固定事实形状；模型只能解释已经验证的事实。**

可以把它理解成“先做仪表盘，再做教练”：

```text
公开赛后数据                确定性 Python                 可解释消费者
Riot API / Data Dragon  →  MatchAnalyzer + Schema  →  报告 / RAG / Agent
```

其中：

- Riot API 是已经发生的比赛数据来源；
- MatchAnalyzer 是计算器；
- Data Dragon 是静态名称词典，不提供玩家强度或版本胜率；
- Player Summary 是下游统一读取的数据合同；
- Markdown 报告是确定性展示；
- LLM/RAG 是后续解释层，不能反向改写事实。

## 2. 设计选择：做了什么，拒绝了什么

### 2.1 采用的设计

1. **薄 Riot HTTP Client**：一个方法对应一个 API 请求；复杂重试、缓存、熔断后来由阶段
   3 Tool Runtime 负责，避免传输层和可靠性控制层混在一起。
2. **依赖注入的 Summary Builder**：`RiotMatchClient` 和 `MatchStaticDataService` 是小型
   Protocol。测试可注入 Fake，不需要 Key 或网络。
3. **纯函数计算事实**：Match Detail、Timeline 和近期聚合分别处理，便于复用和定位错误。
4. **版本化 Summary**：下游必须检查 `schema_version=1.0`，旧无版本数据不能静默进入新链路。
5. **未知值显式化**：Timeline 不可用时标记 `unavailable`；相关统计为 `None` 或空集合，
   而不是伪造为零。
6. **短局保留但不聚合**：默认不足 300 秒的比赛仍保留明细和排除原因，不污染近期均值。
7. **确定性报告与 Coach 草稿分层**：前者只读事实并按固定规则展示；后者必须经过后续 Harness
   的独立评测和发布门。

### 2.2 明确拒绝或推迟的设计

- 不让 LLM 自行计算 KDA、占比、Timeline 事件或 Summary；
- 不让 Agent 直接获得原始 Riot API 和 Data Dragon 权限；后续 Skill 读取验证后的 Summary；
- 不把 Data Dragon 当成动态版本 Meta 数据源；英雄胜率、登场率等属于阶段 7；
- 不把一次真实账号 API 探针当作长期可用性、SLA 或账号所有权证明；
- 不从赛后统计推断录像级走位、技能命中、兵线细节或玩家心理；
- 阶段 1 的 RAG v0.1 和 GLM 脚本只是业务可行性原型，正式 RAG、Provider 和质量运行时分别
  在阶段 4、3、2/5 完成。

## 3. 真实代码地图

### 3.1 数据取得与静态映射

| 文件 | 真实职责 | 不负责什么 |
|---|---|---|
| `app/lol/riot_client.py` | Account-V1、Match-V5 IDs、detail、timeline 的薄 HTTP 请求 | 不做领域计算；不拥有阶段 3 的重试/缓存/熔断 |
| `app/lol/data_dragon.py` | 加载/缓存版本和 `zh_CN` 静态数据，把 champion/item/spell/rune ID 映射为名称 | 不提供实时胜率、出装强度或中国大陆服务器路由 |
| `scripts/riot_api_probe.py` | 人工检查账号和 Match API 链路 | 不是产品入口，也不是 CI 的真实 Riot 测试 |

### 3.2 确定性分析与数据合同

| 文件 | 真实职责 | 关键出口 |
|---|---|---|
| `app/lol/match_analyzer.py` | 找目标参赛者；计算单局 detail 指标；提取 timeline 事件；聚合近期样本 | `analyze_match_detail()`、`analyze_match_timeline()`、`aggregate_recent_matches()` |
| `app/lol/player_summary.py` | 编排账号→比赛列表→逐局 detail/timeline→静态名称→聚合；记录失败和排除项 | `build_player_summary()`、`RiotPlayerSummaryBuilder` |
| `app/lol/summary_schema.py` | 创建并验证 `Player Summary Schema v1.0` | `build_summary_document()`、`validate_summary_document()` |
| `docs/summary_schema.md` | 面向下游解释 Schema、短局和 Timeline 语义 | 文档合同，不执行代码 |

### 3.3 报告与兼容入口

| 文件 | 真实职责 | 边界 |
|---|---|---|
| `app/lol/report_renderer.py` | 从 Summary 生成固定 Markdown 和有限规则发现 | 不调用模型，不创造新比赛事实 |
| `scripts/build_player_summary.py` | 解析 CLI 参数并装配真实 Riot/Data Dragon 依赖 | 外部 I/O 入口；需要本地配置 |
| `scripts/generate_markdown_report.py` | 校验 Summary、应用术语/静态名称并写 Markdown | 当前构造 Data Dragon，可能读取缓存或网络，不是纯 no-I/O 演示 |
| `scripts/generate_llm_coach_report.py` | 历史 Coach 草稿入口 | 模型文本不是自动发布事实；正式链路使用 Provider/Harness |
| `scripts/evaluate_coach_report.py`、`scripts/revise_coach_report.py` | 历史评测和受限修订入口 | 后来由阶段 2 Harness 统一控制生命周期 |
| `app/artifacts.py` | 按玩家生成稳定本地 Artifact 路径 | 不校验报告内容本身 |

### 3.4 主要测试

| 文件 | 证明什么 |
|---|---|
| `tests/test_stage1_pipeline.py` | Riot ID 使用最后一个 `#` 拆分；玩家路径隔离；短局排除；Timeline 缺失；拒绝无版本 Summary |
| `tests/test_recent_review_domain_services.py` | 后续产品服务复用同一个 Summary Builder/报告 renderer；CLI 与 app renderer 字节一致 |
| `tests/test_terminology_display.py`、`tests/test_name_naturalizer.py` | 中文术语展示和名称自然化的确定性行为 |
| Harness、Skill、Context 相关测试 | 下游继续把 Timeline unknown、短局和 Schema 身份当成不可篡改边界 |

这里有一个诚实的测试缺口：当前没有一组专门逐公式穷举 `match_analyzer.py` 中每个指标的
独立参数化单测。代表性 Fake 对局和大量下游 fixture 会执行这些字段，但这不等于每个公式的
边界都被独立证明。以后修改计算公式时，应优先补公式级测试，而不是只依赖大范围回归变绿。

## 4. 数据和控制流

### 4.1 构建 Player Summary

```text
输入 gameName#tagLine、count、queue、最短时长
        │
        ▼
RiotClient.get_account_by_riot_id()
        │ Account-V1 返回公开账号与 PUUID
        ▼
RiotClient.get_recent_match_ids()
        │ 若指定 queue 没结果，记录 fallback 后可无 queue 再查
        ▼
for each match_id
        │
        ├─ get_match_detail()
        │      └─ analyze_match_detail()
        │            KDA / CS/min / GPM / DPM / vision
        │            KP / damage share / gold share / items
        │
        ├─ DataDragon.enrich_match_row()
        │      └─ ID → 官方静态中文名
        │
        ├─ game_duration < threshold ?
        │      ├─ yes: 保留明细，included_in_aggregate=false
        │      └─ no: 允许进入近期聚合
        │
        └─ get_match_timeline()
               ├─ 成功: 死亡时间、15 分钟前死亡、购买、目标事件、分钟快照
               └─ 失败: timeline_status=unavailable，计数保持 unknown
        │
        ├─ detail 失败 → failed_matches，不伪造该局
        └─ 成功 → matches
        ▼
只聚合 included_in_aggregate=true 的比赛
        ▼
build_summary_document() → validate_summary_document()
        ▼
Player Summary Schema v1.0
```

注意两种失败的语义不同：

- **Match Detail 失败**：该局无法形成可靠基础事实，进入 `failed_matches`；
- **Timeline 失败**：该局基础 detail 仍可进入聚合，但 Timeline 专属字段保持未知。

### 4.2 从 Summary 到报告

```text
Player Summary v1.0
    │
    ├─ render_deterministic_report()
    │      └─ 固定表格、样本量提醒、有限赢输差异规则
    │
    └─ 后续 Agent/LLM 消费
           ├─ 只能读取 allowlist 事实
           ├─ 可用 RAG 补解释依据
           └─ 必须经过 ReviewHarness 才能发布
```

确定性 renderer 里的“可能、值得分析”等文字仍只是统计观察，不是因果证明。它会在样本少、
赢输样本不足时收紧表述，但不能替代录像。

## 5. 指标到底怎样算

目标玩家由 PUUID 在 `participants` 中精确匹配。主要公式为：

```text
KDA              = (kills + assists) / max(1, deaths)
CS               = totalMinionsKilled + neutralMinionsKilled
CS/min           = CS / game_duration_minutes
Gold/min         = goldEarned / game_duration_minutes
Damage/min       = totalDamageDealtToChampions / game_duration_minutes
Kill participation = (kills + assists) / team_kills
Damage share     = player champion damage / team champion damage
Gold share       = player gold / team gold
```

`safe_div()` 在分母为零时返回 `0.0`；比赛时长本身必须是正数，否则 detail 被拒绝。零死亡的
KDA 使用分母 1，是一种稳定展示约定，不是“无限 KDA”。

Timeline 按 frame 遍历：

- `CHAMPION_KILL.victimId == participant_id` 记录死亡；
- `ITEM_PURCHASED.participantId == participant_id` 记录购买；
- `ELITE_MONSTER_KILL` 记录目标事件；
- `participantFrames` 提供分钟级 gold、CS、XP、level 快照。

近期均值只使用非 `None` 值。Timeline 缺失的 `deaths_before_15=None` 不会被当作零死亡加入均值。

## 6. 需求到源码、测试、CI 和限制

| 要求 | 源码 | 测试 | 公共证据 | 限制 |
|---|---|---|---|---|
| Riot ID→公开账号→比赛 | `riot_client.py`、`player_summary.py` | `test_stage1_pipeline.py` 使用 Fake 链路 | 当前全量 CI持续覆盖；CI 不调用 Riot | Fake 不能证明真实 Key、区域、限流或网络可用；PUUID 也不证明账号归属 |
| 确定性单局指标 | `match_analyzer.py::analyze_match_detail` | 代表性 Fake 对局贯穿 Stage 1/产品测试 | 5P-3 `4bd5c83` / Actions `31998739178` 重新公开验证 app-level 领域服务 | 缺逐公式参数化测试；赛后统计不是录像细节 |
| Timeline 事件和未知语义 | `analyze_match_timeline()`、`timeline_fallback()` | `test_short_match_and_missing_timeline_are_explicit`；下游 unknown 测试 | 同上，并由当前全量 CI继续回归 | 空集合表示没有可用事件集合，不得把 unknown 描述为实际零事件 |
| 短局不污染聚合 | `process_match()`、`aggregate_recent_matches()` | Stage 1 和 recent-review domain tests | 5P-3 exact-SHA CI | 300 秒是配置策略，不是 Riot 官方统计定律 |
| 版本化 Summary | `summary_schema.py` | 拒绝无版本文档；下游 Skill/Harness 校验 | 当前 CI | v1.0 校验是手写必要字段检查，不是完整 JSON Schema 覆盖所有叶子 |
| 静态中文名称 | `data_dragon.py`、术语模块 | 术语/名称测试 | 当前 CI | Data Dragon 不是动态 Meta，也不等于国服 API |
| 确定性报告与 CLI 复用 | `report_renderer.py`、两个 CLI | renderer 字节一致测试 | 5P-3 public CI | CLI 的 Data Dragon 装配可能访问缓存/网络；报告只做中等粒度复盘 |
| 下游模型不能直接发布 | Stage 1 历史脚本 + `app/harness/` | Harness 状态机、评测、降级测试 | 当前 `pytest` 和 Harness dry-run；6B-2 基线 `0c13a58` / Actions `32301852042` 仍全量通过 | 当前真实领域 Provider 质量仍未准入，确定性 fallback 才是可靠下界 |

原始领域实现历史可见于 `8e6e729`、`b7a6a91`、`fba87ed` 和稳定化提交 `2f855cb`。这些
提交早于当前 exact-SHA CI 治理体系；因此它们证明演进来源，不应冒充当时已有公共 CI。

## 7. 可重复运行

### 7.1 无 Key、无网络的学习验证

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_stage1_pipeline.py `
  tests/test_recent_review_domain_services.py `
  tests/test_terminology_display.py `
  tests/test_name_naturalizer.py `
  -q
```

这些测试注入 Fake Riot/Data Dragon，验证控制流和边界，不证明线上 API。

只用仓库匿名 fixture 查看纯 renderer 输出，可运行：

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from app.lol.report_renderer import render_deterministic_report; p=Path('examples/fixtures/player_summary_demo.json'); d=json.loads(p.read_text(encoding='utf-8')); print(render_deterministic_report(d))"
```

### 7.2 需要真实外部 I/O 的人工运行

确认本地 `.env` 已配置、且你有权查询相应外服公开 Riot ID 后：

```powershell
.\.venv\Scripts\python.exe scripts\build_player_summary.py `
  --riot-id "<GAME_NAME>#<TAG_LINE>" `
  --count 10 `
  --queue 420
```

这会调用 Riot API，并可能通过 Data Dragon 读取网络或缓存。不要在 CI 中加入真实 Key，不要把生成的
玩家缓存提交到 Git。真实运行成功只说明当时的单次链路成功，不是可用性 SLA。

## 8. 失败、安全和范围边界

- `.env`、Riot Key、`data/cache/` 和真实玩家运行数据不得提交；
- `RiotClient` 是兼容旧 CLI 的薄传输层，真实产品入口应经过阶段 3 Tool Runtime 和阶段 6
  owner-scoped API，而不是直接暴露它；
- `player_summary.py` 当前会把本地异常文字写入 `timeline_error`/`failed_matches`，适合本地诊断，
  不应未经安全投影直接成为公网错误响应；
- Summary 只公开 PUUID 前缀，但 Riot ID 和对局 ID仍属于用户数据，公开样例必须匿名化；
- Riot ID→PUUID 表示公开账号可解析，不表示当前应用用户控制该账号；归属验证属于后续 Auth/RSO；
- 中国大陆国服不在当前 Riot 官方 routing 支持范围；`zh_CN` 只是 Data Dragon 语言；
- Match Detail/Timeline 不包含录像级操作上下文，不能判断具体走位、技能命中、沟通和心理；
- 小样本胜率和赢输差异只能作为复盘线索，不能称为稳定能力或因果；
- 阶段 1 不包含 Session、Memory、MCP、Multi-Agent 或生产部署。

## 9. 面试时可以和不可以怎样说

可以准确表述：

> 我把 LoL 事实计算放在确定性领域层：通过 Account-V1/Match-V5 获取公开赛后数据，
> MatchAnalyzer 计算 KDA、每分钟指标、参团和队伍占比，Timeline 单独提取死亡、购买和
> 目标事件；结果进入版本化 Player Summary。短局保留明细但排除聚合，Timeline 缺失保持
> unknown，不伪造为零。下游 Agent 只解释这些事实，不能自行重算或改写。

如果面试官问“为什么不把 Riot JSON 直接给模型”，可以回答：

> 计算型事实需要可重复和可测试。直接给模型会把取数、计算、解释和发布混在一起，数字错误
> 难以定位。稳定 Summary 还能让 Harness、Skill、API 和后续 Memory 在不依赖 Riot 原始字段的
> 情况下复用同一个领域合同。

不可以说：

- “Riot API 能证明这个外服账号属于用户”；
- “Data Dragon 提供当前英雄胜率和最佳出装”；
- “Timeline 可以完成录像级复盘”；
- “所有指标公式都有完备单元测试”；当前仍缺逐公式参数化覆盖；
- “真实 GLM Coach 已稳定上线”；真实领域模型质量目前仍未准入；
- “一次探针成功等于 API 长期稳定或项目已部署”。

一句话总结阶段 1：**RiftCoach 先把公开赛后数据变成有版本、有缺失语义、可回归的事实
Artifact，再允许 Agent 在受控边界内解释。**
