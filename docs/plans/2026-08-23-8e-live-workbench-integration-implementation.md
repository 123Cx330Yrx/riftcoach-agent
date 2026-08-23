# 8E Live Workbench API/SSE Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 fixture-backed Rift Command Center 接到 owner-scoped profile/task/run/Product/Evidence/Training
与 cursor SSE，同时补齐 latest review locator、Recent Summary HTTP 和 typed Evidence schema，且不让异步
响应串档案、不从 Markdown/fixture 发明产品事实。

**Architecture:** FastAPI 新增薄 profile→latest review locator 和 Recent Summary projection，收紧现有
Evidence OpenAPI shape；浏览器通过 same-origin `/api`、exact decoders、generation/AbortController guard 与
单 EventSource 组合已有资源，再映射到 fixture/live 共用的不可变 Workbench view。后端仍是 owner/task/run
身份真源，不新增 BFF 聚合表、缓存、队列或外部调用。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy/PostgreSQL 17、React 19、TypeScript 7、
Vite 8、原生 EventSource、Motion、Radix Dialog、`react-markdown@10.1.0`、Vitest、Playwright/axe。

---

## 实施不变量

- 本计划只执行 RQ-095 live integration；不进入 Auth/RSO、部署、完整入口/Timeline/Training、OP.GG breadth
  或真实 fusion golden slice。
- 每个 profile selection 先关闭旧 EventSource、abort 旧 fetch、清空旧内容；晚到结果必须通过
  generation + profile + task + run 四重身份检查。
- SSE transport、客户端资源错误与 Product State 是三条独立状态线。
- 浏览器不保存 owner/token/Key，不放宽 CORS，不请求 Riot/OP.GG/Provider/LLM。
- fixture 只有显式 `?scenario=` 才可用；默认页面必须走 live controller。
- 先红后绿；实现提交前保留真 PostgreSQL、浏览器 no-I/O、bundle、a11y 与完整公共门。

### Task 1: 建立 latest-review pure contract 与服务

**Files:**

- Create: `app/product/latest_review.py`
- Modify: `app/product/__init__.py`
- Test: `tests/test_latest_profile_review_service.py`

**Step 1: 写 pure 红灯**

覆盖：合法 profile 无 review 返回 `latest_review=None`；active/failed/cancelled/succeeded 都可成为最新项；
repository not-found 映射 `player_profile_not_found`；repository failure/integrity drift 映射 body-free
`latest_review_unavailable`；输入必须是 UUID profile 和安全 owner。

定义最小合同：

```python
class LatestProfileReview(BaseModel):
    task_id: UUID
    run_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    publication_status: TaskPublicationStatus | None
    report_available: bool

class LatestProfileReviewResult(BaseModel):
    player_profile_id: UUID
    latest_review: LatestProfileReview | None
```

Repository port 只暴露 `get_latest(owner_id, player_profile_id)`，不加入现有 `TaskRepository` Protocol。

**Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_latest_profile_review_service.py -q`

Expected: FAIL，因为 `app.product.latest_review` 尚不存在。

**Step 3: 写最小服务**

实现严格 Pydantic models、`LatestProfileReviewRepositoryPort`、service error allowlist 与
`LatestProfileReviewService.get_latest()`；不生成 URL、不读取 task payload/execution target。

**Step 4: 运行绿灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_latest_profile_review_service.py -q`

Expected: PASS。

### Task 2: 实现 owner-scoped PostgreSQL locator

**Files:**

- Create: `app/persistence/latest_review_repository.py`
- Test: `tests/test_latest_profile_review_repository_postgres.py`
- Reference: `app/persistence/player_records.py`
- Reference: `app/persistence/task_record.py`

**Step 1: 写真库红灯**

使用现有 PostgreSQL fixture seed active relationship、successful player link、Conversation 与 schema-2.0
recent review tasks。覆盖：cross-owner/hidden/inactive/无 successful profile 均 not-found；合法 profile 无 task
返回 null；legacy 1.0、wrong kind、wrong relationship 排除；失败任务不被旧成功任务越过；同 created_at 以
`task_id DESC` 稳定决胜。

**Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_latest_profile_review_repository_postgres.py -q`

Expected: FAIL，因为 Repository 尚不存在。

**Step 3: 实现单次短事务查询**

先用与 `PostgresPlayerRepository.list_profiles()` 等价的 active relationship + latest successful link 条件确认
profile 可见，再以 owner/relationship/schema `2.0`/kind `recent_review` 查询最新 task。不得调用外部服务，
不得返回 execution target/PUUID/payload。

**Step 4: 运行真库绿灯与计划检查**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_latest_profile_review_repository_postgres.py -q`

