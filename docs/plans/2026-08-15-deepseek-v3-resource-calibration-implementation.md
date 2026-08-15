# DeepSeek V3 资源校准离线实现计划

> **阶段边界：** 本文是 5D-7 内部实现批，不新增主阶段或子阶段。这里的 V3 是第三次领域采用尝试，不是模型版本。

## 目标

在不读取 API Key、不构造真实 DeepSeek Provider、不运行 V3 held-out 的前提下，把 ADR-0026 冻结的资源校准设计实现成可测试代码：两份全新 development profile 必须通过现有生产组装形成精确四阶段请求；公开快照不得保存请求正文；Fake Provider 必须证明 8-call 完整路径、首错停止和现有资源账本门禁；纯函数必须从完整 Usage 推导 V3 预算，并在成本或 Skill deadline 不可达时拒绝继续。

## 不在本批实现

- 不调用 DeepSeek、GLM、Qwen 或任何外部模型；
- 不读取 `.env` 或 API Key，不新增真实校准 CLI；
- 不创建、查看或运行 V3 held-out；
- 不修改 V2 Dataset、input plan、Context snapshot、结果、Prompt、Skill 或 Harness；
- 不进入 5D exit review、5E、5F 或阶段 6。

## 数据流与控制流

```text
development profile + 独立 fixture
  -> 现有 ProductionDomainCaseExecutor
  -> 受控本地 Provider 强制走四阶段
  -> 内存中的完整 ChatRequest（只给后续回放）
  -> 可公开的 body-free 请求快照（只含摘要和形状）
  -> Fake Provider + 现有 ProviderResourceLedger
  -> 8 条 Usage/latency 安全观察
  -> 纯预算推导器
  -> 允许设计 V3 / 成本超限停止 / Skill deadline 不可达停止
```

## Task 1：冻结 development profile 合同和污染边界

**Files:**

- Create: `app/evaluation/provider_resource_calibration.py`
- Create: `tests/test_provider_resource_calibration.py`
- Create: `data/evaluation/deepseek_v4_pro_resource_calibration_development_profiles.json`
- Create: `examples/fixtures/player_summary_resource_calibration_baseline.json`
- Create: `examples/fixtures/deterministic_report_resource_calibration_baseline.md`
- Create: `examples/fixtures/player_summary_resource_calibration_ceiling.json`
- Create: `examples/fixtures/deterministic_report_resource_calibration_ceiling.md`

**Red tests:**

1. 只接受 `role=development`、`quality_admission_excluded=true`、精确两个 profile 和固定四阶段；
2. fixture 必须是项目内相对路径且 SHA-256 匹配；
3. baseline 与 ceiling 的 profile/case/run ID、fixture digest 和受控正文指纹必须彼此独立；
4. 任一 V2 case ID、注入 marker、fixture digest 或整段正文复用必须在 Provider 前失败；
5. ceiling 必须有 10 条 match 投影，工具调用数量不能超过 Skill 的 3 次上限。

**Focused command:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py -k "profile or contamination" -q
```

## Task 2：用现有生产链生成四阶段请求并创建安全快照

**Files:**

- Modify: `app/evaluation/provider_resource_calibration.py`
- Modify: `tests/test_provider_resource_calibration.py`

**Red tests:**

1. 两个 profile 都精确生成 `agent_initial`、`agent_after_tool`、`evaluation`、`evaluation_repair`；
2. 请求来自现有 Catalog、Router、ExecutionBoundary、ContextBuilder、AgentLoop、本地 RAG、Secure Evaluation 和 ReviewHarness；
3. baseline 使用一次合法检索，ceiling 使用现有 Skill 允许的三次工具调用；
4. `max_revisions=0`，第四次只允许结构化 Evaluation repair；
5. body-free 快照只保存 digest、角色、消息数、本地长度、tool/contract 身份等白名单元数据，序列化结果不得出现 Prompt、用户正文、知识正文、草稿或非法 Evaluation 内容；
6. 完整 `ChatRequest` 只存在于内存内部对象，不是公开 Pydantic 结果字段。

**Focused command:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py -k "capture or envelope" -q
```

