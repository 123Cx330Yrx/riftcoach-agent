# 8E Batch B：玩家档案选择与显式 Riot 路由设计

## 1. 问题与原则

产品需要回答“owner 正在分析哪个外服玩家，以及应该访问哪个 Riot regional
endpoint”。Riot ID 是可改名的显示别名；PUUID 是内部稳定身份；routing region 决定
网络目的地；三者不能由环境默认混成一个值。

本设计遵守两个原则：

1. **稳定身份由服务端恢复**：客户端选择 opaque profile ID，服务端在 trusted owner
   scope 内恢复 relationship、subject 和 region。
2. **网络路由属于请求/subject 合同**：每次 Riot 调用都使用显式 allowlisted region，
   不从环境猜测，不自动跨区重试。

## 2. 范围

本批实现：

- 成功 Player Link 的 owner-scoped、去重、bounded profile list；
- PUUID-free profile DTO；
- Conversation 创建使用 `player_profile_id`，兼容旧 `relationship_id` 输入名；
- legacy recent review 要求显式 region；
- Conversation review 使用 SQL execution target region；
- Worker 的四地区 routed Riot summary builder。

本批不实现 UI、默认档案、档案昵称/排序、Auth/RSO、SSE、EvidenceBundle persistence、
HTTPS、备份或部署。

## 3. 组件设计

### 3.1 Profile projection

`PlayerProfileView` 是安全领域投影，字段为：

- `player_profile_id`：opaque selection ID；
- `riot_id`：最近一次成功确认的显示别名；
- `routing_region`；
- `relationship_role`；
- `verification_status`；
- `last_resolved_at`。

PostgreSQL Repository 从 `player_link_tasks` 选择 owner 下 `succeeded` 行，对
`relationship_id` 按 `finished_at/link_task_id` 取最新一条，再与 active
`owner_player_relationships` 交叉核对。这样 queued/failed/hidden 不可选择，重复 link
不会重复显示，也不需要新表。

### 3.2 Selection

`GET /player-profiles?limit=...` 从 `ActorContext.owner_id` 建立查询。Conversation 请求
接受 `player_profile_id`，并把它作为既有 relationship identity 交给 Repository；跨 owner
或 hidden profile 继续得到 body-free 404。没有“当前默认 profile”这一全局可变状态。

### 3.3 Explicit routing

`RecentReviewProductRequest` 增加 required `routing_region`。地区参与 request payload 与
fingerprint。Application Service 的 `build`/`build_by_puuid` 接缝都显式携带地区。
Conversation 路径的地区来自 `ConversationReviewExecutionTarget`，legacy 路径来自严格
HTTP DTO。

`RoutedRiotPlayerSummaryBuilder` 持有四个显式 regional client，以 exact key 选择；没有
default。Worker composition 删除 `RIOT_REGION` 设置，只保留 Riot Key。

## 4. 错误与兼容

- profile owner/ID 不可用：404 `conversation_not_found` 或空列表；
- profile Repository 故障：503 `service_unavailable`；
- missing/unknown/CN routing：422 `request_invalid`；
- 旧无 region task：Worker `task_input_invalid`，不回退；
- 新旧 Conversation selection 字段同时提交：422；
- raw upstream/network 错误仍由既有 Application safe mapping 处理。

## 5. 测试矩阵

1. pure model：profile shape、role/verification、无 PUUID、bounded page；
2. service：owner query、limit、invalid owner、repository failure；
3. API：可信 Actor、profile list、new/legacy selection alias、cross-owner not-found；
4. PostgreSQL：success-only、latest dedupe、hidden exclusion、two-owner isolation；
5. product/task：region required/allowlisted、payload/fingerprint sensitivity；
6. application/worker：legacy request region 与 SQL target region 均正确传递；
7. composition：无 ambient `riot_region`，四地区 client 无 I/O 构造，错误 region 无 fallback；
8. focused、adjacent、完整回归、PostgreSQL、package、governance 与 exact-SHA CI。
