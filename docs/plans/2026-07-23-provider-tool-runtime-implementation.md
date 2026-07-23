# Provider and Tool Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建立厂商无关的 LLM Provider 和可测试的可靠 Tool Runtime，并让 Harness 与现有外部能力逐步迁移到统一契约。

**Architecture:** Provider 只适配模型厂商请求、响应和错误；Tool Runtime 负责工具注册、Schema、缓存、重试、熔断、fallback 和指标；Harness 保持独立，通过 Adapter 使用两者。阶段 3 使用同步单进程实现，所有网络超时由底层 Client 执行。

**Tech Stack:** Python 3.11、dataclasses、Protocol、Enum、jsonschema、OpenAI-compatible SDK、requests、pytest/unittest。

---

### Task 1：定义 Provider 契约和错误模型

**Files:**
- Create: `app/providers/__init__.py`
- Create: `app/providers/models.py`
- Create: `app/providers/protocol.py`
- Create: `app/providers/errors.py`
- Test: `tests/test_provider_contracts.py`

**Steps:**

1. 编写失败测试，覆盖消息角色、空消息、温度、超时、Token Usage、响应内容和错误安全字段。
2. 运行 `py -3.11 -m pytest tests/test_provider_contracts.py -q`，确认模块缺失失败。
3. 最小实现 `ChatMessage`、`ChatRequest`、`TokenUsage`、`ChatResponse`、`LLMProvider` 和错误层次。
4. 验证异常字符串不包含 credential 或原始请求正文。
5. 运行目标测试和完整测试。
6. 提交：`feat: define llm provider contracts`。

### Task 2：实现智谱 GLM Provider

**Files:**
- Create: `app/providers/zhipu.py`
- Create: `app/providers/config.py`
- Modify: `.env.example`
- Test: `tests/test_zhipu_provider.py`

**Steps:**

1. 使用 Fake OpenAI-compatible Client 编写请求映射和响应解析失败测试。
2. 测试配置缺失、空响应、认证、限流、超时、服务不可用和非法响应。
3. 实现 `ZhipuProvider`，只依赖注入 Client，不在构造函数读取全局环境变量。
4. 实现配置工厂，集中读取环境变量并创建真实 Client。
5. 保证业务日志和异常不包含 API Key。
6. 运行测试并提交：`feat: add zhipu llm provider`。

### Task 3：定义工具契约、Schema 和注册表

**Files:**
- Create: `app/tools/__init__.py`
- Create: `app/tools/models.py`
- Create: `app/tools/errors.py`
- Create: `app/tools/schema.py`
- Create: `app/tools/registry.py`
- Modify: `pyproject.toml`
- Test: `tests/test_tool_contracts.py`
- Test: `tests/test_tool_registry.py`

**Steps:**

1. 编写工具名称/版本、执行上下文、结果、可靠性策略和重复注册测试。
2. 加入 `jsonschema` 依赖，编写输入与输出 Schema 失败测试。
3. 实现不可变 `ToolDefinition`、`ToolContext`、`ToolResult` 和错误分类。
4. 实现 Registry 的注册、查找、列举和重复拒绝。
5. 运行测试并提交：`feat: define tool runtime contracts`。

### Task 4：实现有界 TTL Cache 和三态熔断器

**Files:**
- Create: `app/tools/cache.py`
- Create: `app/tools/circuit_breaker.py`
- Test: `tests/test_tool_cache.py`
- Test: `tests/test_circuit_breaker.py`

**Steps:**

1. 使用 Fake Clock 编写缓存命中、过期、稳定键和容量淘汰测试。
2. 编写 CLOSED、OPEN、HALF_OPEN、恢复成功与失败测试。
3. 实现有界内存 TTL Cache 和每工具熔断器。
4. 确保认证/参数错误不计入熔断。
5. 运行测试并提交：`feat: add tool cache and circuit breaker`。

### Task 5：实现可靠 Tool Runtime

