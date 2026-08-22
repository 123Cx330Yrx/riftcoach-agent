# Stage 8 Multi-Agent、可靠运行时与产品化 Implementation Plan
> **For Codex:** 先完成当前 checkpoint 的设计/治理闭环，再按 canonical 顺序逐项执行；不得跳过 TDD、八维证据或 exact-SHA 公共 CI。

**Goal:** 在不牺牲现有 Python/PostgreSQL/Harness 证据边界的前提下，交付可恢复的 LoL Coach 产品，并用实验决定是否采用 Multi-Agent/DAG。

**Architecture:** 以 PostgreSQL task/control plane、Runtime Trace/Artifact 数据面和现有 Harness 为基线；8A/8B 负责高级能力采用门，8C 提供可靠执行 Core，8D 建立 Riot/OP.GG typed evidence fusion，8E 接入 React/SSE/Auth/部署，8F 完成最终评测与作品集退出。

**Tech Stack:** Python/FastAPI/PostgreSQL/SQLAlchemy/Alembic、既有 AgentRuntime/ToolRuntime/Harness、React + TypeScript、Radix/shadcn、Motion、ECharts；任何新框架或数据基础设施均需独立 ADR。

---

## 执行规则

- 每个 checkpoint 先写教学合同和设计，再写红灯测试；
- 每个 checkpoint 使用独立提交、公共 `pytest`/真实 PostgreSQL/packaging-smoke 三门；
- 本机没有 PostgreSQL/Docker 时明确 skip，不能把 SQLite 或本地 Fake 当作真库证据；
- 外部 Riot、OP.GG、Provider、付费 MotionSites 内容和正式 Auth 只在当前 checkpoint 明确授权且离线门稳定后执行；
- 所有事件、证据、前端 DTO 和实验结果 body-free/owner-scoped，原始秘密、Prompt、MCP body、Provider body 不落盘；
- 若本 checkpoint 失败，保留失败 SHA/Actions/Bad Case，不通过扩大范围来“修绿”。

## Task 0：Entry design 退出与 8A 交接

**Files:**
- Create: `docs/adr/0051-adopt-stage8-evidence-gated-runtime-fusion-and-productization.md`
- Create: `docs/plans/2026-08-22-stage8-multi-agent-reliable-runtime-productization-entry-design.md`
- Create: `docs/plans/2026-08-22-stage8-multi-agent-reliable-runtime-productization-implementation.md`
- Create: `docs/learning/stage-8-multi-agent-reliable-runtime-productization-entry-design-walkthrough.md`
- Modify: canonical state, active plan, roadmap/history, capability matrix, decisions and coverage ledger

**Steps:**

1. 运行治理预检并确认唯一 checkpoint 是 entry design；
2. 保存教学、ADR、蓝图、资源门、测试矩阵和八维 walkthrough；
3. 将 8A–8F 加入治理常量与 coverage canonical order，全部置 `planned`；
4. 运行完整本地门禁、`git diff --check`、治理和 stale-phrase scan；
5. 独立提交/推送 entry design，等待 exact-SHA 三 job；
6. 公共全绿后将 entry design coverage 置 `complete`，canonical 交接 `8A-advanced-adoption-gate`。

## Task 8A：Advanced Adoption Gate

**Files:**
- Create: `docs/adr/0052-stage8-advanced-adoption-gate.md`
- Create: `docs/plans/2026-08-*-8a-advanced-adoption-gate-design.md`
- Create: `docs/learning/8a-advanced-adoption-gate-walkthrough.md`
- Test/asset: `tests/test_stage8_adoption_gate.py`, `data/evaluation/stage8/*`（只含匿名/可复现元数据）

**Steps:**

1. 从真实现有 workflow 提取 2–3 个并行/恢复 Bad Case 候选；
2. 建立候选矩阵：单流程、受限并行、Multi-Agent、DAG/第三方 Runtime；
3. 冻结输入、工具权限、预算、评测集角色、污染规则、停止线和证据身份；
4. 先写离线 gate 红灯，再实现最小候选评估器；
5. 运行同切片 Fake/no-I/O 对照与安全边界测试；
6. 只交接 8B，不能在 8A 安装或接入候选生产框架。

## Task 8B：Conditional Multi-Agent Experiment

