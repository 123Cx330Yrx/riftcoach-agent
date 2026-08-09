# Real Provider Capability Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 在最多 12 次真实外部调用的硬上限内，验证 GLM-5.2 的文本、JSON 模式、
Function Calling、Zhipu Adapter 和一个 RiftCoach 领域切片，并据证据决定是否触发
最多一个第二 Provider 对照。

**Architecture:** 先用隔离的 Zhipu 微探针验证厂商 API，再用 TDD 扩展现有
`ZhipuProvider`，最后把同一 Adapter 接入一个固定的 `recent-form-review` 切片。所有
公开结果只保存脱敏指标和输出摘要，默认 pytest/CI 永不调用真实模型。

**Tech Stack:** Python 3.11、OpenAI-compatible Python client、Pydantic v2、现有
Provider/AgentLoop/ToolRuntime/ReviewHarness、pytest。

---

### Task 1: Provider capability result and call-budget contracts

**Files:**
- Create: `app/evaluation/provider_capability_gate.py`
- Modify: `app/evaluation/__init__.py`
- Test: `tests/test_provider_capability_gate.py`

1. 写失败测试：case/report 必须拒绝未知字段、非法状态、负 Token/延迟、重复 case ID。
2. 写失败测试：外部调用预算在第 6 次调用前拒绝，未执行调用不得消耗预算。
3. 运行目标测试，确认缺少模块或合同的红灯。
4. 实现冻结的 Pydantic 结果合同、总体准入判定和 `ExternalCallBudget(max_calls=5)`。
5. 运行目标测试，确认所有合同与预算测试通过。

### Task 2: Isolated Zhipu P1-P5 microprobe

**Files:**
- Create: `app/providers/zhipu_probe.py`
- Create: `scripts/probe_zhipu_capabilities.py`
- Test: `tests/test_zhipu_capability_probe.py`

1. 写 Fake SDK 红灯，覆盖 P1 文本、P2/P3 严格 Evaluation JSON、P4 ToolCall 和 P5
   Tool Observation final response。
2. 写错误红灯：P1 失败停止全部；P4 失败跳过 P5；全部调用永不超过 5；异常和输出
   原文不进入公开结果。
3. 实现无重试 `ZhipuCapabilityProbe`，结构化案例复用 5D-6a
   `EvaluationResponseModel` 与严格 decoder。
4. 实现显式 CLI 门：没有 `--confirm-real-call` 时拒绝调用；从 `.env` 读取配置但不打印
   Key；结果写入调用方指定路径。
5. 运行目标测试、Provider 合同测试和密钥/运行数据检查。

### Task 3: Execute the authorized P1-P5 GLM microprobe

**Files:**
- Create after success: `data/evaluation/results/provider_capabilities/zhipu_glm52_p1_p5.json`
- Modify: active `findings.md` and `progress.md`

1. 只检查 `.env` 所需键是否存在，不显示值。
2. 记录运行前 Git SHA、配置的 model ID 和官方文档快照日期。
3. 用 `--confirm-real-call --max-calls 5` 运行一次 P1-P5；不自动重试。
4. 核对结果不含 API Key、完整 Prompt、原始响应或原始异常。
5. 若任一 mandatory case 失败，保存结果并停止进入 Task 4；若全部通过，进入下一批。

**Execution result (2026-08-09):** code SHA `b07f986421b1c14ef36656f3a44698decacc9d24`
只执行了 P1；API 返回后未得到符合非空文本合同的 message content，脱敏错误码为
`invalid_text_response`，耗时 4265 ms。P2-P5 按依赖规则 skipped，调用数为 1/5，Task 4
按本计划停止。任何诊断性重跑都需要先补强脱敏元数据设计并重新取得显式授权。

### Task 4: Production Zhipu Adapter mapping

**Files:**
- Modify: `app/providers/zhipu.py`
- Modify: `app/providers/errors.py` only if a stable new error code is required
- Test: `tests/test_zhipu_provider.py`

1. 写失败测试：四类消息、ToolSpec、AUTO/NONE、JSON mode 和 ToolCall response。
2. 写失败测试：REQUIRED、不合法 arguments、array arguments、未知别名、重复 ID。
3. 写失败测试：`knowledge.search` 使用确定性安全别名，响应后恢复原名；别名冲突
   fail closed。
4. 实现每请求别名表、请求映射、响应规范化和 capability flags。
5. 运行 Zhipu、Provider capability、AgentLoop 和 Tool Adapter 聚焦回归。

### Task 5: Real Adapter protocol slice

**Files:**
- Extend: `scripts/probe_zhipu_capabilities.py`
- Test: `tests/test_zhipu_capability_probe.py`
- Create after success: `data/evaluation/results/provider_capabilities/zhipu_adapter_slice.json`

1. 增加显式 adapter 模式，真实运行 Provider-neutral structured request。
2. 真实运行 `AgentLoop + fixed read-only tool`，确认内部 `knowledge.search` 经别名往返。
3. 调用计入第二层 7 次总预算，不得和 P1-P5 各自无限增长。
4. 保存脱敏协议结果；失败时保持相应 capability 未准入并停止领域 Harness。

### Task 6: One real recent-form domain slice

**Files:**
- Create: `scripts/run_real_provider_skill_slice.py`
- Test: `tests/test_real_provider_skill_slice.py`
- Create after success: `data/evaluation/results/provider_capabilities/zhipu_recent_form_slice.json`

1. 复用匿名化 Summary fixture、真实 Catalog/Router/Boundary/ContextBuilder、本地 RAG、
   AgentLoop、ReviewHarness 与 typed output。
2. 用计数 Provider wrapper 强制本层与 Task 5 合计最多 7 次外部调用。
3. 记录 ToolCall、Evidence、严格 Evaluation、repair、terminal state、usage 和 latency。
4. 不根据本例调 Prompt；published/degraded/rejected 原样记录，协议成功与报告质量分开。
5. 清除未跟踪的本地 run 原文，只保留脱敏结果。

### Task 7: Admission decision and checkpoint closeout

**Files:**
- Create: `docs/adr/0012-<admit-or-reject>-glm-provider-capabilities.md`
- Modify: canonical state、活动计划、路线历史、能力矩阵和项目决策

1. 汇总 P1-P5、Adapter 和领域切片的 mandatory 结果、Token、延迟与未知价格项。
2. 决定 GLM capability 采用、局部采用或拒绝；只有真实阻断才决定是否另开一个第二
   Provider 候选对照，不在本任务中擅自接入。
3. 运行聚焦回归、完整 pytest、compileall、diff check、治理和仓库现有 CI 门禁。
4. 提交、推送并核对精确 SHA 的 GitHub Actions。
5. 只在全部准入工作完成后把唯一下一步改为 5D-7；否则保持 5D-6b 并写明阻断。
