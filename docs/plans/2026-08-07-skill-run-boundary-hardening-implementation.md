# 5D-1 Skill Run Boundary Hardening 实施计划

> **For Codex:** 在当前 RiftCoach worktree 中按 TDD 逐项执行；仅完成 5D-1，停止在
> 5D-2 Context Builder 之前。

**目标：** 建立 Router selected decision 到已验证 Skill 输入之间的 fail-closed
执行边界，并用同一 run identity 与规范内容摘要绑定未来 Harness 输入 Artifact。

**架构：** Router 决策保留 Skill 版本；共享 run ID 与 Artifact 字节编码规则消除
跨模块漂移；`SkillExecutionBoundary` 从 Catalog 重新核对身份、调用 Skill 自己的
input model，并比较内容绑定后才返回不可变的 `ValidatedSkillExecution`。

**技术栈：** Python 3.11、Pydantic 2、dataclass、标准库 JSON/SHA-256、pytest。

---

### Task 1：先锁定 Skill I/O 非空文本合同

**文件：**

- 修改：`tests/test_skill_contracts.py`
- 修改：`app/skills/recent_form_review.py`
- 修改：`app/skills/single_match_review.py`
- 新增：`app/skills/text_contracts.py`

**步骤：**

1. 先写两个输入和两个输出的空白、规范化、空项与重复项失败测试。
2. 运行 Skill 合同测试，确认新测试按预期失败。
3. 增加最小共享文本规范化函数并接入两个 Skill。
4. 重跑测试，确认旧发布边界没有变化。

### Task 2：让 Router selected decision 锁定版本

**文件：**

- 修改：`tests/test_skill_router_models.py`
- 修改：`tests/test_deterministic_skill_router.py`
- 修改：必要的手工 selected decision fixture
- 修改：`app/skills/routing_models.py`
- 修改：`app/skills/router.py`

**步骤：**

1. 先测试 selected 缺版本失败、非 selected 携带版本失败、真实路由返回 Manifest
   版本。
2. 给 `RouterDecision` 增加并验证 `selected_skill_version`。
3. 由 Router 从唯一命中候选填入版本。
4. 运行 Router Contract、Router strategy 与 evaluation 回归；不重跑或改写 sealed
   holdout 数据和基线结果。

### Task 3：统一安全 run ID

**文件：**

- 新增：`app/harness/run_ids.py`
- 修改：`app/harness/models.py`
- 修改：`app/harness/store.py`
- 修改：`tests/test_harness_models.py`
- 修改：`tests/test_harness_store.py`

**步骤：**

1. 先测试空白、路径、盘符、空格、Windows 保留名和超长 ID 被拒绝。
2. 实现唯一 `normalize_run_id()`，返回去空白后的安全目录组件。
3. 让 `RunManifest.new()` 与 `FileRunStore` 共同调用它。
4. 重跑 Harness model/store 测试。

### Task 4：建立输入内容绑定与执行边界

**文件：**

- 新增：`app/harness/artifact_content.py`
- 修改：`app/harness/runtime.py`
- 新增：`app/skills/execution.py`
- 修改：`app/skills/__init__.py`
- 新增：`tests/test_skill_execution_boundary.py`

**步骤：**

1. 先测试规范字节、两个真实 Skill 成功路径，以及 decision、Catalog version、input
   model、run ID、kind/schema/digest 的失败路径。
2. 提取 Harness 当前 JSON/text Artifact 编码为共享纯函数，并让现有 Runtime 复用。
3. 实现内容摘要记录、`SkillExecutionRequest`、边界错误与
   `ValidatedSkillExecution`。
4. 输入验证使用深拷贝，避免调用方随后修改原 payload 改变已验证快照。
5. 运行 5D-1 聚焦测试。

### Task 5：全量验证与状态同步

**文件：**

- 修改：`.planning/2026-08-06-riftcoach-development/{task_plan,findings,progress}.md`
- 修改：`docs/project_execution_state.md`
- 修改：`docs/roadmap_change_history.md`
- 修改：`docs/roadmap_v1_3_amendment.md`
- 修改：`docs/architecture_capability_matrix.md`
- 按需要修改：`docs/project_decisions.md`、`docs/requirements_change_log.md`

**步骤：**

1. 运行 5D-1 聚焦测试。
2. 运行完整 `pytest` 与 `compileall`。
3. 运行 `git diff --check`、陈旧状态搜索和治理预检。
4. 只把 5D-1 标记完成，并把唯一下一步改为 5D-2；不得声称 Context Builder 或
   AgentLoop 组合已完成。
5. 审查 diff，提交并推送当前 SHA，再验证该 SHA 的 GitHub Actions 结果。
