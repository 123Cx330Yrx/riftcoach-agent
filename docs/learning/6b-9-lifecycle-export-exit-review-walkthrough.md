# 6B-9 Lifecycle / Export / Session-Memory V1 退出复盘

## 1. 问题与原理

Memory 的可信终点不是“能写进去”，而是用户可以看见、导出、按明确范围删除，并且清理失败时正文不会重新
出现。跨 Conversation、Candidate、typed Memory、Plan 和 Progress 直接硬删容易被 FK 阻断，也可能产生部分
删除。因此 V1 采用 **hidden-before-cleanup**：同一 PostgreSQL 短事务先让全部目标记录对 owner 不可见并写入
不含正文的 deletion marker，提交后再做文件清理；清理失败只留下安全 reason，可幂等重试。

删除还有 provenance 边界。删除一次 Conversation 不自动等于忘掉用户已确认的长期 Memory；只有显式
`conversation_and_derived_memory` 才按来源一并隐藏。删除一个 player relationship 也不能误删 owner-global
Preference，更不能删除另一个 owner 对同一 PUUID 的私有关系。

## 2. 设计与实际实现

- `OwnerDataExport` 是 owner-scoped、schema 1.0、有界同步 snapshot；每 section 最多 500 条，超限
  `export_too_large`，不静默截断。
- export 保留 Candidate decision/provenance、typed version/supersedes、Plan/Progress 来源和 body-free Task/
  Artifact reference；模型 Prompt、Provider/Tool body、PUUID、Key、异常和 Artifact 正文不进入 DTO。
- `conversation_only` 隐藏 Conversation/Message；已确认 Candidate、Preference/Profile/Review、Plan/Progress 保留。
- `conversation_and_derived_memory` 还隐藏该 Conversation 来源的 Candidate、typed target、Plan 和 Progress。
- `relationship_private_data` 隐藏该 owner/relationship、其全部 Conversation/Message 与 player-scoped Memory；
  owner-global Preference、Task/Run/Artifact、全局 Player Subject/alias 不随之删除。
- Candidate、typed query/writer、training query/writer、Memory Context selector 都排除 `hidden_at`；隐藏的 active
  target 不占 partial unique。新链使用历史最大 version + 1，但不把隐藏记录写成 supersedes predecessor。
- retention 使用 injected clock 和 bounded batch；purge 按 Progress→Plan→typed target→Candidate→Message，
  FK 阻塞计数而不扩大级联删除。
- API 只有 `GET /owner-data/export`、`POST /owner-data/deletions`、`POST .../{marker_id}/retry`；owner 只能来自
  `ActorContext`，请求体额外 owner 字段直接 422。

## 3. 代码地图

| 责任 | 文件 |
|---|---|
| strict export/delete/marker/retention contracts | `app/lifecycle/models.py` |
| cleanup compensation 与 injected-clock orchestration | `app/lifecycle/service.py` |
| lifecycle marker ORM | `app/persistence/owner_data_lifecycle_records.py` |
| owner export、三 scope、retention、purge | `app/persistence/owner_data_lifecycle_repository.py` |
| 0009 hidden columns/index/constraint/marker migration | `migrations/versions/0009_owner_data_lifecycle.py` |
| hidden-aware Candidate/typed/training/Context seams | `app/persistence/memory_repository.py`, `typed_memory_writer.py`, `typed_memory_query_repository.py`, `training_writer.py`, `training_query_repository.py`, `memory_context_repository.py` |
| HTTP DTO、routes 与 deployment composition | `app/api/lifecycle_models.py`, `app/api/main.py`, `app/api/composition.py` |
| Linux installed-package vertical | `scripts/run_packaging_smoke.py` |

## 4. 数据与控制流

```text
ActorContext.owner_id + typed target + Idempotency-Key
→ strict command validates exactly one legal target
→ Repository locks owner target and checks idempotency tuple
→ one SQL transaction hides every selected row + inserts cleanup_pending marker
→ commit: all normal query/Context/export paths immediately exclude hidden rows
→ CleanupPort runs outside SQL transaction
   ├─ success → marker complete
   └─ failure → marker remains cleanup_pending + body-free cleanup_failed
→ retry re-loads marker by owner and repeats only cleanup/completion
```

Export 在只读短事务中组装 typed sections。它不读取 run files，也不调用 Riot/Provider。Retention 只改变可见性；
purge 等待 30 天后按 FK 顺序尝试物理删除，Conversation/Relationship 可因 Task 审计引用继续保留 hidden skeleton。

## 5. Session / Memory V1 退出矩阵

