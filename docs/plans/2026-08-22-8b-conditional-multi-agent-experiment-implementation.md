# 8B Conditional Multi-Agent Experiment Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 在不修改产品 Runtime、不调用外部服务的前提下，公平执行串行、普通并行与角色隔离 Multi-Agent 三路实验，并用一次不可覆盖 holdout 形成最终采用裁决。

**Architecture:** 新增隔离的 `app/evaluation/stage8_experiment/`。strict models 保存 body-free 身份与指标；runner 用本地 fixture ports、typed/digest-bound Artifact 和最多双 worker scheduler 组合三条路径，再统一调用真实 `ReviewHarness`。CLI 负责 clean/exact-SHA preflight、development admission 和 exclusive holdout output；不读取 `.env`。

**Tech Stack:** Python 3.11、Pydantic v2、标准库 `concurrent.futures`/JSON/SHA-256、pytest、既有 Harness；无新依赖。

---

### Task 1：冻结授权、设计和结果合同

**Files:**
- Modify: `docs/requirements_change_log.md`
- Modify: canonical state 与 active plan
- Create: `docs/plans/2026-08-22-8b-conditional-multi-agent-experiment-design.md`
- Create: 本实施计划

**Steps:**
1. 记录 RQ-082 与 exact scope；
2. 冻结公平身份、三路唯一变量、指标模型、硬门和一次性生命周期；
3. 运行 governance 与 diff check。

### Task 2：先写 strict contract 与执行红灯

**Files:**
- Create: `tests/test_stage8_multi_agent_experiment.py`
- Create: `app/evaluation/stage8_experiment/__init__.py`
- Create: `app/evaluation/stage8_experiment/models.py`
- Create: `app/evaluation/stage8_experiment/runner.py`

**Steps:**
1. 先测试公开 API 尚不存在时的 collection 红灯；
2. 锁定 normal/schema drift/instruction/timeout/tool probe 的三路终态；
3. 锁定 exact role/tool/Context、Artifact digest、真实 Harness 和八个零硬门；
4. 锁定 development 聚合指标与 body-free JSON；
5. 记录真实红灯摘要，不伪造提交。

### Task 3：实现最小 evaluation-only runner

**Files:**
- Implement: `app/evaluation/stage8_experiment/models.py`
- Implement: `app/evaluation/stage8_experiment/runner.py`
- Implement: `app/evaluation/stage8_experiment/__init__.py`

**Steps:**
1. 实现 frozen/extra-forbid models、canonical digest 和稳定错误码；
2. 实现两个 fixture ports、branch exact-tool guard 与 typed Artifact materialization；
3. 实现串行、最多双 worker 普通并行、独立角色 Context 三路；
4. 用相同 Coach/Evaluator/Reviser/Config 真实执行 `ReviewHarness`；
5. 聚合 match/safe-degraded/latency/Token/calls/isolation，输出 adopt/partial/reject 所需证据；
6. 重跑聚焦测试直至全绿。

### Task 4：实现 preflight、development admission 与不可覆盖 holdout

**Files:**
- Create: `app/evaluation/stage8_experiment/lifecycle.py`
- Create: `scripts/run_stage8_multi_agent_experiment.py`
- Create: `tests/test_stage8_multi_agent_experiment_lifecycle.py`

**Steps:**
1. 先写 clean SHA/public CI SHA/development result/显式 holdout 确认红灯；
2. 实现 bounded loader、strict result validator、repository path guard；
3. development 结果用 exclusive create 写入 `tmp/`，holdout 必须复读其同 SHA 通过证据；
4. holdout 正式路径 exclusive reserve，异常保留 sentinel，第二次永远拒绝；
5. 验证 CLI 不读取 `.env`、不构造 Provider/MCP Client、不调用网络。

### Task 5：本地开发门与八维证据

**Files:**
- Create: `docs/learning/8b-conditional-multi-agent-experiment-walkthrough.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: roadmap/history/amendment/capability/canonical/active plan

**Steps:**
1. 运行 8B 聚焦与 Harness/Context/Meta/Runtime/8A 相邻测试；
2. 运行完整 pytest、两套 RAG、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 和 diff 门；
3. 补齐八维证据，coverage 在 holdout 与最终公共 CI 前保持 `planned`；
4. 审查完整/cached diff，提交并推送实现批。

### Task 6：实现 SHA exact-SHA 公共门

**Steps:**
1. 等待同一实现 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke`；
2. 任一失败只修实现/测试，不运行 holdout；
3. 三 job 全绿后验证工作树、HEAD、origin/main 精确一致。

### Task 7：唯一 development 与 holdout 执行

**Files:**
- Create at runtime: `tmp/stage8/multi_agent_development_v1.json`（ignored）
- Create once: `data/evaluation/results/stage8/role_isolated_multi_agent_holdout_v1.json`

**Steps:**
1. 在 clean/public-success SHA 上运行 development 并复读 strict result；
2. 执行 holdout no-I/O preflight，确认正式结果路径不存在；
3. 唯一执行 holdout，不覆盖、不重跑；
4. 计算结果文件 SHA-256，运行 body-free/identity validator；
5. 若结果失败或 reject，保留真实结论，不调规则追绿。

### Task 8：最终 ADR、归档与公共闭环

**Files:**
- Create: `docs/adr/0053-*.md`（名称按真实 adopt/partial/reject 结果）
- Complete: walkthrough、coverage 与 canonical mirrors

**Steps:**
1. 以 development/holdout 真实指标形成最终采用裁决；
2. 将 8B coverage 八维证据置 complete，仅交接 `8c-reliable-runtime-core`；
3. 独立提交/推送 evidence + ADR + 状态；
4. 等待该 exact SHA 三 job 全绿；
5. 停止，不自动进入 8C。
