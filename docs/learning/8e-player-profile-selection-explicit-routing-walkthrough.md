# 8E Batch B：玩家档案选择与显式 Riot 路由 walkthrough

## 1. 问题与原理

这一批解决的不是“怎么把一个 Riot ID 填进表单”，而是三个容易混淆的问题：

- Riot ID 是可改名的显示别名；
- PUUID 是内部稳定的 Riot 身份；
- routing region 决定请求实际发往 `americas/asia/europe/sea` 哪台 regional 服务。

如果客户端反复重传别名、Worker 再从 `RIOT_REGION=asia` 猜路由，美服或欧服账号就可能被送到错误
服务器，Conversation/Memory 也可能绑定到和本次网络请求不同的玩家。Agent 产品里的通用原则是：
**稳定身份由服务端在 owner scope 内恢复，外部 I/O 路由必须成为逐请求的可审计合同。**

## 2. 设计与实现

ADR-0059 选择复用成功的 Player Link，而不是新增 profile/default 表：

1. `GET /player-profiles` 只投影 owner 自己、仍 active、已有成功解析证据的关系；
2. 同一 relationship 多次成功 link 只保留最新显示别名；queued/failed/hidden 不可选；
3. `player_profile_id` 是 opaque UUID，当前复用 `relationship_id`，不向客户端暴露 PUUID；
4. Conversation 以 `player_profile_id` 为新字段，旧 `relationship_id` 仅作严格输入兼容别名；
5. legacy `/reviews/recent` 必须显式提交 allowlisted routing region；
6. Conversation review 使用 SQL execution target 已固定的 region；
7. Worker 预建四个 regional Riot Client，再由 request/target exact-select；没有默认和自动探区。

没有新增 migration，因为当前没有“全局默认档案、昵称、排序或独立档案生命周期”的真实 Bad Case。

## 3. 代码地图

| 职责 | 主要位置 |
|---|---|
| 安全 profile 领域投影 | `app/players/models.py` |
| profile query port/service | `app/players/ports.py`、`app/players/service.py` |
| latest-success owner-scoped SQL | `app/persistence/player_repository.py` |
| HTTP DTO 与 `GET /player-profiles` | `app/api/player_models.py`、`app/api/main.py` |
| Conversation selection 兼容 | `app/api/conversation_models.py` |
| legacy request 的 required region | `app/product/recent_review.py` |
| Application/Task region 传播 | `app/product/recent_review_service.py`、`app/tasks/recent_review_executor.py` |
| exact regional client selector | `app/lol/player_summary.py` |
| Worker/Compose 去 ambient region | `app/workers/composition.py`、`compose.yaml` |
| Linux no-I/O 产品纵向 | `scripts/run_packaging_smoke.py` |

## 4. 数据与控制流

### 4.1 档案选择路径

```text
trusted Actor owner_id
  → GET /player-profiles?limit=N
  → latest succeeded PlayerLink per relationship
  → active owner relationship cross-check
  → PUUID-free PlayerProfilePage
  → POST /conversations { player_profile_id }
  → owner-scoped relationship lookup
  → immutable Conversation player subject/role
```

### 4.2 复盘路由路径

```text
legacy: explicit request.routing_region ─┐
                                         ├→ RoutedRiotPlayerSummaryBuilder
conversation: SQL execution target.region┘  → exact regional Riot Client → Riot API
```

地区参与 legacy task payload 和 fingerprint。旧 queued task 若没有地区会以 `task_input_invalid` 安全失败，
不会读取历史环境默认来猜。

## 5. 验证证据

- 首轮 TDD 在 collection 阶段因缺 `PlayerProfilePage/PlayerProfileView` 红灯；
- owner scope、latest-success 去重、queued/hidden 排除、observed verification 与 PUUID-free projection
  由 service/API/真实 PostgreSQL 测试覆盖；
- missing/CN/unknown region、不同 region fingerprint、legacy 与 Conversation 两条传播路径、错误 region
  无 fallback、`RIOT_REGION=cn` 不改变 Worker 配置均有回归；
- 本机补齐 Docker Desktop 与 PostgreSQL 17 后，公共真库同构集合为 `187 passed`；
- 最终聚焦回归为 `268 passed, 1 warning`；带真库的完整回归为
  `1842 passed, 1 skipped, 1 warning, 127 subtests passed`。唯一 skip 是 Windows 当前账号不可创建
  symlink，不是业务或数据库缺口；
- 本机 Linux Compose smoke 已返回 schema `1.6`、`external_riot_provider_calls=0`，并通过非 root、无
  `.env/tests/cache/runs/reports/tmp` 镜像边界；临时 Compose 容器、网络和 volume 已清理；
- 两套 RAG、Harness dry-run、compileall、pip、YAML、SDK/Secret/tracked-data、governance 与 diff 门均通过。

## 6. 运行手册

本机 Docker Desktop 已使用 WSL2 后端；持久测试容器名为 `riftcoach-local-postgres`，只绑定
`127.0.0.1:54329`。用户级 `RIFTCOACH_TEST_DATABASE_URL` 指向该本地 PostgreSQL 17。

常用验证顺序：

```powershell
docker start riftcoach-local-postgres
$env:RIFTCOACH_TEST_DATABASE_URL = [Environment]::GetEnvironmentVariable(
  'RIFTCOACH_TEST_DATABASE_URL', 'User'
)
$env:DATABASE_URL = $env:RIFTCOACH_TEST_DATABASE_URL
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pytest -q
```

Docker Desktop 未启动时先启动它；不要把本地测试 URL 或密码写入仓库 `.env`。exact-SHA GitHub
Actions 仍是独立 Linux/PostgreSQL/package 公共关闭门。

## 7. 失败、安全与边界

- profile API 不返回 PUUID、owner ID、link task ID、fingerprint、Key 或 upstream body；
- 跨 owner、未知或 hidden selection 继续使用既有 body-free not-found；
- `cn` 不在 Riot regional allowlist；不自动探区或跨区重试；
- self 仍是 `unverified_claim`，observed 仍是 `not_applicable/public_observed` 语义；本批不实现 RSO verified；
- ShowMaker 只保留为历史真实验证样本，不是默认账号；
- 本批没有实现 profile 昵称/排序/删除按钮/默认项，也没有实现前端、Auth、SSE、EvidenceBundle store、
  HTTPS、备份或公网部署。

## 8. 面试表述

推荐表述：

> 我把“玩家身份”和“Riot 网络路由”拆开处理。用户先通过异步 Player Link 保存多个外服账号或公开
> 观察对象，产品列表只暴露 owner-scoped 的 opaque profile ID；Conversation 再由服务端恢复稳定 subject。
> legacy 请求和 Conversation execution target 都显式携带 regional routing，Worker 用四客户端 exact-select，
> 没有环境默认或自动探区。真实 PostgreSQL、完整回归和 Linux Compose smoke 共同验证了 owner 隔离、
> 去重、失败关闭与部署纵向；我没有把这批合同工作夸成正式 Auth、前端或生产部署。
