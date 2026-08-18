# 6A FastAPI + PostgreSQL 持久任务模型实施计划

> **For Codex:** 按 canonical 一次只执行一个 6A 子阶段；每个子阶段先按 `AGENTS.md` 恢复状态、完成
> 初学者教学与 TDD，再提交/推送/exact-SHA CI。不要使用 subagent，不要自动跨越下一检查点。

**Goal:** 将 5P 同步文件型近期复盘切片演进为 PostgreSQL 持久、owner-scoped、幂等、可由独立
polling Worker 执行的异步任务 API，同时复用现有 Application/Runtime/Harness/Artifact。

**Architecture:** 保持同步 Python 模块化单体。FastAPI 用短事务创建/查询任务，独立 Worker 用
`FOR UPDATE SKIP LOCKED` 领取任务，在事务外调用现有 Application Service，再以 Artifact/receipt
证据条件更新终态。PostgreSQL 是任务控制面，Artifact/Trace 是内容数据面。

**Tech Stack:** Python 3.11、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、psycopg 3、PostgreSQL、
pytest、Docker Compose、GitHub Actions。

---

## 全局执行规则

1. 本计划只在 `6A-entry-design` 完成 exact-SHA 公共闭环后执行；
2. 每次用户“继续”只授权 canonical 指向的一个 6A 子阶段；
3. 每个子阶段必须先解释问题、原理、数据/控制流、测试和限制；
4. 所有数据库生产语义使用真实 PostgreSQL；SQLite 不进入依赖或关键测试；
5. 所有 CI/默认测试无 Riot/Provider I/O，不读取 `.env`；
6. 现有 `RecentReviewApplicationService`、`AgentRuntimeV1` 和 `ReviewHarness` 不复制；
7. 任何新发现会先更新 ADR/plan/canonical，不能在实现中默默扩 scope；
8. 每个子阶段完成本地门后提交、推送并等待 exact-SHA CI，成功才交接下一步。

## 6A-1：PostgreSQL Foundation

### 目标

建立 SQLAlchemy/Alembic/PostgreSQL 基础设施与 initial task migration，只证明“数据库与 schema
可靠存在”，不实现 Repository、Worker 或 API 行为。

### 文件

- Modify: `pyproject.toml`
- Modify: `.env.example`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/0001_create_review_tasks.py`
- Create: `app/persistence/__init__.py`
- Create: `app/persistence/config.py`
- Create: `app/persistence/database.py`
- Create: `app/persistence/task_record.py`
- Create: `tests/test_database_config.py`
- Create: `tests/test_task_migrations_postgres.py`
- Modify: `.github/workflows/tests.yml`
- Create: `compose.yaml`

### 合同草图

```python
@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    pool_size: int = 5
    pool_timeout_s: int = 5

def build_engine(settings: DatabaseSettings) -> Engine: ...
def build_session_factory(engine: Engine) -> sessionmaker[Session]: ...
```

ORM row 只表达 ADR-0038 冻结字段与 constraints；`request_payload`/body-free references 使用 JSONB，
时间使用 `TIMESTAMP WITH TIME ZONE`，status 使用受 CHECK 约束的字符串，不提前实现 Repository 方法。

### TDD 步骤

1. 写 `test_database_config.py` 红灯：缺 URL、SQLite URL、非法 pool 参数 fail closed；
2. 运行 `python -m pytest tests/test_database_config.py -q`，预期因模块不存在失败；
3. 实现最小 settings/engine/session factory，重跑通过；
4. 写 migration 红灯：空 PostgreSQL DB upgrade head 后存在 task table、索引、unique/check constraints；
5. 启动 `docker compose up -d postgres`，设置测试 URL；
6. 运行 `python -m alembic upgrade head` 与 migration test，预期通过；
7. 在临时 DB 验证 downgrade base → upgrade head 可重复；
8. CI 新增独立 PostgreSQL integration job，不改变现有 no-I/O pytest 语义；
9. 运行完整门禁并提交。

### 验收命令

```powershell
python -m pytest tests/test_database_config.py -q
python -m pytest tests/test_task_migrations_postgres.py -q
python scripts/check_project_governance.py
python -m compileall -q app scripts tests
git diff --check
```

预期：配置测试和真实 PostgreSQL migration 测试通过；CI 无 SQLite、Key、Riot/Provider I/O。

### 不在本批

Repository、task create/query、claim、Worker、FastAPI 新 endpoint、retention/delete。

## 6A-2：Task Contract & Repository

### 目标

实现 Provider-neutral task 合同、状态不变量、owner-scoped idempotent create/query 与 PostgreSQL
Repository，不启动 Worker。

### 文件

- Create: `app/tasks/__init__.py`
- Create: `app/tasks/models.py`
- Create: `app/tasks/ports.py`
- Create: `app/tasks/fingerprint.py`
- Create: `app/tasks/service.py`
- Create: `app/persistence/task_repository.py`
- Create: `tests/test_task_models.py`
- Create: `tests/test_task_service.py`
- Create: `tests/test_task_repository_postgres.py`
- Modify: `app/persistence/task_record.py`
- Add migration only if 6A-1 schema must be corrected; never edit an already public migration silently.

### 合同草图

```python
class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class CreateReviewTaskCommand(BaseModel):
    owner_id: str
    idempotency_key: str
    request: RecentReviewProductRequest

