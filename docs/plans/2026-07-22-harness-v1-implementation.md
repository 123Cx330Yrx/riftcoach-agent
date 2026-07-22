# Harness v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有报告生成、评测和受限修订脚本整合为可追踪、可降级、可测试的单入口 Harness v1。

**Architecture:** 使用同步线性状态机和文件型 Run Store。步骤通过小型接口注入，使状态机测试不依赖真实外部 API；现有生成、评测和修订逻辑逐步适配，阶段 3 再统一为正式 Provider/Tool Runtime。

**Tech Stack:** Python 3.11、dataclasses、Enum、JSON、pathlib、hashlib、pytest/unittest、现有 OpenAI-compatible GLM 调用。

---

### Task 1: 定义运行状态与配置

**Files:**
- Create: `app/harness/__init__.py`
- Create: `app/harness/models.py`
- Test: `tests/test_harness_models.py`

**Steps:**

1. 编写失败测试，覆盖合法状态、终态、默认阈值和最大修订次数。
2. 运行 `py -3.11 -m pytest tests/test_harness_models.py -q`，预期因模块不存在而失败。
3. 最小实现 `RunStatus`、`ArtifactKind`、`HarnessConfig` 和 `RunManifest`。
4. 再次运行测试，预期通过。
5. 提交：`feat: define harness run models`。

### Task 2: 实现文件型 Artifact 与 Run Store

**Files:**
- Create: `app/harness/store.py`
- Modify: `.gitignore`
- Test: `tests/test_harness_store.py`

**Steps:**

1. 编写失败测试：创建运行目录、写 Artifact、计算 SHA-256、原子更新 Manifest、读取后哈希一致。
2. 运行目标测试并确认失败。
3. 实现 `FileRunStore`，仅允许相对路径位于当前 run 目录内。
4. 将 `data/runs/` 加入 `.gitignore`。
5. 运行测试并提交：`feat: add file-backed harness store`。

### Task 3: 实现状态推进规则

**Files:**
- Create: `app/harness/state_machine.py`
- Test: `tests/test_harness_state_machine.py`

**Steps:**

1. 编写合法推进、非法跳转、终态不可变和 attempt 过期测试。
2. 运行测试并确认失败。
3. 实现显式 transition 表和 `advance()`；非法转换抛出领域异常。
4. 运行测试并提交：`feat: add harness state machine`。

### Task 4: 抽取可注入的运行步骤协议

**Files:**
- Create: `app/harness/steps.py`
- Test: `tests/test_harness_steps.py`

**Steps:**

1. 用 Fake 实现编写协议测试，定义检索、生成、评测和修订的输入输出。
2. 运行测试并确认缺少协议。
3. 使用 `Protocol` 与 dataclass 定义最小步骤边界，不迁移厂商 SDK。
4. 运行测试并提交：`feat: define harness step contracts`。

### Task 5: 实现 Harness Runtime 的通过路径

**Files:**
- Create: `app/harness/runtime.py`
- Test: `tests/test_harness_runtime.py`

**Steps:**

1. 编写 Fake Steps 测试：输入有效、RAG 成功、草稿成功、首次评测通过、最终发布 Coach 报告。
2. 运行测试并确认失败。
3. 实现最小 `ReviewHarness.run()`，逐步保存 Artifact 和状态。
4. 验证最终 Manifest 为 `PUBLISHED`，且 final_report 哈希对应草稿。
5. 提交：`feat: run quality-gated review workflow`。

### Task 6: 实现修订、预算与降级路径

**Files:**
- Modify: `app/harness/runtime.py`
- Test: `tests/test_harness_runtime.py`

**Steps:**

1. 增加失败测试：修订后通过、复评失败、RAG 异常、生成异常、非法评测、修订越权。
2. 实现最大一次修订和确定性报告降级。
3. 保证任何未通过 Coach 草稿都不会进入 `output/final_report.md`。
4. 运行 Harness 测试并提交：`feat: enforce revision budget and safe fallback`。

### Task 7: 适配现有业务逻辑与单入口 CLI

**Files:**
- Create: `app/harness/adapters.py`
- Create: `scripts/run_review_harness.py`
- Modify: `README.md`
- Test: `tests/test_harness_adapters.py`

**Steps:**

1. 为现有本地 RAG、Coach prompt、评测 parser 和修订 validator 编写适配器测试。
2. 最小复用现有函数，不复制 Prompt 和解析逻辑。
3. CLI 接受 Summary、确定性报告、运行目录、阈值和修订上限。
4. 增加 `--dry-run` 或 Fake 模式，用本地 fixture 验证而不消耗模型额度。
5. 运行测试并提交：`feat: add review harness entrypoint`。

### Task 8: 完整验证、文档和开源检查点

**Files:**
- Modify: `README.md`
- Create: `docs/harness_v1_usage.md`
- Create: `.github/workflows/tests.yml`
- Test: `tests/`

**Steps:**

1. 运行 `py -3.11 -m pytest -q`，预期全部通过。
2. 用匿名 fixture 跑一次 dry-run，检查 Manifest、Artifact 和发布决定。
3. 运行敏感文件检查，确认 `.env`、`data/cache/`、`data/runs/` 未被跟踪。
4. 文档说明状态机、运行命令、目录、降级行为和表述边界。
5. 配置 GitHub Actions 在 Python 3.11 执行测试。
6. 提交：`docs: document harness v1 and add ci`。

## 阶段验收

```powershell
py -3.11 -m pytest -q
python scripts\run_review_harness.py --help
```

预期结果：所有测试通过；CLI 可显示完整参数；Fake/dry-run 可生成带哈希的运行 Manifest；失败路径只能降级为确定性报告或拒绝，不能发布未通过的 Coach 草稿。
