# 8A Advanced Adoption Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建立一个严格、离线、可复现的 Stage 8 高级候选采用门，把角色隔离 Multi-Agent 与普通受限并行交给 8B 公平对照。

**Architecture:** 使用 Pydantic strict models 读取两个版本化 JSON 资产，先验证 case-set digest，再验证同切片身份、角色权限、硬门、收益预算和停止条件。Evaluator 只输出 candidate/deferred 与稳定 reason code，不运行任何 Agent 或外部 I/O。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、JSON/SHA-256、既有治理与 CI；无新依赖。

---

### Task 1：冻结 ADR 与 8A 数据合同

**Files:**
- Create: `docs/adr/0052-admit-role-isolated-multi-agent-to-bounded-stage8-experiment.md`
- Create: `docs/plans/2026-08-22-8a-advanced-adoption-gate-design.md`
- Create: `data/evaluation/stage8/advanced_adoption_cases_v1.json`
- Create: `data/evaluation/stage8/advanced_adoption_gate_v1.json`

**Steps:**

1. 记录 BC-8A-01/02/03 的 observed/hypothesis 和源码证据；
2. 写 development 与 calibration-excluded holdout synthetic cases；
3. 计算 case-set 文件 SHA-256 并写入 gate；
4. 冻结 serial baseline、bounded-parallel comparator、role-isolated candidate 与 deferred 候选；
5. 检查 JSON/YAML 和 `git diff --check`。

### Task 2：先写采用门红灯

**Files:**
- Create: `tests/test_stage8_adoption_gate.py`
- Create: `app/evaluation/stage8_adoption/__init__.py`
- Create: `app/evaluation/stage8_adoption/models.py`
- Create: `app/evaluation/stage8_adoption/gate.py`

**Steps:**

1. 写测试导入尚不存在的 `load_adoption_gate`、`evaluate_adoption_gate`；
2. 断言合法资产得到 primary candidate/comparator/deferred 决策和固定 digest；
3. 断言 case digest 漂移、真实 I/O/重试、角色工具重叠、Agent 发布、缺 holdout/停止线全部拒绝；
4. 运行 `python -m pytest tests/test_stage8_adoption_gate.py -q`，确认因缺模块/行为失败；
5. 保存红灯输出摘要到 active progress，不伪造提交。

### Task 3：实现最小 strict evaluator

**Files:**
- Create: `app/evaluation/stage8_adoption/models.py`
- Create: `app/evaluation/stage8_adoption/gate.py`
- Create: `app/evaluation/stage8_adoption/__init__.py`

**Steps:**

1. 实现 frozen/extra-forbid Pydantic models 与 slug/digest/唯一性验证；
2. 实现 canonical JSON SHA-256 和 case-set exact binding；
3. 实现 baseline/comparator/candidate identity 与 role/tool/publication hard gates；
4. 实现 dataset、budget、metric、stop-condition 和 deferred-reason validation；
5. 输出 body-free `AdvancedAdoptionDecision`；
6. 重跑聚焦测试直至全绿。

### Task 4：比例回归与八维证据

**Files:**
- Create: `docs/learning/8a-advanced-adoption-gate-walkthrough.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: canonical state、active plan、roadmap/history、capability matrix、project decisions

**Steps:**

1. 运行 adoption gate 聚焦测试；
2. 运行 AgentLoop/Context/Meta/Harness/Runtime 相邻测试；
3. 运行完整 pytest、两套 RAG、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 和 diff 门；
4. 补齐问题/原理、设计/实现、代码地图、数据/控制流、验证、runbook、失败/安全/边界和面试表述；
5. coverage 在 public CI 前保持 `planned`。

### Task 5：独立公共闭环

**Files:**
- Modify only the 8A files and canonical mirrors listed above

**Steps:**

1. 审查完整 diff 与 cached diff；
2. 提交/推送 8A implementation；
3. 等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；
4. 公共全绿后将 8A coverage 置 `complete`，只交接 `8b-conditional-multi-agent-experiment`；
5. 独立提交状态收尾并再次等待该 SHA 三 job，全绿后停止。