| checkpoint | 已证明 | 明确未声称 |
|---|---|---|
| 6B-1/2 | immutable PUUID subject、owner relationship、异步 Link | 正式 RSO verified self |
| 6B-3/4 | Conversation/ordered Message、schema 2.0 Task frozen identity | 通用聊天前端/SSE |
| 6B-5 | Candidate gate、pending/accept/reject、事务内 materializer | 模型可直接写长期 Memory |
| 6B-6 | Preference/Profile/Review typed targets、version/concurrency | owner/role 外推或 verified creation |
| 6B-7 | self-only Plan、Artifact-backed Progress、correction/trend | 因果诊断或模型猜测指标 |
| 6B-8 | run-scoped legal Context、body-free manifest、verified terminal turn | failed draft 作为 Assistant 历史 |
| 6B-9 | owner export、三 scope 删除、补偿、retention/purge | 法务级备份擦除或生产隐私 SLA |

跨批不变量：两 owner/两 Conversation/同 PUUID 仍隔离；claimed-self 与 observed 分开；没有 API 能创建
verified-self；Context 只接 legal visible records；Assistant 只有成功发布后写入；真实 Riot/Provider 调用仍为 0。

## 6. 验证与 package 证据

- pure：三 scope target shape、timezone/batch/section bounds、forbidden export keys、pending/complete marker；
- ORM/migration：hidden column、active partial unique、0009 upgrade/downgrade、CHECK/FK/index、metadata=head；
- PostgreSQL Repository：owner export、hidden exclusion、三 scope、idempotency replay/conflict、retention/purge 顺序；
- API：ActorContext owner、body override 422、404/409/202/200、安全 code-only failure；
- regressions：Candidate get 与 post-delete accept 边界、typed/training fresh-chain version、Context/terminal visibility；
- package schema 1.6：先导出 Conversation/Message/Preference/Plan，再执行 `conversation_only`；Conversation/
  Message 404，Preference/Plan 各保留 1 条，`external_riot_provider_calls=0`。

本机无 PostgreSQL/Docker，因此真库 migration/Repository 与 Linux installed-package 证据必须由同一实现 SHA 的
公共 `postgres-migrations`/`packaging-smoke` 补齐；公共三 job 全绿前 coverage 继续是 planned。

## 7. Runbook

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_owner_data_lifecycle_models.py `
  tests\test_owner_data_lifecycle_service.py `
  tests\test_owner_data_lifecycle_records.py `
  tests\test_owner_data_lifecycle_migrations_postgres.py `
  tests\test_owner_data_lifecycle_repository_postgres.py `
  tests\test_owner_data_lifecycle_api.py -q

$env:DATABASE_URL='postgresql+psycopg://riftcoach:test@localhost/riftcoach'
.\.venv\Scripts\python.exe -m alembic upgrade head --sql > $null
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

运维 retention/purge 当前只通过内部 Service 调用，不是公开 HTTP 管理端点。公开 API 的同步 export 上限适合 V1
作品集规模；超限应改走未来异步归档设计，不能临时提高上限或截断。

## 8. 失败、安全与边界

- target 不存在或跨 owner：统一 not-found；idempotency key 同 tuple replay，不同 scope/target 返回 conflict；
- SQL 任一步失败：隐藏与 marker 一起 rollback；不会留下部分 scope；
- cleanup 失败：数据已不可见，marker 保持 pending；retry 只能由同 owner 操作；
- export 任一 section 超限或 DTO 出现 forbidden key：整个 export fail closed；
- `conversation_only` 后 Candidate 历史可看，但新 accept/写入因 source Conversation hidden 而拒绝；
- relationship 删除不级联 Task/Run/Artifact/Player Subject，也不误删 owner Preference；
- purge FK 阻塞保留数据并计数，不关闭约束、不扩大 cascade；
- 没有正式 Auth/RSO/HTTPS/RLS、异步大导出、备份副本擦除、SSE/前端、MCP、Multi-Agent、Redis/向量库或
  真实 Riot/Provider 调用。这些仍按阶段 7/8 和新证据门处理。

## 9. 面试准确表述

可以说：

> 我为 PostgreSQL Session/Memory 做了集中式 owner lifecycle：删除在一个短事务里先隐藏跨表数据并写入
> body-free marker，事务外清理失败可幂等补偿；导出是有界、版本化、owner-scoped snapshot。三种删除 scope
> 明确区分只删对话、连同来源 Memory、以及退出单个 player relationship，并用真实 PostgreSQL migration/
> repository tests 和 Linux package smoke 验证 owner 隔离与失败安全。

不可以说“GDPR/生产隐私合规已完成”“备份已擦除”“正式 Auth 已上线”“异步大导出已实现”或“向量 Memory 已
采用”。V1 证明的是合同、事务可见性、补偿和可审计边界，不是法律结论或互联网生产 SLA。
