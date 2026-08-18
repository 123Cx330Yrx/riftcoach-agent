# 6A FastAPI + PostgreSQL 持久任务基座 Exit Matrix

## 用途

本矩阵逐条核对 ADR-0038 与 6A 正式设计。测试数量只能说明回归规模，不能替代“承诺—实现—证据—限制”
映射。`公开证据待定` 的行在 exact-SHA Actions 成功前不能用于关闭 6A。

## 退出矩阵

| 承诺 | 实现证据 | 测试证据 | 公开证据 | 限制 | 退出裁决 |
|---|---|---|---|---|---|
| PostgreSQL 是唯一生产 task 语义；migration 可逆 | `app/persistence/`、`migrations/`、`alembic.ini` | migration/config/constraint 真库测试 | `854e52d` / Actions `32043214500` | 本机无 Docker；SQLite 不作替代 | 已满足 |
| owner-scoped 幂等 create/query、task_id/run_id 与四态不可逆状态机 | `app/tasks/models.py`、`service.py`、`fingerprint.py`、PostgreSQL Repository | task model/service/repository 并发测试 | `012b066` / Actions `32046532695` | fixed local owner 不是 Auth | 已满足 |
| 两 Worker 原子 claim、短事务、ownership/CAS 与退避 | `task_repository.py`、`app/workers/review_worker.py`、`polling.py` | `FOR UPDATE SKIP LOCKED`、双领、旧 owner、backoff 测试 | `55e369e` / Actions `32097561436` | 无 lease/自动 retry/reclaim | 已满足 |
| SQL run_id 贯穿 Application/Runtime/Harness/Artifact；完整证据后才 success | `recent_review_executor.py`、Application、receipt/query、Trace/Artifact | reconciliation 与真实 PostgreSQL 离线产品纵向 | `41ac9c1` / Actions `32102522662` | Fake Provider 只证明接线，不证明模型质量 | 已满足 |
| hard crash 只按 immutable receipt 补 success；否则 recovery-required/人工 CAS | `app/tasks/reconciliation.py`、`scripts/recover_review_task.py` | receipt 缺失/损坏、人工确认、迟到 Worker 测试 | `41ac9c1` / Actions `32102522662` | 自动 fencing/reclaim 延至阶段 8 | 已满足 |
| POST 202、task/run/report owner 查询、lifespan 与 live/ready | `app/api/main.py`、`actor.py`、`composition.py` | Fake/API 与真实 PostgreSQL API 测试 | `2492951` / Actions `32106378542` | production 缺 Auth Provider 时 fail closed | 已满足 |
| 默认 CORS、body-free logs/errors、容量、7/90/30 retention 与安全删除 | API/Task security、retention、deletion、observability | 安全、生命周期、并发 capacity 与删除补偿测试 | `31d5e60` / Actions `32138025724` | 正式 Auth/HTTPS/备份尚未实现 | 已满足当前 6A 范围 |
| warm create/query `<300ms`、queued→claim `<2s` 的作品集基线 | `tests/test_task_performance_postgres.py` | PostgreSQL 17/Python 3.11，8+8 样本 | `31d5e60` / Actions `32138025724` | 不是公网 SLA、Agent 延迟或模型质量 | 已满足当前 NFR |
| 真实 Worker 在 claim 前完成 DB/Data Dragon/RAG/Prompt composition，并校验 Riot/Provider 配置与构造合同 | `app/workers/composition.py`、`scripts/run_review_worker.py --check` | `tests/test_worker_composition.py` 与相邻回归 | `b0f61ca` pytest/真库绿；runtime profile 尚未真实启动 | 当前只准入 Zhipu 产品基线；预检不冒充在线凭据或领域质量验证 | 本地通过，package 公共待定 |
| 非 root Linux 镜像、migration/API/Worker Compose 与 no-I/O smoke | `Dockerfile`、`.dockerignore`、`compose.yaml`、`run_packaging_smoke.py` | packaging contract；隔离 project 的 `up --wait` + module one-off smoke | `d8c5063` / `32146113582` 定位 direct-script Alembic root 漂移；module fix 待 CI | 本机无 Docker；不放宽 migration readiness | 未满足，待新 Linux CI |
| 完整回归、RAG、compileall、Harness/Secret/SDK/governance 与 diff 门 | workflow 与标准门命令 | 聚焦 `48 passed`；完整 `1102 passed, 27 skipped, 110 subtests passed`；两套 RAG 满门槛；Harness dry-run published | `b0f61ca` pytest `1100/27 skipped/110 subtests`、PostgreSQL `51 passed` 成功；新诊断 SHA 待定 | CI 不读取 Key、不调用 Riot/Provider | 本地通过，待新 exact-SHA CI |

## 明确 deferred

- Session/Memory、`user_id + conversation_id` 长期 Coach 状态；
- 正式 Auth/HTTPS、限流、安全响应头、备份和公网 SLA；
- SSE/前端；
- lease/heartbeat/reclaim、自动 retry、cancel/resume 和 fencing；
- 真实 Provider 领域质量准入、自动模型路由；
- MCP、Multi-Agent、LangGraph、DAG 或新 Agent SDK。

## 当前退出裁决

`keep-open-pending-exact-sha-linux-ci`。本地 composition、完整回归与横向门已经通过，但新增 Linux
Docker/Compose job 尚未产生 exact-SHA 公共结果，因此 6A 仍是 `in_progress`。
