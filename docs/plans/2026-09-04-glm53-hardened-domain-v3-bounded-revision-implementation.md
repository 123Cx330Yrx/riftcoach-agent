# GLM-5.3 Flash Hardened Domain V3 Bounded Revision Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 离线实现 GLM-5.3 Flash V3 的最多一次修订、安全评测诊断、可证明资源墙和全新资产准入，不发真实请求。

**Architecture:** 共享 `ProductionDomainCaseExecutor` 只增加默认关闭的修订参数和 body-free 诊断投影；V3 通过独立预算合同、资产准入和运行身份显式启用。旧 V2 入口、常量、回执 Schema 与零修订行为保持不变。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, versioned JSON assets, existing Harness/AgentLoop.

---

### Task 1: 固定一次修订与诊断的失败测试

**Files:**
- Modify: `tests/test_provider_domain_production.py`
- Modify: `tests/test_provider_domain_experiment.py`
- Modify: `tests/test_domain_e2e_evaluation.py`

**Step 1:** 新增测试，证明默认构造仍把 `max_revisions=0` 传给 Harness，旧 Fake Provider 序列和旧语义投影不变。

**Step 2:** 新增一次修订案例：Agent 工具往返、首评 `needs_revision`、修订、复评通过；断言 5 次正常调用、`revision_count=1`、终态 `published`。

**Step 3:** 新增阻断性 `prompt_injection` 案例，断言即使配置 1 次修订也不会调用 reviser。

**Step 4:** 新增诊断模型测试，只接受 attempt、score、verdict、passed-check 数量、类别计数和严重度计数；向模型注入 `quote`、`summary` 或任意自由文本字段必须失败。

**Step 5:** 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_domain_production.py tests/test_provider_domain_experiment.py tests/test_domain_e2e_evaluation.py -q
```

预期：新测试因参数和诊断模型尚不存在而失败，旧测试继续通过。

### Task 2: 实现默认关闭的修订参数和安全诊断投影

**Files:**
- Modify: `app/evaluation/provider_domain_production.py`
- Modify: `app/evaluation/provider_domain_experiment.py`
- Modify: `app/evaluation/domain_e2e.py`

**Step 1:** 给 `ProductionDomainCaseExecutor.__init__` 增加 `max_revisions: int = 0`，使用与 `HarnessConfig` 相同的 `0..3` 校验，并保存只读属性。

**Step 2:** 将硬编码 `SkillReviewExecutor(max_revisions=0)` 改为显式传递保存值；不要修改任何现有调用方。

**Step 3:** 增加冻结的计数模型，例如：

```python
class EvaluationIssueCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: EvaluationIssueCategory
    count: int = Field(ge=1)

class EvaluationAttemptDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    attempt_id: int = Field(ge=0, le=1)
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    passed_check_count: int = Field(ge=0)
    issue_category_counts: tuple[EvaluationIssueCount, ...]
    severity_counts: tuple[EvaluationSeverityCount, ...]
```

类别与严重度类型必须来自 `EvaluationResponseModelV11` 的固定枚举；计数按枚举顺序规范化，不能包含零值、重复项或自由文本。

**Step 4:** 遍历 `evaluation_attempt_*.json` 工件，逐个严格校验后生成投影；只公开成功校验的轮次，任何缺口或身份不一致返回安全失败，不泄露原始异常值。

**Step 5:** 运行 Task 1 的聚焦测试，预期全部通过。

### Task 3: 建立 V3 资源墙与离线可达性证明

**Files:**
- Create: `app/evaluation/glm53_bounded_revision_budget.py`
- Create: `app/evaluation/glm53_bounded_revision_budget_reachability.py`
- Create: `tests/test_glm53_bounded_revision_budget.py`
- Create: `tests/test_glm53_bounded_revision_budget_reachability.py`
- Create: `data/evaluation/contracts/glm53_flash_hardened_v3_budget_reachability.json`

**Step 1:** 先写失败测试，冻结每案 9 次、全域 27 次、SDK retries=0，并证明旧 `glm53_low_profile_budget` 的 4/12 与 24,000/72,000 常量不变。

**Step 2:** 用 Fake Provider 构建 V3 允许的最坏请求序列：AgentLoop 4、首评与格式修复 2、修订 1、复评与格式修复 2；每次记录请求包络估算并预留 4096 输出。

**Step 3:** 生成 canonical JSON 可达性报告，至少绑定算法版本、候选策略、案例/Context SHA、每步输入估算、输出预留、每案总量、全域总量和报告自身身份；报告不得含 Prompt 或正文。

**Step 4:** 实现 V3 专用预算策略和 Provider wrapper。预算在 I/O 前预留调用；结算 Usage 后校验有限 Token 墙；未知/非法 Usage、调用或 Token 越界均 fail closed。

**Step 5:** 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_glm53_bounded_revision_budget.py tests/test_glm53_bounded_revision_budget_reachability.py tests/test_glm53_low_profile_budget.py -q
```

预期：V3 预算与报告通过，V2 回归无变化。

### Task 4: 创建全新 V3 资产与 no-I/O 准入

**Files:**
- Create: `app/evaluation/glm53_hardened_domain_v3_assets.py`
- Create: `tests/test_glm53_hardened_domain_v3_assets.py`
- Create: `examples/fixtures/player_summary_glm53_flash_hardened_v3.json`
- Create: `examples/fixtures/deterministic_report_glm53_flash_hardened_v3.md`
- Create: `data/evaluation/glm53_flash_hardened_domain_protocol_v3.json`
- Create: `data/evaluation/glm53_flash_hardened_domain_heldout_v3.json`
- Create: `data/evaluation/glm53_flash_hardened_domain_v3_input_plan.json`
- Create: `data/evaluation/contracts/glm53_flash_hardened_context_v3.json`

