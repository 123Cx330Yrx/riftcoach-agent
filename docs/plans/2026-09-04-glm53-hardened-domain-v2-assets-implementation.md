# GLM-5.3 Flash Hardened Domain V2 Assets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 RQ-228 加固后的候选建立一套全新、不可与 RQ-227 混用、可在零外部调用下审计的领域验证协议与资产。

**Architecture:** 新的只读准入器加载协议计划、held-out Dataset、V1.1 Input Plan 与 Prompt/Context Snapshot，重新计算 fixture 和上下文身份，并把它们绑定到候选请求策略与 `glm53-flash-domain-quality-v1`。任何身份漂移、历史 ID/marker 复用、加固缺失或资源墙放宽都 fail closed。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, versioned JSON assets.

---

### Task 1: 固定新版本合同与失败测试

**Files:**
- Create: `tests/test_glm53_hardened_domain_assets.py`
- Modify: `tests/test_prompt_context_identity.py`

1. 写出新准入对象必须包含的协议、数据、上下文、加固和零 I/O 身份断言。
2. 写出缺少冻结确认、历史 case/marker 复用、加固版本漂移时拒绝的测试。
3. 写出候选 policy 附录会改变每案 Context identity、默认调用保持不变的测试。
4. 运行聚焦测试，确认在实现前失败。

### Task 2: 让 Prompt/Context 身份支持显式候选 policy

**Files:**
- Modify: `app/evaluation/prompt_context_identity.py`

1. 为多案例 snapshot 构建器增加默认关闭的 `policy_addendum` 参数。
2. 只把显式参数传入 ContextBuilder；保持所有旧调用和旧 snapshot 字节身份不变。
3. 运行 Context 身份聚焦测试。

### Task 3: 新建 V2 合成数据和冻结资产

**Files:**
- Create: `examples/fixtures/player_summary_glm53_flash_hardened_v2.json`
- Create: `examples/fixtures/deterministic_report_glm53_flash_hardened_v2.md`
- Create: `data/evaluation/glm53_flash_hardened_domain_protocol_v2.json`
- Create: `data/evaluation/glm53_flash_hardened_domain_heldout_v2.json`
- Create: `data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json`
- Create: `data/evaluation/contracts/glm53_flash_hardened_context_v2.json`

1. 使用与 RQ-227 不同的匿名数据、问题、case/run ID 和 marker。
2. 冻结 fixture SHA、每案 Context commitment 和聚合 Snapshot SHA。
3. 明确协议预算与 RQ-228 加固版本，不放宽既有安全门。

### Task 4: 实现 no-I/O 交叉准入

**Files:**
- Create: `app/evaluation/glm53_hardened_domain_assets.py`

1. 严格解析协议计划并核对候选策略、质量版本、预算、终止规则和零重试。
2. 加载 Dataset/Input Plan/Snapshot，拒绝所有历史 case ID 和 marker。
3. 重新构建带候选 policy 附录的 Context Snapshot，要求与冻结文件完全一致。
4. 返回只含 ID、SHA、计数与 `external_provider_calls=0` 的公开安全准入对象。

### Task 5: 验证并持久化检查点

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

1. 运行聚焦测试、相邻回归、compileall、diff check 和治理检查。
2. 记录 provider calls=0、候选仍未注册、产品边界未改变。
3. 将唯一下一动作设为同一实现 SHA 的公共 CI；真实调用不得自动开始。

