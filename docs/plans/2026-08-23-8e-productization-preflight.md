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
- [ ] 对真实 mid 响应做受控 schema-drift 诊断并补一个不含原始 body 的回归样例；未完成前不放宽 parser。

### Batch B：玩家档案合同

- [x] 采用 `Riot ID + routing_region + relationship_role` 输入。
- [x] 采用 `self/unverified_claim` 与 `observed/public_observed` 双关系语义。
- [ ] 设计 owner-scoped profile list/selection DTO 与 API。
- [ ] 设计 legacy endpoint 的兼容/迁移策略，禁止地区隐式错配。

### Batch C：证据与产品 API

- [ ] 设计 EvidenceBundle 的安全持久化/刷新/过期投影。
- [ ] 设计 8C event replay → SSE 的安全 DTO，不暴露 raw body/Prompt/Key。
- [ ] 为 `published/degraded/rejected/not_ready` 固定前端状态合同。

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

1. 先诊断真实 OP.GG `mid` 响应与现有 grammar 的差异，形成安全 schema-drift case；
2. 决定是按证据扩大 allowlist，还是保留该工具的 degraded/unavailable 状态；
3. 冻结 owner-scoped player profile list/selection API 合同；
4. 之后再进入 8E 的第一个静态/fixture-backed 前端小批次。
