# 5P-3 Domain Pipeline 与 Application Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有 Riot Summary 与确定性报告逻辑提升为可复用 app-level domain services，并用一个严格、安全、可注入的 `RecentReviewApplicationService` 串联 5P-1 compiler、5P-2 verified composition 和 `AgentRuntimeV1.run()`。

**Architecture:** 继续使用单体仓库内的模块化分层：`app.lol` 拥有纯领域计算和上游数据编排，`app.product` 拥有一次近期复盘用例的控制顺序与安全错误，`app.runtime` 继续独占 Agent/Harness 执行。CLI 只调用 app-level 服务；FastAPI、receipt/query、Session/Memory 和真实 Provider 均不进入本检查点。

**Tech Stack:** Python 3.11, Pydantic v2, requests exception taxonomy, pytest, existing Skill/Runtime/Harness contracts。

---

## 教学与边界

### 本轮解决的问题

当前 Summary/Report 业务函数仍由 `scripts/` 拥有，而产品 compiler 只能接收已经形成的 Summary 与
报告。若未来 FastAPI handler 直接调用脚本、拼 Runtime request、解释异常，它就会成为第二个
业务编排器。5P-3 建立唯一 Application Service，让 CLI、未来 HTTP 和未来 MCP 都能复用同一用例。

### 本轮不解决的问题

- 不安装或导入 FastAPI；
- 不写 `api_run_receipt.json` 或查询服务；
- 不实现鉴权、限流、SQL、Session、Memory、SSE、后台任务或恢复；
- 不读取 `.env`、API Key，不构造真实 RiotClient/DataDragonService/LLM Provider；
- 不把 Fake Runtime 结果解释为真实 Coach 质量。

### 失败边界

- 上游 404 → `player_not_found`；
- 上游 401/403 → `riot_authentication_failed`；
- 上游 429 → `riot_rate_limited`，只保留受控 retry-after；
- timeout → `upstream_timeout`；
- 5xx/连接失败 → `upstream_unavailable`；
- Summary Schema、Catalog、Prompt Program 或 compiler 漂移 → `service_configuration_invalid`；
- 零可分析比赛 → `insufficient_match_data`，不得创建 Runtime run；
- Runtime failed/不一致终态 → `review_runtime_failed`，只保留 run_id 与 allowlisted terminal reason。

### Task 1: 写失败测试冻结 app-level Summary/Report 边界

**Files:**
- Create: `tests/test_recent_review_domain_services.py`
- Modify: `tests/test_stage1_pipeline.py`

**Step 1: Write failing tests**

验证 app-level `build_player_summary()` 与 `render_deterministic_report()` 可直接导入；现有 Stage 1
短局/timeline 行为不变；CLI `build_report` 与 app renderer 对同一 Summary 逐字节一致。

**Step 2: Run red tests**

Run: `python -m pytest tests/test_recent_review_domain_services.py tests/test_stage1_pipeline.py -q`

Expected: FAIL，因为 `app.lol.player_summary` / `app.lol.report_renderer` 尚不存在。

### Task 2: 提升 Summary Builder 并让 CLI 变薄

**Files:**
- Create: `app/lol/player_summary.py`
- Modify: `scripts/build_player_summary.py`
- Modify: `app/lol/__init__.py` only for stable public exports

**Step 1: Move domain behavior without changing semantics**

提升 `timeline_fallback`、`process_match`、`build_player_summary`，并增加注入 client/ddragon 的
`RiotPlayerSummaryBuilder`。保留 detail 失败和 timeline 不可用的显式边界；不在 domain 层读取 Key。

**Step 2: Keep CLI compatibility**

脚本保留参数解析、真实依赖构造、路径和打印；业务计算改为从 app 模块导入。现有
`from scripts.build_player_summary import build_player_summary` 继续可用。

**Step 3: Run focused tests**

Run: `python -m pytest tests/test_recent_review_domain_services.py tests/test_stage1_pipeline.py -q`

### Task 3: 提升确定性 Report Renderer 并验证字节一致

**Files:**
- Create: `app/lol/report_renderer.py`
- Modify: `scripts/generate_markdown_report.py`
- Modify: `tests/test_recent_review_domain_services.py`

**Step 1: Promote pure rendering functions**

