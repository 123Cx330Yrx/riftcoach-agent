# Structured Output Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 为 RiftCoach 的机器控制数据建立 Provider-neutral 结构化响应合同、严格 Pydantic 校验、最多一次修复和 fail-closed 边界。

**Architecture:** `ChatRequest` 显式携带 JSON Schema 合同，能力协商据此要求结构化输出；LLM Tool Adapter 传递合同；Harness Evaluation Adapter 用严格 Pydantic 模型验证规范化响应，并最多发起一次同合同修复调用。真实厂商 SDK 映射留给 5D-6b。

**Tech Stack:** Python 3.11、dataclasses、Pydantic v2、Protocol、pytest/unittest、现有 Provider/Tool Runtime/Harness。

---

### Task 1: Provider-neutral response contract

**Files:** `app/providers/models.py`, `app/providers/capabilities.py`, `app/providers/__init__.py`, `tests/test_provider_contracts.py`, `tests/test_provider_capabilities.py`

1. 写失败测试：合同名称、版本、object Schema、不可变快照。
2. 写失败测试：结构化请求要求 `STRUCTURED_OUTPUT`，普通请求保持原行为。
3. 运行目标测试确认红灯。
4. 实现合同、请求字段和能力协商。
5. 运行目标测试确认通过。

### Task 2: Strict Pydantic decoder and bounded repair

**Files:** `app/providers/structured.py`, `app/providers/errors.py`, `app/providers/__init__.py`, `tests/test_structured_output.py`

1. 写合法 JSON、缺字段、额外字段、错误类型、非法枚举、非 JSON、fence、截断测试。
2. 写 repair callback 最多一次、修复成功/失败和安全异常测试。
3. 运行目标测试确认红灯。
4. 实现泛型模型解码、repair request/callback 和 `invalid_structured_output` 错误。
5. 运行目标测试确认通过。

### Task 3: Pass contracts through `llm.chat`

**Files:** `app/tools/adapters/llm.py`, `tests/test_riftcoach_tool_adapters.py`, `tests/test_provider_tool_harness_integration.py`

1. 写失败测试：Tool 输入的 response contract 进入 `ChatRequest`。
2. 写失败测试：text-only Provider 在 SDK/Fake 调用前失败。
3. 扩展 `llm.chat` 输入 Schema 和 Handler，不改变普通文本调用。
4. 运行 Tool/Provider 集成测试。

### Task 4: Strict evaluation response model

**Files:** `app/evaluation/coach_report.py`, `tests/test_coach_report_evaluation.py`

1. 写 Pydantic 合法/非法 payload 测试，覆盖嵌套字段和额外字段。
2. 用模型 JSON Schema 作为 Prompt 的机器合同来源。
3. 让旧 parser 成为调用同一严格模型的薄兼容函数。
4. 运行评测合同测试。

### Task 5: Compose one repair into `ChatEvaluationAdapter`

**Files:** `app/harness/adapters.py`, `scripts/run_review_harness.py`, `scripts/evaluate_coach_report.py`, `tests/test_harness_adapters.py`, `tests/test_provider_tool_harness_integration.py`

1. 写合法、一次修复成功、修复失败和零无限重试测试。
2. 让评测适配器传递同一合同并使用严格模型/decoder。
3. repair prompt 只要求 Schema 修复，第二次失败交给 Harness 既有降级/拒绝。
4. 保留旧接口的兼容边界，但生产组合不再注入任意 dict parser。
5. 运行 Harness Adapter 和 Provider/Tool 集成测试。

### Task 6: Verification and checkpoint closeout

**Files:** 状态、活动计划、发现、路线历史、v1.3、能力矩阵和项目决策文档，以及必要回归测试

1. 证明结构化评测失败时不发布猜测结果，只降级或拒绝。
2. 运行聚焦回归、完整 pytest、compileall、`git diff --check`、治理预检和仓库既有门禁。
3. 只标记 5D-6a 完成，下一步设置为 5D-6b；公开说明未调用真实 Provider。
4. 提交、推送、核对 CI；停止，不进入 5D-6b。