**Files:**
- Create: `docs/adr/0053-stage8-conditional-multi-agent-experiment.md`
- Create: `docs/plans/2026-08-*-8b-multi-agent-experiment-design.md`
- Create: `docs/learning/8b-multi-agent-experiment-walkthrough.md`
- Create/Modify: isolated experiment runner and fixed evaluation assets under `experiments/stage8/`

**Steps:**

1. 先写单流程基线测试并记录工具/Provider/Artifact identity；
2. 再写候选并行或 Multi-Agent 的最小隔离 adapter；
3. 比较质量、延迟、成本、失败隔离、上下文泄漏和维护复杂度；
4. 运行一次固定 development/held-out 评测，首错停止、零重试、结果不可覆盖；
5. 形成 adopt/partial/reject ADR；
6. 只有 adopt/partial 才向 8C 传递明确 executor 合同，reject 则保留单 Runtime。

## Task 8C：Reliable Runtime Core

**Files:**
- Modify: `app/tasks/*`, `app/runtime/*`, `app/harness/*`, `app/api/*`
- Create: durable event/replay/checkpoint modules and focused tests
- Database: new Alembic migration only after schema design and PostgreSQL red tests

**Steps:**

1. 先冻结 event envelope、event identity、cursor、lease/fencing 和 cancel state machine；
2. 写 PostgreSQL migration/repository/concurrency 红灯；
3. 实现短事务 event append、claim/heartbeat/terminal CAS 与 replay-safe projection；
4. 实现 cancellation request、checkpoint、receipt-proven recovery 和迟到结果拒绝；
5. 以现有 Runtime/Harness 跑离线产品纵向；
6. 真实 PostgreSQL 注入 DB/Artifact/进程中断故障并完成出口审查。

## Task 8D：Riot + OP.GG Evidence Fusion Core

**Files:**
- Modify: `app/lol/*`, `app/mcp/*`, `app/agent/*`, `app/product/*`
- Create: typed evidence models/adapter/join policy and fixture tests
- Data: versioned, anonymized Riot/Data Dragon/OP.GG fixtures only until external I/O is explicitly authorized

**Steps:**

1. 写 Riot/Data Dragon/OP.GG provenance 与 join key 红灯；
2. 实现分层 source facts、bundle digest、expiry and conflict states；
3. 让 current snapshot Meta 只能产生受限建议；
4. 把 bundle 接入 Context/Harness，不覆盖 Memory 或 system instruction；
5. 在有界授权下执行一次真实 OP.GG/Riot smoke，记录 body-free evidence；
6. 通过版本冲突、过期、缺 patch、schema drift、注入和部分来源测试。

## Task 8E：Full Productization

**Files:**
- Create: `frontend/` React/TypeScript application and its lockfile
- Modify: `app/api/*`, `app/runtime/*`, deployment/Compose/CSP/CORS configuration
- Create: Playwright/component/a11y tests and desktop/mobile screenshot evidence

**Steps:**

1. 先冻结 design tokens、component states、route map and API DTO contracts；
2. 以 placeholder/fixture 建立五个页面，先验证 loading/empty/error/degraded/keyboard/reduced-motion；
3. 只接入经过验证的 API/SSE evidence projection；
4. 逐个审查 MotionSites 候选，获得许可材料后再引入局部效果/资产；
5. 接入正式 Auth/RSO、HTTPS、CSP/CORS、限流、备份/恢复和可观测性；
6. 运行桌面/移动 E2E、真实部署 smoke 和删除/导出/隐私测试。

## Task 8F：Final Evaluation & Portfolio Exit

**Files:**
- Create: `docs/plans/2026-08-*-stage8-exit-review.md`
- Create: `docs/learning/8f-final-evaluation-and-portfolio-walkthrough.md`
- Create: final evaluation assets, screenshots, demo/runbook and resume evidence matrix

**Steps:**

1. 固定产品回归、RAG、Tool/Runtime、evidence fusion、数据库和前端评测集；
2. 采集 p50/p95、队列等待、工具次数、Usage/cost completeness、恢复成功率和失败隔离；
3. 运行安全、依赖许可证、CSP/CORS/Auth、owner isolation、备份 restore、a11y 和 reduced-motion 门；
4. 审查每一项简历技术点对应的源码、测试、实验或 CI；
5. 形成 Stage 8 exit matrix 和明确 deferred/unknown；
6. 只在 exit matrix、coverage、公共 CI 和作品集证据全部满足后关闭 Stage 8。