## Task 3：实现 Fake 8-call 回放、账本和首错停止

**Files:**

- Modify: `app/evaluation/provider_resource_calibration.py`
- Modify: `tests/test_provider_resource_calibration.py`

**Red tests:**

1. 校准策略固定为 `deepseek/deepseek-v4-pro`、8 calls、64 output/request、64000 observed tokens、`$0.10`、零重试；
2. 8 个请求都在调用前被替换为 `max_tokens=64`；
3. 完整 Fake 路径产生精确 8 条观察并保留按 profile/stage 顺序；
4. 每条观察只保存 provider/model、Usage、latency、finish reason 和 request ID digest，不保存响应正文或原始 request ID；
5. 第 N 次 Provider 失败时只使用 N 次调用，后续请求不再发送；
6. 调用、Token、金额或身份越界沿用现有安全失败码并首错停止；
7. public result 明确 `external_provider_calls=0` 和 `quality_admission_excluded=true`，Fake 结果不能冒充真实模型证据。

**Focused command:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py -k "replay or first_error or ledger" -q
```

## Task 4：实现确定性预算推导和拒绝门

**Files:**

- Modify: `app/evaluation/provider_resource_calibration.py`
- Modify: `tests/test_provider_resource_calibration.py`

**Red tests:**

1. 只接受完整 8/8 观察，7/8 不得产生推荐预算；
2. 每阶段取两个 profile 最大 input，乘 `1.25` 并向上到 256；
3. 单例 output 固定 `4 * 1024`，总 Token 向上到 1024；
4. 三案例 domain、1428 历史协议 Token 和历史 `$0.00221496` 成本按 ADR-0026 公式计算；
5. 总成本向上到美分且超过 `$0.10` 时拒绝创建 V3；
6. 延迟使用逐阶段最大值、25% 余量和向上到 5000；
7. 前两次 Agent 的带余量延迟超过 Skill 30 秒时独立拒绝；
8. 纯整数/Decimal 计算可重复，不使用 float 或平均值。

**Focused command:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py -k "derive or budget or deadline" -q
```

## Task 5：实现零 I/O admission 与回归保护

**Files:**

- Modify: `app/evaluation/provider_resource_calibration.py`
- Modify: `tests/test_provider_resource_calibration.py`
- Modify: `tests/test_provider_domain_production.py` only if a production observation seam is strictly necessary; otherwise leave unchanged.

**Red tests:**

1. prepare/admission 函数不接受 Provider、Key、SDK client 或网络配置；
2. code SHA 与 public CI SHA 不一致或 CI 未确认时拒绝；
3. profile/request snapshot/政策身份漂移时拒绝；
4. 输出明确 `external_provider_calls=0`、`held_out_created=false`、`provider_construction_authorized=false`；
5. V1/V2 资产逐字节 digest 不变，现有 DeepSeek held-out/readmission 测试继续通过。

**Focused command:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py tests/test_provider_domain_production.py tests/test_provider_domain_readmission.py -q
```

## Task 6：文档、完整门禁和公开冻结

**Files:**

- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`

**Verification:**

```powershell
python -m pytest tests/test_provider_resource_calibration.py -q
python -m pytest tests/test_provider_domain_production.py tests/test_provider_adoption.py tests/test_provider_domain_readmission.py -q
python -m pytest -q
python -m compileall app scripts tests
python scripts/evaluate_rag.py --dataset data/evaluation/rag_retrieval_cases.json --json
python scripts/evaluate_rag.py --dataset data/evaluation/rag_v1_holdout_cases.json --json
python scripts/validate_harness_dry_run.py
python scripts/check_tracked_data.py
python scripts/check_project_governance.py
git diff --check
```

验收后提交并推送；随后验证 GitHub Actions 对该精确 commit SHA 成功。本批结束时只能声称“离线校准基础设施和公开冻结完成”，不能声称 DeepSeek V3 已校准、已通过或已获领域准入。