class ReviewTaskView(BaseModel):
    task_id: UUID
    run_id: str
    status: TaskStatus
    publication_status: str | None
    report_available: bool
```

`owner_id` 在 service boundary 已是 trusted value，但 model 仍校验长度/字符；公共 HTTP 不接受该字段。
fingerprint 由 canonical JSON bytes + task kind/schema version 计算 SHA-256。

### TDD 步骤

1. 红灯固定四态合法/非法投影、safe code、UTC 时间和 body-free view；
2. 红灯固定 canonical fingerprint 对字段顺序稳定、对语义差异敏感；
3. 用 Fake Repository 固定同 owner/key/fingerprint 复用、不同 fingerprint 冲突；
4. 固定 owner 3/global 50 非终态容量；terminal row 不占 active capacity；
5. 实现 domain/service 最小逻辑；
6. 真库测试 unique、rollback、JSONB、owner query、not-owned/not-found 等价；
7. 保证 run_id/task_id 在 create transaction 一次生成且 immutable；
8. 完整回归、提交与 exact-SHA CI。

### 验收命令

```powershell
python -m pytest tests/test_task_models.py tests/test_task_service.py -q
python -m pytest tests/test_task_repository_postgres.py -q
python -m pytest -q
python scripts/check_project_governance.py
git diff --check
```

### 不在本批

claim、Worker、Application 调用、HTTP endpoint、真实 Auth。

## 6A-3：Atomic Claim & Polling Worker

### 目标

实现原子 claim、Worker ownership/CAS、polling backoff/jitter 和 graceful shutdown，Executor 先用 Fake。

### 文件

- Create: `app/workers/__init__.py`
- Create: `app/workers/polling.py`
- Create: `app/workers/review_worker.py`
- Create: `scripts/run_review_worker.py`
- Modify: `app/tasks/ports.py`
- Modify: `app/persistence/task_repository.py`
- Create: `tests/test_worker_polling.py`
- Create: `tests/test_task_claim_postgres.py`
- Create: `tests/test_review_worker.py`

### 接口草图

```python
class TaskRepository(Protocol):
    def claim_next(self, *, worker_id: str, now: datetime) -> ReviewTask | None: ...
    def succeed(self, *, task_id: UUID, worker_id: str, terminal: TaskTerminal) -> bool: ...
    def fail(self, *, task_id: UUID, worker_id: str, reason: str) -> bool: ...

class ReviewTaskExecutor(Protocol):
    def execute(self, task: ReviewTask) -> TaskTerminal: ...