Expected: PASS；当前索引足够，无 migration。若 EXPLAIN 出现实测 Bad Case，停止并另开 migration ADR，不能
在本任务临时加索引。

### Task 3: 增加 latest locator 与 Recent Summary HTTP DTO

**Files:**

- Create: `app/api/live_workbench_models.py`
- Modify: `app/api/main.py`
- Test: `tests/test_live_workbench_api.py`
- Modify: `tests/test_fastapi_adapter.py`

**Step 1: 写 API 红灯**

覆盖：

```text
GET /player-profiles/{id}/reviews/recent/latest
GET /runs/{run_id}/recent-summary
```

断言 latest null=200、hidden/cross-owner=404 `player_profile_not_found`、service unavailable=503；response links
全部 relative allowlist。Summary 的 published/degraded=200，active=409 `run_not_ready`，failed/cancelled=409
`run_not_available`，rejected=409 `report_not_available`，integrity=500，cross-owner=404。

**Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_workbench_api.py tests/test_fastapi_adapter.py -q`

Expected: FAIL，路由和 models 尚不存在。

**Step 3: 实现薄 HTTP adapter**

`LatestProfileReviewResponse.from_result()` 只在 API 层生成 links。`RecentSummaryResponse` 明确复制
`RecentSummaryView` 的 snake_case 字段。`RunQueryPort` 声明 `get_recent_summary()`，但 `create_app()` 不为
不消费该 endpoint 的旧 Fake 增加全局启动门；endpoint 自身缺能力时安全 503。先用 existing
`owned_run_task()` 绑定 owner/run，再调用 query service。

**Step 4: 运行绿灯与 OpenAPI 检查**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_workbench_api.py tests/test_fastapi_adapter.py -q`

Expected: PASS；OpenAPI 不出现 owner/PUUID/path/raw body。

### Task 4: 把 Evidence public projection 收紧为 typed HTTP schema

**Files:**

- Modify: `app/api/evidence_models.py`
- Modify: `tests/test_evidence_product_api.py`
- Modify: `tests/test_evidence_product_api_postgres.py`

**Step 1: 写 schema 红灯**

断言 OpenAPI 中 `projection` 引用具体 model，嵌套模型覆盖 `sources/matches/joins/conflicts/gaps/claims`；
现有 JSON snapshot byte-shape 不变；extra/未知枚举/坏 digest/坏时间在 model boundary 拒绝。

**Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_evidence_product_api.py tests/test_evidence_product_api_postgres.py -q`

Expected: FAIL，因为 `projection` 仍是 `dict[str, object]`。

**Step 3: 实现嵌套 models**

镜像 `EvidenceBundle.to_public_projection()` 的现行 keys，不修改 storage/fusion wire：四类 source、match、
join key/sources-present、conflict、gap、claim/disposition/confidence/digest。`from_view()` 通过严格
`model_validate(copy.deepcopy(...))`，拒绝 drift，不 best-effort 删除字段。

**Step 4: 运行绿灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_evidence_product_api.py tests/test_evidence_product_api_postgres.py -q`

Expected: PASS，wire JSON 兼容。

### Task 5: composition 与 Linux package 接线

**Files:**

- Modify: `app/api/composition.py`
- Modify: `tests/test_api_composition.py`
- Modify: `scripts/run_packaging_smoke.py`
- Modify: `tests/test_packaging_smoke.py`

**Step 1: 写 composition 红灯**

证明 lifespan 创建 `PostgresLatestProfileReviewRepository` 与 service proxy；proxy 转发 locator 和
`_RunQueryProxy.get_recent_summary()`；数据库配置不可用时 endpoint 503 fail closed。Package smoke 在已有
profile/review/run 上查询 latest + Summary + typed Evidence，且外部调用保持 0。

**Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_composition.py tests/test_packaging_smoke.py -q`

Expected: FAIL，composition 尚未绑定。

**Step 3: 实现接线并运行绿灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_composition.py tests/test_packaging_smoke.py -q`

Expected: PASS。

### Task 6: 拆出 fixture/live 共用 view 与 exact wire decoders

**Files:**

- Create: `web/src/workbench/model.ts`
- Create: `web/src/api/wire.ts`
- Create: `web/src/api/decoders.ts`
- Create: `web/src/api/decoders.test.ts`
- Modify: `web/src/contracts/workbench.ts`
- Modify: `web/src/fixtures/workbenchFixtures.ts`
- Modify: `web/src/fixtures/workbenchFixtures.test.ts`

