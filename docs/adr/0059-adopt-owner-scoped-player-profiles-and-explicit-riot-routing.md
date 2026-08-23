# ADR-0059：采用 owner-scoped 玩家档案与逐请求 Riot 路由

- 状态：Accepted for `8e-productization` Batch B（2026-08-23）
- 关联：ADR-0039、ADR-0040、ADR-0041、ADR-0056、RQ-061、RQ-062、RQ-063、RQ-086

## 背景

`POST /player-links` 已能把显式 `Riot ID + routing_region + relationship_role`
解析为稳定的 player subject 和 owner relationship；Conversation 创建也已经用
owner-scoped relationship 固定玩家。但是产品尚没有一个安全、去重、可选择的玩家
档案列表。旧 `POST /reviews/recent` 又只接收 Riot ID，实际 Riot regional routing
来自 Worker 的环境变量 `RIOT_REGION`，默认 `asia`。这可能把美服或欧服账号送到错误
服务器，且调用方无法从任务合同审计真实路由。

## 方案比较

| 方案 | 裁决 | 原因 |
|---|---|---|
| 复用成功 Player Link 形成 owner-scoped profile projection | 采用 | 已有稳定 relationship、subject、alias、地区和角色；无需迁移或第二套身份状态 |
| 新建 profile/default-selection 表 | 暂不采用 | 当前没有跨设备默认选择、排序、昵称或固定偏好的真实 Bad Case；会提前制造同步语义 |
| 客户端每次重传 Riot ID + 环境地区 | 拒绝为主路径 | 身份可变、地区不可审计，容易与 Conversation/Memory 的稳定 subject 脱节 |

## 决策

1. `GET /player-profiles` 返回 trusted Actor owner 下、由成功 Player Link 解析且仍为
   active relationship 的最新去重档案。`player_profile_id` 是 opaque UUID，在当前
   实现中映射既有 `relationship_id`；它不是 PUUID，也不新增默认选择状态。
2. 公共档案只包含显示 Riot ID、routing region、relationship role、verification
   status 和最近成功解析时间；禁止暴露 owner ID、PUUID、link fingerprint、Key、
   raw Riot/MCP body 或内部 task state。
3. Conversation 的新请求字段使用 `player_profile_id`。服务端仍由 trusted owner scope
   解析 relationship → subject/region；旧 `relationship_id` JSON 名只作为输入兼容别名，
   不能与新字段同时提交。
4. 旧 `/reviews/recent` 若继续使用，必须显式提交 allowlisted `routing_region`。该字段
   写入 Task fingerprint/payload，并在 Worker 中逐请求选择对应 Riot Client；缺失、CN、
   未知地区或旧的无地区 queued payload 一律 fail closed，绝不读取环境默认或自动探区。
5. Conversation-bound review 使用 PostgreSQL 保存的 execution target routing region，
   同样逐请求选择 Riot Client。调用正文和模型不能覆盖该路由。
6. Worker 只从环境读取 Riot Key，不再读取 `RIOT_REGION`。部署组合预建四个无 I/O、
   allowlisted regional clients；request/target 决定精确选择，找不到即配置失败。

## 数据与控制流

```text
trusted Actor owner
  → GET /player-profiles
  → succeeded Player Link + active owner relationship（latest per profile）
  → PUUID-free PlayerProfileResponse
  → POST /conversations { player_profile_id }
  → owner-scoped relationship lookup
  → fixed Conversation subject/role
  → conversation review target supplies exact routing_region
  → regional Riot client

legacy POST /reviews/recent
  → explicit routing_region in strict request/task fingerprint
  → regional Riot client
```

## 验证与安全边界

- 两个 owner 只能看到自己的 profile；queued/failed/hidden/重复成功 link 不产生重复可选项；
- profile 列表和 OpenAPI 不出现 PUUID/Key/raw body；self 与 observed 显示正确验证语义；
- `player_profile_id` 选择继续复用 Conversation 的 owner-scoped not-found 行为；
- legacy 请求缺地区、`cn` 或多余内部字段返回 422；Task payload/fingerprint 包含地区；
- legacy 与 Conversation 两条执行路径都把正确地区传给 routed summary builder；
- Worker 配置不再含 `riot_region`，`RIOT_REGION=asia` 不能覆盖请求/subject 路由。

## 后果与限制

- 本批不实现 profile 自定义昵称、排序、删除按钮、跨设备默认项或 verified ownership；
- 不实现正式 Auth/RSO、SSE、前端、EvidenceBundle store、备份或公网部署；
- 旧 queued schema 1.0 task 若没有 routing region 会安全失败，不能用历史环境值猜测；
- profile ID 当前复用 relationship identity，未来若真的需要独立 profile 生命周期，必须
  以迁移、兼容和 Bad Case 另立 ADR，不能静默换义。
