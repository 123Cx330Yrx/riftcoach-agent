# 6B-7 Training Plan / Progress 实现复盘

## 1. 问题与原理

一次模型建议不等于长期训练计划，一次聊天中的“感觉变好了”也不等于进度。6B-7 把二者拆开：

- Plan 是用户确认的、版本化的目标与 metric allowlist；
- Progress 是绑定完整 terminal Review Task/final Artifact 的不可变测量事件；
- Trend 是纯函数对相同 metric 最近样本的比较，不推断原因、心理或习惯。

pending Training Plan Candidate 就是草稿。只有用户 accept 后才在同一事务物化 active Plan，因此没有
第二套 draft CRUD 绕过 6B-5 write gate。

## 2. 设计与实际实现

实现采用 ADR-0044 的两张表：`training_plans` 和 `training_progress_events`。Plan 是 self-only，
每个 owner relationship 由 partial unique index 保证最多一个 active。Progress 只能引用 active Plan
中列出的 metric，并必须同时绑定 Candidate、Conversation identity、schema 2.0 Review Task、run 和
final Artifact digest。

Plan 替换会把旧 Plan 变为 superseded 并插入新版本；complete/abandon 只改变 active Plan 的终态和
status Candidate。Progress 正常测量并行保留；纠错新增 event 并把指定旧 event 变为 superseded。

## 3. 代码地图

| 责任 | 文件 |
|---|---|
| strict Plan/Progress payload、view、trend | `app/memory/training_models.py` |
| Candidate materializer 与 writer ports | `app/memory/training_materializers.py`, `training_ports.py` |
| production 五类 materializer registry | `app/memory/composition.py` |
| ORM 与 0007 schema/trigger | `app/persistence/training_records.py`, `migrations/versions/0007_create_training_plan_progress.py` |
| 同事务 Plan/Progress writer | `app/persistence/training_writer.py` |
| owner-scoped query/trend | `app/persistence/training_query_repository.py`, `app/memory/training_service.py` |
| HTTP DTO 与两个只读 GET | `app/api/training_models.py`, `app/api/main.py`, `app/api/composition.py` |
| pure/API/PostgreSQL tests | `tests/test_training_*.py` |

## 4. 数据与控制流

### Plan

```text
POST Candidate (training_plan/user_structured_input/self)
→ gate requires_confirmation
→ POST accept by trusted owner
→ Candidate row lock + active Conversation
→ TrainingPlanMaterializer strict parse
→ advisory lock(owner,relationship)
→ active self relationship check
→ expected-version / supersede / insert or terminal transition
→ Candidate accepted + target reference in the same commit
```

### Progress

```text
deterministic Training Progress Candidate
→ source task/run/artifact identity check
→ active self Plan + metric allowlist row lock
→ succeeded + published/degraded + report_available + final_report digest gate
→ append Progress event
→ optional old event active→superseded
→ Candidate accepted in the same commit
```

查询只接受 trusted owner 和 relationship UUID。Repository 先验证 active self relationship，再返回 bounded
Plan/history 或当前 active Plan 的 Progress；趋势按稳定顺序和 Plan direction/tolerance 计算。

## 5. 验证证据

- pure contract：blank/control、extra、重复/未知 metric、bool/NaN/Infinity、naive time、observed 越权；
- materializer：kind/key/provenance、同 Session、UUID reference、无 commit/rollback；
- metadata/migration：两表、复合 FK、CHECK、partial unique、trigger、可逆 head；
- PostgreSQL writer：Plan 首写/替换/终态/stale version、Artifact fail closed、Progress correction/rollback；
- Service/API：trusted owner、bounded history/filter、404/503、两个 GET-only OpenAPI、无私有 body/path；
- 相邻：Candidate gate/service、6B-6 typed query、API composition、package baseline。

本机没有 PostgreSQL/Docker，所以 migration/writer 的真库案例必须明确 skip；只有 exact-SHA 公共
`postgres-migrations` job 能补齐 trigger、FK、transaction 和并发证据。公共闭环前 coverage 保持 planned。

## 6. Runbook

聚焦：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_training_models.py tests\test_training_materializers.py tests\test_training_records.py tests\test_training_migrations_postgres.py tests\test_training_repository_postgres.py tests\test_training_service.py tests\test_training_api.py -q
```

完整与治理：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

写 Plan/Progress 仍使用已有 Candidate POST/accept；目标表没有 PATCH。查询：

```text
GET /memory/players/{relationship_id}/training-plan
GET /memory/players/{relationship_id}/training-progress?metric_key=deaths_before_15
```

## 7. 失败、安全与边界

- observed/cross-owner/non-active relationship 在应用和数据库双拒绝；
- system 不能 accept requires-confirmation Plan；用户 confidence 不提供权限；
- non-terminal、failed、rejected、无 report、非 final_report 或 digest mismatch 的 Task 不能写 Progress；
- 目标 payload、identity、Artifact provenance 不可原地修改；纠错必须新 event；
- API 不返回 PUUID、Candidate ID/payload、Artifact path/body、SQL 或原始异常；
- 趋势响应只有 metric、数值、delta、方向、样本数和枚举结果，不含因果/心理叙述；
- 本批不实现 Memory-aware Context/assistant terminal、lifecycle/export、正式 Auth/RSO、SSE/前端、
  Redis/向量库、MCP、Multi-Agent 或真实 Riot/Provider 调用。

## 8. 面试准确表述

可以说：

> 我把训练计划建模为用户确认、self-only、每关系单 active 的版本化合同，把训练进度建模为绑定完整
> Review Task/final Artifact 的不可变事件。Candidate acceptance、Plan/Progress materialization 在同一个
> PostgreSQL 事务中；partial unique、复合外键和 trigger 提供第二道防线。纠错追加 superseding event，
> 趋势只做确定性数值比较，避免把相关性或模型推断写成长期事实。

不能说：已经证明训练导致了指标改善、已正式验证 Riot 账号所有权、已生产化 Auth/SLA，或已经实现
Memory-aware Context、生命周期导出和前端。