**Step 1: 写 decoder 红灯**

逐一覆盖 profiles/latest/task/events/product/run/summary/report/evidence/training。每个 decoder 拒绝 extra key、
未知 schema/enum、非 finite number、无 timezone timestamp、坏 UUID/digest、错 profile/task/run binding。

**Step 2: 运行红灯**

Run: `npm --prefix web run test:unit -- src/api/decoders.test.ts`

Expected: FAIL，模块尚不存在。

**Step 3: 实现手写 exact decoder 与 view model**

只使用小型 `isRecord/assertExactKeys/read*` helpers，不引入 Zod/codegen。把现有 fixture-only
`CoachReportFixture` 与 session completion 从共享 view 移出；共享 view 只含真实可显示字段和安全 Markdown。

**Step 4: 运行绿灯**

Run: `npm --prefix web run test:unit -- src/api/decoders.test.ts src/fixtures/workbenchFixtures.test.ts`

Expected: PASS。

### Task 7: 实现 bounded API client 与确定性 adapters

**Files:**

- Create: `web/src/api/client.ts`
- Create: `web/src/api/client.test.ts`
- Create: `web/src/workbench/adapters.ts`
- Create: `web/src/workbench/adapters.test.ts`

**Step 1: 写 client/adapter 红灯**

覆盖 relative `/api`、AbortSignal、content-type、JSON/text/SSE size limits、allowlisted error code；禁止渲染
response text。Adapters 覆盖 self/observed、published/degraded/rejected/not-ready、Evidence code 字典、
Training baseline/current/target/trend/sample count，并证明 observed 不生成 personal Training request/view。

**Step 2: 运行红灯**

Run: `npm --prefix web run test:unit -- src/api/client.test.ts src/workbench/adapters.test.ts`

Expected: FAIL。

**Step 3: 实现最小 client/adapters 并运行绿灯**

Run: `npm --prefix web run test:unit -- src/api/client.test.ts src/workbench/adapters.test.ts`

Expected: PASS。

### Task 8: 实现 generation guard 与单 EventSource 生命周期

**Files:**

- Create: `web/src/api/taskEventStream.ts`
- Create: `web/src/api/taskEventStream.test.ts`
- Create: `web/src/workbench/liveController.ts`
- Create: `web/src/workbench/liveController.test.ts`

**Step 1: 写控制面红灯**

Fake fetch/EventSource 证明：初次 profile load；latest null；active task page + stream；terminal authoritative
reload；duplicate/replay cursor 忽略；跳号允许；transient reconnect 不改 Product State；terminal/switch/unmount
close；late response/event 不匹配 generation/profile/task/run 时 fail closed；每 selection 同时最多一个 stream。

**Step 2: 运行红灯**

Run: `npm --prefix web run test:unit -- src/api/taskEventStream.test.ts src/workbench/liveController.test.ts`

Expected: FAIL。

**Step 3: 实现 reducer/controller**

Controller 不依赖 React component；显式持有 generation、AbortController、stream handle 与 authoritative
snapshot。SSE error 只产生 `reconnecting/live_update_error`，不写 rejected。

**Step 4: 运行绿灯**

Run: `npm --prefix web run test:unit -- src/api/taskEventStream.test.ts src/workbench/liveController.test.ts`

Expected: PASS。

### Task 9: 把 React 页面切到默认 live，安全展示 Markdown/Training

**Files:**

- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Modify: `web/vite.config.ts`
- Create: `web/src/components/SafeMarkdown.tsx`
- Create: `web/src/components/SafeMarkdown.test.tsx`
- Modify: `web/src/app/App.tsx`
- Modify: `web/src/components/CoachBrief.tsx`
- Modify: `web/src/components/RecentFormPanel.tsx`
- Modify: `web/src/components/TrainingPanel.tsx`
- Modify: `web/src/components/EvidenceDrawer.tsx`
- Modify: `web/src/app/App.test.tsx`

**Step 1: 锁定依赖并写 UI 红灯**

使用 npm 官方 registry 安装 exact `react-markdown@10.1.0`。测试默认无 `scenario` 时调用 live controller；
显式 scenario 保留 preview。HTML/image/link 不渲染或执行；Recent 标题不再硬编码战术判断；Coach 不猜
verdict/strength/priority；Training 不显示 `2/5`、completion percent/next action；observed 不发 Training 请求。

**Step 2: 运行红灯**

Run: `npm --prefix web run test:unit -- src/components/SafeMarkdown.test.tsx src/app/App.test.tsx`

Expected: FAIL。