提升 format/findings/report 函数；app renderer 不读文件、不构造 DataDragon、不写输出。

**Step 2: Convert CLI into adapter**

脚本只负责 Summary 文件读取/验证、术语映射、输出路径与写盘，并保留 `build_report` 兼容别名。

**Step 3: Prove byte parity**

同一 fixture 分别走兼容 CLI symbol 与 app renderer，要求字符串逐字节一致。

### Task 4: 写失败测试冻结 Application Service 控制流

**Files:**
- Create: `tests/test_recent_review_application_service.py`

**Step 1: Happy and terminal tests**

使用真实 5P-1 compiler、Fake Summary Builder、app renderer 与 Fake Runtime，覆盖 published、
degraded、rejected；校验调用顺序、typed output、publication 一致性和 trace reference 投影。

**Step 2: Failure tests**

覆盖上游状态码/timeout/connection、坏 Summary、零有效比赛、renderer/compiler/config drift、
Runtime failed 和 output/publication 不一致。确认原始异常、URL、Key、路径不进入公开错误字段。

**Step 3: Run red tests**

Run: `python -m pytest tests/test_recent_review_application_service.py -q`

Expected: FAIL，因为 Application Service 合同尚不存在。

### Task 5: 实现严格 Application Service 与安全错误映射

**Files:**
- Create: `app/product/recent_review_service.py`
- Modify: `app/product/__init__.py`
- Modify: `tests/test_recent_review_application_service.py`

**Step 1: Add dependency protocols**

定义最小 `RecentReviewSummaryBuilder` 与 `RecentReviewRuntime` Protocol；不引入通用 DI 容器。

**Step 2: Add strict result and safe failure contracts**

结果使用 frozen/extra-forbid Pydantic 模型，并交叉验证 runtime/publication/output；异常只暴露
固定 code、可选 run_id/terminal_reason/retry_after，不保存或返回 raw exception。

**Step 3: Implement orchestration**

严格按 Summary → validate/zero-data gate → report → compiler → Runtime 顺序执行。Summary/report
成功前不生成 run_id；Runtime 一旦被调用，其失败只通过安全结果映射。

**Step 4: Run focused tests**

Run: `python -m pytest tests/test_recent_review_application_service.py -q`

Expected: PASS。

### Task 6: 深化 secure product execution factory

**Files:**
- Modify: `app/runtime/composition.py`
- Modify: `tests/test_prompt_program.py`
- Modify: `tests/test_agent_runtime.py` only if product composition integration needs it

**Step 1: Add the narrow secure factory constructor**

用既有 `SecureChatEvaluationAdapter`、`coach_evaluation@1.1.0` fact pack、`ChatCoachReviser` 与
revision validator 构造产品 `RuntimeExecutionFactory`。不创建 Provider，不发 I/O。

**Step 2: Make product default explicit**

`RuntimeCompositionRoot.build_runtime()` 在调用者未显式传测试 factory 时，要求 knowledge provider
并构造 secure product factory；测试专用 factory 仍可显式注入，但不能成为默认产品路径。

**Step 3: Verify composition type and no-I/O behavior**

测试实际 bundle 的 evaluator/reviser 类型，证明 Program 1.1 identity 与执行 factory 一致；模块
import 与 factory construction 不读取 Key、不调用网络。

### Task 7: 相邻回归、完整门禁与状态交接

**Files:**
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/requirements_change_log.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/project_decisions.md`
- Modify: `docs/architecture_capability_matrix.md`

**Step 1: Run verification**

运行 focused domain/application/composition tests、相邻 Product/Skill/Runtime/Harness tests、完整
pytest、两套 RAG、compileall、Harness SDK boundary、tracked secret/run-data、dry-run、governance
和 `git diff --check`。

**Step 2: Record limitations**

明确 Fake upstream/Fake Runtime 只证明产品控制流；没有真实 Riot/Provider 质量、HTTP、receipt、
幂等、事务、并发或恢复证据。记录 5P-2 secure factory 的相邻深化，不改写其历史证据。

**Step 3: Commit, push and exact-SHA CI**

公共 CI 成功后关闭 5P-3，canonical 只交接到 `5P-4-file-backed-run-receipt-query`，不得自动实现
5P-4/5P-5/5F。
