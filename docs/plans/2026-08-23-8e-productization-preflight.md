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

### 2.2 Riot 真实验证：等待测试身份

仓库 `.env` 中存在 Riot Key 且未被输出；仓库没有硬编码 ShowMaker，也没有发现用户
提供的测试 Riot ID。Riot 半边不能猜账号执行，必须由用户给出准确的：

```text
Riot ID: gameName#tagLine
routing region: americas | asia | europe | sea
```

执行前后都不把 Key、PUUID 或原始 response 写入结果文件。

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
- [ ] Riot account/match 有界 smoke；等待用户提供测试 Riot ID + routing region。
- [ ] 用脱敏 typed output 做一次 Riot + OP.GG EvidenceBundle replay/fusion。
- [ ] 将真实失败分类和 limitations 写入结果，不修改 8D 规则。

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

1. 用户提供一个准确的测试 Riot ID 和 regional routing；
2. 执行一次 body-free Riot Account/Match gate；
3. 将 Riot typed digest 与本次 OP.GG evidence 做一次离线融合 replay；
4. 冻结 player profile list/selection API 合同；
5. 之后再进入 8E 的第一个小前端批次。
