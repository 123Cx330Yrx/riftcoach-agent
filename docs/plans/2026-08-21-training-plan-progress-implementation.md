# 6B-7 Training Plan / Progress Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 self-only、用户确认的 Training Plan，以及由完整 final Artifact 支撑的不可变 Progress 事件和确定性趋势。

**Architecture:** 复用 6B-5 Candidate acceptance transaction 与 6B-6 typed materializer seam；新增独立 Plan/Progress pure contracts、两张 PostgreSQL 表、同 Session writer 和 owner-scoped query。PostgreSQL 约束负责身份/唯一性/不可变，纯函数负责 payload 与趋势语义。

**Tech Stack:** Python 3.11、Pydantic v2、SQLAlchemy 2、Alembic、PostgreSQL 17、FastAPI、pytest。

---

### Task 1: Pure Plan/Progress contracts and trend

**Files:** Create `app/memory/training_models.py`; test `tests/test_training_models.py`.

1. 先写 strict envelope、action、metric allowlist、finite value、self-only shape、progress correction 和趋势红灯。
2. 运行 `python -m pytest tests/test_training_models.py -q`，确认缺少模块失败。
3. 实现最小 Pydantic contracts 与无 I/O `compare_training_trend()`，重跑聚焦测试。

### Task 2: Candidate materializers

**Files:** Create `app/memory/training_materializers.py`, `app/memory/training_ports.py`; modify `app/memory/composition.py`; test `tests/test_training_materializers.py` and `tests/test_memory_typed_composition.py`.

1. 红灯冻结 Plan/Progress kind、同一 Session writer、目标 UUID 和安全错误。
2. 实现两个 materializer，并把 production registry 从三类扩为五类。
3. 证明构造 no-I/O、registry immutable，旧三类行为不变。

### Task 3: ORM and reversible migration 0007

**Files:** Create `app/persistence/training_records.py`, `migrations/versions/0007_create_training_plan_progress.py`, `tests/test_training_records.py`, `tests/test_training_migrations_postgres.py`; modify `migrations/env.py`, `.github/workflows/tests.yml`.

1. 先写 metadata/migration 红灯：两表、复合 FK/CHECK、partial unique、索引、trigger、upgrade/downgrade/re-upgrade。
2. 实现 ORM 与 0007；生成 offline SQL 并通过 metadata head 检查。
3. 本机无 PostgreSQL 时必须显式 skip；把真库文件加入 blocking job。

### Task 4: Transactional writer and Artifact gate

**Files:** Create `app/persistence/training_writer.py`, `tests/test_training_repository_postgres.py`; modify `tests/memory_candidate_postgres_support.py`.

1. 红灯覆盖 self-only、用户确认、一个 active Plan、expected version、complete/abandon、source Candidate replay。
2. 红灯覆盖 task identity、succeeded/publication/report/final Artifact digest、metric allowlist、correction、并发与 rollback。
3. 在 Candidate Repository 的同一 Session 中实现 advisory/row locks；writer 不 commit/rollback、不做 I/O。
4. 失败映射为既有安全 disposition，Candidate 保持 pending。

### Task 5: Owner-scoped query Service and API

**Files:** Create `app/persistence/training_query_repository.py`, `app/memory/training_service.py`, `app/api/training_models.py`, tests; modify `app/api/main.py`, `app/api/composition.py`.

1. 红灯冻结 active/history Plan、bounded Progress/metric filter、stable order/trend、owner 404 和 503。
2. 实现 Repository/Service/API；不增加 target PATCH，写入继续走 Candidate。
3. 生产 lifespan 绑定真实 query；import/OpenAPI 保持 DB/Key/network no-I/O。

### Task 6: Package vertical and durable evidence

**Files:** Modify package smoke/tests and canonical governance; create `docs/learning/6b-7-training-plan-progress-walkthrough.md`.

1. Linux smoke 扩展 Candidate→active Plan→Artifact-grounded Progress→query，外部调用保持 0。
2. walkthrough 补齐八维证据，公共 CI 前 coverage 保持 planned。
3. 跑聚焦、相邻、完整 pytest、RAG development/holdout、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff 门。
4. 独立提交/推送实现，等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 全绿。
5. 单独状态收尾把 6B-7/coverage 置 complete，再进入已由 RQ-071 授权的 6B-8；不得提前实现 6B-8。

## 验收矩阵

| 维度 | 必须证明 |
|---|---|
| 权限 | self-only，observed/cross-owner 在 Service 和 DB 双拒绝 |
| 计划 | 用户确认、一个 active、版本替换、complete/abandon |
| 进度 | allowlisted metric、finite value、完整 final Artifact 精确绑定 |
| 纠错 | 新事件 supersede 旧事件，不原地覆盖 |
| 趋势 | 稳定纯函数、方向/tolerance、无因果/心理推断 |
| 事务/并发 | Candidate+target 同 commit、rollback、replay、双 writer |
| API/安全 | owner-scoped、bounded、body/path/PUUID/异常不泄露、无 PATCH |
| 证据 | 本地门禁、八维 walkthrough、真实 PostgreSQL/Linux exact-SHA CI |
