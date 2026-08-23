# 8E Batch C Evidence / Product API 实施计划

## Task 1 — Pure contracts first

- 先写 `tests/test_evidence_snapshot_contracts.py` 红灯；
- 冻结 full storage round-trip、nested Meta digest、snapshot digest、expiry/usable claims 和四态 projector；
- 实现 `app/evidence/storage.py`，不得读取环境、网络或数据库。

## Task 2 — PostgreSQL 0011 + Repository

- 先写 metadata/migration/PostgreSQL repository 红灯；
- 新增 `evidence_bundle_snapshots`、复合 task FK `ON DELETE CASCADE`、revision/refresh 唯一约束、
  digest/时间/JSON size CHECK 和 latest index；
- 实现 append/replay/conflict、task row lock revision、owner-scoped latest、strict rehydrate/tamper fail-closed；
- 验证并发 refresh 只得到连续 revision，task 删除级联清除 snapshot。

## Task 3 — Product service and HTTP DTO

- 先写 evidence/product API 红灯；
- 实现 `EvidenceProductService` 与 safe DTO；
- 增加 `GET /runs/{run_id}/evidence` 和 `GET /runs/{run_id}/product-state`；
- 固定 404/409/500/503 allowlist、四态 reason code、OpenAPI 和 forbidden-field scan。

## Task 4 — Cursor SSE

- 先写 encoder/stream/API 红灯；
- 实现 `Last-Event-ID`/after_cursor、TaskEventResponse JSON frame、keepalive、终态关闭、有限连接与安全错误；
- 增加 `/tasks/{task_id}/events/stream` owner preflight 与响应 headers；
- 证明 reconnect 不重复且不暴露 owner/worker/checkpoint/token/operation/body。

## Task 5 — Composition and package vertical

- lifespan 绑定 `PostgresEvidenceSnapshotRepository`、product service 与 SSE service；app import/构造保持 no-I/O；
- 扩展 composed API、真实 PostgreSQL vertical 和 Linux package smoke，外部 Riot/OP.GG/Provider/LLM calls 为 0；
- migration head、downgrade/reupgrade 和 `alembic check` 必须通过。

## Task 6 — Durable teaching/evidence and local gates

- 创建 `docs/learning/8e-evidence-product-api-walkthrough.md`，把八维 coverage 继续挂在 8E planned 组；
- 同步 canonical、active plan、requirements/roadmap/amendment/capability/project decisions；
- 运行 focused、真实 PostgreSQL、完整 pytest、两套 RAG、Harness、compileall、pip/YAML、SDK/Secret/
  tracked-data、governance 与 `git diff --check`。

## Task 7 — Independent public closure

- 创建一个独立 implementation/evidence commit 并 push；
- 等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；
- 公共闭环后独立更新状态，8E coverage 仍保持 `planned`，唯一下一内部批才是 Batch D 静态/
  fixture-backed 前端；不提前进入 Auth/backup/deployment。
