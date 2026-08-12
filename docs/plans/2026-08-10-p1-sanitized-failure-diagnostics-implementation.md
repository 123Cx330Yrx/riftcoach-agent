# P1 Sanitized Failure Diagnostics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 在不进行真实网络调用的前提下，让 GLM P1 失败保留无正文的安全响应观察，
并增加严格单调用的 `p1_diagnostic` scope。

**Architecture:** `CapabilityProbeCaseResult` 升级为兼容 v1.0 的 v1.1 证据合同；
`ZhipuCapabilityProbe` 在 SDK 返回后先生成白名单 observation，再进行语义验证；CLI 用
scope 同时决定调用预算和独立输出路径。原始响应只在调用栈中瞬时存在。

**Tech Stack:** Python 3.11、Pydantic v2、OpenAI-compatible SDK test doubles、pytest。

---

### Task 1: Versioned safe-observation result contract

**Files:**
- Modify: `app/evaluation/provider_capability_gate.py`
- Test: `tests/test_provider_capability_gate.py`

1. 写失败测试：旧 v1.0 JSON 可读取且新增 observation 为 unknown；新 v1.1 case 必须
   明确 `response_received`，并拒绝响应状态与字段形状矛盾。
2. 运行 `pytest tests/test_provider_capability_gate.py -q`，确认新断言失败。
3. 增加 `ResponseFieldState`、`probe_scope`、v1.0/v1.1 兼容与 skipped/未响应不变量。
4. 重跑目标测试，确认通过。

### Task 2: Preserve sanitized metadata across semantic failure

**Files:**
- Modify: `app/providers/zhipu_probe.py`
- Test: `tests/test_zhipu_capability_probe.py`

1. 写失败测试：`content=None` 失败仍保留 model、finish、usage、request hash；非空
   `reasoning_content` 只产生 `non_empty` 状态且原文不进入 JSON。
2. 写参数化失败测试：missing/null/empty/non-string 分别分类；SDK 异常仍未收到响应。
3. 运行目标测试，确认旧失败路径丢失 observation。
4. 实现内部冻结 `_SafeResponseObservation` 和无正文字段分类；`_run_case` 在 validator
   失败时投影同一 observation，绝不持久化 raw content/request id。
5. 重跑 probe 与 result-contract 测试。

### Task 3: One-call diagnostic scope and CLI boundary

**Files:**
- Modify: `app/providers/zhipu_probe.py`
- Modify: `scripts/probe_zhipu_capabilities.py`
- Test: `tests/test_zhipu_capability_probe.py`
- Test: `tests/test_probe_zhipu_capabilities_cli.py`

1. 写失败测试：`p1_diagnostic` 只产生 P1、最多调用一次，P1 成功也不继续 P2-P5。
2. 写失败测试：CLI scope 与 max_calls 必须是 `p1_p5/5` 或 `p1_diagnostic/1`；未确认
   时仍在 client factory 前拒绝；两个 scope 使用不同默认输出路径。
3. 实现 scope 驱动的预算、控制流、结果元数据和 CLI 参数，不增加任何自动重试。
4. 重跑 Task 1-3 聚焦测试，确认默认 pytest 没有网络调用。

### Task 4: Offline closeout and authorization gate

**Files:**
- Modify: active `task_plan.md`, `findings.md`, `progress.md`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/plans/2026-08-10-p1-sanitized-failure-diagnostics-design.md`

1. 运行结构化输出/Provider 聚焦回归、完整 pytest、compileall、diff check、密钥/运行
   数据检查和治理预检。
2. 明确记录“离线诊断已就绪但未调用 GLM”，唯一下一步改为是否授权一次
   `p1_diagnostic` 调用；不得自动进入 Task 4 production Adapter。
3. 提交、推送并核对精确 SHA 的 GitHub Actions。

## Execution progress

- Tasks 1-3 completed locally on 2026-08-10.
- Focused result/Probe/CLI tests: `24 passed`.
- Proportional Provider/structured regression: `82 passed, 42 subtests passed`.
- No real Provider call, API-key read, production Adapter change or P2-P5 execution occurred.
- Task 4 completed offline on 2026-08-12: full regression `383 passed, 95 subtests passed`;
  both RAG gates, compileall, Harness SDK boundary, tracked secret/run-data check, Harness dry-run
  and governance passed.
- The first public closeout run exposed an unbounded OpenAI SDK major-version drift. The verified
  contract is now pinned to `openai>=2,<3`; a clean TEMP venv resolved `openai 2.54.0` and passed
  the same `383` tests plus `95` subtests.
- The plan is complete. The repository now stops at a separate authorization gate: only a new,
  explicit user approval may permit one `p1_diagnostic/1` real call. That approval would not permit
  P2-P5, production Adapter work, a second Provider or 5D-7.