```

### TDD 步骤

1. Fake Repository 红灯固定 poll idle backoff、jitter bounds、stop event 与不忙轮询；
2. 真库并发红灯：两个独立 Session/线程以 barrier 同时 claim N tasks；每 task 恰好一个 owner；
3. 实现 `FOR UPDATE SKIP LOCKED` + deterministic order；
4. 红灯固定旧 worker/错误 status 的 terminal CAS 返回 false 且不改变 row；
5. 红灯固定 Fake Executor success/failure、graceful shutdown 和安全错误；
6. 实现 Worker loop；不捕获后自动重跑；
7. 验证 idle polling 不持有 transaction/connection；
8. 完整回归、提交与 exact-SHA CI。

### 并发测试原则

使用 barrier、独立 Session 与有限 join timeout；不使用长 sleep 猜锁顺序。测试失败必须清楚区分
double claim、deadlock、timeout 和 fixture/connection 错误。

### 不在本批

真实 Application/Runtime、Artifact reconciliation、lease/heartbeat/fencing、自动 retry/cancel。

## 6A-4：Application & Artifact Integration

### 目标

把持久 task 的 run_id 贯穿现有 compiler/Application/Runtime，建立 SQL/Artifact terminal 协调、
receipt-proven reconciliation 与受限人工恢复。

### 文件

- Modify: `app/product/recent_review.py`
- Modify: `app/product/recent_review_service.py`
- Modify: `app/product/run_receipts.py`
- Create: `app/tasks/recent_review_executor.py`
- Create: `app/tasks/reconciliation.py`
- Create: `scripts/recover_review_task.py`
- Modify: `app/workers/review_worker.py`
- Modify: `tests/test_recent_review_product_compiler.py`
- Modify: `tests/test_recent_review_application_service.py`
- Create: `tests/test_task_reconciliation.py`
- Create: `tests/test_task_reconciliation_postgres.py`
- Create: `tests/test_task_product_vertical_postgres.py`

### 关键兼容改动

`RecentReviewRuntimeRequestCompiler.compile()` 与 `RecentReviewApplicationService.review()` 增加 keyword-only
trusted `run_id` 接缝。旧 5P 测试可以保留 factory 默认行为，但 6A production executor 必须传入 SQL
预留 run_id；重复生成或 mismatch fail closed。

### TDD 步骤

1. 红灯：显式 run_id 贯穿 compiler、Runtime request、Artifact binding、result、receipt；
2. 红灯：SQL run_id 与 Runtime/receipt mismatch 在 terminal update 前拒绝；
3. 用现有本地 fixture/RAG、Fake Provider、真实 Runtime/Harness 完成 queued→terminal 离线纵向；
4. 覆盖 published/degraded/rejected 都映射 task succeeded；Runtime/Application failure 映射 task failed；
5. 红灯：Artifact 已完整/SQL running 时 reconciler 补齐 success；
6. 红灯：无 receipt hard crash 不自动 fail/replay，只投影 recovery-required；
7. 红灯：受限恢复命令必须匹配 task/status/worker，并记录 safe reason；
8. 红灯：迟到/旧 Worker 不能覆盖 manual failed；
9. 完整回归、提交与 exact-SHA CI。

### 不在本批

lease、heartbeat、自动 reclaim、真实 Provider/Riot I/O。

## 6A-5：Async FastAPI & Composition

### 目标

将同步 recent POST 演进为 202 task contract，加入 task query、trusted ActorContext、production-like
composition/lifespan 与 live/ready；仍不提供公网 Auth。

### 文件

- Modify: `app/api/main.py`
- Modify: `app/api/__init__.py`
- Create: `app/api/actor.py`
- Create: `app/api/composition.py`
- Create: `app/api/task_models.py`
- Modify: `tests/test_fastapi_adapter.py`
- Create: `tests/test_async_task_api.py`
- Create: `tests/test_async_task_api_postgres.py`
- Create: `tests/test_api_composition.py`

### HTTP 合同

```text
POST /reviews/recent            202
GET  /tasks/{task_id}           200/404
GET  /runs/{run_id}             200/404/409/500
GET  /runs/{run_id}/report      200/404/409/500
GET  /health/live               200
GET  /health/ready              200/503
```

POST 从 header 接收受限 `Idempotency-Key`；owner 只由 ActorContext dependency 提供。公共 response 不含
worker_id、SQL path、exception 或 body。

### TDD 步骤

1. 先更新 OpenAPI/response 红灯，明确 5P 同步 schema 的版本演进；
2. Fake Task Service 测 202、422、409、503 与 safe body；
3. 真库 API 测 create/replay/query、owner 404、状态投影和 report not-ready；
4. readiness 测 DB down、migration behind/head；liveness 不依赖外部 Provider；
5. composition import/OpenAPI 不读 Key、不连网络；lifespan 明确创建/关闭 engine/session；
6. `local-owner` 只在显式 local/test profile；production 无 Auth Provider fail closed；
7. 完整回归、提交与 exact-SHA CI。

### 不在本批

JWT/OAuth、Session、Memory、SSE、正式前端和公网部署。

## 6A-6：Security, Lifecycle & NFR

状态：已由 `31d5e60` / Actions `32138025724` 完成 exact-SHA pytest、真实 PostgreSQL 与性能基线公共验证（2026-08-18）。

### 目标

实现本阶段已经冻结且属于 task 基座的安全/生命周期/NFR：默认 CORS、脱敏、背压、retention/delete、
metrics/benchmark。正式 Auth/HTTPS 仍是公开部署前后续硬门。

### 文件

- Create: `app/tasks/retention.py`
- Create: `app/tasks/deletion.py`
- Create: `scripts/purge_expired_task_data.py`
- Modify: `app/api/composition.py`
- Modify: `app/api/main.py`
- Modify: `app/workers/polling.py`
- Create: `tests/test_task_retention.py`
- Create: `tests/test_task_lifecycle_postgres.py`
- Create: `tests/test_task_api_security.py`
- Create: `tests/test_task_observability.py`
- Create: `tests/test_task_performance_postgres.py`
- Modify: `SECURITY.md`
- Modify: `.env.example`

### TDD 步骤

1. CORS 默认无 allow origin；production wildcard+credentials 配置拒绝；
2. 日志捕获测试确保 Riot ID、Prompt、report、exception body 和 fake secrets 不出现；
3. owner/global capacity race 在真库下仍受约束；
4. retention 用 injected clock 测 7/90/30 天边界，不等待真实时间；
5. terminal delete 立即隐藏资源，Artifact/SQL cleanup 幂等；active delete 返回 conflict；
6. 文件删除失败留下安全补偿状态，可重试但不恢复用户可见内容；
7. benchmark warm-DB create/query p95 与 claim delay；报告样本数/环境，不把 CI 抖动误判为模型质量；
8. 结构化 metrics/logs 只含 allowlisted metadata；
9. 完整回归、安全门、提交与 exact-SHA CI。

### 不在本批

用户 Memory 删除、跨机备份、正式 Auth、反向代理 HTTPS、99.9% SLA。

## 6A-7：Packaging & Exit Review

### 目标

形成可在本地/CI 重建的 API+Worker+PostgreSQL 包，完成 6A exit matrix 与公开证据；不直接公网部署。

### 文件

- Create: `Dockerfile`
- Modify: `compose.yaml`
- Modify: `.dockerignore`
- Modify: `.github/workflows/tests.yml`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Create: `docs/plans/2026-08-XX-6a-exit-matrix.md`
- Create: `docs/plans/2026-08-XX-6a-exit-review.md`
- Create: `tests/test_packaging_contract.py`
- Modify canonical/governance files required by `AGENTS.md`

### TDD/验收步骤

1. 冻结 Compose health/dependency contract：postgres → migration/readiness → API/Worker；
2. 构建镜像，检查 image 不含 `.env`、本地 runs/cache、Key 或测试私有数据；
3. `docker compose up` 后执行 migration、live/ready、POST 202、task poll 的 Fake/no-I/O smoke；
4. GitHub Actions 保持原 pytest/RAG/Pi frozen gates，并增加 PostgreSQL migration/concurrency/API/Worker job；
5. 运行完整 pytest、两套 RAG、compileall、Harness boundary/dry-run、Secret/tracked-data、governance、
   Docker/Compose smoke 和 diff check；
6. exit matrix 将每条 ADR-0038/设计承诺映射到代码、测试、公开 CI 或明确 deferred；
7. 不满足 NFR/安全/恢复硬门时保持 6A open；不能用文档说明替代缺失实现；
8. 提交、推送并等待 exact-SHA Actions success；
9. 成功后关闭 6A，只交接下一个既有阶段 6 checkpoint 准备状态，不自动实施 Session/Memory。

## 每个子阶段的标准本地门

根据改动比例执行以下全集或子集，并在 progress 中记录真实结果：

```powershell
python -m pytest <focused tests> -q
python -m pytest -q
python scripts/evaluate_rag_retrieval.py --provider hybrid --output tmp/rag-v1-evaluation.json --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0
python scripts/evaluate_rag_retrieval.py --provider hybrid --cases data/evaluation/rag_v1_holdout_cases.json --require-independent --output tmp/rag-v1-holdout-evaluation.json --min-recall 1.0 --min-mrr 1.0 --min-ndcg 1.0 --max-no-answer-fpr 0.0 --min-abstention-accuracy 1.0 --min-citation-support 1.0
python -m compileall -q app scripts tests
python scripts/check_project_governance.py
git diff --check
```

PostgreSQL 子阶段还必须运行 Alembic 和真库测试；CI/Docker 命令以当时公开 workflow/compose 的真实
入口为准，若计划命令与仓库实现漂移，先修计划并记录，不得跳过验证。

## 最终边界

6A 完成只证明持久异步 task API 基座，不证明：

- Session/长期 Memory 或个性化进展比较；
- 公网 Auth、限流、HTTPS、备份与 SLA；
- SSE/正式前端；
- 自动 lease/cancel/resume/retry；
- 新 Provider 领域质量；
- Multi-Agent、MCP 或 LangGraph。
