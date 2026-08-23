# 8E Productization Preflight

> 本文是 8E 的前置审查和真实验证门，不是 React 实现报告，也不表示正式 Auth、
> SSE、备份或公网部署已经完成。

## 1. 初学者要解决的问题

8D 已经像“在实验台上验证发动机规则”：给定带来源的 typed facts，融合内核能正确
处理版本冲突、过期、缺失和降级。但产品还要回答两个现实问题：

1. 当前 Riot API 和 OP.GG MCP 真实链路是否能各自返回可用数据，并能通过各自 adapter
   进入同一份 EvidenceBundle？
2. 用户到底在分析谁：自己的外服账号，还是公开的职业选手/高手账号？

8E preflight 先回答边界和证据，再开始前端。前端会慢慢做，不能用漂亮动画掩盖身份、
地区、证据或隐私语义。

## 2. 当前证据

### 2.1 OP.GG 真实验证：已通过

本次授权窗口执行：

- endpoint：`https://mcp-api.op.gg/mcp`
- MCP protocol：`2025-06-18`
- server：`OP.GG MCP Server 1.0.0`
- selected tool：`lol_list_lane_meta_champions`
- tool calls：1
- position：`top`
- fact count：3
- result：`passed`
- body-free evidence digest：`24b49ea9eb9c4c6c6ee682ad21309c7a643fbdde70a8ea18ba8fdf1d26a8c1ec`

脱敏结果：[opgg_external_validation_2026-08-23.json](../../data/evaluation/results/mcp/opgg_external_validation_2026-08-23.json)。

限制仍然有效：`partial provenance`、`upstream_patch_unknown`、
`source_generated_at_unknown`、`upstream_freshness_unknown`；只允许
`current_snapshot_recommendation`，不能做 exact-patch attribution 或 historical
patch comparison。

### 2.2 Riot 真实验证：已通过

用户授权公开核验后，AutoGLM 与 OP.GG 公开页面交叉确认 `DK ShowMaker#KR1` 是当前
可查询的 KR 账号，并显示 Dplus KIA/ShowMaker 关联。以 `DK ShowMaker#KR1 / asia /
observed` 执行有界 Riot probe：

- Account-V1：1 次；
- 最近 Match ID：1 次，返回 1 局；
- Match Detail：1 次；
- 结果：`passed`；
- 真实 game version：`16.16.804.9184`；queue `420`；目标位置 `MIDDLE`；英雄 `Akali`；
  `6/9/12`；对局时长 `1925s`；
- PUUID 只保存 digest `9967ad74365538ce5af6106fa1c58f40ed034e039031cbc1a09d8f255a241333`。

脱敏结果：[riot_external_validation_2026-08-23-v2.json](../../data/evaluation/results/riot_external_validation_2026-08-23-v2.json)。
Key 读取次数记录为 1，但 Key 值、PUUID、Match ID 和原始 response 均未落盘。

### 2.3 真实两源 replay：暴露上游适配缺口

使用上面的 Riot typed projection，调用一次真实 OP.GG `mid` lane-meta 工具并尝试进入
8D `fuse_evidence()`。OP.GG 返回内容触发严格适配器的 `opgg_meta_result_invalid`，因此
本次没有创建 bundle。脱敏失败证据见
[riot_opgg_fusion_validation-2026-08-23.json](../../data/evaluation/results/riot_opgg_fusion_validation_2026-08-23.json)。

这不是 Riot 失败，也不是融合规则失败，而是一个真实上游响应没有满足当前冻结的
allowlisted grammar。当前选择保留 fail-closed 行为，先拿到受控 schema-drift 诊断和回归
样例，再决定是否扩大字段合同；不能用放宽解析器的方式追绿。

### 2.4 RQ-087 字段级 live 诊断与窄兼容裁决

新的明确授权窗口复用既有 Riot body-free projection，并执行一次 OP.GG `mid` replay。
结果仍被拒绝，但 ADR-0057 的诊断把失败收敛到 `Mid.rank_prev_patch`、field index 7、
AST `Name`；live response 的长度和摘要与受控 fixture 不同。脱敏结果见
[riot_opgg_fusion_validation_2026-08-23-v2.json](../../data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v2.json)。

ADR-0058 采用最小兼容：只在 `rank_prev` 和 `rank_prev_patch` 两个 nullable integer
字段接受精确小写 JSON `null`，立即归一化为 `None`。其他字段上的 `null`、`NULL`、
未知 `Name`、调用或表达式继续 fail closed。该窗口唯一 tools/call 已用于诊断，因此
离线修复和公共 no-I/O CI 不能冒充“修复后 live replay 已通过”。

RQ-088 生效后已执行一次修复后 replay：strict adapter 成功解析 10 条 `mid` facts，
并创建 bundle `69ed8a...fff1a`。bundle 仍为 `degraded/unjoined`，因为 Riot 样本 Akali
未命中当前 top-10 Meta，且本 replay 不含 Data Dragon/official patch；这属于显式 gap，
不是 parser/fusion 失败，也不改变 partial provenance 与 patch/freshness 限制。

## 3. 已发现的身份/地区缺口

