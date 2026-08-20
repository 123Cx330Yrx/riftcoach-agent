# Memory Candidate Write Gate Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Build a server-derived, owner-isolated Memory Candidate control plane with a deterministic gate and a
transactional typed-materializer seam, without creating concrete long-term Memory tables.

**Architecture:** A strict `app.memory` domain/service layer creates pending proposals only. PostgreSQL derives the
Conversation identity, owns terminal transitions, and invokes a registered local typed materializer inside the same
short transaction. The production registry is empty until 6B-6, so acceptance fails closed instead of treating a
receipt as Memory.

**Tech Stack:** Python 3.11, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 17, FastAPI, pytest.

---

## Task 1：治理与设计冻结

**Files:**

- Modify: `docs/requirements_change_log.md`
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Create: `docs/adr/0042-use-transactional-typed-materializer-for-memory-candidates.md`
- Create: `docs/plans/2026-08-20-memory-candidate-write-gate-design.md`

**Steps:**

1. 将 RQ-068 改为已执行并追加 RQ-069；只授权 6B-5。
2. 比较万能表、receipt、中间态和 typed materializer；ADR 选择最后一种。
3. 冻结状态、schema、数据流、API、失败、安全、测试和面试边界。
4. 运行 `python scripts/check_project_governance.py`；预期通过。

## Task 2：Candidate pure contracts 与 deterministic gate

**Files:**

- Create: `app/memory/__init__.py`
- Create: `app/memory/models.py`
- Create: `app/memory/gate.py`
- Test: `tests/test_memory_candidate_models.py`
- Test: `tests/test_memory_candidate_gate.py`

**Steps:**

1. 先写 enum、payload bounds、canonical SHA/fingerprint、状态 shape 红灯。
2. 运行两个测试文件，确认缺少 `app.memory` 的真实红灯。
3. 最小实现 strict/frozen models；payload canonical UTF-8 不超过 8192 bytes。
4. 写 Gate 角色/来源矩阵红灯，尤其 confidence=1 的 model 仍需确认、observed 禁止私人类型。
5. 最小实现纯 Gate，无数据库/网络/clock I/O。
6. 运行聚焦测试，预期全绿。

## Task 3：Service、Port 与防御性投影

**Files:**

- Create: `app/memory/ports.py`
- Create: `app/memory/service.py`
- Test: `tests/test_memory_candidate_service.py`

**Steps:**

1. 用 Fake Repository 写 create/replay/conflict/not-found/gate-reject 红灯。
2. 写 get/reject/expire/accept actor policy 与 Repository 坏投影红灯。
3. 实现 Candidate ID/clock/fingerprint、allowlisted service errors 和 body-safe view。
4. 保证 public structured create 固定 provenance，客户端不能伪造 producer/identity。
5. 运行聚焦测试，预期全绿。

## Task 4：0005 migration 与 ORM

**Files:**

- Create: `app/persistence/memory_records.py`
- Modify: `migrations/env.py`
- Create: `migrations/versions/0005_create_memory_candidates.py`
- Test: `tests/test_memory_candidate_migrations_postgres.py`
- Test: `tests/test_memory_candidate_records.py`

**Steps:**

1. 写 metadata/schema 名称、可逆迁移、CHECK/FK/trigger 与 direct SQL 红灯。
2. 实现 ORM 和 migration；constraint/index 名称保持 PostgreSQL 63 字符以内。
3. 为 Conversation Message 与 Review Task 添加 source identity unique key，再建立 Candidate composite FK。
4. trigger 冻结 identity/proposal/provenance，限制终态不可逆。
5. 运行 offline SQL、ORM 聚焦；本机真库允许明确 skip，不能冒充通过。

## Task 5：owner-scoped create/query Repository

**Files:**

- Create: `app/persistence/memory_repository.py`
- Test: `tests/test_memory_candidate_repository_postgres.py`

**Steps:**

1. 写 server-derived tuple、active Conversation/relationship、source ownership、幂等/冲突红灯。
2. 实现 relationship→Conversation 锁顺序和 owner/key advisory lock。
3. 验证不同 owner、隐藏/归档 Conversation、source mismatch 不产生 row。
4. 验证 public observed Gate 规则即使 direct service command 也不能绕过。

## Task 6：终态与 transactional materializer

**Files:**

- Modify: `app/memory/models.py`
- Modify: `app/memory/ports.py`
- Modify: `app/persistence/memory_repository.py`
- Test: `tests/test_memory_candidate_materialization_postgres.py`

**Steps:**

1. 在测试 schema 创建专用 typed target，写同事务成功红灯。
2. 写 missing materializer、materializer exception/坏 reference、rollback 红灯。
3. 写并发双 accept、accepted replay、terminal conflict、reject/expire replay 红灯。
4. 实现 immutable registry 和 `materialize(session,candidate)` protocol；生产默认空 registry。
5. 确认 materializer 只获得同一 Session，不允许 Repository 在 callback 前改变 Candidate 终态。

## Task 7：薄 API、composition 与 no-I/O

**Files:**

- Create: `app/api/memory_models.py`
- Modify: `app/api/main.py`
- Modify: `app/api/composition.py`
- Test: `tests/test_memory_candidate_api.py`
- Modify: `tests/test_api_composition.py`

**Steps:**

1. 先冻结四条 route、strict OpenAPI 和 safe DTO 红灯。
2. 实现 trusted ActorContext、Idempotency-Key、空 decision body、allowlisted errors。
3. composition 构造 PostgreSQL Repository + empty materializer registry；import/OpenAPI 不读 DB URL/Key、不联网。
4. 证明生产 accept 返回 target unavailable 且 Candidate 保持 pending。

## Task 8：CI/package、walkthrough 与退出闭环

**Files:**

- Modify: `.github/workflows/tests.yml`
- Modify: `scripts/run_packaging_smoke.py`（仅在需要最小纵向证据时）
- Create: `docs/learning/6b-5-memory-candidate-write-gate-walkthrough.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: canonical/roadmap/capability/decisions/history/active-plan files

**Steps:**

1. 将 0005/memory Repository/materializer 真库测试加入 blocking PostgreSQL job。
2. package smoke 只证明 no-I/O Candidate pending/reject 或 fail-closed accept；不伪造 Memory 成功。
3. 补八维 walkthrough：原理、设计、代码地图、流、验证、runbook、安全、面试表述。
4. 跑聚焦、相邻、完整 pytest、RAG、Harness dry-run、compileall、secret/SDK/YAML/governance/diff 门。
5. 暂存并复核 cached diff，提交、推送，等待 exact-SHA 三 job。
6. 公共全绿后才把 coverage/6B-5 改为 complete，并只交接 6B-6 prepared/waiting authorization。