**Step 3: 实现真实 UI 消费**

`SafeMarkdown` 使用 `skipHtml`、固定 `allowedElements`，不启用 `rehype-raw`，不允许 `a/img`。Vite proxy
只在 dev 把 `/api` 转发到 allowlisted local target；生产代码仍使用 relative URL。保留 Rift atmosphere、
Coach Core、tokens、responsive、focus 与 reduced-motion，不因接线退化为普通 Dashboard。

**Step 4: 运行组件绿灯**

Run: `npm --prefix web run typecheck`

Run: `npm --prefix web run test:unit`

Expected: PASS。

### Task 10: 建立真实 HTTP/SSE 浏览器 no-I/O 门

**Files:**

- Create: `web/tests/support/liveApiServer.mjs`
- Modify: `web/playwright.config.ts`
- Create: `web/tests/e2e/live-workbench.spec.ts`
- Modify: `web/tests/e2e/workbench.spec.ts`

**Step 1: 写浏览器红灯**

本地 API server 只返回 allowlisted deterministic DTO，并记录请求。覆盖 loading→active SSE→published、
degraded/rejected、empty latest、profile race、self/observed Training、Markdown injection、stream close、
desktop/tablet/mobile、keyboard/focus、reduced-motion、axe 与 remote host 请求为 0。

**Step 2: 运行红灯**

Run: `npm --prefix web run test:e2e`

Expected: FAIL，live server/flow 尚未存在。

**Step 3: 实现 test server 与 Playwright 双 webServer**

测试 server 不导入生产 secret，不读取 `.env`，SSE 使用有界 event 序列并在终态关闭。Vite proxy target 只由
测试 config 注入；不引入 CORS workaround。

**Step 4: 运行浏览器绿灯与 bundle 门**

Run: `npm --prefix web run test:e2e`

Run: `npm --prefix web run build`

Expected: 全部 PASS；JS gzip ≤ 150 kB。超限时先移除/替换 Markdown 依赖，不能提高预算追绿。

### Task 11: 全部后端、真库、前端与安全回归

**Files:**

- Modify only if a verified regression requires a scoped fix.

**Step 1: 后端 focused 与 PostgreSQL**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_latest_profile_review_service.py tests/test_latest_profile_review_repository_postgres.py tests/test_live_workbench_api.py tests/test_evidence_product_api.py tests/test_evidence_product_api_postgres.py tests/test_api_composition.py -q`

Expected: PASS，无 PostgreSQL skip。

**Step 2: 前端全门**

Run: `npm --prefix web ci --ignore-scripts`

Run: `npm --prefix web run typecheck`

Run: `npm --prefix web run test:unit`

Run: `npm --prefix web run build`

Run: `npm --prefix web run test:e2e`

Expected: PASS，npm production audit 0 high/critical，license 清单只有已审计许可。

**Step 3: 完整仓库门**

按当前 CI-equivalent runbook 执行完整 pytest、真实 PostgreSQL collection、Alembic head→base→head/check、
两套 RAG、Harness、compileall/pip/YAML、SDK/Secret/tracked-data、隔离 Linux Compose package、governance 与
`git diff --check`。Expected: 全绿；本批外部调用 0，8B holdout 0。

### Task 12: 八维证据、独立提交与 exact-SHA 公共关闭

**Files:**

- Create: `docs/learning/8e-live-workbench-integration-walkthrough.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`
- Modify: `docs/roadmap_change_history.md`

**Step 1: 写八维 walkthrough**

覆盖问题/原理、设计/实现、代码地图、数据/控制流、验证、runbook、失败/安全/边界和面试表述；明确不能说
Auth/部署/完整五模块/OP.GG breadth/full fusion golden slice 已完成。

**Step 2: 运行治理与 stale phrase 门**

Run: `.\.venv\Scripts\python.exe scripts/check_project_governance.py`

Run: `git diff --check`

Expected: PASS；全仓不出现把 fixture-only、degraded replay 或设计状态冒充完整产品的 stale claim。

**Step 3: 创建独立 implementation/evidence commit 并推送**

提交只包含本计划范围；记录 exact SHA，等待 GitHub Actions 的 `pytest`、`postgres-migrations`、
`packaging-smoke` 三 job 全部 completed/success。

**Step 4: 状态收尾**

公共三 job 成功后再把本批八维 coverage 证据登记完成，并把 canonical 唯一下一动作交给后续 8E 原子批；
整个 8E coverage 仍保持 `planned`，直到 Auth、入口、Timeline、Training、部署和其它列明退出项全部关闭。