- `POST /player-links` 已支持用户提交 Riot ID、routing region 和 `self|observed`。
- Conversation review 已能绑定稳定 player subject；不同 PUUID 要求新 Conversation。
- 最终 UI 尚没有 owner-scoped 的“我的账号/观察对象”档案列表与选择接缝。
- 旧 `/reviews/recent` 直接接受 Riot ID，Worker composition 的地区默认来自 `RIOT_REGION`
  （默认 `asia`），不能作为最终多地区 UI 的隐式来源。
- 需要清晰区分 `claimed_self` 与 `public_observed`，并在 UI 上显示未验证/公开观察标签。

## 4. 8E preflight 分批

### Batch A：真实外部验证

- [x] OP.GG initialize/list/call 有界 smoke；保存 body-free evidence。
- [x] Riot account/match 有界 smoke；`DK ShowMaker#KR1 / asia / observed`，3 次 Riot calls 通过。
- [x] 用脱敏 Riot typed output 尝试一次真实 `mid` OP.GG EvidenceBundle replay/fusion；失败被安全归类为 `opgg_meta_result_invalid`。
- [x] 将真实失败分类和 limitations 写入 body-free 结果，不修改 8D 规则。
- [x] 增加受控 schema-drift diagnostic 合同与不含原始 body 的回归 fixture；诊断只记录阶段、allowlisted 字段位置、AST 节点类型、长度和摘要。
- [x] 在新的明确外部授权窗口内重跑一次真实 mid replay，取得字段级 live diagnostic；结果定位到 `Mid.rank_prev_patch` / field 7 / AST `Name`，且 live digest/length 与 fixture 不同。
- [x] 依据 ADR-0058 用 red→green TDD 只接纳两个 nullable rank-history 字段上的精确小写 JSON `null`；其余 Name/字段/表达式继续拒绝。
- [x] RQ-088 下执行一次修复后最终 live replay；strict adapter 通过并创建 body-free bundle。具体 Akali Meta join 仍因 top-10 未命中而显式 degraded。

### Batch B：玩家档案合同

- [x] 采用 `Riot ID + routing_region + relationship_role` 输入。
- [x] 采用 `self/unverified_claim` 与 `observed/public_observed` 双关系语义。
- [x] ADR-0059、专用设计/TDD 实现 owner-scoped latest-success profile list/selection DTO 与 API；
  `player_profile_id` opaque/PUUID-free，Conversation 保留 strict legacy alias。
- [x] legacy endpoint required `routing_region`，Conversation 使用 SQL execution target，Worker exact-select
  四地区 client 并删除 ambient `RIOT_REGION`；`e844bdd` / Actions `32622696087` exact-SHA 三 job 全绿。

### Batch C：证据与产品 API

- [x] ADR-0060/专用设计冻结 EvidenceBundle PostgreSQL append-only revision、幂等 refresh 与 query-time expiry 投影。
- [x] 冻结 8C event replay → cursor SSE 的安全 DTO，不暴露 raw body/Prompt/Key。
- [x] 固定 `published/degraded/rejected/not_ready` 状态和 reason-code 优先级。
- [ ] 按 TDD 实现 0011/Repository、Evidence/Product API、SSE、composition/package 与八维证据，并完成 exact-SHA 公共闭环。

### Batch D：前端第一小批

- [ ] 先做信息架构、设计 token、真实状态矩阵和可访问性合同。
- [ ] 先做静态/fixture-backed screen，确认桌面/移动/键盘/reduced-motion。
- [ ] 再接 API、SSE、Auth；最后才加入入口叙事、视差和粒子动效。

### Batch E：部署与安全

- [ ] Auth/RSO、CORS/CSP、HTTPS、限流和密钥生命周期。
- [ ] backup restore/erase、公开隐私说明、依赖和许可证审计。
- [ ] Playwright 截图、无障碍扫描、性能 p50/p95 和失败注入。

## 5. 明确不做

- 不把 ShowMaker 或任何职业选手写成默认账号。
- 不为 CN routing 做静默 fallback。
- 不通过自动跨地区重试寻找账号。
- 不把一次真实验证称作生产 SLA 或长期数据新鲜度保证。
- 不在本轮编写大规模 React 页面或引入新的 Agent Runtime/Multi-Agent 框架。

## 6. 下一动作

1. 进入 Batch C：先冻结 EvidenceBundle 安全持久化/刷新/过期投影、8C event replay → SSE 安全 DTO 和
   `published/degraded/rejected/not_ready` 前端状态合同；
2. Batch C 完成独立教学、TDD、持久证据与 exact-SHA 公共门后，再进入 Batch D 的第一个
   静态/fixture-backed 前端小批次。

ADR-0058 最小修复已由 `83fde7d014aae8fdccf2ebd91929967868101075` / Actions
`32615340228` 完成 exact-SHA 三 job 公共闭环；RQ-088 的后续 live 复验现已独立通过。
frozen live-success evidence 又由 `efaccd9a8022f0d75e9baca5470450be6a1a3357` /
Actions `32615821339` 完成 exact-SHA 三 job 公共闭环。
玩家档案/显式路由 implementation/evidence `e844bdd673ee051568e8611160f6ba53e8c745c4` /
Actions `32622696087` 也已完成 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环。