**Files:**
- Create: `app/tools/runtime.py`
- Create: `app/tools/metrics.py`
- Test: `tests/test_tool_runtime.py`

**Steps:**

1. 编写成功、输入无效、输出无效、未知工具和 Handler 异常测试。
2. 编写仅幂等/可重试错误重试、预算耗尽不重试和 Fake Sleep 退避测试。
3. 编写缓存命中、熔断打开、半开探测、fallback 成功/失败测试。
4. 实现执行顺序：查找 → 输入校验 → 缓存 → 熔断 → 有界尝试 → 输出校验 → 缓存 → 指标。
5. 明确区分 upstream success、cache hit 和 fallback success。
6. 运行测试并提交：`feat: implement reliable tool runtime`。

### Task 6：包装 RiftCoach 的现有外部能力

**Files:**
- Create: `app/tools/adapters/__init__.py`
- Create: `app/tools/adapters/riot.py`
- Create: `app/tools/adapters/data_dragon.py`
- Create: `app/tools/adapters/knowledge.py`
- Create: `app/tools/adapters/llm.py`
- Test: `tests/test_riftcoach_tool_adapters.py`

**Steps:**

1. 为 Riot、Data Dragon、本地 RAG 和 LLM 编写 Fake 依赖测试。
2. 定义稳定工具名称、版本和输入/输出 Schema。
3. 将 ToolContext 的剩余预算传入支持超时的底层调用。
4. 为本地 RAG 和 Data Dragon 配置安全缓存；玩家动态数据默认不缓存或短 TTL。
5. 运行测试并提交：`feat: register riftcoach external tools`。

### Task 7：迁移 Harness 到 Provider 与 Tool Runtime

**Files:**
- Modify: `app/harness/adapters.py`
- Modify: `scripts/run_review_harness.py`
- Modify: `scripts/generate_llm_coach_report.py`
- Modify: `scripts/evaluate_coach_report.py`
- Modify: `scripts/revise_coach_report.py`
- Test: `tests/test_harness_adapters.py`
- Test: `tests/test_provider_tool_harness_integration.py`

**Steps:**

1. 编写测试，禁止 Harness Adapter 访问 SDK `choices` 结构。
2. 让生成、评测和修订依赖 `LLMProvider.chat()`。
3. 让本地 RAG 通过 Tool Runtime 返回 `KnowledgeEvidence`。
4. 移除脚本内重复的 Client/环境变量装配。
5. 保留原 CLI 参数和 dry-run 行为。
6. 运行测试并提交：`refactor: route harness through provider runtime`。

### Task 8：故障、指标、安全和兼容性验收

**Files:**
- Create: `docs/provider_tool_runtime_usage.md`
- Modify: `README.md`
- Modify: `docs/roadmap.md`
- Modify: `.github/workflows/tests.yml`
- Test: `tests/`

**Steps:**

1. 运行完整测试与 Harness fixture dry-run。
2. 增加故障集成测试：限流后成功、认证失败不重试、熔断后 fallback、缓存不污染。
3. 检查日志与异常中不存在 Key、Authorization、完整 PUUID。
4. 文档解释 Provider、Tool Runtime、Harness 和 MCP 的区别。
5. 记录 EchoMind 迁移项、修正项和未迁移项。
6. 更新路线状态但不改变阶段 0—8。
7. 提交：`docs: complete provider tool runtime stage`。

## 阶段验收

```powershell
py -3.11 -m pytest -q
python scripts\run_review_harness.py `
  --summary examples\fixtures\player_summary_demo.json `
  --deterministic-report examples\fixtures\deterministic_report_demo.md `
  --run-id provider_runtime_acceptance `
  --dry-run
```

预期：完整测试通过；Harness 不直接实例化具体 SDK Client；Fake Provider 可以替换智谱实现；所有 Tool 调用输出统一结果和指标；失败有界且不会泄漏凭据；内部 Tool Runtime 不被称为 MCP。