**Step 1:** 先写失败测试，拒绝任何 RQ-227/V2 问题、case/run ID、fixture bytes、marker 或 Snapshot 身份复用。

**Step 2:** 创建新的匿名三案例资产，继续覆盖正常复盘、用户数据边界和知识数据边界，但措辞、数据和 marker 全新。

**Step 3:** V3 协议固定 `max_revisions=1`、85 分及事实/引用/注入/来源硬门、9/27 调用墙、Task 3 得出的 Token 墙、零 retry/recovery 和首个不安全失败即停。

**Step 4:** no-I/O 准入重新计算全部文件 SHA，并绑定预算报告、质量版本、候选策略和 V3 诊断 Schema；断言 `external_provider_calls=0`。

**Step 5:** 运行 V3 资产测试与 Prompt/Context identity 相邻回归，预期全部通过且不读取环境 Key。

### Task 5: 实现 V3 专用离线运行入口

**Files:**
- Create: `app/evaluation/glm53_hardened_domain_v3_gate.py`
- Create: `scripts/run_glm53_hardened_domain_v3_gate.py`
- Create: `tests/test_glm53_hardened_domain_v3_gate.py`
- Test: `tests/test_glm53_hardened_domain_gate.py`

**Step 1:** 写失败测试，要求 V3 Admission 绑定全新资产、预算报告、`max_revisions=1`、诊断 Schema、当前实现 SHA、公共 CI SHA 和新鲜 G53-3-L 证据身份。

**Step 2:** 用 Fake Provider 覆盖首评直接通过、一次修订后通过、一次修订后拒绝、阻断性安全失败和资源失败；所有结果保持 body-free/create-only。

**Step 3:** 实现 `--preflight-only`。离线实现批尚无新鲜 G53-3-L 时，入口必须返回明确的 `pending_protocol_evidence`，且不能构造 Provider。

**Step 4:** 保留 `--confirm-real-call` 参数但在缺少 exact-SHA 公共 CI、新鲜协议证据或另行授权时失败关闭；本批不得运行该路径。

**Step 5:** 运行 V3/V2 runner 聚焦测试，预期 V3 no-I/O 预检和全部 V2 回归通过。

### Task 6: 比例回归、文档同步与离线提交

**Files:**
- Modify: `docs/requirements_change_log.md`
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Create: `docs/learning/8e-glm53-hardened-domain-v3-bounded-revision-implementation-walkthrough.md`

**Step 1:** 运行 Provider domain、Harness、预算、V2/V3 runner、资产和 body-free 相邻回归。

**Step 2:** 运行：

```powershell
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
git diff --check
.\.venv\Scripts\python.exe scripts/check_project_governance.py
```

预期：全部通过；provider calls=0、network=false。

**Step 3:** 记录本地测试数、V3 预算数值与报告 SHA；明确候选仍未注册、V2 不变、GLM-5.2 应急路径和产品/前端边界不变。

**Step 4:** 提交离线实现。下一检查点只能是该实现 SHA 的公共 CI；公共绿灯后仍须新鲜 G53-3-L 的单独授权，不能自动运行 V3 领域门。

## 执行结果：公共闭环（2026-09-05）

初始实现 `730c32d074269fb45e5a5351b1af591ecaa35de1` 完成 Tasks 1–6 的离线范围；公共运行
`33894351184` 随后暴露两处版本隔离遗漏：旧输入计划未默认锁回零修订，V2 加固回执被总检
误分流为旧结果模型。修复提交 `f99c142c269df765deb592c463ce6e2555bcc3fe` 保持所有旧调用方
默认 `max_revisions=0`，只有 V3 显式传入 `expected_max_revisions=1`，并按 V2 专属 `protocol_id`
严格解析回执。

修复后的相关与相邻回归为 `93 passed`，compileall、diff check、治理检查通过；Actions
`33895602378` 三任务 exact-SHA 全绿，公共 pytest `2379 passed, 145 skipped, 2 warnings,
127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，packaging-smoke 通过。exact-SHA 预检
返回 `pending_protocol_evidence`、provider calls=0。当前 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-hardened-domain-v3-bounded-revision-implementation / completed-public / pending-fresh-g53-3l-authorization`；
下一步仅在用户明确授权后取得新鲜 G53-3-L，不能自动进入 V3 领域观察。

## RQ-235：真实领域验收已执行（2026-09-05）

RQ-234 已通过新鲜协议。随后用户继续授权的一次 V3 在公共代码 `110f9e8` 上执行，首案
2 次模型调用、两次检索成功但 0 片段，终态 rejected/evidence_required；未评测/修订，
后两案跳过。回执 `zhipu_glm53_flash_hardened_domain_v3_rq235_v1.json` 严格校验通过，
admitted=false。这次不测试重抽，也不因结果失败而增加调用。

V3/执行器/预算相关回归 48 passed；公共回执总检为新 V3 增加专属严格分流和 canonical 比对后
相邻 22 passed。没有修改产品实现、前端或质量/检索阈值；下一步只做候选检索合同离线诊断
与版本化加固。详细归因见现有 V3 walkthrough 的 RQ-235 节。
